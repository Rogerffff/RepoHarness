# iterative__dvc-4719 · 反例期望

- 仓库/版本：`iterative/dvc` @ `6a79111047a838b2e7daee0861570ffe01c38d02`（version 1.8，python 3.9）
- 镜像：`xingyaoww/sweb.eval.x86_64.iterative_s_dvc-4719:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA`
- 判分面：F2P 1 条、P2P 0 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_dvc_2 / records/iterative__dvc-4719.json issues[1]（另见 issues[2] 的上游笔误）`
- 断言编号：零回归保护 P1
- 原文摘要：写 `def save(self, stage): return` 的破坏性假修复跑当前 F2P+P2P，预期 RESOLVED_FULL。（证据：P2P=0；同文件 4/5 在 gold 下 FAILED）issues[2] 另指出 test_patch 里 `assert get_stage_hash.not_called` 是笔误，永远为真。

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/iterative__dvc-4719.fake.diff` | `StageCache.save` 开头无条件 `return`，run cache 从此永不写入。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：唯一的 F2P `test_always_changed` 只断言 `cache.save(stage) is None`（外加两条恒真的 `assert get_stage_hash.not_called`）与 `restore` 抛 `RunCacheNotFoundError`；而 `restore` 的 always_changed 守卫在 base 里已经存在（`dvc/stage/cache.py` 的 `restore` 首行），所以只要 `save` 返回 None 就满分。P2P=0。

## 4. 正确评分器应该抓到什么

普通 stage（`always_changed=False` 且 `is_callback=False`）调用 `save` 时必须真的算 stage hash 并落盘；把上游笔误 `assert get_stage_hash.not_called` 写成 `get_stage_hash.assert_not_called()` 之后，gold 仍通过，而『只加 restore 守卫不加 save 守卫』的版本会失败。

判别用例脚本：`kits/iterative__dvc-4719/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/unit/l7_diag_dvc_4719.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
