**结论：97997d2c、ea6906b0 通过，可落正式修订单；5dbbe143 的 R-c 可单独通过，P5 决定包需小改，题面修订继续待用户决定。**

全程只读。我在内存中应用了草案、核对父版本和 expected，并用正式解析器重新解析 **24 份试跑日志**，结果与记录一致；没有重跑容器。

## 1. `97997d2c`：通过

1. **模板与依据成立。** 三处 R-c 分别针对配置对象读写、`combine()` 实际生效、非空配置的读取与替换，范围明确。
   - 插件确实可能收到 `CoverageConfig`：[control.py:270](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266/worktree/coverage/control.py:270)。
   - `[paths]` 用于合并时的路径映射：[config.rst:223](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266/worktree/doc/config.rst:223)。
   - **支持保留替换断言。** 主要依据是公开 `set_option` 契约的 “new value”，以及既有选项整体赋值的语义：[control.py:384](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266/worktree/coverage/control.py:384)、[config.py:421](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266/worktree/coverage/config.py:421)。第 27 行的 “updated…containing” 与合并相容，但没有要求保留旧项，不足以构成另一条肯定性契约。
   - **证据表述需收紧：**题面第 23 行的示例从空映射开始，单独不能区分两者；插件“取出后修改再 set”的样例也不是替换的决定性证据。本结论不依赖后来版本。

2. **试跑支持验收方向。** gold、A1 均为 1（47/47）；noop 为 0；W1、W2、M 分别只失败于对应新增键；N1 仍为 0。原 44 键未变，没有 missing／unexpected。

3. **未扩大需求或保 gold 放宽。** 新断言来自公开契约，不规定存储位置、对象身份或具体实现；`combine()` 检查的是行为，不是内部属性。未改题面，无新增泄漏。

4. **通过，可落正式修订单。** 不必采用 §2.3 退路；最终材料仍需正式评分复验。

## 2. `ea6906b0`：通过

1. **两处 R-c 用对。**
   - 真正忽略报告文件直接来自[题面第 26 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/user_prompt.txt:26)。
   - 搬入的方法与公开[旧测试第 1843–1848 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/worktree/tests/test_coverage.py:1843)**逐字一致**，没有趁搬迁改变要求。
   - 原 mock 测试没有被替换，因此不是 R-e。

2. **试跑支持验收方向。** gold、C-A 为 1（48/48）；noop 为 0；C-B、RE 从旧正式评分的 1 变为试跑的 0，各只失败于对应新增键。C-C 仍失败于原来的 7 个替身约束键，两个新键通过。
   - **C-B 的具体失败原因仍是推断：**留存日志只有失败摘要，没有完整断言现场。补丁差异和同环境 gold 成功支持该推断，但正式评分应保存完整日志确认。

3. **git 依赖合理，但尚未正式验收。** 这是实现题面行为判定的评分侧工具，符合 v1 §6；不需网络或提交身份。测试在评分用户创建的临时仓库中执行，不依赖 `/testbed` 的属主。正式候选执行继承镜像环境，但 HOME、权限布置与试跑不完全相同，仍须以 **uid 54322、正式 profile** 验证。不能用 root 能执行 git 代替这一步。

4. **通过，可落正式修订单。** 未钉死 `.gitignore` 内容，未删改原断言，也没有复制 gold 文本作为期望。正式复验至少覆盖 gold、noop、C-B、RE。

## 3. `5dbbe143`：R-c 单独通过；P5 包需小改

1. **决定包总体公允，P5 判断成立。**
   - 按 slug 的线索真实存在：[抑制逻辑与说明](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/worktree/coverage/control.py:336)。
   - 按具体消息／对象去重也有公开先例：[按文件去重](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/worktree/coverage/inorout.py:345)；题面没有给出示例的期望输出。
   - 推荐 A 可以基于来源意图、改动成本；**不能据此称按消息实现违反当前公开要求。** A、B 都仍是用户选择任务目标，不属于预授权 R-f 自行裁定。

2. **独立 R-c 的证据充分。** 输入同时采用不同 slug、不同消息，两种读法下首次输出都应保留。gold、CE3 为 1（76/76）；noop 为 0；CE4 从 1 变为 0；CE1 **通过新增键，仅失败于原争议键**，证明新断言没有暗中选择去重语义。它验证的是“两条不同警告首次均输出”，不是所有去重行为。

3. **边界成立。** R-c 没有扩大需求、放宽原测试或照抄 gold。A 的题面草稿也没有泄漏实现或新增隐藏测试输入，但须等 P5 选择后，再做新公开读者验收。CE1 当前不能列为“已确认错误候选”。

4. **处置：**
   - **R-c 可先单独落正式修订单**：只纳入测试修订及对应 expected，不把草案中的 `statement_edits` 一并定稿；整题仍保持 P5 待决，不能因此标为可进探针。
   - **决定包小改一处事实：**[plan 第 81、161 行](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/revision_plan.md:81)所述“题面修订机制尚待实现／复核”已过时；[本批机制复核已通过](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/codex_reviews/review_code_A_B_20260929.md:32)。更新成本和剩余条件即可，具体题面验收仍未完成。

**共同限制：**以上“通过”是允许草案进入正式材料落地，不是正式评分或探针准入通过。三题均以 gold 作正对照，无需援引替代解例外；最终仍需绑定修订单、pins、测试摘要和镜像身份，在正式评分路径确认正负对照及本次触发反例。