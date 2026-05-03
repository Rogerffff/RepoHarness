from __future__ import annotations

import json
from pathlib import Path

from repo_harness.agent_loop import AgentLoop
from repo_harness.config import RunConfig
from repo_harness.model_client import FakeModelClient
from repo_harness.run_metadata.tool_snapshot import build_tool_schema_snapshot
from repo_harness.scaffolds import (
    PATCH_FOCUSED_REACT_TOOL_ORDER,
    build_scaffold,
    resolve_allowed_tools,
    resolve_feedback_policy,
    tool_registry_for_allowed_tools,
)
from repo_harness.tools import ToolExecutor
from repo_harness.trajectory import RunRecorder


def test_patch_focused_react_scaffold_declares_restricted_tool_surface():
    scaffold = build_scaffold("patch_focused_react")

    assert scaffold.scaffold_id == "patch_focused_react"
    assert scaffold.scaffold_version == "repo_harness_patch_focused_react_v1"
    assert scaffold.initial_phase == "patch"
    assert scaffold.allowed_tools == PATCH_FOCUSED_REACT_TOOL_ORDER
    assert "bash" not in scaffold.allowed_tools
    assert "create_file" not in scaffold.allowed_tools
    assert "durable source patch" in scaffold.prompt_fragment
    assert "persistent project files" in scaffold.prompt_fragment
    assert "fallback semantic" in scaffold.prompt_fragment
    assert "environment-derived value" in scaffold.prompt_fragment
    assert "run_tests" in scaffold.prompt_fragment
    assert "git_diff" in scaffold.prompt_fragment


def test_patch_focused_react_prompt_does_not_expose_hidden_evaluator_terms():
    scaffold = build_scaffold("patch_focused_react")
    lowered = scaffold.prompt_fragment.lower()

    forbidden_terms = [
        "hidden selector",
        "fail_to_pass",
        "pass_to_pass",
        "test_patch",
        "gold patch",
        "gold_patch",
        "hidden verifier",
        "hidden result",
        "final verifier hidden result",
        "run outcome",
        "reward/run outcome",
    ]
    assert not any(term in lowered for term in forbidden_terms)


def test_patch_focused_react_feedback_policy_controls_run_tests_only():
    scaffold = build_scaffold("patch_focused_react")
    enabled_policy = resolve_feedback_policy(run_config=RunConfig(), scaffold=scaffold)

    assert enabled_policy.resolved_test_feedback_policy == "structured_public_feedback"
    assert resolve_allowed_tools(scaffold=scaffold, feedback_policy=enabled_policy) == (
        PATCH_FOCUSED_REACT_TOOL_ORDER
    )

    disabled_policy = resolve_feedback_policy(
        run_config=RunConfig.model_validate(
            {"runtime": {"scaffold_id": "patch_focused_react", "test_feedback_policy": "disabled"}}
        ),
        scaffold=scaffold,
    )
    assert resolve_allowed_tools(scaffold=scaffold, feedback_policy=disabled_policy) == [
        "list_files",
        "read_file",
        "grep",
        "edit_file",
        "git_diff",
    ]


def test_patch_focused_react_tool_schema_snapshot_excludes_shell_and_file_create():
    registry = tool_registry_for_allowed_tools(PATCH_FOCUSED_REACT_TOOL_ORDER)
    snapshot = build_tool_schema_snapshot(registry)

    assert snapshot.tool_order == PATCH_FOCUSED_REACT_TOOL_ORDER
    assert [tool.name for tool in snapshot.tools] == PATCH_FOCUSED_REACT_TOOL_ORDER
    assert "bash" not in snapshot.tool_order
    assert "create_file" not in snapshot.tool_order


def test_patch_focused_react_agent_loop_blocks_shell_and_create_file(tmp_path: Path):
    scaffold = build_scaffold("patch_focused_react")
    run_dir = tmp_path / "run"
    client = FakeModelClient.from_steps(
        script_id="patch-focused-restricted-tools",
        task_id="task",
        steps=[
            {
                "step_id": "shell",
                "action": "tool_call",
                "tool_call_id": "call_shell",
                "tool_name": "bash",
                "arguments": {"command": "python -c 'print(1)'"},
            },
            {
                "step_id": "create",
                "action": "tool_call",
                "tool_call_id": "call_create",
                "tool_name": "create_file",
                "arguments": {"path": "scratch.py", "content": "print(1)"},
            },
            {"step_id": "final", "action": "final_answer", "assistant_text": "done"},
        ],
    )

    with RunRecorder("patch-focused-restricted-tools", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            scaffold=scaffold,
            allowed_tool_names=list(PATCH_FOCUSED_REACT_TOOL_ORDER),
        ).run(
            run_id="patch-focused-restricted-tools",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=3,
        )

    events = _read_events(run_dir)
    blocked = [
        event
        for event in events
        if event["event_type"] == "tool_not_allowed"
        and event["data"]["tool_name"] in {"bash", "create_file"}
    ]
    assert state.agent_stop_reason == "final_answer"
    assert {event["data"]["tool_name"] for event in blocked} == {"bash", "create_file"}
    assert not any(
        event["event_type"] == "permission_decision"
        and event["data"]["tool_name"] in {"bash", "create_file"}
        for event in events
    )


def _read_events(run_dir: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
