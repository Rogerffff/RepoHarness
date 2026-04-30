from pathlib import Path
import subprocess

import pytest

from repo_harness.budget import BudgetManager
from repo_harness.permissions import PermissionContext
from repo_harness.tools import (
    DEFAULT_TOOL_ORDER,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutor,
    ToolRegistry,
    build_tool,
    default_tool_registry,
)
from repo_harness.tools.schemas import ToolCall
from repo_harness.trajectory import RunRecorder
from repo_harness.workspace import DependencyState, LocalWorkspaceAdapter, RunWorkspace


def test_tool_registry_order_is_stable():
    registry = default_tool_registry()

    assert registry.names() == DEFAULT_TOOL_ORDER
    assert [build_tool(name).name for name in DEFAULT_TOOL_ORDER] == DEFAULT_TOOL_ORDER


def test_tool_definition_requires_model_visible_contract():
    with pytest.raises(ValueError, match="model_visible_description"):
        ToolDefinition(
            name="bad",
            tool_version="bad_v0",
            model_visible_description="",
            model_visible_prompt="Use bad.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            max_result_size=1,
        )


def test_registry_rejects_duplicate_tool_names():
    registry = ToolRegistry([build_tool("read_file")])

    with pytest.raises(ValueError, match="duplicate tool"):
        registry.register(build_tool("read_file"))


def test_schema_validation_error_returns_model_visible_tool_result(tmp_path: Path):
    context = _tool_context(tmp_path)
    result = ToolExecutor().validate_input(
        ToolCall(
            tool_call_id="call_bad_read",
            tool_name="read_file",
            arguments={},
            turn=1,
        ),
        context,
    )

    assert result is not None
    assert result.status == "error"
    assert result.error_type == "schema_validation_failed"
    assert result.typed["field"] == "path"
    assert result.artifact_refs


def test_grep_no_match_is_successful_observation(tmp_path: Path):
    context = _tool_context(tmp_path)
    Path(context.run_workspace.workspace_path, "notes.txt").write_text("hello\n", encoding="utf-8")
    tool_call = ToolCall(
        tool_call_id="call_grep",
        tool_name="grep",
        arguments={"query": "missing"},
        turn=1,
    )

    assert ToolExecutor().check_permission(tool_call, context).decision == "allow"
    result = ToolExecutor().execute(tool_call, context)

    assert result.status == "ok"
    assert "No matches" in result.content_preview
    assert result.typed["match_count"] == 0


def test_grep_respects_workspace_sensitive_policy(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / ".env").write_text("SECRET_TOKEN=abc\n", encoding="utf-8")
    (workspace / "notes.txt").write_text("public\n", encoding="utf-8")
    tool_call = ToolCall(
        tool_call_id="call_grep_secret",
        tool_name="grep",
        arguments={"query": "SECRET_TOKEN"},
        turn=1,
    )

    result = ToolExecutor().execute(tool_call, context)

    assert result.status == "ok"
    assert result.typed["match_count"] == 0
    assert "SECRET_TOKEN" not in result.content_preview


def test_bash_large_stdout_uses_preview_and_artifact(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "big.txt").write_text("x" * 20000, encoding="utf-8")
    subprocess.run(["git", "init"], cwd=workspace, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(
        ["git", "config", "user.email", "repo-harness@example.invalid"],
        cwd=workspace,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "RepoHarness"], cwd=workspace, check=True)
    subprocess.run(["git", "add", "big.txt"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-m", "add big file"], cwd=workspace, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tool_call = ToolCall(
        tool_call_id="call_big",
        tool_name="bash",
        arguments={"command": "git show HEAD:big.txt"},
        turn=1,
    )

    assert ToolExecutor().check_permission(tool_call, context).decision == "allow"
    result = ToolExecutor().execute(tool_call, context)

    assert result.status == "ok"
    assert result.artifact_refs
    assert len(result.content_preview) < 13000
    assert "[truncated]" in result.content_preview


def test_bash_timeout_is_clamped_to_command_budget(tmp_path: Path):
    context = _tool_context(tmp_path)
    context.budget_manager = BudgetManager(
        max_turns=1,
        max_tool_calls=10,
        max_test_runs=10,
        task_timeout_sec=60,
        command_timeout_sec=2,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=120000,
        max_output_tokens=4096,
    )
    tool_call = ToolCall(
        tool_call_id="call_timeout",
        tool_name="bash",
        arguments={"command": "pwd", "timeout_sec": 999},
        turn=1,
    )

    normalized = ToolExecutor().normalize(tool_call, context)

    assert normalized.requested_arguments["timeout_sec"] == 999
    assert normalized.normalized_arguments["timeout_sec"] == 2
    assert normalized.normalized_arguments["requested_timeout_sec"] == 999
    assert normalized.normalized_arguments["timeout_clamped_to_sec"] == 2


def _tool_context(tmp_path: Path) -> ToolExecutionContext:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    recorder = RunRecorder("tool-test", run_dir, task_id="task")
    adapter = LocalWorkspaceAdapter(run_id="tool-test", run_dir=run_dir)
    return ToolExecutionContext(
        run_id="tool-test",
        task_id="task",
        workspace_facade=adapter,
        run_workspace=RunWorkspace(
            run_id="tool-test",
            workspace_path=workspace.as_posix(),
            artifact_dir=(run_dir / "artifacts").as_posix(),
            dependency_state=DependencyState(),
        ),
        artifact_writer=recorder,
        permission_context=PermissionContext(mode="auto"),
        verifier_feedback_facade=None,  # type: ignore[arg-type]
        resolved_verifier_plan=None,  # type: ignore[arg-type]
    )
