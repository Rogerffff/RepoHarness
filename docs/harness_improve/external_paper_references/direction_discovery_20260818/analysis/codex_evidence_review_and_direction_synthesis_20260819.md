# 第一轮方向发现：Codex 独立核验与后续目标建议

日期：2026-08-19
状态：**讨论材料，不是 owner 定案，不是实施计划，也不改变当前训练语义或闸门。**

## 0. 本文范围

本文整理和审查以下两份 Pro 原始输出：

- Blind：`responses/pro_blind_discovery_raw_20260818.md`
- Seeded：`responses/pro_seeded_discovery_raw_20260818.md`

两份原文单独保存，本文不重写它们，也不把其中的引用自动视为事实。本文完成的工作是：

1. 将两份候选按同一研究问题重新归组；
2. 回到一手论文、官方报告、官方仓库和固定 commit，抽查承重事实；
3. 对照 RepoHarness 当前权威状态、八卡预实验和数据冻结现状；
4. 给出 Codex 对后续方向的暂定建议和仍需讨论的未知。

需要特别说明：两份 Pro 虽然在相互隔离的会话中完成，但来自相同模型、共享同一项目说明，
检索窗口也相同。它们的重合只能算交叉支持，不能算论文意义上的独立复现。

## 1. 结论摘要

原先的“环境、多 harness、OPD/MOPD”不应原样作为三条同级实施主线。Codex 当前建议是：

| 层级 | 方向 | 暂定判断 |
|---|---|---|
| 主研究线 A | 可验证环境与数据生产 | 保留，并升级为第一优先级 |
| 主研究线 B | 多 harness 训练与跨接口泛化 | 保留，是当前最清晰的模型能力命题 |
| 条件式算法线 C | OPD/MOPD | 保留专项研究；先验证单 teacher OPD，暂不承诺完整 MOPD |
| 可信训练底座 | version-aware fully-async、faithful DIS、轨迹与版本治理 | 必须完成，但不是另一条新模型能力方向 |
| 新能力探针 | tool-fault recovery、context/memory | 先做低成本探针，最多竞争一个后续训练槽位 |

可以把最终项目的统一命题暂时表述为：

> 在经过可学习性校准和 verifier 对抗加固的可执行环境上，通过语义等价的多 harness
> 训练，获得对未见工具接口和交互协议更稳健的 agentic 能力；由 version-aware fully-async
> RL 基础设施保证样本、reward、轨迹和模型版本正确。只有在前述研究自然产生多个同源
> specialist 后，才考虑用 OPD/MOPD 做能力整合与保持。

这不是最终题目。它的价值在于把环境、harness、训练系统、模型能力和评测串成一个可证伪
闭环，而不是把多个前沿组件并排堆在简历中。

## 2. 两份 Pro 输出的共同发现与差异

### 2.1 候选对齐

| 统一方向 | Blind 输出 | Seeded 输出 | Codex 归类 |
|---|---|---|---|
| 跨 harness 语义不变性 | 候选 1 | 候选 3 | 顶层模型能力命题 |
| 环境资格、难度与演化 | 候选 2、3 | 候选 1、11 | 主研究线 |
| verifier hardening | 候选 4 | 候选 2 | 环境训练资格的一等属性 |
| fully-async 正确性 | 候选 5 | 候选 8 | 当前必须完成的可信底座 |
| 过程信用、反事实 replay | 候选 6 | 候选 9 | 支持机制，暂不独立立项 |
| tool-fault recovery | 候选 8 | 候选 5 | 高价值低成本探针 |
| context/memory/compaction | 候选 6 部分覆盖 | 候选 4 | 中长期候选，当前证据较新 |
| OPD/MOPD 与能力保持 | 候选 7 | 候选 6 | 条件式算法线 |
| held-out/version 治理 | 候选 10 | 候选 10 | 必备评测治理，不单独立项 |
| 中立轨迹 IR | 候选 9 | 分散在候选 3、8 | RepoHarness 支撑资产 |

Blind 输出更擅长把系统正确性、过程信用和环境组合放入完整闭环，但把若干 RepoHarness
已经在做的工作重新列成了“新方向”。Seeded 输出发现了更多 2026 年 8 月材料，把环境资格
细化为 solver calibration、verifier integrity 和 failure-driven curation；但也更容易高估刚发布
论文和初始代码仓库的成熟度。

### 2.2 整体质量判断

两份报告总体质量较高。抽查中没有发现虚构的承重论文、官方报告或关键 commit，多数数值
和负结果能由一手来源确认。它们适合做证据地图，但 Top 5 不能直接转换成五条项目线程，
原因包括：

- 很多候选与 RepoHarness 当前既有定位高度重合；
- 大量 2026 年新工作只有作者结果，没有不同团队的完整训练复现；
- “框架有代码”“旗舰模型使用过”“受控消融证明有效”是三个不同成熟度，不能互相外推；
- Pro 给出的八卡最小实验通常是建议，不是由论文训练时长推导出的资源证据；
- 本机和订阅 agent 能降低环境生产的本地 GPU 占用，但 API、容器重放、solver、人工复核和
  最终 learnability 验证仍有成本。

### 2.3 核验中发现的主要纠错

1. [CalibForge](https://arxiv.org/abs/2608.06352) 的 5,431 个任务和 solver-relative
   calibration 结果真实，但核心训练是多轮全参数 SFT，不是在线 RL；正式实验使用 64×H20。
   其公开仓库提供数据、模型和评测入口，但不等于完整环境生产与训练流水线已经公开。
2. [Harness Interplay](https://arxiv.org/abs/2606.25447) 的三种 harness、Qwen2.5
   3B/7B、GRPO/GiGPO 和显著性能差距真实，但环境只有 ALFWorld，总资源约 1,800 H200
   GPU-hours。它证明 harness 会影响训练，没有证明多 harness 随机化必然学出接口不变能力。
3. [Hardening Agent Benchmarks](https://arxiv.org/abs/2606.08960) 的 1,968 个任务、
   323 个可攻击任务和 3,632 条攻击轨迹真实。它证明 verifier 可以被攻击和加固，但不直接
   证明加固环境训练出的模型更诚实；攻击存活率下降也不能以大量杀死合法解为代价。
4. Reward Hacking Benchmark 的论文写明代码和数据将在 publication 时发布，当前不应标成
   已有公开实现；ReliabilityBench、RACES、EvoEnv 的官方可复用实现也未得到充分确认。
5. [TRACE](https://arxiv.org/abs/2608.06503) 优化 compaction policy/prompt，不更新目标
   agent 权重；[Verifiable Memory](https://arxiv.org/abs/2608.03137) 的论文训练描述真实，
   但当前公开仓库还不是完整的有状态 memory transition 训练闭环。
6. [BENCH2ROBUST](https://arxiv.org/abs/2608.11977) 的训练硬件和主要配置并非全部
   unknown：论文披露了 8×H100 80GB、Qwen3-4B-Thinking、slime、训练题量和 rollout
   配置；未知的是 wall time 和 user-simulator API 成本。它还显示运行时 BTM 的收益大于
   纯权重训练收益，因此必须区分 runtime scaffold 改进与模型真正学到恢复能力。
7. slime 的 `c1dd9ab` 修复是 `--log-correct-samples` 诊断日志与 DP-local sample 的配对，
   不应扩大成 policy loss 已把 reward 分配给错误训练样本。其他 fully-async 样本守恒、
   resume lineage 和 checkpoint/eval handoff 修复仍然能证明这类正确性问题真实存在。

## 3. 主研究线 A：可验证环境生产与训练资格

### 3.1 为什么保留并提升优先级

RepoHarness 已经把环境质量、评分隔离、anti-cheat、EligibilityGate 和训练资格治理作为核心
价值。这说明两份 Pro 发现的环境资格和 verifier hardening 不是完全新增方向，而是对现有定位
的外部验证和深化。

但当前环境还没有真正准备好进入正式训练：

- SWE-Gym Lite 静态门存活 216/230；
- held-out 只有 542 道候选；
- 216 道题仍需 S2-1 环境四门和 GPU pass-rate 预筛；
- `rh2_formal_training_allowed=false`。

权威现状见：

- `docs/agentic_RL/repo_harness_rh2_workstreams/data_freeze/data_freeze_report.md`
- `docs/agentic_RL/repo_harness_rh2_workstreams/00-project-status.md`

因此环境资格不仅是未来研究方向，也是首训前仍未完成的必要条件。

### 3.2 环境主线应升级成什么

不建议把目标写成“尽可能收集更多 RL 环境”。更完整的闭环是：

```text
候选任务生成或导入
→ model-free validity（环境可启动、依赖可恢复、确定性、gold-pass、no-op-fail）
→ solver-relative learnability（对当前 policy 是否处于可学习区）
→ adversarial verifier hardening（reward 是否代表真实目标）
→ policy-relative difficulty / curriculum
→ 版本化训练资格与数据血缘
→ 按仓库、生成规则、漏洞家族隔离的 held-out 环境家族
```

其中真正相对现有 rh2 新增、并可形成研究贡献的部分主要是：

1. **solver-relative learnability**：不能把“gold 能过”当成“当前模型可学”。可按固定模型、
   harness、预算和版本统计 all-pass、all-fail、solver 分歧、strong-pass/weak-fail，并验证这些
   分桶是否预测后续训练轨迹质量和学习增益。
2. **环境组合、变异与演化**：不只是加入更多公开数据源，而是从可执行任务中生成新的
   依赖、约束、故障和 verifier 组合，并按生成规则留出未见家族。
3. **verifier hardening 的双目标**：同时测 exploit survival 和 honest solution survival，避免
   “通过拒绝一切补丁实现零攻击率”。还需覆盖未见 exploit family 的迁移。
4. **policy-relative 难度控制**：静态难度标签不足，需要随着模型版本更新资格或采样权重，
   同时保留 frozen held-out，避免评测随训练一起移动。
5. **生产角色隔离**：producer、solver、verifier、auditor 不能长期由同一模型同时承担；任务、
   轨迹、修复和淘汰原因需要可重放的数据血缘。

### 3.3 可扩展的环境范围

环境主线不应永久限制在 SWE repository repair，但也不应为了数量机械收集 benchmark。可优先
考虑仍具备可执行、可隔离、可重放 verifier 的家族，例如 terminal、依赖恢复、函数调用、
SQL/MCP、受控搜索、工具 DAG、故障恢复和不可完成任务识别。真实账户、支付、动态网页和
不可回滚外部副作用环境需要额外安全与重放设计，当前不宜作为第一批。

本机、Docker、Codex/Claude 订阅 agent 和模型 API 可以承担大量生成、代码变异、依赖修复、
测试生成、候选求解、攻击 verifier 和轨迹审计工作；真正判断 learnability 和训练收益时，仍然
需要模型 rollout 或小规模训练。

## 4. 主研究线 B：多 harness 与跨接口语义泛化

### 4.1 为什么继续保留

外部证据现在足以确认 harness 不是无关紧要的 wrapper：

- Harness Interplay 在受控环境中观察到 3B + 高信息 harness 可超过 7B + 低信息 harness，
  且训练时使用目标 harness 明显优于训练后再替换；
- [Harness-Bench](https://arxiv.org/abs/2605.27922) 在 106 个任务、6 个 harness、8 个
  backend 上观察到显著 harness gap，但它是诊断评测，不是多 harness 训练证据；
- [KAT-Coder-V2.5](https://arxiv.org/abs/2607.05471) 报告实际使用 harness randomization，
  但没有公开固定数据和计算量、仅改变 harness 多样性的受控消融；
- [Polar](https://arxiv.org/abs/2605.24220) 证明多个黑盒 harness 的 token-faithful 捕获和训练
  接入可行，但不同 harness 收益差距很大，不能当成已经证明接口不变性。

因此，真正仍未解决且适合 RepoHarness 的问题是：

> 相同任务语义经不同工具名、参数 schema、观察格式、system prompt、context policy 和
> agent loop 表达后，模型是否仍能保持能力；多 harness 训练能否提升训练时未见接口上的表现，
> 而不是只记住更多已见模板？

### 4.2 不应怎样做

仅接入 Codex、OpenCode、PI、DeepSeek、Prime Agent，然后分别报告分数，不足以形成可归因
研究，原因包括：

- 每套 harness 的工具能力和默认预算可能不同；
- parser 宽松度、编辑工具粒度、context 长度、错误信息量和 retry 策略会共同变化；
- before/after 变化可能来自更强的 scaffold，而不是模型权重；
- 多套真实 harness 很难形成固定一个变量的完整 factorial。

### 4.3 建议的因果设计

更合适的设计是建立中立的 canonical semantic event/operation 契约：固定 latent task、workspace、
verifier、有效操作、token/turn/时间预算和最终工件要求，再派生多个结构等价的 harness 表达。

可控变化包括：

- tool name、参数 schema、工具粒度；
- patch/edit/write 的表达方式；
- observation 和 error 格式；
- message rendering 和 system prompt；
- 权限提示与失败回执；
- context 管理和 compaction policy；
- agent loop 控制流。

训练和评测至少需要：

```text
单 harness 训练 → 同 harness 评测（bring-up 基线）
单 harness 训练 → 已见其他 harness 评测
多 harness 训练 → 每个已见 harness 评测
多 harness 训练 → 未见 schema/prompt/error/loop 组合评测
```

核心指标不应只有平均分，还应包括 held-out harness 性能、跨 harness 方差、正确集合 turnover、
失败类型、预算归一化结果，以及 capability retention。raw token trace 用于训练保真，canonical trace
用于比较语义等价操作；二者不能互相替代。

首轮实验设计中的“训练与 before/after 使用同一 harness”仍适合作为链路基线。多 harness 是
后续研究矩阵，不应为了追求最终叙事而直接膨胀第一次正式训练。

## 5. 条件式算法线 C：OPD 与 MOPD

### 5.1 为什么不删除 OPD

当前 pin 的 slime 已有直接实现基础：

- 外部 SGLang teacher 模式；
- Megatron 内置 teacher 模式；
- 对学生实际 token 序列获取 teacher logprob；
- teacher logprob 注入 advantage；
- Qwen3-8B student / Qwen3-32B teacher 示例和相关配置。

本地文档：`reference/slime/docs/en/advanced/on-policy-distillation.md`。另有
[thu-nics/mini-opd](https://github.com/thu-nics/mini-opd) 可作为最小实现参考。

所以单 teacher OPD 值得做接口和训练 proof/kill，不应因为两份 Pro 没把它列入 Top 5 就删除。

### 5.2 为什么完整 MOPD 暂时降级

[MOPD](https://arxiv.org/html/2606.30406v1) 的一手证据真实：它使用 student 自身 rollout，
teacher 对同一 token prefix 做 prefill，并以逐 token reverse-KL 整合领域能力；在 Qwen3-30B-A3B
和 MiMo-V2-Flash 上有实际训练和受控比较。

但有四个关键边界：

1. 成功 teacher 主要从与 student 相同的 SFT checkpoint 分叉，先分别做领域 RL；
2. 换成更强但跨源的 Qwen3-235B teacher 后，初始 token KL 由约 0.04 升到 0.19，PG 退化，
   top-k 版本约在 step 18 发散；
3. 能力没有完全无损继承，MiMo 结果仍存在 IFBench 和 SWE 局部回退；
4. 完整配方需要多个领域 specialist 的 RL 训练、student rollout、teacher prefill 服务、整合训练和
   各能力 retained set，成本远高于一次 OPD 接口冒烟。

因此，“直接拿多个现成强模型蒸馏进自己的模型”不能被当成可靠捷径。普通 Codex/Claude
订阅会话不返回学生实际 token 前缀上的精确 top-k/full logprob，不能直接充当 faithful OPD
teacher；只返回文本时更接近 sequence distillation、SFT 或 teacher-as-judge。

### 5.3 八卡资源边界

P3 当前实测是 4 卡训练 + 4 卡 rollout，`wait_time_ratio=0.82`，整 step 1387 秒，权重同步
11.45 秒，仅约占 0.8%。见：

- `docs/agentic_RL/repo_harness_rh2_workstreams/preflight/preflight_report.md`

这说明当前瓶颈是 rollout，不是权重同步。把拓扑改成 4 train + 2 rollout + 2 teacher，即使
显存能放下，也会减少已经不足的 rollout 能力；把 30B teacher 放到单卡，只能证明权重驻留，
不能证明长上下文 teacher prefill、队列积压和训练吞吐可接受。

Codex 当前建议的验证顺序是：

1. 先对拍 exact-token/logprob、tokenizer、top-k 截断和数值稳定性；
2. 验证 teacher freshness、cache identity、重试与版本绑定；
3. 比较外部 SGLang teacher、Megatron 串行/切换 teacher 的吞吐；
4. 在 3B–8B 上做单 teacher、优先同源 teacher 的 proof/kill；
5. 跨源现成 teacher 作为明确风险对照，而不是默认主案；
6. 只有环境和多 harness 研究自然产生多个 specialist checkpoint，且小模型整合实验通过，才
   考虑完整 MOPD 作为最终 capstone。

这意味着 OPD 专项仍有价值，但“技术接口存在”“显存能放下”“有限 GPU-hour 内能完成受控
能力整合”必须分开判断。

## 6. 可信训练底座：fully-async、DIS 与训练治理

两份 Pro 都找到近期 fully-async 的真实正确性事故和修复。这些证据支持 RepoHarness 当前设计，
但不构成新的第四条最终研究方向。

当前权威方案已经是：

- version-aware fully async；
- faithful DIS；
- worker/proxy 身份与恢复边界；
- PromptGroupAssembler 和合格组队列；
- sample、reward、policy version、resume lineage 守恒；
- 首版只做 before/after eval。

见 `docs/agentic_RL/repo_harness_rh2_workstreams/00-project-status.md` 和
`docs/agentic_RL/repo_harness_rh2_workstreams/05-fully-async-execution-plan.md`。

上游材料能证明这些问题不是过度治理：

- slime 曾修复 completed prompt group 被多取后丢弃的问题；
- verifiers 增加 config hash、resume lineage 和显式 retry/replay 语义；
- prime-rl 在线 eval 需要处理 stable checkpoint、resume 后 trace 和 policy version handoff。

最终可以把这部分形成较强的 infra 贡献，但需要绑定正确性和模型结果，而不是只报告吞吐：

```text
sync / async same-sample parity
+ 固定权重 token logprob / MoE routing parity
+ crash/restart queue conservation
+ staleness envelope
+ wall-clock throughput
+ held-out 学习结果不发生不可解释分叉
```

TrajectoryProjection、中立 IR、EligibilityGate、评分隔离和版本化 inspector 同样是主研究线的
支撑资产，不应重新包装为完全新增的模型研究命题。

## 7. 新能力候选

### 7.1 Tool-fault recovery：优先做低成本探针

它与系统级 FA-5 故障注入不同：FA-5 检查训练系统事务是否正确，tool-fault 环境训练的是模型
看到工具失败后能否 retry、切换策略、检查副作用或 abstain。

适合注入的故障包括 timeout、partial response、schema drift、stale value、非原子副作用、重复
执行和错误成功回执。首要问题是模型权重是否学到了超越 runtime transaction protocol 的能力，
因此至少要区分 runtime-only、RL-only、runtime+RL。若权重训练不能超过强 runtime baseline，
它更适合作为 harness 能力和 held-out 评测轴，不应升级成模型主线。

### 7.2 Context/memory/compaction：保留为后续候选

该方向与 RepoHarness 的长程轨迹、history rewrite、compaction lineage 和 resume 语义高度贴合，
但当前复杂度更高：

- 首次 GRPO 已定案关闭 compaction；
- TRACE 不训练目标模型权重；
- Verifiable Memory 公开资产尚不完整；
- CompactionRL 报告过在无 compaction 条件下的能力回退；
- 真正训练需要 compaction event、snapshot/fork、summary provenance 和跨 segment credit。

当前更适合做 paired-boundary replay：冻结同一 pre-compaction 状态，比较 raw history、静态
summary、external store 和 learned/optimized summary 的续跑差异。只有发现稳定、可验证的 silent
corruption，并证明训练信号可以归因，才进入 RL。

### 7.3 过程奖励、VPR、SAO、PPO

[VPR](https://arxiv.org/abs/2605.10325) 证明结构化精确中间 oracle 可以帮助训练，也证明低质量
MCTS oracle 会伤害训练；其训练环境主要是可精确验证的游戏。开放 SWE 很难为每一步提供同等
可靠 oracle。因此过程信号应先用于少数可精确判断的状态，例如依赖恢复、工件产生、工具结果
消费、故障恢复和 compaction 后约束保持，不宜现在单独成为第四主线。

SAO、PPO、压缩 RL 等仍值得在专项中比较，但算法不应先于环境、harness 和评测契约决定项目
题目。算法收益需要在固定任务、harness、token budget、rollout 数和训练信号下比较。

### 7.4 多智能体 RL

当前公开证据不足以把它提升为近期方向。Prime Intellect 的
[General Agent](https://www.primeintellect.ai/blog/general-agent) 主要描述离线多智能体数据合成，
在线 multi-agent training 仍是未来工作。多智能体还会引入信用分配、通信协议、角色坍缩、
环境成本和评测归因问题，八卡资源下不宜只因为概念前沿就并入主线。

## 8. 用户提供的其他外部资源如何定位

### 8.1 Delta weight sync

[Hugging Face delta weight sync](https://huggingface.co/blog/delta-weight-sync) 对跨网络或高频权重
传输有工程价值，但论文/博客演示主要是小模型与解耦部署。当前 P3 权重同步只占 step 约 0.8%，
rollout 才是瓶颈，因此它不是当前主研究方向。若未来模型、节点数、更新频率或跨地域拓扑变化，
再重新评估。

### 8.2 Nemotron SWE 数据

当前能够核验的是官方
[Nemotron-SFT-SWE-v3](https://huggingface.co/datasets/nvidia/Nemotron-SFT-SWE-v3)，包含多种 agent
harness 生成的 SWE 轨迹，可作为 SFT、warm-start、数据 schema 和轨迹质量参考。用户最初给出的
`Nemotron-SFT-SWE-v3.5` 尚未核验到官方数据卡，不能在确认前作为事实引用。无论 v3 还是后续
版本，它们首先是数据来源或基线，不是独立研究方向。

## 9. 首轮实验与最终项目的关系

公开 SWE 数据 + GRPO + before/after 不是没有价值；它是验证完整链路和建立后续因果对照的
必要 baseline。问题只在于不能把它当作最终项目终点。

建议分层理解：

```text
首轮：单 harness、可信环境、GRPO、before/after
  → 证明 FA/S2/训练投影/模型更新链真实闭环

后续小模型研究：环境资格消融 + 多 harness 因果矩阵 + OPD feasibility
  → 选择真正有信号的机制

最终 30B-A3B：只确认最强组合
  → 形成模型能力结果、infra 正确性证据和能力保持评测
```

不建议把环境、多 harness、tool-fault、context、OPD 和多个 RL 算法全部在 30B 上做。P3 的
23 分钟/step 来自 n4 短题探针；正式 n8、长轨迹和过采样可能使 step 再增加 2–3 倍。多个专家、
多随机种子和多 factorial 很快会消耗数个 node-day。

## 10. 当前文档与设计冲突

在后续正式训练或重写实验矩阵前，需要显式处理以下漂移：

1. `00-project-status.md` 已定案 version-aware fully-async-first + faithful DIS，首版只做
   before/after；`repoharness_validation_experiment_design.md` 的部分段落仍写同步 `train_async`
   首训和训中 held-out 快评。
2. E10 的单 harness 同口径适合首轮内部有效性，但不能继续作为最终多 harness 研究的边界。
3. 实验设计仍引用 OpenAI 2026-02 对 SWE-Bench Pro 的推荐；OpenAI 已在 2026-07-08 的
   [后续审计](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)后撤回推荐。
   自建 frozen held-out 路线仍然有效。
4. 当前只有 216 道 bring-up 静态候选和 542 道 held-out 候选，不能表述成正式训练数据和
   评测集已经冻结通过。
5. 旧 `RL_algorithm_design.md` 的 dense、LoRA、vLLM 等前提与当前 30B-A3B、slime、fully-async
   路线不一致，只能作为历史材料。

这些问题不要求在本轮方向讨论中立即改文档，但在下一次训练设计收口时必须统一权威口径。

## 11. Codex 建议的后续研究组织

如果最终仍拆成三个专项，建议按以下边界理解，而不是预先承诺全部正式实施：

### 专项 A：环境资格、扩展与 verifier 可信度

- 现有环境四门和 S2 anti-cheat 是输入，不重复建设；
- 新增 solver-relative calibration、环境家族生成/变异、policy-relative 难度和 adversarial
  hardening；
- tool-fault 作为优先低成本探针；
- 先做本机/API 生产与小模型消融，再决定是否进入 30B。

### 专项 B：多 harness 语义契约与跨接口评测

- 审计 Codex、OpenCode、PI、DeepSeek、Prime Agent 的真实语义差异；
- 定义 canonical operation/event、raw token trace 与预算归一化；
- 设计最小 train-harness × eval-harness 矩阵和未见组合；
- 先证明不是 parser、prompt 信息量或工具能力差异造成的假提升。

### 专项 C：OPD/MOPD 接口与资源 proof/kill

- 对拍 exact token/logprob、teacher 版本、tokenizer 和 cache identity；
- 测量不同 teacher 放置方式在 rollout-bound 拓扑中的真实吞吐；
- 小模型单 teacher、同源优先，跨源作为负对照；
- 不把完整多专家 MOPD 作为当前已承诺路线。

Context/memory 可以先在专项 B 做 offline boundary replay，不必立刻拆出第四个大线程。SAO、PPO、
VPR 等算法可在任务和 harness 固定后单独比较。

## 12. 当前仍未确定的关键问题

本文没有替 owner 决定以下事项：

1. 最终项目是否以“跨 harness 稳健能力”作为唯一中心模型命题，还是把环境生产本身也作为
   同级研究结果；
2. 首批非 SWE 环境选择哪些家族，以及许可证、污染和重放边界；
3. 多 harness 采用真实白盒项目、合成语义变体，还是二者组合；
4. 小模型因果矩阵采用哪个模型规模、多少随机种子和多少任务；
5. OPD 是只做接口/负结果，还是预留一次正式小模型训练；
6. tool-fault 与 context/memory 是否有一个进入近期模型训练；
7. 最终 30B 训练只确认环境改进、多 harness，还是在资源允许时加入 OPD；
8. 第一轮 baseline 结束后，如何定义继续、停止和回退条件。

因此当前最稳妥的判断不是“方向已经定案”，而是：

> 环境和多 harness 得到了更强支持；环境需要升级为 learnability + verifier qualification；
> OPD 值得做单 teacher proof/kill，但完整 MOPD 降为条件式 capstone；tool-fault 和
> context/memory 先用低成本证据竞争一个后续能力槽位；fully-async 正确性继续作为不可跳过的
> 可信训练底座。
