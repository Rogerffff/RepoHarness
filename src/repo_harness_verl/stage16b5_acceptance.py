"""Stage 16B.5 remote Docker-capable backend acceptance inspector."""

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

from pydantic import BaseModel, Field

from repo_harness.errors import RepoHarnessError


STAGE16B5_CANONICAL_EVIDENCE_ITEMS: tuple[str, ...] = (
    "stage16b5_acceptance_summary.json",
    "stage16b5_docker_preflight_report.json",
    "stage16b5_docker_diagnostic_smoke_report.json",
    "stage16b5_path_redaction_report.json",
    "stage16b5_shared_dependency_guard_report.json",
    "stage16b5_concurrency_isolation_report.json",
    "stage16b5_container_cleanup_report.json",
    "stage16b5_formal_online_rl_gate_report.json",
    "stage16b5_negative_cases_report.json",
    "stage16b5_training_eligibility_report.json",
    "stage16b5_command_log.sanitized.jsonl",
    "stage16b5_canonical_evidence_map.json",
    "stage16b5_remote_patch_manifest.json",
    "fixture_manifest.json",
    "fixture_sha256_report.json",
    "runtime_private/stage16b5_command_log.raw.jsonl",
    "runtime_private/raw_container_logs_manifest.json",
)

_PUBLIC_SCAN_SUFFIXES = {".json", ".jsonl", ".log", ".yaml", ".yml", ".sh", ".txt"}
_ALLOWED_RUNTIME_PRIVATE_REFS = {
    "runtime_private/stage16b5_command_log.raw.jsonl",
    "runtime_private/raw_container_logs_manifest.json",
}
_PATH_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/Users/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/workspace/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/root/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/home/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/private/[A-Za-z0-9_.\-/]+"),
    re.compile(r"\.repo_harness_env_overlay"),
    re.compile(r"\.repo_harness_runtime"),
    re.compile(r"repo-harness-run"),
    re.compile(r"hidden[_-]?verifier", re.IGNORECASE),
    re.compile(r"gold[_-]?patch", re.IGNORECASE),
    re.compile(r"provider[_-]?secret", re.IGNORECASE),
    re.compile(r"BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY"),
)


class Stage16B5DockerBackendAcceptanceInspectReport(BaseModel):
    """Machine-readable Stage 16B.5 evidence inspection result."""

    schema_version: str = "repo_harness_verl_stage16b5_docker_backend_acceptance_inspect_report_v0"
    evidence_root: str
    assert_complete: bool = False
    summary_path: str | None = None
    passed: bool
    failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    canonical_evidence_items: list[str] = Field(default_factory=list)


class _EvidenceView:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, relative_path: str) -> Path:
        return self.root / _normalize_relative_path(relative_path)

    def exists(self, relative_path: str) -> bool:
        return self.path(relative_path).exists()

    def read_text(self, relative_path: str) -> str:
        return self.path(relative_path).read_text(encoding="utf-8")

    def iter_public_files(self) -> Iterable[tuple[str, Path]]:
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(self.root).as_posix()
            if relative.startswith("runtime_private/"):
                continue
            if path.suffix in _PUBLIC_SCAN_SUFFIXES:
                yield relative, path


class _PreparedEvidenceView:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> _EvidenceView:
        if self.path.is_dir():
            return _EvidenceView(self.path)
        failures = validate_stage16b5_evidence_tarball(self.path)
        if failures:
            raise RepoHarnessError("Stage 16B.5 evidence tarball 安全检查失败：" + "; ".join(failures))
        self._temp_dir = tempfile.TemporaryDirectory(prefix="repo_harness_stage16b5_evidence_")
        root = Path(self._temp_dir.name)
        with tarfile.open(self.path, "r:*") as tar:
            tar.extractall(root, filter="data")
        return _EvidenceView(root)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()


def inspect_stage16b5_docker_backend_acceptance(
    evidence_path: str | Path,
    *,
    assert_complete: bool = False,
) -> str:
    """检查 Stage 16B.5 远端 Docker-capable backend evidence 是否满足验收条件。"""

    report = inspect_stage16b5_docker_backend_acceptance_report(
        evidence_path,
        assert_complete=assert_complete,
    )
    if assert_complete and report.failures:
        raise RepoHarnessError("; ".join(report.failures))
    return report.model_dump_json(indent=2)


def inspect_stage16b5_docker_backend_acceptance_report(
    evidence_path: str | Path,
    *,
    assert_complete: bool = False,
) -> Stage16B5DockerBackendAcceptanceInspectReport:
    target = Path(evidence_path)
    with _PreparedEvidenceView(target) as view:
        failures: list[str] = []
        warnings: list[str] = []
        summary_path = "stage16b5_acceptance_summary.json"
        summary: dict[str, Any] = {}
        if not view.exists(summary_path):
            failures.append("missing_stage16b5_acceptance_summary")
        else:
            try:
                summary = _load_json(view, summary_path)
            except (json.JSONDecodeError, UnicodeDecodeError, RepoHarnessError) as exc:
                failures.append(f"invalid_stage16b5_acceptance_summary_json:{exc}")

        failures.extend(_validate_canonical_evidence(view, summary))
        failures.extend(_validate_summary(summary))
        failures.extend(_validate_preflight_report(view, summary))
        failures.extend(_validate_diagnostic_smoke_report(view, summary))
        failures.extend(_validate_cleanup_report(view, summary))
        failures.extend(_validate_formal_gate_report(view, summary))
        failures.extend(_validate_training_eligibility_report(view, summary))
        failures.extend(_validate_negative_cases_report(view, summary))
        failures.extend(_validate_path_redaction_report(view, summary))
        failures.extend(_validate_shared_dependency_guard_report(view, summary))
        failures.extend(_validate_concurrency_isolation_report(view))
        failures.extend(_validate_remote_patch_manifest(view))
        failures.extend(_validate_runtime_private_evidence(view, summary))
        failures.extend(_validate_sha256_refs(view, summary))
        failures.extend(_scan_public_evidence_for_leaks(view))
        if assert_complete:
            failures.extend(_assert_complete_failures(summary))

        return Stage16B5DockerBackendAcceptanceInspectReport(
            evidence_root=target.as_posix(),
            assert_complete=assert_complete,
            summary_path=summary_path if summary else None,
            passed=not failures,
            failures=failures,
            warnings=warnings,
            canonical_evidence_items=list(STAGE16B5_CANONICAL_EVIDENCE_ITEMS),
        )


def validate_stage16b5_evidence_tarball(path: str | Path) -> list[str]:
    """Perform conservative tarball safety checks before extracting evidence."""

    failures: list[str] = []
    seen: set[str] = set()
    total_size = 0
    try:
        with tarfile.open(path, "r:*") as tar:
            for member in tar.getmembers():
                normalized = _normalize_tar_member_name(member.name, failures)
                if normalized is None:
                    continue
                if normalized in seen:
                    failures.append(f"duplicate_tar_entry_not_allowed:{normalized}")
                seen.add(normalized)
                if member.issym() or member.islnk():
                    failures.append(f"link_tar_entry_not_allowed:{member.name}")
                if member.isdev() or member.isfifo():
                    failures.append(f"special_tar_entry_not_allowed:{member.name}")
                if member.size > 32 * 1024 * 1024:
                    failures.append(f"tar_entry_too_large:{member.name}")
                total_size += max(member.size, 0)
                if total_size > 128 * 1024 * 1024:
                    failures.append("tarball_total_size_exceeds_limit")
                    break
    except tarfile.TarError as exc:
        failures.append(f"invalid_tarball:{exc}")
    return failures


def _validate_canonical_evidence(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    for item in STAGE16B5_CANONICAL_EVIDENCE_ITEMS:
        if not view.exists(item):
            failures.append(f"missing_canonical_evidence:{item}")
    if summary:
        mapping = _load_optional_json(view, "stage16b5_canonical_evidence_map.json", failures)
        items = mapping.get("items") if isinstance(mapping, Mapping) else None
        if not isinstance(items, Mapping):
            failures.append("stage16b5_canonical_evidence_map_missing_items")
        else:
            for item in STAGE16B5_CANONICAL_EVIDENCE_ITEMS:
                if items.get(item) != item:
                    failures.append(f"canonical_evidence_map_mismatch:{item}")
    return failures


def _validate_summary(summary: Mapping[str, Any]) -> list[str]:
    if not summary:
        return []
    failures: list[str] = []
    required_true = (
        "acceptance_passed",
        "remote_docker_backend_preflight_passed",
        "remote_docker_diagnostic_profile_verified",
        "docker_daemon_available",
        "nvidia_container_toolkit_available",
        "container_nvidia_smi_passed",
        "repo_harness_docker_diagnostic_session_passed",
        "formal_online_rl_gate_passed",
        "training_eligibility_gate_passed",
        "shared_dependency_guard_passed",
        "path_leak_scan_passed",
        "public_path_leak_scan_passed",
        "runtime_private_evidence_present",
        "resource_cleanup_passed",
        "container_cleanup_passed",
        "background_process_cleanup_passed",
        "workspace_projection_sync_passed",
        "run_dir_mount_absent",
        "git_hidden_from_diagnostic_projection",
        "negative_cases_passed",
    )
    for field in required_true:
        if summary.get(field) is not True:
            failures.append(f"summary_{field}_not_true")
    if summary.get("stage") != "16B.5":
        failures.append("summary_stage_not_16b5")
    if summary.get("training_profile_name") != "remote_docker_capable_training_backend":
        failures.append("summary_training_profile_name_mismatch")
    if summary.get("diagnostic_session_backend") != "docker_persistent_container":
        failures.append("summary_diagnostic_session_backend_not_docker_persistent_container")
    if summary.get("docker_gpus_all_status") != "passed":
        failures.append("summary_docker_gpus_all_status_not_passed")
    if summary.get("container_nvidia_smi_status") != "passed":
        failures.append("summary_container_nvidia_smi_status_not_passed")
    if _int(summary.get("valid_docker_diagnostic_sample_count")) < 1:
        failures.append("valid_docker_diagnostic_sample_count_below_minimum")
    if _int(summary.get("formal_online_rl_candidate_count")) < 1:
        failures.append("formal_online_rl_candidate_count_below_minimum")
    if _int(summary.get("invalid_docker_diagnostic_sample_count")) < 1:
        failures.append("invalid_docker_diagnostic_sample_count_below_minimum")
    if _int(summary.get("dependency_mutation_rejected_count")) < 1:
        failures.append("dependency_mutation_rejected_count_below_minimum")
    if _int(summary.get("hidden_path_rejected_count")) < 1:
        failures.append("hidden_path_rejected_count_below_minimum")
    for field in (
        "remote_backend_provider",
        "remote_instance_id",
        "gpu_model",
        "driver_version",
        "cuda_version",
        "docker_version",
        "nvidia_container_toolkit_version",
        "base_os",
        "preflight_image",
        "preflight_image_digest",
    ):
        if not isinstance(summary.get(field), str) or not summary.get(field):
            failures.append(f"summary_missing_remote_reproducibility_field:{field}")
    return failures


def _validate_preflight_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    report = _load_optional_json(view, "stage16b5_docker_preflight_report.json", failures)
    if not report:
        return failures
    if report.get("root_access") is not True:
        failures.append("preflight_root_access_not_true")
    if report.get("docker_daemon_available") is not True:
        failures.append("preflight_docker_daemon_not_available")
    if report.get("docker_gpus_all_status") != "passed":
        failures.append("preflight_docker_gpus_all_not_passed")
    if report.get("container_nvidia_smi_status") != "passed":
        failures.append("preflight_container_nvidia_smi_not_passed")
    if report.get("gpu_count", 0) < 1:
        failures.append("preflight_gpu_count_below_minimum")
    if report.get("docker_server_version") != summary.get("docker_server_version"):
        failures.append("preflight_summary_docker_server_version_mismatch")
    for field in (
        "remote_backend_provider",
        "remote_instance_id",
        "gpu_model",
        "driver_version",
        "cuda_version",
        "docker_version",
        "nvidia_container_toolkit_version",
        "base_os",
        "preflight_image",
        "preflight_image_digest",
    ):
        if not isinstance(report.get(field), str) or not report.get(field):
            failures.append(f"preflight_missing_remote_reproducibility_field:{field}")
        elif summary.get(field) and report.get(field) != summary.get(field):
            failures.append(f"preflight_summary_field_mismatch:{field}")
    return failures


def _validate_diagnostic_smoke_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    report = _load_optional_json(view, "stage16b5_docker_diagnostic_smoke_report.json", failures)
    if not report:
        return failures
    if report.get("repo_harness_docker_diagnostic_session_passed") is not True:
        failures.append("diagnostic_smoke_not_passed")
    if report.get("diagnostic_session_backend") != "docker_persistent_container":
        failures.append("diagnostic_smoke_backend_not_docker_persistent_container")
    if report.get("run_dir_mount_enabled") is not False:
        failures.append("diagnostic_smoke_run_dir_mount_enabled_not_false")
    if report.get("git_visible_in_projection") is not False:
        failures.append("diagnostic_smoke_git_visible_in_projection_not_false")
    if report.get("workspace_projection_sync_status") != "completed":
        failures.append("diagnostic_smoke_workspace_projection_sync_not_completed")
    if report.get("valid_docker_diagnostic_sample_count") != summary.get("valid_docker_diagnostic_sample_count"):
        failures.append("diagnostic_smoke_valid_sample_count_mismatch")
    sample = report.get("sample")
    if not isinstance(sample, Mapping):
        failures.append("diagnostic_smoke_missing_sample")
    else:
        if sample.get("sample_destination") != "formal_online_rl_candidate":
            failures.append("diagnostic_smoke_sample_destination_not_formal_candidate")
        if sample.get("invalid_for_training") is not False:
            failures.append("diagnostic_smoke_sample_invalid_for_training_not_false")
        if sample.get("invalid_for_online_rl") is not False:
            failures.append("diagnostic_smoke_sample_invalid_for_online_rl_not_false")
        failures.extend(_validate_formal_candidate_sample(sample, prefix="diagnostic_smoke_sample"))
    return failures


def _validate_cleanup_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    report = _load_optional_json(view, "stage16b5_container_cleanup_report.json", failures)
    if not report:
        return failures
    for field in (
        "container_cleanup_passed",
        "background_process_cleanup_passed",
        "orphan_container_cleanup_passed",
        "no_session_owned_container_left_running",
    ):
        if report.get(field) is not True:
            failures.append(f"cleanup_report_{field}_not_true")
    if report.get("container_cleanup_status") != "completed":
        failures.append("cleanup_report_container_cleanup_status_not_completed")
    return failures


def _validate_formal_gate_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    report = _load_optional_json(view, "stage16b5_formal_online_rl_gate_report.json", failures)
    if not report:
        return failures
    if report.get("formal_online_rl_gate_passed") is not True:
        failures.append("formal_gate_report_not_passed")
    if _int(report.get("accepted_candidate_count")) < 1:
        failures.append("formal_gate_report_accepted_candidate_count_below_minimum")
    if _int(report.get("invalid_candidate_accepted_count")) != 0:
        failures.append("formal_gate_report_invalid_candidate_accepted_count_not_zero")
    if report.get("accepted_candidate_count") != summary.get("formal_online_rl_candidate_count"):
        failures.append("formal_gate_report_candidate_count_mismatch")
    if report.get("route") != "verl":
        failures.append("formal_gate_report_route_not_verl")
    if _int(report.get("generation_records_count")) < 1:
        failures.append("formal_gate_report_generation_records_count_below_minimum")
    if _int(report.get("response_ids_count")) < 1:
        failures.append("formal_gate_report_response_ids_count_below_minimum")
    if report.get("response_ids_count") != report.get("response_logprobs_count"):
        failures.append("formal_gate_report_response_logprobs_count_mismatch")
    if _int(report.get("response_spans_count")) < 1:
        failures.append("formal_gate_report_response_spans_count_below_minimum")
    if report.get("token_provenance_passed") is not True:
        failures.append("formal_gate_report_token_provenance_not_passed")
    if report.get("final_verifier_status") != "accepted":
        failures.append("formal_gate_report_final_verifier_not_accepted")
    if report.get("reward_boundary_passed") is not True:
        failures.append("formal_gate_report_reward_boundary_not_passed")
    if not isinstance(report.get("formal_sample_digest"), str) or not report.get("formal_sample_digest"):
        failures.append("formal_gate_report_missing_formal_sample_digest")
    smoke = _load_optional_json(view, "stage16b5_docker_diagnostic_smoke_report.json", failures)
    sample = smoke.get("sample") if isinstance(smoke, Mapping) else None
    if isinstance(sample, Mapping):
        if sample.get("generation_record_digest") != report.get("generation_record_digest"):
            failures.append("formal_gate_report_generation_record_digest_mismatch_smoke_sample")
        if sample.get("formal_sample_digest") != report.get("formal_sample_digest"):
            failures.append("formal_gate_report_formal_sample_digest_mismatch_smoke_sample")
        if sample.get("sample_id") and report.get("accepted_sample_id") and sample.get("sample_id") != report.get(
            "accepted_sample_id"
        ):
            failures.append("formal_gate_report_accepted_sample_id_mismatch_smoke_sample")
    return failures


def _validate_training_eligibility_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    report = _load_optional_json(view, "stage16b5_training_eligibility_report.json", failures)
    if not report:
        return failures
    if report.get("training_eligibility_gate_passed") is not True:
        failures.append("training_eligibility_report_not_passed")
    if _int(report.get("eligible_terminal_sample_count")) < 1:
        failures.append("training_eligibility_report_eligible_count_below_minimum")
    if _int(report.get("cleanup_failed_policy_loss_candidate_count")) != 0:
        failures.append("training_eligibility_cleanup_failed_candidate_not_zero")
    if _int(report.get("session_invalidated_policy_loss_candidate_count")) != 0:
        failures.append("training_eligibility_invalidated_candidate_not_zero")
    if _int(report.get("local_process_policy_loss_candidate_count")) != 0:
        failures.append("training_eligibility_local_process_candidate_not_zero")
    return failures


def _validate_negative_cases_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    report = _load_optional_json(view, "stage16b5_negative_cases_report.json", failures)
    if not report:
        return failures
    if report.get("negative_cases_passed") is not True:
        failures.append("negative_cases_report_not_passed")
    expected_counts = {
        "dependency_mutation_rejected_count": summary.get("dependency_mutation_rejected_count"),
        "hidden_path_rejected_count": summary.get("hidden_path_rejected_count"),
        "background_process_invalidated_count": summary.get("background_process_invalidated_count", 1),
    }
    for field, expected in expected_counts.items():
        if expected is not None and report.get(field) != expected:
            failures.append(f"negative_cases_report_{field}_mismatch")
    if _int(report.get("negative_policy_loss_candidate_count")) != 0:
        failures.append("negative_cases_report_policy_loss_candidate_not_zero")
    return failures


def _validate_path_redaction_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    report = _load_optional_json(view, "stage16b5_path_redaction_report.json", failures)
    if not report:
        return failures
    if report.get("path_leak_scan_passed") is not True:
        failures.append("path_redaction_report_path_leak_scan_not_passed")
    if report.get("public_path_leak_scan_passed") is not True:
        failures.append("path_redaction_report_public_path_leak_scan_not_passed")
    if report.get("path_leak_scan_passed") != summary.get("path_leak_scan_passed"):
        failures.append("path_redaction_report_path_leak_summary_mismatch")
    if report.get("public_path_leak_scan_passed") != summary.get("public_path_leak_scan_passed"):
        failures.append("path_redaction_report_public_path_leak_summary_mismatch")
    return failures


def _validate_shared_dependency_guard_report(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    report = _load_optional_json(view, "stage16b5_shared_dependency_guard_report.json", failures)
    if not report:
        return failures
    if report.get("shared_dependency_guard_passed") is not True:
        failures.append("shared_dependency_guard_report_not_passed")
    if _int(report.get("dependency_mutation_rejected_count")) < 1:
        failures.append("shared_dependency_guard_report_rejected_count_below_minimum")
    if report.get("dependency_mutation_rejected_count") != summary.get("dependency_mutation_rejected_count"):
        failures.append("shared_dependency_guard_report_rejected_count_mismatch")
    return failures


def _validate_concurrency_isolation_report(view: _EvidenceView) -> list[str]:
    failures: list[str] = []
    report = _load_optional_json(view, "stage16b5_concurrency_isolation_report.json", failures)
    if not report:
        return failures
    if report.get("concurrency_isolation_passed") is not True:
        failures.append("concurrency_isolation_report_not_passed")
    if _int(report.get("cross_session_workspace_leak_count")) != 0:
        failures.append("concurrency_isolation_cross_session_leak_count_not_zero")
    return failures


def _validate_remote_patch_manifest(view: _EvidenceView) -> list[str]:
    failures: list[str] = []
    report = _load_optional_json(view, "stage16b5_remote_patch_manifest.json", failures)
    if not report:
        return failures
    files = report.get("files")
    if not isinstance(files, list):
        failures.append("remote_patch_manifest_files_not_list")
        return failures
    for index, item in enumerate(files):
        if not isinstance(item, Mapping):
            failures.append(f"remote_patch_manifest_files[{index}]_not_object")
            continue
        for field in ("path", "sha256", "purpose", "enablement", "rollback"):
            if field not in item:
                failures.append(f"remote_patch_manifest_files[{index}]_missing_{field}")
        path = item.get("path")
        if isinstance(path, str):
            try:
                _normalize_relative_path(path)
            except RepoHarnessError:
                failures.append(f"remote_patch_manifest_files[{index}]_unsafe_path")
    return failures


def _validate_runtime_private_evidence(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if summary.get("runtime_private_evidence_present") is not True:
        return failures
    for relative in _ALLOWED_RUNTIME_PRIVATE_REFS:
        if not view.exists(relative):
            failures.append(f"missing_runtime_private_evidence:{relative}")
            continue
        if view.path(relative).stat().st_size <= 0:
            failures.append(f"empty_runtime_private_evidence:{relative}")
    for path in sorted((view.root / "runtime_private").rglob("run_status.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            failures.append(f"invalid_runtime_private_run_status:{path.relative_to(view.root).as_posix()}:{exc}")
            continue
        status = payload.get("status")
        if status == "RUNNING":
            failures.append(f"runtime_private_run_status_still_running:{path.relative_to(view.root).as_posix()}")
    return failures


def _validate_formal_candidate_sample(sample: Mapping[str, Any], *, prefix: str) -> list[str]:
    failures: list[str] = []
    if sample.get("route") != "verl":
        failures.append(f"{prefix}_route_not_verl")
    if _int(sample.get("generation_records_count")) < 1:
        failures.append(f"{prefix}_generation_records_count_below_minimum")
    if _int(sample.get("response_ids_count")) < 1:
        failures.append(f"{prefix}_response_ids_count_below_minimum")
    if sample.get("response_ids_count") != sample.get("response_logprobs_count"):
        failures.append(f"{prefix}_response_logprobs_count_mismatch")
    if _int(sample.get("response_spans_count")) < 1:
        failures.append(f"{prefix}_response_spans_count_below_minimum")
    if sample.get("token_provenance_passed") is not True:
        failures.append(f"{prefix}_token_provenance_not_passed")
    if sample.get("final_verifier_status") != "accepted":
        failures.append(f"{prefix}_final_verifier_not_accepted")
    if sample.get("reward_boundary_passed") is not True:
        failures.append(f"{prefix}_reward_boundary_not_passed")
    if not isinstance(sample.get("generation_record_digest"), str) or not sample.get("generation_record_digest"):
        failures.append(f"{prefix}_missing_generation_record_digest")
    if not isinstance(sample.get("formal_sample_digest"), str) or not sample.get("formal_sample_digest"):
        failures.append(f"{prefix}_missing_formal_sample_digest")
    return failures


def _validate_sha256_refs(view: _EvidenceView, summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    for field, relative in (
        ("remote_patch_manifest_sha256", "stage16b5_remote_patch_manifest.json"),
        ("fixture_manifest_sha256", "fixture_manifest.json"),
        ("fixture_sha256_report_sha256", "fixture_sha256_report.json"),
    ):
        expected = summary.get(field)
        if isinstance(expected, str) and expected:
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
    if summary.get("instance_final_status") not in {"stopped", "paused", "exited", "terminated"}:
        failures.append("assert_complete_instance_not_stopped_paused_exited_or_terminated")
    return failures


def _scan_public_evidence_for_leaks(view: _EvidenceView) -> list[str]:
    failures: list[str] = []
    for relative, path in view.iter_public_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        runtime_private_text = text
        if relative == "stage16b5_canonical_evidence_map.json":
            for allowed in _ALLOWED_RUNTIME_PRIVATE_REFS:
                runtime_private_text = runtime_private_text.replace(allowed, "")
        for pattern in _PATH_LEAK_PATTERNS:
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


def _int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    return 0


__all__ = [
    "STAGE16B5_CANONICAL_EVIDENCE_ITEMS",
    "Stage16B5DockerBackendAcceptanceInspectReport",
    "inspect_stage16b5_docker_backend_acceptance",
    "inspect_stage16b5_docker_backend_acceptance_report",
    "validate_stage16b5_evidence_tarball",
]
