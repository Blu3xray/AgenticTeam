"""Session-scoped API routes for agent management."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, status

from app.api.routes import AgentCreateRequest, AgentResponse
from app.core.models import AgentConfig
from app.orchestration.orchestrator import Orchestrator
from app.runtime import get_orchestrator

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post(
    "/{session_id}/agents",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_agent(
    session_id: str,
    request: AgentCreateRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> AgentResponse:
    """Create an agent scoped to a specific session."""
    # Inject session_id into metadata
    metadata = request.metadata.copy()
    metadata["session_id"] = session_id

    config = AgentConfig(
        name=f"{session_id}-{request.name}",
        role=request.role,
        mcp_server=request.mcp_server,
        metadata=metadata,
    )

    try:
        descriptor = await orchestrator.spawn_agent(config=config)
    except KeyError as exc:
        from fastapi import HTTPException

        detail = exc.args[0] if exc.args else str(exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc

    return AgentResponse.from_descriptor(descriptor)


@router.get("/{session_id}/agents", response_model=List[AgentResponse])
async def list_session_agents(
    session_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> List[AgentResponse]:
    """List all agents belonging to a session."""
    return [
        AgentResponse.from_descriptor(desc)
        for desc in orchestrator.list_agents_by_session(session_id)
    ]


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> None:
    """Terminate all agents for a given session."""
    await orchestrator.terminate_session(session_id)
