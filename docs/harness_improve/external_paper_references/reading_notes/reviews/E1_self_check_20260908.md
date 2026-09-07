# E1 Harness Interplay：作者自查与阅读交付记录

日期：**2026-09-08**。正文：[E1_harness_interplay_posttraining.md](../E1_harness_interplay_posttraining.md)。

**状态：全文及附录文本精读完成，作者自查完成；正文7幅图已目视核对，PDF物理页17–22的图页复核仍有访问缺口；未独立审查、未复现实验。** 当前线程没有独立子agent工具，没有虚构reviewer、线程ID或运行effort。此次只交付E1所属的两份文档，不修改共享索引。

## 1. 来源与继承约定

主来源为 *The Interplay of Harness Design and Post-Training in LLM Agents*，`arXiv:2606.25447v1`，2026-06-24。阅读时的arXiv历史只列v1；正文22页，采用官方[PDF](https://arxiv.org/pdf/2606.25447v1)与[HTML](https://arxiv.org/html/2606.25447v1)。作者/机构与许可来自原文首页及arXiv条目，不来自旧摘要。

项目读取基线：`Rogerffff/RepoHarness@b895451cb7ad50619bf94569976fbb2c7a1ddb5f`，分支`miles-migration`。读了当前简报、笔记模板、E1旧摘要与来源目录，以及用户指定的[O01 Codex质量反馈](15_O01_codex_quality_review_20260907.md)。没有修改O01或重审其代码问题；只把通用写作和并行写入约定应用到本篇。

自查对象是本线程本地的最终两份Markdown草稿；没有另一名独立作者/审查者。本记录描述实际已做和未做的检查，提交SHA由成功写入后的交付回复提供，不提前填写。

## 2. 完整阅读与视觉检查的边界

原文摘要、§1–5、Limitations、Appendix A.1–A.3、B.1–B.2、C、D全部文本均已阅读；参考文献检查来源身份与尾部连续性，没有逐篇扩读被引工作。没有被项目SWE问题清单挤掉的额外后训练分支。

| PDF物理页 | 内容 | 本次实际核查方式 |
| --- | --- | --- |
| 1–3 | 摘要、引言、工具调用/状态重建、研究总览 | 全文；p.2 Fig.1截图成功 |
| 4–5 | Harness、schema、任务与协议，Tables1–3 | 文本和截图成功 |
| 6 | Fig.2 zero-shot、Fig.3 ID训练 | 截图成功，核对象、成功率坐标、整体值和例外 |
| 7 | Fig.4 post-hoc、Fig.5 schema shift、Fig.6错误分解 | 截图成功，核比较方向、百分点/调用比例两种分母 |
| 8 | Table4失败例、Fig.7 task radar、结论 | 截图成功，核ID加粗轴及med/hard两排；无训练时间曲线 |
| 9–13 | Limitations、References、Appendix A | 全文读取，配置数和范围回原文核对 |
| 14–16 | Tables5–8：描述、观测、工具/参数映射 | 截图成功，覆盖13工具与各参数角色 |
| 17 | Table9：13→5聚合 | HTML和PDF提取文本已读；截图失败 |
| 18–19 | Appendix C：MDP、GRPO/GiGPO公式、训练/评测参数 | HTML公式及PDF提取文本对照；截图失败 |
| 20–22 | Tables10–16详细结果与失败注释 | HTML与PDF提取文本读取；截图失败，主图已覆盖部分整体值 |

尝试了versioned及无版本PDF入口、重新打开后截图，以及本地PDF/HTML/TeX下载；尾页截图持续返回cache miss，本地网络下载失败。因此没有写“全部16张表和公式均已目视核验”，也没有将缺图写成“论文未披露”。正文§1、§5、§9及对应表的来源说明保留这个缺口。

正文7幅图和Tables1–8已看，Table9–16虽文本已读，仍建议独立复查优先用本地PDF补看p.17–22。这不是要求重读全部论文才能使用笔记，而是提供具体待核位置。

## 3. 主要核验、修正和限定

| 核查对象 | 来源位置 | 正文处理 |
| --- | --- | --- |
| 训练配置总数 | §4.1、Limitations | 24/model，2模型共48；不把三seed机械变成144次成功训练 |
| 子目标与turn | Table3、Appendix C | 3/4/5/8是最少子目标，50才是episode工具轮数上限 |
| Harness档位是否等信息 | Tables1、5、6 | mid增加可用工具名；high还加描述和持有状态；不是纯格式变换 |
| h-low是否完全无状态 | Table6 | 三档共同有目标、位置、step和raw observation；不沿用“连位置也没有”的理解 |
| Schema是否多步宏工具 | §3.3、Tables7–9 | 13→5入口、离散action选单个原操作；系统提示与验证器同步更新 |
| 算法概率和分母 | Appendix C | current/old/ref分开；token ratio；episode内动作token均值；不填DIS或LOO |
| GiGPO中的h | Appendix C | 是状态识别器，不是harness；语义等价的实现未披露 |
| 参数段的算法范围 | Appendix C Training | 字面GRPO；不宣称GiGPO逐配置参数全确认 |
| Batch两值 | Appendix C | 16×8=128 episode与minibatch256均保留；不猜重组机制 |
| 非单调结果 | Tables10–11、13–16 | 保留3B GiGPO mid>ID high、7B GRPO强shift mid>high、task-shift算法翻转 |
| Post-hoc比较 | Fig.4、Tables11–12 | 八个同测试harness对照逐行复算；不扩大成任意harness变化必须重训 |
| 工具合法率分母 | Fig.6与§4.4 | 34.9是堆叠图全调用类别；正文“of these calls”歧义单列 |
| Task-shift All | Fig.7、Tables14–16 | 包含ID；+17.5/+44.6不是纯OOD分数增益 |
| 训练失败替代值 | Tables15–16表注 | 用ZS†显式标注，不当作成功checkpoint的训练结果 |
| 真正权重迁移 | Table10与16 | 7B GRPO high训练hard后Heat29.1低于同harness base35.9，区分相对低信息训练的提升 |
| 数值不确定性 | Appendix C与Table13 | Table13没有逐格SD，不造误差；其余±按原表为标准差而非CI |

这些多数是防止旧摘要或读者扩大解释，并不是宣称发现了等量的论文错误。源文正文较强的单调表述、图6分母措辞及表13的SD缺失，与确实不成立的旧24总配置计数，分别注明了证据性质。

## 4. 实际执行的草稿检查

检查了Markdown引用式链接定义与首屏锚点、公式分隔符、Unicode替换字符和行尾空格。独立复算配置数、prompt/rollout计数、post-hoc八个差值、schema成功率差值及Fig.6三类比例和；对聚合工具覆盖13种原操作做了集合检查。这些是文档/算术检查，不是策略优化或环境执行复现。

主稿给出三个不同变更轴、GRPO/GiGPO公式、所有整体结果矩阵和关键类别反例；没有把每个数表的全部单元格再机械复制一遍。未给统计显著性、没有拟合规模定律，也没有用“图有趋势”绕过本来可取得的准确表值。

## 5. 没有完成的工作与补查建议

未取得作者关联的专用代码入口或checkpoint，未运行ALFWorld、GPU训练或独立结果复现；未读取TeX；没有对PDF后六页完成视觉复核。正文将未披露、未取得、未检查区分，而不是统一写成unknown。

独立复核可优先处理：p.17的工具聚合；pp.18–19的两算法公式和参数；pp.20–22的例外值、SD及zero-shot替代注。再检查主图Fig.6的分母和正文是否仍有混用。没有必要把这项论文复核扩展成GRPO/GiGPO上游整库审计。

项目映射仅保留两个候选对照：训练时就位与post-hoc的2×2比较，以及等功能schema变化与额外信息的分离诊断。没有批准多harness训练、新算法、自动harness生成器或taskset。

## 6. 并行写入约定

仅写以下两个路径：

```text
docs/harness_improve/external_paper_references/reading_notes/E1_harness_interplay_posttraining.md
docs/harness_improve/external_paper_references/reading_notes/reviews/E1_self_check_20260908.md
```

写入前重新获取远程分支与目标路径；以最新tree为基础只添加这两份文档，以非强制方式更新分支。共享README、SOURCE_CATALOG、批次状态、历史笔记及训练代码不在本线程所有权内。实际远程提交与回读以交付回复为准。
