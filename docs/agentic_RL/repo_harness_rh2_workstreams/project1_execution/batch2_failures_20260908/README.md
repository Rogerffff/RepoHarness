# 第二组：错误、丢组、重试与退出

创建：2026-09-08；更新：2026-09-09。状态：**I13 窄改判、I15 首版完整组＋原因观测已确认；I16 最多追加一次同工件评分及允许失败阶段/类别表均已确认，见补充说明 §8。实现均待办。** 主归属 I05/I12/I13/I15/I16。第一组已确认的 turn KEEP / hard wall 整组不训练保持有效。没有修改训练实现或配置。

用户 2026-09-09 对 I13 原话：“我同意你的建议，这里最后退出对于训练来说影响不大，记录好诊断即可。”按下文限定范围登记：纯中间等待超时可在最终安全收口后允许成功，其它原有失败条件保持。下文保留原提案比较；I15/I16 的成本、分布与重试解释见 [补充说明](i15_i16_sampling_and_retry_20260909.md)。

来源：[问题导读](../issue_inventory_20260908/README.md)、[调用链证据](../issue_inventory_20260908/runtime_tracer.md)、[旧主张反证](../issue_inventory_20260908/claims_falsifier.md)、[06 计划 A2/A4/附录 A](../../06-first-training-local-execution-plan.md)、[已批 D2/B](../../miles_spike/decision_package_D2_B.md)。本组沿既有证据核对当前代码，不重新做全仓审计。

## 1. 五个问题：09-08 的收敛与当前状态

| 问题 | 例子与当前事实 | 本轮怎样收敛 |
|---|---|---|
| I05 内部错误变成普通丢组 | 树侧给两条训练分支，却只给一份配套事实；或者 capture 返回引用但没有对应 TurnTape。异常最终可能变成 ABORTED，miles 丢组后继续生产新组。 | 已知账实矛盾与当前执行链不可归因异常都已有 fatal 原则，直接落实漏网分支。 |
| I12 核心记录写失败跳清理 | 冻结前 harness 失败，随后 receipt 落盘遇到磁盘满；旧分支报 fatal 却跳过 session/container cleanup。 | A4 已要求 fatal 且继续清理，直接修实现和旧测试，不重问。成功冻结后已释放的容器不属于同一残留路径。 |
| I13 晚清理成功仍算失败 | 第一段等待取消用尽预算，后续 RH2 清理实际完成；第一段的失败仍使最终 `ok=false`。 | 原实现符合旧 B-6；2026-09-09 用户已批准下述窄改判，实现待办。 |
| I15 一个失败损失全组 | 八个成员中一个不合格，会损失正常兄弟；异步消费时版本超龄可能进一步丢弃慢组。 | 全员准入与 consume-time staleness 已定。补充已有观测，不改成七人组、不改 FIFO、不在本轮定 staleness 数值。 |
| I16 暂态失败没有自动重试 | 七个成员已完成，第八个遇到一次局部服务故障，整组可能丢弃。 | 09-09 用户批准 B-2 的窄例外：仅测试前镜像/新 grader 准备中的已识别可重试服务/传输故障，同工件最多追加一次评分；详见补充说明 §8。其它失败保持既定规则，不重新 rollout，不把换 epoch 后遇到同一 task 称作恢复重试。 |

## 2. 直接落实：当前执行链的未知异常不默认转 ABORTED

**既定原则：停止作业，保留原始异常和执行上下文，并继续清理；不默认转成成员 ABORTED。** 06 §2 第 1 条已经明确“不可归因/结构性损坏 = typed run-fatal,不补采”；附录 A 限定 ABORTED 来自已归因 task-local 故障。当前 generate/adapter 执行链落实该原则不需要重新拍板；不据此扩展为全仓任何 Python 异常都 fatal。候选仓库的测试 traceback、工具错误文本、已明确为可选的 telemetry 不属于此处未知执行故障。

### 具体原因

`generate.py` 当前对 finalize/deliver 阶段部分结构错误显式 fatal，但较早的 assemble/materialize/harness_run 仍可能进入宽泛兜底。兜底没有查清异常为什么发生，就按所在阶段生成 termination，再返回 ABORTED。`DefaultDataBuffer.put()` 在完整准入之前丢掉含 ABORTED 的组，后面严格的准入校验看不到这个错误。

例如我方 `_leaf_facts_fn` 因编程错误抛 `TypeError`，当前会变成 `missing + ABORTED`。若只在有分支的轨迹触发，简单轨迹仍不断被接受，已有 no-progress 也未必触发；训练可以继续，但输入分布已被代码 bug 筛选。

| 情形 | 建议处理 | 是否需要新决定 |
|---|---|---|
| 可信评分认定模型没修好，或工具返回正常失败 | 按已有规则评分和训练 | 不需要；不按错误文本中的 `TypeError` 等字样分类 |
| 我方身份、引用、token/logprob 等事实自相矛盾 | FATAL，停止并清理 | 已有 D1/A4，补齐漏网分支即可 |
| 已选配置确定缺失必需组件，例如正式入口缺 parser | 尽早明确报错；启动前能发现就启动前报 | 落实已有必需性，不新建“批准运行”闸门；具体 parser 支持由第 4 组与 B 处理 |
| 已归因且局限于单次 execution 的运行故障 | 本组不训练，继续处理后续组 | 沿用已批处置；未形成 present 才可 ABORTED，已形成 present 的评分失败保持 present 并 DROP |
| 第一组定义的墙钟保护触发 | 整组不训练；不能仅凭超时证明 infra 故障 | 第一组已定 |
| 当前执行链不可归因异常 | FATAL；定位后再决定是否纳入某个已知局部故障分支 | 06 §2 已定，本轮落实，不重问 |
| 已明确为可选的诊断写入失败 | 留下诊断，继续原样本处置 | 例如 `repair_signal_sink` 失败；不扩大成新的 fatal 面 |

worker/engine 整体死亡、身份错接、核心记录失败等全局故障不能因为表中有“局部运行故障”就降级。取消也应保留原始停止原因，不能统一视为程序 bug。

**代价：** 首批运行可能因一个后来证明可恢复的异常提前停止；定位、分类后可以缩小停机面。这是已有 fail-fast 原则的成本。未知异常丢组继续、靠次数阈值停止会重新打开掩盖内部错误的路径，本轮不建议推翻旧决定，也不另建逐 reason 熔断平台。

## 3. 已确认的改判：中间关停等待超时，后来清完，算不算成功

### 当前实现与旧合同

正常 dispose 路径是 miles 的 rollout `aclose()` 先取消并有界等待 worker/groups，随后 RH2 继续清理，再执行原 dispose 的其它关闭步骤。默认第一段等待为 60 秒；RH2 inflight 宽限/取消等待另有 30/150 秒；外层默认 900 秒只包住 owner-loop 的 aclose＋RH2 close，**不覆盖之后原 dispose 的 data_source/metric/eval/monitor 清理**。这些是当前配置事实，不是本轮建议的新数值；各项不等于每个容器串行耗时。若 fatal 已提前启动 RH2 close，等待可能重叠，不能把所有路径都画成严格串行。

第一段结束时的 unfinished 快照会构造 `shutdown_failure`，并传为 RH2 的 cause/external residue。最终 verdict 仍要求这个 failure 不存在，因此后续清完也不会自动恢复成功。`cleanup_ok` 本身也包含这项早期 failure；不能简单换读这个字段就声称已按最终清理判定。

旧缩时探针有两组对照：期限内完成可成功；第一段 10ms 到期、60ms 后任务完成清理，最终仍 `ok=false`。这是可达机制的本机证据，不是生产里正常退出必失败的频率证据。

### 推荐的新语义：纯中间等待超时留作诊断，成败看有界最终收口

例：训练与 checkpoint 正常完成，取消等待在 60 秒时尚有一个任务在清理，90 秒时后备清理将它彻底关闭。**若仍在总关停期限内，经现有 owner 确认任务/execution 已结束、应释放资源无残留、必要记录完整且没有其它致命错误，允许成功退出，保留中间超时事实。** 60/90 秒只解释行为，不冻结预算。

仍须非零退出的情形：训练本身失败；核心事实/记录损坏；真实 shutdown 操作失败；总期限到点仍未收口；任务或资源是否结束无法确认。**仅豁免明确的中间等候超时快照**，不是删除整个 `shutdown_failure` 对象：`aclose_raised`、`close_error`、`buffer_not_closed`、driver/worker 错误、现合同 evidence failure、原 dispose 错误都不随之消失。取消在途时 receipt 写失败可能仅作次生事实，不另抛 fatal，不能只查异常类型来判断关键记录完整。

**这不是“只看 trainer 完成就返回 0”**，也不把容器暂时查不到等同于所有后台任务都已结束。必须处理旧 unfinished 快照与最终状态的差别；在无法作出最终确认时保留失败。退出码一旦返回非零，不在作业结束后重写成成功。

**为何推荐：** 本项目没有要求某一个内部阶段必须在 60 秒内完成的服务承诺；只因中间等候到点就永久失败，会把安全完成的后备清理当成一次失败实验。保留总期限、真实失败与最终残留检查，能表达我们实际关心的可靠性。

**最有价值的替代：保持 B-6 当前语义。** 只要任一规定关停阶段未按期完成，作业即非零，即使后来清完。优点是无需改判据；代价是退出码同时表示“最终清理失败”和“曾经清理较慢”，读结果需要解释。这不会自动证明已写出的 checkpoint 无效。

此推荐改变 B-6 的一部分合同，已于 2026-09-09 获 owner 确认，待实施。不把所有证据写失败都顺带降级：核心训练/交付记录的 fatal 规则不变；哪些纯诊断报告可弱化若要调整，另列具体消费者。沿现有 owner 落实清晰覆盖范围的有界收口，不能把现有 900 秒冒充已覆盖全部 dispose；不新建 supervisor、恢复状态机或多份成功证明。

## 4. 丢组和重试：沿用已有决定，补足解释能力

首版继续完整组准入、丢弃本次 physical group、不立即重试。今后若损耗集中在确定的暂态环节，再讨论那个环节的有限重试；重跑冻结补丁的评分与重新采样模型不是同一件事，不能统一套一个 retry 参数。

现有 `drop_events.py` 已统计丢弃阶段、原因、task 分母与 staleness，不是“完全没有统计”。但 ABORTED 分支的事件原因目前只有 `aborted_member`，成员只有身份；底层 audit 的详细错误没有完整带到该汇总。轮数/token/耗时也不足以比较慢组与正常组。

建议复用事件与离线汇总，携带已有根因和已知的轮数、token、耗时；完整信息拿不到时记未知，不能造 0。不记录 prompt/private/patch 内容，不把诊断写失败变成新拒绝路径。汇总里的 attempts 是到达 buffer 终局事件的组数，不是所有已启动/仍在飞的组；比较分布时须与已有执行计数区分。

已批 no-progress 仍保留：不断丢组不能重置“多久没有拿到可训练组”的时钟。但它不能替代内部错误显式暴露，也不等同于第 3 组将讨论的有效梯度监控。数值不在本轮提前定。

## 5. 本轮选择与实施边界

| 已确认决定 | 首版方向 | 主要取舍 |
|---|---|---|
| 纯中间关停等待超时后的 verdict | 总期限内确认最终安全收口且无其它错误，可以成功；超时事实保留 | 修改 B-6，需要按最终状态核对旧快照；保持旧规则则实现更少但晚清理仍非零 |

实现分小批：先落实既有 I05 结构矛盾/不可归因异常分流与 I12 清理；I13 按 2026-09-09 已批范围接入。精确分支清单按产生错误的边界整理，不要求 owner 逐个 reason code 拍板。I15 完整组继续保留；I16 的最多一次同工件评分方向已获后续确认，具体允许失败阶段/类别表见补充说明 §8，未覆盖的重试仍按原 B-2。

验证复用旧缺 capture 引用/分支数不一致/未分类 TypeError/receipt ENOSPC/关停缩时探针，并补修后对应正反例。分类与时序可先本机验证；实际容器残留与目标 Ray/GPU 的生命周期按原定作业验证。当前没有实现变更，因此本轮不重复运行旧测试；不能把本机替身结果当作真实 Docker/GPU 验收。

## 6. 本轮核查记录

主审与复用的 Production Tracer / Falsifier 各自只读核对同一个错误/退出边界，未分裂为五轮全量审查。反证纠正了两个初稿范围：未知执行异常 fatal 已获旧计划批准，不应重问；900 秒不是完整 dispose 的全局期限。主审回读相应源码与 06 §2 后采纳。

关键源码：[早期异常兜底](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L3433)、[receipt 跳清理](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L3646)、[可选 telemetry 与核心记录分流](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L4492)、[aclose 失败构造](../../../../../reference/miles-rh2-integration/miles/utils/rh2_shutdown.py#L100)、[最终 verdict](../../../../../reference/miles-rh2-integration/miles/utils/rh2_shutdown.py#L295)、[原 dispose 后续步骤](../../../../../reference/miles-rh2-integration/miles/ray/rollout/rollout_manager.py#L187)、[drop 汇总](../../../../../rh2/src/repoharness2/adapters/miles/drop_events.py#L115)。

主仓库基线 `d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5`，本轮核对 rh2 无差异。证据沿用前轮主审复跑的 [failure_probes.py](../../miles_spike/external_infra_review_20260905/failure_probes.py) 与 [runtime_probe.py](../../miles_spike/external_infra_review_crosscheck_20260906/runtime_probe.py)，本轮只读，不宣称新测试通过。未运行 Docker/GPU，未提交推送。
