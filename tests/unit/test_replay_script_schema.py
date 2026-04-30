import pytest
from pydantic import ValidationError

from repo_harness.model_client import ReplayScript, ReplayStep


def test_replay_script_visible_steps_exclude_expected_outcome_and_comments():
    script = ReplayScript(
        script_id="replay_success",
        task_id="task_001",
        expected_outcome={"accepted": True},
        metadata={"gold_hint": "do not show"},
        steps=[
            ReplayStep(
                step_id="step_001",
                action="tool_call",
                tool_call_id="call_001",
                tool_name="read_file",
                arguments={"path": "calculator.py"},
                expected_outcome={"must_find": "divide"},
                comment="test-only note",
            ),
            ReplayStep(
                step_id="step_002",
                action="final_answer",
                assistant_text="Done.",
                expected_outcome={"accepted": True},
            ),
        ],
    )

    visible = script.model_visible_steps()

    assert visible[0] == {
        "step_id": "step_001",
        "action": "tool_call",
        "tool_call_id": "call_001",
        "tool_name": "read_file",
        "arguments": {"path": "calculator.py"},
    }
    assert "expected_outcome" not in str(visible)
    assert "gold_hint" not in str(visible)
    assert "test-only note" not in str(visible)


def test_replay_tool_call_requires_tool_call_id():
    with pytest.raises(ValidationError, match="tool_call_id"):
        ReplayStep(
            step_id="step_001",
            action="tool_call",
            tool_name="read_file",
            arguments={"path": "calculator.py"},
        )


def test_replay_tool_call_arguments_must_be_mapping():
    with pytest.raises(ValidationError):
        ReplayStep(
            step_id="step_001",
            action="tool_call",
            tool_call_id="call_001",
            tool_name="read_file",
            arguments="path=calculator.py",
        )


def test_replay_script_needs_at_least_one_step():
    with pytest.raises(ValidationError):
        ReplayScript(script_id="empty", task_id="task_001", steps=[])
