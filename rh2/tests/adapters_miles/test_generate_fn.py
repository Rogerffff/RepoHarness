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


async def test_generate_fn_orchestrator_missing_fails_closed(world):
    """args 缺 rh2_orchestrator：legacy 入口的 fail-closed 在新签名下保留。"""

    world.install_sglang_stub()
    from repoharness2.adapters.slime.generate import SlimeBindingError

    fn = world.Rh2MilesGenerateFn()
    inp = world.mk_miles_input()
    from miles.rollout.base_types import GenerateFnInput

    gi = GenerateFnInput(
        state=SimpleNamespace(args=Namespace()), sample=inp, sampling_params={}, evaluation=False
    )
    with pytest.raises(SlimeBindingError, match="orchestrator_not_configured"):
        await fn(gi)


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
