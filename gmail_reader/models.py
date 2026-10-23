from __future__ import annotations

from typing import TypedDict


class GmailAttachment(TypedDict):
    filename: str
    mime_type: str
    content: bytes
    base64_valid: bool
    decode_error: str | None


class GmailMessage(TypedDict):
    message_id: str
    thread_id: str
    from_name: str
    from_email: str
    subject: str
    received_at: str
    body: str
    attachments: list[GmailAttachment]
