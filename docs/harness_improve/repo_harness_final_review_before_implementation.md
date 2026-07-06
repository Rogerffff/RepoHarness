# RepoHarness 实施前最终检查：项目必要性、实现范围与简历亮点

本文是进入实施计划设计之前的最后一轮检查文档，回答四个问题：

1. slime 框架范围扩张之后，本项目是否还有必要性？
2. 全部外部参考资料（R0~R12 技术报告 + 参考代码库）核对之后，还有哪些设计或决策遗漏？
3. 本项目的最终实现范围是什么（范围内 / 范围外清单）？
4. 作为简历项目，当前设计还缺哪些能出彩的亮点？

本文与主设计文档 `repo_harness_design_doc2_verifiers_based.md` 的关系：主设计文档承载架构定案；本文承载"为什么这个范围是对的"的论证、参考资料最终核对台账和简历叙事建议。本文讨论定稿后，其中需要固化的结论会回写主设计文档，然后进入实施计划设计。

---

## 1. slime 范围重评与项目必要性判断

### 1.1 事实层：slime `e848052a` 现在有什么

`slime/agent/` 新增了一个完整的 agentic rollout substrate（全部经源码确认，非转述）：

```text
slime/agent/harness/
  claude_code.py / codex.py / common.py
  黑盒 CLI 生命周期：装 CLI（npm tarball 上传）、写配置、detached 启动、
  轮询完成标记。Claude Code 以 --permission-mode bypassPermissions 运行。

slime/agent/adapters/
  anthropic.py / openai.py / common.py
  模型边界捕获：CLI 以为自己在调 Anthropic/OpenAI API，adapter 逐轮
  tokenize 消息历史、记录 prompt/output token 快照（TurnRecord，绑
  sglang /generate）、模型生成 token loss_mask=1、模板/observation
  token mask=0。

slime/agent/sandbox.py
  最小 Sandbox Protocol（exec / read_file / write_file / async context）
  + E2B 后端。每样本 fresh sandbox。

slime/agent/trajectory.py
  TrajectoryManager：per-session 消息树。prompt 前缀分叉自动处理
  sub-agent 派发与 auto-compaction（各自成为 root-to-leaf 链）；
  容忍 TITO 重分词漂移（fork/replace）；叶链线性化为 loss-masked Sample。

examples/coding_agent_rl/
  generate.py（custom_generate 全流程）+ swe.py（SWE 任务层：
  prepare_workspace / git_diff / evaluate）+ 8 节点 Qwen3.6-35B-A3B
  SWE RL 启动脚本。swe.py 的 evaluate 在 fresh 第二沙箱评分，
  README 自述 "no test-cheating"。
```

必须诚实承认的结论：**"把 Claude Code 跑在沙箱里、产出 token 保真训练样本、外加干净评分"这条中段链路，工业界已有第一方实现。** 如果本项目的简历故事是"我搭了 rollout 捕获机器"，这个故事已经失效——slime（后端侧）和 verifiers（环境侧）双双把它商品化了。

### 1.2 覆盖矩阵：slime / verifiers / RepoHarness 差异化层

| 能力维度 | slime agent substrate | verifiers v1 | RepoHarness 自建层（设计文档 2 第 5 章） |
| --- | --- | --- | --- |
| 黑盒 harness 捕获 + token 保真轨迹 | ✅ 第一方（slime-native） | ✅ 第一方（interception + Trace 图） | ❌ 不再自建（明确排除，风险 7） |
| 沙箱执行 | ✅ 最小契约 + E2B | ✅ Runtime 契约（docker/prime/modal） | 只做安全加固子类（5.1） |
| 干净评分 | ⚠️ 示例级（fresh 沙箱跑 eval_cmd） | ❌（harbor 是反例：同容器评分） | ✅ 系统级：patch replay 语义、hidden asset 挂载策略、test reset、失败归因三分、P1-P10（5.2） |
| anti-cheat 纵深 | ❌（沙箱必须开网回连 adapter；无 git 清洗） | ❌ | ✅ git 历史清洗 + 网络策略 + monkeypatch 检测（5.3） |
| 任务/环境所有权与生产线 | ❌（预构建 JSONL + 预构建镜像，生产在范围外） | ⚠️ 对象模型有、生产线无 | ✅ 环境包版本化 + empty/golden/determinism 验证 + 任务质量门槛（5.4） |
| 训练资格治理 / artifact 可见性 | ❌（mask 正确性是代码行为，非可审计契约） | ⚠️ token identity fork 有、分级/投影无 | ✅ EligibilityReport sidecar + 统一 gate + fail-closed inspector（5.6） |
| 多后端解耦 / 评测复用 | ❌（全 slime-native） | ✅ EnvServer/EnvClient + EvalClient | ✅ verl / slime / 离线导出三 adapter（5.7） |
| 白盒 harness / 权限 / 用户模拟 | ❌（bypassPermissions） | ⚠️ user hook 有、权限无 | ✅ 后期增量（5.5） |

结论一目了然：**第一行的商品化不影响后六行的稀缺性，而后六行恰好就是设计文档 2 划定的自建层。** slime 的扩张反而是净利好——首个在线训练跑通的工程风险大幅下降（官方示例证明端到端可行，可作对照基线），本项目可以把全部精力压在治理与环境层。

### 1.3 简历叙事的重新校准

原叙事（已失效一半）：

> 我搭建了完整的 RL 基础设施 + 白盒 harness，并在上面训练了一个 coding agent。

问题：面试官会问"这和 slime 的 examples/coding_agent_rl 有什么区别？"——如果答案是"我自己也实现了一遍捕获和评分"，这是减分项（重复造轮子）。

校准后的叙事：

> 我构建了工业训练后端（slime/verl）普遍缺失的**环境与训练治理基础设施**：
> 环境生产线（带 empty/golden patch 验证与确定性门槛）、评分隔离与反作弊、
> 可审计的训练资格治理（fail-closed），并以 verifiers 风格的可组合环境模型
> 做到训练后端解耦（同一环境包供 slime 在线训练、离线 SFT 导出、评测三方消费）。
> 最后在这套设施上完成了一次真实 coding agent RL 训练，用 before/after
> 评测和治理层拦截记录证明设施有效。

这个叙事的每一个名词都对应 slime 没有的东西，且都有一线技术报告（MAI / Nemotron / Polar）背书其必要性。"我知道什么不该自己造"（训练内核、推理服务、黑盒捕获都不造）本身就是架构判断力的展示。

**必要性判断：项目继续推进，价值主张按上述矩阵聚焦。**

---

## 2. 参考资料最终核对结果

R0（Polar）、R1（MAI-Thinking-1）、R2（Nemotron-3 Ultra）已在前几轮完整吸收（`2_techreport_advice.md`、重定位文档 §16、审核报告），本轮不重复。R3~R12 十份报告由三个并行核对线程逐份对照设计文档 2 检查（每条发现均有页码/章节证据），以下为定稿台账。

### 2.0 总体结论

**无推翻性发现。** verifiers 基座、双拓扑、interception 路线、治理层定位全部得到工业实践正面佐证：MiniMax Forge 的白盒/黑盒双形态经统一 Gateway 抽象（"validated across hundreds of distinct agent scaffolds"）、ROCK ModelProxyService 的训练/部署上下文一致性论证、GLM-5 的 server-based HTTP rollout，分别印证了本项目的双形态治理层、interception 决策和 slime 形态 B。需要处理的是：**4 条矛盾/假设修正（2.1）、24 条按章节归组的增量缺口（2.2）、若干无增量确认（2.3）**。

### 2.1 矛盾与假设修正（实施前必须处理）

| # | 内容 | 出处 | 对设计文档 2 的影响与处置 |
| --- | --- | --- | --- |
| **M1** | **MoE routing replay 是 MoE RL 稳定性必需，不是"未来可选"** | DeepSeek-V3.2 §3.1 Keep Routing（自 V3-0324 起采用，称 "crucial"；另有 Keep Sampling Mask 重放 top-p/top-k 截断掩码）；GLM-5 §3.3（非确定 top-k 几步内训练崩溃）；Composer 2 §6.2（router replay + gating 可信度阈值过滤） | 设计文档 2 §9 风险 5 把 routing replay 列为"未来渐进接入、不阻塞第一版"——但训练目标恰是 GLM 系 MoE + slime，该假设不成立。**处置：S0 新增验证项 V4（slime 是否透传 per-token routing 快照与 sampling mask）；若首训模型为 MoE，routing replay 升级为 S1/S2 必备前提** |
| **M2** | **评分应是独立弹性故障域；与 rollout 同驻是资源争抢的根因** | RollArt §3.2/§6.1/Fig12（reward worker stateless + bursty，专用 GPU 利用率仅 7.4%；serverless 化后 6%→88%，单步 rollout 158s→77s） | §5.2 P7 把 SWEGradingManager 定为 per-worker 同驻单例，P2 把并发翻倍当必然代价。**处置：GradingManager 接口改为 backend-neutral 评分服务接口——第一版实现仍 per-worker（S1/S2 规模下够用），但接口按"可替换为独立弹性池 / serverless 后端"设计；P2/P7 相应改写** |
| **M3** | **长尾主成本大概率是容器冷启动 / env.reset，不是 test run** | RollArt §3.1 Fig3 / §8（env.reset 占失败迭代 78% 时间；环境失败约每 10 次迭代一次；多层镜像缓存后 reset 成功率 >99.99%、99.99% 初始化 <1 分钟） | §9 风险 6 的论证方向正确（prewarm 藏不掉 test run）但成本优先级需实测校正。**处置：埋点清单补 `env_reset_seconds` / `image_pull_seconds`（rollout 侧与评分侧都记）；P10 升级——多节点规模需 registry mirror + 分布式镜像缓存层，pre-pull 只是第一档** |
| **M4** | **协议 shim "无损透传"是必要非充分：引擎级 logprob 失配仍然存在** | ROME（R10 §3.2.4）：权重完全相同时 SGLang 推理分布与 Megatron 训练分布仍系统性不同（后端实现/量化/batching），需 token 级 TIS 掩码 | §5.7/S0 的 shim 验证只覆盖"透传正确"。**处置：§5.7 补一条——rollout logprob 必须标注 `logprob_source`（引擎/版本/精度）；训推失配的 IS/TIS 校正归训练后端（H10），RepoHarness 只负责记录 serving 事实** |

### 2.2 新缺口台账（按设计文档 2 章节归组，处置：回写时逐条吸收）

**→ §5.1 安全 Runtime（4 条）**

1. **网络机制定案候选**：Anygress 式透明出网代理——pod 启动注入受信任 root CA、TCP 层透明重定向、丢弃敏感 header、细粒度请求策略，且不依赖 proxy 环境变量（防 agent 察觉/绕过）【Composer 2 §6.2, p11】；对照 ROCK Rocklet 的 per-sandbox egress policy【R10 §2.3】。解决 5.1 悬置的"缓存代理 vs 预装镜像"：两者都要——依赖预装为主、白名单透明代理为辅。
2. **沙箱安全分档**：DSec 四执行基座（Function Call 预热池 / Container / microVM Firecracker / fullVM）+ 统一 SDK、切换只改一个参数；EROFS 分层 + 只读基座 + 本地 CoW 写层 + 毫秒级链式快照【DeepSeek-V4 §5.2.5, p35-36】。5.1 开放选项 (a/b/c) 的工业答案：**接口统一 + 按任务安全等级选档**，且 CoW 快照正是 P6 prepared clean checkout 的实现形态。
3. **沙箱轨迹日志**：per-sandbox 全局有序命令日志 → 抢占恢复 fast-forward（缓存结果重放，防非幂等命令重复执行）+ 细粒度 provenance + 确定性重放【DeepSeek-V4 §5.2.5, p36】。治理层审计底座的现成实现形态，直接支撑 H7 与 5.6 审计。
4. **环境 fork/snapshot**（文件 + 内存级）用于 mid-trajectory checkpoint 与 post-rollout state capture；group 级恢复用 policy-version 标注的 advantage 序列落 NFS【Composer 2 §6.2, p10-11】。佐证 P6；"rollout 级 checkpoint 恢复"记入 S5 待评估。

**→ §5.2 评分与 GradingManager（P 清单修订，3 条）**

5. **新增 P11 评分队列反压**：评分吞吐 < rollout 完成速率时队列无界增长。参照 RollArt SampleBuffer 的 O(α·E) 有界容量 + eager evict【RollArt §6.2, p11】：评分队列必须有界，积压超阈值时按策略处理（阻塞新 rollout 准入 / defer 评分 / 降级 audit_only），反压事件写入 EligibilityReport。
6. **P1 扩充为故障域隔离**：评分沙箱崩溃不得连带失败 rollout（反之亦然）；崩溃的评分 evict-and-reschedule 到健康节点重评，trace 不丢【RollArt §8：env/reward/inference/training 四故障域隔离，3000 GPU 一周仅 1 次失败】。
7. **P4 扩充为完整闭环**：降级之外必须有"组修复"动作——GLM-5 规则（组内有效样本 > 半组则用有效样本 pad，否则整组丢弃）【GLM-5 §4.1.2, p17】+ ROME on-the-fly resampling（同初始态即时重采样）【R10 §3.2.4, p21】+ RollArt 冗余 rollout（组内过采样、收够即杀在途，1.62× 加速）【RollArt §7.4, p14】。且 **infra_failure 降级信号必须在 group 组装前对训练后端可见**（组尺寸维护归后端 H10，但依赖 gate 的及时信号）——写入 5.7 adapter 握手契约。

**→ §5.3 anti-cheat（2 条）**

8. **第四类作弊：谎报成功检测（deceptive-success detection）**——agent 声称完成/合规但实际未执行或伪造通过输出。K2 在确定性验证 + LLM judge 之外专设 hack-check 层【Kimi K2 §3.2.1, p11-12】。当前三类（搜答案/git 历史/篡改测试）之外的新增维度，写入 AntiCheatSpec。
9. **泄漏面补充**：会触发 bug 的测试文件必须从 agent 可见上下文排除（防捷径泄漏）【Qwen3-Coder-Next §2.1, p2】。

**→ §5.4 环境生产线（7 条，增量最集中）**

10. **gold patch 判据精化**：`F2P > 0 且 P2F = 0`（修复有效且不引入回归）作为 EnvironmentValidationReport 显式字段，补齐 empty/golden 之外的第三门槛【DeepSeek-V3.2 §3.2.3, p11】。
11. **假阳性解检测 + 测试覆盖门槛**：golden patch 能过 ≠ 测试套够强——需用已知错误 patch 验证测试能拒（false_positive_solution_check）；测试覆盖率摘要入报告；欠规约任务会被捷径通过，**任务质量本身就是生产期反作弊**【Terminal-Bench-Pro，R10 §3.3.2, p27-28】。
12. **难度校准与实例筛选**：多强基线模型 pass-rate 估难度、只留中等难度（ROME 60K→2K）；spec-test 错配过滤；外部网络敏感任务过滤；query evolution 剥离 hint 防过拟合描述风格【R10 §3.2.3, p19；MiniMax-M2 §4.1.3, p11】。
13. **非功能 verifier 检测**：自动检测并过滤"形同虚设、不真正验证"的测试【Qwen3-Coder-Next §2.1, p2】。
14. **多语言日志解析**：LLM 生成 per-repo 语言感知日志解析函数抽取 F2P/P2P（GLM-5 RepoLaunch：10k+ 环境、数千仓库、9 语言）【GLM-5 §4.2.1, p17-18】。规模化真实 PR 的核心工程环节。
15. **任务类型分化 reward 与任务增广**：按 PR 类型路由 reward（bug-fix→F2P/P2P、feature→新增 test points、perf→前后 P2P）；SWE-Test 反转（把 bug-fix 反转成写测试任务）、bug injection、commit merging；compiled-lang 由 agent 迭代自建环境【MiniMax-M2 §4.1.1 图 3, p7-9】。
16. **合成任务子流水线**："难解易验"原则、verifier 函数与任务共生成、solution 强制仅经工具可解、pass@100 可解性过滤【DeepSeek-V3.2 §3.2.3, p11】；任务级显式 rubric 字段（成功判据 + 期望工具模式 + 检查点）【Kimi K2 §3.1.1, p10】。

**→ §5.5 白盒 harness 与工具面（3 条）**

17. **harness 对部署目标保真是一等设计目标**：Composer 用生产 backend 的影子部署做训练与数据准备（"remain faithful to the harness that Composer 2 will be deployed into"），训练/生产工具面差异是显式可控维度【Composer 2 §6.2, p11】；Qwen3 佐证跨 scaffold 轨迹迁移很弱【R3 图 3】。这是旧问题"训成评测 DSL 专家"的根治思路。
18. **tool-call 格式多样性是训练鲁棒性杠杆**：模板数 2→8 使 SWE-Bench Verified 约 48→54【Qwen3-Coder-Next §4.2.2 图 5, p7-9】。verifiers 三 dialect 不只是捕获协议，也是训练多样性维度。
19. **prompt distillation**：采样时给完整富专家 system prompt，训练时选择性丢弃，迫使模型内化最佳实践【MiniMax-M2 §4.1.2, p10】。5.5 与离线导出的候选机制。另：白盒 agent 把 context management 操作注册给框架供训练期重建【MiniMax-M2 Forge §6.2.2, p20】，与 verifiers token identity fork 互补。

**→ §5.6 / §5.7 治理与 adapter（5 条）**

20. **数据有效性不变量**：抢占/故障恢复必须从持久化 token 续解，**不得从头重生**——从头重生在数学上引入长度偏置（短回复更易在中断中"存活"）【DeepSeek-V4 §5.2.3, p34】。写入 5.6 或 §9 风险清单。
21. **prefix-tree merging**：同组共享前缀合并成树 forward，数学等价独立样本（零近似误差）、最高 40× 训练加速 + 显存下降【MiniMax-M2 §6.2.5, p22-23】。adapter 应把 Trace.branches 的共享前缀结构透传给后端利用，而不是展平成独立样本。
22. **slime 接入细化**：形态 B 的官方形态就是 server-based HTTP rollout（外部框架直调 router 端点，后端优化不变）；S5 服务化要点补 PD 分离（长 prefill 抢占 decode 恶化尾延迟）+ heartbeat 容错下线；GLM-5 orchestrator 的统一 message-list 中立表示 + per-task 采样比治理是多任务服务化的参考形态【GLM-5 §3.6, p14；§4.1.1, p16】。
23. **环境崩溃样本处置的模型版本记录**：GLM-5 每样本记录 rollout 用过的权重版本序列 (w0…wk)，过旧即丢【GLM-5 §4.1.2, p17】——与既有 staleness 握手字段一致，佐证不新增。
24. **多 agent eligibility 远期规则**：PARL——子 agent 冻结、其轨迹排除出优化目标，只训 orchestrator【Kimi K2.5, p1-2】。H4 loss mask 语义在多 agent 场景的自然延伸，记入 5.6 远期扩展（当前不实现）。

### 2.3 无增量确认（诚实排除）

- **R8 MiniMax-M1：无增量**。SWE RL 部分被同公司更新的 M2 完整取代；CISPO / lightning attention / FP32 LM-head 属训练框架与模型架构层（H10 范围外）。仅一点留档：FP32 LM-head 使训推 token 概率相关系数 0.987→0.997，可作 H3 logprob 对齐验收的实证参照。
- **R12 ROLL framework**：被本地分析文档 + R11/R10 更具体的内容覆盖，跳过。
- **K2.5 多模态 / Agent Swarm 实现、K2 tool-simulator world model**（与真实执行路线正交，模拟保真度不足以承载 SWE 训练信号）：不采纳。
- **RollArt 的 Mooncake 权重同步、PD 拆分、hardware-affinity 调度、TIS/TOPR 公式；M2 的 CISPO、reward-to-go**：全部归训练后端（H10），对自建层无增量。
- **ROCK ModelProxyService**：架构上已被 verifiers interception 覆盖；仅其"训练/部署上下文一致性"论证作为 interception 决策的动机背书记入。

---

## 3. 最终实现范围定案（草案，待本文讨论后回写主设计文档）

### 3.1 范围内（按优先级）

```text
P0（S0~S1，闭环骨架）
  1. verifiers 基座集成：pin commit + 依赖行为契约测试套件
     （token identity fork 行为、Rollout 生命周期顺序、EnvServer wire 格式）
  2. 第一个 SWE taskset（SWE-bench Verified 子集起步，借 harbor 模板改隔离评分；
     规模按 D2 定案：S0 用 5~10 个 smoke task，S1 冻结 20~50 个子集任务）
  3. SWEGradingManager 最小版（同生命周期评分 + P1-P11 对照；
     接口按 §2.1-M2 定为 backend-neutral 评分服务接口，第一版 per-worker 实现）
  4. EligibilityReport sidecar + TrainingEligibilityGate + 投影扫描
  5. 离线导出 adapter（最早端到端闭环）
  6. 计时埋点（agent / grading_prep / grading_test + env_reset / image_pull，
     见 §2.1-M3）+ 失败归因三分

P1（S2~S3，训练信号可信）
  7. SWE-SEE 安全 Runtime（断网 / 非 root / seccomp / 资源限制；
     网络机制按 §2.2-1 定为"依赖预装为主 + 白名单透明代理为辅"）
  8. anti-cheat：git 历史清洗（物化期）+ 网络拦截策略（运行期，
     在线拦截语义按 §6.2 定为 block + dummy 观测 + 继续 rollout）+
     test reset（评分期）+ 谎报成功检测最小版（规则式 claim-evidence
     核对，D7 定案，见 §5.1）
  9. 环境生产线最小版：empty/golden patch 验证 + F2P>0 ∧ P2F=0 判据（§2.2-10）
     + 假阳性解检测（已知错误 patch 必须被测试拒绝，§2.2-11）
     + 确定性检查 + 环境包 digest 冻结
  10. 首个在线后端 adapter（slime，形态 A/B 由 S0 定，MoE 显著倾向形态 B，
      见 §5.1-D3）+ 协议 shim（若走 A）+ logprob_source 标注（§2.1-M4）；
      训练目标为 MoE（D3 已定），routing replay / top-p mask 透传为必备前提
  11. 红队环境包 / 作弊注入演示（4.1，D4 定案纳入 P1）
  12. 轻量命令事件日志 + provenance（D6 定案；同时是 §5.1-D7
      claim-evidence 核对和 §6.2 在线 Anti-Hack 的证据底座）

P2（S4~S5，差异化深化）
  13. 白盒 harness：结构化工具 + 权限拦截 + 确定性用户模拟最小版
  14. 训练前后 before/after 评测叙事（同一 Environment + EvalClient）
  15. 第二在线后端（verl）；EnvServer 服务化（如吞吐需要，
      服务化要点含 heartbeat 容错下线 + 多任务采样比治理，§2.2-22）
  16. 完整沙箱确定性重放（D6 后半：在 P1 事件日志之上补 fast-forward
      与全量重放，等基本链路稳定后做）
```

生产线 backlog（范围内方向、不进第一版，按良率与吞吐实测数据拉取）：

```text
B1 任务类型分化 reward / SWE-Test 反转 / bug injection 等任务增广（§2.2-15）
B2 合成任务子流水线 + pass@100 可解性过滤 + 任务级 rubric（§2.2-16）
B3 多语言日志解析 RepoLaunch 式流水线（§2.2-14）
B4 prompt distillation / tool-call 格式多样性训练（§2.2-18/19）
B5 rollout 级 checkpoint 恢复、prefix-tree 树 forward 结构透传（§2.2-4/21）
B6 独立弹性评分池 / serverless 评分后端（兑现 M2 的接口预留）
B7 难度校准（多模型 pass-rate）+ query evolution（§2.2-12）
```

### 3.2 范围外（明确排除，写给未来的自己）

```text
1. 训练内核 / 权重同步 / advantage / loss（归 slime/verl，H10）
2. 推理服务内核 / KV cache / MTP / 低精度（归 vLLM/SGLang，infra_mapping 结论）
3. 第三套黑盒捕获（verifiers interception + slime adapter 已覆盖，风险 7）
4. 大规模环境生产（MAI 的 102M PR 级别；本项目做"同样质量门槛的小规模版"）
5. LLM-in-the-loop 用户模拟（GRPO 噪声，确定性优先；重定位文档已定）
6. 多模态 / Agent Swarm / PARL（backend_tensors 与 Trace 分支结构留了扩展位，
   不做实现）
7. ROCK 级分布式 sandbox service（长期风险项，不进当前范围）
8. 自动 curriculum / 难度调度（重定位 §16.6：第一版静态 registry）
```

---

## 4. 简历亮点机会：当前设计尚未覆盖或未强调的部分

以下各条按"面试演示价值"排序，标注是否需要改设计。

### 4.1 「作弊注入演示」——把 fail-closed 治理做成可演示的招牌（需要小幅加设计）

当前设计有完整的 gate 与 inspector，但没有把它做成**可复现演示**的计划。建议在环境生产线里加一组"红队环境包"：故意构造 5 类污染样本，展示治理层逐条拦截——

```text
1. test tampering（agent 改测试骗过评分）→ test reset + AntiTamper 拦截
2. git 历史泄漏（solution commit 可从 reflog 恢复）→ git sanitizer 拦截
3. hidden test 泄漏进 rollout workspace → 投影扫描 fail closed
4. token 漂移样本（重分词后混入训练）→ token identity fork 降级
5. staleness 超限样本 → gate 拒绝进 batch
```

这是别的开源项目没有的东西：**用注入实验证明训练数据治理有效**，一页演示胜过千行代码。成本低（每类一个 fixture 任务），与 16G 系列的 inspector 文化一脉相承。

### 4.2 「双消费者 parity 证明」——trainer-decoupled 不是口号（需要加验收项）

同一个环境包 + 同一批 rollout，分别经离线导出 adapter 和 slime adapter 消费，
证明两边的 token ids / loss mask / reward 事实逐位一致（parity 测试）。这是
"多后端解耦"最有力的证据，实现成本主要在 S1 已有组件上加一个对照脚本。
建议写进 S1 的完成标准。

### 4.3 「环境包 benchmark card」——像 model card 一样发布环境（已有雏形，建议提级）

重定位文档的 `EnvironmentPackageSpec` 有 benchmark_card_ref 字段，但没人把它
当作产出物。建议：每个冻结环境包自动生成一页卡片（任务来源、验证结果、
reward 画像、anti-cheat 报告摘要、digest）。对外展示时，这是"环境即产品"
理念最直观的载体。

### 4.4 「量化故事」——埋点体系升级为项目指标页（不需要改设计，需要提前规划口径）

设计里已有三类计时埋点与失败归因，建议提前定义简历口径：

```text
环境生产良率（候选任务 → 通过验证的环境包，对照 MAI 的 5.5%）
治理拦截统计（gate 各维度拒绝原因分布）
rollout 吞吐与评分开销占比（prep/test/agent 三段）
训练 before/after 的 SWE-bench 子集分数变化
```

这些数字从 S1 第一天就要开始积累，不能事后补。

### 4.5 「训练有效性实验叙事」——设计文档缺一个实验章节（需要补设计）

当前设计文档 2 全部是基础设施，没有回答"用什么实验证明设施有效"。建议
补一节实验设计（或单独实验文档）：模型选型（renderer 支持决定）、任务集
规模、rollout 预算、评测协议（同一 Environment + EvalClient before/after）、
预期结论形态。这是简历故事的收尾，不能等训练跑起来再想。

### 4.6 本轮 R3~R12 核对新增的亮点候选

```text
1. 「train-test mismatch 系统性消除」故事线升级：部署保真 harness
   （Composer 影子部署实践）+ tool-call 格式多样性（Qwen3 实测 48→54）
   + 训练/部署同一 interception（ROCK 佐证），与 4.2 的 parity 证明
   合并成一条完整叙事——这是当前面试最高频的 agent RL 考点。
2. 「假阳性解检测」进环境验证门（§2.2-11）：已知错误 patch 必须被测试
   拒绝——比 empty/golden 更进一步，直接回应"你的测试套够强吗"的追问。
3. 「评分故障域工程」（§2.2-5/6/7）：有界评分队列反压 + evict-and-reschedule
   + GRPO 组修复信号（pad/drop + 重采样），每条都有工业出处
   （RollArt / GLM-5 / ROME），是治理层工程深度的证明。
4. 「沙箱确定性重放」（§2.2-3，DSec 式命令日志 → provenance + 重放）：
   若做，是治理层审计的招牌能力；实现成本偏高，是否纳入见 D7。
```

---

## 5. 遗留决策清单

```text
S0 验证项（做了才知道，非设计缺口）：
  V1 prime-sandboxes / prime-tunnel 在部署环境可用性（决定方案 A/B）
  V2 训练目标模型的 renderer 覆盖（决定 token 保真上限）
  V3 vLLM 协议 shim 无损透传验证（决定首个在线后端与形态 A/B）
  V4 slime 是否透传 per-token MoE routing 快照与 sampling mask
     （§2.1-M1；若训练目标为 MoE 模型，这是硬前提而非可选项）
  V5 SGLang / Megatron 对 RTX Pro 6000（Blackwell 工作站卡，8×96GB，
     PCIe 互联）的支持：attention kernel、FP8 KV、EP all-to-all
     over PCIe 实际带宽（C1 定案后新增，详见实验设计文档 §1-C1）

待讨论决策（本文第 3/4 章定稿时一并定）：
  D1 新包命名与仓库形态（当前 repo 内新包 vs 新 repo）
  D2 第一批任务源规模（SWE-bench Verified 子集大小）
  D3 训练目标模型（影响 V2/V3/V4 与算力预算；选 MoE 则 M1 生效）
  D4 红队环境包（4.1）是否纳入 P1
  D5 实验章节（4.5）写进主设计文档还是独立文档
  D6 沙箱轨迹日志 / 确定性重放（§2.2-3）是否纳入 P1
     （审计招牌能力 vs 实现成本，也可降级为 P2/backlog）
  D7 谎报成功检测（§2.2-8）第一版形态：规则启发式还是 LLM monitor
     （与 5.3 既有"monkeypatch 检测用规则还是 LLM"开放选项合并决策）
```

### 5.1 定案记录（2026-07-06 讨论）

**D1 已定**：留在当前仓库，开清晰边界的新模块，不新建仓库。旧 `src/repo_harness` 冻结为 legacy/reference，不再沿旧 Stage 16G 继续堆。

**D2 已定**：S0 用 5~10 个 smoke task；S1 冻结 20~50 个 SWE-bench Verified 子集任务；基础设施稳定后正式训练再扩展。已同步进 §3.1 P0-2。

**D3 已定：训练目标选 MoE 模型，RepoHarness 必须支持 MoE**。slime 原生路径的覆盖已逐项源码核实：`Sample.rollout_routed_experts`（从 SGLang meta_info 解码，`utils/types.py:126,352`）、`rollout_log_probs`（`types.py:121`）、top-p mask 重放（`megatron_utils/loss.py:35-47` 的 `rollout_top_p_token_ids/offsets`）、训推失配校正（`examples/train_infer_mismatch_helper`）。**因此 V4 的残余问题收窄为：routing / top-p tape 能否穿过所选接入形态**——形态 B（slime custom_generate 直调）天然成立；形态 A（verifiers TrainClient + vLLM 协议 shim）需要 shim 和 Trace 全程携带这些张量，而 vLLM `/inference/v1/generate` wire 协议没有 top-p ids 槽位。**派生结论：MoE 训练显著加分形态 B，S0 评估两形态时按此加权**。

**D4 已定**：红队环境包（4.1 作弊注入演示）纳入 P1。已同步进 §3.1 P1-11。

**D5 已定**：实验设计独立成文，不并入主设计文档；时机见 §6.3。

**D6 已定**：P1 做轻量命令事件日志 + provenance；完整确定性重放（fast-forward、全量重放）放 P2，等基本链路稳定后做。已同步进 §3.1 P1-12 / P2-16。

**D7 已定：谎报成功检测不进入 reward 主通道，只做事实产出方**。定案要点：

```text
1. 不替代最终 patch reward。最终 reward 唯一来源仍是
   clean grading checkout + verifier（H5 不动摇）。
2. 检测产出物是 AntiCheatFinding / TrajectoryQualityFinding，消费面为：
   SFT / warm-start 过滤（谎报轨迹即使测试碰巧通过，也是坏模仿数据）、
   process reward 分量（经 reward_components，遵守 §16.11 process-level 规则）、
   LLM-judge 型 reward 分量的防骗前置（若未来引入 user burden 等 judge 评分）、
   审计与红队演示（与 D4 联动）。
3. 第一版用规则式 evidence-backed claim checking：agent 的成功声明
   （如"测试已通过"）必须能在 P1-12 的命令事件日志里找到对应证据事件
   （真实执行过测试且 exit 0），找不到即记 finding。LLM judge 视情况后置。
4. 背景澄清：K2 的 hack-check 主要保护"LLM judge 作为 verifier"的
   reward 通道；本项目的可执行 hidden test + clean grading 已在结构上
   保护了 reward 通道，所以该机制在本项目的价值恰好就是上面第 2 条
   列的四个消费面，而不是 reward 主通道本身。
```

---

## 6. GLM-5.2 blog 增补：算法无关接口、在线 Anti-Hack、实验设计时机（2026-07-06 定案）

GLM-5.2 blog 的 Agentic RL 节选（`external_paper_references/pdfs/glm5.2_blog_RL.md`）带来两条对本设计有直接影响的事实，连同"实验设计何时定"一并在此定案。

### 6.1 训练接口必须算法无关：GRPO 组语义降为可选（定案）

GLM-5.2 在长程任务上**放弃了 group-wise 优化，改用 critic-based PPO 从单条 rollout 学习**——原因是 compaction 把超长轨迹切成数量不定、长度悬殊的 sub-trace，同一 prompt 下不同 rollout 产生的可训练 trace 数不同，组内比较的前提（同题样本可比）被破坏。对本设计的影响：

```text
1. RepoHarness 不得假设"一个 prompt 固定 n 条 rollout + 组内比较"。
   verifiers 的 run_rollout（单条）与 run_group（n 条）本来就并存，
   保持两者都是一等路径；num_samples=1 的 PPO 形态必须可用。
2. 组语义相关机制全部条件化：§2.2-7 的 GRPO 组修复（pad/drop）、
   RollArt 冗余 rollout、group_id 握手字段——只在后端声明组式算法时激活。
   EligibilityGate 的降级信号对两类算法都要及时暴露（PPO 下是单样本
   剔除，GRPO 下是组修复）。
3. 天然契合点：GLM-5.2 "把所有 compaction sub-trace 都作为可训练轨迹"
   正是 verifiers Trace 图的 branch 语义（compaction 分叉 → 多个
   root-to-leaf branch，每个 branch 一条训练样本）。本设计无需为此改动，
   记为基座决策的又一佐证。
4. PPO vs GRPO 的选择本身归实验设计（§6.3）与训练后端（H10），
   RepoHarness 只保证两者可接。
```

### 6.2 Anti-Hack 从"事后判无效"升级为"在线拦截 + 继续 rollout"（定案）

GLM-5.2 的 anti-hack 模块：**两段检测**（规则过滤保 recall → LLM judge 查意图保 precision），**在线逐步监控 tool call**；检出即**阻断该调用、返回 dummy 信息、rollout 继续**——理由是"处理具体的无效行为而不是整条轨迹拒绝，避免 rollout 被突然掐断导致的训练不稳定与模型崩溃"。定案吸收方式：

```text
1. 防线次序（纵深，从强到弱）：
   ① 结构隔离优先：hidden verifier 资产根本不挂载进 rollout workspace
     （H5）。GLM-5.2 的 hack 例子（cat /workspace/.eval/secret_cases.json）
     在本设计中被结构性消灭，这是比检测更强的防线——保持不动摇。
   ② 在线拦截：对结构上无法消除的通道（网络出口、git 历史残留、
     可疑命令模式），运行期 CommandFilter 检出即 block + 返回脱敏
     dummy 观测 + rollout 继续，不中断轨迹。
   ③ 事后检测：评分期 test reset / monkeypatch 检测 / 谎报成功核对。
2. attempted vs executed 必须区分并影响资格：
   被拦截的尝试（attempted）→ 记 AntiCheatFinding + 可选 process penalty，
     轨迹仍可训练（agent 学会"这条路不通"正是想要的信号；
     这也是 GLM-5.2 online guard 的训练稳定性论据）；
   实际发生的泄漏（executed，如拦截失败、泄漏内容已进入模型上下文）→
     EligibilityGate 降级（污染样本），fail closed。
3. 两段检测的落位：规则层在线同步（拦截必须实时）；LLM judge 意图复核
   可以异步后置，结果回写 finding 的 precision 字段，不阻塞 rollout。
4. 证据底座复用：拦截事件写入 P1-12 命令事件日志，与 D7 claim checking、
   D4 红队环境包共用同一套 finding 契约。
```

### 6.3 实验设计时机（定案）

**不阻塞 S0 启动，但 S1 任务冻结前必须完成实验设计初稿**（独立文档，D5）。理由：S0 的验证项本身依赖实验决策（V2 renderer 覆盖、V4 routing 透传都取决于具体模型型号），反过来 S0 的验证结果又约束实验设计（形态 A/B、算力形态），二者天然并行。实验设计文档最少要定：

```text
1. 训练目标模型具体型号（MoE 已定，型号待定——牵动 V2/V4 与算力预算）
2. 算法族与后端配置（PPO with critic vs GRPO；slime 侧配置形态）
3. 数据划分：训练任务集（S1 的 20~50 题起步）、held-out 评测集、
   两者不重叠的冻结协议
4. 评测协议：同一 Environment + EvalClient 的 before/after，
   报告口径与 §4.4 量化指标对齐
5. rollout 预算与算力预算（决定任务规模上限与 num_samples）
6. 预期结论形态（简历叙事的收尾：证明"设施有效"的最小实验是什么）
```

S0 退出条件在原有 V1~V4 之上，增加"实验设计文档初稿完成"。

## 7. 结论

1. **项目继续推进**。slime 的扩张商品化了中段（捕获 + 示例级评分），但环境生产、评分隔离语义、anti-cheat、训练资格治理、多后端解耦这六个维度仍然空缺，且它们正是设计文档 2 划定的自建层。简历叙事按 §1.3 校准。
2. 实现范围按 §3 收敛：P0/P1/P2 三档 + B1~B7 生产线 backlog，八条明确排除。
3. 简历亮点按 §4 补强：作弊注入演示（D4）、parity 证明、benchmark card、量化口径、实验叙事章节（D5），以及本轮新增的 train-test mismatch 故事线、假阳性解检测、评分故障域工程、沙箱确定性重放（D6）。
4. **§2 参考资料核对台账已完成：R3~R12 逐份对照，无推翻性发现。** 4 条矛盾/假设修正（M1 routing replay 升级为 S0 硬验证项、M2 评分接口 backend-neutral 化、M3 埋点补容器冷启动、M4 logprob_source 标注）和 24 条增量的处置已定。
5. **D1~D7 全部定案（§5.1），GLM-5.2 增补三项定案（§6）**：训练接口算法无关（GRPO 组语义降为可选）、Anti-Hack 升级为在线拦截 + dummy 观测 + 继续 rollout（attempted/executed 区分资格）、实验设计与 S0 并行独立成文（S1 冻结前完成初稿）。训练目标定为 MoE 模型，接入形态 S0 评估时 MoE 显著加分形态 B。
6. **剩余待定**（转入实验设计文档，不阻塞回写与 S0）：具体模型型号、算力预算、算法族最终选择、评测集协议。下一步：把本文全部定案回写设计文档 2，然后进入实施计划设计。
