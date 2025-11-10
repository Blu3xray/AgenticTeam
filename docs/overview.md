# Agentic Orchestrator

Production-ready platform where an orchestrator dynamically provisions AI agents, supervises their lifecycle, and routes A2A (agent-to-agent) communication.

## Key Capabilities

- **Chat Interface:** Interact with orchestrator using natural language (see `docs/chat-interface.md`)
- **Dynamic Agent Management:** Orchestrator spawns/terminates agents on demand
- **Session Isolation:** Multi-tenant support with per-session agent workspaces
- **LLM Integration:** Agents powered by Azure OpenAI with mock fallback
- **MCP Support:** Model Context Protocol server registry for external integrations

## Documentation

- **Architecture:** `docs/architecture.md` – component design and data flow
- **Operations:** `docs/operations.md` – API usage, deployment, and testing
- **Chat Interface:** `docs/chat-interface.md` – natural language control guide
- **Extension Guide:** `docs/extension-guide.md` – how to add features
- **Azure Deployment:** `docs/azure-deployment.md` – production deployment
- **Roadmap:** `docs/roadmap.md` – planned enhancements

## Quick Example

```bash
# Start the service
uvicorn app.main:app --reload

# Chat with orchestrator
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a new LLM agent"}'
```

Use this page as the top-level entry point before diving into the focused documents.
