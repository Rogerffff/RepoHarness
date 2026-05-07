from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest
import yaml

from repo_harness.evaluation.runner import run_task
from repo_harness.pre_verl_agentloop import inspect_pre_verl_agentloop_boundary_index


def test_pre_verl_agentloop_run_task_uses_clean_source_model_patch_hidden_patch_order(
    tmp_path: Path,
) -> None:
    task_path, config_path = _write_pre_verl_fixture(tmp_path)

    run_dir = run_task(
        task_path,
        config_path=config_path,
        output_dir=tmp_path / "runs",
        run_id="pre-verl-agentloop-accepted",
    )

    boundary = _read_json(run_dir / "final_verifier_boundary.json")
    verifier = _read_json(run_dir / "verifier.json")
    assert verifier["accepted"] is True
    assert boundary["accepted"] is True
    assert boundary["verifier_adapter_id"] == "pre_verl_swebench_lite_dev_final_verifier_v0"
    assert boundary["verification_workspace_source"] == "clean_frozen_source"
    assert boundary["patch_application_order"] == [
        "model_final_patch",
        "evaluator_only_hidden_test_patch",
    ]
    assert boundary["observed_command_order"][:3] == [
        "pre_verl_model_final_patch_apply",
        "pre_verl_hidden_test_patch_apply",
        "pre_verl_fail_to_pass_test_execution",
    ]
    assert boundary["clean_source_tree_sha256"]
    assert boundary["after_model_patch_tree_sha256"]
    assert boundary["after_hidden_test_patch_tree_sha256"]
    assert boundary["run_task_entrypoint"] == "repo-harness run-task"

    index_path = tmp_path / "boundary_index.json"
    command_entry_path = tmp_path / "run_task_command_entry.json"
    _write_json(
        command_entry_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_external_command_log_entry_v0",
            "command_name": "run-task",
            "argv": [
                "repo-harness",
                "run-task",
                task_path.as_posix(),
                "--config",
                config_path.as_posix(),
                "--run-id",
                "pre-verl-agentloop-accepted",
            ],
            "exit_code": 0,
        },
    )
    _write_json(
        index_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_boundary_index_v0",
            "entries": [
                {
                    "task_id": "pre_verl_order_fixture",
                    "run_task_run_dir": run_dir.as_posix(),
                    "final_verifier_boundary_ref": _evaluator_ref(run_dir / "final_verifier_boundary.json"),
                    "scaffold_id": "patch_focused_react",
                    "run_task_command_log_entry_ref": _evaluator_ref(command_entry_path),
                }
            ],
        },
    )
    result = inspect_pre_verl_agentloop_boundary_index(
        index_path,
        assert_all_formal_runs_bound=True,
        assert_command_order=True,
        assert_clean_source_origin=True,
        assert_run_task_lineage=True,
        assert_no_legacy_adapter=True,
    )
    assert "passed" in result


def test_pre_verl_agentloop_boundary_index_rejects_hidden_patch_before_model_patch(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    for name in ("run_metadata.json", "metrics.json"):
        _write_json(run_dir / name, {"run_id": "bad-order"})
    for name in ("events.jsonl", "transcript.jsonl"):
        (run_dir / name).write_text("", encoding="utf-8")
    boundary_path = run_dir / "final_verifier_boundary.json"
    _write_json(
        boundary_path,
        {
            "schema_version": "repo_harness_pre_verl_final_verifier_boundary_v0",
            "task_id": "bad-order",
            "verifier_adapter_id": "pre_verl_swebench_lite_dev_final_verifier_v0",
            "run_task_entrypoint": "repo-harness run-task",
            "final_verifier_timeout_sec": 60,
            "verification_workspace_source": "clean_frozen_source",
            "workspace_creation_input_ref": {"relative_path": "workspaces/source_checkout"},
            "clean_source_tree_sha256": "a" * 64,
            "patch_application_order": [
                "model_final_patch",
                "evaluator_only_hidden_test_patch",
            ],
            "observed_command_order": [
                "pre_verl_hidden_test_patch_apply",
                "pre_verl_model_final_patch_apply",
            ],
        },
    )
    index_path = tmp_path / "boundary_index.json"
    _write_json(
        index_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_boundary_index_v0",
            "entries": [{"run_task_run_dir": run_dir.as_posix()}],
        },
    )

    with pytest.raises(Exception, match="command order"):
        inspect_pre_verl_agentloop_boundary_index(index_path, assert_command_order=True)


def test_pre_verl_agentloop_boundary_index_rejects_missing_formal_steps(
    tmp_path: Path,
) -> None:
    run_dir = _minimal_run_dir(tmp_path / "run")
    _write_json(
        run_dir / "final_verifier_boundary.json",
        {
            "schema_version": "repo_harness_pre_verl_final_verifier_boundary_v0",
            "task_id": "missing-steps",
            "verifier_adapter_id": "pre_verl_swebench_lite_dev_final_verifier_v0",
            "run_task_entrypoint": "repo-harness run-task",
            "final_verifier_timeout_sec": 60,
            "verification_workspace_source": "clean_frozen_source",
            "workspace_creation_input_ref": {"relative_path": "workspaces/source_checkout"},
            "clean_source_tree_sha256": "a" * 64,
            "patch_application_order": [
                "model_final_patch",
                "evaluator_only_hidden_test_patch",
            ],
            "observed_command_order": [],
        },
    )
    index_path = tmp_path / "boundary_index.json"
    _write_json(
        index_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_boundary_index_v0",
            "entries": [{"run_task_run_dir": run_dir.as_posix()}],
        },
    )

    with pytest.raises(Exception, match="observed_command_order 缺少"):
        inspect_pre_verl_agentloop_boundary_index(index_path, assert_command_order=True)


def test_pre_verl_agentloop_boundary_index_rejects_missing_pass_to_pass_step(
    tmp_path: Path,
) -> None:
    run_dir = _minimal_run_dir(tmp_path / "run")
    _write_json(
        run_dir / "final_verifier_boundary.json",
        {
            "schema_version": "repo_harness_pre_verl_final_verifier_boundary_v0",
            "task_id": "missing-pass-to-pass",
            "accepted": True,
            "final_verifier_status": "accepted",
            "verifier_adapter_id": "pre_verl_swebench_lite_dev_final_verifier_v0",
            "run_task_entrypoint": "repo-harness run-task",
            "final_verifier_timeout_sec": 60,
            "verification_workspace_source": "clean_frozen_source",
            "workspace_creation_input_ref": {"relative_path": "workspaces/source_checkout"},
            "clean_source_tree_sha256": "a" * 64,
            "patch_application_order": [
                "model_final_patch",
                "evaluator_only_hidden_test_patch",
            ],
            "observed_command_order": [
                "pre_verl_model_final_patch_apply",
                "pre_verl_hidden_test_patch_apply",
                "pre_verl_fail_to_pass_test_execution",
            ],
            "model_final_patch_apply_result_ref": {"relative_path": "model.json"},
            "hidden_test_patch_apply_result_ref": {"relative_path": "hidden.json"},
            "fail_to_pass_result_ref": {"relative_path": "f2p.json"},
        },
    )
    index_path = tmp_path / "boundary_index.json"
    _write_json(
        index_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_boundary_index_v0",
            "entries": [{"run_task_run_dir": run_dir.as_posix()}],
        },
    )

    with pytest.raises(Exception, match="pre_verl_pass_to_pass_test_execution"):
        inspect_pre_verl_agentloop_boundary_index(index_path, assert_command_order=True)


def test_pre_verl_agentloop_boundary_index_requires_formal_run_artifacts(
    tmp_path: Path,
) -> None:
    run_dir = _minimal_run_dir(tmp_path / "run")
    (run_dir / "final.patch").unlink()
    _write_json(
        run_dir / "final_verifier_boundary.json",
        {
            "schema_version": "repo_harness_pre_verl_final_verifier_boundary_v0",
            "task_id": "missing-final-patch",
        },
    )
    index_path = tmp_path / "boundary_index.json"
    _write_json(
        index_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_boundary_index_v0",
            "entries": [{"run_task_run_dir": run_dir.as_posix()}],
        },
    )

    with pytest.raises(Exception, match="final.patch"):
        inspect_pre_verl_agentloop_boundary_index(index_path, assert_all_formal_runs_bound=True)


def test_pre_verl_agentloop_boundary_index_requires_run_task_command_lineage(
    tmp_path: Path,
) -> None:
    run_dir = _formal_lineage_run_dir(tmp_path / "run", include_raw_provider_refs=True)
    index_path = tmp_path / "boundary_index.json"
    _write_json(
        index_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_boundary_index_v0",
            "entries": [{"run_task_run_dir": run_dir.as_posix(), "scaffold_id": "patch_focused_react"}],
        },
    )

    with pytest.raises(Exception, match="run_task_command_log_entry_ref"):
        inspect_pre_verl_agentloop_boundary_index(index_path, assert_run_task_lineage=True)


def test_pre_verl_agentloop_boundary_index_requires_provider_raw_refs(
    tmp_path: Path,
) -> None:
    run_dir = _formal_lineage_run_dir(tmp_path / "run", include_raw_provider_refs=False)
    command_entry_path = tmp_path / "run_task_command_entry.json"
    _write_json(
        command_entry_path,
        {
            "command_name": "run-task",
            "argv": ["repo-harness", "run-task", "task.yaml", "--run-id", "formal-run"],
            "exit_code": 0,
        },
    )
    index_path = tmp_path / "boundary_index.json"
    _write_json(
        index_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_boundary_index_v0",
            "entries": [
                {
                    "run_task_run_dir": run_dir.as_posix(),
                    "final_verifier_boundary_ref": _evaluator_ref(run_dir / "final_verifier_boundary.json"),
                    "scaffold_id": "patch_focused_react",
                    "run_task_command_log_entry_ref": _evaluator_ref(command_entry_path),
                }
            ],
        },
    )

    with pytest.raises(Exception, match="raw_provider_request_ref"):
        inspect_pre_verl_agentloop_boundary_index(index_path, assert_run_task_lineage=True)


def test_pre_verl_agentloop_boundary_index_rejects_empty_events_log(
    tmp_path: Path,
) -> None:
    run_dir = _formal_lineage_run_dir(tmp_path / "run", include_raw_provider_refs=True)
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    command_entry_path = tmp_path / "run_task_command_entry.json"
    _write_json(
        command_entry_path,
        {
            "command_name": "run-task",
            "argv": ["repo-harness", "run-task", "task.yaml", "--run-id", "formal-run"],
            "exit_code": 0,
        },
    )
    index_path = tmp_path / "boundary_index.json"
    _write_json(
        index_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_boundary_index_v0",
            "entries": [
                {
                    "run_task_run_dir": run_dir.as_posix(),
                    "final_verifier_boundary_ref": _evaluator_ref(run_dir / "final_verifier_boundary.json"),
                    "scaffold_id": "patch_focused_react",
                    "run_task_command_log_entry_ref": _evaluator_ref(command_entry_path),
                }
            ],
        },
    )

    with pytest.raises(Exception, match="events.jsonl"):
        inspect_pre_verl_agentloop_boundary_index(index_path, assert_run_task_lineage=True)


def test_pre_verl_agentloop_boundary_index_requires_command_ref_fingerprint(
    tmp_path: Path,
) -> None:
    run_dir = _formal_lineage_run_dir(tmp_path / "run", include_raw_provider_refs=True)
    command_entry_path = tmp_path / "run_task_command_entry.json"
    _write_json(
        command_entry_path,
        {
            "command_name": "run-task",
            "argv": ["repo-harness", "run-task", "task.yaml", "--run-id", "formal-run"],
            "exit_code": 0,
        },
    )
    index_path = tmp_path / "boundary_index.json"
    _write_json(
        index_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_boundary_index_v0",
            "entries": [
                {
                    "run_task_run_dir": run_dir.as_posix(),
                    "final_verifier_boundary_ref": _evaluator_ref(run_dir / "final_verifier_boundary.json"),
                    "scaffold_id": "patch_focused_react",
                    "run_task_command_log_entry_ref": {"path": command_entry_path.as_posix()},
                }
            ],
        },
    )

    with pytest.raises(Exception, match="sha256"):
        inspect_pre_verl_agentloop_boundary_index(index_path, assert_run_task_lineage=True)


def test_pre_verl_agentloop_boundary_index_requires_event_raw_ref_fingerprint(
    tmp_path: Path,
) -> None:
    run_dir = _formal_lineage_run_dir(tmp_path / "run", include_raw_provider_refs=True)
    command_entry_path = tmp_path / "run_task_command_entry.json"
    _write_json(
        command_entry_path,
        {
            "command_name": "run-task",
            "argv": ["repo-harness", "run-task", "task.yaml", "--run-id", "formal-run"],
            "exit_code": 0,
        },
    )
    events = [
        {"event_type": "run_started", "data": {}},
        {"event_type": "baseline_completed", "data": {}},
        {"event_type": "context_prepared", "data": {}},
        {"event_type": "model_call_started", "data": {"model_call_id": "model-call-1"}},
        {
            "event_type": "model_call_completed",
            "data": {
                "model_call_id": "model-call-1",
                "provider": "deepseek",
                "raw_provider_request_ref": {"relative_path": "artifacts/raw_provider_request.json"},
                "raw_provider_response_ref": {"relative_path": "artifacts/raw_provider_response.json"},
            },
        },
        {"event_type": "run_finished", "data": {}},
    ]
    (run_dir / "events.jsonl").write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )
    index_path = tmp_path / "boundary_index.json"
    _write_json(
        index_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_boundary_index_v0",
            "entries": [
                {
                    "run_task_run_dir": run_dir.as_posix(),
                    "final_verifier_boundary_ref": _evaluator_ref(run_dir / "final_verifier_boundary.json"),
                    "scaffold_id": "patch_focused_react",
                    "run_task_command_log_entry_ref": _evaluator_ref(command_entry_path),
                }
            ],
        },
    )

    with pytest.raises(Exception, match="raw_provider_request_ref.*sha256"):
        inspect_pre_verl_agentloop_boundary_index(index_path, assert_run_task_lineage=True)


def _write_pre_verl_fixture(tmp_path: Path) -> tuple[Path, Path]:
    fixtures = tmp_path / "fixtures"
    tasks_dir = fixtures / "tasks"
    repo_dir = fixtures / "repos" / "pre_verl_repo"
    evidence_dir = tasks_dir / "evaluator"
    tasks_dir.mkdir(parents=True)
    evidence_dir.mkdir()
    (repo_dir / "pkg").mkdir(parents=True)
    (repo_dir / "tests").mkdir()
    (repo_dir / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo_dir / "pkg" / "calc.py").write_text(
        'def answer() -> str:\n    return "old"\n',
        encoding="utf-8",
    )
    (repo_dir / "tests" / "__init__.py").write_text("", encoding="utf-8")

    manifest_path = evidence_dir / "pre_verl_manifest.json"
    _write_json(manifest_path, {"schema_version": "fixture_manifest_v0", "entries": []})
    hidden_patch_path = evidence_dir / "hidden_test.patch"
    hidden_patch_path.write_text(
        """diff --git a/tests/test_hidden.py b/tests/test_hidden.py
new file mode 100644
index 0000000..2d6e7c1
--- /dev/null
+++ b/tests/test_hidden.py
@@ -0,0 +1,5 @@
+from pkg.calc import answer
+
+
+def test_answer():
+    assert answer() == "new"
""",
        encoding="utf-8",
    )
    f2p_path = evidence_dir / "fail_to_pass_selectors.json"
    p2p_path = evidence_dir / "pass_to_pass_selectors.json"
    _write_json(f2p_path, ["tests/test_hidden.py::test_answer"])
    _write_json(p2p_path, [])
    replay_path = tmp_path / "replay.yaml"
    replay_path.write_text(
        """
script_id: pre_verl_success
task_id: pre_verl_order_fixture
steps:
  - step_id: read_source
    action: tool_call
    tool_call_id: call_read_source
    tool_name: read_file
    arguments:
      path: pkg/calc.py
  - step_id: edit_source
    action: tool_call
    tool_call_id: call_edit_source
    tool_name: edit_file
    arguments:
      path: pkg/calc.py
      old_text: "def answer() -> str:\\n    return \\"old\\"\\n"
      new_text: "def answer() -> str:\\n    return \\"new\\"\\n"
  - step_id: final
    action: final_answer
    assistant_text: "Updated answer() to return the expected value."
""".lstrip(),
        encoding="utf-8",
    )
    task_path = tasks_dir / "pre_verl_task.yaml"
    task = {
        "id": "pre_verl_order_fixture",
        "task_version": "pre_verl_order_fixture_v0",
        "dataset_name": "pre_verl_swebench_lite_dev_custom_subset",
        "source_kind": "swebench_lite_dev_materialized",
        "dataset_split": "dev",
        "created_at": "2026-05-07",
        "repo": "../repos/pre_verl_repo",
        "base_commit": "fixture",
        "issue": "Fix answer() so it returns the expected value.",
        "setup_command": None,
        "test_command": "python -m pytest -q",
        "timeouts": {
            "setup_timeout_sec": 60,
            "test_timeout_sec": 30,
            "agent_timeout_sec": 120,
            "final_verifier_timeout_sec": 60,
        },
        "environment": {
            "execution_image": "python:3.12-slim",
            "python_version": "3.12",
            "package_manager": "pip",
            "setup_network_policy": "deny",
        },
        "expected_files": ["pkg/calc.py"],
        "fail_to_pass_tests": ["tests/test_hidden.py::test_answer"],
        "pass_to_pass_tests": [],
        "visibility": {
            "issue": "model_visible",
            "expected_files": "model_visible",
            "fail_to_pass_tests": "verifier_only",
            "pass_to_pass_tests": "verifier_only",
            "gold_patch": "hidden_reference",
        },
        "tags": ["python"],
        "metadata": {
            "pre_verl_adapter": "swebench_lite_dev_agentloop_v0",
            "pre_verl_swebench_dev_manifest_path": manifest_path.as_posix(),
            "pre_verl_agentloop_mode": "formal_baseline",
            "pre_verl_agentloop_baseline_source": "repo_harness_agentloop_run_task",
            "swe_bench_like_final_only": True,
            "final_only": True,
            "pre_verl_setup_shell": "python -m venv .pre_verl_venv && . .pre_verl_venv/bin/activate && python -m pip install -q pytest",
            "pre_verl_verifier_command": ". .pre_verl_venv/bin/activate && python -m pytest -q",
            "source_instance_id": "fixture__pre-verl-order",
            "repo": "fixture/pre_verl_repo",
            "environment_id": "local_pytest_fixture",
            "hidden_test_patch_ref": _evaluator_ref(hidden_patch_path),
            "fail_to_pass_selectors_ref": _evaluator_ref(f2p_path),
            "pass_to_pass_selectors_ref": _evaluator_ref(p2p_path),
            "hidden_patch_clean_source_self_check_ref": {"status": "passed"},
        },
    }
    task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    config = {
        "run_id_prefix": "pre_verl_agentloop",
        "model": {
            "provider": "replay",
            "model_id": "replay-script-v0",
            "replay_script_path": replay_path.as_posix(),
        },
        "runtime": {
            "scaffold_id": "patch_focused_react",
            "execution_mode": "local_process",
            "permission_mode": "auto",
            "test_feedback_policy": "disabled",
            "max_turns": 8,
            "max_tool_calls": 20,
            "max_test_runs": 0,
            "task_timeout_sec": 120,
        },
        "workspace": {
            "output_dir": (tmp_path / "runs").as_posix(),
            "keep_workspace": True,
            "default_command_timeout_sec": 60,
        },
    }
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return task_path, config_path


def _minimal_run_dir(run_dir: Path) -> Path:
    run_dir.mkdir()
    for name in ("run_metadata.json", "metrics.json"):
        _write_json(run_dir / name, {"run_id": run_dir.name})
    for name in ("events.jsonl", "transcript.jsonl", "final.patch", "final.diff"):
        (run_dir / name).write_text("", encoding="utf-8")
    (run_dir / "artifacts").mkdir()
    return run_dir


def _formal_lineage_run_dir(run_dir: Path, *, include_raw_provider_refs: bool) -> Path:
    run_dir = _minimal_run_dir(run_dir)
    artifacts_dir = run_dir / "artifacts"
    tool_schema_path = artifacts_dir / "tool_schema.json"
    request_path = artifacts_dir / "raw_provider_request.json"
    response_path = artifacts_dir / "raw_provider_response.json"
    for path in (tool_schema_path, request_path, response_path):
        _write_json(path, {"kind": path.stem})
    _write_json(run_dir / "run_metadata.json", {"run_id": "formal-run", "scaffold_id": "patch_focused_react"})
    _write_json(
        run_dir / "run_config_facts.json",
        {
            "run_id": "formal-run",
            "final_verifier_mode": "strict_patch_replay",
            "test_feedback_policy": "disabled",
            "scaffold_id": "patch_focused_react",
            "tool_protocol": {"tool_schema_snapshot_ref": _artifact_ref(tool_schema_path, run_dir)},
        },
    )
    completed_data = {
        "model_call_id": "model-call-1",
        "provider": "deepseek",
    }
    if include_raw_provider_refs:
        completed_data.update(
            {
                "raw_provider_request_ref": _artifact_ref(request_path, run_dir),
                "raw_provider_response_ref": _artifact_ref(response_path, run_dir),
            }
        )
    events = [
        {"event_type": "run_started", "data": {}},
        {"event_type": "baseline_completed", "data": {}},
        {"event_type": "context_prepared", "data": {}},
        {"event_type": "model_call_started", "data": {"model_call_id": "model-call-1"}},
        {"event_type": "model_call_completed", "data": completed_data},
        {"event_type": "run_finished", "data": {}},
    ]
    (run_dir / "events.jsonl").write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )
    (run_dir / "transcript.jsonl").write_text("{}\n", encoding="utf-8")
    _write_json(
        run_dir / "final_verifier_boundary.json",
        {
            "schema_version": "repo_harness_pre_verl_final_verifier_boundary_v0",
            "task_id": "formal-task",
            "verifier_adapter_id": "pre_verl_swebench_lite_dev_final_verifier_v0",
            "baseline_source": "repo_harness_agentloop_run_task",
            "run_task_entrypoint": "repo-harness run-task",
            "final_verifier_timeout_sec": 60,
            "verification_workspace_source": "clean_frozen_source",
            "workspace_creation_input_ref": {"relative_path": "workspaces/source_checkout"},
            "clean_source_tree_sha256": "a" * 64,
            "patch_application_order": [
                "model_final_patch",
                "evaluator_only_hidden_test_patch",
            ],
            "observed_command_order": [],
        },
    )
    return run_dir


def _artifact_ref(path: Path, run_dir: Path) -> dict[str, object]:
    return {
        "relative_path": path.relative_to(run_dir).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def _evaluator_ref(path: Path) -> dict[str, object]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "a" * 64
    return {
        "path": path.as_posix(),
        "sha256": digest,
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "visibility": "evaluator_only",
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
