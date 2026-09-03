# W3a 实现报告：formal 评分冻结（D2-1）+ 可信评分投影（D2-3）+ 生命周期分段计时

日期：2026-09-04。执行依据：决策包 `miles_spike/decision_package_D2_B.md` v2（owner 2026-09-04 已批）D2-1 / D2-3 / D2-4；06 计划 §1.5 与 §3 W3a 行；前置清理批报告 `wave3_precleanup_report.md`（本批起点代码形态，HEAD = `b007c0d9`）。本文同时充当本批的 implementation-notes。工作树状态：**未 commit / 未 stash**（任务书禁止）；与 W4 / W10 agent 并行，本文只对本批所有权文件负责（§0 清单），其余工作树改动（`bringup.py`、`capture_wire.py`、`adapters/miles/*`、`tests/adapters_miles/*`、`reference/miles-rh2-integration` 工作树）不是本批的。

## 0. 交付物清单（文件所有权内）

| 文件 | 性质 | 内容 |
|---|---|---|
| `rh2/src/repoharness2/grading/trusted_projection.py` | **新增** | D2-3 可信评分投影纯函数：`classify_control_plane_path` / `split_trusted_scoring_projection` / `build_trusted_scoring_projection` / `expected_candidate_paths`；值对象 `TrustedProjectionSplit`（`to_record()` 审计形态、`evidence_refs()` Outcome 形态、按类计数）与 `IgnoredValidationEntry`；规则版本常量 `TRUSTED_PROJECTION_RULE_VERSION = rh2.trusted_scoring_projection.swe_hygiene.v1`。只 import contracts，producer 与 grader 共用同一实现 |
| `rh2/src/repoharness2/adapters/slime/attempt_timing.py` | **新增** | D2-1 验收项：十三段 `LIFECYCLE_SEGMENTS`、`AttemptLifecycleTiming`（set/get/to_dict/from_dict）、`SegmentStopwatch`、`percentile_nearest_rank`、`aggregate_lifecycle_timings`（p50/p95/max/mean + 反压 attempt 数）、`extract_lifecycle_timing`（从 bringup execution audit 记录取数）、`main`（`python -m repoharness2.adapters.slime.attempt_timing <audit.jsonl|timing.json>...`） |
| `rh2/src/repoharness2/adapters/slime/generate.py` | 修改 | ① D2-1 状态所有权转移：artifact 本体持久化成功后**立即释放 rollout 容器**（新 `_release_rollout_container` :4084，调用点 :3136），`grading_workspace = None`；② 删除评分后 `verify_integrity()` 主链块（原 :3238-3291），`snapshot_integrity_mismatch` / `integrity_recheck_failed` 不再由 producer 发出；③ D2-3：删 `screen_frozen_entries` 的 task 级 hygiene → unsafe 分支，改为 `build_trusted_scoring_projection` 拆分（:3221-3230），`unsafe_artifact_reasons` 只剩结构不安全码；④ 计时：`RolloutAudit.lifecycle_timing / freeze_monotonic / rollout_container_released_before_grading / trusted_projection / ignored_validation_entry_count` 字段、`note_rollout_container_released()`、`timing_summary()` 新增 `lifecycle_timing` 与 `rollout_container_released_before_grading` 键、`_record_export_segments` / `_record_grader_timing`、ctor 新注入位 `grader_phase_timing_source`；⑤ `_write_artifacts` 新 sidecar `trusted_scoring_projection.json` / `attempt_lifecycle_timing.json`；⑥ finally 段：receipt 失败时只对**仍存在**的容器入隔离队列；隔离队列去重 |
| `rh2/src/repoharness2/grading/manager.py` | 修改 | ① `_verify_frozen_delta_binding`：投影路径集必须**等于**按 `spec.hygiene` 独立重算的 candidate 集（:1403；悬空引用单独文案）；② 删 `unscreened_hygiene_hit` infra 保险杠 → `BaselineIntegrityError("scoring_projection_split_inconsistent")`（不可达的防御）；③ `GraderPhaseTiming`（:700）+ `take_grader_phase_timing`（:765）+ FIFO 上限 1024；grade() 六段计时 `phase.add(...)`；④ docstring 同步 |
| `rh2/src/repoharness2/grading/queue.py` | 修改 | `backpressure_count` / `active_grading_count` / `queue_depth` 属性（"评分队列打满次数"） |
| `rh2/src/repoharness2/adapters/slime/patch_exporter.py` | 修改 | `export_frozen_patch(..., segment_sink=None)` 记 `post_census` / `artifact_capture`；第 2/3 步拆为 `_capture_changes`（逻辑逐字不动） |
| `rh2/src/repoharness2/adapters/slime/quiescence_barrier.py` | 修改（仅文本） | 模块/类 docstring：`verify_integrity` 降为调试探针，正式链不调用 |
| `rh2/src/repoharness2/grading/__init__.py` | 修改 | 导出新符号（`GraderPhaseTiming`、`GRADER_PHASE_SEGMENTS`、trusted_projection 六项） |
| `rh2/tests/adapters/test_w3a_formal_grading_freeze.py`（10 例）、`test_w3a_trusted_projection.py`（19 例）、`test_w3a_attempt_timing.py`（11 例） | **新增** | 见 §6 |
| 既有测试 oracle 改动（逐条 T1 登记，§5） | 修改 | `test_b5_finalization.py`、`test_w1b_termination_facts_producer.py`、`test_f2_2b_barrier.py`、`test_w1b_delivery_face.py`、`tests/grading/test_b4_frozen_delta.py`、`tests/contracts/test_f2_2b_b3_hygiene.py`；`test_slime_generate.py` 只加替身旋钮（`FakeRolloutDocker.rm_fail_times / exec_after_rm_raises / rm_attempts`），无 oracle 改动 |

**未触碰**：`bringup.py`（含 :705-713 挡板）、`adapters/miles/*`、`governance/*`、`envpack/*`、`contracts/*`（零改动，含 `unsafe_artifact_permanent_rejection` 豁免集、`PatchHygieneResult`、`GradingTimingRecord`）、`reference/`、`rh2/src/slime`、lanes manifest、`tests/adapters_miles/*`。

## 1. D2-1 状态所有权转移的落点（代码事实，`generate.py`）

正式顺序（`_generate_attempt` fa_formal 分支，自上而下）：

| 步骤 | 位置 | 说明 |
|---|---|---|
| 停止 execution scope + 双读指纹 | `_runtime_barrier.establish()`（:2975 起，计时 `runtime_quiescence` :2997）；确认后 `audit.freeze_monotonic` 记冻结时刻（:3003） | 不变 |
| post census + 变更抓取 | `export_frozen_patch(..., segment_sink=export_segments)`（:3028）；`post_census` / `artifact_capture` 两段由 exporter 写回 | 不变（只加计时） |
| 身份/digest 校验 + 持久化 | exporter 内部重算 baseline digest；`put_artifact_bodies`（:3103-3125，计时 `artifact_persist`）；`FinalizationStoreConflict` 仍 run-halt，其它失败仍 `frozen_artifact_persist_failed` missing 收口 | 不变 |
| **冻结产物成为唯一权威 → 立即释放 rollout 容器** | `await self._release_rollout_container(sandbox, audit)`（:3136）→ `grading_workspace = None` | **新**。`docker rm -f` 成功 → `lease_released=True`、`rollout_container_released_before_grading=True`、时间线 `rollout_container_released`、hold 段闭合；rm 失败（退出码非 0 / 超时）→ `CleanupFailureRecord(remove_container)`、时间线 `rollout_container_release_failed`，finally 再试一次（幂等）；docker 通道异常（OSError）→ `container_release_exception` 落账 + 隔离队列（去重）。三种情况**都不影响评分**（容器已不持有任何事实） |
| 结构 hygiene | `classify_frozen_patch`（:3160 起）：symlink 逃逸 / 排除 namespace 内 entry / 非 UTF-8 target → `unsafe_artifact_permanent_rejection`（present + 永久拒绝，不评分，真实交付，filter 按封闭豁免集 DROP） | 不变，但**只剩结构不安全** |
| 可信评分投影拆分 | `build_trusted_scoring_projection(frozen_patch, grading_spec.hygiene)`（:3224）→ `FrozenDeltaSource(projection=candidate 集)` | **新**（§2） |
| 有界评分队列 → fresh grader | `_finalize` → `_grading_submit(workspace=None, frozen_delta=...)`；grader 侧 `_verify_frozen_delta_binding` + baseline 重建 + candidate 重放 + 后写 official test_patch + eval | grader 只收 `FrozenDeltaSource`，且投影必须等于其独立重算（§2.3） |
| 评分后 | **不再** `verify_integrity()` | 原 :3238-3291 整块删除（§3 T1-2） |
| finally | receipt → session drop / 容器 cleanup（已释放则幂等跳过）→ poison release → cleanup 追加 → audit sink | B5 顺序对"容器之外"的清理不变；receipt 失败时只对**仍存在**的容器入隔离队列 |

**容器保留到 receipt 之后的两种 attempt**（未建立 artifact 本体，容器仍是唯一证据）：`unsupported_object_in_patch`（FIFO 等，`rejection_evidence` 内嵌 receipt）与 `frozen_artifact_persist_failed`；以及一切冻结之前失败的 attempt（harness 崩溃等）。测试：`test_unsupported_object_keeps_container_until_receipt`、`test_receipt_persist_failure_before_release_retains_workspace_and_run_halts`。

**验收前提测试**（`test_w3a_formal_grading_freeze.py`）：
- `test_rollout_container_released_before_grading_and_grader_never_reaches_it`：提交评分时 rollout 容器已在 `docker.removed`；评分侧 docker 调用面从未出现该容器名；替身 `exec_after_rm_raises=True` 下整条链无一次触碰；时间线 `artifact_bodies_persisted < rollout_container_released < grading_started`。
- `test_grader_completes_from_persisted_artifact_alone`：评分 submit 无视内存 `frozen_delta`，只从 store 本体 JSON 往返重建 artifact/baseline、用 `spec.hygiene` 重算投影，digest 与内存对象相同，真实 `SWEGradingManager` 完成评分（tests_failed / reward 0）。
- `test_verify_integrity_no_longer_referenced_by_the_formal_chain`：`_generate_attempt.__code__` 不引用 `verify_integrity`，常量池无 `snapshot_integrity_mismatch` / `integrity_recheck_failed`，含 `_release_rollout_container`。

## 2. D2-3 可信评分投影：拆分规则与审计字段

### 2.1 规则（首训口径 = 当前 SWE adapter `HygieneRules`，排除法）

`classify_control_plane_path(rules, path)`，优先级自上而下、一条路径只记一个类别：

| 类别 | 判据 | 例 |
|---|---|---|
| `official_test_file` | `path in rules.test_files`（official test_patch 触碰的精确文件，prepared 链由 `build_grading_spec_from_host_view` 从 `PrivateGradingBundleV2.test_patch` 提取） | `tests/test_official.py` |
| `test_glob` | `rules.is_test_path(path)`（`DEFAULT_SWE_TEST_GLOBS`：`*tests/*`、`*testing/*`、`test_*.py`、`*/test_*.py`、`*_test.py`、`*/*_test.py`） | `tests/test_new.py`、`pkg/mod_test.py` |
| `reserved_namespace` | `rules.is_forbidden_path(path)`（`DEFAULT_SWE_FORBIDDEN_GLOBS`：`.rh2*`、`rh2/*`）——**命名空间冲突**，不进投影，不宣称边界突破 | `rh2/inject.sh`、`.rh2_note` |
| `None` = solution surface | 其余全部 | `src/fix.py`、`docs/x.md`、**也包括** `conftest.py` / `pytest.ini` / `tox.ini` / `setup.cfg`（已知不足，登记不修，见 §7-1） |

拆分 `split_trusted_scoring_projection(entries, rules)`：候选集与忽略集按 path 排序、两者不交、并集 = 输入路径集（测试钉死）。删除操作同样分类（删 official 测试文件 = `official_test_file` 类的 `delete` entry，不重放，grader 后写 official test_patch 时该文件从 clean baseline 恢复）。

### 2.2 "不再 unsafe" 的路径类 / 仍是 unsafe 的路径类

| 之前（B3/B4） | 现在（W3a） |
|---|---|
| 测试文件精确命中 → `test_file_modified:<p>` → `unsafe_artifact_permanent_rejection`（不评分、reward 不可得、整组 DROP） | `official_test_file` / `test_glob` → **忽略不重放，照常评分**（只改测试没修代码 → 自然 0；写测试且真修好 → 1） |
| 保留路径 `.rh2*` / `rh2/*` → `forbidden_path_touched:<p>` → unsafe | `reserved_namespace` → 忽略不重放，照常评分，不 fatal |
| symlink escape / `entry_in_excluded_namespace` / `unsafe_symlink_into_excluded_namespace` / `unsupported_symlink_target_encoding` → unsafe | **不变**：仍 `unsafe_artifact_permanent_rejection`（结构不安全，不进投影） |
| FIFO/device（`unsupported_object_in_patch`） → unsafe（artifact 建立前） | **不变** |

`contracts/fa_runtime.py` 的封闭豁免集**未改**（`unsafe_artifact_permanent_rejection` 形状谓词原样）；本批只是把普通测试/控制面改动从该路径移出，结构不安全 artifact 仍走它。hidden/golden 材料读取、隔离失效等 infra/security failure 归 W3b（本批未触及其判定源）。

### 2.3 grader 侧信任边界

`SWEGradingManager._verify_frozen_delta_binding`（:1403）：`set(projection.included_entry_paths)` 必须 (a) ⊆ artifact 路径集（否则"含 artifact 不存在的路径"），且 (b) **== `expected_candidate_paths(artifact.entries, spec.hygiene)`**（否则"projection 路径集 != 可信评分投影重算的 candidate_solution 路径集"），两者都是 `frozen_delta_binding_mismatch` run-halt。B4 v1 的"等于 artifact 全路径集"是控制面为空时的特例。这样投影既不能"隐去"solution 路径也不能"夹带"控制面路径；producer 与 grader 用同一函数、同一 `HygieneRules`（同一 attempt 的同一 `GradingEnvSpec`）。随后 `screen_frozen_entries(candidate)` 恒 clean；若不 clean = 程序错误 → `scoring_projection_split_inconsistent`（BaselineIntegrityError，不可达的防御，取代旧 `unscreened_hygiene_hit` infra 保险杠）。

`PatchHygieneResult`（contracts，未改）在 FA 路径描述的是**已重放的 candidate 子集**：`verdict=clean`、`test_files_modified=False`、`cleaned_patch_digest` = 该子集的 `applied_entry_set` digest、`replayed_on_clean_checkout` = 应用完成。gate 的 `patch_test_tampering` / `hygiene_rejected_*` 分支与 admission 的 pending 映射（governance，未改）因此在 formal SWE producer 上**不可达**；S1 diff 文本路径（`clean_patch`）不变，仍可产生这些码（§3 T1-4）。

### 2.4 审计 / 遥测字段

| 载体 | 字段 | 内容 |
|---|---|---|
| `RolloutAudit.trusted_projection`（dict，`TrustedProjectionSplit.to_record()`） | `rule_version`、`candidate_solution_paths`、`candidate_solution_count`、`ignored_validation_entries[{path, operation, object_type, control_plane_class}]`、`ignored_validation_count`、`ignored_validation_counts_by_class{official_test_file,test_glob,reserved_namespace}` | 全量路径清单（发现分布漂移） |
| `RolloutAudit.scoring_projection_entry_count` / `ignored_validation_entry_count` | int | 前者含义改为 candidate 数（bringup audit 记录已写该键） |
| 时间线 | `scoring_projection_built`；ignored 非空时 `ignored_validation_delta_recorded` | |
| Outcome v2 `evidence_refs`（成功路径） | `trusted_projection:<rule_version>`、`trusted_projection:candidate=<n>:ignored=<m>`、逐条 `ignored_validation_delta:<class>:<op>:<path>`（上限 50 条，超出记 `ignored_validation_delta_truncated:<k>`） | 随 receipt / bringup audit JSONL / admission 载荷持久化 |
| sidecar（交付路径，`artifact_dir/<trajectory>/`） | `trusted_scoring_projection.json` | = `to_record()` |
| `FrozenDeltaSource.projection.included_entry_paths` | candidate 路径 | grader 唯一读到的投影 |

## 3. T1 决策及理由

1. **T1-1 释放点 = artifact 本体持久化成功之后、结构 hygiene 之前（B5 的"receipt 之后才 cleanup"对容器移除收窄）。** D2-1 原文"持久化成功后……立即释放 rollout 容器"与 B5"cleanup 只许在 receipt 持久化之后"在容器这一项上不可能同时成立（receipt 需要评分结果，评分在释放之后）。本批取 D2-1：容器移除的前提改为"本体已 durable"（容器不再持有任何独有状态；exporter 已对每个变更文件做内容 digest == census digest 一致性检查、artifact 以 digest 绑定持久化），receipt 之后仍执行的是 session drop / poison release / cleanup 追加记录 / audit sink。后果：post-release 的 receipt 写失败不再有容器可"保留现场"，证据 = 已持久化的本体 + audit；run-halt 语义不变。若 owner 要求字面 B5（容器也等 receipt），等价于放弃 D2-1 的"立即释放"——请在复核时明示。
2. **T1-2 `verify_integrity` 主链依赖删除（二选一取"删除"，不保留为探针调用）。** 容器在评分前已释放，评分后没有 live 状态可复核；若改为"释放前探针"只是多一次 `git status + git diff` exec、延长 `rollout_container_hold_after_freeze`，且信号弱于 exporter 已做的逐文件 digest 一致性检查。`FrozenWorkspace.verify_integrity()` 方法保留（单元测试 `test_frozen_workspace_integrity_recheck` 原样），docstring 标为调试探针；`snapshot_integrity_mismatch` 留在 contracts 封闭集（未改 schema），producer 不再发出；`integrity_recheck_failed` fatal 通道随之消失（`FAILURE_CODE_TERMINATION_MAP` 本就不含它）。
3. **T1-3 投影不一致 = run-halt（不是 infra 成员损耗）。** 旧 `unscreened_hygiene_hit` 把"控制面 entry 到达 grader"当编排缺陷记 failed_to_grade；现在 producer 与 grader 用同一纯函数计算，任何不等只可能是持久化/装配层错误或篡改 → 与既有 `frozen_delta_binding_mismatch` 同通道。新增拒绝面 = 无（run-halt 不是样本剔除；正常运行不可达）。
4. **T1-4 S1 diff 文本路径（`clean_patch` / `CleanedPatch` / s1_compat）零改变。** D2-3 的公共不变量按首训 formal 链落地；S1 路径是冻结回退面，改它会改变 s1_compat 样本处置（触 T0 条件）且不在 W3a 验收内。后果：`PatchHygieneResult.test_files_modified=True` 与 gate 的 `patch_test_tampering` / admission pending 分支只剩 S1 路径可达（§7-3）。
5. **T1-5 控制面改动的记录不进 contracts。** `PatchHygieneResult` 的 `test_files_modified=True` 会强制 `verdict=rejected_test_tampering` 并封顶 resolved，与 D2-3 矛盾；因此 ignored 清单落在 adapters 侧（audit dict + Outcome evidence_refs 字符串 + sidecar），不新增契约字段（那是 T0，见 §7-2）。
6. **T1-6 计时落盘经 `timing_summary()` 嵌套键，不改 bringup。** bringup 的 `write_execution_audit_record` 已原样写 `audit.timing_summary()`，因此十三段记录随 execution audit JSONL 落盘（测试用 bringup 的写函数只读验证）；grader 内部六段经新注入位 `grader_phase_timing_source` 取 `SWEGradingManager.take_grader_phase_timing`，**生产接线归 bringup（§8 接缝 1）**；未接线时只填 `test`（与 `GradingTimingRecord.test_seconds` 同源）和队列等待，其余 grader 段为 None 并留痕 `grader_phase_timing_unavailable`——不用五类计时的 `prep`/`env_reset` 冒充细分段。
7. **T1-7 `rollout_container_hold_after_freeze` 起点 = 屏障确认时刻（`runtime_quiescence_confirmed`），终点 = `docker rm` 确认成功（提前释放或 finally 兜底，只记一次）。** 释放失败且 finally 也失败 → None（从未确认移除），不伪造。
8. **T1-8 manager 分段暂存 FIFO 上限 1024。** 无消费者（bringup 未接线）时淘汰最旧记录，防长 run 无界增长；取走即删。
9. **T1-9 隔离队列去重 + receipt 失败只隔离仍存在的容器。** 释放异常与 finally 清理异常同一容器不重复入队；已释放容器不入队（无现场可保留）。

## 4. 偏离说明

- 任务书"`verify_integrity` 改为非阻塞 debug 探针或删除，二选一"→ 取删除（T1-2）。
- 任务书"cleanup 仍守 B5：receipt 持久化之后"→ 按 T1-1 解读为"容器之外的清理仍在 receipt 之后；容器移除以本体持久化为前提"。
- 未新增 miles lane 测试：组级 KEEP_FULL 由 `decide_member_disposition` 纯函数在交付面测试直接钉死（`test_test_path_change_is_projected_not_unsafe_and_keeps_full`、`test_test_only_change_scores_zero_and_enters_group_normally`），复合 group filter 不读投影记录；本批对 `tests/adapters_miles` 零改动，lane 计数 W3a 贡献为 0（§6）。
- 未做：grader 长驻复用、baseline 缓存、tar 流式重放（按 D2-1 等计时证据）；通用控制面规则引擎（按 owner 细化等 taskset）。

## 5. T1 oracle 改动逐条登记

| 文件 | 改动（原断言 → 新断言） | 触发语义 |
|---|---|---|
| `tests/adapters/test_b5_finalization.py` | `test_receipt_persists_before_any_cleanup`（persist_receipt < docker_rm）→ `test_artifact_persist_then_release_then_grading_then_receipt_then_append`（严格序列 put_artifact_bodies < docker_rm < grading_submit < persist_receipt < append_cleanup_result；rm 恰一次）；`test_receipt_persist_failure_retains_workspace_and_run_halts` → 拆两例：`..._before_release_...`（harness 崩溃形态：不 rm、隔离、run-halt，逐字保留旧断言）+ **新增** `..._after_release_run_halts_without_quarantine`（rm 在 receipt 前、bodies 已存、隔离队列空、`cleanup_skipped_receipt_failure`、run-halt）；`test_abort_path_still_gets_receipt`（测试文件 → unsafe、不评分、persist_receipt < docker_rm）→ `test_test_only_change_is_graded_normally_not_unsafe`（评分发生、投影为空、ignored 记录 `test_glob`、reason_code None、EligibilityReport 在场、put_artifact_bodies < docker_rm < persist_receipt）；模块 docstring 注记 | D2-1 / D2-3 |
| `tests/adapters/test_w1b_termination_facts_producer.py` | `test_split_1_verify_integrity_false_is_missing_abort_producer_once`（漂移 → missing/ABORTED）与 `test_split_2_verify_integrity_exception_is_run_fatal`（复核异常 → fatal）→ 合并为参数化 `test_split_1_2_frozen_workspace_probe_not_consulted_after_release`（drifted / raising 替身都不被调用；present_complete、delivery_prepared、`fresh_grading_complete=True`、容器评分前释放）；docstring ①② 改判 | D2-1 |
| `tests/adapters/test_f2_2b_barrier.py` | `test_e2e_integrity_drift_after_grading_closes_as_missing` → `test_e2e_drift_after_release_is_irrelevant_container_already_gone`（探针调用计数 0、present_complete、真实交付、`docker.removed == [容器]`）；方法级 `test_frozen_workspace_integrity_recheck` 原样；docstring ③ 改判 | D2-1 |
| `tests/adapters/test_w1b_delivery_face.py` | `test_unsafe_is_delivered_without_report_and_drops_by_exemption`（触发条件 = 测试文件）→ `test_structurally_unsafe_artifact_is_delivered_without_report_and_drops_by_exemption`（触发条件 = symlink 逃逸；其余断言逐字保留，另加 `unsafe_symlink_escape:src/escape` 与释放旗标）；**新增** `test_test_path_change_is_projected_not_unsafe_and_keeps_full`（投影为空、reward 1、KEEP_FULL、evidence 含 ignored 路径）；新 helper `_frozen_ws_with_entries`（其 `verify_integrity` 一旦被调用即炸） | D2-3 |
| `tests/grading/test_b4_frozen_delta.py` | `test_unscreened_tampering_entry_is_infra_belt`（failed_to_grade + `unscreened_hygiene_hit`）→ `test_projection_including_control_plane_entry_is_binding_mismatch`（`frozen_delta_binding_mismatch` run-halt、不起容器）；`test_projection_omitting_entry_is_run_halt`（隐去**测试** entry → run-halt）→ `test_projection_omitting_solution_entry_is_run_halt`（隐去 **solution** entry → run-halt；隐去测试 entry 现在是正确投影）；**新增** `test_projection_excluding_control_plane_entry_grades_candidate_only`（只重放 src/fix.py、hygiene clean、digest = 子集）与 `test_projection_with_unknown_path_is_run_halt`（悬空引用） | D2-3 |
| `tests/contracts/test_f2_2b_b3_hygiene.py` | `test_e2e_test_tampering_is_permanent_rejection_no_grader` → `test_e2e_test_path_change_is_projected_and_graded_not_permanent_rejection`（grader 运行、投影为空、完整 artifact 保留、reason_code None、reward 可得、evidence 含 ignored、七维全过）；模块 docstring 注记；`test_symlink_escape_is_unsafe` 等结构 unsafe 用例原样 | D2-3 |
| `tests/adapters/test_slime_generate.py` | 仅 `FakeRolloutDocker` 加 `rm_fail_times` / `exec_after_rm_raises` / `rm_attempts` 旋钮（默认行为逐字不变）；无 oracle 改动 | — |

未改动的相关测试（有意）：`tests/contracts/*` 其余（`PatchHygieneResult` 校验器、Outcome v2 豁免集、`RUNTIME_QUIESCENCE_REASON_CODES` 含 `snapshot_integrity_mismatch`）；`tests/governance/test_gate_dimensions.py::test_hygiene_tampering_fails_security_and_clean_grading`（S1 diff 路径的 hygiene 报告形态仍合法）；`tests/grading/test_manager_unit.py` 的 S1 篡改/污染封顶用例；`tests/adapters_miles/*`。

## 6. 测试证据（2026-09-04 实跑，工作树 = `b007c0d9` + 本批 + 并行 W4/W10 未提交改动）

```
cd rh2
uv run pytest tests/adapters/test_w3a_formal_grading_freeze.py tests/adapters/test_w3a_trusted_projection.py tests/adapters/test_w3a_attempt_timing.py -q   # 40 passed
uv run pytest tests/adapters/test_b5_finalization.py tests/adapters/test_w1b_termination_facts_producer.py tests/adapters/test_f2_2b_barrier.py tests/adapters/test_w1b_delivery_face.py tests/grading tests/contracts/test_f2_2b_b3_hygiene.py -q   # 143 passed, 15 skipped
uv run pytest tests/adapters tests/contracts tests/governance tests/grading tests/envpack tests/test_w1b_prepared_tasks.py -q   # 1117 passed, 15 skipped
uv run pytest tests/ -q                                                                  # 1638 passed, 292 skipped
uv run pytest tests/adapters_miles/ -q                                                   # lane A: 339 passed, 277 skipped
RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/ -q   # lane B: 615 passed, 1 failed
bash scripts/miles_integration_lanes.sh   # 前置校验 1 红：integration checkout 工作树不干净（W4/W10 的 miles 侧未提交改动：
                                          # rollout_manager.py / fully_async_data_buffer.py / arguments.py / rh2_engine_versions.py 等），未跑到 pytest
uv run ruff check src/repoharness2 tests experiments/s1_parity.py experiments/s1_7a_bringup/export_sample.py   # All checks passed!
```

**计数归因**（本批对 `tests/adapters_miles` 零改动）：
- 全仓 1577 → 1638（+61）。本批净 +44：新文件 +40（10 + 19 + 11）；`test_b4_frozen_delta.py` +2；`test_b5_finalization.py` +1；`test_w1b_delivery_face.py` +1；其余 1:1 替换（termination facts 2 例 → 参数化 2 例）。其余 +17（及 skip 247 → 292）来自并行 agent 新增/删除的 `tests/adapters_miles` 文件（`test_w4_*.py`、`test_w10_multi_engine.py`、删 `test_bringup_weight_version_probe.py`、改 `conftest.py`），不是本批。
- lane A 322/232 → 339/277、lane B 554/0 → 615 + 1 failed：排除并行 agent 的四个新文件后重跑 lane A = **318 passed / 232 skipped**、lane B = **549 passed / 1 failed**——相对 manifest −4 = 并行 agent 删除的 `test_bringup_weight_version_probe.py`；lane B 唯一失败 `test_g1_acceptance_events.py::test_producer_tree_digest_matches_audit_manifest` = integration 工作树被并行 agent 改脏后树 digest 与 manifest 不符。**W3a 对两条 lane 的计数贡献为 0，manifest 无需因本批改动。** 最终精确计数须在 W4/W10 落账（含 manifest 更新）后由集成者重跑 `miles_integration_lanes.sh` 取得。

删除面机械自检（review-standards §7）：全仓（src/tests/experiments/scripts）搜 `unscreened_hygiene_hit|test_file_modified:|forbidden_path_touched:|integrity_recheck_failed|snapshot_integrity_mismatch|verify_integrity`——代码行零残留；剩余命中只在注释/docstring、contracts 既有封闭集、断言"不再出现"的测试与 `FrozenWorkspace.verify_integrity` 方法本体（调试探针）。形状改动消费点：`RolloutAudit` 新字段的消费者 = bringup `write_execution_audit_record`（经 `timing_summary()`）、`_write_artifacts`、测试；`timing_summary()` 返回类型 `dict[str, Any]`（`test_glue_factories.py` 用 stub，不受影响）；`_finalize(workspace: Any | None)` 调用点唯一；`FrozenDeltaSource.projection` 语义改变的消费者 = `_verify_frozen_delta_binding`（已改）与 `_apply_frozen_delta`（按 `plan.applied_paths`，无需改）。

## 7. 开放问题

1. **通用控制面定义（登记不修）**：`conftest.py`、`pytest.ini`、`tox.ini`、`setup.cfg` / `pyproject.toml` 的 pytest 段、测试插件、启动脚本等真正能改变测试收集/执行的文件不在 `HygieneRules` 内，会被当作 solution surface 重放。按 owner 细化等 taskset 确定后由最终 environment adapter 声明 `allowed solution surface / evaluator·control surface / official test 恢复与注入规则`；`TRUSTED_PROJECTION_RULE_VERSION` 预留了规则版本字段。
2. **ignored_validation_delta 是否进契约（可选 T0）**：目前只在 audit dict / Outcome evidence 字符串 / sidecar；若要 typed 记录（例如 `GradingReport` 或 Outcome 新字段），需改 contracts/ = T0。`evidence_refs` 逐条路径有 50 条上限（超出计数标注），全量在 audit/sidecar。
3. **governance 侧的 hygiene 分支现在只对 S1 路径可达**：gate `_dim_security_and_leakage` 的 `patch_test_tampering` / `patch_forbidden_contamination`、`_dim_clean_grading` 的 `hygiene_rejected_*` 与 admission 的 `_PENDING` 映射（governance/*，本批不得改）在 formal SWE producer 上不再有 producer。是否收口（删除或改注释）归 governance 所有者，与 D2-3 附录 A 行同步。
4. **bringup 侧未接线项**（§8 接缝）：grader 六段计时需要一行注入；`trusted_scoring_projection` 记录目前只经 Outcome evidence 与交付路径 sidecar 持久化（bringup 的 execution audit 记录未含 `audit.trusted_projection`）。
5. **`rollout_container_hold_after_freeze` 的构成**：正常路径 = post_census + artifact_capture + artifact_persist + `docker rm`；GPU spike 报告应拆看这四段（都已单独记录），再决定 tar 流式重放 / baseline 缓存是否值得做。
6. **S1 路径与 D2-3 的口径差**：s1_compat / verifiers 薄壳仍按 A7 剥离重放 + 封顶；若 S1 路径要与 D2-3 对齐，涉及 s1 样本处置改变（T0），本批未动。

## 8. 接缝（需 bringup / governance 配合，本批不得改）

1. **bringup.py**（`RolloutOrchestrator(...)` 构造处，约 :1047）：加 `grader_phase_timing_source=self.grading_manager.take_grader_phase_timing`，grader 六段即进入 attempt 记录；否则记录只含 `test`/队列等待并留痕 `grader_phase_timing_unavailable`。
2. **bringup.py `write_execution_audit_record`**：建议加 `"trusted_projection": audit.trusted_projection` 与 `"ignored_validation_entry_count": audit.ignored_validation_entry_count`（`timing_summary` 已携带计时，无需另加）；`FileFinalizationStore.put_artifact_bodies` 可另存 `scoring_projection.json`（投影 + 拆分记录）以便 F2-4/审计单点读取——签名固定为两个 kwarg，本批未扩。
3. **bringup.py `BringupService`**：run 结束时输出 `grading_queue.backpressure_count` 与 `aggregate_lifecycle_timings(...)` 的结果到 run evidence（GPU spike 报告 p50/p95 的取数点；命令行 `python -m repoharness2.adapters.slime.attempt_timing <execution_audit.jsonl>` 可离线聚合）。
4. **governance**（gate/admission）：§7-3。
5. **06 计划 / 附录 A**（集成者回写）：W3a 行标记完成并指向本报告；附录 A 中"测试篡改 → unsafe 永久拒绝 / pending"相关行按 D2-3 改判（控制面改动 = 记录不重放、正常评分；unsafe 只指结构不安全）；`snapshot_integrity_mismatch` 行注记"W3a 起 producer 不再发出（contracts 封闭集保留）"。
6. **spike-log / integration manifest**：本批 lane 贡献 0；manifest 的下一次更新由 W4/W10 落账时一并处理。

## 9. 计时字段表（`AttemptLifecycleTiming.segments_seconds`，单位秒，monotonic 差值；None = 未发生/未测到）

| 段 | 起点 → 终点 | 记录者 | 备注 |
|---|---|---|---|
| `runtime_quiescence` | `_runtime_barrier.establish()` 调用前 → 返回 QuiescenceConfirmed | generate.py :2974-2999 | 拒绝路径不记（attempt 收口 missing） |
| `baseline_census` | `generate_baseline_manifest` 前 → 后 | generate.py :2610-2623 | materialize 段，harness 动工前 |
| `post_census` | exporter census 脚本发出 → 解析完成（失败也记） | patch_exporter.py | |
| `artifact_capture` | host 侧 diff + 内容抓取 + 一致性检查 + 组装 | patch_exporter.py | |
| `artifact_persist` | `put_artifact_bodies` 前 → 后 | generate.py :3103-3125 | |
| `grading_queue_wait` | `GradingQueue.submit` → worker 出队（含反压阻塞） | queue.py → `GradingTimingRecord.queue_wait_seconds` | 另记 `grading_queue_depth_at_enqueue` / `grading_backpressure_triggered` |
| `grader_start_and_verify` | `grade()` 入口 → 绑定检查 + 镜像就绪 + 起容器 + 镜像 digest + clean checkout 血缘核验完成 | manager.py :1004 | 含 S1 路径的 patch 导出 |
| `grader_baseline_rebuild` | `_verify_baseline_rebuild` | manager.py :1016 | S1 路径 None |
| `delta_apply` | `_apply_frozen_delta` / `_replay_patch` | manager.py :1020/:1025 | |
| `test` | `_run_eval` | manager.py :1047（= `GradingTimingRecord.test_seconds`） | 未注入分段源时也能填 |
| `parser_and_report` | eval 返回 → 峰值内存读取 + parser + GradingReport 构造完成（infra / apply 失败路径同样记） | manager.py :1040/:1077/:1100 | |
| `grader_cleanup` | finally `_remove_container` | manager.py :1106 | |
| `rollout_container_hold_after_freeze` | 屏障确认时刻 → rollout 容器 `docker rm` 确认成功 | generate.py `note_rollout_container_released` :2090（经 `_cleanup_container` :4565） | 提前释放或 finally 兜底，只记一次；从未确认移除 → None |

聚合：`aggregate_lifecycle_timings(records)` → 每段 `count/p50/p95/max/mean`（最近秩法）+ `attempts_with_backpressure` + `queue_depth_at_enqueue_p50/p95` + `grader_segment_source_counts`（manager / report_only / none）。run 级"评分队列打满次数" = `GradingQueue.backpressure_count`。

## 10. 协作协议五段收尾

**① 待拍板 T0**：无新增；contracts/ 零改动。两项可选 T0 已登记为开放问题（§7-2 ignored 记录进契约；§7-6 S1 路径对齐 D2-3），均不阻塞。

**② T1 决策及理由**：§3 T1-1 ~ T1-9。请 owner 特别知悉 T1-1（容器移除以"本体已持久化"为前提、不再等 receipt——这是 D2-1 与 B5 在容器这一项上的取舍）与 T1-2（`verify_integrity` 取删除而非探针）。

**③ 临时挡板新增/命中/解除**：无新增；`bringup.py:705-713` fa_formal 挡板原样未触碰（`bringup.py` 整体未由本批触碰）。

**④ 推翻或修正了哪些旧结论**：
- F2-2b ③"评分后 `verify_integrity()` 复核指纹、漂移 → `snapshot_integrity_mismatch` 作废评分"——按 D2-1 删除（冻结产物持久化即唯一权威）。
- W1b 切片一复核必修 1 的五分流①②（verify_integrity False → missing / 异常 → `integrity_recheck_failed` fatal）——随之撤销；③④⑤ 保留。
- B5 ①"receipt 前 cleanup 不发生"——对 rollout 容器收窄为"本体持久化前不发生"（T1-1）；session drop / poison / 追加记录仍在 receipt 之后。
- B3/B4"测试文件或保留路径命中 = unsafe 永久拒绝、不运行 grader、绝不剥掉违规文件评剩余 patch"与 codex B4 P1-1 保险杠——按 D2-3 撤销：控制面改动不重放、照常评分；unsafe 只指结构不安全 artifact。
- B4 v1"projection 路径集必须等于 artifact 路径集"——推广为"等于按控制面规则独立重算的 candidate 集"。

**⑤ 测试/证据/账本状态**：§6；manifest 无需因本批改动；spike-log 由集成者落账。

**本轮没有改变哪些已定案语义**：`contracts/` 全部 schema（Outcome v2 豁免集与 `is_unsafe_artifact_rejection_shape`、`RUNTIME_QUIESCENCE_REASON_CODES`、`PatchHygieneResult`、`GradingTimingRecord`、`FinalizationReceiptV1`）；屏障序列①②（scope 终止、双读指纹、drain 前置）与 `QuiescenceRejected` 五码收口；exporter 无 git 纪律、`content_digest_race`、`unsupported_object_in_patch` 的 present + 永久拒绝 + receipt 内嵌证据；B5 receipt 原子持久化、追加不覆盖首因、receipt 失败 run-halt；`FinalizationStoreConflict` run-halt；B4 grader 的 exact-baseline 重建、HEAD 对账、prestate 对账、先 unlink 再写、baseline 软链祖先拒绝；W1b 三终态交付面与 admission 载荷、A2 全员合取；第七维版本事实语义（B-1）；security 维只判执行级事实（D2-2）；S1 diff 文本路径（`clean_patch` 剥离重放 + 封顶）与 s1_compat 交付形状；`bringup.py:705-713` 挡板；`reference/`、`rh2/src/slime`、lanes manifest 与 patch 表；W5a 关停链（cancelled 路径 receipt 先于容器清理不变）。
