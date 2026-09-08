# 2026-09-08 任务09：Real-World Code Repair 阅读入口

本文件只登记本轮任务，不重排其他并行任务或覆盖历史批次状态。

| 项目 | 状态／入口 |
| --- | --- |
| 论文 | *Agentic Reinforcement Learning for Real-World Code Repair*，LinkedIn，arXiv `2510.22075v1`，2025-10-24 |
| 正文 | [环境、数据、训练、迁移与证据边界](agentic_rl_real_world_code_repair_2510.22075.md) |
| 检查 | [作者自查与实际访问缺口](reviews/task09_real_world_code_repair_self_check_20260908.md) |
| 阅读状态 | 正文与Appendix A.1–A.3文字精读、分析、自查已完成；编号图表原图目视待补 |
| 审查／复现 | 无独立reviewer；未运行训练或配套实现 |
| 写入分支 | `research/real-world-code-repair-20260908` |
| 分支基线 | `miles-migration@d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5` |
| 本次变更 | 三个新增Markdown文件，不改训练代码、共享索引、历史笔记或其他任务分支 |

## 快速阅读

看迁移归因，先读正文§3、§6、§10。看数据和资源，读§4–5、§8–9。看reward hacking，读§7。完整转录的图中分数位于§6.2，必须保留“待目视复核”的限定。

## 与此前任务说明相比最重要的增量

论文不是只在两个等价harness之间切换：简化时还改变外层工作流、预算、任务展开／筛选和LLM judge。其负结果支持必须验证训练—部署迁移，却不能单独识别哪项改变造成失败。7–20pp是简化流程内validation/test分别相对原始Qwen的近似改善；3K-step的65%与删除验证代码相关，不可当作正向模型成绩。各结论的位置和限定见正文。

## 待汇总者处理

将本篇作为新增来源登记，但不要抢占旧文献编号，也不要把本轮任务09与历史M2/Forge任务09混淆。共享README的既有计数不由本线程修订。后续拿到PDF图页时优先核p.5–6和p.10–12，再补p.3流程图；所有缺口与已完成范围见自查记录。

原文：[摘要／版本历史](https://arxiv.org/abs/2510.22075)、[v1 HTML](https://arxiv.org/html/2510.22075v1)、[v1 PDF](https://arxiv.org/pdf/2510.22075v1)。
