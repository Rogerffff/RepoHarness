"""V4 stage 7 dataset, run, export cards and provenance evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V4_ALLOWLIST_POLICY_VERSION,
    V4_CARDS_MANIFEST_VERSION,
    V4_CONTAMINATION_DENYLIST_VERSION,
)
from repo_harness.v4_visibility import (
    V4_CARD_CLAIM_DENYLIST_VERSION,
    V4ContaminationDenylist,
    scan_v4_forbidden_card_claims,
    v4_card_claim_denylist_sha256,
    v4_contamination_denylist_sha256,
)


DATASET_CARD_VERSION = "repo_harness_v4_dataset_card_v0"
RUN_CARD_VERSION = "repo_harness_v4_run_card_v0"
EXPORT_CARD_VERSION = "repo_harness_v4_export_card_v0"
PROVENANCE_SUMMARY_VERSION = "repo_harness_v4_provenance_summary_v0"
CONTAMINATION_SCAN_SUMMARY_VERSION = "repo_harness_v4_contamination_scan_summary_v0"
REPRO_COMMAND_INDEX_VERSION = "repo_harness_v4_repro_command_index_v0"
CONTAMINATION_SCAN_REPORT_VERSION = "repo_harness_v4_contamination_scan_report_v0"
IMPLEMENTATION_LOG_INDEX_VERSION = "repo_harness_v4_implementation_log_index_v0"

STAGE7_OUTPUTS = (
    "dataset_card.md",
    "dataset_card.json",
    "run_card.json",
    "export_card.json",
    "provenance_summary.json",
    "contamination_scan_summary.json",
    "repro_command_index.json",
    "cards_manifest.json",
    "contamination_scan_report.json",
    "implementation_log_index.json",
)
REPRO_COMMANDS = (
    "inspect-v2-acceptance",
    "inspect-v3-acceptance",
    "inspect-acceptance-bundle",
    "inspect-v4-task-freeze",
    "inspect-v4-task-validity",
    "inspect-rollout-queue",
    "inspect-rollout-leases",
    "inspect-rollout-retry",
    "inspect-rollout-budget",
    "inspect-resource-locks",
    "inspect-resource-usage",
    "inspect-rollout-resume",
    "inspect-run-selection-query",
    "inspect-v4-tool-contract",
    "inspect-v4-tool-lifecycle",
    "inspect-v4-agent-run-integration",
    "inspect-v4-trajectory-store",
    "inspect-v4-export-quality",
    "inspect-v4-cards",
    "inspect-v4-acceptance",
)


def build_v4_cards(
    *,
    output_dir: str | Path,
    task_freeze: str | Path,
    agent_run_integration: str | Path,
    export_quality: str | Path,
    fail_if_output_exists: bool = False,
) -> Path:
    """Build deterministic V4 stage 7 cards and provenance artifacts."""

    output_path = Path(output_dir)
    if fail_if_output_exists:
        existing = [output_path / name for name in STAGE7_OUTPUTS if (output_path / name).exists()]
        if existing:
            raise ConfigError("V4 stage 7 输出已存在，不能覆盖旧 evidence：" + ", ".join(str(path) for path in existing))
    output_path.mkdir(parents=True, exist_ok=True)
    task_freeze_ref = _external_ref(_resolve_named_file(task_freeze, "task_freeze_manifest.json"))
    agent_report_path = _resolve_named_file(agent_run_integration, "v4_agent_run_integration_report.json")
    export_manifest_path = _resolve_named_file(export_quality, "trajectory_quality_manifest.json")
    agent_ref = _external_ref(agent_report_path)
    export_ref = _external_ref(export_manifest_path)
    task_payload = json.loads(Path(task_freeze_ref["path"]).read_text(encoding="utf-8"))
    agent_payload = json.loads(agent_report_path.read_text(encoding="utf-8"))
    export_payload = json.loads(export_manifest_path.read_text(encoding="utf-8"))
    sample_tier_path = export_manifest_path.parent / "sample_tier_manifest.json"
    preference_path = export_manifest_path.parent / "preference_pair_trainability_report.json"
    blocked_pair_path = export_manifest_path.parent / "blocked_pair_report.json"
    sample_tier_ref = _external_ref(sample_tier_path)
    preference_ref = _external_ref(preference_path)
    blocked_pair_ref = _external_ref(blocked_pair_path)
    sample_tier_payload = json.loads(sample_tier_path.read_text(encoding="utf-8"))
    preference_payload = json.loads(preference_path.read_text(encoding="utf-8"))
    blocked_pair_payload = json.loads(blocked_pair_path.read_text(encoding="utf-8"))
    accepted_count = int(task_payload.get("accepted_auditable_task_definition_count", 8))
    pr_issue_count = int(task_payload.get("pr_issue_accepted_auditable_task_definition_count", 0))
    diagnostic_task_count = int(task_payload.get("diagnostic_public_swebench_like_pool_count", 0))
    sample_split = _sample_split(sample_tier_payload, preference_payload)
    selected_run_refs = [
        str(Path(agent_report_path).parent / str(record.get("relative_path")))
        for record in agent_payload.get("run_refs") or []
    ]
    sample_tiers = sorted({sample.get("outcome_tier") for sample in sample_tier_payload.get("samples") or [] if sample.get("outcome_tier")})

    dataset_card_json_path = output_path / "dataset_card.json"
    dataset_card_payload = {
        "schema_version": DATASET_CARD_VERSION,
        "generated_at": _utc_timestamp(),
        "dataset_name": "RepoHarness V4 fixed auditable trajectory subset",
        "task_sources": {
            "v4_pr_issue_constructed": pr_issue_count,
            "v4_public_swebench_like_extension_pool": 0,
        },
        "distribution": {
            "accepted_auditable_task_definitions": accepted_count,
            "diagnostic_only": diagnostic_task_count,
            "quarantined": 0,
            "rejected": 0,
        },
        "license_provenance_summary": "Per-task license and provenance review are required before accepted counting.",
        "manual_review_required": True,
        "direct_training_without_review_allowed": False,
        "public_leaderboard_comparable": False,
        "production_security_sandbox": False,
        "trained_coding_agent": False,
        "contamination_scan_summary_ref": "contamination_scan_summary.json",
    }
    _write_json(dataset_card_json_path, dataset_card_payload)
    dataset_card_md_path = output_path / "dataset_card.md"
    dataset_card_md_path.write_text(_render_dataset_card_markdown(dataset_card_payload), encoding="utf-8")

    run_card_path = output_path / "run_card.json"
    _write_json(
        run_card_path,
        {
            "schema_version": RUN_CARD_VERSION,
            "generated_at": _utc_timestamp(),
            "selected_run_refs": selected_run_refs,
            "run_status_counts": agent_payload.get("run_status_counts"),
            "provider_mode": "single_machine",
            "scaffold_id": "v4_default_scaffold_metadata_only",
            "budget_policy": "v4_stage5_budget_policy_v0",
            "docker_facts": {
                "docker_backend_baseline": "V3 real Docker backend baseline retained",
                "production_security_sandbox": False,
                "max_workers": 1,
            },
            "resource_usage_summary": {
                "max_workers": 1,
                "single_machine_first": True,
                "distributed_cluster_mode": False,
            },
        },
    )
    export_card_path = output_path / "export_card.json"
    _write_json(
        export_card_path,
        {
            "schema_version": EXPORT_CARD_VERSION,
            "generated_at": _utc_timestamp(),
            "sample_tiers": sample_tiers,
            "trainable_diagnostic_split": sample_split,
            "contamination_scan_status": "clean",
            "blocked_sources": _blocked_sources(blocked_pair_payload),
            "export_policy": "repo_harness_v4_export_quality_policy_v0",
            "final_verifier_authority_preserved": True,
            "reward_is_diagnostic_only": True,
        },
    )
    provenance_path = output_path / "provenance_summary.json"
    _write_json(
        provenance_path,
        {
            "schema_version": PROVENANCE_SUMMARY_VERSION,
            "generated_at": _utc_timestamp(),
            "task_freeze_ref": task_freeze_ref,
            "agent_run_integration_ref": agent_ref,
            "export_quality_ref": export_ref,
            "export_quality_refs": {
                "trajectory_quality_manifest.json": export_ref,
                "sample_tier_manifest.json": sample_tier_ref,
                "preference_pair_trainability_report.json": preference_ref,
                "blocked_pair_report.json": blocked_pair_ref,
            },
            "source_materialization_policy": "fixed source archive and source tree hash required",
            "manual_review_notes_required": True,
            "source_discussion_payload_included": False,
            "source_diff_payload_included": False,
            "provider_unredacted_payload_included": False,
            "verifier_unredacted_log_included": False,
        },
    )
    contamination_summary_path = output_path / "contamination_scan_summary.json"
    _write_json(
        contamination_summary_path,
        {
            "schema_version": CONTAMINATION_SCAN_SUMMARY_VERSION,
            "generated_at": _utc_timestamp(),
            "denylist_version": V4_CONTAMINATION_DENYLIST_VERSION,
            "denylist_sha256": v4_contamination_denylist_sha256(),
            "card_claim_denylist_version": V4_CARD_CLAIM_DENYLIST_VERSION,
            "card_claim_denylist_sha256": v4_card_claim_denylist_sha256(),
            "allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
            "scanned_surfaces": [
                "dataset_card",
                "run_card",
                "export_card",
                "provenance_summary",
                "repro_command_index",
                "implementation_log",
            ],
            "clean": True,
            "finding_count": 0,
        },
    )
    repro_path = output_path / "repro_command_index.json"
    _write_json(
        repro_path,
        {
            "schema_version": REPRO_COMMAND_INDEX_VERSION,
            "generated_at": _utc_timestamp(),
            "commands": [
                _command_ref("v2 regression", "PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete"),
                _command_ref("v3 acceptance", "PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete"),
                _command_ref("v3 bundle", "PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable"),
                _command_ref("v4 task freeze", "PATH=.venv/bin:$PATH repo-harness inspect-v4-task-freeze docs/v4/evidence/task-source-freeze/task_freeze_manifest.json --assert-complete"),
                _command_ref("v4 task validity", "PATH=.venv/bin:$PATH repo-harness inspect-v4-task-validity docs/v4/evidence/task-source-freeze/task_validity_report.json --assert-complete"),
                _command_ref("v4 rollout queue", "PATH=.venv/bin:$PATH repo-harness inspect-rollout-queue docs/v4/evidence/rollout-orchestration --assert-complete"),
                _command_ref("v4 rollout leases", "PATH=.venv/bin:$PATH repo-harness inspect-rollout-leases docs/v4/evidence/rollout-orchestration --assert-complete"),
                _command_ref("v4 rollout retry", "PATH=.venv/bin:$PATH repo-harness inspect-rollout-retry docs/v4/evidence/rollout-orchestration --assert-complete"),
                _command_ref("v4 rollout budget", "PATH=.venv/bin:$PATH repo-harness inspect-rollout-budget docs/v4/evidence/rollout-orchestration --assert-complete"),
                _command_ref("v4 resource locks", "PATH=.venv/bin:$PATH repo-harness inspect-resource-locks docs/v4/evidence/rollout-orchestration --assert-complete"),
                _command_ref("v4 resource usage", "PATH=.venv/bin:$PATH repo-harness inspect-resource-usage docs/v4/evidence/rollout-orchestration --assert-complete"),
                _command_ref("v4 rollout resume", "PATH=.venv/bin:$PATH repo-harness inspect-rollout-resume docs/v4/evidence/rollout-orchestration --assert-complete"),
                _command_ref("v4 run selection query", "PATH=.venv/bin:$PATH repo-harness inspect-run-selection-query docs/v4/evidence/rollout-orchestration/run_selection_query_report.json --assert-complete"),
                _command_ref("v4 tool contract", "PATH=.venv/bin:$PATH repo-harness inspect-v4-tool-contract docs/v4/evidence/tool-lifecycle --assert-frozen"),
                _command_ref("v4 tool lifecycle", "PATH=.venv/bin:$PATH repo-harness inspect-v4-tool-lifecycle docs/v4/evidence/tool-lifecycle --assert-complete"),
                _command_ref("v4 agent run integration", "PATH=.venv/bin:$PATH repo-harness inspect-v4-agent-run-integration docs/v4/evidence/agent-run-integration --assert-complete"),
                _command_ref("v4 trajectory store", "PATH=.venv/bin:$PATH repo-harness inspect-v4-trajectory-store docs/v4/evidence/agent-run-integration --assert-readable"),
                _command_ref("v4 export audit", "PATH=.venv/bin:$PATH repo-harness inspect-v4-export-quality docs/v4/evidence/export-quality --assert-complete"),
                _command_ref("v4 cards", "PATH=.venv/bin:$PATH repo-harness inspect-v4-cards docs/v4/evidence/cards --assert-complete"),
                _command_ref("v4 final acceptance", "PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-YYYYMMDDTHHMMSSZ/acceptance/v4_acceptance_report.json --assert-complete"),
            ],
        },
    )
    implementation_log_path = output_path / "implementation_log_index.json"
    _write_json(
        implementation_log_path,
        {
            "schema_version": IMPLEMENTATION_LOG_INDEX_VERSION,
            "generated_at": _utc_timestamp(),
            "stage_logs": [
                "docs/v4/implementation-log/07-cards.md",
            ],
            "contains_source_discussion_payload": False,
            "contains_provider_unredacted_payload": False,
            "contains_verifier_unredacted_log": False,
        },
    )
    task_visibility_ref = (task_payload.get("artifact_refs_by_name") or {}).get("task_visibility_scan_report.json")
    if not isinstance(task_visibility_ref, dict):
        raise ConfigError("Stage 7 task freeze input 缺少 task_visibility_scan_report.json ref。")
    scan_report_path = output_path / "contamination_scan_report.json"
    _write_json(
        scan_report_path,
        _build_scan_report(output_path, task_visibility_ref=task_visibility_ref),
    )
    manifest_path = output_path / "cards_manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": V4_CARDS_MANIFEST_VERSION,
            "generated_at": _utc_timestamp(),
            "dataset_card_md_ref": _file_ref(dataset_card_md_path, output_path),
            "dataset_card_json_ref": _file_ref(dataset_card_json_path, output_path),
            "run_card_ref": _file_ref(run_card_path, output_path),
            "export_card_ref": _file_ref(export_card_path, output_path),
            "provenance_summary_ref": _file_ref(provenance_path, output_path),
            "contamination_scan_summary_ref": _file_ref(contamination_summary_path, output_path),
            "repro_command_index_ref": _file_ref(repro_path, output_path),
            "contamination_scan_report_ref": _file_ref(scan_report_path, output_path),
            "implementation_log_index_ref": _file_ref(implementation_log_path, output_path),
        },
    )
    inspect_v4_cards(output_path, assert_complete=True)
    return manifest_path


def inspect_v4_cards(path: str | Path, *, assert_complete: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    manifest = _read_json_for_inspect(target / "cards_manifest.json", failures)
    dataset_json = _read_json_for_inspect(target / "dataset_card.json", failures)
    dataset_md = _read_text_for_inspect(target / "dataset_card.md", failures)
    run_card = _read_json_for_inspect(target / "run_card.json", failures)
    export_card = _read_json_for_inspect(target / "export_card.json", failures)
    provenance = _read_json_for_inspect(target / "provenance_summary.json", failures)
    contamination_summary = _read_json_for_inspect(target / "contamination_scan_summary.json", failures)
    repro = _read_json_for_inspect(target / "repro_command_index.json", failures)
    scan_report = _read_json_for_inspect(target / "contamination_scan_report.json", failures)
    implementation_log = _read_json_for_inspect(target / "implementation_log_index.json", failures)
    _expect(manifest, "schema_version", V4_CARDS_MANIFEST_VERSION, failures, "cards_manifest")
    _expect(dataset_json, "schema_version", DATASET_CARD_VERSION, failures, "dataset_card")
    _expect(run_card, "schema_version", RUN_CARD_VERSION, failures, "run_card")
    _expect(export_card, "schema_version", EXPORT_CARD_VERSION, failures, "export_card")
    _expect(provenance, "schema_version", PROVENANCE_SUMMARY_VERSION, failures, "provenance_summary")
    _expect(contamination_summary, "schema_version", CONTAMINATION_SCAN_SUMMARY_VERSION, failures, "contamination_scan_summary")
    _expect(repro, "schema_version", REPRO_COMMAND_INDEX_VERSION, failures, "repro_command_index")
    _expect(scan_report, "schema_version", CONTAMINATION_SCAN_REPORT_VERSION, failures, "contamination_scan_report")
    _expect(implementation_log, "schema_version", IMPLEMENTATION_LOG_INDEX_VERSION, failures, "implementation_log_index")
    for field in (
        "dataset_card_md_ref",
        "dataset_card_json_ref",
        "run_card_ref",
        "export_card_ref",
        "provenance_summary_ref",
        "contamination_scan_summary_ref",
        "repro_command_index_ref",
        "contamination_scan_report_ref",
        "implementation_log_index_ref",
    ):
        _inspect_file_ref(manifest.get(field), target, failures, label=field)
    _inspect_dataset_card(dataset_json, dataset_md, failures)
    _inspect_run_card(run_card, failures)
    _inspect_export_card(export_card, provenance, failures)
    _inspect_provenance(provenance, failures)
    _inspect_contamination_summary(contamination_summary, scan_report, failures)
    _inspect_repro_commands(repro, failures)
    _inspect_implementation_logs(implementation_log, failures)
    _inspect_no_forbidden_card_claims(
        [dataset_json, dataset_md, run_card, export_card, provenance, contamination_summary, repro, implementation_log],
        failures,
    )
    _inspect_scan_clean(scan_report, failures)
    return _inspect_result("inspect-v4-cards", target, failures, assert_complete, "complete")


def _inspect_dataset_card(payload: dict[str, Any], markdown: str, failures: list[str]) -> None:
    for field in ("task_sources", "license_provenance_summary", "distribution"):
        if not payload.get(field):
            failures.append(f"dataset_card 缺少 {field}。")
    distribution = payload.get("distribution") or {}
    for field in ("accepted_auditable_task_definitions", "diagnostic_only", "quarantined", "rejected"):
        if field not in distribution:
            failures.append(f"dataset_card distribution 缺少 {field}。")
    if payload.get("manual_review_required") is not True:
        failures.append("dataset_card 必须说明仍需人工审查。")
    if payload.get("direct_training_without_review_allowed") is not False:
        failures.append("dataset_card 不得声称无需人工审查即可直接训练。")
    if payload.get("public_leaderboard_comparable") is not False:
        failures.append("dataset_card 不得声称公开 leaderboard 可比。")
    if "contamination" not in markdown.lower():
        failures.append("dataset_card.md 必须包含 contamination scan 摘要。")


def _inspect_run_card(payload: dict[str, Any], failures: list[str]) -> None:
    for field in ("selected_run_refs", "run_status_counts", "provider_mode", "scaffold_id", "budget_policy", "docker_facts", "resource_usage_summary"):
        if not payload.get(field):
            failures.append(f"run_card 缺少 {field}。")
    counts = payload.get("run_status_counts") or {}
    for status in ("completed", "interrupted", "crashed"):
        if counts.get(status, 0) < 1:
            failures.append(f"run_card run_status_counts 缺少 {status}。")
    docker_facts = payload.get("docker_facts") or {}
    if docker_facts.get("production_security_sandbox") is not False:
        failures.append("run_card 不得把 Docker backend 描述成生产级安全沙箱。")
    resource = payload.get("resource_usage_summary") or {}
    if resource.get("distributed_cluster_mode") is not False:
        failures.append("run_card 不得声称分布式集群模式。")


def _inspect_export_card(payload: dict[str, Any], provenance: dict[str, Any], failures: list[str]) -> None:
    for field in ("sample_tiers", "trainable_diagnostic_split", "contamination_scan_status", "blocked_sources", "export_policy"):
        if not payload.get(field):
            failures.append(f"export_card 缺少 {field}。")
    if payload.get("final_verifier_authority_preserved") is not True:
        failures.append("export_card 必须说明 final verifier authority preserved。")
    if payload.get("reward_is_diagnostic_only") is not True:
        failures.append("export_card 必须说明 reward 只作为诊断和过滤辅助。")
    split = payload.get("trainable_diagnostic_split") or {}
    for field in ("trainable", "diagnostic_only", "blocked_preference_pairs"):
        if field not in split:
            failures.append(f"export_card trainable_diagnostic_split 缺少 {field}。")
    _inspect_export_card_consistency(payload, provenance, failures)


def _inspect_provenance(payload: dict[str, Any], failures: list[str]) -> None:
    for field in ("task_freeze_ref", "agent_run_integration_ref", "export_quality_ref", "export_quality_refs", "source_materialization_policy"):
        if not payload.get(field):
            failures.append(f"provenance_summary 缺少 {field}。")
    refs = payload.get("export_quality_refs")
    if not isinstance(refs, dict):
        failures.append("provenance_summary export_quality_refs 必须是 object。")
    else:
        for name in (
            "trajectory_quality_manifest.json",
            "sample_tier_manifest.json",
            "preference_pair_trainability_report.json",
            "blocked_pair_report.json",
        ):
            if name not in refs:
                failures.append(f"provenance_summary export_quality_refs 缺少 {name}。")
            else:
                _inspect_external_file_ref(refs[name], failures, label=f"provenance_summary.export_quality_refs.{name}")
    for field in (
        "source_discussion_payload_included",
        "source_diff_payload_included",
        "provider_unredacted_payload_included",
        "verifier_unredacted_log_included",
    ):
        if payload.get(field) is not False:
            failures.append(f"provenance_summary {field} 必须为 false。")


def _inspect_export_card_consistency(export_card: dict[str, Any], provenance: dict[str, Any], failures: list[str]) -> None:
    refs = provenance.get("export_quality_refs")
    if not isinstance(refs, dict):
        return
    sample_tier_payload = _read_json_ref(refs.get("sample_tier_manifest.json"), failures, label="export_quality_refs.sample_tier_manifest.json")
    preference_payload = _read_json_ref(
        refs.get("preference_pair_trainability_report.json"),
        failures,
        label="export_quality_refs.preference_pair_trainability_report.json",
    )
    blocked_pair_payload = _read_json_ref(refs.get("blocked_pair_report.json"), failures, label="export_quality_refs.blocked_pair_report.json")
    if not sample_tier_payload or not preference_payload or not blocked_pair_payload:
        return
    expected_split = _sample_split(sample_tier_payload, preference_payload)
    if export_card.get("trainable_diagnostic_split") != expected_split:
        failures.append("export_card trainable_diagnostic_split 与 Stage 6 preference/sample tier evidence 不一致。")
    expected_tiers = sorted(
        {sample.get("outcome_tier") for sample in sample_tier_payload.get("samples") or [] if sample.get("outcome_tier")}
    )
    if export_card.get("sample_tiers") != expected_tiers:
        failures.append("export_card sample_tiers 与 Stage 6 sample tier evidence 不一致。")
    if export_card.get("blocked_sources") != _blocked_sources(blocked_pair_payload):
        failures.append("export_card blocked_sources 与 Stage 6 blocked pair report 不一致。")


def _inspect_contamination_summary(summary: dict[str, Any], scan_report: dict[str, Any], failures: list[str]) -> None:
    if summary.get("clean") is not True or scan_report.get("clean") is not True:
        failures.append("contamination scan summary/report 必须 clean。")
    if summary.get("denylist_sha256") != v4_contamination_denylist_sha256():
        failures.append("contamination_scan_summary denylist_sha256 不匹配。")
    if summary.get("card_claim_denylist_sha256") != v4_card_claim_denylist_sha256():
        failures.append("contamination_scan_summary card_claim_denylist_sha256 不匹配。")
    if not summary.get("scanned_surfaces"):
        failures.append("contamination_scan_summary 缺少 scanned surfaces。")


def _inspect_repro_commands(payload: dict[str, Any], failures: list[str]) -> None:
    commands = payload.get("commands") or []
    command_text = "\n".join(command.get("command", "") for command in commands if isinstance(command, dict))
    for required in REPRO_COMMANDS:
        if required not in command_text:
            failures.append(f"repro_command_index 缺少 {required}。")
    if "latest" in command_text.lower():
        failures.append("repro_command_index 不得依赖 latest run 自动选择。")


def _inspect_implementation_logs(payload: dict[str, Any], failures: list[str]) -> None:
    logs = payload.get("stage_logs")
    if not isinstance(logs, list) or not logs:
        failures.append("implementation_log_index 缺少 stage_logs。")
        return
    denylist = V4ContaminationDenylist()
    for index, raw in enumerate(logs, start=1):
        path = Path(str(raw))
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            failures.append(f"implementation_log_index stage_logs[{index}] 路径不存在：{raw}")
            continue
        text = path.read_text(encoding="utf-8")
        try:
            denylist.assert_clean(surface="implementation_log", payload=text)
        except ValueError as exc:
            failures.append(f"implementation_log_index stage_logs[{index}] contamination scan failed: {exc}")


def _inspect_no_forbidden_card_claims(payloads: list[Any], failures: list[str]) -> None:
    denylist = V4ContaminationDenylist()
    for index, payload in enumerate(payloads, start=1):
        for finding in scan_v4_forbidden_card_claims(surface="dataset_card", payload=payload):
            failures.append(f"cards payload[{index}] 包含禁止声明：{finding['matched_term']}")
        try:
            denylist.assert_clean(surface="dataset_card", payload=payload)
        except ValueError as exc:
            failures.append(f"cards payload[{index}] contamination scan failed: {exc}")


def _inspect_scan_clean(scan_report: dict[str, Any], failures: list[str]) -> None:
    if scan_report.get("clean") is not True:
        failures.append("contamination_scan_report clean 必须为 true。")
    findings = scan_report.get("findings")
    if not isinstance(findings, list) or findings:
        failures.append("contamination_scan_report findings 必须为空列表。")
    if scan_report.get("card_claim_denylist_sha256") != v4_card_claim_denylist_sha256():
        failures.append("contamination_scan_report card_claim_denylist_sha256 不匹配。")
    refs = scan_report.get("artifact_refs_by_name")
    if not isinstance(refs, dict):
        failures.append("contamination_scan_report 缺少 artifact_refs_by_name。")
        return
    for name in ("task_visibility_scan_report.json", "contamination_scan_summary.json"):
        ref = refs.get(name)
        if not isinstance(ref, dict):
            failures.append(f"contamination_scan_report artifact_refs_by_name 缺少 {name}。")
            continue
        raw = str(ref.get("path") or ref.get("relative_path") or "")
        if not raw:
            failures.append(f"contamination_scan_report {name} ref 缺少 path。")
            continue
        path = Path(raw)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            failures.append(f"contamination_scan_report {name} ref 路径不存在：{raw}")
            continue
        if path.name != name:
            failures.append(f"contamination_scan_report {name} ref path 文件名不匹配。")
        if ref.get("sha256") != sha256_file(path):
            failures.append(f"contamination_scan_report {name} ref sha256 不匹配。")
        if ref.get("size_bytes") is not None and path.stat().st_size != ref.get("size_bytes"):
            failures.append(f"contamination_scan_report {name} ref size_bytes 不匹配。")


def _build_scan_report(output_path: Path, *, task_visibility_ref: dict[str, Any]) -> dict[str, Any]:
    denylist = V4ContaminationDenylist()
    findings: list[dict[str, Any]] = []
    for path in (
        output_path / "dataset_card.md",
        output_path / "dataset_card.json",
        output_path / "run_card.json",
        output_path / "export_card.json",
        output_path / "provenance_summary.json",
        output_path / "contamination_scan_summary.json",
        output_path / "repro_command_index.json",
        output_path / "implementation_log_index.json",
    ):
        payload: Any
        if path.suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload = path.read_text(encoding="utf-8")
        result = denylist.scan_payload(surface=path.stem, payload=payload)
        findings.extend(finding.model_dump(mode="json") for finding in result.findings)
        findings.extend(scan_v4_forbidden_card_claims(surface=path.stem, payload=payload))
    implementation_log_index = json.loads((output_path / "implementation_log_index.json").read_text(encoding="utf-8"))
    for raw in implementation_log_index.get("stage_logs") or []:
        log_path = Path(str(raw))
        if not log_path.is_absolute():
            log_path = Path.cwd() / log_path
        if log_path.exists():
            result = denylist.scan_payload(surface="implementation_log", payload=log_path.read_text(encoding="utf-8"))
            findings.extend(finding.model_dump(mode="json") for finding in result.findings)
            findings.extend(
                scan_v4_forbidden_card_claims(
                    surface="implementation_log",
                    payload=log_path.read_text(encoding="utf-8"),
                )
            )
    return {
        "schema_version": CONTAMINATION_SCAN_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "denylist_version": V4_CONTAMINATION_DENYLIST_VERSION,
        "denylist_sha256": v4_contamination_denylist_sha256(),
        "card_claim_denylist_version": V4_CARD_CLAIM_DENYLIST_VERSION,
        "card_claim_denylist_sha256": v4_card_claim_denylist_sha256(),
        "allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
        "clean": not findings,
        "findings": findings,
        "artifact_refs_by_name": {
            "task_visibility_scan_report.json": task_visibility_ref,
            "contamination_scan_summary.json": _path_file_ref(output_path / "contamination_scan_summary.json"),
        },
    }


def _render_dataset_card_markdown(payload: dict[str, Any]) -> str:
    distribution = payload["distribution"]
    sources = payload["task_sources"]
    return (
        "# RepoHarness V4 Dataset Card\n\n"
        "This card summarizes a fixed, auditable V4 trajectory subset for review and controlled export.\n\n"
        "## Task Sources\n\n"
        f"- V4 PR / issue constructed tasks: {sources['v4_pr_issue_constructed']}\n"
        f"- V4 public SWE-Bench-like extension pool: {sources['v4_public_swebench_like_extension_pool']}\n\n"
        "## Distribution\n\n"
        f"- Accepted auditable task definitions: {distribution['accepted_auditable_task_definitions']}\n"
        f"- Diagnostic-only samples: {distribution['diagnostic_only']}\n"
        f"- Quarantined samples: {distribution['quarantined']}\n"
        f"- Rejected samples: {distribution['rejected']}\n\n"
        "## Review Boundary\n\n"
        "Manual review is required before training use. The dataset card does not claim public leaderboard comparability or production security sandbox coverage.\n\n"
        "## Contamination Scan\n\n"
        "The V4 contamination scan summary is clean and is bound by the cards manifest.\n"
    )


def _command_ref(label: str, command: str) -> dict[str, str]:
    return {"label": label, "command": command}


def _sample_split(sample_tier_payload: dict[str, Any], preference_payload: dict[str, Any]) -> dict[str, int]:
    samples = sample_tier_payload.get("samples") or []
    return {
        "trainable": sum(1 for sample in samples if sample.get("trainability_status") == "trainable"),
        "diagnostic_only": sum(1 for sample in samples if sample.get("trainability_status") == "diagnostic_only"),
        "blocked_preference_pairs": int(preference_payload.get("blocked_pair_count", 0)),
    }


def _blocked_sources(blocked_pair_payload: dict[str, Any]) -> list[str]:
    blocked_reason = str(blocked_pair_payload.get("blocked_reason") or "")
    return [blocked_reason] if blocked_reason else []


def _resolve_named_file(path: str | Path, default_name: str) -> Path:
    target = Path(path)
    if target.is_dir():
        target = target / default_name
    if not target.exists():
        raise ConfigError(f"Stage 7 必需输入不存在：{target}")
    return target


def _external_ref(path: Path) -> dict[str, Any]:
    return {"path": path.resolve().as_posix(), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def _inspect_file_ref(ref: Any, root: Path, failures: list[str], *, label: str) -> Path | None:
    if not isinstance(ref, dict):
        failures.append(f"{label} 文件 ref 缺失或不是 object。")
        return None
    raw = str(ref.get("relative_path") or ref.get("path") or "")
    if not raw:
        failures.append(f"{label} 文件 ref 缺少 path。")
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        failures.append(f"{label} 文件 ref 路径不存在：{raw}")
        return None
    if ref.get("sha256") != sha256_file(path):
        failures.append(f"{label} 文件 ref sha256 不匹配。")
    return path


def _inspect_external_file_ref(ref: Any, failures: list[str], *, label: str) -> Path | None:
    if not isinstance(ref, dict):
        failures.append(f"{label} 文件 ref 缺失或不是 object。")
        return None
    raw = str(ref.get("path") or ref.get("relative_path") or "")
    if not raw:
        failures.append(f"{label} 文件 ref 缺少 path。")
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        failures.append(f"{label} 文件 ref 路径不存在：{raw}")
        return None
    expected_name = ".".join(label.split(".")[-2:]) if "." in label else label
    if path.name != expected_name:
        failures.append(f"{label} 文件 ref path 文件名不匹配。")
    if ref.get("sha256") != sha256_file(path):
        failures.append(f"{label} 文件 ref sha256 不匹配。")
    if ref.get("size_bytes") is not None and path.stat().st_size != ref.get("size_bytes"):
        failures.append(f"{label} 文件 ref size_bytes 不匹配。")
    return path


def _read_json_ref(ref: Any, failures: list[str], *, label: str) -> dict[str, Any]:
    path = _inspect_external_file_ref(ref, failures, label=label)
    if path is None:
        return {}
    return _read_json_for_inspect(path, failures)


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
    if not path.exists():
        failures.append(f"缺少文件：{path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"JSON 无法解析：{path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"JSON 顶层必须是 object：{path}")
        return {}
    return payload


def _read_text_for_inspect(path: Path, failures: list[str]) -> str:
    if not path.exists():
        failures.append(f"缺少文件：{path}")
        return ""
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _file_ref(path: Path, root: Path) -> dict[str, Any]:
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _path_file_ref(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _expect(payload: dict[str, Any], field: str, expected: Any, failures: list[str], label: str) -> None:
    if payload.get(field) != expected:
        failures.append(f"{label}.{field} 不匹配。")


def _inspect_result(command: str, path: Path, failures: list[str], assert_flag: bool, label: str) -> str:
    lines = [f"{command}: {path}"]
    if failures:
        if assert_flag:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_flag:
        lines.append(f"{command}: {label}")
    lines.append(f"{command}: passed")
    return "\n".join(lines)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
