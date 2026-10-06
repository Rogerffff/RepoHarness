"""N1/N4 审查探针：调用真实汇总器和指标函数，不修改生产代码。

从 rh2 目录执行：uv run --no-sync python ../docs/.../observation_probe.py
这里只验证 CPU 数值与标量读取次数，不把结果称为 GPU 性能测量。
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def costs_probe():
    module = load_file("costs_review", ROOT / "rh2/src/repoharness2/adapters/miles/drop_events.py")

    def snapshot(run, paid, elapsed, *, reason=None, task="task_a"):
        return dict(event="attempt_cost_snapshot", run_id=run, physical_attempt_id=paid,
                    rh2_prompt_group_id="miles_g0", task_id=task, elapsed_seconds=elapsed,
                    reason_code=reason)

    def terminal(run, *, dropped=False, member_count=1, paid=None, task="task_a"):
        return dict(event="group_filtered" if dropped else "group_consumed", run_id=run,
                    rh2_prompt_group_id="miles_g0", task_id=task, member_count=member_count,
                    reason_code="aborted_member" if dropped else None,
                    drop_stage="put_aborted" if dropped else None,
                    aborted_members=[dict(physical_attempt_id=paid)] if dropped else [])

    rows = [snapshot("run_a", "a#p1", 10), terminal("run_a"),
            snapshot("run_b", "b#p1", 100), terminal("run_b", dropped=True, paid="b#p1")]
    mixed = module.summarize_attempt_costs(rows)
    isolated = {run: module.summarize_attempt_costs(rows, run_id=run) for run in ("run_a", "run_b")}
    unknown = module.summarize_attempt_costs([snapshot("run_a", "a#p1", None), terminal("run_a")])
    missing = module.summarize_attempt_costs(
        [snapshot("run_a", f"a#p{i}", 600) for i in range(7)] + [terminal("run_a", member_count=8)]
    )
    reasons = module.summarize_attempt_costs([
        snapshot("run_a", "a#p1", 10, reason="grading_image_pull_failed"),
        terminal("run_a", dropped=True, paid="a#p1"),
        {**snapshot("run_a", "a#p2", 900, reason="hard_wall_timeout", task="task_b"),
         "rh2_prompt_group_id": "miles_g1"},
        {**terminal("run_a", dropped=True, paid="a#p2", task="task_b"),
         "rh2_prompt_group_id": "miles_g1"},
    ])
    return dict(
        mixed_runs=mixed,
        isolated_runs=isolated,
        all_elapsed_unknown=unknown,
        one_of_eight_snapshots_missing=missing,
        different_reasons_and_tasks=reasons,
    )


def dis_probe():
    os.environ["RH2_MILES_PATH"] = str(ROOT / "reference/miles-rh2-integration")
    sys.path[:0] = [str(ROOT / "rh2/src"), str(ROOT / "rh2/tests/adapters_miles")]
    wc = load_file("world_review", ROOT / "rh2/tests/adapters_miles/conftest.py")
    setup = wc._vendor_slime_world.__wrapped__()
    next(setup)
    try:
        import torch
        import test_faithful_dis_loss as fixture
        from miles.backends.training_utils.sampling_mask import get_rollout_sampling_masks

        dis = fixture.dis.__wrapped__(wc._World())
        batch, _ = fixture._mk_case(torch)
        masks = get_rollout_sampling_masks(batch)
        reads = []
        original_item = torch.Tensor.item

        def tracked_item(self, *args, **kwargs):
            reads.append(sys._getframe(1).f_code.co_name)
            return original_item(self, *args, **kwargs)

        # 不替换被测函数、CSR 对象或 CP 切分；只记录 Tensor.item 的调用者。
        torch.Tensor.item = tracked_item
        try:
            ratio = torch.tensor(fixture._S0_TARGET_LOG_RATIO + fixture._S1_TARGET_LOG_RATIO)
            metrics = dis.module._dis_observation_metrics(
                sampling_masks=masks,
                total_lengths=batch["total_lengths"], response_lengths=batch["response_lengths"],
                local_lengths=batch["response_lengths"], qkv_format="thd", max_seq_lens=None,
                provenance_bool=torch.cat(batch["loss_masks"]).bool(),
                in_trust=(ratio > dis.module._LOG_TRUST_LOW) & (ratio < dis.module._LOG_TRUST_HIGH),
                log_ratio=ratio, advantages=torch.cat(batch["advantages"]), device=torch.device("cpu"),
            )
        finally:
            torch.Tensor.item = original_item
        return dict(cpu_only=True, scalar_item_calls=len(reads), callers=reads,
                    metrics={k: float(v) for k, v in metrics.items()})
    finally:
        try:
            next(setup)
        except StopIteration:
            pass


if __name__ == "__main__":
    out = dict(costs=costs_probe(), dis=dis_probe())
    print(json.dumps(out, ensure_ascii=False, indent=2))
