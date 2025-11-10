# Operations

## Running the FastAPI Service

```bash
uvicorn app.main:app --reload
```

Available endpoints:

- `GET /health` – readiness probe; terminates all agents on shutdown.
- `POST /agents` – create agent from JSON body `{ "name": str, "role": str, "mcp_server": str, "metadata": dict }`.
- `GET /agents` – list descriptors for managed agents.
- `DELETE /agents/{agent_id}` – terminate a specific agent.
- `POST /agents/{agent_id}/messages` – enqueue payload for the target agent.

## CLI Demonstration

```bash
python -m app.demo
```

Flow:

1. Compose an in-memory orchestrator with the Echo agent catalog entry.
2. Spawn a new agent and log its identifier/state.
3. Exchange a single message using the shared bus.
4. Terminate the agent and exit cleanly.

## Agent Lifecycle Controls

- **Spawn:** orchestrator creates descriptor, validates MCP server, starts async runner, waits for mailbox readiness, and transitions to `RUNNING`.
- **Messaging:** callers send `A2AMessage` instances via the bus; agents can broadcast or reply directly.
- **Idle Hook:** agents may perform background work when no messages arrive (default is no-op).
- **Stop:** orchestrator sets state to `STOPPING`, signals the loop, and awaits completion. Final state becomes `STOPPED` or `FAILED` depending on exit path.
- **Shutdown:** API shutdown hook calls `terminate_all()` ensuring no orphaned tasks remain.

## Testing

```bash
python -m pytest
```

`tests/test_orchestrator.py` covers spawn/termination and message round-trips via AnyIO with the asyncio backend.
