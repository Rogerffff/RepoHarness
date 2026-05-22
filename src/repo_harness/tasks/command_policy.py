"""Stage 12 command policy helpers for task, setup, test, and model bash commands."""

from __future__ import annotations

import shlex
import re
import ast
from pathlib import Path, PurePosixPath
from typing import ClassVar, Literal

from pydantic import Field

from repo_harness.errors import TaskValidationError
from repo_harness.schema_base import StrictBaseModel

COMMAND_POLICY_VERSION = "repo_harness_command_policy_v0"

FORBIDDEN_SHELL_FRAGMENTS = ["|", ">", "<", "&&", "||", ";", "`", "$", "\n", "&"]
PYTEST_FLAG_ALLOWLIST = {
    "-q",
    "--quiet",
    "-v",
    "-vv",
    "-s",
    "-x",
    "--disable-warnings",
    "--strict-config",
    "--strict-markers",
}
PYTEST_TB_VALUES = {"auto", "long", "short", "line", "native", "no"}


class SetupCommandPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_setup_command_policy_v0"
    policy_version: str = COMMAND_POLICY_VERSION
    allowlist: list[str] = Field(default_factory=lambda: ["python <repo_script.py>"])
    allow_network: bool = False
    timeout_sec: int = Field(default=120, gt=0)
    working_directory: Literal["repo_root"] = "repo_root"
    environment_variable_allowlist: list[str] = Field(default_factory=list)
    dependency_install_policy: Literal["repo_script_only", "deny"] = "repo_script_only"


class TestCommandPolicy(StrictBaseModel):
    __test__: ClassVar[bool] = False

    schema_version: str = "repo_harness_test_command_policy_v0"
    policy_version: str = COMMAND_POLICY_VERSION
    public_test_command: str = "pytest -q"
    hidden_formal_verifier_command: str | None = None
    model_visible_execution_allowed: bool = True
    test_feedback_policy_mapping: dict[str, str] = Field(
        default_factory=lambda: {
            "disabled": "deny_model_visible_test_execution",
            "public_only": "route_to_run_tests_public",
            "structured_public_feedback": "route_to_run_tests_structured_public",
            "oracle_hidden_feedback": "route_to_run_tests_oracle",
        }
    )


class CommandPolicyDecision(StrictBaseModel):
    schema_version: str = "repo_harness_command_policy_decision_v0"
    policy_version: str = COMMAND_POLICY_VERSION
    command: str
    command_category: Literal["setup", "public_test", "hidden_test", "diagnostic", "invalid"]
    decision: Literal["allow", "deny", "route_to_run_tests"]
    reason: str
    matched_rule: str
    reason_code: str | None = None
    safe_argv: list[str] | None = None
    recovery_hint: str | None = None


class CommandPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_command_policy_v0"
    policy_version: str = COMMAND_POLICY_VERSION
    setup: SetupCommandPolicy = Field(default_factory=SetupCommandPolicy)
    test: TestCommandPolicy = Field(default_factory=TestCommandPolicy)

    def validate_setup_command(self, command: str | None, repo_path: Path) -> CommandPolicyDecision:
        return validate_setup_command(command, repo_path, policy=self.setup)

    def validate_test_command(self, command: str) -> CommandPolicyDecision:
        return validate_test_command(command, policy=self.test)

    def evaluate_model_bash(
        self,
        command: str,
        *,
        configured_test_command: str,
        test_feedback_policy: str,
    ) -> CommandPolicyDecision:
        return evaluate_model_bash_command(
            command,
            configured_test_command=configured_test_command,
            test_feedback_policy=test_feedback_policy,
            policy=self.test,
        )

    def evaluate_model_execute_bash(
        self,
        command: str,
        *,
        shared_dependency_environment_expected: bool = False,
        shared_dependency_environment_roots: list[str] | None = None,
    ) -> CommandPolicyDecision:
        return evaluate_model_execute_bash_command(
            command,
            shared_dependency_environment_expected=shared_dependency_environment_expected,
            shared_dependency_environment_roots=shared_dependency_environment_roots,
        )


def validate_test_command(
    command: str,
    *,
    policy: TestCommandPolicy | None = None,
) -> CommandPolicyDecision:
    resolved_policy = policy or TestCommandPolicy(public_test_command=command)
    parts = split_static_command(command, field_name="test_command")
    if parts[0] == "pytest":
        validate_pytest_args(parts[1:])
        return CommandPolicyDecision(
            command=command,
            command_category="public_test",
            decision="allow",
            reason="pytest command is in the public test allowlist.",
            matched_rule="pytest_public_allowlist",
        )
    if parts[:3] == ["python", "-m", "pytest"]:
        validate_pytest_args(parts[3:])
        return CommandPolicyDecision(
            command=command,
            command_category="public_test",
            decision="allow",
            reason="python -m pytest command is in the public test allowlist.",
            matched_rule="python_m_pytest_public_allowlist",
        )
    if command.strip() == resolved_policy.hidden_formal_verifier_command:
        return CommandPolicyDecision(
            command=command,
            command_category="hidden_test",
            decision="deny",
            reason="hidden formal verifier command cannot be declared as model-visible test_command.",
            matched_rule="hidden_formal_verifier_denied",
        )
    raise TaskValidationError("test_command 第二版策略门只允许 pytest 或 python -m pytest 形式。")


def validate_setup_command(
    command: str | None,
    repo_path: Path | None,
    *,
    policy: SetupCommandPolicy | None = None,
) -> CommandPolicyDecision:
    if command is None or not command.strip():
        return CommandPolicyDecision(
            command="",
            command_category="setup",
            decision="allow",
            reason="No setup command declared.",
            matched_rule="setup_not_declared",
        )
    resolved_policy = policy or SetupCommandPolicy()
    parts = split_static_command(command, field_name="setup_command")
    if (
        resolved_policy.dependency_install_policy == "repo_script_only"
        and len(parts) == 2
        and parts[0] == "python"
        and parts[1].endswith(".py")
    ):
        if repo_path is not None:
            script_path = resolve_command_path(repo_path, parts[1], field_name="setup_command")
            if not script_path.exists() or not script_path.is_file():
                raise TaskValidationError(f"setup_command 脚本不存在：{parts[1]}")
        return CommandPolicyDecision(
            command=command,
            command_category="setup",
            decision="allow",
            reason=(
                "setup command is a repository-local Python script."
                if repo_path is not None
                else "setup command shape is allowed; file existence is checked after materialization."
            ),
            matched_rule=(
                "setup_python_repo_script_allowlist"
                if repo_path is not None
                else "setup_python_repo_script_shape_allowlist"
            ),
        )
    raise TaskValidationError("setup_command 第二版策略门只允许 python <repo_script.py> 形式。")


def evaluate_model_bash_command(
    command: str,
    *,
    configured_test_command: str,
    test_feedback_policy: str,
    policy: TestCommandPolicy | None = None,
) -> CommandPolicyDecision:
    resolved_policy = policy or TestCommandPolicy(public_test_command=configured_test_command)
    stripped = command.strip()
    category = classify_bash_command(
        stripped,
        configured_test_command=configured_test_command,
        policy=resolved_policy,
    )
    if category == "hidden_test":
        return CommandPolicyDecision(
            command=command,
            command_category="hidden_test",
            decision="deny",
            reason="Model-visible bash cannot execute the hidden formal verifier command.",
            matched_rule="hidden_test_command_denied",
            reason_code="hidden_test_command_denied",
            recovery_hint="Use read_file, grep, edit_file, and git_diff; hidden verifier commands are evaluator-only.",
        )
    if category == "public_test":
        if test_feedback_policy == "disabled":
            return CommandPolicyDecision(
                command=command,
                command_category="public_test",
                decision="deny",
                reason="test_feedback_policy=disabled blocks model-visible test execution.",
                matched_rule="test_feedback_disabled_blocks_bash_test",
                reason_code="denied_by_final_only_feedback_policy",
                safe_argv=_safe_split_or_none(command),
                recovery_hint="This task does not expose tests to the model. Use source inspection and git_diff instead.",
            )
        return CommandPolicyDecision(
            command=command,
            command_category="public_test",
            decision="route_to_run_tests",
            reason=resolved_policy.test_feedback_policy_mapping.get(
                test_feedback_policy,
                "route_to_run_tests",
            ),
            matched_rule="model_bash_test_routed_to_run_tests",
            reason_code="route_public_test_to_run_tests",
            safe_argv=_safe_split_or_none(command),
            recovery_hint="Use the run_tests tool for configured public test feedback.",
        )
    if category == "invalid":
        fragment = first_forbidden_shell_fragment(command)
        return CommandPolicyDecision(
            command=command,
            command_category="invalid",
            decision="deny",
            reason=(
                f"Unsupported shell syntax: {fragment}"
                if fragment is not None
                else "Command contains unsupported shell syntax."
            ),
            matched_rule="unsupported_shell_syntax",
            reason_code="unsupported_shell_syntax",
            recovery_hint="Pass one command without pipes, redirects, command composition, variable expansion, or background execution.",
        )
    safe_argv = _safe_split_or_none(command)
    return CommandPolicyDecision(
        command=command,
        command_category="diagnostic",
        decision="allow",
        reason="Command is not recognized as a test command.",
        matched_rule="diagnostic_bash_fallback",
        reason_code="diagnostic_bash_fallback",
        safe_argv=safe_argv,
        recovery_hint="Use dedicated tools for reading files, searching, test feedback, and diff review when possible.",
    )


def evaluate_model_execute_bash_command(
    command: str,
    *,
    shared_dependency_environment_expected: bool = False,
    shared_dependency_environment_roots: list[str] | None = None,
    _shell_wrapper_depth: int = 0,
) -> CommandPolicyDecision:
    stripped = command.strip()
    if not stripped:
        return _deny_execute_bash(command, "execute_bash_empty_command", "Command must not be empty.")
    issue = _execute_bash_dynamic_shell_expansion_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_dynamic_shell_expansion", issue)
    issue = _execute_bash_pipe_execution_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_pipe_to_interpreter", issue)
    issue = _execute_bash_output_redirection_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_output_redirection", issue)
    issue = _execute_bash_environment_assignment_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_environment_assignment_prefix", issue)
    issue = _execute_bash_secondary_executor_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_secondary_executor", issue)
    shell_inner_command, shell_wrapper_issue = _execute_bash_shell_wrapper_inner_command(stripped)
    if shell_wrapper_issue is not None:
        return _deny_execute_bash(command, "execute_bash_shell_wrapper_unauditable", shell_wrapper_issue)
    if shell_inner_command is not None:
        if _shell_wrapper_depth >= 3:
            return _deny_execute_bash(
                command,
                "execute_bash_shell_wrapper_depth_exceeded",
                "execute_bash shell wrapper nesting is too deep to audit safely.",
            )
        inner_decision = evaluate_model_execute_bash_command(
            shell_inner_command,
            shared_dependency_environment_expected=shared_dependency_environment_expected,
            shared_dependency_environment_roots=shared_dependency_environment_roots,
            _shell_wrapper_depth=_shell_wrapper_depth + 1,
        )
        if inner_decision.decision == "deny":
            return _deny_execute_bash(
                command,
                inner_decision.reason_code or inner_decision.matched_rule,
                f"execute_bash shell wrapper contains a denied command: {inner_decision.reason}",
            )
        return CommandPolicyDecision(
            command=command,
            command_category="diagnostic",
            decision="allow",
            reason="execute_bash shell wrapper inner command passed Stage 16A policy guards.",
            matched_rule="execute_bash_shell_wrapper_inner_policy_allow",
            reason_code="execute_bash_shell_wrapper_inner_policy_allow",
            recovery_hint="Keep shell wrappers focused on a single model-visible workspace diagnostic command.",
        )
    issue = _execute_bash_indirect_execution_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_indirect_script_execution", issue)
    issue = _execute_bash_control_operator_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_control_operator", issue)
    issue = _execute_bash_forbidden_marker_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_evaluator_only_marker", issue)
    issue = _execute_bash_shared_dependency_issue(
        stripped,
        shared_dependency_environment_expected=shared_dependency_environment_expected,
        shared_dependency_environment_roots=shared_dependency_environment_roots,
    )
    if issue is not None:
        return _deny_execute_bash(command, issue[0], issue[1])
    issue = _execute_bash_workspace_path_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_workspace_boundary", issue)
    issue = _execute_bash_git_history_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_git_history_or_metadata", issue)
    issue = _execute_bash_inline_process_escape_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_inline_process_escape", issue)
    issue = _execute_bash_inline_python_visibility_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_inline_python_visibility", issue)
    issue = _execute_bash_allowlist_issue(stripped)
    if issue is not None:
        return _deny_execute_bash(command, "execute_bash_unallowlisted_command", issue)
    return CommandPolicyDecision(
        command=command,
        command_category="diagnostic",
        decision="allow",
        reason="execute_bash command passed Stage 16A leakage and dependency-write guards.",
        matched_rule="execute_bash_stage16a_policy_allow",
        reason_code="execute_bash_stage16a_policy_allow",
        recovery_hint="Keep commands focused on model-visible workspace diagnostics and public task reproduction.",
    )


def classify_bash_command(
    command: str,
    *,
    configured_test_command: str,
    policy: TestCommandPolicy | None = None,
) -> Literal["public_test", "hidden_test", "diagnostic", "invalid"]:
    resolved_policy = policy or TestCommandPolicy(public_test_command=configured_test_command)
    if has_forbidden_shell_syntax(command):
        return "invalid"
    try:
        parts = shlex.split(command)
    except ValueError:
        return "invalid"
    if command.strip() == (resolved_policy.hidden_formal_verifier_command or "").strip():
        return "hidden_test"
    if is_recognized_test_command(command, configured_test_command):
        return "public_test"
    return "diagnostic"


def is_recognized_test_command(command: str, configured_test_command: str) -> bool:
    normalized = command.strip()
    configured = configured_test_command.strip()
    if has_forbidden_shell_syntax(normalized):
        return False
    try:
        parts = shlex.split(normalized)
    except ValueError:
        return False
    if normalized in {
        configured,
        "pytest",
        "pytest -q",
        "python -m pytest",
        "python -m pytest -q",
        "python -m unittest",
    }:
        return True
    return bool(
        parts
        and (
            parts[0] in {"pytest", "tox", "nox"}
            or parts[:3] == ["python", "-m", "pytest"]
            or parts[:3] == ["python", "-m", "unittest"]
        )
    )


def split_static_command(command: str, *, field_name: str) -> list[str]:
    if any(fragment in command for fragment in FORBIDDEN_SHELL_FRAGMENTS):
        raise TaskValidationError(f"{field_name} 包含不支持的 shell 语法。")
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise TaskValidationError(f"{field_name} 无法解析：{exc}") from exc
    if not parts:
        raise TaskValidationError(f"{field_name} 不能为空。")
    return parts


def validate_pytest_args(args: list[str]) -> None:
    for arg in args:
        if any(fragment in arg for fragment in FORBIDDEN_SHELL_FRAGMENTS):
            raise TaskValidationError("test_command 包含不支持的 shell 语法。")
        if arg.startswith("-"):
            validate_pytest_flag(arg)
            continue
        if arg in {".", ":", "::"}:
            continue
        path_candidate = Path(arg.split("::", 1)[0])
        if path_candidate.is_absolute() or ".." in path_candidate.parts:
            raise TaskValidationError("test_command 参数路径不能是绝对路径或包含 ..。")


def validate_pytest_flag(arg: str) -> None:
    if arg in PYTEST_FLAG_ALLOWLIST:
        return
    if arg.startswith("--tb=") and arg.split("=", 1)[1] in PYTEST_TB_VALUES:
        return
    if arg.startswith("--maxfail=") and arg.split("=", 1)[1].isdigit():
        return
    raise TaskValidationError(f"pytest 参数不在第二版白名单：{arg}")


def resolve_command_path(repo_path: Path, requested_path: str, *, field_name: str) -> Path:
    raw = Path(requested_path)
    if raw.is_absolute() or ".." in raw.parts:
        raise TaskValidationError(f"{field_name} 脚本路径不能是绝对路径或包含 ..。")
    resolved = (repo_path / raw).resolve()
    try:
        resolved.relative_to(repo_path.resolve())
    except ValueError as exc:
        raise TaskValidationError(f"{field_name} 脚本路径越过 repo 边界。") from exc
    return resolved


def has_forbidden_shell_syntax(command: str) -> bool:
    return any(fragment in command for fragment in FORBIDDEN_SHELL_FRAGMENTS)


def first_forbidden_shell_fragment(command: str) -> str | None:
    for fragment in FORBIDDEN_SHELL_FRAGMENTS:
        if fragment in command:
            return fragment
    return None


def _safe_split_or_none(command: str) -> list[str] | None:
    try:
        return shlex.split(command)
    except ValueError:
        return None


def _deny_execute_bash(command: str, reason_code: str, reason: str) -> CommandPolicyDecision:
    return CommandPolicyDecision(
        command=command,
        command_category="invalid",
        decision="deny",
        reason=reason,
        matched_rule=reason_code,
        reason_code=reason_code,
        recovery_hint=(
            "Use execute_bash only for model-visible repository diagnostics. "
            "Use read_file, grep, run_tests, and git_diff for safer structured operations when possible."
        ),
    )


def _execute_bash_shell_wrapper_inner_command(command: str) -> tuple[str | None, str | None]:
    try:
        parts = shlex.split(command)
    except ValueError:
        return None, None
    parts, prefix_issue = _strip_execute_bash_prefix_tokens(parts)
    if prefix_issue is not None:
        return None, prefix_issue
    if parts and parts[0].startswith("$"):
        return None, "execute_bash command starts with shell variable or ANSI-C expansion that cannot be audited safely."
    if parts and Path(parts[0]).name == "eval":
        return None, "execute_bash eval command cannot be audited safely in Stage 16A."
    if not parts or Path(parts[0]).name not in {"bash", "sh", "zsh"}:
        return None, None
    idx = 1
    while idx < len(parts):
        token = parts[idx]
        if token == "-c" or (token.startswith("-") and not token.startswith("--") and "c" in token[1:]):
            inner = parts[idx + 1] if idx + 1 < len(parts) else ""
            if inner.strip().startswith("$"):
                return None, (
                    "execute_bash shell wrapper uses shell variable or ANSI-C quoting for the inner command; "
                    "Stage 16A requires a statically auditable command string."
                )
            return inner, None
        idx += 1
    return None, None


def _strip_execute_bash_prefix_tokens(parts: list[str]) -> tuple[list[str], str | None]:
    remaining = list(parts)
    while remaining:
        command_name = Path(remaining[0]).name
        if command_name == "env":
            remaining = remaining[1:]
            if not remaining:
                return [], "execute_bash env wrapper does not contain a command to audit."
            while remaining and remaining[0].startswith("-"):
                return [], "execute_bash env wrapper options are not allowed in Stage 16A."
            while remaining and _looks_like_environment_assignment(remaining[0]):
                return [], "execute_bash env wrapper assignments are not allowed in Stage 16A."
            continue
        if command_name in {"command", "exec"}:
            remaining = remaining[1:]
            if not remaining:
                return [], f"execute_bash {command_name} wrapper does not contain a command to audit."
            if command_name == "command" and remaining and remaining[0].startswith("-"):
                return [], "execute_bash command wrapper options are not allowed in Stage 16A."
            continue
        if command_name == "time":
            remaining = remaining[1:]
            if remaining and remaining[0].startswith("-"):
                return [], "execute_bash time wrapper options are not allowed in Stage 16A."
            if not remaining:
                return [], "execute_bash time wrapper does not contain a command to audit."
            continue
        if command_name == "nice":
            remaining = remaining[1:]
            if remaining and remaining[0] == "-n":
                value = remaining[1] if len(remaining) >= 2 else ""
                if not _wrapper_value_is_model_visible(value) or not _is_safe_nice_adjustment(value):
                    return [], "execute_bash nice wrapper adjustment is not allowed in Stage 16A."
                remaining = remaining[2:]
            elif remaining and re.fullmatch(r"-\d+", remaining[0]):
                remaining = remaining[1:]
            while remaining and remaining[0].startswith("--"):
                return [], "execute_bash nice wrapper long options are not allowed in Stage 16A."
            if not remaining:
                return [], "execute_bash nice wrapper does not contain a command to audit."
            continue
        if command_name == "timeout":
            remaining = remaining[1:]
            if not remaining:
                return [], "execute_bash timeout wrapper does not contain a duration or command to audit."
            while remaining and remaining[0].startswith("-"):
                option = remaining[0]
                if option in {"-k", "--kill-after", "-s", "--signal"}:
                    value = remaining[1] if len(remaining) >= 2 else ""
                    if not _wrapper_value_is_model_visible(value):
                        return [], "execute_bash timeout wrapper option value references hidden or runtime-private material."
                    if option in {"-k", "--kill-after"} and not _is_safe_timeout_duration(value):
                        return [], "execute_bash timeout wrapper kill-after value is not a safe duration."
                    if option in {"-s", "--signal"} and not _is_safe_timeout_signal(value):
                        return [], "execute_bash timeout wrapper signal value is not a safe signal."
                    remaining = remaining[2:]
                    continue
                if option in {"--preserve-status", "--foreground", "-v", "--verbose"}:
                    remaining = remaining[1:]
                    continue
                if option.startswith("--kill-after=") or option.startswith("--signal="):
                    _, value = option.split("=", 1)
                    if not _wrapper_value_is_model_visible(value):
                        return [], "execute_bash timeout wrapper option value references hidden or runtime-private material."
                    if option.startswith("--kill-after=") and not _is_safe_timeout_duration(value):
                        return [], "execute_bash timeout wrapper kill-after value is not a safe duration."
                    if option.startswith("--signal=") and not _is_safe_timeout_signal(value):
                        return [], "execute_bash timeout wrapper signal value is not a safe signal."
                    remaining = remaining[1:]
                    continue
                return [], "execute_bash timeout wrapper option is not allowed in Stage 16A."
            if not remaining:
                return [], "execute_bash timeout wrapper does not contain a duration to audit."
            if not _wrapper_value_is_model_visible(remaining[0]) or not _is_safe_timeout_duration(remaining[0]):
                return [], "execute_bash timeout wrapper duration is not allowed in Stage 16A."
            remaining = remaining[1:]
            if not remaining:
                return [], "execute_bash timeout wrapper does not contain an inner command to audit."
            continue
        break
    return remaining, None


def _looks_like_environment_assignment(value: str) -> bool:
    if "=" not in value:
        return False
    name, _ = value.split("=", 1)
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name))


def _wrapper_value_is_model_visible(value: str) -> bool:
    return bool(value) and _search_path_token_is_model_visible(value)


def _is_safe_timeout_duration(value: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)?(?:[smhd])?", value))


def _is_safe_timeout_signal(value: str) -> bool:
    return bool(re.fullmatch(r"(?:\d+|[A-Za-z][A-Za-z0-9_]*)", value))


def _is_safe_nice_adjustment(value: str) -> bool:
    return bool(re.fullmatch(r"-?\d+", value))


def _execute_bash_dynamic_shell_expansion_issue(command: str) -> str | None:
    if "`" in command:
        return "execute_bash command uses backtick command substitution, which cannot be audited safely."
    if _has_unquoted_glob_metacharacter(command):
        return "execute_bash command uses unquoted shell glob characters, which can expand to hidden or runtime-private paths."
    if "<(" in command or ">(" in command:
        return "execute_bash command uses shell process substitution, which cannot be audited safely."
    if "$(" in command:
        return "execute_bash command uses shell command substitution, which cannot be audited safely."
    if "${" in command:
        return "execute_bash command uses shell parameter expansion, which cannot be audited safely."
    if "$'" in command:
        return "execute_bash command uses ANSI-C shell quoting, which cannot be audited safely."
    if _has_unquoted_shell_variable_expansion(command):
        return "execute_bash command uses shell variable expansion, which cannot be audited safely in Stage 16A."
    return None


def _execute_bash_pipe_execution_issue(command: str) -> str | None:
    if _pipeline_right_hand_segments(command):
        return "execute_bash pipelines are not part of the Stage 16A model-visible shell allowlist."
    return None


def _execute_bash_output_redirection_issue(command: str) -> str | None:
    if _has_unquoted_output_redirection(command):
        return "execute_bash output redirection can write workspace files outside the structured tool surface."
    return None


def _pipeline_right_hand_segments(command: str) -> list[str]:
    segments: list[str] = []
    in_single_quote = False
    in_double_quote = False
    escaped = False
    start = 0
    idx = 0
    while idx < len(command):
        char = command[idx]
        if escaped:
            escaped = False
            idx += 1
            continue
        if char == "\\":
            escaped = True
            idx += 1
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            idx += 1
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            idx += 1
            continue
        if char == "|" and not in_single_quote and not in_double_quote:
            if command.startswith("||", idx):
                idx += 2
                continue
            start = idx + 1
            segments.append(command[start:].strip())
        idx += 1
    return segments


def _execute_bash_environment_assignment_issue(command: str) -> str | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        return "execute_bash command cannot be parsed well enough to audit environment assignments safely."
    if parts and _looks_like_environment_assignment(parts[0]):
        return "execute_bash command uses a model-visible environment assignment prefix, which is not allowed in Stage 16A."
    return None


def _execute_bash_secondary_executor_issue(command: str) -> str | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        return "execute_bash command cannot be parsed well enough to audit secondary execution safely."
    parts, prefix_issue = _strip_execute_bash_prefix_tokens(parts)
    if prefix_issue is not None:
        return prefix_issue
    if not parts:
        return None
    command_name = _command_token_name(parts[0])
    if command_name == "find" and "-exec" in parts[1:]:
        return "execute_bash find -exec can run unaudited commands and is not allowed in Stage 16A."
    if command_name in {"xargs", "parallel"}:
        return f"execute_bash {command_name} can run unaudited secondary commands and is not allowed in Stage 16A."
    if command_name == "builtin":
        return "execute_bash shell builtin wrappers are not allowed in Stage 16A."
    if command_name in {
        "make",
        "npx",
        "uvx",
        "stdbuf",
        "nohup",
        "watch",
        "flock",
        "ionice",
        "setsid",
        "chrt",
        "curl",
        "wget",
        "corepack",
        "unbuffer",
        "script",
        "sudo",
        "doas",
        "su",
        "runuser",
        "sg",
        "daemon",
    }:
        return f"execute_bash {command_name} requires build or package execution provenance before it can be allowed."
    if command_name == "builtin" and len(parts) >= 2 and parts[1] in {"eval", "source", "."}:
        return "execute_bash shell builtin eval/source can hide forbidden commands and is not allowed in Stage 16A."
    if command_name == "deno" and len(parts) >= 2 and parts[1] == "run":
        return "execute_bash deno run can execute remote or unaudited code and is not allowed in Stage 16A."
    if _non_python_inline_executor_issue(parts):
        return "execute_bash inline non-Python interpreter execution is not allowed in Stage 16A."
    return None


def _non_python_inline_executor_issue(parts: list[str]) -> bool:
    command_name = _command_token_name(parts[0])
    lowered_name = command_name.lower()
    args = parts[1:]
    if lowered_name == "perl" and any(_short_option_contains(arg, {"e", "E", "p"}) for arg in args):
        return True
    if lowered_name == "ruby" and any(
        arg == "--execute" or _short_option_contains(arg, {"e"}) for arg in args
    ):
        return True
    if lowered_name == "lua" and any(arg == "-e" or arg.startswith("-e") for arg in args):
        return True
    if lowered_name == "node" and any(
        arg in {"-e", "-p", "--eval", "--print"}
        or arg.startswith("--eval=")
        or arg.startswith("--print=")
        or (arg.startswith("-") and not arg.startswith("--") and any(flag in arg[1:] for flag in {"e", "p"}))
        for arg in args
    ):
        return True
    if lowered_name == "php" and any(arg == "-r" or arg.startswith("-r") for arg in args):
        return True
    if lowered_name in {"awk", "mawk", "gawk"} and any("system(" in arg for arg in args):
        return True
    if lowered_name in {"r", "rscript"} and any(arg == "-e" or arg.startswith("-e") for arg in args):
        return True
    return False


def _short_option_contains(arg: str, flags: set[str]) -> bool:
    return arg.startswith("-") and not arg.startswith("--") and any(flag in arg[1:] for flag in flags)


def _execute_bash_indirect_execution_issue(command: str) -> str | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        return "execute_bash command cannot be parsed well enough to audit indirect execution safely."
    parts, prefix_issue = _strip_execute_bash_prefix_tokens(parts)
    if prefix_issue is not None:
        return prefix_issue
    if not parts:
        return "execute_bash command is empty after shell prefix normalization."
    if _has_unquoted_input_redirection(command) and not _is_safe_python_heredoc_command(command):
        return "execute_bash input redirection can feed unaudited script content into an interpreter."
    command_name = _command_token_name(parts[0])
    if command_name in {"source", "."}:
        return "execute_bash source and dot-script execution are not auditable in Stage 16A."
    if command_name == "alias" or re.search(r"(^|[;&]\s*)alias\s+", command):
        return "execute_bash alias definitions can hide forbidden commands and are not allowed in Stage 16A."
    if command_name == "function" or re.search(r"(^|[;&]\s*)function\s+", command):
        return "execute_bash shell function definitions are not allowed in Stage 16A."
    if re.search(r"(^|[;&]\s*)[A-Za-z_][A-Za-z0-9_]*\s*\(\s*\)\s*\{", command):
        return "execute_bash shell function definitions are not allowed in Stage 16A."
    if command_name in {"bash", "sh", "zsh"} and _shell_command_invokes_script(parts[1:]):
        return "execute_bash cannot run workspace shell scripts until script content provenance is audited."
    if _path_invokes_workspace_script(parts[0]):
        return "execute_bash cannot execute workspace scripts directly until script content provenance is audited."
    if _is_python_interpreter_token(parts[0]) and _python_command_invokes_workspace_script(parts[1:]):
        return "execute_bash cannot run workspace Python scripts until script content provenance is audited."
    if command_name == "awk" and "-f" in parts[1:]:
        return "execute_bash awk -f runs unaudited workspace script files in Stage 16A."
    return None


def _execute_bash_control_operator_issue(command: str) -> str | None:
    if _has_unquoted_control_operator(command):
        return "execute_bash command composition with ;, &&, or || is not allowed in Stage 16A."
    return None


def _shell_command_invokes_script(args: list[str]) -> bool:
    for arg in args:
        if arg == "--":
            continue
        if arg.startswith("-"):
            continue
        return _path_invokes_workspace_script(arg)
    return False


def _path_invokes_workspace_script(value: str) -> bool:
    normalized = value.replace("\\", "/")
    if normalized.startswith(("./", "../")):
        return True
    return normalized.endswith((".sh", ".bash", ".zsh", ".py"))


def _python_command_invokes_workspace_script(args: list[str]) -> bool:
    idx = 0
    while idx < len(args):
        token = args[idx]
        if token in {"-c", "-"}:
            return False
        if token == "-m":
            module = args[idx + 1] if idx + 1 < len(args) else ""
            return module not in {"pytest", "unittest", "pip"}
        if token in {"-u", "-B", "-S", "-E", "-I", "-O", "-OO"}:
            idx += 1
            continue
        if token in {"-W", "-X"}:
            idx += 2
            continue
        if token.startswith("-W") or token.startswith("-X"):
            idx += 1
            continue
        if token.startswith("-"):
            idx += 1
            continue
        return token.endswith(".py") or "/" in token or token.startswith(("./", "../"))
    return False


def _command_token_name(value: str) -> str:
    return value if value == "." else Path(value).name


def _is_python_interpreter_token(value: str) -> bool:
    return bool(re.fullmatch(r"python(?:\d+(?:\.\d+)*)?", Path(value).name))


def _has_unquoted_shell_variable_expansion(command: str) -> bool:
    in_single_quote = False
    in_double_quote = False
    escaped = False
    idx = 0
    while idx < len(command):
        char = command[idx]
        if escaped:
            escaped = False
            idx += 1
            continue
        if char == "\\":
            escaped = True
            idx += 1
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            idx += 1
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            idx += 1
            continue
        if char == "$" and not in_single_quote:
            next_char = command[idx + 1] if idx + 1 < len(command) else ""
            if next_char and re.match(r"[A-Za-z_0-9@*#?$!-]", next_char):
                return True
        idx += 1
    return False


def _has_unquoted_glob_metacharacter(command: str) -> bool:
    in_single_quote = False
    in_double_quote = False
    escaped = False
    for char in command:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue
        if not in_single_quote and not in_double_quote and char in "*?[]{}":
            return True
    return False


def _has_unquoted_control_operator(command: str) -> bool:
    if _is_safe_python_heredoc_command(command):
        return False
    in_single_quote = False
    in_double_quote = False
    escaped = False
    idx = 0
    while idx < len(command):
        char = command[idx]
        if escaped:
            escaped = False
            idx += 1
            continue
        if char == "\\":
            escaped = True
            idx += 1
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            idx += 1
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            idx += 1
            continue
        if not in_single_quote and not in_double_quote:
            if char == "\n":
                return True
            if char == ";":
                return True
            if command.startswith("&&", idx) or command.startswith("||", idx):
                return True
            if char == "&":
                return True
        idx += 1
    return False


def _has_unquoted_input_redirection(command: str) -> bool:
    in_single_quote = False
    in_double_quote = False
    escaped = False
    idx = 0
    while idx < len(command):
        char = command[idx]
        if escaped:
            escaped = False
            idx += 1
            continue
        if char == "\\":
            escaped = True
            idx += 1
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            idx += 1
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            idx += 1
            continue
        if char == "<" and not in_single_quote and not in_double_quote:
            return True
        idx += 1
    return False


def _has_unquoted_output_redirection(command: str) -> bool:
    in_single_quote = False
    in_double_quote = False
    escaped = False
    idx = 0
    while idx < len(command):
        char = command[idx]
        if escaped:
            escaped = False
            idx += 1
            continue
        if char == "\\":
            escaped = True
            idx += 1
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            idx += 1
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            idx += 1
            continue
        if char == ">" and not in_single_quote and not in_double_quote:
            return True
        idx += 1
    return False


def _is_safe_python_heredoc_command(command: str) -> bool:
    stripped = command.strip()
    return bool(
        re.fullmatch(
            r"python(?:\d+(?:\.\d+)*)?\s+-\s*<<'([A-Za-z_][A-Za-z0-9_]*)'\n.*\n\1",
            stripped,
            flags=re.DOTALL,
        )
    )


def _execute_bash_forbidden_marker_issue(command: str) -> str | None:
    lowered = command.lower()
    normalized = re.sub(r"[^a-z0-9]+", "", lowered)
    public_search = _is_public_marker_search_command(command)
    forbidden_markers = [
        "hiddenverifier",
        "goldpatch",
        "officialverifier",
        "repoharnessrun",
        "swebenchofficial",
        "acceptedlabel",
        "rewardmetadata",
        "finalverifier",
        "groundtruth",
        "rewardextrainfo",
        "rewardextrakeys",
        "evaluatoronly",
        "providersecret",
        "secret",
    ]
    for marker in forbidden_markers:
        if marker in normalized:
            return (
                "execute_bash command references evaluator-only, hidden verifier, "
                "gold patch, or RepoHarness run artifact material."
            )
    evaluator_selector_markers = ["failtopass", "passtopass"]
    for marker in evaluator_selector_markers:
        if marker in normalized and not public_search:
            return "execute_bash command references evaluator-only verifier selector material."
    if re.search(r"(?<![a-z0-9])test[-_\s]?patch(?![a-z0-9])", lowered):
        if not public_search:
            return "execute_bash command references evaluator-only test_patch material."
    return None


def _execute_bash_workspace_path_issue(command: str) -> str | None:
    public_search = _is_public_marker_search_command(command)
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = []
    if not public_search:
        for part in parts:
            if part.startswith("/"):
                return "execute_bash command references an absolute local path instead of a workspace-relative path."
    if re.search(r"(^|[\s'\"])\.\.(?:[/\s'\"]|$)", command):
        return "execute_bash command references a parent-directory path outside the current workspace scope."
    if (
        re.search(r"(^|[\s'\"])(?:~|~[A-Za-z_][A-Za-z0-9_-]*)(?:/|$|[\s'\"])", command)
        and not public_search
    ):
        return "execute_bash command references a shell-expanded home-directory path instead of a workspace-relative path."
    absolute_path_pattern = re.compile(
        r"(?<![A-Za-z0-9_.:-])/"
        r"(?:Users|Volumes|private|tmp|var|home|workspace|repo-harness-run|envs|opt|usr|etc|root|mnt)"
        r"(?:/|\b)",
        flags=re.IGNORECASE,
    )
    if absolute_path_pattern.search(command):
        return "execute_bash command references an absolute local path instead of a workspace-relative path."
    return None


def _execute_bash_git_history_issue(command: str) -> str | None:
    lowered = command.lower()
    if ".git" in lowered:
        return "execute_bash command references Git metadata directly."
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = []
    for idx, part in enumerate(parts):
        if Path(part).name != "git":
            continue
        subcommand = _git_subcommand_after_global_options(parts[idx + 1 :])
        git_issue = _git_subcommand_policy_issue(subcommand, parts[idx + 1 :])
        if git_issue is not None:
            return git_issue
    for sequence in _python_literal_git_sequences(command):
        subcommand = _git_subcommand_after_global_options(sequence[1:])
        git_issue = _git_subcommand_policy_issue(subcommand, sequence[1:])
        if git_issue is not None:
            return "execute_bash inline code attempts to inspect or manipulate Git history."
    return None


def _execute_bash_inline_process_escape_issue(command: str) -> str | None:
    inline_code = _inline_python_code(command)
    if inline_code is None:
        return None
    command = inline_code
    lowered = command.lower()
    risky_markers = [
        "subprocess",
        "os.system",
        ".popen",
        "popen(",
        "exec(",
        "eval(",
        "__import__",
        "importlib",
        "getattr",
        "setattr",
        "__builtins__",
        "compile",
        "globals",
        "locals",
    ]
    if any(marker in lowered for marker in risky_markers):
        return (
            "execute_bash inline Python attempts to spawn subprocesses or execute dynamically "
            "constructed code; Stage 16A requires a controlled launcher before allowing that."
        )
    if re.search(r"['\"]g['\"]\s*\+\s*['\"]it['\"]", command, flags=re.IGNORECASE):
        return "execute_bash inline Python dynamically constructs a git command."
    return None


def _execute_bash_allowlist_issue(command: str) -> str | None:
    if _is_safe_python_heredoc_command(command):
        return None
    try:
        parts = shlex.split(command)
    except ValueError:
        return "execute_bash command cannot be parsed well enough to match the Stage 16A allowlist."
    parts, prefix_issue = _strip_execute_bash_prefix_tokens(parts)
    if prefix_issue is not None:
        return prefix_issue
    if not parts:
        return "execute_bash command is empty after wrapper normalization."
    command_name = _command_token_name(parts[0])
    if command_name in {"rg", "grep"}:
        if _search_command_policy_issue(command_name, parts[1:]) is None:
            return None
        return _search_command_policy_issue(command_name, parts[1:])
    if command_name == "git":
        git_global_issue = _git_global_options_issue(parts[1:])
        if git_global_issue is not None:
            return git_global_issue
        subcommand = _git_subcommand_after_global_options(parts[1:])
        if _git_subcommand_policy_issue(subcommand, parts[1:]) is None:
            return None
        return "execute_bash git command is outside the model-visible Git allowlist."
    if command_name == "pytest":
        if _test_args_are_workspace_relative(parts[1:]):
            return None
        return "execute_bash pytest command includes an unsafe path argument."
    if _is_python_interpreter_token(parts[0]):
        if _python_module_test_command_is_allowed(parts[1:]):
            return None
        if _inline_python_code(command) is not None:
            return None
    return "execute_bash command is outside the Stage 16A model-visible allowlist."


def _python_module_test_command_is_allowed(args: list[str]) -> bool:
    idx = 0
    while idx < len(args):
        token = args[idx]
        if token in {"-u", "-B", "-S", "-E", "-I", "-O", "-OO"}:
            idx += 1
            continue
        if token in {"-W", "-X"}:
            idx += 2
            continue
        if token.startswith("-W") or token.startswith("-X"):
            idx += 1
            continue
        if token == "-m":
            module = args[idx + 1] if idx + 1 < len(args) else ""
            if module not in {"pytest", "unittest"}:
                return False
            return _test_args_are_workspace_relative(args[idx + 2 :])
        if token.startswith("-"):
            idx += 1
            continue
        return False
    return False


def _test_args_are_workspace_relative(args: list[str]) -> bool:
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--":
            idx += 1
            continue
        if arg in PYTEST_FLAG_ALLOWLIST:
            idx += 1
            continue
        if arg == "--tb":
            value = args[idx + 1] if idx + 1 < len(args) else ""
            if value not in PYTEST_TB_VALUES:
                return False
            idx += 2
            continue
        if arg.startswith("--tb="):
            if arg.split("=", 1)[1] not in PYTEST_TB_VALUES:
                return False
            idx += 1
            continue
        if arg == "--maxfail":
            value = args[idx + 1] if idx + 1 < len(args) else ""
            if not value.isdigit() or int(value) < 1:
                return False
            idx += 2
            continue
        if arg.startswith("--maxfail="):
            value = arg.split("=", 1)[1]
            if not value.isdigit() or int(value) < 1:
                return False
            idx += 1
            continue
        if arg.startswith("-"):
            return False
        candidate = arg.split("::", 1)[0]
        if candidate and candidate not in {".", ":"}:
            if not _search_path_token_is_model_visible(candidate):
                return False
        idx += 1
    return True


def _execute_bash_inline_python_visibility_issue(command: str) -> str | None:
    inline_code = _inline_python_code(command)
    if inline_code is None:
        return None
    lowered = inline_code.lower()
    risky_markers = [
        "open(",
        "pathlib",
        "path(",
        ".read_text",
        ".read_bytes",
        ".write_text",
        ".write_bytes",
        ".rglob",
        ".glob",
        ".iterdir",
        "os.listdir",
        "os.scandir",
        "os.walk",
        "os.environ",
        "getenv",
        "sys.path",
        "site.getsitepackages",
        "site.getusersitepackages",
        "sysconfig.get_paths",
        "pkgutil.iter_modules",
    ]
    if any(marker in lowered for marker in risky_markers):
        return (
            "execute_bash inline Python attempts filesystem, environment, or path enumeration. "
            "Use read_file, grep, list_files, or a controlled launcher instead."
        )
    positive_policy_issue = _inline_python_positive_policy_issue(command)
    if positive_policy_issue is not None:
        return positive_policy_issue
    return None


def _inline_python_positive_policy_issue(command: str) -> str | None:
    source = _inline_python_source(command)
    if source is None:
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return "execute_bash inline Python cannot be parsed into the Stage 16A safe diagnostic subset."
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                if alias.name not in {"os", "sys"} or alias.asname is not None:
                    return "execute_bash inline Python imports modules outside the Stage 16A safe diagnostic subset."
            continue
        if isinstance(statement, ast.Expr) and _is_allowed_inline_python_print(statement.value):
            continue
        return "execute_bash inline Python is outside the Stage 16A safe diagnostic subset."
    return None


def _inline_python_source(command: str) -> str | None:
    heredoc_match = re.fullmatch(
        r"python(?:\d+(?:\.\d+)*)?\s+-\s*<<'([A-Za-z_][A-Za-z0-9_]*)'\n(?P<body>.*)\n\1",
        command.strip(),
        flags=re.DOTALL,
    )
    if heredoc_match:
        return heredoc_match.group("body")
    return _inline_python_code(command)


def _is_allowed_inline_python_print(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Name) or node.func.id != "print":
        return False
    for arg in node.args:
        if not _is_allowed_inline_python_print_arg(arg):
            return False
    for keyword in node.keywords:
        if keyword.arg != "file" or not _is_sys_attribute(keyword.value, "stderr"):
            return False
    return True


def _is_allowed_inline_python_print_arg(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool, type(None))):
        return True
    if _is_sys_attribute(node, "executable"):
        return True
    if isinstance(node, ast.Call) and _is_os_getcwd_call(node):
        return True
    return False


def _is_sys_attribute(node: ast.AST, attribute: str) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == attribute
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    )


def _is_os_getcwd_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "getcwd"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "os"
        and not node.args
        and not node.keywords
    )


def _is_public_marker_search_command(command: str) -> bool:
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    if not parts:
        return False
    command_name = Path(parts[0]).name
    if command_name in {"rg", "grep"}:
        return _search_command_policy_issue(command_name, parts[1:]) is None
    if len(parts) >= 2 and Path(parts[0]).name == "git" and parts[1] == "grep":
        return _search_command_paths_are_workspace_relative(parts[2:])
    return False


def _git_subcommand_policy_issue(subcommand: str | None, args: list[str]) -> str | None:
    git_global_issue = _git_global_options_issue(args)
    if git_global_issue is not None:
        return git_global_issue
    if subcommand is None:
        return "execute_bash git invocation is incomplete and cannot be audited safely."
    if subcommand == "status":
        if not _git_status_args_are_workspace_only(_args_after_git_subcommand(args)):
            return "execute_bash git status command includes an unsafe pathspec."
        return None
    if subcommand == "ls-files":
        if not _git_ls_files_args_are_workspace_only(_args_after_git_subcommand(args)):
            return "execute_bash git ls-files command includes an unsafe pathspec."
        return None
    if subcommand == "grep":
        if not _git_grep_args_are_workspace_only(_args_after_git_subcommand(args)):
            return "execute_bash git grep command includes a revision or unsafe pathspec."
        return None
    if subcommand == "diff":
        if not _git_diff_args_are_workspace_only(_args_after_git_subcommand(args)):
            return "execute_bash git diff command includes a revision, ref, or unsafe pathspec."
        return None
    return "execute_bash git command is outside the Stage 16A model-visible allowlist."


def _args_after_git_subcommand(args: list[str]) -> list[str]:
    subcommand = _git_subcommand_after_global_options(args)
    if subcommand is None:
        return []
    for idx, token in enumerate(args):
        if token == subcommand:
            return args[idx + 1 :]
    return []


def _git_global_options_issue(args: list[str]) -> str | None:
    option_with_path = {"-C", "--work-tree"}
    forbidden_option_with_value = {"-c", "--config-env", "--exec-path", "--git-dir", "--namespace"}
    idx = 0
    while idx < len(args):
        token = args[idx]
        if token == "--":
            return None
        if token in option_with_path:
            value = args[idx + 1] if idx + 1 < len(args) else ""
            if not _search_path_token_is_model_visible(value):
                return "execute_bash git global option references a hidden, runtime-private, or non-workspace path."
            idx += 2
            continue
        if any(token.startswith(option + "=") for option in option_with_path if option.startswith("--")):
            value = token.split("=", 1)[1]
            if not _search_path_token_is_model_visible(value):
                return "execute_bash git global option references a hidden, runtime-private, or non-workspace path."
            idx += 1
            continue
        if token in forbidden_option_with_value or any(
            token.startswith(option + "=") for option in forbidden_option_with_value if option.startswith("--")
        ):
            return "execute_bash git global option is outside the Stage 16A model-visible allowlist."
        if token.startswith("-"):
            return "execute_bash git global option is outside the Stage 16A model-visible allowlist."
        return None
    return None


def _git_status_args_are_workspace_only(args: list[str]) -> bool:
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--":
            idx += 1
            continue
        if arg in {"--short", "-s", "--porcelain"} or arg in {"--porcelain=v1", "--porcelain=1"}:
            idx += 1
            continue
        if arg.startswith("-"):
            return False
        if not _search_path_token_is_model_visible(arg):
            return False
        idx += 1
    return True


def _git_ls_files_args_are_workspace_only(args: list[str]) -> bool:
    for arg in args:
        if arg == "--":
            continue
        if arg.startswith("-"):
            return False
        if not _search_path_token_is_model_visible(arg):
            return False
    return True


def _git_grep_args_are_workspace_only(args: list[str]) -> bool:
    seen_query = False
    after_double_dash = False
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--":
            after_double_dash = True
            idx += 1
            continue
        if not after_double_dash and arg == "-e":
            query = args[idx + 1] if idx + 1 < len(args) else ""
            if not query:
                return False
            seen_query = True
            idx += 2
            continue
        if not after_double_dash and arg in {"-C", "-A", "-B", "-m"}:
            value = args[idx + 1] if idx + 1 < len(args) else ""
            if not value.isdigit():
                return False
            idx += 2
            continue
        if not after_double_dash and re.fullmatch(r"-(?:C|A|B|m)\d+", arg):
            idx += 1
            continue
        if arg.startswith("-"):
            return False
        if not after_double_dash and not seen_query:
            seen_query = True
            idx += 1
            continue
        if _is_git_ref_like_token(arg):
            return False
        if not _search_path_token_is_model_visible(arg):
            return False
        if not after_double_dash and not _looks_like_workspace_path_argument(arg):
            return False
        idx += 1
    return seen_query


def _git_diff_args_are_workspace_only(args: list[str]) -> bool:
    after_double_dash = False
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--":
            after_double_dash = True
            idx += 1
            continue
        if not after_double_dash:
            if arg in {"--name-only", "--stat"}:
                idx += 1
                continue
            if arg in {"-U", "--unified"}:
                value = args[idx + 1] if idx + 1 < len(args) else ""
                if not value.isdigit():
                    return False
                idx += 2
                continue
            if re.fullmatch(r"-U\d+", arg):
                idx += 1
                continue
            if arg.startswith("--unified="):
                value = arg.split("=", 1)[1]
                if not value.isdigit():
                    return False
                idx += 1
                continue
            if arg.startswith("-"):
                return False
            if _is_git_ref_like_token(arg):
                return False
            if not _search_path_token_is_model_visible(arg):
                return False
            if not _looks_like_workspace_path_argument(arg):
                return False
            idx += 1
            continue
        if _is_git_ref_like_token(arg):
            return False
        if not _search_path_token_is_model_visible(arg):
            return False
        idx += 1
    return True


def _is_git_ref_like_token(value: str) -> bool:
    lowered = value.lower()
    if lowered in {"head", "fetch_head", "orig_head", "main", "master", "develop"}:
        return True
    if lowered.startswith(("head~", "head^", "origin/", "refs/", "tags/", "remotes/")):
        return True
    if re.fullmatch(r"[0-9a-f]{7,40}", lowered):
        return True
    if any(marker in value for marker in ("..", "^", "~", "@{")):
        return True
    return False


def _search_command_policy_issue(command_name: str, args: list[str]) -> str | None:
    if command_name == "rg":
        issue = _rg_search_option_issue(args)
        if issue is not None:
            return issue
    if command_name == "grep":
        issue = _grep_search_option_issue(args)
        if issue is not None:
            return issue
    if not _search_command_paths_are_workspace_relative(args):
        return "execute_bash search command includes a hidden, runtime-private, or non-workspace-relative path."
    return None


def _rg_search_option_issue(args: list[str]) -> str | None:
    unsafe_long_options = {
        "--files",
        "--hidden",
        "--no-ignore",
        "--no-ignore-vcs",
        "--no-ignore-parent",
        "--no-ignore-global",
        "--no-ignore-dot",
        "--no-ignore-files",
        "--unrestricted",
        "--ignore-file",
        "--pre",
        "--pre-glob",
        "--follow",
        "--config",
        "--type-add",
        "--type-set",
        "--type-clear",
        "--type",
        "--type-not",
    }
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--":
            idx += 1
            continue
        if arg in unsafe_long_options or any(arg.startswith(option + "=") for option in unsafe_long_options):
            return "execute_bash rg command uses hidden-file, ignore-bypass, symlink-following, or file-listing options."
        if arg in {"-f", "--file"} or arg.startswith("--file="):
            return "execute_bash rg pattern-file reads are not allowed in Stage 16A."
        if arg.startswith("--ignore-file="):
            return "execute_bash rg ignore-file reads are not allowed in Stage 16A."
        if arg.startswith("--pre="):
            return "execute_bash rg preprocessor execution is not allowed in Stage 16A."
        if arg.startswith("-") and not arg.startswith("--"):
            flags = arg[1:]
            if "u" in flags or "L" in flags:
                return "execute_bash rg command uses hidden-file, ignore-bypass, or symlink-following short options."
            if "t" in flags or "T" in flags:
                return "execute_bash rg type filtering and custom type options are not allowed in Stage 16A."
            if "g" in flags and len(flags) > 1:
                value = flags.split("g", 1)[1]
                if value and not _search_path_token_is_model_visible(value):
                    return "execute_bash rg glob targets hidden, runtime-private, or glob-expanded paths."
        if arg in {"-g", "--glob", "--iglob"}:
            value = args[idx + 1] if idx + 1 < len(args) else ""
            if not _search_path_token_is_model_visible(value):
                return "execute_bash rg glob targets hidden, runtime-private, or glob-expanded paths."
            idx += 2
            continue
        if arg.startswith("--glob=") or arg.startswith("--iglob="):
            value = arg.split("=", 1)[1]
            if not _search_path_token_is_model_visible(value):
                return "execute_bash rg glob targets hidden, runtime-private, or glob-expanded paths."
        if arg in {"--ignore-file", "--pre"}:
            return "execute_bash rg command uses file-reading or command-execution options outside the Stage 16A allowlist."
        idx += 1
    return None


def _grep_search_option_issue(args: list[str]) -> str | None:
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--":
            idx += 1
            continue
        if arg in {"-R", "-r", "--recursive", "--dereference-recursive"}:
            return "execute_bash grep recursive search is not allowed in Stage 16A."
        if arg.startswith("-") and not arg.startswith("--") and any(flag in arg[1:] for flag in {"R", "r"}):
            return "execute_bash grep recursive search is not allowed in Stage 16A."
        if arg == "-d":
            value = args[idx + 1] if idx + 1 < len(args) else ""
            if value == "recurse":
                return "execute_bash grep recursive search is not allowed in Stage 16A."
            idx += 2
            continue
        if arg.startswith("-d") and arg[2:] == "recurse":
            return "execute_bash grep recursive search is not allowed in Stage 16A."
        if arg == "--directories=recurse":
            return "execute_bash grep recursive search is not allowed in Stage 16A."
        if arg in {"-f", "--file"} or arg.startswith("--file="):
            return "execute_bash grep pattern-file reads are not allowed in Stage 16A."
        if (
            arg in {"--exclude-from", "--include-from"}
            or arg.startswith("--exclude-from=")
            or arg.startswith("--include-from=")
        ):
            return "execute_bash grep include/exclude file reads are not allowed in Stage 16A."
        idx += 1
    return None


def _search_command_paths_are_workspace_relative(parts: list[str]) -> bool:
    after_double_dash = False
    skip_next = False
    seen_query = False
    for idx, part in enumerate(parts):
        if skip_next:
            skip_next = False
            continue
        if part == "--":
            after_double_dash = True
            continue
        if part in {"-e", "-f", "-g", "--glob", "--path-separator", "-C", "-A", "-B", "-m"}:
            skip_next = True
            continue
        if part.startswith("-"):
            continue
        if not seen_query and not after_double_dash:
            seen_query = True
            continue
        if not _search_path_token_is_model_visible(part):
            return False
    return True


def _search_path_token_is_model_visible(value: str) -> bool:
    normalized = value.replace("\\", "/")
    if not normalized or normalized in {".", "./"}:
        return True
    if normalized.startswith(":"):
        return False
    if ":" in normalized:
        return False
    if any(char in value for char in "*?[]{}"):
        return False
    if value.startswith("~") or Path(value).is_absolute():
        return False
    parts = PurePosixPath(normalized).parts
    if ".." in parts:
        return False
    return not _search_path_token_is_hidden_or_runtime(value)


def _search_path_token_is_hidden_or_runtime(value: str) -> bool:
    normalized = value.replace("\\", "/")
    hidden_runtime_names = {
        ".git",
        ".env",
        ".repo_harness_env_overlay",
        ".repo_harness_runtime",
        "runtime_private",
    }
    for part in PurePosixPath(normalized).parts:
        if part in {"", ".", "/"}:
            continue
        lowered = part.lower()
        if lowered in hidden_runtime_names:
            return True
        compact = re.sub(r"[^a-z0-9]+", "", lowered)
        if any(
            marker in compact
            for marker in {
                "runtimeprivate",
                "repoharnessruntime",
                "repoharnessenvoverlay",
            }
        ):
            return True
        if part.startswith("."):
            return True
    return False


def _looks_like_workspace_path_argument(value: str) -> bool:
    if "/" in value or value in {".", ".."}:
        return True
    suffixes = (".py", ".txt", ".md", ".rst", ".toml", ".yaml", ".yml", ".json")
    return value.endswith(suffixes)


def _inline_python_code(command: str) -> str | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    for idx, part in enumerate(parts):
        if not _is_python_interpreter_token(part):
            continue
        inline = _python_inline_code_from_args(parts[idx + 1 :], original_command=command)
        if inline is not None:
            return inline
    if re.search(r"\bpython(?:\d+(?:\.\d+)*)?\s+-\s*<<", command):
        return command
    return None


def _python_inline_code_from_args(args: list[str], *, original_command: str) -> str | None:
    idx = 0
    while idx < len(args):
        token = args[idx]
        if token == "-c":
            return args[idx + 1] if idx + 1 < len(args) else ""
        if token == "-":
            return original_command
        if token in {"-u", "-B", "-S", "-E", "-I", "-O", "-OO"}:
            idx += 1
            continue
        if token in {"-W", "-X"}:
            idx += 2
            continue
        if token.startswith("-W") or token.startswith("-X"):
            idx += 1
            continue
        if token.startswith("-"):
            idx += 1
            continue
        return None
    return None


def _execute_bash_shared_dependency_issue(
    command: str,
    *,
    shared_dependency_environment_expected: bool,
    shared_dependency_environment_roots: list[str] | None,
) -> tuple[str, str] | None:
    if _command_mutates_dependency_environment(command):
        return (
            "execute_bash_shared_dependency_write_guard",
            "execute_bash command attempts to install or mutate dependencies from a model-visible shell.",
        )
    if shared_dependency_environment_expected and not shared_dependency_environment_roots:
        return (
            "execute_bash_shared_dependency_roots_missing",
            (
                "execute_bash is disabled for shared dependency environment episodes unless "
                "runtime-only shared_dependency_environment_roots are available."
            ),
        )
    for root in shared_dependency_environment_roots or []:
        normalized_root = root.strip()
        if normalized_root and normalized_root in command:
            return (
                "execute_bash_shared_dependency_root_access",
                "execute_bash command references a runtime-only shared dependency environment path.",
            )
    return None


def _command_mutates_dependency_environment(command: str) -> bool:
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    parts, _ = _strip_execute_bash_prefix_tokens(parts)
    if not parts:
        return False
    command_name = Path(parts[0]).name
    lowered_name = command_name.lower()
    args = parts[1:]
    if re.fullmatch(r"pip(?:\d+(?:\.\d+)*)?", lowered_name):
        return any(arg in {"install", "uninstall", "download", "wheel"} for arg in args) or args[:2] == [
            "cache",
            "purge",
        ] or args[:2] == [
            "cache",
            "remove",
        ]
    if lowered_name in {"pip-compile", "pip-sync"}:
        return True
    if _is_python_interpreter_token(parts[0]):
        return _python_m_pip_mutates_environment(args)
    if lowered_name == "uv":
        if _package_manager_subcommand_in(args, {"add", "sync"}):
            return True
        if args[:2] == ["pip", "compile"]:
            return True
        if args[:2] == ["tool", "run"] or args[:2] == ["tool", "install"] or args[:2] == ["tool", "upgrade"] or args[:2] == ["tool", "uninstall"]:
            return True
        for idx, arg in enumerate(args):
            if arg == "pip" and args[idx + 1 : idx + 2] in (["install"], ["uninstall"]):
                return True
        if args[:2] == ["pip", "install"] or args[:2] == ["pip", "uninstall"]:
            return True
        if args and args[0] == "run" and any(
            arg == "--with"
            or arg.startswith("--with=")
            or arg == "--with-editable"
            or arg.startswith("--with-editable=")
            or arg == "--with-requirements"
            or arg.startswith("--with-requirements=")
            for arg in args
        ):
            return True
    if lowered_name == "poetry":
        return _package_manager_subcommand_in(args, {"add", "install", "update", "remove"})
    if lowered_name == "pipenv":
        return _package_manager_subcommand_in(args, {"install", "uninstall", "update"})
    if lowered_name == "pipx":
        return _package_manager_subcommand_in(args, {"install", "run", "upgrade", "uninstall", "inject"})
    if lowered_name == "virtualenv":
        return True
    if lowered_name == "npm":
        return _package_manager_subcommand_in(
            args,
            {"i", "install", "ci", "exec", "x", "create", "pack", "run", "run-script", "test", "explore"},
        )
    if lowered_name == "pnpm":
        return _package_manager_subcommand_in(args, {"add", "install", "dlx", "create", "pack", "run", "test"})
    if lowered_name == "yarn":
        return _package_manager_subcommand_in(args, {"add", "install", "dlx", "create", "pack", "run", "test", "node"})
    if lowered_name == "pdm":
        return _package_manager_subcommand_in(args, {"add", "install", "remove", "update"})
    if lowered_name == "rye":
        return _package_manager_subcommand_in(args, {"add", "sync"})
    if lowered_name == "pixi":
        return _package_manager_subcommand_in(args, {"add", "install"})
    if lowered_name in {"bun", "bunx"}:
        if lowered_name == "bunx":
            return True
        return _package_manager_subcommand_in(args, {"install", "add", "run", "x"})
    if lowered_name in {"conda", "mamba", "micromamba"}:
        return _package_manager_subcommand_in(args, {"create", "install", "update", "remove"})
    if lowered_name == "gem":
        return _package_manager_subcommand_in(args, {"build", "install", "update", "uninstall"})
    if lowered_name in {"apt", "apt-get", "brew", "apk", "yum", "dnf", "zypper"}:
        return _package_manager_subcommand_in(args, {"add", "install"})
    if lowered_name == "pacman":
        return any(arg == "-S" or arg.startswith("-S") for arg in args)
    if lowered_name == "cargo":
        return _package_manager_subcommand_in(args, {"add", "fetch", "install", "run", "update"})
    if lowered_name == "go":
        if args[:2] == ["mod", "download"]:
            return True
        return _package_manager_subcommand_in(args, {"get", "install", "run"})
    if lowered_name == "bundle":
        return _package_manager_subcommand_in(args, {"install"})
    if lowered_name == "composer":
        return _package_manager_subcommand_in(args, {"install", "require"})
    if lowered_name == "pear":
        return _package_manager_subcommand_in(args, {"install"})
    if lowered_name in {"nvm", "asdf", "pyenv", "rbenv"}:
        return _package_manager_subcommand_in(args, {"install"})
    if lowered_name == "rustup":
        return _package_manager_subcommand_in(args, {"update"})
    if lowered_name == "cpan":
        return True
    if lowered_name == "uv" and args[:2] == ["tool", "run"]:
        return True
    return False


def _package_manager_subcommand_in(args: list[str], mutating_subcommands: set[str]) -> bool:
    for arg in args:
        if arg == "--":
            return False
        if arg in mutating_subcommands:
            return True
    return False


def _python_m_pip_mutates_environment(args: list[str]) -> bool:
    idx = 0
    while idx < len(args):
        token = args[idx]
        if token == "-m":
            module = args[idx + 1] if idx + 1 < len(args) else ""
            if module != "pip":
                return False
            pip_args = args[idx + 2 :]
            return any(arg in {"install", "uninstall", "download", "wheel"} for arg in pip_args) or pip_args[:2] == [
                "cache",
                "purge",
            ] or pip_args[:2] == [
                "cache",
                "remove",
            ]
        if token in {"-u", "-B", "-S", "-E", "-I", "-O", "-OO"}:
            idx += 1
            continue
        if token in {"-W", "-X"}:
            idx += 2
            continue
        if token.startswith("-W") or token.startswith("-X"):
            idx += 1
            continue
        if token.startswith("-"):
            idx += 1
            continue
        return False
    return False


def _git_subcommand_after_global_options(parts: list[str]) -> str | None:
    option_with_value = {
        "-C",
        "-c",
        "--config-env",
        "--exec-path",
        "--git-dir",
        "--namespace",
        "--work-tree",
    }
    idx = 0
    while idx < len(parts):
        token = parts[idx]
        if token == "--":
            idx += 1
            continue
        if token in option_with_value:
            idx += 2
            continue
        if any(token.startswith(prefix + "=") for prefix in option_with_value if prefix.startswith("--")):
            idx += 1
            continue
        if token.startswith("-"):
            idx += 1
            continue
        return token
    return None


def _python_literal_git_sequences(command: str) -> list[list[str]]:
    matches = re.findall(r"\[([^\]]*['\"]git['\"][^\]]*)\]", command, flags=re.IGNORECASE | re.DOTALL)
    sequences: list[list[str]] = []
    for match in matches:
        literals = re.findall(r"['\"]([^'\"]+)['\"]", match)
        if literals and Path(literals[0]).name == "git":
            sequences.append(literals)
    return sequences
