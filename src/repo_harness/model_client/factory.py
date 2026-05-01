"""Model client factory."""

from __future__ import annotations

from repo_harness.config import ModelConfig
from repo_harness.errors import ConfigError
from repo_harness.model_client.fake import FakeModelClient
from repo_harness.model_client.mock import MockProviderClient
from repo_harness.model_client.protocol import ModelClient
from repo_harness.model_client.providers import DeepSeekProviderClient, OpenAIProviderClient
from repo_harness.model_client.providers.deepseek import (
    DEEPSEEK_DEFAULT_BASE_URL,
    normalize_deepseek_model_id,
)
from repo_harness.model_client.replay import ReplayModelClient
from repo_harness.model_client.schemas import ModelProviderOptions, ProviderCredentialPolicy


def create_model_client(model_config: ModelConfig) -> ModelClient:
    """Build a model client for providers supported by the current implementation."""

    if model_config.provider == "replay":
        if model_config.replay_script_path is None:
            raise ConfigError("model.provider=replay 需要 model.replay_script_path。")
        return ReplayModelClient.from_path(model_config.replay_script_path)
    if model_config.provider == "fake":
        if model_config.replay_script_path is None:
            raise ConfigError("model.provider=fake 需要 model.replay_script_path。")
        return FakeModelClient.from_path(model_config.replay_script_path)
    if model_config.provider == "mock":
        return MockProviderClient()
    if model_config.provider == "deepseek":
        return DeepSeekProviderClient.from_options(
            model_id=normalize_deepseek_model_id(model_config.model_id),
            base_url=str(
                model_config.provider_specific_options.get("base_url")
                or DEEPSEEK_DEFAULT_BASE_URL
            ),
            allow_local_secret_file=bool(
                model_config.provider_specific_options.get("allow_local_secret_file", False)
            ),
        )
    if model_config.provider == "openai":
        if not _is_openai_fallback_options(model_config.provider_specific_options):
            raise ConfigError(
                "model.provider=openai 只允许作为 DeepSeek fallback smoke run；"
                "请记录 requested_provider=deepseek、actual_provider=openai、fallback_reason "
                "和 fallback_policy_version。"
            )
        return OpenAIProviderClient.from_options(model_id=model_config.model_id)
    raise ConfigError(
        "Stage 11 支持 model.provider=replay、fake、mock、deepseek；"
        "openai 只允许作为 DeepSeek fallback 内部运行；"
        f"收到 {model_config.provider!r}。"
    )


def provider_options_from_model_config(model_config: ModelConfig) -> ModelProviderOptions:
    credential_policy = ProviderCredentialPolicy(
        credential_source=model_config.credential_policy,
        required_env_vars=_required_env_vars(model_config.provider),
        credential_source_label=model_config.credential_policy,
    )
    return ModelProviderOptions(
        provider=model_config.provider,
        model_id=model_config.model_id,
        credential_policy=credential_policy,
        provider_specific_options={
            "temperature": model_config.temperature,
            "max_output_tokens": model_config.max_output_tokens,
            **model_config.provider_specific_options,
        },
    )


def _required_env_vars(provider: str) -> list[str]:
    if provider == "deepseek":
        return ["DEEPSEEK_API_KEY"]
    if provider == "openai":
        return ["OPENAI_API_KEY"]
    return []


def _is_openai_fallback_options(options: dict[str, object]) -> bool:
    return (
        options.get("requested_provider") == "deepseek"
        and options.get("actual_provider") == "openai"
        and bool(options.get("fallback_reason"))
        and bool(options.get("fallback_policy_version"))
    )
