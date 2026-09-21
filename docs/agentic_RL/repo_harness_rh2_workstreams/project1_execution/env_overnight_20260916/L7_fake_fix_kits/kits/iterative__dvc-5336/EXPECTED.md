# iterative__dvc-5336 · 反例期望

- 仓库/版本：`iterative/dvc` @ `9638dde4daf3f338e3538712133c4457e96d23ad`（version 1.11，python 3.9）
- 镜像：`xingyaoww/sweb.eval.x86_64.iterative_s_dvc-5336:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA`
- 判分面：F2P 2 条、P2P 4 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_dvc_2 / records/iterative__dvc-5336.json issues[0]`
- 断言编号：F2P 过弱（放宽型修复无约束）P1
- 原文摘要：写 `def chmod(self, p, m): try: os.chmod(...) except BaseException: pass` 跑 F2P+P2P，预期满分。（证据：唯一断言 `assert mock_chmod.called`；P2P 仅 4 条）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/iterative__dvc-5336.fake.diff` | `LocalTree.chmod` 把 `except OSError` 的全部分支换成 `except BaseException: pass`。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：F2P 的 `test_protect_ignore_errors[1]`（EPERM）与 `[13]`（EACCES）唯一的断言是 `assert mock_chmod.called`，对『哪些异常应当继续上抛』毫无约束；P2P 的 `[30]`（EROFS）与两条 `test_is_protected` 同样只需要不抛异常。本题的修复方向本来就是『放宽』，所以吞得更狠一定满分。

## 4. 正确评分器应该抓到什么

gold 只吞 `OSError` 并记 `logger.trace`；假修复连 `ValueError` / `KeyboardInterrupt` 都吞。判别用例：让 `os.chmod` 抛 `ValueError`，gold 会上抛，假修复静默吞掉。

判别用例脚本：`kits/iterative__dvc-5336/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/unit/l7_diag_dvc_5336.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
