from __future__ import annotations

import json

from repo_harness.rl import (
    AsyncEpisodeHandle,
    AsyncEpisodeHandleRef,
    AsyncEpisodeState,
    RepoHarnessEpisodeRequest,
)


def _request() -> RepoHarnessEpisodeRequest:
    return RepoHarnessEpisodeRequest.model_validate(
        {
            "episode_id": "snapshot-episode",
            "run_id": "snapshot-run",
            "task_id": "snapshot-task",
            "llm_gateway_route": "verl",
            "inference_backend": "sglang",
            "raw_prompt": [{"role": "user", "content": "Inspect the repository."}],
            "task_ref": {
                "task_ref": "rh://task/snapshot-task",
                "repo_ref": "repo://example/snapshot",
                "base_commit": "abcdef1234567890",
                "model_visible_summary": "Inspect the repository.",
            },
            "agent_policy_ref": "rh://policy/stage13/default",
            "budget_ref": "rh://budget/stage13/default",
            "run_config_ref": "rh://run-config/stage13/default",
            "budgets": {
                "max_turns": 2,
                "max_output_tokens": 64,
                "max_prompt_tokens": 512,
                "generation_timeout_seconds": 30,
                "max_tool_observation_tokens": 128,
                "max_verifier_seconds": 30,
            },
        }
    )


def test_stage13_1_pending_real_episode_snapshot_keeps_workspace_conservative() -> None:
    request = _request()
    handle_ref = AsyncEpisodeHandleRef(
        episode_id=request.episode_id,
        run_id=request.run_id,
        sample_attempt_id="snapshot-episode:attempt-0",
        handle_ref="rh://async/snapshot-episode/snapshot-episode:attempt-0",
    )
    state = AsyncEpisodeState(
        request=request,
        sample_attempt_id="snapshot-episode:attempt-0",
        handle_ref=handle_ref,
        runtime_mode="real_episode",
    )
    state.set_status("running")
    handle = AsyncEpisodeHandle(state)

    snapshot = handle.snapshot()

    assert snapshot.async_status == "running"
    assert snapshot.episode_status is None
    assert snapshot.resume.resume_supported is False
    assert snapshot.resume.resume_status == "unsupported_in_stage13_1"
    assert snapshot.final_audit_write_completed is False
    assert snapshot.run_directory_writer_active is True
    assert snapshot.verifier_worker_may_still_access_workspace is True
    assert snapshot.workspace_lease_safely_released is False

    serialized = json.dumps(snapshot.model_dump(mode="json"), sort_keys=True)
    assert "/Users/" not in serialized
    assert "/tmp/" not in serialized
    assert "hidden_verifier" not in serialized
    assert "ground_truth" not in serialized


def test_stage13_1_pending_minimal_gateway_snapshot_has_no_workspace_worker_claim() -> None:
    request = _request()
    handle_ref = AsyncEpisodeHandleRef(
        episode_id=request.episode_id,
        run_id=request.run_id,
        sample_attempt_id="snapshot-episode:attempt-1",
        handle_ref="rh://async/snapshot-episode/snapshot-episode:attempt-1",
    )
    state = AsyncEpisodeState(
        request=request,
        sample_attempt_id="snapshot-episode:attempt-1",
        handle_ref=handle_ref,
        runtime_mode="minimal_gateway",
    )
    state.set_status("running")
    handle = AsyncEpisodeHandle(state)

    snapshot = handle.snapshot()

    assert snapshot.run_directory_writer_active is True
    assert snapshot.verifier_worker_may_still_access_workspace is False
    assert snapshot.workspace_lease_safely_released is False
