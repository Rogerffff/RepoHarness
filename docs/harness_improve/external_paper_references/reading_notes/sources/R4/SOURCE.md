# R4 来源附件说明

抓取/检查日期：2026-09-07。此目录服务于任务09，不是训练代码。

| 文件 | 来源与用途 |
|---|---|
| `source.pdf` | 原指定 `pdfs/R4_minimax_m2_series_2605.26494.pdf` 的只读副本，首页确认 arXiv v1，2026-05-26；35页 |
| `source.txt` | `pdftotext -layout source.pdf`；公式/图表以 PDF 和 TeX 为准 |
| `arxiv-v1.tar`、`tex/` | [arXiv v1 TeX](https://arxiv.org/src/2605.26494v1)，原始下载及解包；入口 `tex/main.tex` |
| `source-v2.pdf`、`source-v2.txt` | [arXiv v2 PDF](https://arxiv.org/pdf/2605.26494v2)，2026-07-30；35页，附提取文本 |
| `arxiv-v2.tar`、`tex-v2/` | [arXiv v2 TeX](https://arxiv.org/src/2605.26494v2)，入口 `tex-v2/main.tex` |
| `version-diff.txt` | 两版 PDF 文本 unified diff；首页版本标签、附录贡献者名单/排版变化 |
| `page-NN.png` | 原 v1 PDF 指定物理页 Poppler 渲染，用于目视图表/公式 |
| `R4_minimax_m2_series.draft-20260907.md` | 交审固定初稿，不随修订改写；内容链接以 reading_notes 根目录解释 |

全源码目录逐文件比较仅 `app.tex` 变化；正文（包括全部后训练、数据环境、infra、评测）、参考文献与所有图表资产相同。附录增补13个贡献者姓名、修正2个姓氏拼写；不是新增技术附录。正式解读以 [R4 笔记](../../R4_minimax_m2_series.md) 为准。
