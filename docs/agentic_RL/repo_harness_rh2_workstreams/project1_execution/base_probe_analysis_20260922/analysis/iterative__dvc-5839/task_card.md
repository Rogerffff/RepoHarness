# 处置卡：iterative__dvc-5839（基座探针 2026-09-22，12 条尝试）

依据：本目录 `deepseek-v4-pro/{a1,a2,cell}.md`、`qwen3-coder-30b-a3b-instruct/cell.md`、`qwen3.6-35b-a3b/cell.md`；运行记录 §7.2/§7.5/§8；静态题卡 `card.md`/`review.md`/`public_read.md`/`analysis_before_history.md`；队列项 `actor-dvc5839`。本卡另核了原件：12 条候选源码段、DS a2/a3 eval.log、p0 对照账本、P1 dev-check 输出、`checks/dvc5839.py`。已有报告之间无实质矛盾（a1.md 的"99 s"是 CC `duration_ms`，attempt.json `solve_seconds` 为 103 s，口径不同）。ADIR=`runs/base_probe_20260922/remote/runs/matrix/attempts/iterative__dvc-5839/<solver>/<a>`。

## 1. 一句话现状

S/V/N：DeepSeek 2/4/4 [1001]，Coder 4/4/4，Qwen3.6 4/4/4，合计 10/12。无争议：2 次失败是 base 既有公开数值 P2P 拦下的真实回归；10 次成功源码段逐字节相同、与 gold 同义。建议**保留**；actor 环境资格须登记派生镜像；"命令层硬编码 8"校准仍未做。

## 2. 本轮实测回答了题卡的哪些待验项

| 题卡怎么说 | 本轮证据 | 状态 |
| --- | --- | --- |
| actor 条件未验（card.md:3；review.md:59） | 12 条都在 `bash_env_v1`+`actor_dvc5839_v1` 下从 `/testbed` 导入并跑 pytest；7 条成功调用 dvc CLI（DS a1/a2/a3、Q36 a1/a2/a3、Coder a1 `dvc init`）。正式链 `original` 条件与公开镜像（pathspec 0.12.1）下不成立（运行记录 §7.2） | 已回答（限诊断条件） |
| F2P 只查 Mock 实参，可能误拒非 gold 形式（card.md:13；review.md:51） | 10 条关键字传参（gold 为位置实参）全部 F2P 通过，无误拒 | 已回答（只覆盖关键字/位置这一种变体，helper 重组未出现） |
| helper 数值 P2P 能否守住小数位语义（analysis §3） | DS a2/a3 把 `round(val,n)` 改成 `.{n}g`，`test_metrics_show_with_valid_falsey_values`、`_with_no_revision`、`_precision` 3 项失败（a2 eval.log:801-803；a3:789-791） | 已回答（两个已执行实例） |
| 公开 CLI 默认/4/8 × 普通/MD/JSON 对照（card.md:9、15；队列项 question） | base 侧：P1 dev-check 默认/4/8/MD 全 `1e-05 0.0`、JSON 原值（`p1_devcheck/.../bash_env_v1_actor_v1/dev_check_output.txt`:9-28）。修复后：DS a1、Q36 a1/a3 在同一源码段跑真实 CLI，默认→`1e-05 0.0`、8→`1.483e-05 1e-08`（Q36 a1 另 10→`1.48325e-05 5e-09`）；无人跑 4、MD、JSON；其余 7 条只直调 helper 或断言 Mock `run()==0`，未穿过修复点 | 部分 |
| 命令层硬编码 8 可能漏判（card.md:13；analysis §4） | 12 条无一硬编码；校准候选未造、未跑（`checks/README.md` 列为待写） | 未回答 |
| 标量 float 不舍入（review.md:11） | 无轨迹触及 | 未回答 |
| `public_hints`"禁止改测试"是否进 prompt（public_read:46、102） | 未进 prompt；7/12 改了官方 `tests/unit/command/test_metrics.py`（DS 4、Coder a2、Q36 a1/a2），一律按 `official_test_file` 忽略并恢复；Coder a1/a3 夹带根目录脚本；只有 Coder a4、Q36 a3/a4 候选只含源码（475 B） | 已回答 |

## 3. 评分能否区分补丁质量

reward=1 共 10 条：与 gold 同义 10（源码段 md5 `858f0334`，一行 `precision=self.args.precision,`；gold 为一行位置实参 `self.args.precision,`），语义缺口 0。reward=0 共 2 条：误拒 0——两条 F2P 都过，各 3/21 P2P 失败；失败输出（`0.0`→`0`、`1.09877`→`1.0988`）是用户可见回归，帮助文案"digits after the decimal point"与 base 既有 `test_metrics_show_precision` 已公开约定，模型自己跑出失败后改期望掩盖。P2P 覆盖边界：21 项直接测 helper（默认/4/7、falsey、Markdown、diff），能拦 helper 语义变更；不覆盖命令层传常量、Markdown+自定义 n、JSON 原值、标量 float——这些路径 10 条候选与 gold 行为完全一致，所以本轮没有"官方通过但与需求不符"的输入，但缺口本身仍在。奖励看不见的过程差异：Q36 a1/a2、Coder a2 向官方测试文件加了与既有 `test_metrics_show_precision` 同名、被后定义遮蔽、从未执行的测试（收集数 22 不变）并称其通过，Q36 a2 那段若真执行会失败；DS a2/a3 改写既有期望；Coder a1/a3 草稿泄漏。

## 4. 环境与接口条件

actor：`bash_env_v1`（正式链 `original` 下拿不到 testbed 解释器，A 线接缝）+ `actor_dvc5839_v1`（公开镜像 + pathspec==0.8.1，`sha256:7c0e1951…`；公开镜像 pathspec 0.12.1 使 dvc CLI rc=255，只影响 actor 复现，不影响 Mock 单测评分）。grader：`dvc_install_v1c` 配方重建 `sha256:3ff97580…`，noop=0/gold=1，12 条安装 rc=0、导入 `/testbed/dvc`。链路：无 infra；DS a2 有 17/69 次调用 grep in-tree `/testbed/.harness/trajectory.jsonl`（扩量轮已移出树）；DS a2/a3 撞 60 回合，非因果；DS 3/4 条探测答案渠道（git 未来引用、`pip download`、curl）全被隔离挡住；Coder/Q36 出现 `<|im_end|>` 泄漏、CC 参数改写、Task 提醒诱发无关工具（A 线已登记）。

## 5. 对 RL 的含义

本轮唯一组内混合格子（DS [1001]，in_tree/out_of_tree 各一成一败），且是"奖励区分了正确的东西"：范围正确的一行修复 vs 顺手改语义的过度修复，失败侧全被公开既有测试拦下。两款本地基座全 1、补丁全同，组内优势为零，本题对它们已饱和（Q36 9–18 回合、≤27 s；Coder 15–23 回合、≤53 s），与预算无关。可用信号只在 DS 型"过度修复"先验（4 次 2 次同一错误，可作负例样本）和过程侧（死测试、改期望、草稿），后者不进二值 reward。

## 6. 处置选项（不决定）

- 原样保留：评分可信、无争议、环境有现成修法；对本地基座无区分度，作低成本校准题或 DS 对照题。
- 另版本修订参考测试：补真实 CLI 数值断言（默认/4/8 × 普通/MD/JSON）关闭"硬编码 8"与 MD/JSON 缺口——**T0（评分依据变更）**；收益取决于校准实验是否证实漏判。
- 题面/hints 修订：说明官方测试文件改动不被采纳（7/12 改了）——题面变更，不改评分依据；影响训练行为不影响本题分数。
- 仅评测：留作回归/校准题不进训练池——不损失评分可信度，但放弃 DS 型过度修复负例。
- 诊断旁路：先跑第 7 节两项再定——一次 CPU 容器成本。
- 淘汰：无依据。

## 7. 待办（均无需模型）

1. 在 `actor_dvc5839_v1` 上按 `rh2/experiments/base_probe_20260922/checks/README.md` 跑 `checks/dvc5839.py`：base / gold / DS a2（过度修复）/ 任一成功候选（源码段全同，取 Q36 a3 475 B）默认/4/8/2 × 普通/MD/JSON，回填第 2 节"部分"项。
2. 另造"命令层硬编码 8"单行候选（`run()` 第六实参写常量 8）：先走 dvc5839.py 行为裁决，再走 RH2 官方 22 项；若参考全过而默认/4 错误，登记为已执行漏判，作为 T0 修订依据。
3. 可选：同轮加 scalar float YAML 作范围观察，不作必修。

```json
{"task": "iterative__dvc-5839", "cells": {"deepseek-v4-pro": "2/4/4", "qwen3-coder-30b-a3b-instruct": "4/4/4", "qwen3.6-35b-a3b": "4/4/4"}, "verdict": "keep", "gold_equivalent_successes": 10, "semantic_gap_successes": 0, "false_negatives": 0, "p2p_total": 21, "actor_requirements": ["bash_env_v1：agent 可读的 BASH_ENV 副本并注入 CC 进程（正式链 original 条件下拿不到 testbed 解释器，A 线接缝）", "actor_dvc5839_v1 派生镜像：公开镜像 + pathspec==0.8.1（sha256:7c0e1951…）；公开镜像 pathspec 0.12.1 使 dvc CLI rc=255，agent 无法用 CLI 复现", "grader 侧 dvc_install_v1c 配方重建镜像 sha256:3ff97580…，评分条件不变（noop=0 / gold=1）"], "disposition_options": ["原样保留（评分可信、无争议；对本地基座无区分度，作校准题/DS 对照题）", "另版本修订参考测试：补真实 CLI 数值断言 默认/4/8 × 普通/MD/JSON（T0）", "题面/hints 修订：说明官方测试文件改动不被采纳（题面变更，非评分依据）", "仅评测不训练", "诊断旁路：先跑硬编码 8 校准与 CLI 矩阵再定", "淘汰（无依据）"], "t0_items": ["为参考测试补真实 CLI 数值断言（默认/4/8 × 普通/Markdown/JSON）以关闭命令层硬编码 8 与 MD/JSON 覆盖缺口"], "min_followup_experiments": ["actor_dvc5839_v1 上跑 checks/dvc5839.py：base / gold / DeepSeek a2 / 任一成功候选（源码段全同）默认/4/8/2 × 普通/MD/JSON", "另造命令层硬编码 8 单行候选：先 dvc5839.py 行为裁决，再 RH2 官方 22 项；参考全过而默认/4 错误则登记已执行漏判", "可选：scalar float YAML 范围观察（不作必修）"], "confidence": "high"}
```
