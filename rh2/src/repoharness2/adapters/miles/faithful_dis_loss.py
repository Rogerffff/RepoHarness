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
!=response 长度、loss_mask 非 0/1、各列长度不一致、logp/advantage 非有限、
CP>1、target∉support。注意 accepted=0 **不在**此面里（F2:零贡献指标 +
零 loss 继续,全局零信号由 train_one_step 的 optimizer-step 边界处理）。
"""

from __future__ import annotations

import math
from argparse import Namespace
from collections.abc import Callable

import torch
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


def _cat_column(batch, key: str, response_lengths: list[int], *, detach: bool) -> torch.Tensor:
    """batch 的逐样本 [R] 列 -> 平铺 [ΣR]（长度逐样本核对,fail-closed）。"""

    column = batch.get(key)
    if column is None:
        raise FaithfulDisLossError(
            "batch_column_missing",
            f"faithful DIS 要求 batch 携带 {key}（缺失即上游装配/转换链断账）。",
        )
    tensors = []
    for i, (item, resp_len) in enumerate(zip(column, response_lengths, strict=True)):
        t = torch.as_tensor(item)
        if t.numel() != resp_len:
            raise FaithfulDisLossError(
                "batch_column_length_mismatch",
                f"样本 {i}: {key} 长度 {t.numel()} != response_length {resp_len}。",
            )
        tensors.append(t.detach() if detach else t)
    return torch.cat(tensors, dim=0)


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


def _emit_sample_dis_accounting(batch, *, in_trust, provenance, response_lengths) -> None:
    """逐样本 DIS token 记账事件（sample_dis_accounting；P0-8 正控归因）。

    ``in_trust``/``provenance`` 是按 response_lengths 顺序拼接的扁平布尔张量;
    这里按样本切回片段并计数。只在事件层可用且 batch 携带 sample_indices 时
    发射(miles 训练 forward 透传;单元测试构造的 batch 无此键则静默跳过,
    loss 数值路径零改动)。
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
    offset = 0
    for pos, (sid, rlen) in enumerate(zip(sample_indices, response_lengths, strict=True)):
        span_trust = in_trust[offset : offset + rlen]
        span_prov = provenance[offset : offset + rlen]
        entries.append(
            {
                "sample_index": int(sid),
                "leaf_ordinal": (
                    int(leaf_ordinals[pos])
                    if leaf_ordinals is not None and pos < len(leaf_ordinals)
                    else None
                ),
                "accepted_tokens": int((span_trust & span_prov).sum().item()),
                "provenance_tokens": int(span_prov.sum().item()),
            }
        )
        offset += rlen
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
    if parallel_state.cp.size != 1:
        raise FaithfulDisLossError(
            "cp_not_supported",
            f"faithful DIS custom loss 尚未接 CP 归约（cp.size={parallel_state.cp.size}）——"
            "target∈support/逐 token 对齐的 CP 切分语义归硬件段验证,此前 fail-closed。",
        )
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

    response_lengths: list[int] = list(batch["response_lengths"])
    total_lengths: list[int] = list(batch["total_lengths"])
    unconcat_tokens = batch["unconcat_tokens"]

    # wire 字段缺失由 get_rollout_sampling_masks 自身 fail-closed（ValueError）
    sampling_masks = get_rollout_sampling_masks(batch)
    if len(sampling_masks) != len(unconcat_tokens):
        raise FaithfulDisLossError(
            "sampling_mask_batch_mismatch",
            f"mask 条数 {len(sampling_masks)} != 样本数 {len(unconcat_tokens)}。",
        )

    # C2：gather 前逐样本断言 target ∈ support（CPU 侧,B5）
    for i, (tokens, resp_len, mask) in enumerate(
        zip(unconcat_tokens, response_lengths, sampling_masks, strict=True)
    ):
        response_tokens = tokens[-resp_len:] if resp_len else tokens[0:0]
        _assert_targets_in_support(i, torch.as_tensor(response_tokens), mask)

    # current logprob：support-renormalized（miles masked 消费路径,含温度缩放）
    log_probs_list = get_log_probs_and_entropy(
        logits,
        args=args,
        unconcat_tokens=unconcat_tokens,
        total_lengths=total_lengths,
        response_lengths=response_lengths,
        with_entropy=False,
        max_seq_lens=batch.get("max_seq_lens", None),
        rollout_sampling_mask=sampling_masks,
    )["log_probs"]
    for i, (lp, resp_len) in enumerate(zip(log_probs_list, response_lengths, strict=True)):
        if lp.numel() != resp_len:
            raise FaithfulDisLossError(
                "current_logprob_length_mismatch",
                f"样本 {i}: current logprob 长度 {lp.numel()} != response_length {resp_len}"
                "（CP=1 下应逐位对齐;出现说明并行切分假设被破坏）。",
            )
    current_logp = torch.cat(log_probs_list, dim=0)

    # behavior logprob：Sample.rollout_log_probs（support-normalized,T0-B）
    behavior_logp = _cat_column(batch, "rollout_log_probs", response_lengths, detach=True)
    behavior_logp = behavior_logp.to(device=current_logp.device, dtype=current_logp.dtype)
    advantages = _cat_column(batch, "advantages", response_lengths, detach=True)
    advantages = advantages.to(device=current_logp.device, dtype=current_logp.dtype)
    loss_masks_flat = _cat_column(batch, "loss_masks", response_lengths, detach=True)
    if not bool(((loss_masks_flat == 0) | (loss_masks_flat == 1)).all()):
        raise FaithfulDisLossError(
            "loss_mask_not_binary",
            "loss_masks 只允许 0/1（provenance 语义;标量参考同禁）。",
        )

    # execution 分母账目核对（数值由 reducer 消费,这里只核账,B4）
    _validate_rollout_mask_sums(batch, loss_masks_flat, response_lengths)

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

    provenance_bool = loss_masks_flat != 0
    microbatch_provenance = int(provenance_bool.sum().item())
    accepted = int((in_trust & provenance_bool).sum().item())
    rejected = microbatch_provenance - accepted

    # F2（取代 B6 per-microbatch fail-stop）：accepted=0 只记指标,不改控制流。
    # 此时 f(r) 权重在全部 provenance 位上恰为 0,下面的逐 token 分子数值与
    # 梯度都**精确**为零,但乘法保留 autograd 图——megatron 照常完成本
    # microbatch 的 backward 与 pipeline/collective 调用（分布式训练里零贡献
    # microbatch 不得提前退出,否则其它 rank 会在通信处挂起）。"全局是否零
    # 信号"由 miles train_one_step 在归约完成后、optimizer 前统一判定
    # （精确零 → SKIPPED_ZERO_SIGNAL,不 step/不发布/不增版本 + 连续跳过
    # 熔断）,这里不再有权威。
    zero_contribution = 1.0 if accepted == 0 else 0.0

    # 逐 token 分子（provenance 掩码与 execution 分母都由 miles reducer 施加;
    # 非 provenance 位数值有限（上面已断言）,reducer 乘 loss_mask=0 归零）
    per_token_numerator = -(weight * advantages * current_logp)
    loss = sum_of_sample_mean(per_token_numerator)

    # 租前审查 P0-8：逐样本 accepted/provenance token 事实（正控归因）。
    # "正控组与 applied step 共批"不足以证明正控产生了训练信号——同 step 可能
    # 完全由其他组驱动;这里把 DIS 接受判定按样本切片发给验收事件层,judge 据此
    # 要求正控组自身 accepted token > 0。batch["sample_indices"] 由 miles 训练
    # forward 的 get_batch keys 透传(patch 0005),缺席时(单元测试/旧树)不发射。
    _emit_sample_dis_accounting(
        batch, in_trust=in_trust, provenance=provenance_bool, response_lengths=response_lengths
    )

    device = logits.device
    metrics = {
        # 注意口径：这里是本 microbatch 的 execution 部分和;经
        # aggregate_train_losses 跨 microbatch 求和 ÷num_rollouts 后 =
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
