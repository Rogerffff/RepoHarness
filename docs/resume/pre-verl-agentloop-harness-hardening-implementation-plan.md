# Pre-Verl AgentLoop Harness Hardening Implementation Plan

本文档记录正式二十三题 SWE-Bench Lite development instances 测评前，RepoHarness AgentLoop 主链路需要完成的修复实施计划。目标不是提升模型本身能力，而是避免因为 Harness 的上下文、工具、权限、轨迹或者审计实现问题，低估模型在正式测评中的表现。

本文档明确排除 Claude Code 中的 `snip`、`microcompact`、`autocompact`、`context collapse` 等多层上下文压缩能力。它们可以作为后续版本增强，不作为本次正式测评前的阻塞项。但是，和上下文审计、工具调用配对、模型可见输入复核、工具输出截断恢复有关的问题，仍然必须在正式测评前修复。

## 1. 总目标

正式二十三题测评开始前，RepoHarness 至少需要满足以下条件：

1. 模型看到的任务上下文、工具说明、工具返回结果和最终 `final.patch` 都可以从运行产物中完整审计。
2. 模型没有看到 hidden test patch、hidden test selector、gold patch、final verifier 原始输出等 evaluator-only 材料。
3. 工具系统不会因为不清晰、不完整或者不一致的接口设计，让模型明明可能修对，却因为工具不可用、误导性提示、输出被截断后无法恢复、命令被隐藏规则拒绝等 Harness 问题而失败。
4. `bash` 即使不在 formal final-only baseline 中开放，也必须具备清晰、可审计、可测试的安全策略，避免后续 scaffold comparison 或 diagnostic baseline 一旦打开 `bash` 就引入不可信结果。
5. 所有正式测评结果必须能区分以下几类失败：
   - 模型确实修错。
   - 模型没有产出可应用补丁。
   - 模型因为轮次、工具调用次数或者超时预算耗尽而没有完成。
   - 工具、上下文、Provider 协议、Docker 环境或者 final verifier 链路出现 Harness 问题。

## 2. 优先级定义

- `P0`：不修复就不能进入正式二十三题测评，因为它会直接污染 accepted rate 或让非正式链路混入正式结果。
- `P1`：强烈建议正式测评前修复，因为它有较大概率让模型失败被误判为模型能力不足。
- `P2`：建议正式测评前修复，因为它会显著降低审计质量、复现实验质量或者后续扩展质量。
- `P3`：可以在正式测评后继续优化，不影响本轮 accepted rate 的可信边界。

## 3. 非目标

本轮不实现以下能力：

1. Claude Code 风格的 `snip`。
2. Claude Code 风格的 `microcompact`。
3. Claude Code 风格的 `autocompact`。
4. Claude Code 风格的 `context collapse`。
5. 长上下文多层摘要和自动恢复策略。

这些能力的缺失需要在最终报告中作为已知限制说明，但不应阻塞本轮正式测评。原因是二十三题 SWE-Bench Lite development instances 可以先通过较保守的工具输出限制、分页读取、明确截断恢复提示和更高轮次预算来保证基本公平性。

## 4. 当前 Bash 实现是否存在问题

结论：当前 `bash` 不是完全错误的实现，但存在必须在正式测评前修复或者验证清楚的问题。不能因为 formal final-only baseline 暂时不开放 `bash` 就推迟这些修复。

当前实现已经具备一些好的基础：

1. `src/repo_harness/permissions/system.py` 中的 `_deny_reason_for_bash` 已经拒绝了管道、重定向、命令组合、反引号、变量展开、换行、后台执行等危险 shell 语法。
2. 只允许一小组诊断命令，例如 `pwd`、`ls`、部分只读 `git` 命令、`ruff`、`mypy`、`python -m compileall`。
3. `curl`、`wget`、`ssh`、`scp`、`sudo`、`rm`、`find` 等命令被拒绝。
4. `ToolExecutor.normalize()` 会把和配置测试命令完全匹配的 `bash` 请求路由到 `run_tests`。

但是目前仍然有七个主要问题。

### 4.1 Bash 允许规则对模型不够可见

模型只能看到“这是受限诊断命令”这样的说明，但不能稳定知道哪些命令可以用、哪些命令一定会被拒绝。

一个简单例子：

```text
模型想查看当前仓库状态。
模型调用 bash: git status --short
这个命令可能被允许。

模型想搜索文件。
模型调用 bash: find . -name "*.py"
这个命令会被拒绝。
```

如果工具说明没有明确写出 `find` 被禁止，并且应该改用 `list_files` 或 `grep`，模型就会浪费一次工具调用。正式测评中，这类浪费会变成预算压力，特别是复杂任务接近 `max_turns` 时会影响结果。

修复要求：

1. `bash` 工具描述必须列出允许命令类别和典型示例。
2. `bash` 拒绝结果必须告诉模型可替代工具。例如 `find` 被拒绝时，提示使用 `list_files`；`grep` 命令被拒绝时，提示使用 `grep` 工具。
3. formal budget freeze manifest 必须记录 `bash_policy_version` 和实际暴露给模型的 `bash` 工具说明哈希。

### 4.2 Bash 命令策略存在两条路径，容易漂移

当前至少有两处逻辑会影响 `bash`：

1. `src/repo_harness/permissions/system.py` 中的 `_deny_reason_for_bash`。
2. `src/repo_harness/tasks/command_policy.py` 中的 `evaluate_model_bash_command`。

一个简单例子：

```text
任务配置里公开测试命令是 python -m pytest tests/test_public.py。
formal final-only baseline 要求 test_feedback_policy=disabled。

如果模型调用 bash: python -m pytest tests/test_public.py
```

正确结果应该是：拒绝，原因是 final-only 任务不能给模型测试反馈。

如果只有 `ToolExecutor.normalize()` 做字符串完全匹配，那么模型稍微换一种写法，例如：

```text
python -m pytest -q tests/test_public.py
```

就可能绕开精确匹配，进入普通 `bash` 权限判断。虽然当前 `bash` allowlist 可能仍会拒绝它，但这个拒绝原因就不再是“测试反馈策略禁止”，而是“命令不在 allowlist”。这会让失败归因不准确，也会让后续打开 structured public feedback 时出现策略漂移。

修复要求：

1. `bash` 的测试命令判断必须统一调用 `evaluate_model_bash_command`。
2. `PermissionSystem` 不应该自己维护一套和任务测试可见性无关的测试命令判断。
3. `pytest`、`tox`、`nox`、`python -m pytest`、`python -m unittest` 等测试命令必须被统一识别。
4. 当 `test_feedback_policy=disabled` 时，所有测试类命令都必须被拒绝，并返回明确原因。
5. 当 `test_feedback_policy=structured_public_feedback` 且命令被任务定义标记为 public 时，应该路由到 `run_tests`，而不是走普通 `bash`。

### 4.3 Bash 执行语义需要证明不是通用 shell

`src/repo_harness/tools/minimal.py` 中 `_bash()` 当前把 `command` 字符串传给 `workspace_adapter.run_command()`。虽然权限层禁止了常见危险 shell 语法，但正式评测前仍然要确认执行层没有使用不受控的 `shell=True` 或等价通用 shell 拼接。

一个简单例子：

```text
模型调用 bash: git status --short
```

合理实现是把它解析成类似下面的结构化参数：

```text
argv = ["git", "status", "--short"]
cwd = "/workspace"
```

风险实现是：

```text
shell=True command="git status --short"
```

即使权限层已经拦截了大部分危险字符，正式测评链路仍然需要把执行语义审计清楚，因为这是可审计 Harness 的基本边界。

修复要求：

1. 检查 local process 和 Docker workspace adapter 的 `bash_diagnostic` 执行路径。
2. 如果当前是 shell 字符串执行，改成 `shlex.split()` 后的 argv 执行，并保留严格 quoting 限制。
3. 如果必须使用 shell，需要在 run metadata 中标记 `shell_execution=true`，并阻止 formal baseline 使用该模式。
4. 新增 inspect，要求 formal run 的 `bash` 执行记录必须包含 `argv`、`cwd`、`policy_decision`、`command_category` 和 `timeout_sec`。

### 4.4 Bash 输出和拒绝结果缺少结构化归因字段

当前模型可能只看到普通错误文本。正式评测需要把命令拒绝、命令路由、命令超时和命令执行失败区别开。

一个简单例子：

```text
模型调用 bash: python -m pytest tests/test_public.py
```

正确的工具结果应该类似：

```json
{
  "status": "denied",
  "command_category": "test_command",
  "policy_decision": "denied_by_final_only_feedback_policy",
  "recovery": "This task does not expose tests to the model. Use read_file, grep, edit_file, and git_diff instead."
}
```

而不是只返回：

```text
Command denied.
```

修复要求：

1. `bash` 工具结果增加结构化字段。
2. `tool_result`、event log、artifact manifest 和 export diagnostic view 都要保留这些字段。
3. inspect 能统计 `bash` 被拒绝的原因分布。

### 4.5 Bash timeout 和输出上限需要进入 formal budget freeze

如果正式 baseline 不开放 `bash`，也要在 manifest 中明确记录 `bash` 未开放。如果后续 scaffold comparison 开放 `bash`，必须把 timeout 和输出上限冻结。

修复要求：

1. formal budget freeze manifest 增加 `bash.enabled`、`bash.policy_version`、`bash.command_timeout_sec`、`bash.max_output_chars`。
2. scaffold comparison 如果打开 `bash`，必须使用新的 baseline id。
3. inspect 拒绝没有记录 `bash` 冻结信息的 formal run。

### 4.6 Bash 工具 schema 太通用

当前 schema 只有 `command`、`cwd`、`timeout_sec` 这类通用字段。模型不知道应该把 `bash` 当成“受限诊断工具”，还是当成普通 shell。

修复要求：

1. provider tool schema 的 description 中写清楚 `bash` 不是通用 shell。
2. schema 增加 `allowed_command_families` 或在 tool description 中稳定列出允许命令族。
3. 工具 prompt 中写明：读文件用 `read_file`，搜索用 `grep`，测试反馈用 `run_tests`，查看差异用 `git_diff`，不要用 `bash` 替代这些专用工具。

### 4.7 Bash 必须有独立 smoke

formal final-only baseline 不开放 `bash`，但正式评测前仍要跑一个非 formal 的 `bash` hardening smoke。

修复要求：

1. 使用 mock provider 或 replay provider 构造 `bash` 工具调用。
2. 覆盖允许命令、危险命令、测试命令、路径越界、超时和输出截断。
3. 该 smoke 不进入正式 accepted rate，只作为 Harness readiness evidence。

## 5. Stage 0：轻量记录当前状态

优先级：`P3`

实施目标：

1. 记录开始实施 hardening 前的代码提交、已有 smoke 目录、当前正式测评计划文档路径和当前未解决问题列表。
2. 明确当前已有 smoke 只是修复前参考，不是正式二十三题 baseline，也不能作为修复后的 readiness 证据。
3. 不在这个阶段新增正式 freeze manifest，也不阻塞功能修复开始。

建议修改文件：

1. 可以只更新执行记录文档或者 implementation log。
2. 如果执行 agent 已经有清晰的任务日志，也可以不改代码、不新增命令。

验收标准：

1. 能从记录中看出 hardening 开始时的 commit 和已有 smoke 产物路径。
2. 记录中明确写明：后续正式测评前必须重新跑 smoke，并重新生成正式 freeze manifest。
3. 本阶段不作为正式二十三题测评的 hard gate。

## 6. Stage 1：工具系统修复

### 6.1 Grep 工具支持正则表达式和可恢复分页

优先级：`P1`

当前问题：

`grep` 当前是字面量搜索，不是正则表达式搜索。模型常常自然地输入正则表达式样式的查询，例如：

修复方案：

1. `grep` schema 增加 `mode` 字段，取值为 `literal` 或 `regex`。
2. 默认保持 `literal`，避免破坏历史行为。
3. 如果 `mode=literal` 且查询字符串包含明显正则表达式字符，并且结果为空，工具结果返回恢复提示，建议模型改用 `mode=regex`。
4. 增加 `glob`、`max_matches`、`offset` 和 `context_lines` 字段。
5. 工具结果必须包含 `truncated`、`next_offset`、`searched_file_count`、`matched_file_count`、`skipped_hidden_count`。
6. 优先使用 `rg`，如果 `rg` 不可用则回退到 Python 实现。

建议修改文件：

1. `src/repo_harness/tools/minimal.py`
2. `src/repo_harness/tools/schema.py` 或当前工具 schema 定义所在文件
3. `tests/unit/test_tools_minimal.py`
4. `tests/integration/test_agentloop_tool_schema_snapshot.py`

验收标准：

1. literal 查询仍然通过。
2. regex 查询可以找到跨行内单行模式匹配。
3. 非法 regex 不会让工具崩溃，而是返回模型可见的工具错误。
4. 隐藏目录、虚拟环境目录和 evaluator-only 目录不会被搜索。
5. 截断结果可以通过 `offset` 恢复。
6. tool schema snapshot 和 runtime 行为一致。
7. Docker 镜像没有 `rg` 时，Python fallback 的可见结果和 `rg` 路径一致，不能因为镜像缺少 `rg` 让搜索能力静默下降。

### 6.2 Read File 返回行号、哈希和截断恢复信息

优先级：`P1`

当前问题：

模型读取文件后，如果没有稳定行号和内容哈希，后续使用 `edit_file` 做精确替换时容易复制错上下文。大型文件被截断时，模型也不一定知道应该从哪一行继续读。

一个简单例子：

```text
模型读取 src/foo.py 的前 200 行。
工具只返回纯文本。
模型看到 def parse(...):，但不知道它在第几行。
模型后续想继续读取函数下半部分，只能猜 start_line。
```

修复方案：

1. `read_file` 返回内容时带行号，例如 `42 | return value`。
2. 工具结果增加 `path`、`start_line`、`end_line`、`total_lines`、`content_sha256`、`truncated`、`next_start_line`。
3. 如果文件过大，截断提示必须告诉模型下一次应该调用 `read_file(path=..., start_line=...)`。
4. 行号只作为显示前缀，不应该要求模型把行号复制进 `edit_file.old_text`。
5. 工具结果需要同时保留“带行号展示内容”和“可复制原文片段”的边界，避免模型把行号前缀复制进 `edit_file.old_text` 后导致精确替换失败。
6. 如果 `edit_file.old_text` 明显包含 `42 | ` 这样的行号前缀，`edit_file` 应返回明确恢复提示，告诉模型重新复制不带行号的原文。

建议修改文件：

1. `src/repo_harness/tools/minimal.py`
2. `tests/unit/test_tools_minimal.py`
3. `tests/integration/test_export_from_run.py`

验收标准：

1. 范围读取、完整读取和越界读取都有稳定结果。
2. 大文件截断后给出 `next_start_line`。
3. transcript 和 tool artifact 能审计模型实际看到的文件片段。
4. hidden path 仍然不可读。
5. 模型把行号前缀误复制进 `edit_file.old_text` 时，工具不会静默失败，而是返回可恢复错误。

### 6.3 Edit File 增加内容哈希和重复替换保护

优先级：`P1`

当前问题：

`edit_file` 是精确文本替换工具。如果文件内容已经变化，或者 `old_text` 在文件中出现多次，模型可能误改错误位置。

一个简单例子：

```python
def normalize(value):
    return value.strip()

def normalize_name(value):
    return value.strip()
```

如果模型只替换：

```text
return value.strip()
```

它可能改到两个位置，或者工具拒绝重复匹配后模型不知道怎么恢复。

修复方案：

1. `edit_file` schema 使用当前实现已有的 `expected_content_hash` 作为 canonical 字段，字段值是文件内容 sha256。若为了兼容历史文档保留 `expected_content_sha256`，它只能作为 alias，并且必须在 tool schema snapshot 中明确。
2. `edit_file` schema 明确 `replace_all=false` 是默认行为。
3. 当 `old_text` 出现多次时，工具返回结构化错误，要求模型读取更大的上下文后再替换。
4. 当 `expected_content_hash` 不匹配时，工具返回 stale file 错误，要求模型重新读取文件。
5. provider tool schema 必须完整暴露这些字段。

建议修改文件：

1. `src/repo_harness/tools/minimal.py`
2. `src/repo_harness/model_client/providers/common.py`
3. `tests/unit/test_provider_client.py`
4. `tests/unit/test_tools_minimal.py`

验收标准：

1. provider request 中的 tool schema 包含 `expected_content_hash` 和 `replace_all`。
2. stale hash 会被拒绝，并有恢复提示。
3. 重复 old text 会被拒绝，并有恢复提示。
4. 正常单点替换仍然兼容旧调用。

### 6.4 统一工具输出上限

优先级：`P1`

当前问题：

工具 schema snapshot 可能声明一个输出上限，但 runtime 实际使用另一个输出上限。这样会导致 formal budget freeze manifest 和真实运行不一致。

一个简单例子：

```text
manifest 记录 grep max_output_chars=4000。
runtime 实际允许 12000。
```

这会让正式测评预算不可复核。不同运行之间即使命令相同，模型实际看到的上下文量也不同。

修复方案：

1. 定义统一字段 `resolved_max_output_chars`。
2. 工具 schema snapshot、runtime tool executor、tool artifact 和 formal budget freeze manifest 都使用这个 resolved 值。
3. inspect 比较 schema snapshot 和 runtime event，发现不一致就失败。

建议修改文件：

1. `src/repo_harness/tools/minimal.py`
2. `src/repo_harness/agent_loop.py` 或实际 AgentLoop 模块
3. `src/repo_harness/pre_verl_agentloop.py`
4. `tests/integration/test_pre_verl_agentloop_runtime.py`

验收标准：

1. 工具输出超过上限时被截断，并返回恢复提示。
2. manifest 和 runtime event 的输出上限完全一致。
3. formal inspect 可以发现输出上限漂移。

### 6.5 List Files 增加分页和噪声控制

优先级：`P2`

当前问题：

大型仓库中 `list_files` 可能返回大量测试 fixture、数据文件或者依赖目录。模型会在文件列表噪声中浪费上下文。

一个简单例子：

```text
模型想找 pydicom 的核心像素处理代码。
list_files 一次返回几百个文件，其中包含大量测试数据。
模型需要在很长列表中自己猜哪些文件有用。
```

修复方案：

1. `list_files` 增加 `max_entries`、`offset`、`glob` 和 `kind` 字段。
2. 工具结果增加 `truncated`、`next_offset`、`returned_count`、`total_visible_count`、`skipped_hidden_count`。
3. 默认仍然不隐藏源码和测试文件，但虚拟环境、构建产物、`.git`、`.pre_verl_venv` 等目录必须排除。
4. 工具提示中说明可以先用 `grep` 搜索符号，再用 `read_file` 精读相关文件。

建议修改文件：

1. `src/repo_harness/tools/minimal.py`
2. `tests/unit/test_tools_minimal.py`

验收标准：

1. 大文件列表可分页。
2. excluded directories 不会出现在模型可见输出中。
3. 输出截断时给出下一页调用参数。

### 6.6 Git Diff 增加截断恢复和变更文件摘要

优先级：`P1`

当前问题：

`patch_focused_react` formal baseline 会开放 `git_diff`。如果模型修改很多文件，`git_diff` 输出可能被截断。模型此时可能看不到自己引入的错误改动，也无法知道应该查看哪个文件的差异。

一个简单例子：

```text
模型修改了 src/parser.py 和 tests/test_parser.py。
git_diff 只返回前半段 diff，并且被截断在 src/parser.py 中间。
模型没有看到 tests/test_parser.py 的新增内容。
```

如果模型在正式 final-only baseline 中误改了测试文件，或者补丁里包含明显无关改动，`git_diff` 截断会降低模型自我检查能力，也会降低审计质量。

修复方案：

1. `git_diff` 工具结果增加 `changed_files` 摘要，包含文件路径、状态、增加行数、删除行数。
2. 工具结果增加 `truncated`、`resolved_max_output_chars`、`diff_sha256` 和 `recovery_hint`。
3. schema 增加可选 `path` 字段，允许模型按单个文件查看 diff。
4. 如果整体 diff 被截断，恢复提示必须告诉模型可以调用 `git_diff(path=...)` 查看单个文件。
5. formal budget freeze manifest 记录 `git_diff` schema hash 和 runtime output limit。

建议修改文件：

1. `src/repo_harness/tools/minimal.py`
2. `tests/unit/test_tools_minimal.py`
3. `tests/integration/test_pre_verl_agentloop_runtime.py`

验收标准：

1. 无改动时返回稳定的 empty diff 结构。
2. 多文件改动时返回 changed files summary。
3. diff 截断时给出按文件恢复路径。
4. `git_diff(path=...)` 不能读取 workspace 外路径。
5. tool schema snapshot 和 runtime 输出上限一致。

### 6.7 统一符号链接策略

优先级：`P1`

当前问题：

SWE-Bench 物化仓库可能包含符号链接。`read_file`、`grep`、`list_files` 和 `git_diff` 如果各自处理符号链接，可能出现三类问题：读到 workspace 外文件、递归遍历噪声、不同工具看到的文件集合不一致。

一个简单例子：

```text
repo/fixtures/latest -> /tmp/shared-fixtures/latest
```

如果 `list_files` 展示了这个路径，`grep` 继续递归进入它，而 `read_file` 又因为越界拒绝，模型会看到不一致的工具行为。

修复方案：

1. 工具层统一符号链接规则。
2. 不递归符号链接目录。
3. 文件符号链接只有在 target resolve 后仍然位于 workspace 内，并且不是 sensitive path 或 evaluator-only path 时才允许读取。
4. 工具结果增加 `skipped_symlink_count`。
5. hidden material inspect 要覆盖符号链接目标，避免 evaluator-only 文件通过符号链接进入模型可见上下文。

验收标准：

1. workspace 内安全符号链接可以被明确审计。
2. workspace 外符号链接被拒绝，并给出稳定原因。
3. 符号链接目录不会导致递归噪声。
4. `read_file`、`grep`、`list_files` 和 `git_diff` 的符号链接策略一致。

## 7. Stage 2：Bash 工具和命令策略修复

优先级：`P1`

本阶段即使 formal final-only baseline 不开放 `bash`，也必须完成。原因是 RepoHarness 是一个通用软件工程智能体 Harness，而不是只服务这一次 baseline 的脚本。只要后续 scaffold comparison、GitHub issue flow、公开测试反馈任务或者 diagnostic baseline 打开 `bash`，当前问题就会影响评测准确性和安全边界。

实施步骤：

1. 合并 `src/repo_harness/permissions/system.py` 和 `src/repo_harness/tasks/command_policy.py` 中关于模型 `bash` 命令的策略入口。
2. 新增统一函数，例如 `evaluate_model_command_request()`，输入包括：
   - command
   - cwd
   - task_id
   - test_feedback_policy
   - public_test_commands
   - hidden_test_commands
   - allowed_diagnostic_commands
   - workspace boundary
3. 输出统一结构，例如：

```json
{
  "decision": "allow|deny|route_to_run_tests",
  "command_category": "diagnostic|public_test|hidden_test|unsafe_shell|network|destructive|unknown",
  "reason_code": "denied_by_final_only_feedback_policy",
  "safe_argv": ["git", "status", "--short"],
  "recovery_hint": "Use git_diff or read_file instead."
}
```

4. `ToolExecutor.normalize()`、`PermissionSystem.check()` 和 workspace execution 都使用同一个决策结果。
5. `bash` 工具 description 写清楚允许命令族和替代工具。
6. formal run 如果没有开放 `bash`，也要在 manifest 中记录 `bash.enabled=false` 和 `bash_policy_version`。
7. 新增非 formal `bash` hardening smoke。
8. `bash_diagnostic` 执行层必须只接受统一策略返回的 `safe_argv`。如果没有 `safe_argv`，或者 workspace adapter 试图使用 `allow_shell=True`，formal readiness inspect 必须失败。
9. `python -m unittest`、`pytest`、`python -m pytest`、`tox`、`nox` 都必须被识别为测试类命令，并根据 `test_feedback_policy` 决定拒绝或路由到 `run_tests`。
10. 本阶段不要求 formal final-only baseline 开放 `bash`，但要求证明 formal resolved tools 中没有 `bash` 时确实没有任何 `bash` tool call、`bash` tool schema 或 hidden shell execution 混入。

建议修改文件：

1. `src/repo_harness/permissions/system.py`
2. `src/repo_harness/tasks/command_policy.py`
3. `src/repo_harness/tools/minimal.py`
4. `src/repo_harness/workspace/` 下 local process 和 Docker adapter 实现
5. `tests/unit/test_permissions.py`
6. `tests/unit/test_task_command_policy.py`
7. `tests/integration/test_pre_verl_agentloop_runtime.py`

验收标准：

1. `bash: pwd` 在允许时可以运行。
2. `bash: git status --short` 在允许时可以运行。
3. `bash: find . -name "*.py"` 被拒绝，并提示使用 `list_files`。
4. `bash: grep -R "foo" .` 被拒绝，并提示使用 `grep` 工具。
5. `bash: python -m pytest` 在 `test_feedback_policy=disabled` 时被拒绝，原因是测试反馈策略禁止。
6. `bash: python -m pytest` 在 `structured_public_feedback` 且命令匹配公开测试时路由到 `run_tests`。
7. `bash: python -m unittest`、`bash: tox`、`bash: nox` 在 `test_feedback_policy=disabled` 时被拒绝，原因也是测试反馈策略禁止。
8. `bash: curl https://example.com` 被拒绝，原因是网络命令禁止。
9. `bash: rm -rf .` 被拒绝，原因是破坏性命令禁止。
10. `bash: git diff --no-index a b` 被拒绝，原因是不允许 no-index diff。
11. 所有 `bash` 运行事件都包含 `safe_argv`、`policy_decision`、`command_category` 和 `timeout_sec`。
12. workspace execution event 证明实际执行的 argv 与策略返回的 `safe_argv` 完全一致。

## 8. Stage 3：上下文审计和 Provider 输入绑定修复

### 8.1 Context Replacement 必须可恢复

优先级：`P1`

当前问题：

当上下文过长时，系统可能把部分内容替换成 artifact 引用。如果引用只包含 artifact id、哈希、头尾预览，模型可能无法知道怎样恢复完整内容。

一个简单例子：

```text
模型看到：Large tool output replaced by artifact abc123.
```

模型不知道这是哪个文件、哪个 grep 查询、从哪一行开始，也不知道应该怎么重新读取。

修复方案：

1. replacement message 必须包含原始工具名和关键参数。
2. 对 `read_file`，必须包含 `path`、`start_line`、`end_line`、`total_lines` 和推荐恢复调用。
3. 对 `grep`，必须包含 `query`、`mode`、`glob`、`offset` 和推荐下一页调用。
4. 对 `list_files`，必须包含 `root`、`glob`、`offset` 和推荐下一页调用。
5. replacement artifact 不能包含 evaluator-only 内容。

建议修改文件：

1. `src/repo_harness/context/manager.py`
2. `src/repo_harness/trajectory/` 下 transcript 或 artifact 相关模块
3. `tests/unit/test_context_manager.py`

验收标准：

1. 每个 replacement 都能告诉模型如何恢复。
2. replacement 不泄漏 hidden test patch、hidden selector 或 final verifier 输出。
3. prepared messages 和 transcript 中能审计模型实际看到的 replacement 文本。

### 8.2 工具调用和工具结果配对必须成为硬门槛

优先级：`P0`

当前问题：

OpenAI-compatible tool calling 要求 assistant tool call 和 tool result 严格配对。Claude Code 参考实现中有类似 `ensureToolResultPairing` 的不变量。RepoHarness 不能只记录问题，必须在正式运行前阻止不完整上下文进入 Provider。

一个简单例子：

```text
assistant 发出 tool_call_id=call_1 的 read_file。
但是下一轮 messages 里没有 tool result call_1。
```

如果继续请求 Provider，轻则 Provider 报协议错误，重则模型看到不完整上下文，评测结果不可解释。

修复方案：

1. 增加 `ContextIntegrityPolicy`。
2. 每次 Provider 请求前检查：
   - 是否存在没有 tool result 的 assistant tool call。
   - 是否存在没有 tool call 的 tool result。
   - 是否存在重复 tool result。
   - tool result 是否按 Provider 协议出现在合法位置。
3. formal pre-verl 模式下，发现问题必须停止运行，状态为 `context_integrity_error`。
4. 非 formal 诊断模式可以选择合成 interrupted tool result，但必须把运行标记为 `tainted=true`。

建议修改文件：

1. `src/repo_harness/agent_loop.py` 或实际 AgentLoop loop 模块
2. `src/repo_harness/model_client/providers/common.py`
3. `src/repo_harness/pre_verl_agentloop.py`
4. `tests/unit/test_agent_loop.py`
5. `tests/integration/test_pre_verl_agentloop_runtime.py`

验收标准：

1. 缺失 tool result 时，不会写出正式 Provider request。
2. 孤立 tool result 会被拒绝。
3. 重复 tool result 会被拒绝。
4. boundary index inspect 能验证 transcript、events 和 raw provider request 中的 tool call / tool result 配对一致。

### 8.3 Transcript 不能只保存 preview

优先级：`P1`

当前问题：

训练导出和审计不能只依赖 message preview。Preview 适合人快速浏览，但不适合作为完整轨迹来源。

一个简单例子：

```text
assistant 先解释了一句：
"I will inspect the parser first."
然后发起 read_file 工具调用。
```

如果 export 只根据事件重建 tool call，并且把 assistant content 设成 `null`，训练轨迹就丢失了模型真实输出的一部分。

修复方案：

1. transcript message 增加结构化字段：
   - `role`
   - `content`
   - `tool_calls`
   - `tool_call_id`
   - `tool_result`
   - `message_payload_ref`
   - `message_payload_sha256`
   - `prepared_message_ref`
   - `raw_provider_request_ref`
   - `raw_provider_response_ref`
2. preview 继续保留，但只能作为展示字段，不能作为导出唯一来源。
3. exporter 优先从 transcript structured messages 导出，而不是仅按 turn events 猜测。
4. assistant 同时包含自然语言和 tool calls 时，导出必须同时保留两者。
5. exporter 导出前验证 transcript message、prepared messages、raw provider request 和 raw provider response 的哈希绑定一致。

建议修改文件：

1. `src/repo_harness/trajectory/` 下 transcript schema 和 recorder
2. `src/repo_harness/training_export.py` 或当前 exporter 实现
3. `tests/unit/test_export.py`
4. `tests/integration/test_export_from_run.py`

验收标准：

1. assistant text + tool call 不会丢失 text。
2. 每个 tool result 都能通过 `tool_call_id` 找到对应 tool call。
3. 默认 SFT 导出、强化学习 rollout 导出和 diagnostic export 都使用同一套结构化 transcript 来源。
4. transcript 中每条结构化 message 都能通过 sha256 绑定到对应来源 artifact，不能只依赖 preview 文本。

### 8.4 Raw Provider Request Redaction 需要从整字段脱敏改为字段敏感脱敏

优先级：`P1`

当前问题：

如果 redaction 策略把普通长文本误判成凭证，可能把模型实际看到的问题描述、工具说明或者源码片段整段替换成 `<REDACTED_CREDENTIAL>`。这样审计者看不到模型到底拿到了什么上下文。

一个简单例子：

```text
issue statement 很长。
redaction 把整个 message.content 替换成 <REDACTED_CREDENTIAL>。
```

这不是安全审计，而是破坏了评测可复核性。

修复方案：

1. redaction 改为 key-aware 和 span-based。
2. 只有字段名或文本片段明确像 secret 时才脱敏。
3. 普通 `message.content`、工具 description、issue statement 和源码片段不能因为长度较长就整字段脱敏。
4. provider reasoning trace 的策略继续按显式 opt-in 文档执行。
5. raw provider request artifact 增加：
   - `prepared_messages_ref`
   - `tool_schema_snapshot_ref`
   - `model_input_hash`
   - `provider_body_hash_before_redaction`
   - `redacted_body_hash`
   - `redaction_report`
6. raw provider response artifact 增加同等级绑定字段：
   - `model_call_id`
   - `raw_provider_request_ref`
   - `prepared_messages_ref`
   - `tool_schema_snapshot_ref`
   - `response_body_hash_before_redaction`
   - `redacted_response_body_hash`
   - `redaction_report`
   - `parsed_tool_calls_hash`
   - `finish_reason`
7. `prepared_messages` 与真实 provider request body 必须做等价性检查。Provider 私有字段可以有白名单，例如 DeepSeek 的 `reasoning_content` replay 字段，但普通 `role`、`content`、`tool_calls`、`tool_call_id` 和 tool result content 必须逐轮可对齐。

建议修改文件：

1. `src/repo_harness/model_client/` 下 redaction 相关模块
2. `src/repo_harness/model_client/providers/common.py`
3. `tests/unit/test_provider_client.py`
4. `tests/integration/test_pre_verl_agentloop_runtime.py`

验收标准：

1. 普通长 issue statement 不会被整字段脱敏。
2. 假的 API key、token、password 会被片段级脱敏。
3. raw provider request 能绑定 prepared messages 和 tool schema snapshot。
4. raw provider response 能绑定 raw provider request、prepared messages、tool schema snapshot 和 parsed tool calls。
5. inspect 能证明公开产物没有 secret，同时保留模型实际输入和 Provider 实际返回的可审计文本。
6. inspect 能证明 prepared messages 经 provider serializer 转换后的消息投影，与 raw provider request body 中的 messages 等价。

### 8.5 模型可见上下文需要独立 inspect

优先级：`P1`

修复方案：

新增命令：

```bash
repo-harness inspect-model-visible-context RUN_DIR \
  --assert-no-hidden-test-material \
  --assert-prepared-messages-bound \
  --assert-provider-body-equivalent \
  --assert-tool-results-recoverable \
  --assert-no-over-redaction
```

验收标准：

1. 能列出每一轮 Provider 请求中模型看到的 system、user、assistant、tool messages。
2. 能列出每一轮暴露的工具 schema。
3. 能证明 hidden test patch、hidden selector、gold patch 和 final verifier 输出没有进入模型可见上下文。
4. 能证明 raw provider request 没有把普通上下文整段误脱敏。
5. hidden material 检查不能只靠关键词扫描，必须基于 evaluator-only artifact 的 sha256、非空内容片段、selector 字符串、gold patch hunks 和 final verifier 原始输出摘要做反向匹配。
6. 默认 export payload、prepared messages、raw provider request、transcript model-visible fields 都必须通过 hidden material 反向匹配。

## 9. Stage 4：失败归因和训练导出修复

### 9.1 空补丁和预算耗尽不能归因为模型补丁失败

优先级：`P1`

当前问题：

如果模型达到 `max_turns` 后没有生成有效 `final.patch`，这应该被归因为预算耗尽或者空补丁，而不是模型补丁被 final verifier 拒绝。

一个简单例子：

```text
模型用了 32 轮，一直在读文件和尝试编辑。
最后没有生成可应用 final.patch。
```

正确归因：

```text
budget_exhausted_without_patch
```

错误归因：

```text
model_patch_rejected_by_final_verifier
```

修复方案：

1. final report 增加 terminal outcome priority：
   - provider protocol error
   - context integrity error
   - environment setup failed
   - patch apply failed
   - budget exhausted without patch
   - empty patch
   - final verifier accepted
   - final verifier rejected
2. 如果没有可应用模型 patch，不进入 strict final verifier accepted/rejected 统计。
3. aggregation inspect 检查分母口径：
   - planned subset accept rate
   - terminal provider outcome accept rate
   - final verifier reached accept rate
4. `accepted_count` 只能来自 strict final verifier boundary 中 `accepted=true` 的运行。
5. `provider_protocol_error`、`context_integrity_error`、`empty_patch`、`budget_exhausted_without_patch`、`environment_setup_failed` 不能被归为 `final_verifier_rejected`，也不能被 `failure_owner=model_wrong_fix` 掩盖。
6. aggregation inspect 必须检查 `accepted_count`、`blocked_count`、`provider_error_count`、`empty_patch_count`、`budget_exhausted_count`、`final_verifier_reached_count`、`failure_owner` 和 denominator 字段之间的一致性。

建议修改文件：

1. `src/repo_harness/pre_verl_agentloop.py`
2. `scripts/pre_verl/run_agentloop_evaluation.py`
3. `tests/unit/test_pre_verl_agentloop_scheduler.py`

验收标准：

1. 空补丁任务不会被统计为 final verifier rejected。
2. 预算耗尽任务有明确预算字段，包括 used turns、max turns、used tool calls、max tool calls。
3. 聚合报告同时展示计划分母和 terminal 分母。
4. 聚合报告展示 final verifier reached 分母，避免把没有进入 final verifier 的任务伪装成模型修错。

### 9.2 训练导出默认不应包含失败污染样本

优先级：`P2`

修复方案：

1. 对每个 run 增加 `training_export_ready`。
2. accepted run 默认可进入 positive rollout export。
3. final verifier rejected run 可以进入 diagnostic export，但不能默认作为正样本。
4. empty patch、context integrity error、provider protocol error、environment setup failed 默认不能进入训练样本。
5. provider reasoning trace training export 继续使用显式 opt-in 策略。
6. 增加 `training_export_visibility_gate`。默认 SFT 和强化学习 rollout export 只能读取 `model_visible=true` 的结构化 transcript、prepared messages 中模型实际看到的 tool observation，以及 accepted/final reward metadata。
7. 默认训练导出禁止直接读取 `evaluator_only`、`provider_raw_redacted`、`final_verifier_raw_output`、`hidden_test_patch`、`hidden_selector`、`gold_patch`、`provider_reasoning_trace` artifact。
8. diagnostic export 可以显式包含失败信息，但必须标记 `diagnostic_only=true`，不能进入默认正样本。

验收标准：

1. 默认 export 不包含 context integrity error。
2. 默认 export 不包含空补丁作为正样本。
3. diagnostic export 可以显式包含失败轨迹，并带失败类型。
4. 默认 export 的每条样本都能证明来源是模型可见 transcript 或 prepared messages，而不是 raw provider artifact 或 evaluator-only artifact。

## 10. Stage 5：TaskDefinition、Selector 和 Final Verifier 边界复核

优先级：`P0`

这部分与 `docs/resume/pre-verl-agentloop-evaluation-execution-plan.md` 中的正式评测计划保持一致。hardening 实施不能绕过已有要求。

必须确认：

1. 23 个 development instances 都有可被 `repo-harness run-task` 消费的 `TaskDefinition`。
2. final-only 任务必须拒绝所有非 `disabled` 的测试反馈策略。
3. strict final verifier 顺序必须是：

```text
冻结源码
先应用模型 final.patch
再应用 evaluator-only hidden test patch
最后执行冻结 selector
```

4. baseline verifier、final verifier、run metadata 和 aggregation inspect 使用同一套冲突规则。
5. selector 必须完整保存和执行，不能因为命令截断或者 shell 语法不兼容导致假通过或者假失败。
6. formal task set manifest 不能只过滤 `runnable=true` 后悄悄缩小分母。23 个 development instances 中任意任务不可运行，都必须保留在计划分母里，并生成 blocked reason。
7. blocked reason 必须区分环境物化失败、Docker 镜像缺失、TaskDefinition 不兼容、selector 无法执行、Provider 配置不可用和其他 Harness 问题。

验收标准：

1. `inspect-pre-verl-agentloop-task-definitions` 通过。
2. `inspect-pre-verl-agentloop-boundary-index` 通过。
3. `inspect-pre-verl-agentloop-hardening-readiness` 能证明 selector 没有截断、没有 hidden material 泄漏、没有旧 V3 adapter 混入。
4. formal readiness inspect 能证明 `planned_development_instance_count=23`，并且所有不可运行任务都有 blocked reason。

## 11. Stage 6：正式测评前 Smoke Gate

优先级：`P0`

修复完成后，必须重新跑 smoke，而不是沿用旧 smoke 结果。

建议 smoke 组成：

1. 5 个 Docker SWE-Bench Lite development smoke，使用 DeepSeek flash。
2. 1 个 mock provider tool schema smoke，验证 `grep`、`read_file`、`edit_file`、`list_files` 的新 schema。
3. 1 个 non-formal bash hardening smoke，验证 `bash` 策略。
4. 1 个 model-visible context inspect，验证 raw provider request、prepared messages、transcript 和 tool artifacts 可审计。

正式 smoke gate：

1. 5 个 Docker smoke 必须全部由外部脚本调用真实 `repo-harness run-task`。
2. 至少 4 个任务有真实 provider terminal outcome。
3. 至少 3 个任务进入 strict final verifier adapter。
4. 至少 1 个任务产生可应用非空模型补丁。
5. 0 个 `provider_protocol_error`。
6. 0 个 `context_integrity_error`。
7. 0 个 raw provider request over-redaction。
8. 0 个 hidden material leakage。
9. 0 个 legacy adapter usage。
10. 如果任务失败，必须能明确归因到模型补丁质量、预算耗尽、空补丁、环境问题或者工具策略拒绝。
11. 如果 smoke 中有任务 blocked，必须证明它是单任务已知问题，而不是 Docker execution mode、TaskDefinition、execution_image、setup_command、Provider adapter 或 final verifier 的系统性问题。否则不能进入正式二十三题。

建议验证命令：

```bash
PATH=.venv/bin:$PATH python -m compileall src scripts/pre_verl/run_agentloop_evaluation.py
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-agentloop-hardening-readiness RUN_DIR --assert-formal-ready
PATH=.venv/bin:$PATH repo-harness inspect-model-visible-context RUN_DIR --assert-no-hidden-test-material --assert-prepared-messages-bound --assert-provider-body-equivalent --assert-tool-results-recoverable --assert-no-over-redaction
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-agentloop-boundary-index RUN_DIR/pre_verl_agentloop_final_verifier_boundary_index.json --assert-all-formal-runs-bound --assert-command-order --assert-clean-source-origin --assert-run-task-lineage --assert-no-legacy-adapter
```

## 12. 建议实施顺序

推荐按以下顺序实施，避免一次性修改过大。

1. Stage 0：轻量记录当前 commit、已有 smoke 路径和当前问题列表。如果执行 agent 已经有等价记录，可以直接进入 Stage 1。
2. Stage 1.4：先统一工具输出上限，因为后续工具改造都依赖它。
3. Stage 1.2：修复 `read_file` 行号、哈希和截断恢复。
4. Stage 1.1：修复 `grep` 正则表达式、分页和恢复提示。
5. Stage 1.3：修复 `edit_file` 哈希和重复替换保护。
6. Stage 1.5：修复 `list_files` 分页和噪声控制。
7. Stage 1.6：修复 `git_diff` 截断恢复和变更文件摘要。
8. Stage 1.7：统一符号链接策略。
9. Stage 2：修复 `bash` 统一命令策略、执行层 `safe_argv` 绑定和 hardening smoke。
10. Stage 3.2：把 tool call / tool result 配对从记录项升级为 formal 硬门槛。
11. Stage 3.1：补充 context replacement 可恢复信息。
12. Stage 3.3：补充结构化 transcript 和 hash 绑定。
13. Stage 3.4：修复 raw provider request / response redaction 和 Provider body 等价检查。
14. Stage 3.5：新增 model-visible context inspect。
15. Stage 4：修复失败归因和训练导出 readiness。
16. Stage 5：复核 TaskDefinition、selector、二十三题分母和 final verifier boundary。
17. Stage 6：重新跑 smoke，通过后才允许正式二十三题测评。

## 13. 正式二十三题开始条件

只有满足以下所有条件后，才可以进入正式二十三题测评：

1. 全量测试通过。
2. hardening readiness inspect 通过。这个 inspect 应在修复完成并重新 smoke 后生成，不是 Stage 0 的修复前记录。
3. model-visible context inspect 通过。
4. bash hardening smoke 通过。
5. 5 题 Docker smoke 重新通过。
6. boundary index inspect 通过。
7. aggregation inspect 拒绝旧 single-shot pilot、非 `run-task` 结果和 legacy adapter 结果。
8. formal budget freeze manifest 绑定以下字段：
   - provider
   - model
   - provider-specific options sha256
   - DeepSeek thinking policy
   - DeepSeek reasoning content replay policy
   - OpenAI API mode
   - OpenAI reasoning state policy
   - scaffold id
   - scaffold version
   - prompt sha256
   - tool schema snapshot sha256
   - resolved tool list
   - resolved tool output limits
   - grep mode policy
   - git_diff output policy
   - context policy id
   - redaction policy version
   - transcript schema version
   - bash policy version
   - bash enabled
   - Docker execution mode
   - final verifier adapter version
   - planned development instance count
   - selected task count
   - max turns
   - max tool calls
   - max test runs
   - task timeout
   - command timeout
   - temperature
   - seed
9. formal task set manifest 绑定 23 个 development instances。不可运行任务必须带 blocked reason，不能从分母中消失。
10. 每次工具 schema、prompt、provider reasoning compatibility、redaction policy、bash policy 或预算发生变化，都必须生成新的 baseline id，旧 smoke、旧 pilot 和旧 accepted rate 不能与新 baseline 混算。

如果其中任意一项不满足，应停止正式二十三题测评，并生成 blocked report，而不是继续运行后再解释结果。

## 14. 本计划对应的风险收口

本计划完成后，可以把风险收口为以下口径：

1. 如果模型修错，报告可以证明模型看到了什么、调用了什么工具、产出了什么补丁，以及 final verifier 为什么拒绝。
2. 如果模型没有修完，报告可以证明是预算耗尽、空补丁、工具策略拒绝、环境问题还是 Provider 问题。
3. 如果工具输出被截断，模型会看到可恢复提示，审计者也能看到原始工具调用参数和截断边界。
4. 如果 `bash` 将来被打开，运行结果不会因为隐形 shell 能力、测试反馈泄漏或者策略漂移而失真。
5. 如果上下文管理没有实现 Claude Code 的多层压缩，也不会影响本轮 formal baseline 的可信边界，因为模型可见上下文、工具输出截断和恢复路径都已经可审计。
