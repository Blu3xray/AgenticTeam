"""LLM-powered agent that processes messages using language models."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.agents.base import Agent
from app.core.models import A2AMessage

if TYPE_CHECKING:
    from app.core.message_bus import A2AMessageBus
    from app.core.models import AgentDescriptor
    from app.services.llm_pool import LLMPool


class LLMAgent(Agent):
    """Agent that uses LLM to generate responses to incoming messages."""

    def __init__(
        self,
        descriptor: AgentDescriptor,
        bus: A2AMessageBus,
        llm_pool: LLMPool,
    ) -> None:
        super().__init__(descriptor, bus)
        self._llm_pool = llm_pool
        self.model_name = descriptor.config.metadata.get("model", "gpt-4")
        self.system_prompt = descriptor.config.metadata.get(
            "system_prompt",
            "You are a helpful AI assistant agent in a multi-agent system.",
        )
        self.temperature = float(descriptor.config.metadata.get("temperature", 0.7))

    async def handle_message(self, message: A2AMessage) -> None:
        """Process message using LLM and send response."""
        user_prompt = message.payload.get("prompt") or message.payload.get("content")

        if not user_prompt:
            # No prompt to process
            return

        try:
            async with self._llm_pool.acquire(self.model_name) as client:
                response = await client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.temperature,
                )

                assistant_message = response.choices[0].message.content

                # Send response back to sender
                reply = A2AMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    payload={
                        "response": assistant_message,
                        "model": self.model_name,
                        "agent_name": self.config.name,
                    },
                    correlation_id=message.correlation_id,
                )
                await self.send(reply)

        except Exception as exc:  # noqa: BLE001
            # Log error and send error response
            error_reply = A2AMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                payload={
                    "error": str(exc),
                    "agent_name": self.config.name,
                },
                correlation_id=message.correlation_id,
            )
            await self.send(error_reply)

    async def on_start(self) -> None:
        """Log agent startup."""
        return None

    async def on_stop(self) -> None:
        """Cleanup on shutdown."""
        return None
