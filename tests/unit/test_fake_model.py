from pathlib import Path

from repo_harness.context import ContextManager
from repo_harness.model_client import FakeModelClient
from repo_harness.trajectory import RunRecorder


def test_fake_model_can_drive_tool_call_sequence(tmp_path: Path):
    client = FakeModelClient.from_steps(
        script_id="fake",
        task_id="task",
        steps=[
            {
                "step_id": "read",
                "action": "tool_call",
                "tool_call_id": "call_read",
                "tool_name": "read_file",
                "arguments": {"path": "demo.py"},
            },
            {"step_id": "final", "action": "final_answer", "assistant_text": "done"},
        ],
    )
    with RunRecorder("fake-test", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=[{"role": "system", "content": "system"}],
            recorder=recorder,
            task_id="task",
            turn=1,
        )
        first = client.generate(prepared_messages=prepared, recorder=recorder, turn=1)
        observed = ContextManager().prepare_messages(
            messages=[
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "tool_call_id": "call_read",
                            "tool_name": "read_file",
                            "arguments": {"path": "demo.py"},
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_read",
                    "content": "file content",
                },
            ],
            recorder=recorder,
            task_id="task",
            turn=2,
        )
        second = client.generate(prepared_messages=observed, recorder=recorder, turn=2)

    assert first.tool_calls[0].tool_name == "read_file"
    assert second.finish_reason == "stop"
    assert not second.tool_calls


def test_fake_model_simulates_model_error(tmp_path: Path):
    client = FakeModelClient.from_steps(
        script_id="fake-error",
        task_id="task",
        steps=[
            {
                "step_id": "error",
                "action": "model_error",
                "assistant_text": "provider failed",
                "model_error_type": "provider_error",
            }
        ],
    )
    with RunRecorder("fake-error", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=[{"role": "system", "content": "system"}],
            recorder=recorder,
            task_id="task",
            turn=1,
        )
        response = client.generate(prepared_messages=prepared, recorder=recorder, turn=1)

    assert response.model_error_type == "provider_error"
    assert response.model_call_event is not None
    assert response.model_call_event.model_error_type == "provider_error"
