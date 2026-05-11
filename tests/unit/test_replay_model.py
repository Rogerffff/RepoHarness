import json
from pathlib import Path

import pytest

from repo_harness.context import ContextManager
from repo_harness.model_client import ReplayModelClient
from repo_harness.trajectory import RunRecorder


def test_replay_model_writes_separate_provider_request_artifact(tmp_path: Path):
    replay_path = tmp_path / "replay.yaml"
    replay_path.write_text(
        """
script_id: replay
task_id: task
steps:
  - step_id: final
    action: final_answer
    assistant_text: "done"
expected_outcome:
  accepted: true
""".lstrip(),
        encoding="utf-8",
    )
    client = ReplayModelClient.from_path(replay_path)
    with RunRecorder("replay-test", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=[{"role": "system", "content": "system"}],
            recorder=recorder,
            task_id="task",
            turn=1,
        )
        response = client.generate(prepared_messages=prepared, recorder=recorder, turn=1)

    assert response.raw_provider_request_ref is not None
    assert response.raw_provider_request_ref != prepared.prepared_messages_ref
    assert response.model_call_event is not None
    assert response.model_call_event.request_timeout_seconds == 60
    assert response.model_call_event.request_timeout_policy_facts == {}
    raw_response = (tmp_path / "run" / response.raw_provider_response_ref.relative_path).read_text(encoding="utf-8")
    assert "expected_outcome" not in raw_response


def test_replay_model_loads_jsonl_steps(tmp_path: Path):
    replay_path = tmp_path / "steps.jsonl"
    replay_path.write_text(
        json.dumps(
            {
                "step_id": "call",
                "action": "tool_call",
                "tool_call_id": "call_read",
                "tool_name": "read_file",
                "arguments": {"path": "demo.py"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    client = ReplayModelClient.from_path(replay_path)
    with RunRecorder("jsonl-replay", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=[{"role": "system", "content": "system"}],
            recorder=recorder,
            task_id="task",
            turn=1,
        )
        response = client.generate(prepared_messages=prepared, recorder=recorder, turn=1)

    assert response.tool_calls[0].tool_call_id == "call_read"


def test_replay_model_rejects_duplicate_tool_call_ids(tmp_path: Path):
    replay_path = tmp_path / "dupe.yaml"
    replay_path.write_text(
        """
script_id: dupe
task_id: task
steps:
  - step_id: one
    action: tool_call
    tool_call_id: repeated
    tool_name: read_file
    arguments:
      path: a.py
  - step_id: two
    action: tool_call
    tool_call_id: repeated
    tool_name: read_file
    arguments:
      path: b.py
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate tool_call_id"):
        ReplayModelClient.from_path(replay_path)


def test_replay_model_script_exhaustion_is_structured_model_error(tmp_path: Path):
    replay_path = tmp_path / "one.yaml"
    replay_path.write_text(
        """
script_id: one
task_id: task
steps:
  - step_id: final
    action: final_answer
    assistant_text: "done"
""".lstrip(),
        encoding="utf-8",
    )
    client = ReplayModelClient.from_path(replay_path)
    with RunRecorder("exhausted", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=[{"role": "system", "content": "system"}],
            recorder=recorder,
            task_id="task",
            turn=1,
        )
        client.generate(prepared_messages=prepared, recorder=recorder, turn=1)
        exhausted = client.generate(prepared_messages=prepared, recorder=recorder, turn=2)

    assert exhausted.model_error_type == "replay_script_exhausted"
    assert exhausted.model_call_event is not None
    assert exhausted.model_call_event.model_error_type == "replay_script_exhausted"


def test_replay_model_detects_tool_order_mismatch(tmp_path: Path):
    replay_path = tmp_path / "order.yaml"
    replay_path.write_text(
        """
script_id: order
task_id: task
steps:
  - step_id: first
    action: tool_call
    tool_call_id: expected_call
    tool_name: read_file
    arguments:
      path: a.py
  - step_id: second
    action: final_answer
    assistant_text: "done"
""".lstrip(),
        encoding="utf-8",
    )
    client = ReplayModelClient.from_path(replay_path)
    with RunRecorder("order", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=[{"role": "system", "content": "system"}],
            recorder=recorder,
            task_id="task",
            turn=1,
        )
        client.generate(prepared_messages=prepared, recorder=recorder, turn=1)
        mismatched = ContextManager().prepare_messages(
            messages=[
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "tool_call_id": "different_call",
                            "tool_name": "read_file",
                            "arguments": {"path": "a.py"},
                        }
                    ],
                },
                {"role": "tool", "tool_call_id": "different_call", "content": "ok"},
            ],
            recorder=recorder,
            task_id="task",
            turn=2,
        )
        response = client.generate(prepared_messages=mismatched, recorder=recorder, turn=2)

    assert response.model_error_type == "replay_tool_order_mismatch"


def test_replay_model_detects_arguments_and_expected_outcome_mismatch(tmp_path: Path):
    replay_path = tmp_path / "expected.yaml"
    replay_path.write_text(
        """
script_id: expected
task_id: task
steps:
  - step_id: first
    action: tool_call
    tool_call_id: call_read
    tool_name: read_file
    arguments:
      path: a.py
    expected_outcome:
      status: ok
  - step_id: second
    action: final_answer
    assistant_text: "done"
""".lstrip(),
        encoding="utf-8",
    )
    client = ReplayModelClient.from_path(replay_path)
    with RunRecorder("expected", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=[{"role": "system", "content": "system"}],
            recorder=recorder,
            task_id="task",
            turn=1,
        )
        client.generate(prepared_messages=prepared, recorder=recorder, turn=1)
        bad_args = ContextManager().prepare_messages(
            messages=[
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "tool_call_id": "call_read",
                            "tool_name": "read_file",
                            "arguments": {"path": "b.py"},
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_read",
                    "content": "ok",
                    "status": "ok",
                },
            ],
            recorder=recorder,
            task_id="task",
            turn=2,
        )
        response = client.generate(prepared_messages=bad_args, recorder=recorder, turn=2)

    assert response.model_error_type == "replay_tool_arguments_mismatch"
    assert response.model_call_event is not None
    assert response.model_call_event.request_timeout_seconds == 60
    assert response.model_call_event.request_timeout_policy_facts == {}


def test_replay_model_detects_expected_outcome_status_mismatch(tmp_path: Path):
    replay_path = tmp_path / "expected-status.yaml"
    replay_path.write_text(
        """
script_id: expected_status
task_id: task
steps:
  - step_id: first
    action: tool_call
    tool_call_id: call_read
    tool_name: read_file
    arguments:
      path: a.py
    expected_outcome:
      status: ok
  - step_id: second
    action: final_answer
    assistant_text: "done"
""".lstrip(),
        encoding="utf-8",
    )
    client = ReplayModelClient.from_path(replay_path)
    with RunRecorder("expected-status", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=[{"role": "system", "content": "system"}],
            recorder=recorder,
            task_id="task",
            turn=1,
        )
        client.generate(prepared_messages=prepared, recorder=recorder, turn=1)
        bad_status = ContextManager().prepare_messages(
            messages=[
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "tool_call_id": "call_read",
                            "tool_name": "read_file",
                            "arguments": {"path": "a.py"},
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_read",
                    "content": "denied",
                    "status": "denied",
                },
            ],
            recorder=recorder,
            task_id="task",
            turn=2,
        )
        response = client.generate(prepared_messages=bad_status, recorder=recorder, turn=2)

    assert response.model_error_type == "replay_tool_result_status_mismatch"
