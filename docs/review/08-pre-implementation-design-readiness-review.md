# 正式实现前设计完备性审查

## 审查范围

本次审查面向“正式开始实现 RepoHarness 第一版之前，设计文档是否已经足够完整、明确、可落地”这个问题。

已阅读和对照的本地材料包括：

- `docs/00-reading-guide.md` 到 `docs/12-resume-narrative-and-demo-artifacts.md`。
- `docs/13-agentic-technical-report-reading-map.md`，只作为外部趋势阅读地图参考，不把其中尚未逐条核验的报告内容当作事实来源。
- `reference/claude-code-typescript-src/AGENT.md`。
- `reference/claude-code-typescript-src/Tool.ts`、`query.ts`、`tools.ts`、`services/tools/toolExecution.ts`、`services/tools/toolOrchestration.ts`、`tools/BashTool/BashTool.tsx`、`tools/BashTool/bashSecurity.ts`、`tools/FileEditTool/FileEditTool.ts` 等关键参考源码。
- `reference/claude-code-docs/` 下关于 agent loop、工具、权限、上下文、会话、子代理和模型上下文协议的说明文档。

为了校准“最近工业界 agentic coding 训练和评测的趋势”，本次也抽样查阅了一手公开资料，包括：

- OpenAI Codex 官方介绍和 Codex cloud 文档：强调独立云端执行环境、读写文件、运行测试、可追踪终端日志和测试输出，以及可配置的任务环境。
- Anthropic Claude Agent SDK 和 Claude Code hooks 文档：强调同一套 agent loop、工具、上下文管理、权限、会话、子代理、生命周期 hook 和无界面软件开发工具包能力。
- Cursor Composer 2 官方技术报告和论文页：强调在接近真实产品 harness 的环境中做强化学习，并用真实软件工程任务评测长轨迹 coding agent。
- Qwen3-Coder-Next 技术报告：强调可验证任务、可执行环境、环境反馈、工具调用格式鲁棒性、多 scaffold 轨迹、工具格式惩罚、未完成轨迹惩罚和防止 reward hacking 的命令与网络边界。

## 总体结论

当前 00 到 12 号设计文档已经不是玩具级设计。它覆盖了一个训练和评测导向的 coding agent harness 第一版必须具备的主干模块：任务适配、工作区生命周期、工具契约、权限和执行边界、agent loop、模型协议适配、上下文管理、验证器、奖励元数据、轨迹存储、训练导出、批量评测和 scaffold 对比。

和旧的审查记录相比，很多之前的高优先级缺口已经被补上。例如当前文档已经明确了 `ModelClient`、`ToolCallParser`、`ContextBuilder`、`ContextManager`、`RunRecorder`、`ArtifactRef`、`BaselineResult`、`PreparedMessages`、final verifier 的 strict patch replay、tool call 和 tool result 配对不变量、训练导出损失掩码、权限事件字段、网络策略和敏感路径策略。这说明当前设计已经可以支撑后续实现者进入代码层面的拆分工作。

但是，如果目标是“实现第一版可运行闭环”，仍不建议直接跳进 agent loop 主循环。当前剩下的问题主要不是方向错误，而是若干接口仍停留在“原则清楚，但工程入口不够硬”的状态。最需要在编码前补齐的是：第一版最小里程碑验收标准、最小命令行入口和 Eval Runner 操作面、scaffold 和 ContextBuilder 的职责冲突、Task Adapter 输出的初始验证器配置与 baseline 后验证计划的对象所有权、DependencyState 的具体实现策略、local process mode 的网络策略表述、TranscriptRecord 的精确定义、Accepted 判定规则、provider reasoning 内容处理策略、配置依赖选择和真实模型凭据策略。

我的判断是：可以开始实现准备工作，例如数据对象、配置读取、任务 schema 校验、运行目录和只读工作区工具；但在完成本文列出的 P0 修订前，不建议开始写真实模型驱动的长轨迹 agent loop、批量训练导出或真实仓库评测。

## 外部趋势对齐判断

当前设计和近期公开资料中的主线总体对齐。

OpenAI Codex、Cursor Composer 2 和 Qwen3-Coder-Next 都把 coding agent 能力放在“可执行环境、工具调用、环境反馈、最终验证、长轨迹行为”中评估，而不是只看单轮代码答案。RepoHarness 的 `task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export` 闭环正好对齐这个方向。

Cursor Composer 2 强调训练和部署使用接近一致的 harness，Qwen3-Coder-Next 强调多 scaffold 轨迹和工具格式鲁棒性。RepoHarness 当前把工具、workspace、verifier、trajectory store 和 scaffold 解耦，允许同一任务在 single-shot、simple ReAct、planner-coder-verifier 下比较，这是正确方向。

Qwen3-Coder-Next 和 Codex 相关资料都显示，真实 coding agent 必须防止通过网络、Git 历史、未来 commit 或测试环境漏洞取巧。当前文档已经把 `git clone`、`git fetch`、`git remote add`、`curl`、`wget`、`ssh`、`scp`、网络策略和敏感路径列入权限与执行边界，这一点非常重要。

当前设计略弱的地方是：真实任务常常描述不完整、需要跨文件理解、需要兼顾代码质量、成本、延迟和行为质量。`docs/07` 已有 patch size、turn count、tool call count 等指标，但代码质量、无进展检测、真实含糊任务和 prompt injection 风险还可以进一步明确为第二阶段评测维度。

## 逐文档审查

| 文档 | 当前完整度 | 编码前建议 |
| --- | --- | --- |
| `00-reading-guide.md` | 阅读路径、边界、术语和参考材料清楚。 | 增加“正式实现入口阅读路径”和“第一版最小可运行闭环验收清单”，让实现者知道先写哪些模块、哪些模块暂缓。 |
| `01-project-positioning-and-requirements.md` | 项目定位克制，非目标清楚，成功标准合理。 | 增加第一版实现里程碑，例如“3 到 5 个 micro-repo task 跑通闭环”和“20 到 50 个任务是后续扩展目标”，避免第一版目标过大。 |
| `02-system-architecture.md` | 分层架构和模块所有权表完整，关键不变量正确。 | 补充 Eval Runner 的最小命令入口和模块调用边界，例如 validate task、run one task、run batch、export。 |
| `03-agent-loop-and-message-protocol.md` | 当前是最完整的核心文档之一，模型客户端、消息协议、错误恢复、预算和三层结论都比较明确。 | 补充 provider reasoning 或 thinking 内容处理策略：哪些内容可保存、哪些内容只能作为 artifact、哪些内容不能进入训练导出。 |
| `04-tool-system-and-orchestration.md` | 工具清单、执行管线、Workspace Adapter 分工、并发和输出规范完整。 | 冻结第一版 model-facing 编辑工具选择。当前 `apply_patch` “可对模型开放，也可内部使用”的表述仍然会影响实现路径。还应把 `Tool.prompt` 或模型可见工具说明、`tool_version`、结果映射函数写入 Tool 契约。 |
| `05-workspace-sandbox-and-permissions.md` | 权限和执行边界分离非常清楚，命令、Git、网络、敏感路径和 timeout 策略都已覆盖。 | 明确 local process mode 下的网络策略只是命令层和配置层约束，不是操作系统级网络隔离。Docker execution mode 如果要断网，应写清 `--network=none` 或等价策略发生在哪个阶段。 |
| `06-task-dataset-and-environment-adapters.md` | 任务 schema、BaselineResult、三阶段 workspace 和任务质量门控已经很细。 | 把 Task Adapter 输出的初始 `VerifierConfig` 和 baseline 后生成的 `ResolvedVerifierPlan` 分开，避免“baseline 发现的信息进入 VerifierConfig”导致对象所有权混乱。`task_version` 已经在导出 metadata 中出现，但还需要进入任务定义层；同时补充 `dataset_split`、`source_kind` 和 decontamination metadata。 |
| `07-verifier-reward-and-evaluation.md` | 验证器、测试用例级结果、reward metadata、最终验收和指标都已覆盖。 | 明确 `accepted` 的确定性判定规则，例如是否要求所有 fail-to-pass 通过且所有 pass-to-pass 保持通过。当前文档已经覆盖 `fail_to_pass.total = 0`、flaky、invalid task 和 regression penalty 的一部分边界，仍需补充 patch apply failure、parser confidence 过低时的训练过滤、reward clipping 和 accepted policy version。 |
| `08-trajectory-store-and-training-export.md` | 运行目录、RunRecorder、ArtifactRef、events、导出格式、过滤和脱敏都比较完整。 | 增加 `TranscriptRecord` 的最小 schema，包括 `record_id`、`message_id`、`parent_message_id`、`turn`、`role`、`tool_call_id`、`context_revision`、`model_call_id` 和 artifact 引用。说明 recorder 追加写入、崩溃恢复和 finalize 的最小幂等策略。 |
| `09-agent-scaffolds-and-multi-agent.md` | 第一版 scaffold 边界克制，多代理非目标清楚。 | 当前 `Scaffold.build_initial_messages` 和 `ContextBuilder.build_initial_messages` 存在职责重叠。建议 scaffold 只提供 prompt fragment、allowed tools policy、phase transition 和 stop policy，最终初始 messages 仍由 ContextBuilder 统一构造。还要避免把 planner-coder-verifier 中的 verifier role 和正式 Verifier 模块混淆。 |
| `10-context-session-and-failure-diagnostics.md` | 上下文预算、替换状态、resume 降级、timeout 和失败诊断完整。 | 要么定义 `no_progress` 检测的第一版规则，要么把它标成后续扩展。否则实现者不知道何时可以用 `agent_stop_reason = "no_progress"`。 |
| `11-object-model-config-and-data-flow.md` | 这是实现交接最重要的对象模型文档，目录规划、RunConfig、核心对象和端到端数据流都比较完整。 | 增加 `PreparedMessages`、`TranscriptRecord`、`RunSummary`、`MetricsRecord`、`ResolvedVerifierPlan` 和 `ProviderCredentialPolicy`。另外需要决定 Python schema 技术栈，例如标准库 dataclass、Pydantic、PyYAML 或 ruamel.yaml。 |
| `12-resume-narrative-and-demo-artifacts.md` | 简历和展示叙事克制，示例 artifact 有帮助。 | 示例 task 仍使用 `timeout_sec` 这种兼容简写。建议改成和 `docs/06` 一致的 `timeouts.setup_timeout_sec`、`test_timeout_sec`、`agent_timeout_sec` 和 `final_verifier_timeout_sec`，避免展示文档反向制造歧义。 |

## 第一版实现前必须补齐的 P0 项

### P0-1：补一份最小可运行闭环的实现里程碑

当前文档说明了最终目标，但缺少“第一版到底验收什么”的硬边界。建议新增或补充一节，明确第一版最小闭环只要求：

1. 能加载 3 到 5 个 micro-repo task。
2. 能创建 source checkout、setup workspace、agent run workspace 和 verification workspace。
3. 能运行 baseline verifier 和 final verifier。
4. 能用 fake model 或 replay model 跑通 tool call 到 tool result 的协议。
5. 能实现 `read_file`、`grep`、`edit_file`、`bash`、`run_tests`、`git_diff` 的最小版本。
6. 能生成 `transcript.jsonl`、`events.jsonl`、`artifacts.json`、`final.patch`、`verifier.json`、`reward.json`、`metrics.json` 和 `summary.md`。
7. 能导出至少一条监督微调 JSONL 和一条 reinforcement learning rollout JSONL。

真实模型、多 scaffold 对比、20 到 50 个任务、preference pair 和 Docker mode 可以作为第一版之后的阶段，不要都压进第一个闭环。

### P0-2：修正 Scaffold 与 ContextBuilder 的职责冲突

`docs/03` 要求初始上下文由 `ContextBuilder` 统一构造，这是正确的；但 `docs/09` 的 scaffold 接口又包含 `build_initial_messages`。如果直接按这两个文档实现，很容易出现每个 scaffold 各自拼 prompt、绕过隐藏字段隔离和版本记录的问题。

建议把 scaffold 接口改成：

```text
Scaffold:
  scaffold_id
  scaffold_version
  system_prompt_fragment(task, run_config)
  context_requirements(task, run_config)
  allowed_tools(turn_state)
  next_phase(turn_state, tool_result, verifier_feedback)
  should_stop(state)
```

最终的 system message 和 user task message 仍由 `ContextBuilder.build_initial_messages(...)` 统一生成，并记录 `context_builder_version`、`prompt_template_version` 和 `scaffold_version`。

### P0-3：明确 VerifierConfig 与 ResolvedVerifierPlan 的对象所有权

当前 `docs/06` 一方面说 Task Adapter 输出 `VerifierConfig`，另一方面又说 baseline 中发现的 fail-to-pass 和 pass-to-pass 信息必须进入 `VerifierConfig`。`docs/11` 也仍然把 `VerifierConfig` 来源写成 Task Adapter。这会让实现者不清楚 baseline 之后到底是修改原始 task 配置，还是生成运行时验证计划。

建议拆成两个对象：

```text
VerifierConfig:
  来源: Task Adapter
  内容: task definition 中声明的 test command、timeout、parser、visibility policy、可选的预声明 fail_to_pass/pass_to_pass
  性质: 任务定义的静态验证器配置

ResolvedVerifierPlan:
  来源: Eval Runner + Workspace Adapter + Verifier baseline path
  内容: VerifierConfig + BaselineResult 中确认的 initial_fail_to_pass_tests、initial_pass_to_pass_tests、flaky_tests、parser_confidence、acceptance_policy_version
  性质: 正式 feedback verifier、final verifier、accepted 判定和 reward metadata 使用的运行时验证计划
```

这样 baseline 的结果不会反向污染 Task Adapter 的静态输出，也能保证 final verifier 和 reward metadata 使用的是同一份已解析、已门控的验证计划。

### P0-4：定义第一版命令行入口和 Eval Runner 操作面

当前文档有 `RunConfig` 和模块职责，但还没有明确第一版对外怎么运行。没有这个操作面，后续实现容易在“先写库接口”还是“先写可执行命令”之间摇摆，也难以形成端到端验收。

建议第一版至少定义这些入口：

```text
repo-harness validate-task <task_path>
repo-harness run-task <task_path> --config <run_config>
repo-harness run-batch --config <run_config>
repo-harness export <run_dir_or_runs_dir> --format sft_jsonl | rl_jsonl | preference_jsonl
repo-harness inspect-run <run_dir>
```

每个入口都应说明它调用哪些模块、写出哪些 artifacts、遇到 invalid 或 flaky task 时是否退出非零状态。这样 Eval Runner 的职责会更明确，第一版实现也更容易验收。

### P0-5：把 DependencyState 从概念变成可实现策略

当前文档反复要求捕获和恢复 `dependency_state`，但还没有定义第一版到底如何做到。这个对象如果不具体，workspace 生命周期会在实现时卡住。

建议第一版先支持保守策略：

```text
DependencyState:
  strategy: none | rerun_setup | copy_declared_paths | docker_image_layer
  cache_key
  artifact_ref
  restored_paths
  excluded_diff_paths
  created_after_setup_command
  excludes_baseline_side_effects
```

第一版可以先实现 `rerun_setup` 或 `copy_declared_paths`，并明确 baseline verifier 产生的测试缓存和日志不能进入 dependency state。Docker 镜像层缓存可以作为后续扩展。

### P0-6：明确 local process mode 的网络和安全表述

文档说 agent run 阶段默认关闭或强限制网络，这是正确目标。但如果第一版 local process mode 只是本机进程，通常无法真正做到操作系统级断网。

建议写清：

- local process mode 的 `network_policy = deny_agent_run` 第一版主要通过命令策略阻止 `curl`、`wget`、`git clone`、`git fetch`、`ssh`、`scp` 等网络入口，不声称操作系统级网络隔离。
- Docker execution mode 可以在 setup 阶段允许网络，在 agent run 和 final verifier 阶段使用无网络或受控网络配置。
- 所有网络相关拒绝都必须进入 permission event 和 tool result。

这样既能保持安全叙事，又不会把第一版实现说成生产级 sandbox。

### P0-7：补 TranscriptRecord 精确定义

`docs/08` 已经把 transcript 和 events 分开，但 transcript 目前仍偏语义描述。训练导出和 session replay 需要更硬的记录格式。

建议最小 schema：

```text
TranscriptRecord:
  schema_version
  record_id
  run_id
  task_id
  turn
  role: system | user | assistant | tool | verifier | termination
  message_id
  parent_message_id
  model_call_id
  tool_call_id
  tool_result_id
  context_revision
  content_preview
  content_artifact_refs
  model_visible
  trainable
  created_at
```

其中 `model_visible` 表示这条记录是否进入过模型上下文；`trainable` 表示导出时是否可以作为模型生成目标候选。不要让训练导出只能从自由文本 transcript 中猜。

### P0-8：定义 final verifier 的 accepted 规则和 reward 边界

`VerifierResult.accepted` 必须是确定性派生，而不是不同 parser 自由解释。建议第一版规则为：

- 如果 patch 无法应用到 verification workspace，`accepted = false`，`error_type = "patch_apply_failed"`。
- 如果测试命令无法启动，`accepted = false`，`error_type = "test_command_error"` 或 `dependency_error`。
- 如果 final verifier timeout，`accepted = false`，`final_verifier_status = "timeout"`。
- 如果存在 fail-to-pass tests，则必须全部通过。
- 如果存在 pass-to-pass tests，则必须全部保持通过。
- 如果没有声明 fail-to-pass 和 pass-to-pass，则可以退化为整体测试命令 exit code 为 0，但必须记录 `acceptance_policy_version`。

Reward metadata 已经部分覆盖缺失分母、flaky task、invalid task 和 regression penalty，但还应明确最终奖励范围、裁剪策略和低置信解析结果的训练过滤规则。例如 `final_reward` 是否限制在 `[0, 1]`，`parser_confidence` 低于阈值时是否 `invalid_for_training = true`，以及 accepted policy version 如何进入 reward evidence chain。

### P0-9：明确 provider reasoning 和隐藏思考内容的记录与导出策略

真实模型客户端可能返回普通文本、工具调用、原始响应、reasoning summary、隐藏 reasoning token 用量或 provider-specific thinking block。训练数据导出不能含糊处理这些字段。

建议增加：

- 默认 transcript 只保存模型可见的 assistant 文本和工具调用，不导出隐藏 chain-of-thought。
- provider 原始响应作为 artifact 保存时必须标注 `raw_provider_response_ref`、脱敏状态和保留策略。
- 如果供应商只返回 reasoning token usage，不返回内容，则只保存用量，不伪造内容。
- 如果返回 reasoning summary，必须标注 `reasoning_summary_provider` 和 `export_allowed`，默认不作为监督微调目标。

这能避免后续训练导出混入不应该训练或不具备授权语义的内部推理内容。

### P0-10：冻结第一版模型可见工具集

当前工具文档列出了 `edit_file`、`create_file`、`write_file` 和 `apply_patch`，但 `apply_patch` 是否暴露给模型仍是可选。第一版应避免编辑工具过多导致实现和训练协议分散。

建议冻结为：

- ReAct 类 scaffold：`list_files`、`read_file`、`grep`、`edit_file`、`create_file`、`run_tests`、`bash`、`git_diff`。
- single-shot patch scaffold：允许模型输出 patch，由 harness 内部调用 patch apply 能力。
- 第一版暂不把 `apply_patch` 同时暴露给所有 scaffold，除非明确说明它和 `edit_file` 的优先级、失败反馈和训练导出动作类型。

同时把 `Tool` 契约补成：

```text
Tool:
  name
  tool_version
  model_visible_description
  model_visible_prompt
  input_schema
  output_schema
  normalize_input
  validate_input
  check_permissions
  call
  map_result_to_model_observation
  is_read_only
  is_concurrency_safe
  is_destructive
  max_result_size
```

## 中优先级建议

### P1-1：增加 fake model 或 replay model

第一版 agent loop 最好先用 fake model 或 replay model 验证协议，而不是一开始接真实模型供应商。这个测试模型可以按预设脚本输出 tool call、无效 tool call、final answer、超长输出和重复调用，用来测试配对不变量、预算、权限拒绝和 transcript。

### P1-2：补充实现依赖选择

`pyproject.toml` 当前没有依赖。设计文档计划支持 YAML、schema 校验、命令行和可能的 Docker 操作。建议在实现前决定：

- YAML 解析使用 `PyYAML`、`ruamel.yaml`，还是第一版只支持 JSON。
- schema 使用标准库 dataclass、TypedDict，还是 Pydantic。
- 命令行入口使用 argparse、Typer，还是 click。
- 测试 parser 是否只支持 pytest。

这不是架构大问题，但会影响第一批代码结构。

### P1-3：补真实模型供应商凭据和脱敏策略

如果第一版只用 fake model 或 replay model，这一点不阻塞；如果第一版要接真实模型供应商，就需要提前定义 `ProviderCredentialPolicy`。

建议最小覆盖：

- API key 和 base URL 只从环境变量或本地未提交配置读取。
- `RunConfig` 和 artifacts 默认不保存明文凭据。
- `raw_provider_request_ref` 和 `raw_provider_response_ref` 写入前或导出前需要经过 provider-specific secret redaction。
- 鉴权失败要进入 `ModelCallEvent.model_error_type = "auth_error"` 或等价字段。
- summary 和 metrics 只记录 provider、model id、request id、token usage 和错误类型，不记录密钥。

### P1-4：给 prompt injection 和不可信仓库文档一个明确边界

Context Builder 会读取 `README`、`AGENT.md`、`CLAUDE.md` 或其他项目文档摘要。真实仓库文档可能包含恶意指令。建议写清：

- 仓库文件内容是任务上下文，不是高优先级系统指令。
- Context Builder 注入项目说明时要标注它来自仓库文件，不能覆盖系统安全规则、权限规则和隐藏 evaluator metadata。
- 未来进入真实仓库前，可以增加 prompt injection 诊断事件或过滤策略。

### P1-5：定义 `no_progress` 或暂缓它

`docs/10` 把 `no_progress` 作为失败类型，但未定义触发规则。第一版可以先不实现；如果要实现，建议用非常简单的规则，例如连续 N 次 `run_tests` 失败类型相同且 diff 没有变化，或者连续 N 轮只有相同无效工具调用。

### P1-6：补任务定义层的版本、split 和污染控制字段

如果后续轨迹要用于训练，任务必须能说明来源和版本。`docs/08` 的 export metadata 已经出现了 `task_version`，但 `docs/06` 的任务 schema 和 `docs/11` 的 `TaskDefinition` 还没有把这些字段作为任务定义的一部分。建议补充：

```text
task_version
dataset_name
dataset_split
source_kind: hand_written | synthetic | pr_mined | benchmark_import
created_at
decontamination_status
overlap_check_notes
```

第一版手工 micro-repo task 也可以填写这些字段，后续扩展到公开 benchmark 或真实 Pull Request 时会更稳。

### P1-7：增加代码质量和行为质量指标的扩展位

当前 metrics 偏功能正确性和运行成本。可以预留但不强制实现：

- code quality check result，例如 lint、type check、format check。
- interaction efficiency，例如无效工具调用率、重复读取率、过度测试率。
- patch locality，例如是否修改了 expected files 之外的大量文件。
- instruction adherence，例如是否修改了任务不允许修改的文件。

这些指标和 Cursor Composer 2 报告中“真实开发任务不仅看功能正确性”的方向一致，但不必阻塞第一版闭环。

## 建议的第一版实现顺序

1. 定义核心 schema：`RunConfig`、`TaskDefinition`、`RunnableTask`、`VerifierConfig`、`ResolvedVerifierPlan`、`RunWorkspace`、`ArtifactRef`、`TrajectoryEvent`、`TranscriptRecord`、`VerifierResult`、`RewardMetadata`。
2. 定义最小命令行入口和 Eval Runner 操作面：先让 validate task、run task、run batch、export 和 inspect run 有清楚的输入输出边界。
3. 实现 `RunRecorder` 和 run directory：先保证事件、transcript、artifact manifest 可以稳定写入。
4. 实现 task loader 和 micro-repo fixtures：先支持 JSON 或 YAML 中的一种格式。
5. 实现 Workspace Adapter local process mode：复制仓库、运行 setup、捕获 diff、应用 patch、保存 stdout/stderr artifact。
6. 实现 pytest verifier：baseline、feedback 和 final 共用 parser，并在 baseline 后生成 `ResolvedVerifierPlan`。
7. 实现只读工具和编辑工具：`list_files`、`read_file`、`grep`、`edit_file`、`create_file`、`git_diff`。
8. 实现 `run_tests` 和受限 `bash`：测试命令路由到 verifier feedback path。
9. 用 fake model 跑通 agent loop：验证 tool call / tool result 配对、预算、权限拒绝和终止原因。
10. 接入第一个真实 Model Client：只实现一种 provider 和一种工具调用格式。
11. 实现 training export：先导出 SFT JSONL 和 reinforcement learning rollout JSONL，再做 preference pair。
12. 加 simple ReAct 和 single-shot patch 对比。
13. 最后再扩展 Docker execution mode、planner-coder-verifier 和 20 到 50 个任务批量评测。

## 最终判断

当前设计已经包含第一版 agent harness 的主要组件，没有遗漏“必须存在的大模块”。真正剩下的是若干需要在编码前落地的协议细节和边界澄清。

如果按本文 P0 项先修订，RepoHarness 的设计就足够支撑一个可实现、可复盘、可导出训练轨迹的第一版。修订后可以放心进入工程实现，并且应该先从 schema、recorder、workspace、verifier 和 fake model 协议测试开始，而不是直接写真实模型长轨迹循环。

## 参考资料

- [OpenAI: Introducing Codex](https://openai.com/index/introducing-codex/)
- [OpenAI Developers: Codex cloud](https://developers.openai.com/codex/cloud)
- [Anthropic: Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- [Anthropic: Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
- [Cursor: A technical report on Composer 2](https://cursor.com/blog/composer-2-technical-report)
- [Composer 2 Technical Report on arXiv](https://arxiv.org/abs/2603.24477)
- [Qwen3-Coder-Next Technical Report on arXiv](https://arxiv.org/abs/2603.00729)
