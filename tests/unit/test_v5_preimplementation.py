import json
from pathlib import Path

import pytest

from repo_harness.errors import ConfigError
from repo_harness.schema_versions import (
    V5_BASELINE_CHECK_REPORT_VERSION,
    V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V5_DOCUMENTATION_SYNC_REPORT_VERSION,
    V5_PREFLIGHT_INPUT_BINDING_VERSION,
    V5_V4_CLOSURE_REPORT_VERSION,
)
from repo_harness.v5_evidence import (
    V4_DOC_SYNC_BUNDLE_NAME,
    V4_DOC_SYNC_COMMAND_LOG_NAME,
    V4_LATEST_DIR,
    V5_DOCUMENTATION_SYNC_REQUIRED_PATHS,
    V5_PARTIAL_THRESHOLD_STATUS,
    V5_PREFLIGHT_ARTIFACT_FIELDS,
    _evidence_ref,
    inspect_v5_preimplementation,
)


def test_v5_preimplementation_valid_binding_passes(tmp_path: Path) -> None:
    binding = _write_valid_binding(tmp_path)

    result = inspect_v5_preimplementation(binding, assert_complete=True)

    assert "Inspect V5 preimplementation: complete" in result


def test_v5_preimplementation_rejects_threshold_overclaim(tmp_path: Path) -> None:
    binding = _write_valid_binding(tmp_path)
    payload = _read_json(binding)
    payload["full_v5_threshold_status"] = "passed"
    binding.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ConfigError, match="12 total / 8 PR-issue"):
        inspect_v5_preimplementation(binding, assert_complete=True)


def test_v5_preimplementation_rejects_original_v4_bundle(tmp_path: Path) -> None:
    binding = _write_valid_binding(tmp_path)
    original_bundle = tmp_path / "acceptance_bundle_manifest.json"
    original_bundle.write_text("{}", encoding="utf-8")
    payload = _read_json(binding)
    payload["v4_latest_refs"]["v4_doc_sync_acceptance_bundle"] = _ref(
        original_bundle,
        kind="v4_acceptance_bundle",
    )
    binding.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ConfigError, match="doc-sync acceptance bundle"):
        inspect_v5_preimplementation(binding, assert_complete=True)


def test_v5_preimplementation_rejects_sha256_drift(tmp_path: Path) -> None:
    binding = _write_valid_binding(tmp_path)
    payload = _read_json(binding)
    payload["preflight_input_refs"]["flaky_probe_report"]["sha256"] = "0" * 64
    binding.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ConfigError, match="sha256"):
        inspect_v5_preimplementation(binding, assert_complete=True)


def test_v5_preimplementation_rejects_preflight_training_sample_overclaim(tmp_path: Path) -> None:
    binding = _write_valid_binding(tmp_path)
    payload = _read_json(binding)
    payload["stage0_policy"]["preflight_artifacts_do_not_count_as_training_samples"] = False
    binding.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ConfigError, match="preflight_artifacts_do_not_count_as_training_samples"):
        inspect_v5_preimplementation(binding, assert_complete=True)


def _write_valid_binding(tmp_path: Path) -> Path:
    baseline_report = tmp_path / "v5_baseline_check_report.json"
    v4_closure_report = tmp_path / "v4_review_findings_closure_report.json"
    doc_sync_report = tmp_path / "v5_documentation_sync_report.json"
    command_log = tmp_path / "v5_preimplementation_command_log.jsonl"
    preflight_root = tmp_path / "runs" / "v5-preflight"
    preflight_root.mkdir(parents=True)

    preflight_refs = {}
    for field in V5_PREFLIGHT_ARTIFACT_FIELDS:
        path = preflight_root / f"{field}.json"
        path.write_text(json.dumps({"schema_version": field}, sort_keys=True), encoding="utf-8")
        preflight_refs[field] = _ref(path, kind=field)

    v2 = _write_json_file(tmp_path / "v2_acceptance_report.json", {"status": "passed"})
    v3 = _write_json_file(tmp_path / "v3_acceptance_report.json", {"status": "passed"})
    v3_bundle = _write_json_file(tmp_path / "v3_acceptance_bundle.json", {"status": "passed"})
    v4_inputs = _write_json_file(tmp_path / "v4_acceptance_inputs.json", {"status": "passed"})
    v4_report = _write_json_file(tmp_path / "v4_acceptance_report.json", {"status": "passed"})
    v4_bundle = _write_json_file(tmp_path / V4_DOC_SYNC_BUNDLE_NAME, {"status": "passed"})
    v4_log = _write_json_file(tmp_path / V4_DOC_SYNC_COMMAND_LOG_NAME, {"status": "passed"})

    _write_command_log(command_log, tmp_path)
    _write_json_file(baseline_report, _baseline_payload(command_log))
    _write_json_file(v4_closure_report, _v4_closure_payload(v4_inputs, v4_report, v4_bundle, v4_log))
    _write_json_file(doc_sync_report, _doc_sync_payload())

    binding_payload = {
        "schema_version": V5_PREFLIGHT_INPUT_BINDING_VERSION,
        "baseline_commit": "9fd7007",
        "v4_closure_commit": "e0da89c",
        "preflight_root": preflight_root.as_posix(),
        "preflight_root_ref": _ref(preflight_root, kind="preflight_root"),
        "baseline_check_report_ref": _ref(baseline_report, kind="v5_baseline_check_report"),
        "v4_review_findings_closure_report_ref": _ref(v4_closure_report, kind="v4_review_findings_closure_report"),
        "documentation_sync_report_ref": _ref(doc_sync_report, kind="v5_documentation_sync_report"),
        "preimplementation_command_log_ref": _ref(command_log, kind="v5_preimplementation_command_log"),
        "v2_v3_v4_regression_refs": {
            "v2_acceptance_report": _ref(v2, kind="v2_acceptance_report"),
            "v3_acceptance_report": _ref(v3, kind="v3_acceptance_report"),
            "v3_acceptance_bundle": _ref(v3_bundle, kind="v3_acceptance_bundle"),
        },
        "v4_latest_refs": {
            "v4_acceptance_inputs": _ref(v4_inputs, kind="v4_acceptance_inputs"),
            "v4_acceptance_report": _ref(v4_report, kind="v4_acceptance_report"),
            "v4_doc_sync_acceptance_bundle": _ref(v4_bundle, kind="v4_doc_sync_acceptance_bundle"),
            "v4_doc_sync_final_command_log": _ref(v4_log, kind="v4_doc_sync_final_command_log"),
        },
        "preflight_input_refs": preflight_refs,
        "initial_candidate_count": 10,
        "pr_issue_candidate_count": 6,
        "swebench_like_anchor_count": 4,
        "agent_run_ready_count": 10,
        "comparison_ready_count": 9,
        "planned_matrix_cells": 24,
        "real_agent_run_executed": False,
        "provider_api_called": False,
        "accepted_counting_allowed": False,
        "full_v5_threshold_status": V5_PARTIAL_THRESHOLD_STATUS,
        "stage0_policy": {
            "preflight_artifacts_do_not_count_as_final_v5_accepted_tasks": True,
            "preflight_artifacts_do_not_count_as_real_provider_runs": True,
            "preflight_artifacts_do_not_count_as_training_samples": True,
        },
    }
    return _write_json_file(tmp_path / "v5_preflight_input_binding.json", binding_payload)


def _baseline_payload(command_log: Path) -> dict:
    passed = {
        "v5_baseline_commit_is_ancestor": "passed",
        "v4_closure_commit_is_ancestor": "passed",
        "docs_v5_clean": "passed",
        "compileall_src": "passed",
        "pytest": "passed",
        "v2_acceptance": "passed",
        "v3_acceptance": "passed",
        "v3_acceptance_bundle": "passed",
        "v4_inputs": "passed",
        "v4_acceptance": "passed",
        "v4_doc_sync_acceptance_bundle": "passed",
        "docker_hello_world": "passed",
        "docker_arm64_probe": "passed",
        "docker_amd64_probe": "passed",
    }
    return {
        "schema_version": V5_BASELINE_CHECK_REPORT_VERSION,
        "baseline_commit": "9fd7007",
        "v4_closure_commit": "e0da89c",
        "live_checks_run": True,
        "command_log_ref": _ref(command_log, kind="command_log"),
        "baseline_status": passed,
    }


def _v4_closure_payload(v4_inputs: Path, v4_report: Path, v4_bundle: Path, v4_log: Path) -> dict:
    return {
        "schema_version": V5_V4_CLOSURE_REPORT_VERSION,
        "v4_closure_commit": "e0da89c",
        "latest_v4_evidence_root": V4_LATEST_DIR,
        "latest_v4_acceptance_inputs_ref": _ref(v4_inputs, kind="v4_acceptance_inputs"),
        "latest_v4_acceptance_report_ref": _ref(v4_report, kind="v4_acceptance_report"),
        "latest_v4_doc_sync_acceptance_bundle_ref": _ref(v4_bundle, kind="v4_doc_sync_acceptance_bundle"),
        "latest_v4_doc_sync_final_command_log_ref": _ref(v4_log, kind="v4_doc_sync_final_command_log"),
        "closed_findings": [
            {"finding_id": f"finding_{index}", "status": "closed", "closure_commit": "e0da89c"}
            for index in range(8)
        ],
        "status": "passed",
    }


def _doc_sync_payload() -> dict:
    return {
        "schema_version": V5_DOCUMENTATION_SYNC_REPORT_VERSION,
        "checked_paths": [
            {
                "path": path,
                "exists": True,
                "mentions_latest_v4_root": True,
                "mentions_v5_docs": True,
                "old_v4_path_mentions": 0,
                "old_v4_path_marked_historical": True,
            }
            for path in V5_DOCUMENTATION_SYNC_REQUIRED_PATHS
        ],
        "status": "passed",
    }


def _write_command_log(path: Path, tmp_path: Path) -> None:
    records = []
    for command_name in (
        "git_merge_base_v5_baseline_head",
        "git_merge_base_v4_closure_head",
        "inspect_v4_doc_sync_acceptance_bundle",
        "pytest_q",
        "docker_run_alpine_amd64_uname_m",
    ):
        stdout = tmp_path / f"{command_name}.stdout.txt"
        stderr = tmp_path / f"{command_name}.stderr.txt"
        stdout.write_text("ok\n", encoding="utf-8")
        stderr.write_text("\n", encoding="utf-8")
        records.append(
            {
                "schema_version": V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
                "command_name": command_name,
                "argv": ["repo-harness", command_name],
                "cwd": tmp_path.as_posix(),
                "input_refs": [],
                "output_refs": [_ref(stdout, kind="stdout"), _ref(stderr, kind="stderr")],
                "started_at": "2026-05-05T00:00:00Z",
                "finished_at": "2026-05-05T00:00:01Z",
                "exit_code": 0,
                "stdout_sha256": _ref(stdout, kind="stdout")["sha256"],
                "stderr_sha256": _ref(stderr, kind="stderr")["sha256"],
            }
        )
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records) + "\n", encoding="utf-8")


def _write_json_file(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _ref(path: Path, *, kind: str) -> dict:
    return _evidence_ref(
        path,
        kind=kind,
        purpose=f"test {kind}",
        visibility="audit_only",
        producer_command="test",
        producer_stage="test",
        inspect_command="inspect-v5-preimplementation",
    )
