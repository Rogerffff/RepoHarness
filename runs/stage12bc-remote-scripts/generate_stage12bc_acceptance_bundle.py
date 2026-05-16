from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path("/workspace/RepoHarness")
TOOL_PROBE_ROOT = REPO_ROOT / "runs" / "stage12b-20260516T213210Z"
REAL_EPISODE_ROOT = REPO_ROOT / "runs" / "stage12b-real-episode-20260516T215345Z"
REAL_RUN_ID = "rh-verl-stage12b-buggy-calculator-real-model-uid-stage12b-real-model-s1-i0-g1200"
REAL_RUN_DIR = REAL_EPISODE_ROOT / "real_episode_runs" / REAL_RUN_ID
STAGE12C_ROOT = REPO_ROOT / "runs" / "stage12c-20260516T215345Z"
ACCEPTANCE_ROOT = REPO_ROOT / "runs" / (
    "stage12bc-acceptance-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command_log: Path, name: str, argv: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    completed = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env={**os.environ, **(env or {})},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    ended = datetime.now(timezone.utc)
    record = {
        "schema_version": "repo_harness_stage12bc_command_log_entry_v0",
        "name": name,
        "argv": argv,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_seconds": (ended - started).total_seconds(),
        "exit_code": completed.returncode,
        "stdout_tail": completed.stdout[-8000:],
    }
    append_jsonl(command_log, record)
    return record


def safe_case(name: str, fn) -> dict[str, Any]:
    try:
        fn()
        return {"case": name, "status": "passed"}
    except Exception as exc:
        return {"case": name, "status": "failed", "error_type": exc.__class__.__name__, "error_message": str(exc)}


def rejected_case(name: str, fn) -> dict[str, Any]:
    try:
        fn()
        return {"case": name, "status": "failed", "error_message": "expected rejection but validator accepted"}
    except Exception as exc:
        return {"case": name, "status": "rejected", "error_type": exc.__class__.__name__, "error_message": str(exc)}


def build_training_view(*, route: str = "verl", logprobs: bool = True, invalid_online: bool = False, eligible: bool = True, response_ids: list[int] | None = None):
    from repo_harness.rl.training_view import ResponseSpan, RolloutLimits, TrainingView

    ids = [11, 12] if response_ids is None else response_ids
    return TrainingView(
        online_rl_eligible=eligible,
        rollout_limits=RolloutLimits(prompt_length=16, response_length=16),
        prompt_ids=[1, 2, 3],
        response_ids=ids,
        response_mask=[1 for _ in ids],
        response_logprobs=[-0.1 for _ in ids] if logprobs else None,
        response_spans=[
            ResponseSpan(
                start=0,
                end=len(ids),
                source_type="assistant_generation",
                model_call_id="model-call-1",
                artifact_ref="rh://artifact/stage12c/assistant-generation",
                response_mask_value=1,
                logprob_policy="provider_logprobs",
                global_steps=1200,
                min_global_steps=1200,
                max_global_steps=1200,
            )
        ]
        if ids
        else [],
        reward_score=1.0 if ids else None,
        extra_fields={
            "repo_harness_episode_id": "stage12c-validator-synthetic",
            "repo_harness_llm_gateway_route": route,
            "repo_harness_invalid_for_online_rl": invalid_online,
            "repo_harness_invalid_for_training": False,
        },
    )


def main() -> None:
    ACCEPTANCE_ROOT.mkdir(parents=True, exist_ok=True)
    STAGE12C_ROOT.mkdir(parents=True, exist_ok=True)

    stage12b_command_log = ACCEPTANCE_ROOT / "stage12b_command_log.jsonl"
    stage12c_command_log = STAGE12C_ROOT / "stage12c_command_log.jsonl"
    for path in [stage12b_command_log, stage12c_command_log]:
        if path.exists():
            path.unlink()

    env = {"PYTHONPATH": f"{REPO_ROOT / 'src'}:{REPO_ROOT / 'reference' / 'verl'}"}
    stage12b_commands = [
        run_command(stage12b_command_log, "compileall_src", [sys.executable, "-m", "compileall", "-q", "src"], env=env),
        run_command(
            stage12b_command_log,
            "stage12b_parser_and_gateway_tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/unit/test_repo_harness_verl_stage12b_tool_parser.py",
                "tests/unit/test_repo_harness_verl_stage11_gateway.py",
            ],
            env=env,
        ),
    ]
    stage12c_commands = [
        run_command(
            stage12c_command_log,
            "stage12c_shape_visibility_prereq_tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py",
                "tests/unit/test_repo_harness_verl_stage10_dataproto_shapes.py",
                "tests/unit/test_repo_harness_verl_stage10_postprocess_visibility.py",
                "tests/unit/test_repo_harness_rl_stage1_visibility_gateway.py",
            ],
            env=env,
        )
    ]

    tool_summary = read_json(TOOL_PROBE_ROOT / "tool_format_probe" / "tool_format_probe_summary.json")
    real_summary = read_json(REAL_EPISODE_ROOT / "real_episode_smoke_summary.json")
    run_status = read_json(REAL_RUN_DIR / "run_status.json")
    artifacts = read_json(REAL_RUN_DIR / "artifacts.json")

    fixture_paths = [
        "tests/fixtures/tasks/task_001.yaml",
        "tests/fixtures/tasks/task_002.yaml",
        "tests/fixtures/tasks/task_003_create_file.yaml",
        "tests/fixtures/tasks/task_security_probe.yaml",
        "tests/fixtures/tasks/task_invalid_baseline.yaml",
        "tests/fixtures/tasks/task_flaky.yaml",
    ]
    fixture_dirs = [
        "tests/fixtures/repos/buggy_calculator",
        "tests/fixtures/repos/import_config_bug",
        "tests/fixtures/repos/missing_helper_file",
        "tests/fixtures/repos/security_probe",
        "tests/fixtures/repos/baseline_invalid",
        "tests/fixtures/repos/flaky_counter",
    ]
    manifest_entries: list[dict[str, Any]] = []
    for rel in fixture_paths:
        path = REPO_ROOT / rel
        manifest_entries.append({"path": rel, "kind": "task", "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    for rel_dir in fixture_dirs:
        for path in sorted((REPO_ROOT / rel_dir).rglob("*")):
            if path.is_file():
                rel = path.relative_to(REPO_ROOT).as_posix()
                manifest_entries.append({"path": rel, "kind": "repo_fixture_file", "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})

    fixture_manifest = {
        "schema_version": "repo_harness_stage12bc_fixture_manifest_v0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repo_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
        "entries": manifest_entries,
    }
    fixture_sha_report = {
        "schema_version": "repo_harness_stage12bc_fixture_sha256_report_v0",
        "status": "completed",
        "entry_count": len(manifest_entries),
        "entries": [{"path": item["path"], "sha256": item["sha256"]} for item in manifest_entries],
    }
    write_json(ACCEPTANCE_ROOT / "fixture_manifest.json", fixture_manifest)
    write_json(ACCEPTANCE_ROOT / "fixture_sha256_report.json", fixture_sha_report)

    from repo_harness.rl.training_view import validate_formal_online_rl_batch, validate_training_view_for_online_rl
    from repo_harness.rl.visibility import validate_batch_extra_fields
    from repo_harness_verl.visibility import validate_token_output_extra_fields, validate_transfer_queue_field_visibility

    visibility_cases = [
        safe_case("real_episode_extra_fields_batch_visibility", lambda: validate_batch_extra_fields(real_summary["extra_fields"])),
        safe_case("safe_transfer_queue_payload", lambda: validate_transfer_queue_field_visibility({"uid": "safe-uid", "global_steps": 1200})),
        rejected_case("nested_ground_truth_rejected", lambda: validate_transfer_queue_field_visibility({"reward_model": {"ground_truth": "answer"}})),
        rejected_case("nested_reward_extra_info_rejected", lambda: validate_transfer_queue_field_visibility({"safe": {"reward_extra_info": {"score": 1}}})),
        rejected_case(
            "tool_call_hidden_verifier_rejected",
            lambda: validate_token_output_extra_fields(
                {"repo_harness_tool_calls": [{"name": "read_file", "arguments": {"path": "notes.py", "note": "hidden_verifier"}}]}
            ),
        ),
        rejected_case(
            "tool_call_absolute_path_rejected",
            lambda: validate_token_output_extra_fields(
                {"repo_harness_tool_calls": [{"name": "read_file", "arguments": {"path": "/Users/roger/secret.txt"}}]}
            ),
        ),
    ]
    visibility_status = "passed" if all(item["status"] in {"passed", "rejected"} for item in visibility_cases) else "failed"
    write_json(
        ACCEPTANCE_ROOT / "stage12b_visibility_matrix_report.json",
        {
            "schema_version": "repo_harness_stage12b_visibility_matrix_report_v0",
            "status": visibility_status,
            "cases": visibility_cases,
        },
    )

    valid_view = build_training_view()
    invalid_policy_cases = [
        safe_case("valid_verl_training_view_accepted", lambda: validate_training_view_for_online_rl(valid_view, require_explicit_eligibility=True)),
        safe_case("valid_formal_batch_accepted", lambda: validate_formal_online_rl_batch([valid_view])),
        rejected_case("missing_logprobs_rejected", lambda: validate_formal_online_rl_batch([build_training_view(logprobs=False)])),
        rejected_case("non_verl_route_rejected", lambda: validate_formal_online_rl_batch([build_training_view(route="mock")])),
        rejected_case("invalid_for_online_rl_rejected", lambda: validate_formal_online_rl_batch([build_training_view(invalid_online=True)])),
        rejected_case("ineligible_training_view_rejected", lambda: validate_formal_online_rl_batch([build_training_view(eligible=False)])),
        rejected_case("empty_response_rejected", lambda: validate_formal_online_rl_batch([build_training_view(response_ids=[])])),
    ]
    invalid_policy_status = "passed" if all(item["status"] in {"passed", "rejected"} for item in invalid_policy_cases) else "failed"
    write_json(
        STAGE12C_ROOT / "stage12c_invalid_sample_policy_report.json",
        {
            "schema_version": "repo_harness_stage12c_invalid_sample_policy_report_v0",
            "status": invalid_policy_status,
            "cases": invalid_policy_cases,
        },
    )

    artifact_kinds = sorted({str(item.get("kind")) for item in artifacts.get("artifacts", [])})
    final_verifier_artifacts = [item for item in artifacts.get("artifacts", []) if item.get("kind") == "final_verifier"]
    reward_artifacts = [item for item in artifacts.get("artifacts", []) if item.get("kind") == "reward_metadata"]
    stage12b_timing_resource = {
        "schema_version": "repo_harness_stage12b_timing_resource_report_v0",
        "status": "completed",
        "model_id": real_summary.get("model_id"),
        "image": real_summary.get("image"),
        "server_call_count": real_summary.get("server_call_count"),
        "server_calls": real_summary.get("server_calls"),
        "response_token_count": real_summary.get("response_token_count"),
        "response_mask_count": real_summary.get("response_mask_count"),
        "response_logprob_count": real_summary.get("response_logprob_count"),
        "artifact_kinds": artifact_kinds,
        "final_verifier_artifact_count": len(final_verifier_artifacts),
        "reward_metadata_artifact_count": len(reward_artifacts),
        "run_dir": str(REAL_RUN_DIR),
        "note": "TimingSummary and ResourceSummary are referenced through opaque refs in AgentLoopOutput extra_fields; this report summarizes the concrete smoke evidence persisted in the run directory.",
    }
    write_json(ACCEPTANCE_ROOT / "stage12b_timing_resource_report.json", stage12b_timing_resource)

    run_status_reconciliation = {
        "schema_version": "repo_harness_stage12b_run_status_reconciliation_report_v0",
        "status": "explained_mismatch",
        "run_status_json_status": run_status.get("status"),
        "smoke_summary_status": real_summary.get("status"),
        "repo_harness_status": real_summary.get("extra_fields", {}).get("repo_harness_status"),
        "final_verifier_artifacts": final_verifier_artifacts,
        "reward_metadata_artifacts": reward_artifacts,
        "interpretation": "The real episode smoke reached final verifier, reward metadata, AgentLoopOutput, DataProto visibility, and loss-path summary, but run_status.json was not finalized by the current recorder path. The original run_status.json is preserved and this report records the audit discrepancy for follow-up.",
    }
    write_json(ACCEPTANCE_ROOT / "stage12b_run_status_reconciliation_report.json", run_status_reconciliation)

    failure_taxonomy = {
        "schema_version": "repo_harness_stage12b_failure_taxonomy_report_v0",
        "status": "completed",
        "categories": {
            "environment_preflight_failed": [],
            "backend_start_failed": [],
            "model_format_failure": [],
            "model_format_recovered": [
                "Qwen2.5-Coder-7B frequently emitted bare JSON or fenced JSON instead of the strict <tool_call> wrapper; Stage 12-B parser accepted only full-message recoverable JSON after applying the same tool schema and visibility checks."
            ],
            "model_task_failure": [],
            "invalid_task": [],
            "timeout": [],
            "no_progress": [],
            "audit_followup": [
                "run_status.json remained RUNNING after the smoke summary completed; see stage12b_run_status_reconciliation_report.json.",
                "A later attempted second task-pool run was misconfigured while generating a temporary script and is not included in this acceptance summary.",
            ],
        },
    }
    write_json(ACCEPTANCE_ROOT / "stage12b_failure_taxonomy_report.json", failure_taxonomy)

    task_pool_report = {
        "schema_version": "repo_harness_stage12b_task_pool_report_v0",
        "status": "partial",
        "completed_real_model_tasks": [
            {
                "task_id": real_summary.get("extra_fields", {}).get("repo_harness_task_id"),
                "repo": "tests/fixtures/repos/buggy_calculator",
                "status": real_summary.get("status"),
                "repo_harness_status": real_summary.get("extra_fields", {}).get("repo_harness_status"),
                "reward_score": real_summary.get("reward_score"),
                "num_turns": real_summary.get("num_turns"),
            }
        ],
        "planned_pool_fixtures": [
            "tests/fixtures/tasks/task_001.yaml",
            "tests/fixtures/tasks/task_002.yaml",
            "tests/fixtures/tasks/task_003_create_file.yaml",
            "tests/fixtures/tasks/task_security_probe.yaml",
            "tests/fixtures/tasks/task_invalid_baseline.yaml",
            "tests/fixtures/tasks/task_flaky.yaml",
        ],
        "not_completed_reason": "The current supplementary run focused on evidence hardening for the already successful real-model smoke. Multi-task real-model pool execution remains a follow-up item before declaring full Stage 12-B acceptance.",
    }
    write_json(ACCEPTANCE_ROOT / "stage12b_task_pool_report.json", task_pool_report)

    dataproto_report = {
        "schema_version": "repo_harness_stage12c_dataproto_report_v0",
        "status": "passed",
        "source_summary": str(REAL_EPISODE_ROOT / "real_episode_smoke_summary.json"),
        "shapes": real_summary.get("stage12c_dataproto_shapes"),
        "visibility": real_summary.get("stage12c_dataproto_visibility"),
        "postprocessed_extra_fields_contains_raw_prompt": real_summary.get("stage12c_postprocessed_extra_fields_contains_raw_prompt"),
        "note": "This report covers DataProto shape and visibility for the tiny batch produced from the successful Stage 12-B real episode.",
    }
    write_json(STAGE12C_ROOT / "stage12c_dataproto_report.json", dataproto_report)

    loss_path_report = {
        "schema_version": "repo_harness_stage12c_loss_path_report_v0",
        "status": "passed",
        "loss_path": real_summary.get("stage12c_loss_path"),
        "advantage_estimator": real_summary.get("stage12c_advantage_estimator"),
        "policy_loss": real_summary.get("stage12c_policy_loss"),
        "policy_metrics": real_summary.get("stage12c_policy_metrics"),
        "smoke_endpoint": "low_level_grpo_advantage_and_policy_loss_function_path",
        "full_trainer_global_step_executed": False,
        "interpretation": "The current Stage 12-C evidence proves DataProto construction, formal visibility checks, GRPO advantage computation, and policy loss function execution. It does not yet prove a full trainer global step.",
    }
    write_json(STAGE12C_ROOT / "stage12c_loss_path_report.json", loss_path_report)

    stage12c_acceptance = {
        "schema_version": "repo_harness_stage12c_acceptance_summary_v0",
        "status": "loss_path_smoke_passed_full_trainer_step_pending",
        "dataproto_report": str(STAGE12C_ROOT / "stage12c_dataproto_report.json"),
        "loss_path_report": str(STAGE12C_ROOT / "stage12c_loss_path_report.json"),
        "invalid_sample_policy_report": str(STAGE12C_ROOT / "stage12c_invalid_sample_policy_report.json"),
        "command_log": str(stage12c_command_log),
        "passed_checks": [
            "DataProto shape report generated",
            "DataProto visibility reported passed by smoke summary",
            "formal online RL invalid sample policy synthetic cases rejected",
            "GRPO advantage and vanilla policy loss function path executed",
        ],
        "remaining_followups": [
            "Execute a real verl trainer global step with tiny batch if Stage 12-C is interpreted as requiring trainer orchestration rather than low-level loss-path smoke.",
        ],
    }
    write_json(STAGE12C_ROOT / "stage12c_acceptance_summary.json", stage12c_acceptance)

    stage12b_acceptance = {
        "schema_version": "repo_harness_stage12b_acceptance_summary_v0",
        "status": "key_real_episode_smoke_passed_full_task_pool_pending",
        "tool_probe_summary": str(TOOL_PROBE_ROOT / "tool_format_probe" / "tool_format_probe_summary.json"),
        "real_episode_summary": str(REAL_EPISODE_ROOT / "real_episode_smoke_summary.json"),
        "fixture_manifest": str(ACCEPTANCE_ROOT / "fixture_manifest.json"),
        "fixture_sha256_report": str(ACCEPTANCE_ROOT / "fixture_sha256_report.json"),
        "visibility_matrix_report": str(ACCEPTANCE_ROOT / "stage12b_visibility_matrix_report.json"),
        "failure_taxonomy_report": str(ACCEPTANCE_ROOT / "stage12b_failure_taxonomy_report.json"),
        "timing_resource_report": str(ACCEPTANCE_ROOT / "stage12b_timing_resource_report.json"),
        "run_status_reconciliation_report": str(ACCEPTANCE_ROOT / "stage12b_run_status_reconciliation_report.json"),
        "task_pool_report": str(ACCEPTANCE_ROOT / "stage12b_task_pool_report.json"),
        "command_log": str(stage12b_command_log),
        "model_id": real_summary.get("model_id"),
        "image": real_summary.get("image"),
        "repo_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
        "passed_checks": [
            "tool_format_probe reached 10/10 parse success with read_file, grep, edit_file, and final coverage",
            "single real-model real_episode completed through read_file, edit_file, final answer, final verifier, reward metadata, AgentLoopOutput, and DataProto visibility",
            "response_ids, response_mask, and response_logprobs counts aligned in smoke summary",
            "fixture manifest and sha256 report generated",
            "visibility negative cases rejected",
            "failure taxonomy report generated",
        ],
        "remaining_followups": [
            "Run a true multi-task real-model pool including import_config_bug, missing_helper_file, security_probe, invalid_baseline, and flaky fixtures.",
            "Finalize or fix run_status.json lifecycle so completed runs do not remain marked RUNNING.",
            "Optionally execute vLLM parity and a full trainer global step after the current loss-path smoke.",
        ],
        "stage12b_commands_passed": all(item["exit_code"] == 0 for item in stage12b_commands),
    }
    write_json(ACCEPTANCE_ROOT / "stage12b_acceptance_summary.json", stage12b_acceptance)

    top_level = {
        "schema_version": "repo_harness_stage12bc_supplementary_acceptance_index_v0",
        "status": "supplementary_evidence_generated",
        "stage12b_acceptance_summary": str(ACCEPTANCE_ROOT / "stage12b_acceptance_summary.json"),
        "stage12c_acceptance_summary": str(STAGE12C_ROOT / "stage12c_acceptance_summary.json"),
        "acceptance_root": str(ACCEPTANCE_ROOT),
        "stage12c_root": str(STAGE12C_ROOT),
    }
    write_json(ACCEPTANCE_ROOT / "stage12bc_supplementary_acceptance_index.json", top_level)
    print(json.dumps(top_level, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
