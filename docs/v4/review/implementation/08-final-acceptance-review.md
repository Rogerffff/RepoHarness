# V4 Stage 8 Review: Final Acceptance

## 审查范围

本次审查覆盖 Stage 8 final acceptance builder、acceptance inputs 递归 inspect、acceptance report、acceptance bundle、pre-acceptance command log、post-acceptance documentation boundary 和对应负例测试。

## 审查方式

- Subagent Hegel 执行只读审查，未修改文件。
- 主线程根据 Hegel 的 P2 发现补充负例测试，并重新运行验证。

## 初始发现

- P1：未发现。
- P2：`tests/unit/test_v4_acceptance.py` 缺少 command log failure lineage 负例。
- P2：`tests/unit/test_v4_stage1_skeleton.py` 缺少 acceptance inputs 对 Stage 5 trajectory store 递归失败路径的负例。
- P3：implementation log 引用了本审查记录，审查记录尚未创建。

## 修复记录

- 新增 command log 负例，覆盖空日志、缺少 `schema_version`、缺少 `argv`、缺少 `input_refs`、缺少 `output_refs` 和 command log 内部 artifact ref sha256 不匹配。
- 新增 trajectory store 递归负例，确认 `inspect-v4-inputs --assert-complete` 会调用 Stage 5 trajectory store inspect，并拒绝损坏的 `trajectory_store_integrity_report.json`。
- 创建本审查记录，补齐 Stage 8 implementation log 的审查追踪目标。

## 修复后验证

- `PATH=.venv/bin:$PATH python -m compileall src` 通过。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_acceptance.py tests/unit/test_v4_stage1_skeleton.py -q` 通过，31 个测试通过。
- `PATH=.venv/bin:$PATH python -m pytest -q` 通过，659 个测试通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete` 通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete` 通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable` 通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T162105Z/v4_acceptance_inputs.json --assert-complete` 通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-20260504T162105Z/acceptance/v4_acceptance_report.json --assert-complete` 通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T162105Z/acceptance/acceptance_bundle_manifest.json --assert-immutable` 通过。

## 最终复审

Subagent Pasteur 对修复后的 Stage 8 执行最终只读复审，结论是未发现仍需修复的 P1 或 P2，post-acceptance documentation 只绑定在 acceptance bundle 的 `documentation_refs` 中，没有进入 `v4_acceptance_inputs.json` 或 `v4_acceptance_report.json` 输入集合。

## 最终结论

P1 和 P2 均已修复。Stage 8 已通过最终验收重跑，可以提交。
