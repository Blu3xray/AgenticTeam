"""Base agent definition used by the orchestrator."""
from __future__ import annotations

import abc
import asyncio
from typing import Optional

from app.core.message_bus import A2AMessageBus
from app.core.models import A2AMessage, AgentConfig, AgentDescriptor, AgentState


class Agent(abc.ABC):
    """Abstract agent encapsulating lifecycle hooks and message handling."""

    def __init__(
        self,
        descriptor: AgentDescriptor,
        bus: A2AMessageBus,
    ) -> None:
        self.descriptor = descriptor
        self._bus = bus
        self._runner: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()
        self._started_event = asyncio.Event()

    @property
    def agent_id(self) -> str:
        return self.descriptor.agent_id

    @property
    def config(self) -> AgentConfig:
        return self.descriptor.config

    async def start(self) -> None:
        """Start the agent's background loop."""
        if self._runner is not None:
            return
        self._stop_event.clear()
        self._started_event.clear()
        self._runner = asyncio.create_task(self._run_safe())
        await self._started_event.wait()

    async def stop(self) -> None:
        """Signal the agent to stop and wait for completion."""
        if self._runner is None:
            return
        self.descriptor.state = AgentState.STOPPING
        self._stop_event.set()
        await self._runner
        self._runner = None

    async def _run_safe(self) -> None:
        """Wrap the main loop to handle exceptions gracefully."""
        try:
            async with self._bus.deliver(self.agent_id) as inbox:
                self.descriptor.state = AgentState.RUNNING
                self._started_event.set()
                await self.on_start()
                while not self._stop_event.is_set():
                    try:
                        message = await asyncio.wait_for(inbox.get(), timeout=0.5)
                        await self._handle_message(message)
                    except asyncio.TimeoutError:
                        await self.on_idle()
        except Exception as exc:  # noqa: BLE001
            self.descriptor.state = AgentState.FAILED
            self.descriptor.last_error = str(exc)
            self._started_event.set()
        else:
            self.descriptor.state = AgentState.STOPPED
            self._started_event.set()
        finally:
            await self.on_stop()

    async def _handle_message(self, message: A2AMessage) -> None:
        await self.handle_message(message)
        self.descriptor.task_count += 1

    async def send(self, message: A2AMessage) -> None:
        """Send a message via the shared bus."""
        await self._bus.send(message)

    @abc.abstractmethod
    async def handle_message(self, message: A2AMessage) -> None:
        """Process A2A messages coming from the bus."""

    async def on_start(self) -> None:
        """Hook executed once the agent loop begins."""
        return None

    async def on_stop(self) -> None:
        """Hook executed when the agent loop exits."""
        return None

    async def on_idle(self) -> None:
        """Hook invoked when no messages were received during the idle window."""
        return None
