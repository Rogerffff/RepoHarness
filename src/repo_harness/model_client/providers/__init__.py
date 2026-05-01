"""Real provider adapters."""

from repo_harness.model_client.providers.deepseek import DeepSeekProviderClient
from repo_harness.model_client.providers.openai import OpenAIProviderClient

__all__ = [
    "DeepSeekProviderClient",
    "OpenAIProviderClient",
]
