#!/usr/bin/env python3
"""S1-d（评分接线 2026-09-15）：真实评分链 driver 的命令行入口。

子命令：
  prepare      受信准备（与 envpack.trusted_prep 同一入口）→ prepared/private 两目录 + replay_summary.json
  export-gold  从 validation bundle 导出 gold 为候选补丁文件（<iid>.gold.patch）
  run          对指定任务重放候选并经真实 SWEGradingManager（正式 grader profile）评分，写 JSONL 账本

示例（从 rh2/ 目录）：
  .venv/bin/python scripts/replay_grade.py prepare --repo-root .. --out-dir /work/replay/prepared --private-dir /work/replay/private \
      --task-ids swe_gym_lite::python__mypy-12741,swe_gym_lite::conan-io__conan-13326
  .venv/bin/python scripts/replay_grade.py export-gold --ingest-dir ../docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest \
      --instance-ids python__mypy-12741 --out-dir /work/replay/gold
  MILES_RH2_RUN_ID=replay-$(date +%Y%m%d) .venv/bin/python scripts/replay_grade.py run --prepared-summary /work/replay/prepared/replay_summary.json \
      --task-ids python__mypy-12741 --candidate gold-dir:/work/replay/gold --repeat 2 --eval-log-dir /work/replay/eval_logs \
      --artifacts-dir /work/replay/artifacts --ledger /work/replay/ledger.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from repoharness2.adapters.slime.replay_grade import (  # noqa: E402
    DerivedImage,
    ReplayBudgets,
    ReplayGrader,
    ReplayHaltError,
    candidate_from_spec,
    export_gold_candidates,
    load_context,
    prepare_for_replay,
    load_env_qualifications,
)
from repoharness2.adapters.slime.sandbox_profile import grader_profile_from_env, rollout_profile_from_env  # noqa: E402
from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager  # noqa: E402


def _split(csv: str | None) -> list[str]:
    return [x.strip() for x in (csv or "").split(",") if x.strip()]


async def _run(ns: argparse.Namespace) -> int:
    summary = json.loads(Path(ns.prepared_summary).read_text(encoding="utf-8"))
    env = os.environ
    rollout = rollout_profile_from_env(env, model_proxy_upstream_host="127.0.0.1", model_proxy_upstream_port=1)
    grader = grader_profile_from_env(env)
    derived = DerivedImage(ref=ns.derived_image, recipe=ns.derived_image_recipe or "unspecified") if ns.derived_image else None
    ctx = load_context(
        prepared_dir=summary["prepared_dir"], private_dir=summary["private_dir"],
        manifest_sha256=summary["prepared_manifest_sha256"], rollout_profile=rollout, grader_profile=grader,
        artifacts_dir=ns.artifacts_dir, run_id=env.get("MILES_RH2_RUN_ID"), derived_image=derived,
        qualifications=load_env_qualifications(ns.qualification_ledger),
    )
    print(json.dumps({"qualifications": len(ctx.qualifications), "from": ns.qualification_ledger}, ensure_ascii=False), flush=True)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=Path(ns.eval_log_dir), sandbox_profile=grader))
    await manager.startup()
    budgets = ReplayBudgets(
        candidate_stage_seconds=ns.candidate_stage_seconds, grading_deadline_seconds=ns.grading_deadline_seconds,
        cleanup_seconds=ns.cleanup_seconds, image_pull_seconds=ns.image_pull_seconds,
    )
    grader_run = ReplayGrader(ctx, manager, ledger_path=ns.ledger, budgets=budgets)
    tasks = _split(ns.task_ids) or list(ctx.grading_views)
    rows = 0
    halted: str | None = None
    try:
        for ref in tasks:
            if halted:
                break
            task_id = ctx.resolve_task_id(ref)
            instance_id = ctx.grading_views[task_id].instance_id
            candidate = candidate_from_spec(ns.candidate, instance_id=instance_id)
            for attempt in range(1, ns.repeat + 1):
                try:
                    row = await grader_run.replay_one(task_id, candidate, attempt=attempt)
                except ReplayHaltError as exc:
                    halted = str(exc)  # I2：候选容器无法确认清理 → 停止本批（账本行已写）
                    print(json.dumps({"halt": halted}, ensure_ascii=False), flush=True)
                    break
                rows += 1
                rep = row.get("report") or {}
                print(json.dumps({
                    "task_id": task_id, "attempt": attempt, "outcome": rep.get("outcome"), "reward": rep.get("reward"),
                    "apply_method": row["candidate"]["apply_method"], "stage_error": row.get("stage_error"),
                }, ensure_ascii=False), flush=True)
    finally:
        closed = await manager.close()
        print(json.dumps({"ledger": str(ns.ledger), "rows": rows, "manager_close": closed, "halted": halted,
                          "cleanup_failures": grader_run.cleanup_failures}, ensure_ascii=False, default=str))
    return 2 if halted else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="rh2 真实评分链重放 driver（S1-d）")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--repo-root", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--private-dir", required=True)
    p.add_argument("--task-ids", default=None, help="逗号分隔 source-qualified task_id（缺省全部）")
    g = sub.add_parser("export-gold")
    g.add_argument("--ingest-dir", required=True)
    g.add_argument("--instance-ids", required=True)
    g.add_argument("--out-dir", required=True)
    r = sub.add_parser("run")
    r.add_argument("--prepared-summary", required=True)
    r.add_argument("--task-ids", default=None, help="逗号分隔；可用裸 instance_id")
    r.add_argument("--candidate", required=True, help="noop | patch:<file> | gold-dir:<dir> | patch-dir:<dir>")
    r.add_argument("--repeat", type=int, default=1)
    r.add_argument("--candidate-stage-seconds", type=float, default=900.0)
    r.add_argument("--grading-deadline-seconds", type=float, default=3600.0)
    r.add_argument("--cleanup-seconds", type=float, default=120.0)
    r.add_argument("--image-pull-seconds", type=float, default=1800.0, help="首次拉镜像的独立预算")
    r.add_argument("--eval-log-dir", required=True)
    r.add_argument("--artifacts-dir", required=True)
    r.add_argument("--ledger", required=True)
    r.add_argument("--derived-image", default=None, help="D4=A 诊断性派生镜像引用（以 image_local_build 使用）")
    r.add_argument("--derived-image-recipe", default=None, help="派生镜像配方说明（进账本）")
    r.add_argument("--qualification-ledger", action="append", default=[],
                   help="P-A 环境资格来源账本（可重复）：取 gold/noop 成功且参考缺席 0 的行；manager 核对镜像身份与脚本摘要")
    ns = parser.parse_args(argv)
    if ns.cmd == "prepare":
        print(json.dumps(prepare_for_replay(repo_root=ns.repo_root, out_dir=ns.out_dir, private_dir=ns.private_dir, task_ids=_split(ns.task_ids)), ensure_ascii=False, indent=1))
        return 0
    if ns.cmd == "export-gold":
        print(json.dumps(export_gold_candidates(ingest_dir=ns.ingest_dir, instance_ids=_split(ns.instance_ids), out_dir=ns.out_dir), ensure_ascii=False, indent=1))
        return 0
    return asyncio.run(_run(ns))


if __name__ == "__main__":
    raise SystemExit(main())
