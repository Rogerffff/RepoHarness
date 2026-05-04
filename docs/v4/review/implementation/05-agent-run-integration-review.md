# V4 Stage 5 Implementation Review: Agent Run Integration

## 审查范围

本次审查覆盖阶段 5 的 Agent run integration、RunSpec 元数据保留、prepared messages 绑定、final verifier 单向边界、interrupted / crashed run recovery、trajectory store integrity、CLI inspect 命令和阶段 1 机器产物追踪表同步。

审查文件和产物包括：

- `src/repo_harness/v4_agent_run.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/v4_stage1.py`
- `tests/unit/test_v4_agent_run.py`
- `tests/unit/test_v4_stage1_skeleton.py`
- `docs/v4/evidence/agent-run-integration/`
- `docs/v4/evidence/schema-and-inspect/artifact_inspect_tracking_table.json`

## 审查方法

- 对照 `docs/v4/implementation-plan.md` 阶段 5 要求逐项检查。
- 对照阶段 1 追踪表要求，确认新增机器产物有对应 inspect 命令。
- 只读检查 final verifier hidden-facts 单向边界，确认同一次 run 的模型可见 transcript、event、prepared message、tool observation 和 model-visible artifact 不包含 final verifier result。
- 只读检查 Stage 2 / Stage 3 / Stage 4 外部输入引用是否显式绑定 path、sha256、schema 和关键 hash。
- 运行阶段 5 单元测试和强 inspect 命令。

## 审查发现和修复记录

### 已修复 P1：final verifier 泄露检查未覆盖真正的模型可见 observation artifact

初始实现只扫描 transcript 和 events 中 `model_visible=true` 的记录，未扫描 `tool_observation_ref` 指向的模型可见文件，也未扫描 artifacts manifest 中 `model_visible=true` 的 artifact 内容。

修复结果：

- `_inspect_prepared_binding` 扫描 `prepared_messages_ref` 和 `tool_observation_ref` 的 payload。
- `_inspect_no_model_visible_final_verifier_terms` 扫描 transcript、events 和 artifacts manifest 中 `model_visible=true` 的 artifact 实际文本。
- 单元测试覆盖 final verifier result 出现在 events、transcript、prepared messages、tool observation 和 model-visible artifact 的负例。

### 已修复 P1：Stage 5 integration 未强制绑定 Stage 2 / Stage 3 / Stage 4 与 Docker / permission provenance

初始实现中 `tool_lifecycle_ref` 和 `rollout_queue_ref` 是可选引用，且没有 task definition、Docker facts 或 permission trace 绑定。

修复结果：

- `build-v4-agent-run-integration` 强制接收 `--task-freeze`、`--rollout-queue` 和 `--tool-lifecycle`。
- `v4_agent_run_integration_report.json` 绑定 `task_freeze_manifest_ref`、`generated_task_definition_ref`、`environment_stability_report_ref`、`docker_environment_facts_ref`、`rollout_queue_manifest_ref`、`tool_contract_ref`、`permission_decision_trace_ref` 和 `tool_lifecycle_trace_ref`。
- inspect 校验这些引用的绝对路径、sha256、schema version、task id、model-visible task definition 标记、task visibility policy、permission trace schema、allow executed fact、tool lifecycle schema 和 tool schema hash。

### 已修复 P1：PreparedMessages binding records 可以空转或重复

复审发现 `binding_records` 为空、部分覆盖或追加重复 `run_id` 时，可能绕过 prepared messages 与 trajectory run 的一一绑定要求。

修复结果：

- inspect 强制 `binding_records` 非空。
- inspect 强制 `binding_records` 数量等于 `trajectory_store_integrity_report.run_records` 数量。
- inspect 强制每个 `run_id` 唯一。
- inspect 强制 `binding_records` 覆盖每个 trajectory run。
- 单元测试覆盖空 binding、部分 binding 和重复 run id。

### 已修复 P2：Stage 5 trajectory tracking table 未列出 final patch 或 no-patch fact

阶段 1 追踪表的 Stage 5 trajectory store 行缺少 completed run 的 final patch / no-patch evidence。

修复结果：

- `src/repo_harness/v4_stage1.py` 追踪表增加 `final.patch` 和 `no_patch_fact.json`。
- `docs/v4/evidence/schema-and-inspect/artifact_inspect_tracking_table.json` 重新生成。
- trajectory inspect 对 completed run 强制 `final.patch` 或 `no_patch_fact.json` 二选一存在。

### 已修复 P2：PreparedMessages 的 tool schema hash 未与 Stage 4 tool contract 交叉校验

初始实现只检查 `tool_schema_snapshot_hash` 非空，没有与 Stage 4 tool contract 绑定。

修复结果：

- Stage 5 integration report 保存 expected tool schema hash。
- inspect 读取 Stage 4 `tool_contract_v4_snapshot.json` 的 `tool_schema_hash`，并与 `prepared_messages_binding_report.json` 的 `tool_schema_snapshot_hash` 校验一致。
- 单元测试覆盖 tool schema hash 漂移。

## 正例确认

- CLI 命令都显式接收输入路径，没有读取 latest run、默认目录或环境变量猜测输入。
- completed、interrupted、crashed 三类 run 都生成了要求的 trajectory 文件。
- completed run 有 `run_metadata.json` 和 `final.patch`。
- interrupted / crashed run 有结构化 facts，并保持 crash-readable。
- RunSpec 元数据覆盖 provider、model、scaffold、budget、fallback、token usage、tool policy、verifier、environment、task source、task family 和 task visibility policy。
- final verifier boundary 标记 formal final verifier 是 accepted / rejected / inconclusive 的权威来源。

## 负例确认

单元测试覆盖以下失败条件：

- final verifier result 出现在模型可见 event、transcript、prepared messages、tool observation 或 model-visible artifact。
- RunSpec 缺少 `scaffold_id`、`tool_policy_id`、`verifier_id` 或 `environment_id`。
- fallback success 缺少 fallback policy。
- ArtifactRef sha256 不匹配。
- 缺失 artifact 未标记 half-written。
- transcript record_id 或 events event_id 重复。
- finalize 重入产生重复 terminal facts。
- PreparedMessages binding 缺少必需字段、sha256 不匹配、tool schema hash 漂移、空记录、部分覆盖或重复 run id。
- Stage 2 / Stage 3 / Stage 4 外部 ref 缺失。
- generated task definition schema 漂移。
- permission trace schema 漂移。
- tool lifecycle schema hash 漂移。
- required report 缺失。
- interrupted / crashed structured facts 缺失。
- `--fail-if-output-exists` 防覆盖。

## 范围控制

阶段 5 没有实现完整 provider / scaffold / budget matrix，没有生成 provider 对比报告，没有把 provider 或 scaffold 排名作为验收目标。阶段 5 没有实现 P1-3 context strategy、project context 或 session continuation。

## 最终结论

阶段 5 经三轮只读 subagent 审查。前两轮发现的 P1/P2/P3 均已修复；第三轮仅剩的 prepared messages binding 唯一性和数量一致性 P1 也已修复并补充负例。当前未发现剩余 P1、P2 或 P3 问题。阶段 5 可以进入阶段 6。
