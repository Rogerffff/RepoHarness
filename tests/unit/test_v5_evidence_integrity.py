import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.schema_versions import (
    V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V5_CRITICAL_EVIDENCE_MANIFEST_VERSION,
    V5_SCHEMA_TRACKING_TABLE_VERSION,
)
from repo_harness.v5_evidence import (
    V5_REQUIRED_INSPECT_COMMANDS,
    V5_SCHEMA_SPECS,
    _evidence_ref,
    build_pre_acceptance_integrity_report,
    build_schema_fixtures,
    inspect_v5_evidence_integrity,
)


def test_v5_schema_fixtures_cover_required_schema_contracts(tmp_path: Path) -> None:
    tracking_path = build_schema_fixtures(output_dir=tmp_path)

    payload = _read_json(tracking_path)

    assert payload["schema_version"] == V5_SCHEMA_TRACKING_TABLE_VERSION
    assert {row["schema_name"] for row in payload["schemas"]} == {
        spec["schema_name"] for spec in V5_SCHEMA_SPECS
    }
    for row in payload["schemas"]:
        assert row["required_fields"]
        assert Path(row["valid_fixture_ref"]["path"]).exists()
        assert Path(row["negative_fixture_ref"]["path"]).exists()
    assert (tmp_path / "v5_artifact_inspect_tracking_table.json").exists()
    assert (tmp_path / "v5_acceptance_lineage_schema_report.json").exists()


def test_v5_schema_tracking_records_nested_fields_and_one_of_constraints(tmp_path: Path) -> None:
    tracking_path = build_schema_fixtures(output_dir=tmp_path)
    payload = _read_json(tracking_path)
    by_name = {row["schema_name"]: row for row in payload["schemas"]}

    acceptance_report_fields = set(by_name["V5AcceptanceReport"]["required_fields"])
    assert "core_acceptance.status" in acceptance_report_fields
    assert "core_acceptance.required_checks" in acceptance_report_fields
    assert "resume_ready_acceptance.status" in acceptance_report_fields
    assert "resume_ready_acceptance.required_checks" in acceptance_report_fields
    assert "acceptance_report_reference_integrity.expected_check" in acceptance_report_fields
    assert ["preference_pair_export_ref", "preference_pair_blocked_report_ref"] in by_name[
        "V5ExportResultPackManifest"
    ]["one_of_required_fields"]


def test_v5_stage1_cli_exposes_schema_integrity_and_inspect_skeletons(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "build-v5-schema-fixtures" in output
    assert "build-v5-evidence-integrity" in output
    for command in V5_REQUIRED_INSPECT_COMMANDS:
        assert command in output


def test_v5_inspect_skeletons_reject_negative_fixtures(tmp_path: Path) -> None:
    build_schema_fixtures(output_dir=tmp_path)

    valid_task_set = tmp_path / "tests/fixtures/v5/task_set_valid.json"
    negative_task_set = tmp_path / "tests/fixtures/v5/task_set_below_inventory_gate.json"
    assert main(["inspect-v5-task-set", str(valid_task_set), "--assert-complete"]) == 0
    with pytest.raises(SystemExit):
        main(["inspect-v5-task-set", str(negative_task_set), "--assert-complete"])

    valid_export_pack = tmp_path / "tests/fixtures/v5/export_pack_valid.json"
    negative_export_pack = tmp_path / "tests/fixtures/v5/export_pack_missing_blocked_partition.json"
    assert main(["inspect-v5-export-pack", str(valid_export_pack), "--assert-clean"]) == 0
    with pytest.raises(SystemExit):
        main(["inspect-v5-export-pack", str(negative_export_pack), "--assert-clean"])

    valid_acceptance = tmp_path / "tests/fixtures/v5/acceptance_report_valid_core.json"
    negative_acceptance = tmp_path / "tests/fixtures/v5/acceptance_report_references_post_report_output.json"
    assert main(["inspect-v5-acceptance", str(valid_acceptance), "--assert-core-complete"]) == 0
    with pytest.raises(SystemExit):
        main(["inspect-v5-acceptance", str(negative_acceptance), "--assert-core-complete"])


def test_v5_pre_acceptance_evidence_integrity_passes(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    command_log = _write_command_log(tmp_path)
    output = tmp_path / "v5_pre_acceptance_evidence_integrity_report.json"

    build_pre_acceptance_integrity_report(
        critical_evidence_manifest=manifest,
        pre_acceptance_command_log=command_log,
        output=output,
    )

    result = inspect_v5_evidence_integrity(output, assert_complete=True)
    assert "Inspect V5 evidence integrity: complete" in result


def test_v5_pre_acceptance_evidence_integrity_rejects_sha256_drift(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    payload = _read_json(manifest)
    payload["critical_evidence"][0]["ref"]["sha256"] = "0" * 64
    _write_json(manifest, payload)
    command_log = _write_command_log(tmp_path)
    output = tmp_path / "v5_pre_acceptance_evidence_integrity_report.json"

    build_pre_acceptance_integrity_report(
        critical_evidence_manifest=manifest,
        pre_acceptance_command_log=command_log,
        output=output,
    )

    with pytest.raises(ConfigError, match="sha256_drift|finding"):
        inspect_v5_evidence_integrity(output, assert_complete=True)


def test_v5_pre_acceptance_evidence_integrity_rejects_post_report_reference(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    payload = _read_json(manifest)
    payload["critical_evidence"][0]["evidence_class"] = "acceptance_report_reference_integrity"
    _write_json(manifest, payload)
    command_log = _write_command_log(tmp_path)
    output = tmp_path / "v5_pre_acceptance_evidence_integrity_report.json"

    build_pre_acceptance_integrity_report(
        critical_evidence_manifest=manifest,
        pre_acceptance_command_log=command_log,
        output=output,
    )

    with pytest.raises(ConfigError, match="post_report_reference|finding"):
        inspect_v5_evidence_integrity(output, assert_complete=True)


def test_v5_evidence_integrity_builder_refuses_overwrite(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path)
    command_log = _write_command_log(tmp_path)
    output = tmp_path / "v5_pre_acceptance_evidence_integrity_report.json"
    output.write_text("{}", encoding="utf-8")

    with pytest.raises(ConfigError, match="已存在"):
        build_pre_acceptance_integrity_report(
            critical_evidence_manifest=manifest,
            pre_acceptance_command_log=command_log,
            output=output,
        )


def _write_manifest(tmp_path: Path) -> Path:
    evidence = tmp_path / "baseline_evidence.json"
    _write_json(evidence, {"status": "passed"})
    manifest = {
        "schema_version": V5_CRITICAL_EVIDENCE_MANIFEST_VERSION,
        "critical_evidence": [
            {
                "evidence_class": "baseline_proof",
                "criticality": "critical",
                "planned_acceptance_inputs_binding": True,
                "ref": _evidence_ref(
                    evidence,
                    kind="baseline_proof",
                    purpose="Stage 0 baseline proof",
                    visibility="audit_only",
                    producer_command="test",
                    producer_stage="test",
                    inspect_command="inspect-v5-evidence-integrity",
                ),
            }
        ],
    }
    path = tmp_path / "v5_critical_evidence_manifest.json"
    _write_json(path, manifest)
    return path


def _write_command_log(tmp_path: Path) -> Path:
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
        stderr.write_text("", encoding="utf-8")
        records.append(
            {
                "schema_version": V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
                "command_name": command_name,
                "argv": ["repo-harness", command_name],
                "cwd": tmp_path.as_posix(),
                "input_refs": [],
                "output_refs": [
                    _evidence_ref(
                        stdout,
                        kind="command_stdout",
                        purpose="stdout",
                        visibility="audit_only",
                        producer_command=command_name,
                        producer_stage="test",
                        inspect_command="inspect-v5-evidence-integrity",
                    ),
                    _evidence_ref(
                        stderr,
                        kind="command_stderr",
                        purpose="stderr",
                        visibility="audit_only",
                        producer_command=command_name,
                        producer_stage="test",
                        inspect_command="inspect-v5-evidence-integrity",
                    ),
                ],
                "started_at": "2026-05-05T00:00:00Z",
                "finished_at": "2026-05-05T00:00:01Z",
                "exit_code": 0,
                "stdout_sha256": _evidence_ref(stdout, kind="stdout", purpose="stdout", visibility="audit_only", producer_command=command_name, producer_stage="test", inspect_command="inspect-v5-evidence-integrity")["sha256"],
                "stderr_sha256": _evidence_ref(stderr, kind="stderr", purpose="stderr", visibility="audit_only", producer_command=command_name, producer_stage="test", inspect_command="inspect-v5-evidence-integrity")["sha256"],
            }
        )
    path = tmp_path / "v5_pre_acceptance_command_log.jsonl"
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records) + "\n", encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
