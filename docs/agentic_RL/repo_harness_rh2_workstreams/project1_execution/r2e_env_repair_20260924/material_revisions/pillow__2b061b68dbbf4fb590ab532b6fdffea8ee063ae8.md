# 材料修订提案：pillow `2b061b68`（公开题面与目标测试矛盾）

> **当前状态（2026-09-24 夜）**：用户决定 T0-3 留给后续题意与评分质量筛查；环境阶段不改材料，记录转为 `grading_ok_open_items`（未完成项带 `deferred_to`）。以下是提案原文。

2026-09-24 / P4 sub-agent（B 线环境审查）。状态：**提案（T0，待用户决定）**；本轮未改题面、expected、隐藏测试或 gold。环境与评分本身可用（R01/R02/R08/R15 pass，探针最小条件满足）。

## 要决定什么

该题公开题面（`problem_statement`，进 prompt）是否修订，或该题是否暂不进训练池。

## 事实（均有证据）

| 事实 | 证据 |
| --- | --- |
| 题面 Actual Behavior 写的是 save / show 时 `TypeError: exceptions must be derived from Warning, not <class 'NoneType'>`。这句话来自隐藏测试 `test_no_resource_warning_on_save` / `test_show_deprecation` 里的 `pytest.warns(None)`：pytest 8 的 `WarningsChecker` 对 None 抛这个 TypeError（镜像 pytest 8.3.4） | `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-p_d21a126c.eval.log`（FAILURES 段） |
| 库调用触发不了这个异常：公开复现在 base 上 save（JPEG）、`show()`、`show(command=…)` 都正常，`REPRO_OBSERVED=0` | `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/repros/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8.py`、`runs/r2e_env_repair_20260924/p4/dev_probe/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/dev_probe.json`（REPRO_OUTPUT） |
| 目标键 `TestImage.test_open_formats` 断言：`Image.open(PNG, formats=123)` 抛 TypeError；`Image.open(PNG, formats=["JPEG"])` 与 `("JPEG",)` 抛 `UnidentifiedImageError`。题面却说 `Image.open('hopper.png', formats=['JPEG'])` “should work without issues” | noop 日志 `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_90eb28b3.eval.log`（测试源码片段）；`runs/r2e_rf_20260923/remote/prepared_r2e/prompts.jsonl` |
| base 上 `Image.open` 没有 `formats` 参数（示例第一行即 `TypeError: open() got an unexpected keyword argument 'formats'`），标题 “After Adding `formats` Parameter” 暗示参数已存在；gold 只改 `src/PIL/Image.py` | 复现输出 `OPEN_SIGNATURE_HAS_FORMATS False`；facts `gold_included_paths` |
| 两个 FAILED 键本身是死键（与候选代码无关、合法源码改动翻不动），评分一致 | 同上 gold / noop 日志；公开 `Tests/test_image.py` 同样 2 例失败（`runs/r2e_env_repair_20260924/p4/targeted_public_tests/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/agent_probe.log`） |

后果：照题面实现（让 `formats=['JPEG']` 仍能打开 PNG）会让目标键失败、判 0；求解者也可能花时间追一个库里不存在的 TypeError。R2E 题面由测试失败信息生成，“把 harness 伪影写成缺陷”可能是同源数据的系统性问题（本包 `2d01f7d0` 有同样的 FAILED 键，但其题面没受影响）。

## 选项

| 选项 | 做法 | 代价 |
| --- | --- | --- |
| A 保持原样 | 不改，登记为题面质量问题 | 进训练则对“遵循题面”的策略给负信号 |
| B 修订题面 | 新 revision：说明 base 上 `Image.open` 不支持 `formats`；要求新增 `formats`（None = 全部格式；list / tuple 限定格式，不在其中则 `UnidentifiedImageError`；其它类型 → TypeError）；删去 Warning/NoneType TypeError 的描述 | 偏离 R2E 源数据，需版本化（`problem_statement_sha256` 与 pins 重算）；写到断言细节有“透露测试”之嫌，措辞要把握；需人工维护修订版 |
| C 隔离 | 本轮不进训练池，等 R2E 题面质量筛查统一决定（批量修订或剔除） | 少 1 题；随时可撤 |

两个 pytest 8 死键：三种选项下都**不改**（评分一致，不误伤正确解）。

## 推荐

**C（本轮隔离）**，在后续题意筛查中统一评估 B。理由：本轮只做环境资格；题面修订是 T0，且可能是同源数据的系统性问题，逐题手修不如先定统一规则（例如“题面 Actual Behavior 与 noop 目标键失败原因不符即标记”——本包可提供对照：noop 目标键原因 `unexpected keyword argument 'formats'` vs 题面所述 TypeError）。

## 长期代价与以后还能改什么

- 隔离随时可撤；题面修订版可在任意时点加入（版本化），不影响派生镜像与评分面。
- 若选 B，建议同时建立“题面修订层”的 provenance 规则，避免与 R2E 源数据的静默分叉。
