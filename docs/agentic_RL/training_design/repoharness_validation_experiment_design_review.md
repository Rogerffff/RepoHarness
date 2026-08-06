# RepoHarness 验证实验设计决策底稿审查与补充建议

审查对象：`docs/agentic_RL/training_design/repoharness_validation_experiment_design.md`

审查时间基线：初版 2026-07-07；S0 后修订 2026-07-08

本文审查实验设计决策底稿，不替换原文，不修改实现代码。2026-07-08 补充读取了 rh2 S0 阶段的完整产物，并把已经由 S0 消除的未知从“待验证”改为“已定案”或“后续阶段待关闭”。结论来自四类材料交叉检查：

1. 本地设计文档与技术报告摘录，包括 `repo_harness_design_doc2_verifiers_based.md`、`repo_harness_final_review_before_implementation.md`、`glm5.2_blog_RL.md`、warm-start 设计文档，以及 `external_paper_references` 目录下的技术报告索引。
2. 本地参考代码库，包括 `reference/verifiers`、`reference/renderers`、`reference/slime`、`reference/prime-rl`。
3. 公开资料补充核查，包括 GLM-5.2、DeepSWE、SkyRL-Agent、SERA、SWE-Gym、R2E-Gym、SWE-Master、OpenHands RFT、SWE-Bench Pro 等。
4. rh2 S0 阶段 evidence，包括 `s0_acceptance_summary.json`、`v2_renderer_report.md`、`v3_protocol_report.md`、`topology_ab_report.md`、`swe_smoke_report.md`、`s0_8_expdesign_review.md`。

## 0. S0 后修订结论

S0 已完成，`rh2_s0_complete = true`。S0 的核心判定是：

```text
V1 依赖与 Docker 使用层：通过
V2 renderer：通过，Qwen3-30B-A3B 精确命中 Qwen3Renderer
V3 token 协议链路：通过，vLLM /inference/v1/generate + TrainClient 全链 token 保真成立
V4 MoE 张量穿透：通过，但形态 B 被定为 MoE 训练主形态
```

因此，本文初版中几个“需要 S0 验证”的判断已经可以收口：

1. **训练链路选择已有阶段性结论**：首个 MoE RL 训练主形态应改为 **形态 B：SGLang + slime patch 镜像的原生 `/generate` 路径**。形态 A（verifiers 中心 + vLLM `/inference/v1/generate`）保留为协议基线、dense/eval/调试路径。
2. **分水岭不是 routing tape，而是 top-p tape**：S0 证明两条形态都能拿到 routing tape；top-p tape 在 stock vLLM 与 stock SGLang 中都不是开箱即用。形态 B 有 slime 维护的 SGLang patch 与镜像，形态 A 则需要改推理引擎、wire schema 与消费端，工程代价明显更高。
3. **模型选择基本收口为 Qwen3-30B-A3B**：V2 证明 hand-coded renderer 覆盖，V3/V4 证明真实端点 token/logprob/routing 可行。35B-A3B 升级应推迟到 S4 前预实验，不进入第一轮默认方案。
4. **算力判断需要更保守**：S0 只验证了单卡 96GB 推理侧，不等于验证了 8 卡训练侧。多卡训练、权重同步、slime 镜像在 sm_120 上的实际可用性分别留给 U-C 与 U-H。
5. **SWE smoke 的 7/8 解出不能作为能力基准**：deepseek-chat 明显存在 SWE-bench 题目污染或背题嫌疑。S0-7 只能证明链路、评分和 F2P/P2P 判据工作，不能证明目标模型能力。

所以，实验决策的最新判断应写成：

```text
首训主链路：
  slime 原生形态 B + Claude Code harness + Qwen3-30B-A3B + GRPO。

评测与治理：
  train=evaluate 同 harness；
  形态 A 只作为协议基线和可审计对照，不承担 before/after 主口径。

必须先关的未知：
  U-H：slime patch 镜像在 sm_120 / Blackwell 上可用，并能产出 top-p tape；
  U-C：8 卡训练侧吞吐、显存、权重同步和 CPU offload 可接受。
```

## 1. 总结论

当前实验设计底稿的主方向不需要推翻。它选择“小规模可信闭环先行”的方式，而不是一开始追求完整大规模训练，这一点是正确的。它把训练目标限定在软件工程任务，把训练数据与评测数据分离，把 outcome reward 绑定到 clean grading，把 anti-cheat、环境验证、eligibility gate 和 artifact governance 作为分数可信性的组成部分，这些方向都符合目前公开大厂经验。

我赞成保留的核心路线是：

```text
首训目标：Qwen3-30B-A3B，35B-A3B 推迟到 S4 前预实验
训练链路：形态 B，即 slime 原生 SGLang /generate 路径作为 MoE RL 主形态
算法起点：首版关 compaction，用 GRPO / GRPO++ 风格配置起步
数据路线：SWE-Gym / R2E-Gym 等开源可执行任务起步，不使用 SWE-bench Verified 训练
评测方式：同一 harness 的 before/after 配对评测，辅以治理证据
治理边界：clean grading、anti-cheat、hidden verifier 隔离、eligibility gate 不可省略
```

S0 后仍然需要修正的重点变成：

1. `verifiers + renderers` 与 `slime coding_agent_rl` 仍然不是同一条现成链路。S0 的结论不是“它们已经接好了”，而是“为了 MoE 首训，应走 slime 原生形态 B；治理层通过中立 `TrajectoryProjection` 兼容两条形态”。
2. MoE routing 已经动态验证通过；top-p tape 才是真正分水岭。正式实现必须 pin slime patch 镜像，并在启动时用 `top_p < 1.0` 探针 fail closed。
3. SWE-bench Verified 适合作为内部快速 before/after 信号，但不能单独作为“真实世界能力证明”。实验叙事应明确它是内部 sanity check，并增加 SWE-Bench Pro public 小集、Terminal-Bench Pro 小集或其他可信补充评测面。

## 2. 必须修正的问题

### 2.1 形态 A / 形态 B 的边界需要重新写清楚

底稿在 E7 中写：

```text
形态 A（verifiers TrainClient + 协议 shim）vs 形态 B（slime custom_generate 直调）
```

这个拆分本身正确，但原文容易让读者误解为：形态 B 已经天然继承了 renderers 风格的 token fidelity。实际代码并不是这样。

本地代码显示：

- `verifiers` 的 `TrainClient` 明确是“render prompt to token ids，然后调用 vLLM `/inference/v1/generate`”的路径，并且当前只支持 chat-completions dialect。参考 `reference/verifiers/verifiers/v1/clients/train.py`。
- `slime` 的 coding-agent adapter 使用 tokenizer 的 `apply_chat_template` 渲染 prompt，而不是调用 `renderers` 的 hand-coded renderer。参考 `reference/slime/slime/agent/adapters/common.py`。
- `slime` 的黑盒 adapter 调 SGLang `/generate` 后，目前读取的是 `output_ids` 与 `output_log_probs`，没有在该 adapter 层显式看到 top-p token tape 或 routed experts 的完整透传。

建议把 E7 改成三条路径，而不是二选一：

```text
路径 1：verifiers + renderers + prime-rl/offline export
  目标：最强 token fidelity、Trace 可审计性、离线训练样本可解释性。
  风险：接 slime / SGLang 需要协议 shim 或新 TrainClient。

路径 2：slime coding_agent_rl custom_generate
  目标：最快跑通黑盒 coding-agent 在线训练。
  优势：SGLang 原生、GRPO/GSPO/PPO 训练后端成熟、Claude Code / Codex harness 示例现成。
  S0 后状态：routing 已动态验证可取；top-p tape 依赖 slime patch 镜像，
    U-H 必须在 S1 关闭；renderer bridge 不来自 renderers，而由
    slime TrajectoryManager / RepoHarness TrajectoryProjection 承担等价治理。

路径 3：RepoHarness governance layer
  目标：sandbox、clean grading、hidden verifier、anti-cheat、eligibility、artifact projection。
  边界：不假设 verifiers 或 slime 已经完整提供这些治理能力。
```

### 2.2 S0 后 MoE 形态已经定案：形态 B 是首训主形态

底稿把 MoE 与形态 B 绑定得比较强，这个倾向已经被 S0 动态验证支持。现在不应再写成“优先验证形态 B”，而应写成：

```text
形态 B 是 Qwen3-30B-A3B 首训的主形态；
形态 A 保留为协议基线、dense/eval/调试路径。
```

S0 的关键事实是：

```text
routing tape：
  形态 A 和形态 B 都能拿到；
  两侧 wire 形状不同，但都可归一到 TrajectoryProjection。

top-p tape：
  stock vLLM 与 stock SGLang 都不是开箱即用；
  形态 B 有 slime 维护的 sglang-top_p.patch 与官方镜像；
  形态 A 需要改引擎、wire schema、消费端三处，工程成本高。

正式实现要求：
  pin slime patch 镜像；
  服务启动后立刻跑 top_p < 1.0 探针；
  如果 meta_info 缺 top_p_token_ids / top_p_token_offsets，直接 fail closed。
```

仍需注意：形态 B 的 `Sample` 不是审计 artifact。RepoHarness 的治理事实仍应进入中立 `TrajectoryProjection`，不能散落在 slime 训练后端 adapter 中。

### 2.3 附录 A 的 reward/K 分摊说法需要删除

底稿附录 A 写：

```text
fan-out：每条 root-to-leaf 一个 Sample，
reward/K 分摊，siblings 共享 rollout_id
```

这和 slime 当前代码不一致。`reference/slime/slime/agent/trajectory.py` 的注释明确说明：每个 routing leaf 产出的 Sample 都拿到完整 trajectory reward，不按分支数切分。正确理解应是：

```text
同一个 rollout 如果因为 compaction 或 sub-agent fan-out 产生多个 sample，
这些 sample 共享 rollout_id。
reward 对每个 emitted sample 是完整轨迹 reward。
训练侧需要通过 rollout_id、rollout_loss_denominator 或等价机制控制分母，
避免把同一次环境执行因为分裂成多个 sample 而过度计权。
```

这个点很重要，因为它直接影响 reward attribution、advantage broadcast 和 loss denominator 的解释。建议原文把“reward/K 分摊”改成“完整 reward + rollout_id 分母治理”。

### 2.4 `verifiers bash_edit harness` 是过期名称

底稿 E10 仍写 `verifiers bash_edit harness`。最新 `verifiers` 中当前主路径应描述为：

```text
verifiers default harness：
  默认提供 bash；
  edit 默认开启；
  search 默认关闭；
  纯无工具对照是 null harness。
```

相关代码位置：

- `reference/verifiers/verifiers/v1/harnesses/default/harness.py`
- `reference/verifiers/verifiers/v1/harnesses/null/harness.py`

建议原文统一改成：

```text
形态 A → verifiers default harness（edit=true，search=false 起步）
```

不要再使用 `bash_edit harness` 这个名称。

### 2.5 Verified 评测叙事需要降级为内部信号

底稿 E5 / E8 对 SWE-bench Verified 的使用方向基本正确：不用它训练，只用它做 held-out before/after。问题是叙事上不能让 Verified 单独承担“真实世界能力证明”的重量。

公开资料显示，SWE-bench Verified 仍有生态价值、成本低、便于做内部配对评测，但它已经不足以独立代表前沿 coding agent 能力。建议改成：

```text
主评测：
  SWE-bench Verified held-out 小集。
  目的：内部快速信号、配对 before/after、检查训练是否真的改善同一 harness 下的求解能力。

可信补充：
  SWE-Bench Pro public 小子集，或 Terminal-Bench Pro 小子集，或另一个更干净的小型 held-out 集。
  目的：证明结果不是只在 Verified 的已知生态里波动。

叙事限制：
  不写“Verified 提升证明真实世界 coding 能力已提升”。
  应写“在 clean grading、anti-cheat、数据去污和同 harness 控制下，训练信号产生了统计上可辨别的能力变化”。
```

另外，E8 中关于 “Qwen3 Figure 7：不带 hack blocker 时分数虚高到 84.6%，真实 75.1%” 这组具体数字，本轮公开资料核查没有直接定位到可引用来源。建议要么补出明确来源，要么删除具体数字，只保留结论：

```text
没有 blocker 时，agent 会学会通过 git/curl 等方式回捞 ground truth；
加入 heuristic blocker 后，人工检查显示 reward hacking 基本被消除。
```

### 2.6 直接 RL 可以保留，但 RFT / SFT baseline 不应被低估

我同意底稿 E3 的主决策：第一次实验可以先从 instruct checkpoint 直接做 RL，因为 slime 的 coding-agent 示例与 DeepSWE 路线给了这个模板。

但需要补充一条：公开经验中，RFT / SFT / agentic mid-training 仍然是非常强、非常便宜的基线或回退路径。OpenHands RFT、SWE-Gym、SERA、SWE-Master 等资料都说明，小规模高质量轨迹微调经常能带来显著收益，而且工程复杂度比在线 RL 低。

建议不要把首训改成“必须先 SFT”，但要增加两个机制：

```text
Pre-RL 行为诊断：
  正式 RL 前先跑 20~50 题，每题 2~4 条 rollout。
  记录工具格式错误率、有效 patch 率、非零方差组比例、平均轨迹长度、infra_failure 率。
  如果模型连基本工具协议都不稳定，不等 20 个 RL step，直接触发小 SFT / RFT。

RFT / SFT 对照：
  若时间允许，产出一个小型 rejection fine-tuning 或 agentic SFT baseline。
  它不一定进入首训主链路，但可以防止最后出现“RL 提升不如简单 SFT”的解释漏洞。
```

### 2.7 硬件可行性：S0 只验证了推理半边，训练半边仍是 U-C

底稿把 C1 写成 8 张 RTX Pro 6000 Blackwell、单卡 96GB、PCIe、无 NVLink、colocate 与 CPU offload，这是正确约束。但 S0 的实测范围比底稿原先设想更窄：S0 只在单卡 96GB 上验证了 30B-A3B 推理侧可加载、vLLM 0.24.0 可用、SGLang 原生 `/generate` 可产出 token/logprob/routing。

因此现在应把 C1 写成：

```text
推理侧：
  S0 已证明单卡 96GB 可跑 Qwen3-30B-A3B bf16 推理，
  Blackwell 稳定参数组合已记录。

训练侧：
  8 卡训练、权重同步、CPU offload、PCIe 通信、SGLang/slime 镜像在 sm_120 上的真实表现仍未验证。
  该未知编号为 U-C / U-H，不得在实验设计里写成已通过。
```

S4 前预实验至少要补：

```text
1 step × 8 prompt × n=2/4 最小训练冒烟；
真实 32K 或接近 32K 的压力样本；
slime patch 镜像在 sm_120 上启动与 top-p tape 探针；
8 卡权重同步与训练 step 墙钟；
显存峰值、CPU 内存峰值、吞吐 token/s、失败类型统计；
  生成 / 沙箱执行 / 评分 / 训练 step 四段墙钟分解；
```

### 2.8 “关 compaction ↔ GRPO”必须写成硬前提

底稿的算法判断是合理的：首版关 compaction，用 GRPO 起步；如果未来开 compaction 或 sub-agent fan-out，再评估 PPO。

需要补充的是：如果走 slime Claude Code / Codex 黑盒 harness，必须确认 auto-compaction、sub-agent dispatch 或 compact trajectory 是否真的关闭或不会触发。否则“组内每条 rollout 可比较”的 GRPO 语义会变弱。

建议写成：

```text
GRPO 首训的硬前提：
  1. 不启用 compaction；
  2. 不把一个 rollout 切成多个训练 sub-trace，或至少训练侧有清晰 denominator 治理；
  3. 超上下文、超步数、超时轨迹只做 loss mask / eligibility 拒绝，不把 reward 盲目广播到不可训练片段；
  4. 如果必须启用 compact trajectory 或 sub-agent fan-out，E2 自动回到“重新评估 PPO / critic / compact filtering”的状态。
```

## 3. 可以保持不变或基本同意的设计

### 3.1 S1 基础设施冻结集与正式训练集分开

底稿把 20~50 题的 S1 基础设施集与正式训练集拆开，这是正确的。S1 可以使用 SWE-bench Verified 做基础设施 bring-up，因为该阶段不训练；正式训练集不使用 Verified，从源头避免训练/评测污染。

### 3.2 数据路线选择合理

以 SWE-Gym Lite 起步，再扩到 SWE-Gym 全量与 R2E-Gym-Subset，是当前最稳的开源路线。SWE-smith 可作为多样性补充，SWE-rebench 如果只做时间去污而与 Verified 仓库重叠，则默认排除。这些判断都合理。

建议保留底稿中的三段式数据策略：

```text
首训：开源可执行任务，小规模闭环。
并行：agent 自产任务流水线，作为环境生产线证明。
扩容：任务数消融，比较 200 题档与 1000~2000 题档。
```

### 3.3 outcome reward 只能来自 clean grading

底稿把 clean grading + verifier 作为 outcome reward 的唯一来源，这是必须坚持的。过程惩罚可以是独立 reward component 或 token_penalty_spans，但不能篡改 outcome 成败判定。

我赞成原文采用更保守的一侧：

```text
未完成 / 超限轨迹：
  mask loss 或 eligibility 拒绝，不污染 outcome reward。

tool-format 违规：
  作为独立负分量或 token-level negative advantage 透传，
  不回写成“任务失败 reward=0”的假事实。
```

### 3.4 动态采样应作为首训默认项

GRPO 在 SWE 任务上很容易产生全 0 或全 1 的零方差组。底稿把 slime 的 dynamic sampling 从“触发式”升级为首训默认开，我赞成。需要注意的是，如果动态采样导致有效样本不足，应优先提高过采样倍率或调整任务池难度，而不是把组尺寸从 n=8 降得太低。

### 3.5 同 harness 训练与评测优先

第一次实验的目标不是证明跨 scaffold 泛化，而是证明 RepoHarness 治理设施能让训练信号可信地产生可观测提升。因此采用单 harness、train=evaluate 的 Composer 式路线是合理的。

建议保留 optional transfer gap 测量，但不要把它作为成败判据。

### 3.6 用户模拟与权限任务不进第一次实验，但 Anti-Hack 必须进

E9 把用户模拟与权限任务推迟到第二轮实验，我赞成。它们会引入额外 reward 维度与交互复杂度，不适合首训。

但 Anti-Hack 不应被归入“后续复杂任务”。它是训练信号可信性的安全边界，应该进入第一次实验的治理证据包，至少包括：

```text
git 历史 / 远端下载拦截；
protected artifact 访问拦截；
GitHub raw / Pages / upstream commit 回捞拦截；
test tamper 检测；
红队环境包全拦截率；
被拦截后的 dummy observation 与 rollout 是否继续。
```

## 4. 按 E1 到 E10 的具体审查意见

### E1 训练目标模型

S0 后，E1 可以从“候选倾向”收口为：**Qwen3-30B-A3B 是第一轮默认训练目标**。理由是 V2 已证明 `Qwen/Qwen3-30B-A3B` 精确命中 `Qwen3Renderer`，V3 已证明真实端点 token/logprob/Trace identity 可行，V4 已证明 MoE routing 动态可取。

E1 仍需保留两个守门条件：

```text
U-G renderer 守门：
  本地路径加载可能静默降级 DefaultRenderer；
  所有训练脚本必须用 HF id 或显式 renderer config，
  并启动断言 renderer class == Qwen3Renderer。

35B-A3B：
  不进入首训默认项；
  仅在 S4 前预实验确认显存、吞吐和镜像兼容后升级。
```

### E2 算法族与后端配置

我赞成 GRPO 起步，尤其是 n=8、KL 关、entropy 关、不除 reward std、dynamic sampling 默认开这些选择。

需要改写的地方是：不要把 PPO 只写成远期抽象可能性。应明确：

```text
只要开启 compact trajectory、sub-agent fan-out 或长上下文切段训练，
PPO / critic / compact filtering 就从“以后可选”变成“必须重新评估”。
```

### E3 warm-start / SFT

直接 RL from instruct 可以作为第一路径，但建议增加 pre-RL 行为诊断。当前“前 20 步失败再回退”的触发点可能偏晚，因为一个 step 的 rollout 墙钟可能很高，20 步可能已经消耗数天。

建议在正式训练前增加：

```text
20~50 题 × 每题 2~4 条 rollout 的行为诊断；
如果工具格式错误率高、有效 patch 率低、非零方差组比例低，
直接做 1k~5k 轨迹的小型 SFT / RFT，再进入 RL。
```

### E4 训练数据

我同意开源数据先行、自建任务并行的策略。

需要补充的是：数据冻结必须产出机器可检查的 `dataset_freeze_report`，而不是只在文档中列检查清单。至少包含：

```text
数据源版本；
实例 id 列表；
repo / base_commit；
与 Verified 仓库交集断言；
泄漏字段剥离报告；
problem_statement 泄漏扫描报告；
golden patch / empty patch / deterministic rerun 结果；
跨源去重结果；
license 风险摘要。
```

### E5 评测协议

Avg@n、paired bootstrap、30 题 n=8 可分辨约 8~10 个百分点，这些设计合理。

需要补充的是：

```text
30 题 × n=8 只能验证大幅提升。
如果预期提升低于 8 个百分点，应扩大到 50 题或 n=16。
如果要对外表达“能力提升”，需要加入 SWE-Bench Pro public 或 Terminal-Bench Pro 小集。
```

另外，E8 中仍出现 pass@1 口径，应统一改成 Avg@n，best-of-K 单独报告。

### E6 rollout / 训练预算与上下文

32K 起步、30~50 步首训档、600~900 秒 agent budget，这些选择现实。

建议把 timing 指标提升为首训必采，不只是后续优化项：

```text
env_reset_seconds
image_pull_seconds
agent_seconds
tool_execution_seconds
grading_prep_seconds
grading_test_seconds
training_step_seconds
queue_wait_seconds
infra_failure_category
```

公开经验反复说明，coding-agent RL 的瓶颈经常不是纯 GPU 训练，而是容器启动、工具执行、评分尾波、镜像拉取和坏环境重试。

### E7 接入形态

S0 后，E7 应直接定案为：

```text
MoE 首训主形态：
  形态 B，即 SGLang + slime patch 镜像的原生 /generate 路径。

形态 A：
  保留为协议基线、dense/eval/调试路径；
  不承担第一轮 Qwen3-30B-A3B MoE RL 主链路。

治理层：
  不直接绑定 verifiers Trace 或 slime Sample；
  全部经 TrajectoryProjection 中立契约。
```

### E8 成功证据

三件套方向正确：

```text
能力证据；
治理证据；
解耦证据。
```

建议把解耦证据分层：

```text
形态 A：
  可以要求 token ids、loss mask、logprobs、reward facts 的严格 parity。

形态 B：
  先要求语义 parity：
    rollout_id / group_id 一致；
    reward facts 一致；
    eligibility 一致；
    rejection reason 一致；
    loss denominator 解释一致；
    governance sidecar 一致。
  不应要求它和 verifiers Trace JSON 在 token 级逐位相同，除非我们额外实现共享 renderer adapter。
```

### E9 用户模拟与权限任务

同意不进入第一次训练。建议在文档中明确区分：

```text
权限任务 / 用户模拟：第二轮实验。
Anti-Hack / protected artifact / GitHub 回捞拦截：第一轮实验的安全边界。
```

### E10 harness / scaffold

我赞成单 harness、train=evaluate。

S0-8 已经把 E10 收口为：**训练与 before/after 评测使用同一 harness，首选 slime Claude Code harness；形态 A 不承担主 before/after 口径**。如果后续因为可安装性、许可或稳定性改用 Codex harness，也必须同步改训练与评测，不允许训练用 Claude Code、评测用另一套 scaffold 后还把结果解释为同一能力变化。

```text
形态 B：
  slime Claude Code harness 为当前推荐主口径；
  Codex harness 是同层候选，但不能混用到同一 before/after 主实验。

形态 A：
  verifiers default harness（edit=true，search=false 起步）只作为回退或对照；
  若切形态 A，报告必须显式标注 scaffold 已改变。

不建议：
  mini-swe-agent / bash-only 作为首训主 harness。
  它适合作为极简 baseline 或 transfer gap 对照，不适合作为最小可信能力训练主路径。
```

## 5. 基础设施支持性判断

### 5.1 verifiers

`verifiers` 足以作为 RepoHarness 新架构的核心参考。它已经实现了 Taskset / Harness / Runtime / Trace / EnvServer 的成熟分层，Trace branch 可以自然表达一条训练样本。

可依赖的设计思想：

```text
Taskset 拥有任务数据与评分逻辑；
Harness 驱动模型尝试任务；
Runtime 提供运行位置；
Trace 用消息图表达 rollout；
branch 作为训练样本；
TrainClient 通过 renderer 获得 token ids、mask、logprobs。
```

不能照搬或需要补的部分：

```text
verifiers Runtime 不是完整安全沙箱；
TrainClient 当前偏 vLLM /inference/v1/generate；
TrainClient 当前只支持 chat-completions dialect；
routed_experts 等大字段不会留在普通 JSON dump 中；
SWE hidden verifier、clean grading、artifact projection、anti-cheat 仍需 RepoHarness 自建治理层。
```

### 5.2 renderers

`renderers` 能支撑 token provenance、bridge_to_next_turn、loss mask、prompt/completion token 精确复原等设计。它是形态 A 的关键基础。

但需要注意：

```text
模型名必须命中 hand-coded renderer；
renamed checkpoint 或本地微调路径可能退回 DefaultRenderer；
DefaultRenderer 不能自动提供高置信 bridge；
首训模型必须跑 renderer parity 和 bridge 测试。
```

### 5.3 slime

S0 后，`slime` 不再只是“第一个在线训练后端候选”，而是 **Qwen3-30B-A3B MoE 首训主链路的训练后端与原生 SGLang 路径**。它已经支持 GRPO、GSPO、PPO、SGLang rollout、custom_generate、coding_agent_rl、Claude Code / Codex harness、Sample fan-out、logprob 捕获等能力。

但它不替代 RepoHarness：

```text
slime 是训练后端 + agentic rollout substrate；
不是 RepoHarness 的环境治理层；
不是 hidden verifier 隔离层；
不是 artifact public projection 层；
不是 task quality / anti-cheat / eligibility 的唯一权威。
```

S0 后对 slime 的要求应改成：

```text
必须 pin slime patch 镜像，而不是误连 stock SGLang；
启动后必须跑 top_p < 1.0 探针，确认 meta_info 含 top_p_token_ids / top_p_token_offsets；
routing/top-p 解码与校验只在 TrajectoryProjection 中实现一次；
slime Sample 仍然只是训练容器，不是 RepoHarness 的审计 artifact；
示例默认偏 E2B sandbox，如果 RepoHarness 第一阶段用 Docker，需要单独适配。
```

### 5.4 prime-rl

`prime-rl` 的价值主要在于展示如何消费 verifiers Trace，把 branch 转成训练样本。它说明：

```text
一个训练样本可以是完整 token 序列；
mask 标记哪些 token 进入训练；
logprobs、temperatures、advantages 与 token_ids 对齐；
routed_experts 可以作为 backend tensor 进入训练样本。
```

这对 RepoHarness 的 adapter 设计有很大参考价值，但不意味着必须采用 prime-rl 作为训练后端。

## 6. 公开资料对底稿的影响

### 6.1 GLM-5.2

GLM-5.2 说明 slime 能支持 white-box rollout、black-box rollout、compact trajectory、sub-agent workflow 和 OPD。它同时给了一个重要边界：当 long-horizon + compaction 导致轨迹被切成数量和长度可变的 sub-trace 时，group-wise GRPO 语义会变差，critic-based PPO 更合适。

对底稿的影响：

```text
首版关 compaction，用 GRPO，可以保留。
一旦开 compaction 或 sub-agent fan-out，必须重新评估 PPO。
Anti-Hack 不能只是离线审计，应包括在线拦截与 dummy observation 后继续 rollout。
```

### 6.2 DeepSWE

DeepSWE 支持底稿使用 GRPO++ 风格配置、sparse outcome reward、no KL、no entropy、no reward std、leave-one-out advantage 与 compact filtering。它也说明 4.5K 级 R2E-Gym 任务和 64 H100 训练 6 天是一个强公开锚点。

对底稿的影响：

```text
个人 8 卡环境下，150~200 题更适合定义为闭环档，而不是效果证明档。
如果想证明能力提升，后续仍应扩到 1000~2000 题附近。
```

### 6.3 SkyRL-Agent

SkyRL-Agent 支持 group=8、32K context、50 turns、超 context / step limit 轨迹 mask loss 等选择。它也提醒 minimal bash-only 设置的 non-resolved 比例高。

对底稿的影响：

```text
n=8、32K、50 turns 是合理首训锚点。
mini-swe-agent / bash-only 不适合作为首训主 harness。
```

### 6.4 SERA、OpenHands RFT、SWE-Gym、SWE-Master

这些资料共同提醒：RFT / SFT / agentic mid-training 仍然是强基线，且常常比在线 RL 更便宜。直接 RL 不是错误，但不能忽视 RFT / SFT baseline。

对底稿的影响：

```text
保留 direct RL from instruct。
新增 pre-RL 行为诊断。
若行为诊断失败，提前触发小规模 SFT / RFT，而不是等 20 个 RL step。
如果资源允许，增加一个小 RFT / SFT baseline，作为解释对照。
```

### 6.5 SWE-Bench Pro 与 SWE-bench Verified 生态变化

公开讨论已经明确：SWE-bench Verified 仍可用，但不足以单独代表前沿 coding agent 能力。

对底稿的影响：

```text
Verified 可作为内部 held-out sanity check。
成功证据中应加入更干净或更难的补充评测面。
对外叙事要避免“Verified 提升 = 真实世界能力已证明”的过度表达。
```

## 7. 建议的最小预注册实验包

如果下一步要把底稿改成可执行实验设计，我建议按下面方式定稿。

### 7.1 S0 后剩余阻塞项

```text
已由 S0 关闭：
  V1 依赖与 Docker 使用层；
  V2 Qwen3-30B-A3B renderer coverage；
  V3 token 协议链路；
  V4 routing passthrough 与形态 A/B 评估。

S1 必须关闭：
  U-H：slime patch 镜像在 sm_120 / Blackwell 上可用；
  top_p < 1.0 探针确认 top-p tape 存在；
  TrajectoryProjection 能保存 token/logprob/routing/top-p 引用与治理事实。

S4 前必须关闭：
  U-C：8 卡训练侧最小 step；
  32K 压力样本；
  CPU offload、权重同步、PCIe 通信与训练 step 墙钟；
  显存峰值、CPU 内存峰值、token/s、失败类型统计。
```

### 7.2 首训配置

```text
模型：
  Qwen3-30B-A3B；
  35B-A3B 不进第一轮默认配置，仅作 S4 前升级候选。

接入：
  形态 B：slime 原生 SGLang /generate + slime patch 镜像，是 MoE 首训主形态。
  形态 A：verifiers default harness + renderers，作为协议基线、dense/eval/调试路径。

算法：
  GRPO / GRPO++；
  n=8；
  KL 关；
  entropy 关；
  reward std normalization 关；
  clip 0.2 / 0.28；
  dynamic sampling 默认开；
  compaction 关闭。

数据：
  闭环档：SWE-Gym Lite 过滤后约 150~200 题；
  效果档：SWE-Gym 全量 + R2E-Gym-Subset 过滤后 1000~2000 题。

评测：
  内部主评测：Verified held-out ≥30 题，n=8 起；
  预算允许：50 题或 n=16；
  可信补充：SWE-Bench Pro public 小集或 Terminal-Bench Pro 小集。

成功判据：
  Avg@n 提升 ≥8~10 个百分点，且 paired bootstrap 置信区间不跨 0；
  best-of-K 曲线随训练上升；
  governance 拦截统计完整；
  anti-cheat 红队包全部通过；
  infra_failure 与 reward=0 清晰区分；
  离线导出与在线 adapter 的 parity 通过分层定义。
```

### 7.3 回退与停止规则

```text
Pre-RL 行为诊断失败：
  先做 1k~5k 轨迹小 SFT / RFT，再进入 RL。

训练中零方差组过多：
  调整 pass-rate 预筛、提高过采样倍率、扩大任务池；
  不优先降低 n。

熵塌缩或输出重复：
  先检查 dynamic sampling、难度分布、reward hacking；
  再考虑学习率或 entropy bonus。

compaction 不可关闭：
  暂停 GRPO 定案，重新评估 PPO / compact filtering。

infra_failure 大量出现：
  训练样本不得记作 reward=0；
  必须按 failure_category 归因并从训练组中过滤或重试。
```

## 8. 需要项目所有者最终决策的问题

### D1 首训默认形态

S0 后我的建议变为：**直接接受形态 B 作为首训默认形态**，不再把它写成待验证候选。原因是 topology 报告已经证明 top-p tape 是硬分水岭，形态 B 有 slime patch 镜像这条现成维护路径，形态 A 则要改三端协议。

但必须保留形态 A 作为协议基线和可审计对照，因为它的 TrainClient + renderers + Trace 路径已经由 S0-5 证明可用，且适合 dense/eval/调试。

### D2 首训 harness

需要确认是否接受 S0-8 的建议：**slime Claude Code harness 作为首训主 harness**。Codex harness 是同层候选，但不应在第一次 before/after 主实验里与 Claude Code 混用。

我的建议：若 Claude Code 的可安装版本、额度、许可、回连 adapter 稳定，就批准 Claude Code。若转向 Codex，训练与评测必须同时切到 Codex scaffold，并在报告中标注 scaffold 选择变化。

### D3 首训规模

我的建议：把 150~200 题明确写成“闭环档”，目标是证明治理设施与训练链路可以产生可信样本和可观测曲线；如果要证明能力提升，准备扩到 1000~2000 题。

### D4 是否加入 RFT / SFT baseline

我的建议：不把 SFT 作为首训必选前置，但加入 pre-RL 行为诊断；如果行为诊断失败，提前 SFT/RFT。若时间允许，做一个小 RFT baseline，避免最后无法解释“为什么不用更便宜的微调”。

### D5 评测补充面

我的建议：Verified held-out 继续作为主内部面；同时选一个小型可信补充面。优先级：

```text
SWE-Bench Pro public 小集；
Terminal-Bench Pro 小集；
其他与训练 repo 完全不重叠、可 clean grading 的小型 held-out。
```

### D6 MoE backend tensor 要求

S0 后这个问题已经拆成两层：

```text
routing tape：
  已动态验证可取，应纳入 TrajectoryProjection。

top-p tape：
  是否成为硬依赖取决于 E2 的训练 rollout top_p。
  如果 top_p != 1.0，例如 0.95，则 top-p tape 是 slime loss 的硬依赖，U-H 必须在 S1 关闭。
  如果 top_p = 1.0，则可以绕开 top-p tape，但会偏离多数前沿采样配置。
```

我的建议：保持 `top_p < 1.0` 的前沿配方，并把 U-H 作为 S1 必关项，而不是为了绕开镜像问题把采样退化到 `top_p = 1.0`。

## 9. 建议修改原底稿的清单

1. E7 改成“三条路径”描述，不要把 slime 黑盒路径和 renderers token fidelity 写成同一条已完成链路。
2. E10 将 `verifiers bash_edit harness` 改成 `verifiers default harness（edit=true，search=false 起步）`。
3. 附录 A 删除 `reward/K 分摊`，改成“完整 reward + rollout_id 分母治理”。
4. E8 将 pass@1 统一改成 Avg@n；best-of-K 单独报告。
5. E8 删除或标注 Qwen3 blocker 的具体 84.6% / 75.1% 数字，除非补充明确来源。
6. E5 增加 SWE-Bench Pro public 或 Terminal-Bench Pro 小型补充评测面。
7. E3 增加 pre-RL 行为诊断，避免等 20 个 RL step 后才发现必须 SFT。
8. E4 增加 `dataset_freeze_report` 作为数据冻结硬产物。
9. E6 将环境并发、镜像冷启动、工具执行、评分尾波纳入首训必采 timing 指标。
10. E7 写入 S0 定案：形态 B 是 MoE 首训主形态；形态 A 是协议基线、dense/eval/调试路径。
11. E1 写入 S0 定案：Qwen3-30B-A3B 为默认目标；U-G renderer 守门必须作为启动断言。
12. E2 显式拍板训练 rollout 的 `top_p`：若 `top_p != 1.0`，S1 必须 pin slime patch 镜像并用启动探针确认 top-p tape。
13. E6 修正算力表述：S0 只验证单卡推理侧，8 卡训练侧留 U-C / S4 前预实验。
14. 明确 mini-swe-agent / bash-only 只作为 baseline 或 transfer gap 对照，不作为首训主 harness。

## 10. 参考资料与链接

本地参考：

- `docs/agentic_RL/training_design/repoharness_validation_experiment_design.md`
- `docs/harness_improve/repo_harness_design_doc2_verifiers_based.md`
- `docs/harness_improve/repo_harness_final_review_before_implementation.md`
- `docs/agentic_RL/repo_harness_rh2_workstreams/s0/s0_acceptance_summary.json`
- `docs/agentic_RL/repo_harness_rh2_workstreams/s0/v2_renderer_report.md`
- `docs/agentic_RL/repo_harness_rh2_workstreams/s0/v3_protocol_report.md`
- `docs/agentic_RL/repo_harness_rh2_workstreams/s0/topology_ab_report.md`
- `docs/agentic_RL/repo_harness_rh2_workstreams/s0/swe_smoke_report.md`
- `docs/agentic_RL/repo_harness_rh2_workstreams/s0/s0_8_expdesign_review.md`
- `docs/harness_improve/external_paper_references/pdfs/glm5.2_blog_RL.md`
- `docs/agentic_RL/training_design/warm_start_offline_data_filtering_design.md`
- `reference/verifiers/verifiers/v1/clients/train.py`
- `reference/verifiers/verifiers/v1/harnesses/default/harness.py`
- `reference/verifiers/verifiers/v1/trace.py`
- `reference/renderers/renderers/base.py`
- `reference/slime/slime/agent/adapters/common.py`
- `reference/slime/slime/agent/trajectory.py`
- `reference/slime/slime/rollout/sglang_rollout.py`
- `reference/slime/slime/utils/types.py`
- `reference/prime-rl/src/prime_rl/transport/types.py`
- `reference/prime-rl/src/prime_rl/orchestrator/trajectories.py`

公开资料：

- GLM-5.2 blog: https://huggingface.co/blog/zai-org/glm-52-blog
- DeepSWE: https://www.together.ai/blog/deepswe
- SkyRL-Agent: https://arxiv.org/html/2511.16108v1
- SERA: https://arxiv.org/html/2601.20789v2
- SWE-Gym: https://proceedings.mlr.press/v267/pan25g.html
- SWE-Gym GitHub: https://github.com/SWE-Gym/SWE-Gym
- R2E-Gym: https://r2e-gym.github.io/
- SWE-Master: https://github.com/RUCAIBox/SWE-Master
- OpenHands RFT: https://nebius.com/blog/posts/openhands-trajectories-with-qwen3-coder-480b
- Qwen3.6-35B-A3B model card: https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- SWE-Bench Pro: https://scale.com/blog/swe-bench-pro
- OpenAI on SWE-bench Verified limitations: https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
