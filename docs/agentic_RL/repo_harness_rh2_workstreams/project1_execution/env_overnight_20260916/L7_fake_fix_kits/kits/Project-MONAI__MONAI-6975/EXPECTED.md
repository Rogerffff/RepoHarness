# Project-MONAI__MONAI-6975 · 反例期望

- 仓库/版本：`Project-MONAI/MONAI` @ `392c5c1b860c0f0cfd0aa14e9d4b342c8b5ef5e7`（version 1.2，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.project-monai_s_monai-6975:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA `
- 判分面：F2P 4 条、P2P 59 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_monai_1 / records/Project-MONAI__MONAI-6975.json issues[0]`
- 断言编号：partial_fix_accepted P1
- 原文摘要：把 DeepSeek 的 dataset.py:98 单点修复重放一次，同时跑新增的 CacheDataset lazy 用例，确认它失败而 gold 通过。（证据：logs_cc/Project-MONAI__MONAI-6975/candidate.diff 只改 dataset.py:98 → oracle RESOLVED_FULL；base 中另 11 处 apply_transform 调用点）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/Project-MONAI__MONAI-6975.fake.diff` | 只在 `Dataset._transform` 这一个调用点传 `lazy=None`，`apply_transform` 的默认值仍是 `False`。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：4 条 F2P `test_dataset_lazy_with_logging_*` 全部经由 `Dataset.__getitem__` → `_transform`，单点传参即可命中；59 条 P2P 在 test_compose.py / test_dataset.py 内，不覆盖其它调用点。这与 DeepSeek 轨迹里实际判 RESOLVED_FULL 的候选补丁生产代码部分一致。

## 4. 正确评分器应该抓到什么

`inspect.signature(apply_transform).parameters['lazy'].default is None`（gold 改的就是这个默认值）；或为 CacheDataset / IterableDataset / GridPatchDataset 各补一条同形状的 lazy 日志断言。

判别用例脚本：`kits/Project-MONAI__MONAI-6975/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/l7_diag_monai_6975.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
