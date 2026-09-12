# Cognition / SpecForge 精读资料补充包

采集日期：2026-09-11。用途：补足外部 Pro 无法读取的网页图表、图片公式、折叠示例和论文文件。**这是来源采集包，不是新一轮精读报告，也没有验证论文结论或运行训练复现。**

## 交给 Pro 的方式

打开 [delivery/](delivery/)，按对应任务上传 ZIP。ZIP 内的 `TASK_README.md` 是各任务入口。若对话环境不能解压 ZIP，请在本地解压，上传其中的 Markdown、JSON 和 PDF；不必上传原始网页脚本。

每篇网页均提供：

- `reading_text.md`：直接提取的正文，保留网页数学公式的 TeX；可能包含导航或相关推荐残余，不是改写后的摘要。
- `visual_supplement.pdf` 与 `VISUAL_INDEX.md`：带来源链接的图表截图合集、截图文件映射。PDF 是本次排版的视觉附件，不是作者发布的论文 PDF。
- `states/`：展开项、切换任务、播放结束等状态的截图和文字。**滚动框截图不能代表完整内容**，应结合下面的完整数据。
- `embedded/*.json`：从官网公开 JavaScript 的静态数组提取的结构化示例；同目录保留原始片段与字符偏移位置。不执行下载脚本。这里的 JSON 是解析产物，不是另行发现的官方数据 API。
- `public_data/`：官网直接发布的 JSON，保留原文件。链接见 [public_data_manifest.json](public_data_manifest.json)。这些是网页图表/展示数据，不应称作完整训练日志或公开训练数据集。

远程提供分组 ZIP，以及可直接阅读的正文、PDF、图片、交互状态和相关原始数据。完整 HTML/MHTML 网页快照、截图检查临时文件和重复的整包 ZIP 只保留在本地；相关官方脚本片段与原始图片随可读资料上传。MHTML 是采集时的页面快照，不承诺离线后还能继续切换所有交互；已捕获状态的截图与完整示例数据才是补充证据。

## 六组交付内容

| 包 | 主要补齐内容 | 仍需注意 |
| --- | --- | --- |
| 01 SWE-2 与基线参考 | 正文和附录 A/B/C、TeX、Pareto 图、梯度范数散点、KL 与接受率曲线、三种工具行为统计、三个任务的展示状态；官网 12 条轨迹记录和图表 JSON；OPO、Greensmith 论文 | 只有相对刻度的坐标不能还原真实训练 step；网页示例不能当成完整运行日志；Kool 2019 全文仍缺，只有作者海报 |
| 02 SWE-1.7 / 1.6 Preview / 1.5 | 三篇正文与图表；1.7 的 entropy/KL 原始 SVG、三个 CoT 示例与三个轨迹示例的完整静态数据 | `swe2` 是 1.7 网页脚本中的内部字段名，不能据此把该栏误认成 SWE-2；具体模型名以页面展示为准 |
| 03 FrontierCode / 1.1 | 两篇正文；示例 prompt 对照；两套 patch（每套 8 个文件）和各 10 项 rubric 结果；完整 fair-internet-use prompt；两种联网行为示例共 26 个展示步骤及播放完成截图 | `Run eval` 是网页用定时器播放的预置示例，本次没有运行评测；所有 rubric 和 patch 应读 JSON，截图只是视觉补充 |
| 04 DSpark | `2607.05147v1` 原始 PDF（33 页）与布局文本 | 本次确认文件标题、页数与末页可解析，未逐图开展科学内容审查；未采集代码与 TeX 源包 |
| 05 SpecForge | 论文 v1 PDF（16 页）；v0.3 官方文章、7 幅图及原始资源；代码快照和 README | 快照为采集时 `main`，不是声称找到了论文实验提交或 v0.3 发布提交 |
| 06 SWE-Check / SWE-grep | 两篇正文；Check 的 4 张公式图；grep 的重要性权重与 loss 公式图；全部正文图片及去掉 CDN 缩放参数后的原始图片 | GIF 的截图只代表一个状态，原始 GIF 已保留；图片公式应看原图，不要靠普通正文提取猜符号 |

## 高价值直接来源链接

这些公开接口可以先交给 Pro 尝试直接读取，即使它打不开完整网页也可能可以读取 JSON 或静态图片。

- [SWE-2 原文](https://cognition.com/blog/swe-2)
- [SWE-2 图表 JSON：KL / speculative acceptance / scatter](https://cognition.com/data/swe-2/figures.json)
- [SWE-2 展示轨迹 JSON：12 条记录](https://cognition.com/data/swe-2/trajectories.json)
- [SWE-2 FrontierCode 图表数据](https://cognition.com/data/swe-2/data.json)、[DeepSWE 图表数据](https://cognition.com/data/swe-2/deepswe.json)
- [SWE-1.7 entropy 原图](https://cognition.com/images/swe-1-7/policy-entropy.svg)、[train/inference mismatch 原图](https://cognition.com/images/swe-1-7/train-infer-mismatch.svg)
- [FrontierCode 原文](https://cognition.com/blog/frontier-code)、[FrontierCode 1.1 原文](https://cognition.com/blog/frontier-code-1.1)
- [SpecForge v0.3 原文](https://www.lmsys.org/blog/2026-08-04-specforge-v0-3)
- [DSpark v1 PDF](https://arxiv.org/pdf/2607.05147v1)、[SpecForge PDF](https://arxiv.org/pdf/2603.18567)、[OPO v2 PDF](https://arxiv.org/pdf/2505.23585v2)、[Greensmith 2004 PDF](https://jmlr.org/papers/volume5/greensmith04a/greensmith04a.pdf)

## 尚未补齐的明确缺口

1. **Kool et al. 2019 全文**：OpenReview 链接返回浏览器验证/HTTP 403；[作者主页](https://wouterkool.github.io/publication/buy-4-samples-free-baseline/)所链接的 Google Drive 全文地址返回 404。[作者海报](https://wouterkool.github.io/pdf/poster-buy-4-samples-free-baseline.pdf)已取得，但它只有 1 页，**不能代替全文**。因此未绕过验证，也未把其他引用该论文的文档当作该论文。
2. **网页没有披露的材料**仍然没有：完整训练日志、未公开实现、逐样本训练数据、图表隐藏的实际横轴单位等，不能由本次截图补出。
3. **没有承诺穷举每个 hover 与每一种排行榜组合**。已保存核心图表、明确缺失的展开示例与公开数据，其他视觉状态仍可回到原网页检查。
4. 本次没有展开全部延伸引用链；Kevin-32B、Devin Fusion 等不属于附件明确要求补缺的优先项。DSpark / OPO 未额外克隆代码。

## 已做的检查

- 网页正文、标题、附录入口、展开控件和图片清单已保存；重点公式与 KL / acceptance 图经过视觉查看，图例与图注随截图保留。
- 原始论文 PDF 已核对标题、页数、末页可提取文字；海报显式命名 `POSTER_ONLY`。详见 [papers/validation.json](papers/validation.json)。
- FrontierCode 静态数据包含 2 套各 8 文件的 patch、10 项 rubric，以及 1.1 的 14 / 12 步行为示例；1.7 的 CoT 和轨迹示例各 3 个。
- 图表动画曾导致首次截图未显示全部柱条；最终工具行为截图已等待图形稳定后重新采集，四个模型/effort 行均已显示。
- 不把截图过程当作“独立精读审查通过”。Pro 仍需完整阅读正文、附录、图表，注明来源披露边界。

本包保留来源署名与链接，供本项目的精读与核查使用。2026-09-12 按用户要求同步到 `miles-migration` 分支；全量网页缓存和检查临时文件留在本地。
