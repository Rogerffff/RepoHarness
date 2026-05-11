from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from repo_harness.scaffolds import PATCH_FOCUSED_REACT_TOOL_ORDER

PRE_VERL_FINAL_ONLY_RESOLVED_TOOLS = [
    tool for tool in PATCH_FOCUSED_REACT_TOOL_ORDER if tool != "run_tests"
]


def test_pre_verl_agentloop_scheduler_prepare_uses_run_task_compatible_manifests(
    tmp_path: Path,
) -> None:
    script = _load_scheduler_module()
    manifest_path = _write_materialized_manifest_fixture(tmp_path)
    output_dir = tmp_path / "prepared"

    status = script.main(
        [
            "--pre-verl-task-set-manifest",
            manifest_path.as_posix(),
            "--output-dir",
            output_dir.as_posix(),
            "--mode",
            "smoke",
            "--task-id",
            "pre_verl_dev_001_sqlfluff__sqlfluff_1625",
            "--provider",
            "deepseek",
            "--model-id",
            "deepseek-v4-flash",
            "--repo-harness-bin",
            f"{sys.executable} -m repo_harness.cli.main",
        ]
    )

    assert status == 0
    configuration = _read_json(output_dir / "pre_verl_agentloop_configuration_manifest.json")
    assert configuration["baseline_source"] == "repo_harness_agentloop_run_task"
    assert configuration["pre_verl_adapter"] == "swebench_lite_dev_agentloop_v0"
    assert configuration["old_pilot_allowed"] is False
    assert configuration["baseline_id"] == "pre_verl_agentloop_smoke_deepseek_deepseek-v4-flash"
    assert configuration["provider_axis_scope"] == "deepseek_only"
    assert configuration["provider_retry_policy"] == {
        "schema_version": "repo_harness_provider_retry_policy_v0",
        "policy_id": "provider_retry_v0",
        "max_attempts": 3,
        "backoff_delays_ms": [0, 250, 1000],
        "sleep_enabled": True,
        "retryable_error_types": ["provider_error", "provider_timeout", "rate_limited"],
    }
    assert (
        configuration["harness_tool_context_policy"]["convergence_nudge_policy_version"]
        == "repo_harness_convergence_nudge_v2"
    )
    assert configuration["resolved_tools"] == PRE_VERL_FINAL_ONLY_RESOLVED_TOOLS
    task_manifest = _read_json(output_dir / "pre_verl_agentloop_task_definition_manifest.json")
    assert len(task_manifest["task_definition_refs"]) == 1
    run_config_manifest = _read_json(output_dir / "pre_verl_agentloop_run_config_manifest.json")
    assert run_config_manifest["baseline_id"] == configuration["baseline_id"]
    assert run_config_manifest["provider_retry_policy"] == configuration["provider_retry_policy"]
    assert run_config_manifest["entries"][0]["resolved_tools"] == configuration["resolved_tools"]
    assert run_config_manifest["entries"][0]["baseline_id"] == configuration["baseline_id"]
    assert run_config_manifest["entries"][0]["retry_policy"] == "provider_retry_v0"
    assert run_config_manifest["entries"][0]["run_config_preflight_status"] == "passed"
    assert run_config_manifest["entries"][0]["run_config_preflight_failure_count"] == 0
    preflight_path = Path(run_config_manifest["entries"][0]["run_config_preflight_ref"]["path"])
    preflight = _read_json(preflight_path)
    assert preflight["preflight_policy_version"] == "repo_harness_pre_verl_run_config_preflight_v0"
    assert preflight["thinking_mode"] == "enabled"
    assert preflight["max_output_tokens"] == 32768
    assert preflight["failures"] == []
    run_config = _read_yaml(
        output_dir
        / "run_configs"
        / "pre_verl_dev_001_sqlfluff__sqlfluff_1625_deepseek_deepseek-v4-flash.yaml"
    )
    assert run_config["runtime"]["execution_mode"] == "docker"
    assert run_config["model"]["retry_policy"] == "provider_retry_v0"
    assert run_config["runtime"]["docker_backend"]["build_base_image"] == "python:3.8"
    assert run_config["context_management"]["max_context_tokens"] == 120000
    assert run_config["model"]["provider_specific_options"]["thinking"] == {"type": "enabled"}
    assert configuration["budget"]["max_context_tokens"] == 120000
    budget_freeze = _read_json(output_dir / "formal_budget_freeze_manifest.json")
    assert budget_freeze["baseline_id"] == configuration["baseline_id"]
    assert budget_freeze["provider_retry_policy"] == configuration["provider_retry_policy"]
    assert (
        budget_freeze["harness_tool_context_policy"]["convergence_nudge_policy_version"]
        == "repo_harness_convergence_nudge_v2"
    )
    assert "retry_policy" in budget_freeze["requires_new_baseline_id_if_changed"]
    command_log = (output_dir / "pre_verl_agentloop_external_command_log.jsonl").read_text(
        encoding="utf-8"
    )
    assert "inspect-pre-verl-agentloop-task-definitions" in command_log
    assert "inspect-pre-verl-agentloop-run-config" in command_log
    generated_task = (output_dir / "task_definitions" / "pre_verl_dev_001_sqlfluff__sqlfluff_1625.yaml").read_text(
        encoding="utf-8"
    )
    assert "setup_command: null" in generated_task
    assert "pre_verl_setup_shell:" in generated_task
    assert "pre_verl_agentloop_baseline_source: repo_harness_agentloop_run_task" in generated_task


def test_scheduler_freezes_repo_specific_environment_setup_and_platform(tmp_path: Path) -> None:
    script = _load_scheduler_module()
    manifest_path = _write_materialized_manifest_fixture(
        tmp_path,
        task_id="pre_verl_dev_018_pyvista__pyvista_4315",
        repo="pyvista/pyvista",
        version="0.39",
    )
    output_dir = tmp_path / "prepared"

    status = script.main(
        [
            "--pre-verl-task-set-manifest",
            manifest_path.as_posix(),
            "--output-dir",
            output_dir.as_posix(),
            "--mode",
            "formal",
            "--task-id",
            "pre_verl_dev_018_pyvista__pyvista_4315",
            "--provider",
            "deepseek",
            "--model-id",
            "deepseek-v4-pro",
            "--repo-harness-bin",
            f"{sys.executable} -m repo_harness.cli.main",
        ]
    )

    assert status == 0
    run_config = _read_yaml(
        output_dir
        / "run_configs"
        / "pre_verl_dev_018_pyvista__pyvista_4315_deepseek_deepseek-v4-pro.yaml"
    )
    assert run_config["runtime"]["docker_backend"]["build_base_image"] == "python:3.9"
    assert run_config["runtime"]["docker_backend"]["requested_container_platform"] == "linux/amd64"
    run_config_manifest = _read_json(output_dir / "pre_verl_agentloop_run_config_manifest.json")
    entry = run_config_manifest["entries"][0]
    assert entry["run_config_preflight_status"] == "passed"
    preflight = _read_json(Path(entry["run_config_preflight_ref"]["path"]))
    assert preflight["required_container_platform"] == "linux/amd64"
    assert preflight["resolved_container_platform"] == "linux/amd64"
    assert preflight["failures"] == []
    generated_task = (
        output_dir / "task_definitions" / "pre_verl_dev_018_pyvista__pyvista_4315.yaml"
    ).read_text(encoding="utf-8")
    assert "requested_container_platform: linux/amd64" in generated_task

    pvlib_env = script._pre_verl_environment_for_repo("pvlib/pvlib-python", "0.9")
    assert "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PVLIB=0.9.0" in pvlib_env["setup_shell"]
    assert "pytest-mock" in pvlib_env["setup_shell"]
    assert pvlib_env["environment_id"] == "pre_verl_pvlib_0.9_python39_v1"


def test_scheduler_boundary_index_skips_quality_gate_blocked_runs(tmp_path: Path) -> None:
    script = _load_scheduler_module()
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    boundary_run = tmp_path / "runs" / "with_boundary"
    blocked_run = tmp_path / "runs" / "blocked"
    boundary_run.mkdir(parents=True)
    blocked_run.mkdir(parents=True)
    _write_json(
        boundary_run / "final_verifier_boundary.json",
        {
            "final_verifier_status": "rejected",
            "accepted": False,
            "failure_category": "model_patch_rejected_by_final_verifier",
            "failure_owner": "model_wrong_fix",
        },
    )
    _write_json(
        boundary_run / "run_metadata.json",
        {"run_outcome": "inconclusive", "final_verifier_status": "error"},
    )
    _write_json(boundary_run / "metrics.json", {"final_verifier_status": "error"})
    _write_json(boundary_run / "baseline.json", {"status": "valid"})
    _write_json(blocked_run / "run_metadata.json", {"agent_stop_reason": "skipped_invalid_baseline"})
    _write_json(
        blocked_run / "metrics.json",
        {
            "final_verifier_status": "skipped",
            "interaction_efficiency": {"quality_gate_reason": "setup_failed"},
        },
    )
    _write_json(blocked_run / "baseline.json", {"status": "invalid", "dependency_error": "setup_failed"})
    entries = [
        {
            "task_id": "with_boundary",
            "run_task_run_dir": boundary_run.as_posix(),
            "run_task_exit_code": 0,
            "scaffold_id": "patch_focused_react",
            "provider": "deepseek",
            "model_id": "deepseek-v4-flash",
        },
        {
            "task_id": "blocked",
            "run_task_run_dir": blocked_run.as_posix(),
            "run_task_exit_code": 0,
            "scaffold_id": "patch_focused_react",
            "provider": "deepseek",
            "model_id": "deepseek-v4-flash",
        },
    ]

    for entry in entries:
        script._annotate_run_task_entry(entry)
    boundary_index = script._write_boundary_index(output_dir, entries)
    run_matrix = script._write_run_matrix(output_dir, entries, _Args(mode="smoke"))

    boundary_payload = _read_json(boundary_index)
    matrix_payload = _read_json(run_matrix)
    assert [entry["task_id"] for entry in boundary_payload["entries"]] == ["with_boundary"]
    assert entries[0]["status"] == "executed_formal_boundary"
    assert entries[0]["final_verifier_status"] == "rejected"
    assert entries[0]["final_verifier_status_source"] == "final_verifier_boundary"
    assert entries[0]["failure_category"] == "model_patch_rejected_by_final_verifier"
    assert matrix_payload["entries"][0]["final_verifier_status"] == "rejected"
    assert matrix_payload["entries"][0]["final_verifier_status_source"] == "final_verifier_boundary"
    assert entries[1]["status"] == "quality_gate_blocked"
    assert entries[1]["blocked_reason"] == "setup_failed"
    assert matrix_payload["formal_boundary_entry_count"] == 1
    assert matrix_payload["quality_gate_blocked_count"] == 1


def test_scheduler_marks_missing_blocked_evidence_as_incomplete(tmp_path: Path) -> None:
    script = _load_scheduler_module()
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    run_dir = tmp_path / "runs" / "incomplete"
    run_dir.mkdir(parents=True)
    entry = {
        "task_id": "incomplete",
        "run_task_run_dir": run_dir.as_posix(),
        "run_task_exit_code": 0,
        "scaffold_id": "patch_focused_react",
        "provider": "deepseek",
        "model_id": "deepseek-v4-flash",
    }

    script._annotate_run_task_entry(entry)
    run_matrix = script._write_run_matrix(output_dir, [entry], _Args(mode="smoke"))
    matrix_payload = _read_json(run_matrix)

    assert entry["status"] == "incomplete_run_artifacts"
    assert entry["blocked_reason"] == "missing_required_run_artifacts"
    assert entry["missing_run_artifacts"] == [
        "run_metadata.json",
        "metrics.json",
        "baseline.json",
    ]
    assert matrix_payload["incomplete_run_artifact_count"] == 1
    assert matrix_payload["quality_gate_blocked_count"] == 0


def test_scheduler_normalizes_truncated_parametrized_selectors() -> None:
    script = _load_scheduler_module()

    selectors, report = script._normalize_pytest_selectors(
        [
            "pydicom/tests/test_valuerep.py::TestIsValidDS::test_valid[",
            "pydicom/tests/test_valuerep.py::TestIsValidDS::test_valid[1]",
            "tests/test_cli.py::test__cli__command_fix_stdin[select",
            "test/dialects/ansi_test.py::test__dialect__ansi_specific_segment_parses[ExpressionSegment-bits[OFFSET(0)]",
            "test/dialects/ansi_test.py::test__dialect__ansi_specific_segment_parses[ExpressionSegment-NULL::INT]",
        ],
        task_id="task",
        suite="pass_to_pass",
    )

    assert selectors == [
        "pydicom/tests/test_valuerep.py::TestIsValidDS::test_valid",
        "pydicom/tests/test_valuerep.py::TestIsValidDS::test_valid[1]",
        "tests/test_cli.py::test__cli__command_fix_stdin",
        "test/dialects/ansi_test.py::test__dialect__ansi_specific_segment_parses",
        "test/dialects/ansi_test.py::test__dialect__ansi_specific_segment_parses[ExpressionSegment-NULL::INT]",
    ]
    assert report["changed_selector_count"] == 3
    assert report["status"] == "passed"


def _write_materialized_manifest_fixture(
    tmp_path: Path,
    *,
    task_id: str = "pre_verl_dev_001_sqlfluff__sqlfluff_1625",
    repo: str = "sqlfluff/sqlfluff",
    version: str = "0.6",
) -> Path:
    root = tmp_path / "materialized"
    freeze = tmp_path / "freeze"
    source_dir = root / "source_checkouts" / task_id / "source"
    task_dir = root / "tasks" / task_id
    patches_dir = root / "patches" / task_id
    visible_dir = freeze / "adapter_visible_task_inputs"
    evaluator_dir = freeze / "evaluator_only_task_evidence"
    definitions_dir = freeze / "task_definitions"
    for directory in (source_dir, task_dir, patches_dir, visible_dir, evaluator_dir, definitions_dir):
        directory.mkdir(parents=True, exist_ok=True)
    (source_dir / "requirements.txt").write_text("", encoding="utf-8")
    (source_dir / "requirements_dev.txt").write_text("", encoding="utf-8")
    hidden_patch_path = patches_dir / "hidden_test.patch"
    hidden_patch_path.write_text(
        "diff --git a/test_example.py b/test_example.py\n--- a/test_example.py\n+++ b/test_example.py\n",
        encoding="utf-8",
    )
    adapter_input_path = visible_dir / f"{task_id}.json"
    _write_json(
        adapter_input_path,
        {
            "schema_version": "repo_harness_pre_verl_adapter_visible_task_input_v0",
            "task_id": task_id,
            "source_instance_id": task_id.removeprefix("pre_verl_dev_"),
            "repo": repo,
            "problem_statement": "Fix a user-visible SQLFluff issue.",
        },
    )
    evaluator_path = evaluator_dir / f"{task_id}.json"
    _write_json(
        evaluator_path,
        {
            "schema_version": "repo_harness_pre_verl_evaluator_only_task_evidence_v0",
            "task_id": task_id,
            "FAIL_TO_PASS": ["test_example.py::test_hidden"],
            "PASS_TO_PASS": [],
            "test_patch": hidden_patch_path.read_text(encoding="utf-8"),
        },
    )
    materialization_entry_path = task_dir / "materialization_entry.json"
    _write_json(
        materialization_entry_path,
        {
            "schema_version": "repo_harness_pre_verl_swebench_dev_materialization_entry_v0",
            "status": "passed",
            "task_id": task_id,
            "repo": repo,
            "version": version,
            "source_tree_sha256": "a" * 64,
            "test_patch_apply_status": "passed",
            "test_patch_apply_result_ref": _ref(task_dir / "test_patch_apply_result.json"),
        },
    )
    _write_json(task_dir / "test_patch_apply_result.json", {"status": "passed"})
    verifier_plan_path = task_dir / "verifier_plan.json"
    _write_json(
        verifier_plan_path,
        {
            "schema_version": "repo_harness_pre_verl_swebench_dev_verifier_plan_v0",
            "status": "passed",
            "task_id": task_id,
            "repo": repo,
            "base_commit": "fixture",
            "environment_id": f"pre_verl_fixture_{version}_v0",
            "execution_image": "python:3.8",
            "pythonpath": "src",
            "fail_to_pass_selectors": ["test_example.py::test_hidden"],
            "pass_to_pass_selector_count": 0,
            "test_patch_ref": _ref(hidden_patch_path, visibility="evaluator_only"),
        },
    )
    source_record_path = definitions_dir / f"{task_id}.json"
    _write_json(
        source_record_path,
        {
            "schema_version": "repo_harness_pre_verl_task_definition_v0",
            "task_id": task_id,
            "tier": "swebench_lite_development",
            "agent_run_ready": True,
            "runnable": True,
            "verifier_ready": True,
            "repo": repo,
            "version": version,
            "source_instance_id": task_id.removeprefix("pre_verl_dev_"),
            "base_commit": "fixture",
            "source_tree_sha256": "a" * 64,
            "adapter_visible_input_ref": _ref(adapter_input_path, visibility="model_visible"),
            "evaluator_only_evidence_ref": _ref(evaluator_path, visibility="evaluator_only"),
            "swebench_dev_materialization_entry_ref": _ref(materialization_entry_path),
            "verifier_plan_ref": _ref(verifier_plan_path),
        },
    )
    manifest_path = freeze / "pre_verl_task_set_manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "repo_harness_pre_verl_task_set_manifest_v0",
            "task_definition_refs": [_ref(source_record_path)],
        },
    )
    return manifest_path


def _load_scheduler_module():
    path = Path("scripts/pre_verl/run_agentloop_evaluation.py").resolve()
    spec = importlib.util.spec_from_file_location("pre_verl_agentloop_scheduler", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ref(path: Path, *, visibility: str = "audit_only") -> dict[str, object]:
    return {
        "path": path.as_posix(),
        "sha256": "a" * 64,
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "visibility": visibility,
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_yaml(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


class _Args:
    def __init__(self, *, mode: str) -> None:
        self.mode = mode
        self.baseline_id = "fixture_baseline"
        self.parent_baseline_id = None
        self.parent_run_dir = None
        self.parent_status = None
        self.baseline_change_summary = "fixture"
