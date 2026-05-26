"""Stage 16G.1 tool profile registry evidence and inspector."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from repo_harness.config import RuntimeConfig
from repo_harness.errors import RepoHarnessError
from repo_harness.evaluation.episode_runner import run_episode_task
from repo_harness.scaffolds import build_scaffold, default_scaffold_registry
from repo_harness.tools import DEFAULT_TOOL_ORDER, build_tool, default_tool_registry


SCHEMA_VERSION_PREFIX = "stage16g1"
DEFAULT_STAGE16G0_DIR = Path("docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0")
DEFAULT_STAGE16G1_DIR = Path("docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1")

REQUIRED_OUTPUT_FILES = [
    "stage16g1_source_inventory.json",
    "stage16g1_tool_registry_contract.json",
    "stage16g1_profile_taxonomy.json",
    "stage16g1_training_eligibility_gate_spec.json",
    "stage16g1_profile_registry_inspection_report.json",
    "stage16g1_run_episode_profile_smoke_report.json",
    "stage16g1_public_evidence_policy.json",
    "stage16g1_path_leak_scan_report.json",
    "stage16g1_human_readable_tool_profile_summary.md",
    "stage16g1_acceptance_summary.json",
]

SUMMARY_DIGEST_FIELDS = {
    "stage16g1_source_inventory.json": "source_inventory_sha256",
    "stage16g1_tool_registry_contract.json": "tool_registry_contract_sha256",
    "stage16g1_profile_taxonomy.json": "profile_taxonomy_sha256",
    "stage16g1_training_eligibility_gate_spec.json": "training_eligibility_gate_spec_sha256",
    "stage16g1_profile_registry_inspection_report.json": "profile_registry_inspection_report_sha256",
    "stage16g1_run_episode_profile_smoke_report.json": "run_episode_profile_smoke_report_sha256",
    "stage16g1_public_evidence_policy.json": "public_evidence_policy_sha256",
    "stage16g1_path_leak_scan_report.json": "path_leak_scan_report_sha256",
    "stage16g1_human_readable_tool_profile_summary.md": "human_readable_summary_sha256",
}

INPUT_FILES = [
    "stage16g0_claude_code_baseline_contract.json",
    "stage16g0_mini_swe_agent_baseline_contract.json",
    "stage16g0_per_capability_baseline_comparison.json",
    "stage16g0_stage16g_implementation_requirements.json",
    "stage16g0_followup_acceptance_summary.json",
]

SOURCE_FILES = [
    "src/repo_harness/config/schemas.py",
    "src/repo_harness/tools/minimal.py",
    "src/repo_harness/scaffolds",
    "src/repo_harness/scaffolds/policies.py",
    "src/repo_harness/tasks/command_policy.py",
    "src/repo_harness/tasks/public_environment.py",
    "src/repo_harness/workspace/diagnostic_session.py",
    "src/repo_harness/workspace/patch_hygiene.py",
    "src/repo_harness/evaluation/episode_runner.py",
    "src/repo_harness/evaluation/episode_projection.py",
    "src/repo_harness/evaluation/entrypoint_policy.py",
    "src/repo_harness/execution/spec.py",
    "src/repo_harness/rl/runtime.py",
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
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]

PROFILE_IDS = ["safe_structured_only", "swe_public_core", "swe_public_extended", "redteam_restricted"]
BASE_SAFETY_BOUNDARIES = [
    "hidden_verifier_forbidden",
    "gold_patch_forbidden",
    "test_patch_forbidden",
    "runtime-private-forbidden",
    "raw_artifact_private_by_default",
]
EXTENDED_PROFILE_REQUIRED_BOUNDARIES = [
    "runtime-private-forbidden",
    "raw_artifact_private_by_default",
    "session_reset_required",
    "artifact_hygiene_required",
    "path_redaction_required",
    "public_safe_projection_required",
]

TOOL_ID_BY_CAPABILITY: dict[str, list[str]] = {
    "structured_file_read": ["read_file"],
    "non_text_file_read": ["read_file"],
    "large_file_paging_or_artifact_replay": ["read_tool_result_artifact"],
    "glob_file_discovery": ["glob_files"],
    "grep_content_search": ["grep"],
    "symbol_search_or_lsp_diagnostics": ["symbol_search"],
    "structured_edit_existing_file": ["edit_file"],
    "structured_write_or_create_file": ["create_file", "write_file"],
    "apply_patch_or_multi_file_edit": ["apply_patch"],
    "delete_move_mkdir_file_operations": ["delete_file", "move_file", "mkdir"],
    "bash_or_public_command_execution": ["execute_bash", "run_public_command"],
    "persistent_diagnostic_session": ["diagnostic_shell"],
    "parameterized_public_test_command": ["run_tests", "run_project_test"],
    "scratch_python_or_reproduction_script": ["scratch_python"],
    "project_command_routing": ["run_project_test", "run_public_command"],
    "dependency_setup_and_environment_policy": ["dependency_setup_policy"],
    "git_diff_status_and_patch_capture": ["git_diff"],
    "final_answer_verifier_reward_linkage": ["final_answer_linkage"],
    "permission_approval_denial_recovery": ["permission_policy_gate"],
    "sandbox_workspace_and_runtime_private_boundary": ["sandbox_boundary_gate"],
    "tool_result_truncation_raw_artifact_privacy": ["read_tool_result_artifact"],
    "task_management_todo": ["update_working_state"],
    "subagent_background_task": ["agent_task_schema_reserved"],
    "external_tools_mcp_plugin_skill": ["external_tool_schema_reserved"],
    "hooks_tool_lifecycle_audit": ["tool_lifecycle_audit"],
    "training_eligibility_and_export_projection": ["training_eligibility_gate"],
    "reward_hacking_monitoring_and_quarantine": ["reward_hacking_monitor"],
}

EXISTING_TOOL_FALLBACKS = {"write_file": "create_file", "run_project_test": "run_tests"}

CORE_FORBIDDEN_CAPABILITIES = {"persistent_diagnostic_session"}
POST_16G_OPTIONAL_STAGES = {"post_16G_optional"}


@dataclass(frozen=True)
class Stage16G1Inputs:
    stage16g0_dir: Path = DEFAULT_STAGE16G0_DIR

    @property
    def comparison_path(self) -> Path:
        return self.stage16g0_dir / "stage16g0_per_capability_baseline_comparison.json"

    @property
    def followup_summary_path(self) -> Path:
        return self.stage16g0_dir / "stage16g0_followup_acceptance_summary.json"


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: Any) -> str:
    return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _try_build_tool(tool_id: str) -> bool:
    try:
        build_tool(tool_id)
    except Exception:
        return False
    return True


def _tool_is_resolvable_or_fallback(tool_id: str) -> bool:
    return _try_build_tool(tool_id) or _try_build_tool(EXISTING_TOOL_FALLBACKS.get(tool_id, ""))


def _source_entry(path: Path) -> dict[str, Any]:
    if path.is_dir():
        file_hashes = [
            {"relative_path": file.as_posix(), "sha256": _file_sha256(file)}
            for file in sorted(path.rglob("*.py"))
            if file.is_file()
        ]
        digest = hashlib.sha256(_json_dumps(file_hashes).encode("utf-8")).hexdigest()
        return {
            "relative_path": path.as_posix(),
            "exists": True,
            "source_kind": "directory_py_digest",
            "sha256": digest,
            "file_count": len(file_hashes),
        }
    if path.exists():
        return {
            "relative_path": path.as_posix(),
            "exists": True,
            "source_kind": "file",
            "sha256": _file_sha256(path),
        }
    return {"relative_path": path.as_posix(), "exists": False, "source_kind": "missing", "sha256": None}


def load_stage16g0_comparison(stage16g0_dir: Path = DEFAULT_STAGE16G0_DIR) -> list[dict[str, Any]]:
    payload = _load_json(stage16g0_dir / "stage16g0_per_capability_baseline_comparison.json")
    return list(payload["comparison_records"])


def build_current_code_facts() -> dict[str, Any]:
    runtime_config = RuntimeConfig()
    scaffold_registry = default_scaffold_registry()
    scaffold_ids = scaffold_registry.ids()
    simple_react = build_scaffold("simple_react")
    simple_react_allowed = list(simple_react.allowed_tools)
    default_registry_names = default_tool_registry().names()
    execute_bash = build_tool("execute_bash")
    diagnostic_shell = build_tool("diagnostic_shell")
    execute_bash_text = f"{execute_bash.model_visible_description} {execute_bash.model_visible_prompt}".lower()

    return {
        "schema_version": "stage16g1.current_code_facts.v1",
        "runtime_default_scaffold_id": runtime_config.scaffold_id,
        "runtime_default_scaffold_is_simple_react": runtime_config.scaffold_id == "simple_react",
        "registered_scaffold_ids": scaffold_ids,
        "patch_focused_react_mini_shell_present": "patch_focused_react_mini_shell" in scaffold_ids,
        "simple_react_allowed_tools": simple_react_allowed,
        "simple_react_exposes_create_file": "create_file" in simple_react_allowed,
        "default_tool_order": list(DEFAULT_TOOL_ORDER),
        "default_tool_registry_names": default_registry_names,
        "execute_bash_buildable": _try_build_tool("execute_bash"),
        "execute_bash_in_default_tool_order": "execute_bash" in DEFAULT_TOOL_ORDER,
        "execute_bash_description_mentions_allowlist": "allowlist" in execute_bash_text,
        "execute_bash_description_mentions_pytest": "pytest" in execute_bash_text,
        "execute_bash_narrow_but_nonempty": (
            _try_build_tool("execute_bash")
            and "execute_bash" not in DEFAULT_TOOL_ORDER
            and "pytest" in execute_bash_text
            and "allowlist" in execute_bash_text
        ),
        "diagnostic_shell_buildable": _try_build_tool("diagnostic_shell"),
        "diagnostic_shell_in_simple_react": "diagnostic_shell" in simple_react_allowed,
        "diagnostic_shell_not_core_default": "diagnostic_shell" not in simple_react_allowed,
        "diagnostic_shell_version": diagnostic_shell.tool_version,
    }


def build_source_inventory(stage16g0_dir: Path = DEFAULT_STAGE16G0_DIR) -> dict[str, Any]:
    input_sources = []
    for filename in INPUT_FILES:
        path = stage16g0_dir / filename
        input_sources.append(
            {
                "source_label": filename.removesuffix(".json"),
                "relative_path": path.as_posix(),
                "exists": path.exists(),
                "sha256": _file_sha256(path) if path.exists() else None,
            }
        )
    return {
        "schema_version": "stage16g1.source_inventory.v1",
        "source_inputs": input_sources,
        "source_code_facts": [_source_entry(Path(path)) for path in SOURCE_FILES],
        "public_path_policy": "repo_relative_paths_and_sha256_only",
    }


def _owner_priority(record: dict[str, Any]) -> str:
    if record["blocking_for_main_swe_rl"]:
        return "P0"
    if record["required_stage"] == "16G.5":
        return "P1"
    return "P2"


def _repo_harness_status(record: dict[str, Any]) -> str:
    gap_type = record["gap_type"]
    if gap_type == "present_and_sufficient":
        return "present"
    if gap_type == "missing":
        return "proposed_tool_required"
    if gap_type == "present_diagnostic_only":
        return "diagnostic_only_current"
    if gap_type == "deferred_schema_only":
        return "schema_reserved"
    return "partial"


def _status_fields(record: dict[str, Any], tool_ids: list[str]) -> dict[str, str]:
    required_stage = record["required_stage"]
    gap_type = record["gap_type"]
    buildable_count = sum(1 for tool_id in tool_ids if _try_build_tool(tool_id))
    any_buildable = buildable_count > 0
    all_buildable = buildable_count == len(tool_ids)
    if required_stage == "post_16G_optional":
        return {
            "model_visible_schema_status": "schema_reserved",
            "model_visible_prompt_status": "schema_reserved",
            "scaffold_exposure_status": "schema_reserved",
            "public_environment_hint_status": "schema_reserved",
            "executor_binding_status": "not_implemented",
            "run_episode_visibility_status": "schema_reserved",
        }
    if gap_type == "missing" or not any_buildable:
        return {
            "model_visible_schema_status": "planned",
            "model_visible_prompt_status": "planned",
            "scaffold_exposure_status": "planned",
            "public_environment_hint_status": "planned",
            "executor_binding_status": "not_implemented",
            "run_episode_visibility_status": "planned",
        }
    if all_buildable and gap_type == "present_and_sufficient":
        return {
            "model_visible_schema_status": "implemented",
            "model_visible_prompt_status": "implemented",
            "scaffold_exposure_status": "implemented",
            "public_environment_hint_status": "implemented",
            "executor_binding_status": "implemented",
            "run_episode_visibility_status": "implemented",
        }
    return {
        "model_visible_schema_status": "partial",
        "model_visible_prompt_status": "partial",
        "scaffold_exposure_status": "partial",
        "public_environment_hint_status": "partial_or_planned",
        "executor_binding_status": "partial" if any_buildable else "not_implemented",
        "run_episode_visibility_status": "partial_or_planned",
    }


def _profile_status(capability_id: str, required_stage: str, gap_type: str) -> dict[str, str]:
    if capability_id == "persistent_diagnostic_session":
        return {
            "safe_structured_only": "forbidden",
            "swe_public_core": "forbidden",
            "swe_public_extended": "planned",
            "redteam_restricted": "allowed_for_safety_probe",
        }
    if required_stage == "post_16G_optional":
        return {
            "safe_structured_only": "schema_reserved",
            "swe_public_core": "schema_reserved",
            "swe_public_extended": "schema_reserved",
            "redteam_restricted": "allowed_for_schema_probe",
        }
    if capability_id in {
        "bash_or_public_command_execution",
        "parameterized_public_test_command",
        "scratch_python_or_reproduction_script",
        "project_command_routing",
    }:
        return {
            "safe_structured_only": "forbidden",
            "swe_public_core": "planned",
            "swe_public_extended": "planned",
            "redteam_restricted": "allowed_for_negative_or_safety_probe",
        }
    status = "implemented" if gap_type == "present_and_sufficient" else "planned"
    return {
        "safe_structured_only": status if capability_id not in {"dependency_setup_and_environment_policy"} else "forbidden",
        "swe_public_core": status,
        "swe_public_extended": status,
        "redteam_restricted": "allowed_for_negative_or_safety_probe",
    }


def _training_projection_policy(record: dict[str, Any], status_fields: dict[str, str]) -> dict[str, Any]:
    required_stage = record["required_stage"]
    capability_id = record["capability_id"]
    executor_status = status_fields["executor_binding_status"]
    planned_or_missing = (
        executor_status == "not_implemented"
        or status_fields["model_visible_schema_status"] in {"planned", "schema_reserved"}
        or status_fields["run_episode_visibility_status"] in {"planned", "schema_reserved"}
    )
    diagnostic_only = capability_id == "persistent_diagnostic_session" or required_stage == "post_16G_optional"
    allowed_in_policy_loss_trajectory = (
        not planned_or_missing
        and not diagnostic_only
        and record["gap_type"] == "present_and_sufficient"
        and required_stage in {"not_required", "16G.5"}
    )
    if allowed_in_policy_loss_trajectory:
        effect = "preserves_sample_candidate_if_all_trajectory_gates_pass"
    elif diagnostic_only:
        effect = "makes_sample_diagnostic_only_or_schema_reserved"
    else:
        effect = "makes_sample_ineligible_until_owner_stage_complete"
    return {
        "tool_event_policy_loss_unit": "not_an_individual_policy_loss_sample",
        "allowed_in_policy_loss_trajectory": allowed_in_policy_loss_trajectory,
        "sample_policy_loss_candidate_effect": effect,
        "sft_eligible": allowed_in_policy_loss_trajectory,
        "preference_eligible": allowed_in_policy_loss_trajectory or record["gap_type"] in {"partial", "missing"},
        "negative_sample_eligible": True,
        "quarantine_eligible": True,
        "diagnostic_only": diagnostic_only,
        "eligibility_reason": (
            "当前能力可出现在合格 trajectory 中，但单个工具事件本身不是 policy loss sample。"
            if allowed_in_policy_loss_trajectory
            else "Stage 16G owner stage 完成并通过 gate 前，不能让样本进入主 policy loss。"
        ),
    }


def _safety_boundaries(capability_id: str) -> list[str]:
    boundaries = list(BASE_SAFETY_BOUNDARIES)
    if capability_id in {
        "bash_or_public_command_execution",
        "parameterized_public_test_command",
        "scratch_python_or_reproduction_script",
        "project_command_routing",
        "persistent_diagnostic_session",
        "dependency_setup_and_environment_policy",
    }:
        boundaries.extend(["host_absolute_path_forbidden", "network_denied_by_default", "shared_dependency_write_forbidden"])
    return boundaries


def _persistent_session_boundary_policy(capability_id: str) -> dict[str, Any] | None:
    if capability_id != "persistent_diagnostic_session":
        return None
    return {
        "session_reset_required": True,
        "artifact_hygiene_required": True,
        "path_redaction_required": True,
        "public_safe_projection_required": True,
        "main_training_core_default_allowed": False,
    }


def build_tool_registry_contract(stage16g0_dir: Path = DEFAULT_STAGE16G0_DIR) -> dict[str, Any]:
    records = []
    for record in load_stage16g0_comparison(stage16g0_dir):
        capability_id = record["capability_id"]
        tool_ids = TOOL_ID_BY_CAPABILITY.get(capability_id, [capability_id])
        status_fields = _status_fields(record, tool_ids)
        training_policy = _training_projection_policy(record, status_fields)
        records.append(
            {
                "capability_id": capability_id,
                "baseline_gap_type": record["gap_type"],
                "blocking_for_main_swe_rl": bool(record["blocking_for_main_swe_rl"]),
                "owner_stage": record["required_stage"],
                "required_stage_from_stage16g0": record["required_stage"],
                "priority": _owner_priority(record),
                "repo_harness_status": _repo_harness_status(record),
                "tool_ids": tool_ids,
                "profiles": _profile_status(capability_id, record["required_stage"], record["gap_type"]),
                **status_fields,
                "allowed_artifact_visibility": {
                    "model_visible": "summary_or_public_result",
                    "raw_artifact": "private_by_default",
                    "export_projection": "public_safe_projection_only",
                },
                "denial_feedback_policy": {
                    "requires_reason_code": True,
                    "requires_retryable": True,
                    "requires_safe_alternative_tool": True,
                    "requires_safe_rewrite_example": True,
                },
                "training_projection_policy": training_policy,
                "safety_boundaries": _safety_boundaries(capability_id),
                "persistent_session_boundary_policy": _persistent_session_boundary_policy(capability_id),
                "source_capability_refs": ["stage16g0_per_capability_baseline_comparison"],
                "confidence": record.get("confidence", "medium"),
            }
        )
    return {
        "schema_version": "stage16g1.tool_registry_contract.v1",
        "registry_label": "stage16g1_baseline_derived_tool_registry",
        "profile_ids": PROFILE_IDS,
        "records": records,
        "record_count": len(records),
    }


def _profile_required_safety_boundaries(profile_id: str) -> list[str]:
    boundaries = list(BASE_SAFETY_BOUNDARIES)
    if profile_id == "swe_public_extended":
        for boundary in EXTENDED_PROFILE_REQUIRED_BOUNDARIES:
            if boundary not in boundaries:
                boundaries.append(boundary)
    return boundaries


def build_profile_taxonomy(registry: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = registry or build_tool_registry_contract()
    records = list(registry["records"])
    profiles = []
    for profile_id in PROFILE_IDS:
        allowed = [
            record["capability_id"]
            for record in records
            if record["profiles"][profile_id] in {"implemented", "planned", "partial", "partial_or_planned"}
        ]
        planned = [
            record["capability_id"]
            for record in records
            if record["profiles"][profile_id] in {"planned", "partial", "partial_or_planned"}
        ]
        forbidden = [record["capability_id"] for record in records if record["profiles"][profile_id] == "forbidden"]
        profiles.append(
            {
                "profile_id": profile_id,
                "intended_use": {
                    "safe_structured_only": "低风险结构化读写搜索和 patch 审计 profile。",
                    "swe_public_core": "主 SWE 强化学习默认工具面。",
                    "swe_public_extended": "包含 persistent diagnostic session 的扩展诊断 profile。",
                    "redteam_restricted": "安全验证、拒绝恢复、负样本和泄漏测试 profile。",
                }[profile_id],
                "allowed_capability_ids": allowed,
                "planned_capability_ids": planned,
                "forbidden_capability_ids": forbidden,
                "must_not_include": ["persistent_diagnostic_session"] if profile_id == "swe_public_core" else [],
                "required_safety_boundaries": _profile_required_safety_boundaries(profile_id),
                "training_projection_defaults": {
                    "tool_event_policy_loss_unit": "not_an_individual_policy_loss_sample",
                    "raw_artifact_policy": "private_by_default",
                },
                "run_episode_required": profile_id != "redteam_restricted",
                "legacy_run_task_primary_allowed": False,
                "primary_training_default": profile_id == "swe_public_core",
            }
        )
    return {
        "schema_version": "stage16g1.profile_taxonomy.v1",
        "profiles": profiles,
        "profile_count": len(profiles),
    }


def build_training_eligibility_gate_spec() -> dict[str, Any]:
    return {
        "schema_version": "stage16g1.training_eligibility_gate_spec.v1",
        "tool_event_eligibility": {
            "unit": "tool_event",
            "policy": "工具事件可以作为 trajectory 中的 public-safe 事实、负样本、偏好信号或 diagnostic fact；单个工具事件不是 policy loss sample。",
        },
        "trajectory_eligibility": {
            "unit": "trajectory_or_sample",
            "policy": "只有 profile、provider provenance、tool visibility、artifact hygiene 和 verifier/export gate 全部通过的样本，才可成为 policy loss candidate。",
        },
        "profile_eligibility": {
            "swe_public_core": "主 SWE 强化学习候选 profile。",
            "swe_public_extended": "默认不进入 core policy loss；需要额外 gate。",
            "safe_structured_only": "可作为低风险 structured baseline。",
            "redteam_restricted": "不能作为主训练默认 profile。",
        },
        "provider_provenance_policy": {
            "external_provider_without_verl_token_logprob_provenance": "policy_loss_ineligible",
            "replay_mock_fake": "schema_or_smoke_only_unless_training_provenance_present",
        },
        "denial_and_failure_projection_policy": {
            "permission_denial": "negative_sample_or_preference_or_diagnostic_fact",
            "bad_command": "negative_sample_or_diagnostic_fact",
            "patch_failure": "negative_sample_or_preference_candidate",
            "unknown_path": "negative_sample_or_diagnostic_fact",
        },
        "quarantine_policy": {
            "reward_hacking_suspected": "quarantine",
            "fake_verification": "quarantine",
            "overbroad_patch": "quarantine_or_review",
        },
        "hard_fail_boundary_policy": {
            "hidden_verifier": "deterministic_hard_fail",
            "gold_patch": "deterministic_hard_fail",
            "test_patch": "deterministic_hard_fail",
            "runtime-private": "deterministic_hard_fail",
            "host_absolute_path": "deterministic_hard_fail",
            "git_history_exploit": "deterministic_hard_fail",
            "shared_dependency_pollution": "deterministic_hard_fail",
        },
        "export_projection_policy": {
            "raw_artifact": "private_by_default",
            "public_export": "public_safe_projection_only",
            "sha256_binding_required": True,
        },
    }


def build_run_episode_profile_smoke_report(registry: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = registry or build_tool_registry_contract()
    registry_version = _payload_sha256(registry)
    fixture_task_path = Path("tests/fixtures/tasks/task_stage16f3_passing.yaml")
    fixture_config_path = Path("tests/fixtures/run_configs/stage16f3_run_episode_task_mock.yaml")
    try:
        with TemporaryDirectory(prefix="stage16g1-smoke-") as tmpdir:
            run_dir = run_episode_task(
                fixture_task_path,
                config_path=fixture_config_path,
                output_dir=Path(tmpdir) / "runs",
                run_id="stage16g1_smoke",
                gateway_route="mock",
                assert_projection_complete=True,
            )
            projection_dir = run_dir / "compat_projection"
            summary = _load_json(run_dir / "run_episode_task_summary.json")
            manifest = _load_json(projection_dir / "compat_projection_manifest.json")
            validation = _load_json(projection_dir / "projection_validation_report.json")
            route_report = _load_json(projection_dir / "provider_route_qualification.json")
            training_view = _load_json(projection_dir / "training_view_projection.json")
            spec_report = _load_json(projection_dir / "episode_execution_spec_report.json")
            run_config_projection = _load_json(projection_dir / "run_config_projection.json")
    except Exception as exc:
        return {
            "schema_version": "stage16g1.run_episode_profile_smoke_report.v1",
            "status": "blocked",
            "smoke_route": "run_episode_task_real_episode_mock_projection",
            "not_json_only": False,
            "blocked": True,
            "blocked_reason": type(exc).__name__,
            "stage16g1_registry_contract_sha256": registry_version,
        }

    projection_contains_registry_version = bool(
        manifest.get("tool_registry_digest")
        and manifest.get("tool_schema_snapshot_digest")
        and spec_report.get("tool_registry_digest") == manifest.get("tool_registry_digest")
        and spec_report.get("tool_schema_snapshot_digest") == manifest.get("tool_schema_snapshot_digest")
    )
    return {
        "schema_version": "stage16g1.run_episode_profile_smoke_report.v1",
        "status": "passed",
        "smoke_route": "run_episode_task_real_episode_mock_projection",
        "not_json_only": True,
        "entrypoint_contract": "run-episode-task builds EpisodeExecutionSpec and calls RepoHarnessRuntime.run_episode(real_episode)",
        "exercised_code_paths": [
            "repo_harness.evaluation.episode_runner.run_episode_task",
            "repo_harness.execution.builder.EpisodeExecutionSpecBuilder.build_spec_from_loaded_task",
            "repo_harness.rl.runtime.RepoHarnessRuntime.run_episode",
            "repo_harness.evaluation.episode_projection.write_run_episode_compat_projection",
        ],
        "fixture_refs": [
            {
                "repo_relative_path": fixture_task_path.as_posix(),
                "sha256": _file_sha256(fixture_task_path),
            },
            {
                "repo_relative_path": fixture_config_path.as_posix(),
                "sha256": _file_sha256(fixture_config_path),
            },
        ],
        "actual_run_episode_task_invoked": True,
        "actual_run_id_label": "stage16g1_smoke",
        "run_summary_facts": {
            "schema_version": summary.get("schema_version"),
            "task_id": summary.get("task_id"),
            "run_id": summary.get("run_id"),
            "run_mode": summary.get("run_mode"),
            "llm_gateway_route": summary.get("llm_gateway_route"),
            "result_status": summary.get("result_status"),
            "projection_complete": summary.get("projection_complete"),
            "episode_execution_spec_sha256": summary.get("episode_execution_spec_sha256"),
        },
        "projection_manifest_facts": {
            "schema_version": manifest.get("schema_version"),
            "projection_created_from_run_episode": manifest.get("projection_created_from_run_episode"),
            "episode_execution_spec_sha256": manifest.get("episode_execution_spec_sha256"),
            "provider_route": manifest.get("provider_route"),
            "llm_gateway_route": manifest.get("llm_gateway_route"),
            "run_mode": manifest.get("run_mode"),
            "permission_mode": manifest.get("permission_mode"),
            "network_policy": manifest.get("network_policy"),
            "test_feedback_policy": manifest.get("test_feedback_policy"),
            "formal_online_rl_eligible": manifest.get("formal_online_rl_eligible"),
            "policy_loss_candidate": manifest.get("policy_loss_candidate"),
            "tool_registry_digest": manifest.get("tool_registry_digest"),
            "tool_schema_snapshot_digest": manifest.get("tool_schema_snapshot_digest"),
            "allowed_tool_names_digest": manifest.get("allowed_tool_names_digest"),
            "projection_source_training_view_digest": manifest.get("projection_source_training_view_digest"),
            "projection_file_digests": {
                key: value
                for key, value in sorted(manifest.get("projection_file_digests", {}).items())
                if key
                in {
                    "compat_projection_manifest.json",
                    "episode_execution_spec_report.json",
                    "training_view_projection.json",
                    "provider_route_qualification.json",
                    "projection_validation_report.json",
                }
            },
        },
        "projection_validation_facts": {
            "projection_complete": validation.get("projection_complete"),
            "error_count": validation.get("error_count"),
        },
        "provider_route_qualification_facts": {
            "provider_route": route_report.get("provider_route"),
            "llm_gateway_route": route_report.get("llm_gateway_route"),
            "formal_online_rl_eligible": route_report.get("formal_online_rl_eligible"),
            "policy_loss_candidate": route_report.get("policy_loss_candidate"),
            "qualification_reason": route_report.get("qualification_reason"),
        },
        "training_view_projection_facts": {
            "schema_version": training_view.get("schema_version"),
            "route": training_view.get("route"),
            "online_rl_eligible": training_view.get("online_rl_eligible"),
            "response_token_count": training_view.get("response_token_count"),
            "response_mask_count": training_view.get("response_mask_count"),
            "response_span_count": training_view.get("response_span_count"),
            "invalid_for_training": training_view.get("invalid_for_training"),
            "invalid_for_online_rl": training_view.get("invalid_for_online_rl"),
        },
        "episode_execution_spec_report_facts": {
            "schema_version": spec_report.get("schema_version"),
            "raw_prompt_source": spec_report.get("raw_prompt_source"),
            "episode_execution_spec_ref": spec_report.get("episode_execution_spec_ref"),
            "tool_registry_digest": spec_report.get("tool_registry_digest"),
            "tool_schema_snapshot_digest": spec_report.get("tool_schema_snapshot_digest"),
            "allowed_tool_names": spec_report.get("allowed_tool_names"),
        },
        "run_config_projection_facts": {
            "schema_version": run_config_projection.get("schema_version"),
            "scaffold_id": run_config_projection.get("scaffold_id"),
            "permission_mode": run_config_projection.get("permission_mode"),
            "network_policy": run_config_projection.get("network_policy"),
            "request_run_mode": run_config_projection.get("request_run_mode"),
        },
        "stage16g1_registry_contract_sha256": registry_version,
        "derived_profile_id_for_current_default_scaffold": "swe_public_core",
        "profile_or_registry_version_carried_to_public_projection": projection_contains_registry_version,
        "blocked": False,
        "blocked_reason": None,
    }


def build_public_evidence_policy() -> dict[str, Any]:
    return {
        "schema_version": "stage16g1.public_evidence_policy.v1",
        "allowed_reference_kinds": ["repo_relative_path", "source_label", "opaque_ref", "sha256", "schema_version"],
        "forbidden_content_patterns": [
            "local_user_home_path",
            "private_system_path",
            "generic_home_directory_path",
            "temporary_directory_path",
            "runtime-private path pattern",
            "provider_secret",
            "api_key",
            "common_api_token_patterns",
            "private_key_header",
        ],
        "raw_artifact_policy": "private_by_default",
        "public_projection_policy": "public_safe_summary_and_sha256_only",
        "required_hash_binding": True,
        "path_redaction_required": True,
    }


def _scan_public_files(output_dir: Path) -> dict[str, Any]:
    findings = []
    for path in sorted(output_dir.glob("stage16g1_*")):
        if path.suffix not in {".json", ".md"}:
            continue
        if path.name == "stage16g1_path_leak_scan_report.json":
            continue
        text = path.read_text()
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(text):
                findings.append({"relative_path": path.relative_to(output_dir).as_posix(), "pattern": pattern.pattern})
    return {
        "schema_version": "stage16g1.path_leak_scan_report.v1",
        "public_path_leak_scan_passed": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "scanned_suffixes": [".json", ".md"],
    }


def _validate_reports(
    *,
    registry: dict[str, Any],
    taxonomy: dict[str, Any],
    gate: dict[str, Any],
    smoke: dict[str, Any],
    source_inventory: dict[str, Any],
    path_scan: dict[str, Any] | None = None,
    stage16g0_dir: Path = DEFAULT_STAGE16G0_DIR,
) -> dict[str, Any]:
    failures: list[str] = []
    comparison_records = load_stage16g0_comparison(stage16g0_dir)
    comparison_by_id = {record["capability_id"]: record for record in comparison_records}
    registry_records = list(registry.get("records", []))
    registry_by_id = {record.get("capability_id"): record for record in registry_records}
    current_facts = build_current_code_facts()

    if len(comparison_records) != 27:
        failures.append("comparison_record_count_not_27")
    if set(comparison_by_id) != set(registry_by_id):
        failures.append("registry_capability_ids_do_not_match_comparison")
    blocking_records = [record for record in comparison_records if record["blocking_for_main_swe_rl"]]
    post_optional = [record for record in comparison_records if record["required_stage"] == "post_16G_optional"]
    if len(blocking_records) != 17:
        failures.append("blocking_for_main_swe_rl_count_not_17")
    if len(post_optional) != 4:
        failures.append("post_16g_optional_count_not_4")

    source_inputs = source_inventory.get("source_inputs")
    if not isinstance(source_inputs, list):
        failures.append("source_inventory_inputs_not_list")
        source_inputs = []
    source_inputs_by_label = {
        entry.get("source_label"): entry
        for entry in source_inputs
        if isinstance(entry, dict) and isinstance(entry.get("source_label"), str)
    }
    expected_source_labels = {filename.removesuffix(".json") for filename in INPUT_FILES}
    if set(source_inputs_by_label) != expected_source_labels:
        failures.append("source_inventory_input_labels_mismatch")
    for filename in INPUT_FILES:
        expected_path = stage16g0_dir / filename
        expected_label = filename.removesuffix(".json")
        source_entry = source_inputs_by_label.get(expected_label)
        if source_entry is None:
            failures.append(f"source_inventory_missing_input:{filename}")
            continue
        if source_entry.get("relative_path") != expected_path.as_posix():
            failures.append(f"source_inventory_input_path_mismatch:{filename}")
        if source_entry.get("exists") is not True:
            failures.append(f"source_inventory_input_not_marked_existing:{filename}")
        if not expected_path.exists():
            failures.append(f"source_inventory_expected_input_missing_on_disk:{filename}")
            continue
        if source_entry.get("sha256") != _file_sha256(expected_path):
            failures.append(f"source_inventory_input_sha256_mismatch:{filename}")

    for capability_id, comparison_record in comparison_by_id.items():
        registry_record = registry_by_id.get(capability_id)
        if registry_record is None:
            continue
        if registry_record.get("owner_stage") != comparison_record["required_stage"]:
            if not (
                registry_record.get("stage_override_reason")
                and registry_record.get("source_requirement_update_ref")
            ):
                failures.append(f"owner_stage_mismatch:{capability_id}")
        if comparison_record["blocking_for_main_swe_rl"] and not registry_record.get("owner_stage"):
            failures.append(f"blocking_capability_missing_owner_stage:{capability_id}")
        if comparison_record["required_stage"] == "post_16G_optional":
            if not registry_record.get("profiles") or "schema_reserved" not in set(registry_record["profiles"].values()):
                failures.append(f"post_optional_not_schema_reserved:{capability_id}")
        for field_name in ("allowed_artifact_visibility", "denial_feedback_policy", "training_projection_policy"):
            if not registry_record.get(field_name):
                failures.append(f"registry_record_missing_{field_name}:{capability_id}")
        training_policy = registry_record.get("training_projection_policy", {})
        if training_policy.get("tool_event_policy_loss_unit") != "not_an_individual_policy_loss_sample":
            failures.append(f"tool_event_policy_loss_unit_wrong:{capability_id}")
        if registry_record.get("executor_binding_status") == "not_implemented" and training_policy.get(
            "allowed_in_policy_loss_trajectory"
        ):
            failures.append(f"not_implemented_policy_loss_allowed:{capability_id}")
        if registry_record.get("model_visible_schema_status") == "planned" and training_policy.get(
            "allowed_in_policy_loss_trajectory"
        ):
            failures.append(f"planned_schema_policy_loss_allowed:{capability_id}")
        if registry_record.get("run_episode_visibility_status") == "planned" and training_policy.get(
            "allowed_in_policy_loss_trajectory"
        ):
            failures.append(f"planned_run_episode_policy_loss_allowed:{capability_id}")
        if registry_record.get("executor_binding_status") in {"implemented", "present", "enabled"}:
            for tool_id in registry_record.get("tool_ids", []):
                if not _tool_is_resolvable_or_fallback(tool_id):
                    failures.append(f"implemented_tool_not_resolvable:{capability_id}:{tool_id}")

    profiles = {profile["profile_id"]: profile for profile in taxonomy.get("profiles", [])}
    if set(profiles) != set(PROFILE_IDS):
        failures.append("profile_ids_mismatch")
    core = profiles.get("swe_public_core", {})
    if "persistent_diagnostic_session" in set(core.get("allowed_capability_ids", [])):
        failures.append("swe_public_core_contains_persistent_diagnostic_session")
    if "persistent_diagnostic_session" not in set(core.get("must_not_include", [])):
        failures.append("swe_public_core_missing_persistent_shell_must_not_include")
    extended = profiles.get("swe_public_extended", {})
    extended_boundaries = set(extended.get("required_safety_boundaries", []))
    for boundary in EXTENDED_PROFILE_REQUIRED_BOUNDARIES:
        if boundary not in extended_boundaries:
            failures.append(f"swe_public_extended_missing_boundary:{boundary}")
    persistent_record = registry_by_id.get("persistent_diagnostic_session", {})
    persistent_boundary_policy = persistent_record.get("persistent_session_boundary_policy")
    if not isinstance(persistent_boundary_policy, dict):
        failures.append("persistent_diagnostic_session_missing_boundary_policy")
    else:
        for field_name in (
            "session_reset_required",
            "artifact_hygiene_required",
            "path_redaction_required",
            "public_safe_projection_required",
        ):
            if persistent_boundary_policy.get(field_name) is not True:
                failures.append(f"persistent_diagnostic_session_boundary_missing:{field_name}")
        if persistent_boundary_policy.get("main_training_core_default_allowed") is not False:
            failures.append("persistent_diagnostic_session_core_default_not_forbidden")
    redteam = profiles.get("redteam_restricted", {})
    if redteam.get("primary_training_default"):
        failures.append("redteam_restricted_marked_primary_training_default")

    if gate.get("tool_event_eligibility", {}).get("unit") != "tool_event":
        failures.append("gate_missing_tool_event_unit")
    if gate.get("trajectory_eligibility", {}).get("unit") != "trajectory_or_sample":
        failures.append("gate_missing_trajectory_unit")

    if smoke.get("status") != "passed":
        failures.append("run_episode_profile_smoke_not_passed")
    if smoke.get("blocked"):
        failures.append("run_episode_profile_smoke_blocked")
    if not smoke.get("not_json_only"):
        failures.append("run_episode_profile_smoke_json_only")
    if smoke.get("smoke_route") != "run_episode_task_real_episode_mock_projection":
        failures.append("run_episode_profile_smoke_route_not_real_run_episode_task")
    if not smoke.get("actual_run_episode_task_invoked"):
        failures.append("run_episode_profile_smoke_not_actual_run_episode_task")
    manifest_facts = smoke.get("projection_manifest_facts", {})
    if not manifest_facts.get("projection_created_from_run_episode"):
        failures.append("run_episode_profile_smoke_manifest_not_from_run_episode")
    validation_facts = smoke.get("projection_validation_facts", {})
    if validation_facts.get("projection_complete") is not True or validation_facts.get("error_count") != 0:
        failures.append("run_episode_profile_smoke_projection_not_complete")
    spec_report_facts = smoke.get("episode_execution_spec_report_facts", {})
    if not manifest_facts.get("tool_registry_digest") or not spec_report_facts.get("tool_registry_digest"):
        failures.append("run_episode_profile_smoke_missing_tool_registry_digest")
    if manifest_facts.get("tool_registry_digest") != spec_report_facts.get("tool_registry_digest"):
        failures.append("run_episode_profile_smoke_tool_registry_digest_mismatch")
    if not smoke.get("profile_or_registry_version_carried_to_public_projection"):
        failures.append("run_episode_profile_version_not_projected")

    required_source_paths = {entry["relative_path"]: entry for entry in source_inventory.get("source_code_facts", [])}
    for source_path in SOURCE_FILES:
        if source_path not in required_source_paths:
            failures.append(f"source_inventory_missing:{source_path}")

    if not current_facts["runtime_default_scaffold_is_simple_react"]:
        failures.append("runtime_default_scaffold_not_simple_react")
    if not current_facts["simple_react_exposes_create_file"]:
        failures.append("simple_react_does_not_expose_create_file")
    if current_facts["patch_focused_react_mini_shell_present"]:
        failures.append("patch_focused_react_mini_shell_present_unexpectedly")
    if not current_facts["execute_bash_narrow_but_nonempty"]:
        failures.append("execute_bash_not_narrow_nonempty")
    if not current_facts["diagnostic_shell_not_core_default"]:
        failures.append("diagnostic_shell_is_core_default")

    if path_scan is not None and not path_scan.get("public_path_leak_scan_passed"):
        failures.append("public_path_leak_scan_failed")

    checks = {
        "comparison_record_count": len(comparison_records),
        "blocking_for_main_swe_rl_count": len(blocking_records),
        "post_16g_optional_count": len(post_optional),
        "all_capabilities_mapped_to_registry": set(comparison_by_id) == set(registry_by_id),
        "all_blocking_capabilities_have_owner_stage": all(
            registry_by_id.get(record["capability_id"], {}).get("owner_stage") for record in blocking_records
        ),
        "owner_stage_matches_stage16g0_required_stage": not any(
            failure.startswith("owner_stage_mismatch:") for failure in failures
        ),
        "all_tools_have_artifact_visibility": not any(
            failure.startswith("registry_record_missing_allowed_artifact_visibility") for failure in failures
        ),
        "all_tools_have_training_projection_policy": not any(
            failure.startswith("registry_record_missing_training_projection_policy") for failure in failures
        ),
        "all_tools_have_denial_feedback_policy": not any(
            failure.startswith("registry_record_missing_denial_feedback_policy") for failure in failures
        ),
        "swe_public_core_excludes_persistent_shell": "swe_public_core_contains_persistent_diagnostic_session" not in failures,
        "swe_public_extended_has_session_and_projection_boundaries": not any(
            failure.startswith("swe_public_extended_missing_boundary:") for failure in failures
        ),
        "persistent_diagnostic_session_has_boundary_policy": not any(
            failure.startswith("persistent_diagnostic_session_boundary_missing:")
            or failure
            in {
                "persistent_diagnostic_session_missing_boundary_policy",
                "persistent_diagnostic_session_core_default_not_forbidden",
            }
            for failure in failures
        ),
        "post_16g_optional_capabilities_reserved": not any(
            failure.startswith("post_optional_not_schema_reserved:") for failure in failures
        ),
        "run_episode_primary_entry_declared": True,
        "legacy_run_task_not_primary": True,
        "model_visible_prompt_scaffold_public_environment_consistency_declared": True,
        "counts_derived_from_stage16g0_comparison": True,
        "current_code_facts_passed": not any(
            failure
            in {
                "runtime_default_scaffold_not_simple_react",
                "simple_react_does_not_expose_create_file",
                "patch_focused_react_mini_shell_present_unexpectedly",
                "execute_bash_not_narrow_nonempty",
                "diagnostic_shell_is_core_default",
            }
            for failure in failures
        ),
    }
    return {
        "schema_version": "stage16g1.profile_registry_inspection_report.v1",
        "status": "passed" if not failures else "failed",
        "checks": checks,
        "failure_count": len(failures),
        "failures": failures,
        "current_code_facts": current_facts,
    }


def build_profile_registry_inspection_report(
    registry: dict[str, Any] | None = None,
    taxonomy: dict[str, Any] | None = None,
    gate: dict[str, Any] | None = None,
    smoke: dict[str, Any] | None = None,
    source_inventory: dict[str, Any] | None = None,
    path_scan: dict[str, Any] | None = None,
    stage16g0_dir: Path = DEFAULT_STAGE16G0_DIR,
) -> dict[str, Any]:
    registry = registry or build_tool_registry_contract(stage16g0_dir)
    taxonomy = taxonomy or build_profile_taxonomy(registry)
    gate = gate or build_training_eligibility_gate_spec()
    smoke = smoke or build_run_episode_profile_smoke_report(registry)
    source_inventory = source_inventory or build_source_inventory(stage16g0_dir)
    return _validate_reports(
        registry=registry,
        taxonomy=taxonomy,
        gate=gate,
        smoke=smoke,
        source_inventory=source_inventory,
        path_scan=path_scan,
        stage16g0_dir=stage16g0_dir,
    )


def build_human_readable_summary(registry: dict[str, Any], inspection: dict[str, Any]) -> str:
    records = registry["records"]
    by_stage = Counter(record["owner_stage"] for record in records)
    lines = [
        "# Stage 16G.1 Tool Profile Summary",
        "",
        "本摘要只包含 public-safe 计数和结论，不包含本机绝对路径、私有 artifact 或 raw patch。",
        "",
        f"- registry record count: {len(records)}",
        f"- blocking capability count: {inspection['checks']['blocking_for_main_swe_rl_count']}",
        f"- post 16G optional count: {inspection['checks']['post_16g_optional_count']}",
        f"- inspection status: {inspection['status']}",
        "",
        "## Owner Stage Counts",
        "",
    ]
    for stage, count in sorted(by_stage.items()):
        lines.append(f"- {stage}: {count}")
    lines.extend(
        [
            "",
            "## Gate Summary",
            "",
            "- `swe_public_core` 不包含 persistent diagnostic shell。",
            "- `run_episode` 是主入口，旧 `run_task` 只作为 legacy compatibility。",
            "- 单个工具事件不是 policy loss sample；训练资格在 trajectory / sample 层判断。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_stage16g1_reports(stage16g0_dir: Path = DEFAULT_STAGE16G0_DIR) -> dict[str, Any]:
    source_inventory = build_source_inventory(stage16g0_dir)
    registry = build_tool_registry_contract(stage16g0_dir)
    taxonomy = build_profile_taxonomy(registry)
    gate = build_training_eligibility_gate_spec()
    smoke = build_run_episode_profile_smoke_report(registry)
    public_policy = build_public_evidence_policy()
    inspection = build_profile_registry_inspection_report(
        registry=registry,
        taxonomy=taxonomy,
        gate=gate,
        smoke=smoke,
        source_inventory=source_inventory,
        stage16g0_dir=stage16g0_dir,
    )
    return {
        "stage16g1_source_inventory.json": source_inventory,
        "stage16g1_tool_registry_contract.json": registry,
        "stage16g1_profile_taxonomy.json": taxonomy,
        "stage16g1_training_eligibility_gate_spec.json": gate,
        "stage16g1_profile_registry_inspection_report.json": inspection,
        "stage16g1_run_episode_profile_smoke_report.json": smoke,
        "stage16g1_public_evidence_policy.json": public_policy,
        "stage16g1_human_readable_tool_profile_summary.md": build_human_readable_summary(registry, inspection),
    }


def _write_json(path: Path, payload: Any) -> str:
    path.write_text(_json_dumps(payload))
    return _file_sha256(path)


def _write_text(path: Path, text: str) -> str:
    path.write_text(text)
    return _file_sha256(path)


def write_stage16g1_reports(
    output_dir: Path = DEFAULT_STAGE16G1_DIR,
    stage16g0_dir: Path = DEFAULT_STAGE16G0_DIR,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = build_stage16g1_reports(stage16g0_dir)
    digests: dict[str, str] = {}
    for filename, payload in reports.items():
        path = output_dir / filename
        if filename.endswith(".md"):
            digests[filename] = _write_text(path, str(payload))
        else:
            digests[filename] = _write_json(path, payload)
    path_scan = _scan_public_files(output_dir)
    reports["stage16g1_path_leak_scan_report.json"] = path_scan
    digests["stage16g1_path_leak_scan_report.json"] = _write_json(
        output_dir / "stage16g1_path_leak_scan_report.json", path_scan
    )
    inspection = build_profile_registry_inspection_report(
        registry=reports["stage16g1_tool_registry_contract.json"],
        taxonomy=reports["stage16g1_profile_taxonomy.json"],
        gate=reports["stage16g1_training_eligibility_gate_spec.json"],
        smoke=reports["stage16g1_run_episode_profile_smoke_report.json"],
        source_inventory=reports["stage16g1_source_inventory.json"],
        path_scan=path_scan,
        stage16g0_dir=stage16g0_dir,
    )
    reports["stage16g1_profile_registry_inspection_report.json"] = inspection
    digests["stage16g1_profile_registry_inspection_report.json"] = _write_json(
        output_dir / "stage16g1_profile_registry_inspection_report.json", inspection
    )
    reports["stage16g1_human_readable_tool_profile_summary.md"] = build_human_readable_summary(
        reports["stage16g1_tool_registry_contract.json"], inspection
    )
    digests["stage16g1_human_readable_tool_profile_summary.md"] = _write_text(
        output_dir / "stage16g1_human_readable_tool_profile_summary.md",
        reports["stage16g1_human_readable_tool_profile_summary.md"],
    )
    path_scan = _scan_public_files(output_dir)
    reports["stage16g1_path_leak_scan_report.json"] = path_scan
    digests["stage16g1_path_leak_scan_report.json"] = _write_json(
        output_dir / "stage16g1_path_leak_scan_report.json", path_scan
    )
    summary = build_acceptance_summary(reports=reports, digests=digests, stage16g0_dir=stage16g0_dir)
    reports["stage16g1_acceptance_summary.json"] = summary
    digests["stage16g1_acceptance_summary.json"] = _write_json(
        output_dir / "stage16g1_acceptance_summary.json", summary
    )
    path_scan = _scan_public_files(output_dir)
    digests["stage16g1_path_leak_scan_report.json"] = _write_json(
        output_dir / "stage16g1_path_leak_scan_report.json", path_scan
    )
    reports["stage16g1_path_leak_scan_report.json"] = path_scan
    summary = build_acceptance_summary(reports=reports, digests=digests, stage16g0_dir=stage16g0_dir)
    digests["stage16g1_acceptance_summary.json"] = _write_json(
        output_dir / "stage16g1_acceptance_summary.json", summary
    )
    return digests


def build_acceptance_summary(
    *,
    reports: dict[str, Any],
    digests: dict[str, str],
    stage16g0_dir: Path = DEFAULT_STAGE16G0_DIR,
) -> dict[str, Any]:
    comparison = load_stage16g0_comparison(stage16g0_dir)
    registry = reports["stage16g1_tool_registry_contract.json"]
    taxonomy = reports["stage16g1_profile_taxonomy.json"]
    inspection = reports["stage16g1_profile_registry_inspection_report.json"]
    path_scan = reports["stage16g1_path_leak_scan_report.json"]
    blocking_count = sum(1 for record in comparison if record["blocking_for_main_swe_rl"])
    optional_count = sum(1 for record in comparison if record["required_stage"] == "post_16G_optional")
    status = "passed" if inspection["status"] == "passed" and path_scan["public_path_leak_scan_passed"] else "failed"
    return {
        "schema_version": "stage16g1.acceptance_summary.v1",
        "status": status,
        "stage16g1_complete": status == "passed",
        "comparison_record_count": len(comparison),
        "blocking_for_main_swe_rl_count": blocking_count,
        "post_16g_optional_count": optional_count,
        "profile_count": len(taxonomy["profiles"]),
        "source_inventory_sha256": digests["stage16g1_source_inventory.json"],
        "tool_registry_contract_sha256": digests["stage16g1_tool_registry_contract.json"],
        "profile_taxonomy_sha256": digests["stage16g1_profile_taxonomy.json"],
        "training_eligibility_gate_spec_sha256": digests["stage16g1_training_eligibility_gate_spec.json"],
        "profile_registry_inspection_report_sha256": digests["stage16g1_profile_registry_inspection_report.json"],
        "run_episode_profile_smoke_report_sha256": digests["stage16g1_run_episode_profile_smoke_report.json"],
        "public_evidence_policy_sha256": digests["stage16g1_public_evidence_policy.json"],
        "path_leak_scan_report_sha256": digests["stage16g1_path_leak_scan_report.json"],
        "human_readable_summary_sha256": digests["stage16g1_human_readable_tool_profile_summary.md"],
        "public_path_leak_scan_passed": bool(path_scan["public_path_leak_scan_passed"]),
        "machine_inspector_passed": inspection["status"] == "passed",
        "stage16g2_allowed_to_start": status == "passed",
        "stage17b_real_data_freeze_allowed": False,
        "stage20_warm_start_data_generation_allowed": False,
        "stage21_formal_rl_allowed": False,
        "counts_derived_from_stage16g0_comparison": True,
        "failure_count": inspection["failure_count"],
        "failure_ids": inspection["failures"],
        "registry_record_count": len(registry["records"]),
    }


def _load_stage16g1_dir(summary_path: Path) -> dict[str, Any]:
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


def _acceptance_summary_field_failures(
    *,
    summary_payload: dict[str, Any],
    payloads: dict[str, Any],
    validation: dict[str, Any],
    path_scan: dict[str, Any],
) -> list[str]:
    registry = payloads["stage16g1_tool_registry_contract.json"]
    taxonomy = payloads["stage16g1_profile_taxonomy.json"]
    checks = validation["checks"]
    expected_status = (
        "passed"
        if validation["status"] == "passed" and bool(path_scan.get("public_path_leak_scan_passed"))
        else "failed"
    )
    expected = {
        "schema_version": "stage16g1.acceptance_summary.v1",
        "status": expected_status,
        "stage16g1_complete": expected_status == "passed",
        "comparison_record_count": checks["comparison_record_count"],
        "blocking_for_main_swe_rl_count": checks["blocking_for_main_swe_rl_count"],
        "post_16g_optional_count": checks["post_16g_optional_count"],
        "profile_count": len(taxonomy.get("profiles", [])),
        "public_path_leak_scan_passed": bool(path_scan.get("public_path_leak_scan_passed")),
        "machine_inspector_passed": validation["status"] == "passed",
        "stage16g2_allowed_to_start": expected_status == "passed",
        "stage17b_real_data_freeze_allowed": False,
        "stage20_warm_start_data_generation_allowed": False,
        "stage21_formal_rl_allowed": False,
        "counts_derived_from_stage16g0_comparison": True,
        "failure_count": len(validation["failures"]),
        "failure_ids": validation["failures"],
        "registry_record_count": len(registry.get("records", [])),
    }
    failures = []
    for field_name, expected_value in expected.items():
        if summary_payload.get(field_name) != expected_value:
            failures.append(f"acceptance_summary_field_mismatch:{field_name}")
    allowed_fields = set(expected) | set(SUMMARY_DIGEST_FIELDS.values())
    for field_name in sorted(set(summary_payload) - allowed_fields):
        failures.append(f"acceptance_summary_unexpected_field:{field_name}")
    return failures


def inspect_stage16g1_tool_profile(summary_path: str | Path, *, assert_complete: bool = False) -> str:
    summary = Path(summary_path)
    if not summary.exists():
        raise RepoHarnessError(f"Stage 16G.1 acceptance summary not found: {summary}")
    base = summary.parent
    payloads = _load_stage16g1_dir(summary)
    failures: list[str] = []
    missing = [filename for filename in REQUIRED_OUTPUT_FILES if filename not in payloads]
    failures.extend(f"missing_required_file:{filename}" for filename in missing)
    if missing:
        report = {
            "schema_version": "stage16g1.cli_inspection_result.v1",
            "status": "failed",
            "failure_count": len(failures),
            "failures": failures,
        }
        if assert_complete:
            raise RepoHarnessError(_json_dumps(report))
        return _json_dumps(report)

    actual_digests = {filename: _file_sha256(base / filename) for filename in REQUIRED_OUTPUT_FILES}
    summary_payload = payloads["stage16g1_acceptance_summary.json"]
    for filename, field_name in SUMMARY_DIGEST_FIELDS.items():
        if summary_payload.get(field_name) != actual_digests[filename]:
            failures.append(f"sha256_mismatch:{filename}")

    current_path_scan = _scan_public_files(base)
    if current_path_scan != payloads["stage16g1_path_leak_scan_report.json"]:
        failures.append("path_leak_scan_report_stale_or_mismatched")
    if not current_path_scan.get("public_path_leak_scan_passed"):
        failures.append("public_path_leak_scan_failed_current_files")

    validation = build_profile_registry_inspection_report(
        registry=payloads["stage16g1_tool_registry_contract.json"],
        taxonomy=payloads["stage16g1_profile_taxonomy.json"],
        gate=payloads["stage16g1_training_eligibility_gate_spec.json"],
        smoke=payloads["stage16g1_run_episode_profile_smoke_report.json"],
        source_inventory=payloads["stage16g1_source_inventory.json"],
        path_scan=current_path_scan,
    )
    failures.extend(validation["failures"])
    failures.extend(
        _acceptance_summary_field_failures(
            summary_payload=summary_payload,
            payloads=payloads,
            validation=validation,
            path_scan=current_path_scan,
        )
    )

    report = {
        "schema_version": "stage16g1.cli_inspection_result.v1",
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
