"""Shared primitives with no marketplace imports, so any module can use them."""

from datetime import datetime, timedelta, timezone
from typing import Optional

MYT = timezone(timedelta(hours=8))


class BoardError(Exception):
    """A rule blocked the action. `status` maps to the HTTP status code."""

    def __init__(self, message: str, status: int = 400, rule: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.rule = rule


def now() -> datetime:
    return datetime.now(MYT)
