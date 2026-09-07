# N01 原文快照记录

读取/保存日期：2026-09-07。正式标题：KAT-Coder-V2.5 Technical Report。署名 KwaiKAT Team，arXiv:2607.05471v1，提交2026-07-06。

[版本记录](https://arxiv.org/abs/2607.05471v1)本轮仅列v1。本目录只服务N01笔记；原文文件未经改写，不替换共享PDF库。

| 文件 | 原始入口 | SHA-256 |
| --- | --- | --- |
| [2607.05471v1.pdf](2607.05471v1.pdf) | [正式下载](https://arxiv.org/pdf/2607.05471v1) | `6264694a1fbda75ae0abe69a93bae00abcc460a40a0dbd02aca5e35b93996d45` |
| [2607.05471v1-source.tar.gz](2607.05471v1-source.tar.gz) | [正式下载](https://arxiv.org/src/2607.05471v1) | `5357c4e3b9db24fa6d8e46f48a7cebc247c6d38b1487e9237c382a02bcd33dc7` |

`tex/`由原始source压缩包解压，入口为[main.tex](tex/main.tex)，引用见[references.bib](tex/references.bib)，配套图片保留原路径。该目录为论文排版源码，不是模型训练实现。

[layout.txt](2607.05471v1-layout.txt)由 `pdftotext -layout` 从该PDF生成，只用于定位；公式、图和表以原始PDF及TeX为准。PDF共24物理页，p2–24页脚与物理页一致，首页无页脚。p23–24是延后浮动的正文表1–3，没有独立编号附录。

[StreamLake产品入口](https://streamlake.com/product/kat-coder)在本轮网页工具访问中超时，未以服务内容补配方。未添加不可核的训练源码、权重或数据链接。
