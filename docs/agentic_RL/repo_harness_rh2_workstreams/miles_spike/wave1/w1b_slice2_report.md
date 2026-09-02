# W1b 第二段实现报告：三终态 + 组准入 + 薄处置边界 + A3 落地

日期：2026-09-02。执行依据：06 计划 §1 A2/A3/A6（D1 已批）、§3 W1b 行（含"第二段须知"）、§4 D1、附录 A
两层判定与 reason-code 表；切片一报告 `w1b_slice1_report.md`（§8 修复节，post-finalize 失败域五分流
**原样保留、未回退**）。本文同时充当本切片的 implementation-notes。工作树状态：本切片未 commit / 未 stash；
并行的 W5a 关停链已由另一 agent 提交（`52e78b44` 删 lifecycle 原型、`466cfd0b` W5a），本切片改动叠在其上。

## 0. 交付物清单

| 文件 | 性质 | 内容 |
|---|---|---|
| `rh2/src/repoharness2/governance/admission.py` | **新增** | 交付面 typed 载荷 `AdmissionPayloadV1`（内嵌 `RolloutAttemptOutcomeV2` + `EligibilityReport`）+ producer/consumer 边界 `derive_admission_payload` / `stamp_admission_payload` / `resolve_admission_payload` + 薄处置边界纯函数 `decide_member_disposition`（附录 A 两层判定，reason-code 表 `_DIMENSION_REASON_VERDICTS` / `_REASON_PREFIX_VERDICTS`）+ 显式注入位 `DispositionPolicy`（四槽位默认 None）+ `DispositionNotInjectedError`。零 miles/slime import |
| `rh2/src/repoharness2/adapters/miles/group_admission.py` | **新增** | miles `--dynamic-sampling-filter-path` 唯一入口 `rh2_group_admission_filter`（`GROUP_ADMISSION_FILTER_PATH`）+ 与 miles 类型解耦的 `admit_group`（prompt_group↔group 对账、结构矛盾 `GroupAdmissionFatal`、全员 KEEP_FULL 合取、零方差）+ `AdmissionWiringError`。模块级零 miles import（`DynamicFilterOutput` 函数内延迟 import） |
| `rh2/src/repoharness2/governance/gate.py` | 修改（A3） | 删除 `S1_TIER_CAP` / `S1_CEILING_REASON_CODE` / cap 应用分支；`GATE_VERSION` `rh2.gate.s1.v1` → `rh2.gate.w1b.v2`（被动升版）；新增 `SandboxCapabilityFacts` + `REQUIRED_SANDBOX_CAPABILITIES`；security 维改为"正向能力事实在场且无违规"（`sandbox_capability_facts_missing` / `sandbox_capability_unverified_<name>` / `sandbox_capability_violation_<name>`），`_evaluate`/`_check_wiring` 接能力事实 |
| `rh2/src/repoharness2/governance/wrapper.py` | 修改 | `finalize_rollout(..., sandbox_capability_facts=None, sandbox_capability_facts_required=True)` 透传（默认 required=True，fail-closed） |
| `rh2/src/repoharness2/governance/__init__.py` | 修改 | 导出面：删两个 cap 常量，加 `SandboxCapabilityFacts` / `REQUIRED_SANDBOX_CAPABILITIES`；模块分工 docstring 加 admission.py |
| `rh2/src/repoharness2/contracts/eligibility.py` | 修改（仅文本） | 三处 cap 叙述文本（docstring / 字段说明 / 校验消息中的"S1 默认封顶"例子）删除；**零 schema 改动** |
| `rh2/src/repoharness2/adapters/slime/generate.py` | 修改 | ① `SlimeBindingConfig.staleness_threshold: int \| None = None`（无隐式默认）+ `S1_COMPAT_LEGACY_STALENESS_THRESHOLD = 4`（仅 s1_compat 冻结路径）+ `validate_execution_config` fa_formal 缺阈值启动即拒 + `_build_handshake` 非 s1 缺阈值 run-fatal；② 三终态交付面：`_deliver` 非 s1 模式不再把 degraded 压成 abort，新 `_deliver_present_member`（真实样本 + `rh2_admission` 载荷；reward 不可得用 NaN 占位）；两处 unsafe 分支改走真实交付；`_abort_result(audit=…)` present 守卫 `abort_shape_for_present_outcome`；③ `sandbox_capability_facts_provider` 注入位 + `_finalize` 透传能力事实（s1_compat 显式 required=False）；④ `generate()` 的 `termination_facts_stamp_conflict` 经现有 audit sink 追加 attempt-bound fatal 事实（`_append_post_receipt_fatal_fact`） |
| `rh2/src/repoharness2/adapters/miles/generate_fn.py` | 修改 | 非 s1 模式派发前守卫 `_assert_group_admission_filter_wired`（`args.dynamic_sampling_filter_path` 必须指向复合 filter）；身份/分派盖章后 `_verify_admission_binding`（载荷按叶身份 join 得回来） |
| `rh2/tests/governance/test_w1b_admission_disposition.py`（46 例）、`test_w1b_security_capability_facts.py`（16 例）、`rh2/tests/adapters/test_w1b_delivery_face.py`（14 例）、`rh2/tests/adapters_miles/test_w1b_group_admission.py`（24 例，双 lane） | **新增** | 见 §9 |
| 既有测试 oracle/夹具改动（逐个登记 T1，见 §7） | 修改 | governance 四文件、test_slime_generate、test_b5_finalization、test_f2_2b_b3_hygiene、test_f2_2_capability、test_offline_export、test_s1_parity + `experiments/s1_parity.py`、三个 adapters_miles 夹具 |

**未触碰**：`bringup.py`（含 :705 挡板）、`lifecycle.py`（W5a 已删）、shutdown/关停文件、`faithful_dis_loss.py`、`training_view.py`、`prepared_tasks.py`/`trusted_prep.py`、`canonicalize.py`（无需改：交付面 metadata 经既有 `dict(s.metadata)` 复制即达 miles 叶）、`identity.py`、`termination_facts.py`（切片一 F5 语义原样，第二段只消费）、`reference/`、`contracts/` 除上述文本、lanes manifest（集成者改）。

## 1. 三终态在交付面的落点（代码事实，`rh2/src/repoharness2/adapters/slime/generate.py`）

| 终态 | 落点 | 语义 |
|---|---|---|
| ③ 完整 finalize 但（可能）不合格 → 真实 COMPLETED/TRUNCATED 样本 + typed 载荷 | `_deliver` :4140-4181（s1_compat 保留旧 abort 分支 :4140；非 s1 一律 :4174-4181 转 `_deliver_present_member`）；`_deliver_present_member` :4198-4292 | 叶 token/mask/logprob/provenance 真实、`remove_sample=False`（:4264-4265）、reward = GradingReport.reward，**不可得时 `float("nan")`**（:4262，理由见 §7-4）、派生视图两键只在有报告时写（:4267-4270）、`stamp_admission_payload` 盖 `rh2_admission`（:4272）、`step9_samples_delivered` + 观测标记 `degraded_member_delivered_for_group_admission` / `present_member_delivered_without_report`（:4286-4291） |
| ③ 契约封闭豁免集（unsafe artifact 永久拒绝，present_complete + reward 不可得 + 无 EligibilityReport） | export 不支持对象分支 :3027、hygiene 筛查分支 :3154 → `_deliver_present_member(finalized=None)` | 不再 `_abort_result`（那会把 present 事实改写成 ABORTED）；receipt 因 step9 变为 `delivery_prepared`（样本备好交回 miles，不代表进训练），权威归因仍在 `outcome_v2.reason_code`；bringup 审计 disposition 仍派生 `permanent_rejected`（测试钉死） |
| ② 已归因 task-local 故障 → 真实 ABORTED | 既有 `_abort_result` 调用点（audit_only :2836、quiescence 拒绝 :3104、snapshot 不匹配 :3193、通用 except :3300）全部 `audit=audit` | 只允许 `completion_class=missing` 或尚无 Outcome（身份不全的结构化拒绝）；由 miles `put()` 交 unused handler（retry/drop 归 B） |
| ① 结构矛盾 → typed raise（run-fatal 通道，与切片一 `FatalExecutionInfrastructureError` 一致） | `_abort_result` present 守卫 :4520-4536（`abort_shape_for_present_outcome`）；载荷派生矛盾 :4243-4260（`admission_payload_build_failed`）；盖章冲突 :4273-4285（`admission_payload_stamp_conflict`）；无 Outcome 到交付面 :4223-4228（`admission_payload_without_outcome`）；握手缺阈值 :3878-3883（`staleness_threshold_unconfigured`） | 通用 except 内触发的 fatal 也经 `_notify_fatal_halt`（:3363-3372）；切片一的五分流（verify_integrity 异常 / producer 异常 / sidecar 写失败 / 未分类 post-finalize）逐字未动 |

切片一开放问题 3（"deliver 阶段失败后事实说评分完整但样本是 abort 形状"）的收口：deliver 阶段的失败自切片一修复轮起
全部 run-fatal（不交付）；本段再加 present 守卫——非 s1 模式下任何 present Outcome 走 abort 形状都是 fatal，
"abort 形状 + 完整事实"在交付面上不可达（`test_abort_shape_for_present_outcome_is_fatal`）。

**miles 侧对应**（`adapters/miles/generate_fn.py`）：非 s1 派发前 `_assert_group_admission_filter_wired` :80-96/:147
（守卫先于铸造与任何生成，`test_generate_fn_refuses_dispatch_without_admission_filter_wired` 断言 `audits == []`）；
盖章后 `_verify_admission_binding` :66-77/:211。

## 2. 薄处置边界纯函数（`governance/admission.py`）

签名（:528）：

```python
def decide_member_disposition(
    payload: AdmissionPayloadV1,
    *,
    policy: DispositionPolicy,
    finalize_staleness_threshold: int | None,
) -> MemberDisposition   # MemberDisposition(verdict=KEEP_FULL|DROP_GROUP|FATAL, reason_code, layer, detail)
```

输入 = base eligibility facts（`payload.eligibility_report.facts`，七维 reason_code）∧ termination disposition
（`payload.outcome.completion_class/termination_kind` + `policy` 注入）∧ finalize-time staleness（report 的
`policy_staleness` 维 + 显式阈值）。**不设 MASK_MEMBER**（`DispositionPolicy.__post_init__` 拒绝 KEEP_FULL/DROP_GROUP
之外的取值，`test_disposition_policy_rejects_mask_member_or_unknown_values`）。

fail-fast 证据：

- `finalize_staleness_threshold` 为 None/bool/负数/非 int → `AdmissionError(staleness_threshold_not_configured)`（:545-556；
  `test_explicit_staleness_threshold_required` 四参数化）；载荷记录的 finalize 阈值 ≠ 传入权威值 → FATAL
  `staleness_threshold_authority_mismatch`（:580-586；`test_staleness_threshold_authority_mismatch_is_fatal`）。
- `DispositionPolicy()` 四槽位默认 None（:129-160，没有任何隐藏默认答案）；纯函数**只在该槽位真正决定结论时**读取——
  present_truncated 且七维全过（或 pending 已注入 KEEP）时读 `{policy_horizon|hard_wall|owner_cancelled}_truncation`
  （:636-648），命中 hygiene/agent 违规且无其它 FATAL/DROP 时读 `agent_violation`（:614-628）；读到 None 即抛
  `DispositionNotInjectedError(slot)`（reason_code `disposition_not_injected:<slot>`）。
- 双注入中立：同一 present_truncated 载荷，五个 termination_kind 各自参数化——未注入 raise、注入别的槽位仍 raise、
  注入 KEEP_FULL → `KEEP_FULL/truncation_<slot>_kept`、注入 DROP_GROUP → `DROP_GROUP/truncation_<slot>_excluded`
  （`test_present_truncated_requires_explicit_injection_and_chain_is_neutral`）；hygiene 同样双注入
  （`test_agent_violation_requires_injection_and_is_neutral`）。真实 miles buffer 层再验一次
  （`test_truncated_member_fail_fast_without_injection_and_neutral_with`：harness exit=-1 → hard_wall_timeout →
  `put()` 抛 `DispositionNotInjectedError`；注入 KEEP 进 buffer、注入 DROP 记 `drop_admission_truncation_hard_wall_excluded`）。
- 其它维度已 DROP 时不读槽位（附录 A"七维全过再应用 disposition"）：`test_truncation_disposition_not_consulted_when_dimensions_already_drop`、
  `test_pending_not_consulted_when_another_dimension_drops`；FATAL 优先于 pending（`test_fatal_dominates_pending_and_drop`）。

## 3. 复合 group filter 的对账与核对字段（`adapters/miles/group_admission.py`）

miles stock `DefaultDataBuffer.put()`（`fully_async_data_buffer.py:133`）只把 `input.group` 交给 dynamic filter，
`prompt_group` 不在签名内——因此"prompt_group ↔ group 对账"用的是 miles 从派发 prompt 样本**逐字复制**到每个生成样本上的
组事实（`Sample.group_index` / `Sample.index`；canonicalize 已在 generate 边界钉死输出 index/group_index == 输入）、W1a 从
同一组事实铸造的六字段身份、以及 bind 时经 prep manifest 核对过的分派三元组（T1-2）。`admit_group` :288-441 逐项：

| 核对面 | 字段 / 规则 | 违反 → `GroupAdmissionFatal.reason_code` |
|---|---|---|
| 组形状 | `len(group) == args.n_samples_per_prompt`；成员 = `Sample` 或非空 `list[Sample]`（fan-out 叶） | `group_shape_mismatch` |
| 六字段身份（`_read_identity` :171-217） | 六键在场且类型正确；`rh2_prompt_group_id == f"miles_g{group_index}"`；`0 <= slot < n`；`rh2_rollout_execution_id == f"{gid}_m{slot}"`；`rh2_physical_attempt_id` 以 `f"{execution}#p{seq}-"` 开头且 seq ≥ 1 | `identity_missing` / `identity_field_malformed` / `identity_group_mismatch` / `identity_slot_out_of_range` / `identity_execution_mismatch` / `identity_attempt_mismatch` |
| prompt_group ↔ group | 每叶 `sample.group_index == 身份 group_index`、`sample.index == group_index*n + slot` | `prompt_group_index_mismatch` |
| 组级 | 同 group_index、同 (task_id, environment_package_digest, public_bundle_digest)；slot / attempt / execution 两两不同；slot 集合 == 0..n-1 | `mixed_group_members` / `member_slot_duplicated` / `attempt_id_reused` / `execution_id_reused` / `slot_set_mismatch` |
| admission 载荷（`resolve_admission_payload`） | `AdmissionPayloadV1.model_validate`（重跑 EligibilityReport 五连锁含 **facts_digest 重算**、Outcome v2 全部不变量、载荷自身一致性）；attempt id、execution id、task_id、environment_package_digest、public_bundle_digest 逐字 == 样本键；派生视图 `eligibility_report_ref`/`training_eligibility_class` 有报告时 == report.report_id/eligibility_class、无报告时必须缺席 | `admission_payload_missing` / `admission_payload_invalid` / `admission_attempt_mismatch` / `admission_execution_mismatch` / `admission_task_mismatch` / `admission_environment_mismatch` / `admission_public_bundle_mismatch` / `derived_view_mismatch` / `derived_view_without_report` |
| termination 事实 ↔ 载荷（`_check_facts_vs_payload` :269-285） | attempt、execution、task_id、outcome_id、termination_kind、eligibility_report_id、grading_report_id、fresh_grading_complete ⟺ grading_report_id 在场 | `termination_facts_unresolvable` / `admission_termination_facts_mismatch` |
| 声称 vs 交付形状（`_check_leaf_shape_claims` :219-266） | `remove_sample` 必须 False；`outcome.reward_unavailable` ⟺ 样本 reward 为 None/NaN，否则样本 reward == GradingReport.reward；报告 online ⟹ loss_mask 有 mask=1、logprobs 长度 == loss_mask == response_length、tokens ≥ response_length、weight_versions 非空 | `remove_sample_on_delivered_member` / `reward_present_but_unavailable_claimed` / `reward_mismatch_on_delivery` / `online_claim_without_trainable_provenance` |
| fan-out | 同成员全部叶：身份六字段、载荷、事实、分派三元组、reward 逐字相同 | `fan_out_leaf_identity_forgery` / `fan_out_leaf_payload_forgery` / `fan_out_leaf_reward_mismatch` |
| 生命周期 | 叶 status ∈ {completed, truncated}；ABORTED 叶到达 filter = 接线矛盾（miles put() 应先交 handler） | `member_status_not_delivered` / `aborted_member_reached_filter` |
| 权威配置 | 阈值 = `args.rh2_orchestrator.config.staleness_threshold`（与交付面同一 SlimeBindingConfig 对象；`GenerateFnInput.args` 与 buffer 的 `args` 是同一 Namespace——`FullyAsyncRolloutFn.__init__` 已核实）；处置 = `args.rh2_disposition_policy`（缺席 = 四槽位 None） | `staleness_threshold_authority_unreachable` / `disposition_policy_invalid` |
| 准入 | 每成员 `decide_member_disposition`：FATAL → raise；任一 DROP → `keep=False, reason=admission_<code>`；全员 KEEP_FULL → reward 全组相同（pstdev ≤ 1e-8，与 stock 同阈值）→ `keep=False, reason=zero_std_<r>`；否则 `keep=True` | `keep_full_without_reward`（账实矛盾） |

结构矛盾**必须 raise**：`test_structural_contradictions_raise_from_real_buffer_put`（13 参数化，经真实 `DefaultDataBuffer.put()`
抛 `GroupAdmissionFatal`，buffer 与 unused handler 均为空）。keep=False 的固定丢弃：`test_degraded_member_drops_whole_group_and_nothing_reaches_conversion`
（`buf._buffer == []`、`recycled == []`、miles 指标 `rollout/dynamic_filter/drop_admission_reward_scope_none == 1`，零样本进 conversion）。

## 4. A3 删除清单与 security 维新语义

删除（`governance/gate.py` + `governance/__init__.py`）：`S1_TIER_CAP` 常量、`S1_CEILING_REASON_CODE` 常量、
`_evaluate` 内 cap 应用分支（原 :611-623 的 merit/final/cap_applied 三段与 `reason_codes.append(S1_CEILING_REASON_CODE)`）、
包级导出、GroupRepairSignal/EligibilityReport 文本里的封顶叙述。测试侧删除"cap 未解"负例：`test_s1_tier_cap_constant_pinned`
→ 改为 `test_s1_tier_cap_deleted_and_gate_version_bumped`（断言常量不存在 + 版本号）。全仓 `S1_TIER_CAP|s1_default_ceiling`
在 src/experiments/scripts 零残留（docs 历史文档保留，不改写批准史）。

新语义（`_dim_security_and_leakage` :432-499）：`capability_facts_required=True` 时 `SandboxCapabilityFacts` 缺席 →
`sandbox_capability_facts_missing`；`REQUIRED_SANDBOX_CAPABILITIES`（九项，名字取自 06 W3b 行）任一未在
`verified_capabilities` → `sandbox_capability_unverified_<name>`；任一 `violations` → `sandbox_capability_violation_<name>`；
finding/hygiene/marker 三类既有规则不变。`required=False`（**只**由 s1_compat 冻结路径与 s1 parity 的 verifiers 对照路径显式声明）
时保持旧语义并在 evidence 记 `sandbox_capability_facts:not_required`。`findings=()` 不再构成"安全"
（`test_missing_capability_facts_is_not_online_even_with_no_findings`）。`GATE_VERSION = "rh2.gate.w1b.v2"`（被动升版）。

W3b 落地前 formal 路径的预期形态：orchestrator `sandbox_capability_facts_provider=None` → 每个 formal 样本
security 维 `sandbox_capability_facts_missing` → class audit → 真实交付 + 载荷 → filter DROP_GROUP
（`test_all_ok_without_capability_facts_is_delivered_but_drops_by_a3`、`test_missing_capability_facts_drops_group_by_a3`）。
KEEP_FULL 可达性由测试注入 provider 证明（`test_all_ok_with_capability_facts_is_online_and_keep_full`、
`test_full_chain_keep_full_group_reaches_real_conversion`）。

## 5. staleness 两阶段接口（D1-4）

- finalize-time：`SlimeBindingConfig.staleness_threshold: int | None = None`（:1868，**无隐式默认**）；fa_formal 构造
  orchestrator 即 `StartupCheckError(staleness_threshold_required_in_formal_chain)`（:1644-1655）；非 s1 模式握手构造缺阈值
  → run-fatal `staleness_threshold_unconfigured`（:3874-3883）；s1_compat 为 None 时回退 `S1_COMPAT_LEGACY_STALENESS_THRESHOLD = 4`
  （:1842，冻结路径零改变；见 T1-6）。判定消费 EligibilityReport 已有 `policy_staleness` 维（不忽略、不重算），载荷携带
  `finalize_staleness_steps/threshold`，validator 钉死"steps ≤ threshold ⟺ 维 ok"（`test_payload_pins_finalize_staleness_against_report_dimension`）。
- consume-time：由 miles `buffer.get()` 按 `--max-weight-staleness` 复查，归 W4，本段不做；`max_weight_staleness` 唯一语义与阈值数值归 B。
- 同一权威：filter 读 `args.rh2_orchestrator.config.staleness_threshold` 与载荷阈值逐值比对（§3 表末行；
  `test_threshold_authority_must_be_reachable_and_consistent`）。测试全部显式传 4（`_formal_config` / 三个 miles 夹具），4 只是夹具值。

## 6. `termination_facts_stamp_conflict` 的审计追加（codex 硬要求）

`generate()` :2340-2360：盖章冲突 → 构造 fatal → `_append_post_receipt_fatal_fact(audit, fatal, stage="deliver")`
（:2361-2388）：向同一 audit 追加 `RolloutFailureRecord(error_type="termination_facts_stamp_conflict")` + 时间线标记
（携带 `physical_attempt_id`），再**经现有 audit sink 第二次写入**（bringup 的 `fa_execution_audit.jsonl` 是 append-only，
第二条记录携带 `physical_attempt_id` + `failure_records`，磁盘上"receipt=delivery_prepared / 首条审计成功"与"其后 fatal"两条
事实并存、按 attempt 可关联）；追加自身失败只记 secondary fact `post_receipt_fatal_audit_append_failed`，不掩盖首因；
随后 `_notify_fatal_halt` 并抛出。不建恢复平台、不改 receipt（append-only 纪律）。测试：
`test_stamp_conflict_appends_attempt_bound_fatal_fact_via_existing_audit`（sink 调用两次、第二次 failure_types == [stamp_conflict]、
attempt 绑定、receipt 仍 delivery_prepared）、`test_stamp_conflict_audit_append_failure_is_secondary`。

## 7. T1 决策及理由

1. **载荷 = 内嵌完整 `EligibilityReport` + `RolloutAttemptOutcomeV2` 的 `AdmissionPayloadV1`，而不是"最小字段摘要"。**
   计划要求 filter 核对 facts digest——不扫盘、不建 ledger 的前提下，只有把 facts 本体随样本运输才能在消费时刻重算 digest；
   内嵌既有 typed 权威对象让消费时 `model_validate` 自动重跑两者全部不变量，且不引入第二份可独立修改的资格结论（W2a F5 教训）。
   载荷 ~2-3 KB/样本，进 miles Sample.metadata 随 ray 对象流转，可接受。载体 = 紧凑 metadata（`rh2_admission`），只作运输值。
2. **prompt_group ↔ group 对账用样本自带的组事实 + 铸造身份 + 分派三元组（§3）。** stock buffer 不把 prompt_group 交给 filter；
   不改 reference/、不写自定义 buffer（"单个复合 filter 是唯一入口"），也不延长 registry。对账强度：跨组混入、slot 缺/重、
   attempt 复用、fan-out 冒充、非本 prompt group 的样本（index 算术）全部 FATAL。
3. **s1_compat 交付面逐字不变（degraded 仍 abort 形状），三终态只在非 s1 模式生效。** s1_compat 是 slime FA 冻结回退面 +
   miles GPU spike 现行 bring-up 路径（launch.sh 走 s1_compat + stock `check_reward_nonzero_std`），没有组级准入消费者；
   把 degraded 真实交付到没有复合 filter 的路径会让不合格样本进训练。三终态语义（③ 真实交付）与接线守卫（T1-8）只对 fa_formal /
   fa_audit_only 生效。
4. **reward 不可得成员的 miles `Sample.reward` 用 NaN 占位。** 不用 None：miles `generate_and_rm` 对 `reward is None` 的
   样本调 rm hub，rh2 链无 `rm_type/custom_rm_path`，`async_rm` 会 `AttributeError` 炸掉整组 task（已核实
   `inference_rollout_common.py:119-123` + `rm_hub/__init__.py:53`）；不用 0.0：P4 红线，infra/未评分绝不伪装成负样本；
   NaN 若因接线错误绕过 filter 进入训练会在 advantage 计算里 loud-fail 而不是静默污染。typed 载荷里
   `outcome.reward_unavailable=True` 是权威事实，filter 核对二者一致（`reward_present_but_unavailable_claimed`）。
5. **unsafe / failed_to_grade 的 receipt disposition 变为 `delivery_prepared`。** 样本确实备好交回 miles（不代表进训练，
   契约字段说明如此）；权威归因在 `outcome_v2`（receipt 内嵌），bringup 审计 disposition 仍派生 `permanent_rejected`。
   不新增 AttemptDisposition 取值（那是 contracts T0）。
6. **s1_compat 的 staleness 阈值回退到命名常量 `S1_COMPAT_LEGACY_STALENESS_THRESHOLD = 4`。** bringup（非本切片所有权）构造
   SlimeBindingConfig 不传阈值，s1_compat 必须继续能跑；这是被冻结的 S1 历史值而不是"默认值"：formal 路径无任何回退
   （启动即拒 + 握手 run-fatal），filter 与载荷逐值比对。
7. **s1_compat / verifiers 对照路径显式声明 `sandbox_capability_facts_required=False`。** 后果：这两条冻结路径七维全过的样本
   标签由 `offline_or_sft_candidate`（S1 封顶）变为 `online_policy_loss_eligible`。交付/训练行为不变——s1 从未按标签做准入
   （唯一消费者 offline exporter 接受 online/offline 两档），复合 filter 在 s1 不接线、且 s1 样本无 `rh2_admission` 载荷，
   即便误接 filter 也是 FATAL（`admission_payload_missing`）而不是放行。若 owner 认为 s1 也应要求能力事实，改一处
   `required=self._mode != "s1_compat"` 即可——但那会让 s1 全部样本 audit→abort，s1 路径整体不可用。
8. **接线守卫：非 s1 模式 `Rh2MilesGenerateFn` 派发前要求 `args.dynamic_sampling_filter_path == GROUP_ADMISSION_FILTER_PATH`。**
   交付面真实交付不合格成员后，准入完全依赖复合 filter；没挂 filter 的 formal 运行会把不合格成员送进训练（接线 bug，
   A8 配置真实性同纪律）。fa_audit_only 也要求（探针配置应与 formal 同形）。
9. **`SandboxCapabilityFacts` 的 required 清单硬编码为九项（W3b 行原文）。** 这是 gate 的消费契约，不是授权清单；W3b 若
   改名/增项须同步改清单并机械升 GATE_VERSION（接缝 3）。单条报告缺事实 = DROP（附录 A 5b）；能力 producer 全局未接线的
   启动级 FATAL（附录 A 5a）归 W3b/W7 preflight，本段不实现（避免在 W3b 前让每个本地 formal 测试都 fatal）。
10. **hygiene/agent 违规 pending 的 KEEP_FULL 注入是"链路中立"意义上的可达值。** 注入 KEEP 时纯函数返回 KEEP_FULL，
    但 schema 层 `eligibility_class` 仍为 audit（security 失败强制）；D2 若采纳 KEEP，须同批修订 producer/schema 耦合
    （06 附录 A 豁免行注：无 reward 的 unsafe 形状仍按豁免集 DROP，不受本注入影响）。代码不含任何推荐值。
11. **未登记 reason_code 一律 FATAL（`unmapped_reason_code:<dim>:<code>`）。** 新增 gate 理由码而没有登记处置是接线缺口，
    宁停机不静默 DROP（静默 DROP 是系统性偏置的来源）。
12. **失败域 `derive_admission_payload` / `stamp_admission_payload` 在交付面 = run-fatal**（`admission_payload_build_failed` /
    `admission_payload_stamp_conflict`）：各权威对象互相矛盾不是成员损耗；与切片一 ④ 同通道，cleanup 仍执行。

## 8. 偏离说明

- 附录 A 行 5a（"能力 producer/消费面全局未接线 → FATAL（启动/preflight 级）"）本段未实现为代码：W3b 未产出事实前，
  按任务书口径"formal 样本自然非 online——预期不是 bug"落为逐样本 DROP；启动级检查归 W3b/W7 preflight（接缝）。
- `remove_sample=True` 的非 ABORTED 交付样本在 filter 层判 FATAL 而不是 A6 原文的"整组拒绝"：本段交付面已不再用
  `remove_sample` 表达"不合格"（完整成员一律真实交付、组级裁决），剩下的 remove_sample=True 只可能是 eval 占位误入训练面
  或接线矛盾——按 D1"账实矛盾走 FATAL"处理。eval 占位形状本身不变（`test_evaluation_placeholder_unchanged_in_formal_mode`）。
- `governance/wrapper.py` 不在任务书所有权列表内，但 gate 的新输入必须经唯一入口 `finalize_rollout` 透传（+2 关键字参数，
  默认 fail-closed）；登记为 T1 边界扩展。

## 9. 测试证据（2026-09-02 实跑）

新增 100 例全绿：

```
cd rh2
uv run pytest tests/governance/test_w1b_admission_disposition.py tests/governance/test_w1b_security_capability_facts.py -q   # 62 passed
uv run pytest tests/adapters/test_w1b_delivery_face.py -q                                                                  # 14 passed
RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/test_w1b_group_admission.py -q    # 24 passed
```

回归（工作树 = `466cfd0b`（含 W5a 提交）+ 本切片未提交改动）：

```
uv run pytest tests/ -q                                                       # 1557 passed, 232 skipped, 3 warnings in 34.77s（起点 1430/232 + 本切片 +100 + W5a 提交 +27）
uv run pytest tests/adapters_miles/ -q                                        # lane A: 308 passed / 217 skipped
uv run pytest tests/adapters_miles/ -q -m "not integration_base"              # skip 全部为 integration_base 豁免
RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/ -q   # lane B: 525 passed / 0 skipped
bash scripts/miles_integration_lanes.sh   # 前置校验（integration tree a4b60c89…/工作树干净/patch digest 8 个/pin f2b7c792…）全部通过；
                                          # lane A 计数偏离 manifest(285p/217s) 停止——计数由集成者更新（下）
uv run ruff check src/repoharness2 tests experiments/s1_parity.py             # All checks passed!
```

**两条 lane 的精确新计数（供集成者更新 manifest）**：lane A = **308 passed / 217 skipped**，lane B = **525 passed / 0 skipped**。构成：本切片
`test_w1b_group_admission.py` 双 lane 各 **+24 passed**（不标 integration_base，top_p=1.0 链路在 pin base 同样跑）；
同期已提交的 `52e78b44` 删 lifecycle 原型测试段贡献 lane A/B 各 **−1**（不属本切片）。相对 manifest（285/217、502/0）：
A = 285 + 24 − 1 / 217 + 0，B = 502 + 24 − 1 / 0。

### 附录 A 逐行 ↔ 实现位置 ↔ 测试

| 附录 A 行 | 实现位置（`governance/admission.py` 除非另注） | 测试 |
|---|---|---|
| 第一层：结构/身份/引用矛盾 → FATAL | 载荷 validator :227-292（attempt/execution/报告绑定/reward 可得性/评分引用/staleness 互洽）+ filter 对账（§3 表） | `test_payload_derivation_rejects_reference_and_reward_contradictions`、`test_stamp_then_resolve_round_trip_and_join_negatives`、`test_structural_contradictions_raise_from_real_buffer_put`（13 例）、`test_facts_digest_tampering_inside_payload_is_fatal`、`test_prompt_group_reconciliation_rejects_wrong_size_and_duplicate_member`、`test_fan_out_leaves_share_identity_but_forged_leaf_is_fatal` |
| 第一层：missing → ABORTED | `generate.py` `_abort_result` present 守卫 :4520-4536；filter `aborted_member_reached_filter` :336；纯函数兜底 `missing_outcome_delivered_as_present` :559 | `test_missing_outcome_stays_aborted_without_admission_payload`、`test_abort_shape_for_present_outcome_is_fatal`、`test_aborted_group_never_reaches_filter_and_filter_rejects_aborted_if_reached` |
| 第一层：present_* → 第二层 | :557-562 | 全部 ③ 用例 |
| 契约豁免集：present_* + eligibility None（grading_infra_failure / unsafe） → DROP；其余 → FATAL | :566-577（`grading_infra_failure_without_report` / `unsafe_artifact_permanent_rejection` / `present_without_eligibility_report`） | `test_exemption_grading_infra_without_report_is_drop`、`test_exemption_unsafe_artifact_without_report_is_drop`、`test_present_without_report_outside_exemption_is_unrepresentable`、`test_unsafe_is_delivered_without_report_and_drops_by_exemption` |
| 1 token_provenance：capture 丢失/不完整且 present → FATAL | `_DIMENSION_REASON_VERDICTS["token_provenance"]` | `test_appendix_a_reason_code_rows[capture_record_missing]`、`[capture_record_not_complete]` |
| 1 token_provenance + outcome=missing → ABORTED | 不进交付面（missing 由 `_abort_result` 编码） | `test_split_5_pre_finalize_task_local_failure_stays_aborted`（切片一，原样） |
| 2 logprob_alignment：missing/partial → FATAL | 同表 | `[logprob_missing]`、`[logprob_partial_or_mismatch]` |
| 3 loss_mask_integrity：no_trainable_tokens → DROP；loss_denominator_mismatch → FATAL；声称 online 却零可训 token → FATAL | 同表；filter `online_claim_without_trainable_provenance` :239-266 | `[no_trainable_tokens]`、`[loss_denominator_mismatch]`、`test_structural_contradictions_raise_from_real_buffer_put[online_claim_without_trainable_provenance]` |
| 4 reward_scope：reward_scope_none 且与 grading infra 一致 → DROP（按 infra 计数）；不一致 → FATAL | `_DROP_IF_GRADING_INFRA` :448-455、:600-604 | `test_grading_infra_failure_with_report_is_drop_and_counts_as_infra`、`test_reward_scope_none_without_grading_infra_attribution_is_fatal`、miles 指标 `drop_admission_reward_scope_none`（`test_degraded_member_drops_whole_group_and_nothing_reaches_conversion`） |
| 4 reward_value_mismatch / reward_event_ref_missing / credit_assignment_unknown → FATAL | 同表 | 三条参数化 |
| 5a security：能力 producer 全局未接线 → 启动级 FATAL | **未实现**（归 W3b/W7 preflight，§8） | — |
| 5b security：单条报告缺正向能力事实 → DROP | gate `sandbox_capability_facts_missing` :466 + 表 | `test_missing_capability_facts_is_not_online_even_with_no_findings`、`test_all_ok_without_capability_facts_is_delivered_but_drops_by_a3`、`test_missing_capability_facts_drops_group_by_a3` |
| 5c security：sandbox 探针失败并销毁 → ABORTED | 归 W3b（missing 归因路径既有） | — |
| 5d security：隔离未生效 → FATAL | `sandbox_capability_violation_*` → FATAL（前缀规则 :488-492） | `[sandbox_capability_violation_hidden_and_grader_assets_not_mounted]`、`test_violation_fails_dimension_even_when_all_verified` |
| 5e security：public_projection_marker_hit → DROP（默认） | 同表 | `[public_projection_marker_hit]` |
| 5/6 executed 级 agent 违规 / patch_test_tampering / patch_forbidden_contamination → pending（显式注入，未注入 fail-fast） | `_PENDING` + `agent_violation` 槽位 :614-628 | `test_agent_violation_requires_injection_and_is_neutral`、`test_anti_cheat_executed_code_is_pending_too`、`test_pending_not_consulted_when_another_dimension_drops` |
| 6 clean_grading：failed_to_grade → 保持 present，DROP，不得改写 ABORTED | 同 4a；交付面 `_deliver_present_member` | `test_failed_to_grade_is_delivered_as_real_sample_not_aborted` |
| 6 not_replayed_on_clean_checkout → FATAL | 同表 | `[not_replayed_on_clean_checkout]` |
| 6 GradingReport 身份/引用矛盾 → FATAL | 载荷 validator（grading 引用/outcome 归因/task_outcome 互检）+ filter `admission_termination_facts_mismatch` | `test_payload_derivation_rejects_reference_and_reward_contradictions`、`[termination_facts_unresolvable]` |
| 7 staleness_facts_missing → FATAL；staleness_exceeded → DROP | 同表；阈值接口 §5 | `test_staleness_facts_missing_is_fatal_in_formal_path`、`[staleness_exceeded]`、`test_explicit_staleness_threshold_required`、`test_staleness_threshold_authority_mismatch_is_fatal` |
| 七维全过 → 应用显式 termination disposition（A5 归 C） | :636-648 | `test_present_truncated_requires_explicit_injection_and_chain_is_neutral`（5 例）、`test_truncated_member_fail_fast_without_injection_and_neutral_with` |
| 可信 tests_failed / patch_apply_failed = 正常 reward=0 成员（A6） | 全过 → KEEP_FULL；filter 零方差按成员 reward | `test_full_chain_keep_full_group_reaches_real_conversion`（`raw_reward == [1.0, 0.0]` 真实进 conversion）、`test_zero_variance_group_dropped_by_composite_filter` |
| A2 全员合取 / 任一非 KEEP → 整组 keep=False 固定丢弃 | `admit_group` :427-441 | `test_degraded_member_drops_whole_group_and_nothing_reaches_conversion`、`test_missing_capability_facts_drops_group_by_a3` |

### T1 oracle / 夹具改动清单（逐条登记）

| 文件 | 改动 | 触发原因 |
|---|---|---|
| `tests/governance/test_wrapper_finalize.py` | `test_happy_path_all_dimensions_ok_but_capped_to_offline` → `..._is_online`（class online、reason_codes 空）；`test_s1_tier_cap_constant_pinned` → `test_s1_tier_cap_deleted_and_gate_version_bumped`；backpressure 用例只剩观测理由码；async 回调用例未传能力事实 → audit | A3 cap 删除 |
| `tests/governance/governance_samples.py` | `run_finalize` 新增 `sandbox_capability_facts=_DEFAULT（合法事实）/None`、`sandbox_capability_facts_required=True`；新增 `valid_sandbox_capability_facts()` 工厂 | A3 security 维新输入（正例基线显式传事实） |
| `tests/governance/test_governance_api_surface.py` | `__all__` 集合更新；新增 `test_admission_module_public_functions_pinned`（admission.py 五个公开函数钉死、不经包级转出） | 导出面变化 + 新模块 |
| `tests/governance/test_gate_dimensions.py` | `test_attempted_blocked_finding_does_not_fail_security` 结论 offline → online | cap 删除 |
| `tests/adapters/test_slime_generate.py` | `_formal_config` 显式 `staleness_threshold=4`；`build_dense_chain` 新增 `sandbox_capability_facts_provider` / `audit_sink` 注入位；s1 happy path / eval 占位 / 分离拓扑三处标签 offline → online（reason_codes 空 + evidence not_required） | 显式阈值 + A3（s1 显式不要求能力事实） |
| `experiments/s1_parity.py` + `tests/adapters/test_s1_parity.py` + `tests/adapters/test_offline_export.py` | verifiers 对照路径显式 `sandbox_capability_facts_required=False`；slime/导出记录标签 offline → online、`s1_default_ceiling_offline` 断言删除 | A3 |
| `tests/adapters/test_b5_finalization.py` | unsafe（hygiene 篡改、unsupported 对象）两例：`remove_sample` True → False、载荷在场、receipt aborted → delivery_prepared（拒绝证据/本体持久化/outcome 归因断言原样） | 三终态 ③（present 不再 ABORTED） |
| `tests/contracts/test_f2_2b_b3_hygiene.py` | 三处 unsafe 交付形状断言同上（审计 disposition `permanent_rejected` 断言原样） | 同上 |
| `tests/adapters/test_f2_2_capability.py` | 启动校验用例 `dense_config(execution_mode="fa_formal")` 显式 `staleness_threshold=4`（被测的 `fa_formal_requires_real_weight_versions` 先于阈值检查，语义不变） | 显式阈值 |
| `tests/adapters_miles/test_w1a_formal_chain.py` / `test_w1b_prepared_chain.py` / `test_w1a_identity_minting.py` | fa_formal 配置显式 `staleness_threshold=4`；miles args 替身加 `dynamic_sampling_filter_path=GROUP_ADMISSION_FILTER_PATH`（`_args`/`_mk_input`/`_mk_generate_input` 集中） | 显式阈值 + 接线守卫 |
| `tests/contracts/*`（`contract_samples` 的 `s1_default_ceiling_offline` 字符串） | 未改：只是 SafeIdentifier 字面量样例，与 gate 无耦合 | — |

## 10. 开放问题 / 接缝（留给 bringup 侧与后续包）

1. **bringup 接线（W7 launch / 集成者，`bringup.py` 非本切片所有权）**：(a) fa_formal 的 `SlimeBindingConfig(staleness_threshold=<B 包数值>)`
   必须显式传入（现状 :883 构造不传 → fa_formal 启动即 `staleness_threshold_required_in_formal_chain`，fa_audit_only 不受影响）；
   (b) `--dynamic-sampling-filter-path repoharness2.adapters.miles.group_admission.rh2_group_admission_filter`（现 launch.sh :426 是 stock
   `check_reward_nonzero_std`，s1_compat 下照旧可用；切到 fa_formal 时 generate_fn 守卫会拒绝派发）；(c) `args.rh2_disposition_policy`
   的注入位（C 包拍板 A5 / D2 拍板 A4 后由 launch/custom config 构造 `DispositionPolicy`；未注入 = 遇截断/违规成员 fail-fast）；
   (d) `RolloutOrchestrator(sandbox_capability_facts_provider=…)`（W3b）。
2. **B 包连带**：unused handler retry/drop 选择不变；本段 ABORTED 面未扩大（present 全部改走 filter DROP，ABORTED 只剩 missing）。
   `max_weight_staleness`（consume-time）语义与数值、finalize 阈值数值均归 B；W4 接 consume-time 时应从同一 `SlimeBindingConfig`
   派生（本段只在 filter 侧钉死 finalize 阈值的权威等式）。
3. **W3b**：`SandboxCapabilityFacts` 的 producer（sandbox 创建后核实并记录）+ `REQUIRED_SANDBOX_CAPABILITIES` 名单对齐（改名/增项 → 升 GATE_VERSION）
   + 附录 A 5a 的启动级 preflight（全局未接线 → FATAL）+ 5c 探针失败的 ABORTED 归因路径。
4. **D2/A4**：hygiene/agent 违规的 `agent_violation` 注入值；若选 KEEP，需同批修订 security 失败 ⟹ audit 的 schema 耦合与 producer
   （现 formal 链 hygiene 命中在评分前筛为 unsafe 形状，无 reward，按豁免集 DROP，不受注入影响）。
5. **registry.py 未注册** `rh2.admission_payload.v1` / `rh2.sandbox_capability_facts.v1`（与切片一/W2a 的五个 schema 同一待办；
   `registry.py` 不在本切片所有权）。注册时 `admission_payload` 内嵌 EligibilityReport/Outcome，无内容字段，不需 marker 豁免。
6. **载荷体积**：每样本 ~2-3 KB metadata 随 miles Sample 进 ray 对象存储；首训规模（组数 × n=8）下可忽略，若 evidence_refs 变长再评估瘦身（T1）。
7. **`Rh2GovernedBuffer`（C3/C7 spike 原型）** 内部把 `dynamic_sampling_filter_path` 置空并在治理层自行 `call_dynamic_filter`——
   与本段"单个复合 filter 唯一入口"兼容（它转调同一 filter），但该原型非生产面（06 §5 第 4 条），不在本段验证范围。
8. **eval 路径**：`evaluation=True` 的占位形状（remove_sample=True）不变，不进训练 buffer；若未来 eval 样本误入复合 filter → FATAL
   `remove_sample_on_delivered_member`（W8 接线时须保持 eval 不经训练 buffer）。

## 11. 协作协议五段收尾

**① 待拍板 T0**：无新增。两项请 owner 知悉的 T1（不满足 T0 升级条件，但改变了可见标签/接口形状）：
(i) T1-7——s1_compat 与 verifiers 对照路径的 EligibilityReport 标签由 offline 变 online（A3 删封顶的直接后果；无准入行为变化）；
(ii) T1-9——`REQUIRED_SANDBOX_CAPABILITIES` 九项名单先于 W3b 定义（消费契约，W3b 可改并升 GATE_VERSION）。

**② T1 决策及理由**：§7 第 1~12 条；边界扩展：`governance/wrapper.py` +2 参数（§8）。

**③ 临时挡板新增/命中/解除**：无新增临时挡板；`bringup.py:705` fa_formal 挡板原样。新增的都是永久 fail-closed 边界
（接线守卫、present 守卫、阈值显式化、载荷对账、未登记 reason_code FATAL）。

**④ 推翻或修正了哪些旧结论**：
- 切片一 §4 开放问题 3（deliver 失败后"事实完整但 abort 形状"）：本段以 present 守卫封死，交付面上不可达。
- 切片一 §4 开放问题 2（载荷载体）：定为紧凑 metadata + 内嵌 typed 权威对象（T1-1），不建有界映射。
- 切片一 §8.5 登记不修项（stamp_conflict 审计追加）：本段实现（§6）。
- B5/B3 时代"unsafe → abort 形状（remove_sample=True）/receipt aborted"的口径被三终态 ③ 取代（present 事实不再改写为 ABORTED）。
- S1 封顶（`S1_TIER_CAP`）与"无 findings 即安全"的 security 语义按 A3 整体删除/切换。

**⑤ 测试/证据/账本状态**：§9；lanes manifest 由集成者按 §9 计数更新；spike-log 由集成者落账。

**本轮没有改变哪些已定案语义**：切片一的 post-finalize 失败域五分流、F4 attempt 绑定、F5 termination 事实派生与盖章规则；
W1a 六字段铸造规则；W2a 视图/controller；`contracts/` 全部 schema（含 Outcome v2 豁免集、EligibilityReport 五连锁）；
s1_compat 的交付形状（degraded 仍 abort）、v1 八题 bring-up、eval 占位形状；A5 三个截断族与 A4 hygiene 的处置取值
（代码零推荐值）；staleness 阈值数值与 `max_weight_staleness` 语义（B）；unused handler retry/drop（B）；consume-time
staleness（W4）；faithful DIS loss；`bringup.py:705` 挡板；lane 测试集合除本切片 +24 外无增删。

---

## 12. 追加修正节（2026-09-02，codex 复核 #2/#4/#5/#6 后；append-only，本节口径覆盖上文冲突处）

修复基线 = 已提交的 `37fc0d65`（+ 集成者 `4cff6de5`/`8df7f90c`）；本节改动未 commit / 未 stash；
`bringup.py`、`shutdown/`、`reference/` 未触碰（并行 W5a agent 同 worktree 正在改 `bringup.py`/`shutdown/`/`test_w5a_*`）。

### 12.1 #2 P1：结构契约类异常显式提升 run-fatal（`adapters/slime/generate.py`）

原通用 `except Exception`（:3327）把 `GateInputError`（gate.py 明确定义为"编排接错线"）经 stage fallback 洗成 missing
Outcome + ABORTED，之后被补采掩盖。现在 except 链为**显式分支**（不靠 isinstance 猜），白名单：

| 异常类型 | 条件 | fatal reason_code | 落点 |
|---|---|---|---|
| `governance.GateInputError` | 任何阶段 | `gate_wiring_error` | :3336 |
| `governance.admission.AdmissionError`（含 `DispositionNotInjectedError`） | 任何阶段（交付面内部已各自包装，此处为防漏网通道） | `admission_contract_error` | :3341 |
| `pydantic.ValidationError` | **仅** `stage ∈ _STRUCTURAL_CONTRACT_STAGES = {"finalize", "deliver"}`（:1848）——由我方事实构造 RH2 契约对象失败 = 接线矛盾 | `rh2_contract_validation_failed` | :3347 |
| 其它 `Exception`（含 finalize 之前的 ValidationError、`FAILURE_CODE_TERMINATION_MAP` 命中的 typed task-local 错误） | 不变 | 仍走 stage fallback → missing Outcome + ABORTED（`_abort_after_task_local_exception` :3399，逐字搬自原 except 体） | — |

`_structural_contract_fatal`（:3377）：记 failure_record + 时间线标记 + `_notify_fatal_halt`，**不产 Outcome、不返回 ABORTED**；
receipt 由既有 `build_finalization_receipt` 落为 `fatal_run_halt`（terminal_reason_code = 上表 code）。为让 except 链拆成显式分支而
不复制 200 行 finally 体，原 finally 主体逐字搬入 `async _run_finally_section`（:3478）——语义零改变（切片一的分流测试全部原样通过）。
测试：`test_gate_input_error_in_finalize_is_run_fatal_not_aborted`（receipt fatal_run_halt、`outcomes == []`、无 step9、cleanup 完成）、
`test_validation_error_inside_finalize_is_run_fatal`、`test_stale_lease_capability_facts_are_run_fatal_via_gate_wiring`（#5 联动）、
对照 `test_pre_finalize_validation_error_and_task_local_failure_stay_aborted`（materialize 阶段 ValidationError 与 harness 崩溃仍 ABORTED）。

### 12.2 #4 P1：消费侧版本事实绑定（`adapters/miles/group_admission.py` `_check_leaf_version_binding` :301）

对**每个**交付叶（不只 online 成员）按现有版本投影语义核对：
1. 叶 `weight_versions` 非空 ⟺ `Outcome.turn_weight_versions` 非空（`version_facts_presence_mismatch`）；
2. 叶每个版本可解析为十进制 int（`version_not_numeric`）；
3. `set(叶版本) ⊆ set(Outcome.turn_weight_versions)`——**子集**，fan-out 叶只回链自己的入训轮，不要求集合相等（`leaf_version_not_in_outcome`）；
4. `max(叶版本) ≤ int(Outcome.current_version_at_finalize)`（`leaf_version_ahead_of_finalize`）。
执行顺序：版本绑定先于形状声称检查（更具体的矛盾先报）。codex 反例复现为测试
`test_negative_consume_time_staleness_reproduction_is_closed_at_filter`：叶改成 999 时 miles `DefaultDataBuffer._staleness(group, 5) == −994`
（`oldest_weight_version = min(叶 weight_versions)`），`max_weight_staleness=0` 也"满足"；本轮在 filter 侧（finalize 事实层）
`put()` 即 FATAL，组进不了 buffer。**接缝（W4）**：consume-time 的负 lag 拒绝须在 miles `get()` 侧实现（不改 reference/，本轮不做）。
其余测试：参数化 `[leaf_version_not_in_outcome]`、`[leaf_version_ahead_of_finalize]`（Outcome 版本 {5,9}、current 5、叶 9）、
`[version_facts_presence_mismatch]`、`[version_not_numeric]`；`test_fan_out_leaves_share_identity_subset_versions_ok_but_forged_leaf_is_fatal`（子集通过）。

### 12.3 #5 P1：SandboxCapabilityFacts 绑定本次真实 lease（`governance/gate.py` / `wrapper.py` / `generate.py`）

- `finalize_rollout(..., sandbox_lease_id: str | None = None)` → `_evaluate` → `_check_wiring`（gate.py :591-616）：
  `required=True` 且 `sandbox_lease_id is None` → `GateInputError`；facts 在场且 `facts.lease_id != sandbox_lease_id` → `GateInputError`
  （按 #2 升 fatal `gate_wiring_error`）；`required=False`（s1_compat / verifiers 对照）路径不受影响。
- **传入点**：`generate.py` `_finalize` :4179 `sandbox_lease_id=audit.lease.lease_id`——`audit.lease` 是 materialize 时刻挂上的本次
  attempt 真实 `SandboxLease`（:3652 附近），显式传入、不猜。
- 测试：`test_capability_facts_must_bind_to_this_attempts_lease`（同 trajectory 旧 lease 拒、正确 lease 过、required 缺 lease 拒、
  required=False 不受影响）、`test_stale_lease_capability_facts_are_run_fatal_via_gate_wiring`（真实 fa_formal 链）。

### 12.4 #6 P2：authoritative join 与组合测试

- (a) `resolve_admission_payload(..., require_dispatch_identity=True)`（admission.py :373）：**必填键** `task_id` /
  `environment_package_digest` / `public_bundle_digest` 三键在场且逐字等于载荷（缺 → `admission_dispatch_identity_missing`；载荷
  `environment_package_digest=None` → `admission_environment_identity_missing`——legacy v1 链不可进正式准入）。filter 两处调用
  （group_admission.py :391/:421）强制 True；交付面自检（generate_fn `_verify_admission_binding`）与切片一 legacy 夹具保持
  默认 False（只在键在场时比较）。
- (b) `_check_outcome_identity`（group_admission.py :269）：Outcome `identity.prompt_group_id / group_index / rollout_execution_id /
  physical_attempt_id / physical_attempt_seq` + `member_slot` 与外层六字段逐项对账，不一致 `outcome_identity_mismatch`。
- (c) e2e：`test_w1b_e2e_prepared_registry_group_admission_to_conversion`——经过的真实组件：trusted-prep 产物 + 外部 manifest SHA
  （`PreparedTaskFace.load`）→ stock miles `Dataset` + `RolloutDataSource.get_samples` → `Rh2MilesGenerateFn`（接线守卫 → W1a 铸造 →
  `registry.bind`，spy 断言 `face.verify_dispatch` 对 prep manifest 核对了两次 TID1 三元组）→ `RolloutOrchestrator(fa_formal)`
  （task/评分材料只经 attempt 绑定）→ canonicalize → `registry.release`（`len(registry)==0`）→ `DefaultDataBuffer.put()`（复合
  filter）→ `get()` → `postprocess_rollout_data` → `convert_samples_to_train_data`：合格组 2 行进 conversion（`raw_reward == [1.0, 0.0]`）；
  含一个 failed_to_grade 成员的组零样本进 conversion（buffer/handler 均空，`drop_admission_reward_scope_none == 1`）。
  同时 `test_w1b_group_admission.py` **全部**用例改走 prepared registry 链（不再用 legacy v1 任务面）。

### 12.5 非 finding：present_truncated ≠ miles TRUNCATED（钉死，不"修复"）

`test_present_truncated_and_miles_truncated_status_are_legally_distinct`：hard wall 成员 = Outcome present_truncated + 叶 `COMPLETED`；
length 截断成员 = 叶 `TRUNCATED` + Outcome present_complete/termination=completed；两者都通过组准入（前者需注入 hard_wall 处置），
`convert_samples_to_train_data` 的 `truncated == [0, 1]` 只反映生成截断事实。filter 不要求二者相等。

### 12.6 T1 oracle / 夹具改动（本节）

| 文件 | 改动 |
|---|---|
| `tests/governance/governance_samples.py` | `run_finalize(sandbox_lease_id="lease_0001")` 默认与样例事实同租约 |
| `tests/governance/test_wrapper_finalize.py` | 三处直接调 `finalize_rollout` 的用例显式传 `sandbox_lease_id`（required 路径必传） |
| `tests/governance/test_w1b_security_capability_facts.py` / `test_w1b_admission_disposition.py` | 新增 lease 绑定用例；strict 三键必填负例 |
| `tests/adapters/test_w1b_delivery_face.py` | 新增 #2/#5 四例 |
| `tests/adapters_miles/test_w1b_group_admission.py` | 整体改走 prepared registry 链（24 → 37 例：+e2e、+truncated 区别、+#4/#6 参数化 8 例、+负 staleness 复现） |

### 12.7 测试证据（2026-09-02 实跑；工作树含并行 W5a agent 的**进行中**改动）

```
uv run pytest tests/governance tests/adapters tests/contracts -q                          # 871 passed（本切片相关目录）
RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/test_w1b_group_admission.py -q   # 37 passed
uv run pytest tests/ -q --ignore=tests/adapters/test_w5a_resource_closure.py               # 1574 passed, 236 skipped
uv run pytest tests/adapters_miles/ -q                                                      # lane A: 321 passed / 221 skipped
RH2_MILES_PATH=... uv run pytest tests/adapters_miles/ -q                                   # lane B: 541 passed, 1 failed（见下）
bash scripts/miles_integration_lanes.sh                                                     # 前置 1 停止：integration checkout 工作树不干净（见下）
uv run ruff check src/repoharness2 tests experiments/s1_parity.py                           # All checks passed!
```

**本节净增**：governance +1、adapters +4、adapters_miles +13（双 lane；`test_w1b_group_admission.py` 24 → 37）。

**环境噪音（非本切片，须由集成者/相应 agent 处理）**：
1. `tests/adapters/test_w5a_resource_closure.py` 当前 import `repoharness2.shutdown.MemoryBoundInputs` 失败（W5a agent 进行中的改动，
   `shutdown/` 与 `test_w5a_*` 同时在改），全仓需 `--ignore` 该模块才能收集；lane A/B 总数含其新增/跳过的 W5a miles 用例
   （`test_w5a_miles_dispose_chain.py` 未跟踪）。
2. `reference/miles-rh2-integration` 工作树不干净（`rollout_manager.py` / `fully_async_data_buffer.py` / `fully_async_rollout.py` /
   `train_async.py` 有未提交改动，非本切片所为）：`miles_integration_lanes.sh` 在前置 1 停止；lane B 的
   `test_g1_acceptance_events.py::test_producer_tree_digest_matches_audit_manifest` 因树 digest 漂移失败；且 lane B 的
   `DefaultDataBuffer.put()` 路径跑的是被改过的文件——本节 lane B 计数在该 checkout 恢复干净前**不构成 lane 资格**。

**lane 精确新计数（相对 manifest 308/217、525/0，只计本切片）**：lane A = 308 + 13 = **321 passed**（skipped 不变 217 + W5a 的 4 = 221 观测），
lane B = 525 + 13 = **538 passed**（观测 541 = 538 + W5a 进行中 +3；1 failed 为上述 g1 树 digest）。集成者按干净树重跑后以实测为准。

**T0**：无新增。fatal 白名单只提升"我方接线/事实矛盾"类异常（停机不剔除样本，不产生系统性偏置）；task-local ABORTED 面未扩大也未缩小。
