"""RepoHarness 第一版命令行入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from repo_harness import __version__
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
        help="运行单个任务的完整闭环。阶段一暂未实现执行逻辑。",
    )
    run_task.add_argument("task_path", help="任务 YAML 文件路径。")
    run_task.add_argument("--config", required=True, help="RunConfig YAML 文件路径。")
    run_task.add_argument("--output-dir", default=None, help="运行产物根目录。")
    run_task.add_argument("--run-id", default=None, help="显式指定本次 run id。")

    run_batch = subparsers.add_parser(
        "run-batch",
        help="按 RunConfig 顺序运行任务列表。阶段一暂未实现执行逻辑。",
    )
    run_batch.add_argument("--config", required=True, help="RunConfig YAML 文件路径。")
    run_batch.add_argument("--output-dir", default=None, help="运行产物根目录。")

    export = subparsers.add_parser(
        "export",
        help="从已有 run directory 导出训练数据。阶段一暂未实现执行逻辑。",
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
        help="只读检查 run directory。阶段一暂未实现读取逻辑。",
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
    if args.command == "inspect-run":
        print(inspect_run(args.run_dir))
        return 0
    parser.error(f"命令 {args.command!r} 尚未在当前阶段实现")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
