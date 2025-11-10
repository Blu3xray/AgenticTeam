"""LLM client pool for shared model access with concurrency control."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

from app.config import AzureOpenAIConfig


class LLMPool:
    """Manages shared LLM clients with concurrency limiting."""

    def __init__(self) -> None:
        self._clients: Dict[str, Any] = {}
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._initialized: Dict[str, bool] = {}

    def register_azure_openai(self, name: str, config: AzureOpenAIConfig) -> None:
        """Register an Azure OpenAI model configuration."""
        self._clients[name] = config
        self._semaphores[name] = asyncio.Semaphore(config.max_concurrent)
        self._initialized[name] = False

    @asynccontextmanager
    async def acquire(self, model_name: str) -> AsyncIterator[Any]:
        """Acquire access to a model client with concurrency control."""
        if model_name not in self._clients:
            raise KeyError(f"Model '{model_name}' not registered in LLM pool")

        semaphore = self._semaphores[model_name]
        await semaphore.acquire()

        try:
            # Lazy initialization on first use
            if not self._initialized[model_name]:
                await self._initialize_client(model_name)

            yield self._clients[model_name]
        finally:
            semaphore.release()

    async def _initialize_client(self, model_name: str) -> None:
        """Lazy initialization of the actual client."""
        config = self._clients[model_name]

        if isinstance(config, AzureOpenAIConfig):
            try:
                from openai import AsyncAzureOpenAI

                client = AsyncAzureOpenAI(
                    api_key=config.api_key,
                    api_version=config.api_version,
                    azure_endpoint=config.endpoint,
                )
                self._clients[model_name] = client
                self._initialized[model_name] = True
            except ImportError:
                # Fallback to mock if openai not installed
                self._clients[model_name] = MockLLMClient(model_name)
                self._initialized[model_name] = True
        else:
            self._initialized[model_name] = True


class MockLLMClient:
    """Mock LLM client for testing without real API."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    class ChatCompletions:
        def __init__(self, model_name: str):
            self.model_name = model_name

        async def create(self, **kwargs):
            """Simulate a completion response."""
            messages = kwargs.get("messages", [])
            user_message = next(
                (m["content"] for m in messages if m["role"] == "user"), ""
            )

            class MockChoice:
                class Message:
                    content = f"Mock response from {self.model_name}: I received '{user_message}'"
                    role = "assistant"

                message = Message()
                finish_reason = "stop"

            class MockResponse:
                choices = [MockChoice()]
                model = self.model_name

            await asyncio.sleep(0.1)  # Simulate API latency
            return MockResponse()

    @property
    def chat(self):
        class Chat:
            completions = MockLLMClient.ChatCompletions(self.model_name)

        return Chat()
