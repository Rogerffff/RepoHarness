# datalad `6b6fa389` 环境审查（P2，2026-09-24）

**结论**：分类 `solver_condition`；处置暂为 `unknown`，只差 R13（待中央复跑并入）。环境本身无缺口。

**依据**
- R01 / R02 / R08 / R15 pass：gold 17/17、reward 1（入口 rc 1 是期望内的 FAILED 键），与参考逐键一致；noop 16/17，目标键 `test_url_samples`，原因行 `URL(path='weir…` 与题面对应。
- 探针十项最小条件满足：`.venv` Python 3.7.9、pytest 7.4.4；editable 安装，`/tmp` 下可导入；无 pip；`chown -R /testbed` 60.8 s。
- 公开复现（题面示例原样）：`scheme='file:implicit' hostname='' path='weired_url:/'` → REPRO_OBSERVED=1。
- 期望里的 FAILED 键 `test_get_local_file_url_linux`：`'file:///a~' != 'file:///a%7E'`。Python 3.7 起 `urllib.parse.quote` 不再转义 `~`（镜像内实测 `quote('/a~') == '/a~'`，`get_local_file_url` 调 `urlquote`），上游用例按 ≤ 3.6 的行为写。该解释器版本下上游本就失败，确定性；noop、gold 与公开运行结果一致。不是环境缺口。
- 相关公开测试 `datalad/tests/test_network.py`：16 passed / 1 failed（同一键）/ 1 xfailed。

**缺口**：R13 同条件只有一次运行。

**提醒**：该键是 P2P-FAILED。若解答顺手让 `~` 转义成 `%7E`，它会变成 PASSED，反而判 0；这与题面无关，风险低，只作记录。

**解题侧条件**：cwd 不限；无 pip、无网络；agent HOME 没有 git 身份（本题不涉及 git 操作，按同一初始化推断）。

**建议**：中央复跑并入后转 `environment_qualified`。

先后：复现脚本在读隐藏测试 / gold 之前写成（E06）。证据：`runs/r2e_env_repair_20260924/p2/dev_probe/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb/`、`runs/r2e_env_repair_20260924/p2/followups/followups.log`（E、F2 段）、`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-d_9fbcea90.eval.log`。
