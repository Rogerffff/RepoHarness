#!/usr/bin/env python3
"""`scripts/replay_grade.py` 的评分预算包装（2026-09-29，B 线 R2E 探针原型）：只放宽评分 spec 的 `env_reset_timeout_seconds`，
其余逐字执行原脚本（同一进程、同一参数）。

`env_reset_timeout_seconds`（`GradingEnvSpec` 缺省 300 s，CLI 与环境变量都调不了）同时是 grader 里"基线重建 census"与
"控制面保护"（`grader_protect_control_surface_script` 的 `chown -R <评分用户> /testbed`）两步的时限。R2E 的 `.venv` 在
/testbed 里，orange3 / datalad 这类环境大的题，chown 会让 overlay 把整棵树复制一遍；本机多路评分并发时这一步超过
300 s，记 `failed_to_grade / infra_failure: grading_control_surface_protect_timeout_after_300s`（同时段协调者自己的账本
里 datalad 与 orange3 也是这个结果）。这是预算，不是评分语义：放宽后每一步做的事不变，账本照常记录各段耗时。

    <rh2>/.venv/bin/python experiments/r2e_lifecycle_20260929/replay_grade_budget.py --env-reset-timeout 1200 -- run <replay_grade 参数…>
"""

from __future__ import annotations

import dataclasses
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RH2 = HERE.parents[1]
sys.path.insert(0, str(RH2 / "src"))


def main() -> None:
    argv = sys.argv[1:]
    if "--" not in argv or argv[0] != "--env-reset-timeout":
        raise SystemExit("用法：replay_grade_budget.py --env-reset-timeout <秒> -- <replay_grade.py 参数>")
    timeout = float(argv[1])
    rest = argv[argv.index("--") + 1:]
    import repoharness2.adapters.slime.replay_grade as rg

    orig = rg.build_grading_spec_from_host_view

    def patched(*args, **kwargs):
        spec = orig(*args, **kwargs)
        return dataclasses.replace(spec, env_reset_timeout_seconds=max(timeout, spec.env_reset_timeout_seconds))

    rg.build_grading_spec_from_host_view = patched  # ReplayGrader.replay_one 按模块全局名取这个函数
    print(f'{{"replay_grade_budget": {{"env_reset_timeout_seconds": {timeout}}}}}', flush=True)
    sys.argv = [str(RH2 / "scripts" / "replay_grade.py"), *rest]
    runpy.run_path(str(RH2 / "scripts" / "replay_grade.py"), run_name="__main__")


if __name__ == "__main__":
    main()
