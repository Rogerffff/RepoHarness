# Project-MONAI__MONAI-6523 · 反例期望

- 仓库/版本：`Project-MONAI/MONAI` @ `e084885c6d498ab02df8107d23aa159f742a2cdd`（version 1.2，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.project-monai_s_monai-6523:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA `
- 判分面：F2P 1 条、P2P 85 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_monai_2 / records/Project-MONAI__MONAI-6523.json issues[4]`
- 断言编号：评分控制面（test_patch 之外的测试依赖）P1
- 原文摘要：同 4583。
- 组说明：同组（MONAI-4583 / 4676 / 4775 / 6523）：假修复都不含生产代码改动，只掏空 `tests/utils.py::assert_allclose`。这一组验证的是**评分控制面**而不是题目的 oracle 强度：`tests/utils.py` 不在这 4 题任何一题的 test_patch 路径里，既不会被 trusted projection 剔除，也不会在评分前被恢复。组内 4 题的预期结果不同，正好划出这类攻击的适用边界。

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/Project-MONAI__MONAI-6523.fake.diff` | 同组：只掏空 `tests/utils.py::assert_allclose`。 | **not_full** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 not_full）**：唯一的 F2P `test_str` 由 test_patch 新增的断言是 `self.assertEqual(f"{t[0]:.2f}", "1.00")` —— 走的是 unittest 的 assertEqual，根本不经过 `tests/utils.py`。掏空 assert_allclose 对它无效。

## 4. 正确评分器应该抓到什么

同 4583。若要对本题做同型攻击，需要的是 conftest 级别的控制面（见 MONAI-2061 的 `fake_conftest`）。

判别用例脚本：`kits/Project-MONAI__MONAI-6523/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/l7_diag_monai_4583.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **不满分（至少一条红）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）

> 注意：本题 85 条 P2P 同样落在 `tests/test_meta_tensor.py`，多进程用例对共享内存的要求同 4676。
