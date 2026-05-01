# Stage 08: single_shot_patch scaffold

## 本阶段目标

本阶段目标是在 Stage 07 的 `ModelClient` 和 scaffold registry 基础上新增 `single_shot_patch` scaffold。该 scaffold 只允许模型输出一次 unified diff patch，由 Harness 内部解析并应用补丁，不允许模型调用普通工具，也不允许中间 `run_tests` 测试反馈。

## 本阶段实现内容

- 新增 `single_shot_patch` scaffold：
  - `scaffold_id=single_shot_patch`
  - `scaffold_version=repo_harness_single_shot_patch_v0`
  - `allowed_tools=[]`
  - `default_test_feedback_policy=disabled`
  - 单阶段 `patch` phase。
- 新增 patch action parser：
  - 支持 raw unified diff。
  - 支持 fenced `diff` 或 `patch` code block。
  - 解析 changed paths。
  - 非 diff、空输出、无 changed paths 均返回结构化失败。
- 扩展 replay script：
  - 新增 `action: patch_action`。
  - 支持 `patch_text` 字段。
  - replay provider 将 patch action 作为 assistant content 返回，不生成 tool call。
  - replay model-visible payload 继续排除 `expected_outcome` 和脚本注释。
- 修改 Agent Loop：
  - `single_shot_patch` 无 tool call 时走专用 patch action 分支。
  - patch text 写入 `single_shot_patch_action` artifact。
  - patch path 先通过 Workspace Adapter path resolver 校验。
  - patch apply 通过 Workspace Adapter 执行，不暴露为普通模型工具。
  - patch apply 结果写入 `single_shot_patch_apply_result` artifact。
  - 记录 `patch_action_parsed`、`patch_action_parse_failed`、`patch_apply_started`、`patch_apply_completed`、`patch_apply_failed` 事件。
  - 事件数据只包含 patch 摘要、hash、changed paths 和 artifact ref，不把完整 patch text 直接写入事件 data。
- 修改 scaffold policy：
  - `single_shot_patch` 的 effective `test_feedback_policy` 固定为 `disabled`。
  - runtime config 显式请求其他测试反馈策略时抛出 `ConfigError`，不做自动降级。
- 修改 tool schema snapshot schema：
  - 允许 `single_shot_patch` 生成空 tool schema snapshot。
  - 保持 `simple_react` 默认工具顺序不变。
- 修改 ExperimentConfig：
  - Stage 08 允许 `simple_react` 和 `single_shot_patch`。
  - `planner_coder_verifier` 仍被拒绝，留到 Stage 09。
- 修改 metrics test run 计数：
  - 只统计真实执行完成或超时的 `run_tests` tool result。
  - 被 scaffold 阻断的 `run_tests` 请求不计入 `test_run_count`。

## 修改的主要文件

- `src/repo_harness/scaffolds/single_shot_patch.py`
- `src/repo_harness/scaffolds/patch_action.py`
- `src/repo_harness/scaffolds/registry.py`
- `src/repo_harness/scaffolds/policies.py`
- `src/repo_harness/scaffolds/__init__.py`
- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/model_client/schemas.py`
- `src/repo_harness/model_client/replay.py`
- `src/repo_harness/run_metadata/schemas.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/evaluation/schemas.py`
- `tests/unit/test_scaffold_single_shot_patch.py`
- `tests/integration/test_single_shot_patch.py`
- `tests/unit/test_experiment_config.py`
- `tests/fixtures/replays/task_001_single_shot_patch_success.yaml`
- `tests/fixtures/replays/task_001_single_shot_patch_bad_patch.yaml`
- `tests/fixtures/replays/task_001_single_shot_patch_malformed.yaml`
- `tests/fixtures/replays/task_001_single_shot_patch_run_tests.yaml`
- `tests/fixtures/run_configs/v2/single_shot_patch_success.yaml`

## 生成的机器可读产物

阶段验收 smoke run 生成了：

- `runs/v2-stage08-smoke-20260501T195741Z/stage08-single-shot-success/run_config_facts.json`
- `runs/v2-stage08-smoke-20260501T195741Z/stage08-single-shot-success/run_metadata.json`
- `runs/v2-stage08-smoke-20260501T195741Z/stage08-single-shot-success/metrics.json`
- `runs/v2-stage08-smoke-20260501T195741Z/stage08-single-shot-success/events.jsonl`
- `runs/v2-stage08-smoke-20260501T195741Z/stage08-single-shot-success/artifacts.json`
- `runs/v2-stage08-smoke-20260501T195741Z/stage08-single-shot-success/final.patch`
- `runs/v2-stage08-smoke-20260501T195741Z/stage08-single-shot-success/final.diff`

该 smoke run 证明：

- `inspect-run` 可以读取 Stage 08 run。
- `scaffold_id=single_shot_patch`。
- `test_feedback_policy=disabled`。
- `feedback_tests_passed_policy=not_applicable`。
- `test_run_count=0`。
- `patch_action_parsed` 和 `patch_apply_completed` 均已记录。
- final verifier 状态为 `accepted`，run outcome 为 `success`。

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/v2/single_shot_patch_success.yaml --output-dir runs/v2-stage08-smoke-20260501T195741Z --run-id stage08-single-shot-success
PATH=.venv/bin:$PATH repo-harness inspect-run runs/v2-stage08-smoke-20260501T195741Z/stage08-single-shot-success
rg -n 'single_shot_patch|test_feedback_policy|feedback_tests_passed_policy|test_run_count|patch_apply_completed|patch_action_parsed' runs/v2-stage08-smoke-20260501T195741Z/stage08-single-shot-success/run_config_facts.json runs/v2-stage08-smoke-20260501T195741Z/stage08-single-shot-success/run_metadata.json runs/v2-stage08-smoke-20260501T195741Z/stage08-single-shot-success/metrics.json runs/v2-stage08-smoke-20260501T195741Z/stage08-single-shot-success/events.jsonl
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_scaffold_single_shot_patch.py tests/integration/test_single_shot_patch.py -q
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

## 验证结果

- Stage 08 smoke run 成功，`inspect-run` 显示 run metadata、run config facts 和 tool schema snapshot 均为 ok。
- Stage 08 定向测试通过，11 个测试通过。
- `python -m compileall src` 通过。
- 全量测试通过，270 个测试通过。

## 正例证据

- 成功路径：`task_001_single_shot_patch_success.yaml` 的 patch action 修复任务，formal final verifier accepted，run outcome 为 success。
- patch apply 失败路径：错误 context 的 patch 产生 `patch_apply_failed`，run outcome 为 failed，formal final verifier 仍然运行。
- patch parse 失败路径：非 diff 输出产生 `patch_action_parse_failed`，不会进入 `patch_apply_started`，formal final verifier 仍然运行。
- 工具阻断路径：模型请求 `run_tests` 时被 scaffold policy 阻断，生成配对 `ToolResult`，没有进入 Permission System，`test_run_count=0`。
- policy 失败路径：runtime 显式请求 `oracle_hidden_feedback` 时抛出 `ConfigError`。
- tool schema snapshot 路径：`single_shot_patch` 允许空 tool schema snapshot，`simple_react` 默认工具顺序仍由既有测试覆盖。
- replay payload 路径：`patch_action` 的 model-visible payload 不包含 `expected_outcome` 或脚本注释。

## 负例证据

- `single_shot_patch` 不允许普通模型工具调用。
- `single_shot_patch` 不允许中间 `run_tests` feedback。
- `single_shot_patch` 不允许 runtime config 请求非 `disabled` 的测试反馈策略。
- 非 unified diff 不会被当作可应用 patch。
- patch apply 失败不会被误记为成功。
- Stage 08 仍拒绝 `planner_coder_verifier`，没有提前实现 Stage 09。
- Stage 08 没有实现 mock provider、DeepSeek provider、OpenAI provider 或 provider artifact；这些属于 Stage 10 和 Stage 11。

## 允许降级项

- patch parser 是最小 unified diff parser，只负责识别 patch action、提取 changed paths 并交给 Workspace Adapter 应用。
- Stage 08 不实现 patch repair、tree search、自动重试或多候选 patch。
- Stage 08 不新增任务集、不新增真实 provider、不新增 Docker backend。

## 禁止降级项

- 不能把 `single_shot_patch` 实现成普通工具调用 scaffold。
- 不能允许中间 `run_tests` 或通过 bash 测试命令绕过 `test_feedback_policy=disabled`。
- 不能在 runtime 显式请求非 `disabled` 测试反馈策略时自动降级。
- 不能绕过 Workspace Adapter 应用补丁。
- 不能绕过 RunRecorder 写 patch action、patch apply result 或 patch events。
- 不能把 `ReplayScript.expected_outcome`、脚本注释、hidden feedback、baseline/final verifier 信息放进模型可见内容或训练导出。
- 不能提前实现 Stage 09、Stage 10 或 Stage 11 能力。

## 已知限制

- patch parser 只做 Stage 08 所需的最小 unified diff 解析，不做复杂修复。
- `single_shot_patch` 只有单阶段 `patch` phase。
- `single_shot_patch` 的内部 patch result transcript 是模型可见但不可训练的结构化结果；当前 max_turns smoke 配置为 1，因此不会再进入第二轮模型请求。
- Stage 08 不实现 planner/coder/verifier；该能力属于 Stage 09。

## 是否偏离设计文档

未发现需要记录的设计冲突。本阶段按文档要求新增 `single_shot_patch`，并保持 patch apply 为 scaffold 内部结构化 action。为了不把完整 patch text 放进事件 data，事件只记录摘要和 artifact reference；完整 patch text 保存在 RunRecorder artifact 中。

## sub agent 审查结论

已安排只读 sub agent 审查。审查没有发现 P1 或 P2。

审查发现 2 个 P3：

- 缺少端到端 malformed patch parse failure 覆盖。
- 缺少 Stage 08 阶段日志。

上述 P3 均已处理：

- 新增 `task_001_single_shot_patch_malformed.yaml` 和集成测试，覆盖 `patch_action_parse_failed`。
- 新增本阶段日志和审查记录。

审查记录保存到 `docs/v2/review/implementation/stage-08-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 09。进入下一阶段前，Stage 08 commit 必须只包含当前阶段相关代码、测试、fixture、阶段日志和审查记录。
