"""FastAPI entry-point exposing orchestrator controls."""
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router as agents_router
from app.runtime import get_orchestrator

app = FastAPI(title="Agentic Orchestrator PoC")
app.include_router(agents_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.on_event("shutdown")
async def shutdown() -> None:
    orchestrator = get_orchestrator()
    await orchestrator.terminate_all()
