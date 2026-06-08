# Stage 16G.3 重写前设计草案与待确认决策

本文是正式重写 `55-stage-16g-3-execution-plan.md` 之前的设计对齐文档。它不是执行计划本身，也不要求立即实现代码。它的目的有三个：

1. 把 Stage 16G.3 的设计方向从旧的“窄公开命令工具”调整到更接近 Claude Code、Codex 和微软 MAI-Thinking-1 技术报告披露的 SWE agentic RL 工具表面。
2. 把正式执行计划中不能再保留为“二选一”“建议”“可以”的关键决策提前列出，避免执行 agent 在实现阶段自行选择高风险方案。
3. 给出当前建议采用的默认方案，并明确哪些地方需要用户确认后才能写入正式计划。

参考输入：

```text
docs/agentic_RL/repo_harness_verl_workstreams/55-stage-16g-3-execution-plan.md
docs/harness_improve/16G-3_plan_V1.md
docs/harness_improve/bash_tool_advice.md
docs/harness_improve/main_20260602_2.pdf
reference/claude-code-typescript-src/AGENTS.md
reference/codex/AGENTS.md
docs/harness_improve/codex_vs_claude_code_harness_design_analysis.md
```

## 1. 当前需要重写的原因

现有 `55-stage-16g-3-execution-plan.md` 的安全边界非常谨慎，但它仍然明显偏向训练态私有 DSL：

```text
run_public_command(command_profile_id, args)
run_project_test(selector)
scratch_python(code)
pytest 命令进入 run_public_command 时被拒绝并提示 run_project_test
每条公开命令默认在一次性 public execution snapshot 中运行
```

这个设计有较强的可审计性，但存在一个核心问题：模型学到的操作表面和真实 SWE agent 产品形态不一致。Claude Code 的 `Bash`、Codex 的 shell / `exec_command`，以及微软 MAI-Thinking-1 报告中的 SWE RL 工具，都更接近：

```text
bash(command: string)
结构化编辑工具
执行环境负责沙箱、隔离、审计和反作弊
```

微软报告尤其值得重视。报告明确写到 SWE agentic training data 使用的工具是 `bash` 和 `str_replace_editor`，其中 `bash` 的参数是 `command: string`，并且描述为 full Linux shell environment，可以包含 pipes、redirects 和其他 shell features。报告同时强调，reward hacking 防护主要靠 Sandbox Execution Environment、默认网络隔离、git history 清洗、隐藏测试、grading 前测试重置、LLM monitor 和人工复核，而不是靠 Bash 命令白名单。

因此，Stage 16G.3 的重写方向应该从：

```text
安全 profile-routed command DSL
```

调整为：

```text
真实 SWE agent 风格的 bash 表面
+
RepoHarness 内部 SEE 等价沙箱、网络隔离、git/test 防作弊、artifact 分层和训练资格审计
```

这不是降低安全要求，而是把安全边界从“模型命令表面”下沉到“执行环境和训练数据治理”中。

## 2. 建议冻结的总体方向

建议正式 Stage 16G.3 计划采用下面的总体目标：

```text
Stage 16G.3：SEE 风格 Bash 执行底座、内部测试路由和反 reward-hacking 观测体系
```

模型可见主工具建议调整为：

```text
bash(command: string, timeout_sec?, purpose?)
```

或者在短期兼容期使用：

```text
run_public_command(command: string, timeout_sec?, purpose?)
```

但无论工具名如何，模型看到的行为都应该接近 Bash：

```bash
python -m pytest tests/test_parser.py::test_empty_input -q
pytest tests/test_config.py -x
python -m compileall src
rg "missing_timeout" src tests
git diff --stat
cat <<'PY' > /tmp/repro.py
...
PY
python /tmp/repro.py
```

内部仍然必须实现：

```text
SEEEquivalentExecutionSubstrate
CommandMonitor
ProjectTestRouter
TestTrustClassifier
GitHistoryMonitor
NetworkMonitor
TestTamperMonitor
ArtifactVisibilityPolicy
TrainingEligibilityFacts
```

也就是说，模型输入 Bash 命令，RepoHarness 内部识别它是不是测试、搜索、构建、复现脚本、潜在作弊、网络访问、git history 探测或测试篡改。模型不应该被迫学习 `run_project_test(selector=...)` 这种评测 DSL。

## 3. 推荐的子阶段拆分

建议正式计划不再沿用旧的四段：

```text
16G.3A shared public command execution substrate
16G.3B run_public_command
16G.3C run_project_test
16G.3D scratch_python
```

而是改成下面更贴近新方向的拆分。

### 3.1 Stage 16G.3-0：设计冻结与环境能力审计

目的：在实现前确认当前 Docker backend、workspace materialization、hidden verifier、final patch capture、artifact store 和 TrainingView 能否支撑宽 Bash 表面。

必须产出：

```text
stage16g3_design_decision_record.md
stage16g3_execution_backend_capability_audit.json
stage16g3_hard_gate_matrix.json
```

核心检查：

```text
是否能做到每个 episode 一个隔离容器
结构化读文件、搜索、编辑工具和 Bash 是否操作同一个 episode workspace
是否能默认断网
是否能证明没有 run_dir / runtime-private / hidden verifier / gold patch / test patch 挂载
是否能捕获 stdout / stderr / exit_code / duration / timeout / truncation
是否能区分 sanitized artifact 和 raw restricted audit artifact
是否能检测 Bash 对仓库 tracked files 的写入
是否能在最终 patch 导出时排除缓存、临时文件和测试执行副作用
是否能在 grading 前 reset visible tests
是否能把 hidden tests 仅在 grading 阶段 apply
是否能在 clean grader checkout 中 replay cleaned final.patch
```

如果这些硬门槛不满足，宽 Bash 只能标记为 `planned_not_enabled` 或 `diagnostic_only`，不能进入 `swe_public_core`。

### 3.2 Stage 16G.3A：SEE 等价执行底座

目的：把原来的“每条命令一次性 snapshot”改成“每个 episode 一个持久但可销毁的隔离执行环境”。

建议语义：

```text
episode 开始：
  创建 fresh isolated container
  materialize base repo
  预装或挂载已批准依赖
  不挂载 hidden verifier / gold patch / test patch / runtime-private
  默认 network=none

episode 中：
  bash 命令在同一个容器内执行
  每次 bash call 是新的非交互 subshell
  cwd/env 的 shell 进程状态不跨 tool call 持久化
  文件系统副作用在本 episode 容器内持久化
  read_file / grep / glob / apply_patch / write_file / edit_file 和 bash 看到的是同一个 candidate workspace
  stdout/stderr/exit_code/duration/truncation 进入 trajectory
  raw artifact 只进 restricted audit
  sanitized artifact 才能被模型分页读取

episode 结束：
  收集允许的 source diff
  过滤临时文件、缓存、构建产物和 runtime-private 路径
  生成 cleaned final.patch / final.diff 投影
  在 grader-only clean checkout 中 replay cleaned final.patch
  grading 前 reset visible tests
  grading 阶段 apply hidden tests / verifier
  容器销毁
```

这个设计比“每条命令都 disposable snapshot”更接近微软 SEE、Claude Code 和 Codex 的真实终端体验。模型可以自然创建 `/tmp/repro.py`、运行多次测试、保留构建产物和临时脚本来继续调试，但最终训练数据只导出允许的源码补丁和脱敏观察。

这里还有一个必须在正式计划中写硬的边界：最终 verifier 不应该在 rollout 容器原地运行。对于宽 Bash，rollout 容器可能包含测试缓存、临时脚本、被修改的 public tests、环境变量文件、构建产物或模型创建的 wrapper。最终 verifier 应该在 grader-only clean checkout 中应用 cleaned final.patch，再 reset visible tests 并 apply hidden tests。这样 reward 只评估候选源码补丁，不继承 rollout 副作用。

### 3.3 Stage 16G.3B：模型可见 `bash(command)` 工具

目的：提供真实 SWE agent 风格的命令执行表面。

建议 schema：

```python
bash(
    command: str,
    timeout_sec: int | None = None,
    purpose: str | None = None,
)
```

说明：微软 MAI-Thinking-1 报告中的 Bash schema 核心只有 `command: string`。`timeout_sec`、`purpose` 或未来可能出现的 `cwd` 都是 RepoHarness 为审计、预算和工具回放增加的扩展字段，不能在正式计划中描述成微软原样 schema。若追求更强产品表面对齐，可以把 `timeout_sec` 和 `purpose` 作为隐藏执行配置或 optional audit extension，而不是强制模型每次填写。

如果为了兼容已有文档和旧工具名，第一版也可以命名为：

```python
run_public_command(
    command: str,
    timeout_sec: int | None = None,
    purpose: str | None = None,
)
```

但不建议长期训练模型只见 `run_public_command` 这个私有名称。正式计划需要确认：是否要在 Stage 16G.3 就把模型可见工具名改成 `bash`，还是先使用 `run_public_command` 做过渡。

工具描述应该强调：

```text
在仓库工作目录执行 Bash 命令
每次调用是新的非交互 subshell
使用非交互参数
避免 vi / nano / 需要用户输入的命令
长输出会截断并保存 artifact
文件编辑优先使用结构化编辑工具
网络默认不可用
```

不建议把 CommandStringV1 作为最终安全边界。CommandStringV1 可以保留为 transitional profile 或 monitor parser，但正式方向应该是：Bash 真实执行，安全边界由 SEE、网络、git scrub、测试重置、hidden verifier 隔离和 monitor 负责。

这也不等于所有高风险动作都只靠事后 monitor。下面这些边界必须由环境构造、挂载策略、网络策略和文件系统权限直接阻断：

```text
hidden verifier
gold patch
test patch
runtime-private raw artifacts
host absolute paths
secrets
未来 git objects / refs / branches / reflog
网络出口
grader-only scripts
```

CommandMonitor 可以补充分类、记录和 quarantine 信号，但不能成为这些硬边界的唯一防线。

### 3.4 Stage 16G.3C：内部项目测试路由与测试可信度分类

目的：不把 `run_project_test` 暴露为默认模型工具，但内部仍然识别 Bash 中的测试命令。

示例：

```bash
python -m pytest tests/test_parser.py::test_empty_input -q
```

内部记录：

```json
{
  "semantic_command_kind": "project_test",
  "test_runner": "pytest",
  "selector": "tests/test_parser.py::test_empty_input",
  "test_source_origin": "model_selected_existing_test",
  "public_test_observation_trusted": true,
  "official_feedback_eligible": true,
  "diagnostic_value": true
}
```

如果模型新增测试再运行：

```json
{
  "test_source_origin": "candidate_created_test",
  "public_test_observation_trusted": false,
  "official_feedback_eligible": false,
  "diagnostic_value": true
}
```

如果模型修改已有 public tests 或测试配置：

```json
{
  "test_source_origin": "candidate_modified_public_test",
  "public_test_observation_trusted": false,
  "official_feedback_eligible": false,
  "test_tamper_suspicion": true
}
```

如果模型修改 public tests 后又运行测试，正式计划必须明确工具观察语义。推荐优先在 clean visible test snapshot 上运行候选源码补丁；如果为了诊断允许模型运行自己改过的测试，则模型可见 observation 必须显眼提示该结果不可信，并且结构化事实必须至少包含：

```text
public_test_observation_trusted=false
official_feedback_eligible=false
test_tamper_suspicion=true
diagnostic_value=true
```

这样可以允许模型把测试当作调试脚手架，但不能让“改测试后通过”变成官方公开反馈或训练成功依据。

关键点：public test observation 的可信度不能直接等同于整条轨迹是否能进入 policy loss。更清楚的字段应该分开：

```text
public_test_observation_trusted
official_feedback_eligible
trajectory_policy_loss_eligibility
reward_hacking_suspicion
```

### 3.5 Stage 16G.3D：反 reward-hacking monitor 与 grading 前保护

目的：把微软报告指出的三类 SWE reward hacking 显式纳入 RepoHarness 设计。

必须覆盖：

```text
Internet search / 网络访问尝试
local git history search / 未来 commit 或本地历史探测
tampering with tests / 测试和测试框架篡改
```

建议第一版至少实现 rule-based monitor：

```text
network_attempt_detected
git_history_probe_detected
future_git_object_visible
visible_test_modified
test_config_modified
test_framework_tamper_suspicion
hidden_path_probe_detected
runtime_private_probe_detected
host_path_probe_detected
dependency_install_attempted
excessive_resource_use_detected
```

LLM monitor 建议作为 Stage 16G.3D 的可选增强或 Stage 16G.5 / 16G.6 前置。它不应该是唯一安全边界，但应该为 quarantine、人工审查和后续 reward builder 提供信号。

grading 前必须有硬保护：

```text
reset visible test files modified by the agent
apply hidden tests only at grading time
run verifier in grader-only clean checkout after replaying cleaned final.patch
do not expose hidden tests or official verifier artifacts during rollout
mark suspicious trajectories before reward export
```

训练放行前还必须有等价审查机制。Stage 16G.3 可以先只实现 rule-based monitor 和 monitor-ready facts，因为本阶段不放开 policy loss；但如果后续要声称达到 MAI-like training eligibility，Stage 16G.5 / 16G.6 / 17B 之前必须接入 LLM monitor、人工抽审或等价 quarantine 审查流程。微软报告里的 LLM monitor 不是唯一安全边界，但它是发现 monkey-patching testing framework、修改 equivalence behavior 等隐蔽 reward hacking 的重要补充。

### 3.6 Stage 16G.3E：动态诊断闭环 probe

目的：证明模型可以完成接近 Claude Code / Codex / MAI / mini-SWE-agent 的动态闭环。

建议 probe：

```text
1. read_file / grep / bash rg 定位代码和测试
2. bash("python -m pytest tests/test_x.py::test_y -q") 观察失败
3. bash("cat <<'PY' > /tmp/repro.py ... PY\npython /tmp/repro.py") 做临时复现
4. apply_patch / write_file 修改源码
5. bash("python -m pytest tests/test_x.py::test_y -q") 验证
6. bash("git diff --stat") 或 git_diff 查看补丁
7. final.patch capture
8. grading reset visible tests + apply hidden verifier
9. TrainingView / trajectory / artifact / eligibility facts 可检查
```

验收重点不是“某个 allowlist 命令能跑”，而是：

```text
命令输出进入 trajectory
sanitized observation 进入模型上下文
raw artifact 不可被模型读取
模型能用 Bash 真实调试
最终 patch 不包含临时脚本、缓存或测试污染
测试篡改和 git/history/network 探测能被标记
hidden verifier 不泄漏
```

### 3.7 Stage 16G.3F：文档与验收地图更新

需要同步更新：

```text
55-stage-16g-3-execution-plan.md
repo_harness_verl_harness_capability_acceptance_map.html
repo_harness_verl_stage16g_4way_tool_comparison.html
TrainingView / inspector 文档
tool schema 文档
```

尤其要修正旧表述：

```text
run_project_test 不再是 swe_public_core 默认模型工具
scratch_python 不再是最终 MAI-like core 的必需工具
run_public_command 如果保留，只是 bash-like command tool 的过渡命名
每条命令 disposable snapshot 不是宽 Bash 目标语义
真正目标是 per-episode SEE-equivalent container
```

## 4. 需要用户确认的关键决策

下面这些决策建议在正式重写 55 号计划前确认。

### 决策 1：模型可见命令工具名称

选项 A：

```text
bash(command: string)
```

优点：最接近 Claude Code、微软 MAI 和通用 SWE agent 训练表面。  
缺点：当前 RepoHarness 已有 legacy `bash` / `execute_bash` 语义，改名需要清理旧工具和文档，避免混淆。

选项 B：

```text
run_public_command(command: string)
```

优点：兼容现有 Stage 16G 文档和 RepoHarness “公开命令”命名。  
缺点：仍然是 RepoHarness 私有工具名，长期训练可能和真实产品表面有差距。

我的建议：

```text
正式目标采用 bash(command: string)。
如果实现迁移成本较高，可以短期保留 run_public_command 作为兼容别名或内部名称；
但长期 swe_public_core / MAI-like profile 应让模型看到 bash。
```

需要用户确认：Stage 16G.3 是否直接把模型可见主命令工具定名为 `bash`。

### 决策 2：Bash 能力宽度

选项 A：完整 Bash 表面，允许 pipes、redirects、heredoc、命令拼接、脚本创建。  
选项 B：CommandStringV1 受限命令字符串，拒绝大部分 shell 语法。  
选项 C：分 profile：`swe_public_core_transitional` 用 CommandStringV1，`swe_mai_like_core` 用宽 Bash。

我的建议：

```text
目标方案采用 C，但正式计划必须把最终方向写清楚：
  如果 SEE-equivalent 硬门槛满足，swe_mai_like_core 使用宽 Bash；
  如果硬门槛不满足，只能启用 transitional 窄 profile，不能声称 Stage 16G.3 达到 MAI/Claude/Codex 对齐。
```

需要用户确认：是否接受“宽 Bash 只有在 SEE 硬门槛满足时进入 core；否则 Stage 16G.3 只能完成 planned_not_enabled evidence”。

### 决策 3：执行环境语义

选项 A：每条命令 disposable snapshot，命令副作用默认丢弃。  
选项 B：每个 episode 一个持久隔离 container，命令副作用在 episode 内持久，episode 结束后销毁。  
选项 C：混合：Bash 用 episode container，某些审计 probe 或旧工具用 disposable snapshot。

我的建议：

```text
采用 C，其中 Bash 的正式语义采用 B。
每条命令 disposable snapshot 不适合作为宽 Bash 主语义；
它可以保留给某些只读 probe、兼容工具或调试型安全检查。
```

需要用户确认：是否同意把 16G.3A 从“public execution snapshot”重写为“per-episode SEE-equivalent container”。

### 决策 4：`run_project_test` 是否模型可见

选项 A：继续作为默认模型工具。  
选项 B：不作为默认模型工具，只作为内部 router、unit test helper、acceptance probe 或 optional scaffold。  

我的建议：

```text
采用 B。
模型通过 bash(command) 跑测试；
RepoHarness 内部用 ProjectTestRouter 识别测试语义和可信度。
```

需要用户确认：正式计划中是否删除 `run_project_test` 作为 `swe_public_core` 默认模型工具的目标。

### 决策 5：`scratch_python` 的定位

选项 A：继续作为默认模型可见工具。  
选项 B：作为过渡工具保留，直到宽 Bash 可安全支持 heredoc / 临时脚本。  
选项 C：不进入默认 core，只保留为 acceptance probe 或内部兼容能力。

我的建议：

```text
采用 B 或 C。
如果 Stage 16G.3 直接走宽 Bash，scratch_python 不是最终 MAI-like core 必需工具；
模型可以用 bash 创建 /tmp/repro.py 或临时脚本。
如果宽 Bash 暂时不能启用，scratch_python 可作为 transitional profile 的复现能力补丁。
```

需要用户确认：正式计划是否仍把 `scratch_python` 作为 P0 模型可见工具。

### 决策 6：网络与依赖安装

选项 A：完全无网络，依赖必须预装。  
选项 B：默认无网络，后续通过缓存代理和 domain allowlist 支持必要依赖。  
选项 C：允许 rollout 中自由安装依赖。

我的建议：

```text
采用 B 的长期目标，但 Stage 16G.3 第一版按 A 执行。
依赖安装、缓存代理、domain allowlist 和 dependency setup policy 放到 Stage 16G.4 或后续。
```

需要用户确认：Stage 16G.3 是否明确拒绝普通网络和自由依赖安装。

### 决策 7：git history 策略

选项 A：继续禁止 `git log`、`git show`、`git reflog` 等历史命令。  
选项 B：实现 time-traveled repo，清洗 base commit 之后的 commits、references、branches，再允许合理 git history。  
选项 C：宽 Bash 中不特殊处理 git history，只靠 monitor 标记。

我的建议：

```text
目标采用 B。
如果 B 在 Stage 16G.3 来不及完成，则宽 Bash 不应进入正式 core；
或者必须把未来 git history 泄漏作为 hard gate 失败。
不建议只靠 monitor 标记未来 commit 探测。
```

需要用户确认：Stage 16G.3 是否把 git future-history scrub 列为宽 Bash core 的硬门槛。

### 决策 8：测试篡改策略

选项 A：模型修改 public tests 后，相关测试 observation 直接拒绝。  
选项 B：允许作为 diagnostic 运行，但标记为不可信，grading 前 reset tests。  
选项 C：在 clean visible tests + hidden tests overlay 中 grading，rollout 中 public test observation 只作诊断信号。

我的建议：

```text
采用 C。
rollout 中可以让模型创建或修改测试进行调试，但这类 observation 不能成为 official feedback；
最终 reward 由 grading 阶段 reset visible tests 并 apply hidden tests 后决定。
同时必须记录 test_tamper_suspicion 和 public_test_observation_trusted。
```

需要用户确认：是否允许模型在 rollout 中修改测试文件，但通过 grading reset 和 trust facts 防止 reward hacking。

### 决策 9：LLM monitor 是否进入 Stage 16G.3

选项 A：Stage 16G.3 只做 rule-based monitor。  
选项 B：Stage 16G.3 就实现最小 LLM monitor。  
选项 C：Stage 16G.3 只产出 monitor-ready facts，LLM monitor 放到 Stage 16G.5 / 16G.6。

我的建议：

```text
采用 A + C。
Stage 16G.3 必须有 rule-based monitor 和结构化事实；
LLM monitor 可以作为后续训练资格门禁增强，但不应阻塞 Bash 底座。
```

需要用户确认：是否接受 Stage 16G.3 暂不实现 LLM monitor，但保留字段和 artifact 给后续接入。

### 决策 10：是否增加 MAI-like `str_replace_editor` profile

选项 A：Stage 16G.3 只使用现有 `apply_patch` / `write_file` / `edit_file`。  
选项 B：Stage 16G.3 同时新增 `str_replace_editor` 兼容工具。  
选项 C：先在文档和 profile 中预留，后续做 schema mixing。

我的建议：

```text
采用 C。
现有结构化文件修改链路刚在 16G.2 打通，不应在 16G.3 同时大改编辑工具；
但正式计划应承认 MAI-like profile 后续需要 bash + str_replace_editor 的工具表面对齐实验。
```

需要用户确认：是否把 `str_replace_editor` 明确列入后续 profile，而不阻塞 Stage 16G.3。

### 决策 11：Bash 是否允许写仓库源码和测试文件

选项 A：Bash 只能写 `/tmp` 或明确 scratch 目录，不能写仓库 tracked files。源码修改必须通过 `apply_patch` / `write_file` / `edit_file`。  
选项 B：Bash 可以写仓库 tracked files，但这些写入必须被检测为 `bash_workspace_mutation`，默认不具备进入 policy loss 的资格。  
选项 C：Bash 可以像真实终端一样写仓库文件，最终 patch 捕获全部 diff，只通过 final patch hygiene 和 verifier 判断。

我的建议：

```text
Stage 16G.3 默认采用 B。
Bash 表面保持真实，允许模型在 episode workspace 内产生文件系统副作用；
但所有对 tracked source / tests / config 的 Bash 写入都必须被检测和归因。
结构化编辑工具仍然是推荐和训练优先的源码修改路径。
包含 bash_workspace_mutation 的轨迹在 Stage 16G.3 不进入 policy loss；
是否允许后续进入训练，由 Stage 16G.6 / 17B 决定。
```

这样不会把 Bash 再次收窄成 toy shell，也不会让执行 agent 默默绕过结构化编辑工具和 patch provenance。正式计划还需要定义：

```text
bash_created_scratch_file_paths
bash_modified_tracked_source_paths
bash_modified_test_paths
bash_workspace_mutation_detected
structured_edit_required_for_policy_loss
```

需要用户确认：是否接受 Stage 16G.3 中 Bash 可以产生仓库写入，但这些写入默认导致训练资格保持关闭或进入 quarantine，直到后续阶段另行放行。

### 决策 12：最终 verifier 是否必须 clean checkout replay

选项 A：最终 verifier 在 rollout 容器中原地运行。  
选项 B：最终 verifier 在 rollout 容器中运行，但先 reset tests 和清理临时文件。  
选项 C：最终 verifier 在 grader-only clean checkout 中 replay cleaned final.patch，然后 reset visible tests、apply hidden tests 并运行 verifier。

我的建议：

```text
采用 C。
宽 Bash 会让 rollout 容器产生大量合法但不应影响 reward 的副作用。
最终 reward 必须只评估 cleaned final.patch 在干净环境中的行为。
```

需要用户确认：正式计划是否把 clean checkout replay cleaned final.patch 作为宽 Bash 的硬门槛。

## 5. 建议写入正式计划的硬门槛

下面这些建议作为 Stage 16G.3 正式执行计划中的 hard gates。

### 5.1 宽 Bash 暴露门槛

只有同时满足下面条件，`bash(command)` 或 bash-like `run_public_command(command)` 才能进入 `swe_public_core`：

```text
fresh isolated execution environment per episode
read_file / grep / glob / apply_patch / write_file / edit_file / bash 操作同一个 episode workspace
默认 network=none
没有 host path、run_dir、runtime-private、hidden verifier、gold patch、test patch 挂载
容器内无 secrets
CPU / memory / process count / file count / disk write / wall-clock / stdout-stderr byte limits 有机器事实
stdout/stderr/exit_code/duration/timeout/truncation 全记录
sanitized artifact 与 raw restricted artifact 分层
TrainingView 中工具 observation mask=0
tracked source / tests / config 的 Bash 写入可检测和归因
final patch hygiene 能排除缓存、临时文件、构建产物和 runtime-private 路径
grading 前 reset visible tests
hidden tests 只在 grading 阶段 apply
final verifier 在 grader-only clean checkout 中 replay cleaned final.patch
git future history 不可见，或宽 Bash core gate 失败
rule-based reward hacking monitor 可用
```

### 5.2 本机进程 fallback 禁止伪装完成

如果实现只能使用普通 `local_process` 或无法证明隔离的 `workspace_adapter.run_command`，必须写入：

```text
core_profile_exposure_allowed=false
network_isolation_proven=false
host_path_isolation_proven=false
runtime_private_visibility_proven=false
```

这种状态只能算 schema / planned evidence，不能算 Stage 16G.3 训练可用。

### 5.3 hidden verifier 不可见

无论 Bash 多宽，rollout 阶段都不能看到：

```text
hidden verifier
gold patch
test patch
official expected outcomes
runtime-private raw artifacts
grading-only scripts
host absolute paths
```

### 5.4 训练资格不在 16G.3 放开

Stage 16G.3 只产出：

```text
tool event
sanitized observation
artifact manifest
monitor facts
test trust facts
eligibility facts
TrainingView projection
```

正式 policy loss 放行仍然等待 Stage 16G.5 / 16G.6 / 17B。

正式验收建议固定这些字段：

```text
policy_loss_candidate=false
formal_online_rl_eligible=false
stage17b_real_data_freeze_allowed=false
stage20_warm_start_data_generation_allowed=false
stage21_formal_rl_allowed=false
external_provider_policy_loss_candidate=false
```

即使外部 provider 轨迹包含 Bash 工具事件，也不能因为 Stage 16G.3 增强了工具面而自动进入 policy loss。

### 5.5 artifact 机器可验收字段

正式计划建议固定下面这些 artifact 字段，避免只用自然语言描述“raw artifact 不可见”：

```text
sanitized_model_readable_ref
raw_restricted_audit_ref
artifact_visibility
artifact_kind
source_tool_call_id
truncation_policy
read_tool_result_artifact_allowed
raw_ref_read_denied
sha256
```

至少需要 probe：

```text
模型可以分页读取 sanitized artifact
模型读取 raw artifact ref 被拒绝
sanitized artifact 中没有 host path / run_dir / runtime-private marker
超长 stdout / stderr 被截断并有 artifact 指针
```

### 5.6 宽 Bash 验收 probe

正式计划建议至少包含下面这些 probe：

```text
网络命令被环境拒绝
Python socket 网络访问失败
hidden verifier 路径不可见
runtime-private 路径不可见
host absolute path 不泄漏
future git object / ref / reflog 不可见
测试文件修改被标记
测试框架 monkey patch 可疑行为被标记
raw artifact ref 读取被拒绝
超长输出截断和 artifact 分层可检查
/tmp 临时脚本不进入 cleaned final.patch
Bash 修改 tracked source 后 bash_workspace_mutation_detected=true
final verifier 使用 clean checkout replay cleaned final.patch
资源限制触发时返回明确 timeout/resource_limit fact
```

## 6. 对现有文档的预期修改

如果用户确认本草案方向，正式重写时需要做这些同步：

1. `55-stage-16g-3-execution-plan.md`：全面重写阶段定位、子阶段拆分和工具面。
2. `repo_harness_verl_harness_capability_acceptance_map.html`：把 `run_project_test` 从默认模型可见目标改为内部测试路由能力；把 `bash_or_public_command_execution` 改为 SEE-gated Bash。
3. `repo_harness_verl_stage16g_4way_tool_comparison.html`：修正四方对比中 RepoHarness 16G.3 的目标表面，强调 `bash(command)` + 内部 monitor，而不是 `run_project_test(test_profile_id, selector)`。
4. `16G-3_plan_V1.md`：保留“命令字符串 + 内部测试路由”的正确部分，但把 CommandStringV1 从最终主边界降级为 transitional / monitor 方案。
5. `bash_tool_advice.md`：可作为正式计划的外部依据摘要，不需要直接改。

## 7. 当前建议结论

我建议正式 Stage 16G.3 计划采用下面这组默认结论：

```text
1. Stage 16G.3 的目标从“窄公开命令工具”升级为“SEE-gated Bash 工具面”。
2. 模型可见主命令工具最终命名为 bash(command: string)，或短期 run_public_command(command: string) 兼容。
3. run_project_test 不进入 swe_public_core 默认模型工具面，只保留为内部 ProjectTestRouter / acceptance probe。
4. scratch_python 不作为最终 MAI-like core 的必需工具；仅作为 transitional 或 optional 能力。
5. 每条命令 disposable snapshot 不作为宽 Bash 主语义；正式 Bash 使用 per-episode persistent isolated container。
6. 宽 Bash 只有在 SEE-equivalent hard gates 满足后才允许进入 core。
7. 默认无网络，自由依赖安装不属于 Stage 16G.3 第一版。
8. git future-history scrub 是宽 Bash core 的硬门槛；未完成时不能只靠 monitor 放行。
9. public tests 可以在 rollout 中被模型作为诊断对象修改或新增，但不能成为 official feedback；grading 前必须 reset visible tests 并 apply hidden tests。
10. Stage 16G.3 先实现 rule-based reward-hacking monitor 和结构化事实，LLM monitor 后续接入。
11. 现有 apply_patch / write_file / edit_file 继续使用；str_replace_editor 作为后续 profile mixing 预留。
12. Bash 可以在 episode workspace 内产生文件系统副作用，但 tracked source / tests / config 写入必须被检测和归因。
13. 包含 Bash 写入 tracked files 的轨迹在 Stage 16G.3 默认不进入 policy loss，后续是否放行由 Stage 16G.6 / 17B 决定。
14. 最终 verifier 必须在 grader-only clean checkout 中 replay cleaned final.patch，不能继承 rollout 容器副作用。
15. 16G.3 不放开 policy loss，只产出工具事件、观察、artifact、monitor facts 和 eligibility facts。
```

这组结论如果被确认，正式计划应删除旧文档中下列主线：

```text
command_profile_id + structured args 作为主模型表面
pytest 命令被 run_public_command 拒绝并提示模型改用 run_project_test
run_project_test 是默认模型可见测试工具
scratch_python 是最终核心复现工具
每条 public command 默认 disposable snapshot
靠 CommandStringV1 allowlist 作为主要安全边界
```

## 8. 仍需用户确认的最小问题清单

为了进入正式重写，建议用户至少确认下面七个问题：

1. 是否同意 Stage 16G.3 的最终模型可见命令工具目标是 `bash(command: string)`，而不是 `run_project_test(...)` 或 `command_profile_id + args`。
2. 是否同意宽 Bash 必须以 per-episode SEE-equivalent Docker 容器为硬前提；如果当前 backend 做不到，就只能标记 planned / diagnostic，不能进入 `swe_public_core`。
3. 是否同意 `run_project_test` 降级为内部路由和 acceptance probe，不作为默认模型可见工具。
4. 是否同意 Stage 16G.3 正式计划从“每条命令 disposable snapshot”改成“每个 episode 一个持久隔离容器，最终 patch 和 grading 阶段做清洁投影与测试重置”。
5. 是否同意 `scratch_python` 不再作为最终 MAI-like core 的 P0 工具，而是作为过渡或可选工具。
6. 是否同意 Bash 可以在 episode workspace 内产生文件系统副作用，但对 tracked source / tests / config 的写入必须被检测、归因，并且 Stage 16G.3 默认不进入 policy loss。
7. 是否同意最终 verifier 必须在 grader-only clean checkout 中 replay cleaned final.patch，而不是在 rollout 容器中原地运行。

如果这七点确认，正式 `55-stage-16g-3-execution-plan.md` 就可以围绕 SEE-gated Bash 重新编写。
