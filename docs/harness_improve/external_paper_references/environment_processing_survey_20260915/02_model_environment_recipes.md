# 模型团队与 Cognition 评测：环境处理逐篇汇总

整理于 2026-09-15。以下以已有精读中的来源版本为准；是环境专题汇总，不是重新完成全部论文精读或运行复现。**流程明确不等于配置完整，作者报告的效果也不等于本项目已验证。** SWE-Check、SWE-grep 只有原始材料，另标专题初读。

## 一、真实仓库任务的生产与复审

### R1 · MAI-Thinking-1

- **处理流程：**真实 PR 筛选 → agent 构建 Docker → 比较原始/修复代码上的测试，提取 F2P/P2P → 在真实训练 SEE 环境多次确认 empty 失败、gold 成功并排除不稳定测试 → 审查题意清晰度、测试质量、泄漏与可行性，必要时改写。约 487 万候选中，208 万构建通过、745,452 个提取出参考信号、265,617 个通过 SEE 复验；最后一个数仍不是最终训练题数。不合格题的可运行环境可复用来合成新任务。
- **环境与执行：**每任务新容器；预装依赖，隐藏测试在评分时应用。默认隔网，必要访问走缓存代理和域名许可；清理未来 Git 信息，恢复候选改动的测试，monitor 加人工复查作弊。按仓库复用离线构建 actor 和 BuildKit 层，减少重复安装。**评分在原 agent 容器内执行，不能引用它证明已采用 fresh grader。** 通用工具任务另用带状态的 mock API/MCP，执行验证、去重、critique/refine 后评分最终状态与工具使用。
- **对我们有用：**把构建成功、参考信号、真实运行复验、题意质量分开记录。重复次数、质量阈值、合法替代解审计及最后保留量未公开。

定位：[精读 §6.1–6.5](../reading_notes/R1_mai_thinking_1.md#6-coding--swe--terminal-环境与任务生产)；原报告 §3.3.1、App. F（[官方 PDF](https://microsoft.ai/wp-content/uploads/2026/06/main_20260602_2.pdf)，本地/官网两个版本的页码差异见精读 §1）。

### N01 · KAT-Coder-V2.5

- **处理流程：**从 gold/test patch 分别提炼问题、requirements 与接口约束；build agent 生成安装和测试脚本，verification agent 在隔离沙箱解析结构化测试输出，将失败反馈给构建者迭代。验收要求是**收集到超过 90% 的预期测试且状态可重复**，不是 90% 测试通过。预配置底座、模板、成功配置检索库提高构建复用；只把不属于编程挑战的依赖/配置变更预先应用，并清理解法线索。
- **质量与修复：**内部 Code Bench 用采样、执行、人工和轨迹审计排除 flaky 环境、误杀替代合法解、题意—verifier 不符；near-miss 可先带提示取得验证补丁，再从原上下文重建无提示轨迹并检查泄漏。可修复问题、应拒绝缺陷、可生产产物分流。另有 Skill→服务/fixture→任务→容器执行的三层一致性校验，失败局部修复。
- **鲁棒性数据：**改写工具名、参数与输出包装；刻意注入依赖不匹配、瞬态命令失败、截断/噪声日志。这是有意保留可处理困难的训练任务，不是允许 sandbox 给出错误评分；注入概率、严重度和独立收益未给。
- **对我们有用：**先查收集/执行正确性，再谈通过率；区分必要 setup 与应由 solver 解决的任务。作者修复 sandbox 错反馈后报告轨迹故障约 16%→低于 2%，但审计分母、阈值、题单与完整 grader 权限未公开，不宜照搬百分比门槛。

定位：[精读 §4、§6.3、§7.1](../reading_notes/N01_kat_coder_v2_5.md#4-数据环境与轨迹生产)；[原文 §2.1–2.2、§3.4、§4.2.2、§6.1](https://arxiv.org/html/2607.05471v1)。

### R3 · Qwen3-Coder-Next

- **处理流程：**真实 PR 拆 buggy state、fix、test patch；构建 agent 生成 Docker 和验证脚本，要求实际区分坏/好状态，过滤只做表面检查的 verifier；QA agent 剔除题意含糊、环境不一致、测试错配。另一条线复用可运行仓库，模型/规则注入 bug，以原测试 PASS→FAIL 和回退可恢复为条件，生成 issue，并移除暴露触发条件的测试文件。两池分别统计真实 PR 环境与合成任务，不能直接相加为去重训练题量。
- **训练期检查：**估计任务通过率，移除过易和 noisy failure；保留安装依赖/查文档所需网络，同时针对目标仓库链接加网络调用拦截，清理 remotes/branches/tags。后期发现模型重建 remote 获取修复，反过来更新防护。
- **其他验证：**SFT 回答由终端 agent 实际运行命令/代码；WebDev 在 Chromium/Playwright 中渲染，结合截图、DOM 动作和前后状态筛除坏交互。单轮 coding RL 生成候选测试，以独立生成解间共识选测试；共识不是正确性保证。工具定义/调用/返回包装的多样化则用于接口适配。
- **对我们有用：**验证器本身会取巧，也需要质检；环境复用和新题合成是两步。完整 no-op/合法替代解、重复稳定性与拦截漏报率未给；详细构建法转引 **SWE-Universe**，值得单独精读。

定位：[精读 §3.3–3.6、§4、§5.3](../reading_notes/R3_qwen3_coder_next.md#4-coding--swe--terminal-数据与环境)；[原文 §2.1、§4.1–4.2、App. A.1](https://arxiv.org/html/2603.00729v1)。

### R4 · MiniMax-M2 系列

- **SWE：**采集宽松许可仓库 PR → 构建 agent 依执行反馈修 Docker → 按任务类型分流 → 验证奖励 → 模型检查题意/测试一致性并补足信息 → 任务转换扩增。Bug fix 用 F2P/P2P；feature 检查新功能点；performance 要同时保行为、确认稳定性能差异；写测试任务要求 pre-patch 失败、post-patch 通过；code review 则允许无运行环境。不能把全部变体套进一个 bug-fix 门槛。
- **其他环境：**Terminal-Gym 从 Stack Overflow 可验证问答产生明确输入/输出/环境的任务，迭代修 Dockerfile/tests，受限重试，变更 hints 后共用测试并做难度筛选。AppDev 用专家种子/rubric，去重、可行性筛查，部署应用后按执行、浏览器交互、视觉分层验收。办公任务检查文件产物，表格用外部引擎重算和 gold cell 对比，slides 叠加执行/布局/渲染评分；金融工具先执行取得证据，再反推任务。
- **对我们有用：**任务类型决定验收依据；“能运行”之外还要检查请求与测试一致。没有给完整保留漏斗、替代解/不稳定性审计及阈值；terminal 停止修复不等于已说明最终淘汰规则。

定位：[精读 §3、§4.1](../reading_notes/R4_minimax_m2_series.md#3-coding--swe--terminal-任务生产)；[原文 §4.1–4.2，v2](https://arxiv.org/abs/2605.26494v2)（与 v1 技术内容相同）。

### R6c · DeepSeek-V4.1-Flash

- **处理流程：**任务定义为问题、环境、验证系统三元组。复杂真实 coding session/筛选后的仓库 → 可构建可验证检查 → agent 选 turn/commit、设计实现方向及 F2P/P2P 评价点 → 另一 agent 安装依赖、准备目录/测试/题面、自测并清除答案痕迹 → 多 agent 试做 → 独立质检检查事实、题意错配和 hackability → repair 后重新验证。每次新 RL run 的轨迹继续用于复审；不是一次验收后永久合格。
- **其他环境与资源：**真实业务交互/负反馈转成具接口和状态约束的 mock 服务。DSec 分区放置、节点资源准入、NUMA/优先级隔离、每 sandbox 网络策略与执行记录支撑运行。**agent 自己损坏环境算失败轨迹**，不自动归成平台故障丢掉。
- **对我们有用：**建题、搭环境、求解、质检分角色，运行反馈回流修环境。报告未给构建/质检各关分母、采样次数、完整 gold/no-op/替代解协议及任务版本规则；调评价点可能改变题义，需要我们另行决策。

定位：[精读 §6.2–6.3、§7.1](../reading_notes/R6c_deepseek_v41_flash.md#6-后训练流程与任务环境生产)；报告 §5.1.1–5.1.3，pp.25–29（[官方定位入口](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/DeepSeek_V41_Tech_Report.pdf)；精读基于用户提供的冻结 PDF，未证明与当前 main 字节一致）。

## 二、现成任务接入、专门化训练与其他环境

### R2 · Nemotron 3 Ultra

- **SWE：**SFT 从 SWE-Gym、R2E-Gym、SWE-rebench/v2 采多 harness 轨迹，检查有效提交、工具错误、调试残留、编辑后验证及禁用 Git 行为。SWE teacher 经单步 PivotRL 再多轮仓库执行，用 hidden tests 给二元奖励；这些 SFT 来源不等于已公布 teacher RL 的确切题池。
- **环境：**物理重写 Git 为 base 时刻，过滤 remote Git 与 GitHub 下载通道；未声明全面断网。terminal 轨迹在真实终端执行，专项任务允许长 timeout 并重新 profiling。CUDA 任务经过编译、数值和 runtime 验证后选快实现；RTL 做语法、语义与去污染筛查。生产记录 sandbox/tool 故障构成，镜像本地缓存和单 sidecar 归档减少 I/O 争用。
- **对我们有用：**任务有效、轨迹适合监督、执行稳定应分开。启发式 SFT 过滤不宜直接当训练题淘汰标准；构建漏斗、重复评分、替代合法解与 fresh grader 协议未给。

定位：[精读 §3.2、§4.2–4.3、§7.2](../reading_notes/R2_nemotron_3_ultra.md#4-教师关系swe-环境与其他专业训练)；[报告 pp.17–26、32–36](https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf)。

### E10 · Intern-S2-Preview

- **现成来源：**将 SWE-smith、SWE-Gym、R2E-Gym、SWE-rebench V2、Scale-SWE、terminal 等材料统一成初始仓库/容器/资产、目标与 verifier，**保留来源特有测试和 reward 语义**。harness 与 task 分开组合；表中来源库存不是最终消费漏斗。
- **质检：**gold、held-out tests、精确评分 IDs 不进 rollout workspace；Git 清为单 baseline，恢复 canonical tests 后评分；有 expected test-state map 的来源按映射匹配。缺工件、执行错误、解析失败单独记账。另一条社区 skill 线按状态兼容组合能力，逐阶段用可执行 validator 与 rubric 检查、局部 repair/regenerate，再以失败反馈更新模板。
- **对我们有用：**统一运输可以保留来源语义，不能用一个通用 parser 抹平差别。未给镜像验收漏斗、网络合同、重复/替代解检查、错误的完整训练处置；“错误单列”不等于作者都丢组。

定位：[精读 §5.1、§5.3–5.6](../reading_notes/E10_intern_s2_preview.md#5-agentic数据harness训练与-verifier)；[原文 §4.4](https://arxiv.org/abs/2608.13505v1)。

### E11 · Nemotron-Cascade 2

- **SWE：**复用 SWE-Gym、SWE-rebench、R2E-Subset 的 agentic SFT；执行 RL 使用 SWE-Gym 与 R2E-Subset，经 OpenHands 编辑/测试，以编译、单元测试评分。中间模型每题预采 16 条，移除全成功题、随机删除 90% 全失败题；这是能力/训练信号预筛，**不是证明全失败题环境无效**。大批没有 Docker 的任务走另一路 agentless 模型评分，不冒称执行验证。
- **其他环境：**Terminal-Task-Gen 把静态题、种子和 skill 分类改造成可运行任务，在隔离 Docker、Terminus 2 中以执行反馈生成轨迹。
- **对我们有用：**把环境质检与模型难度筛选分开；公开来源有训练证据，但本篇没有完整 gold/no-op、flakiness、评分隔离、权限与失败处理实现。两条 SWE 训练路线的证据不能合并成同一种 verifier。

定位：[精读 §3.4、§7](../reading_notes/E11_nemotron_cascade2.md#7-swe-两条训练路线廉价修复监督与真实执行互补但证据不能合并)；[原文 §3.2.9–3.2.10、§4.8，v2](https://arxiv.org/abs/2603.19220v2)。

### R13 · Kimi K3

- **其他环境方法：**知识图谱按概念扩展/复用取材；个人助理用持久 mock apps，按多日事件和最终状态评分；AET 把初态、目标、工具、预算、独立 verifier 配齐，公开接口供诊断、hidden verifier 测 held-out 情境。Webdev 结合确定性执行、视觉/交互评审；kernel 检查数值精度与性能，跟随新作弊方式更新检测。
- **执行支撑：**同时使用容器、GPU sandbox、AgentENV microVM。后者支持增量 checkpoint、暂停、恢复和 fork；fork 可隔离评分副作用，但保留被 fork 状态中原有的候选污染风险。镜像分层与缓存支撑复用。
- **对我们有用：**可观察状态、独立验收与资源生命周期值得参考。SWE 自身的 PR→环境→有效题漏斗、题意修复、重复与替代解检查没有展开；AET 的 hidden/public 规则不能推广到全部 SWE，百万镜像也不是百万独立题。

定位：[精读 §5、§6.2](../reading_notes/R13_kimi_k3.md#5-全领域任务生产环境与评分)；[原文 §4.2、§5.3.2，v2](https://arxiv.org/abs/2607.24653v2)（相关技术正文与主读版本无实质变化）。

### R5b · GLM-5.2

- **边界执行：**每步先规则找可疑工具调用，再 LLM 判意图；确认违规则阻断该调用、返回替代 observation，保留任务继续求解，同模块用于训练和评测。覆盖读评分材料、复制引用/上游提交等，未给误报率或检测器配置。
- **环境协议：**脚注按 benchmark 分列资源与网络：DeepSWE、ProgramBench 是隔离离线条件；Terminal-Bench 的不同 harness 采用不同时间/资源预算，不能以一个“长上下文”标签替代运行合同。
- **对我们有用：**每题工具/联网/资源策略必须具体，拦截某步与整条样本终止是不同选择。博客没有提供 SWE 环境生产/筛查漏斗、完整 grader 隔离或违规后的 reward/mask，不能把继续执行解释成无惩罚。

定位：[精读 §5.2、§7](../reading_notes/R5b_glm5_2_blog.md#5-rl-for-long-horizon-task-with-anti-hacking)；[官方文章 Anti-hacking、Footnote](https://huggingface.co/blog/zai-org/glm-52-blog)。

## 三、Cognition：持续修订环境与评分

### SWE-1.5

- **做法：**与维护者和资深工程师手工设计贴近产品语言/任务分布的环境；组合单元/集成测试、质量 rubric、浏览器 agent 端到端验收。专家主动找 grader 漏洞，修补经典测试遗漏；产品试用反馈推动工具/prompt 修改后重训。VM 平台提供代码和浏览器执行。
- **边界与用途：**这是人工环境设计、奖励强化和真实工具联合迭代的证据。没有公开任务数、分项成本、重复 gold/no-op、合法替代解保持率或完整评分隔离。后续 FrontierCode 细则不能倒填成 1.5 已采用的协议。

定位：[精读 §2–3、§5](../reading_notes/cognition_swe1_5.md#3-训练环境三类评分与人工hardening)；[原文 RL Coding Environments](https://cognition.com/blog/swe-1-5)。

### SWE-1.6 Preview

- **做法：**为实际 SWE-bench Pro 评测，人工读数百条轨迹并与 Scale 发布轨迹核对，调试依赖、agent/grader 环境、不同 harness 的 timeout、补丁收集/应用边界、grading OOM；检查训练仓库与评测仓库不重叠。
- **边界与用途：**说明“能运行官方评测”仍需逐阶段对账，不只是增加 CPU。没有公开整套训练任务生产、统一重试或资源配置；repo 不重叠也不是完整污染审计。该文的环境调试不能据此全部归因于模型差异。

定位：[精读 §3.1](../reading_notes/cognition_swe1_6_preview.md#31-环境与评分调试是真实工作的组成部分)；[原文 Evaluation Details](https://cognition.com/blog/swe-1-6-preview)。

### SWE-1.7

- **做法：**自动执行 QA 同时降低错误解放行、合法解拒绝，指向 FrontierCode 校准法；按模型通过率移除总成功/总失败任务，偏好少量成功题；限制网络、移除 Git 历史/参考工件、隔离 grading path，程序检测作弊尝试即 reward 0。训练允许长程、自压缩，并交替施加 token/turn/tool-time 成本预算。
- **边界与用途：**环境可信、可学习难度、运行预算是三个维度。未公开采样次数、阈值、题单、误杀率及具体隔离实现；零分不是删除轨迹。低通过率任务选择是其训练经验，不是通用环境质量门槛。

定位：[精读 §5–6](../reading_notes/cognition_swe1_7.md#6-数据verifier-与学习机会)；[原文 Data Quality、Self-Compaction](https://cognition.com/blog/swe-1-7)。

### SWE-2

- **做法：**扩大仓库分布和更难环境，数量称为 1.7 的三倍；在既有任务叠加指令遵循要求。将训练 rollout 和前序 checkpoint 的解答回流，修 verifier 的假阳性与假阴性，再继续生成/训练。
- **边界与用途：**持续重审尤其要检查新模型的合法创造性解是否被误杀；这是运行后证据的价值。没有完整数据漏斗、叠加约束的验收方式、版本更新节奏或误判量化，不能由“三倍环境”推成三倍有效训练信号。固定候选回放、变更留版本是我们的建议，原文未完整披露。

定位：[精读 §7](../reading_notes/cognition_swe2.md#7-数据与环境数量扩展只是其中一部分)；[原文 Data Improvements](https://cognition.com/blog/swe-2)，使用 2026-09-11 冻结快照。

### FrontierCode 原版（1.0）

- **做法：**维护者从真实多 PR 链/自由需求选题，任务附仓库指南。验收组合功能/回归、命令、agent 测试有效性、范围、质量 rubric；区分 blocker 和质量分。五阶段 QC 为设计 → 故意错误高分解及正确替代解找漏洞 → 四份分档解校准 → pod lead/研究员审查、随机子集亲自求解 → 反复复审。
- **修复方向：**reverse-classical 在 base 上跑 agent 测试；mutagent 可适配测试甚至应用代码以容纳表面差异。后者不是纯确定评分，也未公开语义保持的保证。替代解与错误解成组校准，最值得借鉴；不能只跑 gold/no-op。
- **边界：**任务未公开，不能直接当训练池；每题 40+ 小时的人力路线也不能假设等价于一次 agent 静态读题。其误判下降主张受抽样/人工标准限制，完整 grader 和校准解未提供。

定位：[精读 §3.3、§4–5、§7.2](../reading_notes/cognition_frontiercode.md#33-五阶段-qc真正的工程资产是成组校准解)；[原文 Quality Control、Novel Grading Methods](https://cognition.com/blog/frontier-code)。

### FrontierCode 1.1

- **做法：**明确允许通用文档/API/概念检索，禁止获取本题上游修复及其镜像；用 fair-use prompt 加程序 scanner，标记运行计 0 分。针对误杀，复审 1,000+ blocker，将 75 项改为 non-blocker；仍影响质量分，**不是删除 75 道题或测试**。同时停止较小 Diamond 子集的报告。
- **边界与用途：**联网策略应看资料与本题答案的关系，而非只问能否访问 GitHub；全面断网/名单策略有任务能力和维护成本取舍。但 scanner 未公开，作者所称提示后违规低于 1% 不证明检测无漏报，也不证明直接 RL 优化后仍成立。新版网络/评分变化不能当成权重提升，改 rubric 后应重新对账。

定位：[精读 §3–4、§6](../reading_notes/cognition_frontiercode_1_1.md#3-信息边界允许帮助推理的资料不允许直接揭示本题答案)；[原文 Getting Internet Use Right、Refined blocker criteria](https://cognition.com/blog/frontier-code-1.1)。

## 四、已有原始材料、尚待独立精读的专项来源

### SWE-Check · Bug detection（原文专题初读）

- **做法：**在源 commit 仓库沙箱中分析 diff，输出结构化 bug/修复，与参考 bug 集匹配；覆盖多语言/bug 类型并复刻 Windsurf 生产工具。内部使用发现“查一下定义就知道并非 bug”的误报后，给生产和训练同时补 tracing 工具再训练。LLM 先查报告是否错误合并多个问题，再做真值匹配；同时保留无 bug 任务。ID 评测留出同源随机题，OOD 是完全留出的内部真实 bugs。
- **边界与用途：**误报可能来自工具面不足，不只有模型不聪明。参考 bug 集是否完整、额外真实 bug 的接受、补丁执行验证和切分粒度未充分披露；这不是 SWE 修复 all-tests-pass 环境。完整奖励公式与图表留待精读，本节不评价其训练算法。

定位：[已下载正文](../reading_notes/source_supplements/cognition_20260911/swe-check/reading_text.md)，The SWE-check Agent / Training with production settings；[官方文章](https://cognition.com/blog/swe-check-10x-faster)。

### SWE-grep / SWE-grep-mini · 代码检索（原文专题初读）

- **做法：**真实仓库、用户查询、相关文件/行区间真值构成专门任务；输出可核验范围，避免靠自由摘要评分。限制 grep/read/glob 等跨平台工具，训练和主评测最多 4 轮、每轮最多 8 个并行调用，以文件/行范围精度召回及延迟验收。通过受限工具、索引和并行执行共同设计任务；用困难 SWE-bench Verified 子集另检下游效率。
- **边界与用途：**可把“定位是否充分”拆成可检查中间任务，但真值范围不完整可能误杀另一条有效检索路径。原文没有公开标注者一致性、题量/切分和所有合法范围，不应把这一检索评分当成最终修复正确性；演示容器对比也不是严格环境实验。

定位：[已下载正文](../reading_notes/source_supplements/cognition_20260911/swe-grep/reading_text.md)，Motivation / Data and Evals；[官方文章](https://cognition.com/blog/swe-grep)。

本组另检查了 [R5c GLM-5.3](../reading_notes/R5c_glm5_3_blog.md)：现有文档明确是来源获取失败的预读，oracle/no-op/unsolved-state 等仅是待核线索，**本汇总不把它们列为已证实做法**。获取原文后的补读任务见总入口。

核查范围：复用各篇最终修订稿和批次审查结论；本次直接回查了 KAT/Qwen/FrontierCode 两版官方正文，SWE-Check/SWE-grep 读本地原始正文。未重跑任何环境，也未逐篇重新核验所有图表；来源完整性与未披露项以各篇记录为准。
