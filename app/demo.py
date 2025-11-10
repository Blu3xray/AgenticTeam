"""CLI demonstration of orchestrator-managed agent lifecycle."""
from __future__ import annotations

import asyncio
from typing import NoReturn

from app.core.message_bus import A2AMessageBus
from app.core.models import A2AMessage, AgentConfig
from app.orchestration.orchestrator import Orchestrator
from app.runtime import get_mcp_registry
from app.agents.echo import EchoAgent


async def main() -> None:
    bus = A2AMessageBus()
    orchestrator = Orchestrator(
        bus=bus,
        mcp_registry=get_mcp_registry(),
        agent_catalog={"echo": EchoAgent},
    )

    agent_descriptor = await orchestrator.spawn_agent(
        AgentConfig(name="demo-echo", role="echo", mcp_server="echo"),
    )
    print(f"Spawned agent {agent_descriptor.agent_id} in state {agent_descriptor.state.name}")

    async with bus.deliver("demo-client") as inbox:
        await bus.send(
            A2AMessage(
                sender_id="demo-client",
                recipient_id=agent_descriptor.agent_id,
                payload={"content": "Hello agent"},
            )
        )
        response = await asyncio.wait_for(inbox.get(), timeout=2)
        print(f"Received response from {response.sender_id}: {response.payload}")

    await orchestrator.terminate_agent(agent_descriptor.agent_id)
    print("Agent terminated")


def run() -> NoReturn:
    asyncio.run(main())


if __name__ == "__main__":
    run()
