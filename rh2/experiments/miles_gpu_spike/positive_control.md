# GPU spike 正控组预注册（P0-5）

> **口径限定（先读）**：本正控只用于**基础设施验收记账**——证明"当 reward 存在
> 组内方差时，advantage 非零、faithful DIS 产生真实梯度、optimizer/scheduler/
> weight version 正常前进"。它**不得**被表述为任何训练效果、模型能力或 SWE
> 解题率结论（范围建议 §10：本次验证训练链与更新语义，不验证模型能力提升）。
> 依据：tmp/codex_miles_gpu_spike_scope_recommendation_20260826.md §4 P0-5。

## 1. 要解决的问题

真实 SWE 训练早期，同组（同 prompt × n=8 采样）全部失败、reward 全为 0 很常见。
没有正控时，GPU 作业可能只证明"零信号保护会跳过 optimizer"（F2 的
SKIPPED_ZERO_SIGNAL 路径），无法证明"有信号时 optimizer 真的前进"——即
MQ-3 的"正控能真实产生非零梯度并改变参数"缺证据。

## 2. 设计选型（T1 决策，理由记录）

范围建议给了两个方向：(a) 构造任务（一题两解一错）；(b) 既有 S1 探针任务中
已知成败分布的组合。**选 (b)**，理由：

- rh2 任务面是冻结 8 题（`envpack/data/frozen_v1.json`，bringup 按
  metadata.instance_id 反查冻结 BundlePair 且防漂移校验开启）。构造新任务需要
  新 bundle 进 `rh2/src`——超出本次"不碰 src、不建框架"边界，且会在租期前引入
  新的未验证评分面。
- S1-7a 实跑证据（`docs/.../s1/7a_artifacts/artifacts_run8、run9` 的
  bringup_events.jsonl）已给出真实 CC harness + 真实评分下的逐题成败分布，
  可直接作为"已知成败分布"的事实源。

代价与不确定性（如实记录）：(b) 是**概率性**保证，不是逐次确定性保证——见 §4
的失败分支处理。S1 证据来自 Qwen3-4B 主导的探针轮，30B 的逐题成功率会漂移；
方向上 30B 更强，三个候选题难度分布拉开（约 8%/25%/37% 档），同时向"全对"或
"全错"塌缩的概率低。

## 3. 预注册内容

### 3.1 数据文件（钉死，launch preflight 校验 sha256）

`rh2/experiments/miles_gpu_spike/data/gpu_spike_prompts.jsonl`
（sha256 `009b34e547f41e3be4053620d1d73c0967bfb41ee9c2ae02fe9191422c04cdc6`）：
用 `rh2/experiments/s1_7a_bringup/make_prompt_data.py` 从冻结 8 题生成，行 schema
与 S1/J4 完全同源（prompt/label/metadata.instance_id）。8 行全集进 rollout
（`--rollout-batch-size 8` 每轮消费全部 8 组），其中**指定正控实例**与**天然
零方差对照**如下。

### 3.2 正控实例（判定白名单，写死在 thresholds.md `positive_control_instances`）

| instance_id | S1 实跑成败证据（run8/run9，每 run 4 次尝试） | 单次成功率先验 |
|---|---|---|
| `django__django-11099` | run8：1 resolved/3 unresolved；run9：1 resolved/3 unresolved | ≈ 0.25 |
| `django__django-16139` | run8：3 resolved/1 unresolved；run9：0 resolved/4 unresolved | ≈ 0.375 |
| `django__django-11133` | run8：1 resolved/2 unresolved/1 failed_to_grade；run7/9：0 resolved | ≈ 0.08 |

其余 5 题（sympy×2 / requests×2 / astropy）在全部 S1 轮次 0 resolved——它们
既是真实 SWE 环境行为的验证面，也是 F2 语义的**天然阴性对照**：组内 reward
全 0 ⇒ `check_reward_nonzero_std` filter 丢弃或 SKIPPED_ZERO_SIGNAL，
**不得**出现在 applied optimizer step（thresholds.md
`zero_variance_groups_must_not_train`）。

### 3.3 方差概率（n=8/组，按 §2 先验，二项独立近似）

单组"全同 reward"（全成或全败）概率：

- 11099：0.75⁸ + 0.25⁸ ≈ 0.100
- 16139：0.625⁸ + 0.375⁸ ≈ 0.024
- 11133：0.92⁸ + 0.08⁸ ≈ 0.513

三组同时零方差 ≈ 0.100 × 0.024 × 0.513 ≈ **0.0012**（每轮 rollout；G1 至少
3 轮，联合失败概率再降一个量级以上）。即"至少一个正控组产生 reward 方差"在
G1 规模下把握 > 99.8%。先验漂移敏感性：即使 30B 把三题成功率整体推到
0.6/0.8/0.3，三组同轮全同概率仍 < 0.02。

### 3.4 机器判据（写死在 thresholds.md，g1_acceptance.py 执行）

- `positive_control_min_groups_with_reward_std: 1`——整个作业期内，白名单实例
  的组中至少 1 组 reward std > 0；
- 该组必须进入 applied（NORMAL）optimizer step 的训练面（正控的意义就是驱动
  真实梯度）；
- `zero_variance_groups_must_not_train: true`——全等 reward 组一律不得进训。

## 4. 正控失败时的处理（预注册，不现场发明）

若整个 G1 段没有任何正控组产生方差：

1. **区分两种失败**：(a) 三组都全 0/全 1——按 §3.3 概率极低，优先怀疑评分链
   （grading 全挂、reward 恒 0 的管道故障），对照 `bringup_events.jsonl` 的
   `grading.outcome` 判断是评分故障还是真实全败；(b) 评分链正常但分布塌缩——
   记录逐题实测分布，作为先验更新写回本文件（留痕修订）。
2. 允许**只重跑正控三组**一轮（同配置，不改阈值不改数据文件）作为补采；仍无
   方差则 G1 的 MQ-3"正控产生非零梯度"记 **FAIL/未证明**，不得用"零信号保护
   工作正常"替代记绿。
3. 无论哪种情况，不得临时改造 reward、注入假分数或换题——那会把"基础设施
   正控"变成不可审计的现场发明。

## 5. 与 F2 语义的关系（对照表）

| 组形态 | 期望路径 | 验收键 |
|---|---|---|
| 正控组（reward 有方差） | 进 buffer → advantage 非零 → NORMAL step，参数/optimizer/scheduler/version 前进 | `g1_min_applied_optimizer_steps`、`positive_control_min_groups_with_reward_std` |
| 全零/全等组 | filter 丢弃（不进 buffer）或全局零梯度 → SKIPPED_ZERO_SIGNAL，版本不前进 | `zero_variance_groups_must_not_train`、`skipped_rollout_version_must_not_advance` |
