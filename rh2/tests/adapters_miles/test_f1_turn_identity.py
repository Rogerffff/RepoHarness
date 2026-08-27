"""F1 身份制修复的机制测试（finding §3；设计三步 = commit 时刻绑定 /
叶侧树走查导出身份 span / 匹配降级为校验断言）。

覆盖面（e2e 纵链另见 test_f1_e2e_identity_chain.py）：

1. `export_leaf_identity_spans`：真实 TrajectoryManager 造树——CLEAN 多轮、
   rewrite-merge 掉落、REALIGN 掉落、消息级 FORK 多叶、共享前缀轮只被首叶
   train——重放产物与真实 `get_trajectory` 逐 token 对账；
2. `_runs_from_identity_spans`：身份直取 + token 相等降级为校验断言的全部
   fail-closed 分支；
3. F1 反例 [11,21,21] 对照：旧 matcher 按内容反推选中掉落轮（错误行为
   原样保留在旧链），身份路径精确选中活轮；
4. `rh2_record_turn` 包装的 commit 时刻绑定（真实 record_turn，含
   空 prompt_messages 跳过附着的孤儿 capture 不绑定）；
5. bringup `PerRolloutAdapter.finish_session` 的生产附着 +
   `bringup_leaf_facts` 的读出与 fail-closed。

本目录纪律：不得模块级 import slime/miles——一律函数内 import
（conftest 的 module 级 vendor 世界装卸）。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# 工具：真实 TrajectoryManager 造树
# ---------------------------------------------------------------------------

PROMPT = [100, 101, 102, 103]

_USER = {"role": "user", "content": "fix it"}
_TOOL = {"role": "tool", "content": "tool out"}


def _mk_turn(prompt_ids, output_ids, logprobs=None):
    from slime.agent.trajectory import TurnRecord

    return TurnRecord(
        prompt_ids=list(prompt_ids),
        output_ids=list(output_ids),
        finish_reason="stop",
        output_log_probs=list(logprobs or [-0.5] * len(output_ids)),
    )


def _mk_base_sample(world):
    return world.SS(index=0, group_index=0, prompt="p")


def _mk_tape(record_id, output_ids, weight_version, logprobs=None):
    from repoharness2.adapters.slime.generate import TurnTape

    return TurnTape(
        record_id=record_id,
        turn_index=0,
        prompt_token_count=4,
        response_token_count=len(output_ids),
        output_ids=tuple(output_ids),
        output_log_probs=tuple(logprobs or [-0.5] * len(output_ids)),
        top_p_token_ids=None,
        top_p_token_offsets=None,
        routed_experts_flat=None,
        weight_version=weight_version,
    )


# ---------------------------------------------------------------------------
# 1. export_leaf_identity_spans：树走查重放
# ---------------------------------------------------------------------------


def _export_and_crosscheck(world, manager, sid, max_sample_tokens=0):
    """导出身份 span 并与真实 get_trajectory 产物逐 token 对账。

    注意顺序：先拿树根引用，再 get_trajectory（弹树），再在持有的根上
    重放——与生产 finish_session 包装同一顺序（树对象弹出后仍被引用持有）。
    """

    from repoharness2.adapters.slime.turn_identity import export_leaf_identity_spans

    root = manager._trees[sid]
    fork_threshold = manager._fork_threshold
    samples = manager.get_trajectory(
        sid,
        base_sample=_mk_base_sample(world),
        max_sample_tokens=max_sample_tokens,
    )
    exports = export_leaf_identity_spans(
        root, fork_threshold=fork_threshold, max_sample_tokens=max_sample_tokens
    )
    assert len(exports) == len(samples)
    for sample, export in zip(samples, exports):
        assert list(sample.tokens) == export.tokens
        assert list(sample.loss_mask) == export.loss_mask
    return samples, exports


def test_export_spans_clean_two_turns_with_tool_gap(world):
    """CLEAN 两轮 + 工具间隔：span 落在各自 mask=1 段，turn_index 正确。"""

    from slime.agent.trajectory import TrajectoryManager

    manager = TrajectoryManager()
    gen1, tool, gen2 = [11, 12], [301], [13]
    asst1 = {"role": "assistant", "content": "g1"}
    manager.record_turn(
        "s", turn=_mk_turn(PROMPT, gen1), prompt_messages=[_USER], response_message=asst1
    )
    manager.record_turn(
        "s",
        turn=_mk_turn(PROMPT + gen1 + tool, gen2),
        prompt_messages=[_USER, asst1, _TOOL],
        response_message={"role": "assistant", "content": "g2"},
    )
    samples, exports = _export_and_crosscheck(world, manager, "s")
    assert len(samples) == 1
    (export,) = exports
    # response = gen1 + tool + gen2，span 座标以 response 起点为 0
    assert export.loss_mask == [1, 1, 0, 1]
    assert export.spans == ((0, 2, 1), (3, 1, 2))


def test_export_spans_rewrite_merge_drops_turn(world):
    """rewrite-merge 掉落轮（B2 同机制）：掉落轮不产 span，活轮 span 在位。"""

    from slime.agent.trajectory import TrajectoryManager

    manager = TrajectoryManager()
    gen1, tool, live = [11], [21], [21]  # 活轮 token 与掉落轮相同（F1 形状）
    asst1 = {"role": "assistant", "content": "g1"}
    dropped_msg = {"role": "assistant", "content": "draft"}
    rewritten_msg = {"role": "assistant", "content": "draft [rewritten]"}
    manager.record_turn(
        "s", turn=_mk_turn(PROMPT, gen1), prompt_messages=[_USER], response_message=asst1
    )
    manager.record_turn(
        "s",
        turn=_mk_turn(PROMPT + gen1 + tool, [21]),
        prompt_messages=[_USER, asst1, _TOOL],
        response_message=dropped_msg,
    )
    manager.record_turn(
        "s",
        turn=_mk_turn(PROMPT + gen1 + tool, live),
        prompt_messages=[_USER, asst1, _TOOL, rewritten_msg],
        response_message={"role": "assistant", "content": "live"},
    )
    samples, exports = _export_and_crosscheck(world, manager, "s")
    assert len(samples) == 1
    (export,) = exports
    assert export.tokens == PROMPT + [11, 21, 21]
    assert export.loss_mask == [1, 0, 1]
    # 掉落轮（turn_index=2）不在身份账里；活轮 = turn_index 3
    assert export.spans == ((0, 1, 1), (2, 1, 3))


def test_export_spans_realign_drops_previous_span(world):
    """REALIGN：上一响应 span 被整段覆盖（mask=0）——其身份 span 移除。"""

    from slime.agent.trajectory import TrajectoryManager

    manager = TrajectoryManager()
    gen1 = [11, 12, 13]
    gen1_drift = [11, 12, 99]  # 尾 token 漂移（TITO 再分词形态）
    gen2 = [14]
    asst1 = {"role": "assistant", "content": "g1"}
    manager.record_turn(
        "s", turn=_mk_turn(PROMPT, gen1), prompt_messages=[_USER], response_message=asst1
    )
    manager.record_turn(
        "s",
        turn=_mk_turn(PROMPT + gen1_drift, gen2),
        prompt_messages=[_USER, asst1],
        response_message={"role": "assistant", "content": "g2"},
    )
    samples, exports = _export_and_crosscheck(world, manager, "s")
    assert len(samples) == 1
    (export,) = exports
    assert export.tokens == PROMPT + gen1_drift + gen2
    assert export.loss_mask == [0, 0, 0, 1]  # gen1 全段降为上下文
    assert export.spans == ((3, 1, 2),)  # 只剩活轮；turn1 的 span 已随覆盖移除


def test_export_spans_message_fork_two_leaves(world):
    """消息级 FORK：两条叶链各自导出，只含自身前缀链的轮。"""

    from slime.agent.trajectory import TrajectoryManager

    manager = TrajectoryManager()
    user2 = {"role": "user", "content": "another task"}
    gen1, gen2 = [11], [12, 13]
    manager.record_turn(
        "s",
        turn=_mk_turn(PROMPT, gen1),
        prompt_messages=[_USER],
        response_message={"role": "assistant", "content": "g1"},
    )
    manager.record_turn(
        "s",
        turn=_mk_turn([200, 201], gen2),
        prompt_messages=[user2],
        response_message={"role": "assistant", "content": "g2"},
    )
    samples, exports = _export_and_crosscheck(world, manager, "s")
    assert len(samples) == 2
    assert exports[0].spans == ((0, 1, 1),)
    assert exports[1].spans == ((0, 2, 2),)


def test_export_spans_sibling_leaves_train_shared_prefix_once(world):
    """共享前缀轮只被第一条叶链 train：第二叶链把它 re-emit 为 mask=0，
    因此第二叶链的身份账**不含**共享轮——与 vendor response_trained
    首领语义逐位对齐。"""

    from slime.agent.trajectory import TrajectoryManager

    manager = TrajectoryManager()
    gen1, tool, gen2, gen3 = [11], [301], [12], [13]
    asst1 = {"role": "assistant", "content": "g1"}
    manager.record_turn(
        "s", turn=_mk_turn(PROMPT, gen1), prompt_messages=[_USER], response_message=asst1
    )
    manager.record_turn(
        "s",
        turn=_mk_turn(PROMPT + gen1 + tool, gen2),
        prompt_messages=[_USER, asst1, _TOOL],
        response_message={"role": "assistant", "content": "g2"},
    )
    manager.record_turn(
        "s",
        turn=_mk_turn(PROMPT + gen1 + tool, gen3),
        prompt_messages=[_USER, asst1, _TOOL],
        response_message={"role": "assistant", "content": "g3"},
    )
    samples, exports = _export_and_crosscheck(world, manager, "s")
    assert len(samples) == 2
    # 叶 1：asst1 + gen2 都 train
    assert exports[0].loss_mask == [1, 0, 1]
    assert exports[0].spans == ((0, 1, 1), (2, 1, 2))
    # 叶 2：asst1 已被叶 1 认领——re-emit 为 mask=0，无身份 span
    assert exports[1].loss_mask == [0, 0, 1]
    assert exports[1].spans == ((2, 1, 3),)


# ---------------------------------------------------------------------------
# 2. _runs_from_identity_spans：校验断言的 fail-closed 分支
# ---------------------------------------------------------------------------


def _span(start, length, record_id):
    from repoharness2.adapters.slime.generate import TurnIdentitySpan

    return TurnIdentitySpan(start=start, length=length, capture_record_id=record_id)


def test_identity_runs_happy_path_and_used_order(world):
    from repoharness2.adapters.slime.generate import _runs_from_identity_spans

    first = _mk_tape("cap_t0", [11], "1")
    live = _mk_tape("cap_t2", [21], "3")
    per_run, used = _runs_from_identity_spans(
        [11, 21, 21],
        [(0, 1), (2, 3)],
        [first, live],
        [_span(0, 1, "cap_t0"), _span(2, 1, "cap_t2")],
    )
    assert per_run == [[first], [live]]
    assert used == [first, live]


@pytest.mark.parametrize(
    ("tokens", "runs", "spans_spec", "reason"),
    [
        # token 漂移：span 指认的 response 段与捕获轮 output_ids 不等
        ([11, 21, 99], [(0, 1), (2, 3)], [(0, 1, "cap_t0"), (2, 1, "cap_t2")],
         "identity_span_token_drift"),
        # span 宽度 != 捕获轮宽度（截断切进轮内）
        ([11, 21, 21], [(0, 1), (2, 3)], [(0, 1, "cap_t0"), (2, 2, "cap_t2")],
         "identity_span_width_mismatch"),
        # mask=1 段起点无 span 覆盖
        ([11, 21, 21], [(0, 1), (2, 3)], [(0, 1, "cap_t0")],
         "identity_spans_do_not_tile_runs"),
        # span 落在 mask=0 区（不与任何段起点对齐）
        ([11, 21, 21], [(0, 1)], [(0, 1, "cap_t0"), (1, 1, "cap_t2")],
         "identity_spans_outside_runs"),
        # span 乱序/重叠
        ([11, 21, 21], [(0, 3)], [(1, 1, "cap_t2"), (0, 1, "cap_t0")],
         "identity_spans_not_ordered"),
    ],
)
def test_identity_runs_fail_closed_branches(world, tokens, runs, spans_spec, reason):
    from repoharness2.adapters.slime.generate import (
        SlimeBindingError,
        _runs_from_identity_spans,
    )

    tape_by_id = {
        "cap_t0": _mk_tape("cap_t0", [11], "1"),
        "cap_t2": _mk_tape("cap_t2", [21], "3"),  # 宽度不匹配场景里 span 会声称 2 token
    }
    spans = [_span(*s) for s in spans_spec]
    turns = [tape_by_id[s.capture_record_id] for s in spans]
    with pytest.raises(SlimeBindingError) as exc:
        _runs_from_identity_spans(tokens, runs, turns, spans)
    assert exc.value.reason_code == reason


def test_identity_runs_rejects_misaligned_record(world):
    """身份 span 指认活轮、供轮却给了掉落轮（token 相同）——record_id
    复核当场拒绝：身份制下 token 巧合不再可能顶替归属。"""

    from repoharness2.adapters.slime.generate import (
        SlimeBindingError,
        _runs_from_identity_spans,
    )

    first = _mk_tape("cap_t0", [11], "1")
    dropped = _mk_tape("cap_t1", [21], "2")  # 与活轮同 token
    with pytest.raises(SlimeBindingError) as exc:
        _runs_from_identity_spans(
            [11, 21, 21],
            [(0, 1), (2, 3)],
            [first, dropped],
            [_span(0, 1, "cap_t0"), _span(2, 1, "cap_t2")],
        )
    assert exc.value.reason_code == "identity_span_record_misaligned"


# ---------------------------------------------------------------------------
# 3. F1 反例 [11,21,21]：旧 matcher 错选掉落轮，身份路径精确选中活轮
# ---------------------------------------------------------------------------


def test_f1_counterexample_old_matcher_vs_identity_path(world):
    from repoharness2.adapters.slime.generate import (
        _match_turns_to_runs,
        backfill_leaf_sample,
    )

    first = _mk_tape("cap_t0", [11], "1", logprobs=[-0.10])
    dropped = _mk_tape("cap_t1", [21], "2", logprobs=[-0.20])
    live = _mk_tape("cap_t2", [21], "3", logprobs=[-0.30])
    response = [11, 21, 21]
    runs = [(0, 1), (2, 3)]

    # 旧链（无身份信息）：内容反推非单射——first-match 选中掉落轮。
    # 该错误行为在旧链**原样保留**（321 逐数不变的行为面），F1 修复 =
    # bringup 身份路径不再走这里。
    _per_run, used_legacy = _match_turns_to_runs(response, runs, [first, dropped, live])
    assert [t.record_id for t in used_legacy] == ["cap_t0", "cap_t1"]  # 错绑掉落轮
    assert [t.weight_version for t in used_legacy] == ["1", "2"]

    # 身份路径：树侧 span 直取活轮，version 事实全部来自活轮
    sample = SimpleNamespace(
        tokens=PROMPT + response,
        loss_mask=[1, 0, 1],
        metadata={},
    )
    used = backfill_leaf_sample(
        sample,
        [first, live],
        policy_version=None,
        identity_spans=[_span(0, 1, "cap_t0"), _span(2, 1, "cap_t2")],
    )
    assert [t.record_id for t in used] == ["cap_t0", "cap_t2"]
    assert sample.weight_versions == ["1", "3"]


# ---------------------------------------------------------------------------
# 4. rh2_record_turn 包装的 commit 时刻绑定
# ---------------------------------------------------------------------------


class _RecordingHook:
    """commit 消费的最小 hook 替身：返回带真实 record_id 的记录。"""

    def __init__(self):
        self.records = []

    def on_generate_response(self, *, prompt_token_ids, sampling_params, response):
        record = SimpleNamespace(record_id=f"cap_bind_t{len(self.records)}")
        self.records.append(record)
        return record


def _mk_pending(prompt_ids):
    from repoharness2.adapters.slime.capture_wire import PendingTurn

    return PendingTurn(
        prompt_ids=list(prompt_ids),
        capture_params={"top_p": 1.0},
        raw_response={"meta_info": {"id": "rid"}},
        weight_version="7",
        request_id="rid",
    )


def test_record_turn_wrapper_binds_capture_to_tree_turn(world):
    from slime.agent.trajectory import TrajectoryManager

    from repoharness2.adapters.slime import capture_wire as cw

    registry = cw.CaptureRegistry()
    cw.install_capture_wire(registry)
    hook = _RecordingHook()
    registry.register("s-bind", hook)
    manager = TrajectoryManager()
    assert TrajectoryManager.record_turn.__name__ == "rh2_record_turn"

    # 轮 1：stage -> 真实 record_turn（包装 commit + 绑定）
    registry.stage("s-bind", _mk_pending(PROMPT))
    manager.record_turn(
        "s-bind",
        turn=_mk_turn(PROMPT, [11]),
        prompt_messages=[_USER],
        response_message={"role": "assistant", "content": "g1"},
    )
    assert registry.turn_identity_bindings("s-bind") == {1: "cap_bind_t0"}

    # 空 prompt_messages：record_turn 跳过附着——capture 成孤儿，不绑定
    registry.stage("s-bind", _mk_pending(PROMPT))
    manager.record_turn(
        "s-bind",
        turn=_mk_turn(PROMPT, [12]),
        prompt_messages=[],
        response_message=None,
    )
    assert registry.stats["committed"] == 2  # commit 照常发生（既有语义）
    assert registry.turn_identity_bindings("s-bind") == {1: "cap_bind_t0"}  # 无新绑定

    # unregister 清理绑定账
    registry.unregister("s-bind")
    assert registry.turn_identity_bindings("s-bind") == {}


def test_bind_turn_identity_conflict_fail_closed(world):
    from repoharness2.adapters.slime import capture_wire as cw

    registry = cw.CaptureRegistry()
    registry.register("s-dup", _RecordingHook())
    registry.bind_turn_identity("s-dup", 1, "cap_a")
    with pytest.raises(RuntimeError, match="turn_identity_binding_conflict"):
        registry.bind_turn_identity("s-dup", 1, "cap_b")
    assert registry.poison.is_poisoned("s-dup")
    # 幂等同值也拒绝改写路径之外——已有绑定保持原值
    assert registry.turn_capture_binding("s-dup", 1) == "cap_a"


# ---------------------------------------------------------------------------
# 5. PerRolloutAdapter.finish_session 附着 + bringup_leaf_facts 读出
# ---------------------------------------------------------------------------


def _mk_shared_adapter_stub():
    """真实 TrajectoryManager + AnthropicAdapter 会话面形状的最小替身
    （finish_session 语义与 vendor BaseAdapter.finish_session 相同：
    弹 store 取 max_sample_tokens，get_trajectory 弹树）。"""

    from slime.agent.trajectory import TrajectoryManager

    class SharedAdapterStub:
        def __init__(self):
            self.manager = TrajectoryManager()
            self.store = {}

        def open_session(self, sid, *, sampling_defaults=None, max_context_tokens=0):
            self.store[sid] = SimpleNamespace(
                sampling_defaults=dict(sampling_defaults or {}),
                max_context_tokens=int(max_context_tokens or 0),
            )

        async def shutdown_session(self, sid, *, wait_timeout=5.0):
            pass

        async def finish_session(
            self, sid, *, base_sample, reward=0.0, extra_metadata=None, wait_timeout=5.0
        ):
            session = self.store.pop(sid, None)
            max_sample_tokens = (
                int(getattr(session, "max_context_tokens", 0) or 0)
                if session is not None
                else 0
            )
            return self.manager.get_trajectory(
                sid,
                base_sample=base_sample,
                reward=reward,
                extra_metadata=extra_metadata,
                max_sample_tokens=max_sample_tokens,
            )

        async def drop_session(self, sid, *, wait_timeout=5.0):
            self.store.pop(sid, None)
            self.manager.drop_session(sid)

    return SharedAdapterStub()


async def test_per_rollout_adapter_attaches_spans_and_leaf_facts_reads(world):
    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.bringup import (
        bringup_leaf_facts,
        make_per_rollout_adapter,
    )
    from repoharness2.adapters.slime.generate import RH2_TURN_IDENTITY_SPANS_ATTR

    registry = cw.CaptureRegistry()
    hook = _RecordingHook()
    shared = _mk_shared_adapter_stub()
    adapter = make_per_rollout_adapter(registry, shared, hook)
    adapter.open_session("s-prod")
    asst1 = {"role": "assistant", "content": "g1"}
    shared.manager.record_turn(
        "s-prod",
        turn=_mk_turn(PROMPT, [11]),
        prompt_messages=[_USER],
        response_message=asst1,
    )
    shared.manager.record_turn(
        "s-prod",
        turn=_mk_turn(PROMPT + [11, 301], [12]),
        prompt_messages=[_USER, asst1, _TOOL],
        response_message={"role": "assistant", "content": "g2"},
    )
    # commit 时刻绑定的账（本测试不装 wire，手工登记同形绑定）
    registry.bind_turn_identity("s-prod", 1, "cap_bind_t0")
    registry.bind_turn_identity("s-prod", 2, "cap_bind_t1")

    samples = await adapter.finish_session(
        "s-prod", base_sample=_mk_base_sample(world)
    )
    assert len(samples) == 1
    spans = getattr(samples[0], RH2_TURN_IDENTITY_SPANS_ATTR)
    assert [(s.start, s.length, s.capture_record_id) for s in spans] == [
        (0, 1, "cap_bind_t0"),
        (2, 1, "cap_bind_t1"),
    ]
    (facts,) = bringup_leaf_facts("s-prod", samples, hook)
    assert facts.capture_record_ids == ("cap_bind_t0", "cap_bind_t1")
    assert facts.turn_spans == tuple(spans)


async def test_per_rollout_adapter_missing_binding_fail_closed(world):
    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.bringup import make_per_rollout_adapter
    from repoharness2.adapters.slime.generate import SlimeBindingError

    registry = cw.CaptureRegistry()
    shared = _mk_shared_adapter_stub()
    adapter = make_per_rollout_adapter(registry, shared, _RecordingHook())
    adapter.open_session("s-nobind")
    shared.manager.record_turn(
        "s-nobind",
        turn=_mk_turn(PROMPT, [11]),
        prompt_messages=[_USER],
        response_message={"role": "assistant", "content": "g1"},
    )
    # 不登记绑定：trained 轮无 capture 凭据 -> fail-closed
    with pytest.raises(SlimeBindingError) as exc:
        await adapter.finish_session("s-nobind", base_sample=_mk_base_sample(world))
    assert exc.value.reason_code == "turn_identity_binding_missing"


def test_bringup_leaf_facts_missing_spans_fail_closed(world):
    from repoharness2.adapters.slime.bringup import bringup_leaf_facts
    from repoharness2.adapters.slime.generate import SlimeBindingError

    bare = SimpleNamespace(tokens=[1], loss_mask=[1])  # 无身份 span 附加属性
    with pytest.raises(SlimeBindingError) as exc:
        bringup_leaf_facts("s-x", [bare], _RecordingHook())
    assert exc.value.reason_code == "turn_identity_spans_missing_on_leaf"
