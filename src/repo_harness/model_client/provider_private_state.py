"""Runtime-only provider private state helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from repo_harness.model_client.redaction import (
    REDACTED_CREDENTIAL,
    REDACTED_REASONING,
    sanitize_provider_error_message,
)
from repo_harness.trajectory import ArtifactRef, RunRecorder

DEEPSEEK_PRIVATE_FORMAT_VERSION = "repo_harness_deepseek_provider_private_v0"


@dataclass(frozen=True)
class DeepSeekReasoningState:
    state_id: str
    run_id: str
    model_call_id: str
    reasoning_content: str


class ProviderPrivateStateStore:
    """Process-local live state store for provider replay fields.

    The store deliberately keeps live reasoning outside AgentLoop messages,
    prepared messages and training exports. Artifacts only receive redacted
    summaries that prove the state existed and how it may be replayed.
    """

    def __init__(self) -> None:
        self._deepseek_reasoning_by_id: dict[str, DeepSeekReasoningState] = {}

    def put_deepseek_reasoning(
        self,
        *,
        run_id: str,
        model_call_id: str,
        reasoning_content: str,
    ) -> DeepSeekReasoningState:
        state_id = f"{run_id}_{model_call_id}_deepseek_reasoning"
        state = DeepSeekReasoningState(
            state_id=state_id,
            run_id=run_id,
            model_call_id=model_call_id,
            reasoning_content=reasoning_content,
        )
        self._deepseek_reasoning_by_id[state_id] = state
        return state

    def get_deepseek_reasoning(self, state_id: str) -> str | None:
        state = self._deepseek_reasoning_by_id.get(state_id)
        return state.reasoning_content if state is not None else None

    def clear_run(self, run_id: str) -> None:
        for state_id, state in list(self._deepseek_reasoning_by_id.items()):
            if state.run_id == run_id:
                self._deepseek_reasoning_by_id.pop(state_id, None)


_GLOBAL_PROVIDER_PRIVATE_STATE_STORE = ProviderPrivateStateStore()


def provider_private_state_store() -> ProviderPrivateStateStore:
    return _GLOBAL_PROVIDER_PRIVATE_STATE_STORE


def capture_deepseek_reasoning_state(
    *,
    run_id: str,
    model_call_id: str,
    reasoning_content: str,
    replay_required: bool,
    reasoning_trace_training_allowed: bool = False,
    recorder: RunRecorder,
) -> dict[str, Any]:
    """Store live DeepSeek reasoning and return a safe metadata handle."""

    state = provider_private_state_store().put_deepseek_reasoning(
        run_id=run_id,
        model_call_id=model_call_id,
        reasoning_content=reasoning_content,
    )
    redacted_ref = recorder.write_json_artifact(
        "deepseek_provider_private_state",
        {
            "schema_version": DEEPSEEK_PRIVATE_FORMAT_VERSION,
            "provider": "deepseek",
            "state_id": state.state_id,
            "reasoning_content": REDACTED_REASONING,
            "reasoning_content_present": True,
            "reasoning_content_required_for_replay": replay_required,
            "export_allowed": False,
            "default_training_payload_allowed": False,
            "training_payload_allowed": False,
            "reasoning_trace_training_payload_allowed": (
                "explicit_opt_in_only" if reasoning_trace_training_allowed else False
            ),
            "public_demo_allowed": False,
            "live_state_persisted_in_prepared_messages": False,
        },
        {
            "redaction_status": "redacted",
            "retention_policy": "provider_private_state_redacted",
            "budget_policy": "preserve_json",
        },
    )
    if reasoning_trace_training_allowed:
        recorder.write_json_artifact(
            "deepseek_provider_reasoning_trace",
            {
                "schema_version": "repo_harness_provider_reasoning_trace_training_source_v0",
                "provider": "deepseek",
                "state_id": state.state_id,
                "run_id": run_id,
                "model_call_id": model_call_id,
                "target_kind": "provider_reasoning_trace",
                "reasoning_content": reasoning_content,
                "reasoning_trace_training_allowed": True,
                "ordinary_sft_target_allowed": False,
                "default_training_payload_allowed": False,
                "not_public_safe_by_default": True,
                "public_demo_allowed": False,
                "requires_explicit_reasoning_export_policy": True,
                "raw_provider_artifact": False,
                "redacted_state_ref": redacted_ref.model_dump(mode="json"),
            },
            {
                "redaction_status": "not_redacted_explicit_reasoning_trace_opt_in",
                "retention_policy": "provider_reasoning_trace_training_opt_in",
                "budget_policy": "preserve_json",
            },
        )
    return {
        "format_version": DEEPSEEK_PRIVATE_FORMAT_VERSION,
        "state_id": state.state_id,
        "redacted_state_ref": redacted_ref.model_dump(mode="json"),
        "reasoning_content_present": True,
        "reasoning_content_required_for_replay": replay_required,
        "export_allowed": False,
        "default_training_payload_allowed": False,
        "training_payload_allowed": False,
        "reasoning_trace_training_payload_allowed": (
            "explicit_opt_in_only" if reasoning_trace_training_allowed else False
        ),
        "public_demo_allowed": False,
        "live_state_persisted_in_prepared_messages": False,
    }


def sanitize_provider_private_metadata_for_messages(metadata: dict[str, Any]) -> dict[str, Any]:
    """Keep provider private handles but remove live reasoning-like values."""

    if not metadata:
        return {}
    sanitized = _sanitize_metadata_value(metadata)
    return sanitized if isinstance(sanitized, dict) else {}


def deepseek_reasoning_from_metadata(metadata: Any) -> tuple[str | None, bool]:
    """Return live reasoning content and whether replay was required."""

    if not isinstance(metadata, dict):
        return None, False
    provider_private = metadata.get("provider_private")
    if not isinstance(provider_private, dict):
        return None, False
    deepseek = provider_private.get("deepseek")
    if not isinstance(deepseek, dict):
        return None, False
    state_id = deepseek.get("state_id")
    required = bool(deepseek.get("reasoning_content_required_for_replay"))
    if not isinstance(state_id, str) or not state_id:
        return None, required
    return provider_private_state_store().get_deepseek_reasoning(state_id), required


def _drop_live_provider_private_fields(value: Any) -> Any:
    return _sanitize_metadata_value(value)


def _sanitize_metadata_value(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, nested in value.items():
            lowered = str(key).lower().replace("-", "_")
            if lowered in {
                "reasoning_content",
                "encrypted_content",
                "live_state",
                "ordered_output_items",
            }:
                continue
            if _metadata_secret_key(lowered):
                result[key] = REDACTED_CREDENTIAL
            else:
                result[key] = _sanitize_metadata_value(nested)
        return result
    if isinstance(value, list):
        return [_sanitize_metadata_value(item) for item in value]
    if isinstance(value, str):
        return sanitize_provider_error_message(value)
    return value


def _metadata_secret_key(lowered_key: str) -> bool:
    if any(marker in lowered_key for marker in ("api_key", "apikey", "authorization", "password", "secret")):
        return True
    return lowered_key == "token" or lowered_key.endswith("_token")
