# iterative__dvc-1712 · 反例期望

- 仓库/版本：`iterative/dvc` @ `5c39c6b8bd01f543a27abe1d3091640d4e844bf8`（version 0.31，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.iterative_s_dvc-1712:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA`
- 判分面：F2P 1 条、P2P 2 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_dvc_1 / records/iterative__dvc-1712.json issues[0]`
- 断言编号：回归池过小 P2（25/26）
- 原文摘要：base/gold 各跑一次 `pytest -rA tests/test_add.py tests/test_state.py`，取双侧 PASSED 交集作为扩充 P2P；再写 `WHERE inode={} OR 1=1` 的假修复验证当前 F2P 会放行。（证据：`git show 5c39c6b8bd:tests/test_state.py` 全文件 3 条用例；P2P 只有 2 条且已取满同文件；note：F2P 只断言『非 None』而不校验内容）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/iterative__dvc-1712.fake.diff` | `get_state_record_for_inode` 的 SQL 后面挂一个恒真谓词 `OR 1=1`，查询永远返回某一行。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：唯一的 F2P `test_transforms_inode` 只有 `self.assertIsNotNone(ret)`，不校验 mtime/size/md5 的内容；恒真谓词让任何 inode 都能查到行，所以必然命中。真正的 bug（写入用 `_to_sqlite(inode)`、读取用原始 inode）原样留着，而且现在每个文件都会拿到别人的状态记录。两条 P2P 里 `TestState::test_update` 只有一行状态记录、看不出差别；`TestStateOverflow::test` 只断言 `main(["add","dir"])` 返回 0。

## 4. 正确评分器应该抓到什么

内容断言：`ret[2] == file_md5(path)[0]`（L1 proposed_action 的第 2 条）；以及把 `tests/test_add.py` 这种走 state 写入+查询全链路的文件纳入 P2P。

本题没有配 `diagnostic_test`（判别点要么需要重量级 fixture，要么就是下面的 blast 运行）。

## 5. 附加（blast）运行

只在环境变量 `RUN_BLAST=1` 时执行，不进 reward，只作为『判分面 vs 改动面』的证据：

| 运行名 | pytest 参数 | 用途 |
| --- | --- | --- |
| `blast_state_and_add` | `tests/test_state.py tests/test_add.py` | L1 要求的扩充 P2P 候选面：取 base/gold 双侧 PASSED 交集 |

## 6. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）

> 注意：`TestStateOverflow::test` 在 `OR 1=1` 下会拿到错误的状态记录；它只断言返回码 0，静态判读认为仍会通过，但这是本题唯一的不确定点，实跑时请单独看这一条。
