"""E3（第六组 I23）：routing tape 紧凑表示在**真实包装链**上的逐位等价。

`return_sampling_mask=True` 的引擎会话，经真实 capture wire -> `record_turn` commit -> backfill ->
`project_group_with_sampler_support` -> `project_from_slime` -> canonicalize：逐轮工件、分支 routing
工件、miles 侧 ndarray 都与按定义打包的期望逐位一致；mask 事实与 B2 验收相同（证明包装链确实在路径上）。
Codex E3 计划复核 §3.1 要求的真实包装链对照。复用 `test_b2_mask_chain` 的 fake 引擎 / wire adapter /
任务与评分替身，只给每轮引擎应答加上 base64 routing tape。
"""

from __future__ import annotations

import base64
import hashlib
import struct
from argparse import Namespace
from types import SimpleNamespace

import pytest
import test_b2_mask_chain as b2

pytestmark = pytest.mark.integration_base  # mask 链路要求 integration base（同 B2）；原始 pin 的 lane A 跳过

LAYERS, TOPK = 2, 2


def _values(rows: int) -> list[int]:
    return [(i * 13 + 7) % 128 for i in range(rows * LAYERS * TOPK)]


def _packed(rows: int) -> bytes:
    return struct.pack(f"<{rows * LAYERS * TOPK}i", *_values(rows))


def _sha(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _rows(prompt_ids, meta) -> int:
    return len(prompt_ids) - 1 + len(meta["output_token_logprobs"])  # SGLang 对齐律


def _script_with_routing():
    script = []
    for prompt_ids, payload in b2.TURN_SCRIPT:
        meta = dict(payload["meta_info"])
        meta["routed_experts"] = base64.b64encode(_packed(_rows(prompt_ids, meta))).decode("ascii")
        script.append((prompt_ids, {**payload, "meta_info": meta}))
    return script


async def test_e3_routing_tape_survives_the_real_mask_chain_bit_for_bit(world, monkeypatch):
    world.install_sglang_stub()
    import numpy
    from miles.rollout.base_types import GenerateFnInput
    from miles.rollout.inference_rollout.compatibility import load_generate_function

    from repoharness2.adapters.slime import RolloutOrchestrator, SlimeBindingConfig
    from repoharness2.adapters.slime import capture_wire as cw

    script = _script_with_routing()
    monkeypatch.setattr(b2, "TURN_SCRIPT", script)  # wire adapter 的 run_all_turns 读模块常量
    registry = cw.CaptureRegistry()
    cw.install_capture_wire(registry)
    engine = b2._FakeEngine()
    engine.responses = [payload for _prompt, payload in script]
    monkeypatch.setattr(cw, "aiohttp", b2._FakeAiohttp(engine))

    config = SlimeBindingConfig(
        model_name="Qwen/Qwen3-30B-A3B",
        backend_version="0.5.9",
        renderer_cls_name="Qwen3Renderer",
        expected_renderer_cls_name="Qwen3Renderer",
        tokenizer_name="Qwen/Qwen3-30B-A3B",
        template_hash=b2.SHA_TEMPLATE,
        adapter_url="http://127.0.0.1:1",
        harness_name="mock_harness",
        policy_version="7",
        expect_moe_routing=True,
        moe_num_layers=LAYERS,
        moe_router_topk=TOPK,
    )
    holder: dict = {}

    def adapter_factory(hook, session_defaults):
        assert session_defaults.get("return_routed_experts") is True
        assert session_defaults.get("return_sampling_mask") is True
        adapter = b2._make_mask_wire_adapter(registry, hook, session_defaults)
        holder["adapter"], holder["hook"] = adapter, hook
        return adapter

    class Driver:
        name = "mock_harness"

        async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
            await holder["adapter"].run_all_turns()
            return 0

    async def grading_submit(*, trajectory_id, workspace, spec, **kw):
        return b2._make_grading_report(trajectory_id, spec.task_id)

    orchestrator = RolloutOrchestrator(
        config=config,
        task_resolver=b2._make_task(),
        adapter_factory=adapter_factory,
        harness_driver=Driver(),
        grading_submit=grading_submit,
        docker=b2._make_fake_docker(),
        session_poison_check=registry.poison.is_poisoned,
        capture_boundary_check=registry.assert_session_clean,
    )
    fn = load_generate_function("repoharness2.adapters.miles.generate_fn.Rh2MilesGenerateFn")
    args = Namespace(rh2_orchestrator=orchestrator, rollout_top_p=0.8, rh2_engine_sampling_mask=True)
    gi = GenerateFnInput(
        state=SimpleNamespace(args=args),
        sample=world.mk_miles_input(index=0, group_index=0),
        sampling_params={"temperature": 0.7, "top_p": 0.8, "top_k": 32, "max_new_tokens": 512},
        evaluation=False,
    )

    out = await fn(gi)
    (delivered,) = out.samples
    hook = holder["hook"]
    assert registry.stats["committed"] == 3 and len(hook.records) == 3

    # ① 逐轮：store 与 TurnTape 引用同一个 bytes；字节 = 按定义打包的期望；记录里的引用与之一致
    for (prompt_ids, payload), record, tape in zip(script, hook.records, hook.tapes, strict=True):
        expected = _packed(_rows(prompt_ids, payload["meta_info"]))
        stored = hook.artifact_store[f"{record.record_id}_routing"]
        assert tape.routed_experts_le_int32 is stored and stored == expected
        assert (record.routed_experts_ref.sha256, record.routed_experts_ref.byte_size) == (_sha(expected), len(expected))
        assert record.capture_status == "complete"

    # ② 叶链：最后一轮 10 行 = len(tokens) - 1，无裁剪；分支 routing 工件 = 最后一轮的字节
    leaf_rows = len(b2.LEAF_TOKENS) - 1
    last_expected = _packed(leaf_rows)
    audit = orchestrator.audits[0]
    projection = audit.finalized.projection
    (branch,) = projection.branches
    assert branch.routing.alignment == "sglang_prompt_minus1_plus_gen"
    assert (branch.routing.num_rows, branch.routing.num_layers, branch.routing.router_topk) == (leaf_rows, LAYERS, TOPK)
    assert (branch.routing.tensor_ref.sha256, branch.routing.tensor_ref.byte_size) == (_sha(last_expected), len(last_expected))
    assert hook.artifact_store[branch.routing.tensor_ref.ref_id] == last_expected
    assert "rh2_routing_backfill_trimmed_prefix_rows" not in (delivered.metadata or {})

    # ③ 包装链确实在路径上：sampler-support 事实与 B2 验收一致
    assert branch.sampling_mask.mask_kind == "sampler_support_token_ids"
    assert branch.sampling_mask.offsets_len == 8 and branch.sampling_mask.kept_token_count == 12
    mask_ids, mask_offsets = delivered.rollout_sampling_mask._as_tensors()
    assert mask_ids.tolist() == b2.EXPECTED_MASK_IDS and mask_offsets.tolist() == b2.EXPECTED_MASK_OFFSETS
    assert branch.capture_record_refs == [hook.records[0].record_id, hook.records[2].record_id]

    # ④ miles 侧：canonicalize 的 ndarray 独立、连续、int32，字节 = 最后一轮
    arr = delivered.rollout_routed_experts
    assert isinstance(arr, numpy.ndarray) and arr.dtype == numpy.int32 and arr.flags.c_contiguous
    assert arr.shape == (leaf_rows, LAYERS, TOPK) and arr.tobytes() == last_expected
    arr[0, 0, 0] = -1  # 独立副本：不写回捕获工件
    assert hook.artifact_store[branch.routing.tensor_ref.ref_id] == last_expected
