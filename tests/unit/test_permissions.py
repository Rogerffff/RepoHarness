from pathlib import Path

import pytest

from repo_harness.errors import WorkspaceError
from repo_harness.permissions import PermissionContext, PermissionSystem
from repo_harness.tools import build_tool


class FakeWorkspaceFacade:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def resolve_workspace_path(
        self,
        workspace_path: str | Path,
        requested_path: str | Path,
        *,
        must_exist: bool = False,
    ) -> Path:
        raw = Path(requested_path)
        candidate = raw if raw.is_absolute() else self.root / raw
        resolved = candidate.resolve() if must_exist else candidate.parent.resolve() / candidate.name
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError(f"路径越过 workspace 边界：{requested_path}") from exc
        if any(part.startswith(".env") for part in resolved.relative_to(self.root).parts):
            raise WorkspaceError(f"拒绝访问敏感路径：{requested_path}")
        if must_exist and not resolved.exists():
            raise WorkspaceError(f"路径不存在：{requested_path}")
        return resolved


def test_workspace_outside_path_is_denied_before_mode_fallback(tmp_path: Path):
    decision = _check(
        tmp_path,
        tool_name="read_file",
        args={"path": "../secret.txt"},
        mode="auto",
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "workspace_boundary_or_sensitive_path"


@pytest.mark.parametrize(
    "command",
    [
        "curl https://example.com",
        "git fetch",
        "ls /",
        "ls $HOME",
        "find /",
        "pytest -q | tee out.txt",
        "PYTHONPATH=. pytest -q",
        "pytest -q > out.txt",
        "sleep 1 &",
    ],
)
def test_bash_unsafe_commands_are_denied(tmp_path: Path, command: str):
    decision = _check(
        tmp_path,
        tool_name="bash",
        args={"command": command},
        mode="auto",
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "bash_command_safety"


@pytest.mark.parametrize(
    "command, expected_fragment",
    [
        ("cd src", "Command is not in the stage eight bash allowlist: cd"),
        ("cd /workspace && python -c 'print(1)'", "Unsupported shell syntax: &&"),
        ("python -c 'print(1); print(2)'", "Unsupported shell syntax: ;"),
        ("pytest -q | tee out.txt", "Unsupported shell syntax: |"),
        ("python -c 'print(1)'", "Command is not in the stage eight bash allowlist: python"),
    ],
)
def test_bash_denial_reason_includes_recovery_guidance(
    tmp_path: Path,
    command: str,
    expected_fragment: str,
):
    decision = _check(
        tmp_path,
        tool_name="bash",
        args={"command": command},
        mode="auto",
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "bash_command_safety"
    assert expected_fragment in decision.reason
    assert "bash is restricted" in decision.reason
    assert "Use cwd for directories" in decision.reason
    assert "run_tests for configured test feedback" in decision.reason


@pytest.mark.parametrize(
    "command",
    [
        "git diff --no-index /etc/hosts file.py",
        "git show /etc/hosts",
        "git ls-files /etc",
        "ruff check /etc",
        "mypy /etc",
        "python -m compileall /etc",
    ],
)
def test_bash_allowed_commands_reject_outside_path_arguments(tmp_path: Path, command: str):
    decision = _check(
        tmp_path,
        tool_name="bash",
        args={"command": command},
        mode="auto",
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "bash_command_safety"


def test_bash_pytest_routes_to_run_tests_and_is_allowed_in_auto(tmp_path: Path):
    decision = PermissionSystem().check(
        tool_call_id="call_bash",
        requested_tool_name="bash",
        effective_tool_name="run_tests",
        tool_definition=build_tool("run_tests"),
        requested_arguments={"command": "pytest -q"},
        normalized_arguments={"command": "pytest -q", "cwd": ".", "timeout_sec": 30},
        permission_context=PermissionContext(mode="auto", test_command="pytest -q"),
        workspace_facade=FakeWorkspaceFacade(tmp_path),
        workspace_path=tmp_path.as_posix(),
    )

    assert decision.decision == "allow"
    assert decision.effective_tool_name == "run_tests"


@pytest.mark.parametrize("mode", ["plan", "ask", "deny"])
def test_non_read_tools_are_denied_by_conservative_modes(tmp_path: Path, mode: str):
    decision = _check(
        tmp_path,
        tool_name="edit_file",
        args={"path": "file.py", "old_text": "a", "new_text": "b"},
        mode=mode,
    )

    assert decision.decision == "deny"
    if mode == "ask":
        assert decision.requires_user_input is True
        assert decision.non_interactive_resolution == "deny"


def _check(tmp_path: Path, *, tool_name: str, args: dict, mode: str):
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "file.py").write_text("a", encoding="utf-8")
    return PermissionSystem().check(
        tool_call_id="call",
        requested_tool_name=tool_name,
        effective_tool_name=tool_name,
        tool_definition=build_tool(tool_name),
        requested_arguments=args,
        normalized_arguments=args | ({"cwd": "."} if tool_name == "bash" else {}),
        permission_context=PermissionContext(mode=mode, test_command="pytest -q"),
        workspace_facade=FakeWorkspaceFacade(tmp_path),
        workspace_path=tmp_path.as_posix(),
    )
