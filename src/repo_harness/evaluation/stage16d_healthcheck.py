"""Stage 16D official verifier healthcheck contracts and artifact helpers."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.errors import RepoHarnessError
from repo_harness.schema_base import StrictBaseModel


STAGE16D_PUBLIC_ARTIFACTS: tuple[str, ...] = (
    "stage16d_acceptance_summary.json",
    "stage16d_input_seed_manifest.json",
    "stage16d_healthcheck_manifest.json",
    "stage16d_seed_resolution_report.json",
    "stage16d_gold_healthcheck_report.json",
    "stage16d_noop_healthcheck_report.json",
    "stage16d_proxy_official_disagreement_report.json",
    "stage16d_training_disposition_report.json",
    "stage16d_public_leak_scan_report.json",
    "stage16d_command_log.sanitized.jsonl",
    "stage16d_canonical_evidence_map.json",
    "stage16d_1_smoke_scope_report.json",
    "stage16d_1_official_runner_report.json",
    "stage16d_1_repo_harness_owned_verifier_report.json",
)

STAGE16D_RUNTIME_PRIVATE_ARTIFACTS: tuple[str, ...] = (
    "runtime_private/stage16d_command_log.raw.jsonl",
    "runtime_private/stage16d_official_runner_manifest.json",
)

STAGE16D_ALL_ARTIFACTS: tuple[str, ...] = (
    *STAGE16D_PUBLIC_ARTIFACTS,
    *STAGE16D_RUNTIME_PRIVATE_ARTIFACTS,
)

CANONICAL_EMPTY_PATCH = ""
CANONICAL_EMPTY_PATCH_SHA256 = hashlib.sha256(CANONICAL_EMPTY_PATCH.encode("utf-8")).hexdigest()
CANONICAL_EMPTY_PATCH_REF = f"runtime-private:noop-patch:{CANONICAL_EMPTY_PATCH_SHA256}"

CONCRETE_SEED_STATUS = "concrete"
AGGREGATE_SEED_STATUS = "aggregate_not_directly_runnable"

GOLD_PASSED = "passed"
GOLD_FAILED = "gold_healthcheck_failed"
GOLD_NOT_RUN_AGGREGATE = "not_run_aggregate_seed"
GOLD_NOT_RUN_MISSING_RESULT = "not_run_missing_gold_result"

NOOP_EXPECTED_UNRESOLVED = "expected_unresolved"
NOOP_UNEXPECTEDLY_RESOLVED = "noop_unexpectedly_resolved"
NOOP_NOT_RUN_AGGREGATE = "not_run_aggregate_seed"
NOOP_NOT_RUN_MISSING_RESULT = "not_run_missing_noop_result"
NOOP_NOT_RUN_MISSING_INPUT = "not_run_missing_noop_input"

DISPOSITION_TRAINABLE = "trainable_candidate"
DISPOSITION_DIAGNOSTIC = "diagnostic_only"
DISPOSITION_DIAGNOSTIC_UNTIL_REVIEWED = "diagnostic_only_until_reviewed"
DISPOSITION_ENV_OR_ORACLE_INVALID = "environment_or_oracle_invalid"

OVERALL_VERIFIER_HEALTHY = "verifier_healthy"
OVERALL_HEALTHCHECK_NOT_RUN = "healthcheck_not_run"
OVERALL_AGGREGATE_NOT_RUNNABLE = "aggregate_seed_not_runnable"
OVERALL_PROXY_OFFICIAL_DISAGREEMENT = "proxy_official_disagreement"
OVERALL_IMAGE_DIGEST_MISMATCH = "official_image_digest_mismatch"

PUBLIC_SCAN_SUFFIXES: tuple[str, ...] = (
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".sh",
    ".txt",
    ".yaml",
    ".yml",
)

PUBLIC_LEAK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("local_absolute_path", re.compile(r"/(?:Users|private|home|root|workspace|testbed|tmp|var)(?:/|$)")),
    ("runtime_private_path", re.compile(r"(?:^|[^A-Za-z0-9_-])runtime_private(?:/|$)")),
    ("repo_harness_run_path", re.compile(r"(?:^|[^A-Za-z0-9_.-])repo-harness-run(?:/|$)")),
    ("hidden_selector_marker", re.compile(r"\b(?:FAIL_TO_PASS|PASS_TO_PASS)\b")),
    ("hidden_verifier_marker", re.compile(r"hidden[_-]?verifier", re.IGNORECASE)),
    ("test_patch_marker", re.compile(r"\btest[_-]?patch\b", re.IGNORECASE)),
    ("diff_header", re.compile(r"diff --git ")),
    ("diff_hunk", re.compile(r"@@ ")),
)

RUNTIME_PRIVATE_REF_RE = re.compile(r"^runtime-private:[a-z0-9][a-z0-9_-]*:[a-f0-9]{64}$")
SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")
IMAGE_DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")


Stage16DCheckKind = Literal["gold_patch", "noop_patch"]
Stage16DSeedResolutionStatus = Literal["concrete", "aggregate_not_directly_runnable"]
Stage16DDisposition = Literal[
    "trainable_candidate",
    "diagnostic_only",
    "diagnostic_only_until_reviewed",
    "environment_or_oracle_invalid",
]


class Stage16DHealthcheckInputResult(StrictBaseModel):
    """Normalized result from an official harness or test fixture."""

    instance_id: str
    check_kind: Stage16DCheckKind
    official_resolved: bool | None = None
    status: str | None = None
    healthcheck_backend: str = "swebench_official_harness"
    official_harness_execution_status: str = "executed"
    official_image_source: str | None = None
    official_image_digest: str | None = None
    official_image_digest_locked: bool = False
    selected_dataset_rows_ref: str | None = None
    selected_dataset_rows_sha256: str | None = None
    selected_instance_row_sha256: str | None = None
    gold_predictions_ref: str | None = None
    gold_predictions_sha256: str | None = None
    noop_predictions_ref: str | None = None
    noop_predictions_sha256: str | None = None
    official_command_ref: str | None = None
    official_command_sha256: str | None = None
    runner_digest: str | None = None
    runner_digest_method: str | None = None
    execution_image_digest_by_instance: dict[str, str] = Field(default_factory=dict)
    execution_image_source_by_instance: dict[str, str] = Field(default_factory=dict)
    official_environment_digest_lock_method: str | None = None
    official_result_ref: str | None = None
    official_result_sha256: str | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def validate_result(self) -> "Stage16DHealthcheckInputResult":
        if self.official_harness_execution_status == "executed" and self.official_resolved is None:
            raise ValueError("executed healthcheck result must include official_resolved")
        if self.official_harness_execution_status == "executed":
            if not self.official_result_ref or not is_opaque_runtime_private_ref(self.official_result_ref):
                raise ValueError("executed healthcheck result requires runtime-private official_result_ref")
            if not self.official_result_sha256 or not SHA256_HEX_RE.fullmatch(self.official_result_sha256):
                raise ValueError("executed healthcheck result requires official_result_sha256")
            if not self.official_image_digest or not IMAGE_DIGEST_RE.fullmatch(self.official_image_digest):
                raise ValueError("executed healthcheck result requires sha256 official_image_digest")
            if _runtime_private_ref_digest(self.official_result_ref) != self.official_result_sha256:
                raise ValueError("official_result_ref digest must match official_result_sha256")
            _validate_runtime_private_ref_digest_pair(
                self.selected_dataset_rows_ref,
                self.selected_dataset_rows_sha256,
                "selected_dataset_rows",
                expected_kind="selected-dataset-rows",
            )
            _validate_runtime_private_ref_digest_pair(
                self.gold_predictions_ref,
                self.gold_predictions_sha256,
                "gold_predictions",
                expected_kind="gold-predictions",
            )
            _validate_runtime_private_ref_digest_pair(
                self.noop_predictions_ref,
                self.noop_predictions_sha256,
                "noop_predictions",
                expected_kind="noop-predictions",
            )
            _validate_runtime_private_ref_digest_pair(
                self.official_command_ref,
                self.official_command_sha256,
                "official_command",
                expected_kind="official-command",
            )
            if not self.selected_instance_row_sha256 or not SHA256_HEX_RE.fullmatch(self.selected_instance_row_sha256):
                raise ValueError("executed healthcheck result requires selected_instance_row_sha256")
            if not self.runner_digest or not IMAGE_DIGEST_RE.fullmatch(self.runner_digest):
                raise ValueError("executed healthcheck result requires sha256 runner_digest")
            if not self.runner_digest_method:
                raise ValueError("executed healthcheck result requires runner_digest_method")
            if not self.official_environment_digest_lock_method:
                raise ValueError("executed healthcheck result requires official_environment_digest_lock_method")
            if not _execution_environment_locked_for_instance(
                self.instance_id,
                self.execution_image_digest_by_instance,
                self.official_environment_digest_lock_method,
            ):
                raise ValueError("executed healthcheck result requires per-instance execution image digest")
        if self.official_result_ref is not None and not is_opaque_runtime_private_ref(self.official_result_ref):
            raise ValueError("official_result_ref must use runtime-private:<kind>:<sha256>")
        if self.official_result_ref is not None and _runtime_private_ref_kind(self.official_result_ref) != "official-result":
            raise ValueError("official_result_ref kind must be official-result")
        return self


class Stage16DProxyResult(StrictBaseModel):
    """Internal verifier / proxy reward / official verifier comparison input."""

    instance_id: str
    internal_final_verifier_status: str | None = None
    official_verifier_status: str | None = None
    proxy_reward_status: str | None = None
    proxy_official_disagreement: bool | None = None
    disagreement_type: str | None = None
    final_verifier_boundary_ref: str | None = None
    final_verifier_boundary_available: bool = False
    internal_final_verifier_reran: bool = False
    evaluation_rerun_final_verifier: bool | None = None
    final_verifier_skip_reason: str | None = None
    internal_final_verifier_status_source: str = "unavailable_or_skipped"

    @model_validator(mode="after")
    def validate_boundary_ref(self) -> "Stage16DProxyResult":
        if self.final_verifier_boundary_ref is not None and not is_opaque_runtime_private_ref(
            self.final_verifier_boundary_ref
        ):
            raise ValueError("final_verifier_boundary_ref must use runtime-private:<kind>:<sha256>")
        return self


class Stage16DSeedRecord(StrictBaseModel):
    """Public-safe Stage 16D seed projection from Stage 16D.0."""

    instance_id: str
    seed_role: str
    source_dataset: str | None = None
    candidate_instance_status: str | None = None
    gold_patch_source: str | None = None
    noop_patch_source: str | None = None
    source_evidence_ref: str | None = None
    source_doc_sha256: str | None = None
    stage16d_execution_precondition: str | None = None
    official_validation_backend: str = "swebench_official_harness"


class Stage16DHealthcheckRecord(StrictBaseModel):
    """One public-safe Stage 16D healthcheck classification record."""

    schema_version: str = "repo_harness_stage16d_healthcheck_record_v0"
    instance_id: str
    seed_role: str
    seed_resolution_status: Stage16DSeedResolutionStatus
    official_validation_backend: str
    official_harness_execution_status: str
    official_image_source: str | None = None
    official_image_digest: str | None = None
    official_image_digest_locked: bool = False
    selected_dataset_rows_ref: str | None = None
    selected_dataset_rows_sha256: str | None = None
    selected_instance_row_sha256: str | None = None
    runner_digest: str | None = None
    runner_digest_method: str | None = None
    execution_image_digest_by_instance: dict[str, str] = Field(default_factory=dict)
    execution_image_source_by_instance: dict[str, str] = Field(default_factory=dict)
    official_environment_digest_lock_method: str | None = None
    gold_predictions_ref: str | None = None
    gold_predictions_sha256: str | None = None
    noop_predictions_ref: str | None = None
    noop_predictions_sha256: str | None = None
    gold_official_command_ref: str | None = None
    gold_official_command_sha256: str | None = None
    noop_official_command_ref: str | None = None
    noop_official_command_sha256: str | None = None
    gold_official_result_ref: str | None = None
    gold_official_result_sha256: str | None = None
    gold_patch_ref: str | None = None
    gold_patch_ref_status: str
    gold_healthcheck_status: str
    gold_official_resolved: bool | None = None
    gold_healthcheck_backend: str | None = None
    noop_patch_ref: str | None = None
    noop_patch_ref_status: str
    noop_healthcheck_status: str
    noop_official_resolved: bool | None = None
    noop_healthcheck_backend: str | None = None
    noop_official_result_ref: str | None = None
    noop_official_result_sha256: str | None = None
    internal_final_verifier_status: str | None = None
    proxy_reward_status: str | None = None
    official_verifier_status: str | None = None
    proxy_official_disagreement: bool = False
    disagreement_type: str | None = None
    final_verifier_boundary_ref: str | None = None
    final_verifier_boundary_available: bool = False
    internal_final_verifier_reran: bool = False
    evaluation_rerun_final_verifier: bool | None = None
    final_verifier_skip_reason: str | None = None
    internal_final_verifier_status_source: str = "unavailable_or_skipped"
    overall_healthcheck_status: str
    healthcheck_training_disposition: Stage16DDisposition
    invalid_for_training: bool
    invalid_for_online_rl: bool
    not_run_reason: str | None = None

    @model_validator(mode="after")
    def validate_training_disposition(self) -> "Stage16DHealthcheckRecord":
        if self.healthcheck_training_disposition == DISPOSITION_TRAINABLE:
            if self.seed_resolution_status != CONCRETE_SEED_STATUS:
                raise ValueError("aggregate seed cannot be trainable")
            if self.gold_healthcheck_status != GOLD_PASSED:
                raise ValueError("trainable Stage 16D record requires gold healthcheck passed")
            if self.noop_healthcheck_status != NOOP_EXPECTED_UNRESOLVED:
                raise ValueError("trainable Stage 16D record requires no-op expected_unresolved")
            if not self.official_image_digest_locked:
                raise ValueError("trainable Stage 16D record requires locked official image digest")
            if self.official_harness_execution_status != "executed":
                raise ValueError("trainable Stage 16D record requires executed official harness status")
            if not self.official_image_digest or not IMAGE_DIGEST_RE.fullmatch(self.official_image_digest):
                raise ValueError("trainable Stage 16D record requires sha256 official image digest")
            if not self.runner_digest or not IMAGE_DIGEST_RE.fullmatch(self.runner_digest):
                raise ValueError("trainable Stage 16D record requires sha256 runner digest")
            if not _execution_environment_locked_for_instance(
                self.instance_id,
                self.execution_image_digest_by_instance,
                self.official_environment_digest_lock_method,
            ):
                raise ValueError("trainable Stage 16D record requires per-instance execution image digest")
            if not (self.gold_official_result_ref and self.gold_official_result_sha256):
                raise ValueError("trainable Stage 16D record requires gold official result ref and sha256")
            if not (self.noop_official_result_ref and self.noop_official_result_sha256):
                raise ValueError("trainable Stage 16D record requires no-op official result ref and sha256")
            for label, _kind, ref, digest in _stage16d1_required_ref_digest_pairs(self):
                if not (ref and digest):
                    raise ValueError(f"trainable Stage 16D record requires {label} ref and sha256")
            if self.proxy_official_disagreement:
                raise ValueError("trainable Stage 16D record cannot have proxy/official disagreement")
            if self.invalid_for_training or self.invalid_for_online_rl:
                raise ValueError("trainable Stage 16D record cannot be invalid for training")
        elif not (self.invalid_for_training and self.invalid_for_online_rl):
            raise ValueError("non-trainable Stage 16D record must be invalid for training and online RL")

        for ref in (
            self.gold_patch_ref,
            self.noop_patch_ref,
            self.gold_official_result_ref,
            self.noop_official_result_ref,
            self.final_verifier_boundary_ref,
            self.selected_dataset_rows_ref,
            self.gold_predictions_ref,
            self.noop_predictions_ref,
            self.gold_official_command_ref,
            self.noop_official_command_ref,
        ):
            if ref is not None and not is_opaque_runtime_private_ref(ref):
                raise ValueError("runtime private refs must use runtime-private:<kind>:<sha256>")
        for digest in (
            self.gold_official_result_sha256,
            self.noop_official_result_sha256,
            self.selected_dataset_rows_sha256,
            self.selected_instance_row_sha256,
            self.gold_predictions_sha256,
            self.noop_predictions_sha256,
            self.gold_official_command_sha256,
            self.noop_official_command_sha256,
        ):
            if digest is not None and not SHA256_HEX_RE.fullmatch(digest):
                raise ValueError("Stage 16D sha256 fields must be 64 lowercase hex characters")
        if self.official_image_digest is not None and not IMAGE_DIGEST_RE.fullmatch(self.official_image_digest):
            raise ValueError("official image digest must use sha256:<64 lowercase hex>")
        if self.runner_digest is not None and not IMAGE_DIGEST_RE.fullmatch(self.runner_digest):
            raise ValueError("runner digest must use sha256:<64 lowercase hex>")
        for digest in self.execution_image_digest_by_instance.values():
            if not IMAGE_DIGEST_RE.fullmatch(digest):
                raise ValueError("execution image digest must use sha256:<64 lowercase hex>")
        if (
            self.gold_official_result_ref is not None
            and self.gold_official_result_sha256 is not None
            and _runtime_private_ref_digest(self.gold_official_result_ref) != self.gold_official_result_sha256
        ):
            raise ValueError("gold official result ref digest must match gold official result sha256")
        if (
            self.noop_official_result_ref is not None
            and self.noop_official_result_sha256 is not None
            and _runtime_private_ref_digest(self.noop_official_result_ref) != self.noop_official_result_sha256
        ):
            raise ValueError("no-op official result ref digest must match no-op official result sha256")
        for label, kind, ref, digest in _stage16d1_required_ref_digest_pairs(self):
            if ref is not None and _runtime_private_ref_kind(ref) != kind:
                raise ValueError(f"{label} ref kind must be {kind}")
            if ref is not None and digest is not None and _runtime_private_ref_digest(ref) != digest:
                raise ValueError(f"{label} ref digest must match sha256")
        return self


class Stage16DArtifactBuildResult(StrictBaseModel):
    """Result returned by the Stage 16D artifact builder."""

    output_dir: str
    acceptance_summary_path: str
    record_count: int
    trainable_candidate_count: int
    public_leak_scan_passed: bool


class Stage16DHealthcheckInspectReport(StrictBaseModel):
    """Machine-readable Stage 16D acceptance inspection result."""

    schema_version: str = "repo_harness_stage16d_healthcheck_inspect_report_v0"
    evidence_root: str
    assert_contract_complete: bool = False
    assert_official_healthcheck_complete: bool = False
    summary_path: str | None = None
    summary_loaded: bool = False
    failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    passed: bool = False


def is_opaque_runtime_private_ref(value: str) -> bool:
    return bool(RUNTIME_PRIVATE_REF_RE.fullmatch(value))


def load_stage16d_seed_manifest(path: str | Path) -> list[Stage16DSeedRecord]:
    payload = _read_json(Path(path))
    seeds = payload.get("seeds")
    if not isinstance(seeds, list):
        raise RepoHarnessError("Stage 16D seed manifest 缺少 seeds 数组。")
    return [Stage16DSeedRecord.model_validate(_stage16d_seed_public_subset(seed)) for seed in seeds]


def classify_stage16d_seed(
    seed: Stage16DSeedRecord,
    *,
    gold_result: Stage16DHealthcheckInputResult | None = None,
    noop_result: Stage16DHealthcheckInputResult | None = None,
    proxy_result: Stage16DProxyResult | None = None,
) -> Stage16DHealthcheckRecord:
    seed_resolution_status = _seed_resolution_status(seed)
    official_harness_execution_status = _official_execution_status(gold_result, noop_result)
    official_image_source = _first_non_empty(
        gold_result.official_image_source if gold_result else None,
        noop_result.official_image_source if noop_result else None,
    )
    official_image_digest = _first_non_empty(
        gold_result.official_image_digest if gold_result else None,
        noop_result.official_image_digest if noop_result else None,
    )
    official_image_digest_locked = _official_image_digest_pair_locked(gold_result, noop_result)
    selected_dataset_rows_ref = _matching_field(gold_result, noop_result, "selected_dataset_rows_ref")
    selected_dataset_rows_sha256 = _matching_field(gold_result, noop_result, "selected_dataset_rows_sha256")
    selected_instance_row_sha256 = _matching_field(gold_result, noop_result, "selected_instance_row_sha256")
    runner_digest = _matching_field(gold_result, noop_result, "runner_digest")
    runner_digest_method = _matching_field(gold_result, noop_result, "runner_digest_method")
    execution_image_digest_by_instance = _matching_mapping(
        gold_result,
        noop_result,
        "execution_image_digest_by_instance",
    )
    execution_image_source_by_instance = _matching_mapping(
        gold_result,
        noop_result,
        "execution_image_source_by_instance",
    )
    official_environment_digest_lock_method = _matching_field(
        gold_result,
        noop_result,
        "official_environment_digest_lock_method",
    )

    gold_patch_ref = _gold_patch_ref(seed)
    gold_patch_ref_status = "available" if gold_patch_ref else "unavailable"
    noop_patch_ref, noop_patch_ref_status = _noop_patch_ref(seed)

    gold_status, gold_resolved, gold_backend = _gold_status(seed_resolution_status, gold_result)
    noop_status, noop_resolved, noop_backend = _noop_status(seed_resolution_status, noop_result, noop_patch_ref_status)
    proxy_disagreement, disagreement_type = _proxy_disagreement(proxy_result)

    disposition = compute_stage16d_training_disposition(
        seed_resolution_status=seed_resolution_status,
        gold_healthcheck_status=gold_status,
        noop_healthcheck_status=noop_status,
        official_image_digest_locked=official_image_digest_locked,
        proxy_official_disagreement=proxy_disagreement,
    )
    overall = _overall_status(
        seed_resolution_status=seed_resolution_status,
        gold_healthcheck_status=gold_status,
        noop_healthcheck_status=noop_status,
        official_image_digest_locked=official_image_digest_locked,
        proxy_official_disagreement=proxy_disagreement,
        disposition=disposition,
    )
    not_run_reason = _not_run_reason(seed_resolution_status, gold_status, noop_status, noop_patch_ref_status)

    return Stage16DHealthcheckRecord(
        instance_id=seed.instance_id,
        seed_role=seed.seed_role,
        seed_resolution_status=seed_resolution_status,
        official_validation_backend=seed.official_validation_backend,
        official_harness_execution_status=official_harness_execution_status,
        official_image_source=official_image_source,
        official_image_digest=official_image_digest,
        official_image_digest_locked=official_image_digest_locked,
        selected_dataset_rows_ref=selected_dataset_rows_ref,
        selected_dataset_rows_sha256=selected_dataset_rows_sha256,
        selected_instance_row_sha256=selected_instance_row_sha256,
        runner_digest=runner_digest,
        runner_digest_method=runner_digest_method,
        execution_image_digest_by_instance=execution_image_digest_by_instance,
        execution_image_source_by_instance=execution_image_source_by_instance,
        official_environment_digest_lock_method=official_environment_digest_lock_method,
        gold_predictions_ref=gold_result.gold_predictions_ref if gold_result else None,
        gold_predictions_sha256=gold_result.gold_predictions_sha256 if gold_result else None,
        noop_predictions_ref=noop_result.noop_predictions_ref if noop_result else None,
        noop_predictions_sha256=noop_result.noop_predictions_sha256 if noop_result else None,
        gold_official_command_ref=gold_result.official_command_ref if gold_result else None,
        gold_official_command_sha256=gold_result.official_command_sha256 if gold_result else None,
        noop_official_command_ref=noop_result.official_command_ref if noop_result else None,
        noop_official_command_sha256=noop_result.official_command_sha256 if noop_result else None,
        gold_patch_ref=gold_patch_ref,
        gold_patch_ref_status=gold_patch_ref_status,
        gold_healthcheck_status=gold_status,
        gold_official_resolved=gold_resolved,
        gold_healthcheck_backend=gold_backend,
        gold_official_result_ref=gold_result.official_result_ref if gold_result else None,
        gold_official_result_sha256=gold_result.official_result_sha256 if gold_result else None,
        noop_patch_ref=noop_patch_ref,
        noop_patch_ref_status=noop_patch_ref_status,
        noop_healthcheck_status=noop_status,
        noop_official_resolved=noop_resolved,
        noop_healthcheck_backend=noop_backend,
        noop_official_result_ref=noop_result.official_result_ref if noop_result else None,
        noop_official_result_sha256=noop_result.official_result_sha256 if noop_result else None,
        internal_final_verifier_status=proxy_result.internal_final_verifier_status if proxy_result else None,
        proxy_reward_status=proxy_result.proxy_reward_status if proxy_result else None,
        official_verifier_status=proxy_result.official_verifier_status if proxy_result else None,
        proxy_official_disagreement=proxy_disagreement,
        disagreement_type=disagreement_type,
        final_verifier_boundary_ref=proxy_result.final_verifier_boundary_ref if proxy_result else None,
        final_verifier_boundary_available=proxy_result.final_verifier_boundary_available if proxy_result else False,
        internal_final_verifier_reran=proxy_result.internal_final_verifier_reran if proxy_result else False,
        evaluation_rerun_final_verifier=proxy_result.evaluation_rerun_final_verifier if proxy_result else None,
        final_verifier_skip_reason=proxy_result.final_verifier_skip_reason if proxy_result else None,
        internal_final_verifier_status_source=(
            proxy_result.internal_final_verifier_status_source if proxy_result else "unavailable_or_skipped"
        ),
        overall_healthcheck_status=overall,
        healthcheck_training_disposition=disposition,
        invalid_for_training=disposition != DISPOSITION_TRAINABLE,
        invalid_for_online_rl=disposition != DISPOSITION_TRAINABLE,
        not_run_reason=not_run_reason,
    )


def compute_stage16d_training_disposition(
    *,
    seed_resolution_status: str,
    gold_healthcheck_status: str,
    noop_healthcheck_status: str,
    official_image_digest_locked: bool,
    proxy_official_disagreement: bool,
) -> Stage16DDisposition:
    if seed_resolution_status != CONCRETE_SEED_STATUS:
        return DISPOSITION_DIAGNOSTIC
    if gold_healthcheck_status == GOLD_FAILED or noop_healthcheck_status == NOOP_UNEXPECTEDLY_RESOLVED:
        return DISPOSITION_ENV_OR_ORACLE_INVALID
    if proxy_official_disagreement:
        return DISPOSITION_DIAGNOSTIC_UNTIL_REVIEWED
    if (
        gold_healthcheck_status == GOLD_PASSED
        and noop_healthcheck_status == NOOP_EXPECTED_UNRESOLVED
        and official_image_digest_locked
    ):
        return DISPOSITION_TRAINABLE
    return DISPOSITION_DIAGNOSTIC


def build_stage16d_healthcheck_artifacts(
    *,
    seed_manifest_path: str | Path,
    output_dir: str | Path,
    gold_results_path: str | Path | None = None,
    noop_results_path: str | Path | None = None,
    proxy_results_path: str | Path | None = None,
    stage16d0_commit: str = "69da8353",
    stage16c_commit: str = "4711573c",
) -> Stage16DArtifactBuildResult:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    runtime_private = out / "runtime_private"
    runtime_private.mkdir(exist_ok=True)

    seeds = load_stage16d_seed_manifest(seed_manifest_path)
    seed_manifest_sha256 = _sha256_file(Path(seed_manifest_path))
    gold_results = _load_results(gold_results_path, check_kind="gold_patch")
    noop_results = _load_results(noop_results_path, check_kind="noop_patch")
    proxy_results = _load_proxy_results(proxy_results_path)
    records = [
        classify_stage16d_seed(
            seed,
            gold_result=gold_results.get(seed.instance_id),
            noop_result=noop_results.get(seed.instance_id),
            proxy_result=proxy_results.get(seed.instance_id),
        )
        for seed in seeds
    ]

    command_log = {
        "schema_version": "repo_harness_stage16d_command_log_entry_v0",
        "command_name": "build_stage16d_healthcheck_artifacts",
        "seed_manifest_sha256": seed_manifest_sha256,
        "gold_results_sha256": _sha256_file(Path(gold_results_path)) if gold_results_path else None,
        "noop_results_sha256": _sha256_file(Path(noop_results_path)) if noop_results_path else None,
        "proxy_results_sha256": _sha256_file(Path(proxy_results_path)) if proxy_results_path else None,
    }
    _write_jsonl(out / "stage16d_command_log.sanitized.jsonl", [command_log])
    _write_jsonl(runtime_private / "stage16d_command_log.raw.jsonl", [command_log])
    _write_json(
        runtime_private / "stage16d_official_runner_manifest.json",
        {
            "schema_version": "repo_harness_stage16d_official_runner_manifest_v0",
            "official_harness_execution_status": "not_run_in_local_schema_phase",
            "raw_inputs_present": False,
        },
    )

    _write_input_seed_manifest(out / "stage16d_input_seed_manifest.json", seeds, seed_manifest_sha256)
    _write_json(
        out / "stage16d_healthcheck_manifest.json",
        {
            "schema_version": "repo_harness_stage16d_healthcheck_manifest_v0",
            "records": [record.model_dump(mode="json") for record in records],
        },
    )
    _write_json(
        out / "stage16d_seed_resolution_report.json",
        {
            "schema_version": "repo_harness_stage16d_seed_resolution_report_v0",
            "records": [
                {
                    "instance_id": record.instance_id,
                    "seed_role": record.seed_role,
                    "seed_resolution_status": record.seed_resolution_status,
                    "not_run_reason": record.not_run_reason,
                    "healthcheck_training_disposition": record.healthcheck_training_disposition,
                }
                for record in records
            ],
        },
    )
    _write_json(
        out / "stage16d_gold_healthcheck_report.json",
        {
            "schema_version": "repo_harness_stage16d_gold_healthcheck_report_v0",
            "records": [
                {
                    "instance_id": record.instance_id,
                    "gold_patch_ref": record.gold_patch_ref,
                    "gold_patch_ref_status": record.gold_patch_ref_status,
                    "gold_healthcheck_status": record.gold_healthcheck_status,
                    "gold_official_resolved": record.gold_official_resolved,
                    "gold_official_result_ref": record.gold_official_result_ref,
                    "gold_official_result_sha256": record.gold_official_result_sha256,
                    "selected_dataset_rows_ref": record.selected_dataset_rows_ref,
                    "selected_dataset_rows_sha256": record.selected_dataset_rows_sha256,
                    "selected_instance_row_sha256": record.selected_instance_row_sha256,
                    "runner_digest": record.runner_digest,
                    "runner_digest_method": record.runner_digest_method,
                    "execution_image_digest_by_instance": record.execution_image_digest_by_instance,
                    "execution_image_source_by_instance": record.execution_image_source_by_instance,
                    "official_environment_digest_lock_method": record.official_environment_digest_lock_method,
                    "gold_predictions_ref": record.gold_predictions_ref,
                    "gold_predictions_sha256": record.gold_predictions_sha256,
                    "gold_official_command_ref": record.gold_official_command_ref,
                    "gold_official_command_sha256": record.gold_official_command_sha256,
                    "healthcheck_training_disposition": record.healthcheck_training_disposition,
                }
                for record in records
            ],
        },
    )
    _write_json(
        out / "stage16d_noop_healthcheck_report.json",
        {
            "schema_version": "repo_harness_stage16d_noop_healthcheck_report_v0",
            "canonical_empty_patch_ref": CANONICAL_EMPTY_PATCH_REF,
            "records": [
                {
                    "instance_id": record.instance_id,
                    "noop_patch_ref": record.noop_patch_ref,
                    "noop_patch_ref_status": record.noop_patch_ref_status,
                    "noop_healthcheck_status": record.noop_healthcheck_status,
                    "noop_official_resolved": record.noop_official_resolved,
                    "noop_official_result_ref": record.noop_official_result_ref,
                    "noop_official_result_sha256": record.noop_official_result_sha256,
                    "selected_dataset_rows_ref": record.selected_dataset_rows_ref,
                    "selected_dataset_rows_sha256": record.selected_dataset_rows_sha256,
                    "selected_instance_row_sha256": record.selected_instance_row_sha256,
                    "runner_digest": record.runner_digest,
                    "runner_digest_method": record.runner_digest_method,
                    "execution_image_digest_by_instance": record.execution_image_digest_by_instance,
                    "execution_image_source_by_instance": record.execution_image_source_by_instance,
                    "official_environment_digest_lock_method": record.official_environment_digest_lock_method,
                    "noop_predictions_ref": record.noop_predictions_ref,
                    "noop_predictions_sha256": record.noop_predictions_sha256,
                    "noop_official_command_ref": record.noop_official_command_ref,
                    "noop_official_command_sha256": record.noop_official_command_sha256,
                    "healthcheck_training_disposition": record.healthcheck_training_disposition,
                }
                for record in records
            ],
        },
    )
    _write_json(
        out / "stage16d_proxy_official_disagreement_report.json",
        {
            "schema_version": "repo_harness_stage16d_proxy_official_disagreement_report_v0",
            "records": [
                {
                    "instance_id": record.instance_id,
                    "proxy_official_disagreement": record.proxy_official_disagreement,
                    "disagreement_type": record.disagreement_type,
                    "internal_final_verifier_status": record.internal_final_verifier_status,
                    "official_verifier_status": record.official_verifier_status,
                    "internal_final_verifier_status_source": record.internal_final_verifier_status_source,
                    "healthcheck_training_disposition": record.healthcheck_training_disposition,
                }
                for record in records
            ],
        },
    )
    _write_json(
        out / "stage16d_training_disposition_report.json",
        {
            "schema_version": "repo_harness_stage16d_training_disposition_report_v0",
            "records": [
                {
                    "instance_id": record.instance_id,
                    "overall_healthcheck_status": record.overall_healthcheck_status,
                    "healthcheck_training_disposition": record.healthcheck_training_disposition,
                    "invalid_for_training": record.invalid_for_training,
                    "invalid_for_online_rl": record.invalid_for_online_rl,
                }
                for record in records
            ],
        },
    )
    _write_stage16d1_scope_report(
        out / "stage16d_1_smoke_scope_report.json",
        seed_manifest_path=Path(seed_manifest_path),
        seed_manifest_sha256=seed_manifest_sha256,
        seeds=seeds,
    )
    _write_stage16d1_official_runner_report(out / "stage16d_1_official_runner_report.json", records)
    _write_json(
        out / "stage16d_1_repo_harness_owned_verifier_report.json",
        {
            "schema_version": "repo_harness_stage16d_1_repo_harness_owned_verifier_report_v0",
            "status": "not_run_in_stage16d_1",
            "reason": "optional_supplement_not_required_for_official_smoke",
        },
    )
    _write_json(
        out / "stage16d_canonical_evidence_map.json",
        {
            "schema_version": "repo_harness_stage16d_canonical_evidence_map_v0",
            "public_items": {artifact: artifact for artifact in STAGE16D_PUBLIC_ARTIFACTS},
            "private_item_count": len(STAGE16D_RUNTIME_PRIVATE_ARTIFACTS),
            "private_item_refs": {
                artifact.rsplit("/", 1)[-1].replace(".", "_"): _runtime_private_artifact_ref(out / artifact)
                for artifact in STAGE16D_RUNTIME_PRIVATE_ARTIFACTS
            },
        },
    )

    preliminary_summary = _build_summary(
        records,
        stage16d0_commit=stage16d0_commit,
        stage16c_commit=stage16c_commit,
        leak_failures=[],
    )
    _write_json(out / "stage16d_acceptance_summary.json", preliminary_summary)
    _write_public_leak_scan_report(out, [])
    leak_failures = scan_stage16d_public_evidence(out)
    summary = _build_summary(
        records,
        stage16d0_commit=stage16d0_commit,
        stage16c_commit=stage16c_commit,
        leak_failures=leak_failures,
    )
    _write_json(out / "stage16d_acceptance_summary.json", summary)
    leak_failures = scan_stage16d_public_evidence(out)
    summary = _build_summary(
        records,
        stage16d0_commit=stage16d0_commit,
        stage16c_commit=stage16c_commit,
        leak_failures=leak_failures,
    )
    _write_json(out / "stage16d_acceptance_summary.json", summary)
    _write_public_leak_scan_report(out, leak_failures)
    leak_failures = scan_stage16d_public_evidence(out)
    summary = _build_summary(
        records,
        stage16d0_commit=stage16d0_commit,
        stage16c_commit=stage16c_commit,
        leak_failures=leak_failures,
    )
    _write_json(out / "stage16d_acceptance_summary.json", summary)
    _write_json(
        out / "stage16d_public_leak_scan_report.json",
        _public_leak_scan_report_payload(leak_failures),
    )
    return Stage16DArtifactBuildResult(
        output_dir=out.as_posix(),
        acceptance_summary_path=(out / "stage16d_acceptance_summary.json").as_posix(),
        record_count=len(records),
        trainable_candidate_count=summary["training_eligible_after_healthcheck_count"],
        public_leak_scan_passed=not leak_failures,
    )


def inspect_stage16d_healthcheck(
    evidence_path: str | Path,
    *,
    assert_contract_complete: bool = False,
    assert_official_healthcheck_complete: bool = False,
) -> str:
    report = inspect_stage16d_healthcheck_report(
        evidence_path,
        assert_contract_complete=assert_contract_complete,
        assert_official_healthcheck_complete=assert_official_healthcheck_complete,
    )
    if (assert_contract_complete or assert_official_healthcheck_complete) and report.failures:
        raise RepoHarnessError("; ".join(report.failures))
    return report.model_dump_json(indent=2)


def inspect_stage16d_healthcheck_report(
    evidence_path: str | Path,
    *,
    assert_contract_complete: bool = False,
    assert_official_healthcheck_complete: bool = False,
) -> Stage16DHealthcheckInspectReport:
    root = Path(evidence_path)
    failures: list[str] = []
    warnings: list[str] = []
    if not root.exists() or not root.is_dir():
        failures.append("stage16d_evidence_root_missing_or_not_directory")
        return Stage16DHealthcheckInspectReport(
            evidence_root=root.as_posix(),
            assert_contract_complete=assert_contract_complete,
            assert_official_healthcheck_complete=assert_official_healthcheck_complete,
            failures=failures,
            warnings=warnings,
            passed=False,
        )

    for artifact in STAGE16D_PUBLIC_ARTIFACTS:
        if not (root / artifact).is_file():
            failures.append(f"missing_stage16d_public_artifact:{artifact}")
    for artifact in STAGE16D_RUNTIME_PRIVATE_ARTIFACTS:
        if not (root / artifact).is_file():
            warnings.append(f"missing_stage16d_runtime_private_artifact:{artifact}")

    summary = _load_optional_json(root / "stage16d_acceptance_summary.json", failures)
    manifest = _load_optional_json(root / "stage16d_healthcheck_manifest.json", failures)
    input_seed_manifest = _load_optional_json(root / "stage16d_input_seed_manifest.json", failures)
    canonical_evidence_map = _load_optional_json(root / "stage16d_canonical_evidence_map.json", failures)
    stage16d1_scope_report = _load_optional_json(root / "stage16d_1_smoke_scope_report.json", failures)
    stage16d1_runner_report = _load_optional_json(root / "stage16d_1_official_runner_report.json", failures)
    stage16d1_repo_owned_report = _load_optional_json(
        root / "stage16d_1_repo_harness_owned_verifier_report.json",
        failures,
    )
    seed_records = _seeds_from_input_manifest(input_seed_manifest, failures)
    records = _records_from_manifest(manifest, failures)
    failures.extend(_validate_stage16d_records(records))
    failures.extend(_validate_seed_manifest_binding(seed_records, records))
    failures.extend(_validate_stage16d_report_instance_sets(root, seed_records))
    failures.extend(_validate_stage16d1_reports(
        canonical_evidence_map=canonical_evidence_map,
        scope_report=stage16d1_scope_report,
        runner_report=stage16d1_runner_report,
        repo_owned_report=stage16d1_repo_owned_report,
        seed_records=seed_records,
        records=records,
        assert_official_healthcheck_complete=assert_official_healthcheck_complete,
    ))
    failures.extend(scan_stage16d_public_evidence(root))

    if summary:
        failures.extend(_validate_stage16d_summary(summary, records, seed_records))
    if assert_contract_complete:
        failures.extend(_assert_contract_complete(summary, records, seed_records))
    if assert_official_healthcheck_complete:
        failures.extend(_assert_official_complete(summary, records))

    return Stage16DHealthcheckInspectReport(
        evidence_root=root.as_posix(),
        assert_contract_complete=assert_contract_complete,
        assert_official_healthcheck_complete=assert_official_healthcheck_complete,
        summary_path=(root / "stage16d_acceptance_summary.json").as_posix() if summary else None,
        summary_loaded=bool(summary),
        failures=failures,
        warnings=warnings,
        passed=not failures,
    )


def scan_stage16d_public_evidence(root: str | Path) -> list[str]:
    base = Path(root)
    failures: list[str] = []
    for path in _iter_public_files(base):
        relative = path.relative_to(base).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            failures.append(f"public_file_not_utf8:{relative}")
            continue
        for reason, pattern in PUBLIC_LEAK_PATTERNS:
            if pattern.search(text):
                failures.append(f"public_evidence_leak:{reason}:{relative}")
    return failures


def _write_public_leak_scan_report(out: Path, leak_failures: list[str]) -> None:
    _write_json(out / "stage16d_public_leak_scan_report.json", _public_leak_scan_report_payload(leak_failures))


def _public_leak_scan_report_payload(leak_failures: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_stage16d_public_leak_scan_report_v0",
        "public_files_scanned": list(STAGE16D_PUBLIC_ARTIFACTS),
        "public_leak_scan_passed": not leak_failures,
        "failures": leak_failures,
        "allowlisted_contexts": [
            "gold_healthcheck_status field names",
            "noop_oracle_risk seed role",
            "candidate_oracle_noop_resolved risk enum",
        ],
    }


def _write_stage16d1_scope_report(
    path: Path,
    *,
    seed_manifest_path: Path,
    seed_manifest_sha256: str,
    seeds: list[Stage16DSeedRecord],
) -> None:
    concrete = [seed for seed in seeds if _seed_resolution_status(seed) == CONCRETE_SEED_STATUS]
    positive = [seed for seed in concrete if seed.seed_role == "positive_path_official_resolved"]
    risk = [seed for seed in concrete if "risk" in seed.seed_role]
    try:
        source_payload = _read_json(seed_manifest_path)
    except (json.JSONDecodeError, UnicodeDecodeError, FileNotFoundError):
        source_payload = {}
    source_ref = source_payload.get("source_manifest_ref")
    if not isinstance(source_ref, str) or not source_ref:
        source_ref = _public_safe_path_ref(seed_manifest_path)
    full_coverage = bool(source_payload.get("full_stage16d0_seed_coverage_claimed", False))
    remaining_count = source_payload.get("remaining_stage16d0_seed_count_not_healthchecked")
    if not isinstance(remaining_count, int):
        remaining_count = 0 if full_coverage else None
    _write_json(
        path,
        {
            "schema_version": "repo_harness_stage16d_1_smoke_scope_report_v0",
            "source_manifest_ref": source_ref,
            "source_manifest_sha256": seed_manifest_sha256,
            "selection_policy": source_payload.get("selection_policy", "stage16d_healthcheck_contract"),
            "scope_limit": source_payload.get("scope_limit", "Stage 16D healthcheck evidence scope."),
            "selected_instance_ids": [seed.instance_id for seed in seeds],
            "selected_seed_count": len(seeds),
            "selected_concrete_seed_count": len(concrete),
            "selected_positive_path_seed_count": len(positive),
            "selected_risk_seed_count": len(risk),
            "full_stage16d0_seed_coverage_claimed": full_coverage,
            "remaining_stage16d0_seed_count_not_healthchecked": remaining_count,
        },
    )


def _write_stage16d1_official_runner_report(path: Path, records: list[Stage16DHealthcheckRecord]) -> None:
    executed_records = [record for record in records if record.official_harness_execution_status == "executed"]
    first = executed_records[0] if executed_records else None
    _write_json(
        path,
        {
            "schema_version": "repo_harness_stage16d_1_official_runner_report_v0",
            "status": "executed" if executed_records else "not_run_in_local_schema_phase",
            "runner_kind": "swebench_official_harness" if executed_records else None,
            "runner_version": "unknown" if executed_records else None,
            "official_image_source": first.official_image_source if first else None,
            "official_image_digest": first.official_image_digest if first else None,
            "official_image_digest_locked": first.official_image_digest_locked if first else False,
            "runner_digest": first.runner_digest if first else None,
            "runner_digest_method": first.runner_digest_method if first else None,
            "execution_image_digest_by_instance": _merged_execution_image_digests(records),
            "execution_image_source_by_instance": _merged_execution_image_sources(records),
            "official_environment_digest_lock_method": first.official_environment_digest_lock_method if first else None,
            "selected_dataset_rows_ref": first.selected_dataset_rows_ref if first else None,
            "selected_dataset_rows_sha256": first.selected_dataset_rows_sha256 if first else None,
            "selected_instance_row_sha256_by_instance": {
                record.instance_id: record.selected_instance_row_sha256
                for record in records
                if record.selected_instance_row_sha256
            },
            "gold_predictions_ref": first.gold_predictions_ref if first else None,
            "gold_predictions_sha256": first.gold_predictions_sha256 if first else None,
            "noop_predictions_ref": first.noop_predictions_ref if first else None,
            "noop_predictions_sha256": first.noop_predictions_sha256 if first else None,
            "gold_official_command_ref": first.gold_official_command_ref if first else None,
            "gold_official_command_sha256": first.gold_official_command_sha256 if first else None,
            "noop_official_command_ref": first.noop_official_command_ref if first else None,
            "noop_official_command_sha256": first.noop_official_command_sha256 if first else None,
            "docker_available": None,
            "docker_version": None,
            "max_workers": 1 if executed_records else None,
            "timeout_seconds": None,
            "selected_instance_ids": [record.instance_id for record in records],
            "gold_run_status": _run_status_from_records(records, check_kind="gold_patch"),
            "noop_run_status": _run_status_from_records(records, check_kind="noop_patch"),
            "raw_report_ref": None,
            "raw_report_sha256": None,
            "sanitized_command_log_ref": None,
        },
    )


def _validate_stage16d1_reports(
    *,
    canonical_evidence_map: Mapping[str, Any],
    scope_report: Mapping[str, Any],
    runner_report: Mapping[str, Any],
    repo_owned_report: Mapping[str, Any],
    seed_records: list[Stage16DSeedRecord],
    records: list[Stage16DHealthcheckRecord],
    assert_official_healthcheck_complete: bool,
) -> list[str]:
    failures: list[str] = []
    public_items = canonical_evidence_map.get("public_items")
    if not isinstance(public_items, Mapping):
        failures.append("stage16d_canonical_evidence_map_missing_public_items")
    else:
        for artifact in (
            "stage16d_1_smoke_scope_report.json",
            "stage16d_1_official_runner_report.json",
            "stage16d_1_repo_harness_owned_verifier_report.json",
        ):
            if artifact not in public_items:
                failures.append(f"stage16d1_artifact_missing_from_canonical_map:{artifact}")
    expected_ids = [seed.instance_id for seed in seed_records]
    if scope_report:
        if scope_report.get("selected_instance_ids") != expected_ids:
            failures.append("stage16d1_scope_report_selected_instance_ids_mismatch")
        if scope_report.get("selected_seed_count") != len(seed_records):
            failures.append("stage16d1_scope_report_seed_count_mismatch")
        if scope_report.get("full_stage16d0_seed_coverage_claimed") is not False:
            failures.append("stage16d1_scope_report_full_coverage_must_be_false")
        if not isinstance(scope_report.get("source_manifest_sha256"), str) or not SHA256_HEX_RE.fullmatch(
            scope_report.get("source_manifest_sha256", "")
        ):
            failures.append("stage16d1_scope_report_missing_source_manifest_sha256")
    if repo_owned_report and repo_owned_report.get("status") not in {"not_run_in_stage16d_1", "executed"}:
        failures.append("stage16d1_repo_owned_report_invalid_status")
    if runner_report:
        if runner_report.get("selected_instance_ids") != [record.instance_id for record in records]:
            failures.append("stage16d1_runner_report_selected_instance_ids_mismatch")
    if assert_official_healthcheck_complete:
        failures.extend(_assert_stage16d1_runner_report_complete(runner_report, records))
    return failures


def _assert_stage16d1_runner_report_complete(
    runner_report: Mapping[str, Any],
    records: list[Stage16DHealthcheckRecord],
) -> list[str]:
    failures: list[str] = []
    if runner_report.get("status") != "executed":
        failures.append("stage16d1_runner_report_not_executed")
    required = (
        "selected_dataset_rows_sha256",
        "gold_predictions_sha256",
        "noop_predictions_sha256",
        "gold_official_command_sha256",
        "noop_official_command_sha256",
        "runner_digest",
        "execution_image_digest_by_instance",
    )
    for field in required:
        if not runner_report.get(field):
            failures.append(f"stage16d1_runner_report_missing:{field}")
    failures.extend(_stage16d1_runner_report_record_mismatches(runner_report, records))
    for record in records:
        if record.seed_resolution_status != CONCRETE_SEED_STATUS:
            continue
        failures.extend(_official_complete_stage16d1_binding_failures(record))
    return failures


def _stage16d1_runner_report_record_mismatches(
    runner_report: Mapping[str, Any],
    records: list[Stage16DHealthcheckRecord],
) -> list[str]:
    failures: list[str] = []
    concrete_records = [record for record in records if record.seed_resolution_status == CONCRETE_SEED_STATUS]
    if not concrete_records:
        return failures

    uniform_fields = (
        "official_image_source",
        "official_image_digest",
        "official_image_digest_locked",
        "runner_digest",
        "runner_digest_method",
        "official_environment_digest_lock_method",
        "selected_dataset_rows_ref",
        "selected_dataset_rows_sha256",
        "gold_predictions_ref",
        "gold_predictions_sha256",
        "noop_predictions_ref",
        "noop_predictions_sha256",
        "gold_official_command_ref",
        "gold_official_command_sha256",
        "noop_official_command_ref",
        "noop_official_command_sha256",
    )
    for field in uniform_fields:
        expected = _uniform_record_field(concrete_records, field)
        if expected is _NON_UNIFORM_FIELD:
            failures.append(f"stage16d1_runner_report_non_uniform_record_field:{field}")
        elif runner_report.get(field) != expected:
            failures.append(f"stage16d1_runner_report_field_mismatch:{field}")

    expected_selected_rows = {
        record.instance_id: record.selected_instance_row_sha256
        for record in concrete_records
        if record.selected_instance_row_sha256
    }
    if runner_report.get("selected_instance_row_sha256_by_instance") != expected_selected_rows:
        failures.append("stage16d1_runner_report_selected_instance_row_sha256_mismatch")

    expected_execution_digests = _merged_execution_image_digests(concrete_records)
    if runner_report.get("execution_image_digest_by_instance") != expected_execution_digests:
        failures.append("stage16d1_runner_report_execution_image_digest_mismatch")

    expected_execution_sources = _merged_execution_image_sources(concrete_records)
    if runner_report.get("execution_image_source_by_instance") != expected_execution_sources:
        failures.append("stage16d1_runner_report_execution_image_source_mismatch")

    if runner_report.get("gold_run_status") != _run_status_from_records(records, check_kind="gold_patch"):
        failures.append("stage16d1_runner_report_gold_run_status_mismatch")
    if runner_report.get("noop_run_status") != _run_status_from_records(records, check_kind="noop_patch"):
        failures.append("stage16d1_runner_report_noop_run_status_mismatch")

    return failures


_NON_UNIFORM_FIELD = object()


def _uniform_record_field(records: list[Stage16DHealthcheckRecord], field: str) -> Any:
    values = [getattr(record, field) for record in records]
    if not values:
        return None
    first = values[0]
    return first if all(value == first for value in values) else _NON_UNIFORM_FIELD


def _record_has_stage16d1_binding(record: Stage16DHealthcheckRecord) -> bool:
    return not _official_complete_stage16d1_binding_failures(record)


def _official_complete_stage16d1_binding_failures(record: Stage16DHealthcheckRecord) -> list[str]:
    failures: list[str] = []
    for label, kind, ref, digest in _stage16d1_required_ref_digest_pairs(record):
        if not ref or not digest:
            failures.append(f"official_complete_missing_{label}:{record.instance_id}")
        elif not is_opaque_runtime_private_ref(ref) or _runtime_private_ref_kind(ref) != kind:
            failures.append(f"official_complete_{label}_kind_mismatch:{record.instance_id}")
        elif _runtime_private_ref_digest(ref) != digest:
            failures.append(f"official_complete_{label}_digest_mismatch:{record.instance_id}")
    if not record.selected_instance_row_sha256:
        failures.append(f"official_complete_missing_selected_instance_row_sha256:{record.instance_id}")
    if not record.runner_digest:
        failures.append(f"official_complete_missing_runner_digest:{record.instance_id}")
    if not _execution_environment_locked_for_instance(
        record.instance_id,
        record.execution_image_digest_by_instance,
        record.official_environment_digest_lock_method,
    ):
        failures.append(f"official_complete_missing_execution_image_digest:{record.instance_id}")
    return failures


def _merged_execution_image_digests(records: list[Stage16DHealthcheckRecord]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for record in records:
        merged.update(record.execution_image_digest_by_instance)
    return merged


def _merged_execution_image_sources(records: list[Stage16DHealthcheckRecord]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for record in records:
        merged.update(record.execution_image_source_by_instance)
    return merged


def _run_status_from_records(records: list[Stage16DHealthcheckRecord], *, check_kind: Stage16DCheckKind) -> str:
    statuses = []
    for record in records:
        if check_kind == "gold_patch":
            statuses.append(record.gold_healthcheck_status)
        else:
            statuses.append(record.noop_healthcheck_status)
    return "executed" if all(not status.startswith("not_run") for status in statuses) else "not_run_or_incomplete"


def _public_safe_path_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def _seed_resolution_status(seed: Stage16DSeedRecord) -> Stage16DSeedResolutionStatus:
    status = seed.candidate_instance_status or ""
    if status.startswith("aggregate") or seed.instance_id.startswith("repr20-gold-smoke-aggregate"):
        return AGGREGATE_SEED_STATUS
    return CONCRETE_SEED_STATUS


def _gold_patch_ref(seed: Stage16DSeedRecord) -> str | None:
    source = seed.gold_patch_source or ""
    if source in {"", "not_available", "not_applicable"}:
        return None
    digest = hashlib.sha256(f"gold:{seed.instance_id}:{source}".encode("utf-8")).hexdigest()
    return f"runtime-private:gold-patch:{digest}"


def _noop_patch_ref(seed: Stage16DSeedRecord) -> tuple[str | None, str]:
    source = seed.noop_patch_source or ""
    if source in {"", "not_available", "not_applicable"}:
        return CANONICAL_EMPTY_PATCH_REF, "generated_canonical_empty_patch"
    digest = hashlib.sha256(f"noop:{seed.instance_id}:{source}".encode("utf-8")).hexdigest()
    return f"runtime-private:noop-patch:{digest}", "available_from_seed_manifest"


def _gold_status(
    seed_resolution_status: str,
    result: Stage16DHealthcheckInputResult | None,
) -> tuple[str, bool | None, str | None]:
    if seed_resolution_status != CONCRETE_SEED_STATUS:
        return GOLD_NOT_RUN_AGGREGATE, None, None
    if result is None:
        return GOLD_NOT_RUN_MISSING_RESULT, None, None
    if result.official_resolved is True:
        return GOLD_PASSED, True, result.healthcheck_backend
    return GOLD_FAILED, False, result.healthcheck_backend


def _noop_status(
    seed_resolution_status: str,
    result: Stage16DHealthcheckInputResult | None,
    noop_patch_ref_status: str,
) -> tuple[str, bool | None, str | None]:
    if seed_resolution_status != CONCRETE_SEED_STATUS:
        return NOOP_NOT_RUN_AGGREGATE, None, None
    if noop_patch_ref_status == "not_run_missing_noop_input":
        return NOOP_NOT_RUN_MISSING_INPUT, None, None
    if result is None:
        return NOOP_NOT_RUN_MISSING_RESULT, None, None
    if result.official_resolved is False:
        return NOOP_EXPECTED_UNRESOLVED, False, result.healthcheck_backend
    return NOOP_UNEXPECTEDLY_RESOLVED, True, result.healthcheck_backend


def _proxy_disagreement(result: Stage16DProxyResult | None) -> tuple[bool, str | None]:
    if result is None:
        return False, None
    if result.proxy_official_disagreement is not None:
        return result.proxy_official_disagreement, result.disagreement_type
    internal = result.internal_final_verifier_status
    official = result.official_verifier_status
    if internal and official and internal != official:
        return True, f"internal_{internal}_official_{official}"
    return False, None


def _official_execution_status(
    gold_result: Stage16DHealthcheckInputResult | None,
    noop_result: Stage16DHealthcheckInputResult | None,
) -> str:
    statuses = {
        result.official_harness_execution_status
        for result in (gold_result, noop_result)
        if result is not None
    }
    if not statuses:
        return "not_run_in_local_schema_phase"
    if statuses == {"executed"}:
        return "executed"
    return "mixed:" + ",".join(sorted(statuses))


def _overall_status(
    *,
    seed_resolution_status: str,
    gold_healthcheck_status: str,
    noop_healthcheck_status: str,
    official_image_digest_locked: bool,
    proxy_official_disagreement: bool,
    disposition: str,
) -> str:
    if seed_resolution_status != CONCRETE_SEED_STATUS:
        return OVERALL_AGGREGATE_NOT_RUNNABLE
    if gold_healthcheck_status == GOLD_FAILED:
        return GOLD_FAILED
    if noop_healthcheck_status == NOOP_UNEXPECTEDLY_RESOLVED:
        return NOOP_UNEXPECTEDLY_RESOLVED
    if proxy_official_disagreement:
        return OVERALL_PROXY_OFFICIAL_DISAGREEMENT
    if disposition == DISPOSITION_TRAINABLE:
        return OVERALL_VERIFIER_HEALTHY
    if gold_healthcheck_status == GOLD_PASSED and noop_healthcheck_status == NOOP_EXPECTED_UNRESOLVED:
        if not official_image_digest_locked:
            return OVERALL_IMAGE_DIGEST_MISMATCH
    return OVERALL_HEALTHCHECK_NOT_RUN


def _not_run_reason(
    seed_resolution_status: str,
    gold_healthcheck_status: str,
    noop_healthcheck_status: str,
    noop_patch_ref_status: str,
) -> str | None:
    if seed_resolution_status != CONCRETE_SEED_STATUS:
        return "aggregate_seed_not_directly_runnable"
    if gold_healthcheck_status.startswith("not_run"):
        return gold_healthcheck_status
    if noop_patch_ref_status == "not_run_missing_noop_input":
        return noop_patch_ref_status
    if noop_healthcheck_status.startswith("not_run"):
        return noop_healthcheck_status
    return None


def _load_results(path: str | Path | None, *, check_kind: Stage16DCheckKind) -> dict[str, Stage16DHealthcheckInputResult]:
    if path is None:
        return {}
    results: dict[str, Stage16DHealthcheckInputResult] = {}
    for row in _read_jsonl(Path(path)):
        payload = {**row, "check_kind": row.get("check_kind", check_kind)}
        result = Stage16DHealthcheckInputResult.model_validate(payload)
        if result.check_kind != check_kind:
            raise RepoHarnessError(f"Stage 16D {path} 包含错误 check_kind：{result.check_kind}")
        results[result.instance_id] = result
    return results


def _load_proxy_results(path: str | Path | None) -> dict[str, Stage16DProxyResult]:
    if path is None:
        return {}
    results: dict[str, Stage16DProxyResult] = {}
    for row in _read_jsonl(Path(path)):
        result = Stage16DProxyResult.model_validate(row)
        results[result.instance_id] = result
    return results


def _build_summary(
    records: list[Stage16DHealthcheckRecord],
    *,
    stage16d0_commit: str,
    stage16c_commit: str,
    leak_failures: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_stage16d_acceptance_summary_v0",
        "stage": "16D",
        "stage16d0_commit": stage16d0_commit,
        "stage16c_commit": stage16c_commit,
        "runtime_private_evidence_present": True,
        **_derived_summary_from_records(records, leak_failures=leak_failures),
    }


def _derived_summary_from_records(
    records: list[Stage16DHealthcheckRecord],
    *,
    leak_failures: Any,
) -> dict[str, Any]:
    concrete = [record for record in records if record.seed_resolution_status == CONCRETE_SEED_STATUS]
    trainable = [record for record in records if record.healthcheck_training_disposition == DISPOSITION_TRAINABLE]
    positive_path = [record for record in concrete if record.seed_role == "positive_path_official_resolved"]
    risk_seeds = [record for record in concrete if "risk" in record.seed_role]
    positive_gold_pass = sum(1 for record in positive_path if record.gold_healthcheck_status == GOLD_PASSED)
    positive_noop_unresolved = sum(
        1 for record in positive_path if record.noop_healthcheck_status == NOOP_EXPECTED_UNRESOLVED
    )
    positive_trainable = sum(
        1 for record in positive_path if record.healthcheck_training_disposition == DISPOSITION_TRAINABLE
    )
    risk_classified = all(
        record.official_harness_execution_status == "executed"
        and record.gold_healthcheck_status in {GOLD_PASSED, GOLD_FAILED}
        and record.noop_healthcheck_status in {NOOP_EXPECTED_UNRESOLVED, NOOP_UNEXPECTEDLY_RESOLVED}
        and _record_has_stage16d1_binding(record)
        for record in risk_seeds
    )
    normalized_leak_failures = leak_failures if isinstance(leak_failures, list) else []
    official_executed = any(record.official_harness_execution_status != "not_run_in_local_schema_phase" for record in records)
    official_complete = bool(concrete) and all(
        record.gold_healthcheck_status in {GOLD_PASSED, GOLD_FAILED}
        and record.noop_healthcheck_status in {NOOP_EXPECTED_UNRESOLVED, NOOP_UNEXPECTEDLY_RESOLVED}
        and record.official_harness_execution_status == "executed"
        and record.official_image_digest_locked
        and bool(record.official_image_digest and IMAGE_DIGEST_RE.fullmatch(record.official_image_digest))
        and bool(record.gold_official_result_ref and record.gold_official_result_sha256)
        and bool(record.noop_official_result_ref and record.noop_official_result_sha256)
        and _record_has_stage16d1_binding(record)
        for record in concrete
    )
    return {
        "stage16d_complete": official_complete,
        "local_contract_ready": True,
        "official_healthcheck_complete": official_complete,
        "official_harness_execution_status": "executed" if official_executed else "not_run_in_local_schema_phase",
        "remote_healthcheck_required": not official_complete,
        "contract_assert_complete_passed": not normalized_leak_failures,
        "official_healthcheck_assert_complete_passed": official_complete,
        "seed_count": len(records),
        "concrete_seed_count": len(concrete),
        "aggregate_seed_count": len(records) - len(concrete),
        "gold_healthcheck_pass_count": sum(1 for record in records if record.gold_healthcheck_status == GOLD_PASSED),
        "gold_healthcheck_fail_count": sum(1 for record in records if record.gold_healthcheck_status == GOLD_FAILED),
        "noop_healthcheck_expected_unresolved_count": sum(
            1 for record in records if record.noop_healthcheck_status == NOOP_EXPECTED_UNRESOLVED
        ),
        "noop_unexpectedly_resolved_count": sum(
            1 for record in records if record.noop_healthcheck_status == NOOP_UNEXPECTEDLY_RESOLVED
        ),
        "environment_or_oracle_invalid_count": sum(
            1 for record in records if record.healthcheck_training_disposition == DISPOSITION_ENV_OR_ORACLE_INVALID
        ),
        "proxy_official_disagreement_count": sum(1 for record in records if record.proxy_official_disagreement),
        "training_eligible_after_healthcheck_count": len(trainable),
        "stage16d1_selected_positive_path_seed_count": len(positive_path),
        "stage16d1_selected_risk_seed_count": len(risk_seeds),
        "positive_path_gold_healthcheck_pass_count": positive_gold_pass,
        "positive_path_noop_expected_unresolved_count": positive_noop_unresolved,
        "positive_path_trainable_candidate_count": positive_trainable,
        "stage16d1_positive_path_healthcheck_passed": bool(positive_path)
        and positive_gold_pass == len(positive_path)
        and positive_noop_unresolved == len(positive_path)
        and positive_trainable == len(positive_path),
        "stage16d1_risk_seed_classification_complete": risk_classified,
        "public_path_leak_scan_passed": not normalized_leak_failures,
        "hidden_selector_leak_scan_passed": not normalized_leak_failures,
        "patch_content_public_leak_scan_passed": not normalized_leak_failures,
        "public_leak_failures": normalized_leak_failures,
    }


def _write_input_seed_manifest(path: Path, seeds: list[Stage16DSeedRecord], source_sha256: str) -> None:
    seed_payloads = [
        {
            **seed.model_dump(mode="json"),
            "seed_resolution_status": _seed_resolution_status(seed),
        }
        for seed in seeds
    ]
    counts = _seed_projection_counts(seeds)
    _write_json(
        path,
        {
            "schema_version": "repo_harness_stage16d_input_seed_manifest_v0",
            "source_seed_manifest_sha256": source_sha256,
            "seed_instance_ids_sha256": _stable_string_list_sha256([seed.instance_id for seed in seeds]),
            **counts,
            "seeds": seed_payloads,
        },
    )


def _seeds_from_input_manifest(payload: Mapping[str, Any], failures: list[str]) -> list[Stage16DSeedRecord]:
    raw_seeds = payload.get("seeds")
    if not isinstance(raw_seeds, list):
        failures.append("stage16d_input_seed_manifest_missing_seeds")
        return []
    seeds: list[Stage16DSeedRecord] = []
    for index, item in enumerate(raw_seeds):
        try:
            seeds.append(Stage16DSeedRecord.model_validate(_stage16d_seed_public_subset(item)))
        except (RepoHarnessError, ValueError) as exc:
            failures.append(f"invalid_stage16d_input_seed:{index}:{exc}")
    expected_counts = _seed_projection_counts(seeds)
    for field, expected_value in expected_counts.items():
        if payload.get(field) != expected_value:
            failures.append(f"stage16d_input_seed_manifest_count_mismatch:{field}")
    expected_digest = _stable_string_list_sha256([seed.instance_id for seed in seeds])
    if payload.get("seed_instance_ids_sha256") != expected_digest:
        failures.append("stage16d_input_seed_manifest_instance_digest_mismatch")
    if not isinstance(payload.get("source_seed_manifest_sha256"), str) or not SHA256_HEX_RE.fullmatch(
        payload.get("source_seed_manifest_sha256", "")
    ):
        failures.append("stage16d_input_seed_manifest_missing_source_sha256")
    return seeds


def _validate_seed_manifest_binding(
    seed_records: list[Stage16DSeedRecord],
    records: list[Stage16DHealthcheckRecord],
) -> list[str]:
    failures: list[str] = []
    seed_by_id = {seed.instance_id: seed for seed in seed_records}
    record_by_id = {record.instance_id: record for record in records}
    seed_ids = set(seed_by_id)
    record_ids = set(record_by_id)
    for missing in sorted(seed_ids - record_ids):
        failures.append(f"stage16d_healthcheck_missing_seed_record:{missing}")
    for extra in sorted(record_ids - seed_ids):
        failures.append(f"stage16d_healthcheck_extra_record_not_in_seed_manifest:{extra}")
    for instance_id in sorted(seed_ids & record_ids):
        seed = seed_by_id[instance_id]
        record = record_by_id[instance_id]
        if seed.seed_role != record.seed_role:
            failures.append(f"stage16d_seed_role_mismatch:{instance_id}")
        if seed.official_validation_backend != record.official_validation_backend:
            failures.append(f"stage16d_official_backend_mismatch:{instance_id}")
        if _seed_resolution_status(seed) != record.seed_resolution_status:
            failures.append(f"stage16d_seed_resolution_status_mismatch:{instance_id}")
    return failures


def _validate_stage16d_report_instance_sets(root: Path, seed_records: list[Stage16DSeedRecord]) -> list[str]:
    expected = {seed.instance_id for seed in seed_records}
    failures: list[str] = []
    for artifact in (
        "stage16d_seed_resolution_report.json",
        "stage16d_gold_healthcheck_report.json",
        "stage16d_noop_healthcheck_report.json",
        "stage16d_proxy_official_disagreement_report.json",
        "stage16d_training_disposition_report.json",
    ):
        path = root / artifact
        if not path.is_file():
            continue
        try:
            payload = _read_json(path)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            failures.append(f"invalid_stage16d_report_json:{artifact}:{exc}")
            continue
        ids = _record_instance_ids(payload, artifact, failures)
        if ids != expected:
            missing = sorted(expected - ids)
            extra = sorted(ids - expected)
            if missing:
                failures.append(f"stage16d_report_missing_seed_records:{artifact}:{','.join(missing)}")
            if extra:
                failures.append(f"stage16d_report_extra_records:{artifact}:{','.join(extra)}")
    return failures


def _record_instance_ids(payload: Mapping[str, Any], artifact: str, failures: list[str]) -> set[str]:
    rows = payload.get("records")
    if not isinstance(rows, list):
        failures.append(f"stage16d_report_missing_records:{artifact}")
        return set()
    ids: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or not isinstance(row.get("instance_id"), str):
            failures.append(f"stage16d_report_invalid_record:{artifact}:{index}")
            continue
        ids.append(row["instance_id"])
    duplicates = sorted({instance_id for instance_id in ids if ids.count(instance_id) > 1})
    for duplicate in duplicates:
        failures.append(f"stage16d_report_duplicate_record:{artifact}:{duplicate}")
    return set(ids)


def _seed_projection_counts(seeds: list[Stage16DSeedRecord]) -> dict[str, int]:
    concrete = [seed for seed in seeds if _seed_resolution_status(seed) == CONCRETE_SEED_STATUS]
    return {
        "seed_count": len(seeds),
        "concrete_seed_count": len(concrete),
        "aggregate_seed_count": len(seeds) - len(concrete),
    }


def _validate_stage16d_records(records: list[Stage16DHealthcheckRecord]) -> list[str]:
    failures: list[str] = []
    seen: set[str] = set()
    for record in records:
        if record.instance_id in seen:
            failures.append(f"duplicate_stage16d_record:{record.instance_id}")
        seen.add(record.instance_id)
        if record.seed_resolution_status == AGGREGATE_SEED_STATUS and record.healthcheck_training_disposition == DISPOSITION_TRAINABLE:
            failures.append(f"aggregate_seed_marked_trainable:{record.instance_id}")
        if record.healthcheck_training_disposition == DISPOSITION_TRAINABLE:
            if record.gold_healthcheck_status != GOLD_PASSED:
                failures.append(f"trainable_without_gold_passed:{record.instance_id}")
            if record.noop_healthcheck_status != NOOP_EXPECTED_UNRESOLVED:
                failures.append(f"trainable_without_noop_expected_unresolved:{record.instance_id}")
            if not record.official_image_digest_locked:
                failures.append(f"trainable_without_official_image_digest_locked:{record.instance_id}")
            if not (record.gold_official_result_ref and record.gold_official_result_sha256):
                failures.append(f"trainable_without_gold_official_result_artifact:{record.instance_id}")
            if not (record.noop_official_result_ref and record.noop_official_result_sha256):
                failures.append(f"trainable_without_noop_official_result_artifact:{record.instance_id}")
        if record.gold_healthcheck_status == GOLD_FAILED and record.healthcheck_training_disposition == DISPOSITION_TRAINABLE:
            failures.append(f"gold_failed_marked_trainable:{record.instance_id}")
        if record.noop_healthcheck_status == NOOP_UNEXPECTEDLY_RESOLVED and record.healthcheck_training_disposition == DISPOSITION_TRAINABLE:
            failures.append(f"noop_resolved_marked_trainable:{record.instance_id}")
        if record.proxy_official_disagreement and record.healthcheck_training_disposition == DISPOSITION_TRAINABLE:
            failures.append(f"proxy_official_disagreement_marked_trainable:{record.instance_id}")
    return failures


def _validate_stage16d_summary(
    summary: Mapping[str, Any],
    records: list[Stage16DHealthcheckRecord],
    seed_records: list[Stage16DSeedRecord],
) -> list[str]:
    failures: list[str] = []
    required = (
        "stage16d_complete",
        "local_contract_ready",
        "official_healthcheck_complete",
        "official_harness_execution_status",
        "remote_healthcheck_required",
        "contract_assert_complete_passed",
        "official_healthcheck_assert_complete_passed",
    )
    for field in required:
        if field not in summary:
            failures.append(f"stage16d_summary_missing:{field}")
    if summary.get("stage") != "16D":
        failures.append("stage16d_summary_stage_mismatch")
    if summary.get("seed_count") != len(records):
        failures.append("stage16d_summary_seed_count_mismatch")
    if seed_records:
        seed_counts = _seed_projection_counts(seed_records)
        for field, expected_value in seed_counts.items():
            if summary.get(field) != expected_value:
                failures.append(f"stage16d_summary_input_seed_field_mismatch:{field}")
    expected = _derived_summary_from_records(records, leak_failures=summary.get("public_leak_failures", []))
    for field, expected_value in expected.items():
        if summary.get(field) != expected_value:
            failures.append(f"stage16d_summary_derived_field_mismatch:{field}")
    return failures


def _assert_contract_complete(
    summary: Mapping[str, Any],
    records: list[Stage16DHealthcheckRecord],
    seed_records: list[Stage16DSeedRecord],
) -> list[str]:
    failures: list[str] = []
    if not summary:
        return ["missing_stage16d_acceptance_summary"]
    if summary.get("local_contract_ready") is not True:
        failures.append("stage16d_local_contract_ready_not_true")
    if summary.get("contract_assert_complete_passed") is not True:
        failures.append("stage16d_contract_assert_complete_passed_not_true")
    if summary.get("public_path_leak_scan_passed") is not True:
        failures.append("stage16d_public_path_leak_scan_not_passed")
    if not records:
        failures.append("stage16d_healthcheck_manifest_has_no_records")
    if not seed_records:
        failures.append("stage16d_input_seed_manifest_has_no_records")
    for record in records:
        if record.seed_resolution_status == CONCRETE_SEED_STATUS:
            if not record.gold_healthcheck_status:
                failures.append(f"missing_gold_healthcheck_record:{record.instance_id}")
            if not record.noop_healthcheck_status:
                failures.append(f"missing_noop_healthcheck_record:{record.instance_id}")
            if record.not_run_reason and record.healthcheck_training_disposition == DISPOSITION_TRAINABLE:
                failures.append(f"not_run_record_marked_trainable:{record.instance_id}")
    return failures


def _assert_official_complete(
    summary: Mapping[str, Any],
    records: list[Stage16DHealthcheckRecord],
) -> list[str]:
    failures: list[str] = []
    if not summary:
        return ["missing_stage16d_acceptance_summary"]
    if summary.get("official_healthcheck_complete") is not True:
        failures.append("stage16d_official_healthcheck_complete_not_true")
    if summary.get("official_healthcheck_assert_complete_passed") is not True:
        failures.append("stage16d_official_healthcheck_assert_complete_passed_not_true")
    if summary.get("stage16d1_positive_path_healthcheck_passed") is not True:
        failures.append("stage16d1_positive_path_healthcheck_not_passed")
    if summary.get("stage16d1_selected_positive_path_seed_count", 0) < 1:
        failures.append("stage16d1_missing_positive_path_seed")
    if summary.get("positive_path_gold_healthcheck_pass_count", 0) < summary.get(
        "stage16d1_selected_positive_path_seed_count", 0
    ):
        failures.append("stage16d1_positive_path_gold_pass_count_insufficient")
    if summary.get("positive_path_noop_expected_unresolved_count", 0) < summary.get(
        "stage16d1_selected_positive_path_seed_count", 0
    ):
        failures.append("stage16d1_positive_path_noop_unresolved_count_insufficient")
    for record in records:
        if record.seed_resolution_status != CONCRETE_SEED_STATUS:
            continue
        if record.not_run_reason:
            failures.append(f"official_complete_contains_not_run_concrete_seed:{record.instance_id}")
        if not record.official_image_digest_locked:
            failures.append(f"official_complete_missing_image_digest_lock:{record.instance_id}")
        if record.official_harness_execution_status != "executed":
            failures.append(f"official_complete_status_not_executed:{record.instance_id}")
        if not record.official_image_digest or not IMAGE_DIGEST_RE.fullmatch(record.official_image_digest):
            failures.append(f"official_complete_invalid_image_digest:{record.instance_id}")
        if not (record.gold_official_result_ref and record.gold_official_result_sha256):
            failures.append(f"official_complete_missing_gold_result_artifact:{record.instance_id}")
        if not (record.noop_official_result_ref and record.noop_official_result_sha256):
            failures.append(f"official_complete_missing_noop_result_artifact:{record.instance_id}")
        failures.extend(_official_complete_stage16d1_binding_failures(record))
        if record.gold_healthcheck_status not in {GOLD_PASSED, GOLD_FAILED}:
            failures.append(f"official_complete_missing_gold_result:{record.instance_id}")
        if record.noop_healthcheck_status not in {NOOP_EXPECTED_UNRESOLVED, NOOP_UNEXPECTEDLY_RESOLVED}:
            failures.append(f"official_complete_missing_noop_result:{record.instance_id}")
    return failures


def _records_from_manifest(
    manifest: Mapping[str, Any],
    failures: list[str],
) -> list[Stage16DHealthcheckRecord]:
    raw_records = manifest.get("records")
    if not isinstance(raw_records, list):
        failures.append("stage16d_healthcheck_manifest_missing_records")
        return []
    records: list[Stage16DHealthcheckRecord] = []
    for index, item in enumerate(raw_records):
        try:
            records.append(Stage16DHealthcheckRecord.model_validate(item))
        except ValueError as exc:
            failures.append(f"invalid_stage16d_healthcheck_record:{index}:{exc}")
    return records


def _load_optional_json(path: Path, failures: list[str]) -> dict[str, Any]:
    if not path.is_file():
        failures.append(f"missing_stage16d_artifact:{path.name}")
        return {}
    try:
        payload = _read_json(path)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        failures.append(f"invalid_stage16d_json:{path.name}:{exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"stage16d_json_not_object:{path.name}")
        return {}
    return payload


def _iter_public_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith("runtime_private/"):
            continue
        if path.suffix in PUBLIC_SCAN_SUFFIXES:
            yield path


def _normalize_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise RepoHarnessError(f"不安全的 Stage 16D 相对路径：{value}")
    return path.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_string_list_sha256(values: list[str]) -> str:
    payload = json.dumps(sorted(values), separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _validate_runtime_private_ref_digest_pair(
    ref: str | None,
    digest: str | None,
    label: str,
    *,
    expected_kind: str,
) -> None:
    if not ref or not is_opaque_runtime_private_ref(ref):
        raise ValueError(f"executed healthcheck result requires runtime-private {label}_ref")
    if _runtime_private_ref_kind(ref) != expected_kind:
        raise ValueError(f"{label} ref kind must be {expected_kind}")
    if not digest or not SHA256_HEX_RE.fullmatch(digest):
        raise ValueError(f"executed healthcheck result requires {label}_sha256")
    if _runtime_private_ref_digest(ref) != digest:
        raise ValueError(f"{label} ref digest must match sha256")


def _execution_environment_locked_for_instance(
    instance_id: str,
    execution_image_digest_by_instance: Mapping[str, str],
    lock_method: str | None,
) -> bool:
    if instance_id in execution_image_digest_by_instance:
        return bool(IMAGE_DIGEST_RE.fullmatch(execution_image_digest_by_instance[instance_id]))
    return lock_method == "single_layer_environment_digest"


def _stage16d1_required_ref_digest_pairs(
    record: Stage16DHealthcheckRecord,
) -> tuple[tuple[str, str, str | None, str | None], ...]:
    return (
        (
            "gold_official_result",
            "official-result",
            record.gold_official_result_ref,
            record.gold_official_result_sha256,
        ),
        (
            "noop_official_result",
            "official-result",
            record.noop_official_result_ref,
            record.noop_official_result_sha256,
        ),
        (
            "selected_dataset_rows",
            "selected-dataset-rows",
            record.selected_dataset_rows_ref,
            record.selected_dataset_rows_sha256,
        ),
        ("gold_predictions", "gold-predictions", record.gold_predictions_ref, record.gold_predictions_sha256),
        ("noop_predictions", "noop-predictions", record.noop_predictions_ref, record.noop_predictions_sha256),
        ("gold_official_command", "official-command", record.gold_official_command_ref, record.gold_official_command_sha256),
        ("noop_official_command", "official-command", record.noop_official_command_ref, record.noop_official_command_sha256),
    )


def _matching_field(
    gold_result: Stage16DHealthcheckInputResult | None,
    noop_result: Stage16DHealthcheckInputResult | None,
    field: str,
) -> str | None:
    values = [getattr(result, field) for result in (gold_result, noop_result) if result is not None]
    present = [value for value in values if value]
    if not present:
        return None
    return present[0] if all(value == present[0] for value in present) else None


def _matching_mapping(
    gold_result: Stage16DHealthcheckInputResult | None,
    noop_result: Stage16DHealthcheckInputResult | None,
    field: str,
) -> dict[str, str]:
    values = [getattr(result, field) for result in (gold_result, noop_result) if result is not None]
    present = [value for value in values if value]
    if not present:
        return {}
    return dict(present[0]) if all(value == present[0] for value in present) else {}


def _official_image_digest_pair_locked(*results: Stage16DHealthcheckInputResult | None) -> bool:
    present = [result for result in results if result is not None]
    if not present:
        return False
    digests = {result.official_image_digest for result in present if result.official_image_digest}
    if len(digests) != 1:
        return False
    if not all(result.official_image_digest_locked for result in present):
        return False
    shared_fields = (
        "selected_dataset_rows_ref",
        "selected_dataset_rows_sha256",
        "selected_instance_row_sha256",
        "runner_digest",
        "runner_digest_method",
        "official_environment_digest_lock_method",
    )
    for field in shared_fields:
        values = [getattr(result, field) for result in present]
        if not all(values) or len(set(values)) != 1:
            return False
    if len({json.dumps(result.execution_image_digest_by_instance, sort_keys=True) for result in present}) != 1:
        return False
    return all(
        _execution_environment_locked_for_instance(
            result.instance_id,
            result.execution_image_digest_by_instance,
            result.official_environment_digest_lock_method,
        )
        for result in present
    )


def _stage16d_seed_public_subset(seed: Any) -> dict[str, Any]:
    if not isinstance(seed, Mapping):
        raise RepoHarnessError("Stage 16D seed manifest 包含非 object seed。")
    fields = (
        "instance_id",
        "seed_role",
        "source_dataset",
        "candidate_instance_status",
        "gold_patch_source",
        "noop_patch_source",
        "source_evidence_ref",
        "source_doc_sha256",
        "stage16d_execution_precondition",
        "official_validation_backend",
    )
    return {field: seed.get(field) for field in fields if field in seed}


def _runtime_private_artifact_ref(path: Path) -> str:
    digest = _sha256_file(path)
    kind = path.name.replace(".", "-").replace("_", "-")
    return f"runtime-private:{kind}:{digest}"


def _runtime_private_ref_digest(ref: str) -> str:
    return ref.rsplit(":", 1)[-1]


def _runtime_private_ref_kind(ref: str) -> str:
    parts = ref.split(":")
    return parts[1] if len(parts) == 3 else ""


__all__ = [
    "CANONICAL_EMPTY_PATCH_REF",
    "NOOP_EXPECTED_UNRESOLVED",
    "Stage16DArtifactBuildResult",
    "Stage16DHealthcheckInputResult",
    "Stage16DHealthcheckInspectReport",
    "Stage16DHealthcheckRecord",
    "Stage16DProxyResult",
    "Stage16DSeedRecord",
    "build_stage16d_healthcheck_artifacts",
    "classify_stage16d_seed",
    "compute_stage16d_training_disposition",
    "inspect_stage16d_healthcheck",
    "inspect_stage16d_healthcheck_report",
    "is_opaque_runtime_private_ref",
    "load_stage16d_seed_manifest",
    "scan_stage16d_public_evidence",
]
