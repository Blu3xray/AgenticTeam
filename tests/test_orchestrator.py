"""Minimal tests for orchestrator lifecycle management."""
from __future__ import annotations

import asyncio

import pytest

from app.agents.echo import EchoAgent
from app.core.message_bus import A2AMessageBus
from app.core.models import A2AMessage, AgentConfig
from app.orchestration.orchestrator import Orchestrator
from app.services.mcp import MCPRegistry, MCPServer


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_spawn_and_terminate_agent() -> None:
    bus = A2AMessageBus()
    registry = MCPRegistry()
    registry.register("echo", MCPServer(name="echo-mcp", endpoint="mock://echo"))
    orchestrator = Orchestrator(bus=bus, mcp_registry=registry, agent_catalog={"echo": EchoAgent})

    descriptor = await orchestrator.spawn_agent(
        AgentConfig(name="test", role="echo", mcp_server="echo"),
    )

    assert descriptor.state.name in {"SPAWNING", "RUNNING"}
    assert orchestrator.get_agent(descriptor.agent_id) is not None

    await orchestrator.terminate_agent(descriptor.agent_id)
    assert orchestrator.get_agent(descriptor.agent_id) is None


@pytest.mark.anyio
async def test_agent_handles_message_roundtrip() -> None:
    bus = A2AMessageBus()
    registry = MCPRegistry()
    registry.register("echo", MCPServer(name="echo-mcp", endpoint="mock://echo"))
    orchestrator = Orchestrator(bus=bus, mcp_registry=registry, agent_catalog={"echo": EchoAgent})

    descriptor = await orchestrator.spawn_agent(
        AgentConfig(name="test", role="echo", mcp_server="echo"),
    )

    async with bus.deliver("pytest-client") as inbox:
        await bus.send(
            A2AMessage(
                sender_id="pytest-client",
                recipient_id=descriptor.agent_id,
                payload={"content": "ping"},
            )
        )
        reply = await asyncio.wait_for(inbox.get(), timeout=2)
        assert reply.recipient_id == "pytest-client"
    assert "heard ping" in reply.payload["echo"]

    await orchestrator.terminate_agent(descriptor.agent_id)
