"""Stage 12 command policy helpers for task, setup, test, and model bash commands."""

from __future__ import annotations

import shlex
from pathlib import Path
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
