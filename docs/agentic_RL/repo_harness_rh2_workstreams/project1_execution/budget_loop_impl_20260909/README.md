# 预算终止闭环实施计划（Owner Brief）：I02/I03/I04 + I14 + 依赖的 I05/I12

日期：2026-09-09。作者：Claude（A 线）。状态：**已按 Codex 计划审查（[codex_plan_review.md](codex_plan_review.md)，R1–R4 全部接受，附两处我方细化）修订；批 A 已提交 `6bb5ffe4`（Codex 针对性复核通过）；批 B 已实施并按 [Codex 批 B 聚焦审查](batch_b_review/README.md) 修完 R1/R2a/R2b/R3 与 §4 非阻塞项（本地全量通过、未提交，待针对性复核）；§6 六项仍按现状登记，未新增 owner 批准。** 基线：I01 已提交 `297f1f59`（针对性复核通过）；miles 集成 `98a0272e4`，本批不改 fork，不改 vendored slime 字节。修订记录见 §11。

## 0. 一句话

把"为什么停、是否真停、完整记录是否训练"三件事接成一条可核对的链：turn 预算用尽产生真实 `max_turns_exhausted` 事实并 KEEP_FULL 真实评分；宽墙钟从资源占用起表、准备与排队计入、到点是**强制**停止并整组不训练；停止动作真的杀进程、abort 在飞请求、回收 docker CLI 与持有资源；未归因异常不再洗成 ABORTED；receipt 失败仍 fatal 但照常清理。

## 1. 实现哪些决定

- [第一组三项原则](../batch1_budget_20260908/README.md#6-已确认的三项原则与验证范围)（用户 2026-09-08 确认）：保留 turn 上限＋较宽墙钟；turn 用尽且事实可信 → KEEP_FULL、真实评分；墙钟到点 → 整组不训练；数值不定；[墙钟从资源占用起表](../batch1_budget_20260908/README.md#2-决定一首版使用什么模型行动预算)；[停止规则直接落实](../batch1_budget_20260908/README.md#5-停止规则已有决定直接落实)。
- [第二组 §2](../batch2_failures_20260908/README.md#2-直接落实当前执行链的未知异常不默认转-aborted)：当前执行链不可归因异常 → FATAL（06 §2 已定）；[I12](../batch2_failures_20260908/README.md#1-五个问题09-08-的收敛与当前状态) receipt 失败 fatal 且继续清理（06 A4）。
- [可开工清单 §4.1](../decision_batches_20260908.md#41-直接准备实施的明确部分) 第二、三行；[§7 两处修正](../decision_batches_20260908.md#7-现在怎样开工20260909供-claude-编写当批计划)：预算耗尽不伪装 `end_turn`，B 的接口要能区分自然结束 / turn 截断 / hard wall / 执行错误。
- 06 计划 [A4/A5](../../06-first-training-local-execution-plan.md)：A5-a ① KEEP_FULL、A5-b (2) DROP、A5-c 资源占用起表；A4 run-fatal 面"仍 revoke session / 终止 scope / 清容器"、"execution scope 无法终止 = run-fatal"。

## 2. 当前代码事实：为什么每一项都必须改（生产可达性）

| 问题 | 今天正式链（`fa_formal` + `RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1`）的实际行为 | 锚点 |
|---|---|---|
| I02 | 第 26 次请求由 vendored adapter 返回 429；CC 守卫 env 已设 `CLAUDE_CODE_MAX_RETRIES=0`，CC **不重试、直接非零退出**；正式链 `reject_on_nonzero_harness_exit` 与 `RH2_REQUIRE_REAL_WEIGHT_VERSIONS` 联动为真 → `nonzero_harness_exit_in_formal_chain` → `harness_crash` → missing → ABORTED。**结论：turn 预算用尽今天 = 伪装成 harness 崩溃的整组丢弃**，与已批 KEEP_FULL 相反；rh2 也看不见这次 429（capture wire 不包 `_check_turn_cap`）。 | `rh2/src/slime/agent/adapters/common.py:285-306,331`；`generate.py:1036-1041`；`bringup.py:1149-1156`；`generate.py:2824-2833`；`outcome_producer.py:56` |
| I03 | 三个钟各起各的：harness 的 done-marker 轮询从 CC 启动起算 `time_budget_sec`；proxy 的 session deadline 在**首次模型调用**才起表；`_send` 在拿 `model_call` 信号量**之前**算好 timeout，等信号量的时间不受 deadline 约束、拿到后不重算。准备阶段（docker run、trusted init、baseline census、CC 安装、useradd/chown 自带 900s 上限）不在任何钟内。到期取消也没有接通：`docker_sandbox._run` 只处理自身超时不处理外层取消，物化清理只捕 `Exception`（Codex R2 探针：取消时 kill/wait 均未调用）；proxy 把 `_send` 的 deadline 异常改写成 `no_overlapping_update_window`。 | `sandbox.py:63-77`；`capture_wire.py:377-392`、`bringup.py:1238`；`async_worker.py:735-756,868-878,919-923`；`bringup.py:353-365`；`docker_sandbox.py:27-40`；`generate.py:4049` |
| I04 | `DispositionPolicy` 四槽位全 None；`ensure_fa_started` 不注入；第一个 `present_truncated` 成员到 buffer 才抛 `DispositionNotInjectedError`，group filter 把它当 fatal 通知停机 → **第一次截断即停机**。 | `governance/admission.py:634-647`；`bringup.py:2429-2445`；`group_admission.py:540-556` |
| I14（rollout 侧） | exit=-1 后没有任何停止动作就 drain（等 inflight 归零 30s）→ 冻结 → 到屏障才 `pkill -9 -u agent`。CC 仍在跑时 drain 可能不干净 → `session_plane_drain_unclean` → missing；在飞引擎请求继续占槽直到自然结束。 | `generate.py:2770-2806`；`capture_wire.py:534-561`；`quiescence_barrier.py:47,100-115` |
| I14（grading 侧） | `run_docker` 无取消保护；`_exec_bash_checked` 的 `wait_for` 超时后 docker CLI 子进程孤儿化；容器靠 finally 的 `rm -f` 兜底，rm 失败只记 `cleanup_failures`；`_container_running` 把 inspect 失败也压成 False，"仍在跑 / 无法确认"都不会通知停 run。 | `grading/manager.py:95-109,1240-1244,1410-1424,1449-1473` |
| I05 | `except Exception` 兜底把 identity/materialize/harness_run/assemble 的**任何**异常按 stage 表洗成 missing/ABORTED；未映射的 typed 码记 `unmapped_failure_code`；两个点名的账实矛盾码被映射成 capture 不完整；CLI 版本不符以裸 `RuntimeError` 冒出。测试用裸 `RuntimeError` 模拟"harness 崩溃"。 | `generate.py:3460-3474,3500-3575`；`outcome_producer.py:56-62,77-83`；`bringup.py:324-332`；`test_w1b_termination_facts_producer.py:230`、`test_w1b_delivery_face.py:368` |
| I12 | `cleanup_skipped = receipt_persist_failed` → 跳过 drop_session 与容器清理、容器入隔离队列。 | `generate.py:3669-3676`；`test_b5_finalization.py:103-140` |

## 3. 分四个可独立验证的小批（各自成一次提交；同文件再次出现不是错误）

依赖顺序（Codex §3）：**A → B → (D 的处置注入 ≤ C 的 cap 启用) → D 的 grader 回收**。批 B 必须同批完成期限触发的取消清理，不先接主动取消、后补持有资源无人清理的空档；不交付"cap 已产 `present_truncated` 但策略仍 None"的中间版本。

### 批 A：I05/I12 旧规则落实（先做；后面三批的错误码依赖它）

改：`generate.py::_generate_attempt` except 链（新增 `_pre_finalize_exception_is_attributed`）、`_run_finally_section`（receipt / termination 事实两条尾部 fatal 提前通知）；`outcome_producer.py::FAILURE_CODE_TERMINATION_MAP`（穷举 = 唯一判定来源；两个账实矛盾码只在测试参数化里点名，不另设公开集合——Codex 批 A 审查可简化项）；`docker_sandbox.py`（新 typed `SandboxExecError`）；`bringup.py::ClaudeCodeDriver.run`、`_install_native_cli`。

分类原则（Codex R1）：**D1 允许 ABORTED 的依据是"已归因的 task-local 故障"，不是异常有没有名字。** 可识别的局部运行 / 服务 / 传输故障保留 ABORTED；成功读取后发现版本、血缘、digest 不符，以及内部引用 / 事实矛盾，走 fatal 通道；混合原因在抛出点区分，不新建通用分类平台，也不反向把所有 Docker 非零退出都叫结构错误。

| 边界 | 异常 | 处置 | 变化 |
|---|---|---|---|
| materialize | 局部运行故障 typed 码：`rollout_image_inspect_failed` / `rollout_image_ref_inspect_failed` / `rollout_container_start_failed` / `rollout_base_untracked_snapshot_failed` / `rollout_workspace_write_failed` / `rollout_egress_network_failed` / `rollout_egress_relay_connect_failed` / `rollout_git_sanitize_failed` / `rollout_trusted_init_failed` / `baseline_head_unreadable` | ABORTED，显式映射 `("sandbox_failure","sandbox_crash")` | 处置不变；从 stage 兜底改为显式表 |
| materialize | 成功 inspect 后内容不符：`rollout_image_digest_mismatch` / `rollout_testbed_lineage_failed` | **§6 待确认**（Codex 建议 FATAL）；确认前显式登记为 ABORTED | 待确认 |
| harness_run | `DockerSandbox` 自己的操作失败（`exec(check=True)` 非零 / 超时 124、`write_file` 非零；覆盖装 CLI、useradd/chown、slime 的 ensure_agent_user / write_config / spawn）→ typed `SandboxExecError` | driver **只**把它包成 `harness_bootstrap_failed` → ABORTED `("harness_crash","harness_crash")`；其它 `RuntimeError`（我方 / vendored 代码不变量）原样上抛 → 未归因 fatal（Codex 批 A 审查 R1：局部失败类型建立在能证明来源的操作边界上，不按异常类改名） | 处置不变；归因 typed 化 |
| harness_run | CLI 版本不符（原裸 `RuntimeError`） | typed `cc_version_mismatch`，**不入表** → FATAL（run 级配置错误，每个 attempt 都会失败） | **变：ABORTED → FATAL**（Codex R1 例子） |
| harness_run | 非零退出（无预算事实） | 不变 | — |
| assemble | 第二组 §1 点名的两个账实矛盾 `leaf_facts_length_mismatch` / `capture_record_unknown_in_backfill` | 从表中移除 → FATAL | **变：ABORTED → FATAL** |
| assemble | 其余已映射 capture 族码 | 不变 | — |
| identity → assemble 任一阶段 | **未映射的 `SlimeBindingError` 码**（含身份 span / tape / 版本事实矛盾、配置守卫码）、**任何非 typed 异常** | **FATAL** `pre_finalize_failure_unclassified`（复用 `_structural_contract_fatal`：failure_record、mark、`_notify_fatal_halt`、不产 Outcome、不返回 ABORTED；finally 清理照跑） | **T1 oracle 变**：裸 `RuntimeError` 当"harness 崩溃"的测试改用 typed 码；裸异常改为 FATAL 反例 |
| identity / 任一阶段 | `fa_identity_incomplete_in_formal_mode`、finalize 前 `ValidationError`、`frozen_artifact_persist_failed`、`sampling_mask_tape_missing_in_assembly` | **§6 待确认**；确认前显式登记 / 保持 stage 兜底 | 待确认 |
| 任一阶段 | `asyncio.CancelledError` | 原样传播 | — |
| s1_compat | 全部 | 冻结路径逐字不变 | — |

不扩大：grading 的 `failed_to_grade`、可选 telemetry sink 失败、模型工具 / 候选测试报错、`repair_signal_sink` 失败——全部不变。

I12：receipt 写失败 → 仍抛 `finalization_receipt_write_failed`（fatal），但 `cleanup_started` → `drop_session` → 容器 `rm -f` → `cleanup_completed` **照跑**；poison 仍不释放；`cleanup_quarantine` 只在清理本身失败时入队；没有 receipt 就没有追加记录（不变）；audit sink 照写。**通知时机**（Codex 批 A 审查 R2）：receipt 失败是本 attempt 唯一 fatal 时（非 s1_compat、无在途异常），在进入第一个清理 await 之前就经 `_notify_fatal_halt` 通知（worker 停 intake），尾部抛同一对象；termination 事实不可派生的尾部 fatal 同样提前通知；在途首因不被次生错误覆盖、只通知一次。

### 批 B：I03 统一期限、排队重算、到期取消的资源收口与原因传递

改：`generate.py::_generate_attempt`（入口算 deadline；materialize + 引导 + harness 段受同一绝对期限约束；-1 分支）、`_materialize_rollout_sandbox`（取消也清理持有资源）；`bringup.py::PerRolloutAdapter.open_session`（透传 deadline）、`ClaudeCodeDriver.run`（引导步骤超时 = `min(既有上限, remaining)`）；`docker_sandbox.py::_run`（取消时 kill 子进程再抛）；`capture_wire.py::CaptureRegistry.session_deadline/register`（显式设定，正式链不再首调懒起表）；`async_worker.py::ModelCallProxy._send/_call_inner`（信号量等待有界、拿到后重算 timeout、deadline 原因不被改写）；`bringup.py`（不再设 `default_session_budget_seconds`；`runtime_profile.json` 记 `episode_budget_seconds`）。

1. **一个 deadline**：`_generate_attempt` 入口 `episode_deadline = audit.started_monotonic + AGENT_TIME_BUDGET_SEC`。入口时刻 = miles 已占用并发槽、rh2 即将 `docker run`，是当前链上最早的 rh2 可见资源占用事件（`fully_async_rollout.py:205-230` 的组级信号量在此之前、rh2 看不见，按已批"从资源占用起表"取最早可见点，不冒充更早）。
2. **期限是强制保护，不只是审计**（Codex R2）：materialize、驱动引导（装 CLI、useradd/chown、写配置）与 harness 运行整段包在同一绝对期限内；驱动内 900s 的 useradd/chown 上限改为 `min(900, remaining)`；harness 的 `time_budget_sec = floor(remaining at launch)` 只是 vendored 兼容参数；remaining ≤ 0 → 不启动 CC，记 `harness_not_launched_budget_exhausted`，走既有 -1 分支（无 capture → missing → DROP）。
3. **到期取消必须收口持有资源**：`_materialize_rollout_sandbox` 的清理从 `except Exception` 改为 `except BaseException`（取消同样 rm 容器、拆私网、按已生成名字回收创建结果未确认的容器）；`docker_sandbox._run` 在 `CancelledError` 时 `proc.kill()` + `await proc.wait()` 再抛。停止 / drain（30s）/ 清理 / 评分**不在**该期限内，各用自己的有界预算；episode 到点不取消清理。
4. **排队计入**：`_send` 改为 `wait_for(sem.acquire(), remaining)`，超时 → `UnattributableModelCallError("episode_deadline_exhausted")`；拿到信号量后**重算** `_effective_timeout`。`_wait_active_before_send` 已按 remaining，不动。
5. **原因传递闭合**（Codex R2 探针复现）：`_call_inner` 目前把 `_send` 的 deadline 异常吸收改写为 `no_overlapping_update_window`；批 B 让 `episode_deadline_exhausted` 原样成为 poison reason 并经真实 `proxy.call` 到达 harness 取消分支：`audit.termination_kind_hint = "hard_wall_timeout"`，Outcome `termination_kind` 为 `hard_wall_timeout`（watchdog 族）而不是今天的 `api_failure`；completion 仍由事实推导（partial trace 作废 → missing）。单次请求的 900s attempt timeout **仍**归 api/inference 族，不叫 hard wall。`failure_category` 取 v2 validator 允许的既有枚举，不新增类别（实施时 T1 报告选了哪个）。
6. **数值不变、语义变**：`SWE_AGENT_TIME_BUDGET_SEC`（600）从"CC 启动后的运行预算"变为"资源占用起的 episode 预算"，准备、引导与排队都占用它——**T1**，并落 `runtime_profile.json`。不合并 policy_horizon / hard_wall 两个旋钮。**给 B 的提醒**：run6 实测 django 官方镜像的 `chown -R /testbed` 在 60s 超时、驱动为此放宽到 900s；准备计入后，600s 对这类镜像很可能在引导阶段就到墙，首次真实诊断前须与 B 一起选较宽数值（或把 CLI/用户预置烤进镜像，那是 B 线环境工作，不在本批）。
7. **观测**（audit 记录新增可选键 `episode_deadline`）：`budget_seconds`、`deadline_monotonic`、`remaining_at_harness_start`、`harness_time_budget_seconds`（驱动实际拿到的相对整数秒）、`remaining_at_harness_exit`、`harness_launched` / `bootstrap_seconds` / `remaining_at_launch`（驱动回填）、`model_call_queue_wait_seconds_total`（bringup 从 proxy 按 paid 取）、`hit_by ∈ {none, materialize, before_launch, bootstrap, harness_poll, harness_outer, proxy}`。

**已实施（2026-09-09，v2.3，含 Codex 批 B 聚焦审查 R1/R2/R3 修正）与计划的偏离：** (a) `hit_by` 的 proxy 侧只有一个值 `proxy`——三处判定（排队中 / 拿到额度后剩余不足 / 发送中到点）共用同一原因码 `episode_deadline_exhausted`，子环节只在错误文本里；(b) **准备阶段整体受期限约束**（R1）：物化 + HEAD 读取 + 基线 census 合为 `_prepare_workspace`，由同一 `_await_within_episode_deadline` 圈住；容器一物化所有权就交给外层 finally（census 阻塞被期限取消时容器不漏清）；(c) **到期取消的资源回收覆盖真实通道**（R2a/R2b）：物化默认 Docker 通道 `grading.manager.run_docker` 取消时 kill + wait 宿主 CLI（原只改了驱动的 `docker_sandbox._run`）；`create_attempt_network` 在 `network create` 等待响应时被取消 → 按预选名字有界 rm，确认删除 / 不存在才归还地址池槽位，否则槽位保持占用并经 `cancel_report` 落账（`remove_egress_network` / `egress_network_remove_failed`）；relay 接入途中被取消 → 复用既有 teardown（断开、rm、归还）；docker run 途中与之后的取消按名字回收容器并拆已登记私网；(d) **启动事实三态**（R3）：`launch_attempted`（False = 已知未尝试 / True = 已进入上游 run，不等于 CC 已启动）与 `launched`（False / None 未确认），编排只在 `launch_attempted is False` 时跳过 drain / 装配并归 `episode_deadline_in_bootstrap`；引导途中被外层期限取消也如实回填；引导步骤 timeout = min(上限, 剩余) 用浮点不取整，超时归因按"该步骤 timeout 是否由期限决定"判定，不看异常发生时是否刚好过墙；(e) 驱动回填走 task-local contextvar `HARNESS_LAUNCH_FACTS`（不改 vendored 的 `run` 签名）；(f) 取消收口期间抛出的 `FatalExecutionInfrastructureError` 原样传播（不被 `_settle_cancelled_stage` 洗成次生记录）；(g) 期限到点取消 harness task 只回收宿主侧 docker CLI 子进程，容器内 CC 进程仍由屏障 / 清理终止——"先强制停止再 drain"仍归批 C；(h) proxy 排队秒数在外层取消时也累计、审计 ACK 后释放。

### 批 C：I02 turn 预算事实 + rollout 侧 I14 停止 + hard wall 停止顺序

改：`capture_wire.py`（包装 `BaseAdapter._check_turn_cap`，与既有 `__init__`/`record_turn` 包装同机制；守卫增加"计数已达 N 时先等 inflight 归零"；`CaptureRegistry` 新增 `turn_budget_snapshot` / 预算命中订阅，与 poison 订阅同一 `call_soon_threadsafe` 机制）；`bringup.py`（`write_execution_audit_record` 增 `termination` 键）；`generate.py::_generate_attempt` harness_run/assemble 段（预算事件等待、强制停止、-1 分支先停止后 drain、非零退出的预算例外）；`quiescence_barrier.py`（把 `_KILL_SCRIPT/_COUNT_SCRIPT` 与"kill + 有界归零验证"抽成可复用函数，屏障①行为不变）。

1. **计数口径 = vendored `_check_turn_cap` 的前置条件**（Codex：读 body、预处理、closed 检查之后；不复制第三份解析）：计数仍由 vendored `_sid_turn_count` 完成，`MAX_TURNS_PER_SID` 仍传给 vendored 构造（唯一来源不变）；capture_wire 包装 `_check_turn_cap`：放行时透传，拒绝时记录 `turn_budget_exhausted_at` 并把响应换成 **403** `rh2_turn_budget_exhausted` + `x-should-retry: false`（与既有守卫拒绝同形状；不用 429——Anthropic SDK 把 429 视为可重试，403 不会；真实 CC 二进制对该响应怎样退出仍由 B 的真实探针确认，本批不把 SDK 规则写成已跑过的结果）。`count_tokens` 不经 `_run_turn`，不计。扣次后失败不退、CC 重发再计、同一请求内的引擎重算不另计。
2. **第 N+1 次不抢在第 N 次交付之前拒绝**（Codex R3 的并发接缝）：守卫在"计数已达 N"时先等该 sid 的 inflight 归零（受 episode deadline 约束）再放行到 `_run_turn` 被拒——否则并发请求下 CC 收到拒绝立刻退出，会把在飞的第 N 轮断连成 `client_cancelled` poison，第 N 轮白白丢失。N 是接纳数，不承诺 N 条成功生成；计数达到 N 不提前抹掉尚未交付的第 N 轮。
3. **真正停止**：拒绝发生后通知编排 → 等 CC 自行退出最多 `min(TURN_BUDGET_EXIT_GRACE_SEC = 30, remaining)`（常量，有界收口的候选实现值，不是额外行动预算；期间不接受新模型工作）→ 未退出则强制停止：`pkill -9 -u agent` + 有界进程归零验证，然后取消 `harness_task`（标记 `stopped_by_budget`，取消分支不再归 poison/外层取消）。
4. **归因与训练**：cap 事实**只解释"由预算拒绝导致的"非零退出 / 取消**：`termination_kind_hint = "max_turns_exhausted"`，`harness_exit_code` 原样记录；随后 drain → finish_session → 屏障 → 冻结 → 评分照常；quiescence + capture 闭合 → `present_truncated` → 批 D 注入的 KEEP_FULL → 真实 reward 进原组。cap 事实**不豁免**已有 poison / fatal / capture 不完整 / 外层取消（Codex R3）。**不伪造** `end_turn` 或采样 token：第 N+1 次请求根本没有渲染与采样，训练行 = N 轮真实生成。
5. **hard wall 停止顺序**：exit=-1 或期限到点 → **先**强制停止（同上）→ drain（CC 已死；bringup 已设 `handler_cancellation=True`，在飞 handler 随连接断开被取消，走既有 `_send_once` 取消分支广播 `/abort_request`）→ finish_session → 屏障（①再 kill 一次，幂等）→ 冻结。不再出现"CC 还在发请求时就等 inflight 归零"。
6. **cap 与 wall 同现，按既定规则**（Codex R3；撤回原稿的"以 cap 为准"）：episode deadline 到点时执行仍在进行（CC 未停）= 真实 hard wall → `hard_wall_timeout` → DROP，cap 事实保留在 `turn_budget` 块；执行已停止后清理越过期限**不算** hard wall（清理有独立预算），不补造。
7. **观测**（audit 记录新增可选键 `termination`）：`kind`、`turn_budget: {cap, accepted, exhausted, refused_at}`、`harness_exit_code`、`stop: {requested_by, forced, kill_verified, residual_processes, aborts_requested}`。

### 批 D：I04 处置注入 + grading 侧 I14

改：`bringup.py::ensure_fa_started`（注入）、`_start_sandbox_runtime`（`runtime_profile.json` 记 `disposition_policy`）；`grading/manager.py::run_docker`、`_exec_bash_checked`、`_remove_container`、`_container_running`。

1. 常量 `DISPOSITION_POLICY = DispositionPolicy(policy_horizon_truncation="KEEP_FULL", hard_wall_truncation="DROP_GROUP")`。`args.rh2_disposition_policy` 未设则注入；已设但与常量不符 → `StartupCheckError("disposition_policy_conflict")`（不许隐藏覆盖）。`owner_cancelled_truncation` / `agent_violation` 保持 None（未定；遇到仍 fail-fast，如实记录）。`policy_horizon` 共用槽位本轮只服务已批的 turn producer，不从它推导未来 token/context producer。库函数 `apply_member_disposition` 与 `DispositionPolicy` 的中立性不变。**注入必须先于或同批于批 C 的 cap 启用。**
2. `run_docker`：`communicate` 被取消 / 超时 → `proc.kill()` + `await proc.wait()` 再重新抛出（不留孤儿 CLI）。
3. **最终停止事实三分**（Codex R4）：有界收口后容器状态 = 已停止/已删除、仍运行、无法确认。`_container_running` 改为三态（inspect 失败 ≠ 未运行）；第一次 rm 失败但随后确认已停止 → 只留诊断，不 fatal；有界收口结束仍运行或无法确认 → 走既有 fatal 传播（A4"scope 最终无法终止 = run-fatal"），**并继续清理**，不只追加一段 `infra_failure_detail`。普通 `failed_to_grade` 不等于这个通道。不做 I16 的重评分；不推翻 I13 对中间等待超时后安全收口的例外。

## 4. 明确不变、不顺带做的

- 不定次数/秒数；不建 policy-owned 计时平台；不做 SkyRL 式成员梯度 mask；不新增 token/context horizon producer（`task_token_budget_exhausted`、`context_limit_reached` 只保留枚举）。
- 不做 I13 退出 verdict、I16 重评分、I15/I17 观测、I18 路由来源、子 agent 是否启用；不改 loss、gate、staleness、canonicalize、group_admission 的判定逻辑（只注入策略）。
- 不改 vendored slime 字节：cap 观测走 capture_wire 的方法包装；kill 脚本复用 rh2 自己的屏障脚本。
- 不为让旧测试变绿改 oracle；§5 列出的每处 oracle 变化都对应一条已批语义。

## 5. 测试：旧 → 新 oracle（T1）与新增反例

| 测试 | 变化 |
|---|---|
| `tests/adapters/test_w1b_termination_facts_producer.py::test_split_5_pre_finalize_task_local_failure_stays_aborted`、`tests/adapters/test_w1b_delivery_face.py::test_pre_finalize_validation_error_and_task_local_failure_stay_aborted` / `::test_missing_outcome_stays_aborted_without_admission_payload`、`tests/adapters/test_f2_2_capability.py::test_e2e_failure_path_produces_missing_outcome` | **T1（批 A 已做）**：typed `harness_bootstrap_failed` 保持 ABORTED；裸 `RuntimeError`/`TypeError` 改为 `FatalExecutionInfrastructureError("pre_finalize_failure_unclassified")`，且 finally 清理照跑、audit 落盘。新增 5b/5c/5d：裸异常、`_leaf_facts_fn` TypeError、两个账实矛盾码 → fatal。`ValidationError` 分支见 §6，未确认前 oracle 不动。 |
| `tests/adapters/test_b5_finalization.py::test_receipt_persist_failure_before_release_*`、`::…_after_release_run_halts_without_quarantine`、`::test_double_store_failure_first_cause_wins` | **T1（批 A 已做）**：仍抛 `finalization_receipt_write_failed`；`docker_rm` 出现在 `persist_receipt` 之后；`cleanup_quarantine == []`；无 `cleanup_skipped_receipt_failure`、有 `cleanup_started/cleanup_completed`；`cleanup_results == []`。新增：receipt 失败 + rm 失败 → 隔离队列有它、首因仍是 receipt。 |
| `tests/adapters/test_b5_finalization.py` 新增三例（批 A 已做） | 暂停 `drop_session` 观察清理等待期：receipt-only fatal 在清理前已通知、容器未动、放开后清理完成且尾部抛同一对象；在途首因 + receipt 失败 → 只通知首因一次；termination 事实不可派生 → 同样提前通知。 |
| `tests/adapters_miles/test_w1b_prepared_chain.py::_NoDocker` | **T2（批 A 已做）**：替身从抛裸 `FileNotFoundError`（现在 = 未归因 → fatal）改为返回非零 `ExecResult`（typed → sandbox_failure），测试语义不变。 |
| 新 `tests/adapters_miles/test_batch_a_failure_routing.py` | （批 A 已做）driver 单元：`SandboxExecError` → `harness_bootstrap_failed`（在表内）；裸 `RuntimeError` 不改名；typed `cc_version_mismatch` 透传。真实 driver → 真实 fa_formal 编排（移植 Codex `error_routing_probe.py`）：子进程层返回 124 → 真实 `exec(check=True)` 抛 `SandboxExecError` → ABORTED（`reason_code=harness_bootstrap_failed`，0 次 halt 通知）；安装函数内裸 RuntimeError / 引导后 RuntimeError / TypeError / typed 版本不符 → fatal（1 次通知、清理完成）。vendored 类须在测试体内导入（conftest 在测试间重置 `slime.*`）。 |
| `tests/adapters/test_capture_registry_fa.py::test_session_deadline_starts_on_first_call_and_is_bounded` | **T1（批 B 已做）**：显式 `register(deadline_monotonic=…)` 稳定、unregister 清理；未设定且无默认 → None（不再懒起表）；配置了默认预算的兼容路径保留。 |
| `tests/adapters/test_slime_generate.py::test_normal_path_a5_eight_questions_as_schema_instances` | **T1（批 B 已做）**：驱动收到的 `time_budget_sec` 从任务预算原值 900 改为 harness 启动时刻的剩余 episode 预算（= 审计块 `harness_time_budget_seconds`，899–900）。 |
| `MockSessionAdapter`、3 个 adapters_miles 链与 `experiments/s1_parity.py` 的 mock `open_session` | **T2（批 B 已做）**：签名增加 `deadline_monotonic=None`（编排现在显式下传；parity mock 漏改时 offline export / S1 parity 共 12 例在 s1_compat 下走旧兜底变 ABORTED，全量跑才暴露）。 |
| `tests/adapters/test_async_worker.py`（批 B 已做，+3；审查后 +1：排队中被取消也累计、ACK 后释放） | 信号量满时等待受剩余预算约束（0.2s 内拿不到 → `episode_deadline_exhausted`，不发请求，额度不泄漏，排队秒数累计）；排队 0.15s 后按剩余重算 timeout、发送在期限到点被中断 → 归 `episode_deadline_exhausted`；两者都**经真实 `proxy.call`** 断言 poison reason（不是 `no_overlapping_update_window`）；期限未到的单次 attempt timeout 仍归 `no_overlapping_update_window`。 |
| 新 `tests/adapters/test_budget_deadline.py`（批 B 已做，13 例 + 审查后 9 例） | 按调用次序给值的假钟：materialize 卡在 docker run 时到点 → 阶段被取消、容器按名字 rm、私网拆除、`episode_deadline_in_materialize`（hard_wall/missing）、CC 未启动；准备吃光预算 → 不开会话不启动 CC、`episode_deadline_before_launch`；harness 运行中到点 → harness task 被取消、`hit_by=harness_outer`、按 -1 语义收口为 hard_wall；驱动回填 `launched=False` → `episode_deadline_in_bootstrap`、不 drain 不装配；proxy 以 `episode_deadline_exhausted` 中毒 → `episode_deadline_during_model_call`（hard_wall，不是 api_failure），其它 poison 原因仍 api_failure；harness 正常结束后期限已过 → 照常评分交付、只记观测；`docker_sandbox._run` 取消时 kill+wait 子进程（Codex R2 探针缺口）；真实驱动引导受剩余预算约束（吃光 → 返回 -1 且不启动；充裕 → 以剩余秒启动；期限未到的引导失败仍 `harness_bootstrap_failed`）；per-rollout adapter 把 deadline 写进 registry。**审查后新增（真实接缝，移植 Codex 探针）**：census 阻塞过墙自动取消、不启动 CC、容器自清（预算 1s 真等，不跳钟）；`grading.manager.run_docker` 取消时 kill+wait；建网中 / relay 接入中 / docker run 中被期限取消 → 网络删除、登记清空、槽位归还、容器回收、无 cleanup 失败（三案参数化）+ rm 失败时槽位保持占用并留痕；真实驱动安装中被外层期限取消 → `launch_attempted=False` → `episode_deadline_in_bootstrap`、不 drain 不装配；取消收口期间抛 Fatal → 原样传播并通知；预算 600s、安装 0.3s → chown timeout 599.7（浮点）→ 归期限而非引导故障。 |
| `tests/adapters/test_f2_2_capability.py::test_hard_wall_exit_records_trigger_not_crash` | 批 B 已扩：`episode_deadline.hit_by == "harness_poll"`；批 C 再扩：-1 后 `termination.stop.forced=True`、kill 先于 drain（事件顺序断言）；保留原断言。 |
| 新 `tests/adapters_miles/test_budget_loop.py`（批 C/D） | (a) 经真实 aiohttp app + SGLang stub：cap=3 时第 4 次 `POST /v1/messages` 得 403 `rh2_turn_budget_exhausted` + `x-should-retry:false`，`count_tokens` 不计，vendored 计数器与 rh2 快照一致 `{cap:3, accepted:3, exhausted:true}`；第 3 次在飞时第 4 次到达 → 第 4 次的拒绝在第 3 次交付之后返回，无 poison。(b) 编排：cap 命中后 harness 退出码 1 → 不是 crash，`outcome.termination_kind == "max_turns_exhausted"`，屏障通过 → `present_truncated`，评分被调用、reward 来自 grader；harness 不退出 → 30s（可控时钟）后强制停止、`stop.forced=True`；cap 后拖到期限仍未停 → `hard_wall_timeout`、DROP；cap 与在飞 poison / 外层取消同现 → 不 KEEP；执行已停止后清理越界 → 不补造 hard wall。(c) 经 `_buffer` 与真实 `DefaultDataBuffer.put`：`ensure_fa_started` 注入后，turn 截断成员 KEEP_FULL 进组、hard wall 成员 DROP_GROUP、`owner_cancelled` 仍 `DispositionNotInjectedError`；`args` 预设冲突策略 → 启动报错。(d) `episode_deadline` / `termination` 键随 execution audit 落盘、不进 Sample metadata、不进 miles wire。 |
| `tests/grading/test_manager_unit.py` | 新增：挂起的 exec 被超时取消 → 子进程 kill/wait 被调用；rm 失败后 inspect=已停止 → 只留诊断；inspect=仍 running / inspect 不可用 → 有界收口后 fatal 通知且清理继续。宿主 CLI kill 与容器停止分别断言。 |
| `tests/adapters_miles/test_bringup_vendor_only.py` | 扩：`service.adapter.max_turns_per_sid == MAX_TURNS_PER_SID` 且 `_check_turn_cap` 已被 capture_wire 包装。 |
| `tests/adapters_miles/test_w1b_group_admission.py::test_truncated_member_fail_fast_without_injection_and_neutral_with`、`tests/governance/test_w1b_admission_disposition.py` | **不改**：库层中立性保持；注入发生在 bringup。 |

## 6. 待一次快速确认的 6 项（默认不动，不阻塞其余）

依据可开工清单 §4.2"I05 超出既有 D1 的异常分类：改变现行处置的部分列短表再确认"。这些码今天是 ABORTED（且有测试明确保护）；我与 Codex 计划审查一致建议改 FATAL，并同意它们是既有 D1/A4 的落实、不构成新 T0——所以只需 owner 一句话确认，不需要决策包。确认前，映射表把它们显式登记为现状（不再走 `unmapped_failure_code`）。

| 码 / 异常 | 今天 | 建议 | 理由与限定范围（Codex §1） |
|---|---|---|---|
| `fa_identity_incomplete_in_formal_mode` | 成员级结构化拒绝 → ABORTED | FATAL | 正式入口由我方写入 execution/member 身份，到编排时残缺 = 接线或入口违约，补采修不好。只限非 `s1_compat` 守卫 |
| finalize 前的 `ValidationError` | ABORTED（测试注明"不扩大 fatal 面"） | FATAL | 我方必需契约构造失败不因尚未到 finalize 就当可补采成员。只限 generate/adapter 编排边界；可选 telemetry 内自行处理的校验、模型工具/测试报错不扩大 |
| `frozen_artifact_persist_failed` | stage 兜底 → ABORTED | FATAL | 冻结补丁与基线是评分/准入核心事实，A4 核心记录持久化失败；不交付、通知停 run、继续清理 |
| `sampling_mask_tape_missing_in_assembly` | stage 兜底 → ABORTED | FATAL | 已要求记录 sampling support 却缺 tape 事实；只改该装配守卫，未启用 mask 的会话不受影响，合法空支持集 ≠ 缺失 |
| `rollout_image_digest_mismatch` | ABORTED（`test_rollout_image_digest_mismatch_aborts_and_cleans`） | FATAL | inspect 成功读取后 digest 与冻结事实不符 = 确定性环境完整性矛盾，补采只会选择性丢掉这类任务（Codex R1） |
| `rollout_testbed_lineage_failed` | ABORTED | FATAL | 同上：血缘核对成功读取后不符 |

用户确认任一项即并入批 A 的映射表（删掉该显式条目，对应测试 oracle 翻转并报 T1）；未确认保持现状。**实施约束**（Codex 批 A 审查 §4）：digest / 血缘两项切换时不能只删条目——`generate.py:4170-4178` 把第二次镜像 inspect **失败**与真实 digest **不符**合并在同一码，血缘的 `evaluate_probe` 也同时接受命令失败与内容不符；须在抛出点拆成“已识别局部查询失败（仍 ABORTED）”与“事实矛盾（FATAL）”两个码，避免把临时查询故障一并升级。

## 7. 验证方式与预期

```bash
cd rh2
uv run pytest tests/adapters/test_w1b_termination_facts_producer.py tests/adapters/test_w1b_delivery_face.py \
  tests/adapters/test_b5_finalization.py tests/adapters/test_async_worker.py tests/adapters/test_capture_registry_fa.py \
  tests/adapters/test_f2_2_capability.py tests/adapters/test_budget_deadline.py tests/adapters_miles/test_budget_loop.py \
  tests/adapters_miles/test_batch_a_failure_routing.py tests/adapters_miles/test_bringup_vendor_only.py \
  tests/adapters_miles/test_w1b_group_admission.py tests/governance/test_w1b_admission_disposition.py tests/grading/test_manager_unit.py -q
uv run pytest tests/ -q          # 期望：1779 + 新增用例数 passed，310 skipped 不变（需 Docker 的用例无 Docker 时 skip，计入 skipped）
uv run ruff check src tests
```

观测位置：`fa_execution_audit.jsonl` 每条记录的 `termination`、`episode_deadline`、`outcome_v2.termination_kind`、`timing_summary`；`runtime_profile.json` 的 `turn_budget_requests`、`episode_budget_seconds`、`disposition_policy`。

**不宣称：** 真实 Claude Code 对 403 拒绝的退出行为、`pkill` 后残留进程、目标 GPU 上 abort 广播的到达率——这些由 B 的首次真实诊断作业用上述 `termination.stop` 与 `harness_exit_code` 字段证明；本机只证明 aiohttp app、编排、准入与替身 docker 的链路。

## 8. 分级清单

- **T0**：无新增（原稿的"cap 覆盖真实 hard wall"已撤回，不再构成推翻既定决定）；§6 六项按"快速确认"处理，未确认部分不实施。
- **T1**：(1) turn cap 的拒绝形状 429→403 + 不可重试头，并由 capture_wire 包装 vendored `_check_turn_cap` 记录预算事实；(2) 守卫在计数已达 N 时先等 inflight 归零再拒绝第 N+1 次；(3) `SWE_AGENT_TIME_BUDGET_SEC` 语义从 CC 运行预算改为资源占用起的 episode 预算，且对 materialize/引导强制生效并在到期取消时清理持有资源；(4) proxy deadline 中毒的归因从 `api_failure` 改为 `hard_wall_timeout`（单次 attempt timeout 不变）；(5) 未归因异常 → `pre_finalize_failure_unclassified` fatal（含四处测试 oracle）、两个点名账实矛盾码与 `cc_version_mismatch` → fatal，局部引导故障的 typed 边界 = `SandboxExecError`；(6) receipt 失败仍清理（三处 oracle），且 receipt / termination 事实两条尾部 fatal 在清理 await 前先通知 halt；(7) 启动注入 KEEP/DROP 策略并拒绝冲突覆盖；(8) `rh2.fa.execution_audit.v1` 新增可选键 `termination`、`episode_deadline`（`schema_id` 不变）；(9) 批 B 第 5 条的 `failure_category` 选值；(10) grading 有界收口后仍运行 / 无法确认 → fatal 并继续清理；(11) 批 B 审查后：`grading.manager.run_docker` 的取消回收提前到 B（Codex 建议）；`episode_deadline` 观测块新增 `harness_launch_attempted`，`harness_launched` 改为 False / None 两态；`create_attempt_network` 新增 `cancel_report` 参数与 `reclaim_network_after_cancel` 辅助；批 A 的两个驱动测试改用非 124 的本地失败形态（124 在期限决定 timeout 的步骤上按构造归期限）。
- **T2**：`TURN_BUDGET_EXIT_GRACE_SEC = 30`、kill/验证脚本抽函数、映射表补齐既有 typed 码、`_NoDocker` 替身改写。

## 9. 对 B 的影响与接口

- `fa_execution_audit.jsonl` 每条记录可按 `termination.kind` 区分：`completed`（自然结束）/ `max_turns_exhausted`（turn 截断，训练）/ `hard_wall_timeout`（整组不训练，`episode_deadline.hit_by` 说明在哪个环节到点）/ 基础设施族（执行错误，`failure_records` 给根因）。`turn_budget.accepted` 与 `episode_deadline.remaining_at_harness_start` 直接回答"25 次/600 秒够不够、准备吃掉多少"，是定数值的实测来源。
- 预算数值仍用 `RH2_MAX_TURNS_PER_SID` / `SWE_AGENT_TIME_BUDGET_SEC` 两个既有 env，B 的诊断作业可按任务集自设；600 秒现在包含准备、引导与排队（见批 B 第 6 条的 django 提醒）。
- 本批期间 A 线独占修改：`adapters/slime/{generate,bringup,capture_wire,async_worker,quiescence_barrier,outcome_producer,docker_sandbox}.py`、`grading/manager.py` 的上述函数；B 线可继续改其它文件。

## 10. 审查与收口

Codex 计划审查已完成（[codex_plan_review.md](codex_plan_review.md)），R1–R4 全部 accepted，本稿即其停止条件要求的写回。之后按四个小批各自的行为边界做聚焦审查；修复后只复核对应问题与必要回归。本批完成的判据：§7 命令全过、§8 T1 项在 `infra.md` 登记、§6 的确认结果落到映射表。

## 11. 修订记录

- 2026-09-09 Codex 批 B 聚焦审查：R1（HEAD/census 未受期限强制）与 R2（真实物化 runner 取消、私网 create/connect 取消回收）为本批 P1；R3 引导事实/取整归因及排队观测为非阻塞项。共享 `manager.run_docker` 的取消回收需从 D 提前到 B，其余 C/D 分期保留。主审 181 项定向测试通过，独立探针确认上述缺口；见 [完整审查](batch_b_review/README.md)。

- 2026-09-09 Codex 修后复核：批 A 已实施范围通过，R1/R2 关闭；主审定向测试 45 passed、独立探针 8+7 案、10 文件 ruff 通过，复核期间源码/测试摘要未变。§6 六项仍未新增批准。termination 事实错误与 audit sink 同时失败时，通知与尾部异常可能不同；该既有诊断边界不阻塞本批，见 [复核 §6](batch_a_review/README.md#6-修后针对性复核2026-09-09)。

- 2026-09-09 v2.3（Codex 批 B 聚焦审查后，R1/R2a/R2b/R3 + §4 修复）：准备阶段（物化 + HEAD + census）整体受期限约束、容器所有权交外层 finally；`manager.run_docker` 取消回收；建网 / relay 接入 / docker run 三处取消路径回收网络、槽位、容器并留痕；驱动启动事实三态 + 浮点期限 + 引导取消回填；Fatal 不被取消收口吸收；排队秒数取消也记、ACK 释放。撤回 v2.2 偏离 (b)"私网创建途中残留"的残余登记。
- 2026-09-09 v2.2（批 B 实施）：批 A 提交 `6bb5ffe4`；批 B 按 v2 第 1–7 条实施，偏离见批 B 末段（proxy 侧 `hit_by` 单值、私网创建途中取消的残余、contextvar 回填启动事实、容器内 CC 的强制停止仍归批 C）；`failure_category` 选 `capture_incomplete`（T1 (9)）；观测块新增 `harness_time_budget_seconds`。
- 2026-09-09 v2.1（Codex 批 A 聚焦审查后，R1/R2 修复）：driver 只转换 `SandboxExecError`（新 typed 容器操作失败），不再按 RuntimeError 改名；finally 尾部两条 fatal 提前经 `_notify_fatal_halt` 通知；删除 `STRUCTURAL_CONTRADICTION_CODES` 公开常量（可简化项）；Codex §4 提示（digest / 血缘切换 FATAL 时须在抛出点区分查询失败与内容不符）登记为 §6 确认后的实施约束。
- 2026-09-09 v2（Codex 计划审查后）：R1 → 批 A 分类原则改为"已归因 task-local"而非"有名字"，`cc_version_mismatch` typed 且 fatal，digest/血缘不符移入 §6（六项）；R2 → 批 B 增加期限对 materialize/引导的强制、到期取消的资源收口（含 `docker_sandbox._run`）、proxy 原因传递闭合，B 线 django 引导耗时提醒；R3 → 撤回"cap 覆盖 hard wall"，改回既定规则，增加"第 N+1 次等第 N 次交付后再拒绝"；R4 → 批 D 最终停止事实三分，仍运行/无法确认 → fatal 并继续清理；守卫计数改为包装 vendored `_check_turn_cap`（同一前置条件，不复制解析）；依赖顺序 D 注入 ≤ C 启用；所有权补 `docker_sandbox.py`；I01 状态更新为已提交。
- 2026-09-09 v1：首稿。
