from __future__ import annotations

import logging
from typing import Any

from db.db_manager import SupabaseService
from .models import GmailMessage

logger = logging.getLogger(__name__)


def persist_gmail_message(
    message: GmailMessage,
    validation: dict[str, Any],
    supabase: SupabaseService | None = None,
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
        service.update_document_results(
            document_id=document_id,
            extracted_json={
                "source": "GMAIL",
                "message_id": message["message_id"],
                "thread_id": message["thread_id"],
                "from_name": message["from_name"],
                "from_email": message["from_email"],
                "subject": message["subject"],
                "received_at": message["received_at"],
                "validation": result,
            },
            doc_type="UNKNOWN",
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
