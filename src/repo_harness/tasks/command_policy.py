"""Stage 12 command policy helpers for task, setup, test, and model bash commands."""

from __future__ import annotations

import shlex
import re
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
            continue
        if command_name == "time":
            remaining = remaining[1:]
            while remaining and remaining[0].startswith("-"):
                remaining = remaining[1:]
            if not remaining:
                return [], "execute_bash time wrapper does not contain a command to audit."
            continue
        if command_name == "nice":
            remaining = remaining[1:]
            if remaining and remaining[0] == "-n":
                remaining = remaining[2:]
            elif remaining and re.fullmatch(r"-\d+", remaining[0]):
                remaining = remaining[1:]
            while remaining and remaining[0].startswith("--"):
                return [], "execute_bash nice wrapper long options are not allowed in Stage 16A."
            if not remaining:
                return [], "execute_bash nice wrapper does not contain a command to audit."
            continue
        break
    return remaining, None


def _looks_like_environment_assignment(value: str) -> bool:
    if "=" not in value:
        return False
    name, _ = value.split("=", 1)
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name))


def _execute_bash_forbidden_marker_issue(command: str) -> str | None:
    lowered = command.lower()
    public_search = _is_public_marker_search_command(command)
    forbidden_literals = [
        "/repo-harness-run",
        "repo_harness_run",
        "hidden verifier",
        "hidden_verifier",
        "gold patch",
        "gold_patch",
        "official verifier",
        "official_verifier",
        "swebench_official",
    ]
    for marker in forbidden_literals:
        if marker in lowered:
            return (
                "execute_bash command references evaluator-only, hidden verifier, "
                "gold patch, or RepoHarness run artifact material."
            )
    evaluator_selector_markers = ["fail_to_pass", "pass_to_pass"]
    for marker in evaluator_selector_markers:
        if marker in lowered and not public_search:
            return "execute_bash command references evaluator-only verifier selector material."
    if re.search(r"(?<![a-z0-9])test_patch(?![a-z0-9])", lowered):
        if not public_search:
            return "execute_bash command references evaluator-only test_patch material."
    return None


def _execute_bash_workspace_path_issue(command: str) -> str | None:
    if re.search(r"(^|[\s'\"])\.\.(?:[/\s'\"]|$)", command):
        return "execute_bash command references a parent-directory path outside the current workspace scope."
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
    blocked_git_subcommands = {
        "archive",
        "bisect",
        "blame",
        "branch",
        "bundle",
        "cat-file",
        "checkout",
        "cherry-pick",
        "clone",
        "fetch",
        "format-patch",
        "log",
        "merge-base",
        "pull",
        "push",
        "reflog",
        "remote",
        "reset",
        "rev-list",
        "show",
        "submodule",
        "switch",
        "tag",
    }
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = []
    for idx, part in enumerate(parts):
        if Path(part).name != "git":
            continue
        subcommand = _git_subcommand_after_global_options(parts[idx + 1 :])
        if subcommand in blocked_git_subcommands:
            return "execute_bash command attempts to inspect or manipulate Git history."
    for sequence in _python_literal_git_sequences(command):
        subcommand = _git_subcommand_after_global_options(sequence[1:])
        if subcommand in blocked_git_subcommands:
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
    ]
    if any(marker in lowered for marker in risky_markers):
        return (
            "execute_bash inline Python attempts to spawn subprocesses or execute dynamically "
            "constructed code; Stage 16A requires a controlled launcher before allowing that."
        )
    if re.search(r"['\"]g['\"]\s*\+\s*['\"]it['\"]", command, flags=re.IGNORECASE):
        return "execute_bash inline Python dynamically constructs a git command."
    return None


def _is_public_marker_search_command(command: str) -> bool:
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    if not parts:
        return False
    if Path(parts[0]).name in {"rg", "grep"}:
        return _search_command_paths_are_workspace_relative(parts[1:])
    if len(parts) >= 2 and Path(parts[0]).name == "git" and parts[1] == "grep":
        return _search_command_paths_are_workspace_relative(parts[2:])
    return False


def _search_command_paths_are_workspace_relative(parts: list[str]) -> bool:
    after_double_dash = False
    skip_next = False
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
        if idx == 0 and not after_double_dash:
            continue
        if _looks_like_workspace_path_argument(part):
            if Path(part).is_absolute() or ".." in PurePosixPath(part.replace("\\", "/")).parts:
                return False
    return True


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
        if Path(part).name not in {"python", "python3"}:
            continue
        if idx + 1 < len(parts) and parts[idx + 1] == "-c":
            return parts[idx + 2] if idx + 2 < len(parts) else ""
        if idx + 1 < len(parts) and parts[idx + 1] == "-":
            return command
    if re.search(r"\bpython3?\s+-\s*<<", command):
        return command
    return None


def _execute_bash_shared_dependency_issue(
    command: str,
    *,
    shared_dependency_environment_expected: bool,
    shared_dependency_environment_roots: list[str] | None,
) -> tuple[str, str] | None:
    lowered = command.lower()
    write_patterns = [
        "pip install",
        "pip uninstall",
        "python -m pip install",
        "python -m pip uninstall",
        "uv pip install",
        "uv pip uninstall",
        "npm install",
        "npm ci",
        "pnpm install",
        "yarn add",
        "yarn install",
    ]
    if any(pattern in lowered for pattern in write_patterns):
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
