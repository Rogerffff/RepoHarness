# R2E coveragepy__5dbbe143：第3类范围核定结果

2026-09-29 / Claude（云端，第3类负责人）。原分类为第3类“公开目标与验收关系需核定”。当前任务：核对公开依据，明确采用一种读法或允许的范围，完成对应的题面／验收版本，不重复已验证的 R-c。

**结论（09-29 更新）：用户已选定 A（按 slug），问题和修法已明确，转第2类。** 原结论为“公开材料无法消解这个目标选择，需要用户决定（P5），推荐选 A”。选定后的落实见 §6。 本次补查没有找到能推翻 P5 的新公开依据。决定包沿用 R2E 线已备好的 A/B/C 三个选项。与读法无关的 R-c 已由 R2E 线落地，并通过正式评分验收（材料 v5）。选定后就能进入对应的修订验收。

## 1．争议点

题面要求 `_warn(..., once=True)` 的警告“should be displayed only once each, preventing duplicate warnings from appearing”。示例用**同一 slug `bot`、两条不同消息**，且都带 `once=True`，但没有写出期望输出。原目标测试按 slug 判定重复：第二条不显示。

| 读法 | 公开依据 |
| --- | --- |
| 按 slug（测试与 gold 的读法） | `_warn` docstring 写“For warning suppression, use `slug` as the shorthand”；`doc/config.rst` 称 slug 是“the name of the warning”；`doc/cmd.rst` 的警告清单是“消息模板 + (slug)”；示例故意用同一 slug 配两条消息，若按消息去重，示例里 once 看不出任何效果 |
| 按消息 | 题面“duplicate warnings”的日常字义；`inorout.warn_already_imported_files` 对同一 slug 按文件（即按消息）去重；`tests/test_api.py` 的 `test_warnings` 期望同一 slug、不同消息的两条都显示（非 once 路径）；标准库 `warnings` 的 “once” 按消息判定，仓库 `conftest.py` 在用 |

完整论证见 R2E 线的[修订计划 §1](../../../r2e_lifecycle_20260929/results/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/revision_plan.md)。公开读者、主审、复核、Codex 都判为歧义。

**本次补查**（镜像 `namanjain12/coveragepy_final@sha256:66747908…3105`，只读）：
- base 中与“只警告一次”相近的写法有两类：
  - `control.py` 的 `_warn_no_data`、`_warn_unimported_source`、`_warn_preimported_source`，是按警告类别的**开关**（`process_startup` 中置 False），不是“显示过一次就不再显示”的去重；
  - 唯一真正的去重先例是 `inorout.py:345-360` 按文件名去重，属于按消息一方。
- 因此没有新的决定性依据，P5 结论不变。gold 的 docstring “(determined by the slug.)” 是私有材料，只能作来源意图参考，不能当公开依据。

## 2．需要用户决定的事项

| 选项 | 做法 | 结果 | 代价 |
| --- | --- | --- | --- |
| **A（推荐）：按 slug** | R-f 题面补一句：以 slug 识别一条警告，同 slug 的后续 once 警告不再显示，不同 slug 各显示一次。草稿见 [`revision_draft.json`](../../../r2e_lifecycle_20260929/results/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/revision_draft.json) 的 `statement_edits` | gold 1；按消息的实现 CE1 为 0，此时属正确拒绝 | 需要一位新公开读者复读修订题面、Codex 复核，并在新版本上重跑预检与正式评分（至少 gold、noop、CE4、CE1）。本题改记为标明版本的自建题 |
| B：按消息 | R-f 题面补“按消息判断重复”；改原隐藏断言，并补“同一消息只显示一次”的断言 | gold 0；按 D4 需独立核实 CE1 作正对照 | 偏离来源意图，相当于重新定义题目 |
| C：不修订 | 保持现状 | 只作问题定位，不进探针、能力比较和训练 | 少一道简单题 |

**推荐 A 的理由**：
- 按 slug 的公开依据更成体系，包括术语、抑制 API 和示例结构；
- 与来源意图一致，gold 可以继续作正对照；
- 不改动原有断言。

R2E 线已确认，“题面文本替换”修订类已实现并经 Codex 复核，但该类代码仍在未验收的阅读快照中，落地前需核对实际版本。**按 v1 §3，两个读法不能用“或”合并。**

## 3．与选择无关、已完成的部分

- **R-c**：`r2e-mr-038/039` 补了“不同 slug 的两条 once 警告都显示”这一断言，用于拒绝 CE4（第一次 once 之后全部静默，原版得 1）。在 v5 材料上正式评分：gold 1、CE3 1、noop 0、CE4 0、CE1 0。CE1 只错在原目标键上，说明 R-c 没有替 P5 选边。依据见 [准入卡](../../../r2e_lifecycle_20260929/results/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/probe_card.md)。
- **gold 的潜伏副作用**（G1–G3）与共享控制面问题已登记，三个选项都不改变它们。

## 4．当前用途

按 v1 §2，在用户决定前只作问题定位；能力比较、训练和留出评测都为 no。

## 5．未做

- 本次没有新运行；R2E 正式评分和派生镜像没有在云端重建。
- 选定后才能进入 R-f 题面验收流程。
- 独立复核：本题结论沿用多方已有的 P5 判定，本次只补查了一条公开依据，不另起复核。

## 6．用户选定 A 之后（09-29）

**已决定**：用户 09-29 在对话中选定选项 A，即以 slug 识别一条警告。

**已实施（草案）**：R-f 题面修订 [`revised_statement_A.txt`](../../../../../../../rh2/experiments/category3_cloud_20260929/cov5dbbe/revised_statement_A.txt)。
- 父版本 sha256 `439be36d…`，与 public bundle 的 `problem_statement_sha256` 一致；修订后为 `b2a7f5fb…`。
- 修订句取自 R2E 线已备好的 [`revision_draft.json`](../../../r2e_lifecycle_20260929/results/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/revision_draft.json) 中的 `statement_edits`，一字未改：在 Expected Behavior 后补一句“与 `disable_warnings` 一样按 slug 识别警告：显示过一条 `once=True` 警告后，同 slug 的后续 `once=True` 警告即使消息不同也不再显示；不同 slug 的各显示一次”。
- 隐藏测试不改，沿用材料 v5，即已落地的 `r2e-mr-038/039`，共 76 键。

**已验证（私有模拟）**：
- 环境：原镜像 `namanjain12/coveragepy_final@sha256:66747908…3105`，root、断网、一次性容器。
- 对照候选：CE1、CE3、CE4 的原补丁在本地 `runs/`，这里按 R2E 线修订计划的描述重建（`_edit_ce.py`），不是原补丁。
- 修订句的三条断言（`statement_probe.py`），以及 v5 隐藏测试的逐键评分（`grade_r2e.py`，76 键）：

| 候选 | 同 slug、不同消息：只显示第一条 | 不同 slug：各显示一次 | 同消息重复：只显示一次 | v5 隐藏测试 |
| --- | --- | --- | --- | --- |
| base | `TypeError`（题面缺陷） | 同左 | 同左 | 0 |
| gold | 是 | 是 | 是 | **1** |
| CE3：按 slug，独立集合 | 是 | 是 | 是 | **1** |
| CE1：按消息去重 | **否**，两条都显示 | 是 | 是 | 0，只错 `test_warn_once`；选 A 后这是正确拒绝 |
| CE4：第一次 once 后全部静默 | 是 | **否** | 是 | 0，只错 `test_warn_once_each_slug` |

结果与 R2E 线 v5 正式评分一致：gold 1、CE3 1、noop 0、CE4 0、CE1 0。

**验收进行中**：一位没看过隐藏测试和 gold 的新公开读者正在复读修订后的题面，报告写入同目录 `public_read_revised_A.md`。

**交接给第2类**：
1. 在 R2E 修订单中登记 `statement_text_replace`，接在 v5 之后；
2. 在新材料版本上重跑预检与正式评分，至少覆盖 gold、noop、CE4、CE1，建议加 CE3；CE 系列要用原补丁；
3. Codex 复核；
4. 准入卡注明：题面改版后，本题只能作“标明版本的自建题”。

**证据**：[evidence/decision_A/](evidence/decision_A/)（五个候选的核对输出与隐藏测试日志）、`evidence/evidence_manifest.json`。
