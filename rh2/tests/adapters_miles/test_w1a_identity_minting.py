"""W1a（计划 06 §3 / D0-2）：miles 派发路径六字段身份铸造的契约测试。

覆盖验收要求的负例/正例矩阵：身份缺失、重复/复用（跨组错配 + attempt
历史损坏）、retry 换 attempt（真实 miles reset_for_retry）、fan-out 冒充、
canonicalize round-trip 身份无损、s1_compat 零改变。

真实 fa_formal 生产链（挡板以下的 generate/canonicalize 全链）在
test_w1a_formal_chain.py。
"""

from __future__ import annotations

from argparse import Namespace
from types import SimpleNamespace

import pytest


def _idm():
    from repoharness2.adapters.miles import identity as idm

    return idm


# ---------------------------------------------------------------------------
# mint_attempt_identity：推导正例
# ---------------------------------------------------------------------------


def test_mint_two_level_identity_from_group_facts(world):
    idm = _idm()
    # stock data_source 算术：group_index=3, n=4, 组内第 2 个成员 index=3*4+1=13
    s = world.mk_miles_input(index=13, group_index=3)
    minted = idm.mint_attempt_identity(s, n_samples_per_prompt=4)

    assert minted[idm.GROUP_ID_KEY] == "miles_g3"
    assert minted[idm.GROUP_INDEX_KEY] == 3
    assert minted[idm.EXECUTION_ID_KEY] == "miles_g3_m1"
    assert minted[idm.MEMBER_SLOT_KEY] == 1
    assert minted[idm.ATTEMPT_SEQ_KEY] == 1
    assert minted[idm.ATTEMPT_ID_KEY].startswith("miles_g3_m1#p1-")
    # 铸造结果落在样本 metadata（generate.py 入口读的就是它）
    for key in idm.IDENTITY_KEYS:
        assert s.metadata[key] == minted[key]


def test_mint_same_group_members_share_group_identity(world):
    """组身份确定性推导：同组两个成员各自铸造得到相同组身份、不同成员身份。"""

    idm = _idm()
    m0 = world.mk_miles_input(index=8, group_index=4)
    m1 = world.mk_miles_input(index=9, group_index=4)
    a = idm.mint_attempt_identity(m0, n_samples_per_prompt=2)
    b = idm.mint_attempt_identity(m1, n_samples_per_prompt=2)
    assert a[idm.GROUP_ID_KEY] == b[idm.GROUP_ID_KEY] == "miles_g4"
    assert (a[idm.MEMBER_SLOT_KEY], b[idm.MEMBER_SLOT_KEY]) == (0, 1)
    assert a[idm.EXECUTION_ID_KEY] != b[idm.EXECUTION_ID_KEY]
    assert a[idm.ATTEMPT_ID_KEY] != b[idm.ATTEMPT_ID_KEY]


# ---------------------------------------------------------------------------
# 负例：身份事实缺失 / 组形状不可推导
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field,bad", [("group_index", None), ("index", None),
                                       ("group_index", -1), ("index", True)])
def test_mint_missing_or_malformed_facts_fail_closed(world, field, bad):
    idm = _idm()
    s = world.mk_miles_input(index=0, group_index=0)
    setattr(s, field, bad)
    with pytest.raises(idm.MilesIdentityError, match="identity_facts_missing"):
        idm.mint_attempt_identity(s, n_samples_per_prompt=1)


@pytest.mark.parametrize("n", [None, 0, -2, True, "4"])
def test_mint_group_size_missing_fail_closed(world, n):
    idm = _idm()
    s = world.mk_miles_input(index=0, group_index=0)
    with pytest.raises(idm.MilesIdentityError, match="group_size_config_missing"):
        idm.mint_attempt_identity(s, n_samples_per_prompt=n)


def test_mint_metadata_not_dict_fail_closed(world):
    idm = _idm()
    s = world.mk_miles_input(index=0, group_index=0)
    s.metadata = None
    with pytest.raises(idm.MilesIdentityError, match="member_metadata_not_writable"):
        idm.mint_attempt_identity(s, n_samples_per_prompt=1)


def test_mint_slot_out_of_range_fail_closed(world):
    """index 与 group_index*n 算术不合（自定义数据源/身份污染）——宁炸不猜。"""

    idm = _idm()
    # group_index=0, n=2 时合法 index 只有 0/1；index=5 推导 slot=5 越界
    s = world.mk_miles_input(index=5, group_index=0)
    with pytest.raises(idm.MilesIdentityError, match="member_slot_underivable"):
        idm.mint_attempt_identity(s, n_samples_per_prompt=2)


# ---------------------------------------------------------------------------
# retry：真实 reset_for_retry 后 attempt 必换新、组/成员身份稳定
# ---------------------------------------------------------------------------


def test_retry_mints_new_attempt_keeps_member_identity(world):
    idm = _idm()
    s = world.mk_miles_input(index=2, group_index=1)
    first = idm.mint_attempt_identity(s, n_samples_per_prompt=2)

    # 真实 miles 回收路径：reset_for_retry 保留 identity/metadata（含旧
    # attempt 字段）——这正是必须在派发时刻重铸的原因。
    s.reset_for_retry()
    assert s.metadata[idm.ATTEMPT_ID_KEY] == first[idm.ATTEMPT_ID_KEY]

    second = idm.mint_attempt_identity(s, n_samples_per_prompt=2)
    third_sample_state = dict(s.metadata)

    for key in (idm.GROUP_ID_KEY, idm.GROUP_INDEX_KEY,
                idm.EXECUTION_ID_KEY, idm.MEMBER_SLOT_KEY):
        assert second[key] == first[key]
    assert second[idm.ATTEMPT_SEQ_KEY] == 2
    assert second[idm.ATTEMPT_ID_KEY] != first[idm.ATTEMPT_ID_KEY]
    assert second[idm.ATTEMPT_ID_KEY].startswith("miles_g1_m0#p2-")
    assert third_sample_state[idm.ATTEMPT_SEQ_KEY] == 2

    third = idm.mint_attempt_identity(s, n_samples_per_prompt=2)
    assert third[idm.ATTEMPT_SEQ_KEY] == 3
    assert len({first[idm.ATTEMPT_ID_KEY], second[idm.ATTEMPT_ID_KEY],
                third[idm.ATTEMPT_ID_KEY]}) == 3


# ---------------------------------------------------------------------------
# 负例：复用/损坏的身份历史
# ---------------------------------------------------------------------------


def test_mint_conflicting_stable_identity_fail_closed(world):
    """跨组错配：metadata 带别的组/成员身份（从其他样本串过来）不得静默覆写。"""

    idm = _idm()
    s = world.mk_miles_input(index=0, group_index=0)
    s.metadata[idm.GROUP_ID_KEY] = "miles_g99"
    with pytest.raises(idm.MilesIdentityError, match="identity_conflict"):
        idm.mint_attempt_identity(s, n_samples_per_prompt=1)

    s2 = world.mk_miles_input(index=0, group_index=0)
    s2.metadata[idm.MEMBER_SLOT_KEY] = 7
    with pytest.raises(idm.MilesIdentityError, match="identity_conflict"):
        idm.mint_attempt_identity(s2, n_samples_per_prompt=1)


def _full_history(idm, *, attempt_id: object, seq: object) -> dict:
    """构造一套"六键齐全"的 retry 历史种子（稳定四键与推导一致，attempt
    两键由参数指定）——用于把校验推进到历史真实性层。"""

    return {
        idm.GROUP_ID_KEY: "miles_g0",
        idm.GROUP_INDEX_KEY: 0,
        idm.EXECUTION_ID_KEY: "miles_g0_m0",
        idm.MEMBER_SLOT_KEY: 0,
        idm.ATTEMPT_ID_KEY: attempt_id,
        idm.ATTEMPT_SEQ_KEY: seq,
    }


@pytest.mark.parametrize(
    "seed_keys",
    [
        {"rh2_physical_attempt_seq": 1},  # 只有 seq
        {"rh2_physical_attempt_id": "miles_g0_m0#p1-deadbeef"},  # 只有 id
        # F1 codex 复现原型：外部输入只带 attempt 两键伪造历史（稳定四键缺）
        {"rh2_physical_attempt_id": "belongs-to-another-execution",
         "rh2_physical_attempt_seq": 41},
        {"rh2_prompt_group_id": "miles_g0"},  # 只带一个稳定键（值哪怕正确）
    ],
)
def test_mint_reserved_keys_polluted_fail_closed(world, seed_keys):
    """F1：六个身份键是 system-reserved——部分在场即输入污染，结构性拒绝
    （不是 drop）。fresh 样本预置任何保留键子集都到不了续铸。"""

    idm = _idm()
    s = world.mk_miles_input(index=0, group_index=0)
    s.metadata.update(seed_keys)
    with pytest.raises(idm.MilesIdentityError, match="reserved_identity_keys_polluted"):
        idm.mint_attempt_identity(s, n_samples_per_prompt=1)


@pytest.mark.parametrize(
    "attempt_id, seq, reason",
    [
        ("x", "1", "attempt_history_corrupt"),  # seq 非 int
        ("x", 0, "attempt_history_corrupt"),  # seq < 1
        ("x", True, "attempt_history_corrupt"),  # bool 污染
        # F1 历史真实性（六键齐全也不许伪造）：
        ("belongs-to-another-execution#p41-deadbeef", 41, "attempt_history_forged"),  # foreign execution
        ("miles_g0_m0#p40-deadbeef", 41, "attempt_history_forged"),  # #pN 与 seq 不符
        ("", 41, "attempt_history_forged"),  # 空 id
        (41, 41, "attempt_history_forged"),  # 非字符串 id
        ("miles_g0_m0#p41-ZZZZZZZZ", 41, "attempt_history_forged"),  # 后缀非 hex
        ("miles_g0_m0#p41-dead", 41, "attempt_history_forged"),  # 后缀长度不对
    ],
)
def test_mint_attempt_history_corrupt_or_forged_fail_closed(world, attempt_id, seq, reason):
    idm = _idm()
    s = world.mk_miles_input(index=0, group_index=0)
    s.metadata.update(_full_history(idm, attempt_id=attempt_id, seq=seq))
    with pytest.raises(idm.MilesIdentityError, match=reason):
        idm.mint_attempt_identity(s, n_samples_per_prompt=1)


def test_mint_forged_seq41_rejected_even_with_consistent_shape(world):
    """F1 验收：codex 复现的"fresh 样本伪称第 41 次重试"在两个层面都被拒——
    两键裸伪造 = 污染；补齐六键但 id 非本链铸造形制 = forged。合法续铸
    （真实 mint 产物）不受影响。"""

    idm = _idm()
    s = world.mk_miles_input(index=0, group_index=0)
    first = idm.mint_attempt_identity(s, n_samples_per_prompt=1)
    assert first[idm.ATTEMPT_SEQ_KEY] == 1
    # 真实历史续铸仍然成立（metadata 里是上一次 mint 的产物）
    second = idm.mint_attempt_identity(s, n_samples_per_prompt=1)
    assert second[idm.ATTEMPT_SEQ_KEY] == 2
    assert second[idm.ATTEMPT_ID_KEY].startswith("miles_g0_m0#p2-")


# ---------------------------------------------------------------------------
# stamp_identity_on_outputs：fan-out 统一盖章 + 冒充拒绝
# ---------------------------------------------------------------------------


def test_stamp_fanout_leaves_share_one_attempt(world):
    idm = _idm()
    src = world.mk_miles_input(index=0, group_index=0)
    minted = idm.mint_attempt_identity(src, n_samples_per_prompt=1)

    inputs = [world.mk_miles_input(index=0, group_index=0) for _ in range(3)]
    vendor = [world.mk_vendor_sample(index=0, group_index=0, rollout_id=42) for _ in range(2)]
    # 嵌套形状：[leaf, [leaf, leaf]]——canonicalize_group 的合法输出面
    out = [
        world.canonicalize_group([vendor[0]], miles_input_sample=inputs[0])[0],
        world.canonicalize_group([vendor[1], vendor[1]], miles_input_sample=inputs[1]),
    ]
    idm.stamp_identity_on_outputs(out, minted)

    flat = [out[0], out[1][0], out[1][1]]
    for leaf in flat:
        for key in idm.IDENTITY_KEYS:
            assert leaf.metadata[key] == minted[key]
    # fan-out 叶共享同一 physical attempt：绝无逐叶新 attempt
    assert len({leaf.metadata[idm.ATTEMPT_ID_KEY] for leaf in flat}) == 1


def test_stamp_rejects_forged_attempt_on_leaf(world):
    """fan-out 冒充负例：叶自带不同 attempt id / member slot 即拒绝交付。"""

    idm = _idm()
    src = world.mk_miles_input(index=0, group_index=0)
    minted = idm.mint_attempt_identity(src, n_samples_per_prompt=1)

    forged = world.canonicalize_group(
        [world.mk_vendor_sample(index=0, group_index=0)],
        miles_input_sample=world.mk_miles_input(index=0, group_index=0),
    )[0]
    forged.metadata[idm.ATTEMPT_ID_KEY] = "miles_g0_m0#p9-forged00"
    with pytest.raises(idm.MilesIdentityError, match="output_identity_forgery"):
        idm.stamp_identity_on_outputs([forged], minted)

    forged2 = world.canonicalize_group(
        [world.mk_vendor_sample(index=0, group_index=0)],
        miles_input_sample=world.mk_miles_input(index=0, group_index=0),
    )[0]
    forged2.metadata[idm.MEMBER_SLOT_KEY] = 5  # 冒充新 member
    with pytest.raises(idm.MilesIdentityError, match="output_identity_forgery"):
        idm.stamp_identity_on_outputs([forged2], minted)


def test_stamp_requires_complete_identity(world):
    idm = _idm()
    leaf = world.canonicalize_group(
        [world.mk_vendor_sample(index=0, group_index=0)],
        miles_input_sample=world.mk_miles_input(index=0, group_index=0),
    )[0]
    with pytest.raises(idm.MilesIdentityError, match="identity_stamp_incomplete"):
        idm.stamp_identity_on_outputs([leaf], {"rh2_prompt_group_id": "miles_g0"})


# ---------------------------------------------------------------------------
# Rh2MilesGenerateFn 集成：铸造门控 + round-trip 身份无损
# ---------------------------------------------------------------------------


class _FakeOrchestrator:
    """rh2 RolloutOrchestrator.generate 的最小同形替身（与 test_generate_fn 同款）。"""

    def __init__(self, result_fn, execution_mode=None):
        self._result_fn = result_fn
        self.calls: list[tuple] = []
        if execution_mode is not None:
            self.config = SimpleNamespace(execution_mode=execution_mode)

    async def generate(self, args, sample, sampling_params, evaluation=False):
        self.calls.append((args, sample, sampling_params, evaluation))
        return self._result_fn(sample)


def _mk_input(orchestrator, sample, **args_over):
    from miles.rollout.base_types import GenerateFnInput

    args = Namespace(rh2_orchestrator=orchestrator, **args_over)
    return GenerateFnInput(
        state=SimpleNamespace(args=args),
        sample=sample,
        sampling_params={"top_p": 1.0},
        evaluation=False,
    )


async def test_generate_fn_mints_and_round_trips_identity(world):
    """非 s1 模式：__call__ 铸造 → 真实 canonicalize → 输出叶身份无损；
    fan-out 两叶共享同一 attempt（分支不是新 member/新 attempt）。"""

    world.install_sglang_stub()
    idm = _idm()

    inp = world.mk_miles_input(index=1, group_index=0)
    orch = _FakeOrchestrator(
        lambda sample: [
            world.mk_vendor_sample(index=1, group_index=0, rollout_id=42),
            world.mk_vendor_sample(index=1, group_index=0, rollout_id=42),
        ],
        execution_mode="fa_formal",
    )
    fn = world.Rh2MilesGenerateFn()
    out = await fn(_mk_input(orch, inp, n_samples_per_prompt=2))

    # 铸造发生在 rh2_custom_generate 之前：编排层看到的输入样本已带六字段
    (_, seen_sample, _, _), = orch.calls
    for key in idm.IDENTITY_KEYS:
        assert key in seen_sample.metadata
    minted = {k: inp.metadata[k] for k in idm.IDENTITY_KEYS}
    assert minted[idm.GROUP_ID_KEY] == "miles_g0"
    assert minted[idm.EXECUTION_ID_KEY] == "miles_g0_m1"
    assert minted[idm.ATTEMPT_SEQ_KEY] == 1

    # round-trip 无损：输出两叶携带与输入完全一致的六字段（同一 attempt）
    samples = out.samples
    assert isinstance(samples, list) and len(samples) == 2
    for leaf in samples:
        for key in idm.IDENTITY_KEYS:
            assert leaf.metadata[key] == minted[key]
    assert samples[0].metadata[idm.ATTEMPT_ID_KEY] == samples[1].metadata[idm.ATTEMPT_ID_KEY]


async def test_generate_fn_retry_changes_attempt_not_member(world):
    """retry 语义走真实 reset_for_retry：第二次 __call__ = 新 attempt/seq，
    组/成员身份不变；新输出叶带新 attempt id。"""

    world.install_sglang_stub()
    idm = _idm()

    inp = world.mk_miles_input(index=0, group_index=0)
    orch = _FakeOrchestrator(
        lambda sample: [world.mk_vendor_sample(index=0, group_index=0)],
        execution_mode="fa_audit_only",
    )
    fn = world.Rh2MilesGenerateFn()

    out1 = await fn(_mk_input(orch, inp, n_samples_per_prompt=1))
    paid1 = inp.metadata[idm.ATTEMPT_ID_KEY]

    inp.reset_for_retry()  # miles 真实回收路径：保留 metadata（旧身份仍在）
    out2 = await fn(_mk_input(orch, inp, n_samples_per_prompt=1))
    paid2 = inp.metadata[idm.ATTEMPT_ID_KEY]

    assert paid1 != paid2
    assert inp.metadata[idm.ATTEMPT_SEQ_KEY] == 2
    assert inp.metadata[idm.EXECUTION_ID_KEY] == "miles_g0_m0"
    assert out1.samples[0].metadata[idm.ATTEMPT_ID_KEY] == paid1
    assert out2.samples[0].metadata[idm.ATTEMPT_ID_KEY] == paid2


async def test_generate_fn_missing_group_size_fail_closed_in_formal(world):
    """身份缺失负例（generate_fn 门内）：非 s1 模式缺 n_samples_per_prompt
    即拒绝派发——不带残缺身份进生产链。"""

    world.install_sglang_stub()
    idm = _idm()

    orch = _FakeOrchestrator(
        lambda sample: [world.mk_vendor_sample()], execution_mode="fa_formal"
    )
    fn = world.Rh2MilesGenerateFn()
    with pytest.raises(idm.MilesIdentityError, match="group_size_config_missing"):
        await fn(_mk_input(orch, world.mk_miles_input()))
    assert orch.calls == []  # 铸造失败先于任何生成


async def test_generate_fn_s1_compat_mints_nothing(world):
    """s1_compat（含无 config 的老测试面）：零身份写入，行为逐字不变。"""

    world.install_sglang_stub()
    idm = _idm()

    inp = world.mk_miles_input(index=1, group_index=0)
    orch = _FakeOrchestrator(lambda sample: [world.mk_vendor_sample(index=1)])
    fn = world.Rh2MilesGenerateFn()
    out = await fn(_mk_input(orch, inp))

    for key in idm.IDENTITY_KEYS:
        assert key not in inp.metadata
        assert key not in out.samples[0].metadata
