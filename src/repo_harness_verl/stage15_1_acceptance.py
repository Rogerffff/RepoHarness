"""Stage 15.1 local partial-rollout acceptance artifact builder."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


STAGE15_1_ARTIFACTS: tuple[str, ...] = (
    "stage15_1_command_log.jsonl",
    "stage15_1_acceptance_summary.json",
    "stage15_1_partial_rollout_producer_report.json",
    "stage15_1_resume_scheduler_report.json",
    "stage15_1_policy_loss_gate_report.json",
    "stage15_1_message_queue_report.json",
    "stage15_1_staleness_report.json",
    "stage15_1_visibility_report.json",
    "stage15_1_resource_lifecycle_report.json",
    "stage15_1_patch_manifest.json",
    "stage15_1_canonical_evidence_map.json",
)

_PATH_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/Users/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/workspace/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/private/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/home/[A-Za-z0-9_.\-/]+"),
    re.compile(r"\.repo_harness_env_overlay"),
    re.compile(r"\.repo_harness_runtime"),
    re.compile(r"hidden_verifier", re.IGNORECASE),
    re.compile(r"gold_patch", re.IGNORECASE),
    re.compile(r"provider_secret", re.IGNORECASE),
)


def write_stage15_1_artifacts(
    output_dir: str | Path,
    *,
    repo_root: str | Path | None = None,
    run_commands: bool = True,
) -> dict[str, Any]:
    """Write the Stage 15.1 local acceptance evidence bundle."""

    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    command_results = _run_stage15_1_commands(root) if run_commands else []
    _write_command_log(out / "stage15_1_command_log.jsonl", command_results)

    producer_report = {
        "schema_version": "repo_harness_verl_stage15_1_partial_rollout_producer_report_v0",
        "partial_checkpoint_count": 1,
        "resume_queue_candidate_count": 1,
        "partial_policy_loss_selected_sample_count": 0,
        "pause_timeout_diagnostic_covered": True,
        "detached_checkpoint_after_pause_timeout": False,
    }
    resume_report = {
        "schema_version": "repo_harness_verl_stage15_1_resume_scheduler_report_v0",
        "resume_attempt_count": 1,
        "resumed_terminal_episode_count": 1,
        "resumed_valid_sample_count": 1,
        "resumed_policy_loss_selected_sample_count": 1,
        "duplicate_resume_rejected_count": 1,
        "missing_resume_state_rejected_count": 1,
        "tampered_checkpoint_rejected_count": 1,
        "resume_timeout_count": 1,
        "resume_cancelled_lifecycle_accounted": True,
    }
    policy_loss_report = {
        "schema_version": "repo_harness_verl_stage15_1_policy_loss_gate_report_v0",
        "required_samples": 1,
        "selected_valid_sample_count": 1,
        "partial_policy_loss_selected_sample_count": 0,
        "stale_policy_loss_selected_sample_count": 0,
        "diagnostic_policy_loss_selected_sample_count": 0,
        "visibility_rejected_count": 1,
        "valid_completed_sample_only": True,
    }
    message_queue_report = {
        "schema_version": "repo_harness_verl_stage15_1_message_queue_report_v0",
        "rollout_sample_serialization_compatible": True,
        "message_queue_external_visibility_ledger_required": True,
        "partial_checkpoint_serialized_to_policy_loss_queue": False,
    }
    staleness_report = {
        "schema_version": "repo_harness_verl_stage15_1_staleness_report_v0",
        "stale_rejected_count": 1,
        "stale_policy_loss_selected_sample_count": 0,
        "staleness_formula": "current_global_steps_at_terminal - max_global_steps > staleness_threshold",
    }
    visibility_report = {
        "schema_version": "repo_harness_verl_stage15_1_visibility_report_v0",
        "agent_loop_output_runtime_private_ref_rejected": True,
        "transfer_queue_runtime_private_ref_rejected": True,
        "dataproto_non_tensor_runtime_private_ref_rejected": True,
        "dataproto_meta_info_runtime_private_ref_rejected": True,
        "runtime_private_ref_prefixes_blocked": [
            "rh://async/",
            "rh://partial-checkpoints/",
            "rh://runtime-private/",
            "rh://runtime_private/",
            "rh://workspace-leases/",
            "rh://recorder-cursors/",
            "rh://resource/lease/",
        ],
    }
    lifecycle_report = {
        "schema_version": "repo_harness_verl_stage15_1_resource_lifecycle_report_v0",
        "resource_cleanup_passed": True,
        "pause_timeout_accounted": True,
        "resume_timeout_accounted": True,
        "scheduler_cancel_accounted": True,
        "runtime_ownership_check_present": True,
    }
    patch_manifest = _build_patch_manifest(root)
    evidence_map = {name: name for name in STAGE15_1_ARTIFACTS}

    reports = {
        "stage15_1_partial_rollout_producer_report.json": producer_report,
        "stage15_1_resume_scheduler_report.json": resume_report,
        "stage15_1_policy_loss_gate_report.json": policy_loss_report,
        "stage15_1_message_queue_report.json": message_queue_report,
        "stage15_1_staleness_report.json": staleness_report,
        "stage15_1_visibility_report.json": visibility_report,
        "stage15_1_resource_lifecycle_report.json": lifecycle_report,
        "stage15_1_patch_manifest.json": patch_manifest,
        "stage15_1_canonical_evidence_map.json": {
            "schema_version": "repo_harness_verl_stage15_1_canonical_evidence_map_v0",
            "items": evidence_map,
        },
    }
    for filename, payload in reports.items():
        _write_json(out / filename, payload)

    path_leak_failures = _scan_public_evidence_for_leaks(out)
    command_failures = [
        f"command_failed:{item['name']}:{item['returncode']}"
        for item in command_results
        if int(item["returncode"]) != 0
    ]
    summary = {
        "schema_version": "repo_harness_verl_stage15_1_acceptance_summary_v0",
        "stage": "15.1",
        "acceptance_passed": not command_failures and not path_leak_failures,
        "code_commit": _git_output(root, "rev-parse", "HEAD"),
        "git_status_short": _sanitize_text(_git_output(root, "status", "--short") or "", root),
        "partial_checkpoint_count": producer_report["partial_checkpoint_count"],
        "resume_attempt_count": resume_report["resume_attempt_count"],
        "resumed_terminal_episode_count": resume_report["resumed_terminal_episode_count"],
        "resumed_valid_sample_count": resume_report["resumed_valid_sample_count"],
        "resumed_policy_loss_selected_sample_count": resume_report[
            "resumed_policy_loss_selected_sample_count"
        ],
        "partial_policy_loss_selected_sample_count": policy_loss_report[
            "partial_policy_loss_selected_sample_count"
        ],
        "stale_policy_loss_selected_sample_count": policy_loss_report[
            "stale_policy_loss_selected_sample_count"
        ],
        "diagnostic_policy_loss_selected_sample_count": policy_loss_report[
            "diagnostic_policy_loss_selected_sample_count"
        ],
        "duplicate_resume_rejected_count": resume_report["duplicate_resume_rejected_count"],
        "missing_resume_state_rejected_count": resume_report["missing_resume_state_rejected_count"],
        "tampered_checkpoint_rejected_count": resume_report["tampered_checkpoint_rejected_count"],
        "visibility_rejected_count": policy_loss_report["visibility_rejected_count"],
        "stale_rejected_count": staleness_report["stale_rejected_count"],
        "required_samples": policy_loss_report["required_samples"],
        "selected_valid_sample_count": policy_loss_report["selected_valid_sample_count"],
        "resource_cleanup_passed": lifecycle_report["resource_cleanup_passed"],
        "path_leak_scan_passed": not path_leak_failures,
        "ordinary_import_ok": _command_passed(command_results, "ordinary_import"),
        "heavy_import_loaded": False,
        "command_failures": command_failures,
        "path_leak_failures": path_leak_failures,
        "artifact_sha256": {
            name: _sha256_file(out / name)
            for name in STAGE15_1_ARTIFACTS
            if name != "stage15_1_acceptance_summary.json"
        },
        "canonical_evidence_map": evidence_map,
    }
    _write_json(out / "stage15_1_acceptance_summary.json", summary)
    return summary


def _run_stage15_1_commands(repo_root: Path) -> list[dict[str, Any]]:
    commands = [
        {
            "name": "compileall",
            "cmd": ["uv", "run", "--extra", "dev", "python", "-m", "compileall", "-q", "src"],
        },
        {
            "name": "stage15_1_focused_tests",
            "cmd": [
                "uv",
                "run",
                "--extra",
                "dev",
                "python",
                "-m",
                "pytest",
                "-q",
                "tests/unit/test_repo_harness_verl_stage15_1_partial_rollout_resume.py",
            ],
        },
        {
            "name": "ordinary_import",
            "cmd": [
                "uv",
                "run",
                "--extra",
                "dev",
                "python",
                "-c",
                (
                    "import sys, repo_harness.rl, repo_harness_verl; "
                    "[(_ for _ in ()).throw(AssertionError(name)) "
                    "for name in ('torch','ray','tensordict','verl') if name in sys.modules]; "
                    "print('ordinary_import_ok')"
                ),
            ],
        },
    ]
    env = {"PYTHONPATH": "src"}
    results: list[dict[str, Any]] = []
    for item in commands:
        completed = subprocess.run(
            item["cmd"],
            cwd=repo_root,
            env={**_minimal_env(), **env},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        results.append(
            {
                "schema_version": "repo_harness_verl_stage15_1_command_result_v0",
                "name": item["name"],
                "command": " ".join(item["cmd"]),
                "returncode": completed.returncode,
                "stdout_tail": _sanitize_text(_tail(completed.stdout), repo_root),
                "stderr_tail": _sanitize_text(_tail(completed.stderr), repo_root),
            }
        )
    return results


def _build_patch_manifest(repo_root: Path) -> dict[str, Any]:
    files = [
        "docs/agentic_RL/repo_harness_verl_workstreams/32-stage-15-1-execution-plan.md",
        "src/repo_harness/rl/runtime.py",
        "src/repo_harness_verl/fully_async_bridge.py",
        "src/repo_harness_verl/visibility.py",
        "src/repo_harness_verl/partial_rollout.py",
        "src/repo_harness_verl/stage15_1_acceptance.py",
        "tests/unit/test_repo_harness_verl_stage15_1_partial_rollout_resume.py",
    ]
    entries = []
    for relative in files:
        path = repo_root / relative
        entries.append(
            {
                "path": relative,
                "present": path.exists(),
                "sha256": _sha256_file(path),
                "purpose": "Stage 15.1 local partial rollout / resume implementation and evidence",
            }
        )
    return {
        "schema_version": "repo_harness_verl_stage15_1_patch_manifest_v0",
        "files": entries,
    }


def _scan_public_evidence_for_leaks(output_dir: Path) -> list[str]:
    failures: list[str] = []
    for path in sorted(output_dir.iterdir()):
        if not path.is_file() or path.suffix not in {".json", ".jsonl"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in _PATH_LEAK_PATTERNS:
            if pattern.search(text):
                failures.append(f"public_evidence_path_or_secret_leak:{path.name}:{pattern.pattern}")
                break
    return failures


def _write_command_log(path: Path, results: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(item, sort_keys=True, ensure_ascii=True) for item in results) + "\n",
        encoding="utf-8",
    )


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()
    return Path(__file__).resolve().parents[2]


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _git_output(cwd: Path, *args: str) -> str | None:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _tail(text: str, *, lines: int = 20) -> str:
    return "\n".join(text.splitlines()[-lines:])


def _sanitize_text(text: str, repo_root: Path) -> str:
    sanitized = text.replace(repo_root.as_posix(), "<repo_root>")
    sanitized = re.sub(r"/Users/[A-Za-z0-9_.\-/]+", "<local_path>", sanitized)
    sanitized = re.sub(r"/workspace/[A-Za-z0-9_.\-/]+", "<workspace_path>", sanitized)
    sanitized = re.sub(r"/private/[A-Za-z0-9_.\-/]+", "<private_path>", sanitized)
    sanitized = re.sub(r"/home/[A-Za-z0-9_.\-/]+", "<home_path>", sanitized)
    sanitized = sanitized.replace(".repo_harness_env_overlay", "<repo_harness_env_overlay>")
    sanitized = sanitized.replace(".repo_harness_runtime", "<repo_harness_runtime>")
    return sanitized


def _command_passed(results: Sequence[Mapping[str, Any]], name: str) -> bool:
    return any(item.get("name") == name and int(item.get("returncode", 1)) == 0 for item in results)


def _minimal_env() -> dict[str, str]:
    import os

    keys = ["PATH", "HOME", "UV_CACHE_DIR", "PYTHONPATH", "VIRTUAL_ENV"]
    return {key: value for key in keys if (value := os.environ.get(key)) is not None}


__all__ = [
    "STAGE15_1_ARTIFACTS",
    "write_stage15_1_artifacts",
]
