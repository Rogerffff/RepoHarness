# RepoHarness 验证实验设计决策底稿审查与补充建议

审查对象：`docs/agentic_RL/training_design/repoharness_validation_experiment_design.md`

审查时间基线：2026-07-07

本文只审查实验设计决策底稿，不替换原文，不修改实现代码。结论来自三类材料交叉检查：

1. 本地设计文档与技术报告摘录，包括 `repo_harness_design_doc2_verifiers_based.md`、`repo_harness_final_review_before_implementation.md`、`glm5.2_blog_RL.md`、warm-start 设计文档，以及 `external_paper_references` 目录下的技术报告索引。
2. 本地参考代码库，包括 `reference/verifiers`、`reference/renderers`、`reference/slime`、`reference/prime-rl`。
3. 公开资料补充核查，包括 GLM-5.2、DeepSWE、SkyRL-Agent、SERA、SWE-Gym、R2E-Gym、SWE-Master、OpenHands RFT、SWE-Bench Pro 等。

## 1. 总结论

当前实验设计底稿的主方向不需要推翻。它选择“小规模可信闭环先行”的方式，而不是一开始追求完整大规模训练，这一点是正确的。它把训练目标限定在软件工程任务，把训练数据与评测数据分离，把 outcome reward 绑定到 clean grading，把 anti-cheat、环境验证、eligibility gate 和 artifact governance 作为分数可信性的组成部分，这些方向都符合目前公开大厂经验。

我赞成保留的核心路线是：

```text
首训目标：MoE 开源模型，优先 30B-A3B / 35B-A3B 档
训练后端：slime 作为首个在线训练后端候选
算法起点：首版关 compaction，用 GRPO / GRPO++ 风格配置起步
数据路线：SWE-Gym / R2E-Gym 等开源可执行任务起步，不使用 SWE-bench Verified 训练
评测方式：同一 harness 的 before/after 配对评测，辅以治理证据
治理边界：clean grading、anti-cheat、hidden verifier 隔离、eligibility gate 不可省略
```

但是，底稿中有几处内容需要在定稿前修正，否则会把“需要 S0 验证的工程假设”写成“已经被框架支持的事实”。最重要的三点是：

1. `verifiers + renderers` 与 `slime coding_agent_rl` 不是一条已经天然接通的链路。前者是 vLLM 风格的精确 token 渲染与 Trace 路径，后者是 SGLang 原生黑盒 harness 路径。它们互补，但目前不能写成同一个现成能力。
2. MoE routing、top-p token tape、renderer bridge 在 slime 标准 rollout 中支持较好，但在 slime 的黑盒 coding-agent adapter 中还没有完全确认，需要作为 S0 动态验证项。
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
  风险：renderer bridge、message attribution、top-p tape、routed experts 在黑盒路径中需要 S0 验证或扩展。

路径 3：RepoHarness governance layer
  目标：sandbox、clean grading、hidden verifier、anti-cheat、eligibility、artifact projection。
  边界：不假设 verifiers 或 slime 已经完整提供这些治理能力。
```

### 2.2 “MoE 使形态 B 显著加分”可以保留，但必须变成 S0 验证项

底稿把 MoE 与形态 B 绑定得比较强，这个倾向有道理，因为 slime 与 SGLang 的生态对 MoE、routing replay、top-p tape 更友好。但当前只能写成“优先验证形态 B”，不能写成“形态 B 已经满足所有 MoE 训练契约”。

本地代码支持与缺口如下：

- `reference/slime/slime/utils/types.py` 的 `Sample` 已有 `rollout_id` 等字段，slime 的训练数据结构也支持 top-p 与 routed experts 相关字段。
- `reference/slime/slime/rollout/sglang_rollout.py` 在标准 rollout 路径里可以请求 `return_top_p_token_ids` 与 `return_routed_experts`。
- 但是 `reference/slime/slime/agent/adapters/common.py` 的 black-box coding-agent SGLang 调用目前主要返回 `prompt_ids`、`output_ids`、`finish_reason`、`output_log_probs`。

因此 S0 必须增加一个阻塞检查：

```text
S0-MoE-Capture：
  对目标模型运行 1 条真实 coding-agent rollout。
  检查每次模型调用是否能得到：
    prompt token ids
    completion token ids
    completion logprobs
    sampling parameters
    top-p token tape（如果训练后端需要）
    routed experts（如果使用 routing replay / MoE 稳定性分析）
  若 slime coding-agent adapter 当前不透传 top-p 或 routed experts，
  必须明确选择：
    A. 扩展 adapter；
    B. 首训暂不使用相关训练特性；
    C. 改走 verifiers/renderers 路径或协议 shim。
```

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

### 2.7 C1 硬件可行性仍然只是估计

底稿已经把 C1 写得比之前扎实很多：8 张 RTX Pro 6000 Blackwell，单卡 96GB，PCIe，无 NVLink，必须 colocate 与 CPU offload。这是正确方向。

但 30B-A3B / 35B-A3B 是否能稳定做 32K 上下文训练，不能只靠显存粗算。真正阻塞项包括：

```text
SGLang 对 sm_120 Blackwell 工作站卡的 kernel 支持；
Megatron / slime 训练侧对该卡的 kernel 支持；
PCIe 下 MoE expert parallel all-to-all 吞吐；
CPU offload 对训练 step 墙钟的影响；
Docker / sandbox 并发和评分尾波是否反过来成为主瓶颈。
```

建议把 S0 V5 写成阻塞退出条件：

```text
S0 V5 不通过，则不得锁定 E1/E2/E6。
V5 至少包括：
  目标模型加载成功；
  1 step × 8 prompt × n=2/4 最小训练冒烟；
  真实 32K prompt 或接近 32K 的压力样本；
  生成 / 沙箱执行 / 评分 / 训练 step 四段墙钟分解；
  显存峰值、CPU 内存峰值、吞吐 token/s、失败类型统计。
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

我同意 30B-A3B / 35B-A3B 档 MoE 的方向。公开资料与 slime 示例都支持 3B active parameter 这个量级有训练价值。

需要补充的是：具体 checkpoint 不应在文档层提前锁死。即使 Qwen3.6-35B-A3B 公开声称兼容 vLLM / SGLang，仍需 S0 验证：

```text
权重可获得；
tokenizer 与 renderer 匹配；
renamed / fine-tuned checkpoint 是否命中 hand-coded renderer；
SGLang / Megatron / slime 在 Blackwell 工作站卡上可跑；
32K 上下文吞吐可接受。
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

我建议把 S0 默认假设写成：

```text
MoE 首训优先验证形态 B：slime coding_agent_rl custom_generate。
形态 B 通过的条件是：token ids、logprobs、sampling params、eligibility、reward facts、anti-cheat facts、必要的 MoE backend tensors 都能被无损记录或可解释地降级。

形态 A 保留为可审计基准路径：verifiers default harness + renderers + offline export / prime-rl 风格 sample。
形态 A 接 slime 需要 protocol shim 或新 TrainClient，因此不应默认更快。
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

建议将候选改写为：

```text
形态 B：
  slime Claude Code harness 或 slime Codex harness。
  首选哪个取决于本地可安装性、许可、额度、拦截稳定性和 S0 token capture 结果。

形态 A：
  verifiers default harness（edit=true，search=false 起步）。

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

`slime` 足以作为第一个在线训练后端候选。它已经支持 GRPO、GSPO、PPO、SGLang rollout、custom_generate、coding_agent_rl、Claude Code / Codex harness、Sample fan-out、logprob 捕获等能力。

但它不替代 RepoHarness：

```text
slime 是训练后端 + agentic rollout substrate；
不是 RepoHarness 的环境治理层；
不是 hidden verifier 隔离层；
不是 artifact public projection 层；
不是 task quality / anti-cheat / eligibility 的唯一权威。
```

特别需要写进 S0 的 slime 检查：

```text
coding_agent_rl 示例脚本当前走 train.py，不应直接描述成 fully async 示例；
示例默认偏 E2B sandbox，如果项目第一阶段用 Docker，需要适配；
黑盒 adapter 当前使用 tokenizer.apply_chat_template，不是 renderers；
top-p tape 与 routed experts 在黑盒路径中是否可用需要实测。
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

### 7.1 S0 阻塞验证

```text
V1 目标 checkpoint 可获得，license 与 tokenizer 正常。
V2 renderer resolution 命中 hand-coded renderer，bridge_to_next_turn 通过。
V3 SGLang 能在 RTX Pro 6000 Blackwell 上运行目标模型。
V4 slime / Megatron 训练最小 step 通过。
V5 32K 压力样本测出显存、CPU 内存、token/s、训练 step 墙钟。
V6 black-box harness 模型调用能捕获 prompt ids、completion ids、logprobs。
V7 如果使用 MoE routing/top-p replay，确认 coding-agent path 可透传；否则明确降级。
V8 clean grading、anti-cheat、eligibility sidecar 能与训练样本关联。
```

### 7.2 首训配置

```text
模型：
  Qwen3-30B-A3B 档起步；
  35B-A3B 仅在 S0 通过后升级。

接入：
  优先验证形态 B：slime coding_agent_rl custom_generate。
  形态 A：verifiers default harness + renderers，作为可审计基准路径。

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

我的建议：默认先验证形态 B，也就是 slime coding_agent_rl custom_generate + Claude Code 或 Codex harness。原因是它最接近黑盒 coding-agent 训练，且 MoE / SGLang / slime 后端路径更现实。

但必须保留形态 A 作为可审计路径，因为它的 token provenance 更干净，更适合验证 RepoHarness 的 artifact 与 adapter 设计。

### D2 首训 harness

需要在 Claude Code 与 Codex 之间选一个首训主 harness。

我的建议：优先选 slime 示例最成熟、最容易跑通的那个。如果 Claude Code 的可安装版本、额度、许可、回连 adapter 最稳定，就选 Claude Code；如果 Codex CLI 更容易控制，则选 Codex。不要在第一次实验同时混训多个 harness。

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

需要决定首训是否强依赖 top-p tape 与 routed experts。

我的建议：如果只是跑通第一个可信训练闭环，可以允许“记录 token ids / logprobs / sampling params，暂不启用 routing replay”。如果目标是专门验证 MoE 训练稳定性，则必须在 S0 扩展 slime coding-agent adapter 或选择能保留这些 backend tensors 的路径。

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
10. S0 增加 MoE routing/top-p tape 在 slime coding-agent path 的动态验证项。
11. S0 增加 renderer resolution 与 bridge 测试，防止 renamed checkpoint 退回 `DefaultRenderer`。
12. 明确 mini-swe-agent / bash-only 只作为 baseline 或 transfer gap 对照，不作为首训主 harness。

## 10. 参考资料与链接

本地参考：

- `docs/agentic_RL/training_design/repoharness_validation_experiment_design.md`
- `docs/harness_improve/repo_harness_design_doc2_verifiers_based.md`
- `docs/harness_improve/repo_harness_final_review_before_implementation.md`
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
