# orange3__f5026689551be7f0a43ad5f0d129e5bcfff7999c：环境审查结论（P3，2026-09-24）

**结论**：分类 `env_ok`；处置 `unknown`（R13 并入且一致后为 `environment_qualified`）。环境无缺口；R12 自动检查的“峰值超 60%”已归因为 chown 触发的可回收页缓存，2 GiB 限额下 gold 复跑仍 reward 1——不需要内存档位（已验证）。

**依据**
- R01/R02/R08/R15 pass：派生镜像复核通过；noop 0（7/8，只差目标键）；gold 1（8/8，rc=0，导入 /testbed/Orange/__init__.py）；与独立 runner 逐键一致。R13 unknown（中央复跑待主会话并入）。
- 探针（agent/54321、无网络、2 CPU / 4 GiB / `/tmp` 1 GiB）：十项最小条件满足；python → `.venv`（3.8.20），pytest 8.3.4，pip 有（pip check 通过），cwd=/tmp 也能导入；公开测试 `Orange/tests/test__orange.py` 收集 / 运行 rc=0；复现脚本 rc=0、REPRO_OBSERVED=1（migrate_settings 后 selected_id 仍是 'dir1\\bar'）。
- 期望非 PASSED 键：无（期望全 PASSED）。
- 资源：gold 峰值 2632 MB（64% 限额），可信 setup 175 s、测试 4.3 s；探针 `chown -R /testbed` 213.53 s。内存归因：4 GiB：chown 212 s 后 file 2430 MB、kernel 164 MB、anon 0.7 MB；公开测试 test_owdatasets.py（6 passed）期间 anon 峰值 173 MB；memory.peak 2795 MB。2 GiB：chown 225 s、测试同样 6 passed、memory.peak 顶到 2048 MB、memory.events max 2249 次触顶回收、oom 0；2 GiB 真实 grader gold 复跑：reward 1、8/8 键一致、峰值 2048 MB（顶到限额）、可信 setup 185 s、测试 4.9 s、同一派生镜像 ID（`runs/r2e_env_repair_20260924/p3/ledger_gold_mem2g.jsonl`）。
- 泄漏 / 工作区：HEAD 无子提交、无 remote / reflog / 残留补丁；工作区只有 `?? datasets`（install.sh 建的软链 → `Orange/tests/datasets/`）、`?? install.sh`、`?? run_tests.sh`，与修复无关。

**缺口 / 未决**
- R13 待中央复跑并入。
- memory.peak 随宿主页缓存状态波动（R-f 与 memprobe 同题差 0.2–0.9 GB），不能当资源需求量用。

**建议**
- 不设 orange3 内存档位；R12 判据改看 anon 峰值或 memory.events 的 oom（包 README §7）。
- 解题侧：复现 / widget 测试要带 `QT_QPA_PLATFORM=minimal … xvfb-run` 前缀；rollout 初始化的 chown 约 3.5–4 分钟（并行负载下）。

先后说明（E06）：复现脚本只据公开题面与公开工作区源码写成，写完后才读 gold / 私有测试 / 期望映射。
证据：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/tasks/orange3__f5026689551be7f0a43ad5f0d129e5bcfff7999c/facts.json`、`runs/r2e_env_repair_20260924/p3/dev_probe/orange3__f5026689551be7f0a43ad5f0d129e5bcfff7999c/dev_probe.json`、`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-o_777f237e.eval.log`、`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-o_acf8b7dc.eval.log`、`runs/r2e_env_repair_20260924/p3/memprobe/f5026689_mem4g/summary.txt`、`runs/r2e_env_repair_20260924/p3/ledger_gold_mem2g.jsonl`。
