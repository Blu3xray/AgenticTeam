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

```bash
# 1. Clone and setup
git clone https://github.com/Blu3xray/AgenticTeam.git
cd AgenticTeam
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .[dev]

# 2. Start server (works with mock LLM, no API keys needed)
uvicorn app.main:app --reload

# 3. Chat with orchestrator
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a new LLM agent", "session_id": "demo"}'

# 4. Interactive API docs
open http://localhost:8000/docs
```

### With Azure OpenAI (Optional)

```bash
# Create .env file
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# Install dotenv support
pip install python-dotenv

# Restart server
uvicorn app.main:app --reload
```

**📖 Full guide:** See [docs/getting-started.md](docs/getting-started.md)

## Azure Deployment 🚀

Deploy to Azure in minutes! Choose your path:

### Quick Deploy (5 minutes)
```bash
# One-command deployment to Azure Container Apps
./deploy-azure.sh
```

### Documentation
- **[Azure Deploy Tutorial](docs/azure-deploy-tutorial.md)** - Step-by-step guide (START HERE!)
- **[Azure Hosting Options](docs/azure-hosting-options.md)** - Compare all Azure options
- **[Azure Deployment Guide](docs/azure-deployment.md)** - Technical details & Bicep IaC

### What You Get
- ✅ Public HTTPS URL
- ✅ Auto-scaling (1-10 replicas)
- ✅ Monitoring & logs
- ✅ GitHub Actions CI/CD
- ✅ Costs: ~$20-100/month

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

### Getting Started
- [Getting Started](docs/getting-started.md) – **Start here!** Complete setup and first steps
- [Overview](docs/overview.md) – Platform capabilities and architecture summary
- [Chat Interface](docs/chat-interface.md) – Natural language control guide

### Deployment
- **[Azure Deploy Tutorial](docs/azure-deploy-tutorial.md)** – Step-by-step deployment guide
- **[Azure Hosting Options](docs/azure-hosting-options.md)** – Compare Container Apps, App Service, AKS
- [Azure Deployment](docs/azure-deployment.md) – Production deployment with Bicep

### Development
- [Architecture](docs/architecture.md) – Component design and data flow
- [Operations](docs/operations.md) – API reference and testing
- [Extension Guide](docs/extension-guide.md) – How to add features
- [Roadmap](docs/roadmap.md) – Planned enhancements

### Advanced
- [Migration to Production](docs/migration-to-production.md) – Mock to real implementation
- [MCP Quick Start](docs/mcp-quickstart.md) – Real MCP server integration
- [Verification Report](docs/verification-report.md) – Testing and validation results

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
