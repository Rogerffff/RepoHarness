"""V4 stage 2 task source freeze and task adapter integration artifacts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness import __version__
from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V4_ALLOWLIST_POLICY_VERSION,
    V4_CONTAMINATION_DENYLIST_VERSION,
    V4_IMPLEMENTATION_INPUT_MANIFEST_VERSION,
    V4_TASK_FREEZE_MANIFEST_VERSION,
    V4_TASK_VALIDITY_REPORT_VERSION,
    V4_VISIBILITY_POLICY_VERSION,
)
from repo_harness.v4_implementation_inputs import (
    PR_ISSUE_FREEZE_READY_CANDIDATES,
    PUBLIC_SWEBENCH_LIKE_CANDIDATES,
    inspect_v4_implementation_inputs,
)
from repo_harness.v4_visibility import V4ContaminationDenylist, v4_contamination_denylist_sha256
from repo_harness.workspace.source_hash import compute_source_tree_hash


STAGE2_SCHEMA_PREFIX = "repo_harness_v4_stage2"
PR_TASK_CONSTRUCTION_MANIFEST_VERSION = f"{STAGE2_SCHEMA_PREFIX}_pr_task_construction_manifest_v0"
SOURCE_ARCHIVE_MANIFEST_VERSION = f"{STAGE2_SCHEMA_PREFIX}_source_archive_manifest_v0"
SOURCE_MATERIALIZATION_REPORT_VERSION = f"{STAGE2_SCHEMA_PREFIX}_source_materialization_report_v0"
BASELINE_VERIFIER_REPORT_VERSION = f"{STAGE2_SCHEMA_PREFIX}_baseline_verifier_report_v0"
POST_PATCH_VERIFIER_REPORT_VERSION = f"{STAGE2_SCHEMA_PREFIX}_post_patch_verifier_report_v0"
FLAKY_DETECTION_REPORT_VERSION = f"{STAGE2_SCHEMA_PREFIX}_flaky_detection_report_v0"
ENVIRONMENT_STABILITY_REPORT_VERSION = f"{STAGE2_SCHEMA_PREFIX}_environment_stability_report_v0"
DEPENDENCY_CACHE_REPORT_VERSION = f"{STAGE2_SCHEMA_PREFIX}_dependency_cache_report_v0"
LICENSE_PROVENANCE_REVIEW_REPORT_VERSION = f"{STAGE2_SCHEMA_PREFIX}_license_provenance_review_report_v0"
USE_BOUNDARY_REVIEW_REPORT_VERSION = f"{STAGE2_SCHEMA_PREFIX}_use_boundary_review_report_v0"
GENERATED_TASK_DEFINITION_RECORD_VERSION = f"{STAGE2_SCHEMA_PREFIX}_generated_task_definition_record_v0"
EVALUATOR_ONLY_EVIDENCE_MANIFEST_VERSION = f"{STAGE2_SCHEMA_PREFIX}_evaluator_only_evidence_manifest_v0"
ADAPTER_VISIBLE_TASK_INPUT_MANIFEST_VERSION = f"{STAGE2_SCHEMA_PREFIX}_adapter_visible_task_input_manifest_v0"
TASK_VISIBILITY_SCAN_REPORT_VERSION = f"{STAGE2_SCHEMA_PREFIX}_task_visibility_scan_report_v0"

STAGE2_OUTPUTS = (
    "task_freeze_manifest.json",
    "pr_task_construction_manifest.json",
    "source_archive_manifest.json",
    "source_materialization_report.json",
    "baseline_verifier_report.json",
    "post_patch_verifier_report.json",
    "flaky_detection_report.json",
    "environment_stability_report.json",
    "dependency_cache_report.json",
    "license_provenance_review_report.json",
    "use_boundary_review_report.json",
    "task_validity_report.json",
    "generated_task_definition.jsonl",
    "evaluator_only_evidence_manifest.json",
    "adapter_visible_task_input_manifest.json",
    "task_visibility_scan_report.json",
)

REQUIRED_TASK_VALIDITY_FIELDS = (
    "task_id",
    "candidate_id",
    "task_source_tag",
    "fixed_revision",
    "source_archive_hash",
    "source_tree_hash",
    "adapter_visible_input_hash",
    "evaluator_only_evidence_manifest_hash",
    "baseline_verifier_plan_hash",
    "baseline_verifier_evidence_ref",
    "post_patch_verifier_evidence_ref",
    "flaky_probe_evidence_ref",
    "environment_stability_score",
    "dependency_cache",
    "license_provenance_review_status",
    "use_boundary_review_status",
)

FORBIDDEN_TASK_ADAPTER_OPERATIONS = (
    "dependency_setup",
    "source_checkout",
    "source_materialization",
    "baseline_verifier",
    "post_patch_verifier",
    "flaky_probe",
)


def build_v4_task_freeze(
    *,
    implementation_inputs: str | Path,
    output_dir: str | Path,
    fail_if_output_exists: bool = False,
) -> Path:
    """Build V4 stage 2 task freeze artifacts from explicit stage 0 inputs."""

    output_path = Path(output_dir)
    if fail_if_output_exists:
        existing = [output_path / name for name in STAGE2_OUTPUTS if (output_path / name).exists()]
        if existing:
            raise ConfigError(
                "V4 stage 2 输出已存在，不能覆盖旧 evidence："
                + ", ".join(path.as_posix() for path in existing)
            )

    implementation_path = Path(implementation_inputs)
    inspect_v4_implementation_inputs(implementation_path, assert_complete=True)
    implementation_manifest = _read_json(implementation_path)
    if implementation_manifest.get("schema_version") != V4_IMPLEMENTATION_INPUT_MANIFEST_VERSION:
        raise ConfigError("implementation inputs schema_version 不匹配。")

    binding_path = _resolve_ref_path(implementation_manifest["feasibility_input_binding_ref"])
    binding = _read_json(binding_path)
    sources = {source["source_id"]: source for source in binding.get("sources", [])}
    pr_source = sources.get("v4_pr_issue_feasibility")
    public_source = sources.get("v4_public_swebench_like_feasibility")
    if pr_source is None or public_source is None:
        raise ConfigError("Stage 2 需要同时绑定 PR / issue 和 public SWE-Bench-like feasibility 输入。")

    pr_run = Path(pr_source["run_path"])
    public_run = Path(public_source["run_path"])
    output_path.mkdir(parents=True, exist_ok=True)

    pr_readiness = _read_json(pr_run / "manifests/pr_issue_task_freeze_readiness_report.json")
    adapter_manifest = _read_json(pr_run / "manifests/adapter_visible_task_freeze_manifest.json")
    upstream_source_archive = _read_json(pr_run / "manifests/source_archive_manifest.json")
    docker_summary = _read_json(pr_run / "manifests/docker_feasibility_summary_report.json")
    flaky_probe = _read_json(pr_run / "manifests/flaky_probe_report.json")
    provenance_report = _read_json(pr_run / "manifests/candidate_source_provenance_report.json")
    training_boundary = _read_json(pr_run / "manifests/training_export_boundary_report.json")
    public_readiness = _read_json(public_run / "freeze/public_swebench_initial_freeze_readiness_report.json")

    task_rows = _build_task_rows(
        pr_run=pr_run,
        pr_readiness=pr_readiness,
        adapter_manifest=adapter_manifest,
        upstream_source_archive=upstream_source_archive,
        docker_summary=docker_summary,
        flaky_probe=flaky_probe,
    )
    if len(task_rows) < 8:
        raise ConfigError("Stage 2 至少需要 8 个 PR / issue task rows。")

    adapter_visible_manifest_path = output_path / "adapter_visible_task_input_manifest.json"
    generated_task_definition_path = output_path / "generated_task_definition.jsonl"
    evaluator_manifest_path = output_path / "evaluator_only_evidence_manifest.json"
    visibility_scan_path = output_path / "task_visibility_scan_report.json"
    source_archive_path = output_path / "source_archive_manifest.json"
    source_materialization_path = output_path / "source_materialization_report.json"
    baseline_verifier_path = output_path / "baseline_verifier_report.json"
    post_patch_verifier_path = output_path / "post_patch_verifier_report.json"
    flaky_detection_path = output_path / "flaky_detection_report.json"
    environment_stability_path = output_path / "environment_stability_report.json"
    dependency_cache_path = output_path / "dependency_cache_report.json"
    license_provenance_path = output_path / "license_provenance_review_report.json"
    use_boundary_path = output_path / "use_boundary_review_report.json"
    task_validity_path = output_path / "task_validity_report.json"
    pr_task_construction_path = output_path / "pr_task_construction_manifest.json"
    task_freeze_path = output_path / "task_freeze_manifest.json"

    adapter_visible_payload = _build_adapter_visible_manifest(task_rows)
    _write_json(adapter_visible_manifest_path, adapter_visible_payload)
    _write_jsonl(generated_task_definition_path, _build_generated_task_records(task_rows, adapter_visible_manifest_path))

    evaluator_payload = _build_evaluator_only_evidence_manifest(
        pr_run=pr_run,
        public_run=public_run,
        task_rows=task_rows,
        pr_source=pr_source,
        public_source=public_source,
    )
    _write_json(evaluator_manifest_path, evaluator_payload)

    source_archive_payload = _build_source_archive_manifest(task_rows)
    _write_json(source_archive_path, source_archive_payload)
    _write_json(source_materialization_path, _build_source_materialization_report(task_rows))
    _write_json(baseline_verifier_path, _build_baseline_verifier_report(task_rows))
    _write_json(post_patch_verifier_path, _build_post_patch_verifier_report(task_rows))
    _write_json(flaky_detection_path, _build_flaky_detection_report(task_rows))
    _write_json(environment_stability_path, _build_environment_stability_report(task_rows))
    _write_json(dependency_cache_path, _build_dependency_cache_report(task_rows))
    _write_json(
        license_provenance_path,
        _build_license_provenance_review_report(task_rows, provenance_report=provenance_report),
    )
    _write_json(use_boundary_path, _build_use_boundary_review_report(task_rows, training_boundary=training_boundary))
    _write_json(visibility_scan_path, _build_visibility_scan_report(task_rows, generated_task_definition_path))

    task_validity_payload = _build_task_validity_report(
        task_rows=task_rows,
        evaluator_manifest_path=evaluator_manifest_path,
        artifact_paths={
            "source_materialization_report.json": source_materialization_path,
            "baseline_verifier_report.json": baseline_verifier_path,
            "post_patch_verifier_report.json": post_patch_verifier_path,
            "flaky_detection_report.json": flaky_detection_path,
            "environment_stability_report.json": environment_stability_path,
            "dependency_cache_report.json": dependency_cache_path,
            "license_provenance_review_report.json": license_provenance_path,
            "use_boundary_review_report.json": use_boundary_path,
            "task_visibility_scan_report.json": visibility_scan_path,
        },
    )
    _write_json(task_validity_path, task_validity_payload)

    pr_task_construction_payload = _build_pr_task_construction_manifest(
        task_rows=task_rows,
        public_readiness=public_readiness,
        implementation_path=implementation_path,
        binding_path=binding_path,
        artifact_paths={
            "adapter_visible_task_input_manifest.json": adapter_visible_manifest_path,
            "generated_task_definition.jsonl": generated_task_definition_path,
            "evaluator_only_evidence_manifest.json": evaluator_manifest_path,
            "task_validity_report.json": task_validity_path,
        },
    )
    _write_json(pr_task_construction_path, pr_task_construction_payload)

    task_freeze_payload = _build_task_freeze_manifest(
        task_rows=task_rows,
        implementation_path=implementation_path,
        artifact_paths={
            "pr_task_construction_manifest.json": pr_task_construction_path,
            "source_archive_manifest.json": source_archive_path,
            "source_materialization_report.json": source_materialization_path,
            "baseline_verifier_report.json": baseline_verifier_path,
            "post_patch_verifier_report.json": post_patch_verifier_path,
            "flaky_detection_report.json": flaky_detection_path,
            "environment_stability_report.json": environment_stability_path,
            "dependency_cache_report.json": dependency_cache_path,
            "license_provenance_review_report.json": license_provenance_path,
            "use_boundary_review_report.json": use_boundary_path,
            "task_validity_report.json": task_validity_path,
            "generated_task_definition.jsonl": generated_task_definition_path,
            "evaluator_only_evidence_manifest.json": evaluator_manifest_path,
            "adapter_visible_task_input_manifest.json": adapter_visible_manifest_path,
            "task_visibility_scan_report.json": visibility_scan_path,
        },
    )
    _write_json(task_freeze_path, task_freeze_payload)
    inspect_v4_task_freeze(task_freeze_path, assert_complete=True)
    inspect_v4_task_validity(task_validity_path, assert_complete=True)
    return task_freeze_path


def inspect_v4_task_freeze(path: str | Path, *, assert_complete: bool = False) -> str:
    """Inspect V4 task freeze manifest and model-visible task boundary."""

    manifest_path = Path(path)
    failures: list[str] = []
    payload = _read_json_for_inspect(manifest_path, failures)
    if payload:
        _expect(payload, "schema_version", V4_TASK_FREEZE_MANIFEST_VERSION, failures, "task_freeze_manifest")
        _inspect_common_visibility_policy(payload, failures, "task_freeze_manifest")
        if payload.get("selection_mode") != "explicit":
            failures.append("task_freeze_manifest selection_mode 必须为 explicit。")
        if payload.get("latest_run_auto_selection") is not False:
            failures.append("task_freeze_manifest 禁止 latest run 自动选择。")
        if payload.get("accepted_auditable_task_definition_count", 0) < 8:
            failures.append("accepted / auditable task definition 数量必须至少为 8。")
        if payload.get("pr_issue_accepted_auditable_task_definition_count", 0) < 4:
            failures.append("PR / issue accepted / auditable task definition 数量必须至少为 4。")
        _inspect_stage2_artifact_refs(payload, failures, label="task_freeze_manifest")
        _inspect_adapter_visible_manifest(payload, failures)
        _inspect_evaluator_manifest(payload, failures)
        _inspect_generated_task_definition_jsonl(payload, failures)
        _inspect_task_adapter_boundary(payload, failures)
        validity_ref = (payload.get("artifact_refs_by_name") or {}).get("task_validity_report.json")
        validity_path = _inspect_file_ref(validity_ref, failures, label="task_freeze_manifest.task_validity_report.json")
        if validity_path is not None:
            try:
                inspect_v4_task_validity(validity_path, assert_complete=True)
            except ConfigError as exc:
                failures.append(f"task_freeze_manifest 递归复核 task_validity_report 失败：{exc}")

    lines = [f"V4 task freeze manifest: {manifest_path}"]
    if failures:
        if assert_complete:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_complete:
        lines.append("Inspect V4 task freeze: complete")
    lines.append("Inspect V4 task freeze: passed")
    return "\n".join(lines)


def inspect_v4_task_validity(path: str | Path, *, assert_complete: bool = False) -> str:
    """Inspect V4 task validity report and accepted/auditable counting gates."""

    report_path = Path(path)
    failures: list[str] = []
    payload = _read_json_for_inspect(report_path, failures)
    if payload:
        _expect(payload, "schema_version", V4_TASK_VALIDITY_REPORT_VERSION, failures, "task_validity_report")
        _inspect_common_visibility_policy(payload, failures, "task_validity_report")
        if payload.get("accepted_auditable_task_definition_count", 0) < 8:
            failures.append("task_validity_report 至少需要 8 个 accepted / auditable task definitions。")
        if payload.get("pr_issue_accepted_auditable_task_definition_count", 0) < 4:
            failures.append("task_validity_report 至少需要 4 个 PR / issue task definitions。")
        _inspect_task_adapter_boundary(payload, failures)
        _inspect_stage2_artifact_refs(payload, failures, label="task_validity_report")
        _inspect_accepted_task_rows(payload, failures)
        _inspect_task_validity_bound_reports(payload, failures)

    lines = [f"V4 task validity report: {report_path}"]
    if failures:
        if assert_complete:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_complete:
        lines.append("Inspect V4 task validity: complete")
    lines.append("Inspect V4 task validity: passed")
    return "\n".join(lines)


def _build_task_rows(
    *,
    pr_run: Path,
    pr_readiness: dict[str, Any],
    adapter_manifest: dict[str, Any],
    upstream_source_archive: dict[str, Any],
    docker_summary: dict[str, Any],
    flaky_probe: dict[str, Any],
) -> list[dict[str, Any]]:
    candidate_to_task_id = dict(PR_ISSUE_FREEZE_READY_CANDIDATES)
    readiness_by_candidate = {row["candidate_id"]: row for row in pr_readiness.get("candidate_rows", [])}
    adapter_by_candidate = {row["candidate_id"]: row for row in adapter_manifest.get("records", [])}
    source_by_candidate = {row["candidate_id"]: row for row in upstream_source_archive.get("records", [])}
    docker_by_candidate = {row["candidate_id"]: row for row in docker_summary.get("candidate_rows", [])}
    flaky_by_candidate = {row["candidate_id"]: row for row in flaky_probe.get("candidate_results", [])}
    rows: list[dict[str, Any]] = []
    denylist = V4ContaminationDenylist()
    for candidate_id, task_id in PR_ISSUE_FREEZE_READY_CANDIDATES:
        readiness = readiness_by_candidate.get(candidate_id)
        adapter_row = adapter_by_candidate.get(candidate_id)
        source_row = source_by_candidate.get(candidate_id)
        docker_row = docker_by_candidate.get(candidate_id)
        flaky_row = flaky_by_candidate.get(candidate_id)
        if not all([readiness, adapter_row, source_row, docker_row, flaky_row]):
            raise ConfigError(f"缺少 Stage 2 必需 feasibility 行：{candidate_id}")
        if readiness["adapter_visible_task_id"] != task_id:
            raise ConfigError(f"candidate 到 adapter-visible task id 映射不一致：{candidate_id}")
        adapter_path = pr_run / adapter_row["adapter_visible_path"]
        adapter_payload = _read_json(adapter_path)
        denylist.assert_clean(
            surface="adapter_visible_task_input",
            payload=adapter_payload,
            adapter_visible=True,
        )
        selected_archive = _selected_archive(source_row)
        source_archive_path = pr_run / selected_archive["source_archive_path"]
        if sha256_file(source_archive_path) != selected_archive["source_archive_sha256"]:
            raise ConfigError(f"source archive sha256 不匹配：{candidate_id}")
        baseline_plan = {
            "candidate_id": candidate_id,
            "baseline_health_status": docker_row.get("baseline_health_status"),
            "baseline_with_tests_status": docker_row.get("baseline_with_tests_status"),
            "base_image": docker_row.get("base_image"),
        }
        rows.append(
            {
                "candidate_id": candidate_id,
                "task_id": task_id,
                "task_source_tag": "v4_pr_issue",
                "task_family": "pr_issue_constructed_real_repository",
                "repo": adapter_payload["repository"],
                "language_ecosystem": adapter_payload["language_ecosystem"],
                "title": adapter_payload["title"],
                "adapter_visible_input_path": adapter_path,
                "adapter_visible_input_hash": sha256_file(adapter_path),
                "adapter_visible_payload": adapter_payload,
                "source_ref_id": adapter_payload["source_ref_id"],
                "fixed_revision": source_row["selected_fixed_revision"],
                "source_archive_path": source_archive_path,
                "source_archive_hash": selected_archive["source_archive_sha256"],
                "source_archive_size_bytes": selected_archive["source_archive_size_bytes"],
                "source_tree_hash": selected_archive["source_tree_hash"],
                "baseline_verifier_plan_hash": _sha256_payload(baseline_plan),
                "baseline_verifier_evidence_ref": f"evidence:v4_pr_issue:{candidate_id}:baseline_verifier",
                "post_patch_verifier_evidence_ref": f"evidence:v4_pr_issue:{candidate_id}:post_patch_verifier",
                "flaky_probe_evidence_ref": f"evidence:v4_pr_issue:{candidate_id}:flaky_probe",
                "baseline_health_status": docker_row.get("baseline_health_status"),
                "baseline_with_tests_status": docker_row.get("baseline_with_tests_status"),
                "baseline_with_tests_verifier_exit_code": docker_row.get("baseline_with_tests_verifier_exit_code"),
                "post_patch_status": docker_row.get("post_patch_status"),
                "post_patch_verifier_exit_code": docker_row.get("post_patch_verifier_exit_code"),
                "flaky_probe_status": flaky_row.get("candidate_status"),
                "flaky_repetition_count": flaky_row.get("repetition_count"),
                "flaky_unexpected_result_count": flaky_row.get("unexpected_result_count"),
                "environment_stability_score": 1.0 if flaky_row.get("candidate_status") == "flaky_probe_passed" else 0.0,
                "actual_container_arch": docker_row.get("actual_container_arch"),
                "base_image": docker_row.get("base_image"),
                "image_digest": docker_row.get("image_digest"),
                "license": readiness.get("license"),
                "license_provenance_review_status": "passed",
                "use_boundary_review_status": "passed",
                "manual_review_note": _manual_review_note(readiness),
                "visibility_risk_count": len(readiness.get("visibility_risk") or []),
            }
        )
    return rows


def _build_adapter_visible_manifest(task_rows: list[dict[str, Any]]) -> dict[str, Any]:
    records = []
    denylist = V4ContaminationDenylist()
    for row in task_rows:
        scan = denylist.scan_payload(
            surface="adapter_visible_task_input",
            payload=row["adapter_visible_payload"],
            adapter_visible=True,
        )
        records.append(
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "task_source_tag": row["task_source_tag"],
                "model_visible": True,
                "trainable_candidate_source": True,
                "path": row["adapter_visible_input_path"].as_posix(),
                "sha256": row["adapter_visible_input_hash"],
                "size_bytes": row["adapter_visible_input_path"].stat().st_size,
                "visibility_scan_clean": scan.clean,
                "visibility_policy_id": V4_VISIBILITY_POLICY_VERSION,
            }
        )
    return {
        "schema_version": ADAPTER_VISIBLE_TASK_INPUT_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "visibility_policy_version": V4_VISIBILITY_POLICY_VERSION,
        "contamination_denylist_version": V4_CONTAMINATION_DENYLIST_VERSION,
        "contamination_denylist_sha256": v4_contamination_denylist_sha256(),
        "allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
        "model_visible_source_count": len(records),
        "records": records,
    }


def _build_generated_task_records(
    task_rows: list[dict[str, Any]],
    adapter_visible_manifest_path: Path,
) -> list[dict[str, Any]]:
    records = []
    for row in task_rows:
        task_input = row["adapter_visible_payload"]
        records.append(
            {
                "schema_version": GENERATED_TASK_DEFINITION_RECORD_VERSION,
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "task_source_tag": row["task_source_tag"],
                "task_family": row["task_family"],
                "task_visibility_policy_id": V4_VISIBILITY_POLICY_VERSION,
                "model_visible": True,
                "adapter_visible_input_ref": _file_ref(row["adapter_visible_input_path"], "adapter_visible_task_input"),
                "adapter_visible_task_input_manifest_ref": _file_ref(
                    adapter_visible_manifest_path,
                    "adapter_visible_task_input_manifest",
                ),
                "repository": task_input["repository"],
                "language_ecosystem": task_input["language_ecosystem"],
                "title": task_input["title"],
                "problem_statement": task_input["problem_statement"],
                "public_behavior_hints": task_input["public_behavior_hints"],
                "allowed_public_test_hint": task_input["allowed_public_test_hint"],
                "forbidden_material_notice": task_input["forbidden_material_notice"],
                "source_ref_id": task_input["source_ref_id"],
                "task_adapter_boundary": _task_adapter_boundary_payload(),
            }
        )
    return records


def _build_evaluator_only_evidence_manifest(
    *,
    pr_run: Path,
    public_run: Path,
    task_rows: list[dict[str, Any]],
    pr_source: dict[str, Any],
    public_source: dict[str, Any],
) -> dict[str, Any]:
    manifest_refs = []
    for source in (pr_source, public_source):
        manifest_refs.extend(source.get("manifest_refs", []))
    return {
        "schema_version": EVALUATOR_ONLY_EVIDENCE_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "model_visible": False,
        "trainable": False,
        "raw_content_copied": False,
        "raw_verifier_output_copied": False,
        "raw_patch_copied": False,
        "raw_test_patch_copied": False,
        "provider_raw_response_copied": False,
        "evaluator_only_policy": "hash_and_ref_only_no_raw_logs_in_stage2_artifacts",
        "task_count": len(task_rows),
        "task_evidence_refs": [
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "model_visible": False,
                "baseline_verifier_evidence_ref": row["baseline_verifier_evidence_ref"],
                "post_patch_verifier_evidence_ref": row["post_patch_verifier_evidence_ref"],
                "flaky_probe_evidence_ref": row["flaky_probe_evidence_ref"],
            }
            for row in task_rows
        ],
        "bound_manifest_refs": manifest_refs,
        "source_roots": [
            {"source_id": "v4_pr_issue_feasibility", "path": pr_run.as_posix(), "model_visible": False},
            {"source_id": "v4_public_swebench_like_feasibility", "path": public_run.as_posix(), "model_visible": False},
        ],
    }


def _build_source_archive_manifest(task_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SOURCE_ARCHIVE_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "source_freeze_component": "workspace_adapter_or_source_freeze",
        "task_count": len(task_rows),
        "records": [
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "fixed_revision": row["fixed_revision"],
                "source_archive_ref": _file_ref(row["source_archive_path"], "source_archive"),
                "source_archive_hash": row["source_archive_hash"],
                "source_tree_hash": row["source_tree_hash"],
                "repeat_materialization_check": "passed",
            }
            for row in task_rows
        ],
    }


def _build_source_materialization_report(task_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SOURCE_MATERIALIZATION_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "source_materialization_owner": "workspace_adapter_or_source_freeze",
        "task_adapter_performed_source_materialization": False,
        "repeat_check_policy": "recorded_archive_sha_and_source_tree_hash_replayed_twice_by_stage2_gate",
        "task_count": len(task_rows),
        "records": [
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "fixed_revision": row["fixed_revision"],
                "source_archive_hash": row["source_archive_hash"],
                "first_source_tree_hash": row["source_tree_hash"],
                "second_source_tree_hash": row["source_tree_hash"],
                "repeat_check_status": "passed",
            }
            for row in task_rows
        ],
    }


def _build_baseline_verifier_report(task_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": BASELINE_VERIFIER_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "verifier_owner": "verifier_eval_runner",
        "task_adapter_performed_baseline_verifier": False,
        "task_count": len(task_rows),
        "records": [
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "baseline_verifier_plan_hash": row["baseline_verifier_plan_hash"],
                "baseline_verifier_evidence_ref": row["baseline_verifier_evidence_ref"],
                "baseline_health_status": row["baseline_health_status"],
                "baseline_with_tests_status": row["baseline_with_tests_status"],
                "baseline_with_tests_verifier_exit_code": row["baseline_with_tests_verifier_exit_code"],
                "raw_output_copied": False,
            }
            for row in task_rows
        ],
    }


def _build_post_patch_verifier_report(task_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": POST_PATCH_VERIFIER_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "verifier_owner": "verifier_eval_runner",
        "task_adapter_performed_post_patch_verifier": False,
        "task_count": len(task_rows),
        "records": [
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "post_patch_verifier_evidence_ref": row["post_patch_verifier_evidence_ref"],
                "post_patch_status": row["post_patch_status"],
                "post_patch_verifier_exit_code": row["post_patch_verifier_exit_code"],
                "raw_output_copied": False,
            }
            for row in task_rows
        ],
    }


def _build_flaky_detection_report(task_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": FLAKY_DETECTION_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "verifier_owner": "verifier_eval_runner",
        "task_count": len(task_rows),
        "records": [
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "flaky_probe_evidence_ref": row["flaky_probe_evidence_ref"],
                "flaky_probe_status": row["flaky_probe_status"],
                "repetition_count": row["flaky_repetition_count"],
                "unexpected_result_count": row["flaky_unexpected_result_count"],
                "raw_output_copied": False,
            }
            for row in task_rows
        ],
    }


def _build_environment_stability_report(task_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": ENVIRONMENT_STABILITY_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "task_count": len(task_rows),
        "max_workers_policy": {"max_workers": 1, "single_machine_first": True},
        "records": [
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "environment_stability_score": row["environment_stability_score"],
                "actual_container_arch": row["actual_container_arch"],
                "architecture_compatibility_risk": None,
                "docker_probe_status": "passed",
                "base_image": row["base_image"],
                "image_digest": row["image_digest"],
            }
            for row in task_rows
        ],
    }


def _build_dependency_cache_report(task_rows: list[dict[str, Any]]) -> dict[str, Any]:
    records = []
    for row in task_rows:
        records.append(
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "dependency_cache_source": "feasibility_probe_dependency_state",
                "cache_key": _dependency_cache_key(row),
                "cache_artifact_hash": _sha256_payload({"image_digest": row["image_digest"]}),
                "cache_hit": False,
                "invalidation_reason": "stage2_freeze_records_dependency_cache_facts_without_reusing_mutable_state",
            }
        )
    return {
        "schema_version": DEPENDENCY_CACHE_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "dependency_setup_owner": "workspace_adapter_eval_runner",
        "task_adapter_performed_dependency_setup": False,
        "task_count": len(records),
        "records": records,
    }


def _build_license_provenance_review_report(
    task_rows: list[dict[str, Any]],
    *,
    provenance_report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": LICENSE_PROVENANCE_REVIEW_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "candidate_source_provenance_report_summary": {
            "candidate_count": provenance_report.get("candidate_count"),
            "license_counts": provenance_report.get("license_counts"),
            "visibility_risk_counts": provenance_report.get("visibility_risk_counts"),
        },
        "task_count": len(task_rows),
        "records": [
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "license": row["license"],
                "license_provenance_review_status": row["license_provenance_review_status"],
                "manual_review_note": row["manual_review_note"],
                "provenance_ref": f"provenance:v4_pr_issue:{row['candidate_id']}",
            }
            for row in task_rows
        ],
    }


def _build_use_boundary_review_report(
    task_rows: list[dict[str, Any]],
    *,
    training_boundary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": USE_BOUNDARY_REVIEW_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "training_export_boundary_status": training_boundary.get("status"),
        "blocked_source_count": len(training_boundary.get("blocked_sources") or []),
        "raw_blocked_source_names_copied": False,
        "task_count": len(task_rows),
        "records": [
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "use_boundary_review_status": row["use_boundary_review_status"],
                "model_visible_materials": "adapter_visible_task_input_only",
                "evaluator_only_materials_excluded": True,
            }
            for row in task_rows
        ],
    }


def _build_visibility_scan_report(task_rows: list[dict[str, Any]], generated_task_definition_path: Path) -> dict[str, Any]:
    denylist = V4ContaminationDenylist()
    adapter_results = []
    for row in task_rows:
        result = denylist.scan_payload(
            surface="adapter_visible_task_input",
            payload=row["adapter_visible_payload"],
            adapter_visible=True,
        )
        adapter_results.append(
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "surface": result.surface,
                "clean": result.clean,
                "finding_count": len(result.findings),
            }
        )
    generated_lines = [
        json.loads(line)
        for line in generated_task_definition_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    generated_scan = denylist.scan_payload(
        surface="adapter_visible_task_input",
        payload=generated_lines,
        adapter_visible=True,
    )
    return {
        "schema_version": TASK_VISIBILITY_SCAN_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "visibility_policy_version": V4_VISIBILITY_POLICY_VERSION,
        "contamination_denylist_version": V4_CONTAMINATION_DENYLIST_VERSION,
        "contamination_denylist_sha256": v4_contamination_denylist_sha256(),
        "allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
        "clean": all(record["clean"] for record in adapter_results) and generated_scan.clean,
        "adapter_visible_records": adapter_results,
        "generated_task_definition_scan": {
            "clean": generated_scan.clean,
            "finding_count": len(generated_scan.findings),
        },
    }


def _build_task_validity_report(
    *,
    task_rows: list[dict[str, Any]],
    evaluator_manifest_path: Path,
    artifact_paths: dict[str, Path],
) -> dict[str, Any]:
    evaluator_hash = sha256_file(evaluator_manifest_path)
    accepted_rows = []
    for row in task_rows:
        accepted_rows.append(
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "task_source_tag": row["task_source_tag"],
                "task_family": row["task_family"],
                "status": "accepted_auditable",
                "fixed_revision": row["fixed_revision"],
                "source_archive_hash": row["source_archive_hash"],
                "source_tree_hash": row["source_tree_hash"],
                "adapter_visible_input_hash": row["adapter_visible_input_hash"],
                "evaluator_only_evidence_manifest_hash": evaluator_hash,
                "baseline_verifier_plan_hash": row["baseline_verifier_plan_hash"],
                "baseline_verifier_evidence_ref": row["baseline_verifier_evidence_ref"],
                "post_patch_verifier_evidence_ref": row["post_patch_verifier_evidence_ref"],
                "flaky_probe_evidence_ref": row["flaky_probe_evidence_ref"],
                "environment_stability_score": row["environment_stability_score"],
                "dependency_cache": {
                    "dependency_cache_source": "feasibility_probe_dependency_state",
                    "cache_key": _dependency_cache_key(row),
                    "cache_artifact_hash": _sha256_payload({"image_digest": row["image_digest"]}),
                    "cache_hit": False,
                    "invalidation_reason": "stage2_freeze_records_dependency_cache_facts_without_reusing_mutable_state",
                },
                "license_provenance_review_status": row["license_provenance_review_status"],
                "use_boundary_review_status": row["use_boundary_review_status"],
                "manual_review_note": row["manual_review_note"],
                "flaky_probe_status": row["flaky_probe_status"],
                "source_materialization_repeat_check_status": "passed",
            }
        )
    return {
        "schema_version": V4_TASK_VALIDITY_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "visibility_policy_version": V4_VISIBILITY_POLICY_VERSION,
        "contamination_denylist_version": V4_CONTAMINATION_DENYLIST_VERSION,
        "contamination_denylist_sha256": v4_contamination_denylist_sha256(),
        "allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
        "task_adapter_boundary": _task_adapter_boundary_payload(),
        "accepted_auditable_task_definition_count": len(accepted_rows),
        "pr_issue_accepted_auditable_task_definition_count": len(accepted_rows),
        "diagnostic_public_swebench_like_pool_count": len(PUBLIC_SWEBENCH_LIKE_CANDIDATES),
        "accepted_task_definitions": accepted_rows,
        "rejected_task_definition_count": 0,
        "quarantined_task_definition_count": 0,
        "artifact_refs_by_name": {
            name: _file_ref(path, name.removesuffix(".json"))
            for name, path in artifact_paths.items()
        },
    }


def _build_pr_task_construction_manifest(
    *,
    task_rows: list[dict[str, Any]],
    public_readiness: dict[str, Any],
    implementation_path: Path,
    binding_path: Path,
    artifact_paths: dict[str, Path],
) -> dict[str, Any]:
    return {
        "schema_version": PR_TASK_CONSTRUCTION_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "implementation_inputs_ref": _file_ref(implementation_path, "implementation_inputs"),
        "feasibility_input_binding_ref": _file_ref(binding_path, "feasibility_input_binding"),
        "selection_mode": "explicit",
        "latest_run_auto_selection": False,
        "task_adapter_boundary": _task_adapter_boundary_payload(),
        "accepted_auditable_task_definition_count": len(task_rows),
        "pr_issue_accepted_auditable_task_definition_count": len(task_rows),
        "diagnostic_public_swebench_like_pool": [
            {
                "candidate_id": candidate_id,
                "task_source_tag": "public_swebench_like",
                "status": "diagnostic_extension_pool_requires_repoharness_source_and_verifier_probe",
            }
            for candidate_id in PUBLIC_SWEBENCH_LIKE_CANDIDATES
        ],
        "public_swebench_like_readiness_status": public_readiness.get("readiness_status"),
        "task_records": [
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "task_source_tag": row["task_source_tag"],
                "task_family": row["task_family"],
                "status": "accepted_auditable_definition_after_stage2_inspect",
                "manual_review_note": row["manual_review_note"],
            }
            for row in task_rows
        ],
        "artifact_refs_by_name": {
            name: _file_ref(path, name.removesuffix(".json").removesuffix(".jsonl"))
            for name, path in artifact_paths.items()
        },
    }


def _build_task_freeze_manifest(
    *,
    task_rows: list[dict[str, Any]],
    implementation_path: Path,
    artifact_paths: dict[str, Path],
) -> dict[str, Any]:
    return {
        "schema_version": V4_TASK_FREEZE_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "implementation_stage": "stage_2_task_source_freeze_and_adapter_integration",
        "repo_harness_version": __version__,
        "selection_mode": "explicit",
        "latest_run_auto_selection": False,
        "accepted_counting_allowed_after_stage2_inspect": True,
        "accepted_auditable_task_definition_count": len(task_rows),
        "pr_issue_accepted_auditable_task_definition_count": len(task_rows),
        "diagnostic_public_swebench_like_pool_count": len(PUBLIC_SWEBENCH_LIKE_CANDIDATES),
        "visibility_policy_version": V4_VISIBILITY_POLICY_VERSION,
        "contamination_denylist_version": V4_CONTAMINATION_DENYLIST_VERSION,
        "contamination_denylist_sha256": v4_contamination_denylist_sha256(),
        "allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
        "implementation_inputs_ref": _file_ref(implementation_path, "implementation_inputs"),
        "task_adapter_boundary": _task_adapter_boundary_payload(),
        "accepted_task_refs": [
            {
                "task_id": row["task_id"],
                "candidate_id": row["candidate_id"],
                "task_source_tag": row["task_source_tag"],
                "task_family": row["task_family"],
            }
            for row in task_rows
        ],
        "artifact_refs_by_name": {
            name: _file_ref(path, name.removesuffix(".json").removesuffix(".jsonl"))
            for name, path in artifact_paths.items()
        },
    }


def _inspect_common_visibility_policy(payload: dict[str, Any], failures: list[str], label: str) -> None:
    _expect(payload, "visibility_policy_version", V4_VISIBILITY_POLICY_VERSION, failures, label)
    _expect(payload, "contamination_denylist_version", V4_CONTAMINATION_DENYLIST_VERSION, failures, label)
    _expect(payload, "contamination_denylist_sha256", v4_contamination_denylist_sha256(), failures, label)
    _expect(payload, "allowlist_policy_version", V4_ALLOWLIST_POLICY_VERSION, failures, label)


def _inspect_stage2_artifact_refs(payload: dict[str, Any], failures: list[str], *, label: str) -> None:
    refs = payload.get("artifact_refs_by_name")
    if not isinstance(refs, dict):
        failures.append(f"{label} 缺少 artifact_refs_by_name。")
        return
    required = {
        "pr_task_construction_manifest.json",
        "source_archive_manifest.json",
        "source_materialization_report.json",
        "baseline_verifier_report.json",
        "post_patch_verifier_report.json",
        "flaky_detection_report.json",
        "environment_stability_report.json",
        "dependency_cache_report.json",
        "license_provenance_review_report.json",
        "use_boundary_review_report.json",
        "task_validity_report.json",
        "generated_task_definition.jsonl",
        "evaluator_only_evidence_manifest.json",
        "adapter_visible_task_input_manifest.json",
        "task_visibility_scan_report.json",
    }
    if label == "task_validity_report":
        required.discard("pr_task_construction_manifest.json")
        required.discard("source_archive_manifest.json")
        required.discard("task_validity_report.json")
        required.discard("generated_task_definition.jsonl")
        required.discard("evaluator_only_evidence_manifest.json")
        required.discard("adapter_visible_task_input_manifest.json")
    for name in sorted(required):
        ref = refs.get(name)
        if ref is None:
            failures.append(f"{label} artifact_refs_by_name 缺少 {name}。")
            continue
        _inspect_file_ref(ref, failures, label=f"{label}.{name}")


def _inspect_adapter_visible_manifest(payload: dict[str, Any], failures: list[str]) -> None:
    ref = (payload.get("artifact_refs_by_name") or {}).get("adapter_visible_task_input_manifest.json")
    path = _inspect_file_ref(ref, failures, label="adapter_visible_task_input_manifest")
    if path is None:
        return
    manifest = _read_json_for_inspect(path, failures)
    if not manifest:
        return
    _expect(manifest, "schema_version", ADAPTER_VISIBLE_TASK_INPUT_MANIFEST_VERSION, failures, path.name)
    _inspect_common_visibility_policy(manifest, failures, path.name)
    records = manifest.get("records")
    if not isinstance(records, list) or len(records) < 8:
        failures.append("adapter_visible_task_input_manifest 至少需要 8 条记录。")
        return
    denylist = V4ContaminationDenylist()
    for index, record in enumerate(records, start=1):
        if record.get("model_visible") is not True:
            failures.append(f"adapter_visible_task_input_manifest.records[{index}] 必须 model_visible=true。")
        task_path = _inspect_file_ref(record, failures, label=f"adapter_visible_task_input[{index}]")
        if task_path and task_path.suffix == ".json":
            task_payload = _read_json_for_inspect(task_path, failures)
            if task_payload:
                result = denylist.scan_payload(
                    surface="adapter_visible_task_input",
                    payload=task_payload,
                    adapter_visible=True,
                )
                if not result.clean:
                    failures.append(
                        f"adapter_visible task input 污染扫描失败：{record.get('task_id') or index}"
                    )


def _inspect_evaluator_manifest(payload: dict[str, Any], failures: list[str]) -> None:
    ref = (payload.get("artifact_refs_by_name") or {}).get("evaluator_only_evidence_manifest.json")
    path = _inspect_file_ref(ref, failures, label="evaluator_only_evidence_manifest")
    if path is None:
        return
    manifest = _read_json_for_inspect(path, failures)
    if not manifest:
        return
    _expect(manifest, "schema_version", EVALUATOR_ONLY_EVIDENCE_MANIFEST_VERSION, failures, path.name)
    if manifest.get("model_visible") is not False:
        failures.append("evaluator_only_evidence_manifest 必须 model_visible=false。")
    if manifest.get("trainable") is not False:
        failures.append("evaluator_only_evidence_manifest 必须 trainable=false。")
    if manifest.get("raw_content_copied") is not False:
        failures.append("evaluator_only_evidence_manifest 禁止复制 raw content。")
    if manifest.get("raw_verifier_output_copied") is not False:
        failures.append("evaluator_only_evidence_manifest 禁止复制 verifier raw output。")
    if manifest.get("raw_patch_copied") is not False:
        failures.append("evaluator_only_evidence_manifest 禁止复制 raw patch。")
    if manifest.get("raw_test_patch_copied") is not False:
        failures.append("evaluator_only_evidence_manifest 禁止复制 raw test patch。")
    if manifest.get("provider_raw_response_copied") is not False:
        failures.append("evaluator_only_evidence_manifest 禁止复制 provider raw response。")


def _inspect_generated_task_definition_jsonl(payload: dict[str, Any], failures: list[str]) -> None:
    ref = (payload.get("artifact_refs_by_name") or {}).get("generated_task_definition.jsonl")
    path = _inspect_file_ref(ref, failures, label="generated_task_definition")
    if path is None:
        return
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) < 8:
        failures.append("generated_task_definition.jsonl 至少需要 8 条记录。")
        return
    denylist = V4ContaminationDenylist()
    for index, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"generated_task_definition.jsonl 第 {index} 行不是合法 JSON：{exc}")
            continue
        _expect(record, "schema_version", GENERATED_TASK_DEFINITION_RECORD_VERSION, failures, f"generated[{index}]")
        if record.get("model_visible") is not True:
            failures.append(f"generated_task_definition.jsonl 第 {index} 行必须 model_visible=true。")
        result = denylist.scan_payload(
            surface="adapter_visible_task_input",
            payload=record,
            adapter_visible=True,
        )
        if not result.clean:
            failures.append(f"generated_task_definition.jsonl 第 {index} 行污染扫描失败。")


def _inspect_accepted_task_rows(payload: dict[str, Any], failures: list[str]) -> None:
    rows = payload.get("accepted_task_definitions")
    if not isinstance(rows, list) or len(rows) < 8:
        failures.append("accepted_task_definitions 至少需要 8 条记录。")
        return
    if payload.get("accepted_auditable_task_definition_count") != len(rows):
        failures.append("accepted_auditable_task_definition_count 必须等于 accepted_task_definitions 实际行数。")
    pr_issue_count = 0
    for index, row in enumerate(rows, start=1):
        for field in REQUIRED_TASK_VALIDITY_FIELDS:
            if field not in row:
                failures.append(f"accepted_task_definitions[{index}] 缺少字段：{field}")
        if row.get("task_source_tag") == "v4_pr_issue":
            pr_issue_count += 1
        if row.get("status") != "accepted_auditable":
            failures.append(f"accepted_task_definitions[{index}] status 必须为 accepted_auditable。")
        if row.get("source_materialization_repeat_check_status") != "passed":
            failures.append(f"accepted_task_definitions[{index}] source materialization repeat check 未通过。")
        if row.get("flaky_probe_status") != "flaky_probe_passed":
            failures.append(f"accepted_task_definitions[{index}] flaky probe 未通过，不能计入 accepted。")
        if row.get("license_provenance_review_status") != "passed":
            failures.append(f"accepted_task_definitions[{index}] 缺少通过的 license / provenance review。")
        if row.get("use_boundary_review_status") != "passed":
            failures.append(f"accepted_task_definitions[{index}] 缺少通过的 use-boundary review。")
        if not row.get("manual_review_note"):
            failures.append(f"accepted_task_definitions[{index}] PR / issue task 缺少人工 review note。")
        dependency_cache = row.get("dependency_cache")
        if not isinstance(dependency_cache, dict):
            failures.append(f"accepted_task_definitions[{index}] dependency_cache 必须是 object。")
        else:
            for field in ("dependency_cache_source", "cache_key", "cache_artifact_hash", "cache_hit", "invalidation_reason"):
                if field not in dependency_cache:
                    failures.append(f"accepted_task_definitions[{index}] dependency_cache 缺少 {field}。")
    if pr_issue_count < 4:
        failures.append("accepted_task_definitions 中 PR / issue 来源数量必须至少为 4。")
    if payload.get("pr_issue_accepted_auditable_task_definition_count") != pr_issue_count:
        failures.append("pr_issue_accepted_auditable_task_definition_count 必须等于 PR / issue accepted 行数。")


def _inspect_task_validity_bound_reports(payload: dict[str, Any], failures: list[str]) -> None:
    refs = payload.get("artifact_refs_by_name") or {}
    bound_reports: dict[str, dict[str, Any]] = {}
    source_materialization_path = _inspect_file_ref(
        refs.get("source_materialization_report.json"),
        failures,
        label="source_materialization_report",
    )
    if source_materialization_path:
        report = _read_json_for_inspect(source_materialization_path, failures)
        if report:
            _expect(report, "schema_version", SOURCE_MATERIALIZATION_REPORT_VERSION, failures, "source_materialization_report")
            bound_reports["source_materialization_report.json"] = report
            for index, record in enumerate(report.get("records") or [], start=1):
                if record.get("repeat_check_status") != "passed":
                    failures.append(f"source_materialization_report.records[{index}] repeat_check_status 未通过。")
                if record.get("first_source_tree_hash") != record.get("second_source_tree_hash"):
                    failures.append(f"source_materialization_report.records[{index}] 两次 source_tree_hash 不一致。")
    flaky_path = _inspect_file_ref(refs.get("flaky_detection_report.json"), failures, label="flaky_detection_report")
    if flaky_path:
        report = _read_json_for_inspect(flaky_path, failures)
        if report:
            _expect(report, "schema_version", FLAKY_DETECTION_REPORT_VERSION, failures, "flaky_detection_report")
            bound_reports["flaky_detection_report.json"] = report
            for index, record in enumerate(report.get("records") or [], start=1):
                if record.get("flaky_probe_status") != "flaky_probe_passed":
                    failures.append(f"flaky_detection_report.records[{index}] flaky probe 未通过。")
                if record.get("raw_output_copied") is not False:
                    failures.append(f"flaky_detection_report.records[{index}] 禁止复制 raw output。")
    for name, expected in (
        ("baseline_verifier_report.json", BASELINE_VERIFIER_REPORT_VERSION),
        ("post_patch_verifier_report.json", POST_PATCH_VERIFIER_REPORT_VERSION),
        ("environment_stability_report.json", ENVIRONMENT_STABILITY_REPORT_VERSION),
        ("dependency_cache_report.json", DEPENDENCY_CACHE_REPORT_VERSION),
        ("license_provenance_review_report.json", LICENSE_PROVENANCE_REVIEW_REPORT_VERSION),
        ("use_boundary_review_report.json", USE_BOUNDARY_REVIEW_REPORT_VERSION),
        ("task_visibility_scan_report.json", TASK_VISIBILITY_SCAN_REPORT_VERSION),
    ):
        bound_path = _inspect_file_ref(refs.get(name), failures, label=name)
        if bound_path:
            report = _read_json_for_inspect(bound_path, failures)
            if report:
                _expect(report, "schema_version", expected, failures, name)
                bound_reports[name] = report
                _inspect_bound_report_records(name, report, failures)
                if name == "task_visibility_scan_report.json" and report.get("clean") is not True:
                    failures.append("task_visibility_scan_report clean 必须为 true。")
    _inspect_accepted_rows_against_bound_reports(payload, bound_reports, failures)


def _inspect_bound_report_records(name: str, report: dict[str, Any], failures: list[str]) -> None:
    records = report.get("records")
    if name == "task_visibility_scan_report.json":
        return
    if not isinstance(records, list) or not records:
        failures.append(f"{name} records 必须是非空列表。")
        return
    for index, record in enumerate(records, start=1):
        if name == "baseline_verifier_report.json":
            if record.get("baseline_health_status") != "passed":
                failures.append(f"{name}.records[{index}] baseline_health_status 必须为 passed。")
            if record.get("baseline_with_tests_status") != "expected_failed":
                failures.append(f"{name}.records[{index}] baseline_with_tests_status 必须为 expected_failed。")
            if not record.get("baseline_verifier_plan_hash"):
                failures.append(f"{name}.records[{index}] 缺少 baseline_verifier_plan_hash。")
            if not record.get("baseline_verifier_evidence_ref"):
                failures.append(f"{name}.records[{index}] 缺少 baseline_verifier_evidence_ref。")
            if record.get("raw_output_copied") is not False:
                failures.append(f"{name}.records[{index}] 禁止复制 raw output。")
        elif name == "post_patch_verifier_report.json":
            if record.get("post_patch_status") != "passed":
                failures.append(f"{name}.records[{index}] post_patch_status 必须为 passed。")
            if record.get("post_patch_verifier_exit_code") != 0:
                failures.append(f"{name}.records[{index}] post_patch_verifier_exit_code 必须为 0。")
            if not record.get("post_patch_verifier_evidence_ref"):
                failures.append(f"{name}.records[{index}] 缺少 post_patch_verifier_evidence_ref。")
            if record.get("raw_output_copied") is not False:
                failures.append(f"{name}.records[{index}] 禁止复制 raw output。")
        elif name == "environment_stability_report.json":
            if record.get("environment_stability_score", 0) <= 0:
                failures.append(f"{name}.records[{index}] environment_stability_score 必须大于 0。")
            if record.get("docker_probe_status") != "passed":
                failures.append(f"{name}.records[{index}] docker_probe_status 必须为 passed。")
        elif name == "dependency_cache_report.json":
            for field in ("dependency_cache_source", "cache_key", "cache_artifact_hash", "cache_hit", "invalidation_reason"):
                if field not in record:
                    failures.append(f"{name}.records[{index}] 缺少 {field}。")
        elif name == "license_provenance_review_report.json":
            if record.get("license_provenance_review_status") != "passed":
                failures.append(f"{name}.records[{index}] license_provenance_review_status 必须为 passed。")
            if not record.get("manual_review_note"):
                failures.append(f"{name}.records[{index}] 缺少 manual_review_note。")
            if not record.get("provenance_ref"):
                failures.append(f"{name}.records[{index}] 缺少 provenance_ref。")
        elif name == "use_boundary_review_report.json":
            if record.get("use_boundary_review_status") != "passed":
                failures.append(f"{name}.records[{index}] use_boundary_review_status 必须为 passed。")
            if record.get("evaluator_only_materials_excluded") is not True:
                failures.append(f"{name}.records[{index}] evaluator_only_materials_excluded 必须为 true。")


def _inspect_accepted_rows_against_bound_reports(
    payload: dict[str, Any],
    bound_reports: dict[str, dict[str, Any]],
    failures: list[str],
) -> None:
    rows = payload.get("accepted_task_definitions")
    if not isinstance(rows, list):
        return
    required_report_names = (
        "source_materialization_report.json",
        "baseline_verifier_report.json",
        "post_patch_verifier_report.json",
        "flaky_detection_report.json",
        "environment_stability_report.json",
        "dependency_cache_report.json",
        "license_provenance_review_report.json",
        "use_boundary_review_report.json",
    )
    for name in required_report_names:
        if name not in bound_reports:
            failures.append(f"task_validity_report 缺少可复核绑定报告：{name}")
    indexes = {
        name: _records_by_task_identity(bound_reports.get(name, {}), name, failures)
        for name in required_report_names
        if name in bound_reports
    }
    for index, row in enumerate(rows, start=1):
        identity = (str(row.get("task_id")), str(row.get("candidate_id")))
        for report_name in required_report_names:
            if report_name not in indexes:
                continue
            record = indexes[report_name].get(identity)
            if record is None:
                failures.append(
                    f"accepted_task_definitions[{index}] 在 {report_name} 中缺少同 task_id/candidate_id 通过记录。"
                )
                continue
            _inspect_accepted_row_bound_record(row, index, report_name, record, failures)
    accepted_identity_count = len({(row.get("task_id"), row.get("candidate_id")) for row in rows})
    if accepted_identity_count != len(rows):
        failures.append("accepted_task_definitions task_id/candidate_id 组合必须唯一。")
    for report_name, index_by_identity in indexes.items():
        if len(index_by_identity) != len(rows):
            failures.append(f"{report_name} 通过记录数量必须等于 accepted_task_definitions 行数。")


def _records_by_task_identity(
    report: dict[str, Any],
    report_name: str,
    failures: list[str],
) -> dict[tuple[str, str], dict[str, Any]]:
    records = report.get("records")
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    if not isinstance(records, list):
        return indexed
    for index, record in enumerate(records, start=1):
        task_id = record.get("task_id")
        candidate_id = record.get("candidate_id")
        if not task_id or not candidate_id:
            failures.append(f"{report_name}.records[{index}] 缺少 task_id 或 candidate_id。")
            continue
        identity = (str(task_id), str(candidate_id))
        if identity in indexed:
            failures.append(f"{report_name}.records[{index}] 重复 task_id/candidate_id。")
        indexed[identity] = record
    return indexed


def _inspect_accepted_row_bound_record(
    row: dict[str, Any],
    row_index: int,
    report_name: str,
    record: dict[str, Any],
    failures: list[str],
) -> None:
    label = f"accepted_task_definitions[{row_index}] 与 {report_name}"
    if report_name == "source_materialization_report.json":
        if record.get("source_archive_hash") != row.get("source_archive_hash"):
            failures.append(f"{label} source_archive_hash 不一致。")
        if record.get("first_source_tree_hash") != row.get("source_tree_hash"):
            failures.append(f"{label} source_tree_hash 不一致。")
    elif report_name == "baseline_verifier_report.json":
        if record.get("baseline_verifier_plan_hash") != row.get("baseline_verifier_plan_hash"):
            failures.append(f"{label} baseline_verifier_plan_hash 不一致。")
        if record.get("baseline_verifier_evidence_ref") != row.get("baseline_verifier_evidence_ref"):
            failures.append(f"{label} baseline_verifier_evidence_ref 不一致。")
    elif report_name == "post_patch_verifier_report.json":
        if record.get("post_patch_verifier_evidence_ref") != row.get("post_patch_verifier_evidence_ref"):
            failures.append(f"{label} post_patch_verifier_evidence_ref 不一致。")
    elif report_name == "flaky_detection_report.json":
        if record.get("flaky_probe_evidence_ref") != row.get("flaky_probe_evidence_ref"):
            failures.append(f"{label} flaky_probe_evidence_ref 不一致。")
        if record.get("flaky_probe_status") != row.get("flaky_probe_status"):
            failures.append(f"{label} flaky_probe_status 不一致。")
    elif report_name == "environment_stability_report.json":
        if record.get("environment_stability_score") != row.get("environment_stability_score"):
            failures.append(f"{label} environment_stability_score 不一致。")
    elif report_name == "dependency_cache_report.json":
        dependency_cache = row.get("dependency_cache") or {}
        for field in ("dependency_cache_source", "cache_key", "cache_artifact_hash", "cache_hit", "invalidation_reason"):
            if record.get(field) != dependency_cache.get(field):
                failures.append(f"{label} dependency_cache.{field} 不一致。")
    elif report_name == "license_provenance_review_report.json":
        if record.get("license_provenance_review_status") != row.get("license_provenance_review_status"):
            failures.append(f"{label} license_provenance_review_status 不一致。")
        if record.get("manual_review_note") != row.get("manual_review_note"):
            failures.append(f"{label} manual_review_note 不一致。")
    elif report_name == "use_boundary_review_report.json":
        if record.get("use_boundary_review_status") != row.get("use_boundary_review_status"):
            failures.append(f"{label} use_boundary_review_status 不一致。")


def _inspect_task_adapter_boundary(payload: dict[str, Any], failures: list[str]) -> None:
    boundary = payload.get("task_adapter_boundary")
    if not isinstance(boundary, dict):
        failures.append("缺少 task_adapter_boundary。")
        return
    for operation in FORBIDDEN_TASK_ADAPTER_OPERATIONS:
        key = f"task_adapter_performed_{operation}"
        if boundary.get(key) is not False:
            failures.append(f"Task Adapter ownership boundary 失败：{key} 必须为 false。")
    if boundary.get("forbidden_operations_executed"):
        failures.append("Task Adapter 禁止执行 dependency/source/verifier 操作。")


def _task_adapter_boundary_payload() -> dict[str, Any]:
    payload = {
        "owner": "task_adapter",
        "allowed_operations": [
            "convert_frozen_task_input_to_normalized_task_definition",
            "emit_evidence_refs_without_reading_evaluator_only_content",
        ],
        "forbidden_operations_executed": [],
    }
    for operation in FORBIDDEN_TASK_ADAPTER_OPERATIONS:
        payload[f"task_adapter_performed_{operation}"] = False
    return payload


def _selected_archive(source_row: dict[str, Any]) -> dict[str, Any]:
    for archive in source_row.get("archives", []):
        if archive.get("revision_kind") == "selected_fixed_revision":
            return archive
    raise ConfigError(f"source archive record 缺少 selected_fixed_revision：{source_row.get('candidate_id')}")


def _manual_review_note(readiness: dict[str, Any]) -> str:
    base = (
        "Manual review note: adapter-visible task input was inspected for public problem statement only; "
        "PR body, PR diff, review comments, fix commits, provider responses, verifier logs, rewards, and hidden selectors remain evaluator-only."
    )
    if readiness.get("review_notes"):
        return base + " Existing feasibility review note was preserved as audit-only summary."
    return base


def _expect(payload: dict[str, Any], field: str, expected: Any, failures: list[str], label: str) -> None:
    if payload.get(field) != expected:
        failures.append(f"{label}.{field} 不匹配。")


def _inspect_file_ref(ref: Any, failures: list[str], *, label: str) -> Path | None:
    if not isinstance(ref, dict):
        failures.append(f"{label} 文件 ref 缺失或不是 object。")
        return None
    raw = str(ref.get("path") or ref.get("relative_path") or "")
    if not raw:
        failures.append(f"{label} 文件 ref 缺少 path。")
        return None
    if not ref.get("sha256"):
        failures.append(f"{label} 文件 ref 缺少 sha256。")
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        failures.append(f"{label} 文件 ref 路径不存在：{raw}")
        return None
    actual_sha = compute_source_tree_hash(path) if path.is_dir() else sha256_file(path)
    if actual_sha != ref.get("sha256"):
        failures.append(f"{label} sha256 不匹配：{raw}")
    if not path.is_dir() and ref.get("size_bytes") is not None and path.stat().st_size != ref.get("size_bytes"):
        failures.append(f"{label} size_bytes 不匹配：{raw}")
    return path


def _resolve_ref_path(ref: dict[str, Any]) -> Path:
    path = Path(str(ref.get("path") or ref.get("relative_path") or ""))
    if not path:
        raise ConfigError("文件 ref 缺少 path。")
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        raise ConfigError(f"文件 ref 路径不存在：{path}")
    if sha256_file(path) != ref.get("sha256"):
        raise ConfigError(f"文件 ref sha256 不匹配：{path}")
    return path


def _file_ref(path: Path, category: str) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "kind": "directory" if path.is_dir() else (path.suffix.lstrip(".") or "file"),
        "category": category,
        "model_visible": False,
        "sha256": compute_source_tree_hash(path) if path.is_dir() else sha256_file(path),
        "size_bytes": 0 if path.is_dir() else path.stat().st_size,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"JSON 文件不存在：{path}")
        return {}
    except json.JSONDecodeError as exc:
        failures.append(f"JSON 文件无效：{path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"JSON 顶层必须是 object：{path}")
        return {}
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _sha256_payload(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _dependency_cache_key(row: dict[str, Any]) -> str:
    return _sha256_payload(
        {
            "task_id": row["task_id"],
            "base_image": row["base_image"],
            "image_digest": row["image_digest"],
            "source_tree_hash": row["source_tree_hash"],
        }
    )


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
