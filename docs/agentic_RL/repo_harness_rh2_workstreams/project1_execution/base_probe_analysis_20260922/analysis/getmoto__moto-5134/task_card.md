# 处置卡：getmoto__moto-5134

材料：本目录 7 份报告（DS a1 + cell、Q36 a1 + cell、Coder a1/a2 + cell）、12 份 ledger、12 份候选 diff、gold、题卡目录、`cpu_queue.json` 项 `moto5134-public-actor-development`、运行记录 §7.5–§9。缩写：DS = deepseek-v4-pro，Q36 = qwen3.6-35b-a3b，Coder = qwen3-coder-30b-a3b-instruct；ADIR = `runs/base_probe_20260922/remote/runs/matrix/attempts/getmoto__moto-5134/<solver>/<a>`。

## 1. 一句话现状

DS 4/4/4 [1111]、Q36 4/4/4 [1111]、Coder 0/4/4 [0000]；12 条评分全部有效（`RH2_INSTALL_RC=0`、17 项全解析、被测补丁 sha256 = 导出候选、同镜像 P0 noop 0 / gold 1），无争议、无误拒、无疑似假阳性。建议：**保留**，当前池里最干净的跨模型区分题；登记"P2P 不含 archive 回归面"。

## 2. 本轮实测回答了题卡的哪些待验项

| 题卡怎么说 | 本轮证据 | 状态 |
| --- | --- | --- |
| 队列项唯一优先实验：public-image actor 能否从 checkout 跑存在性矩阵与 Logs 复现，并区分目标失败与依赖失败（card.md:13） | `bash_env_v1` 下：解释器 testbed 3.12.4、`moto.__file__=/testbed/moto/__init__.py`（DS a1 #14）、编辑生效、pip 前后不变（各 `facts/`）。base 目标失败经 EventPattern（Q36 a2 #18、a3 #16）和 boto3 端到端（Coder a2、a4 CALL#12）复现；修后 Logs MWE 通过 6 条（DS a3 #30、a4 #25、Q36 a1–a4）。依赖失败可分离：3 个 SQS 用例 `KeyError: 'QueueUrl'`（boto3 1.35.9），DS a1/a3/a4 用 `git stash` 证明 base 即失败 | 部分：诊断变体已答；正式链 `original` BASH_ENV 不达 CC（运行记录 §8.3 #1）仍是 A 线缺口 |
| 只删 None 判断、仍用 `get` 合并缺键会被旧缺键断言拒；"未运行"（review.md:16、analysis_before_history.md:46） | Coder a1–a4 四次实跑，全部止于 `test_event_pattern.py:27` `assert not foo_exists.matches_event({"detail": {}})`（各 eval.log 855–882 行区间） | 已回答 |
| 显式传"键是否存在"是合理替代，"仅静态"（review.md:17、abh:44） | 7/8 成功候选走此路线，reward=1 | 已回答 |
| NoRegionError 属复现配置（public_read.md:38） | 6/12 撞到（DS a4、Q36 a1、Coder a1–a4），各 1 回合绕过 | 已回答 |
| `test_event_pattern` API 是 AWS 对照、moto 未实现（review.md:14） | DS a3 #32、Q36 a1 调用得 `KeyError: 'Result'`，读到 `NotImplementedError` 后放弃 | 已回答 |
| 字符串哨兵碰撞、null+prefix、dump ID 截断、跨题暴露（card.md:11、15） | 无候选用字符串哨兵；17 项均解析无缺；其余本轮无观测 | 未回答 |

## 3. 评分能否区分补丁质量

**8 条 reward=1，三种形态**：① `object()` 哨兵——Q36 a1，与 gold 同构，哨兵插在 import 中间，+2 处 flake8 E402；② `k in event` 布尔标志沿 `_does_event_match → _does_item_match_filters → _does_item_match_named_filter` 下传——DS a1/a2、Q36 a2/a3/a4；③ 布尔标志 + 父节点守卫——DS a3 `if not isinstance(event, dict): return False`，DS a4 `if event is None: event = {}`。各报告本地差分（658–1059 例）：8 条在所有有定义输入上 = gold；显式 null 两向（test_patch:8、16）、缺键、字符串、dict 非叶子、archive `replay-name` 例全部一致。差异只在 base/gold 本就抛 AttributeError 的"父节点缺失 / null / 标量"输入：DS a3 一律 False，DS a4 把 None 父节点当 `{}`（`exists:false` 下二者相反），Q36 a2 改抛 TypeError。题面与参考都未规定，不计语义缺口，但奖励分不出。

**4 条 reward=0，无误拒**：a1/a2/a3 终态 `leaf_exists = is_leaf_node`（违反参考测试 12 条断言中 6 条缺键断言），a4 `return filter_value`（8/12，另违反 dict 非叶子）。四条都先说对根因（`event.get(k)` 合并缺键与 null），T=0.7 下同一路径，是先验。a4 CALL#42–46 曾搭出与 DS 同构的 `key_exists` 下传：缺键用例已过，只剩 `test_event_pattern.py:29` dict 断言失败（ADIR L590），随后整体回滚（L599–621）。

**P2P 边界**：12 P2P = 11 pattern + 1 Logs；执行选集 17 = +2 F2P +3 SQS（非引用）。`tests/test_events/test_events.py`（103 项，含 archive 规则 `replay-name: [{"exists": False}]`，models.py:1441）不在选集。Coder a1 在 actor 全跑 `tests/test_events/` 得 7 failed（transcript.md:2637–2644）：`test_archive_actual_events`、`test_archive_event_with_bus_arn`、`test_start_replay_send_to_log_group` 是候选引入的回归，grader 看不到。本轮未改分数（Coder 已在 F2P 失败），但"过 F2P、破 archive"的候选会被放过。8 条成功里 7 条在 actor 跑过该文件（DS 全目录 121–122 passed / 3 failed 均 SQS；Q36 a1–a3 103 passed），Q36 a4 未跑。

## 4. 环境与接口条件

actor：公开镜像 `79117a6d…`、`bash_env_v1`（正式链缺口未修）、boto3/botocore 1.35.9、无 `AWS_DEFAULT_REGION`、无公网；a1/a2 in_tree（DS a2 grep 偶然命中 `.harness/trajectory.jsonl`，未利用），a3/a4 out_of_tree。grader：sqs_v1 配方派生镜像（revised_install：boto3 1.28.57 / botocore 1.31.57，SQS `protocol=query`），`local_build:sha256:9f94e614…`。12/12 链路正常，无 infra。8 条改了官方 `test_event_pattern.py`，全记 `projection.ignored_paths` 并恢复（`RH2_SETUP_RESTORED=2`）；Coder 4 条夹带 5–11 个仓库根草稿（94–97% 字节），投影但不被收集。接口观察（A 线，不影响分数）：CC 不回传 DS thinking（重推轮占输出 57–76%）、Q36 thinking 每 7 回合被清（2–4 次/条）、末轮 `<|im_end|>` 泄漏（Coder a1、Q36 4/4）、CC 改写工具参数、Q36 a2 首轮误调 `Skill(code-review)`。

## 5. 对 RL 的含义

跨模型有区分度且稳定（8/8 vs 0/4）；组内无信号：Q36 全 1、Coder 全 0，a4 近似解在二值奖励下同样 0。奖励也分不出验证深度（Q36 a4 无修前复现、只抽 2 个回归用例；DS a2 无端到端）、E402、边界语义。预算非因果：Coder a2–a4 撞 60 回合，但 a1 59 回合自行交付同形态，三条终态都是自己已证伪的形态；prompt 峰值 77K < 131K。对 Q36 作训练题当前预算下无梯度；对 Coder 需更多采样或部分分才可能有正样本。

## 6. 处置选项（不决定）

- A 原样保留：无误判、区分稳定；缺点是两款候选基座都无组内信号，archive 回归面未设防。
- B 另版本扩 P2P（把 `test_events.py` 的 3 个 archive/replay 用例或整文件加入执行选集）：堵住已实测的回归面；**评分依据变更（T0）**，需先在 grader 镜像核实 gold 与 8 条成功候选都通过并记耗时。
- B′ 题面补 region 提示：只省 1 回合，不改结果，价值低。
- C 仅评测：作跨模型能力标尺，不进训练池；缺点是闲置一道干净题。
- D actor 侧派生镜像装 compat pins：去掉 3 个 SQS 噪声；代价是再维护一个镜像，本轮模型都能自行排除噪声。
- 淘汰：无依据。

## 7. 待办

1. 跑 `rh2/experiments/base_probe_20260922/checks/moto5134.py`（经 `behavior_check.sh`，原公开镜像；候选清单见 `checks/README.md`）：把 archive 回归从 actor 侧观察升级为对照表。建议追加 DS a3/a4、Q36 a2 与一个"父节点缺失 `{}`"用例，否则脚本矩阵（全在 `detail` 下）暴露不出守卫差异。
2. 若考虑选项 B：在 sqs_v1 grader 镜像对 gold + 8 条成功候选重放含 `test_events.py` 的选集，记 rc 与耗时。
3. 正式链 `original` BASH_ENV 下的 actor 开发路径核验属 A 线接缝，本题不重复做。

```json
{"task": "getmoto__moto-5134", "cells": {"deepseek-v4-pro": "4/4/4", "qwen3-coder-30b-a3b-instruct": "0/4/4", "qwen3.6-35b-a3b": "4/4/4"}, "verdict": "keep", "gold_equivalent_successes": 8, "semantic_gap_successes": 0, "false_negatives": 0, "p2p_total": 12, "actor_requirements": ["public image sha256:79117a6d… (no derived image needed)", "bash_env_v1 diagnostic BASH_ENV (formal-chain BASH_ENV gap open, A-line)", "AWS_DEFAULT_REGION unset: prompt script needs region_name (6/12 hit NoRegionError, 1 turn each)", "boto3/botocore 1.35.9: 3 SQS integration tests fail on base (noise, not in F2P/P2P)", "no network"], "disposition_options": ["A keep as-is", "B extend P2P/execution selection with test_events.py archive/replay tests (T0)", "B' prompt region hint (low value)", "C eval-only", "D actor-side compat-pins derived image"], "t0_items": ["B: adding archive/replay tests or test_events.py to the frozen execution selection / P2P"], "min_followup_experiments": ["Run checks/moto5134.py via behavior_check.sh on the public image for noop/gold/Coder a1-a4/Q36 a1,a2/DS a1 (+ DS a3/a4, Q36 a2 and a parent-missing {} case)", "If option B: replay gold + 8 successful candidates in the sqs_v1 grader image with test_events.py included, record rc and runtime"], "confidence": "high"}
```
