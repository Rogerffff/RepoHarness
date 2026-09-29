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

## 12. A 线接收与排程建议（2026-09-23，Codex）

**建议：现在插入影响求解条件和失败归因的窄修复，不等第六组全部完成；也不把这 11 项全部修完设为恢复效率工作的前提。** 本节是排程与范围建议，未实施修复、未替用户决定新的训练条件。已读交接全文、运行记录 §9 的外推边界，并核对 materialize / driver / harness / adapter / capture / relay 的有关源码；本轮未复算 67 条，也未运行真实 CC 或故障注入。

| 顺序 | 工作 | 具体交付与边界 |
| --- | --- | --- |
| 先做启动修复 | #1 解释器、#2 日志可读 | 一份短 Brief 可拆两个可独立审查的提交。#1 同时修激活文件可读性和按 execution 的环境运输，不能通过进程全局变量串扰其它 attempt；用三个已留证环境核到真实 CC 子 shell 的解释器/导入。#2 让可信写端收集日志，不能只把目录移到 /tmp 或改成 root 只读而让 agent 的重定向失败；同时检查 done/launcher 控制文件的所有权与取消收尾，不扩成通用日志系统 |
| 同期先复现 | #3 流中断 | 经正式 adapter + relay + capture 测完整、RST、干净 EOF 缺结束事件、截断 FIN；核到 poison、装配、交付和 reward。不能因为薄探针有一条错误 0 分，就认定正式链同样漏入。已确证 infra 失败落实既有“无 reward”原则，不必重新批准这条原则；若需要新增不确定交付的接受/拒绝政策，再列具体取舍 |
| 同期准备一个短决策包 | #8 计数/上下文，#6 thinking 提醒，#9 auto-memory，#10 工具面 | 先核 CC 2.1.205 的真实请求、计数调用与可用设置。把服务窗口、CC 所认窗口、预留输出和压缩条件对齐；保留已批准的压缩方向，不用禁用压缩绕过问题。工具、memory、提醒的语义变化由用户决定，实施可以拆片。#8 返回真实计数与窗口取值/工具收窄是不同层面，不能捆成一个未经验证的配置开关 |
| 接入 adapter 小修，不抢首位 | #5 EOS 可见文本与畸形调用 | 用真实输出重放，分清末尾真实 EOS 与普通文本字面量；采样 IDs/logprob 保持不变。不能把所有出现工具标记文本的回答一律新增为丢组。若只是补解析事实可窄修，若改变准入须明确说明 |
| 先量，不改路线 | #4 参数改写造成分行 | 复用 I01 的 training_rows、input_tokens_total、动作覆盖事实，先用真实请求与对应生成记录回放；正式算力成本随 E5。当前 7.9/4.6 倍是表示估算，不是吞吐倍数，不据此自动重开 I01 C |
| 留 B 线 | #7 DeepSeek 回放、#11 探针/正式配置差异 | 前者影响对照组；后者是比较条件与外推范围。A 提供正式入口的配置事实，B 维护比较记录，不复制成 A 的生产修复任务 |

### 两个需要纠正的验收前提

- **#6 不等于旧动作再次从 loss 消失。** I01 B 保留先前采样动作并为不同上下文分行；这里应核实的是后续输入改变及重复前缀成本。修提醒时只要求该机制导致的非预期变化消除或解释清楚，不能要求所有相邻请求 token 前缀单调——已允许的压缩、子 agent 和分支本来就可能打断前缀。
- **25 请求、600 秒、32K 不能据此冻结为下一轮训练方案。** 交接列的是当前入口/旧脚本与本次探针的配置差异；正式八卡方案仍未确定。对齐配置事实是现在要做的事，最终数值另定。单卡求解和模拟端点也不能替代 GPU 训练/路由验收。

### 第六组怎么穿插

- E3/E3b 生产实现已通过 A 线复核；EP1 基准与性能文案修正可顺手收口，不需要回退代码。
- E1 的权限去重放在 #1/#2 明确启动职责之后，复用同一组环境验收；避免先优化随后又要改的启动流程。
- E2 批量 census、E4 历史释放的设计可继续；当前 `baseline_census.py`、`grading/manager.py` 有 B 线未提交改动，落地须顺序安排文件写入者，不能覆盖在制品。
- E5 清单现在即可补上正式求解条件、交付故障与真实分行成本；GPU 参数和实际收益仍等完整作业，不先按旧脚本冻结。

**下一步推荐给 A Claude 的范围：先交 #1/#2 的启动修复 Brief，同时给出 #3 的正式链最小复现方案；#6/#8/#9/#10 汇成短决策材料。** 不需要先写完全部新问题和剩余效率切片的大计划。B 的数据/评分行为裁决可继续；下一轮用于基座比较的求解，应显式固定并记录修正后的运行条件。

## 13. A 线接收：源码核对、修法取舍与实施顺序（2026-09-23，Claude A）

**状态：计划与建议，未实施；#1/#2 的短 Brief 按用户要求暂不写，先定顺序。** 本节在 §12 的排程之上给出 A 线自己的核对结果与顺序建议；与 §12 没有方向性分歧，有三处范围收窄 / 前提补充（§13.2）。

### 13.1 已按源码核对的事实（只列与修法直接相关的）

| 项 | 核对结果 | 对修法的含义 |
| --- | --- | --- |
| #1 | 两处缺口属实：`materialize.BASH_ENV_PATH="/root/.rh2_bash_env"`，而 rollout profile `hidden_paths=("/root",)` 且启动前探针要求 `HIDDEN_*` 为 DENIED；`HarnessLaunchSpec.env_injections` 只被记录，`ClaudeCodeDriver.run` → vendored `ClaudeCodeHarness.launch_and_wait` 的子进程环境只来自 `ANTHROPIC_*`、`static_env` 与进程级 `SLIME_AGENT_CC_EXTRA_ENVS` | `BASH_ENV` 的值对所有 execution 相同，走进程级变量在实践中不会串扰，但按 execution 运输仍是正确设计——字段已存在，只缺 driver 一段运输。容器 `--cap-drop ALL` 且未加 SETUID/SETGID：容器内 root **不能**切换成 agent 起进程，所以"root 提供只读文件、agent 以自己身份读"（`/rh2/<file>` 0644，目录 0755）是唯一机制；同一机制以后也承载依赖供应的 `/etc/pip.conf` |
| #2 | 属实：`run_agent` 在 `{workdir}/.harness` 建目录并 `chown agent`，launcher 以 agent 身份把 stream-json 重定向进去。rh2 源码没有读取该文件内容的消费者（只有排除区路径集合的 census 审计）；B 线探针的分析消费它 | 同上：root 不能包住 agent 进程，所以要么 **(a)** root 在工作区外预建 0733 目录 + 0622 文件（agent 能写不能读，不能列目录；`git status` 干净；census 政策与 `.harness/` 排除区都不动，无 T0），要么 **(b)** root 起 FIFO 读端（`docker exec -u root`，容器内 `setsid`）写入 root 专属文件、agent 只写 FIFO——多保住内容完整性，代价是多一个进程与读端死亡时 CC 写端 EPIPE 的收口。首选 (b)，Brief 里按实测成本定。`/tmp/.run.sh` / `.run.done` 是 agent 可写的控制文件：伪造只会缩短自己的运行、非零码由正式链拒绝，记为残余，同批顺手改成同样的 root 目录布局 |
| #3 | 正式 adapter 对 SGLang 是**非流式**（`call_sglang_generate` 拿到完整 turn 后才 `_respond` 写 SSE）；`record_turn`（= capture commit）在 flush 之后，客户端断连回 499 不记轮；relay 的 `pipe` 吞异常后正常 `close()`（对端只见 FIN） | 探针里"上游首字节后 RST"的形态在正式链不会同样发生；残余是 adapter 认为已 flush 之后、relay→CC 这一段失败：末轮（含 CC 未执行的 tool_use）已 commit，CC 若把残缺流当成功退出 0，该 execution 带评分 reward 进训练。复现矩阵应围绕这一段：relay pipe 异常、adapter 在 `_respond` 中途失败、CC 2.1.205 对 FIN / RST / 缺 `message_stop` 的反应。廉价加固（T1）：relay 任一侧出错时对另一侧 `abort()` 而不是优雅关闭。候选准入规则（若采用则 T0）："末轮含 tool_use、无后续请求、且终止不由预算 / 期限 / 停止解释 → 交付不完整，按 infra 无 reward" |
| #6 | 属实：`_fold_mid_list_system_into_user` 把中列 `system` 折成前一条 user 的 `<system-reminder>` 文本块，`_translate_messages` 再把 user 的 `tool_result` 块译成 `role:tool`、`text` 块译成独立 `role:user`；渲染只用 `apply_chat_template` 默认参数 | (a) 把提醒文本并入紧邻的 `role:tool` 消息内容，恢复 CC 自己的消息结构（提醒本来就是 tool_result 所在那条 user 消息的一部分），是最贴近事实的修法；(b) `preserve_thinking` 取决于训练基座的模板（Qwen3-30B-A3B 的模板同样丢弃历史轮 thinking），是训练条件；(c) 归 #10。三者都改变策略可见输入，T0 |
| #8 | 属实：`_count_tokens` 恒回 `{"input_tokens": 0}`；注释与观测不符 | 用已服务的 tokenizer 走现有 `_render_token_ids` 返回真实计数，改动很小；CC 认知的窗口（`CLAUDE_CODE_AUTO_COMPACT_WINDOW` 等）需在 2.1.205 核实，且与 I19 的压缩方向一起定 |
| #5 | 属实：`parse_model_output` 只 `.strip()`，`ill_formed` 只在工具参数 JSON 解析失败时置位；采样参数 `skip_special_tokens=False, no_stop_trim=True` | 剥离仅限"finish=stop 且末 token 为 EOS"的可见文本；原始输出含 `<tool_call>` 却未解析出调用时置 `ill_formed`。采样 ID / logprob 不动，T1 |
| vendored 约束 | `rh2/src/slime/VENDOR_README.md` 声明与 pin 逐字节相同、"任何修补必须在修补记录逐条登记" | #2/#3/#5/#6/#8 都落在 vendored 文件上。两种做法：登记修补，或在 `RS` 层包装（既有先例：capture_wire 已替换 `call_sglang_generate` 与 `record_turn`）。逐项在 Brief 里选，不在本节定 |
| 文件归属 | `envpack/materialize.py` 目前不在 B 线未提交改动清单里（B 在制品：`envpack/{bundles_v2,prepared_tasks,scoring,training_view,trusted_prep}.py`、`adapters/slime/{baseline_census,prepared_task_face,replay_grade}.py`、`grading/manager.py`） | #1 的 materialize 改动可由 A 写，开工前与 B 确认一句 |

### 13.2 与 §12 的三处范围收窄 / 前提补充

1. **#3 先收窄再复现**：如 13.1 所述，正式链的截断只能发生在 adapter 写完之后的 relay→CC 段。复现不必模拟 SGLang 中途 RST；四种流形态改由"桩 adapter 在 `_respond` 中途失败 / relay 对端异常"产生。同时把 relay 的 `abort()` 加固列为可立即做的 T1，不等准入规则。
2. **决策包与 #3 复现共用一套夹具，并行起步**：#6/#8/#9/#10 需要核 CC 2.1.205 的真实请求体（工具清单、`count_tokens` 调用点、memory 一节、`CLAUDE_CODE_AUTO_COMPACT_WINDOW` / `CLAUDE_CODE_DISABLE_AUTO_MEMORY` 是否生效），这些和 #3 一样只要"真实 CC + 桩端点 + 正式 relay/adapter"就能拿到。一次搭好，两件事都用。
3. **验证机器与 CC 二进制是前提**：#1/#2/#3 的验收都要真实 CC 2.1.205 在题目镜像里跑（三题：conan-15422、dvc-5839、moto-5134）。本地没有 CC tarball（`SLIME_AGENT_{NODE,CC,CC_PLATFORM}_TARBALL` 指向远端 `/root/tarballs` 或探针机 `/work/probe/cc`）；探针机（RTX PRO 6000）已于 2026-09-23 删除，证据已回传本地，盘上的 CC tarball / 模型 / 镜像不再可用。CC 2.1.205 的两个 npm 包（`@anthropic-ai/claude-code` 与 `@anthropic-ai/claude-code-linux-x64`）已核实仍可从 registry 取得，题目镜像可重新拉取、派生镜像可按仓库内 Dockerfile 重建，所以验证只需一台 x86_64 CPU 机（Docker，≥200 GB 盘）。

### 13.3 建议的实施顺序

| 序 | 工作 | 归属 / T 级 | 前提 | 交付与验收 |
| --- | --- | --- | --- | --- |
| 0（已完成） | E3 / E3b 生产实现通过复核；EP1 基准与文案已修 | A | — | 见 batch6 Brief §10 |
| 1 | **#1 + #2 启动修复**：一份短 Brief，两个可独立审查的提交 | A / T1（改 schema 则升级） | 13.2 第 3 条的机器 | 三题在 `original` 条件下 agent 环境事实与 `bash_env_v1` 一致、dev-check 通过、census 不变；agent 身份 `ls`/`cat` 轨迹文件失败、CC 输出完整回收；启动前探针新增"可读不可写"与"CC 同形 launcher 得到 testbed 解释器"两项 |
| 1′（并行） | **#3 正式链复现** + relay `abort()` 加固 | A / 加固 T1；准入规则若采用 T0 | 同上 | 四种流形态的事实表：CC 退出码与 `result`、adapter 是否 commit、是否 poison、是否装配、是否成 0 分样本；据此再提准入取舍 |
| 1″（并行） | **短决策包**：#6 提醒位置、#8 计数与窗口、#9 auto-memory、#10 工具面 | A 起草，B 补探针事实，用户决定 / T0 | 同一套夹具 | 每项给"现状事实 → 选项 → 对策略可见输入的影响 → 验收"，不捆成一个开关；#8 的真实计数可先做（T1），窗口取值与 I19 一起定 |
| 2 | **E1 权限初始化去重**（含 E1+ 的目标机测量）；**E5 清单补项**：正式求解条件（解释器、日志、工具面、窗口）、交付故障（#3）、真实分行成本（#4 用 I01 `turn_coverage` 在真实 CC 流量上实测） | A | #1/#2 定下启动职责后 | 复用第 1 步的环境验收；E5 只补 producer 不建平台 |
| 3 | 按决策实施 #6/#8/#9/#10 的已批部分；**#5** EOS / `ill_formed` 小修并入同一 adapter 块 | A / 各按决定 | 第 1″ 步的用户决定 | 用真实输出重放；采样 ID / logprob 逐位不变 |
| 4 | **E2 批量 census、E4 完成历史释放**（含 CR1 诊断余项）；**依赖供应短设计**（用户把选择一确认为决定后） | A，与 B 的在制品按文件排序 | B 的 `baseline_census.py` / `manager.py` 改动先落地或明确顺序 | 等价输出 + 窄回归；网络 Brief 单列 |
| B 线 | #7 DeepSeek 回放 A/B、#11 差异维护、`public_hints` 措辞、下一轮基座比较的运行条件固定与记录 | B | — | — |

**为什么这样排**：第 1 步是所有正式 rollout 的求解条件，不修则后面的任何基座结果都不能外推；1′/1″ 与它共用夹具与机器，并行不增加等待；E1 放在启动职责定下之后，避免先优化再改；E2/E4 与 B 的文件相交，等在制品落地。第六组四项决定不重开，八卡方案与训练条件数值仍待定。

### 13.4 需要用户现在定的事

1. 13.2 第 3 条：租一台 x86_64 CPU 机（建议 host 79466 的高内存实例；探针机已删除，不存在恢复选项）。
2. 是否同意把 #3 的复现范围按 13.1 收窄到"adapter 写完之后的 relay→CC 段"，以及 relay `abort()` 加固作为 T1 先做。
3. 决策包的形式：一份文档四项分列（我的建议），还是拆成两份（#6/#8 输入相关，#9/#10 工具面相关）。

## 14. §13 的开工复核（2026-09-23，Codex）

**结论：同意实施顺序；下面的工程修订应并入短 Brief 后执行。无需为文档形式、故障矩阵的技术划分再增加用户决策。** 机器租赁与费用仍由用户确认；#6/#8 窗口/#9/#10 的训练条件仍按原安排单独决定。未实施生产修复。

### 14.1 #1/#2 的方案空间与权限需要修正

- **无 SETUID 不是“只剩只读文件/FIFO”的依据。** 它限制容器内进程自行切换 UID；宿主仍能以 `docker exec -u agent` 启动进程并收集输出。现有 `DockerSandbox.exec` 已这样选用户，`_run` 已用宿主 PIPE 接 stdout/stderr；[Docker 官方接口](https://docs.docker.com/reference/cli/docker/container/exec/)同样提供 `--user`。只读激活文件与按 execution 传环境合理，但 FIFO 与宿主收集应按长输出、取消、清理的实际复杂度选择，不能凭能力集合排除后者，也不需要为此给容器增加 SETUID。
- **不采用 §13 的 0733 目录布局。** 0733 给 agent 写目录和搜索已知名称的权限，不能防删除/替换；0622 文件可写也意味着可覆盖、截断。当前 `exec_and_wait` 还会先以 agent 执行 `rm -f out_file done_file`，再重定向创建：直接套这个布局会把 root 预建文件删掉，再建成 agent 文件。Brief 分别明确不可替换的父目录、日志写端、只读 launcher 和退出码的可信来源；不能把它们统一套同一组权限。
- **FIFO 不自动保证输出完整或可信。** root 只写的最终日志可以避免已收集内容被直接改写，但可写 FIFO 仍允许同 UID 注入内容。若选 FIFO，交代读端就绪、EOF、EPIPE、取消和清理；当前 `execution_scope` 只终止 agent UID，不会顺带终止新 root 读端。`done` 可伪造为 0 会遮蔽非零退出，不能只用“非零被拒绝”证明安全。不要为实现日志不可读引入更大的无人管理生命周期。
- **接上已登记的 R2E 边界。** [R2E 计划 §11.5](r2e_grading_wiring_20260920.md#115-与基座探针-a-线修复的接缝2026-09-23codex)已说明通用环境通道必须容纳 `.venv`，不能把 conda `testbed` 激活成功当作所有来源的条件；有副作用的 Python/import 检查不要前移到首次 census 之前。#1 首片可先修 SWE-Gym，但接口不能把另一来源堵死。

### 14.2 #3 同意收窄到正式传输链，不同意只测 commit 之后或预先认定 abort 已修好

正式 SGLang 上游是完整 JSON 应答，不必复制 DeepSeek 上游 SSE 的所有形态；**保留 adapter SSE 写出中途失败（未 commit）和服务端已 commit、下游未完整接收两个边界**。完整流正控、缺 `message_stop` 的干净 EOF、异常断连分别核对。`_render_stream` 当前写事件后直接返回，没有显式 `write_eof()`，随后的 `record_turn/commit` 不能证明 CC 已完整消费。

`transport.abort()` 可以作为 **T1 候选异常收尾修法**，按“先复现→窄改→同一反例和正控复验”完成一片；不应作为无需验证的先行加固。它只保证立即关闭并丢弃缓冲，不保证 TCP RST 或 CC 非零退出（[asyncio 官方契约](https://docs.python.org/3/library/asyncio-protocol.html#asyncio.WriteTransport.abort)）。主审独立运行的[本机 TCP 探针](tmp/relay_abort_semantics_20260923.py)与[结果](tmp/relay_abort_semantics_20260923.json)：已写出的缺结束事件片段后执行 abort，3/3 仍为普通 EOF；显式 RST 正控才抛 ConnectionResetError。此结果不替代 Linux / CC 验收，也不推荐把 SO_LINGER 正控直接变成生产修法。

正常 EOF 不会进入 relay 的异常分支。复现必须区分 TCP 结束、HTTP 完结与 SSE 结束事件；不要把正常结束一律升级为异常，也不要只看工具调用状态就推断交付结果。**§13 的“末轮 tool_use＋无后续请求”暂时只作诊断线索，不随 relay 修补加入 infra/丢组判据**：它没有证明传输失败，纯文本截断也可能漏掉。确证基础设施失败按既定无 reward 原则处理即可；新的不确定交付处置另给证据与取舍。

### 14.3 其余安排与三项确认的处理

- **#8 返回真实计数可先作为窄修做**，与窗口数值分开：复用生产翻译/模板/实际 tokenizer（包含 system/tools 与提醒处理），不是把 Anthropic 原始 messages 直接交给只接受模板消息的 helper；计数不创建生成轮、不消耗模型请求预算。由真实 CC 核实大文件 Read 的行为，最终窗口、压缩条件仍单列决定。
- **vendored 按具体 diff 选择。** 登记必要窄修补或适配层扩展均可，不为保持零改动复制大段实现或叠加不必要 monkeypatch。#3 的 relay 本身在 RH2 `sandbox_profile.py`，并非每一项都必然修改 vendored 文件。
- **机器采用 CPU 验证方向。** §13.2 最新文字记载旧探针机已删除，与消息摘要和旧 infra 条目的“恢复探针机”不一致；按可重建的 x86_64 CPU Docker 环境准备，不保留这个失效选项。本轮未向服务商核实机器状态、价格或租赁。Claude 给出实际 CPU 候选、存储与费用后用户决定；Brief、普通单测、tokenizer 回放与 TCP 复现可以先做，不以租机作为所有工作的前置。
- **一份文档、四项分列即可。** 这是组织方式，无需用户另选两份或一份；共享 CC/relay 启动夹具，断言和参数仍按问题分别独立，不做通用故障平台。
- **E3 的 EP1 可收口。** 已核脚本与 §10：计时/内存分开、编号范围修正、心跳先结算、旧因果推论撤回且正确归属主审数字；本轮对两种测量模式各做小规模冒烟，没有重复大基准。E1/E5 与 E2/E4 的原顺序保持。

依 §10.4 用两路限定只读检查权限/传输边界，主审独立核源码与 TCP 反例。未运行真实 CC、Docker、GPU、远端或付费作业；只增补本节、探针与账本。以上不是新增 T0，也不要求再走一轮“同意文档形式”的批准。

### 13.5 处置（2026-09-23，Claude A）

§14 的修订全部并入 [#1/#2 短 Brief](base_probe_chain_fixes_20260923/brief_startup_1_2_20260923.md)（#2 选宿主收集，理由在 Brief §2.2）。§13.4 三项：机器已由用户提供并完成 go/no-go；#3 按 §14.2 的两个边界复现；决策包一份四项分列。#1 基线已在验证机上复现（Brief §0）。
