from __future__ import annotations

from typing import TypedDict

from gmail_reader.models import GmailMessage


class AttachmentValidation(TypedDict):
    filename: str
    corrupted: bool
    corruption_reasons: list[str]
    supported_document: bool
    document_type: str
    content_legitimate: bool


class ValidationResult(TypedDict):
    attachment_results: list[AttachmentValidation]
    email_is_spam: bool
    spam_reasons: list[str]
    is_tnb_bill: bool


class ValidationState(TypedDict, total=False):
    email: GmailMessage
    attachment_results: list[AttachmentValidation]
    email_is_spam: bool
    spam_reasons: list[str]
    is_tnb_bill: bool
    validation: ValidationResult
