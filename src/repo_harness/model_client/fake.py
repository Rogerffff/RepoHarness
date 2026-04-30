"""Fake model client for deterministic tests."""

from __future__ import annotations

from repo_harness.model_client.replay import ReplayModelClient
from repo_harness.model_client.schemas import ReplayScript


class FakeModelClient(ReplayModelClient):
    """Replay-compatible fake client used by agent loop tests."""

    @classmethod
    def from_steps(cls, *, script_id: str, task_id: str, steps: list[dict[str, object]]) -> "FakeModelClient":
        return cls(
            ReplayScript.model_validate(
                {
                    "script_id": script_id,
                    "task_id": task_id,
                    "steps": steps,
                }
            )
        )
