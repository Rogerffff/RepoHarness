"""W9：faithful DIS custom loss 的 CP（context parallel）>1 切分语义。

对拍口径：**CP=1 全量计算是权威**（它本身已在 test_faithful_dis_loss.py 与
标量权威 `faithful_dis_loss_by_execution` 对拍过）。本文件只证明"CP=2 把
同一批数据按 miles zigzag 规则切成两个 rank 后,逐 token 分子/梯度拼回来
等于 CP=1 全量,计数与零贡献旗标聚合后等于 CP=1"。

切分规则同源：测试侧用 miles 公开的
`cp_utils.get_logits_and_tokens_offset_with_cp(..., cp_rank=, cp_size=)`
（显式传 rank/size,不依赖全局状态）切 behavior/advantage 列,用
`cp_utils.slice_with_cp(parallel_state=...)` 切 tokens/logits（= get_batch
的做法）,用 `cp_utils.assemble_log_prob_from_cp` 把各 rank 的分子拼回。
被测函数内部走的是 miles 自己的 `get_local_response_loss_masks` /
`_iter_response_chunks` 路径——两边都是同一条 offset 规则的消费者。

两种模拟形态：

1. **单进程 mock ParallelState**（cp.size=2,cp.rank∈{0,1},group=None）：
   逐 rank 顺序调用被测函数,CP 组内 all_reduce 的 seam
   `_cp_all_reduce_sum` 用 monkeypatch 替换（第一遍记录各 rank 本地计数,
   第二遍回填组内总数）——覆盖切分对齐、分子/梯度守恒、断言、计数、
   旗标、fail-closed 负例。
2. **两进程 CPU gloo 组**（真实 `dist.all_reduce`、真实 `GroupInfo.group`）：
   spawn 两个子进程各扮演一个 CP rank,跑完整被测函数（含真实 collective
   与 miles CP 感知 reducer）,结果写文件回父进程对拍;另跑一个跨 rank
   边界 target∉support 负例,两 rank 都必须炸（断言在 collective 之前,
   不会有单边挂起）。

真机 CP=2 端到端（ring attention 下 logits 真由 CP 切分产生）归 GPU spike
C 包,本文件不宣称覆盖。

样本形状（thd,VOCAB=17;三样本各自成 execution）：
    s0: total 12 / resp 10（prompt 2）→ chunk 3：rank0 拥有 response 位
        {0,1,8,9},rank1 拥有 {2..7}（两处跨 rank 边界:1|2 与 7|8）
    s1: total 7 / resp 4（prompt 3）→ chunk 2：rank0 **空分片**,rank1 全有
    s2: total 9 / resp 6（prompt 3）→ chunk 3：rank0 {0},rank1 {1..5}
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.integration_base

VOCAB = 17
CP_SIZE = 2

# ---------------------------------------------------------------------------
# 固定数据
# ---------------------------------------------------------------------------

# tokens = prompt + response;支持集逐 response 位（必含 target;单例 = 观察位/退化位）
_TOKENS = [
    [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
    [1, 2, 3, 8, 9, 10, 11],
    [1, 2, 3, 5, 6, 7, 8, 9, 10],
]
_RESP_LENS = [10, 4, 6]
_SUPPORTS = [
    [[4, 9, 10], [5, 2], [6, 1, 14], [7], [8, 3], [9, 15], [10, 11], [11, 2, 3], [12], [13, 16]],
    [[8, 3], [9], [10, 11, 12], [11, 4]],
    [[5, 1], [6], [7, 8], [8, 9, 10], [9, 2], [10, 3]],
]
_LOSS_MASKS = [
    [1, 1, 1, 0, 1, 1, 1, 1, 0, 1],
    [1, 1, 1, 1],
    [1, 0, 1, 1, 1, 1],
]
_ADV = [
    [1.0, -0.5, 2.0, 0.7, 0.3, -1.2, 0.9, 1.1, -0.4, 0.6],
    [0.3, -1.2, 0.9, 0.4],
    [-0.8, 0.5, 1.3, -0.2, 0.75, 0.15],
]
# 目标 log-ratio：信任区间 (0.2,4.0) 开区间 ⇔ log 界约 (-1.609,1.386)
_TARGET_LOG_RATIO = [
    [0.0, 1.5, 0.3, 0.3, -2.0, 0.5, -1.0, 2.0, 0.2, -0.3],
    [0.5, -1.0, 2.0, 0.1],
    [0.4, 0.2, -1.7, 1.0, 0.05, 1.5],
]
# 各样本自成 execution：rollout_mask_sums = 各自 provenance 总数;
# 按上面 log-ratio 与 mask 逐位判定的 (accepted, provenance)：s0 (5,8)、s1 (3,4)、s2 (3,5)
_ROLLOUT_MASK_SUMS = [8.0, 4.0, 5.0]

# 期望的本 rank response 位集合（人工按 zigzag 规则算出,与 miles helper 对账）
_EXPECTED_LOCAL_POSITIONS = {
    0: [[0, 1, 8, 9], [], [0]],
    1: [[2, 3, 4, 5, 6, 7], [0, 1, 2, 3], [1, 2, 3, 4, 5]],
}


def _csr(supports):
    ids: list[int] = []
    offsets = [0]
    for support in supports:
        ids.extend(support)
        offsets.append(len(ids))
    return ids, offsets


def _mk_args(**over):
    base = dict(
        qkv_format="thd",
        rollout_temperature=1.0,
        true_on_policy_mode=True,
        log_probs_chunk_size=-1,
        allgather_cp=False,
        rollout_top_p=0.8,
        rollout_top_k=VOCAB,
        vocab_size=VOCAB,
        bf16=False,
        fp16=False,
    )
    base.update(over)
    return Namespace(**base)


def _boom_reducer(_t):
    raise AssertionError("fail-closed 路径不应触达 sum_of_sample_mean")


def _boom_all_reduce(_t, _cp):
    raise AssertionError("fail-closed 路径不应触达 CP 组内 all_reduce")


def _mk_case(torch, *, seed=23):
    """全量（CP=1 布局）batch + 全量 logits（尚未填 behavior 列）。"""

    g = torch.Generator().manual_seed(seed)
    tokens = [torch.tensor(t, dtype=torch.long) for t in _TOKENS]
    total_lengths = [len(t) for t in _TOKENS]
    logits = torch.randn(1, sum(total_lengths), VOCAB, generator=g, dtype=torch.float64)
    ids_offsets = [_csr(s) for s in _SUPPORTS]
    batch = {
        "unconcat_tokens": tokens,
        "total_lengths": total_lengths,
        "response_lengths": list(_RESP_LENS),
        "loss_masks": [torch.tensor(m, dtype=torch.long) for m in _LOSS_MASKS],
        "advantages": [torch.tensor(a, dtype=torch.float64) for a in _ADV],
        "rollout_sampling_mask_ids": [io[0] for io in ids_offsets],
        "rollout_sampling_mask_offsets": [io[1] for io in ids_offsets],
        "rollout_mask_sums": torch.tensor(_ROLLOUT_MASK_SUMS, dtype=torch.float32),
    }
    return batch, logits


def _fill_behavior_from_current(torch, args, batch, logits):
    """behavior = current − 目标 log-ratio（CP=1 全量路径算 current;调用前须处于 CP=1 状态）。"""

    from miles.backends.training_utils.loss_hub.logit_processors import get_log_probs_and_entropy
    from miles.backends.training_utils.sampling_mask import get_rollout_sampling_masks

    with torch.no_grad():
        current = get_log_probs_and_entropy(
            logits,
            args=args,
            unconcat_tokens=batch["unconcat_tokens"],
            total_lengths=batch["total_lengths"],
            response_lengths=batch["response_lengths"],
            with_entropy=False,
            rollout_sampling_mask=get_rollout_sampling_masks(batch),
        )["log_probs"]
    targets = [torch.tensor(t, dtype=torch.float64) for t in _TARGET_LOG_RATIO]
    batch["rollout_log_probs"] = [c - t for c, t in zip(current, targets, strict=True)]
    return [c.clone() for c in current]


# ---------------------------------------------------------------------------
# 切分工具（测试侧,与 miles helper 同源但显式传 rank/size）
# ---------------------------------------------------------------------------


def _local_response_slice(torch, values, total, resp, cp_rank, cp_size):
    """本 rank 拥有的 response 位切片（镜像 cp_utils.slice_log_prob_with_cp,不读全局状态）。"""

    from miles.backends.training_utils.cp_utils import get_logits_and_tokens_offset_with_cp

    prompt = total - resp
    _, _, logits_offset, _ = get_logits_and_tokens_offset_with_cp(
        total, resp, "thd", None, cp_rank=cp_rank, cp_size=cp_size
    )
    parts = [values[lo - (prompt - 1) : hi - (prompt - 1)] for lo, hi in logits_offset]
    return torch.cat(parts, dim=0)


def _local_positions(torch, total, resp, cp_rank, cp_size):
    return _local_response_slice(torch, torch.arange(resp), total, resp, cp_rank, cp_size).tolist()


def _zigzag_full_rows(total, cp_rank, cp_size):
    """本 rank 的本地 logits 块每一行对应全量样本的哪一行（pad 行记 -1）。"""

    chunk = (total + 2 * cp_size - 1) // (2 * cp_size)
    rows = []
    for k in (cp_rank, 2 * cp_size - 1 - cp_rank):
        for r in range(k * chunk, (k + 1) * chunk):
            rows.append(r if r < total else -1)
    return rows


def _rank_inputs(torch, case, cp_rank, cp_size):
    """从全量 case 构造 rank 视角的 (batch, logits_local)：

    - logits/tokens 用 miles `slice_with_cp`（get_batch 同款）按 zigzag 切+拼；
    - rollout_log_probs/advantages 用 offset 规则切成本 rank 分片
      （= get_rollout_data / compute_advantages 到达 loss 时的形态）；
    - loss_masks、sampling-mask CSR、unconcat_tokens、rollout_mask_sums 保持全量。
    """

    from miles.backends.training_utils.cp_utils import slice_with_cp

    full_batch, full_logits = case["batch"], case["logits"]
    state = SimpleNamespace(cp=SimpleNamespace(rank=cp_rank, size=cp_size))
    totals = full_batch["total_lengths"]
    resps = full_batch["response_lengths"]
    logit_parts, token_parts = [], []
    start = 0
    for t, total in zip(full_batch["unconcat_tokens"], totals, strict=True):
        logit_parts.append(slice_with_cp(full_logits[0, start : start + total], 0.0, "thd", parallel_state=state))
        token_parts.append(slice_with_cp(t, 0, "thd", parallel_state=state))
        start += total
    logits_local = torch.cat(logit_parts, dim=0).unsqueeze(0).clone()
    batch = dict(full_batch)
    batch["tokens"] = torch.cat(token_parts, dim=0).unsqueeze(0)
    for key in ("rollout_log_probs", "advantages"):
        batch[key] = [
            _local_response_slice(torch, v, total, resp, cp_rank, cp_size).clone()
            for v, total, resp in zip(full_batch[key], totals, resps, strict=True)
        ]
    return batch, logits_local


def _mk_reducer(torch, batch):
    """真 reducer：miles dispatcher 同款构造（读全局 ParallelState,CP>1 时自行切 loss_mask）。"""

    from miles.backends.training_utils.cp_utils import get_sum_of_sample_mean

    return get_sum_of_sample_mean(
        list(batch["total_lengths"]),
        list(batch["response_lengths"]),
        batch["loss_masks"],
        False,
        "thd",
        batch.get("max_seq_lens", None),
        denominators=batch.get("rollout_mask_sums", None),
    )


def _run_capturing(module, torch, args, batch, logits):
    """跑被测函数并捕获交给 reducer 的逐 token 分子;返回 (loss, metrics, numerator_flat)。"""

    real = _mk_reducer(torch, batch)
    captured = {}

    def reducer(x):
        captured["numerator"] = x.detach().clone()
        return real(x)

    loss, metrics = module.faithful_dis_loss_function(args, batch, logits, reducer)
    return loss, metrics, captured["numerator"]


def _reassemble_grad(torch, case, grads_by_rank, cp_size):
    """各 rank 本地 logits 梯度块 → 全量 [T, V]（pad 行必须精确为零）。"""

    totals = case["batch"]["total_lengths"]
    full = torch.zeros(sum(totals), VOCAB, dtype=torch.float64)
    for cp_rank in range(cp_size):
        grad = grads_by_rank[cp_rank][0]
        off_local = 0
        off_full = 0
        for total in totals:
            rows = _zigzag_full_rows(total, cp_rank, cp_size)
            block = grad[off_local : off_local + len(rows)]
            for j, r in enumerate(rows):
                if r < 0:
                    assert bool((block[j] == 0.0).all()), "pad 行不得有梯度"
                else:
                    full[off_full + r] = block[j]
            off_local += len(rows)
            off_full += total
        assert off_local == grad.size(0)
    return full


# ---------------------------------------------------------------------------
# fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def dis(world):
    """被测模块 + 可切换的 ParallelState（cp 可指定 rank/size/group 或整体置 None）。"""

    import torch

    from miles.backends.training_utils.parallel import ParallelState, set_parallel_state
    from miles.utils.ft_utils.process_group_utils import GroupInfo

    from repoharness2.adapters.miles import faithful_dis_loss as module

    def trivial() -> GroupInfo:
        return GroupInfo(rank=0, size=1, group=None)

    def mk_state(cp_size: int = 1, cp_rank: int = 0, *, cp=...):
        cp_info = GroupInfo(rank=cp_rank, size=cp_size, group=None) if cp is ... else cp
        state = ParallelState(
            intra_dp=trivial(),
            intra_dp_cp=trivial(),
            cp=cp_info,
            tp=trivial(),
            pp=trivial(),
            ep=trivial(),
            etp=trivial(),
            indep_dp=trivial(),
            is_pp_last_stage=True,
        )
        set_parallel_state(state)
        return state

    mk_state()
    yield SimpleNamespace(module=module, torch=torch, mk_state=mk_state, GroupInfo=GroupInfo)
    mk_state()  # 复位为 CP=1,不污染同模块其它测试


@pytest.fixture()
def case(dis):
    """CP=1 全量 case（behavior 已填）+ CP=1 权威结果（loss/metrics/分子/梯度）。"""

    torch = dis.torch
    args = _mk_args()
    dis.mk_state(cp_size=1)
    batch, logits_data = _mk_case(torch)
    current = _fill_behavior_from_current(torch, args, batch, logits_data)
    logits = logits_data.clone().requires_grad_(True)
    loss, metrics, numerator = _run_capturing(dis.module, torch, args, batch, logits)
    loss.backward()
    baseline = SimpleNamespace(
        loss=loss.detach().clone(),
        metrics={k: v.detach().clone() for k, v in metrics.items()},
        numerators=list(numerator.split(batch["response_lengths"], dim=0)),
        grad=logits.grad[0].detach().clone(),
        current=current,
    )
    return {"batch": batch, "logits": logits_data, "args": args, "baseline": baseline}


class _FakeAllReduce:
    """mock 形态的 CP 组内归约 seam：pass 1 记录本地计数;pass 2 回填组内总数。"""

    def __init__(self, torch):
        self.torch = torch
        self.local = {}
        self.group_total = None
        self.calls = []

    def __call__(self, tensor, cp):
        self.calls.append(cp.rank)
        if self.group_total is None:
            self.local[cp.rank] = tensor.detach().clone()
            return tensor  # pass 1：不归约（旗标此时按本地计数,测试不断言它）
        assert self.torch.equal(tensor, self.local[cp.rank]), "第二遍本地计数必须与第一遍逐位一致"
        tensor.copy_(self.group_total)
        return tensor

    def finish_pass_one(self):
        assert set(self.local) == set(range(CP_SIZE))
        self.group_total = sum(self.local.values())


def _run_cp2_ranks(dis, case, monkeypatch, *, batch_override=None, event_dirs=None):
    """两遍跑完 rank0/rank1（mock 状态）;返回 {rank: (loss, metrics, numerator, grad)} 与 fake。"""

    torch = dis.torch
    fake = _FakeAllReduce(torch)
    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", fake)
    results = {}
    for pass_no in (1, 2):
        for cp_rank in range(CP_SIZE):
            dis.mk_state(cp_size=CP_SIZE, cp_rank=cp_rank)
            batch, logits_local = _rank_inputs(torch, case, cp_rank, CP_SIZE)
            if batch_override is not None:
                batch_override(batch)
            if event_dirs is not None:
                monkeypatch.setenv("MILES_RH2_EVENT_DIR", str(event_dirs[cp_rank]))
            logits_local.requires_grad_(True)
            loss, metrics, numerator = _run_capturing(dis.module, torch, case["args"], batch, logits_local)
            loss.backward()
            results[cp_rank] = (loss.detach(), metrics, numerator, logits_local.grad.detach().clone(), batch)
        if pass_no == 1:
            fake.finish_pass_one()
    dis.mk_state(cp_size=1)
    return results, fake


def _assert_cp2_matches_cp1(torch, case, per_rank, *, cp_size=CP_SIZE):
    """守恒/对齐断言（mock 与 gloo 两条路径共用）。per_rank[r] = dict(loss, metrics, numerators, grad)。"""

    from miles.backends.training_utils.cp_utils import assemble_log_prob_from_cp

    base = case["baseline"]
    batch = case["batch"]
    # (1) 逐 token 分子拼回 == 全量（逐位）
    for i, (total, resp) in enumerate(zip(batch["total_lengths"], batch["response_lengths"], strict=True)):
        chunks = {r: per_rank[r]["numerators"][i] for r in range(cp_size)}
        assert sum(c.numel() for c in chunks.values()) == resp
        restored = assemble_log_prob_from_cp(chunks, total, resp, cp_size)
        assert torch.equal(restored, base.numerators[i]), f"样本 {i} 分子拼回后与 CP=1 不逐位相等"
    # (2) 各 rank 部分和相加 == CP=1 loss（求和顺序不同,float64 下按 1e-12 相对误差）
    loss_sum = sum(per_rank[r]["loss"] for r in range(cp_size))
    torch.testing.assert_close(loss_sum, base.loss, rtol=1e-12, atol=1e-12)
    # (3) 梯度：各 rank 本地块拼回 == CP=1 全量梯度（逐位）
    grad_full = _reassemble_grad(torch, case, {r: per_rank[r]["grad"] for r in range(cp_size)}, cp_size)
    assert torch.equal(grad_full, base.grad), "CP=2 梯度拼回后与 CP=1 不逐位相等"
    # (4) 线性计数指标：跨 rank 求和 == CP=1（= aggregate_train_losses 的 DP×CP 求和口径）
    for key in (
        "dis_microbatch_provenance_tokens", "dis_accepted_tokens", "dis_rejected_tokens",
        # N4（I17/I20 纯观测）新增线性计数：同样按本 rank 分片报、跨 rank 求和 == CP=1
        "dis_nonsingleton_provenance_tokens", "dis_singleton_accepted_tokens", "dis_candidate_signal_tokens",
        "dis_zero_advantage_accepted_tokens", "dis_rejected_low_tokens", "dis_rejected_high_tokens",
        "dis_support_size_1", "dis_support_size_2_3", "dis_support_size_4_7", "dis_support_size_8_15",
        "dis_support_size_16_plus",
    ):
        total = sum(float(per_rank[r]["metrics"][key]) for r in range(cp_size))
        assert total == float(base.metrics[key]), key
    # (5) loss 指标同口径
    loss_metric_sum = sum(float(per_rank[r]["metrics"]["loss"]) for r in range(cp_size))
    assert loss_metric_sum == pytest.approx(float(base.metrics["loss"]), rel=1e-12, abs=1e-12)


# ---------------------------------------------------------------------------
# 0. 切分规则本身：miles helper 给出的本 rank 位置 == 人工按规则算出的集合
# ---------------------------------------------------------------------------


def test_zigzag_local_positions_match_hand_computed(dis):
    torch = dis.torch
    for cp_rank in range(CP_SIZE):
        for i, (t, resp) in enumerate(zip(_TOKENS, _RESP_LENS, strict=True)):
            got = _local_positions(torch, len(t), resp, cp_rank, CP_SIZE)
            assert got == _EXPECTED_LOCAL_POSITIONS[cp_rank][i], (cp_rank, i)
    # 两 rank 的位置集合恰好划分整条 response（无重叠、无遗漏）
    for i, resp in enumerate(_RESP_LENS):
        union = sorted(_EXPECTED_LOCAL_POSITIONS[0][i] + _EXPECTED_LOCAL_POSITIONS[1][i])
        assert union == list(range(resp))


def test_local_layout_helper_agrees_with_miles_mask_slicing(dis, case):
    """被测模块的 `_local_response_layout`：分片长度 = miles 切出的 mask 长度 = 人工集合大小。"""

    torch = dis.torch
    batch = case["batch"]
    for cp_rank in range(CP_SIZE):
        dis.mk_state(cp_size=CP_SIZE, cp_rank=cp_rank)
        cp = dis.module._read_cp_state(__import__("miles.backends.training_utils.parallel", fromlist=["x"]).get_parallel_state())
        local_masks, lengths = dis.module._local_response_layout(
            cp,
            total_lengths=batch["total_lengths"],
            response_lengths=batch["response_lengths"],
            loss_masks=batch["loss_masks"],
            qkv_format="thd",
            max_seq_lens=None,
        )
        for i, positions in enumerate(_EXPECTED_LOCAL_POSITIONS[cp_rank]):
            assert lengths[i] == len(positions)
            expected_mask = torch.tensor([_LOSS_MASKS[i][p] for p in positions], dtype=torch.long)
            assert torch.equal(local_masks[i], expected_mask), (cp_rank, i)


# ---------------------------------------------------------------------------
# 1. CP=1 路径：分片即全量,归约恒等（逐位不变的结构性证据）
# ---------------------------------------------------------------------------


def test_cp1_layout_is_identity_and_reduce_is_noop(dis, case):
    torch = dis.torch
    from miles.backends.training_utils.parallel import get_parallel_state

    dis.mk_state(cp_size=1)
    cp = dis.module._read_cp_state(get_parallel_state())
    assert (cp.size, cp.rank, cp.group) == (1, 0, None)
    batch = case["batch"]
    local_masks, lengths = dis.module._local_response_layout(
        cp,
        total_lengths=batch["total_lengths"],
        response_lengths=batch["response_lengths"],
        loss_masks=batch["loss_masks"],
        qkv_format="thd",
        max_seq_lens=None,
    )
    assert local_masks is batch["loss_masks"]  # miles 在 CP=1 原样返回同一列表对象
    assert lengths == batch["response_lengths"]
    counts = torch.tensor([[1, 2], [3, 4]])
    assert dis.module._cp_all_reduce_sum(counts, cp) is counts  # 恒等,不触碰 dist


def test_cp1_baseline_matches_execution_authority(dis, case):
    """CP=1 权威本身仍与标量权威一致（保证后面 CP=2 对拍的参照物没有漂移）。"""

    from repoharness2.training.faithful_dis import DisTokenRecord, faithful_dis_loss_by_execution

    base = case["baseline"]
    batch = case["batch"]
    executions = {}
    for i, (cur, beh, adv, mask) in enumerate(
        zip(base.current, batch["rollout_log_probs"], batch["advantages"], batch["loss_masks"], strict=True)
    ):
        executions[f"e{i}"] = [
            DisTokenRecord(logp_current=c, logp_rollout=b, advantage=a, provenance_mask=int(m))
            for c, b, a, m in zip(cur.tolist(), beh.tolist(), adv.tolist(), mask.tolist(), strict=True)
        ]
    ref = faithful_dis_loss_by_execution(executions)
    assert float(base.loss) == pytest.approx(sum(ref.per_execution_loss.values()), rel=1e-9)
    assert ref.per_execution_denominator == {"e0": 8, "e1": 4, "e2": 5}
    assert float(base.metrics["dis_microbatch_provenance_tokens"]) == 17
    assert float(base.metrics["dis_zero_contribution_microbatch"]) == 0.0


# ---------------------------------------------------------------------------
# 2. CP=2 mock 切分：守恒/对齐/计数/旗标/事件
# ---------------------------------------------------------------------------


def test_cp2_mock_numerators_grads_and_counts_reconstruct_cp1(dis, case, monkeypatch):
    torch = dis.torch
    results, fake = _run_cp2_ranks(dis, case, monkeypatch)
    per_rank = {
        r: dict(
            loss=results[r][0],
            metrics=results[r][1],
            numerators=list(results[r][2].split([len(p) for p in _EXPECTED_LOCAL_POSITIONS[r]], dim=0)),
            grad=results[r][3],
        )
        for r in range(CP_SIZE)
    }
    _assert_cp2_matches_cp1(torch, case, per_rank)
    # all_reduce seam 在每个 rank 每遍恰好调用一次（含空分片 rank）
    assert fake.calls == [0, 1, 0, 1]
    # 本地逐样本计数：rank0 的 s1 为空分片 → (0,0);两 rank 相加 = 各样本 (accepted, provenance)
    assert fake.local[0][1].tolist() == [0, 0]
    group = (fake.local[0] + fake.local[1]).tolist()
    assert [p for _, p in group] == [8, 4, 5]
    assert sum(a for a, _ in group) == float(case["baseline"].metrics["dis_accepted_tokens"])
    # 旗标：组内 accepted>0 → 两 rank 都报 0（与 CP=1 一致）
    assert float(results[0][1]["dis_zero_contribution_microbatch"]) == 0.0
    assert float(results[1][1]["dis_zero_contribution_microbatch"]) == 0.0


def test_cp2_mock_empty_shard_rank_is_zero_loss_but_graph_connected(dis, case, monkeypatch):
    """只含 s1 的 microbatch：rank0 分片为空——loss 精确 0、仍带 autograd 图、本地计数 0、
    旗标按组内总数（rank1 有 accepted）为 0;rank1 独自等于 CP=1 全量。"""

    torch = dis.torch
    full = case["batch"]
    sub_batch = {k: ([v[1]] if isinstance(v, list) else v) for k, v in full.items()}
    sub_batch["rollout_mask_sums"] = full["rollout_mask_sums"][1:2]
    start = full["total_lengths"][0]
    sub_logits = case["logits"][:, start : start + full["total_lengths"][1]].clone()
    sub_case = {"batch": sub_batch, "logits": sub_logits, "args": case["args"]}

    # CP=1 参照
    dis.mk_state(cp_size=1)
    l1 = sub_logits.clone().requires_grad_(True)
    loss1, metrics1, num1 = _run_capturing(dis.module, torch, case["args"], sub_batch, l1)
    loss1.backward()

    results, fake = _run_cp2_ranks(dis, sub_case, monkeypatch)
    loss0, metrics0, num0, grad0, _ = results[0]
    loss1b, metrics1b, num1b, grad1b, _ = results[1]
    assert num0.numel() == 0 and float(loss0) == 0.0
    assert bool((grad0 == 0.0).all())  # loss.backward() 已在 _run_cp2_ranks 里成功 → 图连接成立
    assert float(metrics0["dis_accepted_tokens"]) == 0.0
    assert float(metrics0["dis_microbatch_provenance_tokens"]) == 0.0
    assert float(metrics0["dis_zero_contribution_microbatch"]) == 0.0  # 组内有 accepted
    assert float(metrics1b["dis_zero_contribution_microbatch"]) == 0.0
    assert torch.equal(num1b, num1)
    torch.testing.assert_close(loss1b, loss1.detach(), rtol=1e-12, atol=1e-12)
    grad_full = _reassemble_grad(torch, sub_case, {0: grad0, 1: grad1b}, CP_SIZE)
    assert torch.equal(grad_full, l1.grad[0])
    assert fake.local[0].tolist() == [[0, 0]] and fake.local[1].tolist() == [[3, 4]]


@pytest.mark.parametrize(
    "scenario",
    ["all_rejected", "zero_provenance"],
)
def test_cp2_mock_zero_signal_semantics_match_cp1(dis, case, monkeypatch, scenario):
    """零贡献语义（F2 / SKIPPED_ZERO_SIGNAL 的 loss 层半场）在 CP=2 下与 CP=1 一致：
    组内 accepted=0 → 只有 cp rank 0 报旗标 1（聚合后 = CP=1 的 1）,两 rank loss 精确 0
    且带图、梯度精确 0。"""

    torch = dis.torch
    full = case["batch"]
    if scenario == "all_rejected":
        # behavior 整体 −10：log_ratio ≈ +10,全部越过信任上界
        mutated = dict(full, rollout_log_probs=[b - 10.0 for b in full["rollout_log_probs"]])
    else:
        mutated = dict(full, loss_masks=[torch.zeros_like(m) for m in full["loss_masks"]])
    mcase = {"batch": mutated, "logits": case["logits"], "args": case["args"]}

    dis.mk_state(cp_size=1)
    l1 = case["logits"].clone().requires_grad_(True)
    loss1, metrics1, _ = _run_capturing(dis.module, torch, case["args"], mutated, l1)
    assert float(loss1.detach()) == 0.0 and loss1.grad_fn is not None
    assert float(metrics1["dis_zero_contribution_microbatch"]) == 1.0

    results, fake = _run_cp2_ranks(dis, mcase, monkeypatch)
    flags = [float(results[r][1]["dis_zero_contribution_microbatch"]) for r in range(CP_SIZE)]
    assert flags == [1.0, 0.0]  # 只由 cp rank 0 发射,聚合和 == CP=1 的 1.0
    for r in range(CP_SIZE):
        assert float(results[r][0]) == 0.0
        assert bool((results[r][3] == 0.0).all())
        assert float(results[r][1]["dis_accepted_tokens"]) == 0.0
    prov_total = sum(float(results[r][1]["dis_microbatch_provenance_tokens"]) for r in range(CP_SIZE))
    assert prov_total == float(metrics1["dis_microbatch_provenance_tokens"])


def test_cp2_mock_accounting_event_emitted_once_with_group_counts(dis, case, monkeypatch, tmp_path):
    """逐样本记账事件：CP=2 下只由 cp rank 0 发射一次,entries 用组内归约后的整条
    response 计数,与 CP=1 发射的 entries 逐字段相等;rank1 不发射。"""

    torch = dis.torch
    sample_indices = [41, 42, 43]
    leaf_ordinals = [0, 1, 0]

    def read_events(directory):
        files = list(Path(directory).glob("rh2_events_*.jsonl"))
        rows = []
        for f in files:
            rows.extend(json.loads(x) for x in f.read_text().splitlines() if x.strip())
        return [r for r in rows if r["event"] == "sample_dis_accounting"]

    cp1_dir = tmp_path / "cp1"
    monkeypatch.setenv("MILES_RH2_EVENT_DIR", str(cp1_dir))
    dis.mk_state(cp_size=1)
    batch1 = dict(case["batch"], sample_indices=sample_indices, leaf_ordinals=leaf_ordinals)
    dis.module.faithful_dis_loss_function(
        case["args"], batch1, case["logits"].clone(), _mk_reducer(torch, batch1)
    )
    [cp1_event] = read_events(cp1_dir)

    event_dirs = {0: tmp_path / "cp2_rank0", 1: tmp_path / "cp2_rank1"}

    def add_identity(batch):
        batch["sample_indices"] = sample_indices
        batch["leaf_ordinals"] = leaf_ordinals

    _run_cp2_ranks(dis, case, monkeypatch, batch_override=add_identity, event_dirs=event_dirs)
    rank0_events = read_events(event_dirs[0])
    # 两遍各发一次（第一遍 seam 不归约,entries 只含本地计数,不作断言;第二遍为组内总数）
    assert len(rank0_events) == 2
    assert rank0_events[-1]["entries"] == cp1_event["entries"]
    assert cp1_event["entries"] == [
        {"sample_index": 41, "leaf_ordinal": 0, "accepted_tokens": 5, "provenance_tokens": 8},
        {"sample_index": 42, "leaf_ordinal": 1, "accepted_tokens": 3, "provenance_tokens": 4},
        {"sample_index": 43, "leaf_ordinal": 0, "accepted_tokens": 3, "provenance_tokens": 5},
    ]
    assert read_events(event_dirs[1]) == []


# ---------------------------------------------------------------------------
# 3. target∈support 断言在切分下逐位执行（跨 rank 边界负例,两个 rank 都必须炸）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("position", [1, 2, 7, 8])  # s0 的两处 rank 边界 1|2、7|8 两侧
def test_cp2_target_not_in_support_across_rank_boundary_raises_on_every_rank(dis, case, monkeypatch, position):
    torch = dis.torch
    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", _boom_all_reduce)
    bad_supports = [list(s) for s in _SUPPORTS[0]]
    target = _TOKENS[0][len(_TOKENS[0]) - _RESP_LENS[0] + position]
    bad_supports[position] = [t for t in bad_supports[position] if t != target] or [0]
    ids, offsets = _csr(bad_supports)
    owner = 0 if position in _EXPECTED_LOCAL_POSITIONS[0][0] else 1
    for cp_rank in range(CP_SIZE):
        dis.mk_state(cp_size=CP_SIZE, cp_rank=cp_rank)
        batch, logits_local = _rank_inputs(torch, case, cp_rank, CP_SIZE)
        batch["rollout_sampling_mask_ids"] = list(batch["rollout_sampling_mask_ids"])
        batch["rollout_sampling_mask_offsets"] = list(batch["rollout_sampling_mask_offsets"])
        batch["rollout_sampling_mask_ids"][0] = ids
        batch["rollout_sampling_mask_offsets"][0] = offsets
        with pytest.raises(dis.module.FaithfulDisLossError) as exc:
            dis.module.faithful_dis_loss_function(case["args"], batch, logits_local, _boom_reducer)
        assert exc.value.reason_code == "target_not_in_support", (cp_rank, position, owner)
        assert f"第 {position} 个 token" in str(exc.value)


def test_cp2_target_not_in_support_positive_control(dis, case, monkeypatch):
    """同一批数据支持集完好时两 rank 都正常出 loss（排除"总是炸"的假阳性）。"""

    results, _ = _run_cp2_ranks(dis, case, monkeypatch)
    assert all(bool(dis.torch.isfinite(results[r][0])) for r in range(CP_SIZE))


# ---------------------------------------------------------------------------
# 4. fail-closed：CP 状态/布局异常一律拒绝（无静默降级）
# ---------------------------------------------------------------------------


def _expect_reject(dis, case, cp_rank, reason, *, mutate=None, args=None, all_reduce=_boom_all_reduce):
    torch = dis.torch
    if all_reduce is not None:
        dis.module._cp_all_reduce_sum = all_reduce  # 由调用方 monkeypatch 兜底还原
    batch, logits_local = _rank_inputs(torch, case, cp_rank, CP_SIZE)
    if mutate is not None:
        replaced = mutate(batch, logits_local)
        if replaced is not None:
            logits_local = replaced
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args or case["args"], batch, logits_local, _boom_reducer)
    assert exc.value.reason_code == reason, str(exc.value)
    return exc.value


def test_cp_state_missing_rejected(dis, case, monkeypatch):
    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", _boom_all_reduce)
    dis.mk_state(cp=None)
    err = _expect_reject(dis, case, 0, "cp_state_invalid", all_reduce=None)
    assert "size=None" in str(err)


def test_cp_size_none_rejected(dis, case, monkeypatch):
    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", _boom_all_reduce)
    dis.mk_state(cp=dis.GroupInfo(rank=0, size=None, group=None))
    _expect_reject(dis, case, 0, "cp_state_invalid", all_reduce=None)


@pytest.mark.parametrize("bad", [dict(rank=2, size=2), dict(rank=-1, size=2), dict(rank=0, size=0), dict(rank=True, size=2)])
def test_cp_rank_or_size_out_of_range_rejected(dis, case, monkeypatch, bad):
    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", _boom_all_reduce)
    dis.mk_state(cp=dis.GroupInfo(rank=bad["rank"], size=bad["size"], group=None))
    _expect_reject(dis, case, 0, "cp_state_invalid", all_reduce=None)


def test_cp_group_missing_rejected_at_reduce_point(dis, case):
    """cp.size=2 而 group=None（真实 seam 未 patch）：走到组内归约处拒绝,不静默按本地计数判旗标。"""

    dis.mk_state(cp_size=CP_SIZE, cp_rank=0)
    batch, logits_local = _rank_inputs(dis.torch, case, 0, CP_SIZE)
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(case["args"], batch, logits_local, _mk_reducer(dis.torch, batch))
    assert exc.value.reason_code == "cp_group_missing"


@pytest.mark.parametrize("key", ["rollout_log_probs", "advantages"])
def test_cp2_unsliced_full_column_rejected(dis, case, monkeypatch, key):
    """behavior/advantage 列若仍是全量（未按本 rank 切分）→ 长度≠本 rank 分片长度,拒绝。"""

    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", _boom_all_reduce)
    dis.mk_state(cp_size=CP_SIZE, cp_rank=0)

    def mutate(batch, _logits):
        batch[key] = list(case["batch"][key])  # 全量列

    err = _expect_reject(dis, case, 0, "batch_column_length_mismatch", mutate=mutate, all_reduce=None)
    assert "本 rank CP 分片长度" in str(err)


def test_cp2_locally_sliced_loss_masks_rejected(dis, case, monkeypatch):
    """loss_masks 必须是全量：误传本 rank 分片 → 长度≠response_length,拒绝。"""

    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", _boom_all_reduce)
    dis.mk_state(cp_size=CP_SIZE, cp_rank=1)
    torch = dis.torch

    def mutate(batch, _logits):
        batch["loss_masks"] = [
            _local_response_slice(torch, m, total, resp, 1, CP_SIZE)
            for m, total, resp in zip(case["batch"]["loss_masks"], batch["total_lengths"], batch["response_lengths"], strict=True)
        ]

    _expect_reject(dis, case, 1, "batch_column_length_mismatch", mutate=mutate, all_reduce=None)


def test_cp2_tokens_missing_rejected(dis, case, monkeypatch):
    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", _boom_all_reduce)
    dis.mk_state(cp_size=CP_SIZE, cp_rank=0)

    def mutate(batch, _logits):
        del batch["tokens"]

    _expect_reject(dis, case, 0, "cp_token_stream_missing", mutate=mutate, all_reduce=None)


def test_cp2_full_layout_tensors_rejected(dis, case, monkeypatch):
    """CP=1 布局（全量 tokens + 全量 logits,行数 28 ≥ 本地所需）误入 cp.size=2：
    只靠行数下界抓不住,token 流对账必须拒绝。"""

    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", _boom_all_reduce)
    dis.mk_state(cp_size=CP_SIZE, cp_rank=0)
    torch = dis.torch

    def mutate(batch, _logits):
        batch["tokens"] = torch.cat(case["batch"]["unconcat_tokens"]).unsqueeze(0)
        return case["logits"].clone()

    err = _expect_reject(dis, case, 0, "cp_token_stream_mismatch", mutate=mutate, all_reduce=None)
    assert "cp.rank=0" in str(err)


def test_cp2_logits_rows_not_matching_tokens_rejected(dis, case, monkeypatch):
    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", _boom_all_reduce)
    dis.mk_state(cp_size=CP_SIZE, cp_rank=1)
    torch = dis.torch

    def mutate(_batch, logits):
        return torch.cat([logits, torch.zeros(1, 3, VOCAB, dtype=logits.dtype)], dim=1)

    _expect_reject(dis, case, 1, "logits_tokens_shape_mismatch", mutate=mutate, all_reduce=None)


def test_cp2_token_stream_from_other_rank_rejected(dis, case, monkeypatch):
    """rank1 的 token 流/logits 被 rank0 消费（rank 串位）→ 对账拒绝。"""

    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", _boom_all_reduce)
    torch = dis.torch
    dis.mk_state(cp_size=CP_SIZE, cp_rank=0)
    other_batch, other_logits = _rank_inputs(torch, case, 1, CP_SIZE)

    def mutate(batch, _logits):
        batch["tokens"] = other_batch["tokens"]
        return other_logits

    _expect_reject(dis, case, 0, "cp_token_stream_mismatch", mutate=mutate, all_reduce=None)


def test_cp2_allgather_cp_rejected(dis, case, monkeypatch):
    """cp.size=2 且 allgather_cp（DSA 连续切分布局,W9 未验证）→ 拒绝。CP=1 下本函数不拦
    该旗标（原样交给 miles:其 allgather_cp_redistribute 在 CP=1 也走一次组内
    all_reduce,单进程无 process group 时由 miles 自己报错,不属本函数语义）。"""

    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", _boom_all_reduce)
    dis.mk_state(cp_size=CP_SIZE, cp_rank=0)
    _expect_reject(dis, case, 0, "allgather_cp_unverified", args=_mk_args(allgather_cp=True), all_reduce=None)


def test_cp1_shaped_batch_declared_under_cp2_is_rejected_before_any_compute(dis, case, monkeypatch):
    """原 test_cp_not_supported_fail_closed 的语义继承：cp.size=2 声明下送入 CP=1
    形态的 batch（无 tokens 流）——不再有笼统的 cp_not_supported,但仍在触达
    reducer/collective 之前拒绝,绝不按 CP=1 口径算。"""

    monkeypatch.setattr(dis.module, "_cp_all_reduce_sum", _boom_all_reduce)
    dis.mk_state(cp_size=CP_SIZE, cp_rank=0)
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(case["args"], case["batch"], case["logits"].clone(), _boom_reducer)
    assert exc.value.reason_code == "cp_token_stream_missing"


# ---------------------------------------------------------------------------
# 5. 两进程 CPU gloo 组：真实 collective + 真实 GroupInfo.group
# ---------------------------------------------------------------------------


def _gloo_worker(rank, world_size, init_file, case_path, out_dir, scenario, conftest_path):
    """子进程：装配 vendor 世界 → gloo 组 → 真实 ParallelState(cp=WORLD) → 跑被测函数。

    每一步写 progress 文件：父进程超时时把它附在断言信息里,定位卡在哪一步。
    """

    progress_path = Path(out_dir) / f"progress_rank{rank}.log"

    def progress(stage: str) -> None:
        with open(progress_path, "a", encoding="utf-8") as fh:
            fh.write(stage + "\n")

    progress("start")
    spec = importlib.util.spec_from_file_location("_w9_adapters_conftest", conftest_path)
    conftest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conftest)
    for p in (str(conftest.MILES_ROOT), str(conftest.RH2_SRC)):
        if p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)  # 最终顺序：RH2_SRC, MILES_ROOT, ...
    conftest._install_ray_stub()
    progress("vendor world ready")

    import torch
    import torch.distributed as dist

    progress("torch imported; init_process_group")
    dist.init_process_group("gloo", init_method=f"file://{init_file}", rank=rank, world_size=world_size)
    progress("process group ready")
    result = {"rank": rank}
    try:
        from miles.backends.training_utils.parallel import ParallelState, set_parallel_state
        from miles.utils.ft_utils.process_group_utils import GroupInfo

        def trivial():
            return GroupInfo(rank=0, size=1, group=None)

        cp_info = GroupInfo(rank=rank, size=world_size, group=dist.group.WORLD)
        set_parallel_state(
            ParallelState(
                intra_dp=trivial(),
                intra_dp_cp=cp_info,
                cp=cp_info,
                tp=trivial(),
                pp=trivial(),
                ep=trivial(),
                etp=trivial(),
                indep_dp=trivial(),
                is_pp_last_stage=True,
            )
        )
        from repoharness2.adapters.miles import faithful_dis_loss as module

        progress("miles + loss module imported")
        case = torch.load(case_path, weights_only=False)
        batch, logits_local = _rank_inputs(torch, case, rank, world_size)
        batch["sample_indices"] = [41, 42, 43]
        batch["leaf_ordinals"] = [0, 1, 0]
        events_dir = Path(out_dir) / f"events_rank{rank}"
        os.environ["MILES_RH2_EVENT_DIR"] = str(events_dir)
        if scenario == "violation":
            bad = [list(s) for s in _SUPPORTS[0]]
            bad[2] = [1, 14]  # s0 位 2（rank1 拥有,紧邻 1|2 边界）的 target 6 被剔除
            ids, offsets = _csr(bad)
            batch["rollout_sampling_mask_ids"] = list(batch["rollout_sampling_mask_ids"])
            batch["rollout_sampling_mask_offsets"] = list(batch["rollout_sampling_mask_offsets"])
            batch["rollout_sampling_mask_ids"][0] = ids
            batch["rollout_sampling_mask_offsets"][0] = offsets
        logits_local.requires_grad_(True)
        try:
            loss, metrics, numerator = _run_capturing(module, torch, _mk_args(), batch, logits_local)
        except module.FaithfulDisLossError as err:
            result["reason_code"] = err.reason_code
        else:
            loss.backward()
            result["loss"] = loss.detach()
            result["metrics"] = {k: float(v) for k, v in metrics.items()}
            result["numerator"] = numerator
            result["grad"] = logits_local.grad.detach().clone()
        events = []
        for f in events_dir.glob("rh2_events_*.jsonl") if events_dir.exists() else []:
            events.extend(json.loads(x) for x in f.read_text().splitlines() if x.strip())
        result["events"] = [e for e in events if e["event"] == "sample_dis_accounting"]
    except Exception as err:  # noqa: BLE001 - 子进程失败原样带回父进程断言
        result["error"] = repr(err)
    finally:
        dist.destroy_process_group()
    progress("done")
    torch.save(result, Path(out_dir) / f"rank{rank}.pt")


def _spawn_gloo(scenario, case, tmp_path):
    import torch
    import torch.multiprocessing as mp

    out_dir = tmp_path / scenario
    out_dir.mkdir()
    case_path = out_dir / "case.pt"
    torch.save({"batch": case["batch"], "logits": case["logits"]}, case_path)
    init_file = out_dir / "rendezvous"
    conftest_path = str(Path(__file__).with_name("conftest.py"))
    ctx = mp.spawn(
        _gloo_worker,
        args=(CP_SIZE, str(init_file), str(case_path), str(out_dir), scenario, conftest_path),
        nprocs=CP_SIZE,
        join=False,
    )
    # ProcessContext.join(timeout) 在**任一**子进程结束时就返回（返回值 = 是否全部结束）,
    # 必须循环到 True;子进程异常退出时它自己抛 ProcessRaisedException。
    deadline = time.monotonic() + 300.0
    while not ctx.join(timeout=max(0.0, deadline - time.monotonic())):
        if time.monotonic() >= deadline:
            for p in ctx.processes:
                p.terminate()
            progress = {
                r: (out_dir / f"progress_rank{r}.log").read_text()
                if (out_dir / f"progress_rank{r}.log").exists()
                else "<无>"
                for r in range(CP_SIZE)
            }
            raise AssertionError(f"gloo CP=2 子进程 300s 内未全部结束（疑似 collective 挂起）;各 rank 进度: {progress}")
    results = {}
    for r in range(CP_SIZE):
        res = torch.load(out_dir / f"rank{r}.pt", weights_only=False)
        assert "error" not in res, res.get("error")
        results[r] = res
    return results


def test_cp2_gloo_two_process_group_reconstructs_cp1(dis, case, tmp_path):
    """真实两进程 gloo 组：完整被测函数（真实 all_reduce + miles CP 感知 reducer）。"""

    torch = dis.torch
    results = _spawn_gloo("normal", case, tmp_path)
    per_rank = {
        r: dict(
            loss=results[r]["loss"],
            metrics=results[r]["metrics"],
            numerators=list(results[r]["numerator"].split([len(p) for p in _EXPECTED_LOCAL_POSITIONS[r]], dim=0)),
            grad=results[r]["grad"],
        )
        for r in range(CP_SIZE)
    }
    _assert_cp2_matches_cp1(torch, case, per_rank)
    assert [results[r]["metrics"]["dis_zero_contribution_microbatch"] for r in range(CP_SIZE)] == [0.0, 0.0]
    # 记账事件：只有 cp rank 0 发射,entries 为组内归约后的整条 response 计数
    assert results[1]["events"] == []
    [event] = results[0]["events"]
    assert event["entries"] == [
        {"sample_index": 41, "leaf_ordinal": 0, "accepted_tokens": 5, "provenance_tokens": 8},
        {"sample_index": 42, "leaf_ordinal": 1, "accepted_tokens": 3, "provenance_tokens": 4},
        {"sample_index": 43, "leaf_ordinal": 0, "accepted_tokens": 3, "provenance_tokens": 5},
    ]


def test_cp2_gloo_cross_rank_target_violation_raises_on_both_ranks(dis, case, tmp_path):
    results = _spawn_gloo("violation", case, tmp_path)
    assert [results[r].get("reason_code") for r in range(CP_SIZE)] == ["target_not_in_support"] * CP_SIZE
    assert all(results[r]["events"] == [] for r in range(CP_SIZE))
