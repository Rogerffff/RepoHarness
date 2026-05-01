from pathlib import Path

import pytest

from repo_harness.errors import TaskValidationError
from repo_harness.tasks.command_policy import (
    CommandPolicy,
    TestCommandPolicy,
    evaluate_model_bash_command,
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
