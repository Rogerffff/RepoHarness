# numpy `18b7cd9d` 环境审查（P2，2026-09-24）

**结论**：分类 `solver_condition`；处置暂为 `unknown`，只差 R13（待中央复跑并入）。环境本身无缺口。

**依据**
- R01 / R02 / R08 / R15 pass：gold 11/11、reward 1、rc 0，导入 `/testbed/numpy/__init__.py`（1.13.0.dev0），与参考逐键一致；noop 10/11，目标键 `TestDocs.test_poly_eq`，原因行 `AttributeError: 'NoneTyp…` 与题面对应。
- 探针十项最小条件满足：`.venv` Python 3.7.9、pytest 7.4.4；无 pip / uv；gcc / make 有；`chown -R /testbed` 19.1 s。
- 导入方式：`install.sh` 就地构建（`setup.py build_ext --inplace`，in-tree `.so` 12 个），没有装进 venv。`/tmp` 下 `IMPORT_FROM_TMP_RC=1`（ModuleNotFoundError）。复现脚本放在 `/rh2/` 下，即使 cwd=/testbed，普通导入也失败（IMPORT_PLAIN=fail），把 cwd 加进 sys.path 后才能导入。与 M3 一致。
- 公开复现：`poly1d([1,2,3]) == None` 抛 AttributeError → REPRO_OBSERVED=1。
- 相关公开测试 `numpy/lib/tests/test_polynomial.py`：10 passed。探针选的 `numpy/tests/test_ctypeslib.py`：7 passed。
- 残留补丁样文件 1 个（`numpy/linalg/lapack_lite/f2c_config.c.patch`），是 git 跟踪的上游文件，不是修复残留。

**缺口**：R13 同条件只有一次运行。

**解题侧条件**：**`/testbed` 必须在 sys.path 上**。在 `/testbed` 下用 `python -c` / `python -m pytest` 可以；脚本放在 `/testbed` 之外或在别处运行会 ModuleNotFoundError，可设 `PYTHONPATH=/testbed`。无 pip、无网络。 跑测试要用 `python -m pytest`：裸 `pytest` 收集会 ModuleNotFoundError（`numpy/lib/tests/` 没有 `__init__.py`，本题实测，`runs/r2e_env_repair_20260924/p2/followups/bare_pytest.log`）。

**建议**：中央复跑并入后转 `environment_qualified`；导入条件是本批 7 个 numpy 题共有的，建议任务面统一处理（E10）。

先后：复现脚本在读隐藏测试 / gold 之前写成（E06）。证据：`runs/r2e_env_repair_20260924/p2/dev_probe/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9/`、`runs/r2e_env_repair_20260924/p2/pubtests/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9.log`、`runs/env_overnight_20260916/M3/facts/18b7cd9df7a4/pkgsrc.txt`。
