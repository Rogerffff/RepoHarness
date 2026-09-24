# 决策包：#6 提醒插入清空 thinking / #8 count_tokens 与上下文窗口 / #9 auto-memory / #10 工具面

2026-09-24 / Claude（A 线）起草；事实由两个 Opus 5.5 子代理按脚本采集，A 线核对口径。**状态：事实齐全，待用户决定（四项均为训练条件，T0；#8 (i) 为 T1 可先做）。** 一份文档四项分列（Codex §14.3）：每项"现状事实 → 选项 → 对策略可见输入的影响 → 验收"，不捆成一个开关；对照实验一次只改一个因素（§9.4）。来源：[交接包](../base_model_probe_20260922_aline_handoff.md) §4/§6/§7/§8；#3 事实表见 [stream3_repro_20260924.md](stream3_repro_20260924.md)。

证据目录（本机，git-ignore）：`runs/decision_package_20260924/p6_thinking/`（回放 JSONL、summary、mechanism_examples、tokenizer 出处）与 `runs/decision_package_20260924/p8_9_10/`；脚本 `rh2/experiments/decision_package_20260924/`（未跟踪）。数字都能从落盘 JSON 复算。

## 0. 怎么读

- "实测"= 用生产同一函数 / 同一 tokenizer / 真实 CC 得到；"回放"= 把已记录的会话按候选方案重新渲染，没有跑模型；"推断"= 来自源码快照或按比例折算。
- 四项都不改 reward、预算、终止规则；改变的是策略看到的 system / tools / 消息，以及训练行的切分与长度。
- 我的建议只是建议；每项最后一行标明。

## 1. #6：提醒插入清空 thinking

### 1.1 现状事实（回放 B 线 22 条 Qwen3.6 尝试，617 轮，与生产同一 `_translate_messages` + `Qwen/Qwen3.6-35B-A3B` tokenizer，revision `995ad96e…`，chat_template sha256 `e84f32a2…`）

| 项 | 实测 | 与 B 线对照 |
| --- | --- | --- |
| 回放长度 = 探针 adapter 记录的 `prompt_tokens` | 617/617 | — |
| 相邻请求消息级前缀（去 `cache_control`）精确扩展 | 595/595 | 断点全部来自渲染，CC 没有改历史 |
| `role:system` 插入 | 72 = Task 提醒 71 + 文件修改说明 1 | 72 ✓ |
| Skill 正文注入（模型调 `Skill` 后 user 文本块紧跟 tool_result） | 2 | B 线未计 |
| thinking 清空对 | **74**，22/22 条与插入逐条相等；无插入不清空、无清空不插入 | — |
| 清空段解码 | 505 段全部是 `<think>…</think>\n\n`；70 对去掉该段后逐字相等，另 4 对同时被 CC 改参（#4） | — |
| 每次清空规模 | 涉及 1–14 个 assistant 轮（中位 6）；净丢 98–4,459 token（中位 462.5，合计 62,399） | — |
| prompt 严格回落 | 32 次；另 42 次清空被新增工具输出掩盖 | 32 ✓ |
| moto-5134-a1 四个插入点增量 | +279 / −43 / +222 / −32；`preserve_thinking` 下 +2,810 / +697 / +523 / +306 | 与 B 线相同；B 线"保留"估算 +2,695/+675/+501/+284 |

训练侧（vendored `TrajectoryManager` fork_threshold=0 + 生产 `export_leaf_identity_spans_with_coverage`）：训练行 **132**，`fork_events` 84 = 74 次清空点 + 5 次清空与改参同轮 + 5 次与 #6 无关；`input_tokens_total` 4,379,385；`turns_trained` 617/617、可训 token 167,985——**各方案完全相同**，即现状没有动作从 loss 里消失；#6 的代价是上下文里 thinking 周期性消失，以及每次分行把长前缀复制一遍。

### 1.2 机制（实测）

- Qwen3.6 模板：`last_query_index` = 从后往前第一条 `role==user` 且内容不被 `<tool_response>` 包住的消息；`role:tool` 不参与。只有 `preserve_thinking` 为真、或该 assistant 位于 `last_query_index` 之后，才渲染 `<think>…</think>`。非首位 `role:system` 直接 `TemplateError('System message must be at the beginning.')`（实测）。
- 所以 vendored adapter 必须 fold：提醒包成 `<system-reminder>…</system-reminder>` 追加到工具结果所在 user 消息 → `_translate_messages` 又拆成独立 `role:user` → 模板当作新 query → 此前所有 thinking 丢弃。
- CC 2.1.205 全部请求带 `anthropic-beta: …mid-conversation-system-2026-04-07…`；CCS 快照的 `smooshSystemReminderSiblings` 只合并 user 消息里以 `<system-reminder>` 开头的文本块，不处理 `role:system`（推断：该 beta 下 CC 不会自己合并）。
- Qwen3-30B-A3B 模板同样的 last_query 规则但**没有** `preserve_thinking` 变量（旁证）。

### 1.3 选项与实测影响（回放）

所有选项共有的非 #6 断点 40 个，任何选项都消除不了：23 次 CC 给 Edit 补 `replace_all:false`、11 次去掉 `cd /testbed && `、4 次调换/删参数（以上属 #4）、2 次模型输出空/未闭合 think。**"相邻请求 token 前缀单调"不能作为验收标准**（与 §12 提醒一致）。

| 指标 | 现状 | (a) 只并 `<system-reminder>` 文本进最后一个 tool_result（CC 规则） | (a2) 并入全部 user 文本块 | (b) 渲染传 `preserve_thinking=True` | (c) 去掉 Task 提醒（模拟删 Task* 工具） |
| --- | --- | --- | --- | --- | --- |
| #6 类清空对 | 74 | 2（Skill 正文残留） | 0 | 0 | 3 |
| 相邻对 CLEAN | 485 | 553 | 555 | 555 | 552 |
| fork_events / 训练行 | 84 / 132 | 7 / 64 | 5 / 62 | 5 / 62 | 8 / 65 |
| input_tokens_total | 4,379,385 | 2,212,759 | 2,174,880 | 2,175,420 | 2,223,815 |
| prompt 均值 / p90 / 最大 | 32,587 / 46,598 / 63,818 | 34,482 / 50,231 / 77,249 | 34,491 / 50,231 / 77,249 | 34,499 / 50,254 / 77,277 | 34,266 / 49,770 / 76,570 |
| 超过 32K / 64K 的轮 | 260 / 0 | 283 / 20 | 283 / 20 | 283 / 20 | 281 / 19 |

对策略可见输入的具体改变：
- (a)/(a2)：提醒从独立的 `<|im_start|>user\n<system-reminder>…` 变成最后一个 `<tool_response>` 的尾巴（每次插入 −4 token）；此前 thinking 全部留在上下文（例：mypy-11236-a2 末轮带 thinking 的 assistant 59/59，现状 5/59）。改在 RH2 层：`_run_turn` 先 `_preprocess_body`（vendored fold）再 `_translate`，可在 RH2 覆盖 `_preprocess_body`（`bringup.py:1210` 直接构造 `AnthropicAdapter`），vendored 零改动；未在真实 adapter 进程里实现或测试。
- (b)：全部历史 thinking 保留，提醒仍是独立 user 轮（比 (a) 每次多 4 token）；逐条 attempt 最大 prompt +393（+1.4%）到 +13,459（+21.1%），逐轮合计 +0.5% 到 +12.1%，训练输入 token −30.5% 到 −64.0%（例外 moto-5752-a1 +4.0%）。**只对 Qwen3.6 模板成立**。改在 RH2 层：`_render_token_ids` 是 vendored 模块级函数，可像 capture_wire 替换 `call_sglang_generate` 那样替换。
- (c)：只删 Task 提醒残留 3 次；真正删 Task* 六个工具每个 prompt 少 2,734 token（TaskCreate 647 / TaskGet 264 / TaskList 297 / TaskOutput 391 / TaskStop 212 / TaskUpdate 923）；22 条中 4 条用过 Task*（652 次工具调用中 15 次）；提醒节奏首次第 5–12 次请求、之后每 5–14 次；触发条件（CCS 快照，非 2.1.205 实测）：清单里有 TaskUpdate 且距上次 TaskCreate/TaskUpdate 与上次提醒都 ≥10 条 assistant 消息。归 #10。

### 1.4 验收（若采纳）

- 回放口径：#6 类清空对归零（(a) 允许 Skill 正文的 2 次，或与 (a2) 同时决定）；`fork_events` 中此类分行归零；40 个非 #6 断点不在本项验收内。
- 真实口径：真实 CC + 真实 adapter 进程，抓取 debug_callback 落盘的逐消息 token 数，相邻请求在插入点不回落；`turn_coverage` 的分行数与回放一致。
- 未核实、需在实施后看的：模型看到自己旧 thinking 后的行为、B 线记录的"把提醒当用户消息"副作用是否消失、32K 窗口下的表现（#8）。

**建议**：(a2)（在 RH2 层覆盖 `_preprocess_body`，把工具结果之后的全部 user 文本块并入最后一个 tool_result）作为默认；它不依赖模板变量、对 Qwen3-30B 同样有效、每次插入还少 4 token；(b) 只在基座定为 Qwen3.6 时作为对照。是否删 Task* 工具在 #10 里决定。

## 2. #8：count_tokens 与上下文窗口

事实来自 25 次真实 CC 2.1.205 运行（真实容器 + 桩端点，经正式 `ClaudeCodeDriver.run`，`SLIME_AGENT_CC_EXTRA_ENVS` 正式通道注入环境变量）+ 从 2.1.205 原生二进制内嵌 JS 读出的静态代码（`runs/decision_package_20260924/p8_9_10/remote/dp_logs/binscan_cc_2.1.205.txt`）。"代理 token"= 用 vendored adapter 同一渲染路径 + Qwen3-30B-A3B tokenizer 计数，只看量级。

### 2.1 交接包里三个前提与 2.1.205 实测不符

1. 整文件 Read 超过 25,000 token 上限时，CC **不是拒绝而是截断**（保留前 `行数 × 上限 ÷ 计数 × 0.85` 行，追加一条 272 字符的 `system` 说明 "[Truncated: PARTIAL view … or Grep …]"——而工具面里根本没有 Grep）。只有显式 `offset/limit` 的超限读才报错。
2. 默认配置下**没有主动压缩**：窗口来源为 "auto" 且被动压缩可用时主动压缩直接关闭；桩把 usage 报到 350K，0 次压缩、也不阻断，`contextWindow=200000`。
3. `CLAUDE_CODE_AUTO_COMPACT_WINDOW=32768` **不生效**：低于 100,000 的值被 `Math.max(1e5, …)` 抬到 100,000；阈值 = 窗口 − 预留输出（默认 20,000）− 13,000。

### 2.2 count_tokens 现状（实测 + 静态）

- 只在整文件 Read 时调用，且 CC 自己的估计（字符/4）超过上限的 1/4（6,250）才调；其它运行一次都没调。请求体只有 `{model, messages:[一条 user = 文件全文], tools:[]}`（测试文件 239,179 字符 → 请求体 241,055 B）。
- 回 0（现状）：全文 247,077 字符进入工具结果，下一请求 325,468 B、代理 118,008 token；回真实估计（字符/4 = 59,795）：截断到第 1–640 行，下一请求 51,825 token；回 null：退回 CC 自估，同截断；`CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS=8000` + 真实估计：截断到 204 行、28,716 token。
- 推断：该文件真实 Qwen3 计数 93,430；按真实计数截断后约 409 行 / 约 2.1 万 token，加约 1.8 万固定开销仍超 32K——**只修计数不够，Read 上限要和窗口一起定**。

### 2.3 压缩触发（usage 为桩合成数字）

| 条件 | 实测 | 静态公式 |
| --- | --- | --- |
| 无变量，usage 150K→350K | 0 次压缩、不阻断 | 主动压缩关闭 |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW=32768` | 70,013 压缩、60,013 不压 | 抬到 100,000；阈值 67,000 |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=15` | 0 次 | — |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS=32768` | `modelUsage.contextWindow=32768`，usage 38K 仍不压；Skill 清单预算随之缩小 | 2.1.205 对非 `claude-` 模型名接受此变量 |
| 上一行 + `AUTO_COMPACT_WINDOW=100000` | 每轮都压：2 次本地失败 `too_few_groups`、3 次成功后 `rapid_refill_breaker`，CC 退出 1，12 步只完成 5 步 | 阈值 32,768 − 20,000 − 13,000 = −232 |
| 上一行 + `CLAUDE_CODE_MAX_OUTPUT_TOKENS=4096` | 请求 `max_tokens=4096`；17,013 压缩、14,013 不压，共 2 次，正常结束 | 阈值 32,768 − 4,096 − 13,000 = 15,672 |
| 桩对第 3 个请求回 400 "prompt is too long: 40000 tokens > 32768 maximum" | **被动压缩后重发，正常结束** | — |
| 回 vendored adapter 溢出时的形状（空 text + `stop_reason:max_tokens`） | CC 追加 user 文本 "Output token limit hit. Resume directly…" 重发（这段留在后续历史）；连续 4 次空回复后 CC 自造 "API Error: …exceeded the 32000 output token maximum…"，退出 1、`is_error`，**始终不触发压缩** | 形状来自 `common.py:457–467`、`anthropic.py:170–177` |

推断：现状工具面固定开销约 1.8 万 token 已高于 15,672 的阈值，会反复压缩直到熔断；只留核心五个工具时约 0.36 万，远低于阈值（与 #10 耦合）。压缩请求 = 完整历史 + 追加 6,361 字符 user 文本（"CRITICAL: Respond with TEXT ONLY…"），system 与工具不变；压缩后只剩 3 条消息（摘要 user、最后一次 tool_use、其结果），Skill 清单不再重发。`contextWindow` 只出现在 `result.modelUsage`，init 事件没有。

### 2.4 选项

| 选项 | 内容 | 对策略可见输入 | 层 / T 级 |
| --- | --- | --- | --- |
| (i) adapter 回真实计数 | `/v1/messages/count_tokens` 用所服务的 tokenizer、经生产同一翻译 / 模板路径（含 system / tools / 提醒处理）计数；不建轮、不耗预算 | 超限整文件读被截断（附截断说明），显式范围读超限报错；工具结果变短 | RH2 层覆盖 vendored `_count_tokens` 路由或登记补丁；**T1 窄修，Codex §14.3 已同意可先做** |
| (ii) 给 CC 与服务一致的窗口 | `CLAUDE_CODE_MAX_CONTEXT_TOKENS=<max_context_len>` + `CLAUDE_CODE_AUTO_COMPACT_WINDOW=<同值>` + `CLAUDE_CODE_MAX_OUTPUT_TOKENS=<max_new_tokens>`（阈值 = 窗口 − 输出预留 − 13,000） | 会出现压缩摘要轮（6,361 字符提示 + 3 条消息的重建历史）；要求固定开销远低于阈值（依赖 #10） | 启动环境常量（RH2 `claude_code_launch_env`），T0（训练条件） |
| (iii) adapter 溢出改回 400 "prompt is too long: N tokens > M maximum" | 代替空 text + `max_tokens` 形状，让 CC 走被动压缩而不是 4 次空回复后退出 1 | 同 (ii) 的压缩轮；不再有 "Output token limit hit. Resume directly…" 留在历史里 | adapter 溢出分支（vendored 行为）→ RH2 层 / 登记补丁，T1 强报告 |
| (iv) Read 上限对齐窗口 | `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS`（如 8,000）代替 CC 面向 200K 的 25,000 | 单次 Read 最多约 8K token | 启动环境常量，T0 |

### 2.5 验收

- (i)：同一大文件，整文件读截断到 `行数 × 上限 ÷ 真实计数 × 0.85` 行、显式范围超限报错；count_tokens 不产生 capture 记录、不计入 turn 预算（现有 `test_real_adapter_turn_cap_*` 已覆盖不计预算）。
- (ii)/(iii)：桩合成 usage 下压缩在算出的阈值触发（如 15,672）；adapter 溢出时 CC 压缩后继续、不退出 1；固定开销（首请求 token）低于阈值的一半。
- 未核实：真实 tokenizer 下的计数与阈值；413 等其它"过长"形式能否触发被动压缩；仅静态可见的阻断阈值（窗口 − 预留输出 − 3,000）；adapter 如何记账空 length 轮。

**建议**：(i) 现在就做（T1）；(ii)+(iii)+(iv) 与 #10 一起决定，窗口数值随 I19。

## 3. #9：auto-memory

### 3.1 现状（实测）

system 里 "# Memory" 一节 2,070 字符（原文在 `analysis.json` 的 `baseline_memory_section_text`），指定 `/home/agent/.claude/projects/-testbed/memory/` 并写明"目录已存在、直接用 Write 写"；init 事件 `memory_paths.auto` 指向同一目录；CC 启动时建出该空目录。B 线观测：2/67 条写过记忆文件，其中 1 条写进 `/testbed` 混入候选补丁。

### 3.2 选项与实测效果

| 做法 | 效果 |
| --- | --- |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`（经 `SLIME_AGENT_CC_EXTRA_ENVS` 正式通道） | 该节消失：system 6,219→4,148 字符；首请求 −2,116 B、代理 −464 token；init 无 `memory_paths`；目录不再创建；工具与清单不变 |
| `~/.claude/settings.json` 加 `autoMemoryEnabled:false` | 请求除 metadata 外与上一行逐字节相同 |
| CLI `--settings '{"autoMemoryEnabled":false}'` | 同上 |
| 会话中途让 CC 自己写 settings | 无效：settings 只在启动时读 |

静态优先级（2.1.205）：环境变量为真 → 关；环境变量显式假值 → 强制开、压过 settings；`--bare`；settings 键；默认开。顺带：CC 启动后会往 settings.json 自行写入 `skipDangerousModePermissionPrompt:true`。

对策略可见输入：只少 system 的 "# Memory" 一节，其余不变。不改 census（公共契约；记忆文件名任意）。

### 3.3 验收

请求 system 无 "# Memory"；init 无 `memory_paths`；census 的 `/testbed` 新增文件里无记忆形态文件（后者要真实模型才能完全核实）。

**建议**：在 RH2 的启动环境常量里加 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`（单一写入者，A 线脚本与探针共用）。

## 4. #10：工具面

### 4.1 现状（实测，`dp_t10_base`，数字可由 `analysis.json` 复算）

- 21 个工具；工具数组 JSON 60,905 字符，非核心 53,164（87.4%），Workflow 21,088（34.6%）；核心五个 = Bash / Read / Edit / Write / NotebookEdit；**Grep / Glob 本来就不在**（Read 的截断说明却让模型用 Grep）。
- system 两块共 6,219 字符；Skill 清单是 `messages[1]` 的一条 `role:system` 会话中系统消息（5,867 字符、14 项；vendored adapter 折进前一条 user 作 `<system-reminder>`，即 #6 的插入之一）。首请求 73,793 B，代理 18,190 token（工具 15,251），约占 32K 的 55%。
- 清单里的描述：deep-research "fan-out web searches, fetch sources"；init 会写 CLAUDE.md；fewer-permission-prompts 会写 `.claude/settings.json`；code-review 带 `--comment/--fix` 会往 PR 发评论或改代码；review 审 GitHub PR；loop 按间隔重复；claude-api "never answer from memory"。

### 4.2 选项与实测效果（相对现状）

| 条件 | 工具数 | 首请求字节 | 代理 token | Skill 清单 |
| --- | --- | --- | --- | --- |
| (a) 现状 `--disallowedTools Task WebFetch WebSearch` | 21 | 73,793 | 18,190 | 在 |
| (b) `--tools Bash,Read,Edit,Write,NotebookEdit`（或 disallow 16 个非核心名，逐字节等价） | 5 | 14,673（−80.1%） | 3,636（−80.0%） | 消失 |
| (b″) 现状 + `--allowedTools` 核心五个 | 21 | 同 (a) | 同 (a) | 在（`--allowedTools` 只是权限放行，不改请求） |
| (c) 现状 + 禁用 `Skill`（或 `--disable-slash-commands`，逐字节等价） | 20 | 65,485（−11.3%） | 16,278（−10.5%） | 消失 |

被禁用的工具是从请求 `tools` 里真正移除，不只是 CC 拒绝调用。去掉 Skill 同时去掉：清单消息（5,867 字符）与 system 的 "# Session-specific guidance" 一节（165 字符）；system 其余与对话消息不变。

与其它项的耦合：(b) 顺带删掉 Task*（#6 的 71/74 次插入来源、每 prompt 2,734 token 的 schema）与 Skill（#6 的 2 次 Skill 正文注入）；(b) 把固定开销降到约 0.36 万 token，是 #8 (ii) 在 32K 窗口下可行的前提。B 线观测的非核心工具调用：DeepSeek 0/776、Coder 40/932、Qwen3.6 17/652。

### 4.3 验收

首请求 `tools` 恰好是所选集合；Skill 清单消息不存在；首请求 token 数落在预期区间；对照实验一次只改这一个因素。未核实：对真实模型行为与成绩的影响（需要真实基座）。

**建议**：(b) `--tools Bash,Read,Edit,Write,NotebookEdit` 作为训练条件；启动参数常量单一写入者（A 线脚本与探针 `--disallowed-tools/--tools` 共用一个来源）。

## 5. 组合与对照顺序（建议）

| 序 | 项 | 改动 | 层 | 决定 |
| --- | --- | --- | --- | --- |
| 1 | #10 (b) | `--tools` 核心五个 | 启动参数常量 | T0，用户 |
| 2 | #9 | `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` | 启动环境常量 | T0，用户 |
| 3 | #8 (i) | count_tokens 回真实计数 | RH2 adapter 层 | T1，可先做 |
| 4 | #8 (ii)(iii)(iv) | 窗口 / 输出预留 / 溢出 400 / Read 上限 | 启动环境常量 + adapter 溢出分支 | T0（数值随 I19） |
| 5 | #6 (a2) | RH2 层覆盖 `_preprocess_body`，提醒并入最后一个 tool_result | RH2 adapter 层 | T0 |

理由：1 先定，因为它同时改变 #6 的插入来源与 #8 的固定开销；#6 在 1 之后再看残余（文件修改说明 1 次、Skill 正文 0 次）决定是否还需要 (a2)；每一步各跑一次同题对照，只改一个因素。

## 6. 本轮没有做的事

没有跑真实基座（所有 token 数是代理计数或回放）；#6 的行为影响、#9 关闭后模型是否仍写"记忆"文件、#10 对成绩的影响都要真实模型；CC 源码只看了 2.1.205 二进制内嵌 JS 的摘录，没有 CCS 同版本源码。
