# 既有问题盘点：运行路径与生产可达性

日期：2026-09-08。角色：Production Tracer（沿真实生产入口追踪问题，不决定修法）。本文只解释旧审查已经提出的 token 覆盖、终止预算、内部异常、receipt 清理与 R3 来源问题；未做新一轮全仓审计，未改实现、测试、配置或 vendor。

## 1. 基线、证据口径与编号对照

本轮读到主仓 HEAD 为 `17d9899c6d4b61938f74bd9121da8dee9b621a8d`，miles 集成 HEAD 为 `98a0272e4158b2c20e3a34d210c79b50159af0f6`。`git diff --name-only ce2009f8 -- rh2` 输出为空。因此，旧报告讨论的这些 tracked RH2 实现没有因主仓同步而消失。源码行号已按当前文件回核。

以下文件作为历史主张入口，不能直接替代源码证据：

- [Codex 2026-09-05 原审查](../../miles_spike/external_infra_review_20260905.md)。本文简称“Codex 原审”。
- [Codex 2026-09-06 交叉复核](../../miles_spike/external_infra_review_crosscheck_20260906.md)。本文简称“交叉复核”。
- [Claude A：训练语义](../../tmp/external_review_20260905/report_A_training_semantics.md)。本文简称“A”。
- [Claude B：rollout 路径](../../tmp/external_review_20260905/report_B_rollout_path.md)。本文简称“B”。

**本轮没有重跑这些探针，也没有运行 GPU、Docker 或整套测试。** 文中数值来自已存在的探针输出；本轮工作是重新阅读输出、追踪当前源码，并核对引用的 pin SGLang 官方源码。历史合成输入不等于真实 Claude Code 请求，历史 Qwen3-4B 作业也不等于当前 30B 作业。

| 本文项 | 旧 ID | 本轮定位 | 与其它项的关系 |
|---|---|---|---|
| RT-1 REALIGN 覆盖损失 | A F-01；交叉复核 §2 | 一个旧响应整轮退出 loss | 与 RT-2 同属训练覆盖问题，但销毁点不同 |
| RT-2 assistant rewrite merge | A F-01；交叉复核 §2.1 | 删除消息树上的旧生成记录 | 不能只修改 REALIGN 就认为覆盖了它 |
| RT-3 25 次模型请求上限 | B F-02；A F-06；交叉复核 §3.1 | 第 26 次请求返回 429，未产预算终止事实 | 与 RT-5 的“到达裁决后怎样处置”是上下游问题 |
| RT-4 deadline、排队与 drain | B F-01；交叉复核 §3.2 | 计时起点与失败归因不同；排队越过期限已被旧探针证实 | 排队缺口与“900 秒必超过 30 秒”推断必须分开 |
| RT-5 截断处置没有生产注入 | A F-06；B F-01；交叉复核 §6.1 | 合格截断成员到达裁决点时 fail-fast | 已登记 C/W7 待办，不是新发现的正式作业事故 |
| RT-6 assemble 内部错误变 ABORTED | Codex F2；B F-03 | 同一问题重复报告 | RT-3/4 可能同样走 ABORTED，但起因不同 |
| RT-7 receipt 失败跳过清理 | Codex F3 | 旧 B5 实现、测试与现行 A4 要求未对齐 | 与 shutdown 总预算争议不同 |
| RT-8 R3 replay 来源替换 | Codex R1 | 保留早轮 logprob/版本，却选最后整段 routing | 与 token 覆盖及 R3 捕获性能是三个问题 |
| RT-9 上下文收缩拒绝 | B §3.E；A F-06 的 harness 预算背景 | 既有 0.6 判据会拒绝同一叶链的大幅收缩 | 是已存在的 profile 边界，不是本轮新增 bug |

当前真实主链是 `Rh2MilesGenerateFn → BringupService → RolloutOrchestrator → Claude Code adapter → TrajectoryManager → backfill → canonicalize → miles buffer/filter`。入口在 `rh2/src/repoharness2/adapters/miles/generate_fn.py:124–127,170–188`；因此，目录名为 `adapters/slime` 的执行代码仍属于当前 miles 候选链，不是仅历史模块。

## 2. RT-1：REALIGN 保持新上下文一致，却把旧响应整轮移出训练

**现在具体做什么。** 每轮 Claude Code 请求都重新翻译完整消息、重新套 tokenizer 模板。`rh2/src/slime/agent/adapters/common.py:58–73,341–344` 没有复用原轮输出 token 作为不可变前缀。生产 tokenizer 从 vendored slime loader 加载，见 `rh2/src/repoharness2/adapters/slime/bringup.py:828,861,887–893`；不能用 miles 的 `qwen3_fixed.jinja` 代替这个实际模板。

`rh2/src/slime/agent/trajectory.py:180–191` 对比新 prompt 与已积累 token。若首次分歧落在最近响应内，并且**新一轮输出**少于默认 1024 token（默认值在 `:271`），选择 REALIGN。真正改数据的是 `:216–224`：从旧响应起点开始替换整个尾部，新尾部的 `loss_mask` 和 `logprobs` 全置零。它不是只清零发生变化的几个 token。

**为何会存在。** 这是 vendor 为吸收聊天模板重渲染差异所做的样本合并取舍：最终训练序列必须等于引擎实际看到的新 prompt 加新输出，不能将旧 logprob 错配给新 prompt token。因此实现选择把旧响应转成上下文，继续合并一条训练行。问题在于这项取舍会损失真实生成动作，而且现有下游验证只验证“剩下的 token 是否自洽”。

`rh2/src/repoharness2/adapters/slime/turn_identity.py:110–116` 同步把被覆盖的身份区间删除；`generate.py:1492–1508` 只收集仍入训的轮版本；`governance/gate.py:333–354` 只重算现有可训 token 与分母。因此这些检查全部通过，也不能证明所有生成轮仍有训练信号。

**具体例子。** 已有 [realign-result.json](../../miles_spike/external_infra_review_crosscheck_20260906/realign-result.json) 使用真实 Qwen3 tokenizer、消息翻译、manager 与身份导出，但消息是合成的：

| 两轮输入 | 结果 | 生成 / 入训 token |
|---|---|---:|
| 27 token 旧响应；正常 tool-only 回放；2 token 新响应 | CLEAN，两轮保留 | 29 / 29 |
| 同样旧响应；tool result 后增加独立 reminder text block；2 token 新响应 | REALIGN，旧轮退出 loss | 29 / 2 |
| 同样 reminder；新响应改为 1024 token | FORK，两条训练行 | 1051 / 1051 |
| 旧响应 1125 token；新响应只有 2 token；同样 reminder | REALIGN，1125 个旧 token 全退出 | 1127 / 2 |

历史 [run8-raw-result.json](../../miles_spike/external_infra_review_crosscheck_20260906/run8-raw-result.json) 中保留的一条 Qwen3-4B 样本，旧响应起点 18508、长度 624，首次分歧在 19064。前 `19064−18508=556` 个旧响应 token 没变，旧轮仍整体不在交付分支 capture 引用里。交叉复核的辅助解码把差异定位到工具参数 JSON 键顺序；不能断言这个历史样本的唯一根因是 thinking 剥离。

**影响与证据限制。** `production_reachable`：当前请求翻译、模板重渲染、manager 合并都是真实路径；历史样本也支持实际出现过覆盖损失。但本轮没有当前 30B/CC 真实请求比例，不能说“所有多轮首轮必丢”。A F-01 的 100% 概括过度。历史报告说 run8 的 60/60 分支不含 t0，本地交叉复核只对一条保留完整 projection 读回 raw token，不能把 60 条全说成本轮核查。

**需要理解的取舍与验收问题。** 这是训练语义问题，旧复核建议训前高优先级处理（P1），不是单纯多加一条对齐断言。用户需要决定允许哪些上下文重写、旧动作应怎样保留、共享动作如何避免重复计 loss。验收要按轮同时核对 generated/trained/dropped token，覆盖 CLEAN/REALIGN/FORK 与多叶。本文不选模板修改、FORK 或 TITO 方案。尤其不能直接采用 `clear_thinking=False`：历史真实模板探针显示该变量不在模板中，开关前后渲染完全相同。

## 3. RT-2：rewrite merge 在 token 合并之前就删除旧生成记录

**位置与因果链。** `rh2/src/slime/agent/trajectory.py:302–305` 先找消息树挂点，再尝试 `_try_merge_assistant_rewrite`。消息匹配按 role 和整个 dict 相等，见 `:352–368`。若新历史回放的 assistant 消息不等，挂点下恰有一个 assistant 子节点，该节点还是叶、有生成记录，且**旧响应**长度小于 1024，则 `:419–425` 写 `merged_rewrite` 元数据后，把 `turn`、`turn_index` 设为 `None`。随后 `:465` 只选择 `turn is not None` 的节点训练，旧动作不再存在于生成轮集合。

**为何会存在。** vendor 注释明确把它定义为“只训练活动分支”的清理：避免为一个短小、已被 harness 重写的旧响应留下独立死端叶。它有意销毁旧 TurnRecord，不是捕获损坏导致的偶然错误。

**例子。** 旧 assistant 是 27 token 的 thinking+工具调用；下一轮回放同一位置时省略 thinking，使消息 dict 不等。若旧节点尚无子节点且是唯一 assistant 子节点，它会被降为 routing-only；旧 27 token 不再作为训练动作。如果旧响应为 1024 token 或更长，这条 merge 分支不执行；这与 RT-1 检查“新输出长度”不同。

**影响与证据边界。** `production_reachable`，但须满足上述树结构条件。已有 `realign-result.json` 的 `replay_omits_thinking` 是合成回放，交叉复核指出它同时涉及这里与 builder 分类；不能用输出中的 `builder_classification=realign` 抹掉消息树先发生的销毁。本轮不声称当前 CC 每次回放都会省略 thinking。

**重复关系与待定面。** 属于 A F-01 同一覆盖问题的第二个销毁点，应与 RT-1 一起解释、分别验收。只修 `_align_to_prompt`，无法恢复已经被设为 `turn=None` 的记录。是否保留此类被改写动作仍是用户的训练语义选择；验收须区分 merge 生效/不生效、多 assistant 子节点、旧节点已有后继以及共享前缀的单次训练规则（`:456–476`）。

## 4. RT-3：25 次 cap 是 API 请求限制，没有变成训练预算事实

**位置与现行行为。** `rh2/src/repoharness2/adapters/slime/bringup.py:229` 默认 `RH2_MAX_TURNS_PER_SID=25`，`:892` 传给 adapter。它已经是环境参数，不是完全不可配置的常量。`rh2/src/slime/agent/adapters/common.py:285–306,331–333` 在渲染和发模型请求前检查 SID 计数：前 25 次加一放行，第 26 次及以后返回 HTTP 429，类型为 `rate_limit_error`。计的是模型 API 请求，不是 bash/read/edit 等工具调用数量；主 agent 和子 agent 共享 SID 的关系见 `generate.py:1111–1116`。

契约存在 `max_turns_exhausted`，见 `rh2/src/repoharness2/contracts/fa_runtime.py:287,306`；本轮 `rg` 搜索 `rh2/src` 与 `rh2/experiments` 只找到契约、说明和消费，没有这个事实的 producer。adapter 也没有把命中 cap 的事件直接交给 orchestrator。

**为何会存在。** 上游 adapter 的限制是 HTTP 层粗粒度保护；RH2 后来增加了训练终止分类，但该 cap 仍沿用 rate-limit 出口，两层没有衔接。代码中“killing run”只是日志文案，返回 429 本身没有直接杀掉整项训练。

**具体例子与限制。** 已有 [runtime-result.log](../../miles_spike/external_infra_review_crosscheck_20260906/runtime-result.log) 的真实 `_check_turn_cap` 探针是 25 个放行结果、随后两次 429。若 CC 收到 429 后非零退出，`generate.py:2801–2809 → outcome_producer.py:56` 会按 `harness_crash` 收口；若它重试等到时间墙，可能进入 RT-4。**CC 2.1.205 到底怎样处理这个 429，本轮与旧探针都没实测，所以不能说第 26 轮必然变 harness_crash。**

**影响、分期与验收问题。** cap 的生产可达性确定，实际覆盖率未知；当它阻断长任务时，会影响长轨迹分布和失败归因。旧 B 报 P0，交叉复核收窄为 C/profile 需要明确的模型请求预算及 producer 缺口。需由用户决定 cap 预算、计数作用域、正常预算终止出口，再实测 CC 行为；不是先把 25 改 100 就证明语义正确。验收须同时区分模型请求数、工具调用数和子 agent 请求数。

## 5. RT-4：多重计时需要分开解释；排队越过 deadline 是已证实的窄缺口

### 5.1 当前三处计时分别控制什么

| 计时点 | 当前代码 | 到期行为 |
|---|---|---|
| harness 墙钟 | `rh2/src/slime/agent/sandbox.py:63–77`，等待 done marker 时起表 | 返回 `-1`；该函数自身不杀进程；轮询会有粒度与 RPC 延迟 |
| 模型 proxy deadline | `capture_wire.py:377–392,1159–1166`，首次模型调用按同一 `AGENT_TIME_BUDGET_SEC` 起表 | 剩余少于默认 5 秒时 poison，或限制单次 send timeout |
| 会话 drain | `capture_wire.py:534–561`，默认 30 秒 | revoke 拒新，等现有 inflight；未归零返回不干净结果 |

`bringup.py:612` 的 900 秒是单次 attempt timeout 上界，`:1222` 设置会话预算；`async_worker.py:734–740` 实际发请求的 timeout 是 `min(900, deadline−now)`。因此 B F-01 仅凭“900 大于 30”推断所有撞墙请求都来不及 drain，不成立。

### 5.2 预算耗尽有几种不同出口

正常观察到 harness `-1` 时，`generate.py:2753–2759` 正确记 `hard_wall_timeout`；随后先 drain，再 `finish_session`，见 `:2762–2789`。若 capture/quiescence 完整，`outcome_producer.py:86–100` 允许形成 `present_truncated`，进入 RT-5。

另一条出口是 proxy 在自己的期限前剩余不足 5 秒：`async_worker.py:853–860` 抛 `episode_deadline_exhausted`，`:827–829` poison；`generate.py:2734–2747` 取消 harness 并将其归为 `session_poisoned_during_execution`，最后按 `api_failure/model_proxy_failure` 形成 missing。两只钟虽同长，起点不同；是否抢在 harness 墙前触发，取决于 CLI 启动时间、请求发起时刻、harness 轮询和排队，不是固定“最后 2–4 秒必触发”。

drain 还有自己的失败出口：`generate.py:4260–4274` 把 revoke/inflight/pending/draft/poison 任一不干净结果转成 `session_plane_drain_unclean`，assemble 的通用异常映射为 `capture_incomplete/missing`。这里可能是真实取消、传输故障或仍在飞请求，不能把所有 drain 不干净都当我方内部逻辑 bug。

### 5.3 已证实的排队缺口

`rh2/src/repoharness2/adapters/slime/async_worker.py:748` **先**算剩余 timeout，`:753` 再等待 `model_call` semaphore，`:756` 使用旧 timeout 调 send。等待 semaphore 本身没有 deadline，拿到许可后也不重算余量。真实接线 `bringup.py:607–615` 的默认 semaphore 容量为 32，因此这不是仅测试可达 helper。

已有 `runtime-result.log` 调真实 `ModelCallProxy.call`：deadline=20ms，先占住 semaphore 约 40ms；`send` 在 41ms 才开始、47ms 成功。它证明“请求已过期仍发出”，不能证明正式任务经常排队 40ms，更不能推算 GPU 损失比例。

**当前理解与待定面。** 排队缺口是已证实的 `production_reachable` P1 实现问题；启用该预算的 formal profile 前应处理。其验收问题很具体：许可等待到期限后还会不会进入 send，许可是否释放，失败是否按选定预算语义归因。其余多钟出口是 C/profile 需要澄清的合同与生产观测，不据此预定“删 proxy deadline”“先 kill 再 drain”等方案。

## 6. RT-5：截断裁决接口存在，实际策略仍未生产注入

**位置与因果链。** `rh2/src/repoharness2/adapters/miles/group_admission.py:515–523` 读取 `args.rh2_disposition_policy`；缺省返回四槽为 None 的 `DispositionPolicy()`。`rh2/src/repoharness2/governance/admission.py:635–647` 在成员其它要求通过、`completion_class=present_truncated` 后，按终止类别选择槽位；None 抛 `DispositionNotInjectedError`。filter 在 `group_admission.py:544–554` 通知 run-fatal 并原样抛出；它在 miles `DefaultDataBuffer.put:257` 被调用。

**为何会存在。** 06 计划 A5 明确把 timeout/truncation 的保留/排除选择留给 C，W1b 只建中立接口与缺注入 fail-fast。这是刻意未替 owner 决策，不是“接口作者忘了给一个安全默认值”。但 C/W7 完成后仍须有真实配置 producer，不能把已有单测当成入口已接好。

**例子。** n=8 中一个成员达到 hard wall，capture、冻结产物与评分均完整，符合截断事实；其余成员正常。若仍没有 `hard_wall_truncation`，该成员到达裁决点时抛错，整次 run 失败。若它先经 RT-3/4 变 ABORTED，则完整组 filter 根本看不到它，故 RT-5 不能代替修正前面的预算归因。

**证据与分期。** 静态路径确认；交叉复核记载 45 项相关测试已覆盖缺注入失败、KEEP_FULL/DROP_GROUP 两种注入，**本轮未重跑**。当前 `rg` 仍无配置好具体槽位的生产构造点。属于 C/W7 已登记的正式入口前置，不把未审 launch 草案当成已声称可正式运行的作业。改变保留/排除会改变训练分布，由用户决定。验收需从真实启动配置追到 filter，不能只测手工构造 policy 的 helper。

## 7. RT-6：结构矛盾在 assemble 阶段仍可被包装成普通 ABORTED

**当前行为与原因。** `rh2/src/repoharness2/adapters/slime/generate.py:3422–3449` 仅显式升级若干契约错误；ValidationError 的阶段升级范围也是 finalize/deliver。其它异常在 assemble 阶段进入 `_abort_after_task_local_exception`，`:3511–3516` 按错误码或阶段归类，`:3537–3556` 产 missing Outcome 并返回 ABORTED。这里保留了旧“未能形成完整对象则保守缺员”的行为，却没有完全落实 06 附录 A `:176` 已批准的“身份、引用、reward、mask、logprob 等账实矛盾走 FATAL”。

**可解释的真实边界例子。** 上游响应有正常 token、logprob 和版本，只有 `meta_info.id` 缺失：

1. `generate.py:806–829` 返回 `capture_status=failed` 的 record，有 `record_id`，没有 TurnTape。
2. `capture_wire.py:737–750` 只要求 hook 返回非空 `record_id`，不要求这里有完整 tape。
3. `capture_wire.py:1284–1299` 先附着真实消息树，再 commit，并把引用绑定到新增 turn。
4. `generate.py:2883–2889` 叶回填时找不到 tape，抛 `capture_record_unknown_in_backfill`。
5. 通用异常出口把它变为 missing/ABORTED。
6. miles `fully_async_data_buffer.py:239–256` 在 dynamic filter **之前**整组交 unused handler 并返回。严格的组 admission 没有机会重新把引用矛盾判成 FATAL。

已有 [failure-probes-repeat.jsonl](../../miles_spike/external_infra_review_20260905/failure-probes-repeat.jsonl) 的 `wire_commit_missing_meta_info_id` 经真实 hook、registry、formal 编排得到上述输出。HTTP、树与 Docker 有夹具，真实树绑定另由当前源码回核。它是 `production_reachable` 的协议故障注入；尚未观察 pin SGLang 在真机返回缺 id，频率未知。人为 TypeError、leaf-facts 数量不一致等探针仅用来说明异常分类，不能另作“生产已发生这些 bug”的证据。

**影响与重复关系。** 这是 Codex F2 与 B F-03 的同一问题，不加算两项风险。后果是某些组消失而训练继续，可能造成类型相关的样本损失；没有证据说明错误 logprob 已进入 loss。也不是完全无日志：Outcome 保留具体 reason，failure record detail 也含异常文字；只是 miles 的组事件此时只输出 `aborted_member` 与成员身份（`:241–253`），`abort_reason` 本身只有 stage 与异常类（`generate.py:3556`）。好组持续产生时，no-progress 不能保证暴露这种部分失败。

**分期与验收问题。** 旧 Codex 建议正式训练前处理 P1。需落实既有内部矛盾 FATAL、已归因 task-local 软失败的边界；不能把所有 drain/capture 故障一并升级。验收应经过真实返回与 put 边界，确认结构矛盾不再成为普通 ABORTED，同时保留已批准的单任务故障出口。本文不采纳新 fatal 白名单或新 N 次计数熔断设计。

## 8. RT-7：receipt 失败时跳清理是旧策略仍在生效

receipt 是 attempt 的终局记录，不是容器本身。`rh2/src/repoharness2/adapters/slime/generate.py:3596–3620` 构造/写 receipt 失败后标记失败，若容器未释放则加入 `cleanup_quarantine`。`:3646–3652` 以 `receipt_persist_failed and mode != s1_compat` 跳过 session drop 与容器清理；`:3767–3775` 在没有首因异常在途时抛 typed fatal。已有 fatal/取消在途时只保留首因传播，不另用 receipt 错误遮盖它。

**为何会存在。** 这不是缺少 finally：finally 主动执行“receipt 未 durable，保留活动现场”的旧 B5 策略。当前测试 `rh2/tests/adapters/test_b5_finalization.py:103–120` 仍将“不执行 docker_rm、存在 quarantine”当正确答案。现行 06 A4 则要求核心 admission 记录失败时“样本不交付、run-fatal，但仍 revoke/终止 scope/清容器”。实现、测试与现行要求未对齐，是问题根因。

**具体例子。** 已有 `failure-probes-repeat.jsonl` 注入冻结前 harness crash 加 receipt `ENOSPC`，得到 `lease_released=false`、`docker_removed=[]`、`adapter_dropped=[]`、一个 quarantine，最后 fatal。这是生产可达的故障组合，但没有实际发生率与真实 Docker 故障实测。

**必须保留的两个限定。**

- 成功冻结后容器已经提前释放，见 `generate.py:3186–3196`；此时 receipt 失败仍 fatal，却没有这个容器可遗留。因此不能说所有 receipt 失败都会留容器。
- service shutdown 的 `bringup.py:1774–1788` 仍 revoke/drop/unregister capture session；不能声称 session 永久可调用。但其 `container_residue:1805–1811` 只报告 quarantine，没有在那里删除残留容器。最终 launch trap 是 W7 接缝，不能假设已替这个分支完成清理。

**分期与验收问题。** Codex F3，建议租 GPU 前与 W7 清理接线一起收口。核对相同 ENOSPC 场景是否仍无交付、仍 fatal、首因保留，且实际执行已批准的清理；成功冻结路径须仍只释放一次。若用户选择保留活动容器现场，就是对当前清理要求的明确改判，不能由旧测试自动决定。它与“shutdown 第一阶段超过预算后晚清理成功是否算失败”不是同一问题。

## 9. RT-8：最后一轮 R3 tape 可以覆盖早轮的路由来源

R3 是记录 MoE 每个 token 选中的专家，并在训练 forward 中重放。这里的问题是“究竟重放哪次 forward 的路由”，不是 tensor 行数。

**当前选择点。** `rh2/src/repoharness2/adapters/slime/generate.py:1427–1472` 检测到 routing 后取 `turns[-1]` 的全量 tape；必要时只裁掉多出的最前行，再给整条 Sample。它没有逐轮拼入最初 decode 的 routing。与此同时，旧轮输出 logprob 按原轮保留，旧轮版本按 `:1492–1508` 汇入。`capture_wire.py:1060–1066` 只请求 `return_routed_experts=true`，没有设置增量起点。

**为何会存在。** 这是沿用上游整序列 R3 表示的拼接办法：最终 Sample 等于末轮 prompt+output，末轮完整 tape 正好有需要的 `len(tokens)−1` 行。这个形状正确的选择没有额外证明：末轮 prompt 中早先生成部分的路由，是否仍等于它们原来 decode 时的路由。

**具体例子。** 已有 [r3-origin-repeat.txt](../../miles_spike/external_infra_review_20260905/r3-origin-repeat.txt) 经真实 TrajectoryManager→backfill，用两轮人工 tape：第一轮路由值为 1、第二轮为 7。合并后早轮两处训练响应的 route 都变成 7，但行为 logprob 仍是 `−0.1, −0.2`，版本保留 `10,11`。这直接证明来源选择，不能证明 GPU 上差异率必为 100%。

**生产条件。** 本轮重新读取 pin `4e230c3d85cefdab5b65eeb6f6f87793a707a6fb` 的官方源码：`reset_for_retract` 在物理源码 `1674–1680` 清空前缀索引与 routing；state capturer 在 `147–162` 默认取从 0 到 `seqlen−1` 的 host cache，`164–186` 将当前 forward 路由写回。见 [SGLang Req reset](https://github.com/sgl-project/sglang/blob/4e230c3d85cefdab5b65eeb6f6f87793a707a6fb/python/sglang/srt/managers/schedule_batch.py#L1674) 与 [state capturer](https://github.com/sgl-project/sglang/blob/4e230c3d85cefdab5b65eeb6f6f87793a707a6fb/python/sglang/srt/state_capturer/base.py#L147)。

当前 miles `miles/backends/megatron_utils/update_weight/update_weight_from_distributed/mixin.py:309–318` 在 retract 等非 in_place 模式下 pause 后 flush cache；`miles/router/router.py:215–229` 按最少活动请求选 engine，没有按 session 绑定。**由这些源码推得**：跨 publish/retract，或下一轮落到冷缓存 engine 时，早前 token 可在新 forward 中重新 prefill，最后 tape 可使用重算路由。不要把最少活动请求说成均匀随机，也不据此推算缓存命中率 `1/N`。

**裁定与待定面。** `production_reachable` 的来源替换；不是 GPU 数值损害已被证实。它也不是 REALIGN：即使 token 覆盖 100%，仍可选到后轮路由；反过来，路由完全保真也不能补回 RT-1/2 被移出 loss 的动作。与 Codex F1/B F-04 的 routing 捕获 CPU/内存成本同样分开。

Codex 原 R1 留给 C 包与 GPU 资格。用户需要明确目标是逐 token 原始行为路由，还是允许最后整段重算路由近似；然后用跨 turn publish 和单次 generate 内 retract 两种情形对拍原始 route、最终 replay route、logprob/ratio 及更新。本文不预定逐轮训练、拼旧路由或关闭 R3；shape 对、消费耗尽、dense smoke 成功，都不能代替内容来源证明。

## 10. RT-9：上下文大幅收缩是已有拒绝面，不与 REALIGN 混为一谈

`rh2/src/repoharness2/adapters/slime/generate.py:1100–1134` 对同一轮序列计算历史最大 prompt，后轮小于 `0.6 × max_prompt` 则记录收缩。session 级调用 `:2862–2868` 只记 audit，避免把主 agent 长历史后启动短上下文子 agent 误判；实际硬拒绝在每条叶链的回链轮上 `:2894–2905`，启用 `reject_context_shrink` 时抛 `context_shrink_detected`，按 capture_incomplete→missing/ABORTED 收口。

例：同一叶链 prompt 从 20000 token 变为 10000，`10000 < 0.6×20000=12000`，命中收缩判据。新建子 agent 使用独立短历史，不等于同一叶链收缩；不能从 SID 全局大小变化直接定违规。

这条路径是已批准的 compaction 兜底在当前代码中的作用，B §3.E 将其列为长度相关拒绝面，并没有为它提供当前 CC 真实频率。本轮只确认 `production_reachable` 的条件，不把它升级成新 bug。REALIGN 是样本合并后旧动作变 mask=0，此处是整个 attempt 缺员，两者影响粒度不同。首训是否允许 compaction、哪些真实请求属于可接受历史改写，仍应跟 C 的 harness 工具面一起决定；不能因为它也影响长轨迹就默认删除。

## 11. 本轮回核清单与停止点

已重新读取上述关键 producer/consumer/异常/清理锚点；核对主仓与 miles HEAD，以及旧基线以来 `rh2` tracked diff 为空；逐项读取旧探针输出；对 R3 的两个 pin SGLang 文件进行了本轮只读网络回核，并用 raw 文件物理行号校正网页提取行号。未保存或修改外部源码。

本轮没有提出新的实现方案、训练拒绝策略、T0 拍板或闸门变化。覆盖损失的真实比例、CC 429 行为、多钟竞争频率、GPU route agreement/数值后果仍是未知；不以 CPU 或合成结果替代。上述主题已覆盖并回到当前真实路径，至此停止，不继续扩审性能、维护删除面、评分质量或其它新问题。
