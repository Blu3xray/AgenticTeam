"""FastAPI entry-point exposing orchestrator controls."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router as agents_router
from app.api.sessions import router as sessions_router
from app.api.chat import router as chat_router
from app.runtime import get_orchestrator, initialize_orchestrator_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application."""
    # Startup: Create the orchestrator agent
    await initialize_orchestrator_agent()
    yield
    # Shutdown: Terminate all agents
    orchestrator = get_orchestrator()
    await orchestrator.terminate_all()


app = FastAPI(title="Agentic Orchestrator", lifespan=lifespan)
app.include_router(agents_router)
app.include_router(sessions_router)
app.include_router(chat_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
