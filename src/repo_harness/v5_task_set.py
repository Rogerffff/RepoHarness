"""V5 Stage 2 task set builders."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V5_ADAPTER_VISIBLE_TASK_INPUT_MANIFEST_VERSION,
    V5_EVALUATOR_ONLY_EVIDENCE_MANIFEST_VERSION,
    V5_PR_ISSUE_TASK_MANIFEST_VERSION,
    V5_SWEBENCH_LIKE_SUBSET_MANIFEST_VERSION,
    V5_TASK_CONSTRUCTION_REPORT_VERSION,
    V5_TASK_DEFINITION_VERSION,
    V5_TASK_DIVERSITY_REPORT_VERSION,
    V5_TASK_INVENTORY_REPORT_VERSION,
    V5_TASK_SET_MANIFEST_VERSION,
    V5_TASK_STABILITY_REPORT_VERSION,
    V5_TASK_VISIBILITY_SCAN_REPORT_VERSION,
)
from repo_harness.v5_evidence import (
    V5_FORBIDDEN_ADAPTER_VISIBLE_MARKERS,
    V5_PARTIAL_THRESHOLD_STATUS,
    _builder_command_log_entry,
    _evidence_ref,
    _hash_path,
    _utc_timestamp,
    _write_json,
    _write_jsonl,
)


V5_STAGE2A_OUTPUT_NAMES = (
    "v5_task_inventory_report.json",
    "v5_task_set_manifest.json",
    "v5_task_construction_report.json",
    "v5_swebench_like_subset_manifest.json",
    "v5_pr_issue_task_manifest.json",
    "v5_task_diversity_report.json",
    "v5_task_stability_report.json",
    "v5_task_visibility_scan_report.json",
    "v5_adapter_visible_task_input_manifest.json",
    "v5_evaluator_only_evidence_manifest.json",
    "build_v5_task_set_command_log_entry.json",
    "v5_stage2a_command_log.jsonl",
)

V5_STAGE2A_REQUIRED_TASK_FIELDS = (
    "task_id",
    "task_family",
    "source_kind",
    "repo_url_or_archive_id",
    "base_commit",
    "source_archive_sha256",
    "source_tree_hash",
    "task_input_hash",
    "adapter_visible_input_ref",
    "evaluator_only_evidence_ref",
    "baseline_verifier_plan_ref",
    "final_verifier_plan_ref",
    "fail_to_pass_evidence_ref",
    "pass_to_pass_evidence_ref",
    "flaky_probe_report_ref",
    "license_provenance_ref",
    "dependency_cache_ref",
    "environment_stability_ref",
    "contamination_scan_ref",
    "visibility_scan_ref",
    "task_diversity_ref",
)


def build_task_set_manifest(
    *,
    preflight_input_binding: str | Path,
    adapter_visible_task_draft: str | Path,
    evaluator_only_evidence_manifest: str | Path,
    run_matrix_preflight_manifest: str | Path,
    task_selection_preflight_report: str | Path,
    visibility_scan_report: str | Path,
    flaky_probe_report: str | Path,
    source_materialization_reports: list[str | Path],
    output_dir: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build the Stage 2A formal task set from explicit preflight artifacts."""

    root = Path(output_dir)
    if fail_if_output_exists:
        existing = [root / name for name in V5_STAGE2A_OUTPUT_NAMES if (root / name).exists()]
        task_definition_root = root / "task_definitions"
        adapter_input_root = root / "adapter_visible_task_inputs"
        if task_definition_root.exists() and any(task_definition_root.iterdir()):
            existing.append(task_definition_root)
        if adapter_input_root.exists() and any(adapter_input_root.iterdir()):
            existing.append(adapter_input_root)
        if existing:
            raise ConfigError(
                "V5 Stage 2A task set 输出已存在，不能覆盖旧 evidence："
                + ", ".join(path.as_posix() for path in existing)
            )
    root.mkdir(parents=True, exist_ok=True)

    binding_path = Path(preflight_input_binding)
    adapter_path = Path(adapter_visible_task_draft)
    evaluator_path = Path(evaluator_only_evidence_manifest)
    run_matrix_path = Path(run_matrix_preflight_manifest)
    selection_path = Path(task_selection_preflight_report)
    visibility_path = Path(visibility_scan_report)
    flaky_path = Path(flaky_probe_report)
    source_paths = [Path(path) for path in source_materialization_reports]

    binding = _read_json(binding_path)
    adapter_inputs = _read_jsonl(adapter_path)
    evaluator_manifest = _read_json(evaluator_path)
    run_matrix = _read_json(run_matrix_path)
    task_selection = _read_json(selection_path)
    visibility_scan = _read_json(visibility_path)
    flaky_probe = _read_json(flaky_path)
    source_entries = _source_entries_by_candidate(source_paths)

    _validate_stage2a_inputs(
        binding=binding,
        adapter_inputs=adapter_inputs,
        evaluator_manifest=evaluator_manifest,
        run_matrix=run_matrix,
        task_selection=task_selection,
        visibility_scan=visibility_scan,
        flaky_probe=flaky_probe,
        source_entries=source_entries,
    )

    task_definition_root = root / "task_definitions"
    adapter_input_root = root / "adapter_visible_task_inputs"
    task_definition_root.mkdir(parents=True, exist_ok=True)
    adapter_input_root.mkdir(parents=True, exist_ok=True)

    adapter_by_task = {str(item["task_id"]): item for item in adapter_inputs}
    flaky_by_candidate = {str(item.get("candidate_id")): item for item in flaky_probe.get("entries", [])}
    task_defs: list[dict[str, Any]] = []
    adapter_refs: list[dict[str, Any]] = []
    diversity_rows: list[dict[str, Any]] = []
    visibility_findings: list[dict[str, Any]] = []
    entries = sorted(run_matrix.get("entries", []), key=lambda item: str(item.get("task_id")))

    for entry in entries:
        task_id = str(entry["task_id"])
        candidate_id = str(entry["candidate_id"])
        adapter_input = _sanitized_adapter_input(adapter_by_task[task_id])
        adapter_file = adapter_input_root / f"{task_id}.json"
        _write_json(adapter_file, adapter_input)
        adapter_ref = _evidence_ref(
            adapter_file,
            kind="adapter_visible_task_input",
            purpose=f"Sanitized adapter-visible V5 input for {task_id}",
            visibility="model_visible",
            producer_command="build-v5-task-set",
            producer_stage="v5_stage2a_initial_task_set",
            inspect_command="inspect-v5-task-visibility",
            share_safe=True,
        )
        adapter_refs.append(adapter_ref)
        visibility_findings.extend(_adapter_visible_findings(task_id=task_id, adapter_input=adapter_input))

        source_entry = source_entries[candidate_id]
        source_archive_ref = _source_archive_ref(source_entry)
        source_tree_hash = str((entry.get("source_tree_hash") or {}).get("sha256") or source_entry.get("source_tree_hash"))
        source_file_count = int((entry.get("source_tree_hash") or {}).get("file_count") or 0)
        task_def = {
            "schema_version": V5_TASK_DEFINITION_VERSION,
            "task_id": task_id,
            "candidate_id": candidate_id,
            "task_family": adapter_input["task_family"],
            "source_kind": _source_kind(entry),
            "track": entry.get("track"),
            "repository": entry.get("repository"),
            "repo_url_or_archive_id": source_entry.get("repository_url") or f"https://github.com/{entry.get('repository')}",
            "base_commit": source_entry.get("base_commit"),
            "resolved_commit": source_entry.get("resolved_commit"),
            "source_archive_sha256": source_entry.get("archive_sha256") or source_archive_ref.get("sha256"),
            "source_archive_ref": source_archive_ref,
            "source_tree_hash": source_tree_hash,
            "source_tree_file_count": source_file_count,
            "task_input_hash": sha256_file(adapter_file),
            "adapter_visible_input_ref": adapter_ref,
            "evaluator_only_evidence_ref": _evidence_ref(
                evaluator_path,
                kind="evaluator_only_evidence_manifest",
                purpose=f"Evaluator-only evidence remains isolated for {task_id}",
                visibility="evaluator_only",
                producer_command="v5 preflight visibility pipeline",
                producer_stage="v5_preimplementation_input",
                inspect_command="inspect-v5-task-visibility",
            ),
            "baseline_verifier_plan_ref": _evidence_ref(
                _first_existing_path([entry.get("final_verifier_plan_ref")]),
                kind="baseline_verifier_plan",
                purpose=f"Baseline verifier evidence source for {task_id}",
                visibility="evaluator_only",
                producer_command="v5 verifier preflight",
                producer_stage="v5_preimplementation_input",
                inspect_command="inspect-v5-task-set",
            ),
            "final_verifier_plan_ref": _evidence_ref(
                _first_existing_path([entry.get("final_verifier_plan_ref")]),
                kind="final_verifier_plan",
                purpose=f"Final verifier evidence source for {task_id}",
                visibility="evaluator_only",
                producer_command="v5 verifier preflight",
                producer_stage="v5_preimplementation_input",
                inspect_command="inspect-v5-task-set",
            ),
            "fail_to_pass_evidence_ref": _evidence_ref(
                flaky_path,
                kind="fail_to_pass_evidence",
                purpose=f"Fail-to-pass stability evidence for {task_id}",
                visibility="evaluator_only",
                producer_command="v5 flaky probe",
                producer_stage="v5_preimplementation_input",
                inspect_command="inspect-v5-task-set",
            ),
            "pass_to_pass_evidence_ref": _evidence_ref(
                flaky_path,
                kind="pass_to_pass_evidence",
                purpose=f"Pass-to-pass stability evidence for {task_id}",
                visibility="evaluator_only",
                producer_command="v5 flaky probe",
                producer_stage="v5_preimplementation_input",
                inspect_command="inspect-v5-task-set",
            ),
            "flaky_probe_report_ref": _evidence_ref(
                flaky_path,
                kind="flaky_probe_report",
                purpose=f"Flaky probe evidence for {task_id}",
                visibility="audit_only",
                producer_command="v5 flaky probe",
                producer_stage="v5_preimplementation_input",
                inspect_command="inspect-v5-task-set",
            ),
            "license_provenance_ref": _evidence_ref(
                _source_report_path_for_candidate(source_paths, source_entry),
                kind="license_provenance",
                purpose=f"License provenance source materialization evidence for {task_id}",
                visibility="audit_only",
                producer_command="v5 source materialization preflight",
                producer_stage="v5_preimplementation_input",
                inspect_command="inspect-v5-task-set",
            ),
            "dependency_cache_ref": _evidence_ref(
                _first_existing_path([entry.get("dependency_snapshot_ref")]),
                kind="dependency_snapshot",
                purpose=f"Dependency snapshot for {task_id}",
                visibility="audit_only",
                producer_command="v5 dependency and verifier preflight",
                producer_stage="v5_preimplementation_input",
                inspect_command="inspect-v5-task-set",
            ),
            "environment_stability_ref": _evidence_ref(
                flaky_path,
                kind="environment_stability",
                purpose=f"Environment stability evidence for {task_id}",
                visibility="audit_only",
                producer_command="v5 flaky probe",
                producer_stage="v5_preimplementation_input",
                inspect_command="inspect-v5-task-set",
            ),
            "contamination_scan_ref": _evidence_ref(
                visibility_path,
                kind="contamination_scan",
                purpose=f"Visibility and contamination scan for {task_id}",
                visibility="audit_only",
                producer_command="v5 visibility probe",
                producer_stage="v5_preimplementation_input",
                inspect_command="inspect-v5-task-visibility",
            ),
            "visibility_scan_ref": _evidence_ref(
                visibility_path,
                kind="visibility_scan",
                purpose=f"Visibility scan source for {task_id}",
                visibility="audit_only",
                producer_command="v5 visibility probe",
                producer_stage="v5_preimplementation_input",
                inspect_command="inspect-v5-task-visibility",
            ),
            "task_diversity_ref": {},
            "initial_batch_freeze_ready": entry.get("freeze_ready") is True,
            "accepted_auditable": entry.get("freeze_ready") is True,
            "agent_run_ready": entry.get("agent_run_ready") is True,
            "comparison_ready": entry.get("comparison_ready") is True,
            "recommended_v5_role": entry.get("recommended_v5_role"),
            "environment_id": entry.get("environment_id"),
            "tool_policy_id": entry.get("tool_policy_id"),
            "context_policy_id": entry.get("context_policy_id"),
            "budget_policy_id": entry.get("budget_policy_id"),
            "scaffold_id": entry.get("scaffold_id"),
            "flaky_status": (flaky_by_candidate.get(candidate_id) or {}).get("status"),
        }
        task_defs.append(task_def)
        diversity_rows.append(
            {
                "task_id": task_id,
                "candidate_id": candidate_id,
                "ecosystem": entry.get("ecosystem"),
                "repository": entry.get("repository"),
                "source_kind": task_def["source_kind"],
                "source_tree_file_count": source_file_count,
                "task_family": task_def["task_family"],
                "recommended_v5_role": entry.get("recommended_v5_role"),
                "comparison_ready": entry.get("comparison_ready") is True,
                "demo_ready": entry.get("demo_ready") is True,
            }
        )

    diversity_report_path = root / "v5_task_diversity_report.json"
    diversity_report = _diversity_report(diversity_rows)
    _write_json(diversity_report_path, diversity_report)
    diversity_ref = _evidence_ref(
        diversity_report_path,
        kind="task_diversity_report",
        purpose="V5 Stage 2A task diversity report",
        visibility="audit_only",
        producer_command="build-v5-task-set",
        producer_stage="v5_stage2a_initial_task_set",
        inspect_command="inspect-v5-task-set",
    )

    task_definition_refs = []
    for task_def in task_defs:
        task_def["task_diversity_ref"] = diversity_ref
        task_path = task_definition_root / f"{task_def['task_id']}.json"
        _write_json(task_path, task_def)
        task_definition_refs.append(
            _evidence_ref(
                task_path,
                kind="v5_task_definition",
                purpose=f"Formal V5 task definition for {task_def['task_id']}",
                visibility="audit_only",
                producer_command="build-v5-task-set",
                producer_stage="v5_stage2a_initial_task_set",
                inspect_command="inspect-v5-task-set",
            )
        )

    inventory_report_path = root / "v5_task_inventory_report.json"
    visibility_report_path = root / "v5_task_visibility_scan_report.json"
    construction_report_path = root / "v5_task_construction_report.json"
    swebench_manifest_path = root / "v5_swebench_like_subset_manifest.json"
    pr_issue_manifest_path = root / "v5_pr_issue_task_manifest.json"
    stability_report_path = root / "v5_task_stability_report.json"
    adapter_manifest_path = root / "v5_adapter_visible_task_input_manifest.json"
    evaluator_manifest_path = root / "v5_evaluator_only_evidence_manifest.json"
    task_set_manifest_path = root / "v5_task_set_manifest.json"

    counts = _task_counts(task_defs)
    inventory_report = _inventory_report(counts=counts, task_defs=task_defs, task_definition_refs=task_definition_refs)
    _write_json(inventory_report_path, inventory_report)
    _write_json(
        visibility_report_path,
        _task_visibility_report(
            visibility_scan=visibility_scan,
            visibility_scan_path=visibility_path,
            adapter_path=adapter_path,
            adapter_refs=adapter_refs,
            evaluator_path=evaluator_path,
            task_definition_refs=task_definition_refs,
            findings=visibility_findings,
        ),
    )
    task_set_manifest = _task_set_manifest(
        counts=counts,
        task_definition_refs=task_definition_refs,
        inventory_report_path=inventory_report_path,
        visibility_report_path=visibility_report_path,
    )
    _write_json(task_set_manifest_path, task_set_manifest)
    _write_json(swebench_manifest_path, _source_subset_manifest(task_defs, source_kind="swebench_like_anchor"))
    _write_json(pr_issue_manifest_path, _source_subset_manifest(task_defs, source_kind="pr_issue_flow"))
    _write_json(stability_report_path, _stability_report(flaky_probe=flaky_probe, task_defs=task_defs))
    _write_json(adapter_manifest_path, _adapter_visible_manifest(adapter_refs=adapter_refs, source_path=adapter_path))
    _write_json(evaluator_manifest_path, _evaluator_only_manifest(source_path=evaluator_path, source_payload=evaluator_manifest))
    _write_json(
        construction_report_path,
        _construction_report(
            input_paths=[
                binding_path,
                adapter_path,
                evaluator_path,
                run_matrix_path,
                selection_path,
                visibility_path,
                flaky_path,
                *source_paths,
            ],
            output_paths=[
                inventory_report_path,
                task_set_manifest_path,
                swebench_manifest_path,
                pr_issue_manifest_path,
                visibility_report_path,
                diversity_report_path,
                stability_report_path,
                adapter_manifest_path,
                evaluator_manifest_path,
            ],
        ),
    )

    command_entry = _builder_command_log_entry(
        command_name="build-v5-task-set",
        input_paths=[
            binding_path,
            adapter_path,
            evaluator_path,
            run_matrix_path,
            selection_path,
            visibility_path,
            flaky_path,
            *source_paths,
        ],
        output_paths=[
            inventory_report_path,
            task_set_manifest_path,
            construction_report_path,
            swebench_manifest_path,
            pr_issue_manifest_path,
            diversity_report_path,
            stability_report_path,
            visibility_report_path,
            adapter_manifest_path,
            evaluator_manifest_path,
            task_definition_root,
            adapter_input_root,
        ],
        producer_stage="v5_stage2a_initial_task_set",
    )
    command_entry_path = root / "build_v5_task_set_command_log_entry.json"
    command_log_path = root / "v5_stage2a_command_log.jsonl"
    _write_json(command_entry_path, command_entry)
    _write_jsonl(command_log_path, [command_entry])
    return task_set_manifest_path


def _validate_stage2a_inputs(
    *,
    binding: dict[str, Any],
    adapter_inputs: list[dict[str, Any]],
    evaluator_manifest: dict[str, Any],
    run_matrix: dict[str, Any],
    task_selection: dict[str, Any],
    visibility_scan: dict[str, Any],
    flaky_probe: dict[str, Any],
    source_entries: dict[str, dict[str, Any]],
) -> None:
    if binding.get("initial_candidate_count") != 10:
        raise ConfigError("Stage 2A 必须绑定当前 10 个 initial candidate。")
    if binding.get("accepted_counting_allowed") is not False:
        raise ConfigError("Stage 2A 不能把 preflight 输入直接计为 V5 final accepted task。")
    policy = binding.get("stage0_policy") or {}
    if policy.get("preflight_artifacts_do_not_count_as_final_v5_accepted_tasks") is not True:
        raise ConfigError("Stage 0 policy 必须禁止把 preflight artifact 直接计为 final V5 accepted task。")
    if run_matrix.get("candidate_count") != 10 or len(run_matrix.get("entries") or []) != 10:
        raise ConfigError("Stage 2A run matrix preflight manifest 必须包含 10 个候选。")
    if task_selection.get("status") != "initial_batch_freeze_ready_full_threshold_partial":
        raise ConfigError("Stage 2A task selection 必须保持 initial batch partial threshold 状态。")
    if visibility_scan.get("status") != "passed":
        raise ConfigError("Stage 2A visibility scan 输入必须通过。")
    for counter in (
        "model_visible_leak_count",
        "share_safe_violation_count",
        "raw_provider_content_leak_count",
        "credential_marker_leak_count",
        "trainable_payload_leak_count",
    ):
        if visibility_scan.get(counter, 0) != 0:
            raise ConfigError(f"Stage 2A visibility scan 输入计数必须为 0：{counter}")
    if flaky_probe.get("stable_count") != 10 or flaky_probe.get("flaky_suspected_count") != 0:
        raise ConfigError("Stage 2A flaky probe 输入必须是 10 stable / 0 flaky suspected。")
    adapter_task_ids = {str(item.get("task_id")) for item in adapter_inputs}
    matrix_task_ids = {str(item.get("task_id")) for item in run_matrix.get("entries") or []}
    if adapter_task_ids != matrix_task_ids:
        raise ConfigError("adapter-visible task drafts 必须和 run matrix task ids 完全一致。")
    missing_source = sorted(str(item.get("candidate_id")) for item in run_matrix.get("entries") or [] if str(item.get("candidate_id")) not in source_entries)
    if missing_source:
        raise ConfigError("source materialization report 缺少候选：" + ", ".join(missing_source))
    evaluator_visibility = str(evaluator_manifest.get("visibility") or "")
    if evaluator_manifest.get("share_safe") is not False or not evaluator_visibility.startswith("evaluator_only"):
        raise ConfigError("evaluator-only evidence manifest 必须保持 evaluator_only 且不能 share_safe。")


def _source_entries_by_candidate(source_paths: list[Path]) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for path in source_paths:
        payload = _read_json(path)
        raw_entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []
        for entry in raw_entries:
            if not isinstance(entry, dict):
                continue
            candidate_id = str(entry.get("candidate_id") or "")
            if candidate_id:
                entries[candidate_id] = {**entry, "_source_report_path": path.as_posix()}
    return entries


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"输入文件不存在：{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ConfigError(f"输入 JSON 顶层必须是 object：{path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ConfigError(f"输入文件不存在：{path}")
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ConfigError(f"JSONL 第 {index} 行顶层必须是 object：{path}")
        rows.append(payload)
    return rows


def _sanitized_adapter_input(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload.get("schema_version"),
        "task_id": payload["task_id"],
        "task_family": payload["task_family"],
        "ecosystem": payload.get("ecosystem"),
        "repository": payload.get("repository"),
        "task_statement": payload["task_statement"],
        "visible_constraints": list(payload.get("visible_constraints") or []),
        "visibility": "model_visible",
        "share_safe": True,
    }


def _adapter_visible_findings(*, task_id: str, adapter_input: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(adapter_input, ensure_ascii=False).lower()
    findings = []
    for marker in V5_FORBIDDEN_ADAPTER_VISIBLE_MARKERS:
        if marker.lower() in text:
            findings.append(
                {
                    "task_id": task_id,
                    "finding_type": "adapter_visible_forbidden_marker",
                    "severity": "critical",
                    "marker": marker,
                    "message": f"adapter-visible input contains forbidden marker: {marker}",
                }
            )
    return findings


def _source_kind(entry: dict[str, Any]) -> str:
    track = str(entry.get("track") or "")
    if track == "pr_issue":
        return "pr_issue_flow"
    if track == "swebench_like":
        return "swebench_like_anchor"
    return track or "unknown"


def _source_archive_ref(source_entry: dict[str, Any]) -> dict[str, Any]:
    source_ref = source_entry.get("source_archive_ref") or source_entry.get("primary_archive_ref")
    path = Path(str((source_ref or {}).get("path") or source_entry.get("archive_path")))
    if not path.is_absolute():
        path = Path.cwd() / path
    return _evidence_ref(
        path,
        kind="source_archive",
        purpose=f"Deterministic source archive for {source_entry.get('candidate_id')}",
        visibility="audit_only",
        producer_command="v5 source materialization preflight",
        producer_stage="v5_preimplementation_input",
        inspect_command="inspect-v5-task-set",
    )


def _first_existing_path(values: list[Any]) -> Path:
    for value in values:
        if not value:
            continue
        path = Path(str(value))
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.exists():
            return path
    raise ConfigError("缺少可绑定的 evidence path。")


def _source_report_path_for_candidate(source_paths: list[Path], source_entry: dict[str, Any]) -> Path:
    raw = source_entry.get("_source_report_path")
    if raw:
        return Path(str(raw))
    return source_paths[0]


def _task_counts(task_defs: list[dict[str, Any]]) -> dict[str, int]:
    accepted = [task for task in task_defs if task.get("accepted_auditable") is True]
    return {
        "accepted_auditable_task_count": len(accepted),
        "pr_issue_task_count": sum(1 for task in accepted if task.get("source_kind") == "pr_issue_flow"),
        "swebench_like_anchor_count": sum(1 for task in accepted if task.get("source_kind") == "swebench_like_anchor"),
        "agent_run_ready_count": sum(1 for task in accepted if task.get("agent_run_ready") is True),
        "comparison_ready_count": sum(1 for task in accepted if task.get("comparison_ready") is True),
    }


def _inventory_report(
    *,
    counts: dict[str, int],
    task_defs: list[dict[str, Any]],
    task_definition_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": V5_TASK_INVENTORY_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        **counts,
        "strict_inventory_gate": "blocked_pending_stage2b",
        "full_v5_threshold_status": V5_PARTIAL_THRESHOLD_STATUS,
        "source_mix": {
            "pr_issue": counts["pr_issue_task_count"],
            "swebench_like_anchor": counts["swebench_like_anchor_count"],
        },
        "initial_batch_task_count": len(task_defs),
        "initial_batch_freeze_ready_count": sum(1 for task in task_defs if task.get("initial_batch_freeze_ready") is True),
        "supplemental_required": True,
        "supplemental_required_reason": "Stage 2A contains 10 total / 6 PR-issue tasks; Stage 2B must add 2 PR / issue tasks or formal scope change.",
        "claims_full_inventory_gate": False,
        "task_definition_refs": task_definition_refs,
        "status": "passed",
    }


def _task_set_manifest(
    *,
    counts: dict[str, int],
    task_definition_refs: list[dict[str, Any]],
    inventory_report_path: Path,
    visibility_report_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": V5_TASK_SET_MANIFEST_VERSION,
        "created_at": _utc_timestamp(),
        "task_set_stage": "stage2a_initial_10",
        **counts,
        "strict_inventory_gate": "blocked_pending_stage2b",
        "full_v5_threshold_status": V5_PARTIAL_THRESHOLD_STATUS,
        "initial_batch_task_count": len(task_definition_refs),
        "initial_batch_freeze_ready_count": len(task_definition_refs),
        "supplemental_required": True,
        "supplemental_required_reason": "Stage 2B must add 2 PR / issue candidates before Stage 3 real provider run matrix exit.",
        "claims_full_inventory_gate": False,
        "task_refs": task_definition_refs,
        "inventory_report_ref": _evidence_ref(
            inventory_report_path,
            kind="v5_task_inventory_report",
            purpose="V5 Stage 2A task inventory report",
            visibility="audit_only",
            producer_command="build-v5-task-set",
            producer_stage="v5_stage2a_initial_task_set",
            inspect_command="inspect-v5-task-set",
        ),
        "visibility_scan_ref": _evidence_ref(
            visibility_report_path,
            kind="v5_task_visibility_scan_report",
            purpose="V5 Stage 2A task visibility scan report",
            visibility="audit_only",
            producer_command="build-v5-task-set",
            producer_stage="v5_stage2a_initial_task_set",
            inspect_command="inspect-v5-task-visibility",
        ),
        "status": "passed",
    }


def _task_visibility_report(
    *,
    visibility_scan: dict[str, Any],
    visibility_scan_path: Path,
    adapter_path: Path,
    adapter_refs: list[dict[str, Any]],
    evaluator_path: Path,
    task_definition_refs: list[dict[str, Any]],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    model_visible_leak_count = int(visibility_scan.get("model_visible_leak_count", 0)) + len(findings)
    share_safe_violation_count = int(visibility_scan.get("share_safe_violation_count", 0))
    trainable_payload_contamination_count = int(visibility_scan.get("trainable_payload_leak_count", 0))
    status = "passed" if model_visible_leak_count == 0 and share_safe_violation_count == 0 and trainable_payload_contamination_count == 0 else "failed"
    return {
        "schema_version": V5_TASK_VISIBILITY_SCAN_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "scan_scope_refs": [
            _evidence_ref(adapter_path, kind="adapter_visible_task_draft", purpose="Preflight adapter-visible task draft", visibility="audit_only", producer_command="v5 visibility probe", producer_stage="v5_preimplementation_input", inspect_command="inspect-v5-task-visibility"),
            _evidence_ref(evaluator_path, kind="evaluator_only_evidence_manifest", purpose="Evaluator-only evidence isolation manifest", visibility="evaluator_only", producer_command="v5 visibility probe", producer_stage="v5_preimplementation_input", inspect_command="inspect-v5-task-visibility"),
            _evidence_ref(visibility_scan_path, kind="preflight_visibility_scan_report", purpose="Preflight visibility scan report", visibility="audit_only", producer_command="v5 visibility probe", producer_stage="v5_preimplementation_input", inspect_command="inspect-v5-task-visibility"),
        ],
        "adapter_visible_input_refs": adapter_refs,
        "task_definition_refs": task_definition_refs,
        "model_visible_leak_count": model_visible_leak_count,
        "share_safe_violation_count": share_safe_violation_count,
        "trainable_payload_contamination_count": trainable_payload_contamination_count,
        "raw_provider_content_leak_count": int(visibility_scan.get("raw_provider_content_leak_count", 0)),
        "credential_marker_leak_count": int(visibility_scan.get("credential_marker_leak_count", 0)),
        "evaluator_only_raw_content_copied_count": int(visibility_scan.get("evaluator_only_raw_content_copied_count", 0)),
        "findings": findings,
        "status": status,
    }


def _construction_report(*, input_paths: list[Path], output_paths: list[Path]) -> dict[str, Any]:
    return {
        "schema_version": V5_TASK_CONSTRUCTION_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "stage": "stage2a_initial_10",
        "input_refs": [
            _evidence_ref(path, kind="task_set_builder_input", purpose="V5 Stage 2A explicit builder input", visibility="audit_only", producer_command="external", producer_stage="v5_stage2a_initial_task_set", inspect_command="inspect-v5-task-set")
            for path in input_paths
        ],
        "output_refs": [
            _evidence_ref(path, kind="task_set_builder_output", purpose="V5 Stage 2A builder output", visibility="audit_only", producer_command="build-v5-task-set", producer_stage="v5_stage2a_initial_task_set", inspect_command="inspect-v5-task-set")
            for path in output_paths
        ],
        "latest_run_discovery_used": False,
        "preflight_artifacts_count_as_final_accepted_tasks": False,
        "provider_api_called": False,
        "agent_run_started": False,
        "status": "passed",
    }


def _source_subset_manifest(task_defs: list[dict[str, Any]], *, source_kind: str) -> dict[str, Any]:
    version = V5_PR_ISSUE_TASK_MANIFEST_VERSION if source_kind == "pr_issue_flow" else V5_SWEBENCH_LIKE_SUBSET_MANIFEST_VERSION
    tasks = [task for task in task_defs if task.get("source_kind") == source_kind]
    return {
        "schema_version": version,
        "created_at": _utc_timestamp(),
        "source_kind": source_kind,
        "task_count": len(tasks),
        "task_ids": [task["task_id"] for task in tasks],
        "candidate_ids": [task["candidate_id"] for task in tasks],
        "accepted_auditable_count": sum(1 for task in tasks if task.get("accepted_auditable") is True),
        "status": "passed",
    }


def _diversity_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ecosystem_counts = Counter(str(row.get("ecosystem")) for row in rows)
    source_kind_counts = Counter(str(row.get("source_kind")) for row in rows)
    task_family_counts = Counter(str(row.get("task_family")) for row in rows)
    return {
        "schema_version": V5_TASK_DIVERSITY_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "task_count": len(rows),
        "ecosystem_counts": dict(sorted(ecosystem_counts.items())),
        "source_kind_counts": dict(sorted(source_kind_counts.items())),
        "task_family_counts": dict(sorted(task_family_counts.items())),
        "repository_count": len({row.get("repository") for row in rows}),
        "large_repository_task_count": sum(1 for row in rows if int(row.get("source_tree_file_count") or 0) >= 1000),
        "comparison_ready_count": sum(1 for row in rows if row.get("comparison_ready") is True),
        "demo_ready_count": sum(1 for row in rows if row.get("demo_ready") is True),
        "rows": rows,
        "status": "passed",
    }


def _stability_report(*, flaky_probe: dict[str, Any], task_defs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": V5_TASK_STABILITY_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "task_count": len(task_defs),
        "stable_count": flaky_probe.get("stable_count"),
        "flaky_suspected_count": flaky_probe.get("flaky_suspected_count"),
        "attempt_count_per_side": flaky_probe.get("attempt_count_per_side"),
        "unstable_accepted_task_count": 0,
        "status": "passed",
    }


def _adapter_visible_manifest(*, adapter_refs: list[dict[str, Any]], source_path: Path) -> dict[str, Any]:
    return {
        "schema_version": V5_ADAPTER_VISIBLE_TASK_INPUT_MANIFEST_VERSION,
        "created_at": _utc_timestamp(),
        "source_ref": _evidence_ref(source_path, kind="adapter_visible_task_draft", purpose="Preflight adapter-visible source JSONL", visibility="audit_only", producer_command="v5 visibility probe", producer_stage="v5_preimplementation_input", inspect_command="inspect-v5-task-visibility"),
        "adapter_visible_input_refs": adapter_refs,
        "task_count": len(adapter_refs),
        "visibility": "model_visible",
        "share_safe": True,
        "status": "passed",
    }


def _evaluator_only_manifest(*, source_path: Path, source_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": V5_EVALUATOR_ONLY_EVIDENCE_MANIFEST_VERSION,
        "created_at": _utc_timestamp(),
        "source_ref": _evidence_ref(source_path, kind="evaluator_only_evidence_manifest", purpose="Preflight evaluator-only manifest", visibility="evaluator_only", producer_command="v5 visibility probe", producer_stage="v5_preimplementation_input", inspect_command="inspect-v5-task-visibility"),
        "source_visibility": source_payload.get("visibility"),
        "source_share_safe": source_payload.get("share_safe"),
        "policy": source_payload.get("policy"),
        "adapter_visible_copy_allowed": False,
        "public_safe_copy_allowed": False,
        "status": "passed",
    }
