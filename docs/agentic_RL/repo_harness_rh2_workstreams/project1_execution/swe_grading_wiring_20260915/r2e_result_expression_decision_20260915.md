# 决策包（T0）：R2E 任务的评分结果在 rh2 里怎样表达

日期：2026-09-15。作者：Claude（B 线，S1-f）。性质：决策包；R2E 代码放第二片。

**用户决定（2026-09-15）：先选 A（最小接入：来源语义字段 + 专用计数），以后再决定是否换 B 或其它修改。** 下文按 §11.3 的三处事实更正修订，方案原文保留。

## 1. 要决定什么

R2E-Gym 的 reward 不是"F2P 由败转胜、P2P 不回归"，而是 **expected 状态映射的精确匹配**：每个测试 id 有一个期望状态（PASSED / FAILED / ERROR / SKIPPED 都可能是期望值），观测映射必须与期望映射逐键相等且键数相等（Prime 的 `parse_log_pytest` + `calculate_reward` 语义，昨夜 `r2e_probe.py` 已逐字复刻并在 24+24 题上验证）。要决定的是：这种语义进入 rh2 时，`GradingReport` 契约与训练侧消费者用哪种表达。

## 2. 代码事实

- [contracts/grading.py](../../../../../rh2/src/repoharness2/contracts/grading.py)：`outcome ∈ {resolved, unresolved, failed_to_grade}`；`resolved` 与 `tests_failed` 必须带齐 `f2p_pass_count / f2p_total_count / p2p_fail_count / p2p_total_count` 四计数；只有 `patch_apply_failed` 与 `test_execution_timeout` 允许无计数的 0；infra 族 reward 必须为 None；`reward_scale_version="binary_v1"`。
- `envpack/scoring.py::grading_outcome_fields` 把 `EvalVerdict`（F2P/P2P 桶）翻成上述字段；v2 入口（S1-b）沿用同一翻译。
- `GradingReport` 的消费者（契约 docstring）：RewardFacts（reward 出处）、EligibilityGate 的 clean_grading 维度、训练视图/审计。四计数今天只被契约校验器与 scoring 产出方引用，训练侧只消费 `reward / outcome / failure_category`。
- R2E 材料形态（昨夜实测）：镜像 `namanjain12/<repo>_final:<commit>`，HEAD = 修复提交的父提交，**修复提交在镜像 git 历史里可达**（泄漏，需要派生镜像或 git-sanitize 后再用）；隐藏测试在 `/r2e_tests`，`run_tests.sh` 运行它们；venv `/testbed/.venv`；expected 映射键含 `::` 拼接的参数化 id，pillow 的键含 ANSI 序列（Prime 侧带 ESC 字节的正则去色）。
- 两个已知反例：coveragepy 016af5 的 expected 里记录了一个**历史环境失败**（子进程缺 `mock`）——目标修复成功而精确匹配判 0；datalad 58ba51 的可信测试依赖旧仓库 helper fixture（`datalad.interface.tests.test_docs`），gold 排除测试文件导致 fixture 未移植。
- SWE-Gym 的 F2P/P2P **不是**R2E 精确映射的特例（§11.3 更正）：官方口径下 XFAIL 也计成功、SKIPPED 不入任何桶、缺席计失败，与"每个参考 id 恰好等于某一状态"不同。两者的共同点只是"参考 id → 可接受状态集合 + 规则"，B 方案若要统一表达必须把可接受状态集合写进去。

## 3. 方案

**A. 来源语义字段 + 专用计数（最小契约扩展；已选）**
- `GradingReport` 加 `grading_semantics: Literal["swe_f2p_p2p", "r2e_expected_map"]`（默认前者，旧数据不变）；R2E 用新计数对 `expected_match_count / expected_total_count`，四个 F2P/P2P 计数置 None；校验器按语义分支要求计数齐全。
- 优点：改动局部、旧报告字段不变；缺点：两套计数并存，扩第三种来源（SWE-rebench 的"目标 id 全 PASSED"）还要再加分支。注意 A **同样改契约**（新增字段与校验分支），只是不改旧字段；旧序列化能否逐字节不变取决于新字段是否带默认值且不进 digest，实施 Brief 里要具体保证。

**B. 泛化为"参考状态表"（统一表达）**
- `GradingReport` 加 `reference_total / reference_matched / reference_mismatched` 与 `reference_rule: Literal["all_listed_pass", "exact_map_match"]`；F2P/P2P 四计数保留为 `swe_f2p_p2p` 规则下的派生字段（可继续填写以兼容）。
- 优点：一种表达覆盖 SWE-Gym、R2E、SWE-rebench；顺带承载 P4"本地重验证参考集"（参考表就是 id→期望状态）；缺点：契约与校验器改动更大，需要 A 线同步消费者与测试。

**C. R2E 暂不进入 rh2 评分契约，只在流水线诊断层用来源 runner 评分**
- 优点：本片零契约改动；缺点：R2E 暂时不能作为训练来源，只能作诊断/对照集。这是暂缓接入，不是永久放弃训练用途（§11.3 更正）。

## 4. 推荐（用户已选 A）

原推荐 **B**，分两步落地：第一步只加字段与校验分支、`swe_f2p_p2p` 规则下仍填四计数（与今天逐字节兼容）；第二步 R2E 适配器产出 `exact_map_match` 报告。理由：R2E 与 SWE-rebench 两个下一批来源都不是 F2P/P2P 形态；P4 本地重验证参考集也需要 id→期望状态的表达；一次改契约比每个来源加一个分支代价低。若用户希望本阶段完全不碰契约，则 A 是次优，C 只在决定放弃 R2E 训练用途时选。

## 5. 长期代价与以后还能改什么

- B 的代价：`contracts/grading.py` 校验器、`scoring.grading_outcome_fields`、契约测试、A 线的报告消费者要同步；`reward_scale_version` 不变（仍二值）。
- 无论 A/B，R2E 接入前还有三项与契约无关的前置：派生镜像清理修复提交历史（泄漏）、expected 生成条件重验证（coveragepy 类）、fixture 完整性（datalad 类）；这些属于流水线 E1/E2 环节，不因本决策而免除。
- 以后可改：规则枚举可扩；期望状态表可从上游字段切换为本地重验证结果（P4 第三类修订版本），不影响报告结构。

## 6. 不在本决策包内

reward 是否连续化（仍 binary_v1）；R2E 是否进正式训练题单；expected 是否修订（按流水线三类划分另行决定）。
