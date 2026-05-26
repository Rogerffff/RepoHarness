# Stage 16G.1 到 Stage 16G.6 执行计划：面向 Claude Code 风格 SWE 强化学习的工具能力补齐

## 1. 阶段定位

Stage 16G.0 已经完成两层工作：

1. 第一轮只读盘点、差距矩阵和小型可执行 probe。
2. follow-up 基线契约，补齐 Claude Code 风格工具环境、mini-SWE-agent 风格 Bash-first 环境和 RepoHarness 当前状态的逐能力对照。

本文件是 Stage 16G.1 到 Stage 16G.6 的后续执行计划。它的目标不是进入 Stage 17 数据 registry，也不是为了追求“开放完整 shell”而扩大能力，而是按 Stage 16G.0 已确认的 27 条逐能力对照和 17 条主 SWE 强化学习阻塞项，补齐 RepoHarness 作为真实软件工程智能体训练环境所需的工具面、权限边界、诊断能力、补丁审计和训练资格门禁。

Stage 16G 后续阶段的中心判断是：

```text
RepoHarness 的主 SWE 强化学习工具面必须覆盖 Claude Code 和 mini-SWE-agent 都证明重要的真实软件工程能力，
但实现形态应采用结构化、公开、可审计、可训练的工具 profile，
而不是把模型直接放进无约束宿主 shell。
```

## 2. 依据文件

后续阶段必须以 Stage 16G.0 follow-up 产物作为权威输入，不能重新回到“凭感觉补工具”。

关键输入文件：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_claude_code_baseline_contract.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_mini_swe_agent_baseline_contract.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_per_capability_baseline_comparison.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_stage16g_implementation_requirements.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_followup_acceptance_summary.json
```

后续每一个 Stage 16G.1 到 Stage 16G.4 的实现项都必须能追溯到 `capability_id`。如果实现过程中发现新的关键差距，必须先更新对照记录和 requirement，再进入行为代码修改。

## 3. 全局设计原则

### 3.1 主训练工具面采用结构化公开命令优先

RepoHarness 不应把 mini-SWE-agent 的 Bash-first 设计误读为“开放完整 shell 才真实”。mini-SWE-agent 给出的最低要求是：模型必须能稳定执行公开诊断命令、公开测试、复现脚本、文件查看、搜索、编辑和补丁生成。RepoHarness 可以用更结构化、更可审计的方式覆盖这些能力。

主 SWE 强化学习 core profile 采用下面的方向：

```text
Read / Grep / Glob / Edit / Write / ApplyPatch 等结构化工具负责主要源码操作。
run_public_command 负责安全公开命令。
run_project_test 负责项目测试命令路由。
scratch_python 负责临时复现脚本。
persistent diagnostic shell 只进入 swe_public_extended profile，不进入 core 默认。
```

### 3.2 安全边界依赖确定性隔离，不依赖削弱能力

Stage 16G 后续不通过继续压缩工具能力来制造安全感。防止 reward hacking 和信息泄漏应依赖下面这些确定性边界：

```text
workspace sandbox
公开路径和私有路径隔离
默认无网络
共享依赖只读
任务间 session reset
每次调用静态扫描或 AST 扫描
hidden verifier / gold patch / test patch / runtime-private 隔离
raw artifact 私有化
路径脱敏
final patch hygiene
训练资格门禁
quarantine 和监控记录
```

### 3.3 工具能力必须进入训练目标，而不只是运行成功

Stage 16G.1 到 Stage 16G.4 的任何新工具，如果不能被投影到 trajectory、TrainingView、final patch、verifier metadata、reward metadata 或 export eligibility 中，就不能视为完成。真实目标是“模型学到正确工具使用策略”，不是单独让某个命令能跑通。

### 3.4 诊断侧通道和正式训练工具面必须分层

Stage 16G 后续必须明确区分：

```text
safe_structured_only：只允许结构化读写搜索和 final patch 的低风险 profile。
swe_public_core：主 SWE 强化学习默认 profile，包含结构化文件工具、公开命令、项目测试和 scratch Python。
swe_public_extended：包含 persistent diagnostic shell、长会话诊断和更复杂项目环境的扩展 profile。
redteam_restricted：用于安全验证、泄漏测试和拒绝恢复训练，不作为主训练默认 profile。
```

### 3.5 所有新能力必须绑定 run_episode 统一入口

Stage 16F 已经把新评测和训练入口收敛到 `run-episode-task` / `RepoHarnessRuntime.run_episode(real_episode)`。Stage 16G 后续新增的工具、profile、scaffold 暴露、public environment 提示和训练投影，都必须通过这个统一入口可用并可验收。

旧 `run_task(...)` 只能作为 legacy compatibility 路径存在，不能成为 Stage 16G 新工具能力、训练轨迹或 acceptance evidence 的主事实来源。

### 3.6 工具存在不等于模型可学会使用

每个新增或改造的工具能力都必须同时验证下面几层是否一致：

```text
tool schema
模型可见工具说明
public environment 提示
scaffold / profile 暴露
权限拒绝和恢复提示
tool event / TrainingView / export projection
```

如果工具已经实现，但默认目标 profile 不暴露、提示语没有说明、拒绝结果不可学习，或者轨迹投影缺失，该能力不能视为完成。

## 4. 总体阶段拆分

推荐阶段顺序如下：

```text
16G.1  工具 registry、profile taxonomy 和训练资格门禁设计
16G.2  结构化文件、补丁和工作区修改工具面
16G.3  公开命令、项目测试命令路由和 scratch Python
16G.4  受控诊断 shell、依赖环境和权限恢复
16G.5  Claude Code / mini-SWE-agent 改造后 parity probe
16G.6  主 SWE 强化学习工具 profile 冻结和训练放行门禁
```

其中 Stage 16G.1 到 Stage 16G.4 是实现阶段；Stage 16G.5 是改造后的实证 probe；Stage 16G.6 是进入 Stage 17 之后真实数据冻结和 Stage 20 warm-start 之前的工具面冻结门禁。

Stage 16G.5 不能再承担“第一次认真对比 Claude Code 和 mini-SWE-agent”的职责。这个职责已经由 Stage 16G.0 follow-up 完成。Stage 16G.5 只验证改造结果是否达到既定 baseline contract。

## 5. Stage 16G.1：工具 registry、profile taxonomy 和训练资格门禁设计

### 5.1 目标

Stage 16G.1 先建立一个可执行的工具能力 registry，使后续实现不再散落在 scaffold、tool executor、command policy 和 export projection 之间。

Stage 16G.1 必须回答：

1. 每个模型可见工具属于哪个 profile。
2. 每个工具对应哪些 `capability_id`。
3. 每个工具的输入、输出、拒绝、artifact、权限和训练投影语义是什么。
4. 哪些工具调用可以进入主 SWE 强化学习 policy loss。
5. 哪些工具调用只能作为诊断、偏好数据、负样本或 quarantine 信号。

### 5.2 必须覆盖的能力

来自 Stage 16G.0 follow-up 的直接输入：

```text
bash_or_public_command_execution
training_eligibility_and_export_projection
permission_approval_denial_recovery
tool_result_truncation_raw_artifact_privacy
sandbox_workspace_and_runtime_private_boundary
```

### 5.3 主要产物

建议产物：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_tool_registry_contract.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_profile_taxonomy.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_training_eligibility_gate_spec.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_profile_registry_inspection_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_acceptance_summary.json
```

如果实现中新增代码，应优先落在 registry、schema、profile 配置和 tests，而不是直接先改 `execute_bash` 或 `diagnostic_shell`。

Stage 16G.1 必须新增或复用一个机器验收入口，例如：

```text
repo-harness inspect-stage16g1-tool-profile <stage16g1_acceptance_summary.json> --assert-complete
```

具体命令名可在实现时调整，但必须满足同等机器验收能力，不能只依赖人工阅读 JSON。

### 5.4 验收条件

Stage 16G.1 完成时必须满足：

1. Stage 16G.0 的 27 条 `capability_id` 都能映射到 profile、阶段或明确的 post-16G optional 状态。
2. 所有阻塞主 SWE 强化学习的能力都能映射到 Stage 16G.2、Stage 16G.3 或 Stage 16G.4。
3. `swe_public_core` 不包含 persistent shell。
4. `swe_public_extended` 可以包含 persistent diagnostic shell，但必须要求 session reset、artifact hygiene 和路径脱敏。
5. 每个工具都有 `allowed_artifact_visibility`、`training_projection_policy` 和 `denial_feedback_policy`。
6. 新增 registry 检查必须能阻止“工具存在但没有训练投影”的静默退化。
7. `post_16G_optional` 能力也必须显式进入 registry，并写清 `schema_reserved`、`not_main_swe_rl_blocking_reason` 和 `revisit_stage`，避免后续被误读成遗漏。
8. 机器验收器能校验 27 条 capability 是否全部映射、17 条 blocking capability 是否都有 owner stage、每个工具是否都有 artifact visibility、training projection 和 denial policy。
9. 机器验收器能校验每个候选 profile 的模型可见 schema、scaffold 暴露、public environment 提示和拒绝恢复提示是否存在一致性声明。
10. 至少一个 `run-episode-task` / `run_episode(real_episode)` smoke 证明 registry 和 profile 能通过统一入口被加载或投影。

### 5.5 非目标

Stage 16G.1 不实现新工具能力，不放宽 shell，不运行大规模 SWE-bench，不冻结真实训练数据。

## 6. Stage 16G.2：结构化文件、补丁和工作区修改工具面

### 6.1 目标

Stage 16G.2 补齐 Claude Code 风格结构化文件操作和 mini-SWE-agent 通过 shell 已经具备的文件修改能力，同时保持 RepoHarness 的可审计优势。

当前 Stage 16G.0 follow-up 明确指出，RepoHarness 已有 `read_file`、`grep`、`glob_files`、`edit_file` 和 `create_file`，但仍缺少足够强的多文件 patch、覆盖写入、删除、移动和目录操作能力。复杂 SWE 任务如果只能依赖 exact replace，会鼓励模型做更少、更局部、更保守的修改，甚至绕开公开验证。

### 6.2 子阶段建议

为了避免 Stage 16G.2 过重，建议拆成四个子阶段：

```text
16G.2A  结构化文件工具 schema 和 profile 暴露
16G.2B  apply_patch / write_file / delete_file / move_file / mkdir 行为实现
16G.2C  patch hygiene、final.patch、official prediction 和 TrainingView 投影
16G.2D  task state / Todo-like tool projection 和 update_working_state 对齐，P2 non-blocking
```

### 6.3 必须覆盖的能力

P0 文件和补丁能力：

```text
structured_edit_existing_file
structured_write_or_create_file
apply_patch_or_multi_file_edit
delete_move_mkdir_file_operations
```

配套但不阻塞 Stage 16G.2 P0 文件工具主线的能力：

```text
git_diff_status_and_patch_capture
task_management_todo
```

### 6.4 设计要求

1. 文件修改仍应优先走结构化工具，不鼓励模型用 shell 重定向或 Python 脚本直接改源码。
2. `apply_patch` 或等价多文件编辑工具必须支持多文件修改、新增文件、删除文件和上下文失败反馈。
3. `write_file` 或 `create_file` 必须明确区分“只新建”“覆盖写入”“已存在时报错”等语义。
4. 删除、移动、目录创建必须进入 final patch 和 export projection，不能只改工作区但丢失审计。
5. patch apply failure、路径不存在、上下文不匹配、越界路径、二进制文件拒绝等结果必须返回结构化恢复信息。
6. 新增工具必须保留 read-before-edit 或等价审计要求，避免模型盲目覆盖未知文件。
7. `update_working_state` 必须被明确评估：是保留为轻量任务状态工具，还是升级为 Claude Code `TodoWrite` 等价能力。无论选择哪种形态，都要进入 trajectory、TrainingView 和训练投影策略，而不是只作为提示层装饰。
8. Stage 16G.2 只负责把文件、补丁和任务状态动作投影到后续 verifier / reward 所需的结构化事实中；完整 `final_answer_verifier_reward_linkage` 仍归 Stage 16G.4D 收口。
9. `task_management_todo` 和 `git_diff_status_and_patch_capture` 不能阻塞 `apply_patch`、`write_file`、`delete_file`、`move_file`、`mkdir` 这些 P0 文件工具完成；它们应作为 16G.2D 或 Stage 16G.5 parity 的补充验收项处理。
10. 新增文件工具必须通过 `run_episode(real_episode)` 统一入口可见，不能只在旧 `run_task(...)` 或局部工具单测中可用。

### 6.5 验收条件

Stage 16G.2 完成时必须有可执行 probe 覆盖：

1. 多文件 patch 成功进入 `final.patch`。
2. 新建文件、删除文件、移动文件和目录创建进入 git diff 与 export projection。
3. patch 失败返回可学习的 `reason_code`、`retryable` 和安全替代建议。
4. 通用临时目录、忽略目录和非追踪 artifact 不会被误纳入 final patch。
5. hidden verifier、gold patch、test patch 和 runtime-private 路径仍不可读写。
6. 结构化文件工具的 tool event 能进入 TrainingView 和后续 reward metadata 候选。
7. task state / Todo-like 工具的模型可见语义、轨迹投影和训练投影策略已经明确。
8. 目标 scaffold / profile 中的模型可见工具说明、public environment 提示和实际 executor registry 对齐。

## 7. Stage 16G.3：公开命令、项目测试命令路由和 scratch Python

### 7.1 目标

Stage 16G.3 是让 RepoHarness 不再弱于 mini-SWE-agent 动态诊断能力的关键阶段。它不开放裸 shell，而是提供可审计的公开命令工具，使模型能够运行真实 SWE 任务中必要的项目命令、定向测试和复现脚本。

Stage 16G.0 follow-up 已经明确：`execute_bash` 当前是窄但非空的安全子集，它允许安全搜索、部分安全 Git 子集、`pytest` 和受限 Python 诊断。但它还不足以作为主 SWE 强化学习默认工具面，因为项目测试命令路由、scratch Python 和公开诊断反馈没有形成稳定、明确、可训练的工具契约。

### 7.2 子阶段建议

Stage 16G.3 风险较高，建议拆成四个子阶段：

```text
16G.3A  shared public command execution substrate：cwd、timeout、输出脱敏、artifact、拒绝语义和审计事件
16G.3B  run_public_command：受控公开命令工具和通用 public command policy
16G.3C  run_project_test：基于共享底座的项目测试命令路由和参数化公开测试
16G.3D  scratch_python：基于共享底座的临时复现脚本、公开诊断 artifact 和 mini-SWE-agent 能力覆盖 probe
```

如果 Stage 16G.3A 不能先给出可靠的共享执行底座、拒绝语义、输出脱敏、artifact 规则和私有路径隔离，Stage 16G.3B 到 Stage 16G.3D 不应继续扩大命令集合。

### 7.3 必须覆盖的能力

```text
bash_or_public_command_execution
parameterized_public_test_command
scratch_python_or_reproduction_script
project_command_routing
tool_result_truncation_raw_artifact_privacy
permission_approval_denial_recovery
```

### 7.4 设计要求

1. `run_project_test` 应优先支持项目声明的公开测试入口，而不是让模型猜测复杂命令。
2. `run_project_test` 必须支持定向测试，例如单个 pytest 文件、单个测试函数、Django test label、Sphinx 或项目自定义 public smoke command。
3. `scratch_python` 必须在临时目录或临时 artifact 空间执行，默认不进入 final patch。
4. `scratch_python` 可以读取公开工作区源码和公开依赖，但不能读取 hidden verifier、gold patch、test patch 或 runtime-private 路径。
5. `run_public_command` 必须限制到公开诊断和项目命令，不允许成为宿主 shell 后门。
6. 所有拒绝都必须包含结构化字段，例如 `reason_code`、`policy_version`、`retryable`、`safe_alternative_tool` 或 `safe_rewrite_example`。
7. stdout、stderr、exit code、截断信息和 raw artifact 指针必须分层：模型可见内容公开，原始 artifact 私有，export 只包含 public-safe projection。
8. Stage 16G.3 的 probe 只使用依赖已经预置的公开环境。依赖安装、共享缓存、private overlay 和复杂环境 setup 到 Stage 16G.4A 才放行。
9. `run_public_command`、`run_project_test` 和 `scratch_python` 必须复用同一套 cwd、timeout、输出脱敏、artifact visibility、权限拒绝和 audit 语义，不能各自实现一套不兼容的执行规则。
10. 三个工具都必须通过 `run_episode(real_episode)` 统一入口可见，并且 profile / scaffold 暴露和模型可见说明一致。

### 7.5 验收条件

Stage 16G.3 完成时必须有 probe 证明：

1. 模型能运行一个公开定向测试并收到 stdout、stderr 和 exit code。
2. 模型能运行 scratch Python 复现脚本，脚本产物不会污染 final patch。
3. 项目命令 routing 能从 task 或 public environment 配置中选择合适命令。
4. 被拒绝的命令返回可学习恢复路径，而不是只返回“权限不足”。
5. 访问 hidden verifier、gold patch、test patch、`.git` 作弊路径、宿主绝对路径或共享依赖写入会 deterministic hard fail。
6. 至少一个 mini-SWE-agent 风格动态诊断闭环可以用结构化 public tools 完成。
7. Stage 16G.3 probe 明确标注其依赖前置条件；如果某个项目命令失败是因为 Stage 16G.4A 尚未实现 dependency setup，不能误判为 public command 工具本身通过或失败。
8. `run_public_command`、`run_project_test` 和 `scratch_python` 的 tool result 结构、截断策略、raw artifact 私有化和拒绝恢复字段一致。

## 8. Stage 16G.4：受控诊断 shell、依赖环境和权限恢复

### 8.1 目标

Stage 16G.4 收口更复杂的真实 SWE agent 能力，包括 persistent diagnostic session、依赖 setup、环境隔离、权限恢复、hooks 审计、训练投影、final answer 和 reward linkage。

这部分在 Stage 16G.0 follow-up 中映射了最多阻塞能力，因此必须拆开执行，不能一次性做成一个不可复核的大改。

### 8.2 子阶段建议

建议拆成四个子阶段：

```text
16G.4A  dependency setup、共享依赖只读策略和 private overlay
16G.4B  persistent diagnostic shell 进入 swe_public_extended profile
16G.4C  权限拒绝恢复、hooks、tool lifecycle audit 和 quarantine
16G.4D  final answer、verifier、reward metadata、TrainingView 和 export linkage
```

### 8.3 必须覆盖的能力

```text
persistent_diagnostic_session
dependency_setup_and_environment_policy
final_answer_verifier_reward_linkage
permission_approval_denial_recovery
sandbox_workspace_and_runtime_private_boundary
tool_result_truncation_raw_artifact_privacy
hooks_tool_lifecycle_audit
training_eligibility_and_export_projection
reward_hacking_monitoring_and_quarantine
```

### 8.4 设计要求

1. Persistent diagnostic shell 只进入 `swe_public_extended`，不进入 `swe_public_core` 默认 profile。
2. 任务之间必须 reset shell session、工作目录、环境变量、临时文件和 artifact namespace。
3. dependency setup 必须区分公开依赖安装、只读共享缓存、任务私有 overlay 和禁止写入区域。
4. 依赖安装和项目命令必须记录可复现 metadata，例如命令、退出码、公开输出摘要、耗时和 artifact 指针。
5. 权限拒绝不应只作为异常处理，也要成为模型可学习的恢复信号。
6. hooks 和 tool lifecycle audit 必须能记录 tool start、tool finish、拒绝、超时、截断、artifact 生成和 quarantine 原因。
7. final answer 中的测试声明必须能和 tool events 或 verifier summary 交叉校验。
8. Stage 16G.4 只负责产出公开安全的诊断质量、权限拒绝恢复、假验证、过宽修改、quarantine 等结构化 facts，并接入 reward metadata / quarantine。具体数值型 process reward、权重和训练目标设计留给后续 reward builder 阶段，不能在 Stage 16G.4 提前展开成 Stage 19 级别的奖励设计。
9. Stage 16G.4 新增或收口的工具投影必须通过 `run_episode(real_episode)` 统一入口验证，旧 `run_task(...)` 只能作为兼容路径检查。

### 8.5 验收条件

Stage 16G.4 完成时必须有 probe 证明：

1. `swe_public_core` 不暴露 persistent shell。
2. `swe_public_extended` 中 persistent shell 的 public-safe projection 可审计，并且任务间 reset。
3. 共享依赖缓存不能被任务写入污染。
4. private overlay、runtime-private 路径、hidden verifier 和 gold/test patch 仍被隔离。
5. permission denial、timeout、truncation、artifact readback、quarantine 都能进入 audit。
6. final answer 测试声明能和真实工具事件或 verifier metadata 对齐。
7. TrainingView、trajectory export、reward metadata 和 official prediction 中的工具投影一致。
8. 模型可见提示、scaffold / profile 暴露、public environment 描述和实际 runtime 工具集合一致。

## 9. Stage 16G.5：改造后的 Claude Code / mini-SWE-agent parity probe

### 9.1 目标

Stage 16G.5 是实证验证阶段。它不再承担第一次 baseline 对照，而是验证 Stage 16G.1 到 Stage 16G.4 的实现是否真正让 RepoHarness 接近目标工具环境。

### 9.2 probe 维度

Stage 16G.5 至少覆盖：

1. Claude Code 分层工具能力：Read、Grep、Glob、Edit、Write、ApplyPatch、Bash 类公开命令、任务管理、artifact 回读、权限拒绝和 final answer 收口。
2. mini-SWE-agent 动态诊断能力：稳定公开命令闭环、stdout / stderr / exit code 反馈、定向测试、scratch Python、项目命令和文件修改闭环。
3. RepoHarness 安全边界：hidden verifier、gold patch、test patch、Git history 作弊、runtime-private 路径、宿主绝对路径、共享依赖污染和 raw artifact 泄漏。
4. 训练投影：工具事件是否进入 TrainingView、reward metadata、trajectory export 和训练资格门禁。

### 9.3 验收条件

Stage 16G.5 完成时必须输出：

```text
stage16g5_parity_probe_summary.json
stage16g5_claude_code_capability_probe_report.json
stage16g5_mini_swe_agent_capability_probe_report.json
stage16g5_training_projection_probe_report.json
stage16g5_safety_boundary_probe_report.json
```

通过条件：

1. 所有 Stage 16G.0 blocking capability 都有 probe 结果。
2. 所有 P0 blocking capability 必须在 `swe_public_core` 或计划明确声明的目标 profile 中通过。
3. 任意 P0 blocking capability 失败时，`stage16g5_status` 必须为 `failed`。
4. 所有失败项都有明确 owner stage、修复建议和重新 probe 条件。
5. 新发现差距必须回写 baseline comparison 或 requirements。
6. 任意 P0 blocking capability 失败时，Stage 16G.6 必须把 `stage17b_real_data_freeze_allowed`、`stage20_warm_start_data_generation_allowed` 和 `stage21_formal_rl_allowed` 全部置为 `false`。

## 10. Stage 16G.6：主 SWE 强化学习工具 profile 冻结和训练放行门禁

### 10.1 目标

Stage 16G.6 是进入后续训练基础设施阶段之前的纯冻结和证据汇总门禁。它的职责不是再新增能力，而是把已经实现并通过 parity probe 的工具面冻结成可以进入数据 registry、轨迹 schema、reward builder 和 warm-start 数据生产的 profile。

Stage 16G.6 解决的问题是：

```text
哪些工具、哪些 profile、哪些任务、哪些轨迹，可以被认定为主 SWE 强化学习训练合格数据？
```

Stage 16G.6 不新增工具、不改变工具语义、不补实现、不放宽权限。如果 Stage 16G.6 发现缺口，只能把 gate 置为不放行，并把问题退回 Stage 16G.1 到 Stage 16G.5 的 owner stage。

Stage 16G.6 必须绑定下面这些输入证据的 sha256：

```text
Stage 16G.1 registry / profile / training eligibility gate 产物
Stage 16G.4 projection、reward linkage、audit 和 quarantine 产物
Stage 16G.5 parity probe 产物
Stage 16G.0 baseline comparison 和 implementation requirements 产物
```

### 10.2 必须冻结的内容

1. `safe_structured_only`、`swe_public_core`、`swe_public_extended`、`redteam_restricted` 的最终字段和工具集合。
2. 主 SWE 强化学习默认 profile，预计为 `swe_public_core`。
3. `swe_public_extended` 进入训练的条件，例如只用于特定任务类型、特定 replay、偏好数据或 diagnostic augmentation。
4. 所有工具的训练投影策略：policy loss、SFT、preference、negative sample、quarantine、auxiliary reward 或 diagnostic-only。
5. 所有 hard-fail 安全边界。
6. 所有公开 artifact 和私有 artifact 的导出规则。
7. Stage 17 数据 registry、Stage 20 warm-start 和 Stage 21 formal RL 的放行条件。

### 10.3 验收条件

Stage 16G.6 完成时必须输出一个明确 gate：

```json
{
  "stage17a_schema_only_allowed": true,
  "stage17b_real_data_freeze_allowed": "<true-or-false>",
  "stage20_warm_start_data_generation_allowed": "<true-or-false>",
  "stage21_formal_rl_allowed": "<true-or-false>"
}
```

如果 `stage17b_real_data_freeze_allowed`、`stage20_warm_start_data_generation_allowed` 或 `stage21_formal_rl_allowed` 为 `false`，必须列出阻塞项、对应 capability、owner stage 和最小修复条件。

## 11. 风险控制

### 11.1 过度保守风险

如果 Stage 16G 后续继续把公开测试、项目命令、scratch Python 和复现脚本排除在主训练工具面之外，RepoHarness 会继续鼓励模型静态猜测，训练结果会偏离 Claude Code 风格真实工具使用能力。

缓解方式：

1. Stage 16G.3 必须把公开动态诊断能力纳入 `swe_public_core`。
2. 工具拒绝必须可学习，而不是只产生无信息失败。
3. parity probe 必须包含 mini-SWE-agent 风格的动态闭环。

### 11.2 过度放开风险

如果 Stage 16G 后续直接开放完整 shell，可能重新引入 hidden leakage、gold patch/test patch 泄漏、Git history 作弊、共享依赖污染、runtime-private 泄漏和宿主路径访问。

缓解方式：

1. `run_public_command` 和 `scratch_python` 必须按公开能力白名单和路径策略执行。
2. Persistent shell 只进入 `swe_public_extended`，默认不进入主 profile。
3. 所有工具都必须经过 artifact hygiene、路径脱敏和 training eligibility gate。

### 11.3 阶段过重风险

Stage 16G.3 和 Stage 16G.4 都容易过重。执行时应坚持子阶段验收，尤其是：

1. 没有 Stage 16G.3A 的拒绝语义和私有路径隔离，不进入 Stage 16G.3D。
2. 没有 Stage 16G.4A 的依赖环境隔离，不进入 Stage 16G.4B 的 persistent shell。
3. 没有 Stage 16G.4D 的训练投影，不进入 Stage 16G.5 parity probe。

## 12. 不进入 Stage 17 的条件

Stage 16G 后续完成前，下面工作不应启动：

1. 大规模真实 SWE 轨迹冻结。
2. 主 SWE 强化学习 warm-start 数据生产。
3. 正式 policy loss 训练。
4. 把现有过窄工具面产出的轨迹当成 Claude Code 风格工具使用数据。

允许继续做的工作：

1. Stage 17A schema-only 设计。
2. 数据 registry 的空 schema、字段命名和兼容性讨论。
3. 不依赖真实轨迹冻结的 inspector 或离线文档工作。

## 13. 推荐执行顺序摘要

最小可执行顺序：

```text
16G.1 registry/profile/gate
-> 16G.2A-2C structured file and patch tools
-> 16G.3A command policy and denial semantics
-> 16G.3B project tests
-> 16G.3C scratch Python
-> 16G.3D public command probe
-> 16G.4A dependency environment
-> 16G.4B extended diagnostic shell
-> 16G.4C permission/audit/quarantine
-> 16G.4D verifier/reward/export linkage
-> 16G.5 parity probe
-> 16G.6 training eligibility freeze
```

这个顺序的关键取舍是：先固定工具契约，再补文件和补丁能力，再补公开动态诊断能力，最后再处理持久 shell 和训练放行。这样可以避免在目标 profile 未确定前盲目扩 shell，也可以避免在工具投影未完成前把新能力误纳入训练数据。
