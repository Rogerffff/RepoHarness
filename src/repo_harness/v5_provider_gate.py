"""V5 Stage 3A provider registry, credential gate, and cost budget builders."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.model_client.providers.deepseek import (
    DEEPSEEK_ALLOWED_MODELS,
    DEEPSEEK_DEFAULT_BASE_URL,
    DEEPSEEK_DEFAULT_MODEL,
    DEEPSEEK_OFFICIAL_DOCS_URL,
    deepseek_credential_status,
)
from repo_harness.model_client.providers.openai import (
    OPENAI_BASE_URL,
    OPENAI_DEFAULT_MODEL,
    OPENAI_ENDPOINT_CATEGORY,
    OPENAI_OFFICIAL_DOCS_URL,
    openai_credential_status,
    openai_sdk_available,
)
from repo_harness.schema_versions import (
    V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V5_PROVIDER_COST_BUDGET_REPORT_VERSION,
    V5_PROVIDER_CREDENTIAL_GATE_REPORT_VERSION,
    V5_PROVIDER_RAW_CONTENT_REDACTION_REPORT_VERSION,
    V5_PROVIDER_REGISTRY_REPORT_VERSION,
    V5_PROVIDER_SMOKE_REPORT_VERSION,
    V5_PROVIDER_STATUS_NORMALIZATION_REPORT_VERSION,
)
from repo_harness.v5_evidence import (
    V5_ADAPTER_STATUS_VALUES,
    V5_CREDENTIAL_STATUS_VALUES,
    V5_PROVIDER_FAMILIES,
    _builder_command_log_entry,
    _evidence_ref,
    _utc_timestamp,
    _write_json,
    _write_jsonl,
)


V5_STAGE3A_PROVIDER_GATE_OUTPUT_NAMES = (
    "v5_provider_registry_report.json",
    "v5_provider_credential_gate_report.json",
    "v5_provider_smoke_report.json",
    "v5_provider_raw_content_redaction_report.json",
    "v5_provider_status_normalization_report.json",
    "build_v5_provider_gate_command_log_entry.json",
    "v5_stage3a_provider_gate_command_log.jsonl",
)

V5_STAGE3A_COST_BUDGET_OUTPUT_NAMES = (
    "v5_provider_cost_budget_report.json",
    "build_v5_provider_cost_budget_command_log_entry.json",
    "v5_stage3a_provider_cost_budget_command_log.jsonl",
)

V5_PROVIDER_RAW_CONTENT_POLICY = "audit_only_redacted_never_model_visible"
V5_STAGE3A_SMOKE_MODE = "credential_and_adapter_structured_probe_no_provider_api_call"
_RAW_SECRET_RE = re.compile(r"\bsk-(?:proj-|ant-api03-)?[A-Za-z0-9_\-]{12,}\b")


def build_provider_gate_report(
    *,
    task_set_manifest: str | Path,
    output_dir: str | Path,
    allow_local_secret_file: bool = False,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build V5 Stage 3A provider registry and credential gate evidence."""

    root = Path(output_dir)
    _refuse_existing_outputs(root, V5_STAGE3A_PROVIDER_GATE_OUTPUT_NAMES, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)

    task_set_path = Path(task_set_manifest)
    task_set = _read_json(task_set_path)
    _require_stage2b_inventory_gate(task_set)

    registry_path = root / "v5_provider_registry_report.json"
    credential_gate_path = root / "v5_provider_credential_gate_report.json"
    smoke_path = root / "v5_provider_smoke_report.json"
    redaction_path = root / "v5_provider_raw_content_redaction_report.json"
    normalization_path = root / "v5_provider_status_normalization_report.json"
    command_entry_path = root / "build_v5_provider_gate_command_log_entry.json"
    command_log_path = root / "v5_stage3a_provider_gate_command_log.jsonl"

    credential_facts = _credential_facts(allow_local_secret_file=allow_local_secret_file)
    registry = _provider_registry_payload(
        task_set_path=task_set_path,
        allow_local_secret_file=allow_local_secret_file,
    )
    smoke = _provider_smoke_payload(credential_facts=credential_facts)
    redaction = _raw_content_redaction_payload()
    normalization = _status_normalization_payload()

    _write_json(registry_path, registry)
    _write_json(smoke_path, smoke)
    _write_json(redaction_path, redaction)
    _write_json(normalization_path, normalization)

    gate = _credential_gate_payload(
        task_set_path=task_set_path,
        registry_path=registry_path,
        smoke_path=smoke_path,
        redaction_path=redaction_path,
        normalization_path=normalization_path,
        credential_facts=credential_facts,
        allow_local_secret_file=allow_local_secret_file,
    )
    gate["raw_secret_value_present"] = _payload_contains_raw_secret_value(gate)
    _write_json(credential_gate_path, gate)

    command_entry = _builder_command_log_entry(
        command_name="build-v5-provider-gate",
        input_paths=[task_set_path],
        output_paths=[
            registry_path,
            credential_gate_path,
            smoke_path,
            redaction_path,
            normalization_path,
        ],
        producer_stage="v5_stage3a_provider_gate",
    )
    command_entry["schema_version"] = V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION
    _write_json(command_entry_path, command_entry)
    _write_jsonl(command_log_path, [command_entry])
    return credential_gate_path


def build_provider_cost_budget_report(
    *,
    provider_gate_report: str | Path,
    output: str | Path,
    max_real_provider_calls: int = 24,
    max_cost_usd: float = 5.0,
    actual_real_provider_calls: int = 0,
    actual_cost_proxy_usd: float = 0.0,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build a V5 Stage 3A provider cost budget report from explicit inputs."""

    output_path = Path(output)
    root = output_path.parent
    _refuse_existing_outputs(root, V5_STAGE3A_COST_BUDGET_OUTPUT_NAMES, fail_if_output_exists)
    if fail_if_output_exists and output_path.exists():
        raise ConfigError(f"V5 Stage 3A 输出已存在，不能覆盖旧 evidence：{output_path}")
    root.mkdir(parents=True, exist_ok=True)
    gate_path = Path(provider_gate_report)
    gate = _read_json(gate_path)
    _require_provider_gate_shape(gate)
    if max_real_provider_calls < 0:
        raise ConfigError("max_real_provider_calls 不能为负数。")
    if max_cost_usd < 0:
        raise ConfigError("max_cost_usd 不能为负数。")
    if actual_real_provider_calls < 0:
        raise ConfigError("actual_real_provider_calls 不能为负数。")
    if actual_cost_proxy_usd < 0:
        raise ConfigError("actual_cost_proxy_usd 不能为负数。")
    if actual_real_provider_calls > max_real_provider_calls:
        raise ConfigError("actual_real_provider_calls 不能超过 max_real_provider_calls。")
    if actual_cost_proxy_usd > max_cost_usd:
        raise ConfigError("actual_cost_proxy_usd 不能超过 max_cost_usd。")

    budget_exhausted = (
        actual_real_provider_calls >= max_real_provider_calls
        or actual_cost_proxy_usd >= max_cost_usd
    )
    cost_limited_skips = []
    if budget_exhausted and (max_real_provider_calls == 0 or max_cost_usd == 0):
        cost_limited_skips.append(
            {
                "provider_id": "all",
                "skip_type": "cost_limited_structured_skip",
                "skip_reason": "Stage 3A budget is exhausted before any real provider call.",
                "affected_matrix_cells": ["all_stage3a_provider_smoke_cells"],
                "affects_core_acceptance": True,
                "affects_resume_ready_acceptance": True,
                "counts_toward_real_provider_accepted_rate": False,
            }
        )

    payload = {
        "schema_version": V5_PROVIDER_COST_BUDGET_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3a_provider_gate",
        "provider_gate_ref": _evidence_ref(
            gate_path,
            kind="v5_provider_credential_gate_report",
            purpose="V5 Stage 3A provider credential gate report",
            visibility="audit_only",
            producer_command="build-v5-provider-gate",
            producer_stage="v5_stage3a_provider_gate",
            inspect_command="inspect-v5-provider-gate",
        ),
        "max_real_provider_calls": max_real_provider_calls,
        "max_cost_usd": float(max_cost_usd),
        "cost_proxy_formula": "actual_cost_proxy_usd is supplied by the run matrix builder; Stage 3A records zero calls before real agent runs.",
        "actual_real_provider_calls": actual_real_provider_calls,
        "actual_cost_proxy_usd": float(actual_cost_proxy_usd),
        "cost_limited_structured_skip": cost_limited_skips,
        "budget_exhausted_before_run": budget_exhausted,
        "provider_family_budget_policy": {
            "deepseek": {
                "primary_family": True,
                "default_max_calls_reserved_for_stage3b": max(0, max_real_provider_calls),
                "counts_toward_core_acceptance_if_actual_run_exists": True,
            },
            "openai": {
                "primary_family": False,
                "fallback_only_current_adapter": True,
                "counts_toward_resume_ready_provider_comparison": False,
            },
            "anthropic_claude": {
                "primary_family": False,
                "adapter_status": "adapter_not_implemented",
                "counts_toward_resume_ready_provider_comparison": False,
            },
        },
        "hard_stop_policy": {
            "stop_before_call_when_max_real_provider_calls_reached": True,
            "stop_before_call_when_max_cost_usd_reached": True,
            "structured_skip_status": "cost_limited_structured_skip",
        },
        "status": "passed",
    }
    _write_json(output_path, payload)

    command_entry_path = root / "build_v5_provider_cost_budget_command_log_entry.json"
    command_log_path = root / "v5_stage3a_provider_cost_budget_command_log.jsonl"
    command_entry = _builder_command_log_entry(
        command_name="build-v5-provider-cost-budget",
        input_paths=[gate_path],
        output_paths=[output_path],
        producer_stage="v5_stage3a_provider_cost_budget",
    )
    command_entry["schema_version"] = V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION
    _write_json(command_entry_path, command_entry)
    _write_jsonl(command_log_path, [command_entry])
    return output_path


def _provider_registry_payload(*, task_set_path: Path, allow_local_secret_file: bool) -> dict[str, Any]:
    return {
        "schema_version": V5_PROVIDER_REGISTRY_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3a_provider_gate",
        "task_set_ref": _evidence_ref(
            task_set_path,
            kind="v5_task_set_manifest",
            purpose="V5 Stage 2B merged task set manifest used by Stage 3A provider gate",
            visibility="audit_only",
            producer_command="merge-v5-task-set",
            producer_stage="v5_stage2b_task_set_merge",
            inspect_command="inspect-v5-task-set",
        ),
        "provider_families": list(V5_PROVIDER_FAMILIES),
        "providers": [
            {
                "provider_id": "deepseek",
                "provider_family": "deepseek",
                "adapter_module": "repo_harness.model_client.providers.deepseek.DeepSeekProviderClient",
                "adapter_status": "primary_supported",
                "primary_provider_supported": True,
                "fallback_only_current_adapter": False,
                "default_model": DEEPSEEK_DEFAULT_MODEL,
                "allowed_models": sorted(DEEPSEEK_ALLOWED_MODELS),
                "base_url_category": "deepseek_openai_compatible_chat_completions",
                "base_url": DEEPSEEK_DEFAULT_BASE_URL,
                "official_docs_url": DEEPSEEK_OFFICIAL_DOCS_URL,
                "credential_env_var": "DEEPSEEK_API_KEY",
                "credential_policy": "env_only" if not allow_local_secret_file else "env_or_local_secret_file_redacted",
                "counts_toward_core_acceptance_if_actual_run_exists": True,
                "counts_toward_resume_ready_provider_comparison": True,
            },
            {
                "provider_id": "openai",
                "provider_family": "openai",
                "adapter_module": "repo_harness.model_client.providers.openai.OpenAIProviderClient",
                "adapter_status": "fallback_only",
                "primary_provider_supported": False,
                "fallback_only_current_adapter": True,
                "default_model": OPENAI_DEFAULT_MODEL,
                "base_url_category": OPENAI_ENDPOINT_CATEGORY,
                "base_url": OPENAI_BASE_URL,
                "official_docs_url": OPENAI_OFFICIAL_DOCS_URL,
                "credential_env_var": "OPENAI_API_KEY",
                "openai_sdk_available": openai_sdk_available(),
                "counts_toward_core_acceptance_if_actual_run_exists": False,
                "counts_toward_resume_ready_provider_comparison": False,
                "fallback_policy": "may only run as DeepSeek fallback until primary-provider gates are implemented",
            },
            {
                "provider_id": "anthropic_claude",
                "provider_family": "anthropic_claude",
                "adapter_module": None,
                "adapter_status": "adapter_not_implemented",
                "primary_provider_supported": False,
                "fallback_only_current_adapter": False,
                "default_model": None,
                "base_url_category": "not_applicable_until_adapter_exists",
                "official_docs_url": "https://docs.anthropic.com/en/api/messages",
                "credential_env_var": "ANTHROPIC_API_KEY or CLAUDE_API_KEY",
                "counts_toward_core_acceptance_if_actual_run_exists": False,
                "counts_toward_resume_ready_provider_comparison": False,
            },
        ],
        "raw_provider_content_policy": V5_PROVIDER_RAW_CONTENT_POLICY,
        "provider_registry_policy": {
            "fallback_success_counts_as_primary_openai_run": False,
            "credential_missing_skip_counts_as_real_provider_run": False,
            "adapter_not_implemented_skip_counts_as_real_provider_run": False,
            "provider_raw_request_response_visibility": "audit_only_redacted",
        },
        "status": "passed",
    }


def _credential_gate_payload(
    *,
    task_set_path: Path,
    registry_path: Path,
    smoke_path: Path,
    redaction_path: Path,
    normalization_path: Path,
    credential_facts: dict[str, dict[str, Any]],
    allow_local_secret_file: bool,
) -> dict[str, Any]:
    adapter_status = {
        "openai": "fallback_only",
        "deepseek": "primary_supported",
        "anthropic_claude": "adapter_not_implemented",
    }
    credential_status = {
        provider: str(facts["credential_status"])
        for provider, facts in credential_facts.items()
    }
    structured_skips = _structured_skips(
        credential_status_by_provider=credential_status,
        adapter_status_by_provider=adapter_status,
    )
    return {
        "schema_version": V5_PROVIDER_CREDENTIAL_GATE_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3a_provider_gate",
        "task_set_ref": _evidence_ref(
            task_set_path,
            kind="v5_task_set_manifest",
            purpose="V5 Stage 2B merged task set manifest used by provider gate",
            visibility="audit_only",
            producer_command="merge-v5-task-set",
            producer_stage="v5_stage2b_task_set_merge",
            inspect_command="inspect-v5-task-set",
        ),
        "provider_registry_report_ref": _evidence_ref(
            registry_path,
            kind="v5_provider_registry_report",
            purpose="V5 Stage 3A provider registry report",
            visibility="audit_only",
            producer_command="build-v5-provider-gate",
            producer_stage="v5_stage3a_provider_gate",
            inspect_command="inspect-v5-provider-gate",
        ),
        "provider_smoke_report_ref": _evidence_ref(
            smoke_path,
            kind="v5_provider_smoke_report",
            purpose="V5 Stage 3A provider smoke structured status report",
            visibility="audit_only",
            producer_command="build-v5-provider-gate",
            producer_stage="v5_stage3a_provider_gate",
            inspect_command="inspect-v5-provider-gate",
        ),
        "provider_raw_content_redaction_report_ref": _evidence_ref(
            redaction_path,
            kind="v5_provider_raw_content_redaction_report",
            purpose="V5 Stage 3A provider raw content redaction policy report",
            visibility="audit_only",
            producer_command="build-v5-provider-gate",
            producer_stage="v5_stage3a_provider_gate",
            inspect_command="inspect-v5-provider-gate",
        ),
        "provider_status_normalization_report_ref": _evidence_ref(
            normalization_path,
            kind="v5_provider_status_normalization_report",
            purpose="V5 Stage 3A provider status normalization report",
            visibility="audit_only",
            producer_command="build-v5-provider-gate",
            producer_stage="v5_stage3a_provider_gate",
            inspect_command="inspect-v5-provider-gate",
        ),
        "provider_families": list(V5_PROVIDER_FAMILIES),
        "credential_status_by_provider": credential_status,
        "credential_source_by_provider": {
            provider: str(facts["credential_source"])
            for provider, facts in credential_facts.items()
        },
        "non_active_credential_sources_by_provider": {
            provider: list(facts.get("non_active_credential_sources", []))
            for provider, facts in credential_facts.items()
        },
        "credential_policy": {
            "deepseek": "env_only" if not allow_local_secret_file else "env_or_local_secret_file_redacted",
            "openai": "env_only",
            "anthropic_claude": "env_only_but_adapter_not_implemented",
        },
        "adapter_status_by_provider": adapter_status,
        "structured_skips": structured_skips,
        "raw_secret_value_present": False,
        "provider_raw_content_policy": V5_PROVIDER_RAW_CONTENT_POLICY,
        "provider_api_called": False,
        "actual_real_provider_calls": 0,
        "fallback_success_counts_toward_primary_openai": False,
        "credential_missing_skip_counts_toward_real_provider_accepted_rate": False,
        "adapter_not_implemented_skip_counts_toward_real_provider_accepted_rate": False,
        "status": "passed",
    }


def _credential_facts(*, allow_local_secret_file: bool) -> dict[str, dict[str, Any]]:
    deepseek_active = deepseek_credential_status(allow_local_secret_file=allow_local_secret_file)
    deepseek_any = deepseek_credential_status(allow_local_secret_file=True)
    non_active_sources: list[str] = []
    if (
        not allow_local_secret_file
        and deepseek_active["credential_status"] == "missing"
        and deepseek_any["credential_status"] == "present"
    ):
        non_active_sources.append(deepseek_any["credential_source"])
    openai_status = openai_credential_status()
    anthropic_status = _anthropic_credential_status()
    return {
        "deepseek": {
            "credential_status": deepseek_active["credential_status"],
            "credential_source": deepseek_active["credential_source"],
            "non_active_credential_sources": non_active_sources,
        },
        "openai": {
            "credential_status": openai_status["credential_status"],
            "credential_source": openai_status["credential_source"],
            "non_active_credential_sources": [],
        },
        "anthropic_claude": {
            "credential_status": anthropic_status["credential_status"],
            "credential_source": anthropic_status["credential_source"],
            "non_active_credential_sources": [],
        },
    }


def _anthropic_credential_status() -> dict[str, str]:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return {"credential_status": "present", "credential_source": "environment:ANTHROPIC_API_KEY"}
    if os.environ.get("CLAUDE_API_KEY"):
        return {"credential_status": "present", "credential_source": "environment:CLAUDE_API_KEY"}
    return {"credential_status": "missing", "credential_source": "none"}


def _structured_skips(
    *,
    credential_status_by_provider: dict[str, str],
    adapter_status_by_provider: dict[str, str],
) -> list[dict[str, Any]]:
    skips: list[dict[str, Any]] = []
    if credential_status_by_provider.get("deepseek") == "missing":
        skips.append(
            _skip(
                provider_id="deepseek",
                skip_type="credential_missing_skip",
                credential_status="missing",
                adapter_status=adapter_status_by_provider["deepseek"],
                skip_reason="DeepSeek primary provider has no active credential under the Stage 3A credential policy.",
                affected_matrix_cells=["deepseek_primary_stage3a_smoke", "deepseek_primary_stage3b_agent_runs"],
                affects_core_acceptance=True,
                affects_resume_ready_acceptance=True,
            )
        )
    if credential_status_by_provider.get("openai") == "missing":
        skips.append(
            _skip(
                provider_id="openai",
                skip_type="credential_missing_skip",
                credential_status="missing",
                adapter_status=adapter_status_by_provider["openai"],
                skip_reason="OpenAI fallback smoke has no active environment credential.",
                affected_matrix_cells=["openai_fallback_stage3a_smoke"],
                affects_core_acceptance=False,
                affects_resume_ready_acceptance=True,
            )
        )
    skips.append(
        _skip(
            provider_id="openai",
            skip_type="primary_provider_comparison_not_enabled_skip",
            credential_status=credential_status_by_provider.get("openai", "missing"),
            adapter_status=adapter_status_by_provider["openai"],
            skip_reason="OpenAI is still limited to DeepSeek fallback smoke and cannot count as a primary provider comparison family.",
            affected_matrix_cells=["openai_primary_provider_comparison_cells"],
            affects_core_acceptance=False,
            affects_resume_ready_acceptance=True,
        )
    )
    skips.append(
        _skip(
            provider_id="anthropic_claude",
            skip_type="adapter_not_implemented_skip",
            credential_status=credential_status_by_provider.get("anthropic_claude", "missing"),
            adapter_status=adapter_status_by_provider["anthropic_claude"],
            skip_reason="Anthropic Claude provider adapter is not implemented in the current codebase.",
            affected_matrix_cells=["anthropic_claude_primary_stage3a_smoke", "anthropic_claude_provider_comparison_cells"],
            affects_core_acceptance=False,
            affects_resume_ready_acceptance=True,
        )
    )
    return skips


def _skip(
    *,
    provider_id: str,
    skip_type: str,
    credential_status: str,
    adapter_status: str,
    skip_reason: str,
    affected_matrix_cells: list[str],
    affects_core_acceptance: bool,
    affects_resume_ready_acceptance: bool,
) -> dict[str, Any]:
    return {
        "provider_id": provider_id,
        "skip_type": skip_type,
        "credential_status": credential_status,
        "adapter_status": adapter_status,
        "skip_reason": skip_reason,
        "affected_matrix_cells": affected_matrix_cells,
        "affects_core_acceptance": affects_core_acceptance,
        "affects_resume_ready_acceptance": affects_resume_ready_acceptance,
        "counts_toward_real_provider_accepted_rate": False,
        "counts_toward_primary_accepted_rate": False,
    }


def _provider_smoke_payload(*, credential_facts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    statuses: list[dict[str, Any]] = []
    deepseek_status = credential_facts["deepseek"]["credential_status"]
    statuses.append(
        {
            "provider_id": "deepseek",
            "provider_mode": "primary",
            "raw_smoke_status": "not_executed" if deepseek_status == "present" else "skipped_no_credentials",
            "normalized_smoke_status": "ready_for_stage3b_primary_smoke" if deepseek_status == "present" else "credential_missing_skip",
            "credential_status": deepseek_status,
            "adapter_status": "primary_supported",
            "provider_api_called": False,
            "counts_toward_real_provider_accepted_rate": False,
        }
    )
    openai_status = credential_facts["openai"]["credential_status"]
    statuses.append(
        {
            "provider_id": "openai",
            "provider_mode": "fallback_only",
            "raw_smoke_status": "not_executed" if openai_status == "present" else "skipped_no_credentials",
            "normalized_smoke_status": "ready_for_stage3b_fallback_smoke" if openai_status == "present" else "credential_missing_skip",
            "credential_status": openai_status,
            "adapter_status": "fallback_only",
            "provider_api_called": False,
            "counts_toward_real_provider_accepted_rate": False,
            "counts_toward_primary_openai_provider_family": False,
        }
    )
    statuses.append(
        {
            "provider_id": "anthropic_claude",
            "provider_mode": "primary",
            "raw_smoke_status": "adapter_not_implemented",
            "normalized_smoke_status": "adapter_not_implemented_skip",
            "credential_status": credential_facts["anthropic_claude"]["credential_status"],
            "adapter_status": "adapter_not_implemented",
            "provider_api_called": False,
            "counts_toward_real_provider_accepted_rate": False,
        }
    )
    return {
        "schema_version": V5_PROVIDER_SMOKE_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3a_provider_gate",
        "smoke_execution_mode": V5_STAGE3A_SMOKE_MODE,
        "provider_api_called": False,
        "actual_real_provider_calls": 0,
        "provider_smoke_statuses": statuses,
        "accepted_with_credentials_count": 0,
        "fallback_success_count": 0,
        "provider_error_count": 0,
        "credential_missing_skip_count": sum(1 for item in statuses if item["normalized_smoke_status"] == "credential_missing_skip"),
        "adapter_not_implemented_skip_count": sum(1 for item in statuses if item["normalized_smoke_status"] == "adapter_not_implemented_skip"),
        "raw_secret_value_present": False,
        "raw_provider_request_response_written": False,
        "status": "passed",
    }


def _raw_content_redaction_payload() -> dict[str, Any]:
    return {
        "schema_version": V5_PROVIDER_RAW_CONTENT_REDACTION_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3a_provider_gate",
        "provider_api_called": False,
        "raw_request_artifact_count": 0,
        "raw_response_artifact_count": 0,
        "raw_request_model_visible_count": 0,
        "raw_response_model_visible_count": 0,
        "raw_request_trainable_count": 0,
        "raw_response_trainable_count": 0,
        "raw_request_public_safe_count": 0,
        "raw_response_public_safe_count": 0,
        "provider_raw_content_policy": V5_PROVIDER_RAW_CONTENT_POLICY,
        "authorization_marker_count": 0,
        "provider_credential_marker_count": 0,
        "status": "passed",
    }


def _status_normalization_payload() -> dict[str, Any]:
    return {
        "schema_version": V5_PROVIDER_STATUS_NORMALIZATION_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3a_provider_gate",
        "normalization_rules": [
            {
                "raw_status": "accepted_with_credentials",
                "normalized_provider_status": "primary_attempted",
                "counts_toward_primary_accepted_rate": True,
                "required_conditions": "actual_provider equals requested_provider and final verifier accepted",
            },
            {
                "raw_status": "fallback_success",
                "normalized_provider_status": "fallback_success",
                "counts_toward_primary_accepted_rate": False,
                "required_conditions": "actual_provider is fallback provider; never counted as primary OpenAI accepted run",
            },
            {
                "raw_status": "skipped_no_credentials",
                "normalized_provider_status": "credential_missing_skip",
                "counts_toward_primary_accepted_rate": False,
                "required_conditions": "active credential source is missing",
            },
            {
                "raw_status": "adapter_not_implemented",
                "normalized_provider_status": "adapter_not_implemented_skip",
                "counts_toward_primary_accepted_rate": False,
                "required_conditions": "adapter is absent from the current codebase",
            },
            {
                "raw_status": "budget_exhausted_before_run",
                "normalized_provider_status": "cost_limited_structured_skip",
                "counts_toward_primary_accepted_rate": False,
                "required_conditions": "cost budget gate stops the call before provider invocation",
            },
            {
                "raw_status": "provider_error",
                "normalized_provider_status": "provider_error",
                "counts_toward_primary_accepted_rate": False,
                "required_conditions": "provider call was attempted and returned a structured provider error",
            },
        ],
        "legacy_statuses_allowed_only_in_audit_fields": ["skipped_no_credentials"],
        "fallback_success_counts_as_primary_openai_run": False,
        "credential_missing_skip_counts_as_real_provider_run": False,
        "adapter_not_implemented_skip_counts_as_real_provider_run": False,
        "status": "passed",
    }


def _require_stage2b_inventory_gate(task_set: dict[str, Any]) -> None:
    if task_set.get("schema_version") is None:
        raise ConfigError("task set manifest 缺少 schema_version。")
    if task_set.get("strict_inventory_gate") != "passed":
        raise ConfigError("Stage 3A provider gate 只能绑定 strict_inventory_gate=passed 的 V5 task set。")
    if int(task_set.get("accepted_auditable_task_count", 0)) < 12:
        raise ConfigError("Stage 3A provider gate 需要至少 12 个 accepted / auditable task definitions。")
    if int(task_set.get("pr_issue_task_count", 0)) < 8:
        raise ConfigError("Stage 3A provider gate 需要至少 8 个 PR / issue tasks。")
    if int(task_set.get("swebench_like_anchor_count", 0)) < 3:
        raise ConfigError("Stage 3A provider gate 需要至少 3 个 SWE-Bench-like anchor tasks。")


def _require_provider_gate_shape(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != V5_PROVIDER_CREDENTIAL_GATE_REPORT_VERSION:
        raise ConfigError("provider gate report schema_version 不匹配。")
    if payload.get("status") != "passed":
        raise ConfigError("provider gate report status 必须为 passed。")
    if payload.get("raw_secret_value_present") is not False:
        raise ConfigError("provider gate report 不能包含 raw secret value。")


def _payload_contains_raw_secret_value(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    lowered = text.lower()
    return bool(_RAW_SECRET_RE.search(text)) or "authorization: bearer" in lowered


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"输入文件不存在：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} 不是合法 JSON：{exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"{path} 顶层必须是 JSON object。")
    return payload


def _refuse_existing_outputs(root: Path, names: tuple[str, ...], fail_if_output_exists: bool) -> None:
    if not fail_if_output_exists:
        return
    existing = [root / name for name in names if (root / name).exists()]
    if existing:
        joined = ", ".join(path.as_posix() for path in existing)
        raise ConfigError(f"V5 Stage 3A 输出已存在，不能覆盖旧 evidence：{joined}")


__all__ = [
    "V5_STAGE3A_COST_BUDGET_OUTPUT_NAMES",
    "V5_STAGE3A_PROVIDER_GATE_OUTPUT_NAMES",
    "build_provider_cost_budget_report",
    "build_provider_gate_report",
]
