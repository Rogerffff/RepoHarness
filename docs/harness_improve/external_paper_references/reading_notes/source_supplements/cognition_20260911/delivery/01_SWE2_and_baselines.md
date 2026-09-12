# 01_SWE2_and_baselines：来源补充附件

采集于 2026-09-11。请先读对应原文，再用这些附件补充图表、公式和交互示例。它们不构成精读结论，也不代表训练复现。阅读应覆盖完整正文、附录和图表，不要只围绕资料补缺项作答。

## 阅读入口

### Introducing SWE-2: Pushing the Pareto Frontier | Cognition

原始网页：https://cognition.com/blog/swe-2

- [swe-2/reading_text.md](swe-2/reading_text.md)：网页提取正文。
- [swe-2/visual_supplement.pdf](swe-2/visual_supplement.pdf)：图表截图 PDF；逐页文件映射见 [swe-2/VISUAL_INDEX.md](swe-2/VISUAL_INDEX.md)。
- `swe-2/states/`：交互状态截图与文本。
- `swe-2/embedded/`：官网脚本中的完整示例；先看 manifest.json。
- `public_data/data/swe-2/`：官网公开 JSON 原文件。

- [opo_2505.23585v2.pdf](papers/opo_2505.23585v2.pdf)：原始论文 PDF；同名 TXT 是布局文本提取。
- [greensmith_2004.pdf](papers/greensmith_2004.pdf)：原始论文 PDF；同名 TXT 是布局文本提取。
- [kool_2019_POSTER_ONLY.pdf](papers/kool_2019_POSTER_ONLY.pdf)：**仅作者海报，不能代替全文。**

## SWE-2 特别说明

优先读 public_data/data/swe-2/figures.json（KL、接受率、散点）与 trajectories.json（12 条网页展示轨迹）。坐标只有相对刻度时，不能把内部坐标当作实际训练 step。
基线来源的唯一未补齐项是 Kool et al. 2019 全文：OpenReview 验证未通过，作者 Drive 链接失效。POSTER_ONLY 是作者海报。OPO 与 Greensmith 全文可读。

## 使用边界

截图 PDF 是本次制作的视觉附件，不是作者发布的 PDF。网页公开的展示轨迹不等于完整训练日志。来源没有披露的训练配方和数值，不得由示意图或脚本变量名推断成事实。
本地完整 HTML/MHTML 底稿单独保留；本 ZIP 优先携带 Pro 可直接阅读的 Markdown、JSON、PDF 与图像。
