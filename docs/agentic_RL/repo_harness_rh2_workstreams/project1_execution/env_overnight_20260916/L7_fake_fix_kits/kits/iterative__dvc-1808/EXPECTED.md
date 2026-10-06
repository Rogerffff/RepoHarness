# iterative__dvc-1808 · 反例期望

- 仓库/版本：`iterative/dvc` @ `b3addbd2832ffda1a4ec9a9ac3958ed9a43437dd`（version 0.33，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.iterative_s_dvc-1808:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA`
- 判分面：F2P 1 条、P2P 7 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_dvc_1 / records/iterative__dvc-1808.json issues[1]`
- 断言编号：测试放过错误修复 P3（25）
- 原文摘要：写『先 _set 再返回 1』的假修复跑 F2P+P2P，预期全过。（证据：`mat/iterative__dvc-1808/grading.json#test_patch` 只断言 main 的返回码；`public.json#problem_statement` 的 Current behavior 展示的正是 .dvc/config 被改掉；note：F2P 不断言报错时配置未被修改）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/iterative__dvc-1808.fake.diff` | 先 `self._set(...)` 把 url 写进去，之后才判断『已存在且没有 --force』并返回 1（同时补上 `-f/--force` 参数）。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：唯一的 F2P `test_overwrite` 断言的是返回码序列 `0 / 1 / 0`，只要第二次返回 1、第三次带 `-f` 返回 0 就过；它不去读 `.dvc/config` 里 url 的实际值。7 条 P2P 都是别的 remote 子命令，不碰这条路径。题面真正抱怨的『url 被静默覆盖』在这一版里原封不动。

## 4. 正确评分器应该抓到什么

第二次 `remote add` 之后 `configobj['remote "a"']["url"]` 必须仍等于第一次的 url（L1 proposed_action 原文）。

判别用例脚本：`kits/iterative__dvc-1808/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/l7_diag_dvc_1808.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
