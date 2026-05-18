from __future__ import annotations

import pytest

from repo_harness.rl import AsyncEpisodeHandleRef, AsyncEpisodeSnapshot, ResumeCapability


def test_stage13_0_resume_capability_can_express_unsupported_resume() -> None:
    resume = ResumeCapability()

    assert resume.resume_supported is False
    assert resume.resume_status == "unsupported_in_stage13_1"


def test_stage13_0_async_handle_ref_uses_opaque_reference() -> None:
    handle = AsyncEpisodeHandleRef(
        episode_id="episode-1",
        run_id="run-1",
        sample_attempt_id="attempt-0",
        handle_ref="rh://async/handle/episode-1",
    )

    assert handle.handle_ref.startswith("rh://")


def test_stage13_0_snapshot_rejects_unsafe_workspace_release() -> None:
    with pytest.raises(ValueError, match="workspace lease cannot be safely released"):
        AsyncEpisodeSnapshot(
            episode_id="episode-1",
            run_id="run-1",
            task_id="task-1",
            sample_attempt_id="attempt-0",
            async_status="timeout",
            verifier_worker_may_still_access_workspace=True,
            workspace_lease_safely_released=True,
        )


def test_stage13_0_orphaned_snapshot_requires_diagnostics() -> None:
    with pytest.raises(ValueError, match="orphan diagnostics"):
        AsyncEpisodeSnapshot(
            episode_id="episode-1",
            run_id="run-1",
            task_id="task-1",
            sample_attempt_id="attempt-0",
            async_status="orphaned",
        )
