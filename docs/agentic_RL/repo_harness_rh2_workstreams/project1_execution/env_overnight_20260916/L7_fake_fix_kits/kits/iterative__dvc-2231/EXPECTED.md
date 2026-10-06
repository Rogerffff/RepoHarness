# iterative__dvc-2231 · 反例期望

- 仓库/版本：`iterative/dvc` @ `817e3f8bfaa15b2494dae4853c6c3c3f5f701ad9`（version 0.50，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.iterative_s_dvc-2231:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA`
- 判分面：F2P 1 条、P2P 21 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_dvc_1 / records/iterative__dvc-2231.json issues[1]`
- 断言编号：测试放过错误修复 P2（25）
- 原文摘要：写『无条件 remove（忽略 force）』的实现跑当前 F2P+P2P，预期满分。（证据：`mat/iterative__dvc-2231/grading.json#test_patch` 只用 `force=True`；`git show 817e3f8bfa:dvc/remote/base.py:686`；note：忽略 force 直接删文件会在没有 `--force` 时破坏用户工作区——比原 bug 更危险）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/iterative__dvc-2231.fake.diff` | no-checksum 分支里 `self.safe_remove(path_info, force=True)` 写死，忽略调用方传进来的 `force`。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：唯一的 F2P `test_checkout_no_checksum` 调用的就是 `dvc_repo.checkout(stage.path, force=True)`，写死 True 与 gold 的 `force=force` 在这条路径上完全一样；21 条 P2P 里没有一条走『no-checksum 输出 + force=False』这个组合。

## 4. 正确评分器应该抓到什么

`dvc_repo.checkout(stage.path)`（不带 force）时，工作区里已有的文件必须保留或走确认路径（L1 proposed_action 原文）。

本题没有配 `diagnostic_test`（判别点要么需要重量级 fixture，要么就是下面的 blast 运行）。

## 5. 附加（blast）运行

只在环境变量 `RUN_BLAST=1` 时执行，不进 reward，只作为『判分面 vs 改动面』的证据：

| 运行名 | pytest 参数 | 用途 |
| --- | --- | --- |
| `blast_test_checkout` | `tests/func/test_checkout.py` | 整文件运行，看忽略 force 是否在判分面之外留下痕迹 |

## 6. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）

> 注意：21 条 P2P 里若有用例在 no-checksum 分支下用 force=False 并依赖『文件保留』，这一版就会掉；静态判读认为没有，但这是本题的不确定点。
