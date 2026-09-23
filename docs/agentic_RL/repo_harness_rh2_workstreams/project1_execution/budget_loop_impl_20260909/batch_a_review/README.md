# 预算闭环批 A：Codex 聚焦审查

日期：2026-09-09。基线：`297f1f59`，审查其上的未提交改动。首审为 3 个源文件、6 个测试文件；修后增加 `docker_sandbox.py`，共 4 个源文件、6 个测试文件。对象：[预算 Brief 的批 A](../README.md#批-ai05i12-旧规则落实先做后面三批的错误码依赖它)。首审证据见 [review_snapshot.json](review_snapshot.json)，修后证据见 [followup_snapshot.json](followup_snapshot.json)。

**当前结论：修后针对性复核通过，R1/R2 均已关闭，批 A 已实施范围没有未解决的阻塞 finding，可以收口并继续批 B。** 代码仍未提交。§1–5 保留首审原始事实，当前处置以 §6 为准；§6.3 另记一项不阻塞提交的既有诊断边界。

六项在作者交接时明确保留现状，本轮不把它们列成“漏实现”。本审查没有登记新的 owner 批准，也不把未实施的预算 B/C/D 当作已经验证。

## 1. R1｜driver 的 RuntimeError 包装仍会把未知错误送去补采（P1）

**位置与行为。** [bringup.py:397](../../../../../../rh2/src/repoharness2/adapters/slime/bringup.py#L397) 的 `except RuntimeError` 将异常统一转成 `harness_bootstrap_failed`。包裹范围从安装函数一直延伸到完整的 `ClaudeCodeHarness.run`，包含 `launch_and_wait`，不是只包含已识别的 Docker 命令失败。

**违反的规则。** 本批 I05 与 Brief `:36,42,47` 要求按实际来源区分已归因局部故障和未知错误。仅将异常类从 RuntimeError 改名为 SlimeBindingError，不能完成归因；事后版本错误的单独例外也不能使其它所有 RuntimeError 自动成为局部故障。

**独立复现。** 主审审读并重跑 [error_routing_probe.py](error_routing_probe.py)，使用真实 driver、真实 formal 编排和既有 CPU 夹具，只在故障来源处注入异常。结果如下：

| 来源 | 当前结果 | fatal 通知 | 清理 |
|---|---|---:|---|
| Docker exec 的局部失败替身 | `harness_bootstrap_failed` → ABORTED | 0 | 完成 |
| 安装函数内部未知 RuntimeError | **同样 ABORTED** | **0** | 完成 |
| 引导完成后运行函数内部未知 RuntimeError | **同样 ABORTED** | **0** | 完成 |
| 同一运行位置的 TypeError | `pre_finalize_failure_unclassified` FATAL | 1 | 完成 |
| typed `cc_version_mismatch` | `pre_finalize_failure_unclassified` FATAL | 1 | 完成 |

**影响与生产可达性。** 当前已启用的正式入口会调用这些方法；发生未知 RuntimeError 时，该包装将其归入表内局部故障。实际结果经 `canonicalize` 成为 miles ABORTED，随后 buffer 丢组、调用 unused handler。后面的严格准入无法再把它识别为内部错误。若只涉及部分任务，仍可能继续补采并选择性丢弃。标签为 `production_reachable`，依据是当前调用链加故障注入；不是已经观察到真实 CC 内部异常，也没有故障频率估计。

**建议修法与分期。** 批 A 提交前修。将局部失败类型建立在能证明来源的现有 Docker/引导操作边界上，driver 只转换这种明确类型或结果。未知 RuntimeError 继续向编排传播。不能改成按异常文本匹配，也不能仅缩短 try 后仍把整个安装函数的裸 RuntimeError 当局部失败。不需要通用异常分类平台，不要求修改 vendored slime。

**验收条件。** 两个未知 RuntimeError 反例均经真实 driver → 编排成为 FATAL：原始原因可诊断、已有通知器被调用、不返回 ABORTED、清理继续；明确局部运行故障仍可 ABORTED，CLI 配置错误仍 FATAL。现有新测试把假 driver 直接接到编排，证明了下游分流；新增驱动测试则只验证了统一包装，因此没有覆盖这个接缝。

## 2. R2｜receipt 失败后先进入清理等待，没有先通知停止（P1）

**位置与行为。** [generate.py:3653](../../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L3653) 捕获 receipt 写入失败后只记账，随后进入 `drop_session`、容器清理等 await；直到 `:3823–3833` 才抛 `finalization_receipt_write_failed`。这一 finally 尾部异常不会再经过同一 try 的 fatal except。

**违反的规则。** 核心持久化失败须停 run，同时继续清理。当前已有 `_notify_fatal_halt`（`:4832–4840`）正是为避免“等待清理推迟致命错误通知”而设计；其它编排 fatal 已在 cleanup 前调用它。本批将 receipt 失败从“跳过清理”改成“实际等待清理”，需要把这个接缝一并接上。

**独立复现。** 主审审读并重跑 [receipt_cleanup_probe.py](receipt_cleanup_probe.py) 的七个组合。使用真实 `RolloutOrchestrator.generate`、`LifecycleState.enter_execution` 与会话包装；Docker、持久化和停止通知回调使用替身。在 `drop_session` 暂停时观察到：

| 情况 | 已记录 receipt 失败 | 已发 fatal 通知 | 探针生命周期仍接受工作 |
|---|---:|---|---:|
| 只有 receipt 导致 fatal | 是 | **无** | **是** |
| 原本已有 fatal，随后 receipt 也失败 | 是 | 原始 fatal | 否 |

放开清理后，第一种最终仍正确抛 receipt fatal，但期间没有通知；第二种保持原始 fatal，不被 receipt 或清理错误覆盖。探针回调中的 `stop_intake` 用来观察通知是否发生，不冒充跑过完整部署关停或真实训练继续更新参数的实测。

**影响与生产可达性。** 正式任务解析会安装 lifecycle notifier，真实 notifier 会交给 BringupService 调度关停。receipt-only 失败时若清理较慢，服务要等异常向上传播才知道核心持久化已经失败，在等待窗口仍可能继续接收其它执行；本次失败样本自身不会被提前返回。该窗口在当前路径可达，并被本批新增的清理 await 扩大；实际发生频率未测。不是要求第一次清理超时都 fatal，也不重开 I13。

**建议修法与分期。** 批 A 提交前修。在非兼容模式确认 receipt 失败后、首次 cleanup await 前，经已有 notifier 通知 fatal，再继续当前清理。保留已经在途的原始 fatal/取消，不以次生 receipt 错误覆盖首因；最终对外异常规则保持。复用当前通知器，不增加后台 supervisor 或新状态机。

**验收条件。** 把 drop/rm 暂停时，receipt-only 情况已经收到停机通知；放开后 cleanup 继续且仍抛 receipt fatal。原 fatal 与 receipt、drop/rm、audit 同时失败时，首因保持；receipt 失败不释放 poison，无 receipt 不追加 cleanup record，成功移除不进隔离队列，移除失败才登记残留。上述后半部分的现有维护测试和本轮七案探针已经通过，不必重建整套清理测试。

## 3. 已验证的正确部分与一个可简化项

- **编排分流有效**：未映射 typed 码与 TypeError 等异常在正式模式下进入 fatal，不产 missing Outcome；已 finalize 的异常仍由原 post-finalize 通道处理，取消仍独立传播。定向测试覆盖这些分支。
- **两条 capture 矛盾有效**：维护测试通过真实树事实条数错配与 ghost capture 引用触发守卫，确认变为 FATAL，并执行清理；不是只验证集合里的名字。
- **receipt 失败清理有效**：容器未提前释放、已经提前释放、drop 失败、rm 非零、rm 抛异常、原 fatal 与多个次生错误共存的七案均守住当前清理与首因规则。R2 只要求补提前通知，不要求撤回 I12。
- **兼容路径保留**：`s1_compat` 的异常进入原收口，receipt 兼容处理不随正式链扩大；六项待确认仍按作者交接范围保留。未修改训练 loss、capture token、预算或依赖版本。
- **可简化，不阻塞**：`STRUCTURAL_CONTRADICTION_CODES` 只有文档/测试用途，运行判定不消费它。可把两码留在参数化测试中，删除该公开常量及“集合与表不相交”的自校验测试，保留真实装配反例即可。这样少维护一份声明，不降低行为验证。

## 4. 六项待确认的范围与后续切片

仍支持之前对四项的限定范围建议。新增 digest/血缘两项也应将“成功读取但与冻结事实矛盾”改为 FATAL；但**不能按 Brief `:125` 只删除整个错误码条目就算完成**：当前 `generate.py:4170–4178` 将第二次镜像 inspect 失败与真实 digest 不符合并到同一码；血缘的 `evaluate_probe` 也同时接受命令失败和内容不符。切换时应在抛出点区分已识别局部查询失败与事实矛盾，避免把临时查询故障一并升级。这是既有分类原则的落实约束，不是本轮批 A 已实施部分的新阻塞项。

本轮没有把用户询问或 Claude 的提议记作新批准；没有开启这六项。批 A 的两条修复不依赖重新决定它们。预算 B/C/D 的新实现另按各切片核对，特别是新加入的“等待在飞请求后拒绝 N+1”尚未由本次实现审查验证，不能从批 A 结果推导该并发方案已通过。

## 5. 实际验证与停止条件

主审在 integration miles 基座运行六个被修改测试文件：

```bash
cd rh2
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run --no-sync pytest -q \
  tests/adapters/test_w1b_termination_facts_producer.py \
  tests/adapters/test_w1b_delivery_face.py \
  tests/adapters/test_b5_finalization.py \
  tests/adapters/test_f2_2_capability.py \
  tests/adapters_miles/test_w1b_prepared_chain.py \
  tests/adapters_miles/test_batch_a_failure_routing.py
```

结果：**90 passed in 5.92s，退出码 0**。9 个被审源码/测试文件的 ruff 通过。独立重跑两份探针均退出 0：错误分流 5 案，receipt 清理 7 案；其中错误行为按原样展示，退出 0 不表示修复已通过。没有再次全量运行作者所报的 1787/310，没有真实 Docker、CC、模型 API 或 GPU 作业。

补充核查：[错误来源与 miles 消费](error_routing_review.md)、[receipt 清理与通知](receipt_cleanup_review.md)。前者由 Production Tracer 核当前调用链，后者由 Falsifier 检查最小反例与清理组合；主审独立回读代码、重跑探针并裁定，未按角色投票。

适用维度：A/B/D/E/F/G/H/I/L/M（失败/并发、训练分布、所有权、测试接缝、既有决定、真实消费、原因来源、分期、活性、诊断）；J/K 限于两个窄修与删除冗余声明；C 无新挡板，N 无依赖变更。不将本次扩大为全链或环境数据审计。

**停止条件**：R1/R2 修复并补真实接缝回归后，只针对这两条与必要回归复核，即可结束批 A 的实现审查；可同时准备批 B，不要求另写完整方案包。可简化项和六项待确认分开登记，不混作“必须全部决策完才能继续”。本轮仅新增审查工件和更新共享留言板，没有修改业务源码、维护测试、执行提交或推送。

## 6. 修后针对性复核（2026-09-09）

### 6.1 R1/R2 的关闭依据

- **R1 已关闭。** `DockerSandbox.exec(check=True)` 与 `write_file` 在真实非零结果处产生 `SandboxExecError`；driver 只转换该类型。底层 `_run` 自身或引导完成后的未知 RuntimeError 均透传为 run-fatal，不产 ABORTED。主审重跑从 `_run` 注入结果的新八案探针：两种操作的普通非零 / 124 均 ABORTED、通知数 0；未知异常均 FATAL、通知数 1，清理完成。`exec(check=False)` 返回约定不变。详见 [R1 复核](error_routing_followup.md) 与 [实际输出](followup_error_routing_result.jsonl)。旧探针直接让 `exec` 抛裸 RuntimeError，绕过了现在产生 typed 错误的源头，因此那一案修后 FATAL 不构成回归。
- **R2 已关闭。** receipt-only 失败在第一个清理 await 之前通知，暂停 drop 时生命周期已停止接收；放行后仍清理并抛已通知的 receipt fatal。原 fatal 与 receipt / drop / rm / audit 多重失败组合保持原首因。主审重跑原七案探针，poison、隔离队列、提前释放、无 receipt 不追加 cleanup record 均未回归。termination 事实错误的提前通知也由维护测试确认。详见 [R2 复核及取消/兼容补测](receipt_cleanup_followup.md) 与 [实际输出](followup_receipt_cleanup_result.json)。
- **可简化项已落实。** 已删除 `STRUCTURAL_CONTRADICTION_CODES`；两个真实装配反例仍保留，不用另一份集合自证。

### 6.2 主审实际运行与边界

```bash
cd rh2
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run --no-sync pytest -q \
  tests/adapters_miles/test_batch_a_failure_routing.py \
  tests/adapters/test_b5_finalization.py \
  tests/adapters/test_w1b_termination_facts_producer.py
uv run --no-sync python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/batch_a_review/error_routing_source_followup_probe.py
uv run --no-sync python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/batch_a_review/receipt_cleanup_probe.py
```

结果：**45 passed in 1.46s**；两个独立探针 **8 + 7 案均退出 0**；本批 10 个源码/测试文件 ruff 通过。测试只重跑修后发生变化的三个维护测试文件，其余三个与首审相同。摘要及命令范围保存在 [followup_snapshot.json](followup_snapshot.json)，原始输出见 [测试](followup_tests.txt)、[ruff](followup_ruff.txt)。作者所报全量 **1796 passed / 310 skipped** 本轮没有再次运行。

主审已回读两个独立角色的结果并自行核对源码、重跑上述测试和探针；复核前后 10 个文件摘要完全相同，没有把并行开展的批 B 代码混入结论。CPU 替身证明异常路由、通知顺序和清理控制流，不代表真实 Docker 超时回收、真实 CC 或 GPU 停机已经实测。

### 6.3 非阻塞：termination 事实错误与 audit sink 同时失败的诊断边界

`generate.py:3817–3840` 的 sink 异常保护只检查 receipt 失败或已有在途异常。主审用真实 `_formal_chain`，同时让 `termination_facts_payload` 抛 `TerminationFactsError`、`_audit_sink` 抛 `OSError`，得到：

```json
{"notified_codes": ["termination_facts_underivable"], "raised_code": "execution_audit_write_failed", "raised_same_object": false}
```

因此不能无条件声称 termination 分支尾部总是抛已通知的同一对象；这一结论要求后续 audit sink 没有再次失败。sink 的尾部优先级在修改前已经存在。修后该组合仍提前通知、完成清理、以 FATAL 退出，`BringupService._on_run_fatal` 保留首次通知的关停首因；它不会重新变成 ABORTED 或推迟 R2 的停止通知。这里仅记录两处诊断原因可能不同的既有边界，不重开 R2，也不要求再扩大修复轮。后续若整理错误诊断，可让 sink 的首因保护一并识别 `pending_tail_fatal`。

### 6.4 收口与后续

本批的实现审查到此收口，可按既有节奏进入批 B；不需要再补一轮全量审查。Brief §6 的六项仍保留现状、未新增 owner 批准，也未纳入“已实施通过”。digest / 血缘切换时拆分查询失败与内容不符的约束继续有效。审查通过不等于预算 B/C/D 或所有 I05 分类已经完成。

本轮只更新复核工件、Brief 状态和 `infra.md` 留言，没有修改业务源码或维护测试，没有提交、推送或发起真实训练。
