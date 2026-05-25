from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from repo_harness.schema_base import stable_hash


CANONICAL_REPORT_FILES = (
    "stage16f6_case_manifest.json",
    "stage16f6_real_model_run_report.json",
    "stage16f6_projection_validation_report.json",
    "stage16f6_tool_and_context_report.json",
    "stage16f6_provider_route_policy_report.json",
    "stage16f6_patch_hygiene_report.json",
    "stage16f6_public_feedback_report.json",
    "stage16f6_docker_optional_report.json",
    "stage16f6_public_leak_scan_report.json",
    "stage16f6_test_report.json",
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_valid_stage16f6_evidence(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    private_items: list[dict[str, Any]] = []

    def write_private_artifact(kind: str, filename: str, content: bytes) -> tuple[str, str]:
        digest = sha256(content).hexdigest()
        relative_path = f"runtime_private/artifacts/{kind}/{digest}-{filename}"
        artifact_path = root / relative_path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(content)
        ref = f"runtime-private:{kind}:{digest}"
        private_items.append(
            {
                "ref": ref,
                "artifact_kind": kind,
                "sha256": digest,
                "relative_path": relative_path,
            }
        )
        return ref, digest

    cases = [
        {
            "case_id": "case-001",
            "task_ref": "tests/fixtures/tasks/task_stage16f3_passing.yaml",
            "task_sha256": "a" * 64,
            "run_config_ref": "tests/fixtures/run_configs/stage16f6_real_model_public_feedback.yaml",
            "run_config_sha256": "b" * 64,
            "entrypoint": "run_episode_task",
            "provider_name": "deepseek",
            "model_id": "deepseek-v4-pro",
            "execution_mode": "local_process",
            "docker_case": False,
            "expected_projection_complete": True,
            "expected_formal_online_rl_eligible": False,
            "expected_policy_loss_candidate": False,
        },
        {
            "case_id": "case-002",
            "task_ref": "tests/fixtures/tasks/task_001.yaml",
            "task_sha256": "c" * 64,
            "run_config_ref": "tests/fixtures/run_configs/stage16f6_real_model_patch.yaml",
            "run_config_sha256": "d" * 64,
            "entrypoint": "run_episode_task",
            "provider_name": "deepseek",
            "model_id": "deepseek-v4-pro",
            "execution_mode": "local_process",
            "docker_case": False,
            "expected_projection_complete": True,
            "expected_formal_online_rl_eligible": False,
            "expected_policy_loss_candidate": False,
        },
        {
            "case_id": "case-003",
            "task_ref": "tests/fixtures/tasks/task_stage14_negative_boundary.yaml",
            "task_sha256": "e" * 64,
            "run_config_ref": "tests/fixtures/run_configs/stage16f6_real_model_negative.yaml",
            "run_config_sha256": "f" * 64,
            "entrypoint": "run_episode_task",
            "provider_name": "deepseek",
            "model_id": "deepseek-v4-pro",
            "execution_mode": "local_process",
            "docker_case": False,
            "expected_projection_complete": True,
            "expected_formal_online_rl_eligible": False,
            "expected_policy_loss_candidate": False,
        },
    ]
    private_by_case: dict[str, dict[str, str]] = {}
    for case in cases:
        case_id = case["case_id"]
        compat_ref, compat_sha = write_private_artifact(
            "compat-projection",
            f"{case_id}.json",
            json.dumps({"case_id": case_id, "projection_complete": True}, sort_keys=True).encode("utf-8"),
        )
        final_patch_ref, final_patch_sha = write_private_artifact(
            "final-patch",
            f"{case_id}.patch",
            f"diff --git a/src/{case_id}.py b/src/{case_id}.py\n".encode("utf-8"),
        )
        final_diff_ref, final_diff_sha = write_private_artifact(
            "final-diff",
            f"{case_id}.diff",
            f"diff --git a/src/{case_id}.py b/src/{case_id}.py\n".encode("utf-8"),
        )
        hygiene_ref, hygiene_sha = write_private_artifact(
            "final-patch-hygiene-report",
            f"{case_id}.json",
            json.dumps(
                {
                    "case_id": case_id,
                    "cleaned_patch_sha256": final_patch_sha,
                    "cleaned_diff_sha256": final_diff_sha,
                },
                sort_keys=True,
            ).encode("utf-8"),
        )
        private_by_case[case_id] = {
            "compat_projection_ref": compat_ref,
            "compat_projection_sha256": compat_sha,
            "final_patch_ref": final_patch_ref,
            "final_patch_sha256": final_patch_sha,
            "final_diff_ref": final_diff_ref,
            "final_diff_sha256": final_diff_sha,
            "final_patch_hygiene_report_ref": hygiene_ref,
            "final_patch_hygiene_report_sha256": hygiene_sha,
        }

    write_json(
        root / "runtime_private" / "runtime_private_manifest.json",
        {
            "schema_version": "repo_harness_stage16f6_runtime_private_manifest_v0",
            "items": private_items,
        },
    )
    reports: dict[str, dict[str, Any]] = {
        "stage16f6_case_manifest.json": {
            "schema_version": "repo_harness_stage16f6_case_manifest_v0",
            "cases": cases,
        },
        "stage16f6_real_model_run_report.json": {
            "schema_version": "repo_harness_stage16f6_real_model_run_report_v0",
            "real_model_case_count": 3,
            "completed_real_model_episode_count": 3,
            "failed_real_model_episode_count": 0,
            "infrastructure_failure_count": 0,
            "provider_failure_count": 0,
            "provider_rate_limit_count": 0,
            "tool_error_count": 0,
            "run_episode_task_invocation_count": 3,
            "legacy_run_task_invocation_count": 0,
            "case_records": [
                {
                    "case_id": case["case_id"],
                    "run_id": f"stage16f6-{case['case_id']}",
                    "episode_completed": True,
                    "entrypoint_report_sha256": "1" * 64,
                    "episode_execution_spec_sha256": "2" * 64,
                    "compat_projection_sha256": private_by_case[case["case_id"]]["compat_projection_sha256"],
                    "final_status": "succeeded",
                    "status_reason": "completed",
                    "verifier_status": "accepted",
                    "reward_score": 1.0,
                    "patch_hygiene_status": "passed",
                    "provider_route": "deepseek",
                    "formal_online_rl_eligible": False,
                    "policy_loss_candidate": False,
                }
                for case in cases
            ],
        },
        "stage16f6_projection_validation_report.json": {
            "schema_version": "repo_harness_stage16f6_projection_validation_report_v0",
            "case_projection_results": [
                {
                    "case_id": case["case_id"],
                    "entrypoint": "run_episode_task",
                    "projection_complete": True,
                    "projection_validation_errors": [],
                    "compat_projection_ref": private_by_case[case["case_id"]]["compat_projection_ref"],
                    "compat_projection_sha256": private_by_case[case["case_id"]]["compat_projection_sha256"],
                    "final_patch_ref": private_by_case[case["case_id"]]["final_patch_ref"],
                    "final_patch_sha256": private_by_case[case["case_id"]]["final_patch_sha256"],
                    "final_diff_ref": private_by_case[case["case_id"]]["final_diff_ref"],
                    "final_diff_sha256": private_by_case[case["case_id"]]["final_diff_sha256"],
                    "final_patch_hygiene_report_ref": private_by_case[case["case_id"]][
                        "final_patch_hygiene_report_ref"
                    ],
                    "final_patch_hygiene_report_sha256": private_by_case[case["case_id"]][
                        "final_patch_hygiene_report_sha256"
                    ],
                }
                for case in cases
            ],
        },
        "stage16f6_tool_and_context_report.json": {
            "schema_version": "repo_harness_stage16f6_tool_and_context_report_v0",
            "public_environment_context_present": True,
            "public_environment_context_digest": "4" * 64,
            "tool_schema_snapshot_digest": "5" * 64,
            "allowed_tool_names": ["read_file", "edit_file", "run_tests"],
            "execute_bash_policy_summary": "stage16a_minimal_allowlist",
            "diagnostic_shell_enabled": False,
            "run_tests_feedback_policy": "public_only",
            "legacy_run_task_context_used": False,
        },
        "stage16f6_provider_route_policy_report.json": {
            "schema_version": "repo_harness_stage16f6_provider_route_policy_report_v0",
            "case_route_results": [
                {
                    "case_id": case["case_id"],
                    "provider_route": "deepseek",
                    "route_is_verl": False,
                    "formal_online_rl_eligible": False,
                    "policy_loss_candidate": False,
                    "training_data_eligibility_asserted": False,
                    "reason_not_policy_loss_candidate": "external_provider_missing_verl_token_provenance",
                }
                for case in cases
            ],
        },
        "stage16f6_patch_hygiene_report.json": {
            "schema_version": "repo_harness_stage16f6_patch_hygiene_report_v0",
            "case_patch_hygiene_results": [
                {
                    "case_id": case["case_id"],
                    "patch_hygiene_status": "passed",
                    "public_report_contains_raw_patch": False,
                    "final_patch_ref": private_by_case[case["case_id"]]["final_patch_ref"],
                    "final_patch_sha256": private_by_case[case["case_id"]]["final_patch_sha256"],
                    "final_diff_ref": private_by_case[case["case_id"]]["final_diff_ref"],
                    "final_diff_sha256": private_by_case[case["case_id"]]["final_diff_sha256"],
                    "final_patch_hygiene_report_ref": private_by_case[case["case_id"]][
                        "final_patch_hygiene_report_ref"
                    ],
                    "final_patch_hygiene_report_sha256": private_by_case[case["case_id"]][
                        "final_patch_hygiene_report_sha256"
                    ],
                    "cleaned_patch_sha256": private_by_case[case["case_id"]]["final_patch_sha256"],
                    "cleaned_diff_sha256": private_by_case[case["case_id"]]["final_diff_sha256"],
                    "cleaned_patch_empty": case["case_id"] != "case-002",
                }
                for case in cases
            ],
        },
        "stage16f6_public_feedback_report.json": {
            "schema_version": "repo_harness_stage16f6_public_feedback_report_v0",
            "public_feedback_enabled_case_count": 1,
            "public_feedback_observed_case_count": 1,
            "public_feedback_event_count": 1,
            "case_public_feedback_results": [
                {
                    "case_id": "case-001",
                    "public_feedback_enabled": True,
                    "public_feedback_observed": True,
                    "public_feedback_event_count": 1,
                    "run_tests_tool_call_observed": True,
                    "hidden_feedback_not_exposed": True,
                },
                {
                    "case_id": "case-002",
                    "public_feedback_enabled": False,
                    "public_feedback_observed": False,
                    "public_feedback_event_count": 0,
                    "run_tests_tool_call_observed": False,
                    "hidden_feedback_not_exposed": True,
                },
                {
                    "case_id": "case-003",
                    "public_feedback_enabled": False,
                    "public_feedback_observed": False,
                    "public_feedback_event_count": 0,
                    "run_tests_tool_call_observed": False,
                    "hidden_feedback_not_exposed": True,
                },
            ],
        },
        "stage16f6_docker_optional_report.json": {
            "schema_version": "repo_harness_stage16f6_docker_optional_report_v0",
            "docker_case_required": False,
            "docker_case_status": "skipped_not_required",
            "docker_daemon_available": True,
            "selected_image_ref": "repo-harness-v3-python:stage2",
            "selected_image_id": "sha256:" + "7" * 64,
            "selected_image_digest_status": "recorded",
            "swebench_cached_image_used": False,
            "reason_swebench_cached_image_not_used": "no_current_task_manifest_digest_verifier_binding",
        },
        "stage16f6_public_leak_scan_report.json": {
            "schema_version": "repo_harness_stage16f6_public_leak_scan_report_v0",
            "public_path_leak_scan_passed": True,
            "finding_count": 0,
            "findings": [],
        },
        "stage16f6_test_report.json": {
            "schema_version": "repo_harness_stage16f6_test_report_v0",
            "stage16f6_tests_status": "passed",
        },
    }
    for filename, payload in reports.items():
        write_json(root / filename, payload)

    evidence_map = {
        "schema_version": "repo_harness_stage16f6_canonical_evidence_map_v0",
        "items": [
            {
                "relative_path": filename,
                "sha256": stable_hash(reports[filename]),
                "artifact_kind": filename.removeprefix("stage16f6_").removesuffix(".json"),
                "required_for_assert_complete": True,
            }
            for filename in CANONICAL_REPORT_FILES
        ],
    }
    write_json(root / "stage16f6_canonical_evidence_map.json", evidence_map)
    summary = {
        "schema_version": "repo_harness_stage16f6_acceptance_summary_v0",
        "status": "passed",
        "stage16f6_complete": True,
        "ready_for_stage16_5": True,
        "ready_for_stage17_data_registry_planning": True,
        "real_model_case_count": 3,
        "completed_real_model_episode_count": 3,
        "projection_complete_count": 3,
        "legacy_run_task_invocation_count": 0,
        "policy_loss_candidate_count": 0,
        "external_provider_case_count": 3,
        "public_feedback_enabled_case_count": 1,
        "public_feedback_observed_case_count": 1,
        "public_feedback_event_count": 1,
        "docker_case_status": "skipped_not_required",
        "canonical_evidence_map_sha256": stable_hash(evidence_map),
        "public_path_leak_scan_passed": True,
        "provider_secret_leak_scan_passed": True,
        "blocking_reason_count": 0,
    }
    write_json(root / "stage16f6_acceptance_summary.json", summary)
    return summary


def refresh_evidence_map(root: Path) -> None:
    evidence_map_path = root / "stage16f6_canonical_evidence_map.json"
    evidence_map = read_json(evidence_map_path)
    for item in evidence_map["items"]:
        relative_path = item["relative_path"]
        item["sha256"] = stable_hash(read_json(root / relative_path))
    write_json(evidence_map_path, evidence_map)
    summary_path = root / "stage16f6_acceptance_summary.json"
    summary = read_json(summary_path)
    summary["canonical_evidence_map_sha256"] = stable_hash(evidence_map)
    write_json(summary_path, summary)
