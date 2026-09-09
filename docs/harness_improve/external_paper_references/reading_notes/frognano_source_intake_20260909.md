# FrogNano：来源登记与精读阻塞记录（尚未精读）

日期：2026-09-09。**状态：已确认官方来源、已建立独立分支；PDF 正文尚未取得，不计入精读完成数量。** 本文不是论文摘要，也不是正式精读稿。没有据社交媒体、同团队旧文或框架默认值补写训练方法和实验结果。

## 1. 分支与写入边界

- 项目：`Rogerffff/RepoHarness`。
- 本任务独立分支：`research/frognano-20260909`。
- 创建基线：`miles-migration@2a533b1f9b8e7cc8a9aca1a90b8ea1b32afb31f8`。
- 本轮只新增此来源记录，不修改共享 README、SOURCE_CATALOG、完成数量、训练代码、数据集或实验定案；没有合并到 miles-migration。
- 后续正式精读沿用同目录 `NOTE_TEMPLATE.md`，建议独立文件名 `frognano_technical_report.md`，但只有真正取得并阅读原文后才创建正式正文与覆盖表。

## 2. 已由官方材料确认的事实

微软团队网页源文件 [`docs/_data/papers.yml`][metadata] 直接登记：

| 字段 | 已核内容 |
| --- | --- |
| 正式标题 | FrogNano: Training a 4B Coding Agent via Online Task Synthesis |
| 团队主页 | Microsoft Research Montréal — The Froggy Team |
| 官方网页登记日期 | 2026-09-07；不能将社交媒体转发日期替代它 |
| 用户指定 PDF | https://microsoft.github.io/debug-gym/static/papers/frognano_technical_report.pdf |
| 托管仓库与分支 | `microsoft/debug-gym`，`gh-page` |
| 固定源提交 | `6c8cea40a507c8e9dac0439c270c3c5a3ce8a4dc` |
| 固定文件路径 | `docs/static/papers/frognano_technical_report.pdf` |
| GitHub blob SHA | `c7ac442cdeb49cd4f0cd15793649b05234abcb55` |
| GitHub 返回的文件大小 | 2,753,933 bytes |

上表版本和大小来自 [GitHub 目录元数据][contents]，不是本地下载后的文件校验结果。

官方网页的一小段介绍称：FrogNano 是 4B coding agent，在合成软件工程任务上仅以 RL 做后训练；任务随 agent 能力变化而调整，目标是在不使用更大模型传统蒸馏的情况下取得有竞争力的表现。[metadata]

**这仅是官方简介的范围。** 当前不能据此填入具体底座、训练算法、任务数量、合成器、教师身份、预算、harness、分数、消融或算力；也不能把“不使用传统蒸馏”扩展成“任务生产完全不用强模型”。这些都是原文待核内容。

## 3. 实际获取状态

| 入口 | 本轮结果 | 对阅读状态的影响 |
| --- | --- | --- |
| 用户指定 Microsoft GitHub Pages PDF | 网页抓取返回 cache miss；下载工具失败 | 未取得正文和图页 |
| 固定提交 raw PDF / GitHub 文件页 | 网页抓取失败 | 只确认文件存在，未读内容 |
| GitHub 文件读取 | 对该大 PDF 的 base64 请求返回空 content；blob/通用读取拒绝二进制 UTF-8 解码 | 不将空结果当成有效 PDF |
| 本地直接下载 | 当前容器域名解析失败 | 没有本地 PDF 可供提取或渲染 |
| 官方 Pages 构建产物 | 成功构建 run `34158005796`；`github-pages` artifact `10031626965` 已标 expired | 未下载；未重跑或修改微软工作流 |
| 同名 arXiv 导航候选 `2609.07925` | 搜索发现候选，原始 abs/PDF/HTML 仍未成功读取 | 未确认其与用户 PDF 的内容/版本关系，不作为原文替代证据 |

没有获得可用 PDF 文档，因此没有完成 PDF 截图、正文/附录阅读、公式校验、图表复核或配套训练代码追查。本轮也没有独立 reviewer、模型训练或环境复现。

这是一项**资料获取阻塞**，不是“论文未披露方法”，更不是该论文证据不可靠的判断。需要用户上传原 PDF，或本地线程提供可直接读取的原始文件；不需要重新讨论选题才能继续。

## 4. 取得原文后的阅读重点（问题，不是结论）

首先根据原文真实目录建立覆盖表，完整阅读全部正文、技术附录、表图与脚注，不把下面的问题当成删减范围的依据。

1. **训练阶段与角色。** 输入模型是什么？是否确实无新增 SFT/轨迹蒸馏阶段？任务生成器、任务校准 solver、训练 policy 与 verifier 分别是谁？有无特权信息或不同大小模型参与？
2. **Online task synthesis 的准确含义。** 是分轮重新生成、持续与 learner 并行，还是周期性重新筛选？怎样触发刷新、定义可学习区、估计成功概率？有无静态同量任务、普通扩容、重复采样或简单分层基线？
3. **SWE 任务与环境资产。** 仓库从何而来、环境怎样复用、任务/测试/修复如何共同构建？候选数、筛选后任务数、环境数、rollout 数和实际训练消费量分别是多少？
4. **评分有效性与可见性。** gold/no-op/重复运行与合法替代解如何验证？模型能看到哪些测试、git 历史和参考材料？超时、工具错误、环境错误怎样影响 reward、采样组与梯度？
5. **RL 与系统实现。** 依照原文恢复 reward、advantage、样本单位、loss 分母、mask、KL、行为策略和更新时序；不从 debug-gym 或其他微软项目推定训练后端、fully async 或特定优化器。
6. **评测与完整成本。** 任务切分、仓库重叠、harness、推理预算、重复次数和 checkpoint 选择如何规定？合成、校准、环境构建、训练与评测分别花费多少？能否把收益归于 online synthesis，而不是更多计算或不同任务分布？
7. **对项目 A/B 线程的条件化映射。** 先整理作者事实和限制；文末再分别讨论训练消费/系统边界，以及数据/环境/评分的借鉴。不得将论文阅读自动转成动态课程实施批准。

## 5. 后续维护

取得源文件后，从本记录的固定版本继续，不必重复搜索同一个官方网站。完整精读稿应注明实际使用的 PDF 是否与上表相同；若只能取得另一个版本，保留版本差异，不静默替换。

正式稿完成后再补作者自查/独立审查的真实状态和阅读库登记。当前来源记录可以保留为获取历史，但**不能用其存在证明论文已精读**。

[metadata]: https://github.com/microsoft/debug-gym/blob/6c8cea40a507c8e9dac0439c270c3c5a3ce8a4dc/docs/_data/papers.yml
[contents]: https://api.github.com/repos/microsoft/debug-gym/contents/docs/static/papers?ref=6c8cea40a507c8e9dac0439c270c3c5a3ce8a4dc
