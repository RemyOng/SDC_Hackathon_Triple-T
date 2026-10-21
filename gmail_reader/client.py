from __future__ import annotations

import base64
import binascii
import os
from datetime import datetime, timezone
from email.utils import parseaddr
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from .models import GmailAttachment, GmailMessage

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _decode_base64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.b64decode(
        (value + padding).translate(str.maketrans("-_", "+/")),
        validate=True,
    )


def _body_from_payload(payload: dict[str, Any]) -> str:
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return _decode_base64(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        body = _body_from_payload(part)
        if body:
            return body
    return ""


def _attachment_parts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    parts = list(payload.get("parts", []))
    result: list[dict[str, Any]] = []
    while parts:
        part = parts.pop()
        result.append(part)
        parts.extend(part.get("parts", []))
    return [part for part in result if part.get("filename") and part.get("body", {}).get("attachmentId")]


def create_gmail_service(
    credentials_file: str | Path = "credentials.json",
    token_file: str | Path = "token.json",
) -> Resource:
    credentials_path = Path(credentials_file)
    token_path = Path(token_file)
    credentials: Credentials | None = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"Gmail OAuth credentials were not found: {credentials_path}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            credentials = flow.run_local_server(port=0)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=credentials)


def list_messages(service: Resource, query: str, max_results: int) -> list[dict[str, str]]:
    response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    return response.get("messages", [])


def get_message(service: Resource, message_id: str) -> GmailMessage:
    raw = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = raw.get("payload", {})
    headers = {header["name"].lower(): header["value"] for header in payload.get("headers", [])}
    from_name, from_email = parseaddr(headers.get("from", ""))
    received_at = datetime.fromtimestamp(
        int(raw.get("internalDate", "0")) / 1000, tz=timezone.utc
    ).isoformat()
    attachments: list[GmailAttachment] = []
    for part in _attachment_parts(payload):
        attachment = (
            service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=part["body"]["attachmentId"])
            .execute()
        )
        try:
            content = _decode_base64(attachment.get("data", ""))
            base64_valid = True
            decode_error = None
        except (binascii.Error, ValueError, TypeError) as error:
            content = b""
            base64_valid = False
            decode_error = str(error) or "invalid_base64_data"
        attachments.append({
            "filename": part["filename"],
            "mime_type": part.get("mimeType", "application/octet-stream"),
            "content": content,
            "base64_valid": base64_valid,
            "decode_error": decode_error,
        })
    return {
        "message_id": message_id,
        "thread_id": raw.get("threadId", ""),
        "from_name": from_name,
        "from_email": from_email,
        "subject": headers.get("subject", ""),
        "received_at": received_at,
        "body": _body_from_payload(payload),
        "attachments": attachments,
    }


def read_messages(
    service: Resource,
    query: str = "category:primary is:unread",
    max_results: int = 5,
) -> list[GmailMessage]:
    return [get_message(service, item["id"]) for item in list_messages(service, query, max_results)]


def configured_service() -> Resource:
    return create_gmail_service(
        credentials_file=os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json"),
        token_file=os.getenv("GMAIL_TOKEN_FILE", "token.json"),
    )
