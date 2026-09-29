# 预算 B/C/D 联合聚焦审查

日期：2026-09-09。基线：`6bb5ffe4` 之后的四个实施提交，审查 HEAD 固定为 `04f599f82d5eef4a808fab001f295896ebed5efa`。

**结论：B 的旧问题修复通过，D-1 处置注入通过；C、D-2 尚不能验收。确认四项 P1，另有一项限定于取消/关停接缝的 P2。** 本轮是 B 的针对性复核、C/D 的首次实现审查及必要连接验证，不是重开 B 全审，也不代替正式训练前的总验收。

| 切片 | 提交 | 本轮判断 |
| --- | --- | --- |
| A：未归因异常 / receipt 清理 | `6bb5ffe4` | 沿用此前通过结论；只在相邻回归中验证，没有重开审查 |
| B：统一 episode 期限及修复 | `510c9b23` | 旧 R1、R2 两项 P1 关闭；旧 R3（P2）与相关观测修复通过 |
| D-1：处置注入 | `756b8fd6` | 通过；turn 截断 KEEP、hard wall DROP 能进入真实 buffer |
| C：turn 预算及强制停止 | `34531b74` | 待修本轮 R1/R2/R3 |
| D-2：grader 停止收口 | `5c8fa4f7` | 待修本轮 R2/R4；R5 为 P2，明确回应，不另加阻塞轮 |
| 交接文档 | `04f599f8` | 需按本报告更新状态；作者的全量测试与独立审查结果分开记录 |

主审重跑维护测试 **243 passed、0 skipped、0 xfailed**（153 项切片测试＋90 项准入/队列接缝测试），25 个变更 Python 文件的 ruff 通过；六份独立 CPU 探针均 exit 0。探针中的部分断言故意确认当前缺陷，**exit 0 不表示实现已通过审查**。作者报告的 1839 passed / 310 skipped 未在本轮重跑，不能当作主审的独立全量结果。

`rh2` 已跟踪源码/测试与 HEAD 一致；仓库其他共享文档、参考目录仍有既有改动，不能笼统说整个工作树干净。没有修改业务源码、维护测试、依赖或预算值，没有提交/推送，没有运行真实 Docker、CC、外部模型 API 或 GPU。

## 1. 检查如何安排，实际查到了哪一层

主审负责 B 旧 R1/R3、D-1 的生产注入与消费、C 的编排停止和墙钟优先级，并重跑子审证据。Production Tracer 主责 D-2 的真实评分/队列/fatal 链及 B 旧 R2；Falsifier 主责 C 的真实 HTTP 并发、capture/轨迹到准入，同时反证主审和 Tracer 的高风险结论。两份报告分别见 [Production Tracer](production_tracer.md)、[Falsifier](falsifier.md)。没有并行修改实现。

关键所有权与调用链：

```text
miles rollout owner loop
  args → ensure_fa_started → DispositionPolicy 注入
  GenerateFn → formal _generate_attempt：episode deadline、harness task、停止处置
      │ HTTP / 线程安全预算与 poison 回调
      ▼
  adapter loop：session guard → 读请求体 → vendored cap counter
      → proxy → 推理 IO → capture / 真实轨迹树 → 响应交付
      │ drain / finish_session
      ▼
  编排：预算强停路径先停止执行；随后会话排空 → runtime 屏障 → 冻结 artifact
      → GradingQueue 独立 worker → SWEGradingManager → finally 停止 grader
      → queue future → 编排 fatal 通知 / Outcome / receipt
      → canonicalize → 真实 DefaultDataBuffer / group filter → 训练数据转换
```

adapter 的 counter 与请求交付属于 adapter loop；harness task、episode deadline 属于编排；grader 容器属于 manager，评分 worker 的存活属于 queue。**请求已接纳、模型已生成、响应已交付、执行已停止、容器已删除分别是不同事实。** 本次缺口集中在这些事实之间的等待和通知，非 GRPO/DIS 算术。

真实覆盖层次：C 的反例一路走到真实 miles buffer；停止跨墙反例使用真实 formal 编排和 `DockerQuiescenceBarrier`；D-2 反例使用真实 manager→queue→bringup 提交→编排，15 案都进入候选测试，未停在前置准备阶段。Docker、模型、评分所需 IO 的替身范围见各脚本和子审报告；没有用这些 CPU 结果冒充目标机器的故障频率或性能数据。

## 2. 四项本轮必修

以下编号属于本次联合审查；“旧 B R1/R2/R3”仍指 [上一轮报告](../batch_b_review/README.md)。P1 表示对应切片验收前修复，不表示阻塞其它已授权的独立工作。

### R1 · P1 · C：两个请求都先过 guard，会提前拒绝并中断合法的最后一轮

**位置和当前行为。** `rh2/src/repoharness2/adapters/slime/capture_wire.py:946–954` 在读取 body 前检查一次预算是否已满，只有此时已经满才等在飞请求结束。实际计数却在 `rh2/src/slime/agent/adapters/common.py:325–333`，位于 `await request.json()` 之后；`capture_wire.py:1076–1097` 一旦拒绝就立即通知编排并返回 403。

**例子。** 上限 25，当前接纳 24 次。第 25、26 个请求的头先后到达，body 都还没收全，于是两者都在“只接纳了 24 次”时通过 guard。第 25 个补齐 body 开始生成；第 26 个随后补齐 body，直接被同步 cap 判定拒绝。此时第 25 个仍未交付，编排却已经收到预算事件、开始退出宽限。若 CC 收到 403 后退出，最后一次合法请求会断连。

**违反的不变量与影响。** 已批路线要求保护已接纳的在飞交付，再拒绝超预算请求。当前实现会把本应保留的正常截断制造成 capture 缺失，最终整组补采；既有 poison/完整性检查在此处正确拒绝了不完整轨迹，不能靠删除这些检查修复。本轮没有发现多采样越过 cap，也没有发现坏 token 被放进 loss。

**可达性与证据。** 当前 app 支持同 SID 并发，body 读取存在真实 await。探针将 cap 缩到 1，以真实分块 HTTP 复现同一末轮边界，没有伪造 budget、capture 或 Outcome：

- 顺序对照：最后一轮交付后才 403，capture=1、真实树 turn=1、无 poison。
- 两份 body 先同时过 guard：403/预算通知时 inflight=2、capture=0、树 turn=0。客户端继续等待，仍可完整结束；因此不能说任何提前 403 都必然丢轨迹。
- 收到 403 后关闭在飞连接：真实 handler 取消产生 `client_cancelled`、abort=1、capture=0。
- 同一竞态进入两成员真实组：第一成员成为 `missing/api_failure`，只评分第二成员；buffer=0、recycled=1。顺序组对照 buffer=1，`raw_reward=[1,0]`，每成员训练 token=2。

真实 CC 二进制收到该 403 后是否退出仍未测；丢轨迹的客户端行为是明确的复现前提。即使客户端继续等待，过早预算通知仍会提前启动强停宽限，故不能只延迟 HTTP 响应而留下提前通知。

**修法与验收。** 在实际 cap 判定附近保证拒绝响应和退出宽限通知都等待已接纳请求交付，保持 vendored counter 的唯一来源。不要把整个 session 的生成串行化，也不要把待拒请求自身加入必须等待归零的集合。保留顺序对照，移植 body 交错反例，再覆盖多个待拒请求不互相等待、等待时真实 deadline/poison/revoke 仍生效。提前读 body 的方案还须照顾现有 capability 重写使用的 `request.clone`，不能只测 helper。

**复现：** [cap_body_race_probe.py](cap_body_race_probe.py)、[cap_to_admission_probe.py](cap_to_admission_probe.py)；主审重跑输出 [HTTP 三案](cap_body_race_result.jsonl)、[准入两组](cap_to_admission_result.jsonl)。分期：C 本次修复，保留现有并发和失败语义，不需要新的 owner 决策。

### R2 · P1 · C / D-2：停止限制了次数，却没有限制 Docker 调用等待多久

**位置和当前行为。** C 的 `execution_scope.py:40,43` 直接等待 `workspace.run_bash`，`generate.py:3755` 也没有外层时间限制。D-2 的 `grading/manager.py:1438,1452,1476` 同样直接等待 rm、inspect、kill；`_close_container_scope:1468–1480` 没有消费 `cleanup_timeout_seconds`。默认 runner 会在收到取消后 kill/wait 宿主 CLI，但它不会自行产生取消。

**例子与违反的规则。** “最多查 10 次、每次间隔 0.5 秒”并不等于“五秒内结束”：第一次 `docker exec` 不返回，就连第二次查询都到不了。`rm → inspect → kill → rm` 也只限制操作次数。已定合同要求有界停止、最终仍运行或未知则 fatal，当前代码在 IO 挂起时到不了最终判定。

**可达性和实际影响。** C 在 cap 强停、hard wall 强停时调用；D-2 在正常评分、测试失败、测试超时的 finally 都调用。Docker daemon/CLI 等待响应即可触发，正常运行期间会占住 execution 或 grader worker；完整 run 关停另有外层超时，不能代替正常收尾的时间上界。这是当前停止边界未兑现合同，不把它倒算成 B 旧 R2 修复失败。

**独立证据。** C 两案使真实 kill 通道挂起：过 episode 期限后 generate 仍 pending，drain=0、halt=0、容器尚未清理；探针自行取消才离开。D-2 分别卡住 rm/inspect/kill，清理配置 1 秒，1.05 秒后仍 pending、评分 active=1、halt=0；探针释放 IO 后才产生 scope fatal。原正常 rm、已停止、二次 rm 成功均正常返回。

**修法与验收。** 给现有停止/清理操作真正的总截止点，并把剩余时间传给每个阻塞 await；超时收掉宿主 CLI，保留 unknown/仍运行的结果并走既定 fatal，继续必要的资源回收。停止/确认/清理使用独立预算，不能因为 episode 已到点就跳过清理。也要让新增强停 await 期间父任务取消能 settle 已持有的 harness task：当前 turn 挂起探针中父任务取消后，该子 task 仍需探针单独收掉。

不用重写所有 Docker 调用或整个 shutdown；先覆盖本次新增的停止入口及共用 helper。验收应在真实编排/评分 finally 中卡住 kill、count、inspect、rm（含第二次 rm），证明有限时间内产生可诊断的终止结果；只测 helper 返回码不够。

**复现：** [stop_deadline_probe.py](stop_deadline_probe.py) 的两个 hang 案；[production_scope_probe.py](production_scope_probe.py) 的三个 block 案。主审结果见 [停止五案](stop_deadline_probe_result.json)、[评分十五案](production_scope_root_rerun.json)。分期：C/D-2 当前停止边界一起窄修。

### R3 · P1 · C：强停尚未生效时跨过墙钟，仍无条件按 turn 截断保留

**位置和当前行为。** `generate.py:3792` 只在强停之前检查剩余预算；`:3800` 等停止；`:3803` 无条件返回 `HARNESS_EXIT_STOPPED_BY_RH2=-2`。随后 `:2921–2927` 因 cap exhausted 记 `max_turns_exhausted`。强停期间，原 episode 等待已经退出，没有继续竞争真正的 hard wall。

**例子。** 600 秒墙钟，565 秒达到 turn cap，30 秒宽限结束于 595 秒。此时还剩 5 秒，于是开始强停；Docker 通道迟迟未执行 kill，直到 606 秒进程才停。当前结果仍是 max_turns/KEEP，但 600 秒时执行确实还活着，违反已批的 hard wall DROP。

**真实入口证据。** 缩短宽限的 CPU 探针使用同一可控时钟，并分别记录 kill 何时生效、进程归零确认何时返回：期限 900，899.5 开始 kill、901 才实际生效；真实 formal 编排和真实 runtime 屏障最后输出 `exit=-2`、remaining=-1、`hit_by=none`、`present_truncated/max_turns_exhausted`、评分一次、`remove_sample=False`。完整组继续准入时，D-1 对该类别的 KEEP 会放行它。此次没有证明实际生产的发生频率。

**必须保留的反证。** 另一个对照在 899.5 已实际停止，只有 count 回包在 901 到达，同样 remaining=-1。这种情况应保持 turn 语义，不能用“最后发现时间已过”一刀切改 hard wall。末尾再看一次 `remaining<0` 不是合格修复。

**修法与验收。** 让期限继续约束尚未停止的执行，并使停止事实能够区分实际终止与晚确认。复用同一时钟和既有停止 owner；不能把“已发出 kill”当成“已停止”。若宿主往返只能提供停止时间区间，须明确处理这个观测边界，而非臆造精确停止时刻。沿用既定 hard wall 优先级，不重新发明 cap 覆盖 wall。

验收三案必须同时成立：墙前停→KEEP；墙到时仍执行→DROP；墙前已停、确认/清理晚→KEEP。与 R2 一起修同一停止边界，但两者不是同一个断言：有一个停止超时仍不足以保证正确训练处置。

**复现：** [stop_deadline_probe.py](stop_deadline_probe.py) 前三案及 [结果](stop_deadline_probe_result.json)。分期：C 本次修复；不要求安排 GPU 实验来决定这条已定语义。

### R4 · P1 · D-2：Docker socket 不存在，被误认成评分容器不存在

**位置和当前行为。** `grading/manager.py:1455–1457` 只要 inspect 非零输出包含 `no such` 或 `not found`，就判 `absent`；`:1472–1474` 据此正常结束停止收口。这些词并没有绑定目标容器。

**例子与不变量。** 清理期间 Docker 连接不可用，返回 `dial unix /var/run/docker.sock: connect: no such file or directory`，缺的是连接 socket，容器可能仍在另一端运行。该诊断只能证明状态未知，不能证明容器已删除。已批 D-2 要求最终 unknown 为 fatal。

**生产入口证据与影响。** 默认 runner 原样返回错误文本。探针把该具体运输诊断送进真实 manager→queue→generate，最后交付一个 reward=1、未 remove 的样本，halt=0，未删 grader record=1，却记为 `container_scope_stopped_but_not_removed:…:absent`。换成普通 `Cannot connect to the Docker daemon` 就正确 fatal。这里的问题是未知运行状态被错误放行，不是 reward 算术错误；本机没有实际制造 daemon 故障。

**修法与验收。** 只认可明确指向本次目标容器的“不存在”响应；其它连接/上下文/凭据错误保留 unknown。成功输出也仅接受明确的 true/false。保留“目标容器确实不存在”和“已停止但未删除”的非 fatal 对照；加入 socket 缺失、传输失败的 unknown 对照。复用当前 typed scope fatal，不建通用错误分类平台。

**复现：** [production_scope_probe.py](production_scope_probe.py) 的 `unknown_socket`，主审结果 [production_scope_root_rerun.json](production_scope_root_rerun.json)。分期：D-2 本次修复，不是新的失败处置决策。

## 3. R5 · P2：取消后 scope fatal 的接收与评分 worker 退出不完整

`GradingQueue.submit` 在 `queue.py:203` 直接 await item.future；提交者取消会取消该 future。评分 worker 稍后在真实收口中抛 `GradingScopeTerminationError`，`:224–226` 因 future 已 done 丢失向编排交付该异常的机会。另一案由 `queue.close(drain=False)` 取消 worker，grade finally 的 ScopeError 替换了 CancelledError，worker 把它当普通 Exception 处理后继续循环，close 的 gather 继续等待。

两个分支都在 [评分十五案](production_scope_root_rerun.json) 复现：`cancel_submitter` 有真实终止失败记录但 halt=0；`cancel_worker` 的调用者收到 fatal，但 queue close 在 grade 展开完成后仍 pending，需要探针再次取消。

**影响限定：** 本轮追到的生产取消来源在 stop/halt 路径，没有证明正常补采会单独取消正在评分的成员。因此不能说已经证明 fatal 后继续训练。manager 的失败文本与未删 records 仍在，后续 service 的 manager.close/gc、残留汇总和外层关停超时有兜底，也不能说资源完全丢账或关停假绿。

建议当前窄修时顺带闭合：已知 scope fatal 应有独立于单个 future 的服务接收者；队列正在关闭时，处理完异常仍应退出 worker。保留原调用者的取消、普通评分错误的隔离以及通知去重。验收上述两个自然取消来源和普通错误对照，不扩到 I13、owner_cancelled 的训练处置或整套 shutdown 重构。此项 P2 明确回应即可，不另开阻塞审查轮；完整分析见 [Tracer D2-3](production_tracer.md#d2-3--p2取消后的-scope-异常没有独立于-future-的接收者)。

## 4. 已关闭的问题与已验证的正确行为

| 边界 | 本轮独立证据 | 结论 |
| --- | --- | --- |
| B 旧 R1：HEAD / baseline census 超过期限 | 真实 formal 入口，1 秒预算，census 自行被取消，CC 调用 0，容器移除 1，网络 0；无需 owner 取消 | 关闭 |
| B 旧 R2：真实 runner / create / connect / run 取消 | 默认 runner kill/wait 各 1；三种阶段网络/登记/槽位归零；创建结果未确认的容器按名字删 | 关闭 |
| B 旧 R2 清理失败对照 | network rm 失败时网络/槽位各留 1，并有明确失败记录 | 符合；不假称每种故障都能立即回收 |
| B 旧 R3：引导事实/浮点 timeout | 引导取消记已知未启动，drain/finish 各 0；599.7 秒保持浮点，超时按期限归因 | 关闭该非阻塞意见 |
| B 取消中的明确 fatal | 原致命异常通知一次、原对象上抛、容器继续清理 | 通过 |
| B proxy 排队 | deadline 原因保留；取消也记等待；50 次获取/取消交错容量均归还；跨 loop 用同一绝对期限 | 通过此次限定复核 |
| D-1 | 注入一致值幂等、冲突拒绝、库层仍中立；真实 buffer：hard wall DROP，顺序 turn 截断 KEEP | 通过 |
| C 非竞态路径 | 最后交付后拒绝、真实 capture/身份闭合，保留真实 reward，拒绝不多发模型请求；真正 poison 仍缺员 | 通过这些对照，受 R1–R3 限制 |
| D-2 正常/已停止/二次 rm 成功 | 不 fatal；停止与删除分别落账 | 通过这些对照 |
| D-2 最终 running / 普通 unknown | 真实队列传播 scope fatal，编排通知，rollout finally 完成 | 通过这些对照，受 R2/R4/R5 限制 |
| D-2 测试超时但已成功清理 | 仍是原评分失败类别，无 scope fatal | 未改变 I06–I11 的评分语义，不借此次审查替其定案 |

主审 B 结果：[batch_b_followup_probe_result.json](batch_b_followup_probe_result.json)、[production_b_r2_root_rerun.json](production_b_r2_root_rerun.json)。旧探针与旧结论保留原样，没有删除修前断言后覆盖历史输出。

## 5. 测试与维护性意见

本次测试不是“没用”：成功/缺员/fatal、准备取消和准入消费的许多接缝已有有效覆盖。漏掉的是请求体 await 的交错、停止操作本身不返回，以及错误文本指代的资源。应把上述反例移植到已有接缝测试，替换掉相同输入下只多断言几个字段的重复案例，不再为每个 helper 加一层重复测试。

- `test_budget_loop.py:297` 的 `assert ... or True` 永远通过，应删掉或改成真实的观测断言；它不阻塞已有其它有效断言，也不应计作已验证事实。
- 当前 cap 维护测试在最后一轮已进入生成后再发下一轮，测的是顺序路径；FakeTurnBudget 的 buffer 测试测消费侧。这两者相加不等于覆盖真实请求生产到消费，R1 探针补的是这个缺口。
- `execution_scope` 的“不抛异常”“约 5 秒”和 manager 的“有界收口”要随修复改成准确描述；现有注释不能作为时间保证的证据。
- `harness_launched` 的 False/None 是“明确未启动/尚未确认”，`harness_launch_attempted=True` 不等于 CC 已实际启动；保留这次改正，不为观测精确度复制 vendored 整段启动流程。
- 批 B 账本把两个既有驱动测试更换故障形态标作 T2，应与 Brief §8(11) 的 T1 登记一致；本轮已核实实际测试语义，不因此追加批准流程。
- `hit_by=proxy` 的粗粒度、count_tokens 不计预算、两个尚未决定的处置槽为 None 均按交接保留，不新增阻塞项。

## 6. 实施次序、决策边界与审查停止条件

推荐由 Claude 做三组窄修：

1. **C 入口：R1。** 修实际 cap 判定与交付等待/通知，保留并发、计数与 poison 语义。
2. **停止边界：R2＋R3。** 合并考虑停止的总时间上界、实际停止事实和 episode 优先级；分别修改 rollout/grader 各自 owner，复用必要 helper，不创建新平台。
3. **D-2 分类：R4；R5 可同批。** 严格区分缺容器与缺连接；若顺带补取消通道，只处理已知 scope fatal，保持普通评分隔离。

这些在落实既定预算/停止规则，不需要 owner 再决定一次 hard wall 是否 DROP，也不需要等 GPU 结果才能修。若拟改成整 session 串行、cap 覆盖 wall、清除 poison、丢掉部分成员重新组团，才是超出本轮的语义变更，应另行讨论。B 与 D-1 的通过结论不因 C/D-2 修复而撤回。

§6 六项 FATAL 分类仍未得到新增确认；`owner_cancelled_truncation`、`agent_violation` 仍保持 None；600 秒/25 次仍为现值，非已经选定的训练配方。此次不改 I13/I16/I18，也不扩大到数据/环境筛选。它们不阻塞修复上述四项。

修后只复核 R1–R4、R5 的实际回应及被触及的维护测试；不因还能构造其它理论状态而开启新一轮全链审查。CPU 侧关闭后，把真实 CC 对 403 的反应、容器内实际终止、目标机器耗时放进既定的 B 线诊断/原定 spike；不单独增加一轮 GPU 租用来裁决已清楚的控制流错误。

## 7. 审查维度与证据清单

| 维度 | 适用范围和结果 |
| --- | --- |
| A 正确性/并发/失败；B 训练分布 | R1–R4；真实反例表明正常截断可变缺员，或跨墙执行被错误保留，未声称训练算术错 |
| C 挡板；F 定案一致性 | 核对 KEEP/DROP、poison 不豁免与六项待确认；未新增临时挡板，未把观测选择改成新门槛 |
| D 所有权/配置；H 唯一事实 | 检查 counter、deadline、adapter→owner 回调、queue future、manager records；R2/R3/R5 指明断点，不提第二套计数 |
| E 测试有效性；G 生产接入 | 真实 HTTP→buffer、真实 manager→queue→编排；243 项维护测试与独立反例分开记录，指出不成立的测试断言 |
| I 分期；K 演进成本 | B/D-1 关闭、C/D-2 窄修；R5 限定 P2；不重造 session、Docker 或 shutdown 平台 |
| J 可读性 | 指出“有界/不抛”与实现不符、冗余恒真断言；ruff 不代替人工语义判断 |
| L 活性/容量；M 诊断 | C/D-2 永久等待、queue 取消与原因错分；不编造吞吐、发生频率或真机时长 |
| N 外部兼容 | vendor 与 miles fork 未改；对真实 vendored app 的 403/capture 接缝已测，真实 CC 退出行为和目标机器仍未验证 |

对 retry/restart、全阶段账目守恒、模型 forward/backward、MoE/loss 没有作全量验收声明：本次未改变这些模块或决定，必要的训练转换对照已覆盖；更大阶段的 Owner Gate Packet 仍归原计划。取消、deadline、queue 获取/归还、真实 scope 故障在本次范围内有专门证据；A 的 receipt 故障只做既有回归。

维护测试日志：[focused_tests.txt](focused_tests.txt)（153）、[integration_tests.txt](integration_tests.txt)（90）、[ruff.txt](ruff.txt)（25 文件）。测试使用本地 `reference/miles-rh2-integration`，只需要 CPU。

```bash
cd rh2
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run --no-sync pytest -q \
  tests/adapters/test_budget_deadline.py tests/adapters/test_async_worker.py \
  tests/adapters_miles/test_budget_loop.py tests/adapters_miles/test_batch_a_failure_routing.py \
  tests/grading/test_manager_unit.py tests/adapters/test_f2_2b_barrier.py \
  tests/adapters/test_w3b_bringup_sandbox_runtime.py tests/adapters_miles/test_w3b_formal_entry_vertical.py
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run --no-sync pytest -q \
  tests/grading/test_queue.py tests/governance/test_w1b_admission_disposition.py \
  tests/adapters_miles/test_w1b_group_admission.py tests/adapters_miles/test_bringup_vendor_only.py
```

独立脚本均在 `rh2/` 下以 `uv run --no-sync python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/<脚本名>` 运行；两个 cap 脚本同样显式使用上述 `RH2_MILES_PATH`。共六份：B followup、B R2、cap HTTP、cap admission、stop deadline、production scope。一次性探针不纳入维护测试计数。

开始快照：[review_snapshot.json](review_snapshot.json)。结束校验与脚本/结果摘要：[verification.json](verification.json)。它们只为绑定本次审查证据，不向生产链新增 hash 闸门。
