"""Rh2MilesGenerateFn（miles 新签名类形态）契约测试。

需要 miles.rollout.base_types（GenerateFnInput/Output）——该链模块级拉
sglang，conftest 的 install_sglang_stub() 先行（CPU 环境噪音，真实训练
环境有真 sglang）。
"""

from __future__ import annotations

from argparse import Namespace
from types import SimpleNamespace

import pytest


class _FakeOrchestrator:
    """rh2 RolloutOrchestrator.generate 的最小同形替身：返回预置输出。"""

    def __init__(self, result_fn):
        self._result_fn = result_fn
        self.calls: list[tuple] = []

    async def generate(self, args, sample, sampling_params, evaluation=False):
        self.calls.append((args, sample, sampling_params, evaluation))
        return self._result_fn(sample)


def _mk_input(world, orchestrator, sample, evaluation=False):
    from miles.rollout.base_types import GenerateFnInput

    args = Namespace(rh2_orchestrator=orchestrator)
    # GenerateFnInput.state 只被本链用作 args 载体（.args property）
    state = SimpleNamespace(args=args)
    return GenerateFnInput(state=state, sample=sample, sampling_params={"top_p": 1.0}, evaluation=evaluation)


async def test_generate_fn_canonicalizes_vendor_fanout(world):
    world.install_sglang_stub()
    from miles.rollout.base_types import GenerateFnOutput

    inp = world.mk_miles_input(index=1, group_index=0)
    orch = _FakeOrchestrator(
        lambda sample: [
            world.mk_vendor_sample(index=1, rollout_id=42),
            world.mk_vendor_sample(index=1, rollout_id=42, truncated=True),
        ]
    )
    fn = world.Rh2MilesGenerateFn()
    out = await fn(_mk_input(world, orch, inp))

    assert isinstance(out, GenerateFnOutput)
    samples = out.samples
    assert isinstance(samples, list) and len(samples) == 2
    assert all(isinstance(s, world.MS) for s in samples)
    assert samples[0].status is world.MS.Status.COMPLETED
    assert samples[1].status is world.MS.Status.TRUNCATED  # metadata 升级链在新签名入口生效
    assert samples[0].rollout_id == samples[1].rollout_id == 42
    assert samples[0].routing_key == inp.routing_key  # 输入侧字段保留

    # legacy 调用面：args/sample/sampling_params/evaluation 原样透传
    (args, sample, sampling_params, evaluation), = orch.calls
    assert sample is inp
    assert sampling_params == {"top_p": 1.0}
    assert evaluation is False


async def test_generate_fn_passthrough_abort_shape(world):
    """abort 收口路径：编排层原地改写输入样本并返回 [同对象]——canonicalize
    直通分支剥除 session_id 后原样返回。"""

    world.install_sglang_stub()

    def abort_result(sample):
        sample.tokens = [0, 0]
        sample.response_length = 1
        sample.loss_mask = [0]
        sample.rollout_log_probs = [0.0]
        sample.reward = 0.0
        sample.remove_sample = True
        sample.status = world.MS.Status.ABORTED
        sample.metadata = {"abort_reason": "rh2_gate_degraded"}
        sample.session_id = "sid-x"
        return [sample]

    inp = world.mk_miles_input(index=0)
    fn = world.Rh2MilesGenerateFn()
    out = await fn(_mk_input(world, _FakeOrchestrator(abort_result), inp))
    (s,) = out.samples
    assert s is inp
    assert s.status is world.MS.Status.ABORTED
    assert "session_id" not in s.__dict__


async def test_generate_fn_orchestrator_missing_triggers_bootstrap_fail_closed(
    world, monkeypatch
):
    """args 缺 rh2_orchestrator：B1（R6-ext）后不再直接抛
    orchestrator_not_configured，而是惰性走既有 bringup
    （ensure_fa_started -> BringupService.get）。本用例的 args 缺全部
    bringup 配置面（hf_checkpoint 等）——启动必须异常传播（fail-closed，
    不静默吞掉继续跑），且 BringupService 按单代语义 latch FAILED。

    monkeypatch 隔离单例类状态与模块级启动锁：本测试故意制造 FAILED，
    不得泄漏到同进程其他 bringup 测试。"""

    import asyncio

    world.install_sglang_stub()
    import repoharness2.adapters.slime.bringup as bringup

    monkeypatch.setattr(bringup.BringupService, "_instance", None)
    monkeypatch.setattr(bringup.BringupService, "_startup_state", "NEW")
    monkeypatch.setattr(bringup.BringupService, "_startup_error", None)
    monkeypatch.setattr(bringup, "_SERVICE_LOCK", asyncio.Lock())

    fn = world.Rh2MilesGenerateFn()
    inp = world.mk_miles_input()
    from miles.rollout.base_types import GenerateFnInput

    gi = GenerateFnInput(
        state=SimpleNamespace(args=Namespace()), sample=inp, sampling_params={}, evaluation=False
    )
    with pytest.raises(Exception):  # noqa: B017 - 启动首因类型不固定（缺字段即炸）
        await fn(gi)
    assert bringup.BringupService._startup_state == "FAILED"  # 单代 latch
    assert getattr(gi.args, "rh2_orchestrator", None) is None  # 不留半成品注入


async def test_generate_fn_passes_moe_config_for_routing_tape(world):
    """F4 透传面：generate_fn 从 args.rh2_orchestrator.config 取
    moe_num_layers/moe_router_topk 交给 canonicalize（与 backfill 同源，
    generate.py RolloutOrchestrator 调 backfill_leaf_sample 用的同一份
    config）。属性链任何一环改名/断裂都会让 R3-on 样本被 config_missing
    拒绝——本用例把该回归从"GPU 上才发现"提前到 CPU。"""

    import numpy as np

    world.install_sglang_stub()

    rows, layers, topk = 4, 2, 3  # mk_vendor_sample tokens=5 -> rows=4
    flat = list(range(rows * layers * topk))
    orch = _FakeOrchestrator(
        lambda sample: [world.mk_vendor_sample(rollout_routed_experts=list(flat))]
    )
    orch.config = SimpleNamespace(moe_num_layers=layers, moe_router_topk=topk)

    fn = world.Rh2MilesGenerateFn()
    out = await fn(_mk_input(world, orch, world.mk_miles_input()))
    (s,) = out.samples
    arr = s.rollout_routed_experts
    assert isinstance(arr, np.ndarray) and arr.dtype == np.int32
    assert arr.shape == (rows, layers, topk)
    assert arr.reshape(-1).tolist() == flat


async def test_generate_fn_moe_config_missing_tape_present_fail_closed(world):
    """F4 反向：orchestrator.config 缺 moe 期望（或属性链断裂取到 None）而
    tape 在场——必须 config_missing 拒绝，不允许静默猜形状/静默丢 tape。"""

    world.install_sglang_stub()
    from repoharness2.adapters.miles.canonicalize import CanonicalizationError

    orch = _FakeOrchestrator(
        lambda sample: [world.mk_vendor_sample(rollout_routed_experts=[0] * 24)]
    )
    orch.config = SimpleNamespace(moe_num_layers=None, moe_router_topk=None)

    fn = world.Rh2MilesGenerateFn()
    with pytest.raises(CanonicalizationError, match="routed_experts_config_missing"):
        await fn(_mk_input(world, orch, world.mk_miles_input()))


def test_miles_loader_instantiates_class_form(world):
    """miles load_generate_function 对类路径直接实例化（不套 Legacy adapter）。"""

    world.install_sglang_stub()
    from miles.rollout.inference_rollout.compatibility import (
        LegacyGenerateFnAdapter,
        load_generate_function,
    )

    fn = load_generate_function("repoharness2.adapters.miles.generate_fn.Rh2MilesGenerateFn")
    assert isinstance(fn, world.Rh2MilesGenerateFn)
    assert not isinstance(fn, LegacyGenerateFnAdapter)


def test_vendor_slime_priority(world):
    """本目录测试世界里 slime 必须解析到 vendor（rh2/src/slime）。

    单独跑本目录时 reference/slime 根本不进 sys.path；整仓套件混跑时其他
    目录可能已把 reference/slime 插进 path——那种情况下断言收敛为
    "vendor 排位必须更靠前 + 实际解析到 vendor"（conftest 的 module 级
    fixture 保证）。"""

    import sys
    from pathlib import Path

    import slime
    import slime.agent.trajectory as traj
    import slime.utils.types as st

    for mod in (slime, traj, st):
        assert Path(mod.__file__).resolve().is_relative_to(world.rh2_src), mod.__file__

    vendor_pos = sys.path.index(str(world.rh2_src))
    ref_positions = [i for i, p in enumerate(sys.path) if "reference/slime" in p]
    assert all(vendor_pos < i for i in ref_positions), (vendor_pos, ref_positions)
