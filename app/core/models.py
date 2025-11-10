"""Core data models shared across orchestrator components."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional


class AgentState(Enum):
    """Lifecycle states for an agent managed by the orchestrator."""

    SPAWNING = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    FAILED = auto()


@dataclass(slots=True)
class AgentConfig:
    """Configuration payload used by the orchestrator when instantiating an agent."""

    name: str
    role: str
    mcp_server: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentDescriptor:
    """Descriptor persisted by the orchestrator for each active agent."""

    agent_id: str
    config: AgentConfig
    state: AgentState = AgentState.SPAWNING
    task_count: int = 0
    last_error: Optional[str] = None


@dataclass(slots=True)
class A2AMessage:
    """Canonical message exchanged between agents over the A2A bus."""

    sender_id: str
    recipient_id: Optional[str]
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None
