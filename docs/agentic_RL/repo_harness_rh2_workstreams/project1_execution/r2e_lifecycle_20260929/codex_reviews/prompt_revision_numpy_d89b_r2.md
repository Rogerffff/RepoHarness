你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。这是 numpy `d89bc4bb` 修订的第 2 轮复核，只看这一题。

你上一轮的结论在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/codex_reviews/review_revision_numpy_d89b.md，是"需小改"。要求有三项：
- R-c2 两处告警过滤改为 `sup.filter(Warning)`，只限两个 `normed` 调用的上下文；
- R-c3 标为"公开先例推知"；
- "挡住所有语义错误"收窄为"挡住所列错误候选"。

执行者已改完，材料在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/：
- revision_plan.md（§5.5 是本轮复验与不重跑的理由）；
- revision_draft.json（`revisions` 换成第 2 轮草案，修订后文件摘要已同步；期望仍是 84 键）；
- trials/rev2_*.json（本轮 5 次试跑）与 trials/ctrl_draft1_DEPUW.json（对照）；
- cands/numpy_d89b_DEPUW.patch（新候选：用不带类别的 `warnings.warn` 弃用 `normed`）。

本轮试跑（试跑工具，不是正式评分）：
- gold 1（84/84），DEP 1，DEPFW 1，DEPUW 1；
- REN 0，仍在两个 `normed` 键因 `TypeError` 失败；
- 对照：DEPUW 在第 1 轮四类名单草案下得 0，报 UserWarning 被当成错误。
- noop、DEG、D1、ORD、C1 没有重跑。执行者的理由：这五个补丁与 base 的 `normed` 路径都不发告警，只改过滤块影响不到它们，它们失败的键都在未改的测试里。

请核：
1. 改动是否只限这两个过滤块，其余测试逐字节未变；修订后文件摘要与草案是否一致；
2. 不重跑那五个候选的理由是否成立；
3. 三项要求是否都已落实。

结论：通过（可落正式修订单）／需再改（写明改什么）。
