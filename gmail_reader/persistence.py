from __future__ import annotations

import logging
from typing import Any

from db.db_manager import SupabaseService
from services.document_processor import process_bytes_to_base64
from services.runpod_client import RunPodVLMClient
from .models import GmailMessage

logger = logging.getLogger(__name__)
EXTRACTED_DOCUMENT_FIELDS = (
    "document_type",
    "account_number",
    "company_name",
    "baseline_kwh",
    "target_capex_myr",
    "equipment_type",
)


def _document_type(validation: dict[str, Any], result: dict[str, Any]) -> str:
    if validation.get("email_is_spam", False):
        return "SPAM"
    if validation.get("is_tnb_bill", False) and result.get("content_legitimate", False):
        return "TNB_BILL"
    return "UNKNOWN"


def _extracted_json(
    attachment: dict[str, Any],
    document_type: str,
    runpod: RunPodVLMClient | None,
) -> dict[str, Any]:
    if document_type == "TNB_BILL":
        if runpod is None:
            raise ValueError("RunPod client is required for validated Gmail TNB bills.")
        extracted = runpod.extract_document_metrics(
            process_bytes_to_base64(attachment["content"], attachment["filename"])
        ).model_dump()
        extracted["document_type"] = document_type
        return extracted

    return {field: document_type if field == "document_type" else None for field in EXTRACTED_DOCUMENT_FIELDS}


def persist_gmail_message(
    message: GmailMessage,
    validation: dict[str, Any],
    supabase: SupabaseService | None = None,
    runpod: RunPodVLMClient | None = None,
) -> list[str]:
    """Persist every Gmail attachment using the same document tables as WhatsApp."""
    attachments = message["attachments"]
    if not attachments:
        return []
    service = supabase or SupabaseService()

    sme_id = service.get_or_create_sme(
        identifier=message["from_email"],
        channel="GMAIL",
    )
    document_ids: list[str] = []
    attachment_results = validation.get("attachment_results", [])
    extractor = runpod

    for index, attachment in enumerate(attachments):
        if not attachment["content"]:
            logger.warning(
                "Skipping empty Gmail attachment for message %s: %s",
                message["message_id"],
                attachment["filename"],
            )
            continue
        storage_path, _ = service.upload_document(
            sme_id=sme_id,
            filename=attachment["filename"],
            file_bytes=attachment["content"],
        )
        document_id = service.register_incoming_document(
            sme_id=sme_id,
            storage_path=storage_path,
            channel="GMAIL",
        )
        result = attachment_results[index] if index < len(attachment_results) else {}
        document_type = _document_type(validation, result)
        if document_type == "TNB_BILL":
            extractor = extractor or RunPodVLMClient()
        service.update_document_results(
            document_id=document_id,
            extracted_json=_extracted_json(attachment, document_type, extractor),
            doc_type=document_type,
            status="NEEDS_HUMAN" if not result.get("content_legitimate", False) else "COMPLETED",
        )
        service.log_audit_event(
            sme_id=sme_id,
            action_type="DOCUMENT_INGESTED",
            metadata={
                "document_id": document_id,
                "channel": "GMAIL",
                "message_id": message["message_id"],
                "filename": attachment["filename"],
                "storage_path": storage_path,
            },
        )
        document_ids.append(document_id)

    return document_ids
