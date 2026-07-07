"""S1-7a T1 递延回归批处理（远程 x86 + 官方 SWE 镜像实机执行）。

三件事（envpack_freeze_v1.md §5 与 grading_p_matrix.md 末节的递延动作）：

1. **镜像 digest 实机比对**（S1-7a 前置修复 codex#1 的真实第一跑）：
   对 8 题官方镜像逐个 `docker image inspect`，把实际 RepoDigests 与
   frozen_v1 冻结的 image_manifest_digest 经 `materialize.evaluate_image_digest`
   比对（与运行期 fail-closed 同一判定函数）。
2. **8 题评分回归（S1-4 递延）**：每题起一个 workspace 容器（官方镜像，
   image_embedded 形态），把 S0-7 当时的模型 agent_diff 原样 `git apply` 进
   /testbed，然后走 SWEGradingManager.grade 全链（导出→清洗→fresh 容器
   clean checkout→重放→官方测试→官方 parser），逐题对照 S0-7 落盘的
   resolution / apply_ok / reward（f2p/p2p 计数一并记录）。
3. **TESTS_ERROR / apply_ok=false 频率统计（codex#4）**：统计本批评分中
   官方日志 verdict.apply_ok=false（TESTS_ERROR/RESET_FAILED 族坏码）与
   infra 族归因的出现次数，为"是否拆分解析器失败 vs 模型补丁合法失败"提供
   实测频率。

用法（远程机 rh2/ 根）::

    .venv/bin/python experiments/s1_7a_t1_regression.py \
        --dumps-dir ../docs/agentic_RL/repo_harness_rh2_workstreams/s0/swe_smoke_dumps \
        --out /root/s1_7a_logs/t1_regression_report.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

RH2_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RH2_ROOT / "src"))

from repoharness2.envpack import bundles, materialize  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    BASE_UNTRACKED_MANIFEST,
    BASE_UNTRACKED_SNAPSHOT_SCRIPT,
    SWEGradingManager,
    build_swe_grading_spec,
    run_docker,
)

INSTANCES = [
    "django__django-11099",
    "django__django-11133",
    "django__django-16139",
    "sympy__sympy-14711",
    "sympy__sympy-15349",
    "psf__requests-1142",
    "psf__requests-2931",
    "astropy__astropy-14995",
]


class WorkspaceContainer:
    """评分 manager 期望的 WorkspaceRunner 形状（rollout 容器替身）。"""

    def __init__(self, name: str, testbed: str = "/testbed") -> None:
        self.name = name
        self.testbed = testbed

    async def run_bash(self, script: str):
        return await run_docker(
            "exec", self.name, "bash", "-c", f"cd {self.testbed} && {script}"
        )


async def verify_image_digest(pair) -> dict:
    """镜像 digest 实机比对（与运行期 _verify_image_digest 同判定路径）。"""

    digests = await run_docker(
        "image", "inspect", "-f", materialize.IMAGE_REPO_DIGESTS_FORMAT, pair.public.image
    )
    check = materialize.evaluate_image_digest(
        pair.public.image_manifest_digest, digests.exit_code, digests.stdout, digests.stderr
    )
    return {
        "instance_id": pair.instance_id,
        "image": pair.public.image,
        "frozen_manifest_digest": pair.public.image_manifest_digest,
        "runtime_repo_digests_raw": digests.stdout.strip()[:400],
        "digest_check_ok": check.ok,
        "failure": None if check.ok else check.failure_message()[:300],
    }


async def grade_one(manager: SWEGradingManager, pair, agent_diff: str) -> dict:
    """起 workspace 容器 -> 应用 S0-7 agent_diff -> manager.grade 全链。"""

    name = f"rh2-t1-{pair.instance_id.replace('__', '-')[:40]}-{uuid.uuid4().hex[:6]}"
    started = time.monotonic()
    result: dict = {"instance_id": pair.instance_id, "workspace_container": name}
    run = await run_docker(
        "run", "--detach", "--name", name, pair.public.image, "sleep", "infinity"
    )
    if run.exit_code != 0:
        raise RuntimeError(f"workspace 容器启动失败: {run.stderr[-300:]}")
    try:
        # 与真实 rollout 物化同纪律：agent（此处 = S0-7 diff 应用）动工前
        # 存基线未跟踪清单，导出按清单排除镜像自带残留（psf__requests-1142
        # 的 build/lib/** 实测反例）。
        snapshot = await run_docker(
            "exec",
            name,
            "bash",
            "-c",
            "cd /testbed && "
            + BASE_UNTRACKED_SNAPSHOT_SCRIPT.format(manifest=BASE_UNTRACKED_MANIFEST),
        )
        if snapshot.exit_code != 0:
            raise RuntimeError(f"基线未跟踪清单生成失败: {snapshot.stderr[-300:]}")
        baseline = await run_docker("exec", name, "bash", "-c", f"wc -l < {BASE_UNTRACKED_MANIFEST}")
        result["base_untracked_count"] = int(baseline.stdout.strip() or 0)

        apply = await run_docker(
            "exec",
            "-i",
            name,
            "bash",
            "-c",
            "cd /testbed && git apply --whitespace=nowarn -",
            input_bytes=agent_diff.encode(),
        )
        result["workspace_apply_exit"] = apply.exit_code
        if apply.exit_code != 0:
            result["workspace_apply_stderr"] = apply.stderr[-300:]
            raise RuntimeError(f"S0-7 agent_diff 应用失败: {apply.stderr[-300:]}")

        report = await manager.grade(
            trajectory_id=f"t1_regress_{pair.instance_id}",
            workspace=WorkspaceContainer(name),
            spec=build_swe_grading_spec(pair),
        )
        result["report"] = json.loads(report.model_dump_json())
        result["grade_wall_seconds"] = round(time.monotonic() - started, 2)
        return result
    finally:
        await run_docker("rm", "-f", name)


def compare_with_s0(report: dict, s0_summary: dict) -> dict:
    """对照 S0-7 直评：resolution 语义 / apply_ok / reward（§5 判据字段）。"""

    s0_reward = s0_summary["reward"]
    s0_resolution = s0_summary["resolution"]  # RESOLVED_FULL / RESOLVED_NO
    s0_apply_ok = bool(s0_summary["metrics"].get("eval_apply_ok", 0.0) == 1.0)

    got_outcome = report["outcome"]  # resolved / unresolved / failed_to_grade
    got_reward = report["reward"]
    # manager 报告没有 resolution 字符串；等价映射：resolved<=>RESOLVED_FULL，
    # unresolved(tests_failed)<=>RESOLVED_NO/PARTIAL。
    resolution_match = (
        (s0_resolution == "RESOLVED_FULL" and got_outcome == "resolved")
        or (s0_resolution in ("RESOLVED_NO", "RESOLVED_PARTIAL") and got_outcome == "unresolved")
    )
    return {
        "s0": {"resolution": s0_resolution, "reward": s0_reward, "apply_ok": s0_apply_ok},
        "got": {
            "outcome": got_outcome,
            "reward": got_reward,
            "failure_category": report.get("failure_category"),
            "f2p": [report.get("f2p_pass_count"), report.get("f2p_total_count")],
            "p2p_fail": [report.get("p2p_fail_count"), report.get("p2p_total_count")],
        },
        "resolution_match": resolution_match,
        "reward_match": got_reward == s0_reward,
        "all_match": resolution_match and got_reward == s0_reward,
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dumps-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--subset", nargs="*", default=None)
    args = ap.parse_args()
    dumps_dir = Path(args.dumps_dir)

    wanted = args.subset or INSTANCES
    pairs = bundles.load_bundle_pairs(subset=wanted)  # 默认防漂移校验（frozen_v1 对照）

    out: dict = {
        "what": "S1-7a T1: image digest verify + 8-task grading regression vs S0-7",
        "digest_checks": [],
        "gradings": [],
        "stats": {
            "graded": 0,
            "verdict_apply_ok_false": 0,  # codex#4：官方日志坏码族（本地 apply 成功前提下）
            "infra_failure": 0,
            "test_log_parse_failed": 0,
            "outcome_counts": {},
        },
    }

    for pair in pairs:
        out["digest_checks"].append(await verify_image_digest(pair))

    manager = SWEGradingManager()
    await manager.startup()

    all_match = True
    for pair in pairs:
        dump = json.loads((dumps_dir / f"{pair.instance_id}.json").read_text())
        agent_diff = dump["trace"]["info"]["agent_diff"]
        entry = await grade_one(manager, pair, agent_diff)
        report = entry["report"]
        entry["compare"] = compare_with_s0(report, dump["summary"])
        all_match = all_match and entry["compare"]["all_match"]
        out["gradings"].append(entry)

        stats = out["stats"]
        stats["graded"] += 1
        oc = report["outcome"]
        stats["outcome_counts"][oc] = stats["outcome_counts"].get(oc, 0) + 1
        fc = report.get("failure_category")
        if fc == "infra_failure":
            stats["infra_failure"] += 1
        if fc == "test_log_parse_failed":
            stats["test_log_parse_failed"] += 1
            stats["verdict_apply_ok_false"] += 1  # 该归因唯一来源即坏码族（manager:991）

    out["digest_all_ok"] = all(c["digest_check_ok"] for c in out["digest_checks"])
    out["regression_all_match"] = all_match
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(
        f"digest_all_ok={out['digest_all_ok']} regression_all_match={all_match} "
        f"stats={json.dumps(out['stats'])}"
    )
    return 0 if (out["digest_all_ok"] and all_match) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
