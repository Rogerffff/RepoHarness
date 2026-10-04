# 云端 Pro 阅读入口：环境流水线与外部 Agentic RL 代码

整理日期：2026-10-04。用途：带用户理解设计、核对论文和源码，并讨论下一步；不是实施授权或训练版本发布。

## 先掌握项目当前状态

主链是 miles + SGLang + Claude Code + RH2。用户希望把稳定的环境准备前移，通过托管沙箱扩大 actor/grader 容量，减少 GPU 等待，再研究长短任务混合。

建议按下面顺序读，不必先通读全部历史记录：

1. [A 线当前状态](../a_line_status.md)：代码、交付包、正式接线和验证边界。
2. [评分优化 next_v2 与最新独立复核](../grading_performance_next_20261004/codex_fix_review_20261004.md)，配合[该批 README](../grading_performance_next_20261004/README.md)：L1 Git 模板、L2 编译缓存、Prime 评分资格与未接线事项。
3. [Codex 环境流水线建议](pipeline_proposal.md)：提前构建、有限就绪队列、生成与评分容量分离，以及维持训练样本组成。
4. [Claude 环境分析](claude_env_pipeline_analysis_20261004.md)：52 题开销、角色模板、Prime 拓扑、网络、计时和待讨论选项。
5. [外部调查与源码调用链](README.md)：每个公开仓库覆盖什么，以及哪些论文机制并未公开完整实现。
6. 有争议再查 [A 线记录](../infra.md)、[B 线记录](../env_data_eval.md)和[环境流程](../environment_pipeline.md)。

Claude 文档的优化后耗时是投影；其中建议、预算和 D1–D8 不因本次提交而自动获批。请把作者分析、独立复核、真实运行结果分开。52 题探针是特定版本的串行诊断，不等同于并发训练结果。

本次只提交阅读材料和外部源码。共享工作区尚未提交的 RH2 实现没有混入；这些文档可能讨论冻结版本、交付补丁和本地工作树，不应把远程 RH2 源码 HEAD 当作它们已经全部集成的证据。原始日志、任务镜像、凭据和本地运行目录也没有整体上传。

## 从代码中读懂 MiMo 三层分工

[固定版本源码总入口](../../../../../reference/external_rl_infra_20261004/README.md)包含可直接浏览的普通文件，克隆本仓库即可阅读，不需要初始化新增子模块。

1. **verl：训练与 rollout 编排。** 先读 [Code runner](../../../../../reference/external_rl_infra_20261004/XiaomiMiMo__verl/recipes/code/mimoagent_runner.py)，再读 [训练配置](../../../../../reference/external_rl_infra_20261004/XiaomiMiMo__verl/recipes/code/config/train.yaml)。追踪任务输入、session、reward 和回传。
2. **mimoagent：agent、环境与评分。** 先读[环境工厂](../../../../../reference/external_rl_infra_20261004/XiaomiMiMo__mimoagent/src/mimoagent/environments/utils.py)，再读 [OpenSourceCodeEnvironment](../../../../../reference/external_rl_infra_20261004/XiaomiMiMo__mimoagent/src/mimoagent/environments/datasets/opensource_code.py)。确认哪些工作在镜像构建时完成、哪些发生在运行时，评分继承什么状态。
3. **uni-agent：session、模型网关和轨迹运输。** 先读 [framework](../../../../../reference/external_rl_infra_20261004/XiaomiMiMo__uni-agent/uni_agent/framework/framework.py)，再读 [session](../../../../../reference/external_rl_infra_20261004/XiaomiMiMo__uni-agent/uni_agent/gateway/session/session.py)。追踪请求路由、正常结束、abort 和训练数据交付。
4. **AgentENV：环境服务。** 从[模板构建说明](../../../../../reference/external_rl_infra_20261004/kvcache-ai__AgentENV/docs/src/concepts/templates/creating.md)和[架构](../../../../../reference/external_rl_infra_20261004/kvcache-ai__AgentENV/docs/src/internals/architecture.md)开始。区分镜像准备、文件快照、进程恢复和 actor 状态隔离。

这些是阅读快照，不是已经安装并可运行的集成。MiMo 两个配套仓库按所选 verl 的 gitlink 固定版本，放在并列目录；其他嵌套子模块未展开，具体记录见源码 manifest。

## 对照论文与本地精读

- MiMo：[官方 PDF 副本](papers/MiMo_V2_6_technical_report.pdf)与[已有全文精读](../../../../harness_improve/external_paper_references/reading_notes/mimo_v2_6_technical_report.md)。重点看 Sample Mixer 如何区分目标组成和生成资源分配，不把报告生产系统等同于公开 recipe。
- DeepSeek DSec：[官方 PDF 副本](papers/DSec_2609.22978v1.pdf)与[本批调查](README.md)。重点看 GPU 池之外的状态所有权、环境分层和提前构建。
- DeepSeek V4.1：[已有精读](../../../../harness_improve/external_paper_references/reading_notes/R6c_deepseek_v41_flash.md)。注意该笔记所用来源版本，不能用 DSec PDF 代替它。
- Qwen：[Qwen3-Coder-Next 精读](../../../../harness_improve/external_paper_references/reading_notes/R3_qwen3_coder_next.md)。重点看环境、rollout、评测的阶段边界。
- Kimi：[K3 精读](../../../../harness_improve/external_paper_references/reading_notes/R13_kimi_k3.md)。区分环境恢复能力和训练轨迹、权重版本恢复。
- 扩展：[MiniMax Forge](../../../../harness_improve/external_paper_references/reading_notes/N10_minimax_forge.md)、[Polar](../../../../harness_improve/external_paper_references/reading_notes/R0_polar.md)、[SkyRL-Agent](../../../../harness_improve/external_paper_references/reading_notes/O01_skyrl_agent_sa_swe.md)。

本次同步了 reading_notes 顶层 Markdown 与文字审查记录；各篇引用的 sources/ 原始资料和其他 runs/ 证据没有全部上传。链接不可用时优先使用论文官方链接，不把缺少原件解读成已完成复现。

## Claude 的开销分析材料

[统计报告](cloud_evidence/report.md)、[逐次数据](cloud_evidence/per_attempt.json)、[逐题数据](cloud_evidence/per_task.json)、[汇总](cloud_evidence/summary.json)和[分析脚本](cloud_evidence/analyze_env_costs.py)是原 runs/env_pipeline_analysis_20261004/ 的逐字节副本。原始 GPU 日志未上传，因此云端可检查统计口径与派生数据，不能仅凭这些副本重做全部日志抽取。

[材料来源与哈希](cloud_materials_manifest.json)记录副本身份；[源码 manifest](../../../../../reference/external_rl_infra_20261004/manifest.json)记录上游提交及每个文件摘要。

## 可直接交给 Pro 的任务

> 请先按本页顺序掌握现状，再带我逐层读 MiMo 的 verl、mimoagent、uni-agent 调用链，用 AgentENV、DSec、Qwen、Kimi 对照环境准备和调度。每一层回答：输入是什么，何时创建环境，谁拥有状态，何时释放，失败怎么恢复，以及 GPU 为什么可能等待。将论文主张、源码事实、项目实验、设计建议分别标明。重点讨论提前模板、就绪队列、远端 actor、独立 grader 与样本组成；不要把讨论当成实现授权，也不要因为看到同容器评分就推定它满足 RH2 的 FrozenPatch 边界。
