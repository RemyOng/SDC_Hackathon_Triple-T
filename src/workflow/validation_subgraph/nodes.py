from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

from gmail_reader.models import GmailAttachment

from .state import AttachmentValidation, ValidationState

SUPPORTED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "doc", "xls", "docx", "xlsx", "txt", "csv",
}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
PHISHING_TERMS = {
    "verify your account", "confirm your account", "urgent action", "click here",
    "password", "suspended", "wire transfer", "gift card",
}
TNB_TERMS = {"tnb", "tenaga nasional", "electricity bill", "utility bill", "billing"}


def _extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def _corruption_reasons(attachment: GmailAttachment) -> list[str]:
    extension = _extension(attachment["filename"])
    content = attachment["content"]
    reasons: list[str] = []
    if not attachment["base64_valid"]:
        reasons.append("invalid_gmail_base64")
    if not content:
        reasons.append("zero_byte_file")
    if extension not in SUPPORTED_EXTENSIONS:
        reasons.append("unsupported_or_missing_extension")
        return reasons
    try:
        if extension == "pdf" and (
            not content.startswith(b"%PDF-") or b"%%EOF" not in content[-1024:]
        ):
            reasons.append("malformed_pdf")
        elif extension == "png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            reasons.append("malformed_png")
        elif extension in {"jpg", "jpeg"} and (
            not content.startswith(b"\xff\xd8\xff") or not content.endswith(b"\xff\xd9")
        ):
            reasons.append("malformed_jpeg")
        elif extension in {"doc", "xls"} and not content.startswith(
            b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        ):
            reasons.append(f"malformed_{extension}")
        elif extension in {"docx", "xlsx"}:
            required_member = "word/document.xml" if extension == "docx" else "xl/workbook.xml"
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if archive.testzip() is not None or required_member not in archive.namelist():
                    reasons.append(f"malformed_{extension}")
        elif extension in {"txt", "csv"}:
            content.decode("utf-8")
    except (UnicodeDecodeError, zipfile.BadZipFile, OSError, ValueError):
        reasons.append(
            "invalid_utf8_text" if extension in {"txt", "csv"} else f"malformed_{extension}"
        )
    return reasons


async def check_corrupted_attachments(state: ValidationState) -> ValidationState:
    results: list[AttachmentValidation] = []
    for attachment in state["email"]["attachments"]:
        extension = _extension(attachment["filename"])
        reasons = _corruption_reasons(attachment)
        results.append({
            "filename": attachment["filename"],
            "corrupted": bool(reasons),
            "corruption_reasons": reasons,
            "supported_document": extension in SUPPORTED_EXTENSIONS,
            "document_type": extension or "unknown",
            "content_legitimate": True,
        })
    return {"attachment_results": results}


async def check_attachment_format(state: ValidationState) -> ValidationState:
    results = []
    for result in state.get("attachment_results", []):
        updated = dict(result)
        updated["supported_document"] = updated["document_type"] in (IMAGE_EXTENSIONS | {"pdf"})
        results.append(updated)
    return {"attachment_results": results}


async def check_content_legitimacy(state: ValidationState) -> ValidationState:
    email = state["email"]
    text = f"{email['subject']} {email['body']}".lower()
    spam_reasons = [f"contains '{term}'" for term in PHISHING_TERMS if term in text]
    if len(re.findall(r"https?://|www\.", text)) > 2:
        spam_reasons.append("contains_multiple_links")
    is_tnb_bill = any(term in text for term in TNB_TERMS)
    results = []
    for result in state.get("attachment_results", []):
        updated = dict(result)
        updated["content_legitimate"] = not spam_reasons and is_tnb_bill
        results.append(updated)
    return {
        "attachment_results": results,
        "email_is_spam": bool(spam_reasons),
        "spam_reasons": spam_reasons,
        "is_tnb_bill": is_tnb_bill,
    }


async def finalize_validation(state: ValidationState) -> ValidationState:
    return {
        "validation": {
            "attachment_results": state.get("attachment_results", []),
            "email_is_spam": state.get("email_is_spam", False),
            "spam_reasons": state.get("spam_reasons", []),
            "is_tnb_bill": state.get("is_tnb_bill", False),
        }
    }
