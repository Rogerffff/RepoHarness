# 预算终止闭环：第二次窄复核（2026-09-09）

**结论：R1 与 R5-F1 关闭；R3 仍未通过。作者新提出的僵尸问题成立，而且正常命令完成后的现有收口流程也受影响。建议先明确停止确认的合同，再一次性修正 R3；僵尸问题优先考虑 Docker `--init`。** 本文不批准新的样本 DROP 规则，不代替 owner 选择预算数值。

复核基线 `3d0bca0cb0e60c049ac4d80b844ddc851cea640e`，当前 HEAD `6b33efee38d2b0d785983e44136dccbdd9c49a60`。对应源码提交：R1 `5192356f`、R3 `dfed0d61`、R5-F1 `f9f6c27b`；文档 `6b33efee`。输入为 [Claude 本轮说明](../../../tmp/claude修复.md)、四个提交及[上一轮复核](../followup/README.md)。9 个变更 Python 文件的起始指纹见 [review_snapshot.json](review_snapshot.json)。

## 1. 当前状态与审查范围

| 项目 | 本轮结论 | 证据与边界 |
|---|---|---|
| A、B、D-1；R2、R4、原 R5 取消问题 | 沿用通过 / 关闭 | 不重新审整条链；只保留本次改动关联的必要回归 |
| R1：生产路由是否实际经过预算包装 | **关闭** | 真实 `BringupService` 构造与实际 HTTP 线程六案通过，含并发交付、取消和故意绑定旧 handler |
| R5-F1：关闭时积压无人消费 | **关闭** | 真实 service 评分队列步骤，两种积压均及时排空；原取消 fatal 三案保持 |
| R3：停止证据决定 KEEP / DROP | **P1，仍未关闭** | 真实 formal 编排与处置函数复现错误 KEEP、错误 DROP 两个方向；见 §3 |
| Z1：僵尸被算成活动残留 | **P1，当前正式路径可达；真实诊断前修正** | 主审四案真实 Docker 对照；这是作者本轮主动提出的问题，不扩大到无关链路 |

主审独立执行 **196 项维护测试、9 文件 ruff、6 案真实服务 HTTP、5 案 queue/service、7 案新停止时序、8 案旧停止时序回放、4 案真实 Docker**。测试通过只说明现有断言通过；新停止探针的成功退出包含“准确复现当前错误”的断言，不能算实现验收通过。没有复跑作者声称的全量 2181 项，也没有运行真实 CC、外部模型 API、GPU 或参数更新。

独立角色完成[生产追踪](production_tracer.md)与[反证 / 简化审查](falsifier.md)。主审回读脚本并复跑，僵尸探针则由主审执行、两角色交叉核对生产父子进程关系与证据限制；结论不按票数决定。

## 2. 两项已关闭问题为什么可以收口

**R1。** `bringup.py:1073–1097` 现在先 `install_capture_wire`，再构造 `AnthropicAdapter`，再核对实际 POST 路由。每个探针在全新子进程中构造真实服务，构造前确认类方法尚未包装，然后向服务真正监听的端口发请求。顺序在飞与分块 body 两案均等完整 capture 交付后才返回 403；cap=3、同时五个请求时前三个保持并发，后两个等待，最终为 200×3 / 403×2。取消待拒请求不污染已接纳轮，取消已接纳请求仍产生原有 poison / abort。故意在真实构造器登记旧 handler 时，启动报 `turn_budget_wire_not_bound_to_route`，HTTP 线程尚未启动。

这次补齐了作者承认未做的“真实服务线程上三个关键 cap 对照”。服务的任务面使用 `fa_audit_only` 夹具，路由构造位于模式分流之前，与正式模式共用；生成 IO 是内存替身，不声称真实 CC 的 403 行为已验证。新增核对只在启动执行，未发现当前固定 adapter 的合法路径被误拒；函数名检查有维护耦合，但不构成另一个阻塞项。

**R5-F1。** `grading/queue.py:166–170` 先等 `queue.join()`，之后才置 `_closing`、撤 worker。实际服务先关闭评分准入，一个 worker 处理两个已接纳 item：提交者仍在、提交者都已取消两案，释放首项后都在约 0.011 秒排完两项，未耗尽探针原有 0.2 秒上界，queue=0、workers=[]。原提交者取消、关停期间 fatal、worker 被取消三案仍只有一次 fatal 通知，并有界退出。正常 drain 修复没有推翻 `drain=False` 的原取消修复。

主审结果：[HTTP 六案](production_route_root_rerun.json)、[队列五案](production_queue_root_rerun.json)。到此关闭，下一轮无需再检查它们的完整矩阵。

## 3. R3 尚未闭合：停止动作与停止事实仍被混用

### 3.1 成功发出 kill、但没有停止确认，仍被判为已经停止

**当前行为与位置。** `execution_scope.py:144–154` 在没有期限后的正数观测时，会仅凭 `kill_delivered_at <= deadline` 返回 True；既不要求 `verified`，也不要求存在任何一次 COUNT 结果。`generate.py:3894–3898` 因此停止重试。后续屏障拿到的新观测没有送回这份判定：`quiescence_barrier.py:106–118` 只消费最后残留数，`generate.py:3832` 又只重判特定的“尝试用尽”字符串，早先的 True 不再纠正。

**违反的不变量。** 未拿到反证不等于拿到停止证明；执行在 hard wall 后仍存在活进程，不能因为更早一次 kill 调用成功就归为 turn 截断保留。评分前最终安全静止，也不能证明执行在期限前已经停止。

**动态证据。** 设期限为 900 秒，主审复跑得到：

| 首次停止动作 | 后续真实屏障 | 当前实际结果 |
|---|---|---|
| 899.5 收到 `pkill_status=0`；COUNT 超时，零条计数观测，`kill_verified=false` | 900.1 发查询、900.2 仍有活残留，901 才归零 | `stop_before_deadline=true` → `max_turns_exhausted` → **KEEP_FULL** |
| 890 收到成功回包；保留真实 10 次轮询上限，890.5–895 十次均为 1，次数耗尽但未发生 IO 超时 | 同样墙后仍有活残留、901 才归零 | 同样错误 **KEEP_FULL** |

这直接反驳了作者“没有未证明就按 KEEP 放行的出口”。数据经真实 `RolloutOrchestrator`、真实屏障、真实 `AdmissionPayloadV1` 到达 `decide_member_disposition`，不是只检查 helper 自己的布尔值。动态探针把 Docker IO 与观测钟换成可控替身，明确注入的是**活残留**，没有把任意 Z 进程等同于仍能执行。

**生产可达性与影响。** 触发需要首次停止未覆盖 / 未结束全部活执行，随后计数 IO 超时或轮询次数用尽，下一次屏障停止才成功。当前调用链确有这些路径；pkill 枚举期间新生进程等生产条件尚未做真实 Docker 竞态复现，频率未知，因此不报 P0 或“必然影响所有训练”。错误处置能把已越墙的执行重新纳入训练，且审计自身记录 `kill_verified=false` 与 `stop_before_deadline=true` 的矛盾，属于原 R3 的 P1 未闭合。

**辅助事实也需更正。** Brief 表格称 pkill 成功证明所有 agent 进程均已收到信号，且状态 1 只表示原本为空。procps-ng 手册实际规定：0 表示至少一个匹配进程成功收到信号；1 包含没有匹配或没有一个能成功发送信号。两者均不能单独证明整个 scope 已停。当前 profile 保留了 `KILL` capability，本文没有把权限不足另作默认生产故障。来源：[procps-ng 的 pkill 手册](https://man7.org/linux/man-pages/man1/pgrep.1.html#EXIT_STATUS)。

### 3.2 已在墙前收到零确认，仅指纹读取跨墙，却被 DROP

**当前行为与位置。** `quiescence_barrier.py:106–118` 先停止并确认归零，`:119–137` 才双读工作区指纹。`generate.py:3258` 等整个 `establish` 返回之后，才在 `:3834–3842` 用当下时间重判；实际的零确认时间没有被消费。

**证据与不变量。** 前三次停止未确认、期限尚未到；屏障在 **899.5 秒已经收到零计数**。若随后两个一致指纹在 899.5 返回，结果 KEEP；只把指纹返回推迟到 **901 秒**，就得到 `hard_wall_timeout` / **DROP_GROUP**。这违反已批“执行停止后的检查 / 清理越界，不补造 hard wall”，也违反作者本轮自己的规则 A“期限前收到零确认即可”。这里已有墙前确认，不属于实际停止时刻不可知的保守边界。

**生产可达性与影响。** 停止尝试可以快速失败或提早耗尽轮询，不必每次都用满 30 秒；后续屏障成功后，读取大工作区指纹可能跨期限。这些均属于现有正式路径，不依赖未来能力，也不依赖真实 CC 对 403 的响应。错误会选择性丢掉停止确认较晚、后处理耗时较长的成员，并按完整组规则扩大损耗；发生率未测。属于本次 R3 修改引入的归类回归，仍列原 R3 P1。

### 3.3 分期、复现与窄验收

R3 应在预算闭环获准进入真实正式路径前修正；不因此阻塞 B 线独立的数据文档、CPU 环境准备等工作。两条反例已经足够，不再扩大停止状态矩阵。

仓库根目录运行：

```bash
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/followup2/stop_evidence_falsifier_probe.py
```

[7 案主审原始结果](stop_evidence_root_rerun.jsonl)包含上述两个失败方向、及时 / 晚到指纹对照、墙后才归零、实际先空但计数回包晚、首轮已确认归零而指纹晚到。原八案回放见 [stop_cases_replay.jsonl](stop_cases_replay.jsonl)；旧 kill 失败后同一次 helper 看见墙后活残留的反例已得到 DROP，这部分修正成立。

**验收条件：** 成功发送 kill 后 COUNT 超时 / 十次正数耗尽不能产生停止证明；后续屏障得到的可信停止事实必须参与同一归类；相同墙前零确认配合及时 / 晚到指纹，最终处置必须一致；已有真越墙反例仍 DROP；取消与停止清理仍有界。晚回包但实际先空的一案，先按 §5 明确合同，再写 oracle，不让测试替 owner 决定。

## 4. Z1：本机真实 Docker 确认正常收口也受僵尸影响

**行为与根因。** `RolloutSandboxProfile.docker_run_args` 在 `sandbox_profile.py:469–479` 以 `sleep infinity` 启动，没有 init。生产 `ClaudeCodeHarness.launch_and_wait` → `run_agent` → vendored `exec_and_wait`，后者在 `slime/agent/sandbox.py:110–124` 通过 `setsid bash launcher ... &` 分离启动；退出后的孤儿需要被回收。当前 `COUNT_SCRIPT`（`execution_scope.py:48`）统计全部 agent PID，包含已经不能执行的 Z 状态。屏障 `quiescence_barrier.py:110–118` 因计数非零拒绝。

**主审真实对照。** 使用本机已有 `node:22-bookworm`，镜像 ID `sha256:9059d9d7db987b86299e052ff6630cd95e5a770336967c21110e53289a877433`，Linux arm64、Docker 29.4.1。四案直接调用真实 `DockerSandbox`、vendored `exec_and_wait` 和 rh2 停止 helper；命令体缩为 `true` 或 `sleep 60 & wait`。相同镜像、相同启动方式，只比较有无 `--init`。

| PID 1 | 命令与收口 | 收口后 agent 进程 | 现有 COUNT / helper |
|---|---|---|---|
| `sleep` | `true` 正常返回 0，再按现有流程停止 / 确认 | 1 个 PPID=1、`Zs bash` | 1 / 未确认 |
| `sleep` | 活着的 bash + sleep 被强停 | 2 个 PPID=1、Z / Zs | 2 / 未确认 |
| `docker-init` | 正常返回 0，再停止 / 确认 | 无 | 0 / 已确认 |
| `docker-init` | 强停 | 无 | 0 / 已确认 |

两种 sleep 案中，仅排除 Z 的计数均为 0。这证明作者的根因判断成立，但“正常完成路径不受影响”不成立。**严格证据边界：** 正常案的进程快照位于 stop helper 之后，未拍摄 kill 之前的状态；因此只断言“正常命令完成后的现有收口仍会被 Z 残留拒绝”，不声称动态测得 launcher 在 kill 之前已经成为僵尸。两位独立审查者都指出了这一区别，主审采纳。

**不变量、影响与分期。** 已不能执行 / 写入的僵尸，不应被当成未终止的活动执行；正式链普通完成也必经该屏障，因此影响不限于 cap 强停。可能使正常成员被判 `execution_scope_termination_timeout` / missing，继而整组丢弃。这是当前默认启动与确认组合的实际问题，需在采用该组合的真实 formal / SWE 诊断前修正；不以四个窄用例推算整个训练任务的失败比例。没有运行目标 SWE 镜像、真实 CC 或 GPU，不能据此宣称完整生产链验收完成。

**建议 B：使用 Docker `--init`。** 本机对照已支持它补上孤儿回收；A 过滤 Z 能修正“还能否执行”的计数，但不会回收僵尸占用的进程槽位。Docker 官方将 `--init` 作为主进程不负责子进程回收时的标准做法，无需引入 systemd 一类完整管理器。[Docker 文档](https://docs.docker.com/engine/containers/multi-service_container/)。僵尸与回收的 Linux 语义见 [wait 手册](https://man7.org/linux/man-pages/man2/waitpid.2.html#NOTES)。

B 的实际改动面是 rollout 容器参数及其 profile 事实 / digest、必要验证；需要保留既有用户、权限、资源、网络隔离条件。A 是可选窄修法，不能将“计数归零”写成“已回收僵尸”。只因 profile digest 会变，不足以认定 B 是一个重大新架构；本次不另扩到 grader、镜像生产线或通用进程管理平台，也不自动同时实施 A+B。

**窄验收：** 用修改后的真实 rollout 参数重新跑正常 / 强停对照，确认 helper 有界归零、正常 exit code 保留、容器回收完成，profile 记录对应实际 init 参数。无需为这个 Linux 进程行为租八卡；目标 SWE 镜像上的一次真实 CC 诊断仍保留为后续集成验证。

复现脚本 [zombie_docker_probe.py](zombie_docker_probe.py)，结果 [zombie_docker_result.json](zombie_docker_result.json)。只使用已有镜像，`--pull=never`、无网络、无宿主挂载、设置资源上界，四个临时容器均已删除。观察窗口缩为三次 COUNT、约 0.5 秒，不把有限观测说成已实测“永远”；持续不可回收的判断另有实际 PPID=1 / sleep 拓扑与内核语义支持。

## 5. 建议的收敛方式：先明确一个可以实现的停止合同

R3 的根因已经不是少一个异常码：停止动作、停止确认、整个冻结完成这三个边界被交替当成同一事实。增加投递时间、逐次观测数组、合并与重判分支仍未闭合它。建议先定下边界，再最小修正；不默认启动另一轮“多加字段 / 多加重试”。这里是根据重复失败作出的设计建议，不把 P1 误报成协议要求的“连续 P0 熔断”。

**推荐候选：以控制端收到可信 scope 停止确认作为预算执行结束边界。** 对强停路径，kill 成功只是动作记录；期限前确认无活动执行，才结束 watchdog 约束。该确认后的指纹读取、冻结、评分、清理不改变这次执行的预算归因。停止尚未确认而到点，执行结束归 watchdog 超时，按已选的 hard wall 策略整组不训练；底层停止 / 清理仍有自己的有界收口时间。一次确认由现有停止 / 屏障流程提供给编排消费，避免两个位置各自推测。

这项建议的**明确代价**是：实际已经停止，但确认回包晚于期限的样本也会被保守排除。它不需要推断不可观测的容器实际退出时刻，实施和诊断都更简单；但会扩大 DROP 的样本集合，发生率未知。事实记录应区分“观测到越墙活执行”和“到点尚未确认停止”，不把后者描述为已经证明前者。

**当前并未批准这项合同。** Claude 说明、交接 §4.6 与账本将上一轮“指出观测不足”写成“Codex 认可保守 DROP”，归属不准确。上一轮没有替 owner 批准新增剔除规则。[协作协议 §2](../../../../collaboration-protocol.md#2-决策分级t0--t1--t2)将“改变训练样本准入”列为 T0；如果采用推荐候选，应明确确认这个代价，再改 oracle。源码中的“按已批规则”和 Brief 中“只改证明、不改 KEEP/DROP”也应随之纠正。无论 owner 如何选择，不存在争议的两条仍是：缺观测不能当停止证明；已经收到的墙前确认不能被后来读指纹的耗时推翻。

若坚持完全按实际退出时刻区分，当前宿主 CLI 回包和离散 COUNT 不足以辨识边界，必须先提供可信的实际停止证据。首版不建议为挽救期限附近的这部分样本另建进程监督 / 恢复系统。删除 turn KEEP 能力会推翻已定案；对每次不确定都 run-fatal 会放大局部故障；仅加监控不能纠正已证实的错误准入。故推荐明确确认边界后的最小局部修复，并保留已经必要的安全收口。

停止合同只需要一种权威确认，不必保留当前每一种推断字段。`pkill_status=None` 为旧脚本 / 测试提供“视作成功”的 fallback 没有当前生产 producer 的必要性；若投递不再支撑 KEEP，它应降为诊断或随不必要推断一起删除，不为它再加一层防御。

## 6. 验证、适用维度与停止条件

本轮适用 A/E/G（真实构造、并发与反例有效性）、B/F（训练处置与已批规则）、D/H（停止事实的生产者 / 消费者）、I（局部收口）、J/K（证明函数和重复判断复杂度）、L（排空、有界清理与僵尸槽位）、M（观测和结论矛盾）、N（vendored 路由 / Docker 进程行为）。C 已核：没有新增临时生产挡板；§6 六项、`owner_cancelled` / `agent_violation`、600 秒 / 25 次均未改。未重审 loss、reward 算术、SWE 数据筛选或所有历史 guards，因为 9 文件 diff 不改这些面；本文不据此扩大已通过范围。

| 主审验证 | 结果 / 工件 |
|---|---|
| 9 个维护测试文件，带 `RH2_MILES_PATH` | **196 passed in 58.57s**；[focused_tests.txt](focused_tests.txt) |
| 本轮 9 个变更 Python 文件 ruff | 通过；[ruff.txt](ruff.txt) |
| 新鲜进程的生产 HTTP 路由六案 | exit 0；[脚本](production_route_probe.py)、[主审结果](production_route_root_rerun.json) |
| queue/service 五案 | exit 0；[脚本](production_queue_probe.py)、[主审结果](production_queue_root_rerun.json) |
| 新停止证据七案 | exit 0，包含反例；[脚本](stop_evidence_falsifier_probe.py)、[主审结果](stop_evidence_root_rerun.jsonl) |
| 旧停止证据八案回放 | exit 0；[脚本](stop_cases_replay.py)、[相对旧探针的修改](stop_cases_replay.diff)、[结果](stop_cases_replay.jsonl) |
| 四案真实 Docker 进程对照 | exit 0，全部删除；[脚本](zombie_docker_probe.py)、[结果](zombie_docker_result.json) |

维护测试命令，从 `rh2` 执行：

```bash
RH2_MILES_PATH="$PWD/../reference/miles-rh2-integration" uv run --no-sync pytest -q \
  tests/adapters/test_budget_deadline.py tests/adapters_miles/test_budget_loop.py \
  tests/grading/test_manager_unit.py tests/grading/test_queue.py \
  tests/adapters/test_f2_2b_barrier.py tests/adapters/test_w3b_bringup_sandbox_runtime.py \
  tests/adapters_miles/test_w3b_formal_entry_vertical.py \
  tests/adapters_miles/test_w1b_group_admission.py tests/adapters/test_w5a_shutdown_chain.py
```

**停止条件：** R1/R5-F1 到此关闭，已关闭的 A/B/D-1/R2/R4/原 R5 不重开。后续只处理 R3 合同与本文三组关键时序、Z1 的正常 / 强停真实容器对照及各自必要回归。确认墙前停止后晚到指纹不改处置，未确认不被冒充成功，正常收口不因僵尸拒绝，即足以收尾本批。真实 CC 的退出 / 403、目标 SWE 镜像和运行预算数值归后续明确的诊断作业，不以本轮测试代替。

本轮只写审查工件、Brief / 交接状态及共享账本；没有修改业务源码、维护测试、依赖或 git 提交。收口指纹与产物检查见 [verification_summary.json](verification_summary.json)。
