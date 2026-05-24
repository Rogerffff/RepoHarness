"""Stage 16C public environment context for model-visible prompts."""

from __future__ import annotations

import json
import re
from typing import Any, Literal, Mapping

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel, stable_hash
from repo_harness.tasks.schemas import RunnableTask
from repo_harness.trajectory import ArtifactRef, RunRecorder

PUBLIC_ENVIRONMENT_CONTEXT_VERSION = "repo_harness_public_environment_context_stage16c_v0"
PUBLIC_ENVIRONMENT_PROMPT_KIND = "public_environment_prompt_block"
PUBLIC_ENVIRONMENT_CONTEXT_KIND = "public_environment_context"

PublicTestEntryStatus = Literal["available", "unavailable", "disabled"]
PublicTestToolName = Literal["run_tests", "run_public_tests"]

_SAFE_COMMAND_TEMPLATE_LABELS = {
    "configured_public_feedback",
    "structured_public_feedback",
    "public_tests_disabled",
    "public_tests_unavailable",
}
_SAFE_FORBIDDEN_GUESS_CATEGORIES = {
    "host_absolute_paths",
    "non_public_runtime_artifacts",
    "non_public_evaluation_materials",
    "ad_hoc_dependency_installation",
    "git_history_or_metadata",
}
_MODEL_VISIBLE_FORBIDDEN_SUBSTRINGS = (
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "gold_patch",
    "gold patch",
    "test_patch",
    "test patch",
    "hidden_verifier",
    "hidden verifier",
    "official_verifier_result",
    "official selector",
    "accepted_label",
    "reward_metadata",
    "reward_extra_info",
    "provider_secret",
    "repo-harness-run",
    "runtime_private",
    ".repo_harness_runtime",
    ".repo_harness_env_overlay",
    "/workspace",
    "/testbed",
    "/Users/",
    "/private/",
    "/root/",
    "/home/",
    "conda activate",
    "pip install -e",
    "python setup.py develop",
)
_ABSOLUTE_PATH_PATTERN = re.compile(r"(^|[^A-Za-z0-9_.-])/(Users|private|workspace|testbed|root|home|tmp|var)/")


class PublicEnvironmentVisibilityError(ValueError):
    """Raised when public environment facts would cross a model-visible boundary."""


class PublicTestEntry(StrictBaseModel):
    """模型可见的公开测试入口事实。"""

    status: PublicTestEntryStatus
    tool_name: PublicTestToolName | None = None
    feedback_policy: str
    model_visible_summary: str
    command_template_label: str | None = None
    non_public_feedback_visible: bool = False
    unavailable_reason: str | None = None

    @model_validator(mode="after")
    def validate_public_test_entry(self) -> "PublicTestEntry":
        if self.status == "available":
            if self.tool_name not in {"run_tests", "run_public_tests"}:
                raise ValueError("available public test entry requires a public test tool")
            if self.command_template_label not in _SAFE_COMMAND_TEMPLATE_LABELS:
                raise ValueError("available public test entry requires a safe command template label")
        else:
            if self.tool_name is not None:
                raise ValueError("unavailable or disabled public test entry must not expose a tool")
        if self.command_template_label is not None:
            _validate_safe_label(self.command_template_label, field_name="command_template_label")
        _validate_model_visible_text(self.model_visible_summary, field_name="model_visible_summary")
        if self.unavailable_reason is not None:
            _validate_safe_label(self.unavailable_reason, field_name="unavailable_reason")
        return self

    def model_visible_payload(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload.pop("non_public_feedback_visible", None)
        if payload.get("feedback_policy") == "oracle_hidden_feedback":
            payload["feedback_policy"] = "non_public_feedback_configured"
        return payload


class PublicEnvironmentContext(StrictBaseModel):
    """模型可见公开环境上下文和审计 digest。"""

    schema_version: str = PUBLIC_ENVIRONMENT_CONTEXT_VERSION
    context_version: str = PUBLIC_ENVIRONMENT_CONTEXT_VERSION
    workspace_semantics: str
    default_cwd_label: str
    path_policy_summary: str
    preferred_tool_order: list[str] = Field(default_factory=list)
    public_test_entry: PublicTestEntry
    dependency_policy_summary: str
    diagnostic_shell_summary: str
    forbidden_environment_guess_categories: list[str] = Field(default_factory=list)
    model_visible_prompt_block: str
    context_digest: str

    @model_validator(mode="after")
    def validate_context(self) -> "PublicEnvironmentContext":
        payload = self._digest_payload()
        expected_digest = stable_hash(payload)
        if self.context_digest != expected_digest:
            raise ValueError("public environment context digest mismatch")
        validate_public_environment_model_visible_payload(self.model_visible_payload())
        return self

    @classmethod
    def build(
        cls,
        *,
        workspace_semantics: str,
        default_cwd_label: str,
        path_policy_summary: str,
        preferred_tool_order: list[str],
        public_test_entry: PublicTestEntry,
        dependency_policy_summary: str,
        diagnostic_shell_summary: str,
        forbidden_environment_guess_categories: list[str],
        model_visible_prompt_block: str,
    ) -> "PublicEnvironmentContext":
        for category in forbidden_environment_guess_categories:
            if category not in _SAFE_FORBIDDEN_GUESS_CATEGORIES:
                raise ValueError(f"unsafe forbidden environment guess category: {category}")
        payload = {
            "schema_version": PUBLIC_ENVIRONMENT_CONTEXT_VERSION,
            "context_version": PUBLIC_ENVIRONMENT_CONTEXT_VERSION,
            "workspace_semantics": workspace_semantics,
            "default_cwd_label": default_cwd_label,
            "path_policy_summary": path_policy_summary,
            "preferred_tool_order": list(preferred_tool_order),
            "public_test_entry": public_test_entry.model_dump(mode="json"),
            "dependency_policy_summary": dependency_policy_summary,
            "diagnostic_shell_summary": diagnostic_shell_summary,
            "forbidden_environment_guess_categories": list(forbidden_environment_guess_categories),
            "model_visible_prompt_block": model_visible_prompt_block,
        }
        return cls(**payload, context_digest=stable_hash(payload))

    def _digest_payload(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload.pop("context_digest", None)
        return payload

    def model_visible_payload(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload.pop("schema_version", None)
        payload["public_test_entry"] = self.public_test_entry.model_visible_payload()
        return payload

    def batch_projection(self) -> dict[str, str]:
        """Return the only fields allowed to travel through training batch metadata."""

        return _validate_batch_projection(
            {
                "repo_harness_public_environment_context_digest": self.context_digest,
                "repo_harness_public_test_entry_status": self.public_test_entry.status,
                "repo_harness_public_test_tool_strategy": (
                    "run_tests_only"
                    if self.public_test_entry.tool_name in {None, "run_tests"}
                    else "run_public_tests_alias"
                ),
            }
        )


def build_public_environment_context(
    *,
    task: RunnableTask,
    resolved_verifier_plan: Any,
    test_feedback_policy: str,
    allowed_tools: list[str],
) -> PublicEnvironmentContext:
    """Build the Stage 16C public environment context from trusted runtime facts."""

    public_test_entry = _build_public_test_entry(
        test_feedback_policy=test_feedback_policy,
        allowed_tools=allowed_tools,
    )
    preferred_tool_order = [
        tool
        for tool in (
            "read_file",
            "grep",
            "list_files",
            "glob_files",
            "edit_file",
            "git_diff",
            "run_tests",
            "diagnostic_shell",
            "execute_bash",
        )
        if tool in allowed_tools
    ]
    dependency_policy_summary = _dependency_policy_summary(task)
    diagnostic_shell_summary = (
        "diagnostic_shell is available only for task-local diagnostic commands in a protected projection; keep final fixes in public source files."
        if "diagnostic_shell" in allowed_tools
        else "diagnostic_shell is not available in this run; use structured tools for repository inspection and changes."
    )
    model_visible_prompt_block = _build_prompt_block(
        public_test_entry=public_test_entry,
        dependency_policy_summary=dependency_policy_summary,
        diagnostic_shell_summary=diagnostic_shell_summary,
    )
    _validate_model_visible_text(model_visible_prompt_block, field_name="model_visible_prompt_block")
    # Touch the verifier plan only through public policy state. This prevents unused-argument drift while
    # keeping raw verifier commands out of the safe label fields.
    _ = resolved_verifier_plan.resolved_verifier_plan_id
    return PublicEnvironmentContext.build(
        workspace_semantics="current repository workspace",
        default_cwd_label="repository root",
        path_policy_summary=(
            "Use workspace-relative paths with structured tools. Do not depend on host paths, runtime-private artifacts, or repository metadata outside the public workspace view."
        ),
        preferred_tool_order=preferred_tool_order,
        public_test_entry=public_test_entry,
        dependency_policy_summary=dependency_policy_summary,
        diagnostic_shell_summary=diagnostic_shell_summary,
        forbidden_environment_guess_categories=[
            "host_absolute_paths",
            "non_public_runtime_artifacts",
            "non_public_evaluation_materials",
            "ad_hoc_dependency_installation",
            "git_history_or_metadata",
        ],
        model_visible_prompt_block=model_visible_prompt_block,
    )


def validate_public_environment_model_visible_payload(value: Any) -> None:
    """Validate that a public environment payload is safe to show or export."""

    _validate_no_forbidden_model_visible_content(value, field_name="public_environment")
    visible_text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    _validate_model_visible_text(visible_text, field_name="public_environment")


def project_public_environment_for_batch(context: PublicEnvironmentContext) -> dict[str, str]:
    return context.batch_projection()


def write_public_environment_context_artifacts(
    *,
    recorder: RunRecorder,
    context: PublicEnvironmentContext,
) -> tuple[ArtifactRef, ArtifactRef]:
    """Write public context artifacts without exposing runtime-private paths."""

    context_ref = recorder.write_json_artifact(
        PUBLIC_ENVIRONMENT_CONTEXT_KIND,
        context.model_visible_payload(),
        {
            "redaction_status": "not_sensitive",
            "retention_policy": "keep",
            "budget_policy": "preserve_json",
            "public_environment_context_digest": context.context_digest,
        },
    )
    prompt_ref = recorder.write_artifact(
        PUBLIC_ENVIRONMENT_PROMPT_KIND,
        context.model_visible_prompt_block,
        {
            "suffix": ".txt",
            "redaction_status": "not_sensitive",
            "retention_policy": "keep",
            "budget_policy": "preserve_text",
            "public_environment_context_digest": context.context_digest,
        },
    )
    return context_ref, prompt_ref


def _build_public_test_entry(*, test_feedback_policy: str, allowed_tools: list[str]) -> PublicTestEntry:
    if test_feedback_policy == "disabled":
        return PublicTestEntry(
            status="disabled",
            tool_name=None,
            feedback_policy=test_feedback_policy,
            model_visible_summary="Public test feedback is disabled for this run.",
            command_template_label="public_tests_disabled",
            unavailable_reason="test_feedback_policy_disabled",
        )
    if test_feedback_policy == "oracle_hidden_feedback":
        return PublicTestEntry(
            status="unavailable",
            tool_name=None,
            feedback_policy=test_feedback_policy,
            model_visible_summary=(
                "No public intermediate test feedback is available in this run. Use source inspection and final answer when ready."
            ),
            command_template_label="public_tests_unavailable",
            non_public_feedback_visible=True,
            unavailable_reason="only_non_public_feedback_configured",
        )
    if "run_tests" not in allowed_tools:
        return PublicTestEntry(
            status="unavailable",
            tool_name=None,
            feedback_policy=test_feedback_policy,
            model_visible_summary="Public test feedback is not available because run_tests is not in the allowed tool set.",
            command_template_label="public_tests_unavailable",
            unavailable_reason="run_tests_not_allowed",
        )
    label = (
        "structured_public_feedback"
        if test_feedback_policy == "structured_public_feedback"
        else "configured_public_feedback"
    )
    summary = (
        "Use run_tests without arguments for structured public feedback."
        if test_feedback_policy == "structured_public_feedback"
        else "Use run_tests without arguments for configured public feedback."
    )
    return PublicTestEntry(
        status="available",
        tool_name="run_tests",
        feedback_policy=test_feedback_policy,
        model_visible_summary=summary,
        command_template_label=label,
    )


def _dependency_policy_summary(task: RunnableTask) -> str:
    if task.setup_command:
        return (
            "Dependencies and setup are managed by RepoHarness when available. Do not install or modify dependencies from the model-visible tools."
        )
    return (
        "Use the prepared repository environment as provided. Do not install dependencies from the model-visible tools."
    )


def _build_prompt_block(
    *,
    public_test_entry: PublicTestEntry,
    dependency_policy_summary: str,
    diagnostic_shell_summary: str,
) -> str:
    test_line = public_test_entry.model_visible_summary
    return (
        "Public environment guidance: work from the repository root using workspace-relative paths. "
        "Inspect files with read_file, grep, list_files, or glob_files; edit source files with edit_file; "
        "review changes with git_diff before the final answer. "
        f"{test_line} "
        f"{dependency_policy_summary} "
        f"{diagnostic_shell_summary} "
        "Do not try to access non-public evaluation materials, host filesystem locations, runtime artifacts, "
        "repository metadata internals, or ad hoc dependency installation."
    )


def _validate_safe_label(value: str, *, field_name: str) -> None:
    _validate_no_absolute_local_path(value, field_name=field_name)
    if value not in _SAFE_COMMAND_TEMPLATE_LABELS and value not in {
        "test_feedback_policy_disabled",
        "only_non_public_feedback_configured",
        "run_tests_not_allowed",
    }:
        if not re.fullmatch(r"[a-z0-9_]+", value):
            raise PublicEnvironmentVisibilityError(f"{field_name} must be a safe label")
    _validate_model_visible_text(value, field_name=field_name)
    if any(marker in value for marker in ("pytest", "FAIL_TO_PASS", "PASS_TO_PASS", "/", "\\")):
        raise PublicEnvironmentVisibilityError(f"{field_name} must not contain command text, selectors, or paths")


def _validate_model_visible_text(value: str, *, field_name: str) -> None:
    _validate_no_absolute_local_path(value, field_name=field_name)
    _validate_no_forbidden_model_visible_content(value, field_name=field_name)
    lowered = value.lower()
    for marker in _MODEL_VISIBLE_FORBIDDEN_SUBSTRINGS:
        if marker.lower() in lowered:
            raise PublicEnvironmentVisibilityError(
                f"{field_name} contains forbidden public environment content: {marker}"
            )
    if _ABSOLUTE_PATH_PATTERN.search(value):
        raise PublicEnvironmentVisibilityError(f"{field_name} contains an absolute path")


def _validate_no_absolute_local_path(value: str, *, field_name: str) -> None:
    local_path_markers = ("/Users/", "/home/", "/private/", "/tmp/", "/var/folders/")
    if value.startswith("/") or any(marker in value for marker in local_path_markers):
        raise PublicEnvironmentVisibilityError(f"{field_name} must not contain an absolute local path")


def _validate_no_forbidden_model_visible_content(value: Any, *, field_name: str) -> None:
    text = _collect_text(value)
    normalized = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    compact = normalized.replace("_", "")
    markers = (
        "hidden_verifier",
        "gold_patch",
        "test_patch",
        "accepted_label",
        "reward_metadata",
        "reward_extra_info",
        "provider_secret",
        "fail_to_pass",
        "pass_to_pass",
        "official_verifier_result",
        "repo_harness_run",
    )
    for marker in markers:
        normalized_marker = marker.lower()
        compact_marker = normalized_marker.replace("_", "")
        if normalized_marker in normalized or compact_marker in compact:
            raise PublicEnvironmentVisibilityError(
                f"{field_name} contains evaluator-only public environment content: {marker}"
            )


def _collect_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(str(key) + " " + _collect_text(item) for key, item in value.items())
    if isinstance(value, list):
        return " ".join(_collect_text(item) for item in value)
    return ""


def _validate_batch_projection(extra_fields: Mapping[str, Any]) -> dict[str, str]:
    validated: dict[str, str] = {}
    for key, value in extra_fields.items():
        if not key.startswith("repo_harness_"):
            raise PublicEnvironmentVisibilityError(f"batch field must be repo_harness_* namespaced: {key}")
        if not isinstance(value, str):
            raise PublicEnvironmentVisibilityError(f"batch field must be a string: {key}")
        _validate_model_visible_text(key, field_name="batch_projection_key")
        _validate_model_visible_text(value, field_name=key)
        validated[key] = value
    return validated
