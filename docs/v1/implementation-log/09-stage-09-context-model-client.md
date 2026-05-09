# Stage 09: Context And Model Clients

## Scope

本阶段实现了：

- 扩展 `ContextBuilder`：
  - 注入系统安全规则。
  - 注入任务 issue、expected files、workspace root、语言、测试命令、允许工具。
  - 注入权限模式、执行模式、网络策略、预算和当前日期。
  - 注入 scaffold prompt fragment。
  - 注入 `context_builder_version`、`prompt_template_version` 和 `scaffold_version`。
  - 可读取 `AGENT.md`、`README.md`、`CLAUDE.md`、`CONTRIBUTING.md` 的短 preview，并明确标记为不可信仓库上下文，不能覆盖系统安全规则、权限规则、hidden metadata policy、网络策略或 workspace boundary。
- 扩展 `ContextManager`：
  - 生成 provider-ready messages artifact。
  - 写 `model_input_hash`、`context_revision`、tokens before/after、context policy 和 tool pairing validation。
  - 控制 tool result aggregate preview budget。
  - 对超预算 tool result 生成确定性 replacement preview。
  - 写 `ContentReplacementState` 和 `ContentReplacementRecord`。
  - 同一个 tool result 后续 replacement 复用第一次生成的 preview。
- Agent Loop 的 tool result message 现在保留 `tool_result_id` 和 artifact refs，方便 Context Manager 和训练导出追溯模型实际可见 observation。
- `ReplayModelClient`：
  - 支持 YAML 和 JSONL replay script。
  - 检测重复 `tool_call_id`。
  - 写独立 `raw_replay_request` artifact，使 `raw_provider_request_ref` 与 `prepared_messages_ref` 概念分开。
  - raw replay response 不包含 `expected_outcome`。
  - 脚本耗尽返回结构化 `model_error_type = "replay_script_exhausted"`。
- `FakeModelClient`：
  - 复用 replay 协议，从内存步骤生成 assistant text、tool call、final answer 或模型错误。
- 阶段九单元测试覆盖 Context Builder、Context Manager、Fake Model 和 Replay Model。

本阶段明确不实现：

- 不接真实模型供应商。
- 不实现 LLM 自动摘要或复杂上下文压缩。
- 不实现训练导出；这里只保证导出后续能读取当时的 prepared messages 和 replacement state。
- 不改变 Agent Loop 的预算终止逻辑；阶段十继续扩展。

## Design References

- `docs/v1/implementation-plan.md`
- `docs/03-agent-loop-and-message-protocol.md`
- `docs/08-trajectory-store-and-training-export.md`
- `docs/11-object-model-config-and-data-flow.md`

## Files Changed

- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/context/builder.py`
- `src/repo_harness/context/manager.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/model_client/__init__.py`
- `src/repo_harness/model_client/fake.py`
- `src/repo_harness/model_client/replay.py`
- `tests/unit/test_context_builder.py`
- `tests/unit/test_context_manager.py`
- `tests/unit/test_fake_model.py`
- `tests/unit/test_replay_model.py`

## Verification

运行的命令：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_context_builder.py tests/unit/test_context_manager.py tests/unit/test_fake_model.py tests/unit/test_replay_model.py
PATH=.venv/bin:$PATH python -m pytest
```

结果：

- 通过。
- 阶段九指定测试收集并通过 13 个测试。
- 阶段七和阶段八相关集成测试收集并通过 12 个测试。
- 全量测试收集并通过 124 个测试。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查。

关键审查意见：

- ReplayModelClient 需要根据上一轮 prepared messages 校验实际 tool call 顺序、工具名、参数和 expected outcome。
- 后续 replacement 不能覆盖同一个 tool result 的首次可见形态和首次可见 revision。
- `ContentReplacementState` 不能只存在内存中，必须持久化到 artifact。
- Agent Loop 的 `model_call_completed` event 应直接关联 `raw_provider_request_ref`。

处理结果：

- 采纳：ReplayModelClient 现在在进入下一步前校验上一轮 assistant tool call 与 tool result；不匹配时返回结构化 model error。新增顺序、参数和 expected outcome 负例测试。
- 采纳：Context Manager 后续 replacement 会保留既有 `first_visible_form`、`first_visible_content_hash` 和 `first_seen_at_context_revision`。新增 replacement continuity 测试。
- 采纳：Context Manager 现在写 `content_replacement_state` artifact，并把完整 state 和 state ref 放入 prepared messages artifact 与 context event。
- 采纳：`model_call_completed` event 现在关联 raw provider request 和 response artifact，并在 event data 中记录两者引用。
- 采纳：审查报告保存到 `docs/v1/review/implementation/09-stage-09-review.md`。

## Known Limitations

- replacement 策略是确定性 preview replacement，不做语义摘要。
- 仓库说明文件只读取固定文件名和短 preview；第一版不做 prompt injection 分类器。
- FakeModelClient 和 ReplayModelClient 只用于测试和可复盘 replay，不连接真实供应商。
- `keep_recent_turns` 和 `keep_recent_test_results` 的更细粒度策略留到后续 context manager 增强。

## Commit

- Commit: `stage 09: implement context and replay model clients`
- Commit message: `stage 09: implement context and replay model clients`
