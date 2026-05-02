# RepoHarness V2 Scope And Roadmap

## 0. 文档定位

本文定义 RepoHarness 第二版的主要方向、范围边界、接口演进和验收标准。它建立在第一版已经完成的最小可运行闭环之上，不重新描述第一版的全部实现细节，也不把未来能力提前写成已经交付的能力。

RepoHarness 的长期目标是产生可执行、可审计、可导出的软件工程智能体训练轨迹。第一版已经证明本地 replay 运行可以完成从任务、工作区、工具调用、验证器、奖励元数据到训练导出的闭环。本文沿用项目已有术语：JSONL 指 JSON Lines，也就是每一行都是一个 JSON 对象的文本数据格式；API 指应用程序编程接口；scaffold 指控制模型规划、调用工具和使用反馈的智能体策略脚手架。第二版的核心问题变成：

> 如何把 replay-only micro-repo 闭环推进为真实模型可运行、任务规模可扩展、智能体策略脚手架可对比、训练导出质量更强，并为 Docker-based executable repository environment 留出清晰落地路径的研究型软件工程智能体 Harness。

这里的 Harness 指任务执行、工具调用、轨迹记录、评测验证和训练数据导出的统一运行框架。第二版仍然是轻量级研究和工程验证系统，不是生产级安全沙箱、企业权限平台、完整插件市场、完整 SWE-Bench 复现系统，也不是新的强化学习算法实现。

## 1. 第一版已经建立的基础

第一版的价值不是模型能力本身，而是把训练友好的运行时闭环跑通并留下可审计证据。根据 `docs/v1/final-acceptance.md`，第一版已经通过全量测试，收集并通过 160 个测试，并完成三个 micro-repo task 的顺序批量 replay 验收：其中包括一个成功任务、一个 invalid task 和一个 flaky task。最终验收还额外覆盖 final verifier failed、权限拒绝和未知工具调用样例。

第一版已经交付的关键能力包括：

1. 任务加载和校验
   - 支持 YAML 任务定义。
   - 支持模型可见字段、验证器专用字段、奖励专用字段和隐藏参考字段的可见性分离。
   - `gold_patch`、隐藏测试、奖励专用字段和 replay expected outcome 不进入模型上下文。

2. 工作区生命周期
   - 创建 source checkout、setup workspace、agent workspace 和独立 verification workspace。
   - 在正式 agent 运行前执行 baseline verifier。
   - 在 agent 停止后先冻结 `final.patch` 和 `final.diff`，再在独立 verification workspace 中执行 strict patch replay final verifier。

3. 工具协议和权限边界
   - 支持 `list_files`、`read_file`、`grep`、`edit_file`、`create_file`、`bash`、`run_tests` 和 `git_diff` 的最小工具族。
   - 未知工具、schema 校验失败、权限拒绝、工具异常、工具超时和中断都能产生结构化 `ToolResult`。
   - 工具调用和工具结果保持配对，工具结果会回流到下一轮模型上下文。
   - 本地进程执行模式下有路径边界、敏感路径拒绝、风险命令拒绝和输出 artifact 记录。

4. 验证器、奖励和指标
   - 支持 baseline verifier、feedback verifier 和 formal final verifier 三种阶段。
   - 中间 `run_tests` 只作为模型反馈，正式奖励和最终评测只来自 final verifier。
   - `RewardMetadata` 引用 final verifier、事件统计和补丁统计，是 verifier-aligned reward metadata，不是新的强化学习算法。

5. 轨迹和导出
   - 进入正式 Agent Loop 的有效 run 会生成 `events.jsonl`、`transcript.jsonl`、`artifacts.json`、`baseline.json`、`resolved_verifier_plan.json`、`final.patch`、`final.diff`、`verifier.json`、`reward.json`、`metrics.json` 和 `summary.md`。
   - 被 baseline quality gate 阻断的 invalid task 和 flaky task 会生成 skipped 状态的 `metrics.json`、`summary.md` 和相关 baseline artifact，但不会生成正式 agent workspace、`resolved_verifier_plan.json`、`final.patch`、`verifier.json` 或 `reward.json`。
   - 支持监督微调 JSONL、强化学习运行轨迹 JSONL 和偏好数据 JSONL 的导出入口。同一任务不足两个可配对 run 时，偏好数据导出会稳定输出 skipped manifest，而不是伪造 pair。
   - 导出器只读取已有 run directory，不重新运行 verifier，不改写已经记录的 reward 或 metrics 事实。

第一版的限制同样明确：

- 只使用 replay model 和 fake model，不调用真实模型供应商。
- 只支持本地进程执行边界，不提供生产级安全沙箱。
- 任务集仍是少量 micro-repo fixture，不是公开大型软件工程评测集。
- `simple_react` 是唯一实际可用的智能体策略脚手架。
- 导出阶段只有基础质量过滤、本机路径脱敏和常见凭据正则脱敏，不等同于完整 secret scanner。

第二版应保留这些第一版不变量，而不是为了新增能力破坏已经验证过的闭环。

## 2. 第二版的一句话主线

第二版的主线是：

> 在不破坏第一版可审计闭环的前提下，把 RepoHarness 从确定性 replay harness 扩展为真实模型驱动、中小规模任务集可评测、多种智能体策略可比较、训练数据质量更可控的研究型软件工程智能体 Harness。

这条主线有三个重要含义。

第一，第二版不是直接跳到大规模异步 rollout 集群。公开技术报告层面的启发是：DeepSeek、GLM、KAT、Qwen 和 Kimi 相关报告都说明，工业级 agentic training infrastructure 很复杂，包含分布式 rollout、可抢占恢复、上下文打包、环境服务化、奖励服务化和大规模并发调度。RepoHarness 第二版更应该先把单机或小规模运行的事实链条做扎实。

第二，第二版不是只接一个真实模型 API。真实模型接入是必要步骤，但如果没有训练导出质量、scaffold 对比、任务质量门控和 failure diagnostics，真实模型运行只能产生一次性演示，不能形成可审计、可导出的训练轨迹。

第三，第二版核心范围不强制交付 Docker execution mode。本文把 Docker 放在第五阶段，作为前四条主线稳定后的扩展目标。若把它纳入第二版交付范围，就必须满足独立的端到端验收；若时间或环境条件不允许，第二版至少应完成接口边界、风险清单和测试计划。Docker execution mode 在本文中只表示 Docker-based executable repository environment，用于提高环境复现性和执行边界控制。它不等同于对抗性隔离、沙箱逃逸防护、操作系统级断网或多租户安全平台。

## 3. 第二版范围优先级

第二版建议按五条主线推进。优先级不是按听起来最先进排序，而是按对现有第一版闭环的增量价值、实现风险和训练数据价值排序。

### 3.1 第一优先级：训练导出和数据质量增强

第一版已经能导出监督微调 JSONL、强化学习运行轨迹 JSONL 和偏好数据 JSONL。第二版首先应该把导出从“能生成”推进到“可解释、可过滤、可对比、可追溯”。

需要增强的内容：

- 沿用并增强现有 `ExportRecord.filter_status` 和 `invalid_for_training` 字段。`filter_status` 继续表达 `included`、`skipped` 或 `filtered`，`invalid_for_training` 继续表达样本是否可以进入训练；如果需要新增 `diagnostic_only`，应作为兼容字段或迁移后的明确枚举，而不是直接破坏旧导出记录。
- 定义唯一训练资格主状态 `training_eligibility`，建议枚举为 `trainable`、`diagnostic_only`、`skipped` 和 `invalid`。`filter_status` 和 `invalid_for_training` 可以继续作为兼容字段存在，但导出审计和训练数据消费方应以 `training_eligibility` 为主判断，避免多个字段互相冲突。
- 为跳过样本记录稳定的 `invalid_reason` 或 `skipped_reason`，例如 `missing_formal_final_verifier`、`permission_violation`、`reward_hacking_suspected`、`artifact_manifest_invalid`、`context_pairing_invalid`。
- 在导出 metadata 中保留 provider、model id、scaffold id、scaffold version、tool policy version、permission policy version、context policy version、export policy version 和 reward formula version。
- 在 run directory 中写入稳定的运行配置事实来源，例如 `run_config.json` 或 `run_metadata.json`。导出器应优先从这个事实来源读取 provider、model id、scaffold version、预算、权限模式和策略版本，而不是只从模型调用事件、metrics 或初始 prompt 中推断。
- 检查导出的 tool observation 是否来自当时真实的 `PreparedMessages`，而不是导出时重新生成的摘要。
- 增强 artifact manifest 校验，确保导出记录中的 artifact ref 可以回到原始 run directory。
- 更清楚地区分 assistant action、tool observation、system instruction 和 evaluator-only metadata。监督微调目标应是 assistant action，不应把工具观察结果作为 loss target。
- 在强化学习运行轨迹 JSONL 中明确 final reward 来源。如果 final reward 不是来自 strict patch replay formal final verifier，则必须标记为不可作为正式训练奖励。

第二版训练导出和审计规范应升为硬性交付物，而不是只补若干 metadata 字段。每次导出至少应产生：

- 目标格式数据文件，例如监督微调 JSONL、强化学习运行轨迹 JSONL 或偏好数据 JSONL。
- `export_manifest.json`：记录导出格式、导出 schema 版本、export policy version、输入 run 列表、输出文件、记录数量、included 数量、skipped 数量、filtered 数量、invalid 数量、导出命令参数和导出时间。
- `audit_report.json`：记录每个样本的机器可校验审计结果，包括 artifact 引用校验、工具调用配对校验、脱敏校验、监督微调损失目标校验、formal final verifier 来源校验、reward 来源校验、隐藏字段泄漏检查和本地绝对路径检查。
- `audit_report.md`：面向人工复盘的摘要，可由 `audit_report.json` 派生，不作为训练事实来源。

`audit_report.json` 中的检查项应有稳定名称和状态，例如 `passed`、`failed`、`warning`、`skipped`。任何 `failed` 的审计项都必须映射到 `training_eligibility` 或 `invalid_reason`，不能只写入自由文本备注。

这条主线的原因是：轨迹格式决定后续能否做监督微调、强化学习训练、偏好训练和失败案例分析。相比马上增加复杂模型策略，先把数据质量层做硬，可以避免后续真实模型运行产生一批难以复用的轨迹。

### 3.2 第二优先级：多 rollout 与智能体策略脚手架对比

第一版只有 `simple_react` 路径。第二版应该把 RepoHarness 从“一个 agent loop 的演示”推进到“同一任务、同一工具、同一验证器下可比较不同策略”的实验框架。

第二版建议支持三类智能体策略脚手架：

1. `single_shot_patch`
   - 模型一次性输出补丁或文件修改请求。
   - Harness 内部应用补丁或转成写文件操作。
   - 不允许中间测试反馈。
   - 作用是提供低成本 baseline，帮助判断多轮工具使用是否真的提升结果。
   - 该策略不是简单增加一个 registry entry。它需要新增 patch action 解析、patch 安全校验、应用失败的结构化结果、模型可见失败反馈策略，以及禁止中间 `run_tests` 反馈的独立 loop policy。

2. `simple_react`
   - 延续第一版主线。
   - 模型循环读取文件、搜索、编辑、运行测试、读取反馈并继续修复。
   - 作用是保留最小 agentic baseline。
   - 第一版中 `run_tests accepted -> feedback_tests_passed -> stop` 是 replay-friendly 简化策略。第二版不应把 feedback verifier accepted 固定等同于停止信号，而应由 scaffold 和 runtime stop policy 决定。

3. `planner_coder_verifier`
   - 顺序式策略脚手架，不是后台多代理系统。
   - planner 阶段定位任务和制定计划。
   - coder 阶段执行文件修改。
   - verifier role 阶段读取 feedback verifier 输出并决定是否继续修复。
   - 这里的 verifier role 只是模型策略角色，不等于系统 Verifier 模块。正式 Verifier 模块仍然是运行测试、解析结果、生成 `VerifierResult` 和 reward evidence 的系统组件。

多 rollout 对比应支持：

- 同一任务在同一 scaffold 下运行多次。Replay 路径用于确定性回归和协议一致性检查；真实模型路径用于观察采样差异和模型行为差异。
- 同一任务在不同 scaffold 下运行，用于比较策略差异。
- 同一任务在不同模型或不同采样参数下运行，用于比较模型和配置差异。
- 偏好数据导出时只在可比较条件下配对，例如同一 task id、同一 verifier version、同一 reward formula version 和相近预算。

第二版应新增可配置的 `feedback_tests_passed_policy`，用于处理 feedback verifier 中 `run_tests` 已经 accepted 后 Agent Loop 是否停止的问题：

- `stop_immediately`：保留第一版 replay 回归和低成本评测行为。`run_tests accepted` 后可以立即停止，并记录 stop reason。
- `require_model_final`：真实 provider 推荐默认值。测试通过后把结果回流给模型，至少再给模型一轮机会输出 final answer、查看 `git_diff` 或检查改动。
- `continue`：把 `run_tests accepted` 当作普通反馈，只由模型行为、预算、超时和 scaffold stop policy 决定停止。

无论选择哪种策略，feedback verifier 仍然只是模型可见中间反馈。formal final verifier 仍然是 run outcome、reward、训练资格和正式验收的唯一来源。

第二版还必须新增独立的 `test_feedback_policy`，用于区分模型能否调用 `run_tests`，以及 `run_tests` 能向模型暴露哪类测试反馈。这个策略解决的是测试反馈可见性问题，不能和 `feedback_tests_passed_policy` 混为一谈。

建议取值如下：

- `disabled`：模型不能调用 `run_tests`。模型只能读代码、修改代码并输出 final answer；系统在 agent 停止后运行 formal final verifier。这是最接近 SWE-Bench final-only 的模式。
- `public_only`：`run_tests` 只运行仓库中模型本来可见的公开测试，或者任务显式声明为 model-visible 的 smoke tests。它不能运行 hidden fail-to-pass 或 pass-to-pass suite。
- `structured_public_feedback`：`run_tests` 可以返回结构化公开测试摘要，例如公开测试通过数量、失败数量、退出码和公开失败摘要，但不能返回 hidden suite 的 accepted、fail-to-pass 或 pass-to-pass 计数。
- `oracle_hidden_feedback`：`run_tests` 可以运行 evaluator-only 测试，并向模型返回 `accepted`、fail-to-pass 和 pass-to-pass 等结构化反馈。这个模式只用于训练环境、调试环境或研究对照，必须在 metadata、metrics、export manifest 和评测报告中显式标记，不能被标记为 SWE-Bench-like final-only 评测。

当 `test_feedback_policy = disabled` 时，`feedback_tests_passed_policy` 对 Agent Loop 是 not applicable，因为模型不可调用 `run_tests`，不会产生模型可见的 feedback verifier accepted 事件。配置中可以保留该字段用于记录默认值，但它不能触发停止行为，也不能被统计为真实测试反馈通过后的停止策略。

`oracle_hidden_feedback` 轨迹默认不能进入正式训练数据，只能作为 `diagnostic_only` 或研究对照数据。只有 export policy 显式允许 oracle feedback training，且导出审计确认 oracle 标记完整、没有伪装成 final-only 评测时，才可以把这类样本标记为 `trainable`。

对 SWE-Bench-like task，默认建议是 `test_feedback_policy = disabled`；如果希望接近真实工程师可以运行仓库公开测试的场景，可以使用 `public_only`。隐藏 suite 只能用于 baseline quality gate、formal final verifier、reward metadata 和 training eligibility，不能进入 `PreparedMessages`、模型可见 transcript、`run_tests` 模型可见输出、SFT prompt 或 SFT target。

偏好数据配对规则必须从路线图阶段就写成硬门控，而不是只在导出时按照 reward 排序。第二版 preference exporter 应记录 `pairing_policy_version` 和 `compare_scope`，并在以下字段不一致时默认阻断配对，除非实验配置显式声明这是跨条件对比：

- task id、task version、base commit 和 source archive hash。
- environment spec、environment spec hash、dependency state policy 和 execution mode。
- verifier name、verifier version、reward formula version 和 final verifier mode。
- tool schema snapshot、tool order、tool parser version 和 tool result format version。
- context policy version、prompt template version 和 export policy version。
- scaffold id、scaffold version、allowed tools policy 和 phase policy。
- model provider、model id、temperature、seed、max output tokens、turn budget、tool budget、test budget 和 task timeout。

第二版不应实现复杂并行 agent swarm、后台长期子代理、远程代理、agent-to-agent mailbox 或自动 worktree 分叉。Claude Code 的 AgentTool 和任务系统可以作为“子流程应该复用同一套 agent loop 和轨迹记录”的参考，但 RepoHarness 第二版只需要支持顺序式 scaffold 对比。这里仅借鉴统一 query、tool call、tool result 链路，不借鉴 Claude Code 的后台任务、远程镜像、持续通信、任务通知和产品级 sidechain transcript 体系。

### 3.3 第三优先级：至少一个真实模型供应商接入

第一版的 `ReplayModelClient` 证明了工具协议、上下文准备、权限拒绝、验证器和导出链条可以跑通。第二版需要接入至少一个真实模型供应商，以验证 harness 在非脚本化模型响应下是否稳定。

真实模型接入应优先保持 Model Client 抽象，不应重写 Agent Loop。现有 `ModelResponse`、`ModelCallEvent`、`raw_provider_request_ref`、`raw_provider_response_ref`、`provider_request_id`、token usage 和 `model_error_type` 已经提供了扩展位置。

同时，当前代码仍然有第一版约束：`run_task` 明确拒绝非 replay provider，Eval Runner 直接构造 `ReplayModelClient`，Agent Loop 的构造函数类型也绑定 replay client。第二版在接入真实 provider 前必须先完成三项解耦：

- 引入通用 `ModelClient` 协议或基类，让 `ReplayModelClient`、mock provider client 和真实 provider client 实现同一契约。
- 引入 model client factory，根据 `RunConfig.model.provider`、凭证策略和运行模式创建模型客户端。
- 调整 Eval Runner 和 Agent Loop 的类型依赖，使它们只依赖通用模型客户端契约，不依赖 replay 具体实现。

真实模型客户端需要处理：

- provider request 构造：把 RepoHarness 标准 messages、工具 schema、模型参数、采样参数和最大输出 token 转换成供应商请求。
- provider response 解析：把供应商返回的 assistant 文本、工具调用、finish reason、错误类型和 token usage 转成标准 `ModelResponse`。
- 工具调用解析：记录 parser id、parser version、parse error type、是否可恢复、是否生成模型可见协议错误。
- 原始请求和响应 artifact：保存脱敏后的 provider request 和 response，记录 redaction 状态和 retention policy。
- 凭证策略：默认只从环境变量读取密钥，不把认证 header、token 或本地绝对路径写入导出样本。
- 重试策略：区分 rate limit、auth error、provider error、context limit 和 invalid response，不把 provider 基础设施错误误记为模型任务失败。
- reasoning 内容策略：如果供应商只返回 reasoning token usage，只记录用量；如果供应商返回 reasoning summary，应默认不把它作为监督微调目标；任何隐藏思考内容默认不进入训练导出。

真实模型接入的第一阶段建议使用 mock HTTP provider 做测试，再接入一个真实 provider。这样可以在没有外部网络或没有密钥时仍然回归工具调用解析、错误分类、脱敏和 artifact 记录。

### 3.4 第四优先级：任务集扩展到 20 到 50 个 repository-level task

第一版任务集主要是 micro-repo fixture。第二版需要扩展任务规模，但不应直接承诺完整 SWE-Bench 复现。

建议任务扩展顺序：

1. 增加更多自建 micro-repo 和小型 repository-level task。
2. 增加 terminal-style 软件工程任务，例如修复命令行脚本、配置错误、导入错误或测试失败。
3. 增加 issue-style task fixture，把 issue statement、仓库状态、测试命令和验证器配置统一成 `TaskDefinition`。
4. 在环境构建和质量门控稳定后，再评估 SWE-Bench Lite 子集适配。

当前第一版 Task Adapter 仍主要面向 fixture repository，并且测试命令策略非常保守，基本围绕 pytest 路径设计。第二版扩展任务集前，需要先扩展 repo materialization 和命令白名单策略：

- repo materialization 应支持 fixture path 之外的本地归档、受控本地仓库副本或未来可校验的公开仓库快照。
- source archive hash、base commit、任务来源和 decontamination metadata 应进入任务事实记录。
- 测试命令白名单可以逐步扩展，但必须仍然经过 VerifierConfig、Permission System 和 Workspace Adapter 的统一约束。
- 不同语言或包管理器的任务必须先定义 environment spec、setup policy 和 verifier parser 策略，不能只把任意 shell 命令塞进任务。

repo materialization 的三类来源应有不同必填字段：

- 本地归档：记录 archive path、archive sha256、解包后 source tree hash、expected root directory 和 base commit 或 synthetic base id。
- 本地仓库副本：记录 source path、当前 commit、working tree clean 状态、source tree hash、是否允许未提交文件进入任务快照。
- 公开仓库快照：记录 remote URL、commit sha、下载或镜像来源、archive sha256、decontamination metadata 和是否移除了 remotes、branches、tags。

无论来源是哪一种，正式 agent workspace 都应来自可审计 source checkout，而不是直接在用户原始仓库目录中运行。

任务扩展必须保留第一版质量门控：

- baseline verifier 用于判断任务是否可执行，不要求 bug-fix task 初始状态全部测试通过。
- pass-to-pass 初始失败、依赖安装失败、parser 低置信、flaky baseline、测试命令错误和 unexpected broad failure 应阻断进入正式 Agent Loop。
- fail-to-pass 初始全部通过通常说明任务无效，不能把这种样本作为修复任务训练数据。
- decontamination metadata、source archive hash、base commit 和任务来源应继续记录。
- 隐藏测试、`gold_patch` 和 reward-only 字段不能进入模型上下文或训练导出。

第二版的任务规模目标应写成“20 到 50 个中小型 repository-level task”，而不是“完整公开榜单复现”。这能保持简历叙事可信，也能让工程实现集中在 harness 质量而不是榜单追逐。

### 3.5 第五优先级：Docker-based executable repository environment

Docker execution mode 是第二版的重要方向，但不属于前四阶段核心验收，且风险最高，建议在前四条主线稳定后作为条件成熟后的扩展阶段推进。当前代码中的 `execution_mode = "docker"` 只是配置和 schema 层的预留，运行器仍会拒绝 Docker 模式；第二版真正实现 Docker 前，必须调整这条拒绝逻辑和对应回归测试。

Docker 相关设计原则：

- Docker execution mode 应作为独立 Workspace Adapter 或清晰分离的执行后端，不应把容器逻辑塞进 `LocalWorkspaceAdapter`。
- setup、agent run 和 formal final verifier 三个阶段都必须记录 execution mode、image id、network policy、mount policy、command timeout 和 artifact 路径。
- 在 Docker 后端能力允许时，agent run 和 formal final verifier 默认配置为无网络或受控网络，并记录实际生效状态；如果 setup 阶段需要网络安装依赖，必须由任务配置显式声明。
- 容器内路径不应直接泄漏成本机绝对路径进入模型上下文或训练导出。
- Docker 模式下仍然必须先冻结 `final.patch`，再在独立 verification workspace 中 strict patch replay。
- Docker 模式应提高环境复现性和依赖隔离，但文档不能声称它提供生产级安全沙箱、沙箱逃逸防护或完整网络隔离。

Docker mode 的最小验收不应只停留在配置可以加载，而应跑通 source checkout、setup、agent workspace、工具执行、`run_tests`、`final.patch`、verification workspace 和 final verifier。

## 4. 第二版接口和对象模型演进

第二版不需要推翻第一版对象模型。更稳妥的做法是沿现有对象边界扩展。

### 4.1 Model Client

现有 replay client 应继续保留，作为协议回归、确定性测试和边界样例的基础。真实 provider client 应实现同一类输出：

- 标准化 `ModelResponse`。
- 标准化 `ToolCall`。
- `ModelCallEvent`，包含 provider、model id、provider request id、context revision、prepared messages ref、model input hash、tool schema hash、token usage、duration、retry count 和 model error type。当前 schema 中已经有 model id 和 provider request id，第二版应补充 provider 字段，避免只能从配置或事件上下文推断供应商。
- 脱敏后的 raw provider request artifact。
- 脱敏后的 raw provider response artifact。
- 可引用的 `tool_schema_snapshot_ref`，包含工具 schema、工具顺序、tool parser version 和 tool result format version。只保存 hash 不足以审计真实模型看到的工具契约。

Agent Loop 不应该因为真实模型接入而知道某个供应商的原始协议。供应商差异应被隔离在 provider client 和 tool call parser 中。

### 4.2 Experiment Config

第二版建议增加实验配置概念，用于描述一组可比较 runs，而不是只在 `RunConfig.tasks` 中顺序列任务。

实验配置至少应能表达：

- 任务集合。
- 每个任务的 rollout 次数。
- 使用哪些模型配置。
- 使用哪些 scaffold。
- 预算和权限模式。
- 输出目录和 run id 命名策略。
- 是否生成对比报告和 preference pair。

这可以先作为 `run-batch` 的增强配置或新的实验命令设计，不要求第一步就引入复杂调度器。

### 4.3 Scaffold Registry

第二版 scaffold registry 至少需要：

- `scaffold_id`
- `scaffold_version`
- prompt fragment
- allowed tools policy
- phase transition policy
- stop policy
- 是否允许 final answer without tool
- 是否允许 feedback verifier 驱动修复

Context Builder 仍然负责最终初始消息拼接、可见性隔离、版本记录和任务上下文注入。Scaffold 不能直接绕过 Context Builder 读取隐藏字段或构造完整初始消息。

现有第一版实现中，`build_scaffold` 只支持 `simple_react`，Context Builder 的 system prompt 仍带有 `simple_react agent` 的硬编码语义，Eval Runner 创建 Agent Loop 时也没有把 `runtime.scaffold_id` 对应的 scaffold 显式传入。第二版扩展 scaffold registry 时必须同时改造 Context Builder、Agent Loop、Eval Runner 和测试入口。否则新增 scaffold 只能影响局部提示词，不能真正影响策略阶段、允许工具、停止条件或训练导出 metadata。

### 4.4 Export Metadata

第二版导出记录应更明确地区分“可以训练”“只用于诊断”“应跳过”三类样本。

建议新增或强化的导出字段：

- `training_eligibility`
- `quality_status`
- `quality_reasons`
- `provider`
- `model_id`
- `scaffold_id`
- `scaffold_version`
- `final_verifier_mode`
- `final_verifier_status`
- `reward_source`
- `artifact_manifest_status`
- `tool_pairing_status`
- `context_policy_version`
- `prepared_messages_ref`
- `content_replacement_state_ref`
- `redaction_status`
- `export_manifest_ref`
- `audit_report_ref`

导出器仍然必须只读已有 run directory，不能重新运行 verifier，不能改写 reward 或 metrics。导出完成后，`export_manifest.json` 和 `audit_report.json` 应作为导出目录下的新产物记录本次导出事实，不反向修改原始 run directory 的事实文件。

偏好数据配对约束也需要落到字段来源。第二版应在 run metadata 或 export metadata 中稳定记录 verifier version、reward formula version、tool budget、time budget、scaffold id 和 model id。Preference exporter 才能在同一 task id 下判断两条运行轨迹是否真的可比较，而不是只按 final reward 和 run outcome 粗略排序。

### 4.5 Workspace Adapter

第二版应把 Workspace Adapter 抽象成可以替换执行后端的接口。Local process mode 和 Docker mode 可以共享任务物料准备、artifact 记录、patch 捕获和敏感路径策略，但命令执行、环境变量、网络策略和路径映射需要分开实现。

关键要求：

- 所有文件读写和命令执行仍然通过 Workspace Adapter。
- 路径解析和最终边界判定由 Workspace Adapter 统一提供。Tool System 和 Permission System 可以做防御性校验，但只能通过 Workspace Adapter 接口请求路径解析、敏感路径判断和 workspace boundary 判定，不能各自实现互相不一致的路径规则。
- Permission System 只做决策，不执行命令。
- Verifier 通过 Workspace Adapter 执行测试，不直接绕过执行边界。

### 4.6 Run Metadata And Environment Fingerprint

第二版应把 `run_metadata.json` 定义成 run directory 中的稳定事实文件。它不是 summary，不是从 prompt 反推的文本说明，而是导出、审计、实验比较和 `inspect-run` 的机器可读来源。

`run_metadata.json` 至少应包含：

- run id、task id、task version、dataset name、source kind、base commit、source archive hash。
- provider、model id、temperature、seed、max output tokens、retry policy、credential policy 和 provider request logging policy。
- scaffold id、scaffold version、allowed tools policy、phase policy 和 stop policy。
- tool schema snapshot ref、tool order、tool parser version、tool result format version 和 tool policy version。
- context builder version、context policy version、prompt template version、token estimator version。
- permission mode、permission policy version、network policy 和 shell command policy version。
- verifier name、verifier version、final verifier mode、reward formula version 和 outcome policy version。
- budget 配置，包括 max turns、max tool calls、max test runs、task timeout、command timeout、context budget 和 artifact budget。
- execution mode facts。即使 Docker 不进入第二版核心交付，本地执行模式也必须记录 Python 版本、操作系统、包管理器版本、关键锁文件 hash、setup artifact hash、dependency state ref、environment spec hash、source checkout hash 和 workspace adapter version。

第一版历史 run directory 没有 `run_metadata.json`。第二版导出器需要有兼容策略：

- 对第一版历史 run，导出器可以只读推断已有字段，但必须在 `audit_report.json` 中标记 `metadata_source = "legacy_inferred"`。
- 无法推断的字段不能伪造，应写为 `unknown` 或 `missing`，并进入 `quality_reasons`。
- 如果提供只读 backfill 工具，它只能生成独立的 backfill 报告或新的 metadata artifact，不能改写原始第一版 run 的历史事实。
- 第二版新 run 必须写入 `run_metadata.json`；缺失该文件时，导出审计应至少给出 warning，涉及配对、训练资格或真实模型审计时可以升级为 failed。

## 5. 第二版成功标准

第二版的成功标准应以可验收事实为准。

### 5.1 产品能力验收

- 真实模型接入必须分三层验收：无密钥环境下 mock provider 可以稳定回归；真实 provider 缺少凭证时测试可以跳过但必须输出结构化 skip reason；提供凭证时至少一个固定任务必须完成端到端 `run-task` 并通过 formal final verifier。
- 真实 provider 路径必须覆盖结构化失败：auth error、rate limit、invalid response、tool call parse failure、context limit、provider timeout 和 provider error 都要有 `model_error_type`、artifact ref 和 summary。
- ReplayModelClient 继续通过现有成功、失败、权限拒绝、未知工具和 schema 错误回归测试。
- 至少两种 scaffold 可以在同一任务集合上运行，并记录 `scaffold_id` 和 `scaffold_version`。验收不能只看标识：`single_shot_patch` 不允许中间 `run_tests`；`planner_coder_verifier` 必须记录 phase transition；allowed tools policy 必须真实限制工具集合；导出 metadata 必须能证明策略确实生效。
- 至少 20 个中小型 repository-level 或 repository-style task 可以通过批量运行入口顺序执行。这些任务可以混合扩展后的 micro-repo、小型仓库任务和 issue-style fixture，但不能把全部 skipped 当作成功。建议最低验收为：20 个任务通过静态校验；至少 15 个任务通过 setup 和 baseline quality gate 并进入正式 Agent Loop；至少 15 个任务产生 formal final verifier；至少 3 个任务产生 accepted 成功样例；invalid、flaky、dependency failed、permission denied、timeout 等类别可以存在，但必须有结构化分布报告。该目标不要求与公开榜单结果直接可比。
- invalid、flaky、dependency failed、permission denied、invalid tool call、final verifier failed、timeout 等结果都有结构化 metrics 和 summary。
- `inspect-run` 能读取真实模型 run 和 replay run，并能报告 provider、model id、scaffold version、run metadata 状态、artifact manifest quality status、export audit status、baseline、final verifier、reward、metrics 和 summary 状态。
- 导出器能为监督微调、强化学习运行轨迹和偏好数据输出清晰的 `training_eligibility`、included、skipped、filtered 或 invalid reason，并生成 `export_manifest.json` 和 `audit_report.json`。

### 5.2 研究评测验收

- 可以在同一任务、同一 verifier、同一工具集合下比较 `simple_react` 和至少一种新增 scaffold。
- 实验报告至少包含 task success rate、fail-to-pass 测试通过率、pass-to-pass 测试保持率、平均 turn 数、平均工具调用数、平均测试次数、final verifier status 分布、run outcome 分布、权限拒绝率、无效工具调用率、timeout rate 和 patch size。
- 能区分模型失败和环境失败，例如 dependency error、parser low confidence、environment unstable、test timeout、provider error 和 permission violation。
- 偏好数据 pair 的 chosen 和 rejected 必须满足 pairing policy 的硬门控，并记录 `pairing_policy_version`、`compare_scope`、chosen/rejected 的 verifier、reward、预算、模型和 scaffold 条件。只满足同一 task id 不能作为第二版偏好数据合格标准。
- 失败样本可以进入诊断数据集，但不能无标记地进入正式训练数据。

### 5.3 工程质量验收

- 第一版全量测试继续通过。
- 新增真实模型路径有 mock provider 单元测试和至少一个可复现 smoke test。
- 新增 scaffold 有 replay 驱动的集成测试，不依赖真实 provider 才能回归。
- Docker mode 是第五阶段扩展目标，不是第二版核心基线的强制交付项。如果纳入第二版交付范围，必须有 source checkout、setup、agent run、final patch、verification workspace 和 final verifier 的端到端测试。
- `gold_patch`、隐藏测试、ReplayScript expected outcome、reward-only 字段和本地敏感路径不能进入 `PreparedMessages`、transcript 的模型可见内容或训练导出 prompt。
- 每个已解析 `ToolCall` 都必须有对应终态 `ToolResult`。
- formal final verifier 仍然是正式 reward 和 run outcome 的来源。

## 6. 第二版非目标

第二版明确不做以下事项：

- 不实现生产级安全沙箱。
- 不承诺操作系统级本地断网。
- 不实现企业权限系统。
- 不实现完整插件市场。
- 不实现完整 Model Context Protocol 动态工具生态。
- 不实现远程多代理平台。
- 不实现后台长期子代理、agent swarm、agent-to-agent mailbox 或多工作区团队协作。
- 不实现大规模异步 rollout 集群。
- 不实现 token-granular write-ahead logging、KV cache resume 或分布式可抢占 rollout service。
- 不复现 GRPO、DAPO、TITO、OPD、Tree Training、MCLA、importance sampling 或其他工业强化学习算法。
- 不声称完整 SWE-Bench 复现。
- 不把少量真实模型运行包装成“训练出了软件工程智能体”。
- 不把 Docker execution mode 描述成 production-grade sandbox。

这些非目标不是价值否定，而是为了保证第二版聚焦在“可执行、可审计、可导出”的训练轨迹基础设施上。

## 7. 风险和保守表述

### 7.1 安全表述风险

可以写：

- 路径边界检查。
- 命令超时。
- 敏感路径拒绝。
- 权限决策事件。
- Docker-based executable repository environment。
- 本地进程执行边界。
- 训练数据脱敏策略。

不要写：

- 生产级安全沙箱。
- 完整网络隔离。
- 沙箱逃逸防护。
- 企业级权限系统。
- 多租户安全平台。

### 7.2 真实模型表述风险

可以写：

- 支持真实模型驱动的评测运行。
- 记录 provider request、provider response、token usage、model error type 和 redaction status。
- 真实模型运行轨迹可以进入同一套 verifier 和 export pipeline。

不要写：

- 已经验证工业级长轨迹智能体能力。
- 已经训练出 coding agent。
- 已经复现 Claude Code 或其他生产级代理产品。

### 7.3 训练算法表述风险

可以写：

- verifier-aligned reward metadata。
- 强化学习运行轨迹 JSONL。
- preference pair JSONL。
- 便于后续连接训练器。

不要写：

- 新强化学习算法。
- 复现工业 post-training pipeline。
- 复现某家公司的内部 agentic training stack。

### 7.4 benchmark 表述风险

可以写：

- 20 到 50 个中小型 repository-level task。
- issue-style fixture task。
- 未来可评估 SWE-Bench Lite 子集适配。

不要写：

- 完整 SWE-Bench 复现。
- 公共榜单级评测平台。
- 与工业 benchmark 结果直接可比，除非任务来源、环境、预算、模型和评测口径都已经对齐。

## 8. 建议实施顺序

第二版建议分阶段实现，每个阶段都保持第一版 replay 验收可用。

### 阶段一：导出质量和实验 metadata

- 写入稳定的 `run_config.json` 或 `run_metadata.json`，作为导出器读取 provider、model id、scaffold、预算、权限模式和策略版本的事实来源。
- 记录 local process mode 的环境指纹，包括 Python 版本、操作系统、包管理器版本、锁文件 hash、setup artifact hash、source archive hash、base commit、dependency state ref 和 environment spec hash。
- 增强 export record 的 `training_eligibility`、质量标签、跳过原因和 provider/scaffold metadata。
- 增加 artifact manifest 和 tool pairing 的导出前检查。
- 增加 `export_manifest.json` 和 `audit_report.json`，并把 artifact 引用校验、工具调用配对校验、脱敏校验、监督微调损失目标校验、formal final verifier 来源校验写成机器可读审计项。
- 增加真实模型字段的空值兼容，确保 replay run 仍然可导出。
- 增加导出质量报告，说明多少样本 included、skipped、invalid。
- 将 preference pair 的可比性约束落到字段和测试中，至少记录同一 task id、verifier version、reward formula version、预算和 scaffold 信息。

### 阶段二：多 rollout 和 scaffold registry

- 扩展 scaffold registry，支持 `single_shot_patch` 和顺序式 `planner_coder_verifier` 的最小版本。
- 改造 Context Builder、Eval Runner 和 Agent Loop，使 `runtime.scaffold_id` 真实影响 prompt fragment、允许工具、停止策略、phase transition 和运行 metadata。
- 为 `single_shot_patch` 增加 patch action 解析、安全校验、应用失败 ToolResult 或等价结构化结果，以及独立 loop policy。
- 增加同一任务多次运行的 run id 生成策略。
- 增加 scaffold 对比报告和 preference pair 构造约束。
- 保证不同 scaffold 仍然共用同一套 Tool System、Permission System、Workspace Adapter、Verifier 和 Exporter。

### 阶段三：真实模型客户端

- 引入通用 `ModelClient` 协议或基类，并把 Eval Runner 和 Agent Loop 从 `ReplayModelClient` 具体类型上解耦。
- 引入 model client factory，根据 `RunConfig.model.provider` 创建 replay、mock 或真实 provider client。
- 新增 provider client 接口实现。
- 使用 mock provider 测试 request/response、工具调用解析、错误处理、重试和脱敏。
- 补充真实 provider 无凭证时的结构化 skip 结果，以及 auth error、rate limit、invalid response、tool call parse failure、context limit 等失败路径测试。
- 接入一个真实 provider 的最小端到端 run。
- 确保 provider 原始响应不直接成为训练目标。

### 阶段四：任务集扩展

- 增加 20 到 50 个中小型 repository-level task。
- 先扩展 repo materialization，让任务来源不再局限于 fixture repository，并为归档、本地仓库副本或未来公开仓库快照记录可校验来源。
- 扩展测试命令和 setup 命令白名单策略，但仍然保持 verifier、permission 和 workspace 三层约束。
- 增强 task adapter 的 repo materialization、source hash 校验和任务质量门控。
- 记录任务来源、难度、标签和 decontamination metadata。
- 生成按任务、按 scaffold、按模型的评测摘要。

### 阶段五：Docker 执行环境扩展目标

- 抽象 Workspace Adapter 接口。
- 实现 Docker-based executable repository environment 的最小路径。
- 移除或调整当前运行器对 Docker execution mode 的拒绝逻辑，并保留 local process mode 的回归测试。
- 验证 setup、agent run、strict patch replay final verifier 的完整链路。
- 记录 image、network policy、mount policy、container command 和 artifact path。
- 明确保守表述，不把 Docker mode 写成生产级安全沙箱。

## 9. 子代理审查结论整合

本文建议整合三类只读审查视角，分别用于约束产品范围、代码可实现性和外部参考映射。

产品范围审查的核心结论是：第二版应该从 replay-only micro-repo harness 推进到真实模型驱动、Docker 执行环境扩展路径、更多任务集和 scaffold 对比的研究型评测平台，同时明确不做生产级安全沙箱、完整 SWE-Bench 复现、新强化学习算法或复杂远程多代理平台。

代码可实现性审查的核心结论是：现有配置层、模型 schema、Agent Loop、工具系统、评测运行器和导出器已经有第二版扩展入口。最稳妥的实现顺序是先增强导出质量，再做多 rollout 和 scaffold 对比，然后接真实模型，再扩展任务集，最后实现 Docker execution mode。Docker mode 风险最高，应该作为独立 Workspace Adapter，而不是混入 `LocalWorkspaceAdapter`。

Claude Code 参考和技术报告审查的核心结论是：RepoHarness 第二版应该学习生产级智能体运行时的纪律，包括工具契约、权限分层、工具结果配对、上下文治理、大输出落盘、transcript/events/artifacts 分离和可插拔 scaffold；但不应照抄交互式产品界面、复杂后台任务系统、远程代理、插件市场或工业级 rollout infrastructure。技术报告共同指向的是训练闭环结构，而不是要求第二版复现任何一家公司的内部训练系统。

## 10. 最终结论

RepoHarness 第二版的主要方向不是追求单点炫技，而是把第一版已经跑通的闭环变成更接近真实 agentic training workflow 的研究型 Harness：

- 用真实模型验证协议。
- 用更多任务验证规模。
- 用多 scaffold 验证策略差异。
- 用更强导出质量保证训练样本可信。
- 为 Docker-based executable repository environment 建立清晰接口和验收路径；如果阶段五纳入交付，再用它增强可复现执行。
- 用严格的 final verifier 和 artifact 证据链保持评测、奖励和导出一致。

如果第二版完成核心范围，它可以被清晰表述为：

> 一个面向软件工程智能体训练轨迹的轻量级研究 Harness，支持真实模型运行、中小规模任务评测、多策略对比、verifier-aligned reward metadata 和可审计训练数据导出，并为 Docker-based executable repository environment 留出可验收的扩展路径。

这条表述保留了项目的技术含量，也避免把第二版夸大成生产级代理产品、完整基准复现或新训练算法。
