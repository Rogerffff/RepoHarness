"""W4 行既有项：一次性 CPU materialization benchmark（只取数，不建监测、不设阈值）。

量的是 rh2 侧一条叶链在进入 miles 之前的 CPU 物化开销（真实 RH2 shape、真实实现）：

    parse_turn_sampling_support   每轮引擎 sampling-mask 响应解析校验（sampled∈support 等）
    assemble_leaf_sampling_mask   跨轮装配成叶链 CSR（run<->turn 锚定 + 观察位单例补齐）
    canonicalize_sample           slime→miles 构造（mask → RolloutSamplingMask 一等字段、spans → metadata、
                                  两本版本账互检）
    RolloutSamplingMask(ids, offsets)  miles 一等字段构造：CSR list → torch int32/int64（训练 wire dtype）+
                                  offsets 不变式检查（canonicalize 内部就是这一步，这里单独再量一次）

默认形状（可用环境变量放大，供报告取数）：
    RH2_W4_BENCH_RESPONSE_TOKENS   叶链 response token 总数（默认 4096）
    RH2_W4_BENCH_TURNS             轮数（默认 8；每轮采样段后跟一段观察 token）
    RH2_W4_BENCH_TOPK              每个采样 token 的支持集大小（默认 20）
    RH2_W4_BENCH_REPEATS           重复次数取中位数（默认 3）
用 `-s` 运行可看到打印的耗时表。断言只检查产物合法（长度/offsets/两本账）。
"""

from __future__ import annotations

import os
import statistics
import time

import pytest

pytestmark = pytest.mark.integration_base


def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name) or default)


def _build_shape(world, sma, *, response_tokens: int, turns: int, topk: int):
    """轮 k：采样段 S_k（mask=1）+ 观察段 O_k（mask=0，工具结果），token id 全部唯一且落在 int32。"""

    per_turn = max(response_tokens // turns, topk + 2)
    sampled_len = max(int(per_turn * 0.7), 1)
    observed_len = per_turn - sampled_len
    response: list[int] = []
    loss_mask: list[int] = []
    turn_supports = []
    metas = []
    next_id = 1000
    for k in range(turns):
        out_ids = list(range(next_id, next_id + sampled_len))
        next_id += sampled_len
        supports = []
        for tok in out_ids:
            # 支持集：该 token + topk-1 个其它 id（引擎 force-include 语义）
            extra = list(range(next_id, next_id + topk - 1))
            supports.append([tok] + extra)
        metas.append({"output_token_sampling_mask": supports, "output_token_sampling_logprobs": [-0.5] * sampled_len,
                      "finish_reason": {"type": "stop"}})
        turn_supports.append((out_ids, metas[-1]))
        response.extend(out_ids)
        loss_mask.extend([1] * sampled_len)
        obs = list(range(next_id, next_id + observed_len))
        next_id += observed_len
        response.extend(obs)
        loss_mask.extend([0] * observed_len)
    return response, loss_mask, turn_supports


def _spans_facts(world, versions_per_turn: list[str]):
    from repoharness2.adapters.miles.weight_version_facts import LeafWeightVersionFacts, TurnWeightVersionFact

    turns = tuple(
        TurnWeightVersionFact(capture_record_id=f"cap-{i}", provenance="single_version_only", spans=None, single_version=v)
        for i, v in enumerate(versions_per_turn)
    )
    return LeafWeightVersionFacts(turns=turns, flat_versions=tuple(versions_per_turn))


def _timed(fn, repeats: int):
    samples = []
    result = None
    for _ in range(repeats):
        t0 = time.perf_counter()
        result = fn()
        samples.append(time.perf_counter() - t0)
    return result, statistics.median(samples)


def test_cpu_materialization_benchmark_numbers(world):
    from repoharness2.adapters.miles import sampling_mask_assembly as sma
    from repoharness2.adapters.miles.weight_version_facts import attach_leaf_weight_version_facts

    response_tokens = _env_int("RH2_W4_BENCH_RESPONSE_TOKENS", 4096)
    turns = _env_int("RH2_W4_BENCH_TURNS", 8)
    topk = _env_int("RH2_W4_BENCH_TOPK", 20)
    repeats = _env_int("RH2_W4_BENCH_REPEATS", 3)

    response, loss_mask, turn_inputs = _build_shape(world, sma, response_tokens=response_tokens, turns=turns, topk=topk)
    n_tokens = len(response)

    def parse():
        return [sma.parse_turn_sampling_support(out_ids, meta)[0] for out_ids, meta in turn_inputs]

    turn_supports, t_parse = _timed(parse, repeats)

    assembled, t_assemble = _timed(lambda: sma.assemble_leaf_sampling_mask(response, loss_mask, turn_supports), repeats)
    assert assembled.response_token_count == n_tokens and assembled.offsets[-1] == len(assembled.ids)

    versions = [str(5 + (k % 2)) for k in range(turns)]  # 跨 publish：轮交替 v5/v6

    def make_vendor():
        s = world.mk_vendor_sample(
            tokens=list(range(100)) + list(response), response="x", response_length=n_tokens, loss_mask=list(loss_mask),
            rollout_log_probs=[-0.1] * n_tokens, versions=tuple(versions),
        )
        sma.attach_assembled_mask(s, assembled)
        attach_leaf_weight_version_facts(s, _spans_facts(world, versions))
        return s

    def canonicalize():
        return world.canonicalize_sample(make_vendor(), miles_input_sample=world.mk_miles_input(), rollout_top_p=0.8)

    out, t_canon = _timed(canonicalize, repeats)
    assert out.response_length == n_tokens and len(out.rollout_sampling_mask) == n_tokens
    assert out.metadata["rh2_weight_version_spans"] and out.weight_versions == versions

    from miles.utils.sampling_mask import RolloutSamplingMask

    ids_list, offsets_list = list(assembled.ids), list(assembled.offsets)
    mask, t_tensor = _timed(lambda: RolloutSamplingMask(ids=ids_list, offsets=offsets_list), repeats)
    ids, offsets = mask._as_tensors()
    assert int(offsets[-1]) == len(assembled.ids) and ids.numel() == len(assembled.ids)

    total_ids = len(assembled.ids)
    table = [
        ("parse_turn_sampling_support (all turns)", t_parse),
        ("assemble_leaf_sampling_mask", t_assemble),
        ("canonicalize_sample (mask+spans, incl. vendor sample build)", t_canon),
        ("RolloutSamplingMask(ids, offsets) list->tensor (already inside canonicalize)", t_tensor),
    ]
    print(
        f"\n[W4 CPU materialization benchmark] response_tokens={n_tokens} turns={turns} topk={topk} "
        f"support_ids={total_ids} sampled={assembled.sampled_token_count} singleton={assembled.singleton_token_count} "
        f"repeats={repeats} (median)"
    )
    for name, secs in table:
        print(f"  {name:<64s} {secs * 1e3:9.2f} ms   ({secs / n_tokens * 1e6:7.2f} us/token)")
    print(f"  {'total per leaf (parse + assemble + canonicalize)':<64s} {sum(t for _, t in table[:3]) * 1e3:9.2f} ms")
