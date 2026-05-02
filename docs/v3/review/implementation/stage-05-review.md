# V3 Stage 05 Implementation Review

## 审查范围

本审查覆盖阶段 5 的固定 source archive / mirror materialization、`source_checkout_facts.json`、`source_materialization_report.json`、verifier workspace patch apply 和 agent workspace contamination 检查。

本审查不覆盖阶段 6 final verifier、fail-to-pass / pass-to-pass test execution，也不把当前 verifier workspace preparation 表述为 SWE-Bench-like final result。

## 本地自审

本地自审检查：

- 正式 materialization 是否只读取固定本地 archive / mirror。
- `source_checkout_facts.json` 和 `source_materialization_report.json` 是否存在并可 inspect。
- SWE-Bench-like `test_patch` 是否只写入 evaluator-only patch artifact 和 verifier workspace。
- agent workspace 是否保持 base source hash。
- verifier workspace patch apply 是否通过 workspace hash 变化验证，而不只看 `git apply` exit code。

## 自审发现和修复

### P2：`git apply` 向上发现父仓库导致 patch 未进入 verifier workspace

初版在 `runs/` 子目录执行 `git apply`，Git 会向上发现 RepoHarness 自身 `.git`。命令返回成功，但 verifier workspace source hash 没有变化。

修复：patch apply 使用 `GIT_CEILING_DIRECTORIES` 限定 Git discovery；inspect 要求 SWE-Bench-like verifier workspace hash 不等于 base source hash。

### P1：source hash 未绑定固定 provenance

只读子代理 `Franklin` 指出，初版 builder 和 inspect 只证明 materialized workspace、report 和 checkout facts 自洽，没有把实际 `source_tree_hash` 反查到阶段 4 真实仓库 source facts、固定本地 mirror 的 `mirror_sha256`，或者 SWE-Bench-like source archive manifest 中声明的 `source_tree_hash`。

修复：builder 为每个 task 写入 per-task `source_provenance.json`，并要求 materialized `source_tree_hash` 与 `expected_source_tree_hash` 一致。真实仓库 task 绑定阶段 4 source facts，SWE-Bench-like task 绑定 source archive manifest。inspect 重新读取 `source_provenance_ref`、`source_checkout_facts_ref` 和 workspace refs，交叉校验 `source_tree_hash`、`expected_source_tree_hash`、`base_commit`、`resolved_commit`、`remote_url`、`archive_sha256` 或 `mirror_sha256`。

负例：`tests/unit/test_v3_source_materialization.py` 覆盖 source archive manifest `source_tree_hash` 漂移和真实仓库 source facts `source_tree_hash` 漂移。

### P2：source_checkout_facts/report 字段不完整

只读子代理 `Franklin` 指出，初版根级 `source_checkout_facts.json` 和 report entry 缺少 remote URL 或 mirror source、resolved commit、mirror sha256 和 materialization command facts。

修复：`SourceCheckoutFacts` 增加 `remote_url`、`mirror_source`、`resolved_commit`、`mirror_sha256` 和 `materialization_command_facts` 字段；materialization 记录固定 archive extract 或 fixed mirror copy 的结构化 command facts，且明确 `network_used=false`、输入输出路径已 redacted。report entry 和根级 manifest 也记录关键 provenance 字段。

### P2：contamination inspect 主要信任报告自述

只读子代理 `Franklin` 指出，初版 inspect 只检查 `agent_workspace_contains_verifier_patch` 布尔值，没有重新读取 evaluator-only verifier patch 并扫描实际 agent workspace 或 task definition。

修复：inspect 重新读取 `verifier_patch_ref`，过滤 base source 中原本存在的普通代码片段后扫描 agent workspace；task definition 扫描 raw patch / diff header 级别的泄漏标记。新增负例会向 agent workspace 写入 verifier patch 片段，并要求 inspect 拒绝。

## 负例覆盖

已有单元测试覆盖：

- 浮动网络 source 拒绝。
- source archive sha256 mismatch 拒绝。
- source archive manifest `source_tree_hash` mismatch 拒绝。
- 真实仓库 source facts `source_tree_hash` mismatch 拒绝。
- report 自述 agent workspace contamination 拒绝。
- agent workspace 真实 verifier patch 片段污染拒绝。
- verifier workspace 未体现 patch 变更拒绝。

## 子代理审查

只读子代理 `Franklin` 首轮审查发现：

- P1：source hash 未绑定固定 provenance。
- P2：source_checkout_facts/report 字段不完整。
- P2：contamination inspect 主要信任报告自述。

上述发现均已修复。修复后 `Franklin` 对当前工作区做了只读复审，结论为 P1 无、P2 无、P3 无。

复审确认：

- 上次 P1“source hash 未绑定固定 provenance”已关闭。
- 上次 P2“source_checkout_facts/report 字段不完整”已关闭。
- 上次 P2“contamination inspect 主要信任报告自述”已关闭。
- 未发现阶段 6 final verifier 越界实现；当前范围没有 `SweBenchLikeVerifierPlan`、`final_verifier_result.json`、`FAIL_TO_PASS` / `PASS_TO_PASS` 解析执行或 final verifier 逻辑。
- 正式 materialization 路径保持固定本地 archive 或 fixed local mirror，未发现网络 clone、fetch 或 pull 路径。

## 结论

当前本地自审和 `Franklin` 复审均未发现剩余 P1/P2/P3 阻断项。阶段 5 允许进入阶段 6。
