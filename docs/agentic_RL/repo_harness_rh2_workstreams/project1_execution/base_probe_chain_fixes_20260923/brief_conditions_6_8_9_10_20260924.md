# Brief：#10 工具面 / #9 auto-memory / #8 计数与窗口 / #6 提醒并入——已批准决定的实施切片

2026-09-24 / Claude（A 线）。**状态：已实施，CI1/CI2 的 Codex 针对性复核通过（见 §4；限定为本机与已记录的协议验收范围）。** 依据：[决策包 §8](decision_package_6_8_9_10_20260924.md)（用户已批准）与 [Codex 复核 §8](codex_stream_decision_review_20260924.md) 的三条修订。方向不再请示；每片给实际改动、测试参数、正式默认值是否变化、模型可见输入的变化、尚未实测的效果。顺序：#10 → #9 → #8(i) → #8 窗口/溢出/Read 接线 → #6(a)。

## 0. 两点版本绑定的提醒（不是异议）

- `CLAUDE_CODE_MAX_CONTEXT_TOKENS` 在 2.1.205 里对非 `claude-` 开头的模型名生效（CCS 里是内部变量）；压缩阈值 = 窗口 − 输出预留 − 13,000，其中 13,000 是 CC 内部常量。两者都随 CC 版本钉死（`RH2_CLAUDE_CODE_VERSION`），升级 CC 时必须重跑本 Brief 的验收。
- Codex R1 的多块残缺 SSE（完整 text 块 + 工具块开始后 HTTP 正常收尾 → CC 退出 0 并交付）在正式纯 TCP relay 下不会自然出现；A 侧不加准入规则。夹具补上该形态只为可重复验证。

## 1. 切片与验收

| 片 | 改动 | 层 | 验收 |
| --- | --- | --- | --- |
| 1：#10 + #9 | 新模块 `adapters/slime/cc_launch_conditions.py`：`CC_TOOL_SURFACE = ("Bash","Read","Edit","Write","NotebookEdit")`、`cc_tool_surface_args()` = `--tools Bash,Read,Edit,Write,NotebookEdit`、`CC_RH2_STATIC_ENV = {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}`；`launch_claude_code` 的命令固定带工具面参数（在 vendored `launch_flags` 之后、进程级 `SLIME_AGENT_CC_EXTRA_ARGS` 之前）；`claude_code_launch_env` 在 vendored `static_env` 之后并入 `CC_RH2_STATIC_ENV`（进程级 extra envs 与逐 execution 注入仍在其后）。脚本里的 `--disallowedTools Task WebFetch WebSearch` 不再是工具面的来源（保留无害）；B 线探针改用同一常量（B 线文件，只留言） | RH2 启动层；**正式默认值变化**：工具面 21 → 5，system 少 "# Memory"（2,070 字符）与 "# Session-specific guidance"（165 字符），Skill 清单消息消失 | 单测：命令含 `--tools …`、env 含 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`、逐 execution 注入仍最高优先级；真机：真实 CC 首请求 `tools` 恰为五个、无 Skill 清单消息、system 无 "# Memory"、init 无 `memory_paths`、记忆目录不创建 |
| 2：#8(i) | `count_tokens_wire.py`：先安装后构造（同 `install_capture_wire` 模式）把 vendored `_count_tokens` 路由换成 RH2 handler：`_preprocess_body` → `_translate` → `_render_token_ids`（当前服务的 tokenizer / 消息处理 / 模板，与生成同一路径），在执行器线程里计数；不建轮、不进 capture、不计 turn 预算；启动核对路由绑定 | RH2 adapter 层；正式默认值变化：count_tokens 从恒 0 变为真实计数 | 单测（真实 vendored app + 假 tokenizer）：返回值 = 渲染长度，registry 预算快照与 hook 记录不变；真机（真实 tokenizer）：超限整文件 Read 按 `行数 × 25000 ÷ 计数 × 0.85` 截断，显式范围超限报错 |
| 3：#8(ii)(iii)(iv) | (ii) 逐 execution 注入 `CLAUDE_CODE_MAX_CONTEXT_TOKENS=<config.max_context_len>`、`CLAUDE_CODE_AUTO_COMPACT_WINDOW=<同值>`、`CLAUDE_CODE_MAX_OUTPUT_TOKENS=<session_defaults.max_new_tokens>`（`max_context_len=0` 时不注入）；(iv) `SlimeBindingConfig.cc_file_read_max_output_tokens: int | None`（None = CC 默认 25,000）→ `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS`；(iii) RH2 `capture_wire` 溢出分支（`max_context_tokens` 剩余 ≤ 0）由"空 text + length"改为抛 `web.HTTPBadRequest`（Anthropic 错误体 `invalid_request_error: prompt is too long: N tokens > M maximum`）——在引擎调用之前、pending 暂存之前，不留 pending、不伪造采样；turn cap 计数沿 vendored 既有行为（请求已被接纳） | RH2 启动层 + capture wire；**数值是作业配置**，本 Brief 只用明确标记的测试参数验证机制 | 单测：溢出请求 → 400 且 registry 无 pending、无 capture、无 poison；真机（真实 tokenizer、测试参数 `max_context_len` 小值）：普通请求与摘要请求受**同一**真实上限约束，跨过一次真实上限后 CC 压缩重发并继续或有界失败；真正生成的摘要只捕获一次并计入 turn 预算；报告实际余量（固定前缀 / 阈值 / 一次大工具输出后的摘要长度），不设"固定前缀 < 阈值一半"闸门 |
| 4：#6(a) | RH2 `Rh2AnthropicAdapter(AnthropicAdapter)` 覆盖 `_preprocess_body`：先 vendored fold，再把**同一条 user 消息里、紧跟在 tool_result 之后、以 `<system-reminder>` 开头的 text 块**并入该消息最后一个 tool_result 的内容尾部；普通 user 文本、摘要指令（"CRITICAL: Respond with TEXT ONLY…"）、Skill 正文保持原角色；count_tokens 与生成共用此预处理 | RH2 adapter 层；正式默认值变化：提醒从独立 user 轮变成 tool_response 尾巴 | 回放（p6 的 617 轮 + Codex 的真实摘要请求 `dp_c8_reactive/.../messages_003.json`）：目标提醒不再清空历史 thinking；摘要指令仍在工具结果之外；训练行归属保持；不以 prompt 长度不下降为判据，不要求新模型自由生成的分行数等于旧回放 |

## 2. 不做的事

不改 reward / loss / 组准入 / 预算终止；不改 vendored 文件（全部经 RH2 层"先安装后构造"或子类）；不改 census；不加记忆文件拒绝规则；不加流交付准入规则；不冻结 32K / 4096 / 8000 为正式参数。

## 3. 实施记录（2026-09-24，Claude；四片已实施、单测与真机验收通过，待 Codex 聚焦复核）

夹具：`rh2/experiments/base_probe_fixes_20260923/stream3_formal_chain.py`（#3 的正式链夹具，`--tokenizer-dir` 用真实 Qwen3-30B-A3B tokenizer 做渲染 / decode / 计数，引擎仍是剧本；已改为构造生产子类 `Rh2AnthropicAdapter`、安装 count_tokens wire、注入生产 `bringup_leaf_facts`）与 `acceptance_startup_2.py`（桩端点 + 正式 driver）。证据 `runs/base_probe_fixes_20260923/remote/{cond1_normal,s3r_R1,s3r_S0,s3r_C1,s3r_C2,s3r_C3}/`，#6 回放 `runs/decision_package_20260924/p6_thinking/smoosh_acceptance.json`。

### 3.1 切片 1：#10 工具面 + #9 auto-memory

| 项 | 内容 |
| --- | --- |
| 改动 | 新模块 `adapters/slime/cc_launch_conditions.py`（`CC_TOOL_SURFACE`、`cc_tool_surface_args()`、`CC_RH2_STATIC_ENV`）；`bringup.launch_claude_code` 命令 = `claude -p … {vendored launch_flags} --tools Bash,Read,Edit,Write,NotebookEdit {SLIME_AGENT_CC_EXTRA_ARGS}`；`claude_code_launch_env` 在 vendored `static_env` 之后并入 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`（进程级 extra envs 与逐 execution 注入仍在其后） |
| 正式默认值变化 | 工具面 21 → 5；system 少 "# Memory"（2,070 字符）与 "# Session-specific guidance"（165 字符）；Skill 清单消息消失；auto-memory 目录不再创建 |
| 测试参数 | 无（常量） |
| 单测 | `tests/adapters/test_cc_launch_conditions.py` 4 例（参数串、优先级、命令位置、单一写入者扫描） |
| 真机（真实 CC 2.1.205，`cond1_normal`） | 首请求 `tools` = [Bash, Edit, NotebookEdit, Read, Write]，工具 JSON 60,905 → 7,780 字符；system 4,170 字符、无 "# Memory"、无 "Session-specific guidance"；messages 只有 1 条（无 Skill 清单）；init `memory_paths=None`；首请求 73,793 → 12,557 B；退出 0、所有既有期望项通过 |
| 未实测 | 对真实模型行为与成绩的影响；模型是否仍自行写笔记文件（不作验收条件） |
| B 线 | 探针 `solve_attempt.py` 的 `--disallowed-tools` 不再是工具面来源，应改读 `cc_launch_conditions`（B 线文件，留言） |

### 3.2 切片 2：#8(i) count_tokens 回真实计数（T1）

| 项 | 内容 |
| --- | --- |
| 改动 | 新模块 `adapters/slime/count_tokens_wire.py`：`install_count_tokens_wire()`（先安装后构造，替换 vendored 模块级 `_count_tokens`）、`rh2_count_tokens`（`_preprocess_body` → `_translate` → `_render_token_ids`，执行器线程里跑 tokenizer；错误回 Anthropic 形状 400；未绑定回 500）、`bind_count_tokens_adapter` + `assert_count_tokens_bound` 启动核对；bringup 接线 |
| 正式默认值变化 | count_tokens 从恒 0 变为真实计数 |
| 单测 | `tests/adapters/test_count_tokens_wire.py` 4 例（真实 vendored app + session guard + turn 预算 wire：计数 = 生成同一路径的渲染长度、fold 已生效、不计预算、无 capture、无 inflight、无 poison；模板拒绝 → 400；坏 JSON → 400；未 bind → 500；先构造后安装被启动核对拒绝；幂等） |
| 真机（真实 tokenizer，`s3r_R1`） | CC 整文件 Read 1,801 行文件 → 调 count_tokens 一次 → RH2 回 **139,052**（真实 Qwen3 计数）→ CC 截断到 274 行 / 40,306 字符（公式 1801 × 25000 ÷ 139052 × 0.85 = 275）；capture 3 条 = 3 个生成轮，turn 预算 accepted 3（计数未计入）；退出 0、交付 |
| 未实测 | 大 body 计数对 adapter 线程事件循环的占用（执行器线程里跑，未量） |

### 3.3 切片 3：#8(ii)(iii)(iv) 窗口 / 溢出 / Read 上限

| 项 | 内容 |
| --- | --- |
| 改动 | `cc_launch_conditions.cc_context_env()`：`max_context_len>0` 时逐 execution 注入 `CLAUDE_CODE_MAX_CONTEXT_TOKENS` = `CLAUDE_CODE_AUTO_COMPACT_WINDOW` = `max_context_len`、`CLAUDE_CODE_MAX_OUTPUT_TOKENS` = 会话 `max_new_tokens`、`CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` = 新配置字段 `SlimeBindingConfig.cc_file_read_max_output_tokens`（None = CC 默认）；`generate.py` 在 `HarnessLaunchSpec.env_injections` 里并入（与 #1 的 HOME/BASH_ENV 同一运输）；RH2 `capture_wire` 溢出分支（`max_context_tokens` 剩余 ≤ 0）由"空 text + length"改为抛 `HTTPBadRequest`（`invalid_request_error: prompt is too long: N tokens > M maximum`），在引擎调用与 pending 暂存之前 |
| 正式默认值变化 | `max_context_len=0`（未配置）时**不注入任何窗口变量、行为不变**；配置后 CC 窗口认知随作业；溢出响应形状从 length 变为 400 |
| 测试参数（不是正式数值） | 单测 4096 / 512 / 2000 / 10；真机 32,768 / 4,096 / 8,000；C1 反例 8,192 / 1,024 |
| 单测 | `tests/adapters/test_cc_context_window.py` 3 例（映射与空配置；dense 链 launch_spec 注入；真实 vendored app + 真实 capture wire + 假引擎：溢出 → 400 形状、引擎未调、无 capture、无 inflight、无 poison、drain 无 pending，随后短请求照常 200） |
| 真机 `s3r_C2`（被动，关掉主动压缩的测试条件） | 第 3 个请求 52,927 token > 32,768 → RH2 **400** → CC 被动压缩：摘要请求 29,347 token（**同一上限内**）→ 引擎摘要**只捕获一次**（capture 4 = T0、T1、摘要、收尾）→ 继续 → 退出 0；turn 预算 accepted 5（含被 400 的请求，沿 vendored 既有行为）；无 poison；装配 3 条叶链交付（loss 54 / 19 / 3）、评分 1 次 |
| 真机 `s3r_C3`（主动） | usage 28,049 > 阈值 15,672（32,768 − 4,096 − 13,000）→ CC 主动压缩 → 同上收尾；无 400 |
| 真机 `s3r_C1`（反例） | 窗口 8,192 + 输出预留 1,024 + 本夹具固定输入（约 3.2K）→ 主动压缩阈值为负 → CC 每轮压缩、熔断后退出 1、只发 1 个请求。只说明这一组参数不可用；阈值还取决于输出预留与固定输入成本，不据此定统一的窗口下界，也不加启动闸门 |
| 实际余量（测试参数 32,768 / 4,096） | 固定前缀（五工具 + system）3,171 token；主动阈值 15,672；一次约 28K 字符的 Bash 输出 ≈ 24.9K token；压缩后摘要请求 29.3K；不设"前缀 < 阈值一半"闸门 |
| 未实测 | 真实模型生成的摘要长度；容量不足时的有界失败形态（本夹具摘要短）；413 等其它过长错误形式 |

### 3.4 切片 4：#6(a) 提醒并入相邻 tool_result

| 项 | 内容 |
| --- | --- |
| 改动 | 新模块 `adapters/slime/rh2_anthropic_adapter.py`：`smoosh_system_reminders_into_last_tool_result(body)`（只并同一 user 消息里、紧跟最后一个 tool_result 之后、以 `<system-reminder>` 开头的连续 text 块；遇非提醒块即停）；`Rh2AnthropicAdapter._preprocess_body` = vendored fold → smoosh；bringup 改构造该子类（count_tokens 共用） |
| 正式默认值变化 | 提醒从独立 user 轮变成 `<tool_response>` 尾巴；普通 user 文本、摘要指令、Skill 正文角色不变 |
| 单测 | `tests/adapters/test_rh2_anthropic_adapter.py` 5 例（并入与翻译形状；vendored fold → 并入；摘要指令保持独立 user、提醒在指令之前才并、指令在前时两者都不动、Skill 正文不动；无 tool_result 不动、列表形 tool_result、两个 tool_result 只并最后一个之后；count 与生成共用） |
| 回放（`p6_smoosh_acceptance.py` v2，B 线 22 条 Qwen3.6 基座尝试的 617 个生成请求 / 595 相邻对，排除启动探针与夹在账本里的 count_tokens 记录；真实 Qwen3.6 tokenizer；`smoosh_acceptance_v2.json`） | 新插入 72 次：历史 thinking 清空 72 → **0**；全部相邻对清空 72 → 0；**prompt 前缀一致对**（上次 prompt 是本次 prompt 的前缀，不含 output，不是训练行归属）519 → 591；617 轮 prompt 合计 20,106,096 → 21,275,351（+5.8%，与决策包 §1.3 (a) 列一致）；Codex 反例（真实压缩请求）：摘要指令仍是独立 user、不在任何 tool 内容里。训练行 / 动作归属未在本片重测（决策包 §1.1 的回放口径） |
| 未实测 | 真实模型看到历史 thinking 后的行为；新模型自由生成的分行数（不要求等于旧回放） |

### 3.5 本地回归与一处修正

- 五目录 **1724 passed / 1 skipped**；双 lane 全绿（A 463p/343s、B 806p/0s）；ruff 通过；新增单测 4 个文件共 17 例；验证机同 17 例通过，S0 正控在最终代码上复检通过（`s3r_S0f`）。
- 修正一次：`rh2_anthropic_adapter` 首版在模块顶层静态子类化 vendored `AnthropicAdapter`，lane A（conftest 在测试模块之间重置 vendored `slime.*`）下子类绑在过期基类上，bringup 的路由 / turn 预算 wire 启动核对失败；改为 `rh2_anthropic_adapter_cls()` 调用时按当前 vendored 类构造子类（与 bringup 里所有 vendored 类延迟导入同一纪律），加了对应用例。
- 两个新测试模块按既有做法（`test_w3b_bringup_sandbox_runtime`）用 autouse fixture 把 capture / turn 预算 wire 的进程级单代归属重置成"新进程"。

### 3.6 Codex 实施复核 §9 的两项 P2 收尾（2026-09-24）

- **CI1（Read 上限缺正式作业来源）**：正式入口定为环境变量 `RH2_CC_FILE_READ_MAX_OUTPUT_TOKENS`（与 `RH2_MAX_TURNS_PER_SID` 等同一类作业配置；未设 = None；若通用透传也未提供值，则使用 CC 默认 25,000；非正整数启动即炸）。bringup 的唯一生产构造点经 `cc_file_read_max_output_tokens_from_env(os.environ)` 读入 `SlimeBindingConfig.cc_file_read_max_output_tokens`，再由既有 `cc_context_env` 逐 execution 注入。配置窗口且 RH2 显式给值时，逐 execution 注入优先于 `SLIME_AGENT_CC_EXTRA_ENVS`；RH2 未给值时，通用透传仍可提供该 CC 环境变量。验收用例 `test_read_cap_flows_from_the_formal_job_entry_to_the_collector_env`：从该环境变量 → 生产读取函数 → 配置 → dense 链 launch_spec 注入 → `claude_code_launch_env` → `launch_claude_code` 交给收集器的 env，设置值 `8000` 与未设置正控各一次；`0` / `8k` 拒绝。
- **CI2（回放分母与指标口径）**：v2 回放只取 22 条 `bp22-*` 尝试的 `/v1/messages` 生成请求（排除 `wire-test-q36-01` 与 2 条 count_tokens 记录），617 请求 / 595 对，与原回放分母一致；结果写新文件 `smoosh_acceptance_v2.json`，v1 保留；指标改名为 "prompt 前缀一致对"，不再作为训练行归属证据（§3.4 已改）。
- 非阻塞两处：§3.3 的"低于约 20K 不可用"收窄为该组参数的失败结果；压缩证据的替身边界（引擎输出、评分、静止屏障、未接真实 model-call proxy / 权重发布；C2 为单测被动路径而关掉主动压缩）不支持"所有真实任务都能恢复"或"正式窗口已定"的说法。

## 4. Codex 实施复核（2026-09-24）

详见[原复核报告 §9](codex_stream_decision_review_20260924.md)。`145cb5fd` 核心实现认可，相关回归 189 passed，未发现 P0/P1。保留两个 P2 收尾：CI1 新 Read 字段缺正式 Bringup 来源（既有 extra env 通道可用，明确一种入口并验证即可）；CI2 回放混入计数/启动探针，且 prompt 前缀一致不能代替训练动作归属。另将“20K 以下不可用”收窄为已测条件。没有新增用户决策或准入规则；正式数值仍留作业配置。本条仅为独立复核指针，不把待修项写成已实施。

**后续收口：** `716c94d5` 的 CI1/CI2 已通过[针对性复核 §10](codex_stream_decision_review_20260924.md)。主审实际构造表达式九案、29 项相关维护测试通过；617 请求回放重算与作者 v2 完全一致，旧证据保留。四片在本机与已记录的协议验收范围内收口，无剩余阻塞项；真实模型/GPU 效果和正式数值继续后置。上段保留首次实施审查的历史状态。
