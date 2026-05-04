import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.v4_agent_run import build_v4_agent_run_integration
from repo_harness.v4_cards import _build_scan_report, build_v4_cards, inspect_v4_cards
from repo_harness.v4_export_quality import build_v4_export_quality
from repo_harness.v4_task_freeze import build_v4_task_freeze
from tests.unit.test_v4_agent_run import _external_inputs


def test_v4_cards_build_and_inspect_pass(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)

    assert "complete" in inspect_v4_cards(cards_dir, assert_complete=True)
    assert main(["inspect-v4-cards", str(cards_dir), "--assert-complete"]) == 0
    assert main(["inspect-v4-contamination-scan", str(cards_dir / "contamination_scan_report.json"), "--assert-clean"]) == 0
    dataset = _read_json(cards_dir / "dataset_card.json")
    assert dataset["task_sources"]["v4_pr_issue_constructed"] == 8
    assert dataset["distribution"]["diagnostic_only"] == 5
    run_card = _read_json(cards_dir / "run_card.json")
    assert run_card["run_status_counts"]["completed"] == 1
    export_card = _read_json(cards_dir / "export_card.json")
    assert export_card["trainable_diagnostic_split"]["trainable"] == 1
    assert export_card["blocked_sources"] == ["preference_pair_baseline_blocked"]
    provenance = _read_json(cards_dir / "provenance_summary.json")
    assert set(provenance["export_quality_refs"]) == {
        "trajectory_quality_manifest.json",
        "sample_tier_manifest.json",
        "preference_pair_trainability_report.json",
        "blocked_pair_report.json",
    }
    scan_report = _read_json(cards_dir / "contamination_scan_report.json")
    assert scan_report["card_claim_denylist_sha256"]


def test_v4_cards_reject_dataset_claiming_direct_training_without_review(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    dataset = cards_dir / "dataset_card.json"
    payload = _read_json(dataset)
    payload["direct_training_without_review_allowed"] = True
    _write_json(dataset, payload)

    with pytest.raises(ConfigError, match="人工审查"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_public_leaderboard_claim(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    dataset = cards_dir / "dataset_card.json"
    payload = _read_json(dataset)
    payload["public_leaderboard_comparable"] = True
    _write_json(dataset, payload)

    with pytest.raises(ConfigError, match="leaderboard"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_production_sandbox_claim(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    run_card = cards_dir / "run_card.json"
    payload = _read_json(run_card)
    payload["docker_facts"]["production_security_sandbox"] = True
    _write_json(run_card, payload)

    with pytest.raises(ConfigError, match="生产级安全沙箱"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_missing_contamination_summary(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    (cards_dir / "contamination_scan_summary.json").unlink()

    with pytest.raises(ConfigError, match="contamination_scan_summary"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_raw_pr_body_or_hidden_selector(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    provenance = cards_dir / "provenance_summary.json"
    payload = _read_json(provenance)
    payload["note"] = "pull_request_body and hidden selector must not appear"
    _write_json(provenance, payload)

    with pytest.raises(ConfigError, match="contamination"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_provider_raw_response_or_verifier_output(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    export_card = cards_dir / "export_card.json"
    payload = _read_json(export_card)
    payload["note"] = "provider_raw_response and verifier_raw_output"
    _write_json(export_card, payload)

    with pytest.raises(ConfigError, match="contamination"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_ai_session_url(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    dataset_md = cards_dir / "dataset_card.md"
    dataset_md.write_text(dataset_md.read_text(encoding="utf-8") + "\nhttps://chatgpt.com/share/example\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="contamination"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_raw_commit_message(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    provenance = cards_dir / "provenance_summary.json"
    payload = _read_json(provenance)
    payload["note"] = "raw commit message must not appear"
    _write_json(provenance, payload)

    with pytest.raises(ConfigError, match="contamination"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_missing_repro_command(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    repro = cards_dir / "repro_command_index.json"
    payload = _read_json(repro)
    payload["commands"] = payload["commands"][:3]
    _write_json(repro, payload)

    with pytest.raises(ConfigError, match="inspect-v4-task-freeze"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_latest_run_repro_command(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    repro = cards_dir / "repro_command_index.json"
    payload = _read_json(repro)
    payload["commands"][0]["command"] += " --latest"
    _write_json(repro, payload)

    with pytest.raises(ConfigError, match="latest"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_missing_implementation_log_file(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    log_index = cards_dir / "implementation_log_index.json"
    payload = _read_json(log_index)
    payload["stage_logs"] = ["docs/v4/implementation-log/does-not-exist.md"]
    _write_json(log_index, payload)

    with pytest.raises(ConfigError, match="路径不存在"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_polluted_implementation_log_file(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    polluted = tmp_path / "polluted-log.md"
    polluted.write_text("raw commit message must fail\n", encoding="utf-8")
    log_index = cards_dir / "implementation_log_index.json"
    payload = _read_json(log_index)
    payload["stage_logs"] = [polluted.as_posix()]
    _write_json(log_index, payload)

    with pytest.raises(ConfigError, match="implementation_log"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_manifest_ref_sha_mismatch(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    manifest = cards_dir / "cards_manifest.json"
    payload = _read_json(manifest)
    payload["contamination_scan_report_ref"]["sha256"] = "0" * 64
    payload["implementation_log_index_ref"]["sha256"] = "1" * 64
    _write_json(manifest, payload)

    with pytest.raises(ConfigError, match="sha256"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_export_card_stage6_mismatch(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    export_card = cards_dir / "export_card.json"
    payload = _read_json(export_card)
    payload["blocked_sources"] = ["stale-hardcoded-source"]
    _write_json(export_card, payload)

    with pytest.raises(ConfigError, match="blocked_sources"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_reject_export_quality_ref_sha_mismatch(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    provenance = cards_dir / "provenance_summary.json"
    payload = _read_json(provenance)
    payload["export_quality_refs"]["sample_tier_manifest.json"]["sha256"] = "0" * 64
    _write_json(provenance, payload)

    with pytest.raises(ConfigError, match="sha256"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_scan_report_reflects_forbidden_card_claims(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    dataset_md = cards_dir / "dataset_card.md"
    dataset_md.write_text(dataset_md.read_text(encoding="utf-8") + "\npublic leaderboard comparable\n", encoding="utf-8")
    task_visibility_ref = _read_json(cards_dir / "contamination_scan_report.json")["artifact_refs_by_name"]["task_visibility_scan_report.json"]
    scan_report = _build_scan_report(cards_dir, task_visibility_ref=task_visibility_ref)

    assert scan_report["clean"] is False
    assert any(finding.get("category") == "forbidden_card_claim" for finding in scan_report["findings"])


def test_v4_cards_reject_scan_report_without_bound_artifacts(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)
    scan_report = cards_dir / "contamination_scan_report.json"
    payload = _read_json(scan_report)
    payload.pop("artifact_refs_by_name")
    _write_json(scan_report, payload)

    with pytest.raises(ConfigError, match="artifact_refs_by_name"):
        inspect_v4_cards(cards_dir, assert_complete=True)


def test_v4_cards_build_respects_fail_if_output_exists(tmp_path: Path) -> None:
    cards_dir = _build(tmp_path)

    with pytest.raises(ConfigError, match="输出已存在"):
        build_v4_cards(
            output_dir=cards_dir,
            task_freeze=tmp_path / "task-freeze" / "task_freeze_manifest.json",
            agent_run_integration=tmp_path / "agent",
            export_quality=tmp_path / "export",
            fail_if_output_exists=True,
        )


def _build(tmp_path: Path) -> Path:
    task_freeze = build_v4_task_freeze(
        implementation_inputs=Path("docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json"),
        output_dir=tmp_path / "task-freeze",
    )
    agent_dir = tmp_path / "agent"
    build_v4_agent_run_integration(output_dir=agent_dir, **_external_inputs(tmp_path))
    export_dir = tmp_path / "export"
    build_v4_export_quality(output_dir=export_dir, agent_run_integration=agent_dir)
    cards_dir = tmp_path / "cards"
    build_v4_cards(
        output_dir=cards_dir,
        task_freeze=task_freeze,
        agent_run_integration=agent_dir,
        export_quality=export_dir,
    )
    return cards_dir


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
