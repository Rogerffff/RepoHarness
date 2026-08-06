# 五层计时模型提案（timing model proposal）

```text
status: draft（提案，待 owner 与 codex 审查）
scope: 只读研究产物——本文档不改变任何已定案语义；所有"接线点"均为
       提案，落地前按各自 T0/T1 分级走流程
inputs: fa2a_decision_package.md v3.2（D1a 第 3 条双时钟 / 第 4 条静止
        屏障）；s2/codex_reviews.md "FA-2A 决策包二审 + 计时调查" 归档段
        （五层模型建议 + measurement_source 四值 + 可救未存清单）
evidence: P3 真实数据 = docs/agentic_RL/repo_harness_rh2_workstreams/
        preflight/remote_evidence_20260708/bringup_selected/
        j5_reduced_gbs20_20260708T171722Z/buf_536870912/artifacts/
        bringup_events.jsonl（32 条 rollout，本文全部数值可由此重算）
```

> **⚡ V0 定案范围（2026-08-07 owner 批准，codex 五审收缩）**：FA-2A 只
> 实现 **Observability V0**——扩展现有 `RolloutAudit.timeline`（不建新
> 服务/数据库/五套公共契约），事件持久化原始 monotonic timestamp + 三个
> 最小字段（clock_domain_id / owner_role / physical_attempt_id），同
> clock domain 才允许相减，缺结束事件即天然表示 crash。**只记录，不用
> 新计时改变 termination/reward/admission/gradient**；不定义
> chargeable_policy_seconds（是否需要留 D1b）；**L4 不导出
> trajectory.jsonl、不新增工具级脱敏 artifact、不声称工具级精确计时**
> （CC 内部时间记 residual_estimate）——本文 §4b 的 L4 方案与三个 T0
> 候选全部转入 D1b 批次待议。本文其余细节契约作为 V1+ 设计储备保留。
>
> **V0 唯一可执行清单**（六审 1：与储备内容物理分开）。**切片前置
> （F2-0 复核 1）**：本清单每个事件带 `physical_attempt_id`，而该字段
> 属四层身份——**F2-1a（身份先行）必须先于本清单落地**；切片顺序 =
> F2-1a 身份 → **F2-0b** 本清单 → F2-1b Outcome v2。四项均归 F2-0b：
> 1. `RolloutAudit.timeline` 扩事件名（服务启动/单 rollout/模型调用/
>    组与 batch 四组事件表，见 codex 五审 §3）+ 每事件三字段
>    （clock_domain_id / owner_role / physical_attempt_id）；
> 2. execution audit 记录加 `wall_*` 原始时间与候选
>    `non_chargeable_intervals`（**不派生 chargeable 值**）；
> 3. `ModelCallAttempt` optional 等待/发送区间字段（同 clock domain）；
> 4. SGLang `server_timing` 白名单保存（§4a 方案，T1）。
> **明确不在 V0**：L4 全部；chargeable_execution_seconds；deadline 起点
> 切换（P1-5 行为变更——改变超时分布，转 D1b 批次）；任何用新计时改变
> termination/reward/admission/gradient 的路径。

## 0. 三条全局规则（所有层共用）

**R1 时间域（clock domain）规则。** `time.monotonic()` 只在同一进程内
可比（跨线程可以：同进程各线程读同一单调钟）。本系统实际只有三个时间域：

```text
域 1：RolloutManager Ray Actor 进程（含 AsyncLoopThread 编排 loop 与
      rh2-anthropic-adapter aiohttp 线程——同进程两个线程，monotonic 可互减）
域 2：rollout 容器内的 Claude Code 进程（stream-json 事件带自己的时间戳）
域 3：SGLang server 进程（meta_info 里返回 queue_time 等 duration）
```

跨域禁止直接相减 monotonic。跨域只允许三种做法：(a) 各自 owner 侧记
duration；(b) 用关联 ID（request_id / tool_use_id）把对方报告的 duration
挂到本域区间上；(c) epoch 时间（`time.time()`）只用于人读对齐展示，
不进任何预算判定。既有代码已实践 (a)+(b)：`RolloutTimelineEntry` 同时记
`seconds_since_start`（monotonic 差）与 `epoch_seconds`（generate.py:1204-1213）。

**R2 measurement_source 四值**（codex 计时调查建议，逐字采纳）：

```text
owner_measured    该时间域 owner 自己测的区间（可信度最高）
server_reported   对端服务自报 duration（SGLang queue_time；CC 事件时间戳）
correlated        通过关联 ID 拼合两端事实得到（tool_use_id 关联 Pre/PostToolUse）
residual_estimate 残差推算（总区间减去已知子区间；CC 内部规划只能这样）
```

**R3 原始区间优先。** 保存 `start/end` monotonic 原始值（附 epoch 副本），
派生秒数在读取端算——这正是 `RolloutAudit.timing_summary()` 的既有模式
（generate.py:1225-1262：存 timeline，summary 是纯函数）。并集/扣除只由
单一 owner 派生一次（v3.2 D1a 第 3 条"重叠暂停不得重复扣除"）。

---



## 1. 现状时钟地图：四个时钟的精确起止点与错位后果



### 1.1 四个时钟


| 时钟                           | 起点（file:line）                                                                                                                                                | 终点                                                                                                                                                                  | 预算/用途                                                        | 时间域 |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | --- |
| A. RolloutAudit 全程钟          | `RolloutAudit` 构造即起表：generate.py:1450（`started_monotonic` 缺省值在 :1179），首事件 `step1_custom_generate_invoked` :1454                                              | timeline 最后一个事件（正常为 `cleanup_completed` :1726）                                                                                                                      | 无预算，纯观测；产出 9 个粗桶（timing_summary :1225-1262）                  | 域 1 |
| B. `harness_run_seconds` 混合桶 | `audit.mark("harness_started")` generate.py:1502——在 `ClaudeCodeDriver.run()`（glue.py:155）**之前**                                                              | `step3_harness_completed` generate.py:1539                                                                                                                          | 无预算；P3 中位 613.5s = 全墙钟的 96.9%                                | 域 1 |
| C. slime `time_budget_sec`   | sandbox.py:124 调 `_await_done_marker`，其内 `deadline = time.time() + time_budget_sec`（sandbox.py:71）——即 CC detached 进程 `setsid` spawn（sandbox.py:117）**之后**才起表 | done marker 出现，或超时返回 `EXIT_TIME_BUDGET_EXCEEDED = -1`（sandbox.py:60）                                                                                                | 600s（glue.py:78 `AGENT_TIME_BUDGET_SEC`）；**超时不杀 setsid 进程组** | 域 1 |
| D. proxy episode deadline    | capture_wire.py:190-205 `session_deadline()`：**首次模型调用**惰性起表（`monotonic + default_session_budget_seconds`，600s 由 glue.py:663 注入）                              | 由 proxy 消费：async_worker.py:843-850（剩余 < `min_attempt_budget_seconds` → `episode_deadline_exhausted` 缺员）及 `_wait_active_before_send`/`_wait_version_advance` 的等待预算封顶 | 600s，但比 C 又晚"CC 启动到首次调用"数秒~数十秒                               | 域 1 |


补充：时钟 B 的"未计时前奏"具体是——glue.py:159 `_install_native_cli`
（CC 平台包上传 + 解包 + `claude --version` 校验，单步 timeout 180s）→
glue.py:165-172 `useradd + chown -R agent:agent /home/agent {workdir}`
（timeout **900s**——django 官方镜像 /testbed 数万文件在 overlay2 copy-up
下极慢，run6 曾 8/8 超 60s 全灭）→ claude_code.py:44 `write_config` →
sandbox.py:111 launcher 写入、:113-123 `setsid` spawn。这些全部发生在
时钟 C 起表之前。

四个时钟起点关系（同一条 rollout 内）：

```text
A 起 ──(materialize ~5s)── B 起 ──(安装+chown+config：0~470s，无计时)── C 起 ──(CC 启动+首轮请求：秒级)── D 起
```



### 1.2 错位后果：P3 的 5 条 exit=-1 轨迹（反例）

P3（32 条真实 rollout，j5_reduced_gbs20 run）整体分布：墙钟
min/中位/max = 302.0 / 633.4 / 1116.2s；`harness_run_seconds` =
280.3 / 613.5 / 1079.9s——中位 96.9%（约 97%）的墙钟落在混合桶 B。

其中 `harness_exit_code = -1`（时钟 C 判超预算）的 5 条：


| instance_id          | index | harness_run_seconds | 超出 600s 预算 | 全程墙钟   |
| -------------------- | ----- | ------------------- | ---------- | ------ |
| psf__requests-1142   | 23    | 781.2               | +181.2     | 798.6  |
| psf__requests-2931   | 26    | 785.1               | +185.1     | 798.6  |
| sympy__sympy-15349   | 19    | 824.9               | +224.9     | 835.6  |
| django__django-11133 | 6     | 1068.4              | +468.4     | 1082.7 |
| django__django-16139 | 8     | 1079.9              | +479.9     | 1116.2 |


这组数字同时证明三件事：

1. **"超出预算 181~~480s"不是策略多跑了 181~~480s**。时钟 C 恰好走满
  600s（外加 5s 轮询 + 15s exec 的过冲，sandbox.py:73-74），多出来的
   181~480s 是时钟 B 里未计时的安装/chown 前奏。django 两条 +468/+480
   对 psf__requests 两条 +181/+185——差异随 repo 体积（chown 文件数）
   变化，是**基建时间**，与策略无关。若拿 `harness_run_seconds > 600`
   当"策略超时"判据，会把 django 的 chown 慢惩罚成策略失败——这正是
   v3.2 D1a 反复强调"基建等待被训练成策略失败"的具体形态。
2. **时钟 C 超时 ≠ workspace 静止**。`_await_done_marker` 返回 -1 后
  setsid 进程组仍在跑（无 kill 逻辑），直到 cleanup 的 `docker rm -f`
   （generate.py:2195 `_cleanup_container`）。中间的 drain/装配/评分窗口
   （generate.py:1548-1671）workspace 可能仍在被写——与 v3.2 D1a 第 4 条
   静止屏障的要求相反（现状靠 `reject_on_nonzero_harness_exit` 在正式链
   把这类 execution 整条拒掉，generate.py:1560-1565，属于兜底而非屏障）。
3. **时钟 D 与 C 不是同一个 deadline**。D 从首次模型调用起表，比 C 晚；
  一条 CC 启动慢的轨迹，C 已耗尽时 D 还有余量，proxy 仍会放行新模型
   调用。此错位已登记为 05 计划 §6.1 P1-5（"orchestrator 在 execution
   启动时生成绝对 deadline 并注册"，归 FA-2 身份批）。

---



## 2. 五层计时契约设计

分层采纳 codex 计时调查的五层建议（RunTiming / ExecutionTiming /
ModelCallTiming / ToolTiming / GroupBatchTiming）。设计总原则：**不新造
平行账本**——每层挂在既有的单一事实来源结构上，新增的只有字段与一个
公共小类型 `TimingInterval`：

```text
TimingInterval:
  name                 区间名（封闭枚举按层定义，见各层字段表）
  start_monotonic      owner 进程 monotonic（float）
  end_monotonic        同上；end >= start（模型校验器）
  start_epoch_seconds  epoch 副本（只作人读对齐，不进判定）
  measurement_source   owner_measured / server_reported / correlated /
                       residual_estimate
```

（duration-only 的对端事实——如 SGLang `queue_time`——不用
TimingInterval，用带 `measurement_source=server_reported` 的标量字段，
因为它没有本域可比的 start/end。）

### 2.1 L1 RunTiming——进程/run 级冷启动（每 actor 进程一次）


| 字段                                 | 含义                                                | source         |
| ---------------------------------- | ------------------------------------------------- | -------------- |
| `startup_checks_interval`          | `_run_startup_checks`（glue.py:519，真实 SGLang 探针往返） | owner_measured |
| `grading_queue_start_interval`     | `grading_queue.start()`（glue.py:520）              | owner_measured |
| `adapter_app_started_interval`     | aiohttp adapter 线程起动到就绪                           | owner_measured |
| `tokenizer_template_hash_interval` | tokenizer/chat template 装载与 hash（glue.py:523-525） | owner_measured |
| `first_cc_install_seconds`         | 首个 rollout 的 CC 安装耗时（从 L2 引用，不重复测）                | correlated     |


- **owner**：Ray actor 进程主线程 / AsyncLoopThread（`BringupService.async_start`，glue.py:508）。
- **挂点**：`startup_evidence.json`（glue.py:13-15 既有产物）加一个
`timing` 段。Ray/Megatron/SGLang 集群级冷启动与 trainer 的
`train_wait / data_preprocess / actor_train / update_weights` **不在
RH2 重测**——slime 已有（preflight_report.md:40 附近：一步 1387s，
其中等 rollout 1135s、训练 252s、权重同步 11.45s），L1 只记引用口径。



### 2.2 L2 ExecutionTiming——execution 级（核心层，双时钟落点）

载体 = 既有 `RolloutAudit`（generate.py:1174）+ 其落盘物
`rh2.fa.execution_audit.v1`（glue.py:319-342）。两类新增：

**(1) 细分 mark 事件**（扩充 timeline 的事件名集合，机制零改动——
`audit.mark()` 旁路时间线本来就为此设计，generate.py:1160-1166）：


| 新事件名                                                    | 位置                                             | 拆开的桶                                         |
| ------------------------------------------------------- | ---------------------------------------------- | -------------------------------------------- |
| `harness_install_started` / `harness_install_completed` | ClaudeCodeDriver.run 内（glue.py:159 前后）         | CC 上传+安装+版本校验                                |
| `agent_user_ready`                                      | glue.py:172 chown 完成后                          | useradd + chown -R                           |
| `harness_config_written`                                | slime `write_config` 返回后                       | CC 配置写入                                      |
| `cc_process_spawned`                                    | `exec_and_wait` spawn 返回后（对应 sandbox.py:124 前） | **时钟 C 的真实起点**从此可与 A/B 对账                    |
| `harness_done_marker_observed`                          | `_await_done_marker` 返回处                       | 区分"CC 自然结束"与"预算耗尽返回 -1"                      |
| `quiescence_barrier_started` / `quiescence_confirmed`   | FA-2A 静止屏障落地处（v3.2 D1a 第 4 条的序列）               | 静止确认耗时；无 `quiescence_confirmed` 即不可评分的机器可查证据 |


接线方式：`ClaudeCodeDriver.run`（glue.py:155）拿不到 audit 对象——
给 driver 协议加可选 `phase_sink: Callable[[str], None]` 参数，
orchestrator 传 `audit.mark`（driver.run 在同一 asyncio loop 内被 await，
generate.py:1503-1512，无跨线程问题）。slime 内部的 spawn/marker 两个
事件归 **F2-0b**（F2-0 已完成且为纯迁移，不加任何事件——复核 2 消除
"F2-0 顺路加"旧文字）：driver 提升后的代码在 F2-0b 加事件（不改
`reference/slime`，见 §6 不做清单）。

**(2) 双时钟字段**（v3.2 D1a 第 3 条的直接落点）：


| 字段                                               | 含义                                                                                                                                                                                                                                                     | source                             |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------- |
| `wall_start_monotonic` / `wall_end_monotonic`    | 即 `started_monotonic` 与 timeline 末事件（已存在，只是显式命名进落盘记录）                                                                                                                                                                                                  | owner_measured                     |
| `non_chargeable_intervals: list[TimingInterval]` | 首版**只含两类 reason**：`weight_update_pause`（proxy `_wait_active_before_send` + `_wait_version_advance` 的等待区间，async_worker.py:753-777 / :960-1037）与 `system_backpressure_wait`（`ResourceLimits.acquire("model_call")` 的排队区间，async_worker.py:121-124 / :748） | owner_measured（域 1 内 adapter 线程测量） |
| `chargeable_execution_seconds`                   | 派生：`(wall_end - wall_start) - 并集(non_chargeable_intervals)`，由 audit owner 在 finalize/audit_sink 时刻计算一次（generate.py:1735-1737 已是唯一收口点）                                                                                                                  | 派生值，不独立维护                          |


**与 v3.2 的对接方式（单一 owner 并集）**：区间的**测量 owner** 是
adapter aiohttp 线程（proxy 在那里跑），**并集 owner** 是编排 loop 的
finalize 路径——两者同进程（域 1），monotonic 可直接比。传递通道复用
既有的 `ModelCallAttempt` 账本：attempt 上新增 optional 等待区间字段
（见 L3），finalize 时 `snapshot_attempts()`（async_worker.py:644-651，
已是跨线程安全接口）取出全部 attempt，把等待区间收集、排序、合并重叠
（interval union 标准算法），写入 execution_audit。**不给 RolloutAudit
增加跨线程可变字段**（FA-1 九轮竞态修复的教训：不再引入新的共享可变
状态面）。

训练面消费：`RolloutAttemptOutcome`（fa_runtime.py:120）新增 optional
`wall_clock_seconds` / `chargeable_execution_seconds` /
`timing_record_ref` 三个标量/引用字段——outcome 只带派生标量与引用，
区间清单的唯一事实来源留在 execution_audit（对齐 D1a 第 5 条"单一事实
来源 + 派生视图"）。D1b 诊断清单（决策包 :211-216 的 materialize /
harness_install / model_queue / … 区间）全部可由 L2 timeline + L3 记录
重算，无需另设诊断专用账本。

### 2.3 L3 ModelCallTiming——单次模型调用 attempt 级

载体 = 既有 `ModelCallAttempt` contract（fa_runtime.py:306）+ 生产它的
`ModelCallProxy`（async_worker.py:583）。新增 optional 字段：


| 字段                                                      | 测量点                                                                                                                                                                                                              | source          |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| `active_wait_interval: TimingInterval | None`           | `_wait_active_before_send` 入口到返回（async_worker.py:753-777）                                                                                                                                                        | owner_measured  |
| `limiter_wait_interval: TimingInterval | None`          | `limits.acquire("model_call")` 从请求到获得（async_worker.py:748；`_ResourceLease.__aenter_`_ :121-124 已统计 backpressure 次数，本项补秒数）                                                                                        | owner_measured  |
| `send_interval: TimingInterval`                         | `_send` 的 `send_fn` await 前后（async_worker.py:858）——含 HTTP 排队+SGLang 全程+SSE 读取                                                                                                                                    | owner_measured  |
| `version_recovery_wait_interval: TimingInterval | None` | `_wait_version_advance` 全程（async_worker.py:960-1037）                                                                                                                                                             | owner_measured  |
| `server_timing: SGLangServerTiming | None`              | 从响应 meta_info 摘取（见 §4a），delivered attempt 才有                                                                                                                                                                     | server_reported |
| `presend_prepare_seconds: float | None`                 | 同一 HTTP 请求从 adapter 入口到 `rh2_call_sglang_generate` 发出前的准备段（解析 + renderer/tokenize 在 slime `BaseAdapter._run_turn` 内完成后才进本函数；入口时间戳可在 session_guard middleware 记，capture_wire.py:367-394，同域 1 相减）；实测预计毫秒~百毫秒级，先记后看 | owner_measured  |


推导链示例（用于验证字段够不够拆）：一次被权重更新 abort 的轮 =
attempt_1（`send_interval` 半途 + `non_delivered_aborted`）→
`version_recovery_wait_interval`（这段同时上报为 L2 non-chargeable 的
`weight_update_pause`）→ attempt_2（新 `send_interval`，delivered，带
`server_timing`）。CC 感知到的单轮总延迟 = 两个 attempt 的区间外包络，
可与 L4 的 CC 侧事件时间戳交叉验证（correlated）。

**owner**：adapter aiohttp 线程（proxy `_clock = time.monotonic`，域 1）。
attempt 已有完整的落盘链：`write_execution_audit_record` 把
`model_call_attempts` 全量 dump 进 execution_audit（glue.py:341），字段
加上即自动随账落盘，**零新增持久化面**。

### 2.4 L4 ToolTiming——工具/subagent 级（诊断专用，不进任何判定）

数据源 = CC stream-json 事件流。事实链：slime `run_agent` 把 CC stdout
重定向到容器内 `{workdir}/.harness/trajectory.jsonl`
（reference/slime/slime/agent/harness/common.py:117），launch flags 已带
`--output-format stream-json --include-partial-messages --include-hook-events --verbose`（claude_code.py:24-28）——即
PreToolUse/PostToolUse hook 事件与消息时间戳**已经在产生**，只是容器
删除前从未读出（§4b 的救援对象）。


| 字段                               | 含义                                                           | source            |
| -------------------------------- | ------------------------------------------------------------ | ----------------- |
| `tool_use_id`                    | 关联键（CC 事件自带）                                                 | ——                |
| `tool_name`                      | Read / Edit / Bash / Task 等                                  | server_reported   |
| `pre_event_ts` / `post_event_ts` | Pre/PostToolUse hook 事件的 CC 侧时间戳（域 2，**只与同文件内其他 CC 时间戳相减**）  | server_reported   |
| `parent_tool_use_id`             | subagent 归属（并行 subagent 的时间**不相加**，见 §6）                     | server_reported   |
| `is_background`                  | 后台化工具（Bash run_in_background）——结束事件 ≠ 进程静止                   | server_reported   |
| `usage_token_counts`             | 相邻 assistant 消息的 usage 计数（脱敏白名单内）                            | server_reported   |
| `cc_internal_residual_seconds`   | 每轮 residual = CC 侧相邻模型请求间隔 − Σ工具区间（黑盒规划/bookkeeping 的唯一可得口径） | residual_estimate |


**owner**：容器内 CC 进程（域 2，**不可信**——文件属 agent 用户，
CC/工具/模型输出都能写它）。因此 L4 有硬性三条：只作诊断与 D1b 分布
分析；解析按不可信输入处理（大小上限、字段白名单、解析失败只记
failure 不影响 rollout 结果）；**任何准入/预算/reward 判定不得引用 L4**。
与域 1 的对齐只能 correlated：adapter 侧每轮的 `send_interval`（L3）与
CC 侧 message 事件按轮序/request 关联，估出两域钟差（±网络与缓冲抖动，
不声称精确）。

### 2.5 L5 GroupBatchTiming——组/批次级

现状：fully async worker 只有计数没有秒数——
`ResourceLimits.backpressure_counts`（async_worker.py:108）、
`BoundedDeliveryQueue.backpressure_events`（:144）、`WorkerCounters`
（:1069-1077）。FA-2B assembler / FA-3 batch 状态机是本层的自然载体：


| 字段                                        | 含义                                                             | 挂点                                                                 |
| ----------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------ |
| `member_outcome_at`                       | 各 member 的 `RolloutAttemptOutcome` 提交时刻                        | assembler 收 outcome 处                                              |
| `group_ready_at`                          | 固定 n 集齐时刻                                                      | `PromptGroupState` OPEN→READY 迁移                                   |
| `ready_queue_enqueued_at` / `dequeued_at` | ready queue 驻留区间                                               | `QualifiedPromptGroupQueue`（05 计划 FA-2B 第 3 条）                     |
| `admission_decided_at`                    | staleness 重算与准入结论时刻                                            | `PromptGroupAdmissionReport`（v3.2 D1a 第 5 条载体）新增 optional timing 段 |
| `handoff_at` / `ack_at`                   | READY→RESERVED→SUBMITTED→…（05 计划 FA-3 lease 状态机，:139-146）各迁移时刻 | batch lease 账本                                                     |
| `delivery_queue_wait_seconds`             | worker 投递队列反压等待                                                | `BoundedDeliveryQueue.put`（async_worker.py:146-151）补时长             |


**owner**：RolloutManager state-owner 进程（与 D2 checkpoint owner 同
进程，域可能 ≠ 域 1 的 rollout actor——若 assembler 与 worker 不同进程，
member 侧只传 duration 与 epoch 副本，state-owner 侧一律用自己的
monotonic 记录"收到时刻"，遵守 R1）。评分侧不重复建层：
`GradingTimingRecord`（contracts/timing.py:26）已是完整先例（五类计时 +
queue_wait + 峰值内存，生产于 grading/manager.py:631-632），L5 直接
引用其 `record_id`。

---



## 3. 接线点清单（每层挂哪个既有结构）


| #   | 层     | 挂点 file:line                                                                                   | 挂在哪个既有结构上                                                                                                                                                                       |
| --- | ----- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | L2    | rh2/src/repoharness2/adapters/slime/generate.py:1160-1166, 1204-1213                           | `RolloutTimelineEntry`/`audit.mark`——只扩事件名集合，机制不动                                                                                                                               |
| 2   | L2    | rh2/experiments/s1_7a_bringup/glue.py:155-188（F2-0 后为 src 内正式位置）                               | `ClaudeCodeDriver.run` 加 optional `phase_sink` 参数，orchestrator 传 `audit.mark`                                                                                                   |
| 3   | L2    | rh2/experiments/s1_7a_bringup/glue.py:298-349                                                  | `write_execution_audit_record`：记录加 `wall_*` 与候选 `non_chargeable_intervals`（**只记录原始区间**；`chargeable_execution_seconds` 派生值 = D1b 决策，V0 不写入——六审 1） |
| 4   | L2/L3 | rh2/src/repoharness2/adapters/slime/async_worker.py:644-651                                    | 并集派生走既有 `snapshot_attempts()` 跨线程安全接口，不新增共享可变状态                                                                                                                                 |
| 5   | L3    | rh2/src/repoharness2/contracts/fa_runtime.py:306-369                                           | `ModelCallAttempt` 新增 optional 区间字段（validator 保持既有 delivered/non-delivered 约束不动）                                                                                                |
| 6   | L3    | rh2/src/repoharness2/adapters/slime/async_worker.py:753-777, 748, 858, 960-1037                | `ModelCallProxy` 四个等待/发送点各包一段区间测量（`self._clock` 已注入可测试）                                                                                                                         |
| 7   | L3'   | rh2/experiments/s1_7a_bringup/capture_wire.py:546-578                                          | `PendingTurn` 增 `server_timing` 字段：stage 时从 `meta` 摘白名单键（§4a）                                                                                                                   |
| 8   | L3'   | rh2/src/repoharness2/adapters/slime/generate.py:493-536；contracts/capture.py:58-153            | `GenerationCaptureRecord` 新增 optional `server_timing` 子模型；:511 的 `raw_meta_info_digest` 照旧全量 hash，语义不变                                                                          |
| 9   | L4    | **（储备，无 F2 归属）**                                                                                | ~~trajectory.jsonl 脱敏导出~~——D1b 拍板前不可执行（六审 1）；V0 期间 CC 内部时间 = residual_estimate                                                  |
| 10  | L5    | FA-2B `PromptGroupState`/`PromptGroupAdmissionReport`（05 计划 :126-128）；FA-3 lease 状态机（:139-146） | admission report 加 optional timing 段；queue 结构补入/出队时刻                                                                                                                            |
| 11  | L1    | rh2/experiments/s1_7a_bringup/glue.py:508-525                                                  | `startup_evidence.json` 加 `timing` 段                                                                                                                                            |
| 12  | 预算统一  | **（D1b，无 F2 归属）**                                                                              | ~~deadline 起点切换~~——行为变更随 D1b 与 watchdog 数值同批（六审 1）                                               |


单一事实来源核对：全部 12 项中新增持久化面只有 #9 一处（tool_event_
ledger），其余全是既有结构加字段/加事件名。#9 是否新增由 owner 拍板
（§4b）。

---



## 4. 两个"能救就救"项的具体方案



### 4a. SGLang meta_info 计时字段保存

**现场**：SGLang 每次 `/generate` 响应的 meta_info 已带计时；slime 上游
已把它们列为 trace 键（reference/slime/slime/utils/trace_utils.py:18-44）。
RH2 当前在 generate.py:511 只存 `canonical_json_digest(dict(meta))`——
digest 只是 integrity/lineage fingerprint（可检测内容变化、关联血缘，不能单独"验证真伪"），且**不可逆**，计时事实等于丢弃。已结束的历史 rollout
无法恢复（§6）。

**保存哪些字段**（白名单 = trace_utils 键集，双向对齐 slime 口径）：

```text
必存 6 键（trace_utils.py:18-25）：
  prompt_tokens / completion_tokens / cached_tokens（prefix cache 命中量）
  queue_time / e2e_latency / decode_throughput
辅助 2 键：finish_reason.type、id（= request_id，已存另字段，留作交叉核对）
PD 分离部署才出现的 13 键（trace_utils.py:26-44）：
  pd_prefill_* 5 段、pd_decode_* 5 段、pd_transfer_speed_gb_s、
  pd_transfer_total_mb、pd_prefill_retry_count——单机 colocate 下缺省 None
```

**存到哪个既有结构**：`GenerationCaptureRecord` 新增 optional 子模型
`server_timing: SGLangServerTiming | None`（全字段 optional，
`measurement_source` 恒 `server_reported`）。摘取点在 capture_wire.py
stage 时（:560-578 构造 `PendingTurn` 处加一次白名单提取），commit 时随
`on_generate_response` 写进 record（generate.py:493-536）。delivered 的
`ModelCallAttempt.server_timing` 引用同一份值（或只在 capture record 存
一份、attempt 记 record_id——倾向后者，避免双写）。

**为什么不用现成的** `raw_meta_info_ref`（contracts/capture.py:116-119）：
该字段语义是"原始 meta_info **全文**引用"。全文含
`output_token_logprobs`（每 token 一对 [logprob, token_id]，2000 token
响应约 60KB JSON），会把已按 tape 存过的 logprobs（generate.py:512-514）
复制一遍；而存"删减版"到该字段 = 改字段语义 = T0（协议 §2"公共 schema
粒度"条）。新增 optional 字段绕开两个坑。

**体积估算**：每轮 6~~21 个数值键 ≈ 300~~500B JSON。P3 实测每 rollout
committed 轮数中位 4（min 1 / 单条最高观测 25，由 bringup_events 的
`weight_versions_engine` 长度重算）→ 每 rollout 约 1.2~12.5KB，对比
既有 token tape（int32/f64 逐 token）完全可忽略。

**分级**：T1 强报告（协议 §2："按已批准设计新增字段…= T1"；本提案获
owner/codex 通过即构成"已批设计"）。**归属**：FA-2A **F2-0**（capture
wire 从 experiments 提升进 src 时顺路，改动同一批文件）。

### 4b. CC `.harness/trajectory.jsonl` 容器删除前的脱敏保存

**现场**：`run_agent` 把 CC 全部 stream-json stdout 写到容器内
`{workdir}/.harness/trajectory.jsonl`（common.py:107-122）；评分 diff
排除 `.harness/`（swe.py 的 git_diff）；RH2 在 `_cleanup_container`
`docker rm -f`（generate.py:2195 起）前从不读它。codex 独立复核确认
"trajectory.jsonl 从未保存"。它是 L4 ToolTiming 的**唯一**数据源
（Pre/PostToolUse + 消息时间戳 + tool_use_id 都在里面）。

**时机**：`step3_harness_completed`（generate.py:1539）之后读出——终态
挂在静止屏障 `quiescence_confirmed` 之后（v3.2 D1a 第 4 条序列里"冻结
snapshot"一步的旁路产物）；FA-2A 屏障落地前的 bring-up 过渡位 =
`_cleanup_container` 调用之前。读取方式 `docker exec cat`（+ 5MB 上限，
超限截断并记 `truncated=true`），解析与脱敏全在宿主侧。

**脱敏必须删什么**（内容按不可信输入对待——该文件属 agent 用户可写）：

```text
- 全部自由文本：assistant text/thinking、tool_use 的 input 参数值、
  tool_result content、user/system 消息正文（含 --include-partial-messages
  的增量 delta）——即完整模型文本一个字节都不落盘
- 任何 env/凭据面：ANTHROPIC_AUTH_TOKEN（当前 = session bearer，
  claude_code.py:64；F2-2 身份/凭证分离前它就是会话凭证）、
  ANTHROPIC_BASE_URL、error message 原文（可能回显请求头）
- 文件路径参数：保守首版整删，只留字节长度（路径可能含任务泄漏面）
```

**保留什么**（白名单式提取，不是黑名单式删除）：

```text
event type / CC 事件时间戳 / uuid / tool_use_id / parent_tool_use_id /
工具名 / is_background / stop_reason / model 名 / usage token 计数 /
各字段字节长度统计（text_bytes=1234 这类形状信息）
```

**分级：建议按 T0 处理，owner 拍板**。理由：虽然"加一个观测产物"形状
像 T1，但 (i) 这是一个**新增持久化面**，内容来源于 agent 可写的不可信
文件——artifact 治理（哪些来自 CC 的内容允许离开容器落盘）此前的同类
决定都是 owner 级；(ii) 白名单本身是安全边界设计（协议升级规则 5 的
毗邻面），一旦有人日后往白名单加"看起来无害"的字段，须有一份 owner
批准过的基线可对照。**决策形状**（两案）：

```text
方案 A（推荐）：白名单脱敏保存（上表），T0 批白名单一次，
  之后白名单的任何扩项 = T1 强报告、删项 = T2。
方案 B：完全不保存（维持现状）——L4 层整层放弃，D1b 诊断的
  tool_execution / sandbox_idle_while_model 两个区间只能靠
  residual_estimate，精度显著下降。
```

**归属（六审 1 修正）**：L4 整层（trajectory.jsonl 解析/脱敏）为
**不可执行设计储备**——不属于任何 F2 切片；其三个 T0 候选随 D1b 批次
拍板后才产生实施归属。V0 期间 CC 内部时间一律 residual_estimate。

---



## 5. 分级与实施归属汇总


| 项                                           | 分级                               | 判据                                                                           | 归属批次                           |
| ------------------------------------------- | -------------------------------- | ---------------------------------------------------------------------------- | ------------------------------ |
| L2 timeline 新事件名 + phase_sink 参数            | T2~T1（报告一句）                      | 旁路观测，不改契约必填面；driver 协议是内部协议                                                  | **F2-0b**（F2-0 纯迁移不加字段） |
| L2 execution_audit 加原始 wall/候选区间两键          | T1 强报告                           | 按 **v4 已批** V0 口径只记原始区间（不派生 chargeable）                                  | **F2-0b**（字段）＋ F2-3（proxy 区间真接线）    |
| L3 `ModelCallAttempt` optional 区间字段         | T1 强报告                           | 公共 schema **加 optional 字段**（协议 §2 粒度条）；任何字段转必填 = T0 另议                       | **F2-0b**（V0 清单第 3 项；字段本身加在 F2-0b，proxy 四点区间真接线随 F2-3 request 归属重写同批填值） |
| L3' `GenerationCaptureRecord.server_timing` | T1 强报告                           | 同上；`raw_meta_info_digest` 语义不动                                               | **F2-0b**                       |
| L4 trajectory.jsonl 脱敏保存                    | **T0（白名单基线拍板）**                  | 新增持久化面 + 内容来自不可信域 + 安全白名单设计                                                  | **无 F2 归属**——不可执行储备，随 D1b 拍板后再定 |
| L4 数据用途限制（只诊断、不进判定）                         | T0 附带条款（写进同一决策）                  | 防止未来悄悄变成准入输入（拒绝路径偏置，升级规则 4）                                                  | 随上项                            |
| L5 admission report / lease 账本 timing 段     | T1 强报告                           | 按已批 FA-2B/FA-3 结构加 optional 段                                                | FA-2B（组）＋ FA-3（batch）          |
| L1 startup_evidence timing 段                | T2                               | 观测文件加键，无消费者契约                                                                | F2-0b 顺路或 FA-5                 |
| P1-5 落实：deadline 统一从 execution 启动起表         | **行为变更（非观测）**                 | 改变超时分布（六审 1）——与 watchdog 数值同批 | **D1b**（已从 FA-2A 移出）       |
| **预算判定切换到 chargeable 时钟**                   | **T0（v3.2 未定案的残留，见 §7）**         | 改变拒绝路径分布与终止语义（升级规则 1/4）                                                      | 决议归 D1b；实施 FA-5 前              |
| 熔断/告警若引用新计时字段                               | 数值阈值 = T0 预注册（决策 4 既定）；统计口径 = T1 | 决策包 D4 待定参数条                                                                 | FA-2B/FA-5                     |




## 6. 显式"不做"清单

1. **不做跨进程时钟同步**（不引 NTP/PTP 精化、不估钟差矩阵）。域 2/3 的
  时间只以 duration 或 correlated 形式进账；epoch 只作展示。
2. **不精确分摊 continuous batching 的 GPU 时间**。`queue_time /
  e2e_latency` 是"该请求视角"的服务器自报值；共享 kernel 的逐请求
   GPU 占用不可得，也不派生"GPU 秒"类字段。
3. **并行 subagent / 并行工具时间不相加**。任何"总工具时间"只允许区间
  并集口径（与双时钟同一算法），Σduration 会超过 episode 墙钟。
4. **CC 黑盒内部不做进一步分解**。规划/调度/bookkeeping 只有
  `residual_estimate` 一个口径，不假装更细。
5. **L4 永不进入准入/预算/reward 判定**（不可信来源硬约束）。
6. **不回填历史 rollout**。meta_info 只剩 digest（单向），
  trajectory.jsonl 已随容器删除——P3 及之前的数据按现有粗桶使用。
7. **不改** `reference/slime` **上游**（`_await_done_marker` 的 5s 轮询过冲、
  超时不杀进程组等问题不在 slime 侧修）：轮询过冲由 L2 的
   `cc_process_spawned`/`harness_done_marker_observed` 事件让账目可解释；
   "杀不干净"由 v3.2 静止屏障（RH2 侧）根治。改上游 = fork 维护面
   （升级规则 6），且非必要。
8. **首版 non-chargeable 只含权重更新暂停 + 系统反压**（v3.2 D1a 第 3
  条定案），安装/chown/评分等其他阶段先观测不扣除；扩大扣除面 =
   改预算语义 = T0 再议。
9. **不新建独立 timing 服务/数据库**。全部计时随既有 evidence 文件
  （execution_audit / capture record / admission report / startup
   evidence）走，禁止第二账本。



## 7. 与决策包 v3.2 的冲突点 / 建议升 T0 的残留问题

1. **"预算判定用 chargeable 时钟"何时生效未定案**（v3.2 D1a 第 3 条写了
  口径，没写切换时机与载体）。现状三个预算执行点全是 wall 口径且各自
   起表（时钟 C sandbox.py:71、时钟 D capture_wire.py:203、attempt 级
   async_worker.py:843-850）。把判定改为 chargeable 会改变哪些 execution
   被判超时/缺员——拒绝路径分布变化，T0。**建议决议**：FA-2A 全程
   audit_only（只记录、只派生、不改判定）；预算判定切 chargeable 与
   watchdog 数值同批在 D1b 拍。
2. **统一 deadline 的数值语义待补**（P1-5 实施细节，建议随上项一并拍）：
  deadline 从 execution 启动起表后，600s 预算是否应改为"chargeable
   600s"或"wall 600s + 安装/chown 不计入"——两种选择对 chown 慢的任务
   （django 类，+470s）产生完全不同的截断偏置。v3.2 未覆盖。
3. **exit=-1 后评分窗口与静止屏障的现状冲突**（§1.2 第 2 点）：时钟 C
  超时不杀 setsid 进程组，bring-up 链在 workspace 未静止时就走
   drain/装配/评分。v3.2 D1a 第 4 条已定方向，本提案补充其机器可查证
   据面（`quiescence_confirmed` timeline 事件 + 无此事件不得出现
   grading 事件的账目断言）——属实施提醒，非新决策。
4. `hard_wall_timeout` **的判定来源**：v3.2 说它"恒按非策略结果处理"，
  但当前唯一的 hard-wall 信号是时钟 C 的 exit=-1，而 §1.2 证明它混入了
   0~480s 基建前奏。若 D1b 用"成功轨迹 P90/P95"定 watchdog 数值，必须
   用 L2 拆桶后的 `cc_process_spawned → done_marker` 段（或 chargeable
   段）为基准，不能用 `harness_run_seconds`——建议在 D1b 决策包里显式
   写死这一口径，防止数值校准建立在混合桶上。
5. **L4 白名单**（§4b）：新增持久化面 + 不可信来源内容出容器，建议 T0
  拍白名单基线与"只诊断"用途限制。
6. 非冲突确认一条：v3.2"同一 owner 做并集"在现拓扑下可行——proxy
  （adapter 线程）与编排 loop 同进程（域 1），monotonic 可比；真正跨
   进程的只有 CC 与 SGLang，均以 server_reported/correlated 进账，
   不参与并集运算。

