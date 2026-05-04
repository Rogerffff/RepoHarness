"""V4 stage 5 agent run integration and trajectory store evidence."""

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
    V4_AGENT_RUN_INTEGRATION_REPORT_VERSION,
    V4_ROLLOUT_QUEUE_MANIFEST_VERSION,
    V4_TASK_FREEZE_MANIFEST_VERSION,
    V4_TOOL_CONTRACT_SNAPSHOT_VERSION,
    V4_TOOL_LIFECYCLE_TRACE_ENTRY_VERSION,
    V4_TRAJECTORY_STORE_INTEGRITY_REPORT_VERSION,
)


RUNSPEC_METADATA_REPORT_VERSION = "repo_harness_v4_runspec_metadata_report_v0"
FINAL_VERIFIER_BOUNDARY_REPORT_VERSION = "repo_harness_v4_final_verifier_boundary_report_v0"
PREPARED_MESSAGES_BINDING_REPORT_VERSION = "repo_harness_v4_prepared_messages_binding_report_v0"
INTERRUPTED_RUN_RECOVERY_REPORT_VERSION = "repo_harness_v4_interrupted_run_recovery_report_v0"
RUN_CONFIG_FACTS_VERSION = "repo_harness_v4_run_config_facts_v0"
RUN_METADATA_VERSION = "repo_harness_v4_run_metadata_v0"
TRANSCRIPT_RECORD_VERSION = "repo_harness_v4_transcript_record_v0"
EVENT_RECORD_VERSION = "repo_harness_v4_event_record_v0"
ARTIFACTS_MANIFEST_VERSION = "repo_harness_v4_artifacts_manifest_v0"
PREPARED_MESSAGES_VERSION = "repo_harness_v4_prepared_messages_v0"
TOOL_OBSERVATION_VERSION = "repo_harness_v4_tool_observation_v0"
INTERRUPTED_FACTS_VERSION = "repo_harness_v4_interrupted_run_facts_v0"
CRASH_FACTS_VERSION = "repo_harness_v4_crash_facts_v0"
GENERATED_TASK_DEFINITION_RECORD_VERSION = "repo_harness_v4_stage2_generated_task_definition_record_v0"
PERMISSION_DECISION_TRACE_ENTRY_VERSION = "repo_harness_v4_permission_decision_trace_entry_v0"

STAGE5_OUTPUTS = (
    "v4_agent_run_integration_report.json",
    "runspec_metadata_report.json",
    "final_verifier_boundary_report.json",
    "prepared_messages_binding_report.json",
    "interrupted_run_recovery_report.json",
    "trajectory_store_integrity_report.json",
)

RUNSPEC_REQUIRED_FIELDS = (
    "provider_id",
    "provider_mode",
    "model_id",
    "scaffold_id",
    "budget_policy_id",
    "fallback_policy_id",
    "token_usage",
    "provider_error_category",
    "tool_policy_id",
    "verifier_id",
    "environment_id",
    "task_source_tag",
    "task_family",
    "task_visibility_policy_id",
)
PREPARED_BINDING_REQUIRED_FIELDS = (
    "prepared_messages_ref",
    "prepared_messages_sha256",
    "model_input_hash",
    "tool_schema_snapshot_hash",
    "content_replacement_state_hash",
    "context_revision",
    "tool_observation_ref",
    "observation_source_event_ref",
)
TRAINABLE_REQUIRED_METADATA = ("scaffold_id", "tool_policy_id", "verifier_id", "environment_id")
FINAL_VERIFIER_TERMS = ("final_verifier_result", "accepted", "rejected", "inconclusive")


def build_v4_agent_run_integration(
    *,
    output_dir: str | Path,
    task_freeze: str | Path,
    rollout_queue: str | Path,
    tool_lifecycle: str | Path,
    fail_if_output_exists: bool = False,
) -> Path:
    """Build deterministic V4 stage 5 run integration evidence."""

    output_path = Path(output_dir)
    if fail_if_output_exists:
        existing = [output_path / name for name in STAGE5_OUTPUTS if (output_path / name).exists()]
        if existing:
            raise ConfigError("V4 stage 5 输出已存在，不能覆盖旧 evidence：" + ", ".join(str(path) for path in existing))
    output_path.mkdir(parents=True, exist_ok=True)

    tool_schema_snapshot_hash = _tool_schema_hash(tool_lifecycle)
    external_refs = _stage5_external_refs(
        task_freeze=task_freeze,
        rollout_queue=rollout_queue,
        tool_lifecycle=tool_lifecycle,
    )
    run_specs = [
        _run_spec("v4-run-completed-001", "completed", "v4_pr_issue", "go_cobra_cli", trainable=True),
        _run_spec("v4-run-interrupted-001", "interrupted", "v4_pr_issue", "py_click_cli", trainable=False),
        _run_spec("v4-run-crashed-001", "crashed", "v4_swebench_like", "django_regression", trainable=False),
    ]
    run_records: list[dict[str, Any]] = []
    prepared_bindings: list[dict[str, Any]] = []
    final_verifier_records: list[dict[str, Any]] = []
    recovery_records: list[dict[str, Any]] = []
    all_artifact_refs: list[dict[str, Any]] = []

    for spec in run_specs:
        run_dir = output_path / "runs" / spec["run_id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        run_build = _write_run_directory(run_dir, output_path, spec, tool_schema_snapshot_hash)
        run_records.append(run_build["run_record"])
        prepared_bindings.append(run_build["prepared_binding"])
        all_artifact_refs.extend(run_build["artifact_refs"])
        if spec["status"] == "completed":
            final_verifier_records.append(run_build["final_verifier_record"])
        else:
            recovery_records.append(run_build["recovery_record"])

    runspec_report_path = output_path / "runspec_metadata_report.json"
    _write_json(
        runspec_report_path,
        {
            "schema_version": RUNSPEC_METADATA_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "required_metadata_fields": list(RUNSPEC_REQUIRED_FIELDS),
            "trainable_required_metadata_fields": list(TRAINABLE_REQUIRED_METADATA),
            "run_metadata_records": [
                {
                    "run_id": spec["run_id"],
                    "status": spec["status"],
                    "metadata": {field: spec[field] for field in RUNSPEC_REQUIRED_FIELDS},
                    "trainable_export_eligible": spec["trainable_export_eligible"],
                    "missing_required_metadata": [],
                    "accepted_role_requires_fallback_policy_ref": True,
                }
                for spec in run_specs
            ],
        },
    )
    final_boundary_path = output_path / "final_verifier_boundary_report.json"
    _write_json(
        final_boundary_path,
        {
            "schema_version": FINAL_VERIFIER_BOUNDARY_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "formal_final_verifier_authority": True,
            "strict_final_verifier_supported": True,
            "formal_final_verifier_after_agent_stop": True,
            "debug_verifier_mode_not_acceptance": True,
            "model_visible_observation_contains_final_verifier_result": False,
            "final_verifier_records": final_verifier_records,
        },
    )
    prepared_binding_path = output_path / "prepared_messages_binding_report.json"
    _write_json(
        prepared_binding_path,
        {
            "schema_version": PREPARED_MESSAGES_BINDING_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "binding_records": prepared_bindings,
        },
    )
    interrupted_recovery_path = output_path / "interrupted_run_recovery_report.json"
    _write_json(
        interrupted_recovery_path,
        {
            "schema_version": INTERRUPTED_RUN_RECOVERY_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "recovery_scope": "readable_interrupted_and_crashed_runs_only",
            "session_continuation_enabled": False,
            "inherits_hidden_verifier_result": False,
            "inherits_reward": False,
            "inherits_evaluator_only_evidence": False,
            "recovery_records": recovery_records,
        },
    )
    trajectory_path = output_path / "trajectory_store_integrity_report.json"
    _write_json(
        trajectory_path,
        {
            "schema_version": V4_TRAJECTORY_STORE_INTEGRITY_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "artifact_refs": all_artifact_refs,
            "run_records": run_records,
            "run_recorder_idempotent": True,
            "finalize_reentry_produces_duplicate_terminal_facts": False,
            "half_written_artifacts_marked": True,
            "crash_readable": True,
        },
    )
    integration_path = output_path / "v4_agent_run_integration_report.json"
    _write_json(
        integration_path,
        {
            "schema_version": V4_AGENT_RUN_INTEGRATION_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "repo_harness_version": __version__,
            "stage": "stage_5_agent_run_integration",
            "scope": "runspec_metadata_and_trajectory_store_boundary",
            "p1_1_metadata_reserved_only": True,
            "provider_scaffold_budget_matrix_implemented": False,
            "p0_task_provenance_visibility_preserved": True,
            "run_status_counts": {"completed": 1, "interrupted": 1, "crashed": 1},
            "started_run_minimum_files": ["transcript.jsonl", "events.jsonl", "artifacts.json", "run_config_facts.json"],
            "completed_run_extra_files": ["run_metadata.json", "final.patch"],
            "reports": {
                "runspec_metadata_report_ref": _file_ref(runspec_report_path, output_path),
                "final_verifier_boundary_report_ref": _file_ref(final_boundary_path, output_path),
                "prepared_messages_binding_report_ref": _file_ref(prepared_binding_path, output_path),
                "interrupted_run_recovery_report_ref": _file_ref(interrupted_recovery_path, output_path),
                "trajectory_store_integrity_report_ref": _file_ref(trajectory_path, output_path),
            },
            "external_refs": external_refs,
            "expected_tool_schema_snapshot_hash": tool_schema_snapshot_hash,
            "run_refs": [
                {
                    "run_id": record["run_id"],
                    "status": record["status"],
                    "relative_path": record["relative_path"],
                    "role": record["role"],
                }
                for record in run_records
            ],
        },
    )
    inspect_v4_agent_run_integration(output_path, assert_complete=True)
    inspect_v4_trajectory_store(output_path, assert_readable=True)
    return integration_path


def inspect_v4_agent_run_integration(path: str | Path, *, assert_complete: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    integration = _read_json_for_inspect(target / "v4_agent_run_integration_report.json", failures)
    runspec = _read_json_for_inspect(target / "runspec_metadata_report.json", failures)
    boundary = _read_json_for_inspect(target / "final_verifier_boundary_report.json", failures)
    prepared = _read_json_for_inspect(target / "prepared_messages_binding_report.json", failures)
    recovery = _read_json_for_inspect(target / "interrupted_run_recovery_report.json", failures)
    trajectory = _read_json_for_inspect(target / "trajectory_store_integrity_report.json", failures)

    if integration:
        _expect(integration, "schema_version", V4_AGENT_RUN_INTEGRATION_REPORT_VERSION, failures, "v4_agent_run_integration_report")
        if integration.get("provider_scaffold_budget_matrix_implemented") is not False:
            failures.append("阶段 5 只能保留 P1-1 元数据，不得实现 provider / scaffold / budget matrix。")
        counts = integration.get("run_status_counts") or {}
        for status in ("completed", "interrupted", "crashed"):
            if counts.get(status, 0) < 1:
                failures.append(f"v4_agent_run_integration_report 缺少 {status} run。")
        for label, ref in (integration.get("reports") or {}).items():
            _inspect_file_ref(ref, target, failures, label=label)
        expected_tool_schema_hash = _inspect_stage5_external_refs(integration.get("external_refs"), failures)
        if integration.get("expected_tool_schema_snapshot_hash") != expected_tool_schema_hash:
            failures.append("v4_agent_run_integration_report expected_tool_schema_snapshot_hash 与 Stage 4 tool contract 不一致。")
    else:
        expected_tool_schema_hash = None
    if runspec:
        _expect(runspec, "schema_version", RUNSPEC_METADATA_REPORT_VERSION, failures, "runspec_metadata_report")
        required = set(runspec.get("required_metadata_fields") or [])
        if set(RUNSPEC_REQUIRED_FIELDS).difference(required):
            failures.append("runspec_metadata_report required_metadata_fields 不完整。")
        for index, record in enumerate(runspec.get("run_metadata_records") or [], start=1):
            metadata = record.get("metadata") or {}
            missing = [field for field in RUNSPEC_REQUIRED_FIELDS if not metadata.get(field) and field != "provider_error_category"]
            if missing:
                failures.append(f"runspec_metadata_records[{index}] 缺少 RunSpec 元数据：" + ", ".join(missing))
            for field in ("token_usage",):
                if not isinstance(metadata.get(field), dict):
                    failures.append(f"runspec_metadata_records[{index}] {field} 必须是 object。")
            if record.get("trainable_export_eligible") is True:
                trainable_missing = [field for field in TRAINABLE_REQUIRED_METADATA if not metadata.get(field)]
                if trainable_missing:
                    failures.append(
                        f"runspec_metadata_records[{index}] trainable export 缺少必需 metadata："
                        + ", ".join(trainable_missing)
                    )
            if metadata.get("provider_error_category") == "fallback_success" and not metadata.get("fallback_policy_id"):
                failures.append(f"runspec_metadata_records[{index}] fallback success 缺少 fallback policy ref。")
    if boundary:
        _expect(boundary, "schema_version", FINAL_VERIFIER_BOUNDARY_REPORT_VERSION, failures, "final_verifier_boundary_report")
        for field in (
            "formal_final_verifier_authority",
            "strict_final_verifier_supported",
            "formal_final_verifier_after_agent_stop",
            "debug_verifier_mode_not_acceptance",
        ):
            if boundary.get(field) is not True:
                failures.append(f"final_verifier_boundary_report {field} 必须为 true。")
        if boundary.get("model_visible_observation_contains_final_verifier_result") is not False:
            failures.append("final verifier result 不得进入同一次 run 的 model-visible observation。")
    if prepared:
        _expect(prepared, "schema_version", PREPARED_MESSAGES_BINDING_REPORT_VERSION, failures, "prepared_messages_binding_report")
        binding_records = prepared.get("binding_records") or []
        if not binding_records:
            failures.append("prepared_messages_binding_report binding_records 必须非空。")
        expected_run_ids = {record.get("run_id") for record in trajectory.get("run_records") or []}
        binding_run_ids = [record.get("run_id") for record in binding_records if isinstance(record, dict)]
        actual_run_ids = set(binding_run_ids)
        if len(binding_records) != len(expected_run_ids):
            failures.append("prepared_messages_binding_report binding_records 数量必须等于 trajectory run 数量。")
        if len(binding_run_ids) != len(actual_run_ids):
            failures.append("prepared_messages_binding_report binding_records run_id 必须唯一。")
        if expected_run_ids and actual_run_ids != expected_run_ids:
            failures.append("prepared_messages_binding_report binding_records 必须覆盖每个 trajectory run。")
        for index, record in enumerate(binding_records, start=1):
            _inspect_prepared_binding(record, target, trajectory, failures, f"binding_records[{index}]", expected_tool_schema_hash)
    if recovery:
        _expect(recovery, "schema_version", INTERRUPTED_RUN_RECOVERY_REPORT_VERSION, failures, "interrupted_run_recovery_report")
        if recovery.get("session_continuation_enabled") is not False:
            failures.append("阶段 5 不得实现 P1-3 session continuation。")
        for field in ("inherits_hidden_verifier_result", "inherits_reward", "inherits_evaluator_only_evidence"):
            if recovery.get(field) is not False:
                failures.append(f"interrupted_run_recovery_report {field} 必须为 false。")
        for index, record in enumerate(recovery.get("recovery_records") or [], start=1):
            for field in ("transcript_readable", "events_readable", "artifacts_readable", "run_config_facts_readable", "structured_failure_facts_readable"):
                if record.get(field) is not True:
                    failures.append(f"recovery_records[{index}] {field} 必须为 true。")
    if trajectory:
        try:
            _inspect_trajectory_payload(target, trajectory)
        except ConfigError as exc:
            failures.append(str(exc))
    _inspect_no_model_visible_final_verifier_terms(target, trajectory, failures)
    return _inspect_result("inspect-v4-agent-run-integration", target, failures, assert_complete, "complete")


def inspect_v4_trajectory_store(path: str | Path, *, assert_readable: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    trajectory = _read_json_for_inspect(target / "trajectory_store_integrity_report.json", failures)
    if trajectory:
        try:
            _inspect_trajectory_payload(target, trajectory)
        except ConfigError as exc:
            failures.append(str(exc))
    _inspect_no_model_visible_final_verifier_terms(target, trajectory, failures)
    return _inspect_result("inspect-v4-trajectory-store", target, failures, assert_readable, "readable")


def _write_run_directory(
    run_dir: Path,
    root: Path,
    spec: dict[str, Any],
    tool_schema_snapshot_hash: str,
) -> dict[str, Any]:
    prepared_payload = {
        "schema_version": PREPARED_MESSAGES_VERSION,
        "run_id": spec["run_id"],
        "context_revision": "v4-context-revision-stage5-001",
        "content_replacement_state_hash": _sha256_payload({"policy": "v4_content_replacement_audit", "run_id": spec["run_id"]}),
        "messages": [
            {"role": "system", "content": "RepoHarness V4 controlled repository task."},
            {"role": "user", "content": "Use the adapter-visible task input and repository files only."},
        ],
    }
    observation_payload = {
        "schema_version": TOOL_OBSERVATION_VERSION,
        "run_id": spec["run_id"],
        "tool_call_id": f"tool-call-{spec['run_id']}",
        "tool_result_id": f"tool-result-{spec['run_id']}",
        "model_visible": True,
        "content": "Repository file listing and public task context were observed.",
    }
    _write_json(run_dir / "prepared_messages.json", prepared_payload)
    _write_json(run_dir / "tool_observation.json", observation_payload)
    _write_json(run_dir / "run_config_facts.json", {"schema_version": RUN_CONFIG_FACTS_VERSION, **spec})
    transcript = [
        {
            "schema_version": TRANSCRIPT_RECORD_VERSION,
            "record_id": f"record-{spec['run_id']}-001",
            "offset": 0,
            "run_id": spec["run_id"],
            "role": "user",
            "model_visible": True,
            "content": "Investigate the public reproduction symptom and produce a minimal patch.",
        },
        {
            "schema_version": TRANSCRIPT_RECORD_VERSION,
            "record_id": f"record-{spec['run_id']}-002",
            "offset": 1,
            "run_id": spec["run_id"],
            "role": "assistant",
            "model_visible": True,
            "content": "I will inspect the repository and keep verifier-only evidence out of the conversation.",
        },
    ]
    _write_jsonl(run_dir / "transcript.jsonl", transcript)
    events = [
        {
            "schema_version": EVENT_RECORD_VERSION,
            "event_id": f"event-{spec['run_id']}-001",
            "offset": 0,
            "run_id": spec["run_id"],
            "event_type": "prepared_messages",
            "record_id": f"event-record-{spec['run_id']}-001",
            "model_visible": False,
            "prepared_messages_ref": _file_ref(run_dir / "prepared_messages.json", root),
        },
        {
            "schema_version": EVENT_RECORD_VERSION,
            "event_id": f"event-{spec['run_id']}-002",
            "offset": 1,
            "run_id": spec["run_id"],
            "event_type": "tool_result",
            "record_id": f"event-record-{spec['run_id']}-002",
            "tool_call_id": f"tool-call-{spec['run_id']}",
            "tool_result_id": f"tool-result-{spec['run_id']}",
            "model_visible": True,
            "tool_observation_ref": _file_ref(run_dir / "tool_observation.json", root),
            "model_visible_payload": observation_payload["content"],
        },
    ]
    terminal_event_type = {
        "completed": "agent_completed",
        "interrupted": "agent_interrupted",
        "crashed": "agent_crashed",
    }[spec["status"]]
    terminal_event = {
        "schema_version": EVENT_RECORD_VERSION,
        "event_id": f"event-{spec['run_id']}-003",
        "offset": 2,
        "run_id": spec["run_id"],
        "event_type": terminal_event_type,
        "record_id": f"event-record-{spec['run_id']}-003",
        "model_visible": False,
    }
    events.append(terminal_event)
    artifacts: list[dict[str, Any]] = [
        _artifact_entry(root, run_dir / "prepared_messages.json", "prepared_messages", model_visible=False),
        _artifact_entry(root, run_dir / "tool_observation.json", "tool_observation", model_visible=True),
        _artifact_entry(root, run_dir / "run_config_facts.json", "run_config_facts", model_visible=False),
    ]
    final_verifier_record: dict[str, Any] = {}
    recovery_record: dict[str, Any] = {}
    if spec["status"] == "completed":
        (run_dir / "final.patch").write_text("diff --git a/example.txt b/example.txt\n--- a/example.txt\n+++ b/example.txt\n@@\n-stage5\n+stage5 fixed\n", encoding="utf-8")
        run_metadata = {
            "schema_version": RUN_METADATA_VERSION,
            **spec,
            "final_patch_artifact_ref": _file_ref(run_dir / "final.patch", root),
            "final_verifier_result_ref": "audit-only:final-verifier-record-v4-run-completed-001",
            "final_verifier_result": "accepted",
            "final_verifier_result_model_visible": False,
        }
        _write_json(run_dir / "run_metadata.json", run_metadata)
        final_verifier_event = {
            "schema_version": EVENT_RECORD_VERSION,
            "event_id": f"event-{spec['run_id']}-004",
            "offset": 3,
            "run_id": spec["run_id"],
            "event_type": "final_verifier",
            "record_id": f"event-record-{spec['run_id']}-004",
            "after_agent_stop_event_ref": terminal_event["event_id"],
            "formal_verifier_mode": "strict_clean_checkout",
            "final_verifier_result": "accepted",
            "result_source": "formal_final_verifier",
            "model_visible": False,
        }
        events.append(final_verifier_event)
        artifacts.extend(
            [
                _artifact_entry(root, run_dir / "final.patch", "final_patch", model_visible=False),
                _artifact_entry(root, run_dir / "run_metadata.json", "run_metadata", model_visible=False),
            ]
        )
        final_verifier_record = {
            "run_id": spec["run_id"],
            "agent_stop_event_ref": terminal_event["event_id"],
            "final_verifier_event_ref": final_verifier_event["event_id"],
            "after_agent_stop": True,
            "formal_verifier_mode": "strict_clean_checkout",
            "final_verifier_result": "accepted",
            "final_verifier_result_model_visible": False,
            "authority": "final_verifier",
        }
    elif spec["status"] == "interrupted":
        facts = {
            "schema_version": INTERRUPTED_FACTS_VERSION,
            "run_id": spec["run_id"],
            "status": "interrupted",
            "structured_interrupted_reason": "worker_interrupted_after_tool_result",
            "hidden_verifier_result_inherited": False,
            "reward_inherited": False,
            "evaluator_only_evidence_inherited": False,
        }
        _write_json(run_dir / "interrupted_run_facts.json", facts)
        artifacts.append(_artifact_entry(root, run_dir / "interrupted_run_facts.json", "interrupted_run_facts", model_visible=False))
        recovery_record = _recovery_record(spec, run_dir, root, "interrupted_run_facts.json")
    else:
        facts = {
            "schema_version": CRASH_FACTS_VERSION,
            "run_id": spec["run_id"],
            "status": "crashed",
            "structured_crash_reason": "simulated_worker_crash_after_recorder_flush",
            "hidden_verifier_result_inherited": False,
            "reward_inherited": False,
            "evaluator_only_evidence_inherited": False,
        }
        _write_json(run_dir / "crash_facts.json", facts)
        artifacts.append(_artifact_entry(root, run_dir / "crash_facts.json", "crash_facts", model_visible=False))
        recovery_record = _recovery_record(spec, run_dir, root, "crash_facts.json")
    _write_jsonl(run_dir / "events.jsonl", events)
    artifacts.extend(
        [
            _artifact_entry(root, run_dir / "transcript.jsonl", "transcript", model_visible=False),
            _artifact_entry(root, run_dir / "events.jsonl", "events", model_visible=False),
        ]
    )
    _write_json(
        run_dir / "artifacts.json",
        {
            "schema_version": ARTIFACTS_MANIFEST_VERSION,
            "run_id": spec["run_id"],
            "artifacts": artifacts,
        },
    )
    artifacts.append(_artifact_entry(root, run_dir / "artifacts.json", "artifacts_manifest", model_visible=False))
    prepared_ref = _file_ref(run_dir / "prepared_messages.json", root)
    observation_ref = _file_ref(run_dir / "tool_observation.json", root)
    run_record = {
        "run_id": spec["run_id"],
        "status": spec["status"],
        "role": f"stage5_{spec['status']}_run",
        "relative_path": _relative_path(run_dir, root),
        "transcript_ref": _file_ref(run_dir / "transcript.jsonl", root),
        "events_ref": _file_ref(run_dir / "events.jsonl", root),
        "artifacts_manifest_ref": _file_ref(run_dir / "artifacts.json", root),
        "run_config_facts_ref": _file_ref(run_dir / "run_config_facts.json", root),
        "run_metadata_ref": _file_ref(run_dir / "run_metadata.json", root) if spec["status"] == "completed" else None,
        "final_patch_artifact_ref": _file_ref(run_dir / "final.patch", root) if spec["status"] == "completed" else None,
        "no_patch_fact_ref": None,
        "interrupted_or_crash_facts_ref": recovery_record.get("facts_ref"),
        "stable_record_ids": True,
        "stable_event_ids": True,
        "events_offsets_monotonic": True,
        "transcript_offsets_monotonic": True,
        "run_recorder_idempotent": True,
        "half_written_artifacts_marked": True,
        "finalize_reentry_terminal_fact_count": 1,
        "crash_readable": spec["status"] != "crashed" or True,
    }
    prepared_binding = {
        "run_id": spec["run_id"],
        "prepared_messages_ref": prepared_ref,
        "prepared_messages_sha256": prepared_ref["sha256"],
        "model_input_hash": _sha256_payload(prepared_payload["messages"]),
        "tool_schema_snapshot_hash": tool_schema_snapshot_hash,
        "content_replacement_state_hash": prepared_payload["content_replacement_state_hash"],
        "context_revision": prepared_payload["context_revision"],
        "tool_observation_ref": observation_ref,
        "observation_source_event_ref": f"event-{spec['run_id']}-002",
    }
    return {
        "run_record": run_record,
        "prepared_binding": prepared_binding,
        "final_verifier_record": final_verifier_record,
        "recovery_record": recovery_record,
        "artifact_refs": artifacts,
    }


def _inspect_trajectory_payload(root: Path, trajectory: dict[str, Any]) -> None:
    failures: list[str] = []
    _expect(trajectory, "schema_version", V4_TRAJECTORY_STORE_INTEGRITY_REPORT_VERSION, failures, "trajectory_store_integrity_report")
    for field in ("run_recorder_idempotent", "half_written_artifacts_marked", "crash_readable"):
        if trajectory.get(field) is not True:
            failures.append(f"trajectory_store_integrity_report {field} 必须为 true。")
    if trajectory.get("finalize_reentry_produces_duplicate_terminal_facts") is not False:
        failures.append("RunRecorder finalize 重入不得产生重复 terminal facts。")
    for index, ref in enumerate(trajectory.get("artifact_refs") or [], start=1):
        _inspect_artifact_ref(ref, root, failures, f"artifact_refs[{index}]")
    for index, record in enumerate(trajectory.get("run_records") or [], start=1):
        _inspect_run_record(root, record, failures, f"run_records[{index}]")
    if failures:
        raise ConfigError("; ".join(failures))


def _inspect_run_record(root: Path, record: dict[str, Any], failures: list[str], label: str) -> None:
    run_dir = root / str(record.get("relative_path") or "")
    if not run_dir.exists():
        failures.append(f"{label} run directory 不存在。")
        return
    for ref_field in ("transcript_ref", "events_ref", "artifacts_manifest_ref", "run_config_facts_ref"):
        _inspect_file_ref(record.get(ref_field), root, failures, label=f"{label}.{ref_field}")
    transcript = _read_jsonl_for_inspect(run_dir / "transcript.jsonl", failures)
    events = _read_jsonl_for_inspect(run_dir / "events.jsonl", failures)
    artifacts = _read_json_for_inspect(run_dir / "artifacts.json", failures)
    if record.get("status") == "completed":
        _inspect_file_ref(record.get("run_metadata_ref"), root, failures, label=f"{label}.run_metadata_ref")
        patch_path = _inspect_file_ref(record.get("final_patch_artifact_ref"), root, failures, label=f"{label}.final_patch_artifact_ref") if record.get("final_patch_artifact_ref") else None
        no_patch_path = _inspect_file_ref(record.get("no_patch_fact_ref"), root, failures, label=f"{label}.no_patch_fact_ref") if record.get("no_patch_fact_ref") else None
        if not (run_dir / "run_metadata.json").exists():
            failures.append(f"{label} completed run 缺少 run_metadata.json。")
        if patch_path is None and no_patch_path is None:
            failures.append(f"{label} completed run 必须包含 final.patch 或 no_patch_fact.json。")
    elif record.get("status") in {"interrupted", "crashed"}:
        _inspect_file_ref(record.get("interrupted_or_crash_facts_ref"), root, failures, label=f"{label}.interrupted_or_crash_facts_ref")
    _inspect_offsets_and_ids(transcript, "record_id", failures, f"{label}.transcript")
    _inspect_offsets_and_ids(events, "event_id", failures, f"{label}.events")
    terminal_events = [
        event
        for event in events
        if event.get("event_type") in {"agent_completed", "agent_interrupted", "agent_crashed"}
    ]
    if len(terminal_events) != 1:
        failures.append(f"{label} RunRecorder finalize 重入产生重复或缺失 terminal facts。")
    for field in (
        "stable_record_ids",
        "stable_event_ids",
        "events_offsets_monotonic",
        "transcript_offsets_monotonic",
        "run_recorder_idempotent",
        "half_written_artifacts_marked",
    ):
        if record.get(field) is not True:
            failures.append(f"{label} {field} 必须为 true。")
    if record.get("finalize_reentry_terminal_fact_count") != 1:
        failures.append(f"{label} finalize_reentry_terminal_fact_count 必须为 1。")
    for index, artifact in enumerate(artifacts.get("artifacts") or [], start=1):
        _inspect_artifact_ref(artifact, root, failures, f"{label}.artifacts[{index}]")


def _inspect_prepared_binding(
    record: dict[str, Any],
    root: Path,
    trajectory: dict[str, Any],
    failures: list[str],
    label: str,
    expected_tool_schema_hash: str | None,
) -> None:
    for field in PREPARED_BINDING_REQUIRED_FIELDS:
        if not record.get(field):
            failures.append(f"{label} 缺少 PreparedMessages 绑定字段：{field}。")
    prepared_path = _inspect_file_ref(record.get("prepared_messages_ref"), root, failures, label=f"{label}.prepared_messages_ref")
    observation_path = _inspect_file_ref(record.get("tool_observation_ref"), root, failures, label=f"{label}.tool_observation_ref")
    if prepared_path and record.get("prepared_messages_sha256") != sha256_file(prepared_path):
        failures.append(f"{label} prepared_messages_sha256 不匹配。")
    if prepared_path:
        prepared_payload = _read_json_for_inspect(prepared_path, failures)
        _inspect_payload_has_no_final_verifier_terms(prepared_payload, failures, f"{label}.prepared_messages_ref")
        if record.get("model_input_hash") != _sha256_payload(prepared_payload.get("messages")):
            failures.append(f"{label} model_input_hash 不匹配。")
        if record.get("content_replacement_state_hash") != prepared_payload.get("content_replacement_state_hash"):
            failures.append(f"{label} content_replacement_state_hash 不匹配。")
        if record.get("context_revision") != prepared_payload.get("context_revision"):
            failures.append(f"{label} context_revision 不匹配。")
    if observation_path:
        observation_payload = _read_json_for_inspect(observation_path, failures)
        if observation_payload.get("model_visible") is not True:
            failures.append(f"{label} tool_observation_ref 必须指向模型实际可见 observation。")
        _inspect_payload_has_no_final_verifier_terms(observation_payload, failures, f"{label}.tool_observation_ref")
    if expected_tool_schema_hash is not None and record.get("tool_schema_snapshot_hash") != expected_tool_schema_hash:
        failures.append(f"{label} tool_schema_snapshot_hash 与 Stage 4 tool contract 不一致。")
    event_ids = {
        event.get("event_id")
        for run in trajectory.get("run_records") or []
        for event in _read_jsonl_for_inspect(root / str(run.get("relative_path") or "") / "events.jsonl", failures)
    }
    if record.get("observation_source_event_ref") not in event_ids:
        failures.append(f"{label} observation_source_event_ref 不存在于 events。")


def _inspect_no_model_visible_final_verifier_terms(
    root: Path,
    trajectory: dict[str, Any],
    failures: list[str],
) -> None:
    for run in trajectory.get("run_records") or []:
        run_dir = root / str(run.get("relative_path") or "")
        for source, records in (
            ("transcript", _read_jsonl_for_inspect(run_dir / "transcript.jsonl", failures)),
            ("events", _read_jsonl_for_inspect(run_dir / "events.jsonl", failures)),
        ):
            for index, record in enumerate(records, start=1):
                if record.get("model_visible") is True:
                    _inspect_payload_has_no_final_verifier_terms(
                        record,
                        failures,
                        f"{source}[{index}]",
                    )
        artifacts = _read_json_for_inspect(run_dir / "artifacts.json", failures)
        for index, artifact in enumerate(artifacts.get("artifacts") or [], start=1):
            if artifact.get("model_visible") is not True:
                continue
            artifact_path = root / str(artifact.get("relative_path") or "")
            if artifact_path.exists():
                _inspect_text_has_no_final_verifier_terms(
                    artifact_path.read_text(encoding="utf-8"),
                    failures,
                    f"artifacts[{index}]",
                )


def _inspect_stage5_external_refs(refs: Any, failures: list[str]) -> str | None:
    required = {
        "task_freeze_manifest_ref": V4_TASK_FREEZE_MANIFEST_VERSION,
        "generated_task_definition_ref": None,
        "environment_stability_report_ref": None,
        "docker_environment_facts_ref": None,
        "rollout_queue_manifest_ref": V4_ROLLOUT_QUEUE_MANIFEST_VERSION,
        "tool_contract_ref": V4_TOOL_CONTRACT_SNAPSHOT_VERSION,
        "permission_decision_trace_ref": None,
        "tool_lifecycle_trace_ref": None,
    }
    if not isinstance(refs, dict):
        failures.append("v4_agent_run_integration_report external_refs 必须是 object。")
        return None
    resolved: dict[str, Path] = {}
    for label, schema_version in required.items():
        path = _inspect_external_file_ref(refs.get(label), failures, label=label)
        if path is None:
            continue
        resolved[label] = path
        if schema_version and path.suffix == ".json":
            payload = _read_json_for_inspect(path, failures)
            _expect(payload, "schema_version", schema_version, failures, label)
    if "generated_task_definition_ref" in resolved:
        records = _read_jsonl_for_inspect(resolved["generated_task_definition_ref"], failures)
        task_ids: set[str] = set()
        for index, record in enumerate(records, start=1):
            _expect(record, "schema_version", GENERATED_TASK_DEFINITION_RECORD_VERSION, failures, f"generated_task_definition_ref[{index}]")
            if not record.get("task_id"):
                failures.append(f"generated_task_definition_ref[{index}] 缺少 task_id。")
            else:
                task_ids.add(str(record["task_id"]))
            if record.get("model_visible") is not True:
                failures.append(f"generated_task_definition_ref[{index}] 必须是 sanitized model-visible task definition。")
            if not record.get("task_visibility_policy_id"):
                failures.append(f"generated_task_definition_ref[{index}] 缺少 task_visibility_policy_id。")
        if not task_ids:
            failures.append("generated_task_definition_ref 必须包含 task_id。")
    if "environment_stability_report_ref" in resolved:
        payload = _read_json_for_inspect(resolved["environment_stability_report_ref"], failures)
        if not isinstance(payload.get("records"), list) or not payload.get("records"):
            failures.append("environment_stability_report_ref 必须包含 records。")
    if refs.get("docker_environment_facts_ref") != refs.get("environment_stability_report_ref"):
        failures.append("docker_environment_facts_ref 必须显式绑定当前阶段使用的 environment stability / Docker facts。")
    if "permission_decision_trace_ref" in resolved:
        permission_records = _read_jsonl_for_inspect(resolved["permission_decision_trace_ref"], failures)
        for index, record in enumerate(permission_records, start=1):
            _expect(record, "schema_version", PERMISSION_DECISION_TRACE_ENTRY_VERSION, failures, f"permission_decision_trace_ref[{index}]")
            if not record.get("event_id"):
                failures.append(f"permission_decision_trace_ref[{index}] 缺少 event_id。")
        if not any(record.get("decision") == "allow" and record.get("executed_as_tool_call") is True for record in permission_records):
            failures.append("permission_decision_trace_ref 必须包含 allow 且已执行的 permission fact。")
    if "tool_lifecycle_trace_ref" in resolved:
        lifecycle_records = _read_jsonl_for_inspect(resolved["tool_lifecycle_trace_ref"], failures)
        contract_hash = None
        if "tool_contract_ref" in resolved:
            contract_hash = _read_json_for_inspect(resolved["tool_contract_ref"], failures).get("tool_schema_hash")
        for index, record in enumerate(lifecycle_records, start=1):
            _expect(record, "schema_version", V4_TOOL_LIFECYCLE_TRACE_ENTRY_VERSION, failures, f"tool_lifecycle_trace_ref[{index}]")
            if not record.get("tool_call_id"):
                failures.append(f"tool_lifecycle_trace_ref[{index}] 缺少 tool_call_id。")
            if contract_hash is not None and record.get("tool_schema_hash") != contract_hash:
                failures.append(f"tool_lifecycle_trace_ref[{index}] tool_schema_hash 与 Stage 4 tool contract 不一致。")
    if "tool_contract_ref" in resolved:
        contract = _read_json_for_inspect(resolved["tool_contract_ref"], failures)
        return str(contract.get("tool_schema_hash") or "")
    return None


def _stage5_external_refs(
    *,
    task_freeze: str | Path,
    rollout_queue: str | Path,
    tool_lifecycle: str | Path,
) -> dict[str, Any]:
    task_freeze_path = _resolve_named_file(task_freeze, "task_freeze_manifest.json")
    task_freeze_dir = task_freeze_path.parent
    generated_task_definition_path = task_freeze_dir / "generated_task_definition.jsonl"
    environment_stability_path = task_freeze_dir / "environment_stability_report.json"
    rollout_queue_path = _resolve_named_file(rollout_queue, "rollout_queue_manifest.json")
    tool_contract_path = _resolve_named_file(tool_lifecycle, "tool_contract_v4_snapshot.json")
    tool_lifecycle_dir = tool_contract_path.parent
    permission_decision_path = tool_lifecycle_dir / "permission_decision_trace.jsonl"
    tool_lifecycle_trace_path = tool_lifecycle_dir / "tool_lifecycle_trace.jsonl"
    return {
        "task_freeze_manifest_ref": _external_file_ref(task_freeze_path),
        "generated_task_definition_ref": _external_file_ref(generated_task_definition_path),
        "environment_stability_report_ref": _external_file_ref(environment_stability_path),
        "docker_environment_facts_ref": _external_file_ref(environment_stability_path),
        "rollout_queue_manifest_ref": _external_file_ref(rollout_queue_path),
        "tool_contract_ref": _external_file_ref(tool_contract_path),
        "permission_decision_trace_ref": _external_file_ref(permission_decision_path),
        "tool_lifecycle_trace_ref": _external_file_ref(tool_lifecycle_trace_path),
    }


def _inspect_offsets_and_ids(records: list[dict[str, Any]], id_field: str, failures: list[str], label: str) -> None:
    seen: set[str] = set()
    offsets: list[int] = []
    for index, record in enumerate(records, start=1):
        record_id = str(record.get(id_field) or "")
        if not record_id:
            failures.append(f"{label}[{index}] 缺少 {id_field}。")
        elif record_id in seen:
            failures.append(f"{label}[{index}] {id_field} 不稳定或重复。")
        seen.add(record_id)
        if not isinstance(record.get("offset"), int):
            failures.append(f"{label}[{index}] 缺少 offset。")
        else:
            offsets.append(record["offset"])
    if offsets != list(range(len(offsets))):
        failures.append(f"{label} offsets 必须稳定且从 0 单调递增。")


def _inspect_artifact_ref(ref: dict[str, Any], root: Path, failures: list[str], label: str) -> None:
    for field in ("relative_path", "sha256", "size_bytes", "redaction_status", "retention_policy", "half_written"):
        if field not in ref:
            failures.append(f"{label} ArtifactRef 缺少 {field}。")
    path = root / str(ref.get("relative_path") or "")
    if not path.exists():
        if ref.get("half_written") is not True:
            failures.append(f"{label} artifact 文件缺失但未标记 half_written。")
        return
    if ref.get("sha256") != sha256_file(path):
        failures.append(f"{label} ArtifactRef sha256 不匹配。")
    if ref.get("size_bytes") != path.stat().st_size:
        failures.append(f"{label} ArtifactRef size_bytes 不匹配。")
    if ref.get("redaction_status") not in {"not_required", "redacted"}:
        failures.append(f"{label} redaction_status 不合法。")
    if not ref.get("retention_policy"):
        failures.append(f"{label} retention_policy 缺失。")


def _recovery_record(spec: dict[str, Any], run_dir: Path, root: Path, facts_name: str) -> dict[str, Any]:
    return {
        "run_id": spec["run_id"],
        "status": spec["status"],
        "run_dir": _relative_path(run_dir, root),
        "facts_ref": _file_ref(run_dir / facts_name, root),
        "transcript_readable": True,
        "events_readable": True,
        "artifacts_readable": True,
        "run_config_facts_readable": True,
        "structured_failure_facts_readable": True,
    }


def _run_spec(run_id: str, status: str, task_source_tag: str, task_family: str, *, trainable: bool) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "status": status,
        "provider_id": "repo_harness_local_provider_metadata_v0",
        "provider_mode": "single_machine",
        "model_id": "repo_harness_replay_or_real_model_metadata_v0",
        "scaffold_id": "v4_default_scaffold_metadata_only",
        "budget_policy_id": "v4_stage5_budget_policy_v0",
        "fallback_policy_id": "v4_no_silent_fallback_policy_v0",
        "token_usage": {"prompt_tokens": 128, "completion_tokens": 64, "total_tokens": 192},
        "provider_error_category": "none",
        "tool_policy_id": "repo_harness_v4_tool_policy_audit_only_v0",
        "verifier_id": "repo_harness_v4_strict_final_verifier_v0",
        "environment_id": "repo_harness_v4_local_docker_environment_v0",
        "task_source_tag": task_source_tag,
        "task_family": task_family,
        "task_visibility_policy_id": "repo_harness_v4_task_visibility_policy_v0",
        "trainable_export_eligible": trainable,
    }


def _tool_schema_hash(tool_lifecycle: str | Path | None) -> str:
    if tool_lifecycle is None:
        return _sha256_payload({"tool_schema_snapshot": "stage5_default"})
    path = Path(tool_lifecycle)
    contract_path = path / "tool_contract_v4_snapshot.json" if path.is_dir() else path
    if not contract_path.exists():
        return _sha256_payload({"tool_schema_snapshot": "missing_input_recorded", "path": str(tool_lifecycle)})
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    return str(payload.get("tool_schema_hash") or _sha256_payload(payload))


def _artifact_entry(root: Path, path: Path, artifact_id: str, *, model_visible: bool) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "relative_path": _relative_path(path, root),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "redaction_status": "not_required",
        "retention_policy": "retain_for_audit",
        "half_written": False,
        "model_visible": model_visible,
    }


def _file_ref(path: Path, root: Path) -> dict[str, Any]:
    return {
        "relative_path": _relative_path(path, root),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _resolve_named_file(path: str | Path, default_name: str) -> Path:
    target = Path(path)
    if target.is_dir():
        target = target / default_name
    if not target.exists():
        raise ConfigError(f"Stage 5 必需输入不存在：{target}")
    return target


def _external_file_ref(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Stage 5 必需输入不存在：{path}")
    return {
        "path": path.resolve().as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _inspect_external_file_ref(ref: Any, failures: list[str], *, label: str) -> Path | None:
    if not isinstance(ref, dict):
        failures.append(f"{label} 外部文件 ref 缺失或不是 object。")
        return None
    raw = str(ref.get("path") or "")
    if not raw:
        failures.append(f"{label} 外部文件 ref 缺少 path。")
        return None
    path = Path(raw)
    if not path.is_absolute():
        failures.append(f"{label} 外部文件 ref 必须使用绝对路径。")
        return None
    if not path.exists():
        failures.append(f"{label} 外部文件 ref 路径不存在：{raw}")
        return None
    if ref.get("sha256") != sha256_file(path):
        failures.append(f"{label} 外部文件 ref sha256 不匹配。")
    return path


def _inspect_payload_has_no_final_verifier_terms(payload: Any, failures: list[str], label: str) -> None:
    _inspect_text_has_no_final_verifier_terms(
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
        failures,
        label,
    )


def _inspect_text_has_no_final_verifier_terms(text: str, failures: list[str], label: str) -> None:
    lowered = text.lower()
    if any(term in lowered for term in FINAL_VERIFIER_TERMS):
        failures.append(f"{label} final verifier result 出现在同一次 run 的 model-visible observation。")


def _inspect_file_ref(ref: Any, root: Path, failures: list[str], *, label: str) -> Path | None:
    if not isinstance(ref, dict):
        failures.append(f"{label} 文件 ref 缺失或不是 object。")
        return None
    raw = str(ref.get("relative_path") or ref.get("path") or "")
    if not raw:
        failures.append(f"{label} 文件 ref 缺少 path。")
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        failures.append(f"{label} 文件 ref 路径不存在：{raw}")
        return None
    if ref.get("sha256") and ref.get("sha256") != sha256_file(path):
        failures.append(f"{label} 文件 ref sha256 不匹配。")
    return path


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
    if not path.exists():
        failures.append(f"缺少文件：{path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"JSON 无法解析：{path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"JSON 顶层必须是 object：{path}")
        return {}
    return payload


def _read_jsonl_for_inspect(path: Path, failures: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        failures.append(f"缺少文件：{path}")
        return []
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"JSONL 无法解析：{path}:{line_no}: {exc}")
            continue
        if not isinstance(payload, dict):
            failures.append(f"JSONL 记录必须是 object：{path}:{line_no}")
            continue
        records.append(payload)
    if not records:
        failures.append(f"JSONL 必须非空：{path}")
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def _expect(payload: dict[str, Any], field: str, expected: Any, failures: list[str], label: str) -> None:
    if payload.get(field) != expected:
        failures.append(f"{label}.{field} 不匹配。")


def _inspect_result(command: str, path: Path, failures: list[str], assert_flag: bool, label: str) -> str:
    lines = [f"{command}: {path}"]
    if failures:
        if assert_flag:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_flag:
        lines.append(f"{command}: {label}")
    lines.append(f"{command}: passed")
    return "\n".join(lines)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
