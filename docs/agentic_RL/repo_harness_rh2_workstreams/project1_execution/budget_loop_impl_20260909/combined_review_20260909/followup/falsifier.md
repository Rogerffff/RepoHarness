# 预算修复针对性复核：Falsifier / Simplifier

审查基线为 `04f599f82d5eef4a808fab001f295896ebed5efa`，复核版本为 `3d0bca0cb0e60c049ac4d80b844ddc851cea640e`。本子审主责 `1d9359f4` 的 R1 包装和必要回归，另按主审指定交叉核查 R3 停止事实。已回读作者 `project1_execution/tmp/claude修复.md`。源码与维护测试没有本轮未提交差异，版本指纹见同目录 `review_snapshot.json`。

**R1 尚不能关闭：新等待包装本身通过必要并发对照，但生产启动先构造 adapter、后安装包装，已绑定的 HTTP 路由仍调用旧方法。R3 的指定反例也成立：kill 命令返回时刻不能代表实际停止时刻，命令失败且墙后仍有进程时仍可得到 KEEP_FULL。** 两者均沿原 finding 收口，不新增编号，不扩展 B 或整条关停链。

## 1. R1：包装未进入生产已绑定的路由（P1，原项未关闭）

### 当前行为和生产可达条件

`rh2/src/repoharness2/adapters/slime/bringup.py:1069–1077` 先构造 `AnthropicAdapter`，再调用 `install_capture_wire`。构造器在 `rh2/src/slime/agent/adapters/common.py:175` 调用 `_register_routes`；`anthropic.py:48–50` 随即把当前绑定方法 `self._run_turn` 注册到 POST `/v1/messages`。

新代码在 `capture_wire.py:1081–1109` 替换类方法，但不会替换 aiohttp 路由已经保存的绑定方法。独立探针按这一生产顺序构造真实 vendored app，观察到路由 handler 为 `_run_turn`，实例当前方法为 `rh2_run_turn`，两者 `__func__` 不同。实际 HTTP 请求也确认没有经过新等待。完整 BringupService 的 renderer、模型加载和资源启动未在本子审中执行；启动顺序与绑定规则由真实源码和真实 app 的运行结果共同定位。

触发条件是新进程第一次启动共享 adapter；不需要畸形输入或测试专用配置。若同一解释器已提前安装 wire，再创建 adapter，会自然遮住此问题。新补丁已经删除旧 guard 中的等待，因此当前生产入口不仅保留旧 body 交错窗口，连“第 N 次已在生成、再正常发送 N+1”也会立即拒绝。

### 不变量、实际影响和分期

已接纳的行动机会应在预算拒绝触发收口前完成交付。当前入口在第 N 次仍生成时发送第 N+1 次，即刻返回 403 并通知预算命中；通知时 capture 和轨迹树仍为 0。等待客户端保留连接的对照最终仍有完整 capture，说明过早拒绝并不必然丢数据；收到拒绝后关闭在飞连接的对照则得到 `client_cancelled`、一次 abort、零 capture。

真实 CC 二进制对该响应的退出行为仍未验证，不能把替身客户端行为表述为已跑过真实 CC。过早的预算事件与其启动编排宽限的接缝则确定存在。这是原 R1 的在飞交付保护未抵达生产入口，并引入顺序请求回归；影响是可能把正常预算截断变成缺员，不是多采一轮或把坏 token 放入训练。发生比例未测，不能降为仅需登记的诊断风险。本次没有重跑完整 buffer 链；旧版真实消息→轨迹→准入影响证据保留在上级目录的两个旧 cap 探针及报告，未改写它们。

### 窄复现和反证对照

新 `cap_wrapper_followup_probe.py` 复用旧 `cap_body_race_probe.py` 的请求动作，不执行旧主函数、不修改旧文件。使用真实本机 aiohttp、vendored app、capability guard、生产 proxy、capture hook 和轨迹树；只用内存替身阻塞/返回 SGLang IO。server 启用生产相同的 `handler_cancellation=True`。

最终退出 0，共 **7 组观测：1 组路由事实、6 个 HTTP 生命周期案例**。主审独立重跑结果见 `cap_wrapper_root_rerun.jsonl`。

| 观测 | 关键结果 |
| --- | --- |
| 生产构造顺序的路由身份 | 路由是旧 `_run_turn`；实例方法是 `rh2_run_turn`，不是同一函数 |
| 生产顺序、N 已生成后发 N+1 | 释放生成前已有 403 和预算通知，capture=0；继续等候后得到 200/403、1 个完整 capture 和叶 |
| 生产顺序、两个分块 body 交错、收到拒绝后断开 | 提前拒绝；capture=0，`client_cancelled`，abort=1 |
| 先安装再构造、同样的分块 body 交错 | 生成完成前没有 403 或预算通知；最终 200/403、1 个完整 capture、无 poison |
| 先安装再构造，cap=3、同时发 5 个请求 | 释放前 3 个引擎请求同时在飞、2 个拒绝请求等待；最终 200×3、403×2、3 个完整 capture；每次预算通知时已接纳 inflight=0 |
| 一个待拒请求被客户端取消 | 最后一个已接纳请求仍完成；另一个待拒请求正常 403；capture=1、无 poison、abort=0 |
| 已接纳请求被客户端取消 | 保留 `client_cancelled`、abort=1、capture=0；待拒响应未清除 poison，新请求被 poison guard 拒绝 |

这些对照反证了“必须把同一 session 的正常生成串行化”及“多个待拒请求必然互锁”：包装正确安装时，只等待 vendored 已接纳请求集合，正常生成并发保持。取消已接纳请求的案例仍会在该请求退出后发出 cap 通知，但 poison 保留；不能把 cap 当成其它失败的豁免。

### 真实 body、认证与 capture 路径的边界

`capture_wire.py:959–970` 在调用下游 handler 前完成 capability 对应的 `request.clone`，随后新包装才读取 body。真实 HTTP 对照没有出现“读取 body 后不能 clone”的故障。新包装读取后的原 `_run_turn` 再次读取的是缓存 body；到同步 `_check_turn_cap` 的接纳计数之间没有新增 await。当前 Anthropic `_session_id` 只从已重写的请求头取 SID，不依赖预处理后的 body。

`common.py:331–338` 在通过 cap 后才加入 vendored inflight；`common.py:359–393` 在响应 flush、`record_turn` 完成后才移出。新等待使用这个集合而不是包含自身和其它待拒请求的 registry inflight，因此上述多个等待者能退出。

新增并发案例同时验证：裸 internal SID 不能替代 capability，立即得到 `rh2_unknown_or_closed_session`；正常请求完成后 REVOKE 仍拒绝新请求；已有 poison 对新请求仍优先生效。动态 REVOKE 对照是在在途请求完成后执行，未声称遍历了等待中撤销的所有交错。本次已覆盖必要新增包装回归，没有因此扩大生命周期审查面。

### 测试盲点、最小修法和验收

维护测试 `rh2/tests/adapters_miles/test_budget_loop.py:210/225`、`:720/725`、`:821/826` 均先安装 wire、后构造 adapter；其中新增真实 buffer 测试的消息链是实测，但其启动顺序仍不能覆盖生产入口。给 helper、capture 或 buffer 加更多相同安装顺序的测试不能消除此盲点。

最小修法是把现有 `install_capture_wire(self.registry)` 移到 `AnthropicAdapter(...)` 构造之前，让现有注册机制直接拿到正确 handler。无需新增状态机、改 vendored 字节或事后修改 aiohttp 私有路由表。现有 `ensure_no_404_middleware` 是幂等补装，保留即可；同一段已有“构造器 patch 对已创建 app 无效”的注释，也说明这是现成启动顺序问题。

窄验收应从干净解释器使用实际生产安装顺序，确认 POST 路由绑定新包装，并通过顺序在飞、分块 body、多个拒绝等待者三个关键对照；保留已验证的正常并发、真实 capability、capture 和 poison 路径。修复应改变安装顺序而不是削弱拒绝/poison/准入 oracle。此项不需要新的 owner 训练语义决策。

## 2. R3：kill 返回不是停止事实（原 P1 的交叉反证）

### 源码和真实可达条件

`execution_scope.py:72` 丢弃 kill 返回的 `ExecResult`，随后 `:77` 无条件记录 `kill_returned_at`。归零轮询会在 `:92–95` 用最后的 0 覆盖先前正数结果。`generate.py:3835–3845` 仅凭 `kill_returned_at <= deadline` 判定墙前已停止，从而返回 `HARNESS_EXIT_STOPPED_BY_RH2`。这与同文件注释所说的“不是把已发出 kill 当已停止”不一致。

默认 Docker workspace 会原样返回 Docker exec 的退出码，非零退出不自动变成 Python 异常。因此“kill 命令因 exec 失败返回、容器内进程仍活着、稍后自然结束或其它收口使其归零”属于当前生产可达条件。它不要求新建异常 producer。`KILL_SCRIPT` 末尾的 `; true` 还会屏蔽容器内 pkill 的退出码；本轮强反例直接使用 Docker exec 的非零结果，不依赖该额外推论。

仅凭任意一次正进程数不能断言进程仍在执行用户代码：僵尸或墙前查询的晚回包都可能产生相同表象。本结论以 kill 明确失败、受控 IO 中仍有活进程的事件时序作为反例前提，并由主审补充墙后再次发起查询排除晚回包解释；不声称已经在真实 Docker 上测得这一故障。

### 两层证据与影响范围

独立新脚本 `stop_return_fact_probe.py` 运行真实 `terminate_agent_processes`，仅替换 workspace IO 和 episode 观测钟，共 2 案、退出 0。它不运行 formal 编排；输出的消费布尔值直接复制当前消费谓词，用于明确 helper 产物会怎样被解读：

- deadline=900；kill 在 899.5 返回 exit_code=1；COUNT 在 900.1 为 1、901 为 0。helper 返回 verified=true、kill_returned_at=899.5、confirmed_at=901，当前谓词仍判墙前停止。
- 对照把“实际在 899.5 停止”设为 IO 夹具前提，仅让 kill 回包晚到 901，得到相反布尔值。该前提不是 helper 可观测事实；此案说明观测不足，不要求实现凭空猜测墙前已停，也不另报一个新缺陷。

另已回读主审 `stop_facts_probe.py` 和 `stop_facts_probe.jsonl`：真实 formal 入口→真实停止 helper→真实屏障→实际交付的 `AdmissionPayloadV1`→`decide_member_disposition`。kill 失败、墙后仍有进程、901 才归零的反例最终为 `max_turns_exhausted/present_truncated`，评分 1 次，处置 `KEEP_FULL`。这证明错误停止归因到达实际准入消费；该夹具没有盖 miles sample 身份，因此是实际 payload 的处置结果，**不是新一轮真实 buffer 或参数更新复现**。

同一根探针的墙前正常停止、停止动作于墙后才生效、仅归零确认晚到三个对照分别得到 KEEP、DROP、KEEP，说明补丁修复了旧单一时序，但新判据仍不能覆盖已有的命令失败路径。挂起/父取消的 R2 结论由主审负责，本子审不借此重新审查。

### 最小修正边界和验收

沿现有 stop 结果修正即可：不要把命令返回填成“已停止”的凭据；至少不能忽略非零 kill 结果，也不能让墙后正数观测被最终归零完全抹去。最终屏障证明“现在安全了”，不反向证明“墙前已经停了”。保持对真实 deadline 的既定 DROP 规则，无需设计新的 session 平台。

不能简单改成最终 `remaining < 0` 或仅用晚到的 `confirmed_at` 判越墙，那会把只是确认慢的对照也改判。对现有 IO 无法识别的实际停止时刻应保留证据边界；不能以“只加一个时间字段”悄悄把已批语义改为命令回包时间语义。

窄验收至少包括 kill 失败后墙后再次确认仍活、最终才归零的反例，并保留墙前成功停止、墙后才停止、墙前停止但确认晚三个对照。验收查看实际 Outcome 与准入处置，不能只断言返回时间字段存在。仍归原 R3，不扩为 I13/I16、未来期限或全 shutdown 问题。

## 3. 执行和收口

本子审新增两个 CPU 探针和本报告；没有修改业务源码、维护测试、旧探针/结果、Brief、infra、git 或共享主报告。没有调用真实 Docker、CC、模型 API 或 GPU，也未重复全量测试。

从仓库 `rh2` 目录运行：

```bash
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/followup/cap_wrapper_followup_probe.py
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/followup/stop_return_fact_probe.py
```

两项均已退出 0，断言用于复现当前行为，不是宣称当前源码已修好。主审独立重跑的 cap 输出另存于同目录，没有覆盖旧工件。本子审至原 R1 与指定 R3 反例及必要对照收口；预算数值、Brief §6 六项、`owner_cancelled` / `agent_violation` 保持既有边界。
