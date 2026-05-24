from __future__ import annotations

from pathlib import Path

from repo_harness.agent_loop import AgentLoop
from repo_harness.model_client import FakeModelClient
from repo_harness.permissions import PermissionContext
from repo_harness.scaffolds import PATCH_FOCUSED_REACT_DIAGNOSTIC_SHELL_TOOL_ORDER, build_scaffold
from repo_harness.tools import ToolExecutionContext, ToolExecutor, ToolRegistry, build_tool, default_tool_registry
from repo_harness.tools.schemas import ToolCall
from repo_harness.trajectory import RunRecorder
from repo_harness.workspace import DependencyState, LocalWorkspaceAdapter, RunWorkspace
from repo_harness.workspace.diagnostic_session import sync_projection_to_workspace


def test_stage16b_diagnostic_shell_is_explicit_tool_not_default() -> None:
    registry = default_tool_registry()
    tool = build_tool("diagnostic_shell")
    scaffold = build_scaffold("patch_focused_react_diagnostic_shell")

    assert "diagnostic_shell" not in registry.names()
    assert tool.tool_version == "repo_harness_diagnostic_shell_stage16b_v0"
    assert "persistent diagnostic" in tool.model_visible_description
    assert "diagnostic_shell" in scaffold.allowed_tools
    assert "execute_bash" not in scaffold.allowed_tools


def test_stage16b_diagnostic_shell_requires_explicit_enablement(tmp_path: Path) -> None:
    context = _tool_context(tmp_path, diagnostic_enabled=False)
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_disabled",
            tool_name="diagnostic_shell",
            arguments={"command": "echo ok"},
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert result.error_type == "diagnostic_shell_disabled"


def test_stage16b_local_diagnostic_shell_requires_test_override(tmp_path: Path) -> None:
    context = _tool_context(tmp_path, allow_local_test_override=False)
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_local_without_override",
            tool_name="diagnostic_shell",
            arguments={"command": "echo ok"},
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert result.error_type == "diagnostic_shell_local_backend_requires_explicit_test_override"
    assert result.typed["invalid_for_online_rl"] is True


def test_stage16b_local_diagnostic_shell_persists_session_and_syncs_public_source(
    tmp_path: Path,
) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / ".git").mkdir()
    (workspace / ".git" / "HEAD").write_text("hidden-history\n", encoding="utf-8")
    (workspace / "pkg.py").write_text("value = 1\n", encoding="utf-8")

    first = _executor().execute(
        ToolCall(
            tool_call_id="call_modify",
            tool_name="diagnostic_shell",
            arguments={
                "command": (
                    "printf 'value = 2\\n' > pkg.py; "
                    "printf scratch > \"$TMPDIR/repro.txt\"; "
                    "ls -a"
                )
            },
            turn=1,
        ),
        context,
    )
    second = _executor().execute(
        ToolCall(
            tool_call_id="call_persist",
            tool_name="diagnostic_shell",
            arguments={"command": "test -f \"$TMPDIR/repro.txt\"; echo tmp_exists=$?"},
            turn=2,
        ),
        context,
    )

    assert first.status == "ok"
    assert ".git" not in first.content_preview
    assert "hidden-history" not in first.content_preview
    assert second.status == "ok"
    assert "tmp_exists=0" in second.content_preview
    assert (workspace / "pkg.py").read_text(encoding="utf-8") == "value = 2\n"
    assert (workspace / ".git" / "HEAD").read_text(encoding="utf-8") == "hidden-history\n"
    assert not (workspace / "repro.txt").exists()
    assert first.typed["diagnostic_session_facts"]["workspace_projection_sync_status"] == "completed"
    assert first.typed["invalid_for_training"] is True
    assert first.typed["sample_destination"] == "diagnostic_side_channel"


def test_stage16f1_local_diagnostic_shell_uses_explicit_bash_lc_semantics(
    tmp_path: Path,
) -> None:
    context = _tool_context(tmp_path)

    result = _executor().execute(
        ToolCall(
            tool_call_id="call_bash_semantics",
            tool_name="diagnostic_shell",
            arguments={
                "command": (
                    "printf 'export RH_STAGE16F1_SOURCE=from_source\\n' > setup.bash; "
                    "source setup.bash; "
                    "set -o pipefail; false | true; pipe_status=$?; "
                    "if shopt -q login_shell; then login_status=login; else login_status=non_login; fi; "
                    "printf 'source=%s pipe=%s login=%s bash=%s\\n' "
                    "\"$RH_STAGE16F1_SOURCE\" \"$pipe_status\" \"$login_status\" "
                    "\"${BASH_VERSION:+present}\""
                )
            },
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert "source=from_source" in result.content_preview
    assert "pipe=1" in result.content_preview
    assert "login=login" in result.content_preview
    assert "bash=present" in result.content_preview
    facts = result.typed["diagnostic_session_facts"]
    assert facts["diagnostic_session_execution_shell"] == "bash"
    assert facts["diagnostic_session_shell_login_mode"] == "login"
    assert facts["diagnostic_session_shell_interactive_mode"] == "non_interactive"
    assert facts["diagnostic_session_shell_startup_policy"] == "recorded"
    assert facts["diagnostic_session_shell_home_policy"] == "session_home"
    assert facts["diagnostic_session_shell_bash_env_policy"] == "cleared"
    assert facts["diagnostic_session_shell_env_policy"] == "cleared"
    assert len(facts["diagnostic_session_execution_argv_digest"]) == 64


def test_stage16b_projection_refreshes_after_structured_file_edits(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "pkg.py").write_text("value = 1\n", encoding="utf-8")
    executor = _executor()

    first = executor.execute(
        ToolCall(
            tool_call_id="call_first",
            tool_name="diagnostic_shell",
            arguments={"command": "cat pkg.py"},
            turn=1,
        ),
        context,
    )
    (workspace / "pkg.py").write_text("value = 3\n", encoding="utf-8")
    second = executor.execute(
        ToolCall(
            tool_call_id="call_second",
            tool_name="diagnostic_shell",
            arguments={"command": "cat pkg.py"},
            turn=2,
        ),
        context,
    )

    assert first.status == "ok"
    assert "value = 1" in first.content_preview
    assert second.status == "ok"
    assert "value = 3" in second.content_preview
    assert (workspace / "pkg.py").read_text(encoding="utf-8") == "value = 3\n"


def test_stage16b_local_diagnostic_shell_blocks_symlink_escape_on_sync(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    outside = tmp_path / "hidden_runtime"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret\n", encoding="utf-8")

    result = _executor().execute(
        ToolCall(
            tool_call_id="call_symlink_escape",
            tool_name="diagnostic_shell",
            arguments={"command": f"ln -s {outside.as_posix()} leak"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["diagnostic_session_facts"]["symlink_escape_blocked"] is True
    assert not (workspace / "leak").exists()


def test_stage16b_local_diagnostic_shell_blocks_symlink_to_hidden_projection_target(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)

    result = _executor().execute(
        ToolCall(
            tool_call_id="call_hidden_symlink",
            tool_name="diagnostic_shell",
            arguments={"command": "ln -s .git/config leak; ln -s runtime_private/secret hidden_leak"},
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert result.error_type == "diagnostic_shell_hidden_projection_path_denied"
    assert not (workspace / "leak").exists()
    assert not (workspace / "hidden_leak").exists()


def test_stage16b_workspace_relative_diagnostic_tmp_is_not_synced_to_final_workspace(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)

    result = _executor().execute(
        ToolCall(
            tool_call_id="call_workspace_tmp",
            tool_name="diagnostic_shell",
            arguments={"command": "mkdir -p tmp cache scratch; printf repro > tmp/repro.py; printf x > cache/x; printf y > scratch/y"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["diagnostic_session_facts"]["workspace_projection_sync_status"] == "failed"
    assert result.typed["invalid_for_training"] is True
    assert not (workspace / "tmp" / "repro.py").exists()
    assert not (workspace / "cache" / "x").exists()
    assert not (workspace / "scratch" / "y").exists()


def test_stage16b_diagnostic_shell_rejects_hidden_projection_paths(tmp_path: Path) -> None:
    executor = _executor()
    commands = [
        "mkdir .git; echo fake > .git/config",
        "mkdir runtime_private; echo secret > runtime_private/x",
        "cat .env",
        "mkdir .repo_harness_runtime",
        "mkdir .repo_harness_env_overlay",
    ]
    for index, command in enumerate(commands, start=1):
        context = _tool_context(tmp_path / f"hidden_path_{index}")
        result = executor.execute(
            ToolCall(
                tool_call_id=f"call_hidden_path_{index}",
                tool_name="diagnostic_shell",
                arguments={"command": command},
                turn=1,
            ),
            context,
        )

        assert result.status == "denied"
        assert result.error_type == "diagnostic_shell_hidden_projection_path_denied"
        assert result.typed["invalid_for_online_rl"] is True


def test_stage16b_projection_sync_purges_model_created_hidden_paths(tmp_path: Path) -> None:
    projection = tmp_path / "projection"
    workspace = tmp_path / "workspace"
    projection.mkdir()
    workspace.mkdir()
    (projection / "pkg.py").write_text("value = 1\n", encoding="utf-8")
    (projection / ".git").mkdir()
    (projection / ".git" / "config").write_text("fake\n", encoding="utf-8")
    (projection / "runtime_private").mkdir()
    (projection / "runtime_private" / "x").write_text("secret\n", encoding="utf-8")

    facts = sync_projection_to_workspace(projection, workspace)

    assert facts.workspace_projection_sync_status == "failed"
    assert facts.workspace_projection_sync_passed is False
    assert any(item.startswith("hidden_projection_path_purged:.git") for item in facts.diagnostics)
    assert any(item.startswith("hidden_projection_path_purged:runtime_private") for item in facts.diagnostics)
    assert not (projection / ".git").exists()
    assert not (projection / "runtime_private").exists()
    assert not (workspace / ".git").exists()
    assert not (workspace / "runtime_private").exists()
    assert (workspace / "pkg.py").read_text(encoding="utf-8") == "value = 1\n"


def test_stage16b_projection_sync_blocks_symlink_to_hidden_projection_path(tmp_path: Path) -> None:
    projection = tmp_path / "projection"
    workspace = tmp_path / "workspace"
    projection.mkdir()
    workspace.mkdir()
    (projection / "pkg.py").write_text("value = 1\n", encoding="utf-8")
    (projection / "leak").symlink_to(".git/config")

    facts = sync_projection_to_workspace(projection, workspace)

    assert facts.symlink_escape_blocked is True
    assert any(item.startswith("symlink_hidden_target_blocked:leak") for item in facts.diagnostics)
    assert not (workspace / "leak").exists()
    assert (workspace / "pkg.py").read_text(encoding="utf-8") == "value = 1\n"


def test_stage16b_projection_sync_unlinks_existing_target_symlink_escape(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (workspace / "pkg.py").symlink_to(outside)

    result = _executor().execute(
        ToolCall(
            tool_call_id="call_replace_symlink",
            tool_name="diagnostic_shell",
            arguments={"command": "printf 'safe\\n' > pkg.py"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert outside.read_text(encoding="utf-8") == "outside\n"
    assert not (workspace / "pkg.py").is_symlink()
    assert (workspace / "pkg.py").read_text(encoding="utf-8") == "safe\n"


def test_stage16b_projection_sync_unlinks_existing_symlink_directory_escape(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    outside = tmp_path / "outside_dir"
    outside.mkdir()
    (workspace / "pkg").symlink_to(outside, target_is_directory=True)

    result = _executor().execute(
        ToolCall(
            tool_call_id="call_replace_symlink_dir",
            tool_name="diagnostic_shell",
            arguments={"command": "mkdir -p pkg; printf 'safe\\n' > pkg/mod.py"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert not (workspace / "pkg").is_symlink()
    assert (workspace / "pkg" / "mod.py").read_text(encoding="utf-8") == "safe\n"
    assert not (outside / "mod.py").exists()


def test_stage16b_local_diagnostic_shell_blocks_parent_path_run_dir_escape(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / ".git").mkdir()
    (workspace / ".git" / "HEAD").write_text("hidden-history\n", encoding="utf-8")

    result = _executor().execute(
        ToolCall(
            tool_call_id="call_parent_escape",
            tool_name="diagnostic_shell",
            arguments={"command": "cat ../../../workspaces/agent_workspace/.git/HEAD"},
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert "diagnostic_shell_parent_path_denied" in result.content_preview


def test_stage16b_diagnostic_shell_blocks_detached_python_process(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_popen",
            tool_name="diagnostic_shell",
            arguments={
                "command": (
                    "python -c \"import subprocess; subprocess.Popen(['sleep','30'], "
                    "start_new_session=True)\""
                )
            },
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert "diagnostic_shell_background_process_entry_denied" in result.content_preview


def test_stage16b_diagnostic_shell_blocks_os_background_process_helpers(tmp_path: Path) -> None:
    executor = _executor()
    commands = [
        "python -c \"import os; os.system('sleep 5 &')\"",
        "python -c \"import os; os.spawnlp(os.P_NOWAIT, 'sleep', 'sleep', '5')\"",
        "python -c \"import os; os.fork()\"",
    ]
    for index, command in enumerate(commands, start=1):
        context = _tool_context(tmp_path / f"background_helper_{index}")
        result = executor.execute(
            ToolCall(
                tool_call_id=f"call_background_helper_{index}",
                tool_name="diagnostic_shell",
                arguments={"command": command},
                turn=1,
            ),
            context,
        )

        assert result.status == "denied"
        assert result.error_type.startswith("diagnostic_shell_background_process_entry_denied")
        assert result.typed["invalid_for_online_rl"] is True


def test_stage16b_diagnostic_shell_rejects_dependency_mutation_commands(tmp_path: Path) -> None:
    executor = _executor()
    commands = [
        "pip install requests",
        "python -m pip install requests",
        "uv pip install requests",
        "npm install left-pad",
        "conda install numpy",
        "bash -lc 'pip install requests'",
        "python -c \"import os; os.system('npm install left-pad')\"",
    ]
    for index, command in enumerate(commands, start=1):
        context = _tool_context(tmp_path / f"dependency_mutation_{index}")
        result = executor.execute(
            ToolCall(
                tool_call_id=f"call_dependency_mutation_{index}",
                tool_name="diagnostic_shell",
                arguments={"command": command},
                turn=1,
            ),
            context,
        )

        assert result.status == "denied"
        assert result.error_type == "dependency_mutation_unsupported_in_stage16b"
        assert result.typed["invalid_for_online_rl"] is True


def test_stage16b_diagnostic_shell_non_regular_projection_file_fails_structured(
    tmp_path: Path,
) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_fifo",
            tool_name="diagnostic_shell",
            arguments={"command": "mkfifo pipe"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    facts = result.typed["diagnostic_session_facts"]
    assert facts["workspace_projection_sync_status"] == "failed"
    assert facts["workspace_projection_sync_passed"] is False
    assert any(item.startswith("non_regular_file_blocked:pipe") for item in facts["diagnostics"])
    assert result.typed["invalid_for_training"] is True
    assert "[repo_harness_diagnostic_workspace]" not in result.content_preview
    assert str(tmp_path) not in result.content_preview
    assert not (workspace / "pipe").exists()


def test_stage16b_local_diagnostic_shell_timeout_invalidates_training_candidate(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_timeout",
            tool_name="diagnostic_shell",
            arguments={"command": "sleep 2", "timeout_sec": 1},
            turn=1,
        ),
        context,
    )

    assert result.status == "timeout"
    assert result.typed["diagnostic_session_facts"]["session_invalidated"] is True
    assert result.typed["invalid_for_training"] is True
    assert result.typed["invalid_for_online_rl"] is True
    assert result.typed["sample_destination"] == "diagnostic_side_channel"


def test_stage16b_diagnostic_shell_rejects_background_processes(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_background",
            tool_name="diagnostic_shell",
            arguments={"command": "sleep 999 & echo leaked"},
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert "diagnostic_shell_background_execution_denied" in result.content_preview


def test_stage16b_diagnostic_shell_shared_environment_fails_closed(tmp_path: Path) -> None:
    context = _tool_context(tmp_path, block_shared_environment_writes=True)
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_shared",
            tool_name="diagnostic_shell",
            arguments={"command": "echo ok"},
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert result.error_type == "dependency_mutation_unsupported_in_stage16b"
    assert result.typed["invalid_for_online_rl"] is True


def test_stage16b_diagnostic_shell_hidden_evaluator_guard_fails_closed(tmp_path: Path) -> None:
    context = _tool_context(
        tmp_path,
        dependency_metadata={"hidden_evaluator_refs": ["rh://hidden/verifier"]},
    )
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_hidden_guard",
            tool_name="diagnostic_shell",
            arguments={"command": "echo ok"},
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert result.error_type == "diagnostic_shell_hidden_evaluator_denied"
    assert result.typed["invalid_for_online_rl"] is True


def test_stage16b_diagnostic_shell_visibility_policy_evaluator_only_fails_closed(tmp_path: Path) -> None:
    context = _tool_context(
        tmp_path,
        dependency_metadata={"visibility_policy": {"hidden_tests": {"visibility": "evaluator_only"}}},
    )
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_visibility_guard",
            tool_name="diagnostic_shell",
            arguments={"command": "echo ok"},
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert result.error_type == "diagnostic_shell_evaluator_only_artifact_denied"
    assert result.typed["invalid_for_online_rl"] is True


def test_stage16b_diagnostic_shell_visibility_policy_hidden_key_fails_closed(tmp_path: Path) -> None:
    context = _tool_context(
        tmp_path,
        dependency_metadata={"visibility_policy": {"hidden_verifier": {"visibility": "runtime_private"}}},
    )
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_visibility_key_guard",
            tool_name="diagnostic_shell",
            arguments={"command": "echo ok"},
            turn=1,
        ),
        context,
    )

    assert result.status == "denied"
    assert result.error_type == "diagnostic_shell_evaluator_only_artifact_denied"
    assert result.typed["invalid_for_online_rl"] is True


def test_stage16b_diagnostic_shell_visibility_policy_hidden_values_fail_closed(tmp_path: Path) -> None:
    executor = _executor()
    for index, marker in enumerate(("hidden_evaluator", "final_only", "swe_bench_like_final_only"), start=1):
        context = _tool_context(
            tmp_path / f"marker_{index}",
            dependency_metadata={"visibility_policy": {"tests": {"visibility": marker}}},
        )
        result = executor.execute(
            ToolCall(
                tool_call_id=f"call_visibility_value_guard_{index}",
                tool_name="diagnostic_shell",
                arguments={"command": "echo ok"},
                turn=1,
            ),
            context,
        )

        assert result.status == "denied"
        assert result.error_type == "diagnostic_shell_evaluator_only_artifact_denied"
        assert result.typed["invalid_for_online_rl"] is True


def test_stage16b_local_diagnostic_shell_without_isolation_fact_is_diagnostic_only(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    result = _executor().execute(
        ToolCall(
            tool_call_id="call_unisolated_local",
            tool_name="diagnostic_shell",
            arguments={"command": "echo ok"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["diagnostic_session_facts"]["local_backend_filesystem_isolation_verified"] is False
    assert result.typed["invalid_for_training"] is True
    assert result.typed["sample_destination"] == "diagnostic_side_channel"


def test_stage16b_agent_loop_can_use_diagnostic_shell_scaffold(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    scaffold = build_scaffold("patch_focused_react_diagnostic_shell")
    client = FakeModelClient.from_steps(
        script_id="stage16b-agent-loop",
        task_id="task",
        steps=[
            {
                "step_id": "shell",
                "action": "tool_call",
                "tool_call_id": "call_shell",
                "tool_name": "diagnostic_shell",
                "arguments": {"command": "echo diagnostic-ok"},
            },
            {"step_id": "final", "action": "final_answer", "assistant_text": "done"},
        ],
    )
    registry = ToolRegistry(
        [build_tool(name) for name in PATCH_FOCUSED_REACT_DIAGNOSTIC_SHELL_TOOL_ORDER]
    )

    state = AgentLoop(
        model_client=client,
        tool_executor=ToolExecutor(registry=registry),
        scaffold=scaffold,
        allowed_tool_names=list(PATCH_FOCUSED_REACT_DIAGNOSTIC_SHELL_TOOL_ORDER),
    ).run(
        run_id="stage16b-agent-loop",
        task_id="task",
        initial_messages=[{"role": "system", "content": "system"}],
        tool_context=context,
        recorder=context.recorder,
        max_turns=3,
    )

    assert state.agent_stop_reason == "final_answer"
    tool_results = [message for message in state.messages if message.get("role") == "tool"]
    assert any("diagnostic-ok" in str(message.get("content")) for message in tool_results)


def _executor() -> ToolExecutor:
    return ToolExecutor(registry=ToolRegistry([build_tool("diagnostic_shell")]))


def _tool_context(
    tmp_path: Path,
    *,
    diagnostic_enabled: bool = True,
    block_shared_environment_writes: bool = False,
    local_isolation_verified: bool = True,
    allow_local_test_override: bool = True,
    dependency_metadata: dict[str, object] | None = None,
) -> ToolExecutionContext:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    recorder = RunRecorder("stage16b-tool-test", run_dir, task_id="task")
    adapter = LocalWorkspaceAdapter(
        run_id="stage16b-tool-test",
        run_dir=run_dir,
        block_shared_environment_writes=block_shared_environment_writes,
        diagnostic_shell_local_isolation_verified=local_isolation_verified,
    )
    metadata = {
        "diagnostic_shell_enabled": diagnostic_enabled,
        "diagnostic_session_backend": "local_filesystem_persistent",
        "allow_unisolated_local_diagnostic_shell_for_tests": allow_local_test_override,
        **dict(dependency_metadata or {}),
    }
    return ToolExecutionContext(
        run_id="stage16b-tool-test",
        task_id="task",
        workspace_facade=adapter,
        run_workspace=RunWorkspace(
            run_id="stage16b-tool-test",
            workspace_path=workspace.as_posix(),
            artifact_dir=(run_dir / "artifacts").as_posix(),
            dependency_state=DependencyState(metadata=metadata),
        ),
        artifact_writer=recorder,
        permission_context=PermissionContext(mode="auto"),
        verifier_feedback_facade=None,  # type: ignore[arg-type]
        resolved_verifier_plan=None,  # type: ignore[arg-type]
    )
