"""Reward metadata schema。"""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import ACCEPTANCE_POLICY_VERSION, REWARD_VERSION


class RewardMetadata(StrictBaseModel):
    schema_version: str = "repo_harness_reward_metadata_v0"
    reward_version: str = REWARD_VERSION
    final_reward: float = Field(ge=0.0, le=1.0)
    formula: str
    components: dict[str, float] = Field(default_factory=dict)
    sources: dict[str, Any] = Field(default_factory=dict)
    invalid_for_training: bool = False
    invalid_reason: str | None = None
    acceptance_policy_version: str = ACCEPTANCE_POLICY_VERSION
    reward_clip_range: tuple[float, float] = (0.0, 1.0)

    @model_validator(mode="after")
    def invalid_samples_need_reason(self) -> "RewardMetadata":
        if self.invalid_for_training and not self.invalid_reason:
            raise ValueError("invalid_for_training=true 时必须提供 invalid_reason。")
        return self
