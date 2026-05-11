from pathlib import Path
import hashlib
import subprocess

import pytest

import repo_harness.tools.minimal as minimal_tools
from repo_harness.budget import BudgetManager
from repo_harness.context.tool_result_artifacts import (
    ToolResultArtifactIndex,
    persist_tool_result_content,
)
from repo_harness.permissions import PermissionContext
from repo_harness.tools import (
    DEFAULT_TOOL_ORDER,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutor,
    ToolRegistry,
    ToolPolicy,
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
    glob_files = build_tool("glob_files")
    recovery = build_tool("read_tool_result_artifact")
    grep = build_tool("grep")
    symbol_search = build_tool("symbol_search")
    working_state = build_tool("update_working_state")
    bash = build_tool("bash")
    run_tests = build_tool("run_tests")

    assert "file-discovery alias" in glob_files.model_visible_description
    assert glob_files.input_schema["required"] == ["pattern"]
    assert "does not modify repository files" in working_state.model_visible_description
    assert "not a full language server" in symbol_search.model_visible_description
    assert "Default mode is literal substring" in grep.model_visible_description
    assert "mode='regex'" in grep.model_visible_description
    assert grep.input_schema["properties"]["mode"]["enum"] == ["literal", "regex"]
    assert "max_matches" in grep.input_schema["properties"]
    assert "pattern" in grep.input_schema["properties"]
    assert grep.input_schema["properties"]["output_mode"]["enum"] == ["content", "files_with_matches", "count"]
    assert "expected_content_hash" in build_tool("edit_file").input_schema["properties"]
    assert build_tool("edit_file").input_schema["properties"]["replace_all"]["default"] is False
    assert "prior read_file" in build_tool("edit_file").model_visible_prompt
    assert "Before the final answer" in build_tool("git_diff").model_visible_prompt
    assert recovery.is_read_only is True
    assert recovery.requires_permission is False
    assert "opaque capability id" in recovery.model_visible_description
    assert recovery.input_schema["required"] == ["artifact_id"]

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


def test_read_tool_result_artifact_recovers_unlocked_page(tmp_path: Path):
    context = _tool_context(tmp_path)
    record = persist_tool_result_content(
        recorder=context.recorder,
        tool_result_id="call_big_result",
        tool_call_id="call_big",
        tool_name="grep",
        content="abcdef" * 2000,
        publishable_after_visibility_scan=True,
        contamination_scan_status="clean",
    )
    index = ToolResultArtifactIndex(run_dir=context.recorder.run_dir)
    index.add(record)
    index.unlock_after_provider_commit(record.artifact_id)
    context.tool_result_artifact_index = index

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_recover",
            tool_name="read_tool_result_artifact",
            arguments={"artifact_id": record.artifact_id, "offset": 0, "limit": 10},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.content_preview.startswith("abcdefabcd")
    assert result.typed["next_offset"] == 10
    assert result.typed["content_sha256"] == record.content_sha256
    assert "artifact_id_looks_like_path" not in result.typed
    assert "suggested_tool" not in result.typed
    assert "suggested_recovery_call" not in result.typed


def test_read_tool_result_artifact_rejects_paths_and_locked_artifacts(tmp_path: Path):
    context = _tool_context(tmp_path)
    record = persist_tool_result_content(
        recorder=context.recorder,
        tool_result_id="call_big_result",
        tool_call_id="call_big",
        tool_name="grep",
        content="locked",
        publishable_after_visibility_scan=True,
        contamination_scan_status="clean",
    )
    index = ToolResultArtifactIndex(run_dir=context.recorder.run_dir)
    index.add(record)
    context.tool_result_artifact_index = index

    path_result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_recover_path",
            tool_name="read_tool_result_artifact",
            arguments={"artifact_id": "../artifacts/secret.txt"},
            turn=1,
        ),
        context,
    )
    locked_result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_recover_locked",
            tool_name="read_tool_result_artifact",
            arguments={"artifact_id": record.artifact_id},
            turn=1,
        ),
        context,
    )

    assert path_result.status == "error"
    assert path_result.error_type == "tool_result_artifact_unavailable"
    assert path_result.typed["artifact_id_looks_like_path"] is True
    assert path_result.typed["suggested_tool"] == "read_file"
    assert path_result.typed["suggested_recovery_call"] == "read_file(path='../artifacts/secret.txt')"
    assert path_result.typed["result_envelope"]["recommended_next_calls"][0] == {
        "tool": "read_file",
        "arguments": {"path": "../artifacts/secret.txt"},
    }
    assert locked_result.status == "error"
    assert "not unlocked" in locked_result.content_preview
    assert locked_result.typed["artifact_id_looks_like_path"] is False
    assert locked_result.typed["suggested_tool"] is None


def test_read_tool_result_artifact_rejects_plain_manifest_artifact_with_persisted_preview_hint(tmp_path: Path):
    context = _tool_context(tmp_path)
    ref = context.recorder.write_artifact(
        "plain_artifact",
        "not recoverable through read_tool_result_artifact",
        {"budget_policy": "preserve_json"},
    )
    context.tool_result_artifact_index = ToolResultArtifactIndex(run_dir=context.recorder.run_dir)

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_recover_manifest_id",
            tool_name="read_tool_result_artifact",
            arguments={"artifact_id": ref.artifact_id},
            turn=1,
        ),
        context,
    )

    assert result.status == "error"
    assert result.error_type == "tool_result_artifact_unavailable"
    assert result.typed["artifact_id_looks_like_path"] is False
    assert result.typed["suggested_tool"] is None
    assert "Only opaque artifact_id values copied from provider-committed persisted tool result previews" in result.content_preview


def test_read_tool_result_artifact_respects_tool_output_budget(tmp_path: Path):
    context = _tool_context(tmp_path)
    context.output_limits = minimal_tools.ToolOutputLimits(max_tool_output_chars=5)
    record = persist_tool_result_content(
        recorder=context.recorder,
        tool_result_id="call_big_result",
        tool_call_id="call_big",
        tool_name="grep",
        content="abcdefghijklmnopqrstuvwxyz",
        publishable_after_visibility_scan=True,
        contamination_scan_status="clean",
    )
    index = ToolResultArtifactIndex(run_dir=context.recorder.run_dir)
    index.add(record)
    index.unlock_after_provider_commit(record.artifact_id)
    context.tool_result_artifact_index = index

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_recover_budget",
            tool_name="read_tool_result_artifact",
            arguments={"artifact_id": record.artifact_id, "offset": 0, "limit": 20},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.truncated is True
    assert result.typed["next_offset"] == 5
    assert result.typed["output_budget_truncated"] is True
    assert result.typed["result_envelope"]["semantic_complete"] is False
    assert "offset=5" in result.content_preview


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
    assert "No matches found after scanning all 1 model-visible files" in result.content_preview
    assert result.typed["result_kind"] == "complete_no_match"
    assert result.typed["scan_complete"] is True
    assert result.typed["scan_limit_reached"] is False
    assert result.typed["result_limit_reached"] is False
    assert result.typed["output_truncated"] is False
    assert result.typed["match_count"] == 0
    _assert_search_fact_protocol(result.typed)
    _assert_result_envelope(result.typed, result_kind="complete_no_match", semantic_complete=True)


def test_grep_accepts_pattern_alias_for_query(tmp_path: Path):
    context = _tool_context(tmp_path)
    Path(context.run_workspace.workspace_path, "notes.txt").write_text("hello alias\n", encoding="utf-8")
    tool_call = ToolCall(
        tool_call_id="call_grep_pattern",
        tool_name="grep",
        arguments={"pattern": "hello"},
        turn=1,
    )

    validation = ToolExecutor().validate_input(tool_call, context)
    normalized = ToolExecutor().normalize(tool_call, context)
    result = ToolExecutor().execute(tool_call, context)

    assert validation is None
    assert normalized.normalized_arguments["query"] == "hello"
    assert result.status == "ok"
    assert result.typed["query"] == "hello"
    assert "notes.txt:1:>hello alias" in result.content_preview


def test_grep_reads_workspace_files_through_workspace_adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    context = _tool_context(tmp_path)
    Path(context.run_workspace.workspace_path, "notes.txt").write_text("fast grep path\n", encoding="utf-8")
    reads: list[str] = []
    original_read_text = context.workspace_adapter.read_text

    def tracking_read_text(workspace_path: str, requested_path: str) -> str:
        reads.append(requested_path)
        return original_read_text(workspace_path, requested_path)

    monkeypatch.setattr(context.workspace_adapter, "read_text", tracking_read_text)

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_grep_direct_read",
            tool_name="grep",
            arguments={"query": "fast"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert "notes.txt:1:>fast grep path" in result.content_preview
    assert reads == ["notes.txt"]
    assert result.typed["search_backend"] == "workspace_adapter_python_fallback"
    assert result.typed["workspace_execution_mode"] == "local_process"
    assert result.typed["read_error_count"] == 0
    _assert_search_fact_protocol(result.typed)


def test_grep_read_error_makes_no_match_incomplete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    context = _tool_context(tmp_path)
    Path(context.run_workspace.workspace_path, "notes.txt").write_text("fast grep path\n", encoding="utf-8")

    def failing_read_text(_workspace_path: str, _requested_path: str) -> str:
        from repo_harness.errors import WorkspaceError

        raise WorkspaceError("backend read failed")

    monkeypatch.setattr(context.workspace_adapter, "read_text", failing_read_text)

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_grep_read_error",
            tool_name="grep",
            arguments={"query": "fast"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["result_kind"] == "partial_scan_no_match"
    assert result.typed["scan_complete"] is False
    assert result.typed["scan_complete_reason"] == "read_errors_present"
    assert result.typed["read_error_count"] == 1
    assert result.typed["read_error_samples"][0]["path"] == "notes.txt"
    _assert_search_fact_protocol(result.typed)
    assert "Do not conclude the query is absent" in result.content_preview


def test_grep_backend_mismatch_blocks_trusted_no_match(tmp_path: Path):
    context = _tool_context(tmp_path)
    context.run_workspace = context.run_workspace.model_copy(update={"execution_mode": "docker"})
    Path(context.run_workspace.workspace_path, "notes.txt").write_text("hello\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_grep_backend_mismatch",
            tool_name="grep",
            arguments={"query": "missing"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["result_kind"] == "partial_scan_no_match"
    assert result.typed["scan_complete"] is False
    assert result.typed["scan_complete_reason"] == "backend_mismatch_detected"
    assert result.typed["backend_mismatch_detected"] is True
    _assert_search_fact_protocol(result.typed)


def test_grep_visibility_error_blocks_trusted_no_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    context = _tool_context(tmp_path)
    Path(context.run_workspace.workspace_path, "notes.txt").write_text("hello\n", encoding="utf-8")

    def broken_visibility(_context: ToolExecutionContext, rel_path: str) -> tuple[bool, str | None]:
        return False, "visibility_error" if rel_path == "notes.txt" else None

    monkeypatch.setattr(minimal_tools, "_model_visible_path_status", broken_visibility)

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_grep_visibility_error",
            tool_name="grep",
            arguments={"query": "missing"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["result_kind"] == "partial_scan_no_match"
    assert result.typed["scan_complete"] is False
    assert result.typed["scan_complete_reason"] == "visibility_errors_present"
    assert result.typed["visibility_error_count"] == 1
    assert result.typed["visibility_error_samples"][0] == {
        "path": "notes.txt",
        "reason": "visibility_error",
    }
    _assert_search_fact_protocol(result.typed)


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
    assert first.typed["result_kind"] == "result_page_truncated"
    assert first.typed["result_limit_reached"] is True
    assert first.typed["scan_complete"] is True
    assert first.typed["truncated"] is True
    assert first.typed["recommended_next_calls"][0]["arguments"]["offset"] == first.typed["next_offset"]
    assert "a.py:1:>alpha = 1" in first.content_preview
    assert "a.py:2: beta = 2" in first.content_preview
    assert "b.txt" not in first.content_preview
    assert second.status == "ok"
    assert "a.py:3:>alpha = 3" in second.content_preview


def test_grep_files_with_matches_output_mode_omits_match_content(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "a.py").write_text("secret-ish public needle\n", encoding="utf-8")
    (workspace / "b.py").write_text("needle again\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_grep_files_only",
            tool_name="grep",
            arguments={"query": "needle", "output_mode": "files_with_matches"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["output_mode"] == "files_with_matches"
    assert result.typed["files_with_matches"] == ["a.py", "b.py"]
    assert "a.py" in result.content_preview
    assert "b.py" in result.content_preview
    assert "secret-ish public needle" not in result.content_preview


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
    assert result.typed["result_kind"] == "partial_scan_no_match"
    assert result.typed["scan_complete"] is False
    assert result.typed["scan_limit_reached"] is True
    assert result.typed["result_limit_reached"] is False
    assert result.typed["candidate_file_count"] == 3
    assert result.typed["scanned_candidate_file_count"] == 1
    assert result.typed["unscanned_file_count"] == 2
    assert result.typed["truncated"] is True
    assert result.typed["next_offset"] is None
    assert "offset=None" not in result.content_preview
    assert "No matches found in the trusted scanned subset" in result.content_preview
    assert "Do not conclude the query is absent" in result.content_preview
    assert "Narrow root, glob, or query" in result.content_preview
    assert result.typed["recommended_next_calls"][0]["tool"] == "grep"
    envelope = _assert_result_envelope(result.typed, result_kind="partial_scan_no_match", semantic_complete=False)
    assert envelope["result_limit_reached"] is False
    assert envelope["recommended_next_calls"][0]["tool"] == "grep"


def test_grep_out_of_range_page_is_not_reported_as_absent_query(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "a.py").write_text("needle = 1\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_grep_out_of_range_page",
            tool_name="grep",
            arguments={"query": "needle", "offset": 10, "max_matches": 5},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["result_kind"] == "page_empty_out_of_range"
    assert result.typed["match_count"] == 0
    assert result.typed["total_match_count"] == 1
    assert result.typed["scan_complete"] is True
    assert "No matches on this result page" in result.content_preview
    assert "This does not mean the query is absent" in result.content_preview


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
    assert result.typed["result_kind"] == "result_page_truncated"
    assert result.typed["scan_complete"] is True
    assert result.typed["scan_complete_reason"] == "result_page_truncated"
    assert result.typed["search_fact_policy_version"] == minimal_tools.SEARCH_FACT_POLICY_VERSION
    assert result.typed["visibility_error_count"] == 0
    assert result.typed["read_error_count"] == 0
    _assert_search_fact_protocol(result.typed)
    envelope = _assert_result_envelope(result.typed, result_kind="result_page_truncated", semantic_complete=False)
    assert envelope["result_limit_reached"] is True
    assert "offset=2" in str(envelope["recovery_call"])
    assert "offset=2" in result.content_preview


def test_list_files_backend_mismatch_blocks_complete_listing(tmp_path: Path):
    context = _tool_context(tmp_path)
    context.run_workspace = context.run_workspace.model_copy(update={"execution_mode": "docker"})
    Path(context.run_workspace.workspace_path, "notes.txt").write_text("hello\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_list_backend_mismatch",
            tool_name="list_files",
            arguments={"path": "."},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["result_kind"] == "incomplete_file_listing"
    assert result.typed["scan_complete"] is False
    assert result.typed["scan_complete_reason"] == "backend_mismatch_detected"
    assert result.typed["backend_mismatch_detected"] is True
    _assert_search_fact_protocol(result.typed)


def test_glob_files_uses_list_files_protocol_and_recovery(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "src").mkdir()
    for name in ["a.py", "b.py", "notes.txt"]:
        (workspace / "src" / name).write_text("# file\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_glob_files",
            tool_name="glob_files",
            arguments={"path": "src", "pattern": "*.py", "offset": 0, "max_entries": 1},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.tool_name == "glob_files"
    assert result.normalized_arguments["root"] == "src"
    assert result.normalized_arguments["glob"] == "*.py"
    assert result.typed["files"] == ["src/a.py"]
    assert result.typed["result_kind"] == "result_page_truncated"
    assert result.typed["recommended_next_calls"][0]["tool"] == "glob_files"
    assert result.typed["recommended_next_calls"][0]["arguments"]["pattern"] == "*.py"
    _assert_search_fact_protocol(result.typed)
    envelope = _assert_result_envelope(result.typed, result_kind="result_page_truncated", semantic_complete=False)
    assert "glob_files(" in str(envelope["recovery_call"])
    assert "offset=1" in result.content_preview


def test_glob_files_incomplete_scan_hint_names_glob_files(tmp_path: Path):
    context = _tool_context(tmp_path)
    context.run_workspace = context.run_workspace.model_copy(update={"execution_mode": "docker"})
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "src").mkdir()
    (workspace / "src" / "a.py").write_text("# file\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_glob_incomplete",
            tool_name="glob_files",
            arguments={"path": "src", "pattern": "*.py"},
            turn=1,
        ),
        context,
    )

    envelope = _assert_result_envelope(result.typed, result_kind="incomplete_file_listing", semantic_complete=False)

    assert result.status == "ok"
    assert envelope["recovery_hint"] is not None
    assert "glob_files" in str(envelope["recovery_hint"])
    assert "list_files" not in str(envelope["recovery_hint"])


def test_update_working_state_records_state_without_repo_mutation(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "notes.txt").write_text("one\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_working_state",
            tool_name="update_working_state",
            arguments={
                "current_hypothesis": "bug is in parser",
                "candidate_files": ["notes.txt", ".git/config"],
                "next_action": "read parser entrypoint",
                "completed_steps": ["listed files"],
                "blocking_question": "",
            },
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert (workspace / "notes.txt").read_text(encoding="utf-8") == "one\n"
    assert context.working_state is not None
    assert context.working_state["current_hypothesis"] == "bug is in parser"
    assert context.working_state["candidate_files"] == ["notes.txt"]
    assert context.working_state["skipped_candidate_file_count"] == 1
    assert result.typed["trainable"] is False
    envelope = _assert_result_envelope(result.typed, result_kind="working_state_updated", semantic_complete=True)
    assert "working_state_updated" in envelope["context_effects"]


def test_symbol_search_finds_python_class_and_method_symbols(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    package = workspace / "pkg"
    package.mkdir()
    (package / "model.py").write_text(
        "class MultiValue:\n"
        "    def append_value(self, value):\n"
        "        return value\n\n"
        "def helper(value):\n"
        "    return value\n",
        encoding="utf-8",
    )

    class_result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_symbol_class",
            tool_name="symbol_search",
            arguments={"query": "MultiValue", "root": "pkg", "symbol_kind": "class"},
            turn=1,
        ),
        context,
    )
    method_result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_symbol_method",
            tool_name="symbol_search",
            arguments={"query": "append_value", "root": "pkg", "symbol_kind": "method"},
            turn=1,
        ),
        context,
    )

    assert class_result.status == "ok"
    assert class_result.typed["result_kind"] == "symbols_found"
    assert class_result.typed["symbols"][0]["qualified_name"] == "MultiValue"
    assert class_result.typed["symbol_index_policy_version"] == minimal_tools.SYMBOL_INDEX_POLICY_VERSION
    _assert_search_fact_protocol(class_result.typed)
    _assert_result_envelope(class_result.typed, result_kind="symbols_found", semantic_complete=True)
    assert method_result.typed["symbols"][0]["qualified_name"] == "MultiValue.append_value"


def test_symbol_search_uses_cache_and_invalidates_on_source_hash_change(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    package = workspace / "pkg"
    package.mkdir()
    model = package / "model.py"
    model.write_text(
        "class Alpha:\n"
        "    pass\n\n"
        "class Beta:\n"
        "    pass\n",
        encoding="utf-8",
    )
    executor = ToolExecutor()

    first = executor.execute(
        ToolCall(
            tool_call_id="call_symbol_alpha",
            tool_name="symbol_search",
            arguments={"query": "Alpha", "root": "pkg", "symbol_kind": "class"},
            turn=1,
        ),
        context,
    )
    second = executor.execute(
        ToolCall(
            tool_call_id="call_symbol_beta",
            tool_name="symbol_search",
            arguments={"query": "Beta", "root": "pkg", "symbol_kind": "class"},
            turn=2,
        ),
        context,
    )
    model.write_text(
        "class Alpha:\n"
        "    pass\n\n"
        "class Gamma:\n"
        "    pass\n",
        encoding="utf-8",
    )
    third = executor.execute(
        ToolCall(
            tool_call_id="call_symbol_gamma",
            tool_name="symbol_search",
            arguments={"query": "Gamma", "root": "pkg", "symbol_kind": "class"},
            turn=3,
        ),
        context,
    )

    assert first.typed["cache_miss_file_count"] == 1
    assert first.typed["cache_hit_file_count"] == 0
    assert second.typed["cache_miss_file_count"] == 0
    assert second.typed["cache_hit_file_count"] == 1
    assert third.typed["cache_miss_file_count"] == 1
    assert third.typed["cache_hit_file_count"] == 0
    assert third.typed["symbols"][0]["qualified_name"] == "Gamma"


def test_symbol_search_wide_root_requires_narrow_root_before_full_scan(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    package = workspace / "pkg"
    package.mkdir()
    threshold = minimal_tools.SYMBOL_SEARCH_WIDE_ROOT_CANDIDATE_FILE_THRESHOLD
    for index in range(threshold + 1):
        (package / f"module_{index}.py").write_text(
            f"class Candidate{index}:\n    pass\n",
            encoding="utf-8",
        )

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_symbol_wide_root",
            tool_name="symbol_search",
            arguments={"query": "Candidate", "root": ".", "symbol_kind": "class"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["result_kind"] == "scan_requires_narrow_root"
    assert result.typed["scan_complete"] is False
    assert result.typed["semantic_complete"] is False
    assert result.typed["scan_complete_reason"] == "wide_root_candidate_file_limit"
    assert result.typed["candidate_file_count"] == threshold + 1
    assert result.typed["scanned_file_count"] == 0
    assert result.typed["recommended_narrow_roots"][0] == "pkg"
    assert result.typed["recommended_next_calls"][0]["arguments"]["root"] == "pkg"
    assert result.typed["slow_scan"] is False
    envelope = _assert_result_envelope(
        result.typed,
        result_kind="scan_requires_narrow_root",
        semantic_complete=False,
    )
    assert "root='pkg'" in envelope["recovery_call"]


def test_symbol_search_parse_error_is_partial_not_complete_no_match(tmp_path: Path):
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "bad.py").write_text("def broken(:\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_symbol_parse_error",
            tool_name="symbol_search",
            arguments={"query": "broken"},
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert result.typed["result_kind"] == "partial_symbol_results"
    assert result.typed["scan_complete"] is False
    assert result.typed["scan_complete_reason"] == "parse_error_detected"
    assert result.typed["parse_error_count"] == 1
    envelope = _assert_result_envelope(result.typed, result_kind="partial_symbol_results", semantic_complete=False)
    assert envelope["recommended_next_calls"][0]["tool"] == "grep"


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
    assert list_result.typed["read_error_count"] == 0
    assert list_result.typed["visibility_error_count"] == 0
    assert grep_result.status == "ok"
    assert "inside.txt" in grep_result.content_preview
    assert "outside-link.txt" not in grep_result.content_preview
    assert grep_result.typed["skipped_symlink_count"] == 1
    assert grep_result.typed["read_error_count"] == 0
    assert grep_result.typed["visibility_error_count"] == 0


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
    assert grep_result.typed["read_error_count"] == 0
    assert grep_result.typed["visibility_error_count"] == 0
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
    envelope = _assert_result_envelope(result.typed, result_kind="file_window_truncated", semantic_complete=False)
    assert envelope["result_limit_reached"] is True
    assert "start_line=2" in str(envelope["recovery_call"])
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


def test_edit_file_requires_read_when_policy_enabled(tmp_path: Path):
    context = _tool_context(tmp_path)
    context.tool_policy = ToolPolicy(
        tool_policy_version="repo_harness_tool_policy_pre_verl_read_before_edit_v1",
        require_read_before_edit=True,
    )
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "notes.txt").write_text("one\n", encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_edit_without_read",
            tool_name="edit_file",
            arguments={"path": "notes.txt", "old_text": "one\n", "new_text": "two\n"},
            turn=1,
        ),
        context,
    )

    assert result.status == "error"
    assert result.error_type == "read_before_edit_required"
    assert (workspace / "notes.txt").read_text(encoding="utf-8") == "one\n"
    envelope = _assert_result_envelope(result.typed, result_kind="read_before_edit_required", semantic_complete=True)
    assert envelope["recovery_call"] == "read_file(path='notes.txt')"


def test_edit_file_allows_cached_read_and_rejects_stale_cache(tmp_path: Path):
    context = _tool_context(tmp_path)
    context.tool_policy = ToolPolicy(
        tool_policy_version="repo_harness_tool_policy_pre_verl_read_before_edit_v1",
        require_read_before_edit=True,
    )
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "notes.txt").write_text("one\n", encoding="utf-8")

    read_result = ToolExecutor().execute(
        ToolCall(tool_call_id="call_read_before_edit", tool_name="read_file", arguments={"path": "notes.txt"}, turn=1),
        context,
    )
    edit_result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_edit_after_read",
            tool_name="edit_file",
            arguments={"path": "notes.txt", "old_text": "one\n", "new_text": "two\n"},
            turn=2,
        ),
        context,
    )
    (workspace / "notes.txt").write_text("three\n", encoding="utf-8")
    stale_result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_edit_stale_cache",
            tool_name="edit_file",
            arguments={"path": "notes.txt", "old_text": "three\n", "new_text": "four\n"},
            turn=3,
        ),
        context,
    )

    assert read_result.status == "ok"
    assert edit_result.status == "ok"
    assert edit_result.typed["require_read_before_edit"] is True
    assert stale_result.status == "error"
    assert stale_result.error_type == "stale_file_state"
    assert stale_result.typed["cached_content_hash"] == hashlib.sha256("two\n".encode()).hexdigest()
    assert stale_result.typed["current_content_hash"] == hashlib.sha256("three\n".encode()).hexdigest()


def test_edit_file_expected_hash_satisfies_read_before_edit_policy(tmp_path: Path):
    context = _tool_context(tmp_path)
    context.tool_policy = ToolPolicy(
        tool_policy_version="repo_harness_tool_policy_pre_verl_read_before_edit_v1",
        require_read_before_edit=True,
    )
    workspace = Path(context.run_workspace.workspace_path)
    original = "one\n"
    (workspace / "notes.txt").write_text(original, encoding="utf-8")

    result = ToolExecutor().execute(
        ToolCall(
            tool_call_id="call_edit_expected_hash",
            tool_name="edit_file",
            arguments={
                "path": "notes.txt",
                "old_text": "one\n",
                "new_text": "two\n",
                "expected_content_hash": hashlib.sha256(original.encode()).hexdigest(),
            },
            turn=1,
        ),
        context,
    )

    assert result.status == "ok"
    assert (workspace / "notes.txt").read_text(encoding="utf-8") == "two\n"


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
    _assert_result_envelope(all_diff.typed, result_kind="diff_present", semantic_complete=True)
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


def test_bash_test_command_variants_route_to_run_tests_policy(tmp_path: Path):
    context = _tool_context(tmp_path)
    context.test_feedback_policy = "structured_public_feedback"
    executor = ToolExecutor()

    for index, command in enumerate(["tox", "nox -s tests", "python -m unittest tests.test_example"]):
        normalized = executor.normalize(
            ToolCall(
                tool_call_id=f"call_bash_test_{index}",
                tool_name="bash",
                arguments={"command": command},
                turn=1,
            ),
            context,
        )

        assert normalized.effective_tool_name == "run_tests"
        assert normalized.route_reason == "model_bash_test_routed_to_run_tests"
        assert normalized.normalized_arguments["command_category"] == "public_test"


def test_bash_test_command_disabled_stays_bash_for_policy_denial(tmp_path: Path):
    context = _tool_context(tmp_path)
    context.test_feedback_policy = "disabled"

    normalized = ToolExecutor().normalize(
        ToolCall(
            tool_call_id="call_disabled_bash_test",
            tool_name="bash",
            arguments={"command": "python -m pytest -q"},
            turn=1,
        ),
        context,
    )

    assert normalized.effective_tool_name == "bash"
    assert normalized.normalized_arguments["policy_decision"] == "deny"
    assert normalized.normalized_arguments["command_category"] == "public_test"
    assert normalized.normalized_arguments["safe_argv"] == ["python", "-m", "pytest", "-q"]


def test_bash_execution_uses_safe_argv_metadata(tmp_path: Path):
    context = _tool_context(tmp_path)
    tool_call = ToolCall(
        tool_call_id="call_pwd_safe_argv",
        tool_name="bash",
        arguments={"command": "pwd"},
        turn=1,
    )
    executor = ToolExecutor()

    assert executor.check_permission(tool_call, context).decision == "allow"
    result = executor.execute(tool_call, context)

    assert result.status == "ok"
    assert result.typed["safe_argv"] == ["pwd"]
    assert result.typed["policy_decision"] == "allow"
    assert result.typed["command_category"] == "diagnostic"
    assert result.typed["shell_execution"] is False


def test_bash_execution_requires_policy_safe_argv(tmp_path: Path):
    context = _tool_context(tmp_path)
    tool_call = ToolCall(
        tool_call_id="call_pwd_missing_safe_argv",
        tool_name="bash",
        arguments={"command": "pwd"},
        turn=1,
    )
    normalized = ToolExecutor().normalize(tool_call, context)
    normalized.normalized_arguments["safe_argv"] = None

    result = ToolExecutor().execute(tool_call, context)

    assert result.status == "ok"
    assert result.typed["safe_argv"] == ["pwd"]

    direct_result = ToolExecutor()._bash(tool_call, normalized, context)  # noqa: SLF001
    assert direct_result.status == "error"
    assert direct_result.error_type == "bash_safe_argv_missing"
    assert direct_result.typed["shell_execution"] is False


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


def _assert_search_fact_protocol(typed: dict[str, object]) -> None:
    assert typed["search_fact_policy_version"] == minimal_tools.SEARCH_FACT_POLICY_VERSION
    assert isinstance(typed["root"], str)
    assert isinstance(typed["search_backend"], str)
    assert typed["workspace_execution_mode"] in {"local_process", "docker"}
    assert isinstance(typed["workspace_backend"], str)
    assert isinstance(typed["read_error_count"], int)
    assert isinstance(typed["read_error_samples"], list)
    assert isinstance(typed["visibility_error_count"], int)
    assert isinstance(typed["visibility_error_samples"], list)
    assert isinstance(typed["backend_mismatch_detected"], bool)
    assert isinstance(typed["scan_complete_reason"], str)


def _assert_result_envelope(
    typed: dict[str, object],
    *,
    result_kind: str,
    semantic_complete: bool,
) -> dict[str, object]:
    envelope = typed["result_envelope"]
    assert isinstance(envelope, dict)
    assert envelope["schema_version"] == minimal_tools.TOOL_RESULT_ENVELOPE_VERSION
    assert envelope["result_kind"] == result_kind
    assert envelope["semantic_complete"] is semantic_complete
    assert isinstance(envelope["model_visible_text_truncated"], bool)
    assert isinstance(envelope["result_limit_reached"], bool)
    assert isinstance(envelope["artifact_backed_full_result"], bool)
    assert isinstance(envelope["recommended_next_calls"], list)
    assert isinstance(envelope["context_effects"], list)
    return envelope
