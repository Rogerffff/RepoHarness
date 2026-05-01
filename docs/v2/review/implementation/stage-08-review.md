# Stage 08 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查 agent 没有修改文件。主流程根据审查结论修复了可以在 Stage 08 范围内完成的 P3 项。

## 审查重点

- 是否严格限于 Stage 08 的 `single_shot_patch` scaffold。
- 是否提前实现 Stage 09 `planner_coder_verifier`、Stage 10 mock provider 或 Stage 11 real provider。
- `single_shot_patch` 是否只接受单次 patch action，不允许普通工具调用。
- `single_shot_patch` 是否强制 `test_feedback_policy=disabled`。
- runtime config 显式请求其他测试反馈策略时是否失败。
- patch action parser 是否支持 replay patch action 和 fenced diff。
- patch parse failure 和 patch apply failure 是否结构化记录。
- patch apply 是否通过 Workspace Adapter 和 RunRecorder 边界。
- `run_tests` 请求是否在进入 Permission System 前被 scaffold policy 阻断，并生成配对 `ToolResult`。
- 是否泄漏 `expected_outcome`、脚本注释、hidden feedback、baseline/final verifier 信息到模型可见内容或训练导出。
- 是否缺少阶段验收测试。

## 审查发现

### P1

未发现。

### P2

未发现。

### P3

1. 缺少端到端 malformed patch parse failure 覆盖。
   - 原因：单元测试已经覆盖非 diff 解析失败，但集成测试还没有覆盖 run 级别的 `patch_action_parse_failed` 事件。
   - 处理：新增 `tests/fixtures/replays/task_001_single_shot_patch_malformed.yaml`，并在 `tests/integration/test_single_shot_patch.py` 中新增集成测试，断言 `patch_action_parse_failed`、不出现 `patch_apply_started`，且 formal final verifier 仍然运行。

2. 缺少 Stage 08 阶段日志。
   - 原因：实现完成时尚未写入 `docs/v2/implementation-log/stage-08.md`。
   - 处理：新增 `docs/v2/implementation-log/stage-08.md`。

## 审查正例证据

- `single_shot_patch` 没有开放普通模型可见工具，`allowed_tools=[]`。
- `single_shot_patch` 默认 `test_feedback_policy=disabled`。
- 显式请求非 `disabled` 的测试反馈会抛出 `ConfigError`。
- 单次补丁动作通过专用 Agent Loop 分支处理，不作为普通模型工具暴露。
- patch apply 通过 Workspace Adapter 执行。
- 事件覆盖 `patch_action_parsed`、`patch_action_parse_failed`、`patch_apply_started`、`patch_apply_completed` 和 `patch_apply_failed`。
- `run_tests` 工具调用在进入 Permission System 前被配对拒绝。
- replay model-visible payload 不包含 `expected_outcome` 和脚本注释。
- 未发现提前实现 Stage 09、Stage 10 或 Stage 11 的情况。

## 审查负例证据

- 非 diff 输出不会被当作有效 patch。
- patch apply 失败不会被误记为成功。
- runtime 显式请求 `oracle_hidden_feedback` 不会被自动降级为 `disabled`。
- `planner_coder_verifier` 仍不允许作为 Stage 08 ExperimentConfig scaffold。
- 空 tool schema snapshot 的 schema 放宽没有改变 `simple_react` 的默认工具顺序。

## 修复后验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_scaffold_single_shot_patch.py tests/integration/test_single_shot_patch.py -q
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

验证结果：

- Stage 08 定向测试通过，11 个测试通过。
- 编译通过。
- 全量测试通过，270 个测试通过。

## 结论

审查没有发现 P1 或 P2。P3 已在 Stage 08 范围内修复并重新验证。Stage 08 可以提交，并可以进入 Stage 09。
