from __future__ import annotations

import pytest
from pydantic import ValidationError

from repo_harness.context import ContextCompactionFacts
from repo_harness.evaluation import ExperimentResumeManifest, RunCheckpoint
from repo_harness.reward import CoreFailureDiagnostics
from repo_harness.run_metadata import (
    HookPolicySnapshot,
    MCPPolicySnapshot,
    PermissionPolicySnapshot,
    ToolContractSnapshot,
)
from repo_harness.tasks import (
    RealRepositorySourceFacts,
    SweBenchLikeEnvironmentSpec,
    SweBenchLikeTaskFacts,
    TaskAdapterFacts,
)
from repo_harness.trajectory import ArtifactRef, TrajectoryStoreFacts
from repo_harness.v3_acceptance import CommandLogEntry, V3AcceptanceReport
from repo_harness.v3_visibility import V3_VISIBILITY_SURFACES
from repo_harness.verifier import SweBenchLikeVerifierPlan
from repo_harness.workspace import ContainerExecutionFacts, DockerBackendFacts

SHA = "a" * 64
SHA_B = "b" * 64


def artifact_ref(artifact_id: str = "artifact_001", kind: str = "json") -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=f"artifacts/{artifact_id}.json",
        kind=kind,
        sha256=SHA,
        size_bytes=12,
    )


def test_v3_docker_and_container_facts_round_trip():
    backend = DockerBackendFacts(
        docker_context="desktop-linux",
        docker_cli_version="Docker version 29.4.1",
        docker_server_version="29.4.1",
        server_platform="linux",
        server_architecture="arm64",
        requested_container_platform="linux/amd64",
        image_ref="alpine:3.20",
        image_id=SHA,
        image_platform="linux/amd64",
        build_mode="pulled",
        cross_architecture_emulation=True,
        network_policy="deny_agent_run",
        mount_policy="workspace_read_write_tmp_only",
        timeout_sec=120,
        cleanup_policy="remove_containers_keep_images",
        cleanup_status="completed",
    )
    execution = ContainerExecutionFacts(
        command_id="cmd_001",
        container_id="container_001",
        image_id=SHA,
        requested_container_platform="linux/amd64",
        container_uname_m="x86_64",
        command=["uname", "-m"],
        workdir="/workspace",
        exit_code=0,
        duration_ms=12,
        network_policy="deny_agent_run",
        mount_policy="workspace_read_write_tmp_only",
        cleanup_status="completed",
        output_artifact_ref=artifact_ref("combined_output", "command_output"),
        stdout_ref=artifact_ref("stdout", "command_stdout"),
        stderr_ref=artifact_ref("stderr", "command_stderr"),
        stdout_preview="ok",
        stderr_preview="",
        captured_output_empty=False,
    )

    assert DockerBackendFacts.model_validate(backend.model_dump(mode="json")) == backend
    assert ContainerExecutionFacts.model_validate(execution.model_dump(mode="json")) == execution


def test_v3_task_and_adapter_facts_reject_unfixed_or_visible_hidden_material():
    with pytest.raises(ValidationError, match="archive_sha256"):
        RealRepositorySourceFacts(
            source_kind="public_archive",
            remote_url="https://github.com/example/project",
            base_commit="abc123",
            source_tree_hash=SHA,
            local_materialization_ref=artifact_ref("source"),
            verifier_evidence_ref=artifact_ref("verifier"),
        )

    with pytest.raises(ValidationError, match="hidden verifier material"):
        SweBenchLikeTaskFacts(
            instance_id="pytest-dev__pytest-7220",
            repo="pytest-dev/pytest",
            base_commit="abc123",
            environment_setup_commit="def456",
            dataset_name="princeton-nlp/SWE-bench_Lite",
            dataset_revision="fixed",
            dataset_split="test",
            task_hash=SHA,
            problem_statement_sha256=SHA,
            test_patch_sha256=SHA,
            fail_to_pass_selectors_sha256=SHA,
            pass_to_pass_selectors_sha256=SHA,
            fail_to_pass_selector_count=1,
            pass_to_pass_selector_count=1,
            adapter_input_ref=artifact_ref("adapter"),
            evaluator_evidence_manifest_ref=artifact_ref("evaluator"),
            model_visible_contains_hidden_material=True,
        )


def test_v3_task_adapter_and_environment_facts_round_trip():
    adapter = TaskAdapterFacts(
        adapter_name="swebench_like_fixed",
        adapter_version="repo_harness_task_adapter_v3_v0",
        input_manifest_ref=artifact_ref("input"),
        output_task_ref=artifact_ref("task"),
        task_hash=SHA,
        visibility_policy_ref=artifact_ref("visibility"),
        final_only_policy="disabled_feedback_only",
    )
    environment = SweBenchLikeEnvironmentSpec(
        instance_id="sympy__sympy-24909",
        repo="sympy/sympy",
        base_commit="abc123",
        execution_image="python:3.11",
        requested_container_platform="linux/amd64",
        setup_commands_ref=artifact_ref("setup"),
    )

    assert TaskAdapterFacts.model_validate(adapter.model_dump(mode="json")) == adapter
    assert SweBenchLikeEnvironmentSpec.model_validate(
        environment.model_dump(mode="json")
    ) == environment


def test_swebench_like_verifier_plan_blocks_oracle_hidden_feedback():
    with pytest.raises(ValidationError, match="oracle_hidden_feedback"):
        SweBenchLikeVerifierPlan(
            instance_id="pytest-dev__pytest-7220",
            base_test_command="pytest",
            fail_to_pass_command="pytest hidden",
            pass_to_pass_command="pytest regression",
            selector_source="evaluator_only_manifest_ref",
            selector_cache_ref=artifact_ref("selectors"),
            verifier_patch_ref=artifact_ref("patch"),
            per_command_timeout_sec=120,
            oracle_hidden_feedback_allowed=True,
        )


def test_resume_checkpoint_context_failure_and_trajectory_constraints():
    with pytest.raises(ValidationError, match="run_metadata_ref"):
        RunCheckpoint(
            run_id="run_001",
            status="interrupted",
            run_metadata_ref=artifact_ref("metadata"),
        )

    completed_checkpoint = RunCheckpoint(run_id="run_001", status="completed")
    manifest = ExperimentResumeManifest(
        experiment_id="exp_001",
        run_checkpoints=[completed_checkpoint],
        completed_run_ids=["run_001"],
    )
    assert manifest.completed_run_ids == ["run_001"]

    with pytest.raises(ValidationError, match="pending_run_ids"):
        ExperimentResumeManifest(
            experiment_id="exp_pending_mismatch",
            run_checkpoints=[RunCheckpoint(run_id="run_pending", status="pending")],
            completed_run_ids=[],
            pending_run_ids=[],
        )

    with pytest.raises(ValidationError, match="token"):
        ContextCompactionFacts(
            run_id="run_001",
            trigger_event_id="event_001",
            context_revision_before=1,
            context_revision_after=2,
            tokens_before=100,
            tokens_after=120,
            content_replacement_state_ref=artifact_ref("replacement"),
            contamination_scan_status="clean",
        )

    with pytest.raises(ValidationError, match="reward metadata"):
        CoreFailureDiagnostics(
            diagnostic_id="diag_001",
            run_id="run_001",
            failure_category="verifier",
            failure_type="final_verifier_failed",
            source_component="verifier",
            blocks_training=True,
            reward_metadata_visible_to_model=True,
        )

    with pytest.raises(ValidationError, match="run_metadata"):
        TrajectoryStoreFacts(
            run_id="run_001",
            transcript_ref=artifact_ref("transcript"),
            events_ref=artifact_ref("events"),
            artifacts_manifest_ref=artifact_ref("artifacts"),
            run_config_facts_ref=artifact_ref("run_config"),
            transcript_readable=True,
            events_readable=True,
            artifacts_resolvable=True,
        )


def test_tool_contract_and_policy_snapshots_block_dynamic_surfaces():
    permission = PermissionPolicySnapshot(
        policy_version="repo_harness_permissions_v0",
        snapshot_id="perm_001",
        policy_sha256=SHA,
        mode="auto",
    )
    assert permission.policy_sha256 == SHA

    with pytest.raises(ValidationError, match="hook-generated"):
        HookPolicySnapshot(
            snapshot_id="hook_001",
            hooks_enabled=False,
            hook_generated_observation_model_visible=True,
        )

    with pytest.raises(ValidationError, match="dynamic MCP"):
        MCPPolicySnapshot(snapshot_id="mcp_001", dynamic_tool_discovery_allowed=True)

    contract = ToolContractSnapshot(
        snapshot_id="tools_001",
        tool_schema_refs=[artifact_ref("tool_schema")],
        tool_schema_sha256=SHA_B,
        permission_policy_snapshot_ref=artifact_ref("permission"),
        hook_policy_snapshot_ref=artifact_ref("hook"),
        mcp_policy_snapshot_ref=artifact_ref("mcp"),
    )
    assert contract.tool_result_pairing_policy == "all_tool_calls_receive_tool_results"


def test_command_log_and_acceptance_skeleton_constraints():
    with pytest.raises(ValidationError, match="exit_code"):
        CommandLogEntry(
            command_name="pytest",
            argv=["python", "-m", "pytest"],
            cwd="/workspace",
            tool_or_cli_version="repo-harness-v3",
            started_at="2026-05-02T00:00:00Z",
            finished_at="2026-05-02T00:01:00Z",
        )

    report = V3AcceptanceReport(
        acceptance_id="acceptance_001",
        status="passed",
        input_manifest_ref=artifact_ref("inputs"),
        command_log_ref=artifact_ref("commands"),
        report_generated_at="2026-05-02T00:00:00Z",
        checks=["schemas"],
        contamination_scan_refs=[artifact_ref("contamination")],
        contamination_scan_surfaces=list(V3_VISIBILITY_SURFACES),
    )
    assert report.status == "passed"

    with pytest.raises(ValidationError, match="contamination scan evidence"):
        V3AcceptanceReport(
            acceptance_id="acceptance_empty",
            status="passed",
            input_manifest_ref=artifact_ref("inputs"),
            command_log_ref=artifact_ref("commands"),
            report_generated_at="2026-05-02T00:00:00Z",
            checks=["schemas"],
        )

    with pytest.raises(ValidationError, match="contamination scan surfaces"):
        V3AcceptanceReport(
            acceptance_id="acceptance_partial",
            status="passed",
            input_manifest_ref=artifact_ref("inputs"),
            command_log_ref=artifact_ref("commands"),
            report_generated_at="2026-05-02T00:00:00Z",
            checks=["schemas"],
            contamination_scan_refs=[artifact_ref("contamination")],
            contamination_scan_surfaces=["prompt"],
        )

    with pytest.raises(ValidationError, match="failures"):
        V3AcceptanceReport(
            acceptance_id="acceptance_002",
            status="failed",
            input_manifest_ref=artifact_ref("inputs"),
            command_log_ref=artifact_ref("commands"),
            report_generated_at="2026-05-02T00:00:00Z",
        )
