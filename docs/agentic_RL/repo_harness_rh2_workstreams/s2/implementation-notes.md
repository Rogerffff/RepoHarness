# S2 implementation-notes（三节制）

范围：S2 各任务执行期的设计决策 / 偏离 / 权衡 / 开放问题。S2-1 的任务级规格见 `s2_1_data_ingestion_execution_plan.md`（已含 codex 轮次 4 审查修订与 O-1~O-4 定案）；本文只记执行中新产生的重要事项。

## 1. 设计决策与偏离

- **[S2-1 T0, 2026-07-12]** 无偏离。两项自检全 PASS（`s2_1_t0_selfcheck.md`）。唯一值得留痕的执行细节：重跑 `assert_repo_disjoint.py` 会原地重写 `meta/repo_disjoint_report.json`——本次重写结果与冻结版逐字节一致所以 digest 复验仍过；**后续任何人重跑该脚本后必须确认报告未漂移**（漂移即数据面变动信号，不是脚本问题）。

## 2. 权衡取舍

（暂无）

## 3. 开放问题

（暂无——O-1~O-4 已在执行计划 §8 定案）
