# Architecture

```
+-----------+        A2A Bus         +---------------+
| Orchestrator|<-------------------->| Agent Mailboxes|
+-----------+                        +---------------+
      |                                       |
      | spawn/terminate                       | async loops
      v                                       v
+-------------+                        +-----------------+
| Agent Catalog|---instantiate-------> | Agent Instances |
+-------------+                        +-----------------+
      |
      | MCP lookup
      v
+-----------------+
| MCP Registry    |
|  + MCP Servers  |
+-----------------+
```

## Key Modules

- **Orchestrator (`app/orchestration/orchestrator.py`)** – coordinates agent lifecycle, validates MCP availability, maintains descriptors, and dispatches messages through the shared bus.
- **Message bus (`app/core/message_bus.py`)** – in-memory async queues per agent; broadcasts or direct routing for A2A messages.
- **Agents**
  - **Base (`app/agents/base.py`)** – defines lifecycle hooks (`start`, `stop`, `handle_message`) and manages safe async execution.
  - **EchoAgent (`app/agents/echo.py`)** – sample role that demonstrates request/response flows.
- **MCP registry (`app/services/mcp.py`)** – lightweight capability map returning `MCPServer` instances; currently simulates execution.
- **Runtime composition (`app/runtime.py`)** – wires orchestrator, bus, and MCP registry with cached singletons for API usage.
- **API layer (`app/main.py`, `app/api/routes.py`)** – FastAPI service exposing HTTP endpoints for lifecycle control and messaging.

## Data Contracts

- **AgentConfig** – desired agent role, name, target MCP server, and metadata.
- **AgentDescriptor** – orchestrator-managed state snapshot (ID, state, task count, last error).
- **A2AMessage** – canonical payload exchanged between agents with optional correlation ID.

## Lifecycle Phases

1. Client issues `POST /agents` with role and MCP binding.
2. Orchestrator validates MCP capability, instantiates the agent class, and starts its async runner.
3. Agent registers with the bus, enters `RUNNING`, and begins handling messages.
4. Messages travel through the bus (`dispatch` API or other agents) and update descriptor metrics.
5. `DELETE /agents/{id}` or shutdown triggers graceful stop: descriptor marked `STOPPING`, loop exits, state becomes `STOPPED`.
