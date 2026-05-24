# 跨工作树同步与 run_episode 统一入口设计

创建时间：2026-05-24

状态：设计草案，供训练链路工作树和测评工作树共同审查。

## 1. 一句话结论

RepoHarness 后续不应该长期保持“测评主要走 `run_task(...)`，训练主要走 `run_episode(real_episode)`”这两条独立 Harness 入口。更稳的方向是：

```text
run_episode(real_episode) 成为测评、轨迹采集、强化学习 rollout 的唯一 canonical Harness 执行入口。

run_task(...)、run-batch、旧导出命令逐步变成兼容包装层，或者迁移到 run_episode 产物之上。
```

同时，当前训练链路工作树和 SWE-Bench 测评工作树已经出现实质重叠。测评工作树发现的工具能力、诊断 shell、patch hygiene、official verifier 和公开测试入口问题，都会直接影响训练样本质量。因此两个工作树需要先回到一个共同的 Harness 代码基线，再继续分工推进。

## 2. 为什么现在需要做这件事

### 2.1 双入口会导致测评结论不能代表训练链路

当前 `run_task(...)` 和 `run_episode(real_episode)` 共享一部分底层组件，例如 `AgentLoop`、工具实现、workspace adapter、final patch 捕获、verifier 和 reward 相关逻辑。但是它们并不等价。

当前 `run_task(...)` 的主要行为是：

```text
load task
-> load run config
-> build scaffold
-> resolve allowed tools
-> build public environment context
-> ContextBuilder.build_initial_messages(...)
-> create model client
-> AgentLoop(...)
-> ToolExecutor(registry=allowed_tool_registry)
-> final patch / verifier / reward / export
```

当前 `run_episode(real_episode)` 的主要行为是：

```text
RepoHarnessEpisodeRequest.raw_prompt
-> LLMGatewayModelClientAdapter
-> AgentLoop(...)
-> ToolExecutor()
-> generation record collector
-> final patch / verifier / reward boundary
-> TrainingView / EpisodeResult / AgentLoopOutput
```

关键差异是：

```text
run_task(...) 会主动构造模型首轮上下文和工具集合。
run_episode(real_episode) 当前主要使用调用方传入的 raw_prompt。
```

因此，如果只用 `run_task(...)` 做测评，然后用 `run_episode(...)` 做训练，可能出现下面的问题：

```text
测评时模型看到 public_environment，但训练时 raw_prompt 没有。
测评时模型有 diagnostic_shell，但训练时实际工具集合没有。
测评时使用某个 scaffold，训练时 AgentLoop 默认回退到另一个 scaffold。
测评时 final patch hygiene 已修复，训练时 TrainingView 或 reward gate 没有同步同一事实。
```

这会让后续实验结论变得难以解释。模型在测评中表现出的能力，不一定是训练中能够学到和复现的能力。

当前关键差异可以概括为：

| 对比项 | `run_task(...)` 当前行为 | `run_episode(real_episode)` 当前行为 | 风险 |
|---|---|---|---|
| 入口文件 | `src/repo_harness/evaluation/runner.py` | `src/repo_harness/rl/runtime.py` | 两条入口分别演进。 |
| 首轮 prompt | 由 `ContextBuilder.build_initial_messages(...)` 构造 | 直接使用 `RepoHarnessEpisodeRequest.raw_prompt` | public environment、scaffold 指导和工具提示可能不一致。 |
| scaffold | 从 `run_config.runtime.scaffold_id` 构造 | 当前 real episode 默认没有显式传入同一 scaffold | 训练时可能回退到默认 scaffold。 |
| allowed tools | 由 `resolve_allowed_tools(...)` 和 `tool_registry_for_allowed_tools(...)` 生成 | 当前 real episode 使用默认 `ToolExecutor()` | 模型可见工具和实际工具面可能不同。 |
| public environment | `run_task(...)` 会构造并写入 `public_environment_context` | 只有调用方把同等内容写入 `raw_prompt` 时才会出现 | Stage 16C 的上下文改动可能只覆盖旧测评入口。 |
| feedback policy | 由 run config、task 和 scaffold 解析 | real episode 当前训练路径默认关闭公开测试反馈 | 测评和训练对 `run_tests` / public feedback 的语义可能不同。 |
| verifier plan | `run_task(...)` 写入 `resolved_verifier_plan` 并用于上下文和工具 | real episode 的工具上下文中 `resolved_verifier_plan` 当前可以为空 | 模型可见测试入口和最终 verifier 事实可能不一致。 |
| 训练事实 | 不是核心目标 | 生成 `GenerationRecord`、`TrainingView`、formal gate facts | 测评入口无法直接证明训练 batch 事实正确。 |
| 外部 API | `run_task(...)` 已成熟支持 DeepSeek / OpenAI provider | 可通过 `ModelClientLLMGateway` 适配，但 provider route 通常不能进入 formal RL | 外部 API 轨迹适合测评和 SFT，不等于在线 RL 样本。 |

因此，`run_episode(real_episode)` 可以成为未来 canonical Harness 入口，但当前实现还不能直接承担这个角色。进入迁移实现前，必须先把下面这些差异冻结成 Stage 16F 的显式工作项：

1. 当前 `run_episode(real_episode)` 仍主要消费外部传入的 `RepoHarnessEpisodeRequest.raw_prompt`，而不是像 `run_task(...)` 一样由共享 builder 统一构造首轮上下文。
2. 当前 real episode 路径中仍存在默认 `ToolExecutor()` 入口，尚未证明它总是等价于 `run_task(...)` 解析出的 `allowed_tool_registry`。
3. 当前 real episode 工具上下文中 `resolved_verifier_plan` 可以为空，不能默认认为它已经继承旧测评入口的公开测试、隐藏 verifier 和最终 verifier 语义。
4. 当前 real episode 路径中的 `test_feedback_policy` 可能是 `disabled`，这和 Stage 16C 之后的公开环境提示、公开测试反馈和 oracle hidden feedback 边界必须重新对齐。
5. 当前训练工作树里 Docker diagnostic shell 的执行语义仍需要同步检查。代码中 Docker persistent diagnostic session 仍存在 `sh -lc` 执行路径，Local diagnostic shell 仍通过 `shell=True` 使用系统默认 shell；测评工作树已经推进到更明确的 `bash -lc` 语义。这个差异会影响 `source`、`conda activate`、`set -o pipefail`、数组语法、错误传播和 shell 启动文件行为，必须作为 Stage 16F 的第一优先级同步项。

换句话说，Stage 16F 的目标不是立刻宣布“现在的 `run_episode` 已经等价于 `run_task`”，而是先把 `run_task(...)` 中成熟的任务解析、上下文构造、工具注册、verifier 计划和 shell 语义收敛到一个共享规格，再让 `run_episode(real_episode)` 消费这个共享规格。

### 2.2 测评工作树发现的问题已经是训练基础设施问题

另一个工作树的 SWE-Bench Verified 分数差距排查已经发现了多类真实 Harness 问题，包括：

```text
受限 bash 不等价于真实 SWE agent 需要的完整诊断 shell。
diagnostic_shell 需要同一题内持久会话。
diagnostic_shell 不能挂载 RepoHarness run directory。
模型不能访问 Git 历史、gold patch、test patch、官方失败到通过测试集合标记、官方通过到通过测试集合标记或 hidden verifier。
public_environment 需要明确仓库根目录、测试入口、testbed 环境和依赖策略。
Docker persistent diagnostic shell 需要使用 bash -lc，而不是 sh -lc。
依赖环境需要只读，模型不能修改 /opt/miniconda3、site-packages 或共享虚拟环境。
dependency prepare 需要在干净源码副本中执行，不能污染 agent workspace。
final.patch 和 official prediction 不能包含 patch.txt、*.orig、*.rej、*.bak、.repo_harness_tmp、tmp 诊断脚本或测试文件改动。
official prediction 还需要过滤 `.modified`、`.new`、旁路副本文件和异常 quoted path。
official harness 验证前需要 gold patch healthcheck 和 no-op healthcheck。
官方 instance image、本地重建镜像、远端预构建镜像需要区分记录。
DeepSeek、OpenAI 或其他 provider 的异常响应、超时、空输出和基础设施错误需要单独记账，不能直接算成模型语义失败。
```

这些问题不是单纯的“评测优化”。它们会决定训练数据是否可信。如果训练工作树没有及时同步这些修复，强化学习可能会学习到错误的工具协议、污染的 patch、错误的 verifier 信号或不可复现的测试反馈。

### 2.3 Stage 17 数据准备前必须明确事实来源

Stage 17 计划把 R2E-Gym、SWE-Gym 和内部微型任务池转成可训练、可验证、无 oracle 泄漏的任务 registry。在进入 Stage 17 前必须明确：

```text
训练数据到底由哪个 Harness 入口生成？
SFT target、preference pair、reward evidence、official prediction、final.patch 以哪个入口的产物为准？
测评结论和训练 rollout 是否来自同一个工具面和上下文分布？
```

如果这个问题不解决，Stage 17 会在两个事实来源之间摇摆：

```text
旧 run_task run directory
run_episode EpisodeResult / TrainingView
```

这会增加后续数据冻结、奖励设计、训练诊断和官方评测归因的复杂度。

## 3. 总体目标

### 3.1 Canonical Harness 入口

统一后的目标链路是：

```text
task
-> EpisodeExecutionSpec
-> RepoHarnessRuntime.run_episode(real_episode)
-> RepoHarnessEpisodeResult
```

测评消费：

```text
RepoHarnessEpisodeResult
-> final.patch
-> verifier summary
-> official prediction
-> official harness result
-> evaluation report
```

训练消费：

```text
RepoHarnessEpisodeResult
-> TrainingView
-> GenerationRecord
-> AgentLoopOutput
-> DataProto
-> policy loss / SFT / preference / reward training
```

也就是说，测评和训练共享 episode 产生过程，只是后续消费不同。

### 3.2 共同 Harness 基线

训练工作树和测评工作树的理想关系不是两个长期分叉的实现，而是：

```text
一个 canonical Harness 基线
两个不同用途的工作树
```

建议工作流：

```text
canonical Harness baseline
  -> evaluation worktree
       负责 SWE-Bench、DeepSeek V4、official harness、工具能力和分数差距诊断
  -> training worktree
       负责 run_episode、verl、SFT、RL、fully async 训练链路和数据准备
```

测评工作树可以更实验化，但一旦发现确定的 Harness 修复，就应该整理成小提交同步回 canonical 基线。训练工作树在生成训练数据或启动远端训练前，必须同步这些已确认修复。

这个共同基线不能只停留在口头约定。Stage 16F.0 必须创建或指定一个可审计的 canonical integration branch 或 canonical integration commit，并让训练工作树和测评工作树都记录自己和该基线的关系。最少需要记录：

```text
canonical_branch_or_commit
sync_base_commit
training_worktree_head_before_sync
evaluation_worktree_head_before_sync
integration_commit_after_sync
training_worktree_head_after_sync
evaluation_worktree_head_after_sync
training_worktree_matches_canonical_after_sync
evaluation_worktree_matches_canonical_after_sync
```

如果两个工作树在 Stage 16F.0 结束时没有指向同一个 canonical commit，也必须写清楚原因、允许偏离的文件范围、偏离 sha256 和下一次同步 gate。否则后续“同步完成”就没有可复查的 Git 语义。

## 4. 非目标

本阶段不做以下事情：

1. 不把另一个工作树的所有文件无差别合并进来。
2. 不提交另一个工作树的本机绝对路径、历史运行目录、HTML 报告或临时调试产物。
3. 不放松 Stage 16A 到 Stage 16E 已建立的防泄漏、patch hygiene、visibility、formal online RL gate。
4. 不要求一次性迁移所有旧命令。旧 `run_task(...)` 可以先保留为兼容包装层。
5. 不把外部 API provider 轨迹伪装成正式 online RL 样本。外部 API 缺少可靠 token id 和 log probability 时，只能作为测评、SFT、preference 或诊断轨迹来源。
6. 不把 official SWE-Bench harness 结果和 RepoHarness 内部 verifier 结果混为一谈。官方 verifier 仍然是 SWE-Bench-like 任务最终 resolved 口径。

## 5. 建议新增阶段：Stage 16F

建议在 Stage 17 之前新增：

```text
Stage 16F：跨工作树 Harness 同步与 run_episode canonical 入口迁移
```

这个阶段可以拆成 7 个子阶段。

### 5.1 Stage 16F.0：同步前冻结和差异盘点

目标：明确两个工作树当前状态，避免把无关改动、临时产物或本机路径混入同步。

Stage 16F.0 是强制前置 gate。没有完成这个 inventory 之前，不能开始 cherry-pick、手工移植、`EpisodeExecutionSpecBuilder` 实现或 `run-episode-task` CLI 实现。原因是两个工作树已经同时修改了工具、诊断 shell、patch hygiene、official verifier 和 provider 失败记账；如果不先冻结 commit 和 dirty 文件，后续 parity audit 无法判断差异来自同步前状态、同步过程，还是新实现。

需要完成：

1. 确认训练工作树当前 Stage 16E 已提交，工作区中未提交改动已分类。
2. 确认测评工作树中待同步修复的提交列表、dirty 文件列表和运行产物列表。
3. 生成跨工作树同步 inventory，至少包含：

   ```text
   source_worktree_label
   source_commit
   source_dirty_files
   source_doc_sha256
   target_worktree_commit_before
   required_cherrypicks
   manual_port_required_items
   skipped_items_with_reason
   ```

4. 公开 inventory 不能记录本机绝对路径。真实路径只能出现在运行时私有证据目录或本地不提交的私有记录中。
5. 明确哪些修复是必须同步，哪些只是测评实验产物。
6. 如果测评工作树存在 dirty 文件，必须为每个 dirty 文件记录：

   ```text
   relative_path
   status
   current_sha256
   base_blob_sha256
   diff_sha256
   diff_summary
   participates_in_sync
   reason_if_not_synced
   ```

   没有进入 inventory 的 dirty 文件内容不能作为 Stage 16F.1 的同步来源。

7. 生成模块级差异矩阵 `module_diff_matrix`。它不能只记录“需要同步 diagnostic shell”这种主题级结论，还必须落到具体模块或文件组。建议至少覆盖：

   ```text
   command_policy
   diagnostic_session
   workspace_adapter
   docker_adapter
   public_environment
   patch_hygiene
   official_input_builder
   healthcheck_builder
   healthcheck_inspector
   provider_failure_accounting
   evaluation_runner
   rl_runtime
   tool_registry
   context_builder
   ```

   每一项至少记录：

   ```text
   module_name
   source_files
   target_files
   source_file_sha256s
   target_file_sha256s
   source_module_digest
   target_module_digest
   module_digest_algorithm=stable_json_sha256(sorted file records)
   source_commit
   target_commit
   decision=sync/defer/ignore/manual-port
   reason
   required_tests
   risk_if_deferred
   ```

   没有进入 `module_diff_matrix` 的模块差异，不能在 Stage 16F.1 中被静默同步。

必须同步的候选类别：

```text
diagnostic_shell 持久会话和 bash -lc 语义
public_environment 公开测试入口和 testbed 提示
Docker dependency prepare 隔离
只读依赖环境和 dependency mutation guard
run directory 不挂载到模型可见 shell
Git 历史和 evaluator-only 信息防泄漏
patch hygiene 和 official prediction hygiene
provider failure / timeout / empty response 结构化记账
provider-only rerun 结果
provider failure denominator 统计
official_prediction_eligible=false 的传播规则
gold patch / no-op / official image healthcheck 经验
score-gap manifest 和代表性样本构建中可复用的安全规则
```

其中 `diagnostic_shell` 执行 shell 语义必须作为 P1 同步项单独记录。换句话说，diagnostic_shell 执行 shell 语义必须作为 P1 同步项，而不是普通兼容性细节。Stage 16F.0 inventory 至少要写清楚：

```text
source_diagnostic_shell_exec_semantics
target_diagnostic_shell_exec_semantics
docker_backend_shell
local_backend_shell
uses_bash_lc
uses_sh_lc
uses_shell_true
conda_activate_supported
pipefail_supported
source_command_policy_sha256
target_command_policy_sha256
```

如果目标工作树仍使用 `sh -lc` 或 `shell=True`，Stage 16F.1 必须先处理该差异，不能等到 Stage 16F.4 parity audit 后再发现真实任务行为不一致。

### 5.2 Stage 16F.1：受控同步关键 Harness 修复

目标：把测评工作树中已经验证可靠的 Harness 修复同步到训练工作树，同时保留当前训练链路的严格边界。

同步原则：

1. 优先 cherry-pick 小提交。
2. 如果提交和当前工作树冲突，手工移植逻辑，不强行覆盖当前 Stage 16A 到 Stage 16E 的实现。
3. 每个同步项都必须有对应测试。
4. 每个同步项都必须标记来源证据。
5. 不能同步历史运行目录、HTML 报告、本地 secret、云服务配置、临时 patch。

建议同步后至少跑：

```text
Stage 16A execute_bash tests
Stage 16B diagnostic_shell tests
Stage 16C public_environment tests
Stage 16D / 16D.1 healthcheck tests
Stage 16E patch_hygiene tests
selected run_episode / fully async regression
compileall
git diff --check
core verl import scan
```

P1 同步项应至少包含 `diagnostic_shell` 执行 shell 语义对齐：

```text
Docker diagnostic backend：显式使用 bash -lc 或等价、可审计的 bash 入口。
Local diagnostic backend：不能依赖不透明 shell=True 默认 shell；如果保留 local fallback，必须记录实际 argv、shell path、shell version 和 profile loading policy。
测试覆盖：source script.sh、source activate、conda activate、set -o pipefail、管道失败传播、bash-only 语法、sh-only 失败样例。
审计事实：每条 diagnostic_shell command 必须记录 execution_shell、execution_argv_digest、shell_semantics_version。
```

如果短期不实现 Local backend 的完整对齐，必须把 Local backend 标成 diagnostic-only，并且不能把它产生的样本计入正式训练候选。

### 5.3 Stage 16F.2：定义共享 EpisodeExecutionSpec

目标：把 `run_task(...)` 中已有的上下文、工具、scaffold、公开环境和 verifier 计划构造逻辑抽成可复用的 episode 规格构建器。

这一阶段不应该一开始大规模重构 `run_task(...)`。更稳的第一版是新增最小可用的 `EpisodeExecutionSpecBuilder`，让它先复用旧入口已经稳定的构造逻辑，并让 `run_episode(real_episode)` 能消费同一个规格。只有 parity audit 证明新规格和旧入口一致后，才逐步让 `run_task(...)` 内部转调新规格。

建议新增或等价实现：

```text
EpisodeExecutionSpec
EpisodeExecutionSpecBuilder
```

模块归属必须保持中立，不能把共享 builder 放进只属于测评入口或只属于训练入口的模块。建议放在类似下面的中立位置：

```text
src/repo_harness/execution/
src/repo_harness/episode_spec.py
```

导入边界要求：

```text
EpisodeExecutionSpec / EpisodeExecutionSpecBuilder 不能 import repo_harness_verl。
EpisodeExecutionSpec / EpisodeExecutionSpecBuilder 不能 eager import torch、ray、verl、tensordict。
repo_harness.rl.runtime 可以消费 EpisodeExecutionSpec。
evaluation.runner 可以消费 EpisodeExecutionSpec。
repo_harness.rl.runtime 不应该反向依赖 evaluation.runner。
evaluation.runner 不应该通过训练专用 adapter 才能构造 prompt 或工具集合。
```

如果实现时确实需要共享旧 `evaluation.runner` 中的逻辑，必须先把那部分逻辑抽到中立模块，再由 `evaluation.runner` 和 `rl.runtime` 共同调用，避免形成循环依赖或让普通导入加载重依赖。

它负责统一生成：

```text
task facts
run config facts
workspace facts
scaffold_id
allowed_tools
allowed_tool_registry
tool schema snapshot
public_environment_context
initial_messages / raw_prompt
feedback policy
test command visibility
resolved verifier plan
permission policy
budget policy
patch hygiene policy
dependency environment facts
```

构建结果必须同时供下面两个入口使用：

```text
旧 run_task compatibility path
run_episode(real_episode) canonical path
```

关键要求：

1. `raw_prompt` 不再由外部零散拼接，而是优先来自同一个 `ContextBuilder` 或共享 builder。
2. `run_episode(real_episode)` 必须能显式接收 scaffold 和 allowed tool registry。
3. `run_episode(real_episode)` 的模型可见工具 schema 必须和实际可执行工具 registry 一致。
4. `public_environment_context_digest` 必须进入 episode evidence。
5. 测评模式可以不产生正式可训练 batch，但仍应记录 `TrainingView` 是否可用、为何不可用、是否缺少 log probability。

### 5.4 Stage 16F.3：新增 run_episode 测评 CLI

目标：提供一个测评入口，但内部走 canonical `run_episode(real_episode)`。

建议新增实验性命令：

```text
repo-harness run-episode-task
repo-harness run-episode-batch
```

第一版能力：

```text
读取现有 task definition 和 run config
构造 EpisodeExecutionSpec
调用 RepoHarnessRuntime.run_episode(real_episode)
写出兼容旧评测工具的 run directory projection
支持外部 API provider 诊断模式
支持 Docker diagnostic session
支持 official prediction builder
支持 final patch hygiene report
```

run directory projection 至少需要包含：

```text
transcript / prepared messages
events
artifacts manifest
cleaned final.patch / final.diff
final_patch_hygiene_report
verifier summary
reward summary
metrics / timing summary
resource summary
public_environment_context
public_environment_prompt_block
tool_schema_snapshot
provider failure facts
TrainingView projection 或明确的 not_available reason
generation_records projection 或明确的 not_available reason
```

这个 projection 必须能机器校验它确实来自同一次 canonical `run_episode`，不能只是后处理脚本拼出的兼容目录。建议至少写入下面这些绑定字段：

```text
episode_execution_spec_schema_version
episode_execution_spec_sha256
task_definition_sha256
run_config_sha256
tool_registry_digest
tool_schema_snapshot_digest
public_environment_context_digest
compat_projection_schema_version
projection_source_episode_id
projection_source_run_id
projection_source_training_view_digest
projection_source_generation_records_digest
projection_created_from_run_episode=true
```

旧评测工具读取 projection 时，应优先展示这些绑定字段。如果字段缺失或 digest 与源 episode 不一致，该 projection 只能用于诊断，不能作为 Stage 17 数据冻结、SFT target、preference pair、reward evidence 或 official prediction 的可信来源。

注意事项：

1. 外部 API provider，例如 DeepSeek V4 或 OpenAI，可以用于测评和轨迹采集。
2. 外部 API provider 如果没有可靠 token id 和 log probability，不能进入 formal online RL policy loss。
3. 对 provider route 产生的 episode，应明确记录：

   ```text
   invalid_for_online_rl=true
   diagnostic_or_sft_candidate=true
   missing_response_logprobs 或 provider_route_not_verl
   ```

4. 旧 `run_task(...)` 暂时保留，但开始降级为兼容层。

### 5.5 Stage 16F.4：run_task 与 run_episode 一致性审计

目标：证明新入口没有改变模型可见上下文和工具面，或者明确记录有意差异。

建议先选 3 到 5 个小任务，分别用旧 `run_task(...)` 和新 `run-episode-task` 运行 fake、replay 或低成本 provider 模式。比较：

```text
initial_messages_digest
public_environment_context_digest
allowed_tool_names
allowed_tool_schema_hash
scaffold_id
test_feedback_policy
resolved_verifier_plan_digest
permission_policy_digest
final_patch_hygiene_policy_digest
final.patch sha256
verifier summary
reward summary
invalid_for_training / invalid_for_online_rl
```

如果差异是设计上的，必须写入：

```text
run_task_run_episode_parity_report.json
```

如果差异不是设计上的，必须修复后才能进入 Stage 16.5 或 Stage 17。

### 5.6 Stage 16F.5：旧 run_task 降级策略

目标：让旧入口继续服务历史兼容，但不能继续成为 Stage 17 之后训练数据的独立事实来源。

建议策略：

```text
第一步：保留 run_task(...)，但新增 warning 和 evidence 字段，说明它是 legacy compatibility path。
第二步：新增 run-episode-task，作为所有新测评实验的默认入口。
第三步：让 run_task(...) 在内部构造 EpisodeExecutionSpec，并尽可能转调 run_episode(real_episode)。
第四步：当 old inspector / export / report 都能读取 run_episode projection 后，把 run_task(...) 标记为 deprecated。
```

旧入口仍可以用于：

```text
历史 evidence 复验
旧 run directory inspector
和新入口做 parity 对照
短期回滚
```

旧入口不能用于：

```text
Stage 17 正式训练数据主路径
新的 SFT target 事实来源
新的 preference pair 事实来源
新的 RL rollout 事实来源
```

### 5.7 Stage 16F.6：小规模真实模型 smoke

目标：用新的 `run_episode` 测评入口替代旧 `run_task` 进行小规模真实模型诊断。

建议范围：

```text
5 到 10 个代表性任务
外部 API 模型，例如 DeepSeek V4
Docker diagnostic backend
official harness 外部验证
gold patch / no-op healthcheck
patch hygiene / official prediction hygiene
```

这一小规模 smoke 需要区分两种目的：

```text
DeepSeek / OpenAI provider smoke：
  证明新的 run_episode 测评入口、外部 API 轨迹、SFT / preference 候选轨迹和 official harness 对接可用。
  这类样本通常不能证明 formal online RL policy loss 可用。

route=verl smoke：
  证明训练入口、generation records、response ids、response logprobs、TrainingView 和 policy-loss 前置事实仍然可用。
  这类样本可以复用 Stage 14 / Stage 15 的小规模训练链路回归。
```

通过后，再进入 Stage 16.5 的 20 到 30 题代表性诊断扩展。

## 6. 完成后的两个工作树工作流

### 6.1 测评工作树

测评工作树继续负责发现 Harness 能力问题和分数差距来源，但它应该基于 canonical Harness 基线工作。

主要任务：

```text
运行 SWE-Bench / DeepSeek V4 / official harness 诊断。
构造代表性样本，例如 resolved、unresolved、no-op 风险、official flaky、不同仓库类型。
发现工具、prompt、diagnostic shell、patch hygiene、official verifier 的系统性问题。
生成小而清晰的 Harness 修复提交。
提供官方验证 evidence、gold/no-op healthcheck、unresolved 审计报告。
```

要求：

1. 测评工作树可以保留实验性脚本和临时运行产物，但不能让它们成为长期事实来源。
2. 已确认的 Harness 修复必须回到 canonical 基线。
3. 测评工作树后续应逐步改用 `run-episode-task`，避免继续扩大旧 `run_task(...)` 分叉。
4. 测评工作树输出给训练工作树的应该是：

   ```text
   小提交
   结构化报告
   样本 manifest
   official harness evidence
   风险样本清单
   ```

   而不是一整个带大量运行产物的工作树。

### 6.2 训练工作树

训练工作树继续负责 verl、fully async、SFT、RL、reward、数据准备和训练实验。

主要任务：

```text
维护 run_episode canonical training path。
维护 TrainingView、GenerationRecord、AgentLoopOutput、DataProto、formal online RL gate。
把 canonical Harness 修复带入训练数据生成。
在 Stage 17 之后构建 R2E-Gym、SWE-Gym 和内部微型任务池 registry。
运行 SFT、preference、reward、RL 训练。
```

要求：

1. 进入数据冻结、SFT 轨迹采集、RL rollout、远端训练前，必须同步 canonical Harness 基线。
2. 训练工作树不能用落后于测评工作树的工具和 patch hygiene 规则生成训练数据。
3. 训练工作树可以保留训练专用字段，但不能让训练入口看到和测评入口不同的任务上下文和工具语义，除非有明确、可审计的配置差异。

### 6.3 同步频率

同步不建议按固定日期，而应按阶段门槛：

```text
每完成一批代表性测评后同步一次。
每发现 P1 / P2 Harness 问题并修复后同步一次。
进入 Stage 17 数据冻结前必须同步。
进入 SFT 数据生成前必须同步。
进入 RL rollout 前必须同步。
进入远端正式训练前必须同步。
```

以下修复应该立即同步：

```text
隐藏信息泄漏
final.patch 污染
工具可见内容和实际可执行工具不一致
official prediction builder 错误
official verifier / gold / no-op healthcheck 错误
workspace / dependency / diagnostic shell 隔离问题
run_episode 和 run_task 行为不一致
```

## 7. 验收标准

### 7.1 文档和 inventory

1. 跨工作树同步 inventory 不包含本机绝对路径。
2. 每个同步项都有来源、风险、测试、是否纳入 canonical 基线的说明。
3. 所有跳过项都有明确原因。

### 7.2 代码和入口

1. `run_episode(real_episode)` 可以由 CLI 测评入口直接调用。
2. 新 CLI 能输出旧测评工具可消费的 run directory projection。
3. `run_task(...)` 可以继续存在，但不能成为新的训练数据事实来源。
4. `run_episode` 测评入口和训练入口使用同一个 `EpisodeExecutionSpec` 或等价共享构造逻辑。

### 7.3 上下文和工具一致性

1. 同一任务、同一 scaffold、同一配置下，`run_task` 和 `run_episode` 的首轮 prompt digest 一致，或者差异被结构化解释。
2. `allowed_tool_names` 一致。
3. 模型可见 tool schema 和实际 `ToolExecutor` registry 一致。
4. `public_environment_context_digest` 一致。
5. `diagnostic_shell`、`execute_bash`、`run_tests`、`git_diff` 等工具的可见说明和实际执行策略一致。

### 7.4 测评和训练事实一致性

1. final patch hygiene report 在测评和训练路径中使用同一策略。
2. verifier summary、reward summary、resource summary、timing summary 在两个路径中不产生冲突解释。
3. provider route 样本不会进入 formal online RL policy loss。
4. `route=verl` 的正式样本仍然必须满足 generation record、response span、token id、logprob、visibility gate 和 formal validator。

### 7.5 真实 smoke

1. 至少 5 到 10 个真实模型 episode 通过 `run_episode` 测评入口完成。
2. 至少一个样本使用 `diagnostic_shell`。
3. 至少一个样本使用 official harness 外部验证。
4. gold/no-op healthcheck 结果被记录。
5. public evidence 没有本机路径、run directory、运行时私有证据目录、hidden verifier、gold patch、test patch 泄漏。

## 8. 主要风险和缓解

### 8.1 迁移影响已经稳定的 fully async 链路

风险：大规模改动 `run_episode` 可能破坏 Stage 15.2 和 Stage 14 的 fully async 训练 smoke。

缓解：

```text
先新增 run_episode 测评 CLI，不直接删除旧 run_task。
保留 Stage 13 到 Stage 15 的关键回归。
每次改动都检查 src/repo_harness/rl 不引入 verl eager import。
provider route 诊断样本和 route=verl 正式样本继续分开。
```

### 8.2 把测评实验产物误同步到训练主线

风险：另一个工作树有大量运行目录、HTML 报告、本机路径和实验中间产物，不能直接合并。

缓解：

```text
只同步代码、测试、计划文档和公开安全 manifest。
运行产物只通过 sha256、opaque ref 和结构化摘要引用。
运行时私有原始日志不进入公开提交。
```

### 8.3 外部 API 测评样本被误当成 RL 样本

风险：DeepSeek 或 OpenAI provider 轨迹可以用于测评和 SFT，但通常缺少正式 RL 所需 log probability。

缓解：

```text
provider route 默认 invalid_for_online_rl=true。
只有 route=verl 且 generation records、response_logprobs、response spans 全部通过 formal gate，才进入 policy loss。
```

### 8.4 旧 `run_task` 迁移过快导致当前测评中断

风险：直接删除或大改 `run_task` 会影响正在进行的 SWE-Bench 诊断。

缓解：

```text
第一版保留 run_task 兼容层。
新增 run-episode-task 后先并行验证。
等 parity smoke 通过后，再逐步让 run_task 内部调用 run_episode。
```

## 9. 和后续阶段的关系

建议阶段顺序调整为：

```text
Stage 16E：patch hygiene 完成并提交
Stage 16F：跨工作树同步与 run_episode canonical 入口迁移
Stage 16.5：20 到 30 题代表性 Harness 诊断，使用新的 run_episode 测评入口
Stage 17：R2E-Gym、SWE-Gym 和内部微型任务池 registry
Stage 18 以后：summary、reward、warm start、SFT、DAPO / GRPO 等训练实验
```

这意味着 Stage 19.5 中原本计划的“`run_episode` 产物、旧 CLI 和 offline export 桥接”需要前移一部分。原因是现在已经确认双入口会影响 Stage 16.5 和 Stage 17 的可信度，不能等到 Stage 19.5 再处理。

对应地，Stage 16.5 的口径也应调整：

```text
Stage 16.5 不再把旧 run_task(...) 作为主诊断入口。
Stage 16.5 应优先使用 run-episode-task。
旧 run_task(...) 只作为对照、历史复验或回滚路径。
```

Stage 19.5 仍然可以保留更完整的 offline export、旧 inspector 和历史 run directory 兼容工作，但最小的 run_episode 测评 CLI 和 run directory projection 必须前移到 Stage 16F。

## 10. 建议给两个工作树执行智能体的分工

### 10.1 测评工作树执行智能体

优先任务：

```text
整理当前 SWE-Bench score-gap 修复提交清单。
区分必须同步的 Harness 修复和纯实验脚本。
提供每个修复的测试命令和 evidence 摘要。
协助挑选 run_episode 测评入口 parity smoke 的任务。
后续继续跑代表性诊断，但逐步切换到 run_episode CLI。
```

### 10.2 训练工作树执行智能体

优先任务：

```text
实现 EpisodeExecutionSpec 或等价共享 builder。
新增 run-episode-task CLI。
把 run_episode(real_episode) 接入相同 scaffold、allowed tool registry、public_environment 和 patch hygiene。
实现 run_task / run_episode parity audit。
同步测评工作树中已经确认的 Harness 修复。
```

### 10.3 主审查口径

两个执行智能体都应接受同一个审查口径：

```text
测评和训练可以消费不同结果字段；
但不能让模型看到不同的任务、工具、约束和测试环境。
```

如果因为训练或测评需要产生差异，必须是显式配置差异，并进入结构化报告。

## 11. 建议下一步

1. 训练工作树先提交 Stage 16E，或者明确把 Stage 16E 未提交差异从 Stage 16F 基线中排除。
2. 两个工作树共同审查本文档。
3. 新增 Stage 16F 执行计划。
4. 执行 Stage 16F.0 inventory。
5. 按 inventory 同步关键 Harness 修复。
6. 实现 `run_episode` 测评 CLI 和 parity audit。
7. 用新入口重跑 5 到 10 个代表性真实模型 episode。
8. 再进入 Stage 16.5 和 Stage 17。
