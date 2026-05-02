"""V3 acceptance skeleton schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V3_CONTAMINATION_DENYLIST_VERSION,
    V3_ACCEPTANCE_REPORT_SCHEMA_VERSION,
    V3_VISIBILITY_POLICY_VERSION,
)
from repo_harness.trajectory import ArtifactRef
from repo_harness.v3_visibility import V3_VISIBILITY_SURFACES


class CommandLogEntry(StrictBaseModel):
    schema_version: str = COMMAND_LOG_ENTRY_SCHEMA_VERSION
    command_name: str
    argv: list[str] = Field(min_length=1)
    cwd: str
    input_refs: list[ArtifactRef] = Field(default_factory=list)
    output_refs: list[ArtifactRef] = Field(default_factory=list)
    exit_code: int | None = None
    tool_or_cli_version: str
    started_at: str
    finished_at: str | None = None
    structured_skip_reason: str | None = None
    structured_failure_reason: str | None = None

    @model_validator(mode="after")
    def terminal_entries_need_result(self) -> "CommandLogEntry":
        if self.finished_at and self.exit_code is None and not self.structured_skip_reason:
            raise ValueError("finished command log entry 必须记录 exit_code 或 structured skip reason。")
        return self


class V3AcceptanceReport(StrictBaseModel):
    schema_version: str = V3_ACCEPTANCE_REPORT_SCHEMA_VERSION
    acceptance_id: str
    status: Literal["passed", "failed", "blocked"]
    visibility_policy_version: Literal[V3_VISIBILITY_POLICY_VERSION] = V3_VISIBILITY_POLICY_VERSION
    contamination_denylist_version: Literal[V3_CONTAMINATION_DENYLIST_VERSION] = (
        V3_CONTAMINATION_DENYLIST_VERSION
    )
    input_manifest_ref: ArtifactRef
    command_log_ref: ArtifactRef
    run_selection_manifest_ref: ArtifactRef | None = None
    report_generated_at: str
    checks: list[str] = Field(default_factory=list)
    contamination_scan_refs: list[ArtifactRef] = Field(default_factory=list)
    contamination_scan_surfaces: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def failures_match_status(self) -> "V3AcceptanceReport":
        if self.status == "passed" and self.failures:
            raise ValueError("passed acceptance report 不能包含 failures。")
        if self.status == "passed" and not self.checks:
            raise ValueError("passed acceptance report 必须包含 checks。")
        if self.status == "passed" and not self.contamination_scan_refs:
            raise ValueError("passed acceptance report 必须引用 contamination scan evidence。")
        if self.status == "passed":
            missing_surfaces = sorted(
                set(V3_VISIBILITY_SURFACES).difference(self.contamination_scan_surfaces)
            )
            if missing_surfaces:
                raise ValueError(
                    "passed acceptance report 缺少 contamination scan surfaces："
                    + ", ".join(missing_surfaces)
                )
        if self.status != "passed" and not self.failures:
            raise ValueError("failed / blocked acceptance report 必须包含 failures。")
        return self
