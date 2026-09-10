# 第 2 组剩余实施 Brief：丢组成本观测（I15/I20）、窄重评分（I16）、退出改判（I13）

日期：2026-09-09。作者：Claude（A 线）。状态：**v2.3——N1–N4 已实施提交（§9）；Codex 集成审查 R1–R7 已修复（§11）；[针对性复核](combined_review_20260910/followup1/README.md)（2026-09-10）R1/R3/R4/R5/R7 通过，R2 余项（P1）与 R6 余项（P2）已接受并修复提交（§12），待 Codex 只核对 R2 余项及直接回归。** 计划正文（§0–§8）保持 v2（按 Codex [计划审查](review_20260909/README.md) R1–R4 与 §5/§6 修正后）。 前置：预算终止闭环已由[第四次窄复核](../budget_loop_impl_20260909/combined_review_20260909/followup4/README.md)关闭（合同 A、F1 通过），本批不重开。

所用决定与链接：[决策分组 §4.1](../decision_batches_20260908.md)（I13 的 fork 文件、I15/I20、I16、I17/I20 纯观测均在已批实施位置表内）、[第 2 组决策](../batch2_failures_20260908/README.md)（I13 §3、I15 §4、I16 §5）、[I15/I16 补充说明 §8](../batch2_failures_20260908/i15_i16_sampling_and_retry_20260909.md)。I05/I12 已随预算闭环落地。第三组（I17–I20）owner 尚未决策：本批只做 §4.1 已批的纯观测部分，不碰 loss / 准入 / 路由来源。

## 0. 一句话

给"为什么丢、丢了多少成本"补可比较的事实（准确口径），给 grader 早期暂态故障一次追加评分（先接总期限与取消，再开循环），让"中途等待超时、最终安全清完"的作业按已批规则成功退出（只在证据完整时改判）。

## 1. 切片与顺序

| 切片 | 内容 | 分级 | 顺序 / 依赖 |
|---|---|---|---|
| N1 | 成本快照事件 + 汇总连接（I15/I20 观测） | T1 | 先做；不等第三组 |
| N2a | 评分工作总期限与取消接线（R1 前置） | T1（期限数值 = 配置默认值，T1；owner 可改） | N1 之后（共享 `generate.py` 串行） |
| N2b | 同工件最多追加一次评分（I16） | T1 | N2a 之后启用 |
| N3 | I13 改判：证据完整才成功 | T1（fork 文件按 §4.1 已批；补丁交付沿 `miles_spike/patches` 方式） | 与 N1/N2 不重叠，可并行 |
| N4 | I17/I20 单例支持集与 DIS 分布纯观测（§4.1 已批） | T1 | N1–N3 之后，或穿插；不改 loss / skip / 熔断 |

每片一次独立提交、各自旧→新 oracle、"已实施待审查"。共享文件 `generate.py`：N1（finally 段快照）与 N2（`_grade` 的 audit grading 块）串行集成，N1 先。

## 2. N1：成本快照与汇总连接

### 2.1 事实与口径（按审查 R3/R4 修正）

- 现有：fork `rh2_event_log.py` 的 `group_filtered`（`put_aborted` / `dynamic_filter` / `consume_stale`）与 `group_consumed`；rh2 `drop_events.py` 汇总。缺口：`put_aborted` 只有 `aborted_member` 与成员身份；三类丢弃都无轮数 / token / 耗时。
- **口径**：`response_length` 是首轮 prompt 之后整个 response 区域（含工具输出等 `loss_mask=0` 上下文），不是生成量，**不用**。用：`captured_output_tokens` = 该 attempt capture 记录里唯一已捕获输出 token 数（真实 tape 计数）；`trainable_tokens_total` / `input_tokens_total` = I01 的 `turn_coverage` 既有键（表示层可训动作量 / 训练行输入规模），不称梯度或 GPU 耗时；`accepted_turns` = 预算 registry 快照的接纳数；`elapsed_seconds` = 从资源占用起表（`started_monotonic`）到快照时刻。拿不到就 null，不填 0；多条 FORK 训练行属同一 physical attempt，只记一条。
- **含义**：事件名 `attempt_cost_snapshot`，在编排 finally 段、audit sink 之前发出；`disposition_hint`（present / aborted / fatal / cancelled）只是当时事实。**最终消费 / 丢弃由 buffer 事件判定**：之后仍可能 audit sink 失败、交付盖章失败、canonicalize 失败或取消未到达发射点，因此快照不承诺每个已发起 attempt 恰有一条终局，未关联项保留。可选事件构造 / 发射失败不改 receipt、交付与错误传播。

### 2.2 改法

- **producer**：`generate.py` `_run_finally_section` 内 audit sink 之前，`rh2_event_log.emit("attempt_cost_snapshot", …)`（未启用不发）。字段：六字段身份、`task_id`、`disposition_hint`、`termination_kind` / `reason_code` / `completion_class`（有 outcome 时）、`abort_reason`（aborted）、`elapsed_seconds`、`lifecycle_segments`（复用 `attempt_timing` 分段）、`accepted_turns`、`captured_output_tokens`、`trainable_tokens_total`、`input_tokens_total`、`capture_records`、`grading_outcome`、`hard_wall_hit_by`、`stop_before_deadline`。不含 prompt / patch / 私有内容。
- **summarizer**（`drop_events.py`）：`summarize_attempt_costs(rows)`——同 run 内按组身份（`rh2_prompt_group_id`）连接 `group_filtered` / `group_consumed` 与快照，`put_aborted` 行再按 `aborted_members[*].physical_attempt_id` 找根因成员。输出：按丢弃原因（真实 reason_code / hard wall / stale / zero_std）与被消费组分别的成员级 elapsed / turns / tokens 分布（min / p50 / max / unknown 计数）；**整组连带成本 = 同组所有已知成员的耗时之和**（例：七个 600s 成员 + 一个 5s 失败成员 = 4205s，不是 5s，也不是八条完整轨迹），多根因组保留原因集合、不跨桶累加称无重叠总量；组终局数仍是分母，成员观测数单列；旧格式 / 缺失 / 未匹配 / 无 buffer 终局的快照单独计数；保留 task 维度与消费侧对照。
- **不做**：不改 fork 事件字段（§4.1 允许必要时补 fork 三个分支的事实运输，本切片先不用）；不改处置；不建实时平台。

### 2.3 测试

- 真实 formal 链（`tests/adapters/test_budget_deadline.py` 旁新文件 `test_attempt_cost_snapshot.py`）：KEEP / hard wall / aborted / fatal 各一条，字段与 audit 一致；aborted 的 token 字段为 null；用真实 vendored `_SampleBuilder` 的例子核 `captured_output_tokens=4`、`response_length=104` 不被采用；**对照**：快照已发、随后 audit sink 失败（fatal）→ 汇总不算消费成功；发射函数抛异常时 delivered 与 receipt 不变。
- 汇总（`tests/adapters_miles/test_drop_events.py`）：七长一短组、多行同成员、多根因同组、外 run 行、缺失记录、旧格式行；分母与成员观测数分开。

## 3. N2：评分工作总期限、取消接线与窄重评分

### 3.1 事实（审查 R1）

`generate.py::_finalize._grade → bringup._grading_submit → GradingQueue.submit → worker → manager.grade` 没有评分总期限；`scoring_timeout` 只剩注释。`_ensure_image`（锁 / inspect / pull）与 `_start_container` 的 `docker run` 不受共同期限约束；提交方 `wait_for` 取消不会取消 worker 里的评分。已批条件要求准备、等待、重试共用一个有界评分预算。

### 3.2 N2a：期限与取消（先做）

- **入口**：编排 `_grade()` 在提交时建立 `deadline_monotonic = now + config.grading_deadline_seconds`（新配置，默认 3600s = 队列等待 + 镜像 + 准备 + 测试 1800s 的余量；数值是运行配置 T1，owner 可改），随同一 `_QueueItem` 传到 worker，再传入 `manager.grade(deadline_monotonic=…)`；入队反压与排队消耗同一期限。
- **约束实际工作**：manager 内每个 Docker 操作与阶段 `wait_for(min(阶段既有 timeout, 剩余))`；剩余 ≤ 0 → `GradingInfraError("grading_deadline_exhausted:<phase>")` → 现有 `failed_to_grade` / infra 族归类（不决定第四组 reward 规则）。测试阶段 `test_timeout_seconds` 同样取 min。
- **清理**：期限耗尽后仍沿既有独立清理预算（`cleanup_timeout_seconds`）收口容器；不因"总预算为零"跳过清理，也不在清理后获得新额度。
- **提交方**：`_grade()` 对 future 的等待 = 期限 + 清理预算余量，超时按既有 typed 传播；取消 / 收口期间的 typed fatal 仍走既有通道。
- **停止状态**：第二次尝试前读取 `manager._closed` 与 queue `_closing`（正常排空既有工作的合同不变）；shutdown / run-fatal 后不再启动追加尝试。

### 3.3 N2b：最多追加一次

- **允许位置**（补充说明 §8）：仅 `_ensure_image` 的 pull 与 `_start_container` 的 `docker run`；prelaunch / profile 违规、准备阶段、候选测试一律不重试。
- **分类**：`classify_docker_transport_error(op, exit_code, stderr) -> str | None`，输入含操作阶段与原始 CLI 返回；只对**已核对的 Docker CLI 错误形态**（固定前缀 / 完整短语，附来源注释的表）返回类别：daemon 连接类（`Cannot connect to the Docker daemon`、`error during connect`、`connection reset by peer`、`connection refused`、`broken pipe`）、registry / 传输暂态（`TLS handshake timeout`、`i/o timeout`、`net/http: request canceled`、`received unexpected HTTP status: 5xx`、`503 Service Unavailable`、`toomanyrequests`）。不按单独的 `EOF` / `timeout` 子串兜底；`not found` / `manifest unknown` / `pull access denied` / `unauthorized` / `invalid reference format` / digest 不符 / 未知非零码一律 None（不重试，沿原分类）。确定的配置 / 认证错误不被通用传输字样覆盖。
- **创建回包丢失**：`docker run` 命中可重试类别时，用本次名字构造 `_ContainerRecord` 并**登记进 `self._records`**，走 `_close_container_scope`：absent / stopped（已删或删除待清理）→ 允许第二次（新 nonce、新名字）；running / unknown → `GradingScopeTerminationError`（run-fatal），不重试。两次对象都进现有清理记录，`close()` / gc 都能看到。
- **循环**：`grade()` 内"镜像就绪 + 容器启动"段最多 2 次尝试（总计）；第二次前核对剩余期限与停止状态；两次都失败 → `failed_to_grade`，`infra_failure_detail` 带两次原始错误；成功 → 照常评分。同一冻结工件、同一配置、同一队列槽位、不重置期限；最终只交付一个评分。
- **记录**：manager `regrade_events`（上限 256 条，复用 `prelaunch_checks` 的截断方式）；`rh2_event_log` 事件 `grading_regrade`（trajectory、阶段、类别、第几次）；关停报告 grading 事实带计数；rollout audit grading 块记 `regrade_attempts`。`GradingReport` 公共 schema 不改。

### 3.4 验收（真实 queue → manager，Docker 替身）

排队耗尽；镜像锁耗尽；首次失败 + 旧容器收口吃光预算；第二次期间到期；提交方已取消（worker 仍受期限约束并收口）；shutdown / run-fatal 后不重开；stopped-but-not-removed 对象仍可清理且 `close()` 报 `containers_open=[]`；两次合计上限与只交付一次；pull 一次传输错误后成功；`connection reset` 后先按名收口再重试；`not found` / `unauthorized` / prelaunch 违规不重试；连续两次失败 → `failed_to_grade`；收口 unknown → run-fatal。文件：`tests/grading/test_manager_unit.py`、`tests/grading/test_queue.py`、`tests/adapters/test_w3a_formal_grading_freeze.py`。

## 4. N3：I13 改判——证据完整才成功

### 4.1 事实（审查 R2）

- fork `rh2_shutdown.py::close_rollout_fn_and_rh2`：`failure = shutdown_failure_from_aclose(...)`（problems：`aclose_raised` / `worker_unfinished` / `active_groups_unfinished` / `close_error` / `buffer_not_closed` / `deadline_exceeded`）；无其它首因时 `primary = failure`；`cleanup_ok`/`ok` 要求 `failure is None`。`FullyAsyncRolloutFn.aclose()` 缓存第一次报告，第二次调用拿旧快照。
- rh2 `LifecycleState` 登记的是 member 执行 task，清空不等于 miles `_worker` / `_active_groups` 的最终状态；"没有 fatal"不等于必要记录成功（取消期间 receipt 写失败只进 audit 次生失败）；`container_residue` 取隔离列表 / grader 记录，不是"所有 rollout 容器已确认删除"。

### 4.2 改法（最小充分）

1. **fork：最终状态复查**（`fully_async_rollout.py` 新增只读 `final_close_state()`：此刻 `_worker` / 每个 `_active_groups` task 的 done / cancelled / exception，收集晚到异常；不做第二次 `aclose()`，第一次快照保留作诊断）。`rh2_shutdown.py` 在合成 verdict 前调用它。
2. **rh2：执行、资源与必要记录的完成事实**（关停报告新增 `execution_closure`）：inflight 表清空（`unfinished_after_cancel_wait == []`）；已关闭执行的 receipt 全部持久化（audit 中无 `finalization_receipt_write_failed`）、audit sink 无失败；rollout 容器按 lease 逐个确认释放（`lease_released`）或按名 / label 查询确认不存在，隔离队列为空；私网登记为空；evidence 全部写成功；无 fatal。任一项拿不到证据 → 不解消。可选观测（N1 快照）写失败不属必要证据。
3. **只解消已验证消失的等待事实**：fork 侧把 problems 全部 ∈ {`worker_unfinished`, `active_groups_unfinished`, `deadline_exceeded`} 的 failure 标为"可解消候选"，**不再作为 first_cause 传给 rh2**（只作 external residue），rh2 报告在 `execution_closure` 完整且 `final_close_state()` 显示相关 task 已 done / cancelled 且无 exception 时把它记为 `resolved_wait_timeouts`（历史诊断）；fork verdict：`cleanup_ok` / `ok` 不因已解消的等待事实置 False，`shutdown_failure` 对象保留并加 `resolved_by_final_closure: true`。`aclose_raised` / `close_error` / `buffer_not_closed` / driver、worker 异常 / evidence 失败 / 原 dispose 错误 / 期限到点 / 无法确认——一律保持非零；已返回的非零不重写。
4. **期限所指** = 当前 owner-loop 关闭范围（900s 包住 aclose + rh2 close），不描述为整个 driver dispose 的统一期限；不另定数值。
5. **补丁交付**：fork 提交在 `reference/miles-rh2-integration` 的 rh2-integration 分支，`git format-patch` 存档 `miles_spike/patches/0017-*.patch`，更新 `integration_base_manifest.json`（expected_tree / patch sha256），跑 `rh2/scripts/miles_integration_lanes.sh` 两 lane。

### 4.3 验收

`tests/adapters_miles/test_w5a_miles_dispose_chain.py`（真实 fork verdict 与 rh2 报告合成）：首次等待 10ms 到期、60ms 安全结束 → `ok=true`，`shutdown_failure` 保留并标 resolved；同形态但 task 未结束 / 晚到异常 / 必要 receipt 写失败 / 容器未确认删除 → 仍 `ok=false`；driver / fatal / evidence 错误保持非零；不用手造 `resolved=true` 字段。`tests/adapters/test_w5a_shutdown_chain.py`：`execution_closure` 各项证据缺一即不解消。

## 5. N4：I17/I20 纯观测（§4.1 已批；不改 loss）

只在 `faithful_dis_loss.py` 现有 metrics 汇合处补：非单例支持集 token 数；**候选信号计数** = `loss_mask=1 ∧ DIS accepted ∧ support>1 ∧ advantage≠0`（不叫"有效梯度 token"，梯度抵消仍可能）；支持集大小有界分桶；ratio 两侧拒绝计数（复用 detached `log_ratio`，注明动作位与分母）；CP/DP 不重计。不加 actor forward、全 token 导出或逐 token 同步；不改 8 步熔断、skip 与 no-progress。测试：`tests/adapters_miles/test_faithful_dis_loss.py`、`test_w9_cp_faithful_dis.py` 补观测反例，loss / 梯度 / 分母 oracle 不变。

## 6. 验证、观测位置、对 B 的接口、修改归属

- 命令：`RH2_MILES_PATH=… uv run --no-sync pytest tests/grading/ tests/adapters/test_w5a_shutdown_chain.py tests/adapters_miles/test_w5a_miles_dispose_chain.py tests/adapters_miles/test_w4_consume_time_staleness.py tests/adapters/test_w3a_formal_grading_freeze.py -q`，全量 `pytest tests/ -q`，`ruff check src tests`；N3 另跑 lanes 脚本。
- 观测位置：`rh2_events_*.jsonl`（`attempt_cost_snapshot` / `grading_regrade`）、`drop_events.py` 汇总输出、关停报告 `execution_closure` / `resolved_wait_timeouts`。
- 对 B：N1 汇总可回答"丢的是不是长 / 难轨迹、各原因成本"（"长"不等于"难"）；N2 不改评分语义；N3 只改退出码解释。本文未发送给 B。
- 修改归属（唯一修改者 = Claude）：`generate.py`（N1 快照、N2 提交期限与 audit grading 块，串行）、`adapters/miles/drop_events.py`、`grading/manager.py`、`grading/queue.py`、`bringup.py`（`_grading_submit` 传期限、关停报告字段）、`shutdown/chain.py`、`adapters/miles/faithful_dis_loss.py`（N4）、fork `miles/utils/rh2_shutdown.py` 与 `miles/rollout/fully_async_rollout.py`（N3），及上述测试。

## 7. 明确不做

不改完整组准入、FIFO、staleness 数值；不给测试已发起后的失败加重试；不改 `GradingReport` / admission 公共 schema；不新建 supervisor / 重试服务 / 实时指标平台 / 指标闸门；不改 vendored slime 字节；不改预算数值；不改 loss / skip / 熔断 / 路由来源（第三组待决）；不重开预算闭环已关闭项。

## 8. 分级清单

- **T0**：无。
- **T1**：N1 事件与汇总口径；N2a 评分期限配置（默认 3600s）、期限与取消接线、`grading_deadline_exhausted` 归 infra 族；N2b 错误映射表、按名收口后重试、`regrade_events`、audit grading 块新键；N3 `final_close_state()`、`execution_closure` / `resolved_wait_timeouts`、fork verdict 合成变化、patches/0017 与 manifest；N4 观测指标；上述新增测试 oracle。
- **T2**：文档与注释。

## 9. 实施状态、偏离与证据（2026-09-09，写于提交后）

| 切片 | 提交 | 主要文件 | 状态 |
|---|---|---|---|
| N1 | `2fbe423e` | `generate.py`（`_run_finally_section` 快照）、`adapters/miles/drop_events.py`（`summarize_attempt_costs`、`--costs`）；`tests/adapters/test_attempt_cost_snapshot.py`（新）、`tests/adapters_miles/test_w4_drop_event_summary.py` | 已实施待审查 |
| N2a | `9c08d558` | `grading/manager.py`、`grading/queue.py`、`generate.py`（`_grade` 期限与提交等待）、`bringup.py`（`_grading_submit` 传期限）；`tests/grading/test_manager_unit.py`、`test_queue.py`、`tests/adapters/test_budget_deadline.py`、两个 W3a 冻结测试的替身签名 | 已实施待审查 |
| N2b | `93f854e6` | `grading/manager.py`（`classify_docker_transport_error`、`_ready_image_and_start_container`、`regrade_events`）；`tests/grading/test_manager_unit.py` | 已实施待审查 |
| N3 | rh2 `c77e8d05`；fork `4c04f997b`（rh2-integration-v3）→ patch `0017` + manifest `afaed0a7` | `shutdown/chain.py`、`bringup.py`；fork `fully_async_rollout.py`、`utils/rh2_shutdown.py`；`tests/adapters/test_w5a_shutdown_chain.py`、`tests/adapters_miles/test_w5a_miles_dispose_chain.py` | 已实施待审查 |
| N4 | `421e0709`（manifest 计数 `04d7a36f`） | `adapters/miles/faithful_dis_loss.py`（`_dis_observation_metrics`）；`tests/adapters_miles/test_faithful_dis_loss.py`、`test_w9_cp_faithful_dis.py` | 已实施待审查 |

### 9.1 T1 偏离与口径（相对 §2–§5 的计划文字）

1. **N2b：rollout audit 的 grading 块不加 `regrade_attempts` 键**。计划 §3.3 写了"audit grading 块记 `regrade_attempts`"；实施时选择不改 `RolloutAudit` 的固定形状（这是实现选择，不是"公共 schema 禁止"——Codex 集成审查 §6 指出前一版计划已允许该记录，措辞据此更正）。追加尝试的事实由 manager `regrade_events`（关停报告 grading 事实计数）+ `grading_regrade` 事件承载，`GradingReport.infra_failure_detail` 带两次原始错误。以后要进 audit 再单独提。
2. **N2a：`grading_deadline_seconds` 默认 3600s** 是运行配置数值（T1），owner 可改；`_grade()` 对 future 的等待 = 期限 + `cleanup_timeout_seconds` + 60s 余量（常量 `GRADING_SUBMIT_WAIT_MARGIN_SEC`），超时 → `FatalExecutionInfrastructureError("grading_submit_wait_exhausted")`（worker 不响应期限本身就是基础设施故障，不是 task-local）。
3. **N3：最终复查的等待上限 = 再等一个取消期限（`rh2_shutdown_deadline_sec`，默认 60s），且不超过由 dispose 总超时推出的 verdict 预算**（`timeout − min(1s, 10%)`）。计划 §4.2 只说"有界"；这里给了具体上界：一个在第一次期限后又整整一个期限仍未结束的 task 视为真实残留，不再等。因此 §4.3 写的"10ms 到期、60ms 安全结束"在实现下不成立（60ms > 2×10ms），验收改为"取消期限 0.2s 到期、任务在取消后 0.3s 收口"（第二个窗口 0.2s 覆盖 0.1s 的余量），三条双 loop 用例（安全收口 ok=true / 晚到异常 / 收口证据缺失）都走真实 fork verdict + rh2 报告合成，不手造 resolved 字段。
4. **N3：解消的所有权在 rh2**。fork 复查通过后调用 `bringup.resolve_external_wait_residue(final_state)`；rh2 只在 `ok_if_wait_residue_resolved`（清理全绿 ∧ 除等待快照外无残留 ∧ 证据全部写成功 ∧ 无首因 ∧ `execution_closure.complete`）时把等待行移到 `resolved_wait_timeouts`（含复查到的 `final_state`）并原子重写磁盘报告；fork verdict 读 rh2 自己的 `ok`。rh2 API 缺失（旧 rh2）或拒绝 → 维持非零，等待失败晚并入 rh2 报告首因、`trigger` 由 `owner_close` 升级为 `shutdown_failure`（新增于 `_merge_late_facts`）。
5. **N3：`execution_closure` 的容器证据只按 lease 记账**（每个 audit 的 `lease_released`）；计划里"或按名 / label 查询确认不存在"未做——关停链本来就不该在 verdict 时再起 Docker 查询（会把关停时长与 Docker 可用性绑在一起），lease 记账是本进程能证明的事实；未记账即不完整。另加 `orchestrator_present` 事实：装配态没有 orchestrator（启动回滚）时 attempts=0，容器项为空是真的空。
6. **N3 双 loop 测试装配**：miles-lane 的 `_assemble_rh2_service` 没有真实 rollout attempt（`orchestrator=None`），"收口证据缺失"用例给它一个只带一条未释放 lease 的 orchestrator 替身；receipt / audit sink 写失败、rh2 自己的未完成执行、evidence 失败、首因等各缺一即不解消的用例在 rh2 lane（`test_w5a_shutdown_chain.py`）用同样的替身逐项覆盖。
7. **N4 指标名与桶边界**（全部动作位 = `loss_mask=1`，本 rank 分片线性计数，跨 DP×CP 求和 = CP=1 值）：`dis_nonsingleton_provenance_tokens`、`dis_singleton_accepted_tokens`、`dis_candidate_signal_tokens`（`accepted ∧ support>1 ∧ advantage≠0`，只称候选）、`dis_zero_advantage_accepted_tokens`、`dis_rejected_low_tokens` / `dis_rejected_high_tokens`（与 `in_trust` 开区间互补，之和 = `dis_rejected_tokens`）、`dis_support_size_{1,2_3,4_7,8_15,16_plus}`（之和 = provenance）。支持集大小由 CSR offsets 差分、用与 loss_mask 同一 CP 切分函数取本 rank 分片；长度对不上时只放弃观测（返回空 dict），不新增拒绝路径。loss / 梯度 / 分母 / 零贡献旗标 / `sample_dis_accounting` 事件全部不变。
8. **N1 的汇总测试落在 `tests/adapters_miles/test_w4_drop_event_summary.py`**（计划写的 `test_drop_events.py` 不存在，汇总器测试历来在该文件）；`tests/adapters` lane 不能 import `repoharness2.adapters.miles`，快照与汇总的连接断言放在 miles lane。

### 9.2 证据（作者本机 CPU，不是 Codex 批准）

- `uv run ruff check src tests` 全过。全量 `RH2_MILES_PATH=… uv run --no-sync pytest tests -q`：****2230 passed, 0 skipped, 0 failed（152s）****（N3 提交前一次 768 项里唯一红的是 fork 树 digest 与 manifest 不一致，manifest 同步后归零）。
- `rh2/scripts/miles_integration_lanes.sh`：lane A **401 passed / 315 skipped**（skip 全部 integration_base）、lane B **716 passed / 0 skipped**；manifest 计数分两次同步（`afaed0a7`：预算闭环批 + N1 + N3；`04d7a36f`：N4 两例），expected_tree `c8687c9b` → `79e8ef65`、miles 源树 digest 更新、`rh2_patches_i13` 表、rebuild 至 0017。
- 没有真实 Docker / 目标 SWE 镜像 / 真实 Claude Code / 模型 API / GPU；评分侧 Docker 全部替身，N3 的"容器已释放"是 lease 记账事实。

### 9.3 请 Codex 聚焦的点（一次审查 + 针对性复核）

N3 的解消条件是否仍有假绿路径（尤其：`execution_closure` 的证据面是否漏了必要记录；`_merge_late_facts` 的 trigger 升级是否影响已有首因的报告）；N2b 的错误形态表是否有把确定性错误误判为暂态的条目；N4 指标口径是否与 CP 切分逐位对齐（`test_w9` 守恒断言已扩到全部新键）。停止条件：以上无 P0/P1 即收口，P2 记后续项。

## 10. 本批没有改变哪些已定案语义

完整组准入、FIFO、staleness 数值；预算数值（600s / 25 turns）与停止合同 A；`GradingReport` / admission / audit 公共 schema；loss / skip / 8 步熔断 / no-progress / 路由来源（第三组待决）；vendored slime 字节；取消期限本身（60s 默认）。

## 11. Codex 集成审查（2026-09-10）处置：R1–R7 全部接受并修复

审查：[combined_review_20260910/README.md](combined_review_20260910/README.md)（基线 `92d165aa`→`06dd7c06`）。逐项按协议四选一，全部 **accepted**；三个探针在作者本机复跑均复现（修前），修后副本（断言改为修后口径）全部通过。修复提交：代码与测试 `dc7a613b`，lanes manifest 计数 `647127c6`。

| 项 | 级别 | 处置 | 修法（最小充分） |
|---|---|---|---|
| R1 容器所有权 | P1 | accepted | `_start_container` 在 `docker run` **发出之前**登记 `_ContainerRecord`；创建失败 / 回包丢失 / 期限到点取消 / 外层取消 / prelaunch 失败一律在同一处按名有界收口（独立清理预算；absent → 干净，仍运行 / 无法确认 → `GradingScopeTerminationError`）。重试循环不再负责清理，只决定是否追加。配套：`rm -f` 得到 daemon 明确的 `No such container: <name>` 视为干净缺席（`absent_on_remove`），不再记清理失败（与 `_container_state` 的 absent 判据同款；连接类 "no such" 仍是失败）。 |
| R2 共同期限 | P1 | accepted | `_grader_prelaunch` 的可信 init 与 prelaunch 探针、`_verify_image_digest` 的两次 inspect 都经 `_await_within_grading_deadline`（期限先到归因 `grading_deadline_exhausted:<phase>`，不包装成 profile 违规）；`_read_peak_memory_mb` 期限已耗尽时不再发起 I/O，有剩余时受 min(剩余, 30s) 约束、超时记 0.0。 |
| R3 必要记录 | P1 | accepted | `RolloutAudit.necessary_records_complete`：finally 末尾 receipt 持久化成功 ∧ audit sink 成功返回才置 True（半途被第二次取消打断保持 False）；`execution_closure` 新增 `attempts_records_incomplete`（含前 20 个 id），任一 attempt 缺正向事实即 `complete=false`，等待类残留不解消。 |
| R4 停止后追加 | P2 | accepted（本轮修） | manager 新增 `stop_requested` 谓词（bringup 注入 `fatal_seen ∨ ¬grading_open`）；旧容器收口之后、追加之前读取，命中即放弃追加并记 `regrade_declined`（close() 报 `regrade_declined`）。**未**提前关闭 queue 排空（不重开 F1）。 |
| R5 跨 run 错连 | P2 | accepted（本轮修） | 汇总连接键改为 (run_id, 组 id) 与 (run_id, attempt id)。 |
| R6 分布维度与缺失口径 | P2 | accepted（本轮修） | 每桶 `by_root_cause`（导致成员按原因的成本分布）、顶层 `by_task`；终局 `member_count` > 快照数记 `groups_with_missing_members`，有未知成员或缺成员的组只进 `group_cost_seconds_known_partial`（下界），全未知记 `groups_cost_unknown`、不填 0。只改离线汇总（输出键新增，schema id 保持 v1）。 |
| R7 设备同步 | P2 | accepted（本轮修） | `_count` 直接返回 `flags.sum(dtype=float32)`，观测函数零次 `.item()`；docstring 补"最终日志 = 求和 ÷ num_rollouts 的每 execution 均值"口径。 |
| §6 小口径 | — | accepted | `close()` 的 `regrade_events` 明确为保留条数（≤256），另报累计 `regrade_total`；§9.1 第 1 条措辞更正（见上）。 |

### 11.1 T1 决定与口径

- `_remove_container` 对 "No such container/object: <本名>" 的处理从"清理失败 + absent 诊断"改为"干净缺席"：这是清理账目口径的收紧（避免每次未生效的创建请求留下两条假失败），不改任何评分或训练语义。
- `execution_closure.complete` 现在要求**正向事实**；装配态没有 orchestrator（attempts=0）仍为空真。miles-lane 与 rh2-lane 的 audit 替身默认带 `necessary_records_complete=True`，并各加一条"没有写失败记录但正向事实缺失"的反例。
- 探针副本（scratchpad，不覆盖 Codex 原始 JSON）只改三处：修前断言 → 修后口径；n3/observation 的 ROOT 路径；n2 `fatal_while_pull` 的 `make_manager` 传入 `service._grading_stop_requested`——探针自己构造 manager 顶替了 bringup 装配的那个，必须复现生产接线（`BringupService.__init__` 注入），否则 R4 修复不在被测路径上。维护测试的两个装配 helper 也同样接线。
- 测试 oracle 变更（T1）：`test_unknowns_legacy_rows_foreign_runs_and_unmatched_snapshots_are_kept_separate` 的组成本从数值 0 改为未知（R6 口径）。

### 11.2 新增反例（按审查 §6 复盘的三个接缝）

- 第二次创建失败 / 创建期间到期 / 创建期间外层取消（`test_manager_unit.py`：两次回包丢失两个名字都收口；到期与取消都收口；digest inspect 受期限约束；到期后不读内存、有剩余时读取有界；停止谓词放弃追加并留账；`No such container` 干净缺席 vs 连接类诊断仍失败）。
- 必要 sink 从未执行（`test_w5a_shutdown_chain.py`：formal 编排 + 真实 finally + 真实关停链，第一次取消后私网清理挂 0.8s，关停链在飞步第二次取消落在该 await 上——receipt 已写、容器已释放、无写失败记录、audit 文件不存在 → `complete=false`、不解消；对照网络立即完成 → 完整）。
- 默认多 run 输入（`test_w4_drop_event_summary.py`：同名组两 run 不混连；按根因 / task 分布；7/8 快照只给下界）；观测函数无主机标量读取（`test_faithful_dis_loss.py`）。

### 11.3 证据（作者本机，不是 Codex 批准）

ruff 全过；全量 `pytest tests -q`（集成树）**2245 passed, 0 skipped, 0 failed（159s；上一轮 2230 + 15 个新反例）**；lanes 清净环境实跑 lane A **404 passed / 316 skipped**、lane B **720 passed / 0 skipped**（manifest 计数 `647127c6`）。探针副本：n2 七案（含修后口径）、n3 两案（对照 ok=true；慢网络 `attempts_records_incomplete=1`、ok=false）、observation（10/100 分离、未知不为 0、7/8 下界、按根因与 task、`scalar_item_calls=0`）全部通过。没有真实 Docker / SWE 镜像 / CC / API / GPU。

### 11.4 请 Codex 针对性复核的收口条件（沿审查 §8）

R1：每个可能创建的名字都收口或明确 fatal；R2：到期停止全部工作且独立清理开始；R3：没有必要记录完成证据不成功改判；各正向对照与核心测试通过。P2 已随本轮修复，不另建 gate。

## 12. Codex 针对性复核（2026-09-10，followup1）处置：R2 余项与 R6 余项均 accepted 并修复

复核：[combined_review_20260910/followup1/README.md](combined_review_20260910/followup1/README.md)（基线 `06dd7c06`→`0313991c`）。R1 / R3 / R4 / R5 / R7 通过。两项余项都在作者本机用 Codex 的新探针复现（修前），修后副本通过。修复提交：代码与测试 `01b7f351`，lanes manifest 计数 `6d8f7f69`。

| 项 | 级别 | 处置 | 修法 |
|---|---|---|---|
| R2 余项：prelaunch 两个失败分支先 await 无 timeout 的 `rm` | P1 | accepted | 删除 `_grader_prelaunch` 里两处 `_remove_container` 等待，直接抛原 `SandboxProfileViolation`；record 由唯一调用方 `_start_container` 经 `_close_container_scope` 按独立清理预算有界收口（docstring 写明清理所有权）。 |
| R6 余项：失败成员成本 ≠ 整组连带成本；同 task 消费 / 丢弃成本混在一起 | P2 | accepted（本轮修） | 每桶新增 `by_root_cause_set`：整组连带成本按根因**集合**归属（单根因归该原因，多根因归 "a\|b" 组合键，不重复计入各单项）；成员缺失 / 未知的组只进该集合的 `group_cost_seconds_known_partial`，全未知只计数。`by_task` 新增 `consumed_member_fields` / `dropped_member_fields`（`member_fields` 仍为合计）。`by_root_cause`（失败成员自身成本）保留。 |

### 12.1 T1 口径

- **rm 卡住时的结果是 run-fatal，不是"违规照常上抛"**：`_close_container_scope` 的清理预算是 rm → inspect → kill → rm 的总额（D-2 合同，Codex 联合审查 R2 定案）；第一次 rm 卡满预算 = 无法确认停止 → `GradingScopeTerminationError` 替换 `SandboxProfileViolation`（两者同为 run-halt 通道），记录保留、`close()` 的 gc 再次清理。Codex 的探针场景（rm 阻塞 1s 预算）在修后正是这个结果，与其验收条件 b 一致；rm 及时返回时违规原样上抛、容器已删、无清理失败。
- 探针副本（scratchpad，不覆盖 Codex 原件）：n2_followup 16 案的 `prelaunch_violation_rm_hang` 断言改为修后口径（提交方 1.25s 内收到 `GradingScopeTerminationError`、worker 槽空、记录保留、`close()` 后 `containers_open=[]`）；cost_diagnostic 加断言"交换正常成员成本后汇总必须不同、根因集合成本 4205/75 随之交换"。
- 新增反例：可信 init 失败（rm 及时 / rm 卡住 / rm 卡住且状态未知）与 prelaunch 检查不合格四例（`tests/grading/test_w3b_grader_profile_unit.py`）；根因集合归属随成本交换而交换、多根因只进组合键且成员缺失只给下界、同 task 消费 / 丢弃分开三例（`tests/adapters_miles/test_w4_drop_event_summary.py`）。

### 12.2 证据（作者本机，不是 Codex 批准）

ruff 全过；全量 `pytest tests -q`（集成树）**2252 passed, 0 skipped, 0 failed（158s；上一轮 2245 + 7 个新反例）**；lanes 清净环境实跑 lane A **407 passed / 316 skipped**、lane B **723 passed / 0 skipped**（计数 `6d8f7f69`）。没有真实 Docker / SWE 镜像 / CC / API / GPU。请 Codex 按其 §5 停止条件只核对 R2 余项与直接回归；R6 余项已一并修复，若认可即可关闭。

