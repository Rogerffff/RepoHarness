from pathlib import Path
import hashlib
import subprocess

import pytest

import repo_harness.tools.minimal as minimal_tools
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


def test_tool_model_visible_contract_explains_restricted_workflow():
    grep = build_tool("grep")
    bash = build_tool("bash")
    run_tests = build_tool("run_tests")

    assert "Default mode is literal substring" in grep.model_visible_description
    assert "mode='regex'" in grep.model_visible_description
    assert grep.input_schema["properties"]["mode"]["enum"] == ["literal", "regex"]
    assert "max_matches" in grep.input_schema["properties"]
    assert "expected_content_hash" in build_tool("edit_file").input_schema["properties"]
    assert build_tool("edit_file").input_schema["properties"]["replace_all"]["default"] is False

    assert "not a general shell" in bash.model_visible_description
    assert "do not use cd" in bash.model_visible_description
    assert "arbitrary python -c" in bash.model_visible_description
    assert "do not combine commands" in bash.model_visible_prompt
    assert bash.input_schema["properties"]["cwd"]["description"].startswith("Optional workspace-relative")

    assert "takes no arguments" in run_tests.model_visible_description
    assert "does not run arbitrary shell commands" in run_tests.model_visible_prompt
    assert run_tests.input_schema["additionalProperties"] is False


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


def test_read_file_accepts_offset_limit_aliases(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "notes.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
    tool_call = ToolCall(
        tool_call_id="call_read_slice",
        tool_name="read_file",
        arguments={"path": "notes.txt", "offset": 2, "limit": 2},
        turn=1,
    )

    validation = ToolExecutor().validate_input(tool_call, context)
    normalized = ToolExecutor().normalize(tool_call, context)
    result = ToolExecutor().execute(tool_call, context)

    assert validation is None
    assert normalized.normalized_arguments["start_line"] == 2
    assert normalized.normalized_arguments["end_line"] == 3
    assert "2 | two" in result.content_preview
    assert "3 | three" in result.content_preview
    assert "one" not in result.content_preview
    assert result.typed["start_line"] == 2
    assert result.typed["end_line"] == 3
    assert result.typed["content_sha256"] == hashlib.sha256("one\ntwo\nthree\nfour\n".encode()).hexdigest()
    assert result.typed["raw_content_preview"] == "two\nthree\n"


@pytest.mark.parametrize("field", ["start_line", "end_line", "offset", "limit"])
def test_read_file_rejects_non_positive_slice_arguments(tmp_path: Path, field: str):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "notes.txt").write_text("one\ntwo\n", encoding="utf-8")
    tool_call = ToolCall(
        tool_call_id=f"call_bad_{field}",
        tool_name="read_file",
        arguments={"path": "notes.txt", field: 0},
        turn=1,
    )

    result = ToolExecutor().validate_input(tool_call, context)

    assert result is not None
    assert result.status == "error"
    assert result.error_type == "schema_validation_failed"
    assert result.typed["field"] == field
    assert result.typed["expected_type"] == "positive integer"


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


def test_grep_supports_regex_context_and_pagination(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "a.py").write_text("alpha = 1\nbeta = 2\nalpha = 3\n", encoding="utf-8")
    (workspace / "b.txt").write_text("alpha = 4\n", encoding="utf-8")

    first = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_grep_regex",
            tool_name="grep",
            arguments={
                "query": r"alpha\s*=",
                "mode": "regex",
                "glob": "*.py",
                "max_matches": 1,
                "offset": 0,
                "context_lines": 1,
            },
            turn=1,
        ),
        context,
    )
    second = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_grep_regex_next",
            tool_name="grep",
            arguments={
                "query": r"alpha\s*=",
                "mode": "regex",
                "glob": "*.py",
                "max_matches": 1,
                "offset": first.typed["next_offset"],
            },
            turn=1,
        ),
        context,
    )

    assert first.status == "ok"
    assert first.typed["match_count"] == 1
    assert first.typed["total_match_count"] == 2
    assert first.typed["truncated"] is True
    assert "a.py:1:>alpha = 1" in first.content_preview
    assert "a.py:2: beta = 2" in first.content_preview
    assert "b.txt" not in first.content_preview
    assert second.status == "ok"
    assert "a.py:3:>alpha = 3" in second.content_preview


def test_grep_invalid_regex_returns_recoverable_error(tmp_path: Path):
    context = _tool_context(tmp_path)
    Path(context.run_workspace.workspace_path, "notes.txt").write_text("hello\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_bad_regex",
            tool_name="grep",
            arguments={"query": "[", "mode": "regex"},
            turn=1,
        ),
        context,
    )

    assert result.status == "error"
    assert result.error_type == "invalid_regex"
    assert "mode='literal'" in result.content_preview


def test_grep_scan_limit_truncation_has_valid_recovery_hint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    for index in range(3):
        (workspace / f"file_{index}.txt").write_text("no match\n", encoding="utf-8")
    monkeypatch.setattr(minimal_tools, "GREP_MAX_SCANNED_FILES", 1)

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_scan_limit",
            tool_name="grep",
            arguments={"query": "missing"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["truncated"] is True
    assert result.typed["next_offset"] is None
    assert "offset=None" not in result.content_preview
    assert "narrow root, glob, or query" in result.content_preview


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


def test_source_inspection_tools_hide_dependency_environment_paths(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "src").mkdir()
    (workspace / "src" / "app.py").write_text("NEEDLE = 'source'\n", encoding="utf-8")
    hidden_file = workspace / ".pre_verl_venv" / "lib" / "python3.8" / "site-packages" / "pkg.py"
    hidden_file.parent.mkdir(parents=True)
    hidden_file.write_text("NEEDLE = 'dependency'\n", encoding="utf-8")

    list_result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_list",
            tool_name="list_files",
            arguments={"path": "."},
            turn=1,
        ),
        context,
    )
    grep_result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_grep",
            tool_name="grep",
            arguments={"query": "NEEDLE"},
            turn=1,
        ),
        context,
    )
    read_result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_read_hidden",
            tool_name="read_file",
            arguments={"path": ".pre_verl_venv/lib/python3.8/site-packages/pkg.py"},
            turn=1,
        ),
        context,
    )

    assert list_result.status == "ok"
    assert "src/app.py" in list_result.content_preview
    assert ".pre_verl_venv" not in list_result.content_preview
    assert grep_result.status == "ok"
    assert grep_result.typed["match_count"] == 1
    assert "src/app.py" in grep_result.content_preview
    assert ".pre_verl_venv" not in grep_result.content_preview
    assert read_result.status == "error"
    assert read_result.error_type == "model_hidden_path"


def test_list_files_paginates_and_reports_recovery(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    for name in ["a.py", "b.py", "c.py"]:
        (workspace / name).write_text("# file\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_list_page",
            tool_name="list_files",
            arguments={"path": ".", "glob": "*.py", "offset": 1, "max_entries": 1},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["files"] == ["b.py"]
    assert result.typed["total_visible_count"] == 3
    assert result.typed["truncated"] is True
    assert result.typed["next_offset"] == 2
    assert "offset=2" in result.content_preview


def test_source_inspection_tools_skip_symlink_to_outside_workspace(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("NEEDLE outside\n", encoding="utf-8")
    (workspace / "inside.txt").write_text("NEEDLE inside\n", encoding="utf-8")
    (workspace / "outside-link.txt").symlink_to(outside)

    list_result = ToolExecutor().execute(
        ToolCall(tool_call_id="call_list_symlink", tool_name="list_files", arguments={"path": "."}, turn=1),
        context,
    )
    grep_result = ToolExecutor().execute(
        ToolCall(tool_call_id="call_grep_symlink", tool_name="grep", arguments={"query": "NEEDLE"}, turn=1),
        context,
    )

    assert list_result.status == "ok"
    assert "inside.txt" in list_result.content_preview
    assert "outside-link.txt" not in list_result.content_preview
    assert list_result.typed["skipped_symlink_count"] == 1
    assert grep_result.status == "ok"
    assert "inside.txt" in grep_result.content_preview
    assert "outside-link.txt" not in grep_result.content_preview
    assert grep_result.typed["skipped_symlink_count"] == 1


def test_source_inspection_tools_skip_symlink_to_hidden_target(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    hidden = workspace / ".pre_verl_venv" / "pkg.py"
    hidden.parent.mkdir(parents=True)
    hidden.write_text("NEEDLE hidden\n", encoding="utf-8")
    (workspace / "visible-link.py").symlink_to(hidden)

    list_result = ToolExecutor().execute(
        ToolCall(tool_call_id="call_list_hidden_symlink", tool_name="list_files", arguments={"path": "."}, turn=1),
        context,
    )
    grep_result = ToolExecutor().execute(
        ToolCall(tool_call_id="call_grep_hidden_symlink", tool_name="grep", arguments={"query": "NEEDLE"}, turn=1),
        context,
    )
    read_result = ToolExecutor().execute(
        ToolCall(tool_call_id="call_read_hidden_symlink", tool_name="read_file", arguments={"path": "visible-link.py"}, turn=1),
        context,
    )

    assert list_result.status == "ok"
    assert "visible-link.py" not in list_result.content_preview
    assert grep_result.status == "ok"
    assert grep_result.typed["match_count"] == 0
    assert read_result.status == "error"
    assert read_result.error_type == "model_hidden_path"
    assert read_result.typed["visibility_reason"] == "symlink_target_hidden_path"


def test_read_file_long_line_reports_truncation_recovery(tmp_path: Path):
    context = _tool_context(tmp_path)
    context.output_limits = context.output_limits.__class__(max_tool_output_chars=120)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "long.txt").write_text("x" * 500 + "\nnext\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(tool_call_id="call_read_long", tool_name="read_file", arguments={"path": "long.txt"}, turn=1),
        context,
    )

    assert result.status == "ok"
    assert result.typed["truncated"] is True
    assert result.typed["next_start_line"] == 2
    assert "[line truncated]" in result.content_preview


def test_edit_file_rejects_stale_hash_ambiguous_text_and_line_prefix(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "notes.txt").write_text("same\nsame\n", encoding="utf-8")
    executor = ToolExecutor()

    stale = executor.execute(
        ToolCall(
            tool_call_id="call_stale",
            tool_name="edit_file",
            arguments={
                "path": "notes.txt",
                "old_text": "same\n",
                "new_text": "changed\n",
                "expected_content_hash": "0" * 64,
            },
            turn=1,
        ),
        context,
    )
    ambiguous = executor.execute(
        ToolCall(
            tool_call_id="call_ambiguous",
            tool_name="edit_file",
            arguments={"path": "notes.txt", "old_text": "same\n", "new_text": "changed\n"},
            turn=1,
        ),
        context,
    )
    numbered = executor.execute(
        ToolCall(
            tool_call_id="call_numbered",
            tool_name="edit_file",
            arguments={"path": "notes.txt", "old_text": "1 | same\n", "new_text": "changed\n"},
            turn=1,
        ),
        context,
    )

    assert stale.status == "error"
    assert stale.error_type == "stale_file_state"
    assert stale.typed["current_content_hash"] == hashlib.sha256("same\nsame\n".encode()).hexdigest()
    assert ambiguous.status == "error"
    assert ambiguous.error_type == "ambiguous_old_text"
    assert ambiguous.typed["match_count"] == 2
    assert numbered.status == "error"
    assert numbered.error_type == "line_number_prefix_in_old_text"


def test_edit_file_accepts_expected_content_sha256_alias(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    original = "one\n"
    (workspace / "notes.txt").write_text(original, encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_edit_alias",
            tool_name="edit_file",
            arguments={
                "path": "notes.txt",
                "old_text": "one\n",
                "new_text": "two\n",
                "expected_content_sha256": hashlib.sha256(original.encode()).hexdigest(),
            },
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert (workspace / "notes.txt").read_text(encoding="utf-8") == "two\n"
    assert result.typed["content_sha256"] == hashlib.sha256("two\n".encode()).hexdigest()


def test_git_diff_reports_changed_files_and_path_filter(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "a.py").write_text("one\n", encoding="utf-8")
    (workspace / "b.py").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=workspace, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "repo-harness@example.invalid"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "RepoHarness"], cwd=workspace, check=True)
    subprocess.run(["git", "add", "."], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=workspace, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (workspace / "a.py").write_text("one\ntwo\n", encoding="utf-8")
    (workspace / "b.py").write_text("changed\n", encoding="utf-8")

    all_diff = ToolExecutor().execute(
        ToolCall(tool_call_id="call_diff_all", tool_name="git_diff", arguments={}, turn=1),
        context,
    )
    path_diff = ToolExecutor().execute(
        ToolCall(tool_call_id="call_diff_path", tool_name="git_diff", arguments={"path": "a.py"}, turn=1),
        context,
    )

    assert all_diff.status == "ok"
    assert {entry["path"] for entry in all_diff.typed["changed_files"]} == {"a.py", "b.py"}
    assert all_diff.typed["diff_sha256"] == hashlib.sha256(all_diff.typed["diff_preview"].encode()).hexdigest()
    assert path_diff.status == "ok"
    assert "a.py" in path_diff.content_preview
    assert "b.py" not in path_diff.content_preview


def test_git_diff_changed_files_uses_full_command_artifact(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    for index in range(180):
        (workspace / f"file_{index:03d}.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=workspace, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "repo-harness@example.invalid"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "RepoHarness"], cwd=workspace, check=True)
    subprocess.run(["git", "add", "."], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=workspace, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for index in range(180):
        (workspace / f"file_{index:03d}.txt").write_text(f"changed {index}\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(tool_call_id="call_diff_many", tool_name="git_diff", arguments={}, turn=1),
        context,
    )

    assert result.status == "ok"
    assert result.typed["changed_file_count"] == 180
    assert result.typed["changed_files"][-1]["path"] == "file_179.txt"


def test_git_diff_includes_untracked_files_without_index_mutation(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "tracked.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=workspace, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "repo-harness@example.invalid"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "RepoHarness"], cwd=workspace, check=True)
    subprocess.run(["git", "add", "tracked.txt"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=workspace, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (workspace / "new_module.py").write_text("def added():\n    return 1\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(tool_call_id="call_diff_untracked", tool_name="git_diff", arguments={}, turn=1),
        context,
    )
    index_result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=workspace,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.status == "ok"
    assert any(entry["path"] == "new_module.py" and entry["status"] == "untracked" for entry in result.typed["changed_files"])
    assert "+++ b/new_module.py" in result.content_preview
    assert result.typed["untracked_files"] == ["new_module.py"]
    assert index_result.stdout == ""


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
