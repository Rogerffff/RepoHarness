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
from repo_harness.export import export_run_or_runs
from repo_harness.tasks import load_task
from repo_harness.trajectory import inspect_run


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

    inspect_run = subparsers.add_parser(
        "inspect-run",
        help="只读检查 run directory。",
    )
    inspect_run.add_argument("run_dir", help="run directory 路径。")

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
    if args.command == "export":
        try:
            output_path = export_run_or_runs(
                args.run_dir_or_runs_dir,
                export_format=args.format,
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
