# SWE judge 与 advantage 重分配：2026-09-17 精读摘要

本轮为 MiMo RL 直播的后续研究。当前项目是 RH2 + miles + SGLang；没有执行训练或修改实现。

[完整分析与建议实验](../docs/harness_improve/external_paper_references/live_reports/mimo_v26_rl_20260917/credit_assignment_followup_20260917/README.md) · [一手资料、版本与检查范围](../docs/harness_improve/external_paper_references/live_reports/mimo_v26_rl_20260917/credit_assignment_followup_20260917/evidence_notes.md)

主要结论：

- **SWE-RM / SWE-TRACE**：最直接的 SWE RL 证据是给完整轨迹更有区分度的评分，再计算组 advantage。不是已证实的动作级 ADV 重写。
- **DRACO / IAPO**：提供轨迹内、按 A 正负分支的权重分配。DRACO 代码明确在 `compute_advantage` 之后改写，但两篇的相关实验不是 SWE。其 token/步骤长度处理也不相同。
- **Agentic Rubrics**：问题级 rubric 与 patch 核查可借鉴，但其证据主要来自候选重排。**PaTR** 用 judge 引导树采样，也不能当作改 ADV 的训练证据。
- **OpenClaw-RL** 有可选 SWE PRM 接线；论文 SWE 曲线与其他域过程奖励消融须分开读。**AEM / RTMC** 提供不用 LLM judge 的对照思路；**OAR** 的数学 token 敏感度方法不能直接算便宜的 SWE judge。
- judge 降低 value-critic 训练的接入负担，不代表同总算力更省。报告包含 DRACO 的评分开销、MiMo 的评分长尾与同预算比较建议。
- **MiMo 只能确认公开了 advantage 行重写等记录，仍不能确认行内动作定位、重写公式及相对组归一化的顺序。**

对本项目的启发是先审计冻结 judge，再分开比较轨迹 reward shaping 和轨迹内乘权；沿用真实捕获 token、现有 loss mask、faithful DIS 与 execution 分母，避免一次改变多个训练语义。具体配方仍是建议。标量 advantage 守恒不等于梯度守恒；同结果组标准化也可能抵消“小 judge reward 系数”。

共保存 14 篇 HTML；11 篇取得同版本 TeX 并核对相关方法/实验；DRACO 与 OpenClaw 资料保存 immutable commit。作者结果未独立复现，静态代码阅读不等于运行验证；IAPO v1 缺少若干被引用附录，限制已记录。
