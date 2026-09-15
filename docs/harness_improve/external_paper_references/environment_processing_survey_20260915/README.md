# 外部资料如何处理 SWE 与其他任务环境

2026-09-15 · B 线环境专题。**先逐篇看作者实际做法，再决定我们的流水线；本汇总不新增环境筛选或评分规则。**

已 `fetch origin`；本地与远端 `miles-migration` 均为 `4529ebd7`（FrontierCode 原版与 1.1 精读），没有待拉取更新。三名 sub-agent 并行整理，主线程补查原始 PDF、新来源并合并；04 章另经独立原文复核。

## 按来源阅读

每条尽量只写：**怎样处理环境／测试，能参考什么，哪些没有证明**。旧精读、原文与页/节均附在条目后。

| 分组 | 包含的来源与重点 |
| --- | --- |
| [01 · SWE 题库与质量审查](01_swe_tasks_and_quality.md) | SWE-Gym、R2E-Gym、SWE-smith、ScaleSWE、SWE-rebench、DeepSWE、Prime、OpenAI、FrogNano、LinkedIn；历史环境、测试语义、题意和稳定性。 |
| [02 · 模型团队与 Cognition](02_model_environment_recipes.md) | MAI、KAT、Qwen、MiniMax、DeepSeek、Nemotron、Intern、Kimi、GLM、Cognition 各版；真实生产、修订和质量校准。 |
| [03 · Terminal、其他环境与运行框架](03_terminal_and_runtime.md) | CalibForge、Envs-FORGE、Endless、ECHO、Nemotron-Terminal、OpenThoughts、Hardening 等；另区分运行框架提供了什么、没有替我们验证什么。 |
| [04 · 已有 PDF 中的补充方法](04_existing_pdfs_topic_scan.md) | GLM-5、DeepSeek V3.2/V4、Kimi K2/K2.5、MiniMax-M1、Composer 2、ROME/ROCK、ROLL、MiMo。此前没有独立精读，本轮只读环境有关部分。 |
| [05 · 新补的环境构建方法](05_new_environment_builders.md) | SWE-Factory、MEnvAgent、SWE-Universe；核实 Pro 提到的分工、增量修复与反捷径。 |
| [06 · 新补的质量与协议审计](06_new_quality_sources.md) | METR、Cursor、Datacurve DeepSWE v1.1、SWE-Bench Pro Verified；区分可合并性、答案泄漏、评分协议和题目修订。 |
| [07 · 已下载原文与精读队列](07_source_intake_and_reading_queue.md) | 29 份 PDF（28 项工作/版本组，约 95.5 MB），另有三份官方网页。逐项说明优先级、版本、用途及待补读内容。 |

**范围与证据：**筛查了顶层精读库全部实质笔记、原 manifest 的 32 份 PDF 对应资料、相关 knowledge 摘要及 Cognition 补充材料；旧汇总只用于去重和找来源。各组覆盖/排除清单见 [核查记录](coverage.json)。不相关的纯算法、模型架构材料不进入方法正文。已有精读以其最终修订稿为基础，不宣称本轮重新逐页精读全部原文；新下载也不等于精读完成。没有运行环境实验或修改训练代码。

## 为我们的讨论，先看这六个区别

1. **搭得起来、测得正确、题意充分是不同检查。** MAI 的构建/参考信号/真实环境复验，SWE-rebench 的安装/parser/稳定性/题意，SWE-Universe 的反捷径/质量 judge，是互补证据；不是所有团队都公开了同一套完整流程。[01](01_swe_tasks_and_quality.md) · [02](02_model_environment_recipes.md) · [05](05_new_environment_builders.md)
2. **通过 empty/gold 只证明有限区分能力。** OpenAI 审计、CalibForge、FrontierCode 和 METR 分别补查未说明要求、误杀替代解、错误解放行、维护者接受度。不能把这几种问题混成一个“坏题率”。[01](01_swe_tasks_and_quality.md) · [02](02_model_environment_recipes.md) · [03](03_terminal_and_runtime.md) · [06](06_new_quality_sources.md)
3. **验收规则不能跨来源硬套。** R2E 可以保留预期 FAILED；KAT 的 90% 指测试收集率；SWE-Factory 使用主测试命令整体退出码。共享执行器可以统一记账，不能悄悄改变各来源的分母和成功定义。[01](01_swe_tasks_and_quality.md) · [02](02_model_environment_recipes.md) · [05](05_new_environment_builders.md)
4. **没有统一的断网答案。** MAI 用隔离与受控访问；Qwen 保留依赖/文档需求并反作弊；FrontierCode 1.1 用规则与检测；Cursor 又测试更严格的出口策略。我们仍需分环境准备、agent 求解、候选安装、测试执行决定资源如何提供。[02](02_model_environment_recipes.md) · [04](04_existing_pdfs_topic_scan.md) · [06](06_new_quality_sources.md)
5. **可复用环境不等于逐题已验证。** ScaleSWE、MEnvAgent 复用同仓配置后仍验证当前任务；SWE-rebench 三次结构化结果稳定与 Prime R2E 的“失败重试至少一次通过”不是同等级证据。[01](01_swe_tasks_and_quality.md) · [05](05_new_environment_builders.md)
6. **辅助模型是发现问题的工具，失败本身不是无效题证据。** 当前策略校准、环境正确性、后续学习价值要分开；修题要保留原版、改变的要求和反例。SWE-Bench Pro Verified 优先改题面匹配测试，也不应直接变成我们的默认原则。[01](01_swe_tasks_and_quality.md) · [03](03_terminal_and_runtime.md) · [06](06_new_quality_sources.md)

建议先读 **05 → 06 → 01 中 SWE-Gym/R2E/Prime**，再选 02 中 MAI/KAT/FrontierCode 对照。之后才能把“来源适配器统一检查”“仓库版本共性修复”“逐题语义审查”“风险驱动深查”分清；完整实施继续在 [最小评分接线计划](../../../agentic_RL/repo_harness_rh2_workstreams/project1_execution/swe_grading_wiring_20260915.md)讨论。

## 这次修正和保留的缺口

- **E12 旧名错误：**本地及 arXiv `2606.13392v2` 实为 *MiniMax Sparse Attention*，不是 MiniMax-M3 完整技术报告；已更正索引/manifest 的身份，原文件名保留以免打断历史链接。不能从它提取 M3 环境配方。
- **同名资料分开：**THUDM SWE-Dev 与 feature-development SWE-Dev 是两篇；Agentica DeepSWE 训练配方与 Datacurve DeepSWE 评测也不同。
- **GLM-5.3 正文仍未取得；SWE-Factory 独立提示词附录仍未取得。**不把旧预读线索计为事实。ScaleSWE 附录 E 已补齐 PDF，留待补读。更多版本/获取限制见 [07](07_source_intake_and_reading_queue.md)。
