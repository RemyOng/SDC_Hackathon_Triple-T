"""Run the Gmail reader FastAPI service from the project root."""

import uvicorn


def main() -> None:
    uvicorn.run("gmail_reader.api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
