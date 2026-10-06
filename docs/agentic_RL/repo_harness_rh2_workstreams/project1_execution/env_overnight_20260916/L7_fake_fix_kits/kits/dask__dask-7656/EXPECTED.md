# dask__dask-7656 · 反例期望

- 仓库/版本：`dask/dask` @ `07d5ad0ab1bc8903554b37453f02cc8024460f2a`（version 2021.04，python None）
- 镜像：`xingyaoww/sweb.eval.x86_64.dask_s_dask-7656:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -n0 -rA  --color=no`
- 判分面：F2P 1 条、P2P 48 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_dask / records/dask__dask-7656.json issues[0]`
- 断言编号：测试放过错误修复 P1
- 原文摘要：在 base 上只改 delayed.py:109 一处，跑当前 F2P+48 条 P2P，预期 RESOLVED_FULL。（证据：`07d5ad0ab1bc8903554b37453f02cc8024460f2a:dask/delayed.py:188-193` 是同形状的第二处；`:dask/tests/test_delayed.py:45-84` 是没被纳入的既有用例）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/dask__dask-7656.fake.diff` | 只在 `unpack_collections`（delayed.py:109）里过滤 `init=False` 的字段，`to_task_dask`（:191）那处不动。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：唯一的 F2P `test_delayed_with_dataclass` 只经 `unpack_collections`；48 条 P2P 也不碰 `to_task_dask` 的 dataclass 分支。gold 两处一起改，半修复在判分面上与它无法区分。

## 4. 正确评分器应该抓到什么

直接对 `to_task_dask` 传一个含 `init=False` 字段的 dataclass 实例：gold 正常，半修复抛 AttributeError。

判别用例脚本：`kits/dask__dask-7656/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/dask/tests/l7_diag_dask_7656.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 附加（blast）运行

只在环境变量 `RUN_BLAST=1` 时执行，不进 reward，只作为『判分面 vs 改动面』的证据：

| 运行名 | pytest 参数 | 用途 |
| --- | --- | --- |
| `blast_test_delayed` | `dask/tests/test_delayed.py` | 整文件运行，量化 to_task_dask 那半边的影响面 |

## 6. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
