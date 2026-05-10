from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.config import RunConfig
from repo_harness.context.schemas import ContextPolicySnapshot
from repo_harness.evaluation import BaselineResult
from repo_harness.run_metadata.fingerprint import (
    build_local_environment_fingerprint,
    compute_source_tree_hash,
)
from repo_harness.run_metadata.schemas import FailureCategory, FailureType
from repo_harness.run_metadata.tool_snapshot import write_tool_schema_snapshot
from repo_harness.run_metadata.writer import (
    _failure_diagnostics,
    _model_call_summary,
    build_run_config_facts,
    build_run_metadata,
    write_run_config_facts,
    write_run_metadata,
)
from repo_harness.tasks import TaskDefinition
from repo_harness.trajectory import RunRecorder
from repo_harness.workspace import DependencyState

from tests.unit.test_task_schema import valid_task_payload


def _artifact_ref(*, artifact_id: str, relative_path: str, kind: str) -> dict[str, object]:
    return {
        "schema_version": "repo_harness_artifact_v0",
        "artifact_id": artifact_id,
        "relative_path": relative_path,
        "kind": kind,
        "sha256": "0" * 64,
        "size_bytes": 1,
        "redaction_status": "not_sensitive",
        "retention_policy": "context_compaction_audit",
    }


def _write_context_policy_fact(run_dir: Path) -> None:
    (run_dir / "run_config_facts.json").write_text(
        json.dumps(
            {
                "context_policy_snapshot": {
                    "local_context_limit_policy": "strict_local_preflight",
                    "reactive_compact_policy": "provider_verified_reactive",
                },
                "effective_context_budget_tokens": 930000,
                "hard_context_limit_tokens": 970000,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_ptl_record_artifact(
    run_dir: Path,
    *,
    artifact_id: str,
    synthetic_marker_id: str,
    omitted_round_count: int,
    retained_round_count: int,
    token_estimate_before: int,
    token_estimate_after: int,
    hard_context_limit_tokens: int,
) -> dict[str, object]:
    relative_path = f"artifacts/{artifact_id}.json"
    payload = {
        "schema_version": "repo_harness_ptl_truncation_record_v1",
        "original_model_call_id": "run_model_call_original",
        "synthetic_marker_id": synthetic_marker_id,
        "omitted_round_count": omitted_round_count,
        "retained_round_count": retained_round_count,
        "token_estimate_before": token_estimate_before,
        "token_estimate_after": token_estimate_after,
        "hard_context_limit_tokens": hard_context_limit_tokens,
        "post_truncation_above_hard_limit": (
            token_estimate_after > hard_context_limit_tokens
        ),
    }
    artifact_path = run_dir / relative_path
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return _artifact_ref(
        artifact_id=artifact_id,
        relative_path=relative_path,
        kind="ptl_truncation_record",
    )


def test_source_tree_hash_excludes_git_and_cache_dirs(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (source / ".git").mkdir()
    (source / ".git" / "HEAD").write_text("ignored\n", encoding="utf-8")
    first = compute_source_tree_hash(source)

    (source / ".git" / "HEAD").write_text("changed but ignored\n", encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "app.pyc").write_bytes(b"ignored")
    second = compute_source_tree_hash(source)

    assert first == second


def test_run_config_facts_and_metadata_are_written_as_root_fact_files(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    task = TaskDefinition.model_validate(valid_task_payload())
    source = tmp_path / "source"
    source.mkdir()
    (source / "calculator.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    with RunRecorder("run_001", run_dir, task_id=task.id) as recorder:
        _, _, tool_protocol = write_tool_schema_snapshot(recorder)
        dependency_state_ref = recorder.write_json_artifact(
            "dependency_state",
            DependencyState().model_dump(mode="json"),
            {"budget_policy": "preserve_json"},
        )
        fingerprint = build_local_environment_fingerprint(
            task_definition=task,
            source_checkout=source,
            dependency_state=DependencyState(),
            dependency_state_ref=dependency_state_ref,
            command_timeout_sec=120,
            network_policy="deny_agent_run",
        )
        facts = build_run_config_facts(
            run_id="run_001",
            task_definition=task,
            config=RunConfig(),
            tool_protocol=tool_protocol,
            environment_fingerprint=fingerprint,
        )
        facts_ref = write_run_config_facts(run_dir, facts)
        (run_dir / "metrics.json").write_text(
            json.dumps(
                {
                    "run_outcome": "success",
                    "final_verifier_status": "accepted",
                    "task_success": True,
                    "turn_count": 1,
                    "tool_call_count": 1,
                    "test_run_count": 1,
                    "interaction_efficiency": {"final_verifier_mode": "strict_patch_replay"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (run_dir / "verifier.json").write_text(
            json.dumps({"verifier_stage": "final", "accepted": True}) + "\n",
            encoding="utf-8",
        )
        (run_dir / "reward.json").write_text(
            json.dumps({"final_reward": 1.0}) + "\n",
            encoding="utf-8",
        )
        (run_dir / "final.patch").write_text("diff --git a/app.py b/app.py\n", encoding="utf-8")
        metadata = build_run_metadata(
            run_dir=run_dir,
            run_id="run_001",
            task_id=task.id,
            run_config_facts_ref=facts_ref,
            tool_protocol=tool_protocol,
            baseline=BaselineResult(task_id=task.id, status="valid"),
            run_outcome="success",
            final_verifier_status="accepted",
            agent_stop_reason="feedback_tests_passed",
            final_verifier_mode="strict_patch_replay",
        )
        metadata_ref = write_run_metadata(run_dir, metadata)
        with pytest.raises(FileExistsError, match="run_metadata.json 已存在"):
            write_run_metadata(run_dir, metadata)

    facts_payload = json.loads((run_dir / "run_config_facts.json").read_text(encoding="utf-8"))
    metadata_payload = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "artifacts.json").read_text(encoding="utf-8"))
    manifest_paths = {artifact["relative_path"] for artifact in manifest["artifacts"]}

    assert facts_ref.relative_path == "run_config_facts.json"
    assert metadata_ref.relative_path == "run_metadata.json"
    assert facts_payload["run_id"] == "run_001"
    assert facts_payload["tool_protocol"]["tool_schema_snapshot_ref"]["artifact_id"]
    assert facts_payload["search_fact_policy_version"] == "repo_harness_search_fact_trust_v1"
    assert facts_payload["repository_action_index_policy_version"] == (
        "repo_harness_repository_action_index_v1"
    )
    assert facts_payload["convergence_nudge_policy_version"] == "repo_harness_convergence_nudge_v2"
    assert facts_payload["context_warning_policy_version"] == "repo_harness_context_warning_v1"
    assert facts_payload["provider_ready_token_estimator_version"] == (
        "provider_body_char4_token_estimator_v1"
    )
    assert facts_payload["context_threshold_decision_source"] == (
        "provider_request_projection_estimate"
    )
    assert facts_payload["compact_threshold_ratio_runtime_effect"] == (
        "reserved_for_autocompact_v1"
    )
    assert facts_payload["context_policy_snapshot_version"] == (
        "repo_harness_context_policy_snapshot_v1"
    )
    assert facts_payload["context_policy_snapshot_hash"]
    assert facts_payload["context_policy_snapshot"]["tool_result_compact_policy"] == (
        "claude_code_fresh_only_v1"
    )
    assert facts_payload["context_policy_snapshot"]["max_single_tool_result_chars"] == 50000
    assert facts_payload["context_policy_snapshot"]["max_tool_results_per_turn_chars"] == 200000
    assert facts_payload["context_policy_snapshot"]["microcompact_policy"] == (
        "count_based_tool_result_clear_v1"
    )
    assert facts_payload["context_policy_snapshot"]["reactive_compact_policy"] == (
        "provider_verified_reactive"
    )
    assert ContextPolicySnapshot.model_validate(facts_payload["context_policy_snapshot"])
    assert facts_payload["harness_control_message_export_policy"] == (
        "exclude_harness_generated_untrainable_control_messages_v1"
    )
    assert metadata_payload["run_config_facts_ref"]["sha256"] == facts_ref.sha256
    assert metadata_payload["tool_protocol"]["tool_schema_snapshot_ref"]["artifact_id"]
    assert metadata_payload["export_readiness"]["training_export_ready"] is True
    assert any(artifact["kind"] == "tool_schema_snapshot" for artifact in manifest["artifacts"])
    assert "run_config_facts.json" not in manifest_paths
    assert "run_metadata.json" not in manifest_paths


def test_run_config_facts_are_immutable_root_facts(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    task = TaskDefinition.model_validate(valid_task_payload())
    source = tmp_path / "source"
    source.mkdir()
    (source / "demo.py").write_text("x = 1\n", encoding="utf-8")
    with RunRecorder("run_001", run_dir, task_id=task.id) as recorder:
        _, _, tool_protocol = write_tool_schema_snapshot(recorder)
        dependency_state_ref = recorder.write_json_artifact(
            "dependency_state",
            DependencyState().model_dump(mode="json"),
            {"budget_policy": "preserve_json"},
        )
        fingerprint = build_local_environment_fingerprint(
            task_definition=task,
            source_checkout=source,
            dependency_state=DependencyState(),
            dependency_state_ref=dependency_state_ref,
            command_timeout_sec=120,
            network_policy="deny_agent_run",
        )
        facts = build_run_config_facts(
            run_id="run_001",
            task_definition=task,
            config=RunConfig(),
            tool_protocol=tool_protocol,
            environment_fingerprint=fingerprint,
        )
        write_run_config_facts(run_dir, facts)
        with pytest.raises(FileExistsError):
            write_run_config_facts(run_dir, facts)


def test_run_metadata_uses_pre_verl_boundary_for_rejected_model_patch(tmp_path: Path):
    run_dir = tmp_path / "run_rejected"
    task = TaskDefinition.model_validate(valid_task_payload())
    source = tmp_path / "source"
    source.mkdir()
    (source / "calculator.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    with RunRecorder("run_rejected", run_dir, task_id=task.id) as recorder:
        _, _, tool_protocol = write_tool_schema_snapshot(recorder)
        dependency_state_ref = recorder.write_json_artifact(
            "dependency_state",
            DependencyState().model_dump(mode="json"),
            {"budget_policy": "preserve_json"},
        )
        fingerprint = build_local_environment_fingerprint(
            task_definition=task,
            source_checkout=source,
            dependency_state=DependencyState(),
            dependency_state_ref=dependency_state_ref,
            command_timeout_sec=120,
            network_policy="deny_agent_run",
        )
        facts = build_run_config_facts(
            run_id="run_rejected",
            task_definition=task,
            config=RunConfig(),
            tool_protocol=tool_protocol,
            environment_fingerprint=fingerprint,
        )
        facts_ref = write_run_config_facts(run_dir, facts)
        (run_dir / "metrics.json").write_text(
            json.dumps(
                {
                    "run_outcome": "failed",
                    "final_verifier_status": "rejected",
                    "task_success": False,
                    "turn_count": 4,
                    "tool_call_count": 7,
                    "test_run_count": 0,
                    "interaction_efficiency": {"final_verifier_mode": "strict_patch_replay"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (run_dir / "final_verifier_boundary.json").write_text(
            json.dumps(
                {
                    "final_verifier_status": "rejected",
                    "accepted": False,
                    "failure_category": "model_patch_rejected_by_final_verifier",
                    "failure_owner": "model_wrong_fix",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        metadata = build_run_metadata(
            run_dir=run_dir,
            run_id="run_rejected",
            task_id=task.id,
            run_config_facts_ref=facts_ref,
            tool_protocol=tool_protocol,
            baseline=BaselineResult(task_id=task.id, status="valid"),
            run_outcome="failed",
            final_verifier_status="rejected",
            agent_stop_reason="final_answer",
            final_verifier_mode="strict_patch_replay",
        )

    diagnostic = metadata.failure_diagnostics[0]
    assert diagnostic.failure_category == FailureCategory.model_failure
    assert diagnostic.failure_type == FailureType.final_verifier_failed
    assert diagnostic.details == {
        "final_verifier_boundary_status": "rejected",
        "final_verifier_boundary_failure_category": "model_patch_rejected_by_final_verifier",
        "final_verifier_boundary_failure_owner": "model_wrong_fix",
        "diagnostic_subtypes": [],
        "late_edit_summary": {"model_wrong_fix_after_late_edit": False},
    }


def test_failure_diagnostics_reports_empty_patch_after_nudge(tmp_path: Path):
    run_dir = tmp_path / "run_empty_patch"
    run_dir.mkdir()
    (run_dir / "final.patch").write_text("", encoding="utf-8")
    (run_dir / "events.jsonl").write_text(
        json.dumps({"event_type": "convergence_nudge_injected", "turn": 10}) + "\n",
        encoding="utf-8",
    )

    diagnostics = _failure_diagnostics(
        baseline=BaselineResult(task_id="task_001", status="valid"),
        run_path=run_dir,
        run_outcome="failed",
        final_verifier_status="skipped",
        agent_stop_reason="max_turns",
    )

    assert diagnostics[0].failure_type == FailureType.nudge_ignored_empty_patch
    assert diagnostics[0].failure_category == FailureCategory.model_failure
    assert diagnostics[0].details["convergence_nudge_injected"] is True


def test_failure_diagnostics_uses_boundary_for_task_timeout_before_final_verifier(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run_task_timeout"
    run_dir.mkdir()
    (run_dir / "final.patch").write_text("diff --git a/app.py b/app.py\n", encoding="utf-8")
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    (run_dir / "final_verifier_boundary.json").write_text(
        json.dumps(
            {
                "final_verifier_status": "not_executed",
                "final_verifier_ran": False,
                "failure_category": "task_timeout_before_final_verifier",
                "failure_owner": "budget_or_timeout",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    diagnostics = _failure_diagnostics(
        baseline=BaselineResult(task_id="task_001", status="valid"),
        run_path=run_dir,
        run_outcome="inconclusive",
        final_verifier_status="not_executed",
        agent_stop_reason="task_timeout",
    )

    assert diagnostics[0].failure_category == FailureCategory.budget_or_timeout_failure
    assert diagnostics[0].failure_type == FailureType.task_timeout_before_final_verifier
    assert diagnostics[0].details["final_verifier_boundary_failure_owner"] == "budget_or_timeout"
    assert diagnostics[0].details["invalid_for_training"] is True


def test_failure_diagnostics_uses_boundary_for_final_verifier_environment_error(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run_final_verifier_environment_error"
    run_dir.mkdir()
    (run_dir / "final.patch").write_text("diff --git a/app.py b/app.py\n", encoding="utf-8")
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    (run_dir / "final_verifier_boundary.json").write_text(
        json.dumps(
            {
                "final_verifier_status": "not_executed",
                "final_verifier_ran": True,
                "failure_category": "final_verifier_environment_error",
                "failure_owner": "harness_or_environment",
                "final_verifier_environment_error_ref": {
                    "relative_path": "pre_verl_final_verifier_environment_error.json"
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    diagnostics = _failure_diagnostics(
        baseline=BaselineResult(task_id="task_001", status="valid"),
        run_path=run_dir,
        run_outcome="inconclusive",
        final_verifier_status="not_executed",
        agent_stop_reason="final_answer",
    )

    assert diagnostics[0].failure_category == FailureCategory.environment_failure
    assert diagnostics[0].failure_type == FailureType.final_verifier_environment_error
    assert (
        diagnostics[0].details["final_verifier_boundary_failure_category"]
        == "final_verifier_environment_error"
    )
    assert diagnostics[0].details["invalid_for_training"] is True


def test_failure_diagnostics_uses_boundary_for_budget_empty_patch(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run_boundary_empty_patch"
    run_dir.mkdir()
    (run_dir / "final.patch").write_text("", encoding="utf-8")
    (run_dir / "events.jsonl").write_text(
        json.dumps({"event_type": "convergence_nudge_injected", "turn": 10}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "final_verifier_boundary.json").write_text(
        json.dumps(
            {
                "final_verifier_status": "not_executed",
                "final_verifier_ran": False,
                "failure_category": "budget_exhausted_empty_patch",
                "failure_owner": "budget_or_timeout",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    diagnostics = _failure_diagnostics(
        baseline=BaselineResult(task_id="task_001", status="valid"),
        run_path=run_dir,
        run_outcome="inconclusive",
        final_verifier_status="not_executed",
        agent_stop_reason="max_turns",
    )

    assert diagnostics[0].failure_category == FailureCategory.budget_or_timeout_failure
    assert diagnostics[0].failure_type == FailureType.budget_exhausted_empty_patch
    assert diagnostics[0].details["diagnostic_subtypes"] == ["nudge_ignored_empty_patch"]


def test_failure_diagnostics_reports_compaction_insufficient_context_limit(tmp_path: Path):
    run_dir = tmp_path / "run_context_limit"
    run_dir.mkdir()
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "context_prepared",
                        "turn": 45,
                        "data": {
                            "context_revision": 45,
                            "provider_ready_token_estimate": 181000,
                            "provider_body_char_estimate": 724000,
                            "internal_token_estimate_after": 184098,
                            "threshold_decision_source": "provider_ready_token_estimate",
                            "context_reduction": {
                                "replacement_applied_but_insufficient_context_limit": True,
                                "replaced_tool_result_ids": ["call_1_result"],
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_type": "budget_exhausted",
                        "error_type": "context_limit",
                        "turn": 45,
                        "data": {
                            "provider_ready_token_estimate": 181000,
                            "max_context_tokens": 180000,
                            "threshold_decision_source": "provider_ready_token_estimate",
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    diagnostics = _failure_diagnostics(
        baseline=BaselineResult(task_id="task_001", status="valid"),
        run_path=run_dir,
        run_outcome="failed",
        final_verifier_status="skipped",
        agent_stop_reason="context_limit",
    )

    assert diagnostics[0].failure_type == (
        FailureType.compaction_applied_but_insufficient_context_limit
    )
    assert diagnostics[0].source_component == "context_manager"
    assert diagnostics[0].details["latest_context_prepared"]["provider_ready_token_estimate"] == 181000


def test_failure_diagnostics_reports_auto_compact_failed_preflight_details(tmp_path: Path):
    run_dir = tmp_path / "run_auto_compact_preflight"
    run_dir.mkdir()
    _write_context_policy_fact(run_dir)
    auto_compact_record_ref = _artifact_ref(
        artifact_id="auto_record_001",
        relative_path="artifacts/auto_compact_record.json",
        kind="auto_compact_record",
    )
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_id": "auto_compact_0001",
                        "event_type": "auto_compact_failed",
                        "turn": 6,
                        "data": {
                            "source_prepared_messages_ref": {
                                "artifact_id": "prepared_001",
                                "relative_path": "artifacts/prepared_001.json",
                                "kind": "prepared_messages",
                            },
                            "failure_reason": "compact_model_timeout",
                            "tokens_before": 990000,
                            "tokens_after": 990000,
                            "effective_context_budget_tokens": 930000,
                            "hard_context_limit_tokens": 970000,
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_id": "budget_0001",
                        "event_type": "budget_exhausted",
                        "error_type": "auto_compact_failed_preflight",
                        "turn": 6,
                        "data": {
                            "token_estimate": 990000,
                            "hard_context_limit_tokens": 970000,
                            "auto_compact_failure_reason": "compact_model_timeout",
                            "auto_compact_record_ref": auto_compact_record_ref,
                            "provider_request_projection_hash": "projection_hash_001",
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    diagnostics = _failure_diagnostics(
        baseline=BaselineResult(task_id="task_001", status="valid"),
        run_path=run_dir,
        run_outcome="failed",
        final_verifier_status="skipped",
        agent_stop_reason="auto_compact_failed_preflight",
    )

    assert diagnostics[0].failure_type == FailureType.auto_compact_failed_preflight
    assert diagnostics[0].source_component == "context_manager"
    assert diagnostics[0].details["local_context_limit_policy"] == "strict_local_preflight"
    assert diagnostics[0].details["reactive_compact_policy"] == "provider_verified_reactive"
    assert diagnostics[0].details["source_prepared_messages_ref"]["artifact_id"] == "prepared_001"
    assert diagnostics[0].details["auto_compact_record_ref"]["artifact_id"] == "auto_record_001"
    assert diagnostics[0].details["failure_reason"] == "compact_model_timeout"
    assert diagnostics[0].details["tokens_before"] == 990000
    assert diagnostics[0].details["tokens_after"] == 990000
    assert diagnostics[0].details["effective_context_budget_tokens"] == 930000
    assert diagnostics[0].details["hard_context_limit_tokens"] == 970000
    assert diagnostics[0].details["provider_request_projection_hash"] == "projection_hash_001"


def test_failure_diagnostics_reports_autocompact_applied_but_preflight_still_high(
    tmp_path: Path,
):
    run_dir = tmp_path / "run_autocompact_preflight_still_high"
    run_dir.mkdir()
    _write_context_policy_fact(run_dir)
    summary_ref = _artifact_ref(
        artifact_id="auto_summary_001",
        relative_path="artifacts/auto_summary_001.json",
        kind="auto_compact_summary",
    )
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_id": "context_0001",
                        "event_type": "context_prepared",
                        "turn": 6,
                        "data": {
                            "context_revision": 6,
                            "provider_ready_token_estimate": 980000,
                            "provider_body_char_estimate": 3920000,
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_id": "auto_compact_0002",
                        "event_type": "auto_compact_applied",
                        "turn": 6,
                        "data": {
                            "source_prepared_messages_ref": {
                                "artifact_id": "prepared_before_compact",
                                "relative_path": "artifacts/prepared_before_compact.json",
                                "kind": "prepared_messages",
                            },
                            "summary_artifact_ref": summary_ref,
                            "tokens_before": 1040000,
                            "tokens_after": 980000,
                            "effective_context_budget_tokens": 930000,
                            "hard_context_limit_tokens": 970000,
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_id": "budget_0002",
                        "event_type": "budget_exhausted",
                        "error_type": "context_limit_preflight_after_autocompact",
                        "turn": 6,
                        "data": {
                            "token_estimate": 980000,
                            "hard_context_limit_tokens": 970000,
                            "provider_request_projection_hash": "projection_hash_002",
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    diagnostics = _failure_diagnostics(
        baseline=BaselineResult(task_id="task_001", status="valid"),
        run_path=run_dir,
        run_outcome="failed",
        final_verifier_status="skipped",
        agent_stop_reason="context_limit_preflight_after_autocompact",
    )

    assert diagnostics[0].failure_type == (
        FailureType.compaction_applied_but_insufficient_context_limit
    )
    assert diagnostics[0].source_component == "context_manager"
    assert diagnostics[0].details["budget_exhausted"]["token_estimate"] == 980000
    assert diagnostics[0].details["source_prepared_messages_ref"]["artifact_id"] == (
        "prepared_before_compact"
    )
    assert diagnostics[0].details["summary_artifact_ref"]["artifact_id"] == "auto_summary_001"
    assert diagnostics[0].details["tokens_before"] == 1040000
    assert diagnostics[0].details["tokens_after"] == 980000


def test_failure_diagnostics_reports_reactive_compact_failed_with_ptl_details(
    tmp_path: Path,
):
    run_dir = tmp_path / "run_reactive_failed"
    run_dir.mkdir()
    _write_context_policy_fact(run_dir)
    ptl_ref = _write_ptl_record_artifact(
        run_dir,
        artifact_id="ptl_record_001",
        synthetic_marker_id="ptl_marker_001",
        omitted_round_count=3,
        retained_round_count=2,
        token_estimate_before=1010000,
        token_estimate_after=980000,
        hard_context_limit_tokens=970000,
    )
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_id": "reactive_0001",
                        "event_type": "reactive_compact_triggered",
                        "turn": 7,
                        "data": {
                            "model_call_id": "run_model_call_0007",
                            "prepared_messages_ref": {
                                "artifact_id": "prepared_007",
                                "relative_path": "artifacts/prepared_007.json",
                                "kind": "prepared_messages",
                            },
                            "raw_provider_request_ref": {
                                "artifact_id": "provider_request_007",
                                "relative_path": "artifacts/provider_request_007.json",
                                "kind": "provider_request",
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_id": "auto_compact_0001",
                        "event_type": "auto_compact_failed",
                        "turn": 7,
                        "data": {
                            "source_prepared_messages_ref": {
                                "artifact_id": "prepared_007",
                                "relative_path": "artifacts/prepared_007.json",
                                "kind": "prepared_messages",
                            },
                            "failure_reason": "compact_source_too_large",
                            "tokens_before": 1010000,
                            "tokens_after": 1010000,
                            "effective_context_budget_tokens": 930000,
                            "hard_context_limit_tokens": 970000,
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_id": "reactive_0002",
                        "event_type": "reactive_compact_failed",
                        "error_type": "compact_source_too_large",
                        "turn": 7,
                        "data": {
                            "compact_id": "compact_007",
                            "failure_reason": "compact_source_too_large",
                            "ptl_fallback_status": "failed",
                            "ptl_fallback_failure_reason": (
                                "ptl_truncation_did_not_reduce_projection"
                            ),
                            "ptl_truncation_ref": ptl_ref,
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    diagnostics = _failure_diagnostics(
        baseline=BaselineResult(task_id="task_001", status="valid"),
        run_path=run_dir,
        run_outcome="failed",
        final_verifier_status="skipped",
        agent_stop_reason="reactive_compact_failed",
    )

    assert diagnostics[0].failure_type == FailureType.reactive_compact_failed
    assert diagnostics[0].details["source_prepared_messages_ref"]["artifact_id"] == "prepared_007"
    assert diagnostics[0].details["failure_reason"] == "compact_source_too_large"
    assert diagnostics[0].details["original_model_call_id"] == "run_model_call_0007"
    assert diagnostics[0].details["tokens_before"] == 1010000
    assert diagnostics[0].details["ptl_fallback"]["synthetic_marker_id"] == "ptl_marker_001"
    assert diagnostics[0].details["ptl_fallback"]["omitted_round_count"] == 3


def test_failure_diagnostics_reports_context_limit_after_reactive_compact_retry(
    tmp_path: Path,
):
    run_dir = tmp_path / "run_context_limit_after_reactive"
    run_dir.mkdir()
    _write_context_policy_fact(run_dir)
    ptl_ref = _write_ptl_record_artifact(
        run_dir,
        artifact_id="ptl_record_002",
        synthetic_marker_id="ptl_marker_002",
        omitted_round_count=4,
        retained_round_count=1,
        token_estimate_before=1050000,
        token_estimate_after=975000,
        hard_context_limit_tokens=970000,
    )
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_id": "ptl_0001",
                        "event_type": "ptl_truncation_applied",
                        "turn": 8,
                        "data": {
                            "ptl_truncation_ref": ptl_ref,
                            "original_model_call_id": "run_model_call_0008",
                            "omitted_round_count": 4,
                            "synthetic_marker_id": "ptl_marker_002",
                            "token_estimate_before": 1050000,
                            "token_estimate_after": 975000,
                            "post_truncation_above_hard_limit": True,
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_id": "model_0009",
                        "event_type": "model_call_started",
                        "turn": 9,
                        "data": {"model_call_id": "run_model_call_0009"},
                    }
                ),
                json.dumps(
                    {
                        "event_id": "reactive_0003",
                        "event_type": "reactive_compact_triggered",
                        "turn": 9,
                        "data": {
                            "model_call_id": "run_model_call_0009",
                            "prepared_messages_ref": {
                                "artifact_id": "prepared_retry",
                                "relative_path": "artifacts/prepared_retry.json",
                                "kind": "prepared_messages",
                            },
                            "raw_provider_request_ref": {
                                "artifact_id": "provider_request_retry",
                                "relative_path": "artifacts/provider_request_retry.json",
                                "kind": "provider_request",
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_id": "reactive_0004",
                        "event_type": "reactive_compact_retry_limit_exhausted",
                        "error_type": "context_limit_after_reactive_compact",
                        "turn": 9,
                        "data": {
                            "reactive_compact_retry_count": 1,
                            "reactive_compact_retry_limit": 1,
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    diagnostics = _failure_diagnostics(
        baseline=BaselineResult(task_id="task_001", status="valid"),
        run_path=run_dir,
        run_outcome="failed",
        final_verifier_status="skipped",
        agent_stop_reason="context_limit_after_reactive_compact",
    )

    assert diagnostics[0].failure_type == FailureType.context_limit_after_reactive_compact
    assert diagnostics[0].details["retry_model_call_id"] == "run_model_call_0009"
    assert diagnostics[0].details["ptl_truncation_ref"]["artifact_id"] == "ptl_record_002"
    assert diagnostics[0].details["synthetic_marker_id"] == "ptl_marker_002"
    assert diagnostics[0].details["omitted_round_count"] == 4
    assert diagnostics[0].details["tokens_before"] == 1050000
    assert diagnostics[0].details["tokens_after"] == 975000
    assert diagnostics[0].details["hard_context_limit_tokens"] == 970000


def test_model_call_summary_records_successful_ptl_retry_diagnostics(tmp_path: Path):
    run_dir = tmp_path / "run_successful_ptl_retry"
    run_dir.mkdir()
    ptl_ref = _write_ptl_record_artifact(
        run_dir,
        artifact_id="ptl_record_003",
        synthetic_marker_id="ptl_marker_003",
        omitted_round_count=2,
        retained_round_count=3,
        token_estimate_before=1020000,
        token_estimate_after=880000,
        hard_context_limit_tokens=970000,
    )
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_id": "ptl_0001",
                        "event_type": "ptl_truncation_applied",
                        "turn": 8,
                        "data": {
                            "ptl_truncation_ref": ptl_ref,
                            "original_model_call_id": "run_model_call_0008",
                            "synthetic_marker_id": "ptl_marker_003",
                            "omitted_round_count": 2,
                            "token_estimate_before": 1020000,
                            "token_estimate_after": 880000,
                            "post_truncation_above_hard_limit": False,
                        },
                    }
                ),
                json.dumps(
                    {
                        "event_id": "model_input_0009",
                        "event_type": "model_input_accepted",
                        "turn": 9,
                        "data": {"model_call_id": "run_model_call_0009"},
                    }
                ),
                json.dumps(
                    {
                        "event_id": "model_completed_0009",
                        "event_type": "model_call_completed",
                        "turn": 9,
                        "data": {"model_error_type": None},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _model_call_summary(run_dir)

    assert summary["model_call_count"] == 1
    assert summary["ptl_truncation_count"] == 1
    assert summary["latest_ptl_truncation"]["retry_model_call_id"] == "run_model_call_0009"
    assert summary["latest_ptl_truncation"]["synthetic_marker_id"] == "ptl_marker_003"
    assert summary["latest_ptl_truncation"]["omitted_round_count"] == 2
    assert summary["latest_ptl_truncation"]["hard_context_limit_tokens"] == 970000


def test_failure_diagnostics_reports_search_backend_false_fact_suspected(tmp_path: Path):
    run_dir = tmp_path / "run_search_issue"
    run_dir.mkdir()
    (run_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "event_type": "tool_completed",
                "turn": 3,
                "data": {
                    "tool_call_id": "call_grep",
                    "effective_tool_name": "grep",
                    "typed": {
                        "result_kind": "partial_scan_no_match",
                        "scan_complete": False,
                        "scan_complete_reason": "read_errors_present",
                        "backend_mismatch_detected": False,
                        "read_error_count": 1,
                        "visibility_error_count": 0,
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    diagnostics = _failure_diagnostics(
        baseline=BaselineResult(task_id="task_001", status="valid"),
        run_path=run_dir,
        run_outcome="failed",
        final_verifier_status="skipped",
        agent_stop_reason=None,
    )

    assert diagnostics[0].failure_type == FailureType.search_backend_false_fact_suspected
    assert diagnostics[0].failure_category == FailureCategory.tool_protocol_failure
    assert diagnostics[0].details["samples"][0]["scan_complete_reason"] == "read_errors_present"


def test_failure_diagnostics_does_not_flag_search_false_fact_when_matches_exist(
    tmp_path: Path,
):
    run_dir = tmp_path / "run_search_match_with_error"
    run_dir.mkdir()
    (run_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "event_type": "tool_completed",
                "turn": 3,
                "data": {
                    "tool_call_id": "call_grep",
                    "effective_tool_name": "grep",
                    "typed": {
                        "result_kind": "partial_scan_with_matches",
                        "scan_complete": False,
                        "scan_complete_reason": "read_errors_present",
                        "backend_mismatch_detected": False,
                        "read_error_count": 1,
                        "visibility_error_count": 0,
                        "total_match_count": 2,
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    diagnostics = _failure_diagnostics(
        baseline=BaselineResult(task_id="task_001", status="valid"),
        run_path=run_dir,
        run_outcome="failed",
        final_verifier_status="skipped",
        agent_stop_reason=None,
    )

    assert not diagnostics


def test_failure_diagnostics_late_edit_requires_near_budget_and_final_answer(
    tmp_path: Path,
):
    run_dir = tmp_path / "run_rejected_late_edit"
    run_dir.mkdir()
    (run_dir / "run_config_facts.json").write_text(
        json.dumps({"max_turns": 10}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "tool_completed",
                        "turn": 9,
                        "data": {"effective_tool_name": "edit_file"},
                    }
                ),
                json.dumps(
                    {
                        "event_type": "tool_completed",
                        "turn": 9,
                        "data": {"effective_tool_name": "grep"},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "transcript.jsonl").write_text(
        json.dumps(
            {
                "role": "assistant",
                "turn": 10,
                "content_preview": "done",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "final_verifier_boundary.json").write_text(
        json.dumps(
            {
                "final_verifier_status": "rejected",
                "failure_category": "model_patch_rejected_by_final_verifier",
                "failure_owner": "model_wrong_fix",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    diagnostics = _failure_diagnostics(
        baseline=BaselineResult(task_id="task_001", status="valid"),
        run_path=run_dir,
        run_outcome="failed",
        final_verifier_status="rejected",
        agent_stop_reason="final_answer",
    )

    assert diagnostics[0].details["diagnostic_subtypes"] == [
        FailureType.model_wrong_fix_after_late_edit.value
    ]
    assert diagnostics[0].details["late_edit_summary"]["near_turn_budget"] is True


def test_environment_fingerprint_records_setup_and_dependency_refs(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    task = TaskDefinition.model_validate(valid_task_payload())
    source = tmp_path / "source"
    source.mkdir()
    (source / "demo.py").write_text("x = 1\n", encoding="utf-8")
    with RunRecorder("run_001", run_dir, task_id=task.id) as recorder:
        dependency_state_ref = recorder.write_json_artifact(
            "dependency_state",
            DependencyState().model_dump(mode="json"),
            {"budget_policy": "preserve_json"},
        )
        setup_ref = recorder.write_artifact("setup_stdout", "setup ok")
        fingerprint = build_local_environment_fingerprint(
            task_definition=task,
            source_checkout=source,
            dependency_state=DependencyState(),
            dependency_state_ref=dependency_state_ref,
            setup_artifact_hash=setup_ref.sha256,
            command_timeout_sec=120,
            network_policy="deny_agent_run",
        )

    execution = fingerprint.workspace_execution
    assert execution.dependency_state_ref == dependency_state_ref
    assert execution.setup_artifact_hash == setup_ref.sha256
