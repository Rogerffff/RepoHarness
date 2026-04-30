import pytest
from pydantic import ValidationError

from repo_harness.tasks import RunnableTask, TaskDefinition


def valid_task_payload():
    return {
        "id": "task_001",
        "task_version": "task_001_v0",
        "dataset_name": "repo_harness_micro",
        "source_kind": "micro_repo_fixture",
        "dataset_split": "dev",
        "created_at": "2026-04-30",
        "repo": "tests/fixtures/repos/buggy_calculator",
        "issue": "Fix divide by zero handling.",
        "setup_command": "python -m pip install -e .",
        "test_command": "pytest -q",
        "timeouts": {
            "setup_timeout_sec": 300,
            "test_timeout_sec": 120,
            "agent_timeout_sec": 900,
            "final_verifier_timeout_sec": 180,
        },
        "environment": {
            "execution_image": "python:3.12-slim",
            "python_version": "3.12",
            "package_manager": "pip",
        },
        "expected_files": ["calculator.py"],
        "fail_to_pass_tests": ["tests/test_calculator.py::test_divide_zero"],
        "pass_to_pass_tests": ["tests/test_calculator.py::test_add"],
        "visibility": {
            "issue": "model_visible",
            "expected_files": "model_visible",
            "fail_to_pass_tests": "verifier_only",
            "pass_to_pass_tests": "verifier_only",
            "gold_patch": "hidden_reference",
        },
        "decontamination": {
            "status": "manual_checked",
            "known_public_solution": False,
        },
    }


def test_valid_task_can_create_runnable_task_and_verifier_config():
    task = TaskDefinition.model_validate(valid_task_payload())
    runnable = RunnableTask.from_definition(task)

    assert runnable.task_id == "task_001"
    assert runnable.issue_statement == "Fix divide by zero handling."
    assert runnable.verifier_config.test_command == "pytest -q"
    assert not hasattr(runnable, "gold_patch")


def test_timeout_shortcut_expands_to_all_timeout_fields():
    payload = valid_task_payload()
    payload["timeouts"] = {"timeout_sec": 42, "test_timeout_sec": 12}

    task = TaskDefinition.model_validate(payload)

    assert task.timeouts.setup_timeout_sec == 42
    assert task.timeouts.test_timeout_sec == 12
    assert task.timeouts.agent_timeout_sec == 42
    assert task.timeouts.final_verifier_timeout_sec == 42


def test_gold_patch_must_be_hidden_reference():
    payload = valid_task_payload()
    payload["gold_patch"] = "diff --git a/calculator.py b/calculator.py"
    payload["visibility"]["gold_patch"] = "model_visible"

    with pytest.raises(ValidationError, match="gold_patch"):
        TaskDefinition.model_validate(payload)


def test_fail_to_pass_tests_are_not_model_visible():
    payload = valid_task_payload()
    payload["visibility"]["fail_to_pass_tests"] = "model_visible"

    with pytest.raises(ValidationError, match="fail_to_pass_tests"):
        TaskDefinition.model_validate(payload)


def test_pass_to_pass_tests_are_not_model_visible():
    payload = valid_task_payload()
    payload["visibility"]["pass_to_pass_tests"] = "model_visible"

    with pytest.raises(ValidationError, match="pass_to_pass_tests"):
        TaskDefinition.model_validate(payload)


def test_runnable_task_agent_visible_view_excludes_evaluator_only_metadata():
    payload = valid_task_payload()
    payload["gold_patch"] = "diff --git a/calculator.py b/calculator.py"
    payload["decontamination"]["overlap_check_notes"] = "private evaluator note"
    task = TaskDefinition.model_validate(payload)
    runnable = RunnableTask.from_definition(task)

    visible = runnable.agent_visible_view()
    visible_text = str(visible)

    assert visible["expected_files"] == ["calculator.py"]
    assert "gold_patch" not in visible_text
    assert "fail_to_pass_tests" not in visible_text
    assert "pass_to_pass_tests" not in visible_text
    assert "private evaluator note" not in visible_text
    assert "decontamination" not in visible_text


def test_missing_required_field_fails():
    payload = valid_task_payload()
    del payload["test_command"]

    with pytest.raises(ValidationError):
        TaskDefinition.model_validate(payload)
