# orange3__9b5494e26f407b75e79699c9d40be6df1d80a040：环境审查结论（P3，2026-09-24）

> **当前状态（2026-09-24 夜更新）**：`grading_ok_open_items`。T0-7 方案 B 已实施：环境配方 `env_pins_v2` 把 SciPy 固定为 1.5.4（环境步骤 `env_v2`），`r2e-mr-020` 把 `test_LogisticRegression`、`test_coefficients` 改为 PASSED。真实 grader：noop 0（11/13）×2、gold 1（13/13）×2，与试跑逐键相同。两个 scorer 键仍 FAILED，原因未定位，保持未完成项，交后续题意与评分质量筛查。以下是修订前的审查原文。

**结论**：分类 `material`；处置 `unknown`（R13 并入且一致后为 `environment_qualified`）。环境支持解题与判分；期望里 4 个 FAILED 是 scikit-learn 0.22.2.post1 与 SciPy 1.7.3 不兼容的依赖伪影（确定性、与参考一致），已写材料修订提案（推荐维持现状）。

**依据**
- R01/R02/R08/R15 pass：派生镜像复核通过；noop 0（11/13，只差目标键）；gold 1（13/13，rc=1，导入 /testbed/Orange/__init__.py）；与独立 runner 逐键一致。R13 unknown（中央复跑待主会话并入）。
- 探针（agent/54321、无网络、2 CPU / 4 GiB / `/tmp` 1 GiB）：十项最小条件满足；python → `.venv`（3.7.9），pytest 7.4.4，pip 有（pip check 通过），cwd=/tmp 也能导入；公开测试 `Orange/tests/test__orange.py` 收集 / 运行 rc=0；复现脚本 rc=0、REPRO_OBSERVED=1（penalty='l1' → ValueError（lbfgs 不支持 l1））。
- 期望非 PASSED 键：4 个 FAILED：lbfgs 未收敛时 sklearn `optimize.py:243` 对 str 调 `.decode` → AttributeError（test_coefficients），同一路径让交叉验证留下未初始化预测值（test_LogisticRegression）；两个 scorer 测试特征排序不符（推断同源，未单独验证）。参考 old / new 两次运行同样失败。
- 资源：gold 峰值 1238 MB（30% 限额），可信 setup 83 s、测试 2.7 s；探针 `chown -R /testbed` 89.16 s。
- 泄漏 / 工作区：HEAD 无子提交、无 remote / reflog / 残留补丁；工作区只有 `?? datasets`（install.sh 建的软链 → `Orange/tests/datasets/`）、`?? install.sh`、`?? run_tests.sh`，与修复无关。

**缺口 / 未决**
- R13 待中央复跑并入。
- 目标键 test_auto_solver 要求 solver="auto" 参数值，题面只说“自动选择”（题意明确度，交后续筛查）。

**建议**
- 材料修订提案 `material_revisions/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040.md`：推荐 A；以后统一重建 orange3 依赖时再做 B。
- 解题侧：本地跑 test_logistic_regression.py 会看到同样 4 个与修复无关的失败。

先后说明（E06）：复现脚本只据公开题面与公开工作区源码写成，写完后才读 gold / 私有测试 / 期望映射。
证据：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/tasks/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/facts.json`、`runs/r2e_env_repair_20260924/p3/dev_probe/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/dev_probe.json`、`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-o_f0536903.eval.log`、`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-o_fec8687a.eval.log`、`runs/r2e_env_repair_20260924/p3/fixture_check/orange3_9b5494e2_versions.txt`。
