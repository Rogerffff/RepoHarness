# Pydantic5662：CPU 输入（2026-09-29）

状态：CPU 当前结果见本目录 result.md / result.json，输入准备说明保留如下。基于既有 card/public_read/review/screening_record 接续，核题面、实际 base main.py 与公开测试节点。精确 core 为 0.27.0，不是题面报告者版本。

输入：`runs/swegym_cpu_preprobe_20260929/task_inputs/pydantic__pydantic-5662/public_commands.json`。原 bug 的唯一预期失败及输出写在 purpose；非零必须检查目标断言，安装、import、超时或收集失败不算复现。私有评分矩阵及补丁与公开清单分开，见 private_quality_experiments.json。把所有非模型比较改 True，公开 dict/object/false matcher 明确违例；正式参考的 dict 护栏预计拒绝。若评分1，确认真实投影与目标执行后判T2b。

质量边界：唯一新增 F2P 只覆盖公开 ANY 示例，v1 §4 第2步示例拟合 S1(T2c) 未解除；一般 matcher 公开诊断通过不能代替正式评分补非示例断言。 一般真假 matcher、dict/object 已一并列入公开行为检查；ANY特判的正式漏判实验另做。

恢复：同目录 recipe_restore.json 固定 upstream digest、历史镜像/配方、wheel manifest。root 统一远端运行并保存当前代码/profile/CC、actor消息与工作区状态、投影、安装加载、逐参考和清理。我负责结果归因与已授权题级配方修订。

剩余：公开开发实际证据；本批 noop/gold/退化评分；质量缺口的正式SWE修订入口成本/适用授权；独立复核；公共GPU入口和预算。不得仅因公开开发可运行就进训练；若原题目标与评分无冲突，能力比较用途另按本批证据标注限制，非自动准入。

既有证据入口：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/pydantic__pydantic-5662/card.md`、同目录 `review.md` 与 `public_read.md`；历史评分 `runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-5662/`。
