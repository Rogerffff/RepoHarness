"""第一版权限系统。"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_harness.errors import WorkspaceError
from repo_harness.permissions.schemas import PermissionDecision
from repo_harness.schema_base import stable_hash


@dataclass(frozen=True)
class PermissionContext:
    mode: str = "auto"
    network_policy: str = "deny_agent_run"
    test_command: str = "pytest -q"


class PermissionSystem:
    """确定一次已规范化工具调用是否允许执行。"""

    def check(
        self,
        *,
        tool_call_id: str,
        requested_tool_name: str,
        effective_tool_name: str,
        tool_definition: Any,
        requested_arguments: dict[str, Any],
        normalized_arguments: dict[str, Any],
        permission_context: PermissionContext,
        workspace_facade: Any,
        workspace_path: str,
    ) -> PermissionDecision:
        resolved_paths: list[str] = []
        requested_cwd = normalized_arguments.get("cwd")
        effective_cwd = None
        for field_name in _path_fields(effective_tool_name):
            if field_name not in normalized_arguments:
                continue
            requested_path = str(normalized_arguments[field_name])
            try:
                resolved = workspace_facade.resolve_workspace_path(
                    workspace_path,
                    requested_path,
                    must_exist=field_name in {"path", "root"} and effective_tool_name in {
                        "read_file",
                        "grep",
                        "list_files",
                    },
                )
            except WorkspaceError as exc:
                return self._decision(
                    tool_call_id=tool_call_id,
                    requested_tool_name=requested_tool_name,
                    effective_tool_name=effective_tool_name,
                    permission_context=permission_context,
                    requested_arguments=requested_arguments,
                    normalized_arguments=normalized_arguments,
                    decision="deny",
                    reason=str(exc),
                    matched_rule="workspace_boundary_or_sensitive_path",
                    resolved_paths=resolved_paths,
                    requested_cwd=str(requested_cwd) if requested_cwd is not None else None,
                    effective_cwd=effective_cwd,
                )
            resolved_paths.append(resolved.as_posix())
            if field_name == "cwd":
                effective_cwd = resolved.as_posix()

        if effective_tool_name == "bash":
            command = str(normalized_arguments.get("command", ""))
            command_issue = _deny_reason_for_bash(command, workspace_facade, workspace_path)
            if command_issue is not None:
                return self._decision(
                    tool_call_id=tool_call_id,
                    requested_tool_name=requested_tool_name,
                    effective_tool_name=effective_tool_name,
                    permission_context=permission_context,
                    requested_arguments=requested_arguments,
                    normalized_arguments=normalized_arguments,
                    decision="deny",
                    reason=command_issue,
                    matched_rule="bash_command_safety",
                    resolved_paths=resolved_paths,
                    command_category="diagnostic",
                    requested_cwd=str(requested_cwd) if requested_cwd is not None else None,
                    effective_cwd=effective_cwd,
                )

        read_only = bool(getattr(tool_definition, "is_read_only", False))
        if permission_context.mode == "plan" and not read_only:
            return self._decision(
                tool_call_id=tool_call_id,
                requested_tool_name=requested_tool_name,
                effective_tool_name=effective_tool_name,
                permission_context=permission_context,
                requested_arguments=requested_arguments,
                normalized_arguments=normalized_arguments,
                decision="deny",
                reason="permission_mode=plan only allows read-only tools.",
                matched_rule="permission_mode_plan",
                resolved_paths=resolved_paths,
                requested_cwd=str(requested_cwd) if requested_cwd is not None else None,
                effective_cwd=effective_cwd,
            )
        if permission_context.mode == "ask" and not read_only:
            return self._decision(
                tool_call_id=tool_call_id,
                requested_tool_name=requested_tool_name,
                effective_tool_name=effective_tool_name,
                permission_context=permission_context,
                requested_arguments=requested_arguments,
                normalized_arguments=normalized_arguments,
                decision="deny",
                reason="permission_mode=ask requires user confirmation; this runner is non-interactive.",
                matched_rule="permission_mode_ask_non_interactive",
                resolved_paths=resolved_paths,
                requested_cwd=str(requested_cwd) if requested_cwd is not None else None,
                effective_cwd=effective_cwd,
                requires_user_input=True,
                non_interactive_resolution="deny",
            )
        if permission_context.mode == "deny" and not read_only:
            return self._decision(
                tool_call_id=tool_call_id,
                requested_tool_name=requested_tool_name,
                effective_tool_name=effective_tool_name,
                permission_context=permission_context,
                requested_arguments=requested_arguments,
                normalized_arguments=normalized_arguments,
                decision="deny",
                reason="permission_mode=deny only allows clearly safe read-only tools.",
                matched_rule="permission_mode_deny",
                resolved_paths=resolved_paths,
                requested_cwd=str(requested_cwd) if requested_cwd is not None else None,
                effective_cwd=effective_cwd,
            )

        return self._decision(
            tool_call_id=tool_call_id,
            requested_tool_name=requested_tool_name,
            effective_tool_name=effective_tool_name,
            permission_context=permission_context,
            requested_arguments=requested_arguments,
            normalized_arguments=normalized_arguments,
            decision="allow",
            reason="Allowed by permission mode fallback after safety checks.",
            matched_rule=f"permission_mode_{permission_context.mode}",
            resolved_paths=resolved_paths,
            command_category=_command_category(effective_tool_name),
            requested_cwd=str(requested_cwd) if requested_cwd is not None else None,
            effective_cwd=effective_cwd,
        )

    def _decision(
        self,
        *,
        tool_call_id: str,
        requested_tool_name: str,
        effective_tool_name: str,
        permission_context: PermissionContext,
        requested_arguments: dict[str, Any],
        normalized_arguments: dict[str, Any],
        decision: str,
        reason: str,
        matched_rule: str,
        resolved_paths: list[str],
        command_category: str | None = None,
        requested_cwd: str | None = None,
        effective_cwd: str | None = None,
        requires_user_input: bool = False,
        non_interactive_resolution: str | None = None,
    ) -> PermissionDecision:
        return PermissionDecision(
            decision_id=f"{tool_call_id}_permission",
            tool_call_id=tool_call_id,
            tool_name=effective_tool_name,
            requested_tool_name=requested_tool_name,
            effective_tool_name=effective_tool_name,
            decision=decision,  # type: ignore[arg-type]
            mode=permission_context.mode,  # type: ignore[arg-type]
            matched_rule=matched_rule,
            reason=reason,
            normalized_input_hash=stable_hash(normalized_arguments),
            resolved_paths=resolved_paths,
            command_category=command_category,
            network_policy=permission_context.network_policy,
            requested_cwd=requested_cwd,
            effective_cwd=effective_cwd,
            requires_user_input=requires_user_input,
            non_interactive_resolution=non_interactive_resolution,
        )


def _path_fields(tool_name: str) -> list[str]:
    fields = {
        "list_files": ["root"],
        "read_file": ["path"],
        "grep": ["root"],
        "edit_file": ["path"],
        "create_file": ["path"],
        "bash": ["cwd"],
    }
    return fields.get(tool_name, [])


def _deny_reason_for_bash(
    command: str,
    workspace_facade: Any,
    workspace_path: str,
) -> str | None:
    stripped = command.strip()
    if not stripped:
        return "bash command must not be empty."
    forbidden_fragments = ["|", ">", "<", "&&", "||", ";", "`", "$", "\n", "&", "~"]
    for fragment in forbidden_fragments:
        if fragment in stripped:
            return f"Unsupported shell syntax: {fragment}"
    try:
        parts = shlex.split(stripped)
    except ValueError as exc:
        return f"Unable to parse shell command: {exc}"
    if not parts:
        return "bash command must not be empty."
    if "=" in parts[0] and not parts[0].startswith(("./", "/")):
        return "Environment variable prefixes are not allowed."
    command_name = Path(parts[0]).name
    if command_name in {"curl", "wget", "ssh", "scp", "sudo", "rm"}:
        return f"Command is denied by default: {command_name}"
    if command_name == "git":
        if len(parts) < 2:
            return "git command must include an allowed read-only subcommand."
        if parts[1] not in {"status", "diff", "show", "log", "ls-files"}:
            return f"git subcommand is denied by default: {parts[1]}"
        return None
    if command_name == "ls":
        return _validate_bash_paths(parts[1:], workspace_facade, workspace_path, allow_flags=True)
    if command_name == "find":
        return _validate_bash_paths(parts[1:] or ["."], workspace_facade, workspace_path, allow_flags=False)
    if command_name in {"pwd", "ruff", "mypy"}:
        return None
    if parts[:3] == ["python", "-m", "compileall"]:
        return None
    return f"Command is not in the stage eight bash allowlist: {command_name}"


def _validate_bash_paths(
    args: list[str],
    workspace_facade: Any,
    workspace_path: str,
    *,
    allow_flags: bool,
) -> str | None:
    for arg in args:
        if arg.startswith("-"):
            if allow_flags:
                continue
            return f"Unsupported argument for restricted command: {arg}"
        try:
            workspace_facade.resolve_workspace_path(workspace_path, arg, must_exist=True)
        except WorkspaceError as exc:
            return str(exc)
    return None


def _command_category(tool_name: str) -> str | None:
    if tool_name == "bash":
        return "diagnostic"
    if tool_name == "run_tests":
        return "test"
    return None
