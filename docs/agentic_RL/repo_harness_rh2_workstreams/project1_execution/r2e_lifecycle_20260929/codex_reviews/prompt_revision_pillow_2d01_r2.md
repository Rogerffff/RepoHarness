你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。这是 pillow `2d01f7d0` 修订的第 2 轮复核，只看这一题。

你上一轮的结论在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/codex_reviews/review_revision_pillow_2d01.md，是"需小改"。要求有三项：
- 第 4 项存储字节断言不要固定 `FillOrder=1`，按文件声明的 FillOrder 归一位序后再比较；删掉"FillOrder=2 不是合理实现"这一无依据排除；
- 补等价实现的正对照；
- P4 维持，措辞不称只改标签的实现"格式不合法 / 标签与数据自相矛盾"。

执行者已改完，材料在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/：
- revision_plan.md；
- revision_draft.json（acceptance 已加 C1FO2）；
- trials/round2/r2_*.json（本轮 9 次试跑）；
- trials/round1/（上一轮方案与草案存档）；
- cands/pillow_2d01_C1FO2.patch（在 C1 基础上，未压缩 `'1'` 路径改用 `'1;IR'` packer 并写 FillOrder=2）。

执行者报告：
- 只动了第 4 项：先读 tag 266（缺省 1），为 2 时把每个字节按位反转，再与原图逐字节取反比较。修订后 `test_1.py` 778 行、sha256 `4beac7f3…`，期望映射不变。
- 试跑结果：gold、C1、C1FO2 都是 1；B 是 0，仍停在字节项（第 473 行）；noop（459）、D（481）、C3（497）、C2（460）、A（457）都是 0。D、C3 的失败点只是随行号下移了 5 行。
- 诊断：C1FO2 在第 1 版草案下是 0（只有 `[1]` 在旧字节断言失败），在当前材料上是 1。

请核：
1. 位序归一是否正确，且不会让 B 或"只改标签不转换数据"的实现过关；
2. C1FO2 是否确为等价实现；
3. 其余措辞要求是否落实。

结论：通过（可落正式修订单）／需再改（写明改什么）。
