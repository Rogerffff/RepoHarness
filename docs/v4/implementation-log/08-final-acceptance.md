# V4 Stage 8: Final Acceptance

## 目标

阶段 8 的目标是生成 V4 final acceptance run selection manifest、acceptance inputs、acceptance report、acceptance command log 和 acceptance bundle，并在 acceptance report 通过后生成 post-acceptance 文档。

## 实现内容

- 新增 `repo-harness build-v4-run-selection-manifest`。
- 新增 `repo-harness build-v4-acceptance-inputs`。
- 新增 `repo-harness build-v4-acceptance-report`。
- 新增 `repo-harness build-v4-acceptance-bundle`。
- 增强 `inspect-v4-acceptance`，检查 accepted task count、PR / issue task count、final verifier authority、trainable payload contamination status、evaluator-only visibility boundary 和 V4 command log。
- 增强 `inspect-acceptance-bundle` 对 V4 bundle 的传递复核，要求 post-acceptance documentation refs 不作为 acceptance report 输入。
- acceptance report 构建时会重新调用 V2、V3 和 V4 各阶段 inspect，生成 role status 和 role evidence refs。
- `inspect-v4-inputs --assert-complete` 会递归复核 V2 acceptance、V3 acceptance、V3 acceptance bundle、implementation inputs、command log、pre-acceptance docs、Stage 2 到 Stage 7 机器产物和 Stage 5 trajectory store。
- Stage 8 的 run selection manifest、acceptance inputs、acceptance report 和 acceptance bundle 构建命令默认拒绝覆盖旧 evidence。

## 主要修改文件

- `src/repo_harness/v4_acceptance.py`
- `src/repo_harness/v4_stage1.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v4_acceptance.py`
- `tests/unit/test_v4_stage1_skeleton.py`
- `docs/v4/final-acceptance.md`
- `docs/v4/walkthrough.md`

## 机器产物

Final acceptance run：

- `runs/v4-final-rerun-20260504T162105Z/v4_query_spec.json`
- `runs/v4-final-rerun-20260504T162105Z/run_selection_manifest.json`
- `runs/v4-final-rerun-20260504T162105Z/v4_acceptance_inputs.json`
- `runs/v4-final-rerun-20260504T162105Z/acceptance/v4_acceptance_report.json`
- `runs/v4-final-rerun-20260504T162105Z/acceptance/acceptance_command_log.jsonl`
- `runs/v4-final-rerun-20260504T162105Z/acceptance/acceptance_bundle_manifest.json`

Pre-acceptance evidence：

- `runs/v4-pre-acceptance-evidence-20260504T162105Z/pre_acceptance_command_log.jsonl`
- `runs/v4-pre-acceptance-evidence-20260504T162105Z/compileall.stdout.txt`
- `runs/v4-pre-acceptance-evidence-20260504T162105Z/stage8_targeted.stdout.txt`
- `runs/v4-pre-acceptance-evidence-20260504T162105Z/full_pytest.stdout.txt`
- `runs/v4-pre-acceptance-evidence-20260504T162105Z/v2_regression.stdout.txt`
- `runs/v4-pre-acceptance-evidence-20260504T162105Z/v3_acceptance.stdout.txt`
- `runs/v4-pre-acceptance-evidence-20260504T162105Z/v3_bundle.stdout.txt`

Post-acceptance documentation：

- `docs/v4/final-acceptance.md`
- `docs/v4/walkthrough.md`

## 验证命令

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_acceptance.py tests/unit/test_v4_stage1_skeleton.py -q`
- `PATH=.venv/bin:$PATH python -m pytest -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T162105Z/v4_acceptance_inputs.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-20260504T162105Z/acceptance/v4_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T162105Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`

## 验证结果

- Compileall 通过。
- Stage 8 定向测试通过，31 个测试通过。
- Full pytest 通过，659 个测试通过。
- V2 regression inspect 通过。
- V3 acceptance inspect 通过。
- V3 acceptance bundle immutable inspect 通过。
- V4 acceptance inputs inspect 通过。
- V4 acceptance report inspect 通过。
- V4 acceptance bundle immutable inspect 通过。

## 正例证据

- `v4_acceptance_inputs.json` 显式绑定 24 个输入类别。
- `v4_acceptance_report.json` status 为 passed。
- `v4_acceptance_report.json` 记录 8 个 accepted / auditable task definitions。
- `v4_acceptance_report.json` 记录 8 个 PR / issue accepted / auditable task definitions。
- `acceptance_command_log.jsonl` 绑定 full pytest、V2 regression、V3 acceptance、V3 bundle 和 report build evidence。
- `acceptance_bundle_manifest.json` 绑定 post-acceptance documentation refs，并传递复核 V4 acceptance report。

## 负例证据

测试覆盖以下失败场景：

- run selection query 绑定报告类产物路径。
- acceptance inputs 缺少 contamination scan。
- acceptance report 目标 acceptance directory 已存在。
- post-acceptance documentation 被误作为 acceptance report 输入。
- contamination scan report 缺少 card claim policy。
- contamination scan report 标记 clean 但仍包含 findings。

## 允许降级项

没有使用允许降级项。

## 禁止降级项

- 不允许 Stage 8 builder 覆盖旧 run selection manifest、acceptance inputs、report、bundle 或 command log evidence。
- 不允许 latest run 自动选择。
- 不允许 post-acceptance documentation 作为 acceptance report 输入。
- 不允许把 final verifier 以外的诊断信号提升为 accepted 主事实。

## 已知限制

- V4 仍然是单机优先实现，未实现分布式 rollout 集群。
- 本阶段只保留 provider / scaffold / budget matrix 相关元数据，不实现完整评测矩阵。
- 本阶段不实现 context strategy / project context / session continuation。

## 是否偏离设计文档

没有偏离。Stage 8 按 V4 implementation plan 生成 final acceptance report 和 acceptance bundle，post-acceptance 文档只在 `inspect-v4-acceptance --assert-complete` 通过后生成。

## Subagent 或等价自审结论

Stage 8 最终复审记录见 `docs/v4/review/implementation/08-final-acceptance-review.md`。

## 是否可以结束 V4

最终复审通过后，V4 可以视为完成。
