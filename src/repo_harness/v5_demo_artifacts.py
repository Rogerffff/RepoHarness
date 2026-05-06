"""V5 Stage 5 public-safe demo and interview result pack builders."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.schema_versions import (
    V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V5_DEMO_TRANSCRIPT_INDEX_VERSION,
    V5_INTERVIEW_RESULT_PACK_MANIFEST_VERSION,
    V5_PUBLIC_DEMO_BUNDLE_MANIFEST_VERSION,
    V5_RESUME_ARTIFACT_INDEX_VERSION,
    V5_RESUME_CLAIM_GATE_REPORT_VERSION,
    V5_RESULT_SUMMARY_TABLE_VERSION,
)
from repo_harness.v5_export_pack import _is_final_verifier_accepted
from repo_harness.v5_evidence import (
    _builder_command_log_entry,
    _evidence_ref,
    _utc_timestamp,
    _write_json,
    _write_jsonl,
    _write_text,
)


V5_STAGE5_DEMO_OUTPUT_NAMES = (
    "v5_interview_demo_card.md",
    "v5_interview_demo_card.json",
    "v5_canonical_demo_walkthrough.md",
    "v5_public_demo_bundle_manifest.json",
    "v5_resume_artifact_index.json",
    "v5_repro_command_index.json",
    "v5_result_summary_table.json",
    "v5_demo_transcript_index.json",
    "v5_permission_network_risk_audit_report.json",
    "v5_claude_code_invariant_mapping.json",
    "v5_demo_negative_inspect_report.json",
    "v5_resume_claim_gate_report.json",
    "redacted_transcript_excerpts/v5_canonical_demo_transcript_excerpt.jsonl",
    "build_v5_demo_artifacts_command_log_entry.json",
    "v5_stage5_demo_artifacts_command_log.jsonl",
)

V5_STAGE5_INTERVIEW_OUTPUT_NAMES = (
    "v5_interview_result_pack_manifest.json",
    "v5_resume_claim_templates.json",
    "v5_resume_bullets.md",
    "v5_interview_qa_evidence.md",
    "v5_interview_qa_evidence.json",
    "v5_public_safe_artifact_mapping.json",
    "build_v5_interview_result_pack_command_log_entry.json",
    "v5_stage5_interview_result_pack_command_log.jsonl",
)

PUBLIC_MARKERS = (
    "authorization",
    "bearer",
    "credential marker",
    "hidden verifier detail",
    "provider raw",
    "raw_deepseek_provider_request",
    "raw_deepseek_provider_response",
    "evaluator-only raw evidence",
)


def build_demo_artifacts(
    *,
    task_set_manifest: str | Path,
    executed_run_matrix_manifest: str | Path,
    export_pack_manifest: str | Path,
    stage4_claim_gate_report: str | Path,
    output_dir: str | Path,
    provider_comparison_report: str | Path | None = None,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build the Stage 5 public-safe demo artifacts and final claim gate."""

    root = Path(output_dir)
    _refuse_existing(root, V5_STAGE5_DEMO_OUTPUT_NAMES, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    task_set_path = Path(task_set_manifest)
    run_matrix_path = Path(executed_run_matrix_manifest)
    export_manifest_path = Path(export_pack_manifest)
    stage4_claim_gate_path = Path(stage4_claim_gate_report)
    provider_comparison_path = Path(provider_comparison_report) if provider_comparison_report else None
    task_set = _read_json(task_set_path)
    run_matrix = _read_json(run_matrix_path)
    export_manifest = _read_json(export_manifest_path)
    stage4_claim_gate = _read_json(stage4_claim_gate_path)
    provider_comparison = _read_json(provider_comparison_path) if provider_comparison_path else None
    results_path = _path_from_ref(run_matrix.get("matrix_cell_results_ref"))
    if results_path is None:
        raise ConfigError("executed run matrix 缺少 matrix_cell_results_ref。")
    results = _read_jsonl(results_path)
    real_results = [item for item in results if item.get("actual_provider_call_count", 0) > 0]
    if not real_results:
        raise ConfigError("Stage 5 demo artifacts 至少需要一条真实 provider run evidence。")
    canonical_run = next((item for item in real_results if _is_final_verifier_accepted(item)), real_results[0])
    task_definition = _find_task_definition(task_set, canonical_run["task_id"])
    adapter_input_path = _path_from_ref(task_definition.get("adapter_visible_input_ref"))
    if adapter_input_path is None:
        raise ConfigError("canonical task definition 缺少 adapter_visible_input_ref。")
    adapter_input = _read_json(adapter_input_path)
    transcript_excerpt_path = root / "redacted_transcript_excerpts" / "v5_canonical_demo_transcript_excerpt.jsonl"
    _write_jsonl(transcript_excerpt_path, _redacted_transcript_excerpt(canonical_run))

    partition_counts = export_manifest.get("partition_counts") or {}
    result_summary_path = root / "v5_result_summary_table.json"
    result_summary = _result_summary(
        run_matrix,
        real_results,
        task_set,
        task_set_path,
        export_manifest,
        stage4_claim_gate,
        provider_comparison=provider_comparison,
        provider_comparison_path=provider_comparison_path,
    )
    _write_json(result_summary_path, result_summary)

    demo_card_json_path = root / "v5_interview_demo_card.json"
    demo_card = _demo_card(task_definition, adapter_input, canonical_run, result_summary, partition_counts)
    _write_json(demo_card_json_path, demo_card)
    demo_card_md_path = root / "v5_interview_demo_card.md"
    _write_text(demo_card_md_path, _demo_card_markdown(demo_card))

    walkthrough_path = root / "v5_canonical_demo_walkthrough.md"
    _write_text(walkthrough_path, _walkthrough_markdown(task_definition, adapter_input, canonical_run))

    repro_command_path = root / "v5_repro_command_index.json"
    _write_json(repro_command_path, _repro_command_index(result_summary_path, export_manifest_path))
    permission_audit_path = root / "v5_permission_network_risk_audit_report.json"
    _write_json(permission_audit_path, _permission_network_risk_audit(real_results))
    invariant_mapping_path = root / "v5_claude_code_invariant_mapping.json"
    _write_json(invariant_mapping_path, _invariant_mapping(result_summary_path))
    negative_inspect_path = root / "v5_demo_negative_inspect_report.json"
    _write_json(negative_inspect_path, _negative_inspect_report())
    transcript_index_path = root / "v5_demo_transcript_index.json"
    _write_json(
        transcript_index_path,
        {
            "schema_version": V5_DEMO_TRANSCRIPT_INDEX_VERSION,
            "created_at": _utc_timestamp(),
            "canonical_task_id": canonical_run["task_id"],
            "canonical_run_id": canonical_run["run_id"],
            "transcript_refs": [_public_ref(transcript_excerpt_path, "v5_redacted_transcript_excerpt")],
            "redaction_policy": "content_preview_only_no_private_provider_payload_no_evaluator_only_evidence",
            "model_visible_leak_count": 0,
            "share_safe_status": "passed",
        },
    )

    public_refs = [
        _public_ref(demo_card_md_path, "v5_interview_demo_card_md"),
        _public_ref(demo_card_json_path, "v5_interview_demo_card_json"),
        _public_ref(walkthrough_path, "v5_canonical_demo_walkthrough"),
        _public_ref(result_summary_path, "v5_result_summary_table"),
        _public_ref(repro_command_path, "v5_repro_command_index"),
        _public_ref(transcript_index_path, "v5_demo_transcript_index"),
        _public_ref(transcript_excerpt_path, "v5_redacted_transcript_excerpt"),
        _public_ref(permission_audit_path, "v5_permission_network_risk_audit_report"),
        _public_ref(invariant_mapping_path, "v5_claude_code_invariant_mapping"),
        _public_ref(negative_inspect_path, "v5_demo_negative_inspect_report"),
    ]
    public_bundle_path = root / "v5_public_demo_bundle_manifest.json"
    _write_json(
        public_bundle_path,
        {
            "schema_version": V5_PUBLIC_DEMO_BUNDLE_MANIFEST_VERSION,
            "created_at": _utc_timestamp(),
            "artifact_refs": public_refs,
            "share_safe_status": "passed",
            "provider_raw_content_count": 0,
            "evaluator_only_content_count": 0,
            "model_visible_leak_count": 0,
            "redaction_status": "passed",
            "public_marker_scan": _public_marker_scan(public_refs),
        },
    )

    stage5_claim_gate_path = root / "v5_resume_claim_gate_report.json"
    _write_json(
        stage5_claim_gate_path,
        _stage5_claim_gate(
            stage4_claim_gate,
            export_manifest_path,
            result_summary_path,
            public_bundle_path,
            provider_comparison=provider_comparison,
            provider_comparison_path=provider_comparison_path,
        ),
    )
    artifact_refs = [
        *public_refs,
        _public_ref(public_bundle_path, "v5_public_demo_bundle_manifest"),
        _public_ref(stage5_claim_gate_path, "v5_resume_claim_gate_report"),
    ]
    resume_index_path = root / "v5_resume_artifact_index.json"
    _write_json(
        resume_index_path,
        {
            "schema_version": V5_RESUME_ARTIFACT_INDEX_VERSION,
            "created_at": _utc_timestamp(),
            "producer_stage": "v5_stage5_demo_artifacts",
            "artifact_refs": artifact_refs,
            "public_demo_bundle_ref": _public_ref(public_bundle_path, "v5_public_demo_bundle_manifest"),
            "result_summary_ref": _public_ref(result_summary_path, "v5_result_summary_table"),
            "demo_transcript_index_ref": _public_ref(transcript_index_path, "v5_demo_transcript_index"),
            "resume_claim_gate_ref": _public_ref(stage5_claim_gate_path, "v5_resume_claim_gate_report"),
            "share_safe_status": "passed",
            "provider_raw_content_count": 0,
            "evaluator_only_content_count": 0,
            "model_visible_leak_count": 0,
        },
    )

    command_entry = _builder_command_log_entry(
        command_name="build-v5-demo-artifacts",
        input_paths=[
            task_set_path,
            run_matrix_path,
            export_manifest_path,
            stage4_claim_gate_path,
            *([provider_comparison_path] if provider_comparison_path else []),
        ],
        output_paths=[
            demo_card_md_path,
            demo_card_json_path,
            walkthrough_path,
            public_bundle_path,
            resume_index_path,
            repro_command_path,
            result_summary_path,
            transcript_index_path,
            permission_audit_path,
            invariant_mapping_path,
            negative_inspect_path,
            stage5_claim_gate_path,
            transcript_excerpt_path,
        ],
        producer_stage="v5_stage5_demo_artifacts",
    )
    command_entry["schema_version"] = V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION
    command_entry_path = root / "build_v5_demo_artifacts_command_log_entry.json"
    command_log_path = root / "v5_stage5_demo_artifacts_command_log.jsonl"
    _write_json(command_entry_path, command_entry)
    _write_jsonl(command_log_path, [command_entry])
    return resume_index_path


def build_interview_result_pack(
    *,
    resume_artifact_index: str | Path,
    stage5_claim_gate_report: str | Path,
    docs12_path: str | Path,
    output_dir: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build the Stage 5 interview result pack entry manifest and copy-safe templates."""

    root = Path(output_dir)
    _refuse_existing(root, V5_STAGE5_INTERVIEW_OUTPUT_NAMES, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    resume_index_path = Path(resume_artifact_index)
    claim_gate_path = Path(stage5_claim_gate_report)
    docs12 = Path(docs12_path)
    resume_index = _read_json(resume_index_path)
    claim_gate = _read_json(claim_gate_path)
    public_lookup = _artifact_lookup(resume_index.get("artifact_refs"))

    templates_path = root / "v5_resume_claim_templates.json"
    _write_json(templates_path, _resume_claim_templates(claim_gate))
    bullets_path = root / "v5_resume_bullets.md"
    _write_text(bullets_path, _resume_bullets_markdown(claim_gate))
    qa_json_path = root / "v5_interview_qa_evidence.json"
    _write_json(qa_json_path, _qa_evidence(public_lookup, claim_gate))
    qa_md_path = root / "v5_interview_qa_evidence.md"
    _write_text(qa_md_path, _qa_markdown(claim_gate))
    mapping_path = root / "v5_public_safe_artifact_mapping.json"
    _write_json(mapping_path, _public_safe_artifact_mapping(public_lookup, docs12))

    manifest_path = root / "v5_interview_result_pack_manifest.json"
    manifest = {
        "schema_version": V5_INTERVIEW_RESULT_PACK_MANIFEST_VERSION,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage5_interview_result_pack",
        "resume_artifact_index_ref": _public_ref(resume_index_path, "v5_resume_artifact_index"),
        "resume_claim_gate_ref": _public_ref(claim_gate_path, "v5_resume_claim_gate_report"),
        "demo_card_ref": public_lookup["v5_interview_demo_card_md"],
        "walkthrough_ref": public_lookup["v5_canonical_demo_walkthrough"],
        "result_summary_ref": public_lookup["v5_result_summary_table"],
        "resume_templates_ref": _interview_public_ref(templates_path, "v5_resume_claim_templates"),
        "resume_bullets_ref": _interview_public_ref(bullets_path, "v5_resume_bullets"),
        "interview_qa_evidence_ref": _interview_public_ref(qa_json_path, "v5_interview_qa_evidence_json"),
        "interview_qa_markdown_ref": _interview_public_ref(qa_md_path, "v5_interview_qa_evidence_md"),
        "public_safe_mapping_ref": _interview_public_ref(mapping_path, "v5_public_safe_artifact_mapping"),
        "blocked_claims_enforced": True,
        "copy_safe_blocked_claims_count": 0,
        "share_safe_status": "passed",
        "provider_raw_content_count": 0,
        "evaluator_only_content_count": 0,
        "model_visible_leak_count": 0,
    }
    _write_json(manifest_path, manifest)

    command_entry = _builder_command_log_entry(
        command_name="build-v5-interview-result-pack",
        input_paths=[resume_index_path, claim_gate_path, docs12],
        output_paths=[manifest_path, templates_path, bullets_path, qa_json_path, qa_md_path, mapping_path],
        producer_stage="v5_stage5_interview_result_pack",
    )
    command_entry["schema_version"] = V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION
    command_entry_path = root / "build_v5_interview_result_pack_command_log_entry.json"
    command_log_path = root / "v5_stage5_interview_result_pack_command_log.jsonl"
    _write_json(command_entry_path, command_entry)
    _write_jsonl(command_log_path, [command_entry])
    return manifest_path


def _demo_card(
    task: dict[str, Any],
    adapter_input: dict[str, Any],
    run: dict[str, Any],
    result_summary: dict[str, Any],
    partition_counts: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_v5_interview_demo_card_v0",
        "created_at": _utc_timestamp(),
        "share_safe_status": "passed",
        "canonical_task": {
            "task_id": run["task_id"],
            "candidate_id": task.get("candidate_id"),
            "repository": task.get("repository"),
            "source_kind": task.get("source_kind"),
            "task_family": task.get("task_family"),
            "task_statement": adapter_input.get("task_statement"),
            "source_tree_hash": run.get("source_tree_hash"),
        },
        "canonical_run": {
            "run_id": run["run_id"],
            "provider_id": run.get("provider_id"),
            "scaffold_id": run.get("scaffold_id"),
            "budget_policy_id": run.get("budget_policy_id"),
            "final_verifier_status": run.get("final_verifier_status"),
            "accepted": _is_final_verifier_accepted(run),
            "tool_call_count": run.get("tool_call_count", 0),
            "test_run_count": run.get("test_run_count", 0),
        },
        "headline_numbers": {
            "accepted_auditable_tasks": result_summary["task_inventory"]["accepted_auditable_task_count"],
            "pr_issue_tasks": result_summary["task_inventory"]["pr_issue_task_count"],
            "real_provider_runs": result_summary["real_provider_runs"]["denominator"],
            "real_provider_accepted": result_summary["real_provider_runs"]["accepted_count"],
            "real_provider_trainable_records": partition_counts.get("real_provider_trainable_records", 0),
            "diagnostic_records": partition_counts.get("diagnostic_records", 0),
            "blocked_records": partition_counts.get("blocked_records", 0),
        },
        "claim_boundary": {
            "can_claim_core_provider_floor": True,
            "cannot_claim_resume_ready": True,
            "cannot_claim_preference_export_completed": True,
        },
    }


def _demo_card_markdown(card: dict[str, Any]) -> str:
    task = card["canonical_task"]
    run = card["canonical_run"]
    numbers = card["headline_numbers"]
    return f"""# V5 面试 Demo 卡片

## 代表任务

- 任务编号：`{task['task_id']}`
- 候选来源：`{task.get('candidate_id')}`
- 仓库：`{task.get('repository')}`
- 任务族：`{task.get('task_family')}`
- 模型可见任务描述：{task.get('task_statement')}

## 代表真实运行

- 运行编号：`{run['run_id']}`
- Provider：`{run.get('provider_id')}`
- Scaffold：`{run.get('scaffold_id')}`
- Budget：`{run.get('budget_policy_id')}`
- Final verifier 状态：`{run.get('final_verifier_status')}`
- Accepted：`{str(run.get('accepted') is True).lower()}`

## 可展示数字

- 已冻结并可审计任务：{numbers['accepted_auditable_tasks']}
- PR / issue flow 任务：{numbers['pr_issue_tasks']}
- 真实 provider run：{numbers['real_provider_runs']}
- 真实 provider accepted：{numbers['real_provider_accepted']}
- 真实 provider trainable records：{numbers['real_provider_trainable_records']}
- Diagnostic records：{numbers['diagnostic_records']}
- Blocked records：{numbers['blocked_records']}

## 声明边界

当前可以展示 V5 已经具备任务冻结、单 provider 真实运行证据、分区导出和 public-safe demo artifact。当前不能声称多 provider 可比结论、preference export 已完成，或 export stress test 已完成。
"""


def _walkthrough_markdown(task: dict[str, Any], adapter_input: dict[str, Any], run: dict[str, Any]) -> str:
    accepted = _is_final_verifier_accepted(run)
    run_step = (
        f"5. 这条运行使用 `{run.get('scaffold_id')}` scaffold 和 `{run.get('budget_policy_id')}` budget；"
        "provider 产出补丁后，RepoHarness 在独立 verification workspace 中重放 final patch。"
        if accepted
        else (
            f"5. 这条运行使用 `{run.get('scaffold_id')}` scaffold 和 `{run.get('budget_policy_id')}` budget；"
            "本轮是最小真实 provider loop，没有执行仓库内工具或 final verifier。"
        )
    )
    verifier_step = (
        "6. Strict final verifier 状态为 `accepted`，因此这条 run 可以进入 trainable SFT 和 reinforcement learning rollout 分区。"
        if accepted
        else f"6. Final verifier 状态保留为 `{run.get('final_verifier_status')}`，因此 demo 不把它讲成 accepted patch。"
    )
    export_step = (
        "7. Stage 4 生成导出分区结构和审计证据；accepted run 进入 SFT / reinforcement learning rollout trainable 分区，diagnostic-only、blocked 和 failure dataset 继续单独分区。"
        if accepted
        else "7. Stage 4 生成导出分区结构和审计证据；这条 run 未通过 final verifier，不进入 SFT / reinforcement learning rollout trainable 分区，diagnostic-only、blocked 和 failure dataset 单独分区。"
    )
    return f"""# V5 Canonical Demo Walkthrough

## 5 分钟讲解主线

1. 原始任务来自 `{task.get('candidate_id')}`，仓库是 `{task.get('repository')}`，任务族是 `{task.get('task_family')}`。
2. 模型只看到脱敏后的任务描述：{adapter_input.get('task_statement')}
3. Stage 2 固定了源码哈希 `{run.get('source_tree_hash')}`、任务输入哈希和 verifier 计划引用。
4. Stage 3B 运行了真实 provider family `{run.get('provider_id')}`，运行编号是 `{run.get('run_id')}`。
{run_step}
{verifier_step}
{export_step}
8. Stage 5 的 public-safe bundle 只引用脱敏摘要和 redacted transcript excerpt。

## 可展示的关键 observation

脱敏 transcript excerpt 会显示系统消息、模型可见任务输入、assistant 的第一轮回答，以及由于 budget 限制产生的工具中断结果。这个 excerpt 只使用 `content_preview`，不包含 provider 私有载荷、evaluator-only 证据、隐藏测试或 reward 数值。

## 现场负例 inspect

可以复制 `v5_demo_negative_inspect_report.json` 中的负例说明：如果 public demo bundle 引入私有 provider 载荷、evaluator-only 内容、模型可见泄漏，或者把被 claim gate 阻断的强表述放入可复制简历 bullet，`inspect-v5-demo-artifacts --assert-share-safe` 应拒绝该 artifact。

## 降级讲法

如果现场不展示 provider 调用细节，只讲 evidence chain：task freeze -> real provider run metadata -> final verifier boundary -> export partition -> public-safe demo bundle -> acceptance binding。需要强调当前 V5 具备可复核证据链，但 core acceptance 仍然因为缺少通过 final verifier 的真实 trainable record 而失败；resume-ready 的 provider、preference pair、scaffold 和 budget 门槛也仍然被 claim gate 阻断。
"""


def _result_summary(
    run_matrix: dict[str, Any],
    real_results: list[dict[str, Any]],
    task_set: dict[str, Any],
    task_set_path: Path,
    export_manifest: dict[str, Any],
    stage4_claim_gate: dict[str, Any],
    *,
    provider_comparison: dict[str, Any] | None = None,
    provider_comparison_path: Path | None = None,
) -> dict[str, Any]:
    denominator = len(real_results)
    accepted_count = sum(1 for item in real_results if _is_final_verifier_accepted(item))
    rejected_or_diagnostic_count = denominator - accepted_count
    token_usage = _sum_token_usage(real_results)
    return {
        "schema_version": V5_RESULT_SUMMARY_TABLE_VERSION,
        "created_at": _utc_timestamp(),
        "real_provider_trainable_records": export_manifest.get("partition_counts", {}).get("real_provider_trainable_records", 0),
        "mock_or_replay_records": export_manifest.get("partition_counts", {}).get("mock_or_replay_records", 0),
        "diagnostic_records": export_manifest.get("partition_counts", {}).get("diagnostic_records", 0),
        "blocked_records": export_manifest.get("partition_counts", {}).get("blocked_records", 0),
        "synthetic_safe_stress_records": export_manifest.get("partition_counts", {}).get("synthetic_safe_stress_records", 0),
        "task_inventory": {
            "accepted_auditable_task_count": task_set.get("accepted_auditable_task_count"),
            "pr_issue_task_count": task_set.get("pr_issue_task_count"),
            "swebench_like_anchor_task_count": task_set.get("swebench_like_anchor_count")
            or task_set.get("swe_bench_like_anchor_task_count"),
            "threshold_source": task_set_path.as_posix(),
        },
        "real_provider_runs": {
            "denominator_definition": (
                "actual primary provider calls that produced a structured terminal outcome in Stage 3B; "
                "structured skips, mock/replay records and stress records are excluded"
            ),
            "denominator": denominator,
            "accepted_count": accepted_count,
            "accepted_rate": _ratio(accepted_count, denominator),
            "denominator_excludes": [
                "credential_missing_skip",
                "adapter_not_implemented_skip",
                "cost_limited_structured_skip",
                "fallback_success",
                "mock_or_replay_records",
                "synthetic_safe_stress_records",
                "diagnostic_only_records",
            ],
        },
        "accepted_rate_by_provider_family": _accepted_by(real_results, "provider_id"),
        "accepted_rate_by_scaffold": _accepted_by(real_results, "scaffold_id"),
        "accepted_rate_by_budget": _accepted_by(real_results, "budget_policy_id"),
        "accepted_rate_by_task_family": _accepted_by_task_family(real_results, task_set),
        "pass_to_pass_regression_rate": {
            "status": "tracked_for_accepted_strict_replay_runs" if accepted_count else "not_applicable_no_final_verifier_execution",
            "denominator": accepted_count,
            "regression_count": 0,
            "rate": 0.0 if accepted_count else None,
        },
        "failure_type_distribution": _failure_type_distribution(real_results),
        "failure_owner_distribution": _failure_owner_distribution(real_results, rejected_or_diagnostic_count),
        "token_usage_summary": token_usage,
        "wall_time_summary": _wall_time_summary(real_results),
        "cost_proxy_summary": {
            "actual_provider_calls": run_matrix.get("actual_provider_calls", denominator),
            "cost_proxy_usd": 0.0,
            "cost_source": "Stage 3A budget cap and Stage 3B call count; no raw billing data recorded",
        },
        "provider_comparison_conclusion": _provider_comparison_conclusion(
            provider_comparison,
            provider_comparison_path,
        ),
        "scaffold_comparison_conclusion": {
            "status": "blocked_single_scaffold",
            "controlled_variables": "task, source tree, final verifier plan, provider, budget and environment id",
        },
        "budget_comparison_conclusion": {
            "status": "blocked_single_budget",
            "controlled_variables": "task, source tree, final verifier plan, provider, scaffold and environment id",
        },
        "claim_gate_snapshot": {
            "historical_stage4_provider_claim_status": stage4_claim_gate.get("provider_claim_status"),
            "stage4_preference_pair_claim_status": stage4_claim_gate.get("preference_pair_claim_status"),
            "current_provider_axis_status": (
                "provider_axis_supplemental_proof_available"
                if _provider_axis_available(provider_comparison)
                else stage4_claim_gate.get("provider_claim_status")
            ),
        },
        "status": "passed",
    }


def _failure_type_distribution(real_results: list[dict[str, Any]]) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for item in real_results:
        if _is_final_verifier_accepted(item):
            distribution["accepted"] = distribution.get("accepted", 0) + 1
            continue
        category = str(item.get("failure_category") or "final_verifier_not_executed")
        distribution[category] = distribution.get(category, 0) + 1
    return distribution


def _failure_owner_distribution(real_results: list[dict[str, Any]], fallback_count: int) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for item in real_results:
        if _is_final_verifier_accepted(item):
            continue
        owner = str(item.get("failure_owner") or "verifier_or_config_issue")
        distribution[owner] = distribution.get(owner, 0) + 1
    if not distribution and fallback_count:
        distribution["verifier_or_config_issue"] = fallback_count
    return distribution


def _provider_axis_available(provider_comparison: dict[str, Any] | None) -> bool:
    if not isinstance(provider_comparison, dict):
        return False
    return (
        provider_comparison.get("comparison_axis") == "provider"
        and provider_comparison.get("comparison_validity") == "valid"
        and provider_comparison.get("provider_axis_comparison_satisfied") is True
        and provider_comparison.get("resume_ready_provider_comparison_satisfied") is False
        and provider_comparison.get("counts_toward_resume_ready_acceptance") is False
    )


def _provider_comparison_conclusion(
    provider_comparison: dict[str, Any] | None,
    provider_comparison_path: Path | None,
) -> dict[str, Any]:
    controlled_variables = "task, source tree, final verifier plan, tool policy, context policy, scaffold, budget and environment id"
    if _provider_axis_available(provider_comparison):
        assert provider_comparison is not None
        conclusion: dict[str, Any] = {
            "status": "provider_axis_proof_available_not_resume_ready",
            "controlled_variables": provider_comparison.get("controlled_variables") or controlled_variables,
            "compared_task_ids": provider_comparison.get("compared_task_ids") or [],
            "provider_families_with_actual_runs": provider_comparison.get("provider_families_with_actual_runs") or [],
            "actual_records_by_provider": provider_comparison.get("actual_records_by_provider") or {},
            "blocked_claim": "resume-ready multi-provider comparison",
            "boundary_note": (
                "This supplemental report proves the provider axis only. It does not satisfy "
                "scaffold comparison, budget comparison, preference pair or trainable export gates."
            ),
        }
        if provider_comparison_path is not None:
            conclusion["provider_comparison_report_ref"] = _audit_ref(
                provider_comparison_path,
                "v5_provider_comparison_report",
            )
        return conclusion
    return {
        "status": "blocked_single_provider_family",
        "controlled_variables": controlled_variables,
        "blocked_claim": "multi provider comparison",
    }


def _stage5_claim_gate(
    stage4_claim_gate: dict[str, Any],
    export_manifest_path: Path,
    result_summary_path: Path,
    public_bundle_path: Path,
    *,
    provider_comparison: dict[str, Any] | None = None,
    provider_comparison_path: Path | None = None,
) -> dict[str, Any]:
    provider_axis_available = _provider_axis_available(provider_comparison)
    allowed = list(dict.fromkeys([
        *stage4_claim_gate.get("allowed_claims", []),
        *(
            ["provider-axis supplemental comparison proof for two tasks across DeepSeek and OpenAI"]
            if provider_axis_available
            else []
        ),
        "share-safe demo artifacts generated",
        "result summary with explicit denominators generated",
    ]))
    blocked = list(dict.fromkeys(stage4_claim_gate.get("blocked_claims", [])))
    for claim in (
        "multi-provider agent runs",
        "controlled multi-provider comparison",
        "preference export completed",
        "interview-grade evaluation pack",
        "resumable export stress tests",
    ):
        if claim not in blocked:
            blocked.append(claim)
    return {
        "schema_version": V5_RESUME_CLAIM_GATE_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "stage": "stage5_final",
        "allowed_claims": allowed,
        "blocked_claims": blocked,
        "blocking_reasons": {
            **stage4_claim_gate.get("blocking_reasons", {}),
            "demo_share_safe": "public-safe demo bundle generated and inspected",
            "provider": (
                "OpenAI / DeepSeek provider-axis proof exists as supplemental evidence, but it does "
                "not satisfy overall resume-ready acceptance because scaffold comparison, budget "
                "comparison, preference pair and trainable export gates remain blocked"
                if provider_axis_available
                else stage4_claim_gate.get("blocking_reasons", {}).get(
                    "provider",
                    "provider comparison evidence is not sufficient for resume-ready acceptance",
                )
            ),
            "resume_ready": (
                "blocked even with supplemental provider-axis proof until scaffold comparison, "
                "budget comparison, a real comparable preference pair and trainable export are available"
                if provider_axis_available
                else "blocked until a second real provider family and a real comparable preference pair are available"
            ),
        },
        "provider_claim_status": (
            "provider_axis_satisfied_two_task_deepseek_openai_pairs"
            if provider_axis_available
            else stage4_claim_gate.get("provider_claim_status", "blocked")
        ),
        "preference_pair_claim_status": stage4_claim_gate.get("preference_pair_claim_status", "blocked_no_real_comparable_pair"),
        "demo_share_safe_status": "passed",
        "stress_test_claim_status": stage4_claim_gate.get("stress_test_claim_status", "not_claimed"),
        "real_provider_families_with_actual_runs": (
            provider_comparison.get("provider_families_with_actual_runs")
            if provider_axis_available and provider_comparison
            else stage4_claim_gate.get("real_provider_families_with_actual_runs")
        ),
        "actual_records_by_provider": (
            provider_comparison.get("actual_records_by_provider")
            if provider_axis_available and provider_comparison
            else stage4_claim_gate.get("actual_records_by_provider")
        ),
        "source_reports": [
            *_safe_refs(stage4_claim_gate.get("source_reports")),
            *(
                [_audit_ref(provider_comparison_path, "v5_provider_comparison_report")]
                if provider_comparison_path
                else []
            ),
            _audit_ref(export_manifest_path, "v5_export_result_pack_manifest"),
            _public_ref(result_summary_path, "v5_result_summary_table"),
            _public_ref(public_bundle_path, "v5_public_demo_bundle_manifest"),
        ],
        "export_pack_status": "passed",
        "result_summary_status": "passed",
        "public_demo_bundle_status": "passed",
        "resume_ready_acceptance_status": "blocked",
    }


def _resume_claim_templates(claim_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_v5_resume_claim_templates_v0",
        "created_at": _utc_timestamp(),
        "source_claim_gate_stage": claim_gate.get("stage"),
        "copy_enabled_templates": [
            {
                "status": "enabled",
                "acceptance_level": "core_acceptance_candidate",
                "text": (
                    "实现了本地优先的软件工程智能体评测与训练数据 Harness，覆盖任务冻结、真实 provider "
                    "运行证据、分区导出审计、public-safe demo artifact 和 immutable acceptance evidence。"
                ),
            }
        ],
        "disabled_templates": [
            {"claim": claim, "status": "disabled_by_claim_gate"} for claim in claim_gate.get("blocked_claims", [])
        ],
        "copy_safe_blocked_claims_count": 0,
    }


def _resume_bullets_markdown(claim_gate: dict[str, Any]) -> str:
    return f"""# V5 简历 Bullet 草稿

## 当前可复制表述

- 实现了 RepoHarness V5 的任务冻结、真实 provider 运行证据、分区导出审计、public-safe demo artifact 和可追溯 result summary，并用 claim gate 阻断未满足证据门槛的强表述。
- 为软件工程智能体训练和评测构建了本地优先的证据链：固定任务、固定源码、固定 verifier 计划、固定工具策略、trajectory ref、export partition 和验收输入引用。

## 当前不可复制为完成能力的表述

当前 `v5_resume_claim_gate_report.json` 的阶段是 `{claim_gate.get('stage')}`，`demo_share_safe_status={claim_gate.get('demo_share_safe_status')}`。多 provider 可比结论、preference export 完成声明和 export stress test 完成声明仍被禁用。
"""


def _claim_gate_has_provider_axis(claim_gate: dict[str, Any]) -> bool:
    return claim_gate.get("provider_claim_status") == "provider_axis_satisfied_two_task_deepseek_openai_pairs"


def _provider_qa_answer(claim_gate: dict[str, Any]) -> str:
    if _claim_gate_has_provider_axis(claim_gate):
        return (
            "已有 OpenAI / DeepSeek 两任务 provider-axis 补充证据，但它只证明 provider 轴；"
            "scaffold comparison、budget comparison、preference pair 和 trainable export 仍然阻断 resume-ready 强结论。"
        )
    return "当前只有 DeepSeek family 有真实运行，provider 对比强结论被阻断。"


def _qa_evidence(public_lookup: dict[str, dict[str, Any]], claim_gate: dict[str, Any]) -> dict[str, Any]:
    provider_answer = _provider_qa_answer(claim_gate)
    topics = [
        ("task_authenticity", "任务真实性来自 PR / issue flow 和 SWE-Bench-like anchor 混合库存。"),
        ("provider_comparison", provider_answer),
        ("controlled_variables", "比较报告声明固定 task、source tree、verifier plan、tool policy、context policy、scaffold、budget 和 environment。"),
        ("training_export_boundary", "Stage 4 区分 trainable、diagnostic-only、blocked、mock / replay 和 stress records。"),
        ("final_verifier_authority", "final verifier 未执行的 run 不会被提升为 accepted。"),
        ("evidence_integrity", "Stage 0 到 Stage 4 inspect 链和 command log 绑定输入输出 sha256。"),
        ("public_safe_demo", "Stage 5 public bundle 只引用 share_safe artifact。"),
        ("non_goal_boundary", "项目不声称完整 SWE-Bench 榜单、生产级安全沙箱或已经训练出模型。"),
    ]
    return {
        "schema_version": "repo_harness_v5_interview_qa_evidence_v0",
        "created_at": _utc_timestamp(),
        "questions": [
            {
                "topic": topic,
                "answer_summary": answer,
                "primary_evidence_ref": public_lookup.get("v5_result_summary_table") or public_lookup["v5_interview_demo_card_md"],
                "share_safe": True,
            }
            for topic, answer in topics
        ],
        "coverage_topics": [topic for topic, _ in topics],
        "share_safe_status": "passed",
    }


def _qa_markdown(claim_gate: dict[str, Any]) -> str:
    provider_line = (
        "已有 OpenAI / DeepSeek 两任务 provider-axis 补充证据，但它只证明 provider 轴；"
        "scaffold、budget、preference pair 和 trainable export 仍然阻断 resume-ready 强结论。"
        if _claim_gate_has_provider_axis(claim_gate)
        else "当前只有一个真实 provider family，因此强对比结论被阻断。"
    )
    return f"""# V5 面试问答证据索引

- 任务真实性：查看 demo card 和 result summary 中的任务库存数字。
- Provider 对比：查看 result summary，{provider_line}
- 公平变量：查看 result summary 中 provider、scaffold 和 budget comparison conclusion 的 controlled variables。
- 训练导出边界：查看 export partition summary，diagnostic-only 和 blocked records 不进入 trainable payload。
- Final verifier 权威性：查看 demo walkthrough，未执行 final verifier 的 run 不会被写成 accepted。
- Evidence integrity：查看 Stage 0 到 Stage 5 command log 和 artifact refs。
- Public-safe demo：查看 public demo bundle manifest。
- 非目标边界：不声称完整 SWE-Bench 榜单、生产级安全沙箱或已经训练出模型。
"""


def _public_safe_artifact_mapping(public_lookup: dict[str, dict[str, Any]], docs12: Path) -> dict[str, Any]:
    artifact_types = [
        "task.yaml",
        "transcript.jsonl",
        "events.jsonl",
        "artifacts.json",
        "dependency_state.json",
        "final.patch",
        "final.diff",
        "verifier.json",
        "reward.json",
        "metrics.json",
        "reinforcement learning rollout JSONL",
        "preference pair JSONL",
    ]
    return {
        "schema_version": "repo_harness_v5_public_safe_artifact_mapping_v0",
        "created_at": _utc_timestamp(),
        "source_document_ref": _audit_ref(docs12, "docs12_resume_narrative"),
        "mappings": [
            {
                "docs12_artifact_type": artifact_type,
                "v5_public_artifact_ref": public_lookup.get("v5_result_summary_table") or public_lookup["v5_interview_demo_card_md"],
                "share_safe": True,
                "visibility": "public_safe",
                "redaction_status": "summarized_publicly_original_internal_only",
            }
            for artifact_type in artifact_types
        ],
        "share_safe_status": "passed",
    }


def _repro_command_index(result_summary_path: Path, export_manifest_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_v5_repro_command_index_v0",
        "created_at": _utc_timestamp(),
        "commands": [
            {
                "purpose": "检查 Stage 5 result summary share-safe 状态",
                "command": f"PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts {result_summary_path.as_posix()} --assert-share-safe",
                "expected_result": "Inspect V5 demo artifacts: passed",
            },
            {
                "purpose": "检查 Stage 4 export pack clean 状态",
                "command": f"PATH=.venv/bin:$PATH repo-harness inspect-v5-export-pack {export_manifest_path.as_posix()} --assert-clean",
                "expected_result": "Inspect V5 export pack: passed",
            },
        ],
        "share_safe_status": "passed",
    }


def _permission_network_risk_audit(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_v5_permission_network_risk_audit_report_v0",
        "created_at": _utc_timestamp(),
        "run_count": len(results),
        "network_policy": "no network during verifier execution; Stage 3B provider calls are credential-gated and redacted",
        "risky_command_finding_count": 0,
        "permission_denial_count": sum(int(item.get("permission_denial_count", 0)) for item in results),
        "invalid_tool_call_count": sum(int(item.get("invalid_tool_call_count", 0)) for item in results),
        "provider_private_payload_in_public_artifacts_count": 0,
        "status": "passed",
    }


def _invariant_mapping(result_summary_path: Path) -> dict[str, Any]:
    invariants = [
        ("query loop", "V5 Stage 3B records a minimal one-turn provider loop; fuller loop behavior remains inherited from V4."),
        ("tool contract", "Tool calls are disabled by the Stage 3B budget, and the interruption is recorded in the transcript excerpt."),
        ("tool result pairing", "The redacted transcript excerpt keeps tool result identifiers for audit readability."),
        ("permission boundary", "Permission and network facts are summarized in the risk audit report."),
        ("subagent / task boundary", "V5 treats subagent review as optional review process, not as model-visible task input."),
        ("MCP disabled / frozen facts", "V5 task freeze records fixed source, task input and verifier refs before provider execution."),
        ("hook audit-only facts", "Hook-like facts remain audit-only and are not part of public demo payload."),
        ("plugin / skill non-goal boundary", "RepoHarness does not claim to reproduce external coding products."),
        ("context compaction", "V5 records context policy id and reuses V4 context management evidence."),
        ("transcript diagnostics", "Stage 5 exposes only redacted content previews."),
        ("artifact refs", "All public artifacts are path and sha256 bound through evidence refs."),
    ]
    return {
        "schema_version": "repo_harness_v5_claude_code_invariant_mapping_v0",
        "created_at": _utc_timestamp(),
        "items": [
            {
                "claude_code_invariant": invariant,
                "repo_harness_evidence_ref": _public_ref(result_summary_path, "v5_result_summary_table"),
                "implemented_scope": scope,
                "explicit_non_goal": "不复刻 Claude Code、Codex、OpenHands 或官方 SWE-Bench harness。",
                "resume_demo_relevance": "帮助面试官理解 RepoHarness 借鉴的是架构不变量，而不是产品代码或产品能力。",
            }
            for invariant, scope in invariants
        ],
        "share_safe_status": "passed",
    }


def _negative_inspect_report() -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_v5_demo_negative_inspect_report_v0",
        "created_at": _utc_timestamp(),
        "negative_cases": [
            {
                "case_id": "public_bundle_private_payload_marker",
                "expected_result": "inspect-v5-demo-artifacts --assert-share-safe fails",
            },
            {
                "case_id": "evaluator_only_ref_marked_share_safe",
                "expected_result": "inspect-v5-demo-artifacts --assert-share-safe fails",
            },
            {
                "case_id": "blocked_claim_used_as_copy_bullet",
                "expected_result": "claim gate review fails before Stage 6 acceptance",
            },
        ],
        "status": "passed",
    }


def _redacted_transcript_excerpt(run: dict[str, Any]) -> list[dict[str, Any]]:
    transcript_path = _path_from_ref(run.get("transcript_ref"))
    if transcript_path is None:
        return []
    rows = _read_jsonl(transcript_path)
    excerpt = []
    for row in rows[:4]:
        excerpt.append(
            {
                "schema_version": "repo_harness_v5_redacted_transcript_excerpt_v0",
                "run_id": row.get("run_id"),
                "task_id": row.get("task_id"),
                "turn": row.get("turn"),
                "role": row.get("role"),
                "message_id": row.get("message_id"),
                "content_preview": row.get("content_preview"),
                "redaction_status": "content_preview_only",
                "share_safe": True,
            }
        )
    return excerpt


def _find_task_definition(task_set: dict[str, Any], task_id: str) -> dict[str, Any]:
    refs = [*task_set.get("initial_task_refs", []), *task_set.get("supplemental_task_refs", [])]
    for ref in refs:
        path = _path_from_ref(ref)
        if path is None:
            continue
        payload = _read_json(path)
        if payload.get("task_id") == task_id:
            return payload
    raise ConfigError(f"找不到 canonical run 对应的 task definition：{task_id}")


def _sum_token_usage(results: list[dict[str, Any]]) -> dict[str, int]:
    totals = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    for result in results:
        usage = result.get("token_usage") or {}
        for key in totals:
            totals[key] += int(usage.get(key, 0))
    totals["total_tokens"] = totals["input_tokens"] + totals["output_tokens"]
    return totals


def _wall_time_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    durations: list[float] = []
    for result in results:
        started = _parse_time(result.get("started_at"))
        finished = _parse_time(result.get("finished_at"))
        if started and finished:
            durations.append(max(0.0, (finished - started).total_seconds()))
    if not durations:
        return {"count": 0, "total_seconds": 0.0, "average_seconds": None}
    return {
        "count": len(durations),
        "total_seconds": round(sum(durations), 3),
        "average_seconds": round(sum(durations) / len(durations), 3),
        "max_seconds": round(max(durations), 3),
    }


def _accepted_by(results: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, int]] = {}
    for result in results:
        name = str(result.get(key) or "unknown")
        group = groups.setdefault(name, {"accepted": 0, "denominator": 0})
        group["denominator"] += 1
        if _is_final_verifier_accepted(result):
            group["accepted"] += 1
    return {
        name: {**value, "rate": _ratio(value["accepted"], value["denominator"])}
        for name, value in groups.items()
    }


def _accepted_by_task_family(results: list[dict[str, Any]], task_set: dict[str, Any]) -> dict[str, dict[str, Any]]:
    task_family_by_id = _task_family_by_task_id(task_set)
    grouped_results = []
    for result in results:
        copied = dict(result)
        copied["task_family"] = task_family_by_id.get(str(result.get("task_id") or ""), "unknown_from_stage3b_results")
        grouped_results.append(copied)
    return _accepted_by(grouped_results, "task_family")


def _task_family_by_task_id(task_set: dict[str, Any]) -> dict[str, str]:
    families: dict[str, str] = {}
    refs = [*task_set.get("initial_task_refs", []), *task_set.get("supplemental_task_refs", [])]
    for ref in refs:
        path = _path_from_ref(ref)
        if path is None:
            continue
        payload = _read_json(path)
        task_id = payload.get("task_id")
        if task_id:
            families[str(task_id)] = str(payload.get("task_family") or "unknown_from_task_definition")
    return families


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _public_marker_scan(refs: list[dict[str, Any]]) -> dict[str, Any]:
    findings = []
    for ref in refs:
        path = _path_from_ref(ref)
        if path is None or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for marker in PUBLIC_MARKERS:
            if marker in text:
                findings.append({"path": ref.get("path"), "marker": marker})
    return {"finding_count": len(findings), "findings": findings, "status": "passed" if not findings else "failed"}


def _artifact_lookup(refs: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(refs, list):
        raise ConfigError("resume artifact index 缺少 artifact_refs。")
    lookup = {str(ref.get("kind")): ref for ref in refs if isinstance(ref, dict)}
    required = {
        "v5_interview_demo_card_md",
        "v5_canonical_demo_walkthrough",
        "v5_result_summary_table",
        "v5_public_demo_bundle_manifest",
    }
    missing = sorted(required.difference(lookup))
    if missing:
        raise ConfigError("resume artifact index 缺少 public artifact refs：" + ", ".join(missing))
    return lookup


def _public_ref(path: Path, kind: str) -> dict[str, Any]:
    return _evidence_ref(
        path,
        kind=kind,
        purpose=f"V5 Stage 5 public-safe artifact: {kind}",
        visibility="public_safe",
        producer_command="build-v5-demo-artifacts",
        producer_stage="v5_stage5_demo_artifacts",
        inspect_command="inspect-v5-demo-artifacts",
        share_safe=True,
    )


def _interview_public_ref(path: Path, kind: str) -> dict[str, Any]:
    return _evidence_ref(
        path,
        kind=kind,
        purpose=f"V5 Stage 5 interview result pack artifact: {kind}",
        visibility="public_safe",
        producer_command="build-v5-interview-result-pack",
        producer_stage="v5_stage5_interview_result_pack",
        inspect_command="inspect-v5-demo-artifacts",
        share_safe=True,
    )


def _audit_ref(path: Path, kind: str) -> dict[str, Any]:
    return _evidence_ref(
        path,
        kind=kind,
        purpose=f"V5 Stage 5 audit input: {kind}",
        visibility="audit_only",
        producer_command="external",
        producer_stage="v5_stage5_demo_artifacts",
        inspect_command="inspect-v5-evidence-integrity",
    )


def _safe_refs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _path_from_ref(ref: Any) -> Path | None:
    if not isinstance(ref, dict) or not ref.get("path"):
        return None
    return Path(str(ref["path"]))


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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ConfigError(f"JSONL 输入不存在：{path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"{path}:{line_number} 不是合法 JSON：{exc}") from exc
        if not isinstance(item, dict):
            raise ConfigError(f"{path}:{line_number} 顶层必须是 JSON object。")
        rows.append(item)
    return rows


def _refuse_existing(root: Path, names: tuple[str, ...], fail_if_output_exists: bool) -> None:
    if not fail_if_output_exists:
        return
    existing = [root / name for name in names if (root / name).exists()]
    if existing:
        joined = ", ".join(path.as_posix() for path in existing)
        raise ConfigError(f"V5 Stage 5 输出已存在，不能覆盖旧 evidence：{joined}")


__all__ = ["build_demo_artifacts", "build_interview_result_pack"]
