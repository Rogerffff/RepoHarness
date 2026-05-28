"""Stage 16G.2 structured file tool surface evidence and inspectors."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from repo_harness.errors import RepoHarnessError
from repo_harness.evaluation.episode_projection import (
    _FORBIDDEN_PUBLIC_MARKERS as PROJECTION_FORBIDDEN_PUBLIC_MARKERS,
    _RUNTIME_PRIVATE_REF_PATTERN,
)
from repo_harness.scaffolds import (
    build_planner_coder_verifier_scaffold,
    build_simple_react_scaffold,
)
from repo_harness.stage16g_tool_profile import (
    DEFAULT_STAGE16G1_DIR,
    PROFILE_IDS,
    inspect_stage16g1_tool_profile,
)
from repo_harness.tools import DEFAULT_TOOL_ORDER, build_tool, default_tool_registry


DEFAULT_STAGE16G2_DIR = Path("docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2")
DEFAULT_STAGE16G2_PLAN = Path("docs/agentic_RL/repo_harness_verl_workstreams/53-stage-16g-2-execution-plan.md")
DEFAULT_STAGE16G2B_PREFLIGHT_CORRECTION = Path(
    "docs/agentic_RL/repo_harness_verl_workstreams/54-stage-16g-2b-preflight-design-correction.md"
)
STAGE16G2A_NEW_TOOL_NAMES = ["write_file", "apply_patch", "delete_file", "move_file", "mkdir"]
STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES = ["write_file", "apply_patch"]
STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES = ["delete_file", "move_file", "mkdir"]
STAGE16G2A_DEFAULT_FILE_MUTATION_TOOLS = ["edit_file", "create_file", "write_file", "apply_patch"]
STAGE16G2A_P0_CAPABILITY_IDS = [
    "structured_edit_existing_file",
    "structured_write_or_create_file",
    "apply_patch_or_multi_file_edit",
    "delete_move_mkdir_file_operations",
]
STAGE16G2A_CAPABILITY_TOOL_IDS = {
    "structured_edit_existing_file": ["edit_file", "apply_patch"],
    "structured_write_or_create_file": ["create_file", "write_file"],
    "apply_patch_or_multi_file_edit": ["apply_patch"],
    "delete_move_mkdir_file_operations": ["apply_patch"],
    "task_management_todo": ["update_working_state"],
}
STAGE16G2A_CAPABILITY_OPERATION_IDS = {
    "delete_move_mkdir_file_operations": [
        "apply_patch.operations.delete_file",
        "apply_patch.operations.move_file",
        "apply_patch.operations.mkdir",
    ],
}
SAFE_STRUCTURED_ONLY_TOOLS = [
    "list_files",
    "glob_files",
    "read_file",
    "read_tool_result_artifact",
    "grep",
    "symbol_search",
    "update_working_state",
    "edit_file",
    "create_file",
    "write_file",
    "apply_patch",
    "git_diff",
]

REQUIRED_OUTPUT_FILES = [
    "implementation-notes.md",
    "stage16g2a_source_inventory.json",
    "stage16g2a_stage16g1_preflight_report.json",
    "stage16g2a_schema_registration_report.json",
    "stage16g2a_scaffold_exposure_report.json",
    "stage16g2a_tool_surface_delta.json",
    "stage16g2a_profile_delta_report.json",
    "stage16g2a_path_leak_scan_report.json",
    "stage16g2a_acceptance_summary.json",
]

STAGE16G2B_REQUIRED_OUTPUT_FILES = [
    "stage16g2b_file_mutation_probe_report.json",
    "stage16g2b_safety_denial_probe_report.json",
    "stage16g2b_path_leak_scan_report.json",
    "stage16g2b_acceptance_summary.json",
]

STAGE16G2B_SUMMARY_DIGEST_FIELDS = {
    "stage16g2b_file_mutation_probe_report.json": "file_mutation_probe_report_sha256",
    "stage16g2b_safety_denial_probe_report.json": "safety_denial_probe_report_sha256",
    "stage16g2b_path_leak_scan_report.json": "path_leak_scan_report_sha256",
}

STAGE16G2B_SOURCE_DIGEST_FILES = [
    "src/repo_harness/tools/file_mutation.py",
    "src/repo_harness/tools/minimal.py",
    "src/repo_harness/stage16g2_file_surface.py",
    "src/repo_harness/cli/main.py",
    "scripts/pre_verl/build_stage16g2b_file_mutation.py",
    "tests/unit/test_repo_harness_stage16g2b_file_mutation.py",
]

STAGE16G2C_REQUIRED_OUTPUT_FILES = [
    "stage16g2c_run_episode_projection_probe_report.json",
    "stage16g2c_projection_linkage_report.json",
    "stage16g2c_path_leak_scan_report.json",
    "stage16g2c_acceptance_summary.json",
]

STAGE16G2C_SUMMARY_DIGEST_FIELDS = {
    "stage16g2c_run_episode_projection_probe_report.json": "run_episode_projection_probe_report_sha256",
    "stage16g2c_projection_linkage_report.json": "projection_linkage_report_sha256",
    "stage16g2c_path_leak_scan_report.json": "path_leak_scan_report_sha256",
}

STAGE16G2C_SOURCE_DIGEST_FILES = [
    "src/repo_harness/tools/file_mutation.py",
    "src/repo_harness/tools/minimal.py",
    "src/repo_harness/evaluation/episode_projection.py",
    "src/repo_harness/rl/runtime.py",
    "src/repo_harness/stage16g2_file_surface.py",
    "src/repo_harness/cli/main.py",
    "scripts/pre_verl/build_stage16g2c_projection_linkage.py",
    "tests/unit/test_repo_harness_stage16g2c_projection_linkage.py",
]

SUMMARY_DIGEST_FIELDS = {
    "implementation-notes.md": "implementation_notes_sha256",
    "stage16g2a_source_inventory.json": "source_inventory_sha256",
    "stage16g2a_stage16g1_preflight_report.json": "stage16g1_preflight_report_sha256",
    "stage16g2a_schema_registration_report.json": "schema_registration_report_sha256",
    "stage16g2a_scaffold_exposure_report.json": "scaffold_exposure_report_sha256",
    "stage16g2a_tool_surface_delta.json": "tool_surface_delta_sha256",
    "stage16g2a_profile_delta_report.json": "profile_delta_report_sha256",
    "stage16g2a_path_leak_scan_report.json": "path_leak_scan_report_sha256",
}

SOURCE_FILES = [
    "src/repo_harness/tools/minimal.py",
    "src/repo_harness/tools/file_mutation.py",
    "src/repo_harness/permissions/system.py",
    "src/repo_harness/scaffolds/simple_react.py",
    "src/repo_harness/scaffolds/planner_coder_verifier.py",
    "src/repo_harness/stage16g2_file_surface.py",
    "src/repo_harness/cli/main.py",
    "scripts/pre_verl/build_stage16g2a_tool_surface.py",
    "scripts/pre_verl/build_stage16g2b_file_mutation.py",
    "tests/unit/test_repo_harness_stage16g2a_tool_surface.py",
    "tests/unit/test_repo_harness_stage16g2b_file_mutation.py",
]

SENSITIVE_PATTERNS = [
    re.compile(r"/Users/"),
    re.compile(r"/private/"),
    re.compile(r"/home/"),
    re.compile(r"/tmp/"),
    re.compile(r"/var/folders/"),
    re.compile(r"runtime_private(?:/|:|\s+path)"),
    re.compile(r"provider_secret\s*[:=]", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*[:=]", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
STAGE16G2_PUBLIC_MARKERS = tuple(PROJECTION_FORBIDDEN_PUBLIC_MARKERS)

STAGE16G2C_PROBE_KEYS = {
    "schema_version",
    "status",
    "run_episode_invocation",
    "projection_writer",
    "projection_created_from_run_episode",
    "projection_complete",
    "result_status",
    "result_status_reason",
    "final_verifier_accepted",
    "tool_names_observed",
    "tool_result_statuses",
    "operation_kinds_observed",
    "final_patch_sha256",
    "final_diff_sha256",
    "final_patch_changed_file_facts",
    "training_projection",
    "provider_route_qualification",
    "forbidden_model_visible_marker_scan_passed",
    "forbidden_model_visible_marker_findings",
    "public_safe_digest_only",
}
STAGE16G2C_PATCH_FACT_KEYS = {
    "entry_count",
    "added_count",
    "modified_count",
    "deleted_count",
    "renamed_count",
    "changed_paths",
    "entries",
}
STAGE16G2C_PATCH_ENTRY_KEYS = {"old_path", "new_path", "status"}
STAGE16G2C_TRAINING_PROJECTION_KEYS = {
    "training_view_projection_schema_version",
    "response_token_count",
    "response_mask_count",
    "response_span_count",
    "generation_record_count",
    "tool_observation_span_count",
    "tool_observation_spans_response_mask_zero",
    "tool_output_response_mask_zero_count",
    "assistant_response_mask_one_count",
    "online_rl_eligible",
    "invalid_for_training",
    "invalid_for_online_rl",
}
STAGE16G2C_PROVIDER_ROUTE_KEYS = {
    "provider_route",
    "llm_gateway_route",
    "formal_online_rl_eligible",
    "policy_loss_candidate",
    "qualification_reason",
}
STAGE16G2C_LINKAGE_KEYS = {
    "schema_version",
    "status",
    "compat_projection_file_count",
    "compat_projection_validation_error_count",
    "manifest_final_patch_sha256_matches_projection",
    "manifest_final_diff_sha256_matches_projection",
    "hygiene_cleaned_patch_sha256_matches_manifest",
    "hygiene_cleaned_diff_sha256_matches_manifest",
    "source_and_compat_final_patch_match",
    "source_and_compat_final_diff_match",
    "public_hygiene_report_contains_raw_fields",
    "patch_hygiene_status",
    "patch_hygiene_filtered_file_count",
    "patch_hygiene_flagged_file_count",
    "compat_projection_public_safe",
    "projection_source_result_digest_present",
    "projection_source_training_view_digest_present",
    "raw_artifact_private_by_omission",
}
STAGE16G2C_PATH_SCAN_KEYS = {
    "schema_version",
    "public_path_leak_scan_passed",
    "finding_count",
    "findings",
    "scanned_suffixes",
}


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _public_text_findings(relative_path: str, text: str) -> list[dict[str, str]]:
    normalized_text = _RUNTIME_PRIVATE_REF_PATTERN.sub("runtime-private:<kind>:<sha256>", text)
    findings: list[dict[str, str]] = []
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(normalized_text):
            findings.append({"relative_path": relative_path, "pattern": pattern.pattern})
    for marker in STAGE16G2_PUBLIC_MARKERS:
        if marker in normalized_text:
            findings.append({"relative_path": relative_path, "marker": marker})
    return findings


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: Any) -> str:
    path.write_text(_json_dumps(payload))
    return _file_sha256(path)


def _write_text(path: Path, text: str) -> str:
    path.write_text(text)
    return _file_sha256(path)


def _try_build_tool(tool_name: str) -> bool:
    try:
        build_tool(tool_name)
    except Exception:
        return False
    return True


def _source_entry(path: Path) -> dict[str, Any]:
    return {
        "relative_path": path.as_posix(),
        "exists": path.exists(),
        "sha256": _file_sha256(path) if path.exists() else None,
    }


def build_stage16g1_preflight_report(stage16g1_dir: Path = DEFAULT_STAGE16G1_DIR) -> dict[str, Any]:
    summary = stage16g1_dir / "stage16g1_acceptance_summary.json"
    try:
        inspection = json.loads(inspect_stage16g1_tool_profile(summary, assert_complete=True))
    except RepoHarnessError as exc:
        return {
            "schema_version": "stage16g2a.stage16g1_preflight_report.v1",
            "status": "failed",
            "stage16g1_summary_ref": summary.as_posix(),
            "preflight_passed_before_stage16g2a_code_edits": False,
            "failure": str(exc),
        }
    return {
        "schema_version": "stage16g2a.stage16g1_preflight_report.v1",
        "status": "passed",
        "stage16g1_summary_ref": summary.as_posix(),
        "preflight_passed_before_stage16g2a_code_edits": True,
        "validated_file_count": inspection.get("validated_file_count"),
        "failure_count": inspection.get("failure_count"),
        "failure_ids": inspection.get("failures", []),
        "derived_checks": inspection.get("derived_checks", {}),
    }


def build_source_inventory(
    *,
    stage16g1_dir: Path = DEFAULT_STAGE16G1_DIR,
    plan_path: Path = DEFAULT_STAGE16G2_PLAN,
    preflight_correction_path: Path = DEFAULT_STAGE16G2B_PREFLIGHT_CORRECTION,
) -> dict[str, Any]:
    input_files = [
        stage16g1_dir / "stage16g1_tool_registry_contract.json",
        stage16g1_dir / "stage16g1_profile_taxonomy.json",
        stage16g1_dir / "stage16g1_training_eligibility_gate_spec.json",
        stage16g1_dir / "stage16g1_acceptance_summary.json",
        plan_path,
        preflight_correction_path,
    ]
    return {
        "schema_version": "stage16g2a.source_inventory.v1",
        "source_inputs": [_source_entry(path) for path in input_files],
        "source_code_facts": [_source_entry(Path(path)) for path in SOURCE_FILES],
        "public_path_policy": "repo_relative_paths_and_sha256_only",
    }


def build_schema_registration_report() -> dict[str, Any]:
    registry_names = default_tool_registry().names()
    tool_records = []
    for tool_name in STAGE16G2A_NEW_TOOL_NAMES:
        tool = build_tool(tool_name)
        properties = tool.input_schema.get("properties", {})
        path_limit_fields = [
            field_name
            for field_name, schema in properties.items()
            if field_name in {"path", "source_path", "target_path"} and isinstance(schema, dict) and schema.get("maxLength")
        ]
        content_limit_fields = [
            field_name
            for field_name, schema in properties.items()
            if field_name in {"content", "old_text", "new_text", "reason"} and isinstance(schema, dict) and schema.get("maxLength")
        ]
        operations_schema = properties.get("operations", {})
        operation_item_schema = {}
        if isinstance(operations_schema, dict):
            operation_item_schema = operations_schema.get("items", {}) if isinstance(operations_schema.get("items"), dict) else {}
        operation_properties = operation_item_schema.get("properties", {}) if isinstance(operation_item_schema, dict) else {}
        tool_records.append(
            {
                "tool_name": tool_name,
                "tool_version": tool.tool_version,
                "buildable": True,
                "in_default_tool_order": tool_name in DEFAULT_TOOL_ORDER,
                "in_default_tool_registry": tool_name in registry_names,
                "is_destructive": tool.is_destructive,
                "is_read_only": tool.is_read_only,
                "behavior_stage": "16G.2B",
                "executor_binding_status": "stage16g2b_behavior_enabled",
                "required_fields": list(tool.input_schema.get("required", [])),
                "input_property_names": sorted(properties),
                "additional_properties_allowed": tool.input_schema.get("additionalProperties", True),
                "mode_enum": properties.get("mode", {}).get("enum"),
                "operations_max_items": operations_schema.get("maxItems") if isinstance(operations_schema, dict) else None,
                "operation_property_names": sorted(operation_properties) if isinstance(operation_properties, dict) else [],
                "path_limit_fields": path_limit_fields,
                "content_limit_fields": content_limit_fields,
                "input_limits_declared": bool(path_limit_fields or content_limit_fields or operations_schema.get("maxItems")),
                "unified_diff_property_present": "unified_diff" in properties,
                "operation_reason_property_present": "reason" in operation_properties,
                "top_level_reason_property_present": "reason" in properties,
                "reason_required": "reason" in set(tool.input_schema.get("required", [])),
                "upsert_exposed_in_core_schema": "upsert" in set(properties.get("mode", {}).get("enum", [])),
            }
        )
    return {
        "schema_version": "stage16g2a.schema_registration_report.v1",
        "new_tool_names": list(STAGE16G2A_NEW_TOOL_NAMES),
        "default_tool_order": list(DEFAULT_TOOL_ORDER),
        "registry_names": registry_names,
        "tool_records": tool_records,
        "all_new_tools_buildable": all(record["buildable"] for record in tool_records),
        "core_visible_new_tools": list(STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES),
        "standalone_operation_tool_names": list(STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES),
        "all_core_new_tools_in_default_tool_order": all(
            record["in_default_tool_order"]
            for record in tool_records
            if record["tool_name"] in STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES
        ),
        "standalone_operation_tools_not_in_default_tool_order": all(
            not record["in_default_tool_order"]
            for record in tool_records
            if record["tool_name"] in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES
        ),
        "all_new_tools_have_input_limits": all(record["input_limits_declared"] for record in tool_records),
        "apply_patch_operations_support_reason": any(
            record["tool_name"] == "apply_patch" and record["operation_reason_property_present"]
            for record in tool_records
        ),
        "standalone_delete_move_require_reason": all(
            record["reason_required"]
            for record in tool_records
            if record["tool_name"] in {"delete_file", "move_file"}
        ),
        "core_write_file_upsert_exposed": any(record["upsert_exposed_in_core_schema"] for record in tool_records),
        "apply_patch_unified_diff_exposed": any(record["unified_diff_property_present"] for record in tool_records),
    }


def build_scaffold_exposure_report() -> dict[str, Any]:
    simple = build_simple_react_scaffold()
    planner = build_planner_coder_verifier_scaffold()
    phase_tools = {
        phase: planner.allowed_tools_for_phase(phase)
        for phase in ["planner", "coder", "verifier", "repair", "final"]
    }
    patch_focused = {
        scaffold_id: []
        for scaffold_id in [
            "patch_focused_react",
            "patch_focused_react_execute_bash",
            "patch_focused_react_diagnostic_shell",
        ]
    }
    return {
        "schema_version": "stage16g2a.scaffold_exposure_report.v1",
        "new_tool_names": list(STAGE16G2A_NEW_TOOL_NAMES),
        "core_visible_new_tool_names": list(STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES),
        "standalone_operation_tool_names": list(STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES),
        "default_file_mutation_tools": list(STAGE16G2A_DEFAULT_FILE_MUTATION_TOOLS),
        "simple_react_allowed_tools": list(simple.allowed_tools),
        "simple_react_default_file_mutation_tools": [
            tool for tool in STAGE16G2A_DEFAULT_FILE_MUTATION_TOOLS if tool in simple.allowed_tools
        ],
        "simple_react_exposes_core_new_tools": all(
            tool in simple.allowed_tools for tool in STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES
        ),
        "simple_react_exposes_standalone_operation_tools": any(
            tool in simple.allowed_tools for tool in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES
        ),
        "planner_coder_verifier_phase_allowed_tools": phase_tools,
        "planner_exposes_write_tools": any(tool in phase_tools["planner"] for tool in STAGE16G2A_NEW_TOOL_NAMES),
        "coder_exposes_core_new_tools": all(
            tool in phase_tools["coder"] for tool in STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES
        ),
        "coder_exposes_standalone_operation_tools": any(
            tool in phase_tools["coder"] for tool in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES
        ),
        "verifier_exposes_write_tools": any(tool in phase_tools["verifier"] for tool in STAGE16G2A_NEW_TOOL_NAMES),
        "repair_exposes_core_new_tools": all(
            tool in phase_tools["repair"] for tool in STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES
        ),
        "repair_exposes_standalone_operation_tools": any(
            tool in phase_tools["repair"] for tool in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES
        ),
        "patch_focused_scaffolds_unchanged_for_stage16g2a": True,
        "patch_focused_new_tool_exposure": patch_focused,
    }


def build_tool_surface_delta(stage16g1_dir: Path = DEFAULT_STAGE16G1_DIR) -> dict[str, Any]:
    registry = _load_json(stage16g1_dir / "stage16g1_tool_registry_contract.json")
    records = []
    for record in registry["records"]:
        if record["owner_stage"] != "16G.2":
            continue
        capability_id = record["capability_id"]
        current_tool_ids = STAGE16G2A_CAPABILITY_TOOL_IDS.get(capability_id, record["tool_ids"])
        tool_build_status = {tool_id: _try_build_tool(tool_id) for tool_id in current_tool_ids}
        standalone_tool_ids = (
            list(STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES)
            if capability_id == "delete_move_mkdir_file_operations"
            else []
        )
        standalone_tool_build_status = {tool_id: _try_build_tool(tool_id) for tool_id in standalone_tool_ids}
        is_p0 = capability_id in STAGE16G2A_P0_CAPABILITY_IDS
        records.append(
            {
                "capability_id": capability_id,
                "priority": "P0" if is_p0 else "P2",
                "blocking_for_main_swe_rl": bool(record["blocking_for_main_swe_rl"]),
                "stage16g1_tool_ids": record["tool_ids"],
                "stage16g2a_tool_ids": current_tool_ids,
                "stage16g2a_internal_operation_ids": STAGE16G2A_CAPABILITY_OPERATION_IDS.get(capability_id, []),
                "stage16g2a_standalone_tool_ids": standalone_tool_ids,
                "tool_build_status": tool_build_status,
                "standalone_tool_build_status": standalone_tool_build_status,
                "stage16g1_model_visible_schema_status": record["model_visible_schema_status"],
                "stage16g2a_model_visible_schema_status": "implemented" if all(tool_build_status.values()) else "blocked",
                "stage16g1_scaffold_exposure_status": record["scaffold_exposure_status"],
                "stage16g2a_scaffold_exposure_status": (
                    "implemented_via_apply_patch_operations"
                    if capability_id == "delete_move_mkdir_file_operations"
                    else ("implemented" if is_p0 else "nonblocking_still_partial")
                ),
                "stage16g1_executor_binding_status": record["executor_binding_status"],
                "stage16g2a_executor_binding_status": (
                    "stage16g2b_behavior_enabled" if is_p0 else "nonblocking_no_change"
                ),
                "stage16g2a_delta_status": (
                    "schema_profile_scaffold_and_stage16g2b_behavior_enabled"
                    if is_p0
                    else "nonblocking_followup_not_required_for_16G2A"
                ),
                "allowed_in_policy_loss_trajectory": False,
                "sample_policy_loss_candidate_effect": "makes_sample_ineligible_until_stage16g2b_2c_complete",
            }
        )
    return {
        "schema_version": "stage16g2a.tool_surface_delta.v1",
        "source_registry": "stage16g1_tool_registry_contract",
        "owner_stage": "16G.2",
        "p0_capability_ids": list(STAGE16G2A_P0_CAPABILITY_IDS),
        "record_count": len(records),
        "records": records,
        "p0_schema_and_scaffold_exposure_complete": all(
            record["stage16g2a_model_visible_schema_status"] == "implemented"
            and record["stage16g2a_scaffold_exposure_status"] in {
                "implemented",
                "implemented_via_apply_patch_operations",
            }
            for record in records
            if record["capability_id"] in STAGE16G2A_P0_CAPABILITY_IDS
        ),
    }


def build_profile_delta_report(stage16g1_dir: Path = DEFAULT_STAGE16G1_DIR) -> dict[str, Any]:
    taxonomy = _load_json(stage16g1_dir / "stage16g1_profile_taxonomy.json")
    taxonomy_by_id = {profile["profile_id"]: profile for profile in taxonomy["profiles"]}
    profile_tool_sets = {
        "safe_structured_only": list(SAFE_STRUCTURED_ONLY_TOOLS),
        "swe_public_core": list(DEFAULT_TOOL_ORDER),
        "swe_public_extended": (
            list(DEFAULT_TOOL_ORDER)
            + list(STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES)
            + ["execute_bash", "diagnostic_shell"]
        ),
        "redteam_restricted": [],
    }
    profiles = []
    for profile_id in PROFILE_IDS:
        tool_names = profile_tool_sets[profile_id]
        profiles.append(
            {
                "profile_id": profile_id,
                "stage16g1_allowed_capability_ids": taxonomy_by_id[profile_id]["allowed_capability_ids"],
                "stage16g2a_tool_names": tool_names,
                "stage16g2a_new_tool_names": [
                    tool_name for tool_name in STAGE16G2A_NEW_TOOL_NAMES if tool_name in tool_names
                ],
                "stage16g2a_core_visible_new_tool_names": [
                    tool_name for tool_name in STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES if tool_name in tool_names
                ],
                "stage16g2a_standalone_operation_tool_names": [
                    tool_name for tool_name in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES if tool_name in tool_names
                ],
                "persistent_diagnostic_shell_in_profile": "diagnostic_shell" in tool_names,
                "execute_bash_in_profile": "execute_bash" in tool_names,
                "primary_training_default": profile_id == "swe_public_core",
                "training_projection_state_for_new_tools": {
                    tool_name: {
                        "model_visible_schema_status": (
                            "implemented"
                            if tool_name in tool_names
                            else "internal_operation_via_apply_patch"
                        ),
                        "scaffold_exposure_status": (
                            "implemented"
                            if tool_name in tool_names
                            else (
                                "covered_by_apply_patch_operations"
                                if tool_name in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES
                                and "apply_patch" in tool_names
                                else "not_default"
                            )
                        ),
                        "executor_binding_status": "stage16g2b_behavior_enabled",
                        "allowed_in_policy_loss_trajectory": False,
                        "sample_policy_loss_candidate_effect": "makes_sample_ineligible_until_stage16g2b_2c_complete",
                    }
                    for tool_name in STAGE16G2A_NEW_TOOL_NAMES
                },
            }
        )
    return {
        "schema_version": "stage16g2a.profile_delta_report.v1",
        "profile_count": len(profiles),
        "profiles": profiles,
        "derived_from_stage16g1_profile_taxonomy": True,
        "derived_from_current_tool_registry": True,
        "swe_public_core_excludes_persistent_shell": "diagnostic_shell" not in profile_tool_sets["swe_public_core"],
        "swe_public_core_excludes_execute_bash": "execute_bash" not in profile_tool_sets["swe_public_core"],
        "swe_public_core_contains_core_new_tools": all(
            tool_name in profile_tool_sets["swe_public_core"] for tool_name in STAGE16G2A_CORE_VISIBLE_NEW_TOOL_NAMES
        ),
        "swe_public_core_excludes_standalone_operation_tools": all(
            tool_name not in profile_tool_sets["swe_public_core"]
            for tool_name in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES
        ),
        "swe_public_extended_contains_standalone_operation_tools": all(
            tool_name in profile_tool_sets["swe_public_extended"]
            for tool_name in STAGE16G2A_STANDALONE_OPERATION_TOOL_NAMES
        ),
        "redteam_restricted_primary_training_default": False,
    }


def _scan_public_files(output_dir: Path) -> dict[str, Any]:
    findings = []
    candidates = [output_dir / "implementation-notes.md"]
    candidates.extend(sorted(output_dir.glob("stage16g2a_*")))
    for path in candidates:
        if not path.exists() or path.name == "stage16g2a_path_leak_scan_report.json":
            continue
        if path.suffix not in {".json", ".md"}:
            continue
        text = path.read_text()
        findings.extend(_public_text_findings(path.name, text))
    return {
        "schema_version": "stage16g2a.path_leak_scan_report.v1",
        "public_path_leak_scan_passed": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "scanned_suffixes": [".json", ".md"],
    }


def scan_stage16g2b_public_files(output_dir: Path) -> dict[str, Any]:
    findings = []
    for path in sorted(output_dir.glob("stage16g2b_*")):
        if not path.exists() or path.name == "stage16g2b_path_leak_scan_report.json":
            continue
        if path.suffix != ".json":
            continue
        text = path.read_text()
        findings.extend(_public_text_findings(path.name, text))
    return {
        "schema_version": "stage16g2b.path_leak_scan_report.v1",
        "public_path_leak_scan_passed": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "scanned_suffixes": [".json"],
    }


def scan_stage16g2c_public_files(output_dir: Path) -> dict[str, Any]:
    findings = []
    for path in sorted(output_dir.glob("stage16g2c_*")):
        if not path.exists() or path.name == "stage16g2c_path_leak_scan_report.json":
            continue
        if path.suffix != ".json":
            continue
        text = path.read_text()
        findings.extend(_public_text_findings(path.name, text))
    return {
        "schema_version": "stage16g2c.path_leak_scan_report.v1",
        "public_path_leak_scan_passed": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "scanned_suffixes": [".json"],
    }


def _source_inventory_failures(source_inventory: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if source_inventory.get("schema_version") != "stage16g2a.source_inventory.v1":
        failures.append("source_inventory_schema_version_mismatch")
    expected_input_names = {
        "stage16g1_tool_registry_contract.json",
        "stage16g1_profile_taxonomy.json",
        "stage16g1_training_eligibility_gate_spec.json",
        "stage16g1_acceptance_summary.json",
        DEFAULT_STAGE16G2_PLAN.name,
        DEFAULT_STAGE16G2B_PREFLIGHT_CORRECTION.name,
    }
    input_entries = source_inventory.get("source_inputs")
    if not isinstance(input_entries, list):
        failures.append("source_inventory_inputs_not_list")
        input_entries = []
    input_names = {
        Path(str(entry.get("relative_path", ""))).name
        for entry in input_entries
        if isinstance(entry, dict)
    }
    if input_names != expected_input_names:
        failures.append("source_inventory_input_names_mismatch")
    for expected_name in sorted(expected_input_names - input_names):
        failures.append(f"source_inventory_missing_input:{expected_name}")

    source_entries = source_inventory.get("source_code_facts")
    if not isinstance(source_entries, list):
        failures.append("source_inventory_source_code_facts_not_list")
        source_entries = []
    source_paths = {
        str(entry.get("relative_path", ""))
        for entry in source_entries
        if isinstance(entry, dict)
    }
    expected_source_paths = set(SOURCE_FILES)
    if source_paths != expected_source_paths:
        failures.append("source_inventory_source_paths_mismatch")
    for expected_path in sorted(expected_source_paths - source_paths):
        failures.append(f"source_inventory_missing_source:{expected_path}")

    for group_name, entries in (("input", input_entries), ("source", source_entries)):
        for entry in entries:
            if not isinstance(entry, dict):
                failures.append(f"source_inventory_{group_name}_entry_not_object")
                continue
            relative_path = entry.get("relative_path")
            if not isinstance(relative_path, str) or not relative_path:
                failures.append(f"source_inventory_{group_name}_entry_missing_path")
                continue
            path = Path(relative_path)
            if entry.get("exists") is not True:
                failures.append(f"source_inventory_{group_name}_not_marked_existing:{relative_path}")
            if not path.exists():
                failures.append(f"source_inventory_{group_name}_missing_on_disk:{relative_path}")
                continue
            if entry.get("sha256") != _file_sha256(path):
                failures.append(f"source_inventory_{group_name}_sha256_mismatch:{relative_path}")
    return failures


def _stage16g1_dir_from_source_inventory(source_inventory: dict[str, Any]) -> Path:
    for entry in source_inventory.get("source_inputs", []):
        if not isinstance(entry, dict):
            continue
        relative_path = entry.get("relative_path")
        if not isinstance(relative_path, str):
            continue
        path = Path(relative_path)
        if path.name == "stage16g1_acceptance_summary.json":
            return path.parent
    return DEFAULT_STAGE16G1_DIR


def _canonical_report_mismatches(
    *,
    source_inventory: dict[str, Any],
    schema: dict[str, Any],
    scaffold: dict[str, Any],
    surface: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[list[str], dict[str, bool]]:
    stage16g1_dir = _stage16g1_dir_from_source_inventory(source_inventory)
    expected_reports = {
        "schema_registration_report": build_schema_registration_report(),
        "scaffold_exposure_report": build_scaffold_exposure_report(),
        "tool_surface_delta_report": build_tool_surface_delta(stage16g1_dir),
        "profile_delta_report": build_profile_delta_report(stage16g1_dir),
    }
    actual_reports = {
        "schema_registration_report": schema,
        "scaffold_exposure_report": scaffold,
        "tool_surface_delta_report": surface,
        "profile_delta_report": profile,
    }
    checks = {
        f"{report_name}_matches_current_code": actual_reports[report_name] == expected_report
        for report_name, expected_report in expected_reports.items()
    }
    failures = [
        f"{report_name}_stale_or_mismatched"
        for report_name, expected_report in expected_reports.items()
        if actual_reports[report_name] != expected_report
    ]
    return failures, checks


def build_stage16g2a_validation(reports: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    source_inventory = reports["stage16g2a_source_inventory.json"]
    preflight = reports["stage16g2a_stage16g1_preflight_report.json"]
    schema = reports["stage16g2a_schema_registration_report.json"]
    scaffold = reports["stage16g2a_scaffold_exposure_report.json"]
    surface = reports["stage16g2a_tool_surface_delta.json"]
    profile = reports["stage16g2a_profile_delta_report.json"]
    path_scan = reports["stage16g2a_path_leak_scan_report.json"]
    source_inventory_failures = _source_inventory_failures(source_inventory)
    failures.extend(source_inventory_failures)
    canonical_failures, canonical_checks = _canonical_report_mismatches(
        source_inventory=source_inventory,
        schema=schema,
        scaffold=scaffold,
        surface=surface,
        profile=profile,
    )
    failures.extend(canonical_failures)

    if preflight.get("status") != "passed" or preflight.get("failure_count") != 0:
        failures.append("stage16g1_preflight_failed")
    if not schema.get("all_new_tools_buildable"):
        failures.append("new_tools_not_all_buildable")
    if not schema.get("all_core_new_tools_in_default_tool_order"):
        failures.append("core_new_tools_not_all_in_default_tool_order")
    if not schema.get("standalone_operation_tools_not_in_default_tool_order"):
        failures.append("standalone_operation_tools_exposed_in_default_tool_order")
    if not schema.get("all_new_tools_have_input_limits"):
        failures.append("new_tools_missing_input_limits")
    if not schema.get("apply_patch_operations_support_reason"):
        failures.append("apply_patch_operations_missing_model_reason_field")
    if not schema.get("standalone_delete_move_require_reason"):
        failures.append("standalone_delete_move_missing_model_reason_requirement")
    if schema.get("core_write_file_upsert_exposed"):
        failures.append("write_file_upsert_exposed_in_core_schema")
    if schema.get("apply_patch_unified_diff_exposed"):
        failures.append("apply_patch_unified_diff_exposed")
    if not scaffold.get("simple_react_exposes_core_new_tools"):
        failures.append("simple_react_missing_core_new_tools")
    if scaffold.get("simple_react_exposes_standalone_operation_tools"):
        failures.append("simple_react_exposes_standalone_operation_tools")
    if scaffold.get("planner_exposes_write_tools"):
        failures.append("planner_phase_exposes_write_tools")
    if scaffold.get("verifier_exposes_write_tools"):
        failures.append("verifier_phase_exposes_write_tools")
    if not scaffold.get("coder_exposes_core_new_tools"):
        failures.append("coder_phase_missing_core_new_tools")
    if scaffold.get("coder_exposes_standalone_operation_tools"):
        failures.append("coder_phase_exposes_standalone_operation_tools")
    if not scaffold.get("repair_exposes_core_new_tools"):
        failures.append("repair_phase_missing_core_new_tools")
    if scaffold.get("repair_exposes_standalone_operation_tools"):
        failures.append("repair_phase_exposes_standalone_operation_tools")
    if not scaffold.get("patch_focused_scaffolds_unchanged_for_stage16g2a"):
        failures.append("patch_focused_scaffolds_changed")
    if surface.get("record_count") != 5:
        failures.append("stage16g2_owner_record_count_not_5")
    if not surface.get("p0_schema_and_scaffold_exposure_complete"):
        failures.append("p0_schema_scaffold_exposure_incomplete")
    if set(profile.get("profiles", [{}])[index].get("profile_id") for index in range(len(profile.get("profiles", [])))) != set(PROFILE_IDS):
        failures.append("profile_ids_mismatch")
    if not profile.get("swe_public_core_excludes_persistent_shell"):
        failures.append("swe_public_core_contains_persistent_shell")
    if not profile.get("swe_public_core_contains_core_new_tools"):
        failures.append("swe_public_core_missing_core_new_tools")
    if not profile.get("swe_public_core_excludes_standalone_operation_tools"):
        failures.append("swe_public_core_contains_standalone_operation_tools")
    if not profile.get("swe_public_extended_contains_standalone_operation_tools"):
        failures.append("swe_public_extended_missing_standalone_operation_tools")
    if profile.get("redteam_restricted_primary_training_default"):
        failures.append("redteam_restricted_marked_primary_training_default")
    for profile_record in profile.get("profiles", []):
        for tool_state in profile_record.get("training_projection_state_for_new_tools", {}).values():
            if tool_state.get("allowed_in_policy_loss_trajectory"):
                failures.append(f"stage16g2a_tool_policy_loss_allowed:{profile_record.get('profile_id')}")
                break
    if not path_scan.get("public_path_leak_scan_passed"):
        failures.append("public_path_leak_scan_failed")

    return {
        "schema_version": "stage16g2a.validation_report.v1",
        "status": "passed" if not failures else "failed",
        "failure_count": len(failures),
        "failures": failures,
        "checks": {
            "stage16g1_preflight_passed": preflight.get("status") == "passed",
            "source_inventory_semantically_valid": not source_inventory_failures,
            "all_new_tools_buildable": bool(schema.get("all_new_tools_buildable")),
            "all_core_new_tools_in_default_tool_order": bool(schema.get("all_core_new_tools_in_default_tool_order")),
            "standalone_operation_tools_not_in_default_tool_order": bool(
                schema.get("standalone_operation_tools_not_in_default_tool_order")
            ),
            "core_write_file_upsert_hidden": not bool(schema.get("core_write_file_upsert_exposed")),
            "all_new_tools_have_input_limits": bool(schema.get("all_new_tools_have_input_limits")),
            "apply_patch_operations_support_reason": bool(schema.get("apply_patch_operations_support_reason")),
            "standalone_delete_move_require_reason": bool(schema.get("standalone_delete_move_require_reason")),
            "apply_patch_unified_diff_not_exposed": not bool(schema.get("apply_patch_unified_diff_exposed")),
            "simple_react_exposes_core_new_tools": bool(scaffold.get("simple_react_exposes_core_new_tools")),
            "simple_react_excludes_standalone_operation_tools": not bool(
                scaffold.get("simple_react_exposes_standalone_operation_tools")
            ),
            "planner_and_verifier_do_not_expose_write_tools": (
                not scaffold.get("planner_exposes_write_tools") and not scaffold.get("verifier_exposes_write_tools")
            ),
            "coder_and_repair_expose_core_new_tools": (
                bool(scaffold.get("coder_exposes_core_new_tools")) and bool(scaffold.get("repair_exposes_core_new_tools"))
            ),
            "coder_and_repair_exclude_standalone_operation_tools": (
                not scaffold.get("coder_exposes_standalone_operation_tools")
                and not scaffold.get("repair_exposes_standalone_operation_tools")
            ),
            "p0_schema_and_scaffold_exposure_complete": bool(surface.get("p0_schema_and_scaffold_exposure_complete")),
            "swe_public_core_excludes_persistent_shell": bool(profile.get("swe_public_core_excludes_persistent_shell")),
            "swe_public_core_contains_core_new_tools": bool(profile.get("swe_public_core_contains_core_new_tools")),
            "swe_public_core_excludes_standalone_operation_tools": bool(
                profile.get("swe_public_core_excludes_standalone_operation_tools")
            ),
            "swe_public_extended_contains_standalone_operation_tools": bool(
                profile.get("swe_public_extended_contains_standalone_operation_tools")
            ),
            "new_tools_policy_loss_ineligible_until_16g2b_2c": not any(
                tool_state.get("allowed_in_policy_loss_trajectory")
                for profile_record in profile.get("profiles", [])
                for tool_state in profile_record.get("training_projection_state_for_new_tools", {}).values()
            ),
            "public_path_leak_scan_passed": bool(path_scan.get("public_path_leak_scan_passed")),
            **canonical_checks,
        },
    }


def build_acceptance_summary(
    *,
    reports: dict[str, Any],
    digests: dict[str, str],
) -> dict[str, Any]:
    validation = build_stage16g2a_validation(reports)
    status = "passed" if validation["status"] == "passed" else "failed"
    return {
        "schema_version": "stage16g2a.acceptance_summary.v1",
        "status": status,
        "stage16g2a_complete": status == "passed",
        "stage16g2b_allowed_to_start": status == "passed",
        "stage16g3_allowed_to_start": False,
        "stage17b_real_data_freeze_allowed": False,
        "stage20_warm_start_data_generation_allowed": False,
        "stage21_formal_rl_allowed": False,
        "new_tool_names": list(STAGE16G2A_NEW_TOOL_NAMES),
        "p0_capability_ids": list(STAGE16G2A_P0_CAPABILITY_IDS),
        "stage16g1_preflight_inspection_passed": reports["stage16g2a_stage16g1_preflight_report.json"]["status"] == "passed",
        "schema_registration_passed": validation["checks"]["all_new_tools_buildable"],
        "profile_delta_passed": (
            validation["checks"]["swe_public_core_contains_core_new_tools"]
            and validation["checks"]["swe_public_core_excludes_standalone_operation_tools"]
        ),
        "input_limit_schema_passed": validation["checks"]["all_new_tools_have_input_limits"],
        "scaffold_exposure_passed": (
            validation["checks"]["simple_react_exposes_core_new_tools"]
            and validation["checks"]["simple_react_excludes_standalone_operation_tools"]
        ),
        "reason_schema_passed": (
            validation["checks"]["apply_patch_operations_support_reason"]
            and validation["checks"]["standalone_delete_move_require_reason"]
        ),
        "public_path_leak_scan_passed": validation["checks"]["public_path_leak_scan_passed"],
        "machine_inspector_passed": validation["status"] == "passed",
        "failure_count": validation["failure_count"],
        "failure_ids": validation["failures"],
        **{field: digests[filename] for filename, field in SUMMARY_DIGEST_FIELDS.items()},
    }


def build_stage16g2a_reports(
    *,
    stage16g1_dir: Path = DEFAULT_STAGE16G1_DIR,
    plan_path: Path = DEFAULT_STAGE16G2_PLAN,
) -> dict[str, Any]:
    reports = {
        "stage16g2a_source_inventory.json": build_source_inventory(stage16g1_dir=stage16g1_dir, plan_path=plan_path),
        "stage16g2a_stage16g1_preflight_report.json": build_stage16g1_preflight_report(stage16g1_dir),
        "stage16g2a_schema_registration_report.json": build_schema_registration_report(),
        "stage16g2a_scaffold_exposure_report.json": build_scaffold_exposure_report(),
        "stage16g2a_tool_surface_delta.json": build_tool_surface_delta(stage16g1_dir),
        "stage16g2a_profile_delta_report.json": build_profile_delta_report(stage16g1_dir),
    }
    reports["stage16g2a_path_leak_scan_report.json"] = {
        "schema_version": "stage16g2a.path_leak_scan_report.v1",
        "public_path_leak_scan_passed": True,
        "finding_count": 0,
        "findings": [],
        "scanned_suffixes": [".json", ".md"],
    }
    return reports


def _default_implementation_notes() -> str:
    return (
        "# Stage 16G.2A Implementation Notes\n\n"
        "- Stage 16G.2A 只启用 schema、profile 和 scaffold 暴露，不启用真实文件写入行为。\n"
        "- 新工具 executor 返回结构化拒绝，真实行为留给 Stage 16G.2B。\n"
        "- `write_file` core schema 不暴露 upsert。\n"
        "- `delete_file`、`move_file`、`mkdir` 不进入主训练默认工具面；默认通过 `apply_patch.operations` 表达。\n"
    )


def write_stage16g2a_reports(
    output_dir: Path = DEFAULT_STAGE16G2_DIR,
    stage16g1_dir: Path = DEFAULT_STAGE16G1_DIR,
    plan_path: Path = DEFAULT_STAGE16G2_PLAN,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    notes_path = output_dir / "implementation-notes.md"
    if not notes_path.exists():
        _write_text(notes_path, _default_implementation_notes())
    reports = build_stage16g2a_reports(stage16g1_dir=stage16g1_dir, plan_path=plan_path)
    digests = {"implementation-notes.md": _file_sha256(notes_path)}
    for filename, payload in reports.items():
        digests[filename] = _write_json(output_dir / filename, payload)
    path_scan = _scan_public_files(output_dir)
    reports["stage16g2a_path_leak_scan_report.json"] = path_scan
    digests["stage16g2a_path_leak_scan_report.json"] = _write_json(
        output_dir / "stage16g2a_path_leak_scan_report.json", path_scan
    )
    summary = build_acceptance_summary(reports=reports, digests=digests)
    reports["stage16g2a_acceptance_summary.json"] = summary
    digests["stage16g2a_acceptance_summary.json"] = _write_json(
        output_dir / "stage16g2a_acceptance_summary.json", summary
    )
    path_scan = _scan_public_files(output_dir)
    reports["stage16g2a_path_leak_scan_report.json"] = path_scan
    digests["stage16g2a_path_leak_scan_report.json"] = _write_json(
        output_dir / "stage16g2a_path_leak_scan_report.json", path_scan
    )
    summary = build_acceptance_summary(reports=reports, digests=digests)
    digests["stage16g2a_acceptance_summary.json"] = _write_json(
        output_dir / "stage16g2a_acceptance_summary.json", summary
    )
    return digests


def _load_stage16g2a_dir(summary_path: Path) -> dict[str, Any]:
    base = summary_path.parent
    payloads: dict[str, Any] = {}
    for filename in REQUIRED_OUTPUT_FILES:
        path = base / filename
        if not path.exists():
            continue
        if filename.endswith(".md"):
            payloads[filename] = path.read_text()
        else:
            payloads[filename] = _load_json(path)
    return payloads


def inspect_stage16g2a_tool_surface(summary_path: str | Path, *, assert_complete: bool = False) -> str:
    summary = Path(summary_path)
    if not summary.exists():
        raise RepoHarnessError(f"Stage 16G.2A acceptance summary not found: {summary}")
    base = summary.parent
    payloads = _load_stage16g2a_dir(summary)
    failures: list[str] = []
    missing = [filename for filename in REQUIRED_OUTPUT_FILES if filename not in payloads]
    failures.extend(f"missing_required_file:{filename}" for filename in missing)
    if missing:
        report = {
            "schema_version": "stage16g2a.cli_inspection_result.v1",
            "status": "failed",
            "failure_count": len(failures),
            "failures": failures,
        }
        if assert_complete:
            raise RepoHarnessError(_json_dumps(report))
        return _json_dumps(report)

    actual_digests = {filename: _file_sha256(base / filename) for filename in REQUIRED_OUTPUT_FILES}
    summary_payload = payloads["stage16g2a_acceptance_summary.json"]
    for filename, field_name in SUMMARY_DIGEST_FIELDS.items():
        if summary_payload.get(field_name) != actual_digests[filename]:
            failures.append(f"sha256_mismatch:{filename}")

    current_path_scan = _scan_public_files(base)
    if current_path_scan != payloads["stage16g2a_path_leak_scan_report.json"]:
        failures.append("path_leak_scan_report_stale_or_mismatched")
    reports = {key: value for key, value in payloads.items() if key.endswith(".json")}
    reports["stage16g2a_path_leak_scan_report.json"] = current_path_scan
    validation = build_stage16g2a_validation(reports)
    failures.extend(validation["failures"])

    expected_summary = build_acceptance_summary(reports=reports, digests=actual_digests)
    for field_name, expected_value in expected_summary.items():
        if summary_payload.get(field_name) != expected_value:
            failures.append(f"acceptance_summary_field_mismatch:{field_name}")
    for field_name in sorted(set(summary_payload) - set(expected_summary)):
        failures.append(f"acceptance_summary_unexpected_field:{field_name}")

    report = {
        "schema_version": "stage16g2a.cli_inspection_result.v1",
        "status": "passed" if not failures else "failed",
        "summary_path": summary.name,
        "failure_count": len(failures),
        "failures": failures,
        "validated_file_count": len(REQUIRED_OUTPUT_FILES),
        "derived_checks": validation["checks"],
    }
    if assert_complete and failures:
        raise RepoHarnessError(_json_dumps(report))
    return _json_dumps(report)


def _load_stage16g2b_dir(summary_path: Path) -> dict[str, Any]:
    base = summary_path.parent
    payloads: dict[str, Any] = {}
    for filename in STAGE16G2B_REQUIRED_OUTPUT_FILES:
        path = base / filename
        if path.exists():
            payloads[filename] = _load_json(path)
    return payloads


def _stage16g2b_validation_failures(payloads: dict[str, Any], *, base: Path) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    summary = payloads["stage16g2b_acceptance_summary.json"]
    mutation = payloads["stage16g2b_file_mutation_probe_report.json"]
    safety = payloads["stage16g2b_safety_denial_probe_report.json"]
    path_scan = payloads["stage16g2b_path_leak_scan_report.json"]

    if summary.get("schema_version") != "stage16g2b.acceptance_summary.v1":
        failures.append("summary_schema_version_mismatch")
    if mutation.get("schema_version") != "stage16g2b.file_mutation_probe_report.v1":
        failures.append("mutation_probe_schema_version_mismatch")
    if safety.get("schema_version") != "stage16g2b.safety_denial_probe_report.v1":
        failures.append("safety_probe_schema_version_mismatch")
    if path_scan.get("schema_version") != "stage16g2b.path_leak_scan_report.v1":
        failures.append("path_scan_schema_version_mismatch")

    if summary.get("status") != "passed" or summary.get("stage16g2b_complete") is not True:
        failures.append("stage16g2b_summary_not_passed")
    if summary.get("stage16g2c_allowed_to_start") is not True:
        failures.append("stage16g2c_not_allowed_after_16g2b")
    if summary.get("stage16g3_allowed_to_start") is not False:
        failures.append("stage16g3_allowed_too_early")
    if summary.get("stage17b_real_data_freeze_allowed") is not False:
        failures.append("stage17b_allowed_too_early")
    if summary.get("default_behavior_enabled_tools") != ["write_file", "apply_patch"]:
        failures.append("default_behavior_enabled_tools_mismatch")
    if summary.get("standalone_tools_default_visible") is not False:
        failures.append("standalone_tools_marked_default_visible")
    if summary.get("standalone_tools_extended_executable") is not True:
        failures.append("standalone_tools_not_marked_extended_executable")
    if summary.get("policy_loss_candidate_for_new_tools") is not False:
        failures.append("new_tools_policy_loss_enabled_too_early")
    if summary.get("next_required_stage_for_policy_loss") != "16G.2C":
        failures.append("next_policy_loss_stage_mismatch")
    if summary.get("unary_delete_supported_by_apply_patch") is not True:
        failures.append("unary_delete_not_supported_by_apply_patch")
    if summary.get("unary_move_supported_by_apply_patch") is not True:
        failures.append("unary_move_not_supported_by_apply_patch")
    if summary.get("atomic_preflight_passed") is not True:
        failures.append("atomic_preflight_not_passed")

    for filename, field_name in STAGE16G2B_SUMMARY_DIGEST_FIELDS.items():
        if summary.get(field_name) != _file_sha256(base / filename):
            failures.append(f"stage16g2b_sha256_mismatch:{filename}")

    source_digests = summary.get("source_digests")
    if not isinstance(source_digests, dict):
        failures.append("source_digests_missing")
    else:
        for relative_path in STAGE16G2B_SOURCE_DIGEST_FILES:
            source_path = Path(relative_path)
            if not source_path.exists():
                failures.append(f"source_digest_file_missing:{relative_path}")
                continue
            if source_digests.get(relative_path) != _file_sha256(source_path):
                failures.append(f"source_digest_mismatch:{relative_path}")
        for relative_path in sorted(set(source_digests) - set(STAGE16G2B_SOURCE_DIGEST_FILES)):
            failures.append(f"source_digest_unexpected_file:{relative_path}")

    current_path_scan = scan_stage16g2b_public_files(base)
    if current_path_scan != path_scan:
        failures.append("stage16g2b_path_leak_scan_report_stale_or_mismatched")
    if not current_path_scan.get("public_path_leak_scan_passed"):
        failures.append("stage16g2b_public_path_leak_scan_failed")

    core_results = mutation.get("core_default_tool_behavior", [])
    extended_results = mutation.get("extended_tool_behavior", [])
    if not isinstance(core_results, list) or not isinstance(extended_results, list):
        failures.append("mutation_probe_result_lists_missing")
        core_results = []
        extended_results = []
    core_by_label = {record.get("label"): record for record in core_results if isinstance(record, dict)}
    extended_by_label = {record.get("label"): record for record in extended_results if isinstance(record, dict)}
    for label in [
        "write_file_create",
        "write_file_overwrite",
        "apply_patch_batch",
        "apply_patch_unary_delete",
        "apply_patch_unary_move",
    ]:
        record = core_by_label.get(label)
        if not isinstance(record, dict) or record.get("status") != "ok":
            failures.append(f"core_mutation_probe_missing_or_failed:{label}")
            continue
        if record.get("repository_mutation_performed") is not True:
            failures.append(f"core_mutation_probe_not_marked_mutating:{label}")
        if not isinstance(record.get("changed_path_count"), int) or record.get("changed_path_count") <= 0:
            failures.append(f"core_mutation_probe_changed_path_count_missing:{label}")
        if record.get("partial_failure") is not False:
            failures.append(f"core_mutation_probe_partial_failure:{label}")
        if record.get("allowed_in_policy_loss_trajectory") is not False:
            failures.append(f"core_mutation_probe_policy_loss_trajectory_enabled:{label}")
        if record.get("policy_loss_candidate") is not False:
            failures.append(f"core_mutation_probe_policy_loss_enabled:{label}")
        if record.get("official_prediction_eligible") is not False:
            failures.append(f"core_mutation_probe_official_prediction_enabled:{label}")
        if record.get("training_export_eligible") is not False:
            failures.append(f"core_mutation_probe_training_export_enabled:{label}")
        if record.get("sample_policy_loss_candidate_effect") != "requires_stage16g2c_patch_projection_linkage":
            failures.append(f"core_mutation_probe_policy_loss_effect_mismatch:{label}")
    batch_kinds = set(core_by_label.get("apply_patch_batch", {}).get("operation_kinds", []))
    if batch_kinds != {"replace_text", "write_file", "delete_file", "move_file", "mkdir"}:
        failures.append("apply_patch_batch_operation_kinds_mismatch")
    if core_by_label.get("apply_patch_unary_delete", {}).get("operation_kinds") != ["delete_file"]:
        failures.append("apply_patch_unary_delete_operation_kind_mismatch")
    if core_by_label.get("apply_patch_unary_move", {}).get("operation_kinds") != ["move_file"]:
        failures.append("apply_patch_unary_move_operation_kind_mismatch")
    for label in ["standalone_delete_file", "standalone_move_file", "standalone_mkdir"]:
        record = extended_by_label.get(label)
        if not isinstance(record, dict) or record.get("status") != "ok":
            failures.append(f"extended_mutation_probe_missing_or_failed:{label}")
            continue
        if record.get("repository_mutation_performed") is not True:
            failures.append(f"extended_mutation_probe_not_marked_mutating:{label}")
        if not isinstance(record.get("changed_path_count"), int) or record.get("changed_path_count") <= 0:
            failures.append(f"extended_mutation_probe_changed_path_count_missing:{label}")
        if record.get("partial_failure") is not False:
            failures.append(f"extended_mutation_probe_partial_failure:{label}")
        if record.get("allowed_in_policy_loss_trajectory") is not False:
            failures.append(f"extended_mutation_probe_policy_loss_trajectory_enabled:{label}")
        if record.get("policy_loss_candidate") is not False:
            failures.append(f"extended_mutation_probe_policy_loss_enabled:{label}")
        if record.get("official_prediction_eligible") is not False:
            failures.append(f"extended_mutation_probe_official_prediction_enabled:{label}")
        if record.get("training_export_eligible") is not False:
            failures.append(f"extended_mutation_probe_training_export_enabled:{label}")
    if mutation.get("standalone_tools_remain_extended") is not True:
        failures.append("standalone_tools_not_marked_extended")
    if mutation.get("raw_temporary_paths_recorded") is not False:
        failures.append("mutation_probe_records_raw_temporary_paths")

    safety_denials = safety.get("denials", [])
    if not isinstance(safety_denials, list):
        failures.append("safety_denial_list_missing")
        safety_denials = []
    safety_by_label = {record.get("label"): record for record in safety_denials if isinstance(record, dict)}
    expected_denials = {
        "atomic_preflight_stale_hash": "stale_file_state",
        "hidden_path_denial": "model_hidden_path_denied",
        "binary_file_denial": "binary_file_denied",
        "non_utf8_file_denial": "non_utf8_file_denied",
        "symlink_denial": "symlink_not_mutable",
        "duplicate_path_denial": "duplicate_mutation_path",
        "sensitive_marker_variant_denial": "model_hidden_path_denied",
    }
    for label, reason_code in expected_denials.items():
        record = safety_by_label.get(label)
        if not isinstance(record, dict):
            failures.append(f"safety_denial_missing:{label}")
            continue
        if record.get("status") != "denied" or record.get("reason_code") != reason_code:
            failures.append(f"safety_denial_reason_mismatch:{label}")
        if record.get("repository_mutation_performed") is not False:
            failures.append(f"safety_denial_mutated_repository:{label}")
        if record.get("changed_path_count") not in {0, None}:
            failures.append(f"safety_denial_changed_path_count_nonzero:{label}")
        if record.get("partial_failure") is not False:
            failures.append(f"safety_denial_partial_failure:{label}")
        if record.get("allowed_in_policy_loss_trajectory") is not False:
            failures.append(f"safety_denial_policy_loss_trajectory_enabled:{label}")
        if record.get("policy_loss_candidate") is not False:
            failures.append(f"safety_denial_policy_loss_enabled:{label}")
        if record.get("official_prediction_eligible") is not False:
            failures.append(f"safety_denial_official_prediction_enabled:{label}")
        if record.get("training_export_eligible") is not False:
            failures.append(f"safety_denial_training_export_enabled:{label}")
        if record.get("sample_policy_loss_candidate_effect") != (
            "denial_not_policy_loss_candidate_requires_stage16g2c_patch_projection_linkage"
        ):
            failures.append(f"safety_denial_policy_loss_effect_mismatch:{label}")
    required_reason_codes = set(safety.get("required_reason_codes", []))
    if required_reason_codes != set(expected_denials.values()):
        failures.append("safety_required_reason_codes_mismatch")
    if safety.get("atomic_preflight_preserved_first_file") is not True:
        failures.append("atomic_preflight_first_file_not_preserved")
    if safety.get("atomic_preflight_preserved_second_file") is not True:
        failures.append("atomic_preflight_second_file_not_preserved")
    if safety.get("duplicate_path_preserved_file") is not True:
        failures.append("duplicate_path_file_not_preserved")
    if safety.get("symlink_target_preserved") is not True:
        failures.append("symlink_target_not_preserved")
    if safety.get("sensitive_marker_variant_path_absent") is not True:
        failures.append("sensitive_marker_variant_path_not_absent")
    if safety.get("raw_temporary_paths_recorded") is not False:
        failures.append("safety_probe_records_raw_temporary_paths")

    checks = {
        "summary_passed": summary.get("status") == "passed",
        "default_behavior_enabled_tools": summary.get("default_behavior_enabled_tools"),
        "standalone_tools_default_visible": summary.get("standalone_tools_default_visible"),
        "unary_delete_supported_by_apply_patch": summary.get("unary_delete_supported_by_apply_patch"),
        "unary_move_supported_by_apply_patch": summary.get("unary_move_supported_by_apply_patch"),
        "atomic_preflight_passed": summary.get("atomic_preflight_passed"),
        "policy_loss_candidate_for_new_tools": summary.get("policy_loss_candidate_for_new_tools"),
        "public_path_leak_scan_passed": current_path_scan.get("public_path_leak_scan_passed"),
        "safety_denial_reason_codes": sorted(required_reason_codes),
    }
    return failures, checks


def inspect_stage16g2b_file_mutation(summary_path: str | Path, *, assert_complete: bool = False) -> str:
    summary = Path(summary_path)
    if not summary.exists():
        raise RepoHarnessError(f"Stage 16G.2B acceptance summary not found: {summary}")
    base = summary.parent
    payloads = _load_stage16g2b_dir(summary)
    failures: list[str] = []
    missing = [filename for filename in STAGE16G2B_REQUIRED_OUTPUT_FILES if filename not in payloads]
    failures.extend(f"missing_required_file:{filename}" for filename in missing)
    checks: dict[str, Any] = {}
    if not missing:
        validation_failures, checks = _stage16g2b_validation_failures(payloads, base=base)
        failures.extend(validation_failures)
    report = {
        "schema_version": "stage16g2b.cli_inspection_result.v1",
        "status": "passed" if not failures else "failed",
        "summary_path": summary.name,
        "failure_count": len(failures),
        "failures": failures,
        "validated_file_count": len(STAGE16G2B_REQUIRED_OUTPUT_FILES),
        "derived_checks": checks,
    }
    if assert_complete and failures:
        raise RepoHarnessError(_json_dumps(report))
    return _json_dumps(report)


def build_stage16g2c_acceptance_summary(
    *,
    reports: dict[str, Any],
    digests: dict[str, str],
) -> dict[str, Any]:
    failures, checks = _stage16g2c_validation_failures(reports, base=None)
    status = "passed" if not failures else "failed"
    return {
        "schema_version": "stage16g2c.acceptance_summary.v1",
        "status": status,
        "stage16g2c_complete": status == "passed",
        "stage16g3_allowed_to_start": status == "passed",
        "stage17b_real_data_freeze_allowed": False,
        "stage20_warm_start_data_generation_allowed": False,
        "stage21_formal_rl_allowed": False,
        "run_episode_projection_linkage_passed": bool(checks.get("projection_complete")),
        "structured_file_tools_projected": bool(checks.get("structured_file_tools_projected")),
        "patch_hygiene_linkage_passed": bool(checks.get("patch_hygiene_linkage_passed")),
        "tool_observation_mask_zero_passed": bool(checks.get("tool_observation_mask_zero_passed")),
        "non_verl_route_policy_loss_blocked": bool(checks.get("non_verl_route_policy_loss_blocked")),
        "public_path_leak_scan_passed": bool(checks.get("public_path_leak_scan_passed")),
        "failure_count": len(failures),
        "failure_ids": failures,
        **{field: digests[filename] for filename, field in STAGE16G2C_SUMMARY_DIGEST_FIELDS.items()},
        "source_digests": {
            relative_path: _file_sha256(Path(relative_path))
            for relative_path in STAGE16G2C_SOURCE_DIGEST_FILES
            if Path(relative_path).exists()
        },
    }


def _load_stage16g2c_dir(summary_path: Path) -> dict[str, Any]:
    base = summary_path.parent
    payloads: dict[str, Any] = {}
    for filename in STAGE16G2C_REQUIRED_OUTPUT_FILES:
        path = base / filename
        if path.exists():
            payloads[filename] = _load_json(path)
    return payloads


def _stage16g2c_validation_failures(
    payloads: dict[str, Any],
    *,
    base: Path | None,
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    probe = payloads["stage16g2c_run_episode_projection_probe_report.json"]
    linkage = payloads["stage16g2c_projection_linkage_report.json"]
    path_scan = payloads["stage16g2c_path_leak_scan_report.json"]
    summary = payloads.get("stage16g2c_acceptance_summary.json")

    for key in sorted(set(probe) - STAGE16G2C_PROBE_KEYS):
        failures.append(f"stage16g2c_probe_unexpected_field:{key}")
    for key in sorted(set(linkage) - STAGE16G2C_LINKAGE_KEYS):
        failures.append(f"stage16g2c_linkage_unexpected_field:{key}")
    for key in sorted(set(path_scan) - STAGE16G2C_PATH_SCAN_KEYS):
        failures.append(f"stage16g2c_path_scan_unexpected_field:{key}")

    if probe.get("schema_version") != "stage16g2c.run_episode_projection_probe_report.v1":
        failures.append("probe_schema_version_mismatch")
    if linkage.get("schema_version") != "stage16g2c.projection_linkage_report.v1":
        failures.append("linkage_schema_version_mismatch")
    if path_scan.get("schema_version") != "stage16g2c.path_leak_scan_report.v1":
        failures.append("path_scan_schema_version_mismatch")

    if probe.get("status") != "passed":
        failures.append("probe_status_not_passed")
    if probe.get("run_episode_invocation") != "RepoHarnessRuntime.run_episode(real_episode)":
        failures.append("probe_not_created_by_run_episode")
    if probe.get("projection_writer") != "write_run_episode_compat_projection":
        failures.append("projection_writer_mismatch")
    if probe.get("projection_created_from_run_episode") is not True:
        failures.append("projection_created_from_run_episode_not_true")
    if probe.get("projection_complete") is not True:
        failures.append("projection_not_complete")
    if probe.get("result_status") != "succeeded":
        failures.append("result_status_not_succeeded")
    if probe.get("final_verifier_accepted") is not True:
        failures.append("final_verifier_not_accepted")
    if probe.get("forbidden_model_visible_marker_scan_passed") is not True:
        failures.append("model_visible_forbidden_marker_scan_failed")

    observed_tools = set(probe.get("tool_names_observed", []))
    if observed_tools != {"write_file", "apply_patch"}:
        failures.append("structured_tool_names_observed_mismatch")
    operation_kinds = set(probe.get("operation_kinds_observed", []))
    if operation_kinds != {"replace_text", "write_file", "delete_file", "move_file", "mkdir"}:
        failures.append("operation_kinds_observed_mismatch")

    patch_facts = probe.get("final_patch_changed_file_facts", {})
    if isinstance(patch_facts, dict):
        for key in sorted(set(patch_facts) - STAGE16G2C_PATCH_FACT_KEYS):
            failures.append(f"stage16g2c_patch_facts_unexpected_field:{key}")
        patch_entries = patch_facts.get("entries", [])
        if isinstance(patch_entries, list):
            for index, entry in enumerate(patch_entries):
                if not isinstance(entry, dict):
                    failures.append(f"stage16g2c_patch_entry_not_object:{index}")
                    continue
                for key in sorted(set(entry) - STAGE16G2C_PATCH_ENTRY_KEYS):
                    failures.append(f"stage16g2c_patch_entry_unexpected_field:{index}:{key}")
    if patch_facts.get("added_count", 0) < 2:
        failures.append("final_patch_missing_added_file_fact")
    if patch_facts.get("modified_count", 0) < 1:
        failures.append("final_patch_missing_modified_file_fact")
    if patch_facts.get("deleted_count", 0) < 1:
        failures.append("final_patch_missing_deleted_file_fact")
    if patch_facts.get("renamed_count", 0) < 1:
        failures.append("final_patch_missing_renamed_file_fact")
    expected_patch_paths = {"docs/generated/notes.md", "legacy.py", "pkg/calc.py", "pkg/helpers.py", "old_name.py", "pkg/renamed.py"}
    observed_patch_paths = set(patch_facts.get("changed_paths", []))
    if not expected_patch_paths.issubset(observed_patch_paths):
        failures.append("final_patch_changed_paths_incomplete")

    training_projection = probe.get("training_projection", {})
    if isinstance(training_projection, dict):
        for key in sorted(set(training_projection) - STAGE16G2C_TRAINING_PROJECTION_KEYS):
            failures.append(f"stage16g2c_training_projection_unexpected_field:{key}")
    if training_projection.get("tool_observation_span_count", 0) < 2:
        failures.append("tool_observation_span_count_too_low")
    if training_projection.get("tool_observation_spans_response_mask_zero") is not True:
        failures.append("tool_observation_spans_not_mask_zero")
    if training_projection.get("tool_output_response_mask_zero_count", 0) <= 0:
        failures.append("tool_output_response_mask_zero_count_missing")
    if training_projection.get("assistant_response_mask_one_count", 0) <= 0:
        failures.append("assistant_response_mask_one_count_missing")
    if training_projection.get("generation_record_count", 0) < 2:
        failures.append("generation_record_count_too_low")

    route = probe.get("provider_route_qualification", {})
    if isinstance(route, dict):
        for key in sorted(set(route) - STAGE16G2C_PROVIDER_ROUTE_KEYS):
            failures.append(f"stage16g2c_provider_route_unexpected_field:{key}")
    if route.get("provider_route") != "mock" or route.get("llm_gateway_route") != "mock":
        failures.append("provider_route_qualification_route_mismatch")
    if route.get("formal_online_rl_eligible") is not False:
        failures.append("non_verl_route_formal_online_rl_enabled")
    if route.get("policy_loss_candidate") is not False:
        failures.append("non_verl_route_policy_loss_enabled")

    if linkage.get("status") != "passed":
        failures.append("linkage_status_not_passed")
    if linkage.get("manifest_final_patch_sha256_matches_projection") is not True:
        failures.append("manifest_final_patch_sha256_mismatch")
    if linkage.get("manifest_final_diff_sha256_matches_projection") is not True:
        failures.append("manifest_final_diff_sha256_mismatch")
    if linkage.get("hygiene_cleaned_patch_sha256_matches_manifest") is not True:
        failures.append("hygiene_cleaned_patch_sha256_mismatch")
    if linkage.get("hygiene_cleaned_diff_sha256_matches_manifest") is not True:
        failures.append("hygiene_cleaned_diff_sha256_mismatch")
    if linkage.get("source_and_compat_final_patch_match") is not True:
        failures.append("source_and_compat_final_patch_mismatch")
    if linkage.get("source_and_compat_final_diff_match") is not True:
        failures.append("source_and_compat_final_diff_mismatch")
    if linkage.get("public_hygiene_report_contains_raw_fields") is not False:
        failures.append("public_hygiene_report_contains_raw_fields")
    if linkage.get("compat_projection_public_safe") is not True:
        failures.append("compat_projection_not_public_safe")

    current_path_scan = scan_stage16g2c_public_files(base) if base is not None else path_scan
    if current_path_scan != path_scan:
        failures.append("stage16g2c_path_leak_scan_report_stale_or_mismatched")
    if not current_path_scan.get("public_path_leak_scan_passed"):
        failures.append("stage16g2c_public_path_leak_scan_failed")

    if summary is not None:
        if summary.get("schema_version") != "stage16g2c.acceptance_summary.v1":
            failures.append("summary_schema_version_mismatch")
        if summary.get("status") != "passed" or summary.get("stage16g2c_complete") is not True:
            failures.append("stage16g2c_summary_not_passed")
        if summary.get("stage16g3_allowed_to_start") is not True:
            failures.append("stage16g3_not_allowed_after_16g2c")
        if summary.get("stage17b_real_data_freeze_allowed") is not False:
            failures.append("stage17b_allowed_too_early")
        if summary.get("stage20_warm_start_data_generation_allowed") is not False:
            failures.append("stage20_allowed_too_early")
        if summary.get("stage21_formal_rl_allowed") is not False:
            failures.append("stage21_allowed_too_early")

    if summary is not None and base is not None:
        for filename, field_name in STAGE16G2C_SUMMARY_DIGEST_FIELDS.items():
            if summary.get(field_name) != _file_sha256(base / filename):
                failures.append(f"stage16g2c_sha256_mismatch:{filename}")
        source_digests = summary.get("source_digests")
        if not isinstance(source_digests, dict):
            failures.append("source_digests_missing")
        else:
            for relative_path in STAGE16G2C_SOURCE_DIGEST_FILES:
                source_path = Path(relative_path)
                if not source_path.exists():
                    failures.append(f"source_digest_file_missing:{relative_path}")
                    continue
                if source_digests.get(relative_path) != _file_sha256(source_path):
                    failures.append(f"source_digest_mismatch:{relative_path}")
            for relative_path in sorted(set(source_digests) - set(STAGE16G2C_SOURCE_DIGEST_FILES)):
                failures.append(f"source_digest_unexpected_file:{relative_path}")

    checks = {
        "projection_complete": probe.get("projection_complete") is True,
        "structured_file_tools_projected": observed_tools == {"write_file", "apply_patch"},
        "patch_hygiene_linkage_passed": (
            linkage.get("hygiene_cleaned_patch_sha256_matches_manifest") is True
            and linkage.get("public_hygiene_report_contains_raw_fields") is False
        ),
        "tool_observation_mask_zero_passed": (
            training_projection.get("tool_observation_spans_response_mask_zero") is True
            and training_projection.get("tool_output_response_mask_zero_count", 0) > 0
        ),
        "non_verl_route_policy_loss_blocked": route.get("policy_loss_candidate") is False,
        "public_path_leak_scan_passed": current_path_scan.get("public_path_leak_scan_passed") is True,
    }
    return failures, checks


def inspect_stage16g2c_projection_linkage(summary_path: str | Path, *, assert_complete: bool = False) -> str:
    summary = Path(summary_path)
    if not summary.exists():
        raise RepoHarnessError(f"Stage 16G.2C acceptance summary not found: {summary}")
    base = summary.parent
    payloads = _load_stage16g2c_dir(summary)
    failures: list[str] = []
    missing = [filename for filename in STAGE16G2C_REQUIRED_OUTPUT_FILES if filename not in payloads]
    failures.extend(f"missing_required_file:{filename}" for filename in missing)
    checks: dict[str, Any] = {}
    if not missing:
        validation_failures, checks = _stage16g2c_validation_failures(payloads, base=base)
        failures.extend(validation_failures)
        actual_digests = {
            filename: _file_sha256(base / filename)
            for filename in STAGE16G2C_REQUIRED_OUTPUT_FILES
        }
        expected_summary = build_stage16g2c_acceptance_summary(
            reports={
                key: value
                for key, value in payloads.items()
                if key != "stage16g2c_acceptance_summary.json"
            },
            digests=actual_digests,
        )
        summary_payload = payloads["stage16g2c_acceptance_summary.json"]
        for field_name, expected_value in expected_summary.items():
            if summary_payload.get(field_name) != expected_value:
                failures.append(f"acceptance_summary_field_mismatch:{field_name}")
        for field_name in sorted(set(summary_payload) - set(expected_summary)):
            failures.append(f"acceptance_summary_unexpected_field:{field_name}")

    report = {
        "schema_version": "stage16g2c.cli_inspection_result.v1",
        "status": "passed" if not failures else "failed",
        "summary_path": summary.name,
        "failure_count": len(failures),
        "failures": failures,
        "validated_file_count": len(STAGE16G2C_REQUIRED_OUTPUT_FILES),
        "derived_checks": checks,
    }
    if assert_complete and failures:
        raise RepoHarnessError(_json_dumps(report))
    return _json_dumps(report)
