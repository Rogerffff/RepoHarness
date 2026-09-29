# getmoto__moto-5752 处置卡（基座探针 2026-09-22，W6–W7）

材料：`task_investigation.md`（DeepSeek / Qwen3.6 四条）、`qwen3-coder-30b-a3b-instruct/cell.md`（Coder 两条）、运行记录 §7.5c / §8.4 / §9.2.2、静态题卡目录 `CARD`（`.../expansion/batch02/results/getmoto__moto-5752`）与 `expansion/batch02/cpu_queue.json` 队列项 `moto5752-filter-scope`。路径前缀 `M`、`X`、`PUB` 沿用两份报告。本卡只核矛盾与缺口，逐条审查以两份报告为准。

## 1. 一句话现状

S/V/N：DeepSeek 0/2/2、Coder 0/2/2、Qwen3.6 0/2/2；6 条全部有效评分（`M/*/*/grading/ledger.jsonl`：`apply_ok`、80 项解析、`report.reward=0.0`），无 infra。**争议题：规范欠说明型误拒，置信 high**。建议"规范欠说明"——不进模型比较分母与训练池，A/B/B′/C/D 待用户裁定。

## 2. 本轮实测回答了题卡的哪些待验项

| 题卡怎么说 | 本轮证据 | 状态 |
| --- | --- | --- |
| 唯一优先实验：自然的"只修 Equals AND 顺序"候选是否只在 w/world 前缀断言被拒（`CARD/card.md`:13、队列项 `question`） | 6 条独立求解交出的都是这条路线（未命中 `return False`、命中 `continue`）；6/6 死在 `tests/test_ssm/test_ssm_boto3.py:1069`（`should be 2, but is 0`），前两条题面断言 6/6 通过（pytest 走到 1069 即证 1053 / 1062 已过）；P2P 79/79 | 已回答，且比题卡设想更强：不是诊断补丁，是 6 次独立求解 |
| 看两顺序返回 Name，不只看数量 | Qwen3.6 a1 修复后两顺序均 `['test_my_param_01_b']`；Coder a1 真实 boto3 两顺序各 1 条 | 已回答 |
| a/a 不能区分，w/world 才能（`CARD/review.md`:17） | 第 3 断言即失败，第 4 断言 6/6 未执行 | w/world 已实证；a/a 仍是静态推断 |
| raw hints 缺 `continue`，只去 `return` 会落入通用比较（`review.md`:28） | Coder a1 2 次、a2 4 次施加此改法，公开 MWE 得 0 条（cell.md §1.3） | 已回答，陷阱真实存在 |
| 标签 + 普通字段混合、标签多 Values OR（队列 `diagnostic_steps` 第 1 条） | 无候选、无测试触及 | 未回答 |
| 实际 actor 导入 / 写权限 / 离线验证 / 答案可见性（`card.md`:11） | `bash_env_v1` 下 6 条导入、pytest、mock 全正常；无答案渠道命中、未读 `.harness` | `bash_env_v1` 下已回答；正式链 `original` 仍缺（§8.3 #1） |
| 5134 / 7584 版本关系（`card.md`:15） | 与本次失败无关，无跨题暴露观察 | 未回答 |

eval.log 命中行（`M/<solver>/<a>/grading/eval_logs/*.eval.log`）：DS a1 954/996/1007、a2 956/998/1009；Coder a1 969/1011/1022、a2 971/1013/1024；Qwen3.6 a1 953/995/1006、a2 957/999/1010；汇总行均 `1 failed, 79 passed`。

## 3. 评分能否区分补丁质量

- reward=1：0 条（与 gold 同义 0、语义缺口 0）。
- reward=0：6 条同一原因，均为疑似误拒（条件于范围裁定）。输入 `tag:hello` + `BeginsWith ["w"]` 预期 2、实得 0：候选保留 base 的 `tag["Value"] in values`（不看 `Option`），gold 把标签值收成列表并入通用 `Option` 比较（`runs/base_probe_20260922/remote/gold/getmoto__moto-5752.gold.patch`）。
- 要求来源：题面 `BeginsWith` 出现 0 次（6 份 `prompt.txt` 同文，`Option` 出现 4 次全是 Equals）；断言 3、4 来自 gold PR 的范围扩展，测试补丁注释 `# tag begins_with should also work`（`s2/ingest/grading_bundles_v2_v0.jsonl` 本题行）。
- 模型侧：DeepSeek a1 看到校验器放行 tag+BeginsWith，明确以 "The issue only concerns Equals… minimally fix order dependence without changing existing behavior" 放弃（`M/deepseek-v4-pro/a1/transcript.md`:495–505）；其余 5 条未考察。
- P2P 边界：79 项覆盖 describe / by_path 既有行为（题卡逐体读 33/79），不覆盖标签与 Name/Type 混合、标签多 Values OR、F2P 结果身份（只查数量）。对照 `X/noop` 0（死于 1062）、`X/gold` 1。

## 4. 环境与接口条件

- actor：原公开镜像 `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5752:latest`（digest `sha256:2665…`）+ `bash_env_v1` + `--harness-out out_of_tree`（6 份 `attempt.json`）；无区域变量要求。
- grader：同一原镜像，`derived_image_recipe=None`，parser `swegym_parsers@242429c1`，80 项无缺席。
- 链路：6 条 `completed`，无 infra、无截断因果（Coder a2 撞 60 回合，源码在第 41 次调用已定）。不影响分数的登记项：DeepSeek 两条改官方测试文件被 `projection.ignored_paths` 恢复；Coder 候选夹带 9 / 11 个仓库根草稿、a2 留一条 git stash；`<|im_end|>` 泄漏、CC 参数改写、Task 提醒（§8.3 #5–#7）。

## 5. 对 RL 的含义

- 三款全 0 且 6 条候选语义相同：组内优势为零，无梯度。原因是未公开要求，不是能力。
- **原样进训练池最差**：偶发通过奖励的是"顺手扩范围"，学到的不是修 bug。
- 过程差异只在 Coder：52 / 61 回合、213 / 239 s，对另两款 10–14 回合、26–51 s 是 4–5 倍；6 次同一不完整改法，a1 两次把自伤失败归因给仓库——正是题卡预言的陷阱。二值奖励看不见，只能靠过程奖励或回合预算塑形。
- 预算无关。改版后：B′ 让现有 6 条全 1（仍无区分）；B 不改测试，需重跑、结果未知（修正 cell.md §1.6 "B/B′ 两条都会变 1"）。

## 6. 处置选项（不决定）

| 选项 | 内容 | 利 / 弊 | 等级 |
| --- | --- | --- | --- |
| A | 原样保留，标"规范欠说明"，留诊断旁路，不进比较分母与训练池 | 不动材料；对训练无用，Coder "4 题无正样本"仍占 1 | 非 T0 |
| B | 另版本：题面补一句维护者说明（标签过滤按 `Option` 生效，含 BeginsWith），原版保留 | **依据（Codex 09-22 §9.2.2）**：AWS 官方 API 文档 `ParameterStringFilter` 明确允许 DescribeParameters 的标签过滤用 Equals / BeginsWith（Path 例外）——争议是"本题应修的范围"，不是 BeginsWith 行为没有依据；仓库校验器 `PUB/base/moto/ssm/models.py`:1462–1468 亦放行。但当前文档不自动证明 2022-12 base 时代的约定；本卡未联网、本机无 botocore，未能独立核实。利：保住 gold PR 完整验收、样本可解；弊：题面带提示性，需重做 noop / gold，新版结果不得回填原版 | 题目版本变更，不改 oracle；仍需用户批准 |
| B′ | 另版本：F2P 去掉断言 3、4（两条 BeginsWith），只留题面对应的 1、2 | 利：现有 6 条全过；弊：偏离 SWE-Gym 官方评分，放过一处 AWS 文档支持的旧缺陷，对当前三款无区分 | **T0（评分依据变更）** |
| C | 仅评测不训练，报告并列含 / 不含本题的分母 | 保留观测；不产训练样本 | 非 T0 |
| D | 淘汰 | 最省事；丢掉一道拒绝点清晰、可修订的题 | 非 T0（池决定） |

Codex §9.2.2 的路径可与 A 并行：先做行为矩阵与 B / B′ 修订草案，保留原始全题分数，诊断子集另列。

## 7. 待办（CPU 即可，无需模型）

1. 运行已备好的裁决脚本 `rh2/experiments/base_probe_20260922/checks/moto5752.py`，经 `behavior_check.sh` 对 noop / gold / 6 条候选（命令见 `checks/README.md`）。建议补两个用例：与题面 MWE 完全一致（b 同时带两标签，两顺序 Name 均应为 `['test_my_param_01_b']`）；标签 + Name 混合与标签多 Values OR（题卡未验项）。
2. 时代约定离线核：在原镜像 testbed 环境读 botocore `data/ssm/*/service-2.json` 的 `ParameterStringFilter.Option` 文档串并记 botocore 版本，与 Codex 引用的当前文档对照，决定 B 的依据是否成立。
3. 若选 B：起草题面补充文本，新版本重做 noop / gold；若选 B′：起草测试补丁 diff，用户批准后才进 oracle。
4. 回填静态题卡：`CARD/card.md` "唯一优先实验"标为已由本轮 6 条实测完成，指向本卡 §2（题卡归属方执行）。

```json
{"task": "getmoto__moto-5752", "cells": {"deepseek-v4-pro": "0/2/2", "qwen3-coder-30b-a3b-instruct": "0/2/2", "qwen3.6-35b-a3b": "0/2/2"}, "verdict": "spec_dispute", "gold_equivalent_successes": 0, "semantic_gap_successes": 0, "false_negatives": 6, "p2p_total": 79, "actor_requirements": ["原公开镜像 xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5752:latest（digest sha256:2665…），无派生配方", "bash_env_v1（agent 可读激活副本 + BASH_ENV 注入；正式链 original 下无项目解释器，§8.3 #1）", "--harness-out out_of_tree", "无区域变量要求"], "disposition_options": ["A 原样保留，标规范欠说明，留诊断旁路，不进比较分母与训练池", "B 另版本：题面补维护者说明（标签过滤按 Option 生效，含 BeginsWith）；依据 Codex §9.2.2 的 AWS API 文档 + 仓库校验器放行，需先核时代约定；原版保留", "B′ 另版本：F2P 去掉断言 3、4，只留题面对应的 1、2（T0）", "C 仅评测不训练，并列报告含/不含本题分母", "D 淘汰"], "t0_items": ["B′：修改参考测试（去掉两条 BeginsWith 断言）= 评分依据变更"], "min_followup_experiments": ["用 checks/moto5752.py + behavior_check.sh 对 noop/gold/6 候选做行为矩阵（补题面 MWE 原样用例、标签+Name 混合、多 Values OR）", "原镜像内读 botocore ssm service-2.json 的 ParameterStringFilter.Option 文档串，核 2022-12 时代是否允许标签 BeginsWith", "按用户选择起草 B 题面文本或 B′ 测试 diff，新版本重做 noop/gold，不回填原版", "回填 CARD/card.md 唯一优先实验状态"], "confidence": "high"}
```
