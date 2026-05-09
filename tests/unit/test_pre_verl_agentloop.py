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
    _selector_input_error,
    _selector_result_payload,
    inspect_model_visible_context,
    inspect_pre_verl_agentloop_run_config,
    inspect_pre_verl_agentloop_task_definitions,
    load_pre_verl_swebench_dev_runtime_plan,
)
from repo_harness.schema_base import stable_hash
from repo_harness.scaffolds import build_scaffold, resolve_feedback_policy
from repo_harness.tasks import RunnableTask, TaskDefinition
from repo_harness.config import load_run_config
from repo_harness.workspace.schemas import ExecutionResult


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
                    "resolved_tools": ["list_files", "read_file", "grep", "edit_file", "git_diff"],
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
                    "resolved_tools": ["list_files", "read_file", "grep", "edit_file", "git_diff"],
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
                    "resolved_tools": ["list_files", "read_file", "grep", "edit_file", "git_diff"],
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
                    "resolved_tools": ["list_files", "read_file", "grep", "edit_file", "git_diff"],
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
                    "resolved_tools": ["list_files", "read_file", "grep", "edit_file", "git_diff"],
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
) -> Path:
    config = {
        "run_id_prefix": "pre_verl_formal_baseline",
        "model": {
            "provider": provider,
            "model_id": "deepseek-v4-flash" if provider == "deepseek" else "replay-script-v0",
            "temperature": 0.0,
            "max_output_tokens": 4096,
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
