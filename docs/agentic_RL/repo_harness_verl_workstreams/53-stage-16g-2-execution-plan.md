# Stage 16G.2 执行计划：结构化文件、补丁和工作区修改工具面

## 1. 阶段定位

Stage 16G.2 是 Stage 16G 工具面改造的第一个行为实现阶段。它承接 Stage 16G.1 已经固定的 tool registry、profile taxonomy 和训练资格门禁，开始补齐 RepoHarness 在真实软件工程任务中最基础的“改代码能力”。

本阶段目标不是开放完整 shell，也不是进入 Stage 17 数据 registry。它要解决的是：

```text
模型能不能用结构化、可审计、可训练的方式完成真实仓库修改，
包括已有文件编辑、新建或覆盖写入、多文件 patch、删除、移动和目录创建，
并且这些动作能稳定进入 final.patch、patch hygiene、run_episode projection 和训练资格判断。
```

Stage 16G.2 完成后，RepoHarness 的文件修改能力应该不再被 `edit_file` exact replace 和 `create_file` create-only 语义限制住。复杂 SWE 任务需要的多文件变更、文件重组和补丁审计，必须能在 `swe_public_core` 目标工具面中表达和验收。

## 2. 非目标

Stage 16G.2 明确不做下面这些事情：

1. 不实现 `run_public_command`、`run_project_test` 或 `scratch_python`，这些属于 Stage 16G.3。
2. 不把 `diagnostic_shell` 或 persistent shell 放进 `swe_public_core`，这些属于 Stage 16G.4 的 extended profile。
3. 不放宽 `execute_bash`。
4. 不实现 dependency setup、project command routing 或 public command allowlist。
5. 不定义数值型 process reward 权重，不把 reward builder 提前做进来。
6. 不冻结真实 SWE 训练数据，不启动 Stage 20 warm-start 或 Stage 21 formal RL。
7. 不把旧 `run_task(...)` 作为新增工具面的主验收入口。
8. 不实现非文本文件读取、完整 LSP、MCP、子代理或后台任务。

## 3. 上游依据

Stage 16G.2 必须继承这些已提交产物：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_per_capability_baseline_comparison.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_stage16g_implementation_requirements.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_tool_registry_contract.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_profile_taxonomy.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_training_eligibility_gate_spec.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_acceptance_summary.json
```

Stage 16G.1 evidence 是当时的完成态，不应在 Stage 16G.2 中原地改写。Stage 16G.2 应生成自己的 delta evidence，说明哪些 Stage 16G.1 planned / partial 能力已经被实现、验证和投影。

Stage 16G.2 开工前必须先重新运行当前代码中的 Stage 16G.1 inspector，并确认它仍然通过：

```bash
PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main inspect-stage16g1-tool-profile docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_acceptance_summary.json --assert-complete
```

这个前置检查必须确认：

1. `stage16g1_source_inventory.json` 已经被 `stage16g1_acceptance_summary.json` 的 `source_inventory_sha256` 绑定。
2. inspector 会重新扫描当前公开 evidence，而不是只信任旧的 `stage16g1_path_leak_scan_report.json`。
3. Stage 16G.1 registry、profile taxonomy 和 training eligibility gate 都是已提交基线。若这些前置条件不满足，必须先修复并提交 Stage 16G.1，不能在不可靠的 registry evidence 上继续实现 Stage 16G.2。

## 4. 必须覆盖的 capability

Stage 16G.2 的第一优先级能力来自 Stage 16G.0 follow-up 和 Stage 16G.1 registry：

| capability_id | 当前状态 | Stage 16G.2 目标 |
| --- | --- | --- |
| `structured_edit_existing_file` | `edit_file` 已有，但 exact replace 对复杂修改不够稳 | 保留 `edit_file`，并通过 batch patch 补齐复杂已有文件修改 |
| `structured_write_or_create_file` | `create_file` 已有，但只新建，覆盖写入语义不足 | 新增 `write_file`，明确新建、覆盖和哈希保护语义 |
| `apply_patch_or_multi_file_edit` | 缺少模型可见多文件 patch 工具 | 新增 `apply_patch` 或等价结构化批量文件操作工具 |
| `delete_move_mkdir_file_operations` | 缺少结构化删除、移动、目录创建工具面 | 新增 `delete_file`、`move_file`、`mkdir`，并接入 patch/export |

第二优先级配套能力：

| capability_id | 处理原则 |
| --- | --- |
| `task_management_todo` | 非阻塞；Stage 16G.2D 只做 `update_working_state` 和 Todo-like 语义对齐，不阻塞文件工具主线 |
| `git_diff_status_and_patch_capture` | 当前已有 `git_diff`、patch hygiene 和 projection；Stage 16G.2 只做回归绑定，完整 parity 留给 Stage 16G.5 |
| `tool_result_truncation_raw_artifact_privacy` | 主要属于 Stage 16G.4；Stage 16G.2 只要求新增文件工具不得引入新的路径、raw artifact 或工具结果泄漏，不要求提前完成完整 truncation framework |

## 5. 关键设计决策

### 5.1 `create_file` 保持 create-only，新增 `write_file`

`create_file` 已经在 `simple_react` 默认工具面中存在，并且语义是：

```text
只创建新 UTF-8 文件；目标文件已存在时拒绝。
```

Stage 16G.2 不应把这个既有工具悄悄改成“可覆盖写入”，否则会破坏旧轨迹和模型提示中的含义。应新增独立 `write_file`：

```text
write_file(path, content, mode, expected_content_hash?)
```

建议语义：

1. `mode="create"`：目标不存在才成功，等价于更明确的新建写入。
2. `mode="overwrite"`：目标存在才成功，Stage 16G.2 第一版必须显式要求 `expected_content_hash`，不能只依赖隐式 prior read cache。
3. `mode="upsert"`：默认不进入 `swe_public_core`，除非实现者提供足够强的审计理由；主训练建议先不用 upsert，避免模型盲目覆盖。
4. 任何覆盖写入都必须返回 `content_hash`、`previous_content_hash`、`result_kind`、`reason_code` 和 `result_envelope`。

这条决策必须变成机器验收项，而不是只写在设计文档里：

1. `create_file` 对已存在路径必须继续失败，并返回 create-only 语义的结构化拒绝原因。
2. `write_file(mode="upsert")` 默认不得进入 `swe_public_core`。如果实现者决定支持 upsert，只能先放入 extended、restricted 或 explicitly gated profile，并在 evidence 中说明原因。
3. `create_file` 的历史提示语、工具说明和测试不能被静默改成覆盖写入语义。
4. 如果 core profile 暴露 `write_file`，模型可见 schema 不应包含 `mode="upsert"`；如果实现层必须保留统一 schema，executor 必须能根据 profile 或 execution spec 明确拒绝 core profile 下的 upsert 调用。

如果后续版本想支持“最近一次 `read_file` 缓存哈希匹配”的便利语义，必须额外满足：

1. operation audit 记录具体 `read_observation_id`、工具调用编号、路径、读取时的 hash 和使用该 hash 的写入 operation。
2. stale cache、多文件交叉读写、同一路径重复编辑和移动后再写入都必须有拒绝测试。
3. 该便利语义不能替代 Stage 16G.2 第一版的显式 `expected_content_hash` 主路径。

### 5.2 `apply_patch` 采用结构化批量操作，不使用裸 shell patch

Stage 16G.2 的 `apply_patch` 不应直接等价于 `patch -p1`、`git apply` 或任意 shell 命令。建议实现为结构化批量文件操作：

```json
{
  "operations": [
    {
      "op": "replace_text",
      "path": "src/pkg/module.py",
      "old_text": "old raw text",
      "new_text": "new raw text",
      "expected_content_hash": "..."
    },
    {
      "op": "write_file",
      "path": "src/pkg/new_file.py",
      "content": "file content",
      "mode": "create"
    },
    {
      "op": "delete_file",
      "path": "src/pkg/old_file.py",
      "expected_content_hash": "..."
    },
    {
      "op": "move_file",
      "source_path": "src/pkg/old_name.py",
      "target_path": "src/pkg/new_name.py",
      "expected_source_hash": "..."
    },
    {
      "op": "mkdir",
      "path": "src/pkg/subpackage"
    }
  ]
}
```

这不是要求最终字段名必须完全照抄上面示例，但实现必须满足：

1. 每个 operation 都有明确 `op`、路径字段、成功事实和失败 reason。
2. 不依赖行号补丁；行号可以作为辅助上下文，但不能作为唯一定位依据。
3. `replace_text` 仍使用 raw text 和内容哈希来防止 stale edit。
4. Stage 16G.2 第一版必须采用“全部 operation 预检通过后再写入”的原子化语义。预检阶段发现任何失败时，不得修改任何文件。
5. 不接受任意 unified diff 作为模型输入，除非实现者同时提供安全 parser、路径清洗、失败恢复和测试覆盖。第一版不建议做这个扩展。

如果全部预检通过后，实际写入阶段发生极少数运行时失败，工具结果必须明确返回：

```text
partial_failure=true
rollback_attempted=true/false
rollback_status=...
applied_operation_ids=[...]
failed_operation_id=...
```

这类异常必须进入 safety denial probe 或等价安全验收报告，不能被伪装成普通成功或普通拒绝。

只要 episode 中出现 `partial_failure=true`，或者 rollback 未干净完成，该 episode 默认必须标记为：

```text
invalid_for_training=true
policy_loss_candidate=false
official_prediction_eligible=false
training_export_eligible=false
diagnostic_side_channel_only=true
```

这类 episode 可以保留为诊断材料，但不能进入主 SWE 强化学习训练样本、official prediction 或训练导出。

### 5.3 写入工具必须有输入规模上限

Stage 16G.2 新增写入工具不能接受无限大小的内容、路径或 operation 列表。具体数值可以在实现时按现有测试资源微调，但必须写入 `stage16g2_structured_file_tool_contract.json`、executor 常量和验收测试。

建议第一版采用下面这组保守上限作为起点：

| 限制项 | 建议上限 | 触发时行为 |
| --- | ---: | --- |
| 单个 workspace-relative path 字符数 | 1024 | 拒绝，`reason_code="path_too_long"` |
| 单个路径 segment 字符数 | 255 | 拒绝，`reason_code="path_segment_too_long"` |
| `write_file` 单文件 `content` 字节数 | 1 MiB | 拒绝，`reason_code="content_too_large"` |
| `apply_patch.operations` 数量 | 50 | 拒绝，`reason_code="too_many_operations"` |
| `apply_patch` 单个 operation 写入字节数 | 1 MiB | 拒绝，`reason_code="operation_too_large"` |
| `apply_patch` 总写入字节数 | 2 MiB | 拒绝，`reason_code="patch_too_large"` |
| 单次工具可见结果摘要 | 64 KiB | 截断或摘要化，但 raw artifact 仍必须私有且 public-safe |

任何超过上限的请求必须在预检阶段拒绝，不得产生半应用工作区变更。完整工具结果截断框架仍属于 Stage 16G.4；Stage 16G.2 只要求新增工具有明确的输入规模上限和不泄漏的结果摘要。

### 5.4 单文件工具和批量工具复用同一底层文件变更服务

建议新增一个小型共享模块，例如：

```text
src/repo_harness/tools/file_mutation.py
```

它负责：

1. workspace-relative 路径解析。
2. hidden path、runtime-private、版本控制目录和宿主绝对路径拒绝。
3. UTF-8 文本文件检查。
4. Stage 16G.2 第一版的显式 expected hash 检查；隐式 prior read cache 只能作为后续扩展或带完整 observation 绑定事实的可选能力。
5. 新建、覆盖、删除、移动、目录创建的预检和执行。
6. 统一输入规模上限、`reason_code`、`retryable`、`safe_alternative_tool`、`safe_rewrite_example` 和 `result_envelope`。

这样 `edit_file`、`create_file`、`write_file`、`delete_file`、`move_file`、`mkdir` 和 `apply_patch` 不会各自实现一套路径检查和拒绝语义。

### 5.5 文件操作必须进入 final patch，而不是只改工作区

Stage 16G.2 的成功条件不是“工具调用返回 ok”，而是：

```text
工作区修改 -> git diff -> final.diff/final.patch -> patch hygiene -> compat projection -> official prediction eligibility
```

新增文件工具必须通过 `run_episode(real_episode)` 路径证明这条链路可达。只做工具单元测试不够。

这里需要区分 Git diff 事实和工具操作审计事实：

1. `mkdir` 创建空目录不会出现在 Git diff 中，所以 Stage 16G.2 不能要求空目录本身进入 `final.patch`。它的成功事实应来自 tool event、operation audit 和 TrainingView projection。只有目录下产生可追踪文件时，才要求相关文件进入 `final.patch`。
2. `move_file` 在 `final.patch` 中可能表现为 rename，也可能表现为 delete+add，这取决于 diff 生成方式和相似度检测。Stage 16G.2 必须允许这两种 patch 表现，但结构化 operation facts 必须保留 move 语义、source path、target path 和 source hash。
3. changed file facts 必须同时能表达 Git diff 侧的新增、修改、删除事实，以及工具操作侧的移动、目录创建事实。

### 5.6 `task_management_todo` 是第二优先级非阻塞项

`update_working_state` 当前已经存在，但弱于 Claude Code `TodoWrite`。Stage 16G.2D 可以做下面两件事之一：

1. 保持 `update_working_state` 轻量语义，但明确它不是 repository mutation 工具，并补齐 projection 和训练资格说明。
2. 新增更接近 TodoWrite 的结构化任务状态工具。

无论选择哪条路，它都不能阻塞 `apply_patch`、`write_file`、`delete_file`、`move_file`、`mkdir` 的第一优先级主线。

## 6. 建议实现范围

建议修改或新增：

```text
src/repo_harness/tools/minimal.py
src/repo_harness/tools/__init__.py
src/repo_harness/tools/file_mutation.py
src/repo_harness/scaffolds/simple_react.py
src/repo_harness/scaffolds/planner_coder_verifier.py
src/repo_harness/evaluation/episode_projection.py
src/repo_harness/rl/runtime.py
src/repo_harness/stage16g_file_surface.py
src/repo_harness/cli/main.py
scripts/pre_verl/build_stage16g2_structured_file_surface.py
tests/unit/test_tools.py
tests/unit/test_repo_harness_stage16g2_structured_file_surface.py
```

说明：

1. `simple_react` 通过 `DEFAULT_TOOL_ORDER` 暴露默认工具，Stage 16G.2 新工具如果进入 `DEFAULT_TOOL_ORDER`，会进入当前默认训练 scaffold。
2. `planner_coder_verifier` 有手写 phase tool list，必须显式更新 coder / repair phase；planner 不应获得写工具。
3. `patch_focused_react` 系列是显式受限 scaffold。Stage 16G.2 不应静默改变它们的历史语义；如果决定让它们获得新文件工具，必须版本号升级、测试更新，并在 implementation notes 中说明理由。
4. `stage16g1_*` evidence 不应原地改写；Stage 16G.2 用自己的 evidence 表示 delta。
5. 当前主入口主要通过 scaffold 的 `allowed_tools` 把工具带入 `EpisodeExecutionSpecBuilder`，还没有完整 runtime profile 选择层。因此 Stage 16G.2 的“进入 profile”验收必须同时检查实际 scaffold 暴露和 Stage 16G.1 profile taxonomy delta，不能只检查文档里的 profile 名称。

## 7. 子阶段拆分

### 7.1 Stage 16G.2A：schema、profile 暴露和工具注册

目标：

1. 新增 `write_file`、`apply_patch`、`delete_file`、`move_file`、`mkdir` 的 ToolDefinition。
2. 更新参数 normalization 规则。
3. 更新 `DEFAULT_TOOL_ORDER` 和 `simple_react` 模型可见提示。
4. 更新 `planner_coder_verifier` 的 coder / repair phase 工具列表。
5. 生成 tool surface delta evidence，说明 Stage 16G.1 registry 中哪些 `owner_stage=16G.2` 能力从 planned / partial 变成 implemented 或 still_partial。
6. 生成 profile delta evidence，重新推导 `safe_structured_only`、`swe_public_core`、`swe_public_extended` 和 `redteam_restricted` 的工具集合、训练投影状态和 policy-loss 相关门禁。

验收：

1. `build_tool(...)` 能构造所有 Stage 16G.2 新工具。
2. `run_episode` execution spec 中的 `allowed_tool_names` 包含目标工具。
3. 模型可见 prompt 不鼓励 shell 重定向、临时脚本或裸 patch。
4. `swe_public_core` 仍不包含 persistent shell。
5. `safe_structured_only`、`swe_public_core`、`swe_public_extended` 和 `redteam_restricted` 的 delta 不是手写声明，而是从 Stage 16G.1 registry、Stage 16G.1 profile taxonomy 和当前工具注册状态重新计算得到。
6. 新增工具的训练投影状态必须从 `planned`、`partial` 或 `not_implemented` 转成有证据支撑的 `implemented`、`still_partial` 或 `blocked`；不能只改模型可见 prompt。

### 7.2 Stage 16G.2B：文件操作行为实现

目标：

1. `write_file` 支持安全新建和覆盖写入。
2. `delete_file` 支持删除 UTF-8 文本文件，Stage 16G.2 第一版必须显式要求 `expected_content_hash`。
3. `move_file` 支持 workspace 内移动或重命名，默认不覆盖目标，并且 Stage 16G.2 第一版必须显式要求 `expected_source_hash`。
4. `mkdir` 支持创建 workspace 内目录，但拒绝 runtime-private、版本控制、依赖环境和宿主路径。
5. `apply_patch` 支持批量执行 `replace_text`、`write_file`、`delete_file`、`move_file`、`mkdir`。

验收：

1. 成功路径真实修改工作区文件。
2. 失败路径不产生半应用 patch。第一版必须全部预检成功后再写入。
3. 拒绝路径返回结构化 `reason_code`、`retryable` 和 recovery 信息。
4. 二进制文件、非 UTF-8 文件、symlink 越界、`.git`、`.repo_harness_runtime`、`.repo_harness_env_overlay`、`runtime_private`、绝对路径和 `..` 越界路径均被拒绝。
5. `apply_patch` 的事务语义必须通过真实文件系统 probe 验证：任意 operation 预检失败时，工作区文件内容、文件列表和 git diff 均保持不变。
6. 写入阶段异常必须返回 rollback / partial failure 状态，并进入安全验收报告。
7. 覆盖、删除、移动和 `apply_patch.replace_text` 的主路径必须显式绑定 expected hash；隐式 prior read cache 如被实现，必须有 observation 绑定事实和 stale cache 测试。
8. 内容大小、operation 数量和路径长度超过上限时必须在预检阶段拒绝，并证明工作区无变化。

### 7.3 Stage 16G.2C：patch hygiene、final patch 和训练投影绑定

目标：

1. 使用真实 `run_episode(real_episode)` 或等价 `run-episode-task` smoke，让模型通过新增工具完成多文件变更。
2. 验证变更进入 `final.patch` 和 `final.diff`。
3. 验证 `final_patch_hygiene_report.json` 仍然过滤临时文件、缓存、runtime-private 和依赖目录。
4. 验证 `compat_projection_manifest.json`、`training_view_projection.json` 和 `provider_route_qualification.json` 保持 public-safe。
5. 验证 mock/replay/provider 路径不会因为工具实现而被错误标成 policy loss eligible。

验收：

1. `projection_created_from_run_episode=true`。
2. `projection_complete=true`。
3. `final_patch_sha256`、`final_diff_sha256` 和 cleaned patch sha256 绑定正确。
4. 多文件 patch 中的新增、修改、删除、移动都能在 changed file facts 中被看见。
5. Tool observation span 仍然是 response mask 0，不把工具输出误计入 policy loss。

### 7.4 Stage 16G.2D：Todo-like 状态工具对齐，非阻塞

目标：

1. 明确 `update_working_state` 是否继续作为轻量 task state 工具。
2. 如果不新增 TodoWrite 等价工具，则补充 evidence 说明它为什么不阻塞主 SWE 强化学习。
3. 如果新增 Todo-like 工具，则必须有 projection、训练资格和 no repository mutation 测试。

验收：

1. task state 工具不修改仓库文件。
2. task state tool event 能进入 trajectory。
3. task state 工具不会影响 final.patch。
4. 该子阶段失败不能阻塞 Stage 16G.2A 到 Stage 16G.2C 的 P0 文件工具完成，但必须在 acceptance summary 中如实标注。

## 8. 公开 evidence 产物

建议新增目录：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/
```

建议产物：

```text
implementation-notes.md
stage16g2_source_inventory.json
stage16g2_profile_delta_report.json
stage16g2_tool_surface_delta.json
stage16g2_structured_file_tool_contract.json
stage16g2_file_mutation_probe_report.json
stage16g2_run_episode_projection_probe_report.json
stage16g2_safety_denial_probe_report.json
stage16g2_training_projection_linkage_report.json
stage16g2_task_state_followup_report.json
stage16g2_path_leak_scan_report.json
stage16g2_acceptance_summary.json
```

`stage16g2_acceptance_summary.json` 至少包含：

```json
{
  "schema_version": "stage16g2.acceptance_summary.v1",
  "status": "passed",
  "stage16g2_complete": true,
  "stage16g1_registry_input_sha256": "...",
  "stage16g1_profile_taxonomy_input_sha256": "...",
  "profile_delta_report_sha256": "...",
  "profile_delta_passed": true,
  "stage16g1_preflight_inspection_passed": true,
  "input_limit_contract_sha256": "...",
  "explicit_hash_guard_passed": true,
  "partial_failure_invalidates_training_passed": true,
  "implemented_capability_ids": [
    "structured_edit_existing_file",
    "structured_write_or_create_file",
    "apply_patch_or_multi_file_edit",
    "delete_move_mkdir_file_operations"
  ],
  "nonblocking_followup_capability_ids": [
    "task_management_todo",
    "git_diff_status_and_patch_capture"
  ],
  "run_episode_projection_probe_passed": true,
  "final_patch_hygiene_passed": true,
  "public_path_leak_scan_passed": true,
  "stage16g3_allowed_to_start": true,
  "stage17b_real_data_freeze_allowed": false,
  "stage20_warm_start_data_generation_allowed": false,
  "stage21_formal_rl_allowed": false,
  "failure_count": 0,
  "failure_ids": []
}
```

和 Stage 16G.1 一样，acceptance summary 必须用 sha256 绑定所有公开 evidence，并且 inspector 需要重新扫描当前目录，不能只信任旧的 path leak scan 报告。

## 9. 机器验收入口

建议新增：

```text
repo-harness inspect-stage16g2-structured-file-tools \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/stage16g2_acceptance_summary.json \
  --assert-complete
```

验收器必须至少检查：

1. Stage 16G.1 registry 中 `owner_stage=16G.2` 的能力全部出现在 Stage 16G.2 delta report。
2. 4 个 P0 capability 全部被标成 implemented 或带明确失败原因；没有失败原因时不能 passed。
3. 新工具都能 `build_tool(...)`。
4. `simple_react` 和 run_episode execution spec 能看见目标工具。
5. `planner_coder_verifier` coder / repair phase 能看见目标工具，planner phase 不能看见写工具。
6. `patch_focused_react` 系列没有被静默改变；如果改变，必须有版本号和测试说明。
7. public evidence 没有本机绝对路径、runtime-private 路径、provider secret、API key 或 raw patch 私有内容。
8. acceptance summary 的计数、sha256、放行字段和 failure 列表能重新推导。
9. Stage 17B / Stage 20 / Stage 21 仍然不能被 Stage 16G.2 单独放行。
10. profile delta report 能从 Stage 16G.1 profile taxonomy 和当前工具注册状态重新推导，且覆盖 `safe_structured_only`、`swe_public_core`、`swe_public_extended` 和 `redteam_restricted`。
11. `create_file` 对已存在路径继续拒绝，`write_file(mode="upsert")` 默认不进入 `swe_public_core`。
12. `mkdir` 的空目录成功事实来自 operation audit / TrainingView projection，而不是要求空目录出现在 `final.patch`。
13. `move_file` 的 operation facts 保留 move 语义，即使 final diff 表现为 rename 或 delete+add。
14. `apply_patch` 第一版采用全部预检通过后再写入的事务语义。
15. core profile 下的 `write_file` schema 不暴露 upsert，或者 executor 会基于 profile / execution spec 拒绝 upsert。
16. Stage 16G.1 preflight inspector 在当前代码和当前 public evidence 上通过。
17. `write_file`、`delete_file`、`move_file` 和 `apply_patch.replace_text` 的主路径显式要求 expected hash。
18. 写入工具 schema、executor 和测试都包含有限输入规模上限。
19. partial failure 或 rollback 未干净完成的 episode 被标记为 `invalid_for_training=true`，不能进入 policy-loss candidate、official prediction 或训练导出。

## 10. 必须测试的行为矩阵

### 10.1 成功路径

1. `write_file(mode="create")` 新建文件成功。
2. `write_file(mode="overwrite", expected_content_hash=...)` 覆盖已读文件成功。
3. `delete_file(expected_content_hash=...)` 删除文件成功。
4. `move_file(source_path, target_path, expected_source_hash=...)` 移动文件成功，并在 operation facts 中保留 source path、target path 和 move 语义。
5. `mkdir(path)` 创建目录成功，并在 tool event、operation audit 和 TrainingView projection 中可见。
6. `apply_patch` 单次调用完成至少 3 个文件变更，包括修改已有文件和新增文件。
7. `apply_patch` 单次调用覆盖删除、移动和目录创建。
8. 成功调用后 `git_diff` 能看到所有变更。
9. `run_episode` smoke 中最终 `final.patch` 包含新增、修改和删除事实；移动可以表现为 rename 或 delete+add，但结构化 operation facts 必须保留 move 事实。
10. 如果 `mkdir` 后目录下创建了 tracked file，则 `final.patch` 包含该 tracked file；如果只创建空目录，则不要求 `final.patch` 表达空目录。

### 10.2 失败和拒绝路径

1. 目标路径是宿主绝对路径，拒绝。
2. 目标路径使用 `..` 越界，拒绝。
3. 目标路径在 `.git`、`.repo_harness_runtime`、`.repo_harness_env_overlay`、`runtime_private` 或依赖环境目录下，拒绝。
4. 覆盖写入缺少显式 expected hash，拒绝。
5. Stage 16G.2 第一版中，覆盖写入、删除、移动或 `apply_patch.replace_text` 缺少显式 expected hash，拒绝。
6. expected hash 过期，拒绝。
7. `apply_patch` 某个 operation 预检失败，整个批量 patch 不产生半应用变更。
8. 目标文件是二进制或非 UTF-8 文本，拒绝。
9. symlink 指向 workspace 外部，拒绝。
10. `move_file` 目标已存在且没有显式安全覆盖语义，拒绝。
11. `delete_file` 删除目录，拒绝；目录删除不是 Stage 16G.2 目标。
12. `create_file` 写入已存在路径继续失败，并返回 create-only 语义的结构化拒绝原因。
13. `write_file(mode="upsert")` 如果被实现，默认不能出现在 `swe_public_core`，并必须在 profile delta report 中标明 gated profile。
14. `apply_patch` 预检通过后发生运行时写入失败时，工具结果必须包含 `partial_failure`、`rollback_attempted`、`rollback_status`、`applied_operation_ids` 和 `failed_operation_id` 等可审计字段。
15. core profile 下如果模型尝试调用 `write_file(mode="upsert")`，必须被 schema 或 executor 拒绝，不能降级成静默覆盖写入。
16. 超过路径长度、单文件内容大小、operation 数量、单 operation 写入大小或总 patch 大小上限时，必须拒绝并保持工作区无变化。
17. 如果实现隐式 prior read cache，stale cache、多文件交叉读写、同一路径重复编辑和移动后再写入都必须被测试覆盖。

### 10.3 投影和训练资格路径

1. 新工具的 tool observation 进入 TrainingView，且 response mask 为 0。
2. 新工具事件的 projection 不包含 raw artifact 或本机绝对路径。
3. mock / external provider route 不会进入 policy loss。
4. 成功文件工具不会绕过 patch hygiene。
5. 被 patch hygiene 过滤的临时文件不会进入 official prediction。
6. 新工具的拒绝事件可以作为负样本或 diagnostic fact，但不能单独成为 policy loss sample。
7. 新文件工具不得新增本机绝对路径、runtime-private 路径、raw patch 私有内容或 provider secret 泄漏。完整工具结果截断框架仍留给 Stage 16G.4。
8. profile delta report 必须证明工具不是只出现在 `simple_react`，还被映射到 Stage 16G.1 定义的目标 profile 和训练投影策略。
9. `partial_failure=true` 或 rollback 未干净完成的 episode 必须被排除出主训练样本、policy-loss candidate、official prediction 和训练导出，只能进入 diagnostic side channel。

## 11. 建议测试命令

Stage 16G.2 完成时至少运行：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_tools.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_stage16g2_structured_file_surface.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_stage16g1_tool_profile_registry.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_stage16f3_run_episode_task_cli.py
PATH=.venv/bin:$PATH python -m compileall -q src/repo_harness scripts/pre_verl/build_stage16g2_structured_file_surface.py
PATH=.venv/bin:$PATH python -m repo_harness.cli.main inspect-stage16g2-structured-file-tools docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/stage16g2_acceptance_summary.json --assert-complete
```

如果 `.venv/bin/repo-harness` console script 不存在，可以用：

```bash
PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main inspect-stage16g2-structured-file-tools ...
```

## 12. 安全红线

Stage 16G.2 实现时不能越过这些边界：

1. 不能让模型读写 hidden verifier、gold patch、test patch 或 runtime-private 内容。
2. 不能允许 `.git`、Git history、宿主绝对路径或本机家目录路径进入工具结果。
3. 不能用 shell 重定向、`python -c` 或 `git apply` 作为主训练文件修改面。
4. 不能让临时复现脚本默认进入 final patch；临时脚本能力属于 Stage 16G.3 的 scratch Python。
5. 不能把 `diagnostic_shell` 提前暴露给 `swe_public_core`。
6. 不能把工具实现成功误解释成 Stage 17B、Stage 20 或 Stage 21 放行。

## 13. 完成判定

Stage 16G.2 可以被视为完成，必须同时满足：

1. 4 个 P0 capability 都有模型可见工具、executor、scaffold/profile 暴露、run_episode 可见性和训练投影证据。
2. 新增文件工具通过成功、失败、拒绝和安全边界测试。
3. 多文件变更经过 `run_episode(real_episode)` 进入 final patch、patch hygiene 和 compat projection。
4. public evidence 通过路径和 secret 扫描。
5. `inspect-stage16g2-structured-file-tools --assert-complete` 通过。
6. Stage 16G.3 被允许开始，但 Stage 17B / Stage 20 / Stage 21 仍然保持 false。

如果 16G.2D 的 Todo-like 状态工具没有完成，可以将它作为非阻塞 follow-up 记录，但必须满足：

```text
P0 文件工具主线全部完成；
task_management_todo 明确标成 non-blocking；
acceptance summary 记录 remaining_followup；
Stage 16G.5 parity probe 会重新检查它。
```
