# 首轮模型探针：分析报告远端副本

日期：2026-09-23。源目录为 `runs/base_probe_20260922/analysis/`。这里发布43份Markdown报告/协议、统计及Codex核对结果，供远端阅读；**没有上传完整模型请求/响应或宣称重新审阅全部轨迹**。内容归因仍以原作者、证据范围和后续更正为准。

先读[运行记录 §8.8及§9](../base_model_probe_run_20260922.md)、[A线交接包](../base_model_probe_20260922_aline_handoff.md)。报告中的绝对本机路径已替换，`runs/`和原日志行号保留作溯源定位。

| 题目 | 跨轨迹处置卡 | 逐条/格子报告目录 |
| --- | --- | --- |
| conan-io__conan-15422 | [处置卡](analysis/conan-io__conan-15422/task_card.md) | [分析目录](analysis/conan-io__conan-15422/) |
| dask__dask-8597 | [处置卡](analysis/dask__dask-8597/task_card.md) | [分析目录](analysis/dask__dask-8597/) |
| getmoto__moto-5134 | [处置卡](analysis/getmoto__moto-5134/task_card.md) | [分析目录](analysis/getmoto__moto-5134/) |
| getmoto__moto-5752 | [处置卡](analysis/getmoto__moto-5752/task_card.md) | [分析目录](analysis/getmoto__moto-5752/) |
| iterative__dvc-5839 | [处置卡](analysis/iterative__dvc-5839/task_card.md) | [分析目录](analysis/iterative__dvc-5839/) |
| iterative__dvc-6954 | [处置卡](analysis/iterative__dvc-6954/task_card.md) | [分析目录](analysis/iterative__dvc-6954/) |
| python__mypy-11236 | [处置卡](analysis/python__mypy-11236/task_card.md) | [分析目录](analysis/python__mypy-11236/) |
| python__mypy-17071 | [处置卡](analysis/python__mypy-17071/task_card.md) | [分析目录](analysis/python__mypy-17071/) |

- [跨轨迹统计](cross_trajectory_stats.json)、[最终成绩统计](summary_final.json)：每个字段的覆盖分母单独解释，不把部分字段覆盖当67条全覆盖。
- [派发与覆盖记录](analysis/DISPATCH_LEDGER.md)、[逐条协议](analysis/REVIEW_PROTOCOL.md)、[格子协议](analysis/CELL_PROTOCOL.md)、[题卡协议](analysis/TASK_CARD_PROTOCOL.md)。
- [Codex账本核对](codex_review_20260922/attempt_reconciliation.json)、[SSE完整性扫描](codex_review_20260922/sse_completion_scan.json)：历史产物复读，不是本轮重新运行。

卡片中的 keep / coverage_gap / spec_dispute 是分析建议。题面、断言、奖励或正式题池是否改变，需要结合实证和项目决定；本文不授权修改。
