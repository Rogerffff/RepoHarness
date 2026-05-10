from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from repo_harness.errors import ConfigError
from repo_harness.pre_verl_agentloop import (
    _empty_patch_failure_attribution,
    _append_boundary_step_event,
    _file_ref,
    _selector_environment_error,
    _selector_input_error,
    _selector_result_payload,
    inspect_model_visible_context,
    inspect_pre_verl_agentloop_run_config,
    inspect_pre_verl_agentloop_task_definitions,
    load_pre_verl_swebench_dev_runtime_plan,
)
from repo_harness.schema_base import stable_hash
from repo_harness.scaffolds import PATCH_FOCUSED_REACT_TOOL_ORDER, build_scaffold, resolve_feedback_policy
from repo_harness.tasks import RunnableTask, TaskDefinition
from repo_harness.config import load_run_config
from repo_harness.trajectory import ArtifactRef, RunRecorder
from repo_harness.workspace.schemas import ExecutionResult

PRE_VERL_FINAL_ONLY_RESOLVED_TOOLS = [
    tool for tool in PATCH_FOCUSED_REACT_TOOL_ORDER if tool != "run_tests"
]


def test_pre_verl_agentloop_task_definitions_pass_formal_gates(tmp_path: Path) -> None:
    task_path = _write_task_definition(tmp_path)
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    result = inspect_pre_verl_agentloop_task_definitions(
        manifest,
        assert_run_task_compatible=True,
        assert_evaluator_only_hidden_inputs=True,
        assert_no_hidden_material_in_model_visible_fields=True,
    )

    assert "passed" in result


def test_pre_verl_agentloop_task_definitions_reject_legacy_v3_adapter(tmp_path: Path) -> None:
    task_path = _write_task_definition(
        tmp_path,
        metadata_updates={"v3_adapter": "swebench_like_fixed"},
    )
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    with pytest.raises(ConfigError, match="legacy v3_adapter=swebench_like_fixed"):
        inspect_pre_verl_agentloop_task_definitions(
            manifest,
            assert_run_task_compatible=True,
            assert_evaluator_only_hidden_inputs=True,
        )


def test_pre_verl_agentloop_task_definitions_do_not_accept_tag_only_final_only(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(
        tmp_path,
        metadata_updates={"swe_bench_like_final_only": None, "final_only": None},
        tags=["swe_bench_like_final_only", "final_only"],
    )
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    with pytest.raises(ConfigError, match="metadata.swe_bench_like_final_only"):
        inspect_pre_verl_agentloop_task_definitions(manifest, assert_run_task_compatible=True)


def test_pre_verl_agentloop_runtime_helper_rejects_missing_final_only_metadata(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(
        tmp_path,
        metadata_updates={"swe_bench_like_final_only": None, "final_only": None},
    )
    definition = TaskDefinition.model_validate(yaml.safe_load(task_path.read_text(encoding="utf-8")))

    with pytest.raises(ConfigError, match="metadata is incomplete"):
        load_pre_verl_swebench_dev_runtime_plan(RunnableTask.from_definition(definition))


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("pre_verl_adapter", "other_adapter", "metadata.pre_verl_adapter"),
        ("pre_verl_agentloop_mode", "ad_hoc", "metadata.pre_verl_agentloop_mode"),
        (
            "pre_verl_agentloop_baseline_source",
            "direct_provider_prompt",
            "metadata.pre_verl_agentloop_baseline_source",
        ),
        (
            "pre_verl_swebench_dev_manifest_path",
            ["not", "a", "string"],
            "pre_verl_swebench_dev_manifest_path must be a non-empty string",
        ),
        (
            "pre_verl_swebench_dev_manifest_path",
            "   ",
            "pre_verl_swebench_dev_manifest_path must be a non-empty string",
        ),
    ],
)
def test_pre_verl_agentloop_task_definitions_reject_bad_formal_metadata(
    tmp_path: Path,
    key: str,
    value: object,
    message: str,
) -> None:
    task_path = _write_task_definition(tmp_path, metadata_updates={key: value})
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    with pytest.raises(ConfigError, match=message):
        inspect_pre_verl_agentloop_task_definitions(manifest, assert_run_task_compatible=True)


@pytest.mark.parametrize(
    ("ref_update", "message"),
    [
        ({"visibility": "model_visible"}, "visibility=evaluator_only"),
        ({"path": 123}, "must bind path or relative_path"),
        ({"path": "   "}, "must bind path or relative_path"),
        ({"sha256": "Z" * 64}, "must bind sha256"),
        ({"sha256": "a" * 63}, "must bind sha256"),
        ({"size_bytes": -1}, "must bind non-negative size_bytes"),
    ],
)
def test_pre_verl_agentloop_task_definitions_reject_bad_evaluator_refs(
    tmp_path: Path,
    ref_update: dict[str, object],
    message: str,
) -> None:
    bad_ref = _evaluator_ref("evaluator/hidden.patch")
    bad_ref.update(ref_update)
    task_path = _write_task_definition(
        tmp_path,
        metadata_updates={"hidden_test_patch_ref": bad_ref},
    )
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    with pytest.raises(ConfigError, match=message):
        inspect_pre_verl_agentloop_task_definitions(
            manifest,
            assert_evaluator_only_hidden_inputs=True,
        )


def test_pre_verl_agentloop_task_definitions_reject_truncated_selector_ref(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    selector_path = task_path.parent / "evaluator" / "pass_to_pass.json"
    selector_path.write_text(
        '["tests/test_sample.py::test_valid["]\n',
        encoding="utf-8",
    )
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    with pytest.raises(ConfigError, match="不可 collect 的 pytest selector"):
        inspect_pre_verl_agentloop_task_definitions(
            manifest,
            assert_evaluator_only_hidden_inputs=True,
        )


def test_pre_verl_agentloop_task_definitions_accept_selector_with_colons_inside_parameter(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    selector_path = task_path.parent / "evaluator" / "pass_to_pass.json"
    selector_path.write_text(
        json.dumps(
            [
                "test/dialects/ansi_test.py::test__dialect__ansi_specific_segment_parses[ExpressionSegment-NULL::INT]"
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    result = inspect_pre_verl_agentloop_task_definitions(
        manifest,
        assert_evaluator_only_hidden_inputs=True,
    )

    assert "passed" in result


def test_pre_verl_agentloop_task_definitions_reject_hidden_visible_markers(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(
        tmp_path,
        issue="Fix the bug. hidden_test.patch should not be visible.",
    )
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    with pytest.raises(ConfigError, match="model-visible field issue contains hidden marker"):
        inspect_pre_verl_agentloop_task_definitions(
            manifest,
            assert_no_hidden_material_in_model_visible_fields=True,
        )


def test_pre_verl_selector_exit_code_four_is_not_implicitly_harness_input_error() -> None:
    assert _selector_input_error(
        {
            "exit_code": 4,
            "error_type": "test_command_error",
            "selector_input_validated": True,
            "selector_input_invalid": False,
        }
    ) is False
    assert _selector_input_error({"selector_input_invalid": True}) is True


def test_pre_verl_selector_payload_uses_per_selector_pytest_facts() -> None:
    plan = SimpleNamespace(task_id="task_001", final_verifier_timeout_sec=120)
    stdout = """
tests/test_widget.py::test_existing_a PASSED
tests/test_widget.py::test_regression FAILED
tests/test_widget.py::test_existing_b PASSED

short test summary info
FAILED tests/test_widget.py::test_regression - AssertionError: changed behavior
========================= 1 failed, 2 passed in 0.12s =========================
"""

    payload = _selector_result_payload(
        plan=plan,
        suite="pass_to_pass",
        selectors=[
            "tests/test_widget.py::test_existing_a",
            "tests/test_widget.py::test_regression",
            "tests/test_widget.py::test_existing_b",
        ],
        command=["python", "-m", "pytest", "-q"],
        result=ExecutionResult(exit_code=1, timeout=False),
        stdout=stdout,
        stderr="",
    )

    assert payload["parser_version"] == "pytest_parser_v1"
    assert payload["passed_count"] == 2
    assert payload["failed_count"] == 1
    assert payload["unknown_count"] == 0
    assert {case["test_id"]: case["status"] for case in payload["test_cases"]} == {
        "tests/test_widget.py::test_existing_a": "passed",
        "tests/test_widget.py::test_regression": "failed",
        "tests/test_widget.py::test_existing_b": "passed",
    }


def test_pre_verl_selector_payload_attributes_parameterized_selector_failures() -> None:
    plan = SimpleNamespace(task_id="task_001", final_verifier_timeout_sec=120)
    stdout = """
short test summary info
FAILED tests/cli/test_fix.py::test__cli__command_fix_stdin[stdin0-output0] - AssertionError
========================= 1 failed, 3 passed in 0.12s =========================
"""

    payload = _selector_result_payload(
        plan=plan,
        suite="pass_to_pass",
        selectors=["tests/cli/test_fix.py::test__cli__command_fix_stdin"],
        command=["python", "-m", "pytest", "-q"],
        result=ExecutionResult(exit_code=1, timeout=False),
        stdout=stdout,
        stderr="",
    )

    assert payload["failed_count"] == 1
    assert payload["passed_count"] == 0
    assert payload["test_cases"][0]["status"] == "failed"
    assert payload["test_cases"][0]["match_strategy"] == "parameterized_selector_prefix"
    assert payload["matched_failed_nodeids"] == [
        "tests/cli/test_fix.py::test__cli__command_fix_stdin[stdin0-output0]"
    ]
    assert payload["unmatched_failed_nodeids"] == []
    assert payload["selector_match_summary"]["failure_kind_counts"] == {"failed": 1}


def test_pre_verl_selector_payload_counts_error_nodeids_after_status_prefix_cleanup() -> None:
    plan = SimpleNamespace(task_id="task_001", final_verifier_timeout_sec=120)
    stdout = """
ERROR tests/test_widget.py::test_import_error - ImportError: libGL.so.1
========================= 1 error in 0.12s =========================
"""

    payload = _selector_result_payload(
        plan=plan,
        suite="fail_to_pass",
        selectors=["tests/test_widget.py::test_import_error"],
        command=["python", "-m", "pytest", "-q"],
        result=ExecutionResult(exit_code=1, timeout=False),
        stdout=stdout,
        stderr="",
    )

    assert payload["failed_count"] == 0
    assert payload["error_count"] == 1
    assert payload["error_nodeids"] == ["tests/test_widget.py::test_import_error"]
    assert payload["matched_error_nodeids"] == ["tests/test_widget.py::test_import_error"]
    assert payload["unmatched_error_nodeids"] == []
    assert payload["test_cases"][0]["status"] == "error"


def test_pre_verl_selector_payload_exposes_exit_reason_and_output_refs() -> None:
    plan = SimpleNamespace(task_id="task_001", final_verifier_timeout_sec=120)
    output_ref = ArtifactRef(
        artifact_id="out",
        relative_path="artifacts/out.txt",
        kind="command_output",
        sha256="a" * 64,
        size_bytes=1,
    )
    stdout_ref = ArtifactRef(
        artifact_id="stdout",
        relative_path="artifacts/stdout.txt",
        kind="command_stdout",
        sha256="b" * 64,
        size_bytes=0,
    )
    stderr_ref = ArtifactRef(
        artifact_id="stderr",
        relative_path="artifacts/stderr.txt",
        kind="command_stderr",
        sha256="c" * 64,
        size_bytes=21,
    )

    payload = _selector_result_payload(
        plan=plan,
        suite="fail_to_pass",
        selectors=["tests/test_widget.py::test_import_error"],
        command=["python", "-m", "pytest", "-q"],
        result=ExecutionResult(
            exit_code=4,
            timeout=False,
            stderr_preview="ImportError: libGL.so.1",
            output_artifact_ref=output_ref,
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
        ),
        stdout="",
        stderr="ImportError: libGL.so.1",
    )

    assert payload["pytest_exit_reason"] == "pytest_config_or_import_error"
    assert payload["verifier_output_unparsed"] is True
    assert "nonzero_exit_without_parsed_test_facts" in payload["parse_warnings"]
    assert payload["stdout_ref"]["artifact_id"] == "stdout"
    assert payload["stderr_ref"]["artifact_id"] == "stderr"
    assert payload["output_artifact_ref"]["artifact_id"] == "out"
    assert payload["stderr_preview"] == "ImportError: libGL.so.1"


def test_pre_verl_boundary_step_event_records_output_audit_fields(tmp_path: Path) -> None:
    stdout_ref = ArtifactRef(
        artifact_id="stdout",
        relative_path="artifacts/stdout.txt",
        kind="command_stdout",
        sha256="a" * 64,
        size_bytes=0,
    )
    stderr_ref = ArtifactRef(
        artifact_id="stderr",
        relative_path="artifacts/stderr.txt",
        kind="command_stderr",
        sha256="b" * 64,
        size_bytes=21,
    )
    with RunRecorder("run_event", tmp_path, task_id="task_001") as recorder:
        _append_boundary_step_event(
            recorder=recorder,
            plan=SimpleNamespace(task_id="task_001"),
            command_semantics="pre_verl_fail_to_pass_test_execution",
            result=ExecutionResult(
                exit_code=4,
                timeout=False,
                stderr_preview="ImportError: libGL.so.1",
                stdout_ref=stdout_ref,
                stderr_ref=stderr_ref,
            ),
        )

    event = json.loads((tmp_path / "events.jsonl").read_text(encoding="utf-8").strip())
    assert event["data"]["pytest_exit_reason"] == "pytest_config_or_import_error"
    assert event["data"]["stdout_ref"]["artifact_id"] == "stdout"
    assert event["data"]["stderr_ref"]["artifact_id"] == "stderr"
    assert event["data"]["captured_output_empty"] is False


def test_pre_verl_selector_environment_error_requires_external_library_marker() -> None:
    environment_error = _selector_environment_error(
        {
            "suite": "fail_to_pass",
            "exit_code": 4,
            "timeout": False,
            "pytest_exit_reason": "pytest_config_or_import_error",
            "stderr_preview": "ImportError: libGL.so.1: cannot open shared object file",
            "stderr_ref": {"artifact_id": "stderr"},
        }
    )

    assert environment_error is not None
    assert environment_error["failure_category"] == "final_verifier_environment_error"
    assert environment_error["failure_owner"] == "harness_or_environment"
    assert environment_error["matched_environment_error_marker"] == "cannot open shared object file"
    assert environment_error["stderr_ref"] == {"artifact_id": "stderr"}

    model_import_error = _selector_environment_error(
        {
            "suite": "pass_to_pass",
            "exit_code": 2,
            "timeout": False,
            "pytest_exit_reason": "pytest_config_or_import_error",
            "stderr_preview": "ModuleNotFoundError: No module named 'project_internal_module'",
        }
    )

    assert model_import_error is None


@pytest.mark.parametrize(
    ("agent_stop_reason", "expected_category", "expected_owner"),
    [
        ("max_turns", "budget_exhausted_empty_patch", "budget_or_timeout"),
        ("task_timeout", "budget_exhausted_empty_patch", "budget_or_timeout"),
        ("output_token_limit_reached", "output_token_limit_empty_patch", "budget_or_timeout"),
        ("context_integrity_error", "harness_context_integrity_empty_patch", "harness_or_environment"),
        ("model_error", "provider_or_model_error_empty_patch", "provider_or_model"),
        (
            "tool_call_parse_failure_unrecovered",
            "tool_call_parse_failure_unrecovered",
            "provider_or_model",
        ),
        ("final_answer", "empty_final_patch", "model_no_patch_generated"),
    ],
)
def test_empty_patch_failure_attribution_preserves_harness_and_provider_causes(
    agent_stop_reason: str,
    expected_category: str,
    expected_owner: str,
) -> None:
    assert _empty_patch_failure_attribution(agent_stop_reason) == (
        expected_category,
        expected_owner,
    )


def test_pre_verl_file_ref_accepts_run_root_prefixed_relative_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    run_root = Path("runs") / "run_001"
    run_root.mkdir(parents=True)
    target = run_root / "pre_verl_verification_workspace_creation_result.json"
    target.write_text('{"status": "ok"}\n', encoding="utf-8")

    ref = _file_ref(
        target,
        base_dir=run_root,
        artifact_id="pre_verl_verification_workspace_creation_result",
        kind="pre_verl_verification_workspace_creation_result",
        redaction_status="evaluator_only",
    )

    assert ref["relative_path"] == "pre_verl_verification_workspace_creation_result.json"
    assert ref["size_bytes"] == target.stat().st_size


def test_pre_verl_file_ref_does_not_escape_to_existing_cwd_relative_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    run_root = Path("runs") / "run_001"
    run_root.mkdir(parents=True)
    external = Path("external") / "artifact.json"
    external.parent.mkdir()
    external.write_text('{"status": "outside"}\n', encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        _file_ref(
            external,
            base_dir=run_root,
            artifact_id="external",
            kind="external",
        )


def test_pre_verl_file_ref_rejects_parent_relative_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    root = Path("runs")
    run_root = root / "run_001"
    run_root.mkdir(parents=True)
    external = root / "external.json"
    external.write_text('{"status": "outside"}\n', encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        _file_ref(
            Path("../external.json"),
            base_dir=run_root,
            artifact_id="external",
            kind="external",
        )


def test_inspect_model_visible_context_passes_bound_provider_body(tmp_path: Path) -> None:
    run_dir = _write_model_visible_context_run(tmp_path)

    result = inspect_model_visible_context(
        run_dir,
        assert_no_hidden_test_material=True,
        assert_prepared_messages_bound=True,
        assert_provider_body_equivalent=True,
        assert_tool_results_recoverable=True,
        assert_no_over_redaction=True,
    )

    assert "passed" in result


def test_inspect_model_visible_context_accepts_started_artifact_ref_binding(
    tmp_path: Path,
) -> None:
    run_dir = _write_model_visible_context_run(
        tmp_path,
        model_call_started_ref_location="artifact_refs",
    )

    result = inspect_model_visible_context(run_dir, assert_prepared_messages_bound=True)

    assert "passed" in result


def test_inspect_model_visible_context_rejects_hidden_marker(tmp_path: Path) -> None:
    run_dir = _write_model_visible_context_run(tmp_path, user_content="do not show hidden_test.patch")

    with pytest.raises(ConfigError, match="hidden_test.patch"):
        inspect_model_visible_context(run_dir, assert_no_hidden_test_material=True)


def test_inspect_model_visible_context_rejects_evaluator_only_selector_leak(tmp_path: Path) -> None:
    leaked_selector = "tests/test_private_behavior.py::test_private_case"
    run_dir = _write_model_visible_context_run(tmp_path, user_content=f"Please run {leaked_selector}")

    with pytest.raises(ConfigError, match="test_private_case"):
        inspect_model_visible_context(run_dir, assert_no_hidden_test_material=True)


def test_inspect_model_visible_context_rejects_root_relative_hidden_patch_leak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    leaked_patch_line = "hidden_private_expected_value == actual_value"
    run_dir = _write_model_visible_context_run(tmp_path, user_content=f"Maybe {leaked_patch_line} is relevant")
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    hidden_patch_path = evidence_dir / "hidden.patch"
    hidden_patch_path.write_text(f"+assert {leaked_patch_line}\n", encoding="utf-8")
    boundary_path = run_dir / "final_verifier_boundary.json"
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    boundary["hidden_test_patch_ref"] = {
        "path": "evidence/hidden.patch",
        "sha256": hashlib.sha256(hidden_patch_path.read_bytes()).hexdigest(),
        "size_bytes": hidden_patch_path.stat().st_size,
        "visibility": "evaluator_only",
    }
    boundary_path.write_text(json.dumps(boundary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ConfigError, match="hidden_private_expected_value"):
        inspect_model_visible_context(run_dir, assert_no_hidden_test_material=True)


def test_inspect_model_visible_context_allows_public_issue_text_in_hidden_patch(
    tmp_path: Path,
) -> None:
    public_issue_line = "class MySchema(Schema):"
    run_dir = _write_model_visible_context_run(tmp_path, user_content=public_issue_line)
    (run_dir / "task.yaml").write_text(
        yaml.safe_dump({"issue": f"Public reproduction:\n{public_issue_line}\n"}),
        encoding="utf-8",
    )
    hidden_patch_path = run_dir / "artifacts" / "hidden_test.patch"
    hidden_patch_path.write_text(f"+        {public_issue_line}\n", encoding="utf-8")
    boundary_path = run_dir / "final_verifier_boundary.json"
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    boundary["hidden_test_patch_ref"] = _artifact_ref_for_path(
        run_dir,
        hidden_patch_path,
        "hidden_test_patch",
    )
    boundary_path.write_text(json.dumps(boundary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = inspect_model_visible_context(run_dir, assert_no_hidden_test_material=True)

    assert "passed" in result


def test_inspect_model_visible_context_allows_public_source_text_in_hidden_patch(
    tmp_path: Path,
) -> None:
    public_source_line = "# For details: https://github.com/example/project/blob/main/LICENSE"
    run_dir = _write_model_visible_context_run(tmp_path, user_content=public_source_line)
    source_file = run_dir / "workspaces" / "source_checkout" / "pkg" / "module.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(public_source_line + "\n", encoding="utf-8")
    hidden_patch_path = run_dir / "artifacts" / "hidden_test.patch"
    hidden_patch_path.write_text(f"+{public_source_line}\n", encoding="utf-8")
    boundary_path = run_dir / "final_verifier_boundary.json"
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    boundary["hidden_test_patch_ref"] = _artifact_ref_for_path(
        run_dir,
        hidden_patch_path,
        "hidden_test_patch",
    )
    boundary_path.write_text(json.dumps(boundary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = inspect_model_visible_context(run_dir, assert_no_hidden_test_material=True)

    assert "passed" in result


def test_inspect_model_visible_context_rejects_hidden_source_text_in_hidden_patch(
    tmp_path: Path,
) -> None:
    hidden_source_line = "SECRET_ONLY_HIDDEN_TEST_VALUE = 'private'"
    run_dir = _write_model_visible_context_run(tmp_path, user_content=f"Leaked value: {hidden_source_line}")
    hidden_file = run_dir / "workspaces" / "source_checkout" / ".pre_verl_venv" / "pkg.py"
    hidden_file.parent.mkdir(parents=True)
    hidden_file.write_text(hidden_source_line + "\n", encoding="utf-8")
    hidden_patch_path = run_dir / "artifacts" / "hidden_test.patch"
    hidden_patch_path.write_text(f"+{hidden_source_line}\n", encoding="utf-8")
    boundary_path = run_dir / "final_verifier_boundary.json"
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    boundary["hidden_test_patch_ref"] = _artifact_ref_for_path(
        run_dir,
        hidden_patch_path,
        "hidden_test_patch",
    )
    boundary_path.write_text(json.dumps(boundary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="SECRET_ONLY_HIDDEN_TEST_VALUE"):
        inspect_model_visible_context(run_dir, assert_no_hidden_test_material=True)


def test_inspect_model_visible_context_accepts_compaction_artifacts(tmp_path: Path) -> None:
    run_dir = _write_model_visible_context_run(tmp_path)
    _add_auto_compact_inspect_fixture(run_dir)
    _add_ptl_truncation_inspect_fixture(run_dir)

    result = inspect_model_visible_context(
        run_dir,
        assert_prepared_messages_bound=True,
        assert_no_hidden_test_material=True,
    )

    assert "passed" in result


def test_inspect_model_visible_context_accepts_plain_auto_compact_applied_shape(
    tmp_path: Path,
) -> None:
    run_dir = _write_model_visible_context_run(tmp_path)
    _add_auto_compact_inspect_fixture(
        run_dir,
        applied_event_type="auto_compact_applied",
        include_ordinary_assistant_flag=False,
    )

    result = inspect_model_visible_context(
        run_dir,
        assert_prepared_messages_bound=True,
        assert_no_hidden_test_material=True,
    )

    assert "passed" in result


def test_inspect_model_visible_context_rejects_hidden_auto_compact_summary(
    tmp_path: Path,
) -> None:
    run_dir = _write_model_visible_context_run(tmp_path)
    _add_auto_compact_inspect_fixture(
        run_dir,
        summary_updates={"task_intent": "Do not expose hidden_test.patch"},
    )

    with pytest.raises(ConfigError, match="auto_compact_summary"):
        inspect_model_visible_context(
            run_dir,
            assert_prepared_messages_bound=True,
            assert_no_hidden_test_material=True,
        )


def test_inspect_model_visible_context_rejects_context_limit_transcript_pollution(
    tmp_path: Path,
) -> None:
    run_dir = _write_model_visible_context_run(tmp_path)
    _append_events(
        run_dir,
        [
            {
                "event_type": "reactive_compact_triggered",
                "data": {
                    "model_call_id": "rejected_context_limit_call",
                    "terminal_error_type": "context_limit",
                    "ordinary_assistant_message_appended": False,
                    "trainable": False,
                },
            }
        ],
    )
    _append_transcript(
        run_dir,
        [
            {
                "role": "assistant",
                "model_visible": True,
                "trainable": False,
                "model_call_id": "rejected_context_limit_call",
                "content_preview": "provider context limit rejected this input",
            }
        ],
    )

    with pytest.raises(ConfigError, match="provider 拒绝的 context_limit 调用"):
        inspect_model_visible_context(run_dir, assert_prepared_messages_bound=True)


def test_inspect_model_visible_context_rejects_compact_only_transcript_action(
    tmp_path: Path,
) -> None:
    run_dir = _write_model_visible_context_run(tmp_path)
    _add_auto_compact_inspect_fixture(run_dir)
    _append_transcript(
        run_dir,
        [
            {
                "role": "assistant",
                "model_visible": True,
                "trainable": True,
                "model_call_id": "compact_model_call_1",
                "content_preview": "compact-only response should not be an ordinary action",
            }
        ],
    )

    with pytest.raises(ConfigError, match="compact-only model call"):
        inspect_model_visible_context(run_dir, assert_prepared_messages_bound=True)


def test_inspect_model_visible_context_rejects_auto_compact_event_ref_mismatch(
    tmp_path: Path,
) -> None:
    run_dir = _write_model_visible_context_run(tmp_path)
    _add_auto_compact_inspect_fixture(run_dir)
    events = _read_events(run_dir)
    for event in events:
        if event["event_type"] == "reactive_compact_applied":
            summary_ref = dict(event["artifact_refs"][1])
            summary_ref["sha256"] = "0" * 64
            event["data"]["summary_artifact_ref"] = summary_ref
    _write_events(run_dir, events)

    with pytest.raises(ConfigError, match="summary_artifact_ref 与 auto_compact_record 不一致"):
        inspect_model_visible_context(run_dir, assert_prepared_messages_bound=True)


@pytest.mark.parametrize("leak_target", ["prepared_messages", "transcript", "raw_provider_request"])
def test_inspect_model_visible_context_rejects_evaluator_only_ref_sha_leak(
    tmp_path: Path,
    leak_target: str,
) -> None:
    run_dir = _write_model_visible_context_run(tmp_path)
    boundary = json.loads((run_dir / "final_verifier_boundary.json").read_text(encoding="utf-8"))
    hidden_sha = boundary["hidden_test_patch_ref"]["sha256"]
    if leak_target == "prepared_messages":
        prepared_path = run_dir / "artifacts" / "prepared_messages.json"
        prepared_payload = json.loads(prepared_path.read_text(encoding="utf-8"))
        prepared_payload["messages"][1]["content"] = f"maybe hidden sha {hidden_sha}"
        prepared_path.write_text(
            json.dumps(prepared_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        _refresh_event_ref_for_artifact(run_dir, "artifacts/prepared_messages.json")
    elif leak_target == "transcript":
        transcript = [
            {
                "role": "user",
                "model_visible": True,
                "content_preview": f"maybe hidden sha {hidden_sha}",
            }
        ]
        (run_dir / "transcript.jsonl").write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in transcript),
            encoding="utf-8",
        )
    else:
        request_path = run_dir / "artifacts" / "raw_provider_request.json"
        request_payload = json.loads(request_path.read_text(encoding="utf-8"))
        request_payload["body"]["messages"][1]["content"] = f"maybe hidden sha {hidden_sha}"
        request_path.write_text(
            json.dumps(request_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        _refresh_event_ref_for_artifact(run_dir, "artifacts/raw_provider_request.json")

    with pytest.raises(ConfigError, match=hidden_sha[:24]):
        inspect_model_visible_context(run_dir, assert_no_hidden_test_material=True)


def test_inspect_model_visible_context_allows_empty_artifact_sha_in_public_tool_result(
    tmp_path: Path,
) -> None:
    run_dir = _write_model_visible_context_run(tmp_path)
    prepared_path = run_dir / "artifacts" / "prepared_messages.json"
    prepared_payload = json.loads(prepared_path.read_text(encoding="utf-8"))
    empty_sha = hashlib.sha256(b"").hexdigest()
    prepared_payload["messages"].append(
        {
            "role": "tool",
            "tool_call_id": "call_diff",
            "tool_result_id": "call_diff_result",
            "tool_name": "git_diff",
            "content": "No diff.",
            "typed": {"diff_sha256": empty_sha, "changed_file_count": 0},
        }
    )
    prepared_path.write_text(
        json.dumps(prepared_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _refresh_event_ref_for_artifact(run_dir, "artifacts/prepared_messages.json")
    boundary_path = run_dir / "final_verifier_boundary.json"
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    empty_patch_path = run_dir / "final.patch"
    empty_patch_path.write_text("", encoding="utf-8")
    empty_ref = _artifact_ref_for_path(run_dir, empty_patch_path, "final_patch")
    empty_ref["redaction_status"] = "evaluator_only"
    boundary["final_patch_ref"] = empty_ref
    boundary_path.write_text(json.dumps(boundary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = inspect_model_visible_context(run_dir, assert_no_hidden_test_material=True)

    assert "passed" in result


def test_inspect_model_visible_context_rejects_whole_field_redaction(tmp_path: Path) -> None:
    run_dir = _write_model_visible_context_run(tmp_path, user_content="<REDACTED_CREDENTIAL>")

    with pytest.raises(ConfigError, match="整字段 credential 脱敏"):
        inspect_model_visible_context(run_dir, assert_no_over_redaction=True)


def test_inspect_model_visible_context_rejects_redacted_replacement_sha256(
    tmp_path: Path,
) -> None:
    run_dir = _write_model_visible_context_run(
        tmp_path,
        replacement_content=(
            "[tool result replaced]\n"
            "tool_name: read_file\n"
            f"sha256: {'a' * 64}\n"
            "recovery_call: read_file(path='src/demo.py', start_line=20)\n"
            "recovery_hint: continue reading\n"
            "preview_redacted: source artifact is evaluator-only or secret\n"
        ),
    )

    with pytest.raises(ConfigError, match="sha256"):
        inspect_model_visible_context(run_dir, assert_tool_results_recoverable=True)


def test_inspect_model_visible_context_recomputes_provider_projection_hash(tmp_path: Path) -> None:
    run_dir = _write_model_visible_context_run(tmp_path)
    request_path = run_dir / "artifacts" / "raw_provider_request.json"
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    request_payload["body"]["messages"][1]["content"] = "different provider body"
    request_path.write_text(json.dumps(request_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _refresh_event_artifact_ref(run_dir, "raw_provider_request.json")

    with pytest.raises(ConfigError, match="projection"):
        inspect_model_visible_context(run_dir, assert_provider_body_equivalent=True)


def test_inspect_model_visible_context_rejects_mismatched_response_request_ref(tmp_path: Path) -> None:
    run_dir = _write_model_visible_context_run(tmp_path)
    response_path = run_dir / "artifacts" / "raw_provider_response.json"
    response_payload = json.loads(response_path.read_text(encoding="utf-8"))
    response_payload["raw_provider_request_ref"]["sha256"] = "9" * 64
    response_path.write_text(json.dumps(response_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _refresh_event_artifact_ref(run_dir, "raw_provider_response.json")

    with pytest.raises(ConfigError, match="raw_provider_request_ref"):
        inspect_model_visible_context(run_dir, assert_provider_body_equivalent=True)


def test_pre_verl_agentloop_run_config_passes_formal_gates(tmp_path: Path) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(tmp_path, test_feedback_policy="disabled", max_test_runs=0)
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                    "resolved_tools": PRE_VERL_FINAL_ONLY_RESOLVED_TOOLS,
                }
            ]
        },
    )

    result = inspect_pre_verl_agentloop_run_config(
        manifest,
        assert_final_only_test_feedback_disabled=True,
        assert_resolved_tools_derived=True,
        assert_no_hidden_feedback_visible=True,
    )

    assert "passed" in result


def test_pre_verl_agentloop_run_config_rejects_structured_public_feedback(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="structured_public_feedback",
        max_test_runs=4,
    )
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="test_feedback_policy=disabled"):
        inspect_pre_verl_agentloop_run_config(
            manifest,
            assert_final_only_test_feedback_disabled=True,
            assert_no_hidden_feedback_visible=True,
        )


def test_pre_verl_agentloop_run_config_rejects_deepseek_without_formal_reasoning_policy(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="disabled",
        max_test_runs=0,
        provider="deepseek",
        execution_mode="local_process",
        provider_specific_options={"allow_local_secret_file": True},
    )
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                    "resolved_tools": PRE_VERL_FINAL_ONLY_RESOLVED_TOOLS,
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="execution_mode=docker"):
        inspect_pre_verl_agentloop_run_config(
            manifest,
            assert_final_only_test_feedback_disabled=True,
            assert_resolved_tools_derived=True,
            assert_no_hidden_feedback_visible=True,
        )


def test_pre_verl_agentloop_run_config_rejects_deepseek_without_provider_retry(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="disabled",
        max_test_runs=0,
        provider="deepseek",
        execution_mode="docker",
        provider_specific_options={
            "allow_local_secret_file": True,
            "thinking": {"type": "enabled"},
            "reasoning_compatibility": "provider_private_state_replay",
        },
        docker_build_base_image="python:3.12-slim",
        retry_policy="none",
    )
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                    "resolved_tools": PRE_VERL_FINAL_ONLY_RESOLVED_TOOLS,
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="model.retry_policy=provider_retry_v0"):
        inspect_pre_verl_agentloop_run_config(
            manifest,
            assert_final_only_test_feedback_disabled=True,
            assert_resolved_tools_derived=True,
            assert_no_hidden_feedback_visible=True,
        )


def test_pre_verl_agentloop_run_config_rejects_deepseek_docker_image_mismatch(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="disabled",
        max_test_runs=0,
        provider="deepseek",
        execution_mode="docker",
        provider_specific_options={
            "allow_local_secret_file": True,
            "thinking": {"type": "enabled"},
            "reasoning_compatibility": "provider_private_state_replay",
        },
        docker_build_base_image="python:3.11-slim",
    )
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                    "resolved_tools": PRE_VERL_FINAL_ONLY_RESOLVED_TOOLS,
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="docker_backend.build_base_image"):
        inspect_pre_verl_agentloop_run_config(
            manifest,
            assert_final_only_test_feedback_disabled=True,
            assert_resolved_tools_derived=True,
            assert_no_hidden_feedback_visible=True,
        )


def test_pre_verl_agentloop_run_config_rejects_deepseek_missing_task_image(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path, execution_image=None)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="disabled",
        max_test_runs=0,
        provider="deepseek",
        execution_mode="docker",
        provider_specific_options={
            "allow_local_secret_file": True,
            "thinking": {"type": "enabled"},
            "reasoning_compatibility": "provider_private_state_replay",
        },
        docker_build_base_image="python:3.12-slim",
    )
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                    "resolved_tools": PRE_VERL_FINAL_ONLY_RESOLVED_TOOLS,
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="environment.execution_image"):
        inspect_pre_verl_agentloop_run_config(
            manifest,
            assert_final_only_test_feedback_disabled=True,
            assert_resolved_tools_derived=True,
            assert_no_hidden_feedback_visible=True,
        )


def test_pre_verl_agentloop_run_config_rejects_deepseek_thinking_without_compatibility(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="disabled",
        max_test_runs=0,
        provider="deepseek",
        execution_mode="docker",
        provider_specific_options={
            "allow_local_secret_file": True,
            "thinking": {"type": "enabled"},
        },
        docker_build_base_image="python:3.12-slim",
    )
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                    "resolved_tools": PRE_VERL_FINAL_ONLY_RESOLVED_TOOLS,
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="reasoning_compatibility=provider_private_state_replay"):
        inspect_pre_verl_agentloop_run_config(
            manifest,
            assert_final_only_test_feedback_disabled=True,
            assert_resolved_tools_derived=True,
            assert_no_hidden_feedback_visible=True,
        )


def test_feedback_policy_rejects_non_disabled_for_swebench_like_final_only(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="structured_public_feedback",
        max_test_runs=4,
    )
    definition = TaskDefinition.model_validate(yaml.safe_load(task_path.read_text(encoding="utf-8")))
    config = load_run_config(config_path)
    scaffold = build_scaffold("patch_focused_react")

    with pytest.raises(ConfigError, match="SWE-Bench-like final-only task requires"):
        resolve_feedback_policy(run_config=config, scaffold=scaffold, task=definition)


def _write_task_definition(
    tmp_path: Path,
    *,
    metadata_updates: dict[str, object] | None = None,
    issue: str = "Fix the parser bug without using hidden verifier material.",
    tags: list[str] | None = None,
    execution_image: str | None = "python:3.12-slim",
) -> Path:
    fixtures = tmp_path / "fixtures"
    tasks_dir = fixtures / "tasks"
    repo_dir = fixtures / "repos" / "sample_repo"
    evaluator_dir = tasks_dir / "evaluator"
    tasks_dir.mkdir(parents=True)
    repo_dir.mkdir(parents=True)
    evaluator_dir.mkdir()
    metadata = {
        "pre_verl_adapter": "swebench_lite_dev_agentloop_v0",
        "pre_verl_swebench_dev_manifest_path": "runs/pre_verl/dev_manifest.json",
        "pre_verl_agentloop_mode": "formal_baseline",
        "pre_verl_agentloop_baseline_source": "repo_harness_agentloop_run_task",
        "swe_bench_like_final_only": True,
        "final_only": True,
        "hidden_test_patch_ref": _evaluator_ref("evaluator/hidden.patch"),
        "fail_to_pass_selectors_ref": _evaluator_ref("evaluator/fail_to_pass.json"),
        "pass_to_pass_selectors_ref": _evaluator_ref("evaluator/pass_to_pass.json"),
    }
    if metadata_updates:
        for key, value in metadata_updates.items():
            if value is None:
                metadata.pop(key, None)
            else:
                metadata[key] = value
    task = {
        "id": "pre_verl_formal_task",
        "task_version": "pre_verl_formal_task_v0",
        "dataset_name": "pre_verl_swebench_lite_dev_custom_subset",
        "source_kind": "swebench_lite_dev_materialized",
        "dataset_split": "dev",
        "created_at": "2026-05-07",
        "repo": "../repos/sample_repo",
        "base_commit": "fixture",
        "issue": issue,
        "setup_command": None,
        "test_command": "pytest -q",
        "timeouts": {
            "setup_timeout_sec": 60,
            "test_timeout_sec": 30,
            "agent_timeout_sec": 120,
            "final_verifier_timeout_sec": 60,
        },
        "environment": {
            "execution_image": execution_image,
            "python_version": "3.12",
            "package_manager": "pip",
            "setup_network_policy": "deny",
        },
        "expected_files": ["src/sample.py"],
        "fail_to_pass_tests": ["tests/test_sample.py::test_bug"],
        "pass_to_pass_tests": ["tests/test_sample.py::test_existing"],
        "visibility": {
            "issue": "model_visible",
            "expected_files": "model_visible",
            "fail_to_pass_tests": "verifier_only",
            "pass_to_pass_tests": "verifier_only",
            "gold_patch": "hidden_reference",
        },
        "tags": tags or ["python"],
        "metadata": metadata,
    }
    task_path = tasks_dir / "formal_task.yaml"
    task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
    return task_path


def _write_run_config(
    tmp_path: Path,
    *,
    test_feedback_policy: str,
    max_test_runs: int,
    provider: str = "replay",
    execution_mode: str = "local_process",
    provider_specific_options: dict[str, object] | None = None,
    docker_build_base_image: str | None = None,
    retry_policy: str | None = None,
) -> Path:
    config = {
        "run_id_prefix": "pre_verl_formal_baseline",
        "model": {
            "provider": provider,
            "model_id": "deepseek-v4-flash" if provider == "deepseek" else "replay-script-v0",
            "temperature": 0.0,
            "max_output_tokens": 4096,
            "retry_policy": retry_policy
            if retry_policy is not None
            else ("provider_retry_v0" if provider in {"deepseek", "openai"} else "none"),
            "provider_specific_options": provider_specific_options or {},
        },
        "runtime": {
            "scaffold_id": "patch_focused_react",
            "execution_mode": execution_mode,
            "permission_mode": "auto",
            "test_feedback_policy": test_feedback_policy,
            "feedback_tests_passed_policy": "require_model_final",
            "max_turns": 24,
            "max_tool_calls": 96,
            "max_test_runs": max_test_runs,
            "task_timeout_sec": 1200,
        },
        "workspace": {
            "output_dir": str(tmp_path / "runs"),
            "keep_workspace": True,
            "default_command_timeout_sec": 90,
            "network_policy": "deny_agent_run",
        },
    }
    if docker_build_base_image is not None:
        config["runtime"]["docker_backend"] = {
            "build_base_image": docker_build_base_image,
            "image_ref": "repo-harness-pre-verl-test:v0",
        }
    config_path = tmp_path / "formal_run_config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return config_path


def _write_manifest(tmp_path: Path, payload: dict[str, object]) -> Path:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return manifest


def _rel(base: Path, path: Path) -> str:
    return path.relative_to(base).as_posix()


def _write_model_visible_context_run(
    tmp_path: Path,
    *,
    user_content: str = "Fix the parser bug.",
    replacement_content: str | None = None,
    model_call_started_ref_location: str = "data",
) -> Path:
    run_dir = tmp_path / "model_visible_run"
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)
    prepared_messages = {
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": user_content},
            {
                "role": "tool",
                "tool_call_id": "call_read",
                "tool_result_id": "call_read_result",
                "tool_name": "read_file",
                "content": replacement_content
                or (
                    "[tool result replaced]\n"
                    "tool_name: read_file\n"
                    "recovery_call: read_file(path='src/demo.py', start_line=20)\n"
                    "recovery_hint: continue reading\n"
                ),
                "context_replacement": True,
            },
        ]
    }
    prepared_ref = _write_json_ref(run_dir, artifacts_dir / "prepared_messages.json", prepared_messages, "prepared_messages")
    tool_schema_ref = _write_json_ref(
        run_dir,
        artifacts_dir / "tool_schema_snapshot.json",
        {"snapshot_sha256": "b" * 64},
        "tool_schema_snapshot",
    )
    body_messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": user_content},
        {
            "role": "tool",
            "tool_call_id": "call_read",
            "content": prepared_messages["messages"][2]["content"],
        },
    ]
    projection_hash = stable_hash(body_messages)
    raw_request = {
        "export_allowed": False,
        "training_payload_allowed": False,
        "body": {"messages": body_messages},
        "prepared_messages_ref": prepared_ref,
        "tool_schema_snapshot_ref": tool_schema_ref,
        "model_input_hash": "a" * 64,
        "provider_body_hash_before_redaction": "c" * 64,
        "redacted_body_hash": "d" * 64,
        "provider_body_message_projection_hash": projection_hash,
        "prepared_messages_projection_hash": projection_hash,
        "prepared_messages_body_equivalent": True,
        "redaction_report": {
            "ordinary_text_whole_field_redaction_allowed": False,
        },
    }
    raw_request_ref = _write_json_ref(
        run_dir,
        artifacts_dir / "raw_provider_request.json",
        raw_request,
        "raw_provider_request",
    )
    raw_response = {
        "export_allowed": False,
        "training_payload_allowed": False,
        "raw_provider_request_ref": raw_request_ref,
        "prepared_messages_ref": prepared_ref,
        "tool_schema_snapshot_ref": tool_schema_ref,
        "response_body_hash_before_redaction": "f" * 64,
        "redacted_response_body_hash": "f" * 64,
        "parsed_tool_calls_hash": stable_hash({"error": None, "tool_calls": []}),
        "finish_reason": "stop",
    }
    raw_response_ref = _write_json_ref(
        run_dir,
        artifacts_dir / "raw_provider_response.json",
        raw_response,
        "raw_provider_response",
    )
    hidden_patch_ref = _write_text_ref(
        run_dir,
        artifacts_dir / "hidden_test.patch",
        "+assert hidden_private_expected_value == actual_value\n",
        "hidden_test_patch",
    )
    fail_to_pass_ref = _write_json_ref(
        run_dir,
        artifacts_dir / "fail_to_pass_selectors.json",
        ["tests/test_private_behavior.py::test_private_case"],
        "fail_to_pass_selectors",
    )
    pass_to_pass_ref = _write_json_ref(
        run_dir,
        artifacts_dir / "pass_to_pass_selectors.json",
        ["tests/test_public.py::test_existing"],
        "pass_to_pass_selectors",
    )
    (run_dir / "final_verifier_boundary.json").write_text(
        json.dumps(
            {
                "hidden_test_patch_ref": hidden_patch_ref,
                "fail_to_pass_selectors_ref": fail_to_pass_ref,
                "pass_to_pass_selectors_ref": pass_to_pass_ref,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    events = [
        {
            "event_type": "context_prepared",
            "data": {"prepared_messages_ref": prepared_ref},
            "artifact_refs": [prepared_ref],
        },
        (
            {
                "event_type": "model_call_started",
                "data": {"model_call_id": "model-call-1"},
                "artifact_refs": [prepared_ref],
            }
            if model_call_started_ref_location == "artifact_refs"
            else {"event_type": "model_call_started", "data": {"prepared_messages_ref": prepared_ref}}
        ),
        {
            "event_type": "model_call_completed",
            "data": {
                "raw_provider_request_ref": raw_request_ref,
                "raw_provider_response_ref": raw_response_ref,
            },
        },
    ]
    (run_dir / "events.jsonl").write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )
    transcript = [
        {
            "role": "user",
            "model_visible": True,
            "content_preview": user_content,
        }
    ]
    (run_dir / "transcript.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in transcript),
        encoding="utf-8",
    )
    return run_dir


def _add_auto_compact_inspect_fixture(
    run_dir: Path,
    *,
    summary_updates: dict[str, object] | None = None,
    applied_event_type: str = "reactive_compact_applied",
    include_ordinary_assistant_flag: bool = True,
) -> None:
    artifacts_dir = run_dir / "artifacts"
    events = _read_events(run_dir)
    prepared_ref = events[0]["data"]["prepared_messages_ref"]
    compact_id = "compact_inspect_1"
    source_ref = _write_json_ref(
        run_dir,
        artifacts_dir / "auto_compact_source_messages.json",
        {
            "schema_version": "repo_harness_auto_compact_source_messages_v1",
            "policy_version": "repo_harness_auto_compact_v1",
            "compact_id": compact_id,
            "mode": "emergency",
            "trigger_reason": "provider_context_limit_retry",
            "source_prepared_messages_ref": prepared_ref,
            "source_model_input_hash": "a" * 64,
            "provider_visible_source_messages": [{"role": "user", "content": "Fix"}],
            "compact_request_messages": [{"role": "user", "content": "Summarize"}],
            "provider_visible_projection_applied": True,
        },
        "auto_compact_source_messages",
    )
    model_call_ref = _write_json_ref(
        run_dir,
        artifacts_dir / "auto_compact_model_call.json",
        {
            "schema_version": "repo_harness_auto_compact_model_call_v1",
            "policy_version": "repo_harness_auto_compact_v1",
            "compact_id": compact_id,
            "model_call_id": "compact_model_call_1",
            "trainable": False,
            "scaffold_phase": "compact",
            "allowed_tools": [],
            "tool_choice": "none",
        },
        "auto_compact_model_call",
    )
    summary = {
        "schema_version": "repo_harness_compact_summary_v1",
        "task_intent": "Fix the parser bug.",
        "repository_facts": ["src/demo.py is relevant."],
        "actions_taken": ["Read the current failure context."],
        "patch_state": {"changed_files": [], "important_diffs": []},
        "test_state": {"commands_run": [], "passing": [], "failing": [], "unknown": []},
        "tool_recovery_index": [
            {
                "schema_version": "repo_harness_compact_tool_recovery_entry_v1",
                "tool_result_id": None,
                "tool_call_id": None,
                "tool_name": None,
                "artifact_id": None,
                "sha256": None,
                "recovery_status": "not_needed",
            }
        ],
        "open_questions": [],
        "next_step": "Continue from compacted context.",
        "visibility_policy": "model_visible_only",
    }
    if summary_updates:
        summary.update(summary_updates)
    summary_ref = _write_json_ref(
        run_dir,
        artifacts_dir / "auto_compact_summary.json",
        {
            "schema_version": "repo_harness_auto_compact_summary_artifact_v1",
            "policy_version": "repo_harness_auto_compact_v1",
            "compact_id": compact_id,
            "summary": summary,
            "source_prepared_messages_ref": prepared_ref,
            "source_model_input_hash": "a" * 64,
            "visibility_policy": "model_visible_only",
            "trainable": False,
        },
        "auto_compact_summary",
    )
    rebuilt_ref = _write_json_ref(
        run_dir,
        artifacts_dir / "auto_compact_rebuilt_messages.json",
        {
            "schema_version": "repo_harness_auto_compact_rebuilt_messages_v1",
            "policy_version": "repo_harness_auto_compact_v1",
            "compact_id": compact_id,
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "repo_harness_auto_compact_summary": summary,
                    },
                    "metadata": {"trainable": False},
                }
            ],
            "source_prepared_messages_ref": prepared_ref,
            "summary_artifact_ref": summary_ref,
            "trainable": False,
        },
        "auto_compact_rebuilt_messages",
    )
    record_ref = _write_json_ref(
        run_dir,
        artifacts_dir / "auto_compact_record.json",
        {
            "schema_version": "repo_harness_auto_compact_record_v1",
            "compact_id": compact_id,
            "trigger_reason": "provider_context_limit_retry",
            "mode": "emergency",
            "source_prepared_messages_ref": prepared_ref,
            "source_model_input_hash": "a" * 64,
            "compact_source_messages_ref": source_ref,
            "compact_source_projection_hash": "b" * 64,
            "tokens_before": 1000,
            "tokens_after": 400,
            "effective_context_budget_tokens": 900,
            "summary_artifact_ref": summary_ref,
            "compact_model_call_ref": model_call_ref,
            "rebuilt_messages_ref": rebuilt_ref,
            "post_compact_above_target": False,
            "status": "applied",
            "failure_reason": None,
        },
        "auto_compact_record",
    )
    applied_event_data = {
        "compact_id": compact_id,
        "trigger_reason": "provider_context_limit_retry",
        "mode": "emergency",
        "source_prepared_messages_ref": prepared_ref,
        "summary_artifact_ref": summary_ref,
        "rebuilt_messages_ref": rebuilt_ref,
        "tokens_before": 1000,
        "tokens_after": 400,
        "effective_context_budget_tokens": 900,
        "post_compact_above_target": False,
        "trainable": False,
    }
    if include_ordinary_assistant_flag:
        applied_event_data["ordinary_assistant_message_appended"] = False
    _append_events(
        run_dir,
        [
            {
                "event_type": "auto_compact_model_call_started",
                "artifact_refs": [source_ref],
                "data": {
                    "model_call_id": "compact_model_call_1",
                    "scaffold_phase": "compact",
                    "allowed_tools": [],
                    "tool_choice": "none",
                    "trainable": False,
                },
            },
            {
                "event_type": applied_event_type,
                "artifact_refs": [record_ref, summary_ref, rebuilt_ref],
                "data": applied_event_data,
            },
        ],
    )


def _add_ptl_truncation_inspect_fixture(run_dir: Path) -> None:
    artifacts_dir = run_dir / "artifacts"
    events = _read_events(run_dir)
    prepared_ref = events[0]["data"]["prepared_messages_ref"]
    completed = next(event for event in events if event["event_type"] == "model_call_completed")
    raw_request_ref = completed["data"]["raw_provider_request_ref"]
    raw_response_ref = completed["data"]["raw_provider_response_ref"]
    record = {
        "schema_version": "repo_harness_ptl_truncation_record_v1",
        "policy": "auto_compact_then_round_truncate",
        "reason": "provider_context_limit_retry",
        "original_model_call_id": "rejected_context_limit_call",
        "original_prepared_messages_ref": prepared_ref,
        "original_model_input_hash": "a" * 64,
        "original_provider_request_ref": raw_request_ref,
        "original_provider_response_ref": raw_response_ref,
        "emergency_compact_record_ref": None,
        "emergency_compact_failure_reason": "invalid_compact_summary:ValueError",
        "ordinary_turn": 1,
        "loop_turn": 1,
        "synthetic_marker_id": "ptl_marker_demo",
        "synthetic_marker_message": {
            "role": "user",
            "content": {"repo_harness_ptl_truncation_marker": {"omitted_round_count": 1}},
            "metadata": {"synthetic": True, "trainable": False},
        },
        "omitted_rounds": [{"group_id": "round_0001", "roles": ["assistant", "tool"]}],
        "retained_rounds": [{"group_id": "round_0002", "roles": ["user"]}],
        "omitted_round_count": 1,
        "retained_round_count": 1,
        "message_count_before": 5,
        "message_count_after": 4,
        "token_estimate_before": 1200,
        "token_estimate_after": 700,
        "hard_context_limit_tokens": 1000,
        "post_truncation_above_hard_limit": False,
        "tool_pairing_preservation_policy": "drop_complete_rounds_only_v1",
        "trainable": False,
    }
    ptl_ref = _write_json_ref(
        run_dir,
        artifacts_dir / "ptl_truncation_record.json",
        record,
        "ptl_truncation_record",
    )
    _append_events(
        run_dir,
        [
            {
                "event_type": "ptl_truncation_applied",
                "artifact_refs": [ptl_ref],
                "data": {
                    "ptl_truncation_ref": ptl_ref,
                    "original_model_call_id": "rejected_context_limit_call",
                    "omitted_round_count": 1,
                    "synthetic_marker_id": "ptl_marker_demo",
                    "token_estimate_before": 1200,
                    "token_estimate_after": 700,
                    "post_truncation_above_hard_limit": False,
                    "trainable": False,
                },
            }
        ],
    )


def _read_events(run_dir: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _append_events(run_dir: Path, events: list[dict[str, object]]) -> None:
    with (run_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _write_events(run_dir: Path, events: list[dict[str, object]]) -> None:
    (run_dir / "events.jsonl").write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )


def _append_transcript(run_dir: Path, records: list[dict[str, object]]) -> None:
    with (run_dir / "transcript.jsonl").open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_json_ref(run_dir: Path, path: Path, payload: object, kind: str) -> dict[str, object]:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return _artifact_ref_for_path(run_dir, path, kind)


def _write_text_ref(run_dir: Path, path: Path, text: str, kind: str) -> dict[str, object]:
    path.write_text(text, encoding="utf-8")
    return _artifact_ref_for_path(run_dir, path, kind)


def _artifact_ref_for_path(run_dir: Path, path: Path, kind: str) -> dict[str, object]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "schema_version": "repo_harness_artifact_ref_v0",
        "artifact_id": path.stem,
        "relative_path": path.relative_to(run_dir).as_posix(),
        "kind": kind,
        "sha256": digest,
        "size_bytes": path.stat().st_size,
        "redaction_status": "redacted" if "raw_provider" in kind else "not_required",
        "retention_policy": "keep",
    }


def _refresh_event_artifact_ref(run_dir: Path, artifact_filename: str) -> None:
    _refresh_event_ref_for_artifact(run_dir, f"artifacts/{artifact_filename}")


def _refresh_event_ref_for_artifact(run_dir: Path, relative_path: str) -> None:
    artifact_path = run_dir / relative_path
    digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    size_bytes = artifact_path.stat().st_size
    _refresh_refs_in_events(run_dir, relative_path, digest, size_bytes)


def _refresh_refs_in_events(
    run_dir: Path,
    relative_path: str,
    digest: str,
    size_bytes: int,
) -> None:
    def refresh(value: object) -> None:
        if isinstance(value, dict):
            if value.get("relative_path") == relative_path:
                value["sha256"] = digest
                value["size_bytes"] = size_bytes
            for child in value.values():
                refresh(child)
        elif isinstance(value, list):
            for child in value:
                refresh(child)

    events = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    refresh(events)
    (run_dir / "events.jsonl").write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )


def _evaluator_ref(path: str) -> dict[str, object]:
    return {
        "path": path,
        "sha256": "a" * 64,
        "size_bytes": 1,
        "visibility": "evaluator_only",
    }
