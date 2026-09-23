# B/C/D 联合审查：Falsifier / Simplifier

审查基线：`04f599f82d5eef4a808fab001f295896ebed5efa`；本子审主责批 C `34531b74` 的 turn 预算包装与消息→轨迹→训练准入接缝。已读 `handover_20260909.md` 和 Brief 批 C/D；交叉回读了主审与 Production Tracer 的指定探针。本次没有修改源码、维护测试、旧工件、Brief、infra 或 git，没有运行真实 Docker、CC、模型 API 或 GPU。

**独立新增一个 P1：cap 守卫在读取请求体之前检查计数，不能覆盖同一 session 的并发请求体交错。第 N+1 次可在第 N 次仍生成时发出 403 和预算事件，导致本应保留的正常 turn 截断变成缺员并整组补采。** 已用真实 HTTP、生产 capture/proxy、真实 formal 编排与 miles buffer 连通验证；不只是单测响应码。既有 poison/缺员准入在该反例里正确挡住了不完整数据，问题是过早拒绝制造了这种不完整。

## 1. C-F1：读取 body 前的计数检查留下并发窗口（P1，批 C 必修）

### 行为、位置和违反的不变量

`capture_wire.py:944–954` 的 guard 在进入下游 handler 前只检查一次 `turn_budget_reached`，只有此刻已经到 N 才等待 inflight 归零。实际计数位于生产 vendored `rh2/src/slime/agent/adapters/common.py:325–333`：先 `await request.json()`，再同步调用 `_check_turn_cap`。`capture_wire.py:1076–1097` 在该同步方法拒绝时立即写预算事实、通知编排并返回 403。

因此，当前已接纳 N−1 次时，第 N 次与第 N+1 次若都先到达 HTTP 头、body 尚未收全，两者看到的预算都未满，都会越过 guard。第 N 次补齐 body 后进入生成；第 N+1 次随后补齐 body，直接在 `_check_turn_cap` 被拒绝，已经没有等待前一请求交付的步骤。

违反 Brief C 第 2–4 项的边界：预算拒绝与开始收口不能提前切断已获行动机会的在飞请求。只延迟 403 而保留提前发出的预算通知也不够，因为编排会据通知启动 30 秒退出宽限。

### 生产可达性与影响边界

生产条件是同一 SID 允许并发请求，且请求体读取发生交错。这是当前 vendored app、request 级 capture 所有权明确支持的并发形态，包括同 session 的子 agent 请求；无需修改服务配置或给数据注入未知字段。探针用 cap=1 缩短准备，等价于默认 cap=25 时前 24 次已经结束、最后两次发生交错；没有把预算数值改成 owner 决策。

实测的丢轨迹后果包含一个明确条件：客户端收到不可重试 403 后关闭同一运行的在飞连接。真实 CC 二进制对此响应的退出行为仍未验证，不声称已经跑过真实 CC。但过早的预算事件本身已经确定；即使客户端暂不退出，当前编排也会提前启动强停宽限，仍不能把此问题降为纯文案或观测错误。

这是正常截断样本被错误丢弃的训练分布问题，发生比例未测。没有观察到额外模型请求越过 cap，也没有观察到错误 token 或缺失 capture 被放进训练。

### 独立复现与对照

`cap_body_race_probe.py` 不替换 `_run_turn`、`_check_turn_cap`、`_respond`、record_turn、capture hook 或 proxy。请求体通过真实本机 aiohttp 连接分两块发送；上游 SGLang 请求仅用显式内存替身阻塞/返回。测试 server 使用生产相同的 `handler_cancellation=True`。

| 案例 | 第 N 次生成未释放时 | 最终真实捕获/轨迹结果 |
| --- | --- | --- |
| 顺序对照，第 N 次已进入生成再发 N+1 | 没有 403，没有预算通知 | 200→403；1 个 complete capture、1 条真实叶、2 个 response token、1 个身份绑定；无 poison |
| 两个分块 body 先同时过 guard，客户端继续等待 | 403 已返回；预算通知时 guard inflight=2，capture=0、tree turn=0 | 放开生成后仍能得到 1 个 complete capture 和叶；说明提前拒绝本身不必然污染数据 |
| 同样的 body 交错，收到 403 后关闭在飞连接 | 同样提前 403/通知 | 真实 handler 取消→`client_cancelled` poison→1 次 abort；capture=0、tree turn=0 |

`cap_to_admission_probe.py` 把同一请求动作继续接到真实准入面：prepared 任务派发→`Rh2MilesGenerateFn`→formal `RolloutOrchestrator`→实际 `make_per_rollout_adapter`→真实 HTTP/proxy/capture/轨迹树→`bringup_leaf_facts`→canonicalize→真实 `DefaultDataBuffer.put/get`→训练数据转换。Docker IO、屏障与 grader 使用已有 CPU fixture；没有用 MockSessionAdapter 喂轨迹，也没有手写预算快照或 Outcome。

| 全链案例 | 编排结果 | 准入/转换结果 |
| --- | --- | --- |
| 两成员均按顺序触发 cap | 两者 `present_truncated/max_turns_exhausted`，各 1 个真实 capture，均被评分 | buffer 中 1 组；`raw_reward=[1.0,0.0]`，各 2 个训练 token；reward 来自 grader fixture 报告 |
| 仅第一成员换成上述竞态并退出 | 第一成员 `missing/api_failure/session_poisoned_during_execution`、`remove_sample=True`，未评分；第二成员仍正常截断并评分 | buffer 中 0 组，1 组进入既有 unused/recycle 路径；没有调用该组的训练转换 |

### 最小修订和验收

把等待放在实际请求体已经可读、与 vendored cap 判定相邻的正确边界；拒绝响应和使编排开始退出宽限的通知都必须遵守该边界。继续让 vendored counter 是唯一计数来源，并只等待真正已接纳的请求完成，不能把等待被拒的请求自身也算进“必须归零”的集合而死锁。可复用已有请求/inflight 所有权，没必要新增整个 session 状态平台。

不建议用“整个 session 一次只执行一个模型请求”的锁绕过此窗口：那会改变已经支持的并发形态与吞吐/采样分布。也不应通过延长宽限或放宽 poison 来容忍提前截断。若选择提前读 body，要留意当前 capability 重写通过 `request.clone` 完成，不能在已读 body 后盲目 clone；验收应覆盖真实入口而不是只测新 helper。

窄验收至少保留：① 当前顺序对照；② N−1 时两份 body 同时越过旧守卫的反例；③ 多个待拒请求与最后已接纳请求并发，证明不相互等待死锁；④ 等待期间 poison/revoke/外层取消仍按既有边界拒绝，不能因 cap 豁免；⑤ 真实 capture/叶/准入的 KEEP 对照与真实 deadline 的 DROP 对照。无需改 §6 六项、owner_cancelled 或 agent_violation 的未定处置。

## 2. 已反证或限定的其他 C 判断

- **不是计数器竞争导致多采样**：计数仍在同一 loop 的同步 `_check_turn_cap` 内，counter 的增量与检查之间没有 await。探针各次只发出了 1 个上游模型请求，N+1 没有渲染/采样。不需要新建第二套配额计数。
- **cap 本身不 poison/revoke**：包装只记事实并返回拒绝；顺序全链证明真正的最后一轮能完整 stage→flush→commit→身份绑定，并按注入策略进入训练。不能把全部 403 都说成会丢轨迹。
- **认证与 REVOKE**：guard 等待之后重新读取 known、capability required、poison、revoked（`capture_wire.py:955–985`），认证与 inflight enter 之间仍无 await。静态核对未发现新权限绕过。等待发生在认证前可能延后拒绝，但这不是本反例的授权缺口，未扩成新的安全 finding。
- **失败优先级确有防线**：真实竞态触发 poison 后，编排在 `generate.py:2864–2870` 或 drain 的 `4750–4784` 将其归缺员，cap 没把它改为 KEEP；后面的 no-capture 守卫仍在。C-F1 的修复应保护在飞交付，不能删掉这些防线来让测试“重新 KEEP”。
- **维护测试的覆盖边界**：`test_budget_loop.py` 的真实 app 测试在第 N 次已生成 0.05 秒后才发送 N+1，并以 canned SGLang 返回时刻代表交付；它能测顺序，但不能覆盖 body await 窗口。另一个 buffer KEEP 测试使用 FakeTurnBudget 与喂好的 mock 轨迹，验证消费侧，不能单独证明真实消息生产侧。新增探针专门补这两个接缝，没有重跑全量测试。

## 3. 主审/Tracer finding 的交叉反证

以下是回读其脚本、结果和真实源码后的判断，不算本子审独立重跑的动态结果。

### C 停止跨越墙钟与停止调用无界

支持主审 `stop_deadline_probe.py` 的区分：`generate.py:3792–3803` 只在强停前检查剩余，899.5 开始停止、901 才实际生效时仍返回 -2、产出 max_turns/KEEP；这是“仍在执行时已经过墙”的已批 DROP 语义缺口。对照“899.5 已实际停止，901 才得到确认”应继续保持 KEEP，不能仅以 `remaining_at_harness_exit<0` 修复。

最小闭环要让期限持续约束尚未停止的执行，并把实际停止事实与后续确认/清理分开。应复用现有 stop 结果和同一时钟；如果只知道宿主发出 kill 或收到回包的时刻，要如实说明跨墙是否可判明，不能拿“已经发命令”冒充停止，也不能把晚确认补造成实际 hard wall。

无界调用也成立：`execution_scope.py:37–51` 的循环只限制查询次数，kill/count 的 `workspace.run_bash` 都可长期 await；新 `generate.py:3754–3765` 入口没有对整个停止动作加墙钟上界。主审挂起案在过墙后仍 pending、drain=0、halt=0；这是当前 C 路径问题，不用扩大成全 shutdown 审查。turn stop 期间父任务取消后仍遗留 harness task 的结果也应在这个新 await 的所有权修正中闭合。

### D-2 最终收口的三项

1. **rm/inspect/kill 无独立期限：支持。** `manager.py:1468–1482` 都直接 await runner，没有使用 `cleanup_timeout_seconds`。Tracer 让三种 IO 各自挂起，配置 1 秒、观察 1.051 秒后生成与 grading worker 仍在，halt=0。有限动作次数不能反证有限时间；应在现有最终收口路径补上有界预算和未确认结果，不必重写 grader/队列平台。
2. **daemon socket 不存在误判为容器已不存在：支持。** `manager.py:1455–1458` 用任意 `no such` / `not found` 文本判 absent；真实 Docker 连接错误中的 `connect: no such file or directory` 也命中。Tracer 案实际返回正常样本、无 halt、grader 记录仍未移除。最小修法是只认可可归属到目标容器不存在的已知响应；daemon/传输/无法解析状态保留 unknown，不能扩大字符串匹配。未知最终状态应走 D-2 已批 fatal，不是新的 owner 决策。
3. **提交者取消后丢失 scope fatal（P2）：结构与路径支持，影响表述需限定。** `queue.py:203` 的 submit 直接 await item.future，取消会取消该 future；worker 捕获 `GradingScopeTerminationError` 时 `225–226` 因 future.done 不再交付异常。Tracer 的真实 manager→queue→generate 案显示 worker 仍活着，终止失败却无通知。它证明了“当前通知只依赖原提交者仍在等待”的缺口；没有证明真实生产某次取消后训练仍继续更新参数。若生产取消已经处于 run-halt/关停，应保留这一对照。最小修法是让 D-2 已知 scope-fatal 通过既有生命周期 notifier 独立通知，原调用者的 CancelledError 仍保留；不需要让所有评分异常都 fatal，也不涉及 I13 中间等待超时后已安全结束的例外。

## 4. 验证与范围结束

两个新增脚本最终均退出 0：`cap_body_race_probe.py` 的 3 个 HTTP/capture 案例；`cap_to_admission_probe.py` 的 2 个真实准入组案例。所有关键结果都有断言。第一次构造独立 hook 时曾把含 `#` 的 paid 当作 trajectory_id，触发探针自身 ArtifactRef 格式校验；已改为符合真实入口形状的稳定 trajectory_id 再运行，未改业务源码或维护测试。

未复跑主审/Tracer 的探针与全量维护测试。生产输入、代理、capture、轨迹和准入的真实范围在上文逐项列出，Docker/模型/评分/屏障替身的边界也已列出。本报告不决定预算值、子 agent 开关、§6 六项、owner_cancelled/agent_violation，也不调查未来 token/context producer、I13/I16 或全 shutdown。C 已有可复现反例及必要回归，本子审到此收口。
