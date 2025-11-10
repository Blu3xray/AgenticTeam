"""Application runtime composition helpers."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from app.agents.echo import EchoAgent
from app.agents.llm_agent import LLMAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.config import config
from app.core.message_bus import A2AMessageBus
from app.core.models import AgentConfig, AgentDescriptor
from app.orchestration.orchestrator import Orchestrator
from app.services.llm_pool import LLMPool
from app.services.mcp import MCPRegistry, MCPServer

_AGENT_CATALOG = {
    "echo": EchoAgent,
    "llm": LLMAgent,
}

# Global orchestrator agent ID (created on startup)
_ORCHESTRATOR_AGENT_ID: Optional[str] = None


@lru_cache
def get_bus() -> A2AMessageBus:
    return A2AMessageBus()


@lru_cache
def get_mcp_registry() -> MCPRegistry:
    registry = MCPRegistry()
    registry.register("echo", MCPServer(name="echo-mcp", endpoint="mock://echo"))
    return registry


@lru_cache
def get_llm_pool() -> LLMPool:
    pool = LLMPool()

    # Register Azure OpenAI if configured
    if config.azure_openai:
        pool.register_azure_openai("gpt-4", config.azure_openai)
        pool.register_azure_openai(
            "gpt-35-turbo",
            config.azure_openai,
        )

    return pool


@lru_cache
def get_orchestrator() -> Orchestrator:
    orchestrator = Orchestrator(
        bus=get_bus(),
        mcp_registry=get_mcp_registry(),
        agent_catalog=_AGENT_CATALOG,
    )
    # Wire LLM pool
    orchestrator.set_llm_pool(get_llm_pool())
    return orchestrator


async def initialize_orchestrator_agent() -> AgentDescriptor:
    """Create the meta-orchestrator agent on application startup."""
    global _ORCHESTRATOR_AGENT_ID

    orchestrator = get_orchestrator()
    llm_pool = get_llm_pool()
    bus = get_bus()

    # Create orchestrator agent manually (special case)
    config = AgentConfig(
        name="orchestrator",
        role="orchestrator",
        mcp_server="echo",
        metadata={"model": "gpt-4"},
    )

    descriptor = AgentDescriptor(
        agent_id="orchestrator-agent",
        config=config,
    )

    agent = OrchestratorAgent(
        descriptor=descriptor,
        bus=bus,
        orchestrator=orchestrator,
        llm_pool=llm_pool,
    )

    await agent.start()

    # Store reference
    orchestrator._agents[descriptor.agent_id] = agent
    _ORCHESTRATOR_AGENT_ID = descriptor.agent_id

    return descriptor


def get_orchestrator_agent_id() -> str:
    """Get the ID of the global orchestrator agent."""
    if _ORCHESTRATOR_AGENT_ID is None:
        raise RuntimeError("Orchestrator agent not initialized. Call initialize_orchestrator_agent() first.")
    return _ORCHESTRATOR_AGENT_ID


def default_agent_config(name: str) -> AgentConfig:
    return AgentConfig(name=name, role="echo", mcp_server="echo")
