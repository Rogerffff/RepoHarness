# numpy `2f4a9650` 环境审查（P2，2026-09-24）

**结论**：分类 `resource`；处置 `qualified_with_recipe`。评分侧按逐题资源配方 `task_resources_v1`（grader `/tmp` 6 GiB + 内存 12 GiB，E04）运行；rollout 用默认 profile。

**依据**
- 默认 profile（`/tmp` 1 GiB tmpfs、内存 4 GiB）：`TestSavezLoad.test_big_arrays` 报 `OSError: Not enough free space to write 2147583648 bytes`，gold 141/142、reward 0。numpy 在 `convert.c:152` 对整个数组调 `npy_fallocate`，`fallocate` 一失败就报错（源码实证）。默认运行峰值只有 340 MiB，说明没有真正写满 `/tmp`——这里的"tmpfs 在 fallocate 失败时释放已分配页"是内核行为推断，与实测峰值吻合。
- 配方 v1 两次（09-23 R-f、09-24 中央复跑，同一派生镜像 `3a64ae08…`、同一 scripts_digest）：noop 都是 141/142，只有目标键 `TestSaveTxt.test_0D_3D` 不符；gold 都是 142/142。R15：`reconcile_numpy_bigtmp` 2/2 与参考一致。
- **"两个副本合计略大于 4 GiB、峰值约 4.3 GiB"的依据**：
  - 数组 2^31 + 100000 = 2,147,583,648 B。
  - `_savez` 先在目标文件旁写临时 `.npy`，再复制进 ZIP_STORED 的 `.npz`，复制完才删临时文件。两份合计 ≥ 4,295,167,296 B = 4096.2 MiB，比 4 GiB 多 200,000 B（源码在 `r2e_rf_review_20260924/evidence_agent/numpy_source_and_profiles.json`）。
  - tmpfs 页计入容器内存 cgroup，所以 4096.2 MiB + 基线约 340 MiB（默认运行峰值）≈ 4436 MiB。实测 gold / noop 峰值 4435.1 / 4439.3 MiB（09-23）、4429.4 / 4437.3 MiB（09-24），约 4.33 GiB。`mem_peak_mb` 取自 cgroup `memory.peak` ÷ 1024²，单位是 MiB。
  - 所以 4 GiB 的 `/tmp` 或 4 GiB 的内存都不够。最小充分配置未测。
- 探针十项最小条件满足：`.venv` Python 3.7.9、pytest 7.4.4；无 pip；`chown` 20.9 s。公开复现：0D 抛 IndexError → REPRO_OBSERVED=1；题面说 3D 也抛 IndexError，但 base 上 3D 实际不抛异常，属题面小出入。

**缺口**：最小充分资源未测（按 E04 不找最小值）；配方的正式消费方式留给流水线。

**解题侧条件**：`/testbed` 必须在 sys.path 上（同其它 numpy 题）；无 pip、无网络。**rollout 的 `/tmp` 也是 1 GiB**：解题者跑公开 `numpy/lib/tests/test_io.py` 时，`test_big_arrays` 在 base 上就失败（140 passed / 1 failed），与改动无关。 跑测试要用 `python -m pytest`：裸 `pytest` 收集会 ModuleNotFoundError（`numpy/lib/tests/` 没有 `__init__.py`，18b7cd9d 实测，本题同一构建方式，推断相同）。

**建议**：维持配方 v1；中央复跑里默认 profile 那两行作为"无配方即假阴性"的对照保留。

先后：复现脚本在读隐藏测试 / gold 之前写成（E06）。证据：`recipes/task_resources_v1.json`、`runs/r2e_env_repair_20260924/p2/_rerun2/`、`runs/r2e_rf_20260923/remote/ledger_r2e_numpy_bigtmp_{noop,gold}.jsonl`、`runs/r2e_env_repair_20260924/p2/followups/numpy_2f4a_fallocate_source.txt`。
