"""训练导出策略和导出记录 schema。"""

from __future__ import annotations

from pathlib import PurePath
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import EXPORT_POLICY_VERSION, EXPORT_SCHEMA_VERSION


class ExportPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_export_policy_schema_v0"
    export_policy_version: str = EXPORT_POLICY_VERSION
    loss_mask_policy: str = "assistant_actions_only_v0"
    observation_mask_policy: str = "tool_results_are_observations_v0"
    filter_rules: list[str] = Field(default_factory=list)
    redaction_policy: str = "repo_harness_export_redaction_v0"


class ExportRecord(StrictBaseModel):
    schema_version: str = EXPORT_SCHEMA_VERSION
    sample_id: str
    task_id: str
    source_run_id: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    filter_status: Literal["included", "skipped", "filtered"] = "included"
    invalid_for_training: bool = False
    invalid_reason: str | None = None

    @model_validator(mode="after")
    def reject_evaluator_only_payload(self) -> "ExportRecord":
        blocked_keys = {
            "gold_patch",
            "hidden_tests",
            "hidden_test",
            "fail_to_pass_tests",
            "pass_to_pass_tests",
            "baseline_raw_log",
            "baseline_stdout",
            "baseline_stderr",
            "expected_outcome",
            "reward_only",
            "reward_only_metadata",
            "decontamination_metadata",
        }
        for location, value in (("payload", self.payload), ("metadata", self.metadata)):
            found = _find_blocked_export_value(value, blocked_keys)
            if found is not None:
                raise ValueError(f"{location} 包含不可导出的隐藏或本机字段：{found}")
        return self


def _find_blocked_export_value(value: Any, blocked_keys: set[str]) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered_key = str(key).lower()
            if lowered_key in blocked_keys:
                return str(key)
            found = _find_blocked_export_value(nested, blocked_keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_blocked_export_value(nested, blocked_keys)
            if found is not None:
                return found
    elif isinstance(value, str):
        if value.startswith("/Users/") or value.startswith("/private/"):
            return "local_absolute_path"
        path = PurePath(value)
        if path.is_absolute():
            return "absolute_path"
    return None
