# Getting Started

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- (Optional) Azure OpenAI account for production LLM features

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Blu3xray/AgenticTeam.git
cd AgenticTeam
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -e .[dev]
```

This installs:
- FastAPI and Uvicorn (API server)
- Pytest and AnyIO (testing)
- Optional: openai package (if you have Azure OpenAI)

## Configuration

### Option 1: Run with Mock LLM (No API Keys Required)

The project works out-of-the-box with mock responses. Just skip to "Running the Application".

### Option 2: Configure Azure OpenAI (Production)

#### Using Environment Variables

```bash
export AZURE_OPENAI_KEY="your-azure-openai-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4"
```

#### Using .env File (Recommended for Development)

```bash
# 1. Copy the example file
cp .env.example .env

# 2. Edit .env and add your credentials
nano .env  # or use your preferred editor
```

Edit `.env`:
```env
AZURE_OPENAI_KEY=your-actual-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

```bash
# 3. Install python-dotenv to auto-load .env
pip install python-dotenv
```

## Running the Application

### Start the API Server

```bash
uvicorn app.main:app --reload
```

Output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Verify It's Running

Open browser: http://localhost:8000/health

Or with curl:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok"}
```

## First Steps

### 1. Chat with the Orchestrator

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a new LLM agent",
    "session_id": "my-session"
  }'
```

Response (with mock LLM):
```json
{
  "response": "Created llm agent: abc-123-def",
  "action": "create_agent",
  "details": {
    "agent_id": "abc-123-def",
    "name": "agent-1",
    "role": "llm"
  },
  "session_id": "my-session"
}
```

### 2. List Your Agents

```bash
curl http://localhost:8000/sessions/my-session/agents
```

### 3. Create Agent Directly (Without Chat)

```bash
curl -X POST http://localhost:8000/sessions/my-session/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-assistant",
    "role": "llm",
    "mcp_server": "echo",
    "metadata": {
      "model": "gpt-4",
      "temperature": 0.7
    }
  }'
```

### 4. Send Message to an Agent

```bash
curl -X POST http://localhost:8000/agents/{agent_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "user-123",
    "payload": {
      "prompt": "Hello, how are you?"
    }
  }'
```

## Running Tests

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_chat.py -v
```

Expected output:
```
================================ test session starts =================================
collected 4 items

tests/test_chat.py::test_orchestrator_agent_creates_new_agent PASSED           [ 25%]
tests/test_chat.py::test_session_isolation PASSED                              [ 50%]
tests/test_orchestrator.py::test_spawn_and_terminate_agent PASSED              [ 75%]
tests/test_orchestrator.py::test_agent_handles_message_roundtrip PASSED        [100%]

================================= 4 passed in 2.66s ==================================
```

## Interactive API Documentation

FastAPI provides automatic interactive docs:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

You can test all endpoints directly from the browser!

## Troubleshooting

### Import Errors

```bash
# Make sure you're in the virtual environment
which python  # Should show .venv/bin/python

# Reinstall dependencies
pip install -e .[dev]
```

### Port Already in Use

```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
```

### Azure OpenAI Errors

If you see "Model 'gpt-4' not registered in LLM pool":
- Check your `.env` file has correct credentials
- Verify `AZURE_OPENAI_KEY` and `AZURE_OPENAI_ENDPOINT` are set
- Try running with mock: unset the environment variables and restart

### Mock vs Real LLM

**Mock LLM** (no API keys):
- Returns: `"Mock response from gpt-4: I received '...'"`
- Perfect for development and testing

**Real LLM** (with Azure OpenAI keys):
- Returns: Actual GPT-4 responses
- Requires valid Azure OpenAI subscription

## Next Steps

- Read [Chat Interface Documentation](chat-interface.md) for advanced usage
- See [Architecture](architecture.md) to understand the system
- Check [Extension Guide](extension-guide.md) to add new features
- Review [Azure Deployment](azure-deployment.md) for production deployment

## Quick Reference

```bash
# Start server
uvicorn app.main:app --reload

# Chat with orchestrator
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "list my agents", "session_id": "demo"}'

# Health check
curl http://localhost:8000/health

# Run tests
python -m pytest

# API docs
open http://localhost:8000/docs
```
