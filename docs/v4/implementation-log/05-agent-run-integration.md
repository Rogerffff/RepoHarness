# V4 Stage 5: Agent Run Integration

## 目标

阶段 5 的目标是在不实现完整 provider / scaffold / budget matrix 的前提下，把 V4 run 的 RunSpec 元数据、P0 task provenance / visibility 元数据、prepared messages 绑定、final verifier 单向边界、interrupted / crashed run 可读性和 trajectory store 完整性固定为可审计机器产物。

## 实现内容

- 新增 `repo-harness build-v4-agent-run-integration`。
- 新增强检查器 `inspect-v4-agent-run-integration --assert-complete`。
- 新增强检查器 `inspect-v4-trajectory-store --assert-readable`。
- 生成 completed、interrupted、crashed 三类 run fixture，并为每个实际启动 run 写入 `transcript.jsonl`、`events.jsonl`、`artifacts.json` 和 `run_config_facts.json`。
- completed run 额外写入 `run_metadata.json` 和 `final.patch`。
- interrupted / crashed run 分别写入 `interrupted_run_facts.json` 和 `crash_facts.json`。
- 在 `v4_agent_run_integration_report.json` 中显式绑定阶段 2 task freeze / generated task definition / environment stability 或 Docker facts、阶段 3 rollout queue、阶段 4 tool contract / permission decision trace / tool lifecycle trace。
- 在 prepared messages binding 中绑定 `prepared_messages_ref`、`prepared_messages_sha256`、`model_input_hash`、`tool_schema_snapshot_hash`、`content_replacement_state_hash`、`context_revision`、`tool_observation_ref` 和 `observation_source_event_ref`。
- final verifier boundary 明确记录 strict final verifier 支持、formal verifier 在 agent 停止后运行、debug verifier mode 不能作为 acceptance 口径，以及 final verifier result 不进入 model-visible observation。
- trajectory store integrity 检查 ArtifactRef 可解析性、sha256、size_bytes、relative path、redaction status、retention policy、stable record_id / event_id、events offset、transcript offset、RunRecorder 幂等、半写 artifact 标记、finalize 重入和 crash-readable 状态。

## 主要修改文件

- `src/repo_harness/v4_agent_run.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/v4_stage1.py`
- `tests/unit/test_v4_agent_run.py`
- `tests/unit/test_v4_stage1_skeleton.py`

## 机器产物

目录：`docs/v4/evidence/agent-run-integration/`

- `v4_agent_run_integration_report.json`
- `runspec_metadata_report.json`
- `final_verifier_boundary_report.json`
- `prepared_messages_binding_report.json`
- `interrupted_run_recovery_report.json`
- `trajectory_store_integrity_report.json`
- `runs/v4-run-completed-001/transcript.jsonl`
- `runs/v4-run-completed-001/events.jsonl`
- `runs/v4-run-completed-001/artifacts.json`
- `runs/v4-run-completed-001/run_config_facts.json`
- `runs/v4-run-completed-001/run_metadata.json`
- `runs/v4-run-completed-001/final.patch`
- `runs/v4-run-interrupted-001/interrupted_run_facts.json`
- `runs/v4-run-crashed-001/crash_facts.json`

## 验证命令

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH repo-harness build-v4-agent-run-integration --output-dir docs/v4/evidence/agent-run-integration --task-freeze docs/v4/evidence/task-source-freeze/task_freeze_manifest.json --tool-lifecycle docs/v4/evidence/tool-lifecycle --rollout-queue docs/v4/evidence/rollout-orchestration/rollout_queue_manifest.json`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-agent-run-integration docs/v4/evidence/agent-run-integration --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-trajectory-store docs/v4/evidence/agent-run-integration --assert-readable`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_agent_run.py tests/unit/test_v4_stage1_skeleton.py tests/unit/test_v4_tool_lifecycle.py -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`

## 验证结果

- Compileall 通过。
- 阶段 5 build 通过。
- `inspect-v4-agent-run-integration --assert-complete` 通过。
- `inspect-v4-trajectory-store --assert-readable` 通过。
- 阶段 5、阶段 1 追踪表和阶段 4 组合单元测试通过。
- V2 acceptance inspect 通过。
- V3 acceptance inspect 通过。
- V3 acceptance bundle immutable inspect 通过。

## 正例证据

- `runspec_metadata_report.json` 为每个 run 保留 `provider_id`、`provider_mode`、`model_id`、`scaffold_id`、`budget_policy_id`、`fallback_policy_id`、`token_usage`、`provider_error_category`、`tool_policy_id`、`verifier_id`、`environment_id`、`task_source_tag`、`task_family` 和 `task_visibility_policy_id`。
- `v4_agent_run_integration_report.json` 显式绑定阶段 2、阶段 3 和阶段 4 输入，不读取 latest run 或隐式目录。
- `prepared_messages_binding_report.json` 的 `tool_schema_snapshot_hash` 必须与阶段 4 tool contract 中的 `tool_schema_hash` 一致。
- final verifier result 只出现在非模型可见 final verifier boundary / run metadata 中，不进入 transcript、events、prepared messages、tool observation 或 model-visible artifact。
- interrupted / crashed run 保留可读 transcript、events、artifacts、run config facts 和结构化失败事实。

## 负例证据

测试覆盖以下失败场景：

- final verifier result 出现在 model-visible events 或 tool observation artifact。
- RunSpec 缺少 `scaffold_id`、`tool_policy_id`、`verifier_id` 或 `environment_id`。
- provider fallback success 缺少 fallback policy ref。
- ArtifactRef sha256 不匹配。
- 缺失 artifact 未标记 half-written。
- transcript record_id 或 events event_id 重复。
- RunRecorder finalize 重入产生重复 terminal facts。
- PreparedMessages binding 缺少 content replacement hash、observation source event ref 或 tool schema snapshot hash。
- PreparedMessages sha256 不匹配。
- 缺少阶段 2 / 3 / 4 外部输入 ref。
- 缺少 required report。
- interrupted / crashed structured facts 缺失。
- `--fail-if-output-exists` 防覆盖。

## 允许降级项

- 阶段 5 只保留 P1-1 provider / scaffold / budget 元数据，不实现完整评测矩阵、不生成 provider 对比报告、不把 provider 或 scaffold 排名作为验收目标。
- 阶段 5 的 run fixture 是 deterministic integration evidence，不声称替代真实 provider rollout 的最终 V4 acceptance 样本。

## 禁止降级项

- 不允许 final verifier result、reward、hidden verifier 或 evaluator-only evidence 进入同一次 run 的模型可见 observation。
- 不允许缺少 `scaffold_id`、`tool_policy_id`、`verifier_id` 或 `environment_id` 的 run 进入 trainable export。
- 不允许 provider fallback success 缺少 fallback policy ref。
- 不允许 ArtifactRef sha256、size、路径或 redaction / retention facts 漂移。
- 不允许 PreparedMessages 绑定缺少 tool schema hash、content replacement hash 或 observation source event ref。

## 已知限制

- 阶段 5 仍然不实现 P1-3 context strategy、project context 或 session continuation。
- 阶段 5 不实现完整 provider / scaffold / budget matrix，只保留后续可分层分析所需的最小元数据。

## 是否偏离设计文档

没有偏离。阶段 5 保持在 agent run integration、RunSpec 元数据保留、prepared messages 绑定、final verifier boundary 和 trajectory store integrity 范围内，没有扩张到完整 provider 矩阵或 session continuation。

## Subagent 或等价自审结论

阶段 5 初轮只读审查发现两个 P1、两个 P2 和若干 P3：final verifier 泄露扫描没有覆盖真正的 tool observation artifact；Stage 5 integration 没有强制绑定阶段 2 / 3 / 4 和 Docker / permission provenance；trajectory tracking table 没有列出 final patch 或 no-patch fact；PreparedMessages tool schema hash 未与 Stage 4 tool contract 交叉校验；负例测试覆盖不完整。上述问题已经修复，并补充了对应负例。最终复审结论见 `docs/v4/review/implementation/05-agent-run-integration-review.md`。

## 是否可以进入下一阶段

最终复审通过后可以进入阶段 6。
