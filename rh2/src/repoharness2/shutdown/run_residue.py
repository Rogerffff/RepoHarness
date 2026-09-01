#!/usr/bin/env python3
"""按 run-label 的兜底清理 + 无残留检查（W5a：campaign supervisor 缩为 launch trap）。

背景：就绪稿 §2.6 允许 campaign supervisor 在进程退出后按 run label 清理并核对
残留；06 计划 W5a 行把它缩成两件事——**一个能被 launch 脚本 `trap` 调用的清理
入口**和**一个"列出残留即失败"的检查**。没有常驻进程、没有账本、没有授权语义。

归属锚点 = docker 容器 label `rh2.run_id=<run_id>`：launch 经 Ray runtime env
下发 `MILES_RH2_RUN_ID` 后，rollout 容器（`adapters/slime/generate.py`）与评分容器
（`grading/manager.py`）启动时都盖这个 label。本工具**只动带本 run label 的容器**
——同宿主上其他 run / 其他人的容器一律不碰（这是它和 `SWEGradingManager.startup`
的年龄式孤儿清扫的区别）。工作区/临时目录按显式给出的 glob 处理（RH2 目前不在
宿主上创建 per-run 临时目录，此项留给 launch 按需传入）。

两个纪律：

- **查询失败 ≠ 零残留**：docker 不可用、非零退出、超时都记 `query_ok=false`
  并让 `check` 非零退出（与 `postrun_probes.py` shutdown 探针同口径）；
- **清理先记后删**：`cleanup` 先把将要删除的容器名/目录写进报告再执行 `rm -f`，
  被删掉的隔离容器（receipt 写失败时 generate.py 故意保留的现场）名字不会丢——
  它们的 receipt/audit 证据本来就在 artifact 目录里，容器本身在共享 GPU 机上
  不能留。

纯 stdlib、无包内 import：可以 `python3 -m repoharness2.shutdown.run_residue …`，
也可以直接按文件路径运行（launch trap 里 PYTHONPATH 未必就位）。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "RUN_LABEL_KEY",
    "check_residue",
    "cleanup_residue",
    "list_run_containers",
    "main",
    "remove_containers",
    "tmp_residue",
]

RUN_LABEL_KEY = "rh2.run_id"
DOCKER_TIMEOUT_SEC = 30.0
RESIDUE_SCHEMA_ID = "rh2.run_residue_report.v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_run_containers(docker_bin: str, run_id: str, *, timeout: float = DOCKER_TIMEOUT_SEC) -> tuple[list[str] | None, str | None]:
    """`docker ps -a --filter label=rh2.run_id=<run_id>`（含已退出未删除的容器）。

    返回 (names, error)：查询失败时 names=None 且 error 非空。
    """

    if not run_id:
        return None, "run_id 为空：没有归属锚点，拒绝按空 label 查询"
    try:
        proc = subprocess.run(
            [docker_bin, "ps", "-a", "--filter", f"label={RUN_LABEL_KEY}={run_id}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001 —— 失败是显式事实，不是零
        return None, f"docker ps failed: {type(exc).__name__}: {exc}"
    if proc.returncode != 0:
        return None, f"docker ps rc={proc.returncode}: {proc.stderr.strip()[-300:]}"
    return sorted({line.strip() for line in proc.stdout.splitlines() if line.strip()}), None


def remove_containers(docker_bin: str, names: list[str], *, timeout: float = DOCKER_TIMEOUT_SEC) -> tuple[list[str], dict[str, str]]:
    removed: list[str] = []
    failed: dict[str, str] = {}
    for name in names:
        try:
            proc = subprocess.run([docker_bin, "rm", "-f", name], capture_output=True, text=True, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            failed[name] = f"{type(exc).__name__}: {exc}"
            continue
        if proc.returncode == 0:
            removed.append(name)
        else:
            failed[name] = f"rc={proc.returncode}: {proc.stderr.strip()[-300:]}"
    return removed, failed


def tmp_residue(globs: list[str]) -> list[str]:
    """显式 glob 命中的工作区/临时目录（空 glob 列表 = 该面不适用，返回空）。"""

    hits: set[str] = set()
    for pattern in globs:
        for match in glob.glob(pattern):
            hits.add(os.path.abspath(match))
    return sorted(hits)


def cleanup_residue(
    *,
    run_id: str,
    docker_bin: str,
    tmp_globs: list[str],
    timeout: float = DOCKER_TIMEOUT_SEC,
) -> dict[str, Any]:
    """兜底清理：先记录再删除。返回报告 dict（`ok` = 查询成功且全部删除成功）。"""

    report: dict[str, Any] = {
        "schema_id": RESIDUE_SCHEMA_ID,
        "action": "cleanup",
        "run_id": run_id,
        "taken_at_utc": _now(),
        "docker_query_ok": False,
        "containers_found": None,
        "containers_removed": [],
        "containers_failed": {},
        "tmp_found": [],
        "tmp_removed": [],
        "tmp_failed": {},
        "detail": {},
    }
    names, error = list_run_containers(docker_bin, run_id, timeout=timeout)
    if names is None:
        report["detail"]["docker_error"] = error
    else:
        report["docker_query_ok"] = True
        report["containers_found"] = names
        removed, failed = remove_containers(docker_bin, names, timeout=timeout)
        report["containers_removed"] = removed
        report["containers_failed"] = failed
    found = tmp_residue(tmp_globs)
    report["tmp_found"] = found
    for path in found:
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
            report["tmp_removed"].append(path)
        except OSError as exc:
            report["tmp_failed"][path] = f"{type(exc).__name__}: {exc}"
    report["ok"] = bool(
        report["docker_query_ok"] and not report["containers_failed"] and not report["tmp_failed"]
    )
    return report


def check_residue(
    *,
    run_id: str,
    docker_bin: str,
    tmp_globs: list[str],
    timeout: float = DOCKER_TIMEOUT_SEC,
) -> dict[str, Any]:
    """无残留检查：列出残留即失败；查询失败也失败（不冒充零）。"""

    report: dict[str, Any] = {
        "schema_id": RESIDUE_SCHEMA_ID,
        "action": "check",
        "run_id": run_id,
        "taken_at_utc": _now(),
        "docker_query_ok": False,
        "containers": None,
        "tmp": [],
        "detail": {},
    }
    names, error = list_run_containers(docker_bin, run_id, timeout=timeout)
    if names is None:
        report["detail"]["docker_error"] = error
    else:
        report["docker_query_ok"] = True
        report["containers"] = names
    report["tmp"] = tmp_residue(tmp_globs)
    report["residue_count"] = (len(names) if names is not None else None)
    if report["residue_count"] is not None:
        report["residue_count"] += len(report["tmp"])
    report["ok"] = bool(report["docker_query_ok"] and report["residue_count"] == 0)
    return report


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("cleanup", "check"):
        p = sub.add_parser(name)
        p.add_argument("--run-id", required=True, help="本 run 的唯一 id（容器 label rh2.run_id=<id>）")
        p.add_argument("--docker-bin", default="docker", help="docker CLI 路径（launch preflight 验证过的那一个）")
        p.add_argument("--tmp-glob", action="append", default=[], help="工作区/临时目录 glob，可重复；不传 = 该面不适用")
        p.add_argument("--out", default=None, help="报告 JSON 输出路径（可选）")
        p.add_argument("--timeout", type=float, default=DOCKER_TIMEOUT_SEC)
    args = parser.parse_args(argv)
    fn = cleanup_residue if args.cmd == "cleanup" else check_residue
    report = fn(run_id=args.run_id, docker_bin=args.docker_bin, tmp_globs=list(args.tmp_glob), timeout=args.timeout)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
