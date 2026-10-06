# RepoHarness Agent Guide

更新：2026-09-28。本文件只保留当前定位、导航与必要协作规则；具体进展和决定维护在执行目录。

## 当前阶段与工作入口

当前聚焦**项目一：真实 coding agent 的可靠、高效后训练闭环**。主链为 **miles + SGLang + Claude Code + RH2**，并行推进链路修复、SWE 环境/数据、训练设计与测评。SWE 为主，terminal 为补充评测候选；项目二暂缓。正式题单、模型、配方和预算以具体决策为准。

**当前执行目录：** [project1_execution/](docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/README.md)

| 主线 | 职责与记录入口 |
| --- | --- |
| **A：链路正确性与运行效率** | [infra.md](docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/infra.md)：执行、轨迹/训练消费、通用评分运输、异常与清理、性能和观测。 |
| **B：环境、数据、评测与基座诊断** | [env_data_eval.md](docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_data_eval.md)：任务与环境清洗、具体评分依据、数据划分、真实 harness 下的基座测试和评测。 |

- 决策导航：[分组决策入口](docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/decision_batches_20260908.md)。具体决定、实施 Brief 和审查结果留在各批次原目录；交流与交接写入对应 A/B 记录。
- 主链计划与既有定案：[06 执行计划](docs/agentic_RL/repo_harness_rh2_workstreams/06-first-training-local-execution-plan.md)、[D2/B 定案](docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/decision_package_D2_B.md)。项目方向背景见[项目一设计建议](docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)，其中建议不等于用户批准。
- 开工时按任务读取相关主线的**最新日期记录、当批决定和 Brief**；开头快照可能过时，实现状态还需核对代码、提交和审查证据。旧 S0/S1/S2/FA、16G 计划及旧状态简报按需追溯，不作为默认执行入口。

## 主要代码目录

| 路径 | 用途 |
| --- | --- |
| `rh2/src/repoharness2/` | 当前主实现：`adapters/miles/` 训练接线与 loss；`adapters/slime/` harness 编排与捕获；`envpack/`、`taskset/` 任务输入；`grading/` 评分；`contracts/`、`governance/` 契约与准入；`shutdown/`、`training/` 关停与训练辅助。 |
| `rh2/src/slime/` | vendored slime agent 层，按现有 pin/集成约定维护，不混作 RH2 自有实现。 |
| `reference/miles-rh2-integration/` | 实际接入的 miles fork；窄改动及 patch 存档按 `docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/` 的集成约定维护。 |
| `rh2/tests/` | 当前测试；从 `rh2/` 执行与改动相关的检查，具体命令和集成树要求看当批 Brief。 |
| `rh2/experiments/`、`rh2/scripts/` | 实验、诊断与运行脚本；以当前作业方案选入口。 |
| `reference/` | 其它外部参考库与 harness 源码；按需查阅，不默认修改。 |
| `src/repo_harness/`、根目录 `tests/` | 冻结的 legacy 实现与旧测试，新功能放在 `rh2/`。 |

## 外部资料与精读

- 资料总入口：[external_paper_references/README.md](docs/harness_improve/external_paper_references/README.md)。
- 逐篇精读正文：[reading_notes/](docs/harness_improve/external_paper_references/reading_notes/README.md)；来源目录：[SOURCE_CATALOG.md](docs/harness_improve/external_paper_references/reading_notes/SOURCE_CATALOG.md)；自查与审查记录位于 `reading_notes/reviews/`。
- 先检索已有精读，再按需核对原文和参考代码。来源版本、作者自查、独立审查、运行复现分别看各篇记录，不以索引旧总数判断完成情况；论文主张和外部模型建议不自动成为项目决定。

## 必要协作规则

- 文档、注释与解释使用清晰中文，保留必要术语和代码标识符；发现用户假设或旧结论有误，给出具体依据。
- 默认用户负责关键决策，Claude 实现，Codex 独立审查与设计建议；具体分工服从当前任务授权。
- 决策与实现按[协作协议](docs/agentic_RL/repo_harness_rh2_workstreams/collaboration-protocol.md)，审查按[审查标准](docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md)。训练语义、公共契约、安全边界等 T0 变更实施前由用户决定；已有授权不重复请示，不新增授权闸门。
- A/B 共用工作区时，明确共享文件的修改归属；不覆盖他人未提交改动，提交只包含本任务路径。写入留言板不等于已通知对方。
- 报告区分建议、已决定、已实施与已验证；验证范围与成本匹配。运行产物使用明确路径，历史 evidence 不回写；凭据和本机私有路径不写入提交文档。

## 面向用户的 HTML 汇报

用户要求 HTML 时，先确定这页要帮助他理解或验收什么，再组织内容。默认遵循以下原则；具体展示范围服从当次要求。

- **按读者的问题组织，不照搬 Markdown。** 不按原文章节逐字转换，不把讨论史、审查编号、采纳记录堆进正文。规则页回答“遇到什么 → 怎么处理 → 怎样验收 → 哪些不能直接做”；只呈现当前有效规则，来源和历史另给链接。
- **首屏先给结论和必要行动。** 说明本页范围、当前状态、关键限制、是否需要用户决定。无需决定就明确写出；已有授权不包装成新的审批。不要用大段背景、技术目录或装饰占满首屏。
- **分层阅读，不以压缩语言代替取舍。** 概览 → 用户选中的规则或题目 → 证据。主视图默认以一至两屏能掌握主结论为目标，细节按需展开或分主题查看；不是硬字数上限，不为缩短页面删掉决定性条件，也不把整篇长文原样藏进折叠块。影响结论的风险、未完成项必须直接可见。
- **批次页逐题可验收。** 每题能找到“目标／问题、实际处理、验证结果、当前用途、剩余事项”；可用简短总表导航，点开再看前后变化和证据。修法建议、已改未验、验证完成要区分；不能只展示成功题或用总通过数代替逐题情况。题目多时提供搜索或筛选。
- **自然语言优先。** 使用完整、简短的句子和有意义的标题；编号、路径、哈希作为次级索引。必要术语首次解释，不让用户背代码表，也不缩小字体、铺超宽表格或连用缩写来塞内容。
- **证据够用且可追溯。** 结论旁给最少必要证据和适用版本，原日志、长推导、失败尝试留链接。数字注明分母与范围；跨线程汇总说明依据日期、题目重叠关系与作者自测／独立验收状态，阶段数量不能直接相加。规则已授权不等于代码已实现，环境验证通过不等于训练资格。不要把历史判断静默改成当前事实。
- **维护一个当前阅读入口。** 更新时按有效现状重写相关部分，避免每轮追加重复总结；历史材料保留原件。页面标明依据与整理日期。旧全文生成器不得再覆盖人工整理的验收页；原规则、逐题记录仍是事实来源。
- **交付前真的看页面。** 检查默认视图是否能直接回答用户问题、点开一题是否能完成验收；在浏览器核对桌面与窄屏、链接、筛选／切换、折叠和键盘操作。默认用轻量、可离线打开的 HTML，不为简单汇报引入应用框架或无关交互。
