"""V5 Stage 2 task set builders."""

from __future__ import annotations

import json
import subprocess
import tarfile
import tempfile
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V5_ADAPTER_VISIBLE_TASK_INPUT_MANIFEST_VERSION,
    V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V5_EVALUATOR_ONLY_EVIDENCE_MANIFEST_VERSION,
    V5_PR_ISSUE_TASK_MANIFEST_VERSION,
    V5_SWEBENCH_LIKE_SUBSET_MANIFEST_VERSION,
    V5_SUPPLEMENTAL_PR_ISSUE_CANDIDATE_REPORT_VERSION,
    V5_SUPPLEMENTAL_PR_ISSUE_PROBE_REPORT_VERSION,
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

V5_STAGE2B_SUPPLEMENTAL_OUTPUT_NAMES = (
    "v5_supplemental_pr_issue_candidate_report.json",
    "v5_supplemental_pr_issue_command_log.jsonl",
    "build_v5_supplemental_pr_issue_candidates_command_log_entry.json",
)

V5_STAGE2B_MERGE_OUTPUT_NAMES = (
    "v5_task_set_manifest.json",
    "v5_task_inventory_report.json",
    "v5_task_visibility_scan_report.json",
    "merge_v5_task_set_command_log_entry.json",
    "v5_stage2b_merge_command_log.jsonl",
)


@dataclass(frozen=True)
class SupplementalCandidateSpec:
    candidate_id: str
    task_id: str
    repository: str
    repo_url: str
    base_commit: str
    resolved_commit: str
    title: str
    ecosystem: str
    task_family: str
    task_statement: str
    visible_constraints: tuple[str, ...]
    test_patch_paths: tuple[str, ...]
    dependency_install_command: tuple[str, ...]
    verifier_command: tuple[str, ...]
    environment_id: str = "docker_based_python_v5_stage2b_probe"
    tool_policy_id: str = "v5_stage2b_read_write_shell_no_provider"
    context_policy_id: str = "v5_stage2b_sanitized_task_context"
    budget_policy_id: str = "v5_stage2b_probe_budget"
    scaffold_id: str = "repo_harness_default_single_agent"


V5_DEFAULT_SUPPLEMENTAL_CANDIDATE_ORDER = (
    "pallets/click#3364",
    "python-attrs/attrs#1428",
    "pypa/packaging#1124",
    "hynek/structlog#620",
    "chalk/chalk#335",
    "sindresorhus/execa#1176",
    "clap-rs/clap#6340",
)


DEFAULT_SUPPLEMENTAL_CANDIDATES: dict[str, SupplementalCandidateSpec] = {
    "pallets/click#3364": SupplementalCandidateSpec(
        candidate_id="pallets/click#3364",
        task_id="v5_pr_issue_click_3364",
        repository="pallets/click",
        repo_url="https://github.com/pallets/click.git",
        base_commit="8a2b48901a08b3d2ec3a9bbd151948a9765368c6",
        resolved_commit="c8da1fcc2cb4523c1fb5bef7f0ca82394dde1efd",
        title="Split string default_map values for multi-value Click parameters",
        ecosystem="python",
        task_family="pr_issue_default_value_parsing",
        task_statement=(
            "In the Click repository, update default_map handling so a string value used for a "
            "multi-value option is split the same way an environment variable value is split. "
            "Keep existing behavior for already-structured list or tuple values and for explicit "
            "command line arguments."
        ),
        visible_constraints=(
            "Use the fixed repository revision and the provided final verifier command.",
            "Use only the sanitized task statement and repository workspace as model-visible input; audit-only materials stay outside the prompt.",
        ),
        test_patch_paths=("tests/test_defaults.py",),
        dependency_install_command=("python", "-m", "pip", "install", "-q", "-e", ".", "pytest"),
        verifier_command=("python", "-m", "pytest", "-q", "tests/test_defaults.py::test_default_map_nargs"),
    ),
    "python-attrs/attrs#1428": SupplementalCandidateSpec(
        candidate_id="python-attrs/attrs#1428",
        task_id="v5_pr_issue_attrs_1428",
        repository="python-attrs/attrs",
        repo_url="https://github.com/python-attrs/attrs.git",
        base_commit="94caa57142c057ce52504cdf239ae0ed3168f9b5",
        resolved_commit="937b1e232803cc4ec9b9375ef525fc57c24ec498",
        title="Pass user supplied init values to attrs pre-init hooks",
        ecosystem="python",
        task_family="pr_issue_init_hook_argument_flow",
        task_statement=(
            "In the attrs repository, ensure __attrs_pre_init__ receives the values supplied "
            "to __init__ for positional, defaulted, factory-backed, keyword-only, and "
            "keyword-only defaulted attributes."
        ),
        visible_constraints=(
            "Use the fixed repository revision and the provided final verifier command.",
            "Use only the sanitized task statement and repository workspace as model-visible input; audit-only materials stay outside the prompt.",
        ),
        test_patch_paths=("tests/test_make.py",),
        dependency_install_command=("python", "-m", "pip", "install", "-q", "-e", ".", "pytest", "hypothesis"),
        verifier_command=(
            "python",
            "-m",
            "pytest",
            "-q",
            "tests/test_make.py::TestAttributes::test_pre_init_with_mixture_of_defaults_and_kw_only",
        ),
    ),
    "pypa/packaging#1124": SupplementalCandidateSpec(
        candidate_id="pypa/packaging#1124",
        task_id="v5_pr_issue_packaging_1124",
        repository="pypa/packaging",
        repo_url="https://github.com/pypa/packaging.git",
        base_commit="e9385363dcbdc4494cd1b2438e1f945b42a49422",
        resolved_commit="69307a312b3e4a3d989fd46abc6cbc0acf70adba",
        title="Packaging PR issue supplemental fallback",
        ecosystem="python",
        task_family="pr_issue_packaging_fallback",
        task_statement="Resolve the fixed packaging task described by the sanitized V5 supplemental candidate metadata.",
        visible_constraints=("Use only sanitized task metadata and the fixed verifier command.",),
        test_patch_paths=("tests",),
        dependency_install_command=("python", "-m", "pip", "install", "-q", "-e", ".", "pytest"),
        verifier_command=("python", "-m", "pytest", "-q"),
    ),
    "hynek/structlog#620": SupplementalCandidateSpec(
        candidate_id="hynek/structlog#620",
        task_id="v5_pr_issue_structlog_620",
        repository="hynek/structlog",
        repo_url="https://github.com/hynek/structlog.git",
        base_commit="767ec8b9a196263bf9d8addcd4cb031433a49d4b",
        resolved_commit="b16e08f0c2989be813b666c62e633a70e59cfb42",
        title="Structlog PR issue supplemental fallback",
        ecosystem="python",
        task_family="pr_issue_structlog_fallback",
        task_statement="Resolve the fixed structlog task described by the sanitized V5 supplemental candidate metadata.",
        visible_constraints=("Use only sanitized task metadata and the fixed verifier command.",),
        test_patch_paths=("tests",),
        dependency_install_command=("python", "-m", "pip", "install", "-q", "-e", ".", "pytest"),
        verifier_command=("python", "-m", "pytest", "-q"),
    ),
    "chalk/chalk#335": SupplementalCandidateSpec(
        candidate_id="chalk/chalk#335",
        task_id="v5_pr_issue_chalk_335",
        repository="chalk/chalk",
        repo_url="https://github.com/chalk/chalk.git",
        base_commit="c25c32a25f4315c1f7ee21cc7b36b497c4f0212a",
        resolved_commit="87156ce8e2696a6002a51fbd1168e43eb9c70ce4",
        title="Chalk JavaScript smoke fallback",
        ecosystem="javascript",
        task_family="pr_issue_javascript_smoke_fallback",
        task_statement="Resolve the fixed chalk task described by the sanitized V5 supplemental candidate metadata.",
        visible_constraints=("Use only sanitized task metadata and the fixed verifier command.",),
        test_patch_paths=("test", "tests"),
        dependency_install_command=("npm", "install"),
        verifier_command=("npm", "test"),
    ),
    "sindresorhus/execa#1176": SupplementalCandidateSpec(
        candidate_id="sindresorhus/execa#1176",
        task_id="v5_pr_issue_execa_1176",
        repository="sindresorhus/execa",
        repo_url="https://github.com/sindresorhus/execa.git",
        base_commit="c8cff27a47b6e6f1cfbfec2bf7fa9dcd08cefed1",
        resolved_commit="2aa3b0ceeb76bc9bd5e4e4789d965cc483dba185",
        title="Execa JavaScript supplemental fallback",
        ecosystem="javascript",
        task_family="pr_issue_javascript_process_fallback",
        task_statement="Resolve the fixed execa task described by the sanitized V5 supplemental candidate metadata.",
        visible_constraints=("Use only sanitized task metadata and the fixed verifier command.",),
        test_patch_paths=("test", "tests"),
        dependency_install_command=("npm", "install"),
        verifier_command=("npm", "test"),
    ),
    "clap-rs/clap#6340": SupplementalCandidateSpec(
        candidate_id="clap-rs/clap#6340",
        task_id="v5_pr_issue_clap_6340",
        repository="clap-rs/clap",
        repo_url="https://github.com/clap-rs/clap.git",
        base_commit="14202755e52802a3d294c4ceeadd703d24b21fe6",
        resolved_commit="2b3ddd0294a147d1eda917cb303243bcde0c12ee",
        title="Clap Rust diagnostic fallback",
        ecosystem="rust",
        task_family="pr_issue_rust_diagnostic_fallback",
        task_statement="Resolve the fixed clap task described by the sanitized V5 supplemental candidate metadata.",
        visible_constraints=("Use only sanitized task metadata and the fixed verifier command.",),
        test_patch_paths=("tests", "clap_builder/tests", "clap_complete/tests"),
        dependency_install_command=("cargo", "fetch"),
        verifier_command=("cargo", "test", "--quiet"),
    ),
}


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


def build_supplemental_pr_issue_candidates(
    *,
    candidate_ids: list[str],
    source_preflight_root: str | Path,
    output_dir: str | Path,
    fail_if_output_exists: bool = True,
    max_accepted: int = 2,
    candidate_specs: dict[str, SupplementalCandidateSpec] | None = None,
    execute_live_probes: bool = True,
) -> Path:
    """Build V5 Stage 2B supplemental PR / issue candidate evidence."""

    root = Path(output_dir)
    if fail_if_output_exists:
        existing = [root / name for name in V5_STAGE2B_SUPPLEMENTAL_OUTPUT_NAMES if (root / name).exists()]
        candidate_root = root / "candidates"
        if candidate_root.exists() and any(candidate_root.iterdir()):
            existing.append(candidate_root)
        if existing:
            raise ConfigError(
                "V5 Stage 2B supplemental 输出已存在，不能覆盖旧 evidence："
                + ", ".join(path.as_posix() for path in existing)
            )
    if not candidate_ids:
        raise ConfigError("Stage 2B 必须显式传入至少一个 candidate-id。")
    preflight_root = Path(source_preflight_root)
    if not preflight_root.exists():
        raise ConfigError(f"source-preflight-root 不存在：{preflight_root}")
    root.mkdir(parents=True, exist_ok=True)

    specs = candidate_specs or DEFAULT_SUPPLEMENTAL_CANDIDATES
    candidate_records: list[dict[str, Any]] = []
    accepted_records: list[dict[str, Any]] = []
    aggregate_command_records: list[dict[str, Any]] = []

    for candidate_id in candidate_ids:
        spec = specs.get(candidate_id)
        safe_id = _safe_candidate_id(candidate_id)
        candidate_dir = root / "candidates" / safe_id
        if spec is None:
            record = _supplemental_unknown_candidate_record(candidate_id=candidate_id, candidate_dir=candidate_dir)
        elif execute_live_probes:
            record = _build_live_supplemental_candidate(
                spec=spec,
                candidate_dir=candidate_dir,
                preflight_root=preflight_root,
            )
        else:
            record = _build_offline_supplemental_candidate(
                spec=spec,
                candidate_dir=candidate_dir,
                preflight_root=preflight_root,
            )
        candidate_records.append(record)
        aggregate_command_records.extend(record.get("_command_records", []))
        record.pop("_command_records", None)
        if (
            len(accepted_records) < max_accepted
            and record.get("freeze_ready") is True
            and record.get("agent_run_ready") is True
            and _visibility_counters_clean(record)
        ):
            record["selected_for_stage2b_merge"] = True
            record["run_matrix_backup"] = True
            accepted_records.append(record)
        else:
            record["selected_for_stage2b_merge"] = False
            record["run_matrix_backup"] = False
            if record.get("freeze_ready") is True and len(accepted_records) >= max_accepted:
                record["replacement_reason"] = "not_selected_after_required_stage2b_two_candidates_were_filled"

    report_path = root / "v5_supplemental_pr_issue_candidate_report.json"
    aggregate_log_path = root / "v5_supplemental_pr_issue_command_log.jsonl"
    _write_jsonl(aggregate_log_path, aggregate_command_records)

    report = {
        "schema_version": V5_SUPPLEMENTAL_PR_ISSUE_CANDIDATE_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "stage": "v5_stage2b_supplemental_pr_issue_candidates",
        "source_preflight_root_ref": _evidence_ref(
            preflight_root,
            kind="v5_preflight_source_root",
            purpose="Explicit V5 preflight source root used to bind Stage 2B supplemental candidates",
            visibility="audit_only",
            producer_command="v5 preflight pipeline",
            producer_stage="v5_preimplementation_input",
            inspect_command="inspect-v5-task-set",
        ),
        "candidate_order": candidate_ids,
        "candidate_count": len(candidate_records),
        "accepted_supplemental_count": len(accepted_records),
        "required_supplemental_count": max_accepted,
        "freeze_ready_count": sum(1 for item in candidate_records if item.get("freeze_ready") is True),
        "agent_run_ready_count": sum(1 for item in candidate_records if item.get("agent_run_ready") is True),
        "visibility_clean_count": sum(1 for item in candidate_records if _visibility_counters_clean(item)),
        "selected_candidate_ids": [record["candidate_id"] for record in accepted_records],
        "candidate_records": candidate_records,
        "accepted_task_definition_refs": [record["task_definition_ref"] for record in accepted_records],
        "command_log_ref": _evidence_ref(
            aggregate_log_path,
            kind="v5_stage2b_supplemental_command_log",
            purpose="Aggregate command log for Stage 2B supplemental candidate probes",
            visibility="audit_only",
            producer_command="build-v5-supplemental-pr-issue-candidates",
            producer_stage="v5_stage2b_supplemental_pr_issue_candidates",
            inspect_command="inspect-v5-task-set",
        ),
        "live_probes_executed": execute_live_probes,
        "provider_api_called": False,
        "agent_run_started": False,
        "latest_run_discovery_used": False,
        "status": "passed" if len(accepted_records) >= max_accepted else "blocked",
    }
    _write_json(report_path, report)

    command_entry = _builder_command_log_entry(
        command_name="build-v5-supplemental-pr-issue-candidates",
        input_paths=[preflight_root],
        output_paths=[report_path, aggregate_log_path, root / "candidates"],
        producer_stage="v5_stage2b_supplemental_pr_issue_candidates",
    )
    command_entry["network_policy"] = "github_source_fetch_only_for_explicit_candidates" if execute_live_probes else "local_fixture_only"
    command_entry_path = root / "build_v5_supplemental_pr_issue_candidates_command_log_entry.json"
    _write_json(command_entry_path, command_entry)
    return report_path


def merge_task_set_manifests(
    *,
    base_task_set: str | Path,
    supplemental_report: str | Path,
    output: str | Path,
    output_inventory: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    """Merge the Stage 2A initial task set with accepted Stage 2B supplemental tasks."""

    base_path = Path(base_task_set)
    supplemental_path = Path(supplemental_report)
    output_path = Path(output)
    inventory_path = Path(output_inventory)
    visibility_path = output_path.parent / "v5_task_visibility_scan_report.json"
    command_entry_path = output_path.parent / "merge_v5_task_set_command_log_entry.json"
    command_log_path = output_path.parent / "v5_stage2b_merge_command_log.jsonl"
    if fail_if_output_exists:
        existing = [
            path
            for path in (output_path, inventory_path, visibility_path, command_entry_path, command_log_path)
            if path.exists()
        ]
        if existing:
            raise ConfigError(
                "V5 Stage 2B merge 输出已存在，不能覆盖旧 evidence："
                + ", ".join(path.as_posix() for path in existing)
            )

    base_manifest = _read_json(base_path)
    supplemental = _read_json(supplemental_path)
    if base_manifest.get("task_set_stage") != "stage2a_initial_10":
        raise ConfigError("merge-v5-task-set 只接受 Stage 2A initial task set 作为 base-task-set。")
    _validate_supplemental_report_for_merge(supplemental)
    accepted_refs = supplemental.get("accepted_task_definition_refs")
    if not isinstance(accepted_refs, list) or len(accepted_refs) < 2:
        raise ConfigError("supplemental-report 必须至少提供 2 个 accepted task definition refs。")

    base_task_refs = list(base_manifest.get("task_refs") or [])
    supplemental_task_refs = accepted_refs[:2]
    task_refs = [*base_task_refs, *supplemental_task_refs]
    task_defs = [_read_task_ref_payload(ref) for ref in task_refs]
    counts = _task_counts(task_defs)
    if counts["accepted_auditable_task_count"] < 12 or counts["pr_issue_task_count"] < 8:
        raise ConfigError("Stage 2B merge 后仍未满足 12 total / 8 PR-issue 严格任务库存门。")
    if counts["swebench_like_anchor_count"] < 3:
        raise ConfigError("Stage 2B merge 后 SWE-Bench-like anchor 数量不足 3。")

    base_visibility = _read_ref_payload_for_builder(base_manifest.get("visibility_scan_ref"))
    supplemental_adapter_refs = [
        _read_task_ref_payload(ref)["adapter_visible_input_ref"] for ref in supplemental_task_refs
    ]
    adapter_refs = list(base_visibility.get("adapter_visible_input_refs") or []) + supplemental_adapter_refs
    visibility_findings = _adapter_visible_ref_findings(adapter_refs)
    visibility_report = {
        "schema_version": V5_TASK_VISIBILITY_SCAN_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "scan_scope_refs": [
            base_manifest["visibility_scan_ref"],
            _evidence_ref(
                supplemental_path,
                kind="v5_supplemental_pr_issue_candidate_report",
                purpose="Stage 2B supplemental candidate visibility source",
                visibility="audit_only",
                producer_command="build-v5-supplemental-pr-issue-candidates",
                producer_stage="v5_stage2b_supplemental_pr_issue_candidates",
                inspect_command="inspect-v5-task-visibility",
            ),
        ],
        "adapter_visible_input_refs": adapter_refs,
        "task_definition_refs": task_refs,
        "model_visible_leak_count": len(visibility_findings),
        "share_safe_violation_count": 0,
        "trainable_payload_contamination_count": 0,
        "raw_provider_content_leak_count": 0,
        "credential_marker_leak_count": 0,
        "evaluator_only_raw_content_copied_count": 0,
        "findings": visibility_findings,
        "status": "passed" if not visibility_findings else "failed",
    }
    _write_json(visibility_path, visibility_report)

    inventory_report = {
        "schema_version": V5_TASK_INVENTORY_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        **counts,
        "strict_inventory_gate": "passed",
        "full_v5_threshold_status": "passed",
        "source_mix": {
            "pr_issue": counts["pr_issue_task_count"],
            "swebench_like_anchor": counts["swebench_like_anchor_count"],
        },
        "initial_batch_task_count": len(base_task_refs),
        "supplemental_task_count": len(supplemental_task_refs),
        "supplemental_candidate_report_ref": _evidence_ref(
            supplemental_path,
            kind="v5_supplemental_pr_issue_candidate_report",
            purpose="Stage 2B supplemental PR / issue candidate report",
            visibility="audit_only",
            producer_command="build-v5-supplemental-pr-issue-candidates",
            producer_stage="v5_stage2b_supplemental_pr_issue_candidates",
            inspect_command="inspect-v5-task-set",
        ),
        "supplemental_required": False,
        "claims_full_inventory_gate": True,
        "task_definition_refs": task_refs,
        "status": "passed",
    }
    _write_json(inventory_path, inventory_report)

    selected_records = [
        record
        for record in supplemental.get("candidate_records", [])
        if record.get("candidate_id") in {task.get("candidate_id") for task in task_defs[-len(supplemental_task_refs):]}
    ]
    merged_manifest = {
        "schema_version": V5_TASK_SET_MANIFEST_VERSION,
        "created_at": _utc_timestamp(),
        "task_set_stage": "stage2b_merged_12",
        **counts,
        "strict_inventory_gate": "passed",
        "full_v5_threshold_status": "passed",
        "initial_batch_task_count": len(base_task_refs),
        "supplemental_task_count": len(supplemental_task_refs),
        "supplemental_required": False,
        "claims_full_inventory_gate": True,
        "task_refs": task_refs,
        "initial_task_refs": base_task_refs,
        "supplemental_task_refs": supplemental_task_refs,
        "supplemental_task_sources": [
            {
                "candidate_id": record.get("candidate_id"),
                "producer_command": "build-v5-supplemental-pr-issue-candidates",
                "run_matrix_backup": record.get("run_matrix_backup") is True,
                "task_definition_ref": record.get("task_definition_ref"),
            }
            for record in selected_records
        ],
        "inventory_report_ref": _evidence_ref(
            inventory_path,
            kind="v5_task_inventory_report",
            purpose="V5 Stage 2B merged task inventory report",
            visibility="audit_only",
            producer_command="merge-v5-task-set",
            producer_stage="v5_stage2b_task_set_merge",
            inspect_command="inspect-v5-task-set",
        ),
        "visibility_scan_ref": _evidence_ref(
            visibility_path,
            kind="v5_task_visibility_scan_report",
            purpose="V5 Stage 2B merged task visibility scan report",
            visibility="audit_only",
            producer_command="merge-v5-task-set",
            producer_stage="v5_stage2b_task_set_merge",
            inspect_command="inspect-v5-task-visibility",
        ),
        "status": "passed",
    }
    _write_json(output_path, merged_manifest)

    command_entry = _builder_command_log_entry(
        command_name="merge-v5-task-set",
        input_paths=[base_path, supplemental_path],
        output_paths=[output_path, inventory_path, visibility_path],
        producer_stage="v5_stage2b_task_set_merge",
    )
    _write_json(command_entry_path, command_entry)
    _write_jsonl(command_log_path, [command_entry])
    return output_path


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


def _validate_supplemental_report_for_merge(payload: dict[str, Any]) -> None:
    failures: list[str] = []
    if payload.get("schema_version") != V5_SUPPLEMENTAL_PR_ISSUE_CANDIDATE_REPORT_VERSION:
        failures.append("supplemental-report schema_version 不匹配。")
    if payload.get("status") != "passed":
        failures.append("supplemental-report 必须 status=passed。")
    if payload.get("live_probes_executed") is not True:
        failures.append("supplemental-report 必须来自 live probes，不能用 offline fixture 关闭库存门。")
    if payload.get("required_supplemental_count") != 2:
        failures.append("supplemental-report required_supplemental_count 必须为 2。")
    if payload.get("accepted_supplemental_count", 0) < 2:
        failures.append("supplemental-report accepted_supplemental_count 至少为 2。")
    selected_ids = [str(item) for item in payload.get("selected_candidate_ids") or []]
    if len(selected_ids) != 2:
        failures.append("supplemental-report 必须选择 2 个 candidate。")
    accepted_refs = payload.get("accepted_task_definition_refs")
    if not isinstance(accepted_refs, list) or len(accepted_refs) < 2:
        failures.append("supplemental-report 必须至少提供 2 个 accepted task definition refs。")
        accepted_refs = []
    records = payload.get("candidate_records")
    if not isinstance(records, list) or not records:
        failures.append("supplemental-report candidate_records 必须是非空 list。")
        records = []
    by_candidate = {str(record.get("candidate_id")): record for record in records if isinstance(record, dict)}
    unknown_candidates = sorted(set(by_candidate).difference(V5_DEFAULT_SUPPLEMENTAL_CANDIDATE_ORDER))
    if unknown_candidates:
        failures.append("supplemental-report 包含未在默认补位顺序中审查过的候选：" + ", ".join(unknown_candidates))
    ready_in_order: list[str] = []
    for candidate_id in V5_DEFAULT_SUPPLEMENTAL_CANDIDATE_ORDER:
        record = by_candidate.get(candidate_id)
        if isinstance(record, dict) and _supplemental_record_ready_for_merge(record):
            ready_in_order.append(candidate_id)
    if selected_ids and ready_in_order[:2] != selected_ids:
        failures.append("supplemental-report selected_candidate_ids 必须是默认顺序中最早满足补位门的 2 个候选。")
    task_candidate_ids: list[str] = []
    accepted_ref_paths = {str((ref or {}).get("path") or "") for ref in accepted_refs if isinstance(ref, dict)}
    for index, ref in enumerate(accepted_refs, start=1):
        try:
            task_payload = _read_task_ref_payload(ref)
        except ConfigError as exc:
            failures.append(f"accepted_task_definition_refs[{index}] 无法读取：{exc}")
            continue
        task_candidate_ids.append(str(task_payload.get("candidate_id") or ""))
        if task_payload.get("accepted_auditable") is not True:
            failures.append(f"accepted_task_definition_refs[{index}] 必须 accepted_auditable=true。")
        if task_payload.get("agent_run_ready") is not True:
            failures.append(f"accepted_task_definition_refs[{index}] 必须 agent_run_ready=true。")
        if task_payload.get("source_kind") != "pr_issue_flow":
            failures.append(f"accepted_task_definition_refs[{index}] 必须来自 PR / issue flow。")
        if task_payload.get("live_probe_executed") is not True:
            failures.append(f"accepted_task_definition_refs[{index}] 必须绑定 live probe evidence。")
    if selected_ids and task_candidate_ids[:2] != selected_ids:
        failures.append("accepted_task_definition_refs 前两个 candidate_id 必须和 selected_candidate_ids 一致。")

    for index, record in enumerate(records, start=1):
        label = f"candidate_records[{index}]"
        if not isinstance(record, dict):
            failures.append(f"{label} 必须是 object。")
            continue
        command_ref = record.get("candidate_command_log_ref")
        if not _ref_path_exists(command_ref):
            failures.append(f"{label}.candidate_command_log_ref 必须存在。")
        elif not _candidate_command_log_has_entries(command_ref):
            failures.append(f"{label}.candidate_command_log_ref 必须至少包含 1 条命令记录。")
        if record.get("selected_for_stage2b_merge") is True:
            candidate_id = str(record.get("candidate_id") or "")
            if candidate_id not in selected_ids:
                failures.append(f"{label} 被标记 selected，但不在 selected_candidate_ids 中。")
            if not _supplemental_record_ready_for_merge(record):
                failures.append(f"{label} 被选中但未满足 freeze_ready、agent_run_ready、visibility clean、baseline failure、post-patch pass 和 stable flaky probe。")
            if record.get("live_probe_executed") is not True:
                failures.append(f"{label} 被选中但 live_probe_executed 不是 true。")
            task_ref_path = str(((record.get("task_definition_ref") or {}).get("path")) or "")
            if task_ref_path not in accepted_ref_paths:
                failures.append(f"{label}.task_definition_ref 必须出现在 accepted_task_definition_refs 中。")
            for field in (
                "source_materialization_report_ref",
                "source_archive_manifest_ref",
                "dependency_probe_report_ref",
                "baseline_verifier_probe_report_ref",
                "post_patch_verifier_probe_report_ref",
                "flaky_probe_report_ref",
                "adapter_visible_denylist_scan_report_ref",
                "training_export_boundary_probe_report_ref",
                "provider_raw_content_leak_probe_report_ref",
                "task_definition_ref",
            ):
                if not _ref_path_exists(record.get(field)):
                    failures.append(f"{label}.{field} 必须存在。")
        else:
            if record.get("freeze_ready") is False:
                for field in (
                    "failure_owner",
                    "failure_category",
                    "replacement_reason",
                    "failed_command_name",
                    "stdout_sha256",
                    "stderr_sha256",
                ):
                    if not record.get(field):
                        failures.append(f"{label} 未通过补位门时必须记录 {field}。")
            elif not record.get("replacement_reason"):
                failures.append(f"{label} 满足补位门但未被选择时必须记录 replacement_reason。")
    if failures:
        raise ConfigError("; ".join(failures))


def _build_live_supplemental_candidate(
    *,
    spec: SupplementalCandidateSpec,
    candidate_dir: Path,
    preflight_root: Path,
) -> dict[str, Any]:
    candidate_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = candidate_dir / "command_logs"
    archives_dir = candidate_dir / "archives"
    patches_dir = candidate_dir / "patches"
    stdout_dir = candidate_dir / "command_outputs"
    archives_dir.mkdir(parents=True, exist_ok=True)
    patches_dir.mkdir(parents=True, exist_ok=True)
    stdout_dir.mkdir(parents=True, exist_ok=True)
    command_records: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="repo-harness-v5-stage2b-fetch-") as temp_root:
        clone_dir = Path(temp_root) / "repo"
        command_records.append(
            _run_stage2b_command(
                command_name=f"{spec.task_id}_git_clone",
                argv=("git", "clone", "--filter=blob:none", "--no-checkout", spec.repo_url, clone_dir.as_posix()),
                cwd=Path.cwd(),
                input_paths=[],
                output_dir=stdout_dir,
            )
        )
        if command_records[-1]["exit_code"] != 0:
            return _failed_candidate_record(
                spec=spec,
                candidate_dir=candidate_dir,
                command_records=command_records,
                failure_owner="external_source",
                failure_category="source_clone_failed",
                failed_record=command_records[-1],
            )
        command_records.append(
            _run_stage2b_command(
                command_name=f"{spec.task_id}_git_fetch_fixed_revisions",
                argv=("git", "fetch", "origin", spec.base_commit, spec.resolved_commit),
                cwd=clone_dir,
                input_paths=[],
                output_dir=stdout_dir,
            )
        )
        if command_records[-1]["exit_code"] != 0:
            return _failed_candidate_record(
                spec=spec,
                candidate_dir=candidate_dir,
                command_records=command_records,
                failure_owner="external_source",
                failure_category="fixed_revision_fetch_failed",
                failed_record=command_records[-1],
            )
        command_records.append(
            _run_stage2b_command(
                command_name=f"{spec.task_id}_git_checkout_base",
                argv=("git", "checkout", "--detach", spec.base_commit),
                cwd=clone_dir,
                input_paths=[],
                output_dir=stdout_dir,
            )
        )
        if command_records[-1]["exit_code"] != 0:
            return _failed_candidate_record(
                spec=spec,
                candidate_dir=candidate_dir,
                command_records=command_records,
                failure_owner="external_source",
                failure_category="base_checkout_failed",
                failed_record=command_records[-1],
            )
        source_archive_path = archives_dir / f"{spec.task_id}_source.tar"
        command_records.append(
            _run_stage2b_command(
                command_name=f"{spec.task_id}_git_archive_base",
                argv=("git", "archive", "--format=tar", "--output", source_archive_path.resolve().as_posix(), spec.base_commit),
                cwd=clone_dir,
                input_paths=[],
                output_dir=stdout_dir,
            )
        )
        if command_records[-1]["exit_code"] != 0:
            return _failed_candidate_record(
                spec=spec,
                candidate_dir=candidate_dir,
                command_records=command_records,
                failure_owner="external_source",
                failure_category="source_archive_failed",
                failed_record=command_records[-1],
            )
        full_patch_path = patches_dir / f"{spec.task_id}_full_patch.diff"
        test_patch_path = patches_dir / f"{spec.task_id}_test_patch.diff"
        command_records.append(
            _run_stage2b_command(
                command_name=f"{spec.task_id}_git_diff_full_patch",
                argv=("git", "diff", "--binary", spec.base_commit, spec.resolved_commit),
                cwd=clone_dir,
                input_paths=[],
                output_dir=stdout_dir,
                stdout_redirect=full_patch_path,
            )
        )
        if command_records[-1]["exit_code"] != 0:
            return _failed_candidate_record(
                spec=spec,
                candidate_dir=candidate_dir,
                command_records=command_records,
                failure_owner="external_source",
                failure_category="full_patch_diff_failed",
                failed_record=command_records[-1],
            )
        command_records.append(
            _run_stage2b_command(
                command_name=f"{spec.task_id}_git_diff_test_patch",
                argv=("git", "diff", "--binary", spec.base_commit, spec.resolved_commit, "--", *spec.test_patch_paths),
                cwd=clone_dir,
                input_paths=[],
                output_dir=stdout_dir,
                stdout_redirect=test_patch_path,
            )
        )
        if command_records[-1]["exit_code"] != 0:
            return _failed_candidate_record(
                spec=spec,
                candidate_dir=candidate_dir,
                command_records=command_records,
                failure_owner="external_source",
                failure_category="test_patch_diff_failed",
                failed_record=command_records[-1],
            )

    source_materialization_report_path = candidate_dir / "source_materialization_report.json"
    source_archive_manifest_path = candidate_dir / "source_archive_manifest.json"
    source_tree_hash = _source_tree_hash_from_tar(source_archive_path)
    _write_json(
        source_archive_manifest_path,
        {
            "schema_version": V5_SUPPLEMENTAL_PR_ISSUE_PROBE_REPORT_VERSION,
            "created_at": _utc_timestamp(),
            "candidate_id": spec.candidate_id,
            "probe_kind": "source_archive_manifest",
            "source_archive_ref": _stage2b_evidence_ref(source_archive_path, kind="source_archive", purpose=f"Base source archive for {spec.candidate_id}"),
            "source_tree_hash": source_tree_hash,
            "status": "passed",
        },
    )
    _write_json(
        source_materialization_report_path,
        {
            "schema_version": V5_SUPPLEMENTAL_PR_ISSUE_PROBE_REPORT_VERSION,
            "created_at": _utc_timestamp(),
            "candidate_id": spec.candidate_id,
            "repository": spec.repository,
            "repo_url": spec.repo_url,
            "base_commit": spec.base_commit,
            "resolved_commit": spec.resolved_commit,
            "source_archive_manifest_ref": _stage2b_evidence_ref(source_archive_manifest_path, kind="source_archive_manifest", purpose=f"Source archive manifest for {spec.candidate_id}"),
            "source_preflight_root_ref": _stage2b_evidence_ref(preflight_root, kind="v5_preflight_source_root", purpose="Explicit V5 preflight input root"),
            "latest_run_discovery_used": False,
            "status": "passed",
        },
    )

    dependency_report_path = candidate_dir / "dependency_probe_report.json"
    dependency_probe = _run_probe_workspace(
        spec=spec,
        candidate_dir=candidate_dir,
        source_archive_path=source_archive_path,
        patch_path=None,
        verifier_command=(),
        probe_name="dependency_probe",
        expected_exit_code=0,
        command_records=command_records,
    )
    _write_json(
        dependency_report_path,
        _probe_report_payload(
            spec=spec,
            probe_kind="dependency_probe",
            probe=dependency_probe,
            expected_status="passed",
            source_archive_path=source_archive_path,
        ),
    )

    baseline_report_path = candidate_dir / "baseline_verifier_probe_report.json"
    baseline_probe = _run_probe_workspace(
        spec=spec,
        candidate_dir=candidate_dir,
        source_archive_path=source_archive_path,
        patch_path=test_patch_path,
        verifier_command=spec.verifier_command,
        probe_name="baseline_verifier_probe",
        expected_exit_code=1,
        command_records=command_records,
    )
    _write_json(
        baseline_report_path,
        _probe_report_payload(
            spec=spec,
            probe_kind="baseline_verifier_probe",
            probe=baseline_probe,
            expected_status="expected_failure",
            source_archive_path=source_archive_path,
            patch_path=test_patch_path,
        ),
    )

    post_patch_report_path = candidate_dir / "post_patch_verifier_probe_report.json"
    post_patch_probe = _run_probe_workspace(
        spec=spec,
        candidate_dir=candidate_dir,
        source_archive_path=source_archive_path,
        patch_path=full_patch_path,
        verifier_command=spec.verifier_command,
        probe_name="post_patch_verifier_probe",
        expected_exit_code=0,
        command_records=command_records,
        verifier_repeat_count=3,
    )
    _write_json(
        post_patch_report_path,
        _probe_report_payload(
            spec=spec,
            probe_kind="post_patch_verifier_probe",
            probe=post_patch_probe,
            expected_status="passed",
            source_archive_path=source_archive_path,
            patch_path=full_patch_path,
        ),
    )

    task_artifacts = _write_supplemental_task_artifacts(
        spec=spec,
        candidate_dir=candidate_dir,
        preflight_root=preflight_root,
        source_archive_path=source_archive_path,
        source_tree_hash=source_tree_hash,
        source_materialization_report_path=source_materialization_report_path,
        source_archive_manifest_path=source_archive_manifest_path,
        dependency_report_path=dependency_report_path,
        baseline_report_path=baseline_report_path,
        post_patch_report_path=post_patch_report_path,
        full_patch_path=full_patch_path,
        test_patch_path=test_patch_path,
        command_records=command_records,
        baseline_probe=baseline_probe,
        post_patch_probe=post_patch_probe,
        live_probe_executed=True,
    )
    return {
        **task_artifacts["candidate_record"],
        "_command_records": command_records,
    }


def _build_offline_supplemental_candidate(
    *,
    spec: SupplementalCandidateSpec,
    candidate_dir: Path,
    preflight_root: Path,
) -> dict[str, Any]:
    candidate_dir.mkdir(parents=True, exist_ok=True)
    archive_path = candidate_dir / "archives" / f"{spec.task_id}_source.tar"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    source_file = candidate_dir / "offline_source.txt"
    source_file.write_text(f"{spec.candidate_id}\n{spec.base_commit}\n", encoding="utf-8")
    with tarfile.open(archive_path, "w") as archive:
        archive.add(source_file, arcname="README.md")
    full_patch_path = candidate_dir / "patches" / f"{spec.task_id}_full_patch.diff"
    test_patch_path = candidate_dir / "patches" / f"{spec.task_id}_test_patch.diff"
    full_patch_path.parent.mkdir(parents=True, exist_ok=True)
    full_patch_path.write_text("offline evaluator-only full patch placeholder\n", encoding="utf-8")
    test_patch_path.write_text("offline evaluator-only test patch placeholder\n", encoding="utf-8")
    source_tree_hash = _source_tree_hash_from_tar(archive_path)
    command_records = [
        _offline_command_record(
            command_name=f"{spec.task_id}_offline_probe_fixture",
            output_dir=candidate_dir / "command_outputs",
        )
    ]

    reports: dict[str, Path] = {}
    for name, status in (
        ("source_materialization_report", "passed"),
        ("source_archive_manifest", "passed"),
        ("dependency_probe_report", "passed"),
        ("baseline_verifier_probe_report", "expected_failure"),
        ("post_patch_verifier_probe_report", "passed"),
    ):
        path = candidate_dir / f"{name}.json"
        _write_json(
            path,
            {
                "schema_version": V5_SUPPLEMENTAL_PR_ISSUE_PROBE_REPORT_VERSION,
                "created_at": _utc_timestamp(),
                "candidate_id": spec.candidate_id,
                "probe_kind": name,
                "status": status,
                "offline_fixture": True,
            },
        )
        reports[name] = path

    task_artifacts = _write_supplemental_task_artifacts(
        spec=spec,
        candidate_dir=candidate_dir,
        preflight_root=preflight_root,
        source_archive_path=archive_path,
        source_tree_hash=source_tree_hash,
        source_materialization_report_path=reports["source_materialization_report"],
        source_archive_manifest_path=reports["source_archive_manifest"],
        dependency_report_path=reports["dependency_probe_report"],
        baseline_report_path=reports["baseline_verifier_probe_report"],
        post_patch_report_path=reports["post_patch_verifier_probe_report"],
        full_patch_path=full_patch_path,
        test_patch_path=test_patch_path,
        command_records=command_records,
        baseline_probe={"exit_codes": [1], "status": "expected_failure"},
        post_patch_probe={"exit_codes": [0, 0, 0], "status": "passed"},
        live_probe_executed=False,
    )
    return {
        **task_artifacts["candidate_record"],
        "_command_records": command_records,
    }


def _write_supplemental_task_artifacts(
    *,
    spec: SupplementalCandidateSpec,
    candidate_dir: Path,
    preflight_root: Path,
    source_archive_path: Path,
    source_tree_hash: str,
    source_materialization_report_path: Path,
    source_archive_manifest_path: Path,
    dependency_report_path: Path,
    baseline_report_path: Path,
    post_patch_report_path: Path,
    full_patch_path: Path,
    test_patch_path: Path,
    command_records: list[dict[str, Any]],
    baseline_probe: dict[str, Any],
    post_patch_probe: dict[str, Any],
    live_probe_executed: bool,
) -> dict[str, Any]:
    adapter_input_path = candidate_dir / "adapter_visible_task_input.json"
    adapter_input = {
        "schema_version": "repo_harness_v5_adapter_visible_task_input_v0",
        "task_id": spec.task_id,
        "candidate_id": spec.candidate_id,
        "task_family": spec.task_family,
        "ecosystem": spec.ecosystem,
        "repository": spec.repository,
        "title": spec.title,
        "task_statement": spec.task_statement,
        "visible_constraints": list(spec.visible_constraints),
        "final_verifier_command": list(spec.verifier_command),
        "visibility": "model_visible",
        "share_safe": True,
    }
    _write_json(adapter_input_path, adapter_input)
    visibility_findings = _adapter_visible_findings(task_id=spec.task_id, adapter_input=adapter_input)

    evaluator_manifest_path = candidate_dir / "evaluator_only_evidence_manifest.json"
    _write_json(
        evaluator_manifest_path,
        {
            "schema_version": V5_EVALUATOR_ONLY_EVIDENCE_MANIFEST_VERSION,
            "created_at": _utc_timestamp(),
            "candidate_id": spec.candidate_id,
            "visibility": "evaluator_only",
            "share_safe": False,
            "policy": "never_adapter_visible",
            "full_patch_ref": _stage2b_evidence_ref(full_patch_path, kind="evaluator_only_full_patch", purpose=f"Full evaluator-only patch for {spec.candidate_id}", visibility="evaluator_only"),
            "test_patch_ref": _stage2b_evidence_ref(test_patch_path, kind="evaluator_only_test_patch", purpose=f"Evaluator-only test patch for {spec.candidate_id}", visibility="evaluator_only"),
            "baseline_verifier_probe_ref": _stage2b_evidence_ref(baseline_report_path, kind="baseline_verifier_probe_report", purpose=f"Baseline verifier probe for {spec.candidate_id}"),
            "post_patch_verifier_probe_ref": _stage2b_evidence_ref(post_patch_report_path, kind="post_patch_verifier_probe_report", purpose=f"Post-patch verifier probe for {spec.candidate_id}"),
            "status": "passed",
        },
    )

    flaky_report_path = candidate_dir / "flaky_probe_report.json"
    baseline_exit_codes = list(baseline_probe.get("exit_codes") or [])
    post_patch_exit_codes = list(post_patch_probe.get("exit_codes") or [])
    stable = bool(baseline_exit_codes) and all(code != 0 for code in baseline_exit_codes) and len(post_patch_exit_codes) >= 3 and all(code == 0 for code in post_patch_exit_codes)
    _write_json(
        flaky_report_path,
        {
            "schema_version": V5_SUPPLEMENTAL_PR_ISSUE_PROBE_REPORT_VERSION,
            "created_at": _utc_timestamp(),
            "candidate_id": spec.candidate_id,
            "probe_kind": "flaky_probe",
            "baseline_exit_codes": baseline_exit_codes,
            "post_patch_exit_codes": post_patch_exit_codes,
            "attempt_count_per_side": {"baseline": len(baseline_exit_codes), "post_patch": len(post_patch_exit_codes)},
            "flaky_suspected": not stable,
            "status": "stable" if stable else "unstable",
        },
    )

    visibility_report_path = candidate_dir / "adapter_visible_denylist_scan_report.json"
    _write_json(
        visibility_report_path,
        {
            "schema_version": V5_TASK_VISIBILITY_SCAN_REPORT_VERSION,
            "created_at": _utc_timestamp(),
            "candidate_id": spec.candidate_id,
            "scan_scope_refs": [
                _stage2b_evidence_ref(adapter_input_path, kind="adapter_visible_task_input", purpose=f"Adapter-visible task input for {spec.candidate_id}", visibility="model_visible", share_safe=True),
                _stage2b_evidence_ref(evaluator_manifest_path, kind="evaluator_only_evidence_manifest", purpose=f"Evaluator-only evidence manifest for {spec.candidate_id}", visibility="evaluator_only"),
            ],
            "adapter_visible_input_refs": [
                _stage2b_evidence_ref(adapter_input_path, kind="adapter_visible_task_input", purpose=f"Adapter-visible task input for {spec.candidate_id}", visibility="model_visible", share_safe=True)
            ],
            "model_visible_leak_count": len(visibility_findings),
            "share_safe_violation_count": 0,
            "trainable_payload_contamination_count": 0,
            "raw_provider_content_leak_count": 0,
            "credential_marker_leak_count": 0,
            "evaluator_only_raw_content_copied_count": 0,
            "findings": visibility_findings,
            "status": "passed" if not visibility_findings else "failed",
        },
    )

    training_boundary_path = candidate_dir / "training_export_boundary_probe_report.json"
    provider_leak_path = candidate_dir / "provider_raw_content_leak_probe_report.json"
    _write_json(
        training_boundary_path,
        {
            "schema_version": V5_SUPPLEMENTAL_PR_ISSUE_PROBE_REPORT_VERSION,
            "created_at": _utc_timestamp(),
            "candidate_id": spec.candidate_id,
            "probe_kind": "training_export_boundary_probe",
            "trainable_payload_created": False,
            "evaluator_only_refs_count": 1,
            "evaluator_only_content_copied_to_trainable_count": 0,
            "reward_scalar_model_visible_count": 0,
            "reward_label_model_visible_count": 0,
            "status": "passed",
        },
    )
    _write_json(
        provider_leak_path,
        {
            "schema_version": V5_SUPPLEMENTAL_PR_ISSUE_PROBE_REPORT_VERSION,
            "created_at": _utc_timestamp(),
            "candidate_id": spec.candidate_id,
            "probe_kind": "provider_raw_content_leak_probe",
            "provider_api_called": False,
            "provider_raw_request_model_visible_count": 0,
            "provider_raw_response_model_visible_count": 0,
            "credential_marker_count": 0,
            "status": "passed",
        },
    )

    diversity_report_path = candidate_dir / "task_diversity_report.json"
    _write_json(
        diversity_report_path,
        {
            "schema_version": V5_TASK_DIVERSITY_REPORT_VERSION,
            "created_at": _utc_timestamp(),
            "task_count": 1,
            "ecosystem_counts": {spec.ecosystem: 1},
            "source_kind_counts": {"pr_issue_flow": 1},
            "task_family_counts": {spec.task_family: 1},
            "repository_count": 1,
            "large_repository_task_count": 0,
            "comparison_ready_count": 0,
            "demo_ready_count": 0,
            "rows": [
                {
                    "task_id": spec.task_id,
                    "candidate_id": spec.candidate_id,
                    "ecosystem": spec.ecosystem,
                    "repository": spec.repository,
                    "source_kind": "pr_issue_flow",
                    "task_family": spec.task_family,
                    "recommended_v5_role": "run_matrix_backup",
                    "comparison_ready": False,
                    "demo_ready": False,
                }
            ],
            "status": "passed",
        },
    )

    command_log_path = candidate_dir / "candidate_command_log.jsonl"
    _write_jsonl(command_log_path, command_records)
    adapter_ref = _stage2b_evidence_ref(adapter_input_path, kind="adapter_visible_task_input", purpose=f"Adapter-visible task input for {spec.candidate_id}", visibility="model_visible", share_safe=True)
    task_definition_path = candidate_dir / "task_definition.json"
    task_def = {
        "schema_version": V5_TASK_DEFINITION_VERSION,
        "task_id": spec.task_id,
        "candidate_id": spec.candidate_id,
        "task_family": spec.task_family,
        "source_kind": "pr_issue_flow",
        "track": "pr_issue",
        "repository": spec.repository,
        "repo_url_or_archive_id": spec.repo_url,
        "base_commit": spec.base_commit,
        "resolved_commit": spec.resolved_commit,
        "source_archive_sha256": sha256_file(source_archive_path),
        "source_archive_ref": _stage2b_evidence_ref(source_archive_path, kind="source_archive", purpose=f"Base source archive for {spec.candidate_id}"),
        "source_tree_hash": source_tree_hash,
        "source_tree_file_count": _tar_file_count(source_archive_path),
        "task_input_hash": sha256_file(adapter_input_path),
        "adapter_visible_input_ref": adapter_ref,
        "evaluator_only_evidence_ref": _stage2b_evidence_ref(evaluator_manifest_path, kind="evaluator_only_evidence_manifest", purpose=f"Evaluator-only evidence manifest for {spec.candidate_id}", visibility="evaluator_only"),
        "baseline_verifier_plan_ref": _stage2b_evidence_ref(baseline_report_path, kind="baseline_verifier_probe_report", purpose=f"Baseline verifier plan and probe for {spec.candidate_id}"),
        "final_verifier_plan_ref": _stage2b_evidence_ref(post_patch_report_path, kind="final_verifier_probe_report", purpose=f"Final verifier plan and probe for {spec.candidate_id}"),
        "fail_to_pass_evidence_ref": _stage2b_evidence_ref(baseline_report_path, kind="fail_to_pass_evidence", purpose=f"Expected failing baseline verifier probe for {spec.candidate_id}"),
        "pass_to_pass_evidence_ref": _stage2b_evidence_ref(post_patch_report_path, kind="pass_to_pass_evidence", purpose=f"Passing post-patch verifier probe for {spec.candidate_id}"),
        "flaky_probe_report_ref": _stage2b_evidence_ref(flaky_report_path, kind="flaky_probe_report", purpose=f"Flaky probe report for {spec.candidate_id}"),
        "license_provenance_ref": _stage2b_evidence_ref(source_materialization_report_path, kind="license_provenance", purpose=f"Source materialization and provenance report for {spec.candidate_id}"),
        "dependency_cache_ref": _stage2b_evidence_ref(dependency_report_path, kind="dependency_probe_report", purpose=f"Dependency probe report for {spec.candidate_id}"),
        "environment_stability_ref": _stage2b_evidence_ref(flaky_report_path, kind="environment_stability", purpose=f"Environment stability facts for {spec.candidate_id}"),
        "contamination_scan_ref": _stage2b_evidence_ref(visibility_report_path, kind="contamination_scan", purpose=f"Visibility and contamination scan for {spec.candidate_id}"),
        "visibility_scan_ref": _stage2b_evidence_ref(visibility_report_path, kind="visibility_scan", purpose=f"Visibility scan for {spec.candidate_id}"),
        "task_diversity_ref": _stage2b_evidence_ref(diversity_report_path, kind="task_diversity_report", purpose=f"Task diversity facts for {spec.candidate_id}"),
        "supplemental_candidate": True,
        "accepted_auditable": _supplemental_candidate_ready(
            baseline_probe=baseline_probe,
            post_patch_probe=post_patch_probe,
            stable=stable,
            visibility_findings=visibility_findings,
        ),
        "agent_run_ready": _supplemental_candidate_ready(
            baseline_probe=baseline_probe,
            post_patch_probe=post_patch_probe,
            stable=stable,
            visibility_findings=visibility_findings,
        ),
        "comparison_ready": False,
        "run_matrix_backup": True,
        "recommended_v5_role": "run_matrix_backup",
        "environment_id": spec.environment_id,
        "tool_policy_id": spec.tool_policy_id,
        "context_policy_id": spec.context_policy_id,
        "budget_policy_id": spec.budget_policy_id,
        "scaffold_id": spec.scaffold_id,
        "live_probe_executed": live_probe_executed,
    }
    _write_json(task_definition_path, task_def)

    freeze_ready = task_def["accepted_auditable"] is True
    failed_record = None if freeze_ready else next(
        (record for record in reversed(command_records) if record.get("exit_code") != 0),
        command_records[-1] if command_records else None,
    )
    candidate_record = {
        "candidate_id": spec.candidate_id,
        "task_id": spec.task_id,
        "repository": spec.repository,
        "source_kind": "pr_issue_flow",
        "freeze_ready": freeze_ready,
        "agent_run_ready": task_def["agent_run_ready"],
        "visibility_counters": {
            "model_visible_leak_count": len(visibility_findings),
            "share_safe_violation_count": 0,
            "trainable_payload_contamination_count": 0,
            "raw_provider_content_leak_count": 0,
            "credential_marker_leak_count": 0,
        },
        "baseline_expected_failure": bool(baseline_exit_codes) and all(code != 0 for code in baseline_exit_codes),
        "post_patch_passed": len(post_patch_exit_codes) >= 3 and all(code == 0 for code in post_patch_exit_codes),
        "flaky_probe_status": "stable" if stable else "unstable",
        "failure_owner": None if freeze_ready else "repo_harness",
        "failure_category": None if freeze_ready else "candidate_probe_failed",
        "replacement_reason": None if freeze_ready else "candidate did not satisfy freeze_ready and visibility gates",
        "failed_command_name": None if failed_record is None else failed_record.get("command_name"),
        "stdout_sha256": None if failed_record is None else failed_record.get("stdout_sha256"),
        "stderr_sha256": None if failed_record is None else failed_record.get("stderr_sha256"),
        "source_materialization_report_ref": _stage2b_evidence_ref(source_materialization_report_path, kind="source_materialization_report", purpose=f"Source materialization report for {spec.candidate_id}"),
        "source_archive_manifest_ref": _stage2b_evidence_ref(source_archive_manifest_path, kind="source_archive_manifest", purpose=f"Source archive manifest for {spec.candidate_id}"),
        "dependency_probe_report_ref": _stage2b_evidence_ref(dependency_report_path, kind="dependency_probe_report", purpose=f"Dependency probe report for {spec.candidate_id}"),
        "baseline_verifier_probe_report_ref": _stage2b_evidence_ref(baseline_report_path, kind="baseline_verifier_probe_report", purpose=f"Baseline verifier probe report for {spec.candidate_id}"),
        "post_patch_verifier_probe_report_ref": _stage2b_evidence_ref(post_patch_report_path, kind="post_patch_verifier_probe_report", purpose=f"Post-patch verifier probe report for {spec.candidate_id}"),
        "flaky_probe_report_ref": _stage2b_evidence_ref(flaky_report_path, kind="flaky_probe_report", purpose=f"Flaky probe report for {spec.candidate_id}"),
        "adapter_visible_denylist_scan_report_ref": _stage2b_evidence_ref(visibility_report_path, kind="adapter_visible_denylist_scan_report", purpose=f"Adapter-visible denylist scan for {spec.candidate_id}"),
        "training_export_boundary_probe_report_ref": _stage2b_evidence_ref(training_boundary_path, kind="training_export_boundary_probe_report", purpose=f"Training export boundary probe for {spec.candidate_id}"),
        "provider_raw_content_leak_probe_report_ref": _stage2b_evidence_ref(provider_leak_path, kind="provider_raw_content_leak_probe_report", purpose=f"Provider raw content leak probe for {spec.candidate_id}"),
        "candidate_command_log_ref": _stage2b_evidence_ref(command_log_path, kind="candidate_command_log", purpose=f"Candidate command log for {spec.candidate_id}"),
        "task_definition_ref": _stage2b_evidence_ref(task_definition_path, kind="v5_task_definition", purpose=f"Supplemental V5 task definition for {spec.candidate_id}"),
        "live_probe_executed": live_probe_executed,
    }
    return {"candidate_record": candidate_record}


def _run_probe_workspace(
    *,
    spec: SupplementalCandidateSpec,
    candidate_dir: Path,
    source_archive_path: Path,
    patch_path: Path | None,
    verifier_command: tuple[str, ...],
    probe_name: str,
    expected_exit_code: int,
    command_records: list[dict[str, Any]],
    verifier_repeat_count: int = 1,
) -> dict[str, Any]:
    stdout_dir = candidate_dir / "command_outputs"
    exit_codes: list[int] = []
    with tempfile.TemporaryDirectory(prefix=f"repo-harness-v5-{spec.task_id}-{probe_name}-") as temp_root:
        work_dir = Path(temp_root) / "repo"
        work_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(source_archive_path, "r") as archive:
            archive.extractall(work_dir)
        command_records.append(
            _run_stage2b_command(
                command_name=f"{spec.task_id}_{probe_name}_git_init",
                argv=("git", "init", "-q"),
                cwd=work_dir,
                input_paths=[source_archive_path],
                output_dir=stdout_dir,
            )
        )
        if command_records[-1]["exit_code"] != 0:
            return {"exit_codes": [command_records[-1]["exit_code"]], "status": "failed"}
        command_records.append(
            _run_stage2b_command(
                command_name=f"{spec.task_id}_{probe_name}_create_venv",
                argv=("python3", "-m", "venv", ".venv-stage2b"),
                cwd=work_dir,
                input_paths=[source_archive_path],
                output_dir=stdout_dir,
            )
        )
        if command_records[-1]["exit_code"] != 0:
            return {"exit_codes": [command_records[-1]["exit_code"]], "status": "failed"}
        install_command = _venv_python_command(spec.dependency_install_command)
        command_records.append(
            _run_stage2b_command(
                command_name=f"{spec.task_id}_{probe_name}_dependency_install",
                argv=install_command,
                cwd=work_dir,
                input_paths=[source_archive_path],
                output_dir=stdout_dir,
            )
        )
        if command_records[-1]["exit_code"] != 0:
            return {"exit_codes": [command_records[-1]["exit_code"]], "status": "failed"}
        if patch_path is not None:
            command_records.append(
                _run_stage2b_command(
                    command_name=f"{spec.task_id}_{probe_name}_apply_patch",
                    argv=("git", "apply", patch_path.resolve().as_posix()),
                    cwd=work_dir,
                    input_paths=[patch_path],
                    output_dir=stdout_dir,
                )
            )
            if command_records[-1]["exit_code"] != 0:
                return {"exit_codes": [command_records[-1]["exit_code"]], "status": "failed"}
        if verifier_command:
            for index in range(verifier_repeat_count):
                command_records.append(
                    _run_stage2b_command(
                        command_name=f"{spec.task_id}_{probe_name}_verifier_{index + 1}",
                        argv=_venv_python_command(verifier_command),
                        cwd=work_dir,
                        input_paths=[source_archive_path, *( [patch_path] if patch_path is not None else [] )],
                        output_dir=stdout_dir,
                    )
                )
                exit_codes.append(int(command_records[-1]["exit_code"]))
        else:
            exit_codes.append(0)
    expected_status = "passed" if expected_exit_code == 0 else "expected_failure"
    if expected_exit_code == 0:
        status = "passed" if exit_codes and all(code == 0 for code in exit_codes) else "failed"
    else:
        status = "expected_failure" if exit_codes and all(code != 0 for code in exit_codes) else "failed"
    return {"exit_codes": exit_codes, "status": status}


def _probe_report_payload(
    *,
    spec: SupplementalCandidateSpec,
    probe_kind: str,
    probe: dict[str, Any],
    expected_status: str,
    source_archive_path: Path,
    patch_path: Path | None = None,
) -> dict[str, Any]:
    refs = [
        _stage2b_evidence_ref(source_archive_path, kind="source_archive", purpose=f"Source archive input for {spec.candidate_id}")
    ]
    if patch_path is not None:
        refs.append(
            _stage2b_evidence_ref(patch_path, kind="evaluator_only_patch", purpose=f"Evaluator-only patch input for {spec.candidate_id}", visibility="evaluator_only")
        )
    return {
        "schema_version": V5_SUPPLEMENTAL_PR_ISSUE_PROBE_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "candidate_id": spec.candidate_id,
        "probe_kind": probe_kind,
        "expected_status": expected_status,
        "exit_codes": probe.get("exit_codes") or [],
        "input_refs": refs,
        "status": probe.get("status"),
    }


def _run_stage2b_command(
    *,
    command_name: str,
    argv: tuple[str, ...],
    cwd: Path,
    input_paths: list[Path],
    output_dir: Path,
    stdout_redirect: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_candidate_id(command_name)
    stdout_path = stdout_redirect or output_dir / f"{safe_name}.stdout.txt"
    stderr_path = output_dir / f"{safe_name}.stderr.txt"
    started_at = _utc_timestamp()
    completed = subprocess.run(
        list(argv),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    finished_at = _utc_timestamp()
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return {
        "schema_version": V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
        "command_name": command_name,
        "argv": list(argv),
        "cwd": cwd.as_posix(),
        "builder_invocation_cwd": Path.cwd().as_posix(),
        "env_policy": "temporary workspace command; provider credential values are not recorded",
        "network_policy": "github_source_fetch_only" if any(arg in {"clone", "fetch"} for arg in argv) else "local_probe_only",
        "risk_command_hits": [],
        "input_ref_policy": "explicit Stage 2B candidate command inputs are bound when materialized as paths",
        "input_refs": [
            _stage2b_evidence_ref(path, kind="candidate_command_input", purpose=f"{command_name} input")
            for path in input_paths
            if path.exists()
        ],
        "output_refs": [
            _stage2b_evidence_ref(stdout_path, kind="command_stdout", purpose=f"{command_name} stdout"),
            _stage2b_evidence_ref(stderr_path, kind="command_stderr", purpose=f"{command_name} stderr"),
        ],
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": completed.returncode,
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_sha256": sha256_file(stderr_path),
        "structured_skip_reason": None,
        "structured_failure_reason": None if completed.returncode == 0 else "command_exit_nonzero",
        "stdout_path": _rel_path(stdout_path),
        "stderr_path": _rel_path(stderr_path),
    }


def _failed_candidate_record(
    *,
    spec: SupplementalCandidateSpec,
    candidate_dir: Path,
    command_records: list[dict[str, Any]],
    failure_owner: str,
    failure_category: str,
    failed_record: dict[str, Any],
) -> dict[str, Any]:
    command_log_path = candidate_dir / "candidate_command_log.jsonl"
    _write_jsonl(command_log_path, command_records)
    return {
        "candidate_id": spec.candidate_id,
        "task_id": spec.task_id,
        "repository": spec.repository,
        "source_kind": "pr_issue_flow",
        "freeze_ready": False,
        "agent_run_ready": False,
        "visibility_counters": {
            "model_visible_leak_count": 0,
            "share_safe_violation_count": 0,
            "trainable_payload_contamination_count": 0,
            "raw_provider_content_leak_count": 0,
            "credential_marker_leak_count": 0,
        },
        "failure_owner": failure_owner,
        "failure_category": failure_category,
        "replacement_reason": "candidate probe failed before Stage 2B freeze gates",
        "stdout_sha256": failed_record.get("stdout_sha256"),
        "stderr_sha256": failed_record.get("stderr_sha256"),
        "candidate_command_log_ref": _stage2b_evidence_ref(command_log_path, kind="candidate_command_log", purpose=f"Candidate command log for failed {spec.candidate_id}"),
        "_command_records": command_records,
    }


def _supplemental_unknown_candidate_record(*, candidate_id: str, candidate_dir: Path) -> dict[str, Any]:
    candidate_dir.mkdir(parents=True, exist_ok=True)
    command_log_path = candidate_dir / "candidate_command_log.jsonl"
    _write_jsonl(command_log_path, [])
    return {
        "candidate_id": candidate_id,
        "task_id": _safe_candidate_id(candidate_id),
        "source_kind": "pr_issue_flow",
        "freeze_ready": False,
        "agent_run_ready": False,
        "visibility_counters": {
            "model_visible_leak_count": 0,
            "share_safe_violation_count": 0,
            "trainable_payload_contamination_count": 0,
            "raw_provider_content_leak_count": 0,
            "credential_marker_leak_count": 0,
        },
        "failure_owner": "repo_harness",
        "failure_category": "candidate_spec_missing",
        "replacement_reason": "candidate is not part of the reviewed Stage 2B default candidate registry",
        "candidate_command_log_ref": _stage2b_evidence_ref(command_log_path, kind="candidate_command_log", purpose=f"Candidate command log for unknown {candidate_id}"),
        "_command_records": [],
    }


def _venv_python_command(command: tuple[str, ...]) -> tuple[str, ...]:
    if not command:
        return command
    if command[0] == "python":
        return (".venv-stage2b/bin/python", *command[1:])
    return command


def _source_tree_hash_from_tar(path: Path) -> str:
    digest = sha256()
    with tarfile.open(path, "r") as archive:
        for member in sorted(archive.getmembers(), key=lambda item: item.name):
            if not member.isfile():
                continue
            digest.update(member.name.encode("utf-8"))
            extracted = archive.extractfile(member)
            if extracted is not None:
                digest.update(extracted.read())
    return digest.hexdigest()


def _tar_file_count(path: Path) -> int:
    with tarfile.open(path, "r") as archive:
        return sum(1 for member in archive.getmembers() if member.isfile())


def _supplemental_candidate_ready(
    *,
    baseline_probe: dict[str, Any],
    post_patch_probe: dict[str, Any],
    stable: bool,
    visibility_findings: list[dict[str, Any]],
) -> bool:
    baseline_exit_codes = list(baseline_probe.get("exit_codes") or [])
    post_patch_exit_codes = list(post_patch_probe.get("exit_codes") or [])
    return (
        bool(baseline_exit_codes)
        and all(code != 0 for code in baseline_exit_codes)
        and len(post_patch_exit_codes) >= 3
        and all(code == 0 for code in post_patch_exit_codes)
        and stable
        and not visibility_findings
    )


def _visibility_counters_clean(record: dict[str, Any]) -> bool:
    counters = record.get("visibility_counters")
    if not isinstance(counters, dict):
        return False
    return all(
        int(counters.get(key) or 0) == 0
        for key in (
            "model_visible_leak_count",
            "share_safe_violation_count",
            "trainable_payload_contamination_count",
            "raw_provider_content_leak_count",
            "credential_marker_leak_count",
        )
    )


def _supplemental_record_ready_for_merge(record: dict[str, Any]) -> bool:
    return (
        record.get("freeze_ready") is True
        and record.get("agent_run_ready") is True
        and record.get("baseline_expected_failure") is True
        and record.get("post_patch_passed") is True
        and record.get("flaky_probe_status") == "stable"
        and _visibility_counters_clean(record)
    )


def _ref_path_exists(ref: Any) -> bool:
    path = _path_from_ref_for_builder(ref)
    return path is not None and path.exists()


def _candidate_command_log_has_entries(ref: Any) -> bool:
    path = _path_from_ref_for_builder(ref)
    if path is None or not path.exists() or path.is_dir():
        return False
    try:
        return any(line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    except UnicodeDecodeError:
        return False


def _adapter_visible_ref_findings(adapter_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, ref in enumerate(adapter_refs, start=1):
        path = _path_from_ref_for_builder(ref)
        if path is None or not path.exists() or path.is_dir():
            findings.append(
                {
                    "finding_type": "adapter_visible_ref_missing",
                    "severity": "critical",
                    "ref_index": index,
                    "message": "adapter-visible ref cannot be resolved during Stage 2B merge",
                }
            )
            continue
        text = path.read_text(encoding="utf-8").lower()
        for marker in V5_FORBIDDEN_ADAPTER_VISIBLE_MARKERS:
            if marker.lower() in text:
                findings.append(
                    {
                        "finding_type": "adapter_visible_forbidden_marker",
                        "severity": "critical",
                        "ref_index": index,
                        "marker": marker,
                        "message": f"adapter-visible input contains forbidden marker: {marker}",
                    }
                )
    return findings


def _read_task_ref_payload(ref: dict[str, Any]) -> dict[str, Any]:
    payload = _read_ref_payload_for_builder(ref)
    if payload.get("schema_version") != V5_TASK_DEFINITION_VERSION:
        raise ConfigError(f"task ref 不是 V5 task definition：{ref.get('path')}")
    return payload


def _read_ref_payload_for_builder(ref: Any) -> dict[str, Any]:
    path = _path_from_ref_for_builder(ref)
    if path is None:
        raise ConfigError("evidence ref 缺少 path。")
    return _read_json(path)


def _path_from_ref_for_builder(ref: Any) -> Path | None:
    if not isinstance(ref, dict) or not ref.get("path"):
        return None
    path = Path(str(ref["path"]))
    if path.is_absolute():
        return path
    return Path.cwd() / path


def _stage2b_evidence_ref(
    path: Path,
    *,
    kind: str,
    purpose: str,
    visibility: str = "audit_only",
    share_safe: bool = False,
) -> dict[str, Any]:
    return _evidence_ref(
        path,
        kind=kind,
        purpose=purpose,
        visibility=visibility,
        producer_command="build-v5-supplemental-pr-issue-candidates",
        producer_stage="v5_stage2b_supplemental_pr_issue_candidates",
        inspect_command="inspect-v5-task-set",
        share_safe=share_safe,
    )


def _offline_command_record(*, command_name: str, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / f"{command_name}.stdout.txt"
    stderr_path = output_dir / f"{command_name}.stderr.txt"
    stdout_path.write_text("offline fixture probe\n", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    return {
        "schema_version": V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
        "command_name": command_name,
        "argv": [command_name],
        "cwd": Path.cwd().as_posix(),
        "builder_invocation_cwd": Path.cwd().as_posix(),
        "env_policy": "offline unit test fixture",
        "network_policy": "local_fixture_only",
        "risk_command_hits": [],
        "input_ref_policy": "offline fixture has no external inputs",
        "input_refs": [],
        "output_refs": [
            _stage2b_evidence_ref(stdout_path, kind="command_stdout", purpose=f"{command_name} stdout"),
            _stage2b_evidence_ref(stderr_path, kind="command_stderr", purpose=f"{command_name} stderr"),
        ],
        "started_at": _utc_timestamp(),
        "finished_at": _utc_timestamp(),
        "exit_code": 0,
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_sha256": sha256_file(stderr_path),
        "structured_skip_reason": None,
        "structured_failure_reason": None,
    }


def _safe_candidate_id(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_") or "candidate"


def _rel_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


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
