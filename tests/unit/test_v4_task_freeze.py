import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.v4_task_freeze import (
    build_v4_task_freeze,
    inspect_v4_task_freeze,
    inspect_v4_task_validity,
)


IMPLEMENTATION_INPUTS = Path("docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json")


def test_v4_task_freeze_build_and_inspect_pass(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )

    assert "complete" in inspect_v4_task_freeze(manifest, assert_complete=True)
    assert "complete" in inspect_v4_task_validity(manifest.parent / "task_validity_report.json", assert_complete=True)
    assert main(["inspect-v4-task-freeze", str(manifest), "--assert-complete"]) == 0
    assert main(["inspect-v4-task-validity", str(manifest.parent / "task_validity_report.json"), "--assert-complete"]) == 0


def test_v4_task_freeze_rejects_adapter_visible_contamination(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )
    bad_task = tmp_path / "bad_adapter_visible.json"
    bad_task.write_text(
        json.dumps(
            {
                "schema_version": "v4.adapter_visible_task.0",
                "adapter_visible_task_id": "bad",
                "model_visibility": "adapter_visible",
                "problem_statement": "Do not include gold_patch or pull request #123 in task input.",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    adapter_manifest = manifest.parent / "adapter_visible_task_input_manifest.json"
    payload = _read_json(adapter_manifest)
    payload["records"][0]["path"] = bad_task.as_posix()
    payload["records"][0]["sha256"] = sha256_file(bad_task)
    payload["records"][0]["size_bytes"] = bad_task.stat().st_size
    _write_json(adapter_manifest, payload)
    _refresh_manifest_artifact_ref(manifest, "adapter_visible_task_input_manifest.json", adapter_manifest)

    with pytest.raises(ConfigError, match="污染扫描失败"):
        inspect_v4_task_freeze(manifest, assert_complete=True)


def test_v4_task_validity_rejects_source_materialization_mismatch(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )
    report = manifest.parent / "source_materialization_report.json"
    payload = _read_json(report)
    payload["records"][0]["second_source_tree_hash"] = "different"
    _write_json(report, payload)
    validity = manifest.parent / "task_validity_report.json"
    _refresh_manifest_artifact_ref(validity, "source_materialization_report.json", report)

    with pytest.raises(ConfigError, match="source_tree_hash 不一致"):
        inspect_v4_task_validity(validity, assert_complete=True)


def test_v4_task_validity_rejects_unstable_flaky_probe_marked_accepted(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )
    validity = manifest.parent / "task_validity_report.json"
    payload = _read_json(validity)
    payload["accepted_task_definitions"][0]["flaky_probe_status"] = "flaky_probe_unstable"
    _write_json(validity, payload)

    with pytest.raises(ConfigError, match="flaky probe 未通过"):
        inspect_v4_task_validity(validity, assert_complete=True)


def test_v4_task_validity_rejects_post_patch_failure_in_bound_report(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )
    report = manifest.parent / "post_patch_verifier_report.json"
    payload = _read_json(report)
    payload["records"][0]["post_patch_status"] = "failed"
    _write_json(report, payload)
    validity = manifest.parent / "task_validity_report.json"
    _refresh_manifest_artifact_ref(validity, "post_patch_verifier_report.json", report)

    with pytest.raises(ConfigError, match="post_patch_status 必须为 passed"):
        inspect_v4_task_validity(validity, assert_complete=True)


def test_v4_task_validity_rejects_baseline_failure_and_raw_output_in_bound_report(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )
    report = manifest.parent / "baseline_verifier_report.json"
    payload = _read_json(report)
    payload["records"][0]["baseline_health_status"] = "failed"
    payload["records"][0]["raw_output_copied"] = True
    _write_json(report, payload)
    validity = manifest.parent / "task_validity_report.json"
    _refresh_manifest_artifact_ref(validity, "baseline_verifier_report.json", report)

    with pytest.raises(ConfigError, match="baseline_health_status 必须为 passed|raw output"):
        inspect_v4_task_validity(validity, assert_complete=True)


def test_v4_task_validity_rejects_evaluator_only_provider_and_patch_leakage(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )
    evaluator = manifest.parent / "evaluator_only_evidence_manifest.json"
    payload = _read_json(evaluator)
    payload["provider_raw_response_copied"] = True
    payload["raw_patch_copied"] = True
    payload["raw_test_patch_copied"] = True
    payload["raw_verifier_output_copied"] = True
    _write_json(evaluator, payload)
    _refresh_manifest_artifact_ref(manifest, "evaluator_only_evidence_manifest.json", evaluator)

    with pytest.raises(ConfigError, match="provider raw response|raw patch|raw test patch|verifier raw output"):
        inspect_v4_task_freeze(manifest, assert_complete=True)


def test_v4_task_freeze_recursively_rejects_invalid_task_validity(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )
    validity = manifest.parent / "task_validity_report.json"
    payload = _read_json(validity)
    payload["accepted_auditable_task_definition_count"] = 999
    _write_json(validity, payload)
    _refresh_manifest_artifact_ref(manifest, "task_validity_report.json", validity)

    with pytest.raises(ConfigError, match="递归复核 task_validity_report 失败|accepted_auditable_task_definition_count"):
        inspect_v4_task_freeze(manifest, assert_complete=True)


def test_v4_task_validity_rejects_accepted_count_inflation(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )
    validity = manifest.parent / "task_validity_report.json"
    payload = _read_json(validity)
    payload["accepted_auditable_task_definition_count"] = 99
    payload["pr_issue_accepted_auditable_task_definition_count"] = 99
    _write_json(validity, payload)

    with pytest.raises(ConfigError, match="实际行数|PR / issue accepted 行数"):
        inspect_v4_task_validity(validity, assert_complete=True)


def test_v4_task_validity_rejects_evidence_ref_mismatch_with_bound_report(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )
    validity = manifest.parent / "task_validity_report.json"
    payload = _read_json(validity)
    payload["accepted_task_definitions"][0]["baseline_verifier_evidence_ref"] = "evidence:wrong"
    _write_json(validity, payload)

    with pytest.raises(ConfigError, match="baseline_verifier_evidence_ref 不一致"):
        inspect_v4_task_validity(validity, assert_complete=True)


def test_v4_task_validity_rejects_bound_report_missing_accepted_task_identity(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )
    report = manifest.parent / "post_patch_verifier_report.json"
    payload = _read_json(report)
    payload["records"][0]["task_id"] = "different_task"
    _write_json(report, payload)
    validity = manifest.parent / "task_validity_report.json"
    _refresh_manifest_artifact_ref(validity, "post_patch_verifier_report.json", report)

    with pytest.raises(ConfigError, match="缺少同 task_id/candidate_id|通过记录数量"):
        inspect_v4_task_validity(validity, assert_complete=True)


def test_v4_task_validity_rejects_environment_and_dependency_report_gaps(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )
    env_report = manifest.parent / "environment_stability_report.json"
    env_payload = _read_json(env_report)
    env_payload["records"][0]["environment_stability_score"] = 0
    _write_json(env_report, env_payload)
    dep_report = manifest.parent / "dependency_cache_report.json"
    dep_payload = _read_json(dep_report)
    dep_payload["records"][0].pop("cache_artifact_hash")
    _write_json(dep_report, dep_payload)
    validity = manifest.parent / "task_validity_report.json"
    _refresh_manifest_artifact_ref(validity, "environment_stability_report.json", env_report)
    _refresh_manifest_artifact_ref(validity, "dependency_cache_report.json", dep_report)

    with pytest.raises(ConfigError, match="environment_stability_score|cache_artifact_hash"):
        inspect_v4_task_validity(validity, assert_complete=True)


def test_v4_task_validity_rejects_missing_reviews_and_adapter_boundary_violation(tmp_path: Path) -> None:
    manifest = build_v4_task_freeze(
        implementation_inputs=IMPLEMENTATION_INPUTS,
        output_dir=tmp_path / "task-freeze",
    )
    validity = manifest.parent / "task_validity_report.json"
    payload = _read_json(validity)
    payload["accepted_task_definitions"][0]["license_provenance_review_status"] = "missing"
    payload["accepted_task_definitions"][1]["manual_review_note"] = ""
    payload["task_adapter_boundary"]["task_adapter_performed_dependency_setup"] = True
    payload["task_adapter_boundary"]["forbidden_operations_executed"] = ["dependency_setup"]
    _write_json(validity, payload)

    with pytest.raises(ConfigError, match="license / provenance|人工 review note|Task Adapter"):
        inspect_v4_task_validity(validity, assert_complete=True)


def _refresh_manifest_artifact_ref(manifest: Path, name: str, target: Path) -> None:
    payload = _read_json(manifest)
    payload["artifact_refs_by_name"][name] = {
        "path": target.as_posix(),
        "kind": target.suffix.lstrip("."),
        "category": name.removesuffix(".json").removesuffix(".jsonl"),
        "model_visible": False,
        "sha256": sha256_file(target),
        "size_bytes": target.stat().st_size,
    }
    _write_json(manifest, payload)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
