from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from .agents import run_incident

app = FastAPI(title="Agentic Ops")


class TriageRequest(BaseModel):
    alert: str
    logs: str


class TriageResponse(BaseModel):
    root_cause: str
    action: str
    runbook_update: str


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/triage", response_model=TriageResponse)
async def triage(request: TriageRequest) -> TriageResponse:
    result = run_incident(alert=request.alert, logs=request.logs)
    return TriageResponse(
        root_cause=result.diagnosis,
        action=result.action,
        runbook_update=result.runbook_update,
    )
