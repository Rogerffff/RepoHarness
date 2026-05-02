"""第一版工具系统和内置工具。"""

from __future__ import annotations

import fnmatch
import json
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.errors import WorkspaceError
from repo_harness.permissions import PermissionContext, PermissionDecision, PermissionSystem
from repo_harness.schema_base import stable_hash
from repo_harness.tasks.command_policy import is_recognized_test_command
from repo_harness.tools.schemas import ToolCall, ToolResult
from repo_harness.trajectory import ArtifactRef, RunRecorder
from repo_harness.verifier import PytestVerifier
from repo_harness.workspace import LocalWorkspaceAdapter, RunWorkspace

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
    max_tool_output_chars: int = 12000


@dataclass(frozen=True)
class ToolPolicy:
    tool_order: list[str] = field(default_factory=lambda: list(DEFAULT_TOOL_ORDER))
    tool_policy_version: str = "repo_harness_tool_policy_v0"


@dataclass
class ToolExecutionContext:
    run_id: str
    task_id: str
    workspace_facade: LocalWorkspaceAdapter
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
    def workspace_adapter(self) -> LocalWorkspaceAdapter:
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
            typed={"permission_decision": decision.model_dump(mode="json")},
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
            normalized_args = {"root": args.get("path", args.get("root", "."))}
            if "pattern" in args:
                normalized_args["pattern"] = args["pattern"]
            effective_args = dict(normalized_args)
        elif requested == "read_file":
            normalized_args = {"path": args["path"]}
            if "start_line" in args:
                normalized_args["start_line"] = args["start_line"]
            if "end_line" in args:
                normalized_args["end_line"] = args["end_line"]
            effective_args = dict(normalized_args)
        elif requested == "grep":
            normalized_args = {
                "query": args["query"],
                "root": args.get("path", args.get("root", ".")),
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
            effective_args = dict(normalized_args)
        elif requested == "create_file":
            normalized_args = {"path": args["path"], "content": args["content"]}
            effective_args = dict(normalized_args)
        elif requested == "bash":
            command = str(args["command"]).strip()
            cwd = str(args.get("cwd", "."))
            requested_timeout = int(args.get("timeout_sec", 30))
            timeout = _clamp_command_timeout(requested_timeout, context)
            requested_cwd = cwd
            normalized_args = {
                "command": command,
                "cwd": cwd,
                "timeout_sec": timeout,
            }
            if timeout != requested_timeout:
                normalized_args["requested_timeout_sec"] = requested_timeout
                normalized_args["timeout_clamped_to_sec"] = timeout
            if _is_test_command(command, context.permission_context.test_command):
                effective = "run_tests"
                route_reason = "recognized_task_test_command"
                effective_args = {}
            else:
                effective_args = dict(normalized_args)
                effective_args["effective_cwd"] = effective_cwd
        elif requested in {"run_tests", "git_diff"}:
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
        root = context.workspace_adapter.resolve_workspace_path(
            context.run_workspace.workspace_path,
            str(normalized.normalized_arguments["root"]),
            must_exist=True,
        )
        pattern = normalized.normalized_arguments.get("pattern")
        match_all = pattern in {None, "", "**/*"}
        workspace = Path(context.run_workspace.workspace_path).resolve()
        files: list[str] = []
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(workspace).as_posix()
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if context.workspace_adapter.is_sensitive_relative_path(rel):
                continue
            if path.is_file() and (match_all or fnmatch.fnmatch(rel, str(pattern))):
                files.append(rel)
        ref = context.recorder.write_json_artifact("list_files", {"files": files})
        preview = "\n".join(files) if files else "No files matched."
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(preview, context.output_limits.max_tool_output_chars),
            artifact_refs=[ref],
            typed={"files": files[:100], "match_count": len(files)},
        )

    def _read_file(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        path = str(normalized.normalized_arguments["path"])
        content = context.workspace_adapter.read_text(context.run_workspace.workspace_path, path)
        content_hash = stable_hash(content)
        context.file_state_cache[path] = content_hash
        visible = _slice_text(
            content,
            normalized.normalized_arguments.get("start_line"),
            normalized.normalized_arguments.get("end_line"),
        )
        ref = context.recorder.write_artifact("read_file", content)
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(visible, context.output_limits.max_tool_output_chars),
            artifact_refs=[ref],
            typed={"path": path, "content_hash": content_hash},
        )

    def _grep(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        query = str(normalized.normalized_arguments["query"])
        root = str(normalized.normalized_arguments["root"])
        matches = _python_grep(context, root, query)
        ref = context.recorder.write_json_artifact("grep_results", {"query": query, "matches": matches})
        preview = "\n".join(matches) if matches else "No matches."
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(preview, context.output_limits.max_tool_output_chars),
            artifact_refs=[ref],
            typed={"query": query, "match_count": len(matches)},
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
        if expected_hash is not None and expected_hash != stable_hash(content):
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content="expected_content_hash does not match current file content.",
                error_type="stale_file_state",
            )
        count = content.count(old_text)
        if count == 0 or (count > 1 and not replace_all):
            return _tool_result(
                tool_call,
                normalized=normalized,
                status="error",
                content=f"old_text matched {count} times; expected exactly 1 unless replace_all=true.",
                error_type="input_validation_failed",
            )
        updated = content.replace(old_text, new_text) if replace_all else content.replace(old_text, new_text, 1)
        context.workspace_adapter.write_text(context.run_workspace.workspace_path, path, updated)
        context.file_state_cache[path] = stable_hash(updated)
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=f"Edited {path}.",
            typed={"path": path, "replacement_count": count if replace_all else 1},
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
        context.file_state_cache[path] = stable_hash(content)
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=f"Created {path}.",
            typed={"path": path, "content_hash": stable_hash(content)},
        )

    def _bash(
        self,
        tool_call: ToolCall,
        normalized: NormalizedToolRequest,
        context: ToolExecutionContext,
    ) -> ToolResult:
        command = str(normalized.normalized_arguments["command"])
        cwd = _resolve_cwd(context, str(normalized.normalized_arguments["cwd"]))
        result = context.workspace_adapter.run_command(
            cwd,
            command,
            timeout_sec=float(normalized.normalized_arguments["timeout_sec"]),
            recorder=context.recorder,
            command_semantics="bash_diagnostic",
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
        result = context.workspace_adapter.run_command(
            context.run_workspace.workspace_path,
            "git diff HEAD",
            recorder=context.recorder,
            command_semantics="git_diff",
        )
        return _tool_result(
            tool_call,
            normalized=normalized,
            status="ok",
            content=_preview(result.stdout_preview, context.output_limits.max_tool_output_chars),
            artifact_refs=[result.output_artifact_ref] if result.output_artifact_ref else [],
            typed={"diff_preview": result.stdout_preview, "exit_code": result.exit_code},
        )


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry([build_tool(name) for name in DEFAULT_TOOL_ORDER])


def build_tool(name: str) -> ToolDefinition:
    definitions = {
        "list_files": ToolDefinition(
            name="list_files",
            tool_version="repo_harness_list_files_v0",
            model_visible_description="List files inside the workspace.",
            model_visible_prompt="Use list_files with optional path and pattern.",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "pattern": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"files": {"type": "array"}}},
            max_result_size=4000,
            is_read_only=True,
            is_concurrency_safe=True,
        ),
        "read_file": ToolDefinition(
            name="read_file",
            tool_version="repo_harness_read_file_v0",
            model_visible_description="Read a UTF-8 text file inside the workspace.",
            model_visible_prompt="Use read_file with a workspace-relative path.",
            input_schema={"type": "object", "required": ["path"]},
            output_schema={"type": "object", "properties": {"content_preview": {"type": "string"}}},
            max_result_size=4000,
            is_read_only=True,
            is_concurrency_safe=True,
        ),
        "grep": ToolDefinition(
            name="grep",
            tool_version="repo_harness_grep_v0",
            model_visible_description="Search text inside workspace files.",
            model_visible_prompt="Use grep with query and optional path.",
            input_schema={"type": "object", "required": ["query"]},
            output_schema={"type": "object", "properties": {"matches": {"type": "array"}}},
            max_result_size=4000,
            is_read_only=True,
            is_concurrency_safe=True,
        ),
        "edit_file": ToolDefinition(
            name="edit_file",
            tool_version="repo_harness_edit_file_v0",
            model_visible_description="Replace exact text in an existing UTF-8 file.",
            model_visible_prompt="Use edit_file with path, old_text, and new_text.",
            input_schema={"type": "object", "required": ["path", "old_text", "new_text"]},
            output_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            max_result_size=4000,
        ),
        "create_file": ToolDefinition(
            name="create_file",
            tool_version="repo_harness_create_file_v0",
            model_visible_description="Create a new UTF-8 file inside the workspace.",
            model_visible_prompt="Use create_file with path and content. Existing files are rejected.",
            input_schema={"type": "object", "required": ["path", "content"]},
            output_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            max_result_size=4000,
        ),
        "bash": ToolDefinition(
            name="bash",
            tool_version="repo_harness_bash_v0",
            model_visible_description="Run a restricted diagnostic command inside the workspace.",
            model_visible_prompt="Use bash with command, optional cwd, and optional timeout_sec.",
            input_schema={"type": "object", "required": ["command"]},
            output_schema={"type": "object", "properties": {"stdout_preview": {"type": "string"}}},
            max_result_size=4000,
        ),
        "run_tests": ToolDefinition(
            name="run_tests",
            tool_version="repo_harness_run_tests_v0",
            model_visible_description="Run the task verifier as intermediate feedback.",
            model_visible_prompt="Use run_tests without arguments.",
            input_schema={"type": "object", "additionalProperties": False},
            output_schema={"type": "object", "properties": {"accepted": {"type": "boolean"}}},
            max_result_size=4000,
        ),
        "git_diff": ToolDefinition(
            name="git_diff",
            tool_version="repo_harness_git_diff_v0",
            model_visible_description="Show the current workspace diff.",
            model_visible_prompt="Use git_diff without arguments.",
            input_schema={"type": "object", "additionalProperties": False},
            output_schema={"type": "object", "properties": {"diff_preview": {"type": "string"}}},
            max_result_size=4000,
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
        "read_file.path": (str, True),
        "read_file.start_line": (int, False),
        "read_file.end_line": (int, False),
        "grep.query": (str, True),
        "grep.path": (str, False),
        "grep.root": (str, False),
        "edit_file.path": (str, True),
        "edit_file.old_text": (str, True),
        "edit_file.new_text": (str, True),
        "edit_file.replace_all": (bool, False),
        "edit_file.expected_content_hash": (str, False),
        "create_file.path": (str, True),
        "create_file.content": (str, True),
        "bash.command": (str, True),
        "bash.cwd": (str, False),
        "bash.timeout_sec": (int, False),
    }
    if tool_name in {"run_tests", "git_diff"} and args:
        field = next(iter(args))
        return _issue(field, "no arguments", args[field], retryable=True)
    tool_rules = {key.split(".", 1)[1]: value for key, value in rules.items() if key.startswith(f"{tool_name}.")}
    for field_name, (expected_type, required) in tool_rules.items():
        if required and field_name not in args:
            return _issue(field_name, _type_name(expected_type), None, retryable=True)
        if field_name in args and not _is_exact_type(args[field_name], expected_type):
            return _issue(field_name, _type_name(expected_type), args[field_name], retryable=True)
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


def _is_test_command(command: str, configured_test_command: str) -> bool:
    return is_recognized_test_command(command, configured_test_command)


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


def _python_grep(context: ToolExecutionContext, root: str, query: str) -> list[str]:
    root_path = context.workspace_adapter.resolve_workspace_path(
        context.run_workspace.workspace_path,
        root,
        must_exist=True,
    )
    workspace = Path(context.run_workspace.workspace_path).resolve()
    matches: list[str] = []
    for path in sorted(root_path.rglob("*") if root_path.is_dir() else [root_path]):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            rel_path = path.relative_to(workspace).as_posix()
            if context.workspace_adapter.is_sensitive_relative_path(rel_path):
                continue
            text = context.workspace_adapter.read_text(context.run_workspace.workspace_path, rel_path)
        except (UnicodeDecodeError, ValueError, WorkspaceError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if query in line:
                matches.append(f"{rel_path}:{line_number}:{line}")
    return matches


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
