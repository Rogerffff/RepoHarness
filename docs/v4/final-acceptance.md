# RepoHarness V4 Final Acceptance

## 验收结论

RepoHarness V4 final acceptance 已通过。本文已同步到修复复核问题后重新生成的最终验收证据。

最终验收报告：

- `runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json`

最终验收输入：

- `runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json`

最终验收 bundle，原始 implementation closure 版本：

- `runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest.json`

最终验收 bundle，本轮文档同步后可复核版本：

- `runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json`

最终验收命令日志，原始 implementation closure 版本：

- `runs/v4-final-rerun-20260504T194758Z/acceptance/final_acceptance_command_log.jsonl`

最终验收命令日志，本轮文档同步版本：

- `runs/v4-final-rerun-20260504T194758Z/acceptance/final_acceptance_command_log_doc_sync_20260505T075410Z.jsonl`

预验收命令日志：

- `runs/v4-pre-acceptance-evidence-20260504T192620Z/pre_acceptance_command_log.jsonl`

## 验收范围

本次 V4 验收覆盖以下主线：

- Stage 0：基线确认和 implementation inputs freeze。
- Stage 1：V4 schema、inspect 命令和 acceptance skeleton。
- Stage 2：task source freeze 和 task adapter integration。
- Stage 3：单机 rollout queue、lease、retry、resource lock、budget control、resource usage、batch resume 和 run selection query。
- Stage 4：audit-only permission、tool lifecycle、hook 和 MCP policy evidence。
- Stage 5：agent run integration、RunSpec metadata、prepared messages binding、final verifier boundary 和 trajectory store。
- Stage 6：export quality、trajectory packing、failure dataset、reward audit、patch quality 和 preference pair trainability。
- Stage 7：dataset card、run card、export card、provenance summary、contamination summary 和 repro command index。
- Stage 8：final acceptance report、acceptance command log 和 acceptance bundle。

## 关键结果

- V2 regression inspect 通过。
- V3 acceptance inspect 通过。
- V3 acceptance bundle immutable inspect 通过。
- V4 acceptance inputs inspect 通过。
- V4 acceptance report inspect 通过。
- V4 acceptance bundle immutable inspect 通过；本轮文档同步后生成的 bundle 也已经通过 immutable inspect。
- V4 accepted / auditable task definitions 数量为 8。
- V4 PR / issue accepted / auditable task definitions 数量为 8。
- Trainable payload contamination status 为 clean。
- Evaluator-only evidence 没有进入模型可见上下文。
- Final verifier authority 被保留为 accepted / rejected / inconclusive 的主事实来源。
- 完整测试结果为 `712 passed`。
- 针对 V4 修复点的定向测试结果为 `125 passed`。
- 复核中发现的 command log 绑定、reward audit schema、structured reward allowlist、preference pair 可比较性、独立 regression evidence 和 implementation log index 问题已经在最新 evidence 中收口。

## 验证命令

主要验证命令包括：

- `PATH=.venv/bin:$PATH python -m pytest -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json --assert-immutable`

## 历史验收路径说明

`runs/v4-final-rerun-20260504T162105Z/` 是 V4 早期最终验收目录。后续复核发现若干检查器和 evidence 绑定缺口，已经通过后续修复提交和 `runs/v4-final-rerun-20260504T194758Z/` 下的新 acceptance evidence 收口。因此，引用 V4 最新通过状态时，应使用 `194758Z` 目录。

`acceptance_bundle_manifest.json` 是 implementation closure 时生成的原始 bundle。由于本文件和 `docs/v4/walkthrough.md` 属于 post-acceptance documentation refs，文档同步会改变它们的 sha256。为了让当前文档版本也能被不可变检查覆盖，本轮额外生成了 `acceptance_bundle_manifest_doc_sync_20260505T075410Z.json`。当前阅读文档后复核 V4 bundle 时，应优先使用这个文档同步 bundle。

## 边界声明

V4 是单机优先的 RepoHarness trajectory production 和 audit upgrade，不是公开榜单复现、生产安全隔离系统、分布式训练系统、完整产品复刻或模型训练成果声明。
