"""V3 experiment resume builder and inspection helpers."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import ValidationError

from repo_harness import __version__
from repo_harness.errors import ConfigError, RepoHarnessError
from repo_harness.evaluation.experiment import (
    _run_config_payload,
    _run_id,
    _task_id,
    load_experiment_config,
)
from repo_harness.evaluation.runner import InjectInterruptPoint, InjectedInterruptError, run_task
from repo_harness.evaluation.schemas import (
    ExperimentResumeManifest,
    ExperimentResumeRunEntry,
    RunCheckpoint,
)
from repo_harness.trajectory import ArtifactRef, read_jsonl, verify_artifact_manifest
from repo_harness.trajectory.recorder import RunRecorder, RunRecorderError
from repo_harness.v3_acceptance import CommandLogEntry
from repo_harness.v3_visibility import V3ContaminationDenylist
from repo_harness.workspace.source_hash import compute_file_sha256, compute_source_tree_hash


RESUME_REPORT_VERSION = "repo_harness_v3_experiment_resume_report_v0"
CHECKPOINT_MANIFEST_VERSION = "repo_harness_v3_run_checkpoint_manifest_v0"
INTERRUPTED_DIAGNOSTICS_VERSION = "repo_harness_v3_interrupted_run_diagnostics_v0"
FAILURE_DISTRIBUTION_VERSION = "repo_harness_v3_failure_distribution_stage8_v0"
LOCK_DIAGNOSTIC_VERSION = "repo_harness_v3_run_directory_lock_diagnostic_v0"


def build_v3_experiment_resume(
    *,
    config_path: str | Path,
    output_dir: str | Path,
    inject_interrupt_after: InjectInterruptPoint = "baseline",
) -> Path:
    """Construct an interrupted experiment, resume it, and write V3 resume evidence."""

    if inject_interrupt_after not in {"baseline", "agent_loop", "final_verifier"}:
        raise ConfigError(f"不支持的中断注入点：{inject_interrupt_after}")
    config = load_experiment_config(config_path, output_dir=output_dir)
    output_root = Path(config.output_dir)
    if output_root.exists():
        raise ConfigError(f"Stage 8 output directory 已存在，不能覆盖：{output_root}")
    output_root.mkdir(parents=True)
    config_dir = output_root / ".repo_harness_experiment_configs"
    config_dir.mkdir()
    checkpoint_dir = output_root / "checkpoints"
    checkpoint_dir.mkdir()
    command_log_path = output_root / "command_log.jsonl"
    specs = _run_specs(config)
    if len(specs) < 3:
        raise ConfigError("V3 resume smoke 至少需要三个 run specs：completed、interrupted、pending。")

    checkpoint_records: list[dict[str, Any]] = []
    checkpoints: list[RunCheckpoint] = []
    run_entries: list[ExperimentResumeRunEntry] = []
    command_entries: list[CommandLogEntry] = []

    completed_spec = specs[0]
    interrupted_spec = specs[1]
    pending_spec = specs[2]

    completed_run_dir, completed_config = _execute_run(
        spec=completed_spec,
        config=config,
        config_dir=config_dir,
        output_root=output_root,
        command_log_path=command_log_path,
        command_entries=command_entries,
        inject_interrupt_after=None,
    )
    completed_checkpoint = _write_checkpoint(
        checkpoint_dir=checkpoint_dir,
        output_root=output_root,
        run_id=completed_spec["run_id"],
        run_dir=completed_run_dir,
        task_id=completed_spec["task_id"],
        status="completed",
        checkpoint_type="export_completed",
        resume_eligibility="not_needed",
    )
    checkpoints.append(completed_checkpoint["checkpoint"])
    checkpoint_records.append(completed_checkpoint["record"])

    interrupted_run_dir = output_root / interrupted_spec["run_id"]
    interrupted_config = _write_run_config(config_dir, config=config, spec=interrupted_spec)
    interrupted_started_at = _utc_timestamp()
    interrupted_exit_code = 1
    interrupted_failure = None
    try:
        run_task(
            interrupted_spec["task_path"],
            config_path=interrupted_config,
            output_dir=output_root,
            run_id=interrupted_spec["run_id"],
            inject_interrupt_after=inject_interrupt_after,
        )
        interrupted_failure = "interrupt injection did not fire"
    except InjectedInterruptError:
        interrupted_exit_code = 130
    except RepoHarnessError as exc:
        interrupted_failure = str(exc)
    _append_command_log(
        command_log_path,
        command_entries,
        command_name="run-task",
        argv=[
            "repo-harness",
            "run-task",
            str(interrupted_spec["task_path"]),
            "--config",
            str(interrupted_config),
            "--run-id",
            interrupted_spec["run_id"],
            "--inject-interrupt-after",
            inject_interrupt_after,
        ],
        started_at=interrupted_started_at,
        input_paths=[Path(interrupted_spec["task_path"]), interrupted_config],
        output_paths=[path for path in [interrupted_run_dir] if path.exists()],
        exit_code=interrupted_exit_code,
        structured_failure_reason=interrupted_failure,
    )
    if interrupted_failure:
        raise ConfigError(f"中断注入运行失败：{interrupted_failure}")
    interrupted_checkpoint = _write_checkpoint(
        checkpoint_dir=checkpoint_dir,
        output_root=output_root,
        run_id=interrupted_spec["run_id"],
        run_dir=interrupted_run_dir,
        task_id=interrupted_spec["task_id"],
        status="interrupted",
        checkpoint_type="interrupted",
        resume_eligibility="eligible",
    )
    checkpoints.append(interrupted_checkpoint["checkpoint"])
    checkpoint_records.append(interrupted_checkpoint["record"])

    pending_checkpoint = _write_pending_checkpoint(
        checkpoint_dir=checkpoint_dir,
        output_root=output_root,
        spec=pending_spec,
        config_path=_write_run_config(config_dir, config=config, spec=pending_spec),
    )
    checkpoints.append(pending_checkpoint["checkpoint"])
    checkpoint_records.append(pending_checkpoint["record"])

    _append_command_log(
        command_log_path,
        command_entries,
        command_name="experiment-resume-skip-completed",
        argv=[
            "repo-harness",
            "build-v3-experiment-resume",
            "--skip-completed-run",
            completed_spec["run_id"],
        ],
        started_at=_utc_timestamp(),
        input_paths=[completed_config, completed_run_dir / "run_metadata.json"],
        output_paths=[],
        exit_code=0,
        structured_skip_reason="completed run skipped during resume",
    )

    continuation_spec = {
        **interrupted_spec,
        "run_id": f"{interrupted_spec['run_id']}__resume001",
        "attempt": 2,
        "parent_run_id": interrupted_spec["run_id"],
    }
    continuation_run_dir, _ = _execute_run(
        spec=continuation_spec,
        config=config,
        config_dir=config_dir,
        output_root=output_root,
        command_log_path=command_log_path,
        command_entries=command_entries,
        inject_interrupt_after=None,
    )
    continuation_checkpoint = _write_checkpoint(
        checkpoint_dir=checkpoint_dir,
        output_root=output_root,
        run_id=continuation_spec["run_id"],
        run_dir=continuation_run_dir,
        task_id=continuation_spec["task_id"],
        status="completed",
        checkpoint_type="export_completed",
        resume_eligibility="not_needed",
    )
    checkpoints.append(continuation_checkpoint["checkpoint"])
    checkpoint_records.append(continuation_checkpoint["record"])

    pending_run_dir, _ = _execute_run(
        spec=pending_spec,
        config=config,
        config_dir=config_dir,
        output_root=output_root,
        command_log_path=command_log_path,
        command_entries=command_entries,
        inject_interrupt_after=None,
    )
    pending_completed_checkpoint = _write_checkpoint(
        checkpoint_dir=checkpoint_dir,
        output_root=output_root,
        run_id=pending_spec["run_id"],
        run_dir=pending_run_dir,
        task_id=pending_spec["task_id"],
        status="completed",
        checkpoint_type="export_completed",
        resume_eligibility="not_needed",
    )
    checkpoints.append(pending_completed_checkpoint["checkpoint"])
    checkpoint_records.append(pending_completed_checkpoint["record"])

    lock_diagnostic = _write_lock_diagnostic(output_root)
    interrupted_diagnostics = _write_interrupted_diagnostics(
        output_root=output_root,
        interrupted_run_dir=interrupted_run_dir,
        continuation_run_dir=continuation_run_dir,
        inject_interrupt_after=inject_interrupt_after,
        lock_diagnostic=lock_diagnostic,
    )

    run_entries = [
        ExperimentResumeRunEntry(
            run_id=completed_spec["run_id"],
            task_id=completed_spec["task_id"],
            rollout_index=completed_spec["rollout_index"],
            model_alias=config.model_alias,
            scaffold_id=config.scaffold_id,
            status="completed",
            attempt=1,
            run_dir=_relative_path(completed_run_dir, output_root),
            last_checkpoint_ref=completed_checkpoint["record"]["checkpoint_ref"],
            resume_action="skip_completed",
        ),
        ExperimentResumeRunEntry(
            run_id=interrupted_spec["run_id"],
            task_id=interrupted_spec["task_id"],
            rollout_index=interrupted_spec["rollout_index"],
            model_alias=config.model_alias,
            scaffold_id=config.scaffold_id,
            status="interrupted",
            attempt=1,
            run_dir=_relative_path(interrupted_run_dir, output_root),
            last_checkpoint_ref=interrupted_checkpoint["record"]["checkpoint_ref"],
            failure_category="interrupted",
            failure_type=f"inject_after_{inject_interrupt_after}",
            retryable=True,
            resume_action="continue_interrupted_as_new_run",
        ),
        ExperimentResumeRunEntry(
            run_id=continuation_spec["run_id"],
            task_id=continuation_spec["task_id"],
            rollout_index=continuation_spec["rollout_index"],
            model_alias=config.model_alias,
            scaffold_id=config.scaffold_id,
            status="completed",
            attempt=2,
            run_dir=_relative_path(continuation_run_dir, output_root),
            last_checkpoint_ref=continuation_checkpoint["record"]["checkpoint_ref"],
            resume_action="none",
            parent_run_id=interrupted_spec["run_id"],
            continuation_reason="resume_interrupted_run",
            resume_from=inject_interrupt_after,
        ),
        ExperimentResumeRunEntry(
            run_id=pending_spec["run_id"],
            task_id=pending_spec["task_id"],
            rollout_index=pending_spec["rollout_index"],
            model_alias=config.model_alias,
            scaffold_id=config.scaffold_id,
            status="completed",
            attempt=1,
            run_dir=_relative_path(pending_run_dir, output_root),
            last_checkpoint_ref=pending_completed_checkpoint["record"]["checkpoint_ref"],
            resume_action="continue_pending",
        ),
    ]
    checkpoint_manifest = {
        "schema_version": CHECKPOINT_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "experiment_id": config.experiment_id,
        "checkpoint_count": len(checkpoint_records),
        "checkpoint_refs": [record["checkpoint_ref"] for record in checkpoint_records],
        "checkpoints": [checkpoint.model_dump(mode="json") for checkpoint in checkpoints],
    }
    checkpoint_manifest_path = output_root / "run_checkpoint_manifest.json"
    _write_json(checkpoint_manifest_path, checkpoint_manifest)

    failure_distribution = {
        "schema_version": FAILURE_DISTRIBUTION_VERSION,
        "generated_at": _utc_timestamp(),
        "categories": {
            "provider_transient": 0,
            "docker_infrastructure": 0,
            "environment_setup": 0,
            "deterministic_verifier": 0,
            "task_quality": 0,
            "interrupted": 1,
        },
        "classification_policy": "stage8_resume_runner_explicit_categories_v0",
    }
    failure_distribution_path = output_root / "failure_distribution_report.json"
    _write_json(failure_distribution_path, failure_distribution)

    manifest = ExperimentResumeManifest(
        experiment_id=config.experiment_id,
        config_hash=compute_file_sha256(config_path),
        generated_at=_utc_timestamp(),
        updated_at=_utc_timestamp(),
        max_parallel_runs=1,
        runs=run_entries,
        state_distribution=dict(sorted(Counter(entry.status for entry in run_entries).items())),
        failure_distribution={"interrupted": 1},
        completed_run_refs=[
            _artifact_ref(run_dir, base_dir=output_root, artifact_id=f"{run_id}_run_dir", kind="directory")
            for run_id, run_dir in [
                (completed_spec["run_id"], completed_run_dir),
                (continuation_spec["run_id"], continuation_run_dir),
                (pending_spec["run_id"], pending_run_dir),
            ]
        ],
        pending_run_specs=[
            {
                "run_id": pending_spec["run_id"],
                "task_id": pending_spec["task_id"],
                "rollout_index": pending_spec["rollout_index"],
                "pending_run_config_ref": pending_checkpoint["record"]["pending_run_config_ref"],
            }
        ],
        interrupted_run_refs=[
            _artifact_ref(
                interrupted_run_dir,
                base_dir=output_root,
                artifact_id=f"{interrupted_spec['run_id']}_interrupted_run_dir",
                kind="directory",
            )
        ],
        run_checkpoints=checkpoints,
        completed_run_ids=[
            completed_spec["run_id"],
            continuation_spec["run_id"],
            pending_spec["run_id"],
        ],
        pending_run_ids=[pending_spec["run_id"]],
        interrupted_run_ids=[interrupted_spec["run_id"]],
    )
    manifest_path = output_root / "experiment_resume_manifest.json"
    _write_json(manifest_path, manifest.model_dump(mode="json"))

    report = {
        "schema_version": RESUME_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "experiment_id": config.experiment_id,
        "inject_interrupt_after": inject_interrupt_after,
        "manifest_ref": _artifact_ref(
            manifest_path,
            base_dir=output_root,
            artifact_id="experiment_resume_manifest",
            kind="json",
        ),
        "checkpoint_manifest_ref": _artifact_ref(
            checkpoint_manifest_path,
            base_dir=output_root,
            artifact_id="run_checkpoint_manifest",
            kind="json",
        ),
        "interrupted_run_diagnostics_ref": _artifact_ref(
            interrupted_diagnostics,
            base_dir=output_root,
            artifact_id="interrupted_run_diagnostics",
            kind="json",
        ),
        "failure_distribution_ref": _artifact_ref(
            failure_distribution_path,
            base_dir=output_root,
            artifact_id="failure_distribution_report",
            kind="json",
        ),
        "command_log_ref": _artifact_ref(
            command_log_path,
            base_dir=output_root,
            artifact_id="command_log",
            kind="jsonl",
        ),
        "resume_actions": {
            "skip_completed": completed_spec["run_id"],
            "continue_interrupted_as_new_run": continuation_spec["run_id"],
            "continue_pending": pending_spec["run_id"],
        },
    }
    _write_json(output_root / "experiment_resume_report.json", report)
    return output_root


def inspect_experiment_resume(
    run_dir: str | Path,
    *,
    manifest: str | Path,
    assert_resumable: bool = False,
) -> str:
    root = Path(run_dir)
    manifest_path = Path(manifest)
    failures: list[str] = []
    if not root.exists():
        failures.append(f"experiment resume directory 不存在：{root}")
    payload = _read_json_for_inspect(manifest_path, failures)
    try:
        resume_manifest = ExperimentResumeManifest.model_validate(payload)
    except ValidationError as exc:
        failures.append(f"experiment_resume_manifest schema 无效：{exc}")
        resume_manifest = None

    checkpoint_manifest_path = root / "run_checkpoint_manifest.json"
    interrupted_diagnostics_path = root / "interrupted_run_diagnostics.json"
    command_log_path = root / "command_log.jsonl"
    checkpoint_payload = _read_json_for_inspect(checkpoint_manifest_path, failures)
    interrupted_payload = _read_json_for_inspect(interrupted_diagnostics_path, failures)
    command_entries = _read_command_log(command_log_path, failures)

    if resume_manifest is not None:
        _inspect_resume_manifest(
            root=root,
            manifest=resume_manifest,
            checkpoint_payload=checkpoint_payload,
            failures=failures,
            assert_resumable=assert_resumable,
        )
    _inspect_interrupted_diagnostics(interrupted_payload, failures)
    _inspect_command_log(command_entries, failures)
    _inspect_checkpoint_contamination(
        {
            "experiment_resume_manifest": payload,
            "run_checkpoint_manifest": checkpoint_payload,
            "interrupted_run_diagnostics": interrupted_payload,
        },
        failures,
    )
    lines = [
        f"Experiment resume directory: {root}",
        f"Experiment resume manifest: {manifest_path}",
        f"Checkpoint manifest: {checkpoint_manifest_path}",
        f"Interrupted diagnostics: {interrupted_diagnostics_path}",
        f"Command log entries: {len(command_entries)}",
    ]
    if failures:
        raise ConfigError("; ".join(failures))
    if assert_resumable:
        lines.append("Inspect experiment resume: resumable")
    lines.append("Inspect experiment resume: passed")
    return "\n".join(lines)


def _run_specs(config: Any) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for task_path in config.tasks:
        task_id = _task_id(task_path)
        for rollout_index in range(config.rollout_count):
            specs.append(
                {
                    "task_path": str(task_path),
                    "task_id": task_id,
                    "rollout_index": rollout_index,
                    "run_id": _run_id(config, task_id=task_id, rollout_index=rollout_index),
                    "attempt": 1,
                    "parent_run_id": None,
                }
            )
    return specs


def _execute_run(
    *,
    spec: dict[str, Any],
    config: Any,
    config_dir: Path,
    output_root: Path,
    command_log_path: Path,
    command_entries: list[CommandLogEntry],
    inject_interrupt_after: InjectInterruptPoint | None,
) -> tuple[Path, Path]:
    run_config_path = _write_run_config(config_dir, config=config, spec=spec)
    started_at = _utc_timestamp()
    run_dir = run_task(
        spec["task_path"],
        config_path=run_config_path,
        output_dir=output_root,
        run_id=spec["run_id"],
        inject_interrupt_after=inject_interrupt_after,
    )
    argv = [
        "repo-harness",
        "run-task",
        str(spec["task_path"]),
        "--config",
        str(run_config_path),
        "--run-id",
        spec["run_id"],
    ]
    if inject_interrupt_after is not None:
        argv.extend(["--inject-interrupt-after", inject_interrupt_after])
    _append_command_log(
        command_log_path,
        command_entries,
        command_name="run-task",
        argv=argv,
        started_at=started_at,
        input_paths=[Path(spec["task_path"]), run_config_path],
        output_paths=[run_dir],
        exit_code=0,
    )
    return run_dir, run_config_path


def _write_run_config(config_dir: Path, *, config: Any, spec: dict[str, Any]) -> Path:
    run_config_path = config_dir / f"{spec['run_id']}.yaml"
    if run_config_path.exists():
        return run_config_path
    _write_yaml(run_config_path, _run_config_payload(config, task_path=spec["task_path"]))
    return run_config_path


def _write_checkpoint(
    *,
    checkpoint_dir: Path,
    output_root: Path,
    run_id: str,
    run_dir: Path,
    task_id: str,
    status: Literal["completed", "failed", "interrupted", "crashed"],
    checkpoint_type: Literal["export_completed", "interrupted"],
    resume_eligibility: Literal["eligible", "not_needed", "not_recoverable", "not_evaluated"],
) -> dict[str, Any]:
    checkpoint_id = f"{run_id}_{checkpoint_type}"
    checkpoint = RunCheckpoint(
        checkpoint_id=checkpoint_id,
        checkpoint_type=checkpoint_type,
        created_at=_utc_timestamp(),
        run_id=run_id,
        status=status,
        run_config_facts_ref=_file_ref_if_exists(run_dir / "run_config_facts.json", base_dir=run_dir, artifact_id=f"{run_id}_run_config_facts", kind="json"),
        event_offset=_jsonl_record_count(run_dir / "events.jsonl"),
        transcript_offset=_jsonl_record_count(run_dir / "transcript.jsonl"),
        artifact_manifest_ref=_file_ref_if_exists(run_dir / "artifacts.json", base_dir=run_dir, artifact_id=f"{run_id}_artifacts_manifest", kind="json"),
        run_metadata_ref=(
            _file_ref_if_exists(run_dir / "run_metadata.json", base_dir=run_dir, artifact_id=f"{run_id}_run_metadata", kind="json")
            if status in {"completed", "failed"}
            else None
        ),
        interrupted_or_crash_facts_ref=(
            _file_ref_if_exists(run_dir / "interrupted_run_facts.json", base_dir=run_dir, artifact_id=f"{run_id}_interrupted_facts", kind="json")
            if status in {"interrupted", "crashed"}
            else None
        ),
        resume_eligibility=resume_eligibility,
    )
    path = checkpoint_dir / f"{checkpoint_id}.json"
    _write_json(path, checkpoint.model_dump(mode="json"))
    return {
        "checkpoint": checkpoint,
        "record": {
            "run_id": run_id,
            "task_id": task_id,
            "checkpoint_ref": _artifact_ref(
                path,
                base_dir=output_root,
                artifact_id=checkpoint_id,
                kind="json",
            ),
        },
    }


def _write_pending_checkpoint(
    *,
    checkpoint_dir: Path,
    output_root: Path,
    spec: dict[str, Any],
    config_path: Path,
) -> dict[str, Any]:
    checkpoint_id = f"{spec['run_id']}_pending"
    checkpoint = RunCheckpoint(
        checkpoint_id=checkpoint_id,
        checkpoint_type="created",
        created_at=_utc_timestamp(),
        run_id=spec["run_id"],
        status="pending",
        resume_eligibility="eligible",
    )
    path = checkpoint_dir / f"{checkpoint_id}.json"
    _write_json(path, checkpoint.model_dump(mode="json"))
    return {
        "checkpoint": checkpoint,
        "record": {
            "run_id": spec["run_id"],
            "task_id": spec["task_id"],
            "pending_run_config_ref": _artifact_ref(
                config_path,
                base_dir=output_root,
                artifact_id=f"{spec['run_id']}_pending_run_config",
                kind="yaml",
            ),
            "checkpoint_ref": _artifact_ref(
                path,
                base_dir=output_root,
                artifact_id=checkpoint_id,
                kind="json",
            ),
        },
    }


def _write_interrupted_diagnostics(
    *,
    output_root: Path,
    interrupted_run_dir: Path,
    continuation_run_dir: Path,
    inject_interrupt_after: str,
    lock_diagnostic: Path,
) -> Path:
    transcript = read_jsonl(interrupted_run_dir / "transcript.jsonl")
    events = read_jsonl(interrupted_run_dir / "events.jsonl")
    tool_pairing = _tool_pairing(events)
    payload = {
        "schema_version": INTERRUPTED_DIAGNOSTICS_VERSION,
        "generated_at": _utc_timestamp(),
        "interrupted_run_id": interrupted_run_dir.name,
        "interrupted_after": inject_interrupt_after,
        "continuation_run_id": continuation_run_dir.name,
        "continuation_created_new_run_id": continuation_run_dir.name != interrupted_run_dir.name,
        "original_evidence_preserved": {
            "run_status": _read_json(interrupted_run_dir / "run_status.json").get("status"),
            "transcript_jsonl": (interrupted_run_dir / "transcript.jsonl").exists(),
            "events_jsonl": (interrupted_run_dir / "events.jsonl").exists(),
            "artifacts_json": (interrupted_run_dir / "artifacts.json").exists(),
            "run_config_facts_json": (interrupted_run_dir / "run_config_facts.json").exists(),
            "run_metadata_json": (interrupted_run_dir / "run_metadata.json").exists(),
        },
        "partial_counts": {
            "transcript_records": len(transcript),
            "events": len(events),
        },
        "tool_result_pairing": tool_pairing,
        "artifact_manifest_errors": verify_artifact_manifest(interrupted_run_dir),
        "resume_eligibility": "eligible",
        "lock_diagnostic_ref": _artifact_ref(
            lock_diagnostic,
            base_dir=output_root,
            artifact_id="run_directory_lock_diagnostic",
            kind="json",
        ),
    }
    path = output_root / "interrupted_run_diagnostics.json"
    _write_json(path, payload)
    return path


def _write_lock_diagnostic(output_root: Path) -> Path:
    locked_dir = output_root / "lock_probe_run"
    locked_dir.mkdir()
    with RunRecorder("lock_probe_run", locked_dir, task_id="lock_probe") as recorder:
        locked = False
        message = None
        second_recorder = None
        try:
            second_recorder = RunRecorder("lock_probe_run", locked_dir, task_id="lock_probe")
        except RunRecorderError:
            locked = True
            message = "run directory lock conflict detected"
        finally:
            if second_recorder is not None:
                second_recorder.close()
        recorder.mark_interrupted(
            "# RepoHarness Lock Probe\n\n"
            f"- lock_conflict_detected: {locked}\n"
        )
    path = output_root / "run_directory_lock_diagnostic.json"
    _write_json(
        path,
        {
            "schema_version": LOCK_DIAGNOSTIC_VERSION,
            "generated_at": _utc_timestamp(),
            "run_directory": "lock_probe_run",
            "lock_conflict_detected": locked,
            "failure_type": "run_directory_lock_conflict" if locked else None,
            "message": message,
        },
    )
    return path


def _inspect_resume_manifest(
    *,
    root: Path,
    manifest: ExperimentResumeManifest,
    checkpoint_payload: dict[str, Any],
    failures: list[str],
    assert_resumable: bool,
) -> None:
    checkpoint_refs = checkpoint_payload.get("checkpoint_refs", [])
    if checkpoint_payload.get("checkpoint_count") != len(checkpoint_refs):
        failures.append("run_checkpoint_manifest checkpoint_count 与 checkpoint_refs 数量不一致。")
    for ref_payload in checkpoint_refs:
        checkpoint_path = _resolve_ref(root, ref_payload, failures)
        if checkpoint_path is None:
            continue
        checkpoint_payload_on_disk = _read_json_for_inspect(checkpoint_path, failures)
        try:
            checkpoint = RunCheckpoint.model_validate(checkpoint_payload_on_disk)
        except ValidationError as exc:
            failures.append(f"checkpoint schema 无效：{checkpoint_path}: {exc}")
            continue
        _inspect_checkpoint_refs(root=root, checkpoint=checkpoint, run_id=checkpoint.run_id, failures=failures)
    actions = {entry.resume_action for entry in manifest.runs}
    if assert_resumable:
        required_actions = {
            "skip_completed",
            "continue_interrupted_as_new_run",
            "continue_pending",
        }
        missing_actions = sorted(required_actions.difference(actions))
        if missing_actions:
            failures.append("resume manifest 缺少必需 resume action：" + ", ".join(missing_actions))
        if not manifest.interrupted_run_ids:
            failures.append("resume manifest 必须包含 interrupted run。")
        continuation_entries = [entry for entry in manifest.runs if entry.parent_run_id]
        if not continuation_entries:
            failures.append("resume manifest 必须记录 continuation run。")
        for entry in continuation_entries:
            if entry.run_id == entry.parent_run_id:
                failures.append("continuation run 不能复用 parent run id。")
        if not any(entry.resume_action == "skip_completed" for entry in manifest.runs):
            failures.append("resume 必须跳过 completed run。")
        if not any(entry.resume_action == "continue_pending" for entry in manifest.runs):
            failures.append("resume 必须继续 pending run。")
    for entry in manifest.runs:
        run_path = Path(entry.run_dir)
        if not run_path.is_absolute():
            run_path = root / run_path
        if entry.status == "completed":
            for name in ("transcript.jsonl", "events.jsonl", "artifacts.json", "run_config_facts.json", "run_metadata.json"):
                if not (run_path / name).exists():
                    failures.append(f"completed run 缺少 {name}: {entry.run_id}")
            failures.extend(f"{entry.run_id} artifact manifest: {error}" for error in verify_artifact_manifest(run_path))
        if entry.status == "interrupted" and (run_path / "run_metadata.json").exists():
            failures.append(f"interrupted run 不能包含最终 run_metadata.json：{entry.run_id}")


def _inspect_checkpoint_refs(
    *,
    root: Path,
    checkpoint: RunCheckpoint,
    run_id: str,
    failures: list[str],
) -> None:
    run_path = root / run_id
    for label, ref in [
        ("run_config_facts_ref", checkpoint.run_config_facts_ref),
        ("artifact_manifest_ref", checkpoint.artifact_manifest_ref),
        ("run_metadata_ref", checkpoint.run_metadata_ref),
        ("interrupted_or_crash_facts_ref", checkpoint.interrupted_or_crash_facts_ref),
    ]:
        if ref is None:
            continue
        base = run_path if label != "run_config_facts_ref" or checkpoint.status != "pending" else root
        resolved = _resolve_ref(base, ref.model_dump(mode="json"), failures)
        if resolved is None:
            failures.append(f"{checkpoint.run_id} checkpoint {label} 不可解析。")
    if checkpoint.run_metadata_ref is not None and checkpoint.status not in {"completed", "failed"}:
        failures.append(f"{checkpoint.run_id} checkpoint 在 final metadata 前引用 run_metadata_ref。")
    if checkpoint.status == "interrupted" and checkpoint.run_metadata_ref is not None:
        failures.append(f"{checkpoint.run_id} interrupted checkpoint 不能引用 run_metadata_ref。")


def _inspect_interrupted_diagnostics(payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("schema_version") != INTERRUPTED_DIAGNOSTICS_VERSION:
        failures.append("interrupted_run_diagnostics schema_version 无效。")
    preserved = payload.get("original_evidence_preserved", {})
    for name in ("transcript_jsonl", "events_jsonl", "artifacts_json", "run_config_facts_json"):
        if preserved.get(name) is not True:
            failures.append(f"interrupted run 未保留必需 evidence：{name}")
    if preserved.get("run_metadata_json") is True:
        failures.append("interrupted run 不应要求或写入最终 run_metadata.json。")
    if payload.get("continuation_created_new_run_id") is not True:
        failures.append("continuation run 必须使用新的 run id。")
    pairing = payload.get("tool_result_pairing", {})
    if pairing.get("missing_terminal_tool_call_ids"):
        failures.append("interrupted run 存在未配对 tool call。")
    lock_ref = payload.get("lock_diagnostic_ref")
    if not isinstance(lock_ref, dict):
        failures.append("interrupted diagnostics 缺少 lock_diagnostic_ref。")


def _inspect_command_log(entries: list[CommandLogEntry], failures: list[str]) -> None:
    if not entries:
        failures.append("command_log.jsonl 缺少 CommandLogEntry。")
    command_names = {entry.command_name for entry in entries}
    if "run-task" not in command_names:
        failures.append("command log 必须记录 run-task 命令。")
    if "experiment-resume-skip-completed" not in command_names:
        failures.append("command log 必须记录 completed run skip。")
    if not any("--inject-interrupt-after" in entry.argv for entry in entries):
        failures.append("command log 必须记录中断注入 argv。")


def _inspect_checkpoint_contamination(payload: dict[str, Any], failures: list[str]) -> None:
    result = V3ContaminationDenylist().scan_payload(surface="checkpoint", payload=payload)
    if not result.clean:
        terms = ", ".join(sorted({finding.matched_term for finding in result.findings}))
        failures.append(f"checkpoint contamination scan failed: {terms}")


def _read_command_log(path: Path, failures: list[str]) -> list[CommandLogEntry]:
    if not path.exists():
        failures.append("command_log.jsonl 不存在。")
        return []
    entries: list[CommandLogEntry] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entries.append(CommandLogEntry.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError) as exc:
            failures.append(f"command_log.jsonl 第 {line_number} 行无效：{exc}")
    return entries


def _append_command_log(
    path: Path,
    entries: list[CommandLogEntry],
    *,
    command_name: str,
    argv: list[str],
    started_at: str,
    input_paths: list[Path],
    output_paths: list[Path],
    exit_code: int | None,
    structured_skip_reason: str | None = None,
    structured_failure_reason: str | None = None,
) -> None:
    entry = CommandLogEntry(
        command_name=command_name,
        argv=argv,
        cwd=Path.cwd().as_posix(),
        input_refs=[
            _artifact_ref(path, base_dir=Path.cwd(), artifact_id=f"{command_name}_input_{index}", kind=_kind_for_path(path))
            for index, path in enumerate(input_paths, start=1)
            if path.exists()
        ],
        output_refs=[
            _artifact_ref(path, base_dir=Path.cwd(), artifact_id=f"{command_name}_output_{index}", kind=_kind_for_path(path))
            for index, path in enumerate(output_paths, start=1)
            if path.exists()
        ],
        exit_code=exit_code,
        tool_or_cli_version=f"repo-harness {__version__}",
        started_at=started_at,
        finished_at=_utc_timestamp(),
        structured_skip_reason=structured_skip_reason,
        structured_failure_reason=structured_failure_reason,
    )
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n")
    entries.append(entry)


def _tool_pairing(events: list[dict[str, Any]]) -> dict[str, Any]:
    requested = [
        event.get("data", {}).get("tool_call_id")
        for event in events
        if event.get("event_type") == "tool_requested"
    ]
    terminal = {
        event.get("data", {}).get("tool_call_id")
        for event in events
        if event.get("event_type") in {"tool_completed", "tool_denied", "tool_failed", "tool_timeout", "tool_interrupted"}
    }
    missing = sorted(str(call_id) for call_id in requested if call_id and call_id not in terminal)
    return {
        "requested_tool_call_count": len([call_id for call_id in requested if call_id]),
        "terminal_tool_result_count": len([call_id for call_id in terminal if call_id]),
        "missing_terminal_tool_call_ids": missing,
    }


def _file_ref_if_exists(path: Path, *, base_dir: Path, artifact_id: str, kind: str) -> ArtifactRef | None:
    if not path.exists():
        return None
    return ArtifactRef.model_validate(
        _artifact_ref(path, base_dir=base_dir, artifact_id=artifact_id, kind=kind)
    )


def _artifact_ref(
    path: Path,
    *,
    base_dir: Path,
    artifact_id: str,
    kind: str,
    redaction_status: str = "not_required",
) -> dict[str, Any]:
    if path.is_dir():
        digest = compute_source_tree_hash(path)
        size_bytes = 0
    else:
        digest = compute_file_sha256(path)
        size_bytes = path.stat().st_size
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=_relative_path(path, base_dir),
        kind=kind,
        sha256=digest,
        size_bytes=size_bytes,
        redaction_status=redaction_status,
        retention_policy="keep",
    ).model_dump(mode="json")


def _resolve_ref(base_dir: Path, ref_payload: dict[str, Any], failures: list[str]) -> Path | None:
    try:
        ref = ArtifactRef.model_validate(ref_payload)
    except ValidationError as exc:
        failures.append(f"ArtifactRef schema 无效：{exc}")
        return None
    relative = Path(ref.relative_path)
    path = relative if relative.is_absolute() else base_dir / relative
    if not path.exists():
        failures.append(f"ArtifactRef 路径不存在：{ref.relative_path}")
        return None
    if path.is_dir():
        actual_sha = compute_source_tree_hash(path)
    else:
        actual_sha = compute_file_sha256(path)
    if actual_sha != ref.sha256:
        failures.append(f"ArtifactRef sha256 不匹配：{ref.relative_path}")
    if not path.is_dir() and path.stat().st_size != ref.size_bytes:
        failures.append(f"ArtifactRef size_bytes 不匹配：{ref.relative_path}")
    return path


def _relative_path(path: Path, base_dir: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _kind_for_path(path: Path) -> str:
    if path.is_dir():
        return "directory"
    suffix = path.suffix.lower().lstrip(".")
    return suffix or "file"


def _jsonl_record_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


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


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
