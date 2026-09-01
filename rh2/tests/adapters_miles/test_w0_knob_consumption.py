"""W0 算法/config 核对（06 计划 §3 W0 行 + §1 A8/A6;Wave1）。

两块内容,全部以真实 miles 代码路径实测,不建通用"未消费参数检测器":

一、A6 前提验证——miles stock 的 remove_sample 行为实测（锚定行号,
integration base rh2-integration-v3）:

- `miles/ray/rollout/train_data_conversion.py:107-108`:
  ``if sample.remove_sample: sample.loss_mask = [0]*response_length``
  —— 样本**留在组内**（不剔除行）,只把 loss_mask 全置零;
- 同文件 `_post_process_rewards`（:313-314）与 `_normalize_rewards_by_rollout`
  （:288-293）对**全部**样本取 reward,没有任何 remove_sample 检查——
  remove_sample 成员的 reward **照常进组内 baseline 的 mean/std**（上游
  arguments.py:2412 的 help 文本自己写明 "does not determine whether the
  sample participates in advantage normalization"）;
- `_compute_rollout_mask_sums`（:209-216）在置零**之后**统计,整条 rollout
  被 remove 时其 rollout_mask_sums = 0（零分母事实）;
- 训练侧 reducer `cp_utils.get_sum_of_sample_mean`（:121）对分母
  ``torch.clamp_min(denominator, 1)``——零分母被静默 clamp 成 1,该样本
  以"零贡献行"的形式静默通过 stock loss,不产生 NaN 也不报警;
- rh2 faithful DIS（`faithful_dis_loss.py` `_validate_rollout_mask_sums`）
  对 rollout_mask_sums < 1 直接抛 ``execution_zero_provenance``——即便
  W1b 组级准入漏放,这条 stock"留组零分母"路径在 faithful DIS profile 下
  也 fail-closed,支撑 A6"我们的准入下该路径不可达"的断言。

二、E2 旋钮清单逐一核对（每旋钮:消费点行号 + 正例 + 反例）:

- ``--disable-grpo-std-normalization`` -> train_data_conversion.py:290
  （06 计划写 :288,integration base 上已漂移到 :290,语义不变）;
- ``--disable-rewards-normalization``/rewards_normalization ->
  train_data_conversion.py:314;
- dynamic_sampling_filter_path -> fully_async_data_buffer.py:117（装载）
  + :133（put 时调用）;
- ``--max-weight-staleness`` -> fully_async_data_buffer.py:161（get 时消费）;
- ``--eps-clip``/``--eps-clip-high`` -> **仅** losses.py:214（stock PPO
  policy_loss_function）经 compute_policy_loss（math_utils.py:263）消费;
  faithful DIS profile 下填 eps-clip = 假配置,本文件给出机械证明
  （逐位相等断言）;
- faithful DIS 自有信任区间 -> 预注册常量 DIS_EPS_LOW/HIGH_PREREGISTERED
  （repoharness2.training.faithful_dis,0.8/3.0,开区间 (0.2,4.0)）,
  不走任何 CLI 旋钮。

运行方式（与本目录其它 integration_base 测试一致）::

    cd rh2 && RH2_MILES_PATH=$REPO/reference/miles-rh2-integration \
        uv run pytest tests/adapters_miles/test_w0_knob_consumption.py -q
"""

from __future__ import annotations

import math
from argparse import Namespace
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.integration_base

VOCAB = 13


# ---------------------------------------------------------------------------
# 公共工具
# ---------------------------------------------------------------------------


@pytest.fixture()
def dis(world, monkeypatch):
    """faithful DIS 被测模块 + 单进程 trivial ParallelState（沿用
    test_faithful_dis_loss.py 的 dis fixture 形态,不 import 该测试模块）。"""

    monkeypatch.delenv("MILES_EXPERIMENTAL_FT_TRAINER", raising=False)

    import torch

    from miles.backends.training_utils.parallel import ParallelState, set_parallel_state
    from miles.utils.ft_utils.process_group_utils import GroupInfo

    from repoharness2.adapters.miles import faithful_dis_loss as module

    def trivial() -> GroupInfo:
        return GroupInfo(rank=0, size=1, group=None)

    set_parallel_state(
        ParallelState(
            intra_dp=trivial(),
            intra_dp_cp=trivial(),
            cp=trivial(),
            tp=trivial(),
            pp=trivial(),
            ep=trivial(),
            etp=trivial(),
            indep_dp=trivial(),
            is_pp_last_stage=True,
        )
    )
    return SimpleNamespace(module=module, torch=torch)


def _mk_conv_sample(world, i, reward, *, remove=False):
    """conversion 消费的最小完成样本:每样本自成一条 rollout（rollout_id=i）,
    同一 prompt 组（group_index=0）,response 3 token 全 provenance。"""

    s = world.mk_miles_input(index=i, group_index=0, rollout_id=i)
    s.tokens = [1, 2, 3, 10 + i, 11 + i]
    s.response_length = 3
    s.loss_mask = [1, 1, 1]
    s.status = world.MS.Status.COMPLETED
    s.reward = reward
    s.remove_sample = remove
    return s


def _convert(world, samples, **args_over):
    from miles.ray.rollout.train_data_conversion import convert_samples_to_train_data

    args = world.mk_miles_args(rollout_top_p=1.0, **args_over)
    return convert_samples_to_train_data(args, samples, {}, None, None)


def _mk_done_sample(world, i, reward, versions=()):
    s = world.mk_miles_input(index=i, group_index=0, rollout_id=i)
    s.status = world.MS.Status.COMPLETED
    s.reward = reward
    s.weight_versions = [str(v) for v in versions]
    return s


def _mk_buffer(world, **args_over):
    from miles.rollout.fully_async_data_buffer import (
        DataBufferConstructorInput,
        DefaultDataBuffer,
    )

    args = world.mk_miles_args(**args_over)
    recycled: list = []
    buf = DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=recycled.append))
    return buf, recycled


def _mk_entry(world, rewards, versions=()):
    from miles.rollout.fully_async_data_buffer import DataBufferInput

    group = [_mk_done_sample(world, i, r, versions) for i, r in enumerate(rewards)]
    prompt_group = [world.mk_miles_input(index=i) for i in range(len(rewards))]
    return DataBufferInput(prompt_group=prompt_group, group=group), prompt_group


# --- faithful DIS 最小两样本 case（形态沿 test_faithful_dis_loss,自含不互 import）


def _csr(supports):
    ids: list[int] = []
    offsets = [0]
    for sup in supports:
        ids.extend(sup)
        offsets.append(len(ids))
    return ids, offsets


_DIS_SPEC = [
    # tokens = prompt+response;supports 逐 response token（target 必在其内）
    dict(tokens=[1, 2, 3, 4, 5, 6], resp=3, supports=[[4, 7], [5], [6, 8]], adv=[1.0, -0.5, 0.7]),
    dict(tokens=[1, 2, 7, 8], resp=2, supports=[[7, 4], [8]], adv=[0.3, -1.2]),
]


def _mk_dis_args(**over):
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


def _mk_dis_case(torch, *, targets, loss_masks=None, rollout_mask_sums=None, seed=11):
    """targets = 逐样本目标 log-ratio 列表;behavior 列由 current − target 回填。"""

    loss_masks = loss_masks or [[1] * spec["resp"] for spec in _DIS_SPEC]
    g = torch.Generator().manual_seed(seed)
    total_lengths = [len(spec["tokens"]) for spec in _DIS_SPEC]
    logits = torch.randn(1, sum(total_lengths), VOCAB, generator=g, dtype=torch.float64)
    batch = {
        "unconcat_tokens": [torch.tensor(spec["tokens"], dtype=torch.long) for spec in _DIS_SPEC],
        "total_lengths": total_lengths,
        "response_lengths": [spec["resp"] for spec in _DIS_SPEC],
        "loss_masks": [torch.tensor(m, dtype=torch.long) for m in loss_masks],
        "advantages": [torch.tensor(spec["adv"], dtype=torch.float64) for spec in _DIS_SPEC],
        "rollout_sampling_mask_ids": [_csr(spec["supports"])[0] for spec in _DIS_SPEC],
        "rollout_sampling_mask_offsets": [_csr(spec["supports"])[1] for spec in _DIS_SPEC],
        "rollout_mask_sums": torch.tensor(
            rollout_mask_sums
            if rollout_mask_sums is not None
            else [float(sum(m)) for m in loss_masks],
            dtype=torch.float32,
        ),
    }

    from miles.backends.training_utils.loss_hub.logit_processors import get_log_probs_and_entropy
    from miles.backends.training_utils.sampling_mask import get_rollout_sampling_masks

    args = _mk_dis_args()
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
    batch["rollout_log_probs"] = [
        c - torch.tensor(t, dtype=torch.float64) for c, t in zip(current, targets, strict=True)
    ]
    return batch, logits


def _mk_dis_reducer(torch, batch):
    from miles.backends.training_utils.cp_utils import get_sum_of_sample_mean

    return get_sum_of_sample_mean(
        list(batch["total_lengths"]),
        list(batch["response_lengths"]),
        batch["loss_masks"],
        False,
        "thd",
        None,
        denominators=batch["rollout_mask_sums"],
    )


# ===========================================================================
# 一、A6 前提验证:miles stock remove_sample 行为实测
# ===========================================================================


def test_a6_remove_sample_stays_in_group_and_pollutes_baseline(world):
    """正例:remove_sample=True 成员**留组**,loss_mask 全零、rollout_mask_sums=0,
    且其 reward 照常进组内 baseline 的 mean/std（污染证明:与"含它计算"逐位
    一致,与"剔除它计算"不一致）。"""

    import torch

    rewards = [1.0, 0.0, 0.0, 1.0]
    samples = [_mk_conv_sample(world, i, r, remove=(i == 2)) for i, r in enumerate(rewards)]
    td = _convert(world, samples, rewards_normalization=True, grpo_std_normalization=True)

    # 留组:4 个样本一行不少（train_data_conversion.py:107 只置零 mask,不删行）
    assert len(td["tokens"]) == 4
    assert td["loss_masks"][2] == [0, 0, 0]
    assert td["loss_masks"][0] == [1, 1, 1]
    # 零分母事实:被 remove 的 rollout 的 mask 总和 = 0（:112 + :209-216）
    assert td["rollout_mask_sums"] == [3, 3, 0, 3]
    # raw reward 原样保留(remove_sample 的 0.0 也在列)
    assert td["raw_reward"] == rewards

    # baseline 污染:归一化按**含** remove 成员的 mean/std（:288-293）
    t = torch.tensor(rewards, dtype=torch.float)
    include = (t - t.mean()) / (t.std() + 1e-6)
    assert td["rewards"] == pytest.approx(include.tolist())
    kept = torch.tensor([r for i, r in enumerate(rewards) if i != 2], dtype=torch.float)
    exclude = (kept - kept.mean()) / (kept.std() + 1e-6)
    assert td["rewards"][0] != pytest.approx(exclude.tolist()[0])


def test_a6_remove_sample_false_negative_control(world):
    """反例:同批数据 remove_sample 全 False,loss_mask/分母原样保留。"""

    rewards = [1.0, 0.0, 0.0, 1.0]
    samples = [_mk_conv_sample(world, i, r) for i, r in enumerate(rewards)]
    td = _convert(world, samples, rewards_normalization=True, grpo_std_normalization=True)
    assert td["loss_masks"] == [[1, 1, 1]] * 4
    assert td["rollout_mask_sums"] == [3, 3, 3, 3]


def test_a6_stock_reducer_clamps_zero_denominator_to_zero_contribution(dis):
    """stock 训练侧对零分母的实际处置:cp_utils.py:121 ``clamp_min(denominator,1)``
    —— 全 remove 的 rollout 以 0/1=0 的零贡献行静默通过,不产生 NaN、不报错。"""

    torch = dis.torch
    from miles.backends.training_utils.cp_utils import get_sum_of_sample_mean

    reducer = get_sum_of_sample_mean(
        [4, 3],
        [3, 3],
        [torch.tensor([1, 1, 1]), torch.tensor([0, 0, 0])],  # 样本 1 = 全 remove
        False,
        "thd",
        None,
        denominators=torch.tensor([3.0, 0.0]),  # rollout_mask_sums 含零分母
    )
    x = torch.ones(6, dtype=torch.float64)
    out = reducer(x)
    assert torch.isfinite(out)
    assert out.item() == pytest.approx(1.0)  # 样本 0: 3/3;样本 1: 0/clamp(0,1)=0


def test_a6_faithful_dis_fail_closed_on_zero_provenance_execution(dis):
    """faithful DIS 侧:同一"留组零分母"形状直接 fail-closed
    （execution_zero_provenance）——即便组级准入漏放,该路径也到不了梯度。"""

    torch = dis.torch
    batch, logits = _mk_dis_case(
        torch,
        targets=[[0.0, 0.0, 0.0], [0.0, 0.0]],
        loss_masks=[[1, 1, 1], [0, 0]],  # 样本 1 = stock remove 后的全零 mask
        rollout_mask_sums=[3.0, 0.0],
    )
    with pytest.raises(dis.module.FaithfulDisLossError) as ei:
        dis.module.faithful_dis_loss_function(_mk_dis_args(), batch, logits, _mk_dis_reducer(torch, batch))
    assert ei.value.reason_code == "execution_zero_provenance"


# ===========================================================================
# 二、旋钮逐一核对（正例 + 反例）
# ===========================================================================

# --- --disable-grpo-std-normalization（train_data_conversion.py:290）-------


def test_grpo_std_normalization_consumed_positive(world):
    """正例:grpo_std_normalization=True 时归一化含 ÷(std+1e-6)。"""

    import torch

    rewards = [1.0, 0.0, 0.0, 1.0]
    samples = [_mk_conv_sample(world, i, r) for i, r in enumerate(rewards)]
    td = _convert(world, samples, rewards_normalization=True, grpo_std_normalization=True)
    t = torch.tensor(rewards, dtype=torch.float)
    expected = (t - t.mean()) / (t.std() + 1e-6)
    assert td["rewards"] == pytest.approx(expected.tolist())


def test_grpo_std_normalization_disabled_negative(world):
    """反例:--disable-grpo-std-normalization（False）时只做去均值,无 std 除法。"""

    rewards = [1.0, 0.0, 0.0, 1.0]
    samples = [_mk_conv_sample(world, i, r) for i, r in enumerate(rewards)]
    td = _convert(world, samples, rewards_normalization=True, grpo_std_normalization=False)
    assert td["rewards"] == pytest.approx([0.5, -0.5, -0.5, 0.5])  # 仅 mean-centered


# --- rewards_normalization（train_data_conversion.py:314）------------------


def test_rewards_normalization_consumed_positive(world):
    """正例:rewards_normalization=True 时 rewards != raw_reward（进归一化分支）。"""

    rewards = [1.0, 0.0, 0.0, 1.0]
    samples = [_mk_conv_sample(world, i, r) for i, r in enumerate(rewards)]
    td = _convert(world, samples, rewards_normalization=True, grpo_std_normalization=False)
    assert td["rewards"] != td["raw_reward"]
    assert sum(td["rewards"]) == pytest.approx(0.0)  # 去均值后组内和为 0


def test_rewards_normalization_disabled_negative(world):
    """反例:--disable-rewards-normalization（False）时 raw reward 原样透传。"""

    rewards = [1.0, 0.0, 0.0, 1.0]
    samples = [_mk_conv_sample(world, i, r) for i, r in enumerate(rewards)]
    td = _convert(world, samples, rewards_normalization=False)
    assert td["rewards"] == rewards
    assert td["raw_reward"] == rewards


# --- dynamic_sampling_filter_path（fully_async_data_buffer.py:117/:133）----


async def test_dynamic_filter_consumed_in_async_buffer_positive(world):
    """正例:配 stock check_reward_nonzero_std 时,零方差组在 put 即被丢弃
    （不进 buffer、不回收、drop 计数入 metrics）;非零方差组正常入队。"""

    buf, recycled = _mk_buffer(
        world,
        dynamic_sampling_filter_path=(
            "miles.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std"
        ),
    )
    same, _ = _mk_entry(world, [1.0, 1.0])
    await buf.put(same)  # 全同 reward -> drop
    varied, _ = _mk_entry(world, [0.0, 1.0])
    await buf.put(varied)
    got = await buf.get()
    assert got is varied
    assert recycled == []  # drop 不是 recycle:prompt 不回 unused handler
    metrics = buf.get_metrics()
    assert metrics["rollout/dynamic_filter/drop_zero_std_1.0"] == 1


async def test_dynamic_filter_none_negative(world):
    """反例:path=None 时 load_function 返回 None、call_dynamic_filter 恒 keep,
    零方差组照常入队。"""

    buf, recycled = _mk_buffer(world, dynamic_sampling_filter_path=None)
    same, _ = _mk_entry(world, [1.0, 1.0])
    await buf.put(same)
    got = await buf.get()
    assert got is same
    assert recycled == []


# --- --max-weight-staleness（fully_async_data_buffer.py:161,get 时消费）----


async def test_max_weight_staleness_consumed_positive(world):
    """正例:staleness=current−oldest 超阈值的组在 get() 被回收(prompt 交
    unused handler),消费者拿到的是新鲜组。"""

    buf, recycled = _mk_buffer(world, max_weight_staleness=2)
    stale, stale_prompts = _mk_entry(world, [0.0, 1.0], versions=("1",))
    fresh, _ = _mk_entry(world, [0.0, 1.0], versions=("5",))
    await buf.put(stale)
    await buf.put(fresh)
    got = await buf.get(current_version=5)  # stale 组 staleness=4 > 2
    assert got is fresh
    assert recycled == [stale_prompts]


async def test_max_weight_staleness_none_negative(world):
    """反例:max_weight_staleness=None(默认)时同样陈旧的组原样返回。"""

    buf, recycled = _mk_buffer(world, max_weight_staleness=None)
    stale, _ = _mk_entry(world, [0.0, 1.0], versions=("1",))
    await buf.put(stale)
    got = await buf.get(current_version=5)
    assert got is stale
    assert recycled == []


# --- --eps-clip / --eps-clip-high（仅 stock PPO,losses.py:214）--------------


def test_eps_clip_consumed_by_stock_ppo_positive(world):
    """正例:stock PPO 消费链 compute_policy_loss 对 eps 变化敏感;
    并锚定唯一 args 级消费点 = losses.py:214。"""

    import torch

    from miles.backends.training_utils.loss_hub.math_utils import compute_policy_loss

    kl = torch.tensor([0.5, -0.5, 0.0], dtype=torch.float64)  # ratio ≈ 0.607/1.649/1.0
    adv = torch.ones(3, dtype=torch.float64)
    tight, _ = compute_policy_loss(kl, adv, 0.2, 0.2, None)
    loose, _ = compute_policy_loss(kl, adv, 1.0, 1.0, None)
    assert not torch.equal(tight, loose)  # clip 区间真实生效
    assert tight[1].item() == pytest.approx(-1.2)  # ratio 1.649 被 clamp 到 1.2

    # 源码锚:args.eps_clip 在 losses.py 恰出现一行,且行号 = 214（vendor 钉死;
    # 漂移即此断言先红,提醒回写 A8 证据）
    losses_py = world.miles_root / "miles" / "backends" / "training_utils" / "loss_hub" / "losses.py"
    hits = [n for n, line in enumerate(losses_py.read_text().splitlines(), 1) if "args.eps_clip" in line]
    assert hits == [214]


def test_eps_clip_dead_config_under_faithful_dis(dis):
    """机械证明(A8):faithful DIS profile 下 eps-clip 全家桶是假配置——
    极端改动 eps_clip/eps_clip_high/eps_clip_c 后,loss、全部 metrics、
    dL/dlogits **逐位**(torch.equal)不变。"""

    torch = dis.torch
    targets = [[0.0, 1.5, -2.0], [0.5, 2.0]]

    def run(**eps_over):
        batch, logits_data = _mk_dis_case(torch, targets=targets)
        logits = logits_data.clone().requires_grad_(True)
        loss, metrics = dis.module.faithful_dis_loss_function(
            _mk_dis_args(**eps_over), batch, logits, _mk_dis_reducer(torch, batch)
        )
        loss.backward()
        return loss.detach(), metrics, logits.grad.clone()

    loss_a, metrics_a, grad_a = run(eps_clip=0.2, eps_clip_high=0.2)
    loss_b, metrics_b, grad_b = run(eps_clip=5.0, eps_clip_high=9.0, eps_clip_c=3.0)
    assert torch.equal(loss_a, loss_b)
    assert torch.equal(grad_a, grad_b)
    assert metrics_a.keys() == metrics_b.keys()
    for k in metrics_a:
        assert torch.equal(metrics_a[k], metrics_b[k]), k

    # 源码面:faithful_dis_loss.py 全文无 eps_clip 读取
    import inspect

    assert "eps_clip" not in inspect.getsource(dis.module)


# --- faithful DIS 自有信任区间（预注册常量,非 CLI 旋钮）---------------------


def test_dis_trust_region_preregistered_consumed_positive(dis):
    """正例:紧贴预注册边界 (0.2,4.0) 两侧的 log-ratio,接受/拒绝计数按常量
    判定翻转——消费的正是 DIS_EPS_LOW/HIGH_PREREGISTERED,与标量权威同源。"""

    torch = dis.torch
    from repoharness2.training.faithful_dis import (
        DIS_EPS_HIGH_PREREGISTERED,
        DIS_EPS_LOW_PREREGISTERED,
    )

    # 同源断言:模块内界 = log(1−0.8), log(1+3.0)
    assert dis.module._LOG_TRUST_LOW == math.log(1.0 - DIS_EPS_LOW_PREREGISTERED)
    assert dis.module._LOG_TRUST_HIGH == math.log(1.0 + DIS_EPS_HIGH_PREREGISTERED)

    # 边界两侧各取一点:1.35/-1.55 在内(界 ≈ (−1.6094, 1.3863)),1.42/-1.65 在外
    targets = [[1.35, 1.42, -1.55], [-1.65, 0.0]]
    batch, logits = _mk_dis_case(torch, targets=targets)
    _, metrics = dis.module.faithful_dis_loss_function(
        _mk_dis_args(), batch, logits, _mk_dis_reducer(torch, batch)
    )
    flat = [t for ts in targets for t in ts]
    expected_accept = sum(1 for t in flat if dis.module._LOG_TRUST_LOW < t < dis.module._LOG_TRUST_HIGH)
    assert expected_accept == 3  # 判例自检:确实两点在外
    assert metrics["dis_accepted_tokens"].item() == expected_accept
    assert metrics["dis_rejected_tokens"].item() == len(flat) - expected_accept


def test_dis_trust_region_boundary_flip_negative(dis):
    """反例:把在外点挪回界内(其余不动),接受计数随之 +2——证明判定确由
    该常量区间驱动,而不是恰好的数据巧合。"""

    torch = dis.torch
    targets = [[1.35, 1.30, -1.55], [-1.50, 0.0]]  # 全部移入界内
    batch, logits = _mk_dis_case(torch, targets=targets)
    _, metrics = dis.module.faithful_dis_loss_function(
        _mk_dis_args(), batch, logits, _mk_dis_reducer(torch, batch)
    )
    assert metrics["dis_accepted_tokens"].item() == 5
    assert metrics["dis_rejected_tokens"].item() == 0


# ===========================================================================
# 三、消费者清单钉死 + loss 显式选择
# ===========================================================================


def test_knob_consumer_file_sets_locked(world):
    """E2 旋钮消费者文件集合逐一钉死（miles 源码树全文扫描;新增/移动消费点
    先红此测试,提醒回写 W0 清单——**不是**通用未消费参数检测器,只锁这五个）。"""

    root = world.miles_root / "miles"
    files = sorted(p for p in root.rglob("*.py"))

    def owners(needle: str) -> set[str]:
        return {
            str(p.relative_to(root))
            for p in files
            if needle in p.read_text(encoding="utf-8", errors="ignore")
        }

    assert owners("grpo_std_normalization") == {
        "utils/arguments.py",  # 定义 + n_samples_per_prompt=1 时强制 False(:3490)
        "ray/rollout/train_data_conversion.py",  # 唯一真消费(:290)
    }
    assert owners("rewards_normalization") == {
        "utils/arguments.py",
        "ray/rollout/train_data_conversion.py",  # 唯一真消费(:314)
    }
    assert owners("max_weight_staleness") == {
        "rollout/fully_async_data_buffer.py",  # fully-async 消费(get,:161)
        "rollout/multi_lora/async_rollout.py",  # multi-LoRA driver 自己的消费面
    }
    assert owners("dynamic_sampling_filter_path") == {
        "rollout/fully_async_data_buffer.py",  # fully-async:put(:133)
        "rollout/sglang_rollout.py",  # 同步 driver(:478)
        "rollout/multi_lora/async_rollout.py",
        "rollout/inference_rollout/inference_rollout_train.py",
    }
    # eps-clip:args 级消费只在 stock PPO(losses.py);math_utils 是纯位置传参被调方
    assert owners("args.eps_clip") == {
        "utils/arguments.py",  # 定义 + eps_clip_high=None 时回填 eps_clip(:3215)
        "backends/training_utils/loss_hub/losses.py",
    }
    assert owners("eps_clip") == {
        "utils/arguments.py",
        "backends/training_utils/loss_hub/losses.py",
        "backends/training_utils/loss_hub/math_utils.py",
    }


def test_loss_selection_explicit_no_unknown_fallback(world):
    """loss/profile 显式选择(A8):未知 loss_type 必炸;custom_loss 显式指到
    faithful DIS 可解析;policy_loss 解析为 stock PPO。
    另:custom_loss + path=None 当前**静默返回 None**(finding W0-F3,
    这里如实断言现状,preflight 须在 rh2 侧补拒绝)。"""

    from miles.backends.training_utils.loss_hub.losses import (
        get_loss_function,
        policy_loss_function,
    )

    from repoharness2.adapters.miles.faithful_dis_loss import faithful_dis_loss_function

    assert get_loss_function(Namespace(loss_type="policy_loss")) is policy_loss_function
    got = get_loss_function(
        Namespace(
            loss_type="custom_loss",
            custom_loss_function_path=(
                "repoharness2.adapters.miles.faithful_dis_loss.faithful_dis_loss_function"
            ),
        )
    )
    assert got is faithful_dis_loss_function
    with pytest.raises(ValueError, match="Unknown loss type"):
        get_loss_function(Namespace(loss_type="totally_unknown"))
    # finding W0-F3:静默 None,不在 get_loss_function 处 fail
    assert get_loss_function(Namespace(loss_type="custom_loss", custom_loss_function_path=None)) is None
