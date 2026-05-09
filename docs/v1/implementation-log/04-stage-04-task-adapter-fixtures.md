# Stage 04: Task Adapter And Micro-Repo Fixtures

## Scope

本阶段实现了：

- `TaskAdapter` 和 `load_task()`，负责读取 YAML、校验 schema、规范化 fixture repo 路径，并输出 `TaskDefinition`、`RunnableTask` 和静态 `VerifierConfig`。
- `repo-harness validate-task <task_path>`，只做静态校验，不创建 workspace、不运行测试。
- 6 个可静态校验的 micro-repo task：
  - `task_001.yaml`：Python 计算类 bug。
  - `task_002.yaml`：多文件导入/配置 bug。
  - `task_003_create_file.yaml`：需要新增文件的任务。
  - `task_security_probe.yaml`：后续权限拒绝和安全负例 replay 使用。
  - `task_invalid_baseline.yaml`：后续 baseline 质量门控 invalid fixture。
  - `task_flaky.yaml`：后续 deterministic flaky simulator fixture。
- 1 个故意错误任务 `task_bad_visibility.yaml`，用于验证静态 schema 会拒绝公开 `gold_patch`。
- 3 个 replay fixture YAML：
  - 成功 replay。
  - 失败 replay。
  - 安全负例 replay，覆盖 workspace 外读取、`.env` 读取、`curl` 和 `git fetch` 请求。
- `tests/unit/test_task_adapter.py`，覆盖 fixture 任务加载、路径边界、当前工作目录无关性、模型可见投影泄漏检查、CLI 成功和失败、replay schema 校验。
- pytest 配置排除 `tests/fixtures/repos`，避免项目自身测试直接收集 micro-repo 内部测试。

本阶段明确不实现：

- 不创建 source checkout、setup workspace、agent run workspace 或 verification workspace。
- 不运行 micro-repo 测试。
- 不生成 `BaselineResult`。
- 不执行 replay。
- 不实现权限系统、工具系统或 verifier。

## Design References

- `docs/v1/implementation-plan.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/06-task-dataset-and-environment-adapters.md`

## Files Changed

- `src/repo_harness/tasks/adapter.py`
- `src/repo_harness/tasks/__init__.py`
- `src/repo_harness/cli/main.py`
- `pyproject.toml`
- `tests/fixtures/repos/...`
- `tests/fixtures/tasks/...`
- `tests/fixtures/replays/...`
- `tests/unit/test_task_adapter.py`

## Verification

运行的命令：

```bash
PATH=.venv/bin:$PATH repo-harness validate-task tests/fixtures/tasks/task_001.yaml
for task in tests/fixtures/tasks/task_001.yaml tests/fixtures/tasks/task_002.yaml tests/fixtures/tasks/task_003_create_file.yaml tests/fixtures/tasks/task_security_probe.yaml tests/fixtures/tasks/task_invalid_baseline.yaml tests/fixtures/tasks/task_flaky.yaml; do PATH=.venv/bin:$PATH repo-harness validate-task "$task" >/dev/null || exit 1; done
PATH=.venv/bin:$PATH repo-harness validate-task tests/fixtures/tasks/task_bad_visibility.yaml
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_task_adapter.py
PATH=.venv/bin:$PATH python -m pytest
PATH=.venv/bin:$PATH python -m compileall src
```

结果：

- 有效 fixture task 全部通过 `validate-task`。
- `task_bad_visibility.yaml` 按预期失败，错误指出 `gold_patch` 必须是 `hidden_reference`。
- `tests/unit/test_task_adapter.py` 收集并通过 20 个测试。
- 全量测试收集并通过 49 个测试。
- `compileall` 通过。

调试记录：

- 引入 micro-repo fixture 后，全量 pytest 曾直接收集 `tests/fixtures/repos/**/tests`，导致 fixture 内部测试在错误工作目录下导入失败。
- 根因是项目自身测试配置没有排除 micro-repo fixture。
- 处理方式是在 `pyproject.toml` 增加 `norecursedirs = ["tests/fixtures/repos"]`，让 micro-repo 测试只在后续 Workspace/Verifier 阶段由任务工作区运行。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查。

关键审查意见：

- `TaskAdapter._resolve_repo_path()` 原先通过当前工作目录计算 `tests/fixtures/repos`，从仓库外调用绝对任务路径时会拒绝合法任务。
- 工作区中有用户要求不要主动提交的未跟踪历史文档，后续提交必须继续显式暂存文件。
- micro-repo fixture 目录中残留 `__pycache__` 和 `.pyc` 缓存文件，虽然不会被 Git 跟踪，但会让 fixture 目录不够干净。
- 建议增加有效 fixture 的模型可见投影批量泄漏测试。

处理结果：

- 采纳：Task Adapter 改为从任务文件路径向上定位 `fixtures/repos` 根目录，不再依赖调用进程当前工作目录。
- 采纳：增加从临时当前工作目录加载绝对 task path 的回归测试。
- 采纳：增加所有有效 fixture 的 `agent_visible_view()` 批量泄漏测试，确认不包含 `gold_patch`、fail/pass 测试列表和 decontamination 字段。
- 采纳：清理 fixture repo 目录中的 `__pycache__` 和 `.pyc` 缓存文件。
- 采纳：继续使用显式路径暂存，避免误纳入 `docs/build-your-own/` 和旧 review 文件。

## Known Limitations

- Task Adapter 当前只允许本地 fixture repo 路径位于 `tests/fixtures/repos` 内；未来真实仓库 adapter 会在后续版本扩展。
- Task Adapter 只做静态路径和 schema 校验，不证明任务 baseline 有效。
- replay fixture 只做 schema 校验，不在本阶段执行。
- invalid 和 flaky fixture 本阶段可以通过静态校验；它们的质量门控行为在后续 verifier 和 eval runner 阶段实现。

## Commit

- Commit: `stage 04: add task adapter and fixtures`
- Commit message: `stage 04: add task adapter and fixtures`
