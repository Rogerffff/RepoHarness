# V5 accepted provider run path 实现日志

## 目标

本轮目标是补齐一个窄范围真实 provider accepted run 路径，用于后续在冻结任务上执行“真实 provider 修改仓库、严格 final verifier 复放、accepted 后才进入训练导出”的闭环。该日志只记录代码路径和检查防线，尚不声明 V5 core acceptance 通过。

## 实现内容

- 新增 `repo-harness run-v5-accepted-provider-task` 命令，显式接收 task set、provider gate、provider cost budget、输出目录、任务标识、provider、模型、既有 executed run matrix manifest 和预算参数。
- 新增 `run_accepted_provider_task` builder，默认不覆盖既有输出，并写入 command log entry。
- accepted run 使用 `patch_focused_react` scaffold，允许读取、搜索、编辑和查看 diff，但禁用模型可见测试反馈。
- accepted run 的模型可见任务提示明确要求生成持久源码补丁，避免模型把全部 turn 花在分析上；该提示不包含隐藏测试、gold patch 或 verifier 输出。
- `single_shot_patch` accepted run 可以接收来自冻结 source archive 的公开源码片段，帮助无工具 scaffold 生成 unified diff。该片段只来自模型本可读取的仓库源码，不包含 evaluator-only 测试补丁、gold patch 或 verifier 输出。
- final verifier 使用严格复放路径：从冻结源码重新创建 verification workspace，应用 provider 产出的 final patch，再应用 evaluator-only 测试补丁，最后执行冻结 verifier 命令。
- accepted 判定必须同时满足：
  - baseline workspace 成功应用 evaluator-only 测试补丁；
  - baseline verifier 在隐藏测试下失败；
  - final verification workspace 成功应用 provider final patch；
  - final verification workspace 成功应用 evaluator-only 测试补丁；
  - final verifier 退出码为 0 且没有超时；
  - provider final patch 非空；
  - 至少发生 1 次真实 provider API 调用。
- `inspect-v5-run-matrix` 对 `accepted=true` 的 cell 增加一致性检查：必须绑定非空 final patch、final verifier result、final verifier boundary，并要求 boundary、final verifier result 和顶层 accepted 字段一致。final verifier result 必须显式记录 `timed_out=false`，字段缺失、`null` 或 `true` 都不能作为 accepted evidence。
- Stage 4 export pack 只在同一严格 accepted predicate 通过时生成 SFT 和 reinforcement learning rollout trainable records；未通过 final verifier 的真实 provider run 只能进入 failure、diagnostic-only 或 blocked 分区。
- Stage 5 result summary 在存在 accepted run 时优先选择 accepted canonical run，并继续保留 provider-axis supplemental proof 的当前状态说明。

## 主要修改文件

- `src/repo_harness/cli/main.py`
- `src/repo_harness/v5_run_matrix.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/v5_export_pack.py`
- `src/repo_harness/v5_demo_artifacts.py`
- `tests/unit/test_v5_run_matrix.py`
- `tests/unit/test_v5_export_pack.py`

## 新增或更新的命令

- `repo-harness run-v5-accepted-provider-task`

## 新增或更新的测试

- accepted run matrix result 的 final verifier boundary、final verifier result、`exit_code` 和 `timed_out` 篡改负例。
- accepted final verifier run 能生成 SFT 和 reinforcement learning rollout trainable records 的正例。
- 未 accepted 的真实 provider run 仍然不会进入 trainable export 的既有负例。
- Stage 4 在浅层 `accepted=true` 但 final verifier result 不完整时不生成 trainable records 的负例。

## 验证命令

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_v5_run_matrix.py tests/unit/test_v5_export_pack.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_v5_*.py
git diff --check -- src/repo_harness/v5_run_matrix.py src/repo_harness/v5_evidence.py src/repo_harness/v5_export_pack.py src/repo_harness/v5_demo_artifacts.py src/repo_harness/cli/main.py tests/unit/test_v5_run_matrix.py tests/unit/test_v5_export_pack.py
```

## 验证结果

- `compileall src`：通过。
- `tests/unit/test_v5_run_matrix.py tests/unit/test_v5_export_pack.py`：11 passed。
- `tests/unit/test_v5_*.py`：66 passed。
- V5 相关路径 `git diff --check`：通过。

## 正例证据

- 单元测试证明 accepted run result 在 boundary、final verifier result、final patch ref 均一致时，可以通过 `inspect-v5-run-matrix`。
- 单元测试证明 accepted run 可以生成 1 条 SFT record 和 1 条 reinforcement learning rollout record。

## 负例证据

- 篡改 accepted boundary 的 `accepted` 字段后，`inspect-v5-run-matrix --assert-complete` 会失败。
- 篡改 accepted final verifier result 的 `accepted` 字段后，`inspect-v5-run-matrix --assert-complete` 会失败。
- 删除 accepted final verifier result 的 `timed_out` 字段、设置为 `true` 或把 `exit_code` 设置为非 0 后，`inspect-v5-run-matrix --assert-complete` 会失败。
- Stage 4 如果遇到浅层 `accepted=true` 但 final verifier result 不完整的 result，不会生成 SFT 或 reinforcement learning rollout trainable records。
- 未 accepted 的真实 provider run 不会进入 SFT 或 reinforcement learning rollout trainable 分区。

## 允许降级项

- 如果 DeepSeek V4 Flash 或 DeepSeek V4 Pro 因额度、provider 错误、模型未产出补丁或 final verifier 不通过而失败，本轮必须生成 blocked evidence，不得把失败 run 塞进 trainable export。

## 禁止降级项

- 不允许把 final verifier 未接受的 run 标记为 accepted。
- 不允许在 hidden test patch 未成功应用时，把 final verifier 退出码 0 解释为 accepted。
- 不允许把 provider raw request、provider raw response 或 credential raw value 写入模型可见内容、训练 payload、public-safe demo bundle 或最终验收文档。
- 不允许在 V5 源码变更后把旧 V4 doc-sync bundle immutable inspect 当作当前阶段门。

## 实际 provider 执行结果

本轮后续执行了 DeepSeek provider accepted-run 链路：

- DeepSeek V4 Flash 链路烟测目录：`runs/v5-accepted-provider-smoke-deepseek-flash-20260506T114718Z/`。该运行完成真实 provider 调用，但没有产出可接受 final patch，因此没有进入 trainable export。
- DeepSeek V4 Pro 多轮正式尝试目录包括：
  - `runs/v5-accepted-provider-formal-deepseek-pro-20260506T114822Z/`
  - `runs/v5-accepted-provider-formal-deepseek-pro-retry-20260506T115126Z/`
  - `runs/v5-accepted-provider-formal-deepseek-pro-guided-20260506T115710Z/`
  - `runs/v5-accepted-provider-formal-deepseek-pro-single-shot-20260506T120515Z/`
- 最终通过的 accepted run 目录：`runs/v5-accepted-provider-formal-deepseek-pro-single-shot-context-20260506T120930Z/`。

最终 accepted run 的关键事实：

- `provider_id=deepseek`
- `model_id=deepseek-v4-pro`
- `task_id=v5_task_008`
- `scaffold_id=single_shot_patch`
- `accepted=true`
- `final_verifier_ran=true`
- `final_verifier_status=accepted`
- `final_verifier_mode=strict_patch_replay`
- `exit_code=0`
- `timed_out=false`
- `actual_provider_call_count=1`

## 后续导出和验收证据

- Stage 4 accepted export pack：`runs/v5-stage4-export-pack-accepted-20260506T121016Z/v5_export_result_pack_manifest.json`。
- Stage 5 accepted demo artifacts：`runs/v5-stage5-demo-artifacts-accepted-followup-20260506T122627Z/v5_resume_artifact_index.json`。
- Stage 6 accepted final acceptance：`runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_report.json`。

Stage 4 export pack 现在记录：

- `real_provider_trainable_records=2`
- `diagnostic_records=1`
- `blocked_records=1`
- `mock_or_replay_records=0`
- `synthetic_safe_stress_records=0`

## 已知限制

- resume-ready acceptance 仍需要额外的 scaffold comparison、budget comparison 和真实可比较 preference pair。
- OpenAI / DeepSeek provider-axis proof 是补充证据，不能单独覆盖 scaffold、budget 和 preference pair 的缺口。

## 审查结论

只读审查发现 1 个 P1 和 2 个 P2，均已修复：

- P1：hidden test patch 应用失败时仍可能 accepted。修复为 baseline 和 final 的 hidden patch apply 都必须成功。
- P2：inspect 未读取 final verifier result payload。修复为 accepted result 必须校验 final verifier result。
- P2：export 仅信任浅层 accepted flags。修复为 Stage 4 复用严格 accepted predicate。
- P2：final verifier result 的 `timed_out` 字段检查不够严格。修复为必须显式等于 `false`，并补充负例测试。
- P3：failure dataset 和分区说明文字过于固定。修复为根据 strict replay 是否实际运行和 trainable record 数量动态生成说明。

修复后可以进入真实 provider 链路烟测。
