"""第一版工具系统和内置工具。"""

from __future__ import annotations

import json
import hashlib
import difflib
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.errors import WorkspaceError
from repo_harness.permissions import PermissionContext, PermissionDecision, PermissionSystem
from repo_harness.schema_base import stable_hash
from repo_harness.tasks.command_policy import evaluate_model_bash_command
from repo_harness.tools.schemas import ToolCall, ToolResult
from repo_harness.trajectory import ArtifactRef, RunRecorder
from repo_harness.verifier import PytestVerifier
from repo_harness.workspace import RunWorkspace, WorkspaceAdapter

DEFAULT_TOOL_ORDER = [
    "list_files",
    "read_file",
    "grep",
    "edit_file",
    "create_file",
    "bash",
    "run_tests",
    "git_diff",
]
MINIMAL_TOOLS = DEFAULT_TOOL_ORDER
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
            if normalized.effective_tool_name == "read_file":
                return self._read_file(tool_call, normalized, context)
            if normalized.effective_tool_name == "grep":
                return self._grep(tool_call, normalized, context)
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
        elif requested == "grep":
            query = args.get("query", args.get("pattern"))
            normalized_args = {
                "query": query,
                "root": args.get("path", args.get("root", ".")),
                "mode": args.get("mode", "literal"),
                "max_matches": int(args.get("max_matches", GREP_MAX_MATCHES)),
                "offset": int(args.get("offset", 0)),
                "context_lines": int(args.get("context_lines", 0)),
            }
            if "glob" in args:
                normalized_args["glob"] = args["glob"]
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
        max_entries = max(1, min(int(normalized.normalized_arguments.get("max_entries", LIST_FILES_DEFAULT_MAX_ENTRIES)), 1000))
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
        skipped_hidden_count = 0
        skipped_symlink_count = 0
        for rel_path in files:
            visible, reason = _model_visible_path_status(context, rel_path)
            if visible:
                visible_files.append(rel_path)
                continue
            if reason == "symlink_outside_workspace":
                skipped_symlink_count += 1
            else:
                skipped_hidden_count += 1
        page = visible_files[offset : offset + max_entries]
        next_offset = offset + len(page) if offset + len(page) < len(visible_files) else None
        truncated = next_offset is not None
        ref = context.recorder.write_json_artifact(
            "list_files",
            {
                "root": root,
                "glob": glob,
                "files": visible_files,
                "offset": offset,
                "max_entries": max_entries,
                "returned_files": page,
                "truncated": truncated,
                "next_offset": next_offset,
                "skipped_hidden_count": skipped_hidden_count,
                "skipped_symlink_count": skipped_symlink_count,
            },
        )
        preview = "\n".join(page) if page else "No files matched."
        if truncated:
            preview += (
                f"\n[truncated] call list_files(path={root!r}, offset={next_offset}, "
                f"max_entries={max_entries}) for the next page."
            )
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(preview, context.output_limits.max_tool_output_chars),
            artifact_refs=[ref],
            typed={
                "files": page,
                "returned_count": len(page),
                "total_visible_count": len(visible_files),
                "match_count": len(visible_files),
                "offset": offset,
                "max_entries": max_entries,
                "truncated": truncated,
                "next_offset": next_offset,
                "skipped_hidden_count": skipped_hidden_count,
                "skipped_symlink_count": skipped_symlink_count,
                "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
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
                typed={"path": path, "visibility_reason": visibility_reason},
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
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(preview, context.output_limits.max_tool_output_chars),
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
        mode = str(normalized.normalized_arguments.get("mode", "literal"))
        glob = normalized.normalized_arguments.get("glob")
        offset = max(0, int(normalized.normalized_arguments.get("offset", 0)))
        max_matches = max(1, min(int(normalized.normalized_arguments.get("max_matches", GREP_MAX_MATCHES)), GREP_MAX_MATCHES))
        context_lines = max(0, min(int(normalized.normalized_arguments.get("context_lines", 0)), 20))
        try:
            payload = _grep_python(
                context=context,
                root=root,
                query=query,
                mode=mode,
                glob=str(glob) if glob is not None else None,
                offset=offset,
                max_matches=max_matches,
                context_lines=context_lines,
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
                },
            )
        except WorkspaceError as exc:
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=str(exc),
                error_type="tool_execution_failed",
                typed={"query": query, "mode": mode, "resolved_max_output_chars": context.output_limits.max_tool_output_chars},
            )
        matches = [str(match) for match in payload.get("matches", []) if isinstance(match, str)]
        recovery_hint = None
        if not matches and mode == "literal" and _looks_like_regex(query):
            recovery_hint = "No literal matches. The query looks like a regular expression; retry with mode='regex'."
        if payload.get("truncated") and payload.get("next_offset") is None:
            recovery_hint = "Search reached the scanned-file limit; narrow root, glob, or query instead of paginating."
        ref = context.recorder.write_json_artifact(
            "grep_results",
            {
                "query": query,
                "mode": mode,
                "glob": glob,
                "matches": matches,
                "offset": offset,
                "max_matches": max_matches,
                "context_lines": context_lines,
                "scanned_file_count": int(payload.get("scanned_file_count") or 0),
                "skipped_hidden_path_count": int(payload.get("skipped_hidden_path_count") or 0),
                "skipped_hidden_count": int(payload.get("skipped_hidden_count") or 0),
                "skipped_symlink_count": int(payload.get("skipped_symlink_count") or 0),
                "matched_file_count": int(payload.get("matched_file_count") or 0),
                "truncated": bool(payload.get("truncated")),
                "next_offset": payload.get("next_offset"),
                "engine": payload.get("engine"),
            },
        )
        preview = "\n".join(matches) if matches else "No matches."
        if payload.get("truncated") and payload.get("next_offset") is not None:
            preview += (
                f"\n[truncated] call grep(query={query!r}, mode={mode!r}, "
                f"offset={payload.get('next_offset')}, max_matches={max_matches}) for more matches."
            )
        elif payload.get("truncated"):
            preview += f"\n[truncated] {recovery_hint}"
        elif recovery_hint:
            preview += f"\n{recovery_hint}"
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(preview, context.output_limits.max_tool_output_chars),
            artifact_refs=[ref],
            typed={
                "query": query,
                "mode": mode,
                "glob": glob,
                "match_count": len(matches),
                "total_match_count": int(payload.get("total_match_count") or len(matches)),
                "scanned_file_count": int(payload.get("scanned_file_count") or 0),
                "skipped_hidden_path_count": int(payload.get("skipped_hidden_path_count") or 0),
                "skipped_hidden_count": int(payload.get("skipped_hidden_count") or 0),
                "skipped_symlink_count": int(payload.get("skipped_symlink_count") or 0),
                "matched_file_count": int(payload.get("matched_file_count") or 0),
                "truncated": bool(payload.get("truncated")),
                "next_offset": payload.get("next_offset"),
                "offset": offset,
                "max_matches": max_matches,
                "context_lines": context_lines,
                "recovery_hint": recovery_hint,
                "engine": payload.get("engine"),
                "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
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
                    "recovery_hint": "Call read_file again, copy the raw_content_preview without line numbers, then retry edit_file.",
                    "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
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
                "resolved_max_output_chars": context.output_limits.max_tool_output_chars,
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
            },
        )


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry([build_tool(name) for name in DEFAULT_TOOL_ORDER])


def build_tool(name: str) -> ToolDefinition:
    definitions = {
        "list_files": ToolDefinition(
            name="list_files",
            tool_version="repo_harness_list_files_v0",
            model_visible_description=(
                "List model-visible files inside the workspace with pagination. "
                "Hidden dependency, credential, build, cache, and version-control paths are excluded."
            ),
            model_visible_prompt=(
                "Use list_files with optional path/root, glob, offset, and max_entries. "
                "For symbols or text, prefer grep first and then read_file on the relevant file."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Alias for root; workspace-relative."},
                    "root": {"type": "string", "description": "Workspace-relative directory or file."},
                    "glob": {"type": "string", "description": "Optional fnmatch-style file glob."},
                    "pattern": {"type": "string", "description": "Legacy alias for glob."},
                    "offset": {"type": "integer", "description": "Zero-based result offset for pagination."},
                    "max_entries": {"type": "integer", "description": "Maximum returned entries for this page."},
                    "kind": {"type": "string", "enum": ["file"], "description": "Currently only file entries are returned."},
                },
            },
            output_schema={"type": "object", "properties": {"files": {"type": "array"}}},
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
        "grep": ToolDefinition(
            name="grep",
            tool_version="repo_harness_grep_v0",
            model_visible_description=(
                "Search model-visible workspace files. Default mode is literal substring; "
                "set mode='regex' for regular expressions. Results are paginated and hidden paths are excluded."
            ),
            model_visible_prompt=(
                "Use grep with query and optional root/path, mode, glob, offset, max_matches, "
                "and context_lines. If a literal search for a regex-like query returns no matches, retry with mode='regex'."
            ),
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "description": "Literal substring or regular expression to find."},
                    "pattern": {"type": "string", "description": "Legacy alias for query."},
                    "mode": {"type": "string", "enum": ["literal", "regex"], "description": "Search mode; defaults to literal."},
                    "root": {"type": "string", "description": "Optional workspace-relative search root."},
                    "path": {"type": "string", "description": "Alias for root; workspace-relative."},
                    "glob": {"type": "string", "description": "Optional fnmatch-style file glob."},
                    "max_matches": {"type": "integer", "description": "Maximum returned matches for this page."},
                    "offset": {"type": "integer", "description": "Zero-based match offset for pagination."},
                    "context_lines": {"type": "integer", "description": "Line context before and after each match."},
                },
            },
            output_schema={"type": "object", "properties": {"matches": {"type": "array"}}},
            max_result_size=DEFAULT_RESOLVED_MAX_OUTPUT_CHARS,
            is_read_only=True,
            is_concurrency_safe=True,
        ),
        "edit_file": ToolDefinition(
            name="edit_file",
            tool_version="repo_harness_edit_file_v0",
            model_visible_description="Replace exact text in an existing UTF-8 file.",
            model_visible_prompt=(
                "Use edit_file with path, old_text, and new_text. "
                "Prefer passing expected_content_hash from read_file. Do not include read_file line-number prefixes in old_text."
            ),
            input_schema={
                "type": "object",
                "required": ["path", "old_text", "new_text"],
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                    "expected_content_hash": {"type": "string", "description": "sha256 from read_file content_hash."},
                    "expected_content_sha256": {"type": "string", "description": "Legacy alias for expected_content_hash."},
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
            model_visible_prompt="Use git_diff with optional workspace-relative path.",
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
        "read_file.path": (str, True),
        "read_file.start_line": (int, False),
        "read_file.end_line": (int, False),
        "read_file.offset": (int, False),
        "read_file.limit": (int, False),
        "grep.query": (str, True),
        "grep.pattern": (str, False),
        "grep.path": (str, False),
        "grep.root": (str, False),
        "grep.mode": (str, False),
        "grep.glob": (str, False),
        "grep.max_matches": (int, False),
        "grep.offset": (int, False),
        "grep.context_lines": (int, False),
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
            tool_name in {"read_file", "list_files", "grep"}
            and field_name in {"start_line", "end_line", "offset", "limit", "max_entries", "max_matches", "context_lines"}
            and field_name in args
            and args[field_name] < (
                0
                if (
                    (field_name == "offset" and tool_name in {"list_files", "grep"})
                    or (field_name == "context_lines" and tool_name == "grep")
                )
                else 1
            )
        ):
            expected = (
                "non-negative integer"
                if (
                    (field_name == "offset" and tool_name in {"list_files", "grep"})
                    or (field_name == "context_lines" and tool_name == "grep")
                )
                else "positive integer"
            )
            return _issue(field_name, expected, args[field_name], retryable=True)
        if tool_name == "grep" and field_name == "mode" and field_name in args and args[field_name] not in {"literal", "regex"}:
            return _issue(field_name, "literal|regex", args[field_name], retryable=True)
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
    return expected_type.__name__


def _tool_result(
    tool_call: ToolCall,
    *,
    status: str,
    content: str,
    normalized: NormalizedToolRequest | None = None,
    error_type: str | None = None,
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
    host_candidate = Path(context.run_workspace.workspace_path) / rel_path
    if host_candidate.is_symlink():
        try:
            target_rel = host_candidate.resolve().relative_to(Path(context.run_workspace.workspace_path).resolve())
        except ValueError:
            return False, "symlink_outside_workspace"
        if _is_model_hidden_tool_path(target_rel.as_posix()):
            return False, "symlink_target_hidden_path"
    try:
        context.workspace_adapter.resolve_workspace_path(
            context.run_workspace.workspace_path,
            rel_path,
            must_exist=True,
        )
    except WorkspaceError as exc:
        if "符号链接" in str(exc) or "symlink" in str(exc).lower():
            return False, "symlink_outside_workspace"
        return False, "workspace_boundary_or_missing"
    return True, None


def _looks_like_numbered_read_file_snippet(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    prefixed = sum(1 for line in lines[:5] if re.match(r"^\s*\d+\s*\|\s?", line))
    return prefixed >= max(1, min(len(lines[:5]), 2))


def _looks_like_regex(query: str) -> bool:
    return bool(re.search(r"(?<!\\)(\.\*|\[[^\]]+\]|\([^)]*[|?+*][^)]*\)|\\d|\\w|\\s|\^|\$)", query))


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
) -> dict[str, Any]:
    if mode not in {"literal", "regex"}:
        raise WorkspaceError("grep mode must be literal or regex.")
    pattern = re.compile(query) if mode == "regex" else None
    all_matches: list[dict[str, Any]] = []
    searched_file_count = 0
    skipped_hidden_count = 0
    skipped_symlink_count = 0
    matched_files: set[str] = set()
    files = context.workspace_adapter.list_files(
        context.run_workspace.workspace_path,
        root,
        pattern=glob,
    )
    for rel_path in files[:GREP_MAX_SCANNED_FILES]:
        visible, reason = _model_visible_path_status(context, rel_path)
        if not visible:
            if reason == "symlink_outside_workspace":
                skipped_symlink_count += 1
            else:
                skipped_hidden_count += 1
            continue
        searched_file_count += 1
        try:
            text = _read_model_visible_text_for_grep(context, rel_path)
        except (UnicodeDecodeError, ValueError, WorkspaceError):
            continue
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
    if len(files) > GREP_MAX_SCANNED_FILES:
        truncated_by_scan_limit = True
    else:
        truncated_by_scan_limit = False
    page = all_matches[offset : offset + max_matches]
    next_offset = offset + len(page) if offset + len(page) < len(all_matches) else None
    return {
        "matches": [entry["rendered"] for entry in page],
        "total_match_count": len(all_matches),
        "scanned_file_count": searched_file_count,
        "searched_file_count": searched_file_count,
        "matched_file_count": len(matched_files),
        "skipped_hidden_count": skipped_hidden_count,
        "skipped_hidden_path_count": skipped_hidden_count,
        "skipped_symlink_count": skipped_symlink_count,
        "truncated": bool(next_offset is not None or truncated_by_scan_limit),
        "next_offset": next_offset,
        "engine": "python_fallback",
    }


def _read_model_visible_text_for_grep(context: ToolExecutionContext, rel_path: str) -> str:
    workspace = Path(context.run_workspace.workspace_path).resolve()
    candidate = (workspace / rel_path).resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError as exc:
        raise WorkspaceError(f"路径越过 workspace 边界：{rel_path}") from exc
    if not candidate.is_file():
        raise WorkspaceError(f"路径不是文件：{rel_path}")
    try:
        return candidate.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkspaceError(f"无法读取文件：{rel_path}") from exc


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


def _preview(text: str, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[:limit] + "\n[truncated]"


MinimalToolSpec = ToolDefinition
MinimalToolContext = ToolExecutionContext
MinimalToolExecutor = ToolExecutor
