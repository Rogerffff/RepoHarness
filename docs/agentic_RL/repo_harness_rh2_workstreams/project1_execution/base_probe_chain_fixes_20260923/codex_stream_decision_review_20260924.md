# #3 事实表与 #6/#8/#9/#10 决策包复核

> 最新状态（2026-09-24）：`716c94d5` 的 **CI1/CI2 针对性复核通过，见 §10**；决策包 §8 的四片在本机与已记录的协议验收范围内收口，无剩余阻塞项或新增用户决策。真实模型效果、GPU 集成和正式窗口数值仍按既定作业方案处理。§1–§9 保留各轮审查时结论；用户已批准的实施反馈见 §8，权威决定记录在[决策包](decision_package_6_8_9_10_20260924.md) §8。

2026-09-24，Codex（A 线分叉）。审查 `88b10599`、`6b023ebe`，同时针对性复验上一片的 `a07812e5`（F1/F2）。本轮只补审查工件和记录，没有改生产代码、测试、fork 或用户决定，没有提交、push 或发送跨任务消息。

**结论：#1/#2 的 F1/F2 修复通过；#3 的事实表须修正，但目前不据此要求正式链新增准入规则；#9/#10 可以进入用户决策，#6 的默认方案和 #8 的验收条件需先收窄。** 以下是审查意见，不代替用户批准训练条件。

## 1. 结果与排程

| 项 | 裁定 | 下一步 |
| --- | --- | --- |
| #1/#2，F1/F2 | 通过，无剩余阻塞项 | 启动与宿主收集这一片收口 |
| #3 | 原九案的数据可复用；“任何 message_delta 前截断都退出 1”“B 旧案可能只是 launcher 记错”不成立 | 补上本报告三案及边界；B 网关不得把残缺 SSE 包装为正常 HTTP 完成。正式纯 TCP relay 暂不增加规则 |
| #6 | 清空机制及回放收益成立；不推荐默认 a2 合并全部 user 文本 | 默认建议改为 a，只合并约定的提醒；普通用户指令、摘要指令、Skill 正文保留角色。先定 #10，再看残余 |
| #8 | 真实计数可先做；400 能进入被动压缩分支成立，实际超限恢复尚未验证 | 实施覆盖正式 capture 接线；增加同一真实长度上限下的普通请求、摘要请求验收。窗口数值留具体作业配置 |
| #9 | 开关效果核对成立 | 建议关闭 auto-memory；是否采纳由用户决定 |
| #10 | 五工具配置确实缩小请求并移除 Skill 清单 | 建议作为首版 SWE 的受控工具配置；不是“完整 CC 能力无损”，成绩影响未知，交用户决定 |

## 2. R1：#3 的完整性分界被过度概括，B 旧案不是单凭退出标记推断的（P2，证据与结论）

### 2.1 旧证据与作者夹具遗漏了什么

B 线 `iterative__dvc-6954/deepseek-v4-pro/a1` 的 `attempt.json` 确实记退出 0；更关键的是其 `trajectory.jsonl` 最后一条真实 CC `result` 自身就是 `subtype=success, is_error=false, stop_reason=tool_use`。不能仅用旧 `/tmp/.run.done` 可写来否定它。

对应 `gateway/deepseek/bp22-deepseek-v4-pro-dvc-6954-a1/resp_11.sse` 的结构是：先完整结束一个空 thinking/signature 块，再开始 index=1 的 Read 工具块，随后中断。作者 S5 只测了第一个工具块尚未完整时中断；二者不是同一内容结构。

主审没有伪造 DeepSeek 的 reasoning parser，而是在原夹具第二轮真实工具文本前加入一段普通文本，让既有解析器与 `_build_reply_parts` 自己产生 **text + tool_use**。生产 `anthropic.py:157–166` 支持这种响应。只包装作者实验脚本，不改生产实现。实测仍用真实 CC 2.1.205、真实镜像、正式 driver、relay、adapter、capture 和编排。

### 2.2 主审补测三案

| 场景 | 第二轮收到什么 | CC 退出码 / is_error | 第二轮工具执行 | 评分调用 | 交付 |
| --- | --- | --- | --- | --- | --- |
| 完整流正控 | 完整 text + 完整 tool_use | 0 / false | 是 | 1 | 正常，4 个 capture，合成 loss mask 合计 24 |
| S5，多块 SSE 中断、HTTP 正常结束 | text 完整；只收到下一 tool_use 的开始；故障器转发终止 chunk | **0 / false**，stop_reason=tool_use | **否** | **1** | **completed / present_complete，remove_sample=false；2 个 capture，合成 loss mask 合计 12** |
| S3，同一切点直接 FIN | text 完整；下一工具块开始后断流，无终止 chunk | **1 / true** | 否 | **0** | **nonzero_harness_exit_in_formal_chain，remove_sample=true** |

工件：[汇总及源码同一性](review_stream_decisions_20260924/main_stream_summary.json)、[复现包装脚本](review_stream_decisions_20260924/probe_s3_completed_block.py)。原始运行目录为 `runs/codex_stream_decisions_review_20260924/{control,cut,cut_fin}/`，含 `facts.json`、宿主 CC 日志及运行日志。七个关键源码/夹具文件的远端与本地摘要相同。三次运行各自标签下容器、网络均为零残留；结束后远端 `docker ps -a` 为空。

**这不是实测 SWE 得分为 1，更不是已经执行了一步错误梯度。** 评分仍是作者的罐头 `GradingSubmitStub`，tokenizer/引擎仍为替身，mask 数量只是捕获与交付路径证据。问题是未完整交付的生成轮在该 S5 条件下没有被评分前检查识别。

### 2.3 生产可达性与处置边界

- **B 探针网关：production_observed。** 原始真实 CC 日志已有多块残缺后成功结束；其上游 EOF 后调用 `write_eof()` 的机制能制造正常 HTTP 收尾。应由 B 在网关传输边界修复并复验，修复前不要把这种结束当作正常求解结果。
- **当前正式纯 TCP relay：没有复现同一放行。** 主审 S3 裸 FIN 正确拒绝；relay 只转发字节，不会自行产生 HTTP 终止 chunk。S5 在正式编排中是故障器主动加工响应的实验条件，不能升格为已证明的正式主链自然故障。若未来加入会“正常收尾残缺上游”的 HTTP 网关，则该风险为 `conditional_future`，启用前必须验证。
- 因此保留“**当前不改正式 relay、不新加准入规则**”这一窄处置是合理的。应撤回的是“现有非零退出检查保证了所有未交付工具轮都不训练”的承诺，以及对 B 旧案的错误归因。
- S1/S3 原表只证明当前 relay 把上游 RST/FIN 都变成 CC 看到的 FIN；没有测“对 CC 直接施加 RST”或改后 `abort()`。应写“当前未发现需要这项改动的证据”，不能写“已实验证明 abort 无效”。

真实静止屏障 `quiescence_barrier.py:103–150` 只检查会话排空、agent 进程归零和工作区稳定，不核对 SSE。它不会专门识别上述 S5；但本轮没有实测真实屏障放行，不能省略替身边界。

**最小后续与停止条件：** B 修复有明确证据的错误 HTTP 收尾，使用多块完整流与多块中断各作反控；A 修正文档即可继续后续切片。若以后需要正式侧处理确定的传输故障，优先复用已有 poison/取消/drain 收口。不要据此直接添加“末轮 tool_use 无后续请求即拒绝”或“缺 message_stop 即拒绝”；后者会否定作者已验证的 S2/S4 良性形态。新样本拒绝规则才需要另行 T0。

### 2.4 同步改正夹具描述

`stream3_formal_chain.py:635` 还注入了测试 `_Barrier()`；不是标题所说的“只有引擎和 tokenizer 是替身”。registry 未接真实 model-call proxy，未覆盖异步权重发布。评分替身原文已在正文披露，应与静止屏障一并放进夹具说明。

`collect()` 从不存在的 `audit.launch_spec` 取 session id，九份事实中该值为空，根本没有采到 `poisoned` 字段；而且事后读取还可能发生在 session release 之后。不能以这些产物声称“所有场景 poison 均未触发”。当前结果足以判断上述交付行为，不必为修正文案新增常开观测。

## 3. R2：#6 的 a2 会改写真实压缩指令，不能只称为提醒归一化（P2，待实施设计）

主审独立重跑候选 `smoosh_into_last_tool_result` 与真实 Qwen3.6 模板，输入是作者 #8 的真实 CC 压缩请求 `dp_c8_reactive/stub/requests/messages_003.json`。它的末条 user 消息含一个 `tool_result`，之后是 **6,361 字符的摘要指令**，开头为 `CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.`。

| 方案 | 摘要指令归属 | 模板位置 |
| --- | --- | --- |
| 现状 / a（只合并 system-reminder） | 独立 user 指令 | 位于工具输出之外，last_query_index=6 |
| a2（合并全部 user 文本块） | **tool 内容** | 全文移入 `<tool_response>`，last_query_index=3 |

文字没有丢，但角色和模板处理改变了；这是实际已有请求，不是想象的将来形态。尚未跑模型，不能说一定压缩失败。它足以说明默认 a2 的影响面比决策包列出的“大约少 4 token、保留 thinking”更大。

**推荐：** #10 确定后，若需要处理剩余提醒，先采用 a 的窄范围；普通用户指令与摘要指令保持原角色，Skill 正文也不为减少分行而自动当工具结果。若选核心五工具，历史样本的 Task/Skill 来源大多已不在工具面中，不能再用那两次 Skill 残余作为扩大到全部文本的理由。`preserve_thinking=True` 可保留为基座模板支持时的选项，不要求先做专门对比实验。

**验收修订：** 用同一批已记录请求验证目标提醒不再清空历史 thinking、真实摘要指令仍位于工具结果之外；训练行完整归属保持。只看 prompt 长度不下降不够，作者自己的 74 次清空中有 42 次被新增工具输出掩盖。固定脚本回放可比较分行；新模型自由生成的整段运行不能要求与历史回放分行数相等。

证据：[独立探针](review_stream_decisions_20260924/falsifier_p6_scope_probe.py)、[结果](review_stream_decisions_20260924/falsifier_p6_scope_probe.json)、[主审重跑](review_stream_decisions_20260924/main_rerun_p6_scope.json)，两次结果完全一致。

另外两处口径应改，不影响机制判断：

- 617 轮/595 相邻对、74 次清空、各方案训练行和输入量均核对一致；但生成 token 是把旧 `raw_output` 重新 tokenize，原采样 token id 未落盘，且 `max_sample_tokens=0`。应称“本回放没有丢失所提供的动作 token”，不能单靠它证明所有真实训练阶段零掉落。没有发现新的动作丢失证据。
- `84=74+5+5` 的总数正确，中间五次不是“清空与改参同轮”，而发生在清空后的下一次请求、没有新的提醒插入。详见探针 `fork_attribution`；修正文案即可。

## 4. R3：#8 目前证明的是进入压缩分支，不是真实超限后可恢复（P2，实施验收）

作者 `stub_p8910.py:147–169` 对普通第三次请求按剧本回一次 400，但对任何识别为压缩的请求都直接返回摘要，没有用同一上下文限制判断长度。

主审按生产同一翻译/模板重新计算实际请求：

| tokenizer | 被桩拒绝的请求 | 接着发来的摘要请求 | 桩声称的限制 |
| --- | ---: | ---: | ---: |
| 作者 Qwen3-30B-A3B 代理 | 18,272 | 19,529 | 32,768，错误文本写 40,000 |
| 已固定版本的 Qwen3.6-35B-A3B | 18,460 | 19,772 | 同上 |

两条实际都没到 32K。这里证明 **CC 认得该 400，愿意进入被动压缩并重发**，不能证明真正满窗时摘要能被同一引擎接受。本案摘要甚至更长。也不能反向概括“所有摘要一定更长”：该真实请求先移除了最后一对工具调用/结果，再附摘要指令，普通请求 6 条 messages、摘要请求 4 条；决策包“完整历史再加提示”的说法也需修正。

**实现接线必须写清：** 正式 `install_capture_wire` 在 `capture_wire.py:1471` 替换了 `slime_common.call_sglang_generate`。实际溢出分支位于 RH2 的 `capture_wire.py:1237–1248`。只改 vendored `common.py` 无效。主审用已安装的真实包装函数，以 33 token / 32 上限复现了当前空 `length` 返回。

**推荐的实施验收：**

1. #8(i) 真实计数沿已批 T1 先做，复用当前服务的 tokenizer、消息处理和模板；不建生成轮、不消耗请求预算、不产生 capture。
2. 普通请求与压缩请求受**同一个真实 token 长度上限**约束；用真实 CC + 正式 adapter/capture 接线跨过一次真正的限制，核对压缩后继续或明确有界失败，不能给摘要专设无限制桩分支。引擎生成内容仍可替身，这一步不需要 GPU。
3. 普通过长请求没有伪造采样或遗留 pending；真正生成的摘要只捕获一次，并遵守已有模型请求预算。不要暗中把压缩请求免计，也不要因改异常返回而意外 poison 整个正常恢复会话。
4. 窗口、输出预留和 Read 上限一起计算余量，并观察一次大工具输出后的摘要长度；“固定前缀低于阈值一半”没有已有决定或数学保证，改为报告实际余量，不新增固定比例闸门。

32K、4096、8000 都是示例，当前不用冻结成训练参数。I19 已批准恢复压缩，不需要再等 I19 决策；这里是下一份作业配置和实现验收的问题。#8(ii)/(iv) 的输入限制方向仍交用户决定，400 是该方案下的协议修复，不承诺一切超限都可恢复。

证据：[主审探针](review_stream_decisions_20260924/probe_decision_inputs.py)、[结果](review_stream_decisions_20260924/decision_input_results.json)。

## 5. #9/#10 可交用户决定，另改两处非阻塞措辞

主审回读原始请求并用两套真实 tokenizer 重算，#9 去除 Memory 节、#10 真正从 tools 移除非核心工具及 Skill 清单均成立。Qwen3.6 的首请求为 **18,358 → 3,795 token**；作者 Qwen3 代理数字 **18,190 → 3,636** 也一致。收益是当前同一请求的静态长度差，不是求解成功率或训练吞吐的保证。

- **#9 推荐关闭。** 对相互独立、容器不共享记忆的 SWE episode，没有必要默认鼓励维护跨会话记忆。验收是 Memory system 节、对应 init 字段和自动创建目录消失。模型仍可能自行写笔记或记忆样式文件；这不是开关失效，不应新增文件名拒绝规则，也不应要求“候选永远不含记忆文件”才验收。
- **#10 推荐核心五工具作为首版配置。** 它去掉了 Task/Skill/工作流等真实能力，是有意限定求解工具面，不能称功能无损。Bash 仍可执行命令，但不能因此推定所有被删能力等价替代。Grep/Glob 在作者现状里本来就没有；这次不把新增工具混入范围。后续真实基座诊断观察工具需求与成绩即可，不先扩成长期工具平台。

## 6. #1/#2 F1/F2 复验通过

本机运行 `test_startup_fix_1_activation.py`、`test_startup_fix_2_host_collected.py`、`test_startup_fix_2_engine_exec_docker.py`：**76 passed**，含 8 个真实 Docker 用例。主审原独立探针原样重跑：

- F1：真实评测 slot、prompt 100/101、physical attempt 与训练 retry 的文件隔离均正确；前一份日志不再被后一份覆盖。
- F2：短帧头、短 payload、无终止 chunk、非法 chunk 均标 partial；可信退出码保持 0；完整 raw/chunked 正控仍完整。

新结果：[F1](review_stream_decisions_20260924/f1_after_fix.json)、[F2](review_stream_decisions_20260924/f2_after_fix.json)。不再为此重复大规模 daemon 对抗实验。

## 7. 本轮范围、成本与停止条件

- 按审查标准 §10.4，沿用一对限定角色：Production Tracer 核真实调用链和原始 B 证据；Falsifier 核反例可达性、替身边界和更小处置。主审独立核源码、重跑关键 CPU 探针，并在用户已有 CPU 机跑上述三次真实 CC（无模型 API、无 GPU）。不是用多数意见代替证据。
- 相关测试 76 passed；独立 CPU 探针通过；探针按 `rh2/pyproject.toml` 的 ruff 检查通过；三个所审提交 `git show --check` 通过。没有重跑全库、双 lane、216 题或真实基座模型。
- 远端只使用本次具名资源，未调整 daemon、停机或销毁机器；机器继续运行。历史证据没有回写，B 在制品没有改动。
- 本轮审查停止于：#1/#2 收口；#3 补三案、纠正原表结论与 B 归因后即可继续，不扩大交付状态机；#6/#8 以本报告修订选项/验收，再由用户决定训练条件。#9/#10 不需要等全链实验才能讨论。工具/记忆/窗口/提醒仍分别记录决定，避免把四项包装成一次不可拆分的批准。

## 8. 给 Claude 的实施反馈（用户已批准，2026-09-24）

用户已经逐项了解问题、推荐和代价，并同意四项推荐决定。请以[决策包 §8](decision_package_6_8_9_10_20260924.md)为当前实施依据，不再按原 §5 的 a2 建议开工，也无需重复询问四项方向是否获准。

**已批准内容：**

1. **#10：首版 SWE 选五工具。** 采用 `--tools Bash,Read,Edit,Write,NotebookEdit`，正式启动与 B 线探针使用一致的配置来源；实际请求的工具集合及 Skill 清单变化作为验收事实。这是首版能力范围选择，后续可按基座表现调整。
2. **#9：关闭 auto-memory。** 启动时设置 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`。核对相关 system 节、init 字段和自动目录行为；不把“模型永远不写任何笔记文件”设为验收条件，不增加文件拒绝规则。
3. **#8：上下文管理与服务容量对齐。** 落实真实计数、提前压缩的容量/输出预留配置、真正溢出时明确的 400，以及随窗口调整的 Read 上限。具体窗口、输出预留、Read 数值留作业配置；可以用明确标记的测试参数验证机制，不把示例值固化为正式首训决定。
4. **#6：采用 a，仅处理约定提醒。** 普通 user 文本、真实摘要指令和 Skill 正文保留角色；不采用 a2，不同时启用方案 b。先落实工具集合，再验证剩余提醒；I01 的分行路线保持。

**请把三处审查修订落实到 Brief 和验收：**

- #6 复用本报告真实摘要请求反例：目标提醒不再意外清空历史 thinking，摘要指令仍在工具输出之外。长度不下降不是充分判据，也不要求新模型自由生成的分行数等于旧回放。
- #8 普通请求与摘要请求执行同一个真实 token 上限，走正式 adapter/capture 接线；不得对摘要使用无条件放行的桩。正确覆盖 RH2 `capture_wire` 的溢出分支，核对超限返回没有伪造采样或遗留 pending，正常恢复没有被误 poison。真正生成的摘要只捕获一次并消耗既有模型请求预算；count_tokens 不建轮、不消耗预算。容量不足时不能承诺一定恢复，需如实验证现有失败收口。这里不新增“固定前缀小于阈值一半”的闸门。
- #3 修正文档事实边界：多块残缺 SSE 被正常结束 HTTP 时确实可能成功退出；同切点裸 FIN 已被正式链正确拒绝。A 暂不改 relay 或增加准入；B 修复探针网关错误收尾，交接按已有分工办理，不在 A 切片中混改 B 在制品。

**建议执行顺序：** #10 → #9 → #8(i) 真实计数 → #8 的窗口/溢出/Read 接线 → #6(a)。顺序是实施建议，方向已批准；每片给出实际改动和对应证据。#6 改预处理后，#8 的计数/生成应继续使用同一套消息与模板处理。无需把专门 GPU 对比实验作为这些窄修的前置，真实基座行为和成绩随后在诊断中评估。

**收口与报告：** #1/#2 的 F1/F2 已通过，不重开这一片。更新短 Brief 与被修正的调查措辞，按既有流程推进已批准范围，实施后交 Codex 聚焦复核。明确报告测试参数、正式默认值是否变化、模型可见输入的变化与尚未实测的效果；没有新增用户决策时不要再次以“待四项确认”停工。

本节仅写入仓库供用户转交，未发送外部消息，未改生产代码、运行作业或提交/push。

## 9. `145cb5fd` 实施复核（2026-09-24，Codex）

**结论：四项实现的核心方向和行为认可，未发现 P0/P1。保留 CI1、CI2 两项 P2 收尾，再标为全部验收完成；不需要用户重新决定四项方向，也不要求重做 GPU 或大规模 CC 实验。** 本节是代码实施复核；§1–§7 的历史意见不再直接作为当前缺陷清单。

### 9.1 已核实通过的部分

| 项 | 本轮裁定及证据 |
| --- | --- |
| #10 / #9 | 正式 `launch_claude_code` 确实拼入五工具白名单，`claude_code_launch_env` 默认关闭 auto-memory；原有 extra args/env 覆盖优先级保留。作者 `cond1_normal` 原始请求的五工具、无 Skill 清单、无 Memory 节与实现一致。没有把模型自行写笔记设成拒绝条件 |
| #8(i) | count 与生成都使用当前生产子类的预处理、翻译和 tokenizer；安装在 app 构造前完成。主审独立重跑真实 Qwen3.6 tokenizer 探针：真实提醒请求计数 **28,767**、真实摘要请求 **19,772**，分别与生成渲染相同；计数调用不增加请求预算或 capture |
| #8(iii) | 溢出检查确在 RH2 capture wire 的引擎调用和 pending/draft 建立前；普通请求、摘要请求没有不同的绕限分支。独立 HTTP 探针使两条真实请求均返回 JSON 400：共 accepted=2、capture=0、pending=0、draft=0，无 poison；这是已接纳生成请求的既有预算口径 |
| #8(ii) / 压缩运输 | 上下文窗口与本次 session 的输出预算确实进入 CC 环境，同一窗口也进入 adapter session。回读作者 `s3r_C2`：52,927 token 的普通请求真超 32,768 后返回 400，29,347 token 的摘要在同一限制内生成，5 个接纳请求对应 4 个 capture、摘要一次；`s3r_C3` 覆盖主动压缩。此前“桩只按次数回 400、摘要无限放行”的验收缺口已修正 |
| #6(a) | 只移动最后一个 tool_result 后连续的约定提醒；遇普通文本即停止，摘要和 Skill 正文保留角色。独立真实摘要反例仍为 `role:user`，预处理幂等；没有启用 a2 或 preserve_thinking。训练分行规则没有在本片改动 |

主审独立重跑结果与子审结果逐字节相同：[探针](review_conditions_impl_20260924/falsifier_adapter_paths.py)、[主审结果](review_conditions_impl_20260924/main_adapter_paths.json)。它是本地真实 tokenizer / 生产 HTTP 路由检查，没有运行真实模型或 CC。

### 9.2 CI1：Read 上限字段缺正式作业来源（P2，配置接线）

**生产可达性：`production_reachable`。** 调用链为 `BringupService._async_start_body → SlimeBindingConfig → _generate_attempt → cc_context_env → claude_code_launch_env`。当前 `bringup.py:1482–1518` 的唯一生产构造点只传了 `max_context_len`，没有读取或传入新字段 `cc_file_read_max_output_tokens`；因此该字段一直为 `None`。`generate.py:2961–2963` 下游运输正确，但收不到这个专用配置值。单测与真机夹具直接构造 `SlimeBindingConfig(..., cc_file_read_max_output_tokens=8000)`，绕过了缺口。

主审执行真实构造表达式及实际环境合并函数，测试窗口 32,768 / 输出 4,096：默认只注入三个窗口变量，不含 Read 上限。**既有 `SLIME_AGENT_CC_EXTRA_ENVS` 可以把 `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS=8000` 送入正式 CC 环境，已用同一探针正控确认。** 所以这不是“Read 上限完全不能配置”，也没有证据说明本片已污染训练。准确问题是：Brief 所写的新字段运输没有正式来源，直接照实验配置无法配置正式作业，默认仍由 CC 使用 25,000。

**最小处理：** 优先复用已有配置能力，不新增配置框架。Claude 可以明确将现有 extra env 作为正式作业入口，统一 Brief/运行配置说明和测试；也可以补一处显式读取映射到该字段。不要同时声称两套互不连接的入口都是唯一来源。保持未配置时的原默认，不把 8000 固化，也不加任意窗口比例闸门。

**验收：** 从最终选定的正式作业配置入口到 `launch_claude_code` 交给收集器的环境验证一次设置值，以及未设置的正控；不能只直接实例化配置对象。若采用现有 extra env 路径，不要求为形式一致增加第二个参数或用户确认。

证据：[独立构造/环境探针](review_conditions_impl_20260924/main_config_probe.py)、[结果](review_conditions_impl_20260924/main_config_probe.json)。探针执行生产构造表达式，未执行完整 Bringup 的 Docker/引擎初始化；所加 `args` 同名属性仅用于检查构造点不读取它，不表示存在这个 CLI 参数。

### 9.3 CI2：#6 验收混入非生成请求，前缀指标不能替代动作归属（P2，证据口径）

`p6_smoosh_acceptance.py:73–78` 枚举目录内所有 `requests.jsonl`，没有按生成路径或原回放的 `seq`/有效记录条件筛选，也纳入了 `wire-test-q36-01`。当前输入实际为：

- **22 条基座尝试的 617 个生成请求**；
- 其中夹入的 **2 个 count_tokens 请求**；
- 另一个启动探针的 **1 个 wire-test 请求**。

合计 **620 个 body / 23 个目录 / 597 个相邻对**。因此 Brief §3.4 的“617 轮 prompt 合计 +5.8%”与实际分母不一致，71→0、73→2 等也是这份混合输入的结果，不能当成原 617 轮生成回放直接比较。主审核对原始账本并重跑独立探针确认了两条计数记录和额外启动探针；未据此推断提醒实现失效。

另一个独立问题是 `prefix_clean`（脚本 :87–89）只比较**上次 prompt 是否为下次 prompt 的前缀**。训练行能否合并需要比较**上次已有的 prompt + output** 与本次 prompt，并处理实际分支/动作归属；这个脚本未导出训练身份。故 518→589 可称“prompt 前缀一致对”，不能作为“训练行归属保持”或动作不丢的验收证据。

**最小处理：** 固定原 22 条尝试，过滤非生成记录后重算受影响统计，在新证据文件记录，不覆盖历史输出；前缀指标按真实含义命名。若要继续报告训练行/动作覆盖，复用既有 `held → prompt` 回放或身份导出证据；否则收窄文案即可，不必为了本片再建一套覆盖统计或重跑自由生成基座。当前核心预处理的角色、计数和溢出结论不依赖这组错误分母。

### 9.4 另两处非阻塞说明

1. Brief §3.3 的“窗口低于约 20K 在 2.1.205 下不可用”应收窄为 **8,192 窗口 / 1,024 输出预留 / 当前输入** 的失败结果。阈值还依赖输出预留和固定输入成本，单个负阈值反例不能确定统一 20K 下界。保留版本与固定预留的提醒，不据此添加 20K 启动闸门。
2. 新压缩证据使用真实 CC 和真实 tokenizer，但引擎输出、评分、静止屏障仍有替身，未覆盖真实 model-call proxy / 权重发布；C2 还明确移除主动压缩变量来单测被动路径。这些边界不妨碍本次协议验收，但不能宣称所有真实任务都能恢复、实际 SWE reward 已核准或正式训练窗口已确定。无须为本次收口补 GPU 实验。

### 9.5 验证、修改范围与停止条件

- 主审先跑 17 个新增用例，再纳入 capture、预算、编排、能力、Bringup 既有回归，合计 **189 passed**（含前述 17 个，不能相加成 206）。命令：从 `rh2/` 运行 `.venv/bin/python -m pytest -q tests/adapters/{test_cc_launch_conditions,test_cc_context_window,test_count_tokens_wire,test_rh2_anthropic_adapter,test_f2_0_migration,test_f2_2_capability,test_f2_3_real_adapter_freeze,test_capture_registry_fa,test_budget_deadline,test_w3b_bringup_sandbox_runtime,test_slime_generate}.py`。
- 一对限定角色分别追生产接线、反驳严重度与验证真实请求；主审自行核源码、重跑关键真实 tokenizer/HTTP 探针、补构造/环境探针并裁定。不是按多数票报告。探针及三个新模块的 Ruff 通过，`git show --check 145cb5fd` 通过。
- 本轮未新跑 Docker、真实 CC、GPU、模型 API、双 lane 或全库；真实 CC 结论是回读作者具名证据，不冒充主审另起真机复验。没有登录或调整验证机，也未重新核实其当前清理状态。
- 仅新增审查工件、更新本报告/Brief 指针与 infra 记录；未改生产代码、维护测试、fork、B 在制品或历史运行证据，未提交/push，未发送跨任务消息。
- **给 Claude 的收尾范围：** CI1 明确一条可用且经正式启动验证的 Read 配置路径，CI2 修正回放分母和证据措辞，并收窄 20K 结论即可。无新 T0，无新拒绝规则；完成后聚焦复核这些点，不重新开启已通过的宿主收集、SSE 全矩阵或已批准四项决策。正式窗口/输出/Read 数值继续留作业方案。

## 10. `716c94d5` 的 CI1 / CI2 收口复核（2026-09-24，Codex）

**通过。两项 P2 已解决，没有新增运行时 finding；决策包 §8 的四片可在既定验收范围内收口。** 本轮只复核配置运输与回放证据，不重开 §9 已通过的采样、capture、压缩与角色处理。

### 10.1 CI1：正式配置来源已接通

`BringupService._async_start_body` 的实际 `SlimeBindingConfig(...)` 构造点现已调用 `cc_file_read_max_output_tokens_from_env(os.environ)`。新入口 `RH2_CC_FILE_READ_MAX_OUTPUT_TOKENS` 解析为正整数或 `None`，经既有 `cc_context_env` 逐 execution 送入 CC 环境；没有固定测试值或新增上下文下界。

主审沿用上轮反例的边界，**执行当前源码中的实际构造表达式**，而不是在测试里手填新配置字段，结果如下：

| 输入 | 配置与 CC 环境结果 |
| --- | --- |
| `8000`，测试窗口 32,768 / 输出 4,096 | config=8000，CC 收到 `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS=8000` |
| 未设置、空字符串 | config=None，不注入该变量 |
| 两端空格的 `8000` | 正常解析并传入 8000 |
| RH2 显式 8000 + 通用 extra env 7000 | 最终为 8000，逐 execution 注入优先 |
| RH2 未设置 + 通用 extra env 7000 | 通用透传仍生效，最终为 7000 |
| `0`、`-1`、`8k` | 生产配置构造时抛 `ValueError`，不静默退回默认 |

同时重跑维护测试，确认正式读取函数 → dense 编排的 launch spec → `launch_claude_code` → 收集器所收环境，设置/未设置两案通过。维护测试本身仍手工拼装配置；本轮实际构造表达式探针补上这段接缝，所以不把它误称为整套 Bringup 的真机运行。

证据：[探针](review_conditions_impl_20260924/ci_followup_716c94d5/config_entry_probe.py)、[九案结果](review_conditions_impl_20260924/ci_followup_716c94d5/config_entry_probe.json)。测试窗口是探针条件；`max_context_len<=0` 时不注入窗口变量的既定规则未改变。

### 10.2 CI2：新回放分母与结果复算一致

主审核对脚本只枚举 `bp22-*`、只保留 `/v1/messages`（忽略 query string），并重新运行真实 Qwen3.6 tokenizer 的全部回放。仅将输出路径改到本轮审查目录，没有改处理逻辑或覆盖作者 v1/v2。结果 JSON 与作者 `smoosh_acceptance_v2.json` **完全一致**：

- 22 条尝试、617 个生成请求、595 个相邻对；两条 count_tokens 与 wire-test 已排除。
- 72 次插入处 thinking 清空 **72 → 0**；全部相邻对同样 **72 → 0**。
- prompt 前缀一致对 **519 → 591**；prompt 总量 **20,106,096 → 21,275,351（约 +5.8%）**。
- 真实摘要反例仍为独立 user 指令，没有移入工具内容。

正文和结果字段已限定为 prompt 前缀，不再据此声称训练行归属或真实动作覆盖。脚本开头还残留“训练行归属的代理指标”这一旧注释；以本段和 Brief 的明确范围为准，后续整理时删除即可，**不作为继续阻塞本片的理由**。本轮没有重新验证训练行/动作覆盖，也不把静态回放收益外推为实际求解成绩。

证据：[主审重算结果](review_conditions_impl_20260924/ci_followup_716c94d5/smoosh_acceptance_rerun.json)、[一致性及历史文件摘要记录](review_conditions_impl_20260924/ci_followup_716c94d5/replay_check.json)。v1 与 v2 在本轮运行前后摘要均未变。

### 10.3 验证与最终状态

- 相关维护测试 **29 passed**：`test_cc_context_window.py`、`test_cc_launch_conditions.py`、`test_count_tokens_wire.py`、`test_rh2_anthropic_adapter.py`、`test_w3b_bringup_sandbox_runtime.py`。改动源码、测试和本轮探针 Ruff 通过，`git show --check 716c94d5` 通过。
- Brief 已将“20K 以下不可用”收窄为具体测试参数，并说明压缩夹具的替身边界；本轮把 extra env 的覆盖措辞进一步写成上述实际优先级。没有新数值闸门。
- 本轮只做本地 CPU 复核；未新跑 Docker、CC、GPU、双 lane、全库或远端作业。字段映射与回放口径属于上一边界的窄收尾，按比例原则不另起子代理或扩大故障矩阵。
- 仅新增审查证据、更新报告/Brief/infra；不改生产实现、维护测试、B 在制品或历史证据，未提交/push、未向外发送消息。
- **停止条件已满足：CI1/CI2 关闭，本片不再等待修复或用户确认。** 正式窗口、输出预留、Read 数值仍在具体作业中决定；真实模型行为/成绩和 GPU 集成核验继续作为既定后续工作，不混作本轮通过结论。
