# 第 2 章 Command Tools And Safety：构建 Agent Harness 需要掌握的命令行知识

## 本章解决什么问题

你在 `docs/05-workspace-sandbox-and-permissions.md` 里已经把命令安全规则写成了设计原则，例如：

- 测试命令应该走 `run_tests`，而不是普通 `bash`。
- `bash` 默认只允许诊断命令和受限只读命令。
- `git clone`、`git fetch`、`curl`、`wget`、`ssh`、`scp` 等命令在 agent run 阶段默认拒绝。
- 所有命令必须有 timeout，输出必须截断或落盘。

如果你不熟悉命令行，这些规则会显得有点像“背黑名单”。本章的目标是把它们讲清楚：**为什么 agent harness 需要命令工具、哪些命令有用、哪些命令危险、如何把命令执行变成可控的工具结果、第一版应该怎么保守实现。**

读完本章，你应该能回答四个问题：

1. `bash` 工具、`run_tests` 工具、setup command 和 final verifier 分别负责什么。
2. `stdout`、`stderr`、`exit_code`、`cwd`、环境变量、timeout、进程树这些概念是什么意思。
3. 为什么不能把模型给出的任意 shell 字符串直接执行。
4. RepoHarness 第一版可以采用怎样的命令 allowlist、denylist 和路由规则。

---

## 1. Agent Harness 里的“命令工具”是什么

软件工程 agent 需要和仓库互动。它不只是读文件和改文件，还要运行测试、看报错、跑类型检查、查看 Git diff。命令工具就是让模型请求这些动作的接口。

RepoHarness 第一版应该至少区分四类命令入口：

| 入口 | 作用 | 是否进入训练评测指标 |
| --- | --- | --- |
| `bash` | 普通诊断命令，例如 `ruff check .`、`mypy .`、`python -m compileall .`、受限 `ls` 或 `find`。 | 只作为环境观察进入 transcript 和 events，默认不计算 success rate。 |
| `run_tests` | 执行任务定义中的测试命令，调用 verifier feedback path，返回结构化 `VerifierResult`。 | 可以用于中间反馈，但最终指标仍以 final verifier 为准。 |
| setup command | 安装依赖、准备环境，只在 setup workspace 中执行。 | 不进入正式 agent action-observation 训练轨迹。 |
| final verifier | agent 停止后重新验证最终 patch，最好支持 strict patch replay。 | 是 success rate、reward metadata、训练导出的默认依据。 |

一个简单例子：

```text
用户任务：修复 calculator.divide 的除零错误

setup command:
  pip install -e .

run_tests:
  pytest -q

普通 bash 诊断:
  python -m compileall .
  ruff check .
```

这里 `pytest -q` 是测试语义，不应该被普通 `bash` 结果替代。普通 `bash` 可以告诉模型“某个诊断命令失败了”，但不能直接成为 reward 或 pass-to-pass 统计依据。

---

## 2. 命令行基础概念

### 2.1 命令、参数和 shell

当你写：

```bash
python -m pytest tests/test_calculator.py -q
```

它可以拆成：

```text
program: python
argv:
  - python
  - -m
  - pytest
  - tests/test_calculator.py
  - -q
```

这里 `argv` 是“参数数组”。如果你直接把整段字符串交给 shell，例如 `bash -lc "python -m pytest ..."`，shell 会先解析变量、引号、通配符、管道、重定向、子命令，然后再启动真实程序。

这就是风险来源：模型给出的不是一个单纯程序调用，而可能是一段 shell 程序。

例如：

```bash
pytest -q && curl https://example.com/leak
```

这不是一个单纯测试命令，而是两个命令用 `&&` 连接。第一个成功后会执行第二个网络命令。

第一版实现建议：

- 能用参数数组执行时，不要用 shell 字符串执行。
- 如果必须支持 shell 字符串，先做命令分类和安全检查。
- 复杂 shell 语法默认拒绝，除非任务配置显式 allowlist。

### 2.2 cwd：当前工作目录

`cwd` 是 current working directory，也就是命令执行时所在目录。

同一个命令在不同目录结果可能完全不同：

```bash
pytest -q
```

如果 `cwd` 是仓库根目录，它可能运行整个测试集；如果 `cwd` 是某个子目录，它可能找不到配置或只跑一部分测试。

RepoHarness 规则：

- 所有命令都必须在 workspace boundary 内执行。
- 默认 `cwd` 应是正式 agent run workspace 的仓库根目录。
- 如果允许子目录执行，必须解析后确认仍在 workspace 内。

### 2.3 环境变量

环境变量是传给进程的键值对，例如：

```bash
PYTHONPATH=src pytest -q
NODE_ENV=test npm test
```

环境变量会影响命令行为，也可能携带密钥，例如 `GITHUB_TOKEN`、`OPENAI_API_KEY`。

RepoHarness 规则：

- setup 阶段可以有受控环境变量。
- agent run 阶段使用环境变量白名单。
- 不把宿主机所有环境变量原样传给 agent 命令。
- transcript 和 export 中默认不泄漏密钥类环境变量。

### 2.4 stdout、stderr 和 exit code

命令通常有三类结果：

| 字段 | 含义 |
| --- | --- |
| `stdout` | 标准输出，通常是正常结果。 |
| `stderr` | 标准错误，通常是错误、警告、日志。 |
| `exit_code` | 进程退出码。通常 `0` 表示成功，非 `0` 表示失败或异常。 |

例子：

```bash
pytest -q
```

可能返回：

```text
exit_code = 1
stdout = "F.."
stderr = ""
```

这不是 harness 崩溃，而是测试失败，是正常 environment feedback。模型应该看到失败摘要并继续修复。

再比如：

```bash
python missing_file.py
```

可能返回：

```text
exit_code = 2
stderr = "python: can't open file 'missing_file.py'"
```

这通常是命令错误，不是代码测试失败。

RepoHarness 规则：

- 非零 exit code 不一定等于工具崩溃。
- 测试失败应进入 `VerifierResult(error_type = "assertion_failure")` 或类似类型。
- 命令无法启动、依赖缺失、测试框架崩溃应进入 `test_command_error`、`dependency_error` 或 `parser_error`。

### 2.5 输出截断和 artifact

测试和构建输出可能非常长。不能把完整输出全部塞进模型上下文，否则很快超出 token 限制。

推荐做法：

```text
完整 stdout/stderr -> 写入 artifact 文件
模型上下文 -> 只放 preview，例如前 200 行、后 200 行、关键失败片段
events -> 记录 artifact_ref、truncated、exit_code、duration_ms
```

工具结果示例：

```json
{
  "tool_name": "bash",
  "status": "error",
  "exit_code": 1,
  "stdout_preview": "FAILED tests/test_calculator.py::test_divide_by_zero ...",
  "stderr_preview": "",
  "truncated": true,
  "artifact_refs": ["artifact_stdout_001", "artifact_stderr_001"],
  "duration_ms": 1200
}
```

### 2.6 timeout 和进程树

有些命令可能永远不结束：

```bash
npm start
python -m http.server
tail -f log.txt
```

如果 harness 没有 timeout，整个 agent run 会卡死。

更麻烦的是，一个命令可以启动子进程。例如：

```bash
sh -c "python long_task.py & wait"
```

只杀父进程可能留下子进程继续跑。

RepoHarness 规则：

- 每个命令必须有 timeout。
- timeout 后要尽量终止整个进程树。
- local process mode 可以使用 process group 或等价机制。
- Docker execution mode 要记录容器停止和清理状态。
- 被中断的命令也要生成 `ToolResult(status = "timeout")` 或 `ToolResult(status = "interrupted")`。

---

## 3. 为什么不能直接执行模型给出的任意命令

模型输出的命令可能有三类问题。

### 3.1 破坏 workspace 或宿主机

危险命令例子：

```bash
rm -rf .
rm -rf /
sudo rm -rf /tmp/something
chmod -R 777 .
chown -R user .
```

在真实仓库中，即使只是删除 workspace 也会污染轨迹和 diff。更严重的是，如果路径边界没做好，可能影响 workspace 外文件。

第一版策略：

- 默认拒绝 `rm -rf`。
- 默认拒绝 `sudo`。
- 默认拒绝写 home directory。
- 所有路径都必须解析到 workspace 内。

### 3.2 引入外部状态，破坏可复现性

这些命令会访问外部网络或远程仓库：

```bash
git clone https://github.com/example/repo
git fetch origin
git pull
curl https://example.com/script.sh
wget https://example.com/file
ssh user@host
scp file user@host:/tmp
```

在 agent run 阶段，这些命令会带来几个问题：

- 结果依赖当前网络状态。
- 远程内容可能变化，导致评测不可复现。
- 模型可能获取未来 commit 或答案，形成数据泄漏。
- 可能把本地任务信息发送到外部。

第一版策略：

- setup 阶段可以按任务配置允许网络，例如安装公开依赖。
- agent run 阶段默认拒绝网络命令。
- 如果未来允许网络，必须记录 `network_policy`、允许域名、命令、时间和输出 artifact。

### 3.3 绕过 verifier 或 reward

模型可能试图让测试“看起来通过”，而不是修复问题。

危险例子：

```bash
pytest -q || true
sed -i 's/assert False/assert True/' tests/test_bug.py
rm tests/test_bug.py
```

这里的风险是 reward hacking。模型不是修代码，而是绕过测试。

第一版策略：

- `run_tests` 只能执行任务定义中的测试命令。
- final verifier 必须重新运行。
- strict final verifier 最好从 source checkout 创建 verification workspace，恢复合法依赖状态，应用 `final.patch` 后再运行。
- 测试文件是否允许修改必须由任务 schema 或 verifier 策略明确决定。

---

## 4. 命令分类：哪些可以允许，哪些要路由，哪些要拒绝

### 4.1 测试命令：路由到 `run_tests`

常见测试命令：

| 生态 | 常见命令 |
| --- | --- |
| Python | `pytest -q`、`python -m pytest`、`python -m unittest` |
| JavaScript / TypeScript | `npm test`、`pnpm test`、`yarn test`、`npx vitest run`、`npx jest` |
| Rust | `cargo test` |
| Go | `go test ./...` |
| Java | `mvn test`、`gradle test` |

这些命令默认不应该作为普通 `bash` observation。它们应该路由到 `run_tests`，由 verifier 解析成结构化结果。

规则可以这样写：

```text
如果命令等于 task.test_command:
  route_to = run_tests
如果命令是 task.allowed_test_subset_commands 中的一个:
  route_to = run_tests
如果命令看起来像 pytest / npm test / cargo test，但不在 allowlist:
  deny 或 ask，不能直接作为 reward 来源
```

为什么不让模型随便跑测试子集？

因为模型可能只跑容易通过的测试，然后误以为任务完成。真正的 final verifier 仍然必须跑完整任务定义。

### 4.2 诊断命令：可以走受限 `bash`

诊断命令帮助模型理解错误，但不直接产生最终 reward。

常见诊断命令：

| 生态 | 命令 | 用途 |
| --- | --- | --- |
| Python | `ruff check .` | 静态检查和 lint。 |
| Python | `mypy .` | 类型检查。 |
| Python | `python -m compileall .` | 检查 Python 文件是否能编译。 |
| TypeScript | `npx tsc --noEmit` | 类型检查，不写输出。 |
| JavaScript | `npm run lint` | lint。 |
| Rust | `cargo check` | 编译检查，不运行测试。 |
| Rust | `cargo clippy` | lint。 |
| Go | `go vet ./...` | 静态诊断。 |

注意：有些诊断命令也可能写缓存或下载依赖。第一版可以保守处理：

- 只允许任务 schema 中声明过的诊断命令。
- 或只允许一小组明确只读或低风险的命令。
- 诊断产生的缓存默认排除在 `final.diff` 之外。

### 4.3 只读文件系统查询：优先用专用工具

模型可能会请求：

```bash
pwd
ls
find . -name "*.py"
grep -R "divide" .
cat calculator.py
git status
git diff
```

这些看起来安全，但在 agent harness 中更推荐专用工具：

| 模型意图 | 推荐工具 |
| --- | --- |
| 看当前目录 | `list_files` |
| 读文件 | `read_file` |
| 搜索文本 | `search`，底层可以用 `rg` |
| 看最终 diff | `git_diff` |

为什么不鼓励全走 `bash`？

- 专用工具更容易做路径边界检查。
- 专用工具输出更结构化，方便训练导出。
- 专用工具更容易截断和保存 artifact。
- `cat`、`grep`、`find` 的 shell 参数组合非常多，容易绕过简单规则。

第一版策略：

- `pwd`、受限 `ls`、受限 `find` 可以作为 bash 只读命令。
- 搜索和读取优先使用 `read_file` / `search`。
- `git diff` 优先使用 `git_diff`。

### 4.4 依赖安装和构建：只在 setup 阶段默认允许

常见依赖安装命令：

```bash
pip install -e .
pip install -r requirements.txt
npm install
pnpm install
cargo fetch
go mod download
```

这些命令会访问网络、修改缓存、创建目录。它们应该属于 setup workspace，而不是正式 agent run。

规则：

- setup command 可以安装依赖。
- setup 产物保存为 `dependency_state`。
- agent run workspace 从 source checkout 创建，再恢复 `dependency_state`。
- 依赖目录和缓存目录默认排除出 final diff。

### 4.5 写入和格式化命令：谨慎允许

有些命令会修改文件：

```bash
ruff check . --fix
prettier --write .
gofmt -w .
cargo fmt
```

它们不一定危险，但会产生大量修改，可能掩盖真正 patch。

第一版建议：

- 默认不要通过 `bash` 允许自动写入格式化命令。
- 如果要格式化，优先让模型通过 `apply_patch` 明确修改。
- 如果任务确实需要格式化命令，必须配置 allowlist，并记录 patch size。

---

## 5. Bash 语法里最容易踩坑的地方

### 5.1 管道

```bash
pytest -q | tee output.txt
```

管道把前一个命令输出传给后一个命令。它可能改变 exit code，也可能写文件。

第一版可以默认拒绝复杂管道，除非显式允许。

### 5.2 重定向

```bash
pytest -q > result.txt
cat secret.txt 2>/dev/null
```

重定向会读写文件。它可能把输出写到 workspace 外，也可能隐藏错误。

第一版规则：

- 重定向路径必须在 workspace 内。
- 不允许写 home directory 或绝对路径。
- 复杂重定向默认拒绝。

### 5.3 命令连接符

```bash
ruff check . && pytest -q
pytest -q || true
rm file; pytest -q
```

`&&`、`||`、`;` 可以把多个命令连起来。`pytest -q || true` 会把失败测试伪装成成功退出。

第一版规则：

- 测试命令不允许带 `|| true`。
- 多命令组合默认拒绝或要求配置 allowlist。

### 5.4 子命令和命令替换

```bash
echo $(cat secret.txt)
python -c "import os; print(os.environ)"
```

`$()` 会先执行内部命令，再把结果嵌入外部命令。它很难通过简单字符串规则安全判断。

第一版策略：默认拒绝包含命令替换的 shell 字符串。

### 5.5 后台进程

```bash
npm start &
python server.py &
```

后台进程会在工具返回后继续运行，污染后续测试和 workspace 状态。

第一版策略：

- 默认拒绝后台命令。
- 如果未来支持后台任务，需要单独的 Task 系统、输出文件、停止接口和生命周期事件。

---

## 6. 第一版命令策略建议

可以把命令决策分成四步。

### 第一步：先判断是不是测试命令

```text
if command == task.test_command:
    route_to = run_tests
elif command in task.allowed_test_subset_commands:
    route_to = run_tests
elif looks_like_test_command(command):
    deny_or_ask
```

### 第二步：判断是不是明确允许的诊断命令

```text
if command in task.allowed_diagnostic_commands:
    route_to = bash
elif command matches small_builtin_diagnostic_allowlist:
    route_to = bash
```

### 第三步：拒绝高风险命令

```text
deny if command contains:
  rm -rf
  sudo
  git clone / fetch / pull / remote add
  curl / wget
  ssh / scp
  background process
  command substitution
  workspace-outside path
```

### 第四步：无法判断就拒绝

对于批量评测和训练数据采集，保守拒绝比冒险执行更好。

```text
unknown command:
  interactive single run -> ask
  batch evaluation -> deny
```

---

## 7. 命令执行结果应该怎么记录

一次命令执行至少要记录：

```text
command
cwd
exit_code
stdout_preview
stderr_preview
stdout_artifact_ref
stderr_artifact_ref
duration_ms
timeout
truncated
permission_decision
network_policy
```

对应到 `ToolResult`：

```json
{
  "tool_name": "bash",
  "tool_call_id": "toolu_001",
  "status": "error",
  "content_preview": "ruff reported 2 lint errors.",
  "duration_ms": 850,
  "error_type": "command_failed",
  "truncated": false,
  "permission_decision": {
    "decision": "allow",
    "reason": "allowed diagnostic command"
  },
  "stdout_preview": "...",
  "stderr_preview": "...",
  "exit_code": 1,
  "artifact_refs": ["artifact_stdout_001", "artifact_stderr_001"]
}
```

对应到 events：

```json
{
  "event_type": "tool_completed",
  "tool_name": "bash",
  "exit_code": 1,
  "duration_ms": 850,
  "artifact_refs": ["artifact_stdout_001", "artifact_stderr_001"],
  "truncated": false
}
```

---

## 8. Python 实现时的最小注意点

第一版 RepoHarness 如果用 Python 写 Workspace Adapter，可以遵守这些原则。

### 8.1 尽量使用参数数组

更推荐：

```python
subprocess.run(
    ["python", "-m", "pytest", "-q"],
    cwd=workspace_path,
    env=safe_env,
    timeout=120,
    capture_output=True,
    text=True,
)
```

谨慎使用：

```python
subprocess.run(
    "python -m pytest -q && curl https://example.com",
    shell=True,
)
```

如果传入 shell 字符串，必须先经过命令安全策略。

### 8.2 设置 cwd 和环境变量

```python
safe_env = {
    "PATH": safe_path,
    "PYTHONPATH": "src",
}
```

不要默认传入完整 `os.environ`。至少要过滤密钥类变量。

### 8.3 处理 timeout 和进程树

在类 Unix 系统上，可以考虑：

```python
subprocess.Popen(..., start_new_session=True)
```

timeout 后用进程组清理子进程。具体实现要小心平台差异；第一版可以先支持 macOS / Linux，并在文档中说明 Windows 不是第一版目标。

### 8.4 输出落盘

不要只把 stdout/stderr 存在内存里。命令输出大时要写 artifact：

```text
artifacts/tool_outputs/tool_001.stdout.txt
artifacts/tool_outputs/tool_001.stderr.txt
```

模型上下文只拿 preview。

---

## 9. 命令安全不是生产级沙箱

本章所有规则都服务两个目标：

1. 让训练和评测可复现。
2. 防止 agent 在任务工作区外做明显危险或污染数据的事。

它们不是生产级安全隔离。

不要把这些规则描述成：

- 完整沙箱逃逸防护。
- 企业级权限系统。
- 多租户安全平台。
- 完整网络隔离。

可以保守描述为：

- command timeout and path-boundary checks。
- Docker-based executable repository environment。
- task-level separated workspace。
- restricted command policy for reproducible evaluation。

---

## 10. 给 RepoHarness v1 的最小命令工具清单

第一版可以这样落地：

| 工具 | 是否必须 | 说明 |
| --- | --- | --- |
| `read_file` | 必须 | 不建议让模型用 `cat` 读文件。 |
| `search` | 必须 | 底层可以用 `rg`，输出结构化。 |
| `apply_patch` | 必须 | 第一版比 `write_file` 更适合控制修改范围。 |
| `git_diff` | 必须 | 用于查看最终 patch。 |
| `bash` | 必须，但要严格限制 | 只允许诊断命令和受限只读命令。 |
| `run_tests` | 必须 | 唯一中间测试反馈入口。 |
| setup command runner | 必须 | 只在 setup workspace 执行。 |
| final verifier runner | 必须 | 最终评测和 reward metadata 来源。 |

如果你只记住一句话，就是：

> `bash` 是普通环境观察工具，`run_tests` 是结构化评测入口，final verifier 是最终裁判。三者不能混用。

---

## 继续阅读

- `docs/05-workspace-sandbox-and-permissions.md`：正式设计中的权限模式、命令安全规则和 workspace 边界。
- `docs/04-tool-system-and-orchestration.md`：工具契约、ToolResult schema、并发安全。
- `docs/07-verifier-reward-and-evaluation.md`：VerifierResult、TestCaseResult、reward metadata。
- `docs/08-trajectory-store-and-training-export.md`：命令输出如何落盘为 artifact，并进入 transcript、events 和训练导出。
