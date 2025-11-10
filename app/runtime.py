"""Application runtime composition helpers."""
from __future__ import annotations

from functools import lru_cache

from app.agents.echo import EchoAgent
from app.core.message_bus import A2AMessageBus
from app.core.models import AgentConfig
from app.orchestration.orchestrator import Orchestrator
from app.services.mcp import MCPRegistry, MCPServer

_AGENT_CATALOG = {
    "echo": EchoAgent,
}


@lru_cache
def get_bus() -> A2AMessageBus:
    return A2AMessageBus()


@lru_cache
def get_mcp_registry() -> MCPRegistry:
    registry = MCPRegistry()
    registry.register("echo", MCPServer(name="echo-mcp", endpoint="mock://echo"))
    return registry


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator(
        bus=get_bus(),
        mcp_registry=get_mcp_registry(),
        agent_catalog=_AGENT_CATALOG,
    )


def default_agent_config(name: str) -> AgentConfig:
    return AgentConfig(name=name, role="echo", mcp_server="echo")
