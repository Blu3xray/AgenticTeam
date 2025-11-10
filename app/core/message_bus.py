"""Lightweight in-memory bus implementing A2A message delivery."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Optional

from .models import A2AMessage


class A2AMessageBus:
    """Async message hub enabling agent-to-agent communication."""

    def __init__(self) -> None:
        self._mailboxes: Dict[str, asyncio.Queue[A2AMessage]] = defaultdict(asyncio.Queue)
        self._lock = asyncio.Lock()

    async def register(self, agent_id: str) -> None:
        """Ensure a mailbox exists for the agent."""
        async with self._lock:
            # Accessing the defaultdict creates the queue.
            _ = self._mailboxes[agent_id]

    async def unregister(self, agent_id: str) -> None:
        """Remove the mailbox to stop further deliveries."""
        async with self._lock:
            self._mailboxes.pop(agent_id, None)

    async def send(self, message: A2AMessage) -> None:
        """Send a message to the intended recipient or broadcast if recipient not set."""
        if message.recipient_id:
            queue = self._mailboxes.get(message.recipient_id)
            if queue:
                await queue.put(message)
            return

        # Broadcast to all registered mailboxes except the sender.
        for agent_id, queue in list(self._mailboxes.items()):
            if agent_id == message.sender_id:
                continue
            await queue.put(message)

    @asynccontextmanager
    async def deliver(self, agent_id: str) -> AsyncIterator[asyncio.Queue[A2AMessage]]:
        """Context manager yielding the agent's mailbox queue."""
        await self.register(agent_id)
        try:
            yield self._mailboxes[agent_id]
        finally:
            await self.unregister(agent_id)
