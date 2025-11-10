# Roadmap

## Short Term

- Replace the in-memory message bus with a persistent transport (Redis streams or Azure Service Bus) to support multi-instance orchestration.
- Add persistence for agent descriptors and audit trails (e.g., PostgreSQL) to survive orchestrator restarts.
- Expand the agent catalog with differentiated roles and shared libraries for MCP integrations.
- Harden the FastAPI surface with authentication, structured logging, and rate limiting.

## Medium Term

- Integrate real MCP servers using official clients; implement capability discovery and health probing.
- Introduce workload-aware scheduling decisions (e.g., spawn based on task queue depth, CPU/RAM hints).
- Support dynamic agent reconfiguration without full teardown.
- Provide metrics and tracing (OpenTelemetry) for message latency and agent health.

## Long Term

- Package the orchestrator for Azure Container Apps including Infrastructure-as-Code templates and CI/CD.
- Develop a chat-based frontend for orchestrator control with role-based access.
- Implement policy-driven governance (quotas, SLAs, sandboxing) across agents and MCP servers.
- Explore agent collaboration patterns (task boards, shared memory) and conflict resolution strategies.
