from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from repo_harness.config import RunConfig
from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.execution import EpisodeExecutionSpec, EpisodeExecutionSpecBuilder
from repo_harness.rl import (
    EpisodeBudgets,
    EpisodeTaskRef,
    FakeLLMGateway,
    LLMGatewayResponse,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
    RepoHarnessRuntimeOptions,
)
from repo_harness.tasks import EnvironmentSpec, RunnableTask, TaskTimeouts, VerifierConfig, VisibilityPolicy
from repo_harness.verifier import VerifierResult
from repo_harness.workspace import DependencyState, RunWorkspace


def _source_repo(tmp_path: Path) -> Path:
    source = tmp_path / "source_repo"
    source.mkdir()
    (source / "tests").mkdir()
    (source / "README.md").write_text("stage16f2 real episode repo\n", encoding="utf-8")
    (source / "pkg.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "tests" / "test_public.py").write_text(
        "def test_existing():\n    assert True\n",
        encoding="utf-8",
    )
    return source


def _task() -> RunnableTask:
    visibility = VisibilityPolicy()
    verifier = VerifierConfig(
        test_command="python -m pytest tests/test_public.py -q",
        test_timeout_sec=30,
        final_verifier_timeout_sec=60,
        fail_to_pass_tests=["tests/test_hidden.py::test_fix"],
        pass_to_pass_tests=["tests/test_public.py::test_existing"],
        visibility_policy=visibility,
    )
    return RunnableTask(
        task_id="stage16f2_task",
        task_version="v1",
        dataset_name="stage16f2_fixture",
        issue_statement="Update the package behaviour.",
        repo_source="stage16f2_repo",
        environment=EnvironmentSpec(),
        timeouts=TaskTimeouts(
            setup_timeout_sec=30,
            test_timeout_sec=30,
            agent_timeout_sec=120,
            final_verifier_timeout_sec=60,
        ),
        verifier_config=verifier,
        expected_files=["pkg.py"],
        visibility_policy=visibility,
    )


def _run_config() -> RunConfig:
    return RunConfig.model_validate(
        {
            "model": {"provider": "fake", "model_id": "fake-stage16f2"},
            "runtime": {
                "scaffold_id": "patch_focused_react_diagnostic_shell",
                "permission_mode": "auto",
                "test_feedback_policy": "public_only",
                "feedback_tests_passed_policy": "require_model_final",
                "max_turns": 3,
                "max_tool_calls": 5,
                "max_test_runs": 2,
            },
            "workspace": {
                "network_policy": "deny_agent_run",
                "max_tool_output_chars": 8000,
            },
        }
    )


def _resolved_plan(task: RunnableTask, run_id: str) -> ResolvedVerifierPlan:
    return ResolvedVerifierPlan(
        verifier_config=task.verifier_config,
        initial_fail_to_pass_tests=["tests/test_hidden.py::test_fix"],
        initial_pass_to_pass_tests=["tests/test_public.py::test_existing"],
        flaky_tests=[],
        parser_confidence=1.0,
        resolved_verifier_plan_id=f"{run_id}_verifier_plan",
    )


def _spec(tmp_path: Path, source: Path, *, run_id: str = "stage16f2_run") -> EpisodeExecutionSpec:
    task = _task()
    run_config = _run_config()
    workspace = RunWorkspace(
        run_id=run_id,
        workspace_path=source.as_posix(),
        repo_base_commit="stage16f2-base",
        execution_mode="local_process",
        artifact_dir=(tmp_path / "artifacts").as_posix(),
        dependency_state=DependencyState(),
    )
    return EpisodeExecutionSpecBuilder().build_spec_from_loaded_task(
        task=task,
        workspace=workspace,
        run_config=run_config,
        resolved_verifier_plan=_resolved_plan(task, run_id),
        run_id=run_id,
        task_ref="rh://task/stage16f2_task",
    )


def _request(spec: EpisodeExecutionSpec, **updates: Any) -> RepoHarnessEpisodeRequest:
    payload: dict[str, Any] = {
        "episode_id": "stage16f2_episode",
        "run_id": spec.run_id,
        "task_id": spec.task_id,
        "llm_gateway_route": "verl",
        "inference_backend": "sglang",
        "raw_prompt": [],
        "raw_prompt_source": "episode_execution_spec",
        "episode_execution_spec_ref": f"rh://episode-execution-spec/{spec.spec_payload_sha256}",
        "episode_execution_spec_sha256": spec.spec_payload_sha256,
        "task_definition_sha256": spec.task_facts.task_definition_sha256,
        "run_config_sha256": spec.run_config_facts.run_config_sha256,
        "permission_mode": spec.run_config_facts.permission_mode,
        "network_policy": spec.run_config_facts.network_policy,
        "run_mode_hint": spec.run_config_facts.run_mode_hint,
        "allowed_tool_names": spec.allowed_tool_names,
        "tool_registry_digest": spec.tool_facts.tool_registry_digest,
        "resolved_verifier_plan_digest": spec.verifier_facts.resolved_verifier_plan_digest,
        "test_feedback_policy": spec.feedback_facts.test_feedback_policy,
        "feedback_tests_passed_policy": spec.feedback_facts.feedback_tests_passed_policy,
        "task_ref": {
            "task_id": spec.task_id,
            "task_ref": "rh://task/stage16f2_task",
            "repo_ref": spec.task_facts.repo_ref,
            "base_commit": spec.task_facts.base_commit,
        },
        "budgets": EpisodeBudgets(
            max_turns=spec.budget_facts.max_turns,
            max_tool_calls=spec.budget_facts.max_tool_calls,
            max_test_runs=spec.budget_facts.max_test_runs,
            max_tool_observation_tokens=spec.budget_facts.max_tool_output_chars,
            max_model_calls=4,
            max_output_tokens=16,
            max_artifact_bytes=2_000_000,
        ).model_dump(mode="json"),
        "run_mode": "training_fast",
    }
    payload.update(updates)
    return RepoHarnessEpisodeRequest.model_validate(payload)


def _final_response() -> LLMGatewayResponse:
    return LLMGatewayResponse(
        route="verl",
        inference_backend="sglang",
        model_call_id="stage16f2-call-0",
        assistant_message={"role": "assistant", "content": "done"},
        tool_calls=[],
        prompt_ids=[101, 102],
        output_token_ids=[9001],
        output_logprobs=[-0.12],
        response_mask=[1],
        stop_reason="stop",
        usage={"input_tokens": 2, "output_tokens": 1},
        provider_request_id="stage16f2-provider-0",
    )


def _run_tests_response() -> LLMGatewayResponse:
    return LLMGatewayResponse(
        route="verl",
        inference_backend="sglang",
        model_call_id="stage16f2-call-run-tests",
        assistant_message={"role": "assistant", "content": "I will run the public tests."},
        tool_calls=[
            {
                "tool_call_id": "call_run_tests",
                "tool_name": "run_tests",
                "arguments": {},
            }
        ],
        prompt_ids=[101, 103],
        output_token_ids=[9002],
        output_logprobs=[-0.17],
        response_mask=[1],
        stop_reason="tool_calls",
        usage={"input_tokens": 2, "output_tokens": 1},
        provider_request_id="stage16f2-provider-run-tests",
    )


def _runtime(tmp_path: Path, source: Path) -> RepoHarnessRuntime:
    def verifier_factory(_context):
        return lambda: VerifierResult(
            verifier_stage="final",
            parser_confidence=1.0,
            command="python -m pytest tests/test_public.py -q",
            accepted=True,
            pass_ratio=1.0,
            fail_to_pass={"passed": 1, "total": 1},
            pass_to_pass={"passed": 1, "total": 1},
            exit_code=0,
        )

    return RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(
            runtime_execution_mode="real_episode",
            output_dir=tmp_path / "runs",
            real_episode_source_resolver=lambda _request: source,
            real_episode_final_verifier_factory=verifier_factory,
            tool_observation_token_projector=lambda _content: [77_001],
        )
    )


def test_stage16f2_real_episode_consumes_spec_messages_tools_and_verifier(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    spec = _spec(tmp_path, source)
    request = _request(spec)
    gateway = FakeLLMGateway([_final_response()])
    runtime = _runtime(tmp_path, source)

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway, execution_spec=spec))

    assert result.status == "succeeded"
    assert gateway.requests
    first_request = gateway.requests[0]
    assert first_request.messages == spec.initial_messages
    assert any(tool["name"] == "diagnostic_shell" for tool in first_request.tools)
    assert result.invalid_for_training is False
    assert result.invalid_for_online_rl is False


def test_stage16f2_spec_public_feedback_run_tests_returns_structured_result(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    spec = _spec(tmp_path, source, run_id="stage16f2_run_tests")
    request = _request(spec, episode_id="stage16f2_episode_run_tests")
    gateway = FakeLLMGateway([_run_tests_response(), _final_response()])

    result = asyncio.run(_runtime(tmp_path, source).run_episode(request, llm_gateway=gateway, execution_spec=spec))

    assert result.status == "succeeded"
    run_dir = tmp_path / "runs" / spec.run_id
    visible_evidence = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted(run_dir.rglob("*.json*"))
        if path.is_file()
    )
    assert "NoneType" not in visible_evidence
    assert "call_run_tests" in visible_evidence
    assert "feedback_verifier_result" in visible_evidence
    events = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    run_tests_event = next(
        event
        for event in events
        if event["event_type"] == "tool_completed"
        and event["data"].get("effective_tool_name") == "run_tests"
    )
    typed = run_tests_event["data"]["typed"]
    assert typed["public_tests_ran"] is True
    assert typed["hidden_feedback_ran"] is False
    assert typed["verifier_result_preview"]["accepted"] is True


def test_stage16f2_request_task_id_mismatch_is_rejected_before_generation(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    spec = _spec(tmp_path, source)
    request = _request(spec, task_id="stage16f2_other_task")
    gateway = FakeLLMGateway([_final_response()])

    result = asyncio.run(_runtime(tmp_path, source).run_episode(request, llm_gateway=gateway, execution_spec=spec))

    assert result.status == "invalid_task"
    assert result.status_reason == "episode_execution_spec_mismatch"
    assert any("task_id" in diagnostic.message for diagnostic in result.audit_diagnostics)
    assert gateway.requests == []


def test_stage16f2_request_task_ref_mismatch_is_rejected_before_generation(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    spec = _spec(tmp_path, source)
    request = _request(
        spec,
        task_ref={
            "task_id": spec.task_id,
            "task_ref": "rh://task/other-task",
        },
    )
    gateway = FakeLLMGateway([_final_response()])

    result = asyncio.run(_runtime(tmp_path, source).run_episode(request, llm_gateway=gateway, execution_spec=spec))

    assert result.status == "invalid_task"
    assert any("task_ref" in diagnostic.message for diagnostic in result.audit_diagnostics)
    assert gateway.requests == []


def test_stage16f2_request_base_commit_mismatch_is_rejected_before_generation(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    spec = _spec(tmp_path, source)
    request = _request(
        spec,
        task_ref={
            "task_id": spec.task_id,
            "task_ref": spec.task_facts.task_ref,
            "repo_ref": spec.task_facts.repo_ref,
            "base_commit": "other-base-commit",
        },
    )
    gateway = FakeLLMGateway([_final_response()])

    result = asyncio.run(_runtime(tmp_path, source).run_episode(request, llm_gateway=gateway, execution_spec=spec))

    assert result.status == "invalid_task"
    assert any("base_commit" in diagnostic.message for diagnostic in result.audit_diagnostics)
    assert gateway.requests == []


def test_stage16f2_request_budget_mismatch_is_rejected_before_generation(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    spec = _spec(tmp_path, source)
    budgets = EpisodeBudgets(
        max_turns=99,
        max_tool_calls=spec.budget_facts.max_tool_calls,
        max_test_runs=spec.budget_facts.max_test_runs,
        max_tool_observation_tokens=spec.budget_facts.max_tool_output_chars,
    ).model_dump(mode="json")
    request = _request(spec, budgets=budgets)
    gateway = FakeLLMGateway([_final_response()])

    result = asyncio.run(_runtime(tmp_path, source).run_episode(request, llm_gateway=gateway, execution_spec=spec))

    assert result.status == "invalid_task"
    assert any("max_turns" in diagnostic.message for diagnostic in result.audit_diagnostics)
    assert gateway.requests == []


def test_stage16f2_request_raw_prompt_mismatch_is_rejected_before_generation(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    spec = _spec(tmp_path, source)
    request = _request(
        spec,
        raw_prompt_source="external",
        raw_prompt=[{"role": "user", "content": {"task": "wrong prompt"}}],
    )
    gateway = FakeLLMGateway([_final_response()])

    result = asyncio.run(_runtime(tmp_path, source).run_episode(request, llm_gateway=gateway, execution_spec=spec))

    assert result.status == "invalid_task"
    assert any("raw_prompt_digest" in diagnostic.message for diagnostic in result.audit_diagnostics)
    assert gateway.requests == []


def test_stage16f2_request_spec_digest_mismatch_is_rejected_before_generation(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    spec = _spec(tmp_path, source)
    request = _request(spec, episode_execution_spec_sha256="0" * 64)
    gateway = FakeLLMGateway([_final_response()])

    result = asyncio.run(_runtime(tmp_path, source).run_episode(request, llm_gateway=gateway, execution_spec=spec))

    assert result.status == "invalid_task"
    assert any("episode_execution_spec_sha256" in diagnostic.message for diagnostic in result.audit_diagnostics)
    assert gateway.requests == []


def test_stage16f2_runtime_verifier_plan_tamper_is_rejected_before_generation(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    spec = _spec(tmp_path, source)
    other_plan = _resolved_plan(_task(), "stage16f2_other_run").model_copy(
        update={"resolved_verifier_plan_id": "stage16f2_other_plan"}
    )
    tampered = spec.model_copy(update={"runtime_resolved_verifier_plan": other_plan})
    request = _request(spec)
    gateway = FakeLLMGateway([_final_response()])

    result = asyncio.run(_runtime(tmp_path, source).run_episode(request, llm_gateway=gateway, execution_spec=tampered))

    assert result.status == "invalid_task"
    assert any("verifier_plan_digest_mismatch" in diagnostic.message for diagnostic in result.audit_diagnostics)
    assert gateway.requests == []
