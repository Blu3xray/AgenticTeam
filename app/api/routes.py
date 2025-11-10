"""HTTP API exposing orchestrator capabilities."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.models import AgentConfig, AgentDescriptor
from app.orchestration.orchestrator import Orchestrator
from app.runtime import get_orchestrator

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentCreateRequest(BaseModel):
    name: str = Field(..., description="Logical agent name")
    role: str = Field(..., description="Catalog role to instantiate")
    mcp_server: str = Field(..., description="Name of the MCP server to bind")
    metadata: dict = Field(default_factory=dict)


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    role: str
    state: str
    task_count: int
    last_error: Optional[str]

    @classmethod
    def from_descriptor(cls, descriptor: AgentDescriptor) -> "AgentResponse":
        return cls(
            agent_id=descriptor.agent_id,
            name=descriptor.config.name,
            role=descriptor.config.role,
            state=descriptor.state.name,
            task_count=descriptor.task_count,
            last_error=descriptor.last_error,
        )


class MessageRequest(BaseModel):
    sender_id: str = Field(..., description="Identifier of the sender")
    payload: dict = Field(default_factory=dict)


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: AgentCreateRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> AgentResponse:
    try:
        config = AgentConfig(
            name=request.name,
            role=request.role,
            mcp_server=request.mcp_server,
            metadata=request.metadata,
        )
        descriptor = await orchestrator.spawn_agent(config=config)
    except KeyError as exc:
        detail = exc.args[0] if exc.args else str(exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
    return AgentResponse.from_descriptor(descriptor)


@router.get("", response_model=List[AgentResponse])
async def list_agents(orchestrator: Orchestrator = Depends(get_orchestrator)) -> List[AgentResponse]:
    return [AgentResponse.from_descriptor(desc) for desc in orchestrator.list_agents()]


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, orchestrator: Orchestrator = Depends(get_orchestrator)) -> None:
    await orchestrator.terminate_agent(agent_id)


@router.post("/{agent_id}/messages", status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    agent_id: str,
    request: MessageRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> None:
    if orchestrator.get_agent(agent_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")
    await orchestrator.dispatch(
        sender_id=request.sender_id,
        recipient_id=agent_id,
        payload=request.payload,
    )
