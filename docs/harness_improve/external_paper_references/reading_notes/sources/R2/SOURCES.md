# R2 来源与审查附件

读取日期：2026-09-07。正文入口为 [R2笔记](../../R2_nemotron_3_ultra.md)。所有论文页码按PDF物理页，从1起算，与印刷页一致。

- [online_20260907.pdf](online_20260907.pdf)：2026-06-09版官方报告；与主资料本地PDF逐字节相同，65页。下载入口见正文§1。
- [local_report.txt](local_report.txt)：本地PDF的 `pdftotext -layout` 提取，仅辅助搜索。图形字体含控制字符，不能以formfeed片段序号作页码；重读应用PDF的物理页范围。
- [page-21.png](page-21.png)、[page-22.png](page-22.png)、[page-30.png](page-30.png)、[page-65.png](page-65.png)：两轮教师关系/MOPD公式、SWE处理、MTP公式、完整harness矩阵的原页渲染。
- page-11.png、page-12.png、page-13.png：预训练发散图5–8的原页渲染，用于处理提取乱码。
- [R2_nemotron_3_ultra_draft_20260907.md](R2_nemotron_3_ultra_draft_20260907.md)：交给独立审查者的固定初稿，之后不修改。它是原文内容快照；其中相对链接按其原位置（reading_notes/R2_nemotron_3_ultra.md）解释，不是另一个可独立导航的最终笔记。审查修订只进入正文和 [审查记录](../../reviews/07_R2_review.md)。
- [model_metadata_20260907.json](model_metadata_20260907.json)：HF四模型metadata读取结果，只保留ID、revision、可访问性和license标签，不含权重。
- [evaluator_reproducibility_20260907.txt](evaluator_reproducibility_20260907.txt)：官方Evaluator复现入口的原文快照；内部相对路径保持上游原样，按上游repo位置解释。正文附固定commit链接。
- Evaluator_revision.txt、Nemotron_revision.txt、evaluator_entry.json、nemotron_root.json：本次官方仓库入口及HEAD观察记录；不表示查过或复现整个仓库。
