import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V5_TASK_INVENTORY_REPORT_VERSION,
    V5_TASK_SET_MANIFEST_VERSION,
    V5_TASK_VISIBILITY_SCAN_REPORT_VERSION,
)
from repo_harness.v5_evidence import V5_FORBIDDEN_ADAPTER_VISIBLE_MARKERS, inspect_v5_task_set, inspect_v5_task_visibility
from repo_harness.v5_task_set import build_task_set_manifest


def test_v5_task_set_builder_imports_initial_10_without_claiming_full_inventory(tmp_path: Path) -> None:
    inputs = _write_stage2a_inputs(tmp_path)

    manifest_path = build_task_set_manifest(output_dir=tmp_path / "out", **inputs)

    manifest = _read_json(manifest_path)
    inventory = _read_json(tmp_path / "out/v5_task_inventory_report.json")
    visibility = _read_json(tmp_path / "out/v5_task_visibility_scan_report.json")

    assert manifest["schema_version"] == V5_TASK_SET_MANIFEST_VERSION
    assert manifest["task_set_stage"] == "stage2a_initial_10"
    assert manifest["accepted_auditable_task_count"] == 10
    assert manifest["pr_issue_task_count"] == 6
    assert manifest["swebench_like_anchor_count"] == 4
    assert manifest["strict_inventory_gate"] == "blocked_pending_stage2b"
    assert manifest["claims_full_inventory_gate"] is False
    assert inventory["schema_version"] == V5_TASK_INVENTORY_REPORT_VERSION
    assert inventory["supplemental_required"] is True
    assert visibility["schema_version"] == V5_TASK_VISIBILITY_SCAN_REPORT_VERSION
    assert visibility["model_visible_leak_count"] == 0

    task_set_result = inspect_v5_task_set(manifest_path, assert_complete=True)
    visibility_result = inspect_v5_task_visibility(tmp_path / "out/v5_task_visibility_scan_report.json", assert_clean=True)
    assert "Inspect V5 task set: complete" in task_set_result
    assert "Inspect V5 task visibility: complete" in visibility_result


def test_v5_task_set_cli_builds_and_inspects_stage2a_outputs(tmp_path: Path) -> None:
    inputs = _write_stage2a_inputs(tmp_path)
    output_dir = tmp_path / "out"

    assert main(
        [
            "build-v5-task-set",
            "--preflight-input-binding",
            str(inputs["preflight_input_binding"]),
            "--adapter-visible-task-draft",
            str(inputs["adapter_visible_task_draft"]),
            "--evaluator-only-evidence-manifest",
            str(inputs["evaluator_only_evidence_manifest"]),
            "--run-matrix-preflight-manifest",
            str(inputs["run_matrix_preflight_manifest"]),
            "--task-selection-preflight-report",
            str(inputs["task_selection_preflight_report"]),
            "--visibility-scan-report",
            str(inputs["visibility_scan_report"]),
            "--flaky-probe-report",
            str(inputs["flaky_probe_report"]),
            "--source-materialization-report",
            str(inputs["source_materialization_reports"][0]),
            "--output-dir",
            str(output_dir),
        ]
    ) == 0
    assert main(["inspect-v5-task-set", str(output_dir / "v5_task_set_manifest.json"), "--assert-complete"]) == 0
    assert main(["inspect-v5-task-visibility", str(output_dir / "v5_task_visibility_scan_report.json"), "--assert-clean"]) == 0


def test_v5_task_set_rejects_initial_10_claiming_full_inventory(tmp_path: Path) -> None:
    inputs = _write_stage2a_inputs(tmp_path)
    manifest_path = build_task_set_manifest(output_dir=tmp_path / "out", **inputs)
    manifest = _read_json(manifest_path)
    manifest["accepted_auditable_task_count"] = 12
    manifest["pr_issue_task_count"] = 8
    manifest["strict_inventory_gate"] = "passed"
    manifest["claims_full_inventory_gate"] = True
    _write_json(manifest_path, manifest)

    with pytest.raises(ConfigError, match="Stage 2A|accepted_auditable_task_count"):
        inspect_v5_task_set(manifest_path, assert_complete=True)


def test_v5_task_set_builder_rejects_adapter_visible_forbidden_marker(tmp_path: Path) -> None:
    inputs = _write_stage2a_inputs(tmp_path)
    adapter_path = Path(inputs["adapter_visible_task_draft"])
    rows = [json.loads(line) for line in adapter_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["task_statement"] += " raw_pr_diff provider_raw_content hidden_selector reward_scalar"
    adapter_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")

    manifest_path = build_task_set_manifest(output_dir=tmp_path / "out", **inputs)

    with pytest.raises(ConfigError, match="model_visible_leak_count|task visibility"):
        inspect_v5_task_visibility(tmp_path / "out/v5_task_visibility_scan_report.json", assert_clean=True)
    with pytest.raises(ConfigError, match="visibility_scan_ref|model_visible"):
        inspect_v5_task_set(manifest_path, assert_complete=True)


@pytest.mark.parametrize(
    "marker",
    [
        "raw pr diff",
        "raw_pr_diff",
        "raw pr body",
        "raw_pr_body",
        "hidden selector",
        "hidden_selector",
        "gold patch",
        "gold_patch",
        "raw test patch",
        "raw_test_patch",
        "provider raw content",
        "provider_raw_content",
        "reward scalar",
        "reward_scalar",
        "reward label",
        "reward_label",
    ],
)
def test_v5_task_set_forbidden_marker_contract_contains_reviewed_variants(marker: str) -> None:
    assert marker in V5_FORBIDDEN_ADAPTER_VISIBLE_MARKERS


def test_v5_task_visibility_inspect_rescans_adapter_visible_refs(tmp_path: Path) -> None:
    inputs = _write_stage2a_inputs(tmp_path)
    build_task_set_manifest(output_dir=tmp_path / "out", **inputs)
    adapter_input = tmp_path / "out/adapter_visible_task_inputs/v5_task_001.json"
    payload = _read_json(adapter_input)
    payload["task_statement"] += " hidden_selector"
    _write_json(adapter_input, payload)

    with pytest.raises(ConfigError, match="hidden_selector"):
        inspect_v5_task_visibility(tmp_path / "out/v5_task_visibility_scan_report.json", assert_clean=True)


def test_v5_task_set_builder_refuses_existing_outputs(tmp_path: Path) -> None:
    inputs = _write_stage2a_inputs(tmp_path)
    output_dir = tmp_path / "out"
    build_task_set_manifest(output_dir=output_dir, **inputs)

    with pytest.raises(ConfigError, match="已存在"):
        build_task_set_manifest(output_dir=output_dir, **inputs)


def _write_stage2a_inputs(tmp_path: Path) -> dict:
    candidate_ids = [
        "owner1/repo1#101",
        "owner2/repo2#102",
        "owner3/repo3#103",
        "owner4/repo4#104",
        "owner5/repo5#105",
        "owner6/repo6#106",
        "swe__anchor-001",
        "swe__anchor-002",
        "swe__anchor-003",
        "swe__anchor-004",
    ]
    task_ids = [f"v5_task_{index:03d}" for index in range(1, 11)]
    preflight_binding = {
        "initial_candidate_count": 10,
        "accepted_counting_allowed": False,
        "stage0_policy": {
            "preflight_artifacts_do_not_count_as_final_v5_accepted_tasks": True,
        },
    }
    preflight_path = tmp_path / "v5_preflight_input_binding.json"
    _write_json(preflight_path, preflight_binding)

    adapter_rows = []
    for index, (task_id, candidate_id) in enumerate(zip(task_ids, candidate_ids, strict=True), start=1):
        ecosystem = "python" if index > 6 else "go"
        adapter_rows.append(
            {
                "schema_version": "repo_harness_v5_adapter_visible_task_draft_v0",
                "task_id": task_id,
                "task_family": f"family_{index}",
                "ecosystem": ecosystem,
                "repository": candidate_id.split("#")[0].replace("__", "/").replace("-", "/"),
                "task_statement": f"Fix behavior for task {index} using only the provided repository workspace.",
                "visible_constraints": ["do not use network access during verifier execution"],
                "visibility": "adapter_visible_model_input",
                "share_safe": True,
            }
        )
    adapter_path = tmp_path / "adapter_visible.jsonl"
    adapter_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in adapter_rows) + "\n", encoding="utf-8")

    evaluator_path = tmp_path / "evaluator_only.json"
    _write_json(
        evaluator_path,
        {
            "schema_version": "repo_harness_v5_evaluator_only_preflight_manifest_v0",
            "candidate_count": 10,
            "visibility": "evaluator_only_internal_audit",
            "share_safe": False,
            "policy": "never_adapter_visible",
        },
    )

    verifier_report = tmp_path / "verifier_report.json"
    _write_json(verifier_report, {"status": "passed"})
    visibility_path = tmp_path / "visibility_report.json"
    _write_json(
        visibility_path,
        {
            "status": "passed",
            "model_visible_leak_count": 0,
            "share_safe_violation_count": 0,
            "raw_provider_content_leak_count": 0,
            "credential_marker_leak_count": 0,
            "trainable_payload_leak_count": 0,
            "evaluator_only_raw_content_copied_count": 0,
        },
    )
    flaky_path = tmp_path / "flaky_report.json"
    _write_json(
        flaky_path,
        {
            "stable_count": 10,
            "flaky_suspected_count": 0,
            "attempt_count_per_side": 3,
            "entries": [{"candidate_id": candidate_id, "status": "stable"} for candidate_id in candidate_ids],
        },
    )
    selection_path = tmp_path / "task_selection.json"
    _write_json(
        selection_path,
        {
            "status": "initial_batch_freeze_ready_full_threshold_partial",
            "candidate_count": 10,
            "freeze_ready_tasks": task_ids,
        },
    )

    run_matrix_entries = []
    source_entries = []
    for index, (task_id, candidate_id) in enumerate(zip(task_ids, candidate_ids, strict=True), start=1):
        archive = tmp_path / f"archive_{index}.tar"
        archive.write_text(f"archive {index}\n", encoding="utf-8")
        dependency_dir = tmp_path / f"dependency_{index}"
        dependency_dir.mkdir()
        (dependency_dir / "dependency.txt").write_text("ok\n", encoding="utf-8")
        track = "pr_issue" if index <= 6 else "swebench_like"
        run_matrix_entries.append(
            {
                "task_id": task_id,
                "candidate_id": candidate_id,
                "track": track,
                "repository": f"repo/{index}",
                "ecosystem": "python" if index > 6 else "go",
                "freeze_ready": True,
                "agent_run_ready": True,
                "comparison_ready": index <= 9,
                "demo_ready": index in {1, 3},
                "source_tree_hash": {"sha256": f"{index:064x}", "file_count": 10 + index},
                "dependency_snapshot_ref": dependency_dir.as_posix(),
                "final_verifier_plan_ref": verifier_report.as_posix(),
                "recommended_v5_role": "test",
                "environment_id": "docker_test",
                "tool_policy_id": "tool_policy",
                "context_policy_id": "context_policy",
                "budget_policy_id": "budget",
                "scaffold_id": "simple_react",
            }
        )
        source_entries.append(
            {
                "candidate_id": candidate_id,
                "repository_url": f"https://github.com/repo/{index}",
                "base_commit": f"{index:040x}",
                "resolved_commit": f"{index:040x}",
                "archive_sha256": sha256_file(archive),
                "source_archive_ref": {"path": archive.as_posix()},
                "source_tree_hash": f"{index:064x}",
            }
        )
    run_matrix_path = tmp_path / "run_matrix.json"
    _write_json(
        run_matrix_path,
        {
            "candidate_count": 10,
            "entries": run_matrix_entries,
        },
    )
    source_report_path = tmp_path / "source_materialization.json"
    _write_json(source_report_path, {"entries": source_entries})

    return {
        "preflight_input_binding": preflight_path,
        "adapter_visible_task_draft": adapter_path,
        "evaluator_only_evidence_manifest": evaluator_path,
        "run_matrix_preflight_manifest": run_matrix_path,
        "task_selection_preflight_report": selection_path,
        "visibility_scan_report": visibility_path,
        "flaky_probe_report": flaky_path,
        "source_materialization_reports": [source_report_path],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
