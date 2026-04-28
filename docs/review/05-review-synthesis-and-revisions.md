# Review Synthesis And Revisions

## 审查流程

设计文档初稿完成后，启动了四个只读审查方向：

1. 架构审查：检查模块边界、数据流、控制流和 Claude Code 参考方式。
2. agentic training 对齐审查：检查 post-training、verifier reward、trajectory export 和简历叙事。
3. 实现可行性审查：检查文档是否足够进入后续工程实现。
4. 安全与范围边界审查：检查 sandbox、权限、SWE-Bench、强化学习、多代理和产品级能力是否过度声称。

所有审查都只读完成，没有直接修改文件。主线程根据审查意见统一修订设计文档。

## 关键意见处理结果

| 审查意见 | 处理结果 | 修订位置 | 处理说明 |
| --- | --- | --- | --- |
| 架构图过于线性，容易误解为一次性流水线 | 采纳 | `02-system-architecture.md` | 改为 control plane、execution plane、data plane，并说明 Trajectory Store 贯穿运行过程。 |
| Tool System、Permission System、Workspace Adapter 边界不够精确 | 采纳 | `02-system-architecture.md`、`04-tool-system-and-orchestration.md`、`05-workspace-sandbox-and-permissions.md` | 明确 Tool System 不绕过 workspace boundary，Permission System 只做决策，Workspace Adapter 统一处理路径、命令、输出和 diff。 |
| `run_tests` 与 final verifier 的关系不清楚 | 采纳 | `03-agent-loop-and-message-protocol.md`、`04-tool-system-and-orchestration.md`、`07-verifier-reward-and-evaluation.md` | 明确 baseline、feedback、final 三种 verifier 使用场景；最终 reward 和评测以 final verifier 为准。 |
| 缺少端到端对象流和统一对象模型 | 采纳 | `02-system-architecture.md`、`11-object-model-config-and-data-flow.md` | 增加核心对象清单、配置样例、未来目录规划和端到端数据流。 |
| 缺少模块所有权表 | 采纳 | `02-system-architecture.md` | 增加每个模块拥有的数据、不负责的事项、下游调用和事件产出。 |
| baseline 阶段结果如何进入正式运行不够明确 | 采纳 | `06-task-dataset-and-environment-adapters.md` | 增加 `BaselineResult`，说明 `valid`、`invalid`、`flaky` 状态和 workspace snapshot。 |
| 权限模式 `deny` 容易和单次拒绝混淆 | 部分采纳 | `05-workspace-sandbox-and-permissions.md` | 保留用户计划中的四种模式名称，但把 `deny` 明确定义为非交互拒绝风险操作模式，并说明它不是单次 permission decision。 |
| Event schema 对非工具事件不友好 | 采纳 | `08-trajectory-store-and-training-export.md` | 改为通用字段加工具、权限、verifier、上下文、终止等按类型扩展字段。 |
| reward metadata 缺少字段来源和边界条件 | 采纳 | `07-verifier-reward-and-evaluation.md` | 增加 `RewardMetadata` schema，说明字段来源、`fail_to_pass.total = 0`、flaky task 和 regression penalty。 |
| 训练导出样例过于占位 | 采纳 | `08-trajectory-store-and-training-export.md` | 扩展监督微调、reinforcement learning rollout 和 preference pair JSONL 的最小 schema。 |
| 运行产物目录有样例但缺少文件内容契约 | 采纳 | `08-trajectory-store-and-training-export.md` | 增加每个 artifact 的语义、生成时机和失败运行下的保留原则。 |
| 简历表述中“证明了能力”偏强 | 采纳 | `01-project-positioning-and-requirements.md` | 改为“提供了经验基础”，并说明设计阶段简历应保留“设计”“规划”等限定词。 |
| Docker execution mode 的“正式评测”可能被误读为生产安全保证 | 采纳 | `05-workspace-sandbox-and-permissions.md` | 改为本地或离线批量评测，补充“面向可复现执行，不面向对抗性代码隔离”。 |
| “task-level isolated workspace” 安全暗示偏强 | 采纳 | `05-workspace-sandbox-and-permissions.md` | 改为 `task-level separated workspace` 和 `task-level workspace boundary`。 |
| SWE-Bench Lite 在架构文档中应标注为未来或预留能力 | 采纳 | `02-system-architecture.md` | 改为“未来 SWE-Bench Lite 子集”。 |
| planner-coder-verifier 可能被误解为复杂后台多代理 | 采纳 | `09-agent-scaffolds-and-multi-agent.md` | 明确它是顺序式多角色 scaffold，不是独立后台多代理系统。 |
| 需要面向简历和面试的展示 artifact 文档 | 采纳 | `12-resume-narrative-and-demo-artifacts.md` | 增加项目谱系、技术难点、安全表述和 illustrative artifact 样例。 |
| 是否立刻实现 Python runtime 类和模块 | 拒绝 | `src/repo_harness/README.md`、`11-object-model-config-and-data-flow.md` | 第一阶段只做设计和骨架。新增对象模型文档，不新增实际功能代码。 |
| 是否把 Claude Code 产品源码结构复制到 Python 实现 | 拒绝 | `02-system-architecture.md` | 明确只借鉴架构模式和运行时不变量，不要求保留 TypeScript 文件名、产品模式名称或交互功能。 |

## 修订后的设计重点

修订后，RepoHarness 的设计更加明确地分为三个层面：

- 控制层：CLI / Eval Runner、Task Adapter、Agent Loop 和 Scaffold 负责组织任务、预算、模型调用和终止条件。
- 执行层：Tool System、Permission System、Workspace / Sandbox Adapter 和 Verifier 负责把模型动作变成受控环境反馈。
- 数据层：Trajectory Store、Metrics 和 Training Exporter 负责保存、统计、诊断和导出训练数据。

最重要的不变量保持不变：

- 工具结果必须回流到下一轮模型上下文。
- 训练 reward metadata 和离线 evaluation 必须共用 final verifier。
- transcript 与 events 必须分离。
- permission 和 sandbox 必须分离。
- 第一阶段不实现运行时功能，不声称生产级安全沙箱、完整强化学习训练、完整 SWE-Bench 复现或产品级编码助手能力。

## 后续实现建议

下一阶段如果进入具体实现，建议按以下顺序推进：

1. 先实现 `TaskDefinition`、`RunConfig`、`RunWorkspace`、`TrajectoryEvent` 和 `VerifierResult` 等数据对象。
2. 实现只读工具、workspace 路径边界和 events 写入。
3. 实现 `run_tests` feedback verifier 和 final verifier 的共享 parser。
4. 实现 simple ReAct scaffold，先在 3 到 5 个 micro-repo tasks 上跑通。
5. 实现 metrics 和训练导出，再比较 single-shot patch 与 simple ReAct。

这一路线保持项目和 agentic training、post-training、verifier-aligned evaluation 的目标一致，同时避免过早扩展到复杂远程多代理、生产级安全隔离或大规模 rollout 集群。
