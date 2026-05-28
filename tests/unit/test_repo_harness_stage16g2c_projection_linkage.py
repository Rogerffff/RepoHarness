import json
from pathlib import Path

import pytest

from repo_harness.errors import RepoHarnessError
from repo_harness.permissions import PermissionContext
from repo_harness.rl.visibility import validate_no_forbidden_model_visible_content
from repo_harness.stage16g2_file_surface import (
    inspect_stage16g2c_projection_linkage,
    scan_stage16g2c_public_files,
)
from repo_harness.tools import ToolExecutionContext, ToolExecutor
from repo_harness.tools.schemas import ToolCall
from repo_harness.trajectory import RunRecorder
from repo_harness.workspace import DependencyState, LocalWorkspaceAdapter, RunWorkspace
from scripts.pre_verl.build_stage16g2c_projection_linkage import write_stage16g2c_reports


def _sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _refresh_summary_digest(output_dir: Path, filename: str, digest_field: str) -> None:
    summary_path = output_dir / "stage16g2c_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary[digest_field] = _sha256_file(output_dir / filename)
    _write_json(summary_path, summary)


def _tool_context(tmp_path: Path) -> ToolExecutionContext:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    recorder = RunRecorder("stage16g2c-tool-result-test", run_dir, task_id="task")
    adapter = LocalWorkspaceAdapter(run_id="stage16g2c-tool-result-test", run_dir=run_dir)
    return ToolExecutionContext(
        run_id="stage16g2c-tool-result-test",
        task_id="task",
        workspace_facade=adapter,
        run_workspace=RunWorkspace(
            run_id="stage16g2c-tool-result-test",
            workspace_path=workspace.as_posix(),
            artifact_dir=(run_dir / "artifacts").as_posix(),
            dependency_state=DependencyState(),
        ),
        artifact_writer=recorder,
        permission_context=PermissionContext(mode="auto"),
        verifier_feedback_facade=None,  # type: ignore[arg-type]
        resolved_verifier_plan=None,  # type: ignore[arg-type]
    )


def test_stage16g2c_writer_outputs_public_safe_evidence_and_inspector(tmp_path: Path) -> None:
    digests = write_stage16g2c_reports(tmp_path)

    for filename in [
        "stage16g2c_run_episode_projection_probe_report.json",
        "stage16g2c_projection_linkage_report.json",
        "stage16g2c_path_leak_scan_report.json",
        "stage16g2c_acceptance_summary.json",
    ]:
        assert filename in digests
        assert (tmp_path / filename).exists()

    inspection = json.loads(
        inspect_stage16g2c_projection_linkage(
            tmp_path / "stage16g2c_acceptance_summary.json",
            assert_complete=True,
        )
    )
    assert inspection["status"] == "passed"
    assert inspection["derived_checks"]["projection_complete"] is True
    assert inspection["derived_checks"]["tool_observation_mask_zero_passed"] is True
    assert inspection["derived_checks"]["non_verl_route_policy_loss_blocked"] is True

    probe = json.loads((tmp_path / "stage16g2c_run_episode_projection_probe_report.json").read_text())
    assert probe["tool_names_observed"] == ["apply_patch", "write_file"]
    assert set(probe["operation_kinds_observed"]) == {
        "delete_file",
        "mkdir",
        "move_file",
        "replace_text",
        "write_file",
    }
    assert probe["final_patch_changed_file_facts"]["renamed_count"] >= 1


def test_stage16g2c_file_mutation_tool_result_is_gateway_model_visible_safe(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_write",
            tool_name="write_file",
            arguments={"path": "helper.py", "content": "def x():\n    return 1\n", "mode": "create"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    payload = result.model_dump(mode="json")
    visible_message = {"role": "tool", **payload}
    validate_no_forbidden_model_visible_content([visible_message], field_name="messages")
    serialized = json.dumps(visible_message, ensure_ascii=False, sort_keys=True)
    assert "audit_ref" not in serialized
    assert "audit_artifact" in serialized


def test_stage16g2c_inspector_rejects_projection_semantic_tamper_even_if_digest_updated(
    tmp_path: Path,
) -> None:
    write_stage16g2c_reports(tmp_path)
    probe_path = tmp_path / "stage16g2c_run_episode_projection_probe_report.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    probe["projection_created_from_run_episode"] = False
    _write_json(probe_path, probe)
    _refresh_summary_digest(
        tmp_path,
        "stage16g2c_run_episode_projection_probe_report.json",
        "run_episode_projection_probe_report_sha256",
    )

    with pytest.raises(RepoHarnessError) as exc_info:
        inspect_stage16g2c_projection_linkage(
            tmp_path / "stage16g2c_acceptance_summary.json",
            assert_complete=True,
        )

    assert "projection_created_from_run_episode_not_true" in str(exc_info.value)


def test_stage16g2c_inspector_rescans_public_evidence(tmp_path: Path) -> None:
    write_stage16g2c_reports(tmp_path)
    summary_path = tmp_path / "stage16g2c_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["debug_path"] = "/Users/roger/secret"
    _write_json(summary_path, summary)

    with pytest.raises(RepoHarnessError) as exc_info:
        inspect_stage16g2c_projection_linkage(summary_path, assert_complete=True)

    assert "stage16g2c_path_leak_scan_report_stale_or_mismatched" in str(exc_info.value)


def test_stage16g2c_inspector_rejects_projection_forbidden_public_markers(
    tmp_path: Path,
) -> None:
    write_stage16g2c_reports(tmp_path)
    probe_path = tmp_path / "stage16g2c_run_episode_projection_probe_report.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    probe["debug_marker"] = "gold_patch hidden_test_patch FAIL_TO_PASS /workspace/testbed"
    _write_json(probe_path, probe)
    _refresh_summary_digest(
        tmp_path,
        "stage16g2c_run_episode_projection_probe_report.json",
        "run_episode_projection_probe_report_sha256",
    )

    with pytest.raises(RepoHarnessError) as exc_info:
        inspect_stage16g2c_projection_linkage(
            tmp_path / "stage16g2c_acceptance_summary.json",
            assert_complete=True,
        )

    assert "stage16g2c_path_leak_scan_report_stale_or_mismatched" in str(exc_info.value)


def test_stage16g2c_inspector_rejects_unexpected_probe_and_linkage_fields(
    tmp_path: Path,
) -> None:
    write_stage16g2c_reports(tmp_path)
    linkage_path = tmp_path / "stage16g2c_projection_linkage_report.json"
    linkage = json.loads(linkage_path.read_text(encoding="utf-8"))
    linkage["debug_extra"] = "safe-extra-field"
    _write_json(linkage_path, linkage)
    _refresh_summary_digest(
        tmp_path,
        "stage16g2c_projection_linkage_report.json",
        "projection_linkage_report_sha256",
    )
    path_scan = scan_stage16g2c_public_files(tmp_path)
    _write_json(tmp_path / "stage16g2c_path_leak_scan_report.json", path_scan)
    _refresh_summary_digest(
        tmp_path,
        "stage16g2c_path_leak_scan_report.json",
        "path_leak_scan_report_sha256",
    )

    with pytest.raises(RepoHarnessError) as exc_info:
        inspect_stage16g2c_projection_linkage(
            tmp_path / "stage16g2c_acceptance_summary.json",
            assert_complete=True,
        )

    assert "stage16g2c_linkage_unexpected_field:debug_extra" in str(exc_info.value)


def test_stage16g2c_inspector_rejects_unexpected_patch_entry_fields(
    tmp_path: Path,
) -> None:
    write_stage16g2c_reports(tmp_path)
    probe_path = tmp_path / "stage16g2c_run_episode_projection_probe_report.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    probe["final_patch_changed_file_facts"]["entries"][0]["debug_extra"] = "safe-extra-field"
    _write_json(probe_path, probe)
    _refresh_summary_digest(
        tmp_path,
        "stage16g2c_run_episode_projection_probe_report.json",
        "run_episode_projection_probe_report_sha256",
    )
    path_scan = scan_stage16g2c_public_files(tmp_path)
    _write_json(tmp_path / "stage16g2c_path_leak_scan_report.json", path_scan)
    _refresh_summary_digest(
        tmp_path,
        "stage16g2c_path_leak_scan_report.json",
        "path_leak_scan_report_sha256",
    )

    with pytest.raises(RepoHarnessError) as exc_info:
        inspect_stage16g2c_projection_linkage(
            tmp_path / "stage16g2c_acceptance_summary.json",
            assert_complete=True,
        )

    assert "stage16g2c_patch_entry_unexpected_field:0:debug_extra" in str(exc_info.value)
