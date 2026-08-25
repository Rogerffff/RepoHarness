"""C1′-b delta 测试 (c)：canonicalize 的 sampling-mask 扩表。

覆盖面：
- slime->miles 构造分支：装配 mask（rh2_sampling_mask 附加属性）转
  miles `RolloutSamplingMask` 一等字段（CSR ids int32 / offsets int64）;
- replay 开启（rollout_top_p<1.0）无 mask 的 fail-closed 拒绝;闸关闭
  （None / 1.0）时无 mask 直通;
- 附加属性类型/长度错误拒绝;pin base（无一等字段）拒绝（monkeypatch 模拟）;
- miles 直通分支：rollout_sampling_mask 原样保留;
- generate_fn 闸透传：args.rollout_top_p 经 Rh2MilesGenerateFn 进 canonicalize。
"""

from __future__ import annotations

from argparse import Namespace
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.integration_base


@pytest.fixture()
def sma(world):
    from repoharness2.adapters.miles import sampling_mask_assembly as module

    return module


def _assembled_for_vendor_sample(sma):
    """world.mk_vendor_sample 形状（tokens[10..14],response_length=3,
    loss_mask=[1,0,1]）对应的装配 mask：采样位 12/14,观察位 13 单例。"""

    turns = [
        sma.TurnSupport(output_ids=(12,), supports=((12, 5),)),
        sma.TurnSupport(output_ids=(14,), supports=((14, 6, 7),)),
    ]
    return sma.assemble_leaf_sampling_mask([12, 13, 14], [1, 0, 1], turns)


def test_slime_branch_converts_attached_mask_to_first_class_field(world, sma):
    import torch

    sample = world.mk_vendor_sample()
    assembled = _assembled_for_vendor_sample(sma)
    sma.attach_assembled_mask(sample, assembled)

    out = world.canonicalize_sample(
        sample, miles_input_sample=world.mk_miles_input(), rollout_top_p=0.8
    )
    mask = out.rollout_sampling_mask
    from miles.utils.sampling_mask import RolloutSamplingMask

    assert isinstance(mask, RolloutSamplingMask)
    ids, offsets = mask._as_tensors()
    assert ids.tolist() == [12, 5, 13, 14, 6, 7]
    assert offsets.tolist() == [0, 2, 3, 6]
    assert ids.dtype == torch.int32 and offsets.dtype == torch.int64  # wire dtype
    assert len(mask) == out.response_length == 3
    # 附加属性不进 miles 对象外挂（__dict__ 无 rh2_sampling_mask）
    assert sma.ATTACHED_MASK_ATTR not in vars(out)


def test_replay_enabled_without_mask_fail_closed(world):
    sample = world.mk_vendor_sample()
    with pytest.raises(world.CanonicalizationError) as exc:
        world.canonicalize_sample(
            sample, miles_input_sample=world.mk_miles_input(), rollout_top_p=0.8
        )
    assert exc.value.reason_code == "sampling_mask_required"


@pytest.mark.parametrize("rollout_top_p", [None, 1.0])
def test_gate_off_without_mask_passes(world, rollout_top_p):
    sample = world.mk_vendor_sample()
    out = world.canonicalize_sample(
        sample, miles_input_sample=world.mk_miles_input(), rollout_top_p=rollout_top_p
    )
    assert out.rollout_sampling_mask is None


def test_attached_mask_wrong_type_rejected(world):
    sample = world.mk_vendor_sample()
    sample.rh2_sampling_mask = ([12, 13, 14], [0, 1, 2, 3])  # 裸 CSR 二元组不接受
    with pytest.raises(world.CanonicalizationError) as exc:
        world.canonicalize_sample(
            sample, miles_input_sample=world.mk_miles_input(), rollout_top_p=0.8
        )
    assert exc.value.reason_code == "sampling_mask_wrong_type"


def test_attached_mask_length_mismatch_rejected(world, sma):
    sample = world.mk_vendor_sample()  # response_length=3
    short = sma.assemble_leaf_sampling_mask(
        [12], [1], [sma.TurnSupport(output_ids=(12,), supports=((12,),))]
    )
    # 绕过 attach_assembled_mask 的入口闸,直接挂错长度——canonicalize 自己的
    # 边界校验必须兜住（防御深度:两道闸独立生效）
    setattr(sample, sma.ATTACHED_MASK_ATTR, short)
    with pytest.raises(world.CanonicalizationError) as exc:
        world.canonicalize_sample(
            sample, miles_input_sample=world.mk_miles_input(), rollout_top_p=0.8
        )
    assert exc.value.reason_code == "sampling_mask_length_mismatch"


def test_pin_base_without_field_rejected(world, sma, monkeypatch):
    """模拟 pin base（Sample 无 rollout_sampling_mask 字段）：mask 在场必须拒绝,
    不存在静默丢弃/塞 metadata 路径。真实 pin 上本文件整体 skip,故用
    monkeypatch 翻 MILES_HAS_SAMPLING_MASK_FIELD 断言拒绝分支本身。"""

    from repoharness2.adapters.miles import canonicalize as canon

    monkeypatch.setattr(canon, "MILES_HAS_SAMPLING_MASK_FIELD", False)
    sample = world.mk_vendor_sample()
    sma.attach_assembled_mask(sample, _assembled_for_vendor_sample(sma))
    with pytest.raises(world.CanonicalizationError) as exc:
        world.canonicalize_sample(
            sample, miles_input_sample=world.mk_miles_input(), rollout_top_p=0.8
        )
    assert exc.value.reason_code == "sampling_mask_field_absent"


def test_miles_passthrough_preserves_first_class_mask(world):
    """abort 收口路径（直通分支的真实形态）：已带 rollout_sampling_mask 的
    miles 样本原样直通,一等字段不被触碰。"""

    from miles.utils.sampling_mask import RolloutSamplingMask

    inp = world.mk_miles_input()
    result = world.mk_miles_input(rollout_id=7)
    result.session_id = "sid-1"  # rh2 附加属性,直通分支应剥除
    result.tokens = [0, 0]
    result.response_length = 2
    result.loss_mask = [0, 0]
    result.rollout_log_probs = [0.0, 0.0]
    result.reward = 0.0
    result.status = world.MS.Status.ABORTED  # PENDING 被直通分支拒绝（既有语义）
    result.rollout_sampling_mask = RolloutSamplingMask(ids=[3, 4], offsets=[0, 1, 2])
    out = world.canonicalize_sample(result, miles_input_sample=inp)
    assert out is result
    assert out.rollout_sampling_mask is not None and len(out.rollout_sampling_mask) == 2
    assert not hasattr(out, "session_id")


def test_group_recursion_passes_rollout_top_p(world, sma):
    with_mask = world.mk_vendor_sample()
    sma.attach_assembled_mask(with_mask, _assembled_for_vendor_sample(sma))
    without_mask = world.mk_vendor_sample(index=1)
    with pytest.raises(world.CanonicalizationError) as exc:
        world.canonicalize_group(
            [with_mask, without_mask],
            miles_input_sample=world.mk_miles_input(),
            rollout_top_p=0.8,
        )
    assert exc.value.reason_code == "sampling_mask_required"  # 逐样本透传,第二个被拦


# ---------------------------------------------------------------------------
# generate_fn 闸透传（args.rollout_top_p -> canonicalize）
# ---------------------------------------------------------------------------


class _FakeOrchestrator:
    def __init__(self, result_fn):
        self._result_fn = result_fn

    async def generate(self, args, sample, sampling_params, evaluation=False):
        return self._result_fn(sample)


def _mk_input(orchestrator, sample, *, rollout_top_p):
    from miles.rollout.base_types import GenerateFnInput

    args = Namespace(rh2_orchestrator=orchestrator, rollout_top_p=rollout_top_p)
    return GenerateFnInput(
        state=SimpleNamespace(args=args), sample=sample, sampling_params={}, evaluation=False
    )


async def test_generate_fn_gate_rejects_maskless_when_replay_on(world):
    world.install_sglang_stub()
    inp = world.mk_miles_input()
    orch = _FakeOrchestrator(lambda sample: [world.mk_vendor_sample()])
    fn = world.Rh2MilesGenerateFn()
    with pytest.raises(world.CanonicalizationError) as exc:
        await fn(_mk_input(orch, inp, rollout_top_p=0.8))
    assert exc.value.reason_code == "sampling_mask_required"


async def test_generate_fn_passes_mask_through_when_replay_on(world, sma):
    world.install_sglang_stub()

    def result(sample):
        s = world.mk_vendor_sample()
        sma.attach_assembled_mask(s, _assembled_for_vendor_sample(sma))
        return [s]

    inp = world.mk_miles_input()
    fn = world.Rh2MilesGenerateFn()
    out = await fn(_mk_input(_FakeOrchestrator(result), inp, rollout_top_p=0.8))
    (sample,) = out.samples
    assert sample.rollout_sampling_mask is not None
    assert len(sample.rollout_sampling_mask) == sample.response_length
