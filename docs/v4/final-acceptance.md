# RepoHarness V4 Final Acceptance

## 验收结论

RepoHarness V4 final acceptance 已通过。

最终验收报告：

- `runs/v4-final-rerun-20260504T162105Z/acceptance/v4_acceptance_report.json`

最终验收输入：

- `runs/v4-final-rerun-20260504T162105Z/v4_acceptance_inputs.json`

最终验收 bundle：

- `runs/v4-final-rerun-20260504T162105Z/acceptance/acceptance_bundle_manifest.json`

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
- V4 acceptance bundle immutable inspect 通过。
- V4 accepted / auditable task definitions 数量为 8。
- V4 PR / issue accepted / auditable task definitions 数量为 8。
- Trainable payload contamination status 为 clean。
- Evaluator-only evidence 没有进入模型可见上下文。
- Final verifier authority 被保留为 accepted / rejected / inconclusive 的主事实来源。

## 验证命令

主要验证命令包括：

- `PATH=.venv/bin:$PATH python -m pytest -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T162105Z/v4_acceptance_inputs.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-20260504T162105Z/acceptance/v4_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T162105Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`

## 边界声明

V4 是单机优先的 RepoHarness trajectory production 和 audit upgrade，不是公开榜单复现、生产安全隔离系统、分布式训练系统、完整产品复刻或模型训练成果声明。
