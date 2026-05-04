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
from repo_harness.evaluation.experiment import (
    inspect_experiment as inspect_experiment_command,
)
from repo_harness.evaluation.experiment import run_experiment as run_experiment_command
from repo_harness.export import ExportPolicy, export_run_or_runs, inspect_export
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
        choices=["sft_jsonl", "rl_jsonl", "preference_jsonl"],
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
        choices=["sft_jsonl", "rl_jsonl", "preference_jsonl"],
        default=None,
        help="只检查指定导出格式。",
    )
    inspect_export_parser.add_argument("--assert-clean", action="store_true", help="发现导出审计问题时返回失败。")
    inspect_export_parser.add_argument(
        "--require-trainable-samples",
        action="store_true",
        help="要求至少有一个 trainable 样本进入正式训练数据文件。",
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
                    filter_rules=(
                        ["allow_oracle_feedback_training"]
                        if args.allow_oracle_feedback_training
                        else []
                    ),
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
