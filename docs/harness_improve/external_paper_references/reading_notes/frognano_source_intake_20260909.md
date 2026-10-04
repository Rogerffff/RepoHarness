# FrogNano：来源登记与获取历史（阻塞已解决）

更新：2026-09-09。**用户已上传官方原始PDF；37页全文、附录A–H、20图4表已完成精读及作者自查。** 正式维护入口为 [FrogNano精读](frognano_technical_report.md)，检查记录为 [作者自查](reviews/frognano_self_check_20260909.md)。尚未独立审查或复现训练，本文不替代正式笔记。

## 1. 分支与原件

- 项目：`Rogerffff/RepoHarness`。
- 独立分支：`research/frognano-20260909`。
- 创建基线：`miles-migration@2a533b1f9b8e7cc8a9aca1a90b8ea1b32afb31f8`。
- 初次来源记录提交：`4e9ab870706fc45d835843481491833741377176`。
- 用户加入PDF的提交：`ed425b2eaaac02911e8d8b20b1610caea710c421`，作为本轮写入基线。
- [仓库原始PDF](../pdfs/frognano_technical_report.pdf)，本轮不修改原文件。
- 只维护本篇、作者检查及此获取记录；不合并到miles-migration，不修改共享README/catalog的完成数量、训练代码或实验定案。

## 2. 来源身份与本次实际校验

| 字段 | 已核内容 |
| --- | --- |
| 正式标题 | FrogNano: Training a 4B Coding Agent via Online Task Synthesis |
| 团队 | Microsoft Research Montréal — Froggy Team |
| 官方网页登记日期 | 2026-09-07 |
| 官方PDF | https://microsoft.github.io/debug-gym/static/papers/frognano_technical_report.pdf |
| 官方托管提交 | `microsoft/debug-gym@6c8cea40a507c8e9dac0439c270c3c5a3ce8a4dc`，gh-page |
| 官方文件路径 | `docs/static/papers/frognano_technical_report.pdf` |
| 官方blob与本地计算结果 | 均为`c7ac442cdeb49cd4f0cd15793649b05234abcb55` |
| 实际附件大小／页数 | 2,753,933 bytes／37页 |
| PDF生成metadata | 2026-09-07 19:41:50Z |

标题和登记日期来自[官方页面源数据][metadata]。文件身份先由[官方目录][contents]取得；本轮已用用户上传的真实bytes验证，与固定官方原件一致，不再只有远程元数据。

## 3. 首轮获取历史（保留，不代表当前仍阻塞）

2026-09-09首次处理时，官方GitHub Pages、固定raw PDF和同名arXiv候选均未成功返回可读正文；GitHub text/blob工具不支持该PDF二进制，base64读取返回空content；容器直接下载发生DNS失败。官方Pages构建曾成功，但其artifact已expired，因此没有下载、重跑或修改微软工作流。

当时仅建立来源记录和阅读问题，没有用团队简介、其他论文或社交媒体补写方法与分数。导航候选`2609.07925`当时未确认与用户PDF的内容／版本关系，本轮也未用它替代固定原件。

**解除方式：用户将PDF提交到本分支并上传当前会话。** 本轮直接读取已挂载附件，提取全部文字并渲染图页；没有重新依赖失败的网络下载。原件获取障碍已解决，后续可从本库PDF按页复查。

## 4. 正式精读已回答什么

正文覆盖主RL阶段、任务生成器与当前policy角色、Leaf协议、五轮task calibration、raw/shaped reward与DPPO公式、硬件与预算、四项评测、独立ranker、SFT consolidation、自摘要、行为漂移、完整hack rubric和输入实例。

重要边界也已落文：online为分轮交替；generator可用强模型但不提供主策略模仿目标；Verified为validation；第五轮同时改变多个变量；没有完整TaskPilot资产和总成本。正文与附录的公式、分数、compaction及hack表述冲突分别记录，不擅自取最好值或补成统一配方。

因此，正式稿中的“未披露”现在指**完整固定PDF及已说明资产检查中没有相应信息**，与首轮“没有取得原文”是两种不同状态。

## 5. 后续维护

正式来源以[frognano_technical_report.md](frognano_technical_report.md)为准，未来独立复查或作者勘误在正文和检查记录追加。此文只保留来源身份与获取历史。读完论文不等于批准动态课程、harness改造或新loss，也不等于论文实验已被本项目复现。

[metadata]: https://github.com/microsoft/debug-gym/blob/6c8cea40a507c8e9dac0439c270c3c5a3ce8a4dc/docs/_data/papers.yml
[contents]: https://api.github.com/repos/microsoft/debug-gym/contents/docs/static/papers?ref=6c8cea40a507c8e9dac0439c270c3c5a3ce8a4dc
