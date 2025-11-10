# Agentic Orchestrator

Proof-of-concept platform where an orchestrator dynamically provisions AI agents, supervises their lifecycle, and routes A2A (agent-to-agent) communication.

## Quick Start

1. **Setup environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -e .[dev]
   ```

2. **Run CLI demo:**
   ```bash
   python -m app.demo
   ```

3. **Start API service:**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Run tests:**
   ```bash
   python -m pytest
   ```

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
