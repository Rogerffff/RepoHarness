# numpy `a5ea773e` 环境审查（P2，2026-09-24）

**结论**：分类 `solver_condition`；处置暂为 `unknown`，只差 R13（待中央复跑并入）。环境本身无缺口。

**依据**
- R01 / R02 / R08 / R15 pass：gold 32/32、reward 1、rc 0，导入 `/testbed/numpy/__init__.py`（1.10.0.dev0），与参考逐键一致；noop 31/32，目标键 `TestTile.test_tile_one_repetition_on_array_gh4679`（原因行只有 FAILED，断言无消息）。
- 探针十项最小条件满足：`.venv` Python 3.7.9、pytest 7.4.4；无 pip；`/tmp` 下导入失败（就地构建，in-tree `.so` 12 个）；`chown` 19.6 s。
- 公开复现：`np.tile(a, 1)` 与 `a` 共享内存，`b += 2` 后 `a` 变成 `[2..6]` → REPRO_OBSERVED=1。第一版脚本用了 1.10 里没有的 `np.shares_memory`，预检时发现，已改用 `may_share_memory`。
- 相关公开测试 `numpy/lib/tests/test_shape_base.py`：31 passed。探针的 `numpy/tests/test_ctypeslib.py` 运行 rc 1：模块级的 `test` 被 pytest 当成用例（`fixture 'self' not found`），属 nose 时代遗留，与改动无关；不加 `-x` 时是 6 passed / 1 error。

**缺口**：R13 同条件只有一次运行。

**解题侧条件**：`/testbed` 必须在 sys.path 上；无 pip、无网络；跑 `test_ctypeslib.py` 会看到 1 个无关 ERROR。 跑测试要用 `python -m pytest`：裸 `pytest` 收集会 ModuleNotFoundError（`numpy/lib/tests/` 没有 `__init__.py`，18b7cd9d 实测，本题同一构建方式，推断相同）。

**建议**：中央复跑并入后转 `environment_qualified`。

先后：复现脚本在读隐藏测试 / gold 之前写成（E06）。证据：`runs/r2e_env_repair_20260924/p2/dev_probe/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764/`、`runs/r2e_env_repair_20260924/p2/pubtests/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764.log`、`runs/r2e_env_repair_20260924/p2/followups/followups.log`（F5 段）、`runs/r2e_env_repair_20260924/p2/precheck/`。
