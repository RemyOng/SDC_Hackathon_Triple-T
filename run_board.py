"""Run only the GreenReady Opportunity Board (no Supabase, RunPod or Gmail needed).

    python run_board.py          -> http://localhost:8001/app
"""

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from marketplace import mount_frontend, register

app = FastAPI(title="Orbyte GreenReady Opportunity Board")
register(app)
mount_frontend(app)


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse("/app")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
