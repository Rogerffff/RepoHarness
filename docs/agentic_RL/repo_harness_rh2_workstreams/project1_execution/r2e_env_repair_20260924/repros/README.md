# 公开复现脚本（`<instance_id>.py`）

用途：由探针以 agent 身份、cwd=/testbed、无网络、入口脚本同样的环境前缀（如 orange3 的 `QT_QPA_PLATFORM=minimal … xvfb-run -a`）运行，展示 base 上题面所述的行为，回答"求解者能否在公开工作区复现问题"（R09）。

规则（decisions E06）：

1. 只据 `tasks/<iid>/facts.json` 之外的**公开题面**（`s2_r2e` public bundle 的 `problem_statement`，或本地 `runs/r2e_rf_20260923/remote/prepared_r2e/prompts.jsonl` 的 prompt）改写题面示例；写脚本前不读隐藏测试、期望映射与 gold。
2. 只观测：打印异常类型与消息、关键返回值；不修改工作区文件、不写 `/testbed`；临时文件用 `tempfile`（落在 `/tmp` tmpfs）。
3. 退出码约定：能复现题面所述问题 → `exit 0` 并打印 `REPRO_OBSERVED=1`；未复现（行为已正确或环境不允许）→ 打印 `REPRO_OBSERVED=0` 与原因，`exit 0`；脚本自身出错 → 非 0。
4. 单文件、标准库 + 本仓库包，≤ 60 行；运行 ≤ 60 s。
5. 题面没有可执行示例时，写最小等价调用并在文件头注释说明推断依据；推断不成立时在 findings 里记 `unknown`。
