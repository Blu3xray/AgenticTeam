# Agentic Orchestrator

Production-ready platform where an orchestrator dynamically provisions AI agents, supervises their lifecycle, and routes A2A (agent-to-agent) communication. Features a chat interface for natural language control.

## Features

- 🤖 **Dynamic Agent Creation** – Orchestrator can spawn/terminate agents on demand
- 💬 **Natural Language Control** – Chat with the orchestrator to manage agents
- 🔐 **Session Isolation** – Each user session has isolated agents
- 🧠 **LLM Integration** – Agents powered by Azure OpenAI (with mock fallback)
- 📡 **A2A Communication** – Async message bus for inter-agent messaging
- 🎯 **MCP Support** – Model Context Protocol server registry
- 🚀 **Azure Ready** – Deployment scripts for Azure Container Apps

## Quick Start

1. **Setup environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -e .[dev]
   ```

2. **Configure (optional - works with mocks if not set):**
   ```bash
   export AZURE_OPENAI_KEY="your-key"
   export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
   ```

3. **Start API service:**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Chat with orchestrator:**
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Create a new LLM agent for me"}'
   ```

5. **Run tests:**
   ```bash
   python -m pytest
   ```

## API Endpoints

### Chat Interface
- `POST /chat` – Send natural language commands to orchestrator
  ```json
  {
    "message": "Create an LLM agent",
    "session_id": "optional-session-id"
  }
  ```

### Session Management
- `POST /sessions/{session_id}/agents` – Create agent in session
- `GET /sessions/{session_id}/agents` – List session agents
- `DELETE /sessions/{session_id}` – Terminate all session agents

### Agent Management
- `POST /agents` – Create agent (global scope)
- `GET /agents` – List all agents
- `DELETE /agents/{agent_id}` – Terminate specific agent
- `POST /agents/{agent_id}/messages` – Send A2A message

### Health
- `GET /health` – Service health check

## Documentation

- [Overview](docs/overview.md) – entry point
- [Architecture](docs/architecture.md) – component design
- [Operations](docs/operations.md) – runtime & API usage
- [Roadmap](docs/roadmap.md) – planned enhancements

## Project Structure

```
app/
├── agents/          # Agent implementations
├── api/             # FastAPI routes
├── core/            # Message bus & models
├── orchestration/   # Orchestrator logic
├── services/        # MCP registry
├── runtime.py       # Dependency composition
├── main.py          # FastAPI entry point
└── demo.py          # CLI demonstration

docs/                # Documentation
tests/               # Test suite
```

## License

MIT
