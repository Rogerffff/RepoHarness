# 预算终止闭环 Brief 聚焦审查

日期：2026-09-09。对象：[Claude Owner Brief](README.md)。结论：**支持四项按下述限定范围改为 FATAL；不支持原 Brief 不作修订直接实施。下面四组修改是在落实既有决定，不要求 owner 再决定一套预算或失败策略。** 本文是审查建议，不将用户“是否可以确认”的提问登记为批准。

审查结束时 HEAD 为 `297f1f59`，对应 I01 提交；`rh2/src` 与 `rh2/tests` 没有未提交差异。该提交在本轮审查期间出现，不是本轮执行提交，也不是预算闭环已实施。I01 针对性复核已通过，Brief 的“I01 待复核、未提交”须更新。

## 1. 四项可以一起确认，但不能只按异常名字扩大全仓处置

| 项目 | 建议与原因 | 必须保留的范围 |
|---|---|---|
| `fa_identity_incomplete_in_formal_mode` | FATAL。正式入口由我方写入 execution/member 身份，到编排时残缺表示接线或入口违约；补采不能修复它。 | 当前非 `s1_compat` 身份守卫；不改变兼容链允许无 FA 身份的规则。 |
| finalize 前逃出的 `ValidationError` | FATAL。不能只因尚未到 finalize，就把我方必需契约构造失败当作可补采成员。它可能是内部错误、配置错误或未正确归因的输入问题，不必声称每一种都是代码 bug。 | 限于本次 generate/adapter 编排边界；可选 telemetry 内自行处理的校验错误、模型工具或测试中的报错不扩大。已识别的外部局部失败应在其来源处分类。 |
| `frozen_artifact_persist_failed` | FATAL。冻结补丁及基线是后续评分与准入的核心事实，落盘失败属于 A4 已明确的核心记录持久化失败。 | 不交付样本、通知停 run，同时继续 session/scope/container 清理；不扩大为所有可选审计写入失败都停 run。 |
| `sampling_mask_tape_missing_in_assembly` | FATAL。已经要求记录 sampling support，但装配引用的 tape 没有该事实，不能继续伪装成普通缺员。 | 只改该装配守卫；未启用 mask 的会话不受影响。合法零输出的空支持集与缺失 `None` 不混为一谈。 |

来源：`generate.py:2654–2666,2951–2965,3187–3207,3456–3467`；逐项入口与例外见 [错误来源核查 §1](error_scope_review.md#1-四项的真实来源与限定范围)。既有授权见 [06 A4](../../06-first-training-local-execution-plan.md#L37)、[D1 高层原则](../../06-first-training-local-execution-plan.md#L182) 与 [第二组 §2](../batch2_failures_20260908/README.md)。

**旧测试保护 ABORTED，只能证明旧行为，不能推翻后续已批规则。** 这四项大多属于既有 D1/A4 的落实；本轮快速确认适合澄清范围，不必再为每个错误码建立新的 T0 决策包。

## 2. 开工前应修正的四组内容

以下均为本次计划范围内的修改，不扩展至 I13/I16、loss、子 agent 是否启用或新的恢复平台。P1 表示应在对应切片启用前闭合，不等于要求阻塞其它已授权的独立工作。实际发生频率尚无新作业统计，不编造比例。

### R1｜批 A：不能把“已有错误码”直接当作“已归因局部故障”（P1）

- **计划行为与位置**：Brief `:36–39` 将 materialize 的整批 typed 码保留为 ABORTED，将 CLI 引导的 `RuntimeError` 统一包成 `harness_bootstrap_failed`，已映射 capture 族不动。
- **违反的规则**：D1 允许 ABORTED 的依据是已归因的 task-local 故障，而不是异常有没有名字。内部事实、引用或配置矛盾不能被补采掩盖。
- **主审核对的证据**：`bringup.py:324–332` 的 CLI 版本不符确实抛 `RuntimeError`；`generate.py:3934–3943,4136–4144` 的血缘/digest 码包含查询成功但内容错误；`outcome_producer.py:61–62` 已将 `leaf_facts_length_mismatch`、`capture_record_unknown_in_backfill` 归为 capture 不完整，而 `generate.py:2896–2912` 表明它们是我方树事实条数或引用对不上。
- **具体后果**：例如每次装入错误版本的 CC，都可以被改名成“引导失败”，丢组后继续补采；若只涉及部分镜像或分支，系统可能一直运行却选择性丢掉这类任务。上述来源在当前生产调用链中可达；本轮未声称真实训练已经触发。
- **修法与分期**：批 A 开始写映射前先修短表。可识别的局部运行/服务/传输故障保留 ABORTED；成功读取后发现版本、血缘、digest 不符，以及内部引用/事实矛盾，沿既定 fatal 通道。混合原因码在抛出点区分，保留原始原因，不新增通用分类平台。不能反向把所有 Docker 非零退出都叫结构错误。
- **最小反例与验收**：错误 CLI 版本、成功 inspect 但 digest 不符、两条内部 capture 矛盾不能返回 ABORTED；一个明确局部运行故障仍按原规则缺员。FATAL 必须实际通知 halt 且 finally 清理继续。具体来源和 CPU 反例记录见 [窄核查 §2–3](error_scope_review.md)。

### R2｜批 B：统一 deadline 必须同时接通执行中断、取消清理与原因传递（P1）

- **计划行为与位置**：Brief `:49–56` 主要在入口计算 deadline、harness 启动前扣剩余，以及限制 model-call 信号量等待。
- **违反的规则**：从资源占用起表必须是实际强制保护，不能只是审计时间。准备、排队和引导也要受限；到期不能把清理一并取消。
- **证据与例子**：`generate.py:2668` 等待物化，随后执行 baseline；`bringup.py:350–382` 接收剩余秒数后，仍先安装 CLI 和执行最长 900 秒的 useradd/chown，才调用 vendored harness。若传入还剩 20 秒，引导又用了 60 秒，只靠相对参数仍可能在总期限后启动 CC。物化若一直不返回，启动前的剩余检查根本到不了。
- **取消的直接接缝**：`docker_sandbox.py:27–40` 只处理自身超时，不处理外层取消；`generate.py:4049` 的物化清理只捕获 `Exception`，取消时外层 `sandbox` 尚未返回，`:3689` 也不会清理它。应在现有资源 owner 内补齐取消责任，包括已经创建或创建结果未确认的容器/网络，不只修改 grading 的 Docker runner。
- **归因的直接接缝**：`async_worker.py:868–878,919–923` 会吸收 `_send` 的 deadline 异常并改写为 `no_overlapping_update_window`。主审独立重跑探针已经确认；只让 `_send` 抛正确码、再在 harness 取消分支读 poison reason，还没有闭合。普通单次请求超时也不能一律改叫 hard wall。
- **修法与分期**：批 B 内用同一绝对期限约束实际执行阶段，停止/清理/评分仍各用有界预算；vendored 相对整数秒仅作兼容参数。一起补实际子进程通道、物化取消收口及 proxy 原因传递。不要求另建状态机或计时归因系统。
- **可达性、反例与验收**：准备与引导等待、proxy 通用异常分支为当前生产可达；新 deadline 主动取消物化会启用现有取消缺口。用可控时钟和资源替身覆盖“已创建容器后到期”“CLI 引导未完成时到期”“排队/发送时到期”。必须断言不再启动后续工作、已持资源收口，以及经真实 `proxy.call` 后原因仍正确，不能只测 `_send`。已运行的窄反证见 §5。

### R3｜批 C：cap 事实不能覆盖 hard wall、真实故障或不完整 capture（P1）

- **计划行为与位置**：Brief `:64,66,129` 将“预算事实在场”的非零退出/取消改为正常 turn 截断；cap 后挂到墙钟仍以 cap 为准，并把该优先级写成 T1。
- **违反的规则**：[第一组已批](../batch1_budget_20260908/README.md#L5) hard wall 触发整组不训练；cap KEEP 以可信、完整收口为条件。首个停止原因与最终是否可训练是两件事。
- **最小反例**：600 秒期限，595 秒 cap 命中，CC 未停止；600 秒执行仍在持续并触发 hard wall，625 秒才强杀。不能只因先命中 cap 就 KEEP。反之，若 598 秒已经停止执行，之后清理到 620 秒，不应仅因清理越过 episode 时间戳就补造 hard wall；清理本来有独立预算。
- **另一个真实接缝**：同一 sid 没有强制串行请求锁。cap 拒绝本身不 poison，不代表在飞请求不会因断连 poison；`async_worker.py:870–876` 明确记录 `client_cancelled`。主审回环探针确认断连能经现有 relay 取消 handler，同时产生这个真实失败。不得为得到 KEEP 而清除它、覆盖外层取消或跳过完整性检查。
- **修法与分期**：批 C 沿用“实际 hard wall → DROP”；cap 与 wall 的事实都保留。30 秒只作有界收口的候选实现值，允许执行的等待服从 episode deadline，不接受新模型工作；不把它包装成已定的额外行动预算。cap 只解释由预算拒绝导致的退出，不豁免已有 fatal/poison/capture 缺失。若坚持 cap 覆盖实际 hard wall，才是需要重新提出的 T0；本审查不推荐。
- **可达性与验收**：cap 优先规则尚未实现，为本批会启用的条件分支；并发请求及取消传播是现有代码能力。覆盖 cap→wall、cap→正常停止、已停止后清理越界，以及 cap 与在飞失败/外层取消同时发生。计数达到 N 不应直接提前抹掉尚未交付的第 N 轮；N 是接纳数，不承诺 N 条成功生成。

### R4｜批 D：最终仍在运行或无法确认停止，不能只追加一段 infra 文本（P1）

- **计划行为与位置**：Brief `:74` 在 rm 失败或容器仍在时，仅记录 `cleanup_failures` 与 `container_stop_unconfirmed`。
- **违反的规则**：A4 与第一组停止规则已批准 scope 最终无法终止为 run-fatal，仍继续清理。普通 `failed_to_grade` 不等于这个通道。
- **当前证据**：`manager.py:1410–1424` 清理失败只记录，`_container_running` 把 inspect 失败也压成 False；普通 grading infra 会经 manager 返回评分失败而非通知停 run。Docker 服务不可达时，inspect 失败不能证明容器不存在。
- **影响与可达性**：评分超时后的清理是当前正式调用链；容器测试仍运行或状态未知却继续接收新任务，会延续资源占用。确切发生频率未知。
- **修法与分期**：批 D 明确三种事实：已停止/已删除、仍运行、无法确认。有界收口结束仍运行或未知，走已有 fatal 传播，并继续清理。第一次 rm 失败但随后确认安全停止，不自动 fatal；停止与删除也不混为一谈。这不推翻 I13 对中间等待超时后安全收口的既定例外。
- **最小反例与验收**：FakeDocker 分别模拟 rm 失败后已停止、仍 running、inspect 不可用；前者保留诊断，后两者在最终有界收口失败时通知停 run。宿主 CLI kill/wait 与容器停止分别验证；只测 `cleanup_failures` 增加不足以验收。

## 3. 实施顺序可以保留小批，但调整两个接缝

1. **先 A**：修正错误来源短表，落实四项的限定范围、两条 capture 矛盾和 I12。无需等 36 个问题全决定；四项尚未由用户本轮明确回复时，已经批准的独立部分仍可按原授权推进。
2. **再 B**：同批完成 deadline 和它会触发的取消清理，不能先接主动取消、后面再补持有资源无人清理的空档。
3. **C 与 D 中的 disposition 注入形成同一可运行版本**：可以分提交，也可以先注入再启用 cap；不要交付“cap 已产 `present_truncated`，但策略仍 None”的中间版本，否则第一个 cap 又会 `DispositionNotInjectedError`。D 的 grader 回收可以独立提交。
4. **不冻结完整未来批次**：以上只是当前依赖关系。代码所有权按 Brief 列出的具体文件协调；这次查到的 `docker_sandbox.py` 要补入，不扩大为 A 独占全部 adapter。每批实际修改后做聚焦审查与必要回归。

其它范围说明：

- 600 秒、25 次继续是现有默认，不是已验证正式配方。把准备和排队计入后，同样 600 秒对应的可行动时间会减少。首次真实诊断前与 B 一起选较宽数值并记录，无需现在冻结数字。
- `policy_horizon_truncation="KEEP_FULL"` 共用槽位本轮只服务已批准的 turn producer；不从它推导未来 token/context producer 也已获准。
- 守卫计数前置条件须保持：旧 `common.py:325–331` 先读 JSON、预处理与检查 session，再计数；不要把“仅认证通过”直接称为完全相同口径。复用已有解析，不复制第三份消息校验逻辑。
- 429 的现有拒绝路径及非零退出分类可静态证明；具体 CC 二进制收到 429/403 如何退出，仍需按已列的真实 CC 探针确认。不能将 SDK 规则推断写成此次已经跑过的真实 CC 结果。停止链的大部分逻辑可以本机测试；目标 GPU 上 abort 到达与实际停算仍是部署验证，不要求先租八卡才能改上述代码。

## 4. 决策与审查边界

- **既有 T0 的落实**：四类当前执行链内部/核心持久化失败、hard wall DROP、可信 turn KEEP、scope 最终停止失败 fatal。旧测试 oracle 相应改变至少作为 T1 报告，不能以“不动旧测试”保留相反行为。
- **遗漏的 T0**：仅当作者仍坚持“cap 覆盖实际 hard wall”时，需作为推翻既有决定单列。按 R3 修回旧规则就消除此新增决策。
- **递延**：具体预算数值、未来 token/context horizon、子 agent 是否启用、I13/I16 其它实现，不由本轮批准。
- **需实验验证而非先决定的内容**：真实 CC 403 行为、部署环境的 kill/abort 停止事实。本机反证足以指出当前接线缺口，不能替代这些真实验证。
- **适用性**：本次是计划审，重点 A/B/D/E/F/G/H/I/L/M/N（失败与并发、训练处置、所有权、测试入口、定案一致性、实际路径、事实来源、分期、活性、诊断、CLI 依赖）。J/K 只核是否需要更复杂的实现；C 未建议新增临时挡板。没有把未改的 loss、数据筛选、完整 shutdown 系统重新审一遍。

## 5. 验证证据与停止条件

主审回读现有授权、Brief、实际生产入口与错误来源，独立审读两份窄报告；随后独立重跑 [timing_stop_probe.py](timing_stop_probe.py)，命令如下，退出码为 0：

```bash
cd rh2
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/timing_stop_probe.py
```

输出说明三个当前事实，而不是修复已经通过：

```json
{
  "deadline_reason": {
    "raised_reason": "no_overlapping_update_window",
    "poison_reason": "no_overlapping_update_window"
  },
  "docker_cli_cancel": {"kill_called": false, "wait_called": false},
  "relay_disconnect": {"handler_cancelled": true, "poison_reason": "client_cancelled"}
}
```

探针只用进程替身和本机回环 HTTP，没有真实 Docker、CC、模型 API 或 GPU 作业。没有修改业务源码/测试，没有再次运行 I01 的全量测试，没有执行提交或推送。补充报告：[错误来源与停止分类](error_scope_review.md)、[计时与停止反证](timing_stop_review.md)。

**停止条件**：Claude 将 R1–R4 的语义修正、资源归属和最小验收写回 Brief，即可按上述依赖推进已授权工作；不要求再等一轮全面设计评审。实现后核对应切片，不因还能构造未来功能反例而无限延长本批。若作者不同意某条，按既有四选一回应给出源码/决策证据即可。
