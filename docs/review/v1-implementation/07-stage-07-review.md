# Stage 07 Read-Only Review

## Scope

本审查针对 RepoHarness 第一版 Stage 07 minimal vertical slice。审查方式为 sub agent 只读检查，不修改文件、不创建 commit。

## Findings

1. `src/repo_harness/evaluation/metrics.py`
   - 问题：`patch_apply_failed` 被映射为 `final_verifier_status = "error"`，随后 `run_outcome = "inconclusive"`。
   - 风险：strict patch replay 失败属于 final verifier 失败，应计为 `failed`，否则会低估不可应用补丁的失败。
   - 处理：已采纳。`patch_apply_failed` 现在派生为 `final_verifier_status = "failed"`，对应 `run_outcome = "failed"`，并增加测试。

2. `src/repo_harness/evaluation/runner.py`
   - 问题：`run_task` 在打开 `RunRecorder` 前直接删除已有 run directory。
   - 风险：绕过 RunRecorder 的 finalized-run 和 lock 保护，可能破坏已有 transcript、events 和 artifact manifest。
   - 处理：已采纳。已有 run directory 现在会让 `run_task` 抛出配置错误，要求使用新的 run id 或手动归档。

3. `src/repo_harness/tools/minimal.py`
   - 问题：Stage 07 permission shim 只特殊处理 `deny`，`plan` 和 `ask` 会继续允许非只读工具。
   - 风险：`plan` 模式可能写文件或运行测试，`ask` 模式没有非交互降级记录。
   - 处理：已采纳。`plan`、`ask`、`deny` 模式现在只允许只读工具；`ask` 对非只读工具写入 `requires_user_input = true` 和 `non_interactive_resolution = "deny"`。

4. `src/repo_harness/tasks/schemas.py`
   - 问题：`agent_visible_view()` 暴露原始 `repo_source` 路径。
   - 风险：模型可见 prepared messages 包含本地 fixture/source repository 路径，超过完成任务所需信息。
   - 处理：已采纳。模型可见任务投影移除了 `repo_source`；ContextBuilder 仍单独注入 agent workspace 根目录。

## Conclusion

审查未发现 Stage 07 明显提前实现后续大功能。未知工具没有进入 Permission System，已知工具在进入 Permission System 前有基本输入校验。上述问题均已处理，并重新运行阶段验证。
