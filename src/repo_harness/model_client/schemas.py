"""模型消息、模型响应、模型调用事件和 replay script schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import MODEL_CLIENT_PROTOCOL_VERSION, REPLAY_SCRIPT_SCHEMA_VERSION
from repo_harness.run_metadata import RunConfigFactsRef
from repo_harness.tools.schemas import ToolCall
from repo_harness.trajectory import ArtifactRef

SHA256_PATTERN = r"^[0-9a-f]{64}$"


class ModelMessage(StrictBaseModel):
    schema_version: str = "repo_harness_model_message_v0"
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderCredentialPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_provider_credential_policy_v0"
    credential_source: str = "env_only"
    required_env_vars: list[str] = Field(default_factory=list)
    redact_request_headers: bool = True
    redact_provider_response: bool = True
    secret_scan_policy: str = "default"
    local_secret_file_policy: str = "disabled"
    credential_source_label: str | None = None


class ModelProviderOptions(StrictBaseModel):
    schema_version: str = "repo_harness_model_provider_options_v2_v0"
    provider: str
    model_id: str
    endpoint_category: str = "default"
    credential_policy: ProviderCredentialPolicy = Field(default_factory=ProviderCredentialPolicy)
    provider_specific_options: dict[str, Any] = Field(default_factory=dict)


class ModelRequestContext(StrictBaseModel):
    schema_version: str = MODEL_CLIENT_PROTOCOL_VERSION
    run_id: str
    task_id: str
    turn: int = Field(ge=0)
    model_call_id: str
    prepared_messages: list[dict[str, Any]]
    prepared_messages_ref: ArtifactRef
    model_input_hash: str = Field(pattern=SHA256_PATTERN)
    context_revision: int = Field(ge=0)
    provider_message_format: str
    context_truncation_facts: dict[str, Any]
    omitted_context_facts: dict[str, Any]
    generation_config: dict[str, Any]
    provider_model_settings: dict[str, Any]
    allowed_tool_definitions: list[dict[str, Any]]
    tool_choice: str | dict[str, Any] | None = None
    tool_schema_snapshot_ref: ArtifactRef
    provider_options: ModelProviderOptions
    scaffold_id: str
    scaffold_phase: str
    run_config_facts_ref: RunConfigFactsRef
    budget_state: dict[str, Any]
    request_timeout_seconds: float = Field(gt=0)
    raw_request_logging_policy: str
    credential_policy: ProviderCredentialPolicy
    retry_policy: str


class ModelGenerationRequest(StrictBaseModel):
    schema_version: str = "repo_harness_model_generation_request_v2_v0"
    protocol_version: str = MODEL_CLIENT_PROTOCOL_VERSION
    context: ModelRequestContext
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    provider_options: ModelProviderOptions


class ModelCallEvent(StrictBaseModel):
    schema_version: str = "repo_harness_model_call_event_v0"
    model_call_id: str
    model_id: str
    provider_request_id: str | None = None
    context_revision: int = Field(ge=0)
    prepared_messages_ref: ArtifactRef
    model_input_hash: str
    provider_message_format: str
    tool_schema_hash: str
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    model_error_type: str | None = None


class ModelResponse(StrictBaseModel):
    schema_version: str = "repo_harness_model_response_v0"
    assistant_message: ModelMessage
    tool_calls: list[ToolCall] = Field(default_factory=list)
    raw_provider_request_ref: ArtifactRef | None = None
    raw_provider_response_ref: ArtifactRef | None = None
    token_usage: dict[str, int] = Field(default_factory=dict)
    finish_reason: str | None = None
    model_error_type: str | None = None
    provider_request_id: str | None = None
    model_call_event: ModelCallEvent | None = None


class ToolCallParseResult(StrictBaseModel):
    schema_version: str = "repo_harness_tool_call_parse_result_v0"
    parser_id: str = "repo_harness_tool_call_parser_v0"
    success: bool
    tool_calls: list[ToolCall] = Field(default_factory=list)
    parse_error_type: str | None = None
    recoverable: bool = False
    duplicate_tool_call_ids: list[str] = Field(default_factory=list)
    missing_tool_call_ids: int = Field(default=0, ge=0)
    malformed_tool_call_count: int = Field(default=0, ge=0)


class ReplayStep(StrictBaseModel):
    schema_version: str = REPLAY_SCRIPT_SCHEMA_VERSION
    step_id: str
    action: Literal["assistant", "tool_call", "final_answer", "model_error"]
    assistant_text: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    model_error_type: str | None = None
    expected_outcome: dict[str, Any] | None = None
    comment: str | None = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "ReplayStep":
        if self.action == "tool_call":
            if not self.tool_call_id or not self.tool_name or self.arguments is None:
                raise ValueError("tool_call replay step 必须包含 tool_call_id、tool_name 和 arguments。")
        if self.action == "final_answer" and not self.assistant_text:
            raise ValueError("final_answer replay step 必须包含 assistant_text。")
        if self.action == "model_error" and not self.model_error_type:
            raise ValueError("model_error replay step 必须包含 model_error_type。")
        return self

    def model_visible_payload(self) -> dict[str, Any]:
        """返回 ReplayModelClient 可以模拟给 Agent Loop 的内容，不包含评测答案。"""

        payload: dict[str, Any] = {
            "step_id": self.step_id,
            "action": self.action,
            "assistant_text": self.assistant_text,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "model_error_type": self.model_error_type,
        }
        return {key: value for key, value in payload.items() if value is not None}


class ReplayScript(StrictBaseModel):
    schema_version: str = REPLAY_SCRIPT_SCHEMA_VERSION
    script_id: str
    task_id: str
    steps: list[ReplayStep] = Field(min_length=1)
    expected_outcome: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_visible_steps(self) -> list[dict[str, Any]]:
        """返回不包含 expected_outcome、注释和测试专用 metadata 的 replay 步骤。"""

        return [step.model_visible_payload() for step in self.steps]
