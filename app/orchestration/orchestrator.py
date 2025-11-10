"""Orchestrator responsible for provisioning and supervising agents."""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, Iterable, Optional, Type

from app.agents.base import Agent
from app.core.message_bus import A2AMessageBus
from app.core.models import A2AMessage, AgentConfig, AgentDescriptor, AgentState
from app.services.mcp import MCPRegistry


class Orchestrator:
    """Coordinate agent lifecycle and mediate access to MCP servers."""

    def __init__(
        self,
        *,
        bus: A2AMessageBus,
        mcp_registry: MCPRegistry,
        agent_catalog: Dict[str, Type[Agent]],
    ) -> None:
        self._bus = bus
        self._mcp_registry = mcp_registry
        self._agent_catalog = agent_catalog
        self._agents: Dict[str, Agent] = {}
        self._lock = asyncio.Lock()
        self._llm_pool: Optional[Any] = None  # Lazy loaded

    def set_llm_pool(self, llm_pool: Any) -> None:
        """Set the LLM pool for agents that need it."""
        self._llm_pool = llm_pool

    async def spawn_agent(self, config: AgentConfig) -> AgentDescriptor:
        """Create and start an agent based on the provided configuration."""
        agent_cls = self._resolve_agent_class(config.role)
        # Validate MCP server availability before provisioning the agent.
        self._mcp_registry.get(config.mcp_server)
        descriptor = AgentDescriptor(
            agent_id=str(uuid.uuid4()),
            config=config,
            state=AgentState.SPAWNING,
        )

        # Pass LLM pool to agents that need it
        if self._llm_pool and hasattr(agent_cls, "__init__"):
            import inspect

            sig = inspect.signature(agent_cls.__init__)
            if "llm_pool" in sig.parameters:
                agent = agent_cls(descriptor, self._bus, self._llm_pool)
            else:
                agent = agent_cls(descriptor, self._bus)
        else:
            agent = agent_cls(descriptor, self._bus)

        async with self._lock:
            self._agents[descriptor.agent_id] = agent
        await agent.start()
        return descriptor

    async def terminate_agent(self, agent_id: str) -> None:
        """Stop and remove an agent from the orchestrator."""
        async with self._lock:
            agent = self._agents.pop(agent_id, None)
        if agent is None:
            return
        await agent.stop()

    async def terminate_all(self) -> None:
        """Shutdown every agent currently managed by the orchestrator."""
        async with self._lock:
            agents = list(self._agents.values())
            self._agents.clear()
        await asyncio.gather(*(agent.stop() for agent in agents), return_exceptions=True)

    def list_agents(self) -> Iterable[AgentDescriptor]:
        return (agent.descriptor for agent in self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[AgentDescriptor]:
        agent = self._agents.get(agent_id)
        return agent.descriptor if agent else None

    def list_agents_by_session(self, session_id: str) -> Iterable[AgentDescriptor]:
        """Return agents belonging to a specific session."""
        return (
            agent.descriptor
            for agent in self._agents.values()
            if agent.descriptor.config.metadata.get("session_id") == session_id
        )

    async def terminate_session(self, session_id: str) -> None:
        """Terminate all agents for a given session."""
        async with self._lock:
            session_agents = [
                (agent_id, agent)
                for agent_id, agent in self._agents.items()
                if agent.descriptor.config.metadata.get("session_id") == session_id
            ]
            for agent_id, _ in session_agents:
                self._agents.pop(agent_id)

        # Stop agents outside the lock to avoid blocking
        await asyncio.gather(
            *(agent.stop() for _, agent in session_agents), return_exceptions=True
        )

    async def dispatch(self, sender_id: str, recipient_id: Optional[str], payload: dict) -> None:
        """Send an A2A message on behalf of a caller."""
        message = A2AMessage(sender_id=sender_id, recipient_id=recipient_id, payload=payload)
        await self._bus.send(message)

    def resolve_mcp(self, capability: str):
        """Expose MCP registry to agents or callers."""
        return self._mcp_registry.get(capability)

    def _resolve_agent_class(self, role: str) -> Type[Agent]:
        if role not in self._agent_catalog:
            raise KeyError(f"No agent registered for role '{role}'")
        return self._agent_catalog[role]
