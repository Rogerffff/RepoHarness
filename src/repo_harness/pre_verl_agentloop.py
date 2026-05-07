"""Pre-verl AgentLoop formal baseline inspection helpers."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from repo_harness.config import RunConfig, load_run_config
from repo_harness.context import ContextBuilder
from repo_harness.errors import ConfigError, TaskValidationError
from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.scaffolds import build_scaffold, resolve_allowed_tools, resolve_feedback_policy
from repo_harness.tasks import RunnableTask, TaskAdapter, TaskDefinition
from repo_harness.workspace import DependencyState, RunWorkspace

PRE_VERL_AGENTLOOP_ADAPTER_ID = "swebench_lite_dev_agentloop_v0"
PRE_VERL_AGENTLOOP_MODE = "formal_baseline"
PRE_VERL_AGENTLOOP_BASELINE_SOURCE = "repo_harness_agentloop_run_task"
LEGACY_V3_SWEBENCH_LIKE_ADAPTER_ID = "swebench_like_fixed"

_REQUIRED_EVALUATOR_ONLY_REFS = (
    "hidden_test_patch_ref",
    "fail_to_pass_selectors_ref",
    "pass_to_pass_selectors_ref",
)
_HIDDEN_MARKERS = (
    "hidden_test.patch",
    "test_patch",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "gold_patch",
    "official_harness_report",
    "official_resolved",
    "final_verifier_raw_output",
    "reward scalar",
    "reward label",
)


def is_formal_pre_verl_agentloop_metadata(metadata: dict[str, Any]) -> bool:
    """Return true only for the single approved formal pre-verl metadata shape."""

    manifest_path = metadata.get("pre_verl_swebench_dev_manifest_path")
    return (
        metadata.get("pre_verl_adapter") == PRE_VERL_AGENTLOOP_ADAPTER_ID
        and isinstance(manifest_path, str)
        and bool(manifest_path.strip())
        and metadata.get("pre_verl_agentloop_mode") == PRE_VERL_AGENTLOOP_MODE
        and metadata.get("pre_verl_agentloop_baseline_source")
        == PRE_VERL_AGENTLOOP_BASELINE_SOURCE
    )


def inspect_pre_verl_agentloop_task_definitions(
    manifest: str | Path,
    *,
    assert_run_task_compatible: bool = False,
    assert_evaluator_only_hidden_inputs: bool = False,
    assert_no_hidden_material_in_model_visible_fields: bool = False,
) -> str:
    manifest_path = Path(manifest)
    payload = _read_structured(manifest_path)
    task_paths = _collect_paths(payload, manifest_path, ("task_definition_refs", "task_definitions", "tasks"))
    failures: list[str] = []
    if not task_paths:
        failures.append("task definition manifest does not reference any task definitions")
    adapter = TaskAdapter()
    for task_path in task_paths:
        definition = _load_task_definition(task_path, failures)
        if definition is None:
            continue
        if assert_run_task_compatible:
            try:
                adapter.load(task_path)
            except TaskValidationError as exc:
                failures.append(f"{task_path}: not run-task compatible: {exc}")
        _inspect_formal_metadata(definition, failures, task_path)
        if assert_evaluator_only_hidden_inputs:
            _inspect_evaluator_only_refs(definition, failures, task_path)
        if assert_no_hidden_material_in_model_visible_fields:
            _inspect_model_visible_fields(definition, failures, task_path)
    return _inspect_result(
        "Inspect pre-verl AgentLoop task definitions",
        manifest_path,
        failures,
        assert_requested=(
            assert_run_task_compatible
            or assert_evaluator_only_hidden_inputs
            or assert_no_hidden_material_in_model_visible_fields
        ),
    )


def inspect_pre_verl_agentloop_run_config(
    manifest: str | Path,
    *,
    assert_final_only_test_feedback_disabled: bool = False,
    assert_resolved_tools_derived: bool = False,
    assert_no_hidden_feedback_visible: bool = False,
) -> str:
    manifest_path = Path(manifest)
    payload = _read_structured(manifest_path)
    entries = _collect_run_config_entries(payload, manifest_path)
    failures: list[str] = []
    if not entries:
        failures.append("run config manifest does not reference any task/config pairs")
    for entry in entries:
        task_path = entry["task_path"]
        config_path = entry["config_path"]
        definition = _load_task_definition(task_path, failures)
        if definition is None:
            continue
        _inspect_formal_metadata(definition, failures, task_path)
        try:
            run_config = load_run_config(config_path)
        except ConfigError as exc:
            failures.append(f"{config_path}: invalid run config: {exc}")
            continue
        if assert_final_only_test_feedback_disabled:
            if run_config.runtime.test_feedback_policy != "disabled":
                failures.append(f"{config_path}: final-only task must set test_feedback_policy=disabled")
            if run_config.runtime.max_test_runs != 0:
                failures.append(f"{config_path}: final-only task must set max_test_runs=0")
        _inspect_resolved_policy_and_context(
            definition=definition,
            run_config=run_config,
            config_path=config_path,
            expected_resolved_tools=entry.get("resolved_tools"),
            failures=failures,
            assert_resolved_tools_derived=assert_resolved_tools_derived,
            assert_no_hidden_feedback_visible=assert_no_hidden_feedback_visible,
        )
    return _inspect_result(
        "Inspect pre-verl AgentLoop run config",
        manifest_path,
        failures,
        assert_requested=(
            assert_final_only_test_feedback_disabled
            or assert_resolved_tools_derived
            or assert_no_hidden_feedback_visible
        ),
    )


def _inspect_formal_metadata(definition: TaskDefinition, failures: list[str], path: Path) -> None:
    metadata = definition.metadata or {}
    required = {
        "pre_verl_adapter": PRE_VERL_AGENTLOOP_ADAPTER_ID,
        "pre_verl_agentloop_mode": PRE_VERL_AGENTLOOP_MODE,
        "pre_verl_agentloop_baseline_source": PRE_VERL_AGENTLOOP_BASELINE_SOURCE,
        "swe_bench_like_final_only": True,
        "final_only": True,
    }
    for key, expected in required.items():
        if metadata.get(key) != expected:
            failures.append(f"{path}: metadata.{key} must be {expected!r}")
    manifest_path = metadata.get("pre_verl_swebench_dev_manifest_path")
    if not isinstance(manifest_path, str) or not manifest_path.strip():
        failures.append(f"{path}: metadata.pre_verl_swebench_dev_manifest_path must be a non-empty string")
    if metadata.get("v3_adapter") == LEGACY_V3_SWEBENCH_LIKE_ADAPTER_ID:
        failures.append(f"{path}: formal pre-verl task cannot use legacy v3_adapter=swebench_like_fixed")
    if not is_formal_pre_verl_agentloop_metadata(metadata):
        failures.append(f"{path}: formal pre-verl metadata shape is incomplete")


def _inspect_evaluator_only_refs(
    definition: TaskDefinition,
    failures: list[str],
    path: Path,
) -> None:
    metadata = definition.metadata or {}
    for key in _REQUIRED_EVALUATOR_ONLY_REFS:
        ref = metadata.get(key)
        if not isinstance(ref, dict):
            failures.append(f"{path}: metadata.{key} must be an evaluator-only ref")
            continue
        visibility = ref.get("visibility") or ref.get("redaction_status")
        if visibility != "evaluator_only":
            failures.append(f"{path}: metadata.{key} must have visibility=evaluator_only")
        ref_path = ref.get("path") or ref.get("relative_path")
        if not isinstance(ref_path, str) or not ref_path.strip():
            failures.append(f"{path}: metadata.{key} must bind path or relative_path")
        sha256 = ref.get("sha256")
        if not isinstance(sha256, str) or len(sha256) != 64 or not _is_lower_hex_sha256(sha256):
            failures.append(f"{path}: metadata.{key} must bind sha256")
        size_bytes = ref.get("size_bytes")
        if not isinstance(size_bytes, int) or size_bytes < 0:
            failures.append(f"{path}: metadata.{key} must bind non-negative size_bytes")
    if definition.gold_patch is not None:
        failures.append(f"{path}: formal pre-verl TaskDefinition must not inline raw gold_patch")


def _inspect_model_visible_fields(
    definition: TaskDefinition,
    failures: list[str],
    path: Path,
) -> None:
    fields = {
        "issue": definition.issue,
        "expected_files": definition.expected_files,
        "tags": definition.tags,
    }
    for field, value in fields.items():
        finding = _find_hidden_marker(value)
        if finding:
            failures.append(f"{path}: model-visible field {field} contains hidden marker {finding!r}")


def _inspect_resolved_policy_and_context(
    *,
    definition: TaskDefinition,
    run_config: RunConfig,
    config_path: Path,
    expected_resolved_tools: list[str] | None,
    failures: list[str],
    assert_resolved_tools_derived: bool,
    assert_no_hidden_feedback_visible: bool,
) -> None:
    runnable = RunnableTask.from_definition(definition)
    scaffold = build_scaffold(run_config.runtime.scaffold_id)
    try:
        feedback_policy = resolve_feedback_policy(
            run_config=run_config,
            scaffold=scaffold,
            task=definition,
        )
    except ConfigError as exc:
        failures.append(f"{config_path}: feedback policy invalid: {exc}")
        return
    resolved_tools = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)
    if assert_resolved_tools_derived and expected_resolved_tools is not None:
        if list(expected_resolved_tools) != resolved_tools:
            failures.append(f"{config_path}: resolved_tools does not match scaffold/test feedback policy")
    if assert_resolved_tools_derived and expected_resolved_tools is None:
        failures.append(f"{config_path}: resolved_tools audit field is required")
    if assert_no_hidden_feedback_visible:
        if feedback_policy.hidden_feedback_visible_to_model:
            failures.append(f"{config_path}: hidden feedback is model-visible")
        if feedback_policy.resolved_test_feedback_policy.value != "disabled":
            failures.append(f"{config_path}: final-only task resolved test feedback must be disabled")
        _inspect_context_redaction(
            runnable=runnable,
            run_config=run_config,
            scaffold=scaffold,
            resolved_tools=resolved_tools,
            failures=failures,
            config_path=config_path,
        )


def _inspect_context_redaction(
    *,
    runnable: RunnableTask,
    run_config: RunConfig,
    scaffold: Any,
    resolved_tools: list[str],
    failures: list[str],
    config_path: Path,
) -> None:
    with tempfile.TemporaryDirectory(prefix="repo_harness_pre_verl_context_") as temp:
        workspace = RunWorkspace(
            run_id="pre_verl_context_inspect",
            workspace_path=temp,
            artifact_dir=str(Path(temp) / "artifacts"),
            dependency_state=DependencyState(),
        )
        plan = ResolvedVerifierPlan(
            verifier_config=runnable.verifier_config,
            parser_confidence=1.0,
            resolved_verifier_plan_id="pre_verl_context_inspect",
        )
        messages = ContextBuilder().build_initial_messages(
            task=runnable,
            workspace=workspace,
            run_config=run_config,
            resolved_verifier_plan=plan,
            allowed_tools=resolved_tools,
            scaffold=scaffold,
        )
    user_content = messages[1].get("content")
    if not isinstance(user_content, dict):
        failures.append(f"{config_path}: prepared user message is not structured")
        return
    if user_content.get("test_command") is not None:
        failures.append(f"{config_path}: prepared messages exposed test_command")
    if user_content.get("test_command_visibility") != "redacted_final_only":
        failures.append(f"{config_path}: test_command_visibility must be redacted_final_only")
    finding = _find_hidden_marker(messages)
    if finding:
        failures.append(f"{config_path}: prepared messages contain hidden marker {finding!r}")


def _collect_run_config_entries(payload: Any, base: Path) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("entries"), list):
        entries = []
        for item in payload["entries"]:
            if not isinstance(item, dict):
                continue
            task_ref = item.get("task_definition_ref") or item.get("task_ref") or item.get("task_definition")
            config_ref = item.get("run_config_ref") or item.get("config_ref") or item.get("run_config")
            if task_ref and config_ref:
                entries.append(
                    {
                        "task_path": _path_from_ref(task_ref, base),
                        "config_path": _path_from_ref(config_ref, base),
                        "resolved_tools": item.get("resolved_tools"),
                    }
                )
        return entries
    task_paths = _collect_paths(payload, base, ("task_definition_refs", "task_definitions", "tasks"))
    config_paths = _collect_paths(payload, base, ("run_config_refs", "run_configs", "configs"))
    if len(task_paths) != len(config_paths):
        return []
    return [
        {"task_path": task_path, "config_path": config_path, "resolved_tools": None}
        for task_path, config_path in zip(task_paths, config_paths)
    ]


def _collect_paths(payload: Any, base: Path, keys: tuple[str, ...]) -> list[Path]:
    records: Any = payload if isinstance(payload, list) else None
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                records = value
                break
    if not isinstance(records, list):
        return []
    return [_path_from_ref(item, base) for item in records]


def _path_from_ref(ref: Any, base: Path) -> Path:
    value: str
    if isinstance(ref, str):
        value = ref
    elif isinstance(ref, dict):
        raw = ref.get("path") or ref.get("relative_path")
        if not raw:
            return base.parent / "<missing>"
        value = str(raw)
    else:
        return base.parent / "<invalid>"
    path = Path(value)
    return path if path.is_absolute() else (base.parent / path)


def _load_task_definition(path: Path, failures: list[str]) -> TaskDefinition | None:
    try:
        raw = _read_structured(path)
        return TaskDefinition.model_validate(raw)
    except (OSError, ValidationError, ConfigError) as exc:
        failures.append(f"{path}: invalid TaskDefinition: {exc}")
        return None


def _read_structured(path: str | Path) -> Any:
    target = Path(path)
    try:
        return yaml.safe_load(target.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"无法读取文件：{target}") from exc


def _find_hidden_marker(value: Any) -> str | None:
    if isinstance(value, str):
        for marker in _HIDDEN_MARKERS:
            if marker in value:
                return marker
        return None
    if isinstance(value, dict):
        for item in value.values():
            finding = _find_hidden_marker(item)
            if finding:
                return finding
    if isinstance(value, list):
        for item in value:
            finding = _find_hidden_marker(item)
            if finding:
                return finding
    return None


def _is_lower_hex_sha256(value: str) -> bool:
    return all(char in "0123456789abcdef" for char in value)


def _inspect_result(
    title: str,
    path: str | Path,
    failures: list[str],
    *,
    assert_requested: bool,
) -> str:
    if failures and assert_requested:
        raise ConfigError("; ".join(failures))
    status = "passed" if not failures else "failed"
    payload = {
        "path": str(path),
        "status": status,
        "failure_count": len(failures),
        "failures": failures,
    }
    return f"{title}: {status}\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
