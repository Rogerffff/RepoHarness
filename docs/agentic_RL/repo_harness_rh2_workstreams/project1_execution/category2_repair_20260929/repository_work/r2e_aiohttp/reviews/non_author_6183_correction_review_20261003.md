# aiohttp6183：AIO-MAT-01 文案修正非作者窄核

2026-10-03。结论：**AIO-MAT-01 已在当前本地材料中关闭**；原报告保留，不回写历史结论。此结论仅覆盖文案、材料身份与修订范围，不代表 fresh 公开阅读、CPU 验收或正式发布。

审查者已见私有材料，本次不是 fresh 公开读者；只做文本、JSON、SHA256和版本差异检查，没有执行复现、项目／维护测试、SSH、容器、安装或下载。唯一新写文件为本记录，排他创建。

## 当前材料身份

- [revision_draft.json](../revision_draft.json)：`sha256:dba217c4e6ca3bdb502046c37545ae40ecf8dee93c6aa475c0e0267fc6f1ed69`。
- [6183公开题面](../materials/61833518/problem_statement.txt)：`sha256:ab73a3ec70cb08e3fd6846b8ceead6552ea82082d6f837fd9118787a0e4f004d`。
- 首版位于 [material_draft_v1_20261003](../snapshots/material_draft_v1_20261003/revision_draft.json)，revision SHA仍为原审查的 `7317999c74f70569e56f2c5f8c3433494bc4df284cb5d8724b11125a4823abe4`，可追溯原 finding。

## 关闭依据

首版与当前题面全文对比只变化第56行：原句要求所有 chunk 大于零，现句明确**非终止的数据块必须非空；零终止块只允许在完整载荷已经交付后的末尾**。这与第8行说明和第46–52行的线上解析／解压载荷断言一致；既有完整响应中的末尾 `0\r\n\r\n` 不再与 Expected Behavior 的字面要求冲突。

核对结果：

- 当前 `public_reader_bundle.json` 与题面全文／新SHA一致，相对首版仅更改 `problem_statement` 及其摘要。
- 6183草案条目只新增这一句的文本替换 edit，并更新 `sha256_after`；原两项复现 edits 不变。
- 当前 `material_manifest.json` 的所有登记本地文件摘要均吻合；`statement.patch` 包含该句变更。
- `public_repro.py` 与首版逐字节一致，未改代码或不变评分材料。其它三题全部材料及其修订条目与首版相同。

因此本修正满足 [首轮报告](non_author_material_review_20261003.md) 对 AIO-MAT-01 的文字澄清、公开bundle同步及摘要绑定要求，没有扩展目标或泄露源码修法。最终 actor 分别执行两段、新公开读者和正式发布／实际送达核对仍按原准备入口完成；它们属于尚未运行的交付验收，不妨碍本次静态文案 finding 关闭。
