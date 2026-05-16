from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from repo_harness_verl import (
    RepoHarnessVerlRequestMappingError,
    build_episode_request_from_verl_kwargs,
    validate_repo_harness_verl_kwargs,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _safe_kwargs() -> dict:
    return {
        "raw_prompt": [{"role": "user", "content": "fix the failing unit test"}],
        "agent_name": "repo_harness",
        "task_id": "task-1",
        "repo_harness_task_ref": {"task_ref": "rh://task/task-1", "task_path": "tasks/task-1.json"},
        "repo_harness_run_config_ref": "rh://config/default",
        "repo_harness_budget_ref": "rh://budget/default",
        "repo_harness_agent_policy_ref": "rh://policy/default",
        "repo_harness_episode_seed": 7,
        "repo_harness_run_mode": "training_fast",
        "repo_harness_dataset_name": "repo-harness-smoke",
        "repo_harness_dataset_split": "train",
        "repo_harness_dataset_revision": "rev1",
        "index": 3,
        "uid": "uid-abc",
        "session_id": 2,
        "global_steps": 11,
    }


def test_stage11_ordinary_import_does_not_need_reference_verl() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import repo_harness.rl; import repo_harness_verl; print('ordinary_import_ok')",
        ],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT / "src")},
        text=True,
        capture_output=True,
        check=True,
    )

    assert "ordinary_import_ok" in result.stdout


def test_stage11_kwargs_accepts_request_and_verl_control_fields() -> None:
    validated = validate_repo_harness_verl_kwargs(_safe_kwargs())

    assert validated["index"] == 3
    assert validated["uid"] == "uid-abc"
    assert validated["session_id"] == 2
    assert validated["global_steps"] == 11


@pytest.mark.parametrize(
    "key,value",
    [
        ("hidden_verifier", "secret"),
        ("prompts", [1, 2, 3]),
        ("extra_fields", {"repo_harness_status": "succeeded"}),
        ("reward_model", {"ground_truth": "answer"}),
    ],
)
def test_stage11_kwargs_rejects_hidden_and_reserved_fields(key: str, value: object) -> None:
    payload = _safe_kwargs()
    payload[key] = value

    with pytest.raises(RepoHarnessVerlRequestMappingError):
        validate_repo_harness_verl_kwargs(payload)


def test_stage11_builds_episode_request_with_safe_identifiers_and_backend() -> None:
    request = build_episode_request_from_verl_kwargs(
        _safe_kwargs(),
        sampling_params={"max_tokens": 5},
        rollout_config={"name": "sglang", "prompt_length": 32, "response_length": 8},
    )

    assert request.llm_gateway_route == "verl"
    assert request.inference_backend == "sglang"
    assert request.task_id == "task-1"
    assert request.episode_id == "task-1-uid-abc-s2-i3-g11"
    assert request.run_id == "rh-verl-task-1-uid-abc-s2-i3-g11"
    assert request.task_ref.task_path == "tasks/task-1.json"
    assert request.budgets.max_output_tokens == 5
    assert request.budgets.max_prompt_tokens == 32
    assert request.run_mode == "training_fast"


def test_stage11_output_budget_uses_strictest_rollout_bound() -> None:
    request = build_episode_request_from_verl_kwargs(
        _safe_kwargs(),
        sampling_params={"max_tokens": 1000},
        rollout_config={"name": "sglang", "response_length": 8},
    )

    assert request.budgets.max_output_tokens == 8


def test_stage11_output_budget_uses_max_new_tokens_when_stricter() -> None:
    request = build_episode_request_from_verl_kwargs(
        _safe_kwargs(),
        sampling_params={"max_new_tokens": 5},
        rollout_config={"name": "sglang", "response_length": 8},
    )

    assert request.budgets.max_output_tokens == 5


@pytest.mark.parametrize(
    "key,value",
    [
        ("index", True),
        ("session_id", 1.9),
        ("global_steps", 1.9),
    ],
)
def test_stage11_control_fields_reject_bool_and_non_integer_float(key: str, value: object) -> None:
    payload = _safe_kwargs()
    payload[key] = value

    with pytest.raises(RepoHarnessVerlRequestMappingError, match="integer scalar"):
        validate_repo_harness_verl_kwargs(payload)


@pytest.mark.parametrize(
    "key,value",
    [
        ("uid", ["abc"]),
        ("uid", {"safe": "abc"}),
        ("task_id", ["task"]),
    ],
)
def test_stage11_identifier_fields_reject_composite_values(key: str, value: object) -> None:
    payload = _safe_kwargs()
    payload[key] = value

    with pytest.raises(RepoHarnessVerlRequestMappingError, match="flat scalar identifier"):
        build_episode_request_from_verl_kwargs(
            payload,
            sampling_params={},
            rollout_config={"name": "sglang"},
        )


def test_stage11_budget_limits_reject_non_integer_float() -> None:
    with pytest.raises(RepoHarnessVerlRequestMappingError, match="integer scalars"):
        build_episode_request_from_verl_kwargs(
            _safe_kwargs(),
            sampling_params={"max_tokens": 8.9},
            rollout_config={"name": "sglang"},
        )


def test_stage11_model_visible_context_refs_are_not_enabled_yet() -> None:
    payload = _safe_kwargs()
    payload["repo_harness_model_visible_context_refs"] = ["rh://context/model-visible"]

    with pytest.raises(RepoHarnessVerlRequestMappingError, match="not_allowlisted"):
        validate_repo_harness_verl_kwargs(payload)


def test_stage11_build_request_rejects_missing_backend_and_absolute_task_path() -> None:
    with pytest.raises(RepoHarnessVerlRequestMappingError, match="inference_backend"):
        build_episode_request_from_verl_kwargs(_safe_kwargs(), sampling_params={}, rollout_config={})

    payload = _safe_kwargs()
    payload["repo_harness_task_ref"] = {"task_path": "/Users/roger/private/task.json"}
    with pytest.raises(RepoHarnessVerlRequestMappingError, match="absolute local path"):
        build_episode_request_from_verl_kwargs(
            payload,
            sampling_params={},
            rollout_config={"name": "vllm"},
        )
