# V4 Stage 6: Export Quality

## 目标

阶段 6 的目标是实现 P0-3 export quality、trajectory packing、failure dataset、reward audit、reward hacking risk、patch quality、test-overfitting risk 和 preference pair trainability 的机器证据与强 inspect。阶段 6 不训练 reward model，不实现强化学习算法，也不把 reward audit 结果提升为 final verifier 结果。

## 实现内容

- 新增 `repo-harness build-v4-export-quality`。
- 新增 `inspect-v4-export-quality --assert-complete` 强检查器。
- 生成 `trajectory_quality_manifest.json`，绑定统一 V4 denylist version、denylist sha256、allowlist policy version、Stage 5 trajectory store 和所有 Stage 6 报告。
- 生成 `sample_tier_manifest.json`，明确区分 outcome tier 和 trainability status。
- 生成 `failure_dataset.jsonl`，绑定 run、task、turn、tool call、workspace state、final verifier result ref、failure category、failure source component 和 evidence ref。
- 生成 `packing_manifest.json`，要求 packed sample 回指 original trajectory ref。
- 生成 `reward_audit_report.json`，只允许 audit-only RewardMetadata 和 structured reward，并强制 `model_visible=false`。
- 生成 `reward_hacking_risk_audit_report.json`，保留 final verifier authority，禁止 reward 提升 verifier rejected 样本。
- 生成 `patch_quality_report.json`，记录文件数、行数、测试文件比例、生成文件改动、重复改动和无关改动风险。
- 生成 `test_overfitting_risk_audit_report.json`，覆盖只改测试、删除 verifier path、硬编码 hidden selector、删除失败断言、读取 evaluator-only evidence、verifier bypass 和修改 verifier 配置。
- 生成 `preference_pair_trainability_report.json` 和 `blocked_pair_report.json`，要求 trainable pair 与 blocked pair 的计数、样本、可比范围和 blocked reason 可审计。
- 为 SFT、reinforcement learning rollout 和 preference export 生成 valid fixture 与 negative fixture。

## 主要修改文件

- `src/repo_harness/v4_export_quality.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v4_export_quality.py`

## 机器产物

目录：`docs/v4/evidence/export-quality/`

- `trajectory_quality_manifest.json`
- `sample_tier_manifest.json`
- `failure_dataset.jsonl`
- `packing_manifest.json`
- `reward_audit_report.json`
- `reward_hacking_risk_audit_report.json`
- `patch_quality_report.json`
- `test_overfitting_risk_audit_report.json`
- `preference_pair_trainability_report.json`
- `blocked_pair_report.json`
- `fixtures/sft_valid.jsonl`
- `fixtures/sft_negative.jsonl`
- `fixtures/rl_valid.jsonl`
- `fixtures/rl_negative.jsonl`
- `fixtures/preference_valid.jsonl`
- `fixtures/preference_negative.jsonl`

## 验证命令

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH repo-harness build-v4-export-quality --output-dir docs/v4/evidence/export-quality --agent-run-integration docs/v4/evidence/agent-run-integration`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-export-quality docs/v4/evidence/export-quality --assert-complete`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_export_quality.py tests/unit/test_v4_agent_run.py tests/unit/test_v4_stage1_skeleton.py -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`

## 验证结果

- Compileall 通过。
- 阶段 6 build 通过。
- `inspect-v4-export-quality --assert-complete` 通过。
- 阶段 6、阶段 5 和阶段 1 组合单元测试通过。
- V2 acceptance inspect 通过。
- V3 acceptance inspect 通过。
- V3 acceptance bundle immutable inspect 通过。

## 正例证据

- `sample_tier_manifest.json` 中 outcome tier 与 final verifier result 强绑定，trainability status 单独记录。
- trainable payload 污染扫描 clean，不包含 reward scalar、reward label 或 hidden selector。
- `reward_audit_report.json` 中 RewardMetadata 与 structured reward 都是 audit-only，`model_visible=false`。
- `failure_dataset.jsonl` 具有 task、run、turn、tool、workspace、final verifier、failure category 和 evidence 绑定。
- `packing_manifest.json` 中每个 packed sample 都保留 original trajectory ref。
- `preference_pair_trainability_report.json` 至少包含一个合规 trainable pair，同时 `blocked_pair_report.json` 明确记录 blocked pair 的 warning、原因、数量、拒绝分布和下一步修复入口。

## 负例证据

测试覆盖以下失败场景：

- reward scalar 或 reward label 出现在 trainable target。
- hidden selector 出现在 trainable payload。
- packed sample 缺失 original trajectory ref。
- verifier rejected 样本被 reward audit 改成 accepted。
- outcome tier 与 trainability status 混用。
- outcome tier 与 final verifier result 不一致。
- RewardMetadata 缺少 version / formula / invalid_for_training。
- RewardMetadata 或 structured reward `model_visible=true`。
- failure dataset 缺少 run、task、turn、tool、workspace、final verifier 或 failure category 绑定。
- 任一 export 格式缺少 negative fixture。
- test-overfitting 风险未 flagged 或未 export_blocked。
- verifier / overfitting 风险缺失。
- excessive patch 被当作 accepted 主事实或 reward 主事实。
- patch quality metrics 缺失。
- blocked pair report 静默吞掉 warning、数量或拒绝原因分布。
- trainable preference pair 的 chosen / rejected 样本、baseline_blocked 或 compare_scope 不合法。
- preference pair count 与记录不一致。
- no trainable pair 时缺少 `no_trainable_preference_pair` 口径。
- `--fail-if-output-exists` 防覆盖。

## 允许降级项

- 阶段 6 的 preference pair 使用小型 deterministic fixture 证明 schema、分流和阻塞报告行为，不声称已经完成大规模偏好数据生产。
- reward audit 仅作为诊断、过滤、分层和人工审查辅助，不替代 final verifier。

## 禁止降级项

- 不允许 reward scalar 或 reward label 进入模型可见文本、assistant target、SFT target、preference target 或 trainable payload。
- 不允许 hidden selector、evaluator-only evidence 或 verifier raw output 进入 trainable payload。
- 不允许 final verifier rejected 样本被 reward audit 提升为 accepted。
- 不允许 outcome tier 和 trainability status 混用。
- 不允许 excessive patch 成为 accepted 主事实或 reward 主事实。
- 不允许 preference pair baseline blocked 或 no trainable pair 被静默吞掉。

## 已知限制

- 阶段 6 不训练 coding agent，不训练 reward model，也不实现强化学习训练算法。
- 阶段 6 不扩大为完整 public leaderboard export，只提供 V4 final acceptance 需要的审计与导出质量证据。

## 是否偏离设计文档

没有偏离。阶段 6 保持在 P0-3 export quality、trajectory packing、failure dataset、reward audit 和 preference pair trainability 范围内，没有把 reward audit 变成 final verifier，也没有新增本阶段明确排除的训练系统。

## Subagent 或等价自审结论

阶段 6 初轮只读审查发现三个 P1、三个 P2 和两个 P3：outcome tier 未与 final verifier result 强绑定、preference pair trainability 检查不足、failure dataset 缺少 run 和 failure category、patch quality metrics 太薄、test-overfitting 风险缺 verifier bypass 和修改 verifier 配置、blocked pair 的 no-trainable 口径不够明确、reward label 与 reward visibility 负例不足。上述问题均已修复并补充负例。复审未发现 P1/P2/P3，结论为允许进入阶段 7。

## 是否可以进入下一阶段

可以进入阶段 7。
