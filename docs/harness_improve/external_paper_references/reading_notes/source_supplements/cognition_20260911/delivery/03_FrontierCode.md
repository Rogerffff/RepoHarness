# 03_FrontierCode：来源补充附件

采集于 2026-09-11。请先读对应原文，再用这些附件补充图表、公式和交互示例。它们不构成精读结论，也不代表训练复现。阅读应覆盖完整正文、附录和图表，不要只围绕资料补缺项作答。

## 阅读入口

### Introducing FrontierCode | Cognition

原始网页：https://cognition.com/blog/frontier-code

- [frontier-code/reading_text.md](frontier-code/reading_text.md)：网页提取正文。
- [frontier-code/visual_supplement.pdf](frontier-code/visual_supplement.pdf)：图表截图 PDF；逐页文件映射见 [frontier-code/VISUAL_INDEX.md](frontier-code/VISUAL_INDEX.md)。
- `frontier-code/states/`：交互状态截图与文本。
- `frontier-code/embedded/`：官网脚本中的完整示例；先看 manifest.json。
- `public_data/data/frontier-code/`：官网公开 JSON 原文件。

### FrontierCode 1.1 | Cognition

原始网页：https://cognition.com/blog/frontier-code-1.1

- [frontier-code-1.1/reading_text.md](frontier-code-1.1/reading_text.md)：网页提取正文。
- [frontier-code-1.1/visual_supplement.pdf](frontier-code-1.1/visual_supplement.pdf)：图表截图 PDF；逐页文件映射见 [frontier-code-1.1/VISUAL_INDEX.md](frontier-code-1.1/VISUAL_INDEX.md)。
- `frontier-code-1.1/states/`：交互状态截图与文本。
- `frontier-code-1.1/embedded/`：官网脚本中的完整示例；先看 manifest.json。
- `public_data/data/frontier-code-1.1/`：官网公开 JSON 原文件。


## 交互示例入口

FrontierCode：embedded/array-576.json 是 10 项 rubric；array-2002.json 是两模型的 patch 与评分，每模型 8 个文件、10 项结果。
FrontierCode 1.1：states/fair-internet-use-prompt.txt 是完整展开提示；embedded/array-2876.json 包含 14 步 flagged 示例与 12 步 allowed 示例。
Run eval 是网页播放预置数据的动画，本次没有运行真实评测。截图中的滚动框只显示部分内容，完整 patch / 步骤请看 JSON。

## 使用边界

截图 PDF 是本次制作的视觉附件，不是作者发布的 PDF。网页公开的展示轨迹不等于完整训练日志。来源没有披露的训练配方和数值，不得由示意图或脚本变量名推断成事实。
本地完整 HTML/MHTML 底稿单独保留；本 ZIP 优先携带 Pro 可直接阅读的 Markdown、JSON、PDF 与图像。
