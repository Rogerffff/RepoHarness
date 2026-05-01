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
    if args.command == "run-task":
        try:
            run_dir = run_task_command(
                args.task_path,
                config_path=args.config,
                output_dir=args.output_dir,
                run_id=args.run_id,
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
