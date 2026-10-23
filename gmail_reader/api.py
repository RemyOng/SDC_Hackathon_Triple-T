from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .client import configured_service, list_messages
from .reader import read_gmail_messages
from .persistence import persist_gmail_message
from workflow.validation_subgraph import build_validation_subgraph

POLL_SECONDS = 10
PROCESSED_FILE = Path(os.getenv("GMAIL_PROCESSED_FILE", "processed_email_ids.json"))


class GmailPoller:
    def __init__(self) -> None:
        self.validation_graph = build_validation_subgraph()
        self.processed_ids = self._load_processed_ids()
        self.latest_messages: list[dict[str, Any]] = []
        self.last_error: str | None = None
        self.task: asyncio.Task[None] | None = None
        self.primed = bool(self.processed_ids)

    def _load_processed_ids(self) -> set[str]:
        if not PROCESSED_FILE.exists():
            return set()
        return set(json.loads(PROCESSED_FILE.read_text(encoding="utf-8")))

    def _save_processed_ids(self) -> None:
        PROCESSED_FILE.write_text(
            json.dumps(sorted(self.processed_ids), indent=2), encoding="utf-8"
        )

    async def poll_once(self) -> list[dict[str, Any]]:
        service = await asyncio.to_thread(configured_service)
        message_refs = await asyncio.to_thread(
            list_messages,
            service,
            os.getenv("GMAIL_QUERY", "in:anywhere"),
            int(os.getenv("GMAIL_MAX_RESULTS", "25")),
        )
        if not self.primed:
            self.processed_ids.update(item["id"] for item in message_refs)
            self._save_processed_ids()
            self.primed = True
            return []
        new_refs = [item for item in message_refs if item["id"] not in self.processed_ids]
        if not new_refs:
            return []
        fetched_messages = await read_gmail_messages(
            os.getenv("GMAIL_QUERY", "in:anywhere"),
            int(os.getenv("GMAIL_MAX_RESULTS", "25")),
            service,
        )
        new_ids = {item["id"] for item in new_refs}
        fetched_messages = [
            message for message in fetched_messages if message["message_id"] in new_ids
        ]
        messages = []
        for message in fetched_messages:
            result = await self.validation_graph.ainvoke({"email": message})
            validation = result["validation"]
            document_ids = await asyncio.to_thread(
                persist_gmail_message,
                message,
                validation,
            )
            messages.append({
                **message,
                "validation": validation,
                "document_ids": document_ids,
            })
        self.processed_ids.update(item["id"] for item in new_refs)
        self._save_processed_ids()
        self.latest_messages = messages
        return messages

    async def run(self) -> None:
        while True:
            checked_at = datetime.now(timezone.utc).isoformat()
            print(f"[{checked_at}] Checking Gmail for new emails...", flush=True)
            try:
                messages = await self.poll_once()
                self.last_error = None
                if messages:
                    print(
                        json.dumps(
                            {
                                "new_email_count": len(messages),
                                "emails": _json_messages(messages),
                            },
                            indent=2,
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                else:
                    print("No new emails found.", flush=True)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.last_error = str(error)
                print(f"Gmail check failed: {error}", flush=True)
            await asyncio.sleep(POLL_SECONDS)


poller = GmailPoller()


def _json_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for message in messages:
        item = dict(message)
        item["attachments"] = [
            {
                key: value
                for key, value in attachment.items()
                if key != "content"
            }
            | {"content_size": len(attachment["content"])}
            for attachment in message.get("attachments", [])
        ]
        output.append(item)
    return output


@asynccontextmanager
async def lifespan(_: FastAPI):
    poller.task = asyncio.create_task(poller.run())
    try:
        yield
    finally:
        if poller.task:
            poller.task.cancel()
            try:
                await poller.task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="Gmail TNB Bill Reader", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "poll_seconds": POLL_SECONDS, "last_error": poller.last_error}


@app.get("/emails")
def emails() -> dict[str, Any]:
    return {"count": len(poller.latest_messages), "emails": _json_messages(poller.latest_messages)}


@app.post("/check-now")
async def check_now() -> dict[str, Any]:
    messages = await poller.poll_once()
    return {"new_email_count": len(messages), "emails": _json_messages(messages)}
