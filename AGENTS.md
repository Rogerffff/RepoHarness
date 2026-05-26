# RepoHarness Agent Guide

所有编写的文档或者注释，除了必要的专业词汇、命令名称、文件名、字段名和代码标识符之外，都使用清晰、详细、通俗易懂的中文。如果解释一个容易混淆的概念，尽量搭配具体数值、文件路径、命令或者实现例子。

## 项目一句话定位

RepoHarness 是一个面向软件工程智能体训练和评测的 Harness，目标是让真实或半真实仓库任务产生可执行、可审计、可导出的训练轨迹。核心闭环是：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

它不是 Claude Code、Cursor、OpenHands、SWE-agent 或官方 SWE-Bench harness 的复刻；也不要把它描述成生产级安全沙箱、分布式 rollout 服务、公开榜单系统、完整产品复刻或已经训练出模型的项目。



## 仓库结构速览

- `src/repo_harness/`：RepoHarness Python 主实现。
  - `cli/`：`repo-harness` 命令行入口。
  - `workspace/`：local process 和 Docker-based executable repository environment。
  - `model/`：replay、mock 和 provider client 抽象。
  - `tools.py`、`agent_loop.py`、`eval_runner.py`、`training_export.py`：V1/V2 核心闭环相关模块。
  - `v3_*`：V3 Docker backend、repository-level task、SWE-Bench-like fixed subset、export audit 和 acceptance 相关模块。
  - `v4_*`：V4 implementation inputs、task freeze、rollout、tool lifecycle、agent run integration、export quality、cards 和 acceptance 相关模块。
- `tests/`：单元测试、集成测试和 fixtures。V4 相关测试主要在 `tests/unit/test_v4_*.py`，V3 Docker 和 acceptance 相关测试在 `tests/integration/` 与 `tests/unit/test_v3_*.py`。
- `docs/`：核心设计文档、版本文档、实现日志、审查记录和验收记录。
- `docs/v1/` 到 `docs/v5/`：各版本范围、实施计划、实现日志、review、evidence、walkthrough、final acceptance 或下一版本范围设计。
- `runs/`：本地运行产物和 acceptance evidence。不要默认读取 latest run，所有 inspect 和 acceptance builder 都应显式传入路径。
- `reference/claude-code-docs/`：Claude Code 架构分析资料。
- `reference/claude-code-typescript-src/`：Claude Code TypeScript 参考源码。该目录只作为设计参考，不是 RepoHarness 主实现的一部分；其中 `AGENTS.md` 是参考源码导航。

## 当前 agentic RL / verl 工作流背景

本工作树现在不只是早期 V1-V5 harness 原型，还包含一条更长的 agentic RL 训练链路：

```text
RepoHarness task
-> run_episode(real_episode)
-> RepoHarnessEpisodeResult
-> TrainingView / GenerationRecord / formal online RL gate
-> repo_harness_verl bridge
-> verl fully async rollout / MessageQueue / trainer smoke
```

重要阶段状态：

- Stage 13 到 Stage 15：已经打通 RepoHarness 到 verl fully async 的本地桥接、远端 smoke、partial checkpoint / 同进程 resume 原型和 partial rollout 远端 smoke。
- Stage 16A 到 Stage 16E：围绕正式训练工具面、diagnostic shell、公开环境提示、official verifier healthcheck 和 patch hygiene 做了多轮加固。
- Stage 16F：把测评入口从旧 `run_task(...)` 收敛到新的 `run-episode-task` / `run_episode(real_episode)` 统一入口，并把旧入口标记为 legacy compatibility。
- Stage 16F.6 / 16F.7：已经用真实外部 provider 做过小规模 `run-episode-task` smoke，并补了 provider attempt / error accounting。外部 provider 轨迹默认不能进入 policy loss，因为缺少 verl 训练路径需要的 token / logprob provenance。

当前训练 worktree 的关键事实来源：

- `src/repo_harness/rl/runtime.py`：`RepoHarnessRuntime.run_episode(...)`、`start_episode(...)`、`LLMGatewayModelClientAdapter`、formal result 构造和 real episode runtime。
- `src/repo_harness/execution/spec.py`、`src/repo_harness/execution/builder.py`：`EpisodeExecutionSpec` 和任务 / verifier / tool / budget / feedback 策略绑定。
- `src/repo_harness/evaluation/episode_runner.py`：`run-episode-task` 的执行入口、provider diagnostics、projection 输入。
- `src/repo_harness/evaluation/episode_projection.py`：新入口到旧评测 / export 可读 projection 的绑定。
- `src/repo_harness/evaluation/entrypoint_policy.py`：旧 `run_task(...)` 与新 `run-episode-task` 的训练资格策略。
- `src/repo_harness/evaluation/episode_parity.py`：旧入口和新入口的小规模 parity audit。
- `src/repo_harness/workspace/patch_hygiene.py`：`final.patch` / `final.diff` 清洁投影、过滤目录、runtime-private 路径和 public-safe hygiene report。
- `src/repo_harness/workspace/diagnostic_session.py`、`src/repo_harness/workspace/docker_adapter.py`、`src/repo_harness/workspace/adapter.py`：Stage 16B diagnostic shell、Docker / local backend session 和 projection writeback。
- `src/repo_harness/tasks/command_policy.py`：Stage 16A 的安全最小 `execute_bash` 策略。它是正式训练 shell 的保守 baseline，不应被误读成完整 Claude Code Bash 能力。
- `src/repo_harness/tools/minimal.py`：模型可见工具 registry、`execute_bash`、`diagnostic_shell`、`run_tests` 等工具实现入口。

## 两个 worktree 的并行协作

现在有两个长期并行工作树：

```text
training_worktree:
  当前仓库，public label 为 training_worktree
  负责 verl / RL 训练链路、formal gates、数据 schema、reward、export、远端训练 smoke。

evaluation_worktree:
  相邻评测仓库，public label 为 evaluation_worktree
  负责 SWE-Bench / 强模型真实任务测评、harness 能力诊断、score gap 排查和评测驱动修复。
```

协作原则：

1. 两个 worktree 不能长期分叉出不同 harness 语义。评测 worktree 发现的共享链路 bugfix，应及时同步回 training worktree。
2. 训练 worktree 当前以 `run-episode-task` / `run_episode(real_episode)` 为 canonical 新入口；旧 `run_task(...)` 只保留 legacy compatibility，不应作为新训练数据默认事实来源。
3. evaluation worktree 仍会继续发现工具能力、public test、diagnostic shell、provider accounting、patch hygiene 等问题。若修复影响共享 harness 行为，不应只留在 evaluation worktree。
4. 未通过代表性 Stage 16.5 harness 诊断前，不应贸然冻结真实 Stage 17 数据 split、生产 Stage 20 warm-start 数据或启动 Stage 21 RL 训练。

常见同步背景文档：

- `docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md`
- `docs/agentic_RL/training_design/stage16f_unified_baseline_handoff_to_evaluation_agent.md`
- evaluation worktree 中的 `docs/resume/stage16_5_execution_plan.md`
- evaluation worktree 中的 `docs/resume/repo_harness_vs_claude_code_capability_gap_analysis.md`

公开文档不要写入真实本机绝对路径。需要引用另一个 worktree 时，使用 `source_worktree_label`、`source_commit`、`source_doc_sha256`、`opaque_ref` 这类 public-safe 字段；真实路径只应留在不提交的 runtime-private 报告里。

## 当前紧急任务：Stage 16G.0

当前不要直接进入 Stage 17A 数据 registry。紧急任务是 Stage 16G.0：盘点 RepoHarness 与 Claude Code / mini-SWE-agent / 其他真实 SWE harness 的工具能力差距。

核心问题：

```text
如果 RepoHarness 的工具能力弱到连只给 Bash 的 mini-SWE-agent 都不如，
那么在这个 harness 里做强化学习可能会训练出错误能力。

目标不是简单放开完整 shell，
而是判断正式训练工具面是否足够接近 Claude Code 类真实软件工程 agent 的工作方式。
```

Stage 16G.0 是 inventory / gap analysis 阶段，原则上不改模型可见工具、不放宽 `execute_bash`、不修改 `run_episode(...)` 行为、不启动训练。它应该产出能力矩阵、风险报告和后续 Stage 16G.1+ 的改造建议。

新接手 agent 必读：

- `docs/agentic_RL/repo_harness_verl_workstreams/49-stage-16g-0-execution-plan.md`
- `reference/claude-code-typescript-src/AGENTS.md`
- `docs/harness_improve/gpt_advice.md`
- evaluation worktree 的 `docs/resume/repo_harness_vs_claude_code_capability_gap_analysis.md`
- `docs/agentic_RL/training_design/post_stage15_training_infra_stage_plan.md`
- `docs/agentic_RL/training_design/stage16f_unified_baseline_handoff_to_evaluation_agent.md`

审查 Stage 16G.0 时，请重点检查这些能力是否被覆盖：

- Claude Code 风格的 `Read` / `Grep` / `Glob` / `Edit` / `Write` / `Bash` 分层，而不是只看一个 Bash。
- RepoHarness 的 scaffold 工具集合与实际 executor registry 是否一致。
- `execute_bash`、`diagnostic_shell`、未来可能的 `run_public_command(...)` 的边界和训练资格。
- public test routing、scratch Python / reproduction script、project command routing、dependency setup。
- 文件查看分页、大文件处理、symbol search、artifact 回读、任务管理、子代理 / plugin / skill 的 schema 预留。
- 权限拒绝是否给模型可学习的恢复路径，而不是只让模型少用工具。
- hidden verifier、gold patch、test patch、Git history、runtime-private、共享依赖环境和本机路径的防泄漏边界。

Stage 16G.0 通过后，也不等于可以立刻大规模训练。它只应回答：下一步应该怎样把 harness 能力向 Claude Code 类真实工具环境靠拢，同时仍保持训练数据和 verifier 边界安全。

## 核心设计文档索引

建议先读：

- `docs/00-reading-guide.md`：阅读路径和当前文档定位。
- `docs/01-project-positioning-and-requirements.md`：项目定位、边界和版本进度。
- `docs/02-system-architecture.md`：系统分层、模块职责和对象流。
- `docs/11-object-model-config-and-data-flow.md`：对象模型、配置字段、模块所有权和端到端数据流。

按模块深入：

- `docs/03-agent-loop-and-message-protocol.md`：agent loop、message protocol、tool call / tool result 配对。
- `docs/04-tool-system-and-orchestration.md`：工具契约、工具执行顺序、并发和权限交互。
- `docs/05-workspace-sandbox-and-permissions.md`：workspace boundary、permission 与 Docker execution mode 的边界。
- `docs/06-task-dataset-and-environment-adapters.md`：任务 schema、task adapter、baseline 和 dependency state。
- `docs/07-verifier-reward-and-evaluation.md`：verifier、accepted policy、reward metadata 和评测指标。
- `docs/08-trajectory-store-and-training-export.md`：RunRecorder、transcript、events、artifact manifest 和 export schema。
- `docs/09-agent-scaffolds-and-multi-agent.md`：scaffold 和多角色 agent 边界。
- `docs/10-context-session-and-failure-diagnostics.md`：context management、resume、budget 和 failure diagnostics。
- `docs/12-resume-narrative-and-demo-artifacts.md`：项目展示、简历叙事和 demo artifact 边界。
- `docs/13-agentic-technical-report-reading-map.md`：对照工业界 agentic training 技术报告的阅读地图。

## 版本文档索引

- `docs/v1/`：V1 micro-repo 最小闭环、实现日志、review、walkthrough 和 final acceptance。
- `docs/v2/`：V2 范围、实施计划、实现日志、review、provider / export / acceptance 增强和 final acceptance。
- `docs/v3/`：V3 repository-level harness、Docker backend、固定 SWE-Bench-like 子集、context compaction、export audit、acceptance bundle 和 final acceptance。
- `docs/v4/`：V4 task freeze、rollout orchestration、tool lifecycle audit、agent run integration、export quality、cards、implementation review 和 final acceptance。
- `docs/v5/`：V5 scope 和 review，目标是补齐最终简历和大厂面试所需的结果包。



常用复核命令：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json --assert-immutable
```
