"""预算终止闭环——批 D-1（I04 处置注入）与批 C（I02 turn 预算）的准入面回归。

批 D-1（2026-09-09）：已批处置（第一组：turn 截断 KEEP_FULL、hard wall DROP_GROUP）由
`bringup.inject_disposition_policy(args)` 在 `ensure_fa_started` 注入 `args.rh2_disposition_policy`；
`owner_cancelled_truncation` / `agent_violation` 未定保持 None（遇到仍 fail-fast）；冲突覆盖 →
StartupCheckError。库层 `DispositionPolicy` / `apply_member_disposition` 保持中立（不带值）。

真实接缝：经 `world` 的真实 miles `DefaultDataBuffer.put` + 复合 group filter，hard wall 成员
（fa_formal 编排本体产出的 present_truncated + hard_wall_timeout）在注入后整组 DROP，不再
DispositionNotInjectedError；policy_horizon 的 KEEP 路径由批 C 产出真实 `max_turns_exhausted` 后验证。
"""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_w1b_group_admission import BOTH_OK, _build_chain, _buffer, _dispatch_group, _entry, _miles_args  # noqa: E402


def test_inject_disposition_policy_sets_expected_and_rejects_conflict():
    from repoharness2.adapters.miles.group_admission import DISPOSITION_POLICY_ARGS_KEY
    from repoharness2.adapters.slime.bringup import (
        DISPOSITION_POLICY_VALUES,
        inject_disposition_policy,
        make_disposition_policy,
    )
    from repoharness2.adapters.slime.generate import StartupCheckError
    from repoharness2.governance.admission import DispositionPolicy

    assert DISPOSITION_POLICY_VALUES == {
        "policy_horizon_truncation": "KEEP_FULL",
        "hard_wall_truncation": "DROP_GROUP",
        "owner_cancelled_truncation": None,
        "agent_violation": None,
    }
    args = Namespace()
    policy = inject_disposition_policy(args)
    assert getattr(args, DISPOSITION_POLICY_ARGS_KEY) is policy
    assert policy.policy_horizon_truncation == "KEEP_FULL" and policy.hard_wall_truncation == "DROP_GROUP"
    assert policy.owner_cancelled_truncation is None and policy.agent_violation is None
    assert inject_disposition_policy(args) is policy  # 幂等：已注入且一致 → 保持

    consistent = Namespace(**{DISPOSITION_POLICY_ARGS_KEY: make_disposition_policy()})
    assert inject_disposition_policy(consistent) is getattr(consistent, DISPOSITION_POLICY_ARGS_KEY)

    conflicting = Namespace(**{DISPOSITION_POLICY_ARGS_KEY: DispositionPolicy(hard_wall_truncation="KEEP_FULL")})
    with pytest.raises(StartupCheckError, match="disposition_policy_conflict"):
        inject_disposition_policy(conflicting)
    wrong_type = Namespace(**{DISPOSITION_POLICY_ARGS_KEY: {"hard_wall_truncation": "DROP_GROUP"}})
    with pytest.raises(StartupCheckError, match="disposition_policy_conflict"):
        inject_disposition_policy(wrong_type)


def test_library_policy_stays_neutral():
    """库层不带值：不注入时四槽位全 None（fail-fast 语义由既有测试覆盖）。"""

    from repoharness2.governance.admission import DispositionPolicy

    p = DispositionPolicy()
    assert (p.policy_horizon_truncation, p.hard_wall_truncation, p.owner_cancelled_truncation, p.agent_violation) == (
        None, None, None, None,
    )


async def test_injected_policy_drops_hard_wall_member_through_real_buffer(world, tmp_path):
    """真实 fa_formal 编排本体产出 hard wall 成员（exit=-1 → present_truncated / hard_wall_timeout）→
    注入后经真实 DefaultDataBuffer.put + group filter 整组 DROP（度量 `drop_admission_truncation_hard_wall_excluded`），
    不再 DispositionNotInjectedError；同一 world 下未注入仍 fail-fast（对照）。"""

    world.install_sglang_stub()
    from repoharness2.adapters.slime.bringup import inject_disposition_policy
    from repoharness2.governance.admission import DispositionNotInjectedError

    chain = _build_chain(world, tmp_path / "a", grading_kinds=BOTH_OK, exit_codes=(0, -1))
    prompt_group, group = await _dispatch_group(world, chain)
    (leaf,) = group[1]
    assert leaf.metadata["rh2_admission"]["outcome"]["termination_kind"] == "hard_wall_timeout"
    assert leaf.metadata["rh2_admission"]["outcome"]["completion_class"] == "present_truncated"

    args = _miles_args(world, chain)
    buf, recycled = _buffer(world, args)
    with pytest.raises(DispositionNotInjectedError, match="hard_wall_truncation"):
        await buf.put(_entry(world, prompt_group, group))  # 对照：未注入 → fail-fast

    chain2 = _build_chain(world, tmp_path / "b", grading_kinds=BOTH_OK, exit_codes=(0, -1))
    prompt_group2, group2 = await _dispatch_group(world, chain2)
    args2 = _miles_args(world, chain2)
    inject_disposition_policy(args2)  # 批 D-1：启动注入的同一函数
    buf2, recycled2 = _buffer(world, args2)
    await buf2.put(_entry(world, prompt_group2, group2))
    assert buf2._buffer == [] and recycled2 == []
    assert buf2.get_metrics()["rollout/dynamic_filter/drop_admission_truncation_hard_wall_excluded"] == 1
