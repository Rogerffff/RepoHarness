# RepoHarness

RepoHarness 是一个面向软件工程智能体训练和评测的 Harness。它的核心目标是把真实或半真实仓库任务转化为**可执行、可审计、可导出**的训练轨迹：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

这个项目不是 Claude Code、Cursor、OpenHands、SWE-agent 或官方 SWE-Bench harness 的复刻，也不把公开榜单复现、生产级安全沙箱、分布式训练系统或已经训练出模型作为当前交付目标。RepoHarness 更关注训练数据生产链路本身：任务冻结、工具调用协议、执行边界、轨迹记录、最终验证器、reward metadata、训练导出和验收证据能不能被机器复核。

## 当前定位

RepoHarness 当前已经从最小本地闭环推进到 repository-level evaluation harness：

- V1：跑通本地 micro-repo task 的最小闭环，覆盖 task adapter、workspace adapter、tool system、agent loop、trajectory store、verifier、reward metadata 和基础训练导出。
- V2：扩展 run metadata、导出审计、多 rollout、scaffold registry、mock provider、DeepSeek 主 provider、OpenAI fallback provider、20 个任务级 fixture，以及 V2 final acceptance。
- V3：交付 Docker-based executable repository environment、真实 repository-level task、固定 SWE-Bench-like 小子集、source materialization、fail-to-pass / pass-to-pass final verifier、context compaction、experiment resume、export audit 和 acceptance bundle。
- V4：在 V3 基础上增加 task source freeze、单机 rollout orchestration、resource lock、checkpoint state、tool lifecycle audit、agent run integration、trajectory store 字段级检查、export quality audit、reward / preference pair 审计、dataset / run / export cards 和 final acceptance machinery。

截至 2026-05-05，V4 已完成复核问题修复并重新生成验收证据。最新 V4 closure commit 为 `e0da89c test: refresh V4 acceptance evidence after hardening`，完整测试结果为 `712 passed`，V4 acceptance report 和 acceptance bundle immutable inspect 均已通过。本轮文档同步后，又在同一验收目录下生成了 `acceptance_bundle_manifest_doc_sync_20260505T075410Z.json`，用于绑定当前版本的 `docs/v4/final-acceptance.md` 和 `docs/v4/walkthrough.md`。对外介绍时可以说“V4 已经通过修复后最终验收”，但仍不要把 RepoHarness 描述成完整 SWE-Bench 复现、公开榜单系统、生产级安全沙箱或已经训练出模型的项目。

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

复核当前关键验收产物：

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

- `docs/00-reading-guide.md`：项目文档阅读顺序。
- `docs/01-project-positioning-and-requirements.md` 到 `docs/12-resume-narrative-and-demo-artifacts.md`：核心设计文档。
- `docs/13-agentic-technical-report-reading-map.md`：对照工业界 agentic training 技术报告的阅读地图。
- `docs/v1/`：V1 实施计划、验收记录和 walkthrough。
- `docs/v2/`：V2 范围、实施计划、实现日志、审查记录和最终验收。
- `docs/v3/`：V3 repository-level harness、Docker backend、SWE-Bench-like 固定子集和最终验收。
- `docs/v4/`：V4 范围、实施计划、实现日志、审查记录、evidence、cards、walkthrough 和 final acceptance。
- `docs/v5/`：V5 范围设计和 review，目标是补齐最终简历和面试所需的结果包。
- `reference/claude-code-typescript-src/`：Claude Code TypeScript 参考源码；其中 `AGENTS.md` 是参考项目结构导航。

注意：`runs/v4-final-rerun-20260504T162105Z/` 是 V4 早期最终验收目录，已经被后续修复后的 `runs/v4-final-rerun-20260504T194758Z/` 取代。引用 V4 最新结论时，应使用 `194758Z` 目录下的 acceptance inputs、acceptance report、文档同步后的 acceptance bundle 和对应 final acceptance command log。

## 边界提醒

RepoHarness 当前适合用于训练轨迹生产链路、评测协议、导出审计和验收证据的工程研究。它不等同于生产级安全沙箱、完整远程多代理产品、完整公开榜单基础设施或新的强化学习算法。涉及 V4 结论时，请使用修复后最新 acceptance 产物：`runs/v4-final-rerun-20260504T194758Z/`。
