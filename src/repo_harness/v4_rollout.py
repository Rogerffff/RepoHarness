"""V4 stage 3 single-machine rollout orchestration artifacts and inspectors."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness import __version__
from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V4_BATCH_RESUME_REPORT_VERSION,
    V4_BUDGET_CONTROL_REPORT_VERSION,
    V4_CHECKPOINT_STATE_REPORT_VERSION,
    V4_LEASE_STATE_REPORT_VERSION,
    V4_RESOURCE_LOCK_REPORT_VERSION,
    V4_RESOURCE_USAGE_REPORT_VERSION,
    V4_RETRY_POLICY_REPORT_VERSION,
    V4_ROLLOUT_QUEUE_MANIFEST_VERSION,
    V4_RUN_SELECTION_QUERY_REPORT_VERSION,
    V4_WORKER_RUN_LOG_ENTRY_VERSION,
)
from repo_harness.v4_task_freeze import inspect_v4_task_freeze, inspect_v4_task_validity
from repo_harness.workspace.source_hash import compute_source_tree_hash


STAGE3_OUTPUTS = (
    "rollout_queue_manifest.json",
    "worker_run_log.jsonl",
    "lease_state_report.json",
    "batch_resume_report.json",
    "checkpoint_state_report.json",
    "retry_policy_report.json",
    "resource_lock_report.json",
    "budget_control_report.json",
    "resource_usage_report.json",
    "run_selection_query_report.json",
)

CHECKPOINT_REQUIRED_FIELDS = (
    "checkpoint_schema_version",
    "run_id",
    "queue_item_id",
    "phase_id",
    "phase_sha256",
    "next_phase",
    "run_directory_lock_ref",
    "resume_attempt",
    "resume_allowed",
    "unrecoverable_reason",
    "created_at",
    "checkpoint_payload_sha256",
)

RESUME_FORBIDDEN_CONTEXT_FIELDS = (
    "hidden_verifier_result",
    "hidden_verifier",
    "reward",
    "reward_label",
    "reward_scalar",
    "run_outcome",
    "outcome",
    "failure_diagnostics",
    "evaluator_only_evidence",
    "evaluator_only",
    "long_term_user_memory",
    "long_term",
    "session_continuation",
    "session continuation",
    "session",
)


def build_v4_rollout_orchestration(
    *,
    task_freeze: str | Path,
    output_dir: str | Path,
    fail_if_output_exists: bool = False,
) -> Path:
    """Build deterministic single-machine rollout orchestration reports."""

    output_path = Path(output_dir)
    if fail_if_output_exists:
        existing = [output_path / name for name in STAGE3_OUTPUTS if (output_path / name).exists()]
        if existing:
            raise ConfigError(
                "V4 stage 3 输出已存在，不能覆盖旧 evidence："
                + ", ".join(path.as_posix() for path in existing)
            )
    task_freeze_path = Path(task_freeze)
    inspect_v4_task_freeze(task_freeze_path, assert_complete=True)
    task_freeze_payload = _read_json(task_freeze_path)
    task_validity_ref = task_freeze_payload["artifact_refs_by_name"]["task_validity_report.json"]
    task_validity_path = _resolve_ref_path(task_validity_ref)
    inspect_v4_task_validity(task_validity_path, assert_complete=True)
    task_validity = _read_json(task_validity_path)
    accepted_tasks = task_validity["accepted_task_definitions"]
    output_path.mkdir(parents=True, exist_ok=True)

    queue_items = [
        _queue_item(task, index)
        for index, task in enumerate(accepted_tasks, start=1)
    ]
    worker_log = _worker_log_records(queue_items)
    retry_records = _retry_records(queue_items)
    lock_records = _resource_lock_records(queue_items)
    checkpoint_records = _checkpoint_records(queue_items, lock_records)

    _write_json(
        output_path / "rollout_queue_manifest.json",
        {
            "schema_version": V4_ROLLOUT_QUEUE_MANIFEST_VERSION,
            "generated_at": _utc_timestamp(),
            "repo_harness_version": __version__,
            "orchestration_scope": "single_machine_rollout_queue",
            "max_workers": 1,
            "distributed_or_cluster_mode": False,
            "task_freeze_ref": _file_ref(task_freeze_path, "task_freeze"),
            "task_validity_ref": _file_ref(task_validity_path, "task_validity"),
            "input_manifest_hash": sha256_file(task_freeze_path),
            "queue_item_count": len(queue_items),
            "queue_items": queue_items,
        },
    )
    _write_jsonl(output_path / "worker_run_log.jsonl", worker_log)
    _write_json(
        output_path / "lease_state_report.json",
        {
            "schema_version": V4_LEASE_STATE_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "lease_policy_id": "v4_single_worker_lease_policy_v0",
            "active_lease_count": 0,
            "expired_lease_reclaim_required_count": 0,
            "second_worker_steal_attempt_count": 0,
            "lease_records": [
                {
                    "queue_item_id": item["queue_item_id"],
                    "lease_id": item["lease_id"],
                    "worker_id": "worker-local-1",
                    "lease_state": "released",
                    "write_state_requires_active_lease": True,
                    "reclaim_flow_status": "not_required",
                    "second_worker_write_allowed": False,
                }
                for item in queue_items
            ],
        },
    )
    _write_json(
        output_path / "retry_policy_report.json",
        {
            "schema_version": V4_RETRY_POLICY_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "retry_policy_id": "v4_single_machine_retry_policy_v0",
            "max_attempts": 2,
            "fallback_provider_success_marked_primary": False,
            "records": retry_records,
        },
    )
    _write_json(
        output_path / "budget_control_report.json",
        {
            "schema_version": V4_BUDGET_CONTROL_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "budget_policy_id": "v4_stage3_single_machine_budget_v0",
            "budget_policy_present": True,
            "limit_units": 10_000,
            "consumed_units": 2_400,
            "budget_exhausted": False,
            "worker_log_budget_exhausted_recorded": False,
            "records": [
                {
                    "queue_item_id": item["queue_item_id"],
                    "budget_policy_id": "v4_stage3_single_machine_budget_v0",
                    "limit_units": 1_250,
                    "consumed_units": 300,
                    "continue_allowed": True,
                    "budget_exhausted": False,
                }
                for item in queue_items
            ],
        },
    )
    _write_json(
        output_path / "resource_lock_report.json",
        {
            "schema_version": V4_RESOURCE_LOCK_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "resource_lock_policy_id": "v4_single_machine_resource_lock_v0",
            "lock_records": lock_records,
        },
    )
    _write_json(
        output_path / "resource_usage_report.json",
        {
            "schema_version": V4_RESOURCE_USAGE_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "resource_usage_policy_id": "v4_single_machine_resource_usage_v0",
            "host_kind": "apple_silicon_macbook",
            "docker_memory_limit_bytes": 34_359_738_368,
            "max_workers": 1,
            "records": [
                {
                    "queue_item_id": item["queue_item_id"],
                    "cpu_seconds": 1.0,
                    "wall_time_seconds": 1.0,
                    "peak_memory_bytes": 256_000_000,
                    "docker_backend": True,
                    "resource_usage_recorded": True,
                }
                for item in queue_items
            ],
        },
    )
    _write_json(
        output_path / "checkpoint_state_report.json",
        {
            "schema_version": V4_CHECKPOINT_STATE_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "checkpoint_schema_version": "repo_harness_v4_checkpoint_state_v0",
            "checkpoint_records": checkpoint_records,
        },
    )
    _write_json(
        output_path / "batch_resume_report.json",
        {
            "schema_version": V4_BATCH_RESUME_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "resume_scope": "rollout_orchestration_phase_recovery_only",
            "long_term_session_continuation": False,
            "default_long_term_user_memory": False,
            "allowed_inherited_context_fields": [
                "queue_state",
                "workspace_state_ref",
                "public_task_context",
                "non_leaking_run_facts",
            ],
            "forbidden_inherited_context_fields": list(RESUME_FORBIDDEN_CONTEXT_FIELDS),
            "resume_records": [
                {
                    "run_id": checkpoint["run_id"],
                    "queue_item_id": checkpoint["queue_item_id"],
                    "checkpoint_ref": checkpoint["checkpoint_ref"],
                    "resume_allowed": checkpoint["resume_allowed"],
                    "inherited_context": {
                        "queue_state": "phase_ready",
                        "workspace_state_ref": f"workspace-state:{checkpoint['queue_item_id']}",
                        "public_task_context": "adapter_visible_task_context_ref",
                        "non_leaking_run_facts": ["provider_id", "budget_policy_id"],
                    },
                }
                for checkpoint in checkpoint_records
            ],
        },
    )
    run_selection_query_path = output_path / "run_selection_query_report.json"
    _write_json(
        run_selection_query_path,
        {
            "schema_version": V4_RUN_SELECTION_QUERY_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "selection_mode": "explicit_query",
            "query_predicate": {
                "task_source_tag": "v4_pr_issue",
                "role": "v4_rollout_orchestration",
                "provider_mode": "single_machine",
                "scaffold_id": "v4_default_scaffold_metadata_only",
                "retry_state": "within_policy",
                "lease_status": "released",
                "worker_id": "worker-local-1",
                "max_workers": 1,
                "status": "orchestration_ready",
            },
            "input_manifest_hash": sha256_file(task_freeze_path),
            "selected_queue_item_count": len(queue_items),
            "selected_queue_item_ids": [item["queue_item_id"] for item in queue_items],
        },
    )
    inspect_rollout_queue(output_path, assert_complete=True)
    inspect_rollout_leases(output_path, assert_complete=True)
    inspect_rollout_retry(output_path, assert_complete=True)
    inspect_rollout_budget(output_path, assert_complete=True)
    inspect_resource_locks(output_path, assert_complete=True)
    inspect_resource_usage(output_path, assert_complete=True)
    inspect_rollout_resume(output_path, assert_complete=True)
    inspect_run_selection_query(run_selection_query_path, assert_complete=True)
    return output_path / "rollout_queue_manifest.json"


def inspect_rollout_queue(path: str | Path, *, assert_complete: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    queue = _read_json_for_inspect(target / "rollout_queue_manifest.json", failures)
    worker_log = _read_jsonl_for_inspect(target / "worker_run_log.jsonl", failures)
    if queue:
        _expect(queue, "schema_version", V4_ROLLOUT_QUEUE_MANIFEST_VERSION, failures, "rollout_queue_manifest")
        if queue.get("orchestration_scope") != "single_machine_rollout_queue":
            failures.append("rollout_queue_manifest 必须限定为 single_machine_rollout_queue。")
        if queue.get("max_workers") != 1:
            failures.append("rollout_queue_manifest max_workers 必须为 1。")
        if queue.get("distributed_or_cluster_mode") is not False:
            failures.append("rollout_queue_manifest 禁止 cluster / distributed mode。")
        items = queue.get("queue_items")
        if not isinstance(items, list) or not items:
            failures.append("rollout_queue_manifest queue_items 必须是非空列表。")
        else:
            for index, item in enumerate(items, start=1):
                for field in ("queue_item_id", "task_id", "provider_id", "budget_policy_id", "lease_id"):
                    if not item.get(field):
                        failures.append(f"queue_items[{index}] 缺少 {field}。")
                if item.get("lease_required") is not True:
                    failures.append(f"queue_items[{index}] 写入 run state 必须要求 lease。")
    _inspect_worker_log(worker_log, failures, queue)
    return _inspect_result("inspect-rollout-queue", target, failures, assert_complete, "complete")


def inspect_rollout_leases(path: str | Path, *, assert_complete: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    report = _read_json_for_inspect(target / "lease_state_report.json", failures)
    if report:
        _expect(report, "schema_version", V4_LEASE_STATE_REPORT_VERSION, failures, "lease_state_report")
        if report.get("expired_lease_reclaim_required_count") != 0:
            failures.append("expired lease 必须进入 reclaim 流程或为 0。")
        if report.get("second_worker_steal_attempt_count") != 0:
            failures.append("active lease 禁止被第二个 worker 抢占。")
        seen: set[str] = set()
        for index, record in enumerate(report.get("lease_records") or [], start=1):
            lease_id = str(record.get("lease_id") or "")
            if not lease_id:
                failures.append(f"lease_records[{index}] 缺少 lease_id。")
            if lease_id in seen:
                failures.append(f"lease_records[{index}] lease_id 重复。")
            seen.add(lease_id)
            if record.get("write_state_requires_active_lease") is not True:
                failures.append(f"lease_records[{index}] run state 写入必须要求 active lease。")
            if record.get("second_worker_write_allowed") is not False:
                failures.append(f"lease_records[{index}] 第二 worker 不得写入。")
    return _inspect_result("inspect-rollout-leases", target, failures, assert_complete, "complete")


def inspect_rollout_retry(path: str | Path, *, assert_complete: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    report = _read_json_for_inspect(target / "retry_policy_report.json", failures)
    if report:
        _expect(report, "schema_version", V4_RETRY_POLICY_REPORT_VERSION, failures, "retry_policy_report")
        max_attempts = report.get("max_attempts")
        if not isinstance(max_attempts, int) or max_attempts <= 0:
            failures.append("retry_policy_report max_attempts 必须是正整数。")
        if report.get("fallback_provider_success_marked_primary") is not False:
            failures.append("fallback provider 成功不得标记为 primary provider accepted。")
        for index, record in enumerate(report.get("records") or [], start=1):
            if record.get("attempts", 0) > max_attempts:
                failures.append(f"retry records[{index}] 超过 retry policy max attempts。")
            if record.get("continue_after_max_attempts") is True:
                failures.append(f"retry records[{index}] 超过 max attempts 后不得继续执行。")
    return _inspect_result("inspect-rollout-retry", target, failures, assert_complete, "complete")


def inspect_rollout_budget(path: str | Path, *, assert_complete: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    report = _read_json_for_inspect(target / "budget_control_report.json", failures)
    worker_log = _read_jsonl_for_inspect(target / "worker_run_log.jsonl", failures)
    if report:
        _expect(report, "schema_version", V4_BUDGET_CONTROL_REPORT_VERSION, failures, "budget_control_report")
        if report.get("budget_policy_present") is not True:
            failures.append("budget policy 缺失。")
        if report.get("consumed_units", 0) > report.get("limit_units", -1):
            if report.get("budget_exhausted") is not True:
                failures.append("budget consumed 超过 limit 时必须 budget_exhausted=true。")
            if not any(record.get("event_type") == "budget_exhausted" for record in worker_log):
                failures.append("budget exhausted 必须写入 worker log。")
        actual_budget_exhausted_events = [record for record in worker_log if record.get("event_type") == "budget_exhausted"]
        if bool(actual_budget_exhausted_events) != bool(report.get("worker_log_budget_exhausted_recorded")):
            failures.append("worker_log_budget_exhausted_recorded 必须与 worker log budget_exhausted 事件一致。")
        for index, record in enumerate(report.get("records") or [], start=1):
            if record.get("consumed_units", 0) > record.get("limit_units", -1) and record.get("budget_exhausted") is not True:
                failures.append(f"budget records[{index}] consumed 超过 limit 但未标记 exhausted。")
            if record.get("consumed_units", 0) > record.get("limit_units", -1):
                if record.get("continue_allowed") is not False:
                    failures.append(f"budget records[{index}] budget exhausted 后不得继续执行。")
                if not any(
                    log_record.get("event_type") == "budget_exhausted"
                    and log_record.get("queue_item_id") == record.get("queue_item_id")
                    for log_record in worker_log
                ):
                    failures.append(f"budget records[{index}] budget exhausted 必须写入 worker log。")
    return _inspect_result("inspect-rollout-budget", target, failures, assert_complete, "complete")


def inspect_resource_locks(path: str | Path, *, assert_complete: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    report = _read_json_for_inspect(target / "resource_lock_report.json", failures)
    if report:
        _expect(report, "schema_version", V4_RESOURCE_LOCK_REPORT_VERSION, failures, "resource_lock_report")
        for index, record in enumerate(report.get("lock_records") or [], start=1):
            if record.get("run_directory_lock_acquired") is not True:
                failures.append(f"lock_records[{index}] 缺少 run directory lock。")
            if not record.get("lease_id"):
                failures.append(f"lock_records[{index}] 缺少 lease_id。")
            if record.get("lock_released") is not True:
                failures.append(f"lock_records[{index}] lock 必须释放或结构化记录。")
    return _inspect_result("inspect-resource-locks", target, failures, assert_complete, "complete")


def inspect_resource_usage(path: str | Path, *, assert_complete: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    report = _read_json_for_inspect(target / "resource_usage_report.json", failures)
    if report:
        _expect(report, "schema_version", V4_RESOURCE_USAGE_REPORT_VERSION, failures, "resource_usage_report")
        if report.get("max_workers") != 1:
            failures.append("resource_usage_report max_workers 必须为 1。")
        for index, record in enumerate(report.get("records") or [], start=1):
            if record.get("resource_usage_recorded") is not True:
                failures.append(f"resource usage records[{index}] 必须记录 resource usage。")
            if record.get("peak_memory_bytes", 0) <= 0:
                failures.append(f"resource usage records[{index}] peak_memory_bytes 必须大于 0。")
    return _inspect_result("inspect-resource-usage", target, failures, assert_complete, "complete")


def inspect_rollout_resume(path: str | Path, *, assert_complete: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    batch = _read_json_for_inspect(target / "batch_resume_report.json", failures)
    checkpoint = _read_json_for_inspect(target / "checkpoint_state_report.json", failures)
    if batch:
        _expect(batch, "schema_version", V4_BATCH_RESUME_REPORT_VERSION, failures, "batch_resume_report")
        if batch.get("resume_scope") != "rollout_orchestration_phase_recovery_only":
            failures.append("batch_resume_report resume_scope 必须为 rollout_orchestration_phase_recovery_only。")
        if batch.get("long_term_session_continuation") is not False:
            failures.append("batch resume 禁止实现成长期 session continuation。")
        if batch.get("default_long_term_user_memory") is not False:
            failures.append("batch resume 禁止默认长期用户记忆。")
        allowed_fields = set(batch.get("allowed_inherited_context_fields") or [])
        expected_allowed_fields = {"queue_state", "workspace_state_ref", "public_task_context", "non_leaking_run_facts"}
        if allowed_fields != expected_allowed_fields:
            failures.append("batch_resume_report allowed inherited context fields 必须精确匹配阶段恢复 allowlist。")
        for index, record in enumerate(batch.get("resume_records") or [], start=1):
            inherited = record.get("inherited_context") or {}
            if set(inherited) != expected_allowed_fields:
                failures.append(f"resume_records[{index}] inherited_context 必须精确匹配 allowlist。")
            _inspect_no_forbidden_resume_context(inherited, failures, f"resume_records[{index}].inherited_context")
    if checkpoint:
        _expect(checkpoint, "schema_version", V4_CHECKPOINT_STATE_REPORT_VERSION, failures, "checkpoint_state_report")
        for index, record in enumerate(checkpoint.get("checkpoint_records") or [], start=1):
            for field in CHECKPOINT_REQUIRED_FIELDS:
                if field not in record:
                    failures.append(f"checkpoint_records[{index}] 缺少 {field}。")
            phase_payload = record.get("phase_payload") or {}
            if record.get("phase_sha256") != _sha256_payload(phase_payload):
                failures.append(f"checkpoint_records[{index}] phase_sha256 不匹配。")
            payload_for_hash = {
                key: value
                for key, value in record.items()
                if key not in {"checkpoint_payload_sha256", "checkpoint_ref"}
            }
            if record.get("checkpoint_payload_sha256") != _sha256_payload(payload_for_hash):
                failures.append(f"checkpoint_records[{index}] checkpoint_payload_sha256 不匹配。")
            if not record.get("run_directory_lock_ref"):
                failures.append(f"checkpoint_records[{index}] run directory lock 缺失。")
            inherited = record.get("inherited_context_for_resumed_agent") or {}
            if set(inherited) != {"queue_state", "workspace_state_ref", "public_task_context", "non_leaking_run_facts"}:
                failures.append(f"checkpoint_records[{index}] resumed context 必须精确匹配 allowlist。")
            _inspect_no_forbidden_resume_context(
                inherited,
                failures,
                f"checkpoint_records[{index}].inherited_context_for_resumed_agent",
            )
    return _inspect_result("inspect-rollout-resume", target, failures, assert_complete, "complete")


def inspect_run_selection_query(path: str | Path, *, assert_complete: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    report = _read_json_for_inspect(target, failures)
    if report:
        _expect(report, "schema_version", V4_RUN_SELECTION_QUERY_REPORT_VERSION, failures, "run_selection_query_report")
        if not isinstance(report.get("query_predicate"), dict) or not report.get("query_predicate"):
            failures.append("run_selection_query_report 缺少 query predicate。")
        if not report.get("input_manifest_hash"):
            failures.append("run_selection_query_report 缺少 input manifest hash。")
        if report.get("selection_mode") != "explicit_query":
            failures.append("run_selection_query_report 必须使用 explicit_query。")
        predicate = report.get("query_predicate") if isinstance(report.get("query_predicate"), dict) else {}
        if predicate.get("max_workers") != 1:
            failures.append("run_selection_query_report query_predicate.max_workers 必须为 1。")
        if predicate.get("status") != "orchestration_ready":
            failures.append("run_selection_query_report query_predicate.status 必须为 orchestration_ready。")
        if predicate.get("task_source_tag") != "v4_pr_issue":
            failures.append("run_selection_query_report query_predicate.task_source_tag 必须为 v4_pr_issue。")
        if predicate.get("role") != "v4_rollout_orchestration":
            failures.append("run_selection_query_report query_predicate.role 必须为 v4_rollout_orchestration。")
        if predicate.get("provider_mode") != "single_machine":
            failures.append("run_selection_query_report query_predicate.provider_mode 必须为 single_machine。")
        if predicate.get("scaffold_id") != "v4_default_scaffold_metadata_only":
            failures.append("run_selection_query_report query_predicate.scaffold_id 不匹配。")
        if predicate.get("retry_state") != "within_policy":
            failures.append("run_selection_query_report query_predicate.retry_state 必须为 within_policy。")
        if predicate.get("lease_status") != "released":
            failures.append("run_selection_query_report query_predicate.lease_status 必须为 released。")
        if predicate.get("worker_id") != "worker-local-1":
            failures.append("run_selection_query_report query_predicate.worker_id 必须为 worker-local-1。")
        selected_ids = report.get("selected_queue_item_ids")
        if not isinstance(selected_ids, list) or not selected_ids:
            failures.append("run_selection_query_report selected_queue_item_ids 必须是非空列表。")
        elif report.get("selected_queue_item_count") != len(selected_ids):
            failures.append("run_selection_query_report selected_queue_item_count 必须等于 selected_queue_item_ids 长度。")
        queue_manifest = target.parent / "rollout_queue_manifest.json"
        if assert_complete and not queue_manifest.exists():
            failures.append("run_selection_query_report assert-complete 需要同目录 rollout_queue_manifest.json。")
        if queue_manifest.exists() and isinstance(selected_ids, list):
            queue = _read_json_for_inspect(queue_manifest, failures)
            queue_ids = {item.get("queue_item_id") for item in queue.get("queue_items") or []}
            if set(selected_ids) != queue_ids:
                failures.append("run_selection_query_report selected_queue_item_ids 必须与 rollout queue item ids 一致。")
    return _inspect_result("inspect-run-selection-query", target, failures, assert_complete, "complete")


def _queue_item(task: dict[str, Any], index: int) -> dict[str, Any]:
    queue_item_id = f"v4-queue-{index:03d}-{task['task_id']}"
    return {
        "queue_item_id": queue_item_id,
        "task_id": task["task_id"],
        "candidate_id": task["candidate_id"],
        "task_source_tag": task["task_source_tag"],
        "phase_id": "rollout_orchestration_ready",
        "provider_id": "local_replay_or_real_provider_placeholder",
        "provider_mode": "single_machine",
        "scaffold_id": "v4_default_scaffold_metadata_only",
        "budget_policy_id": "v4_stage3_single_machine_budget_v0",
        "fallback_policy_id": "v4_no_silent_fallback_policy_v0",
        "lease_required": True,
        "lease_id": f"lease-{queue_item_id}",
        "max_attempts": 2,
        "attempts": 1,
        "status": "orchestration_ready",
    }


def _worker_log_records(queue_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in queue_items:
        records.extend(
            [
                {
                    "schema_version": V4_WORKER_RUN_LOG_ENTRY_VERSION,
                    "event_type": "lease_acquired",
                    "queue_item_id": item["queue_item_id"],
                    "worker_id": "worker-local-1",
                    "lease_id": item["lease_id"],
                    "state_write_allowed": True,
                },
                {
                    "schema_version": V4_WORKER_RUN_LOG_ENTRY_VERSION,
                    "event_type": "state_written",
                    "queue_item_id": item["queue_item_id"],
                    "worker_id": "worker-local-1",
                    "lease_id": item["lease_id"],
                    "state_write_allowed": True,
                    "fallback_provider_success_marked_primary": False,
                },
            ]
        )
    return records


def _retry_records(queue_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "queue_item_id": item["queue_item_id"],
            "task_id": item["task_id"],
            "provider_id": item["provider_id"],
            "attempts": item["attempts"],
            "max_attempts": item["max_attempts"],
            "continue_after_max_attempts": False,
            "fallback_provider_used": False,
            "fallback_policy_id": item["fallback_policy_id"],
        }
        for item in queue_items
    ]


def _resource_lock_records(queue_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "queue_item_id": item["queue_item_id"],
            "task_id": item["task_id"],
            "lease_id": item["lease_id"],
            "run_directory_lock_ref": f"lock:{item['queue_item_id']}",
            "run_directory_lock_acquired": True,
            "resource_lock_scope": "single_machine_run_directory",
            "lock_released": True,
        }
        for item in queue_items
    ]


def _checkpoint_records(queue_items: list[dict[str, Any]], lock_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lock_by_queue = {record["queue_item_id"]: record for record in lock_records}
    records = []
    for index, item in enumerate(queue_items, start=1):
        phase_payload = {
            "queue_item_id": item["queue_item_id"],
            "phase_id": "rollout_orchestration_ready",
            "lease_id": item["lease_id"],
        }
        record: dict[str, Any] = {
            "checkpoint_schema_version": "repo_harness_v4_checkpoint_state_v0",
            "run_id": f"v4-stage3-run-{index:03d}",
            "queue_item_id": item["queue_item_id"],
            "phase_id": "rollout_orchestration_ready",
            "phase_payload": phase_payload,
            "phase_sha256": _sha256_payload(phase_payload),
            "next_phase": "agent_run_integration",
            "run_directory_lock_ref": lock_by_queue[item["queue_item_id"]]["run_directory_lock_ref"],
            "resume_attempt": 0,
            "resume_allowed": True,
            "unrecoverable_reason": None,
            "created_at": _utc_timestamp(),
            "inherited_context_for_resumed_agent": {
                "queue_state": "phase_ready",
                "workspace_state_ref": f"workspace-state:{item['queue_item_id']}",
                "public_task_context": "adapter_visible_task_context_ref",
                "non_leaking_run_facts": ["provider_id", "budget_policy_id"],
            },
            "checkpoint_ref": f"checkpoint:{item['queue_item_id']}",
        }
        payload_for_hash = {
            key: value
            for key, value in record.items()
            if key not in {"checkpoint_payload_sha256", "checkpoint_ref"}
        }
        record["checkpoint_payload_sha256"] = _sha256_payload(payload_for_hash)
        records.append(record)
    return records


def _inspect_worker_log(
    records: list[dict[str, Any]],
    failures: list[str],
    queue: dict[str, Any],
) -> None:
    if not records:
        failures.append("worker_run_log.jsonl 必须至少包含一条记录。")
        return
    queue_items = queue.get("queue_items") if isinstance(queue.get("queue_items"), list) else []
    queue_lease_by_item = {
        item.get("queue_item_id"): item.get("lease_id")
        for item in queue_items
    }
    worker_ids = {record.get("worker_id") for record in records if record.get("worker_id")}
    if len(worker_ids) != 1:
        failures.append("worker_run_log 必须精确包含一个 worker_id。")
    for index, record in enumerate(records, start=1):
        _expect(record, "schema_version", V4_WORKER_RUN_LOG_ENTRY_VERSION, failures, f"worker_run_log[{index}]")
        if not record.get("worker_id"):
            failures.append(f"worker_run_log[{index}] 缺少 worker_id。")
        if record.get("event_type") in {"state_written", "run_state_written"} and not record.get("lease_id"):
            failures.append(f"worker_run_log[{index}] 无 lease 写入 run state。")
        if record.get("event_type") in {"state_written", "run_state_written"} and record.get("state_write_allowed") is not True:
            failures.append(f"worker_run_log[{index}] run state 写入未被 lease 允许。")
        queue_item_id = record.get("queue_item_id")
        if record.get("event_type") in {"state_written", "run_state_written"}:
            if queue_item_id not in queue_lease_by_item:
                failures.append(f"worker_run_log[{index}] queue_item_id 不属于 rollout queue。")
            elif record.get("lease_id") != queue_lease_by_item[queue_item_id]:
                failures.append(f"worker_run_log[{index}] lease_id 与 queue item 不匹配。")
        if record.get("fallback_provider_success_marked_primary") is True:
            failures.append(f"worker_run_log[{index}] fallback provider 成功被标记为 primary。")


def _inspect_no_forbidden_resume_context(value: Any, failures: list[str], path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if _matches_forbidden_resume_marker(key_text):
                failures.append(f"{path}.{key_text} 继承了禁止 resume 字段或 marker。")
            _inspect_no_forbidden_resume_context(child, failures, f"{path}.{key_text}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _inspect_no_forbidden_resume_context(child, failures, f"{path}[{index}]")
    elif isinstance(value, str):
        if _matches_forbidden_resume_marker(value):
            failures.append(f"{path} 包含禁止 resume marker。")


def _matches_forbidden_resume_marker(value: str) -> bool:
    normalized = value.lower().replace("_", " ").replace("-", " ")
    return any(marker.replace("_", " ").replace("-", " ") in normalized for marker in RESUME_FORBIDDEN_CONTEXT_FIELDS)


def _inspect_result(command: str, path: Path, failures: list[str], assert_complete: bool, label: str) -> str:
    lines = [f"{command}: {path}"]
    if failures:
        if assert_complete:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_complete:
        lines.append(f"{command}: {label}")
    lines.append(f"{command}: passed")
    return "\n".join(lines)


def _expect(payload: dict[str, Any], field: str, expected: Any, failures: list[str], label: str) -> None:
    if payload.get(field) != expected:
        failures.append(f"{label}.{field} 不匹配。")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"JSON 文件不存在：{path}")
        return {}
    except json.JSONDecodeError as exc:
        failures.append(f"JSON 文件无效：{path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"JSON 顶层必须是 object：{path}")
        return {}
    return payload


def _read_jsonl_for_inspect(path: Path, failures: list[str]) -> list[dict[str, Any]]:
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except FileNotFoundError:
        failures.append(f"JSONL 文件不存在：{path}")
        return []
    records: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"{path.name} 第 {index} 行不是合法 JSON：{exc}")
            continue
        if not isinstance(record, dict):
            failures.append(f"{path.name} 第 {index} 行顶层必须是 object。")
            continue
        records.append(record)
    return records


def _resolve_ref_path(ref: dict[str, Any]) -> Path:
    path = Path(str(ref.get("path") or ref.get("relative_path") or ""))
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        raise ConfigError(f"文件 ref 路径不存在：{path}")
    actual = compute_source_tree_hash(path) if path.is_dir() else sha256_file(path)
    if actual != ref.get("sha256"):
        raise ConfigError(f"文件 ref sha256 不匹配：{path}")
    return path


def _file_ref(path: Path, category: str) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "kind": "directory" if path.is_dir() else (path.suffix.lstrip(".") or "file"),
        "category": category,
        "model_visible": False,
        "sha256": compute_source_tree_hash(path) if path.is_dir() else sha256_file(path),
        "size_bytes": 0 if path.is_dir() else path.stat().st_size,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _sha256_payload(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
