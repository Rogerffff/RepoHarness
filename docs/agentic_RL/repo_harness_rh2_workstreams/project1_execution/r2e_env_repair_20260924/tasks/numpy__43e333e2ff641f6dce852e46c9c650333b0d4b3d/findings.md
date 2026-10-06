# numpy `43e333e2` 环境审查（P2，2026-09-24）

> **当前状态（2026-09-24 更新）**：`qualified_with_recipe`。环境配方 `env_pins_v1`（E15）把 hypothesis 固定回仓库 `test_requirements.txt` 的 6.24.1（pytest 不动），派生配方 `r2e_derive_v1+env_v1`。以解题身份常规运行 `python -m pytest numpy/ma/tests/test_extras.py`：收集正常，78 passed / 10 failed，TestAverage 6 passed；10 个失败全是 TestCov / TestCorrcoef 的旧式 setup 问题，与本题修复无关，记为解题侧噪声。真实 grader：noop 0（87/88）×2、gold 1（88/88）×2，与配方前和独立 runner 逐键一致。下文"缺口""建议"两段已由配方解决。证据 `runs/r2e_t0_revisions_20260924/`。

**结论**：分类 `solver_condition`；处置暂为 `unknown`，只差 R13（待中央复跑并入）。评分环境无缺口，但**解题侧无法按常规运行仓库自带测试**（R09 issue）。

**依据**
- R01 / R02 / R08 / R15 pass：gold 88/88、reward 1、rc 0，导入 `/testbed/numpy/__init__.py`，与参考逐键一致；noop 87/88，目标键 `TestAverage.test_masked_weights`。
- 探针十项最小条件满足：`.venv` Python 3.10.16、pytest 8.3.4；无 pip；`/tmp` 下导入失败（就地构建，in-tree `.so` 19 个）；`chown` 28.5 s。公开复现：`np.ma.average` 返回 nan → REPRO_OBSERVED=1。
- **公开测试**：探针选的 `numpy/tests/test__all__.py` 收集失败（rc 4）。相关模块 `numpy/ma/tests/test_extras.py` 同样失败。原因：`numpy/conftest.py:33` 调 `hypothesis.HealthCheck.all()`，本镜像的 hypothesis 6.124.1 为此发 `HypothesisDeprecationWarning`，`pytest.ini` 的 `filterwarnings = error` 把它变成 conftest 加载错误；`-W ignore`（含 `run_tests.sh` 的解释器参数）和 `-W ignore::DeprecationWarning` 都无效。
- 用 `-o filterwarnings=ignore` 或 `--noconftest` 绕过后，`test_extras.py` 78 passed / 10 failed：pytest 8.3.4 不再调用 nose 风格的 `setup(self)`，`TestCov` / `TestCorrcoef` 缺 `data` 属性。
- 隐藏测试不受影响：`r2e_tests/` 在 `numpy/` 之外，不加载 `numpy/conftest.py`。本批其它 6 个 numpy 镜像是 hypothesis 6.79.4 + pytest 7.4.4，conftest 能加载。

**缺口**：解题者在本环境不能直接用仓库测试验证改动；R13 待并入。

**解题侧条件**：`/testbed` 必须在 sys.path 上；无 pip、无网络。跑仓库测试需加 `-o filterwarnings=ignore`（或 `--noconftest`），并预期 nose 风格 setup 的类会失败。 跑测试要用 `python -m pytest`：裸 `pytest` 收集会 ModuleNotFoundError（`numpy/lib/tests/` 没有 `__init__.py`，18b7cd9d 实测，本题同一构建方式，推断相同）。

**建议**：本轮只把绕法记入解题侧条件。环境侧可在后续派生配方里固定 hypothesis（到不弃用 `HealthCheck.all()` 的版本）和 pytest < 8，但要先验证 gold / noop 不变；本轮不做。

先后：复现脚本在读隐藏测试 / gold 之前写成（E06）。证据：`runs/r2e_env_repair_20260924/p2/dev_probe/numpy__43e333e2ff641f6dce852e46c9c650333b0d4b3d/`、`runs/r2e_env_repair_20260924/p2/pubtests/numpy__43e333e2ff641f6dce852e46c9c650333b0d4b3d.log`、`runs/r2e_env_repair_20260924/p2/followups/followups.log`（B、F3 段）。
