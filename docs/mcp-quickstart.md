# Quick Start: Implementacja Real MCP Server

Ten przewodnik pokazuje jak zaimplementować pierwszy real MCP server (filesystem) krok po kroku.

## Setup

### 1. Instalacja Dependencies

```bash
# Dodaj do pyproject.toml
pip install mcp anthropic-mcp-client

# Zainstaluj MCP filesystem server
npm install -g @modelcontextprotocol/server-filesystem
```

### 2. Testuj MCP Server Lokalnie

```bash
# Uruchom MCP server standalone (test)
npx -y @modelcontextprotocol/server-filesystem /tmp

# Powinien wyświetlić dostępne tools
```

## Implementacja

### Krok 1: Stwórz Real MCP Client

Utwórz `app/services/mcp_client.py`:

```python
"""Real MCP client using official SDK."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional
from dataclasses import dataclass

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


@dataclass
class MCPToolInfo:
    """Information about an MCP tool."""
    name: str
    description: str
    input_schema: dict


class RealMCPServer:
    """Real MCP server connection."""

    def __init__(
        self,
        name: str,
        command: str,
        args: list[str],
        env: Optional[Dict[str, str]] = None,
    ):
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP SDK not installed. Install with: pip install mcp anthropic-mcp-client"
            )

        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self._session: Optional[ClientSession] = None
        self._client = None
        self._tools: list[MCPToolInfo] = []

    async def connect(self) -> None:
        """Establish connection to MCP server."""
        print(f"[MCP] Connecting to {self.name}: {self.command} {' '.join(self.args)}")

        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env,
        )

        # Create stdio transport
        try:
            self._client, self._session = await stdio_client(server_params)
            await self._session.initialize()
            print(f"[MCP] Connected to {self.name}")

            # Cache available tools
            await self._refresh_tools()

        except Exception as e:
            print(f"[MCP] Failed to connect to {self.name}: {e}")
            raise

    async def disconnect(self) -> None:
        """Close connection."""
        if self._client:
            print(f"[MCP] Disconnecting from {self.name}")
            await self._client.cleanup()
        self._session = None
        self._client = None

    async def _refresh_tools(self) -> None:
        """Refresh list of available tools."""
        if not self._session:
            return

        tools_response = await self._session.list_tools()
        self._tools = [
            MCPToolInfo(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema,
            )
            for tool in tools_response.tools
        ]
        print(f"[MCP] {self.name} has {len(self._tools)} tools")

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute tool with given arguments."""
        if not self._session:
            raise RuntimeError(f"MCP server {self.name} not connected")

        # Verify tool exists
        tool = next((t for t in self._tools if t.name == tool_name), None)
        if not tool:
            available = [t.name for t in self._tools]
            raise ValueError(
                f"Tool '{tool_name}' not found in {self.name}. "
                f"Available: {available}"
            )

        print(f"[MCP] Calling {self.name}.{tool_name}({arguments})")

        # Call tool
        try:
            result = await self._session.call_tool(tool_name, arguments)

            # Extract content
            if hasattr(result, "content") and result.content:
                # MCP returns list of content blocks
                content_blocks = result.content
                if len(content_blocks) == 1:
                    return {"result": content_blocks[0].text}
                else:
                    return {"results": [block.text for block in content_blocks]}
            else:
                return {"result": str(result)}

        except Exception as e:
            print(f"[MCP] Error calling {tool_name}: {e}")
            raise

    async def list_tools(self) -> list[MCPToolInfo]:
        """Get available tools."""
        return self._tools

    def __repr__(self) -> str:
        status = "connected" if self._session else "disconnected"
        return f"RealMCPServer(name={self.name}, status={status}, tools={len(self._tools)})"
```

### Krok 2: Zaktualizuj MCPRegistry

Edytuj `app/services/mcp.py`:

```python
"""MCP server registry supporting both mock and real servers."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, Protocol, runtime_checkable


@runtime_checkable
class MCPServerProtocol(Protocol):
    """Protocol for MCP server interface."""
    name: str

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute MCP tool."""
        ...

    async def list_tools(self) -> list:
        """List available tools."""
        ...


@dataclass(slots=True)
class MockMCPServer:
    """Mock MCP server for testing."""
    name: str
    endpoint: str

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Simulate tool execution."""
        await asyncio.sleep(0.1)
        return {
            "server": self.name,
            "tool": tool_name,
            "status": "ok",
            "arguments": arguments,
        }

    async def list_tools(self) -> list:
        """Return mock tools."""
        return [
            {"name": "echo", "description": "Echo arguments back"},
            {"name": "ping", "description": "Simple ping"},
        ]


class MCPRegistry:
    """Registry for MCP servers."""

    def __init__(self) -> None:
        self._servers: Dict[str, MCPServerProtocol] = {}

    def register(self, capability: str, server: MCPServerProtocol) -> None:
        """Register MCP server."""
        self._servers[capability] = server
        print(f"[Registry] Registered {capability} -> {server.name}")

    async def register_real(
        self,
        capability: str,
        name: str,
        command: str,
        args: list[str],
        env: dict | None = None,
    ) -> None:
        """Register and connect to real MCP server."""
        try:
            from app.services.mcp_client import RealMCPServer

            server = RealMCPServer(name, command, args, env)
            await server.connect()
            self._servers[capability] = server
            print(f"[Registry] Real MCP server registered: {capability}")

        except ImportError:
            print(f"[Registry] MCP SDK not available, using mock for {capability}")
            self._servers[capability] = MockMCPServer(name, f"mock://{capability}")

        except Exception as e:
            print(f"[Registry] Failed to register real MCP {capability}: {e}")
            print(f"[Registry] Falling back to mock for {capability}")
            self._servers[capability] = MockMCPServer(name, f"mock://{capability}")

    def get(self, capability: str) -> MCPServerProtocol:
        """Get MCP server by capability."""
        if capability not in self._servers:
            raise KeyError(f"No MCP server for: {capability}")
        return self._servers[capability]

    async def shutdown_all(self) -> None:
        """Disconnect all real MCP servers."""
        from app.services.mcp_client import RealMCPServer

        for capability, server in self._servers.items():
            if isinstance(server, RealMCPServer):
                try:
                    await server.disconnect()
                except Exception as e:
                    print(f"[Registry] Error disconnecting {capability}: {e}")

    def list_capabilities(self) -> list[str]:
        """Get all registered capabilities."""
        return list(self._servers.keys())
```

### Krok 3: Konfiguracja

Edytuj `app/config.py`:

```python
"""Configuration with MCP support."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MCPServerConfig:
    """Configuration for single MCP server."""
    enabled: bool
    command: str
    args: list[str]
    env: dict[str, str]


@dataclass(frozen=True)
class AzureOpenAIConfig:
    """Azure OpenAI configuration."""
    api_key: str
    endpoint: str
    api_version: str = "2024-02-15-preview"
    deployment_name: str = "gpt-4"
    max_concurrent: int = 50


@dataclass(frozen=True)
class Config:
    """Application configuration."""
    azure_openai: Optional[AzureOpenAIConfig] = None
    environment: str = "development"
    use_real_mcp: bool = False
    mcp_servers: dict[str, MCPServerConfig] = None

    @classmethod
    def from_env(cls) -> Config:
        """Load from environment variables."""
        # Azure OpenAI
        azure_key = os.getenv("AZURE_OPENAI_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_config = None

        if azure_key and azure_endpoint:
            azure_config = AzureOpenAIConfig(
                api_key=azure_key,
                endpoint=azure_endpoint,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
                max_concurrent=int(os.getenv("AZURE_OPENAI_MAX_CONCURRENT", "50")),
            )

        # MCP Servers
        use_real_mcp = os.getenv("MCP_USE_REAL", "false").lower() == "true"
        mcp_servers = {}

        if use_real_mcp:
            # Filesystem MCP
            if os.getenv("MCP_FILESYSTEM_ENABLED", "false").lower() == "true":
                args_str = os.getenv("MCP_FILESYSTEM_ARGS", "/tmp")
                mcp_servers["filesystem"] = MCPServerConfig(
                    enabled=True,
                    command=os.getenv("MCP_FILESYSTEM_COMMAND", "npx"),
                    args=["-y", "@modelcontextprotocol/server-filesystem"] + [args_str],
                    env={},
                )

            # Brave Search MCP
            if os.getenv("MCP_BRAVE_ENABLED", "false").lower() == "true":
                brave_key = os.getenv("MCP_BRAVE_API_KEY", "")
                mcp_servers["brave-search"] = MCPServerConfig(
                    enabled=True,
                    command=os.getenv("MCP_BRAVE_COMMAND", "npx"),
                    args=["-y", "@modelcontextprotocol/server-brave-search"],
                    env={"BRAVE_API_KEY": brave_key} if brave_key else {},
                )

        return cls(
            azure_openai=azure_config,
            environment=os.getenv("ENVIRONMENT", "development"),
            use_real_mcp=use_real_mcp,
            mcp_servers=mcp_servers or {},
        )


# Global config instance
config = Config.from_env()
```

### Krok 4: Runtime Setup

Edytuj `app/runtime.py` - dodaj async initialization:

```python
"""Runtime composition with async MCP initialization."""
from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Optional

from app.agents.echo import EchoAgent
from app.agents.llm_agent import LLMAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.config import config
from app.core.message_bus import A2AMessageBus
from app.core.models import AgentConfig, AgentDescriptor
from app.orchestration.orchestrator import Orchestrator
from app.services.llm_pool import LLMPool
from app.services.mcp import MCPRegistry, MockMCPServer

_AGENT_CATALOG = {
    "echo": EchoAgent,
    "llm": LLMAgent,
}

_ORCHESTRATOR_AGENT_ID: Optional[str] = None
_MCP_REGISTRY: Optional[MCPRegistry] = None


@lru_cache
def get_bus() -> A2AMessageBus:
    return A2AMessageBus()


async def initialize_mcp_registry() -> MCPRegistry:
    """Initialize MCP registry (async for real servers)."""
    global _MCP_REGISTRY

    if _MCP_REGISTRY:
        return _MCP_REGISTRY

    registry = MCPRegistry()

    if config.use_real_mcp and config.mcp_servers:
        # Register real MCP servers
        for capability, server_config in config.mcp_servers.items():
            if server_config.enabled:
                await registry.register_real(
                    capability=capability,
                    name=f"{capability}-mcp",
                    command=server_config.command,
                    args=server_config.args,
                    env=server_config.env,
                )
    else:
        # Fallback to mock
        print("[Runtime] Using mock MCP servers")
        registry.register("echo", MockMCPServer(name="echo-mcp", endpoint="mock://echo"))
        registry.register("filesystem", MockMCPServer(name="fs-mcp", endpoint="mock://fs"))

    _MCP_REGISTRY = registry
    return registry


def get_mcp_registry() -> MCPRegistry:
    """Get MCP registry (sync wrapper)."""
    if _MCP_REGISTRY is None:
        raise RuntimeError("MCP registry not initialized. Call initialize_mcp_registry() first.")
    return _MCP_REGISTRY


@lru_cache
def get_llm_pool() -> LLMPool:
    pool = LLMPool()

    if config.azure_openai:
        pool.register_azure_openai("gpt-4", config.azure_openai)
        pool.register_azure_openai("gpt-35-turbo", config.azure_openai)
    else:
        from app.services.llm_pool import MockLLMClient

        pool._clients["gpt-4"] = MockLLMClient("gpt-4")
        pool._clients["gpt-35-turbo"] = MockLLMClient("gpt-35-turbo")
        pool._semaphores["gpt-4"] = asyncio.Semaphore(50)
        pool._semaphores["gpt-35-turbo"] = asyncio.Semaphore(50)
        pool._initialized["gpt-4"] = True
        pool._initialized["gpt-35-turbo"] = True

    return pool


@lru_cache
def get_orchestrator() -> Orchestrator:
    orchestrator = Orchestrator(
        bus=get_bus(),
        mcp_registry=get_mcp_registry(),
        agent_catalog=_AGENT_CATALOG,
    )
    orchestrator.set_llm_pool(get_llm_pool())
    return orchestrator


async def initialize_orchestrator_agent() -> AgentDescriptor:
    """Initialize orchestrator agent (with MCP setup)."""
    global _ORCHESTRATOR_AGENT_ID

    # First initialize MCP registry
    await initialize_mcp_registry()

    orchestrator = get_orchestrator()
    llm_pool = get_llm_pool()
    bus = get_bus()

    config_obj = AgentConfig(
        name="orchestrator",
        role="orchestrator",
        mcp_server="echo",
        metadata={"model": "gpt-4"},
    )

    descriptor = AgentDescriptor(
        agent_id="orchestrator-agent",
        config=config_obj,
    )

    agent = OrchestratorAgent(
        descriptor=descriptor,
        bus=bus,
        orchestrator=orchestrator,
        llm_pool=llm_pool,
    )

    await agent.start()

    orchestrator._agents[descriptor.agent_id] = agent
    _ORCHESTRATOR_AGENT_ID = descriptor.agent_id

    return descriptor


def get_orchestrator_agent_id() -> str:
    """Get orchestrator agent ID."""
    if _ORCHESTRATOR_AGENT_ID is None:
        raise RuntimeError("Orchestrator agent not initialized")
    return _ORCHESTRATOR_AGENT_ID


def default_agent_config(name: str) -> AgentConfig:
    return AgentConfig(name=name, role="echo", mcp_server="echo")
```

### Krok 5: Zaktualizuj Main

Edytuj `app/main.py`:

```python
"""FastAPI with async MCP initialization."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router as agents_router
from app.api.sessions import router as sessions_router
from app.api.chat import router as chat_router
from app.runtime import get_orchestrator, initialize_orchestrator_agent, get_mcp_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle with MCP setup and teardown."""
    # Startup: Initialize MCP and orchestrator agent
    print("[App] Starting up...")
    await initialize_orchestrator_agent()
    print("[App] Startup complete")

    yield

    # Shutdown: Clean up
    print("[App] Shutting down...")
    orchestrator = get_orchestrator()
    await orchestrator.terminate_all()

    # Disconnect MCP servers
    registry = get_mcp_registry()
    await registry.shutdown_all()
    print("[App] Shutdown complete")


app = FastAPI(title="Agentic Orchestrator", lifespan=lifespan)
app.include_router(agents_router)
app.include_router(sessions_router)
app.include_router(chat_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/mcp/capabilities")
async def mcp_capabilities() -> dict:
    """List registered MCP capabilities."""
    registry = get_mcp_registry()
    capabilities = registry.list_capabilities()

    details = {}
    for cap in capabilities:
        server = registry.get(cap)
        tools = await server.list_tools()
        details[cap] = {
            "server": server.name,
            "tools": [
                {"name": t.name, "description": t.description}
                if hasattr(t, "name")
                else t
                for t in tools
            ],
        }

    return {"capabilities": details}
```

### Krok 6: Environment Config

Stwórz `.env.mcp`:

```env
# Enable Real MCP Servers
MCP_USE_REAL=true

# Filesystem MCP
MCP_FILESYSTEM_ENABLED=true
MCP_FILESYSTEM_COMMAND=npx
MCP_FILESYSTEM_ARGS=/tmp

# Brave Search MCP (optional)
MCP_BRAVE_ENABLED=false
MCP_BRAVE_COMMAND=npx
MCP_BRAVE_API_KEY=your-brave-api-key-here

# Azure OpenAI (optional)
AZURE_OPENAI_KEY=
AZURE_OPENAI_ENDPOINT=
```

## Testowanie

### Test 1: Sprawdź dostępne capabilities

```bash
# Start server
source .env.mcp
uvicorn app.main:app --reload

# Check MCP capabilities
curl http://localhost:8000/mcp/capabilities
```

Powinno zwrócić:
```json
{
  "capabilities": {
    "filesystem": {
      "server": "filesystem-mcp",
      "tools": [
        {"name": "read_file", "description": "Read file contents"},
        {"name": "write_file", "description": "Write file"},
        ...
      ]
    }
  }
}
```

### Test 2: Użyj MCP z agentem

Stwórz agenta używającego filesystem MCP:

```python
# tests/test_real_filesystem_mcp.py
import pytest
import os


@pytest.mark.skipif(
    not os.getenv("TEST_REAL_MCP"),
    reason="Real MCP tests disabled"
)
@pytest.mark.anyio
async def test_filesystem_mcp_integration():
    """Test agent using real filesystem MCP."""
    from app.runtime import initialize_mcp_registry, get_mcp_registry

    # Initialize MCP
    await initialize_mcp_registry()
    registry = get_mcp_registry()

    # Get filesystem server
    fs_server = registry.get("filesystem")

    # Test read file
    # First create test file
    test_file = "/tmp/mcp_test.txt"
    with open(test_file, "w") as f:
        f.write("Hello from MCP!")

    # Read via MCP
    result = await fs_server.execute(
        "read_file",
        {"path": test_file}
    )

    assert "Hello from MCP!" in str(result)

    # Cleanup
    os.remove(test_file)
```

Uruchom test:
```bash
TEST_REAL_MCP=true MCP_USE_REAL=true MCP_FILESYSTEM_ENABLED=true pytest tests/test_real_filesystem_mcp.py -v
```

## Troubleshooting

### Problem: "MCP SDK not installed"

```bash
pip install mcp anthropic-mcp-client
```

### Problem: "npx command not found"

```bash
# Install Node.js
# Ubuntu/Debian:
sudo apt install nodejs npm

# macOS:
brew install node
```

### Problem: MCP server nie startuje

Sprawdź logi:
```python
# Dodaj debug logging w app/services/mcp_client.py
print(f"[DEBUG] Starting MCP: {self.command} {self.args}")
print(f"[DEBUG] Environment: {self.env}")
```

### Problem: Timeout podczas połączenia

Zwiększ timeout w `mcp_client.py`:
```python
# W stdio_client() może być domyślny timeout
# Sprawdź dokumentację MCP SDK dla opcji timeout
```

## Co dalej?

Po pomyślnym uruchomieniu filesystem MCP:

1. **Dodaj więcej serwerów MCP**:
   - Brave Search
   - GitHub
   - Slack
   - Custom MCP server

2. **Stwórz agenta wykorzystującego MCP**:
   ```python
   # app/agents/researcher.py
   class ResearcherAgent(Agent):
       async def handle_message(self, message: A2AMessage):
           query = message.payload.get("query")
           # Use brave-search MCP
           mcp = self._orchestrator.resolve_mcp("brave-search")
           results = await mcp.execute("search", {"query": query})
           # Process and send back
   ```

3. **Zaktualizuj dokumentację**:
   - Dodaj do `docs/mcp-integration.md`
   - Przykłady użycia dla każdego MCP
   - Best practices

Powodzenia! 🚀
