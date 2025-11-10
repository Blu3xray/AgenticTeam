"""Minimal MCP server registry abstraction used by the orchestrator."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict


@dataclass(slots=True)
class MCPServer:
    """Represents a remote MCP server endpoint."""

    name: str
    endpoint: str

    async def execute(self, task_payload: dict) -> dict:
        """Simulate a call to the MCP server."""
        await asyncio.sleep(0.1)
        return {"server": self.name, "status": "ok", "result": task_payload}


class MCPRegistry:
    """Registry maintaining MCP server definitions by capability."""

    def __init__(self) -> None:
        self._servers: Dict[str, MCPServer] = {}

    def register(self, capability: str, server: MCPServer) -> None:
        self._servers[capability] = server

    def get(self, capability: str) -> MCPServer:
        if capability not in self._servers:
            raise KeyError(f"No MCP server registered for capability: {capability}")
        return self._servers[capability]
