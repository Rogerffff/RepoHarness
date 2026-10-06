# Moto5960：GSI 完整投影与存储保留

2026-10-03。当前：新私有测试与定向错误候选离线检查通过，新断言的非作者窄核未见阻断；发布、CPU 未做。

**问题与有效证据：** 公开目标同时要求 GSI INCLUDE 和 KEYS_ONLY scan；原 F2P 的另一项是 LSI，旧 GSI KEYS_ONLY P2P 只查 query。已有 actor 能复现两个公开例，gold 均通过；原评分无“只漏 GSI KEYS_ONLY”候选的实测。历史实际 158 节点、157 解析键有参数节点合键，未证现有对照错分。

**本轮修订：** [revised_test_draft_v1.patch](revised_test_draft_v1.patch) 为 GSI KEYS_ONLY scan 增加独立 F2P，写入两条不同数据，核总数及两条完整投影，再复读原表以查丢字段。原 INCLUDE F2P 补数量和原表复读；LSI 原断言与 155 P2P 完全不改。不得把新失败行为加进旧 P2P。预期参考为 3 F2P／155 P2P，实际收集数须另核。

**定向候选：** [omit_keys_only.patch](omit_keys_only.patch) 从 gold 仅删除 GSI KEYS_ONLY 的 scan 投影，保留 INCLUDE／LSI、query 与深复制。它的原 reward 尚未知，不能记录为已证漏判。

**后续矩阵：** noop 0、gold 1、omit_keys_only 0；错误候选先测原评分以确定是否漏判。同时核节点合键与参考身份；不私改 parser 或参考。gold 的完整扫描及复读均要真正执行。

仅做补丁应用和 AST 检查，未运行 SDK／pytest。[非作者窄核](../../reviews/non_author_new_tests_review_20261003.md) 已核新断言与既有复制行为的依据，未见阻断；不新增 LSI 目标或分页范围。当前仅修订准备，正式用途待验。
