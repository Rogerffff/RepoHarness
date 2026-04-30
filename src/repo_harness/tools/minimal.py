"""阶段七最小工具执行器。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.errors import WorkspaceError
from repo_harness.permissions import PermissionDecision
from repo_harness.schema_base import stable_hash
from repo_harness.tools.schemas import ToolCall, ToolResult
from repo_harness.trajectory import RunRecorder
from repo_harness.verifier import PytestVerifier
from repo_harness.workspace import LocalWorkspaceAdapter, RunWorkspace

MINIMAL_TOOLS = ["read_file", "edit_file", "run_tests", "git_diff"]


@dataclass(frozen=True)
class MinimalToolSpec:
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


@dataclass
class MinimalToolContext:
    workspace_adapter: LocalWorkspaceAdapter
    run_workspace: RunWorkspace
    verifier: PytestVerifier
    resolved_verifier_plan: ResolvedVerifierPlan
    recorder: RunRecorder
    permission_mode: str = "auto"


class MinimalToolExecutor:
    def validate_input(self, tool_call: ToolCall) -> ToolResult | None:
        if tool_call.tool_name == "read_file":
            path = tool_call.arguments.get("path")
            if not isinstance(path, str) or not path:
                return _tool_result(
                    tool_call,
                    status="error",
                    content="read_file requires a non-empty string path.",
                    error_type="schema_validation_failed",
                )
        elif tool_call.tool_name == "edit_file":
            path = tool_call.arguments.get("path")
            old_text = tool_call.arguments.get("old_text")
            new_text = tool_call.arguments.get("new_text")
            if not isinstance(path, str) or not path:
                return _tool_result(
                    tool_call,
                    status="error",
                    content="edit_file requires a non-empty string path.",
                    error_type="schema_validation_failed",
                )
            if not isinstance(old_text, str) or not isinstance(new_text, str):
                return _tool_result(
                    tool_call,
                    status="error",
                    content="edit_file requires string old_text and new_text.",
                    error_type="schema_validation_failed",
                )
        elif tool_call.tool_name in {"run_tests", "git_diff"}:
            if tool_call.arguments:
                return _tool_result(
                    tool_call,
                    status="error",
                    content=f"{tool_call.tool_name} does not accept arguments in the stage seven shim.",
                    error_type="schema_validation_failed",
                )
        return None

    def check_permission(
        self,
        tool_call: ToolCall,
        context: MinimalToolContext,
    ) -> PermissionDecision:
        normalized_hash = stable_hash(tool_call.arguments)
        tool_spec = build_tool(tool_call.tool_name)
        resolved_paths: list[str] = []
        if tool_call.tool_name in {"read_file", "edit_file"}:
            requested_path = str(tool_call.arguments.get("path", ""))
            try:
                resolved = context.workspace_adapter.resolve_workspace_path(
                    context.run_workspace.workspace_path,
                    requested_path,
                    must_exist=False,
                )
                resolved_paths.append(resolved.as_posix())
            except WorkspaceError as exc:
                return _permission_decision(
                    tool_call,
                    context,
                    decision="deny",
                    reason=str(exc),
                    normalized_input_hash=normalized_hash,
                )
        if context.permission_mode == "plan" and not tool_spec.is_read_only:
            return _permission_decision(
                tool_call,
                context,
                decision="deny",
                reason="permission_mode=plan only allows read-only tools.",
                normalized_input_hash=normalized_hash,
                resolved_paths=resolved_paths,
            )
        if context.permission_mode == "ask" and not tool_spec.is_read_only:
            return _permission_decision(
                tool_call,
                context,
                decision="deny",
                reason="permission_mode=ask requires user confirmation; stage seven run-task is non-interactive.",
                normalized_input_hash=normalized_hash,
                resolved_paths=resolved_paths,
                requires_user_input=True,
                non_interactive_resolution="deny",
            )
        if context.permission_mode == "deny" and not tool_spec.is_read_only:
            return _permission_decision(
                tool_call,
                context,
                decision="deny",
                reason="permission_mode=deny only allows clearly safe read-only tools.",
                normalized_input_hash=normalized_hash,
                resolved_paths=resolved_paths,
            )
        return _permission_decision(
            tool_call,
            context,
            decision="allow",
            reason="Allowed by stage seven minimal permission shim.",
            normalized_input_hash=normalized_hash,
            resolved_paths=resolved_paths,
        )

    def denied_result(self, tool_call: ToolCall, decision: PermissionDecision) -> ToolResult:
        return _tool_result(
            tool_call,
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

    def execute(self, tool_call: ToolCall, context: MinimalToolContext) -> ToolResult:
        if tool_call.tool_name not in MINIMAL_TOOLS:
            return self.invalid_tool_result(tool_call)
        try:
            if tool_call.tool_name == "read_file":
                return self._read_file(tool_call, context)
            if tool_call.tool_name == "edit_file":
                return self._edit_file(tool_call, context)
            if tool_call.tool_name == "run_tests":
                return self._run_tests(tool_call, context)
            if tool_call.tool_name == "git_diff":
                return self._git_diff(tool_call, context)
        except WorkspaceError as exc:
            return _tool_result(
                tool_call,
                status="denied" if "拒绝" in str(exc) or "边界" in str(exc) else "error",
                content=str(exc),
                error_type="permission_denied" if "拒绝" in str(exc) or "边界" in str(exc) else "tool_error",
            )
        except Exception as exc:  # noqa: BLE001 - 工具错误必须回流为 ToolResult
            return _tool_result(tool_call, status="error", content=str(exc), error_type="tool_error")
        return _tool_result(tool_call, status="error", content="Unhandled tool", error_type="tool_error")

    def _read_file(self, tool_call: ToolCall, context: MinimalToolContext) -> ToolResult:
        path = str(tool_call.arguments.get("path", ""))
        content = context.workspace_adapter.read_text(context.run_workspace.workspace_path, path)
        ref = context.recorder.write_artifact("read_file", content)
        return _tool_result(
            tool_call,
            status="ok",
            content=_preview(content),
            artifact_refs=[ref],
            typed={"path": path, "content_hash": stable_hash(content)},
        )

    def _edit_file(self, tool_call: ToolCall, context: MinimalToolContext) -> ToolResult:
        path = str(tool_call.arguments.get("path", ""))
        old_text = tool_call.arguments.get("old_text")
        new_text = tool_call.arguments.get("new_text")
        if not isinstance(old_text, str) or not isinstance(new_text, str):
            return _tool_result(
                tool_call,
                status="error",
                content="edit_file requires string old_text and new_text.",
                error_type="schema_validation_failed",
            )
        content = context.workspace_adapter.read_text(context.run_workspace.workspace_path, path)
        count = content.count(old_text)
        if count != 1:
            return _tool_result(
                tool_call,
                status="error",
                content=f"old_text matched {count} times; expected exactly 1.",
                error_type="input_validation_failed",
            )
        context.workspace_adapter.write_text(
            context.run_workspace.workspace_path,
            path,
            content.replace(old_text, new_text),
        )
        return _tool_result(tool_call, status="ok", content=f"Edited {path}.", typed={"path": path})

    def _run_tests(self, tool_call: ToolCall, context: MinimalToolContext) -> ToolResult:
        result = context.verifier.run_feedback(
            context.run_workspace.workspace_path,
            context.resolved_verifier_plan,
            context.recorder,
        )
        ref = context.recorder.write_json_artifact("feedback_verifier_result", result.model_dump(mode="json"))
        return _tool_result(
            tool_call,
            status="ok",
            content=(
                f"accepted={result.accepted} pass_ratio={result.pass_ratio:.2f} "
                f"fail_to_pass={result.fail_to_pass} pass_to_pass={result.pass_to_pass}"
            ),
            artifact_refs=[ref],
            typed={"verifier_result": result.model_dump(mode="json")},
        )

    def _git_diff(self, tool_call: ToolCall, context: MinimalToolContext) -> ToolResult:
        result = context.workspace_adapter.run_command(
            context.run_workspace.workspace_path,
            "git diff HEAD",
            recorder=context.recorder,
            command_semantics="git_diff",
        )
        return _tool_result(
            tool_call,
            status="ok",
            content=_preview(result.stdout_preview),
            artifact_refs=[result.output_artifact_ref] if result.output_artifact_ref else [],
            typed={"exit_code": result.exit_code},
        )


def _tool_result(
    tool_call: ToolCall,
    *,
    status: str,
    content: str,
    error_type: str | None = None,
    artifact_refs: list[object] | None = None,
    typed: dict[str, object] | None = None,
) -> ToolResult:
    return ToolResult(
        tool_result_id=f"{tool_call.tool_call_id}_result",
        tool_call_id=tool_call.tool_call_id,
        tool_name=tool_call.tool_name,
        requested_tool_name=tool_call.tool_name,
        effective_tool_name=tool_call.tool_name,
        requested_arguments=tool_call.arguments,
        normalized_arguments=tool_call.arguments,
        effective_arguments=tool_call.arguments,
        normalized_input_hash=stable_hash(tool_call.arguments),
        status=status,  # type: ignore[arg-type]
        content_preview=content,
        error_type=error_type,
        artifact_refs=artifact_refs or [],  # type: ignore[arg-type]
        typed=typed or {},
    )


def _permission_decision(
    tool_call: ToolCall,
    context: MinimalToolContext,
    *,
    decision: str,
    reason: str,
    normalized_input_hash: str,
    resolved_paths: list[str] | None = None,
    requires_user_input: bool = False,
    non_interactive_resolution: str | None = None,
) -> PermissionDecision:
    return PermissionDecision(
        decision_id=f"{tool_call.tool_call_id}_permission",
        tool_call_id=tool_call.tool_call_id,
        tool_name=tool_call.tool_name,
        requested_tool_name=tool_call.tool_name,
        effective_tool_name=tool_call.tool_name,
        decision=decision,  # type: ignore[arg-type]
        mode=context.permission_mode,  # type: ignore[arg-type]
        matched_rule="stage_07_minimal_workspace_boundary",
        reason=reason,
        normalized_input_hash=normalized_input_hash,
        resolved_paths=resolved_paths or [],
        requires_user_input=requires_user_input,
        non_interactive_resolution=non_interactive_resolution,
    )


def build_tool(name: str) -> MinimalToolSpec:
    if name == "read_file":
        return MinimalToolSpec(
            name=name,
            tool_version="repo_harness_read_file_v0",
            model_visible_description="Read a UTF-8 text file inside the workspace.",
            model_visible_prompt="Use read_file with a workspace-relative path.",
            input_schema={"type": "object", "required": ["path"]},
            output_schema={"type": "object", "properties": {"content_preview": {"type": "string"}}},
            max_result_size=4000,
            is_read_only=True,
            is_concurrency_safe=True,
        )
    if name == "edit_file":
        return MinimalToolSpec(
            name=name,
            tool_version="repo_harness_edit_file_v0",
            model_visible_description="Replace one exact text span in a UTF-8 file inside the workspace.",
            model_visible_prompt="Use edit_file with path, old_text, and new_text.",
            input_schema={"type": "object", "required": ["path", "old_text", "new_text"]},
            output_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            max_result_size=4000,
        )
    if name == "run_tests":
        return MinimalToolSpec(
            name=name,
            tool_version="repo_harness_run_tests_v0",
            model_visible_description="Run the task verifier as intermediate feedback.",
            model_visible_prompt="Use run_tests without arguments.",
            input_schema={"type": "object", "additionalProperties": False},
            output_schema={"type": "object", "properties": {"accepted": {"type": "boolean"}}},
            max_result_size=4000,
        )
    if name == "git_diff":
        return MinimalToolSpec(
            name=name,
            tool_version="repo_harness_git_diff_v0",
            model_visible_description="Show the current workspace diff.",
            model_visible_prompt="Use git_diff without arguments.",
            input_schema={"type": "object", "additionalProperties": False},
            output_schema={"type": "object", "properties": {"diff_preview": {"type": "string"}}},
            max_result_size=4000,
            is_read_only=True,
            is_concurrency_safe=True,
        )
    raise KeyError(f"Unknown stage seven tool: {name}")


def _preview(text: str, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[:limit] + "\n[truncated]"
