from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.errors import RepoHarnessError
from repo_harness.evaluation.stage16d_healthcheck import (
    build_stage16d_healthcheck_artifacts,
    inspect_stage16d_healthcheck,
    inspect_stage16d_healthcheck_report,
)


def test_stage16d_builder_writes_contract_evidence_with_structured_not_run_records(tmp_path: Path) -> None:
    seed_manifest = _write_seed_manifest(tmp_path)
    evidence = tmp_path / "evidence"

    result = build_stage16d_healthcheck_artifacts(seed_manifest_path=seed_manifest, output_dir=evidence)

    assert result.record_count == 2
    assert result.trainable_candidate_count == 0
    summary = _read_json(evidence / "stage16d_acceptance_summary.json")
    assert summary["local_contract_ready"] is True
    assert summary["official_healthcheck_complete"] is False
    assert summary["official_harness_execution_status"] == "not_run_in_local_schema_phase"
    assert summary["training_eligible_after_healthcheck_count"] == 0
    assert summary["runtime_private_evidence_present"] is True
    evidence_map = _read_json(evidence / "stage16d_canonical_evidence_map.json")
    assert "runtime_private" not in json.dumps(evidence_map, ensure_ascii=False)
    assert "runtime-private:" in json.dumps(evidence_map, ensure_ascii=False)

    report = inspect_stage16d_healthcheck_report(evidence, assert_contract_complete=True)
    assert report.passed is True
    assert report.failures == []
    with pytest.raises(RepoHarnessError, match="official_healthcheck_complete"):
        inspect_stage16d_healthcheck(evidence, assert_official_healthcheck_complete=True)


def test_stage16d_builder_accepts_complete_official_healthcheck_evidence(tmp_path: Path) -> None:
    seed_manifest = _write_seed_manifest(tmp_path)
    gold_results = tmp_path / "gold.jsonl"
    noop_results = tmp_path / "noop.jsonl"
    _write_jsonl(gold_results, [_official_result("task-1", "gold_patch", True)])
    _write_jsonl(noop_results, [_official_result("task-1", "noop_patch", False)])
    evidence = tmp_path / "evidence"

    build_stage16d_healthcheck_artifacts(
        seed_manifest_path=seed_manifest,
        output_dir=evidence,
        gold_results_path=gold_results,
        noop_results_path=noop_results,
    )

    summary = _read_json(evidence / "stage16d_acceptance_summary.json")
    assert summary["official_healthcheck_complete"] is True
    assert summary["official_harness_execution_status"] == "executed"
    assert summary["training_eligible_after_healthcheck_count"] == 1
    payload = json.loads(
        inspect_stage16d_healthcheck(
            evidence,
            assert_contract_complete=True,
            assert_official_healthcheck_complete=True,
        )
    )
    assert payload["passed"] is True


def test_stage16d_builder_keeps_unlocked_official_image_out_of_training(tmp_path: Path) -> None:
    seed_manifest = _write_seed_manifest(tmp_path)
    gold_results = tmp_path / "gold.jsonl"
    noop_results = tmp_path / "noop.jsonl"
    _write_jsonl(gold_results, [_official_result("task-1", "gold_patch", True, digest_locked=False)])
    _write_jsonl(noop_results, [_official_result("task-1", "noop_patch", False, digest_locked=False)])
    evidence = tmp_path / "evidence"

    build_stage16d_healthcheck_artifacts(
        seed_manifest_path=seed_manifest,
        output_dir=evidence,
        gold_results_path=gold_results,
        noop_results_path=noop_results,
    )

    summary = _read_json(evidence / "stage16d_acceptance_summary.json")
    assert summary["official_healthcheck_complete"] is False
    assert summary["training_eligible_after_healthcheck_count"] == 0
    with pytest.raises(RepoHarnessError, match="image_digest_lock"):
        inspect_stage16d_healthcheck(evidence, assert_official_healthcheck_complete=True)


def test_stage16d_builder_rejects_gold_noop_image_digest_mismatch(tmp_path: Path) -> None:
    seed_manifest = _write_seed_manifest(tmp_path)
    gold_results = tmp_path / "gold.jsonl"
    noop_results = tmp_path / "noop.jsonl"
    gold = _official_result("task-1", "gold_patch", True)
    noop = _official_result("task-1", "noop_patch", False)
    noop["official_image_digest"] = "sha256:" + "9" * 64
    _write_jsonl(gold_results, [gold])
    _write_jsonl(noop_results, [noop])
    evidence = tmp_path / "evidence"

    build_stage16d_healthcheck_artifacts(
        seed_manifest_path=seed_manifest,
        output_dir=evidence,
        gold_results_path=gold_results,
        noop_results_path=noop_results,
    )

    summary = _read_json(evidence / "stage16d_acceptance_summary.json")
    assert summary["official_healthcheck_complete"] is False
    assert summary["training_eligible_after_healthcheck_count"] == 0
    manifest = _read_json(evidence / "stage16d_healthcheck_manifest.json")
    concrete = next(record for record in manifest["records"] if record["instance_id"] == "task-1")
    assert concrete["official_image_digest_locked"] is False
    assert concrete["overall_healthcheck_status"] == "official_image_digest_mismatch"


def test_stage16d_builder_public_leak_scan_rejects_public_artifact_leak(tmp_path: Path) -> None:
    seed_manifest = _write_seed_manifest(tmp_path)
    evidence = tmp_path / "evidence"
    build_stage16d_healthcheck_artifacts(seed_manifest_path=seed_manifest, output_dir=evidence)
    (evidence / "stage16d_command_log.sanitized.jsonl").write_text(
        '{"command": "cat /Users/example/secret"}\n',
        encoding="utf-8",
    )

    report = inspect_stage16d_healthcheck_report(evidence, assert_contract_complete=True)

    assert any(failure.startswith("public_evidence_leak:local_absolute_path") for failure in report.failures)


def test_stage16d_builder_rejects_missing_official_result_artifact_for_official_complete(tmp_path: Path) -> None:
    seed_manifest = _write_seed_manifest(tmp_path)
    gold_results = tmp_path / "gold.jsonl"
    noop_results = tmp_path / "noop.jsonl"
    gold = _official_result("task-1", "gold_patch", True)
    noop = _official_result("task-1", "noop_patch", False)
    gold.pop("official_result_ref")
    gold.pop("official_result_sha256")
    _write_jsonl(gold_results, [gold])
    _write_jsonl(noop_results, [noop])

    try:
        build_stage16d_healthcheck_artifacts(
            seed_manifest_path=seed_manifest,
            output_dir=tmp_path / "evidence",
            gold_results_path=gold_results,
            noop_results_path=noop_results,
        )
    except ValueError as exc:
        assert "official_result_ref" in str(exc)
    else:
        raise AssertionError("missing official result artifact should be rejected")


def test_stage16d_builder_rejects_invalid_official_image_digest_format(tmp_path: Path) -> None:
    seed_manifest = _write_seed_manifest(tmp_path)
    gold_results = tmp_path / "gold.jsonl"
    noop_results = tmp_path / "noop.jsonl"
    gold = _official_result("task-1", "gold_patch", True)
    noop = _official_result("task-1", "noop_patch", False)
    gold["official_image_digest"] = "not-a-real-digest"
    _write_jsonl(gold_results, [gold])
    _write_jsonl(noop_results, [noop])

    try:
        build_stage16d_healthcheck_artifacts(
            seed_manifest_path=seed_manifest,
            output_dir=tmp_path / "evidence",
            gold_results_path=gold_results,
            noop_results_path=noop_results,
        )
    except ValueError as exc:
        assert "official_image_digest" in str(exc)
    else:
        raise AssertionError("invalid official image digest should be rejected")


def test_stage16d_inspector_rejects_manifest_image_digest_tamper(tmp_path: Path) -> None:
    evidence = _write_complete_evidence(tmp_path)
    manifest = _read_json(evidence / "stage16d_healthcheck_manifest.json")
    concrete = next(record for record in manifest["records"] if record["instance_id"] == "task-1")
    concrete["official_image_digest"] = "not-a-real-digest"
    _write_json(evidence / "stage16d_healthcheck_manifest.json", manifest)

    report = inspect_stage16d_healthcheck_report(evidence, assert_official_healthcheck_complete=True)

    assert any("requires sha256 official image digest" in failure for failure in report.failures)


def test_stage16d_inspector_rejects_not_run_status_in_official_complete(tmp_path: Path) -> None:
    evidence = _write_complete_evidence(tmp_path)
    manifest = _read_json(evidence / "stage16d_healthcheck_manifest.json")
    concrete = next(record for record in manifest["records"] if record["instance_id"] == "task-1")
    concrete["official_harness_execution_status"] = "not_run_in_local_schema_phase"
    _write_json(evidence / "stage16d_healthcheck_manifest.json", manifest)
    summary = _read_json(evidence / "stage16d_acceptance_summary.json")
    summary["official_harness_execution_status"] = "not_run_in_local_schema_phase"
    summary["official_healthcheck_complete"] = False
    summary["stage16d_complete"] = False
    summary["official_healthcheck_assert_complete_passed"] = False
    summary["remote_healthcheck_required"] = True
    _write_json(evidence / "stage16d_acceptance_summary.json", summary)

    report = inspect_stage16d_healthcheck_report(evidence, assert_official_healthcheck_complete=True)

    assert any("requires executed official harness status" in failure for failure in report.failures)


def test_stage16d_builder_rejects_result_ref_digest_mismatch(tmp_path: Path) -> None:
    seed_manifest = _write_seed_manifest(tmp_path)
    gold_results = tmp_path / "gold.jsonl"
    noop_results = tmp_path / "noop.jsonl"
    gold = _official_result("task-1", "gold_patch", True)
    noop = _official_result("task-1", "noop_patch", False)
    gold["official_result_sha256"] = "9" * 64
    _write_jsonl(gold_results, [gold])
    _write_jsonl(noop_results, [noop])

    try:
        build_stage16d_healthcheck_artifacts(
            seed_manifest_path=seed_manifest,
            output_dir=tmp_path / "evidence",
            gold_results_path=gold_results,
            noop_results_path=noop_results,
        )
    except ValueError as exc:
        assert "official_result_ref digest" in str(exc)
    else:
        raise AssertionError("official result ref digest mismatch should be rejected")


def test_stage16d_inspector_rejects_tampered_summary_derived_fields(tmp_path: Path) -> None:
    seed_manifest = _write_seed_manifest(tmp_path)
    evidence = tmp_path / "evidence"
    build_stage16d_healthcheck_artifacts(seed_manifest_path=seed_manifest, output_dir=evidence)
    summary = _read_json(evidence / "stage16d_acceptance_summary.json")
    summary["stage16d_complete"] = True
    summary["official_healthcheck_complete"] = True
    summary["training_eligible_after_healthcheck_count"] = 999
    _write_json(evidence / "stage16d_acceptance_summary.json", summary)

    report = inspect_stage16d_healthcheck_report(evidence, assert_contract_complete=True)

    assert "stage16d_summary_derived_field_mismatch:stage16d_complete" in report.failures
    assert "stage16d_summary_derived_field_mismatch:official_healthcheck_complete" in report.failures
    assert "stage16d_summary_derived_field_mismatch:training_eligible_after_healthcheck_count" in report.failures


def _write_seed_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "seeds.json"
    payload = {
        "schema_version": "repo_harness_stage16d_seed_manifest_v0",
        "seeds": [
            {
                "instance_id": "repr20-gold-smoke-aggregate",
                "seed_role": "gold_patch_smoke_pass_candidate",
                "source_dataset": "swebench_verified",
                "candidate_instance_status": "aggregate_not_directly_runnable",
                "official_validation_backend": "swebench_official_harness",
            },
            {
                "instance_id": "task-1",
                "seed_role": "positive_path_official_resolved",
                "source_dataset": "swebench_verified",
                "candidate_instance_status": "concrete_not_healthchecked_in_stage16d_0",
                "gold_patch_source": "dataset_gold_patch_or_not_available",
                "noop_patch_source": "not_available",
                "official_validation_backend": "swebench_official_harness",
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_complete_evidence(tmp_path: Path) -> Path:
    seed_manifest = _write_seed_manifest(tmp_path)
    gold_results = tmp_path / "gold.jsonl"
    noop_results = tmp_path / "noop.jsonl"
    _write_jsonl(gold_results, [_official_result("task-1", "gold_patch", True)])
    _write_jsonl(noop_results, [_official_result("task-1", "noop_patch", False)])
    evidence = tmp_path / "complete-evidence"
    build_stage16d_healthcheck_artifacts(
        seed_manifest_path=seed_manifest,
        output_dir=evidence,
        gold_results_path=gold_results,
        noop_results_path=noop_results,
    )
    return evidence


def _official_result(
    instance_id: str,
    check_kind: str,
    resolved: bool,
    *,
    digest_locked: bool = True,
) -> dict[str, object]:
    return {
        "instance_id": instance_id,
        "check_kind": check_kind,
        "official_resolved": resolved,
        "official_harness_execution_status": "executed",
        "official_image_source": "swebench:latest",
        "official_image_digest": "sha256:" + "1" * 64,
        "official_image_digest_locked": digest_locked,
        "official_result_ref": "runtime-private:official-result:" + "2" * 64,
        "official_result_sha256": "2" * 64,
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
