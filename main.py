import os
import uvicorn
import requests
from fastapi import FastAPI, Request
from pydantic import BaseModel
from services.whapi_client import WhapiClient
from workflow.graph import greenready_graph

app = FastAPI(title="Orbyte GreenReady MVP")
whapi_client = WhapiClient(api_token=os.getenv("WHAPI_TOKEN", "YOUR_WHAPI_TOKEN"))


def send_whatsapp_message(to_number: str, text: str):
    """Simple helper to send messages back to the SME owner."""
    url = "https://panel.whapi.cloud/messages/text"
    headers = {
        "Authorization": f"Bearer {whapi_client.token}",
        "Content-Type": "application/json"
    }
    payload = {"typing_time": 0, "to": to_number, "body": text}
    try:
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print(f"Failed to send WhatsApp message: {e}")


@app.post("/webhook/whapi")
async def whapi_webhook(request: Request):
    """Catches all incoming WhatsApp messages and routes them to LangGraph."""
    payload = await request.json()
    messages = payload.get("messages", [])

    if not messages:
        return {"status": "ignored", "reason": "no messages"}

    msg = messages[0]
    sender_number = msg.get("chat_id", "").split("@")[0]
    msg_type = msg.get("type")

    # LangGraph uses the phone number as the persistent Thread ID
    config = {"configurable": {"thread_id": sender_number}}

    if msg_type == "text":
        text_body = msg.get("text", {}).get("body", "").strip().upper()

        # Check if the graph is currently paused waiting for this user
        state_snapshot = greenready_agent.get_state(config)

        if state_snapshot.next and text_body in ["YES", "APPROVE", "Y"]:
            # Update the state to approve the publication
            greenready_agent.update_state(
                config,
                {"human_approved": True}
            )
            # Resume the graph (routes to publish_to_marketplace)
            greenready_agent.invoke(None, config)

            send_whatsapp_message(
                sender_number,
                "*Success!* Your verified Green Dossier has been anonymously published to the Orbyte Investor Board."
            )
            return {"status": "resumed_graph"}


    elif msg_type in ["document", "image"]:
        doc = whapi_client.process_webhook(payload)

        if not doc:
            return {"status": "error", "reason": "failed to download document"}

        send_whatsapp_message(
            sender_number,
            "📄 Document received. Processing your GreenReady audit using deterministic validation..."
        )

        # Initialize the LangGraph state
        initial_state = {
            "sme_id": "resolved_in_node",  # In a full build, resolve this via Supabase first
            "document_url": msg.get(msg_type, {}).get("link"),
            "filename": doc.filename,
            "human_approved": False
        }

        # Run the graph (It will execute extraction -> math -> then pause)
        final_state = greenready_agent.invoke(initial_state, config)

        # Pull the calculated metrics to show the user
        metrics = final_state.get("audit_metrics", {})
        savings = metrics.get("projected_annual_savings_myr", 0)
        co2e = metrics.get("annual_tco2e_avoided", 0)

        # Prompt the user for the Human-in-the-Loop approval
        approval_msg = (
            f"*Audit Complete*\n\n"
            f"• Projected Savings: RM {savings}/year\n"
            f"• Carbon Offset: {co2e} tCO2e/year\n\n"
            f"Reply *YES* to anonymously publish this verified dossier to the Orbyte marketplace."
        )
        send_whatsapp_message(sender_number, approval_msg)

        return {"status": "graph_paused_for_approval"}

    return {"status": "ignored", "reason": "unhandled message type"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)