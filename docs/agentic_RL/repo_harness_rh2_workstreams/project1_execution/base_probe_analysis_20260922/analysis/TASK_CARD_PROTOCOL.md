# 逐题处置卡协议（基座探针 2026-09-22 第二轮分析，W6–W7）

一个 agent 负责一道题：把该题在本轮探针里的**全部尝试**（三款 solver、2–4 次）与已有分析并起来，产出一张供用户做处置决定的卡。只读分析；除报告外不改任何文件；不运行容器、不联网、不 ssh；不替用户做决定。工作目录是仓库根。

## 先读
1. `runs/base_probe_20260922/analysis/REVIEW_PROTOCOL.md`（材料布局、归因标签）。
2. 该题目录下全部已有报告：`runs/base_probe_20260922/analysis/<TASK>/**/*.md`（单条报告 `a*.md`、格子报告 `cell.md`、任务级调查 `task_investigation.md`）。
3. `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/base_model_probe_run_20260922.md` §7.5–§8（本轮结论与问题清单）。
4. 该题静态题卡目录（派发消息给出）：`card.md`、`review.md`、`public_read.md`、`analysis_before_history.md`；以及 `quality_batch01_20260921/cpu_queue.json` 或 `expansion/batch0X/cpu_queue.json` 里该题的队列项（"唯一优先实验" / 待验项）。
5. 需要核原件时再开 attempt 目录、gold、测试补丁、eval 日志；不要重做已有报告做过的逐条审查，只核对矛盾与缺口。

## 卡片内容（写到 `runs/base_probe_20260922/analysis/<TASK>/task_card.md`，正文 ≤ 1500 字）
1. **一句话现状**：S/V/N 逐 solver、争议与否、当前建议（保留 / 参考覆盖不足 / 规范欠说明 / 先诊断 / 环境缺口）。
2. **本轮实测回答了题卡的哪些待验项**：逐项写"题卡怎么说 → 本轮证据 → 已回答 / 部分 / 未回答"。这是回填静态题卡的材料，要给证据指针。
3. **评分能否区分补丁质量**：本题所有 reward=1 的候选里，与 gold 同义的有几条、有语义缺口的有几条（列输入与预期 / 实际）；reward=0 里被误拒的有几条；P2P 覆盖的边界。
4. **环境与接口条件**：actor 侧需要什么（派生镜像 / BASH_ENV 变体 / 区域变量等）、grader 侧用的配方；本题有没有出现链路问题。
5. **对 RL 的含义**：有无区分度、哪款模型有信号、稳定全 0 / 全 1 的含义、预算是否相关。
6. **处置选项**（不决定）：至少给出"原样保留 / 另版本修订（题面或参考测试，写清改什么）/ 仅评测 / 诊断旁路 / 淘汰"中适用的几项，各一句利弊；标出哪一项是评分依据变更（T0）。
7. **待办**：需要再做的最小实验（可在 CPU / grader 上做、无需模型的优先）。
8. 末尾 JSON：`{"task": "...", "cells": {"<solver>": "S/V/N"}, "verdict": "keep|coverage_gap|spec_dispute|diagnose_first|env_gap", "gold_equivalent_successes": n, "semantic_gap_successes": n, "false_negatives": n, "p2p_total": n, "actor_requirements": [...], "disposition_options": [...], "t0_items": [...], "min_followup_experiments": [...], "confidence": "high|medium|low"}`

纪律：每个结论指向可核对的证据；已有报告之间有矛盾时指出并说明采信哪个、为什么；不确定写未知。最终回复 ≤ 8 行复述并附同一 JSON。
