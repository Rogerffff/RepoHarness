"""Stage 15.2 partial-rollout remote smoke acceptance inspection helpers."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import tarfile
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import Field

from repo_harness.errors import RepoHarnessError
from repo_harness.schema_base import StrictBaseModel


STAGE15_CANONICAL_EVIDENCE_ITEMS: tuple[str, ...] = (
    "stage15_acceptance_summary.json",
    "stage15_partial_checkpoint_report.json",
    "stage15_resume_scheduler_report.json",
    "stage15_policy_loss_gate_report.json",
    "stage15_trainer_steps_report.json",
    "stage15_parameter_sync_report.json",
    "stage15_staleness_report.json",
    "stage15_message_queue_report.json",
    "stage15_side_channel_report.json",
    "stage15_visibility_report.json",
    "stage15_batch_provenance_report.json",
    "stage15_remote_patch_manifest.json",
    "stage15_resource_lifecycle_report.json",
    "stage15_path_leak_scan_report.json",
    "stage15_command_log.sanitized.jsonl",
    "stage15_training_profile.json",
    "stage15_hydra_overrides.json",
    "stage15_environment_matrix.json",
    "stage15_fixture_manifest.json",
    "stage15_fixture_sha256_report.json",
    "stage15_canonical_evidence_map.json",
    "runtime_private/stage15_command_log.raw.jsonl",
)

PUBLIC_SCAN_SUFFIXES: tuple[str, ...] = (
    ".json",
    ".jsonl",
    ".log",
    ".py",
    ".yaml",
    ".yml",
    ".sh",
    ".txt",
    ".parquet",
)

PATH_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/Users/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/workspace/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/private/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/home/[A-Za-z0-9_.\-/]+"),
    re.compile(r"\.repo_harness_env_overlay"),
    re.compile(r"\.repo_harness_runtime"),
    re.compile(r"VASTAI_API_KEY"),
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"hf_[A-Za-z0-9_\-]{12,}"),
    re.compile(r"BEGIN (?:RSA |OPENSSH |EC |)PRIVATE KEY"),
    re.compile(r"hidden_verifier", re.IGNORECASE),
    re.compile(r"gold_patch", re.IGNORECASE),
    re.compile(r"provider_secret", re.IGNORECASE),
)

REMOTE_PATCH_REQUIRED_FIELDS: tuple[str, ...] = (
    "path",
    "sha256",
    "purpose",
    "enabled_by",
    "rollback_method",
    "public_or_runtime_private",
)

BAD_POLICY_LOSS_COUNT_FIELDS: tuple[str, ...] = (
    "partial_policy_loss_consumed_sample_count",
    "pending_reward_policy_loss_consumed_sample_count",
    "stale_policy_loss_consumed_sample_count",
    "diagnostic_policy_loss_consumed_sample_count",
    "visibility_rejected_policy_loss_consumed_sample_count",
    "missing_logprob_policy_loss_consumed_sample_count",
    "non_verl_route_policy_loss_consumed_sample_count",
    "timeout_policy_loss_consumed_sample_count",
    "cancelled_policy_loss_consumed_sample_count",
    "resume_timeout_policy_loss_consumed_sample_count",
    "policy_loss_queue_invalid_sample_count",
)


class Stage15PartialRolloutAcceptanceInspectReport(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage15_partial_rollout_acceptance_inspect_report_v0"
    evidence_root: str
    assert_complete: bool = False
    summary_path: str | None = None
    summary_loaded: bool = False
    canonical_items_checked: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    passed: bool = False


class _EvidenceView:
    def __init__(self, root: Path) -> None:
        self.root = root

    def exists(self, relative_path: str) -> bool:
        return self.path(relative_path).is_file()

    def path(self, relative_path: str) -> Path:
        return self.root / _normalize_relative_path(relative_path)

    def read_bytes(self, relative_path: str) -> bytes:
        return self.path(relative_path).read_bytes()

    def read_text(self, relative_path: str) -> str:
        return self.read_bytes(relative_path).decode("utf-8")

    def iter_public_files(self) -> Iterable[tuple[str, Path]]:
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(self.root).as_posix()
            if relative.startswith("runtime_private/"):
                continue
            if path.suffix in PUBLIC_SCAN_SUFFIXES:
                yield relative, path


class _PreparedEvidenceView:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.view: _EvidenceView | None = None

    def __enter__(self) -> _EvidenceView:
        if self.path.is_dir():
            self.view = _EvidenceView(self.path)
            return self.view
        failures = validate_stage15_evidence_tarball(self.path)
        if failures:
            raise RepoHarnessError("Stage 15 evidence tarball 安全检查失败：" + "; ".join(failures))
        self._temp_dir = tempfile.TemporaryDirectory(prefix="repo_harness_stage15_evidence_")
        root = Path(self._temp_dir.name)
        with tarfile.open(self.path, "r:*") as tar:
            tar.extractall(root, filter="data")
        self.view = _EvidenceView(root)
        return self.view

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()


def inspect_stage15_partial_rollout_acceptance(
    evidence_path: str | Path,
    *,
    assert_complete: bool = False,
) -> str:
    """检查 Stage 15.2 partial rollout 远端 smoke evidence 是否满足验收条件。"""

    report = inspect_stage15_partial_rollout_acceptance_report(
        evidence_path,
        assert_complete=assert_complete,
    )
    if assert_complete and report.failures:
        raise RepoHarnessError("; ".join(report.failures))
    return report.model_dump_json(indent=2)


def inspect_stage15_partial_rollout_acceptance_report(
    evidence_path: str | Path,
    *,
    assert_complete: bool = False,
) -> Stage15PartialRolloutAcceptanceInspectReport:
    target = Path(evidence_path)
    with _PreparedEvidenceView(target) as view:
        failures: list[str] = []
        warnings: list[str] = []
        summary_path = "stage15_acceptance_summary.json"
        summary: dict[str, Any] = {}
        if not view.exists(summary_path):
            failures.append("missing_stage15_acceptance_summary")
        else:
            try:
                summary = _load_json(view, summary_path)
            except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError) as exc:
                failures.append(f"invalid_stage15_acceptance_summary_json:{exc}")

        canonical_items = STAGE15_CANONICAL_EVIDENCE_ITEMS
        failures.extend(_validate_canonical_evidence(view, summary, canonical_items))
        failures.extend(_validate_summary(summary))
        failures.extend(_validate_profile_hydra_environment(view, summary))
        failures.extend(_validate_partial_checkpoint_report(view, summary))
        failures.extend(_validate_resume_scheduler_report(view, summary))
        failures.extend(_validate_policy_loss_gate_report(view, summary))
        failures.extend(_validate_trainer_steps_report(view, summary))
        failures.extend(_validate_parameter_sync_report(view, summary))
        failures.extend(_validate_message_queue_report(view, summary))
        failures.extend(_validate_side_channel_report(view, summary))
        failures.extend(_validate_staleness_report(view, summary))
        failures.extend(_validate_batch_provenance_report(view, summary))
        failures.extend(_validate_remote_patch_manifest(view, summary))
        failures.extend(_validate_resource_lifecycle_report(view, summary))
        failures.extend(_validate_sha256_refs(view, summary))
        failures.extend(_scan_public_evidence_for_leaks(view))
        if assert_complete:
            failures.extend(_assert_complete_failures(summary))

        return Stage15PartialRolloutAcceptanceInspectReport(
            evidence_root=target.as_posix(),
            assert_complete=assert_complete,
            summary_path=summary_path if summary else None,
            summary_loaded=bool(summary),
            canonical_items_checked=list(canonical_items),
            failures=failures,
            warnings=warnings,
            passed=not failures,
        )


def validate_stage15_evidence_tarball(
    tarball_path: str | Path,
    *,
    max_single_file_bytes: int = 64 * 1024 * 1024,
    max_total_bytes: int = 512 * 1024 * 1024,
) -> list[str]:
    """只读检查 Stage 15 evidence tarball 是否可安全展开。"""

    failures: list[str] = []
    seen: set[str] = set()
    total_size = 0
    with tarfile.open(tarball_path, "r:*") as tar:
        for member in tar.getmembers():
            normalized = _normalize_tar_member_name(member.name, failures)
            if normalized is None:
                continue
            if normalized in seen:
                failures.append(f"duplicate_tar_entry_after_normalize:{normalized}")
            seen.add(normalized)
            if member.issym() or member.islnk():
                failures.append(f"tar_link_entry_not_allowed:{member.name}")
            if member.isdev() or member.isfifo():
                failures.append(f"tar_special_entry_not_allowed:{member.name}")
            if not (member.isdir() or member.isfile()):
                failures.append(f"tar_unknown_entry_type_not_allowed:{member.name}")
            if member.isfile():
                total_size += member.size
                if member.size > max_single_file_bytes:
                    failures.append(f"tar_file_too_large:{member.name}")
                if total_size > max_total_bytes:
                    failures.append("tar_total_size_too_large")
                    break
    return failures


def _validate_canonical_evidence(
    view: _EvidenceView,
    summary: Mapping[str, Any],
    canonical_items: Iterable[str],
) -> list[str]:
    failures: list[str] = []
    map_payload: Mapping[str, Any] | None = None
    if view.exists("stage15_canonical_evidence_map.json"):
        try:
            raw = _load_json(view, "stage15_canonical_evidence_map.json")
            items = raw.get("items")
            if isinstance(items, Mapping):
                map_payload = items
            else:
                map_payload = raw
        except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError) as exc:
            failures.append(f"invalid_stage15_canonical_evidence_map_json:{exc}")
    summary_map = summary.get("canonical_evidence_map") if isinstance(summary, Mapping) else None
    if isinstance(summary_map, Mapping):
        map_payload = summary_map
    if not isinstance(map_payload, Mapping):
        return failures + ["missing_or_invalid_stage15_canonical_evidence_map"]
    for item in canonical_items:
        mapped = map_payload.get(item)
        if not isinstance(mapped, str) or not mapped:
            failures.append(f"canonical_evidence_map_missing:{item}")
            continue
        try:
            normalized = _normalize_relative_path(mapped)
        except RepoHarnessError as exc:
            failures.append(f"canonical_evidence_map_invalid_path:{item}:{exc}")
            continue
        if item != "runtime_private/stage15_command_log.raw.jsonl" and normalized.startswith("runtime_private/"):
            failures.append(f"canonical_public_item_points_to_runtime_private:{item}")
        if not view.exists(normalized):
            failures.append(f"canonical_evidence_file_missing:{item}->{normalized}")
    return failures


def _validate_summary(summary: Mapping[str, Any]) -> list[str]:
    if not summary:
        return []
    failures: list[str] = []
    required_fields = [
        "acceptance_passed",
        "training_profile_name",
        "partial_rollout_enabled",
        "native_partial_rollout_enabled",
        "native_abort_resume_observed",
        "native_abort_signal_visible_to_repo_harness",
        "controlled_turn_boundary_trigger_used",
        "repo_harness_checkpoint_generated_by_controlled_trigger",
        "partial_checkpoint_count",
        "resume_attempt_count",
        "resumed_terminal_episode_count",
        "resumed_valid_sample_count",
        "resumed_policy_loss_consumed_sample_count",
        "resumed_policy_loss_consumed_unique_checkpoint_count",
        "resumed_policy_loss_consumed_unique_resume_attempt_count",
        "completed_trainer_step_count",
        "parameter_sync_count",
        "initial_parameter_sync_count",
        "post_train_parameter_sync_count",
        "post_train_parameter_sync_after_step",
        "current_param_version",
        "post_sync_resumed_valid_sample_count",
        "message_queue_produced_sample_count",
        "message_queue_consumed_sample_count",
        "message_queue_dropped_sample_count",
        "side_channel_sample_count",
        "policy_loss_queue_invalid_sample_count",
        "trainer_batch_logprob_provenance_passed",
        "visibility_scan_passed",
        "path_leak_scan_passed",
        "resource_cleanup_passed",
        "instance_final_status",
        "training_profile_sha256",
        "hydra_overrides_sha256",
        "fixture_manifest_sha256",
        "public_path_leak_scan_passed",
        "runtime_private_evidence_present",
        "remote_patch_manifest_sha256",
        "evidence_tarball_sha256",
        *BAD_POLICY_LOSS_COUNT_FIELDS,
    ]
    for field in required_fields:
        if field not in summary:
            failures.append(f"acceptance_summary_missing_field:{field}")
    if summary.get("acceptance_passed") is not True:
        failures.append("acceptance_passed_not_true")
    for field in [
        "partial_rollout_enabled",
        "native_partial_rollout_enabled",
        "controlled_turn_boundary_trigger_used",
        "repo_harness_checkpoint_generated_by_controlled_trigger",
        "trainer_batch_logprob_provenance_passed",
        "visibility_scan_passed",
        "path_leak_scan_passed",
        "resource_cleanup_passed",
        "public_path_leak_scan_passed",
        "runtime_private_evidence_present",
    ]:
        if summary.get(field) is not True:
            failures.append(f"{field}_not_true")
    if _int_field(summary, "partial_checkpoint_count", failures) < 2:
        failures.append("partial_checkpoint_count_below_stage15_minimum")
    if _int_field(summary, "resumed_terminal_episode_count", failures) < 2:
        failures.append("resumed_terminal_episode_count_below_stage15_minimum")
    if _int_field(summary, "resumed_policy_loss_consumed_sample_count", failures) < 2:
        failures.append("resumed_policy_loss_consumed_sample_count_below_stage15_minimum")
    if _int_field(summary, "resumed_policy_loss_consumed_unique_checkpoint_count", failures) < 2:
        failures.append("resumed_policy_loss_consumed_unique_checkpoint_count_below_stage15_minimum")
    if _int_field(summary, "resumed_policy_loss_consumed_unique_resume_attempt_count", failures) < 2:
        failures.append("resumed_policy_loss_consumed_unique_resume_attempt_count_below_stage15_minimum")
    if _int_field(summary, "completed_trainer_step_count", failures) < 3:
        failures.append("completed_trainer_step_count_below_stage15_minimum")
    if _int_field(summary, "post_train_parameter_sync_count", failures) < 1:
        failures.append("post_train_parameter_sync_count_below_stage15_minimum")
    if _int_field(summary, "post_sync_resumed_valid_sample_count", failures) < 1:
        failures.append("post_sync_resumed_valid_sample_count_below_stage15_minimum")
    if _int_field(summary, "message_queue_dropped_sample_count", failures) != 0:
        failures.append("message_queue_dropped_sample_count_not_zero")
    for field in BAD_POLICY_LOSS_COUNT_FIELDS:
        if _int_field(summary, field, failures) != 0:
            failures.append(f"{field}_not_zero")
    if summary.get("instance_final_status") not in {"stopped", "paused", "exited"}:
        failures.append("instance_final_status_not_stopped_paused_or_exited")
    return failures


def _validate_profile_hydra_environment(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    profile = _load_optional_json(view, "stage15_training_profile.json", failures)
    environment = _load_optional_json(view, "stage15_environment_matrix.json", failures)
    hydra_payload: Any = None
    if view.exists("stage15_hydra_overrides.json"):
        try:
            hydra_payload = json.loads(view.read_text("stage15_hydra_overrides.json"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            failures.append(f"invalid_stage15_hydra_overrides_json:{exc}")
    else:
        failures.append("missing_stage15_hydra_overrides")
    overrides = _override_set(hydra_payload)
    profile_name = profile.get("profile_name") if isinstance(profile, Mapping) else None
    if summary.get("training_profile_name") != profile_name:
        failures.append("summary_profile_mismatch:training_profile_name")
    for field in [
        "model_id",
        "inference_backend",
        "training_strategy",
        "weight_sync_strategy",
    ]:
        if isinstance(profile, Mapping) and field in summary and field in profile and summary.get(field) != profile.get(field):
            failures.append(f"summary_profile_mismatch:{field}")
    if isinstance(environment, Mapping):
        if environment.get("checkpoint_engine_backend") not in {"nixl", "nixl_cuda"}:
            failures.append("stage15_environment_matrix_checkpoint_engine_not_nixl")
        if environment.get("rollout_backend") not in {"sglang", "SGLang"}:
            failures.append("stage15_environment_matrix_rollout_backend_not_sglang")
    required_overrides = {
        "actor_rollout_ref.hybrid_engine=False",
        "actor_rollout_ref.rollout.mode=async",
        "actor_rollout_ref.rollout.multi_turn.enable=True",
        "actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness",
        "actor_rollout_ref.rollout.calculate_log_probs=True",
        "actor_rollout_ref.actor.use_rollout_log_probs=True",
        "actor_rollout_ref.rollout.checkpoint_engine.backend=nixl",
        "async_training.partial_rollout=True",
        "async_training.require_batches=1",
        "critic.enable=False",
        "reward.reward_model.enable=False",
        "algorithm.rollout_correction.bypass_mode=True",
        "trainer.n_gpus_per_node=1",
        "rollout.n_gpus_per_node=1",
    }
    for override in required_overrides:
        if override not in overrides:
            failures.append(f"stage15_hydra_overrides_missing:{override}")
    if not any(item.startswith("actor_rollout_ref.rollout.agent.agent_loop_config_path=") for item in overrides):
        failures.append("stage15_hydra_overrides_missing_agent_loop_config_path")
    return failures


def _validate_partial_checkpoint_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    report = _load_optional_json(view, "stage15_partial_checkpoint_report.json", [])
    if not report:
        return ["missing_or_invalid_stage15_partial_checkpoint_report"]
    failures: list[str] = []
    for field in [
        "partial_rollout_enabled",
        "native_partial_rollout_enabled",
        "native_abort_resume_observed",
        "native_abort_signal_visible_to_repo_harness",
        "controlled_turn_boundary_trigger_used",
        "repo_harness_checkpoint_generated_by_controlled_trigger",
    ]:
        if report.get(field) != summary.get(field):
            failures.append(f"partial_checkpoint_report_summary_mismatch:{field}")
    if _int_field(report, "partial_checkpoint_count", failures) != _int_field(summary, "partial_checkpoint_count", failures):
        failures.append("partial_checkpoint_report_count_mismatch")
    if _int_field(report, "policy_loss_consumed_partial_count", failures) != _int_field(
        summary, "partial_policy_loss_consumed_sample_count", failures
    ):
        failures.append("partial_checkpoint_report_policy_loss_consumed_count_mismatch")
    checkpoints = report.get("checkpoints")
    if not isinstance(checkpoints, list) or len(checkpoints) < 2:
        failures.append("partial_checkpoint_report_checkpoints_below_minimum")
    else:
        seen: set[str] = set()
        for index, checkpoint in enumerate(checkpoints):
            if not isinstance(checkpoint, Mapping):
                failures.append(f"partial_checkpoint_report_checkpoints[{index}]_not_object")
                continue
            for field in [
                "checkpoint_id",
                "content_digest",
                "trajectory_digest",
                "generation_record_digest",
                "visibility_scan_digest",
                "policy_loss_consumed",
            ]:
                if field not in checkpoint:
                    failures.append(f"partial_checkpoint_report_checkpoints[{index}]_missing_{field}")
            checkpoint_id = str(checkpoint.get("checkpoint_id") or "")
            if checkpoint_id in seen:
                failures.append(f"partial_checkpoint_report_duplicate_checkpoint_id:{checkpoint_id}")
            seen.add(checkpoint_id)
            if checkpoint.get("policy_loss_consumed") is not False:
                failures.append(f"partial_checkpoint_consumed_by_policy_loss:{checkpoint_id or index}")
    return failures


def _validate_resume_scheduler_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    report = _load_optional_json(view, "stage15_resume_scheduler_report.json", [])
    if not report:
        return ["missing_or_invalid_stage15_resume_scheduler_report"]
    failures: list[str] = []
    for field in [
        "resume_attempt_count",
        "resumed_terminal_episode_count",
        "resumed_valid_sample_count",
        "resumed_policy_loss_consumed_sample_count",
    ]:
        if _int_field(report, field, failures) != _int_field(summary, field, failures):
            failures.append(f"resume_scheduler_report_summary_mismatch:{field}")
    attempts = report.get("resume_attempts")
    if not isinstance(attempts, list) or len(attempts) < 2:
        failures.append("resume_scheduler_report_attempts_below_minimum")
    else:
        terminal_count = 0
        for index, attempt in enumerate(attempts):
            if not isinstance(attempt, Mapping):
                failures.append(f"resume_scheduler_report_attempts[{index}]_not_object")
                continue
            for field in ["resume_attempt_id", "source_partial_checkpoint_id", "terminal_status", "policy_loss_consumed"]:
                if field not in attempt:
                    failures.append(f"resume_scheduler_report_attempts[{index}]_missing_{field}")
            if attempt.get("terminal_status") in {"succeeded", "failed"}:
                terminal_count += 1
        if terminal_count < 2:
            failures.append("resume_scheduler_report_terminal_attempts_below_minimum")
    return failures


def _validate_policy_loss_gate_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    report = _load_optional_json(view, "stage15_policy_loss_gate_report.json", [])
    if not report:
        return ["missing_or_invalid_stage15_policy_loss_gate_report"]
    failures: list[str] = []
    for field in [
        "accepted_for_policy_loss_count",
        "consumed_sample_count",
        "invalid_consumed_sample_count",
        "partial_consumed_sample_count",
        "pending_reward_consumed_sample_count",
        "stale_consumed_sample_count",
        "diagnostic_consumed_sample_count",
    ]:
        if field not in report:
            failures.append(f"policy_loss_gate_report_missing_field:{field}")
    if _int_field(report, "invalid_consumed_sample_count", failures) != 0:
        failures.append("policy_loss_gate_invalid_consumed_not_zero")
    if _int_field(report, "partial_consumed_sample_count", failures) != 0:
        failures.append("policy_loss_gate_partial_consumed_not_zero")
    if _int_field(report, "pending_reward_consumed_sample_count", failures) != 0:
        failures.append("policy_loss_gate_pending_reward_consumed_not_zero")
    if _int_field(report, "stale_consumed_sample_count", failures) != 0:
        failures.append("policy_loss_gate_stale_consumed_not_zero")
    if _int_field(report, "diagnostic_consumed_sample_count", failures) != 0:
        failures.append("policy_loss_gate_diagnostic_consumed_not_zero")
    ledger = report.get("sample_ledger")
    if not isinstance(ledger, list) or not ledger:
        return failures + ["policy_loss_gate_sample_ledger_missing"]
    consumed = [row for row in ledger if isinstance(row, Mapping) and row.get("consumed_by_policy_loss") is True]
    if len(consumed) != _int_field(summary, "message_queue_consumed_sample_count", failures):
        failures.append("policy_loss_gate_consumed_count_mismatch_summary")
    sample_ids = [str(row.get("policy_loss_consumed_sample_id") or row.get("sample_id")) for row in consumed]
    if len(sample_ids) != len(set(sample_ids)):
        failures.append("policy_loss_gate_duplicate_consumed_sample_id")
    checkpoint_ids = {str(row.get("source_partial_checkpoint_id")) for row in consumed if row.get("source_partial_checkpoint_id")}
    resume_attempt_ids = {str(row.get("resume_attempt_id")) for row in consumed if row.get("resume_attempt_id")}
    if len(checkpoint_ids) != _int_field(summary, "resumed_policy_loss_consumed_unique_checkpoint_count", failures):
        failures.append("policy_loss_gate_unique_checkpoint_count_mismatch")
    if len(resume_attempt_ids) != _int_field(summary, "resumed_policy_loss_consumed_unique_resume_attempt_count", failures):
        failures.append("policy_loss_gate_unique_resume_attempt_count_mismatch")
    for index, row in enumerate(consumed):
        for field in [
            "route",
            "reward_state",
            "partial_rollout_status",
            "source_partial_checkpoint_id",
            "resume_attempt_id",
            "trainer_step",
            "global_step",
            "parameter_version",
            "min_global_steps",
            "max_global_steps",
            "response_ids_digest",
            "response_mask_digest",
            "rollout_log_probs_digest",
        ]:
            if field not in row or row.get(field) in {None, ""}:
                failures.append(f"policy_loss_gate_consumed[{index}]_missing_{field}")
        if row.get("route") != "verl":
            failures.append(f"policy_loss_gate_consumed_non_verl_route:{sample_ids[index]}")
        if row.get("reward_state") != "final":
            failures.append(f"policy_loss_gate_consumed_reward_not_final:{sample_ids[index]}")
        if row.get("partial_rollout_status") not in {"complete", "not_requested"}:
            failures.append(f"policy_loss_gate_consumed_partial_not_complete:{sample_ids[index]}")
    return failures


def _validate_trainer_steps_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    report = _load_optional_json(view, "stage15_trainer_steps_report.json", [])
    if not report:
        return ["missing_or_invalid_stage15_trainer_steps_report"]
    failures: list[str] = []
    if _int_field(report, "completed_trainer_step_count", failures) != _int_field(
        summary, "completed_trainer_step_count", failures
    ):
        failures.append("trainer_steps_completed_count_mismatch")
    steps = report.get("steps")
    if not isinstance(steps, list) or len(steps) < _int_field(summary, "completed_trainer_step_count", failures):
        failures.append("trainer_steps_report_steps_below_completed_count")
    required_samples = _int_field(summary, "required_samples", failures) if "required_samples" in summary else 1
    for index, step in enumerate(steps if isinstance(steps, list) else []):
        if not isinstance(step, Mapping):
            failures.append(f"trainer_steps_report_steps[{index}]_not_object")
            continue
        if _int_field(step, "consumed_valid_sample_count", failures) < required_samples:
            failures.append(f"trainer_steps_report_step_below_required_samples:{index}")
    return failures


def _validate_parameter_sync_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    report = _load_optional_json(view, "stage15_parameter_sync_report.json", [])
    if not report:
        return ["missing_or_invalid_stage15_parameter_sync_report"]
    failures: list[str] = []
    for field in [
        "initial_parameter_sync_count",
        "post_train_parameter_sync_count",
        "current_param_version",
        "post_sync_resumed_valid_sample_count",
    ]:
        if _int_field(report, field, failures) != _int_field(summary, field, failures):
            failures.append(f"parameter_sync_report_summary_mismatch:{field}")
    if _int_field(report, "post_train_parameter_sync_count", failures) < 1:
        failures.append("parameter_sync_report_post_train_sync_below_minimum")
    return failures


def _validate_message_queue_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    report = _load_optional_json(view, "stage15_message_queue_report.json", [])
    if not report:
        return ["missing_or_invalid_stage15_message_queue_report"]
    failures: list[str] = []
    for field in [
        "message_queue_produced_sample_count",
        "message_queue_consumed_sample_count",
        "message_queue_dropped_sample_count",
    ]:
        if _int_field(report, field, failures) != _int_field(summary, field, failures):
            failures.append(f"message_queue_report_summary_mismatch:{field}")
    if _int_field(report, "message_queue_dropped_sample_count", failures) != 0:
        failures.append("message_queue_report_dropped_count_not_zero")
    return failures


def _validate_side_channel_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    report = _load_optional_json(view, "stage15_side_channel_report.json", [])
    if not report:
        return ["missing_or_invalid_stage15_side_channel_report"]
    failures: list[str] = []
    if _int_field(report, "side_channel_sample_count", failures) != _int_field(summary, "side_channel_sample_count", failures):
        failures.append("side_channel_report_summary_count_mismatch")
    samples = report.get("samples")
    if not isinstance(samples, list):
        return failures + ["side_channel_report_samples_missing"]
    for index, sample in enumerate(samples):
        if not isinstance(sample, Mapping):
            failures.append(f"side_channel_report_samples[{index}]_not_object")
            continue
        if sample.get("policy_loss_consumed") is not False:
            failures.append(f"side_channel_sample_consumed_by_policy_loss:{sample.get('sample_id', index)}")
    return failures


def _validate_staleness_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    report = _load_optional_json(view, "stage15_staleness_report.json", [])
    if not report:
        return ["missing_or_invalid_stage15_staleness_report"]
    failures: list[str] = []
    if _int_field(report, "stale_policy_loss_consumed_sample_count", failures) != _int_field(
        summary, "stale_policy_loss_consumed_sample_count", failures
    ):
        failures.append("staleness_report_consumed_count_mismatch")
    return failures


def _validate_batch_provenance_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    report = _load_optional_json(view, "stage15_batch_provenance_report.json", [])
    if not report:
        return ["missing_or_invalid_stage15_batch_provenance_report"]
    failures: list[str] = []
    if report.get("trainer_batch_logprob_provenance_passed") is not True:
        failures.append("batch_provenance_passed_not_true")
    for field in [
        "response_ids_digest",
        "response_mask_digest",
        "rollout_log_probs_digest",
        "response_ids_shape",
        "response_mask_shape",
        "rollout_log_probs_shape",
    ]:
        value = report.get(field)
        if field not in report or value is None or value == "" or value == []:
            failures.append(f"batch_provenance_report_missing_{field}")
    return failures


def _validate_remote_patch_manifest(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    report = _load_optional_json(view, "stage15_remote_patch_manifest.json", [])
    if not report:
        return ["missing_or_invalid_stage15_remote_patch_manifest"]
    failures: list[str] = []
    files = report.get("files", [])
    if files is None:
        files = []
    if not isinstance(files, list):
        return ["stage15_remote_patch_manifest_files_not_list"]
    for index, row in enumerate(files):
        if not isinstance(row, Mapping):
            failures.append(f"stage15_remote_patch_manifest_files[{index}]_not_object")
            continue
        for field in REMOTE_PATCH_REQUIRED_FIELDS:
            if not row.get(field):
                failures.append(f"stage15_remote_patch_manifest_files[{index}]_missing_{field}")
        path = row.get("path")
        if isinstance(path, str) and (path.startswith("/") or ".." in PurePosixPath(path).parts):
            failures.append(f"stage15_remote_patch_manifest_files[{index}]_unsafe_path")
    if _sha256_file(view.path("stage15_remote_patch_manifest.json")) != summary.get("remote_patch_manifest_sha256"):
        failures.append("remote_patch_manifest_sha256_mismatch")
    return failures


def _validate_resource_lifecycle_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    report = _load_optional_json(view, "stage15_resource_lifecycle_report.json", [])
    if not report:
        return ["missing_or_invalid_stage15_resource_lifecycle_report"]
    failures: list[str] = []
    if report.get("resource_cleanup_passed") is not True:
        failures.append("resource_lifecycle_cleanup_not_passed")
    if summary.get("resource_cleanup_passed") is not True:
        failures.append("summary_resource_cleanup_not_passed")
    return failures


def _validate_sha256_refs(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    if not summary:
        return []
    checks = {
        "training_profile_sha256": "stage15_training_profile.json",
        "hydra_overrides_sha256": "stage15_hydra_overrides.json",
        "fixture_manifest_sha256": "stage15_fixture_manifest.json",
        "remote_patch_manifest_sha256": "stage15_remote_patch_manifest.json",
    }
    failures: list[str] = []
    for field, relative in checks.items():
        expected = summary.get(field)
        if not isinstance(expected, str) or not expected:
            continue
        if not view.exists(relative):
            continue
        actual = _sha256_file(view.path(relative))
        if actual != expected:
            failures.append(f"{field}_mismatch")
    return failures


def _assert_complete_failures(summary: Mapping[str, Any]) -> list[str]:
    if not summary:
        return []
    failures: list[str] = []
    if summary.get("acceptance_passed") is not True:
        failures.append("assert_complete_acceptance_not_passed")
    if summary.get("instance_final_status") not in {"stopped", "paused", "exited"}:
        failures.append("assert_complete_instance_not_stopped_paused_or_exited")
    return failures


def _scan_public_evidence_for_leaks(view: _EvidenceView) -> list[str]:
    failures: list[str] = []
    for relative, path in view.iter_public_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        runtime_private_text = text
        if relative == "stage15_canonical_evidence_map.json":
            runtime_private_text = runtime_private_text.replace(
                "runtime_private/stage15_command_log.raw.jsonl",
                "",
            )
        for pattern in PATH_LEAK_PATTERNS:
            if pattern.search(text):
                failures.append(f"public_evidence_path_or_secret_leak:{relative}:{pattern.pattern}")
                break
        if "runtime_private/" in runtime_private_text:
            failures.append(f"public_evidence_references_runtime_private_path:{relative}")
    return failures


def _load_optional_json(view: _EvidenceView, relative_path: str, failures: list[str]) -> dict[str, Any]:
    if not view.exists(relative_path):
        failures.append(f"missing_{relative_path}")
        return {}
    try:
        return _load_json(view, relative_path)
    except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError) as exc:
        failures.append(f"invalid_{relative_path}:{exc}")
        return {}


def _load_json(view: _EvidenceView, relative_path: str) -> dict[str, Any]:
    payload = json.loads(view.read_text(relative_path))
    if not isinstance(payload, dict):
        raise RepoHarnessError(f"{relative_path} 必须是 JSON object。")
    return payload


def _override_set(payload: Any) -> set[str]:
    if isinstance(payload, list):
        return {str(item) for item in payload}
    if isinstance(payload, Mapping):
        values = payload.get("overrides", payload.get("hydra_overrides", []))
        if isinstance(values, list):
            return {str(item) for item in values}
    return set()


def _int_field(mapping: Mapping[str, Any], field: str, failures: list[str]) -> int:
    value = mapping.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        failures.append(f"{field}_must_be_int")
        return 0
    return value


def _normalize_relative_path(path: str) -> str:
    if ".." in PurePosixPath(path).parts:
        raise RepoHarnessError(f"非法 evidence 相对路径：{path}")
    normalized = posixpath.normpath(path)
    if normalized == "." or normalized.startswith("../") or normalized.startswith("/") or "/../" in normalized:
        raise RepoHarnessError(f"非法 evidence 相对路径：{path}")
    return normalized


def _normalize_tar_member_name(name: str, failures: list[str]) -> str | None:
    if name.startswith("/") or PurePosixPath(name).is_absolute():
        failures.append(f"absolute_tar_entry_not_allowed:{name}")
        return None
    if ".." in PurePosixPath(name).parts:
        failures.append(f"path_traversal_tar_entry_not_allowed:{name}")
        return None
    normalized = posixpath.normpath(name)
    if normalized == "." or normalized.startswith("../") or "/../" in normalized:
        failures.append(f"path_traversal_tar_entry_not_allowed:{name}")
        return None
    return normalized


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


__all__ = [
    "STAGE15_CANONICAL_EVIDENCE_ITEMS",
    "Stage15PartialRolloutAcceptanceInspectReport",
    "inspect_stage15_partial_rollout_acceptance",
    "inspect_stage15_partial_rollout_acceptance_report",
    "validate_stage15_evidence_tarball",
]
