# 基座探针（2026-09-22）A 线交接包：链路与接口问题

2026-09-23 / Claude（B 线）。状态：**建议**，只读分析；没有改代码，没有运行容器、模型或网络。来源：[运行记录](base_model_probe_run_20260922.md) §7.2–§7.5b、§8.3、§9，19 份格子报告与 10 份单条报告，以及网关 / adapter 原始留证。写入本文件不等于已通知 A 线。

**路径简写**：`GW`=`runs/base_probe_20260922/remote/gateway`；`AT`=`runs/base_probe_20260922/remote/runs/matrix/attempts/<task>/<solver>/<aN>`；`AN`=`runs/base_probe_20260922/analysis`；`SA`=`rh2/src/slime/agent`；`RS`=`rh2/src/repoharness2/adapters/slime`；`CCS`=`reference/claude-code-typescript-src`（本地 Claude Code 源码快照，约 2026-05，**不是 2.1.205**，只用来参考机制）。

**计数口径**：`cross_trajectory_stats.json` 的接口字段只覆盖 47 条格子报告（10 条单条报告为 null，10 条任务级报告未覆盖）。标"复算"的数字覆盖全部 67 条：逐条比较 `GW/<solver>/<attempt_id>/resp_<n>.sse` 与第 n+1 次请求中回放的同一 assistant 消息，比较口径与 `TrajectoryManager._find_mount_point` 相同（dict 相等）。与 stats 重叠的 47 条中，45 条完全一致；另 2 条各差 1，原因是格子报告把 `replace_all` 单列。

**验收总原则**（Codex §9.3 工作包 A）：先用窄证据证明问题在原条件下出现、在候选修法下消失。模拟引擎只能核对控制流；缺少真实采样 ID 或 logprob 时，不能作为数值训练验收。按文件分成两块，各指定一名写入者：启动 / 日志块是 #1、#2、#9、#10；adapter 块是 #3、#4、#5、#6、#8。

下文按对训练正确性的影响排序，标题中的 #n 是任务清单编号。

## 1. #1 actor 拿不到项目解释器

**现象与证据**：在 `original` 条件下，三题 agent 的 `BASH_ENV` 都为空，`python` 指向 miniconda base 3.11.5，也没有 pytest；`import conan/dvc/moto` 全部失败。66 条有效求解都是在诊断变体 `bash_env_v1` 下完成的，结论不能直接外推到正式链。

**正式链位置（已核实，源码）**：这里有两处彼此独立的缺口。① **路径不可读**：激活文件写在 `/root`，而 rollout profile 把 `/root` 列为隐藏路径，启动前探针还要求它对 agent 返回 DENIED。② **未注入**：`env_injections` 只写进 `HarnessLaunchSpec`，调用 driver 时没有传下去；CC 子进程的环境只来自 `ANTHROPIC_*`、静态键和进程级 `SLIME_AGENT_CC_EXTRA_ENVS`。只修其中一处仍然无效。`public_hints` 写着"pre-activated conda env"，与现状不符；该字段不进 prompt。

**最小复现**：直接看已有产物（见下表）；或在 CPU 上用题目镜像运行 `solve_attempt.py --mode dev-check --actor-env original`。

**候选修法与验收**：把激活文件放到 root 属主、agent 只读的 `/rh2/bash_env`；把 `launch.env_injections` 经 driver 按 execution 注入 CC 子进程，不经过进程级全局变量；启动前探针增加两项检查：agent 可读但不可写，以及经 CC 同形 launcher 得到的是 testbed 解释器。验收：三题修复后在 `original` 下的 agent 环境事实与 `bash_env_v1` 一致，dev-check 通过，census 不变。**T1**（落实既定设计；若改 schema 则升级）。`envpack/materialize.py` 由 A、B 线共用，需要指定单一写入者。

| 类别 | 指针 |
|---|---|
| 事实 | `runs/base_probe_20260922/remote/runs/p1_devcheck/conan-io__conan-15422/original/facts/agent_env_facts.txt` L7–16；同目录 `dev_check_output.txt` L10；`facts/prelaunch.json` L69 |
| 路径 | `rh2/src/repoharness2/envpack/materialize.py:47`；`RS/sandbox_profile.py:339, 1592–1593`；`RS/generate.py:4856–4873` |
| 注入 | `RS/generate.py:2934`（只记录）、`:2960`（未传）；`RS/bringup.py:432, 506`；`SA/harness/claude_code.py:57–71` |

## 2. #2 harness 轨迹文件对 agent 可读

**现象与证据**：首轮 18 条轨迹写在仓库树内（in_tree），其中 2 条碰到了 `/testbed/.harness/trajectory.jsonl`。DVC5839/DeepSeek/a2 有 17/69 次调用在 grep 这个文件，还把自己的编辑当成"参考解"比对；第 59–69 次调用全部耗在这里，最后撞上 60 回合上限。Moto5134/DeepSeek/a2 的 `grep -rn` 偶然命中该文件，模型判定为噪声。`git status` 会显示 `?? .harness/`。扩量轮改写到 `/tmp/.rh2_harness/`，只解决了文件位置：目录仍归 agent 所有（权限 0700），同一 UID 仍能读。

**正式链位置（已核实，源码）**：`run_agent` 在 `{workdir}/.harness` 建目录并 `chown agent`，stream-json 由 agent 身份的 shell 重定向写入。census 排除了 `.harness/`，只能防止它混入候选，挡不住模型读取。rh2 源码中没有读取该文件内容的消费者，census 只对排除区做路径集合审计。另有一处相邻问题（读码发现，未验证）：`/tmp/.run.sh` 与 `/tmp/.run.done` 也是 agent 可写的控制文件。

**最小复现**：在 CPU 容器里经 `run_agent` 启动任意命令，再用 agent 身份 `cat` 该文件；也可直接看下表中的已有产物。

**候选修法与验收**：让写端改由非 agent 身份持有，例如 root 从 FIFO 读取后写入只有 root 可读的文件，或在宿主侧收集 stdout；agent 对该路径没有读权限。不改 baseline policy：`.harness/` 排除区属于公共契约，改动它是 T0。验收：agent 身份的 `ls` / `cat` 失败，CC 输出完整回收，census digest 不变。**T1**（强化边界）。`SA/harness/common.py` 是 vendored 代码，按 vendoring 约定修改，或在 `RS` 层包装。

| 类别 | 指针 |
|---|---|
| 证据 | `AN/iterative__dvc-5839/deepseek-v4-pro/a2.md` L18、T10/T11（transcript L2886–3135、3853–4240）；`AN/getmoto__moto-5134/deepseek-v4-pro/cell.md` L65 |
| 位置 | `SA/harness/common.py:107–122`；`SA/sandbox.py:106–117`；`rh2/src/repoharness2/contracts/baseline_manifest.py:98–103`；探针 `solve_attempt.py:384` |

## 3. #3 上游流中断被 CC 当成功

**现象与证据**：DVC6954/DeepSeek/a1 的第 11 次响应在首字节之后被上游复位，`resp_11.sse` 只有 949 B，停在 `content_block_start(tool_use Read)`。CC 仍报 `subtype=success`、退出码 0，空补丁按 noop 得 0（旧网关"正常收尾"是读码推断）。Codex 回扫 2,326 份 SSE 只此一例。现网关读流异常即 `abort()`，仍有两处缺口：① 上游干净 EOF 但缺 `message_stop` 时照常 `write_eof()`；② relay 的 `pipe` 吞掉异常后正常 `close()`，CC 侧可能只收到 FIN（读码推断）。

**正式链位置**：**已核实（源码）**：adapter 写完整段 SSE 后才 `record_turn`，客户端断连则回 499、不记这一轮；capture 在 `record_turn` 时提交；终止只看退出码、预算和 poison，不读 CC 的 `result`。**推断**：relay 或 adapter 中途失败时，若 CC 仍把残缺流当完整消息并退出 0，已提交的末轮（含 CC 未执行的工具调用）会带 reward 进训练。**未核**：正式链没有做过故障注入。

**最小复现（CPU）**：真实 CC 2.1.205 + 桩端点，经正式 relay 发送四种流：① 完整；② 中途 RST；③ 分块传输正常结束但缺 `message_stop`；④ 中途 FIN、没有分块结束标记。②③ 可直接用 `resp_11.sse` 构造。

**候选修法与验收**：先测后改：逐种记录 CC 退出码与 `result`、adapter 是否提交该轮、是否 poison、是否装配、是否成为可训的 0 分样本。B 线另补探针网关：未见 `message_stop` 不 `write_eof()`，改为中止连接。正式链若新增"末轮未完整交付即剔除"，属 **T0**。

| 类别 | 指针 |
|---|---|
| 证据 | `GW/deepseek/bp22-deepseek-v4-pro-dvc-6954-a1/resp_11.sse`、`responses.jsonl` seq 11；`AT` 下同一条的 `attempt.json` 字段 `trajectory_summary.cc_result`；`runs/base_probe_20260922/codex_review_20260922/sse_completion_scan.json` |
| 位置 | `SA/adapters/common.py:359–391`；`RS/capture_wire.py:19–24, 1475–1478`；`RS/generate.py:3141–3155`；`RS/sandbox_profile.py:869–881`；探针 `model_gateway.py:214–221, 257–264` |

## 4. #6 Qwen3.6 的 thinking 被周期性清空

**现象与证据**：CC 在最新 `tool_result` 之后追加 `role:system`（Task 提醒或"文件已被修改"说明）。复算：22/22 条 Qwen3.6 尝试都有插入，共 72 次（Task 提醒 71、文件修改说明 1）；617 轮中 prompt token 严格回落 32 次；stats 覆盖的 17 条清空数与插入数逐条相等（53）。Moto5134/a1 四个插入点实测增量 +279/−43/+222/−32，吻合"清空"估算 +212/−47/+206/−51，不符"保留"估算 +2695/+675/+501/+284。副作用：mypy17071/a2 把提醒当成"用户报告测试失败"多跑一轮；Moto5134/a1 的 thinking 写 "The user wants me to continue"。

**正式链位置**：**已核实（源码）**：vendored adapter 把提醒追加到前一条 user（即工具结果消息），翻译时又拆成独立 `role:user`；渲染不传 `preserve_thinking`；capture wire 不改这些环节。**推断**：Qwen3.5/3.6 模板只保留最后一条真实 user 之后的 thinking（参考渲染器同逻辑），每次插入丢弃此前全部 thinking，I01 B 下每次新开一个训练行。**未核**：渲染后的 prompt 未落盘。

**最小复现（CPU）**：用 Qwen3.6 tokenizer 对 `GW/q36/<id>/requests.jsonl` 相邻两次请求重跑"折叠→翻译→`apply_chat_template`"，比较 token 前缀；或由 B 线在探针 `qwen_adapter_server.py` 的 debug_callback 落盘逐消息 token 数。

**候选修法与验收**：(a) 把 `<system-reminder>` 并入同条消息的最后一个 tool_result（同 CCS `smooshSystemReminderSiblings` 思路）；(b) 渲染传 `preserve_thinking=True`；(c) 去掉 Task* 工具（只消除 71/72）。验收：相邻请求 token 前缀单调，`turn_coverage.fork_events` 中此类分行归零。三者都改变策略可见的输入，**T0**。

| 类别 | 指针 |
|---|---|
| 证据 | `AN/getmoto__moto-5134/qwen3.6-35b-a3b/a1.md` L25；`AN/python__mypy-17071/qwen3.6-35b-a3b/cell.md` L11、L50；`GW/q36/bp22-qwen3-6-35b-a3b-dask-8597-a2/requests.jsonl` 末次请求 idx 24/33/40 |
| 位置 | `SA/adapters/anthropic.py:55–56, 81–120, 291–350`；`SA/adapters/common.py:58–73`；`reference/renderers/renderers/qwen35.py:285–296, 890–897`；`CCS/utils/messages.ts:1819–1835` |

## 5. #4 CC 改写回放的工具参数

**现象与证据（复算，67 条）**：67/67 条都有改写：2,227 个工具调用轮中 307 轮（13.8%）、2,360 个调用中 333 个在回放时与模型原样不同。类型：去 `cd /testbed && ` 147、补 `replace_all:false` 90、Write 行尾空白 74、Edit `new_string` 行尾空白 25。按轮：DeepSeek 106/697（15.2%）、Coder 166/932（17.8%）、Qwen3.6 35/598（5.9%）。另有 51 个调用 dict 相等但键序不同（Coder 45）。stats 覆盖的 47 条合计 222（78/113/31）。CCS 的 `normalizeToolInput` 恰有这三类改写。

**正式链位置**：**已核实（源码）**：消息树按 dict 相等挂载；阈值 0 关闭改写合并，被改写的轮成为死端叶（仍训练一次）；token 级漂移一律 FORK。**推断**：键序不同虽过 dict 相等，模板按键序渲染参数，仍会 token 级分行。把改写、键序、Qwen3.6 插入点都当分行边界、行长取"该轮 prompt+output"估算：60 回合预算下 Coder 每个 execution 中位 10 行、总 token≈单行 7.9 倍，Qwen3.6 中位 5.5 行、4.6 倍。可训 token 不减，增加的是 loss_mask=0 的前缀重复。

**最小复现**：上面的比较只需读取 `GW/*`。正式口径用 I01 已有的 `turn_coverage`（`fork_events`、`training_rows`、`input_tokens_total`），在真实 CC 流量上实测。

**候选修法与验收**：先用实测替换本估算；成本不可接受时，可"识别 CC 已知规范化后按采样消息匹配与渲染"，接近已定暂缓的 I01 C 路线，属 **T0**。只加观测为 T2。

| 类别 | 指针 |
|---|---|
| 位置 | `SA/trajectory.py:169–191, 352–368, 394–395`；`RS/bringup.py:235`；`reference/renderers/renderers/qwen35.py:1009–1010`；`CCS/utils/api.ts:566–660` |
| 首轮原例 | `AN/conan-io__conan-15422/qwen3-coder-30b-a3b-instruct/a1.md` L89（7/32）；`AN/getmoto__moto-5134/qwen3-coder-30b-a3b-instruct/a2.md` L63（5/59） |

## 6. #8 count_tokens 返回 0，以及 CC 对上下文窗口的认知

**现象与证据**：本探针中 CC 只在大文件内容时调 `count_tokens`（请求体是一条 user 消息，内容为 33–77 KB 的整个文件）：67 条中 15 条共 19 次；DeepSeek 端点回真实数（13,065–13,313），两款自部署都在 1 ms 内回 0。网关不特殊处理这条路径，0 来自 vendored adapter（格子报告"网关直接回"不准确）。Coder Dask8597/a2 计数后整读 `slicing.py`，prompt 19,942→47,061。67/67 条 CC 都报告 `slime-actor` 的 `contextWindow=200000`。

**正式链位置**：**已核实（源码）**：正式链是同一个回 0 的 `_count_tokens`，其注释称"每轮都调、只作提示"，与观测不符。**推断（CCS）**：Read 的 25,000 token 上限因此失效，上例本可能被拒；自动压缩阈值约 167K，而现有脚本默认上下文 32,768、CC 固定开销已约 1.9 万 token，I19 的"恢复正常压缩"大概率不触发，adapter 会先回空的 `length`。**未核**：2.1.205 的实际行为，以及 CC 对空回复的反应。

**最小复现（CPU）**：真实 CC + 桩端点：读一个超过 25K token 的文件，比较计数回 0 与回真实值；让桩端点报告递增 usage，看压缩触发点。

**候选修法与验收**：adapter 用所服务的 tokenizer 计数；给 CC 设与服务上下文一致的窗口（CCS 有 `CLAUDE_CODE_AUTO_COMPACT_WINDOW`，2.1.205 待核）。验收：超限 Read 被拒，压缩先于服务上限触发。会改变轨迹长度分布，至少 **T1 强报告**，建议并入 T0 决策包。

| 类别 | 指针 |
|---|---|
| 证据 | `GW/coder/bp22-qwen3-coder-30b--conan-15422-a3/{requests,responses}.jsonl`；`GW/coder_adapter/bp22-qwen3-coder-30b--dask-8597-a2.turns.jsonl` turn 3→4；`AT/*/attempt.json` 字段 `cc_result.modelUsage` |
| 位置 | `SA/adapters/anthropic.py:50, 277–281`；`CCS/tools/FileReadTool/FileReadTool.ts:755–771`；`CCS/services/compact/autoCompact.ts:30–92`；`rh2/experiments/p3_preflight/j4_full_step.sh:92` |

## 7. #10 工具面（训练条件，只列证据与选项）

**现象与证据**：用 `--disallowedTools Task WebFetch WebSearch` 禁用后，CC 仍暴露 21 个工具。工具 JSON 共 60,863 字符，Bash、Read、Edit、Write、NotebookEdit 之外的非核心工具占 87.4%，其中 Workflow 一项占 34.6%。此外还有 14 项 Skill 清单，其中 deep-research 的描述提到 web 搜索。自部署 44 条的首轮 prompt 为 18,646–19,488 token，按字符比例折算，非核心工具约 1.3 万 token（推断），在 32K 上下文里约占四成。复算的非核心工具调用：DeepSeek 0/776；Coder 40/932，分布在 13 条尝试中（TaskCreate 11、TaskUpdate 16、ReportFindings 11、Skill 1、TaskList 1）；Qwen3.6 17/652，分布在 5 条尝试中（stats 47 条口径：Coder 35 次、Qwen3.6 14 次）。Skill 被误调时会注入大段指令：verify 11,766 字符（Coder Conan/a2，多出 4 次调用和第二份总结），code-review 6,141 字符（Qwen3.6 Moto5134/a2），init 让 Qwen3.6 Conan/a1 被"写 CLAUDE.md"的指令带偏两轮。收到 Task 提醒后一轮内调用 Task* 的次数：DeepSeek 0/67、Coder 6/141、Qwen3.6 2/71。

**正式链位置**：**已核实（配置）**：正式启动脚本使用相同的禁用参数和同一个 CC 版本。**推断**：工具面相同，但正式链的请求体尚未抓取核对。

**最小复现**：真实 CC + 桩端点，查看首个请求中的 tools 与 system。

**候选选项（不作决定）**：① 维持现状；② 扩充禁用清单，只保留核心工具；③ 另外禁用 Skill。对照时一次只改这一个因素（§9.4）。这是训练条件，属于 **T0**，由用户决定。启动参数常量要有单一写入者，A 线脚本与探针 `--disallowed-tools` 共用这一个来源。

| 类别 | 指针 |
|---|---|
| 证据 | `GW/*/<id>/requests.jsonl` seq 1 的 `tools` 与 `messages[1]`；`AN/conan-io__conan-15422/qwen3-coder-30b-a3b-instruct/cell.md` L60；`AN/getmoto__moto-5134/qwen3.6-35b-a3b/cell.md` L20；`AN/conan-io__conan-15422/qwen3.6-35b-a3b/cell.md` L18 |
| 位置 | `rh2/experiments/p3_preflight/j4_full_step.sh:203`；`rh2/experiments/miles_gpu_spike/launch.sh:109` |

## 8. #9 CC auto-memory

**现象与证据**：67 条尝试的系统提示都有 "# Memory" 一节，并指定记忆目录为 `/home/agent/.claude/projects/-testbed/memory/`。复算发现 2 条写过记忆文件。Coder Dask8597/a2 把 `MEMORY.md` 和 `indexing-zero-d-dask-array-fix.md` 写进了 `/testbed`，两者随投影进入候选，占该候选 38.7% 的字节。Coder DVC6954/a1 写到了指定目录，没有进入候选。

**正式链位置（已核实，源码）**：`write_config` 和 `static_env` 都没有关闭 auto-memory；census 只排除 `.git/` 和 `.harness/`，所以写进 `/testbed` 的记忆文件会进入候选。

**最小复现**：真实 CC + 桩端点，查看 system 中是否有 "# Memory" 一节。

**候选修法与验收**：在 launcher 中设置 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`，或在 settings 中设置 `autoMemoryEnabled:false`（CCS 里有这两个键，2.1.205 需要核实）。验收：请求的 system 中不再有该节。不建议改 census：一是属于公共契约，二是记忆文件的文件名是任意的。这会改变策略看到的系统提示，按训练条件处理，属于 **T0**，建议与 #10 合成一个决策包。

| 类别 | 指针 |
|---|---|
| 证据 | `GW/coder/bp22-qwen3-coder-30b--dask-8597-a2/resp_19.sse`、`resp_20.sse`；`AN/dask__dask-8597/qwen3-coder-30b-a3b-instruct/cell.md` L9、L28 |
| 位置 | `SA/harness/claude_code.py:30–34, 44–55`；`rh2/src/repoharness2/contracts/baseline_manifest.py:98–110`；`CCS/memdir/paths.ts:21–55` |

## 9. #5 `<|im_end|>` 进入 content

**现象与证据（复算，44 条自部署）**：33 个没有工具调用的末轮中，32 个带字面量 `<|im_end|>`（Coder 13、Qwen3.6 19），另 1 个是悬空调用；其余 11 条撞回合上限，末轮是工具调用。非末轮出现 0 次，本探针没有发生回放。悬空调用占全部 1,563 轮的 1 轮：Coder Dask8597/a2 的末轮原始输出以 `<tool_call><|im_end|>` 结束，解析器把这段丢掉，按 `end_turn` 收尾，而 `ill_formed` 仍为 False。

**正式链位置**：**已核实（源码）**：capture wire 复用 vendored 代码的 `_sampling_params`（`skip_special_tokens=False`、`no_stop_trim=True`）和同一解码路径；`parse_model_output` 只做 `.strip()`，`ill_formed` 只在 JSON 解析失败时才置位。训练用的是采样 ID，所以末轮文本里的泄漏不改变训练 token。**推断**：如果 CC 在纯文本轮之后继续对话，重新渲染时会出现双重结束符。

**最小复现**：直接给 `parse_model_output` 喂上述两种原始文本即可（可以不加载 tokenizer）；已有留证见 `GW/*_adapter/*.turns.jsonl`。

**候选修法与验收**：当 finish 为 stop 且最后一个 token 是 EOS 时，只从可见文本中剥掉 EOS 字面量，采样 ID 不动；当原始输出含 `<tool_call>` 却没解析出调用时，把 `ill_formed` 置位。验收：两个单测通过，末轮 CC result 中不再有字面量，`output_ids` 逐位不变。**T1**。

| 类别 | 指针 |
|---|---|
| 位置 | `SA/adapters/common.py:346, 417–421`；`SA/parsing.py:50–55, 79–85`；`SA/adapters/anthropic.py:170–178`；`RS/capture_wire.py:1196` |
| 证据 | `GW/coder_adapter/bp22-qwen3-coder-30b--dask-8597-a2.turns.jsonl` turn 21；`AN/getmoto__moto-5134/qwen3-coder-30b-a3b-instruct/a1.md` L65 |

## 10. #7 CC 不回放 DeepSeek 的 thinking

**现象与证据（复算）**：DeepSeek 的 713 次响应全部带 thinking，但此后 690 次请求的历史里一块都没有；同一个 CC 对 Qwen3.6 adapter 的 thinking 则回放了 593/593 次（signature 为空串）。CC 能看到的差异有两处。① DeepSeek 在 `message_start.model` 中回的是 `deepseek-v4-pro`，而请求的模型名是 `slime-actor`；② DeepSeek 的 thinking 带 `signature_delta`，值为该消息的 UUID。adapter 则回 `slime-actor`，也不发 signature。代价（因果为推断）：重复推理占输出 token 的比例，Conan/a2 为 35%，Moto5134 a2–a4 为 57–63%，Moto5134/a1 为 76%。

**正式链位置（已核实，源码）**：adapter 的流式回显把模型名写死为 `slime-actor`，也不发 signature，所以正式链属于"会回放 thinking"的一侧。这个问题只影响 DeepSeek 对照组的可比性。

**A/B 方案**：在网关转发首个 chunk 时加一行改写，例如 `chunk = chunk.replace(b'"model":"deepseek-v4-pro"', b'"model":"slime-actor"', 1)`（用配置开关控制，并记录是否命中），也就是把 `message_start.message.model` 改回请求名；第二组去掉 `signature_delta`。每组各跑一道短题，只需 2–3 次请求，然后数 seq≥2 的请求历史里有多少个 thinking 块。改动的是 B 线探针文件，不涉及 T 级。

| 类别 | 指针 |
|---|---|
| 证据 | `GW/deepseek/bp22-deepseek-v4-pro-dask-8597-a1/resp_2.sse`；`AN/conan-io__conan-15422/deepseek-v4-pro/cell.md` L61、L80；`AN/dask__dask-8597/deepseek-v4-pro/cell.md` L10 |
| 位置 | `SA/adapters/anthropic.py:231, 242–244`；探针 `model_gateway.py:214–221` |

## 11. #11 薄入口与正式链的差异（外推边界）

| 维度 | 探针 | 正式链 | 不能直接外推的结论 |
|---|---|---|---|
| actor 环境 | `bash_env_v1` | `original`（见 #1） | 全部求解结果 |
| 预算 | 60 回合；网关上限 200 次请求；1800 s；上下文 131,072 | 25 次请求（第 26 次返回 403）；600 s；脚本默认上下文 32,768 | 67 条中 39 条超过 25 次请求，48 条 prompt 超过 32,768；46 条成功里只有 14 条同时落在这两条限制内。成功率与区分度都不能外推 |
| 端点 | 每个 attempt 各有一个 relay → 探针网关（留证、首字节前重试）→ adapter 或 DeepSeek | 每个 run 一个 relay → adapter + capture wire（认证、预算、poison） | 流中断与错误路径（见 #3） |
| 训练消费 | 虽用 fork=0 的 manager，但没有 capture / backfill / `turn_coverage` | 三者都有 | 分行数只有本文估算（见 #4） |
| census 冻结 | 在 replay 容器里，按 git diff 导出 | 在求解容器里做 post census（相对基线） | §7.5b 的导出污染；`.harness` 与记忆文件要按正式规则另行判断 |
| 其它 | DVC5839 的 actor 用派生镜像；DeepSeek 的 thinking 不回放 | 公开镜像；不涉及 | 该题的 actor 行为；对照组的推理成本 |

可以外推的部分：评分使用同一个 `SWEGradingManager`；CC 版本和启动参数相同；adapter 的解析与模板路径是同一份 vendored 代码。

## 总表：优先级 × 影响面 × 建议 owner

| 优先级 | 问题 | 影响面 | 建议 owner / 等级 |
|---|---|---|---|
| P0 | #1 解释器 | 所有正式 rollout | A 线启动块；B 线核对 `public_hints` 措辞 / T1 |
| P0 | #2 轨迹可读 | 所有正式 rollout | A 线启动块 / T1 |
| P1 | #3 截断当成功 | 频率低，但会静默写错 reward | A 线 adapter 块做故障注入；B 线补网关 / 若新增剔除规则则 T0 |
| P1 | #6 thinking 清空 | 带 thinking 的基座，22/22 条 | A 线 adapter 块；B 线落盘 token 数 / T0 |
| P1 | #4 参数改写 | 所有 solver，影响行数与成本 | A 线 adapter 块先实测 / 改匹配方式则 T0 |
| P1 | #8 计数与窗口 | 32K 上下文下的大多数轨迹 | A 线 adapter 块 / ≥T1 |
| P1（决策） | #10 工具面 | 训练条件，约占上下文四成（推断） | 用户决定，A、B 两线执行 / T0 |
| P2 | #9 auto-memory | 候选污染 1/67，外加提示开销 | 与 #10 合包 / T0 |
| P2 | #5 EOS 外显 | 仅末轮文本 | A 线 adapter 块 / T1 |
| P2 | #7 DeepSeek thinking | 仅 DeepSeek 对照组 | B 线 / 无 |
| 参考 | #11 差异 | 外推边界 | B 线维护 |

排序说明：与任务清单的原顺序相比，#6、#8 前移。前者影响 22/22 条 Qwen3.6 尝试的输入与分行；后者在正式链默认 32K 上下文下可能影响多数轨迹。#5 后移：它只出现在末轮文本，不改变训练 token。

## 本交接包没有做的事

- 没有改任何代码、配置或历史产物，没有提交；没有运行容器、CC、模型、tokenizer，也没有做故障注入。标"推断"的结论都还需要按上文的最小复现来证实。
- 复算只读取了本地回传的网关与 adapter 留证；分析脚本没有进仓库，方法见上文"计数口径"。没有逐条通读 67 条全文，除复算外依赖格子报告与单条报告。
- CCS 不是 2.1.205，只用来说明机制；凡涉及 CC 实际行为的结论，都要在真实 2.1.205 上核对。
- 没有替用户做任何 T0 决定，没有更新 `infra.md` 或 `env_data_eval.md`，也没有覆盖运行记录 §6 第 3 条（`max_new_tokens`）。
