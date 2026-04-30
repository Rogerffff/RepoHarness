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
        return _validate_git_command(parts[1:], workspace_facade, workspace_path)
    if command_name == "ls":
        return _validate_ls_command(parts[1:], workspace_facade, workspace_path)
    if command_name == "find":
        return "find is not allowed in bash; use list_files for sensitive-path-filtered enumeration."
    if command_name == "pwd":
        return None
    if command_name == "ruff":
        return _validate_ruff_command(parts[1:], workspace_facade, workspace_path)
    if command_name == "mypy":
        return _validate_path_operands(
            parts[1:],
            workspace_facade,
            workspace_path,
            allowed_flags={
                "--strict",
                "--ignore-missing-imports",
                "--show-error-codes",
                "--pretty",
                "--no-color-output",
                "-q",
            },
            default_path_args=["."],
        )
    if parts[:3] == ["python", "-m", "compileall"]:
        return _validate_path_operands(
            parts[3:],
            workspace_facade,
            workspace_path,
            allowed_flags={"-q", "-qq", "-f", "-b", "-l"},
            default_path_args=["."],
        )
    return f"Command is not in the stage eight bash allowlist: {command_name}"


def _validate_git_command(
    args: list[str],
    workspace_facade: Any,
    workspace_path: str,
) -> str | None:
    if not args:
        return "git command must include an allowed read-only subcommand."
    subcommand = args[0]
    if subcommand not in {"status", "diff", "show", "log", "ls-files"}:
        return f"git subcommand is denied by default: {subcommand}"
    rest = args[1:]
    if subcommand == "diff" and "--no-index" in rest:
        return "git diff --no-index is not allowed in agent bash."
    if subcommand in {"status", "ls-files"}:
        return _validate_path_operands(
            rest,
            workspace_facade,
            workspace_path,
            allowed_flags={
                "--short",
                "-s",
                "--porcelain",
                "--porcelain=v1",
                "--porcelain=v2",
                "--cached",
                "--deleted",
                "--modified",
                "--others",
                "--stage",
            },
            all_non_flag_operands_are_paths=True,
            default_path_args=["."],
        )
    return _validate_path_operands(
        rest,
        workspace_facade,
        workspace_path,
        allowed_flags={
            "--",
            "--cached",
            "--staged",
            "--stat",
            "--name-only",
            "--name-status",
            "--oneline",
            "--decorate",
            "--no-color",
            "--color=never",
            "-p",
        },
        allowed_flag_prefixes={"--pretty=", "--format=", "--max-count=", "-n"},
        validate_path_like_operands=True,
    )


def _validate_ruff_command(
    args: list[str],
    workspace_facade: Any,
    workspace_path: str,
) -> str | None:
    if not args:
        return _validate_path_operands(["."], workspace_facade, workspace_path)
    subcommand = args[0]
    if subcommand != "check":
        return f"ruff subcommand is denied by default: {subcommand}"
    return _validate_path_operands(
        args[1:],
        workspace_facade,
        workspace_path,
        allowed_flags={"--quiet", "--no-cache", "--no-fix", "--show-files", "--show-settings"},
        allowed_flag_prefixes={"--output-format="},
        default_path_args=["."],
    )


def _validate_path_operands(
    args: list[str],
    workspace_facade: Any,
    workspace_path: str,
    *,
    allowed_flags: set[str] | None = None,
    allowed_flag_prefixes: set[str] | None = None,
    default_path_args: list[str] | None = None,
    all_non_flag_operands_are_paths: bool = False,
    validate_path_like_operands: bool = False,
) -> str | None:
    allowed_flags = allowed_flags or set()
    allowed_flag_prefixes = allowed_flag_prefixes or set()
    operands = args or (default_path_args or [])
    path_mode = False
    for arg in operands:
        if arg == "--":
            path_mode = True
            continue
        if not path_mode and arg.startswith("-"):
            if arg in allowed_flags or any(arg.startswith(prefix) for prefix in allowed_flag_prefixes):
                continue
            return f"Unsupported argument for restricted command: {arg}"
        if path_mode or all_non_flag_operands_are_paths or _is_path_like_operand(arg, workspace_path):
            reason = _validate_single_path_operand(arg, workspace_facade, workspace_path)
            if reason is not None:
                return reason
            continue
        if validate_path_like_operands:
            continue
    return None


def _is_path_like_operand(arg: str, workspace_path: str) -> bool:
    candidate = _path_component(arg)
    raw = Path(candidate)
    if raw.is_absolute() or candidate.startswith((".", "..")):
        return True
    if "/" in candidate or "\\" in candidate:
        return True
    return (Path(workspace_path) / candidate).exists()


def _validate_single_path_operand(
    arg: str,
    workspace_facade: Any,
    workspace_path: str,
) -> str | None:
    path_arg = _path_component(arg)
    if path_arg.startswith(":("):
        return f"Unsupported pathspec syntax for restricted command: {arg}"
    try:
        workspace_facade.resolve_workspace_path(workspace_path, path_arg, must_exist=True)
    except WorkspaceError as exc:
        return str(exc)
    return None


def _path_component(arg: str) -> str:
    if ":" not in arg:
        return arg
    _, path_part = arg.rsplit(":", 1)
    return path_part or arg


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


def _validate_ls_command(
    args: list[str],
    workspace_facade: Any,
    workspace_path: str,
) -> str | None:
    if not args:
        return "ls without explicit file operands is not allowed; use list_files for directory enumeration."
    for arg in args:
        if arg.startswith("-"):
            return f"Unsupported ls argument for restricted command: {arg}"
        try:
            resolved = workspace_facade.resolve_workspace_path(workspace_path, arg, must_exist=True)
        except WorkspaceError as exc:
            return str(exc)
        if resolved.is_dir():
            return "ls on directories is not allowed; use list_files for sensitive-path-filtered enumeration."
    return None


def _command_category(tool_name: str) -> str | None:
    if tool_name == "bash":
        return "diagnostic"
    if tool_name == "run_tests":
        return "test"
    return None
