# #1/#2 启动修复：IR1–IR3 针对性复核

2026-09-24，Codex A。审查提交 `8f790df6e2db485c100b2cee27a462833f8ba6fb`；工作区中 B 线在制品未改动。承接[上一轮报告](codex_implementation_review_20260924.md)，只复核修复及其直接接缝。

**结论：原 IR1 的执行终态、IR2 的异常审计运输、IR3 的短写计数均已修复。没有新的 P1；还有两项日志 P2，应在本片补齐后再标记 #2 全部收口。无需新增用户决策，#3 复现和后续决策包可以并行推进。** 两项均不要求修改 reward、预算、模型输出准入、容器停止 owner 或训练表示。

## 1. 原问题的裁定

| 原问题 | 本轮结论 | 独立核对 |
| --- | --- | --- |
| IR1：CLI 退出被当作 CC 已结束，且宿主负码撞内部码 | 通过 | create → start → inspect 关联同一 exec ID；仍运行、查不到或退出码非法不给正常退出码。起流故障走 bootstrap 失败，失去执行终态走既有 typed 连接故障。真 Docker 用例覆盖正常 0/3、容器内 SIGINT=130、外部 kill=137、未启动、超时与取消。正式编排 cap 有/无的 typed 故障均不评分 |
| IR2：异常/取消时持久 audit 没有日志引用 | 运输修复通过 | progress 在收集前挂入 launch facts，collector finally 发布，编排 finally 吸收。正常、typed、外层期限的落盘用例通过；poison/关停共用取消收口，未另造多套同构夹具。**引用所指文件的隔离仍有 F1** |
| IR3：短写计数虚高且误报完整 | 通过 | 按 `write()` 实际接受字节累加；真实 `RLIMIT_FSIZE=4096` 的 8192 B 输出只计实际 4096 B，并标写入失败。正常双流与短写正反控通过。**流本身的完整性仍有 F2** |

本轮没有再引入 CLI stderr 推断、CC `result` 准入或进程数量猜测。收集器只关闭连接，容器内进程仍由既有编排收口；源代码追踪与相关取消用例没有发现这一责任链断开。

## 2. F1 / P2：真实评测身份在日志目录中被截断，文件仍会覆盖

**位置与行为**：`generate.py:3957–3967` 的 `_harness_log_dir()` 对 execution 和 physical attempt 两层都调用 `_sanitize_for_name()`；该函数在 `2431–2433` 把结果截到 **24 字符**。新增末级目录不能自动带来唯一性。`docker_sandbox.py:423–429` 本次改成 `wb`，同名文件会被重新截空。

**实际生产身份**：miles 的 `inference_rollout_eval.py:52` 用 `uuid4().hex[:12]` 生成评测点；RH2 的 `identity.py:372–382` 生成以下合法身份：

```text
execution 0: eval-0123456789ab-d0-p0_m0
execution 1: eval-0123456789ab-d0-p0_m1
attempt 0:   eval-0123456789ab-d0-p0_m0#p1-<uuid8>
attempt 1:   eval-0123456789ab-d0-p0_m1#p1-<另一 uuid8>

两者最终目录都为：
<artifact_dir>/eval-0123456789ab-d0-p0_/harness/eval-0123456789ab-d0-p0_/
```

成员编号及整段 attempt 后缀均消失。即使每题只评一个样本，prompt index **100 与 101** 也会一起截成 `…-p10`，仍碰撞。这是当前评测形态可达的命名问题，不依赖引入评测重试或特殊 Docker 配置。

**反例证据**：[探针](ir_followup_20260924/falsifier_attempt_path_collision.py)、[结果](ir_followup_20260924/falsifier_attempt_path_collision.json)。运行真实 `mint_eval_attempt_identity`、`mint_attempt_identity`、目录函数及 `_open_log`；Sample 外壳用 `SimpleNamespace`。主审独立重跑确认：依次写入 `slot0 log`、`slot1 log` 后，前一条 audit 路径下只剩 **slot1 的内容**。并发写入也没有文件隔离保证，但本轮没有把并发混写当作已实测事实。

**不变量、影响与范围**：一个 audit 应指向该次尝试的日志。现在两个 audit 可指向同一文件，影响评测失败归因、请求/动作核查和后续基座诊断；没有证据表明模型 capture 或 reward 随此混样。P2，`reachable`。所测训练 group 0、1、1000、1,000,000 的真实 ABORTED→retry 均不碰撞，不能泛称训练重试普遍受损；同 eval execution 再铸造一个 physical ID 的附加反例也**不代表当前 miles 已实现 eval retry**。

**本片最小修法**：日志路径使用能区分完整 physical attempt 身份的文件名，例如日志专用的可读前缀加完整身份摘要，或适当编码的完整身份。不要修改仍用于容器命名的共用 `_sanitize_for_name()`，不要追加文件一致性闸门。消费者继续按 audit 中的实际路径读取。

**验收**：用真实 minter 覆盖同题两个评测 slot、单样本评测的 prompt 100/101、同 execution 的不同 physical ID；两次写入后各自内容与字节计数仍可独立回读。保留正常训练身份正控即可，不需重跑真实 CC 或整套环境筛查。

## 3. F2 / P2：明确不完整的帧流仍被标为完整日志

**位置与行为**：`docker_sandbox.py:337–377` 把不完整帧头、payload 或 chunk 提前 EOF 当作普通结束；部分路径没有设置 `source.error`。即使已记录流错误，`595–599` 的最终 `log_complete` 也只检查 `exited` 与文件写入错误。

**独立反例**：[Unix 假 daemon 探针](ir_followup_20260924/probe_stream_completion.py)、[结果](ir_followup_20260924/stream_completion_results.json)。从真实收集器执行完整 create/start/inspect，每案先发送完整 `good\n`，同一 exec 的 inspect 均返回 `Running=false / ExitCode=0 / Pid=123`：

| 流 | 当前 `log_complete` | 当前 partial / stream_error |
| --- | --- | --- |
| 完整 raw 帧（正控） | true | null / null |
| 下一帧只交付 3 B 帧头 | **true** | null / null |
| 下一帧声明 9 B payload，只交付 3 B | **true** | null / null |
| 完整 chunked（正控） | true | null / null |
| chunked 缺少终止块 | **true** | null / null |
| 后续 chunk size 非法 | **true** | null / 已有 ValueError |

**不变量、影响与可达性**：执行完成事实和日志完整性是两个事实。连接在一帧中途断开，进程随后退出，inspect 得到退出码是合理的；但已知缺失的输出不能标成完整。属于现有运输故障分支下可达的日志错误，CPU 故障注入已证实；没有测量真实训练中的发生频率。P2，不推导出应该拒绝样本。

现有 reset 维护用例的 inspect 一直 `Running=true`，因此由 `exec_state` 把日志标为 partial，掩盖了“坏流 + 可信终态”组合。作者对抗表 D13 修的是普通 HTTP 响应体，不等于 `_FrameSource` 的这些流分支也已覆盖。

**本片最小修法**：区分可观测的帧边界正常 EOF 与帧截断；对已有流错误和截断记录 partial，纳入 `log_complete`。完整性只能表达到收集器可观测的范围，不要为证明每一字节都到达另建校验协议。**保留 inspect 证明的退出码和原训练/评分处置**。

**验收**：补“坏流 + 已退出”的日志反控，保留“完整流 + 已退出”和“流断 + 仍运行”两类已有正控。无需重新做 daemon 重启、几百次竞态或八卡实验。

## 4. 非阻塞的小建议

`_await_exec_terminal()` 的每次 inspect 仍传完整 `settle_seconds`，而非剩余量，所以目前不是严格的“总共最多 10 秒”。限定 reviewer 的缩短时间 CPU 探针中，名义 0.45 秒等候实际约 0.85 秒。正式编排外层绝对期限仍可取消它，未据此发现训练预算被绕过或执行完成误认，**不列为本轮收口阻塞项**。可在同函数顺手改为剩余时间，也应避免文档继续把经验值写成严格总上限。

特殊 `DOCKER_HOST`/context 组合没有当前部署触发证据，不扩大成新配置平台。未知帧类型或超大帧也不重开本轮已接受的可信 daemon 边界。原始套件已覆盖本轮执行终态，不因测试规模大或 token 消耗高而提升证明强度。

## 5. 验证与证据边界

主审实际重跑：

```bash
# 从 rh2/ 执行
.venv/bin/python -m pytest -q tests/adapters/test_startup_fix_1_activation.py tests/adapters/test_startup_fix_2_host_collected.py tests/adapters/test_startup_fix_2_engine_exec_docker.py
# 68 passed，含 8 个真实 Docker 用例
.venv/bin/python -m pytest -q tests/adapters/test_budget_deadline.py tests/adapters/test_w3b_sandbox_profile.py
# 89 passed
```

合计 **157 passed**。改动源码、三份直接测试和新审查探针的 ruff，以及提交 diff whitespace 检查均通过。按审查标准由 Production Tracer / Falsifier 做限定交叉核对，主审复现两项保留意见。

回读了作者 `acc3_*` 与最终代码的 `acc4_normal/attempt.json`、`acc4_time_budget/attempt.json`：后两案日志、inspect 终态/仍运行与期望吻合。作者真实 CC 证据仍是 driver 验收；不能把它写成完整 orchestrator、RH2 403 cap、真实 SGLang 或 GPU 训练验证。`acc4` 两案没有走正式长评测身份，不能据此排除 F1。

本轮未重跑远端、真实 CC、全库、双 lane 或 GPU，也未改 daemon、机器生命周期、生产代码、维护测试、fork 或 B 线在制品。作者全量与远端结果仅作为复用证据。只新增本次审查工件，追加 Brief 指针和 infra 记录；未提交、push 或向外部 Claude/B 发送消息。

**停止条件**：F1 的真实身份隔离与 F2 的部分日志标记补齐，现有终态/取消/短写正控保持，即可结束 #1/#2 的这轮修复。没有新的 T0；不应把日志问题扩展成样本拒绝、训练语义重审或大规模测试工程。#3 复现与 #6/#8/#9/#10 决策包现在即可并行。
