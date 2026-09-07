# R13 来源附件与版本记录

读取日期：2026-09-07。附件用于复核本任务；正文入口是 `../../R13_kimi_k3.md`，固定初稿文件中的链接按该正文位置解释。

- 主资料 `pdfs/k3_tech_report.pdf`：47页、本地无arXiv水印，元数据生成于2026-07-27；其提取文本保存在 `k3_v1_layout.txt`（文件名中的v1是技术正文对应关系，不声称字节同一）。
- `arxiv_v1.pdf` / `arxiv_v1_layout.txt`：https://arxiv.org/pdf/2607.24653v1 。逐页去空白比较与本地仅p.1、41、42不同；p.1水印/版式，p.41–42贡献名单，其余技术内容一致。
- `arxiv_v2.pdf` / `k3_v2_layout.txt`：https://arxiv.org/pdf/2607.24653v2 ，47页。Poppler报告PDF字符串/字典语法警告；未把提取成功当无缺口证明，版本差异以源TeX为准。
- `arxiv_v1_source.tar.gz` / `tex_v1/` 与 `arxiv_v2_source.tar.gz` / `tex_v2/`：官方对应 `/src/2607.24653v1`、`/src/2607.24653v2`；入口 `main.tex`。附录由 `appendix.tex` 引入，包括 `appendix/4-post-training-chat-template.tex`。
- `v1_v2_source.diff`：对所有共同TeX/Bib源文件的文本diff；新首图 `tex_v2/figures/benchmark0727-fixed.tex` 与v1嵌入PDF图另按panel数字核对。§4、§6、§7、全部tables、技术附录B–F不变；§5.3措辞与其他归因变化见正文§1。
- `k25_tex/4-pipeline.tex`：从 https://arxiv.org/src/2602.02276v1 获取，仅保留K3明确引用算法所在源文件；`k25_page-08.png` 为资料库K2.5 PDF p.8原页，核Eq.(1)及正文语义；`k25_layout.txt` 为提取供定位。未做K2.5全篇精读。
- `page-*.png`：从本地K3报告渲染的核验页；图/公式/表格证据以对应原页为准，不是新生成内容。
- `arxiv_abs.html`：2026-09-07 arXiv摘要页快照，用于版本记录。
- `model_card.md` / `model_metadata.json`：官方Hugging Face模型卡与API快照，查询revision `f831ab66814297da540d832a5235f8e904f29d06`；仅用于资产可访问性、模型license名与文件目录，不复核卡片全部评测内容。
- `agentenv_metadata.json`：官方GitHub仓库metadata快照，仅核公开可访问/MIT；不从当前代码推断K3实际训练配置。
- `coverage_before_old_notes.md`：读旧稿前的覆盖记录。
- `R13_kimi_k3.draft_20260907.md`：固定被审初稿；后续不修改。独立审查另存 `../../reviews/08_R13_review.md`，正式修订见正文。

未下载权重、训练数据集或运行训练。原始论文源码/模型卡快照包含作者自己的路径和网页链接，其上下文以官方来源为准；可提交正文的本地链接按最终reading_notes位置核验。
