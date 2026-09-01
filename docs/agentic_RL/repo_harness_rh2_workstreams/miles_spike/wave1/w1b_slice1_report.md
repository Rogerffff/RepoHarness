# W1b 第一集成切片实现报告：F6 prepared-artifact 真实消费链 + F4 attempt 绑定 + F5 termination 事实 producer

日期：2026-09-02。执行依据：06 计划 §5 第 3 条（Wave1 复核裁定的第一集成切片）+ `tmp/wave1检查.md`
F4/F5/F6 的"最小修复"；切片定义由 owner 裁定：**只做三件事的生产集成，不启用 admission/filter、
不写三终态判定、不实现 A5 disposition、不定 staleness 阈值**。本文同时充当本切片的
implementation-notes（miles_spike 目录下没有独立的 implementation-notes.md，沿用 wave1 报告为载体）。

## 0. 交付物清单

| 文件 | 性质 | 内容 |
|---|---|---|
| `rh2/src/repoharness2/envpack/prepared_tasks.py` | 新增（envpack） | prepared artifact 的 schema（`PromptRowMetadata` / `PreparedTaskRecord` / `PreparedTasksManifest`）、host 侧一次性写入 `prepare_tasks`、actor 侧三个只读复核口 `load_prepared_manifest` / `load_prepared_rollout_views` / `load_host_grading_views`、`verify_prompt_data_binding`、保留键边界 `assert_no_reserved_keys` |
| `rh2/src/repoharness2/envpack/trusted_prep.py` | 新增（envpack） | 一次性 trusted-prep 进程入口 `python -m repoharness2.envpack.trusted_prep --repo-root … --out-dir … --private-dir …`（唯一调用 `TrustedTaskController.from_repo_root` 的生产位置，跑完即退出） |
| `rh2/src/repoharness2/envpack/termination_facts.py` | 修改（envpack） | 新增 `TerminationFactsPayloadV1`（交付面载荷）、`termination_facts_payload(receipt)`（producer 唯一入口）、`stamp_termination_facts` / `resolve_termination_facts` / `assert_payload_dereferences`（producer/consumer 边界）；W2a 的 `derive_termination_facts` 只读派生原样保留 |
| `rh2/src/repoharness2/adapters/miles/attempt_assignment.py` | 新增（adapters/miles，零 miles/slime import） | `AttemptAssignment`（typed 分派载荷）、`AttemptAssignmentRegistry`（有界进程内映射）、`assignment_from_dispatch`、`stamp_assignment_on_outputs` |
| `rh2/src/repoharness2/adapters/slime/prepared_task_face.py` | 新增（adapters/slime） | `PreparedTaskFace`（actor 内任务面：公开 `RolloutTaskSpec` 表 + host 侧 `HostGradingView` 表）、`build_grading_spec_from_host_view`（actor 内从 v2 safe view 构造评分 spec/parser）、`render_v2_eval_script`、`rollout_spec_from_view` |
| `rh2/src/repoharness2/adapters/slime/generate.py` | 修改 | `RolloutTaskSpec.grading_spec` 改为可选（:1773）；`RolloutOrchestrator(grading_spec_resolver=…)`（:2209）+ `_grading_spec_for`（:2314）；`generate()` 拆为 wrapper（:2286，交付面盖章）+ `_generate_attempt`；通用异常路径的 P1-1 处理（:3260 前后）；finally 段 receipt 持久化后派生事实（:3339 前后）与派生失败 run-halt（:3486）；`RolloutAudit.termination_facts_payload` |
| `rh2/src/repoharness2/adapters/slime/bringup.py` | 修改 | 三个启动旋钮（:180 起）+ 纯函数 `select_task_face_mode`（:185）；`__init__` 任务面二选一（prepared / legacy v1，在 adapter 线程启动之前）；`_resolve_task` prepared 分支、新 `_resolve_grading_spec`（:1242）；orchestrator 注入 `grading_spec_resolver`；`ensure_fa_started` 挂 `args.rh2_attempt_assignments`（:1454） |
| `rh2/src/repoharness2/adapters/miles/generate_fn.py` | 修改 | 铸造身份后 `registry.bind`（:127）→ 生产链 → 身份盖章后 `_verify_termination_facts_binding`（:161）+ `stamp_assignment_on_outputs`（:165）→ finally `registry.release`（:169） |
| `rh2/tests/test_w1b_prepared_tasks.py`（14 例）、`rh2/tests/adapters/test_w1b_termination_facts_producer.py`（7 例）、`rh2/tests/adapters_miles/test_w1b_prepared_chain.py`（7 例）、`rh2/tests/w1b_synthetic_tasks.py`（共用夹具，非测试模块） | 新增 | 见 §6 |

**未触碰**：`bringup.py:705-715` 的 fa_formal 临时挡板（原样，且本切片的任务面选择放在挡板之后、adapter 线程之前）；
`contracts/`（零改动）；eligibility 契约语义；`reference/`；既有测试 oracle（零改动，全部既有测试原样通过）；
`adapters/miles/identity.py`（W1a 铸造规则原样）；`envpack/training_view.py`（W2a controller/视图原样）；
`ingest_swegym_lite.py`；`registry.py`；lanes manifest（按要求由集成者更新，见 §6）。无 git commit / stash。

## 1. 三阶段落地形态（代码事实）

### 1.1 F6：prepared artifact 真实消费链

```text
host 进程（一次性，create_rollout_manager 之前；trusted_prep.main → 退出）
  TrustedTaskController.from_repo_root（完整 loader + 四面关系检查，仅此处）
    ├─ 公开目录 <prepared_dir>/            0644
    │    prompts.jsonl                 miles --prompt-data 直接消费：{"prompt": render_user_prompt(public),
    │                                  "label": task_id, "metadata": {task_id, source, instance_id,
    │                                  environment_package_digest, public_bundle_digest}}
    │    rollout_task_views.jsonl      RolloutTaskView 行（public bundle 全量 + 身份 + 两个 digest）
    │    prepared_manifest.json        逐任务记录（同 metadata 五键）+ 两个公开文件 sha256 + 私有产物期望 sha256
    └─ 私有目录 <private_dir>/           0700
         host_grading_views.jsonl      0600；HostGradingView 行（PrivateGradingBundleV2，无 golden 字段）

RolloutManager actor 进程（BringupService.__init__，fa_audit_only / fa_formal + RH2_PREPARED_TASKS_DIR）
  PreparedTaskFace.load(prepared_dir, host_grading_path, host_grading_sha256, prompt_data_path=args.prompt_data)
    ├─ 三个读取口全部复核：文件 sha256 ↔ manifest；视图行 revalidated() 后逐字段对 manifest 记录；
    │  prompt 文本 == render_user_prompt(public)；metadata 五键 == 记录；无 rh2_ 保留键；
    │  私有文件：启动参数交回的期望 sha256 == manifest 期望 == 实际内容，POSIX 权限位 group/other 为 0；
    │  args.prompt_data 按内容 digest 绑定到 prep 的 prompts.jsonl
    ├─ RolloutTaskSpec 表（grading_spec=None：rollout 侧只带 public 面 + digest 锚）
    └─ HostGradingView 表（host 侧，同进程持有）→ 评分时刻按 attempt 绑定 revalidated() 后
       build_grading_spec_from_host_view：parser 闭包捕获 PrivateGradingBundleV2，eval 脚本由 eval_cmd + test_patch 渲染
```

- **actor 不调完整 loader**：读取口只解析 JSONL 行为 `RolloutTaskView` / `HostGradingView`；进程内不存在
  `ValidationOnlyBundle`、v1 `PrivateGradingBundle`、golden 内容（测试以对象图遍历 + 完整 loader/controller
  构造/v1 `load_bundle_pairs` 全部 monkeypatch 成 raise 证明）。
- **formal 不回退 v1**：`select_task_face_mode("fa_formal", None)` 直接 RuntimeError（"不得静默回退 v1 BundlePair"）；
  prepared 目录在场时 s1_compat 也拒绝（attempt 绑定依赖六字段身份）。fa_formal 既有挡板在前，未动。

### 1.2 F4：attempt → host 原始分派的 authoritative join

- `Rh2MilesGenerateFn.__call__`：铸造六字段之后、进入 `rh2_custom_generate` 之前，
  `assignment_from_dispatch(sample.metadata, minted)` 组装 `AttemptAssignment`（六字段身份 + 分派三元组
  `task_id / environment_package_digest / public_bundle_digest`），`registry.bind(assignment)`：bind 时用
  `PreparedTaskFace.verify_dispatch` 对 prep manifest 核对三元组（不是回显自洽就算）；attempt 结束（含异常）
  `finally: registry.release(attempt_id)`。
- 编排层 `task_resolver` 与 `grading_spec_resolver`（bringup 的 `_resolve_task` / `_resolve_grading_spec`）
  只按样本自带的 `rh2_physical_attempt_id` 取绑定；样本回显的身份/分派键逐字与绑定比对，不一致即拒。
- 有界：容量 4096（触顶即拒，不静默增长）；无 durable ledger，无扫盘。

### 1.3 F5：termination 事实 producer

- `_generate_attempt` finally 段：receipt 持久化成功后，若 attempt 形成了 Outcome v2 →
  `audit.termination_facts_payload = termination_facts_payload(receipt)`（内部 `derive_termination_facts`，fail-closed）；
  无 Outcome（s1 兼容 / 身份不全的结构化拒绝）→ `termination_facts_skipped_no_outcome`，不伪造。
- `generate()` wrapper：返回前 `stamp_termination_facts(delivered, payload)` 盖到交付面全部叶
  （成功叶链或 abort 形状）；键 `rh2_termination_facts`。
- miles 侧：`Rh2MilesGenerateFn` 在六字段盖章之后 `_verify_termination_facts_binding`——载荷必须能按叶自身
  attempt/execution join 回来（`resolve_termination_facts`）。

## 2. T1 决策及理由

1. **prepared artifact 形态 = 两目录三公开文件 + 一私有文件，manifest 只记 digest**（§1.1）。公开产物全部是模型侧可见面：
   写入前逐行 forbidden marker 扫描；私有产物只以 opaque 路径 + 期望 sha256 被引用（`RH2_HOST_GRADING_ARTIFACT_PATH`
   / `RH2_HOST_GRADING_ARTIFACT_SHA256`），期望值同时写在 manifest 里，加载时三方比对（参数交回值 == manifest == 实际）。
   权限：私有目录 0700 / 文件 0600（`os.open(O_EXCL, 0o600)` 创建，不经历宽权限窗口；读取口检查 group/other 位）。
   产物**一次性**：目标文件已存在即拒绝覆盖（避免半旧半新被 actor 读到）。
2. **不写自定义 miles DataSource；用内容 digest 把 `args.prompt_data` 绑定到 prep 的 prompts.jsonl。** stock
   `RolloutDataSource` 原样消费 prompts.jsonl（真实 `Dataset` + `get_samples` 在测试里跑过），bringup 加载任务面时按
   `args.prompt_data` 的 sha256 与 manifest 对账——比再写一个 `--data-source-path` 类少一个集成面，效果等价。
3. **prepared 链要求 execution_mode ≠ s1_compat**。F4 绑定以 attempt id 为键，s1_compat 不铸造身份，无键可用；
   `select_task_face_mode` 对"prepared + s1_compat"拒绝启动（不是静默走 legacy）。
4. **`RolloutTaskSpec.grading_spec` 改为可选而不是删除。** prepared 链构造 `grading_spec=None`（rollout 侧对象只带
   public 面 + digest 锚，W2a T1 落地）；v1 八题 bring-up（`rollout_task_from_bundle_pair`）与既有测试夹具继续内嵌，
   零 oracle 改动。评分材料统一经 `_grading_spec_for`：有 resolver 走 attempt 绑定（prepared），否则用内嵌，两者皆无 =
   Fatal `grading_spec_unavailable`。**残余**：库层 fa_formal 配内嵌 spec 且无 resolver 仍可运行（测试夹具形态）——
   "formal 不可达 v1"在**生产入口 bringup** 强制，不在库层强制（强制会改 W1a 等既有 fa_formal 夹具）。
5. **join 载体 = frozen dataclass `AttemptAssignment` + 进程内 `AttemptAssignmentRegistry`，挂 `args.rh2_attempt_assignments`。**
   放 adapters/miles（attempt 身份只在 miles 路径铸造），bringup 惰性 import；orchestrator 只收两个 callable，
   不认识 registry 类型。评分时刻 join 失败（`AttemptAssignmentError` / `GradingMaterialsError` / revalidated 失败）
   在 `_grading_spec_for` 统一包成 `FatalExecutionInfrastructureError("grading_materials_join_failed")`——
   与 B4 `BaselineIntegrityError` 同通道 run-halt（本 actor 自己的绑定表与正在处理的样本对不上 = 系统性矛盾，
   不许伪装成 failed_to_grade 当成员损耗）。task 解析时刻的绑定失败发生在 audit 创建之前，`AttemptAssignmentError`
   直接向上传播（与 legacy resolver 未知 instance_id 的 ValueError 同位，不进 abort 形状）。
6. **v2 评分 spec 在 actor 内构造；eval 脚本按 swebench `make_eval_script_list_py` 尾段形态渲染。**
   `PrivateGradingBundleV2` 只有 vendor `eval_cmd`（无官方 eval_script 全文），`GradingEnvSpec.eval_script` 是必填字符串，
   本切片渲染：reset 测试文件 → heredoc apply test_patch → `>>>>> Start Test Output` → `eval_cmd + 测试文件` →
   `>>>>> End Test Output` → reset（标记与 swebench 常量逐字对拍有测试）；渲染前 `verify_grading_eval_cmd` 互检。
   parser = `scoring.parse_eval_log(view.grading, log)`（duck-typed，闭包只捕获 v2 评分面）。**该脚本在真实镜像上的
   正确性（含 SWE-Gym 各仓库测试选择器与 vendor parser 覆盖）归 T2-d/W3a**（见 §4 开放问题 1）。
7. **F5 载荷 = `TerminationFactsPayloadV1`（envpack/termination_facts.py），键 `rh2_termination_facts`，只在有 Outcome v2 时派生。**
   字段表见 §3。派生失败 = receipt 与 outcome 账实矛盾：receipt 已 durable 后 run-halt
   （`termination_facts_underivable`，与 receipt 写失败同纪律：异常在途时只记 secondary fact，不覆盖首因）；
   盖章冲突（叶与本次 receipt 的 attempt/execution 对不上）同样 run-halt（`termination_facts_stamp_conflict`）。
   这两条是 producer 完整性 fail-closed，**不是**样本处置——它们停机而不是剔除样本，不产生样本偏置。
8. **通用异常路径的 P1-1 处理（登记边界的判定结论，见 §3.2）**：step8 之后、成功 Outcome 产出之前的异常，先撤销
   `runtime_quiescence_confirmed` 并清 `audit.finalized`，再走既有异常收口；Outcome 已产出（CAS）时不动。
9. **分派三元组也盖回输出叶**（`stamp_assignment_on_outputs`）：vendor 叶链 metadata 由 `to_sample` 重建，
   `task_id/environment_package_digest/public_bundle_digest` 不会自动传播；第二段 filter 的环境身份 join 要在
   交付样本上读到它。叶上已带不同值即拒。
10. **prepared 链的 `RolloutTaskSpec.task_id` = source-qualified id**（`swe_gym_lite::<instance_id>`），贯穿 audit /
    GradingReport / receipt（契约 `task_id` 均为 NonEmptyStr，`SafeIdentifier` 也允许 `:`）。prompt metadata 仍带
    `instance_id`（人读/record_event），但**不是** join 键（join 只认 task_id + 两个 digest）——避免 `_abort_result`
    把 `metadata["instance_id"]` 覆写成 task_id 后 retry 被误拒。

## 3. F5 载荷字段表与登记边界判定

### 3.1 `TerminationFactsPayloadV1`（schema_id `rh2.termination_facts_payload.v1`，`extra=forbid`，导入期断言字段名不含 disposition/admission/reward/mask/train/penal/sample/keep/drop 词根）

| 字段 | 来源（全部派生自 FinalizationReceiptV1 + 内嵌 RolloutAttemptOutcomeV2） | 用途 |
|---|---|---|
| `physical_attempt_id` | receipt.physical_attempt_id（== outcome.identity.physical_attempt_id，派生层已核） | 主键 |
| `rollout_execution_id` | receipt.trajectory_id | join：与样本 `rh2_rollout_execution_id` 比对 |
| `task_id` | receipt.task_id | join 锚 |
| `receipt_id` / `outcome_id` | receipt.receipt_id / outcome.outcome_id | 唯一解引用锚（`assert_payload_dereferences`） |
| `termination_kind` | outcome.termination_kind（契约五族封闭枚举） | 事实 |
| `triggered_by_policy_horizon` / `triggered_by_hard_wall` | 五族划分派生；validator 钉死与 kind 一致（矛盾不可表示） | 事实 |
| `execution_scope_quiescent` | receipt.runtime_quiescence_confirmed | 闭合事实 |
| `canonical_frozen_patch_formed` | receipt.frozen_patch_digest is not None | 闭合事实 |
| `fresh_grading_complete` | receipt.grading_report_id is not None（validator 钉死一致） | 闭合事实 |
| `grading_report_id` / `eligibility_report_id` | receipt 引用（派生层已核 receipt↔outcome 的 eligibility 引用逐字对称） | 第二段 authoritative join 的引用 |

刻意不含：任何 disposition/admission/reward/mask 字段；`capture_closed`（owner = eligibility 事实层）；时长（归 monotonic timeline）；
`environment_package_digest`（交付样本上由分派三元组携带，不在载荷里复制）。

### 3.2 登记边界："通用异常路径若在 audit.finalized 已设之后触发"

**判定：真实可达。** step8（`audit.finalized = finalized`）之后、成功路径 `_produce_outcome_v2` 之前，fa_formal 会调
`grading_workspace.verify_integrity()`——`FrozenWorkspace.verify_integrity` 走 `RolloutContainerWorkspace.run_bash` →
`docker exec` 子进程通道（`grading/manager.py:run_docker` 用 `asyncio.create_subprocess_exec`，通道层异常如
OSError/FileNotFoundError 会原样抛出，不是 ExecResult）。异常进入通用 `except Exception`：此前 receipt 会带 finalized 的
grading/eligibility 引用而 Outcome 的 eligibility 引用为 None → `derive_termination_facts` fail-closed。**同一路径还有一个
更早的既有问题**：stage=finalize 的回退映射是 `("completed", "capture_incomplete")`，而此时 quiescence 与 capture 都已确认，
`derive_completion` 推出 present_complete，与 execution-fact 类 failure_category 在 Outcome v2 契约上不可表示——
`build_outcome_v2` 的 ValidationError 会从 except 块裸逃，`generate()` 不再返回 abort 形状。

**处理（按 P1-1 先例 :3057 整体套用）**：在 `except Exception` 里，若 `audit.finalized is not None and audit.outcome_v2 is None`：
`audit.runtime_quiescence_confirmed = False`（评分后完整性复核未完成，冻结副本未被证实）+ `audit.finalized = None`
（missing 收口不得与 finalized 引用并存）+ `audit.mark("finalized_refs_cleared_on_exception")`。之后既有收口产出 missing
Outcome（eligibility None），receipt 引用同为 None，事实可派生，abort 形状照常返回。Outcome 已产出（CAS，deliver 阶段失败）
时不动——引用两侧同源，派生通过。测试：
`test_exception_after_finalize_is_reachable_and_handled_per_p1_1`（verify_integrity 抛 OSError：断言 step8 已过、
finalized 清空、receipt/outcome 引用皆 None、completion=missing、事实派生通过、abort 样本带本 attempt 载荷、cleanup 完成）；
`test_deliver_failure_after_outcome_keeps_symmetric_refs`（repair sink 抛错：不清引用、两侧同源、载荷 fresh_grading_complete=True）。

## 4. 开放问题 / 第二段接缝清单

1. **v2 eval 脚本与 parser 覆盖（T2-d/W3a）**：本切片只保证构造接缝与对象图属性；`render_v2_eval_script` 的测试选择器
   = test_patch 触碰路径（swebench 通用规则，django/sympy 类仓库有专门规则），parser 走官方 `MAP_REPO_TO_PARSER`
   （对 SWE-Gym 11 仓库覆盖为 0，需 vendor parser）。真实镜像上跑 216 题之前，T2-d 须替换/验证这两处；否则评分只会得到
   `failed_to_grade`（fail-closed，但白烧 grader）。
2. **第二段复合 filter 的取数**：交付样本 metadata 现在同时携带六字段身份、分派三元组、`rh2_termination_facts`、
   `eligibility_report_ref`/`training_eligibility_class`。filter 的 authoritative join 原语已就位
   （`resolve_termination_facts` + `assert_payload_dereferences` + `registry.resolve_for_sample`）；EligibilityReport 的
   facts digest 目前只在 sidecar（`artifact_dir/<trajectory>/eligibility_report.json`），紧凑 metadata 载体还是有界映射由第二段 T1 决定。
3. **deliver 阶段失败后的语义空隙**（既有行为，本切片未改）：Outcome 已产出为 present_complete + eligibility 引用，随后
   `_deliver`（repair sink / artifact 落盘）失败 → 样本 abort 形状，但 receipt.outcome_v2 与事实载荷都说"评分完整"。
   第二段必须以 `remove_sample`/abort 形状为准（A6：任一 remove_sample → 整组拒绝），不能只看事实载荷。建议第二段把
   "deliver 阶段 failure_record 在场"作为显式 reason。
4. **`identity.py` 的 PENDING 污染规则仍只查六键**：`rh2_termination_facts` 等其它 `rh2_*` 键由 prep 边界
   （`assert_no_reserved_keys`）与 actor 读取口拦截；自定义数据源直接注入仍可绕过铸造点。扩到 `rh2_` 前缀会触碰 W1a
   模块与其 oracle，留第二段作 T1。
5. **launch 接线（W7）**：`experiments/miles_gpu_spike/launch.sh` 仍走 s1_compat + v1 八题 prompt 数据，本切片未改它；
   接线配方见 `trusted_prep.py` 模块 docstring（先跑 trusted-prep → `--prompt-data <prepared>/prompts.jsonl` +
   三个 `RH2_*` 旋钮）。
6. **registry.py 未注册新 schema**（`rh2.prepared_tasks_manifest.v1` / `rh2.termination_facts_payload.v1`；W2a 的三个也未注册）：
   `registry.py` 不在本切片所有权，建议随下一批 adapters 集成同轮提交；注册时 `host_grading_view` 与 prepared manifest
   不需豁免（manifest 无内容字段），`rollout_task_view` 不豁免 marker 扫描。
7. **`_abort_result` / eval 分支把 `metadata["instance_id"]` 覆写为 source-qualified task_id**（既有代码，prepared 链下值形态变了）：
   只影响 `record_event` 的人读字段，不影响 join（join 不用 instance_id）。是否改名归第二段。
8. **B 包连带**（未变）：unused handler 选 retry 时 sidecar/audit 按 trajectory 固定文件名覆盖写的问题仍在（Wave1 复核 F2）。
9. **lanes manifest**（集成者更新）：见 §6 精确计数。

**T0 升级项：无。** 未改 `contracts/`（新增的 typed payload 都在 envpack/adapters 内）、未改训练样本准入/reward/loss、
未新增剔除样本的拒绝路径（新增的两条 run-halt 是 producer 完整性 fail-closed，停机不剔除）、未引入依赖/服务
（trusted-prep 是一次性进程）。

## 5. 协作协议五段收尾

**① 待拍板 T0**：无（见 §4 末）。

**② T1 决策及理由**：§2 第 1~10 条。

**③ 临时挡板新增/命中/解除**：无新增临时挡板；`bringup.py:705-715` fa_formal 挡板原样保留（源码顺序测试钉死其先于任务面选择）。
新增的都是永久 fail-closed 边界（保留键、digest/权限、manifest 核对、attempt 绑定、事实派生），不是待解除的挡板。

**④ 推翻或修正了哪些旧结论**：
- W2a 报告"开放问题 1/3"（adapters 换消费链）与 Wave1 复核 F6 判定：runtime closure 已接通，`TrustedTaskController`
  现在有生产消费者（`trusted_prep` 一次性进程）；actor 侧不再构造 controller。
- 通用异常路径在 step8 之后的收口被证实存在两个缺口（引用不对称 + Outcome 不可表示的 ValidationError 裸逃），按 P1-1 修正（§3.2）。
- `build_swe_grading_spec` 捕获 v1 golden 的构造方式在 prepared 链被 `build_grading_spec_from_host_view` 取代；v1 形态只剩八题 bring-up。

**⑤ 测试/证据/账本状态**：§6。

**本轮没有改变哪些已定案语义**：eligibility 契约与七维语义；三终态/组准入（未实现）；A5 disposition（未实现，载荷无处置字段）；
staleness 阈值/接口（未触碰 `staleness_threshold`）；W1a 六字段铸造规则与 W2a 视图/controller/关系检查；fa_formal 挡板；
v1 八题 bring-up 路径与 s1_compat 行为（s1 零改变有测试）；`contracts/`、`reference/`、`registry.py` 零改动。

## 6. 测试证据（2026-09-02 实跑）

新增 28 例全绿：

```
cd rh2
uv run pytest tests/test_w1b_prepared_tasks.py -q                              # 14 passed in 2.28s
uv run pytest tests/adapters/test_w1b_termination_facts_producer.py -q         # 7 passed in 0.14s
uv run pytest tests/adapters_miles/test_w1b_prepared_chain.py -q               # 7 passed in 3.59s（bringup 用例本机有 Qwen3-8B tokenizer 缓存，真实构造未 skip）
```

回归：

```
uv run pytest tests/ -q                                                        # 1422 passed, 232 skipped, 3 warnings in 28.49s
RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/ -q
                                                                               # 502 passed, 17 warnings in 18.69s
bash scripts/miles_integration_lanes.sh
  前置校验（integration tree a4b60c89…/工作树干净/patch digest 8 个/pin f2b7c792…）全部通过
  lane A: 285 passed, 217 skipped  → FAIL: 计数偏离 manifest expected=278p/185s（脚本在 lane A 停止；lane B 用同命令手跑 = 502 passed, 0 skipped）
uv run ruff check <全部改动的 8 个 src 文件 + 4 个测试文件>                    # All checks passed!
```

**两条 lane 的精确新计数（供集成者更新 manifest）**：lane A = **285 passed / 217 skipped**；lane B = **502 passed / 0 skipped**。
构成：本切片 `test_w1b_prepared_chain.py` 双 lane 各 **+7 passed**（不标 integration_base）；同期已提交的 W9
（commit b4986f68，`test_w1b` 之外的 `test_w9_cp_faithful_dis.py` 32 例整模块 integration_base）贡献 lane A +32 skipped、
lane B +32 passed。相对 manifest（278/185、463/0）：A = 278+7 / 185+32，B = 463+7+32 / 0。

### F6 验收清单 ↔ 测试

| 验收项 | 测试（文件::用例） | 断言方式 |
|---|---|---|
| prepared prompt → DataSource → Sample.metadata → GenerateFn → resolver → sandbox public payload 真实形状 | `test_w1b_prepared_chain.py::test_w1b_prepared_chain_real_shape_prompt_to_sandbox_and_delivery` | 真实 miles `Dataset` + `RolloutDataSource.get_samples` 读 prep 的 prompts.jsonl（组/index 算术断言）；`Sample.metadata` == manifest 记录五键；`Rh2MilesGenerateFn` → 真实 fa_formal orchestrator（resolver 形状 = bringup 的两个方法）；`docker.writes["/rh2/public_task_bundle.json"]` == public bundle JSON；harness prompt == `render_user_prompt(public)` == prompts.jsonl 的 prompt |
| bringup 自身的 resolver 真实装配 | `test_w1b_prepared_chain.py::test_w1b_bringup_builds_prepared_face_without_v1_loader` | 真实 `BringupService.__init__`（fa_audit_only + 三旋钮）：`prepared_face` 在场、`pairs is None`、任务面 = prepared 两题且 `grading_spec is None`；`_resolve_task` 未绑定即拒、绑定后解析；`_resolve_grading_spec` 产出含 test_patch 的 spec |
| actor 未调 full loader | 同上两例 + `test_w1b_prepared_chain_never_calls_full_loader_and_graph_has_no_golden` + `test_w1b_prepared_tasks.py::test_trusted_prep_cli_real_assets_then_actor_loads_without_full_loader` | `ingest_swegym_lite.load_trusted_ingest_outputs` / `load_ingest_outputs` / `training_view.load_trusted_ingest_outputs` / `TrustedTaskController._build` / `from_repo_root` / `bundles.load_bundle_pairs` 全部 monkeypatch 为 raise AssertionError 后，加载与整条链照常成功（真实 216 题 CLI 产物同样通过） |
| 对象图无 golden | `..._graph_has_no_golden`、`test_w1b_prepared_tasks.py::test_v2_grading_spec_built_in_actor_from_safe_view_without_golden`、`test_synthetic_controller_still_holds_no_golden` | 从 face / registry / orchestrator / spec / args / 交付样本遍历对象图：无 `ValidationOnlyBundle`、无 v1 `PrivateGradingBundle`、任何字符串不含 golden 内容 |
| private 不进四个面 | `..._real_shape_prompt_to_sandbox_and_delivery`（adapter 请求：`session_defaults`；模型输入：harness prompt；sandbox payload：docker writes；`Sample.metadata`：交付样本 JSON 无 test_patch/golden 内容且 marker 零命中；args：`repr(vars(args))` 无私有内容）+ `test_prepare_artifacts_shape_permissions_and_no_private_leak`（公共 evidence：三公开文件 marker 零命中、无 test_patch/golden/eval_cmd/version） | 逐字内容扫描 + `scan_for_forbidden_markers` |
| v2 spec 在 actor 内构造 | `..._real_shape…`、`test_v2_grading_spec_built_in_actor_from_safe_view_without_golden` | `spec.parse_log.__closure__` 单元包含 `PrivateGradingBundleV2` 且不含 v1/validation 面；eval 脚本含 test_patch、标记与 swebench 常量逐字一致；hygiene.test_files 来自 test_patch |
| mismatch fail-closed | `test_w1b_dispatch_pair_swap_and_missing_keys_rejected_at_bind`、`test_w1b_registry_join_negatives`、`test_reader_rejects_public_tampering`、`test_reader_rejects_reserved_keys_even_when_digest_consistent`、`test_reader_rejects_manifest_record_mismatch`、`test_host_grading_reader_fail_closed`、`test_verify_prompt_data_binding_rejects_other_file`、`test_v2_grading_spec…`（digest 错配 join 拒） | 见 §7 F4 反例清单 + 读取口九类篡改 |
| formal 不可达 v1 | `test_w1b_select_task_face_mode_matrix`、`test_w1b_bringup_builds_prepared_face_without_v1_loader`（源码顺序：fa_formal 挡板文本先于 `select_task_face_mode`） | fa_formal + 无 prepared → RuntimeError "不得静默回退 v1"；s1_compat + prepared → 拒；prepared 链 `load_bundle_pairs` 被封死仍可构造 |

## 7. F4 join 反例清单（全部拒绝，`test_w1b_registry_join_negatives` / `test_w1b_dispatch_pair_swap_and_missing_keys_rejected_at_bind` / `test_v2_grading_spec…`）

| 反例 | 拒绝点 / reason_code |
|---|---|
| 合法 package A 的 task_id + 合法 package B 的 environment digest（成对替换，两方向） | bind：`dispatch_not_authoritative`（manifest 核对）；生产链未进入（`audits == []`），registry 无残留 |
| legacy 形状样本（只有 instance_id）进 prepared 链 | `dispatch_metadata_missing` |
| 旧 retry attempt（release 后的 id）解析/评分材料查找 | `attempt_not_bound` |
| 并发同题错接：携带 X 的 attempt id、回显 Y 的 execution/slot | `assignment_echo_mismatch` |
| 回显别的 (task_id, digest) 二元组 | `assignment_echo_mismatch` |
| 同一 attempt 二次派发 | `attempt_already_bound` |
| 样本无 attempt id | `attempt_id_missing` |
| 在飞绑定数触顶 | `registry_capacity_exceeded` |
| 评分材料查找交回错 environment digest / unknown task | `GradingMaterialsError(grading_dispatch_not_authoritative)` |
| 正例 | 正确绑定的 attempt 解析出 host 分派任务；attempt 结束 registry 归零 |

F5 五类 join 反例（`test_termination_facts_join_negatives_five_classes_and_unique_dereference`）：同题 n=8 sibling 的事实、
同 member 旧 retry attempt 的事实、fan-out 叶各自携带别的 attempt 的事实、错 attempt、错 trajectory——全部拒绝；
`assert_payload_dereferences` 对别的 attempt 的 receipt 拒绝（唯一解引用）；合法覆盖只在"同一样本对象 reset_for_retry 后
新 attempt 盖章"这一形态（`test_w1b_retry_replaces_stale_termination_facts_on_passthrough_sample` 在真实 miles
`reset_for_retry` 路径上验证）。

---

## 8. 追加修正节（2026-09-02，codex 聚焦复核后；append-only，本节口径覆盖上文冲突处）

### 8.0 T0 口径修正（引用 06 计划 A9）

上文 §4 末与 §5 ① 的"T0 升级项：无"**不成立**。owner 2026-09-02 事后拍板 **A9**：RolloutManager 被定义为
**可信 host control-plane 进程**，可以加载并长期持有剥离后的 `HostGradingView`（含 `PrivateGradingBundleV2`：
test_patch/F2P/P2P/eval_cmd），并在 actor 内构造 grading spec/parser；模型执行始终在隔离 sandbox；private 内容
不得进入 prompt、mount、`Sample`、adapter response、公共 evidence、export；**本项目不承诺 RolloutManager 进程自身
被攻破后的内存隔离**。切片一的"同一可信 actor 内共址"与 D0-3 原文"private 仅进入 host grader"是不同的所有权边界，
属事后批准的 T0（不需要改架构；本节所有注释/口径按 A9 写）。

### 8.1 必修 1：post-finalize 失败域五分流（取代上文 §2 第 8 条与 §3.2 的"P1-1 处理"）

**被否决并已删除的行为**：切片一初版在通用 `except` 里对 `audit.finalized is not None and audit.outcome_v2 is None`
撤销 quiescence + 清 finalized，再由 producer 第二次产出 missing Outcome 返回 ABORTED（producer 调用 2 次、
`remove_sample=True`、receipt aborted、completion=missing、reason_code=unmapped_failure_code）——把 Outcome
schema/producer bug、docker 完整性检查异常、核心 sidecar 磁盘失败洗成普通缺员，miles 丢弃并补采，掩盖系统性故障。

**新分流**（`rh2/src/repoharness2/adapters/slime/generate.py`）：

| 失败域 | 处置 | reason_code / 标记 | 测试（tests/adapters/test_w1b_termination_facts_producer.py） |
|---|---|---|---|
| ① `verify_integrity()` 返回 False | 明确的完整性不匹配：既有 P1-1 路径（撤销静止事实、清 finalized）→ missing / ABORTED；producer 恰一次 | `snapshot_integrity_mismatch` | `test_split_1_verify_integrity_false_is_missing_abort_producer_once` |
| ② `verify_integrity()` 抛未知异常 | run-fatal（P0-1 独立通道），不撤销 finalized、不产 Outcome、不返回 ABORTED | `integrity_recheck_failed` | `test_split_2_verify_integrity_exception_is_run_fatal` |
| ③ Outcome producer / 契约异常 | run-fatal；producer **只允许调用一次**（二次调用本身 run-fatal） | `outcome_producer_failed` / `outcome_producer_called_twice` | `test_split_3_outcome_producer_exception_is_run_fatal_and_called_once`（断言恰一次）、`test_split_3b_producer_second_call_itself_is_run_fatal` |
| ④ 核心 admission sidecar 写失败（`_write_artifacts`：eligibility_report / grading_report / trajectory_projection / group_repair_signal / capture_records / tapes） | run-fatal（A4：样本不交付 + run-fatal，finally 的 cleanup 仍执行） | `admission_artifact_write_failed` | `test_split_4_core_admission_sidecar_write_failure_is_run_fatal_cleanup_still_runs`（真实文件系统失败：artifact_dir 位置被普通文件占住；断言 cleanup_completed、lease_released） |
| ⑤ finalize 之前的 task-local 故障 | 仍是普通 ABORTED（missing Outcome，miles 补采） | 既有映射（如 `harness_crash`） | `test_split_5_pre_finalize_task_local_failure_stays_aborted` |
| 可选 telemetry：`repair_signal_sink` 写失败 | 记录 failure_record 后**照常交付**，不改写样本处置；`audit.repair_signal_forwarded=False` | `repair_signal_sink_failed` | `test_telemetry_repair_signal_sink_failure_records_and_still_delivers` |
| 通用 except 里发现 `audit.finalized is not None`（未分类 post-finalize 异常） | 不该到达的状态：升 fatal，**不**撤销 finalized、不二次产出 | `post_finalize_failure_unclassified` | `test_post_finalize_unclassified_exception_is_run_fatal_not_laundered` |

实现要点：
- `_produce_outcome_v2` 改为**守卫入口**（once-only → `outcome_producer_called_twice`；构造异常 → `outcome_producer_failed`，
  failure_record stage=`outcome_producer`），原实现改名 `_produce_outcome_v2_unguarded`；P0-2 的静默 compare-and-set **删除**。
- 新增 `_notify_fatal_halt`：联合终核 P1-1 的 task-local halt 通知在 except 子句内抛出的 Fatal 上同样生效（外层 Fatal 分支不会二次分派）。
- 顺手加固：mismatch 分支的 `snapshot:` 证据引用先于 audit 改写取得——取值失败时 finalized 仍在场，按未分类 post-finalize 故障升 fatal。
- receipt disposition：in-flight Fatal → `fatal_run_halt`（`build_finalization_receipt` 既有逻辑）；②③④与未分类四个 fatal 测试各自断言
  `attempt_disposition == "fatal_run_halt"` 与 `terminal_reason_code`。
- **分类判断（T1）**：`_write_artifacts` 六类 sidecar = 核心 admission 记录及其引用 → fatal；`repair_signal_sink` = 可选 telemetry
  （miles 路径无生产消费者——组准入由第二段 filter 按交付面 typed 载荷判定，FA-2 assembler 按 06 §2 不做）。owner 若认为组修复
  信号转发应视为核心，改 `_deliver` 一处分类即可（登记为可翻转项）。

**oracle 改动（T1 登记）**：
1. 上文 §6 的 `test_exception_after_finalize_is_reachable_and_handled_per_p1_1` / `test_deliver_failure_after_outcome_keeps_symmetric_refs`
   **已删除**（编码的是被否决行为），由上表七个测试取代；
2. `tests/adapters/test_f2_2_capability.py::test_outcome_terminal_cas_single_write` 的 oracle 从"第二次产出静默不改写"改为
   "第二次调用 run-fatal `outcome_producer_called_twice`，首次 Outcome 不变"（docstring 注明修订来源）。

§3.2 的判定结论修正：可达性结论不变（verify_integrity 走 docker 通道可抛异常），处置改为 run-fatal；P1-1 只保留给
"verify_integrity 返回 False"这一明确的完整性不匹配。

### 8.2 顺手修 2：公开 manifest 的外部 sha256（输入身份，不是授权闸门）

- trusted-prep stdout 增 `prepared_manifest_sha256`（`prepared_tasks.manifest_file_sha256(prepared_dir)`）；启动方经环境变量
  **`RH2_PREPARED_TASKS_MANIFEST_SHA256`** 传给 actor；bringup 读为 `PREPARED_TASKS_MANIFEST_SHA256` →
  `PreparedTaskFace.load(manifest_sha256=…)` → `load_prepared_manifest(prepared_dir, expected_sha256=…)`：缺失/非法/不符
  一律 fail-closed。性质 = 06 §6 允许的"本次实际输入被动 digest"；不做签名系统、不建 ledger。
- 测试（tests/test_w1b_prepared_tasks.py）：`test_external_manifest_sha_is_the_trust_root_against_coordinated_tampering`
  ——缺失/非法/不符各拒；**协调篡改三件套**（新题面重算 problem_statement 自证 sha + 视图 public digest、重渲染 prompt、
  manifest 记录同步）后目录内互检全部自洽、旧 grader 原样配对（证明漏洞真实存在），外部 sha 未变 → `load_prepared_manifest`
  与 `PreparedTaskFace.load` 均拒；`test_prepared_face_requires_private_ref_and_digest` 增"manifest_sha256=None → 拒"。
  既有篡改测试改为交回**重算后的**外部 sha 以继续覆盖目录内互检。

### 8.3 顺手修 3：AttemptAssignmentRegistry 生命周期

- `resolve_for_sample` 在生产有调用者（bringup `_resolve_task` / `_resolve_grading_spec`，均在 GenerateFn 调用栈内）→ **保留**；
  docstring 改为"仅在飞（GenerateFn 返回前）可用，release 之后一律 `attempt_not_bound`"；类 docstring 写明生命周期 = 一次
  GenerateFn 调用，**不延长**。
- 上文 §4 接缝 2 修正：第二段 buffer/filter 阶段**不能**用 registry 对账（绑定已 release）。那一层以 miles `DataBufferInput` 的
  原始 `prompt_group` 与生成结果 `group` 对账；交付样本上已带六字段身份 + 分派三元组 + `rh2_termination_facts`，
  `resolve_termination_facts` / `assert_payload_dereferences` 仍是 join 原语。

### 8.4 顺手修 4：解引用 = 全字段核对

`assert_payload_dereferences(payload, receipt)` 改为用 `termination_facts_payload(receipt)` 重新派生并与传入载荷**全字段**比对，
不一致列出字段名 fail-closed；receipt 无 outcome → 不可解引用。核对字段（14）：`schema_id`、`physical_attempt_id`、
`rollout_execution_id`、`task_id`、`receipt_id`、`outcome_id`、`termination_kind`、`triggered_by_policy_horizon`、
`triggered_by_hard_wall`、`execution_scope_quiescent`、`canonical_frozen_patch_formed`、`fresh_grading_complete`、
`grading_report_id`、`eligibility_report_id`。测试 `test_dereference_compares_every_field_not_only_ids`（八类非 ID 改写各拒，
字段集合钉死）。仍不建 durable ledger。

### 8.5 登记不修

`termination_facts_stamp_conflict` 在 receipt/audit 已落盘之后触发、磁盘证据显示成功——已登记为解除 formal 挡板 / GPU 验收前的
审计追加项（06 计划 W1b 第二段须知），本轮不做。

### 8.6 测试/证据（2026-09-02 实跑）

```
cd rh2
uv run pytest tests/adapters/test_w1b_termination_facts_producer.py tests/adapters/test_f2_2_capability.py -q   # 44 passed
uv run pytest tests/test_w1b_prepared_tasks.py tests/adapters_miles/test_w1b_prepared_chain.py -q             # 23 passed
uv run pytest tests/ -q                                                    # 1430 passed, 232 skipped, 3 warnings in 30.00s
RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/ -q   # 502 passed
bash scripts/miles_integration_lanes.sh   # lane A 285 passed/217 skipped、lane B 502 passed/0 skipped → C5 双 lane 全部通过
uv run ruff check <全部改动文件>            # All checks passed!
```

**两条 lane 精确新计数**：lane A = **285 passed / 217 skipped**，lane B = **502 passed / 0 skipped**——与集成者已同步的 manifest
（f7f3b8d7）一致，本轮未增删 adapters_miles 测试。本轮净增 +8 例都在 lane 之外：producer 分流套件 7→13、envpack 套件 14→16。

改动文件：`generate.py`（分流/守卫/notifier）、`prepared_tasks.py`、`prepared_task_face.py`、`trusted_prep.py`、`bringup.py`
（外部 sha）、`termination_facts.py`（全字段核对）、`attempt_assignment.py`（仅 docstring）、测试 4 个 + `test_f2_2_capability.py`
oracle。未 commit / 未 stash；`bringup.py:705` 挡板、`contracts/`、`reference/`、`identity.py`、`training_view.py` 未动。

**T0**：无新增；A9 已由 owner 落账（§8.0）。

### 8.7 本轮没有改变哪些已定案语义

verify_integrity 返回 False 的 P1-1 路径（missing/ABORTED）逐字未动；finalize 之前的 task-local 收口（映射表/stage 兜底/abort 形状）
未动；A5 disposition / 三终态 / 组准入仍未实现；eligibility 契约、W1a 铸造规则、W2a 视图/controller、`contracts/` 零改动；
lane 测试集合无增减。
