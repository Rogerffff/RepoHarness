from pathlib import Path

import pytest

from repo_harness.errors import TaskValidationError
from repo_harness.tasks.command_policy import (
    CommandPolicy,
    TestCommandPolicy,
    evaluate_model_bash_command,
    evaluate_model_execute_bash_command,
    is_recognized_test_command,
    validate_setup_command,
    validate_test_command,
)


def test_setup_command_policy_rejects_unallowlisted_install_command(tmp_path: Path):
    with pytest.raises(TaskValidationError, match="setup_command"):
        validate_setup_command("python -m pip install -e .", tmp_path)


def test_setup_command_policy_allows_repo_local_python_script(tmp_path: Path):
    (tmp_path / "setup_task.py").write_text("print('ok')\n", encoding="utf-8")

    decision = validate_setup_command("python setup_task.py", tmp_path)

    assert decision.decision == "allow"
    assert decision.command_category == "setup"


def test_setup_command_policy_can_validate_shape_before_archive_materialization():
    decision = validate_setup_command("python setup_task.py", None)

    assert decision.decision == "allow"
    assert decision.matched_rule == "setup_python_repo_script_shape_allowlist"


def test_test_command_policy_accepts_pytest_and_rejects_shell():
    assert validate_test_command("python -m pytest -q").decision == "allow"
    with pytest.raises(TaskValidationError, match="shell"):
        validate_test_command("pytest -q && echo hidden")


def test_model_bash_hidden_test_command_is_denied():
    policy = TestCommandPolicy(
        public_test_command="pytest -q",
        hidden_formal_verifier_command="python -m pytest tests/hidden -q",
    )

    decision = evaluate_model_bash_command(
        "python -m pytest tests/hidden -q",
        configured_test_command="pytest -q",
        test_feedback_policy="public_only",
        policy=policy,
    )

    assert decision.decision == "deny"
    assert decision.command_category == "hidden_test"


def test_model_bash_pytest_disabled_is_denied():
    decision = CommandPolicy().evaluate_model_bash(
        "pytest -q",
        configured_test_command="pytest -q",
        test_feedback_policy="disabled",
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "test_feedback_disabled_blocks_bash_test"


def test_model_bash_pytest_public_feedback_routes_to_run_tests():
    decision = CommandPolicy().evaluate_model_bash(
        "python -m pytest -q",
        configured_test_command="pytest -q",
        test_feedback_policy="structured_public_feedback",
    )

    assert decision.decision == "route_to_run_tests"
    assert decision.command_category == "public_test"


def test_tox_and_nox_are_recognized_as_test_commands_for_policy_gate():
    assert CommandPolicy().evaluate_model_bash(
        "tox",
        configured_test_command="pytest -q",
        test_feedback_policy="public_only",
    ).decision == "route_to_run_tests"
    assert CommandPolicy().evaluate_model_bash(
        "nox -s tests",
        configured_test_command="pytest -q",
        test_feedback_policy="disabled",
    ).decision == "deny"
    assert is_recognized_test_command("pytest tests/test_example.py -q", "pytest -q")


def test_unittest_is_recognized_as_test_command_for_policy_gate():
    decision = CommandPolicy().evaluate_model_bash(
        "python -m unittest tests.test_example",
        configured_test_command="pytest -q",
        test_feedback_policy="disabled",
    )

    assert decision.decision == "deny"
    assert decision.command_category == "public_test"
    assert decision.reason_code == "denied_by_final_only_feedback_policy"
    assert decision.safe_argv == ["python", "-m", "unittest", "tests.test_example"]


def test_execute_bash_policy_allows_current_worktree_diagnostics_without_false_positive():
    commands = [
        "bash -lc 'python -m pytest -q lib/matplotlib/tests/test_patches.py'",
        "git status --short",
        "git diff -- src/pkg.py",
        "git grep InvalidURL",
        "git ls-files",
        "bash -lc 'git status --short'",
        "bash -lc 'git diff -- src/pkg.py'",
        "env bash -lc 'git status --short'",
        "command bash -lc 'git status --short'",
        "exec bash -lc 'git status --short'",
        "rg subprocess src",
        "pytest tests/test_subprocess.py -q",
        "rg 'exec(' src",
        "rg 'eval(' src",
        "rg '$foo' src",
        "python -c 'print(\"$literal\")'",
        "python - <<'PY'\nprint('$literal')\nPY",
        "rg 'test_patch' docs/public_note.txt",
        "git grep 'FAIL_TO_PASS' -- docs/public_readme.md",
        "bash -lc \"git grep 'FAIL_TO_PASS' -- docs/public_readme.md\"",
    ]

    for command in commands:
        decision = evaluate_model_execute_bash_command(command)
        assert decision.decision == "allow", command


@pytest.mark.parametrize(
    ("command", "reason_code"),
    [
        ("cat /repo-harness-run/task.yaml", "execute_bash_evaluator_only_marker"),
        ("cat gold_patch.diff", "execute_bash_evaluator_only_marker"),
        ("git log --oneline --all", "execute_bash_git_history_or_metadata"),
        ("git -C . log --oneline --all", "execute_bash_git_history_or_metadata"),
        ("git --no-pager log --oneline --all", "execute_bash_git_history_or_metadata"),
        ("python -c \"import subprocess; subprocess.run(['git', 'log'])\"", "execute_bash_git_history_or_metadata"),
        ("python -c \"import subprocess; subprocess.run(['git', '-C', '.', 'log'])\"", "execute_bash_git_history_or_metadata"),
        ("python -c \"import subprocess; subprocess.run(('git', 'log'))\"", "execute_bash_inline_process_escape"),
        ("python -c \"import subprocess; subprocess.run(['g'+'it', 'log'])\"", "execute_bash_inline_process_escape"),
        ("python -c \"exec('print(1)')\"", "execute_bash_inline_process_escape"),
        ("python -c \"eval('1 + 1')\"", "execute_bash_inline_process_escape"),
        ("bash -lc 'git log --oneline --all'", "execute_bash_git_history_or_metadata"),
        ("sh -c 'git show HEAD'", "execute_bash_git_history_or_metadata"),
        ("bash -c 'git cat-file -p HEAD'", "execute_bash_git_history_or_metadata"),
        ("env bash -lc 'git log --oneline'", "execute_bash_git_history_or_metadata"),
        ("command bash -lc 'git show HEAD'", "execute_bash_git_history_or_metadata"),
        ("exec bash -lc 'git log --oneline'", "execute_bash_git_history_or_metadata"),
        (
            "bash -lc 'python -c \"import subprocess; subprocess.run([\\\"git\\\", \\\"log\\\"])\"'",
            "execute_bash_inline_process_escape",
        ),
        ("eval 'git log --oneline'", "execute_bash_shell_wrapper_unauditable"),
        ("bash -lc \"eval 'git log --oneline'\"", "execute_bash_shell_wrapper_unauditable"),
        ("bash -lc \"env bash -lc 'git log --oneline'\"", "execute_bash_git_history_or_metadata"),
        ("bash -lc $'git log --oneline'", "execute_bash_dynamic_shell_expansion"),
        ("bash -c $'git show HEAD'", "execute_bash_dynamic_shell_expansion"),
        ("G=git; $G log --oneline", "execute_bash_dynamic_shell_expansion"),
        ("g=gi; t=t; $g$t log --oneline", "execute_bash_dynamic_shell_expansion"),
        ("`printf git` log --oneline", "execute_bash_dynamic_shell_expansion"),
        ("git${IFS}log --oneline", "execute_bash_dynamic_shell_expansion"),
        ("bash -lc 'G=git; $G log --oneline'", "execute_bash_dynamic_shell_expansion"),
        ("bash -lc '`printf git` log --oneline'", "execute_bash_dynamic_shell_expansion"),
        ("bash -lc 'git${IFS}log --oneline'", "execute_bash_dynamic_shell_expansion"),
        ("bash -lc \"cat '$HOME/.ssh/config'\"", "execute_bash_dynamic_shell_expansion"),
        ("bash -lc \"echo '$HOME'\"", "execute_bash_dynamic_shell_expansion"),
        ("bash -lc \"python -c 'print(\\\"$HOME\\\")'\"", "execute_bash_dynamic_shell_expansion"),
        ("bash -lc \"rg '$foo' src\"", "execute_bash_dynamic_shell_expansion"),
        ("python -m pip install requests", "execute_bash_shared_dependency_write_guard"),
        ("python -c \"from pathlib import Path; Path('/envs/repoA').write_text('x')\"", "execute_bash_shared_dependency_root_access"),
        ("cat /etc/passwd", "execute_bash_workspace_boundary"),
        ("cd .. && pytest -q", "execute_bash_workspace_boundary"),
    ],
)
def test_execute_bash_policy_rejects_hidden_history_and_dependency_writes(command: str, reason_code: str):
    decision = evaluate_model_execute_bash_command(
        command,
        shared_dependency_environment_roots=["/envs/repoA"],
    )

    assert decision.decision == "deny"
    assert decision.reason_code == reason_code


def test_execute_bash_policy_fails_closed_when_shared_environment_roots_missing():
    decision = evaluate_model_execute_bash_command(
        "python -c \"print('ok')\"",
        shared_dependency_environment_expected=True,
        shared_dependency_environment_roots=None,
    )

    assert decision.decision == "deny"
    assert decision.reason_code == "execute_bash_shared_dependency_roots_missing"
