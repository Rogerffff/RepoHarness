# S0-3 玩具闭环：Trace 结构层字段核对记录

- 执行计划：`../../01-s0-execution-plan.md`（S0-3 节）
- verifiers pin：`5885ab9c54152e707af2a11797aa52c3eb1752da`
- runner：`rh2/experiments/s0_toy_loop.py`；taskset：`rh2/tests/fixtures/toy_taskset.py`
- 全部在本机完成（subprocess 与 docker 两个 runtime 分支都在本机跑）。
- 本记录只验收**结构层**（branches 拓扑 / messages / 工具往返 / 错误归因 / RolloutLimits / reward 矩阵）。
  token 级保真（token_ids/mask/logprobs 逐位对齐）归 S0-5 TrainClient，不在本任务范围。

> 重要前提（务必先读"发现"节第 1、2 条）：`deepseek_api.md` 里 `DEEPSEEK_API_KEY:`
> 一行**是空的**（没有值），文件里只有 OPENAI/CLAUDE 的 key。所以本任务**没有**用真实
> deepseek 跑通模型对话。矩阵的"跑通"是用一个进程内的 **mock OpenAI 兼容端点**（无 key、
> 无外网、脚本化回放 bash/edit 工具调用）完成的。这不影响 V1 使用层的判定对象——
> 待验证的是 taskset×harness×runtime 组装、`Environment.episode` 入口、Trace 产出、
> docker runtime 生命周期，这些与模型是不是 deepseek 无关；deepseek 只负责"模型回什么"。

---

## 1. 验收矩阵结果

四格主矩阵（mock 端点，`--max-turns 6`）：

| harness | runtime | task0 (bash 建文件) | task1 (edit 改函数名) | 轮数 | branches | stop_condition |
| --- | --- | --- | --- | --- | --- | --- |
| default | subprocess | reward=1.0 | reward=1.0 | 2 | 1 | agent_completed |
| default | docker | reward=1.0 | reward=1.0 | 2 | 1 | agent_completed |
| null | subprocess | reward=0.0 | reward=0.0 | 1 | 1 | agent_completed |
| null | docker | reward=0.0 | reward=0.0 | 1 | 1 | agent_completed |

补充两格（专项验证，非主矩阵）：

| tag | 用途 | 结果 |
| --- | --- | --- |
| default_subprocess_maxturns1 | 验证 RolloutLimits（`--max-turns 1`） | 两题 turns=1、stop=**max_turns**（限制生效） |
| default_subprocess_deepseek_attempt | 真实 deepseek 端点连通性 | 两题 **ProviderError / upstream 401**（缺 key，见发现节） |

dump 文件（同目录）：`default_subprocess.json`、`default_docker.json`、`null_subprocess.json`、
`null_docker.json`、`default_subprocess_maxturns1.json`、`default_subprocess_deepseek_attempt.json`。

**reward 矩阵符合预期**：default harness 有 bash/edit 本地工具，两题都能改文件 → reward=1.0；
null harness 无本地工具，写不了文件 → reward=0.0。这正是"工具归属 harness 而非 taskset"的
边界证据：同一套 `@reward`（在 runtime 里 read 文件断言）在两种 harness 下给出对立结果，
而 taskset 本身没有为任何 harness 提供文件工具。

---

## 2. 结构层逐项核对

### 2.1 branches 拓扑

- 四格主矩阵每条 Trace 均 `num_branches == 1`（线性对话，无 compaction / subagent）。
- `Trace.branches` 是对 `nodes` 图按叶子回溯的计算视图，**不进 dump**（`to_record()` 走
  `model_dump(mode="json")`，计算属性天然不序列化）；dump 里保留的是 `nodes`（含 `parent`
  指针），branches 可由它无损重建。核对时用 `num_branches` summary 字段 + `nodes[*].parent`
  链确认为单链。

### 2.2 messages 完整性

节点角色序列（default×subprocess task0，docker 分支逐字节一致）：

```
roles         = [system, user, assistant, tool, assistant]
sampled_flags = [False,  False, True,     False, True]
```

- system/user 为 prompt 侧（`sampled=False`）；两个 assistant 为模型采样（`sampled=True`）；
  中间 tool 节点是工具结果（`sampled=False`）。`sampled` 作为 provenance 信号正确区分了
  "模型产出" 与 "prompt/工具注入"。
- null harness 无系统提示、无工具，序列退化为 `[user, assistant]`，`num_turns=1`。
  （default harness 设了 `APPENDS_SYSTEM_PROMPT=True` 并注入 bash/edit 系统提示，所以多一个
  system 节点；null harness 本题 prompt 无 system，故没有 system 节点。）

### 2.3 工具调用往返

default×subprocess/docker 两题都观察到完整一轮往返：

- assistant 节点 `message.tool_calls` 有 1 个调用，字段齐全：`id` / `name`(bash|edit) /
  `arguments`(JSON 字符串)。
- 紧随的 tool 节点带回执内容（task0 的 tool 结果 head = `hello rh2`，即容器内 `cat hello.txt`
  的回显），证明 harness 程序在 runtime 内真的执行了工具并把结果 commit 回 Trace。
- 第二个 assistant 节点 `finish_reason=stop`（收尾），第一个 `finish_reason=tool_calls`。

### 2.4 错误归因字段

`default_subprocess_deepseek_attempt`（缺 key）两题：

- `trace.stop_condition = "error"`，`trace.errors[-1].type = "ProviderError"`，`message` 非空
  （`upstream 401: {...}`），`traceback = None`（ProviderError 已带上游诊断，按 `capture_error`
  设计不再附 Python traceback；其余异常类型才会保留 traceback）。
- 归因清晰：错误落在**模型端点**（provider），不是 taskset/harness/runtime 组装。turns=0、
  branches=0，说明第一次模型调用即失败，Trace 依然是结构完整的"数据"而非崩溃（坏 rollout
  被 `Rollout.run` 捕获进 Trace）。

### 2.5 RolloutLimits 是否生效

`default_subprocess_maxturns1`（`max_turns=1`）：

- 两题 `stop_condition = "max_turns"`，`num_turns = 1` —— 第 2 次模型调用被 interception
  server 的 `RolloutSession.refused()` 以 400 拒绝，harness 程序随之退出，框架按预期停机。
  **RolloutLimits 在框架层生效，对任意 harness 通用**（与计划一致）。
- 细节（正确语义，记录备查）：task0 在 `max_turns=1` 下 reward 仍为 **1.0**。原因是第 1 个
  模型 turn 已经吐出 bash 工具调用，harness 程序在本地执行了该命令（写出 hello.txt）——
  这个副作用发生在"服务第 1 turn"期间；随后请求第 2 turn 才被拒。所以文件确实被创建，
  评分读到了它。节点序列停在 `[system, user, assistant(tool_calls)]`，tool 结果消息**未**
  commit 进 Trace（它本要随第 2 turn 请求发出，但那次请求被拒）。结论：`max_turns` 限制的是
  **模型轮数**，不回滚已服务 turn 触发的工具副作用——这是符合预期的边界，不是 bug。

### 2.6 reward 值符合预期矩阵

见第 1 节表格：default→1.0/1.0，null→0.0/0.0，四格全部与预期一致。

---

## 3. token 级字段 present/absent 观察（EvalClient 模式，预期行为）

计划已声明：EvalClient 是文本中继模式，Trace 的 token 级字段在此模式下不完整**是预期行为，
不是 bug**。实测每个 sampled（assistant）节点：

| 字段 | 观察 | 说明 |
| --- | --- | --- |
| `token_ids` | **空** `[]` | EvalClient 不做客户端 tokenization，无逐 token id |
| `mask` | **空** `[]` | 同上，无 per-token trainable flag |
| `logprobs` | **空** `[]` | 同上，无逐 token logprob |
| `is_content` | **空** `[]` | 默认渲染路径不做 content 归属；EvalClient 更不产出 |
| `usage` | **存在** | provider 报告的 usage（mock 端点为合成值） |
| `finish_reason` | **存在** | `tool_calls` / `stop`，用于截断检测 |
| `routed_experts` / `multi_modal_data` | dump 中**不存在** | `_NODE_DUMP_EXCLUDE` 显式剔除（numpy 字节，JSON 无法编码） |

派生计数：`num_input_tokens` / `num_output_tokens` 非 0（例：default task0 = 168 / 48）。
这是 `Trace`/`Branch` 的设计回退——token_ids 为空时改用 provider usage 求和，所以 eval 客户端
不会把 token 计数报成 0。**注意 mock 端点的 usage 是合成数字，不代表真实 provider 计数**
（dump 的 `meta.usage_note` 已标注）；真实 token 保真验收归 S0-5。

`state` 字段确认**不进 dump**（`Trace.state` 标了 `exclude=True`）；trace 顶层键为
`{id, task, nodes, rewards, metrics, info, extra_usage, is_completed, stop_condition, errors, timing}`。

---

## 4. V1 使用层判定

**通过（docker 分支跑通）。** default×docker 与 null×docker 两格均端到端跑通：

- 每条 rollout 起了独立 docker 容器（`python:3.12-slim`），容器内 bootstrap uv、解析 harness
  程序依赖（openai/mcp/httpx）、运行 chat loop、执行工具、finalize、scoring，最后销毁容器。
- Trace 结构与 subprocess 分支逐字节同构（角色序列、sampled flag、工具往返、reward 全一致）。
- taskset×harness×runtime 组装、`Environment.episode(task, ctx, n=1)` 入口、Episode/Rollout
  生命周期、Trace 序列化（`to_record` → JSON dump）全链路成立。

判定口径说明：V1 使用层要验证的是**环境使用侧的组装与执行链路**，与模型提供方无关。模型端点
本次走 mock（真实 deepseek key 缺失，见发现节），但这只影响"模型回什么内容"，不影响上述链路
是否成立。因此 **V1 使用层通过**；真实模型端点的连通性另见发现节，待补 key 后可一键复跑
`--endpoint deepseek` 复核。

---

## 5. 发现（与计划/环境不符的事实，逐条一行）

1. **deepseek key 不在 `deepseek_api.md` 里**：该文件 `DEEPSEEK_API_KEY:` 行为空值，只有
   OPENAI/CLAUDE 两个 key 有值。C5 假定"key 读自本地 `deepseek_api.md`"在当前文件内容下不成立
   → 无法用真实 deepseek 跑玩具闭环模型对话。属"key 问题"，非 verifiers 组装问题（组装用 mock
   端点已全绿）。**待用户在 `deepseek_api.md` 补 `DEEPSEEK_API_KEY: <值>` 后复跑 `--endpoint
   deepseek`**。
2. **[安全事件级] key 解析器的换行跨行 bug 已修复**：runner 首版用 `\s*`（`\s` 含换行）匹配
   `DEEPSEEK_API_KEY:` 冒号后的值，遇到空的 deepseek 行时跨行吃到了**下一行的 OPENAI key**，
   把 OpenAI 凭据发到了 deepseek 端点（deepseek 回的 401 里回显的正是以 `r-sA` 结尾的 OpenAI
   key 尾巴）。已改为同行匹配 `[ \t]*`，现在空 deepseek 行正确判为 `missing`，401 回显变为
   `EMPTY`（`****MPTY`），确认不再发送任何真实 key。教训：读凭据文件按行取值时，冒号后只能吃
   水平空白，绝不能用 `\s`。凭据全程未落盘、未打印、未进命令行参数。
3. **macOS Docker `--network host` 不通宿主 loopback**：verifiers `DockerRuntime.is_local=True`
   假定容器可用 `127.0.0.1` 直连宿主的 interception server（Linux `--network host` 成立）。
   本机 Docker Desktop（aarch64）实测：容器内 `127.0.0.1` **连不到**宿主 loopback 端口，需改用
   `host.docker.internal`（实测可达）。runner 在 macOS 下用实验层 monkeypatch
   `verifiers.v1.rollout.reachable_url`（仅当 service=HOST 且 consumer 是 DockerRuntime 时改写为
   `host.docker.internal`）绕过，**未改动 `reference/` 或 site-packages**。在 Linux GPU 机上
   这个 shim 不触发（`platform.system()!="Darwin"`），走原生 127.0.0.1 路径。
4. **`max_turns` 不回滚已服务 turn 的工具副作用**：`max_turns=1` 时第 1 个 turn 的 bash 调用副作用
   （建文件）仍落地、reward=1.0，但第 2 个 model turn 被拒（stop=max_turns），tool 结果消息未
   commit 进 Trace。属正确语义（限制模型轮数而非工具副作用），记录备查以免后续误判为限制失效。
5. **计划 F6 核实**：`Taskset.setup(self, task, trace, runtime)` 三参签名在 5885ab9c 上成立且被
   框架按参数名注入（题 1 的 `a.py` 物化就走这个入口，rollout 全绿即证明）。与计划一致，无偏离。

---

## 6. key 安全自检声明

- key 内容全程**未落盘**、**未 print**、**未进命令行参数**：runner 在进程内从 `deepseek_api.md`
  读值直接写入 `os.environ`；日志只打印 `key status: present|missing|file_missing`（状态词，无值）。
- dump 落盘前两道防线：`scrub_secrets`（递归掩码 `authorization/api_key/...` 等键名的值 +
  字符串内 `sk-*`/`Bearer *` 掩码）+ `assert_no_secret`（检出 `sk-` 形态串或 env 里 key 字面值
  即拒绝落盘）。
- 事后全量扫描 6 个 dump：无 `sk-` 形态串（`grep -rIE 'sk-[A-Za-z0-9_-]{8,}'` 无命中），无
  裸 `authorization`/`api_key`/`x-api-key`/`secret` 字段（grep 退出码 1 = 无命中）。
- 发现 2 的跨服务误用已修复并复验：现在缺 key 时端点收到的是 `EMPTY`，不再发送任何真实凭据。

---

**2026-07-07 补充（key 补填后实跑）**：用户补填 DEEPSEEK_API_KEY 后，default×subprocess 已用真实 deepseek-chat 端点复跑：task0 reward=1.0（3 轮）、task1 reward=1.0（4 轮），stop=agent_completed，dump 为 `default_subprocess_deepseek.json`（落盘前 scrub + 事后独立扫描无 key 形态串）。"真实 provider 中继"缺口关闭，S0-3 无遗留。
