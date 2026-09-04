# 《Post-Training on Office Work Improves Software Engineering: A Behavioral Account of Cross-Domain Transfer》阅读摘要

## 论文信息

- arXiv:2608.01604v1,2026-08-03 提交
- 作者:Logan Ritchie、Sushant Mehta、Liudas Panavas、Edwin Chen(Surge AI)
- 官方页面:<https://arxiv.org/abs/2608.01604>

## 核心问题

长程多工具任务(long-horizon multi-tool agentic tasks,LHMTA)的 post-training 收益能否跨域迁移?论文假设存在域通用的"目标导向执行"(goal-directed execution,GDE)能力——goal formation(目标形成)、state construction(状态构建)、goal stability(目标保持)、verification(验证)四项——因此在办公任务上做 RL 也应改进软件工程表现。

标题里的 "Behavioral Account" 指分析方法:通过轨迹中目标、行动、环境反馈与结果之间的可观察关系来解释行为变化,不做内部机制归因。

## 任务与 verifier 构建(LHMTA 数据集)

- 共 403 个任务:363 个训练 + 40 个 held-out 验证;论文两次明确写 "The collection contained no software-engineering tasks"(训练集零 SWE 任务)。
- 任务形态:通过 MCP(Model Context Protocol)server 暴露的真实办公工作流——文档/电子表格/幻灯片操作、搜索检索、文件管理、日程与日历、浏览器自动化、规划与办公服务工具编排;典型成功轨迹 30~40 次工具调用、80k~100k tokens。
- verifier:每任务一个确定性 Python grader,对最终环境状态按多条 criteria 判定;reward = 满足 criteria 的比例(轨迹级 dense reward,不做前缀级分配)。任务作者"targeted realistic work",但作者构成与质检流程细节论文未披露。

## 训练与结果(带具体数字)

- 模型:Qwen3.5-122B-A10B(122B 总参 / 10B 激活的 MoE),LoRA 挂在 attention 与 MLP 投影上。
- 两阶段:先用 Kimi K2.6 在 LHMTA 上生成轨迹并 rejection-sample(仅留得分 >0.9)出 3,000 条做 SFT 预热;再用 GSPO(sequence-level estimator)做 RL,每 prompt 采 8 条 rollout,用全部 363 个训练任务。
- 域内:LHMTA held-out 验证集 10.0%→27.5%(+17.5pp)。
- 跨域迁移:SWE-Bench Pro pass@1(greedy)20.5%→26.3%(+5.8pp);Toolathlon 22.2%→31.8%(+9.6pp);BFCL-V4 55.7%→59.2%(+3.5pp)。
- 行为分析(731 个 SWE-Bench Pro 配对任务):重复检索占比 22.5%→14.3%,检索到的不同信息量 7,985→9,019,平均检索调用 25.6→23.9,含正式测试运行的轨迹 37.5%→73.3%(验证频率近乎翻倍),patch 平均新增行数 415.5→111.7(实现更克制精准)。
- 论文结论主张:应把 post-training 数据视为"锻炼行为能力的经验",而不只是覆盖特定题材、工具或答案的示例;并自述因果关系仍需受控实验验证。

## 重要限制

- 单模型、单次训练,无跨随机种子复现;无因果消融,也无等预算对照组(例如同算力直接训 SWE 任务能提多少,未回答)。
- 行为解释来自对 103 个"基座失败→训练后成功"任务的迭代定性分析,存在选择偏差;各行为指标是间接代理信号。
- SWE-Bench Pro 只报 greedy pass@1 单点;评测所用 scaffold/harness 论文未说明。

## 对 RepoHarness 的意义

- 多域组合训练与跨域迁移目前最直接的证据:零 SWE 的办公任务 RL 让 SWE-Bench Pro +5.8pp,支撑我们"第二域投入不是零和"的判断——域 2 供给不只是摊薄域 1 算力,还可能反哺域 1。
- 迁移机制假设(GDE 四能力)加行为证据(验证率翻倍、patch 更克制、检索更少重复)提示:跨域收益走的是通用执行行为而非领域知识;设计第二域任务时应优先覆盖深度分解、状态维护、自我验证等结构,而不是题材表面多样性。
- 论文自己承认没有等预算对照:它只能支持"并行投入有正外部性",不能推出"第二域优先级高于第一域";我们排期仍以域 1 为主线。
- verifier 形态可直接借鉴:确定性 Python grader + 多 criteria 比例式 reward(而非二值)是已被验证的参考实现,与我们 grader 设计讨论对得上。
