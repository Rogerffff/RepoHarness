# L2 · 参考 ID 脆弱题专项（SWE-Gym 10 题）

任务：`getmoto__moto-5417, getmoto__moto-5545, getmoto__moto-5562, getmoto__moto-5701, getmoto__moto-6308, iterative__dvc-4185, modin-project__modin-6780, pandas-dev__pandas-48106, pandas-dev__pandas-50319, pydantic__pydantic-8977`（阶段一 gold 下参考 ID 缺席的 10 题）。

## 做什么
1. 对每题：从 `grading_bundles_v2_v0.jsonl` 取 F2P/P2P 参考 ID；从阶段一日志 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/<iid>/gold/offline/a1/test_output.txt`（及 empty）取 pytest 实际输出行；用 `rh2/src/repoharness2/envpack/swegym_parsers.py` 的同一 parser 复现 status_map.json；列出每个缺席参考 ID 对应的**实际完整 nodeid 候选**（用 `repr()` 展示反斜杠、空格、Unicode、控制字符），标注差异类型：转义层数 / 空格截断 / Unicode 规范化 / 控制字符 / 参数化键碰撞（一对多）。
2. 判定每个缺席 ID 是"可证明一一映射"还是"一对多/歧义"（pandas-48106 已知一对多：截断键对应 2、2、3 条完整案例）。可证明的给出第二类修订记录 JSON（原 ID → 映射 ID → 证据）；歧义的写清为什么不能自动映射，给出替代方案（例如在 ingest 时按镜像实际 nodeid 重生成参考、或排除并记录），**不改 expected，不改任何数据文件**。
3. 产出 parser 回归样例：每种差异类型一份最小日志片段 + 期望状态映射，放 `<包目录>/parser_samples/`，供以后加进 `rh2/tests/envpack/test_swegym_parsers.py`（你不改测试文件，只准备样例与说明）。
4. 附带：用同一方法扫描全部 182 份阶段一 gold 日志，确认缺席参考 ID 的题恰为这 10 题；若发现其它题有"参考 ID 存在但状态非 PASSED/XFAIL"的可疑形态（例如 SKIPPED 参考项）也列出来（只列，不判）。
5. 报告 `<包目录>/L2_reference_ids.md`：逐题表 + 分类统计 + 建议的处置（每题一行）+ 需要用户决定的问题。
