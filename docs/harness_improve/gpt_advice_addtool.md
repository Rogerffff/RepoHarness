我的问题：
当前我正在进行harness的修改和升级，这是其中一部分agent向我推荐的设计。但是我认为这里可能存在权衡，如果新增了这些结构化工具的话可能在训练过程中更方便控制和审计，但是可能会增加工具量给模型带来的负担，同时如果希望模型适配更多的例如claude code这样的不给这些工具的harness的话是否会导致一些问题，还是说模型的能力应该足够适配多种harness，当前对于我的简历项目来说还是优先这样设计，后续要适配更多的harness的话可以继续对其他harness进行RL或者sft/opd等。同时我记得有些中国模型厂商的技术报告中曾经说过要如何训练模型适配多种不同的harness或者tool schema.帮我搜索一下。最终给出建议


Q3 · delete/move/mkdir 都要新增工具吗？还是像 CC 用 Write+Bash？
计划定的是都新增结构化工具（delete_file / move_file / mkdir），不走 Bash。每个都接入 patch/export、带越界拒绝，delete/move 强制 expected_hash。

为什么不学 CC 用 Bash：这正是我们之前定的"结构化优先"。CC 用 Write+Bash 做文件组织变更，但 RH 主训练 core 故意不给裸 bash（防 reward-hacking/泄漏，见安全红线）。所以用显式结构化工具替代 CC 的"Bash 做文件操作"——能力覆盖到，但形态更可控可审计。


回答：
根据 2026-05-26 这份 RepoHarness 能力差距文档，以及我刚查到的 Cursor、Claude Code、Codex、Qwen、Kimi 等公开经验，我的结论是：

**你的直觉是对的：这里确实有权衡。**
但在你当前阶段，我仍然建议 **优先采用结构化文件操作**，只是不要把 `delete_file / move_file / mkdir` 三个都毫无节制地暴露成主训练默认工具。更好的方案是：

> **内部实现可以是三个强审计工具，但模型可见层最好收敛成一个低负担的 `file_op` / `manage_path` 工具，或者优先让 `apply_patch + create_file(auto_mkdir)` 覆盖大部分需求。**

也就是说，我不建议你完全学 Claude Code 用 Bash 做文件组织变更；但也不建议默认工具面膨胀到很多小工具，让模型在 RL 里把注意力消耗在“该选哪个文件操作工具”上。

---

# 1. 先回答 Q3：delete/move/mkdir 都要新增吗？

我的建议是分层：

```text
P0：必须有
  apply_patch
  create_file，最好支持自动创建父目录

P1：建议有，但不要三个都作为默认独立模型可见工具
  file_op(op="mkdir" | "move" | "delete", ...)

P2：如果发现模型经常误用 file_op，再拆成独立工具
  mkdir
  move_file
  delete_file
```

也就是说：

```text
不建议：
  默认暴露 delete_file + move_file + mkdir 三个独立工具

更建议：
  内部实现 delete/move/mkdir 三个 executor
  模型可见层暴露一个 file_op / manage_file 工具
```

例如：

```json
{
  "tool_name": "file_op",
  "arguments": {
    "op": "move",
    "src": "src/old_name.py",
    "dst": "src/new_name.py",
    "expected_src_hash": "sha256:...",
    "create_parent_dirs": true
  }
}
```

或者：

```json
{
  "tool_name": "file_op",
  "arguments": {
    "op": "delete",
    "path": "src/legacy_unused.py",
    "expected_hash": "sha256:...",
    "reason": "The module is no longer imported after replacing it with src/new_impl.py."
  }
}
```

这样你同时得到三件事：

```text
1. 结构化可审计；
2. 不让工具数量膨胀；
3. 不必把文件删除/移动交给 Bash 解析。
```

你的上传文档里已经指出，当前 exact `edit_file(old_text, new_text)` 对复杂补丁很不自然，缺少 `apply_patch`、`write_file`、`delete_file`、`move_file`、`mkdir` 等能力会让多文件、多步骤修改消耗大量工具预算，并增加字符串替换失败风险；同时它也强调“结构化不等于强”，如果结构化工具不能覆盖真实开发动作，就会成为能力瓶颈。

---

# 2. 为什么不要简单“学 Claude Code 用 Bash”？

Claude Code 确实允许通过 Bash 做很多文件组织操作。官方权限文档里，Claude Code 把 read-only、Bash commands、file modification 分成不同权限类型；`acceptEdits` 模式还会自动接受工作目录内常见文件系统命令，比如 `mkdir`、`touch`、`mv`、`cp` 等。([Claude Code][1])

但 Claude Code 的上下文和你的 RL 训练环境不同。

Claude Code 产品态通常有：

```text
用户审批
权限模式
sandboxed Bash
项目级 settings
hooks
人工可见的交互轨迹
```

Claude Code 的 Bash sandbox 文档说，它通过文件系统和网络边界来让 Bash 命令更自主地运行；权限规则在命令运行前判断工具调用，sandbox 则由操作系统约束 Bash 及其子进程能访问什么。([Claude Code][2])

你的 RepoHarness 训练态则是：

```text
没有真人逐条审批；
模型会被 RL 激励去探索 reward loophole；
所有工具输出都会进入训练轨迹；
hidden verifier / gold patch / git history 泄漏风险更高；
一旦 Bash 太强，模型可能学会 reward hacking。
```

所以你不需要照抄 Claude Code 的“Bash 做文件操作”形态。你应该学习的是它的**能力原则**：

```text
能力足够强；
权限足够清楚；
拒绝足够结构化；
轨迹足够可审计。
```

这也和你文档中的判断一致：Claude Code 的核心优势不是“没有权限限制”，而是把足够强的开发能力放进统一、可审计、可拒绝、可扩展的工具生命周期中。

---

# 3. 结构化工具的好处是什么？

结构化文件操作对 SWE RL 很有价值，尤其是你当前还要防 reward hacking。

## 3.1 可审计

如果模型调用：

```bash
rm -rf src/legacy
```

你需要解析 shell，判断：

```text
它删了什么？
是不是 workspace 内？
是不是测试文件？
是不是 hidden 文件？
是不是 .git？
是不是通过 glob 扩大了删除范围？
是不是 symlink escape？
```

如果是结构化工具：

```json
{
  "op": "delete",
  "path": "src/legacy/foo.py",
  "expected_hash": "..."
}
```

harness 可以非常明确地记录：

```text
删除对象
删除前 hash
删除原因
是否曾被 read_file 读取
是否在 workspace 内
是否命中 forbidden path
是否进入 final patch
```

这对 RL 训练非常重要，因为你后续可以对行为做 reward shaping、过滤、OPD 或 LLM-as-judge 监控。

---

## 3.2 更容易防止 reward hacking

Bash 里的文件操作有很多绕路：

```bash
rm tests/test_bug.py
mv tests/test_bug.py /tmp/
python - <<'PY'
import os
os.remove("tests/test_bug.py")
PY
find . -name '*test*' -delete
```

结构化工具则可以硬性规定：

```text
delete_file 不能删除 public tests，除非任务明确要求；
move_file 不能把文件移出 workspace；
mkdir 不能创建 .git / runtime_private / hidden verifier 路径；
expected_hash 不匹配就拒绝；
模型未读过的文件不能删除，或需要更高权限；
批量删除必须显式列出路径，不允许 glob。
```

这比让 Bash 执行器猜测意图安全得多。

---

## 3.3 更好的训练信号

如果 `delete_file` 被拒绝，你可以返回：

```json
{
  "allowed": false,
  "reason_code": "DELETE_TEST_FILE_FORBIDDEN",
  "safe_alternative": "Modify implementation code instead of deleting tests.",
  "retryable": true
}
```

这就可以作为 targeted textual feedback 或 OPD target。

如果是 Bash 拒绝：

```text
Command denied.
```

模型可能只学会：

```text
少用 shell
少验证
尽快 final
```

你上传的文档里也强调，权限拒绝不应该只是错误文本，而应该给出 `denied_reason_code`、`policy_version`、`safe_alternative_tool`、`safe_rewrite_example`、`retryable` 等字段，否则模型学到的是“工具很难用，少用工具”。

---

# 4. 结构化工具的坏处是什么？

你的担心也成立。

## 4.1 工具数量增加会带来 tool selection 负担

如果默认工具面变成：

```text
read_file
grep
glob_files
symbol_search
edit_file
create_file
apply_patch
delete_file
move_file
mkdir
run_public_command
git_diff
git_status
todo_write
read_tool_result_artifact
...
```

模型每一步都要判断：

```text
新文件用 create_file 还是 apply_patch？
重命名用 move_file 还是 apply_patch？
创建目录用 mkdir 还是 create_file 自动创建？
删除文件用 delete_file 还是 apply_patch 删除？
```

这会增加 tool-selection entropy。RL 早期尤其容易出现：

```text
调用格式错
选错工具
重复工具调用
该用 patch 却用 edit_file
该用 run_public_command 却用 diagnostic_shell
```

Qwen3-Coder-Next 技术报告里也能看到，模型对不同 IDE/CLI scaffolds、XML/JSON tool-call schema 的适配是一个专门评测项；报告说一些模型在不同模板之间表现波动很大，说明工具格式和 scaffold 适配本身就是能力瓶颈。([arXiv][3])

所以你不能无限加工具。

---

## 4.2 会让模型过拟合 RepoHarness 私有工具面

如果你只在 RepoHarness 上 RL，且默认总是暴露：

```text
delete_file
move_file
mkdir
```

那么模型迁移到 Claude Code 时可能会尝试调用：

```json
{"tool_name": "move_file", ...}
```

但 Claude Code 没有这个工具；它可能需要用：

```text
Bash(mv ...)
Edit / Write
```

或者迁移到 MiniSWEAgent / SWE-Agent 时，它需要通过 shell 完成同一语义。

所以问题不是“结构化工具绝对不好”，而是：

```text
只训练一种工具 schema 会造成 harness overfitting。
```

你的文档里也明确指出，如果最终希望适配 Claude Code 类工具，训练环境至少要覆盖 shell、文件编辑、patch、测试、任务管理、权限拒绝恢复、工具输出分页和外部工具抽象，否则动作空间差异过大。

---

# 5. 公开经验怎么处理“多 harness / 多 schema 适配”？

这里你记得没错，中国模型厂商的报告里确实有相关内容，尤其是 Qwen 和 Kimi。

## 5.1 Cursor：优先贴近部署 harness，但允许训练时动态改变工具

Composer 2 报告的原则是：训练时使用代表 Cursor client harness 的工具，并维护 Cursor backend 的 shadow deployment，从而让训练 rollouts 尽量 faithful to deployed harness；但他们也明确说，训练和生产可以有意不同，例如训练时更严格检查工具参数，或者为了 steerability 移除某些工具，并且每个环境可动态决定可用工具集合和工具行为。([arXiv][4])

这对你的启发是：

```text
主训练工具面要接近目标部署；
但可以用更严格、更可审计的结构化形式训练；
关键是不要让结构化形式破坏真实 SWE 闭环。
```

---

## 5.2 Qwen3-Coder-Next：显式评估多 scaffold / 多 tool-call schema 泛化

Qwen3-Coder-Next 报告说，他们构建了一个内部 evaluation benchmark，专门衡量模型对不同真实 agentic coding scaffolds/IDEs 的适配能力；benchmark 包含多个 prompt templates 和 tool-call schemas，覆盖 system instruction、XML variant 和 JSON-based tool-call patterns。报告中还说，Qwen3-Coder-Next 在五种环境上的表现比较稳定，说明训练中多样化 tool-call formats 和 agentic workflows 能迁移到真实交互式 coding setting。([arXiv][3]) ([arXiv][3])

这个经验很直接：

```text
不要指望模型天然适配所有 harness；
要显式把多 schema / 多 scaffold 作为训练和评测目标。
```

也就是说，你可以现在优先做 RepoHarness 结构化工具，但后续必须做：

```text
RH structured profile
ClaudeCode-like profile
MiniSWEAgent bash profile
OpenHands/SWE-Agent profile
XML tool-call profile
JSON tool-call profile
```

然后评估同一批任务在不同 profile 下的表现。

---

## 5.3 Kimi K2：用大量真实 MCP 工具 + 合成工具 + 多 agent 配置教“陌生工具”适配

Kimi K2 报告里专门有大规模 agentic data synthesis for tool use learning。它们的 pipeline 包括：从真实 MCP 工具和 LLM 合成工具构建 tool spec repository；为每个工具集生成 agent 和任务；再生成工具调用轨迹。报告说他们抓取了 3000+ 真实 MCP tools，又合成了 20,000+ synthetic tools，并生成 thousands of distinct agents，每个 agent 有不同 system prompt 和工具组合。([arXiv][5]) ([arXiv][5])

更关键的是，Kimi 报告也承认纯 simulation fidelity 有限制，所以对 coding/SWE 这类 authenticity 关键的场景，会补充真实 execution sandbox，用实际代码执行和测试通过率作为 ground-truth feedback。([arXiv][5])

这个经验对应到你这里就是：

```text
想要多 harness 适配，不是少给工具；
而是多给工具组合、多给 schema、多给真实执行反馈。
```

---

## 5.4 Qwen 函数调用文档：模板和协议本身会影响效果，最终方案是用自己的数据微调

Qwen 的 function calling 文档说，function calling 本质上建立了一个协议：应用提供函数说明，模型选择是否使用函数，并按说明给出调用方式，应用执行后把结果返回给模型；文档也提醒，不同模板/协议会影响工具调用稳定性，生产中要准备解析和修复机制，最终方案是用自己的数据 fine-tune。([Qwen][6])

这说明你现在做 RepoHarness 时，最好把工具 schema 当成训练对象，而不是只当工程接口。

---

# 6. 所以：结构化优先是否会影响适配 Claude Code？

会有影响，但不是不可接受。关键看你怎么训练。

## 情况 A：只在 RH 结构化工具上 RL

风险：

```text
模型学会 move_file/delete_file/mkdir
部署到 Claude Code 看到没有这些工具
可能 unknown tool call 上升
可能不知道该用 Bash/Write 等价替代
```

这个风险真实存在。

## 情况 B：RH 结构化工具 + 多 profile 混训/蒸馏

风险大幅降低。

你可以让模型学到的是：

```text
“我需要移动文件”这个语义
```

而不是死记：

```text
“移动文件一定调用 move_file”
```

在 RH profile 下：

```json
file_op(op="move", src="a.py", dst="b.py")
```

在 ClaudeCode-like profile 下：

```json
Bash(command="mv a.py b.py")
```

在 MiniSWEAgent profile 下：

```bash
mv a.py b.py
```

在 patch-only profile 下：

```diff
rename from a.py
rename to b.py
```

这样模型学的是**语义动作到当前工具 schema 的映射**。

---

# 7. 我建议你采用“语义动作层 + harness adapter”的设计

你可以把系统分成三层：

```text
Level 1: SWE semantic action
  read
  search
  patch
  create
  move
  delete
  mkdir
  run_public_test
  inspect_diff
  final_answer

Level 2: RepoHarness model-visible tools
  read_file
  grep
  apply_patch
  create_file
  file_op
  run_public_command
  git_diff

Level 3: Target harness adapters
  RepoHarness structured
  ClaudeCode-like Bash/Write
  MiniSWEAgent shell
  OpenHands
  SWE-Agent
```

例如同一个语义动作：

```text
Move file src/foo.py → src/bar.py
```

在不同 harness 中映射成：

```text
RepoHarness:
  file_op(op="move", src="src/foo.py", dst="src/bar.py", expected_hash="...")

Claude Code-like:
  Bash("mv src/foo.py src/bar.py")

Patch-only:
  apply_patch("diff --git a/src/foo.py b/src/bar.py ...")

MiniSWEAgent:
  shell: mv src/foo.py src/bar.py
```

这样你的项目叙述会非常清楚：

> 我不是训练模型死适配某个私有工具，而是在 RepoHarness 中定义可审计的 SWE semantic action，并通过不同 adapter 研究模型对 tool schema / harness 的泛化能力。

这对简历项目反而是加分点。

---

# 8. 具体到 delete / move / mkdir，我建议这样设计

## 8.1 `mkdir`

**优先级最低。**

很多时候不需要单独暴露 `mkdir`，因为：

```text
create_file("pkg/new_module/__init__.py")
```

可以自动创建父目录。

或者：

```text
apply_patch
```

在添加新文件时也可以让 harness 自动创建父目录。

所以我建议：

```text
默认不暴露 mkdir
create_file 和 apply_patch 支持 create_parent_dirs=true
内部记录 mkdir 事件
```

只有当你发现模型经常需要创建空目录，或者某些框架确实要求空目录存在时，再开放：

```json
file_op(op="mkdir", path="...")
```

---

## 8.2 `move_file`

**建议有，但放进 `file_op`。**

它适合这些任务：

```text
重命名模块
迁移目录结构
把测试文件移动到新 package
拆分 legacy 文件
```

安全策略：

```text
src 必须存在
src 必须 workspace 内
dst 必须 workspace 内
dst 默认不能存在，除非 overwrite=true 且 expected_dst_hash 提供
src 必须提供 expected_src_hash
禁止操作 .git / hidden / runtime_private / verifier / gold patch
移动 public tests 需要任务明确要求或更高权限
移动后自动记录 git diff / rename detection 信息
```

示例：

```json
{
  "op": "move",
  "src": "src/foo/legacy_parser.py",
  "dst": "src/parser/legacy_parser.py",
  "expected_src_hash": "sha256:abc...",
  "create_parent_dirs": true
}
```

---

## 8.3 `delete_file`

**建议有，但必须比 move 更严格。**

它适合：

```text
删除死代码
删除旧 feature flag
删除被替换的生成文件
删除过期配置
```

安全策略：

```text
必须 expected_hash
必须给 reason
最好要求文件已被 read_file 读取过
禁止删除 tests，除非任务明确是删除/迁移测试
禁止删除 lockfile / config / CI 文件，除非任务明确要求
禁止 glob 删除
禁止 recursive delete，至少 P0 不支持
删除后自动生成 patch event
```

示例：

```json
{
  "op": "delete",
  "path": "src/old_feature_flag.py",
  "expected_hash": "sha256:def...",
  "reason": "All references were removed after migrating to src/feature_flags.py."
}
```

---

# 9. 默认工具面应该长什么样？

我建议你的 `swe_public_core` 默认工具面控制在 **10–12 个模型可见工具** 左右：

```text
list_files / glob_files
read_file
read_tool_result_artifact
grep 或 symbol_search
edit_file
create_file
apply_patch
file_op
run_public_command
git_diff
todo_write 或 update_working_state
final_answer
```

如果你觉得 `list_files + glob_files + grep + symbol_search` 太多，可以合并/裁剪：

```text
find_files(pattern)
search_code(query, mode="text" | "symbol")
```

重点是：

```text
不要为了结构化，把工具面做成 20+ 个默认工具；
也不要为了简洁，把核心 SWE 闭环砍掉。
```

你的文档里建议的 P0 顺序是：先补 public diagnostic shell / public command，再补 apply_patch / create_file，再加 preflight，并用小样本验证“复现、修改、验证、diff 收口”闭环，这个顺序我同意。

---

# 10. 如何降低工具数量带来的模型负担？

## 10.1 工具分层显示

不要所有任务都显示所有工具。

例如：

```text
普通 bug fix:
  read/search/edit/apply_patch/run_public_command/git_diff

迁移/重构任务:
  额外显示 file_op

文档任务:
  不显示 run_public_command 或 file_op，除非需要
```

Cursor Composer 2 报告也提到，可用工具集合和工具行为可以按环境动态决定；训练时甚至可以更严格检查参数或移除某些工具来提高 steerability。([arXiv][4])

---

## 10.2 工具描述中写清楚优先级

例如：

```text
apply_patch:
  Use for multi-file edits, creating or deleting files via unified diff,
  or when exact old_text replacement is inconvenient.

edit_file:
  Use for small local replacements after reading the file.

file_op:
  Use only for filesystem organization operations:
  move, delete, or create an empty directory.
  Do not use this to edit file contents.

run_public_command:
  Use for public tests, smoke checks, and self-authored repro scripts.
  Do not use for file deletion/move; use file_op instead.
```

这样模型不会把 `run_public_command("rm ...")` 当常规路径。

---

## 10.3 对工具选择做 targeted feedback / OPD

如果模型调用：

```bash
run_public_command("rm src/foo.py")
```

你可以返回：

```json
{
  "allowed": false,
  "reason_code": "FILESYSTEM_MUTATION_REQUIRES_STRUCTURED_TOOL",
  "safe_alternative_tool": "file_op",
  "safe_rewrite_example": {
    "tool_name": "file_op",
    "arguments": {
      "op": "delete",
      "path": "src/foo.py",
      "expected_hash": "..."
    }
  }
}
```

然后做 targeted textual feedback：

```text
For deleting files, use file_op with expected_hash instead of shell rm.
```

teacher 分布会把概率从：

```text
run_public_command("rm ...")
```

推向：

```text
file_op(op="delete", ...)
```

这比简单拒绝有效得多。

---

# 11. 如何训练模型适配多种 harness？

我建议你分四步。

## 11.1 Schema randomization

同一个语义工具，换不同表层名字和格式训练。

例如同一个“运行公开命令”：

```text
RepoHarness JSON:
  run_public_command(command="pytest ...", cwd=".")

ClaudeCode-like:
  Bash(command="pytest ...")

XML:
  <tool_call name="bash"><command>pytest ...</command></tool_call>

ReAct:
  Action: Bash
  Action Input: pytest ...
```

Qwen3-Coder-Next 的多 scaffold / XML/JSON schema 评测说明，这种适配不是自动发生的，必须显式评估和训练。([arXiv][3])

---

## 11.2 Harness profile mixing

同一批任务，按比例混入不同 profile：

```text
60% RepoHarness structured
20% ClaudeCode-like Bash/Write
10% MiniSWEAgent shell
10% OpenHands/SWE-Agent style
```

随着训练推进，可以调整：

```text
早期：RH structured 多一些，便于安全和审计
中期：混入 ClaudeCode-like，让模型学等价动作
后期：profile randomization / held-out schema eval
```

---

## 11.3 Tool dropout

在某些 rollout 中故意隐藏 `file_op`，要求模型用 `apply_patch` 或 Bash 等价替代。

例如：

```text
profile A:
  file_op 可用

profile B:
  file_op 不可用，但 apply_patch 可用

profile C:
  file_op 不可用，Bash 可用
```

这样模型不会形成：

```text
“移动文件只能用 move_file”
```

而会形成：

```text
“我要表达 rename/move 这个语义；当前工具面里哪个工具能表达？”
```

---

## 11.4 Cross-harness OPD / SFT

你可以用结构化 RH 作为 teacher 产生高质量轨迹，再转写到其他 harness。

例如 teacher 轨迹：

```json
file_op(op="move", src="a.py", dst="b.py")
```

转写为 ClaudeCode-like student target：

```json
Bash(command="mv a.py b.py")
```

或者转写为 patch-only：

```diff
rename from a.py
rename to b.py
```

然后做 SFT/OPD。

这就是“从安全可审计 harness 里学语义动作，再蒸馏到目标 harness 表面形式”。

---

# 12. 最适合你简历项目的设计叙事

你当前项目不是单纯产品落地，而是“可展示的 SWE agentic RL harness”。所以我建议你优先选择一个工程上更干净、可证明安全性的设计。

你的项目可以这样描述：

```text
RepoHarness uses structured filesystem operations for high-risk mutations
(delete/move/mkdir) to make RL trajectories auditable and prevent
reward-hacking through shell-side effects. To avoid overfitting to a private
tool schema, the harness defines a semantic action layer and supports
profile-level schema adaptation, including ClaudeCode-like Bash/Write,
MiniSWEAgent shell, and patch-only modes.
```

这比“我们照抄 Claude Code 用 Bash”更有研究/工程含量。

---

# 13. 我给你的最终建议

## 13.1 对当前 Q3 方案的评价

agent 的方案：

```text
delete/move/mkdir 都新增结构化工具，不走 Bash；
每个接入 patch/export；
带越界拒绝；
delete/move 强制 expected_hash。
```

我认为方向是对的，但默认模型可见形态建议改一下：

```text
内部：delete_file / move_file / mkdir 三个 executor 可以都有
外部：默认只暴露一个 file_op 工具
```

即：

```text
保留结构化优先；
降低工具数量；
减少模型 tool selection 负担；
保留后续适配 Claude Code-like Bash 的空间。
```

---

## 13.2 默认不要把 Bash 当文件组织工具

在 RH 主训练 profile 中，建议明确：

```text
run_public_command 用于测试、复现、诊断；
file_op / apply_patch 用于文件系统修改；
Bash 里的 rm/mv/mkdir 默认拒绝，并给 safe alternative。
```

这和 Claude Code / Codex 的真实产品模式不完全一样，但适合 RL 训练。Codex 默认也不是无边界 Bash，而是在 workspace sandbox 内允许读写和 routine local commands，越界、网络等通过 approval 控制；它强调 sandbox 和 approval 是两层不同控制。([OpenAI 开发者][7]) ([OpenAI 开发者][8])

你的训练环境没有真人 approval，所以用结构化工具替代高风险 Bash mutation 是合理的。

---

## 13.3 但必须保留 public command / shell 诊断能力

不要因为结构化优先，就又回到“模型不能跑命令”的状态。

默认必须有：

```text
run_public_command(command, cwd, timeout_sec)
```

允许：

```text
pytest tests/test_x.py::test_y
python .repo_harness_tmp/repro.py
npm test -- ...
go test ./...
cargo test ...
git diff
git status
```

禁止：

```text
rm / mv / mkdir 这类文件 mutation
git log / git show / git cat-file
curl / wget / git clone
pip install / npm install，除非 setup phase
hidden verifier / runtime_private
```

你的文档也强调，final-only 不应关闭公开诊断；hidden final verifier 不可见，不等于模型不能运行公开测试或写复现。

---

# 14. 一个具体默认工具 schema 建议

我建议你下一版默认工具面这样设计：

```yaml
profile: swe_public_core_v2

tools:
  - read_file
  - search_code          # 可内部合并 grep/symbol_search
  - glob_files
  - edit_file
  - create_file          # create_parent_dirs 默认 true
  - apply_patch
  - file_op              # op: mkdir | move | delete
  - run_public_command
  - git_diff
  - read_tool_result_artifact
  - todo_write
  - final_answer
```

`file_op` schema：

```json
{
  "op": "move | delete | mkdir",
  "path": "string",
  "target_path": "string | null",
  "expected_hash": "string | null",
  "expected_target_hash": "string | null",
  "create_parent_dirs": "boolean",
  "reason": "string"
}
```

规则：

```text
mkdir:
  expected_hash 不需要；
  只允许 workspace 内；
  禁止 .git / hidden / runtime_private。

move:
  required: path, target_path, expected_hash；
  target 默认不能存在；
  可 create_parent_dirs；
  禁止移入/移出 forbidden path。

delete:
  required: path, expected_hash, reason；
  默认禁止删除 public tests / lockfile / config / CI；
  不允许 recursive；
  不允许 glob；
  最好要求该文件之前被 read_file 或 search_code 命中过。
```

---

# 15. 你后续要怎么验证这套设计没把模型带偏？

用小样本做四组 eval。

```text
A. RH structured:
   file_op 可用，Bash mutation 禁止

B. RH patch-only:
   file_op 不可用，apply_patch 可表达 delete/create/rename

C. ClaudeCode-like:
   Bash/Write/Edit 可用，无 file_op

D. MiniSWEAgent-like:
   主要通过 shell + patch/edit 完成
```

同一批 30–50 个任务，记录：

```text
resolved_rate
invalid_tool_call_rate
tool_not_found_rate
file_op_usage_rate
bash_mutation_attempt_rate
apply_patch_success_rate
public_test_used_rate
self_repro_used_rate
permission_denial_recovery_rate
cross_profile_drop
```

你要看的不是单一分数，而是：

```text
模型是否只会 RH file_op？
file_op 隐藏后，它能否改用 apply_patch？
ClaudeCode-like profile 下，它能否改用 Bash/Write？
它是否仍然保持复现、修改、验证、diff 收口？
```

如果 B/C/D 掉得很厉害，就说明结构化工具带来了 overfitting，需要加 profile mixing / schema randomization / OPD。

---

# 16. 最终结论

我建议你这样决策：

```text
1. 当前简历项目阶段：
   采用结构化优先，这是正确选择。
   它能展示安全、审计、RL trajectory 质量和 reward-hacking 防护。

2. 但不要默认暴露 delete_file / move_file / mkdir 三个独立工具：
   用一个 file_op 合并，内部仍然拆 executor。

3. 不要用 Bash 做高风险文件组织变更：
   Bash/run_public_command 主要用于公开测试、复现和诊断。

4. 必须同时设计多 harness 适配路线：
   profile mixing、tool dropout、schema randomization、cross-harness SFT/OPD。

5. 后续适配 Claude Code：
   不需要现在牺牲 RH 安全性；
   可以用 ClaudeCode-like profile 继续 RL/SFT/OPD，把 file_op 语义蒸馏到 Bash/Write/Edit 表面形式。
```

一句话压缩：

**你的主训练 harness 可以比 Claude Code 更结构化、更可审计；但训练目标不能只适配这一个结构化 schema。最好的方案是：结构化 RH 做安全主线，多 profile / 多 schema 做泛化路线。**

[1]: https://code.claude.com/docs/en/permissions "Configure permissions - Claude Code Docs"
[2]: https://code.claude.com/docs/en/sandboxing "Configure the sandboxed Bash tool - Claude Code Docs"
[3]: https://arxiv.org/html/2603.00729v1 "Qwen3-Coder-Next Technical Report"
[4]: https://arxiv.org/html/2603.24477v1 "Composer 2 Technical Report"
[5]: https://arxiv.org/html/2507.20534v2 "Kimi K2: Open Agentic Intelligence"
[6]: https://qwen.readthedocs.io/en/latest/framework/function_call.html "Function Calling - Qwen"
[7]: https://developers.openai.com/codex/concepts/sandboxing "Sandbox – Codex | OpenAI Developers"
[8]: https://developers.openai.com/codex/agent-approvals-security "Agent approvals & security – Codex | OpenAI Developers"