# pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199：环境审查结论（P3，2026-09-24）

> **当前状态（2026-09-24 晚更新）**：`qualified_with_revision`（T0-6 代表题）。`r2e-mr-006` 新增私有 `r2e_tests/conftest.py`，原样摘出 base 提交 `baa10328` 的 `pandas/conftest.py` 里两个 fixture；`r2e-mr-007` 期望删 2 个 ERROR 键、加 13 个参数化键。真实 grader：noop 0（233/237）×2、gold 1（237/237）×2，与试跑逐键相同；题面场景 `NA_float[Float32/Float64]` 成为活的 F2P 键。同族其余 6 题已按 T0-6 第二步照做（09-24 夜，`r2e-mr-008`…`019`）。以下是修订前的审查原文。

**结论**：分类 `material`；处置 `unknown`（R13 并入且一致后为 `environment_qualified`）。环境支持解题与判分；期望里 2 个 ERROR 键全部是隐藏测试移出原目录后 fixture 不可达（any_float_dtype / any_int_ea_dtype），确定性、与参考一致，已写材料修订提案。被掩盖的恰是题面场景的两个测试，F2P 只剩“整列全 NA”两键。

**依据**
- R01/R02/R08/R15 pass：派生镜像复核通过；noop 0（224/226，只差目标键）；gold 1（226/226，rc=1，导入 /testbed/pandas/__init__.py）；与独立 runner 逐键一致。R13 unknown（中央复跑待主会话并入）。
- 探针（agent/54321、无网络、2 CPU / 4 GiB / `/tmp` 1 GiB）：十项最小条件满足；python → `.venv`（3.8.20），pytest 8.3.4，pip 有（pip check 通过），cwd=/tmp 也能导入；公开测试 `pandas/tests/test_aggregation.py` 收集 / 运行 rc=0；复现脚本 rc=0、REPRO_OBSERVED=1（Float64 含 pd.NA 的 groupby quantile → TypeError（NAType））。
- 期望非 PASSED 键：2/226 个 ERROR，逐键 `E fixture '<名>' not found`；fixture 在 pandas 自己的 conftest 里，原位跑 base 版公开测试时同名测试 PASSED（`runs/r2e_env_repair_20260924/p3/fixture_check/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/result.txt`）。不是缺可选依赖 / 网络 / 资源。
- 资源：gold 峰值 763 MB（19% 限额），可信 setup 30 s、测试 3.4 s；探针 `chown -R /testbed` 42.55 s。
- 泄漏 / 工作区：HEAD 无子提交、无 remote / reflog / 残留补丁；工作区 7 行 = 来源 install.sh 的 versioneer 改写（pandas/__init__.py 加 3 行取版本号、_version.py、versioneer.py、setup.cfg 只剩 [versioneer] 段）+ 删除 pyproject.toml + 两个未跟踪脚本；不触及 gold 文件、无修复痕迹。

**缺口 / 未决**
- R13 待中央复跑并入。
- R16 issue：题面例子（部分 NA → 2.5）没有任何运行中的键在检查；只修全 NA 场景的候选理论上也能拿 1（推断）。

**建议**
- 材料修订提案见 `material_revisions/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199.md`（推荐进入正式池前做 B：补 fixture 生成 expected_v1）。
- 解题侧：cwd 不限；pip 有但无网络；pandas 自带 pytest 配置因 setup.cfg 被改写而不生效；不要 reset 来源镜像自带的 5 个已跟踪改动。

先后说明（E06）：复现脚本只据公开题面与公开工作区源码写成，写完后才读 gold / 私有测试 / 期望映射。
证据：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/tasks/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/facts.json`、`runs/r2e_env_repair_20260924/p3/dev_probe/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/dev_probe.json`、`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-p_bb99de50.eval.log`、`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_e47e4f78.eval.log`、`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/material_revisions/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199.md`、`runs/r2e_env_repair_20260924/p3/fixture_check/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/result.txt`。
