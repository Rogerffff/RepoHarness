# Stage 08 Read-Only Review

## Scope

本审查针对 RepoHarness 第一版 Stage 08 tool and permission system。审查方式为 sub agent 只读检查，不修改文件、不创建 commit。

## Findings

1. `src/repo_harness/permissions/system.py`
   - 问题：`bash` allowlist 按命令名允许 `ls`、`find`，但没有解析路径参数。因为 Workspace Adapter 使用 `shell=True` 执行原始命令，`ls /`、`ls $HOME`、`find /` 可能读取 workspace 外信息。
   - 处理：已采纳。`bash` 安全检查现在拒绝 `$`、`~`、后台任务等 shell 语法，并对 `ls`、`find` 的路径参数调用 Workspace Adapter 路径解析；测试覆盖 `ls /`、`ls $HOME` 和 `find /`。

2. `src/repo_harness/tools/minimal.py`
   - 问题：pytest 路由发生在 shell 安全拒绝之前，且使用 `startswith`，导致 `pytest -q | tee out.txt`、`pytest -q > out.txt`、`pytest -q &` 会被路由成 `run_tests`。
   - 处理：已采纳。pytest 路由现在先检查危险 shell 语法，再用 `shlex.split` 判断测试命令；新增真实 Agent Loop 测试覆盖危险 pytest shell 语法拒绝。

3. `src/repo_harness/tools/minimal.py`
   - 问题：`bash.cwd` 在 normalize 阶段解析，越界时会在 Permission System 之前抛出异常，导致缺少 `PermissionDecision` 和配对 `ToolResult`。
   - 处理：已采纳。normalize 不再解析 cwd；cwd 解析交给 Permission System。新增端到端测试确认 cwd 越界会写 deny decision 和配对 ToolResult。

4. `src/repo_harness/tools/minimal.py`
   - 问题：`grep` Python fallback 只解析 root，随后直接 `path.read_text`，可能读取敏感文件或跨 workspace 符号链接。
   - 处理：已采纳。fallback 对每个候选文件使用 Workspace Adapter `read_text()`，敏感路径和越界符号链接会被拒绝；新增测试确认 `.env` 内容不会进入结果。

5. `src/repo_harness/workspace/adapter.py`
   - 问题：命令环境使用完整 `os.environ.copy()`，可能让被测代码读取宿主密钥。
   - 处理：已采纳。命令环境改为最小 allowlist，只保留路径、临时目录和 locale 等必要字段，并显式设置 Python 编码相关变量。

6. `src/repo_harness/evaluation/runner.py`
   - 问题：summary 没有复盘权限拒绝原因。
   - 处理：已采纳。AgentLoopState 记录权限拒绝原因，summary 写出 `permission_denial_count` 和去重后的前若干条原因；测试覆盖安全负例 summary。

7. 测试覆盖不足。
   - 问题：缺少真实 Agent Loop 路径下的危险 pytest shell 语法拒绝测试，以及大 stdout artifact / preview 测试。
   - 处理：已采纳。新增端到端危险 pytest shell 语法测试、cwd 越界配对测试、大 stdout artifact 测试。

## Conclusion

审查发现的阻断问题均已处理，并重新运行阶段八指定测试和全量测试。
