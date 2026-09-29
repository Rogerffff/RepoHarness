# 批 B 首次审查：独立反证与最小修法

基线：`6bb5ffe4db4b7b7a3f9e28b3ab39000640cb99f8`；审查的是批 B 未提交改动，文件版本绑定同目录 `review_snapshot.json`。范围是 Owner Brief 批 B 第 1–7 项、proxy 排队/期限/取消接缝、实际驱动的引导归因；按主审请求静态交叉复核了 materialize 的两个资源问题。没有修改业务源码、维护测试、主文档或 git，没有运行真实 Docker、CC、模型 API 或 GPU。

**结论：支持主审保留两个 P1 阻塞项：准备基线阶段缺少强制期限，以及 materialize 取消后的真实资源回收未闭合。** 独立反证未能把这两项降为“只写残余风险”：它们都能由批 B 新增的自身 deadline 触发，且不依赖未来批 C。没有发现 proxy 新额度获取逻辑泄漏名额；bootstrap 事实与整数截断归因问题应合并成一个 P2，不上升为已证明的训练错误。

## 1. 已验证的闭环与测试边界

| 核对点 | 证据与判断 |
| --- | --- |
| 正式链传同一个绝对期限 | `generate.py:2627,2800` 算出并传入期限，`bringup.py:749–771` 经 per-rollout adapter 注册，`capture_wire.py:294–327,382–398,1172` 保存并向真实 `proxy.call` 传递。编排与 proxy 的生产默认时钟都是同进程 `time.monotonic`；跨线程/loop 不需要另起表或换算。启动代码已撤掉正式链的首调懒起表。 |
| 信号量排队计入期限 | `async_worker.py:745–829` 等待额度期间按剩余时间等待；获取后重算剩余与本次超时。独立探针在额度持续占用时约 0.036 秒终止，没有调用 send，poison 为 `episode_deadline_exhausted`。 |
| 获取/取消竞态 | 真实 `_ResourceLease` + 新 `_send`，50 案（取消先到 25、获取先完成 25）全部归还额度，最终 `in_use=0`、信号量值为 1。没有证据支持重写这段 helper 或新增额度状态机。 |
| 外层取消区别于自身 deadline | 真实 `proxy.call` 在排队时被取消，向外仍为 `CancelledError`，poison 为 `client_cancelled`，额度恢复。新 typed 分支 `async_worker.py:965–974` 让 `_send` 的 deadline 原因不再被通用更新窗口归因覆盖。 |
| 单次 attempt timeout | `async_worker.py:978–993` 只有超时且观察到 episode 剩余不大于零才改成 deadline；期限仍充足时保留旧 interruption 分支。维护测试 `test_attempt_timeout_before_deadline_is_still_interruption_not_hard_wall` 给出了该对照；本审查只读该维护测试，未重复主审的测试运行。 |
| 双 loop 接缝 | 独立探针在一个 loop 中注册 deadline，首调前先耗去一部分时间，再在线程内的新 loop 上跑真实 proxy；读取值完全相同，约在原期限后 0.0012 秒结束。该探针验证 registry→proxy 的真实时钟接缝，没有声称执行过真实 HTTP/模型链。 |
| 编排的 poison 映射 | `generate.py:2834–2864` 仅把 `episode_deadline_exhausted` 映为 hard wall；其他 poison 保持原分流。`test_budget_deadline.py` 的两个对照是直接注入 poison，证明消费侧，不能独自证明真实模型排队至编排取消的全链。结合以上实际 proxy 探针和静态注册/调用链，当前没有发现该接线丢失。 |

## 2. 支持阻塞的两个问题

### R1：基线准备阶段仍能越过期限而不结束（P1）

- **行为与位置**：`generate.py:2712–2752` 只包住 `_materialize_rollout_sandbox`，后面的 HEAD 读取和 `generate_baseline_manifest` 两个 await 在 wrapper 外。真正剩余量检查直到 `2756` 才发生。
- **违反约束**：Brief B 第 1–2 项要求从资源占用起表，并强制限制准备阶段；“阶段跑完后再发现过期”不满足这个边界。
- **生产可达条件**：正式模式已经取得 rollout 容器后，基线 HEAD/文件普查的 Docker 调用长期不返回。此时不是模型正常执行，容器与 miles 并发槽却仍占用。
- **证据与影响**：静态接线与主审 `orchestrator_probe.py` 的挂起案一致；本子审未重复该探针。不能用后面的启动前检查反证，因为程序到不了那里。也不能由批 C 的模型停止顺序修复准备阶段 await。
- **分期与最小修法**：批 B 必修。把现有 baseline 准备段放入同一 deadline wrapper，继续使用已经持有的 sandbox/lease 与 finally 清理；不另起相对预算，不新建任务状态平台。
- **窄验收**：分别让 HEAD 读取与 census 内部 await 挂起，证明期限会取消它们、不开 harness、产生既有 hard-wall missing/DROP 事实、原容器与网络照常清理；外层取消仍保留首因。

### R2：自身 deadline 触发的 materialize 取消未覆盖真实 runner 与完整网络获取路径（P1）

- **行为与位置**：`generate.py` 导入并默认使用 `grading.manager.run_docker`；`manager.py:95–111` 在 `proc.communicate` 被取消时没有 kill/wait。批 B 修的是 `docker_sandbox.py:42–61`，那是驱动侧另一条通道。`generate.py:4169` 的“宿主 CLI 已被 _run 杀掉”注释不能作为真实默认通道的证据。
- **另一段同所有权缺口**：`generate.py:4158` 的网络创建/relay 接入发生在 materialize 两个取消保护块之前；`sandbox_profile.py:746–756` 已 allocate 子网后 await create，`generate.py:4379–4382` 已登记网络后 await connect。两者的取消都绕过已有 teardown。
- **生产可达条件**：正式 profile 路径运行时，deadline 在 Docker 创建或连接私网的 await 上到点；daemon 是否已经创建网络是待确认结果，并非必须假设“创建成功且响应丢失”才会泄漏池槽。connect 案甚至已经拥有明确网络记录。
- **证据与影响**：静态回读了 Production Tracer 的 `production_resource_probe.py` 与结果，没有重复运行。真实默认 runner 的进程替身记录 kill/wait 为 `0/0`，驱动 runner 对照为 `1/1`。真实 formal 编排加 Docker IO 替身的 create/connect 两案都留下 1 个网络和 1 个池槽；connect 还留下 1 个已登记 mapping，而执行已返回 ABORTED、`cleanup_completed`、零 cleanup failure。
- **为何不能只登记残余风险**：Brief 中的声明只覆盖“创建结果未知”的窄表述，实际遗漏也覆盖已登记的 connect 阶段。shutdown label 清扫在后续运行中不会被执行；即使执行也没有归还当前 live pool 的槽位。正常补采会继续累积资源，最终可能耗尽地址池。此处的回收要求来自批 B 第 3 项，不能转交批 C 的 CC 停止顺序。
- **分期与最小修法**：批 B 必修。给真正的默认 runner 接上取消时 kill/wait；在现有网络获取函数持有名字/子网的位置处理取消，按既有 teardown 证明确实删除后归还槽位，connect 取消复用已登记网络的回收。无需改整个 shutdown 或引入新资源平台；daemon 操作已发送但结果未确认时仍须按名字核对，不能把 kill CLI 当成 daemon 回滚。
- **窄验收**：沿现有生产 runner 的进程替身证明取消会 kill/wait；分别在 create 与 connect await 取消，证明网络、mapping、pool 槽位都闭合。删除失败必须进入既有 cleanup failure/隔离记录，不得报无失败的清理完成。

## 3. 非阻塞问题与严重度反证

### R3：bootstrap 的启动事实与缩短超时归因不准确（P2）

`bringup.py:371–421` 在安装前没有初始化 `launched=False`，在进入 `ClaudeCodeHarness().run` 前又提前置为 True。真实 vendored `harness/common.py:97–105` 此后仍做 ensure_user、write_config；`sandbox.py:109–126` 还会写 launcher 和发送 spawn。故安装时取消得到 None，配置阶段取消可能得到 True，都不能严格代表“CC 已启动”。主审已经复现安装取消落 `harness_outer` 并继续 drain/装配。

另 `bounded()` 先 `int(min(cap, remaining))`，而异常归 hard wall 要求剩余不大于零。独立探针给真实驱动 2 秒相对预算，跳过安装，按驱动实际给出的 `timeout=1.0` 等满后返回 124，实际得到 `harness_bootstrap_failed`、空 launch facts。维护测试只用 1 秒预算，`max(1, ...)` 恰好避免了这种小数余量，未覆盖一般的 floor 分支。

生产可达条件是安装/用户准备/配置阶段被自身期限取消，或 driver 的收缩超时先于绝对期限不足一秒触发。它们影响 `hit_by`、bootstrap 统计与不必要的无 capture 装配；当前证据中仍然是 hard-wall 或已归因缺员并 DROP，不能据此声称样本错误进训练。

最小修法是把事实写在能够证明的真实启动边界，并区分“尚未发起 spawn”与“spawn 已发起但结果未知”；只在入口补 False 还不够，提前置 True 也要收紧。可以沿现有 driver/contextvar 的少量接点完成，不需要新平台。驱动步骤 timeout 不必跟着 vendored 整数参数一起向下取整；也可保留阶段超时来源，准确区分原有 cap 与 episode 收缩。验收应覆盖安装、write_config、spawn 前/返回未确认、带小数余量的超时，而不是给所有 -1 都强行认定“从未启动”。

### 观测与既有边界（不新增阻塞）

- **排队耗时遗漏**：`async_worker.py:768–770` 的 `_note_queue_wait` 只在 acquire 正常返回后执行。独立探针排队约 0.0158 秒后外层取消，实际统计仍为 0。这不漏发/多发请求、不丢额度，但使预算调参的观测低估。把记录放在该 await 的 finally 即可，注意只记一次。
- **新增热状态未回收**：`queue_wait_seconds` 按 paid 累积；`ack_attempts` 只移除旧 attempt ledger（`async_worker.py:662–669`），没有清这个 map。静态证据足以说明随执行数增长，但未测得内存故障，不提高严重度。最小做法是在已有审计持久化成功后的 ack 一起释放，而非另建清扫器。
- **旧 ACTIVE/版本等待归因**：独立探针在 ACTIVE 等待中耗尽 episode 时仍得到 `engine_not_active_before_send`；`_wait_version_advance` 相同截止条件仍叫 `version_did_not_advance`。这两个原因已有于基线，Brief 明说前者不改；都有缺员处置，真实编排外层 deadline 还可能先到。本审查不据此新增训练错误或本批阻塞。
- **取消收口吞异常**：`_settle_cancelled_stage` 会记录而吞掉 Exception。主审用取消 handler 注入 Fatal 的组合证明了该结构，但尚未提供生产默认 handler 天然产生该 Fatal 的证据；不把条件性组合升级为生产 bug。若需要修正，保留已知 fatal 首因即可，不应借此重开 shutdown 审查。
- **批 C 分期仍成立**：到期后先停止 CC，再 drain 的顺序已明确归 C。本审查没有拿“CC 容器进程尚待后续屏障/清理”再造一个 B 阻塞。

## 4. 验证记录与结束范围

本子审新增并运行了同目录 `queue_deadline_probe.py`：最终退出码 0，共 6 组观测；其中额度取消竞态为 50 案，全部保持容量守恒。初次运行暴露了探针自身窗口 fixture 的非法组合，修正为实际契约允许的 ACTIVE/PAUSING 后重跑完成；未改维护测试 oracle。脚本故意报告已确认的诊断缺口，退出码 0 不等于“上述缺口已经修好”。

没有重复全量或维护测试，没有重新跑主审与 tracer 的探针。R1/R2 的动态结果明确来自其证据产物，本子审完成独立源码与测试替身可达性核对。报告交付后停止于批 B，不调查未来 deadline 平台、I13/I16 或全 shutdown；之后新增源码改动须另行复核。
