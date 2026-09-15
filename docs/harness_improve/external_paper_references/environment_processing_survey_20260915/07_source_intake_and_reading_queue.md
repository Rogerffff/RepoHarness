# 补齐的原始资料与后续精读队列

[返回总入口](README.md)。本次补入 **29 份 PDF，覆盖 28 项工作/资料版本组**（MEnvAgent 保留 v1、v3 两份），共约 **95.5 MB**；另有三份官方质量审计网页。PDF 首页版本、页数、来源和下载校验记录见 [清单](sources/manifest.json)。均保留原文件内容；没有下载 Docker 镜像、模型或大型代码仓库。

**阅读状态：**第 [05 章](05_new_environment_builders.md) 的三篇、以及第 [06 章](06_new_quality_sources.md) 的来源已做方法相关章节核查；其余新 PDF 本轮仅核身份/摘要/相关性，以下是精读入口和问题，不冒称完整方法结论。已有精读的专题汇总在 01–04 章。

这是供用户给外部 Pro 排队的建议，未启动新的外部线程或任何环境实验。

## 先补环境构建与质量细节

| 来源与本地原文 | 环境相关内容／精读要核的细节 |
| --- | --- |
| [SWE-Factory: Your Automated Factory for Issue Resolution Training Data and Evaluation Benchmarks](sources/swe_factory_2506.10954v3.pdf)<br>2506.10954v3 · 21页 | 多角色构建、局部返工、二进制测试资产、整体退出码。核清 error-to-pass 与真实 F2P；已专题摘录，独立提示词附录未取得。 |
| [MEnvAgent: Scalable Polyglot Environment Construction for Verifiable Software Engineering](sources/menvagent_2601.22859v3.pdf)<br>2601.22859v3 · 25页 | 规划—执行—验证、历史环境检索与增量适配。以 v3 主读，对照 Pro 引用的 v1；不要混结果。 [v1对照](sources/menvagent_pro_version_2601.22859v1.pdf)。 |
| [SWE-Universe: Scale Real-World Verifiable Environments to Millions](sources/swe_universe_2602.02361v1.pdf)<br>2602.02361v1 · 13页 | 在 buggy/fixed 状态间自验证、循环内反捷径和独立质量判断。重点查构建者怎样避免伪造区分信号。 |
| [SWE-Bench Pro Verified: A Reliable Benchmark for Software Engineering Agents](sources/swe_bench_pro_verified_2609.08149v1.pdf)<br>2609.08149v1 · 37页 | 2026-09-08 新文：同时修题目质量与运行期答案泄漏。优先核修订依据、正常工具能力保持和修改后的评测口径。 |
| [Immersion in the GitHub Universe: Scaling Coding Agents to Mastery](sources/scaleswe_appendix_2602.09892v4.pdf)<br>2602.09892v4 · 25页 | 已有 O05 精读，但附录 E 生产提示词曾未获取。本次 PDF 确实含提示词，补读即可，不必重做整篇。 |
| [SWE-bench Goes Live!](sources/swe_bench_live_2505.23419v2.pdf)<br>2505.23419v2 · 24页 | RepoLaunch 自动恢复环境，持续更新真实 issue–PR 题。重点核历史依赖、测试解析、逐题接纳与失败类型。 |
| [SWE-Dev: Building Software Engineering Agents with Training and Inference Scaling](sources/swe_dev_thudm_2506.07636v2.pdf)<br>2506.07636v2 · 20页 | THUDM 的 SWE-Dev：真实任务与测试合成、轨迹扩展。重点核生成测试的校准方式和已有 Gym 的差别。 |
| [Automated Benchmark Generation for Repository-Level Coding Tasks](sources/setupagent_2503.07701v1.pdf)<br>2503.07701v1 · 25页 | SetUpAgent：历史依赖安装、测试执行及结果解析；SWEE-Bench/SWA-Bench 扩展到更多仓库与应用。 |
| [SWE-Bench++: A Framework for the Scalable Generation of Software Engineering Benchmarks from Open-Source Repositories](sources/swe_bench_plus_plus_2512.17419v1.pdf)<br>2512.17419v1 · 21页 | 四段生产：程序采集、环境合成、版本间测试差异、质量验证。重点查状态变化能否排除偶然/错误失败。 |
| [SWE-Hub: A Unified Production System for Scalable, Executable Software Engineering Tasks](sources/swe_hub_2603.00575v1.pdf)<br>2603.00575v1 · 23页 | 统一仓库环境自动化、SWE-Scale 合成与多种任务生产。重点查共享运行底座、逐题验证和真实生产漏斗。 |

## 之后比较任务派生与测试质量

| 来源与本地原文 | 环境相关内容／精读要核的细节 |
| --- | --- |
| [SWE-Dev: Evaluating and Training Autonomous Feature-Driven Software Development](sources/swe_dev_feature_2505.16975v3.pdf)<br>2505.16975v3 · 41页 | 另一篇 SWE-Dev，来自 justLittleWhite：基于真实测试的动态调用关系挖去功能并生成需求。它是 feature development 数据，不是上一行的 THUDM 训练系统。 |
| [SWE-Flow: Synthesizing Software Engineering Data in a Test-Driven Manner](sources/swe_flow_2506.09003v2.pdf)<br>2506.09003v2 · 23页 | 按单元测试和 Runtime Dependency Graph 组织开发步骤，生成部分代码库、测试及代码改动；适合比较测试可见的开发任务。 |
| [SWE-Mirror: Scaling Issue-Resolving Datasets by Mirroring Issues Across Repositories](sources/swe_mirror_2509.08724v1.pdf)<br>2509.08724v1 · 21页 | 把真实 issue 的语义迁移到已建好的另一仓库 Gym；重点核迁移后题面、缺陷和新测试是否一致。 |
| [BugPilot: Complex Bug Generation for Efficient Learning of SWE Skills](sources/bugpilot_2510.19898v2.pdf)<br>2510.19898v2 · 24页 | 对比直接造 bug 与开发新功能时产生的 bug；重点核缺陷真实性、测试质量和生成分布。 |
| [SWE-Bench Pro: Can AI Agents Solve Long-Horizon Software Engineering Tasks?](sources/swe_bench_pro_2509.16941v2.pdf)<br>2509.16941v2 · 20页 | 原始 benchmark 的人工验证、补充需求/接口、公开与留出来源。与 OpenAI 审计及 Pro Verified 修订版分别读。 |
| [Toward Training Superintelligent Software Agents through Self-Play SWE-RL](sources/ssr_2512.18552v3.pdf)<br>2512.18552v3 · 21页 | Self-play SWE-RL：生成与求解共同训练。重点核任务有效性、不可解/退化任务控制；不因自博弈标签先批准采用。 |
| [Socratic-SWE: Self-Evolving Coding Agents via Trace-Derived Agent Skills](sources/socratic_swe_2606.07412v1.pdf)<br>2606.07412v1 · 21页 | 从历史求解轨迹提取技能/失败模式，再生成并验证新题。重点核闭环反馈与题目独立性。 |

## Terminal、工具与其他领域：扩域前再读

| 来源与本地原文 | 环境相关内容／精读要核的细节 |
| --- | --- |
| [Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in Command Line Interfaces](sources/terminal_bench_2601.11868v1.pdf)<br>2601.11868v1 · 84页 | 原始 Terminal-Bench 2.0 论文，人工任务、参考解与测试及错误分析；84页，正文和附录应一起读，不能用训练衍生数据的结论替代。 |
| [SETA: Scaling Environments for Terminal Agents](sources/seta_2607.10891v1.pdf)<br>2607.10891v1 · 32页 | SETA terminal 环境扩展。核任务生成、oracle、测试、难度与去污染的具体接受条件。 |
| [EnvFactory: Scaling Tool-Use Agents via Executable Environments Synthesis and Robust RL](sources/envfactory_2605.18703v1.pdf)<br>2605.18703v1 · 34页 | 可执行工具环境合成与鲁棒 RL；重点核自然用户意图、状态/工具实现和 verifier 的一致性。 |
| [Agent-World: Scaling Real-World Environment Synthesis for Evolving General Agent Intelligence](sources/agent_world_2604.18292v1.pdf)<br>2604.18292v1 · 48页 | 真实主题、数据库与可执行工具生态→可验证任务→持续训练；重点核工具执行与模拟的边界。 |
| [SENTINEL: Failure-Driven Reinforcement Learning for Training Tool-Using Language Model Agents](sources/sentinel_2606.12908v1.pdf)<br>2606.12908v1 · 11页 | 失败驱动的工具任务生成；核失败分类怎样进入 proposer，以及防止只迎合当前策略的检查。 |
| [Training Language Model Agents to Find Vulnerabilities with CTF-Dojo](sources/ctf_dojo_2508.18370v2.pdf)<br>2508.18370v2 · 41页 | 将 CTF 挑战容器化为可执行训练环境；核挑战资产、验证器、运行隔离与非 SWE 适用边界。 |
| [CUDA Agent: Large-Scale Agentic RL for High-Performance CUDA Kernel Generation](sources/cuda_agent_2602.24286v1.pdf)<br>2602.24286v1 · 32页 | CUDA kernel 开发环境、验证与性能反馈；核硬件、数值正确性、计时稳定性与特权工具条件。 |
| [AgentRL: Scaling Agentic Reinforcement Learning with a Multi-Turn, Multi-Task Framework](sources/agentrl_2510.04206v1.pdf)<br>2510.04206v1 · 24页 | 多轮、多任务 RL 与环境执行架构；重点查接入与恢复，而非预设存在 SWE 全套清洗流水线。 |
| [OpenClaw-RL: Train Any Agent Simply by Talking](sources/openclawrl_2603.10165v2.pdf)<br>2603.10165v2 · 33页 | 用户/工具下一状态反馈接入训练，当前 v2。核真实环境反馈、异步评分与实验任务构造。 |
| [RLVE: Scaling Up Reinforcement Learning for Language Models with Adaptive Verifiable Environments](sources/rlve_2511.07317v2.pdf)<br>2511.07317v2 · 23页 | 已有人工程序化环境摘要与本轮 v1 专题；补存 v2 作完整精读和版本对照，不能把难度控制直接当 SWE 资格。 |
| [Agentic Environment Engineering for Large Language Models: A Survey of Environment Modeling, Synthesis, Evaluation, and Application](sources/agentic_environment_survey_2606.12191v1.pdf)<br>2606.12191v1 · 63页 | 环境建模、合成、评估、应用的综述地图。用于继续查漏；引用具体机制时回到其一手论文。 |

## 网页与仍未补齐的部分

- [METR、Cursor、Datacurve 原文快照](sources/web_quality/manifest.json)：三份均取得正文。专题摘要和各自的检查边界见 [06](06_new_quality_sources.md)；完整图表/交互资产不在此次离线包内。
- **GLM-5.3**：本次重试官方博客仍没有取得可读正文；旧稿只有预读线索，不列作已证实环境方法。其产品文档不能替代后训练报告。
- **SWE-Factory 独立 Appendix.pdf**：论文所链地址与本次仓库核查未取得文件；[获取记录](sources/swe_factory_supplement/manifest.json)保留失败事实，并附已取得的官方 README。正文足以支持专题摘录，不代表提示词附录已读。
- **既有精读缺口**：LinkedIn Real-World Code Repair 原图、SWE-rebench 演讲视频/幻灯片还需补核；不把“我们的阅读没覆盖”写成“作者没公开”。

队列覆盖本地索引、两份 Pro 建议及本轮一手来源追查发现的相关缺口；没有声称穷尽全部外部文献。已有模型卡但没有具体环境做法的来源，不为增加数量单列方法条目。
