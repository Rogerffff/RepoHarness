"""训练导出策略和导出记录 schema。"""

from __future__ import annotations

from pathlib import PurePath
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    EXPORT_AUDIT_SCHEMA_VERSION,
    EXPORT_MANIFEST_SCHEMA_VERSION,
    EXPORT_POLICY_VERSION,
    EXPORT_SCHEMA_VERSION,
    PAIRING_POLICY_VERSION,
)

ExportFormat = Literal[
    "sft_jsonl",
    "rl_jsonl",
    "preference_jsonl",
    "provider_reasoning_trace_training_export",
]
AuditStatus = Literal["passed", "failed", "warning", "skipped"]
TrainingEligibility = Literal["trainable", "diagnostic_only", "skipped", "invalid"]

STRICT_COMPARE_FIELDS = (
    "task_id",
    "task_version",
    "base_commit",
    "source_archive_sha256",
    "environment_spec_hash",
    "dependency_state_policy",
    "execution_mode",
    "verifier_name",
    "verifier_version",
    "reward_formula_version",
    "final_verifier_mode",
    "tool_schema_snapshot_hash",
    "tool_order",
    "tool_parser_version",
    "tool_result_format_version",
    "context_policy_version",
    "prompt_template_version",
    "export_policy_version",
    "scaffold_id",
    "scaffold_version",
    "allowed_tools_policy",
    "phase_policy",
    "model_provider",
    "model_id",
    "temperature",
    "max_output_tokens",
    "turn_budget",
    "tool_budget",
    "test_budget",
    "task_timeout",
)


class ExportPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_export_policy_schema_v0"
    export_policy_version: str = EXPORT_POLICY_VERSION
    loss_mask_policy: str = "assistant_actions_only_v0"
    observation_mask_policy: str = "tool_results_are_observations_v0"
    allow_oracle_feedback_training: bool = False
    allow_provider_reasoning_trace_training: bool = False
    filter_rules: list[str] = Field(default_factory=list)
    redaction_policy: str = "repo_harness_export_redaction_v0"


class ExportRecordQuality(StrictBaseModel):
    schema_version: str = "repo_harness_export_record_quality_v2_v0"
    training_eligibility: TrainingEligibility = "trainable"
    quality_reasons: list[str] = Field(default_factory=list)
    artifact_manifest_status: Literal["ok", "missing", "invalid", "not_checked"] = "not_checked"
    tool_pairing_status: Literal["ok", "missing", "invalid", "not_checked"] = "not_checked"
    redaction_status: Literal["passed", "failed", "warning", "not_checked"] = "not_checked"
    reward_source: str | None = None
    failure_diagnostics_ref: dict[str, Any] | None = None


class ExportRecord(StrictBaseModel):
    schema_version: str = EXPORT_SCHEMA_VERSION
    sample_id: str
    task_id: str
    source_run_id: str
    payload: dict[str, Any]
    quality: ExportRecordQuality = Field(default_factory=ExportRecordQuality)
    metadata: dict[str, Any] = Field(default_factory=dict)
    filter_status: Literal["included", "skipped", "filtered"] = "included"
    invalid_for_training: bool = False
    invalid_reason: str | None = None

    @model_validator(mode="before")
    @classmethod
    def infer_quality_from_v1_fields(cls, value: Any) -> Any:
        if not isinstance(value, dict) or "quality" in value:
            return value
        inferred = dict(value)
        invalid_for_training = bool(inferred.get("invalid_for_training", False))
        filter_status = inferred.get("filter_status", "included")
        invalid_reason = inferred.get("invalid_reason")
        if not invalid_for_training and filter_status == "included":
            eligibility: TrainingEligibility = "trainable"
        elif filter_status == "skipped":
            eligibility = "skipped"
        elif invalid_reason:
            eligibility = "invalid"
        else:
            eligibility = "diagnostic_only"
        inferred["quality"] = {
            "training_eligibility": eligibility,
            "quality_reasons": [invalid_reason] if invalid_reason else [],
        }
        return inferred

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
            "final_verifier_ref",
            "reward_metadata_ref",
            "reward_metadata",
            "verifier",
            "run_outcome",
            "final_verifier_status",
            "chosen_run_metadata",
            "rejected_run_metadata",
            "chosen_verifier_result_ref",
            "rejected_verifier_result_ref",
        }
        for location, value in (("payload", self.payload), ("metadata", self.metadata)):
            found = _find_blocked_export_value(value, blocked_keys)
            if found is not None:
                raise ValueError(f"{location} 包含不可导出的隐藏或本机字段：{found}")
        self._validate_training_eligibility_compatibility()
        return self

    def _validate_training_eligibility_compatibility(self) -> None:
        eligibility = self.quality.training_eligibility
        if eligibility == "trainable":
            if self.invalid_for_training:
                raise ValueError("trainable 样本不能同时 invalid_for_training=true。")
            if self.filter_status != "included":
                raise ValueError("trainable 样本必须保持 filter_status=included。")
            if self.invalid_reason:
                raise ValueError("trainable 样本不能包含 invalid_reason。")
            return
        if not self.invalid_for_training:
            raise ValueError(f"{eligibility} 样本必须设置 invalid_for_training=true。")
        if not self.invalid_reason and eligibility in {"diagnostic_only", "skipped", "invalid"}:
            raise ValueError(f"{eligibility} 样本必须记录 invalid_reason。")
        if eligibility == "skipped" and self.filter_status != "skipped":
            raise ValueError("skipped 样本必须保持 filter_status=skipped。")


class ExportDataFile(StrictBaseModel):
    schema_version: str = "repo_harness_export_data_file_v2_v0"
    relative_path: str
    sha256: str
    record_count: int = Field(ge=0)


class ExportManifest(StrictBaseModel):
    schema_version: str = EXPORT_MANIFEST_SCHEMA_VERSION
    export_id: str
    format: ExportFormat
    export_policy_version: str = EXPORT_POLICY_VERSION
    source_run_dirs: list[str]
    command_args: dict[str, Any] = Field(default_factory=dict)
    data_files: list[ExportDataFile] = Field(default_factory=list)
    record_count: int = Field(ge=0)
    included_count: int = Field(ge=0)
    filtered_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    invalid_count: int = Field(ge=0)
    diagnostic_only_count: int = Field(ge=0)
    generated_at: str
    exporter_version: str
    audit_report_path: str
    audit_report_sha256: str
    audit_report_md_path: str
    audit_report_md_sha256: str


class ExportAuditItem(StrictBaseModel):
    schema_version: str = "repo_harness_export_audit_item_v2_v0"
    name: str
    status: AuditStatus
    severity: Literal["info", "warning", "error"]
    reason: str
    evidence_ref: dict[str, Any] | None = None


class ExportAuditSample(StrictBaseModel):
    schema_version: str = "repo_harness_export_audit_sample_v2_v0"
    sample_id: str
    data_file: str | None = None
    line_number: int | None = Field(default=None, ge=1)
    run_id: str | None = None
    task_id: str
    training_eligibility: TrainingEligibility
    filter_status: Literal["included", "skipped", "filtered"]
    invalid_for_training: bool
    invalid_reason: str | None = None
    quality_reasons: list[str] = Field(default_factory=list)
    audit_items: list[ExportAuditItem] = Field(default_factory=list)
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    metadata_source: str | None = None
    source_run_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def failed_items_must_explain_quality(self) -> "ExportAuditSample":
        if any(item.status == "failed" for item in self.audit_items):
            if self.training_eligibility == "trainable":
                raise ValueError("存在 failed audit item 时样本不能保持 trainable。")
            if not self.invalid_reason and not self.quality_reasons:
                raise ValueError("failed audit item 必须映射到 invalid_reason 或 quality_reasons。")
        return self


class ExportAuditReport(StrictBaseModel):
    schema_version: str = EXPORT_AUDIT_SCHEMA_VERSION
    export_id: str
    format: ExportFormat
    status: Literal["passed", "passed_with_warnings", "failed", "skipped"]
    source_run_dirs: list[str]
    data_files: list[str] = Field(default_factory=list)
    generated_at: str
    exporter_version: str
    summary: dict[str, Any]
    samples: list[ExportAuditSample] = Field(default_factory=list)


class CompareScope(StrictBaseModel):
    schema_version: str = "repo_harness_compare_scope_v2_v0"
    canonical_key_fields: list[str] = Field(default_factory=lambda: list(STRICT_COMPARE_FIELDS))
    controlled_sampling_variables: list[str] = Field(default_factory=lambda: ["seed", "rollout_index"])
    experimental_variables: list[str] = Field(default_factory=list)
    training_export_allowed: bool = True

    @model_validator(mode="after")
    def require_strict_compare_fields(self) -> "CompareScope":
        missing = sorted(set(STRICT_COMPARE_FIELDS) - set(self.canonical_key_fields))
        if missing:
            raise ValueError(f"compare scope 缺少硬门控字段：{', '.join(missing)}")
        return self


class PairingPolicy(StrictBaseModel):
    schema_version: str = PAIRING_POLICY_VERSION
    pairing_policy_version: str = PAIRING_POLICY_VERSION
    compare_scope: CompareScope = Field(default_factory=CompareScope)
    blocked_reason_enum: list[str] = Field(
        default_factory=lambda: [
            "compare_key_mismatch",
            "missing_reward",
            "reward_tie",
            "missing_formal_final_verifier",
            "non_formal_reward_source",
            "artifact_manifest_invalid",
            "tool_schema_snapshot_mismatch",
            "context_policy_mismatch",
            "budget_mismatch",
            "experimental_variable_not_training_approved",
        ]
    )


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
