# 第二次窄复核：Production Tracer

**结论：R1 的生产路由安装缺口与 R5-F1 的 drain 回归均可关闭。本角色未发现新的阻塞问题。** 新增启动核对在正常生产构造路径通过，明确绑定旧 handler 时会在启动 HTTP 线程之前拒绝；当前固定的 vendored adapter 没有发现会被它误拒的合法配置路径。

复核 `3d0bca0c` → `6b33efee38d2b0d785983e44136dccbdd9c49a60`，2026-09-09；主责 `5192356f`、`f9f6c27b`。已读当前 `project1_execution/tmp/claude修复.md` 和对应 diff。只核 R1 与 R5-F1，未重开 B、R2、R4、旧 R5 全面审查，也未审作者的僵尸进程提议或 R3；后两项由主审负责。开始及收口时源码、维护测试的工作树 diff 均为空。

## R1：真实服务入口已使用等待包装

生产路径是 `BringupService.__init__` 的 `install_capture_wire`（`bringup.py:1073`）→ 构造 `AnthropicAdapter`（1074）→ `BaseAdapter.__init__/_register_routes`（`rh2/src/slime/agent/adapters/common.py:175`、`anthropic.py:49`）→ POST `/v1/messages`。现在安装发生在构造之前，路由直接保存 `rh2_run_turn` 的绑定方法；起线程前的核对在 `bringup.py:1094–1097`。这关闭了“实例当前方法已包装，但已登记路由仍调用旧方法”的实际缺口。

[production_route_probe.py](production_route_probe.py) 的六案各启一个干净 Python 子进程。每案构造前都断言实际类方法仍名为 `_run_turn`、两种 wire 的 registry 均未绑定，随后调用真实 `BringupService` 构造器，使用缓存 tokenizer 和真实 HTTP 线程。五个正常构造案都向服务实际监听端口发请求，实际模块为 `rh2/src/slime/agent/adapters/common.py`；没有再另建一个“先安装再构造”的测试 app 代替生产入口。

| 对照 | 实际服务端口的结果 |
|---|---|
| N 已生成，再发 N+1，cap=1 | 生成释放前无 403、无预算通知；最终 200/403，一条完整 capture、一条叶，叶 response tokens=`[7,8]`，身份绑定=1 |
| 两个分块 body 交错，cap=1 | 同样等已接纳轮完成才拒绝；完整 capture=1，无 poison、无 abort |
| cap=3，同时 5 个请求 | 释放前引擎已有 3 个并发请求，2 个待拒请求尚未返回；最终 200×3、403×2，完整 capture=3；两次预算通知均发生于 capture=3、已接纳 inflight=0 |
| 取消一个待拒请求 | 已接纳请求仍完成，另一待拒请求返回 403；capture=1、无 poison、abort=0 |
| 取消已接纳请求 | 保留 `client_cancelled`、abort=1、capture=0；新请求被 `rh2_session_poisoned` 拒绝，预算通知没有清除 poison |
| 故意使真实构造器登记旧 handler | 实际抛 `StartupCheckError(turn_budget_wire_not_bound_to_route)`；`rh2-anthropic-adapter` 线程数量=0 |

并发对照也保留旧断言：裸 internal SID 不能代替 capability；完成后的 REVOKE 继续拒绝新请求。所有实际 HTTP 线程最终停止。结果为六案 exit 0，见 [production_route_result.json](production_route_result.json)。

**启动核对的必要性与复杂度。** `capture_wire.py:1000–1029` 检查三件具体事实：当前类方法是预算包装、目标 POST 路由存在、handler 同时绑定本 adapter 和当前函数。它在既有启动链中核对一个固定路由，不新增运行状态、恢复所有者或训练样本剔除语义。此次正常服务、cap=1/3 均通过，故意重现旧绑定才拒绝。函数名字符串是额外的重构耦合，未来包装改名时须同步；当前 pin 的生产类和路由固定，没有已建立的合法扩展路径会被误拒，不据此提出额外阻塞或要求删掉核对。

**证据边界。** 服务采用 `fa_audit_only` 的冻结本地任务面；路由安装及核对在模式/任务面分流之前，与 `fa_formal` 共用。未调用 `async_start` 中的 Docker/API 检查，而是用该阶段同一个 `build_production_model_call_proxy` 工厂接上内存生成 IO。HTTP handler、capability guard、预算包装、proxy、capture/轨迹交付都真实执行；生成和 abort 的远端 IO 为替身。这里证明实际服务入口与必要并发语义，不宣称完整 formal 服务启动、真实 CC 处理 403 或参数更新已执行。

## R5-F1：排空后再撤 worker，原取消收口不回归

`queue.py:166–170` 现在先等 `queue.join()`，再设 `_closing=True` 并取消 worker。`drain=False` 跳过 join，仍立即设关闭标志，保留上一轮 ScopeError 覆盖取消后 worker 必须退出的修复。服务生产入口（`bringup.py:1967–1978`）先关闭评分准入，继续使用 `close(drain=True)`；超过既有上界才退为 `drain=False`。此次没有增加第二个队列状态机或改动外层关停策略。

[production_queue_probe.py](production_queue_probe.py) 复用上轮两个积压反例的设置和真实 service 评分队列步骤：一个 worker、两个已接受 item，第一个在 grade 中暂停，第二个排队。提交者仍在与两个提交者均已取消两案，都在释放第一个后完成两个 grade，`drained_within_timeout=true`、queue depth=0、worker 列表为空。配置 drain 上界仍是旧探针的 0.2 秒；实测约 0.011 秒，未耗满上界。

另外原样调用上轮的三个实际 manager→queue→generate/service 对照：

- 提交者取消后，真实 manager 产生的 scope 失败经带外 sink 到达 service 一次；
- 关停已开始时，该失败记入真实关停报告的 `run_fatal_during_shutdown`，仍只有一次；
- `close(drain=False)` 取消 worker，finally 产生 scope 失败后，等待的 generate 收到一次 fatal，带外 sink=0，close 与原 worker 均完成。

五案 exit 0，见 [production_queue_result.json](production_queue_result.json)。没有重跑已关闭的全部 R2/R4 状态矩阵。

## 与旧探针相比的有限调整

旧文件和旧结果均未修改。

1. R1 复用 `cap_body_race_probe.case` 和 `cap_wrapper_followup_probe.new_wrapper_case` 的请求动作。把其 TestClient 传输适配为真实服务端口；替身释放信号用线程安全事件，以配合实际后台 HTTP loop。旧独立 app 的安装顺序不再作为生产入口。顺序/分块 body 的“提前拒绝”坏结果断言改为等待完整交付；正常并发、待拒取消、poison 的既有断言保留。新增一案在真实构造器中登记旧 handler，专门验证新增启动核对的 typed 拒绝及线程未起。
2. R5 的 `drain_case` 是上一轮最小副本。旧同步点“等 `_closing=True` 才释放第一个 grade”已过时，会人为让修后 drain 一直等；改为观察实际 service 已关闭评分准入，再让出 0.01 秒并断言 worker 仍活着、close 尚未结束、`_closing=False`。结果断言从旧坏结果改为两个 item 完成、队列清空、及时排空。三个取消 fatal helper 没改，只把临时产物根目录指向本轮目录。

仓库根目录执行命令：

```bash
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/followup2/production_route_probe.py
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/followup2/production_queue_probe.py
```

本角色只新增本目录的报告、探针和结果；未改业务源码、维护测试、共享 Brief/infra、旧工件或 git，未运行全量测试及真实 Docker/CC/API/GPU 作业。停止于 R1/R5-F1 关闭证据与必要回归，整体批准由主审汇总。
