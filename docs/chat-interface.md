# Chat Interface

## Overview

The chat interface allows you to interact with the orchestrator using natural language to manage agents dynamically.

## How It Works

1. **OrchestratorAgent** – A meta-agent that understands user requests using LLM
2. **Natural Language Processing** – Interprets commands like "create agent", "list agents", "terminate agent"
3. **Action Execution** – Spawns/terminates agents based on interpreted intent
4. **Response Generation** – Returns human-readable status and details

## Example Usage

### Create an Agent

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a new LLM agent for customer support",
    "session_id": "user-123"
  }'
```

Response:
```json
{
  "response": "Created llm agent: abc-123-def",
  "action": "create_agent",
  "details": {
    "agent_id": "abc-123-def",
    "name": "agent-1",
    "role": "llm"
  },
  "session_id": "user-123"
}
```

### List Active Agents

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me all my agents",
    "session_id": "user-123"
  }'
```

Response:
```json
{
  "response": "Found 2 active agents in this session",
  "action": "list_agents",
  "details": {
    "agents": [
      {"id": "abc-123", "name": "agent-1", "role": "llm", "state": "RUNNING"},
      {"id": "def-456", "name": "agent-2", "role": "echo", "state": "RUNNING"}
    ]
  },
  "session_id": "user-123"
}
```

### Terminate an Agent

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Delete agent abc-123",
    "session_id": "user-123"
  }'
```

## Supported Commands

- **Create agents:** "create llm agent", "spawn new echo agent", "make an agent"
- **List agents:** "show my agents", "list all agents", "what agents are running"
- **Terminate:** "delete agent abc-123", "remove all agents", "terminate agent"

## Session Isolation

Each `session_id` creates an isolated workspace:
- Agents in one session cannot see agents in another
- Terminating a session removes all its agents
- Perfect for multi-tenant scenarios

## Architecture

```
User Request
    ↓
POST /chat
    ↓
A2AMessage → OrchestratorAgent
    ↓
LLM interprets request
    ↓
Orchestrator.spawn_agent() / terminate_agent()
    ↓
Response → User
```

## Configuration

OrchestratorAgent uses the model specified in config:
```python
# app/config.py
AZURE_OPENAI_DEPLOYMENT = "gpt-4"  # Default model for orchestrator
```

If Azure OpenAI is not configured, falls back to mock responses.

## Error Handling

- **Timeout:** 30 seconds wait for orchestrator response
- **Unknown request:** Returns "I didn't understand that request"
- **Invalid agent_id:** Returns error message in response
