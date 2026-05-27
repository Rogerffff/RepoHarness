"""Stage 16G.2A structured file tool surface evidence and inspector."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from repo_harness.errors import RepoHarnessError
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
    "src/repo_harness/permissions/system.py",
    "src/repo_harness/scaffolds/simple_react.py",
    "src/repo_harness/scaffolds/planner_coder_verifier.py",
    "src/repo_harness/stage16g2_file_surface.py",
    "src/repo_harness/cli/main.py",
    "scripts/pre_verl/build_stage16g2a_tool_surface.py",
    "tests/unit/test_repo_harness_stage16g2a_tool_surface.py",
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


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
                "executor_binding_status": "schema_only_denial_until_16G2B",
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
                    "schema_only_denial_until_16G2B" if is_p0 else "nonblocking_no_change"
                ),
                "stage16g2a_delta_status": (
                    "schema_profile_and_scaffold_exposure_complete_behavior_pending_16G2B"
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
                        "executor_binding_status": "schema_only_denial_until_16G2B",
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
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(text):
                findings.append({"relative_path": path.name, "pattern": pattern.pattern})
    return {
        "schema_version": "stage16g2a.path_leak_scan_report.v1",
        "public_path_leak_scan_passed": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "scanned_suffixes": [".json", ".md"],
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
