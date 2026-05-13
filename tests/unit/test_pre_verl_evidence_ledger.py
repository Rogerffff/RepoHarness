from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from repo_harness.errors import ConfigError
from repo_harness.config import load_run_config
from repo_harness.pre_verl_agentloop import validate_pre_verl_run_config_entry
from repo_harness.pre_verl_evidence_ledger import (
    build_pre_verl_evidence_ledger,
    inspect_pre_verl_evidence_ledger,
)
from repo_harness.run_metadata.writer import _context_policy_snapshot
from repo_harness.schema_base import stable_hash


def test_build_ledger_distinguishes_formal_and_discarded_attempts(tmp_path: Path) -> None:
    root = _write_root(tmp_path)
    _write_formal_run(root, "pre_verl_dev_001_demo", result="success", verifier="accepted", trainable=2)
    _write_formal_run(root, "pre_verl_dev_002_demo", result="failed", verifier="rejected", invalid=2)
    _write_formal_run(
        root,
        "pre_verl_dev_003_demo",
        result="inconclusive",
        verifier="not_executed",
        skipped=2,
    )
    _write_discarded_run(root, "pre_verl_dev_002_demo", "host_oom_before_final_verifier")

    ledger_path = build_pre_verl_evidence_ledger(
        root,
        context_inspector=lambda _run_dir: ("passed", None),
    )
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    assert ledger["formal_denominator"] == 3
    assert ledger["formal_result_counts"] == {"success": 1, "failed": 1, "inconclusive": 1}
    assert ledger["discarded_attempt_count"] == 1
    failed_entry = next(item for item in ledger["entries"] if item["task_id"] == "pre_verl_dev_002_demo")
    assert failed_entry["discarded_attempts"][0]["discard_reason"] == "host_oom_before_final_verifier"
    assert "Inspect pre-verl evidence ledger: complete" in inspect_pre_verl_evidence_ledger(
        ledger_path,
        assert_complete=True,
        expected_formal_denominator=3,
        expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
    )


def test_inspect_rejects_missing_discard_reason(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0]["discarded_attempts"] = [
        {
            "run_dir": "discarded_runs/pre_verl_dev_001_demo",
            "discard_reason": None,
            "excluded_from_denominator": True,
        }
    ]
    ledger["discarded_attempt_count"] = 1
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="discard_reason"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_success_without_trainable_export(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0]["export_summary"]["trainable_count"] = 0
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="success run"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_failed_run_with_trainable_sample(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    failed = next(item for item in ledger["entries"] if item["formal_result"] == "failed")
    failed["export_summary"]["trainable_count"] = 1
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="failed run"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_inconclusive_invalid_sample(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    inconclusive = next(item for item in ledger["entries"] if item["formal_result"] == "inconclusive")
    inconclusive["export_summary"]["invalid_count"] = 1
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="inconclusive run"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_count_and_denominator_drift(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["formal_denominator"] = 4
    ledger["formal_result_counts"] = {"success": 2, "failed": 1, "inconclusive": 1}
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="formal_denominator"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_missing_policy_versions(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    del ledger["entries"][0]["timeout_policy_version"]
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="timeout_policy_version"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_context_strategy_hash_drift(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    entry = ledger["entries"][0]
    entry["repository_hints_mode"] = "weak_model_scaffold"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="context_strategy_hash"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_allows_task_specific_repository_hints_hashes(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    for index, entry in enumerate(ledger["entries"], start=1):
        entry["repository_hints_model_visible_hash"] = f"{index}" * 64
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    assert "Inspect pre-verl evidence ledger: complete" in inspect_pre_verl_evidence_ledger(
        ledger_path,
        assert_complete=True,
        expected_formal_denominator=3,
        expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
    )


def test_inspect_rejects_mixed_context_strategy_entries(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    entry = ledger["entries"][1]
    strategy = {
        "initial_context_policy_version": entry["initial_context_policy_version"],
        "repository_hints_mode": "disabled",
        "repository_hints_config": entry["repository_hints_config"],
        "tool_schema_snapshot_hash": entry["tool_schema_snapshot_hash"],
        "context_policy_snapshot_hash": entry["context_policy_snapshot_hash"],
    }
    entry["repository_hints_mode"] = "disabled"
    entry["repository_hints_model_visible_hash"] = "disabled"

    entry["context_strategy_hash"] = stable_hash(strategy)
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="不同 context_strategy_hash"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_missing_context_policy_snapshot_hash(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0].pop("context_policy_snapshot_hash")
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="context_policy_snapshot_hash"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_preflight_context_strategy_mismatch(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    entry = ledger["entries"][0]
    entry["tool_schema_snapshot_hash"] = "9" * 64
    strategy = {
        "initial_context_policy_version": entry["initial_context_policy_version"],
        "repository_hints_mode": entry["repository_hints_mode"],
        "repository_hints_config": entry["repository_hints_config"],
        "tool_schema_snapshot_hash": entry["tool_schema_snapshot_hash"],
        "context_policy_snapshot_hash": entry["context_policy_snapshot_hash"],
    }
    entry["context_strategy_hash"] = stable_hash(strategy)
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="config preflight 字段 tool_schema_snapshot_hash"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_empty_config_preflight_payload(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    entry = ledger["entries"][0]
    _rewrite_config_preflight_ref(
        ledger_root=Path(ledger["run_root"]),
        entry=entry,
        raw_text="{}\n",
    )
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="config preflight 缺少 initial_context_policy_version"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_invalid_config_preflight_payload(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    entry = ledger["entries"][0]
    _rewrite_config_preflight_ref(
        ledger_root=Path(ledger["run_root"]),
        entry=entry,
        raw_text="{not-json}\n",
    )
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="config_preflight_ref 必须指向可解析的 JSON 对象"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_context_policy_snapshot_hash_content_drift(
    tmp_path: Path,
) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    root = Path(ledger["run_root"])
    run_dir = root / ledger["entries"][0]["formal_run_dir"]
    facts_path = run_dir / "run_config_facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["context_policy_snapshot"] = {"changed": True}
    facts_path.write_text(json.dumps(facts), encoding="utf-8")

    with pytest.raises(ConfigError, match="context_policy_snapshot_hash"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_missing_formal_run_config_facts(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    root = Path(ledger["run_root"])
    run_dir = root / ledger["entries"][0]["formal_run_dir"]
    (run_dir / "run_config_facts.json").unlink()

    with pytest.raises(ConfigError, match="run_config_facts.json"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


@pytest.mark.parametrize(
    ("field_name", "expected_error"),
    [
        ("initial_context_policy_version", "initial_context_policy_version"),
        ("repository_hints_mode", "repository_hints_mode"),
        ("repository_hints_config", "repository_hints_config"),
        ("tool_schema_snapshot_hash", "tool_schema_snapshot_hash"),
        ("context_policy_snapshot_hash", "context_policy_snapshot_hash"),
    ],
)
def test_inspect_rejects_formal_run_config_facts_missing_context_field(
    tmp_path: Path,
    field_name: str,
    expected_error: str,
) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    root = Path(ledger["run_root"])
    run_dir = root / ledger["entries"][0]["formal_run_dir"]
    facts_path = run_dir / "run_config_facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    if field_name == "tool_schema_snapshot_hash":
        facts["tool_protocol"].pop("tool_schema_snapshot_sha256")
    else:
        facts.pop(field_name)
    facts_path.write_text(json.dumps(facts), encoding="utf-8")

    with pytest.raises(ConfigError, match=f"formal run_config_facts 缺少 {expected_error}"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_empty_formal_context_policy_snapshot(
    tmp_path: Path,
) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    root = Path(ledger["run_root"])
    run_dir = root / ledger["entries"][0]["formal_run_dir"]
    facts_path = run_dir / "run_config_facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["context_policy_snapshot"] = {}
    facts_path.write_text(json.dumps(facts), encoding="utf-8")

    with pytest.raises(ConfigError, match="formal run_config_facts 缺少 context_policy_snapshot"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_missing_formal_context_policy_snapshot(
    tmp_path: Path,
) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    root = Path(ledger["run_root"])
    run_dir = root / ledger["entries"][0]["formal_run_dir"]
    facts_path = run_dir / "run_config_facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts.pop("context_policy_snapshot")
    facts_path.write_text(json.dumps(facts), encoding="utf-8")

    with pytest.raises(ConfigError, match="formal run_config_facts 缺少 context_policy_snapshot"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_build_does_not_acknowledge_unrelated_preflight_failure(tmp_path: Path) -> None:
    root = _write_root(tmp_path)
    config_path = root / "run_configs" / "pre_verl_dev_001_demo_deepseek_deepseek-v4-pro.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["runtime"]["docker_backend"]["build_base_image"] = "python:3.8"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    _write_formal_run(root, "pre_verl_dev_001_demo", result="success", verifier="accepted", trainable=1)

    ledger_path = build_pre_verl_evidence_ledger(
        root,
        context_inspector=lambda _run_dir: ("passed", None),
    )
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    assert ledger["entries"][0]["config_preflight_status"] == "failed_current_policy"
    assert ledger["entries"][0]["config_preflight_policy_difference_acknowledged"] is False
    with pytest.raises(ConfigError, match="config preflight"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=1,
            expected_result_counts={"success": 1, "failed": 0, "inconclusive": 0},
        )


def test_inspect_rejects_acknowledged_preflight_failure_drift(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    entry = ledger["entries"][0]
    entry["config_revision"] = "dev23_config_r0"
    entry["config_preflight_status"] = "failed_current_policy"
    entry["config_preflight_policy_difference_acknowledged"] = True
    entry["config_preflight_failures"] = []
    entry["config_preflight_failure_count"] = 0
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="config preflight"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )

    entry["config_preflight_failures"] = ["runtime.docker_backend.build_base_image must be python:3.12-slim"]
    entry["config_preflight_failure_count"] = 1
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="config_preflight_policy_difference_acknowledged"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )

    entry["config_preflight_failures"] = ["model.max_output_tokens>=32768 is required"]
    entry["config_preflight_failure_count"] = 2
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="config_preflight_failure_count"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_inspect_rejects_broken_evidence_references(tmp_path: Path) -> None:
    ledger_path = _good_ledger(tmp_path / "missing_formal")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0]["formal_run_dir"] = "run_task_runs/does_not_exist"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="formal_run_dir"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )

    ledger_path = _good_ledger(tmp_path / "bad_preflight_hash")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0]["config_preflight_ref"]["sha256"] = "bad"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="sha256"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )

    ledger_path = _good_ledger(tmp_path / "missing_export")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0]["export_summary"]["export_manifest_refs"][0]["path"] = "exports/missing/export_manifest.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="export_manifest_refs"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )

    ledger_path = _good_ledger(tmp_path / "missing_discard")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][0]["discarded_attempts"] = [
        {
            "run_dir": "discarded_runs/does_not_exist",
            "discard_reason": "host_oom_before_final_verifier",
            "excluded_from_denominator": True,
        }
    ]
    ledger["discarded_attempt_count"] = 1
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    with pytest.raises(ConfigError, match="discarded attempt run_dir"):
        inspect_pre_verl_evidence_ledger(
            ledger_path,
            assert_complete=True,
            expected_formal_denominator=3,
            expected_result_counts={"success": 1, "failed": 1, "inconclusive": 1},
        )


def test_build_rejects_unfinalized_formal_run(tmp_path: Path) -> None:
    root = _write_root(tmp_path)
    _write_formal_run(
        root,
        "pre_verl_dev_001_demo",
        result="success",
        verifier="accepted",
        trainable=1,
        run_status="RUNNING",
    )

    with pytest.raises(ConfigError, match="尚未 FINALIZED"):
        build_pre_verl_evidence_ledger(
            root,
            context_inspector=lambda _run_dir: ("passed", None),
        )


def _good_ledger(tmp_path: Path) -> Path:
    root = _write_root(tmp_path)
    _write_formal_run(root, "pre_verl_dev_001_demo", result="success", verifier="accepted", trainable=2)
    _write_formal_run(root, "pre_verl_dev_002_demo", result="failed", verifier="rejected", invalid=2)
    _write_formal_run(
        root,
        "pre_verl_dev_003_demo",
        result="inconclusive",
        verifier="not_executed",
        skipped=2,
    )
    return build_pre_verl_evidence_ledger(
        root,
        context_inspector=lambda _run_dir: ("passed", None),
    )


def _rewrite_config_preflight_ref(
    *,
    ledger_root: Path,
    entry: dict[str, object],
    raw_text: str,
) -> None:
    ref = entry["config_preflight_ref"]
    assert isinstance(ref, dict)
    path = ref["path"]
    assert isinstance(path, str)
    target = ledger_root / path
    target.write_text(raw_text, encoding="utf-8")
    ref["sha256"] = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def _write_root(tmp_path: Path) -> Path:
    root = tmp_path / "pre-verl-dev-ledger"
    for name in ("run_task_runs", "discarded_runs", "run_configs", "task_definitions", "analysis"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "analysis" / "dev23_task_order.txt").write_text(
        "\n".join(["pre_verl_dev_001_demo", "pre_verl_dev_002_demo", "pre_verl_dev_003_demo"]) + "\n",
        encoding="utf-8",
    )
    for task_id in ("pre_verl_dev_001_demo", "pre_verl_dev_002_demo", "pre_verl_dev_003_demo"):
        _write_task_definition(root, task_id)
        _write_run_config(root, task_id)
    return root


def _write_task_definition(root: Path, task_id: str) -> None:
    task = {
        "id": task_id,
        "task_version": f"{task_id}_v0",
        "dataset_name": "pre_verl_swebench_lite_dev_custom_subset",
        "source_kind": "swebench_lite_dev_materialized",
        "dataset_split": "dev",
        "created_at": "2026-05-11",
        "repo": "../repos/sample_repo",
        "base_commit": "fixture",
        "issue": "Fix the parser bug.",
        "setup_command": None,
        "test_command": "pytest -q",
        "timeouts": {
            "setup_timeout_sec": 60,
            "test_timeout_sec": 30,
            "agent_timeout_sec": 120,
            "final_verifier_timeout_sec": 60,
        },
        "environment": {
            "execution_image": "python:3.12-slim",
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
        "tags": ["python"],
        "metadata": {
            "pre_verl_adapter": "swebench_lite_dev_agentloop_v0",
            "pre_verl_swebench_dev_manifest_path": "runs/pre_verl/dev_manifest.json",
            "pre_verl_agentloop_mode": "formal_baseline",
            "pre_verl_agentloop_baseline_source": "repo_harness_agentloop_run_task",
            "swe_bench_like_final_only": True,
            "final_only": True,
        },
    }
    (root / "task_definitions" / f"{task_id}.yaml").write_text(
        yaml.safe_dump(task, sort_keys=False),
        encoding="utf-8",
    )


def _write_run_config(root: Path, task_id: str) -> None:
    config = {
        "run_id_prefix": "pre_verl_dev_ledger",
        "model": {
            "provider": "deepseek",
            "model_id": "deepseek-v4-pro",
            "max_output_tokens": 32768,
            "retry_policy": "provider_retry_v0",
            "provider_specific_options": {
                "allow_local_secret_file": True,
                "thinking": {"type": "enabled"},
                "reasoning_compatibility": "provider_private_state_replay",
            },
        },
        "runtime": {
            "scaffold_id": "patch_focused_react",
            "execution_mode": "docker",
            "docker_backend": {
                "build_base_image": "python:3.12-slim",
                "image_ref": "repo-harness-pre-verl-test:v0",
            },
            "permission_mode": "auto",
            "test_feedback_policy": "disabled",
            "feedback_tests_passed_policy": "require_model_final",
            "max_turns": 24,
            "max_tool_calls": 96,
            "max_test_runs": 0,
            "task_timeout_sec": 1200,
        },
        "workspace": {
            "output_dir": str(root / "run_task_runs"),
            "keep_workspace": True,
            "network_policy": "deny_agent_run",
        },
    }
    (root / "run_configs" / f"{task_id}_deepseek_deepseek-v4-pro.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )


def _write_formal_run(
    root: Path,
    task_id: str,
    *,
    result: str,
    verifier: str,
    trainable: int = 0,
    invalid: int = 0,
    skipped: int = 0,
    run_status: str = "FINALIZED",
) -> None:
    run_dir = root / "run_task_runs" / f"pre_verl_dev_ledger_{task_id}_deepseek_deepseek-v4-pro"
    run_dir.mkdir(parents=True)
    config_path = root / "run_configs" / f"{task_id}_deepseek_deepseek-v4-pro.yaml"
    task_definition_path = root / "task_definitions" / f"{task_id}.yaml"
    preflight = validate_pre_verl_run_config_entry(
        task_definition_path=task_definition_path,
        config_path=config_path,
        report_path=root / "analysis" / f"{task_id}_fixture_preflight.json",
        assert_resolved_tools_derived=False,
    )
    run_config = load_run_config(config_path)
    repository_hints_config = (
        run_config.context_management.repository_hints.resolved_facts()
    )
    context_policy_snapshot = _context_policy_snapshot(run_config)
    _write_json(run_dir / "run_status.json", {"status": run_status})
    _write_json(
        run_dir / "metrics.json",
        {"run_outcome": result, "final_verifier_status": verifier, "turn_count": 1, "tool_call_count": 1},
    )
    _write_json(
        run_dir / "run_metadata.json",
        {
            "task_id": task_id,
            "failure_diagnostics": [],
            "initial_context_artifacts": {
                "initial_context_policy_version": (
                    "repo_harness_initial_context_policy_v1_lean_hints"
                ),
                "repository_hints_mode": "balanced_eval",
                "repository_hints_config": repository_hints_config,
                "repository_hints_model_visible_hash": "1" * 64,
            },
        },
    )
    _write_json(
        run_dir / "final_verifier_boundary.json",
        {
            "task_id": task_id,
            "accepted": verifier == "accepted",
            "final_verifier_status": verifier,
            "failure_category": None if verifier == "accepted" else "model_patch_rejected_by_final_verifier",
        },
    )
    _write_json(run_dir / "reward.json", {"invalid_for_training": result == "inconclusive"})
    _write_json(
        run_dir / "run_config_facts.json",
        {
            "task_id": task_id,
            "max_output_tokens": 32768,
            "initial_context_policy_version": (
                "repo_harness_initial_context_policy_v1_lean_hints"
            ),
            "repository_hints_mode": "balanced_eval",
            "repository_hints_config": repository_hints_config,
            "context_policy_snapshot_hash": preflight["context_policy_snapshot_hash"],
            "context_policy_snapshot": context_policy_snapshot,
            "tool_protocol": {
                "tool_schema_snapshot_sha256": preflight["tool_schema_snapshot_hash"]
            },
        },
    )
    _write_jsonl(
        run_dir / "events.jsonl",
        [{"event_type": "context_prepared", "data": {"context_reduction": {"microcompact_applied": False}}}],
    )
    _write_export(run_dir, trainable=trainable, invalid=invalid, skipped=skipped)


def _write_discarded_run(root: Path, task_id: str, reason: str | None) -> None:
    name = task_id if reason is None else f"pre_verl_dev_ledger_{task_id}_deepseek_deepseek-v4-pro_{reason}"
    run_dir = root / "discarded_runs" / name
    run_dir.mkdir(parents=True)
    _write_json(run_dir / "run_status.json", {"status": "FINALIZED"})
    _write_json(run_dir / "metrics.json", {"run_outcome": "inconclusive", "final_verifier_status": "not_executed"})


def _write_export(run_dir: Path, *, trainable: int, invalid: int, skipped: int) -> None:
    export_dir = run_dir / "exports" / "sft_fixture"
    export_dir.mkdir(parents=True)
    status = "failed" if invalid else "passed_with_warnings" if skipped else "passed"
    _write_json(
        export_dir / "audit_report.json",
        {
            "export_id": "sft_fixture",
            "format": "sft_jsonl",
            "status": status,
            "summary": {
                "trainable_count": trainable,
                "invalid_count": invalid,
                "skipped_count": skipped,
                "diagnostic_only_count": 0,
            },
        },
    )
    _write_json(
        export_dir / "export_manifest.json",
        {
            "export_id": "sft_fixture",
            "format": "sft_jsonl",
            "included_count": trainable,
            "invalid_count": invalid,
            "skipped_count": skipped,
            "diagnostic_only_count": 0,
            "data_files": [],
        },
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
