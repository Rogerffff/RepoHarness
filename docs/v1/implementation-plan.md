# RepoHarness 第一版实现计划

## 0. 文档定位

这份文档用于把 `docs/00-reading-guide.md` 到 `docs/12-resume-narrative-and-demo-artifacts.md` 中的设计，转化为第一版可以直接执行的工程实现计划。

第一版的核心目标不是一次性做成完整产品，也不是复刻 Claude Code、Cursor、OpenHands 或 SWE-agent，而是先跑通一个面向训练和评测的最小闭环：

```text
任务定义 -> 可执行工作区 -> 工具调用 -> agent 多轮循环 -> 轨迹记录 -> 最终验证器 -> 奖励元数据 -> 评测指标 -> 训练导出
```

这份计划默认第一版先在单机环境中实现，优先使用本地进程执行模式。Docker-based executable repository environment 作为接口和后续增强保留，不作为第一版最小验收的硬性前置条件。

## 1. 趋势对齐和实现原则

近期 coding agent 技术报告和官方材料的共同趋势可以概括为：

- coding agent 训练和评测正在从单轮答案，转向可执行环境中的长轨迹任务。
- 训练环境和评测环境需要尽量一致，否则模型会学到无法在真实工具系统中复现的行为。
- 轨迹必须包含工具调用、环境反馈、测试输出、权限拒绝、失败原因和最终补丁，而不仅仅是最终回答。
- verifier，也就是验证器，必须成为训练奖励、离线评测和训练数据过滤的共同依据。
- 需要防止 reward hacking，也就是模型通过网络、Git 历史、未来提交、隐藏答案或测试环境漏洞取巧。
- 工业级 agent harness 的复杂能力很多，但第一版应该优先保证可复现性、结构化记录和安全边界，而不是优先实现界面、插件、远程多代理或流式工具执行。

这些趋势和本项目文档中的设计方向一致。实现时采用以下原则：

本计划只把这些外部材料作为趋势核对，不把它们当作 RepoHarness 已经实现能力的证据。核对时参考的公开材料包括：

- OpenAI Codex 官方介绍：https://openai.com/index/introducing-codex/
- OpenAI Codex cloud 文档：https://platform.openai.com/docs/codex
- Cursor Composer 2 technical report：https://cursor.com/blog/composer-2-technical-report/
- Qwen3-Coder-Next 官方博客：https://qwen.ai/blog?id=qwen3-coder-next
- Qwen3-Coder-Next arXiv technical report：https://arxiv.org/abs/2603.00729

- 先做可运行闭环，再做规模扩大。
- 先做 fake model 或 replay model，再接真实模型供应商。
- 先做本地进程工作区，再做 Docker 执行模式。
- 先做固定工具集合，再做动态工具发现、插件或 Model Context Protocol 工具。
- 先做单任务和顺序批量评测，再做并发批量评测。
- 先做监督微调和强化学习 rollout 导出，再做大规模 preference pair 批量构造。
- 所有模型可见内容和 evaluator-only metadata 必须隔离，尤其是 `gold_patch`、隐藏测试、baseline 原始日志和奖励元数据。

## 2. 第一版实现范围

### 2.1 第一版必须实现的能力

第一版必须实现以下能力，并以端到端验收为准：

1. 任务加载和校验
   - 支持 YAML 任务定义。
   - 支持 3 到 5 个自建 micro-repo task。
   - 校验任务字段、可见性、仓库来源、测试命令、超时配置、环境身份和 decontamination metadata。
   - 输出规范化后的 `TaskDefinition`、`RunnableTask` 和静态 `VerifierConfig`。

2. 运行配置
   - 支持 YAML `RunConfig`。
   - 支持模型配置、运行时预算、权限模式、执行模式、输出目录、上下文策略、评测策略和版本字段。
   - 批量评测中拒绝或降级 `ask` 权限模式，避免非交互运行卡住。

3. 工作区生命周期
   - 创建 run directory。
   - 创建 source checkout。
   - 创建 setup workspace。
   - 捕获 `dependency_state`，第一版至少支持 `none` 和 `rerun_setup`。
   - 运行 baseline verifier。
   - 创建 agent run workspace。
   - 建立 `agent_start_snapshot`。
   - Agent Loop 停止后，由 Eval Runner 协调冻结 `final.patch` 和 `final.diff`。
   - 创建 verification workspace。
   - 在 verification workspace 中应用 `final.patch` 并运行 formal final verifier。

4. 轨迹和 artifact 记录
   - 统一通过 `RunRecorder` 写入 `transcript.jsonl`、`events.jsonl` 和 `artifacts.json`。
   - 所有大输出都写入 artifact，模型上下文只放 preview 和 artifact 引用说明。
   - 每个 artifact 记录 `artifact_id`、相对路径、类型、哈希、大小、创建事件、脱敏状态和保留策略。
   - 失败运行也尽量生成 summary、metrics、events 和已产生的 artifacts。

5. 工具系统
   - 第一条端到端成功路径只依赖 `read_file`、`edit_file`、`run_tests` 和 `git_diff`，用于尽早验证纵向闭环。
   - 第一版完整模型可见工具集冻结为：
     - `list_files`
     - `read_file`
     - `grep`
     - `edit_file`
     - `create_file`
     - `bash`
     - `run_tests`
     - `git_diff`
   - 工具必须具备输入 schema、输入规范化、语义校验、权限检查、执行、结果映射、只读标记、并发安全标记和最大输出限制。
   - 未知工具、schema 校验失败、权限拒绝、超时、执行异常和中断都必须生成结构化 `ToolResult`。
   - `bash` 不作为第一条成功路径依赖。第一版只允许内置诊断命令和测试命令路由，不提供用户自定义复杂 shell 白名单。

6. 权限和命令安全
   - 支持 `plan`、`ask`、`auto`、`deny` 四种权限模式。
   - 第一版批量评测默认使用 `auto` 或 `deny`。
   - 所有路径必须限制在 agent run workspace 内。
   - 默认拒绝 `.git/`、`.env`、私钥、证书、认证文件和任务元数据等敏感路径。
   - 默认拒绝 `curl`、`wget`、`ssh`、`scp`、`git clone`、`git fetch`、`git pull`、`git remote add`、`sudo`、`rm -rf` 等风险命令。
   - 允许受限只读 Git 命令，例如 `git status`、`git diff`、`git log`、`git show` 和 `git ls-files`。
   - 如果 `bash` 请求的是任务测试命令或可识别 pytest 命令，默认路由到 `run_tests`。

7. Verifier、reward 和 metrics
   - 第一版实现 pytest verifier。
   - 支持 baseline verifier、feedback verifier 和 final verifier 三种 stage。
   - 支持测试用例级 `TestCaseResult`。
   - 支持 `fail_to_pass`、`pass_to_pass`、`pass_ratio`、`accepted` 和 `error_type`。
   - `accepted` 必须由确定性规则派生。
   - `RewardMetadata` 必须引用 final verifier、events 和 diff 统计。
   - `MetricsRecord` 必须统计 turn、tool calls、test runs、patch size、permission denial、invalid tool call、timeout、agent stop reason、final verifier status 和 run outcome。

8. Agent loop 和 fake model
   - 第一版先支持 fake model 或 replay model。
   - Agent loop 必须支持多轮 tool call -> tool result -> 下一轮模型调用。
   - 每个已解析的 `ToolCall` 必须有配对 `ToolResult`。
   - Agent Loop 只拥有 `agent_stop_reason` 和 loop 内部状态；`final_verifier_status`、`run_outcome` 和 `final_verifier_mode` 由 Eval Runner 在 Agent Loop 停止、patch 冻结和 final verifier 完成后派生。
   - 支持预算控制：最大轮数、最大工具调用次数、最大测试次数、单任务超时、命令超时和上下文预算。
   - 第一版硬性验收只要求 `simple_react` scaffold。`single_shot_patch` 可以作为内部测试或后续对比实验预留，`planner_coder_verifier` 推迟到第一版闭环稳定之后。

9. Context Builder 和 Context Manager
   - Context Builder 统一构造初始 system message 和 user task message。
   - Scaffold 只能提供 prompt fragment、允许工具策略、阶段策略和停止策略，不能绕过 Context Builder 直接拼完整初始消息。
   - Context Manager 在每次模型调用前生成 `PreparedMessages`，写入 provider-ready messages artifact 和 context event。
   - 第一版采用确定性 preview replacement，不实现复杂自动压缩。

10. 命令行接口和评测运行器
    - `repo-harness validate-task <task_path>`
    - `repo-harness run-task <task_path> --config <run_config> [--output-dir <dir>] [--run-id <id>]`
    - `repo-harness run-batch --config <run_config> [--output-dir <dir>]`
    - `repo-harness export <run_dir_or_runs_dir> --format <sft_jsonl|rl_jsonl|preference_jsonl>`
    - `repo-harness inspect-run <run_dir>`

11. 训练导出
    - 导出监督微调 JSONL。
    - 导出强化学习 rollout JSONL。
    - `preference_jsonl` 命令可以保留。第一版硬性验收不要求真实生成 preference pair；当同一任务没有足够多个 run 时，应稳定输出 skipped manifest 或 skipped reason。

### 2.2 第一版暂不实现的能力

以下能力不进入第一版最小验收：

- 真实模型供应商长轨迹评测。
- 大规模异步 rollout 集群。
- 完整 Docker execution mode 覆盖。
- 生产级安全沙箱。
- 操作系统级本地断网。
- 企业权限系统。
- 插件市场。
- Model Context Protocol 动态工具。
- 图形界面。
- 远程多代理平台。
- 长期后台子代理。
- 任意中间 turn 的 workspace resume。
- 完整 SWE-Bench 复现。
- 新强化学习算法。

第一版可以在接口和 schema 中为这些能力保留位置，但不能在 README、summary 或展示材料中声称已经完成。

## 3. 第一版技术选择

### 3.1 Python 和依赖

建议第一版使用：

- Python 3.11 及以上版本。
- Pydantic v2：用于任务、运行配置、事件、transcript、verifier 和 reward schema 校验。
- PyYAML：用于 YAML 任务和运行配置读取。
- pytest：用于项目自身测试和 micro-repo fixture 测试。
- 标准库 `argparse`：用于第一版命令行接口，避免过早引入复杂命令行框架。

第一版暂不强制引入：

- tiktoken。上下文预算先使用确定性的字符数估算，例如 `char4_token_estimator_v0`，并在 run metadata 中记录。
- Docker Python SDK。Docker 执行模式后续可以先通过 `docker` 命令行适配，再决定是否引入 SDK。
- rich、textual 或其他界面库。第一版以结构化文件和简洁命令行输出为主。

### 3.2 源代码目录

建议第一版按下列目录落地：

```text
src/repo_harness/
  agent_loop/
  cli/
  config/
  context/
  evaluation/
  export/
  model_client/
  permissions/
  reward/
  scaffolds/
  tasks/
  tools/
  trajectory/
  verifier/
  workspace/
```

建议测试和 fixture 目录：

```text
tests/
  unit/
  integration/
  fixtures/
    repos/
    tasks/
    run_configs/
```

第一版运行产物默认写入：

```text
runs/
```

`runs/`、临时 workspace、测试缓存、虚拟环境和其他生成产物必须保持在 `.gitignore` 中。

## 4. 实现顺序

第一版实现顺序采用“先纵向闭环，再横向补全”的方式。也就是说，不等所有工具、所有权限规则、完整上下文管理和全部导出能力都完成后才集成，而是在 schema、recorder、任务适配、工作区和 verifier 可用后，尽早插入一个最小端到端 replay 修复闭环。

最小纵向闭环只要求：

- 一个 micro-repo task。
- `ReplayModelClient`。
- 最小 `ContextBuilder`。
- 最小 `AgentLoop`。
- `read_file`、`edit_file`、`run_tests`、`git_diff` 四个工具。
- baseline verifier。
- strict patch replay final verifier。
- `transcript.jsonl`、`events.jsonl`、`artifacts.json`、`dependency_state.json`、`final.patch`、`final.diff`、`verifier.json`、`reward.json`、`metrics.json` 和 `summary.md`。

这个闭环跑通后，再补齐 `list_files`、`grep`、`create_file`、受限 `bash`、批量运行和训练导出。第一版工具执行默认串行，只保留并发安全字段；只读工具并发放到第一版之后。这样可以更早暴露对象模型、RunRecorder、Workspace Adapter、Verifier 和 Agent Loop 之间的接口错位。

### 阶段一：工程骨架、依赖和命令行空入口

目标：让项目具备可测试、可安装、可调用的最小工程骨架。

实现内容：

- 更新 `pyproject.toml`：
  - 增加 Pydantic v2、PyYAML 和 pytest。
  - 增加 `repo-harness` 命令行入口。
  - 增加基础测试配置。
- 创建模块目录和 `__init__.py`。
- 创建 `src/repo_harness/cli/main.py`。
- 先实现命令行空入口和帮助信息。
- 创建统一异常基类，例如 `RepoHarnessError`、`ConfigError`、`TaskValidationError`、`WorkspaceError`。

完成后审查：

- 命令行入口是否只做参数解析，不直接执行工具或解析测试日志。
- 包导入是否没有副作用。
- 新增依赖是否确实服务第一版闭环。
- 是否避免引入界面库、远程执行库或与第一版无关的重依赖。

完成后验证：

```bash
python -m repo_harness.cli.main --help
repo-harness --help
python -m pytest
```

验收标准：

- 两种命令行调用都能显示帮助。
- 测试命令能够运行。
- 包可以正常导入。

### 阶段二：核心 schema 和配置加载

目标：先把所有模块共享的数据结构固定下来，避免后续实现各自定义相似对象。

实现内容：

- 在 `config/` 实现 `RunConfig` 读取和校验。
- 在 `tasks/` 实现 `TaskDefinition`、`RunnableTask` 和 `VerifierConfig`。
- 在 `evaluation/` 实现 `BaselineResult` schema。`BaselineResult` 是正式 agent run 前的质量门控对象，由 Eval Runner 协调 Workspace Adapter 和 Verifier 生成；Task Adapter 不能生成或拥有 baseline 结果。
- 在 `evaluation/` 实现 `ResolvedVerifierPlan` schema。它由 Eval Runner 根据静态 `VerifierConfig` 和 `BaselineResult` 生成。
- 在 `verifier/` 实现 `TestCaseResult` 和 `VerifierResult` schema。
- 在 `workspace/` 实现 `ExecutionResult` schema。它由 Workspace Adapter 产生，供 Tool System 和 Verifier 消费。
- 在 `reward/` 实现 `RewardMetadata` schema。如果第一版暂时不单独建 `reward/` 包，也必须保持 Reward module 语义清晰，不能把 reward 计算塞进 verifier parser 内部。
- 在 `context/` 实现 `PreparedMessages`、`ContextReductionRecord`、`ContentReplacementState` 和 `ContentReplacementRecord` schema。
- 在 `trajectory/` 实现 `TranscriptRecord`、`TrajectoryEvent`、`ArtifactRef`、`RunSummary` 和 `MetricsRecord` schema。
- 在 `tools/` 实现 `ToolCall`、`ToolResult` 和工具输入输出基础类型。
- 在 `permissions/` 实现 `PermissionDecision` schema。
- 在 `model_client/` 实现 `ModelMessage`、`ModelResponse` 和 `ModelCallEvent` schema。
- 在 `workspace/` 实现 `DependencyState` 和 `RunWorkspace` schema。
- 在 `agent_loop/` 实现 `AgentLoopState`、`ToolPairingState` 和 agent loop 终止状态 schema；`AgentLoopState` 内部引用预算运行状态，但对象命名应和 `BudgetManager` 区分。
- 在 `budget/` 实现 `BudgetManager` schema 和预算状态对象，至少覆盖最大轮数、最大工具调用次数、最大测试次数、总 wall clock timeout、模型费用预算、上下文 token 预算和单工具 timeout。Agent Loop 只能引用 `BudgetManager`，不能再定义第二套预算对象。
- 在 `model_client/` 或 `agent_loop/` 实现 `ToolCallParser` 结果对象，覆盖解析成功、解析失败、重复 tool call id、缺失 tool call id 和残缺工具调用。
- 在 `verifier/` 实现 `VerifierParser` 对象或配置，记录 parser id、parser version、parser confidence 和低置信处理规则。
- 在 `model_client/` 实现 `ProviderCredentialPolicy` 或等价配置，明确 provider request、provider response 和凭证脱敏策略。
- 在 `context/` 实现 `ContextBuilder` 配置对象，和运行时 `ContextManager` / `PreparedMessages` 分开。
- 在 `export/` 实现 `ExportPolicy` 和 `ExportRecord` schema。
- 在 `model_client/` 或 `tests/fixtures/` helper 中定义 `ReplayScript` schema，至少包含 replay step id、assistant text、tool call id、tool name、arguments、final answer 和 expected outcome。
- `ReplayScript.expected_outcome`、replay fixture metadata、脚本注释和脚本中编码的正确动作序列都属于 test-only / evaluator-only 信息，不能进入 `PreparedMessages`、模型可见 transcript、监督微调或强化学习导出的 prompt、observation、assistant target。ReplayModelClient 只能把当前 step 的 assistant message 或 tool call 作为模型响应模拟出来，不能把 expected outcome 注入模型上下文。
- 实现统一 schema version 常量。

阶段二的重点是固定对象名称、字段、版本和唯一归属位置，不要求一次性实现所有后续业务逻辑。训练导出、复杂上下文替换和批量评测专用字段可以先作为严格校验的 Pydantic 对象存在，但第一条纵向闭环会用到的字段必须具备真实读写和测试覆盖。

完成后审查：

- 每个对象是否只有一个定义位置。
- 静态 `VerifierConfig` 和运行时 `ResolvedVerifierPlan` 是否分开。
- `BaselineResult` 是否明确阻断 invalid 或 flaky task 进入正式 agent run。
- `agent_stop_reason`、`final_verifier_status` 和 `run_outcome` 是否是三个独立字段。
- `ContentReplacementState` 是否能记录每个 tool result 第一次可见形态和后续替换形态。
- 所有 artifact 引用是否使用 `ArtifactRef`，而不是裸路径字符串。
- 所有 schema 是否包含版本字段。
- `gold_patch`、隐藏测试和 reward-only 字段是否有可见性字段约束。
- `ReplayScript` 是否能在第一条纵向闭环前固定工具调用顺序、工具参数和预期结论。

完成后验证：

```bash
python -m pytest tests/unit/test_config_schema.py tests/unit/test_task_schema.py tests/unit/test_core_schemas.py tests/unit/test_replay_script_schema.py
```

重点测试：

- 有效任务可以加载。
- 缺少必填字段会失败。
- `timeout_sec` 兼容简写可以展开为四类 timeout，如果实现兼容路径。
- `gold_patch` 不是 `hidden_reference` 时校验失败。
- 批量配置使用 `ask` 权限模式时校验失败或明确降级。
- `BaselineResult.status = invalid` 或 `flaky` 时，Eval Runner 的 schema 层和运行策略都能表达“不进入正式 agent run”。
- `ContentReplacementRecord` 至少能表达 `first_visible_form`、`first_visible_content_hash`、`replacement_text_hash`、`first_seen_at_context_revision` 和 `first_replaced_at_context_revision`。
- `ToolResult`、`VerifierResult`、`TranscriptRecord`、`ArtifactRef`、`PermissionDecision`、`ModelCallEvent`、`AgentLoopState`、`BudgetManager`、`ResolvedVerifierPlan` 和 `RewardMetadata` 都有 schema version、必填字段校验和基本 round-trip 测试。
- replay script 缺少 `tool_call_id`、工具名或参数类型错误时校验失败。

验收标准：

- schema 单元测试覆盖主要正常路径和错误路径。
- 第一版所有下游模块都只引用这些 schema。

### 阶段三：RunRecorder、JSONL 记录和 artifact manifest

目标：先建立事实记录层，让后续任何模块都通过统一接口写 transcript、events 和 artifact。

实现内容：

- 实现 `RunRecorder`：
  - `append_transcript(record)`
  - `append_event(event)`
  - `write_artifact(kind, data, metadata) -> ArtifactRef`
  - `write_json_artifact(kind, obj, metadata) -> ArtifactRef`
  - `finalize_run(summary)`
- 实现 run directory 初始化。
- 实现稳定 `run_id`、`event_id`、`record_id` 和 `artifact_id` 生成策略。
- artifact 写入先写临时文件，完成哈希后进入 `artifacts.json`。
- `append_event` 和 `append_transcript` 采用每行一个 JSON 对象的 JSONL 格式。
- `artifacts.json` 保存 manifest。
- `summary.md` 可以重复生成，但不能改写历史事实事件。
- 创建 `run.lock` 或等价运行锁，避免两个进程写入同一个 run directory。
- 记录 run directory 状态，例如 `RUNNING`、`FINALIZED`、`INTERRUPTED` 和 `CORRUPT_PARTIAL`。
- 在本阶段先实现最小 `inspect-run` 只读能力，至少能读取 `events.jsonl` 和 `artifacts.json`；如果 `metrics.json` 或 `summary.md` 已存在则读取并展示，如果尚未生成则明确报告缺失状态。即使 agent loop 还没有实现，也要能检查半成品 run directory。

完成后审查：

- 是否没有其他模块直接打开 `events.jsonl` 或 `transcript.jsonl` 写入。
- artifact 是否全部使用相对路径。
- artifact 哈希和大小是否在写入后计算。
- artifact manifest 中的哈希是否能通过重新读取文件复算出来。
- events、transcript、metrics、export 中出现的每个 `ArtifactRef` 是否都能解析回同一个 manifest 条目。
- 篡改 artifact 后，`inspect-run` 或 artifact 校验工具是否能报告哈希不匹配。
- 写入失败是否会产生结构化错误，而不是静默丢弃。
- interrupted 或 inconclusive 运行是否仍能被 `inspect-run` 读取。
- 运行锁是否能防止重复写同一 run directory。
- `inspect-run` 是否能识别未 finalize 的部分运行。

完成后验证：

```bash
python -m pytest tests/unit/test_run_recorder.py
```

重点测试：

- 写入 transcript 后文件每行都是合法 JSON。
- 写入 artifact 后 `artifacts.json` 中存在哈希、大小和相对路径。
- 写入 artifact 后重新计算 sha256，必须和 `artifacts.json` 中的值一致。
- transcript、events 或 summary 中引用的 artifact id 必须能在 `artifacts.json` 中找到。
- 人为修改 artifact 内容后，`inspect-run` 或 manifest 校验测试必须能发现不一致。
- 重复 finalize 不会破坏已有 events。
- 大文本 artifact 可以被引用，不会直接塞进 transcript。
- 并发尝试打开同一个 run directory 时，第二个 writer 会失败或进入只读模式。
- `inspect-run` 能对 `RUNNING`、`FINALIZED` 和 `INTERRUPTED` 状态给出不同摘要。

验收标准：

- 任何模块都可以用 `RunRecorder` 记录事实。
- 后续实现中禁止绕过 `RunRecorder` 写运行事实。

### 阶段四：Task Adapter 和 micro-repo fixture

目标：让第一版具备真实可执行任务输入，而不是只测空对象。

实现内容：

- 实现 `TaskAdapter`：
  - 读取 YAML。
  - 校验 schema。
  - 规范化路径。
  - 规范化 timeout。
  - 输出 `RunnableTask` 和静态 `VerifierConfig`。
- 在本阶段实现最小 `validate-task` 子命令，只调用 Task Adapter 做 schema、visibility、路径和静态 verifier 配置校验，不创建正式 workspace，不运行模型。
- 创建 3 到 5 个 micro-repo fixture：
  - 至少一个 Python 计算类 bug。
  - 至少一个多文件导入或配置 bug。
  - 至少一个需要新增文件的任务。该任务到阶段八实现 `create_file` 后再进入批量验收，不作为阶段七最小成功路径。
  - 至少一个会失败的 replay，用于阶段七之后验证失败 artifact。
  - 至少一个安全负例 replay，用于阶段八之后验证权限拒绝、工具结果配对和安全事件。安全负例应覆盖读取 `../outside.txt`、读取 `.env`、执行 `curl` 或执行 `git fetch` 这类风险动作中的至少两类。
  - 至少一个 invalid task fixture，用于验证 schema、静态 verifier 配置、setup command 或 baseline parser confidence 失败时不会进入正式 agent run。
  - 至少一个 flaky task fixture 或确定性的 flaky baseline simulator，用于验证多次 baseline 结果不一致时会被质量门控阻断。该 fixture 只用于门控测试，不作为默认训练样本。
- 每个任务都写清：
  - `task_version`
  - `dataset_name`
  - `source_kind`
  - `dataset_split`
  - `created_at`
  - `repo`
  - `issue`
  - `setup_command`
  - `test_command`
  - `timeouts`
  - `environment`
  - `visibility`
  - `fail_to_pass_tests`
  - `pass_to_pass_tests`
  - `decontamination`

replay 脚本映射不写入通用 `TaskDefinition`；如果测试需要 replay 文件路径或 replay fixture id，应放在 run config、测试 fixture manifest 或 replay-specific 配置中，避免任务定义和某个模型脚本耦合。

阶段四只要求这些 replay fixture 能通过静态校验并被后续阶段消费；真正运行失败 replay 和安全负例 replay，应分别放到阶段七、阶段八或阶段十的集成测试中。

完成后审查：

- 任务说明是否足够明确，但不泄漏答案。
- `fail_to_pass_tests` 和 `pass_to_pass_tests` 是否默认 verifier-only。
- micro-repo 是否足够小，方便快速运行和排查。
- fixture 是否不依赖外部网络。
- 任务定义中的相对路径是否只能指向 fixture 区域。
- 阶段四是否只做安全负例的静态定义，不要求完整权限系统已经运行。

完成后验证：

```bash
repo-harness validate-task tests/fixtures/tasks/<task>.yaml
python -m pytest tests/unit/test_task_adapter.py
```

验收标准：

- 所有 fixture task 都能通过 `validate-task`。
- 至少一个故意错误任务会被清晰拒绝，并给出具体字段原因。

### 阶段五：Workspace Adapter 和本地执行边界

目标：实现 source checkout、setup workspace、agent run workspace 和 verification workspace 的可复现生命周期。

实现内容：

- 实现本地 `WorkspaceAdapter`：
  - 接收由 Eval Runner / RunRecorder 创建并持有的 run directory。
  - 复制 fixture repo 到 source checkout。
  - 复制 source checkout 到 setup workspace。
  - 执行 setup command。
  - 捕获 `DependencyState`。
  - 复制 source checkout 到 agent run workspace。
  - 在 agent run workspace 恢复 dependency state。
  - 建立 `agent_start_snapshot`。
  - 捕获 `final.diff` 和 `final.patch`。
  - 创建 verification workspace。
  - 在 verification workspace 恢复 dependency state。
  - 应用 `final.patch`。
  - 清理或保留 workspace。
- 第一版 `DependencyState` 策略：
  - `none`：不做依赖恢复。
  - `rerun_setup`：在 agent run workspace 和 verification workspace 重新运行 setup command。
- 路径边界：
  - 解析相对路径。
  - 解析符号链接。
  - 拒绝访问 workspace 外路径。
  - 拒绝敏感路径。
- patch 和 diff 规则：
  - `final.patch` 和 `final.diff` 使用同一套 `excluded_diff_paths`。
  - 第一版允许普通文本文件新增、修改和删除。
  - 第一版拒绝或显式标记二进制文件改动。
  - 第一版拒绝或显式标记符号链接改动。
  - 未跟踪文本文件可以进入 patch，但必须在 patch stats 中单独统计。
  - 删除文件必须进入 patch stats，并在 summary 中显示。
- 命令执行：
  - 使用独立进程。
  - 所有命令必须有 timeout。
  - 保存 stdout 和 stderr artifact。
  - 记录 exit code、duration、timeout 和工作目录。
  - 本地进程模式使用进程组或等价机制清理子进程。

完成后审查：

- `final.patch` 和 `final.diff` 是否以 `agent_start_snapshot` 为基线。
- baseline verifier 产生的缓存是否不会进入 dependency state。
- verification workspace 是否从干净 source checkout 重建。
- setup mutation 是否不会被误记为 agent 贡献。
- 路径解析是否覆盖 `..`、绝对路径和符号链接。
- `.git/`、`.env`、私钥和 token 文件是否被拒绝。
- 新增文件、删除文件、二进制文件和符号链接的 diff 规则是否明确。

完成后验证：

```bash
python -m pytest tests/unit/test_workspace_paths.py tests/integration/test_workspace_lifecycle.py
```

重点测试：

- 访问 `../outside.txt` 被拒绝。
- 指向 workspace 外的符号链接被拒绝。
- 普通命令超时后进程被终止。
- agent run workspace 修改文件后可以生成 patch。
- patch 可以应用到 verification workspace。

验收标准：

- 工作区生命周期可以独立于 agent loop 运行。
- 任意写入和命令执行都必须经过 Workspace Adapter。
- Workspace Adapter 不直接绕过 RunRecorder 创建或写入运行事实；source checkout、setup workspace、agent run workspace 和 verification workspace 都位于 RunRecorder 管理的 run directory 之下。

### 阶段六：Verifier、accepted 判定、reward 和 metrics

目标：让任务是否成功由同一套 verifier 决定，并让 reward metadata 可追溯。

实现内容：

- 实现 `Verifier`：
  - `run_baseline(workspace, verifier_config)`
  - `run_feedback(workspace, resolved_verifier_plan)`
  - `run_final(verification_workspace, resolved_verifier_plan)`
- 实现 pytest parser：
  - 解析常见 pytest 输出。
  - 记录 parser confidence。
  - 记录 stdout/stderr artifact。
  - 生成 `TestCaseResult`。
- baseline 质量门控：
  - baseline 至少运行一次；micro-repo fixture 默认建议运行两次，或由 `baseline_rerun_count` 配置。
  - setup command 失败、测试命令无法启动、任务字段不完整、仓库无法准备时，`BaselineResult.status = "invalid"`。
  - 多次 baseline 结果不一致或声明测试用例初始状态不稳定时，`BaselineResult.status = "flaky"`。
  - baseline parser confidence 明显低于阈值时，不把任务标记为 flaky；应把任务标记为 `invalid`，并记录 `error_type = "low_parser_confidence"` 或 `parser_error`。
  - `invalid` 和 `flaky` 默认不进入正式 agent run，不产生默认训练样本，只写质量门控 artifacts、metrics 和 summary。
- 第一版为了稳定统计 `fail_to_pass` 和 `pass_to_pass`，建议对声明的测试用例额外运行可选择的单测试验证路径。具体策略：
  - baseline 阶段运行完整 `test_command`，保存完整输出。
  - 对 `fail_to_pass_tests` 和 `pass_to_pass_tests` 中声明的测试用例，使用 pytest 单测试命令确认初始状态。
  - final 阶段同样先运行完整 `test_command`，再确认声明测试用例状态。
  - 这条策略只用于第一版 pytest micro-repo task，后续再扩展为更通用的 parser 配置。
- 实现 `repo_harness_acceptance_policy_v0`：
  - patch 无法应用：`accepted = false`，`error_type = "patch_apply_failed"`。
  - 测试命令无法启动：`accepted = false`，`error_type = "test_command_error"`。
  - final verifier 超时：`accepted = false`，`timeout = true`，`error_type = "test_timeout"`；Eval Runner 再派生 `final_verifier_status = "timeout"` 和最终 `run_outcome`。
  - 有 fail-to-pass tests 时必须全部通过。
  - 有 pass-to-pass tests 时必须全部保持通过。
  - 没有声明 fail-to-pass 和 pass-to-pass 时，退化为整体 exit code 为 0，并记录 fallback reason。
  - parser confidence 低于阈值时，不能生成精细成功结论；`accepted = false`、`error_type = "low_parser_confidence"`，由 Eval Runner 派生 `final_verifier_status = "error"` 和 `run_outcome = "inconclusive"`。
- 实现 `RewardMetadata`：
  - final verifier 分量。
  - pass-to-pass regression penalty。
  - timeout penalty。
  - patch size penalty。
  - cost penalty 第一版可以为 0，但字段必须存在。
  - reward 裁剪到 `[0.0, 1.0]`。
  - `fail_to_pass.total = 0` 时，不把 fail-to-pass score 默认为满分；必须使用备用公式或标记该分量不可用。
  - patch replay failure、final verifier timeout、parser confidence 低于阈值、invalid task 和 flaky task 默认设置 `invalid_for_training = true` 或在 export filter 中标记为不可训练。
- 实现 `MetricsRecord` 聚合。

完成后审查：

- feedback verifier 是否只作为模型中间反馈，不替代 final verifier。
- baseline 和 final verifier 是否共用 parser 和 schema。
- `accepted` 是否只由 policy 派生。
- reward 是否只依赖 final verifier、events 和 diff。
- parser 低置信度时是否会标记训练无效或 inconclusive。
- pass-to-pass regression 是否能被单独识别。
- `BaselineResult.status = invalid` 或 `flaky` 时是否不会进入正式 agent run。
- reward 是否覆盖缺失 fail-to-pass 分母、patch replay failure、final timeout 和低 parser confidence。

完成后验证：

```bash
python -m pytest tests/unit/test_pytest_parser.py tests/unit/test_acceptance_policy.py tests/unit/test_reward.py tests/integration/test_verifier_micro_repos.py
```

验收标准：

- micro-repo 初始状态能生成 baseline。
- 修复 patch 后 final verifier 能接受。
- 引入回归时 final verifier 能拒绝并标记 `regression_detected`。
- 损坏补丁、无法应用到干净 source checkout 的补丁，或者依赖 agent workspace 残留状态的补丁，必须在 strict patch replay 中产生 `error_type = "patch_apply_failed"`，并进入 verifier、reward、metrics 和 training filter。
- baseline 或 final verifier 的低置信 parser 输出必须产生 `error_type = "low_parser_confidence"`，并由 Eval Runner 派生 `final_verifier_status = "error"` 和 `run_outcome = "inconclusive"`。
- reward 和 metrics 可以从 final verifier、events 和 diff 重建。

### 阶段七：最小纵向闭环

目标：在补齐所有工具和复杂上下文管理前，先用最小能力跑通一个真实 replay 修复任务，尽早验证模块接口是否正确。

阶段七不是一次性临时代码，而是后续阶段继续扩展的 thin vertical implementation。阶段九和阶段十只能在同一套 Context Builder、Context Manager、ReplayModelClient 和 Agent Loop 上补全预算、替换、错误路径和 scaffold 能力，不能重新实现第二套运行时状态机。

实现内容：

- 实现最小 `ContextBuilder`：
  - 注入系统规则、任务 issue、仓库根目录、测试命令摘要、允许工具和预算。
  - 不读取或注入隐藏测试、`gold_patch`、baseline 原始日志或 reward-only metadata。
- 实现简化版 `ContextManager`：
  - 每轮都生成 `PreparedMessages`、`context_revision`、`model_input_hash`、`prepared_messages_ref` 和 context event。
  - 第一条闭环可以不做复杂 replacement，但必须让 transcript、实际模型输入和后续导出能追踪到同一轮模型可见内容。
- 实现最小 `ReplayModelClient`：
  - 从 replay script 输出 `read_file`、`edit_file`、`run_tests`、`git_diff` 和 final answer。
  - 每一步都写 `ModelCallEvent`。
- 实现最小 `Tool` 工厂 `build_tool()`：
  - 未显式声明 `is_read_only` 的工具默认按可能写入处理。
  - 未显式声明 `is_concurrency_safe` 的工具默认不并发。
  - 未显式声明 `is_destructive` 的工具默认不是破坏性操作，但仍不能绕过权限。
  - 所有工具必须声明模型可见描述、输入 schema、输出上限和结果映射函数。
- 实现最小 `PermissionSystem` shim：
  - 覆盖 `read_file`、`edit_file`、`run_tests` 和 `git_diff` 四个最小工具。
  - 复用 Workspace Adapter 的路径解析、workspace boundary 和敏感路径检查。
  - 对允许动作写 `PermissionDecision(decision = "allow")`。
  - 对已知工具的 workspace 外路径和敏感路径写 `PermissionDecision(decision = "deny")`，并生成配对的 denied `ToolResult`。
  - 未知工具不进入 Permission System；工具查找阶段必须写结构化 invalid tool event，并生成配对的 error `ToolResult`。
  - 阶段八在该 shim 的同一接口上扩展完整规则，不能绕过或替换事件语义。
- 只实现四个最小工具：
  - `read_file`
  - `edit_file`
  - `run_tests`
  - `git_diff`
- 实现最小 `AgentLoop`：
  - 接收 Context Builder 生成的初始可见上下文，并维护后续 message state。
  - 每轮调用简化版 Context Manager 生成 `PreparedMessages`。
  - 调用 replay model。
  - 执行四个工具。
  - 回填 tool result。
- 实现只支持 replay 的最小 `run-task` 编排器：
  - 调用 Task Adapter、Workspace Adapter、Verifier baseline path、ResolvedVerifierPlan builder、Agent Loop 和 RunRecorder。
  - Agent Loop 返回停止状态后，由编排器调用 Workspace Adapter / Trajectory Store 捕获 `final.patch` 和 `final.diff`。
  - 编排器随后调用 Verifier final path、Reward module、Metrics 聚合和 summary 写出。
- 用一个 micro-repo task 跑通成功修复。
- 用一个失败 replay 验证 run 仍然能写出可复盘的 artifact、metrics 和 summary。

完成后审查：

- 纵向闭环是否只使用公开可见任务信息。
- replay 中每个 `tool_call_id` 是否恰好对应一个 `tool_result_id`。
- 阶段七是否没有把 final verifier、reward 或 metrics 逻辑塞进 Agent Loop 内部。
- 每轮是否都有 `context_revision`、`prepared_messages_ref` 和 `model_input_hash`。
- `events.jsonl` 中是否能看到 `model_call_started`、`model_call_completed`、`tool_requested`、`permission_decision`、`tool_completed`、`verifier_final` 和 `run_finished`。
- `final.patch` 是否能应用到全新 verification workspace。
- `summary.md` 是否来自真实 replay run，而不是手写示例。

完成后验证：

```bash
repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/replay_success_minimal.yaml --output-dir runs/test-stage-07 --run-id stage07-success
repo-harness inspect-run runs/test-stage-07/stage07-success
test -f runs/test-stage-07/stage07-success/dependency_state.json
test -f runs/test-stage-07/stage07-success/final.diff
test -f runs/test-stage-07/stage07-success/verifier.json
python -m pytest tests/integration/test_minimal_vertical_slice.py
```

机器可执行断言：

- `transcript.jsonl` 中没有孤立 tool call。
- `events.jsonl` 中至少包含一个 `tool_requested`、一个 `permission_decision` 和一个 `tool_completed`。
- 如果 replay 请求 workspace 外路径或未知工具，`events.jsonl` 必须包含 denied `permission_decision` 或结构化 invalid tool event，transcript 中仍必须有配对 `ToolResult`。
- `final.patch` 在 verification workspace 中可以应用。
- `verifier.json.accepted = true`。
- `metrics.json.run_outcome = "success"`。
- 每个 model call event 都能追踪到 `prepared_messages_ref`。

验收标准：

- 一个真实 micro-repo replay 修复闭环跑通。
- 最小闭环产物已经保留后续 Training Exporter 所需的基础引用字段；完整 observation 过滤、loss mask 和导出策略在阶段十二完成。

### 阶段八：完整权限系统和工具系统

目标：让模型动作变成受控、可记录、可回流的工具结果。

实现内容：

- 实现 `Tool` 基类或协议。
- 实现 `ToolRegistry`，并固定第一版工具顺序。
- 扩展阶段七中的 `build_tool()` 工厂，确保工具默认值保持保守：
  - 默认不只读。
  - 默认不并发。
  - 默认不能跳过权限系统。
  - 新工具缺少模型可见描述、schema 或输出上限时注册失败。
- 实现 `ToolExecutionContext`：
  - `run_id`
  - `task_id`
  - `workspace_facade`
  - `artifact_writer`
  - `permission_context`
  - `verifier_feedback_facade`
  - `abort_signal`
  - `output_limits`
  - `tool_policy`
  - `budget_manager`
  - `file_state_cache`
- 实现 `PermissionSystem`：
  - schema 和规范化之后再判断权限。
  - 不可绕过安全检查优先。
  - 显式 deny 规则优先于 allow。
  - 工具自身权限检查。
  - 任务 allowlist。
  - 当前权限模式 fallback。
- 实现工具：
  - `list_files`：路径边界内列文件。
  - `read_file`：读取文件片段，返回 content hash。
  - `grep`：调用 ripgrep 或 Python fallback。
  - `edit_file`：old_text/new_text 局部替换，默认要求唯一匹配。
  - `create_file`：只创建不存在的文件。
  - `bash`：只执行内置受限诊断命令，测试命令路由到 `run_tests`。
  - `run_tests`：调用 verifier feedback path。
  - `git_diff`：输出当前 diff preview 和完整 artifact。
- 实现非模型可见内部能力：
  - `write_file` 可以作为测试 helper 或内部能力，但第一版不暴露给 ReAct 类模型。
  - `apply_patch` 作为 Workspace Adapter 内部能力，或作为 single-shot patch 后续对比实验的处理能力；第一版不和 `edit_file` 同时暴露给 ReAct 类模型。
- 实现工具执行编排：
  - 第一版所有工具默认串行执行。
  - 工具仍保留 `is_concurrency_safe` 字段，便于后续开启只读工具并发。
  - 后续如果开启并发，结果必须按 tool call 原始顺序提交；第一版只通过字段和设计注释保留这个约束，不把并发执行作为验收条件。
- schema 校验失败的模型可见 observation 必须至少包含：
  - `error_type = "schema_validation_failed"`。
  - 失败字段名。
  - 期望类型。
  - 实际类型。
  - 是否可重试。
  - 原始参数 artifact 引用或摘要。
- 工具调用事件必须区分输入校验和权限判断：
  - tool requested event。
  - 如果工具名未知、schema 校验失败或工具输入语义校验失败，写结构化 validation failed event，并生成模型可见的合成 `ToolResult`；这类调用还没有进入 Permission System，不强制写 `permission_decision`。
  - 只有通过工具查找、schema 校验、输入规范化和工具级 validate_input 的调用，才进入 Permission System 并写 `permission_decision`。
  - tool completed、failed、denied、timeout 或 interrupted event。
  - transcript tool result record。

完成后审查：

- 工具是否绕过 Workspace Adapter。
- 权限拒绝是否也生成 ToolResult。
- schema 校验失败是否进入 transcript 和 events。
- `requested_arguments`、`normalized_arguments` 和 `effective_arguments` 是否都记录。
- bash 测试命令路由是否记录 `requested_tool_name`、`effective_tool_name` 和 `route_reason`。
- 大输出是否写 artifact，不直接进入模型上下文。
- 工具执行是否保持串行，且没有因为并发优化改变 transcript 顺序。
- schema 错误是否作为模型可见 tool result 回流，而不是抛出顶层异常。

完成后验证：

```bash
python -m pytest tests/unit/test_permissions.py tests/unit/test_tools.py tests/integration/test_tool_execution.py
```

重点测试：

- 未知工具生成 `unknown_tool`。
- schema 错误生成 `schema_validation_failed`。
- 访问 workspace 外路径生成权限拒绝。
- 权限拒绝必须有至少一个端到端 replay：断言 transcript 中有 denied `ToolResult`，events 中有 `permission_decision`，metrics 中 permission denial 计数递增，summary 能复盘原因，且 `tool_call_id` 与 `tool_result_id` 配对完整。
- `bash` 请求 `pytest -q` 被路由到 `run_tests`。
- `bash` 请求 `curl`、`git fetch`、管道、重定向、环境变量前缀或后台任务会被拒绝。
- `grep` 无匹配不是工具崩溃。
- 大 stdout 被写入 artifact。
- 工具注册顺序稳定，同一 replay 下 transcript 和 events 顺序稳定。

验收标准：

- 每个已解析 tool call 都有对应 tool result。
- 工具事件、权限事件和 transcript 可以互相追踪。

### 阶段九：Context Builder、Context Manager 和 fake/replay Model Client

目标：让 agent loop 看到的模型输入和训练导出使用的 observation 保持一致。

实现内容：

- 实现 `ContextBuilder`：
  - 注入系统规则。
  - 注入任务 issue statement。
  - 注入仓库根目录、语言、测试命令摘要和允许工具。
  - 注入权限模式、执行模式、预算和当前日期。
  - 注入 scaffold prompt fragment。
  - 注入可见的 expected files。
  - 可以注入 `README`、`AGENT.md`、`CLAUDE.md`、`CONTRIBUTING.md` 等仓库说明文件的摘要或路径，但必须标明来源是“不可信仓库上下文”，并明确这些内容不能覆盖系统安全规则、权限规则、隐藏 evaluator metadata、网络策略和 workspace boundary。
  - 不注入 hidden、verifier-only 或 reward-only metadata。
  - 记录 `context_builder_version`、`prompt_template_version` 和 `scaffold_version`。
- 实现 `ContextManager`：
  - 生成 `PreparedMessages`。
  - 写 provider-ready messages artifact。
  - 生成 `model_input_hash`。
  - 控制 tool result aggregate preview budget。
  - 保留最近若干 turn。
  - 旧测试输出替换为确定性摘要。
  - 校验 tool call 和 tool result 配对。
- 实现 `ContentReplacementState` 和 `ContentReplacementRecord`：
  - 记录每个 tool result 第一次进入模型上下文时的可见形态，例如 full、preview 或 replacement。
  - 记录第一次可见内容哈希。
  - 记录是否允许后续替换。
  - 记录替换文本哈希。
  - 记录替换 artifact refs。
  - 记录首次看到和首次替换的 `context_revision`。
  - 同一个 tool result 第一次被替换后，后续轮次和训练导出必须复用同一段 replacement preview。
- 第一版确定性替换规则：
  - replacement preview 包含 `tool_result_id`、`artifact_id`、`sha256`、前若干行、后若干行和截断原因。
  - 训练导出必须使用对应 `context_revision` 的模型可见内容，不能在导出阶段重新摘要。
- 实现 `FakeModelClient`：
  - 从脚本返回 assistant text 或 tool calls。
  - 支持非法工具名。
  - 支持 schema 错误参数。
  - 支持 final answer。
  - 支持模型错误模拟。
- 实现 `ReplayModelClient`：
  - 从 JSONL 或 YAML replay script 逐轮读取模型动作。
  - 用于端到端测试和示例运行。

完成后审查：

- Context Builder 是否是唯一初始消息构造入口。
- Scaffold 是否没有读取 hidden metadata。
- provider-ready messages 是否落盘并进入 artifact manifest。
- `prepared_messages_ref` 和 `raw_provider_request_ref` 是否概念分开，即使 fake model 没有真实供应商请求。
- 训练导出是否能够找到当时模型实际可见的 observation。
- provider reasoning 或隐藏思考内容默认不进入训练目标。
- 仓库说明文件中的 prompt injection 是否不会覆盖系统级边界。
- `ContentReplacementState.state_hash` 是否能证明导出阶段复用了同一份替换状态。

完成后验证：

```bash
python -m pytest tests/unit/test_context_builder.py tests/unit/test_context_manager.py tests/unit/test_fake_model.py tests/unit/test_replay_model.py
```

验收标准：

- 初始消息不包含 `gold_patch`。
- 旧大工具输出会被稳定替换。
- 相同输入下 `model_input_hash` 稳定。
- fake model 可以驱动至少一个工具调用序列。
- replay model 必须覆盖脚本耗尽、重复 `tool_call_id`、工具顺序不符合脚本、参数与 expected outcome 不一致、模型错误模拟后 Agent Loop 结构化收尾等负例。
- final answer 无工具调用、模型错误、schema 错误后继续、多轮 replacement continuity 都必须写入连续的 context event 和 `PreparedMessages` 引用。
- 同一个 tool result 在不同轮次中被替换时，replacement preview 保持一致。

### 阶段十：Agent loop 和 scaffold

目标：跑通多轮 action-observation agent loop。

实现内容：

- 接入并完善 `budget/` 中的 `BudgetManager` 运行时逻辑：
  - 最大轮数。
  - 最大工具调用次数。
  - 最大测试运行次数。
  - 单任务全局超时。
  - 命令超时。
  - verifier 超时。
  - 上下文预算。
  - artifact 大小预算。
- 实现 `ToolPairingState`。
- 实现 agent loop：
  - 从 Context Builder 生成的初始可见上下文初始化 message state。
  - 每轮 prepare messages。
  - model client generate。
  - parse tool calls。
  - 处理模型错误。
  - 处理无工具 final answer。
  - 执行工具。
  - 回填 tool result。
  - 如果 feedback tests passed，可以停止为 `feedback_tests_passed`。
  - 预算耗尽时生成确定性 `agent_stop_reason`。
  - 中断时补齐 interrupted tool result。
- 实现 scaffold：
  - `simple_react`：第一版硬性验收的唯一 scaffold。
  - `single_shot_patch`：只作为内部 patch apply 测试或后续对比实验预留，不阻塞第一版。
  - `planner_coder_verifier`：推迟到第一版闭环稳定之后，不进入第一版硬性验收。
  - scaffold 只提供 prompt fragment、允许工具、阶段转移和停止策略，不直接拼完整初始 messages。

完成后审查：

- agent loop 是否不直接操作文件系统。
- agent loop 是否不直接解析测试日志。
- 工具结果是否一定回流下一轮模型上下文。
- 停止后是否先 freeze final patch，再 run final verifier。
- `feedback_tests_passed` 是否不会直接等价于最终 success。
- `final_answer` 是否经过有效性检查，而不是无工具响应就自动接受。
- Agent Loop 是否不派生 `run_outcome`，只返回 `agent_stop_reason` 和 loop state。
- final patch 冻结、final verifier、reward、metrics 和 summary 是否由 Eval Runner 编排，而不是由 Agent Loop 内部直接完成。

完成后验证：

```bash
python -m pytest tests/unit/test_agent_loop_protocol.py tests/integration/test_agent_loop_replay.py
```

重点测试：

- 成功 replay：读文件、编辑、运行测试，并以 `feedback_tests_passed` 或有效 final answer 停止。
- schema 错误 replay：产生错误 tool result 后模型可继续。
- 权限拒绝 replay：产生 denied tool result。
- max_turns：停止原因为 `max_turns`。
- feedback 测试通过时 Agent Loop 可以停止为 `feedback_tests_passed`；final verifier 回归和最终 outcome 派生放到阶段十一 Eval Runner 验收。
- Agent Loop 只返回 `agent_stop_reason` 和 loop state；invalid baseline、flaky baseline、final timeout、final parser error 和最终 `run_outcome` 的派生测试放到阶段十一 Eval Runner。

验收标准：

- agent loop 能用 fake 或 replay model 在 micro-repo 上完成至少一个真实 action-observation 修复过程；最终 patch 冻结、final verifier 和 `run_outcome` 由阶段十一 Eval Runner 验收。
- 所有异常路径都有结构化记录。

### 阶段十一：Eval Runner 和命令行端到端闭环

目标：把各模块通过命令行串起来，形成用户可以直接运行的第一版工具。

实现内容：

- `validate-task`：
  - 只做任务 schema、可见性和静态配置校验。
- `run-task`：
  - 加载任务和配置。
  - 创建 workspace。
  - 运行 setup。
  - 运行 baseline verifier。
  - 生成 `BaselineResult`。
  - 如果 `BaselineResult.status` 是 `invalid` 或 `flaky`，默认不创建正式 agent run workspace，不进入 agent loop，只写质量门控 artifacts、metrics 和 summary。此时不生成正式 `ResolvedVerifierPlan`，summary 必须记录未生成原因；如果需要诊断对象，应命名为 diagnostic verifier plan，不能和正式 agent run plan 混用。
  - 只有 baseline 质量门控通过后，才根据静态 `VerifierConfig` 和有效 `BaselineResult` 生成正式 `ResolvedVerifierPlan`。
  - 运行 agent loop。
  - 冻结 patch。
  - 运行 final verifier。
  - 调用 `evaluation/outcome_policy.py` 或等价 Eval Runner 所属模块中的 `derive_run_outcome`，根据 baseline、agent stop reason、final verifier、timeout、manual stop 和策略版本派生最终运行结论。
  - 生成 reward、metrics 和 summary。
- `derive_run_outcome` 必须按下列优先级派生：
  - baseline status 为 `invalid`：`run_outcome = "invalid_task"`。
  - baseline status 为 `flaky`：`run_outcome = "flaky_task"`。
  - final verifier status 为 `accepted`：`run_outcome = "success"`。
  - final verifier status 为 `failed`：`run_outcome = "failed"`。
  - final verifier status 为 `timeout` 且没有可解析测试结果：`run_outcome = "inconclusive"`，如果配置选择把 final timeout 计为失败，必须在 metrics 中记录策略版本。
  - final verifier status 为 `error`：`run_outcome = "inconclusive"`。
  - manual stop 且未运行 final verifier：`run_outcome = "interrupted"`。
  - 任何新增细分 outcome 都必须在策略版本中记录，不能由不同模块自由解释。
- `run-batch`：
  - 顺序运行任务列表。
  - 第一版并发默认为 1。
  - invalid 或 flaky task 根据 `fail_on_invalid_task` 处理。
  - 写出 `batch_manifest.json`，记录每个任务对应的 run directory、run id、状态、失败原因和关键 artifact 引用。
- `inspect-run`：
  - 读取 run directory。
  - 输出任务 id、运行结果、停止原因、final verifier、reward、关键 artifact 路径和失败诊断。
- 命令返回码策略：
  - schema 或配置错误返回非零。
  - `validate-task` 失败返回非零。
  - `run-task` 如果命令本身完成但任务失败，可以根据配置决定返回 0 或非零；第一版建议默认返回 0，同时在 summary 中明确 `run_outcome`，便于批量评测不因单任务失败中断。
  - `fail_on_invalid_task = true` 时 invalid task 返回非零。

完成后审查：

- Eval Runner 是否没有绕过模块边界。
- baseline artifact 是否不进入 agent action-observation 轨迹。
- final verifier 是否总是在 agent 停止后运行，除非任务在 workspace 创建前失败。
- run directory 是否包含设计文档要求的产物。
- summary 是否清楚区分 agent 停止原因、final verifier 状态和最终运行结论。
- `derive_run_outcome` 是否位于 evaluation / outcome policy / Eval Runner 所属模块，而不是 Agent Loop 内部。

完成后验证：

```bash
repo-harness validate-task tests/fixtures/tasks/task_001.yaml
repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/replay_success.yaml --output-dir runs/test-stage-11 --run-id stage11-success
repo-harness inspect-run runs/test-stage-11/stage11-success
repo-harness run-task tests/fixtures/tasks/task_invalid.yaml --config tests/fixtures/run_configs/replay_success.yaml --output-dir runs/test-stage-11 --run-id stage11-invalid
repo-harness run-task tests/fixtures/tasks/task_flaky.yaml --config tests/fixtures/run_configs/replay_success.yaml --output-dir runs/test-stage-11 --run-id stage11-flaky
repo-harness run-batch --config tests/fixtures/run_configs/batch_replay.yaml --output-dir runs/test-stage-11-batch
python -m pytest tests/integration/test_eval_runner_quality_gate.py
```

验收标准：

- 单任务闭环可以完整运行。
- 批量运行至少覆盖 3 个 micro-repo task。
- 每个 run directory 都能被 `inspect-run` 读取。
- invalid 和 flaky fixture 必须阻断正式 agent run：不创建 agent run workspace，不生成正式 `ResolvedVerifierPlan`，不进入 Agent Loop，summary 记录门控原因，且 `fail_on_invalid_task` 的返回码策略可测试。

### 阶段十二：Training Exporter

目标：把已记录的运行产物转成训练数据，而不是重新运行任务或重新解释事实。

实现内容：

- 实现 `ExportPolicy`。
- 实现 SFT JSONL 导出：
  - system、user、assistant tool call、tool observation。
  - assistant 动作 loss mask。
  - tool result observation mask。
  - final patch 和 termination summary。
  - verifier 和 reward metadata ref。
- 实现 reinforcement learning rollout JSONL 导出：
  - prompt。
  - trajectory action。
  - observation。
  - final reward。
  - reward metadata ref。
  - invalid_for_training 和 invalid_reason。
- 实现最小 preference pair JSONL：
  - 同一 task 下有两个或多个 run 时，根据 final reward 和 verifier outcome 构造 chosen/rejected。
  - 如果没有足够多个 run，不生成 pair，但稳定输出 skipped manifest 或 skipped reason。
- 导出必须读取已有 run directory，不重新运行 verifier，不修改原始轨迹。
- 导出必须应用脱敏和过滤策略。
- 导出的 observation 必须来自对应 `context_revision` 的模型可见内容，不能使用导出时重新生成的摘要。

完成后审查：

- tool result 是否不会作为模型生成目标。
- hidden metadata 是否不会进入导出。
- export record 是否包含可复现实验字段。
- reward 是否来自 final verifier，不来自 feedback verifier。
- invalid、flaky、timeout 和 parser 低置信样本是否有清晰过滤原因。
- 导出的 observation 是否能追踪到 `PreparedMessages` 和 `ContentReplacementState`。

完成后验证：

```bash
repo-harness export runs/test-stage-11/stage11-success --format sft_jsonl
repo-harness export runs/test-stage-11/stage11-success --format rl_jsonl
repo-harness export runs --format preference_jsonl
python -m pytest tests/unit/test_export.py tests/integration/test_export_from_run.py
```

验收标准：

- 至少导出一条监督微调 JSONL。
- 至少导出一条强化学习 rollout JSONL。
- 导出记录中的 artifact refs 可以在原 run directory 中找到。
- 导出不包含 `gold_patch`、隐藏测试或 baseline 原始日志。
- 监督微调导出中，assistant tool call 是训练目标，tool observation 不是 assistant loss target。
- 强化学习 rollout 导出中，final reward 来自 formal final verifier，而不是 feedback verifier。
- 对导出 JSONL 做字符串扫描时，不应出现隐藏字段名、baseline 原始日志正文、本机绝对路径、provider credential 或 reward-only metadata 正文。
- 当没有足够 run 生成 preference pair 时，命令稳定输出 skipped manifest，而不是失败或静默无输出。

### 阶段十三：完整验收、审查和项目说明更新

目标：确认第一版实现和文档叙事一致，能够作为后续真实模型接入和批量评测的基础。

实现内容：

- 更新 README：
  - 从“设计阶段骨架”更新为“第一版实现范围”。
  - 明确已经实现和暂未实现的能力。
  - 保留安全边界的保守表述。
- 增加一个 walkthrough 文档：
  - 如何运行 `validate-task`。
  - 如何运行 replay agent。
  - 如何查看 run artifacts。
  - 如何导出训练数据。
- 增加一个示例 run summary。
- 增加开发者检查清单。

完成后审查：

- README 是否没有声称生产级安全沙箱。
- README 是否没有声称已经完成真实模型训练。
- 示例是否来自真实运行产物，而不是手写伪造产物。
- 示例 run summary 是否可以通过 `repo-harness run-task` 重新生成。
- run artifacts 是否可以独立复盘。
- 训练导出是否可以被下游训练流程读取。

完成后验证：

```bash
python -m pytest
repo-harness run-batch --config tests/fixtures/run_configs/batch_replay.yaml --output-dir runs/final-acceptance
repo-harness export runs/final-acceptance --format sft_jsonl
repo-harness export runs/final-acceptance --format rl_jsonl
python - <<'PY'
import json
import subprocess
from pathlib import Path

manifest = json.loads(Path("runs/final-acceptance/batch_manifest.json").read_text())
first_run_dir = manifest["runs"][0]["run_dir"]
subprocess.run(["repo-harness", "inspect-run", first_run_dir], check=True)
PY
```

验收标准：

- 全部测试通过。
- 批量 replay 至少跑通 3 个 micro-repo task。
- 成功 run、final verifier failed run、权限拒绝 run 和无效工具调用 run 至少各有一个可复盘样例。
- strict patch replay 失败、parser 低置信、invalid task 和 flaky task 至少各有一个可复盘样例，或者在 final acceptance manifest 中明确标记为第一版暂不纳入默认批量运行但已有独立集成测试覆盖。
- 所有必需运行产物存在。
- 导出文件合法且可追踪到原始 run artifacts。

## 5. 每个模块的实现细节和验收重点

### 5.1 Task Adapter

实现重点：

- 只负责读取、校验和规范化任务。
- 不创建 workspace。
- 不运行测试。
- 不计算 reward。
- 不把 baseline 结果写回 `VerifierConfig`。

验收重点：

- invalid task 有明确错误。
- visibility policy 生效。
- 任务路径不能越过仓库或 fixture 根目录。
- 任务元数据满足后续训练复现需要。

### 5.2 Workspace Adapter

实现重点：

- 所有文件写入、patch 应用和命令执行都经过这一层。
- 工作区路径、符号链接和敏感路径在这一层统一检查。
- 命令输出统一写 artifact。
- diff 和 patch 统一由这一层捕获。

验收重点：

- agent diff 不包含 setup 副作用。
- final verifier 使用 strict patch replay。
- workspace 外访问被拒绝。
- timeout 后没有遗留长时间进程。

### 5.3 Tool System

实现重点：

- 工具是能力契约，不是普通函数列表。
- 工具 schema 校验和语义校验必须在执行前完成。
- `ToolResult` 使用统一通用字段加工具类型扩展字段。
- tool result preview 和 artifact ref 同时存在。

验收重点：

- 每个 tool call 必有 tool result。
- 错误路径不抛出到 agent loop 顶层，而是转成结构化 observation。
- 所有工具在第一版默认串行。
- 工具 schema 中保留并发安全字段，但不在第一版执行并发优化。

### 5.4 Permission System

实现重点：

- permission 和 execution boundary 分开。
- 权限只是决策，不执行命令。
- 不可绕过安全检查优先于 allowlist。
- 批量评测不允许真实等待用户确认。

验收重点：

- 所有拒绝都有 `PermissionDecision`。
- 权限事件记录匹配规则、原因、模式、版本和路径解析结果。
- 网络相关命令在 local process mode 下被命令策略拒绝，但文档不声称操作系统级断网。

### 5.5 Verifier

实现重点：

- baseline、feedback 和 final 共用 parser 和 result schema。
- feedback verifier 可以进入模型上下文。
- baseline 和 final verifier 默认不进入模型可见上下文。
- final verifier 是 reward 和 success rate 的依据。

验收重点：

- low parser confidence 不被误判为成功。
- patch apply failure 进入 verifier error type。
- pass-to-pass regression 可以识别。
- final verifier timeout 和普通 assertion failure 分开记录。
- invalid 和 flaky 任务会被质量门控阻断，并能通过 `inspect-run` 查看原因。

### 5.6 Trajectory Store

实现重点：

- transcript 面向重放。
- events 面向统计和诊断。
- artifacts 面向完整输出和审计。
- 三者通过 id 和 artifact ref 关联。

验收重点：

- 不能把完整大日志塞进 transcript。
- event schema 对工具、权限、verifier、上下文和终止事件都友好。
- 崩溃或中断后已有记录仍可读取。

### 5.7 Agent Loop

实现重点：

- Agent loop 负责状态机，不负责工具内部执行细节。
- 每轮模型调用前必须经过 Context Manager。
- 模型错误、工具错误、权限拒绝和预算耗尽都有确定处理。
- Agent Loop 停止后，Eval Runner 仍然必须运行 final verifier，除非 run 在 workspace 创建前失败。

验收重点：

- `feedback_tests_passed` 不是最终成功。
- `final_answer` 需要有效性检查。
- `run_outcome` 由 deterministic rule 派生。
- 中断工具调用会补齐 interrupted tool result。

### 5.8 Training Exporter

实现重点：

- 只读取已有 run artifacts。
- 不重新运行 verifier。
- 不修改 transcript。
- 清楚区分 action、observation、target 和 reward。

验收重点：

- 监督微调 loss mask 正确。
- 强化学习 rollout 的 reward 来自 final verifier。
- hidden metadata 不泄漏。
- export metadata 足够复现实验。

## 6. 设计文档中需要反馈或进一步澄清的点

阅读 `00` 到 `12` 设计文档后，整体设计已经比较一致，没有发现会导致第一版无法实现的根本性矛盾。但正式编码前仍建议注意以下细节。

### 6.1 当前 README 和部分文档仍写着“设计阶段”

`README.md`、`docs/00-reading-guide.md` 和 `src/repo_harness/README.md` 都明确说当前仓库还只是设计阶段和 Python 骨架。开始实现后，这些表述需要在第一版完成时同步更新，否则项目状态会和代码能力不一致。

建议处理：

- 实现过程中可以暂时保留。
- 第一版闭环验收通过后，再更新为“已实现第一版最小闭环”。
- 同时写清楚哪些能力仍未实现。

### 6.2 pytest verifier 的测试用例级解析需要更硬的实现策略

设计文档要求 `fail_to_pass` 和 `pass_to_pass` 统计，但如果只运行 `pytest -q` 并解析普通文本输出，某些通过测试不会出现在输出中，导致 pass-to-pass 无法可靠统计。

建议第一版采用保守策略：

- micro-repo task 必须声明 `fail_to_pass_tests` 和 `pass_to_pass_tests`。
- verifier 运行完整 `test_command` 保存整体结果。
- 对声明的测试用例额外运行单测试命令确认状态。
- 文档中明确这是第一版 pytest 策略，后续再扩展到结构化测试报告、其他语言和更复杂 parser。

### 6.3 RunConfig 中默认 token estimator 需要和第一版依赖选择一致

`docs/11` 的示例已经同步为 `char4_token_estimator_v0`。第一版不引入 tiktoken，因此实现中的默认值也应使用确定性的字符估算器，并在版本字段中记录。

建议处理：

- 第一版默认 `token_estimator = "char4_token_estimator_v0"`。
- 后续接真实模型供应商后再引入 provider-specific token estimator。

### 6.4 bash 诊断命令 allowlist 需要配置入口

`docs/05` 已经说明 bash 默认只允许诊断命令、受限只读命令和任务声明的普通诊断命令，但任务 schema 和 RunConfig 里还没有非常明确的 `allowed_diagnostic_commands` 字段。

第一版必须二选一。为了降低风险，本计划选择更保守的一种：第一版不提供用户自定义 `allowed_diagnostic_commands` 字段，只允许内置诊断命令和测试命令路由。

第一版具体口径：

- 实现内置安全 allowlist，例如 `pwd`、`ls`、`find` 的受限形式、`python -m compileall`、`ruff`、`mypy`。
- 只允许任务 `test_command` 通过 `run_tests` 执行。
- 默认拒绝复杂 shell、管道、重定向、环境变量前缀、后台任务、网络命令和未列入白名单的 Git 子命令。
- 后续第二版再在 task schema 或 RunConfig 中增加结构化 `allowed_diagnostic_commands`。

### 6.5 DependencyState 第一版不应一开始实现太重

设计文档列出了 `none`、`rerun_setup`、`copy_declared_paths` 和 `docker_image_layer`。其中 `copy_declared_paths` 涉及依赖路径归档、恢复、排除 diff 和跨平台文件复制，容易拖慢第一版。

建议第一版硬性支持：

- `none`
- `rerun_setup`

建议第一版可选支持：

- `copy_declared_paths`

暂缓：

- `docker_image_layer`

### 6.6 no_progress 第一版建议先作为诊断，不作为默认终止条件

`docs/10` 已经给出 no progress 的保守启发式，但在 fake/replay model 阶段，过早把它作为强终止条件可能让协议测试变复杂。

建议第一版：

- 记录 no progress diagnostic event。
- 默认不因为 no_progress 终止。
- 在 `RunConfig` 中允许开启 `terminate_on_no_progress`。

### 6.7 preference pair 导出不应阻塞第一版闭环

设计文档列出了 preference pair JSONL，但最小闭环只要求至少导出监督微调和强化学习 rollout。preference pair 需要同一任务多个 run 的排序策略，适合在稳定 run-batch 后再扩展。

建议第一版：

- 保留 preference pair schema。
- 实现最小同任务 chosen/rejected 生成。
- 没有足够 run 时记录 skipped reason。
- 不把大规模 pair 生成作为第一版验收条件。

### 6.8 本地进程网络策略必须继续保守表述

设计文档已经强调 local process mode 不是操作系统级断网。实现计划也必须保持这个口径。

建议第一版：

- 通过命令解析和权限规则拒绝常见网络命令。
- 在 summary 中写明 `network_policy = deny_agent_run` 在 local process mode 下是命令层约束。
- Docker execution mode 后续再实现更强的网络边界。

## 7. 最终验收标准

第一版完成后，必须满足以下验收标准。

### 7.1 功能验收

- `repo-harness validate-task` 可以校验所有 fixture task。
- `repo-harness run-task` 可以用 replay model 跑通至少一个成功任务。
- `repo-harness run-batch` 可以顺序运行至少 3 个 micro-repo task。
- 至少一个 run 的 final verifier accepted。
- 至少一个 run 的 final verifier failed，并能在 summary 中说明原因。
- 至少一个 run 覆盖权限拒绝，并且至少一个 run 覆盖无效工具调用；两者都必须有可复盘 transcript、events、metrics 和 summary。
- 每个有效 run 都生成：
  - `task.yaml`
  - `transcript.jsonl`
  - `events.jsonl`
  - `artifacts.json`
  - `dependency_state.json`
  - `final.patch`
  - `final.diff`
  - `verifier.json`
  - `reward.json`
  - `metrics.json`
  - `summary.md`

### 7.2 协议验收

- transcript 中不存在孤立 tool call。
- 所有工具调用都有 tool result。
- 每个 `tool_call_id` 恰好对应一个 `tool_result_id`，中断或超时场景除外也必须有 interrupted 或 timeout result。
- unknown tool、`schema_validation_failed`、permission denied、timeout 和 interrupted 都有合成 tool result。
- `agent_stop_reason`、`final_verifier_status` 和 `run_outcome` 分开记录。
- feedback verifier 不能替代 final verifier。
- baseline 和 final verifier 默认 `model_visible = false`。
- `events.jsonl` 中必须能用事件类型断言至少存在 `run_started`、`baseline_completed`、`model_call_completed`、`tool_requested`、`permission_decision`、`tool_completed` 或等价失败事件、`verifier_final` 和 `run_finished`。

### 7.3 安全边界验收

- workspace 外路径读取被拒绝。
- workspace 外路径写入被拒绝。
- 跨 workspace 的符号链接访问被拒绝。
- `.git/`、`.env`、私钥、证书和 token 文件默认拒绝或脱敏。
- 风险 Git 子命令被拒绝。
- 网络命令被拒绝，并记录 `permission_decision` event。
- 所有命令都有 timeout。

### 7.4 评测和 reward 验收

- final verifier accepted 由 policy 派生。
- pass-to-pass regression 会导致失败或强惩罚。
- final verifier timeout 不会被误判为普通测试失败。
- parser 低置信度不会生成可靠成功样本。
- reward metadata 可以追踪到 final verifier、events 和 diff。

### 7.5 训练导出验收

- 可以导出至少一条监督微调 JSONL。
- 可以导出至少一条强化学习 rollout JSONL。
- 导出记录包含可复现实验 metadata。
- 导出记录不包含 `gold_patch`、隐藏测试、baseline 原始日志或 reward-only hidden fields。
- tool result observation 不作为 assistant loss target。
- export 中的 artifact ref 可以回到原始 run directory 查到。
- 导出的 observation 必须对应某个 `context_revision` 下模型实际可见的内容。
- 对导出 JSONL 做字符串扫描时，不应出现 `gold_patch`、隐藏测试字段名、baseline 原始日志正文和本机绝对路径。

### 7.6 工程验收

- `python -m pytest` 全部通过。
- 所有新增模块有基础单元测试。
- 关键闭环有集成测试。
- README 和示例文档不夸大安全能力或训练能力。
- `runs/` 和临时 workspace 不进入 Git。

## 8. 第一版之后的扩展顺序

第一版验收通过后，建议按以下顺序扩展：

1. 接入真实模型供应商。
2. 引入 provider-specific tool call parser 和 raw provider request/response artifact。
3. 增强 Context Manager，加入更好的 deterministic compaction。
4. 实现 Docker-based executable repository environment。
5. 扩展任务集到 20 到 50 个。
6. 增加真实模型多 rollout。
7. 增加 preference pair 批量生成。
8. 增加代码质量指标和行为质量指标。
9. 增加 planner-coder-verifier 的更完整顺序式策略。
10. 再评估是否需要后台子代理、Model Context Protocol 或远程执行。

## 9. 实施过程中的审查节奏

每完成一个阶段，应执行三类检查：

1. 模块内检查
   - schema 是否稳定。
   - 单元测试是否覆盖正常路径和错误路径。
   - 是否遵守模块所有权。

2. 跨模块检查
   - 是否绕过 RunRecorder。
   - 是否绕过 Workspace Adapter。
   - 是否把 hidden metadata 泄漏给模型。
   - 是否破坏 tool call 和 tool result 配对。

3. 端到端检查
   - replay run 是否仍能跑通。
   - run artifacts 是否完整。
   - final verifier 是否以 strict patch replay 为准。
   - export 是否仍能读取旧 run。

建议每完成阶段五、阶段七、阶段八、阶段十和阶段十二后做一次小型代码审查，因为这些阶段分别引入工作区执行、最小纵向闭环、工具权限、agent loop 和训练导出，是最容易产生边界错误的地方。

## 10. 最小完成定义

第一版只有在以下条件同时满足时，才可以认为完成：

- 至少 3 个 micro-repo task 通过 batch replay 跑完。
- 至少 1 个任务成功，至少 1 个任务失败且失败原因可复盘。
- 每个 run directory 的核心 artifact 完整。
- strict patch replay final verifier 可运行。
- SFT 和强化学习 rollout 导出可运行。
- 测试套件通过。
- 文档清楚说明第一版已实现能力和未实现能力。
- 安全表述仍然保守，不声称生产级安全沙箱、完整网络隔离或完整强化学习训练。
