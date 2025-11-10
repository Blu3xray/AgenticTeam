"""Simple agent implementation used in the proof-of-concept."""
from __future__ import annotations

import asyncio
import random
from typing import Dict

from app.agents.base import Agent
from app.core.models import A2AMessage, AgentState


class EchoAgent(Agent):
    """Agent that echoes incoming messages to demonstrate lifecycle control."""

    async def handle_message(self, message: A2AMessage) -> None:
        await asyncio.sleep(random.uniform(0.05, 0.2))  # Simulate work
        reply_payload: Dict[str, str] = {
            "echo": f"{self.config.name} heard {message.payload.get('content', '')}",
        }
        reply = A2AMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            payload=reply_payload,
            correlation_id=message.correlation_id,
        )
        await self.send(reply)

    async def on_start(self) -> None:
        self.descriptor.state = AgentState.RUNNING

    async def on_stop(self) -> None:
        self.descriptor.state = AgentState.STOPPED
