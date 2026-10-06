# iterative__dvc-4778 · 反例期望

- 仓库/版本：`iterative/dvc` @ `f8ba5daae23ffc5c2135f86670bd562d6ce654d7`（version 1.9，python 3.9）
- 镜像：`xingyaoww/sweb.eval.x86_64.iterative_s_dvc-4778:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA`
- 判分面：F2P 4 条、P2P 0 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_dvc_2 / records/iterative__dvc-4778.json issues[0]`
- 断言编号：奖励漏洞（可复现）P1
- 原文摘要：在 `resolve_paths` 开头写一行 `raise DvcException("x")` 跑真实 grader，预期 RESOLVED_FULL —— 这是本包最值得先跑的一个反例。（证据：F2P 四条只断言 `pytest.raises(DvcException)`；P2P=0；gold 下同文件 51/55 FAILED）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/iterative__dvc-4778.fake.diff` | `dvc/utils/__init__.py::resolve_paths` 开头无条件 `raise DvcException`，`dvc add` 对任何路径都不再工作。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：4 条 F2P 全形如 `with pytest.raises(DvcException): dvc.add(...)`（test_patch 新增的 `test_add_symlink_dir` / `test_add_file_in_symlink_dir`），无条件抛异常必然命中；P2P 为空，没有任何回归能拦下它。

## 4. 正确评分器应该抓到什么

正常路径的 `dvc.add("foo")` 必须成功并生成 `foo.dvc`；当前判分面里没有任何一条这样的用例。

判别用例脚本：`kits/iterative__dvc-4778/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/unit/l7_diag_dvc_4778.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 附加（blast）运行

只在环境变量 `RUN_BLAST=1` 时执行，不进 reward，只作为『判分面 vs 改动面』的证据：

| 运行名 | pytest 参数 | 用途 |
| --- | --- | --- |
| `blast_test_add` | `tests/func/test_add.py` | 整文件运行，量化『gold 下 51/55 FAILED』这一已知环境问题与 fake 的差别 |

## 6. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）

> 注意：L1 记录该题存在 pathspec 依赖问题（`test_add_symlink_file` 等在 gold 下也 FAILED）。本套件不修依赖，只看 F2P∪P2P 的判定；blast 运行的整文件结果要按这一偏差解读。
