# #1/#2 启动修复实施复核

2026-09-24，Codex A。审查提交 A `47755976`、B `56d22d71`、验收记录 `9379af1d`；主审时 HEAD 为 `9379af1d`。工作区中 B 线在制品保持原样。

**结论：#1 的激活与逐 execution 注入可以接受；#2 的方向接受，但暂不标为审查通过。剩余 1 项 P1、2 项 P2，均属于此前 SR2/SR4 已要求的执行完成事实和失败日志运输，没有新用户 T0。** 修复集中于宿主执行/收集与审计接缝，不重开 reward、turn-cap、hard wall 或模型输出准入规则。

## 1. 已落实的内容

| 边界 | 本轮裁定与证据 |
| --- | --- |
| SR1 单例与逐题状态 | 接受。`launch_claude_code` 是无状态函数，env、路径、期限经参数运输，未塞进 `ClaudeCodeHarness` 单例。新增并发用例通过 |
| SR3 激活位置 | 接受。新增解释器检查在首次 census 之后；原安全 prelaunch 保持原位。HOME/BASH_ENV 在 Bash 启动前传入，激活脚本/期望前缀取自任务规格 |
| 只读激活文件 | 接受。`/rh2` 0755、文件 0644；本轮真容器维护测试覆盖 agent 可读不可写及 Bash 环境生效 |
| 容器内 RH2 日志与退出标记 | 接受删除。新路径不再调用 vendored `run_agent`，不再创建 `.harness/trajectory.jsonl`、`/tmp/.run.sh`、`/tmp/.run.done`。未修改 vendored 目录 |
| 正常日志与审计 | 接受正常路径。两路输出分别写宿主文件，正常返回时 audit 可回读路径；作者真实 CC normal 证据中解释器、3 次请求与 message_start 数吻合 |
| 超时/取消的宿主资源回收 | 本轮窄探针可正常回收、未见读取任务残留；容器内停止继续归现有 owner。日志事实缺失见 IR2。不把“尚未复现挂起”写成所有反压条件的证明 |
| SR2 执行完成事实 | 尚未闭合。Docker 客户端返回值不能直接等同于容器内 CC 的结束事实，见 IR1 |

## 2. IR1 / P1：Docker 客户端已退出，不等于本次 CC 执行已结束

**当前行为 / 不变量**：`docker_sandbox.py:177–187` 根据宿主 CLI 的返回码与 stderr 尾部推断 `container_process_exit`；`284–287` 原样把它作为执行退出码，`bringup.py:440–446` 仅对 `docker_cli_error` 抛已登记的连接故障。SR2 要求的是可信的本次执行结束事实，且连接故障不能由 turn-cap 豁免。

**真实 Docker 证据**：主审在本机 Docker client/server **29.4.1** 和已有 Linux 验证机 **29.8.1** 各运行一个隔离、无网络的临时容器。容器内命令只打印 PID，然后 sleep；信号只发送给本探针持有的宿主 `docker exec` 客户端。客户端结束后，用独立连接读取该 PID 的 `/proc/<pid>/cmdline`。

| 注入 | 两台机器的 CLI 返回码 | 收集器当前分类 / 完整标记 | 容器内同一个执行进程 |
| --- | ---: | --- | --- |
| SIGHUP | -1 | container_process_exit / true | 仍活着 |
| SIGINT | 0 | container_process_exit / true | 仍活着 |
| SIGTERM | 0 | container_process_exit / true | 仍活着 |
| SIGKILL | -9 | container_process_exit / true | 仍活着 |

验证机上的正常退出 `0 / 3 / 130` 三个对照均原样返回对应码。两边收集器源码摘要相同；临时容器均已删除、按本次精确名称查询无残留。脚本：[review_docker_signals_20260924.py](review_docker_signals_20260924.py)；[本机 PID 核对](review_docker_signals_20260924_with_pid.json)、[验证机结果](review_docker_signals_20260924_remote.json)。最初仅查看 CLI 返回值的结果另留在 [首次探针](review_docker_signals_20260924.json)，未用它单独证明容器内进程仍活。

这也与 Docker CLI 的取消处理接缝相符：官方 [v29.4.1 CLI 入口](https://github.com/docker/cli/blob/v29.4.1/cmd/docker/docker.go#L39-L50) 对取消类错误有特殊退出处理；[exec 的退出查询](https://github.com/docker/cli/blob/v29.4.1/cli/command/container/exec.go#L181-L201) 是另一段逻辑。这里以实际信号探针为结论依据，不推广到所有版本和全部断连方式。

**进入训练链的条件与后果**：

- `generate.py:3168–3175` 放过 0；`capture_closed` 只证明已记录轮次装配闭合，不能证明 CC 已结束。
- 真正的 `quiescence_barrier.py:108–127` 是**先终止 agent 进程，再确认归零**，不会区分 CC 此前是自然退出，还是被这次屏障杀死。
- `generate.py:4061–4064` 仅重新判定既有的 forced/turn-budget 情形，普通 CLI 0 不会被它修正。
- 因而，在工具执行期间或两轮之间、没有在飞模型请求且已有 capture 闭合时，丢失执行连接仍可能走完整执行的评分与交付。其它时序中的 poison/drain/capture 失败可以拒绝部分执行，不能替代完成事实。

另有负码碰撞：真实本地 Python 子进程的 SIGINT 返回 `-2`，当前收集器原样放行，而 `-2` 恰是 `HARNESS_EXIT_STOPPED_BY_RH2`。既有 **fa_formal 编排**探针开启非零退出拒绝，仍得到 completed、评分 1 次、`remove_sample=False`；普通容器退出 130 则为 missing/harness_crash、评分 0 次。`-15 + cap` 同样被保留；改为相同 capture 后抛现有 `harness_exec_connection_lost`，有无 cap 都正确移除。见 [CPU 脚本](review_impl_probe_20260924.py)和[结果](review_impl_probe_20260924.json)。**不要把 Python 子进程的 -2 错写成这两版真实 Docker CLI 的 SIGINT 行为；后者实测为 0。** ABORTED 样本上的 reward 0 是运输占位，其 `remove_sample=True`、Outcome missing，不是已评分负样本。

**可达性 / 严重度**：`reachable`，当前运输路径在宿主客户端遭外部信号终止时已用真 Docker 复现。真实 CC/RL 中的发生频率未知；本轮没有跑 GPU 或复现一次真实训练污染。P1 针对完成事实被误认及可能错误保留的后果。

**建议本轮修**：退出来源要关联**同一次 Docker exec 的可信终态**。优先在局部执行运输层持有 exec ID，通过 daemon 的对应 exec 状态确认 `Running=false` 并读取 `ExitCode`；若 CLI 不稳定暴露 ID，可局部改用 Engine create/start/inspect 接缝。连接已结束但 exec 仍在运行、或无法取得其终态，走现有 typed 连接故障与清理路径。负宿主返回码也不能透传成 RH2 的内部 `-1/-2`。

只有 `rc < 0` 的修补**不充分**，因为已证实的 SIGINT/SIGTERM 返回 0。继续叠加 stderr 正则也不能解决无 stderr 的反例。不应改为检查所有 agent 进程是否为 0、`pkill` 是否命中，或强制 CC `result` 在场；这些不是同一次执行的完成证明，也会改变既定准入范围。owner 主动 timeout/cancel 保持既定语义，不能先等容器退出、再让现有 owner 去终止容器。

**最小验收**：真实 Docker 自然退出 0、非零 3/130；客户端 SIGINT/SIGTERM 退出但 exec 仍活；SIGHUP/SIGKILL；现有 owner timeout、外层 cancel。故障在 cap 有/无两种正式编排下均不得评分交付；正常与主动预算终止保持原语义。无需改训练算法或新增通用恢复平台。

## 3. IR2 / P2：失败与取消时，部分日志文件存在，但审计引用丢失

**两个确定的丢失点**：

1. `bringup.py:433–439` 只在 collector 返回后写 `HARNESS_LAUNCH_FACTS["harness_log"]`。collector 的取消分支直接传播 `CancelledError`，跳过这次赋值。主审经实际 launcher→collector 再由生产 `_await_harness_within_deadline` 取消，得到 `-1 / hit_by=harness_outer`、磁盘已有 7 B，但 facts 没有日志块；外部取消对照同样如此，读取任务均已收口。
2. 连接故障即使已把 `harness_log` 放进 launch facts，`generate.py:3079–3082` 的复制仍在 await 正常返回之后。正式编排中，driver 先写日志事实再抛既有 typed 码，最终内存 audit 和**实际落盘 JSON**均为 `harness_log=null`，两条 harness artifact 路径未登记。正常路径对照有块、有两条路径。

**不变量 / 影响**：SR4 已要求从持久 audit 回读失败路径。B 线改读宿主日志后，恰好最需要诊断的失败 execution 会失去索引及 partial 原因。此次 typed 连接故障本身仍正确拒绝，没有因日志丢失额外进入评分；这是诊断运输缺口，P2。

**可达性**：`reachable`，现有连接异常与外层期限取消即可进入，不依赖新功能；同一 collector 取消路径也供 poison、关停和 cap 强停使用。证据见 CPU 脚本的 `typed_loss_audit`、`cancelled_launch`、`outer_deadline_launch`，不是只检查源码字符串。

**建议本轮顺手修**：在现有收集器取消/异常收口中交出已知路径、实际写入量与 partial 原因；编排在既有 finally 中复制现存事实。保持原 `CancelledError` / typed 首因，不能为交出日志吞取消、改预算类别或新增停止 owner。

**验收**：连接异常、外层期限、外部取消及共用取消入口的 poison/cap 强停，从落盘 JSON 能找到已收到的部分、字节数和 partial 原因；正常路径仍完整；未启动 CC 时不伪造日志或完成事实。只覆盖实际不同分支，不要求重复建五套大型夹具。

## 4. IR3 / P2：短写被误报为完整日志

**位置 / 当前行为**：`docker_sandbox.py:243–244` 忽略无缓冲文件 `write(data)` 的返回值，直接按 `len(data)` 加计数。短写没有抛异常时，`log_complete` 仍为 true。

**独立证据**：在隔离子进程中设真实 OS `RLIMIT_FSIZE=4096`，忽略 SIGXFSZ，另一个真实子进程输出 8192 B。当前收集器的结果是：实际文件 **4096 B**，报告 **8192 B / complete=true / partial=null**，退出码仍为 0。仅限制探针子进程，不修改主进程限额或耗尽磁盘。见 CPU 脚本的 `--short-write-child` 与结果 `short_write`。

**可达性 / 影响**：`reachable under storage fault`，文件大小限制下真实短写已经复现；普通运行磁盘中发生频率未知。违背“日志写失败只标 partial、保留可信执行结果”的既定诊断合同，不直接改变训练数学。

**建议本轮顺手修 / 验收**：按实际写入长度计数，处理未写完的部分；若选择停止该文件写入，明确 partial 并继续排空管道。8192→4096 的真实短写必须被标为不完整，正常双流与原有 open/write 错误用例维持预期，不能把诊断短写改成样本拒绝或新的 run-fatal。

## 5. 作者验收证据的使用范围

- 回读了四份 `acc2_*/attempt.json`、实际宿主输出及验收脚本。它们证明真实 CC 2.1.205 经正式 **driver** 的启动和工具解释器；脚本没有运行整个正式 orchestrator、训练 capture 或 GPU 链。
- `max_turns` 用的是 CC 的 `--max-turns 3`，不是 RH2 guard 的 403 预算路径；time_budget 为 driver 自己的预算，外层保护额外放宽 300 秒。两者不能代替本轮 IR1/IR2 的正式编排接缝验收。
- normal/max_turns 原始 `all_expected_ok=false` 分别来自 `.git` 目录 mtime 被算作新写、对应剧本没有执行解释器检查。作者已在 Brief 解释，未据此提出产品故障。`git status` 加 mtime 对照的证据强度仍低于完整 census 对照。
- cut_stream 的 RC 1、`subtype=success` 且 `is_error=true` 与日志吻合；只能作为已测那种断流的事实，不能推出四形状×commit 前后全部安全。#3 仍按既定顺序继续，不用 `result` 新设准入规则。
- 四个短场景没有 count_tokens 请求，不证明长上下文、Read 或压缩路径永远不用该入口；#8 待真实形态核对。
- 本轮读取验证机实际 Docker 版本为 **29.8.1**，Brief 的“Docker 28”不能当作当前版本记录；本轮没有升级或修改 daemon。R2E `.venv` 映射和 B 线 `solve_attempt.py` 改读宿主路径仍归其现有接线任务，不算 A 已替 B 完成。

## 6. 验证、范围与停止条件

主审运行的维护测试：

```bash
# 从 rh2/ 执行
.venv/bin/python -m pytest -q tests/adapters/test_startup_fix_1_activation.py tests/adapters/test_startup_fix_2_host_collected.py
# 41 passed
.venv/bin/python -m pytest -q tests/adapters/test_budget_deadline.py tests/adapters/test_w3b_sandbox_profile.py
# 89 passed
.venv/bin/python -m pytest -q tests/adapters/test_w3b_sandbox_docker.py
# 14 passed（真实 Docker）
```

审查探针（从仓库根执行）：

```bash
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/base_probe_chain_fixes_20260923/review_impl_probe_20260924.py
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/base_probe_chain_fixes_20260923/review_docker_signals_20260924.py
```

Docker 探针要求镜像已经在本机；`--pull=never`，可用 `RH2_REVIEW_IMAGE` 指定既有镜像 ID。验证机使用已有 Python 镜像 ID，通过 stdin 执行同一脚本，未部署代码、拉镜像或改配置。连接细节仍只留本机私有配置。正常 0/3/130 对照与故障后的 PID 核对均在验证机执行；主审 CPU、Docker 探针及 ruff 通过。

审查维度：A/D/G/H/L 深查启动 owner、取消、执行事实与并发参数；B/F 检查是否改变预算/失败处置，命中 IR1；E 通过真实消费者正反控检出正常路径测试的盲区；M 命中 IR2/IR3；N 固定并记录 CC 与 Docker 实测版本。C 无新增临时挡板；J/K/I 接受无状态 helper 和局部改造，限制修复范围；本片未动 loss、路由、评分公式，相关数学不重审。依 §10.4 一对限定角色检查，主审独立复现并裁决；真 Docker 的 CLI 0 反例推翻了初步“仅补负码即可”的建议。

**停止条件与排程**：IR1 完成可信执行终态修复，IR2/IR3 补齐失败日志运输和短写标记，保留上述正控即可收口 #1/#2。没有新 T0，Claude 可直接处理。#3 夹具与 #6/#8/#9/#10 文档准备可并行；在 IR1 修复前，不把当前完成状态判断用于正式 rollout 验收结论。不要求重跑三题全部基座、216 题筛查或八卡训练来验证这些局部修复。

本轮未重跑全库/双 lane、真实 CC 或 GPU，作者相应结果仅作为复用证据。只新增审查文件、探针和结果，追加 Brief 指针与 infra 记录；未改生产代码、维护测试、fork 或历史 evidence，未提交/push，未向 B/Claude 发送外部消息。只删除本轮拥有的临时容器；验证机生命周期保持原样。
