"""Meta-agent that controls the orchestrator to spawn/terminate other agents."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.agents.base import Agent
from app.core.models import A2AMessage, AgentConfig

if TYPE_CHECKING:
    from app.core.message_bus import A2AMessageBus
    from app.core.models import AgentDescriptor
    from app.orchestration.orchestrator import Orchestrator
    from app.services.llm_pool import LLMPool


class OrchestratorAgent(Agent):
    """Meta-agent that uses LLM to interpret user requests and manage other agents."""

    def __init__(
        self,
        descriptor: AgentDescriptor,
        bus: A2AMessageBus,
        orchestrator: Orchestrator,
        llm_pool: LLMPool,
    ) -> None:
        super().__init__(descriptor, bus)
        self._orchestrator = orchestrator
        self._llm_pool = llm_pool
        self.model_name = descriptor.config.metadata.get("model", "gpt-4")

    async def handle_message(self, message: A2AMessage) -> None:
        """Process incoming messages to manage agents."""
        user_request = message.payload.get("content")
        session_id = message.payload.get("session_id", "default")

        if not user_request:
            return

        try:
            # Use LLM to understand the request and decide action
            action = await self._interpret_request(user_request, session_id)

            # Execute the action
            result = await self._execute_action(action, session_id)

            # Send response back
            reply = A2AMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                payload={
                    "response": result.get("message"),
                    "action": action.get("type"),
                    "details": result.get("details"),
                },
                correlation_id=message.correlation_id,
            )
            await self.send(reply)

        except Exception as exc:  # noqa: BLE001
            error_reply = A2AMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                payload={"error": str(exc)},
                correlation_id=message.correlation_id,
            )
            await self.send(error_reply)

    async def _interpret_request(self, user_request: str, session_id: str) -> dict:
        """Use LLM to interpret user request and decide action."""
        system_prompt = """You are an orchestrator agent that manages other AI agents.
Users can ask you to:
- Create new agents (specify role: llm, echo, or researcher)
- List active agents
- Terminate agents
- Ask agents to perform tasks

Respond with JSON in this format:
{
  "type": "create_agent" | "list_agents" | "terminate_agent" | "send_message" | "unknown",
  "params": {
    "role": "llm|echo|researcher",  // for create_agent
    "agent_id": "...",               // for terminate_agent or send_message
    "message": "...",                // for send_message
    "model": "gpt-4"                 // optional for create_agent
  }
}"""

        async with self._llm_pool.acquire(self.model_name) as client:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_request},
                ],
                temperature=0.3,
            )

            content = response.choices[0].message.content

            # Try to parse JSON from response
            try:
                # Extract JSON from markdown code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                return json.loads(content)
            except (json.JSONDecodeError, IndexError):
                # Fallback to simple heuristics
                lower_request = user_request.lower()
                if "create" in lower_request or "spawn" in lower_request:
                    role = "llm" if "llm" in lower_request else "echo"
                    return {"type": "create_agent", "params": {"role": role}}
                if "list" in lower_request:
                    return {"type": "list_agents", "params": {}}
                if "terminate" in lower_request or "delete" in lower_request:
                    return {"type": "terminate_agent", "params": {}}
                return {"type": "unknown", "params": {}}

    async def _execute_action(self, action: dict, session_id: str) -> dict:
        """Execute the interpreted action."""
        action_type = action.get("type")
        params = action.get("params", {})

        if action_type == "create_agent":
            role = params.get("role", "llm")
            model = params.get("model", "gpt-4")

            config = AgentConfig(
                name=f"agent-{len(list(self._orchestrator.list_agents())) + 1}",
                role=role,
                mcp_server="echo",  # Default MCP
                metadata={
                    "session_id": session_id,
                    "model": model,
                },
            )

            descriptor = await self._orchestrator.spawn_agent(config)
            return {
                "message": f"Created {role} agent: {descriptor.agent_id}",
                "details": {
                    "agent_id": descriptor.agent_id,
                    "name": descriptor.config.name,
                    "role": role,
                },
            }

        if action_type == "list_agents":
            agents = list(self._orchestrator.list_agents_by_session(session_id))
            agent_list = [
                {
                    "id": a.agent_id,
                    "name": a.config.name,
                    "role": a.config.role,
                    "state": a.state.name,
                }
                for a in agents
            ]
            return {
                "message": f"Found {len(agents)} active agents in this session",
                "details": {"agents": agent_list},
            }

        if action_type == "terminate_agent":
            agent_id = params.get("agent_id")
            if agent_id:
                await self._orchestrator.terminate_agent(agent_id)
                return {"message": f"Terminated agent {agent_id}", "details": {}}
            return {"message": "No agent_id provided", "details": {}}

        return {
            "message": "I didn't understand that request. Try asking me to create, list, or terminate agents.",
            "details": {},
        }
