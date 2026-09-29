# 处置卡：dask__dask-8597（基座探针 2026-09-22 第二轮，6 条尝试）

2026-09-23，Claude（Fable 5.1），协议 `runs/base_probe_20260922/analysis/TASK_CARD_PROTOCOL.md`；只读分析，不替用户决定。材料：三份 `cell.md`、静态题卡（`card.md` / `review.md` / `public_read.md` / `analysis_before_history.md`）、`cpu_queue.json` items[1]/[2]、`acceptance/dask8597_reference_scope.md`、运行记录 §7.2 / §7.5 / §8 / §9。本卡另核了 6 份候选 diff 与 gold、6 份 ledger、eval.log、冻结 bundle 与 x1_controls 原件；三份格子报告之间没有事实矛盾，只有口径差（§4）。

## 1. 一句话现状

S/V/N：DeepSeek 2/2/2、Coder 2/2/2、Qwen3.6 2/2/2；无争议、无 infra。六条候选的 `dask/array/slicing.py` hunk 去 `index` 行后与 gold 逐行相同（`if math.isnan(other_numel) or other_numel == 0:`），F2P 1/1、P2P 116/116。建议：**保留**——本轮已饱和、无区分度；但它是环境 / 评分链的干净对照（同一重建镜像上 noop=0、gold=1、六候选=1）。

## 2. 题卡待验项 → 本轮证据

| 题卡 / 队列怎么说 | 本轮证据 | 状态 |
| --- | --- | --- |
| `card.md:16`、`review.md:43–63`、队列 `semantics-dask8597-config`："仅 split=True 才算阈值"的部分修复可能过原参考 | 6/6 直接扩展既有 `isnan` 守卫，该变体 0 次出现；MCVE 栈都指到 `slicing.py:647` | **未回答**。它是无模型 CPU 实验，仍待做；本轮只说明该变体在三款、此预算下不"自然"出现（n=6，不能排除） |
| 队列 `actor-dask8597`：compat_v1 是否真被 actor 消费 | 否。actor = 原公开镜像 + `bash_env_v1`，六条 transcript 都是 `pytest-8.3.2`（DS a1 L763 / a2 L1490，Coder a1 L2299 / a2 L559，Q36 a1 L522 / a2 L557）；grader 侧才装 7.4.4（eval.log:622–630 或 629–637） | **已回答**（诊断条件下；正式链 `original` 连项目解释器都拿不到，§7.2，A 线接缝） |
| 同项：公开 MCVE + 窄测试能否分开目标 bug 与环境失败 | 6/6 改前复现得 `OverflowError`；`test_slicing_integer_no_warnings` / `test_getitem_avoids_large_chunks` 在 actor 因 `pytest.warns(None)` 抛 TypeError，六条都判为既有（Q36 a2 用 `git stash` 实证 L620 / L671，其余为推断）；grader 侧两项 PASSED | **已回答**。附带发现：队列 C3 的 `-k` 选集含 `getitem_avoids_large_chunks`（base `test_slicing.py:891/898` 用 `warns(None)`），在 actor 8.3.2 下必然假失败——窄测试要么剔除这两项，要么 actor 同配方 |
| `review.md:17`：两项已执行旧测试不在 P2P | bundle 逐 ID 仍为 False；六条评分里都 PASSED 但不计分（eval.log:758/769 或 765/776） | 事实再确认；本轮无候选触及 |
| `review.md:16`：返回类型 / 零轴+True 漏测 | 六条与 gold 同文，沿原 slicing plan、返回 Array | 未触发（静态缺口仍在） |
| `card.md:12`：实际 actor 消息、镜像泄漏未验 | 真实 prompt / 请求体已落盘；0/6 答案渠道探测、0/6 读 `.harness` | 部分：消息已验；"未探测"≠"无泄漏" |
| 队列 controls：镜像 / recipe 变化则旧账本不适用 | 09-22 按 compat_v1 重建为 `local_build:sha256:91979e6c…`（≠ 09-19 的 `065c32c1…`），x1_controls noop=0 / gold=1 | 已回答 |

## 3. 评分能否区分补丁质量

reward=1 共 6：与 gold 同义 6（且同文），语义缺口 0；reward=0 共 0，误拒 0。P2P=116 的边界：单 F2P 只测默认配置 `(3,0)[[0]]`；`split=True/False` × 空轴、Array 返回类型无直接保护；两项默认警告旧测试执行但不计分。六条之间的真实差异全部在奖励之外：
- 新增测试：DS a1 `test_take_empty_array`、a2 `test_slicing_zero_dim_array` 写进官方 `test_slicing.py` → `projection.ignored_paths=official_test_file`，被恢复、未执行；Coder a2 新建 `dask/array/tests/test_zero_dim_indexing.py` → 进 `included_paths`，但评分命令只收集 `test_slicing.py`，同样未执行。
- 编造 issue 号：DS a1 注释 `#8562`（离线不可核）、a2 `#8644`（大于 PR 号 8597，不可能是本 PR 所修的 issue）。
- 候选卫生：Coder a1 4 个仓库根草稿（7560/8121 B = 93%）；a2 根草稿 + `MEMORY.md` + `indexing-zero-d-dask-array-fix.md`（CC 系统提示 "# Memory" 节被照抄进 cwd，2116 B = 38.7%）。Qwen3.6 两条 561 B 纯源码。
- 过程：11–38 回合、27–82 s；Task* 仪式（Coder a1 ×3、Q36 a2 ×3）；DS a2 复现与全量 pytest 接 `| head` / `| tail` 掩盖退出码，其 `tool_result_errors=0` 不可与他条直接比。

## 4. 环境与接口条件

actor：原公开镜像（期望 digest `ab148b56…`）+ `bash_env_v1` + `--harness-out out_of_tree`；python 3.9.19 testbed、pytest 8.3.2（两项既有失败是题级环境事实，未阻断任何一条）。grader：`compat_v1:dask__dask-8597(rebuilt20260922)` → `local_build:sha256:91979e6c…`，离线装 pytest 7.4.4 + `pip install --no-deps -e .`，`pytest -n0 -rA --color=no dask/array/tests/test_slicing.py`，六条均 `119 passed, 2 skipped, 2 xfailed`。链路：无 infra、无 apply 失败、无截断。接口现象（回交 A 线，未影响分数）：CC 不回放 DeepSeek thinking（40/40 请求体 0 块，a2 约 13% 墙钟重复推理）；CC 改写工具参数（**口径差**：Coder 格子不计 `replace_all:false` 补默认，另两格子计入，聚合前统一）；`<|im_end|>` 泄漏 3/4 自部署条；Qwen3.6 thinking 被中段 `role:system` 提醒清空（a2 有 token 直接证据）；`count_tokens` 桩；DeepSeek 端缓存在 system 提醒处回落；CC 自动记忆指令让 Coder a2 把记忆文件写进 `/testbed`。

## 5. 对 RL 的含义

三款组内优势全为 0；稳定全 1 = 在 60 回合 / 当前预算下饱和（最长 38 回合），预算无关。用途：(a) 环境 + 评分链的校准 / 冒烟题（快、便宜、正确性固定，§9.4 "保留 1–2 道已知题校准"）；(b) 若未来引入卫生项（草稿、记忆文件、编造引用），本题是正确性已固定的干净试验台；(c) 作 GRPO 类样本无梯度，作 SFT / 拒绝采样正样本时六条的"过程差"才可见。

## 6. 处置选项（不决定）

- **A 原样保留**，标"已饱和 / 校准题"，不计入区分题、训练池低权重或只做 sanity：利——干净对照；弊——占采样预算却无梯度。
- **B 另版本修订参考（T0，评分依据变更）**：把两项已执行的默认警告旧测试纳入 P2P，或新增 `split=True` 空轴 / 显式 `False` 断言：利——关闭 `review.md` 的静态缺口；弊——本轮 6/6 未触及，修订不改变任何已得分数，应先由 E1 证明缺口可被误收再做。
- **C 仅评测**：作饱和指示题留在评测集，跟踪 actor 入口回归；无成本。
- **D 诊断旁路（非 T0，环境资格）**：actor 侧同配方派生（pytest 7.4.4）消除两项假失败，避免弱策略在训练里追逐无关失败；由 E2 决定是否必要。
- **E 淘汰**：无证据支持——题面清楚、gold 最小、链路干净。
题面无需修订（标题 "0-D" 误称不影响定位，6/6 证实）。

## 7. 待办（最小实验，均无需模型）

- E1 `semantics-dask8597-config`：按 `review.md:43–63` / 队列 `command_draft`，在 `91979e6c…` 镜像 + 冻结 compat_v1 配方上重放条件式部分修复，记录 reward、全模块 rc、两项 warns 测试、`split=True` MCVE；决定 B 是否必要。
- E2 `actor-dask8597` 余项：agent UID + `bash_env_v1` 下执行 recipe 的 `revised_install`，确认 `pytest --version` = 7.4.4 且队列 C3 选集在 gold 上全过；决定 D。
- E3（A 线读码）：正式链 census 是否排除 / 标记 `MEMORY.md` 与仓库根草稿；`.harness` 出树后的同 UID 可读性。
- 不必为本题再扩采样；若顺带重跑，只为统计条件式变体的自然出现率。

## 8. 证据指针

- 候选 vs gold：`runs/base_probe_20260922/remote/runs/matrix/attempts/dask__dask-8597/<solver>/a{1,2}/candidate/dask__dask-8597.diff`（源码段各 561 B）；`remote/gold/dask__dask-8597.gold.patch`；本卡脚本比对 6/6 True。
- 评分：各 `grading/ledger.jsonl`（`resolved`、`reward 1.0`、`f2p 1/1`、`p2p_fail 0/116`、`image_identity`、`derived_image_recipe`、`projection`）；`grading/eval_logs/*.eval.log`（DS / Q36：622–630、663、758、769、794、941；Coder：629–637、670、765、776、801、948）。
- 参考清单：`docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl` instance `dask__dask-8597`（F2P 1、P2P 116，两项 warns 测试不在）。
- 对照：`remote/runs/x1_controls/dask__dask-8597/{noop,gold}/ledger.jsonl`（0 / 1）。
- actor 条件：各 `attempt.json`（`actor_env=bash_env_v1`、`harness_out=out_of_tree`、`termination=completed`、`solve_seconds` 67.2/82.3、82.2/72.1、26.8/31.8）；`facts/agent_env_facts.txt`。
- 题卡 / 队列 / 验收：`results/dask__dask-8597/{card.md:12–18, review.md:16–20,43–63, analysis_before_history.md:50–58, public_read.md:44}`；`cpu_queue.json` items[1]/[2]；`acceptance/dask8597_reference_scope.md`；base `runs/swegym_quality_batch01_20260921_v2/public/dask__dask-8597/base/dask/array/tests/test_slicing.py:788,891,898`。
- 既有报告：三份 `cell.md`；`base_model_probe_run_20260922.md` §7.2、§7.5 #5/#6/#9、§8.1、§8.3 #1/#5–#8、§8.4、§9.2.1、§9.4。

```json
{"task": "dask__dask-8597", "cells": {"deepseek-v4-pro": "2/2/2", "qwen3-coder-30b-a3b-instruct": "2/2/2", "qwen3.6-35b-a3b": "2/2/2"}, "verdict": "keep", "gold_equivalent_successes": 6, "semantic_gap_successes": 0, "false_negatives": 0, "p2p_total": 116, "actor_requirements": ["bash_env_v1 (agent-readable activation copy + BASH_ENV injection); formal chain `original` gives no project interpreter (A-line seam, run record §7.2)", "original public image (expected digest sha256:ab148b56...) with pytest 8.3.2: test_slicing_integer_no_warnings and test_getitem_avoids_large_chunks fail with TypeError on the actor side (pre-existing, not the target bug); actor did NOT consume compat_v1; optional actor-side compat_v1 derivation (pytest 7.4.4) pending E2", "--harness-out out_of_tree", "grader: compat_v1:dask__dask-8597(rebuilt20260922) -> local_build:sha256:91979e6c..., pytest 7.4.4 offline wheel + pip install --no-deps -e ., cmd pytest -n0 -rA --color=no dask/array/tests/test_slicing.py"], "disposition_options": ["A keep as saturated calibration/control task (no discrimination; low weight or sanity-only in training pool)", "B revised reference version: add the two executed default-warning tests to P2P and/or a split=True empty-axis / explicit False assertion (T0)", "C eval-only saturation indicator", "D actor-side compat_v1 derived image, pytest 7.4.4 (environment qualification, non-T0)", "E retire (no evidence supports)"], "t0_items": ["B: any change to the frozen F2P/P2P reference lists or new reference assertions"], "min_followup_experiments": ["E1 semantics-dask8597-config: CPU/RH2 replay of the config-gated partial fix (review.md:43-63) on image 91979e6c... with the frozen compat_v1 recipe; record reward, full-module rc, the two warns tests, split=True MCVE (no model)", "E2 actor-dask8597 remainder: run the recipe's revised_install under agent UID + bash_env_v1, confirm pytest 7.4.4 and that the queue's C3 -k selection passes on gold (no model)", "E3 A-line code check: formal census handling of MEMORY.md / root scratch files; same-UID readability of .harness after out_of_tree"], "confidence": "high"}
```
