# RepoHarness Agent Guide

所有编写的文档或者注释，除了必要的专业词汇、命令名称、文件名、字段名和代码标识符之外，都使用清晰、详细、通俗易懂的中文。如果解释一个容易混淆的概念，尽量搭配具体数值、文件路径、命令或者实现例子。

## 项目一句话定位

RepoHarness 是一个面向软件工程智能体训练和评测的 Harness，目标是让真实或半真实仓库任务产生可执行、可审计、可导出的训练轨迹。核心闭环是：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

它不是 Claude Code、Cursor、OpenHands、SWE-agent 或官方 SWE-Bench harness 的复刻；也不要把它描述成生产级安全沙箱、分布式 rollout 服务、公开榜单系统、完整产品复刻或已经训练出模型的项目。

## 当前实现状态

截至 2026-05-05 本轮复核时，V4 implementation 的阶段提交包括：

- V4 Stage 0：冻结 V4 implementation inputs。
- V4 Stage 1：增加 V4 schema 和 inspect skeleton。
- V4 Stage 2：`021dde7 feat: add V4 task freeze integration`
- V4 Stage 3：`40992d9 feat: add V4 rollout orchestration`
- V4 Stage 4：`e985b3e feat: add V4 tool lifecycle audit`
- V4 Stage 5：`89cf86e feat: add V4 agent run integration`
- V4 Stage 6：`fe96dec feat: add V4 export quality audit`
- V4 Stage 7：`f15ed67 feat: add V4 cards evidence`
- V4 Stage 8：`35f76c0 feat: complete V4 final acceptance`

截至 2026-05-05，V4 已完成复核问题修复并重新生成验收证据。最新 V4 closure commit 为 `e0da89c test: refresh V4 acceptance evidence after hardening`，完整测试结果为 `712 passed`，V4 acceptance report 和 acceptance bundle immutable inspect 均已通过。本轮文档同步后，新增 `runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json`，用于绑定当前版本的 `docs/v4/final-acceptance.md` 和 `docs/v4/walkthrough.md`。后续 agent 可以把当前 V4 描述为“已通过修复后最终验收”，但仍不能把 RepoHarness 描述成完整 SWE-Bench 复现、公开榜单系统、生产级安全沙箱或已经训练出模型的项目。

上一轮 V4 复核发现的污染 denylist 哈希、final verifier boundary、preference pair 可比较性、structured reward allowlist、独立 regression evidence、implementation log index、final command log 绑定和 reward audit schema 等问题，已经通过后续修复提交和 `runs/v4-final-rerun-20260504T194758Z/` 下的最新 acceptance evidence 收口。引用 V4 最新状态时，以 `194758Z` 目录为准；`runs/v4-final-rerun-20260504T162105Z/` 只作为历史验收目录。

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

V4 当前最重要的入口：

- `docs/v4/scope-and-roadmap.md`
- `docs/v4/implementation-plan.md`
- `docs/v4/review/implementation-plan-review.md`
- `docs/v4/final-acceptance.md`
- `docs/v4/walkthrough.md`
- `docs/v4/review/implementation/08-final-acceptance-review.md`

注意：`docs/v4/final-acceptance.md` 和 `docs/v4/walkthrough.md` 已同步到修复后的最新 V4 验收路径。若看到 `runs/v4-final-rerun-20260504T162105Z/`，应理解为历史验收目录；当前 V4 closure baseline 是 `runs/v4-final-rerun-20260504T194758Z/`。

## 最新关键运行产物

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

## 工作规则

- 修改前先用 `rg` 或 `rg --files` 定位文件，不要凭记忆改。
- 工作区可能有和当前任务无关的既有改动；不要删除、回滚或提交不属于当前任务的文件。
- 所有 inspect 命令都应显式传入输入路径，不要扫描 latest run 或依赖当前目录猜测。
- 涉及 V4 结论时，要以 `runs/v4-final-rerun-20260504T194758Z/` 下的 acceptance inputs、acceptance report、文档同步后的 acceptance bundle 和对应 final command log 为准。
- Docker execution mode 只能描述为 Docker-based executable repository environment，不能写成生产级安全沙箱。
- 参考 Claude Code TypeScript 源码时，只借鉴架构不变量，例如统一 query loop、tool contract、permission boundary、tool result 回流、context compaction 和 transcript diagnostics；不要照搬产品代码或把参考项目当成 RepoHarness 的运行依赖。
