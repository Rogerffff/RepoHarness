"""I01（2026-09-08 定案：B 路线）接线与动作覆盖观测的回归。

覆盖面（Brief：docs/.../project1_execution/i01_b_impl_20260909/README.md）：

1. 构造参数：`AnthropicAdapter(fork_threshold_tokens=0)` 的 manager 阈值为 0；
   不传参时库默认 1024 不变（vendored 字节未改）。
2. 生产包装链：`make_per_rollout_adapter` → 真实 `TrajectoryManager` →
   `attach_turn_identity_spans` → `backfill_leaf_sample`，移植 Codex 八案
   （clean / token_drift(20,1024) / message_rewrite × 阈值 1024/0）：阈值 0 下
   两个销毁点（REALIGN 覆盖、消息 rewrite-merge）关闭，旧动作仍有唯一训练
   归属；阈值 1024 的同输入保留旧行为作对照，证明差异只来自阈值。
3. 覆盖统计（TurnCoverageSummary）逐字段断言；`take_turn_coverage` 取走后
   样本上不再残留附加属性（canonicalize 未知属性 fail-closed 边界不被触碰）。
4. FORK 出的多行共享 index/group_index/rollout_id——miles 侧 advantage 与
   rollout_mask_sums 的分组键。
5. run8 唯一留存样本的真实 token 重放（artifact 缺失时 skip）：阈值 0 →
   行长 [19132, 26283]、可训 2772、无掉落；阈值 1024 → 单行 26283、可训
   2148、REALIGN 掉落 1 轮。数字与 Codex 的 run8_cost_probe 一致。
6. Codex 审查（i01_b_impl_20260909/codex_review.md）两条反例的回归：
   R1 共享前缀上的同一次 token FORK 被多条叶重放时事件只记一次；
   R2 `input_tokens_excluding_last_row` 只是表示层观测量，不是 B 相对
   阈值 1024 的实际增量（次轮输出 1024 时两种阈值行长相同、增量为 0）。

本目录纪律：不得模块级 import slime/miles——一律函数内 import。
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN8_DIR = (
    REPO_ROOT
    / "docs/agentic_RL/repo_harness_rh2_workstreams/s1/7a_artifacts/artifacts_run8"
)

PROMPT = [100, 101]
_USER = {"role": "user", "content": "task"}
_TOOL = {"role": "tool", "content": "observation"}
_ASST = {"role": "assistant", "content": "original"}


def _mk_turn(prompt_ids, output_ids, logprob=-0.2):
    from slime.agent.trajectory import TurnRecord

    return TurnRecord(
        prompt_ids=list(prompt_ids),
        output_ids=list(output_ids),
        finish_reason="stop",
        output_log_probs=[logprob] * len(output_ids),
    )


def _mk_base_sample(world):
    return world.SS(index=0, group_index=0, prompt="p")


class _RecordingHook:
    def __init__(self):
        self.records = []

    def on_generate_response(self, *, prompt_token_ids, sampling_params, response):
        record = SimpleNamespace(record_id=f"cap_bind_t{len(self.records)}")
        self.records.append(record)
        return record


def _mk_shared_adapter_stub(fork_threshold):
    """真实 TrajectoryManager + vendor BaseAdapter 会话面形状的最小替身（与
    test_f1_turn_identity 同形，只多一个阈值参数）。"""

    from slime.agent.trajectory import TrajectoryManager

    class SharedAdapterStub:
        def __init__(self):
            self.manager = TrajectoryManager(fork_threshold_tokens=fork_threshold)
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


def _mk_tape(record_id, turn_index, prompt_ids, output_ids):
    from repoharness2.adapters.slime.generate import TurnTape

    return TurnTape(
        record_id=record_id,
        turn_index=turn_index,
        prompt_token_count=len(prompt_ids),
        response_token_count=len(output_ids),
        output_ids=tuple(output_ids),
        output_log_probs=tuple([-0.2] * len(output_ids)),
        top_p_token_ids=None,
        top_p_token_offsets=None,
        routed_experts_flat=None,
        weight_version=str(turn_index),
    )


# ---------------------------------------------------------------------------
# 1. 构造参数
# ---------------------------------------------------------------------------


def test_anthropic_adapter_threshold_zero_and_library_default_unchanged(world):
    from slime.agent.adapters.anthropic import AnthropicAdapter

    wired = AnthropicAdapter(tokenizer=object(), sglang_url="http://unused", fork_threshold_tokens=0)
    assert wired.manager._fork_threshold == 0
    stock = AnthropicAdapter(tokenizer=object(), sglang_url="http://unused")
    assert stock.manager._fork_threshold == 1024  # vendored 库默认不变，只有 bringup 接线为 0


# ---------------------------------------------------------------------------
# 2/3/4. 生产包装链八案 + 覆盖统计 + 多行共享 rollout 身份
# ---------------------------------------------------------------------------

_CASES = [
    # (case, threshold, new_output_len)
    ("clean", 1024, 20),
    ("clean", 0, 20),
    ("token_drift", 1024, 20),
    ("token_drift", 1024, 1024),
    ("token_drift", 0, 20),
    ("token_drift", 0, 1024),
    ("message_rewrite", 1024, 20),
    ("message_rewrite", 0, 20),
]


async def _run_case(world, case, threshold, new_output_len):
    """两轮会话：第一轮 4 token 响应；第二轮 prompt 在第一轮响应内 token 漂移
    （token_drift）或消息级改写（message_rewrite）。返回 (samples, coverage, used_ids)。"""

    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.bringup import make_per_rollout_adapter
    from repoharness2.adapters.slime.generate import (
        RH2_TURN_COVERAGE_ATTR,
        RH2_TURN_IDENTITY_SPANS_ATTR,
        backfill_leaf_sample,
        take_turn_coverage,
    )

    registry = cw.CaptureRegistry()
    shared = _mk_shared_adapter_stub(threshold)
    adapter = make_per_rollout_adapter(registry, shared, _RecordingHook())
    sid = f"s-{case}-{threshold}-{new_output_len}"
    adapter.open_session(sid)

    r1 = [201, 202, 203, 204]
    r2 = list(range(5000, 5000 + new_output_len))
    t1 = _mk_turn(PROMPT, r1)
    p2 = PROMPT + r1 + [300]
    echoed = dict(_ASST)
    if case == "token_drift":
        p2[4] = 999  # 分歧落在第一轮响应之内（偏移 2/4）
    if case == "message_rewrite":
        echoed["content"] = "rewritten"
        p2[4] = 999
    t2 = _mk_turn(p2, r2)
    shared.manager.record_turn(sid, turn=t1, prompt_messages=[_USER], response_message=_ASST)
    shared.manager.record_turn(
        sid,
        turn=t2,
        prompt_messages=[_USER, echoed, _TOOL],
        response_message={"role": "assistant", "content": "done"},
    )
    registry.bind_turn_identity(sid, 1, "c1")
    registry.bind_turn_identity(sid, 2, "c2")

    samples = await adapter.finish_session(sid, base_sample=_mk_base_sample(world))
    assert samples
    coverage = take_turn_coverage(samples)
    assert coverage is not None
    for s in samples:
        assert RH2_TURN_COVERAGE_ATTR not in s.__dict__  # 取走即剥除

    tapes = {"c1": _mk_tape("c1", 1, t1.prompt_ids, r1), "c2": _mk_tape("c2", 2, t2.prompt_ids, r2)}
    used = []
    for s in samples:
        spans = getattr(s, RH2_TURN_IDENTITY_SPANS_ATTR)
        turn_tapes = [tapes[x.capture_record_id] for x in spans]
        used.extend(
            t.record_id
            for t in backfill_leaf_sample(
                s, turn_tapes, identity_spans=spans, require_real_weight_versions=True
            )
        )
    return samples, coverage, used


@pytest.mark.parametrize("case,threshold,new_output_len", _CASES)
async def test_wired_chain_eight_cases(world, case, threshold, new_output_len):
    samples, cov, used = await _run_case(world, case, threshold, new_output_len)
    trained_tokens = sum(sum(s.loss_mask) for s in samples)

    old_turn_kept = threshold == 0 or case == "clean" or new_output_len >= 1024
    assert trained_tokens == (4 + new_output_len if old_turn_kept else new_output_len)
    assert used == (["c1", "c2"] if old_turn_kept else ["c2"])

    assert cov["fork_threshold_tokens"] == threshold
    assert cov["turns_generated"] == 2
    assert cov["turns_empty_output"] == 0
    assert cov["training_rows"] == len(samples)
    assert cov["row_trainable_tokens"] == [sum(s.loss_mask) for s in samples]
    assert cov["row_tokens"] == [len(s.tokens) for s in samples]
    assert cov["trainable_tokens_total"] == trained_tokens
    assert cov["input_tokens_total"] == sum(cov["row_tokens"])
    assert cov["input_tokens_excluding_last_row"] == sum(cov["row_tokens"]) - cov["row_tokens"][-1]

    if case == "clean":
        assert (cov["turns_trained"], cov["turns_dropped_realign"], cov["turns_dropped_merge"]) == (2, 0, 0)
        assert cov["training_rows"] == 1 and cov["fork_events"] == []
    elif case == "token_drift":
        if old_turn_kept:
            assert (cov["turns_trained"], cov["turns_dropped_realign"]) == (2, 0)
            assert cov["training_rows"] == 2
            assert cov["fork_events"] == [
                {
                    "turn_index": 2,
                    "prev_response_len": 4,
                    "divergence_offset_in_prev_response": 2,
                    "next_output_len": new_output_len,
                    "position": "in_response",
                }
            ]
        else:  # 阈值 1024 + 新输出 < 1024：REALIGN 覆盖旧轮（旧行为，对照）
            assert (cov["turns_trained"], cov["turns_dropped_realign"]) == (1, 1)
            assert cov["training_rows"] == 1 and cov["fork_events"] == []
        assert cov["turns_dropped_merge"] == 0
    else:  # message_rewrite
        if threshold == 0:
            # merge 关闭：改写的 assistant 在树上另起分支，旧生成节点保留为独立叶
            assert (cov["turns_trained"], cov["turns_dropped_merge"]) == (2, 0)
            assert cov["training_rows"] == 2 and cov["fork_events"] == []
        else:  # 阈值 1024：rewrite-merge 把旧节点降为 routing-only（旧行为，对照）
            assert (cov["turns_trained"], cov["turns_dropped_merge"]) == (1, 1)
            assert cov["training_rows"] == 1
        assert cov["turns_dropped_realign"] == 0


async def test_fork_rows_share_rollout_identity(world):
    """FORK 出的两行共享 index/group_index/rollout_id——miles 按 rollout_id 求
    rollout_mask_sums、按 group_index 算优势，新增行不会成为新 member。"""

    samples, cov, _ = await _run_case(world, "token_drift", 0, 20)
    assert cov["training_rows"] == 2 and len(samples) == 2
    keys = {(s.index, s.group_index, s.rollout_id) for s in samples}
    assert keys == {(0, 0, 0)}


def test_take_turn_coverage_absent_returns_none(world):
    from repoharness2.adapters.slime.generate import take_turn_coverage

    bare = SimpleNamespace(tokens=[1], loss_mask=[1])
    assert take_turn_coverage([bare]) is None
    assert take_turn_coverage([]) is None
    assert take_turn_coverage(None) is None


# ---------------------------------------------------------------------------
# 5. run8 真实 token 重放
# ---------------------------------------------------------------------------


def _load_run8_turns():
    projections = list(RUN8_DIR.glob("rollouts/*/trajectory_projection.json"))
    if len(projections) != 1:
        pytest.skip("run8 唯一留存 projection 不在本地（浅 checkout / 文档目录缺失），跳过重放")
    directory = projections[0].parent
    captures = json.loads((directory / "capture_records.json").read_text())
    turns = []
    for capture in captures:
        columns = []
        for field in ("prompt_token_ids_ref", "response_token_ids_ref"):
            reference = capture[field]
            raw = (directory / "tapes" / f"{reference['ref_id']}.bin").read_bytes()
            assert hashlib.sha256(raw).hexdigest() == reference["sha256"].split(":")[1]
            columns.append(list(struct.unpack("<" + "i" * (len(raw) // 4), raw)))
        turns.append(columns)
    return turns


@pytest.mark.parametrize(
    "threshold,expect",
    [
        (
            0,
            dict(row_tokens=[19132, 26283], trainable=2772, rows=2, trained=6, dropped_realign=0,
                 extra=19132, forks=1),
        ),
        (
            1024,
            dict(row_tokens=[26283], trainable=2148, rows=1, trained=5, dropped_realign=1,
                 extra=0, forks=0),
        ),
    ],
)
def test_run8_real_tokens_replay(world, threshold, expect):
    from slime.agent.trajectory import TrajectoryManager

    from repoharness2.adapters.slime.turn_identity import (
        export_leaf_identity_spans_with_coverage,
    )

    turns = _load_run8_turns()
    manager = TrajectoryManager(fork_threshold_tokens=threshold)
    history = [_USER]
    for k, (prompt_ids, output_ids) in enumerate(turns):
        asst = {"role": "assistant", "content": f"g{k}"}
        manager.record_turn(
            "run8",
            turn=_mk_turn(prompt_ids, output_ids, logprob=0.0),
            prompt_messages=list(history),
            response_message=asst,
        )
        history += [asst, {"role": "tool", "content": f"o{k}"}]
    root = manager._trees["run8"]
    samples = manager.get_trajectory("run8", base_sample=_mk_base_sample(world))
    exports, cov = export_leaf_identity_spans_with_coverage(root, fork_threshold=threshold)
    assert [list(s.tokens) for s in samples] == [e.tokens for e in exports]

    assert cov.row_tokens == expect["row_tokens"]
    assert cov.trainable_tokens_total == expect["trainable"]
    assert cov.training_rows == expect["rows"]
    assert cov.turns_generated == 6
    assert cov.turns_trained == expect["trained"]
    assert cov.turns_dropped_realign == expect["dropped_realign"]
    assert cov.turns_dropped_merge == 0
    assert cov.input_tokens_total == sum(expect["row_tokens"])
    assert cov.input_tokens_excluding_last_row == expect["extra"]
    assert len(cov.fork_events) == expect["forks"]
    if expect["forks"]:
        assert cov.fork_events == [
            {
                "turn_index": 2,
                "prev_response_len": 624,
                "divergence_offset_in_prev_response": 556,
                "next_output_len": 606,
                "position": "in_response",
            }
        ]


# ---------------------------------------------------------------------------
# 6. Codex 审查反例的回归（R1 / R2）
# ---------------------------------------------------------------------------


async def _run_specs(world, specs, threshold, *, cap=0):
    """多轮会话通用驱动：specs = [(prompt_ids, output_ids, prompt_messages, response_message)]。
    经真实 AnthropicAdapter 会话面 + 生产 finish 包装，返回 (samples, coverage)。"""

    from slime.agent.adapters.anthropic import AnthropicAdapter

    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.bringup import make_per_rollout_adapter
    from repoharness2.adapters.slime.generate import take_turn_coverage

    class _Tok:
        def decode(self, ids, **kw):
            return ",".join(map(str, ids))

    registry = cw.CaptureRegistry()
    shared = AnthropicAdapter(tokenizer=_Tok(), sglang_url="http://unused", fork_threshold_tokens=threshold)
    adapter = make_per_rollout_adapter(registry, shared, _RecordingHook())
    sid = f"s-specs-{threshold}"
    adapter.open_session(sid, max_context_tokens=cap)
    for i, (prompt_ids, output_ids, history, reply) in enumerate(specs, start=1):
        shared.manager.record_turn(
            sid, turn=_mk_turn(prompt_ids, output_ids), prompt_messages=history, response_message=reply
        )
        registry.bind_turn_identity(sid, i, f"c{i}")
    samples = await adapter.finish_session(sid, base_sample=_mk_base_sample(world))
    return samples, take_turn_coverage(samples)


_A1 = {"role": "assistant", "content": "a1"}
_A2 = {"role": "assistant", "content": "a2"}
_A3 = {"role": "assistant", "content": "a3"}
_A4 = {"role": "assistant", "content": "a4"}
_O1 = {"role": "tool", "content": "o1"}
_O2 = {"role": "tool", "content": "o2"}
_O3 = {"role": "tool", "content": "o3"}
_P1, _R1 = [100, 101], [201, 202, 203, 204]
_P2, _R2 = [100, 101, 201, 202, 999, 204, 300], [401, 402]  # 在 t1 响应内漂移
_P3, _R3 = _P2 + _R2 + [500], [601, 602]


async def test_r1_shared_prefix_fork_event_counted_once(world):
    """R1：t2 相对 t1 响应内 token 漂移（一次 FORK）；t4 的历史改写 t3，树上分出第二条叶，
    两条叶共享 t1..t2 前缀。事件必须按真实生成轮只记一次，训练归属仍各一次。"""

    rewrite = {"role": "assistant", "content": "a3-rewritten"}
    specs = [
        (_P1, _R1, [_USER], _A1),
        (_P2, _R2, [_USER, _A1, _O1], _A2),
        (_P3, _R3, [_USER, _A1, _O1, _A2, _O2], _A3),
        (_P3 + [601, 999] + [700], [801, 802], [_USER, _A1, _O1, _A2, _O2, rewrite, _O3], _A4),
    ]
    samples, cov = await _run_specs(world, specs, 0, cap=100)
    assert cov["training_rows"] == 3 and [len(s.tokens) for s in samples] == [6, 12, 15]
    assert cov["turns_generated"] == 4 and cov["turns_trained"] == 4
    assert [e["turn_index"] for e in cov["fork_events"]] == [2]  # 修复前为 [2, 2]
    assert cov["fork_events"][0]["position"] == "in_response"


async def test_r1_two_independent_forks_both_recorded(world):
    """连续两次独立漂移（t2、t3 各自在上一响应内漂移）仍分别记录。"""

    specs = [
        (_P1, _R1, [_USER], _A1),
        (_P2, _R2, [_USER, _A1, _O1], _A2),
        ([100, 101, 201, 202, 999, 204, 300, 401, 999, 500], _R3, [_USER, _A1, _O1, _A2, _O2], _A3),
    ]
    _, cov = await _run_specs(world, specs, 0, cap=100)
    assert cov["training_rows"] == 3 and cov["turns_trained"] == 3
    assert [e["turn_index"] for e in cov["fork_events"]] == [2, 3]


@pytest.mark.parametrize("threshold", [0, 1024])
async def test_r2_excluding_last_row_is_not_a_delta_against_old_threshold(world, threshold):
    """R2：次轮输出恰为 1024 时旧阈值同样 FORK——两种阈值行长都是 [6, 1031]，B 的真实增量为 0；
    `input_tokens_excluding_last_row` 在两种阈值下都等于 6，因此它只是表示层观测量。"""

    specs = [
        (_P1, _R1, [_USER], _A1),
        (_P2, list(range(1000, 2024)), [_USER, _A1, _O1], _A2),
    ]
    samples, cov = await _run_specs(world, specs, threshold, cap=2000)
    assert [len(s.tokens) for s in samples] == [6, 1031]
    assert cov["input_tokens_total"] == 1037
    assert cov["input_tokens_excluding_last_row"] == 6  # 与阈值无关：不能读成"相对 1024 多出 6"
    assert cov["training_rows"] == 2 and cov["turns_dropped_realign"] == 0


# ---------------------------------------------------------------------------
# 7. 运输接缝：orchestrator → execution audit 落盘 → canonicalize → 组准入 → buffer →
#    训练数据转换（移植自 Codex 审查的 production_transport_probe.py；生成响应、capture
#    绑定、Docker、评分与排空屏障用既有测试替身）
# ---------------------------------------------------------------------------


async def test_coverage_reaches_audit_and_conversion_through_orchestrator(world, tmp_path):
    from slime.agent.adapters.anthropic import AnthropicAdapter
    from slime.agent.trajectory import TurnRecord

    from repoharness2.adapters.slime.bringup import (
        bringup_leaf_facts,
        make_per_rollout_adapter,
        write_execution_audit_record,
    )
    from repoharness2.adapters.slime.capture_wire import CaptureRegistry
    from repoharness2.adapters.slime.generate import (
        RH2_TURN_COVERAGE_ATTR,
        RH2_TURN_IDENTITY_SPANS_ATTR,
    )
    from test_w1a_formal_chain import _dense_turns
    from test_w1b_group_admission import (
        BOTH_OK,
        _buffer,
        _build_chain,
        _convert,
        _dispatch_group,
        _entry,
        _miles_args,
    )

    world.install_sglang_stub()
    registry = CaptureRegistry()
    shared = AnthropicAdapter(
        tokenizer=SimpleNamespace(decode=lambda ids, **kw: "decoded"),
        sglang_url="http://unused",
        fork_threshold_tokens=0,
    )
    active: dict = {}

    def factory(hook, session_defaults):
        adapter = make_per_rollout_adapter(registry, shared, hook)
        original_open = adapter.open_session

        def open_session(sid, **kwargs):
            active.update(sid=sid, hook=hook, defaults=session_defaults)
            return original_open(sid, **kwargs)

        adapter.open_session = open_session
        return adapter

    class Driver:
        name = "mock_harness"

        async def run(self, *args, **kwargs):
            sid = active["sid"]
            history = [{"role": "user", "content": "task"}]
            for index, scripted in enumerate(_dense_turns()):
                prompt_ids = list(scripted.prompt_ids)
                if index == 1:
                    prompt_ids[14] = 9999  # 分歧位于上一响应内：阈值 0 应保留两行
                record = active["hook"].on_generate_response(
                    prompt_token_ids=prompt_ids,
                    sampling_params=active["defaults"],
                    response=scripted.response,
                )
                rows = scripted.response["meta_info"]["output_token_logprobs"]
                turn = TurnRecord(
                    prompt_ids=prompt_ids,
                    output_ids=[row[1] for row in rows],
                    output_log_probs=[row[0] for row in rows],
                    finish_reason="stop",
                )
                answer = {"role": "assistant", "content": f"answer-{index}"}
                shared.manager.record_turn(
                    sid, turn=turn, prompt_messages=list(history), response_message=answer
                )
                registry.bind_turn_identity(sid, index + 1, record.record_id)
                history += [answer, {"role": "tool", "content": f"observation-{index}"}]
            return 0

    try:
        chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
        chain.orchestrator._adapter_factory = factory
        chain.orchestrator._harness_driver = Driver()
        chain.orchestrator._leaf_facts_fn = bringup_leaf_facts
        audit_path = tmp_path / "execution_audit.jsonl"
        chain.orchestrator._audit_sink = lambda audit: write_execution_audit_record(
            None, audit, audit_path
        )
        prompt_group, group = await _dispatch_group(world, chain)

        # ① execution audit：每个 member 一条记录，覆盖统计落盘
        records = [json.loads(line) for line in audit_path.read_text().splitlines()]
        assert len(records) == 2
        assert [len(member) for member in group] == [2, 2]
        for record in records:
            coverage = record["turn_coverage"]
            assert coverage["fork_threshold_tokens"] == 0
            assert coverage["turns_generated"] == coverage["turns_trained"] == 2
            assert coverage["training_rows"] == 2
            assert coverage["row_tokens"] == [22, 35]
            assert coverage["row_trainable_tokens"] == [10, 8]
            assert coverage["input_tokens_total"] == 57
            assert [e["turn_index"] for e in coverage["fork_events"]] == [2]
        # ② 交付的 miles 样本上没有任何诊断/身份临时属性
        for member in group:
            for leaf in member:
                assert isinstance(leaf, world.MS)
                assert RH2_TURN_COVERAGE_ATTR not in leaf.__dict__
                assert RH2_TURN_IDENTITY_SPANS_ATTR not in leaf.__dict__
                assert RH2_TURN_COVERAGE_ATTR not in leaf.metadata
        # ③ 组准入 → buffer → 训练数据转换：两行共享 rollout_id，分母跨行求和
        args = _miles_args(world, chain)
        buffer, recycled = _buffer(world, args)
        await buffer.put(_entry(world, prompt_group, group))
        delivered = await buffer.get(current_version=5)
        assert delivered.group is group and not recycled
        converted = _convert(world, args, delivered.group)
        assert converted["rollout_ids"] == [0, 0, 1, 1]
        assert converted["rollout_mask_sums"] == [18, 18, 18, 18]
        assert converted["raw_reward"] == [1.0, 1.0, 0.0, 0.0]
    finally:
        registry.close()
