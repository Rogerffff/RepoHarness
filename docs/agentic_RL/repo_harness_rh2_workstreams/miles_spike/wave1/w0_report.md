# W0 算法/config 核对报告(Wave1;06 计划 §3 W0 行 + §1 A8/A6)

- 执行日期:2026-09-02
- 载体:`rh2/tests/adapters_miles/test_w0_knob_consumption.py`(18 个新测试)+ 本报告
- miles 基座:`reference/miles-rh2-integration`,分支 `rh2-integration-v3`(HEAD 63c7a94e7)
- 范围:严格限定 E2 旋钮清单逐一核对 + A6 前提验证 + 两类 loss 消费者清单;**没有**建通用"未消费参数检测器",没有改任何生产源码、既有测试或 reference/ 文件,没有 git 操作。

---

## 0. A6 前提验证结论(首项)

**问题**:miles stock 对 `remove_sample=True` 成员的实际处置是"留组零分母"还是"剔除"?

**实测结论(留组零分母,且分母被静默 clamp)**,消费链逐段锚定:

| 环节 | 代码事实(integration base 行号) | 实测证据 |
|---|---|---|
| conversion 处置 | `miles/ray/rollout/train_data_conversion.py:107-108`:`if sample.remove_sample: sample.loss_mask = [0]*response_length` —— 只置零 loss_mask,**样本行保留在训练批里** | `test_a6_remove_sample_stays_in_group_and_pollutes_baseline`:4 样本组 remove 第 2 个,输出仍 4 行,`loss_masks[2]==[0,0,0]` |
| 组内 baseline | `_post_process_rewards`(:313-314)与 `_normalize_rewards_by_rollout`(:288-293)对**全部**样本取 reward,无任何 remove_sample 检查。上游 `arguments.py:2412` help 文本自己写明:"This attribute does not determine whether the sample participates in advantage normalization" | 同测试:归一化后 rewards 与"含 remove 成员计算的 mean/std"逐位一致,与"剔除它计算"不一致——**remove_sample 的 reward=0.0 确实污染组统计**(A6 拒绝理由成立) |
| 分母出账 | `_compute_rollout_mask_sums`(:209-216)在置零**之后**统计:整条 rollout 被 remove 时 `rollout_mask_sums=0` | 同测试:`td["rollout_mask_sums"] == [3,3,0,3]` |
| 训练侧分母 | reducer `cp_utils.get_sum_of_sample_mean`(`miles/backends/training_utils/cp_utils.py:121`):`torch.clamp_min(denominator, 1)` —— 零分母被**静默 clamp 成 1**,该样本以 0/1=0 的零贡献行通过 stock loss,不产生 NaN、不报警 | `test_a6_stock_reducer_clamps_zero_denominator_to_zero_contribution`:denominators 含 0 时输出有限且恰为非 remove 部分的贡献 |
| faithful DIS 侧 | `rh2/src/repoharness2/adapters/miles/faithful_dis_loss.py` `_validate_rollout_mask_sums`:`rollout_mask_sums < 1` 直接抛 `execution_zero_provenance` | `test_a6_faithful_dis_fail_closed_on_zero_provenance_execution`:同一"全零 mask + 零分母"形状必红 |

**对 A6 断言的支撑**:A6 冻结稿要求"断言 miles stock remove_sample 行为(留组零分母)在我们的准入下不可达"。本轮证实:

1. stock 行为确实是"留组零分母"(不是剔除),且 reward 污染组 baseline——这正是 A6 把"任一 remove_sample 成员 → conversion 前整组拒绝+补采"定为准入规则的事实依据;
2. 即便未来 W1b 准入漏放,faithful DIS profile 下该路径也在 loss 层 fail-closed(`execution_zero_provenance`),不会静默产出零贡献样本——双保险成立;
3. 但 **stock PPO profile 下没有第二道保险**(clamp 静默吞掉零分母,见 finding W0-F1)——若 C 包改选 stock PPO,W1b 组级拒绝是唯一防线,验收 oracle 须单独覆盖这一点(已按 A8"不能继承 faithful DIS 验收结论"口径记入开放问题)。

---

## 1. 每旋钮消费点一览(正例+反例测试均实跑)

| 旋钮 | 真实消费点(行号) | 正例测试 | 反例测试 |
|---|---|---|---|
| `--disable-grpo-std-normalization`(dest `grpo_std_normalization`,默认 True) | `train_data_conversion.py:290`(06 计划锚 :288,integration base 已漂移到 :290,语义不变):grpo/gspo 且组>1 时 ÷(std+1e-6) | `test_grpo_std_normalization_consumed_positive`:True 时归一化含 std 除法,数值逐位对上 | `test_grpo_std_normalization_disabled_negative`:False 时只去均值 |
| `--disable-rewards-normalization`(dest `rewards_normalization`,默认 True) | `train_data_conversion.py:314`:grpo/gspo/reinforce++baseline 且 True 才进归一化分支 | `test_rewards_normalization_consumed_positive`:rewards≠raw_reward 且组内和为 0 | `test_rewards_normalization_disabled_negative`:raw reward 原样透传 |
| `dynamic_sampling_filter_path` | fully-async 权威消费点 = `fully_async_data_buffer.py:117`(装载)+ `:133`(put 时调用);另有三个**不同 driver** 的消费点(见 §3 澄清) | `test_dynamic_filter_consumed_in_async_buffer_positive`:配 stock `check_reward_nonzero_std`,零方差组 put 即丢弃(不回收、drop 计数进 metrics) | `test_dynamic_filter_none_negative`:path=None 时恒 keep |
| `--max-weight-staleness`(默认 None) | `fully_async_data_buffer.py:161`(**get 时**消费:`staleness = current_version − min(oldest_weight_version)` 超阈值回收给 unused handler) | `test_max_weight_staleness_consumed_positive`:staleness=4>2 的组被回收,消费者拿到新鲜组 | `test_max_weight_staleness_none_negative`:None 时同样陈旧的组原样返回 |
| `--eps-clip`/`--eps-clip-high`(默认 0.2/回填) | **仅** `losses.py:214`(stock PPO `policy_loss_function`)经 `compute_policy_loss`(`math_utils.py:263`)消费;06 计划锚 :213,实为 :214 | `test_eps_clip_consumed_by_stock_ppo_positive`:clip 区间变化真实改变 loss;并断言 `args.eps_clip` 在 losses.py 恰好出现一行且行号=214 | `test_eps_clip_dead_config_under_faithful_dis`:见 §2 机械证明 |
| faithful DIS 信任区间 | 预注册常量 `DIS_EPS_LOW/HIGH_PREREGISTERED = 0.8/3.0`(`repoharness2/training/faithful_dis.py:66-67`),开区间 (0.2,4.0);`faithful_dis_loss.py:172-173` log 空间同源换算,**无 CLI 旋钮** | `test_dis_trust_region_preregistered_consumed_positive`:紧贴边界两侧(1.35/1.42、−1.55/−1.65)的 log-ratio,接受计数按常量判定;并断言模块内界与预注册常量同源 | `test_dis_trust_region_boundary_flip_negative`:把界外点移回界内,接受计数随之翻转(排除数据巧合) |

---

## 2. 两类 loss 的真实消费者清单(A8 W0 落地)

### faithful DIS profile
接线:`--loss-type custom_loss --custom-loss-function-path repoharness2.adapters.miles.faithful_dis_loss.faithful_dis_loss_function`(`losses.py:522-523` custom_loss 分支 → `load_function`)。

- **算法参数**:信任区间 = 预注册常量(0.8/3.0,与标量权威 `faithful_dis_loss_by_execution` 同源 import,写死无开关);分母语义 = `provenance_tokens` 预注册。
- **batch 列**:`rollout_log_probs`(behavior)、`advantages`、`loss_masks`、`rollout_mask_sums`(execution 分母,fail-closed 核账)、`rollout_sampling_mask_ids/offsets`、`unconcat_tokens`、`response_lengths`、`total_lengths`;`sample_indices`/`leaf_ordinals` 仅事件层。
- **args 消费**:`rollout_top_p`(replay 开关,必须 <1.0 否则 fail-closed)、`rollout_temperature`、`vocab_size`、`qkv_format`、`true_on_policy_mode`、`log_probs_chunk_size` 等 logprob 计算路径参数;`calculate_per_token_loss` 必须 False;环境变量 `MILES_EXPERIMENTAL_FT_TRAINER` 必须关。
- **明确不消费**:`eps_clip`/`eps_clip_high`/`eps_clip_c` 全家桶。

### stock PPO profile
接线:`--loss-type policy_loss`(默认)→ `policy_loss_function`(`losses.py:64`)。

- **clip 参数**:`args.eps_clip`/`args.eps_clip_high`/`args.eps_clip_c`,唯一消费点 `losses.py:214` → `compute_policy_loss`。
- 其余专属面(未逐一测,列作清单):`kl_loss_type`/`use_kl_loss`/`kl_loss_coef`、`entropy_coef`、`use_opsm`、`use_tis`/`get_mismatch_metrics`/`custom_tis_function_path`、`use_rollout_logprobs`、`skip_actor_forward_only`(且 `arguments.py:3575` 断言它只兼容 policy_loss)。

### 两 profile 共用的上游面(与 loss 选择无关)
`grpo_std_normalization`、`rewards_normalization`(conversion 层);`dynamic_sampling_filter_path`、`max_weight_staleness`(buffer 层);`rollout_mask_sums` 生产(conversion :112)。这些在两个 profile 下都真实生效,不属于"互斥参数"。

### "faithful DIS profile 下填 eps-clip 即假配置"的机械证明
`test_eps_clip_dead_config_under_faithful_dis` 三层证明,全部通过:

1. **行为层(逐位)**:同一 batch/logits,args 只把 `eps_clip 0.2→5.0`、`eps_clip_high 0.2→9.0`、增设 `eps_clip_c=3.0`,loss、全部 metrics、`dL/dlogits` 用 `torch.equal` **逐位**相等(不是 allclose);
2. **源码层**:`inspect.getsource(faithful_dis_loss)` 全文无 `eps_clip`;
3. **全树扫描层**:`test_knob_consumer_file_sets_locked` 钉死 `args.eps_clip` 在 miles 树内只出现在 `losses.py`(消费)与 `arguments.py`(定义+回填),消费点集合有增删会先红此测试。

---

## 3. Findings(如实记录,未修任何 miles 源码)

| 编号 | 内容 | 分类建议 |
|---|---|---|
| **W0-F1** | stock 训练侧零分母被静默吞:`cp_utils.py:121` `clamp_min(denominator,1)` 把整 rollout 被 remove 的零分母 clamp 成 1,样本以零贡献行静默通过 stock loss,无警告无指标。faithful DIS 有自己的 fail-closed;**stock PPO profile 没有** | 静默 fallback。faithful DIS profile 下无影响(loss 层拦截);若 C 改选 stock PPO,须把"remove_sample 组级拒绝"列入其独立验收 oracle |
| **W0-F2** | `arguments.py:3490-3491`:`n_samples_per_prompt==1` 时**强制** `grpo_std_normalization=False`,静默覆盖用户显式传入的值(只打一行 info 日志) | 静默覆写。首训 profile n_samples_per_prompt>1,当前不可达;launch preflight 应把"声称的 std normalization 与实际生效值"对账 |
| **W0-F3** | `losses.py:522` + `load_function`(路径为空返回 None):`--loss-type custom_loss` 而 `--custom-loss-function-path` 未设时,`get_loss_function` **静默返回 None**,失败推迟到训练首次调用点(TypeError),不在配置期 fail。已在 `test_loss_selection_explicit_no_unknown_fallback` 里如实断言现状 | 静默 fallback,正中 A8"未知 loss、静默 fallback 均使 preflight 失败"条款——须由 rh2 侧 preflight 拒绝(载体见开放问题 ①) |
| **W0-F4** | `arguments.py:3215-3216`:`eps_clip_high=None` 时静默回填为 `eps_clip` | 低危、行为与 help 文本一致;记录备查(对 stock PPO profile 的 launch 参数表要写"实际生效值") |
| **W0-F5** | 多消费点澄清(**非**同 run 双重消费):`dynamic_sampling_filter_path` 有 4 个消费点、`max_weight_staleness` 有 2 个,分属不同 rollout driver(fully-async buffer / 同步 `sglang_rollout` / multi-LoRA / inference_rollout)。单一运行模式下各只有一个生效;fully-async 首训 profile 的权威消费点 = `fully_async_data_buffer.py`。消费者文件集合已由 `test_knob_consumer_file_sets_locked` 钉死 | 澄清,无需处置 |
| **W0-F6** | 06 计划行号锚点漂移:`--disable-grpo-std-normalization` 消费点计划写 `train_data_conversion.py:288`,integration base 实为 `:290`;eps-clip 计划写 `losses.py:213`,实为 `:214`。语义均不变(vendor refresh 引起的行漂移) | T2 级;回写载体 = 本报告(06 计划文档不在本包可写路径内,待 owner 或后续批合并锚点) |

---

## 4. 协作协议五段收尾

**① 待拍板 T0**:无。本轮纯核对+测试,未触碰任何公共 schema、训练语义、准入路径。

**② T1 决策及理由**
- 测试文件放在 `rh2/tests/adapters_miles/`(而非 tests/ 顶层新目录):复用该目录 conftest 的 vendor slime 世界、ray/sglang stub 与 `RH2_MILES_PATH` 重定向机制,避免重复搭一套 miles 装配;整个模块打 `integration_base` 标记,默认 pin base 下自动 skip(与既有 delta 测试同规)。
- "消费者清单钉死"用**枚举五个旋钮的文件集合断言**实现(`test_knob_consumer_file_sets_locked`),不是通用检测器——集合有增删测试先红,提醒回写清单,符合 A8"范围限定 E2 旋钮清单"的边界。
- eps-clip 行号锚(=214)写成精确断言:vendor 已钉死在 rh2-integration-v3,行号漂移应当显式红灯而不是静默跟随。
- W0-F3(custom_loss 静默 None)在测试里**如实断言现状**而不是断言"应当抛错":W0 不修 miles 源码,现状断言保证未来 vendor 行为变化可见。

**③ 临时挡板新增/命中/解除**:无新增挡板;未命中既有挡板。

**④ 推翻或修正了哪些旧结论**
- 修正 06 计划两处行号锚(288→290、213→214,见 W0-F6),语义结论不变。
- 细化 A6 表述:stock"留组零分母"的完整语义是"留组 + loss_mask 全零 + reward 污染 baseline + 训练侧分母被 clamp 成 1 的**静默零贡献**"——比计划文本里"留组零分母"多出"分母被 clamp、不产生 NaN"这一层事实(W0-F1),对 stock PPO 备选路线有验收含义。

**⑤ 测试/证据/账本状态**

```
# integration base(权威运行形态)
cd rh2 && RH2_MILES_PATH=$REPO/reference/miles-rh2-integration \
  uv run pytest tests/adapters_miles/test_w0_knob_consumption.py -q
# => 18 passed, 14 warnings in 1.70s

# 默认 pin base:整模块自动 skip(integration_base 标记生效)
cd rh2 && uv run pytest tests/adapters_miles/test_w0_knob_consumption.py -q
# => 18 skipped in 0.01s

# 全目录回归(不污染既有测试;403 旧 + 18 新)
cd rh2 && RH2_MILES_PATH=$REPO/reference/miles-rh2-integration \
  uv run pytest tests/adapters_miles -q
# => 421 passed, 17 warnings in 14.93s

cd rh2 && uv run ruff check tests/adapters_miles/test_w0_knob_consumption.py
# => All checks passed!
```

**开放问题**
1. **preflight 载体**(W0-F3/F2/F4 的处置点):A8 要求"未知 loss、两套互斥参数同时声称生效、静默 fallback 均使 preflight 失败",W0 只交付事实清单与测试;拒绝逻辑落在哪个包(建议 W7 launch preflight 引用本报告 §2 清单)待 owner 确认。
2. **stock PPO 备选路线的 remove_sample 防线**(W0-F1):若 C 包改选 stock PPO,W1b 组级拒绝成为唯一防线,其独立 GPU oracle 须显式覆盖"remove_sample 组不得入训"(与 A8"不能继承 faithful DIS 验收结论"同源)。
3. 06 计划行号锚回写(W0-F6):本报告已记录,计划文档本身的修订归下一次计划文档维护批。

**本轮没有改变哪些已定案语义**:A6 成员语义(冻结稿原样)、A8 配置真实性条款、faithful DIS 的信任区间数值/分母语义/fail-closed 面、miles vendor 树(零改动)、既有 421 项测试的任何 oracle。
