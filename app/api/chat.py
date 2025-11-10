"""Chat endpoint for natural language interaction with the orchestrator."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.message_bus import A2AMessageBus
from app.core.models import A2AMessage
from app.runtime import get_bus, get_orchestrator_agent_id

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to send to orchestrator")
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Session identifier for conversation continuity",
    )


class ChatResponse(BaseModel):
    response: str
    action: Optional[str] = None
    details: Optional[dict] = None
    session_id: str


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    bus: A2AMessageBus = Depends(get_bus),
) -> ChatResponse:
    """Send a natural language message to the orchestrator agent."""
    orchestrator_agent_id = get_orchestrator_agent_id()
    client_id = f"chat-client-{uuid.uuid4()}"

    # Send message to orchestrator agent
    message = A2AMessage(
        sender_id=client_id,
        recipient_id=orchestrator_agent_id,
        payload={
            "content": request.message,
            "session_id": request.session_id,
        },
        correlation_id=str(uuid.uuid4()),
    )

    async with bus.deliver(client_id) as inbox:
        await bus.send(message)

        # Wait for response from orchestrator agent
        import asyncio

        try:
            reply = await asyncio.wait_for(inbox.get(), timeout=30.0)
            return ChatResponse(
                response=reply.payload.get("response", "No response"),
                action=reply.payload.get("action"),
                details=reply.payload.get("details"),
                session_id=request.session_id,
            )
        except asyncio.TimeoutError:
            return ChatResponse(
                response="Request timed out. The orchestrator agent may be busy.",
                session_id=request.session_id,
            )
