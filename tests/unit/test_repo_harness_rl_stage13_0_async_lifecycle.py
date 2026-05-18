from __future__ import annotations

import pytest

from repo_harness.rl import AsyncEpisodeLifecycleFacts, AsyncEpisodeSnapshot


def test_stage13_0_lifecycle_rejects_mixed_attempts() -> None:
    snapshots = [
        AsyncEpisodeSnapshot(
            episode_id="episode-1",
            run_id="run-1",
            task_id="task-1",
            sample_attempt_id="attempt-0",
            async_status="running",
            run_directory_writer_active=True,
        ),
        AsyncEpisodeSnapshot(
            episode_id="episode-1",
            run_id="run-1",
            task_id="task-1",
            sample_attempt_id="attempt-1",
            async_status="running",
            run_directory_writer_active=True,
        ),
    ]

    with pytest.raises(ValueError, match="one sample_attempt_id"):
        AsyncEpisodeLifecycleFacts(snapshots=snapshots)


def test_stage13_0_lifecycle_can_record_cleanup_deadline_and_hidden_runtime_cleanup() -> None:
    facts = AsyncEpisodeLifecycleFacts(
        snapshots=[
            AsyncEpisodeSnapshot(
                episode_id="episode-1",
                run_id="run-1",
                task_id="task-1",
                sample_attempt_id="attempt-0",
                async_status="cleanup_running",
                cleanup_status="waiting_for_worker",
                run_directory_writer_active=True,
            )
        ],
        cleanup_deadline_seconds=5.0,
        recorder_lock_timeout_seconds=2.0,
        hidden_runtime_directory_cleanup_status="pending",
    )

    assert facts.cleanup_deadline_seconds == 5.0


def test_stage13_0_snapshot_rejects_released_writer_before_final_audit() -> None:
    with pytest.raises(ValueError, match="writer must remain active"):
        AsyncEpisodeSnapshot(
            episode_id="episode-1",
            run_id="run-1",
            task_id="task-1",
            sample_attempt_id="attempt-0",
            async_status="cleanup_running",
            final_audit_write_completed=False,
            run_directory_writer_active=False,
        )


def test_stage13_0_snapshot_allows_writer_release_after_final_audit() -> None:
    snapshot = AsyncEpisodeSnapshot(
        episode_id="episode-1",
        run_id="run-1",
        task_id="task-1",
        sample_attempt_id="attempt-0",
        async_status="completed",
        final_audit_write_completed=True,
        run_directory_writer_active=False,
    )

    assert snapshot.final_audit_write_completed is True
