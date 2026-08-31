"""per-token weight version spans 端到端（vendor refresh V2）。

覆盖四段链路（adv_miles 反例：一条 /generate 跨权重更新时
`meta_info.weight_versions=[{version,start,end},...]`，单数 `weight_version`
只是最后区间——单数记账把 v10+v11 轮记成全 v11，staleness 低报）：

1. `parse_weight_version_spans`：wire 形态/合同不变式（以 sglang 4e230c3d
   weight_versions.py 及其单测为准），**引擎报了就必须合法**（fail-closed）；
2. capture wire（`rh2_call_sglang_generate`）：合法 spans 进 PendingTurn/
   TurnTape/registry 版本账（全部区间版本），坏 spans 当轮抛错 + poison；
   未报 spans 回退单数、provenance=single_version_only；
3. backfill：spans 的**全部**版本并入 `Sample.weight_versions`（oldest/min
   语义修复），结构化 facts 挂附加属性；
4. canonicalize：facts 校验（类型/两本账互检/双事实源）后转
   `metadata["rh2_weight_version_spans"]`，miles `oldest_weight_version`
   端到端恢复真实最旧版本。

按 conftest 约定：slime/miles/repoharness2.adapters.* 一律测试函数内（或
fixture 内）import，不在模块级 import。
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# 1. parse_weight_version_spans（wire 合同）
# ---------------------------------------------------------------------------


def _parse(world, meta, generated):
    from repoharness2.adapters.slime.generate import parse_weight_version_spans

    return parse_weight_version_spans(meta, generated=generated)


def _meta(spans, single="auto", **extra):
    meta = dict(extra)
    if spans is not None:
        meta["weight_versions"] = spans
        if single == "auto" and spans and isinstance(spans[-1], dict):
            meta["weight_version"] = spans[-1].get("version")
        elif single != "auto":
            if single is not None:
                meta["weight_version"] = single
    elif single not in ("auto", None):
        meta["weight_version"] = single
    return meta


def test_parse_absent_returns_none(world):
    assert _parse(world, {"weight_version": "7"}, 5) is None
    assert _parse(world, {}, 5) is None


def test_parse_single_span_ok(world):
    spans = _parse(world, _meta([{"version": "10", "start": 0, "end": 5}]), 5)
    assert [(s.version, s.start, s.end) for s in spans] == [("10", 0, 5)]


def test_parse_adv_miles_example_ok(world):
    """adv_miles 反例原样：v10 300 token -> 更新 v11 -> 续 200 token。"""

    spans = _parse(
        world,
        _meta(
            [
                {"version": "10", "start": 0, "end": 300},
                {"version": "11", "start": 300, "end": 500},
            ]
        ),
        500,
    )
    assert [(s.version, s.start, s.end) for s in spans] == [("10", 0, 300), ("11", 300, 500)]


def test_parse_zero_output_empty_span_ok(world):
    """sglang 合同：零输出轮恰好一个空区间 {v, 0, 0}。"""

    spans = _parse(world, _meta([{"version": "9", "start": 0, "end": 0}]), 0)
    assert [(s.version, s.start, s.end) for s in spans] == [("9", 0, 0)]


def test_parse_version_can_return_after_tokens(world):
    """sglang 单测：版本可回归（v1->v2->v1），不得假设单调。"""

    spans = _parse(
        world,
        _meta(
            [
                {"version": "1", "start": 0, "end": 2},
                {"version": "2", "start": 2, "end": 4},
                {"version": "1", "start": 4, "end": 6},
            ]
        ),
        6,
    )
    assert [s.version for s in spans] == ["1", "2", "1"]


@pytest.mark.parametrize(
    ("reason", "meta_builder", "generated"),
    [
        # 键在场值为 null ≠ 键缺失（P2 #1）：writer 只会不写键或写非空 list，
        # null 走 fail-closed，不得洗成"旧引擎"回退单数
        ("null", lambda: {"weight_versions": None, "weight_version": "10"}, 3),
        ("not_a_list", lambda: {"weight_versions": "10", "weight_version": "10"}, 3),
        ("empty", lambda: {"weight_versions": [], "weight_version": "10"}, 3),
        ("item_not_mapping", lambda: _meta([["10", 0, 3]], single="10"), 3),
        ("item_missing_keys", lambda: _meta([{"version": "10", "start": 0}], single="10"), 3),
        # version 必须是字符串（P2 #1，pin 的 writer 显式 str 化）：int 不再
        # 宽容转换——原正例 test_parse_int_version_coerced_to_str 改为本负例
        ("version_not_string", lambda: _meta([{"version": 7, "start": 0, "end": 3}], single="7"), 3),
        ("version_not_string", lambda: _meta([{"version": 1.5, "start": 0, "end": 3}], single="1.5"), 3),
        ("version_empty", lambda: _meta([{"version": "", "start": 0, "end": 3}], single=""), 3),
        ("bound_not_int", lambda: _meta([{"version": "10", "start": True, "end": 3}], single="10"), 3),
        ("bound_negative", lambda: _meta([{"version": "10", "start": -1, "end": 3}], single="10"), 3),
        ("first_start_nonzero", lambda: _meta([{"version": "10", "start": 1, "end": 3}], single="10"), 3),
        (
            "gap",
            lambda: _meta(
                [{"version": "10", "start": 0, "end": 1}, {"version": "11", "start": 2, "end": 3}],
                single="11",
            ),
            3,
        ),
        (
            "overlap",
            lambda: _meta(
                [{"version": "10", "start": 0, "end": 2}, {"version": "11", "start": 1, "end": 3}],
                single="11",
            ),
            3,
        ),
        (
            "adjacent_same_version",
            lambda: _meta(
                [{"version": "10", "start": 0, "end": 2}, {"version": "10", "start": 2, "end": 3}],
                single="10",
            ),
            3,
        ),
        (
            "zero_output_shape",
            lambda: _meta([{"version": "10", "start": 0, "end": 2}], single="10"),
            0,
        ),
        ("empty_span", lambda: _meta([{"version": "10", "start": 0, "end": 0}], single="10"), 3),
        # 末区间 end 与生成 token 数不一致：越界（end 超出）与欠覆盖各一条
        ("end_mismatch", lambda: _meta([{"version": "10", "start": 0, "end": 5}], single="10"), 3),
        ("end_mismatch", lambda: _meta([{"version": "10", "start": 0, "end": 2}], single="10"), 3),
        ("single_version_missing", lambda: {"weight_versions": [{"version": "10", "start": 0, "end": 3}]}, 3),
        (
            "single_version_mismatch",
            lambda: _meta([{"version": "10", "start": 0, "end": 3}], single="11"),
            3,
        ),
    ],
)
def test_parse_fail_closed(world, reason, meta_builder, generated):
    from repoharness2.adapters.slime.generate import SlimeBindingError

    with pytest.raises(SlimeBindingError) as err:
        _parse(world, meta_builder(), generated)
    assert err.value.reason_code == f"weight_version_spans_{reason}"


# ---------------------------------------------------------------------------
# 2. capture hook 直调路径（探针/测试替身：hook 自行解析同一函数）
# ---------------------------------------------------------------------------


def _mk_hook():
    from repoharness2.adapters.slime.generate import GenerationCaptureHook

    return GenerationCaptureHook(
        trajectory_id="traj_wvs",
        model_name="m",
        backend_name="sglang",
        backend_version="test",
        renderer_cls_name="r",
        tokenizer_name="tok",
        template_hash="sha256:" + "0" * 64,
    )


def _hook_response(meta_over=None, n_tokens=2):
    meta = {
        "id": "rid-1",
        "weight_version": "11",
        "finish_reason": {"type": "stop"},
        "output_token_logprobs": [[-0.5, 100 + i] for i in range(n_tokens)],
    }
    meta.update(meta_over or {})
    return {"text": "ok", "meta_info": meta}


_PARAMS = {
    "temperature": 1.0,
    "top_p": 1.0,
    "max_new_tokens": 64,
    "return_top_p_token_ids": False,
    "return_routed_experts": False,
}


def test_hook_direct_parses_spans_and_provenance(world):
    hook = _mk_hook()
    record = hook.on_generate_response(
        prompt_token_ids=[1, 2],
        sampling_params=_PARAMS,
        response=_hook_response(
            {
                "weight_versions": [
                    {"version": "10", "start": 0, "end": 1},
                    {"version": "11", "start": 1, "end": 2},
                ]
            }
        ),
    )
    assert record.capture_status == "complete"
    tape = hook.tapes[-1]
    assert [(s.version, s.start, s.end) for s in tape.weight_version_spans] == [
        ("10", 0, 1),
        ("11", 1, 2),
    ]
    assert tape.weight_version == "11"  # 单数 = finalize 时刻值（FA-0 收窄）
    assert tape.weight_version_provenance == "engine_spans"


def test_hook_direct_no_spans_falls_back_single(world):
    hook = _mk_hook()
    record = hook.on_generate_response(
        prompt_token_ids=[1, 2],
        sampling_params=_PARAMS,
        response=_hook_response(),
    )
    assert record.capture_status == "complete"
    tape = hook.tapes[-1]
    assert tape.weight_version_spans is None
    assert tape.weight_version == "11"
    assert tape.weight_version_provenance == "single_version_only"


def test_hook_direct_bad_spans_partial_mismatch(world):
    """直调路径坏 spans：hook 只记账不抛——partial + mismatch（投影层拒收）。"""

    hook = _mk_hook()
    record = hook.on_generate_response(
        prompt_token_ids=[1, 2],
        sampling_params=_PARAMS,
        response=_hook_response(
            {
                "weight_versions": [
                    {"version": "10", "start": 0, "end": 1},
                    {"version": "11", "start": 2, "end": 3},  # 缝隙
                ],
                "weight_version": "11",
                "output_token_logprobs": [[-0.5, 100], [-0.4, 101], [-0.3, 102]],
            }
        ),
    )
    assert record.capture_status == "partial"
    assert record.alignment_status == "mismatch"
    assert hook.tapes[-1].weight_version_spans is None


def test_hook_turn_weight_versions_expands_spans(world):
    """Outcome 记账 helper：spans 轮展开全部区间版本（intra_execution_version_span
    的 max-min 派生才不低报），单数轮取单数，failed 轮（无版本）跳过。"""

    from repoharness2.adapters.slime.generate import hook_turn_weight_versions

    hook = _mk_hook()
    hook.on_generate_response(
        prompt_token_ids=[1, 2],
        sampling_params=_PARAMS,
        response=_hook_response(
            {
                "weight_versions": [
                    {"version": "10", "start": 0, "end": 1},
                    {"version": "11", "start": 1, "end": 2},
                ]
            }
        ),
    )
    hook.on_generate_response(
        prompt_token_ids=[1, 2], sampling_params=_PARAMS, response=_hook_response()
    )
    hook.on_generate_response(  # meta_info 缺失 -> failed record、无 tape、无版本
        prompt_token_ids=[1, 2], sampling_params=_PARAMS, response={"text": "x"}
    )
    assert hook_turn_weight_versions(hook) == ["10", "11", "11"]


def test_hook_turn_weight_versions_empty_is_none(world):
    from repoharness2.adapters.slime.generate import hook_turn_weight_versions

    assert hook_turn_weight_versions(_mk_hook()) is None


# ---------------------------------------------------------------------------
# 3. capture wire（rh2_call_sglang_generate 真函数 + fake aiohttp/引擎）
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload):
        self.status = 200
        self._payload = payload

    async def json(self, content_type=None):
        return self._payload

    async def text(self):
        return ""


class _PostCM:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, *exc):
        return False


class _FakeEngine:
    def __init__(self):
        self.requests: list[dict] = []
        self.response_payload: dict | None = None


class _FakeClientSession:
    def __init__(self, engine):
        self._engine = engine

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def post(self, url, json=None, headers=None):
        self._engine.requests.append({"url": url, "payload": json, "headers": headers})
        return _PostCM(_FakeResponse(self._engine.response_payload))


class _FakeAiohttp:
    class ClientError(Exception):
        pass

    def __init__(self, engine):
        self._engine = engine

    def ClientTimeout(self, **_kw):  # noqa: N802 - 镜像 aiohttp API 名
        return None

    def ClientSession(self, **_kw):  # noqa: N802
        return _FakeClientSession(self._engine)


SID = "sid-wvs-test"


@pytest.fixture(scope="module")
def wire(_vendor_slime_world):
    from slime.agent.adapters import common as slime_common

    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.generate import GenerationCaptureHook

    registry = cw.CaptureRegistry()
    registry.register(
        SID,
        GenerationCaptureHook(
            trajectory_id="traj_wvs_wire",
            model_name="m",
            backend_name="sglang",
            backend_version="test",
            renderer_cls_name="r",
            tokenizer_name="tok",
            template_hash="sha256:" + "0" * 64,
        ),
    )
    cw.install_capture_wire(registry)

    engine = _FakeEngine()
    saved_aiohttp = cw.aiohttp
    cw.aiohttp = _FakeAiohttp(engine)
    try:
        yield SimpleNamespace(
            registry=registry, engine=engine, slime_common=slime_common, cw=cw
        )
    finally:
        cw.aiohttp = saved_aiohttp
        # vendor slime 模块随 _vendor_slime_world teardown 整体摘除。


def _wire_payload(meta_over=None):
    meta = {
        "id": "rid-wire",
        "weight_version": "11",
        "finish_reason": {"type": "stop"},
        "output_token_logprobs": [[-1.0, 7], [-0.8, 8], [-0.6, 9]],
    }
    meta.update(meta_over or {})
    return {"text": "ok", "meta_info": meta}


async def _call(wire, payload, sid=SID):
    wire.engine.response_payload = payload
    session = wire.slime_common.Session(sampling_defaults={}, max_context_tokens=0)
    adapter = SimpleNamespace(
        logger=logging.getLogger("test_weight_version_spans"),
        max_token_keys=("max_tokens",),
        stop_keys=("stop",),
        sglang_url="http://fake-engine:1",
    )
    return await wire.slime_common.call_sglang_generate(
        [101, 102, 103], session, {}, adapter=adapter, session_id=sid
    )


def _pop_staged(wire, sid=SID):
    slot = wire.registry.pending.get(sid) or {}
    assert len(slot) == 1, f"期望恰好 1 条暂存，得到 {len(slot)}"
    return slot.pop(next(iter(slot)))


async def test_wire_valid_spans_staged_and_ledgered(wire):
    """合法 spans：PendingTurn 携带，commit 后 registry 版本账含全部区间版本。"""

    await _call(
        wire,
        _wire_payload(
            {
                "weight_versions": [
                    {"version": "10", "start": 0, "end": 2},
                    {"version": "11", "start": 2, "end": 3},
                ]
            }
        ),
    )
    slot = wire.registry.pending.get(SID) or {}
    assert len(slot) == 1
    staged = next(iter(slot.values()))
    assert [(s.version, s.start, s.end) for s in staged.weight_version_spans] == [
        ("10", 0, 2),
        ("11", 2, 3),
    ]
    assert staged.weight_version == "11"

    # commit（record_turn 时点）：版本账 = 全部区间版本（不是只有单数 "11"）
    import contextvars

    ctx = contextvars.copy_context()

    def _commit():
        wire.cw._capture_request_key.set(staged.request_id)
        return wire.registry.commit(SID)

    capture_ref = ctx.run(_commit)
    assert capture_ref is not None
    assert wire.registry.weight_versions[SID] == ["10", "11"]
    tape = wire.registry.hooks[SID].tapes[-1]
    assert tape.weight_version_provenance == "engine_spans"
    assert [s.version for s in tape.weight_version_spans] == ["10", "11"]


async def test_wire_bad_spans_fail_closed(wire):
    """引擎报了 spans 就必须合法：重叠区间当轮抛错、零暂存、版本账干净。

    注：poison 属于 proxy delivered-draft 生命周期兜底（F5 guard 只在
    proxy_result 非 None 时 poison+abandon）；本测试走无 proxy 直连路径，
    fail-closed 的形态 = 异常传播（该轮不产生 TurnRecord、不 stage、
    不进版本账），上游 _run_turn 按会话失败收口。"""

    from repoharness2.adapters.slime.generate import SlimeBindingError

    sid = "sid-wvs-bad"
    from repoharness2.adapters.slime.generate import GenerationCaptureHook

    wire.registry.register(
        sid,
        GenerationCaptureHook(
            trajectory_id="traj_wvs_bad",
            model_name="m",
            backend_name="sglang",
            backend_version="test",
            renderer_cls_name="r",
            tokenizer_name="tok",
            template_hash="sha256:" + "0" * 64,
        ),
    )
    with pytest.raises(SlimeBindingError) as err:
        await _call(
            wire,
            _wire_payload(
                {
                    "weight_versions": [
                        {"version": "10", "start": 0, "end": 2},
                        {"version": "11", "start": 1, "end": 3},
                    ]
                }
            ),
            sid=sid,
        )
    assert err.value.reason_code == "weight_version_spans_overlap"
    assert not (wire.registry.pending.get(sid) or {})  # 坏轮不得暂存
    assert wire.registry.weight_versions.get(sid) == []  # 版本账不得被坏轮污染


async def test_wire_no_spans_single_version_fallback(wire):
    """旧引擎（未报 spans）：回退单数，provenance=single_version_only。"""

    await _call(wire, _wire_payload())
    staged = _pop_staged(wire)
    assert staged.weight_version_spans is None
    assert staged.weight_version == "11"


# ---------------------------------------------------------------------------
# 4. backfill：全部版本并入 + 结构化 facts 附加属性
# ---------------------------------------------------------------------------


def _mk_tape(world, record_id, output_ids, *, spans=None, weight_version=None):
    from repoharness2.adapters.slime.generate import TurnTape, WeightVersionSpan

    span_objs = (
        tuple(WeightVersionSpan(version=v, start=a, end=b) for v, a, b in spans)
        if spans is not None
        else None
    )
    return TurnTape(
        record_id=record_id,
        turn_index=0,
        prompt_token_count=2,
        response_token_count=len(output_ids),
        output_ids=tuple(output_ids),
        output_log_probs=tuple(-0.1 for _ in output_ids),
        top_p_token_ids=None,
        top_p_token_offsets=None,
        routed_experts_flat=None,
        weight_version=weight_version,
        weight_version_spans=span_objs,
    )


def _mk_leaf(world, response_tokens, loss_mask):
    return world.SS(
        index=0,
        group_index=0,
        prompt="p",
        tokens=[1, 2, *response_tokens],
        response="r",
        response_length=len(loss_mask),
        loss_mask=list(loss_mask),
        status=world.SS.Status.COMPLETED,
        metadata={},
    )


def test_backfill_merges_all_span_versions(world):
    """adv_miles 反例修复：v10+v11 轮的 Sample.weight_versions 必须含两个版本。"""

    from repoharness2.adapters.miles.weight_version_facts import (
        ATTACHED_WEIGHT_VERSION_SPANS_ATTR,
        LeafWeightVersionFacts,
    )
    from repoharness2.adapters.slime.generate import backfill_leaf_sample

    leaf = _mk_leaf(world, [101, 102, 103], [1, 1, 1])
    tape = _mk_tape(
        world,
        "cap_t0",
        [101, 102, 103],
        spans=[("10", 0, 2), ("11", 2, 3)],
        weight_version="11",
    )
    used = backfill_leaf_sample(leaf, [tape])
    assert [t.record_id for t in used] == ["cap_t0"]
    # 旧口径只记 ["11"]（min=11、staleness 低报）；spans 口径记全部区间版本
    assert leaf.weight_versions == ["10", "11"]

    facts = getattr(leaf, ATTACHED_WEIGHT_VERSION_SPANS_ATTR)
    assert isinstance(facts, LeafWeightVersionFacts)
    assert facts.flat_versions == ("10", "11")
    assert facts.turns[0].provenance == "engine_spans"
    assert facts.turns[0].spans == (("10", 0, 2), ("11", 2, 3))
    assert facts.flatten_turn_versions() == ("10", "11")


def test_backfill_mixed_spans_and_single_turns(world):
    """混合链：spans 轮按区间展平、single 轮记单数，逐轮 provenance 显式。"""

    from repoharness2.adapters.miles.weight_version_facts import (
        ATTACHED_WEIGHT_VERSION_SPANS_ATTR,
    )
    from repoharness2.adapters.slime.generate import backfill_leaf_sample

    leaf = _mk_leaf(world, [101, 102, 0, 103], [1, 1, 0, 1])
    tape0 = _mk_tape(
        world, "cap_t0", [101, 102], spans=[("10", 0, 1), ("11", 1, 2)], weight_version="11"
    )
    tape1 = _mk_tape(world, "cap_t1", [103], weight_version="11")
    used = backfill_leaf_sample(leaf, [tape0, tape1])
    assert len(used) == 2
    assert leaf.weight_versions == ["10", "11", "11"]
    facts = getattr(leaf, ATTACHED_WEIGHT_VERSION_SPANS_ATTR)
    assert [t.provenance for t in facts.turns] == ["engine_spans", "single_version_only"]
    assert facts.turns[1].spans is None
    assert facts.turns[1].single_version == "11"
    assert facts.flatten_turn_versions() == ("10", "11", "11")


def test_backfill_no_spans_keeps_legacy_behavior(world):
    """纯单数链：旧行为逐字不变，且不挂附加属性（321 面/旧链零改变）。"""

    from repoharness2.adapters.miles.weight_version_facts import (
        ATTACHED_WEIGHT_VERSION_SPANS_ATTR,
    )
    from repoharness2.adapters.slime.generate import backfill_leaf_sample

    leaf = _mk_leaf(world, [101, 102, 103], [1, 1, 1])
    tape = _mk_tape(world, "cap_t0", [101, 102, 103], weight_version="7")
    backfill_leaf_sample(leaf, [tape])
    assert leaf.weight_versions == ["7"]
    assert not hasattr(leaf, ATTACHED_WEIGHT_VERSION_SPANS_ATTR)


def test_backfill_formal_chain_spans_satisfy_real_version_requirement(world):
    """正式链（require_real_weight_versions）：spans 轮就是真实版本事实，不炸。"""

    from repoharness2.adapters.slime.generate import backfill_leaf_sample

    leaf = _mk_leaf(world, [101, 102, 103], [1, 1, 1])
    tape = _mk_tape(
        world,
        "cap_t0",
        [101, 102, 103],
        spans=[("10", 0, 2), ("11", 2, 3)],
        weight_version="11",
    )
    backfill_leaf_sample(leaf, [tape], require_real_weight_versions=True)
    assert leaf.weight_versions == ["10", "11"]


# ---------------------------------------------------------------------------
# 5. canonicalize：metadata 落点 + fail-closed 三闸 + miles oldest 端到端
# ---------------------------------------------------------------------------


def _attach_facts(world, vend, *, turns, flat):
    from repoharness2.adapters.miles.weight_version_facts import (
        LeafWeightVersionFacts,
        TurnWeightVersionFact,
        attach_leaf_weight_version_facts,
    )

    attach_leaf_weight_version_facts(
        vend,
        LeafWeightVersionFacts(
            turns=tuple(TurnWeightVersionFact(**t) for t in turns),
            flat_versions=tuple(flat),
        ),
    )


def test_canonicalize_spans_to_metadata_and_oldest_fixed(world):
    """端到端反例修复：miles oldest_weight_version 看到 spans 里的真实最旧版本。"""

    vend = world.mk_vendor_sample(versions=("10", "11"))
    _attach_facts(
        world,
        vend,
        turns=[
            dict(
                capture_record_id="cap_t0",
                provenance="engine_spans",
                spans=(("10", 0, 2), ("11", 2, 3)),
                single_version="11",
            )
        ],
        flat=["10", "11"],
    )
    out = world.canonicalize_sample(vend, miles_input_sample=world.mk_miles_input())
    assert out.weight_versions == ["10", "11"]
    # adv_miles 反例的 miles 端断言：单数记账 oldest=11（lag 低报），spans 口径=10
    assert out.oldest_weight_version == 10
    payload = out.metadata["rh2_weight_version_spans"]
    assert payload == [
        {
            "capture_record_id": "cap_t0",
            "provenance": "engine_spans",
            "spans": [
                {"version": "10", "start": 0, "end": 2},
                {"version": "11", "start": 2, "end": 3},
            ],
            "version": "11",
        }
    ]
    # 附加属性消费后不得外挂到 miles 对象
    assert "rh2_weight_version_spans" not in out.__dict__


def test_canonicalize_facts_wrong_type_rejected(world):
    vend = world.mk_vendor_sample(versions=("10", "11"))
    setattr(vend, "rh2_weight_version_spans", [{"version": "10"}])  # 裸结构绕过装配
    with pytest.raises(world.CanonicalizationError, match="weight_version_spans_wrong_type"):
        world.canonicalize_sample(vend, miles_input_sample=world.mk_miles_input())


def test_canonicalize_ledger_mismatch_rejected(world):
    """facts 展平与 Sample.weight_versions 两本账不一致 = 记账损坏，拒绝。

    这正是低报形态（记账列表少了 v10）在转换边界的红证明。"""

    vend = world.mk_vendor_sample(versions=("11",))  # 记账只有 v11（低报）
    _attach_facts(
        world,
        vend,
        turns=[
            dict(
                capture_record_id="cap_t0",
                provenance="engine_spans",
                spans=(("10", 0, 2), ("11", 2, 3)),  # 引擎证据是 v10+v11
                single_version="11",
            )
        ],
        flat=["10", "11"],
    )
    with pytest.raises(world.CanonicalizationError, match="weight_version_spans_ledger_mismatch"):
        world.canonicalize_sample(vend, miles_input_sample=world.mk_miles_input())


def test_canonicalize_duplicate_metadata_source_rejected(world):
    vend = world.mk_vendor_sample(versions=("10", "11"))
    vend.metadata["rh2_weight_version_spans"] = []  # 输入侧不该有该键
    _attach_facts(
        world,
        vend,
        turns=[
            dict(
                capture_record_id="cap_t0",
                provenance="engine_spans",
                spans=(("10", 0, 2), ("11", 2, 3)),
                single_version="11",
            )
        ],
        flat=["10", "11"],
    )
    with pytest.raises(world.CanonicalizationError, match="weight_version_spans_duplicate_source"):
        world.canonicalize_sample(vend, miles_input_sample=world.mk_miles_input())


def test_canonicalize_without_facts_unchanged(world):
    """无 spans 链：canonicalize 行为逐字不变（无 metadata 键）。"""

    out = world.canonicalize_sample(
        world.mk_vendor_sample(versions=("7",)),
        miles_input_sample=world.mk_miles_input(),
    )
    assert out.weight_versions == ["7"]
    assert "rh2_weight_version_spans" not in (out.metadata or {})


# ---------------------------------------------------------------------------
# 6. miles stock `update_from_meta_info`（vendor refresh 复核 P2 #1 miles 半场，
#    patch 0009）：assert 改真异常 + 与 rh2 parser 同款结构不变式。
#    integration_base：严格校验只存在于 integration tree（pin base 的
#    update_from_meta_info 只读单数键，无 spans 语义可测）。
#    诚实边界：stock 路径拿不到本次调用的生成 token 数（函数签名只有
#    args/meta_info），rh2 parser 的 end==generated 覆盖检查不在此处——结构
#    不变式（null/空表/类型/首段 0/连续/相邻版本/零输出唯一空段/单数一致）
#    全部对齐。
# ---------------------------------------------------------------------------


def _stock_sample(world):
    return world.MS()


def _stock_args():
    return SimpleNamespace(sglang_speculative_algorithm=None)


def _stock_meta(**over):
    meta = {"finish_reason": {"type": "stop"}}
    meta.update(over)
    return meta


@pytest.mark.integration_base
def test_stock_update_valid_spans_books_all_versions(world):
    """正例：跨更新 turn 的全部区间版本入账（adv_miles 反例 miles 侧修复）。"""

    s = _stock_sample(world)
    s.update_from_meta_info(
        _stock_args(),
        _stock_meta(
            weight_versions=[
                {"version": "10", "start": 0, "end": 300},
                {"version": "11", "start": 300, "end": 500},
            ],
            weight_version="11",
        ),
    )
    assert s.weight_versions == ["10", "11"]
    assert s.status == world.MS.Status.COMPLETED


@pytest.mark.integration_base
def test_stock_update_zero_output_span_ok(world):
    """正例：零输出请求的唯一空区间 [v,0,0)（writer 合同形态）入账。"""

    s = _stock_sample(world)
    s.update_from_meta_info(
        _stock_args(),
        _stock_meta(weight_versions=[{"version": "9", "start": 0, "end": 0}], weight_version="9"),
    )
    assert s.weight_versions == ["9"]


@pytest.mark.integration_base
def test_stock_update_missing_key_falls_back_scalar(world):
    """正例（旧引擎链不变）：键**缺失**才允许回退单数——与 null 判然两分。"""

    s = _stock_sample(world)
    s.update_from_meta_info(_stock_args(), _stock_meta(weight_version="7"))
    assert s.weight_versions == ["7"]


@pytest.mark.integration_base
def test_stock_update_neither_key_books_nothing(world):
    s = _stock_sample(world)
    s.update_from_meta_info(_stock_args(), _stock_meta())
    assert s.weight_versions == []


@pytest.mark.parametrize(
    ("label", "meta_over"),
    [
        # null ≠ 键缺失：显式 null 是账目损坏，禁止洗成"旧引擎"回退单数
        ("null", {"weight_versions": None, "weight_version": "10"}),
        # 空 list 同理（旧代码 walrus 真值判断会静默落进单数回退分支）
        ("empty_list", {"weight_versions": [], "weight_version": "10"}),
        ("not_a_list", {"weight_versions": "10", "weight_version": "10"}),
        ("item_not_dict", {"weight_versions": [["10", 0, 3]], "weight_version": "10"}),
        ("item_missing_keys", {"weight_versions": [{"version": "10", "start": 0}], "weight_version": "10"}),
        # version 必须字符串（pin 的 writer 显式 str 化；int 不做宽容转换）
        ("int_version", {"weight_versions": [{"version": 7, "start": 0, "end": 3}], "weight_version": "7"}),
        ("empty_version", {"weight_versions": [{"version": "", "start": 0, "end": 3}], "weight_version": ""}),
        ("bool_bound", {"weight_versions": [{"version": "10", "start": True, "end": 3}], "weight_version": "10"}),
        ("negative_bound", {"weight_versions": [{"version": "10", "start": 0, "end": -3}], "weight_version": "10"}),
        # 以下两条是旧 assert 覆盖的两个不变式——负例证明现在是真异常
        ("first_start_nonzero", {"weight_versions": [{"version": "10", "start": 1, "end": 3}], "weight_version": "10"}),
        (
            "gap",
            {
                "weight_versions": [
                    {"version": "10", "start": 0, "end": 1},
                    {"version": "11", "start": 2, "end": 3},
                ],
                "weight_version": "11",
            },
        ),
        (
            "overlap",
            {
                "weight_versions": [
                    {"version": "10", "start": 0, "end": 2},
                    {"version": "11", "start": 1, "end": 3},
                ],
                "weight_version": "11",
            },
        ),
        (
            "adjacent_same_version",
            {
                "weight_versions": [
                    {"version": "10", "start": 0, "end": 2},
                    {"version": "10", "start": 2, "end": 3},
                ],
                "weight_version": "10",
            },
        ),
        # 空区间只允许零输出的唯一 [v,0,0) 形态；混在多段里 = 损坏
        (
            "empty_span_mixed",
            {
                "weight_versions": [
                    {"version": "10", "start": 0, "end": 0},
                    {"version": "11", "start": 0, "end": 3},
                ],
                "weight_version": "11",
            },
        ),
        ("scalar_missing", {"weight_versions": [{"version": "10", "start": 0, "end": 3}]}),
        (
            "scalar_mismatch",
            {"weight_versions": [{"version": "10", "start": 0, "end": 3}], "weight_version": "11"},
        ),
    ],
)
@pytest.mark.integration_base
def test_stock_update_bad_spans_raise_value_error(world, label, meta_over):
    """负例逐条：ValueError（真异常，python -O 下不消失；AssertionError 不算数），
    且版本账不得被坏轮污染（校验先于任何 extend）。"""

    s = _stock_sample(world)
    with pytest.raises(ValueError, match="malformed weight_versions spans"):
        s.update_from_meta_info(_stock_args(), _stock_meta(**meta_over))
    assert s.weight_versions == []
