from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print

from .agents import run_incident
from .config import SETTINGS
from .rag import build_vectorstore

app = typer.Typer(help="Agentic Ops CLI")


@app.command()
def ingest() -> None:
    """Ingest kb/ into the local Chroma vector store."""
    build_vectorstore()
    print(f"Ingested KB into {SETTINGS.faiss_dir}")


@app.command()
def triage(alert: str, logs: str) -> None:
    """Run a single incident triage."""
    result = run_incident(alert=alert, logs=logs)
    print(json.dumps({
        "root_cause": result.diagnosis,
        "action": result.action,
        "runbook_update": result.runbook_update,
    }, indent=2))


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run FastAPI server."""
    import uvicorn

    uvicorn.run("agentic_ops.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
