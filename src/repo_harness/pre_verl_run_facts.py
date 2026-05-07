"""Pre-verl formal AgentLoop run facts.

These helpers write small, auditable artifacts that freeze the policy surface
used by formal pre-verl smoke and 23-task evaluation runs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repo_harness.config import RunConfig
from repo_harness.evaluation.schemas import ResolvedFeedbackPolicyFacts
from repo_harness.schema_base import stable_hash
from repo_harness.schema_versions import PERMISSION_POLICY_VERSION
from repo_harness.scaffolds import ScaffoldDefinition
from repo_harness.tasks import TaskDefinition
from repo_harness.tasks.command_policy import COMMAND_POLICY_VERSION
from repo_harness.trajectory import ArtifactRef, RunRecorder
from repo_harness.workspace.source_hash import compute_file_sha256, compute_source_tree_hash

PRE_VERL_PROVIDER_AXIS_SCOPE_SINGLE_PROVIDER_VERSION = "repo_harness_pre_verl_provider_axis_scope_v0"
PRE_VERL_PERMISSION_POLICY_MANIFEST_VERSION = "repo_harness_pre_verl_permission_policy_manifest_v0"
PRE_VERL_SOURCE_SNAPSHOT_VERSION = "repo_harness_pre_verl_source_snapshot_v0"
PRE_VERL_REPO_CONTEXT_INDEX_VERSION = "repo_harness_pre_verl_repo_context_index_v0"
PRE_VERL_FORBIDDEN_SCAFFOLD_IDS = ["single_shot_patch_no_tools"]

_SOURCE_INDEX_EXCLUDED_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
}


def write_permission_policy_manifest(
    *,
    recorder: RunRecorder,
    config: RunConfig,
    feedback_policy: ResolvedFeedbackPolicyFacts,
    allowed_tools: list[str],
) -> ArtifactRef:
    payload = permission_policy_manifest_payload(
        config=config,
        feedback_policy=feedback_policy,
        allowed_tools=allowed_tools,
    )
    return recorder.write_json_artifact(
        "permission_policy_manifest",
        payload,
        {
            "redaction_status": "not_sensitive",
            "retention_policy": "keep",
            "budget_policy": "preserve_json",
        },
    )


def permission_policy_manifest_payload(
    *,
    config: RunConfig,
    feedback_policy: ResolvedFeedbackPolicyFacts,
    allowed_tools: list[str],
) -> dict[str, Any]:
    bash_enabled = "bash" in allowed_tools
    core = {
        "permission_policy_version": config.versions.permission_policy_version
        or PERMISSION_POLICY_VERSION,
        "command_policy_version": COMMAND_POLICY_VERSION,
        "decision_order": [
            "tool_schema_resolution",
            "workspace_boundary_or_sensitive_path",
            "bash_safe_argv_policy",
            "permission_mode",
            "non_interactive_resolution",
        ],
        "permission_mode": config.runtime.permission_mode,
        "non_interactive_resolution": "deny_when_user_confirmation_would_be_required",
        "hooks": {"enabled": False},
        "mcp": {"enabled": False},
        "dynamic_permission_classifier": {"enabled": False},
        "bash": {
            "enabled": bash_enabled,
            "shell_execution": False,
            "safe_argv_required": True,
            "test_feedback_policy_can_route_pytest_to_run_tests": (
                feedback_policy.resolved_test_feedback_policy.value != "disabled"
            ),
        },
        "test_feedback_policy": feedback_policy.resolved_test_feedback_policy.value,
        "feedback_tests_passed_policy": feedback_policy.resolved_feedback_tests_passed_policy,
        "deny_rule_summary": [
            "workspace_boundary_or_sensitive_path",
            "permission_mode_plan_write_denied",
            "permission_mode_ask_non_interactive_denied",
            "permission_mode_deny_write_denied",
            "bash_shell_composition_denied",
            "bash_network_or_destructive_command_denied",
            "bash_python_inline_code_denied",
        ],
    }
    return {
        "schema_version": PRE_VERL_PERMISSION_POLICY_MANIFEST_VERSION,
        **core,
        "policy_hash": stable_hash(core),
        "policy_claims": {
            "hooks_enabled": False,
            "mcp_enabled": False,
            "dynamic_permission_classifier_enabled": False,
            "bash_shell_execution": False,
            "bash_safe_argv_required": True,
        },
    }


def write_source_snapshot_and_context_index(
    *,
    recorder: RunRecorder,
    task_definition: TaskDefinition,
    config: RunConfig,
    scaffold: ScaffoldDefinition,
    source_checkout: str | Path,
    allowed_tools: list[str],
) -> tuple[ArtifactRef, ArtifactRef]:
    source_root = Path(source_checkout)
    agents_ref = _agents_md_ref(source_root)
    source_snapshot = {
        "schema_version": PRE_VERL_SOURCE_SNAPSHOT_VERSION,
        "task_id": task_definition.id,
        "source_kind": task_definition.source_kind,
        "base_commit": task_definition.base_commit,
        "source_tree_hash": compute_source_tree_hash(source_root),
        "agent_start_snapshot_policy": "source_checkout_before_agent_workspace",
        "dirty_state_policy": "materialized_source_checkout_expected_clean",
        "agents_md_present": agents_ref is not None,
        "agents_md_ref": agents_ref,
    }
    source_snapshot_ref = recorder.write_json_artifact(
        "source_snapshot",
        source_snapshot,
        {
            "redaction_status": "not_sensitive",
            "retention_policy": "keep",
            "budget_policy": "preserve_json",
        },
    )
    indexed_files = _source_index(source_root)
    context_index = {
        "schema_version": PRE_VERL_REPO_CONTEXT_INDEX_VERSION,
        "task_id": task_definition.id,
        "source_snapshot_ref": source_snapshot_ref.model_dump(mode="json"),
        "context_policy_version": config.context_management.context_policy_version,
        "context_builder_version": config.versions.context_builder_version,
        "scaffold_id": scaffold.scaffold_id,
        "allowed_tools": allowed_tools,
        "agents_md_resolution": "root_only" if agents_ref else "not_present",
        "agents_md_injected_into_initial_context": False,
        "full_hierarchical_instruction_resolution": False,
        "model_visible_file_index_summary": {
            "file_count": len(indexed_files),
            "sample_paths": indexed_files[:200],
            "sample_limit": 200,
        },
        "expected_files": list(task_definition.expected_files),
        "truncation_policy": {
            "max_context_tokens": config.context_management.max_context_tokens,
            "token_estimator": config.context_management.token_estimator,
        },
        "sensitive_path_filter_policy": "exclude evaluator-only hidden patch, selectors, provider raw artifacts, VCS and cache directories",
        "evaluator_only_material_excluded": True,
        "known_limitations": [
            "本轮只记录 root AGENTS.md 是否存在，没有实现完整层级 instruction resolver。",
            "repo_context_index 是轻量文件索引，不是符号级检索或语言服务器索引。",
        ],
    }
    repo_context_index_ref = recorder.write_json_artifact(
        "repo_context_index",
        {
            **context_index,
            "index_hash": stable_hash(context_index),
        },
        {
            "redaction_status": "not_sensitive",
            "retention_policy": "keep",
            "budget_policy": "preserve_json",
        },
    )
    return source_snapshot_ref, repo_context_index_ref


def provider_axis_scope_for_config(config: RunConfig) -> str:
    explicit = config.model.provider_specific_options.get("provider_axis_scope")
    if isinstance(explicit, str) and explicit:
        expected = f"{config.model.provider}_only"
        if explicit != expected:
            from repo_harness.errors import ConfigError

            raise ConfigError(
                "formal pre-verl 单 provider baseline 的 provider_axis_scope "
                f"必须是 {expected}，不能覆盖为 {explicit!r}。"
            )
        return explicit
    if config.model.provider == "deepseek":
        return "deepseek_only"
    return f"{config.model.provider}_only"


def provider_axis_scope_payload(config: RunConfig) -> dict[str, Any]:
    return {
        "schema_version": PRE_VERL_PROVIDER_AXIS_SCOPE_SINGLE_PROVIDER_VERSION,
        "provider_axis_scope": provider_axis_scope_for_config(config),
        "provider": config.model.provider,
        "model_id": config.model.model_id,
        "accepted_rate_source": "repo_harness_run_task_only",
        "multi_provider_runtime_unified": False,
        "comparison_policy": (
            "本轮正式 accepted rate 冻结为单 primary provider；OpenAI 或其他 provider "
            "comparison 不能混入该 baseline。"
        ),
    }


def _agents_md_ref(source_root: Path) -> dict[str, Any] | None:
    path = source_root / "AGENTS.md"
    if not path.exists() or not path.is_file():
        return None
    return {
        "relative_path": "AGENTS.md",
        "sha256": compute_file_sha256(path),
        "size_bytes": path.stat().st_size,
        "visibility": "model_visible_policy_reference",
    }


def _source_index(source_root: Path) -> list[str]:
    paths: list[str] = []
    for path in sorted(source_root.rglob("*")):
        relative = path.relative_to(source_root)
        if any(part in _SOURCE_INDEX_EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.is_file() and not path.is_symlink():
            paths.append(relative.as_posix())
    return paths
