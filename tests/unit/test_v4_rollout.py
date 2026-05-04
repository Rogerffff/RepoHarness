import json
import hashlib
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.v4_rollout import (
    build_v4_rollout_orchestration,
    inspect_resource_locks,
    inspect_resource_usage,
    inspect_rollout_budget,
    inspect_rollout_leases,
    inspect_rollout_queue,
    inspect_rollout_resume,
    inspect_rollout_retry,
    inspect_run_selection_query,
)


TASK_FREEZE = Path("docs/v4/evidence/task-source-freeze/task_freeze_manifest.json")


def test_v4_rollout_build_and_inspect_pass(tmp_path: Path) -> None:
    queue_manifest = build_v4_rollout_orchestration(
        task_freeze=TASK_FREEZE,
        output_dir=tmp_path / "rollout",
    )
    rollout_dir = queue_manifest.parent

    assert "complete" in inspect_rollout_queue(rollout_dir, assert_complete=True)
    assert "complete" in inspect_rollout_leases(rollout_dir, assert_complete=True)
    assert "complete" in inspect_rollout_retry(rollout_dir, assert_complete=True)
    assert "complete" in inspect_rollout_budget(rollout_dir, assert_complete=True)
    assert "complete" in inspect_resource_locks(rollout_dir, assert_complete=True)
    assert "complete" in inspect_resource_usage(rollout_dir, assert_complete=True)
    assert "complete" in inspect_rollout_resume(rollout_dir, assert_complete=True)
    assert "complete" in inspect_run_selection_query(rollout_dir / "run_selection_query_report.json", assert_complete=True)
    assert main(["inspect-rollout-queue", str(rollout_dir), "--assert-complete"]) == 0
    assert main(["inspect-run-selection-query", str(rollout_dir / "run_selection_query_report.json"), "--assert-complete"]) == 0


def test_v4_rollout_queue_rejects_state_write_without_lease(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    log = rollout_dir / "worker_run_log.jsonl"
    records = _read_jsonl(log)
    records[1].pop("lease_id")
    _write_jsonl(log, records)

    with pytest.raises(ConfigError, match="无 lease 写入 run state"):
        inspect_rollout_queue(rollout_dir, assert_complete=True)


def test_v4_rollout_queue_rejects_second_worker_or_wrong_lease(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    log = rollout_dir / "worker_run_log.jsonl"
    records = _read_jsonl(log)
    records[1]["worker_id"] = "worker-local-2"
    records[1]["lease_id"] = "lease-for-another-item"
    _write_jsonl(log, records)

    with pytest.raises(ConfigError, match="一个 worker_id|lease_id 与 queue item 不匹配"):
        inspect_rollout_queue(rollout_dir, assert_complete=True)


def test_v4_rollout_queue_rejects_missing_worker_id(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    log = rollout_dir / "worker_run_log.jsonl"
    records = _read_jsonl(log)
    for record in records:
        record.pop("worker_id", None)
    _write_jsonl(log, records)

    with pytest.raises(ConfigError, match="worker_id"):
        inspect_rollout_queue(rollout_dir, assert_complete=True)


def test_v4_rollout_leases_rejects_expired_or_stolen_lease(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    report = rollout_dir / "lease_state_report.json"
    payload = _read_json(report)
    payload["expired_lease_reclaim_required_count"] = 1
    payload["second_worker_steal_attempt_count"] = 1
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="expired lease|第二个 worker"):
        inspect_rollout_leases(rollout_dir, assert_complete=True)


def test_v4_rollout_retry_rejects_attempts_and_fallback_mislabel(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    report = rollout_dir / "retry_policy_report.json"
    payload = _read_json(report)
    payload["fallback_provider_success_marked_primary"] = True
    payload["records"][0]["attempts"] = 3
    payload["records"][0]["continue_after_max_attempts"] = True
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="fallback provider|超过 retry policy|max attempts 后不得继续"):
        inspect_rollout_retry(rollout_dir, assert_complete=True)


def test_v4_rollout_budget_rejects_exceeded_budget_without_worker_log(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    report = rollout_dir / "budget_control_report.json"
    payload = _read_json(report)
    payload["consumed_units"] = payload["limit_units"] + 1
    payload["budget_exhausted"] = False
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="budget consumed|worker log"):
        inspect_rollout_budget(rollout_dir, assert_complete=True)


def test_v4_rollout_budget_rejects_item_exceeded_budget_continuing_without_worker_log(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    report = rollout_dir / "budget_control_report.json"
    payload = _read_json(report)
    record = payload["records"][0]
    record["consumed_units"] = record["limit_units"] + 1
    record["budget_exhausted"] = True
    record["continue_allowed"] = True
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="不得继续执行|worker log"):
        inspect_rollout_budget(rollout_dir, assert_complete=True)


def test_v4_rollout_budget_rejects_worker_log_budget_flag_mismatch(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    report = rollout_dir / "budget_control_report.json"
    payload = _read_json(report)
    payload["worker_log_budget_exhausted_recorded"] = True
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="worker_log_budget_exhausted_recorded"):
        inspect_rollout_budget(rollout_dir, assert_complete=True)


def test_v4_rollout_resource_locks_reject_missing_lock(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    report = rollout_dir / "resource_lock_report.json"
    payload = _read_json(report)
    payload["lock_records"][0]["run_directory_lock_acquired"] = False
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="run directory lock"):
        inspect_resource_locks(rollout_dir, assert_complete=True)


def test_v4_rollout_resume_rejects_checkpoint_tampering_and_hidden_context(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    report = rollout_dir / "checkpoint_state_report.json"
    payload = _read_json(report)
    payload["checkpoint_records"][0]["phase_sha256"] = "0" * 64
    payload["checkpoint_records"][0]["inherited_context_for_resumed_agent"]["reward"] = 1
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="phase_sha256 不匹配|resumed context"):
        inspect_rollout_resume(rollout_dir, assert_complete=True)


def test_v4_rollout_resume_rejects_nested_hidden_context_and_wrong_scope(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    batch = rollout_dir / "batch_resume_report.json"
    payload = _read_json(batch)
    payload["resume_scope"] = "long_term_session_continuation"
    payload["resume_records"][0]["inherited_context"]["non_leaking_run_facts"].append("hidden_verifier_result")
    payload["resume_records"][0]["inherited_context"]["extra_memory"] = "session_continuation"
    _write_json(batch, payload)

    with pytest.raises(ConfigError, match="resume_scope|allowlist|禁止 resume marker"):
        inspect_rollout_resume(rollout_dir, assert_complete=True)


def test_v4_rollout_resume_rejects_short_hidden_marker_with_valid_checkpoint_hash(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    report = rollout_dir / "checkpoint_state_report.json"
    payload = _read_json(report)
    record = payload["checkpoint_records"][0]
    record["inherited_context_for_resumed_agent"]["non_leaking_run_facts"].append("hidden_verifier")
    _refresh_checkpoint_hash(record)
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="禁止 resume marker"):
        inspect_rollout_resume(rollout_dir, assert_complete=True)


def test_v4_rollout_resume_rejects_bare_session_marker_with_valid_checkpoint_hash(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    report = rollout_dir / "checkpoint_state_report.json"
    payload = _read_json(report)
    record = payload["checkpoint_records"][0]
    record["inherited_context_for_resumed_agent"]["non_leaking_run_facts"].append("session")
    _refresh_checkpoint_hash(record)
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="禁止 resume marker"):
        inspect_rollout_resume(rollout_dir, assert_complete=True)


def test_v4_run_selection_query_rejects_missing_predicate_or_hash(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    report = rollout_dir / "run_selection_query_report.json"
    payload = _read_json(report)
    payload["query_predicate"] = {}
    payload["input_manifest_hash"] = ""
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="query predicate|input manifest hash"):
        inspect_run_selection_query(report, assert_complete=True)


def test_v4_run_selection_query_rejects_wrong_predicate_or_selection_mismatch(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    report = rollout_dir / "run_selection_query_report.json"
    payload = _read_json(report)
    payload["query_predicate"]["max_workers"] = 2
    payload["query_predicate"]["role"] = "wrong_role"
    payload["query_predicate"]["provider_mode"] = "cluster"
    payload["query_predicate"]["lease_status"] = "active"
    payload["query_predicate"]["status"] = "accepted"
    payload["query_predicate"]["task_source_tag"] = "public_swebench_like"
    payload["selected_queue_item_ids"] = ["missing"]
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="max_workers|role|provider_mode|lease_status|orchestration_ready|v4_pr_issue|queue item ids"):
        inspect_run_selection_query(report, assert_complete=True)


def test_v4_run_selection_query_requires_sibling_queue_manifest(tmp_path: Path) -> None:
    rollout_dir = _build(tmp_path)
    source = rollout_dir / "run_selection_query_report.json"
    standalone = tmp_path / "standalone" / "run_selection_query_report.json"
    standalone.parent.mkdir()
    standalone.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(ConfigError, match="rollout_queue_manifest"):
        inspect_run_selection_query(standalone, assert_complete=True)


def _build(tmp_path: Path) -> Path:
    queue_manifest = build_v4_rollout_orchestration(
        task_freeze=TASK_FREEZE,
        output_dir=tmp_path / "rollout",
    )
    return queue_manifest.parent


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _refresh_checkpoint_hash(record: dict) -> None:
    payload_for_hash = {
        key: value
        for key, value in record.items()
        if key not in {"checkpoint_payload_sha256", "checkpoint_ref"}
    }
    record["checkpoint_payload_sha256"] = _sha256_payload(payload_for_hash)


def _sha256_payload(payload: object) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
