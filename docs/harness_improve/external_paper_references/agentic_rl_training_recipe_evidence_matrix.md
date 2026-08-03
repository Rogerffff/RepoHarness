# Agentic RL 训练配方与基础设施证据矩阵

> 状态：外部证据汇总稿。
>
> 用途：统一记录公开技术报告、论文、官方代码与配置中可核验的 agentic RL 训练事实，供 RepoHarness 的实验设计、FA 训练链、SWE-Safety 和后续算法演进复用。本文是证据索引，不直接修改任何已定案的训练语义。
>
> 最近核验：2026-08-03。

## 1. 为什么需要这份矩阵

现有资料入口回答了“有哪些报告、各自值得读什么”，专题分析回答了“某一个设计问题应如何理解”，但缺少一张使用同一字段横向比较训练配方的账本。这个缺口容易造成三类错误：

1. 把厂商报告中的方向性描述误写成可以复现的训练配方；
2. 把 `context limit`、`turn limit`、`wall-clock timeout` 和基础设施故障合并成同一种“未完成轨迹”；
3. 把轨迹是否属于同题组、reward 是否进入组统计、该轨迹 token 是否产生梯度，错误地压缩成一个布尔资格字段。

本文采用统一证据字段，并明确区分“公开事实”“代码事实”“合理推断”和“未披露”。后续新增报告时，应先进入本文或 `manifest.json`，不要直接把某个外部做法提升为 RepoHarness 的设计定案。

## 2. 证据等级与使用规则

| 等级 | 定义 | 可以支持什么 | 不可以支持什么 |
| --- | --- | --- | --- |
| E0 | 论文或官方技术报告给出明确公式、表格、数值、实验设置或算法流程 | 算法语义、实验锚点、字段需求 | 未披露的工程实现细节 |
| E1 | 官方开源代码、启动脚本、配置或模型卡能够定位到具体实现 | 可执行参数、数据流、框架能力与真实默认值 | 宣称该配置就是厂商内部生产配方，除非官方明确说明 |
| E2 | 官方博客或报告只给出定性描述 | 架构方向、风险清单、待验证假设 | 精确超参数、完整 loss、失败处理或可复现成本 |
| E3 | 基于多个 E0/E1 事实作出的工程推断 | RepoHarness 的候选设计或实验问题 | 写成外部来源已经验证的结论 |
| U | 来源没有披露，或公开材料互相矛盾 | 明确登记未知项 | 用常见默认值补空白 |

使用规则：

- 同一个来源可以在不同字段拥有不同证据等级。例如论文可以精确披露算法公式，却不披露 sandbox 重试策略。
- 论文正文和开源仓库发生冲突时，两者分别登记；不能用代码当前默认值反推历史论文实验。
- 第三方文章只用于发现线索，不作为最终训练事实的唯一证据。技术结论尽量回到论文、官方模型卡、官方博客和官方代码。
- “没有披露”本身是一条重要结论。本文不会为了表格完整而猜测 batch size、timeout 或 group repair。

## 3. 统一训练配方字段

每个来源尽量按以下字段记录。无法确认的字段写 `U`，不留模糊空白。

| 类别 | 字段 |
| --- | --- |
| 身份 | 来源、版本或日期、论文结果对应的代码版本、证据等级 |
| 模型 | base / instruct checkpoint、dense 或 MoE、总参数与激活参数、上下文上限 |
| 前置训练 | SFT、rejection sampling、RFT、value pretraining、teacher / OPD |
| 数据 | 数据集、题数、真实或合成、过滤、难度与污染控制、held-out 方式 |
| 环境 | harness、工具面、sandbox、网络、环境重置、hidden verifier、anti-cheat |
| rollout | 每题采样数 `n`、并发、最大 token、最大 turn、最大 wall-clock、compaction、partial rollout |
| 终止 | 成功、任务失败、turn/context horizon、wall timeout、模型服务故障、安全拒绝分别如何处理 |
| 奖励 | verifier、reward 范围、过程奖励、长度惩罚、reward hacking 处理 |
| 优势与 loss | GRPO / PPO / GSPO / SAO 等、组统计、loss mask、分母、importance correction、KL / entropy |
| 异步 | rollout / trainer 拓扑、weight version、staleness、权重同步、队列与反压、长尾处理 |
| 规模 | GPU、训练步数、样本或 token 数、训练时长、推理与训练放置 |
| 可复现性 | 代码、配置、数据、模型权重、环境镜像是否公开 |
| RepoHarness 映射 | 直接采用、实验候选、基础设施参考、远期方向或当前不适用 |

## 4. 总结性判断

### 4.1 公开资料没有提供一份可以整体照抄的完整配方

目前公开工作呈现的是互补证据：有的报告公开算法但不公开环境故障语义，有的仓库公开 rollout 实现但不公开最终模型的真实训练参数，有的模型卡给出数据规模与预算却没有 trainer 内部细节。因此，RepoHarness 应采用“字段级取证”，不能把任何单一来源称作完整权威实现。

### 4.2 训练 horizon 不是一个数字

至少需要独立记录：

```text
model_context_limit
max_generated_tokens_per_call
episode_turn_limit
episode_wall_clock_limit
tool_call_timeout
sandbox_ttl
grading_timeout
trainer_staleness_limit
```

这些限制的归因与训练语义不同。策略正常触达 turn 或 context horizon，基础设施在模型尚可继续时耗尽 wall-clock，以及 sandbox / model service 失败，不能使用同一个 `timeout=true` 表示。

### 4.3 终止结果至少需要三个正交决定

```text
group_membership:
  该 execution 是否仍是同题统计中的一个真实结果

reward_disposition:
  reward 是否定义，以及是否进入组内均值和方差

gradient_disposition:
  该 execution 自己的 action token 是否产生 policy gradient
```

这三个决定不能由 `loss_mask` 一项承担。`loss_mask` 只表达 token provenance 与角色资格；算法针对某次 trainer step 的梯度屏蔽，应由独立的训练决定表示。

### 4.4 “一个成员超限就整组作废”不是普遍的 GRPO 必然要求

GRPO 需要可解释的同题比较，但不意味着所有非成功终止都不是组成员。一个可信的失败结果、一个可信的 horizon 截断，以及一个因基础设施错误缺失的 execution，统计含义不同。首训必须在算法配置中预注册处理方式，并用组级单元测试证明 reward、advantage 与梯度行为；不能让 adapter 根据 `exit_code` 临时决定。

### 4.5 Fully async 需要行为策略证据，不只是队列

只把 rollout 与 trainer 放进两个并发循环并不构成训练语义完整的 fully async。公开工作共同指向以下必要事实：每轮模型调用的行为策略版本和 logprob、训练消费时的当前版本、staleness、丢弃或修正规则、权重更新窗口，以及 trainer 对样本的最终确认。RepoHarness 当前选择 version-aware fully async + faithful DIS，属于有外部证据支持的工程方向，但仍需通过 FA-4/FA-5 的生产路径验收，不能因小张量公式对拍通过就宣称整链完成。

## 5. 来源总表

> 本节给出索引级结论。第 6 节起记录能够影响 RepoHarness 设计或实验的详细事实。

| 来源 | 公开程度 | 最有价值的训练证据 | 主要空白 | 对 RepoHarness 的作用 |
| --- | --- | --- | --- | --- |
| Polar / ProRL-Agent-Server | 论文 + 代码 | 黑盒 harness 的模型边界捕获、rollout service、trajectory build | 不是完整 SWE 环境与训练算法配方 | 黑盒 rollout 与 capture 参考 |
| MAI-Thinking-1 | 技术报告 | SWE 环境生产、验证、评分与 anti-cheat | 大量 trainer 超参数未披露 | 数据与环境生产参考 |
| Nemotron 3 Ultra | 技术报告 | 多阶段 post-training、RLVR、MOPD、MoE routing 与故障经验 | SWE 专用 rollout recipe 不完整 | 训练契约与故障归因参考 |
| Qwen3-Coder-Next | 技术报告 | coding / agentic 数据和跨环境训练方向 | 可复现 RL 参数有限 | 任务与 harness 泛化参考 |
| MiniMax-M1 / M2 | 技术报告 | CISPO、长上下文、异步数据生产与 agent 环境方向 | 环境失败与完整训练脚本未公开 | 算法和系统演进参考 |
| GLM-5 / GLM-5.2 | 报告 + 博客 + slime | 异步 GRPO、缺员处理、PPO / SAO / CompactionRL 演进、OPD | 产品模型的完整配方仍不公开 | 当前算法与 slime 主参考 |
| DeepSeek-V3.2 / V4 | 技术报告 | agentic data synthesis、tool-use、长上下文训练 | SWE 环境和终止语义披露有限 | 数据生产和模型能力背景 |
| Kimi K2 / K2.5 / K3 | 技术报告 + 权重 + AgentENV | agentic RL、partial rollout、per-token 约束、persistent sandbox、harness 多样性 | K3 的组统计、精确 optimizer 与多数失败规则未披露 | 长程 rollout 与 sandbox 演进参考 |
| Composer 2 | 技术报告 | 在接近产品的 coding harness 中训练、减少 train-test mismatch | 完整训练参数和代码有限 | 真实 harness 一致性参考 |
| ROME / RollArt / ROLL | 论文 + 多仓库代码 | 轨迹级异步、环境与训练解耦、bounded staleness、生产级调度 | 论文模型配方与仓库默认值需分开 | 后端、环境服务与 fully async 参考 |
| DeepSWE / SkyRL-Agent | 模型卡、论文、代码与脚本 | 可公开核对的数据、`n`、上下文、turn、过滤与训练规模锚点 | 某些 timeout 与内部部署细节仍未知 | 首训配置和终止语义锚点 |
| CompactionRL | 论文 | summary joint training、token-level loss、跨 segment credit | 与 SAO 的完整组合未公开 | 关闭 compaction 的近期边界与远期 schema |
| SAO | 论文 | single-rollout async、DIS、critic 与 Skip-Observation GAE | 官方完整代码和生产参数有限 | GRPO 之后的算法演进方向 |

## 6. 可复现程度较高的 coding-agent RL 配方

### 6.1 ROME / ROLL 生态公开事实

来源：R10～R12 与 `reference/ROLL/`。论文事实为 E0，当前仓库实现与
示例为 E1；两者不能互相替代。

| 字段 | 公开事实 | 使用限制 |
| --- | --- | --- |
| ROME 任务漏斗 | R10 第 19～20 页：约 6 万 RL 候选经过难度、环境稳定性与 spec-test 一致性过滤，最终保留约 2 千中等难度任务；测试只在评分期挂载 | 支持环境生产与 hidden-test 边界，不给出 RH2 首训完整题单 |
| ROLL RLVR 混合 | R12 第 9 页：约 5k 数学、2k 代码及 general 数据，比例 40/30/30；reward 来自规则、sandbox 与 LLM judge | 多领域配方，不应照搬到 deterministic SWE-only 首训 |
| ROLL 默认值 | 当前代码默认 `rollout_batch_size=128`、并发 128、`async_generation_ratio=0`、`ppo_epochs=1`、`gamma=1`、`pg_clip=0.2` | 框架默认，不是论文训练结果 |
| ROLL 示例 | FrozenLake 示例使用 async ratio 1、group 8、rollout 1024、8192 tokens；WebShop 示例 group 8、batch 64、8192 tokens | 小环境示例，不是 coding-agent 配方 |
| R12 实验 | Sokoban 报告 8 GPU、batch 1024、advantage clip 10、reward clip 20、format penalty -0.001；WebShop 为 50 steps、8192 tokens、format penalty -0.05 | 论文数值与当前示例已经发生漂移，必须标来源版本 |
| slime coding 示例 | agent 1800 秒、grader 600 秒、外层 guard 为两者加 180 秒；batch 8、`n=8`、context 96K、每 turn response 32K | 示例用于能力演示，不能直接成为 RH2 首训默认 |

关键代码：

```text
reference/ROLL/roll/configs/base_config.py
reference/ROLL/examples/qwen2.5-0.5B-agentic/agent_val_frozen_lake_async.yaml
reference/ROLL/examples/qwen2.5-7B-agentic_megatron/agentic_val_webshop.yaml
reference/slime/examples/coding_agent_rl/README.md
reference/slime/examples/coding_agent_rl/generate.py
```

### 6.2 其他公开 coding-agent 配方

#### 6.2.1 SA-SWE / SkyRL-Agent：首训算法与 horizon 语义的主要锚点

来源：[SA-SWE 论文](https://arxiv.org/abs/2511.16108) 与
[SkyRL 官方仓库](https://github.com/NovaSky-AI/SkyRL)。论文配方属于 E0。

| 字段 | 论文配方 |
| --- | --- |
| 基座 | dense Qwen3-32B；没有先做 SWE SFT |
| 数据 | 约 4.5K R2E-Gym 任务 |
| harness | 简单 ReAct agent；bash、文件编辑、AST 搜索 |
| 算法 | 完全 on-policy；leave-one-out advantage；不做 reward 标准差归一化和长度归一化；KL 与 entropy 关闭 |
| 组与 batch | 每题 `n=8`；training batch 与 minibatch 均为 64；学习率 `1e-6` |
| 预算 | 训练 32K context、最多 50 turns；评测 40K、最多 100 steps |
| horizon 语义 | 达到 context 或 turn 上限的轨迹仍参与 reward / advantage 计算，但该 execution 自身 token 不产生梯度 |
| 异步 | 环境初始化、agent 执行和评分流水化，同时保持 fully on-policy；不是允许长期 stale policy 的 continuous fully async |
| 规模 | 125 steps；两组各 8 张 H100；约 4601 H100-hours |

这是目前最接近 RH2 首训问题的公开成功配方，但模型是 dense Qwen3-32B，
harness 也不是黑盒 Claude Code。RH2 只能把它作为算法与 horizon 语义锚点，
不能声称复现。

当前 SkyRL 仓库的 Mini-SWE 示例也不能与论文混称。该示例使用
Qwen3-Coder-30B-A3B-Instruct、SWE-Gym subset、`n=4`、batch 16 和
`step_limit=20`；转换器会从 messages 重新分词并传
`assistant_logprobs=None`。它是工程 demonstration，不满足 RH2 的 token
provenance 要求：

```text
examples/train/mini_swe_agent/run_mini_swe_30B.sh
examples/train/mini_swe_agent/swebench.yaml
examples/train/mini_swe_agent/mini_swe_generator.py
```

#### 6.2.2 DeepSWE：成功模型证据较强，训练复现面不完整

来源：[官方模型卡](https://huggingface.co/agentica-org/DeepSWE-Preview/blob/main/README.md)
与 [R2E reproduction](https://github.com/R2E-Gym/R2E-Gym/blob/main/reproduction/DEEPSWE_REPRODUCTION.MD)。

| 字段 | 公开事实 | 未披露 |
| --- | --- | --- |
| 基座与数据 | dense Qwen3-32B；direct RL；约 4.5K R2E-Gym | 完整训练代码 |
| 算法 | enhanced GRPO、leave-one-out、无 KL、无 reward std normalization、最大 context 分母 | 准确 `n` 和 batch |
| reward | tests 全过为 1；失败或 verifier 超过 5 分钟为 0 | infra 与 verifier timeout 是否进一步分类 |
| Compact Filtering | 达到最大 context、20 分钟 generation timeout 或最大 step 的轨迹屏蔽自身 loss | 是否仍进入组统计的全部实现细节 |
| 训练 / 评测 | 训练 200 steps；评测 64K context、100 steps | GPU 数、训练墙钟、staleness 规则 |

SA-SWE 明确支持“horizon 轨迹保留 reward / advantage，但自身梯度屏蔽”的
实验起点。DeepSWE 只公开了自身 loss masking；它是否仍把该轨迹纳入组内
reward / advantage 统计没有披露，不能据此补全。DeepSWE 的公开 reproduction
也主要复现评测，不能当成完整 trainer 配方。

#### 6.2.3 R2E-Gym、SWE-Gym 与 Scale-SWE：主要是数据证据

| 来源 | 公开训练事实 | 对 RH2 的用途与边界 |
| --- | --- | --- |
| [R2E-Gym](https://arxiv.org/abs/2504.07164) | 约 8.7K 环境，Lite 约 4.5K；Claude Sonnet 成功轨迹；最多 40 steps、32K rollout、总计 10 分钟、单 action 90 秒；Qwen2.5-Coder 7B/14B/32B 做 full SFT，两 epoch、batch 8、`lr=1e-5`、20K context | 环境生产、RFT/SFT 和评测证据，不提供在线 GRPO 的 group、advantage、staleness 或 mask 配方 |
| [SWE-Gym](https://arxiv.org/abs/2412.21139) | 2438 个真实任务、11 个仓库；491 条 GPT-4o / Sonnet 成功轨迹，平均约 19 turns、19K tokens；Qwen2.5-Coder 7B/14B/32B，`lr=1e-4`、batch 8、最多 5 epochs、32K context、2～8 H100；推理最多 100 turns 或 32K | RH2 首训数据源；其主要结果是 rejection-sampling fine-tuning 与有限自训练，不是成熟在线 RL。论文还显示简单自训练容易被易题和成功样本分布主导 |
| [Scale-SWE](https://arxiv.org/abs/2602.09892) | 约 100K 环境、5.2K 仓库；25K 问题每题采 5 次，保留 71,498 条全测试通过轨迹、约 3.5B tokens；DeepSeek-V3.2 teacher，OpenHands scaffold，temperature 0.95、最多 100 turns；Qwen3-30B-A3B-Instruct student，131K context、batch 128、`lr=1e-5`、3 epochs | 证明当前目标模型适合大规模 coding SFT，但不是 RL。未披露统一 wall timeout、工具 timeout 与完整可复现仓库 |

#### 6.2.4 SETA、Endless Terminals 与 AgentRL：系统和算法对照

| 来源 | 配方要点 | 重要限制 |
| --- | --- | --- |
| [SETA](https://arxiv.org/abs/2607.10891) | Qwen3-8B non-thinking；4567 terminal 环境；GRPO；部分测试通过比例 reward + 全通过 bonus；论文 `n=16`、最多 30 iterations、28672 token、最大 off-policy 头距 2；reset 300s、agent reset 120s、agent step 900s、grading 600s；单机 8 GPU | 当前仓库同时出现 `n_trajs=16` 和 `actor.group_size=1`，与论文组语义冲突；main 不能直接视为论文复现配置 |
| [Endless Terminals](https://arxiv.org/abs/2601.16443) | 3255 terminal 任务；shell-only；PPO + critic；`n=16`、16 turns、每 turn 最多 2048 token、16K context、temperature 0.6；二元终局 reward、sequence-level loss averaging、无 KL；环境 wall timeout 5 分钟 | wall timeout 时不运行最终测试并保留 reward 0，turn 耗尽则仍测试。任务和 harness 明显比 Claude Code SWE 简单，只适合 PPO 与预算对照 |
| [AgentRL](https://arxiv.org/abs/2510.04206) | Qwen2.5 3B～32B / GLM4-9B；多种 AgentBench 环境；GRPO、`n=8`、temperature 0.8；异常终止、超交互次数或 response 长度 reward `-0.2`；rollout / actor / reference 独立资源池，TaskManager 队列持续生成 | 不是 SWE 专用配方；未披露统一 context、turn/time、batch 与数值 staleness 上限。价值在 ready queue、group-aware buffer 与异步拓扑 |

#### 6.2.5 OpenClaw-RL SWE-RL：接线参考，不是已验证成功配方

[OpenClaw-RL SWE-RL](https://github.com/Gen-Verse/OpenClaw-RL/blob/main/swe-rl/README.md)
使用 Qwen3-32B、slime、Mini-SWE-Agent 和远程 Docker 环境服务，示例配置
`n=8`、16K rollout context、每轮 4096 tokens，并给出 64 GPU / 8 节点脚本
与 checkpoint resume。它高度相关，但目前没有公开与配置对应的 SWE 模型、
训练曲线、成功率、坏样本比例和 staleness 分布。本文只将它列为 slime SWE
接线、远程容器池和产物布局的 E1 参考。

## 7. Frontier 模型技术报告能确认的训练事实

### 7.1 Kimi K3：固定 K partial rollout，不是 wall-clock 截断训练

来源：R13，[arXiv 2607.24653](https://arxiv.org/abs/2607.24653)，本地
`pdfs/k3_tech_report.pdf` 第 12～22 页。以下属于 E0，除非另行标注。

| 字段 | 报告明确披露 | 未披露或不能推导 |
| --- | --- | --- |
| 模型 | 2.8T MoE、104B 激活、1M context | 这些规模不构成 RH2 首训参数锚点 |
| 后训练阶段 | SFT 冷启动；训练 `3 个领域 × 3 个 reasoning effort = 9` 个 RL expert；最后用 MOPD 合并 | 各阶段数据量、步数、学习率 |
| partial rollout | 每个 prompt 采样 `K` 条，系统维持 `N×K` 活跃轨迹；完成比例达到 `lambda` 后暂停剩余轨迹并进入本轮训练；暂停项下一迭代优先恢复 | `lambda` 的数值、暂停调度源码 |
| PromptGroup | 只有同一 prompt 的全部 `K` 条 response 最终完成，才提交该组做 policy optimization | 不支持“缺一条后直接以 K-1 归一化”的推导 |
| staleness | 单条长轨迹可以跨多个训练迭代；使用 per-token regularization 约束局部更新 | 报告没有出现 PPO、GRPO 或 DIS，也没有给该正则公式 |
| reasoning-effort budget | 用冷启动模型估计每题 `b0(x)`；agentic 预算累计 reasoning 与 tool-call argument 输出 token；超过 `tau * b0(x)` 时将 task reward 覆盖为 `-1` | 这不是 wall-clock timeout；未披露 `tau`，也没说明超限轨迹自身 token 是否产生梯度 |
| harness | 将工具、system prompt、context management、skills、memory、subagent 等模块组合；按 task group 动态使用 Kimi Code、Claude Code、Codex 等配置 | 对应 white-box unified environment 没有开源，不能直接复用 |
| verifier / safety | AET 用独立 verifier 评最终环境状态，结合 public / hidden verifier、提交预算与惩罚；kernel 任务维护持续演进的 anti-hacking | 这些是 K3 训练系统能力，不是 AgentENV runtime 的内置能力 |
| rollout infra | co-located 训练、外部 CPU KV pool、训练状态 / NVMe 交换、KV 压力感知 auto-throttling | 不支持 RH2 改回 co-located；规模和约束不同 |
| sandbox scale | 报告称训练与评测期间创建 51,219,741 个 sandbox、涉及 1,505,678 个 image | 开源仓库不能独立复现这些生产统计 |

对 RepoHarness 的准确映射：

- K3 直接支持未来 `true_resume`：暂停慢轨迹、保留固定 `K` 语义、跨迭代继续执行；
- 它不直接支持“episode wall-clock 到点后，冻结当前 patch、评分并立即训练”；
- K3 的 token budget 是 policy-consumable budget，不能与 infra wall time 合并；
- AgentENV 只提供 sandbox 恢复，PromptGroup、capture ledger、policy version、ready queue 和 trainer ACK 仍由 RepoHarness / trainer runtime 拥有。

### 7.2 NVIDIA Nemotron 3 Ultra

来源：R2，本地 PDF 物理页 19、24～27、35～36。

- 550B 总参数、55B 激活；两阶段 SFT、统一多环境 RLVR、两轮异步 MOPD、
  最后 MTP boosting。
- SFT 第一阶段 sequence 294912、global batch 64、204800 samples；第二阶段
  sequence 515000、global batch 64、19200 samples。
- RLVR 覆盖 terminal、office、SWE、search、general tool、math/code/STEM，
  并刻意混合 harness 与交互格式。采用异步 GRPO，global batch 8192，
  每个 sample 生成 16 条 rollout，最大生成长度由 48K 提升到 64K。报告未
  说明 8192 的精确统计单位。
- MOPD 每批 1024 prompts、每题一条 rollout、最大生成 192K；使用
  behavior / proximal / current 三套 policy ratio、PPO clipping 和 IcePop
  token mask。
- SWE 流程为 agentic SFT、单步 PivotRL、多轮 SWE RL；hidden tests 给二元
  GRPO reward。SWE 最多 192K generation、200 agent turns。
- 达到最大 turn、agent timeout 或 evaluator timeout 的未完成轨迹，整条
  trajectory loss 被屏蔽；错误 reasoning / tool-call token 则给负 advantage，
  不修改 provenance loss mask。
- 反作弊包括物理删除 future git objects，以及运行期阻止 remote git 与
  GitHub web/raw/Pages 下载。
- one-step off-policy async 让 rollout 与更新重叠。故障统计中 generation /
  timeout 约 56%，sandbox / tool 约 36%，其他约 8%。
- `U`：SWE 专用 group、batch、RL steps、GPU 数、grading timeout、staleness
  阈值和数据规模。模型与部分 NeMo 资产公开，完整生产配方不可复现。

### 7.3 Qwen3-Coder-Next

来源：R3，本地 PDF 物理页 3、5、9～12。

- 80B 总参数、3B 激活；agentic mid-training、SFT/post-training、单轮与
  SWE expert RL、expert distillation。
- 训练涉及 SWE-agent、mini-swe-agent、OpenHands、Claude Code、Qwen-Code
  与 Terminus；MegaFlow 在 Kubernetes / Argo 中同置 rollout agent 与执行
  container，评分使用独立 container。
- mid-training 会删除无终止信号、任务失败或 tool-call 格式错误的轨迹；
  SWE 的 SFT / RL prompts 完全互斥，并按 pass rate 去除过易和噪声失败题。
- RL 使用 outcome reward；超过最大交互轮数有 unfinished-trajectory reward
  penalty；非法 tool-call token 有 token-level penalty。RL 后平均交互轮数
  从约 50 增到 130，但这不是训练上限。
- 反作弊删除 remotes / branches / tags，并阻止同时含 repo URL 与
  `git/curl/wget` 等网络关键词的命令，同时给 agent 反馈。
- `U`：RL 算法、group、batch、训练 turn/token/time/grading 限制、loss
  denominator、unfinished group 语义、异步、staleness、硬件和 steps。
  报告中的 300 turns 属于评测，不能拿来设训练 budget。

### 7.4 MiniMax-M2 Series

来源：R4，本地 PDF 物理页 12～22。

- 229.9B 总参数、9.8B 激活；大规模 rejection sampling / cleaning、
  interleaved-thinking SFT、mixed-domain RL。
- 任务覆盖真实 PR/SWE、Terminal-Gym、retrieval、office、spreadsheet、slide
  等 executable workspace；终态 artifact 决定 verifier 类型。
- agentic CISPO 将一次 model generation request 视为一个 policy action；
  `G` 出现在公式中但数值未披露，loss denominator 是组内全部 trajectory
  token 总和。
- 使用 reward-to-go、trajectory baseline、语言混用/tool format/reasoning
  过程 reward 与 task reward。另有基于 `T_completion/T_baseline` 的速度
  reward，但函数和权重未披露。
- Forge 分为 Agent Side、Gateway/Data Pool 与 Rollout/Train Engine，支持
  black-box / white-box agent；Windowed FIFO 示例 `W=0.3N`。gateway 捕获
  每次请求所见 context 与输出，并用 prefix tree 合并共享前缀。
- “192K token、数千 action、秒到小时”是能力范围，不是公开 hard cap。
- `U`：timeout / bad environment 的组语义、精确 mask、staleness correction、
  group/batch、硬件和 steps。Forge 未提供可运行公开实现。

### 7.5 GLM-5 与 GLM-5.2

来源：R5 与 R5b。

GLM-5：

- 744B 总参数、40B 激活；SFT、reasoning RL、agentic RL、general RL、
  cross-stage OPD。
- reasoning RL 是 fully on-policy GRPO：group 32、batch 32、`beta=2`、clip
  `0.2/0.28`。这些数值不能外推到 agentic RL。
- agentic RL 是 fully async group-wise optimization；每题 `K` 条但 `K`
  未披露，只训练模型生成 token，environment feedback 不进 loss。
- 超过 10K 个 SWE / terminal / search 环境；每个 response 记录参与生成的
  weight-version 序列、token ids 与 logprobs。版本差超过未披露的 `tau` 时
  丢弃；DIS 对超出双侧 ratio 窗口的 token 梯度置零。
- environment collapse 样本被排除。缺员后若有效成员超过原组一半，则重复
  有效成员补齐，否则丢组。这个做法保持张量形状，却改变成员权重，只能作
  消融候选。
- rollout 持续生成并按阈值送 trainer；每若干 gradient updates 同步权重；
  推理权重更新后重置 optimizer。准确阈值均未披露。

GLM-5.2：

- 官方网页报告没有披露 base checkpoint 与完整 SFT/RL 顺序。
- compaction 使同题 rollout 产生数量和长度不同的 sub-traces，因而转向
  critic-based PPO，并用 token-level loss 训练全部 compacted sub-traces。
- slime 支持 white-box、black-box、compact trajectory 与 subagent；并行
  OPD 合并十多个 expert，约两天，但硬件和 batch 未披露。
- Anti-Hack 先用规则高召回筛查，再由 LLM judge 判断意图；在线阻止违规
  tool call、返回 dummy result，并允许 rollout 继续。
- `U`：critic/GAE/clip、batch、训练 horizon、坏环境、staleness、steps 与
  硬件。官方网页列出的 2 小时、2000 turns / 6 小时、4 小时等是评测配置。

### 7.6 DeepSeek-V3.2 与 DeepSeek-V4

来源：R6a 与 R6b。

DeepSeek-V3.2：

- 从 128K DeepSeek-V3.1-Terminus 继续预训练；specialist fine-tuning / 大规模
  RL、specialist distillation、reasoning / agent / alignment 混合 GRPO。
- 最终模型经历数千 continued-RL steps，post-training compute 超过
  pretraining 的 10%；GPU 数未披露。
- GRPO 只减 group mean，不除组 reward 标准差。reward 包括规则 outcome、
  length penalty、language consistency 与 per-task rubric GRM。
- 只屏蔽“负 advantage 且 sampling/current 平均 KL 超阈值”的整条 sequence；
  保留 MoE routing 与 top-p/top-k sampling mask 对齐动作空间。
- 任务量：code agent 24667、search 50275、general agent 4417、code
  interpreter 5908。SWE 从数百万 issue/PR 构建，gold patch 必须 F2P>0 且
  P2F=0；general synthetic task 只保留 pass@100 非零环境。
- `U`：group/batch、训练 horizon、坏环境、异步/staleness、硬件。

DeepSeek-V4：

- V4-Pro 1.6T/49B active，V4-Flash 284B/13B active；specialist fine-tuning、
  specialist GRPO、十多个 teacher 的 full-vocabulary OPD；最终 mixed RL 被
  OPD 取代。
- specialist GRPO 参数只称接近既有工作；最终 OPD 使用 reverse-KL 全词表
  目标，并明确拒绝高方差 sampled-token approximation。
- generation request 使用 token-granular WAL；preemption 保存未完成 KV，
  恢复时继续 decode；硬故障用持久 token 重建 KV。报告明确指出从头重采
  未完成请求会引入长度偏差。
- DSec 管理 function/container/microVM/fullVM 与数十万实例，为 sandbox
  保留全局有序 command/result trajectory，避免恢复时重复非幂等操作。
- `U`：coding GRPO group/batch、训练 horizon、timeout reward/loss、
  staleness、steps、硬件。500 tool calls / 512K context 是评测配置。

### 7.7 Kimi K2 与 Kimi K2.5

来源：R7a 与 R7b。

Kimi K2：

- 1.04T/32.6B active；15.5T token 预训练；agentic synthesis/SFT、joint RL。
- SFT 数据使用 3K+ MCP tools、20K+ synthetic tools、user simulator、tool
  simulator 和 rubric judge，只保留成功轨迹；SWE 使用真实 sandbox。
- RL 的 SWE 来自 issue/PR + executable tests，Kubernetes sandbox 支持
  10K+ 并发；按 SFT pass@k 选择中等难度。
- K1.5-style group-relative optimization，组大小 `K` 未披露，另有 PTX loss
  与 temperature decay。超 per-sample token budget 会截断并施加 reward
  penalty。
- 同步 colocated 训练对长尾使用 partial rollout，下个 RL iteration 恢复，
  而不是评分后丢弃；1T 全权重更新报告少于 30 秒。

Kimi K2.5：

- 继承 K2 base；SFT、text/vision joint RL 与 PARL。
- 每题 `K` responses、group-mean reward；token ratio 超出 `[alpha,beta]`
  时梯度为零；分母是 batch 内全部 generated tokens。
- Toggle 在 budget-limited 与 max-token 阶段间交替；只在组平均正确率超过
  `lambda` 后启用 budget，budget 取正确 rollout 长度的某分位数并在训练
  开始时冻结。具体常数未披露。
- PARL 训练 orchestrator、冻结 subagents，reward 组合 task performance、
  parallel instantiation 与 finish rate。
- 统一 Gym 支持异步 coroutine 与递归 subrollout，最高 100K concurrent
  tasks；TITO 保存 token 与 inference logprobs，black-box 由 gateway 捕获。
- `U`：coding 数据量、训练 horizon、坏环境 / 缺员规则、staleness、nodes
  与 steps。256K 等属于评测配置。

### 7.8 MiniMax-M1

来源：R8，本地 PDF 物理页 2～11。

- 456B/45.9B active；继续预训练 7.5T token、CoT SFT、mixed RL。
- CISPO 使用 GRPO group-relative advantage，clip stop-gradient importance
  weight 而非 token objective；全局 token denominator、无 KL，配合 dynamic
  sampling 与 length penalty。
- 数据约 50K math、53K logic、30K competitive programming、数千 SWE、
  25K general。SWE 由 issue/PR、container 和 tests 构成。
- 最大生成从 40K 扩至 80K。若连续 3000 token 的概率都高于 0.99，提前
  终止异常 repetition loop；这不是对全部超长轨迹的统一惩罚。
- 512×H800，完整 RL 约三周，估算 53 万美元，是这批报告中训练成本较透明
  的一项。
- `U`：group、turn/time/grading、坏环境、异步/staleness、完整 batch 与
  steps。模型和公式公开，完整数据 / sandbox / trainer 不公开。

### 7.9 Composer 2

来源：R9，本地 PDF 物理页 1～12。

- 以 Kimi K2.5 1.04T/32B 为基座；code-heavy continued pretraining 以
  32K 为主并扩至 256K；短 SFT 后 large-scale async RL。
- 直接在与 Cursor 产品等价的 harness 中训练，使用真实 system prompt、
  tool schema、文件 / shell / 搜索 / web tools 和真实任务分布。
- 固定但未披露数值的 group size；single epoch、每 prompt 不重复训练、
  full-parameter Adam；类似 Dr.GRPO，去掉 length normalization，也不按组
  reward 标准差归一化。
- 小实验未观察到 overlong masking 收益，因此不屏蔽超过 max sequence 的
  rollout；self-summary 降低超限率，最终 reward 广播到 summary chain 的全部
  模型 token。这是 SA-SWE / DeepSWE mask 方案的重要反例。
- reward 组合 correctness、style、communication、tool behavior；长度惩罚
  同时考虑 thinking/tool-call/tool-output/final token、tool calls 和 turns。
- rollout 与训练独立，允许 mid-rollout 更新权重并做 MoE routing replay；
  rollout checkpoint 保存环境内存快照，group checkpoint 把带 advantage 与
  policy version 的 sequence 写 NFS，重启后恢复 ready groups。
- 训练跨 3 个 GPU region、4 个 CPU region，B300 上 `EP=8/CP=8`；总 GPU、
  group/batch、steps、staleness 与 importance correction 未披露。核心系统
  为内部实现，可复现性低。

### 7.10 跨报告冲突不是噪声，而是实验变量

| 问题 | 公开做法 |
| --- | --- |
| 超限 / 未完成 | Nemotron：整轨梯度 mask；Qwen/Kimi：reward penalty；Composer：不做 overlong mask；Kimi K2 / DeepSeek V4：暂停并恢复原 rollout |
| 缺员组 | GLM-5：有效成员过半则复制补齐，否则丢组；固定 K 系统等待完整组；GLM-5.2 / SAO 用 critic + single rollout 取消同题组约束 |
| advantage | GLM reasoning RL 用 mean/std；DeepSeek-V3.2、Composer 与 GLM agentic 只减 group mean |
| 异步 | Kimi K2 同步 colocated + partial rollout；Nemotron one-step async；GLM / Composer fully async |
| 超长 token 梯度 | Nemotron / SA-SWE mask；Composer 不 mask；CISPO 尽量保留；DIS / IcePop 按 off-policy ratio 屏蔽 |

这些冲突说明不存在一个可直接称作“业界标准”的 timeout 或 group repair
规则。RepoHarness 至少需要独立记录 `group_membership`、
`reward_disposition`、`gradient_disposition`、`termination_reason`、
`infra_failure_category` 和 `policy_version_span`。

## 8. 异步训练、长尾与组语义

### 8.1 固定组、冗余派发与动态过滤是三件不同的事

当前 `reference/ROLL/` 固定提交 `c7e3793570` 的 `GroupQueue` 保存明确的
`group_size`，最多并行派发 `group_size + group_size_redundancy`；只有收到
完整 `group_size` 才 ready，消费时也截成固定组。冗余执行用于减少长尾，
不把 GRPO 改成可变 `n`。

ROLL 动态采样会 oversample prompt，过滤全对或全错组，有效组足够后 abort
其余请求。当前 slime pin `e848052a65` 的 dynamic filter 默认关闭；启用后
也是整组替换，并断言 `len(group) == n`。这两种机制优化的是有效梯度比例，
都不能代替 RepoHarness 的安全、token provenance 或 eligibility gate。

关键位置：

```text
reference/ROLL/roll/distributed/scheduler/rollout_scheduler.py
reference/ROLL/roll/distributed/scheduler/user_defined_rollout_loop.py
reference/slime/slime/utils/arguments.py
reference/slime/slime/rollout/sglang_rollout.py
```

### 8.2 失败、截断和 `remove_sample` 不能混用

R10 的 error masking 证据来自 SFT：失败 turn 的 token loss 置零。其 RL
流水线会过滤瞬时 API、非确定工具响应和重复非法调用，并从同一初始状态
重采。这不能自动推出在线 GRPO 中 wall-time 截断的处理方式。

slime coding 示例把外层超时写成 `ABORTED + remove_sample + reward=0`，但
CLI 非零退出仍可能评分并返回训练样本。它是示例行为，不是 RH2 应继承的
语义。尤其是 `infra_failure` 不能伪装为 reward 0。

更关键的是，slime 当前训练侧先按 reward 计算组统计，之后才将
`remove_sample` 的 loss mask 置零；若实际样本数不符合固定形状，代码可能
把残余 batch 当成一个组归一化。因此：

```text
member present + reward enters group stats + own gradient disabled
```

可以由明确算法语义支持；而：

```text
member missing because execution never produced a trustworthy outcome
```

必须在 RH2 adapter / PromptGroupAssembler 处拒绝或等待，不能靠
`remove_sample` 表达，也不能静默变成 `n-1`。

### 8.3 branch fan-out 不增加 PromptGroup 成员数

slime `TrajectoryManager` 用消息树表示 subagent、compaction 和 token drift
分叉，并在不一致时 REALIGN 或 FORK；共享前缀只训练一次。一个 execution
可以展开为多个 trainable `Sample`，但这些 branches 共享同一个环境结果，
不是独立同题 rollout。PromptGroup 的 reward 统计必须先按 execution 计算，
再把 execution-level advantage 映射到其 branches，并用统一 denominator
避免 branch 数放大权重。

```text
reference/slime/slime/agent/trajectory.py
reference/slime/examples/coding_agent_rl/README.md
```

### 8.4 partial rollout、proxy 内重生成和 true-resume 不是同一机制

slime partial rollout 默认关闭。开启后，权重更新导致的部分响应可以回到
buffer，并可把旧段 `loss_mask` 设为 0；当前 fully-async worker 对 ABORTED
组主要是重新入队、从头重跑，并没有完整接通跨环境状态的 partial resume。
RH2 的 proxy 内同一 HTTP turn 重生成又是另一种机制：旧 attempt 不应暴露
给黑盒 harness，也不形成新的 PromptGroup member。首版不能同时打开多套
恢复语义后只用一个 `retry_count` 记账。

### 8.5 Fully async 的公开实现缺口

RollArt 报告描述 SampleBuffer、暂停新请求、保留在途请求、权重更新、KV
重算后续跑，并报告默认 staleness `alpha=1`；`alpha=2` 已在后期出现退化。
但当前公开 ROLL 中没有找到完全等价的生产实现。

slime 有跨 batch 长驻 worker和 `weight_version` 捕获，也有
`/get_weight_version`；然而当前 pin 的训练消费路径没有基于真实 version
span 的完整 admission，worker 也不拥有 RH2 所需的 durable failure ledger、
lease / ACK、PromptGroup 恢复和 trainer consume receipt。其权重 updater 还会
先递增版本，再 pause generation、flush cache 和发送权重；worker 本身不理解
协调器 phase / fence。

因此 FA 仍需两个不同层次的校正：

1. 组级 admission 使用逐轮真实 `weight_version`、组版本跨度、消费时当前版本和 staleness 上限；
2. faithful DIS 使用逐 token 行为策略 logprob 与训练时 current logprob。

组级拒绝不能替代 token-level off-policy correction，DIS 也不能使任意陈旧组
重新有效。RollArt 的 `alpha=1` 可以作为首训候选锚点，但必须由 FA-5 实测
校准，且不能用 trainer step id 冒充模型引擎版本。

### 8.6 当前组语义建议的证据状态

| 设计项 | 证据 | 当前建议 |
| --- | --- | --- |
| 完整固定 `n` | ROLL `GroupQueue`、slime dynamic filter、K3 固定 K 均支持 | 首训保持 `n=8`；禁止隐式 `n-1` |
| 冗余执行 | ROLL 有 `group_size_redundancy` | 可作为后续长尾优化；不是首版必需，不等于补采语义已经解决 |
| 策略 horizon | SA-SWE 明确保留 reward / advantage，但屏蔽该 execution 自身梯度；DeepSWE 只明确披露自身 loss masking，是否保留组统计为 `U` | 首训可优先把 SA-SWE 语义作为可解释基线；不把 provenance `loss_mask` 改写成算法事实，也不把 DeepSWE 的未知项补成同一结论 |
| infra failure | 多来源均显示需要过滤或重采 | `reward=None`、不进组统计；结构化归因和拒绝率熔断 |
| 零方差组 | ROLL / slime 支持动态过滤 | 首训先关闭或只审计，避免同时改变任务覆盖；后续单独消融 |
| OPD | ROLL 与 slime 均有实现 | 作为独立实验轴，不能与首训 GRPO + DIS 同时引入 |

### 8.7 推荐使用三轴终止语义，而不是一个 eligibility 布尔值

综合 SA-SWE、DeepSWE、Nemotron、Composer 2、K3、Prime 和当前代码，建议
将下面的表作为 FA-2A 决策输入，而不是提前宣布全部定案：

| 终止或失败类型 | 进入组 reward / advantage 统计 | 自身 policy gradient | fixed-n 处理 |
| --- | --- | --- | --- |
| 正常解决，reward=1 | 是 | 是 | 正常成员 |
| 正常未解决，reward=0 | 是 | 是 | 正常负样本，绝不能当缺员 |
| max turn / context / policy token budget；已静止、capture 完整、快照可评分 | 是 | 首训建议屏蔽，后续与负向训练做消融 | 仍是完整成员 |
| `finish_reason=length`；完整响应已交付且可冻结评分 | 是 | 首训建议屏蔽 | 仍是完整成员 |
| mid-generation abort、半截 SSE、capture 未闭合 | 否 | 否 | 真缺员；整组不进本次在线更新 |
| patch 导致测试确定性超时 | 是，通常 reward=0 | 是 | 模型真实失败 |
| grader / container / image / hidden verifier 基础设施失败 | 否 | 否 | 对同一冻结快照做有界幂等重试；仍失败则缺员 |
| `attempted_blocked` 且无泄漏、无副作用 | 是 | 是 | 合法安全学习行为 |
| 命令实际越权执行、测试篡改、hidden 数据泄漏 | 否 | 否 | 拒绝并按 fault domain 决定 task quarantine / run halt |
| staleness 合格但仅部分 token 通过 DIS | 是 | 仅合格 token | 仍是成员 |
| 整条轨迹过度陈旧，或 DIS 有效 token 为零 | 否 | 否 | 当前更新中的缺员；整组不进在线 batch |

这里的“整组不进在线更新”不等于删除 artifact。可信轨迹、失败事实和拒绝
报告都应留在审计存储中。

公开证据不是单一结论：

- SA-SWE 最明确地保留 max-context / max-step 轨迹的 reward 与 advantage，
  只屏蔽其自身梯度；DeepSWE 只明确了 Compact Filtering 会屏蔽自身 loss，
  是否保留组统计没有披露；
- DAPO 报告直接惩罚截断 response 会引入 reward noise，曾使用 overlong
  masking，最终最佳配方更偏 soft overlong reward shaping；
- Nemotron 对 max turns 或 agent / eval timeout 的未完成轨迹屏蔽 loss，
  但对 malformed tool-call token 单独给负 advantage；
- Composer 2 的小规模实验没有观察到 overlong masking 收益，因此不屏蔽
  max-sequence rollout；
- K3 对相对 token budget 超限直接设 reward=-1，并用 true-resume 处理尚未
  完成的固定 K 轨迹。

所以“horizon 参与组统计、自身不反传”是证据最强的首训起点，不是普遍
定律。它必须预注册，并与“把可归因 horizon 作为负向训练信号”做后续消融。

### 8.8 为什么不能把缺员成员静默删除

以 `n=8`、reward `[1,0,0,0,0,0,0,0]`、不除 reward 标准差为例：

```text
GRPO: success advantage = 0.875
      each failure advantage = -0.125

删除一个 reward=0 成员，改成 variable n=7：
      success advantage = 0.8571
      each remaining failure advantage = -0.1429
```

删除一条会改变全部兄弟样本的 advantage。若保留 horizon 成员的 reward=0，
只屏蔽它自身梯度，其他成员仍使用原固定组统计。这个目标依然经过过滤，
不能称为完全无偏，但至少没有把“是否反传”误写成“从 baseline 删除”。

整组拒绝也有选择偏差。若每个成员独立有 5% 不可用概率，`n=8` 的整组
存活率只有 `0.95^8 = 66.34%`，即约 33.66% 的组被丢弃。真实 timeout 和
infra failure 往往与任务长度、难度相关，偏差通常比独立模型更严重。因此
fixed-n 并不免除监控义务：必须按 termination、题目难度、长度和仓库统计
丢组率，并设置 fail-loud 熔断。

### 8.9 算法名称需要保持准确

- RLOO 要求同一 prompt 的样本来自同一策略并近似 i.i.d.。跨版本补采会
  破坏此前提；DIS 能校正 token action ratio，不能修复选择性缺失偏差。
- 完整 Dr.GRPO 不只是关闭 reward standard deviation；还要去掉逐 response
  长度归一化并采用固定全局 token-budget 分母。若未实现完整分母，RH2 应
  写“Dr-style group advantage”，不能写成 Dr.GRPO 复现。
- DAPO dynamic sampling 过滤的是完整 all-0 / all-1 零梯度组，再采新的
  完整组；它不是对缺员成员做补采，也会把训练分布推向中等难度任务。
- K3 恢复的是同一轨迹；它没有重采一条新成员来替代旧成员。

### 8.10 当前实现与该语义的差距

1. `rh2/experiments/fa_bringup/rollout_entry.py` 的
   `_InterimGroupCollector` 仍是过渡实现：任一 abort 即整组弃置。它只适合
   真缺员，不能决定已评分 horizon 的最终语义。
2. `rh2/src/repoharness2/adapters/slime/batch_admission.py` 当前要求每个
   execution 至少一个 trainable token，尚不能表达“参与组统计但自身全梯度
   屏蔽”。
3. prime-rl 的顺序值得参考：先对完整 survivors 计算组 advantage，再运行
   rollout filter；被过滤样本不送 trainer，但其 reward 已参与 baseline。
4. FA-2 应形成两个视图：`GroupOutcomeView` 包含全部 present 成员及 reward；
   `TrainableBranchView` 只包含实际进入反传的 branches。
5. 建议新增独立的 `gradient_disposition = train | masked_external_limit |
   rejected`。它不得覆盖 provenance `loss_mask`，也不得塞进 eligibility 的
   单一布尔值。
6. `termination_kind` 至少需要区分 `policy_turn_limit`、`context_limit`、
   `generation_length_limit`、`hard_wall_timeout` 与
   `mid_generation_abort`。

这一组改动会影响公共契约与训练分布，属于 T0 决策；本文只记录证据和推荐，
不替用户拍板。

### 8.11 GRPO 之后的算法演进证据

R14 CompactionRL 与 R15 SAO 已有单独分析：
`docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md`。
本矩阵只保留影响基础设施契约的结论。

SAO：

- 将每题一条 rollout 的 single-rollout sampling 与 critic 结合，取消等待同题
  fixed group 的必要；
- 使用 rollout behavior policy 与 current policy 的 token ratio 做 direct
  importance sampling，并施加严格双侧 token clipping；
- 使用 Skip-Observation GAE，只在模型 action token 之间传播 credit；
- value model 需要预训练，并对 critic 使用专门更新策略；只把 slime 的
  `advantage_estimator=ppo` 打开不能称为 SAO；
- 论文显示 SAO 与 GRPO+DIS 在早期接近，较长训练后才拉开。当前 30～50
  step 首训不适合把 SAO 优势当作必然可见目标。

CompactionRL：

- summary generation 本身是 policy action；原始 summary token 可训练，
  resume prompt 中复制的 summary / history / observation 必须 mask；
- execution 与 summary segments 共享最终 task reward；token-level loss
  normalization 消除“每个 segment 各自平均”造成的 segment-count 偏置，
  使每个 trainable token 等权，但不保证每条轨迹等权，更长轨迹仍可能因
  trainable token 更多而贡献更大的总梯度；
- cross-trajectory GAE 根据后续 trainable token 距离修正早期 segment 的
  credit；
- 论文没有公开“SAO + CompactionRL”的完整联合 loss，不能自行把两个公式
  机械拼接后宣称复现。

对 RH2 的影响是保持算法中立的事实契约：segment lineage、summary token
provenance、behavior logprob、policy version、observation/action mask 与多种
denominator 都应准确提供；选择 GRPO、SAO、PPO 或 CompactionRL 仍归 trainer。

## 9. 环境、sandbox、评分与 anti-cheat

### 9.1 AgentENV 的能力和边界

来源：[官方仓库](https://github.com/kvcache-ai/AgentENV)，本地固定提交
`6296bc4be7ad79eb3a278eb5264ef011c341adf5`。以下是 E1 代码事实：

| 能力 | 代码事实 | RepoHarness 边界 |
| --- | --- | --- |
| 生命周期 | `Creating -> Running -> Pausing -> Paused -> Resuming`；pause 捕获内存和可写磁盘层 | 可作为未来可恢复 Runtime，不替代 episode / group 状态机 |
| 持久恢复 | paused record 与 artifact 可跨 AgentENV server restart 恢复 | 进程若在 `Resuming` 状态崩溃，当前启动恢复会丢弃该记录与 artifact；不是无条件 exactly-once |
| snapshot / fork | persistent snapshot 与 pause artifact 是不同 repository；running sandbox 可在同节点 fork；单次 fork 请求默认 1 个 child、OpenAPI 上限 100，实际并发仍受节点容量约束 | fork 可作为 grader-side 副作用隔离组件，但不自动提供可信 clean checkout、只读 hidden verifier、评分隔离或防污染 |
| 可观测性 | Prometheus 记录 create、pause、resume、fork 等生命周期阶段直方图 | 可以接入 RH2 timing，不应另造估算值 |
| 多节点 | gateway / scheduler 仍偏 prototype；binding 默认在内存，配置 Redis 后才有进程外持久性 | 近期不能把它写成成熟的跨节点恢复控制面 |
| 安全 | Firecracker microVM 隔离强于普通共享内核容器 | 当前认证只检查 header 非空；默认允许外网；支持 CIDR 规则但不支持 domain allow rule；仍需 RepoHarness SWE-Safety |
| API | 提供 E2B 兼容 HTTP API | slime 按 task metadata 传 OCI image，AgentENV 标准创建要求 `templateID`；需要 image-to-template 映射或薄 create adapter，不能只改 URL |

关键代码入口：

```text
reference/AgentEnv/docs/src/concepts/sandboxes.md
reference/AgentEnv/src/orchestrator/service.rs
reference/AgentEnv/src/orchestrator/persistence/file_backed.rs
reference/AgentEnv/docs/src/internals/persistence-artifact-inventory.md
reference/AgentEnv/src/observability/prometheus.rs
reference/AgentEnv/src/api/impls/auth.rs
reference/AgentEnv/src/sandbox/network/policy.rs
reference/AgentEnv/src/api/openapi.yml
reference/slime/slime/agent/sandbox.py
```

许可证是 MIT。AgentENV 不拥有 command policy、secret visibility、hidden
verifier、git sanitization、artifact public projection、token capture 或 training
eligibility；把它接入 RH2 只会替换 Runtime 的一个实现，不会替换 RH2 的核心定位。

### 9.2 其余环境与安全证据

| 来源 | 明确做法 | RepoHarness 结论 |
| --- | --- | --- |
| MAI-Thinking-1 | 环境生产先验证 empty patch / golden patch，隔离 agent execution 与评分，使用 SEE 类沙箱和系统化质量漏斗 | 环境质量在 ingestion 时 fail-closed；运行期只消费冻结、带 digest 与 validation report 的包 |
| ROME / ROLL | 大规模候选经难度、环境稳定性与 spec-test 一致性过滤；测试只在评分期挂载 | 训练任务数量不能代替可验证性；hidden material 不进入 agent workspace |
| Nemotron | 物理删除 future git objects；阻止 remote git 与 GitHub web/raw/Pages；失败细分到 generation、sandbox/tool 等 | anti-cheat 需要物化期、运行期和评分期纵深；infra failure 与模型失败分开 |
| Qwen3-Coder-Next | 删除 remote / branch / tag；对 repo URL + `git/curl/wget` 组合命令做在线拦截并向 agent 反馈 | 在线拦截应留行为反馈，但命令词匹配只是其中一层，不能替代网络 egress policy |
| GLM-5.2 | 规则层先高召回检测，再由 LLM judge 判断意图；违规 tool call 被阻止、返回 dummy observation，rollout 继续 | `attempted_blocked` 且无泄漏可以是可信训练行为；是否引入 LLM judge 是单独成本与可信度决策 |
| K3 AET | public verifier 提供诊断，hidden verifier 评 held-out 场景；限制提交次数并施加惩罚；独立 verifier 只看最终环境状态 | public feedback、hidden outcome 与提交预算应是 rubric / environment 契约，不属于 AgentENV runtime |
| K3 kernel | 持续扩充 hacking detector，覆盖 replay、input caching 与精度削减等新策略 | anti-cheat 是持续更新的风险库，不是一次性静态 denylist |
| ROCK | Admin / Worker / Rocklet / EnvHub、agent 安装与 sandbox-side model proxy | Runtime 服务化参考；其 request JSONL record/replay 不等于 token-faithful training artifact |

共同边界：sandbox 隔离强度、hidden verifier 可见性、命令策略、网络策略、
评分 checkout、artifact public projection 与训练资格是不同防线。引入
AgentENV 或 ROCK 不会自动获得后五项；RepoHarness 的 SWE-Safety 层仍有独立
价值。

## 10. 对 RepoHarness 当前实验的约束

### 10.1 近期不应被新资料改变的部分

- 先完成 FA 正式链，再做大预算训练；不能用算法切换掩盖 adapter 和身份账目问题。
- 首个 GRPO 基线关闭 compaction；无法解释的上下文收缩不得进入该基线。
- token provenance、行为策略 logprob、weight version、staleness 和训练消费决定必须可审计。
- infra failure 不得伪装成 `reward=0`；安全泄漏与事实矛盾继续 fail-closed。
- 环境、harness、评分和 trainer 保持 ownership 解耦。

### 10.2 需要在首训前单独拍板的实验语义

- turn/context horizon 是否保留为组成员，reward 如何定义，自身梯度是否屏蔽；
- hard wall 中策略时间与基础设施时间如何拆账，以及无法完成静止序列时如何处置；
- 固定 `n` 下真正缺失成员的整组拒绝规则与损耗监控；
- 每类 rejection 的熔断阈值，避免 fail-closed 静默改变训练分布；
- wall-clock、turn、context 和 grading 预算的预注册值，以及是否按任务难度分桶。

### 10.3 需要增加的可观测事实

```text
episode_deadline_seconds
policy_active_seconds
model_queue_seconds
model_generation_seconds
tool_execution_seconds
sandbox_prepare_seconds
sandbox_idle_while_model_seconds
grading_queue_seconds
grading_execution_seconds
termination_reason
group_membership
reward_disposition
gradient_disposition
```

这些字段用于解释训练分布，不表示 RepoHarness 要自己实现 SGLang、slime 或 sandbox 内核。能够从后端读取的事实应由 adapter 规范化，不能复制一套估计值。

### 10.4 首训参数如何使用这些证据

1. `n=8` 是 SA-SWE、AgentRL 和多项公开系统中反复出现的可用锚点；首训
   可以保持，但它是预注册选择，不是 GRPO 唯一合法值。
2. 32K context、50 turns 是 SA-SWE 的成功训练锚点，适合作为起始 horizon。
   Nemotron 192K/200 turns、MiniMax 80K、Composer 数百 tool calls 都来自
   更大模型或不同系统，不能直接照搬。
3. 不应先验把 600 秒写成统一 episode wall limit。先对 50～100 题、每题
   `n=8` 做 pre-RL 诊断，拆出模型等待、工具执行、sandbox、评分和清理，
   再按成功样本的 P90 / P95 与成本上限设置 watchdog。
4. SA-SWE 的 batch 64 不能机械照搬到 8 卡 MoE。保持固定组语义后，由
   ready queue 与 batch admission 按 DP/PP 和 token packing 选择完整组。
5. “Qwen3-Coder-30B-A3B + SWE-Gym + Claude Code + slime + faithful DIS”
   是有依据的 RH2 工程组合，但没有公开论文完整验证过。报告中应写成受
   SA-SWE 算法、SWE-Gym 数据和 GLM/slime 系统证据启发，不写成论文复现。
6. 首训保持 binary verifier reward；速度奖励、复杂 process reward、
   effective-member duplication、dynamic easy-group filtering 与 OPD 都作为
   后续独立消融，避免无法归因。
7. version-aware fully async + faithful DIS 方向可以保持，但没有来源验证了
   RH2 的整套组合。首训前必须实测逐 token version/logprob、消费时 staleness、
   DIS 有效 token 比例、组拒绝率和训练后端 ACK。

## 11. 尚未由公开资料回答的问题

1. 大多数 frontier 模型没有披露 wall-clock timeout 与基础设施耗时的精确拆分。
2. 很少有报告同时公开“超 turn/context 的 reward、组统计与自身梯度”三种决定。
3. 厂商常报告 fully async，但不披露每次模型调用的版本跨度分布、拒绝率和最终有效 token 比例。
4. 黑盒 harness 的原生重试、compaction、subagent 并发与训练身份如何统一，公开生产实现仍很少。
5. SAO 与 CompactionRL 都用于 GLM-5.2，但公开资料没有给出两者完整联合目标，不能自行拼接后宣称复现。

## 12. 维护方式

新增来源时执行以下顺序：

1. 在 `manifest.json` 登记本地文件、来源 URL 和 SHA-256；
2. 在 `README.md` 增加资料入口与阅读重点；
3. 在本文按统一字段登记明确事实和 `U`；
4. 只有影响当前阶段 T0 决策时，才另建决策包；
5. 任何从外部证据推导出的 RepoHarness 建议都标为 E3，并附上验证或消融条件。
