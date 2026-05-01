from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from repo_harness.evaluation import (
    ExperimentConfig,
    FeedbackPolicyConfig,
    ResolvedFeedbackPolicyFacts,
)
from repo_harness.export import (
    CompareScope,
    ExportAuditItem,
    ExportAuditReport,
    ExportAuditSample,
    ExportManifest,
    ExportRecord,
    ExportRecordQuality,
    PairingPolicy,
)
from repo_harness.model_client import (
    ModelGenerationRequest,
    ModelProviderOptions,
    ModelRequestContext,
    ProviderCredentialPolicy,
)
from repo_harness.run_metadata import (
    EnvironmentFingerprint,
    ExecutionModeFacts,
    ExportReadinessFacts,
    FailureCategory,
    FailureDiagnostics,
    FailureType,
    RunConfigFacts,
    RunConfigFactsRef,
    RunMetadata,
    RunMetadataRef,
    SourceCheckoutFacts,
    ToolProtocolFacts,
    ToolSchemaEntry,
    ToolSchemaSnapshot,
    WorkspaceBackendFacts,
    WorkspaceExecutionFacts,
)
from repo_harness.trajectory import ArtifactRef
from repo_harness.workspace import WorkspaceBackend, WorkspaceCommandResult, WorkspacePaths

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


def fact_ref() -> RunConfigFactsRef:
    return RunConfigFactsRef(relative_path="run_config_facts.json", sha256=SHA)


def workspace_execution_facts() -> WorkspaceExecutionFacts:
    execution_mode = ExecutionModeFacts(
        requested_execution_mode="local_process",
        resolved_execution_mode="local_process",
        execution_mode_status="active",
    )
    backend = WorkspaceBackendFacts(
        backend="local_process",
        backend_version="local_workspace_adapter_v0",
        execution_mode=execution_mode,
        network_policy="deny_agent_run",
    )
    source = SourceCheckoutFacts(
        source_kind="micro_repo_fixture",
        base_commit="main",
        source_tree_hash=SHA,
        checkout_path_status="redacted",
        decontamination_status="manual_checked",
    )
    return WorkspaceExecutionFacts(
        workspace_backend=backend,
        source_checkout=source,
        python_version="3.12",
        operating_system="darwin",
        command_timeout_sec=120,
        shell_command_policy_version="repo_harness_shell_policy_v0",
        environment_spec_hash=SHA,
    )


def environment_fingerprint() -> EnvironmentFingerprint:
    return EnvironmentFingerprint(
        fingerprint_id="env_001",
        python_version="3.12",
        platform="darwin-arm64",
        package_manager="pip",
        lockfile_hashes={"pyproject.toml": SHA},
        environment_spec_hash=SHA,
        workspace_execution=workspace_execution_facts(),
    )


def tool_protocol_facts() -> ToolProtocolFacts:
    return ToolProtocolFacts(
        tool_schema_snapshot_ref=artifact_ref("tool_schema_snapshot", "tool_schema_snapshot"),
        tool_schema_snapshot_sha256=SHA,
        tool_order=["read_file"],
        tool_parser_version="repo_harness_tool_call_parser_v0",
        tool_result_format_version="repo_harness_tool_result_v0",
        tool_policy_version="repo_harness_tools_v0",
    )


def run_config_facts() -> RunConfigFacts:
    return RunConfigFacts(
        run_id="run_001",
        task_id="task_001",
        task_version="task_001_v0",
        dataset_name="repo_harness_micro",
        source_kind="micro_repo_fixture",
        base_commit="main",
        provider="replay",
        model_id="replay-script-v0",
        temperature=0.0,
        seed=42,
        max_output_tokens=4096,
        retry_policy="none",
        credential_policy="env_only",
        provider_request_logging_policy="redact_secrets",
        scaffold_id="simple_react",
        scaffold_version="simple_react_v0",
        allowed_tools_policy="repo_harness_tools_v0",
        phase_policy="single_phase_v0",
        stop_policy="stop_on_final_or_budget_v0",
        test_feedback_policy="public_only",
        feedback_tests_passed_policy="stop_immediately",
        hidden_feedback_visible_to_model=False,
        tool_protocol=tool_protocol_facts(),
        context_builder_version="repo_harness_context_v0",
        context_policy_version="repo_harness_context_policy_v0",
        prompt_template_version="repo_harness_prompt_v0",
        token_estimator_version="char4_token_estimator_v0",
        permission_mode="auto",
        permission_policy_version="repo_harness_permissions_v0",
        network_policy="deny_agent_run",
        shell_command_policy_version="repo_harness_shell_policy_v0",
        verifier_name="pytest",
        verifier_version="pytest_parser_v0",
        final_verifier_mode="strict_patch_replay",
        reward_formula_version="repo_harness_reward_v0",
        outcome_policy_version="repo_harness_outcome_policy_v0",
        max_turns=20,
        max_tool_calls=80,
        max_test_runs=6,
        task_timeout_sec=900,
        command_timeout_sec=120,
        context_budget_tokens=120000,
        environment_fingerprint=environment_fingerprint(),
    )


def run_metadata() -> RunMetadata:
    return RunMetadata(
        run_id="run_001",
        task_id="task_001",
        run_config_facts_ref=fact_ref(),
        tool_protocol=tool_protocol_facts(),
        run_status="completed",
        agent_stop_reason="feedback_tests_passed",
        run_outcome="success",
        reward_status="present",
        final_verifier_status="accepted",
        final_verifier_mode="strict_patch_replay",
        metrics_summary={"turn_count": 2},
        artifact_manifest_status="ok",
        export_readiness=ExportReadinessFacts(
            has_final_patch=True,
            has_formal_final_verifier=True,
            has_reward_metadata=True,
            clean_transcript=True,
            clean_artifact_manifest=True,
            training_export_ready=True,
        ),
    )


def model_request_context_payload() -> dict[str, Any]:
    return {
        "run_id": "run_001",
        "task_id": "task_001",
        "turn": 1,
        "model_call_id": "model_call_001",
        "prepared_messages": [{"role": "user", "content": "Fix it"}],
        "prepared_messages_ref": artifact_ref("prepared_messages", "prepared_messages").model_dump(
            mode="json"
        ),
        "model_input_hash": SHA,
        "context_revision": 1,
        "provider_message_format": "repo_harness_messages_v0",
        "context_truncation_facts": {"truncated": False},
        "omitted_context_facts": {"omitted": []},
        "generation_config": {"temperature": 0.0, "max_output_tokens": 512},
        "provider_model_settings": {"model_id": "replay-script-v0"},
        "allowed_tool_definitions": [{"name": "read_file"}],
        "tool_choice": "auto",
        "tool_schema_snapshot_ref": artifact_ref(
            "tool_schema_snapshot", "tool_schema_snapshot"
        ).model_dump(mode="json"),
        "provider_options": {
            "provider": "replay",
            "model_id": "replay-script-v0",
            "credential_policy": ProviderCredentialPolicy().model_dump(mode="json"),
        },
        "scaffold_id": "simple_react",
        "scaffold_phase": "react",
        "run_config_facts_ref": fact_ref().model_dump(mode="json"),
        "budget_state": {"turns_remaining": 19},
        "request_timeout_seconds": 30.0,
        "raw_request_logging_policy": "redact_secrets",
        "credential_policy": ProviderCredentialPolicy().model_dump(mode="json"),
        "retry_policy": "none",
    }


def test_run_metadata_schema_round_trips():
    config_facts = run_config_facts()
    metadata = run_metadata()
    snapshot = ToolSchemaSnapshot(
        snapshot_id="snapshot_001",
        tool_order=["read_file"],
        tool_parser_version="repo_harness_tool_call_parser_v0",
        tool_result_format_version="repo_harness_tool_result_v0",
        tools=[
            ToolSchemaEntry(
                name="read_file",
                tool_version="read_file_v0",
                model_visible_description="读取工作区内文件。",
                input_schema={"type": "object"},
                tool_result_format_version="repo_harness_tool_result_v0",
                read_only=True,
                destructive=False,
                permission_required=False,
                max_output_chars=12000,
            )
        ],
        snapshot_sha256=SHA,
    )

    assert RunConfigFacts.model_validate(config_facts.model_dump(mode="json")) == config_facts
    assert RunMetadata.model_validate(metadata.model_dump(mode="json")) == metadata
    assert ToolSchemaSnapshot.model_validate(snapshot.model_dump(mode="json")) == snapshot


def test_export_manifest_audit_report_and_pairing_policy_round_trip():
    manifest = ExportManifest(
        export_id="sft_20260502_001",
        format="sft_jsonl",
        source_run_dirs=["runs/run_001"],
        data_files=[{"relative_path": "data.sft.jsonl", "sha256": SHA, "record_count": 1}],
        record_count=1,
        included_count=1,
        filtered_count=0,
        skipped_count=0,
        invalid_count=0,
        diagnostic_only_count=0,
        generated_at="2026-05-02T00:00:00Z",
        exporter_version="repo_harness_exporter_v2_v0",
        audit_report_path="audit_report.json",
        audit_report_sha256=SHA,
        audit_report_md_path="audit_report.md",
        audit_report_md_sha256=SHA_B,
    )
    sample = ExportAuditSample(
        sample_id="sample_001",
        data_file="data.sft.jsonl",
        line_number=1,
        run_id="run_001",
        task_id="task_001",
        training_eligibility="trainable",
        filter_status="included",
        invalid_for_training=False,
        audit_items=[
            ExportAuditItem(
                name="artifact_manifest_valid",
                status="passed",
                severity="info",
                reason="manifest ok",
            )
        ],
    )
    report = ExportAuditReport(
        export_id=manifest.export_id,
        format="sft_jsonl",
        status="passed",
        source_run_dirs=["runs/run_001"],
        data_files=["data.sft.jsonl"],
        generated_at="2026-05-02T00:00:00Z",
        exporter_version="repo_harness_exporter_v2_v0",
        summary={"trainable": 1},
        samples=[sample],
    )
    pairing = PairingPolicy()
    experiment = ExperimentConfig(
        experiment_id="exp_001",
        tasks=["tests/fixtures/tasks/task_001.yaml"],
        rollout_count=2,
    )

    assert ExportManifest.model_validate(manifest.model_dump(mode="json")) == manifest
    assert ExportAuditReport.model_validate(report.model_dump(mode="json")) == report
    assert PairingPolicy.model_validate(pairing.model_dump(mode="json")) == pairing
    assert ExperimentConfig.model_validate(experiment.model_dump(mode="json")) == experiment


def test_invalid_training_eligibility_and_audit_status_are_rejected():
    with pytest.raises(ValidationError):
        ExportRecord(
            sample_id="sample_bad",
            task_id="task_001",
            source_run_id="run_001",
            payload={},
            quality={"training_eligibility": "invalid"},
            invalid_for_training=False,
        )

    with pytest.raises(ValidationError):
        ExportRecord(
            sample_id="sample_bad_enum",
            task_id="task_001",
            source_run_id="run_001",
            payload={},
            quality={"training_eligibility": "maybe"},
        )

    with pytest.raises(ValidationError):
        ExportAuditItem(name="artifact_manifest_valid", status="ok", severity="info", reason="bad")


def test_compare_scope_requires_all_hard_gate_fields():
    with pytest.raises(ValidationError, match="tool_schema_snapshot_hash"):
        CompareScope(canonical_key_fields=["task_id"])


def test_model_request_context_requires_stage_one_core_fields():
    context = ModelRequestContext.model_validate(model_request_context_payload())
    request = ModelGenerationRequest(
        context=context,
        messages=context.prepared_messages,
        tools=context.allowed_tool_definitions,
        provider_options=ModelProviderOptions(provider="replay", model_id="replay-script-v0"),
    )

    assert request.context.model_call_id == "model_call_001"
    required_fields = [
        "tool_schema_snapshot_ref",
        "generation_config",
        "model_call_id",
        "prepared_messages_ref",
        "model_input_hash",
        "context_truncation_facts",
        "budget_state",
        "scaffold_phase",
    ]
    for field in required_fields:
        payload = model_request_context_payload()
        payload.pop(field)
        with pytest.raises(ValidationError):
            ModelRequestContext.model_validate(payload)


def test_fact_refs_use_relative_paths_and_cannot_be_mixed():
    assert RunConfigFactsRef(relative_path="run_config_facts.json", sha256=SHA).sha256 == SHA
    assert RunMetadataRef(relative_path="run_metadata.json", sha256=SHA).sha256 == SHA

    bad_refs = [
        (RunConfigFactsRef, {"relative_path": "/tmp/run_config_facts.json", "sha256": SHA}),
        (RunConfigFactsRef, {"relative_path": "../run_config_facts.json", "sha256": SHA}),
        (RunConfigFactsRef, {"relative_path": "run_metadata.json", "sha256": SHA}),
        (
            RunConfigFactsRef,
            {
                "schema_version": "repo_harness_run_metadata_ref_v2_v0",
                "relative_path": "run_config_facts.json",
                "sha256": SHA,
            },
        ),
        (RunMetadataRef, {"relative_path": "run_config_facts.json", "sha256": SHA}),
        (
            RunMetadataRef,
            {
                "schema_version": "repo_harness_run_config_facts_ref_v2_v0",
                "relative_path": "run_metadata.json",
                "sha256": SHA,
            },
        ),
        (RunMetadataRef, {"relative_path": "run_metadata.json", "sha256": "not-a-sha"}),
    ]
    for ref_cls, payload in bad_refs:
        with pytest.raises(ValidationError):
            ref_cls(**payload)


def test_failure_diagnostics_unknown_fallback_classification():
    diagnostic = FailureDiagnostics.unknown(source_component="unit_test")

    assert diagnostic.failure_category == FailureCategory.unknown_failure
    assert diagnostic.failure_type == FailureType.unknown_failure
    assert diagnostic.recoverable is False


def test_feedback_policy_values_and_oracle_visibility_rules():
    disabled = ResolvedFeedbackPolicyFacts(
        scaffold_default_test_feedback_policy="public_only",
        scaffold_default_feedback_tests_passed_policy="stop_immediately",
        runtime_test_feedback_policy="disabled",
        runtime_feedback_tests_passed_policy=None,
        resolved_test_feedback_policy="disabled",
        resolved_feedback_tests_passed_policy="not_applicable",
        hidden_feedback_visible_to_model=False,
    )

    assert disabled.resolved_feedback_tests_passed_policy == "not_applicable"

    with pytest.raises(ValidationError):
        FeedbackPolicyConfig(
            test_feedback_policy="disabled",
            feedback_tests_passed_policy="not_applicable",
        )

    with pytest.raises(ValidationError, match="oracle_hidden_feedback"):
        ResolvedFeedbackPolicyFacts(
            scaffold_default_test_feedback_policy="oracle_hidden_feedback",
            scaffold_default_feedback_tests_passed_policy="require_model_final",
            resolved_test_feedback_policy="oracle_hidden_feedback",
            resolved_feedback_tests_passed_policy="require_model_final",
            hidden_feedback_visible_to_model=True,
            swe_bench_like_final_only=True,
        )

    with pytest.raises(ValidationError, match="隐藏反馈"):
        ResolvedFeedbackPolicyFacts(
            scaffold_default_test_feedback_policy="public_only",
            scaffold_default_feedback_tests_passed_policy="require_model_final",
            resolved_test_feedback_policy="public_only",
            resolved_feedback_tests_passed_policy="require_model_final",
            hidden_feedback_visible_to_model=True,
        )


def test_run_config_facts_rejects_invalid_feedback_policy_combinations():
    disabled_payload = run_config_facts().model_dump(mode="json")
    disabled_payload["test_feedback_policy"] = "disabled"
    disabled_payload["feedback_tests_passed_policy"] = "stop_immediately"
    with pytest.raises(ValidationError, match="not_applicable"):
        RunConfigFacts.model_validate(disabled_payload)

    not_applicable_payload = run_config_facts().model_dump(mode="json")
    not_applicable_payload["feedback_tests_passed_policy"] = "not_applicable"
    with pytest.raises(ValidationError, match="not_applicable"):
        RunConfigFacts.model_validate(not_applicable_payload)

    oracle_payload = run_config_facts().model_dump(mode="json")
    oracle_payload["test_feedback_policy"] = "oracle_hidden_feedback"
    oracle_payload["hidden_feedback_visible_to_model"] = True
    oracle_payload["swe_bench_like_final_only"] = True
    with pytest.raises(ValidationError, match="oracle_hidden_feedback"):
        RunConfigFacts.model_validate(oracle_payload)


def test_v1_export_record_construction_remains_supported():
    record = ExportRecord(
        sample_id="sample_001",
        task_id="task_001",
        source_run_id="run_001",
        payload={"messages": []},
    )
    invalid = ExportRecord(
        sample_id="sample_invalid",
        task_id="task_001",
        source_run_id="run_001",
        payload={"messages": []},
        invalid_for_training=True,
        invalid_reason="missing_formal_final_verifier",
    )

    assert record.quality.training_eligibility == "trainable"
    assert invalid.quality.training_eligibility == "invalid"
    assert invalid.invalid_for_training is True


def test_workspace_protocol_schemas_are_strict():
    paths = WorkspacePaths(run_dir="runs/run_001", workspaces_dir="runs/run_001/workspaces")
    result = WorkspaceCommandResult(
        exit_code=0,
        execution_backend=WorkspaceBackend.local_process,
        output_artifact_ref=artifact_ref("stdout", "stdout"),
    )

    assert paths.workspaces_dir.endswith("workspaces")
    assert result.execution_backend == WorkspaceBackend.local_process
