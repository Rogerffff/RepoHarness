from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repo_harness.config import ContextManagementConfig
from repo_harness.context.auto_compact import AutoCompactRunner
from repo_harness.context.schemas import PreparedMessages
from repo_harness.context.tool_result_artifacts import (
    ToolResultArtifactIndex,
    persist_tool_result_content,
)
from repo_harness.model_client import (
    ModelMessage,
    ModelProviderOptions,
    ModelRequestContext,
    ModelResponse,
)
from repo_harness.run_metadata import RunConfigFactsRef
from repo_harness.schema_base import stable_hash
from repo_harness.trajectory import ArtifactRef, RunRecorder, TrajectoryEvent, read_jsonl


def test_auto_compact_runner_applies_summary_with_compact_only_request(tmp_path: Path) -> None:
    recorder = RunRecorder(run_id="run-auto", task_id="task-1", run_dir=tmp_path / "run")
    source = _source_prepared(recorder)
    tool_index = ToolResultArtifactIndex(run_dir=recorder.run_dir)
    artifact = persist_tool_result_content(
        recorder=recorder,
        tool_result_id="tool_result_1",
        tool_call_id="tool_1",
        tool_name="grep",
        content="full grep output",
        publishable_after_visibility_scan=True,
        contamination_scan_status="clean",
    )
    tool_index.add(artifact)
    tool_index.unlock_after_provider_commit(artifact.artifact_id)
    client = _CompactFakeClient(
        content=json.dumps(_summary_payload(artifact_id=artifact.artifact_id, sha256=artifact.content_sha256))
    )

    result = AutoCompactRunner().run(
        mode="proactive",
        trigger_reason="projection_above_auto_compact_trigger",
        source_prepared=source,
        recorder=recorder,
        task_id="task-1",
        turn=3,
        context_config=ContextManagementConfig(),
        provider_options=ModelProviderOptions(provider="mock", model_id="mock-v0"),
        model_client=client,
        tool_schema_snapshot_ref=_artifact_ref(recorder, "tool_schema_snapshot"),
        run_config_facts_ref=RunConfigFactsRef(sha256="1" * 64),
        tool_result_artifact_index=tool_index,
    )

    assert result.status == "applied"
    assert result.summary is not None
    assert result.summary_artifact_ref is not None
    assert result.compact_model_request_ref is not None
    assert result.compact_model_response_ref is not None
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request.scaffold_phase == "compact"
    assert request.allowed_tool_definitions == []
    assert request.tool_choice == "none"
    assert request.provider_message_format == "repo_harness_compact_summary_request_v0"
    assert request.generation_config["max_output_tokens"] == 16000
    assert not recorder.transcript_path.read_text(encoding="utf-8").strip()

    source_payload = _read_artifact(recorder, result.compact_source_messages_ref)
    assert "typed" not in json.dumps(source_payload, ensure_ascii=False)
    assert source_payload["compact_request_messages"][0]["role"] == "system"
    assert result.compact_source_projection_hash == request.provider_request_projection_hash

    rebuilt_text = json.dumps(result.rebuilt_messages, ensure_ascii=False)
    assert "repo_harness_auto_compact_boundary" in rebuilt_text
    assert "repo_harness_auto_compact_summary" in rebuilt_text
    assert "repo_harness_auto_compact_recovery_index" in rebuilt_text
    assert artifact.artifact_id in rebuilt_text
    assert "Fix calculator division by zero." in rebuilt_text
    assert "typed" not in rebuilt_text

    event_types = [event["event_type"] for event in read_jsonl(recorder.events_path)]
    assert "auto_compact_model_call_started" in event_types
    assert "auto_compact_model_call_completed" in event_types
    assert "auto_compact_applied" in event_types


def test_auto_compact_runner_rejects_non_json_summary(tmp_path: Path) -> None:
    recorder = RunRecorder(run_id="run-auto", task_id="task-1", run_dir=tmp_path / "run")
    source = _source_prepared(recorder)
    client = _CompactFakeClient(content="not json")

    result = AutoCompactRunner().run(
        mode="proactive",
        trigger_reason="projection_above_auto_compact_trigger",
        source_prepared=source,
        recorder=recorder,
        task_id="task-1",
        turn=3,
        context_config=ContextManagementConfig(),
        provider_options=ModelProviderOptions(provider="mock", model_id="mock-v0"),
        model_client=client,
        tool_schema_snapshot_ref=_artifact_ref(recorder, "tool_schema_snapshot"),
        run_config_facts_ref=RunConfigFactsRef(sha256="1" * 64),
    )

    assert result.status == "failed"
    assert result.failure_reason == "invalid_compact_summary:JSONDecodeError"
    assert result.summary_artifact_ref is None
    assert len(client.requests) == 1
    event_types = [event["event_type"] for event in read_jsonl(recorder.events_path)]
    assert "auto_compact_failed" in event_types


def test_auto_compact_runner_rejects_forbidden_summary_content(tmp_path: Path) -> None:
    recorder = RunRecorder(run_id="run-auto", task_id="task-1", run_dir=tmp_path / "run")
    source = _source_prepared(recorder)
    payload = _summary_payload()
    payload["repository_facts"] = ["gold patch contained the answer"]
    client = _CompactFakeClient(content=json.dumps(payload))

    result = AutoCompactRunner().run(
        mode="proactive",
        trigger_reason="projection_above_auto_compact_trigger",
        source_prepared=source,
        recorder=recorder,
        task_id="task-1",
        turn=3,
        context_config=ContextManagementConfig(),
        provider_options=ModelProviderOptions(provider="mock", model_id="mock-v0"),
        model_client=client,
        tool_schema_snapshot_ref=_artifact_ref(recorder, "tool_schema_snapshot"),
        run_config_facts_ref=RunConfigFactsRef(sha256="1" * 64),
    )

    assert result.status == "failed"
    assert result.failure_reason == "invalid_compact_summary:ValueError"
    assert result.summary_artifact_ref is None


def test_auto_compact_runner_rejects_unlocked_recovery_claims(tmp_path: Path) -> None:
    recorder = RunRecorder(run_id="run-auto", task_id="task-1", run_dir=tmp_path / "run")
    source = _source_prepared(recorder)
    client = _CompactFakeClient(
        content=json.dumps(_summary_payload(artifact_id="unregistered", sha256="2" * 64))
    )

    result = AutoCompactRunner().run(
        mode="proactive",
        trigger_reason="projection_above_auto_compact_trigger",
        source_prepared=source,
        recorder=recorder,
        task_id="task-1",
        turn=3,
        context_config=ContextManagementConfig(),
        provider_options=ModelProviderOptions(provider="mock", model_id="mock-v0"),
        model_client=client,
        tool_schema_snapshot_ref=_artifact_ref(recorder, "tool_schema_snapshot"),
        run_config_facts_ref=RunConfigFactsRef(sha256="1" * 64),
        tool_result_artifact_index=ToolResultArtifactIndex(run_dir=recorder.run_dir),
    )

    assert result.status == "failed"
    assert result.failure_reason == "invalid_compact_summary:ValueError"
    assert result.summary_artifact_ref is None


def test_auto_compact_runner_rejects_mismatched_recovery_claim_metadata(
    tmp_path: Path,
) -> None:
    recorder = RunRecorder(run_id="run-auto", task_id="task-1", run_dir=tmp_path / "run")
    source = _source_prepared(recorder)
    tool_index = ToolResultArtifactIndex(run_dir=recorder.run_dir)
    artifact = persist_tool_result_content(
        recorder=recorder,
        tool_result_id="tool_result_1",
        tool_call_id="tool_1",
        tool_name="grep",
        content="full grep output",
        publishable_after_visibility_scan=True,
        contamination_scan_status="clean",
    )
    tool_index.add(artifact)
    tool_index.unlock_after_provider_commit(artifact.artifact_id)
    payload = _summary_payload(artifact_id=artifact.artifact_id, sha256=artifact.content_sha256)
    payload["tool_recovery_index"][0]["tool_call_id"] = "wrong_tool_call"
    client = _CompactFakeClient(content=json.dumps(payload))

    result = AutoCompactRunner().run(
        mode="proactive",
        trigger_reason="projection_above_auto_compact_trigger",
        source_prepared=source,
        recorder=recorder,
        task_id="task-1",
        turn=3,
        context_config=ContextManagementConfig(),
        provider_options=ModelProviderOptions(provider="mock", model_id="mock-v0"),
        model_client=client,
        tool_schema_snapshot_ref=_artifact_ref(recorder, "tool_schema_snapshot"),
        run_config_facts_ref=RunConfigFactsRef(sha256="1" * 64),
        tool_result_artifact_index=tool_index,
    )

    assert result.status == "failed"
    assert result.failure_reason == "invalid_compact_summary:ValueError"
    assert result.summary_artifact_ref is None


def test_auto_compact_runner_skips_model_call_when_source_projection_is_too_large(
    tmp_path: Path,
) -> None:
    recorder = RunRecorder(run_id="run-auto", task_id="task-1", run_dir=tmp_path / "run")
    source = _source_prepared(recorder, extra_content="x" * 8000)
    client = _CompactFakeClient(content=json.dumps(_summary_payload()))
    config = ContextManagementConfig(
        model_context_window_tokens=500,
        main_output_reserve_tokens=0,
        estimator_safety_margin_ratio=0.0,
        estimator_safety_margin_min_tokens=0,
        hard_context_limit_ratio=0.2,
        post_compact_target_max_tokens=300,
    )

    result = AutoCompactRunner().run(
        mode="proactive",
        trigger_reason="projection_above_auto_compact_trigger",
        source_prepared=source,
        recorder=recorder,
        task_id="task-1",
        turn=3,
        context_config=config,
        provider_options=ModelProviderOptions(provider="mock", model_id="mock-v0"),
        model_client=client,
        tool_schema_snapshot_ref=_artifact_ref(recorder, "tool_schema_snapshot"),
        run_config_facts_ref=RunConfigFactsRef(sha256="1" * 64),
    )

    assert result.status == "failed"
    assert result.failure_reason == "auto_compact_source_too_large"
    assert client.requests == []
    event_types = [event["event_type"] for event in read_jsonl(recorder.events_path)]
    assert "auto_compact_model_call_started" not in event_types
    assert "auto_compact_failed" in event_types


class _CompactFakeClient:
    def __init__(self, *, content: str) -> None:
        self.content = content
        self.requests: list[ModelRequestContext] = []

    def generate(self, *, request: ModelRequestContext, recorder: RunRecorder) -> ModelResponse:
        self.requests.append(request)
        raw_request_ref = recorder.write_json_artifact(
            "raw_fake_compact_request",
            {
                "model_call_id": request.model_call_id,
                "messages": request.prepared_messages,
                "tools": request.allowed_tool_definitions,
                "tool_choice": request.tool_choice,
                "scaffold_phase": request.scaffold_phase,
                "provider_request_projection_hash": request.provider_request_projection_hash,
            },
            {"budget_policy": "preserve_json"},
        )
        raw_response_ref = recorder.write_json_artifact(
            "raw_fake_compact_response",
            {"content": self.content},
            {"budget_policy": "preserve_json"},
        )
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content=self.content),
            raw_provider_request_ref=raw_request_ref,
            raw_provider_response_ref=raw_response_ref,
            finish_reason="stop",
        )


def _source_prepared(recorder: RunRecorder, *, extra_content: str = "") -> PreparedMessages:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "Fix calculator division by zero."},
        {
            "role": "assistant",
            "turn": 1,
            "content": None,
            "tool_calls": [
                {
                    "tool_call_id": "tool_1",
                    "tool_name": "grep",
                    "arguments": {"pattern": "divide"},
                }
            ],
        },
        {
            "role": "tool",
            "turn": 1,
            "tool_call_id": "tool_1",
            "tool_result_id": "tool_result_1",
            "content": f"divide appears in calculator.py {extra_content}",
            "typed": {"verifier_result_preview": {"accepted": False}},
        },
        {"role": "user", "turn": 2, "content": "Continue from the grep result."},
    ]
    ref = recorder.write_json_artifact(
        "prepared_messages",
        {"messages": messages, "model_input_hash": stable_hash(messages)},
        {"budget_policy": "preserve_json"},
    )
    event = TrajectoryEvent(
        event_id=recorder.next_event_id("context"),
        timestamp="2026-05-10T00:00:00+00:00",
        run_id=recorder.run_id,
        task_id=recorder.task_id,
        turn=2,
        event_type="context_prepared",
        artifact_refs=[ref],
        data={"model_input_hash": stable_hash(messages)},
    )
    return PreparedMessages(
        messages=messages,
        prepared_messages_ref=ref,
        model_input_hash=stable_hash(messages),
        context_revision=2,
        context_event=event,
        token_estimate=max(1, len(json.dumps(messages, ensure_ascii=False)) // 4),
        internal_char_estimate=len(json.dumps(messages, ensure_ascii=False)),
        internal_token_estimate=max(1, len(json.dumps(messages, ensure_ascii=False)) // 4),
        provider_body_char_estimate=len(json.dumps(messages, ensure_ascii=False)),
        provider_ready_token_estimate=max(1, len(json.dumps(messages, ensure_ascii=False)) // 4),
    )


def _summary_payload(
    *,
    artifact_id: str | None = None,
    sha256: str | None = None,
) -> dict[str, Any]:
    recovery = []
    if artifact_id is not None:
        recovery.append(
            {
                "tool_result_id": "tool_result_1",
                "tool_call_id": "tool_1",
                "tool_name": "grep",
                "artifact_id": artifact_id,
                "sha256": sha256,
                "recovery_status": "artifact_recoverable",
            }
        )
    return {
        "schema_version": "repo_harness_compact_summary_v1",
        "task_intent": "Fix calculator division by zero while preserving public context.",
        "repository_facts": ["calculator.py contains divide."],
        "actions_taken": ["Searched for divide."],
        "patch_state": {
            "changed_files": ["calculator.py"],
            "important_diffs": ["divide should raise ValueError for zero divisor."],
        },
        "test_state": {
            "commands_run": ["pytest -q"],
            "passing": [],
            "failing": [],
            "unknown": ["Full verification still needs to run."],
        },
        "tool_recovery_index": recovery,
        "open_questions": [],
        "next_step": "Edit calculator.py and run the public tests.",
        "visibility_policy": "model_visible_only",
    }


def _artifact_ref(recorder: RunRecorder, kind: str) -> ArtifactRef:
    return recorder.write_json_artifact(kind, {"kind": kind}, {"budget_policy": "preserve_json"})


def _read_artifact(recorder: RunRecorder, ref: ArtifactRef | None) -> dict[str, Any]:
    assert ref is not None
    return json.loads((recorder.run_dir / ref.relative_path).read_text(encoding="utf-8"))
