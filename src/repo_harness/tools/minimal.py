"""第一版工具系统和内置工具。"""

from __future__ import annotations

import json
import hashlib
import difflib
import re
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from repo_harness.context.tool_result_artifacts import (
    ToolResultArtifactError,
    ToolResultArtifactIndex,
    read_tool_result_artifact as read_tool_result_artifact_page,
)
from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.errors import WorkspaceError
from repo_harness.permissions import PermissionContext, PermissionDecision, PermissionSystem
from repo_harness.schema_base import stable_hash
from repo_harness.tasks.command_policy import evaluate_model_bash_command
from repo_harness.tools.symbol_index import (
    SUPPORTED_SYMBOL_KINDS,
    SYMBOL_INDEX_POLICY_VERSION,
    filter_symbols,
    index_python_symbols,
)
from repo_harness.tools.schemas import ToolCall, ToolResult
from repo_harness.trajectory import ArtifactRef, RunRecorder
from repo_harness.verifier import PytestVerifier
from repo_harness.workspace import RunWorkspace, WorkspaceAdapter

DEFAULT_TOOL_ORDER = [
    "list_files",
    "glob_files",
    "read_file",
    "read_tool_result_artifact",
    "grep",
    "symbol_search",
    "update_working_state",
    "edit_file",
    "create_file",
    "bash",
    "run_tests",
    "git_diff",
]
MINIMAL_TOOLS = DEFAULT_TOOL_ORDER
SYMBOL_SEARCH_WIDE_ROOT_CANDIDATE_FILE_THRESHOLD = 120
SYMBOL_SEARCH_SLOW_SCAN_THRESHOLD_MS = 5000
MODEL_HIDDEN_TOOL_PATH_PARTS = frozenset(
    {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pre_verl_venv",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        ".aws",
        ".env",
        ".gnupg",
        ".netrc",
        ".npmrc",
        ".pypirc",
        ".ssh",
        "__pycache__",
        "build",
        "credentials",
        "credentials.json",
        "dist",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
        "node_modules",
        "pip.conf",
        "pip.ini",
        "secret",
        "secret.json",
        "secret.txt",
        "secrets.json",
        "token",
        "token.json",
        "token.txt",
        "venv",
    }
)
MODEL_HIDDEN_TOOL_PATH_SUFFIXES = frozenset({".cer", ".crt", ".key", ".p12", ".pem", ".pfx"})
GREP_MAX_SCANNED_FILES = 2000
GREP_MAX_MATCHES = 200
DEFAULT_RESOLVED_MAX_OUTPUT_CHARS = 12000
LIST_FILES_DEFAULT_MAX_ENTRIES = 200
GIT_DIFF_CHANGED_FILE_LIMIT = 200
SEARCH_FACT_POLICY_VERSION = "repo_harness_search_fact_trust_v1"
TOOL_RESULT_ENVELOPE_VERSION = "repo_harness_tool_result_envelope_v1"
TOOL_RESULT_CONTEXT_EFFECTS = frozenset(
    {
        "repository_diff_observed",
        "repository_file_state_updated",
        "tool_result_recoverable",
        "working_state_updated",
    }
)
GREP_OUTPUT_MODES = {"content", "files_with_matches", "count"}

@dataclass(frozen=True)
class ToolDefinition:
    name: str
    tool_version: str
    model_visible_description: str
    model_visible_prompt: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    max_result_size: int
    is_read_only: bool = False
    is_concurrency_safe: bool = False
    is_destructive: bool = False
    requires_permission: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("tool definition must include name.")
        if not self.model_visible_description:
            raise ValueError(f"{self.name} missing model_visible_description.")
        if not self.model_visible_prompt:
            raise ValueError(f"{self.name} missing model_visible_prompt.")
        if not self.input_schema:
            raise ValueError(f"{self.name} missing input_schema.")
        if not self.output_schema:
            raise ValueError(f"{self.name} missing output_schema.")
        if self.max_result_size <= 0:
            raise ValueError(f"{self.name} must declare positive max_result_size.")


class ToolRegistry:
    def __init__(self, definitions: list[ToolDefinition] | None = None) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._order: list[str] = []
        for definition in definitions or []:
            self.register(definition)

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"duplicate tool registered: {definition.name}")
        self._tools[definition.name] = definition
        self._order.append(definition.name)

    def get(self, name: str) -> ToolDefinition:
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return list(self._order)


@dataclass(frozen=True)
class ToolOutputLimits:
    max_tool_output_chars: int = DEFAULT_RESOLVED_MAX_OUTPUT_CHARS


@dataclass(frozen=True)
class ToolPolicy:
    tool_order: list[str] = field(default_factory=lambda: list(DEFAULT_TOOL_ORDER))
    tool_policy_version: str = "repo_harness_tool_policy_v0"
    require_read_before_edit: bool = False


@dataclass
class ToolExecutionContext:
    run_id: str
    task_id: str
    workspace_facade: WorkspaceAdapter
    run_workspace: RunWorkspace
    artifact_writer: RunRecorder
    permission_context: PermissionContext
    verifier_feedback_facade: PytestVerifier
    resolved_verifier_plan: ResolvedVerifierPlan
    output_limits: ToolOutputLimits = field(default_factory=ToolOutputLimits)
    tool_policy: ToolPolicy = field(default_factory=ToolPolicy)
    test_feedback_policy: str = "oracle_hidden_feedback"
    feedback_tests_passed_policy: str = "stop_immediately"
    budget_manager: object | None = None
    abort_signal: object | None = None
    file_state_cache: dict[str, str] = field(default_factory=dict)
    working_state: dict[str, Any] | None = None
    tool_result_artifact_index: ToolResultArtifactIndex | None = None

    @property
    def workspace_adapter(self) -> WorkspaceAdapter:
        return self.workspace_facade

    @property
    def recorder(self) -> RunRecorder:
        return self.artifact_writer

    @property
    def verifier(self) -> PytestVerifier:
        return self.verifier_feedback_facade


@dataclass(frozen=True)
class NormalizedToolRequest:
    requested_tool_name: str
    effective_tool_name: str
    requested_arguments: dict[str, Any]
    normalized_arguments: dict[str, Any]
    effective_arguments: dict[str, Any]
    normalized_input_hash: str
    route_reason: str | None = None
    requested_cwd: str | None = None
    effective_cwd: str | None = None


class ToolExecutor:
    def __init__(
        self,
        *,
        registry: ToolRegistry | None = None,
        permission_system: PermissionSystem | None = None,
    ) -> None:
        self.registry = registry or default_tool_registry()
        self.permission_system = permission_system or PermissionSystem()
        self._symbol_index_cache: dict[
            tuple[str, str],
            tuple[list[dict[str, Any]], str | None],
        ] = {}

    def is_known(self, tool_name: str) -> bool:
        return self.registry.has(tool_name)

    def validate_input(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolResult | None:
        issue = _schema_issue(tool_call.tool_name, tool_call.arguments)
        if issue is None:
            return None
        ref = context.recorder.write_json_artifact(
            "tool_schema_validation_failed",
            {
                "tool_call_id": tool_call.tool_call_id,
                "tool_name": tool_call.tool_name,
                "arguments": tool_call.arguments,
                **issue,
            },
        )
        return _tool_result(
            tool_call,
            status="error",
            content=(
                "schema_validation_failed: "
                f"field={issue['field']} expected={issue['expected_type']} "
                f"actual={issue['actual_type']} retryable=true"
            ),
            error_type="schema_validation_failed",
            artifact_refs=[ref],
            typed=issue,
        )

    def check_permission(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> PermissionDecision:
        normalized = self.normalize(tool_call, context)
        return self.permission_system.check(
            tool_call_id=tool_call.tool_call_id,
            requested_tool_name=normalized.requested_tool_name,
            effective_tool_name=normalized.effective_tool_name,
            tool_definition=self.registry.get(normalized.effective_tool_name),
            requested_arguments=normalized.requested_arguments,
            normalized_arguments=normalized.normalized_arguments,
            permission_context=context.permission_context,
            workspace_facade=context.workspace_adapter,
            workspace_path=context.run_workspace.workspace_path,
        )

    def denied_result(
        self,
        tool_call: ToolCall,
        decision: PermissionDecision,
        context: ToolExecutionContext,
    ) -> ToolResult:
        normalized = self.normalize(tool_call, context)
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="denied",
            content=decision.reason,
            error_type="permission_denied",
            typed={
                "permission_decision": decision.model_dump(mode="json"),
                "policy_decision": decision.policy_decision,
                "command_category": decision.command_category,
                "reason_code": decision.reason_code,
                "recovery_hint": decision.recovery_hint,
                "safe_argv": decision.safe_argv,
                "timeout_sec": decision.timeout_sec,
                "shell_execution": decision.shell_execution,
            },
        )

    def invalid_tool_result(self, tool_call: ToolCall) -> ToolResult:
        return _tool_result(
            tool_call,
            status="error",
            content=f"Unknown tool: {tool_call.tool_name}",
            error_type="unknown_tool",
        )

    def disallowed_tool_result(
        self,
        tool_call: ToolCall,
        *,
        reason: str,
        normalized: NormalizedToolRequest | None = None,
    ) -> ToolResult:
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="denied",
            content=reason,
            error_type="tool_not_allowed_by_scaffold",
            typed={"policy_reason": reason},
        )

    def disabled_test_feedback_result(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
    ) -> ToolResult:
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="denied",
            content=(
                "run_tests is disabled by test_feedback_policy=disabled; "
                "formal final verifier still runs after the agent stops."
            ),
            error_type="test_feedback_disabled",
            typed={
                "test_feedback_policy": "disabled",
                "feedback_tests_passed_policy": "not_applicable",
            },
        )

    def execute(self, tool_call: ToolCall, context: ToolExecutionContext) -> ToolResult:
        if not self.is_known(tool_call.tool_name):
            return self.invalid_tool_result(tool_call)
        normalized = self.normalize(tool_call, context)
        try:
            if normalized.effective_tool_name == "list_files":
                return self._list_files(tool_call, normalized, context)
            if normalized.effective_tool_name == "glob_files":
                return self._list_files(tool_call, normalized, context)
            if normalized.effective_tool_name == "read_file":
                return self._read_file(tool_call, normalized, context)
            if normalized.effective_tool_name == "read_tool_result_artifact":
                return self._read_tool_result_artifact(tool_call, normalized, context)
            if normalized.effective_tool_name == "grep":
                return self._grep(tool_call, normalized, context)
            if normalized.effective_tool_name == "symbol_search":
                return self._symbol_search(tool_call, normalized, context)
            if normalized.effective_tool_name == "update_working_state":
                return self._update_working_state(tool_call, normalized, context)
            if normalized.effective_tool_name == "edit_file":
                return self._edit_file(tool_call, normalized, context)
            if normalized.effective_tool_name == "create_file":
                return self._create_file(tool_call, normalized, context)
            if normalized.effective_tool_name == "bash":
                return self._bash(tool_call, normalized, context)
            if normalized.effective_tool_name == "run_tests":
                return self._run_tests(tool_call, normalized, context)
            if normalized.effective_tool_name == "git_diff":
                return self._git_diff(tool_call, normalized, context)
        except WorkspaceError as exc:
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="denied" if _is_permission_workspace_error(str(exc)) else "error",
                content=str(exc),
                error_type=(
                    "permission_denied"
                    if _is_permission_workspace_error(str(exc))
                    else "tool_error"
                ),
            )
        except Exception as exc:  # noqa: BLE001 - 工具错误必须回流为 ToolResult
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=str(exc),
                error_type="tool_error",
            )
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="error",
            content="Unhandled tool",
            error_type="tool_error",
        )

    def normalize(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> NormalizedToolRequest:
        args = dict(tool_call.arguments)
        requested = tool_call.tool_name
        effective = requested
        route_reason = None
        normalized_args: dict[str, Any]
        effective_args: dict[str, Any]
        requested_cwd = None
        effective_cwd = None

        if requested == "list_files":
            normalized_args = {
                "root": args.get("path", args.get("root", ".")),
                "offset": int(args.get("offset", 0)),
                "max_entries": int(args.get("max_entries", LIST_FILES_DEFAULT_MAX_ENTRIES)),
                "kind": args.get("kind", "file"),
            }
            if "glob" in args:
                normalized_args["glob"] = args["glob"]
            elif "pattern" in args:
                normalized_args["glob"] = args["pattern"]
            effective_args = dict(normalized_args)
        elif requested == "glob_files":
            normalized_args = {
                "root": args.get("path", args.get("root", ".")),
                "glob": args.get("pattern", args.get("glob")),
                "offset": int(args.get("offset", 0)),
                "max_entries": int(args.get("max_entries", LIST_FILES_DEFAULT_MAX_ENTRIES)),
                "kind": "file",
            }
            effective_args = dict(normalized_args)
        elif requested == "read_file":
            normalized_args = {"path": args["path"]}
            if "start_line" in args:
                normalized_args["start_line"] = args["start_line"]
            if "end_line" in args:
                normalized_args["end_line"] = args["end_line"]
            if "offset" in args and "start_line" not in normalized_args:
                normalized_args["start_line"] = args["offset"]
            if "limit" in args and "end_line" not in normalized_args:
                start_line = int(normalized_args.get("start_line", 1))
                normalized_args["end_line"] = start_line + int(args["limit"]) - 1
            effective_args = dict(normalized_args)
        elif requested == "read_tool_result_artifact":
            normalized_args = {
                "artifact_id": str(args["artifact_id"]),
                "offset": int(args.get("offset", 0)),
                "limit": int(args.get("limit", 8000)),
            }
            effective_args = dict(normalized_args)
        elif requested == "grep":
            query = args.get("query", args.get("pattern"))
            normalized_args = {
                "query": query,
                "root": args.get("path", args.get("root", ".")),
                "mode": args.get("mode", "literal"),
                "output_mode": args.get("output_mode", "content"),
                "max_matches": int(args.get("max_matches", GREP_MAX_MATCHES)),
                "offset": int(args.get("offset", 0)),
                "context_lines": int(args.get("context_lines", 0)),
            }
            if "glob" in args:
                normalized_args["glob"] = args["glob"]
            effective_args = dict(normalized_args)
        elif requested == "symbol_search":
            normalized_args = {
                "query": args["query"],
                "root": args.get("path", args.get("root", ".")),
                "symbol_kind": args.get("symbol_kind", args.get("kind", "any")),
                "offset": int(args.get("offset", 0)),
                "max_results": int(args.get("max_results", 20)),
            }
            effective_args = dict(normalized_args)
        elif requested == "update_working_state":
            normalized_args = {
                "current_hypothesis": str(args.get("current_hypothesis", "")),
                "candidate_files": list(args.get("candidate_files", [])),
                "next_action": str(args.get("next_action", "")),
                "completed_steps": list(args.get("completed_steps", [])),
                "blocking_question": str(args.get("blocking_question", "")),
            }
            effective_args = dict(normalized_args)
        elif requested == "edit_file":
            normalized_args = {
                "path": args["path"],
                "old_text": args["old_text"],
                "new_text": args["new_text"],
                "replace_all": bool(args.get("replace_all", False)),
            }
            if "expected_content_hash" in args:
                normalized_args["expected_content_hash"] = args["expected_content_hash"]
            elif "expected_content_sha256" in args:
                normalized_args["expected_content_hash"] = args["expected_content_sha256"]
            effective_args = dict(normalized_args)
        elif requested == "create_file":
            normalized_args = {"path": args["path"], "content": args["content"]}
            effective_args = dict(normalized_args)
        elif requested == "bash":
            command = str(args["command"]).strip()
            cwd = str(args.get("cwd", "."))
            requested_timeout = int(args.get("timeout_sec", 30))
            timeout = _clamp_command_timeout(requested_timeout, context)
            command_policy_decision = evaluate_model_bash_command(
                command,
                configured_test_command=context.permission_context.test_command,
                test_feedback_policy=context.test_feedback_policy,
            )
            requested_cwd = cwd
            normalized_args = {
                "command": command,
                "cwd": cwd,
                "timeout_sec": timeout,
                "command_policy_decision": command_policy_decision.model_dump(mode="json"),
                "policy_decision": command_policy_decision.decision,
                "command_category": command_policy_decision.command_category,
                "reason_code": command_policy_decision.reason_code or command_policy_decision.matched_rule,
                "safe_argv": command_policy_decision.safe_argv,
                "recovery_hint": command_policy_decision.recovery_hint,
            }
            if timeout != requested_timeout:
                normalized_args["requested_timeout_sec"] = requested_timeout
                normalized_args["timeout_clamped_to_sec"] = timeout
            if (
                command_policy_decision.command_category == "public_test"
                and command_policy_decision.decision == "route_to_run_tests"
            ):
                effective = "run_tests"
                route_reason = "model_bash_test_routed_to_run_tests"
                effective_args = {}
            else:
                effective_args = dict(normalized_args)
                effective_args["effective_cwd"] = effective_cwd
        elif requested == "git_diff":
            normalized_args = {}
            if "path" in args:
                normalized_args["path"] = args["path"]
            effective_args = dict(normalized_args)
        elif requested == "run_tests":
            normalized_args = {}
            effective_args = {}
        else:
            normalized_args = args
            effective_args = args
        return NormalizedToolRequest(
            requested_tool_name=requested,
            effective_tool_name=effective,
            requested_arguments=tool_call.arguments,
            normalized_arguments=normalized_args,
            effective_arguments=effective_args,
            normalized_input_hash=stable_hash(normalized_args),
            route_reason=route_reason,
            requested_cwd=requested_cwd,
            effective_cwd=effective_cwd,
        )

    def _list_files(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        root = str(normalized.normalized_arguments["root"])
        glob = normalized.normalized_arguments.get("glob")
        offset = max(0, int(normalized.normalized_arguments.get("offset", 0)))
        max_entries = max(
            1,
            min(
                int(normalized.normalized_arguments.get("max_entries", LIST_FILES_DEFAULT_MAX_ENTRIES)),
                1000,
            ),
        )
        kind = str(normalized.normalized_arguments.get("kind", "file"))
        if kind != "file":
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content="list_files currently supports kind='file' only; use grep to locate symbols.",
                error_type="unsupported_kind",
                typed={
                    "kind": kind,
                    "supported_kinds": ["file"],
                    "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                    "result_envelope": _result_envelope(
                        result_kind="unsupported_kind",
                        semantic_complete=True,
                        recovery_call="list_files(kind='file')",
                        recovery_hint="list_files currently supports kind='file' only.",
                    ),
                },
            )
        context.workspace_adapter.resolve_workspace_path(
            context.run_workspace.workspace_path,
            root,
            must_exist=True,
        )
        files = context.workspace_adapter.list_files(
            context.run_workspace.workspace_path,
            root,
            pattern=glob,
        )
        visible_files: list[str] = []
        hidden_path_count = 0
        symlink_outside_workspace_count = 0
        workspace_boundary_or_missing_count = 0
        visibility_error_count = 0
        visibility_error_samples: list[dict[str, str]] = []
        for rel_path in files:
            visible, reason = _model_visible_path_status(context, rel_path)
            if visible:
                visible_files.append(rel_path)
                continue
            if reason in {"hidden_path", "symlink_target_hidden_path"}:
                hidden_path_count += 1
            elif reason == "symlink_outside_workspace":
                symlink_outside_workspace_count += 1
            elif reason == "workspace_boundary_or_missing":
                workspace_boundary_or_missing_count += 1
            else:
                visibility_error_count += 1
                if len(visibility_error_samples) < 5:
                    visibility_error_samples.append({"path": rel_path, "reason": reason or "visibility_error"})
        page = visible_files[offset : offset + max_entries]
        next_offset = offset + len(page) if offset + len(page) < len(visible_files) else None
        truncated = next_offset is not None
        backend_mismatch_detected = _backend_mismatch_detected(context)
        scan_complete = (
            visibility_error_count == 0
            and workspace_boundary_or_missing_count == 0
            and not backend_mismatch_detected
        )
        scan_complete_reason = _scan_complete_reason(
            scan_complete=scan_complete,
            result_limit_reached=truncated,
            scan_limit_reached=False,
            read_error_count=0,
            visibility_error_count=visibility_error_count,
            workspace_boundary_or_missing_count=workspace_boundary_or_missing_count,
            backend_mismatch_detected=backend_mismatch_detected,
            total_match_count=len(visible_files),
        )
        result_kind = (
            "result_page_truncated"
            if truncated
            else ("complete_file_listing" if scan_complete else "incomplete_file_listing")
        )
        recommended_next_calls = _list_files_recommended_next_calls(
            root=root,
            glob=str(glob) if glob is not None else None,
            next_offset=next_offset,
            max_entries=max_entries,
            scan_complete=scan_complete,
        )
        if normalized.effective_tool_name == "glob_files":
            recommended_next_calls = _glob_files_recommended_next_calls(
                recommended_next_calls,
                fallback_pattern=str(glob or "*"),
            )
        search_fact_fields = _search_fact_fields(
            context=context,
            root=root,
            search_backend="workspace_adapter_list_files",
            scan_complete_reason=scan_complete_reason,
            read_error_count=0,
            read_error_samples=[],
            visibility_error_count=visibility_error_count,
            visibility_error_samples=visibility_error_samples,
            backend_mismatch_detected=backend_mismatch_detected,
        )
        ref = context.recorder.write_json_artifact(
            "list_files",
            {
                "tool_name": normalized.effective_tool_name,
                "root": root,
                "glob": glob,
                "files": visible_files,
                "offset": offset,
                "max_entries": max_entries,
                "returned_files": page,
                "truncated": truncated,
                "next_offset": next_offset,
                "result_kind": result_kind,
                "scan_complete": scan_complete,
                "scan_complete_reason": scan_complete_reason,
                "hidden_path_count": hidden_path_count,
                "skipped_hidden_count": hidden_path_count,
                "skipped_hidden_path_count": hidden_path_count,
                "symlink_outside_workspace_count": symlink_outside_workspace_count,
                "skipped_symlink_count": symlink_outside_workspace_count,
                "workspace_boundary_or_missing_count": workspace_boundary_or_missing_count,
                "recommended_next_calls": recommended_next_calls,
                **search_fact_fields,
            },
        )
        preview = "\n".join(page) if page else "No files matched."
        if truncated:
            if normalized.effective_tool_name == "glob_files":
                recovery_text = (
                    f"glob_files(pattern={str(glob)!r}, path={root!r}, offset={next_offset}, "
                    f"max_entries={max_entries})"
                )
            else:
                recovery_text = (
                    f"list_files(path={root!r}, offset={next_offset}, "
                    f"max_entries={max_entries})"
                )
            preview += (
                f"\n[truncated] call {recovery_text} for the next page."
            )
        if not scan_complete:
            preview += (
                "\n[incomplete_scan] Some candidate paths could not be classified by the workspace backend. "
                "Do not treat this listing as a complete repository fact."
            )
        output_truncated = len(preview) > context.output_limits.max_tool_output_chars
        if next_offset is not None and normalized.effective_tool_name == "glob_files":
            recovery_call = (
                f"glob_files(pattern={str(glob)!r}, path={root!r}, "
                f"offset={next_offset}, max_entries={max_entries})"
            )
        elif next_offset is not None:
            recovery_call = f"list_files(root={root!r}, offset={next_offset}, max_entries={max_entries})"
        else:
            recovery_call = None
        recovery_hint = (
            "Use next_offset to continue the same file listing page."
            if next_offset is not None
            else (
                (
                    "Re-run glob_files with a narrower path or pattern before treating this listing as complete."
                    if normalized.effective_tool_name == "glob_files"
                    else "Re-run list_files with a narrower root or glob before treating this listing as complete."
                )
                if not scan_complete
                else None
            )
        )
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(preview, context.output_limits.max_tool_output_chars),
            truncated=output_truncated,
            artifact_refs=[ref],
            typed={
                "files": page,
                "returned_count": len(page),
                "total_visible_count": len(visible_files),
                "match_count": len(visible_files),
                "offset": offset,
                "max_entries": max_entries,
                "result_kind": result_kind,
                "scan_complete": scan_complete,
                "scan_complete_reason": scan_complete_reason,
                "truncated": truncated,
                "next_offset": next_offset,
                "hidden_path_count": hidden_path_count,
                "skipped_hidden_count": hidden_path_count,
                "skipped_hidden_path_count": hidden_path_count,
                "symlink_outside_workspace_count": symlink_outside_workspace_count,
                "skipped_symlink_count": symlink_outside_workspace_count,
                "workspace_boundary_or_missing_count": workspace_boundary_or_missing_count,
                "recommended_next_calls": recommended_next_calls,
                **search_fact_fields,
                "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                "result_envelope": _result_envelope(
                    result_kind=result_kind,
                    semantic_complete=scan_complete and not truncated,
                    model_visible_text_truncated=output_truncated,
                    result_limit_reached=truncated,
                    artifact_backed_full_result=True,
                    recommended_next_calls=recommended_next_calls,
                    recovery_call=recovery_call,
                    recovery_hint=recovery_hint,
                    context_effects=["tool_result_recoverable"],
                ),
            },
        )

    def _read_file(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        path = str(normalized.normalized_arguments["path"])
        visible, visibility_reason = _model_visible_path_status(context, path)
        if _is_model_hidden_tool_path(path) or visibility_reason in {"hidden_path", "symlink_target_hidden_path", "symlink_outside_workspace"}:
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=(
                    "Path is outside the model-visible repository source area. "
                    "Inspect source and tests in the repository checkout instead."
                ),
                error_type="model_hidden_path",
                typed={
                    "path": path,
                    "visibility_reason": visibility_reason,
                    "result_envelope": _result_envelope(
                        result_kind="model_hidden_path",
                        semantic_complete=True,
                        recovery_hint="Choose a model-visible source or test file inside the repository checkout.",
                    ),
                },
            )
        content = context.workspace_adapter.read_text(context.run_workspace.workspace_path, path)
        content_hash = _sha256_text(content)
        context.file_state_cache[path] = content_hash
        line_window = _line_window(
            content,
            start_line=normalized.normalized_arguments.get("start_line"),
            end_line=normalized.normalized_arguments.get("end_line"),
            max_chars=context.output_limits.max_tool_output_chars,
        )
        ref = context.recorder.write_artifact("read_file", content)
        preview = line_window["numbered_content"]
        if line_window["truncated"]:
            preview += (
                f"\n[truncated] call read_file(path={path!r}, "
                f"start_line={line_window['next_start_line']}) to continue."
            )
        output_truncated = bool(line_window["truncated"]) or len(preview) > context.output_limits.max_tool_output_chars
        recovery_call = (
            f"read_file(path={path!r}, start_line={line_window['next_start_line']})"
            if line_window["next_start_line"] is not None
            else None
        )
        recovery_hint = (
            "Use next_start_line to continue reading this file."
            if line_window["next_start_line"] is not None
            else "Re-read this file with a narrower line range if more context is needed."
        )
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(preview, context.output_limits.max_tool_output_chars),
            truncated=output_truncated,
            artifact_refs=[ref],
            typed={
                "path": path,
                "start_line": line_window["start_line"],
                "end_line": line_window["end_line"],
                "total_lines": line_window["total_lines"],
                "content_hash": content_hash,
                "content_sha256": content_hash,
                "truncated": line_window["truncated"],
                "next_start_line": line_window["next_start_line"],
                "raw_content_preview": line_window["raw_content_preview"],
                "numbered_content_preview": line_window["numbered_content"],
                "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                "result_envelope": _result_envelope(
                    result_kind="file_window_truncated" if line_window["truncated"] else "file_window_complete",
                    semantic_complete=not bool(line_window["truncated"]),
                    model_visible_text_truncated=output_truncated,
                    result_limit_reached=bool(line_window["truncated"]),
                    artifact_backed_full_result=True,
                    recovery_call=recovery_call,
                    recovery_hint=recovery_hint,
                    context_effects=["tool_result_recoverable"],
                ),
            },
        )

    def _read_tool_result_artifact(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        artifact_id = str(normalized.normalized_arguments.get("artifact_id") or "")
        misuse_hint = _tool_result_artifact_misuse_hint(artifact_id)
        if context.tool_result_artifact_index is None:
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=(
                    "tool_result_artifact_index_unavailable: no recoverable tool result artifacts "
                    f"are registered for this run. {misuse_hint['message']}"
                ),
                error_type="tool_result_artifact_index_unavailable",
                typed={
                    "artifact_id": artifact_id,
                    **misuse_hint["typed"],
                    "result_envelope": _result_envelope(
                        result_kind="tool_result_artifact_index_unavailable",
                        semantic_complete=True,
                        recovery_call=misuse_hint["typed"]["suggested_recovery_call"],
                        recovery_hint=misuse_hint["message"],
                        recommended_next_calls=misuse_hint["recommended_next_calls"],
                    ),
                },
            )
        try:
            page = read_tool_result_artifact_page(
                context.tool_result_artifact_index,
                artifact_id=artifact_id,
                offset=int(normalized.normalized_arguments.get("offset", 0)),
                limit=int(normalized.normalized_arguments.get("limit", 8000)),
            )
        except ToolResultArtifactError as exc:
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=f"tool_result_artifact_unavailable: {exc} {misuse_hint['message']}",
                error_type="tool_result_artifact_unavailable",
                typed={
                    "artifact_id": artifact_id,
                    "offset": normalized.normalized_arguments.get("offset"),
                    "limit": normalized.normalized_arguments.get("limit"),
                    **misuse_hint["typed"],
                    "result_envelope": _result_envelope(
                        result_kind="tool_result_artifact_unavailable",
                        semantic_complete=True,
                        recovery_call=misuse_hint["typed"]["suggested_recovery_call"],
                        recovery_hint=misuse_hint["message"],
                        recommended_next_calls=misuse_hint["recommended_next_calls"],
                    ),
                },
            )
        content = str(page["content"])
        visible_limit = max(1, context.output_limits.max_tool_output_chars)
        visible_content_chars = min(len(content), visible_limit)
        output_budget_truncated = len(content) > visible_content_chars
        visible_content = content[:visible_content_chars]
        visible_next_offset = (
            int(page["offset"]) + visible_content_chars
            if output_budget_truncated
            else page["next_offset"]
        )
        if page["next_offset"] is not None:
            content += (
                "\n[truncated] call read_tool_result_artifact("
                f"artifact_id={page['artifact_id']!r}, offset={page['next_offset']}, "
                f"limit={page['limit']}) to continue."
            )
        if output_budget_truncated:
            visible_content += (
                "\n[truncated] call read_tool_result_artifact("
                f"artifact_id={page['artifact_id']!r}, offset={visible_next_offset}, "
                f"limit={page['limit']}) to continue."
            )
        elif page["next_offset"] is not None:
            visible_content = content
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=visible_content,
            truncated=visible_next_offset is not None,
            typed={
                **page,
                "next_offset": visible_next_offset,
                "output_budget_truncated": output_budget_truncated,
                "requested_page_next_offset": page["next_offset"],
                "result_envelope": _result_envelope(
                    result_kind=(
                        "tool_result_artifact_page_truncated"
                        if visible_next_offset is not None
                        else "tool_result_artifact_page_complete"
                    ),
                    semantic_complete=visible_next_offset is None,
                    model_visible_text_truncated=visible_next_offset is not None,
                    artifact_backed_full_result=True,
                    recovery_call=(
                        "read_tool_result_artifact("
                        f"artifact_id={page['artifact_id']!r}, offset={visible_next_offset}, "
                        f"limit={page['limit']})"
                        if visible_next_offset is not None
                        else None
                    ),
                    recovery_hint=(
                        "Use next_offset to continue reading this stored tool result."
                        if visible_next_offset is not None
                        else "This page covers the remaining stored tool result content."
                    ),
                    context_effects=["tool_result_recoverable"],
                ),
            },
        )

    def _grep(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        query = str(normalized.normalized_arguments["query"])
        root = str(normalized.normalized_arguments["root"])
        legacy_query_alias_used = (
            "query" not in normalized.requested_arguments
            and "pattern" in normalized.requested_arguments
        )
        mode = str(normalized.normalized_arguments.get("mode", "literal"))
        output_mode = str(normalized.normalized_arguments.get("output_mode", "content"))
        glob = normalized.normalized_arguments.get("glob")
        offset = max(0, int(normalized.normalized_arguments.get("offset", 0)))
        max_matches = max(
            1,
            min(int(normalized.normalized_arguments.get("max_matches", GREP_MAX_MATCHES)), GREP_MAX_MATCHES),
        )
        context_lines = max(0, min(int(normalized.normalized_arguments.get("context_lines", 0)), 20))
        try:
            search_text = getattr(context.workspace_adapter, "search_text", None)
            backend = getattr(context.workspace_adapter, "backend", None)
            backend_value = getattr(backend, "value", backend)
            if callable(search_text) and str(backend_value) == "docker":
                payload = search_text(
                    context.run_workspace.workspace_path,
                    root=root,
                    query=query,
                    mode=mode,
                    glob=str(glob) if glob is not None else None,
                    output_mode=output_mode,
                    offset=offset,
                    max_matches=max_matches,
                    context_lines=context_lines,
                    timeout_sec=_clamp_command_timeout(30, context),
                    recorder=context.recorder,
                )
            else:
                payload = _grep_python(
                    context=context,
                    root=root,
                    query=query,
                    mode=mode,
                    glob=str(glob) if glob is not None else None,
                    offset=offset,
                    max_matches=max_matches,
                    context_lines=context_lines,
                    output_mode=output_mode,
                )
        except re.error as exc:
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=f"invalid_regex: {exc}; retry with a valid regex or mode='literal'.",
                error_type="invalid_regex",
                typed={
                    "query": query,
                    "mode": mode,
                    "recovery_hint": "Use mode='literal' for exact text, or simplify the regular expression.",
                    "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                    "result_envelope": _result_envelope(
                        result_kind="invalid_regex",
                        semantic_complete=True,
                        recovery_call=f"grep(query={query!r}, mode='literal')",
                        recovery_hint="Use mode='literal' for exact text, or simplify the regular expression.",
                    ),
                },
            )
        except WorkspaceError as exc:
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=str(exc),
                error_type="tool_execution_failed",
                typed={
                    "query": query,
                    "mode": mode,
                    "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                    "result_envelope": _result_envelope(
                        result_kind="workspace_error",
                        semantic_complete=False,
                        recovery_hint="Retry with a model-visible workspace-relative root or narrower glob.",
                    ),
                },
            )
        matches = [str(match) for match in payload.get("matches", []) if isinstance(match, str)]
        total_match_count = int(payload.get("total_match_count") or len(matches))
        candidate_file_count = int(payload.get("candidate_file_count") or 0)
        scanned_candidate_file_count = int(payload.get("scanned_candidate_file_count") or 0)
        scanned_file_count = int(payload.get("scanned_file_count") or 0)
        scanned_file_limit = int(payload.get("scanned_file_limit") or GREP_MAX_SCANNED_FILES)
        unscanned_file_count = int(payload.get("unscanned_file_count") or 0)
        scan_limit_reached = bool(payload.get("scan_limit_reached"))
        result_limit_reached = payload.get("next_offset") is not None
        scan_complete = bool(payload.get("scan_complete"))
        read_error_count = int(payload.get("read_error_count") or 0)
        visibility_error_count = int(payload.get("visibility_error_count") or 0)
        workspace_boundary_or_missing_count = int(payload.get("workspace_boundary_or_missing_count") or 0)
        backend_mismatch_detected = bool(payload.get("backend_mismatch_detected"))
        scan_complete_reason = str(payload.get("scan_complete_reason") or "unknown")
        root_kind = payload.get("root_kind")
        candidate_fact_source = payload.get("candidate_fact_source")
        candidate_count_reliable = payload.get("candidate_count_reliable")
        candidate_fact_error = payload.get("candidate_fact_error")
        result_kind = _grep_result_kind(
            current_page_match_count=len(matches),
            total_match_count=total_match_count,
            result_limit_reached=result_limit_reached,
            scan_complete=scan_complete,
        )
        reliable_empty_candidate_scan = (
            candidate_count_reliable is True
            and candidate_file_count == 0
            and scanned_candidate_file_count == 0
            and root_kind != "file"
        )
        empty_scan_no_match = (
            not matches
            and total_match_count == 0
            and reliable_empty_candidate_scan
        )
        if empty_scan_no_match:
            scan_complete = False
            scan_complete_reason = "no_model_visible_files_scanned"
            result_kind = "empty_scan_no_match"
        recovery_hint = None
        if not matches and mode == "literal" and _looks_like_regex(query):
            recovery_hint = "No literal matches. The query looks like a regular expression; retry with mode='regex'."
        if empty_scan_no_match:
            recovery_hint = (
                "grep found no model-visible candidate files for this root/glob, so this is not proof "
                "that the query is absent from the repository. Confirm the root or glob with list_files "
                "before retrying grep."
            )
        if scan_limit_reached and payload.get("next_offset") is None:
            recovery_hint = "Search reached the scanned-file limit; narrow root, glob, or query instead of paginating."
        recommended_next_calls = _grep_recommended_next_calls(
            query=query,
            mode=mode,
            root=root,
            glob=str(glob) if glob is not None else None,
            next_offset=payload.get("next_offset"),
            max_matches=max_matches,
            scan_limit_reached=scan_limit_reached,
            regex_hint=bool(not matches and mode == "literal" and _looks_like_regex(query)),
        )
        if empty_scan_no_match:
            recommended_next_calls = [
                {
                    "tool": "list_files",
                    "arguments": {"root": root, "max_entries": 50},
                    "reason": "Confirm which model-visible files exist under this root before treating the no-match as evidence.",
                },
                *recommended_next_calls,
            ]
        search_fact_fields = _search_fact_fields(
            context=context,
            root=root,
            search_backend=str(payload.get("search_backend") or "workspace_adapter_python_fallback"),
            scan_complete_reason=scan_complete_reason,
            read_error_count=read_error_count,
            read_error_samples=payload.get("read_error_samples") or [],
            visibility_error_count=visibility_error_count,
            visibility_error_samples=payload.get("visibility_error_samples") or [],
            backend_mismatch_detected=backend_mismatch_detected,
        )
        ref = context.recorder.write_json_artifact(
            "grep_results",
            {
                "query": query,
                "mode": mode,
                "output_mode": output_mode,
                "glob": glob,
                "matches": matches,
                "files_with_matches": payload.get("files_with_matches") or [],
                "page_files_with_matches": payload.get("page_files_with_matches") or [],
                "offset": offset,
                "max_matches": max_matches,
                "context_lines": context_lines,
                "result_kind": result_kind,
                "scan_complete": scan_complete,
                "scan_complete_reason": scan_complete_reason,
                "scan_limit_reached": scan_limit_reached,
                "result_limit_reached": result_limit_reached,
                "candidate_file_count": candidate_file_count,
                "scanned_candidate_file_count": scanned_candidate_file_count,
                "scanned_file_count": scanned_file_count,
                "root_kind": root_kind,
                "candidate_fact_source": candidate_fact_source,
                "candidate_count_reliable": candidate_count_reliable,
                "candidate_fact_error": candidate_fact_error,
                "scanned_file_limit": scanned_file_limit,
                "unscanned_file_count": unscanned_file_count,
                "hidden_path_count": int(payload.get("hidden_path_count") or 0),
                "skipped_hidden_path_count": int(payload.get("skipped_hidden_path_count") or 0),
                "skipped_hidden_count": int(payload.get("skipped_hidden_count") or 0),
                "symlink_outside_workspace_count": int(payload.get("symlink_outside_workspace_count") or 0),
                "skipped_symlink_count": int(payload.get("skipped_symlink_count") or 0),
                "workspace_boundary_or_missing_count": workspace_boundary_or_missing_count,
                "read_error_count": read_error_count,
                "read_error_samples": payload.get("read_error_samples") or [],
                "visibility_error_count": visibility_error_count,
                "visibility_error_samples": payload.get("visibility_error_samples") or [],
                "backend_mismatch_detected": backend_mismatch_detected,
                "matched_file_count": int(payload.get("matched_file_count") or 0),
                "total_match_count": total_match_count,
                "truncated": bool(result_limit_reached or not scan_complete),
                "next_offset": payload.get("next_offset"),
                "recommended_next_calls": recommended_next_calls,
                "engine": payload.get("engine"),
                "fallback_reason": payload.get("fallback_reason"),
                "execution_duration_ms": payload.get("execution_duration_ms"),
                "container_execution_facts_ref": payload.get("container_execution_facts_ref"),
                "rg_exit_code": payload.get("rg_exit_code"),
                "rg_timeout": payload.get("rg_timeout"),
                "rg_summary_stats": payload.get("rg_summary_stats"),
                "legacy_query_alias_used": legacy_query_alias_used,
                "canonical_query_source": "pattern" if legacy_query_alias_used else "query",
                "empty_scan": empty_scan_no_match,
                **search_fact_fields,
            },
        )
        if matches:
            preview = "\n".join(matches)
        elif result_kind == "page_empty_out_of_range":
            preview = (
                f"No matches on this result page: offset={offset} is outside the "
                f"{total_match_count} available match(es). This does not mean the query is absent. "
                "Retry with offset=0 or a smaller offset."
            )
        elif empty_scan_no_match:
            preview = (
                f"No model-visible candidate files were found under root={root!r}"
                + (f" with glob={str(glob)!r}" if glob is not None else "")
                + ". Do not conclude the query is absent from the repository. "
                "Confirm the root or glob with list_files before retrying grep."
            )
        elif not scan_complete:
            preview = (
                "No matches found in the trusted scanned subset, but the search is incomplete "
                f"(reason={scan_complete_reason}; scanned {scanned_candidate_file_count} candidate files "
                f"out of {candidate_file_count}). Do not conclude the query is absent. "
                "Narrow root, glob, or query and retry."
            )
        else:
            if root_kind == "file":
                preview = f"No matches found after searching file {root!r}."
            else:
                preview = (
                    f"No matches found after scanning all {scanned_file_count} model-visible files "
                    f"under root={root!r}."
                )
        if result_limit_reached:
            preview += (
                f"\n[truncated] call grep(query={query!r}, mode={mode!r}, "
                f"offset={payload.get('next_offset')}, max_matches={max_matches}) for more matches."
            )
        if not scan_complete and matches:
            preview += (
                f"\n[partial_scan] Search is incomplete (reason={scan_complete_reason}) after "
                f"scanning {scanned_candidate_file_count} candidate files out of {candidate_file_count}; "
                "narrow root, glob, or query and retry if needed."
            )
        elif recovery_hint:
            preview += f"\n{recovery_hint}"
        if legacy_query_alias_used:
            preview = (
                "[tool input normalized] grep(pattern=...) was accepted as a legacy alias "
                "for grep(query=...). Use query in future grep calls.\n"
                + preview
            )
        output_truncated = len(preview) > context.output_limits.max_tool_output_chars
        content_preview = _preview(preview, context.output_limits.max_tool_output_chars)
        recovery_call, envelope_recovery_hint = _tool_recovery_call(
            tool_name="grep",
            arguments=normalized.normalized_arguments,
            typed={
                "query": query,
                "mode": mode,
                "next_offset": payload.get("next_offset"),
            },
        )
        if not (result_limit_reached or not scan_complete or output_truncated):
            recovery_call = None
            envelope_recovery_hint = recovery_hint
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=content_preview,
            truncated=output_truncated,
            artifact_refs=[ref],
            typed={
                "query": query,
                "mode": mode,
                "output_mode": output_mode,
                "glob": glob,
                "result_kind": result_kind,
                "match_count": len(matches),
                "total_match_count": total_match_count,
                "scan_complete": scan_complete,
                "scan_complete_reason": scan_complete_reason,
                "scan_limit_reached": scan_limit_reached,
                "result_limit_reached": result_limit_reached,
                "output_truncated": output_truncated,
                "candidate_file_count": candidate_file_count,
                "scanned_candidate_file_count": scanned_candidate_file_count,
                "scanned_file_count": scanned_file_count,
                "root_kind": root_kind,
                "candidate_fact_source": candidate_fact_source,
                "candidate_count_reliable": candidate_count_reliable,
                "candidate_fact_error": candidate_fact_error,
                "scanned_file_limit": scanned_file_limit,
                "unscanned_file_count": unscanned_file_count,
                "hidden_path_count": int(payload.get("hidden_path_count") or 0),
                "skipped_hidden_path_count": int(payload.get("skipped_hidden_path_count") or 0),
                "skipped_hidden_count": int(payload.get("skipped_hidden_count") or 0),
                "symlink_outside_workspace_count": int(payload.get("symlink_outside_workspace_count") or 0),
                "skipped_symlink_count": int(payload.get("skipped_symlink_count") or 0),
                "workspace_boundary_or_missing_count": workspace_boundary_or_missing_count,
                "read_error_count": read_error_count,
                "read_error_samples": payload.get("read_error_samples") or [],
                "visibility_error_count": visibility_error_count,
                "visibility_error_samples": payload.get("visibility_error_samples") or [],
                "backend_mismatch_detected": backend_mismatch_detected,
                "matched_file_count": int(payload.get("matched_file_count") or 0),
                "files_with_matches": payload.get("files_with_matches") or [],
                "page_files_with_matches": payload.get("page_files_with_matches") or [],
                "truncated": bool(result_limit_reached or not scan_complete),
                "next_offset": payload.get("next_offset"),
                "offset": offset,
                "max_matches": max_matches,
                "context_lines": context_lines,
                "recovery_hint": recovery_hint,
                "recommended_next_calls": recommended_next_calls,
                "legacy_query_alias_used": legacy_query_alias_used,
                "canonical_query_source": "pattern" if legacy_query_alias_used else "query",
                "empty_scan": empty_scan_no_match,
                "engine": payload.get("engine"),
                "fallback_reason": payload.get("fallback_reason"),
                "execution_duration_ms": payload.get("execution_duration_ms"),
                "container_execution_facts_ref": payload.get("container_execution_facts_ref"),
                "rg_exit_code": payload.get("rg_exit_code"),
                "rg_timeout": payload.get("rg_timeout"),
                "rg_summary_stats": payload.get("rg_summary_stats"),
                **search_fact_fields,
                "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                "result_envelope": _result_envelope(
                    result_kind=result_kind,
                    semantic_complete=scan_complete and not result_limit_reached,
                    model_visible_text_truncated=output_truncated,
                    result_limit_reached=result_limit_reached,
                    artifact_backed_full_result=True,
                    recommended_next_calls=recommended_next_calls,
                    recovery_call=recovery_call,
                    recovery_hint=envelope_recovery_hint,
                    context_effects=["tool_result_recoverable"],
                ),
            },
        )

    def _symbol_search(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        started_at = time.monotonic()
        query = str(normalized.normalized_arguments["query"])
        root = str(normalized.normalized_arguments["root"])
        symbol_kind = str(normalized.normalized_arguments.get("symbol_kind", "any"))
        offset = max(0, int(normalized.normalized_arguments.get("offset", 0)))
        max_results = max(1, min(int(normalized.normalized_arguments.get("max_results", 20)), 100))
        context.workspace_adapter.resolve_workspace_path(
            context.run_workspace.workspace_path,
            root,
            must_exist=True,
        )
        python_files = context.workspace_adapter.list_files(
            context.run_workspace.workspace_path,
            root,
            pattern="*.py",
        )
        candidate_file_count = len(python_files)
        backend_mismatch_detected = _backend_mismatch_detected(context)
        if (
            _is_wide_symbol_root(root)
            and candidate_file_count > SYMBOL_SEARCH_WIDE_ROOT_CANDIDATE_FILE_THRESHOLD
        ):
            return self._symbol_search_wide_root_guard_result(
                tool_call=tool_call,
                normalized=normalized,
                context=context,
                query=query,
                root=root,
                symbol_kind=symbol_kind,
                offset=offset,
                max_results=max_results,
                candidate_file_count=candidate_file_count,
                python_files=python_files,
                backend_mismatch_detected=backend_mismatch_detected,
                started_at=started_at,
            )
        symbols: list[dict[str, Any]] = []
        hidden_path_count = 0
        symlink_outside_workspace_count = 0
        workspace_boundary_or_missing_count = 0
        visibility_error_count = 0
        visibility_error_samples: list[dict[str, str]] = []
        read_error_count = 0
        read_error_samples: list[dict[str, str]] = []
        parse_error_count = 0
        parse_error_samples: list[dict[str, str]] = []
        scanned_file_count = 0
        cache_hit_file_count = 0
        cache_miss_file_count = 0
        for rel_path in python_files:
            visible, reason = _model_visible_path_status(context, rel_path)
            if not visible:
                if reason in {"hidden_path", "symlink_target_hidden_path"}:
                    hidden_path_count += 1
                elif reason == "symlink_outside_workspace":
                    symlink_outside_workspace_count += 1
                elif reason == "workspace_boundary_or_missing":
                    workspace_boundary_or_missing_count += 1
                else:
                    visibility_error_count += 1
                    if len(visibility_error_samples) < 5:
                        visibility_error_samples.append({"path": rel_path, "reason": reason or "visibility_error"})
                continue
            try:
                source = context.workspace_adapter.read_text(context.run_workspace.workspace_path, rel_path)
            except WorkspaceError as exc:
                read_error_count += 1
                if len(read_error_samples) < 5:
                    read_error_samples.append({"path": rel_path, "error": str(exc)[:300]})
                continue
            scanned_file_count += 1
            source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
            cache_key = (rel_path, source_hash)
            cached = self._symbol_index_cache.get(cache_key)
            if cached is None:
                cache_miss_file_count += 1
                cached = index_python_symbols(path=rel_path, source=source)
                self._symbol_index_cache[cache_key] = cached
            else:
                cache_hit_file_count += 1
            file_symbols, parse_error = cached
            if parse_error is not None:
                parse_error_count += 1
                if len(parse_error_samples) < 5:
                    parse_error_samples.append({"path": rel_path, "error": parse_error[:300]})
                continue
            symbols.extend(file_symbols)
        matches = filter_symbols(symbols, query=query, symbol_kind=symbol_kind)
        total_match_count = len(matches)
        page = matches[offset : offset + max_results]
        next_offset = offset + len(page) if offset + len(page) < total_match_count else None
        result_limit_reached = next_offset is not None
        scan_complete = (
            read_error_count == 0
            and parse_error_count == 0
            and visibility_error_count == 0
            and workspace_boundary_or_missing_count == 0
            and not backend_mismatch_detected
        )
        if parse_error_count:
            scan_complete_reason = "parse_error_detected"
        else:
            scan_complete_reason = _scan_complete_reason(
                scan_complete=scan_complete,
                result_limit_reached=result_limit_reached,
                scan_limit_reached=False,
                read_error_count=read_error_count,
                visibility_error_count=visibility_error_count,
                workspace_boundary_or_missing_count=workspace_boundary_or_missing_count,
                backend_mismatch_detected=backend_mismatch_detected,
                total_match_count=total_match_count,
            )
        if not scan_complete:
            result_kind = "partial_symbol_results"
        elif result_limit_reached:
            result_kind = "result_page_truncated"
        elif total_match_count:
            result_kind = "symbols_found"
        else:
            result_kind = "complete_no_symbol_match"
        recommended_next_calls: list[dict[str, Any]] = []
        if next_offset is not None:
            recommended_next_calls.append(
                {
                    "tool": "symbol_search",
                    "arguments": {
                        "query": query,
                        "root": root,
                        "symbol_kind": symbol_kind,
                        "offset": next_offset,
                        "max_results": max_results,
                    },
                    "reason": "More symbol results are available through result pagination.",
                }
            )
        if not scan_complete:
            recommended_next_calls.append(
                {
                    "tool": "grep",
                    "arguments": {"query": query, "root": root, "glob": "*.py", "output_mode": "files_with_matches"},
                    "reason": "AST symbol search was partial; use grep to cross-check text-level matches.",
                }
            )
        search_fact_fields = _search_fact_fields(
            context=context,
            root=root,
            search_backend="python_ast_symbol_index",
            scan_complete_reason=scan_complete_reason,
            read_error_count=read_error_count,
            read_error_samples=read_error_samples,
            visibility_error_count=visibility_error_count,
            visibility_error_samples=visibility_error_samples,
            backend_mismatch_detected=backend_mismatch_detected,
        )
        duration_ms = int((time.monotonic() - started_at) * 1000)
        slow_scan = duration_ms > SYMBOL_SEARCH_SLOW_SCAN_THRESHOLD_MS
        semantic_complete = scan_complete and not result_limit_reached
        ref = context.recorder.write_json_artifact(
            "symbol_search_results",
            {
                "query": query,
                "root": root,
                "symbol_kind": symbol_kind,
                "result_kind": result_kind,
                "symbols": matches,
                "returned_symbols": page,
                "offset": offset,
                "max_results": max_results,
                "total_match_count": total_match_count,
                "scanned_file_count": scanned_file_count,
                "candidate_file_count": candidate_file_count,
                "wide_root_candidate_file_threshold": SYMBOL_SEARCH_WIDE_ROOT_CANDIDATE_FILE_THRESHOLD,
                "scan_complete": scan_complete,
                "scan_complete_reason": scan_complete_reason,
                "semantic_complete": semantic_complete,
                "cache_hit_file_count": cache_hit_file_count,
                "cache_miss_file_count": cache_miss_file_count,
                "slow_scan": slow_scan,
                "slow_scan_threshold_ms": SYMBOL_SEARCH_SLOW_SCAN_THRESHOLD_MS,
                "duration_ms": duration_ms,
                "execution_duration_ms": duration_ms,
                "recommended_narrow_roots": [],
                "parse_error_count": parse_error_count,
                "parse_error_samples": parse_error_samples,
                "read_error_count": read_error_count,
                "read_error_samples": read_error_samples,
                "visibility_error_count": visibility_error_count,
                "visibility_error_samples": visibility_error_samples,
                "hidden_path_count": hidden_path_count,
                "skipped_hidden_count": hidden_path_count,
                "symlink_outside_workspace_count": symlink_outside_workspace_count,
                "skipped_symlink_count": symlink_outside_workspace_count,
                "workspace_boundary_or_missing_count": workspace_boundary_or_missing_count,
                "backend_mismatch_detected": backend_mismatch_detected,
                "next_offset": next_offset,
                "recommended_next_calls": recommended_next_calls,
                "symbol_index_policy_version": SYMBOL_INDEX_POLICY_VERSION,
                **search_fact_fields,
            },
        )
        if page:
            lines = [
                (
                    f"{symbol['path']}:{symbol['line']}:"
                    f"{symbol['symbol_kind']} {symbol['qualified_name']}"
                )
                for symbol in page
            ]
            preview = "\n".join(lines)
        elif scan_complete:
            preview = f"No Python symbols matched query={query!r} under root={root!r}."
        else:
            preview = (
                f"No symbol matches in the parsed subset, but symbol search is incomplete "
                f"(reason={scan_complete_reason}). Cross-check with grep."
            )
        if result_limit_reached:
            preview += (
                f"\n[truncated] call symbol_search(query={query!r}, root={root!r}, "
                f"symbol_kind={symbol_kind!r}, offset={next_offset}, max_results={max_results}) for more symbols."
            )
        if not scan_complete and page:
            preview += (
                f"\n[partial_symbol_results] AST parsing was incomplete "
                f"(reason={scan_complete_reason}); cross-check with grep if needed."
            )
        output_truncated = len(preview) > context.output_limits.max_tool_output_chars
        recovery_call = (
            f"symbol_search(query={query!r}, root={root!r}, symbol_kind={symbol_kind!r}, "
            f"offset={next_offset}, max_results={max_results})"
            if next_offset is not None
            else None
        )
        recovery_hint = (
            "Use next_offset to continue symbol pagination."
            if next_offset is not None
            else (
                "AST symbol search was partial; use grep to cross-check text-level matches."
                if not scan_complete
                else None
            )
        )
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(preview, context.output_limits.max_tool_output_chars),
            truncated=output_truncated,
            artifact_refs=[ref],
            typed={
                "query": query,
                "root": root,
                "symbol_kind": symbol_kind,
                "symbols": page,
                "returned_count": len(page),
                "total_match_count": total_match_count,
                "offset": offset,
                "max_results": max_results,
                "result_kind": result_kind,
                "scan_complete": scan_complete,
                "scan_complete_reason": scan_complete_reason,
                "semantic_complete": semantic_complete,
                "result_limit_reached": result_limit_reached,
                "output_truncated": output_truncated,
                "next_offset": next_offset,
                "scanned_file_count": scanned_file_count,
                "candidate_file_count": candidate_file_count,
                "wide_root_candidate_file_threshold": SYMBOL_SEARCH_WIDE_ROOT_CANDIDATE_FILE_THRESHOLD,
                "cache_hit_file_count": cache_hit_file_count,
                "cache_miss_file_count": cache_miss_file_count,
                "slow_scan": slow_scan,
                "slow_scan_threshold_ms": SYMBOL_SEARCH_SLOW_SCAN_THRESHOLD_MS,
                "duration_ms": duration_ms,
                "execution_duration_ms": duration_ms,
                "recommended_narrow_roots": [],
                "parse_error_count": parse_error_count,
                "parse_error_samples": parse_error_samples,
                "read_error_count": read_error_count,
                "read_error_samples": read_error_samples,
                "visibility_error_count": visibility_error_count,
                "visibility_error_samples": visibility_error_samples,
                "hidden_path_count": hidden_path_count,
                "skipped_hidden_count": hidden_path_count,
                "symlink_outside_workspace_count": symlink_outside_workspace_count,
                "skipped_symlink_count": symlink_outside_workspace_count,
                "workspace_boundary_or_missing_count": workspace_boundary_or_missing_count,
                "backend_mismatch_detected": backend_mismatch_detected,
                "recommended_next_calls": recommended_next_calls,
                "symbol_index_policy_version": SYMBOL_INDEX_POLICY_VERSION,
                **search_fact_fields,
                "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                "result_envelope": _result_envelope(
                    result_kind=result_kind,
                    semantic_complete=semantic_complete,
                    model_visible_text_truncated=output_truncated,
                    result_limit_reached=result_limit_reached,
                    artifact_backed_full_result=True,
                    recommended_next_calls=recommended_next_calls,
                    recovery_call=recovery_call,
                    recovery_hint=recovery_hint,
                    context_effects=["tool_result_recoverable"],
                ),
            },
        )

    def _symbol_search_wide_root_guard_result(
        self,
        *,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
        query: str,
        root: str,
        symbol_kind: str,
        offset: int,
        max_results: int,
        candidate_file_count: int,
        python_files: list[str],
        backend_mismatch_detected: bool,
        started_at: float,
    ) -> ToolResult:
        recommended_narrow_roots = _recommended_symbol_search_roots(python_files)
        recommended_next_calls = [
            {
                "tool": "symbol_search",
                "arguments": {
                    "query": query,
                    "root": narrow_root,
                    "symbol_kind": symbol_kind,
                    "offset": 0,
                    "max_results": max_results,
                },
                "reason": (
                    "Narrow symbol_search to a likely source package or directory before using root='.'."
                ),
            }
            for narrow_root in recommended_narrow_roots[:3]
        ]
        recovery_call = (
            f"symbol_search(query={query!r}, root={recommended_narrow_roots[0]!r}, "
            f"symbol_kind={symbol_kind!r}, offset=0, max_results={max_results})"
            if recommended_narrow_roots
            else f"symbol_search(query={query!r}, root='<narrow-source-dir>', symbol_kind={symbol_kind!r})"
        )
        recovery_hint = (
            "Wide root symbol search was not executed because it would scan too many Python files. "
            "Choose a narrower root from recommended_narrow_roots or repository_hints."
        )
        scan_complete_reason = "wide_root_candidate_file_limit"
        result_kind = "scan_requires_narrow_root"
        duration_ms = int((time.monotonic() - started_at) * 1000)
        search_fact_fields = _search_fact_fields(
            context=context,
            root=root,
            search_backend="python_ast_symbol_index",
            scan_complete_reason=scan_complete_reason,
            read_error_count=0,
            read_error_samples=[],
            visibility_error_count=0,
            visibility_error_samples=[],
            backend_mismatch_detected=backend_mismatch_detected,
        )
        payload = {
            "query": query,
            "root": root,
            "symbol_kind": symbol_kind,
            "result_kind": result_kind,
            "symbols": [],
            "returned_symbols": [],
            "offset": offset,
            "max_results": max_results,
            "total_match_count": 0,
            "returned_count": 0,
            "scanned_file_count": 0,
            "candidate_file_count": candidate_file_count,
            "wide_root_candidate_file_threshold": SYMBOL_SEARCH_WIDE_ROOT_CANDIDATE_FILE_THRESHOLD,
            "scan_complete": False,
            "scan_complete_reason": scan_complete_reason,
            "semantic_complete": False,
            "parse_error_count": 0,
            "parse_error_samples": [],
            "read_error_count": 0,
            "read_error_samples": [],
            "visibility_error_count": 0,
            "visibility_error_samples": [],
            "hidden_path_count": 0,
            "skipped_hidden_count": 0,
            "symlink_outside_workspace_count": 0,
            "skipped_symlink_count": 0,
            "workspace_boundary_or_missing_count": 0,
            "backend_mismatch_detected": backend_mismatch_detected,
            "next_offset": None,
            "recommended_narrow_roots": recommended_narrow_roots,
            "recommended_next_calls": recommended_next_calls,
            "cache_hit_file_count": 0,
            "cache_miss_file_count": 0,
            "slow_scan": False,
            "slow_scan_threshold_ms": SYMBOL_SEARCH_SLOW_SCAN_THRESHOLD_MS,
            "duration_ms": duration_ms,
            "execution_duration_ms": duration_ms,
            "symbol_index_policy_version": SYMBOL_INDEX_POLICY_VERSION,
            **search_fact_fields,
        }
        ref = context.recorder.write_json_artifact("symbol_search_results", payload)
        root_preview = ", ".join(recommended_narrow_roots[:5]) or "<narrow-source-dir>"
        preview = (
            f"symbol_search(query={query!r}, root={root!r}) was not executed as a full AST scan: "
            f"{candidate_file_count} Python files exceed the wide-root threshold "
            f"{SYMBOL_SEARCH_WIDE_ROOT_CANDIDATE_FILE_THRESHOLD}. "
            f"Retry with a narrower root such as {root_preview}."
        )
        output_truncated = len(preview) > context.output_limits.max_tool_output_chars
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(preview, context.output_limits.max_tool_output_chars),
            truncated=output_truncated,
            artifact_refs=[ref],
            typed={
                **payload,
                "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                "result_envelope": _result_envelope(
                    result_kind=result_kind,
                    semantic_complete=False,
                    model_visible_text_truncated=output_truncated,
                    result_limit_reached=False,
                    artifact_backed_full_result=True,
                    recommended_next_calls=recommended_next_calls,
                    recovery_call=recovery_call,
                    recovery_hint=recovery_hint,
                    context_effects=["tool_result_recoverable"],
                ),
            },
        )

    def _update_working_state(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        current_hypothesis = _bounded_string(
            normalized.normalized_arguments.get("current_hypothesis"),
            max_chars=800,
        )
        candidate_files, skipped_candidate_file_count = _candidate_file_list(
            normalized.normalized_arguments.get("candidate_files"),
            max_items=20,
            max_chars=240,
        )
        next_action = _bounded_string(
            normalized.normalized_arguments.get("next_action"),
            max_chars=500,
        )
        completed_steps = _bounded_string_list(
            normalized.normalized_arguments.get("completed_steps"),
            max_items=20,
            max_chars=300,
        )
        blocking_question = _bounded_string(
            normalized.normalized_arguments.get("blocking_question"),
            max_chars=500,
        )
        if not any([current_hypothesis, candidate_files, next_action, completed_steps, blocking_question]):
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=(
                    "working_state_empty: provide at least one of current_hypothesis, "
                    "candidate_files, next_action, completed_steps, or blocking_question."
                ),
                error_type="working_state_empty",
                typed={
                    "result_envelope": _result_envelope(
                        result_kind="working_state_empty",
                        semantic_complete=True,
                        recovery_call="update_working_state(next_action='...')",
                        recovery_hint="Record the current hypothesis or next concrete action before continuing.",
                    ),
                },
            )
        working_state = {
            "schema_version": "repo_harness_working_state_v0",
            "current_hypothesis": current_hypothesis,
            "candidate_files": candidate_files,
            "next_action": next_action,
            "completed_steps": completed_steps,
            "blocking_question": blocking_question,
            "skipped_candidate_file_count": skipped_candidate_file_count,
            "policy_version": "repo_harness_update_working_state_v0",
        }
        context.working_state = working_state
        ref = context.recorder.write_json_artifact(
            "working_state_update",
            {
                "tool_call_id": tool_call.tool_call_id,
                "working_state": working_state,
            },
            {"budget_policy": "preserve_json"},
        )
        preview = {
            "working_state_updated": True,
            "current_hypothesis": current_hypothesis,
            "candidate_files": candidate_files,
            "next_action": next_action,
            "completed_step_count": len(completed_steps),
            "blocking_question": blocking_question,
        }
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(
                json.dumps(preview, ensure_ascii=False, sort_keys=True),
                context.output_limits.max_tool_output_chars,
            ),
            artifact_refs=[ref],
            typed={
                "working_state": working_state,
                "working_state_ref": ref.model_dump(mode="json"),
                "policy_version": "repo_harness_update_working_state_v0",
                "trainable": False,
                "resolved_trainable": False,
                "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                "result_envelope": _result_envelope(
                    result_kind="working_state_updated",
                    semantic_complete=True,
                    artifact_backed_full_result=True,
                    context_effects=["working_state_updated"],
                ),
            },
        )

    def _edit_file(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        path = str(normalized.normalized_arguments["path"])
        old_text = str(normalized.normalized_arguments["old_text"])
        new_text = str(normalized.normalized_arguments["new_text"])
        replace_all = bool(normalized.normalized_arguments.get("replace_all", False))
        content = context.workspace_adapter.read_text(context.run_workspace.workspace_path, path)
        expected_hash = normalized.normalized_arguments.get("expected_content_hash")
        current_hash = _sha256_text(content)
        if expected_hash is not None and expected_hash != current_hash:
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=(
                    "expected_content_hash does not match current file content. "
                    "Re-run read_file on this path and retry with the new content_hash."
                ),
                error_type="stale_file_state",
                typed={
                    "path": path,
                    "expected_content_hash": expected_hash,
                    "current_content_hash": current_hash,
                    "policy_version": context.tool_policy.tool_policy_version,
                    "require_read_before_edit": context.tool_policy.require_read_before_edit,
                    "recovery_hint": "Call read_file again, copy the raw_content_preview without line numbers, then retry edit_file.",
                    "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                    "result_envelope": _result_envelope(
                        result_kind="stale_file_state",
                        semantic_complete=True,
                        recovery_call=f"read_file(path={path!r})",
                        recovery_hint="Call read_file again, then retry edit_file with the new content_hash.",
                    ),
                },
            )
        cached_hash = context.file_state_cache.get(path)
        if context.tool_policy.require_read_before_edit and expected_hash is None:
            if cached_hash is None:
                return _tool_result(
                    tool_call,
                    normalized=normalized,
                    status="error",
                    content=(
                        "read_before_edit_required: call read_file on this path before edit_file, "
                        "or pass expected_content_hash from a recent read_file result."
                    ),
                    error_type="read_before_edit_required",
                    typed={
                        "path": path,
                        "policy_version": context.tool_policy.tool_policy_version,
                        "require_read_before_edit": True,
                        "recovery_hint": "Call read_file(path=...) and retry edit_file with the returned content_hash.",
                        "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                        "result_envelope": _result_envelope(
                            result_kind="read_before_edit_required",
                            semantic_complete=True,
                            recovery_call=f"read_file(path={path!r})",
                            recovery_hint="Call read_file on this path before retrying edit_file.",
                        ),
                    },
                )
            if cached_hash != current_hash:
                return _tool_result(
                    tool_call,
                    normalized=normalized,
                    status="error",
                    content=(
                        "stale_file_state: the file changed after it was last read. "
                        "Re-run read_file and retry edit_file with the refreshed content hash."
                    ),
                    error_type="stale_file_state",
                    typed={
                        "path": path,
                        "cached_content_hash": cached_hash,
                        "current_content_hash": current_hash,
                        "policy_version": context.tool_policy.tool_policy_version,
                        "require_read_before_edit": True,
                        "recovery_hint": "Call read_file again, then retry edit_file with the new content_hash.",
                        "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                        "result_envelope": _result_envelope(
                            result_kind="stale_file_state",
                            semantic_complete=True,
                            recovery_call=f"read_file(path={path!r})",
                            recovery_hint="Call read_file again, then retry edit_file with the new content_hash.",
                        ),
                    },
                )
        if _looks_like_numbered_read_file_snippet(old_text):
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=(
                    "old_text appears to include read_file line-number prefixes like '42 | '. "
                    "Use the raw_content_preview text without line numbers."
                ),
                error_type="line_number_prefix_in_old_text",
                typed={
                    "path": path,
                    "recovery_hint": "Re-read the file and copy old_text from raw_content_preview, not numbered_content_preview.",
                    "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                    "result_envelope": _result_envelope(
                        result_kind="line_number_prefix_in_old_text",
                        semantic_complete=True,
                        recovery_call=f"read_file(path={path!r})",
                        recovery_hint="Copy old_text from raw_content_preview, not numbered_content_preview.",
                    ),
                },
            )
        count = content.count(old_text)
        if count == 0 or (count > 1 and not replace_all):
            error_type = "old_text_not_found" if count == 0 else "ambiguous_old_text"
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=(
                    f"old_text matched {count} times; expected exactly 1 unless replace_all=true. "
                    "Read a larger surrounding snippet and include enough unique context."
                ),
                error_type=error_type,
                typed={
                    "path": path,
                    "match_count": count,
                    "replace_all": replace_all,
                    "recovery_hint": "Use read_file with a wider line range and include surrounding lines so old_text is unique.",
                    "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                    "result_envelope": _result_envelope(
                        result_kind=error_type,
                        semantic_complete=True,
                        recovery_call=f"read_file(path={path!r})",
                        recovery_hint="Use read_file with a wider line range and include enough surrounding raw text for a unique edit.",
                    ),
                },
            )
        updated = content.replace(old_text, new_text) if replace_all else content.replace(old_text, new_text, 1)
        context.workspace_adapter.write_text(context.run_workspace.workspace_path, path, updated)
        updated_hash = _sha256_text(updated)
        context.file_state_cache[path] = updated_hash
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=f"Edited {path}.",
            typed={
                "path": path,
                "replacement_count": count if replace_all else 1,
                "content_hash": updated_hash,
                "content_sha256": updated_hash,
                "policy_version": context.tool_policy.tool_policy_version,
                "require_read_before_edit": context.tool_policy.require_read_before_edit,
                "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                "result_envelope": _result_envelope(
                    result_kind="edit_applied",
                    semantic_complete=True,
                    context_effects=["repository_file_state_updated"],
                ),
            },
        )

    def _create_file(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        path = str(normalized.normalized_arguments["path"])
        target = context.workspace_adapter.resolve_workspace_path(
            context.run_workspace.workspace_path,
            path,
        )
        if target.exists():
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=f"File already exists: {path}",
                error_type="file_exists",
            )
        content = str(normalized.normalized_arguments["content"])
        context.workspace_adapter.write_text(context.run_workspace.workspace_path, path, content)
        content_hash = _sha256_text(content)
        context.file_state_cache[path] = content_hash
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=f"Created {path}.",
            typed={
                "path": path,
                "content_hash": content_hash,
                "content_sha256": content_hash,
                "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
            },
        )

    def _bash(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        command = str(normalized.normalized_arguments["command"])
        cwd = _resolve_cwd(context, str(normalized.normalized_arguments["cwd"]))
        safe_argv = normalized.normalized_arguments.get("safe_argv")
        if not isinstance(safe_argv, list) or not all(isinstance(part, str) for part in safe_argv):
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content="bash command missing policy safe_argv; command was not executed.",
                error_type="bash_safe_argv_missing",
                typed={
                    "command": command,
                    "policy_decision": normalized.normalized_arguments.get("policy_decision"),
                    "command_category": normalized.normalized_arguments.get("command_category"),
                    "safe_argv": None,
                    "shell_execution": False,
                    "timeout_sec": normalized.normalized_arguments.get("timeout_sec"),
                },
            )
        result = context.workspace_adapter.run_command(
            cwd,
            safe_argv,
            timeout_sec=float(normalized.normalized_arguments["timeout_sec"]),
            recorder=context.recorder,
            command_semantics="bash_diagnostic",
            artifact_metadata={
                "policy_decision": normalized.normalized_arguments.get("policy_decision"),
                "command_category": normalized.normalized_arguments.get("command_category"),
                "reason_code": normalized.normalized_arguments.get("reason_code"),
                "safe_argv": safe_argv,
                "timeout_sec": normalized.normalized_arguments["timeout_sec"],
                "shell_execution": False,
            },
        )
        status = "timeout" if result.timeout else "ok"
        return _tool_result(
            tool_call,
            normalized=normalized,
            status=status,
            content=_preview(
                _command_preview(result.stdout_preview, result.stderr_preview),
                context.output_limits.max_tool_output_chars,
            ),
            error_type="command_timeout" if result.timeout else None,
            artifact_refs=[result.output_artifact_ref] if result.output_artifact_ref else [],
            typed={
                "stdout_preview": result.stdout_preview,
                "stderr_preview": result.stderr_preview,
                "exit_code": result.exit_code,
                "command_semantics": result.command_semantics,
                "exit_code_interpretation": result.exit_code_interpretation,
                "policy_decision": normalized.normalized_arguments.get("policy_decision"),
                "command_category": normalized.normalized_arguments.get("command_category"),
                "reason_code": normalized.normalized_arguments.get("reason_code"),
                "recovery_hint": normalized.normalized_arguments.get("recovery_hint"),
                "safe_argv": safe_argv,
                "timeout_sec": normalized.normalized_arguments["timeout_sec"],
                "shell_execution": False,
            },
        )

    def _run_tests(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        if context.test_feedback_policy == "disabled":
            return self.disabled_test_feedback_result(tool_call, normalized)
        hidden_feedback_ran = context.test_feedback_policy == "oracle_hidden_feedback"
        if hidden_feedback_ran:
            result = context.verifier.run_feedback(
                context.run_workspace.workspace_path,
                context.resolved_verifier_plan,
                context.recorder,
            )
        else:
            result = context.verifier.run_feedback_public(
                context.run_workspace.workspace_path,
                context.resolved_verifier_plan,
                context.recorder,
            )
        ref = context.recorder.write_json_artifact(
            "feedback_verifier_result",
            result.model_dump(mode="json"),
        )
        timed_out = bool(result.timeout)
        if hidden_feedback_ran:
            content = (
                f"run_tests accepted={result.accepted} pass_ratio={result.pass_ratio:.2f} "
                f"fail_to_pass={result.fail_to_pass} pass_to_pass={result.pass_to_pass}"
            )
            preview = {
                "accepted": result.accepted,
                "pass_ratio": result.pass_ratio,
                "error_type": result.error_type,
                "fail_to_pass": result.fail_to_pass,
                "pass_to_pass": result.pass_to_pass,
            }
        elif context.test_feedback_policy == "structured_public_feedback":
            content = (
                "run_tests public_feedback="
                + json.dumps(
                    {
                        "accepted": result.accepted,
                        "pass_ratio": round(result.pass_ratio, 4),
                        "error_type": result.error_type,
                    },
                    sort_keys=True,
                )
            )
            preview = {
                "accepted": result.accepted,
                "pass_ratio": result.pass_ratio,
                "error_type": result.error_type,
            }
        else:
            status = "accepted" if result.accepted else "failed"
            content = (
                f"run_tests public_status={status} pass_ratio={result.pass_ratio:.2f} "
                f"error_type={result.error_type or 'none'}"
            )
            preview = {
                "accepted": result.accepted,
                "pass_ratio": result.pass_ratio,
                "error_type": result.error_type,
            }
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="timeout" if timed_out else "ok",
            content=content,
            error_type="test_timeout" if timed_out else None,
            artifact_refs=[ref],
            typed={
                "verifier_result_preview": preview,
                "verifier_result_ref": ref.model_dump(mode="json"),
                "test_feedback_policy": context.test_feedback_policy,
                "feedback_tests_passed_policy": context.feedback_tests_passed_policy,
                "public_tests_ran": not hidden_feedback_ran,
                "hidden_feedback_ran": hidden_feedback_ran,
            },
        )

    def _git_diff(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        path = normalized.normalized_arguments.get("path")
        command = ["git", "diff", "HEAD"]
        numstat_command = ["git", "diff", "--numstat", "HEAD"]
        name_status_command = ["git", "diff", "--name-status", "HEAD"]
        untracked_command = ["git", "ls-files", "--others", "--exclude-standard"]
        if path is not None:
            context.workspace_adapter.resolve_workspace_path(
                context.run_workspace.workspace_path,
                str(path),
                must_exist=False,
            )
            command.extend(["--", str(path)])
            numstat_command.extend(["--", str(path)])
            name_status_command.extend(["--", str(path)])
            untracked_command.extend(["--", str(path)])
        result = context.workspace_adapter.run_command(
            context.run_workspace.workspace_path,
            command,
            recorder=context.recorder,
            command_semantics="git_diff",
        )
        numstat_result = context.workspace_adapter.run_command(
            context.run_workspace.workspace_path,
            numstat_command,
            recorder=context.recorder,
            command_semantics="git_diff_summary",
        )
        name_status_result = context.workspace_adapter.run_command(
            context.run_workspace.workspace_path,
            name_status_command,
            recorder=context.recorder,
            command_semantics="git_diff_summary",
        )
        untracked_result = context.workspace_adapter.run_command(
            context.run_workspace.workspace_path,
            untracked_command,
            recorder=context.recorder,
            command_semantics="git_diff_summary",
        )
        tracked_diff_text = _command_stdout_from_artifact(context, result) or result.stdout_preview
        untracked_files = _visible_untracked_files(
            context,
            _command_stdout_from_artifact(context, untracked_result) or untracked_result.stdout_preview,
        )
        untracked_diff_text = _synthetic_untracked_diff(context, untracked_files)
        diff_text = _join_diff_sections(tracked_diff_text, untracked_diff_text)
        truncated = diff_text.endswith("\n[truncated]") or len(diff_text) > context.output_limits.max_tool_output_chars
        changed_files = _parse_changed_files(
            _command_stdout_from_artifact(context, name_status_result) or name_status_result.stdout_preview,
            _command_stdout_from_artifact(context, numstat_result) or numstat_result.stdout_preview,
        )
        changed_files.extend(_untracked_changed_files(context, untracked_files))
        recovery_hint = None
        if truncated:
            recovery_hint = "Diff output was truncated; call git_diff(path='relative/path.py') for one changed file."
        elif changed_files:
            recovery_hint = "Use git_diff(path='relative/path') to inspect a single changed file if needed."
        recovery_call, envelope_recovery_hint = _tool_recovery_call(
            tool_name="git_diff",
            arguments=normalized.normalized_arguments,
            typed={"changed_files": changed_files[:GIT_DIFF_CHANGED_FILE_LIMIT]},
        )
        if not (truncated or changed_files):
            recovery_call = None
            envelope_recovery_hint = None
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(diff_text or "No diff.", context.output_limits.max_tool_output_chars),
            artifact_refs=[
                ref
                for ref in [
                    result.output_artifact_ref,
                    numstat_result.output_artifact_ref,
                    name_status_result.output_artifact_ref,
                    untracked_result.output_artifact_ref,
                ]
                if ref is not None
            ],
            typed={
                "diff_preview": diff_text,
                "diff_sha256": _sha256_text(diff_text),
                "changed_files": changed_files[:GIT_DIFF_CHANGED_FILE_LIMIT],
                "changed_file_count": len(changed_files),
                "untracked_files": untracked_files,
                "path": path,
                "exit_code": result.exit_code,
                "truncated": truncated,
                "recovery_hint": recovery_hint,
                "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
                "result_envelope": _result_envelope(
                    result_kind="diff_truncated" if truncated else ("diff_present" if diff_text else "no_diff"),
                    semantic_complete=not truncated,
                    model_visible_text_truncated=truncated,
                    result_limit_reached=truncated,
                    artifact_backed_full_result=True,
                    recovery_call=recovery_call,
                    recovery_hint=envelope_recovery_hint,
                    context_effects=["repository_diff_observed", "tool_result_recoverable"],
                ),
            },
        )


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry([build_tool(name) for name in DEFAULT_TOOL_ORDER])


def build_tool(name: str) -> ToolDefinition:
    definitions = {
        "list_files": ToolDefinition(
            name="list_files",
            tool_version="repo_harness_list_files_v1",
            model_visible_description=(
                "Discover model-visible files inside the workspace with pagination. "
                "Use this before grep when you know a filename, module name, or glob pattern. "
                "Hidden dependency, credential, build, cache, and version-control paths are excluded."
            ),
            model_visible_prompt=(
                "Use list_files with optional path/root, glob, offset, and max_entries. "
                "For file discovery, call list_files first; then call grep(output_mode='files_with_matches') "
                "or read_file on the relevant paths."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Alias for root; workspace-relative."},
                    "root": {"type": "string", "description": "Workspace-relative directory or file."},
                    "glob": {"type": "string", "description": "Optional fnmatch-style file glob."},
                    "offset": {"type": "integer", "description": "Zero-based result offset for pagination."},
                    "max_entries": {"type": "integer", "description": "Maximum returned entries for this page."},
                    "kind": {"type": "string", "enum": ["file"], "description": "Currently only file entries are returned."},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "files": {"type": "array"},
                    "result_kind": {"type": "string"},
                    "scan_complete_reason": {"type": "string"},
                    "recommended_next_calls": {"type": "array"},
                },
            },
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
            is_read_only=True,
            is_concurrency_safe=True,
        ),
        "glob_files": ToolDefinition(
            name="glob_files",
            tool_version="repo_harness_glob_files_v0",
            model_visible_description=(
                "Discover model-visible files matching a fnmatch-style glob pattern. "
                "This is a direct file-discovery alias for list_files with the same pagination, "
                "workspace boundary, hidden path filtering, and scan completeness fields."
            ),
            model_visible_prompt=(
                "Use glob_files(pattern='*.py') or glob_files(pattern='src/**/*.py', path='src') "
                "when you know a filename shape or module path. Then use read_file or "
                "grep(output_mode='files_with_matches') on the returned paths."
            ),
            input_schema={
                "type": "object",
                "required": ["pattern"],
                "properties": {
                    "pattern": {"type": "string", "description": "fnmatch-style file glob."},
                    "path": {"type": "string", "description": "Workspace-relative search root."},
                    "root": {"type": "string", "description": "Alias for path; workspace-relative search root."},
                    "offset": {"type": "integer", "description": "Zero-based result offset for pagination."},
                    "max_entries": {"type": "integer", "description": "Maximum returned entries for this page."},
                },
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "files": {"type": "array"},
                    "result_kind": {"type": "string"},
                    "scan_complete_reason": {"type": "string"},
                    "recommended_next_calls": {"type": "array"},
                },
            },
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
            is_read_only=True,
            is_concurrency_safe=True,
        ),
        "read_file": ToolDefinition(
            name="read_file",
            tool_version="repo_harness_read_file_v0",
            model_visible_description=(
                "Read a UTF-8 text file using a workspace-relative path. "
                "Absolute container paths are not accepted."
            ),
            model_visible_prompt=(
                "Use read_file with a workspace-relative path. Optionally pass start_line "
                "and end_line; offset and limit are accepted as aliases. The displayed lines "
                "include line-number prefixes, but edit_file old_text must use raw text without those prefixes."
            ),
            input_schema={
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "offset": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "content_preview": {"type": "string"},
                    "content_sha256": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "total_lines": {"type": "integer"},
                    "truncated": {"type": "boolean"},
                    "next_start_line": {"type": "integer"},
                    "raw_content_preview": {"type": "string"},
                },
            },
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
            is_read_only=True,
            is_concurrency_safe=True,
        ),
        "read_tool_result_artifact": ToolDefinition(
            name="read_tool_result_artifact",
            tool_version="repo_harness_read_tool_result_artifact_v0",
            model_visible_description=(
                "Recover a paginated page from a stored tool result artifact that was explicitly "
                "referenced by a provider-committed persisted tool result preview. The artifact_id "
                "is an opaque capability id, not a workspace path."
            ),
            model_visible_prompt=(
                "Use read_tool_result_artifact only when a previous persisted tool result preview "
                "gave an opaque artifact_id. This is not a file-reading tool. Pass artifact_id plus "
                "optional offset and limit. Do not pass workspace file paths or ordinary artifact "
                "manifest ids. For workspace files use read_file. For ordinary grep or symbol_search "
                "pagination, keep using that original tool with its offset or paging argument."
            ),
            input_schema={
                "type": "object",
                "required": ["artifact_id"],
                "properties": {
                    "artifact_id": {"type": "string", "description": "Opaque recoverable tool result artifact id."},
                    "offset": {"type": "integer", "description": "Zero-based character offset."},
                    "limit": {"type": "integer", "description": "Maximum characters to return."},
                },
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "next_offset": {"type": ["integer", "null"]},
                    "content_sha256": {"type": "string"},
                    "tool_result_id": {"type": "string"},
                    "artifact_id_looks_like_path": {"type": "boolean"},
                    "suggested_tool": {"type": ["string", "null"]},
                    "suggested_recovery_call": {"type": ["string", "null"]},
                },
            },
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
            is_read_only=True,
            is_concurrency_safe=True,
            requires_permission=False,
        ),
        "grep": ToolDefinition(
            name="grep",
            tool_version="repo_harness_grep_v1",
            model_visible_description=(
                "Search model-visible workspace files. root/path may be a workspace-relative file "
                "or directory. Default mode is literal substring; set mode='regex' for regular "
                "expressions. Results are paginated, hidden paths are excluded, and scan "
                "completeness is reported explicitly."
            ),
            model_visible_prompt=(
                "Use grep with query and optional root/path, mode, glob, output_mode, offset, max_matches, "
                "and context_lines. root/path may name a workspace-relative single file or directory. Use "
                "grep(query='needle', path='src/foo.py') to search one file, or "
                "grep(query='needle', root='src', glob='*.py', output_mode='files_with_matches') "
                "to search matching files under a directory. Prefer output_mode='files_with_matches' "
                "before reading large content. "
                "If a literal search for a regex-like query returns no matches, retry with mode='regex'. "
                "Do not treat partial_scan_no_match or incomplete scan facts as proof that the query is absent."
            ),
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "description": "Literal substring or regular expression to find."},
                    "mode": {"type": "string", "enum": ["literal", "regex"], "description": "Search mode; defaults to literal."},
                    "root": {"type": "string", "description": "Optional workspace-relative file or directory to search."},
                    "path": {"type": "string", "description": "Alias for root; workspace-relative file or directory to search."},
                    "glob": {"type": "string", "description": "Optional fnmatch-style file glob used when searching a directory root."},
                    "output_mode": {
                        "type": "string",
                        "enum": ["content", "files_with_matches", "count"],
                        "description": "content returns matching lines, files_with_matches returns matching paths, count returns counts only.",
                    },
                    "max_matches": {"type": "integer", "description": "Maximum returned matches for this page."},
                    "offset": {"type": "integer", "description": "Zero-based match offset for pagination."},
                    "context_lines": {"type": "integer", "description": "Line context before and after each match."},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "matches": {"type": "array"},
                    "files_with_matches": {"type": "array"},
                    "result_kind": {"type": "string"},
                    "scan_complete_reason": {"type": "string"},
                    "read_error_count": {"type": "integer"},
                    "visibility_error_count": {"type": "integer"},
                },
            },
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
            is_read_only=True,
            is_concurrency_safe=True,
        ),
        "symbol_search": ToolDefinition(
            name="symbol_search",
            tool_version="repo_harness_symbol_search_v0",
            model_visible_description=(
                "Search Python class, function, and method definitions using a lightweight AST index. "
                "This is symbol navigation, not a full language server or complete static analysis."
            ),
            model_visible_prompt=(
                "Use symbol_search when the task names a class, function, method, inheritance behavior, "
                "or call-related entry point. Pass query plus optional root/path, symbol_kind, offset, "
                "and max_results. Prefer a narrow package or source directory root from repository_hints; "
                "wide root='.' may return scan_requires_narrow_root with a recovery call. "
                "If result_kind is partial_symbol_results, cross-check with grep."
            ),
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "description": "Class, function, method, or symbol text."},
                    "path": {"type": "string", "description": "Alias for root; workspace-relative search root."},
                    "root": {"type": "string", "description": "Workspace-relative search root."},
                    "symbol_kind": {
                        "type": "string",
                        "enum": ["any", "class", "function", "method"],
                        "description": "Optional symbol kind filter.",
                    },
                    "kind": {"type": "string", "enum": ["any", "class", "function", "method"], "description": "Alias for symbol_kind."},
                    "offset": {"type": "integer", "description": "Zero-based result offset for pagination."},
                    "max_results": {"type": "integer", "description": "Maximum returned symbols for this page."},
                },
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "symbols": {"type": "array"},
                    "result_kind": {"type": "string"},
                    "scan_complete_reason": {"type": "string"},
                    "parse_error_count": {"type": "integer"},
                    "candidate_file_count": {"type": "integer"},
                    "scanned_file_count": {"type": "integer"},
                    "semantic_complete": {"type": "boolean"},
                    "slow_scan": {"type": "boolean"},
                    "recommended_narrow_roots": {"type": "array"},
                    "recommended_next_calls": {"type": "array"},
                },
            },
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
            is_read_only=True,
            is_concurrency_safe=True,
        ),
        "update_working_state": ToolDefinition(
            name="update_working_state",
            tool_version="repo_harness_update_working_state_v0",
            model_visible_description=(
                "Record the current investigation hypothesis, candidate files, completed steps, "
                "next concrete action, and any blocking question. This tool does not modify repository files."
            ),
            model_visible_prompt=(
                "Use update_working_state when exploration is starting to branch or repeat. "
                "Keep it brief: state the current_hypothesis, candidate_files, next_action, "
                "completed_steps, or blocking_question. Then continue with a concrete read, edit, or final answer."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "current_hypothesis": {"type": "string"},
                    "candidate_files": {"type": "array", "items": {"type": "string"}},
                    "next_action": {"type": "string"},
                    "completed_steps": {"type": "array", "items": {"type": "string"}},
                    "blocking_question": {"type": "string"},
                },
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "working_state": {"type": "object"},
                    "policy_version": {"type": "string"},
                },
            },
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
            is_read_only=True,
            is_concurrency_safe=False,
        ),
        "edit_file": ToolDefinition(
            name="edit_file",
            tool_version="repo_harness_edit_file_v0",
            model_visible_description="Replace exact text in an existing UTF-8 file.",
            model_visible_prompt=(
                "Use edit_file with path, old_text, and new_text only after reading the target file. "
                "In formal runtimes, edit_file may require a prior read_file observation or a matching "
                "expected_content_hash from read_file. old_text must be exact raw text, not read_file "
                "line-number prefixes."
            ),
            input_schema={
                "type": "object",
                "required": ["path", "old_text", "new_text"],
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                    "expected_content_hash": {"type": "string", "description": "sha256 from read_file content_hash."},
                    "replace_all": {"type": "boolean", "default": False},
                },
            },
            output_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
        ),
        "create_file": ToolDefinition(
            name="create_file",
            tool_version="repo_harness_create_file_v0",
            model_visible_description="Create a new UTF-8 file inside the workspace.",
            model_visible_prompt="Use create_file with path and content. Existing files are rejected.",
            input_schema={"type": "object", "required": ["path", "content"]},
            output_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
        ),
        "bash": ToolDefinition(
            name="bash",
            tool_version="repo_harness_bash_v0",
            model_visible_description=(
                "Run a restricted diagnostic command inside the workspace. This is not a "
                "general shell: do not use cd, pipes, redirects, shell composition, "
                "variable expansion, or arbitrary python -c snippets. Allowed diagnostic "
                "families include pwd, file-specific ls, read-only git status/diff/show/log/ls-files, "
                "ruff check, mypy, and python -m compileall. find, grep shell commands, curl, wget, "
                "ssh, sudo, rm, and git diff --no-index are denied. Use cwd for directories, "
                "read_file/grep for inspection, run_tests for configured test feedback, and git_diff for patch review."
            ),
            model_visible_prompt=(
                "Use bash only for the restricted allowlist. Pass a single command plus "
                "optional cwd and timeout_sec; do not combine commands. Do not use bash as a replacement "
                "for read_file, grep, run_tests, or git_diff."
            ),
            input_schema={
                "type": "object",
                "required": ["command"],
                "properties": {
                    "command": {"type": "string", "description": "Single restricted diagnostic command."},
                    "cwd": {"type": "string", "description": "Optional workspace-relative working directory."},
                    "timeout_sec": {"type": "integer", "description": "Optional command timeout in seconds."},
                },
            },
            output_schema={"type": "object", "properties": {"stdout_preview": {"type": "string"}}},
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
        ),
        "run_tests": ToolDefinition(
            name="run_tests",
            tool_version="repo_harness_run_tests_v0",
            model_visible_description=(
                "Run the current task's configured intermediate feedback path. "
                "Do not pass a command; this tool takes no arguments."
            ),
            model_visible_prompt=(
                "Use run_tests without arguments. It does not run arbitrary shell commands."
            ),
            input_schema={"type": "object", "additionalProperties": False},
            output_schema={"type": "object", "properties": {"accepted": {"type": "boolean"}}},
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
        ),
        "git_diff": ToolDefinition(
            name="git_diff",
            tool_version="repo_harness_git_diff_v0",
            model_visible_description=(
                "Show the current workspace diff with a changed-file summary. "
                "Use the optional path field to inspect one file when the full diff is truncated."
            ),
            model_visible_prompt=(
                "Use git_diff with optional workspace-relative path. Before the final answer after editing files, "
                "inspect git_diff to verify the actual patch."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Optional workspace-relative file or directory."},
                },
                "additionalProperties": False,
            },
            output_schema={"type": "object", "properties": {"diff_preview": {"type": "string"}}},
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
            is_read_only=True,
            is_concurrency_safe=True,
        ),
    }
    if name not in definitions:
        raise KeyError(f"Unknown tool: {name}")
    return definitions[name]


def _schema_issue(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    rules: dict[str, tuple[type, bool]] = {
        "list_files.path": (str, False),
        "list_files.root": (str, False),
        "list_files.pattern": (str, False),
        "list_files.glob": (str, False),
        "list_files.offset": (int, False),
        "list_files.max_entries": (int, False),
        "list_files.kind": (str, False),
        "glob_files.pattern": (str, True),
        "glob_files.path": (str, False),
        "glob_files.root": (str, False),
        "glob_files.offset": (int, False),
        "glob_files.max_entries": (int, False),
        "read_file.path": (str, True),
        "read_file.start_line": (int, False),
        "read_file.end_line": (int, False),
        "read_file.offset": (int, False),
        "read_file.limit": (int, False),
        "read_tool_result_artifact.artifact_id": (str, True),
        "read_tool_result_artifact.offset": (int, False),
        "read_tool_result_artifact.limit": (int, False),
        "grep.query": (str, True),
        "grep.pattern": (str, False),
        "grep.path": (str, False),
        "grep.root": (str, False),
        "grep.mode": (str, False),
        "grep.glob": (str, False),
        "grep.output_mode": (str, False),
        "grep.max_matches": (int, False),
        "grep.offset": (int, False),
        "grep.context_lines": (int, False),
        "symbol_search.query": (str, True),
        "symbol_search.path": (str, False),
        "symbol_search.root": (str, False),
        "symbol_search.symbol_kind": (str, False),
        "symbol_search.kind": (str, False),
        "symbol_search.offset": (int, False),
        "symbol_search.max_results": (int, False),
        "update_working_state.current_hypothesis": (str, False),
        "update_working_state.candidate_files": (list, False),
        "update_working_state.next_action": (str, False),
        "update_working_state.completed_steps": (list, False),
        "update_working_state.blocking_question": (str, False),
        "edit_file.path": (str, True),
        "edit_file.old_text": (str, True),
        "edit_file.new_text": (str, True),
        "edit_file.replace_all": (bool, False),
        "edit_file.expected_content_hash": (str, False),
        "edit_file.expected_content_sha256": (str, False),
        "create_file.path": (str, True),
        "create_file.content": (str, True),
        "bash.command": (str, True),
        "bash.cwd": (str, False),
        "bash.timeout_sec": (int, False),
        "git_diff.path": (str, False),
    }
    if tool_name == "run_tests" and args:
        field = next(iter(args))
        return _issue(field, "no arguments", args[field], retryable=True)
    tool_rules = {key.split(".", 1)[1]: value for key, value in rules.items() if key.startswith(f"{tool_name}.")}
    for field_name, (expected_type, required) in tool_rules.items():
        if required and field_name not in args:
            if tool_name == "grep" and field_name == "query" and "pattern" in args:
                continue
            return _issue(field_name, _type_name(expected_type), None, retryable=True)
        if field_name in args and not _is_exact_type(args[field_name], expected_type):
            return _issue(field_name, _type_name(expected_type), args[field_name], retryable=True)
        if (
            tool_name in {"read_file", "read_tool_result_artifact", "list_files", "glob_files", "grep", "symbol_search"}
            and field_name in {"start_line", "end_line", "offset", "limit", "max_entries", "max_matches", "max_results", "context_lines"}
            and field_name in args
            and args[field_name] < (
                0
                if (
                    (field_name == "offset" and tool_name in {"list_files", "glob_files", "grep", "symbol_search"})
                    or (field_name == "offset" and tool_name == "read_tool_result_artifact")
                    or (field_name == "context_lines" and tool_name == "grep")
                )
                else 1
            )
        ):
            expected = (
                "non-negative integer"
                if (
                    (field_name == "offset" and tool_name in {"list_files", "glob_files", "grep", "symbol_search"})
                    or (field_name == "offset" and tool_name == "read_tool_result_artifact")
                    or (field_name == "context_lines" and tool_name == "grep")
                )
                else "positive integer"
            )
            return _issue(field_name, expected, args[field_name], retryable=True)
        if tool_name == "grep" and field_name == "mode" and field_name in args and args[field_name] not in {"literal", "regex"}:
            return _issue(field_name, "literal|regex", args[field_name], retryable=True)
        if (
            tool_name == "symbol_search"
            and field_name in {"symbol_kind", "kind"}
            and field_name in args
            and args[field_name] not in SUPPORTED_SYMBOL_KINDS
        ):
            return _issue(field_name, "class|function|method|any", args[field_name], retryable=True)
        if tool_name == "list_files" and field_name == "kind" and field_name in args and args[field_name] not in {"file"}:
            return _issue(field_name, "file", args[field_name], retryable=True)
    for field_name in args:
        if field_name not in tool_rules:
            return _issue(field_name, "known field", args[field_name], retryable=True)
    return None


def _issue(field: str, expected_type: str, value: Any, *, retryable: bool) -> dict[str, Any]:
    return {
        "field": field,
        "expected_type": expected_type,
        "actual_type": "missing" if value is None else type(value).__name__,
        "retryable": retryable,
    }


def _is_exact_type(value: Any, expected_type: type) -> bool:
    if expected_type is bool:
        return type(value) is bool
    if expected_type is int:
        return type(value) is int
    return isinstance(value, expected_type)


def _type_name(expected_type: type) -> str:
    if expected_type is str:
        return "string"
    if expected_type is int:
        return "integer"
    if expected_type is bool:
        return "boolean"
    if expected_type is list:
        return "array"
    return expected_type.__name__


def _result_envelope(
    *,
    result_kind: str,
    semantic_complete: bool,
    model_visible_text_truncated: bool = False,
    result_limit_reached: bool = False,
    artifact_backed_full_result: bool = False,
    recommended_next_calls: list[dict[str, Any]] | None = None,
    recovery_call: str | None = None,
    recovery_hint: str | None = None,
    context_effects: list[str] | None = None,
) -> dict[str, Any]:
    effects = [
        effect
        for effect in context_effects or []
        if effect in TOOL_RESULT_CONTEXT_EFFECTS
    ]
    return {
        "schema_version": TOOL_RESULT_ENVELOPE_VERSION,
        "result_kind": result_kind,
        "semantic_complete": semantic_complete,
        "model_visible_text_truncated": model_visible_text_truncated,
        "result_limit_reached": result_limit_reached,
        "artifact_backed_full_result": artifact_backed_full_result,
        "recommended_next_calls": recommended_next_calls or [],
        "recovery_call": recovery_call,
        "recovery_hint": recovery_hint,
        "context_effects": effects,
    }


def _tool_result_artifact_misuse_hint(artifact_id: str) -> dict[str, Any]:
    if _artifact_id_looks_like_workspace_path(artifact_id):
        suggested_call = f"read_file(path={artifact_id!r})"
        return {
            "message": (
                "This value looks like a workspace file path. read_tool_result_artifact is not a file reader; "
                "use read_file for workspace files."
            ),
            "typed": {
                "artifact_id_looks_like_path": True,
                "suggested_tool": "read_file",
                "suggested_recovery_call": suggested_call,
            },
            "recommended_next_calls": [
                {"tool": "read_file", "arguments": {"path": artifact_id}},
            ],
        }
    return {
        "message": (
            "Only opaque artifact_id values copied from provider-committed persisted tool result previews "
            "can be recovered. For ordinary files use read_file; for ordinary search pagination use grep "
            "or symbol_search with their paging arguments."
        ),
        "typed": {
            "artifact_id_looks_like_path": False,
            "suggested_tool": None,
            "suggested_recovery_call": None,
        },
        "recommended_next_calls": [],
    }


def _artifact_id_looks_like_workspace_path(artifact_id: str) -> bool:
    if not artifact_id:
        return False
    if "/" in artifact_id or "\\" in artifact_id:
        return True
    if artifact_id.startswith("."):
        return True
    suffixes = {
        ".py",
        ".pyi",
        ".txt",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".rst",
    }
    return PurePosixPath(artifact_id).suffix.lower() in suffixes


def _tool_recovery_call(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    typed: dict[str, Any],
) -> tuple[str, str]:
    if tool_name == "read_file":
        path = str(arguments.get("path") or typed.get("path") or "")
        start_line = typed.get("next_start_line") or arguments.get("start_line") or 1
        call = f"read_file(path={path!r}, start_line={start_line})"
        hint = (
            "Continue reading from next_start_line to recover omitted content."
            if typed.get("next_start_line") is not None
            else "Re-read this file range with read_file when the omitted content is needed."
        )
        return call, hint
    if tool_name == "grep":
        query = str(arguments.get("query") or typed.get("query") or "")
        mode = str(arguments.get("mode") or typed.get("mode") or "literal")
        root = str(arguments.get("root") or arguments.get("path") or ".")
        offset = typed.get("next_offset") if typed.get("next_offset") is not None else arguments.get("offset", 0)
        parts = [f"query={query!r}", f"mode={mode!r}", f"root={root!r}", f"offset={offset}"]
        glob = arguments.get("glob")
        if isinstance(glob, str) and glob:
            parts.append(f"glob={glob!r}")
        max_matches = arguments.get("max_matches")
        if isinstance(max_matches, int):
            parts.append(f"max_matches={max_matches}")
        call = f"grep({', '.join(parts)})"
        hint = (
            "Use the next_offset page to continue the same search."
            if typed.get("next_offset") is not None
            else "Re-run or narrow the grep query, root, or glob to recover omitted matches."
        )
        return call, hint
    if tool_name == "list_files":
        root = str(arguments.get("root") or arguments.get("path") or ".")
        offset = typed.get("next_offset") if typed.get("next_offset") is not None else arguments.get("offset", 0)
        parts = [f"root={root!r}", f"offset={offset}"]
        glob = arguments.get("glob") or arguments.get("pattern")
        if isinstance(glob, str) and glob:
            parts.append(f"glob={glob!r}")
        max_entries = arguments.get("max_entries")
        if isinstance(max_entries, int):
            parts.append(f"max_entries={max_entries}")
        call = f"list_files({', '.join(parts)})"
        hint = (
            "Use the next_offset page to continue listing files."
            if typed.get("next_offset") is not None
            else "Re-run list_files with the same root or a narrower glob."
        )
        return call, hint
    if tool_name == "git_diff":
        path = arguments.get("path")
        if not path:
            changed_files = typed.get("changed_files")
            if isinstance(changed_files, list):
                for changed_file in changed_files:
                    if isinstance(changed_file, dict) and changed_file.get("path"):
                        path = changed_file["path"]
                        break
                    if isinstance(changed_file, str) and changed_file:
                        path = changed_file
                        break
        if path:
            return f"git_diff(path={str(path)!r})", "Re-run git_diff for this changed file."
        return "git_diff()", "Re-run git_diff to recover the current patch context."
    path = arguments.get("path") or typed.get("path")
    if path:
        return f"{tool_name}(path={str(path)!r}, ...)", "Retry the tool after refreshing the relevant file context."
    return f"{tool_name}(...)", "Retry the tool with corrected arguments."


def _tool_result(
    tool_call: ToolCall,
    *,
    status: str,
    content: str,
    normalized: NormalizedToolRequest | None = None,
    error_type: str | None = None,
    truncated: bool = False,
    artifact_refs: list[ArtifactRef] | None = None,
    typed: dict[str, Any] | None = None,
) -> ToolResult:
    normalized = normalized or NormalizedToolRequest(
        requested_tool_name=tool_call.tool_name,
        effective_tool_name=tool_call.tool_name,
        requested_arguments=tool_call.arguments,
        normalized_arguments=tool_call.arguments,
        effective_arguments=tool_call.arguments,
        normalized_input_hash=stable_hash(tool_call.arguments),
    )
    result_typed = dict(typed or {})
    result_typed.setdefault("status", status)
    if error_type is not None:
        result_typed.setdefault("error_type", error_type)
    return ToolResult(
        tool_result_id=f"{tool_call.tool_call_id}_result",
        tool_call_id=tool_call.tool_call_id,
        tool_name=normalized.effective_tool_name,
        requested_tool_name=normalized.requested_tool_name,
        effective_tool_name=normalized.effective_tool_name,
        requested_arguments=normalized.requested_arguments,
        normalized_arguments=normalized.normalized_arguments,
        effective_arguments=normalized.effective_arguments,
        normalized_input_hash=normalized.normalized_input_hash,
        route_reason=normalized.route_reason,
        status=status,  # type: ignore[arg-type]
        content_preview=content,
        error_type=error_type,
        truncated=truncated,
        artifact_refs=artifact_refs or [],
        typed=result_typed,
    )


def _is_permission_workspace_error(message: str) -> bool:
    return "拒绝" in message or "边界" in message or "敏感路径" in message


def _clamp_command_timeout(requested_timeout: int, context: ToolExecutionContext) -> int:
    command_timeout = getattr(context.budget_manager, "command_timeout_sec", None)
    if command_timeout is None:
        return requested_timeout
    return max(1, min(requested_timeout, int(command_timeout)))


def _resolve_cwd(context: ToolExecutionContext, cwd: str) -> str:
    return context.workspace_adapter.resolve_workspace_path(
        context.run_workspace.workspace_path,
        cwd,
        must_exist=True,
    ).as_posix()


def _slice_text(content: str, start_line: Any, end_line: Any) -> str:
    if start_line is None and end_line is None:
        return content
    lines = content.splitlines(keepends=True)
    start = max(int(start_line or 1), 1)
    end = int(end_line or len(lines))
    return "".join(lines[start - 1 : end])


def _line_window(
    content: str,
    *,
    start_line: Any,
    end_line: Any,
    max_chars: int,
) -> dict[str, Any]:
    lines = content.splitlines()
    total_lines = len(lines)
    start = max(int(start_line or 1), 1)
    requested_end = int(end_line or total_lines or start)
    requested_end = max(requested_end, start)
    numbered_parts: list[str] = []
    raw_parts: list[str] = []
    current_end = start - 1
    truncated = False
    budget = max(1, max_chars - 300)
    for line_number in range(start, min(requested_end, total_lines) + 1):
        raw_line = lines[line_number - 1]
        numbered = f"{line_number:>6} | {raw_line}"
        next_numbered = "\n".join([*numbered_parts, numbered])
        if len(numbered) > budget:
            visible_budget = max(0, budget - len(f"{line_number:>6} | ") - len("\n[line truncated]"))
            clipped_raw = raw_line[:visible_budget] + "\n[line truncated]"
            numbered_parts.append(f"{line_number:>6} | {clipped_raw}")
            raw_parts.append(clipped_raw)
            current_end = line_number
            truncated = True
            break
        if len(next_numbered) > budget and numbered_parts:
            truncated = True
            break
        numbered_parts.append(numbered)
        raw_parts.append(raw_line)
        current_end = line_number
    if current_end < min(requested_end, total_lines):
        truncated = True
    numbered_content = "\n".join(numbered_parts)
    raw_content = "\n".join(raw_parts)
    if content.endswith("\n") and raw_parts:
        raw_content += "\n"
    return {
        "start_line": start,
        "end_line": current_end,
        "total_lines": total_lines,
        "numbered_content": numbered_content,
        "raw_content_preview": raw_content,
        "truncated": truncated,
        "next_start_line": current_end + 1 if truncated else None,
    }


def _sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _is_model_hidden_tool_path(path: str) -> bool:
    normalized = PurePosixPath(path.replace("\\", "/"))
    parts = tuple(part.lower() for part in normalized.parts)
    if any(
        part in MODEL_HIDDEN_TOOL_PATH_PARTS or part.startswith(".env") or part.endswith(".egg-info")
        for part in parts
    ):
        return True
    return normalized.suffix.lower() in MODEL_HIDDEN_TOOL_PATH_SUFFIXES


def _model_visible_path_status(
    context: ToolExecutionContext,
    rel_path: str,
) -> tuple[bool, str | None]:
    if _is_model_hidden_tool_path(rel_path):
        return False, "hidden_path"
    try:
        resolved = context.workspace_adapter.resolve_workspace_path(
            context.run_workspace.workspace_path,
            rel_path,
            must_exist=True,
        )
    except WorkspaceError as exc:
        message = str(exc)
        lowered = message.lower()
        if "符号链接" in message or "symlink" in lowered:
            return False, "symlink_outside_workspace"
        if "敏感路径" in message or "sensitive" in lowered:
            return False, "symlink_target_hidden_path"
        if "边界" in message:
            try:
                context.workspace_adapter.resolve_workspace_path(
                    context.run_workspace.workspace_path,
                    rel_path,
                    must_exist=False,
                )
            except WorkspaceError as symlink_probe_exc:
                probe_message = str(symlink_probe_exc)
                if "符号链接" in probe_message or "symlink" in probe_message.lower():
                    return False, "symlink_outside_workspace"
        if "路径不存在" in message or "不存在" in message or "missing" in lowered or "边界" in message:
            return False, "workspace_boundary_or_missing"
        return False, "workspace_boundary_or_missing"
    except Exception:
        return False, "visibility_error"
    try:
        workspace_root = context.workspace_adapter.resolve_workspace_path(
            context.run_workspace.workspace_path,
            ".",
            must_exist=True,
        )
        target_rel = resolved.relative_to(workspace_root)
        target_rel_posix = target_rel.as_posix()
        if target_rel_posix != rel_path and _is_model_hidden_tool_path(target_rel_posix):
            return False, "symlink_target_hidden_path"
    except Exception:
        return False, "visibility_error"
    return True, None


def _looks_like_numbered_read_file_snippet(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    prefixed = sum(1 for line in lines[:5] if re.match(r"^\s*\d+\s*\|\s?", line))
    return prefixed >= max(1, min(len(lines[:5]), 2))


def _looks_like_regex(query: str) -> bool:
    return bool(
        re.search(
            r"(?<!\\)(\.\*|\[[^\]]+\]|\([^)]*[|?+*][^)]*\)|\\[dws.]|\^|\$|\||\?)",
            query,
        )
    )


def _grep_result_kind(
    *,
    current_page_match_count: int,
    total_match_count: int,
    result_limit_reached: bool,
    scan_complete: bool,
) -> str:
    if total_match_count > 0 and current_page_match_count == 0:
        return "page_empty_out_of_range"
    if total_match_count == 0:
        return "complete_no_match" if scan_complete else "partial_scan_no_match"
    if not scan_complete:
        return "partial_scan_with_matches"
    if result_limit_reached:
        return "result_page_truncated"
    return "complete_with_matches"


def _is_wide_symbol_root(root: str) -> bool:
    return root.strip() in {"", "."}


def _recommended_symbol_search_roots(paths: list[str], *, max_roots: int = 6) -> list[str]:
    ignored_first_parts = {
        ".github",
        "doc",
        "docs",
        "documentation",
        "examples",
        "images",
        "img",
        "news",
        "requirements",
        "scripts",
        "test",
        "tests",
        "tools",
    }
    counts: dict[str, int] = {}
    for path in paths:
        parts = PurePosixPath(path).parts
        if not parts:
            continue
        first = parts[0]
        if first in ignored_first_parts or first.startswith("."):
            continue
        if first == "src" and len(parts) >= 2:
            root = f"src/{parts[1]}"
        elif len(parts) >= 3 and parts[1] in {"core", "nodes", "rules"}:
            root = f"{parts[0]}/{parts[1]}"
        else:
            root = first
        counts[root] = counts.get(root, 0) + 1
    if not counts:
        for path in paths:
            parts = PurePosixPath(path).parts
            if parts and not parts[0].startswith("."):
                counts[parts[0]] = counts.get(parts[0], 0) + 1
    return [
        root
        for root, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:max_roots]
    ]


def _scan_complete_reason(
    *,
    scan_complete: bool,
    result_limit_reached: bool,
    scan_limit_reached: bool,
    read_error_count: int,
    visibility_error_count: int,
    workspace_boundary_or_missing_count: int,
    backend_mismatch_detected: bool,
    total_match_count: int,
) -> str:
    if backend_mismatch_detected:
        return "backend_mismatch_detected"
    if scan_limit_reached:
        return "scan_limit_reached"
    if read_error_count:
        return "read_errors_present"
    if visibility_error_count:
        return "visibility_errors_present"
    if workspace_boundary_or_missing_count:
        return "workspace_boundary_or_missing_present"
    if result_limit_reached:
        return "result_page_truncated"
    if scan_complete and total_match_count == 0:
        return "complete_no_match_all_visible_candidates_read"
    if scan_complete:
        return "complete_all_visible_candidates_read"
    return "scan_incomplete"


def _backend_mismatch_detected(context: ToolExecutionContext) -> bool:
    backend = getattr(context.workspace_adapter, "backend", None)
    backend_value = getattr(backend, "value", backend)
    execution_mode = getattr(context.run_workspace, "execution_mode", None)
    return bool(backend_value and execution_mode and str(backend_value) != str(execution_mode))


def _search_fact_fields(
    *,
    context: ToolExecutionContext,
    root: str,
    search_backend: str,
    scan_complete_reason: str,
    read_error_count: int,
    read_error_samples: list[dict[str, str]],
    visibility_error_count: int,
    visibility_error_samples: list[dict[str, str]],
    backend_mismatch_detected: bool,
) -> dict[str, Any]:
    return {
        "root": root,
        "search_backend": search_backend,
        "workspace_execution_mode": context.run_workspace.execution_mode,
        "workspace_backend": str(getattr(getattr(context.workspace_adapter, "backend", ""), "value", getattr(context.workspace_adapter, "backend", ""))),
        "read_error_count": read_error_count,
        "read_error_samples": read_error_samples,
        "visibility_error_count": visibility_error_count,
        "visibility_error_samples": visibility_error_samples,
        "scan_complete_reason": scan_complete_reason,
        "backend_mismatch_detected": backend_mismatch_detected,
        "search_fact_policy_version": SEARCH_FACT_POLICY_VERSION,
    }


def _grep_recommended_next_calls(
    *,
    query: str,
    mode: str,
    root: str,
    glob: str | None,
    next_offset: int | None,
    max_matches: int,
    scan_limit_reached: bool,
    regex_hint: bool,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    if next_offset is not None:
        args: dict[str, Any] = {
            "query": query,
            "mode": mode,
            "root": root,
            "offset": next_offset,
            "max_matches": max_matches,
        }
        if glob is not None:
            args["glob"] = glob
        calls.append(
            {
                "tool": "grep",
                "arguments": args,
                "reason": "More matches are available through result pagination.",
            }
        )
    if scan_limit_reached:
        narrowed_args: dict[str, Any] = {
            "query": query,
            "mode": mode,
            "root": "src" if root == "." else root,
        }
        narrowed_args["glob"] = glob if glob is not None else "*.py"
        calls.append(
            {
                "tool": "grep",
                "arguments": narrowed_args,
                "reason": "The previous search did not scan the full candidate set; narrow root or glob.",
            }
        )
    if regex_hint:
        args = {"query": query, "mode": "regex", "root": root}
        if glob is not None:
            args["glob"] = glob
        calls.append(
            {
                "tool": "grep",
                "arguments": args,
                "reason": "The literal query looks like a regular expression.",
            }
        )
    return calls


def _list_files_recommended_next_calls(
    *,
    root: str,
    glob: str | None,
    next_offset: int | None,
    max_entries: int,
    scan_complete: bool,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    if next_offset is not None:
        args: dict[str, Any] = {"root": root, "offset": next_offset, "max_entries": max_entries}
        if glob is not None:
            args["glob"] = glob
        calls.append(
            {
                "tool": "list_files",
                "arguments": args,
                "reason": "More files are available through result pagination.",
            }
        )
    if not scan_complete:
        args = {"root": "." if root == "/" else root, "max_entries": max_entries}
        if glob is not None:
            args["glob"] = glob
        calls.append(
            {
                "tool": "list_files",
                "arguments": args,
                "reason": "The previous listing could not classify every candidate path; retry with a narrower root or glob.",
            }
        )
    return calls


def _glob_files_recommended_next_calls(
    calls: list[dict[str, Any]],
    *,
    fallback_pattern: str,
) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for call in calls:
        args = dict(call.get("arguments") or {})
        pattern = args.pop("glob", fallback_pattern)
        path = args.pop("root", ".")
        converted.append(
            {
                **call,
                "tool": "glob_files",
                "arguments": {
                    "pattern": pattern,
                    "path": path,
                    **args,
                },
            }
        )
    return converted


def _grep_python(
    *,
    context: ToolExecutionContext,
    root: str,
    query: str,
    mode: str,
    glob: str | None,
    offset: int,
    max_matches: int,
    context_lines: int,
    output_mode: str,
) -> dict[str, Any]:
    if mode not in {"literal", "regex"}:
        raise WorkspaceError("grep mode must be literal or regex.")
    if output_mode not in GREP_OUTPUT_MODES:
        raise WorkspaceError("grep output_mode must be content, files_with_matches, or count.")
    pattern = re.compile(query) if mode == "regex" else None
    all_matches: list[dict[str, Any]] = []
    searched_file_count = 0
    hidden_path_count = 0
    symlink_outside_workspace_count = 0
    workspace_boundary_or_missing_count = 0
    visibility_error_count = 0
    visibility_error_samples: list[dict[str, str]] = []
    read_error_count = 0
    read_error_samples: list[dict[str, str]] = []
    matched_files: set[str] = set()
    files = context.workspace_adapter.list_files(
        context.run_workspace.workspace_path,
        root,
        pattern=glob,
    )
    scanned_candidate_file_count = min(len(files), GREP_MAX_SCANNED_FILES)
    for rel_path in files[:GREP_MAX_SCANNED_FILES]:
        visible, reason = _model_visible_path_status(context, rel_path)
        if not visible:
            if reason in {"hidden_path", "symlink_target_hidden_path"}:
                hidden_path_count += 1
            elif reason == "symlink_outside_workspace":
                symlink_outside_workspace_count += 1
            elif reason == "workspace_boundary_or_missing":
                workspace_boundary_or_missing_count += 1
            else:
                visibility_error_count += 1
                if len(visibility_error_samples) < 5:
                    visibility_error_samples.append({"path": rel_path, "reason": reason or "visibility_error"})
            continue
        try:
            text = _read_model_visible_text_for_grep(context, rel_path)
        except (UnicodeDecodeError, ValueError, WorkspaceError) as exc:
            read_error_count += 1
            if len(read_error_samples) < 5:
                read_error_samples.append({"path": rel_path, "reason": str(exc)[:240]})
            continue
        searched_file_count += 1
        lines = text.splitlines()
        for index, line in enumerate(lines):
            matched = query in line if mode == "literal" else bool(pattern and pattern.search(line))
            if not matched:
                continue
            matched_files.add(rel_path)
            start = max(0, index - context_lines)
            end = min(len(lines), index + context_lines + 1)
            rendered = []
            for line_index in range(start, end):
                prefix = ">" if line_index == index else " "
                rendered.append(f"{rel_path}:{line_index + 1}:{prefix}{lines[line_index]}")
            all_matches.append(
                {
                    "path": rel_path,
                    "line_number": index + 1,
                    "rendered": "\n".join(rendered),
                }
            )
    scan_limit_reached = len(files) > GREP_MAX_SCANNED_FILES
    page = all_matches[offset : offset + max_matches]
    next_offset = offset + len(page) if offset + len(page) < len(all_matches) else None
    result_limit_reached = next_offset is not None
    backend_mismatch_detected = _backend_mismatch_detected(context)
    scan_complete = not any(
        [
            scan_limit_reached,
            read_error_count,
            visibility_error_count,
            workspace_boundary_or_missing_count,
            backend_mismatch_detected,
        ]
    )
    scan_complete_reason = _scan_complete_reason(
        scan_complete=scan_complete,
        result_limit_reached=result_limit_reached,
        scan_limit_reached=scan_limit_reached,
        read_error_count=read_error_count,
        visibility_error_count=visibility_error_count,
        workspace_boundary_or_missing_count=workspace_boundary_or_missing_count,
        backend_mismatch_detected=backend_mismatch_detected,
        total_match_count=len(all_matches),
    )
    page_matched_files = sorted({str(entry["path"]) for entry in page})
    return {
        "matches": _grep_rendered_page(page, output_mode=output_mode),
        "files_with_matches": sorted(matched_files),
        "page_files_with_matches": page_matched_files,
        "total_match_count": len(all_matches),
        "candidate_file_count": len(files),
        "scanned_candidate_file_count": scanned_candidate_file_count,
        "scanned_file_count": searched_file_count,
        "searched_file_count": searched_file_count,
        "scanned_file_limit": GREP_MAX_SCANNED_FILES,
        "unscanned_file_count": max(0, len(files) - scanned_candidate_file_count),
        "scan_limit_reached": scan_limit_reached,
        "scan_complete": scan_complete,
        "scan_complete_reason": scan_complete_reason,
        "result_limit_reached": result_limit_reached,
        "matched_file_count": len(matched_files),
        "hidden_path_count": hidden_path_count,
        "skipped_hidden_count": hidden_path_count,
        "skipped_hidden_path_count": hidden_path_count,
        "symlink_outside_workspace_count": symlink_outside_workspace_count,
        "skipped_symlink_count": symlink_outside_workspace_count,
        "workspace_boundary_or_missing_count": workspace_boundary_or_missing_count,
        "read_error_count": read_error_count,
        "read_error_samples": read_error_samples,
        "visibility_error_count": visibility_error_count,
        "visibility_error_samples": visibility_error_samples,
        "backend_mismatch_detected": backend_mismatch_detected,
        "truncated": bool(result_limit_reached or not scan_complete),
        "next_offset": next_offset,
        "engine": "python_fallback",
        "search_backend": "workspace_adapter_python_fallback",
        "output_mode": output_mode,
    }


def _read_model_visible_text_for_grep(context: ToolExecutionContext, rel_path: str) -> str:
    return context.workspace_adapter.read_text(context.run_workspace.workspace_path, rel_path)


def _grep_rendered_page(page: list[dict[str, Any]], *, output_mode: str) -> list[str]:
    if output_mode == "files_with_matches":
        return sorted({str(entry["path"]) for entry in page})
    if output_mode == "count":
        return []
    return [str(entry["rendered"]) for entry in page]


def _parse_changed_files(name_status_text: str, numstat_text: str) -> list[dict[str, Any]]:
    statuses: dict[str, str] = {}
    for raw_line in name_status_text.splitlines():
        if not raw_line.strip():
            continue
        parts = raw_line.split("\t")
        if len(parts) >= 2:
            status = parts[0]
            path = parts[-1]
            statuses[path] = status
    changed: list[dict[str, Any]] = []
    for raw_line in numstat_text.splitlines():
        if not raw_line.strip():
            continue
        parts = raw_line.split("\t")
        if len(parts) < 3:
            continue
        added_raw, removed_raw, path = parts[0], parts[1], parts[-1]
        changed.append(
            {
                "path": path,
                "status": statuses.get(path, "modified"),
                "added_lines": 0 if added_raw == "-" else int(added_raw),
                "removed_lines": 0 if removed_raw == "-" else int(removed_raw),
            }
        )
    for path, status in statuses.items():
        if not any(entry["path"] == path for entry in changed):
            changed.append(
                {
                    "path": path,
                    "status": status,
                    "added_lines": 0,
                    "removed_lines": 0,
                }
            )
    return changed


def _command_stdout_from_artifact(
    context: ToolExecutionContext,
    result: Any,
) -> str | None:
    ref = getattr(result, "output_artifact_ref", None)
    if ref is None:
        return None
    try:
        artifact_text = (context.recorder.run_dir / ref.relative_path).read_text(encoding="utf-8")
    except OSError:
        return None
    marker = "\n\n[stdout]\n"
    stderr_marker = "\n\n[stderr]\n"
    if marker not in artifact_text:
        return None
    payload = artifact_text.split(marker, 1)[1]
    if stderr_marker in payload:
        payload = payload.rsplit(stderr_marker, 1)[0]
    return payload


def _visible_untracked_files(
    context: ToolExecutionContext,
    stdout_text: str,
) -> list[str]:
    files: list[str] = []
    for raw_line in stdout_text.splitlines():
        rel_path = raw_line.strip()
        if not rel_path:
            continue
        visible, _reason = _model_visible_path_status(context, rel_path)
        if visible:
            files.append(rel_path)
    return files


def _synthetic_untracked_diff(
    context: ToolExecutionContext,
    files: list[str],
) -> str:
    sections: list[str] = []
    for rel_path in files:
        try:
            content = context.workspace_adapter.read_text(context.run_workspace.workspace_path, rel_path)
        except (UnicodeDecodeError, WorkspaceError):
            sections.append(
                "\n".join(
                    [
                        f"diff --git a/{rel_path} b/{rel_path}",
                        "new file mode 100644",
                        f"--- /dev/null",
                        f"+++ b/{rel_path}",
                        "@@ unreadable model-visible untracked file @@",
                    ]
                )
            )
            continue
        lines = content.splitlines(keepends=True)
        diff_lines = list(
            difflib.unified_diff(
                [],
                lines,
                fromfile="/dev/null",
                tofile=f"b/{rel_path}",
                lineterm="",
            )
        )
        header = [
            f"diff --git a/{rel_path} b/{rel_path}",
            "new file mode 100644",
        ]
        sections.append("\n".join([*header, *diff_lines]))
    return "\n".join(section for section in sections if section)


def _untracked_changed_files(
    context: ToolExecutionContext,
    files: list[str],
) -> list[dict[str, Any]]:
    changed: list[dict[str, Any]] = []
    for rel_path in files:
        try:
            content = context.workspace_adapter.read_text(context.run_workspace.workspace_path, rel_path)
            added_lines = len(content.splitlines())
        except (UnicodeDecodeError, WorkspaceError):
            added_lines = 0
        changed.append(
            {
                "path": rel_path,
                "status": "untracked",
                "added_lines": added_lines,
                "removed_lines": 0,
            }
        )
    return changed


def _join_diff_sections(*sections: str) -> str:
    return "\n".join(section.strip("\n") for section in sections if section.strip())


def _has_forbidden_shell_syntax(command: str) -> bool:
    forbidden_fragments = ["|", ">", "<", "&&", "||", ";", "`", "$", "\n", "&"]
    return any(fragment in command for fragment in forbidden_fragments)


def _command_preview(stdout: str, stderr: str) -> str:
    if stdout and stderr:
        return f"[stdout]\n{stdout}\n\n[stderr]\n{stderr}"
    if stdout:
        return stdout
    if stderr:
        return f"[stderr]\n{stderr}"
    return ""


def _bounded_string(value: Any, *, max_chars: int) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...[truncated]"


def _bounded_string_list(value: Any, *, max_items: int, max_chars: int) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = _bounded_string(item, max_chars=max_chars)
        if not text:
            continue
        items.append(text)
        if len(items) >= max_items:
            break
    return items


def _candidate_file_list(value: Any, *, max_items: int, max_chars: int) -> tuple[list[str], int]:
    files: list[str] = []
    skipped = 0
    for path in _bounded_string_list(value, max_items=max_items * 2, max_chars=max_chars):
        if _is_model_hidden_tool_path(path):
            skipped += 1
            continue
        files.append(path)
        if len(files) >= max_items:
            break
    return files, skipped


def _preview(text: str, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[:limit] + "\n[truncated]"


MinimalToolSpec = ToolDefinition
MinimalToolContext = ToolExecutionContext
MinimalToolExecutor = ToolExecutor
