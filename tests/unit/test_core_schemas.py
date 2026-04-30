import importlib
import pkgutil

import pytest

import repo_harness
from repo_harness.agent_loop import AgentLoopState, ToolPairingState
from repo_harness.budget import BudgetManager, BudgetState
from repo_harness.context import (
    ContentReplacementRecord,
    ContentReplacementState,
    ContextReductionRecord,
    PreparedMessages,
)
from repo_harness.evaluation import BaselineResult, ResolvedVerifierPlan
from repo_harness.export import ExportPolicy, ExportRecord
from repo_harness.model_client import ModelCallEvent, ModelMessage, ModelResponse
from repo_harness.permissions import PermissionDecision
from repo_harness.reward import RewardMetadata
from repo_harness.tools import ToolCall, ToolResult
from repo_harness.trajectory import ArtifactRef, MetricsRecord, TrajectoryEvent, TranscriptRecord
from repo_harness.verifier import TestCaseResult, VerifierResult
from repo_harness.workspace import DependencyState, ExecutionResult, RunWorkspace
from repo_harness.schema_base import StrictBaseModel

from tests.unit.test_task_schema import valid_task_payload
from repo_harness.tasks import TaskDefinition


def artifact_ref(artifact_id="artifact_001"):
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=f"artifacts/{artifact_id}.txt",
        kind="text",
        sha256="0" * 64,
        size_bytes=12,
        created_by_event_id="event_001",
    )


def verifier_config():
    return TaskDefinition.model_validate(valid_task_payload()).to_verifier_config()


def assert_round_trip(model):
    dumped = model.model_dump(mode="json")
    assert model.__class__.model_validate(dumped) == model


def test_core_schema_round_trips():
    ref = artifact_ref()
    event = TrajectoryEvent(
        event_id="event_001",
        timestamp="2026-04-30T00:00:00Z",
        run_id="run_001",
        task_id="task_001",
        event_type="unit_test",
        artifact_refs=[ref],
    )
    transcript = TranscriptRecord(
        record_id="record_001",
        run_id="run_001",
        task_id="task_001",
        message_id="msg_001",
        turn=0,
        role="system",
        content_preview="system",
        content_artifact_refs=[ref],
        model_visible=True,
        trainable=False,
        created_at="2026-04-30T00:00:00Z",
    )
    execution = ExecutionResult(exit_code=0, output_artifact_ref=ref)
    dependency = DependencyState(strategy="none", artifact_ref=ref)
    workspace = RunWorkspace(
        run_id="run_001",
        workspace_path="runs/run_001/workspaces/agent",
        artifact_dir="runs/run_001/artifacts",
        dependency_state=dependency,
    )
    test_case = TestCaseResult(test_id="tests/test_demo.py::test_ok", status="passed")
    verifier = VerifierResult(
        parser_confidence=0.95,
        command="pytest -q",
        test_cases=[test_case],
        accepted=True,
        pass_ratio=1.0,
        fail_to_pass={"passed": 1, "total": 1},
        pass_to_pass={"passed": 1, "total": 1},
        exit_code=0,
    )
    baseline = BaselineResult(
        task_id="task_001",
        status="invalid",
        baseline_verifier_result_ref=ref,
        dependency_state=dependency,
    )
    resolved = ResolvedVerifierPlan(
        verifier_config=verifier_config(),
        parser_confidence=0.95,
        resolved_verifier_plan_id="plan_001",
    )
    reward = RewardMetadata(
        final_reward=1.0,
        formula="accepted",
        components={"accepted_bonus": 1.0},
    )
    metrics = MetricsRecord(run_outcome="success", task_success=True, final_verifier_status="accepted")
    tool_call = ToolCall(tool_call_id="tool_001", tool_name="read_file", arguments={"path": "a.py"}, turn=1)
    tool_result = ToolResult(
        tool_result_id="tool_result_001",
        tool_call_id="tool_001",
        tool_name="read_file",
        requested_tool_name="read_file",
        effective_tool_name="read_file",
        normalized_input_hash="1" * 64,
        status="ok",
        content_preview="content",
        artifact_refs=[ref],
    )
    permission = PermissionDecision(
        decision_id="decision_001",
        tool_call_id="tool_001",
        tool_name="read_file",
        requested_tool_name="read_file",
        effective_tool_name="read_file",
        decision="allow",
        mode="auto",
        reason="read in workspace",
        normalized_input_hash="1" * 64,
    )
    replacement = ContentReplacementRecord(
        tool_call_id="tool_001",
        original_tool_result_id="tool_result_001",
        replaced=True,
        first_visible_form="preview",
        first_visible_content_hash="2" * 64,
        replacement_allowed_after_first_seen=True,
        replacement_text_hash="3" * 64,
        first_seen_at_context_revision=1,
        first_replaced_at_context_revision=2,
    )
    replacement_state = ContentReplacementState(
        seen_tool_result_ids=["tool_result_001"],
        records=[replacement],
        state_hash="4" * 64,
        last_context_revision=2,
    )
    reduction = ContextReductionRecord(context_revision=2, replaced_tool_result_ids=["tool_result_001"])
    prepared = PreparedMessages(
        messages=[{"role": "system", "content": "hi"}],
        prepared_messages_ref=ref,
        model_input_hash="5" * 64,
        context_revision=2,
        context_event=event,
        content_replacement_state=replacement_state,
        token_estimate=10,
    )
    model_event = ModelCallEvent(
        model_call_id="model_call_001",
        model_id="replay",
        context_revision=2,
        prepared_messages_ref=ref,
        model_input_hash="5" * 64,
        provider_message_format="repo_harness_messages_v0",
        tool_schema_hash="6" * 64,
    )
    model_response = ModelResponse(
        assistant_message=ModelMessage(role="assistant", tool_calls=[tool_call]),
        tool_calls=[tool_call],
        model_call_event=model_event,
    )
    budget_manager = BudgetManager(
        max_turns=2,
        max_tool_calls=4,
        max_test_runs=1,
        task_timeout_sec=30,
        command_timeout_sec=10,
        verifier_timeout_sec=20,
        max_tool_output_chars=1000,
        max_context_tokens=1000,
        max_output_tokens=200,
    )
    budget_state = BudgetState(started_at="2026-04-30T00:00:00Z")
    agent_state = AgentLoopState(
        run_id="run_001",
        task_id="task_001",
        budget_state=budget_state,
        tool_pairing_state=ToolPairingState(),
    )
    export_policy = ExportPolicy()
    export_record = ExportRecord(
        sample_id="sample_001",
        task_id="task_001",
        source_run_id="run_001",
        payload={"messages": []},
    )

    for model in [
        ref,
        event,
        transcript,
        execution,
        dependency,
        workspace,
        verifier,
        baseline,
        resolved,
        reward,
        metrics,
        tool_call,
        tool_result,
        permission,
        replacement,
        replacement_state,
        reduction,
        prepared,
        model_event,
        model_response,
        budget_manager,
        budget_state,
        agent_state,
        export_policy,
        export_record,
    ]:
        assert_round_trip(model)

    assert baseline.can_enter_agent_run is False
    assert agent_state.agent_stop_reason is None


def test_all_strict_schema_classes_have_schema_version():
    missing: list[str] = []
    for module_info in pkgutil.walk_packages(repo_harness.__path__, repo_harness.__name__ + "."):
        if not module_info.name.endswith("schemas"):
            continue
        module = importlib.import_module(module_info.name)
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, StrictBaseModel) and value is not StrictBaseModel:
                if "schema_version" not in value.model_fields:
                    missing.append(f"{value.__module__}.{value.__name__}")

    assert missing == []


def test_baseline_invalid_and_flaky_do_not_enter_agent_run():
    invalid = BaselineResult(task_id="task_invalid", status="invalid")
    flaky = BaselineResult(task_id="task_flaky", status="flaky")
    valid = BaselineResult(task_id="task_valid", status="valid")

    assert invalid.can_enter_agent_run is False
    assert flaky.can_enter_agent_run is False
    assert valid.can_enter_agent_run is True


def test_export_record_rejects_hidden_metadata_and_absolute_paths():
    with pytest.raises(ValueError, match="gold_patch"):
        ExportRecord(
            sample_id="sample_hidden",
            task_id="task_001",
            source_run_id="run_001",
            payload={"gold_patch": "diff --git ..."},
        )

    with pytest.raises(ValueError, match="absolute_path|local_absolute_path"):
        ExportRecord(
            sample_id="sample_path",
            task_id="task_001",
            source_run_id="run_001",
            payload={"artifact": "/Users/roger/Desktop/secret.txt"},
        )


def test_reward_invalid_training_requires_reason():
    try:
        RewardMetadata(final_reward=0.0, formula="accepted", invalid_for_training=True)
    except ValueError as exc:
        assert "invalid_reason" in str(exc)
    else:
        raise AssertionError("RewardMetadata should reject invalid samples without a reason")
