# E10 原始来源与阅读附件

查阅日：2026-09-07。正式笔记见 [E10](../../E10_intern_s2_preview.md)。

- 指定论文：[E10 PDF](../../../pdfs/E10_intern_s2_preview_2608.13505.pdf)，35页，arXiv:2608.13505v1，2026-08-13。本目录不复制PDF。
- `2608.13505v1-source.tar.gz`：从 [arXiv v1 TeX](https://arxiv.org/src/2608.13505v1) 下载的原始源码包；`tex/` 为解包内容，入口 `tex/main.tex`，正文为 `tex/sections/0.abstract.tex` 至 `6.conclusion.tex`。仅作原始附件，未改写第三方内容。
- `paper-layout.txt`：指定PDF的 `pdftotext -layout` 提取；分页符分隔物理页。公式以PDF/TeX交叉核对，不能只依赖提取布局。
- `pages/pNN.png`：指定PDF22个图表/公式页的渲染，供独立审查复用；覆盖全部12幅图和5张表。部分TeX包图素材与指定PDF排版不同，正文定位以指定PDF为准。
- `hf-model-metadata.json` / `hf-model-card.md`：官方模型仓库 `internlm/Intern-S2-Preview` revision `4f57cab513689b089019fce4ad24e26520df183c` 的metadata与README。卡介绍35B，不能替代论文397B参数。未下载权重。原始README中的外部示例/相对链接保持原样，不作为本资料库的导航。
- `xtuner-revision.json` / `xtuner-README.md`：官方 `InternLM/xtuner` commit `76e705134521eff867b409f3b3451df1c4d8dd36` 的版本信息与README；只用于公开入口核查，不代表已审论文完整实现。
- `E10_intern_s2_preview.initial-20260907.md`：交独立审查的固定初稿快照；内容不再改动。其链接原以reading_notes根目录解释，仅为版本留档，不作为当前导航成品。

来源可获取不等于训练可复现。附件不包含训练数据、权重或GPU运行结果。
