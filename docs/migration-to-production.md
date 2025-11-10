# Migracja z Mock do Produkcji - Szczegółowy Plan

## Przegląd obecnego stanu

### Komponenty z mock implementacją:

1. **MCP Server Registry** (`app/services/mcp.py`)
   - Obecny stan: Symulowane serwery MCP z `async def execute()`
   - Problem: Brak rzeczywistej komunikacji z MCP serwerami

2. **LLM Pool** (`app/services/llm_pool.py`)
   - Obecny stan: `MockLLMClient` gdy brak Azure OpenAI
   - Problem: Mock zwraca tylko echo wiadomości, nie generuje prawdziwych odpowiedzi

3. **Message Bus** (`app/core/message_bus.py`)
   - Obecny stan: In-memory `asyncio.Queue`
   - Problem: Brak persystencji, nie działa w multi-instance deployment

4. **Agent State** (brak persystencji)
   - Obecny stan: Wszystko w pamięci
   - Problem: Utrata stanu po restarcie

---

## Faza 1: Integracja Real MCP Servers

### Krok 1.1: Dodaj MCP Client SDK

```bash
# Zainstaluj oficjalny klient MCP
pip install mcp anthropic-mcp-client
```

Zaktualizuj `pyproject.toml`:
```toml
[project]
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "mcp>=1.0.0",  # Model Context Protocol SDK
    "anthropic-mcp-client>=0.1.0",  # Oficjalny klient
]
```

### Krok 1.2: Stwórz Real MCP Client

Utwórz nowy plik `app/services/mcp_client.py`:

```python
"""Real MCP client implementation using official SDK."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class RealMCPServer:
    """Real MCP server connection using official SDK."""

    def __init__(self, name: str, command: str, args: list[str], env: Optional[Dict[str, str]] = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self._session: Optional[ClientSession] = None
        self._client = None

    async def connect(self) -> None:
        """Establish connection to MCP server."""
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env,
        )

        # Create stdio client connection
        stdio_transport = await stdio_client(server_params)
        self._client, self._session = stdio_transport

        # Initialize session
        await self._session.initialize()

    async def disconnect(self) -> None:
        """Close MCP server connection."""
        if self._client:
            await self._client.cleanup()
        self._session = None
        self._client = None

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute MCP tool with given arguments."""
        if not self._session:
            raise RuntimeError(f"MCP server {self.name} not connected")

        # List available tools
        tools = await self._session.list_tools()
        tool = next((t for t in tools.tools if t.name == tool_name), None)

        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in {self.name}")

        # Call tool
        result = await self._session.call_tool(tool_name, arguments)
        return result.content

    async def list_tools(self) -> list[dict]:
        """Get available tools from this MCP server."""
        if not self._session:
            raise RuntimeError(f"MCP server {self.name} not connected")

        tools_response = await self._session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools_response.tools
        ]
```

### Krok 1.3: Zaktualizuj MCPRegistry

Zmodyfikuj `app/services/mcp.py`:

```python
"""MCP server registry with support for both mock and real servers."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, Protocol


class MCPServerProtocol(Protocol):
    """Protocol defining MCP server interface."""
    name: str

    async def execute(self, *args, **kwargs) -> dict:
        """Execute task on MCP server."""
        ...


@dataclass(slots=True)
class MockMCPServer:
    """Mock MCP server for testing."""
    name: str
    endpoint: str

    async def execute(self, task_payload: dict) -> dict:
        """Simulate a call to the MCP server."""
        await asyncio.sleep(0.1)
        return {"server": self.name, "status": "ok", "result": task_payload}


class MCPRegistry:
    """Registry maintaining both mock and real MCP servers."""

    def __init__(self) -> None:
        self._servers: Dict[str, MCPServerProtocol] = {}

    def register(self, capability: str, server: MCPServerProtocol) -> None:
        """Register MCP server (mock or real)."""
        self._servers[capability] = server

    async def register_real(
        self,
        capability: str,
        name: str,
        command: str,
        args: list[str],
        env: dict | None = None,
    ) -> None:
        """Register and connect to real MCP server."""
        from app.services.mcp_client import RealMCPServer

        server = RealMCPServer(name, command, args, env)
        await server.connect()
        self._servers[capability] = server

    def get(self, capability: str) -> MCPServerProtocol:
        if capability not in self._servers:
            raise KeyError(f"No MCP server registered for capability: {capability}")
        return self._servers[capability]

    async def shutdown_all(self) -> None:
        """Disconnect all real MCP servers."""
        from app.services.mcp_client import RealMCPServer

        for server in self._servers.values():
            if isinstance(server, RealMCPServer):
                await server.disconnect()
```

### Krok 1.4: Konfiguracja Real MCP Servers

Zaktualizuj `.env.example`:

```env
# MCP Servers Configuration
MCP_USE_REAL=true  # Use real MCP servers instead of mocks

# Example: Filesystem MCP Server
MCP_FILESYSTEM_ENABLED=true
MCP_FILESYSTEM_COMMAND=npx
MCP_FILESYSTEM_ARGS=-y,@modelcontextprotocol/server-filesystem,/tmp

# Example: Brave Search MCP Server
MCP_BRAVE_SEARCH_ENABLED=false
MCP_BRAVE_SEARCH_COMMAND=npx
MCP_BRAVE_SEARCH_ARGS=-y,@modelcontextprotocol/server-brave-search
MCP_BRAVE_SEARCH_API_KEY=your-brave-api-key
```

Zaktualizuj `app/config.py`:

```python
@dataclass(frozen=True)
class MCPServerConfig:
    """Configuration for a single MCP server."""
    enabled: bool
    command: str
    args: list[str]
    env: dict[str, str]


@dataclass(frozen=True)
class Config:
    """Application configuration."""
    azure_openai: Optional[AzureOpenAIConfig] = None
    environment: str = "development"
    use_real_mcp: bool = False
    mcp_servers: dict[str, MCPServerConfig] = None

    @classmethod
    def from_env(cls) -> Config:
        # ... existing Azure OpenAI config ...

        # Parse MCP servers from environment
        use_real_mcp = os.getenv("MCP_USE_REAL", "false").lower() == "true"
        mcp_servers = {}

        if use_real_mcp:
            # Filesystem MCP
            if os.getenv("MCP_FILESYSTEM_ENABLED", "false").lower() == "true":
                mcp_servers["filesystem"] = MCPServerConfig(
                    enabled=True,
                    command=os.getenv("MCP_FILESYSTEM_COMMAND", "npx"),
                    args=os.getenv("MCP_FILESYSTEM_ARGS", "").split(","),
                    env={},
                )

            # Brave Search MCP
            if os.getenv("MCP_BRAVE_SEARCH_ENABLED", "false").lower() == "true":
                mcp_servers["brave-search"] = MCPServerConfig(
                    enabled=True,
                    command=os.getenv("MCP_BRAVE_SEARCH_COMMAND", "npx"),
                    args=os.getenv("MCP_BRAVE_SEARCH_ARGS", "").split(","),
                    env={"BRAVE_API_KEY": os.getenv("MCP_BRAVE_SEARCH_API_KEY", "")},
                )

        return cls(
            azure_openai=azure_config,
            environment=os.getenv("ENVIRONMENT", "development"),
            use_real_mcp=use_real_mcp,
            mcp_servers=mcp_servers,
        )
```

### Krok 1.5: Zaktualizuj Runtime

Zmodyfikuj `app/runtime.py`:

```python
@lru_cache
def get_mcp_registry() -> MCPRegistry:
    registry = MCPRegistry()

    if config.use_real_mcp and config.mcp_servers:
        # Register real MCP servers
        import asyncio

        async def init_real_servers():
            for capability, server_config in config.mcp_servers.items():
                if server_config.enabled:
                    await registry.register_real(
                        capability=capability,
                        name=f"{capability}-mcp",
                        command=server_config.command,
                        args=server_config.args,
                        env=server_config.env,
                    )

        # Run async initialization
        asyncio.run(init_real_servers())
    else:
        # Fallback to mock servers
        from app.services.mcp import MockMCPServer

        registry.register("echo", MockMCPServer(name="echo-mcp", endpoint="mock://echo"))
        registry.register("filesystem", MockMCPServer(name="fs-mcp", endpoint="mock://fs"))

    return registry
```

### Krok 1.6: Shutdown Hook

Zaktualizuj `app/main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application."""
    # Startup
    await initialize_orchestrator_agent()
    yield
    # Shutdown
    orchestrator = get_orchestrator()
    await orchestrator.terminate_all()

    # Disconnect MCP servers
    registry = get_mcp_registry()
    await registry.shutdown_all()
```

---

## Faza 2: Persistent Message Bus (Redis)

### Krok 2.1: Instalacja Redis

```bash
pip install redis[hiredis] aioredis
```

Zaktualizuj `pyproject.toml`:
```toml
dependencies = [
    "redis[hiredis]>=5.0.0",
]
```

### Krok 2.2: Redis Message Bus Implementation

Utwórz `app/core/redis_bus.py`:

```python
"""Redis-based persistent message bus for distributed orchestration."""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as redis

from .models import A2AMessage


class RedisMessageBus:
    """Persistent message bus using Redis Streams."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self._redis_url = redis_url
        self._redis: redis.Redis | None = None
        self._consumer_tasks: dict[str, asyncio.Task] = {}

    async def connect(self) -> None:
        """Initialize Redis connection."""
        self._redis = await redis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        """Close Redis connection."""
        # Cancel all consumer tasks
        for task in self._consumer_tasks.values():
            task.cancel()
        await asyncio.gather(*self._consumer_tasks.values(), return_exceptions=True)

        if self._redis:
            await self._redis.close()

    async def register(self, agent_id: str) -> None:
        """Create consumer group for agent."""
        stream_key = f"agent:{agent_id}"
        try:
            await self._redis.xgroup_create(
                stream_key,
                groupname=agent_id,
                id="0",
                mkstream=True,
            )
        except redis.ResponseError:
            # Group already exists
            pass

    async def unregister(self, agent_id: str) -> None:
        """Remove agent's stream and consumer group."""
        stream_key = f"agent:{agent_id}"
        await self._redis.delete(stream_key)

    async def send(self, message: A2AMessage) -> None:
        """Send message to recipient's stream."""
        if not message.recipient_id:
            # Broadcast not implemented yet
            return

        stream_key = f"agent:{message.recipient_id}"
        message_data = {
            "sender_id": message.sender_id,
            "payload": json.dumps(message.payload),
            "correlation_id": message.correlation_id or "",
        }

        await self._redis.xadd(stream_key, message_data)

    @asynccontextmanager
    async def deliver(self, agent_id: str) -> AsyncIterator[asyncio.Queue[A2AMessage]]:
        """Context manager yielding queue of messages from Redis stream."""
        await self.register(agent_id)
        inbox = asyncio.Queue()

        # Start consumer task
        consumer_task = asyncio.create_task(
            self._consume_stream(agent_id, inbox)
        )
        self._consumer_tasks[agent_id] = consumer_task

        try:
            yield inbox
        finally:
            consumer_task.cancel()
            await self.unregister(agent_id)
            del self._consumer_tasks[agent_id]

    async def _consume_stream(self, agent_id: str, inbox: asyncio.Queue) -> None:
        """Continuously read from Redis stream and put into queue."""
        stream_key = f"agent:{agent_id}"
        last_id = ">"

        while True:
            try:
                # Read from stream
                messages = await self._redis.xreadgroup(
                    groupname=agent_id,
                    consumername=agent_id,
                    streams={stream_key: last_id},
                    count=10,
                    block=1000,  # 1 second timeout
                )

                if not messages:
                    continue

                for stream, msg_list in messages:
                    for msg_id, msg_data in msg_list:
                        # Parse message
                        message = A2AMessage(
                            sender_id=msg_data["sender_id"],
                            recipient_id=agent_id,
                            payload=json.loads(msg_data["payload"]),
                            correlation_id=msg_data.get("correlation_id") or None,
                        )

                        # Put into queue
                        await inbox.put(message)

                        # Acknowledge message
                        await self._redis.xack(stream_key, agent_id, msg_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                print(f"Error consuming stream for {agent_id}: {e}")
                await asyncio.sleep(1)
```

### Krok 2.3: Konfiguracja Redis

Zaktualizuj `.env.example`:

```env
# Message Bus Configuration
MESSAGE_BUS_TYPE=redis  # "memory" or "redis"
REDIS_URL=redis://localhost:6379
```

Zaktualizuj `app/config.py`:

```python
@dataclass(frozen=True)
class Config:
    # ... existing fields ...
    message_bus_type: str = "memory"
    redis_url: str = "redis://localhost:6379"

    @classmethod
    def from_env(cls) -> Config:
        # ... existing code ...

        return cls(
            # ... existing fields ...
            message_bus_type=os.getenv("MESSAGE_BUS_TYPE", "memory"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        )
```

### Krok 2.4: Runtime Selection

Zaktualizuj `app/runtime.py`:

```python
@lru_cache
def get_bus() -> A2AMessageBus:
    if config.message_bus_type == "redis":
        from app.core.redis_bus import RedisMessageBus

        bus = RedisMessageBus(config.redis_url)
        # Initialize connection
        import asyncio
        asyncio.run(bus.connect())
        return bus
    else:
        from app.core.message_bus import A2AMessageBus
        return A2AMessageBus()
```

---

## Faza 3: Database Persistence (PostgreSQL)

### Krok 3.1: Instalacja Dependencies

```bash
pip install sqlalchemy[asyncio] asyncpg alembic
```

### Krok 3.2: Database Models

Utwórz `app/db/models.py`:

```python
"""SQLAlchemy models for agent persistence."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Integer, Enum
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.models import AgentState


class Base(AsyncAttrs, DeclarativeBase):
    pass


class AgentRecord(Base):
    """Persistent agent state in database."""
    __tablename__ = "agents"

    agent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(64))
    mcp_server: Mapped[str] = mapped_column(String(256))
    state: Mapped[str] = mapped_column(String(32))
    metadata_json: Mapped[dict] = mapped_column(JSON)
    task_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MessageRecord(Base):
    """Audit trail for A2A messages."""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_id: Mapped[str] = mapped_column(String(64), index=True)
    recipient_id: Mapped[str] = mapped_column(String(64), index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### Krok 3.3: Repository Pattern

Utwórz `app/db/repository.py`:

```python
"""Repository for agent and message persistence."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AgentConfig, AgentDescriptor, AgentState, A2AMessage
from app.db.models import AgentRecord, MessageRecord


class AgentRepository:
    """Repository for agent CRUD operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, descriptor: AgentDescriptor) -> None:
        """Persist agent descriptor to database."""
        record = AgentRecord(
            agent_id=descriptor.agent_id,
            name=descriptor.config.name,
            role=descriptor.config.role,
            mcp_server=descriptor.config.mcp_server,
            state=descriptor.state.name,
            metadata_json=descriptor.config.metadata,
            task_count=descriptor.task_count,
            last_error=descriptor.last_error,
        )

        self._session.add(record)
        await self._session.commit()

    async def update(self, descriptor: AgentDescriptor) -> None:
        """Update existing agent record."""
        stmt = select(AgentRecord).where(AgentRecord.agent_id == descriptor.agent_id)
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            record.state = descriptor.state.name
            record.task_count = descriptor.task_count
            record.last_error = descriptor.last_error
            await self._session.commit()

    async def delete(self, agent_id: str) -> None:
        """Remove agent from database."""
        stmt = select(AgentRecord).where(AgentRecord.agent_id == agent_id)
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            await self._session.delete(record)
            await self._session.commit()

    async def load_all(self) -> List[AgentDescriptor]:
        """Load all agent descriptors from database."""
        stmt = select(AgentRecord)
        result = await self._session.execute(stmt)
        records = result.scalars().all()

        return [
            AgentDescriptor(
                agent_id=r.agent_id,
                config=AgentConfig(
                    name=r.name,
                    role=r.role,
                    mcp_server=r.mcp_server,
                    metadata=r.metadata_json,
                ),
                state=AgentState[r.state],
                task_count=r.task_count,
                last_error=r.last_error,
            )
            for r in records
        ]


class MessageRepository:
    """Repository for message audit trail."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def log_message(self, message: A2AMessage) -> None:
        """Store message in audit trail."""
        record = MessageRecord(
            sender_id=message.sender_id,
            recipient_id=message.recipient_id or "",
            correlation_id=message.correlation_id,
            payload_json=message.payload,
        )

        self._session.add(record)
        await self._session.commit()
```

### Krok 3.4: Database Configuration

Zaktualizuj `.env.example`:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost/agentic_team
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

Zaktualizuj `app/config.py`:

```python
@dataclass(frozen=True)
class DatabaseConfig:
    """Database connection configuration."""
    url: str
    pool_size: int = 20
    max_overflow: int = 10


@dataclass(frozen=True)
class Config:
    # ... existing fields ...
    database: Optional[DatabaseConfig] = None

    @classmethod
    def from_env(cls) -> Config:
        # ... existing code ...

        # Database config
        db_url = os.getenv("DATABASE_URL")
        database_config = None
        if db_url:
            database_config = DatabaseConfig(
                url=db_url,
                pool_size=int(os.getenv("DATABASE_POOL_SIZE", "20")),
                max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
            )

        return cls(
            # ... existing fields ...
            database=database_config,
        )
```

### Krok 3.5: Database Setup

Utwórz `app/db/engine.py`:

```python
"""Database engine and session management."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import config


def get_engine():
    """Get async SQLAlchemy engine."""
    if not config.database:
        raise RuntimeError("Database not configured")

    return create_async_engine(
        config.database.url,
        pool_size=config.database.pool_size,
        max_overflow=config.database.max_overflow,
        echo=config.environment == "development",
    )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get session factory."""
    engine = get_engine()
    return async_sessionmaker(engine, expire_on_commit=False)
```

### Krok 3.6: Alembic Migrations

Inicjalizacja Alembic:

```bash
alembic init migrations
```

Edytuj `alembic.ini`:
```ini
sqlalchemy.url = postgresql+asyncpg://user:password@localhost/agentic_team
```

Utwórz pierwszą migrację:
```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

---

## Faza 4: Orchestrator Integration

### Krok 4.1: Zaktualizuj Orchestrator

Zmodyfikuj `app/orchestration/orchestrator.py`:

```python
class Orchestrator:
    """Orchestrator with database persistence."""

    def __init__(
        self,
        *,
        bus: A2AMessageBus,
        mcp_registry: MCPRegistry,
        agent_catalog: Dict[str, Type[Agent]],
        repository: Optional[AgentRepository] = None,
    ) -> None:
        self._bus = bus
        self._mcp_registry = mcp_registry
        self._agent_catalog = agent_catalog
        self._agents: Dict[str, Agent] = {}
        self._lock = asyncio.Lock()
        self._llm_pool: Optional[Any] = None
        self._repository = repository

    async def spawn_agent(self, config: AgentConfig) -> AgentDescriptor:
        """Spawn agent and persist to database."""
        # ... existing spawn logic ...

        descriptor = AgentDescriptor(...)
        agent = agent_cls(...)

        async with self._lock:
            self._agents[descriptor.agent_id] = agent

        await agent.start()

        # Persist to database
        if self._repository:
            await self._repository.save(descriptor)

        return descriptor

    async def terminate_agent(self, agent_id: str) -> None:
        """Terminate agent and update database."""
        # ... existing terminate logic ...

        # Remove from database
        if self._repository:
            await self._repository.delete(agent_id)

    async def restore_from_database(self) -> None:
        """Restore agents from database on startup."""
        if not self._repository:
            return

        descriptors = await self._repository.load_all()

        for descriptor in descriptors:
            # Only restore RUNNING agents
            if descriptor.state == AgentState.RUNNING:
                try:
                    agent_cls = self._resolve_agent_class(descriptor.config.role)
                    agent = agent_cls(descriptor, self._bus)
                    await agent.start()
                    self._agents[descriptor.agent_id] = agent
                except Exception as e:
                    print(f"Failed to restore agent {descriptor.agent_id}: {e}")
```

### Krok 4.2: Zaktualizuj Runtime

Zmodyfikuj `app/runtime.py`:

```python
@lru_cache
def get_orchestrator() -> Orchestrator:
    # Get repository if database configured
    repository = None
    if config.database:
        from app.db.engine import get_session_factory
        from app.db.repository import AgentRepository

        session_factory = get_session_factory()

        async def get_repo():
            async with session_factory() as session:
                return AgentRepository(session)

        import asyncio
        repository = asyncio.run(get_repo())

    orchestrator = Orchestrator(
        bus=get_bus(),
        mcp_registry=get_mcp_registry(),
        agent_catalog=_AGENT_CATALOG,
        repository=repository,
    )

    orchestrator.set_llm_pool(get_llm_pool())

    # Restore agents from database
    if repository:
        import asyncio
        asyncio.run(orchestrator.restore_from_database())

    return orchestrator
```

---

## Faza 5: Testing & Deployment

### Krok 5.1: Integration Tests

Utwórz `tests/test_real_mcp.py`:

```python
"""Tests for real MCP server integration."""
import pytest
from app.services.mcp_client import RealMCPServer


@pytest.mark.skipif(not os.getenv("TEST_REAL_MCP"), reason="Real MCP tests disabled")
@pytest.mark.anyio
async def test_filesystem_mcp():
    """Test real filesystem MCP server."""
    server = RealMCPServer(
        name="fs-test",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    )

    await server.connect()

    try:
        # List tools
        tools = await server.list_tools()
        assert len(tools) > 0

        # Execute read_file tool
        result = await server.execute(
            "read_file",
            {"path": "/tmp/test.txt"}
        )
        assert result is not None
    finally:
        await server.disconnect()
```

### Krok 5.2: Docker Compose dla Local Development

Utwórz `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: agentic_team
      POSTGRES_USER: agent_user
      POSTGRES_PASSWORD: agent_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://agent_user:agent_pass@postgres/agentic_team
      - REDIS_URL=redis://redis:6379
      - MESSAGE_BUS_TYPE=redis
      - MCP_USE_REAL=true
    depends_on:
      - postgres
      - redis
    volumes:
      - ./app:/app/app

volumes:
  postgres_data:
  redis_data:
```

### Krok 5.3: Migration Guide

Utwórz `docs/migration-checklist.md`:

```markdown
# Migration Checklist

## Prerequisites
- [ ] PostgreSQL 14+ installed
- [ ] Redis 6+ installed
- [ ] Node.js (for MCP servers)
- [ ] Azure OpenAI credentials (or other LLM provider)

## Step 1: Local Testing
- [ ] Start PostgreSQL and Redis
- [ ] Run migrations: `alembic upgrade head`
- [ ] Set environment variables
- [ ] Test with mock first: `MCP_USE_REAL=false`
- [ ] Verify all tests pass: `pytest`

## Step 2: Enable Real MCP
- [ ] Install MCP servers: `npm install -g @modelcontextprotocol/server-*`
- [ ] Configure MCP in `.env`
- [ ] Set `MCP_USE_REAL=true`
- [ ] Test MCP connectivity

## Step 3: Enable Redis
- [ ] Set `MESSAGE_BUS_TYPE=redis`
- [ ] Test multi-instance deployment
- [ ] Verify message persistence

## Step 4: Production Deployment
- [ ] Update Azure deployment scripts
- [ ] Configure managed PostgreSQL
- [ ] Configure managed Redis
- [ ] Update secrets in Azure Key Vault
- [ ] Deploy and monitor
```

---

## Podsumowanie Migracji

### Kolejność implementacji (rekomendowana):

1. **Tydzień 1-2:** Real MCP Servers
   - Najmniejsze ryzyko
   - Największy wpływ na funkcjonalność
   - Testowalne lokalnie bez infrastruktury

2. **Tydzień 3:** Redis Message Bus
   - Umożliwia horizontal scaling
   - Wymaga Redis infrastructure
   - Backward compatible (można przełączać)

3. **Tydzień 4-5:** Database Persistence
   - Najbardziej złożone
   - Wymaga migrations
   - Umożliwia recovery po restartach

4. **Tydzień 6:** Integration Testing & Production Deploy
   - End-to-end testy
   - Performance testing
   - Deployment na Azure

### Feature Flags

Wszystkie zmiany używają configuration flags, więc można:
- Testować każdą feature osobno
- Rollback bez zmian w kodzie
- Stopniowo migrować w produkcji

### Backward Compatibility

- Mock implementacje pozostają jako fallback
- Można mieszać mock i real components
- Graceful degradation gdy brak infrastruktury
