"""Runtime-only turn-boundary pause / resume helpers for Stage 14.3.

This module intentionally does not implement cross-process durable resume.
It coordinates a same-process worker thread that pauses at a safe turn
boundary, records a partial checkpoint, and waits for an explicit resume or
cancel signal.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Literal, Mapping

from repo_harness.schema_base import StrictBaseModel

from .partial_checkpoint import PartialEpisodeCheckpoint, validate_partial_checkpoint_roundtrip

PauseOutcomeStatus = Literal[
    "paused",
    "pause_timeout",
    "pause_not_supported",
    "pause_request_cancelled",
]
ResumeOutcomeStatus = Literal[
    "resumed",
    "not_paused",
    "unsupported_cross_process_resume_in_stage14_3",
    "checkpoint_mismatch",
]


class EpisodePauseCancelled(RuntimeError):
    """Raised inside the worker thread when a paused episode is cancelled."""


class PauseOutcome(StrictBaseModel):
    schema_version: str = "repo_harness_stage14_3_pause_outcome_v0"
    status: PauseOutcomeStatus
    checkpoint_ref: str | None = None
    checkpoint: PartialEpisodeCheckpoint | None = None
    message: str | None = None


class ResumeOutcome(StrictBaseModel):
    schema_version: str = "repo_harness_stage14_3_resume_outcome_v0"
    status: ResumeOutcomeStatus
    checkpoint_ref: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class ResumeStateStoreEntry:
    checkpoint_id: str
    content_digest: str
    run_id: str
    lease_token: str
    recorder_cursor_digest: str
    generation_record_digest: str
    checkpoint: PartialEpisodeCheckpoint


class ResumeStateStore:
    """Runtime-private checkpoint identity store.

    A syntactically valid checkpoint is not enough for Stage 14.3 resume.  The
    active runtime must also hold a matching entry proving that the paused
    worker thread, writer lease, recorder cursor, and generation records belong
    to this process.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entries: dict[str, ResumeStateStoreEntry] = {}

    def put(self, checkpoint: PartialEpisodeCheckpoint) -> ResumeStateStoreEntry:
        parsed = validate_partial_checkpoint_roundtrip(checkpoint)
        entry = ResumeStateStoreEntry(
            checkpoint_id=parsed.checkpoint_id,
            content_digest=parsed.content_digest,
            run_id=parsed.run_id,
            lease_token=parsed.durable_writer_lease.lease_token,
            recorder_cursor_digest=parsed.recorder_cursor.recorder_cursor_digest,
            generation_record_digest=parsed.token_provenance.generation_record_digest,
            checkpoint=parsed,
        )
        with self._lock:
            self._entries[parsed.checkpoint_id] = entry
        return entry

    def validate_resume_checkpoint(
        self,
        checkpoint: PartialEpisodeCheckpoint | Mapping[str, object],
    ) -> PartialEpisodeCheckpoint:
        parsed = validate_partial_checkpoint_roundtrip(checkpoint)
        with self._lock:
            entry = self._entries.get(parsed.checkpoint_id)
        if entry is None:
            raise ValueError("unsupported_cross_process_resume_in_stage14_3")
        mismatches: list[str] = []
        if entry.content_digest != parsed.content_digest:
            mismatches.append("content_digest")
        if entry.run_id != parsed.run_id:
            mismatches.append("run_id")
        if entry.lease_token != parsed.durable_writer_lease.lease_token:
            mismatches.append("lease_token")
        if entry.recorder_cursor_digest != parsed.recorder_cursor.recorder_cursor_digest:
            mismatches.append("recorder_cursor_digest")
        if entry.generation_record_digest != parsed.token_provenance.generation_record_digest:
            mismatches.append("generation_record_digest")
        if mismatches:
            raise ValueError("checkpoint_mismatch:" + ",".join(mismatches))
        return parsed

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


class TurnBoundaryPauseController:
    """Thread-safe same-process pause gate for a single async episode."""

    def __init__(
        self,
        *,
        status_callback: Callable[[str, str | None], None] | None = None,
    ) -> None:
        self.resume_state_store = ResumeStateStore()
        self._condition = threading.Condition(threading.RLock())
        self._pause_requested = False
        self._paused = False
        self._resume_requested = False
        self._cancel_requested = False
        self._reason: str | None = None
        self._checkpoint: PartialEpisodeCheckpoint | None = None
        self._status_callback = status_callback

    @property
    def is_paused(self) -> bool:
        with self._condition:
            return self._paused

    @property
    def current_checkpoint(self) -> PartialEpisodeCheckpoint | None:
        with self._condition:
            return self._checkpoint

    def set_status_callback(self, callback: Callable[[str, str | None], None] | None) -> None:
        with self._condition:
            self._status_callback = callback

    def request_pause_at_next_turn_boundary(
        self,
        *,
        reason: str = "pause_requested",
        timeout: float | None = None,
    ) -> PauseOutcome:
        with self._condition:
            if self._checkpoint is not None and self._paused:
                return PauseOutcome(
                    status="paused",
                    checkpoint_ref=_checkpoint_ref(self._checkpoint),
                    checkpoint=self._checkpoint,
                )
            self._pause_requested = True
            self._reason = reason
            self._condition.notify_all()
            if timeout is None:
                while self._checkpoint is None and self._pause_requested and not self._cancel_requested:
                    self._condition.wait()
            elif self._checkpoint is None and self._pause_requested and not self._cancel_requested:
                self._condition.wait(timeout=timeout)

            if self._checkpoint is not None and self._paused:
                return PauseOutcome(
                    status="paused",
                    checkpoint_ref=_checkpoint_ref(self._checkpoint),
                    checkpoint=self._checkpoint,
                )
            if self._cancel_requested or not self._pause_requested:
                return PauseOutcome(status="pause_request_cancelled", message="pause request was cancelled")
            return PauseOutcome(
                status="pause_timeout",
                message="pause request is still pending and will remain active",
            )

    def cancel_pause_request(self, *, reason: str = "pause_request_cancelled") -> PauseOutcome:
        with self._condition:
            if self._paused and self._checkpoint is not None:
                return PauseOutcome(
                    status="paused",
                    checkpoint_ref=_checkpoint_ref(self._checkpoint),
                    checkpoint=self._checkpoint,
                    message="episode is already paused; use cancel() or resume()",
                )
            self._pause_requested = False
            self._reason = reason
            self._condition.notify_all()
        return PauseOutcome(status="pause_request_cancelled", message=reason)

    def cancel_paused_episode(self, *, reason: str = "cancel_requested") -> None:
        with self._condition:
            self._cancel_requested = True
            self._reason = reason
            self._condition.notify_all()

    def resume(
        self,
        checkpoint: PartialEpisodeCheckpoint | Mapping[str, object],
    ) -> ResumeOutcome:
        try:
            parsed = self.resume_state_store.validate_resume_checkpoint(checkpoint)
        except ValueError as exc:
            message = str(exc)
            status: ResumeOutcomeStatus = (
                "unsupported_cross_process_resume_in_stage14_3"
                if "unsupported_cross_process_resume_in_stage14_3" in message
                else "checkpoint_mismatch"
            )
            return ResumeOutcome(status=status, message=message)
        with self._condition:
            if not self._paused or self._checkpoint is None:
                return ResumeOutcome(status="not_paused", checkpoint_ref=_checkpoint_ref(parsed))
            if parsed.checkpoint_id != self._checkpoint.checkpoint_id:
                return ResumeOutcome(
                    status="checkpoint_mismatch",
                    checkpoint_ref=_checkpoint_ref(parsed),
                    message="checkpoint_id does not match current paused checkpoint",
                )
            self._resume_requested = True
            self._condition.notify_all()
        return ResumeOutcome(status="resumed", checkpoint_ref=_checkpoint_ref(parsed))

    def maybe_pause_at_turn_boundary(
        self,
        *,
        checkpoint_builder: Callable[[], PartialEpisodeCheckpoint],
    ) -> PartialEpisodeCheckpoint | None:
        with self._condition:
            if not self._pause_requested:
                return None
        checkpoint = checkpoint_builder()
        self.resume_state_store.put(checkpoint)
        with self._condition:
            if not self._pause_requested:
                return None
            self._checkpoint = checkpoint
            self._paused = True
            self._resume_requested = False
            if self._status_callback is not None:
                self._status_callback("paused", self._reason)
            self._condition.notify_all()
            while not self._resume_requested and not self._cancel_requested:
                self._condition.wait()
            if self._cancel_requested:
                if self._status_callback is not None:
                    self._status_callback("cancelling", self._reason)
                self._paused = False
                raise EpisodePauseCancelled(self._reason or "pause_cancelled")
            self._paused = False
            self._pause_requested = False
            self._resume_requested = False
            if self._status_callback is not None:
                self._status_callback("running", "resumed_from_stage14_3_pause")
            return checkpoint


def _checkpoint_ref(checkpoint: PartialEpisodeCheckpoint) -> str:
    return f"rh://partial-checkpoints/{checkpoint.checkpoint_id}"
