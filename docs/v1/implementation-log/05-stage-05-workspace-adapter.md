# Stage 05: Workspace Adapter And Local Execution Boundary

## Scope

本阶段实现了：

- `LocalWorkspaceAdapter`，负责本地 source checkout、setup workspace、agent workspace 和 verification workspace 生命周期。
- `DependencyState` 的第一版策略支持：`none` 和 `rerun_setup`。
- 工作区路径解析和边界检查：
  - 拒绝 `..` 越界。
  - 拒绝指向 workspace 外部的符号链接。
  - 拒绝 `.git/`、`.env`、私钥、证书和 key 文件等敏感路径。
- 本地命令执行：
  - 独立进程组。
  - timeout 后终止进程组。
  - stdout/stderr preview。
  - 可通过 `RunRecorder.write_artifact()` 保存完整命令输出。
- agent start snapshot：
  - 在 agent workspace 内初始化本地 git baseline。
  - 写入 `.git/info/exclude`，排除测试缓存和构建产物。
- `final.patch` 和 `final.diff` 捕获：
  - 以 agent start snapshot 为基线。
  - 支持普通文本文件新增、修改和删除。
- verification workspace：
  - 从干净 source checkout 重建。
  - 恢复 dependency state。
  - 初始化相同 baseline。
  - 应用冻结后的 `final.patch`。
- 工作区相关单元测试和集成测试。

本阶段明确不实现：

- 不实现 verifier parser 或 accepted policy。
- 不实现 Tool System 或 Permission System。
- 不实现 Agent Loop。
- 不实现 Eval Runner 对 baseline/final verifier 的编排。
- 不声称本地进程模式提供操作系统级安全沙箱或完整网络隔离。

## Design References

- `docs/v1/implementation-plan.md`
- `docs/05-workspace-sandbox-and-permissions.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/08-trajectory-store-and-training-export.md`

## Files Changed

- `src/repo_harness/workspace/adapter.py`
- `src/repo_harness/workspace/__init__.py`
- `tests/unit/test_workspace_paths.py`
- `tests/integration/test_workspace_lifecycle.py`

## Verification

运行的命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_workspace_paths.py tests/integration/test_workspace_lifecycle.py
PATH=.venv/bin:$PATH python -m pytest
PATH=.venv/bin:$PATH python -m compileall src
```

结果：

- 通过。
- workspace 相关测试收集并通过 10 个测试。
- 全量测试收集并通过 59 个测试。
- `compileall` 通过。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查。

关键审查意见：

- `final.patch` / `final.diff` 最初使用当前 `HEAD` 作为 diff 基线，而不是 `RunWorkspace.agent_start_snapshot`。
- `run_command()` 最初只检查 cwd 存在，没有强制 cwd 位于当前 run directory 的 `workspaces/` 下。
- stdout/stderr artifact 保存最初是可选的，可能让命令执行事实绕过 `RunRecorder`。
- `final.patch` / `final.diff` 最初直接写根目录文件，没有进入 artifact manifest。
- 内部 git 命令最初没有 timeout，也没有 stdout/stderr artifact 记录。
- 建议补充 `rerun_setup` 在 agent workspace 和 verification workspace 中恢复依赖状态的测试。

处理结果：

- 采纳：`capture_final_patch()` 改为使用 `run_workspace.agent_diff_base` 或 `agent_start_snapshot` 作为 diff 基线，测试覆盖 agent 期间 `HEAD` 移动后仍能捕获完整 patch。
- 采纳：`resolve_workspace_path()` 和 `run_command()` 都要求 workspace 位于当前 run directory 的 `workspaces/` 下。
- 采纳：`run_command()` 和 `apply_patch()` 要求提供 `RunRecorder`，并保存完整 stdout/stderr artifact。
- 采纳：`capture_final_patch()` 继续写出根目录契约文件 `final.patch` 和 `final.diff`，同时通过 `RunRecorder.write_artifact()` 写入 manifest 可追踪副本。
- 采纳：内部 git 命令改为走 adapter 内部受控 helper，设置 timeout，并在有 recorder 时保存 git stdout/stderr artifact。
- 采纳：新增测试覆盖 cwd 越界拒绝、manifest 中 final patch/diff artifact、`HEAD` 移动后基线稳定、`rerun_setup` 恢复 agent 和 verification workspace。

## Known Limitations

- 第一版只实现本地进程工作区边界，不是生产级安全沙箱。
- Docker-based executable repository environment 未实现。
- `copy_declared_paths` 和 `docker_image_layer` dependency strategy 未实现。
- 命令安全策略仍属于后续 Permission System；本阶段只保证命令在指定 workspace cwd 内执行并有 timeout。
- 二进制文件和符号链接 diff 当前没有单独统计或细分错误类型，后续工具和 patch policy 阶段需要进一步收紧。

## Commit

- Commit: `stage 05: implement workspace lifecycle`
- Commit message: `stage 05: implement workspace lifecycle`
