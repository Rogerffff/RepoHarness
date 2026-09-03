# Wave3 前置清理批实现报告：删每轨迹能力事实 / 删 finalize-time 阈值资格门 / 删 projection 扫描资格语义

日期：2026-09-04。执行依据：决策包 `miles_spike/decision_package_D2_B.md` v2（owner 2026-09-04 已批）§0、D2-2、D2-4、B-1 与"落地顺序 1"；06 计划 §1.5 与 §5 3a；W1b 第二段报告 `w1b_slice2_report.md`（本批删除的机制即它实现的）。本文同时充当本批的 implementation-notes（与 W1b 报告同一惯例）。工作树状态：**未 commit / 未 stash**；`git rm` 过的旧测试文件已 `git reset` 回未暂存状态（index 未动）。

本批**只做删除/收窄，不加新功能**：不实现 run 级 `runtime_profile_digest`（W3b）、不接 consume-time staleness（W4）、不做可信评分投影（W3a）。

## 0. 三项删除清单（文件:符号）

### 0.1 第一项：每轨迹 sandbox 能力事实证明系统（D2-2 改判 A3 实现机制）

| 文件 | 删除的符号 / 分支 |
|---|---|
| `rh2/src/repoharness2/adapters/slime/generate.py` | `RolloutOrchestrator.__init__(..., sandbox_capability_facts_provider=...)` 参数与 `self._sandbox_capability_facts_provider` 属性；`_finalize` 内 provider 调用与 `finalize_rollout(sandbox_capability_facts=…, sandbox_capability_facts_required=…, sandbox_lease_id=…)` 三个透传；`from repoharness2.governance import SandboxCapabilityFacts` |
| `rh2/src/repoharness2/governance/wrapper.py` | `finalize_rollout` 的 `sandbox_capability_facts` / `sandbox_capability_facts_required` / `sandbox_lease_id` 三个参数及其透传；`SandboxCapabilityFacts` import |
| `rh2/src/repoharness2/governance/gate.py` | `REQUIRED_SANDBOX_CAPABILITIES` 常量（九项必需集）；`SandboxCapabilityFacts` 类定义（迁出，见下）；`_dim_security_and_leakage` 的 `capability_facts_required` 参数与 `sandbox_capability_facts_missing` / `sandbox_capability_unverified_<name>` / `sandbox_capability_violation_<name>` 三族分支及 `sandbox_capability_facts:absent` / `:not_required` evidence；`_check_wiring` 的 `sandbox_capability_facts` / `sandbox_capability_facts_required` / `sandbox_lease_id` 参数与 trajectory / lease 绑定检查；`_evaluate` 同名三参数；`__all__` 中两项；`AwareDatetime` import |
| `rh2/src/repoharness2/governance/__init__.py` | `REQUIRED_SANDBOX_CAPABILITIES` 导出（`SandboxCapabilityFacts` 导出保留，改从冻结模块 import） |
| `rh2/src/repoharness2/governance/admission.py` | `_DIMENSION_REASON_VERDICTS["security_and_leakage"]["sandbox_capability_facts_missing"] = DROP_GROUP`；`_REASON_PREFIX_VERDICTS` 的 `sandbox_capability_unverified_ → DROP_GROUP`、`sandbox_capability_violation_ → FATAL` 两条前缀规则 |
| `rh2/src/repoharness2/adapters/miles/group_admission.py` | 无直接消费（映射在 admission.py）；docstring 同步 |
| `rh2/experiments/s1_parity.py` | verifiers 对照路径的 `sandbox_capability_facts_required=False` |

**保留（按任务书）**：`SandboxCapabilityFacts` 类型迁到新模块 `rh2/src/repoharness2/governance/sandbox_capability_facts.py`，模块与类 docstring 明写"冻结历史 schema（v1），不进新 formal 链"，校验器（无重复、已核实与违规不重叠）逐字不变；仍经 `repoharness2.governance` 包级导出（兼容读路径）。历史九项必需集只作为 docstring 里的解读说明，**不再是可 import 的常量**。

security 维新语义（`gate._dim_security_and_leakage(grading_report, findings)`）：只判本次轨迹的执行级事实——executed 级 `AntiCheatFinding`（`anti_cheat_executed_<category>`）+ hygiene 落盘篡改事实（`patch_test_tampering` / `patch_forbidden_contamination`，admission 侧仍 pending 显式注入；改判其处置归 D2-3/W3a，本批不动）。`findings=()` 且 hygiene 干净 ⇒ 通过，evidence 可为空——这是预期。s1_compat 的 `required=False` 分支随之消失。

### 0.2 第二项：finalize-time staleness 阈值作为资格门（B-1 改判 D1-4）

| 文件 | 删除的符号 / 分支 |
|---|---|
| `rh2/src/repoharness2/adapters/slime/generate.py` | `validate_execution_config` 的 fa_formal 显式阈值启动校验（`StartupCheckError("staleness_threshold_required_in_formal_chain")`）；`_build_handshake` 的 `FatalExecutionInfrastructureError("staleness_threshold_unconfigured")` |
| `rh2/src/repoharness2/governance/admission.py` | `decide_member_disposition(..., finalize_staleness_threshold)` 参数；`AdmissionError("staleness_threshold_not_configured")`；`staleness_threshold_authority_mismatch` FATAL 分支；`AdmissionPayloadV1.finalize_staleness_threshold` 字段与"steps ≤ threshold ⟺ 维 ok"校验；`_DIMENSION_REASON_VERDICTS["policy_staleness"]["staleness_exceeded"] = DROP_GROUP` |
| `rh2/src/repoharness2/adapters/miles/group_admission.py` | `_threshold_from_args`（`staleness_threshold_authority_unreachable`）；`admit_group(..., finalize_staleness_threshold)` 参数与透传 |
| `rh2/src/repoharness2/governance/gate.py` | `_dim_policy_staleness` 对 `handshake.staleness_within_threshold` / `staleness_threshold` 的消费与 `staleness_exceeded` 理由码 |

**第七维新语义**（`gate._dim_policy_staleness(handshake, projection, *, require_real_weight_versions)`）：**"版本事实可用且合法"**——

1. 可用：`BackendHandshake` 在场；缺席 → `staleness_facts_missing`（既有码）。
2. 合法（`require_real_weight_versions=True`，formal 链）：`weight_versions_seen` 非空、`policy_version` 在场（schema 已保证，防御性重申，违反仍记 `staleness_facts_missing`）、全部可解析为 ASCII 十进制 int（严格：不吞空白/符号/其它 Unicode 数字）、**没有任何 seen 版本比 `policy_version` 更新**；违反 → **新码 `staleness_facts_invalid`**。
3. finalize-time lag 只作观测：evidence `finalize_lag_observed:<n>` + `weight_versions_range:<min>..<max>:current:<c>`；**没有 `staleness_exceeded`**；gate 不读 `staleness_within_threshold` / `staleness_threshold` / `accepted`（测试用代码对象常量与 `co_names` 钉死）。
4. admission 映射：`staleness_facts_missing → FATAL`（不变）、`staleness_facts_invalid → FATAL`（版本账目错误，B-1 原文）；`staleness_exceeded` 不再登记（旧报告若携带 → `unmapped_reason_code` FATAL）。

**保留**：W1b 消费侧叶版本绑定 `_check_leaf_version_binding`（非空⟺Outcome 有版本、可解析 int、⊆ Outcome 版本、≤ current_version_at_finalize）与 `_build_handshake` 正式链的 `weight_versions_not_numeric_in_formal_chain` / `weight_version_ahead_of_current` fail-closed 逐字未动；负 lag 反例测试 `test_negative_consume_time_staleness_reproduction_is_closed_at_filter` 原样通过。

**contracts/ 零改动**：`BackendHandshake.staleness_threshold` / `staleness_within_threshold` 字段与 validator 原样。处理方式见 T1-2。

### 0.3 第三项：projection 扫描的资格语义（D2-4）

| 文件 | 删除的符号 / 分支 |
|---|---|
| `rh2/src/repoharness2/governance/wrapper.py` | `finalize_rollout` 的 `_scan_public_projection` 调用（"scan"步骤）；`FinalizedRollout.scan_result` 字段（**直接删除**，不留 Optional——理由见 T1-4）及其 trajectory_id 一致性对；`ProjectionScanResult` / `_scan_public_projection` import；docstring 由"grade→project→scan→gate"改"grade→project→gate" |
| `rh2/src/repoharness2/governance/gate.py` | `_dim_security_and_leakage` 的 `scan_result` 参数、`public_projection_marker_hit` 分支与 `scan_result.evidence_refs()` 留痕；`_check_wiring` / `_evaluate` 的 `scan_result` 参数与接线检查；`ProjectionScanResult` import |
| `rh2/src/repoharness2/governance/admission.py` | `_DIMENSION_REASON_VERDICTS["security_and_leakage"]["public_projection_marker_hit"] = DROP_GROUP` |
| `rh2/src/repoharness2/adapters/offline_export/exporter.py` | `if not finalized.scan_result.clean: raise OfflineExportError("projection_scan_not_clean")` 门槛与 docstring 条目 |
| `rh2/experiments/s1_parity.py` | `scan_result.scanner` / `scan_result.clean` 两条 parity 断言（改为断言产物无 `scan_result`） |
| `rh2/experiments/s1_7a_bringup/export_sample.py` | `scan_result=_scan_public_projection(projection)` 重算与私有 import |

**保留**：`governance/projection_scan.py` 整体代码冻结不动（`ProjectionScanResult` / `ProjectionMarkerHit` / `_scan_public_projection`），只改 docstring 为"冻结兼容读路径"；`contracts.scan_for_forbidden_markers()` 在真模型可见面（`envpack/bundles.py` PublicTaskBundle、`envpack/training_view.py` RolloutTaskView、`envpack/prepared_tasks.py` 公开产物、`contracts/sandbox.py` env 注入）的检查原样，`tests/envpack/*` 与 `tests/test_w1b_prepared_tasks.py` 的 marker 拒绝测试原样通过（本批全仓跑过）。

`GATE_VERSION`：`rh2.gate.w1b.v2` → **`rh2.gate.w3pre.v3`**（机械升版，被动版本号）。

## 1. T1 决策及理由

1. **T1-1 第七维的版本契约开关 `require_real_weight_versions`（`finalize_rollout` 新增关键字参数，默认 True）。** 直接实现"全部可解析 int"会让冻结的 s1_compat 路径整体不可用：s1 握手按 S1 契约恒 lag=0、版本是静态哨兵 `step_0`（`SlimeBindingConfig.policy_version` 默认值；bringup 也以 `"step_0"` 起步，探针拿到引擎版本后才覆盖），第七维一失败，s1_compat 的"降级即 abort（`rh2_gate_degraded`）"规则会把**每一条** s1 样本剔除——那是改写冻结路径，且触发 T0 条件（改变样本准入）。因此 gate 增加与 `SlimeBindingConfig.require_real_weight_versions` **同名同义**的开关（这是既有的、正交的"版本契约"旗标，不是新发明的 s1 豁免）：True = 数值合法性检查（formal 链启动校验已强制 True，`fa_formal_requires_real_weight_versions`）；False = 只要求握手在场，evidence 如实记 `weight_versions_contract:legacy_sentinel_allowed`。generate.py 按 `self.config.require_real_weight_versions` 传入；governance 测试默认 True。后果：s1_compat 与 verifiers 对照路径的标签维持 W1b T1-7 的 online（不再回摆），s1 交付行为零改变。
2. **T1-2 `BackendHandshake.staleness_threshold` 的"记录用镜像"处理（缺省方式）。** contracts/ 不改：该字段仍必填 int ≥ 0，validator 仍要求 `staleness_within_threshold == steps <= threshold`。语义改为 consume-time 阈值（miles `--max-weight-staleness N`）的记录用镜像，来源 = `SlimeBindingConfig.staleness_threshold`（字段保留、docstring 改写；由启动侧从 miles args 填入归 W4）。**缺省（None）时**：s1_compat 仍写冻结历史值 `S1_COMPAT_LEGACY_STALENESS_THRESHOLD = 4`（冻结路径零改变）；非 s1 写新命名哨兵 **`STALENESS_THRESHOLD_MIRROR_UNBOUNDED = 2**31 − 1`** 并在 audit 时间线记 `staleness_threshold_mirror_unconfigured`（仅当没有注入式 `handshake_builder` 时）。选哨兵而不是复用 4 的理由：miles `--max-weight-staleness` 的缺省就是 `None`（`fully_async_data_buffer.py:188` 不过滤），"无上界"是它的如实镜像；把 S1 的 4 写进 formal evidence 会谎称"后端声明阈值 = 4"。gate 不把该字段写进 EligibilityReport evidence（只记 lag 观测），所以哨兵只出现在 `audit.handshake` 记录里，且有时间线留痕可区分。备选（未采用）：改 contracts 让两字段 Optional——那是 T0，本批未触发；作为开放问题 4 登记。
3. **T1-3 "未来版本"按"任一 seen 版本 > current"判，而不是任务书字面的"min ≤ policy_version"。** 只查 min 会放过 seen=[3, 9] / current=5（lag 非负、但有 token 由比 finalize 时刻 current 更新的权重生成），而消费侧 W1b `_check_leaf_version_binding` 对同一形状已判 FATAL `leaf_version_ahead_of_finalize`，generate.py 正式链 `_build_handshake` 也判 `weight_version_ahead_of_current` fatal——三处口径一致才不会出现"gate 放行、filter 停机"的矛盾。更严不更松，不引入新的拒绝面（该形状本来就在两处被拒）。
4. **T1-4 `FinalizedRollout.scan_result` 直接删除而非 Optional。** `FinalizedRollout` 是进程内聚合值，不是落盘 schema（sidecar 按四类分别落盘，`export_sample.py` 注明"sidecar 没有 scan_result"），也不在 registry；留一个永远 None 的字段只会诱导"有人还在填它"的误读。`ProjectionScanResult` 类型本身冻结保留。
5. **T1-5 `AdmissionPayloadV1` 保留 `finalize_staleness_steps` 为观测值、删 `finalize_staleness_threshold`。** validator 改为只核对在场性："握手缺席 ⟺ policy_staleness 维以 `staleness_facts_missing` 失败"（不再有任何阈值互检）。载荷是运输值、不在 contracts/、无落盘消费者（formal 链挡板未解），形状变更 T1。
6. **T1-6 security 维通过时 evidence 允许为空。** 旧实现靠 `public_projection_scan:clean:*` / `sandbox_capability_facts:*` 留痕区分"扫过且干净"与"没扫"；两者都不再是本维事实源后，"没有执行级违规事实"的如实记录就是空 evidence（有 finding 时仍记 finding id / `attempted_blocked:*` / `patch_hygiene:*`）。不发明装饰性 evidence。
7. **T1-7 旧理由码不再登记 → `unmapped_reason_code` FATAL。** `sandbox_capability_facts_missing` / `sandbox_capability_unverified_*` / `sandbox_capability_violation_*` / `public_projection_marker_hit` / `staleness_exceeded` 若出现在报告里（只可能是旧材料或漏删的 producer），按 W1b T1-11"未登记 code 一律 FATAL"停机，不静默 DROP（参数化测试钉死五个码）。
8. **T1-8 `SandboxCapabilityFacts` 迁到独立冻结模块并保留包级导出。** 留在 gate.py 会与"gate 只消费上游事实"的模块职责冲突；与 `projection_scan.py` 同样处理为"冻结兼容读路径"。`REQUIRED_SANDBOX_CAPABILITIES` 不保留为常量（决策包明写删除"作为 eligibility 必需集"，保留常量会诱导再消费）。
9. **T1-9 `SlimeBindingConfig.staleness_threshold` 字段保留、不再校验。** 若有人传非法值（bool/负数），会在握手构造时被 contracts validator 以 pydantic `ValidationError` 拒绝——处于 finalize 阶段，按 W1b 复核 #2 白名单升 `rh2_contract_validation_failed` run-fatal，仍 fail-closed；不另加启动校验（那是在给一个记录字段重新造门）。

## 2. T1 oracle 改动逐条登记

规则：每一条都对应一处已删除/改判的语义；没有任何"为保绿删测试"。

| 文件 | 改动（原断言 → 新断言 / 删除理由） | 触发的语义删除 |
|---|---|---|
| `tests/governance/test_w1b_security_capability_facts.py`（**整文件删除**，16 例） | `test_capability_facts_present_all_ok_is_online_with_evidence`（evidence 含 `sandbox_capability_facts:lease_0001`）、`test_missing_capability_facts_is_not_online_even_with_no_findings`（缺事实 → `sandbox_capability_facts_missing` / audit）、`test_each_required_capability_unverified_fails_dimension`（×9）、`test_violation_fails_dimension_even_when_all_verified`、`test_not_required_path_records_evidence_and_keeps_old_semantics`、`test_foreign_capability_facts_are_wiring_errors`、`test_capability_facts_must_bind_to_this_attempts_lease` —— 被测机制整体删除；`test_executed_finding_still_fails_with_facts_present` 与 `test_capability_facts_model_rejects_duplicates_and_overlap` 的仍有效部分迁入新文件（后者改用冻结模块与字面量九项，不再依赖常量） | D2-2 |
| `tests/governance/test_w3pre_security_and_version_facts.py`（**新增**，10 例） | 正例：无 sidecar、`findings=()` → online、security evidence 无 `sandbox_capability_facts` / `public_projection_scan`；executed finding 仍失败；签名/模块面删除清单钉死（代码对象常量而非源码文本）；冻结 schema 仍可解析；第七维 缺失 / 非数值（`step_5`、带空白、带符号、`1e2`、`policy_version` 非数值）/ 未来版本（`[121]`、`[119,121]`、`[121,125]`）各负例 + 合法正例（lag 6 > 镜像 4 仍通过，evidence `finalize_lag_observed:6`）；`require_real_weight_versions=False` 允许哨兵且留痕、True 下同一握手判 invalid；gate 不再发出 `staleness_exceeded`、不读 `staleness_within_threshold`/`staleness_threshold`/`accepted` | D2-2 / B-1 |
| `tests/governance/governance_samples.py` | 删 `valid_sandbox_capability_facts` 工厂与 `run_finalize` 的三个 sandbox 参数；新增 `numeric_backend_handshake()`（`policy_version="120"`、`weight_versions_seen=["119","120"]`、lag 1）作为默认握手——contracts 样例的 `step_120` / `default` 是哨兵串，formal 版本契约下不合法；`run_finalize(require_real_weight_versions=True)` 透传 | B-1（契约样例本身未改） |
| `tests/governance/test_wrapper_finalize.py` | `test_happy_path_all_dimensions_ok_is_online`：删 `final.scan_result.clean` 与 `public_projection_scan:clean:*` evidence 断言 → 改断言产物无 `scan_result` 字段、security evidence 无扫描留痕、`finalize_lag_observed:1` 在场；`test_s1_tier_cap_deleted_and_gate_version_bumped`：`GATE_VERSION == "rh2.gate.w1b.v2"` → `"rh2.gate.w3pre.v3"` + 断言 gate 无能力事实/扫描符号；`test_async_grade_and_project_callables_supported`：结论 `audit_only_or_rejected`（未传能力事实）→ `online_policy_loss_eligible`；三处 `sandbox_lease_id="lease_0001"` 关键字删除；`_default_handshake` 改数值握手 | D2-2 / D2-4 / B-1 |
| `tests/governance/test_governance_api_surface.py` | `__all__` 集合删 `REQUIRED_SANDBOX_CAPABILITIES`（`SandboxCapabilityFacts` 保留并注明冻结）；公开函数扫描加入 `sandbox_capability_facts` 模块；`test_unknown_fields_rejected_on_governance_models` / `test_governance_models_are_frozen` 的 `final.scan_result` 样例改为手工构造的冻结 `ProjectionScanResult`；**新增** `test_finalize_rollout_does_not_run_projection_scan`（把 `_scan_public_projection` 换成炸弹，finalize 仍走通） | D2-4 |
| `tests/governance/test_gate_dimensions.py` | `_variant_kwargs("policy_staleness")`：`staleness_steps=6 > 4 → staleness_exceeded` → `weight_versions_seen=["119","121"]`（未来版本）→ `staleness_facts_invalid`（档位仍 offline）；`test_all_seven_dimensions_can_fail_together`：超阈值握手 → 非数值版本握手；`test_security_failure_forces_audit_only_schema_layer` 手工报告的理由码字面量 `public_projection_marker_hit` → `anti_cheat_executed_test_tampering`（纯 schema 测试，避免引用已删码） | B-1 / D2-4 |
| `tests/governance/test_projection_scan.py`（重写，7 → 9 例） | 原 `test_forbidden_marker_in_projection_fails_security_dimension`（命中 → security 失败 → audit）**反转**为 `test_marker_hit_in_projection_no_longer_affects_eligibility`（同一 `fail_to_pass_bonus` 投影 → online、无 `public_projection_marker_hit`、无扫描 evidence、无 `scan_result`）；`test_clean_projection_scan_result_is_clean` / 排序 / 重复运行三条改为直接调用冻结实现 `_scan_public_projection`（它已无生产调用方）；schema 校验器三条原样；新增 clean 投影也无扫描 evidence | D2-4 |
| `tests/governance/test_w1b_admission_disposition.py`（46 → 44 例） | 附录 A 行表删 5 行：`sandbox_capability_facts_missing → DROP`、`sandbox_capability_unverified_non_root_user → DROP`、`sandbox_capability_violation_* → FATAL`、`public_projection_marker_hit → DROP`、`staleness_exceeded → DROP`；加 `staleness_facts_invalid → FATAL`；**新增** `test_deleted_reason_codes_are_now_unregistered_and_fatal`（×5，`unmapped_reason_code:*`）与 `test_policy_staleness_verdict_table_has_only_missing_and_invalid`；删 `test_explicit_staleness_threshold_required`（×4）、`test_staleness_threshold_authority_mismatch_is_fatal`；`test_payload_pins_finalize_staleness_against_report_dimension`（6 > 4 与 report ok 矛盾 / 1 ≤ 4 与 exceeded 矛盾）→ `test_finalize_lag_is_observation_only_and_pinned_to_handshake_presence`（6 > 4 不再矛盾且 KEEP_FULL；握手缺席/在场与 `staleness_facts_missing` 互洽；`staleness_facts_invalid` 与握手在场互洽且 FATAL）+ `test_no_threshold_interface_remains_on_payload_or_pure_function`；`test_pending_not_consulted_when_another_dimension_drops` 的"另一维 DROP"由 `staleness_exceeded` 改 `no_trainable_tokens`；`_decide` 删阈值参数 | B-1 / D2-2 / D2-4 |
| `tests/adapters/test_w1b_delivery_face.py`（18 → 15 例） | 删 `_capability_facts_provider`；`test_all_ok_without_capability_facts_is_delivered_but_drops_by_a3`（无事实 → audit / DROP）与 `test_all_ok_with_capability_facts_is_online_and_keep_full` 合并为 `test_all_ok_without_any_sandbox_sidecar_is_online_and_keep_full`（构造器无 provider 参数、online、KEEP_FULL、security evidence 空）；删 `test_stale_lease_capability_facts_are_run_fatal_via_gate_wiring`（lease 绑定机制删除；GateInputError → fatal 通道由 `test_gate_input_error_in_finalize_is_run_fatal_not_aborted` 继续覆盖）；`test_failed_to_grade_*` 的 `payload.finalize_staleness_threshold == 4` → `payload.finalize_staleness_steps == 0`；删 `test_formal_chain_requires_explicit_staleness_threshold_at_startup`（×3，启动校验已删）与 `test_handshake_without_threshold_is_fatal_in_non_s1_and_legacy_pin_in_s1`（run-fatal 已删）→ 新增 `test_finalize_completes_without_staleness_threshold_and_records_mirror_sentinel`（fa_formal 无阈值：启动通过、finalize 完成、哨兵 + 时间线留痕、online/KEEP_FULL、receipt delivery_prepared）、`test_finalize_lag_beyond_recorded_mirror_is_observation_only`（turns 版本 3 / current 5 / 镜像 0：lag 2、within=False，仍 online/KEEP_FULL）、`test_handshake_threshold_mirror_defaults_by_mode`（s1 → 4、非 s1 → 哨兵、显式值原样） | D2-2 / B-1 |
| `tests/adapters/test_slime_generate.py` | `build_dense_chain` 删 `sandbox_capability_facts_provider` 注入位；s1 happy path：`"sandbox_capability_facts:not_required" in security evidence` → security evidence 为空 + `weight_versions_contract:legacy_sentinel_allowed` 在 policy_staleness evidence（标签仍 online）；`_formal_config` 的 `staleness_threshold=4` 注释改"记录用镜像" | D2-2 / B-1 |
| `tests/adapters/test_offline_export.py`（+1） | 新增 `test_projection_marker_hit_no_longer_blocks_export`：给 parity 链产物的 reward components 加 `fail_to_pass_bonus` 后照常导出（曾 `projection_scan_not_clean` 拒绝） | D2-4 |
| `tests/adapters_miles/test_w1b_group_admission.py`（38 → 38） | 删 `_capability_facts_provider` 与 `_build_chain(capability_facts=...)`；`test_missing_capability_facts_drops_group_by_a3`（`drop_admission_sandbox_capability_facts_missing == 1`）→ `test_group_without_any_sandbox_sidecar_is_admitted`（无 provider 的整链 keep=True、报告 security 通过且 evidence 空、无该指标）；`test_threshold_authority_must_be_reachable_and_consistent`（无 orchestrator → `staleness_threshold_authority_unreachable`；配置 8 ≠ 载荷 4 → `_mismatch`）→ `test_filter_has_no_threshold_authority_and_ignores_config_threshold`（两种情形都准入、模块无 `_threshold_from_args`、载荷无 `finalize_staleness_threshold`）；`admit_group(...)` 调用删阈值参数 | D2-2 / B-1 |
| `tests/adapters_miles/test_w1a_formal_chain.py` / `test_w1b_prepared_chain.py` | 仅注释：`staleness_threshold=4` 由"显式传入（禁止隐式默认）"改"记录用镜像"；值与语义不变 | B-1 |

未改动的相关测试（有意）：`tests/contracts/*`（含 `test_handshake.py` 对 `staleness_within_threshold` validator 的测试——contracts 记录语义不变；`test_f2_1b_outcome_v2.py` / `test_handshake.py` 里 `staleness_exceeded` 作为 contracts 枚举值的用例）；`tests/envpack/*`、`tests/test_w1b_prepared_tasks.py`（真模型可见面 marker 拒绝）；`tests/adapters/test_s1_parity.py`（slime 路仍 online、verifiers 路 `staleness_facts_missing` 分歧点不变）。

## 3. 开放问题 / 接缝

1. **W4 接线（镜像来源）**：`SlimeBindingConfig.staleness_threshold` 现为记录用镜像，bringup（`bringup.py:920` 构造 `SlimeBindingConfig` 处，本批未触碰）尚未从 miles `args.max_weight_staleness` 填入；在 W4 接 consume-time 唯一权威时一并填入（缺省 None 时按 miles 语义无上界，与本批哨兵一致）。W0 旋钮消费者清单（`test_w0_knob_consumption.py::test_knob_consumer_file_sets_locked`）只锁 miles 源码树，rh2 侧填镜像不会红它。
2. **W3b**：security 维现在完全不看 sandbox；W3b 的创建期强制 + 启动前探针 + run 级 `runtime_profile_digest` 记录是唯一的 sandbox 合规面。附录 A 5a"能力 producer 全局未接线 → 启动级 FATAL"随 D2-2 取消，由创建入口的启动前核对取代（决策包 D2-4 末条）。
3. **D2-3 / W3a**：hygiene 命中（`patch_test_tampering` / `patch_forbidden_contamination` / `hygiene_rejected_*`）仍在 security / clean_grading 维失败并在 admission 侧 pending（显式注入 `agent_violation`）。可信评分投影落地时需同批改 producer（控制面不重放、正常出 0/1）并修订这两维的 hygiene 分支——本批按任务书不动。
4. **contracts 记录字段的诚实表示（可选 T0）**：`BackendHandshake.staleness_threshold` / `staleness_within_threshold` 必填导致"未镜像"只能用哨兵表示。若 owner 希望 evidence 里出现 `null` 而不是 `2147483647`，需要 contracts/ schema 改 Optional（T0）。本批未触发该改动；哨兵有命名常量 + 时间线留痕 + gate 不消费三重防误读。
5. **s1_compat 的 `S1_COMPAT_LEGACY_STALENESS_THRESHOLD = 4`** 继续写进 s1 握手记录（冻结路径零改变）。它现在只是记录，日后清理 s1 路径时一并删除。
6. **`registry.py` 未注册** `rh2.sandbox_capability_facts.v1`（W1b 开放问题 5 的一部分）——现在它是冻结 schema，是否注册由集成者决定；本批未动 registry。

## 4. 需集成者同步的文档行（附录 A / W1b 行；本批只列不改）

- `06-first-training-local-execution-plan.md`
  - :161（§5 3a）——标记本批已完成，落账指向本报告。
  - :201（附录 A 5a"能力 producer/消费面全局未接线 → FATAL（启动/preflight 级）"）——随 D2-2 取消，改为"正式 profile 缺必需配置 / 探针未生效 → 不启动/停 run（W3b 创建入口）"。
  - :202（5b"单条合法报告缺正向能力事实 → DROP_GROUP"）——删除（机制不存在）。
  - :205（5e `public_projection_marker_hit`）——删除。
  - :212（7 `staleness_exceeded`（finalize-time）→ DROP_GROUP）——删除；`staleness_facts_missing → FATAL` 行保留；新增 `staleness_facts_invalid`（非法/未来版本，formal 路径）→ ① FATAL。
  - :34（A3 行"security 维改为正向能力事实在场且无违规"）与 :130（W1b 行"两阶段 staleness"）——加"已由 §1.5 D2-2 / B-1 改判"注记（不改写批准史）。
  - :135（W3b 行）与 :167（§6"本次实际能力（sandbox 正向能力事实）"）——措辞改为 run 级记录（`runtime_profile_digest` + 探针报告），不是每轨迹事实。
  - 附录 A 表下方"code 名来自 governance/gate.py 实际发出的 reason_code"——gate 现发出的 security 码只剩 `anti_cheat_executed_*` / `patch_test_tampering` / `patch_forbidden_contamination`；staleness 码 `staleness_facts_missing` / `staleness_facts_invalid`。
- `miles_spike/wave1/w1b_slice2_report.md`（append-only 注记，不改正文）：:14、:16（gate/__init__ 交付物）、:62-64（阈值 fail-fast）、:96（filter 权威配置行）、:112-119（§4 security 新语义与 W3b 落地前形态）、:128（§5 两阶段接口）、:242、:245、:250（附录 A 逐行表 5b/5e/7）、:282（开放问题 3 W3b producer）、:298（T1-9 九项名单）——标"已由 Wave3 前置清理批删除，见 wave3_precleanup_report.md"；`GATE_VERSION` 现为 `rh2.gate.w3pre.v3`。
- `miles_spike/spike-log.md`：落账本批（三项删除 + lane 计数不变）。
- `miles_spike/integration_base_manifest.json`：**expected_counts 无需改**（lane A 322/232、lane B 554/0 与现值相同，见 §5）。
- 决策包 D2-2 里的"删除"清单与本报告 §0 一一对应，无需改。

## 5. 测试证据（2026-09-04 实跑，工作树 = `5b6b2f33` + 本批未提交改动）

```
cd rh2
uv run pytest tests/governance -q                                                        # 108 passed
uv run pytest tests/adapters tests/contracts tests/governance tests/envpack tests/test_w1b_prepared_tasks.py -q   # 999 passed
uv run pytest tests/ -q                                                                  # 1577 passed, 247 skipped
uv run pytest tests/adapters_miles/ -q                                                   # lane A: 322 passed, 232 skipped
RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/ -q   # lane B: 554 passed, 0 skipped
bash rh2/scripts/miles_integration_lanes.sh   # 前置校验（integration tree 773f22b0…/工作树干净/rh2 patch + 12 个语义 patch digest/pin f2b7c792…）全部通过；
                                              # lane A 322p/232s、lane B 554p/0s 精确匹配 manifest，"C5 双 lane 全部通过"
uv run ruff check src/repoharness2 tests experiments/s1_parity.py experiments/s1_7a_bringup/export_sample.py   # All checks passed!
```

**lane 精确计数**：lane A = **322 passed / 232 skipped**，lane B = **554 passed / 0 skipped**——与 manifest 现值相同（`test_w1b_group_admission.py` 两处改动均为 1:1 替换，38 → 38），**manifest 不需要改**。

**全仓计数**：1577 passed / 247 skipped。相对本批之前的净变化 = −7（按文件：删 `test_w1b_security_capability_facts.py` −16；新 `test_w3pre_security_and_version_facts.py` +10；`test_projection_scan.py` +2；`test_w1b_admission_disposition.py` −2；`test_governance_api_surface.py` +1；`test_w1b_delivery_face.py` −3；`test_offline_export.py` +1；其余 0）。

删除面机械自检（review-standards §7）：全仓（src/tests/experiments/scripts）搜 `sandbox_capability_facts_provider|sandbox_capability_facts_required|sandbox_lease_id|REQUIRED_SANDBOX_CAPABILITIES|finalize_staleness_threshold|staleness_threshold_unconfigured|staleness_threshold_required_in_formal_chain|staleness_threshold_authority|staleness_threshold_not_configured|public_projection_marker_hit|scan_result|_scan_public_projection|projection_scan_not_clean|_threshold_from_args`，代码行零残留；剩余命中只在 docstring/注释、contracts/ 既有枚举（`BackendRejectionReason` / `RuntimeFailureCategory` 的 `staleness_exceeded`，未动）与断言"已删除"的测试。

## 6. 协作协议五段收尾

**① 待拍板 T0**：无新增。未触发 contracts/ schema 改动（握手阈值字段以记录用镜像 + 哨兵处理，见 T1-2；诚实表示为 Optional 的可选 T0 登记为开放问题 4，不阻塞）。

**② T1 决策及理由**：§1 T1-1 ~ T1-9。请 owner 特别知悉两条：T1-1（第七维版本契约开关与 `SlimeBindingConfig.require_real_weight_versions` 同名同义；formal 链被启动校验强制 True，s1_compat 沿用 S1 哨兵契约）、T1-2（`STALENESS_THRESHOLD_MIRROR_UNBOUNDED` 哨兵 + 时间线留痕）。

**③ 临时挡板新增/命中/解除**：无新增；`bringup.py:705-713` fa_formal 挡板原样未触碰；`bringup.py` 整体未触碰。删除的都是永久 fail-closed 边界中已被 owner 改判的部分（W1b 的 provider/required/lease 绑定、显式阈值必传/权威一致、exporter 扫描双检）。

**④ 推翻或修正了哪些旧结论**：
- W1b §4"security 维 = 正向能力事实在场且无违规"、"W3b 落地前 formal 样本自然非 online 是预期时序防护"——按 D2-2 整体撤销：合格轨迹无需任何 sidecar 即 online。
- W1b §5 / T1-6"两阶段 staleness、显式阈值必传、载荷阈值 ≠ 权威即 FATAL"——按 B-1 撤销；`S1_COMPAT_LEGACY_STALENESS_THRESHOLD` 由"资格回退值"降为"s1 记录值"。
- W1b T1-9"`REQUIRED_SANDBOX_CAPABILITIES` 九项名单先于 W3b 定义"——删除，不再是消费契约。
- W1b 复核修复 #5（能力事实 lease 绑定）——随机制删除；复核修复 #2（GateInputError → run-fatal 白名单）与 #4（消费侧叶版本绑定）**保留**。
- S1-5 "grade → project → scan → gate" 四步关口——改为三步；S1-8 exporter 的 `projection_scan_not_clean` 双检——删除。
- 附录 A 行 5a/5b/5e/7b 的终态映射——按 §4 列表由集成者回写。

**⑤ 测试/证据/账本状态**：§5；manifest 无需改；spike-log 由集成者落账。

**本轮没有改变哪些已定案语义**：`contracts/` 全部 schema（含 `BackendHandshake` 两个阈值记录字段与 validator、Outcome v2 豁免集、EligibilityReport 五连锁）；W1b 三终态交付面、`AdmissionPayloadV1` 除阈值字段外的全部对账、复合 group filter 的身份/分派/termination/fan-out/版本绑定对账与零方差过滤、`DispositionPolicy` 四槽位未注入 fail-fast（含 hygiene/agent 违规 pending）；W1b 复核修复 #2（结构契约异常升 run-fatal）与 #4（叶版本绑定、负 lag 反例）；`_build_handshake` 正式链的数值版本与"seen 不得比 current 新"fail-closed；A3 无封顶（七维全过即 online）；s1_compat 交付形状（degraded 仍 abort）与 s1 握手记录（阈值 4、恒 lag 0）；真模型可见面（PublicTaskBundle / RolloutTaskView / prepared 公开产物 / sandbox env 注入）的 marker 拒绝；`bringup.py:705-713` 挡板；`reference/`、`rh2/src/slime`、lanes manifest 与 patch 表；faithful DIS loss；W5a 关停链。
