from __future__ import annotations

from pathlib import Path
import sys

from repo_harness.agent_loop import AgentLoop
from repo_harness.model_client import FakeModelClient
from repo_harness.permissions import PermissionContext
from repo_harness.scaffolds import PATCH_FOCUSED_REACT_EXECUTE_BASH_TOOL_ORDER, build_scaffold
from repo_harness.tools import ToolExecutionContext, ToolExecutor, ToolRegistry, build_tool
from repo_harness.tools.schemas import ToolCall
from repo_harness.trajectory import RunRecorder
from repo_harness.workspace.docker_adapter import SEMANTICS_TO_PHASE
from repo_harness.workspace import DependencyState, LocalWorkspaceAdapter, RunWorkspace


def test_stage16a_execute_bash_runs_shell_command_and_records_visibility_split(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    executor = _executor()
    result = executor.execute(
        ToolCall(
            tool_call_id="call_execute_bash",
            tool_name="execute_bash",
            arguments={
                "command": "python -c \"import sys; print('hello'); print(' err', file=sys.stderr)\"",
                "timeout_sec": 5,
            },
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert "hello" in result.content_preview
    assert "err" in result.content_preview
    assert result.typed["shell_execution"] is True
    assert result.typed["model_visible_observation"] == "redacted_truncated"
    assert result.typed["raw_command_artifact_visibility"] == "runtime_private_or_restricted_audit"
    assert result.typed["raw_command_artifact_returned_to_model"] is False
    assert result.artifact_refs == []


def test_stage16a_execute_bash_cwd_must_be_workspace_relative(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "pkg").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "escaped").symlink_to(outside, target_is_directory=True)
    executor = _executor()

    absolute = executor.execute(
        ToolCall(
            tool_call_id="call_absolute_cwd",
            tool_name="execute_bash",
            arguments={"command": "pwd", "cwd": str(workspace / "pkg")},
            turn=1,
        ),
        context,
    )
    parent = executor.execute(
        ToolCall(
            tool_call_id="call_parent_cwd",
            tool_name="execute_bash",
            arguments={"command": "pwd", "cwd": "../agent_workspace"},
            turn=1,
        ),
        context,
    )
    symlink_escape = executor.execute(
        ToolCall(
            tool_call_id="call_symlink_cwd",
            tool_name="execute_bash",
            arguments={"command": "pwd", "cwd": "escaped"},
            turn=1,
        ),
        context,
    )

    assert absolute.status == "denied"
    assert parent.status == "denied"
    assert symlink_escape.status == "denied"


def test_stage16a_execute_bash_denies_default_local_process_backend(tmp_path: Path) -> None:
    context = _tool_context(tmp_path, dependency_metadata={"allow_unisolated_local_execute_bash_for_tests": False})
    call = ToolCall(
        tool_call_id="call_local_denied",
        tool_name="execute_bash",
        arguments={"command": "python -c \"print('ok')\""},
        turn=1,
    )
    executor = _executor()
    decision = executor.check_permission(call, context)
    result = executor.execute(
        call,
        context,
    )

    assert decision.decision == "deny"
    assert decision.reason_code == "execute_bash_requires_workspace_only_execution_backend"
    assert result.status == "denied"
    assert result.error_type == "execute_bash_requires_workspace_only_execution_backend"


def test_stage16a_execute_bash_policy_blocks_hidden_markers_and_git_history(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    executor = _executor()

    hidden = executor.execute(
        ToolCall(
            tool_call_id="call_hidden_marker",
            tool_name="execute_bash",
            arguments={"command": "cat /repo-harness-run/task.yaml"},
            turn=1,
        ),
        context,
    )
    git_history = executor.execute(
        ToolCall(
            tool_call_id="call_git_history",
            tool_name="execute_bash",
            arguments={"command": "python -c \"import subprocess; subprocess.run(['git', 'log'])\""},
            turn=1,
        ),
        context,
    )

    assert hidden.status == "denied"
    assert hidden.error_type == "execute_bash_evaluator_only_marker"
    assert git_history.status == "denied"
    assert git_history.error_type == "execute_bash_git_history_or_metadata"


def test_stage16a_execute_bash_blocks_absolute_and_parent_paths(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    executor = _executor()

    absolute = executor.execute(
        ToolCall(
            tool_call_id="call_absolute_read",
            tool_name="execute_bash",
            arguments={"command": "cat /etc/passwd"},
            turn=1,
        ),
        context,
    )
    parent = executor.execute(
        ToolCall(
            tool_call_id="call_parent_read",
            tool_name="execute_bash",
            arguments={"command": "cat ../artifacts/public.txt"},
            turn=1,
        ),
        context,
    )

    assert absolute.status == "denied"
    assert absolute.error_type == "execute_bash_workspace_boundary"
    assert parent.status == "denied"
    assert parent.error_type == "execute_bash_workspace_boundary"


def test_stage16a_execute_bash_redacts_paths_from_model_visible_output(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_pwd_redact",
            tool_name="execute_bash",
            arguments={
                "command": (
                    "python -c \"import os, sys; print(os.getcwd()); print(sys.executable)\""
                )
            },
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert str(workspace) not in result.content_preview
    assert str(sys.executable) not in result.content_preview
    assert "[repo_harness_workspace_path]" in result.content_preview
    assert (
        "[repo_harness_python_executable]" in result.content_preview
        or "[repo_harness_python_environment_path]" in result.content_preview
    )
    assert result.artifact_refs == []


def test_stage16a_execute_bash_shared_environment_protection_fails_closed(tmp_path: Path) -> None:
    context = _tool_context(tmp_path, block_shared_environment_writes=True)
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_shared_env",
            tool_name="execute_bash",
            arguments={"command": "python -c \"print('ok')\""},
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert result.error_type == "execute_bash_shared_dependency_roots_missing"


def test_stage16a_execute_bash_blocks_inline_python_environment_probe_in_shared_mode(tmp_path: Path) -> None:
    context = _tool_context(
        tmp_path,
        block_shared_environment_writes=True,
        dependency_metadata={"shared_dependency_environment_roots": ["/envs/repoA_py311"]},
    )
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_env_probe",
            tool_name="execute_bash",
            arguments={"command": "python -c \"import os; print(os.environ)\""},
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert result.error_type == "execute_bash_inline_python_visibility"


def test_stage16a_execute_bash_schema_and_permission_metadata(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    call = ToolCall(
        tool_call_id="call_permission",
        tool_name="execute_bash",
        arguments={"command": "python -c \"print('ok')\""},
        turn=1,
    )
    executor = _executor()
    definition = build_tool("execute_bash")
    decision = executor.check_permission(call, context)

    assert definition.input_schema["required"] == ["command"]
    assert "cwd" in definition.input_schema["properties"]
    assert decision.decision == "allow"
    assert decision.shell_execution is True
    assert decision.command_category == "diagnostic"
    assert SEMANTICS_TO_PHASE["execute_bash"] == "agent_tool"


def test_stage16a_agent_loop_executes_patch_focused_execute_bash_scaffold(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    scaffold = build_scaffold("patch_focused_react_execute_bash")
    client = FakeModelClient.from_steps(
        script_id="stage16a-agent-loop",
        task_id="task",
        steps=[
            {
                "step_id": "shell",
                "action": "tool_call",
                "tool_call_id": "call_shell",
                "tool_name": "execute_bash",
                "arguments": {"command": "python -c \"print('shell-ok')\""},
            },
            {"step_id": "final", "action": "final_answer", "assistant_text": "done"},
        ],
    )
    registry = ToolRegistry([build_tool(name) for name in PATCH_FOCUSED_REACT_EXECUTE_BASH_TOOL_ORDER])

    state = AgentLoop(
        model_client=client,
        tool_executor=ToolExecutor(registry=registry),
        scaffold=scaffold,
        allowed_tool_names=list(PATCH_FOCUSED_REACT_EXECUTE_BASH_TOOL_ORDER),
    ).run(
        run_id="stage16a-agent-loop",
        task_id="task",
        initial_messages=[{"role": "system", "content": "system"}],
        tool_context=context,
        recorder=context.recorder,
        max_turns=3,
    )

    assert state.agent_stop_reason == "final_answer"
    tool_results = [message for message in state.messages if message.get("role") == "tool"]
    assert any("shell-ok" in str(message.get("content")) for message in tool_results)


def _executor() -> ToolExecutor:
    return ToolExecutor(registry=ToolRegistry([build_tool("execute_bash")]))


def _tool_context(
    tmp_path: Path,
    *,
    block_shared_environment_writes: bool = False,
    dependency_metadata: dict[str, object] | None = None,
) -> ToolExecutionContext:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    recorder = RunRecorder("stage16a-tool-test", run_dir, task_id="task")
    adapter = LocalWorkspaceAdapter(
        run_id="stage16a-tool-test",
        run_dir=run_dir,
        block_shared_environment_writes=block_shared_environment_writes,
        command_env_provider=(
            None
            if not block_shared_environment_writes
            else lambda path: {
                "PATH": f"{sys.executable.rsplit('/', 1)[0]}:/usr/bin:/bin",
                "PYTHONNOUSERSITE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        ),
    )
    metadata = {"allow_unisolated_local_execute_bash_for_tests": True, **dict(dependency_metadata or {})}
    return ToolExecutionContext(
        run_id="stage16a-tool-test",
        task_id="task",
        workspace_facade=adapter,
        run_workspace=RunWorkspace(
            run_id="stage16a-tool-test",
            workspace_path=workspace.as_posix(),
            artifact_dir=(run_dir / "artifacts").as_posix(),
            dependency_state=DependencyState(metadata=metadata),
        ),
        artifact_writer=recorder,
        permission_context=PermissionContext(mode="auto"),
        verifier_feedback_facade=None,  # type: ignore[arg-type]
        resolved_verifier_plan=None,  # type: ignore[arg-type]
    )
