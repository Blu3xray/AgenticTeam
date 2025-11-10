# Project Structure & Extension Guide

## Current Architecture

```
AgenticTeam/
├── app/
│   ├── agents/           # Agent implementations
│   │   ├── base.py       # Abstract Agent class with lifecycle hooks
│   │   └── echo.py       # Sample EchoAgent (request/response)
│   ├── api/              # HTTP interface
│   │   └── routes.py     # REST endpoints for agent CRUD + messaging
│   ├── core/             # Core primitives
│   │   ├── models.py     # Data contracts (AgentConfig, AgentDescriptor, A2AMessage)
│   │   └── message_bus.py # In-memory async message routing
│   ├── orchestration/    # Lifecycle management
│   │   └── orchestrator.py # Spawn/terminate agents, validate MCP, dispatch messages
│   ├── services/         # External integrations
│   │   └── mcp.py        # MCP server registry (currently mocked)
│   ├── runtime.py        # Dependency injection & singleton composition
│   ├── main.py           # FastAPI entry point
│   └── demo.py           # CLI demonstration script
├── docs/                 # Documentation
├── tests/                # Test suite
├── infrastructure/       # Azure Bicep templates
├── Dockerfile            # Container image definition
└── pyproject.toml        # Python dependencies
```

## Design Principles (SOLID)

### Single Responsibility
- **Agent:** handles messages, maintains state, reports metrics
- **Orchestrator:** lifecycle management only (no business logic)
- **MessageBus:** routing only (no persistence or transformation)
- **MCPRegistry:** capability lookup only

### Open/Closed
- New agent types extend `Agent` base class without modifying orchestrator
- New MCP servers register via `MCPRegistry.register()` without code changes
- New API endpoints add routes without touching existing ones

### Liskov Substitution
- Any `Agent` subclass works with orchestrator (polymorphic lifecycle)
- Message bus agnostic to agent implementation details

### Interface Segregation
- Agents implement only `handle_message()` (not forced to use MCP if not needed)
- Optional hooks: `on_start()`, `on_stop()`, `on_idle()`

### Dependency Inversion
- Orchestrator depends on `Agent` abstraction, not concrete implementations
- Runtime composition injects dependencies (bus, registry) via `get_orchestrator()`

---

## How to Extend

### 1. Add New Agent Type

Create a new agent class in `app/agents/`:

```python
# app/agents/researcher.py
from app.agents.base import Agent
from app.core.models import A2AMessage

class ResearcherAgent(Agent):
    """Agent that performs web research via MCP."""
    
    async def handle_message(self, message: A2AMessage) -> None:
        query = message.payload.get("query")
        # Use MCP to search
        # Process results
        # Send response back
        await self.send(A2AMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            payload={"results": [...]}
        ))
```

Register in catalog (`app/runtime.py`):

```python
_AGENT_CATALOG = {
    "echo": EchoAgent,
    "researcher": ResearcherAgent,  # Add here
}
```

### 2. Add New MCP Server

Register capability in `app/runtime.py`:

```python
@lru_cache
def get_mcp_registry() -> MCPRegistry:
    registry = MCPRegistry()
    registry.register("echo", MCPServer(name="echo-mcp", endpoint="mock://echo"))
    registry.register("web-search", MCPServer(name="brave-search", endpoint="http://brave-mcp:8080"))
    return registry
```

### 3. Add LLM Integration

Create LLM pool service:

```python
# app/services/llm_pool.py
class LLMPool:
    def __init__(self):
        self._clients = {}
    
    def register_model(self, name: str, api_key: str, endpoint: str):
        self._clients[name] = AsyncOpenAI(api_key=api_key, base_url=endpoint)
    
    async def complete(self, model_name: str, messages: list):
        client = self._clients[model_name]
        return await client.chat.completions.create(model=model_name, messages=messages)
```

Wire in orchestrator:

```python
# app/orchestration/orchestrator.py
def __init__(self, *, bus, mcp_registry, agent_catalog, llm_pool):
    self._llm_pool = llm_pool
    # Pass to agents during spawn
```

### 4. Add Persistent Message Bus

Replace `A2AMessageBus` with Redis implementation:

```python
# app/core/redis_bus.py
import redis.asyncio as redis

class RedisMessageBus:
    def __init__(self, redis_url: str):
        self._redis = redis.from_url(redis_url)
    
    async def send(self, message: A2AMessage):
        await self._redis.xadd(
            f"agent:{message.recipient_id}",
            {"payload": json.dumps(message.payload)}
        )
    
    async def deliver(self, agent_id: str):
        # Stream consumer implementation
        pass
```

Update `app/runtime.py` to use Redis bus instead of in-memory.

### 5. Add Session Management

Extend orchestrator with session-aware methods:

```python
# app/orchestration/orchestrator.py
def list_agents_by_session(self, session_id: str):
    return [a.descriptor for a in self._agents.values() 
            if a.config.metadata.get("session_id") == session_id]

async def terminate_session(self, session_id: str):
    agents = [a for a in self._agents.values() 
              if a.config.metadata.get("session_id") == session_id]
    await asyncio.gather(*(self.terminate_agent(a.agent_id) for a in agents))
```

Add API routes:

```python
# app/api/routes.py
@router.get("/sessions/{session_id}/agents")
async def list_session_agents(session_id: str, orch: Orchestrator = Depends(...)):
    return [AgentResponse.from_descriptor(d) 
            for d in orch.list_agents_by_session(session_id)]

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, orch: Orchestrator = Depends(...)):
    await orch.terminate_session(session_id)
```

### 6. Add Authentication

Install FastAPI security:

```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

Add auth middleware:

```python
# app/api/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    token = credentials.credentials
    # Validate JWT or API key
    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user_id
```

Protect routes:

```python
@router.post("/agents", dependencies=[Depends(verify_token)])
async def create_agent(...):
    # Now requires authentication
```

### 7. Add Database Persistence

Install SQLAlchemy + async driver:

```bash
pip install sqlalchemy[asyncio] aiosqlite
```

Create models:

```python
# app/db/models.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class AgentRecord(Base):
    __tablename__ = "agents"
    
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    role: Mapped[str]
    state: Mapped[str]
    config_json: Mapped[str]  # JSON serialized AgentConfig
```

Repository pattern:

```python
# app/db/repository.py
class AgentRepository:
    async def save(self, descriptor: AgentDescriptor):
        # Persist to DB
        pass
    
    async def load_all(self) -> List[AgentDescriptor]:
        # Restore from DB on orchestrator startup
        pass
```

### 8. Add Monitoring

Install OpenTelemetry:

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
```

Instrument application:

```python
# app/main.py
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

# Add custom metrics
from opentelemetry import metrics
meter = metrics.get_meter(__name__)
agent_counter = meter.create_counter("agents.spawned")

# In orchestrator:
async def spawn_agent(self, config):
    descriptor = ...
    agent_counter.add(1, {"role": config.role})
    return descriptor
```

---

## Extension Priority (based on roadmap)

### Phase 1: Foundation (weeks 1-4)
1. ✅ LLM Pool integration
2. ✅ Session management
3. Authentication & authorization
4. Structured logging

### Phase 2: Persistence (weeks 5-8)
5. PostgreSQL for agent state
6. Redis message bus
7. Audit trail logging

### Phase 3: Production-ready (weeks 9-12)
8. OpenTelemetry metrics
9. Health checks & graceful shutdown
10. Rate limiting per session
11. Error handling & retries

### Phase 4: Advanced Features (months 4-6)
12. Real MCP client integration
13. Dynamic agent reconfiguration
14. Multi-tenant isolation
15. Web UI for orchestrator

---

## Testing Strategy

- **Unit tests:** Individual components (message bus, agent lifecycle)
- **Integration tests:** Orchestrator + agents + MCP
- **E2E tests:** API endpoints with real HTTP calls
- **Load tests:** Concurrent agent spawning, message throughput

Add tests in `tests/` following existing patterns.

---

## Contributing Guidelines

1. Each feature in separate file (Single File Responsibility)
2. Update `docs/` when adding major components
3. Add tests for new functionality
4. Keep backwards compatibility in API routes
5. Use type hints everywhere
6. Document public APIs with docstrings
