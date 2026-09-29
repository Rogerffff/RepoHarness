# Online-fixing 与反馈训练专题入口

2026-09-16：核对 *Extrapolative Weight Averaging Reveals Correctness–Efficiency Frontiers in Code RL*（2605.28751v1）的 §2、§4.2、Appendix G，并比较 RLEF、SCoRe、SDPO、OPSD 和 KAT 的相关机制。

正式维护入口：[阅读库专题](../docs/harness_improve/external_paper_references/reading_notes/online_fixing_2605.28751_and_feedback_training_20260916.md)。本稿只保留导航，避免重复维护。

核心结论：online-fixing 可继续采用 GRPO；反馈进入 actor 的修复题、进入教师的自蒸馏、以及是否训练整条多轮轨迹应分开。原论文提供探索性证据，未验证真实 SWE；Figure 30 存在图例/曲线冲突。项目建议尚待真实任务的配对成本与学习实验，未改训练代码。
