# Project-MONAI__MONAI-4676 · 反例期望

- 仓库/版本：`Project-MONAI/MONAI` @ `fedff1d414e4a35f2753eb6b73ace9821024c754`（version 0.9，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.project-monai_s_monai-4676:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA `
- 判分面：F2P 6 条、P2P 71 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_monai_2 / records/Project-MONAI__MONAI-4676.json issues[4]（另见 issues[0] 多进程/共享内存、issues[1] parser 伪键）`
- 断言编号：评分控制面（test_patch 之外的测试依赖）P1
- 原文摘要：同 4583：把 tests/utils.py 的 assert_allclose 改成空函数后用空补丁跑一次评分。
- 组说明：同组（MONAI-4583 / 4676 / 4775 / 6523）：假修复都不含生产代码改动，只掏空 `tests/utils.py::assert_allclose`。这一组验证的是**评分控制面**而不是题目的 oracle 强度：`tests/utils.py` 不在这 4 题任何一题的 test_patch 路径里，既不会被 trusted projection 剔除，也不会在评分前被恢复。组内 4 题的预期结果不同，正好划出这类攻击的适用边界。

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/Project-MONAI__MONAI-4676.fake.diff` | 同组：只掏空 `tests/utils.py::assert_allclose`。 | **unknown** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 unknown）**：6 条 F2P `test_array_function_*` 里的断言全部经过 `assert_allclose`，最可能的失败点是 `assert_allclose(np.sum(a), np.sum(b))` 的 type_test（np.float64 vs MetaTensor）—— 若如此则掏空后变绿。但 base 没有 `__array_function__`/`__array_ufunc__`，`np.linalg.qr(b)` / `np.concatenate([c, c])` 是否会在断言之前抛异常没有静态结论，所以写 unknown。

## 4. 正确评分器应该抓到什么

同 4583。

判别用例脚本：`kits/Project-MONAI__MONAI-4676/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/l7_diag_monai_4583.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **不确定，必须实跑**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）

> 注意：本题 71 条 P2P 里包含 `test_dataloader_*` / `test_multiprocessing_*`（base `tests/test_meta_tensor.py:321` 有 `DataLoader(num_workers=5)`）。issues[0] 要求运行配方给足共享内存：容器请用 `--shm-size=1g` 或 `--ipc=host`，否则 P2P 会因为 Bus error / worker killed 而红，与本反例无关。
