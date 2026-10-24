import logging
import os
import requests
import uvicorn
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from services.whapi_client import WhapiClient
from db.db_manager import (
    SupabaseService,
    DatabaseOperationError,
    StorageOperationError,
)
from workflow.graph import greenready_graph
from gmail_reader.api import poller as gmail_poller
import marketplace

# Configure structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    gmail_poller.task = asyncio.create_task(gmail_poller.run())
    try:
        yield
    finally:
        if gmail_poller.task:
            gmail_poller.task.cancel()
            try:
                await gmail_poller.task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Orbyte GreenReady Webhook Orchestrator",
    lifespan=lifespan,
)
marketplace.register(app)
marketplace.mount_frontend(app)


@app.get("/", include_in_schema=False)
async def index():
    return {"status": "online", "message": "GreenReady API is active"}

# Initialize shared singleton services
whapi_token = os.getenv("WHAPI_TOKEN", "")
whapi_client = WhapiClient(api_token=whapi_token)
supabase_service = SupabaseService()


def send_whatsapp_message(to_number: str, body_text: str) -> bool:
    """
    Sends an outbound text response to the SME owner via Whapi.cloud.
    """
    url = "https://gate.whapi.cloud/messages/text"
    headers = {
        "Authorization": f"Bearer {whapi_client.token}",
        "Content-Type": "application/json",
    }
    payload = {"to": to_number, "body": body_text, "typing_time": 0}

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        logger.info("Outbound WhatsApp notification delivered to %s", to_number)
        return True
    except requests.exceptions.RequestException as exc:
        logger.error("Failed to send WhatsApp message to %s: %s", to_number, exc)
        return False


@app.post("/webhook/whapi")
@app.post("/webhook/whapi/")
async def whapi_webhook(request: Request):
    """
    Main webhook entry point.
    Handles media downloads, Supabase persistence, and LangGraph interrupts.
    """
    try:
        payload = await request.json()
    except Exception as exc:
        logger.error("Invalid JSON payload received: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "error", "message": "Malformed JSON"},
        )

    messages = payload.get("messages", [])
    if not messages:
        return {"status": "ignored", "reason": "No messages in webhook payload"}

    msg = messages[0]
    raw_sender = msg.get("chat_id", "")
    sender_number = raw_sender.split("@")[0]
    msg_type = msg.get("type")

    if not sender_number:
        logger.warning("Webhook received message without a valid chat_id.")
        return {"status": "ignored", "reason": "Missing chat_id"}

    # LangGraph checkpoints state using the sender's phone number as the thread ID
    thread_config = {"configurable": {"thread_id": sender_number}}

    # =========================================================================
    # SCENARIO 1: TEXT MESSAGE (Human-in-the-Loop Consent Approval)
    # =========================================================================
    if msg_type == "text":
        incoming_text = msg.get("text", {}).get("body", "").strip().upper()
        current_state = greenready_graph.get_state(thread_config)

        # Check if the graph is paused at the approval checkpoint
        if current_state.next and incoming_text in {"YES", "APPROVE", "CONFIRM", "Y"}:
            logger.info("Human consent granted via WhatsApp for thread: %s", sender_number)

            # Update the paused graph state with approval flag
            greenready_graph.update_state(
                thread_config,
                {"human_approved": True},
            )

            # Resume execution (routes through node_publish_to_marketplace -> END)
            greenready_graph.invoke(None, thread_config)

            # Log verified consent in the immutable audit log
            sme_id = current_state.values.get("sme_id")
            if sme_id:
                supabase_service.log_audit_event(
                    sme_id=sme_id,
                    action_type="WHATSAPP_CONSENT_GRANTED",
                    actor_role="SME_OWNER",
                    metadata={"sender_number": sender_number, "text": incoming_text},
                )

            send_whatsapp_message(
                to_number=sender_number,
                body_text=(
                    "✅ *Verification Published*\n\n"
                    "Your anonymized Green Dossier is now live on the Orbyte Opportunity Board. "
                    "Matched licensed lenders and verified equipment vendors can now review your profile."
                ),
            )
            return {"status": "success", "event": "graph_resumed_and_published"}

        return {"status": "ignored", "reason": "No pending approval state matched"}

    # =========================================================================
    # SCENARIO 2: DOCUMENT / IMAGE UPLOAD (Initiate Green Audit)
    # =========================================================================
    if msg_type in ["document", "image"]:
        # 1. Download raw file bytes using Whapi's authenticated channel
        downloaded_doc = whapi_client.process_webhook(payload)
        if not downloaded_doc:
            logger.error("WhapiClient failed to extract or download file bytes.")
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"status": "error", "message": "Unable to retrieve document payload"},
            )

        send_whatsapp_message(
            to_number=sender_number,
            body_text="📄 *Document Received.* Ingesting file and performing deterministic green audit...",
        )

        try:
            # 2. Resolve or initialize the client's SME record
            sme_id = supabase_service.get_or_create_sme(
                identifier=sender_number,
                channel="WHATSAPP",
            )

            # 3. Store raw bytes in the client-specific bucket directory
            # Path format: {sme_id}/{uuid}/{filename}
            storage_path, public_url = supabase_service.upload_document(
                sme_id=sme_id,
                filename=downloaded_doc.filename,
                file_bytes=downloaded_doc.file_bytes,
            )

            # 4. Register document row in PostgREST tracking table
            doc_id = supabase_service.register_incoming_document(
                sme_id=sme_id,
                storage_path=storage_path,
                channel="WHATSAPP",
            )

            # 5. Record activity in the Orbyte Activity Audit Log
            supabase_service.log_audit_event(
                sme_id=sme_id,
                action_type="DOCUMENT_INGESTED",
                actor_role="SME_OWNER",
                metadata={
                    "document_id": doc_id,
                    "filename": downloaded_doc.filename,
                    "storage_path": storage_path,
                    "sender_number": sender_number,
                },
            )

        except (DatabaseOperationError, StorageOperationError) as exc:
            logger.error("Supabase ingestion pipeline failed: %s", exc)
            send_whatsapp_message(
                to_number=sender_number,
                body_text="⚠️ System error storing your document. Please try again shortly.",
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": "error", "message": str(exc)},
            )

        # 6. Initialize LangGraph State with the public Supabase URL
        # Node 1 (extract_data) can now read the document via standard HTTP
        initial_state = {
            "sme_id": sme_id,
            "document_id": doc_id,
            "document_url": public_url,
            "filename": downloaded_doc.filename,
            "human_approved": False,
        }

        logger.info("Executing LangGraph workflow for SME: %s", sme_id)
        execution_state = greenready_graph.invoke(initial_state, thread_config)

        # 7. Extract calculated metrics from the interrupted state snapshot
        audit_metrics = execution_state.get("audit_metrics", {})
        savings = audit_metrics.get("projected_annual_savings_myr", 0.0)
        co2e = audit_metrics.get("annual_tco2e_avoided", 0.0)
        payback = audit_metrics.get("payback_period_years", "N/A")

        # 8. Dispatch Human-in-the-Loop decision prompt via WhatsApp
        prompt_message = (
            "📊 *Audit Analysis Completed*\n\n"
            f"• *Projected Savings:* RM {savings:,.2f} / year\n"
            f"• *Carbon Avoided:* {co2e:,.2f} tCO2e / year\n"
            f"• *Est. Payback:* {payback} years\n\n"
            "Reply *YES* to approve publishing your verified green dossier to the Orbyte Deal Board."
        )
        send_whatsapp_message(to_number=sender_number, body_text=prompt_message)

        return {"status": "success", "event": "workflow_halted_awaiting_approval"}

    return {"status": "ignored", "reason": f"Unsupported message type: {msg_type}"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
