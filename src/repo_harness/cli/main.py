"""RepoHarness 第一版命令行入口。"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from repo_harness import __version__
from repo_harness.config import load_run_config
from repo_harness.errors import RepoHarnessError
from repo_harness.evaluation.runner import run_batch as run_batch_command
from repo_harness.evaluation.runner import run_task as run_task_command
from repo_harness.evaluation.episode_runner import run_episode_task as run_episode_task_command
from repo_harness.evaluation.episode_parity import inspect_stage16f4_parity
from repo_harness.evaluation.experiment import (
    inspect_experiment as inspect_experiment_command,
)
from repo_harness.evaluation.experiment import run_experiment as run_experiment_command
from repo_harness.export import ExportPolicy, export_run_or_runs, inspect_export
from repo_harness.inspect_initial_context import inspect_initial_context
from repo_harness.model_client.mock_smoke import inspect_mock_provider_smoke
from repo_harness.model_client.real_smoke import inspect_real_provider_smoke, run_real_provider_smoke
from repo_harness.tasks import load_task
from repo_harness.trajectory import inspect_run
from repo_harness.v2_acceptance import (
    build_v2_acceptance_report,
    inspect_feedback_policy_coverage,
    inspect_v2_acceptance,
)
from repo_harness.v3_swebench_fixture import (
    inspect_v3_swebench_fixture,
    prepare_v3_swebench_fixture,
)
from repo_harness.v3_agent_loop import (
    build_v3_agent_loop_integration,
    inspect_v3_agent_loop_integration,
)
from repo_harness.v3_experiment_resume import (
    build_v3_experiment_resume,
    inspect_experiment_resume,
)
from repo_harness.v3_context_diagnostics import (
    build_v3_context_diagnostics,
    inspect_context_report,
    inspect_long_rollout_diagnostics,
)
from repo_harness.v3_failure_diagnostics import (
    build_v3_failure_diagnostics,
    inspect_reward_diagnostics,
)
from repo_harness.v3_export_audit import (
    build_v3_export_audit,
    inspect_v3_export_audit,
)
from repo_harness.v3_acceptance import (
    build_v3_acceptance_bundle,
    build_v3_acceptance_inputs,
    build_v3_acceptance_report,
    build_v3_run_selection_manifest,
    inspect_acceptance_bundle,
    inspect_tool_contract,
    inspect_trajectory_store,
    inspect_v3_acceptance,
)
from repo_harness.v3_source_materialization import (
    build_v3_source_materialization,
    inspect_v3_source_materialization,
)
from repo_harness.v3_swebench_like import build_v3_swebench_like, inspect_swebench_like
from repo_harness.v3_task_set import build_v3_task_set, inspect_v3_task_set
from repo_harness.v4_implementation_inputs import (
    build_v4_implementation_inputs,
    inspect_v4_implementation_inputs,
)
from repo_harness.v4_stage1 import (
    inspect_v4_acceptance,
    inspect_v4_artifact_set,
    inspect_v4_inputs,
)
from repo_harness.v4_task_freeze import (
    build_v4_task_freeze,
    inspect_v4_task_freeze as inspect_v4_task_freeze_stage2,
    inspect_v4_task_validity as inspect_v4_task_validity_stage2,
)
from repo_harness.v4_rollout import (
    build_v4_rollout_orchestration,
    inspect_resource_locks as inspect_v4_resource_locks_stage3,
    inspect_resource_usage as inspect_v4_resource_usage_stage3,
    inspect_rollout_budget as inspect_v4_rollout_budget_stage3,
    inspect_rollout_leases as inspect_v4_rollout_leases_stage3,
    inspect_rollout_queue as inspect_v4_rollout_queue_stage3,
    inspect_rollout_resume as inspect_v4_rollout_resume_stage3,
    inspect_rollout_retry as inspect_v4_rollout_retry_stage3,
    inspect_run_selection_query as inspect_v4_run_selection_query_stage3,
)
from repo_harness.v4_tool_lifecycle import (
    build_v4_tool_lifecycle,
    inspect_v4_tool_contract as inspect_v4_tool_contract_stage4,
    inspect_v4_tool_lifecycle as inspect_v4_tool_lifecycle_stage4,
)
from repo_harness.v4_agent_run import (
    build_v4_agent_run_integration,
    inspect_v4_agent_run_integration as inspect_v4_agent_run_integration_stage5,
    inspect_v4_trajectory_store as inspect_v4_trajectory_store_stage5,
)
from repo_harness.v4_export_quality import (
    build_v4_export_quality,
    inspect_v4_export_quality as inspect_v4_export_quality_stage6,
)
from repo_harness.v4_cards import (
    build_v4_cards,
    inspect_v4_cards as inspect_v4_cards_stage7,
)
from repo_harness.v4_acceptance import (
    build_v4_acceptance_bundle,
    build_v4_acceptance_inputs,
    build_v4_acceptance_report,
    build_v4_run_selection_manifest,
)
from repo_harness.v5_evidence import (
    build_pre_acceptance_integrity_report,
    build_schema_fixtures,
    build_v5_preimplementation,
    inspect_v5_acceptance,
    inspect_v5_demo_artifacts,
    inspect_v5_evidence_integrity,
    inspect_v5_export_pack,
    inspect_v5_inputs,
    inspect_v5_preimplementation,
    inspect_v5_provider_cost_budget,
    inspect_v5_provider_gate,
    inspect_v5_run_matrix,
    inspect_v5_task_set,
    inspect_v5_task_visibility,
)
from repo_harness.v5_task_set import (
    build_supplemental_pr_issue_candidates as build_v5_supplemental_pr_issue_candidates,
)
from repo_harness.v5_task_set import build_task_set_manifest as build_v5_task_set_manifest
from repo_harness.v5_task_set import merge_task_set_manifests as merge_v5_task_set_manifests
from repo_harness.v5_export_pack import build_export_result_pack as build_v5_export_result_pack
from repo_harness.v5_demo_artifacts import (
    build_demo_artifacts as build_v5_demo_artifacts,
)
from repo_harness.v5_demo_artifacts import (
    build_interview_result_pack as build_v5_interview_result_pack,
)
from repo_harness.v5_acceptance import (
    build_acceptance_bundle as build_v5_acceptance_bundle,
)
from repo_harness.v5_acceptance import (
    build_acceptance_inputs as build_v5_acceptance_inputs,
)
from repo_harness.v5_acceptance import (
    build_acceptance_report as build_v5_acceptance_report,
)
from repo_harness.v5_acceptance import build_final_command_log as build_v5_final_command_log
from repo_harness.v5_acceptance import (
    build_pre_bundle_command_log as build_v5_pre_bundle_command_log,
)
from repo_harness.v5_acceptance import (
    plan_acceptance_bundle_build_entry as plan_v5_acceptance_bundle_build_entry,
)
from repo_harness.v5_acceptance import (
    plan_acceptance_bundle_inspect_entry as plan_v5_acceptance_bundle_inspect_entry,
)
from repo_harness.v5_provider_gate import (
    build_provider_cost_budget_report as build_v5_provider_cost_budget_report,
)
from repo_harness.v5_provider_gate import build_provider_gate_report as build_v5_provider_gate_report
from repo_harness.v5_run_matrix import (
    build_comparison_reports as build_v5_comparison_reports,
)
from repo_harness.v5_run_matrix import (
    build_run_matrix_manifest as build_v5_run_matrix_manifest,
)
from repo_harness.v5_run_matrix import run_accepted_provider_task as run_v5_accepted_provider_task
from repo_harness.v5_run_matrix import run_matrix_cells as run_v5_run_matrix_cells
from repo_harness.pre_verl_evaluation import (
    build_pre_verl_agent_evaluation,
    build_pre_verl_baseline,
    build_pre_verl_export_audit,
    build_pre_verl_final,
    build_pre_verl_materialized_task_set,
    build_pre_verl_runtime_audit,
    build_pre_verl_swebench_dev_materialization,
    build_pre_verl_task_set,
    build_pre_verl_verifier_correctness,
    inspect_pre_verl_agent_evaluation,
    inspect_pre_verl_baseline,
    inspect_pre_verl_bundle,
    inspect_pre_verl_claim_gate,
    inspect_pre_verl_evaluation,
    inspect_pre_verl_export_audit,
    inspect_pre_verl_inputs,
    inspect_pre_verl_phase_coverage,
    inspect_pre_verl_public_safe,
    inspect_pre_verl_readiness,
    inspect_pre_verl_reward_boundary,
    inspect_pre_verl_runtime_audit,
    inspect_pre_verl_swebench_dev_materialization,
    inspect_pre_verl_task_set,
    inspect_pre_verl_task_visibility,
    inspect_pre_verl_verifier_correctness,
)
from repo_harness.pre_verl_agentloop import (
    inspect_model_visible_context,
    inspect_pre_verl_agentloop_boundary_index,
    inspect_pre_verl_agentloop_run_config,
    inspect_pre_verl_agentloop_task_definitions,
)
from repo_harness.pre_verl_evidence_ledger import (
    build_pre_verl_evidence_ledger,
    inspect_pre_verl_evidence_ledger,
)
from repo_harness.pre_verl_failure_injection import (
    DEFAULT_PROVIDER_FAILURE_INJECTION_SCENARIOS,
    run_provider_failure_injection_smoke,
)
from repo_harness.evaluation.stage16d_healthcheck import inspect_stage16d_healthcheck
from repo_harness_verl.stage14_acceptance import inspect_stage14_fully_async_acceptance
from repo_harness_verl.stage15_acceptance import inspect_stage15_partial_rollout_acceptance
from repo_harness_verl.stage16b5_acceptance import inspect_stage16b5_docker_backend_acceptance
from repo_harness_verl.stage14_remote_smoke import write_stage14_remote_smoke_kit
from repo_harness.workspace import inspect_workspace_backend_status, write_workspace_backend_status


def build_parser() -> argparse.ArgumentParser:
    """构造顶层命令行解析器。"""

    parser = argparse.ArgumentParser(
        prog="repo-harness",
        description="RepoHarness：轻量级、可审计的软件工程智能体 harness。",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"repo-harness {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    validate_task = subparsers.add_parser(
        "validate-task",
        help="校验任务定义文件，但不创建工作区、不运行测试。",
    )
    validate_task.add_argument("task_path", help="任务 YAML 文件路径。")

    run_task = subparsers.add_parser(
        "run-task",
        help="用 replay model 运行单个任务的最小完整闭环。",
    )
    run_task.add_argument("task_path", help="任务 YAML 文件路径。")
    run_task.add_argument("--config", required=True, help="RunConfig YAML 文件路径。")
    run_task.add_argument("--output-dir", default=None, help="运行产物根目录。")
    run_task.add_argument("--run-id", default=None, help="显式指定本次 run id。")
    run_task.add_argument(
        "--inject-interrupt-after",
        choices=["baseline", "agent_loop", "final_verifier"],
        default=None,
        help="V3 resume 测试专用：在固定 phase 后结构化中断 run。",
    )

    run_episode_task = subparsers.add_parser(
        "run-episode-task",
        help="实验性入口：把单个任务通过 run_episode(real_episode) 路径运行，并写出安全兼容投影。",
    )
    run_episode_task.add_argument("task_path", help="任务 YAML 文件路径。")
    run_episode_task.add_argument("--config", required=True, help="RunConfig YAML 文件路径。")
    run_episode_task.add_argument("--output-dir", default=None, help="运行产物根目录。")
    run_episode_task.add_argument("--run-id", default=None, help="显式指定本次 run id。")
    run_episode_task.add_argument(
        "--gateway-route",
        default=None,
        choices=["mock", "replay", "openai", "deepseek"],
        help="覆盖 RunConfig.model.provider 映射出的 LLMGateway route；fake provider 会映射为 mock。",
    )
    run_episode_task.add_argument(
        "--assert-projection-complete",
        action="store_true",
        help="要求兼容投影通过绑定、摘要、路径泄漏和训练资格校验。",
    )

    run_batch = subparsers.add_parser(
        "run-batch",
        help="按 RunConfig.tasks 顺序运行任务列表。",
    )
    run_batch.add_argument("--config", required=True, help="RunConfig YAML 文件路径。")
    run_batch.add_argument("--output-dir", default=None, help="运行产物根目录。")

    run_experiment = subparsers.add_parser(
        "run-experiment",
        help="按 ExperimentConfig 顺序运行最小多 rollout 实验。",
    )
    run_experiment.add_argument("--config", required=True, help="ExperimentConfig YAML 文件路径。")
    run_experiment.add_argument("--output-dir", default=None, help="实验产物目录。")

    inspect_experiment = subparsers.add_parser(
        "inspect-experiment",
        help="只读检查实验目录。",
    )
    inspect_experiment.add_argument("experiment_dir", help="实验目录路径。")
    inspect_experiment.add_argument(
        "--assert-minimums",
        default=None,
        help="实验 smoke 阈值 YAML 文件路径。",
    )

    export = subparsers.add_parser(
        "export",
        help="从已有 run directory 或 runs 根目录导出训练数据。",
    )
    export.add_argument("run_dir_or_runs_dir", help="单个 run directory 或 runs 根目录。")
    export.add_argument(
        "--format",
        required=True,
        choices=[
            "sft_jsonl",
            "rl_jsonl",
            "preference_jsonl",
            "provider_reasoning_trace_training_export",
        ],
        help="导出格式。",
    )
    export.add_argument(
        "--allow-oracle-feedback-training",
        action="store_true",
        help="显式允许 oracle_hidden_feedback 样本进入正式训练数据；默认不允许。",
    )
    export.add_argument(
        "--compare-scope",
        default=None,
        help="Preference export 使用的 CompareScope 或 PairingPolicy JSON 文件路径。",
    )
    export.add_argument(
        "--allow-provider-reasoning-trace-training",
        action="store_true",
        help=(
            "显式允许 provider_reasoning_trace_training_export 输出 DeepSeek reasoning trace "
            "训练目标；默认不允许。"
        ),
    )

    inspect_run = subparsers.add_parser(
        "inspect-run",
        help="只读检查 run directory。",
    )
    inspect_run.add_argument("run_dir", help="run directory 路径。")

    inspect_export_parser = subparsers.add_parser(
        "inspect-export",
        help="只读检查规范导出目录。",
    )
    inspect_export_parser.add_argument("export_dir", help="单个规范导出目录或 exports 根目录。")
    inspect_export_parser.add_argument("--all", action="store_true", help="检查 exports 根目录下全部规范导出目录。")
    inspect_export_parser.add_argument(
        "--format",
        choices=[
            "sft_jsonl",
            "rl_jsonl",
            "preference_jsonl",
            "provider_reasoning_trace_training_export",
        ],
        default=None,
        help="只检查指定导出格式。",
    )
    inspect_export_parser.add_argument("--assert-clean", action="store_true", help="发现导出审计问题时返回失败。")
    inspect_export_parser.add_argument(
        "--require-trainable-samples",
        action="store_true",
        help="要求至少有一个 trainable 样本进入正式训练数据文件。",
    )
    inspect_export_parser.add_argument(
        "--allow-provider-reasoning-trace-diagnostic-only",
        action="store_true",
        help=(
            "检查 provider_reasoning_trace_training_export 时，允许失败题的 reasoning trace "
            "只作为诊断导出存在，但仍要求目标内容、隔离策略、文件哈希和审计项正确。"
        ),
    )

    inspect_mock = subparsers.add_parser(
        "inspect-mock-provider-smoke",
        help="生成并检查 mock provider smoke report。",
    )
    inspect_mock.add_argument("--run-dir", required=True, help="mock provider run directory。")
    inspect_mock.add_argument("--output", required=True, help="mock_provider_smoke_report.json 输出路径。")
    inspect_mock.add_argument("--assert-accepted", action="store_true", help="要求 smoke run accepted。")
    inspect_mock.add_argument("--assert-export-clean", action="store_true", help="要求已有导出审计 clean。")

    run_real = subparsers.add_parser(
        "run-real-provider-smoke",
        help="运行 Stage 11 真实 provider smoke；无凭证时生成结构化 skip report。",
    )
    run_real.add_argument("--output-dir", required=True, help="真实 provider smoke 输出目录。")
    run_real.add_argument("--report", default=None, help="real_provider_smoke_report.json 输出路径。")
    run_real.add_argument(
        "--allow-openai-fallback",
        action="store_true",
        help="DeepSeek 缺凭证或失败时允许显式 OpenAI 备用 smoke。",
    )
    run_real.add_argument(
        "--allow-local-secret-file",
        action="store_true",
        help="允许 Stage 11 smoke 从 reference/deepseek_api.md 读取本地 DeepSeek 密钥；报告只记录脱敏来源标签。",
    )

    inspect_real = subparsers.add_parser(
        "inspect-real-provider-smoke",
        help="只读检查 real_provider_smoke_report.json。",
    )
    inspect_real.add_argument("--report", required=True, help="real_provider_smoke_report.json 路径。")
    inspect_real.add_argument(
        "--allow-skip-without-credentials",
        action="store_true",
        help="无凭证时允许结构化 skip。",
    )
    inspect_real.add_argument(
        "--require-accepted-with-credentials",
        action="store_true",
        help="报告显示有凭证时要求 accepted 或 fallback_success。",
    )

    workspace_backend_status = subparsers.add_parser(
        "workspace-backend-status",
        help="生成 Stage 14 docker_stage_status.json。",
    )
    workspace_backend_status.add_argument("--output", required=True, help="docker_stage_status.json 输出路径。")
    workspace_backend_status.add_argument(
        "--mode",
        required=True,
        choices=["interface-only", "docker-backend"],
        help="Stage 14 完成方式；写入 JSON 时映射为 interface_only 或 docker_backend。",
    )

    inspect_workspace_backend = subparsers.add_parser(
        "inspect-workspace-backend",
        help="只读检查 Stage 14 docker_stage_status.json。",
    )
    inspect_workspace_backend.add_argument("--status-file", required=True, help="docker_stage_status.json 路径。")
    inspect_workspace_backend.add_argument("--assert-interface-only", action="store_true", help="要求 interface_only 验收通过。")
    inspect_workspace_backend.add_argument("--assert-docker-backend", action="store_true", help="要求 docker_backend 验收通过。")
    inspect_workspace_backend.add_argument("--assert-stage-complete", action="store_true", help="要求 Stage 14 在任一允许模式下完成。")

    feedback_policy = subparsers.add_parser(
        "inspect-feedback-policy-coverage",
        help="生成并检查 Stage 15 feedback policy 覆盖报告。",
    )
    feedback_policy.add_argument("--experiment-dir", required=True, help="Stage 13 或最终 task set experiment 目录。")
    feedback_policy.add_argument("--output", required=True, help="feedback_policy_report.json 输出路径。")
    feedback_policy.add_argument("--assert-complete", action="store_true", help="要求 feedback policy 覆盖完整。")

    build_acceptance = subparsers.add_parser(
        "build-v2-acceptance-report",
        help="汇总既有机器产物，生成全局 v2_acceptance_report.json。",
    )
    build_acceptance.add_argument("--v1-regression-dir", required=True, help="第一版 replay 回归 runs 目录。")
    build_acceptance.add_argument("--task-set-manifest", required=True, help="Stage 13 task set experiment_manifest.json。")
    build_acceptance.add_argument("--mock-provider-report", required=True, help="mock_provider_smoke_report.json。")
    build_acceptance.add_argument("--real-provider-report", required=True, help="real_provider_smoke_report.json。")
    build_acceptance.add_argument("--feedback-policy-report", required=True, help="feedback_policy_report.json。")
    build_acceptance.add_argument(
        "--export-audit-root",
        action="append",
        default=[],
        help="包含规范 export audit directories 的 exports 根目录；可重复传入。",
    )
    build_acceptance.add_argument("--docker-status", required=True, help="docker_stage_status.json。")
    build_acceptance.add_argument("--output", required=True, help="v2_acceptance_report.json 输出路径。")

    inspect_acceptance = subparsers.add_parser(
        "inspect-v2-acceptance",
        help="只读检查全局 v2_acceptance_report.json。",
    )
    inspect_acceptance.add_argument("report", help="v2_acceptance_report.json 路径。")
    inspect_acceptance.add_argument("--assert-complete", action="store_true", help="要求第二版最终验收完成。")

    prepare_v3_fixture = subparsers.add_parser(
        "prepare-v3-swebench-fixture",
        help="把 V3 前置 SWE-Bench-like 可实现性实验冻结为受版本控制输入。",
    )
    prepare_v3_fixture.add_argument("--feasibility-root", required=True, help="V3 SWE feasibility 实验目录。")
    prepare_v3_fixture.add_argument("--fixture-dir", required=True, help="V3 fixture 根目录。")
    prepare_v3_fixture.add_argument("--evidence-dir", required=True, help="V3 evaluator-only evidence 根目录。")

    inspect_v3_fixture = subparsers.add_parser(
        "inspect-v3-swebench-fixture",
        help="只读检查 V3 SWE-Bench-like 固定输入和 evaluator-only evidence。",
    )
    inspect_v3_fixture.add_argument("--fixture-dir", required=True, help="V3 fixture 根目录。")
    inspect_v3_fixture.add_argument("--evidence-dir", required=True, help="V3 evaluator-only evidence 根目录。")
    inspect_v3_fixture.add_argument("--manifest", required=True, help="v3_feasibility_input_manifest.json 路径。")
    inspect_v3_fixture.add_argument("--assert-frozen", action="store_true", help="要求固定输入完整且无 adapter 污染。")

    build_v3_tasks = subparsers.add_parser(
        "build-v3-task-set",
        help="读取 V3 真实仓库任务输入和固定 SWE-Bench-like JSONL，生成 task adapter facts。",
    )
    build_v3_tasks.add_argument("--real-repository-inputs", required=True, help="真实仓库任务输入 JSON。")
    build_v3_tasks.add_argument("--swebench-fixture-dir", required=True, help="阶段 0 SWE-Bench-like fixture 根目录。")
    build_v3_tasks.add_argument("--swebench-manifest", required=True, help="阶段 0 task_input_manifest.json。")
    build_v3_tasks.add_argument("--swebench-evidence-dir", required=True, help="阶段 0 evaluator-only evidence 根目录。")
    build_v3_tasks.add_argument("--output-dir", required=True, help="V3 task adapter 产物目录。")

    inspect_v3_tasks = subparsers.add_parser(
        "inspect-v3-task-set",
        help="只读检查 V3 真实仓库和 SWE-Bench-like task adapter 产物。",
    )
    inspect_v3_tasks.add_argument("run_dir", help="包含 task_adapter_facts.json 的目录。")
    inspect_v3_tasks.add_argument("--assert-complete", action="store_true", help="要求 V3 task set 完整。")

    build_v3_sources = subparsers.add_parser(
        "build-v3-source-materialization",
        help="从固定本地 archive/mirror materialize V3 source 并准备 verifier workspace。",
    )
    build_v3_sources.add_argument("--task-set-dir", required=True, help="阶段 4 task set 产物目录。")
    build_v3_sources.add_argument("--swebench-source-manifest", required=True, help="SWE-Bench-like 固定源码 archive manifest。")
    build_v3_sources.add_argument("--hidden-verifier-inputs", required=True, help="阶段 0 evaluator-only hidden verifier inputs JSONL。")
    build_v3_sources.add_argument("--output-dir", required=True, help="source materialization 产物目录。")

    inspect_v3_sources = subparsers.add_parser(
        "inspect-v3-source-materialization",
        help="只读检查 V3 source materialization 产物。",
    )
    inspect_v3_sources.add_argument("run_dir", help="source materialization 产物目录。")
    inspect_v3_sources.add_argument("--report", required=True, help="source_materialization_report.json 路径。")
    inspect_v3_sources.add_argument("--assert-complete", action="store_true", help="要求 source materialization 完整。")

    build_swebench_like = subparsers.add_parser(
        "build-v3-swebench-like",
        help="生成 SWE-Bench-like verifier plan 并运行 RepoHarness 自有 F2P/P2P verifier。",
    )
    build_swebench_like.add_argument("--source-materialization-run", required=True, help="阶段 5 source materialization 目录。")
    build_swebench_like.add_argument("--hidden-verifier-inputs", required=True, help="阶段 0 evaluator-only hidden verifier inputs JSONL。")
    build_swebench_like.add_argument("--gold-patch-predictions", required=True, help="阶段 0 evaluator-only gold patch predictions JSONL。")
    build_swebench_like.add_argument("--output-dir", required=True, help="SWE-Bench-like verifier 产物目录。")
    build_swebench_like.add_argument("--skip-execute", action="store_true", help="只生成结构，不执行 verifier；仅用于负例测试。")

    inspect_swebench = subparsers.add_parser(
        "inspect-swebench-like",
        help="检查 SWE-Bench-like verifier plan 和 RepoHarness 自有 verifier evidence。",
    )
    inspect_swebench.add_argument("run_dir", help="SWE-Bench-like verifier 产物目录。")
    inspect_swebench.add_argument("--manifest", required=True, help="swebench_like_task_manifest.json 路径。")
    inspect_swebench.add_argument("--assert-complete", action="store_true", help="要求 verifier plan 和 evidence 完整。")

    build_v3_agent_loop = subparsers.add_parser(
        "build-v3-agent-loop-integration",
        help="运行 V3 Stage 7 Agent Loop 集成 smoke，并生成污染扫描报告。",
    )
    build_v3_agent_loop.add_argument("--source-materialization-run", required=True, help="阶段 5 source materialization 目录。")
    build_v3_agent_loop.add_argument("--swebench-like-run", required=True, help="阶段 6 SWE-Bench-like verifier 目录。")
    build_v3_agent_loop.add_argument("--output-dir", required=True, help="Stage 7 Agent Loop 集成产物目录。")
    build_v3_agent_loop.add_argument("--real-task-id", default="realrepo_local_buggy_calculator", help="真实仓库任务 id。")
    build_v3_agent_loop.add_argument("--swebench-task-id", default="pytest-dev__pytest-7220", help="SWE-Bench-like 任务 id。")

    inspect_v3_agent_loop = subparsers.add_parser(
        "inspect-v3-agent-loop-integration",
        help="只读检查 V3 Stage 7 Agent Loop 集成报告。",
    )
    inspect_v3_agent_loop.add_argument("run_dir", help="Stage 7 Agent Loop 集成产物目录。")
    inspect_v3_agent_loop.add_argument("--report", required=True, help="v3_agent_loop_integration_report.json 路径。")
    inspect_v3_agent_loop.add_argument("--assert-complete", action="store_true", help="要求 Stage 7 Agent Loop 集成完整。")

    build_v3_resume = subparsers.add_parser(
        "build-v3-experiment-resume",
        help="构造 V3 Stage 8 可恢复实验、中断注入和 resume evidence。",
    )
    build_v3_resume.add_argument("--config", required=True, help="ExperimentConfig YAML 文件路径。")
    build_v3_resume.add_argument("--output-dir", required=True, help="Stage 8 experiment resume 产物目录。")
    build_v3_resume.add_argument(
        "--inject-interrupt-after",
        choices=["baseline", "agent_loop", "final_verifier"],
        default="baseline",
        help="固定中断注入点。",
    )

    inspect_resume = subparsers.add_parser(
        "inspect-experiment-resume",
        help="只读检查 V3 experiment resume manifest、checkpoint 和中断诊断。",
    )
    inspect_resume.add_argument("run_dir", help="Stage 8 experiment resume 产物目录。")
    inspect_resume.add_argument("--manifest", required=True, help="experiment_resume_manifest.json 路径。")
    inspect_resume.add_argument("--assert-resumable", action="store_true", help="要求 resume evidence 完整。")

    build_v3_context = subparsers.add_parser(
        "build-v3-context-diagnostics",
        help="构造 V3 Stage 9 context compaction 和 long rollout diagnostics evidence。",
    )
    build_v3_context.add_argument("--output-dir", required=True, help="Stage 9 context diagnostics 产物目录。")
    build_v3_context.add_argument(
        "--task-path",
        default="tests/fixtures/tasks/task_001.yaml",
        help="用于 Stage 9 long-output replay 的任务 YAML。",
    )

    inspect_context = subparsers.add_parser(
        "inspect-context-report",
        help="只读检查 V3 context_compaction_report.json。",
    )
    inspect_context.add_argument("run_dir", help="Stage 9 context diagnostics 产物目录。")
    inspect_context.add_argument("--report", required=True, help="context_compaction_report.json 路径。")
    inspect_context.add_argument("--assert-consistent", action="store_true", help="要求 compaction evidence 一致。")

    inspect_long_rollout = subparsers.add_parser(
        "inspect-long-rollout-diagnostics",
        help="只读检查 V3 long_rollout_diagnostics.json。",
    )
    inspect_long_rollout.add_argument("run_dir", help="Stage 9 context diagnostics 产物目录。")
    inspect_long_rollout.add_argument("--report", required=True, help="long_rollout_diagnostics.json 路径。")
    inspect_long_rollout.add_argument("--assert-complete", action="store_true", help="要求 long rollout diagnostics 完整。")

    build_v3_failure = subparsers.add_parser(
        "build-v3-reward-diagnostics",
        help="构造 V3 Stage 10 core failure diagnostics 和 filtering evidence。",
    )
    build_v3_failure.add_argument("--run-dir", required=True, help="已有 RepoHarness run directory。")
    build_v3_failure.add_argument("--output-dir", required=True, help="Stage 10 failure diagnostics 产物目录。")
    build_v3_failure.add_argument("--context-report", default=None, help="可选 context_compaction_report.json。")
    build_v3_failure.add_argument("--long-rollout-report", default=None, help="可选 long_rollout_diagnostics.json。")

    inspect_reward = subparsers.add_parser(
        "inspect-reward-diagnostics",
        help="只读检查 V3 failure_diagnostics_core_report.json 和 failure_distribution_report.json。",
    )
    inspect_reward.add_argument("run_dir", help="Stage 10 failure diagnostics 产物目录。")
    inspect_reward.add_argument("--core-report", required=True, help="failure_diagnostics_core_report.json 路径。")
    inspect_reward.add_argument("--distribution-report", required=True, help="failure_distribution_report.json 路径。")
    inspect_reward.add_argument("--assert-core-complete", action="store_true", help="要求核心失败诊断字段完整。")

    build_v3_export = subparsers.add_parser(
        "build-v3-export-audit",
        help="构造 V3 Stage 11 export audit 和 preference baseline evidence。",
    )
    build_v3_export.add_argument("--run-dir", action="append", required=True, help="需要导出的已有 run directory；可重复。")
    build_v3_export.add_argument("--output-dir", required=True, help="Stage 11 export audit 产物目录。")
    build_v3_export.add_argument("--preference-runs-dir", default=None, help="可选同条件 preference baseline runs 目录。")

    inspect_v3_export = subparsers.add_parser(
        "inspect-v3-export-audit",
        help="只读检查 V3 export_manifest.json 和 audit_report.json。",
    )
    inspect_v3_export.add_argument("run_dir", help="Stage 11 export audit 产物目录。")
    inspect_v3_export.add_argument("--manifest", required=True, help="V3 export_manifest.json 路径。")
    inspect_v3_export.add_argument("--audit-report", required=True, help="V3 audit_report.json 路径。")
    inspect_v3_export.add_argument("--assert-clean", action="store_true", help="要求 V3 export audit 无结构或污染失败。")

    inspect_trajectory = subparsers.add_parser(
        "inspect-trajectory-store",
        help="只读检查 V3 run trajectory store 的 transcript/events/artifacts/facts 可读性。",
    )
    inspect_trajectory.add_argument("run_dir", help="run directory 路径。")
    inspect_trajectory.add_argument("--assert-readable", action="store_true", help="要求 trajectory store 完整可读。")

    inspect_tool = subparsers.add_parser(
        "inspect-tool-contract",
        help="只读检查 V3 tool contract、tool schema snapshot 和 policy snapshot 冻结事实。",
    )
    inspect_tool.add_argument("run_dir", help="run directory 路径。")
    inspect_tool.add_argument("--assert-frozen", action="store_true", help="要求 tool contract 和 policy facts 已冻结。")

    build_run_selection = subparsers.add_parser(
        "build-v3-run-selection-manifest",
        help="构建显式 typed V3 run selection manifest，不读取 latest run。",
    )
    build_run_selection.add_argument(
        "--run-ref",
        action="append",
        required=True,
        help="显式 run 引用，格式 role=ROLE,path=PATH，可附加 run_state、accepted、structured_skip_reason；可重复。",
    )
    build_run_selection.add_argument("--output", required=True, help="RUN_SELECTION_MANIFEST 输出路径。")

    build_acceptance_inputs = subparsers.add_parser(
        "build-v3-acceptance-inputs",
        help="构建显式 V3 ACCEPTANCE_INPUTS manifest。",
    )
    build_acceptance_inputs.add_argument("--run-selection-manifest", required=True, help="RUN_SELECTION_MANIFEST 路径。")
    build_acceptance_inputs.add_argument("--export-root", required=True, help="V3 export audit 根目录。")
    build_acceptance_inputs.add_argument("--v2-report", required=True, help="V2 final acceptance report 路径。")
    build_acceptance_inputs.add_argument(
        "--pre-acceptance-doc",
        action="append",
        required=True,
        help="pre-acceptance 文档路径；可重复。",
    )
    build_acceptance_inputs.add_argument("--documentation-manifest", default=None, help="pre-acceptance 阶段日志和审查文档 manifest。")
    build_acceptance_inputs.add_argument("--command-log", default=None, help="pre-acceptance command_log.jsonl 路径。")
    build_acceptance_inputs.add_argument("--test-evidence", default=None, help="pre-acceptance 测试 evidence 目录或 manifest。")
    build_acceptance_inputs.add_argument("--output", required=True, help="ACCEPTANCE_INPUTS 输出路径。")

    build_acceptance_report = subparsers.add_parser(
        "build-v3-acceptance-report",
        help="从 ACCEPTANCE_INPUTS 构建 fresh V3 acceptance report。",
    )
    build_acceptance_report.add_argument("--acceptance-dir", required=True, help="不存在的新 ACCEPTANCE_DIR。")
    build_acceptance_report.add_argument("--input-manifest", required=True, help="ACCEPTANCE_INPUTS 路径。")
    build_acceptance_report.add_argument("--output", required=True, help="v3_acceptance_report.json 输出路径。")

    inspect_v3_acceptance_parser = subparsers.add_parser(
        "inspect-v3-acceptance",
        help="只读检查 V3 acceptance report 和所有绑定 evidence。",
    )
    inspect_v3_acceptance_parser.add_argument("report", help="v3_acceptance_report.json 路径。")
    inspect_v3_acceptance_parser.add_argument("--assert-complete", action="store_true", help="要求 V3 acceptance 完整通过。")

    build_acceptance_bundle = subparsers.add_parser(
        "build-v3-acceptance-bundle",
        help="绑定 post-acceptance 文档并构建 acceptance bundle manifest。",
    )
    build_acceptance_bundle.add_argument("--acceptance-dir", required=True, help="ACCEPTANCE_DIR 路径。")
    build_acceptance_bundle.add_argument("--input-manifest", required=True, help="ACCEPTANCE_INPUTS 路径。")
    build_acceptance_bundle.add_argument("--report", required=True, help="v3_acceptance_report.json 路径。")
    build_acceptance_bundle.add_argument(
        "--documentation-ref",
        action="append",
        required=True,
        help="post-acceptance 文档路径；可重复。",
    )
    build_acceptance_bundle.add_argument("--output", required=True, help="acceptance_bundle_manifest.json 输出路径。")

    inspect_bundle = subparsers.add_parser(
        "inspect-acceptance-bundle",
        help="只读检查 acceptance bundle manifest 不可变性。",
    )
    inspect_bundle.add_argument("manifest", help="acceptance_bundle_manifest.json 路径。")
    inspect_bundle.add_argument("--final-command-log", help="V5 final acceptance command log 路径。")
    inspect_bundle.add_argument("--assert-immutable", action="store_true", help="要求 bundle refs sha256 全部匹配。")

    build_v4_inputs = subparsers.add_parser(
        "build-v4-implementation-inputs",
        help="构建 V4 阶段 0 implementation input freeze 机器产物。",
    )
    build_v4_inputs.add_argument("--pr-issue-run", required=True, help="V4 PR / issue feasibility run 根目录。")
    build_v4_inputs.add_argument("--public-swebench-run", required=True, help="V4 public SWE-Bench-like feasibility run 根目录。")
    build_v4_inputs.add_argument("--output-dir", required=True, help="Stage 0 implementation input 产物目录。")
    build_v4_inputs.add_argument("--v2-acceptance", required=True, help="V2 acceptance report 路径。")
    build_v4_inputs.add_argument("--v3-acceptance", required=True, help="V3 acceptance report 路径。")
    build_v4_inputs.add_argument("--v3-acceptance-bundle", required=True, help="V3 acceptance bundle manifest 路径。")
    build_v4_inputs.add_argument("--baseline-commit", default="f38cb93", help="V4 planning baseline commit。")
    build_v4_inputs.add_argument("--v3-closure-commit", default="17b1b95", help="V3 closure commit。")
    build_v4_inputs.add_argument(
        "--run-live-baseline-checks",
        action="store_true",
        help="在写入 Stage 0 产物前运行正式 baseline、acceptance 和 Docker 检查。",
    )
    build_v4_inputs.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        help="如果目标 Stage 0 输出已存在，则失败，避免覆盖 evidence。",
    )

    inspect_v4_inputs = subparsers.add_parser(
        "inspect-v4-implementation-inputs",
        help="只读检查 V4 阶段 0 implementation input manifest 和绑定 evidence。",
    )
    inspect_v4_inputs.add_argument("manifest", help="v4_implementation_input_manifest.json 路径。")
    inspect_v4_inputs.add_argument("--assert-complete", action="store_true", help="要求 Stage 0 input freeze 完整通过。")

    build_v4_task_freeze_parser = subparsers.add_parser(
        "build-v4-task-freeze",
        help="构建 V4 阶段 2 task source freeze 和 task adapter integration 产物。",
    )
    build_v4_task_freeze_parser.add_argument("--implementation-inputs", required=True, help="Stage 0 v4_implementation_input_manifest.json 路径。")
    build_v4_task_freeze_parser.add_argument("--output-dir", required=True, help="Stage 2 task freeze 产物目录。")
    build_v4_task_freeze_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        help="如果目标 Stage 2 输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v4_rollout_parser = subparsers.add_parser(
        "build-v4-rollout-orchestration",
        help="构建 V4 阶段 3 单机 rollout queue、lease、retry、budget、resource 和 resume 产物。",
    )
    build_v4_rollout_parser.add_argument("--task-freeze", required=True, help="Stage 2 task_freeze_manifest.json 路径。")
    build_v4_rollout_parser.add_argument("--output-dir", required=True, help="Stage 3 rollout orchestration 产物目录。")
    build_v4_rollout_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        help="如果目标 Stage 3 输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v4_tool_lifecycle_parser = subparsers.add_parser(
        "build-v4-tool-lifecycle",
        help="构建 V4 阶段 4 audit-only permission、hook、MCP 和 tool lifecycle 产物。",
    )
    build_v4_tool_lifecycle_parser.add_argument("--output-dir", required=True, help="Stage 4 tool lifecycle 产物目录。")
    build_v4_tool_lifecycle_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        help="如果目标 Stage 4 输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v4_agent_run_parser = subparsers.add_parser(
        "build-v4-agent-run-integration",
        help="构建 V4 阶段 5 Agent run integration 和 trajectory store 产物。",
    )
    build_v4_agent_run_parser.add_argument("--output-dir", required=True, help="Stage 5 agent run integration 产物目录。")
    build_v4_agent_run_parser.add_argument("--task-freeze", required=True, help="Stage 2 task_freeze_manifest.json 或 task freeze 产物目录。")
    build_v4_agent_run_parser.add_argument("--tool-lifecycle", required=True, help="Stage 4 tool lifecycle 产物目录或 tool contract snapshot。")
    build_v4_agent_run_parser.add_argument("--rollout-queue", required=True, help="Stage 3 rollout_queue_manifest.json 或 rollout 产物目录。")
    build_v4_agent_run_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        help="如果目标 Stage 5 输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v4_export_quality_parser = subparsers.add_parser(
        "build-v4-export-quality",
        help="构建 V4 阶段 6 export quality、packing、failure 和 reward audit 产物。",
    )
    build_v4_export_quality_parser.add_argument("--output-dir", required=True, help="Stage 6 export quality 产物目录。")
    build_v4_export_quality_parser.add_argument("--agent-run-integration", required=True, help="Stage 5 agent run integration 产物目录或 trajectory_store_integrity_report.json。")
    build_v4_export_quality_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        help="如果目标 Stage 6 输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v4_cards_parser = subparsers.add_parser(
        "build-v4-cards",
        help="构建 V4 阶段 7 dataset、run、export cards 和 provenance 产物。",
    )
    build_v4_cards_parser.add_argument("--output-dir", required=True, help="Stage 7 cards 产物目录。")
    build_v4_cards_parser.add_argument("--task-freeze", required=True, help="Stage 2 task_freeze_manifest.json 或 task freeze 产物目录。")
    build_v4_cards_parser.add_argument("--agent-run-integration", required=True, help="Stage 5 agent run integration 产物目录或 report。")
    build_v4_cards_parser.add_argument("--export-quality", required=True, help="Stage 6 export quality 产物目录或 trajectory_quality_manifest.json。")
    build_v4_cards_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        help="如果目标 Stage 7 输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v4_run_selection_parser = subparsers.add_parser(
        "build-v4-run-selection-manifest",
        help="构建 V4 final acceptance run selection manifest。",
    )
    build_v4_run_selection_parser.add_argument("--query", required=True, help="V4_QUERY_SPEC.json 路径。")
    build_v4_run_selection_parser.add_argument("--output", required=True, help="run_selection_manifest.json 输出路径。")
    build_v4_run_selection_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v4_inputs_parser = subparsers.add_parser(
        "build-v4-acceptance-inputs",
        help="构建 V4 final acceptance explicit inputs manifest。",
    )
    build_v4_inputs_parser.add_argument("--run-selection", required=True)
    build_v4_inputs_parser.add_argument("--v2-acceptance", required=True)
    build_v4_inputs_parser.add_argument("--v3-acceptance", required=True)
    build_v4_inputs_parser.add_argument("--v3-acceptance-bundle", required=True)
    build_v4_inputs_parser.add_argument("--real-repository-regression", required=True)
    build_v4_inputs_parser.add_argument("--swebench-like-regression", required=True)
    build_v4_inputs_parser.add_argument("--implementation-inputs", required=True)
    build_v4_inputs_parser.add_argument("--rollout-queue", required=True)
    build_v4_inputs_parser.add_argument("--lease-state", required=True)
    build_v4_inputs_parser.add_argument("--retry-policy", required=True)
    build_v4_inputs_parser.add_argument("--budget-control", required=True)
    build_v4_inputs_parser.add_argument("--resource-locks", required=True)
    build_v4_inputs_parser.add_argument("--resource-usage", required=True)
    build_v4_inputs_parser.add_argument("--batch-resume", required=True)
    build_v4_inputs_parser.add_argument("--run-selection-query", required=True)
    build_v4_inputs_parser.add_argument("--task-freeze", required=True)
    build_v4_inputs_parser.add_argument("--task-validity", required=True)
    build_v4_inputs_parser.add_argument("--tool-contract", required=True)
    build_v4_inputs_parser.add_argument("--tool-lifecycle", required=True)
    build_v4_inputs_parser.add_argument("--agent-run-integration", required=True)
    build_v4_inputs_parser.add_argument("--trajectory-store", required=True)
    build_v4_inputs_parser.add_argument("--export-quality", required=True)
    build_v4_inputs_parser.add_argument("--cards", required=True)
    build_v4_inputs_parser.add_argument("--contamination-scan", required=True)
    build_v4_inputs_parser.add_argument("--command-log", required=True)
    build_v4_inputs_parser.add_argument("--pre-acceptance-doc", action="append", default=[], help="可重复提供的 pre-acceptance 文档。")
    build_v4_inputs_parser.add_argument("--output", required=True)
    build_v4_inputs_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v4_report_parser = subparsers.add_parser(
        "build-v4-acceptance-report",
        help="构建 V4 final acceptance report。",
    )
    build_v4_report_parser.add_argument("--acceptance-inputs", required=True)
    build_v4_report_parser.add_argument("--output", required=True)
    build_v4_report_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标 acceptance evidence 已存在，则失败。",
    )

    build_v4_bundle_parser = subparsers.add_parser(
        "build-v4-acceptance-bundle",
        help="构建 V4 final acceptance bundle manifest。",
    )
    build_v4_bundle_parser.add_argument("--acceptance-report", required=True)
    build_v4_bundle_parser.add_argument("--final-command-log", required=True)
    build_v4_bundle_parser.add_argument("--documentation-ref", action="append", default=[], help="可重复提供的 post-acceptance 文档。")
    build_v4_bundle_parser.add_argument("--output", required=True)
    build_v4_bundle_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标 bundle 已存在，则失败。",
    )

    inspect_v4_acceptance_inputs = subparsers.add_parser(
        "inspect-v4-inputs",
        help="只读检查 V4 final acceptance inputs skeleton。",
    )
    inspect_v4_acceptance_inputs.add_argument("manifest", help="v4_acceptance_inputs.json 路径。")
    inspect_v4_acceptance_inputs.add_argument("--assert-complete", action="store_true", help="要求 V4 acceptance inputs 完整。")

    for command_name, help_text in (
        ("inspect-rollout-queue", "只读检查 V4 rollout queue skeleton。"),
        ("inspect-rollout-leases", "只读检查 V4 rollout lease skeleton。"),
        ("inspect-rollout-retry", "只读检查 V4 rollout retry skeleton。"),
        ("inspect-rollout-budget", "只读检查 V4 rollout budget skeleton。"),
        ("inspect-resource-locks", "只读检查 V4 resource lock skeleton。"),
        ("inspect-resource-usage", "只读检查 V4 resource usage skeleton。"),
        ("inspect-rollout-resume", "只读检查 V4 rollout resume skeleton。"),
        ("inspect-v4-tool-lifecycle", "只读检查 V4 tool lifecycle skeleton。"),
        ("inspect-v4-agent-run-integration", "只读检查 V4 agent run integration skeleton。"),
        ("inspect-v4-export-quality", "只读检查 V4 export quality skeleton。"),
        ("inspect-v4-cards", "只读检查 V4 cards skeleton。"),
    ):
        skeleton = subparsers.add_parser(command_name, help=help_text)
        skeleton.add_argument("path", help="显式输入路径。")
        skeleton.add_argument("--assert-complete", action="store_true", help="要求 skeleton 产物完整。")

    inspect_run_selection_query = subparsers.add_parser(
        "inspect-run-selection-query",
        help="只读检查 V4 run selection query report skeleton。",
    )
    inspect_run_selection_query.add_argument("path", help="run_selection_query_report.json 路径。")
    inspect_run_selection_query.add_argument("--assert-complete", action="store_true", help="要求 skeleton 产物完整。")

    inspect_v4_task_freeze = subparsers.add_parser(
        "inspect-v4-task-freeze",
        help="只读检查 V4 task freeze manifest skeleton。",
    )
    inspect_v4_task_freeze.add_argument("path", help="TASK_FREEZE_MANIFEST.json 路径。")
    inspect_v4_task_freeze.add_argument("--assert-complete", action="store_true", help="要求 skeleton 产物完整。")

    inspect_v4_task_validity = subparsers.add_parser(
        "inspect-v4-task-validity",
        help="只读检查 V4 task validity report skeleton。",
    )
    inspect_v4_task_validity.add_argument("path", help="TASK_VALIDITY_REPORT.json 路径。")
    inspect_v4_task_validity.add_argument("--assert-complete", action="store_true", help="要求 skeleton 产物完整。")

    inspect_v4_tool_contract = subparsers.add_parser(
        "inspect-v4-tool-contract",
        help="只读检查 V4 tool contract skeleton。",
    )
    inspect_v4_tool_contract.add_argument("path", help="RUN_DIR 路径。")
    inspect_v4_tool_contract.add_argument("--assert-frozen", action="store_true", help="要求 V4 tool contract 冻结。")

    inspect_v4_trajectory = subparsers.add_parser(
        "inspect-v4-trajectory-store",
        help="只读检查 V4 trajectory store skeleton。",
    )
    inspect_v4_trajectory.add_argument("path", help="RUN_DIR 路径。")
    inspect_v4_trajectory.add_argument("--assert-readable", action="store_true", help="要求 V4 trajectory store 可读。")

    inspect_v4_scan = subparsers.add_parser(
        "inspect-v4-contamination-scan",
        help="只读检查 V4 contamination scan skeleton。",
    )
    inspect_v4_scan.add_argument("path", help="SCAN_REPORT.json 路径。")
    inspect_v4_scan.add_argument("--assert-clean", action="store_true", help="要求污染扫描 clean。")

    inspect_v4_acceptance_parser = subparsers.add_parser(
        "inspect-v4-acceptance",
        help="只读检查 V4 acceptance report skeleton。",
    )
    inspect_v4_acceptance_parser.add_argument("report", help="v4_acceptance_report.json 路径。")
    inspect_v4_acceptance_parser.add_argument("--assert-complete", action="store_true", help="要求 V4 acceptance 完整通过。")

    build_v5_preimplementation_parser = subparsers.add_parser(
        "build-v5-preimplementation",
        help="构建 V5 Stage 0 preimplementation baseline 和 preflight input binding。",
    )
    build_v5_preimplementation_parser.add_argument("--output-dir", required=True)
    build_v5_preimplementation_parser.add_argument("--v2-acceptance-report", required=True)
    build_v5_preimplementation_parser.add_argument("--v3-acceptance-report", required=True)
    build_v5_preimplementation_parser.add_argument("--v3-acceptance-bundle", required=True)
    build_v5_preimplementation_parser.add_argument("--v4-acceptance-inputs", required=True)
    build_v5_preimplementation_parser.add_argument("--v4-acceptance-report", required=True)
    build_v5_preimplementation_parser.add_argument("--v4-doc-sync-acceptance-bundle", required=True)
    build_v5_preimplementation_parser.add_argument("--v4-doc-sync-final-command-log", required=True)
    build_v5_preimplementation_parser.add_argument("--preflight-root", required=True)
    build_v5_preimplementation_parser.add_argument("--preflight-flaky-probe-report", required=True)
    build_v5_preimplementation_parser.add_argument("--preflight-visibility-probe-summary", required=True)
    build_v5_preimplementation_parser.add_argument("--preflight-run-matrix-manifest", required=True)
    build_v5_preimplementation_parser.add_argument("--preflight-task-selection-report", required=True)
    build_v5_preimplementation_parser.add_argument("--preflight-resume-claim-gate-report", required=True)
    build_v5_preimplementation_parser.add_argument("--preflight-evidence-manifest", required=True)
    build_v5_preimplementation_parser.add_argument("--baseline-commit", default="9fd7007")
    build_v5_preimplementation_parser.add_argument("--v4-closure-commit", default="e0da89c")
    build_v5_preimplementation_parser.add_argument(
        "--baseline-command-cwd",
        help="显式指定执行 Stage 0 baseline 命令的干净 worktree；默认使用当前目录。",
    )
    build_v5_preimplementation_parser.add_argument(
        "--run-live-baseline-checks",
        action="store_true",
        help="实际执行 Stage 0 baseline 命令。最终 Stage 0 产物必须启用。",
    )
    build_v5_preimplementation_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    inspect_v5_preimplementation_parser = subparsers.add_parser(
        "inspect-v5-preimplementation",
        help="只读检查 V5 Stage 0 preflight input binding。",
    )
    inspect_v5_preimplementation_parser.add_argument("binding", help="v5_preflight_input_binding.json 路径。")
    inspect_v5_preimplementation_parser.add_argument("--assert-complete", action="store_true", help="要求 V5 Stage 0 输入完整。")

    build_v5_schema_fixtures_parser = subparsers.add_parser(
        "build-v5-schema-fixtures",
        help="构建 V5 Stage 1 schema fixtures、tracking table 和 lineage schema report。",
    )
    build_v5_schema_fixtures_parser.add_argument("--output-dir", required=True)
    build_v5_schema_fixtures_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_evidence_integrity_parser = subparsers.add_parser(
        "build-v5-evidence-integrity",
        help="构建 V5 pre-acceptance evidence integrity report。",
    )
    build_v5_evidence_integrity_parser.add_argument("--critical-evidence-manifest", required=True)
    build_v5_evidence_integrity_parser.add_argument("--pre-acceptance-command-log", required=True)
    build_v5_evidence_integrity_parser.add_argument("--output", required=True)
    build_v5_evidence_integrity_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    inspect_v5_evidence_integrity_parser = subparsers.add_parser(
        "inspect-v5-evidence-integrity",
        help="只读检查 V5 pre-acceptance evidence integrity report。",
    )
    inspect_v5_evidence_integrity_parser.add_argument("report", help="v5_pre_acceptance_evidence_integrity_report.json 路径。")
    inspect_v5_evidence_integrity_parser.add_argument("--assert-complete", action="store_true", help="要求 V5 pre-acceptance evidence integrity 完整通过。")

    build_v5_task_set_parser = subparsers.add_parser(
        "build-v5-task-set",
        help="从显式 V5 preflight 输入构建 Stage 2A task set manifest。",
    )
    build_v5_task_set_parser.add_argument("--preflight-input-binding", required=True)
    build_v5_task_set_parser.add_argument("--adapter-visible-task-draft", required=True)
    build_v5_task_set_parser.add_argument("--evaluator-only-evidence-manifest", required=True)
    build_v5_task_set_parser.add_argument("--run-matrix-preflight-manifest", required=True)
    build_v5_task_set_parser.add_argument("--task-selection-preflight-report", required=True)
    build_v5_task_set_parser.add_argument("--visibility-scan-report", required=True)
    build_v5_task_set_parser.add_argument("--flaky-probe-report", required=True)
    build_v5_task_set_parser.add_argument("--source-materialization-report", action="append", required=True)
    build_v5_task_set_parser.add_argument("--output-dir", required=True)
    build_v5_task_set_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_supplemental_parser = subparsers.add_parser(
        "build-v5-supplemental-pr-issue-candidates",
        help="构建 V5 Stage 2B supplemental PR / issue candidate probe evidence。",
    )
    build_v5_supplemental_parser.add_argument("--candidate-id", action="append", required=True)
    build_v5_supplemental_parser.add_argument("--source-preflight-root", required=True)
    build_v5_supplemental_parser.add_argument("--output-dir", required=True)
    build_v5_supplemental_parser.add_argument("--max-accepted", type=int, default=2)
    build_v5_supplemental_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    merge_v5_task_set_parser = subparsers.add_parser(
        "merge-v5-task-set",
        help="合并 V5 Stage 2A initial task set 和 Stage 2B supplemental tasks。",
    )
    merge_v5_task_set_parser.add_argument("--base-task-set", required=True)
    merge_v5_task_set_parser.add_argument("--supplemental-report", required=True)
    merge_v5_task_set_parser.add_argument("--output", required=True)
    merge_v5_task_set_parser.add_argument("--output-inventory", required=True)
    merge_v5_task_set_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    inspect_v5_task_set_parser = subparsers.add_parser(
        "inspect-v5-task-set",
        help="只读检查 V5 task set manifest skeleton。",
    )
    inspect_v5_task_set_parser.add_argument("manifest", help="v5_task_set_manifest.json 路径。")
    inspect_v5_task_set_parser.add_argument("--assert-complete", action="store_true", help="要求 V5 task set 完整通过。")

    inspect_v5_task_visibility_parser = subparsers.add_parser(
        "inspect-v5-task-visibility",
        help="只读检查 V5 task visibility scan report skeleton。",
    )
    inspect_v5_task_visibility_parser.add_argument("report", help="v5_task_visibility_scan_report.json 路径。")
    inspect_v5_task_visibility_parser.add_argument("--assert-clean", action="store_true", help="要求 V5 task visibility scan 无泄漏。")

    build_v5_provider_gate_parser = subparsers.add_parser(
        "build-v5-provider-gate",
        help="构建 V5 Stage 3A provider registry、credential gate 和 provider smoke structured evidence。",
    )
    build_v5_provider_gate_parser.add_argument("--task-set-manifest", required=True)
    build_v5_provider_gate_parser.add_argument("--output-dir", required=True)
    build_v5_provider_gate_parser.add_argument(
        "--allow-local-secret-file",
        action="store_true",
        help="允许 DeepSeek 和 OpenAI 使用本地脱敏 secret file 作为 active credential source；报告仍不得写入 raw secret value。",
    )
    build_v5_provider_gate_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_provider_cost_budget_parser = subparsers.add_parser(
        "build-v5-provider-cost-budget",
        help="构建 V5 Stage 3A provider cost budget report。",
    )
    build_v5_provider_cost_budget_parser.add_argument("--provider-gate-report", required=True)
    build_v5_provider_cost_budget_parser.add_argument("--output", required=True)
    build_v5_provider_cost_budget_parser.add_argument("--max-real-provider-calls", type=int, default=24)
    build_v5_provider_cost_budget_parser.add_argument("--max-cost-usd", type=float, default=5.0)
    build_v5_provider_cost_budget_parser.add_argument("--actual-real-provider-calls", type=int, default=0)
    build_v5_provider_cost_budget_parser.add_argument("--actual-cost-proxy-usd", type=float, default=0.0)
    build_v5_provider_cost_budget_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_run_matrix_parser = subparsers.add_parser(
        "build-v5-run-matrix",
        help="构建 V5 Stage 3B DeepSeek primary run matrix manifest。",
    )
    build_v5_run_matrix_parser.add_argument("--task-set-manifest", required=True)
    build_v5_run_matrix_parser.add_argument("--provider-gate-report", required=True)
    build_v5_run_matrix_parser.add_argument("--provider-cost-budget-report", required=True)
    build_v5_run_matrix_parser.add_argument("--output-dir", required=True)
    build_v5_run_matrix_parser.add_argument("--task-id", action="append", default=None)
    build_v5_run_matrix_parser.add_argument(
        "--provider-id",
        action="append",
        default=None,
        help="显式选择 Stage 3B provider cell；可重复传入 deepseek 和 openai。默认只生成 deepseek。",
    )
    build_v5_run_matrix_parser.add_argument("--deepseek-model-id", default="deepseek-v4-flash")
    build_v5_run_matrix_parser.add_argument("--openai-model-id", default="gpt-5.4-nano")
    build_v5_run_matrix_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    run_v5_run_matrix_parser = subparsers.add_parser(
        "run-v5-run-matrix",
        help="执行 V5 Stage 3B DeepSeek primary run matrix cells。",
    )
    run_v5_run_matrix_parser.add_argument("--run-matrix-manifest", required=True)
    run_v5_run_matrix_parser.add_argument("--provider-cost-budget-report", required=True)
    run_v5_run_matrix_parser.add_argument("--output-dir", required=True)
    run_v5_run_matrix_parser.add_argument(
        "--allow-local-secret-file",
        action="store_true",
        help="允许 DeepSeek 和 OpenAI 使用本地脱敏 secret file 作为 active credential source；运行产物仍不得写入 raw secret value。",
    )
    run_v5_run_matrix_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    run_v5_accepted_provider_parser = subparsers.add_parser(
        "run-v5-accepted-provider-task",
        help="执行一个 V5 真实 provider 修复任务，并用 strict final verifier replay 生成 accepted-run evidence。",
    )
    run_v5_accepted_provider_parser.add_argument("--task-set-manifest", required=True)
    run_v5_accepted_provider_parser.add_argument("--provider-gate-report", required=True)
    run_v5_accepted_provider_parser.add_argument("--provider-cost-budget-report", required=True)
    run_v5_accepted_provider_parser.add_argument("--output-dir", required=True)
    run_v5_accepted_provider_parser.add_argument("--task-id", required=True)
    run_v5_accepted_provider_parser.add_argument("--provider-id", default="deepseek")
    run_v5_accepted_provider_parser.add_argument("--model-id", default="deepseek-v4-pro")
    run_v5_accepted_provider_parser.add_argument("--scaffold-id", default="patch_focused_react")
    run_v5_accepted_provider_parser.add_argument("--prior-executed-run-matrix-manifest")
    run_v5_accepted_provider_parser.add_argument(
        "--allow-local-secret-file",
        action="store_true",
        help="允许 DeepSeek 和 OpenAI 使用本地脱敏 secret file 作为 active credential source；运行产物仍不得写入 raw secret value。",
    )
    run_v5_accepted_provider_parser.add_argument("--max-turns", type=int, default=12)
    run_v5_accepted_provider_parser.add_argument("--max-tool-calls", type=int, default=40)
    run_v5_accepted_provider_parser.add_argument("--max-output-tokens", type=int, default=4096)
    run_v5_accepted_provider_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_comparison_reports_parser = subparsers.add_parser(
        "build-v5-comparison-reports",
        help="构建 V5 Stage 3C comparison reports 和阶段性 resume claim gate。",
    )
    build_v5_comparison_reports_parser.add_argument("--executed-run-matrix-manifest", required=True)
    build_v5_comparison_reports_parser.add_argument(
        "--additional-executed-run-matrix-manifest",
        action="append",
        default=None,
        help="额外绑定一个已执行 run matrix manifest，用于组合 DeepSeek 和 OpenAI provider comparison evidence。",
    )
    build_v5_comparison_reports_parser.add_argument("--provider-gate-report", required=True)
    build_v5_comparison_reports_parser.add_argument("--output-dir", required=True)
    build_v5_comparison_reports_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_export_pack_parser = subparsers.add_parser(
        "build-v5-export-pack",
        help="构建 V5 Stage 4 export result pack。",
    )
    build_v5_export_pack_parser.add_argument("--executed-run-matrix-manifest", required=True)
    build_v5_export_pack_parser.add_argument("--stage3-claim-gate-report", required=True)
    build_v5_export_pack_parser.add_argument("--output-dir", required=True)
    build_v5_export_pack_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_demo_artifacts_parser = subparsers.add_parser(
        "build-v5-demo-artifacts",
        help="构建 V5 Stage 5 interview demo card、public-safe bundle 和 result summary。",
    )
    build_v5_demo_artifacts_parser.add_argument("--task-set-manifest", required=True)
    build_v5_demo_artifacts_parser.add_argument("--executed-run-matrix-manifest", required=True)
    build_v5_demo_artifacts_parser.add_argument("--export-pack-manifest", required=True)
    build_v5_demo_artifacts_parser.add_argument("--stage4-claim-gate-report", required=True)
    build_v5_demo_artifacts_parser.add_argument("--provider-comparison-report")
    build_v5_demo_artifacts_parser.add_argument("--output-dir", required=True)
    build_v5_demo_artifacts_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_interview_result_pack_parser = subparsers.add_parser(
        "build-v5-interview-result-pack",
        help="构建 V5 Stage 5 interview result pack、简历模板和问答证据索引。",
    )
    build_v5_interview_result_pack_parser.add_argument("--resume-artifact-index", required=True)
    build_v5_interview_result_pack_parser.add_argument("--stage5-claim-gate-report", required=True)
    build_v5_interview_result_pack_parser.add_argument("--docs12-path", required=True)
    build_v5_interview_result_pack_parser.add_argument("--output-dir", required=True)
    build_v5_interview_result_pack_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_acceptance_inputs_parser = subparsers.add_parser(
        "build-v5-acceptance-inputs",
        help="构建 V5 Stage 6 acceptance inputs 和 final pretest report。",
    )
    build_v5_acceptance_inputs_parser.add_argument("--output-dir", required=True)
    for option in (
        "v2-acceptance-report",
        "v3-acceptance-report",
        "v3-acceptance-bundle",
        "v4-acceptance-inputs",
        "v4-acceptance-report",
        "v4-doc-sync-acceptance-bundle",
        "v4-doc-sync-final-command-log",
        "v5-baseline-check-report",
        "v5-v4-closure-report",
        "v5-documentation-sync-report",
        "v5-preflight-input-binding",
        "v5-pre-acceptance-evidence-integrity-report",
        "v5-task-set-manifest",
        "v5-task-inventory-report",
        "v5-task-diversity-report",
        "v5-task-visibility-scan-report",
        "v5-run-matrix-manifest",
        "v5-executed-run-matrix-manifest",
        "v5-matrix-compare-scope-report",
        "v5-provider-credential-gate-report",
        "v5-provider-cost-budget-report",
        "v5-resume-claim-gate-report",
        "v5-export-result-pack-manifest",
        "v5-preference-pair-blocked-report",
        "v5-failure-taxonomy-report",
        "v5-reward-source-taxonomy-report",
        "v5-interview-demo-card",
        "v5-canonical-demo-walkthrough",
        "v5-public-demo-bundle-manifest",
        "v5-resume-artifact-index",
        "v5-repro-command-index",
        "v5-result-summary-table",
        "v5-demo-transcript-index",
        "v5-permission-network-risk-audit-report",
        "v5-claude-code-invariant-mapping",
        "v5-interview-result-pack-manifest",
    ):
        build_v5_acceptance_inputs_parser.add_argument(f"--{option}", required=True)
    build_v5_acceptance_inputs_parser.add_argument("--v5-implementation-log", action="append", required=True)
    build_v5_acceptance_inputs_parser.add_argument("--v5-review-record", action="append", required=True)
    build_v5_acceptance_inputs_parser.add_argument("--v5-provider-comparison-report")
    build_v5_acceptance_inputs_parser.add_argument("--full-test-summary", required=True)
    build_v5_acceptance_inputs_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_acceptance_report_parser = subparsers.add_parser(
        "build-v5-acceptance-report",
        help="构建 V5 Stage 6 acceptance report。",
    )
    build_v5_acceptance_report_parser.add_argument("--acceptance-inputs", required=True)
    build_v5_acceptance_report_parser.add_argument("--output-dir", required=True)
    build_v5_acceptance_report_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_pre_bundle_command_log_parser = subparsers.add_parser(
        "build-v5-pre-bundle-command-log",
        help="合并 V5 Stage 6 pre-bundle command log。",
    )
    build_v5_pre_bundle_command_log_parser.add_argument("--base-command-log", required=True)
    build_v5_pre_bundle_command_log_parser.add_argument("--command-log-entry", action="append", required=True)
    build_v5_pre_bundle_command_log_parser.add_argument("--output", required=True)
    build_v5_pre_bundle_command_log_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_acceptance_bundle_parser = subparsers.add_parser(
        "build-v5-acceptance-bundle",
        help="构建 V5 acceptance bundle 或 doc-sync bundle。",
    )
    build_v5_acceptance_bundle_parser.add_argument("--acceptance-report", required=False)
    build_v5_acceptance_bundle_parser.add_argument("--post-report-inspect-output", required=False)
    build_v5_acceptance_bundle_parser.add_argument("--pre-bundle-command-log", required=False)
    build_v5_acceptance_bundle_parser.add_argument("--bundle-build-command-log-entry-output", required=True)
    build_v5_acceptance_bundle_parser.add_argument("--documentation-ref", action="append", required=True)
    build_v5_acceptance_bundle_parser.add_argument("--output", required=True)
    build_v5_acceptance_bundle_parser.add_argument("--doc-sync-from-bundle")
    build_v5_acceptance_bundle_parser.add_argument("--final-command-log")
    build_v5_acceptance_bundle_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    plan_acceptance_bundle_inspect_entry_parser = subparsers.add_parser(
        "plan-acceptance-bundle-inspect-entry",
        help="生成 V5 acceptance bundle inspect planned command entry。",
    )
    plan_acceptance_bundle_inspect_entry_parser.add_argument("--acceptance-bundle", required=True)
    plan_acceptance_bundle_inspect_entry_parser.add_argument("--final-command-log", required=True)
    plan_acceptance_bundle_inspect_entry_parser.add_argument(
        "--self-referential-acceptance-bundle",
        action="store_true",
        help="用于最终 bundle 自身绑定 final command log 的场景；此时 bundle hash 通过最终 manifest 闭环检查。",
    )
    plan_acceptance_bundle_inspect_entry_parser.add_argument("--output", required=True)
    plan_acceptance_bundle_inspect_entry_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    plan_acceptance_bundle_build_entry_parser = subparsers.add_parser(
        "plan-v5-acceptance-bundle-build-entry",
        help="生成 V5 最终 acceptance bundle build planned command entry。",
    )
    plan_acceptance_bundle_build_entry_parser.add_argument("--acceptance-report", required=True)
    plan_acceptance_bundle_build_entry_parser.add_argument("--post-report-inspect-output", required=True)
    plan_acceptance_bundle_build_entry_parser.add_argument("--pre-bundle-command-log", required=True)
    plan_acceptance_bundle_build_entry_parser.add_argument("--documentation-ref", action="append", required=True)
    plan_acceptance_bundle_build_entry_parser.add_argument("--bundle-build-command-log-entry-output", required=True)
    plan_acceptance_bundle_build_entry_parser.add_argument("--output-bundle", required=True)
    plan_acceptance_bundle_build_entry_parser.add_argument("--final-command-log", required=True)
    plan_acceptance_bundle_build_entry_parser.add_argument("--doc-sync-from-bundle")
    plan_acceptance_bundle_build_entry_parser.add_argument("--output", required=True)
    plan_acceptance_bundle_build_entry_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    build_v5_final_command_log_parser = subparsers.add_parser(
        "build-v5-final-command-log",
        help="构建 V5 final acceptance command log。",
    )
    build_v5_final_command_log_parser.add_argument("--pre-bundle-command-log", required=True)
    build_v5_final_command_log_parser.add_argument("--command-log-entry", action="append", required=True)
    build_v5_final_command_log_parser.add_argument("--output", required=True)
    build_v5_final_command_log_parser.add_argument(
        "--fail-if-output-exists",
        action="store_true",
        default=True,
        help="默认启用：如果目标输出已存在，则失败，避免覆盖 evidence。",
    )

    inspect_v5_run_matrix_parser = subparsers.add_parser(
        "inspect-v5-run-matrix",
        help="只读检查 V5 run matrix manifest skeleton。",
    )
    inspect_v5_run_matrix_parser.add_argument("manifest", help="v5_run_matrix_manifest.json 路径。")
    inspect_v5_run_matrix_parser.add_argument("--assert-complete", action="store_true", help="要求 V5 run matrix 完整通过。")

    inspect_v5_provider_gate_parser = subparsers.add_parser(
        "inspect-v5-provider-gate",
        help="只读检查 V5 provider credential gate report skeleton。",
    )
    inspect_v5_provider_gate_parser.add_argument("report", help="v5_provider_credential_gate_report.json 路径。")
    inspect_v5_provider_gate_parser.add_argument("--assert-consistent", action="store_true", help="要求 provider gate 一致。")

    inspect_v5_provider_cost_budget_parser = subparsers.add_parser(
        "inspect-v5-provider-cost-budget",
        help="只读检查 V5 provider cost budget report skeleton。",
    )
    inspect_v5_provider_cost_budget_parser.add_argument("report", help="v5_provider_cost_budget_report.json 路径。")
    inspect_v5_provider_cost_budget_parser.add_argument("--assert-consistent", action="store_true", help="要求 provider cost budget 一致。")

    inspect_v5_export_pack_parser = subparsers.add_parser(
        "inspect-v5-export-pack",
        help="只读检查 V5 export result pack manifest skeleton。",
    )
    inspect_v5_export_pack_parser.add_argument("manifest", help="v5_export_result_pack_manifest.json 路径。")
    inspect_v5_export_pack_parser.add_argument("--assert-clean", action="store_true", help="要求 V5 export pack 无污染。")

    inspect_v5_demo_artifacts_parser = subparsers.add_parser(
        "inspect-v5-demo-artifacts",
        help="只读检查 V5 resume/demo artifacts skeleton。",
    )
    inspect_v5_demo_artifacts_parser.add_argument("index", help="v5_resume_artifact_index.json 或相关 demo artifact manifest 路径。")
    inspect_v5_demo_artifacts_parser.add_argument("--assert-share-safe", action="store_true", help="要求 demo artifacts share-safe。")

    inspect_v5_inputs_parser = subparsers.add_parser(
        "inspect-v5-inputs",
        help="只读检查 V5 acceptance inputs skeleton。",
    )
    inspect_v5_inputs_parser.add_argument("inputs", help="v5_acceptance_inputs.json 路径。")
    inspect_v5_inputs_parser.add_argument("--assert-complete", action="store_true", help="要求 V5 acceptance inputs 完整通过。")

    inspect_v5_acceptance_parser = subparsers.add_parser(
        "inspect-v5-acceptance",
        help="只读检查 V5 acceptance report skeleton。",
    )
    inspect_v5_acceptance_parser.add_argument("report", help="v5_acceptance_report.json 路径。")
    inspect_v5_acceptance_parser.add_argument("--assert-core-complete", action="store_true", help="要求 core_acceptance 通过。")
    inspect_v5_acceptance_parser.add_argument("--assert-resume-ready", action="store_true", help="要求 resume_ready_acceptance 通过。")
    inspect_v5_acceptance_parser.add_argument("--assert-complete", action="store_true", help="等价于 --assert-resume-ready。")
    inspect_v5_acceptance_parser.add_argument("--reference-integrity-output")
    inspect_v5_acceptance_parser.add_argument("--reference-integrity-input")
    inspect_v5_acceptance_parser.add_argument("--command-log-entry-output")

    pre_verl_baseline_parser = subparsers.add_parser(
        "build-pre-verl-baseline",
        help="构建 pre-verl Stage 0 baseline binding。",
    )
    pre_verl_baseline_parser.add_argument("--output-dir", required=True)
    pre_verl_baseline_parser.add_argument("--v5-acceptance-report", required=True)
    pre_verl_baseline_parser.add_argument("--v5-export-pack-manifest", required=True)
    pre_verl_baseline_parser.add_argument("--v5-result-summary-table", required=True)
    pre_verl_baseline_parser.add_argument("--v5-acceptance-bundle", required=True)
    pre_verl_baseline_parser.add_argument("--v5-final-command-log", required=True)
    pre_verl_baseline_parser.add_argument("--run-live-checks", action="store_true")
    pre_verl_baseline_parser.add_argument("--fail-if-output-exists", action="store_true", default=True)

    inspect_pre_verl_baseline_parser = subparsers.add_parser("inspect-pre-verl-baseline")
    inspect_pre_verl_baseline_parser.add_argument("binding")
    inspect_pre_verl_baseline_parser.add_argument("--assert-baseline-complete", action="store_true")

    pre_verl_task_set_parser = subparsers.add_parser("build-pre-verl-task-set")
    pre_verl_task_set_parser.add_argument("--output-dir", required=True)
    pre_verl_task_set_parser.add_argument("--v5-task-set-manifest", required=True)
    pre_verl_task_set_parser.add_argument("--v5-task-inventory-report", required=True)
    pre_verl_task_set_parser.add_argument("--v5-task-visibility-scan-report", required=True)
    pre_verl_task_set_parser.add_argument("--swebench-lite-dev-rows")
    pre_verl_task_set_parser.add_argument("--swebench-lite-test-rows")
    pre_verl_task_set_parser.add_argument("--supplemental-pr-issue-candidate-report")
    pre_verl_task_set_parser.add_argument("--planned-dev-instances", type=int, default=23)
    pre_verl_task_set_parser.add_argument("--planned-curated-lite", type=int, default=50)
    pre_verl_task_set_parser.add_argument("--planned-github-issue", type=int, default=10)
    pre_verl_task_set_parser.add_argument("--fail-if-output-exists", action="store_true", default=True)

    inspect_pre_verl_task_set_parser = subparsers.add_parser("inspect-pre-verl-task-set")
    inspect_pre_verl_task_set_parser.add_argument("manifest")
    inspect_pre_verl_task_set_parser.add_argument("--assert-task-freeze-complete", action="store_true")

    inspect_pre_verl_task_visibility_parser = subparsers.add_parser("inspect-pre-verl-task-visibility")
    inspect_pre_verl_task_visibility_parser.add_argument("report")
    inspect_pre_verl_task_visibility_parser.add_argument("--assert-clean", action="store_true")

    inspect_pre_verl_agentloop_tasks_parser = subparsers.add_parser(
        "inspect-pre-verl-agentloop-task-definitions",
        help="只读检查 pre-verl formal AgentLoop 任务定义是否可被 run-task 正式链路消费。",
    )
    inspect_pre_verl_agentloop_tasks_parser.add_argument("manifest")
    inspect_pre_verl_agentloop_tasks_parser.add_argument("--assert-run-task-compatible", action="store_true")
    inspect_pre_verl_agentloop_tasks_parser.add_argument("--assert-evaluator-only-hidden-inputs", action="store_true")
    inspect_pre_verl_agentloop_tasks_parser.add_argument("--assert-no-hidden-material-in-model-visible-fields", action="store_true")

    inspect_pre_verl_agentloop_config_parser = subparsers.add_parser(
        "inspect-pre-verl-agentloop-run-config",
        help="只读检查 pre-verl formal AgentLoop 运行配置和解析后的工具策略。",
    )
    inspect_pre_verl_agentloop_config_parser.add_argument("manifest")
    inspect_pre_verl_agentloop_config_parser.add_argument("--assert-final-only-test-feedback-disabled", action="store_true")
    inspect_pre_verl_agentloop_config_parser.add_argument("--assert-resolved-tools-derived", action="store_true")
    inspect_pre_verl_agentloop_config_parser.add_argument("--assert-no-hidden-feedback-visible", action="store_true")

    inspect_pre_verl_agentloop_boundary_parser = subparsers.add_parser(
        "inspect-pre-verl-agentloop-boundary-index",
        help="只读检查 pre-verl formal AgentLoop final verifier boundary index。",
    )
    inspect_pre_verl_agentloop_boundary_parser.add_argument("index")
    inspect_pre_verl_agentloop_boundary_parser.add_argument("--assert-all-formal-runs-bound", action="store_true")
    inspect_pre_verl_agentloop_boundary_parser.add_argument("--assert-command-order", action="store_true")
    inspect_pre_verl_agentloop_boundary_parser.add_argument("--assert-clean-source-origin", action="store_true")
    inspect_pre_verl_agentloop_boundary_parser.add_argument("--assert-run-task-lineage", action="store_true")
    inspect_pre_verl_agentloop_boundary_parser.add_argument("--assert-no-legacy-adapter", action="store_true")

    inspect_model_visible_context_parser = subparsers.add_parser(
        "inspect-model-visible-context",
        help="只读检查一次 run 的模型可见上下文、prepared messages 和 provider body 绑定。",
    )
    inspect_model_visible_context_parser.add_argument("run_dir")
    inspect_model_visible_context_parser.add_argument("--assert-no-hidden-test-material", action="store_true")
    inspect_model_visible_context_parser.add_argument("--assert-prepared-messages-bound", action="store_true")
    inspect_model_visible_context_parser.add_argument("--assert-provider-body-equivalent", action="store_true")
    inspect_model_visible_context_parser.add_argument("--assert-tool-results-recoverable", action="store_true")
    inspect_model_visible_context_parser.add_argument("--assert-no-over-redaction", action="store_true")

    inspect_initial_context_parser = subparsers.add_parser(
        "inspect-initial-context",
        help="检查首轮模型可见上下文、provider body 和工具 schema 是否符合 lean context 策略。",
    )
    inspect_initial_context_parser.add_argument("target", nargs="?", help="run directory。")
    inspect_initial_context_parser.add_argument("--first-model-call", action="store_true")
    inspect_initial_context_parser.add_argument("--model-call-id")
    inspect_initial_context_parser.add_argument("--prepared-messages")
    inspect_initial_context_parser.add_argument("--raw-provider-request")
    inspect_initial_context_parser.add_argument("--assert-pre-verl-lean", action="store_true")

    build_pre_verl_evidence_ledger_parser = subparsers.add_parser(
        "build-pre-verl-evidence-ledger",
        help="构建 pre-verl 开发集正式 run 和 discarded attempt 的机器可读证据索引。",
    )
    build_pre_verl_evidence_ledger_parser.add_argument("run_root")
    build_pre_verl_evidence_ledger_parser.add_argument("--output")

    inspect_pre_verl_evidence_ledger_parser = subparsers.add_parser(
        "inspect-pre-verl-evidence-ledger",
        help="只读检查 pre-verl evidence ledger 的正式分母、导出和 verifier 一致性。",
    )
    inspect_pre_verl_evidence_ledger_parser.add_argument("ledger")
    inspect_pre_verl_evidence_ledger_parser.add_argument("--assert-complete", action="store_true")
    inspect_pre_verl_evidence_ledger_parser.add_argument(
        "--expected-formal-denominator",
        type=int,
        help="覆盖完整检查使用的 formal run 分母；3 题 canary 可传 3，正式 dev23 默认是 23。",
    )
    inspect_pre_verl_evidence_ledger_parser.add_argument(
        "--expected-result-counts",
        help=(
            "覆盖完整检查使用的结果分布 JSON，例如 "
            "'{\"success\": 1, \"failed\": 2, \"inconclusive\": 0}'。"
        ),
    )

    provider_failure_injection_parser = subparsers.add_parser(
        "run-provider-failure-injection-smoke",
        help="运行 pre-verl provider failure injection smoke，验证 retry、timeout、length 和 malformed tool call 异常路径。",
    )
    provider_failure_injection_parser.add_argument("--output-dir", required=True)
    provider_failure_injection_parser.add_argument(
        "--scenario",
        default=",".join(DEFAULT_PROVIDER_FAILURE_INJECTION_SCENARIOS),
        help="逗号分隔的 failure injection scenario 列表。",
    )

    pre_verl_swebench_materialization_parser = subparsers.add_parser("build-pre-verl-swebench-dev-materialization")
    pre_verl_swebench_materialization_parser.add_argument("--output-dir", required=True)
    pre_verl_swebench_materialization_parser.add_argument("--pre-verl-task-set-manifest", required=True)
    pre_verl_swebench_materialization_parser.add_argument("--max-tasks", type=int)
    pre_verl_swebench_materialization_parser.add_argument("--determinism-repeats", type=int, default=3)
    pre_verl_swebench_materialization_parser.add_argument("--fail-if-output-exists", action="store_true", default=True)

    inspect_pre_verl_swebench_materialization_parser = subparsers.add_parser("inspect-pre-verl-swebench-dev-materialization")
    inspect_pre_verl_swebench_materialization_parser.add_argument("report")
    inspect_pre_verl_swebench_materialization_parser.add_argument("--assert-materialized", action="store_true")

    pre_verl_materialized_task_set_parser = subparsers.add_parser("build-pre-verl-materialized-task-set")
    pre_verl_materialized_task_set_parser.add_argument("--output-dir", required=True)
    pre_verl_materialized_task_set_parser.add_argument("--pre-verl-task-set-manifest", required=True)
    pre_verl_materialized_task_set_parser.add_argument("--swebench-dev-materialization-report", required=True)
    pre_verl_materialized_task_set_parser.add_argument("--fail-if-output-exists", action="store_true", default=True)

    pre_verl_verifier_parser = subparsers.add_parser("build-pre-verl-verifier-correctness")
    pre_verl_verifier_parser.add_argument("--output-dir", required=True)
    pre_verl_verifier_parser.add_argument("--pre-verl-task-set-manifest", required=True)
    pre_verl_verifier_parser.add_argument("--executed-run-matrix-manifest", required=True)
    pre_verl_verifier_parser.add_argument("--swebench-dev-materialization-report")
    pre_verl_verifier_parser.add_argument("--fail-if-output-exists", action="store_true", default=True)

    inspect_pre_verl_verifier_parser = subparsers.add_parser("inspect-pre-verl-verifier-correctness")
    inspect_pre_verl_verifier_parser.add_argument("report")
    inspect_pre_verl_verifier_parser.add_argument("--assert-verifier-correctness-complete", action="store_true")
    inspect_pre_verl_verifier_parser.add_argument("--assert-verifier-readiness-complete", action="store_true")

    inspect_pre_verl_phase_parser = subparsers.add_parser("inspect-pre-verl-docker-phase-coverage")
    inspect_pre_verl_phase_parser.add_argument("matrix")
    inspect_pre_verl_phase_parser.add_argument("--assert-docker-phase-coverage-complete", action="store_true")
    inspect_pre_verl_phase_parser.add_argument("--assert-docker-phase-minimum-complete", action="store_true")

    pre_verl_agent_eval_parser = subparsers.add_parser("build-pre-verl-agent-evaluation-report")
    pre_verl_agent_eval_parser.add_argument("--output-dir", required=True)
    pre_verl_agent_eval_parser.add_argument("--pre-verl-task-set-manifest", required=True)
    pre_verl_agent_eval_parser.add_argument("--executed-run-matrix-manifest", required=True)
    pre_verl_agent_eval_parser.add_argument("--v5-result-summary-table", required=True)
    pre_verl_agent_eval_parser.add_argument("--provider-comparison-report")
    pre_verl_agent_eval_parser.add_argument("--fail-if-output-exists", action="store_true", default=True)

    inspect_pre_verl_agent_eval_parser = subparsers.add_parser("inspect-pre-verl-agent-evaluation")
    inspect_pre_verl_agent_eval_parser.add_argument("report")
    inspect_pre_verl_agent_eval_parser.add_argument("--assert-agent-evaluation-pilot-complete", action="store_true")
    inspect_pre_verl_agent_eval_parser.add_argument("--assert-agent-evaluation-readiness-complete", action="store_true")

    pre_verl_runtime_parser = subparsers.add_parser("build-pre-verl-agent-runtime-audit")
    pre_verl_runtime_parser.add_argument("--output-dir", required=True)
    pre_verl_runtime_parser.add_argument("--executed-run-matrix-manifest", required=True)
    pre_verl_runtime_parser.add_argument("--fail-if-output-exists", action="store_true", default=True)

    inspect_pre_verl_runtime_parser = subparsers.add_parser("inspect-pre-verl-agent-runtime-audit")
    inspect_pre_verl_runtime_parser.add_argument("report")
    inspect_pre_verl_runtime_parser.add_argument("--assert-runtime-invariants-clean", action="store_true")

    pre_verl_export_parser = subparsers.add_parser("build-pre-verl-export-audit")
    pre_verl_export_parser.add_argument("--output-dir", required=True)
    pre_verl_export_parser.add_argument("--v5-export-pack-manifest", required=True)
    pre_verl_export_parser.add_argument("--fail-if-output-exists", action="store_true", default=True)

    inspect_pre_verl_export_parser = subparsers.add_parser("inspect-pre-verl-export-audit")
    inspect_pre_verl_export_parser.add_argument("manifest")
    inspect_pre_verl_export_parser.add_argument("--assert-export-clean", action="store_true")

    inspect_pre_verl_reward_parser = subparsers.add_parser("inspect-pre-verl-reward-boundary")
    inspect_pre_verl_reward_parser.add_argument("report")
    inspect_pre_verl_reward_parser.add_argument("--assert-reward-boundary-clean", action="store_true")

    pre_verl_final_parser = subparsers.add_parser("build-pre-verl-evaluation-report")
    pre_verl_final_parser.add_argument("--output-dir", required=True)
    pre_verl_final_parser.add_argument("--baseline-binding", required=True)
    pre_verl_final_parser.add_argument("--task-set-manifest", required=True)
    pre_verl_final_parser.add_argument("--verifier-correctness-report", required=True)
    pre_verl_final_parser.add_argument("--agent-evaluation-report", required=True)
    pre_verl_final_parser.add_argument("--runtime-trace-report", required=True)
    pre_verl_final_parser.add_argument("--export-pack-manifest", required=True)
    pre_verl_final_parser.add_argument("--fail-if-output-exists", action="store_true", default=True)

    inspect_pre_verl_inputs_parser = subparsers.add_parser("inspect-pre-verl-evaluation-inputs")
    inspect_pre_verl_inputs_parser.add_argument("inputs")
    inspect_pre_verl_inputs_parser.add_argument("--assert-evaluation-inputs-complete", action="store_true")

    inspect_pre_verl_eval_parser = subparsers.add_parser("inspect-pre-verl-evaluation")
    inspect_pre_verl_eval_parser.add_argument("report")
    inspect_pre_verl_eval_parser.add_argument("--assert-evaluation-report-complete", action="store_true")

    inspect_pre_verl_claim_parser = subparsers.add_parser("inspect-pre-verl-claim-gate")
    inspect_pre_verl_claim_parser.add_argument("report")
    inspect_pre_verl_claim_parser.add_argument("--assert-claims-consistent", action="store_true")

    inspect_pre_verl_bundle_parser = subparsers.add_parser("inspect-pre-verl-evaluation-bundle")
    inspect_pre_verl_bundle_parser.add_argument("bundle")
    inspect_pre_verl_bundle_parser.add_argument("--final-command-log")
    inspect_pre_verl_bundle_parser.add_argument("--assert-immutable", action="store_true")

    inspect_pre_verl_public_parser = subparsers.add_parser("inspect-pre-verl-public-safe")
    inspect_pre_verl_public_parser.add_argument("report")
    inspect_pre_verl_public_parser.add_argument("--assert-share-safe", action="store_true")

    inspect_pre_verl_readiness_parser = subparsers.add_parser("inspect-pre-verl-readiness")
    inspect_pre_verl_readiness_parser.add_argument("report")
    inspect_pre_verl_readiness_parser.add_argument("--assert-verl-ready", action="store_true")

    inspect_stage14_parser = subparsers.add_parser(
        "inspect-stage14-fully-async-acceptance",
        help="检查 Stage 14 fully async 远端 smoke evidence 是否满足验收条件。",
    )
    inspect_stage14_parser.add_argument("evidence", help="Stage 14 evidence 目录或 tarball。")
    inspect_stage14_parser.add_argument("--assert-complete", action="store_true", help="要求 evidence 完整通过。")

    inspect_stage15_parser = subparsers.add_parser(
        "inspect-stage15-partial-rollout-acceptance",
        help="检查 Stage 15 partial rollout 远端 smoke evidence 是否满足验收条件。",
    )
    inspect_stage15_parser.add_argument("evidence", help="Stage 15 evidence 目录或 tarball。")
    inspect_stage15_parser.add_argument("--assert-complete", action="store_true", help="要求 evidence 完整通过。")

    inspect_stage16b5_parser = subparsers.add_parser(
        "inspect-stage16b5-docker-backend-acceptance",
        help="检查 Stage 16B.5 远端 Docker-capable 后端 evidence 是否满足验收条件。",
    )
    inspect_stage16b5_parser.add_argument("evidence", help="Stage 16B.5 evidence 目录或 tarball。")
    inspect_stage16b5_parser.add_argument("--assert-complete", action="store_true", help="要求 evidence 完整通过。")

    inspect_stage16d_parser = subparsers.add_parser(
        "inspect-stage16d-healthcheck",
        help="检查 Stage 16D official verifier healthcheck evidence 是否满足本地契约或正式验收条件。",
    )
    inspect_stage16d_parser.add_argument("evidence", help="Stage 16D evidence 目录。")
    inspect_stage16d_parser.add_argument(
        "--assert-contract-complete",
        action="store_true",
        help="要求本地契约、schema、分类和公开泄漏扫描完整通过。",
    )
    inspect_stage16d_parser.add_argument(
        "--assert-official-healthcheck-complete",
        action="store_true",
        help="要求真实 official harness gold/no-op healthcheck 完整通过。",
    )

    inspect_stage16f4_parser = subparsers.add_parser(
        "inspect-stage16f4-parity",
        help="检查 Stage 16F.4 run_task 与 run_episode parity audit evidence 是否满足验收条件。",
    )
    inspect_stage16f4_parser.add_argument("evidence", help="Stage 16F.4 evidence 目录。")
    inspect_stage16f4_parser.add_argument("--assert-complete", action="store_true", help="要求 evidence 完整通过。")

    build_stage14_smoke_kit_parser = subparsers.add_parser(
        "build-stage14-remote-smoke-kit",
        help="生成 Stage 14 远端 fully async smoke 配置骨架。",
    )
    build_stage14_smoke_kit_parser.add_argument("--output-dir", required=True)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """执行命令行入口。"""

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "validate-task":
        try:
            loaded = load_task(args.task_path)
        except RepoHarnessError as exc:
            parser.exit(1, f"任务校验失败：{exc}\n")
        print(f"任务校验通过：{loaded.runnable_task.task_id}")
        print(f"仓库：{loaded.runnable_task.repo_source}")
        print(f"测试命令：{loaded.verifier_config.test_command}")
        return 0
    if args.command == "inspect-run":
        print(inspect_run(args.run_dir))
        return 0
    if args.command == "inspect-export":
        try:
            print(
                inspect_export(
                    args.export_dir,
                    all_exports=args.all,
                    export_format=args.format,
                    assert_clean=args.assert_clean,
                    require_trainable_samples=args.require_trainable_samples,
                    allow_provider_reasoning_trace_diagnostic_only=(
                        args.allow_provider_reasoning_trace_diagnostic_only
                    ),
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"导出检查失败：{exc}\n")
        return 0
    if args.command == "inspect-mock-provider-smoke":
        try:
            print(
                inspect_mock_provider_smoke(
                    run_dir=args.run_dir,
                    output=args.output,
                    assert_accepted=args.assert_accepted,
                    assert_export_clean=args.assert_export_clean,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"mock provider smoke 检查失败：{exc}\n")
        return 0
    if args.command == "run-real-provider-smoke":
        try:
            report_path = run_real_provider_smoke(
                output_dir=args.output_dir,
                report_path=args.report,
                allow_openai_fallback=args.allow_openai_fallback,
                allow_local_secret_file=args.allow_local_secret_file,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"real provider smoke 运行失败：{exc}\n")
        print(f"真实 provider smoke report：{report_path}")
        return 0
    if args.command == "inspect-real-provider-smoke":
        try:
            print(
                inspect_real_provider_smoke(
                    report=args.report,
                    allow_skip_without_credentials=args.allow_skip_without_credentials,
                    require_accepted_with_credentials=args.require_accepted_with_credentials,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"real provider smoke 检查失败：{exc}\n")
        return 0
    if args.command == "workspace-backend-status":
        mode = "interface_only" if args.mode == "interface-only" else "docker_backend"
        try:
            output_path = write_workspace_backend_status(output=args.output, mode=mode)
        except RepoHarnessError as exc:
            parser.exit(1, f"workspace backend status 生成失败：{exc}\n")
        print(f"workspace backend status：{output_path}")
        return 0
    if args.command == "inspect-workspace-backend":
        try:
            print(
                inspect_workspace_backend_status(
                    status_file=args.status_file,
                    assert_interface_only=args.assert_interface_only,
                    assert_docker_backend=args.assert_docker_backend,
                    assert_stage_complete=args.assert_stage_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"workspace backend 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-feedback-policy-coverage":
        try:
            print(
                inspect_feedback_policy_coverage(
                    experiment_dir=args.experiment_dir,
                    output=args.output,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"feedback policy 覆盖检查失败：{exc}\n")
        return 0
    if args.command == "build-v2-acceptance-report":
        try:
            output_path = build_v2_acceptance_report(
                v1_regression_dir=args.v1_regression_dir,
                task_set_manifest=args.task_set_manifest,
                mock_provider_report=args.mock_provider_report,
                real_provider_report=args.real_provider_report,
                feedback_policy_report=args.feedback_policy_report,
                export_audit_roots=args.export_audit_root,
                docker_status=args.docker_status,
                output=args.output,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V2 acceptance report 生成失败：{exc}\n")
        print(f"V2 acceptance report：{output_path}")
        return 0
    if args.command == "inspect-v2-acceptance":
        try:
            print(
                inspect_v2_acceptance(
                    args.report,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V2 acceptance 检查失败：{exc}\n")
        return 0
    if args.command == "prepare-v3-swebench-fixture":
        try:
            manifest_path = prepare_v3_swebench_fixture(
                feasibility_root=args.feasibility_root,
                fixture_dir=args.fixture_dir,
                evidence_dir=args.evidence_dir,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 SWE-Bench-like fixture 冻结失败：{exc}\n")
        print(f"V3 SWE-Bench-like fixture manifest：{manifest_path}")
        return 0
    if args.command == "inspect-v3-swebench-fixture":
        try:
            print(
                inspect_v3_swebench_fixture(
                    fixture_dir=args.fixture_dir,
                    evidence_dir=args.evidence_dir,
                    manifest=args.manifest,
                    assert_frozen=args.assert_frozen,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 SWE-Bench-like fixture 检查失败：{exc}\n")
        return 0
    if args.command == "build-v3-task-set":
        try:
            output_path = build_v3_task_set(
                real_repository_inputs=args.real_repository_inputs,
                swebench_fixture_dir=args.swebench_fixture_dir,
                swebench_manifest=args.swebench_manifest,
                swebench_evidence_dir=args.swebench_evidence_dir,
                output_dir=args.output_dir,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 task set 构建失败：{exc}\n")
        print(f"V3 task set 产物目录：{output_path}")
        return 0
    if args.command == "inspect-v3-task-set":
        try:
            print(
                inspect_v3_task_set(
                    args.run_dir,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 task set 检查失败：{exc}\n")
        return 0
    if args.command == "build-v3-source-materialization":
        try:
            output_path = build_v3_source_materialization(
                task_set_dir=args.task_set_dir,
                swebench_source_manifest=args.swebench_source_manifest,
                hidden_verifier_inputs=args.hidden_verifier_inputs,
                output_dir=args.output_dir,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 source materialization 构建失败：{exc}\n")
        print(f"V3 source materialization 产物目录：{output_path}")
        return 0
    if args.command == "inspect-v3-source-materialization":
        try:
            print(
                inspect_v3_source_materialization(
                    args.run_dir,
                    report=args.report,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 source materialization 检查失败：{exc}\n")
        return 0
    if args.command == "build-v3-swebench-like":
        try:
            output_path = build_v3_swebench_like(
                source_materialization_run=args.source_materialization_run,
                hidden_verifier_inputs=args.hidden_verifier_inputs,
                gold_patch_predictions=args.gold_patch_predictions,
                output_dir=args.output_dir,
                execute=not args.skip_execute,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"SWE-Bench-like verifier 构建失败：{exc}\n")
        print(f"SWE-Bench-like verifier 产物目录：{output_path}")
        return 0
    if args.command == "inspect-swebench-like":
        try:
            print(
                inspect_swebench_like(
                    args.run_dir,
                    manifest=args.manifest,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"SWE-Bench-like verifier 检查失败：{exc}\n")
        return 0
    if args.command == "build-v3-agent-loop-integration":
        try:
            output_path = build_v3_agent_loop_integration(
                source_materialization_run=args.source_materialization_run,
                swebench_like_run=args.swebench_like_run,
                output_dir=args.output_dir,
                real_task_id=args.real_task_id,
                swebench_task_id=args.swebench_task_id,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 Agent Loop 集成构建失败：{exc}\n")
        print(f"V3 Agent Loop 集成产物目录：{output_path}")
        return 0
    if args.command == "inspect-v3-agent-loop-integration":
        try:
            print(
                inspect_v3_agent_loop_integration(
                    args.run_dir,
                    report=args.report,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 Agent Loop 集成检查失败：{exc}\n")
        return 0
    if args.command == "build-v3-experiment-resume":
        try:
            output_path = build_v3_experiment_resume(
                config_path=args.config,
                output_dir=args.output_dir,
                inject_interrupt_after=args.inject_interrupt_after,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 experiment resume 构建失败：{exc}\n")
        print(f"V3 experiment resume 产物目录：{output_path}")
        return 0
    if args.command == "inspect-experiment-resume":
        try:
            print(
                inspect_experiment_resume(
                    args.run_dir,
                    manifest=args.manifest,
                    assert_resumable=args.assert_resumable,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 experiment resume 检查失败：{exc}\n")
        return 0
    if args.command == "build-v3-context-diagnostics":
        try:
            output_path = build_v3_context_diagnostics(
                output_dir=args.output_dir,
                task_path=args.task_path,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 context diagnostics 构建失败：{exc}\n")
        print(f"V3 context diagnostics 产物目录：{output_path}")
        return 0
    if args.command == "inspect-context-report":
        try:
            print(
                inspect_context_report(
                    args.run_dir,
                    report=args.report,
                    assert_consistent=args.assert_consistent,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 context report 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-long-rollout-diagnostics":
        try:
            print(
                inspect_long_rollout_diagnostics(
                    args.run_dir,
                    report=args.report,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 long rollout diagnostics 检查失败：{exc}\n")
        return 0
    if args.command == "build-v3-reward-diagnostics":
        try:
            output_path = build_v3_failure_diagnostics(
                run_dir=args.run_dir,
                output_dir=args.output_dir,
                context_report=args.context_report,
                long_rollout_report=args.long_rollout_report,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 reward diagnostics 构建失败：{exc}\n")
        print(f"V3 reward diagnostics 产物目录：{output_path}")
        return 0
    if args.command == "inspect-reward-diagnostics":
        try:
            print(
                inspect_reward_diagnostics(
                    args.run_dir,
                    core_report=args.core_report,
                    distribution_report=args.distribution_report,
                    assert_core_complete=args.assert_core_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 reward diagnostics 检查失败：{exc}\n")
        return 0
    if args.command == "build-v3-export-audit":
        try:
            output_path = build_v3_export_audit(
                run_dirs=args.run_dir,
                output_dir=args.output_dir,
                preference_runs_dir=args.preference_runs_dir,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 export audit 构建失败：{exc}\n")
        print(f"V3 export audit 产物目录：{output_path}")
        return 0
    if args.command == "inspect-v3-export-audit":
        try:
            print(
                inspect_v3_export_audit(
                    args.run_dir,
                    manifest=args.manifest,
                    audit_report=args.audit_report,
                    assert_clean=args.assert_clean,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 export audit 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-trajectory-store":
        try:
            print(
                inspect_trajectory_store(
                    args.run_dir,
                    assert_readable=args.assert_readable,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 trajectory store 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-tool-contract":
        try:
            print(
                inspect_tool_contract(
                    args.run_dir,
                    assert_frozen=args.assert_frozen,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 tool contract 检查失败：{exc}\n")
        return 0
    if args.command == "build-v3-run-selection-manifest":
        try:
            output_path = build_v3_run_selection_manifest(
                run_refs=args.run_ref,
                output=args.output,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 run selection manifest 构建失败：{exc}\n")
        print(f"V3 run selection manifest：{output_path}")
        return 0
    if args.command == "build-v3-acceptance-inputs":
        try:
            output_path = build_v3_acceptance_inputs(
                run_selection_manifest=args.run_selection_manifest,
                export_root=args.export_root,
                v2_report=args.v2_report,
                pre_acceptance_docs=args.pre_acceptance_doc,
                documentation_manifest=args.documentation_manifest,
                command_log=args.command_log,
                test_evidence=args.test_evidence,
                output=args.output,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 acceptance inputs 构建失败：{exc}\n")
        print(f"V3 acceptance inputs：{output_path}")
        return 0
    if args.command == "build-v3-acceptance-report":
        try:
            output_path = build_v3_acceptance_report(
                acceptance_dir=args.acceptance_dir,
                input_manifest=args.input_manifest,
                output=args.output,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 acceptance report 构建失败：{exc}\n")
        print(f"V3 acceptance report：{output_path}")
        return 0
    if args.command == "inspect-v3-acceptance":
        try:
            print(
                inspect_v3_acceptance(
                    args.report,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 acceptance 检查失败：{exc}\n")
        return 0
    if args.command == "build-v3-acceptance-bundle":
        try:
            output_path = build_v3_acceptance_bundle(
                acceptance_dir=args.acceptance_dir,
                input_manifest=args.input_manifest,
                report=args.report,
                documentation_refs=args.documentation_ref,
                output=args.output,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 acceptance bundle 构建失败：{exc}\n")
        print(f"V3 acceptance bundle：{output_path}")
        return 0
    if args.command == "inspect-acceptance-bundle":
        try:
            print(
                inspect_acceptance_bundle(
                    args.manifest,
                    final_command_log=args.final_command_log,
                    assert_immutable=args.assert_immutable,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V3 acceptance bundle 检查失败：{exc}\n")
        return 0
    if args.command == "build-v4-implementation-inputs":
        try:
            output_path = build_v4_implementation_inputs(
                pr_issue_run=args.pr_issue_run,
                public_swebench_run=args.public_swebench_run,
                output_dir=args.output_dir,
                v2_acceptance=args.v2_acceptance,
                v3_acceptance=args.v3_acceptance,
                v3_acceptance_bundle=args.v3_acceptance_bundle,
                baseline_commit=args.baseline_commit,
                v3_closure_commit=args.v3_closure_commit,
                run_live_baseline_checks=args.run_live_baseline_checks,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 implementation inputs 构建失败：{exc}\n")
        print(f"V4 implementation input manifest：{output_path}")
        return 0
    if args.command == "inspect-v4-implementation-inputs":
        try:
            print(
                inspect_v4_implementation_inputs(
                    args.manifest,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 implementation inputs 检查失败：{exc}\n")
        return 0
    if args.command == "build-v4-task-freeze":
        try:
            output_path = build_v4_task_freeze(
                implementation_inputs=args.implementation_inputs,
                output_dir=args.output_dir,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 task freeze 构建失败：{exc}\n")
        print(f"V4 task freeze manifest：{output_path}")
        return 0
    if args.command == "build-v4-rollout-orchestration":
        try:
            output_path = build_v4_rollout_orchestration(
                task_freeze=args.task_freeze,
                output_dir=args.output_dir,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 rollout orchestration 构建失败：{exc}\n")
        print(f"V4 rollout queue manifest：{output_path}")
        return 0
    if args.command == "build-v4-tool-lifecycle":
        try:
            output_path = build_v4_tool_lifecycle(
                output_dir=args.output_dir,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 tool lifecycle 构建失败：{exc}\n")
        print(f"V4 tool contract snapshot：{output_path}")
        return 0
    if args.command == "build-v4-agent-run-integration":
        try:
            output_path = build_v4_agent_run_integration(
                output_dir=args.output_dir,
                task_freeze=args.task_freeze,
                tool_lifecycle=args.tool_lifecycle,
                rollout_queue=args.rollout_queue,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 agent run integration 构建失败：{exc}\n")
        print(f"V4 agent run integration report：{output_path}")
        return 0
    if args.command == "build-v4-export-quality":
        try:
            output_path = build_v4_export_quality(
                output_dir=args.output_dir,
                agent_run_integration=args.agent_run_integration,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 export quality 构建失败：{exc}\n")
        print(f"V4 export quality manifest：{output_path}")
        return 0
    if args.command == "build-v4-cards":
        try:
            output_path = build_v4_cards(
                output_dir=args.output_dir,
                task_freeze=args.task_freeze,
                agent_run_integration=args.agent_run_integration,
                export_quality=args.export_quality,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 cards 构建失败：{exc}\n")
        print(f"V4 cards manifest：{output_path}")
        return 0
    if args.command == "build-v4-run-selection-manifest":
        try:
            output_path = build_v4_run_selection_manifest(
                query=args.query,
                output=args.output,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 run selection manifest 构建失败：{exc}\n")
        print(f"V4 run selection manifest：{output_path}")
        return 0
    if args.command == "build-v4-acceptance-inputs":
        try:
            output_path = build_v4_acceptance_inputs(
                output=args.output,
                pre_acceptance_docs=args.pre_acceptance_doc,
                fail_if_output_exists=args.fail_if_output_exists,
                run_selection=args.run_selection,
                v2_acceptance=args.v2_acceptance,
                v3_acceptance=args.v3_acceptance,
                v3_acceptance_bundle=args.v3_acceptance_bundle,
                real_repository_regression=args.real_repository_regression,
                swebench_like_regression=args.swebench_like_regression,
                implementation_inputs=args.implementation_inputs,
                rollout_queue=args.rollout_queue,
                lease_state=args.lease_state,
                retry_policy=args.retry_policy,
                budget_control=args.budget_control,
                resource_locks=args.resource_locks,
                resource_usage=args.resource_usage,
                batch_resume=args.batch_resume,
                run_selection_query=args.run_selection_query,
                task_freeze=args.task_freeze,
                task_validity=args.task_validity,
                tool_contract=args.tool_contract,
                tool_lifecycle=args.tool_lifecycle,
                agent_run_integration=args.agent_run_integration,
                trajectory_store=args.trajectory_store,
                export_quality=args.export_quality,
                cards=args.cards,
                contamination_scan=args.contamination_scan,
                command_log=args.command_log,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 acceptance inputs 构建失败：{exc}\n")
        print(f"V4 acceptance inputs：{output_path}")
        return 0
    if args.command == "build-v4-acceptance-report":
        try:
            output_path = build_v4_acceptance_report(
                acceptance_inputs=args.acceptance_inputs,
                output=args.output,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 acceptance report 构建失败：{exc}\n")
        print(f"V4 acceptance report：{output_path}")
        return 0
    if args.command == "build-v4-acceptance-bundle":
        try:
            output_path = build_v4_acceptance_bundle(
                acceptance_report=args.acceptance_report,
                output=args.output,
                documentation_refs=args.documentation_ref,
                final_command_log=args.final_command_log,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 acceptance bundle 构建失败：{exc}\n")
        print(f"V4 acceptance bundle：{output_path}")
        return 0
    if args.command == "inspect-v4-inputs":
        try:
            print(inspect_v4_inputs(args.manifest, assert_complete=args.assert_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 acceptance inputs 检查失败：{exc}\n")
        return 0
    v4_artifact_command_map = {}
    if args.command in v4_artifact_command_map:
        try:
            print(
                inspect_v4_artifact_set(
                    v4_artifact_command_map[args.command],
                    args.path,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"{args.command} 检查失败：{exc}\n")
        return 0
    v4_rollout_command_map = {
        "inspect-rollout-queue": inspect_v4_rollout_queue_stage3,
        "inspect-rollout-leases": inspect_v4_rollout_leases_stage3,
        "inspect-rollout-retry": inspect_v4_rollout_retry_stage3,
        "inspect-rollout-budget": inspect_v4_rollout_budget_stage3,
        "inspect-resource-locks": inspect_v4_resource_locks_stage3,
        "inspect-resource-usage": inspect_v4_resource_usage_stage3,
        "inspect-rollout-resume": inspect_v4_rollout_resume_stage3,
        "inspect-run-selection-query": inspect_v4_run_selection_query_stage3,
    }
    if args.command in v4_rollout_command_map:
        try:
            print(v4_rollout_command_map[args.command](args.path, assert_complete=args.assert_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"{args.command} 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v4-task-freeze":
        try:
            print(inspect_v4_task_freeze_stage2(args.path, assert_complete=args.assert_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"inspect-v4-task-freeze 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v4-task-validity":
        try:
            print(inspect_v4_task_validity_stage2(args.path, assert_complete=args.assert_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"inspect-v4-task-validity 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v4-tool-contract":
        try:
            print(inspect_v4_tool_contract_stage4(args.path, assert_frozen=args.assert_frozen))
        except RepoHarnessError as exc:
            parser.exit(1, f"inspect-v4-tool-contract 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v4-tool-lifecycle":
        try:
            print(inspect_v4_tool_lifecycle_stage4(args.path, assert_complete=args.assert_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"inspect-v4-tool-lifecycle 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v4-agent-run-integration":
        try:
            print(inspect_v4_agent_run_integration_stage5(args.path, assert_complete=args.assert_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"inspect-v4-agent-run-integration 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v4-trajectory-store":
        try:
            print(inspect_v4_trajectory_store_stage5(args.path, assert_readable=args.assert_readable))
        except RepoHarnessError as exc:
            parser.exit(1, f"inspect-v4-trajectory-store 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v4-export-quality":
        try:
            print(inspect_v4_export_quality_stage6(args.path, assert_complete=args.assert_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"inspect-v4-export-quality 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v4-cards":
        try:
            print(inspect_v4_cards_stage7(args.path, assert_complete=args.assert_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"inspect-v4-cards 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v4-contamination-scan":
        try:
            print(inspect_v4_artifact_set("contamination_scan", args.path, assert_complete=args.assert_clean))
        except RepoHarnessError as exc:
            parser.exit(1, f"inspect-v4-contamination-scan 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v4-acceptance":
        try:
            print(inspect_v4_acceptance(args.report, assert_complete=args.assert_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"V4 acceptance 检查失败：{exc}\n")
        return 0
    if args.command == "build-v5-preimplementation":
        try:
            output_path = build_v5_preimplementation(
                output_dir=args.output_dir,
                v2_acceptance_report=args.v2_acceptance_report,
                v3_acceptance_report=args.v3_acceptance_report,
                v3_acceptance_bundle=args.v3_acceptance_bundle,
                v4_acceptance_inputs=args.v4_acceptance_inputs,
                v4_acceptance_report=args.v4_acceptance_report,
                v4_doc_sync_acceptance_bundle=args.v4_doc_sync_acceptance_bundle,
                v4_doc_sync_final_command_log=args.v4_doc_sync_final_command_log,
                preflight_root=args.preflight_root,
                preflight_flaky_probe_report=args.preflight_flaky_probe_report,
                preflight_visibility_probe_summary=args.preflight_visibility_probe_summary,
                preflight_run_matrix_manifest=args.preflight_run_matrix_manifest,
                preflight_task_selection_report=args.preflight_task_selection_report,
                preflight_resume_claim_gate_report=args.preflight_resume_claim_gate_report,
                preflight_evidence_manifest=args.preflight_evidence_manifest,
                baseline_commit=args.baseline_commit,
                v4_closure_commit=args.v4_closure_commit,
                baseline_command_cwd=args.baseline_command_cwd,
                run_live_baseline_checks=args.run_live_baseline_checks,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 preimplementation 构建失败：{exc}\n")
        print(f"V5 preflight input binding：{output_path}")
        return 0
    if args.command == "inspect-v5-preimplementation":
        try:
            print(
                inspect_v5_preimplementation(
                    args.binding,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 preimplementation 检查失败：{exc}\n")
        return 0
    if args.command == "build-v5-schema-fixtures":
        try:
            output_path = build_schema_fixtures(
                output_dir=args.output_dir,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 schema fixtures 构建失败：{exc}\n")
        print(f"V5 schema tracking table：{output_path}")
        return 0
    if args.command == "build-v5-evidence-integrity":
        try:
            output_path = build_pre_acceptance_integrity_report(
                critical_evidence_manifest=args.critical_evidence_manifest,
                pre_acceptance_command_log=args.pre_acceptance_command_log,
                output=args.output,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 evidence integrity 构建失败：{exc}\n")
        print(f"V5 pre-acceptance evidence integrity report：{output_path}")
        return 0
    if args.command == "inspect-v5-evidence-integrity":
        try:
            print(
                inspect_v5_evidence_integrity(
                    args.report,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 evidence integrity 检查失败：{exc}\n")
        return 0
    if args.command == "build-v5-task-set":
        try:
            output_path = build_v5_task_set_manifest(
                preflight_input_binding=args.preflight_input_binding,
                adapter_visible_task_draft=args.adapter_visible_task_draft,
                evaluator_only_evidence_manifest=args.evaluator_only_evidence_manifest,
                run_matrix_preflight_manifest=args.run_matrix_preflight_manifest,
                task_selection_preflight_report=args.task_selection_preflight_report,
                visibility_scan_report=args.visibility_scan_report,
                flaky_probe_report=args.flaky_probe_report,
                source_materialization_reports=args.source_materialization_report,
                output_dir=args.output_dir,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 task set 构建失败：{exc}\n")
        print(f"V5 task set manifest：{output_path}")
        return 0
    if args.command == "build-v5-supplemental-pr-issue-candidates":
        try:
            output_path = build_v5_supplemental_pr_issue_candidates(
                candidate_ids=args.candidate_id,
                source_preflight_root=args.source_preflight_root,
                output_dir=args.output_dir,
                max_accepted=args.max_accepted,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 supplemental PR / issue candidate 构建失败：{exc}\n")
        print(f"V5 supplemental PR / issue candidate report：{output_path}")
        return 0
    if args.command == "merge-v5-task-set":
        try:
            output_path = merge_v5_task_set_manifests(
                base_task_set=args.base_task_set,
                supplemental_report=args.supplemental_report,
                output=args.output,
                output_inventory=args.output_inventory,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 task set merge 失败：{exc}\n")
        print(f"V5 merged task set manifest：{output_path}")
        return 0
    if args.command == "inspect-v5-task-set":
        try:
            print(inspect_v5_task_set(args.manifest, assert_complete=args.assert_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 task set 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v5-task-visibility":
        try:
            print(inspect_v5_task_visibility(args.report, assert_clean=args.assert_clean))
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 task visibility 检查失败：{exc}\n")
        return 0
    if args.command == "build-v5-provider-gate":
        try:
            output_path = build_v5_provider_gate_report(
                task_set_manifest=args.task_set_manifest,
                output_dir=args.output_dir,
                allow_local_secret_file=args.allow_local_secret_file,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 provider gate 构建失败：{exc}\n")
        print(f"V5 provider credential gate report：{output_path}")
        return 0
    if args.command == "build-v5-provider-cost-budget":
        try:
            output_path = build_v5_provider_cost_budget_report(
                provider_gate_report=args.provider_gate_report,
                output=args.output,
                max_real_provider_calls=args.max_real_provider_calls,
                max_cost_usd=args.max_cost_usd,
                actual_real_provider_calls=args.actual_real_provider_calls,
                actual_cost_proxy_usd=args.actual_cost_proxy_usd,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 provider cost budget 构建失败：{exc}\n")
        print(f"V5 provider cost budget report：{output_path}")
        return 0
    if args.command == "build-v5-run-matrix":
        try:
            output_path = build_v5_run_matrix_manifest(
                task_set_manifest=args.task_set_manifest,
                provider_gate_report=args.provider_gate_report,
                provider_cost_budget_report=args.provider_cost_budget_report,
                output_dir=args.output_dir,
                task_ids=args.task_id,
                provider_ids=args.provider_id,
                deepseek_model_id=args.deepseek_model_id,
                openai_model_id=args.openai_model_id,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 run matrix 构建失败：{exc}\n")
        print(f"V5 run matrix manifest：{output_path}")
        return 0
    if args.command == "run-v5-run-matrix":
        try:
            output_path = run_v5_run_matrix_cells(
                run_matrix_manifest=args.run_matrix_manifest,
                provider_cost_budget_report=args.provider_cost_budget_report,
                output_dir=args.output_dir,
                allow_local_secret_file=args.allow_local_secret_file,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 run matrix 执行失败：{exc}\n")
        print(f"V5 executed run matrix manifest：{output_path}")
        return 0
    if args.command == "run-v5-accepted-provider-task":
        try:
            output_path = run_v5_accepted_provider_task(
                task_set_manifest=args.task_set_manifest,
                provider_gate_report=args.provider_gate_report,
                provider_cost_budget_report=args.provider_cost_budget_report,
                output_dir=args.output_dir,
                task_id=args.task_id,
                provider_id=args.provider_id,
                model_id=args.model_id,
                scaffold_id=args.scaffold_id,
                prior_executed_run_matrix_manifest=args.prior_executed_run_matrix_manifest,
                allow_local_secret_file=args.allow_local_secret_file,
                max_turns=args.max_turns,
                max_tool_calls=args.max_tool_calls,
                max_output_tokens=args.max_output_tokens,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 accepted provider run 执行失败：{exc}\n")
        print(f"V5 accepted provider executed run matrix manifest：{output_path}")
        return 0
    if args.command == "build-v5-comparison-reports":
        try:
            output_path = build_v5_comparison_reports(
                executed_run_matrix_manifest=args.executed_run_matrix_manifest,
                additional_executed_run_matrix_manifests=args.additional_executed_run_matrix_manifest,
                provider_gate_report=args.provider_gate_report,
                output_dir=args.output_dir,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 comparison reports 构建失败：{exc}\n")
        print(f"V5 matrix compare scope report：{output_path}")
        return 0
    if args.command == "build-v5-export-pack":
        try:
            output_path = build_v5_export_result_pack(
                executed_run_matrix_manifest=args.executed_run_matrix_manifest,
                stage3_claim_gate_report=args.stage3_claim_gate_report,
                output_dir=args.output_dir,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 export pack 构建失败：{exc}\n")
        print(f"V5 export result pack manifest：{output_path}")
        return 0
    if args.command == "build-v5-demo-artifacts":
        try:
            output_path = build_v5_demo_artifacts(
                task_set_manifest=args.task_set_manifest,
                executed_run_matrix_manifest=args.executed_run_matrix_manifest,
                export_pack_manifest=args.export_pack_manifest,
                stage4_claim_gate_report=args.stage4_claim_gate_report,
                provider_comparison_report=args.provider_comparison_report,
                output_dir=args.output_dir,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 demo artifacts 构建失败：{exc}\n")
        print(f"V5 resume artifact index：{output_path}")
        return 0
    if args.command == "build-v5-interview-result-pack":
        try:
            output_path = build_v5_interview_result_pack(
                resume_artifact_index=args.resume_artifact_index,
                stage5_claim_gate_report=args.stage5_claim_gate_report,
                docs12_path=args.docs12_path,
                output_dir=args.output_dir,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 interview result pack 构建失败：{exc}\n")
        print(f"V5 interview result pack manifest：{output_path}")
        return 0
    if args.command == "build-v5-acceptance-inputs":
        try:
            output_path = build_v5_acceptance_inputs(
                output_dir=args.output_dir,
                v2_acceptance_report=args.v2_acceptance_report,
                v3_acceptance_report=args.v3_acceptance_report,
                v3_acceptance_bundle=args.v3_acceptance_bundle,
                v4_acceptance_inputs=args.v4_acceptance_inputs,
                v4_acceptance_report=args.v4_acceptance_report,
                v4_doc_sync_acceptance_bundle=args.v4_doc_sync_acceptance_bundle,
                v4_doc_sync_final_command_log=args.v4_doc_sync_final_command_log,
                v5_baseline_check_report=args.v5_baseline_check_report,
                v5_v4_closure_report=args.v5_v4_closure_report,
                v5_documentation_sync_report=args.v5_documentation_sync_report,
                v5_preflight_input_binding=args.v5_preflight_input_binding,
                v5_pre_acceptance_evidence_integrity_report=args.v5_pre_acceptance_evidence_integrity_report,
                v5_task_set_manifest=args.v5_task_set_manifest,
                v5_task_inventory_report=args.v5_task_inventory_report,
                v5_task_diversity_report=args.v5_task_diversity_report,
                v5_task_visibility_scan_report=args.v5_task_visibility_scan_report,
                v5_run_matrix_manifest=args.v5_run_matrix_manifest,
                v5_executed_run_matrix_manifest=args.v5_executed_run_matrix_manifest,
                v5_matrix_compare_scope_report=args.v5_matrix_compare_scope_report,
                v5_provider_credential_gate_report=args.v5_provider_credential_gate_report,
                v5_provider_cost_budget_report=args.v5_provider_cost_budget_report,
                v5_resume_claim_gate_report=args.v5_resume_claim_gate_report,
                v5_export_result_pack_manifest=args.v5_export_result_pack_manifest,
                v5_preference_pair_blocked_report=args.v5_preference_pair_blocked_report,
                v5_failure_taxonomy_report=args.v5_failure_taxonomy_report,
                v5_reward_source_taxonomy_report=args.v5_reward_source_taxonomy_report,
                v5_interview_demo_card=args.v5_interview_demo_card,
                v5_canonical_demo_walkthrough=args.v5_canonical_demo_walkthrough,
                v5_public_demo_bundle_manifest=args.v5_public_demo_bundle_manifest,
                v5_resume_artifact_index=args.v5_resume_artifact_index,
                v5_repro_command_index=args.v5_repro_command_index,
                v5_result_summary_table=args.v5_result_summary_table,
                v5_demo_transcript_index=args.v5_demo_transcript_index,
                v5_permission_network_risk_audit_report=args.v5_permission_network_risk_audit_report,
                v5_claude_code_invariant_mapping=args.v5_claude_code_invariant_mapping,
                v5_interview_result_pack_manifest=args.v5_interview_result_pack_manifest,
                v5_implementation_logs=args.v5_implementation_log,
                v5_review_records=args.v5_review_record,
                full_test_summary=args.full_test_summary,
                v5_provider_comparison_report=args.v5_provider_comparison_report,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 acceptance inputs 构建失败：{exc}\n")
        print(f"V5 acceptance inputs：{output_path}")
        return 0
    if args.command == "build-v5-acceptance-report":
        try:
            output_path = build_v5_acceptance_report(
                acceptance_inputs=args.acceptance_inputs,
                output_dir=args.output_dir,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 acceptance report 构建失败：{exc}\n")
        print(f"V5 acceptance report：{output_path}")
        return 0
    if args.command == "build-v5-pre-bundle-command-log":
        try:
            output_path = build_v5_pre_bundle_command_log(
                base_command_log=args.base_command_log,
                command_log_entries=args.command_log_entry,
                output=args.output,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 pre-bundle command log 构建失败：{exc}\n")
        print(f"V5 pre-bundle command log：{output_path}")
        return 0
    if args.command == "build-v5-acceptance-bundle":
        try:
            output_path = build_v5_acceptance_bundle(
                acceptance_report=args.acceptance_report,
                post_report_inspect_output=args.post_report_inspect_output,
                pre_bundle_command_log=args.pre_bundle_command_log,
                documentation_refs=args.documentation_ref,
                bundle_build_command_log_entry_output=args.bundle_build_command_log_entry_output,
                output=args.output,
                doc_sync_from_bundle=args.doc_sync_from_bundle,
                final_command_log=args.final_command_log,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 acceptance bundle 构建失败：{exc}\n")
        print(f"V5 acceptance bundle：{output_path}")
        return 0
    if args.command == "plan-acceptance-bundle-inspect-entry":
        try:
            output_path = plan_v5_acceptance_bundle_inspect_entry(
                acceptance_bundle=args.acceptance_bundle,
                final_command_log=args.final_command_log,
                self_referential_acceptance_bundle=args.self_referential_acceptance_bundle,
                output=args.output,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 acceptance bundle inspect entry 生成失败：{exc}\n")
        print(f"V5 inspect acceptance bundle command entry：{output_path}")
        return 0
    if args.command == "plan-v5-acceptance-bundle-build-entry":
        try:
            output_path = plan_v5_acceptance_bundle_build_entry(
                acceptance_report=args.acceptance_report,
                post_report_inspect_output=args.post_report_inspect_output,
                pre_bundle_command_log=args.pre_bundle_command_log,
                documentation_refs=args.documentation_ref,
                bundle_build_command_log_entry_output=args.bundle_build_command_log_entry_output,
                output_bundle=args.output_bundle,
                final_command_log=args.final_command_log,
                doc_sync_from_bundle=args.doc_sync_from_bundle,
                output=args.output,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 acceptance bundle build entry 生成失败：{exc}\n")
        print(f"V5 build acceptance bundle command entry：{output_path}")
        return 0
    if args.command == "build-v5-final-command-log":
        try:
            output_path = build_v5_final_command_log(
                pre_bundle_command_log=args.pre_bundle_command_log,
                command_log_entries=args.command_log_entry,
                output=args.output,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 final command log 构建失败：{exc}\n")
        print(f"V5 final command log：{output_path}")
        return 0
    if args.command == "inspect-v5-run-matrix":
        try:
            print(inspect_v5_run_matrix(args.manifest, assert_complete=args.assert_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 run matrix 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v5-provider-gate":
        try:
            print(inspect_v5_provider_gate(args.report, assert_consistent=args.assert_consistent))
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 provider gate 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v5-provider-cost-budget":
        try:
            print(inspect_v5_provider_cost_budget(args.report, assert_consistent=args.assert_consistent))
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 provider cost budget 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v5-export-pack":
        try:
            print(inspect_v5_export_pack(args.manifest, assert_clean=args.assert_clean))
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 export pack 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v5-demo-artifacts":
        try:
            print(inspect_v5_demo_artifacts(args.index, assert_share_safe=args.assert_share_safe))
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 demo artifacts 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v5-inputs":
        try:
            print(inspect_v5_inputs(args.inputs, assert_complete=args.assert_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 acceptance inputs 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-v5-acceptance":
        try:
            print(
                inspect_v5_acceptance(
                    args.report,
                    assert_core_complete=args.assert_core_complete,
                    assert_resume_ready=args.assert_resume_ready,
                    assert_complete=args.assert_complete,
                    reference_integrity_output=args.reference_integrity_output,
                    reference_integrity_input=args.reference_integrity_input,
                    command_log_entry_output=args.command_log_entry_output,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"V5 acceptance 检查失败：{exc}\n")
        return 0
    if args.command == "build-pre-verl-baseline":
        try:
            output_path = build_pre_verl_baseline(
                output_dir=args.output_dir,
                v5_acceptance_report=args.v5_acceptance_report,
                v5_export_pack_manifest=args.v5_export_pack_manifest,
                v5_result_summary_table=args.v5_result_summary_table,
                v5_acceptance_bundle=args.v5_acceptance_bundle,
                v5_final_command_log=args.v5_final_command_log,
                run_live_checks=args.run_live_checks,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl baseline 构建失败：{exc}\n")
        print(f"pre-verl baseline binding：{output_path}")
        return 0
    if args.command == "inspect-pre-verl-baseline":
        try:
            print(inspect_pre_verl_baseline(args.binding, assert_baseline_complete=args.assert_baseline_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl baseline 检查失败：{exc}\n")
        return 0
    if args.command == "build-pre-verl-task-set":
        try:
            output_path = build_pre_verl_task_set(
                output_dir=args.output_dir,
                v5_task_set_manifest=args.v5_task_set_manifest,
                v5_task_inventory_report=args.v5_task_inventory_report,
                v5_task_visibility_scan_report=args.v5_task_visibility_scan_report,
                swebench_lite_dev_rows=args.swebench_lite_dev_rows,
                swebench_lite_test_rows=args.swebench_lite_test_rows,
                supplemental_pr_issue_candidate_report=args.supplemental_pr_issue_candidate_report,
                planned_dev_instances=args.planned_dev_instances,
                planned_curated_lite=args.planned_curated_lite,
                planned_github_issue=args.planned_github_issue,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl task set 构建失败：{exc}\n")
        print(f"pre-verl task set manifest：{output_path}")
        return 0
    if args.command == "inspect-pre-verl-task-set":
        try:
            print(inspect_pre_verl_task_set(args.manifest, assert_task_freeze_complete=args.assert_task_freeze_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl task set 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-pre-verl-task-visibility":
        try:
            print(inspect_pre_verl_task_visibility(args.report, assert_clean=args.assert_clean))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl visibility 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-pre-verl-agentloop-task-definitions":
        try:
            print(
                inspect_pre_verl_agentloop_task_definitions(
                    args.manifest,
                    assert_run_task_compatible=args.assert_run_task_compatible,
                    assert_evaluator_only_hidden_inputs=args.assert_evaluator_only_hidden_inputs,
                    assert_no_hidden_material_in_model_visible_fields=(
                        args.assert_no_hidden_material_in_model_visible_fields
                    ),
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl AgentLoop task definition 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-pre-verl-agentloop-run-config":
        try:
            print(
                inspect_pre_verl_agentloop_run_config(
                    args.manifest,
                    assert_final_only_test_feedback_disabled=(
                        args.assert_final_only_test_feedback_disabled
                    ),
                    assert_resolved_tools_derived=args.assert_resolved_tools_derived,
                    assert_no_hidden_feedback_visible=args.assert_no_hidden_feedback_visible,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl AgentLoop run config 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-pre-verl-agentloop-boundary-index":
        try:
            print(
                inspect_pre_verl_agentloop_boundary_index(
                    args.index,
                    assert_all_formal_runs_bound=args.assert_all_formal_runs_bound,
                    assert_command_order=args.assert_command_order,
                    assert_clean_source_origin=args.assert_clean_source_origin,
                    assert_run_task_lineage=args.assert_run_task_lineage,
                    assert_no_legacy_adapter=args.assert_no_legacy_adapter,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl AgentLoop boundary index 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-model-visible-context":
        try:
            print(
                inspect_model_visible_context(
                    args.run_dir,
                    assert_no_hidden_test_material=args.assert_no_hidden_test_material,
                    assert_prepared_messages_bound=args.assert_prepared_messages_bound,
                    assert_provider_body_equivalent=args.assert_provider_body_equivalent,
                    assert_tool_results_recoverable=args.assert_tool_results_recoverable,
                    assert_no_over_redaction=args.assert_no_over_redaction,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"模型可见上下文检查失败：{exc}\n")
        return 0
    if args.command == "inspect-initial-context":
        try:
            print(
                inspect_initial_context(
                    args.target,
                    first_model_call=args.first_model_call,
                    model_call_id=args.model_call_id,
                    prepared_messages=args.prepared_messages,
                    raw_provider_request=args.raw_provider_request,
                    assert_pre_verl_lean=args.assert_pre_verl_lean,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"首轮模型上下文检查失败：{exc}\n")
        return 0
    if args.command == "build-pre-verl-evidence-ledger":
        try:
            output_path = build_pre_verl_evidence_ledger(
                args.run_root,
                output=args.output,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl evidence ledger 构建失败：{exc}\n")
        print(f"pre-verl evidence ledger：{output_path}")
        return 0
    if args.command == "inspect-pre-verl-evidence-ledger":
        try:
            expected_result_counts = (
                json.loads(args.expected_result_counts)
                if args.expected_result_counts
                else None
            )
            if expected_result_counts is not None and not isinstance(expected_result_counts, dict):
                raise RepoHarnessError("--expected-result-counts 必须是 JSON object。")
            print(
                inspect_pre_verl_evidence_ledger(
                    args.ledger,
                    assert_complete=args.assert_complete,
                    expected_formal_denominator=args.expected_formal_denominator,
                    expected_result_counts=expected_result_counts,
                )
            )
        except json.JSONDecodeError as exc:
            parser.exit(1, f"pre-verl evidence ledger 检查失败：--expected-result-counts 不是有效 JSON：{exc}\n")
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl evidence ledger 检查失败：{exc}\n")
        return 0
    if args.command == "run-provider-failure-injection-smoke":
        try:
            scenarios = [item.strip() for item in args.scenario.split(",") if item.strip()]
            report_path = run_provider_failure_injection_smoke(
                output_dir=args.output_dir,
                scenarios=scenarios,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"provider failure injection smoke 失败：{exc}\n")
        print(f"provider failure injection smoke report：{report_path}")
        return 0
    if args.command == "build-pre-verl-swebench-dev-materialization":
        try:
            output_path = build_pre_verl_swebench_dev_materialization(
                output_dir=args.output_dir,
                pre_verl_task_set_manifest=args.pre_verl_task_set_manifest,
                max_tasks=args.max_tasks,
                determinism_repeats=args.determinism_repeats,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl SWE-Bench development materialization 构建失败：{exc}\n")
        print(f"pre-verl SWE-Bench development materialization report：{output_path}")
        return 0
    if args.command == "inspect-pre-verl-swebench-dev-materialization":
        try:
            print(inspect_pre_verl_swebench_dev_materialization(args.report, assert_materialized=args.assert_materialized))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl SWE-Bench development materialization 检查失败：{exc}\n")
        return 0
    if args.command == "build-pre-verl-materialized-task-set":
        try:
            output_path = build_pre_verl_materialized_task_set(
                output_dir=args.output_dir,
                pre_verl_task_set_manifest=args.pre_verl_task_set_manifest,
                swebench_dev_materialization_report=args.swebench_dev_materialization_report,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl materialized task set 构建失败：{exc}\n")
        print(f"pre-verl materialized task set manifest：{output_path}")
        return 0
    if args.command == "build-pre-verl-verifier-correctness":
        try:
            output_path = build_pre_verl_verifier_correctness(
                output_dir=args.output_dir,
                pre_verl_task_set_manifest=args.pre_verl_task_set_manifest,
                executed_run_matrix_manifest=args.executed_run_matrix_manifest,
                swebench_dev_materialization_report=args.swebench_dev_materialization_report,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl verifier correctness 构建失败：{exc}\n")
        print(f"pre-verl verifier correctness report：{output_path}")
        return 0
    if args.command == "inspect-pre-verl-verifier-correctness":
        try:
            print(
                inspect_pre_verl_verifier_correctness(
                    args.report,
                    assert_verifier_correctness_complete=args.assert_verifier_correctness_complete,
                    assert_verifier_readiness_complete=args.assert_verifier_readiness_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl verifier correctness 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-pre-verl-docker-phase-coverage":
        try:
            print(
                inspect_pre_verl_phase_coverage(
                    args.matrix,
                    assert_complete=args.assert_docker_phase_coverage_complete,
                    assert_minimum_complete=args.assert_docker_phase_minimum_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl phase coverage 检查失败：{exc}\n")
        return 0
    if args.command == "build-pre-verl-agent-evaluation-report":
        try:
            output_path = build_pre_verl_agent_evaluation(
                output_dir=args.output_dir,
                pre_verl_task_set_manifest=args.pre_verl_task_set_manifest,
                executed_run_matrix_manifest=args.executed_run_matrix_manifest,
                v5_result_summary_table=args.v5_result_summary_table,
                provider_comparison_report=args.provider_comparison_report,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl agent evaluation 构建失败：{exc}\n")
        print(f"pre-verl agent evaluation report：{output_path}")
        return 0
    if args.command == "inspect-pre-verl-agent-evaluation":
        try:
            print(
                inspect_pre_verl_agent_evaluation(
                    args.report,
                    assert_agent_evaluation_pilot_complete=args.assert_agent_evaluation_pilot_complete,
                    assert_agent_evaluation_readiness_complete=args.assert_agent_evaluation_readiness_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl agent evaluation 检查失败：{exc}\n")
        return 0
    if args.command == "build-pre-verl-agent-runtime-audit":
        try:
            output_path = build_pre_verl_runtime_audit(
                output_dir=args.output_dir,
                executed_run_matrix_manifest=args.executed_run_matrix_manifest,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl runtime audit 构建失败：{exc}\n")
        print(f"pre-verl runtime trace report：{output_path}")
        return 0
    if args.command == "inspect-pre-verl-agent-runtime-audit":
        try:
            print(inspect_pre_verl_runtime_audit(args.report, assert_runtime_invariants_clean=args.assert_runtime_invariants_clean))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl runtime audit 检查失败：{exc}\n")
        return 0
    if args.command == "build-pre-verl-export-audit":
        try:
            output_path = build_pre_verl_export_audit(
                output_dir=args.output_dir,
                v5_export_pack_manifest=args.v5_export_pack_manifest,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl export audit 构建失败：{exc}\n")
        print(f"pre-verl export result pack manifest：{output_path}")
        return 0
    if args.command == "inspect-pre-verl-export-audit":
        try:
            print(inspect_pre_verl_export_audit(args.manifest, assert_export_clean=args.assert_export_clean))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl export audit 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-pre-verl-reward-boundary":
        try:
            print(inspect_pre_verl_reward_boundary(args.report, assert_reward_boundary_clean=args.assert_reward_boundary_clean))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl reward boundary 检查失败：{exc}\n")
        return 0
    if args.command == "build-pre-verl-evaluation-report":
        try:
            output_path = build_pre_verl_final(
                output_dir=args.output_dir,
                baseline_binding=args.baseline_binding,
                task_set_manifest=args.task_set_manifest,
                verifier_correctness_report=args.verifier_correctness_report,
                agent_evaluation_report=args.agent_evaluation_report,
                runtime_trace_report=args.runtime_trace_report,
                export_pack_manifest=args.export_pack_manifest,
                fail_if_output_exists=args.fail_if_output_exists,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl final report 构建失败：{exc}\n")
        print(f"pre-verl evaluation report：{output_path}")
        return 0
    if args.command == "inspect-pre-verl-evaluation-inputs":
        try:
            print(inspect_pre_verl_inputs(args.inputs, assert_complete=args.assert_evaluation_inputs_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl evaluation inputs 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-pre-verl-evaluation":
        try:
            print(inspect_pre_verl_evaluation(args.report, assert_evaluation_report_complete=args.assert_evaluation_report_complete))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl evaluation 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-pre-verl-claim-gate":
        try:
            print(inspect_pre_verl_claim_gate(args.report, assert_claims_consistent=args.assert_claims_consistent))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl claim gate 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-pre-verl-evaluation-bundle":
        try:
            print(inspect_pre_verl_bundle(args.bundle, final_command_log=args.final_command_log, assert_immutable=args.assert_immutable))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl bundle 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-pre-verl-public-safe":
        try:
            print(inspect_pre_verl_public_safe(args.report, assert_share_safe=args.assert_share_safe))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl public-safe 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-pre-verl-readiness":
        try:
            print(inspect_pre_verl_readiness(args.report, assert_verl_ready=args.assert_verl_ready))
        except RepoHarnessError as exc:
            parser.exit(1, f"pre-verl readiness 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-stage14-fully-async-acceptance":
        try:
            print(
                inspect_stage14_fully_async_acceptance(
                    args.evidence,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"Stage 14 fully async acceptance 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-stage15-partial-rollout-acceptance":
        try:
            print(
                inspect_stage15_partial_rollout_acceptance(
                    args.evidence,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"Stage 15 partial rollout acceptance 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-stage16b5-docker-backend-acceptance":
        try:
            print(
                inspect_stage16b5_docker_backend_acceptance(
                    args.evidence,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"Stage 16B.5 Docker backend acceptance 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-stage16d-healthcheck":
        try:
            print(
                inspect_stage16d_healthcheck(
                    args.evidence,
                    assert_contract_complete=args.assert_contract_complete,
                    assert_official_healthcheck_complete=args.assert_official_healthcheck_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"Stage 16D healthcheck acceptance 检查失败：{exc}\n")
        return 0
    if args.command == "inspect-stage16f4-parity":
        try:
            print(
                inspect_stage16f4_parity(
                    args.evidence,
                    assert_complete=args.assert_complete,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"Stage 16F.4 parity acceptance 检查失败：{exc}\n")
        return 0
    if args.command == "build-stage14-remote-smoke-kit":
        try:
            result = write_stage14_remote_smoke_kit(args.output_dir)
        except RepoHarnessError as exc:
            parser.exit(1, f"Stage 14 remote smoke kit 构建失败：{exc}\n")
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    if args.command == "run-episode-task":
        try:
            run_dir = run_episode_task_command(
                args.task_path,
                config_path=args.config,
                output_dir=args.output_dir,
                run_id=args.run_id,
                gateway_route=args.gateway_route,
                assert_projection_complete=args.assert_projection_complete,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"run_episode 任务运行失败：{exc}\n")
        print(f"run_episode 任务运行完成：{run_dir}")
        return 0
    if args.command == "run-task":
        try:
            run_dir = run_task_command(
                args.task_path,
                config_path=args.config,
                output_dir=args.output_dir,
                run_id=args.run_id,
                inject_interrupt_after=args.inject_interrupt_after,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"任务运行失败：{exc}\n")
        print(f"任务运行完成：{run_dir}")
        config = load_run_config(args.config, output_dir=args.output_dir)
        if config.evaluation.fail_on_invalid_task and _run_outcome(run_dir) in {
            "invalid_task",
            "flaky_task",
        }:
            return 1
        return 0
    if args.command == "run-batch":
        try:
            manifest_path = run_batch_command(
                config_path=args.config,
                output_dir=args.output_dir,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"批量运行失败：{exc}\n")
        print(f"批量运行完成：{manifest_path}")
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        return 1 if manifest.get("should_fail_command") else 0
    if args.command == "run-experiment":
        try:
            manifest_path = run_experiment_command(
                config_path=args.config,
                output_dir=args.output_dir,
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"实验运行失败：{exc}\n")
        print(f"实验运行完成：{manifest_path}")
        return 0
    if args.command == "inspect-experiment":
        try:
            print(
                inspect_experiment_command(
                    args.experiment_dir,
                    minimums_path=args.assert_minimums,
                )
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"实验检查失败：{exc}\n")
        return 0
    if args.command == "export":
        try:
            output_path = export_run_or_runs(
                args.run_dir_or_runs_dir,
                export_format=args.format,
                compare_scope_path=args.compare_scope,
                policy=ExportPolicy(
                    allow_oracle_feedback_training=args.allow_oracle_feedback_training,
                    allow_provider_reasoning_trace_training=(
                        args.allow_provider_reasoning_trace_training
                    ),
                    filter_rules=[
                        *(
                            ["allow_oracle_feedback_training"]
                            if args.allow_oracle_feedback_training
                            else []
                        ),
                        *(
                            ["allow_provider_reasoning_trace_training"]
                            if args.allow_provider_reasoning_trace_training
                            else []
                        ),
                    ],
                ),
            )
        except RepoHarnessError as exc:
            parser.exit(1, f"导出失败：{exc}\n")
        print(f"导出完成：{output_path}")
        return 0
    parser.error(f"命令 {args.command!r} 尚未在当前阶段实现")
    return 2


def _run_outcome(run_dir: str | Path) -> str | None:
    metrics_path = Path(run_dir) / "metrics.json"
    if not metrics_path.exists():
        return None
    return json.loads(metrics_path.read_text(encoding="utf-8")).get("run_outcome")


if __name__ == "__main__":
    raise SystemExit(main())
