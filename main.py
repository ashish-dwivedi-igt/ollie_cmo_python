import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from Orchestrator.api import router as chat_router
app = FastAPI(
    title="CMO Agent API",
    description="Agent API with Meta advertising tools",
    version="0.1.0",
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


app.include_router(chat_router)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    """Serve the chatbot frontend."""
    return FileResponse(STATIC_DIR / "index.html")


def main() -> None:
    """Start the uvicorn server."""
    uvicorn.run(
        app,
        host="localhost",
        port=8000,
    )


if __name__ == "__main__":
    main()
