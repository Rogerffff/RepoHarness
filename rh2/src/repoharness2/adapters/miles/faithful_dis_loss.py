"""faithful DIS 的 miles custom loss 接线（C1′-b delta 第 2 项;R6-ext B4/B5/B6 修订）。

加载方式：miles `--loss-type custom_loss --custom-loss-function-path
repoharness2.adapters.miles.faithful_dis_loss.faithful_dis_loss_function`
（integration base `miles/backends/training_utils/loss_hub/losses.py`
get_loss_function 的 "custom_loss" 分支 -> load_function 按点路径加载）。
签名 = 该文件 LossFunction Protocol：``(args, batch, logits,
sum_of_sample_mean) -> (loss, metrics)``，loss 是带梯度标量，metrics 是
detached 标量 dict。

语义权威 = `repoharness2.training.faithful_dis` 的
``faithful_dis_loss_by_execution``（标量参考,FA-4;本模块**不改它**,只做
torch 同构实现,ε 与分母语义常量直接 import 同源）::

    loss_e   = -( Σ_{i∈e} f(r_i)·Â_i·logπ_θ(a_i) ) / D_e    D_e = execution e 的 provenance token 总数
    loss     = ( Σ_e loss_e ) / N_exec                       （batch 内 execution 等权）
    r_i      = exp(logπ_θ(a_i) - logπ_rollout(a_i))
    f(x)     = x  若 1-ε_ℓ < x < 1+ε_h（开区间,log 空间判定防溢出）,否则 0

归约层次（R6-ext B4 修订,逐 token 分子交 miles 既有 reducer,不自建
DP/CP 归约层）——本函数**只产逐 token 分子**,三层归约由 miles 链路完成：

1. **execution 级 provenance 分母**：``sum_of_sample_mean``（miles
   `loss.py` dispatcher 用 ``denominators=batch["rollout_mask_sums"]``
   构造,`cp_utils.get_sum_of_sample_mean`）对每个样本算
   ``(numerator·loss_mask).sum() / rollout_mask_sum``。
   ``rollout_mask_sums``（`train_data_conversion._compute_rollout_mask_sums`）
   = 该样本所属 rollout（= execution）**全部** sibling 的 loss_mask 总和,
   每个 sibling 都携带同一个整 rollout 分母——sibling 分散到不同
   microbatch/DP rank 时,各片段 ``片段分子/D_e`` 跨 microbatch 求和恰好
   重构出一个完整的 ``loss_e``。
2. **batch execution 等权**：dispatcher 把返回的 loss 乘
   ``num_microbatches/global_batch_size·loss_parallel_size``,其中
   ``global_batch_size = num_rollouts``（本 step 全 DP rollout 总数
   = N_exec）;megatron forward_backward 再 ÷num_microbatches、DDP 梯度
   归约 ÷DP size 与 loss_parallel_size 相消——净效果 = Σ_e loss_e / N_exec。
   （对照 integration base `loss.py:163-171` 与 `model.py` train_one_step
   的 apply_megatron_loss_scaling=True 路径。）

因此本函数返回的"loss"= 本 microbatch 各样本 ``片段分子/D_e`` 之和
（execution 部分和）,不是最终标量;metrics["loss"] 同口径,经
`aggregate_train_losses` 跨 microbatch 求和 ÷num_rollouts 后才等于权威
标量。旧实现的 microbatch 扁平 ``provenance.sum()`` 分母（把不同
execution 的 token 扁平平均）已删除——那是 B4 指出的真算法 bug。

关键实现决策（与验收条款一一对应）：

- **区间外 ratio 梯度精确为零**：f(r) 权重整体由 detach 后的 log_ratio
  构造（先 detach 再 exp/比较）,区间外权重恒 0——loss 项与 d loss/d logπ_θ
  都**精确**为 0（不是数值近似小,是乘 0）,与标量参考
  `per_token_grad_logp_current = -(f(r_i)·Â_i)/(D_e·N_exec)` 逐位一致。
- **ratio detach**：f(r) 是常数权重（faithful_dis.py 模块注释:RH2 显式
  算法决策,IcePop 族一致）；不 detach 变体必须另立函数名,本函数不留开关。
  ε 同理写死为预注册值（DIS_EPS_LOW/HIGH_PREREGISTERED）,消融另立名字。
- **denominator 语义显式预注册（FA-4 §1）**：``DENOMINATOR_SEMANTICS =
  DENOMINATOR_SEMANTICS_V1 = "provenance_tokens"``——D_e = execution 的
  provenance（loss_mask=1）token 总数,被 DIS 拒绝的 token **留在分母**
  （梯度为零但不重归一化）。与标量参考 v1 预注册同源 import,不复制字面量。
  fail-closed 配套：``rollout_mask_sums`` 缺失、per-sample 值 < 本样本
  provenance 数（账目矛盾）、或 <1（零 provenance execution,上游 FA-3
  应已拒绝）都拒绝整个 microbatch。``calculate_per_token_loss`` 模式下
  miles 会把 reducer 换成全局 token 扁平和（正是 B4 要删除的口径）,
  同样 fail-closed 拒绝。
- **current logprob = support-renormalized**（rollout_sampling_mask masked
  路径）：经 miles `get_log_probs_and_entropy(rollout_sampling_mask=...)`
  计算——`build_local_sampling_mask` 产 dense bool mask,`compute_log_probs`
  masked_fill(-inf) 后 log_softmax（integration base logit_processors.py
  的同一条消费路径,不自写第二份 softmax）。温度缩放同路径内完成
  （args.rollout_temperature）。
- **behavior logprob = batch["rollout_log_probs"]**,provenance =
  support-normalized（T0-B 正式分母列）：上游 sglang_rollout
  `append_sampling_metadata` 用引擎 `output_token_sampling_logprobs` 整体
  替换逐轮 logprob 后落 `Sample.rollout_log_probs`；rh2 capture 链在
  capture_wire `parse_turn_sampling_support` 做同款替换。观察/工具位
  （loss_mask=0）在两条链上都是单例支持集,其 support-normalized logprob
  恒 0。全词表 logprob 只留在 raw_response 诊断列,不进本函数。
- **weight-version spans 不改本函数任何计算（V2 交互确认）**：per-token
  权重版本区间（sglang meta_info.weight_versions -> Sample.weight_versions
  并入全部区间版本）**只修 staleness/版本记账**——buffer 准入
  （DefaultDataBuffer 的 oldest=min(weight_versions)）与验收审计因此看到
  turn 内跨更新的真实最旧版本。ratio 计算与它无关也不得有关：behavior
  logprob 是**生成时刻**由当时在役权重逐 token 算出并随 wire 原样传输的
  数值（跨更新轮的前段 token 天然是旧版本权重的 logprob，后段是新版本
  的——数值本身已经 per-token faithful，不存在"按版本换列"的操作），
  r_i = exp(logπ_θ - logπ_rollout) 与 f(r) 信任区间是纯数值判定，不看
  版本。**本模块没有、也不得新增按 weight_version 的 token/样本 gating**
  （排查结论：rh2/miles 两侧唯一按版本的准入 = buffer staleness 组级
  过滤；miles logprob_compare 的 same_version 只影响 parity 对拍的分组
  统计，不进 loss）。
- **target∈support 断言在 gather 之前（C2 收口）**：上游三层校验全在
  rollout 侧,loss 层没有——这里是训练端唯一防线（防传输错位/artifact
  损坏）。断言失败抛 FaithfulDisLossError,绝不静默出 -inf/NaN。
  设备约定（R6-ext B5）：`RolloutSamplingMask` 的 CSR 恒在 CPU
  （`sampling_mask.py` _to_owned_cpu_integer_tensor）,而 response tokens
  在训练设备上——检查在 **CPU 侧**完成（response tokens 是小整型张量,
  搬 CPU 的代价可忽略;把 CSR 搬 GPU 反而每 microbatch 都要拷大数组）。
- **全零 accepted token = 零贡献 microbatch,继续（F2,取代 B6 临时
  fail-stop）**：本 microbatch accepted（信任区间内 provenance token）为 0
  时**不再抛异常**——记 ``dis_zero_contribution_microbatch=1`` 指标,照常
  返回逐 token 分子（f(r) 权重全为 0,数值与梯度都精确为零,但乘法保留
  autograd 图连接）,让 megatron 完成本 microbatch 的 backward 与全部
  pipeline/collective 调用。理由（codex 零信号建议 §3）：microbatch 只是
  梯度累积切片,不是参数更新边界——"某 microbatch 全拒、其它 microbatch
  有效"是合法状态,per-microbatch 停机会误停有效的 global step。
  "零梯度不得静默走 AdamW"（B6 的真实风险:weight decay/momentum 在零梯度
  下仍改参）改由 **miles train_one_step 的全局 optimizer-step 边界**兜底：
  归约完成后扫描累计梯度,全局精确为零 → SKIPPED_ZERO_SIGNAL（不
  optimizer.step/不 scheduler.step/不发布权重/不增 weight_version,batch
  视为已消费）,并带连续跳过熔断（rh2-integration-v2 分支 model.py,
  commit 620aa6924）。数据损坏类（NaN/Inf、target∉support、长度错位、
  缺字段）**保持 fail-stop 不降级**,见下面 fail-closed 面。

- **CP>1 切分语义（W9;owner 2026-09-02 拍板目标链路必须同时支持 CP=1 与
  CP>1,此前 cp.size≠1 整体 fail-closed）**：切分规则只有一个来源——miles
  `cp_utils.get_logits_and_tokens_offset_with_cp` 的 zigzag 规则：每条样本
  （thd 按 total_length、bshd 按 max_seq_len）补到 2·cp_size·chunk_size 后
  等分 2·cp_size 块,rank r 拥有第 r 块与第 2·cp_size−1−r 块,本 rank 的
  response 位置 = 这两块与 response 区间的交集,按块序拼接。到达本函数时
  各列的形态（integration base 代码事实,行号见 w9_report.md）：
  * `rollout_log_probs`（behavior）——**已是本 rank 分片**：`data.py
    get_rollout_data` 用 `slice_log_prob_with_cp` 切过；
  * `advantages`——**已是本 rank 分片**：`loss.py compute_advantages_and_returns`
    从本 rank 分片形状的 kl/log_probs 广播标量 reward（`math_utils.
    get_grpo_returns` 的 `ones_like(kl[i])·reward`）；
  * `loss_masks`——**全量**：reducer `get_sum_of_sample_mean` 与本函数各自
    用 `get_local_response_loss_masks`（同一私有切片实现）切片；
  * `unconcat_tokens` 与 sampling-mask CSR——**全量**：`logit_processors.
    _iter_response_chunks` 按全局偏移取本 rank 的 logits 行/target token/
    response_indices,`build_local_sampling_mask` 据 response_indices 从全量
    CSR 选出本 rank 行的支持集（current logprob 的支持集重归一化因此天然
    只在本 rank 分片上做）；
  * `logits`——本 rank 布局 `[1, Σ_i 2·chunk_size_i (+尾部 pad), V]`,与
    `batch["tokens"]`（get_batch 切片后模型真正 forward 的 token 流）逐行对应。
  本函数在 CP>1 下做的事：(1) 用 `slice_with_cp`（get_batch 同款）把
  unconcat_tokens 切成本 rank 应有的 token 流,与 batch["tokens"] 逐位对账,
  且 logits 行数 == tokens 行数——全量（CP=1 布局）张量误入 CP>1 时行数往往
  碰巧够（全量 12 行 vs 本地 8 行）,只靠行数下界抓不住错位,必须对账 token
  流本身；(2) 逐样本本 rank 分片长度用 offset 规则独立算出,与 miles 切出的
  loss_mask 分片对账,再据此校验 current/behavior/advantage 三列长度；
  (3) target∈support 断言在**每个** rank 对整条 response 执行（本 rank 分片
  的超集;CSR 与 unconcat_tokens 都是全量,断言与 CP 无关,任一 rank 发现损坏
  即拒绝）；(4) 逐 token 分子只在本 rank 分片上算,交 CP 感知的 reducer——
  它按同一规则切 loss_mask 并除以整 execution 分母,各 rank 的 ``片段分子/D_e``
  经 DP×CP 梯度归约求和恰好重构完整 loss_e（与 sibling 分散到不同 microbatch
  的重构机制同构）；(5) accepted/provenance 计数做一次 CP 组内 all_reduce
  （`math_utils.compute_ess_ratio_contribution` 同款）：线性计数指标仍报本
  rank 分片值（miles `aggregate_train_losses` 跨 DP×CP 求和后 = CP=1 数值）,
  零贡献旗标按**组内总** accepted 判定且只由 cp rank 0 发射（其余 rank 报 0,
  避免聚合重复计数）,逐样本记账事件用组内归约后的整条 response 计数、只由
  cp rank 0 发射一次。CP=1 路径逐位不变：分片 = 全量,归约为恒等,旗标/事件
  发射条件恒真。
  fail-closed（不留静默降级）：cp 状态读不到/非法 → `cp_state_invalid`;
  CP>1 但 cp.group 缺失 → `cp_group_missing`;`allgather_cp`（DSA 连续切分
  布局,W9 未验证）→ `allgather_cp_unverified`;缺 batch["tokens"] →
  `cp_token_stream_missing`;logits 行数≠tokens 行数 →
  `logits_tokens_shape_mismatch`;token 流≠zigzag 分片 →
  `cp_token_stream_mismatch`;miles 两处切片长度不一致 →
  `cp_layout_inconsistent`;各列长度≠本 rank 分片长度 → 沿用
  `batch_column_length_mismatch`/`current_logprob_length_mismatch`。
  本地验证边界：单进程 mock ParallelState（cp.size=2,rank∈{0,1}）与两进程
  CPU gloo 组（tests/adapters_miles/test_w9_cp_faithful_dis.py）;真机 CP=2
  端到端归 GPU spike（C 包）。

- **实验 FT trainer 锁定（fail-closed,保留）**：
  ``MILES_EXPERIMENTAL_FT_TRAINER`` 开启时（miles/utils/environ.py
  ``enable_experimental_ft_trainer``,placement_group 的
  ``_select_train_group_class`` 据此选 miles/ray/train/group.py 的实验
  RayTrainGroup）本函数直接拒绝。理由：数据损坏类 fail-stop（本模块全部
  FaithfulDisLossError 拒绝路径）依赖"异常直达、job 在 optimizer 前终止";
  而实验 FT trainer 的 ``train()`` 用 ``_execute_all_alive_and_catch``
  捕获 cell 异常并 ``retry(_fn, max_attempts=30)`` 盲重试,部分 cell 失败、
  其余 normal 时甚至判 no_retry 继续前进（group.py
  ``_check_train_one_attempt``）——fail-stop 会被吞掉或退化成 30 次重试后
  的迟滞失败。spike 拓扑锁定默认 actor group（miles/ray/actor_group.py,
  异常无捕获直达 optimizer 之前）。

fail-closed 面（任一违反即抛错,样本不进梯度）：实验 FT trainer 开启、
replay 未开启
（rollout_top_p>=1.0）、calculate_per_token_loss、缺 rollout_sampling_mask
wire 字段、缺 rollout_log_probs、缺/矛盾 rollout_mask_sums、mask 覆盖数
!=response 长度、loss_mask 非 0/1、各列长度≠本 rank 应有长度、logp/advantage
非有限、CP 状态非法/CP 切分对账失败（见上面 CP 条目的 reason_code 清单）、
target∉support。注意 accepted=0 **不在**此面里（F2:零贡献指标 +
零 loss 继续,全局零信号由 train_one_step 的 optimizer-step 边界处理）。
"""

from __future__ import annotations

import math
from argparse import Namespace
from collections.abc import Callable
from dataclasses import dataclass

import torch
import torch.distributed as dist
from miles.backends.training_utils.cp_utils import (
    get_local_response_loss_masks,
    get_logits_and_tokens_offset_with_cp,
    slice_with_cp,
)
from miles.backends.training_utils.loss_hub.logit_processors import get_log_probs_and_entropy
from miles.backends.training_utils.parallel import get_parallel_state
from miles.backends.training_utils.sampling_mask import get_rollout_sampling_masks
from miles.utils.environ import enable_experimental_ft_trainer
from miles.utils.sampling import top_p_sampling_replay_enabled

try:
    # integration base（patch 0004+）才有事件层；pin base 下缺席 = 不发射，
    # 不影响 loss 语义（GPU spike 只在 integration base 上跑）。
    from miles.utils import rh2_event_log
except ImportError:  # pragma: no cover - pin base 分支
    rh2_event_log = None  # type: ignore[assignment]

from repoharness2.training.faithful_dis import (
    DENOMINATOR_SEMANTICS_V1,
    DIS_EPS_HIGH_PREREGISTERED,
    DIS_EPS_LOW_PREREGISTERED,
)

__all__ = [
    "DENOMINATOR_SEMANTICS",
    "FaithfulDisLossError",
    "faithful_dis_loss_function",
]

# 预注册分母语义（写死,不提供运行时开关；见模块 docstring 的选择理由）。
DENOMINATOR_SEMANTICS = DENOMINATOR_SEMANTICS_V1
assert DENOMINATOR_SEMANTICS == "provenance_tokens"  # 防止上游常量被改后静默漂移

# 信任区间（开区间,log 空间;与标量参考 _trust_bounds + _token_weight 同式）
_LOG_TRUST_LOW = math.log(1.0 - DIS_EPS_LOW_PREREGISTERED)
_LOG_TRUST_HIGH = math.log(1.0 + DIS_EPS_HIGH_PREREGISTERED)


class FaithfulDisLossError(RuntimeError):
    """faithful DIS 训练端 fail-closed 错误（reason_code 机器可读）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


@dataclass(frozen=True)
class _CpState:
    """本 rank 的 CP 事实（size/rank 已校验;group 只在 size>1 的组内归约处消费）。"""

    size: int
    rank: int
    group: object | None


def _is_plain_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _read_cp_state(parallel_state) -> _CpState:
    """读取并校验 CP 状态（W9）：cp 缺失/size 非正整数/rank 越界一律 fail-closed。

    这里绝不给默认值——"读不到 cp 就当 CP=1"正是 W9 禁止的静默降级：CP>1 下
    按 CP=1 口径算,会把本 rank 分片当成整条 response 消费而不报错。
    """

    cp = getattr(parallel_state, "cp", None)
    size = getattr(cp, "size", None)
    rank = getattr(cp, "rank", None)
    if not (_is_plain_int(size) and size >= 1 and _is_plain_int(rank) and 0 <= rank < size):
        raise FaithfulDisLossError(
            "cp_state_invalid",
            f"parallel_state.cp 不可读或非法（size={size!r}, rank={rank!r}）——CP 切分语义"
            "无法确定,拒绝整个 microbatch（不退回 CP=1 口径计算）。",
        )
    return _CpState(size=size, rank=rank, group=getattr(cp, "group", None))


def _cp_all_reduce_sum(tensor: torch.Tensor, cp: _CpState) -> torch.Tensor:
    """CP 组内原地 SUM 归约（与 miles math_utils.compute_ess_ratio_contribution 同款）。

    CP=1 直接返回;CP>1 而 group 缺失 → fail-closed（拿不到组内总计数,零贡献
    判定就无法与 CP=1 一致）。单进程 mock 测试可替换本 seam;真实 collective
    语义由两进程 gloo 测试覆盖。必须在所有 CP rank 上无条件调用（含本 rank
    分片为空的 rank）,否则其它 rank 会在此挂起。
    """

    if cp.size == 1:
        return tensor
    if cp.group is None:
        raise FaithfulDisLossError(
            "cp_group_missing",
            f"cp.size={cp.size} 但 parallel_state.cp.group 为 None——组内 accepted 计数无法"
            "归约,零贡献判定无法与 CP=1 保持一致,拒绝整个 microbatch。",
        )
    dist.all_reduce(tensor, op=dist.ReduceOp.SUM, group=cp.group)
    return tensor


def _local_response_layout(
    cp: _CpState,
    *,
    total_lengths: list[int],
    response_lengths: list[int],
    loss_masks: list[torch.Tensor],
    qkv_format: str,
    max_seq_lens,
) -> tuple[list[torch.Tensor], list[int]]:
    """本 rank 拥有的 response 位置 = miles zigzag 规则（切分规则唯一来源）。

    loss_mask 分片直接用 miles `get_local_response_loss_masks`（reducer
    `get_sum_of_sample_mean` 用同一私有切片实现）,CP=1 时它原样返回全量列表。
    CP>1 时再用 `get_logits_and_tokens_offset_with_cp` 独立算一遍本 rank 的
    response 行数,与切出的分片长度对账——两处都源自同一 offset 规则,对账
    防的是 miles 内部两处切片实现漂移（升 pin 时当场红,而不是静默错位）。
    返回 (本 rank loss_mask 分片列表, 逐样本分片长度)。
    """

    local_masks = get_local_response_loss_masks(
        total_lengths, response_lengths, loss_masks, qkv_format, max_seq_lens
    )
    if cp.size == 1:
        return local_masks, list(response_lengths)
    lengths: list[int] = []
    for i, (total, resp, mask) in enumerate(zip(total_lengths, response_lengths, local_masks, strict=True)):
        max_seq_len = max_seq_lens[i] if max_seq_lens is not None else None
        _, _, logits_offset, _ = get_logits_and_tokens_offset_with_cp(
            total, resp, qkv_format, max_seq_len, cp_rank=cp.rank, cp_size=cp.size
        )
        expected = sum(hi - lo for lo, hi in logits_offset)
        if int(mask.numel()) != expected:
            raise FaithfulDisLossError(
                "cp_layout_inconsistent",
                f"样本 {i}: miles 切出的 loss_mask 分片长度 {int(mask.numel())} != offset 规则算出的"
                f"本 rank response 行数 {expected}（cp.size={cp.size}, cp.rank={cp.rank}）——miles"
                " 内部切片实现已漂移,拒绝整个 microbatch。",
            )
        lengths.append(expected)
    return local_masks, lengths


def _authenticate_local_token_stream(
    cp: _CpState,
    parallel_state,
    *,
    batch,
    unconcat_tokens,
    logits: torch.Tensor,
    qkv_format: str,
    max_seq_lens,
) -> None:
    """CP>1：本 rank 实际喂给模型的 token 流必须是 unconcat_tokens 按 zigzag 规则切出的分片。

    这是"CP 切分与 tokens 不符"的直接校验：batch["tokens"] 是 get_batch 切片后
    模型真正 forward 的输入,logits 逐行对应它。若全量（CP=1 布局）的 tokens/
    logits 被送进 CP>1 的 loss,行数常常碰巧够用（全量 12 行 vs 本地 8 行）,
    下游按 zigzag 偏移取行会静默错位——只有与 token 流本身对账才能抓住。
    切片用 miles `slice_with_cp`（get_batch 同款,含 2·cp_size·chunk_size 补齐）;
    thd 下 get_batch 还会在拼接后补尾部 pad,所以只对账前缀,pad 值不做假设。
    """

    tokens = batch.get("tokens")
    if tokens is None:
        raise FaithfulDisLossError(
            "cp_token_stream_missing",
            f"cp.size={cp.size} 下 faithful DIS 需要 batch[tokens]（get_batch 切片后的本 rank"
            " token 流）做切分对账,缺失即无法证明 logits 布局与本 rank 分片一致。",
        )
    tokens = torch.as_tensor(tokens)
    if tuple(logits.shape[:-1]) != tuple(tokens.shape):
        raise FaithfulDisLossError(
            "logits_tokens_shape_mismatch",
            f"logits 行形状 {tuple(logits.shape[:-1])} != tokens 形状 {tuple(tokens.shape)}"
            "（模型输出必须与本 rank token 流逐行对应）。",
        )
    expected_parts = []
    for i, sample_tokens in enumerate(unconcat_tokens):
        max_seq_len = max_seq_lens[i] if max_seq_lens is not None else None
        expected_parts.append(
            slice_with_cp(torch.as_tensor(sample_tokens), 0, qkv_format, max_seq_len, parallel_state=parallel_state)
        )

    def _mismatch(detail: str) -> FaithfulDisLossError:
        return FaithfulDisLossError(
            "cp_token_stream_mismatch",
            f"batch[tokens] 不是 unconcat_tokens 按 zigzag 规则（cp.size={cp.size}, "
            f"cp.rank={cp.rank}）切出的本 rank 分片：{detail}——切分长度/布局与 tokens 不符,"
            "拒绝整个 microbatch。",
        )

    if qkv_format == "bshd":
        if tokens.dim() != 2 or tokens.size(0) != len(expected_parts):
            raise _mismatch(f"bshd 期望 [{len(expected_parts)}, L],实际 {tuple(tokens.shape)}")
        for i, part in enumerate(expected_parts):
            part = part.to(device=tokens.device, dtype=tokens.dtype)
            if tokens[i].numel() != part.numel() or not torch.equal(tokens[i], part):
                raise _mismatch(f"样本 {i} 的行与切片不等")
        return
    expected = torch.cat(expected_parts, dim=0).to(device=tokens.device, dtype=tokens.dtype)
    if tokens.dim() != 2 or tokens.size(0) != 1 or tokens.size(1) < expected.numel():
        raise _mismatch(f"thd 期望 [1, >={expected.numel()}],实际 {tuple(tokens.shape)}")
    if not torch.equal(tokens[0, : expected.numel()], expected):
        raise _mismatch(f"前 {expected.numel()} 个 token 与切片不等")


def _assert_targets_in_support(sample_index: int, response_tokens: torch.Tensor, mask) -> None:
    """C2：gather 前逐 token 断言 target ∈ 其支持集（整个检查在 CPU 侧,B5）。

    读 CSR 用 `RolloutSamplingMask._as_tensors()`——与上游
    train_data_conversion 的出账读法同一私有面（升 pin 时若重构,此处
    与上游同批断链,哨兵性质与 governed_buffer 的 `_inner._dynamic_filter`
    自检相同）。CSR 由构造器钉死在 CPU;response tokens 在训练设备
    （CUDA/MPS）上——先把这一小段整型 token 搬到 CPU,再做比较,避免
    跨设备索引直接 RuntimeError（R6-ext B5 的 MPS 复现）。
    """

    resp_len = int(response_tokens.numel())
    if len(mask) != resp_len:
        raise FaithfulDisLossError(
            "sampling_mask_length_mismatch",
            f"样本 {sample_index}: mask 覆盖 {len(mask)} 个 token != response 长度 {resp_len}。",
        )
    # B5：完整性检查统一搬到 CPU（CSR 本来就在 CPU;tokens 是 [R] 小整型）
    targets = response_tokens.detach().to(device="cpu", dtype=torch.long)
    ids, offsets = mask._as_tensors()
    lengths = (offsets[1:] - offsets[:-1]).to(torch.long)
    row = torch.repeat_interleave(torch.arange(resp_len, dtype=torch.long), lengths)
    hit = torch.zeros(resp_len, dtype=torch.bool)
    hit[row[ids.to(torch.long) == targets[row]]] = True
    if not bool(hit.all()):
        bad = int((~hit).nonzero()[0].item())
        raise FaithfulDisLossError(
            "target_not_in_support",
            f"样本 {sample_index}: response 第 {bad} 个 token "
            f"{int(targets[bad])} 不在其采样支持集内——引擎出站有 "
            "force-include 保证,出现此况即传输错位或数据损坏（C2,fail-closed:"
            "拒绝整个 microbatch,不静默产出 -inf logprob）。",
        )


def _column_tensors(
    batch,
    key: str,
    expected_lengths: list[int],
    *,
    detach: bool,
    length_label: str = "response_length",
) -> list[torch.Tensor]:
    """batch 的逐样本 [R] 列 -> 张量列表（长度逐样本核对,fail-closed）。

    ``expected_lengths``：CP=1 下就是 response_lengths;CP>1 下 behavior/advantage
    两列已是本 rank 分片,期望长度 = 本 rank 分片长度（全量列误入即拒绝）。
    """

    column = batch.get(key)
    if column is None:
        raise FaithfulDisLossError(
            "batch_column_missing",
            f"faithful DIS 要求 batch 携带 {key}（缺失即上游装配/转换链断账）。",
        )
    tensors = []
    for i, (item, expected) in enumerate(zip(column, expected_lengths, strict=True)):
        t = torch.as_tensor(item)
        if t.numel() != expected:
            raise FaithfulDisLossError(
                "batch_column_length_mismatch",
                f"样本 {i}: {key} 长度 {t.numel()} != {length_label} {expected}。",
            )
        tensors.append(t.detach() if detach else t)
    return tensors


def _cat_column(
    batch,
    key: str,
    expected_lengths: list[int],
    *,
    detach: bool,
    length_label: str = "response_length",
) -> torch.Tensor:
    """batch 的逐样本 [R] 列 -> 平铺 [ΣR]（长度逐样本核对,fail-closed）。"""

    return torch.cat(
        _column_tensors(batch, key, expected_lengths, detach=detach, length_label=length_label), dim=0
    )


def _validate_rollout_mask_sums(batch, loss_masks_flat: torch.Tensor, response_lengths: list[int]) -> None:
    """execution 分母账目核对（B4 配套 fail-closed;数值本身由 reducer 消费）。

    `rollout_mask_sums[i]` = 样本 i 所属 execution 的全体 sibling loss_mask
    总和,必须 >= 本样本自己的 provenance 数（sibling 只会加不会减）,且
    >= 1（零 provenance execution 上游 FA-3 已拒绝,出现即账目矛盾——与
    标量权威 `faithful_dis_loss_by_execution` 对 D_e=0 直接 raise 同义）。
    """

    sums = batch.get("rollout_mask_sums")
    if sums is None:
        raise FaithfulDisLossError(
            "rollout_mask_sums_missing",
            "faithful DIS 的 execution 分母依赖 batch[rollout_mask_sums]"
            "（train_data_conversion 无条件产出;缺失说明转换链断账,或 reducer"
            " 将退化为 per-sample-mean 口径——两者都不允许静默发生）。",
        )
    own_sums = [
        float(chunk.sum().item()) for chunk in loss_masks_flat.split(response_lengths, dim=0)
    ]
    for i, (execution_sum, own_sum) in enumerate(zip(sums, own_sums, strict=True)):
        execution_sum = float(execution_sum)
        if not math.isfinite(execution_sum) or execution_sum < 1.0:
            raise FaithfulDisLossError(
                "execution_zero_provenance",
                f"样本 {i}: rollout_mask_sums={execution_sum}——零 provenance "
                "execution 上游（FA-3 归一化）已拒绝,出现在这里是账目矛盾。",
            )
        if execution_sum + 1e-6 < own_sum:
            raise FaithfulDisLossError(
                "rollout_mask_sums_inconsistent",
                f"样本 {i}: rollout_mask_sums={execution_sum} < 本样本 provenance"
                f" 数 {own_sum}——整 execution 分母不可能小于单个 sibling 的"
                " provenance 数,上游账目矛盾。",
            )


def _emit_sample_dis_accounting(batch, *, per_sample_counts) -> None:
    """逐样本 DIS token 记账事件（sample_dis_accounting；P0-8 正控归因）。

    ``per_sample_counts`` = 按样本顺序的 ``(accepted, provenance)`` 计数;CP>1
    时是组内归约后的**整条 response** 计数,且只由 cp rank 0 调用一次（每个
    microbatch 每个 DP 组恰好一条事件,judge 的逐样本事实不因 CP 切分被拆半）。
    只在事件层可用且 batch 携带 sample_indices 时发射(miles 训练 forward
    透传;单元测试构造的 batch 无此键则静默跳过,loss 数值路径零改动)。
    """
    if rh2_event_log is None or not rh2_event_log.enabled():
        return
    sample_indices = batch.get("sample_indices") if hasattr(batch, "get") else None
    if sample_indices is None:
        return
    # leaf 唯一身份（租前聚焦修复批 #1）：fan-out 叶继承同一 Sample.index，
    # (sample_index, leaf_ordinal) 才是唯一叶身份。列缺失（旧 wire）时记 None，
    # judge 侧对缺失身份 fail-closed。
    leaf_ordinals = batch.get("leaf_ordinals") if hasattr(batch, "get") else None
    entries = []
    for pos, (sid, (accepted, provenance)) in enumerate(zip(sample_indices, per_sample_counts, strict=True)):
        entries.append(
            {
                "sample_index": int(sid),
                "leaf_ordinal": (
                    int(leaf_ordinals[pos])
                    if leaf_ordinals is not None and pos < len(leaf_ordinals)
                    else None
                ),
                "accepted_tokens": int(accepted),
                "provenance_tokens": int(provenance),
            }
        )
    rh2_event_log.emit("sample_dis_accounting", entries=entries)


def faithful_dis_loss_function(
    args: Namespace,
    batch,
    logits: torch.Tensor,
    sum_of_sample_mean: Callable[[torch.Tensor], torch.Tensor],
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """faithful DIS loss（miles custom loss 入口;语义见模块 docstring）。"""

    # B6 半收口：实验 FT trainer 会吞掉 fail-stop（catch+retry(30)+部分失败
    # 继续,见模块 docstring）——本 loss 的全部 fail-closed 语义只在默认
    # actor group 下成立,启用即拒绝。旗标与 placement_group 选型同源
    # （enable_experimental_ft_trainer 读 MILES_EXPERIMENTAL_FT_TRAINER）。
    if enable_experimental_ft_trainer():
        raise FaithfulDisLossError(
            "experimental_ft_trainer_locked",
            "MILES_EXPERIMENTAL_FT_TRAINER 已开启——实验 FT trainer 捕获 cell "
            "异常并最多重试 30 次,部分 cell 失败其余 normal 时不重试继续前进"
            "（miles/ray/train/group.py train→_execute_all_alive_and_catch→"
            "_check_train_one_attempt）,会吞掉 faithful DIS 的 fail-stop 语义。"
            "spike 锁定默认 actor group;解锁 = FT 语义与 fail-stop 交互经 owner"
            " 审定后另行放行。",
        )
    parallel_state = get_parallel_state()
    # W9：CP 状态显式读取+校验（此前 cp.size≠1 整体 fail-closed;现按真实切分
    # 语义消费,读不到/非法 → 拒绝,绝不默认按 CP=1 算）。
    cp = _read_cp_state(parallel_state)
    if getattr(args, "calculate_per_token_loss", False):
        raise FaithfulDisLossError(
            "per_token_loss_not_supported",
            "calculate_per_token_loss 下 miles 把 reducer 换成全局 token 扁平和"
            "（sum_of_token）,分母语义退化为跨 execution 扁平平均——正是 B4 删除"
            "的口径,fail-closed。",
        )
    if not top_p_sampling_replay_enabled(args):
        raise FaithfulDisLossError(
            "sampling_replay_disabled",
            f"faithful DIS 要求 sampling-support replay 开启（rollout_top_p="
            f"{getattr(args, 'rollout_top_p', 1.0)} 须 <1.0）——current/behavior 两列都以"
            "支持集归一化为口径,replay 关闭时该口径不存在（T0-B）。",
        )
    if cp.size > 1 and getattr(args, "allgather_cp", False):
        # DSA 的 allgather CP 用连续切分布局（get_batch/logit_processors 各有一条
        # 分支,再经 allgather_cp_redistribute 转回 zigzag）,W9 只验证了 zigzag
        # 布局的对账与守恒,未验证的布局不放行（CP=1 下该旗标不改变本函数的任何布局
        # 假设,原样交给 miles 处理,不拦——保持 CP=1 行为不变）。
        raise FaithfulDisLossError(
            "allgather_cp_unverified",
            f"cp.size={cp.size} 且 args.allgather_cp=True——DSA allgather-CP 布局未经 faithful"
            " DIS 的 CP 对账验证（W9 只覆盖 zigzag 布局）,fail-closed。",
        )

    response_lengths: list[int] = list(batch["response_lengths"])
    total_lengths: list[int] = list(batch["total_lengths"])
    unconcat_tokens = batch["unconcat_tokens"]
    qkv_format: str = args.qkv_format
    max_seq_lens = batch.get("max_seq_lens", None)

    if cp.size > 1:
        # W9：先证明"本 rank 拿到的 logits 确实是 zigzag 分片布局",再消费任何列。
        _authenticate_local_token_stream(
            cp,
            parallel_state,
            batch=batch,
            unconcat_tokens=unconcat_tokens,
            logits=logits,
            qkv_format=qkv_format,
            max_seq_lens=max_seq_lens,
        )

    # wire 字段缺失由 get_rollout_sampling_masks 自身 fail-closed（ValueError）
    sampling_masks = get_rollout_sampling_masks(batch)
    if len(sampling_masks) != len(unconcat_tokens):
        raise FaithfulDisLossError(
            "sampling_mask_batch_mismatch",
            f"mask 条数 {len(sampling_masks)} != 样本数 {len(unconcat_tokens)}。",
        )

    # C2：gather 前逐样本断言 target ∈ support（CPU 侧,B5）。CP>1 下 CSR 与
    # unconcat_tokens 都是全量,每个 rank 对整条 response 断言（本 rank 分片的
    # 超集）——断言与切分无关,任一 rank 发现损坏即拒绝,也避免"只查本 rank
    # 行"时切分规则一旦漂移就漏查。
    for i, (tokens, resp_len, mask) in enumerate(
        zip(unconcat_tokens, response_lengths, sampling_masks, strict=True)
    ):
        response_tokens = tokens[-resp_len:] if resp_len else tokens[0:0]
        _assert_targets_in_support(i, torch.as_tensor(response_tokens), mask)

    # provenance：loss_masks 到达时是全量（逐样本长度 = response_length）
    loss_masks_full = _column_tensors(batch, "loss_masks", response_lengths, detach=True)
    loss_masks_flat = torch.cat(loss_masks_full, dim=0)
    if not bool(((loss_masks_flat == 0) | (loss_masks_flat == 1)).all()):
        raise FaithfulDisLossError(
            "loss_mask_not_binary",
            "loss_masks 只允许 0/1（provenance 语义;标量参考同禁）。",
        )

    # execution 分母账目核对（数值由 reducer 消费,这里只核账,B4;用全量 mask——
    # 整 execution 分母 ≥ 本样本整条 response 的 provenance 数,比分片口径更强）
    _validate_rollout_mask_sums(batch, loss_masks_flat, response_lengths)

    # W9：本 rank 分片（CP=1 时 = 全量列表,长度 = response_lengths）
    local_masks, local_lengths = _local_response_layout(
        cp,
        total_lengths=total_lengths,
        response_lengths=response_lengths,
        loss_masks=loss_masks_full,
        qkv_format=qkv_format,
        max_seq_lens=max_seq_lens,
    )
    length_label = "response_length" if cp.size == 1 else f"本 rank CP 分片长度(cp.rank={cp.rank}/{cp.size})"

    # current logprob：support-renormalized（miles masked 消费路径,含温度缩放;
    # CP>1 下 miles 自行按同一 zigzag 规则取本 rank 行与本 rank 支持集）
    log_probs_list = get_log_probs_and_entropy(
        logits,
        args=args,
        unconcat_tokens=unconcat_tokens,
        total_lengths=total_lengths,
        response_lengths=response_lengths,
        with_entropy=False,
        max_seq_lens=max_seq_lens,
        rollout_sampling_mask=sampling_masks,
    )["log_probs"]
    # 形状归一：miles true_on_policy 路径的 compute_log_probs 已返回一维 [R],
    # get_log_probs_and_entropy 再 squeeze(-1) 会把 R=1（单 token response,或 CP>1
    # 下本 rank 恰好只有一行的分片）压成零维,torch.cat 直接炸;megatron 路径返回
    # [R,1] 无此问题。reshape(-1) 只规整形状不改数值（W9 finding,见 w9_report.md）。
    log_probs_list = [lp.reshape(-1) for lp in log_probs_list]
    for i, (lp, local_len) in enumerate(zip(log_probs_list, local_lengths, strict=True)):
        if lp.numel() != local_len:
            raise FaithfulDisLossError(
                "current_logprob_length_mismatch",
                f"样本 {i}: current logprob 长度 {lp.numel()} != {length_label} {local_len}"
                "（miles 取行规则与本函数的分片规则应逐位对齐;出现说明并行切分假设被破坏）。",
            )
    current_logp = torch.cat(log_probs_list, dim=0)

    # behavior logprob：Sample.rollout_log_probs（support-normalized,T0-B;CP>1 下
    # get_rollout_data 已切成本 rank 分片）
    behavior_logp = _cat_column(
        batch, "rollout_log_probs", local_lengths, detach=True, length_label=length_label
    )
    behavior_logp = behavior_logp.to(device=current_logp.device, dtype=current_logp.dtype)
    # advantage：CP>1 下由本 rank 分片形状的 kl 广播得到,同样已是分片
    advantages = _cat_column(batch, "advantages", local_lengths, detach=True, length_label=length_label)
    advantages = advantages.to(device=current_logp.device, dtype=current_logp.dtype)
    local_mask_flat = torch.cat(local_masks, dim=0)

    # fail-closed：任何非有限输入拒绝整个 microbatch（标量参考对 mask=0 位
    # 同样校验——掩码不豁免数据损坏检查）
    for name, tensor in (
        ("current_logp", current_logp),
        ("behavior_logp", behavior_logp),
        ("advantages", advantages),
    ):
        if not bool(torch.isfinite(tensor).all()):
            raise FaithfulDisLossError(
                "non_finite_input",
                f"{name} 含非有限值——上游事实矛盾（logp 采集/归一化损坏）,fail-closed。",
            )

    # f(r)：detach 后 log 空间判区间,区间外权重精确为 0（梯度也精确为 0）
    log_ratio = (current_logp - behavior_logp).detach()
    in_trust = (log_ratio > _LOG_TRUST_LOW) & (log_ratio < _LOG_TRUST_HIGH)
    ratio_weight = torch.where(in_trust, log_ratio, torch.zeros_like(log_ratio)).exp()
    weight = ratio_weight * in_trust.to(current_logp.dtype)

    provenance_bool = local_mask_flat != 0
    # 逐样本 (accepted, provenance) 计数,先本 rank 分片,再 CP 组内求和。
    # 线性计数指标报本 rank 值（aggregate_train_losses 跨 DP×CP 求和后 = CP=1
    # 数值）;零贡献旗标与逐样本记账事件用组内总数（非线性判定/逐样本事实不能
    # 被切分拆半）。all_reduce 在所有 CP rank 上无条件执行,含空分片 rank。
    accepted_flags = (in_trust & provenance_bool).to(torch.int64)
    provenance_flags = provenance_bool.to(torch.int64)
    local_counts = torch.stack(
        [
            torch.stack([acc.sum(), prov.sum()])
            for acc, prov in zip(
                accepted_flags.split(local_lengths, dim=0),
                provenance_flags.split(local_lengths, dim=0),
                strict=True,
            )
        ]
    )  # [N, 2]
    group_counts = _cp_all_reduce_sum(local_counts.clone(), cp)
    accepted, microbatch_provenance = (int(v) for v in local_counts.sum(dim=0).tolist())
    rejected = microbatch_provenance - accepted
    accepted_group = int(group_counts[:, 0].sum().item())

    # F2（取代 B6 per-microbatch fail-stop）：accepted=0 只记指标,不改控制流。
    # 此时 f(r) 权重在全部 provenance 位上恰为 0,下面的逐 token 分子数值与
    # 梯度都**精确**为零,但乘法保留 autograd 图——megatron 照常完成本
    # microbatch 的 backward 与 pipeline/collective 调用（分布式训练里零贡献
    # microbatch 不得提前退出,否则其它 rank 会在通信处挂起）。"全局是否零
    # 信号"由 miles train_one_step 在归约完成后、optimizer 前统一判定
    # （精确零 → SKIPPED_ZERO_SIGNAL,不 step/不发布/不增版本 + 连续跳过
    # 熔断）,这里不再有权威。CP>1：按组内总 accepted 判定,只由 cp rank 0 报 1。
    zero_contribution = 1.0 if (accepted_group == 0 and cp.rank == 0) else 0.0

    # 逐 token 分子（provenance 掩码与 execution 分母都由 miles reducer 施加;
    # 非 provenance 位数值有限（上面已断言）,reducer 乘 loss_mask=0 归零）
    per_token_numerator = -(weight * advantages * current_logp)
    loss = sum_of_sample_mean(per_token_numerator)
    if not loss.requires_grad:
        # W9：本 rank 在本 microbatch 没有任何 response 行（CP>1 下分片全空,例如短
        # response 整体落在另一 rank 的块里）时,miles 对空块返回 logits.new_zeros((0,))
        # 不带 autograd 图,loss 也就没有 grad_fn——megatron backward 会直接报错。用
        # 0·logits.sum() 把图接回 logits（数值与梯度都精确为 0）,与 miles loss.py 对
        # allgather_cp 的处理同款（"Forces autograd to traverse the full graph on every
        # rank to avoid hang"）。CP=1 下 response 至少一行,本分支不可达。
        loss = loss + 0.0 * logits.sum()

    # 租前审查 P0-8：逐样本 accepted/provenance token 事实（正控归因）。
    # "正控组与 applied step 共批"不足以证明正控产生了训练信号——同 step 可能
    # 完全由其他组驱动;这里把 DIS 接受判定按样本切片发给验收事件层,judge 据此
    # 要求正控组自身 accepted token > 0。batch["sample_indices"] 由 miles 训练
    # forward 的 get_batch keys 透传(patch 0005),缺席时(单元测试/旧树)不发射。
    # CP>1：整条 response 的计数只由 cp rank 0 发射一次。
    if cp.rank == 0:
        _emit_sample_dis_accounting(batch, per_sample_counts=group_counts.tolist())

    device = logits.device
    metrics = {
        # 注意口径：这里是本 microbatch（CP>1 时:本 rank 分片）的 execution 部分和;
        # 经 aggregate_train_losses 跨 microbatch/DP×CP 求和 ÷num_rollouts 后 =
        # faithful_dis_loss_by_execution 的权威标量。
        "loss": loss.clone().detach(),
        "dis_microbatch_provenance_tokens": torch.tensor(float(microbatch_provenance), device=device),
        "dis_accepted_tokens": torch.tensor(float(accepted), device=device),
        "dis_rejected_tokens": torch.tensor(float(rejected), device=device),
        # 聚合口径同上：aggregate_train_losses 跨 microbatch 求和 ÷num_rollouts,
        # 因此聚合值 = 零贡献 microbatch 数 / num_rollouts（监控看非零即可）。
        "dis_zero_contribution_microbatch": torch.tensor(zero_contribution, device=device),
    }
    return loss, metrics
