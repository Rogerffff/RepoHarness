from __future__ import annotations

import json
from pathlib import Path

from repo_harness.evaluation.stage16d_healthcheck import (
    build_stage16d_healthcheck_artifacts,
    inspect_stage16d_healthcheck_report,
)


def test_stage16d_acceptance_rejects_missing_healthcheck_manifest(tmp_path: Path) -> None:
    evidence = _write_contract_evidence(tmp_path)
    (evidence / "stage16d_healthcheck_manifest.json").unlink()

    report = inspect_stage16d_healthcheck_report(evidence, assert_contract_complete=True)

    assert "missing_stage16d_public_artifact:stage16d_healthcheck_manifest.json" in report.failures
    assert "missing_stage16d_artifact:stage16d_healthcheck_manifest.json" in report.failures


def test_stage16d_acceptance_rejects_missing_record_for_seed_contract(tmp_path: Path) -> None:
    evidence = _write_contract_evidence(tmp_path)
    manifest = _read_json(evidence / "stage16d_healthcheck_manifest.json")
    manifest["records"] = []
    _write_json(evidence / "stage16d_healthcheck_manifest.json", manifest)

    report = inspect_stage16d_healthcheck_report(evidence, assert_contract_complete=True)

    assert "stage16d_summary_seed_count_mismatch" in report.failures
    assert "stage16d_healthcheck_manifest_has_no_records" in report.failures


def test_stage16d_acceptance_rejects_trainable_not_run_record(tmp_path: Path) -> None:
    evidence = _write_contract_evidence(tmp_path)
    manifest = _read_json(evidence / "stage16d_healthcheck_manifest.json")
    concrete = next(record for record in manifest["records"] if record["instance_id"] == "task-1")
    concrete["healthcheck_training_disposition"] = "trainable_candidate"
    concrete["invalid_for_training"] = False
    concrete["invalid_for_online_rl"] = False
    concrete["gold_healthcheck_status"] = "passed"
    concrete["noop_healthcheck_status"] = "expected_unresolved"
    concrete["official_image_digest_locked"] = True
    _write_json(evidence / "stage16d_healthcheck_manifest.json", manifest)

    report = inspect_stage16d_healthcheck_report(evidence, assert_contract_complete=True)

    assert any(
        failure.startswith("invalid_stage16d_healthcheck_record:1:")
        and "requires executed official harness status" in failure
        for failure in report.failures
    )


def test_stage16d_acceptance_rejects_public_diff_content(tmp_path: Path) -> None:
    evidence = _write_contract_evidence(tmp_path)
    (evidence / "stage16d_command_log.sanitized.jsonl").write_text(
        '{"patch": "diff --git a/pkg.py b/pkg.py"}\n',
        encoding="utf-8",
    )

    report = inspect_stage16d_healthcheck_report(evidence, assert_contract_complete=True)

    assert any(failure.startswith("public_evidence_leak:diff_header") for failure in report.failures)


def test_stage16d_acceptance_contract_mode_accepts_not_run_but_official_mode_rejects(tmp_path: Path) -> None:
    evidence = _write_contract_evidence(tmp_path)

    contract = inspect_stage16d_healthcheck_report(evidence, assert_contract_complete=True)
    official = inspect_stage16d_healthcheck_report(evidence, assert_official_healthcheck_complete=True)

    assert contract.passed is True
    assert official.passed is False
    assert "stage16d_official_healthcheck_complete_not_true" in official.failures


def test_stage16d_acceptance_rejects_silently_deleted_seed_records(tmp_path: Path) -> None:
    evidence = _write_contract_evidence(tmp_path)
    deleted_instance = "task-1"
    report_files = [
        "stage16d_healthcheck_manifest.json",
        "stage16d_seed_resolution_report.json",
        "stage16d_gold_healthcheck_report.json",
        "stage16d_noop_healthcheck_report.json",
        "stage16d_proxy_official_disagreement_report.json",
        "stage16d_training_disposition_report.json",
    ]
    for name in report_files:
        payload = _read_json(evidence / name)
        payload["records"] = [row for row in payload["records"] if row["instance_id"] != deleted_instance]
        _write_json(evidence / name, payload)
    summary = _read_json(evidence / "stage16d_acceptance_summary.json")
    summary["seed_count"] = 1
    summary["concrete_seed_count"] = 0
    _write_json(evidence / "stage16d_acceptance_summary.json", summary)

    report = inspect_stage16d_healthcheck_report(evidence, assert_contract_complete=True)

    assert f"stage16d_healthcheck_missing_seed_record:{deleted_instance}" in report.failures
    assert any(
        failure.startswith("stage16d_report_missing_seed_records:stage16d_seed_resolution_report.json")
        for failure in report.failures
    )
    assert "stage16d_summary_input_seed_field_mismatch:seed_count" in report.failures


def _write_contract_evidence(tmp_path: Path) -> Path:
    seed_manifest = tmp_path / "seeds.json"
    seed_manifest.write_text(
        json.dumps(
            {
                "schema_version": "repo_harness_stage16d_seed_manifest_v0",
                "seeds": [
                    {
                        "instance_id": "repr20-gold-smoke-aggregate",
                        "seed_role": "gold_patch_smoke_pass_candidate",
                        "source_dataset": "swebench_verified",
                        "candidate_instance_status": "aggregate_not_directly_runnable",
                    },
                    {
                        "instance_id": "task-1",
                        "seed_role": "positive_path_official_resolved",
                        "source_dataset": "swebench_verified",
                        "candidate_instance_status": "concrete_not_healthchecked_in_stage16d_0",
                        "gold_patch_source": "dataset_gold_patch_or_not_available",
                        "noop_patch_source": "not_available",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence"
    build_stage16d_healthcheck_artifacts(seed_manifest_path=seed_manifest, output_dir=evidence)
    return evidence


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
