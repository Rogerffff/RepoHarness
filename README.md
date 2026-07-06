# RepoHarness

RepoHarness 是一个面向软件工程智能体训练和评测的 Harness。它的核心目标是把真实或半真实仓库任务转化为**可执行、可审计、可导出**的训练轨迹：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

这个项目不是 Claude Code、Cursor、OpenHands、SWE-agent、Codex 或官方 SWE-Bench harness 的复刻，也不把公开榜单复现、生产级安全沙箱、分布式训练系统或已经训练出模型作为当前交付目标。RepoHarness 更关注训练数据生产链路本身：任务冻结、工具调用协议、执行边界、轨迹记录、最终验证器、reward metadata、训练导出和验收证据能不能被机器复核。

> ## 📍 最新进度（2026-07：项目已转入 rh2 新架构）
>
> **2026-07 重大转折**：项目重新定位为"**verifiers v1 基座之上的 SWE agent RL 安全与训练治理层 + 环境生产线**"，绿地重写（rh2），旧白盒单体（`src/repo_harness/`，Stage 13 ~ 16G.2C 的成果）冻结为 legacy；16G.3 ~ 16G.6 不再执行，旧 17B/20/21 闸门作废。README 下方的"当前定位 / 已实现的主要功能"反映的是**冻结前旧架构**的状态，仅作历史快照。
>
> **当前位置与完整导航都在 [AGENTS.md](AGENTS.md)**（进度章节 + rh2 必读清单）。当前任务：**rh2 S0 可行性验证**，执行计划见 [docs/agentic_RL/repo_harness_rh2_workstreams/01-s0-execution-plan.md](docs/agentic_RL/repo_harness_rh2_workstreams/01-s0-execution-plan.md)。
>
> 三份定案文档：[设计文档 2](docs/harness_improve/repo_harness_design_doc2_verifiers_based.md)（架构）· [实施前最终检查](docs/harness_improve/repo_harness_final_review_before_implementation.md)（范围与决策）· [实施计划总纲](docs/harness_improve/repo_harness_implementation_plan_v1.md)（S0~S5）。

## 当前定位（V4 时点快照，已被 16G 系列扩展）

RepoHarness 当前已经从最小本地闭环推进到 repository-level evaluation harness：

- V1：跑通本地 micro-repo task 的最小闭环，覆盖 task adapter、workspace adapter、tool system、agent loop、trajectory store、verifier、reward metadata 和基础训练导出。
- V2：扩展 run metadata、导出审计、多 rollout、scaffold registry、mock provider、DeepSeek 主 provider、OpenAI fallback provider、20 个任务级 fixture，以及 V2 final acceptance。
- V3：交付 Docker-based executable repository environment、真实 repository-level task、固定 SWE-Bench-like 小子集、source materialization、fail-to-pass / pass-to-pass final verifier、context compaction、experiment resume、export audit 和 acceptance bundle。
- V4：在 V3 基础上增加 task source freeze、单机 rollout orchestration、resource lock、checkpoint state、tool lifecycle audit、agent run integration、trajectory store 字段级检查、export quality audit、reward / preference pair 审计、dataset / run / export cards 和 final acceptance machinery。

截至 2026-05-05，V4 已完成复核问题修复并重新生成验收证据。最新 V4 closure commit 为 `e0da89c test: refresh V4 acceptance evidence after hardening`，完整测试结果为 `712 passed`，V4 acceptance report 和 acceptance bundle immutable inspect 均已通过。本轮文档同步后，又在同一验收目录下生成了 `acceptance_bundle_manifest_doc_sync_20260505T075410Z.json`，用于绑定当前版本的 `docs/v4/final-acceptance.md` 和 `docs/v4/walkthrough.md`。对外介绍时可以说"V4 已经通过修复后最终验收"，但仍不要把 RepoHarness 描述成完整 SWE-Bench 复现、公开榜单系统、生产级安全沙箱或已经训练出模型的项目。

**V4 之后的扩展**（详见 [AGENTS.md](AGENTS.md)）：V4 提供的是评测时点的 harness 基础闭环；V5 之后，项目重心转向 **agentic RL / verl 训练桥接**：
- Stage 13 / 14 / 15：打通 RepoHarness ↔ verl fully async 本地桥接和远端 smoke
- Stage 16A ~ 16F：围绕正式训练工具面、diagnostic shell、公开环境提示、verifier healthcheck、patch hygiene 做了 12 轮加固，并把测评入口统一到 `run-episode-task` / `run_episode(real_episode)`
- Stage 16G.0 ~ 16G.2C：完成与 Claude Code / Codex / mini-SWE-agent 的 27 条能力差距盘点，建立 4 档 profile taxonomy（`safe_structured_only` / `swe_public_core` / `swe_public_extended` / `redteam_restricted`），实现 `write_file` / `apply_patch` / `delete_file` / `move_file` / `mkdir` 五件套共享原子语义，并打通 run_episode → 14 公开文件投影 linkage

## 已实现的主要功能

- 任务适配和任务冻结：把 YAML / JSON fixture、V2 / V3 / V4 任务集和固定源码输入转换为 RepoHarness 可执行任务，并区分 adapter-visible、evaluator-only 和 audit-only 数据。
- 工作区和执行边界：支持 local process 和 Docker-based executable repository environment；Docker 用于可复现执行，不宣称生产级安全隔离。
- 工具系统和权限系统：提供文件读取、搜索、编辑、创建、受控 shell、测试运行、diff 捕获等工具，并记录权限决策、工具生命周期和 hook / MCP 冻结事实。
- Agent Loop：支持 replay、mock 和真实 provider 路径，维护 tool call / tool result 配对、上下文构造、预算、停止原因和 final patch 冻结。
- Verifier / Reward：使用确定性 verifier 派生 accepted policy、reward metadata、failure diagnostics 和训练过滤信息。
- Trajectory Store：记录 `transcript.jsonl`、`events.jsonl`、artifact manifest、run metadata、final patch 或 no-patch fact，并为导出绑定 prepared messages、observation 和上下文修订。
- Training Export：导出监督微调、reinforcement learning rollout 和 preference pair 数据，并通过 audit report、skipped manifest、contamination scan 和 export quality 规则过滤不可训练样本。
- Acceptance：V2、V3、V4 都有机器可读 acceptance report 和 acceptance bundle，关键 inspect 命令必须显式读取输入路径，避免依赖 latest run。

## 快速开始

安装开发依赖：

```bash
python -m pip install -e '.[dev]'
```

如果使用仓库内虚拟环境，常用命令建议加上：

```bash
PATH=.venv/bin:$PATH
```

运行基础验证：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

运行一个本地 replay 示例：

```bash
PATH=.venv/bin:$PATH repo-harness validate-task tests/fixtures/tasks/task_001.yaml

PATH=.venv/bin:$PATH repo-harness run-task \
  tests/fixtures/tasks/task_001.yaml \
  --config tests/fixtures/run_configs/replay_success.yaml \
  --output-dir runs/demo \
  --run-id demo-success

PATH=.venv/bin:$PATH repo-harness inspect-run runs/demo/demo-success
```

运行批量 replay 和训练导出：

```bash
PATH=.venv/bin:$PATH repo-harness run-batch \
  --config tests/fixtures/run_configs/batch_replay.yaml \
  --output-dir runs/demo-batch

PATH=.venv/bin:$PATH repo-harness export runs/demo-batch --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export runs/demo-batch --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness export runs/demo-batch --format preference_jsonl
```

复核当前关键验收产物（V1 ~ V4 历史 acceptance，仍可用）：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance \
  runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json \
  --assert-complete

PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance \
  runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json \
  --assert-complete

PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle \
  runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json \
  --assert-immutable

PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs \
  runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json \
  --assert-complete

PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance \
  runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json \
  --assert-complete

PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle \
  runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json \
  --assert-immutable
```

复核最新 Stage 16G 系列 acceptance（agentic RL 工作流）：

```bash
PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main \
  inspect-stage16g1-tool-profile \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_acceptance_summary.json \
  --assert-complete

PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main \
  inspect-stage16g2a-tool-surface \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/stage16g2a_acceptance_summary.json \
  --assert-complete

PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main \
  inspect-stage16g2b-file-mutation \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/stage16g2b_acceptance_summary.json \
  --assert-complete

PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main \
  inspect-stage16g2c-projection-linkage \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/stage16g2c_acceptance_summary.json \
  --assert-complete
```

## 关键运行产物

- V2 acceptance report：`runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json`
- V3 acceptance report：`runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json`
- V3 acceptance bundle：`runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json`
- V4 acceptance inputs：`runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json`
- V4 acceptance report：`runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json`
- V4 acceptance bundle，原始 implementation closure 版本：`runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest.json`
- V4 acceptance bundle，本轮文档同步后可复核版本：`runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json`
- V4 final acceptance command log，原始 implementation closure 版本：`runs/v4-final-rerun-20260504T194758Z/acceptance/final_acceptance_command_log.jsonl`
- V4 final acceptance command log，本轮文档同步版本：`runs/v4-final-rerun-20260504T194758Z/acceptance/final_acceptance_command_log_doc_sync_20260505T075410Z.jsonl`
- V4 pre-acceptance command log：`runs/v4-pre-acceptance-evidence-20260504T192620Z/pre_acceptance_command_log.jsonl`

## 推荐阅读

> **如果你是新接手的 agent 或开发者，请先读 [AGENTS.md](AGENTS.md)**。它有 rh2 最新进度与闸门、rh2 必读清单、接手前不要犯的 4 个判断，以及标注【legacy】的旧架构导览（5 道安全防线、4 档 profile、关键代码架构）。本节以下的"推荐阅读"条目均属冻结前旧架构快照。

V1 ~ V4 历史设计文档（仍准确，看模块前先看）：

- `docs/00-reading-guide.md`：项目文档阅读顺序。
- `docs/01-project-positioning-and-requirements.md` 到 `docs/12-resume-narrative-and-demo-artifacts.md`：核心设计文档。
- `docs/13-agentic-technical-report-reading-map.md`：对照工业界 agentic training 技术报告的阅读地图。
- `docs/v1/`：V1 实施计划、验收记录和 walkthrough。
- `docs/v2/`：V2 范围、实施计划、实现日志、审查记录和最终验收。
- `docs/v3/`：V3 repository-level harness、Docker backend、SWE-Bench-like 固定子集和最终验收。
- `docs/v4/`：V4 范围、实施计划、实现日志、审查记录、evidence、cards、walkthrough 和 final acceptance。
- `docs/v5/`：V5 范围设计和 review，目标是补齐最终简历和面试所需的结果包。

agentic RL / verl 训练桥接（V5 之后的主战场）：

- `docs/agentic_RL/`：阶段计划、阶段证据、HTML 报告、代码导览（[code_guide_index.html](docs/agentic_RL/code_guide_index.html)）、能力地图（[repo_harness_verl_harness_capability_acceptance_map.html](docs/agentic_RL/repo_harness_verl_harness_capability_acceptance_map.html)）、4-way 工具对比（[repo_harness_verl_stage16g_4way_tool_comparison.html](docs/agentic_RL/repo_harness_verl_stage16g_4way_tool_comparison.html)）等
- `docs/agentic_RL/repo_harness_verl_workstreams/`：旧 verl 线按编号 01 ~ 56 的执行计划 + shared_contracts/（已冻结；其中 16G.3 相关计划已废弃不再执行。rh2 执行计划在 `repo_harness_rh2_workstreams/`）
- `docs/agentic_RL/training_design/`：RL 算法设计、实验设计、worktree 同步契约、长链路 SWE Agent RL 落地研究
- `docs/harness_improve/`：外部 harness 设计参考（Codex / Claude Code / mini-SWE-agent / 微软 MAI-Thinking-1）和 gpt advice

外部参考源码（设计参考，不是 RepoHarness 实现的一部分）：

- `reference/claude-code-typescript-src/`：Claude Code TypeScript 参考源码；其中 `AGENTS.md` 是参考项目结构导航。
- `reference/codex/`：Codex 参考源码（codex-rs Rust 实现）；含其自己的 `AGENTS.md`。
- `reference/verl/`：verl 异步训练框架源码。

注意：`runs/v4-final-rerun-20260504T162105Z/` 是 V4 早期最终验收目录，已经被后续修复后的 `runs/v4-final-rerun-20260504T194758Z/` 取代。引用 V4 最新结论时，应使用 `194758Z` 目录下的 acceptance inputs、acceptance report、文档同步后的 acceptance bundle 和对应 final acceptance command log。

## 边界提醒

RepoHarness 当前适合用于训练轨迹生产链路、评测协议、导出审计和验收证据的工程研究。它不等同于生产级安全沙箱、完整远程多代理产品、完整公开榜单基础设施或新的强化学习算法。涉及 V4 结论时，请使用修复后最新 acceptance 产物：`runs/v4-final-rerun-20260504T194758Z/`。涉及 V5 之后最新状态（V5 / Stage 13 / 14 / 15 / 16A-G）时，以 [AGENTS.md](AGENTS.md) 和 `docs/agentic_RL/` 下最新阶段证据为准。
