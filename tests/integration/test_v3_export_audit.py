from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.evaluation.runner import run_task
from repo_harness.export.audit import audit_export_records
from repo_harness.export.exporter import export_sft_jsonl
from repo_harness.export.schemas import STRICT_COMPARE_FIELDS, CompareScope, ExportPolicy, ExportRecord
from repo_harness.v3_export_audit import (
    V3_COMPARE_SCOPE_FIELDS,
    build_v3_export_audit,
    inspect_v3_export_audit,
)


ROOT = Path(__file__).resolve().parents[2]


def test_v3_export_audit_builds_and_inspects(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    success = _run_replay(
        runs_dir,
        run_id="v3_export_success",
        replay="tests/fixtures/replays/task_001_success.yaml",
    )
    failure = _run_replay(
        runs_dir,
        run_id="v3_export_failure",
        replay="tests/fixtures/replays/task_001_failure.yaml",
    )
    output_dir = tmp_path / "v3_export_audit"

    result_dir = build_v3_export_audit(
        run_dirs=[success],
        output_dir=output_dir,
        preference_runs_dir=runs_dir,
    )
    output = inspect_v3_export_audit(
        result_dir,
        manifest=result_dir / "export_manifest.json",
        audit_report=result_dir / "audit_report.json",
        assert_clean=True,
    )

    manifest = _read_json(result_dir / "export_manifest.json")
    report = _read_json(result_dir / "audit_report.json")
    preference = _read_json(result_dir / "preference_pair_baseline_report.json")

    assert "Inspect V3 export audit: passed" in output
    assert {entry["format"] for entry in manifest["format_exports"]} == {
        "sft_jsonl",
        "rl_jsonl",
        "preference_jsonl",
    }
    assert report["status"] == "passed"
    assert report["format_export_summary"]["included_count"] >= 3
    assert preference["eligible_pair_count"] == 1
    assert preference["compare_scope_contains_v2_fields"] is True
    assert preference["compare_scope_contains_v3_fields"] is True
    assert set(V3_COMPARE_SCOPE_FIELDS).issubset(
        set(preference["compare_scope"]["canonical_key_fields"])
    )
    assert (result_dir / "command_log.jsonl").exists()

    _ = failure


def test_v3_export_audit_cli(tmp_path: Path, capsys):
    runs_dir = tmp_path / "runs_cli"
    success = _run_replay(
        runs_dir,
        run_id="v3_export_cli_success",
        replay="tests/fixtures/replays/task_001_success.yaml",
    )
    _run_replay(
        runs_dir,
        run_id="v3_export_cli_failure",
        replay="tests/fixtures/replays/task_001_failure.yaml",
    )
    output_dir = tmp_path / "v3_export_audit_cli"

    assert main(
        [
            "build-v3-export-audit",
            "--run-dir",
            str(success),
            "--output-dir",
            str(output_dir),
            "--preference-runs-dir",
            str(runs_dir),
        ]
    ) == 0
    assert "V3 export audit 产物目录" in capsys.readouterr().out
    assert main(
        [
            "inspect-v3-export-audit",
            str(output_dir),
            "--manifest",
            str(output_dir / "export_manifest.json"),
            "--audit-report",
            str(output_dir / "audit_report.json"),
            "--assert-clean",
        ]
    ) == 0
    assert "Inspect V3 export audit: passed" in capsys.readouterr().out


def test_inspect_v3_export_audit_rejects_data_sha_drift(tmp_path: Path):
    runs_dir = tmp_path / "runs_bad_sha"
    success = _run_replay(
        runs_dir,
        run_id="v3_export_bad_sha_success",
        replay="tests/fixtures/replays/task_001_success.yaml",
    )
    _run_replay(
        runs_dir,
        run_id="v3_export_bad_sha_failure",
        replay="tests/fixtures/replays/task_001_failure.yaml",
    )
    output_dir = build_v3_export_audit(
        run_dirs=[success],
        output_dir=tmp_path / "v3_export_bad_sha",
        preference_runs_dir=runs_dir,
    )
    manifest_path = output_dir / "export_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["format_exports"][0]["data_file_refs"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="sha256"):
        inspect_v3_export_audit(
            output_dir,
            manifest=manifest_path,
            audit_report=output_dir / "audit_report.json",
            assert_clean=True,
        )


def test_v3_compare_scope_does_not_mutate_v2_strict_fields():
    assert "docker_backend" not in STRICT_COMPARE_FIELDS
    assert "verifier_plan_ref" not in STRICT_COMPARE_FIELDS
    scope = CompareScope(canonical_key_fields=list(STRICT_COMPARE_FIELDS))
    assert scope.canonical_key_fields == list(STRICT_COMPARE_FIELDS)


def test_inspect_v3_export_audit_rejects_unbound_audit_report(tmp_path: Path):
    runs_dir = tmp_path / "runs_unbound_report"
    success = _run_replay(
        runs_dir,
        run_id="v3_export_unbound_success",
        replay="tests/fixtures/replays/task_001_success.yaml",
    )
    _run_replay(
        runs_dir,
        run_id="v3_export_unbound_failure",
        replay="tests/fixtures/replays/task_001_failure.yaml",
    )
    output_dir = build_v3_export_audit(
        run_dirs=[success],
        output_dir=tmp_path / "v3_export_unbound_report",
        preference_runs_dir=runs_dir,
    )
    alternate_report = output_dir / "alternate_audit_report.json"
    alternate_report.write_text((output_dir / "audit_report.json").read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(ConfigError, match="audit_report_ref"):
        inspect_v3_export_audit(
            output_dir,
            manifest=output_dir / "export_manifest.json",
            audit_report=alternate_report,
            assert_clean=True,
        )


def test_v3_export_audit_rejects_metadata_contamination(tmp_path: Path):
    runs_dir = tmp_path / "runs_metadata_contamination"
    success = _run_replay(
        runs_dir,
        run_id="v3_export_metadata_success",
        replay="tests/fixtures/replays/task_001_success.yaml",
    )
    failure = _run_replay(
        runs_dir,
        run_id="v3_export_metadata_failure",
        replay="tests/fixtures/replays/task_001_failure.yaml",
    )
    for run_dir in (success, failure):
        facts_path = run_dir / "run_config_facts.json"
        facts = _read_json(facts_path)
        facts["model_id"] = "provider_raw_response"
        facts_path.write_text(
            json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    output_dir = build_v3_export_audit(
        run_dirs=[success],
        output_dir=tmp_path / "v3_export_metadata_contamination",
        preference_runs_dir=runs_dir,
    )

    with pytest.raises(ConfigError, match="provider raw"):
        inspect_v3_export_audit(
            output_dir,
            manifest=output_dir / "export_manifest.json",
            audit_report=output_dir / "audit_report.json",
            assert_clean=True,
        )


def test_v3_observation_binding_rechecks_prepared_messages_sha(tmp_path: Path):
    runs_dir = tmp_path / "runs_binding"
    success = _run_replay(
        runs_dir,
        run_id="v3_export_binding_success",
        replay="tests/fixtures/replays/task_001_success.yaml",
    )
    output = export_sft_jsonl(success)
    record = _read_jsonl(output)[0]
    record["payload"]["v3_observation_bindings"][0]["prepared_messages_sha256"] = "0" * 64

    audited = audit_export_records(
        [ExportRecord.model_validate(record)],
        run_paths={success.name: success},
        export_format="sft_jsonl",
        policy=ExportPolicy(),
    )

    assert audited[0].record.quality.training_eligibility == "invalid"
    assert "prepared_messages_sha256" in str(audited[0].record.invalid_reason)


def _run_replay(runs_dir: Path, *, run_id: str, replay: str) -> Path:
    config_path = runs_dir / f"{run_id}.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        f"""
run_id_prefix: v3_export
tasks:
  - tests/fixtures/tasks/task_001.yaml
model:
  provider: replay
  model_id: replay-script-v0
  replay_script_path: {replay}
runtime:
  scaffold_id: simple_react
  execution_mode: local_process
  permission_mode: auto
  test_feedback_policy: structured_public_feedback
  feedback_tests_passed_policy: require_model_final
  max_turns: 8
  max_tool_calls: 20
  max_test_runs: 4
workspace:
  output_dir: {runs_dir.as_posix()}
  keep_workspace: true
  default_command_timeout_sec: 60
evaluation:
  final_verifier_mode: strict_patch_replay
""".lstrip(),
        encoding="utf-8",
    )
    return run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=runs_dir,
        run_id=run_id,
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
