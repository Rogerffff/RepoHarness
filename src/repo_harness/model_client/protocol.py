"""Common model client protocol."""

from __future__ import annotations

from typing import Protocol

from repo_harness.model_client.schemas import ModelRequestContext, ModelResponse
from repo_harness.trajectory import RunRecorder


class ModelClient(Protocol):
    """Minimal provider-independent model client contract."""

    def generate(self, request: ModelRequestContext, recorder: RunRecorder) -> ModelResponse:
        """Generate one assistant response for a prepared RepoHarness request."""
