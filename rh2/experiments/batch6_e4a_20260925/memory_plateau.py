"""E4a 内存平台期（CPU，FakeDocker profile 路径；组件级，不代表真实 run 的总内存）。

同一评分流程连评 N 次，按检查点记录 `_records` 长度与 tracemalloc 当前分配；对照组把 container_history_limit 设成
极大值（相当于修前的"只 append 不裁剪"）。用法（rh2/）：.venv/bin/python experiments/batch6_e4a_20260925/memory_plateau.py {bounded_256|unbounded_control}
"""

from __future__ import annotations

import asyncio
import gc
import json
import sys
import tracemalloc
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path[:0] = [str(HERE.parents[2] / "tests" / "grading"), str(HERE.parents[2] / "tests")]

from grading_fixtures import GOOD_FAKE_LOG, GOOD_PATCH, FakeWorkspace  # noqa: E402
from sandbox_test_support import make_grader_profile  # noqa: E402
from test_w3b_grader_profile_unit import BASE_COMMIT, ProfileGraderFakeDocker, _spec  # noqa: E402

from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager  # noqa: E402

CHECKPOINTS = (100, 256, 400, 600, 800)
# 每次评分的解析结果与诊断带一段约 20 KB 的日志，放大单条记录的占用，让增长趋势可见
BIG_LOG = GOOD_FAKE_LOG + "".join(f"tests/test_x.py::test_{i} PASSED\n" for i in range(600))


async def run(limit: int) -> list[dict]:
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=BIG_LOG)
    manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile(), container_history_limit=limit),
                                docker=docker)
    out = []
    tracemalloc.start()
    for i in range(1, max(CHECKPOINTS) + 1):
        report = await manager.grade(trajectory_id=f"t{i}", workspace=FakeWorkspace(GOOD_PATCH), spec=_spec())
        manager.take_grader_phase_timing(report.timings.record_id)  # 生产里 orchestrator 逐次取走
        # 替身自己的记账（调用、输入、删除名单、run 参数）不属于 manager，逐次清掉
        for bucket in (docker.calls, docker.exec_sequence, docker.input_payloads, docker.removed,
                       docker.profile_fake.exec_scripts):
            bucket.clear()
        docker.profile_fake.run_args_by_name.clear()
        await asyncio.sleep(0)  # 让事件循环跑一轮（替身不挂起；真实 docker 调用会挂起，loop 借此清掉已取消的定时器）
        if i in CHECKPOINTS:
            gc.collect()
            current, _peak = tracemalloc.get_traced_memory()
            out.append({"grades": i, "records": len(manager.container_records), "traced_mib": round(current / 2**20, 2)})
    tracemalloc.stop()
    return out


async def main(mode: str) -> None:
    limit = 256 if mode == "bounded_256" else 10**9
    print(json.dumps({mode: await run(limit)}))


if __name__ == "__main__":
    # 每种配置单独一个进程跑（tracemalloc 只计本进程开始追踪后的分配，同进程先后两跑不可比）
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "bounded_256"))
