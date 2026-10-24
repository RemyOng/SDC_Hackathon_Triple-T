from __future__ import annotations

import asyncio
import os

from googleapiclient.discovery import Resource

from .client import configured_service, read_messages
from .models import GmailMessage


async def read_gmail_messages(
    query: str | None = None,
    max_results: int | None = None,
    service: Resource | None = None,
) -> list[GmailMessage]:
    """Read Gmail messages without wrapping Gmail access in a LangGraph."""
    gmail_service = service or await asyncio.to_thread(configured_service)
    return await asyncio.to_thread(
        read_messages,
        gmail_service,
        query or os.getenv("GMAIL_QUERY", "in:anywhere"),
        max_results or int(os.getenv("GMAIL_MAX_RESULTS", "25")),
    )
