# Stage 09 Read-Only Review

## Scope

本审查针对 RepoHarness 第一版 Stage 09 context and model clients。审查方式为 sub agent 只读检查，不修改文件、不创建 commit。

## Findings

1. `src/repo_harness/model_client/replay.py`
   - 问题：`ReplayModelClient.generate()` 只按脚本顺序返回下一步，没有根据上一轮 `PreparedMessages` 校验实际 tool call 顺序、工具名、参数或 expected outcome。
   - 处理：已采纳。ReplayModelClient 现在会在进入下一步前校验上一轮 assistant tool call 与 tool result；工具顺序、工具名、参数、期望 status 或 error_type 不一致时返回结构化 model error。新增 replay 负例测试。

2. `src/repo_harness/context/manager.py`
   - 问题：同一个 tool result 如果先以 preview 进入上下文，后续才触发 replacement，记录会覆盖首次可见形态和首次可见 revision。
   - 处理：已采纳。后续 replacement 会保留既有 `first_visible_form`、`first_visible_content_hash` 和 `first_seen_at_context_revision`，只补充 replacement 字段。新增 continuity 测试。

3. `src/repo_harness/context/manager.py`
   - 问题：`ContentReplacementState` 只存在于内存返回对象中，prepared messages artifact 只写 hash，训练导出和 session resume 无法复原完整状态。
   - 处理：已采纳。Context Manager 现在写 `content_replacement_state` artifact，并把完整 state 和 state ref 放进 prepared messages artifact 与 context event。新增持久化测试。

4. `src/repo_harness/agent_loop/loop.py`
   - 问题：Model Client 返回了独立 `raw_provider_request_ref`，但 `model_call_completed` event 没有关联它。
   - 处理：已采纳。model call completed event 现在同时关联 raw provider request 和 response artifact，并在 event data 中记录两者引用。集成测试覆盖 request ref 与 prepared messages ref 分离。

## Conclusion

审查发现的阻断问题均已处理，并重新运行阶段九指定测试、阶段七和阶段八相关集成测试以及全量测试。
