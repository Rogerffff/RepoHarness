# python__mypy-11236 处置卡（基座探针 2026-09-22，W6–W7）

材料：`task_investigation.md`（6 条全覆盖）、运行记录 §7.5b / §8.3 / §8.4 / §9.2、静态题卡 `CARD`（`.../expansion/batch02/results/python__mypy-11236`）与队列项 `mypy11236-literal-tuple-contract`（`expansion/batch02/cpu_queue.json`）。前缀 `M`、`X`、`PUB` 同 task_investigation；DeepSeek、Qwen3.6 四条以 `candidate_v2/`、`grading_v2/` 为准。

## 1. 一句话现状

S/V/N：DeepSeek 0/2/2、Coder 0/2/2、Qwen3.6 0/2/2，6 条均有效评分（`apply_ok`、安装 rc=0、解析 1 项）。**争议题，混合**：DeepSeek a1/a2、Qwen3.6 a2 三条实质候选只被两处题面未提的断言拒绝；Coder a1/a2、Qwen3.6 a1 失败输出与 noop 逐字相同，是预算内的模型失败（是否全归因于能力未证，§9.2.4）。建议：规范欠说明，两处分开裁定，裁定前先做行为矩阵；不进比较分母与训练池。

## 2. 本轮实测回答了题卡的哪些待验项

| 题卡怎么说 | 本轮证据 | 状态 |
| --- | --- | --- |
| 唯一优先实验：固定 grader 上 MWE 的 base/gold 对照 + `(2,)`、`(1,999)`，题面 flags（`CARD/card.md`:18、队列 `diagnostic_steps[0]`） | 未按原样做；三条实质候选在 actor 内以 `--python-version 3.7 --strict-optional` 复现通过（DS a1 transcript:2149、a2:1631、Q36 a2:3245）；gold 只跑过 F2P | 部分 |
| 上下文方案会让 got 显示 Literal；只拼元组上下文修不好 Final（`review.md`:19） | 3/3 应验（§3） | 已回答 |
| 漏长度检查的局部实现可能接受 `(1,999)`（`card.md`:16） | 无候选走此路线 | 未回答 |
| 被改写的 `testLiteralFinalGoesOnlyOneLevelDown` 不在执行集（`card.md`:9） | DS 两条在 actor 内全量通过（含该用例 base 版）；gold 侧仍是静态推断 | 部分 |
| actor 解释器、源码来源、可写目录未验（`card.md`:12、`review.md`:38） | `bash_env_v1` 下已核（§4），`checkexpr.py` 的编辑在 actor 内生效；`original` 未测 | 部分 |
| 未证明唯一 gold 或实际误拒（`review.md`:5） | 三条候选只因两处断言被拒，误拒与否待裁定 | 部分 |

## 3. 评分能否区分补丁质量

- reward=1：0 条。唯一 F2P `testLiteralAndInstanceSubtyping` 期望 7 行（main:14 note；main:26/30/34/36/40/42 错误）。三条实质候选修好了 main:10/12，其余 5 行逐字一致，只差两处（`M/deepseek-v4-pro/a1/grading_v2/eval_logs/*.eval.log`:631–647、a2 :607–623、`M/qwen3.6-35b-a3b/a2/grading_v2/...`:628–644）：
  1. **Final（main:18）**：`x: Final = (1,)` 后 `return x` 仍报错。prompt 无 Final（6 份同文）。公开依据两向：文档说无显式类型的 Final 按原值"substituting"（`PUB/base/docs/source/literal_types.rst`:109–127），旧用例 TODO 称其 "somewhat broken"（`check-literal.test`:2690–2691），但同用例 2693–2694 把报错写成预期。它是行为要求、不专属 gold：base 只对 Instance 取已知值（`checkexpr.py`:258–260），推断路线扩到元组也能修（静态推断）。
  2. **措辞（main:34/36）**：两种写法都拒绝交叉搭配，只差 got 显示 `Tuple[bool, int]` 还是 `Tuple[Literal[False], int]`；仓库先例是有 Literal 上下文时显示 Literal（`check-literal.test`:1458、1520）。
- 按 §9.2.2：两处分开裁定；不因 prompt 未逐字出现就删断言，也不把"按 gold 路线修"写成要求。静态看，"逐候选试推断、失败回退"的变体（`CARD/public_read.md`:50）能保持原措辞，约束实为"报错时不显示替换出的字面量"；推断路线若按标量先例修 Final，main:26/30 也会变；task_investigation §2 说"必然改变"，过强。
- 误拒：**确认 0，条件 3**。两处裁定都对候选有利才翻 1，只放宽一处仍全 0。
- 三条实质候选间的差异 F2P 看不出（静态推断，未执行）：A = `Union[Tuple[int, str], Tuple[Literal[1], int]]` 返回 `(1, 5)`，DS a2 的 `make_simplified_union` 把位置 0 折成 `int` 而拒绝；B = `Union[Tuple[Literal[1], int], Tuple[str, Literal[2]]]` 返回 `("a", 2)`，DS a2 与 Q36 a2（取首个含 Literal 的元组）拒绝。gold 与 DS a1 两例都接受。
- P2P=0：评分只选 1 项（`X/noop/eval_logs/*.eval.log`:555），不跑 testcheck 其余约 5334 例；DS 两条在 actor 内全量 5334 passed（a1 transcript:2373、a2:2891）。未覆盖：`(1,999)`、无上下文 `d = (1, 2)`、变长 / 星号上下文、A/B。池级：216 题中 22 题 P2P 为空（mypy 14/40、MONAI 4、DVC 3、Conan 1；`s2/ingest/grading_bundles_v2_v0.jsonl`）；§9.2.6：一个 F2P 可含多条负例（本题 6 条），先定位具体缺口再选最小回归集。
- actor 反馈与奖励反向：gold 行为会让 base 版 `testLiteralFinalGoesOnlyOneLevelDown` 失败（静态推断），但该用例被上游同 PR 有意改写，**不是 gold 回归证据**；上下文路线在 actor 内全量通过却得 0。
- 更正 task_investigation：DS a1 在 `check-tuples.test` 只加 1 个 case（4 个函数），非 4 例（5334→5335 passed）。

## 4. 环境与接口条件

- actor：原公开镜像 `xingyaoww/sweb.eval.x86_64.python_s_mypy-11236:latest`（manifest `sha256:6b6a59ea…`）+ `bash_env_v1` + `--harness-out out_of_tree`，无区域变量。dev-check：testbed Python 3.9.19、mypy 从 `/testbed` 导入、pytest 6.2.5、`/testbed` 可写（`runs/base_probe_20260922/remote/runs/x1_devcheck/python__mypy-11236/bash_env_v1/`）；`original` 未单测，§8.3 #1 按机制同样适用（推断）。`pytest.ini` 带 `-nauto`，窄测需 `-n0`。
- grader：`install_wave1:python__mypy-11236(rebuilt20260922)` → `sha256:5e4a1727…`（≠ 09-19 历史 `sha256:853ffff2…`），parser `swegym_parsers@242429c1`；同镜像 noop 0、gold 1（`X/*/ledger.jsonl`）。
- 链路：镜像自带的已跟踪脏文件 `test-requirements.txt` 被薄入口卷入，4 条 v1 apply_failed，已清洗重评（§7.5b；正式链 census 不受影响）。Qwen3.6 a1 的 `grading_v2/ledger.jsonl` 首行为空补丁 `apply_failed`，次行按 noop 评 0，采信次行。无网关 / adapter 故障；Qwen3.6 thinking 清空（§8.3 #7）在 a1 可见，因果未证。

## 5. 对 RL 的含义

- 当前 6/6 全 0，无梯度；奖励把"修好题面缺陷并守住 6 条负例"与"零改动"都记 0。过程差异（DS 修好后反复跑全量、不收尾；Coder 在错误函数上循环；Q36 a1 只读不改）二值奖励看不见。
- 预算：6/6 撞 60 回合。DS 两条非因果（功能编辑在调用 #31 / #25 已定型）；Q36 a1 的空补丁由截断直接造成；其余未知。"延长预算也必失败"没有证据（§9.2.4；task_investigation 摘要"六条都非因果"过强）。
- 两处都放宽时按现有候选推算：DS [1,1]、Q36 [0,1]、Coder [0,0]；但 A/B 缺口会拿同分，需补区分输入。
- **原样进训练池最差**：全 0 无梯度；偶发的 1 分只奖励恰好满足 Final 与 gold 显示约定的样本，区分的是路线而非能力。

## 6. 处置选项（不决定）

| 选项 | 内容 | 利 / 弊 | 等级 |
| --- | --- | --- | --- |
| A | 原样保留，标"规范欠说明（Final + 措辞）"，诊断旁路，不进比较分母与训练池；原始分数保留、诊断子集另列 | 不动材料；对训练无用 | 非 T0 |
| B | 另版本：题面补 Final 行为说明（`x: Final = (1,)` 后 `return x` 应被接受），**不写实现层**（task_investigation 原文"修复放在子类型层"按 §9.2.2 删去） | 保住 gold PR 完整验收；措辞仍要配 B′-w；需重跑 | 题目版本变更，需用户批准 |
| B′ | 另版本改参考测试，两开关分开裁定：**B′-w** 保留 incorrect_return1 两条负例、不再断言 got 文本（如拆成独立 case，用 `# type: ignore` + `--warn-unused-ignores` 只断言"会报错"，未验证）；**B′-f** 把 does_work 移出或单列 | 利：两条路线可比；弊：偏离官方评分；task_investigation 原 B′ 整删 incorrect_return1，会丢掉唯一的字面量交叉搭配负例 | **T0（评分依据变更）** |
| C | 仅评测不训练，并列含 / 不含本题的分母 | 保留观测；无训练样本 | 非 T0 |
| D | 淘汰 | 最省事；丢掉一道可修订的题 | 非 T0（池决定） |

## 7. 待办（CPU / grader 即可，无需模型）

1. 在固定 grader（重建镜像 `sha256:5e4a1727…`，探针机恢复后）对 gold 跑 base 版 `testLiteralFinalGoesOnlyOneLevelDown`（只应用源码段，`pytest -n0 -rA -k testLiteralFinalGoesOnlyOneLevelDown`），noop / DS a1 / DS a2 / Q36 a2 同跑 base 版与上游改写版。静态预期：base 版 gold 失败、其余通过，改写版相反。只作"反馈与奖励反向"的实测，不作 gold 回归证据。
2. 写 `rh2/experiments/base_probe_20260922/checks/mypy11236.py`（`checks/README.md` 标"待写"），经 `behavior_check.sh` 对 noop / gold / DS a1 / DS a2 / Q36 a2 逐条输出，"是否报错"与 got 文本分列：① 公开 MWE，flags `--python-version 3.7 --strict --strict-optional --warn-return-any`；② `(2,)`、`(1, 999)`；③ Final `does_work`；④ F2P 六条负例；⑤ A、B；⑥ `d = (1, 2)` 与 `CARD/public_read.md`:109 的窄回归集。候选用 `candidate_v2/*.diff`（v1 含脏文件，apply 会失败）；README 候选列表补 DS a2。
3. 队列 `replay_entry` 仍指历史镜像 `sha256:853ffff2…`（旧实例已删），改指重建镜像（题卡归属方）。
4. 按裁定起草 B 题面文本或 B′ 测试 diff，新版重做 noop/gold 并重放 DS a1，不回填原版分数。
5. 回填题卡：`review.md`:19 两条预言 3/3 应验；唯一优先实验仍未执行（§2）。

```json
{"task": "python__mypy-11236", "cells": {"deepseek-v4-pro": "0/2/2", "qwen3-coder-30b-a3b-instruct": "0/2/2", "qwen3.6-35b-a3b": "0/2/2"}, "verdict": "spec_dispute", "gold_equivalent_successes": 0, "semantic_gap_successes": 0, "false_negatives": 0, "conditional_false_negatives": 3, "p2p_total": 0, "actor_requirements": ["原公开镜像 xingyaoww/sweb.eval.x86_64.python_s_mypy-11236:latest（manifest sha256:6b6a59ea…），无 actor 派生", "bash_env_v1（正式链 original 缺口见 §8.3 #1；本题 original 未单测）", "--harness-out out_of_tree", "无区域变量；pytest.ini 带 -nauto，窄测需 -n0", "导出须排除镜像自带的已跟踪脏文件 test-requirements.txt（薄入口已修；正式链 census 不受影响）"], "disposition_options": ["A 原样保留，标规范欠说明（Final + 措辞），诊断旁路，不进比较分母与训练池；原始分数保留、诊断子集另列", "B 另版本：题面补 Final 行为说明，不写实现层；措辞需配 B′-w；原版保留", "B′ 另版本改参考测试，两开关分开裁定：B′-w 保留负例、只去 got 文本；B′-f 移出或单列 does_work（T0）", "C 仅评测不训练，并列报告含/不含本题分母", "D 淘汰"], "t0_items": ["B′-w：参考测试不再断言 incorrect_return1 的 got 文本 = 评分依据变更", "B′-f：把 does_work（Final 分支）移出 F2P 或单列 = 评分依据变更", "为 P2P=0 补执行选集或回归门 = 评分依据变更（§8.3 #11）"], "min_followup_experiments": ["固定 grader（rebuilt sha256:5e4a1727…）上对 gold 跑 base 版 testLiteralFinalGoesOnlyOneLevelDown，并对 noop/DS a1/DS a2/Q36 a2 跑 base 版与上游改写版", "写 checks/mypy11236.py 并经 behavior_check.sh 跑：公开 MWE（题面 flags）/ (2,)、(1,999) / Final / 六负例（报错与 got 文本分列）/ 区分输入 A、B / 无上下文与窄回归集；候选用 candidate_v2，补 DS a2", "cpu_queue replay_entry 改指重建 grader 镜像", "按裁定起草 B 题面文本或 B′ 测试 diff，新版重做 noop/gold 并重放 DS a1"], "confidence": "high"}
```
