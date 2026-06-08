# Stage 16G.3 执行计划：公开命令、项目测试路由和 scratch Python

## 1. 阶段定位

Stage 16G.3 是 RepoHarness 从“结构化文件修改能力已经可用”走向“真实软件工程动态诊断能力可训练”的关键阶段。Stage 16G.2 已经把 `write_file`、`apply_patch`、删除、移动、目录创建、`final.patch`、patch hygiene 和 TrainingView 投影打通；但真实软件工程任务不能只靠静态阅读和补丁生成完成。模型还需要稳定地运行公开测试、公开项目命令和临时复现脚本，观察 stdout、stderr、exit code，再据此迭代修改。

本阶段的目标不是开放完整宿主 shell，也不是把 `diagnostic_shell` 放入主训练默认工具面。Stage 16G.3 要做的是：

```text
在 swe_public_core 中新增可审计、可拒绝、可投影、可训练的公开动态诊断工具面，
覆盖 Claude Code / Codex / mini-SWE-agent 都证明重要的命令执行能力，
同时继续保持 hidden verifier、参考补丁、测试补丁、runtime-private、Git history 和宿主路径隔离。
```

Stage 16G.3 完成后，RepoHarness 的主 SWE 强化学习默认工具面应该能够表达下面这条闭环：

```text
读代码 / 搜索
-> 运行公开命令或公开定向测试
-> 写 scratch Python 复现最小问题
-> 修改代码
-> 再运行公开测试或公开 smoke
-> 查看 diff
-> 最终回答
```

## 2. 非目标

Stage 16G.3 明确不做下面这些事情：

1. 不开放无约束 Bash，不支持任意管道、重定向、后台任务、环境变量展开、命令拼接、进程替换或下载命令。
2. 不把 `diagnostic_shell` 或 persistent shell 放入 `swe_public_core`；持久诊断会话属于 Stage 16G.4B 的 `swe_public_extended`。
3. 不实现依赖安装、共享依赖缓存写入、private overlay 或复杂 dependency setup；这些属于 Stage 16G.4A。
4. 不把真人 approval 引入强化学习 rollout。Codex / Claude Code 的 approval 思想在本阶段转成 deterministic allow / deny / recover policy。
5. 不把 public command 结果直接放入 policy loss。Stage 16G.3 只负责工具事件、TrainingView mask、artifact visibility 和 sample eligibility facts；正式训练放行仍由 Stage 16G.5 / 16G.6 门禁决定。
6. 不把旧 `run_task(...)` 作为主验收入口；所有新增能力必须通过 `run_episode(real_episode)` / `run-episode-task` 可见。
7. 不做完整 process reward、LLM judge、quarantine 权重或 reward builder 数值设计；Stage 16G.3 只产出后续 reward 可以使用的公开安全事实。

## 3. 上游依据

Stage 16G.3 必须继承下面这些已经提交的基线和 evidence：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_per_capability_baseline_comparison.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_stage16g_implementation_requirements.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_tool_registry_contract.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_profile_taxonomy.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_training_eligibility_gate_spec.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_acceptance_summary.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/stage16g2c_acceptance_summary.json
```

Stage 16G.3 开工前必须重新运行并确认 Stage 16G.1、Stage 16G.2A、Stage 16G.2B、Stage 16G.2C inspector 仍然通过。若前置 evidence 过期，先修前置 evidence，不要在不可靠的工具 registry 和文件修改链路上继续扩展命令执行能力。

建议前置命令：

```bash
PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main inspect-stage16g1-tool-profile docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_acceptance_summary.json --assert-complete
PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main inspect-stage16g2a-tool-surface docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/stage16g2a_acceptance_summary.json --assert-complete
PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main inspect-stage16g2b-file-mutation docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/stage16g2b_acceptance_summary.json --assert-complete
PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main inspect-stage16g2c-projection-linkage docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/stage16g2c_acceptance_summary.json --assert-complete
```

## 4. 参考 harness 结论

### 4.1 Claude Code 参考

Claude Code 的参考源码显示，真实产品态软件工程代理把 `Read`、`Grep`、`Glob`、`Edit`、`Write`、`Bash`、`TodoWrite`、hooks、权限和工具生命周期放在同一个 agent loop 中。`Bash` 是测试、构建、项目命令和复杂诊断的一等能力，但它经过权限、沙箱、hook、输出处理和工具结果配对。

对 RepoHarness 的启发是：不要让模型只能静态猜补丁；但也不要把所有读、写、改、测都压进一个不透明 shell。结构化文件工具继续承担文件修改，Stage 16G.3 补齐公开命令和测试诊断。

### 4.2 Codex 参考

Codex 参考源码和分析文档说明，Codex 的真实软件工程能力更偏 `exec_command` / `write_stdin` / `apply_patch` / permission profile / approval / sandbox / event stream。它允许模型运行项目命令、测试和诊断脚本，但将命令执行放入 workdir、timeout、输出截断、sandbox permission、approval、guardian、hook 和 rollout trace 中。

对 RepoHarness 的启发是：

```text
命令执行能力应该是正式工具面的一部分；
技术 sandbox、权限策略、approval/reviewer 思想和事件审计必须分层；
模型可见结果、客户端事件、raw artifact 和训练投影不能混成一个字符串。
```

RepoHarness 不需要复制 Codex 的 PTY、ongoing session 或 `write_stdin`。Stage 16G.3 第一版应该先实现 stateless public command runner，把单次公开命令执行做稳定。持久进程和 stdin 续写留给 Stage 16G.4B 或更后续阶段。

还需要明确区分 Codex 的模型工具和客户端控制面。Codex app-server 中的 `command/exec`、`process/spawn`、`fs/readFile`、`fs/writeFile` 等 API 主要服务客户端或桌面端控制流程，不等同于普通模型可见动作。RepoHarness Stage 16G.3 只设计模型可见、可训练、可审计的工具动作空间，不能把客户端 API 级别的宿主文件系统能力映射成模型默认权限。

### 4.3 mini-SWE-agent 参考

本地没有 mini-SWE-agent 官方源码，但评测工作树已有真实配置和运行日志，Stage 16G.0 follow-up 已经把它作为 tier-2 evidence 纳入 baseline。mini-SWE-agent 的下限能力是稳定 shell 闭环：命令输入、stdout、stderr、exit code 反馈、公开测试和复现脚本。

对 RepoHarness 的启发不是“照抄 Bash-first”，而是必须覆盖同等动态诊断能力：

```text
能运行公开命令；
能运行定向测试；
能写和运行 scratch reproduction；
能拿到 stdout / stderr / exit code；
能在失败后继续迭代。
```

## 5. 必须覆盖的 capability

Stage 16G.3 直接负责下面这些 Stage 16G.0 blocking capability：

| capability_id | 当前状态 | Stage 16G.3 目标 |
| --- | --- | --- |
| `bash_or_public_command_execution` | `execute_bash` 窄但非空，不在 `swe_public_core` 默认目标内 | 新增正式 `run_public_command` 或等价公开命令工具，覆盖安全公开诊断和项目命令 |
| `parameterized_public_test_command` | `run_tests` 无参数，`execute_bash` 只支持部分 pytest | 新增 `run_project_test`，支持公开定向测试和任务声明的 public test route |
| `scratch_python_or_reproduction_script` | 只有受限 inline Python 或 diagnostic shell 特例 | 新增 `scratch_python`，在临时公开诊断空间运行，不污染 final patch |
| `project_command_routing` | 缺少统一 project command router | 建立基于任务 public environment / command profile 的命令路由 |
| `tool_result_truncation_raw_artifact_privacy` | 旧 shell 工具有部分 redacted/truncated 语义 | 新命令工具必须复用并加严 stdout/stderr 摘要、raw artifact 私有化和 public projection |
| `permission_approval_denial_recovery` | 有 reason_code / recovery_hint，但尚未覆盖新命令面 | 所有拒绝必须有结构化恢复路径，不诱导模型少用工具 |

Stage 16G.3 必须保持下面能力不退化：

| capability_id | Stage 16G.3 约束 |
| --- | --- |
| `sandbox_workspace_and_runtime_private_boundary` | 新命令工具不能读写 hidden verifier、参考补丁、测试补丁、runtime-private、`.git` 作弊路径、宿主绝对路径或共享依赖写入区 |
| `training_eligibility_and_export_projection` | 新工具事件必须进入 TrainingView、projection 和 eligibility facts，但不得绕过 Stage 16G.5 / 16G.6 放行门禁 |

## 6. 子阶段拆分

Stage 16G.3 必须拆成四个子阶段，顺序不能反过来：

```text
16G.3A  shared public command execution substrate
16G.3B  run_public_command
16G.3C  run_project_test
16G.3D  scratch_python 和 mini-SWE-agent 风格动态诊断闭环 probe
```

### 6.1 为什么必须先做 16G.3A

`run_public_command`、`run_project_test` 和 `scratch_python` 都需要相同的底层能力：

```text
cwd 解析
workspace-only 路径边界
timeout
stdout / stderr / exit code
输出截断
raw artifact 私有化
public-safe projection
拒绝 reason_code
safe_alternative_tool
safe_rewrite_example
TrainingView mask
run_episode 投影
```

如果先分别实现三个工具，很容易出现三套不一致的路径策略、输出截断、artifact visibility、拒绝语义和训练资格判断。Stage 16G.3A 必须先提供共享底座和机器验收器，后面三个工具只是在这个底座上选择不同 command family 和 schema。

## 7. Stage 16G.3A：共享公开命令执行底座

### 7.1 目标

Stage 16G.3A 建立一个非模型专属的底层服务，例如：

```text
src/repo_harness/tools/public_command.py
```

具体文件名可以调整，但必须有一个共享模块负责所有公开命令工具的安全执行和审计。这个模块应成为 `run_public_command`、`run_project_test`、`scratch_python` 的唯一执行底座。

### 7.2 设计要求

共享底座必须满足：

1. 默认 stateless，一次工具调用只运行一个命令或一个脚本，不保留 shell session。
2. 默认不使用 shell；如果底层 adapter 暂时只能接受字符串，也必须由 harness 先解析成安全 argv，再用可审计方式组装，禁止任意 shell 语法。
3. 所有 `run_public_command`、`run_project_test` 和 `scratch_python` 都必须使用已验证的 workspace-only isolated backend、public projection、临时复制工作区或 Docker sandbox。普通未隔离 `local_process`、可见 run-directory mount 或无法证明隔离的 backend 必须确定性拒绝，不能靠 command classifier 和 `cwd` 检查替代运行时隔离。
4. 三个公开动态诊断工具默认都必须在 disposable public execution snapshot 中运行。这个快照必须包含模型当前 candidate source patch，否则运行结果不能验证当前候选补丁；命令产生的 `__pycache__`、`.pytest_cache`、构建目录、临时日志和 scratch 文件默认不得写回真实 episode workspace。
5. 必须新增 public-command 专用执行接口，不能直接复用现有普通 `workspace_adapter.run_command(...)` 作为模型可见 public command runner。该接口可以在内部复用底层进程能力，但必须先创建 public execution snapshot，并证明没有 run directory mount、没有宿主路径暴露、没有 raw runtime artifact 可见。
6. 每次执行必须生成 `public_execution_snapshot_digest` 或等价快照标识，记录 `candidate_patch_included`、`execution_side_effects_discarded`、`post_run_workspace_digest_matches_pre_run`、`workspace_mutation_detected`、`result_valid_for_training` 和 `final_patch_pollution=false` 等事实。
7. 如果执行后真实 episode workspace 被 public command / project test / scratch Python 改变，必须设置 `workspace_mutation_detected=true` 和 `result_valid_for_training=false`，除非该变化发生在明确可丢弃且已丢弃的 snapshot side effect 中。
8. Stage 16G.3A complete 的最低通过条件必须是下面二选一：
   - Docker 或等价隔离后端可用，并有机器证据证明 `network_policy=deny` / `network_policy=none`、无 run directory mount、无宿主路径暴露、snapshot side effects 已丢弃。
   - 只完成 schema、profile、classifier 和 `planned_not_enabled` evidence，不把 `run_public_command`、`run_project_test`、`scratch_python` 暴露进 `swe_public_core`。
9. 如果实现只能退回普通本机子进程执行，必须写入 `network_isolation_proven=false` 和 `core_profile_exposure_allowed=false`，不能把这个 fallback 当成 Stage 16G.3A 完成态。
10. runtime 层必须提供无网络 evidence。不能只靠拒绝 `curl`、`wget` 等命令名，因为网络也可能来自 Python socket、测试插件、项目脚本或二级解释器。Docker backend 的网络策略必须 fail closed：未知策略、默认 bridge、未记录策略或非 deny 策略都使 Stage 16G.3 inspector 失败。
11. `cwd` 必须是 workspace-relative，不能是绝对路径，不能包含 `..`，不能指向 hidden path、runtime-private、依赖缓存写入区或 evaluator-only 路径。
12. 命令必须先进入 command classifier，得到 `command_family`、`public_command_capability`、`risk_level`、`policy_decision`、`safe_argv` 和 `reason_code`。
13. 受控环境变量必须来自 public command profile 的 `env_profile` 或 `public_env_overrides`，并在 ingestion-time 通过白名单校验。模型不能通过 shell 前缀、`env` 包装或工具参数自由设置环境变量。第一版建议只允许 `PYTHONPATH`、`DJANGO_SETTINGS_MODULE`、`CI`、`NODE_ENV` 等显式登记字段。
14. 工具结果必须包含 `stdout_preview`、`stderr_preview`、`exit_code`、`timed_out`、`duration_ms`、`truncated`、`stdout_artifact_ref` / `stderr_artifact_ref` 或等价私有 artifact 指针。
15. 模型可见 preview 必须路径脱敏、长度受限、禁止 hidden marker、禁止本机绝对路径、禁止 raw run directory、禁止 runtime-private ref。
16. 截断输出必须同时生成两层 artifact：模型可分页读取的 public-safe sanitized artifact，以及不可直接给模型的 raw stdout / stderr 私有 artifact。`read_tool_result_artifact` 或等价分页入口只能读取 sanitized artifact；inspector 必须验证 sanitized artifact 和 raw artifact 没有混用。
17. Stage 16G.3A 必须新增 command output artifact schema，至少区分 `sanitized_model_readable`、`raw_restricted_audit`、`artifact_visibility`、`artifact_kind`、`source_tool_call_id`、`truncation_policy` 和 `sha256`。现有通用 tool result artifact 如果没有 visibility / raw-sanitized 类型字段，必须扩展或包一层 Stage 16G.3 专用 manifest。
18. raw stdout / stderr artifact 默认 `runtime_private_or_restricted_audit`，不能直接进入 public evidence、模型可见 transcript 或 `read_tool_result_artifact`。必须有 raw-ref 读取拒绝测试。
19. 所有拒绝都必须使用统一 envelope：`status="denied"`、`reason_code`、`policy_version`、`retryable`、`safe_alternative_tool`、`safe_rewrite_example`、`public_command_capability`。
20. 所有 timeout 都必须区分“命令真实超时”和“工具预算超时”；timeout 结果不能进入成功验证声明。
21. 工具 observation token 必须在 TrainingView 中 mask 为 0；模型的 tool call token 是否进入 policy loss 仍由 Stage 16G.6 统一决定。
22. 新工具必须登记到 permission system 的路径字段白名单或等价路径审计机制中，至少覆盖 `cwd`、profile 派生路径、scratch 目录和 sanitized artifact 读取路径。不能只在 registry 和 executor 中新增工具。

### 7.3 第一版 command family

Stage 16G.3A 第一版应支持下面这些公开 family 的分类和执行承载：

| command_family | 示例 | 处理方式 |
| --- | --- | --- |
| `public_test` | `python -m pytest -q tests/test_x.py::test_y` | 优先路由到 `run_project_test` |
| `python_module_smoke` | `python -m compileall src` | 允许有限集合，必须无网络、无写依赖 |
| `repo_inspection` | `git status --short`、`git diff --name-only`、`git grep pattern`、`rg pattern path` | 可由 `run_public_command` 承载，但应继续鼓励结构化 `grep` / `git_diff` |
| `project_declared_command` | 任务 public environment 声明的 smoke / lint / docs 命令 | 必须由 command routing 生成，不由模型自由猜测 |
| `manifest_derived_command` | 从 `pyproject.toml`、`tox.ini`、`noxfile.py`、`package.json`、`Makefile` 等公开清单派生的候选命令 | Stage 16G.3 第一版可标记为 `planned_not_enabled`，但 schema 必须预留来源、校验和 profile 状态 |
| `scratch_python` | 临时 Python 脚本 | 只由 `scratch_python` 承载，不通过任意 `python -c` 放开 |

说明：`pytest --collect-only` 也属于测试体系，默认应由 `run_project_test` 或 project test router 承载。只有当 Stage 16G.3C 明确把它登记为 public test profile，`run_public_command` 才能通过结构化路由提示模型改用 `run_project_test`。

第一版必须拒绝：

```text
curl / wget / network command
pip install / npm install / cargo fetch 等依赖安装
rm / mv / cp / chmod / chown / git checkout / git reset 等破坏性或状态回滚命令
git log / git show / reflog / blame 等 Git history 作弊路径
cat / sed / awk 大范围文件读取，如果已有 read_file / grep / glob 可替代
任何 shell 管道、重定向、命令拼接、命令替换、变量展开、后台运行
任何访问 hidden verifier、参考补丁、测试补丁、runtime-private、run directory、本机绝对路径的命令
```

### 7.4 16G.3A 产物

建议新增：

```text
src/repo_harness/tools/public_command.py
scripts/pre_verl/build_stage16g3a_public_command_substrate.py
tests/unit/test_repo_harness_stage16g3a_public_command_substrate.py
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_3/implementation-notes.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_3/stage16g3a_public_command_profile_schema_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_3/stage16g3a_public_test_profile_schema_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_3/stage16g3a_public_command_substrate_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_3/stage16g3a_command_artifact_visibility_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_3/stage16g3a_safety_denial_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_3/stage16g3a_path_leak_scan_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_3/stage16g3a_acceptance_summary.json
```

并新增 inspector：

```bash
repo-harness inspect-stage16g3a-public-command-substrate <stage16g3a_acceptance_summary.json> --assert-complete
```

### 7.5 Public command profile schema

Stage 16G.3A 必须先设计 public command / public test 的数据契约，再实现具体工具。建议新增 `PublicCommandProfile` 和 `PublicTestProfile`，字段至少包括：

```text
id
profile_kind
runner
base_argv
allowed_args_schema
selector_schema
env_profile
timeout_sec
working_directory_policy
network_policy
source
source_sha256
visibility
enabled_state
public_safe_description
```

设计要求：

1. `base_argv` 必须是结构化 argv，不是 shell 字符串。
2. `allowed_args_schema` 必须描述模型可传的参数形状，禁止任意字符串拼接。
3. `env_profile` 只能来自 ingestion-time 校验后的 public environment，不能由模型自由设置。
4. `source` 必须区分 `task_declared`、`manifest_derived`、`harness_builtin`、`planned_not_enabled`。
5. `source_sha256` 或等价 digest 必须绑定 task public environment、公开清单或 profile 定义，避免后续 evidence 静默漂移。
6. `visibility` 必须是 public-safe；任何 hidden verifier、official selector、参考补丁、测试补丁或 evaluator-only 来源都不能进入 public profile。
7. `enabled_state` 必须区分 `enabled`、`planned_not_enabled`、`diagnostic_only`、`rejected`，避免 Python / pytest 第一版被误读成多语言完整 parity。

## 8. Public test source boundary

Stage 16G.3 正在新增可训练的公开测试工具，因此 public test source 的完整性必须在本阶段成为硬边界，不能只留到 Stage 16G.4D reward metadata。

`run_project_test` 执行前必须判断 public test 文件是否被模型当前 candidate patch 修改。若 public test source 被修改，第一版必须选择下面两种策略之一：

```text
策略 A：拒绝运行，并返回 public_test_source_clean=false、result_valid_for_training=false、safe_rewrite_example。
策略 B：在干净 public test 快照上运行，并返回 public_test_source_clean=false、ran_on_clean_public_test_snapshot=true。
```

无论选择哪种策略，都必须满足：

1. 不能让“模型先修改 public tests，再运行 public tests 通过”的轨迹进入主 policy-loss candidate。
2. tool result 必须包含 `public_test_source_clean`、`public_test_snapshot_digest`、`candidate_patch_included`、`result_valid_for_training`、`official_prediction_eligible` 等事实。
3. 如果 public test 被修改但命令仍然运行，必须明确运行的是干净测试快照，而不是被模型改过的测试文件。
4. 这个边界必须有 probe：先修改 public test，再调用 `run_project_test`，验收器必须看到拒绝或 clean snapshot facts。

## 9. Stage 16G.3B：`run_public_command`

### 9.1 目标

Stage 16G.3B 新增主训练默认 profile 中的公开命令工具：

```text
run_public_command(command_profile_id, args?, cwd=".", timeout_sec=60, purpose?)
```

字段名可以在实现时微调，但必须表达：

1. 模型请求的公开命令 profile。
2. workspace-relative `cwd`。
3. timeout。
4. 可选 `purpose`，用于模型说明这次命令的公开诊断目的。

Stage 16G.3 第一版必须以 `command_profile_id + structured args` 为主路径。裸 `argv` 不能作为自由命令入口；只有当 `argv` 能被规范化匹配到某个已启用 `PublicCommandProfile`，并且参数满足该 profile 的 `allowed_args_schema` 时才允许执行。字符串 `command` 只能作为兼容层或模型提示中的自然语言示例，不能成为 executor 内部安全事实来源。

验收 summary 必须显式写入：

```text
raw_freeform_argv_supported=false
argv_must_resolve_to_enabled_profile=true
unknown_argv_rejected=true
```

必须包含下面这些负例：

```text
argv=["bash","-lc","..."] -> denied
argv=["python","-c","..."] -> denied 或路由建议 scratch_python
argv=["pytest", ...] -> denied 并建议 run_project_test
argv=["git","log"] -> denied
```

`run_public_command` 是正式 `swe_public_core` 工具，不是 `execute_bash` 的别名。`execute_bash` 继续作为 legacy / extended / diagnostic 过渡能力存在，不应重新进入主训练默认 scaffold。

### 9.2 允许范围

第一版 `run_public_command` 应聚焦：

```text
公开仓库检查：git status --short、git diff --name-only、git diff --stat、git grep
公开内容搜索：rg 的受限形式，且不要替代结构化 grep 的主路径
公开 Python smoke：python -m compileall <公开路径>
任务声明的公开命令：只能通过 public command router 显式声明
```

`run_public_command` 不应直接承担定向测试主路径。模型想跑测试时，应优先使用 `run_project_test`。如果模型把 pytest 命令传给 `run_public_command`，工具可以返回结构化拒绝或路由提示：

```json
{
  "reason_code": "route_public_test_to_run_project_test",
  "safe_alternative_tool": "run_project_test",
  "safe_rewrite_example": "run_project_test(selector=\"tests/test_x.py::test_y\")"
}
```

### 9.3 模型可见说明

模型提示必须写清：

1. `run_public_command` 用于公开诊断，不用于文件修改。
2. 文件修改使用 `apply_patch` / `write_file`。
3. 文件读取优先使用 `read_file` / `grep` / `glob_files` / `symbol_search`。
4. 测试优先使用 `run_project_test`。
5. 不能用它访问 hidden evaluator、Git history、runtime-private、宿主路径或网络。

### 9.4 验收

Stage 16G.3B probe 必须覆盖：

1. 一个允许的公开仓库检查命令返回 stdout、stderr、exit code。
2. 一个允许的公开 compile / smoke 命令返回 exit code。
3. 一个 pytest 命令被路由到 `run_project_test` 或返回可学习替代建议。
4. 一个破坏性文件命令被拒绝，并说明应使用结构化文件工具。
5. 一个 Git history 命令被拒绝。
6. 一个网络命令被拒绝。
7. 一个尝试访问 hidden marker / runtime-private / 本机路径的命令被拒绝。
8. tool result 公开摘要无路径泄漏，raw artifact 不返回给模型。

## 10. Stage 16G.3C：`run_project_test`

### 10.1 目标

Stage 16G.3C 新增参数化公开测试工具：

```text
run_project_test(selector?, test_file?, test_name?, command_profile?, timeout_sec?)
```

具体 schema 可以在实现时选择，但必须解决当前 `run_tests` 无参数的问题。模型必须能够运行单个测试文件、单个测试函数、少量公开 selector 或任务声明的 public smoke command。

### 10.2 路由原则

`run_project_test` 不能让模型自由提交任意 shell 命令。它应从下面来源生成真实命令：

1. task public environment 中声明的 `public_test_command`。
2. task public environment 中声明的 `public_test_profiles`，例如 `pytest`、`unittest`、`django_test`、`sphinx_build_smoke`、`npm_test`、`go_test`、`cargo_test`。
3. Stage 16G.3C 第一版实际实现可以先只支持 Python / pytest，但 schema 和 evidence 必须说明其它 profile 是 `planned_not_enabled`，不能假装已经覆盖。
4. 如果任务没有公开测试配置，工具必须返回结构化拒绝，并建议使用 `run_public_command` 的公开 smoke 或源码检查，而不是偷偷运行 hidden verifier。

任务声明的公开命令本身也必须经过 ingestion-time validation、profile whitelist、字段白名单和 sha256 绑定。不能因为某个命令写在 task public environment 中，就绕过 Stage 16G.3A 的 command policy、runtime isolation、网络隔离和路径边界。

### 10.3 selector 安全规则

第一版 pytest selector 必须满足：

1. 路径是 workspace-relative。
2. 路径不能包含 `..`、绝对路径、hidden path、runtime-private、参考补丁、测试补丁或 evaluator-only marker。
3. selector 数量有上限，建议第一版最多 20 个。
4. `-k` 表达式如果支持，必须有长度上限和字符白名单。
5. 不允许通过 selector 注入 shell 语法。
6. 不允许修改 public tests 后把测试通过作为成功依据。若 public test 文件已被 candidate patch 修改，必须按第 8 节执行拒绝或 clean snapshot 策略。

### 10.4 与旧 `run_tests` 的关系

`run_tests` 当前是无参数 public feedback 工具。Stage 16G.3C 不应立即删除它。推荐路线：

```text
run_tests:
  legacy compatibility / full configured public feedback

run_project_test:
  新主路径，支持参数化公开测试和 public command routing
```

后续 Stage 16G.5 parity probe 再决定是否把 `run_tests` 降级为兼容工具或内部 verifier facade。

### 10.5 多语言覆盖状态

Stage 16G.3C 第一版可以只实现 Python / pytest，但 acceptance summary 必须明确列出下面这些 profile 的状态：

```text
pytest
unittest
django_test
sphinx_build_smoke
tox
nox
npm_test
go_test
cargo_test
make_test
```

非 pytest profile 如果尚未实现，必须标记为 `planned_not_enabled` 或 `post_16G_optional_for_current_dataset`，不能让 Stage 16G.3 完成态被误读成已经完成 Claude Code / Codex 多语言动态诊断 parity。

### 10.6 验收

Stage 16G.3C probe 必须覆盖：

1. 运行单个 pytest 文件。
2. 运行单个 pytest node id。
3. 运行任务声明的默认 public test command。
4. public test 失败时返回 stdout、stderr、exit code、parsed test summary 和 retry hint。
5. public test timeout 时返回 timeout fact，不允许模型把它声明为测试通过。
6. final-only 或 hidden verifier 存在时，只有 public environment 明确声明的公开测试或公开命令可以运行；没有 public route 时必须结构化拒绝，不能自动推断 hidden verifier、official selector 或 evaluator-only command。
7. public test 被模型修改后的拒绝或 clean snapshot 运行策略。
8. run_episode projection 中能看到工具事件、public test facts、TrainingView mask 和 sample eligibility facts。

## 11. Stage 16G.3D：`scratch_python` 和动态诊断闭环 probe

### 11.1 目标

Stage 16G.3D 新增临时复现脚本工具：

```text
scratch_python(code, cwd=".", timeout_sec=30, purpose?)
```

它用于让模型写最小复现、导入 smoke、数据结构实验或快速验证假设。它不是文件修改工具，不应把临时代码写进仓库最终补丁。

需要明确：`scratch_python` 是 Python-first 的受控复现工具，不等价于 mini-SWE-agent 的任意 shell 复现能力。语言通用 scratch reproduction、Node / Ruby / Go / Rust 等临时脚本能力不在 Stage 16G.3 第一版完成范围内，必须在 evidence 中标记为未覆盖或后续扩展。

### 11.2 执行边界

`scratch_python` 必须满足：

1. 脚本内容有字节上限，建议第一版 64 KiB。
2. 执行 timeout 有上限，建议第一版默认 30 秒，最大 120 秒。
3. 第一版必须在隔离的 public projection、临时复制工作区或 Docker sandbox 中执行，不能直接在真实 episode 工作区中运行任意 Python。
4. 默认无网络、无宿主路径、无 run directory mount、无 runtime-private mount；这些隔离事实必须进入 evidence。
5. 源码对脚本应只读，或者写入发生在可丢弃的复制工作区中。脚本产生的缓存、临时文件和输出默认不进入 final patch。
6. 脚本可以读取公开源码和公开依赖，但不能写共享依赖环境。
7. 脚本不能访问 hidden verifier、参考补丁、测试补丁、runtime-private、run directory、宿主绝对路径、网络、环境密钥或共享依赖写入区。
8. 脚本不能修改 episode 源码；如需修改源码，模型必须使用 `apply_patch` 或 `write_file`。
9. 如果实现无法证明上面隔离条件，`scratch_python` 不得进入 `swe_public_core`，只能作为 rejected / planned / diagnostic-only evidence。

### 11.3 输出和 artifact

`scratch_python` 结果必须和 public command 底座一致：

```json
{
  "status": "ok",
  "exit_code": 0,
  "stdout_preview": "...",
  "stderr_preview": "...",
  "timed_out": false,
  "truncated": false,
  "script_artifact_visibility": "runtime_private_or_restricted_audit",
  "model_visible_observation": "redacted_truncated",
  "repository_mutation_performed": false,
  "final_patch_pollution": false
}
```

### 11.4 mini-SWE-agent 风格闭环 probe

Stage 16G.3D 必须提供一个小型真实闭环 probe，证明 RepoHarness 已经覆盖 mini-SWE-agent 的动态诊断下限，但用结构化工具实现：

```text
read_file / grep
-> run_project_test 或 run_public_command 观察失败
-> scratch_python 写最小复现
-> apply_patch 修改源码
-> run_project_test 验证公开测试
-> git_diff / final patch projection
```

这个 probe 必须通过 `run_episode(real_episode)` 入口，而不是只调用工具函数。公开 evidence 只保留状态、计数、sha256、相对路径和 public-safe 摘要，不保留临时目录、本机路径、原始完整 stdout/stderr 或隐藏 selector。

## 12. 权限和安全设计

### 12.1 确定性策略优先

RepoHarness 强化学习 rollout 不能依赖真人 approval。Codex / Claude Code 中的 approval、guardian 和 hooks 思想在 Stage 16G.3 转成确定性策略：

```text
公开安全动作：自动允许
明确越界动作：确定性拒绝
可恢复错误：返回 safe alternative 和 rewrite example
可疑行为：记录 monitor / quarantine facts，但不靠 LLM judge 做唯一安全边界
```

### 12.2 必须拒绝的行为

Stage 16G.3 所有命令工具都必须拒绝：

1. 读取或输出 hidden verifier、参考补丁、测试补丁、official selector、reward metadata、provider secret。
2. 访问 `.git` 历史、reflog、对象数据库、未来提交或 benchmark 元数据。
3. 使用绝对路径或 `..` 越过 workspace。
4. 访问 run directory、runtime-private artifact、workspace 外宿主目录。
5. 网络访问，包括命令名网络工具、Python / Node / pytest 插件 / 项目脚本触发的 runtime-level 网络访问。
6. 依赖安装或共享依赖写入。
7. shell 注入、管道、重定向、命令拼接、变量展开、subshell、heredoc、后台任务。
8. 通过 Python、Node、Ruby、Perl 等二级解释器绕过命令策略读取隐藏路径。
9. 修改 public tests 之后只用 public tests 作为成功证明。`run_project_test` 必须按第 8 节拒绝或改用干净 public test 快照。

### 12.3 拒绝也要可学习

每个拒绝结果都必须包含：

```text
reason_code
policy_version
command_family
retryable
safe_alternative_tool
safe_rewrite_example
public_safe_explanation
invalid_for_training / negative_sample_eligible / quarantine_eligible facts
```

拒绝事件不能被简单过滤出轨迹。合理拒绝可以作为负样本或恢复训练材料；工具面误拒绝应进入 false positive 统计，作为后续 harness 改进输入。

## 13. 训练投影和 run_episode linkage

Stage 16G.3 新工具必须进入：

1. tool registry contract delta。
2. profile taxonomy delta。
3. scaffold / model-visible tool schema。
4. public environment prompt。
5. tool event / trajectory。
6. TrainingView response spans，其中 tool observation mask 为 0。
7. compat projection。
8. route qualification / policy-loss eligibility facts。
9. final answer 测试声明的后续交叉校验候选 facts。

Stage 16G.3 完成不等于正式允许 policy loss。建议 acceptance summary 继续保持：

```text
stage17b_real_data_freeze_allowed=false
stage20_warm_start_data_generation_allowed=false
stage21_formal_rl_allowed=false
```

是否允许进入主 SWE 强化学习 profile 冻结，必须等 Stage 16G.5 parity probe 和 Stage 16G.6 training eligibility gate。

## 14. 建议实现范围

建议新增或修改：

```text
src/repo_harness/tools/minimal.py
src/repo_harness/tools/public_command.py
src/repo_harness/workspace/public_execution.py
src/repo_harness/tasks/command_policy.py
src/repo_harness/tasks/public_command_profiles.py
src/repo_harness/tasks/public_environment.py
src/repo_harness/context/tool_result_artifacts.py
src/repo_harness/permissions/system.py
src/repo_harness/scaffolds/simple_react.py
src/repo_harness/scaffolds/planner_coder_verifier.py
src/repo_harness/stage16g3_public_command.py
src/repo_harness/cli/main.py
scripts/pre_verl/build_stage16g3a_public_command_substrate.py
scripts/pre_verl/build_stage16g3b_run_public_command.py
scripts/pre_verl/build_stage16g3c_run_project_test.py
scripts/pre_verl/build_stage16g3d_scratch_python_probe.py
tests/unit/test_repo_harness_stage16g3a_public_command_substrate.py
tests/unit/test_repo_harness_stage16g3b_run_public_command.py
tests/unit/test_repo_harness_stage16g3c_run_project_test.py
tests/unit/test_repo_harness_stage16g3d_scratch_python.py
```

如果现有模块名称不同，实现时可以调整，但必须保持模块职责清晰：共享 public command 底座不能被分散在三个工具各自的 handler 里。

## 15. Evidence 和 inspector

Stage 16G.3 建议新增 evidence 目录：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_3/
```

每个子阶段至少输出：

```text
stage16g3*_source_inventory.json
stage16g3*_capability_delta_report.json
stage16g3*_tool_schema_report.json
stage16g3*_scaffold_exposure_report.json
stage16g3*_public_command_profile_report.json
stage16g3*_public_execution_snapshot_report.json
stage16g3*_command_artifact_visibility_report.json
stage16g3*_safety_denial_report.json
stage16g3*_projection_linkage_report.json
stage16g3*_path_leak_scan_report.json
stage16g3*_acceptance_summary.json
```

最终 Stage 16G.3 应有总 summary：

```text
stage16g3_acceptance_summary.json
```

Inspector 必须做到：

1. 重新扫描 public evidence，不信任旧 path leak report。
2. 绑定 source inventory sha256。
3. 校验 Stage 16G.3 所有新增工具出现在 registry、profile、scaffold、executor 和 run_episode projection 中。
4. 校验 public command / project test / scratch Python 共用同一套底座 policy version。
5. 校验每个拒绝 reason_code 都有 safe alternative 或明确不可恢复说明。
6. 校验截断输出存在可继续读取的 public-safe sanitized artifact 路径，且 raw artifact 没有直接返回给模型，也不能被 `read_tool_result_artifact` 读取。
7. 校验 public execution snapshot 隔离事实：没有 run directory mount，没有宿主绝对路径，没有 raw runtime artifact 可见，candidate patch 已包含，execution side effects 被丢弃，真实 episode workspace digest 未被公开诊断工具改变。
8. 校验 `workspace_mutation_detected`、`post_run_workspace_digest_matches_pre_run`、`final_patch_pollution` 和 `result_valid_for_training` 的组合语义。若公开诊断工具修改了真实 workspace，必须使训练成功依据失效。
9. 校验 Docker 或等价 backend 的网络策略 fail closed。未知策略、默认 bridge、未记录策略或非 deny 策略都必须失败；普通本机子进程 fallback 只能产生 `network_isolation_proven=false` 和 `core_profile_exposure_allowed=false`。
10. 校验 `run_public_command` 不支持自由裸 `argv`：`raw_freeform_argv_supported=false`、`argv_must_resolve_to_enabled_profile=true`、`unknown_argv_rejected=true` 必须成立。
11. 校验 public test source boundary：修改 public tests 后，`run_project_test` 必须拒绝或在干净 public test 快照上运行，并且 `result_valid_for_training=false` 或等价事实必须成立。
12. 校验 `PublicCommandProfile` / `PublicTestProfile` 字段完整、digest 绑定、source 可追溯、enabled_state 不夸大多语言能力。
13. 校验 mock / non-verl route 不被误标为 policy loss candidate。
14. 校验 Stage 17B / Stage 20 / Stage 21 仍不放行。
15. 对关键 report 使用字段白名单，禁止同步更新 digest 后塞入隐藏标记或本机路径。

建议 CLI：

```bash
repo-harness inspect-stage16g3a-public-command-substrate <summary> --assert-complete
repo-harness inspect-stage16g3b-run-public-command <summary> --assert-complete
repo-harness inspect-stage16g3c-run-project-test <summary> --assert-complete
repo-harness inspect-stage16g3d-scratch-python <summary> --assert-complete
repo-harness inspect-stage16g3-public-diagnostics <stage16g3_acceptance_summary.json> --assert-complete
```

## 16. 验收矩阵

Stage 16G.3 完成时必须至少通过下面这些 probe：

| probe | 必须证明 |
| --- | --- |
| public command allow probe | 允许的公开检查命令能返回 stdout、stderr、exit code、duration 和截断事实 |
| public command denial probe | 网络、Git history、hidden marker、宿主路径、破坏性文件命令被确定性拒绝 |
| raw argv denial probe | 自由裸 `argv` 默认不支持；未知 `argv` 被拒绝；`bash -lc`、`python -c`、`pytest`、`git log` 等负例返回结构化拒绝或更合适工具建议 |
| public execution isolation probe | public command 不直接复用普通 `run_command`，执行快照包含 candidate patch，没有 run directory mount、宿主路径、runtime-private artifact 或可持久化 side effects |
| side effect discard probe | `compileall`、`pytest` 或等价命令产生缓存后，真实 episode workspace digest 保持不变，`final_patch_pollution=false` |
| backend isolation gate probe | Docker 或等价后端证明无网络；普通本机子进程 fallback 不允许暴露进 `swe_public_core` |
| command profile schema probe | `PublicCommandProfile` / `PublicTestProfile` 字段完整、digest 绑定、source 可追溯，manifest-derived profiles 第一版标记为 `planned_not_enabled` |
| project test default probe | 任务声明的默认 public test 能通过 `run_project_test` 执行 |
| project test selector probe | 单文件、单 node id 或等价 selector 能执行，且 selector 注入被拒绝 |
| modified public test boundary probe | 模型修改 public test 后，`run_project_test` 拒绝或在干净 public test 快照上运行，且结果不能成为主训练成功依据 |
| long output artifact probe | 长 stdout / stderr 被截断成模型可见 preview，sanitized artifact 可分页读取，raw artifact 读取被拒绝 |
| scratch Python probe | 临时 Python 复现脚本能运行，输出可见但 raw artifact 私有，不污染 final patch |
| run_episode projection probe | 三个新工具都通过 `run_episode(real_episode)` 出现在 tool event、TrainingView 和 compat projection |
| mini-SWE-agent parity-lite probe | 用结构化工具完成“观察失败 -> 复现 -> 修改 -> 验证 -> diff”的动态闭环 |
| public path leak probe | evidence 无本机路径、hidden marker、runtime-private、参考补丁、测试补丁、run directory 泄漏 |

通过条件：

```text
failure_count=0
stage16g3_complete=true
stage16g4_allowed_to_start=true
stage17b_real_data_freeze_allowed=false
stage20_warm_start_data_generation_allowed=false
stage21_formal_rl_allowed=false
```

## 17. 风险和回退策略

| 风险 | 回退策略 |
| --- | --- |
| 命令策略过窄，模型仍无法完成真实诊断 | 把被拒绝但合理的命令记录为 false positive，Stage 16G.3B/C 小步扩 allowlist |
| 命令策略过宽，出现泄漏或作弊路径 | 立即 hard fail 对应 probe，收紧 command family，不进入 Stage 16G.4 |
| `run_project_test` 被模型滥用为 hidden verifier 探测 | public test route 只从 public environment 生成，不暴露 hidden selector；失败进入 quarantine facts |
| `scratch_python` 污染工作区或 final patch | 保持或收紧为隔离 public projection、临时复制工作区、只读源码投影或 Docker sandbox；不满足污染隔离则不得进入 `swe_public_core` |
| 输出太长或包含路径泄漏 | 强制 head-tail summary、raw artifact 私有化、public scan fail closed |
| 与 `execute_bash` 语义分叉 | 明确 `run_public_command` 是新主路径，`execute_bash` 不进入 core 默认；保留兼容测试但不扩大旧工具 |

## 18. 完成后的状态

Stage 16G.3 完成后，RepoHarness 应达到下面状态：

1. `swe_public_core` 具备结构化文件修改和公开动态诊断能力。
2. 模型可以运行公开命令、公开定向测试和 scratch Python 复现脚本。
3. 所有动态诊断输出都有 stdout、stderr、exit code、timeout、truncation 和 raw artifact 私有化事实。
4. 所有拒绝都有结构化恢复路径。
5. 新工具通过 `run_episode(real_episode)` 和 TrainingView 投影。
6. hidden evaluator、参考补丁、测试补丁、runtime-private、Git history、宿主路径、网络和共享依赖写入边界仍然被机器 probe 覆盖。

Stage 16G.3 完成后仍不进入 Stage 17 数据冻结或 Stage 20 / Stage 21 训练。下一阶段应进入 Stage 16G.4，收口 dependency setup、persistent diagnostic shell、权限恢复、hooks、quarantine、final answer / verifier / reward metadata linkage。
