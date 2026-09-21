# iterative__dvc-2141 · 反例期望

- 仓库/版本：`iterative/dvc` @ `c023b8da570a9b18ff26969d602011ae03ff75bf`（version 0.41，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.iterative_s_dvc-2141:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA`
- 判分面：F2P 2 条、P2P 26 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_dvc_1 / records/iterative__dvc-2141.json issues[0]`
- 断言编号：题面与评分不对应 P1（23/25）
- 原文摘要：写『只加 `yield 'working tree'`、不动 active_branch』的半修复跑当前 F2P+P2P，预期满分——即题面所述缺陷仍在却判通过。（证据：problem_statement 两个建议都是改文档；test_patch 只新增 `"working tree"` 键；hints_text 有 "master should not be included"、"rename Working Tree to working tree"）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/iterative__dvc-2141.fake.diff` | 只做 gold 的前一半：去掉 `is_dirty()` 守卫、把 `"Working Tree"` 改名成 `"working tree"`；保留 `if branches is None: revs.extend([scm.active_branch()])`。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：2 条 F2P 与 26 条 P2P 都走 `all_branches=True` 的路径，此时 `branches` 不是 None，gold 删掉的那个分支根本不会被执行，所以半修复与 gold 在判分面上无法区分。hints 里 "master should not be included" 这个缺陷仍然在。

## 4. 正确评分器应该抓到什么

`brancher(tags=[...])`（即 `branches is None` 且 `tags` 非空）时，gold 的 revs 只有传入的 tag，半修复会额外塞进 `scm.active_branch()`。当前判分面里没有这条路径。

本题没有配 `diagnostic_test`（判别点要么需要重量级 fixture，要么就是下面的 blast 运行）。

## 5. 附加（blast）运行

只在环境变量 `RUN_BLAST=1` 时执行，不进 reward，只作为『判分面 vs 改动面』的证据：

| 运行名 | pytest 参数 | 用途 |
| --- | --- | --- |
| `blast_test_metrics` | `tests/func/test_metrics.py` | 整文件运行，看半修复是否在判分面之外留下别的痕迹 |

## 6. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
