from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from marketplace.api import board_error_handler, router
from marketplace.store import BoardError
from marketplace.store import store as board_store

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


def register(app: FastAPI) -> None:
    """Mount the Opportunity Board API and, when built, the GreenReady web app."""
    app.include_router(router)
    app.add_exception_handler(BoardError, board_error_handler)


def mount_frontend(app: FastAPI) -> None:
    if not FRONTEND_DIST.exists():
        return
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/app/{path:path}", include_in_schema=False)
    @app.get("/app", include_in_schema=False)
    def spa(path: str = "") -> FileResponse:
        candidate = FRONTEND_DIST / path
        if path and candidate.is_file() and FRONTEND_DIST in candidate.resolve().parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")


__all__ = ["register", "mount_frontend", "board_store"]
