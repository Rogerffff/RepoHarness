# Agent Scaffolds And Multi-Agent Design

## 设计目标

Scaffold 控制模型如何规划、调用工具和利用反馈。它不应该绑定任务格式、工具实现、workspace 或 verifier。

RepoHarness 第一版只设计 scaffold 接口和少量策略，不实现复杂远程多代理系统。

## Scaffold 抽象

一个 scaffold 至少决定：

- system prompt fragment 和角色策略。
- 每轮是否允许工具调用。
- 如何处理测试失败反馈。
- 是否有 planning 阶段。
- 是否有 verifier-driven repair 阶段。
- 何时停止。

Scaffold 必须可替换，以便同一批任务、同一套工具和同一 verifier 下比较不同 agent 策略。

## Scaffold 接口

第一版 scaffold 应是 agent loop 外层的策略接口，而不是另一个模型运行时。建议最小接口：

```text
Scaffold:
  scaffold_id
  scaffold_version
  system_prompt_fragment(task, run_config)
  context_requirements(task, run_config)
  allowed_tools(turn_state)
  next_phase(turn_state, tool_result, verifier_feedback)
  should_stop(state)
```

职责边界：

- Scaffold 可以决定 prompt fragment、允许工具、规划阶段、修复阶段和停止条件。
- Scaffold 不直接构造最终初始 messages。最终 system message、user task message、工具说明、权限说明、隐藏字段隔离和版本记录必须由 `ContextBuilder.build_initial_messages(...)` 统一完成。
- Scaffold 不应该直接读写 workspace，不应该直接执行 verifier，也不应该绕过 Tool System。
- Agent Loop 仍然负责模型调用、工具结果回流、预算检查和终止记录。
- Tool System、Workspace Adapter、Verifier、Trajectory Store 在不同 scaffold 下必须保持同一套实现，方便做公平对比实验。

每次运行必须记录 `scaffold_id` 和 `scaffold_version`。如果 scaffold 改变 prompt fragment、允许工具集合、phase transition 或 verifier feedback 处理策略，必须递增版本或在 run metadata 中记录差异。Context Builder 应同时记录 `context_builder_version`、`prompt_template_version` 和 `scaffold_version`，避免每个 scaffold 自己拼接 prompt 后绕过字段可见性规则。

## 第一版 Scaffold

single-shot patch：

- 模型一次性输出 patch。
- 不允许多轮测试反馈。
- 作为 baseline。

simple ReAct：

- 模型循环读取、搜索、编辑、运行测试。
- 测试失败后继续修复。
- 作为最小 agentic baseline。

planner-coder-verifier：

- planner 读取任务、定位文件、生成计划。
- coder 根据计划修改代码。
- verifier 运行测试、总结失败、请求继续修复。
- 第一版是顺序式多角色 scaffold，不是独立后台多代理系统，不需要真实后台 agent。

planner、coder 和 verifier role 可以共享同一个 workspace、tool system、permission system 和 trajectory store。它们的区别主要体现在 prompt fragment、允许动作、停止条件和如何消费 verifier feedback，而不是启动多个互相通信的远程代理。

这里的 verifier role 是 scaffold 内的“读测试反馈并建议下一步”的模型角色，不等同于 `Verifier` 模块。正式 `Verifier` 模块仍然是运行测试、解析结果、生成 `VerifierResult` 和 reward evidence 的系统组件，不能被 scaffold 角色替代。

## 多代理边界

第一版不实现：

- 后台长期子代理。
- 远程代理。
- agent-to-agent mailbox。
- 多 agent 并行工作区。
- 自动 worktree 分叉。

这些能力只保留为后续扩展。

## Claude Code 参考

参考模块：

- `reference/claude-code-docs/claude-doc/06-agent-and-multi-agent.md`
- `reference/claude-code-docs/claude-code-ai-core-codex/04-agenttool-tasks-and-remote-execution.md`
- `reference/claude-code-typescript-src/tools/AgentTool/AgentTool.tsx`
- `reference/claude-code-typescript-src/tools/AgentTool/runAgent.ts`
- `reference/claude-code-typescript-src/tasks/LocalAgentTask/LocalAgentTask.tsx`

借鉴点是：子代理应复用同一套 agent loop，而不是另写一套推理器。RepoHarness 第一版只保留这个设计原则。
