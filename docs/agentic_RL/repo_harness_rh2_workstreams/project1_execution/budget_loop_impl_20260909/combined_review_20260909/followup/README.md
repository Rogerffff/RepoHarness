# 预算终止闭环：R1–R5 修后针对性复核

日期：2026-09-09。主审：Codex；独立角色：[Production Tracer](production_tracer.md)、[Falsifier](falsifier.md)。审查版本 `3d0bca0cb0e60c049ac4d80b844ddc851cea640e`，对照 `04f599f82d5eef4a808fab001f295896ebed5efa`；作者说明为 `project1_execution/tmp/claude修复.md`。本轮只复核原 R1–R5 和修复直接影响的回归，不是新一轮全链审查。

**结论：尚不能把本轮修复全部关闭。原 R2、R4 已通过；原 R5 的两个取消问题通过，但关闭标志新增一项 P2 回归。原 R1、R3 仍各有一项生产可达的 P1。** A、B、D-1 沿用已有通过结论。C 仍待 R1/R3 收口；D-2 的停止与 fatal 核心修复通过，建议带上 R5 的队列排空回归后收尾。

| 原问题 | 修复提交 | 本次结论 | 关键证据 |
| --- | --- | --- | --- |
| R1：cap 拒绝早于在飞交付 | `1d9359f4` | **未关闭，P1** | 新 wrapper 在正确安装顺序下有效；真实 BringupService 先构造路由、后安装，实际 POST handler 仍是旧方法 |
| R2：停止 / 清理 IO 没有时间上界 | `02807adc` | **关闭** | rollout 挂起自动有界收口、harness task 已结束；grader 四处阻塞均消费同一个总预算，默认 runner 取消执行 kill/wait |
| R3：强停跨墙仍按 turn KEEP | `02807adc` | **未关闭，P1** | kill 命令失败在 899.5 返回，900.1 后发起的查询仍有进程，901 才停止；真实正式编排及处置函数仍给 KEEP_FULL |
| R4：socket 错误被认作 absent | `5d822ae9` | **关闭** | socket 缺失、畸形成功输出、其它容器的不存在均 unknown→fatal；明确本容器 stopped/absent 的例外保留 |
| R5：取消后的 fatal 接收与 worker 退出 | `5d822ae9` | **旧反例关闭；新增 R5-F1，P2** | 真实服务收到一次 fatal，`drain=False` 能退出；但 `drain=True` 提前停 worker，已有积压无法排空 |

主审独立重跑 **157 项维护测试全部通过**，11 个变更 Python 文件的 ruff 通过。另执行四份 CPU 脚本：真实 BringupService 路由绑定、7 组 cap 观测、8 个停止时序案例、20 个评分/服务/队列案例。部分断言用于确认尚存缺陷，脚本 exit 0 **不等于实现通过**。作者报告的全量 1857 passed / 310 skipped 本轮未重跑。

## 1. R1 · P1：新等待没有进入生产已经登记的 HTTP 路由

**行为与位置。** `rh2/src/repoharness2/adapters/slime/bringup.py:1069` 构造 `AnthropicAdapter`，到 `:1077` 才调用 `install_capture_wire`。vendored 构造器在 `rh2/src/slime/agent/adapters/common.py:175` 调用路由登记；`anthropic.py:48` 把当时的 `self._run_turn` 绑定为 POST handler。后续 `capture_wire.py:1109` 替换类方法不会更新路由已经保存的方法对象。与此同时，旧 guard 等待已在本次修复中删除。

**不变量与直接反例。** 已接纳的最后一轮应在预算拒绝触发收口前完成交付。现在，第 N 轮还在生成时发 N+1，实际生产形状直接返回 403 并通知预算用尽；此刻 capture=0、轨迹树=0。客户端继续等时最终还能得到完整轨迹；若收到拒绝后断开在飞连接，则真实 proxy 记录 `client_cancelled`、abort=1、capture=0。后一分支是已有 missing/丢组的入口，不是越过 cap 多采样。

**生产可达性与证据强度。** 新进程首次初始化就采用该顺序；不需要新功能、特殊训练配置或损坏输入。主审补充 [bringup_route_binding_probe.py](bringup_route_binding_probe.py)，直接运行现有 `BringupService.__init__`、真实离线 tokenizer 与本机 HTTP 线程，输出见 [结果](bringup_route_binding_result.jsonl)：

```json
{"route_handler":"_run_turn","current_method":"rh2_run_turn","route_uses_current_method":false,"cap":25}
```

该补证使用 `fa_audit_only` 的本地冻结任务面；被测的 adapter 构造/路由安装段位于任务面分流之前，与 formal 共用。没有执行 `async_start`、Docker、CC 或推理服务，HTTP handle 已停止。另一个 [HTTP 探针](cap_wrapper_followup_probe.py) 按相同生产顺序，跑真实 aiohttp→guard→vendored→proxy→capture/轨迹，确认顺序在飞和分块 body 两种提前拒绝。主审已独立重跑：[输出](cap_wrapper_root_rerun.jsonl)。真实 CC 对 403 的具体退出行为和故障发生率仍未实测，因此不宣称“每次 cap 都必然丢组”。

**修复有效部分与测试盲点。** 先安装 wire、再构造 adapter 的对照能关闭 body 交错窗口；cap=3 的三个请求仍可同时生成，另外两个待拒请求不会互锁。取消待拒请求不会 poison 已接纳轮；取消已接纳轮仍保留原 poison。新增维护测试都先 install、后构造，因而没有覆盖生产相反的顺序；旧探针动作迁移为维护测试后，其初始化假设也必须重新核对。

**修法与验收。** 优先把既有 `install_capture_wire(self.registry)` 移到 adapter 构造前，让现成路由登记直接绑定 wrapper。现有 404 middleware 补装幂等，可保留；不需要改 vendored 字节、aiohttp 私有路由表或新增状态机。验收从干净解释器构造真实 BringupService，并验证实际 POST 入口：顺序在飞、分块 body、多个待拒请求三个关键对照成立，capture、正常并发及 poison 仍正确。

**分期与成本。** 这是原在飞交付保护没有抵达生产入口，并带来顺序请求回归，属于 C 验收前的 P1。修复范围是初始化顺序和对应接线回归，无需重决策训练语义；延后会让所有正常截断监控建立在尚未生效的保护上。

## 2. R3 · P1：kill 命令返回仍被当作“执行已经停止”的证据

**行为与位置。** `execution_scope.py:72` 没有检查 `workspace.run_bash(KILL_SCRIPT)` 的结果，`:77` 无条件填 `kill_returned_at`。之后计数最终归零会覆盖先前的正数结果。`generate.py:3837–3845` 只用 `kill_returned_at <= deadline` 判墙前停止，决定返回 -2、继续按 `max_turns_exhausted` 处理。`_DockerWorkspace.run_bash` 原样返回 Docker exec 结果，命令非零并不会自动成为 Python 异常。

**违反的不变量。** 已批规则针对的是执行是否遇到 hard wall；停止命令返回、执行 scope 已停止、后来确认归零不是同一个事实。最终屏障证明现在可安全冻结，不能反向证明墙前就已停止。这里 `kill_verified=true` 只表达最终归零，不支持 `kill_returned_before_deadline=true` 被解释成“墙前已停”。

**真实正式链反例。** [stop_facts_probe.py](stop_facts_probe.py) 使用真实 formal 编排、停止 helper、`DockerQuiescenceBarrier`、评分/投影/Outcome 与实际 `AdmissionPayloadV1`，仅替换 Docker IO、模型轨迹/评分夹具及可控时钟。关键案例 `kill_failed_alive_after_wall`：

| 事件 | 相对 episode 起点的秒数 | 事实 |
| --- | --- | --- |
| kill exec 返回 | 899.5 | exit_code=1，容器内执行未停 |
| episode 墙钟 | 900.0 | 执行仍未停 |
| 第二次 COUNT 发起 / 返回 | 900.1 / 900.2 | 仍有 1 个进程；此查询本身在墙后发起，排除墙前查询晚回包的解释 |
| 执行停止并归零 | 901.0 | 后续屏障通过，可以评分 |
| 当前 Outcome / 准入处置 | — | `max_turns_exhausted / present_truncated`，**KEEP_FULL** |

[主审输出](stop_facts_probe.jsonl)中，该案例评分一次、清理完成，没有 fatal。真实 payload 经 `decide_member_disposition` 得到 `truncation_policy_horizon_kept`。夹具没有经过 miles 样本身份盖章，因此这里是实际载荷的处置验证，**不是另一次完整 buffer 或参数更新实验**。

该故障的 producer 是已有 Docker exec 的非零结果，不是人为注入一个生产不会抛的异常。受控 IO 明确给出未停止的执行；不能仅凭任意正进程数就断言用户代码还在运行，真实进程数也可能包括僵尸。这里不依靠该推论，也不声称已在真实 Docker 上测得故障率。`pkill …; true` 还会屏蔽容器内命令退出码，但主反例只需 Docker exec 本身失败，已足以成立。

**旧对照与观测缺口。** 同一探针确认墙前正常停止→KEEP、停止动作墙后才生效→DROP、墙前停止而归零确认晚→KEEP，说明旧三案中的特定缺陷确有修复。另有“实际 899.5 已停、kill 的宿主回包 901 才到”得到 DROP 的对照：夹具知道实际停止时刻，当前代码不知道。它用于说明两个回包时间无法完整识别停止时刻，**不要求实现凭空猜测，也不另报新 P1**。独立 Falsifier 用真实 helper 另做两案，交叉回读主审正式链输出，见其报告 §2。

**修正边界与验收。** 继续沿原 R3 修正停止事实与判据：至少保留 kill 失败，不能把墙后仍未停止的事实被最终归零覆盖，不能用命令返回时刻冒充停止时刻。对能够证明的墙前停止，后续清理/确认迟到不应凭时间戳改造出 hard wall；实际无法区分的边界需要明确表达不确定性，不能以 T1 时间字段名掩盖语义替换。若实现方案准备统一改变这类未知边界的 KEEP/DROP 处置，应在写码前说明该变化与已批规则的关系，不由本次审查默认批准。

窄验收至少包含上述 kill 非零、墙后再次查询仍活、最终归零的正式链反例，并保留正常停止、晚停止、已知墙前停止但确认晚的对照。看最终 Outcome 和真实处置函数，不能只断言字段已存在或最后屏障通过。简单改为“最后 remaining<0 就 DROP”仍不能准确实现此前约定。

**分期与成本。** 原 P1 未关闭，原因是当前停止 IO 的现成失败结果会进入错误训练处置。频率未知，不能据 CPU 探针估算训练偏差比例；影响限于 cap 强停与墙钟相邻的故障轨迹。需要修的是已有停止动作的证据定义及其消费者，不要求实现分布式时间平台或扩大 scope 所有权。

## 3. R5-F1 · P2：关闭标志让 drain 阶段没有 worker 消费积压

**行为、位置与不变量。** `grading/queue.py:162` 在 close 一开始设 `_closing=True`，`:164` 才等 `queue.join()`；worker 在 `:241` 却只在 `not _closing` 时取下一项。当前评分完成后 worker 全退出，剩余排队条目无人 `task_done`，与该函数“先等在途/排队请求全部完成再撤 worker”的合同相反。

**生产反例。** 一个 worker、两个已接收请求：第一条正在评分，第二条排队；执行真实 bringup `grading_queue` 关闭步骤并放开第一条。此时 worker 已退出、队列深度仍为 1、close 仍等 join。把既有外层 `grading_drain` 缩为 0.2 秒后，真实步骤耗满期限，返回 `drained_within_timeout=false`；仅处理第一条，第二个 future 仍 pending。另一个对照先取消全部提交者，队列条目仍在，回归同样成立，覆盖服务先取消在飞执行的真实顺序。

**影响与限定。** 当前服务默认 drain 为 60 秒，这类正常可以完成的收尾会无谓等满一分钟，再走已有 `close(drain=False)`。服务还有外层步骤上界及后续 manager/residue 清理，故本项为关闭阶段 P2：不宣称整个服务永久挂死、正常训练继续或容器失去登记。直接调用 queue 的默认 close/async with 则没有服务外层超时，可能一直等。

**窄修与验收。** 让 drain 阶段继续消费已接收条目，把使 worker 退出的标志放到 drain 完成之后、撤 worker 之前；`drain=False` 仍立即设置。无需重写队列生命周期。验证一个 worker/两个条目、提交者仍在/已取消两案及时排空，保留旧 R5 的取消后带外 fatal、关停中 fatal、worker 被取消三案，仍只通知一次。建议作为本次修复回归一并收尾，不阻塞其它独立工作；不改变 `owner_cancelled` 的训练处置。

## 4. 已通过部分的证据与边界

- **R2 rollout**：挂起 kill 用 0.08 秒测试预算，编排强停与屏障各自消费总预算，约 0.16–0.17 秒自动结束，屏障拒绝、不评分、样本 missing、容器清理完成、harness task 全结束。维护测试额外验证父任务在强停中取消时仍回收子任务。这里 final cleanup 成功，不把中间未确认停止误报成最终容器无法回收。
- **R2 grader**：真实 manager→queue→编排→service，首次 rm、inspect、kill、二次 rm 四处分别挂起，总预算 1 秒时都约 1 秒自动取消并报告一次 scope fatal。真实默认 `run_docker` 配子进程替身，前两步各耗 0.025 秒，总预算 0.1 秒在 kill 处到期，宿主 CLI 的 kill/wait 各调用一次，未逐步骤重置预算。没有把操作系统层不可中断的任意故障纳入新的阻塞面。
- **R4**：socket 不存在、成功但输出畸形、其它容器不存在均不能当作本容器 absent。明确 stopped/absent、正常删除、kill 后二次删除成功的既定例外保留。普通评分测试超时且 scope 已关闭时保持 `failed_to_grade`，不扩大为 run-fatal。
- **原 R5**：提交者取消后，真实注入的 `notify_run_fatal` 到达 service lifecycle 与关闭报告，记录一次；关停已开始时同样进入报告。`close(drain=False)` 取消评分被 ScopeError 替换后 worker 仍退出，close 返回。带外通道没有依靠 `list.append` 替身冒充服务接收。

评分完整证据与替身边界见 [Production Tracer](production_tracer.md)，主审重跑输出为 [production_root_rerun.jsonl](production_root_rerun.jsonl)（文件内容是 JSON 数组），其 20 个案例已逐项断言；该脚本也会写 [独立结果文件](production_followup_probe_result.json)。这四条通过结论不依赖真实 CC 的 403 行为或 GPU 性能实测。

## 5. 覆盖、验证与收口条件

按审查标准 A–N 只扫描本轮差异与必要连接：

| 维度 | 本轮处理与证据 |
| --- | --- |
| A 正确性/并发/失败模型，L 活性/反压 | R1 真实 HTTP 交错、R2 四类阻塞、R5 取消/排空；没有增加正常生成串行锁 |
| B 训练分布，F 已定语义 | R1 可能制造缺员；R3 实际 payload 错误 KEEP；完整组及两类预算策略值保持原样 |
| C 挡板 | 此次未新增生产拒绝路径或临时挡板；未把监控改为准入条件 |
| D 所有权/配置，G 生产路径 | 真实 BringupService 初始化、同一总截止点、真实服务 fatal 接收；R1 是实际接线失败，不只函数实现问题 |
| E 测试有效性 | 检出 install-first、kill 返回即生效、只有单条在飞的三个夹具盲点；补针对性反例，不重复全量堆测试 |
| H 唯一事实源，M 诊断 | R3 命令返回与实际停止仍混用；R5 fatal 进入服务且不重复；新停止诊断不是停止事实的自动证明 |
| J 可读性，K 演进成本 | 指出停止注释与行为不符；建议安装顺序和关闭标志窄修，不新增 owner/生命周期平台 |
| N 外部兼容性 | vendored 路由绑定及 aiohttp 实际请求被验证；依赖与采样配置未改，真实 CC/GPU 未覆盖，不从替身推断兼容性实测 |

维护测试命令（仓库根进入 `rh2`）：

```bash
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run --no-sync pytest -q \
  tests/adapters/test_budget_deadline.py tests/adapters_miles/test_budget_loop.py \
  tests/grading/test_manager_unit.py tests/grading/test_queue.py \
  tests/adapters/test_f2_2b_barrier.py tests/adapters/test_w3b_bringup_sandbox_runtime.py \
  tests/adapters_miles/test_w3b_formal_entry_vertical.py tests/adapters_miles/test_w1b_group_admission.py
```

结果：[focused_tests.txt](focused_tests.txt)，157 passed in 49.83s，exit 0；[ruff.txt](ruff.txt)，11 个变更源码/测试文件通过。四个脚本均用相同 `uv run --no-sync python` 运行，入口是本目录的 `bringup_route_binding_probe.py`、`cap_wrapper_followup_probe.py`、`stop_facts_probe.py`、`production_followup_probe.py`；错误输出文件同目录单独保存，没有改写上级旧探针和历史结果。

版本与变更范围见 [review_snapshot.json](review_snapshot.json)。源码及维护测试 11/11 摘要复核一致、`rh2/src` 与 `rh2/tests` 无工作区 diff；全仓其它共享文档/参考目录有既有改动。本轮只新增审查工件、更新 Brief/交接的当前状态及 infra 账本，没有提交/推送或修改代码。没有调用真实 Docker、CC、外部模型 API 或 GPU。

**停止条件与下一步。** R2、R4 和原 R5 的已验证部分到此关闭；A、B、D-1 不重开。后续只围绕 R1 安装顺序、原 R3 停止事实、R5-F1 排空回归及必要对照收尾。R1/R5-F1 可以直接作局部修复；R3 应先把判据能证明什么写清楚，避免再添加一个时间字段却仍推导不出停止事实。新的无关 P1/P2 进入阶段 backlog。§6 六项、`owner_cancelled`/`agent_violation` 未定槽位、600 秒/25 次预算均未获本轮新增批准。
