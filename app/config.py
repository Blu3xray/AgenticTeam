"""Configuration management for the orchestrator."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AzureOpenAIConfig:
    """Azure OpenAI service configuration."""

    api_key: str
    endpoint: str
    api_version: str = "2024-02-15-preview"
    deployment_name: str = "gpt-4"
    max_concurrent: int = 50


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables."""

    azure_openai: Optional[AzureOpenAIConfig] = None
    environment: str = "development"

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables."""
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

        return cls(
            azure_openai=azure_config,
            environment=os.getenv("ENVIRONMENT", "development"),
        )


# Global config instance
config = Config.from_env()
