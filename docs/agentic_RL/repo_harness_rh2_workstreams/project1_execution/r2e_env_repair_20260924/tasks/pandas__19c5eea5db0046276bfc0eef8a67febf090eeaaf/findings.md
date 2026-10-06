# pandas__19c5eea5db0046276bfc0eef8a67febf090eeaaf：环境审查结论（P3，2026-09-24）

> **当前状态（2026-09-24 夜更新）**：`qualified_with_revision`（T0-6 第二步）。`r2e-mr-008` 新增私有 `r2e_tests/conftest.py`，从 base 提交的 conftest 链原样摘出 fixture `datetime_series`, `float_frame`, `frame_or_series`, `multiindex_year_month_day_dataframe_random_data`, `ordered`, `string_series`；`r2e-mr-009` 按修复后 gold 重新核定期望（删 6 键、加 13 键、11 键改状态）。真实 grader：noop 0（161/162）×2、gold 1（162/162）×2，与试跑逐键相同；目标键不变。证据 `runs/r2e_t0_batch3_20260924/`。以下是修订前的审查原文。

**结论**：分类 `material`；处置 `environment_qualified`。环境支持解题与判分；期望里 17 个 ERROR 键全部是隐藏测试移出原目录后 fixture 不可达（frame_or_series / string_series / float_frame / datetime_series / ordered / multiindex_…），确定性、与参考一致，已写材料修订提案。

**依据**
- R01/R02/R08/R15 pass：派生镜像复核通过；noop 0（154/155，只差目标键）；gold 1（155/155，rc=1，导入 /testbed/pandas/__init__.py）；与独立 runner 逐键一致。R13 pass（R-f reps 与 all 两次一致）。
- 探针（agent/54321、无网络、2 CPU / 4 GiB / `/tmp` 1 GiB）：十项最小条件满足；python → `.venv`（3.7.9），pytest 7.4.4，pip 有（pip check 通过），cwd=/tmp 也能导入；公开测试 `pandas/tests/test_aggregation.py` 收集 / 运行 rc=0；复现脚本 rc=0、REPRO_OBSERVED=1（空 DataFrame loc 赋列表 → ValueError）。
- 期望非 PASSED 键：17/155 个 ERROR，逐键 `E fixture '<名>' not found`；fixture 在 pandas 自己的 conftest 里，原位跑 base 版公开测试时同名测试 PASSED（`runs/r2e_env_repair_20260924/p3/fixture_check/pandas__19c5eea5db0046276bfc0eef8a67febf090eeaaf/result.txt`）。不是缺可选依赖 / 网络 / 资源。
- 资源：gold 峰值 916 MB（22% 限额），可信 setup 28 s、测试 4.4 s；探针 `chown -R /testbed` 36.91 s。
- 泄漏 / 工作区：HEAD 无子提交、无 remote / reflog / 残留补丁；工作区 7 行 = 来源 install.sh 的 versioneer 改写（pandas/__init__.py 加 3 行取版本号、_version.py、versioneer.py、setup.cfg 只剩 [versioneer] 段）+ 删除 pyproject.toml + 两个未跟踪脚本；不触及 gold 文件、无修复痕迹。

**缺口 / 未决**
- R13 已 pass（R-f reps + all 两次一致）。
- 另有 9 个测试因缺 SciPy 被 skip（不在 expected 里）：expected 绑定“无 SciPy”，以后改环境要重算。

**建议**
- 材料修订提案见 `material_revisions/pandas__19c5eea5db0046276bfc0eef8a67febf090eeaaf.md`（推荐 A 维持现状；要强 P2P 信号时 7 题一起做 B）。
- 解题侧：cwd 不限；pip 有但无网络；pandas 自带 pytest 配置因 setup.cfg 被改写而不生效；不要 reset 来源镜像自带的 5 个已跟踪改动。

先后说明（E06）：复现脚本只据公开题面与公开工作区源码写成，写完后才读 gold / 私有测试 / 期望映射。
证据：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/tasks/pandas__19c5eea5db0046276bfc0eef8a67febf090eeaaf/facts.json`、`runs/r2e_env_repair_20260924/p3/dev_probe/pandas__19c5eea5db0046276bfc0eef8a67febf090eeaaf/dev_probe.json`、`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-p_c9cd4c5a.eval.log`、`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_f021bb69.eval.log`、`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/material_revisions/pandas__19c5eea5db0046276bfc0eef8a67febf090eeaaf.md`、`runs/r2e_env_repair_20260924/p3/fixture_check/pandas__19c5eea5db0046276bfc0eef8a67febf090eeaaf/result.txt`。
