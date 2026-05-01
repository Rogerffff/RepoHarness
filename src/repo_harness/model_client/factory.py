"""Model client factory for stage seven providers."""

from __future__ import annotations

from repo_harness.config import ModelConfig
from repo_harness.errors import ConfigError
from repo_harness.model_client.fake import FakeModelClient
from repo_harness.model_client.protocol import ModelClient
from repo_harness.model_client.replay import ReplayModelClient
from repo_harness.model_client.schemas import ModelProviderOptions, ProviderCredentialPolicy


def create_model_client(model_config: ModelConfig) -> ModelClient:
    """Build a model client for providers supported before real-provider stages."""

    if model_config.provider == "replay":
        if model_config.replay_script_path is None:
            raise ConfigError("model.provider=replay 需要 model.replay_script_path。")
        return ReplayModelClient.from_path(model_config.replay_script_path)
    if model_config.provider == "fake":
        if model_config.replay_script_path is None:
            raise ConfigError("model.provider=fake 需要 model.replay_script_path。")
        return FakeModelClient.from_path(model_config.replay_script_path)
    raise ConfigError(
        "Stage 07 只支持 model.provider=replay 或 model.provider=fake；"
        f"收到 {model_config.provider!r}。"
    )


def provider_options_from_model_config(model_config: ModelConfig) -> ModelProviderOptions:
    credential_policy = ProviderCredentialPolicy(
        credential_source=model_config.credential_policy,
        required_env_vars=[],
        credential_source_label=model_config.credential_policy,
    )
    return ModelProviderOptions(
        provider=model_config.provider,
        model_id=model_config.model_id,
        credential_policy=credential_policy,
        provider_specific_options={
            "temperature": model_config.temperature,
            "max_output_tokens": model_config.max_output_tokens,
        },
    )
