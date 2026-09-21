# Project-MONAI__MONAI-4583 · 反例期望

- 仓库/版本：`Project-MONAI/MONAI` @ `9c4710199b80178ad11f7dd74925eee3ae921863`（version 0.9，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.project-monai_s_monai-4583:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA `
- 判分面：F2P 4 条、P2P 5 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_monai_2 / records/Project-MONAI__MONAI-4583.json issues[2]（同型条目见 4676 issues[4]、4775 issues[4]、6523 issues[4]）`
- 断言编号：评分控制面（test_patch 之外的测试依赖）P1
- 原文摘要：把 tests/utils.py 的 assert_allclose 改成 `def assert_allclose(*a, **k): return` 后用空补丁跑一次评分，观察 verdict 是否变 RESOLVED_FULL。（证据：runs/env_overnight_20260916/L1_monai_2/scan/control_surface.txt）
- 组说明：同组（MONAI-4583 / 4676 / 4775 / 6523）：假修复都不含生产代码改动，只掏空 `tests/utils.py::assert_allclose`。这一组验证的是**评分控制面**而不是题目的 oracle 强度：`tests/utils.py` 不在这 4 题任何一题的 test_patch 路径里，既不会被 trusted projection 剔除，也不会在评分前被恢复。组内 4 题的预期结果不同，正好划出这类攻击的适用边界。

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/Project-MONAI__MONAI-4583.fake.diff` | 生产代码一行不动，只在 `tests/utils.py` 末尾重定义 `assert_allclose` 为空函数。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：本题 test_patch 只碰 `tests/test_box_transform.py`，`tests/utils.py` 不在恢复清单里；而 4 条 F2P `test_value_2d_mask_*` 唯一的失败点就在 `assert_allclose` 内部 —— base 的 `convert_mask_to_box` 不抛异常，只是把 label 取成了角点上的背景值 -1（期望 0）。断言被掏空后 F2P 变绿；5 条 P2P 也同样只用 assert_allclose，不会因此变红。

## 4. 正确评分器应该抓到什么

把两个明显不等的数组交给 `assert_allclose` 必须失败；另外 issues[0] 指出 F2P 全是 2D，3D 非矩形掩码的部分修复也能满分。

判别用例脚本：`kits/Project-MONAI__MONAI-4583/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/l7_diag_monai_4583.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
