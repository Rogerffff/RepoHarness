"""第一版权限系统。"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_harness.errors import WorkspaceError
from repo_harness.permissions.schemas import PermissionDecision
from repo_harness.schema_base import stable_hash
from repo_harness.tasks.command_policy import evaluate_model_bash_command


@dataclass(frozen=True)
class PermissionContext:
    mode: str = "auto"
    network_policy: str = "deny_agent_run"
    test_command: str = "pytest -q"
    test_feedback_policy: str = "oracle_hidden_feedback"


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
                        "glob_files",
                        "symbol_search",
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
            policy_decision = evaluate_model_bash_command(
                command,
                configured_test_command=permission_context.test_command,
                test_feedback_policy=permission_context.test_feedback_policy,
            )
            if policy_decision.decision == "deny":
                return self._decision(
                    tool_call_id=tool_call_id,
                    requested_tool_name=requested_tool_name,
                    effective_tool_name=effective_tool_name,
                    permission_context=permission_context,
                    requested_arguments=requested_arguments,
                    normalized_arguments=normalized_arguments,
                    decision="deny",
                    reason=_with_bash_recovery_guidance(
                        policy_decision.reason
                        + (
                            f" {policy_decision.recovery_hint}"
                            if policy_decision.recovery_hint
                            else ""
                        )
                    ),
                    matched_rule=policy_decision.matched_rule,
                    resolved_paths=resolved_paths,
                    command_category=policy_decision.command_category,
                    requested_cwd=str(requested_cwd) if requested_cwd is not None else None,
                    effective_cwd=effective_cwd,
                    policy_decision=policy_decision.decision,
                    reason_code=policy_decision.reason_code or policy_decision.matched_rule,
                    safe_argv=policy_decision.safe_argv,
                    recovery_hint=policy_decision.recovery_hint,
                    timeout_sec=_timeout_from_args(normalized_arguments),
                )
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
                    reason=_with_bash_recovery_guidance(command_issue),
                    matched_rule="bash_command_safety",
                    resolved_paths=resolved_paths,
                    command_category="diagnostic",
                    requested_cwd=str(requested_cwd) if requested_cwd is not None else None,
                    effective_cwd=effective_cwd,
                    policy_decision="deny",
                    reason_code=_bash_reason_code(command_issue),
                    safe_argv=policy_decision.safe_argv,
                    recovery_hint=_bash_recovery_hint(command_issue),
                    timeout_sec=_timeout_from_args(normalized_arguments),
                )

        if effective_tool_name == "execute_bash":
            policy_decision = str(normalized_arguments.get("policy_decision") or "")
            if policy_decision == "deny":
                return self._decision(
                    tool_call_id=tool_call_id,
                    requested_tool_name=requested_tool_name,
                    effective_tool_name=effective_tool_name,
                    permission_context=permission_context,
                    requested_arguments=requested_arguments,
                    normalized_arguments=normalized_arguments,
                    decision="deny",
                    reason=str(normalized_arguments.get("recovery_hint") or "execute_bash command denied."),
                    matched_rule=str(normalized_arguments.get("reason_code") or "execute_bash_denied"),
                    resolved_paths=resolved_paths,
                    command_category=str(normalized_arguments.get("command_category") or "diagnostic"),
                    requested_cwd=str(requested_cwd) if requested_cwd is not None else None,
                    effective_cwd=effective_cwd,
                    policy_decision=policy_decision,
                    reason_code=str(normalized_arguments.get("reason_code") or "execute_bash_denied"),
                    recovery_hint=str(normalized_arguments.get("recovery_hint") or ""),
                    timeout_sec=_timeout_from_args(normalized_arguments),
                    shell_execution=True,
                )
            backend = str(getattr(workspace_facade, "backend", ""))
            if not (
                normalized_arguments.get("execute_bash_workspace_isolation_verified") is True
                or normalized_arguments.get("allow_unisolated_local_execute_bash_for_tests") is True
            ):
                return self._decision(
                    tool_call_id=tool_call_id,
                    requested_tool_name=requested_tool_name,
                    effective_tool_name=effective_tool_name,
                    permission_context=permission_context,
                    requested_arguments=requested_arguments,
                    normalized_arguments=normalized_arguments,
                    decision="deny",
                    reason=(
                        "execute_bash requires a workspace-only isolated execution backend in Stage 16A; "
                        "ordinary local_process and Docker run-directory mounts are not safe for "
                        "model-visible shell commands."
                    ),
                    matched_rule="execute_bash_requires_workspace_only_execution_backend",
                    resolved_paths=resolved_paths,
                    command_category=str(normalized_arguments.get("command_category") or "diagnostic"),
                    requested_cwd=str(requested_cwd) if requested_cwd is not None else None,
                    effective_cwd=effective_cwd,
                    policy_decision="deny",
                    reason_code="execute_bash_requires_workspace_only_execution_backend",
                    recovery_hint=str(normalized_arguments.get("recovery_hint") or ""),
                    timeout_sec=_timeout_from_args(normalized_arguments),
                    shell_execution=True,
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
            policy_decision=(
                str(normalized_arguments.get("policy_decision"))
                if effective_tool_name in {"bash", "execute_bash"}
                and normalized_arguments.get("policy_decision") is not None
                else None
            ),
            reason_code=(
                str(normalized_arguments.get("reason_code"))
                if effective_tool_name in {"bash", "execute_bash"}
                and normalized_arguments.get("reason_code") is not None
                else None
            ),
            safe_argv=(
                normalized_arguments.get("safe_argv")
                if effective_tool_name == "bash" and isinstance(normalized_arguments.get("safe_argv"), list)
                else None
            ),
            recovery_hint=(
                str(normalized_arguments.get("recovery_hint"))
                if effective_tool_name in {"bash", "execute_bash"}
                and normalized_arguments.get("recovery_hint") is not None
                else None
            ),
            timeout_sec=(
                _timeout_from_args(normalized_arguments)
                if effective_tool_name in {"bash", "execute_bash"}
                else None
            ),
            shell_execution=effective_tool_name == "execute_bash",
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
        policy_decision: str | None = None,
        reason_code: str | None = None,
        safe_argv: list[str] | None = None,
        recovery_hint: str | None = None,
        timeout_sec: int | None = None,
        shell_execution: bool = False,
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
            policy_decision=policy_decision,
            reason_code=reason_code,
            safe_argv=safe_argv,
            recovery_hint=recovery_hint,
            timeout_sec=timeout_sec,
            shell_execution=shell_execution,
            requires_user_input=requires_user_input,
            non_interactive_resolution=non_interactive_resolution,
        )


def _path_fields(tool_name: str) -> list[str]:
    fields = {
        "list_files": ["root"],
        "glob_files": ["root"],
        "read_file": ["path"],
        "grep": ["root"],
        "symbol_search": ["root"],
        "edit_file": ["path"],
        "create_file": ["path"],
        "bash": ["cwd"],
        "execute_bash": ["cwd"],
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


_BASH_RECOVERY_GUIDANCE = (
    "bash is restricted: pass one allowlisted diagnostic command only; do not use cd, "
    "pipes, redirects, shell composition, variable expansion, or arbitrary python -c. "
    "Use cwd for directories, read_file/grep for inspection, run_tests for configured "
    "test feedback, and git_diff for patch review."
)


def _with_bash_recovery_guidance(reason: str) -> str:
    if _BASH_RECOVERY_GUIDANCE in reason:
        return reason
    return f"{reason}. {_BASH_RECOVERY_GUIDANCE}"


def _bash_reason_code(reason: str) -> str:
    lowered = reason.lower()
    if "find is not allowed" in lowered:
        return "use_list_files_instead_of_find"
    if "grep" in lowered and "not in" in lowered:
        return "use_grep_tool_instead_of_bash_grep"
    if "curl" in lowered or "wget" in lowered or "network" in lowered:
        return "network_command_denied"
    if "rm" in lowered or "destructive" in lowered:
        return "destructive_command_denied"
    if "unsupported shell syntax" in lowered:
        return "unsupported_shell_syntax"
    return "bash_command_safety_denied"


def _bash_recovery_hint(reason: str) -> str:
    lowered = reason.lower()
    if "find is not allowed" in lowered:
        return "Use list_files with path, glob, offset, and max_entries."
    if "grep" in lowered:
        return "Use the grep tool with literal or regex mode."
    if "git diff" in lowered:
        return "Use git_diff for patch review."
    if "test_feedback_policy=disabled" in lowered:
        return "Use source inspection and git_diff; tests are final-verifier-only."
    return _BASH_RECOVERY_GUIDANCE


def _timeout_from_args(arguments: dict[str, Any]) -> int | None:
    value = arguments.get("timeout_sec")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
    if subcommand == "show":
        has_safe_path, path_reason = _validate_git_explicit_paths(rest, workspace_facade, workspace_path)
        if path_reason is not None:
            return path_reason
        if not has_safe_path:
            return "git show requires an explicit safe path to avoid exposing full history."
    if subcommand == "log":
        exposes_file_details = any(arg in {"-p", "--patch", "--name-only", "--name-status", "--stat"} for arg in rest)
        has_safe_path, path_reason = _validate_git_explicit_paths(rest, workspace_facade, workspace_path)
        if path_reason is not None:
            return path_reason
        if exposes_file_details and not has_safe_path:
            return "git log file-detail output requires an explicit safe path."
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


def _validate_git_explicit_paths(
    args: list[str],
    workspace_facade: Any,
    workspace_path: str,
) -> tuple[bool, str | None]:
    explicit_paths: list[str] = []
    path_mode = False
    for arg in args:
        if arg == "--":
            path_mode = True
            continue
        if path_mode:
            explicit_paths.append(arg)
            continue
        if arg.startswith("-"):
            continue
        path_part = _path_component(arg)
        if path_part != arg:
            explicit_paths.append(path_part)
    for path in explicit_paths:
        reason = _validate_single_path_operand(path, workspace_facade, workspace_path)
        if reason is not None:
            return False, reason
    return bool(explicit_paths), None


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
    if tool_name in {"bash", "execute_bash"}:
        return "diagnostic"
    if tool_name == "run_tests":
        return "test"
    return None
