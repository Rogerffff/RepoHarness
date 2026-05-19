"""Stage 14 fully async remote smoke acceptance inspection helpers."""

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

STAGE14_CANONICAL_EVIDENCE_ITEMS: tuple[str, ...] = (
    "stage14_acceptance_summary.json",
    "stage14_command_log.sanitized.jsonl",
    "stage14_training_profile.json",
    "stage14_remote_preflight.json",
    "stage14_environment_matrix.json",
    "stage14_remote_patch_manifest.json",
    "stage14_fixture_manifest.json",
    "stage14_fixture_sha256_report.json",
    "stage14_fully_async_import_inventory.json",
    "stage14_trainer_steps_report.json",
    "stage14_parameter_sync_report.json",
    "stage14_message_queue_report.json",
    "stage14_policy_loss_gate_report.json",
    "stage14_valid_sample_filter_report.json",
    "stage14_visibility_report.json",
    "stage14_staleness_report.json",
    "stage14_batch_provenance_report.json",
    "stage14_resource_cleanup_report.json",
    "stage14_path_leak_scan_report.json",
    "stage14_stdout.sanitized.log",
    "run_stage14_fully_async_smoke.sh",
    "repo_harness_agent_loop_config.yaml",
    "stage14_train.parquet",
    "stage14_val.parquet",
    "stage14_task_pool_manifest.json",
    "stage14_source_map.json",
    "runtime_private_manifest.json",
)

PUBLIC_SCAN_SUFFIXES = (
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

PUBLIC_RUNTIME_HELPER_PREFIXES = (
    "scripts/",
    "vllm_stub/",
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

STDOUT_FATAL_PATTERNS: tuple[str, ...] = (
    "RepoHarnessVerlAdapterError",
    "invalid_for_training_sample_in_formal_batch",
    "Got LoRA adapter that has never been loaded",
    "CUDA out of memory",
    "Traceback",
)

REMOTE_PATCH_REQUIRED_FIELDS: tuple[str, ...] = (
    "path",
    "sha256",
    "purpose",
    "git_status_code",
    "enabled_by_command_or_import",
    "rollback_or_cleanup_note",
    "public_or_private",
)

POLICY_LOSS_LEDGER_REQUIRED_FIELDS: tuple[str, ...] = (
    "sample_id",
    "trajectory_digest",
    "status",
    "reward_state",
    "route",
    "generation_record_digest",
    "visibility_scan_digest",
    "staleness",
    "gate_decision",
    "gate_rejection_reason",
    "side_channel_ref",
    "trainer_step_index",
    "consumed_by_policy_loss",
)


class Stage14AcceptanceInspectReport(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage14_acceptance_inspect_report_v0"
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
        path = self.path(relative_path)
        return path.exists() and path.is_file()

    def path(self, relative_path: str) -> Path:
        normalized = _normalize_relative_path(relative_path)
        return self.root / normalized

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

    def iter_files(self) -> Iterable[tuple[str, Path]]:
        for path in self.root.rglob("*"):
            if path.is_file():
                yield path.relative_to(self.root).as_posix(), path


def inspect_stage14_fully_async_acceptance(
    evidence_path: str | Path,
    *,
    assert_complete: bool = False,
) -> str:
    """检查 Stage 14 fully async 远端 smoke evidence 是否满足本地验收条件。"""

    report = inspect_stage14_fully_async_acceptance_report(
        evidence_path,
        assert_complete=assert_complete,
    )
    if assert_complete and report.failures:
        raise RepoHarnessError("; ".join(report.failures))
    return report.model_dump_json(indent=2)


def inspect_stage14_fully_async_acceptance_report(
    evidence_path: str | Path,
    *,
    assert_complete: bool = False,
) -> Stage14AcceptanceInspectReport:
    target = Path(evidence_path)
    with _prepared_evidence_view(target) as view:
        failures: list[str] = []
        warnings: list[str] = []
        summary_path = "stage14_acceptance_summary.json"
        summary: dict[str, Any] = {}
        if not view.exists(summary_path):
            failures.append("missing_stage14_acceptance_summary")
        else:
            try:
                summary = _load_json(view, summary_path)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                failures.append(f"invalid_stage14_acceptance_summary_json:{exc}")

        canonical_items = _canonical_items(summary)
        failures.extend(_validate_canonical_evidence_map(view, summary, canonical_items))
        failures.extend(_validate_canonical_evidence_content(view, summary))
        failures.extend(_validate_summary(summary))
        failures.extend(_validate_profile_and_override_consistency(view, summary))
        failures.extend(_validate_environment_matrix_consistency(view, summary))
        failures.extend(_validate_trainer_steps_report(view, summary))
        failures.extend(_validate_remote_patch_manifest(view, summary))
        failures.extend(_validate_public_runtime_helpers(view))
        failures.extend(_validate_policy_loss_gate_report(view, summary))
        failures.extend(_validate_staleness_report(view, summary))
        failures.extend(_validate_batch_provenance_report(view, summary))
        failures.extend(_validate_sha256_refs(view, summary))
        failures.extend(_scan_public_evidence_for_leaks(view))
        failures.extend(_validate_runtime_private_manifest(view, summary))

        if assert_complete:
            failures.extend(_assert_complete_failures(summary))

        return Stage14AcceptanceInspectReport(
            evidence_root=target.as_posix(),
            assert_complete=assert_complete,
            summary_path=summary_path if summary else None,
            summary_loaded=bool(summary),
            canonical_items_checked=list(canonical_items),
            failures=failures,
            warnings=warnings,
            passed=not failures,
        )


def validate_stage14_evidence_tarball(
    tarball_path: str | Path,
    *,
    max_single_file_bytes: int = 64 * 1024 * 1024,
    max_total_bytes: int = 512 * 1024 * 1024,
) -> list[str]:
    """只读检查 evidence tarball 是否可安全展开。"""

    failures: list[str] = []
    seen: set[str] = set()
    total_size = 0
    with tarfile.open(tarball_path, "r:*") as tar:
        for member in tar.getmembers():
            name = member.name
            normalized = _normalize_tar_member_name(name, failures)
            if normalized is None:
                continue
            if normalized in seen:
                failures.append(f"duplicate_tar_entry_after_normalize:{normalized}")
            seen.add(normalized)
            if member.issym() or member.islnk():
                failures.append(f"tar_link_entry_not_allowed:{name}")
            if member.isdev() or member.isfifo():
                failures.append(f"tar_special_entry_not_allowed:{name}")
            if not (member.isdir() or member.isfile()):
                failures.append(f"tar_unknown_entry_type_not_allowed:{name}")
            if member.isfile():
                total_size += member.size
                if member.size > max_single_file_bytes:
                    failures.append(f"tar_file_too_large:{name}")
                if total_size > max_total_bytes:
                    failures.append("tar_total_size_too_large")
                    break
    return failures


class _PreparedEvidenceView:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.view: _EvidenceView | None = None

    def __enter__(self) -> _EvidenceView:
        if self.path.is_dir():
            self.view = _EvidenceView(self.path)
            return self.view
        failures = validate_stage14_evidence_tarball(self.path)
        if failures:
            raise RepoHarnessError("Stage 14 evidence tarball 安全检查失败：" + "; ".join(failures))
        self._temp_dir = tempfile.TemporaryDirectory(prefix="repo_harness_stage14_evidence_")
        root = Path(self._temp_dir.name)
        with tarfile.open(self.path, "r:*") as tar:
            tar.extractall(root, filter="data")
        self.view = _EvidenceView(root)
        return self.view

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()


def _prepared_evidence_view(path: Path) -> _PreparedEvidenceView:
    return _PreparedEvidenceView(path)


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


def _load_json(view: _EvidenceView, relative_path: str) -> dict[str, Any]:
    payload = json.loads(view.read_text(relative_path))
    if not isinstance(payload, dict):
        raise RepoHarnessError(f"{relative_path} 必须是 JSON object。")
    return payload


def _canonical_items(summary: Mapping[str, Any]) -> tuple[str, ...]:
    mapping = summary.get("canonical_evidence_map")
    if isinstance(mapping, Mapping):
        return tuple(STAGE14_CANONICAL_EVIDENCE_ITEMS)
    return tuple(STAGE14_CANONICAL_EVIDENCE_ITEMS)


def _validate_canonical_evidence_map(
    view: _EvidenceView,
    summary: Mapping[str, Any],
    canonical_items: Iterable[str],
) -> list[str]:
    failures: list[str] = []
    mapping = summary.get("canonical_evidence_map")
    if not isinstance(mapping, Mapping):
        return ["missing_or_invalid_canonical_evidence_map"]
    for item in canonical_items:
        mapped = mapping.get(item)
        if not isinstance(mapped, str) or not mapped:
            failures.append(f"canonical_evidence_map_missing:{item}")
            continue
        try:
            normalized = _normalize_relative_path(mapped)
        except RepoHarnessError as exc:
            failures.append(f"canonical_evidence_map_invalid_path:{item}:{exc}")
            continue
        if normalized.startswith("runtime_private/") and item != "runtime_private_manifest.json":
            failures.append(f"canonical_public_item_points_to_runtime_private:{item}")
        if not view.exists(normalized):
            failures.append(f"canonical_evidence_file_missing:{item}->{normalized}")
    return failures


def _validate_canonical_evidence_content(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    if not summary:
        return []
    mapping = summary.get("canonical_evidence_map")
    if not isinstance(mapping, Mapping):
        return []
    failures: list[str] = []
    failures.extend(_validate_run_script_content(view, mapping))
    failures.extend(_validate_agent_loop_config_content(view, mapping))
    failures.extend(_validate_parquet_magic(view, mapping, "stage14_train.parquet"))
    failures.extend(_validate_parquet_magic(view, mapping, "stage14_val.parquet"))
    return failures


def _validate_run_script_content(view: _EvidenceView, mapping: Mapping[str, Any]) -> list[str]:
    path = mapping.get("run_stage14_fully_async_smoke.sh")
    if not isinstance(path, str) or not view.exists(path):
        return []
    text = view.read_text(path)
    failures: list[str] = []
    if not text.startswith("#!"):
        failures.append("run_stage14_fully_async_smoke_missing_shebang")
    for required in [
        "verl.experimental.fully_async_policy.fully_async_main",
        "inspect-stage14-fully-async-acceptance",
        "repo_harness_agent_loop_config.yaml",
    ]:
        if required not in text:
            failures.append(f"run_stage14_fully_async_smoke_missing:{required}")
    return failures


def _validate_agent_loop_config_content(view: _EvidenceView, mapping: Mapping[str, Any]) -> list[str]:
    path = mapping.get("repo_harness_agent_loop_config.yaml")
    if not isinstance(path, str) or not view.exists(path):
        return []
    text = view.read_text(path)
    failures: list[str] = []
    if "name: repo_harness" not in text:
        failures.append("repo_harness_agent_loop_config_missing_name")
    if "_target_: repo_harness_verl.agent_loop.RepoHarnessVerlAgentLoop" not in text:
        failures.append("repo_harness_agent_loop_config_missing_target")
    return failures


def _validate_parquet_magic(view: _EvidenceView, mapping: Mapping[str, Any], item: str) -> list[str]:
    path = mapping.get(item)
    if not isinstance(path, str) or not view.exists(path):
        return []
    payload = view.read_bytes(path)
    if len(payload) < 8 or not (payload.startswith(b"PAR1") and payload.endswith(b"PAR1")):
        return [f"{item}_missing_parquet_magic"]
    return []


def _validate_summary(summary: Mapping[str, Any]) -> list[str]:
    if not summary:
        return []
    failures: list[str] = []
    required_fields = [
        "schema_version",
        "stage",
        "acceptance_passed",
        "repo_harness_commit",
        "repo_harness_git_status_short",
        "remote_git_status_short",
        "required_samples",
        "remote_patch_manifest_sha256",
        "training_profile_name",
        "instance_id",
        "gpu_count",
        "inference_backend",
        "training_strategy",
        "weight_sync_strategy",
        "model_id",
        "remote_command_exit_code",
        "completed_trainer_step_count",
        "parameter_sync_count",
        "current_param_version",
        "valid_sample_count",
        "formal_validator_rejected_count",
        "diagnostic_sample_count",
        "policy_loss_gate_passed",
        "policy_loss_gate_mode",
        "policy_loss_queue_invalid_sample_count",
        "message_queue_consumed_sample_count",
        "message_queue_dropped_sample_count",
        "post_sync_valid_sample_count",
        "staleness_threshold",
        "stale_sample_count",
        "filtered_stale_sample_count",
        "max_observed_staleness",
        "trainer_batch_logprob_provenance_passed",
        "trainer_batch_digest",
        "visibility_scan_passed",
        "path_leak_scan_passed",
        "resource_cleanup_passed",
        "stdout_sha256",
        "instance_final_status",
        "canonical_evidence_map",
    ]
    for field in required_fields:
        if field not in summary:
            failures.append(f"acceptance_summary_missing_field:{field}")

    completed_steps = _int_field(summary, "completed_trainer_step_count", failures)
    required_samples = _int_field(summary, "required_samples", failures)
    consumed = _int_field(summary, "message_queue_consumed_sample_count", failures)
    expected_consumed = completed_steps * required_samples
    if completed_steps < 3:
        failures.append("completed_trainer_step_count_below_stage14_minimum")
    if _int_field(summary, "current_param_version", failures) < 1:
        failures.append("current_param_version_below_stage14_minimum")
    if _int_field(summary, "valid_sample_count", failures) < 1:
        failures.append("valid_sample_count_below_stage14_minimum")
    if _int_field(summary, "post_sync_valid_sample_count", failures) < 1:
        failures.append("post_sync_valid_sample_count_below_stage14_minimum")
    if consumed < expected_consumed:
        failures.append("message_queue_consumed_sample_count_below_required_steps")

    for field in [
        "acceptance_passed",
        "policy_loss_gate_passed",
        "trainer_batch_logprob_provenance_passed",
        "visibility_scan_passed",
        "path_leak_scan_passed",
        "resource_cleanup_passed",
    ]:
        if summary.get(field) is not True:
            failures.append(f"{field}_not_true")
    if _int_field(summary, "policy_loss_queue_invalid_sample_count", failures) != 0:
        failures.append("policy_loss_queue_invalid_sample_count_not_zero")
    if _int_field(summary, "message_queue_dropped_sample_count", failures) != 0:
        failures.append("message_queue_dropped_sample_count_not_zero")
    if _int_field(summary, "parameter_sync_count", failures) < 1:
        failures.append("parameter_sync_count_below_minimum")
    if summary.get("remote_command_exit_code") != 0:
        failures.append("remote_command_exit_code_not_zero")
    if summary.get("instance_final_status") not in {"exited", "stopped", "paused"}:
        failures.append("instance_final_status_not_paused_or_exited")
    return failures


def _validate_profile_and_override_consistency(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    if not summary:
        return []
    failures: list[str] = []
    profile: dict[str, Any] = {}
    if not view.exists("stage14_training_profile.json"):
        failures.append("missing_stage14_training_profile")
    else:
        try:
            profile = _load_json(view, "stage14_training_profile.json")
        except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError) as exc:
            failures.append(f"invalid_stage14_training_profile:{exc}")

    if profile:
        _expect_equal(
            failures,
            "training_profile_name",
            summary.get("training_profile_name"),
            profile.get("profile_name"),
            "summary_profile",
        )
        for field in [
            "model_id",
            "gpu_count",
            "inference_backend",
            "weight_sync_strategy",
            "required_samples",
            "staleness_threshold",
        ]:
            _expect_equal(failures, field, summary.get(field), profile.get(field), "summary_profile")
        _validate_summary_profile_training_strategy_mode(
            failures,
            summary.get("training_strategy"),
            profile.get("training_strategy"),
            profile.get("lora_rank"),
        )
        _validate_training_strategy_lora_rank(
            failures,
            profile.get("training_strategy"),
            profile.get("lora_rank"),
            "stage14_training_profile",
        )
        _validate_checkpoint_strategy(
            failures,
            summary.get("weight_sync_strategy"),
            profile.get("checkpoint_engine_backend"),
            profile.get("checkpoint_engine_device"),
            "stage14_training_profile",
        )

    if view.exists("stage14_hydra_overrides.json"):
        try:
            overrides_payload = json.loads(view.read_text("stage14_hydra_overrides.json"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            failures.append(f"invalid_stage14_hydra_overrides:{exc}")
            overrides_payload = None
        if not isinstance(overrides_payload, list):
            failures.append("stage14_hydra_overrides_not_list")
        else:
            overrides = _parse_hydra_overrides(overrides_payload, failures)
            _expect_equal(
                failures,
                "model_id",
                summary.get("model_id"),
                overrides.get("actor_rollout_ref.model.path"),
                "summary_hydra",
            )
            _expect_equal(
                failures,
                "inference_backend",
                summary.get("inference_backend"),
                overrides.get("actor_rollout_ref.rollout.name"),
                "summary_hydra",
            )
            _expect_equal(
                failures,
                "required_samples",
                summary.get("required_samples"),
                overrides.get("async_training.require_batches"),
                "summary_hydra",
            )
            _validate_training_strategy_lora_rank(
                failures,
                summary.get("training_strategy"),
                overrides.get("actor_rollout_ref.model.lora_rank"),
                "stage14_hydra_overrides",
            )
            _validate_checkpoint_strategy(
                failures,
                summary.get("weight_sync_strategy"),
                overrides.get("actor_rollout_ref.rollout.checkpoint_engine.backend"),
                overrides.get("actor_rollout_ref.rollout.checkpoint_engine.engine_kwargs.nixl.device"),
                "stage14_hydra_overrides",
            )
    return failures


def _validate_environment_matrix_consistency(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    if not summary:
        return []
    if not view.exists("stage14_environment_matrix.json"):
        return ["missing_stage14_environment_matrix"]
    failures: list[str] = []
    try:
        environment_matrix = _load_json(view, "stage14_environment_matrix.json")
    except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError) as exc:
        return [f"invalid_stage14_environment_matrix:{exc}"]
    profile: dict[str, Any] = {}
    if view.exists("stage14_training_profile.json"):
        try:
            profile = _load_json(view, "stage14_training_profile.json")
        except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError):
            profile = {}
    _expect_equal(
        failures,
        "training_profile_name",
        summary.get("training_profile_name"),
        environment_matrix.get("execution_profile"),
        "summary_environment_matrix",
    )
    for field in ["gpu_count", "image", "inference_backend"]:
        _expect_equal(failures, field, summary.get(field), environment_matrix.get(field), "summary_environment_matrix")
    expected_checkpoint_backend = profile.get("checkpoint_engine_backend")
    if expected_checkpoint_backend is None:
        strategy = str(summary.get("weight_sync_strategy") or "").lower()
        if "nixl" in strategy:
            expected_checkpoint_backend = "nixl"
    if expected_checkpoint_backend is not None:
        _expect_equal(
            failures,
            "checkpoint_engine_backend",
            expected_checkpoint_backend,
            environment_matrix.get("checkpoint_engine_backend"),
            "profile_environment_matrix",
        )
    return failures


def _validate_remote_patch_manifest(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if not view.exists("stage14_remote_patch_manifest.json"):
        return ["missing_stage14_remote_patch_manifest"]
    try:
        manifest = _load_json(view, "stage14_remote_patch_manifest.json")
    except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError) as exc:
        return [f"invalid_stage14_remote_patch_manifest:{exc}"]
    dirty_entries = _parse_git_status_entries(
        "\n".join(
            value
            for value in [
                str(summary.get("repo_harness_git_status_short") or "").rstrip(),
                str(summary.get("remote_git_status_short") or "").rstrip(),
            ]
            if value.strip()
        )
    )
    if dirty_entries:
        files = manifest.get("files")
        if not isinstance(files, list) or not files:
            failures.append("dirty_worktree_without_patch_manifest_files")
        else:
            manifest_status_by_path: dict[str, str] = {}
            for index, item in enumerate(files):
                if not isinstance(item, Mapping):
                    failures.append(f"remote_patch_manifest_files[{index}]_not_object")
                    continue
                path = item.get("path")
                if isinstance(path, str):
                    manifest_status_by_path[path] = str(item.get("git_status_code") or "")
                for field in REMOTE_PATCH_REQUIRED_FIELDS:
                    if not item.get(field):
                        failures.append(f"remote_patch_manifest_files[{index}]_missing_{field}")
            for status_entry in dirty_entries:
                manifest_status = manifest_status_by_path.get(status_entry["path"])
                if manifest_status is None:
                    failures.append(f"dirty_worktree_file_missing_from_patch_manifest:{status_entry['path']}")
                elif manifest_status != status_entry["git_status_code"]:
                    failures.append(f"dirty_worktree_git_status_code_mismatch:{status_entry['path']}")
    return failures


def _validate_public_runtime_helpers(view: _EvidenceView) -> list[str]:
    failures: list[str] = []
    manifest_files: dict[str, Mapping[str, Any]] = {}
    if view.exists("stage14_remote_patch_manifest.json"):
        try:
            manifest = _load_json(view, "stage14_remote_patch_manifest.json")
        except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError):
            manifest = {}
        files = manifest.get("files") if isinstance(manifest, Mapping) else None
        if isinstance(files, list):
            for item in files:
                if isinstance(item, Mapping) and isinstance(item.get("path"), str):
                    manifest_files[str(item["path"])] = item
    for relative, path in view.iter_files():
        if relative.startswith("runtime_private/"):
            continue
        if "__pycache__/" in relative or relative.endswith(".pyc"):
            failures.append(f"public_evidence_pycache_not_allowed:{relative}")
            continue
        if not relative.startswith(PUBLIC_RUNTIME_HELPER_PREFIXES):
            continue
        entry = manifest_files.get(relative)
        if entry is None:
            failures.append(f"public_runtime_helper_missing_from_patch_manifest:{relative}")
            continue
        for field in REMOTE_PATCH_REQUIRED_FIELDS:
            if not entry.get(field):
                failures.append(f"public_runtime_helper_manifest_missing_{field}:{relative}")
        sha = entry.get("sha256")
        if isinstance(sha, str) and not _sha256_matches(sha, _sha256_bytes(path.read_bytes())):
            failures.append(f"public_runtime_helper_sha256_mismatch:{relative}")
    return failures


def _validate_trainer_steps_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    if not view.exists("stage14_trainer_steps_report.json"):
        return ["missing_stage14_trainer_steps_report"]
    failures: list[str] = []
    required_samples = _int_field(summary, "required_samples", failures)
    try:
        report = _load_json(view, "stage14_trainer_steps_report.json")
    except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError) as exc:
        return [f"invalid_stage14_trainer_steps_report:{exc}"]
    summary_completed = _int_field(summary, "completed_trainer_step_count", failures)
    summary_param_version = _int_field(summary, "current_param_version", failures)
    report_completed = _int_field(report, "completed_trainer_step_count", failures)
    if report_completed != summary_completed:
        failures.append("trainer_steps_completed_count_mismatch")
    steps = report.get("steps")
    if not isinstance(steps, list):
        failures.append("trainer_steps_report_steps_missing")
        return failures
    if len(steps) < summary_completed:
        failures.append("trainer_steps_report_steps_below_completed_count")
    observed_indexes: set[int] = set()
    max_param_version = 0
    for index, row in enumerate(steps):
        if not isinstance(row, Mapping):
            failures.append(f"trainer_steps_report_steps[{index}]_not_object")
            continue
        step_index = row.get("trainer_step_index")
        if not isinstance(step_index, int) or isinstance(step_index, bool):
            failures.append(f"trainer_steps_report_steps[{index}]_missing_trainer_step_index")
        else:
            observed_indexes.add(step_index)
        if not row.get("trainer_batch_digest"):
            failures.append(f"trainer_steps_report_steps[{index}]_missing_trainer_batch_digest")
        consumed_valid = row.get("consumed_valid_sample_count")
        if consumed_valid is None:
            failures.append(f"trainer_steps_report_steps[{index}]_missing_consumed_valid_sample_count")
        else:
            consumed_valid_count = _int_field(row, "consumed_valid_sample_count", failures)
            if consumed_valid_count < required_samples:
                failures.append(f"trainer_steps_report_step_below_required_samples:{step_index}")
        max_param_version = max(max_param_version, _int_field(row, "current_param_version", failures))
    expected_zero_based = set(range(summary_completed))
    expected_one_based = set(range(1, summary_completed + 1))
    if not (expected_zero_based <= observed_indexes or expected_one_based <= observed_indexes):
        failures.append("trainer_steps_report_missing_completed_step_index")
    if max_param_version != summary_param_version:
        failures.append("trainer_steps_current_param_version_mismatch")
    return failures


def _validate_policy_loss_gate_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    if not view.exists("stage14_policy_loss_gate_report.json"):
        return ["missing_stage14_policy_loss_gate_report"]
    failures: list[str] = []
    try:
        report = _load_json(view, "stage14_policy_loss_gate_report.json")
    except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError) as exc:
        return [f"invalid_stage14_policy_loss_gate_report:{exc}"]
    if report.get("policy_loss_gate_passed") is not True:
        failures.append("policy_loss_gate_report_not_passed")
    if _int_field(report, "invalid_consumed_sample_count", failures) != 0:
        failures.append("policy_loss_gate_invalid_consumed_not_zero")
    accepted = _int_field(report, "accepted_for_policy_loss_count", failures)
    consumed = _int_field(report, "consumed_sample_count", failures)
    required_samples = _int_field(summary, "required_samples", failures)
    completed_steps = _int_field(summary, "completed_trainer_step_count", failures)
    expected = required_samples * completed_steps
    if accepted < expected:
        failures.append("accepted_for_policy_loss_count_below_required_steps")
    if consumed < expected:
        failures.append("policy_loss_gate_consumed_count_below_required_steps")
    ledger = report.get("sample_ledger")
    if not isinstance(ledger, list):
        failures.append("policy_loss_gate_sample_ledger_missing")
    else:
        consumed_step_indexes: set[int] = set()
        consumed_count_by_step: dict[int, int] = {}
        consumed_accepted_count = 0
        trainer_step_indexes = _trainer_step_indexes(view)
        for index, row in enumerate(ledger):
            if not isinstance(row, Mapping):
                failures.append(f"policy_loss_gate_sample_ledger[{index}]_not_object")
                continue
            for field in POLICY_LOSS_LEDGER_REQUIRED_FIELDS:
                if field not in row:
                    failures.append(f"policy_loss_gate_sample_ledger[{index}]_missing_{field}")
            if row.get("consumed_by_policy_loss") and row.get("gate_decision") != "accepted":
                failures.append(f"policy_loss_gate_consumed_unaccepted_sample:{row.get('sample_id', index)}")
            if row.get("consumed_by_policy_loss") and row.get("gate_decision") == "accepted":
                step_index = row.get("trainer_step_index")
                if isinstance(step_index, int) and not isinstance(step_index, bool):
                    if trainer_step_indexes and step_index not in trainer_step_indexes:
                        failures.append(f"policy_loss_gate_consumed_step_not_completed:{step_index}")
                    consumed_step_indexes.add(step_index)
                    consumed_count_by_step[step_index] = consumed_count_by_step.get(step_index, 0) + 1
                    consumed_accepted_count += 1
        expected_zero_based = set(range(completed_steps))
        expected_one_based = set(range(1, completed_steps + 1))
        if trainer_step_indexes:
            expected_steps = sorted(trainer_step_indexes)
        elif expected_zero_based <= consumed_step_indexes:
            expected_steps = sorted(expected_zero_based)
        elif expected_one_based <= consumed_step_indexes:
            expected_steps = sorted(expected_one_based)
        else:
            expected_steps = sorted(expected_zero_based)
        if not set(expected_steps) <= consumed_step_indexes:
            failures.append("policy_loss_gate_missing_valid_sample_for_completed_trainer_step")
        for step_index in expected_steps:
            if consumed_count_by_step.get(step_index, 0) < required_samples:
                failures.append(f"policy_loss_gate_step_below_required_samples:{step_index}")
        if consumed_accepted_count != consumed:
            failures.append("policy_loss_gate_consumed_count_mismatch_ledger")
    return failures


def _validate_staleness_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    if not view.exists("stage14_staleness_report.json"):
        return ["missing_stage14_staleness_report"]
    failures: list[str] = []
    try:
        report = _load_json(view, "stage14_staleness_report.json")
    except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError) as exc:
        return [f"invalid_stage14_staleness_report:{exc}"]
    threshold = _float_field(summary, "staleness_threshold", failures)
    summary_max_observed_staleness = _float_field(summary, "max_observed_staleness", failures)
    ledger = report.get("sample_ledger")
    if not isinstance(ledger, list):
        return ["staleness_sample_ledger_missing"]
    stale_count = 0
    filtered_stale_count = 0
    for index, row in enumerate(ledger):
        if not isinstance(row, Mapping):
            continue
        is_stale = _float(row.get("staleness")) > threshold
        if is_stale:
            stale_count += 1
        if row.get("consumed_by_policy_loss") and is_stale:
            failures.append(f"stale_sample_consumed_by_policy_loss:{row.get('sample_id', index)}")
        if is_stale and not _row_marks_stale_filtered(row):
            failures.append(f"stale_sample_missing_filtered_ledger_mark:{row.get('sample_id', index)}")
        if is_stale and _row_marks_stale_filtered(row):
            filtered_stale_count += 1
    if _int_field(summary, "filtered_stale_sample_count", failures) > _int_field(summary, "stale_sample_count", failures):
        failures.append("filtered_stale_sample_count_exceeds_stale_sample_count")
    if stale_count != _int_field(summary, "stale_sample_count", failures):
        failures.append("staleness_report_stale_count_mismatch")
    if filtered_stale_count != _int_field(summary, "filtered_stale_sample_count", failures):
        failures.append("staleness_report_filtered_stale_count_mismatch")
    if summary_max_observed_staleness != max(
        [_float(row.get("staleness")) for row in ledger if isinstance(row, Mapping)] or [0.0]
    ):
        failures.append("staleness_report_max_observed_staleness_mismatch")
    return failures


def _validate_batch_provenance_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    if not view.exists("stage14_batch_provenance_report.json"):
        return ["missing_stage14_batch_provenance_report"]
    failures: list[str] = []
    try:
        report = _load_json(view, "stage14_batch_provenance_report.json")
    except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError) as exc:
        return [f"invalid_stage14_batch_provenance_report:{exc}"]
    if report.get("trainer_batch_logprob_provenance_passed") is not True:
        failures.append("batch_provenance_report_not_passed")
    _expect_equal(
        failures,
        "trainer_batch_digest",
        summary.get("trainer_batch_digest"),
        report.get("trainer_batch_digest"),
        "summary_batch_provenance",
    )
    for field in [
        "response_ids_digest",
        "response_mask_digest",
        "rollout_log_probs_digest",
        "response_ids_shape",
        "response_mask_shape",
        "rollout_log_probs_shape",
    ]:
        if field not in report:
            failures.append(f"batch_provenance_missing_field:{field}")
    shape_fields = [
        "response_ids_shape",
        "response_mask_shape",
        "rollout_log_probs_shape",
    ]
    shapes: list[tuple[str, tuple[int, ...]]] = []
    for field in shape_fields:
        shape = report.get(field)
        if not isinstance(shape, list) or not shape or any(not isinstance(item, int) or isinstance(item, bool) or item < 0 for item in shape):
            failures.append(f"batch_provenance_invalid_shape:{field}")
            continue
        shapes.append((field, tuple(shape)))
    if len(shapes) == len(shape_fields):
        first_shape = shapes[0][1]
        for field, shape in shapes[1:]:
            if shape != first_shape:
                failures.append(f"batch_provenance_shape_mismatch:{shapes[0][0]}:{field}")
    for field in [
        "response_ids_digest",
        "response_mask_digest",
        "rollout_log_probs_digest",
    ]:
        value = report.get(field)
        if not isinstance(value, str) or not value.startswith("sha256:"):
            failures.append(f"batch_provenance_invalid_digest:{field}")
    return failures


def _validate_sha256_refs(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    patch_expected = summary.get("remote_patch_manifest_sha256")
    if isinstance(patch_expected, str) and view.exists("stage14_remote_patch_manifest.json"):
        patch_actual = _sha256_bytes(view.read_bytes("stage14_remote_patch_manifest.json"))
        if not _sha256_matches(patch_expected, patch_actual):
            failures.append("remote_patch_manifest_sha256_mismatch")
    stdout_expected = summary.get("stdout_sha256")
    if isinstance(stdout_expected, str) and view.exists("stage14_stdout.sanitized.log"):
        stdout_actual = _sha256_bytes(view.read_bytes("stage14_stdout.sanitized.log"))
        if not _sha256_matches(stdout_expected, stdout_actual):
            failures.append("stdout_sha256_mismatch")
    return failures


def _validate_runtime_private_manifest(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    if not view.exists("runtime_private_manifest.json"):
        return ["missing_runtime_private_manifest"]
    failures: list[str] = []
    try:
        manifest = _load_json(view, "runtime_private_manifest.json")
    except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError) as exc:
        return [f"invalid_runtime_private_manifest:{exc}"]
    private_files = manifest.get("private_files", [])
    if not isinstance(private_files, list):
        failures.append("runtime_private_manifest_private_files_not_list")
    public_refs = json.dumps(summary, sort_keys=True, ensure_ascii=False)
    if "runtime_private/stage14_stdout.raw.log" in public_refs:
        failures.append("acceptance_summary_references_raw_stdout_private_file")
    for relative, path in view.iter_public_files():
        if relative == "runtime_private_manifest.json":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "runtime_private/" in text:
            failures.append(f"public_evidence_references_runtime_private_path:{relative}")
    return failures


def _scan_public_evidence_for_leaks(view: _EvidenceView) -> list[str]:
    failures: list[str] = []
    for relative, path in view.iter_public_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            failures.append(f"public_file_unreadable:{relative}:{exc}")
            continue
        for pattern in PATH_LEAK_PATTERNS:
            if pattern.search(text):
                failures.append(f"public_evidence_path_or_secret_leak:{relative}:{pattern.pattern}")
        if relative == "stage14_stdout.sanitized.log":
            for pattern in STDOUT_FATAL_PATTERNS:
                if pattern in text:
                    failures.append(f"stage14_stdout_contains_fatal_pattern:{pattern}")
    return failures


def _assert_complete_failures(summary: Mapping[str, Any]) -> list[str]:
    if not summary:
        return []
    failures: list[str] = []
    if summary.get("acceptance_passed") is not True:
        failures.append("assert_complete_acceptance_passed_false")
    if summary.get("instance_final_status") not in {"exited", "stopped", "paused"}:
        failures.append("assert_complete_instance_not_paused")
    return failures


def _parse_hydra_overrides(overrides: list[Any], failures: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for index, item in enumerate(overrides):
        if not isinstance(item, str) or "=" not in item:
            failures.append(f"stage14_hydra_overrides[{index}]_not_key_value")
            continue
        key, value = item.split("=", 1)
        parsed[key.lstrip("+")] = value
    return parsed


def _expect_equal(
    failures: list[str],
    field: str,
    left: Any,
    right: Any,
    scope: str,
) -> None:
    if left is None or right is None:
        failures.append(f"{scope}_missing_field:{field}")
        return
    if str(left) != str(right):
        failures.append(f"{scope}_mismatch:{field}")


def _validate_training_strategy_lora_rank(
    failures: list[str],
    training_strategy: Any,
    lora_rank: Any,
    scope: str,
) -> None:
    strategy = str(training_strategy or "").lower()
    try:
        rank = int(lora_rank)
    except (TypeError, ValueError):
        failures.append(f"{scope}_lora_rank_must_be_int")
        return
    if "lora" in strategy and rank <= 0:
        failures.append(f"{scope}_lora_strategy_requires_positive_lora_rank")
    if "lora" not in strategy and rank != 0:
        failures.append(f"{scope}_non_lora_strategy_requires_zero_lora_rank")


def _validate_summary_profile_training_strategy_mode(
    failures: list[str],
    summary_training_strategy: Any,
    profile_training_strategy: Any,
    profile_lora_rank: Any,
) -> None:
    summary_strategy = str(summary_training_strategy or "").lower()
    profile_strategy = str(profile_training_strategy or "").lower()
    try:
        profile_rank = int(profile_lora_rank)
    except (TypeError, ValueError):
        return
    summary_expects_lora = "lora" in summary_strategy
    profile_uses_lora = "lora" in profile_strategy or profile_rank > 0
    summary_expects_full = "full" in summary_strategy and "lora" not in summary_strategy
    profile_uses_full = "lora" not in profile_strategy and profile_rank == 0
    if summary_expects_lora != profile_uses_lora:
        failures.append("summary_profile_training_strategy_lora_mode_mismatch")
    if summary_expects_full and not profile_uses_full:
        failures.append("summary_profile_training_strategy_full_mode_mismatch")


def _validate_checkpoint_strategy(
    failures: list[str],
    weight_sync_strategy: Any,
    checkpoint_backend: Any,
    checkpoint_device: Any,
    scope: str,
) -> None:
    strategy = str(weight_sync_strategy or "").lower()
    backend = str(checkpoint_backend or "").lower()
    device = str(checkpoint_device or "").lower()
    if "nixl" in strategy:
        if backend != "nixl":
            failures.append(f"{scope}_nixl_weight_sync_requires_nixl_backend")
        if "cuda" in strategy and device != "cuda":
            failures.append(f"{scope}_nixl_cuda_weight_sync_requires_cuda_device")
    if backend == "nixl" and "nixl" not in strategy:
        failures.append(f"{scope}_nixl_backend_requires_nixl_weight_sync")
    if backend == "nccl" and "nixl" in strategy:
        failures.append(f"{scope}_nccl_backend_conflicts_with_nixl_weight_sync")


def _int_field(payload: Mapping[str, Any], field: str, failures: list[str]) -> int:
    value = payload.get(field, 0)
    if isinstance(value, bool):
        failures.append(f"{field}_must_be_int")
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        failures.append(f"{field}_must_be_int")
        return 0


def _parse_git_status_entries(value: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in value.splitlines():
        if not line.strip():
            continue
        if len(line) >= 3 and line[2] == " ":
            status_code = line[:2].strip() or line[:2]
            path = line[3:].strip()
        else:
            parts = line.strip().split(maxsplit=1)
            status_code = parts[0] if parts else ""
            path = parts[1] if len(parts) > 1 else ""
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            entries.append({"git_status_code": status_code, "path": path})
    return entries


def _trainer_step_indexes(view: _EvidenceView) -> set[int]:
    if not view.exists("stage14_trainer_steps_report.json"):
        return set()
    try:
        report = _load_json(view, "stage14_trainer_steps_report.json")
    except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError):
        return set()
    indexes: set[int] = set()
    steps = report.get("steps")
    if not isinstance(steps, list):
        return indexes
    for row in steps:
        if not isinstance(row, Mapping):
            continue
        step_index = row.get("trainer_step_index")
        if isinstance(step_index, int) and not isinstance(step_index, bool):
            indexes.add(step_index)
    return indexes


def _row_marks_stale_filtered(row: Mapping[str, Any]) -> bool:
    if row.get("filtered_as_stale") is True:
        return True
    decision = str(row.get("gate_decision") or "").lower()
    reason = str(row.get("gate_rejection_reason") or "").lower()
    return "stale" in decision or "stale" in reason


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _float_field(payload: Mapping[str, Any], field: str, failures: list[str]) -> float:
    if field not in payload:
        failures.append(f"{field}_must_be_number")
        return 0.0
    value = payload.get(field)
    if isinstance(value, bool):
        failures.append(f"{field}_must_be_number")
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        failures.append(f"{field}_must_be_number")
        return 0.0


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_matches(expected: str, actual: str) -> bool:
    normalized = expected.removeprefix("sha256:")
    return normalized == actual
