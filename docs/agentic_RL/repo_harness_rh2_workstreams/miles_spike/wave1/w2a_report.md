# W2a 实现报告：runtime 通用消费链（training-only typed view）+ termination 事实

日期：2026-09-02。执行依据：06 计划 §1 D0-3（W2a 所有权边界，已拍板）与 §3 W2a 行；A5 只落中立 termination 事实（批准前边界原文："代码只实现 termination 事实与观测；A5 未拍板前不实现任何新的 admission/gradient mask/补采语义"）。

## 0. 交付物清单

| 文件 | 内容 |
|---|---|
| `rh2/src/repoharness2/envpack/training_view.py`（新增） | `TrustedTaskController` + `RolloutTaskView` + `HostGradingView` + `TrustedViewError` |
| `rh2/src/repoharness2/envpack/termination_facts.py`（新增） | `TerminationFactsV1`（中立事实记录） |
| `rh2/tests/test_w2a_trusted_views.py`（新增） | 消费链/泄漏边界/fail-closed/真实 216 题集成，16 用例 |
| `rh2/tests/test_w2a_termination_facts.py`（新增） | 事实正例三类 + 矛盾不可表示 + 中立性断言，10 用例 |

未改动：`ingest_swegym_lite.py`（只包装、不改 ingestion 语义）、`contracts/`、`adapters/`（miles 与 slime 都没碰，接缝见 §5）、`reference/`、`envpack/__init__.py`（刻意不改，见 §4 偏离）。未 commit、未 stash。

## 1. 两条代码事实的逐行复核结论

**事实 1（确认）：完整 loader 无条件反序列化全部四面，含 ValidationOnlyBundle。**
`rh2/src/repoharness2/envpack/ingest_swegym_lite.py`：`load_ingest_outputs` 在 483~488 行一次性构造 `IngestResult(packages=…, public_bundles=…, grading_bundles=…, validation_bundles=_load_models("validation_bundles_v0.jsonl", ValidationOnlyBundle))`，没有任何"跳过 validation 面"的参数或分支；`load_trusted_ingest_outputs`（554 行起）在 595 行直接调它。结论成立：**谁调完整 loader，谁的进程内存里就有 216 份 golden_patch**——rollout actor 不得直调，必须经 host 侧 trusted controller 拿剥离视图。

**事实 2（确认）：EnvironmentPackageV1 仅身份+digest；官方 spec 对 216 题覆盖为 0。**
`rh2/src/repoharness2/envpack/bundles_v2.py:156-196`：`EnvironmentPackageV1` 的字段 = task_id/source/instance_id/repo/repo_key_lower/base_commit/image/image_manifest_digest + 三个 bundle digest + 三个 provenance digest，**零内容字段**（无 prompt、无 test_patch、无 eval_cmd）——docstring 自述"只有 digest 与身份字段"与代码一致。官方覆盖 0 的旁证：`s2/implementation-notes.md`（S2-1 T2-a 条目）与 `s2/vendor/swegym_constants_242429c1.provenance.json` 均记录"swebench 4.1.0 官方对 SWE-Gym 11 仓库零覆盖（风险 F 实锤），SWE-Gym fork constants（pin 242429c1）覆盖 216/216"。推论照写进实现：**W2a 不宣称单独产出可评分链**——评分材料只经 `HostGradingView` 内嵌的 v2 grading bundle（vendor spec 派生 eval_cmd）流向 host grader，完整 v2 评分链仍归 T2-d/W3a。

## 2. typed view 形状与所有权架构

```text
load_trusted_ingest_outputs（host 侧，四面全量 + 全链验证）
        ▼
TrustedTaskController（host 进程内查表层，非新服务/权限平台）
  ├─ 构建时逐包重跑四面关系检查（运行输入一致性检查，非授权门；
  │   from_repo_root 用 strict verify_package_relations + 可信 pins/store）
  ├─ rollout_view(task_id) → RolloutTaskView：
  │     schema_id / task_id / source / instance_id
  │     / environment_package_digest / public(PublicTaskBundle 全量)
  ├─ grading_view(task_id, *, environment_package_digest) → HostGradingView：
  │     schema_id / task_id / source / instance_id
  │     / environment_package_digest / grading_bundle_digest（validator 重算自证）
  │     / grading(PrivateGradingBundleV2 密封内嵌)
  └─ ValidationOnlyBundle：参与关系检查后即丢弃，controller 无任何属性持有
```

防线（与 bundles.py 三道防线同源）：
1. 两个视图都是 `extra="forbid"` 严格模型，塞私有字段构造即拒；
2. 导入期静态断言：`RolloutTaskView` 字段名 ∩ (`PRIVATE_ONLY_FIELD_NAMES` ∪ `GOLDEN_FIELD_NAMES`) = ∅，且不含 grading/validation 字段；`HostGradingView`/`PrivateGradingBundleV2` 字段名 ∩ `GOLDEN_FIELD_NAMES` = ∅；
3. `RolloutTaskView` 的 **validator 内建**整树 forbidden marker 扫描——脏视图构造那一刻就炸，不存在"构造完再扫"的窗口。

digest 贯穿方式：`environment_package_digest = EnvironmentPackageV1.digest()` 在构建时现算，两侧视图各带一份；`grading_view()` 把它设计成**必交回的 keyword-only 参数**，不符即 `TrustedViewError`——digest 不是入口核一次就丢，而是每次评分 join 都要对账。另给 `verify_environment_package_digest(task_id, digest)` 供 baseline/eligibility 等只对锚不取内容的 join 消费方（对应 `contracts/baseline_manifest.py:131` 那个"正式链接通前保持 None"的字段，W3a/W1b 接线时用）。

## 3. T1 决策与理由

1. **RolloutTaskSpec 方向：opaque ref，不内嵌密封 grading bundle。** rollout 侧只携带 `environment_package_digest` 一个 opaque 锚（连 grading_bundle_digest 都不带——包 digest 已承诺三个 bundle digest，最小面原则）。理由：发往 rollout 方向的对象会被序列化进 actor 进程/日志/prompt 组装路径，内嵌密封对象离"一次 model_dump 就泄漏"只差一个 bug；digest 锚零内容但保留 join 一致性。密封内嵌只发生在 `HostGradingView`——它从不跨进程发往 rollout 方向。现状对照：`adapters/slime/generate.py:1749` 的 `RolloutTaskSpec` 目前把 `grading_spec: GradingEnvSpec` 内嵌在同一对象上（靠注释纪律保证不进 rollout 容器）——按本 T1，下一批集成应改为 rollout spec 只带 digest 锚、评分时经 `grading_view()` 换取材料（见 §5 接缝 1）。
2. **ValidationOnlyBundle 在 controller 上零驻留。** controller 让它参与四面关系检查后立即丢弃、不存属性；环境验证门（T2-d/W3a）是另一个 host 侧消费方，自己调 trusted 入口。测试用对象图遍历（非 gc 依赖）证明从 controller 根不可达任何 `ValidationOnlyBundle` 实例与 golden 内容字符串。
3. **termination 事实的触发者布尔冗余存储 + validator 钉死一致性。** `triggered_by_policy_horizon`/`triggered_by_hard_wall` 与 `termination_kind` 的五族划分（复用 `contracts/fa_runtime.py` 的已批封闭枚举，不新增值）由 validator 强制相等——矛盾事实（hard_wall_timeout 却声称 policy horizon）在模型层不可表示，消费方不必 import 五族常量也能读到布尔事实。
4. **计时 = 单一粗粒度区间**：`resource_occupancy_started_unix_s → terminated_unix_s`（起点 = 资源占用，A5-c 原文），不分段、不建归因系统——A5-b 复核已裁定粗粒度计时无法区分排队与真实行动，不为无实验需求的选项建基建。
5. **test-only 构造入口显式命名** `build_for_tests_from_ingest_result`（非权威关系检查，不核 pins/镜像清单），与既有 `write_ingest_outputs_for_tests` 同一命名纪律；正式链唯一入口 `from_repo_root`。
6. **from_repo_root 消费期重验**：loader 内部已逐包 strict 验证，controller 不依赖这一实现细节，用 loader 返回的可信 pins/store 再逐包重验一次（消费期重验义务，同 ingest 模块轮次 12 纪律；216 包双重验证实测整链 <2s，代价可接受）。

## 4. 偏离说明

- **不改 `envpack/__init__.py` 导出面**：任务所有权写的是"envpack/ 下新增模块"，为把 diff 严格限制在新文件，新符号经 `from repoharness2.envpack.training_view import …` 直接消费。若 owner 希望进包级导出面，属一行 T2 改动。
- **新 schema 未注册进 `registry.py` 的 `EXTRA_SCHEMA_REGISTRY`**：`registry.py` 在 envpack 之外，不在本包所有权内。后果：三个新 schema_id（`rh2.rollout_task_view.v1` / `rh2.host_grading_view.v1` / `rh2.termination_facts.v1`）暂不能被 `inspect-rh2-artifact` CLI 判型校验。注册时注意：`host_grading_view` 内容天然含 test_patch，需按 v2 grading bundle 同口径加进 marker 扫描豁免；`rollout_task_view` **不豁免**（模型可见面必须保持 0 命中）。见 §5 接缝 6。
- 泄漏扫描做成 validator 内建而非外部函数调用，比计划最低要求（"剥离后 typed view + 泄漏负测试"）更强一格——属实现强化，不改变任何已定案语义。

## 5. 开放问题（含与 adapters 层的接缝清单，留下一批集成）

1. **slime 适配层换消费链**（`adapters/slime/generate.py:1749` `RolloutTaskSpec`、`:1780` `rollout_task_from_bundle_pair`）：现走 v1 `BundlePair`（8 题冻结路径），且 `grading_spec` 内嵌在 rollout spec 上。集成方向：216 链由 `TrustedTaskController` 驱动——`RolloutTaskView` → rollout spec（public 面 + `environment_package_digest` 新字段），评分时经 `grading_view(task_id, digest)` 换材料。
2. **bringup 的 v1 私有半区**（`adapters/slime/bringup.py:729`）：`load_bundle_pairs()` 的 v1 `PrivateGradingBundle` **内嵌 golden_patch**（v1 冻结形态如此）——8 题遗留路径可容忍，但 216 链绝不许沿用该形态；控制器路径天然规避。
3. **miles 适配层同构接缝**（`adapters/miles/generate_fn.py` 任务解析面）：与 W1a 并行中，等 W1a 身份边界落定后同批切换取数通道。
4. **`environment_package_digest` 的下游落点**：`contracts/baseline_manifest.py:131` 该字段现为 None（"正式链接通前不伪造"）；W3a 装配 baseline manifest、W1b 装配 EligibilityReport join 时消费 controller 的锚核对口。
5. **TerminationFactsV1 的生产者接线**：谁在 finalize 时刻填这条记录（lifecycle/finalization 所有权在 adapters/miles 与 fa 面）归 W1b/W5a；本批只交付 typed 记录与不可表示性约束。W1b 的 disposition 纯函数将以它为输入之一（fail-fast + 双注入中立已在 W1b 行写明）。
6. **registry 注册**（见 §4 第二条）：建议随下一批 adapters 集成同轮提交。
7. **W8 eval 运输链**按计划依赖"W2a 环境解析器"——eval 侧应复用同一 `from_repo_root` controller，不另开取数通道。

**T0 升级项：无。** 本批未改任何公共 schema/协议/唯一事实来源，未新增拒绝路径进训练样本准入（fail-closed 全部发生在"构造视图/评分 join"的输入一致性层，不触样本 disposition），无需决策包。

## 6. 测试与证据

- 新测试真实运行：`uv run pytest tests/test_w2a_trusted_views.py tests/test_w2a_termination_facts.py -q` → **26 passed in 0.93s**（含真实 216 题资产的 `from_repo_root` 端到端集成用例）。
- 全仓回归：`uv run pytest -q` → **1342 passed, 200 skipped, 3 warnings in 23.80s**（skip 与 warning 均为既有项：GPU/可选依赖跳过、torch dcp 警告，非本批引入）。
- `uv run ruff check` 四个新文件 → All checks passed。

泄漏测试矩阵（tests/test_w2a_trusted_views.py）：

| 方向 | 用例 | 判定 |
|---|---|---|
| 反：private 内容不进模型侧 | rollout 视图整树 dump 无 golden/test_patch/F2P/eval_cmd/version 内容 | pass |
| 反：字段名静态互斥 | rollout 字段 ∩ 私有/golden 名单 = ∅（模块导入断言 + 单测双保险） | pass |
| 正：防线真会红 | 题面混入 "test_patch" marker → 视图构造即 ValidationError | pass |
| 反：字段走私 | rollout 视图塞 test_patch/golden_patch/grading/validation 字段 → 拒 | pass |
| 反：validation 不可达 | controller 全对象图无 ValidationOnlyBundle 实例、无 golden 内容字符串 | pass |
| 反：test_patch 只在 host 侧 | 全部 rollout 视图对象图 0 出现 test_patch 内容 | pass |
| 正：host grader 材料齐全 | grading_view 内 test_patch/eval_cmd/F2P 在位（私有内容进 host 的正例半区） | pass |
| 反：正式 grader 不见金标 | HostGradingView 塞 golden_patch 字段 → 拒 | pass |

fail-closed 三例：unknown task（rollout/grading/锚核对三口各一）、漏包（grading 面与 validation 面各删一包 → 构建拒绝）、digest mismatch（包记录 grading digest 篡改 → 构建拒绝；public repo 漂移 → 构建拒绝；评分 join 交回错误 digest → 拒绝）。

termination 事实字段表（`TerminationFactsV1`，schema_id `rh2.termination_facts.v1`）：

| 字段 | 类型 | 说明 |
|---|---|---|
| task_id / environment_package_digest | str / sha256 | join 锚（与 typed view 同一贯穿纪律） |
| termination_kind | contracts 五族封闭枚举 | 不新增枚举值 |
| resource_occupancy_started_unix_s / terminated_unix_s | float | 粗粒度单区间，validator 拒倒挂 |
| capture_closed | bool | 轨迹 capture 是否闭合 |
| execution_scope_quiescent | bool | 沙箱写手是否静默 |
| canonical_frozen_patch_formed | bool | 冻结 patch 是否形成 |
| fresh_grading_complete | bool | fresh grading 是否完整（不含好坏判断） |
| triggered_by_policy_horizon / triggered_by_hard_wall | bool | validator 钉死与五族一致，矛盾不可表示 |

中立性由导入断言 + 单测双重钉死：字段名不许含 disposition/admission/reward/mask/train/penal/sample 词根，实例无处置属性，塞 `disposition` 字段构造即拒。

## 7. 本轮没有改变哪些已定案语义

ingest 四面构造/验证链逐字未动；v1/v2 bundle schema 未动；contracts（含 TerminationKind 五族、baseline manifest）未动；adapters 两侧未动；A5 的任何 disposition 选项未预设（记录布尔事实不携带任何"该不该训练"的暗示）；registry 的 S1 冻结口径未动。

---

> **2026-09-02 codex Wave1 复核后修正注记（append-only）**：本报告的完成口径改判为
> **contract slice complete / runtime closure pending**——上文"runtime 通用消费链"的说法过宽：
> 三个新组件在生产源码中尚无消费者，真实入口仍走 v1 BundlePair（复核 F6）。runtime 接线
> （trusted-prep 一次性进程 → prepared artifact → RolloutDataSource/Bringup 复核 → generate 消费，
> formal 入口不得回退 v1）并入 **W1b 第一集成切片**。同轮已修：F3（取数口深拷贝隔离 +
> 消费时刻 `revalidated()` 重验）、F4（Controller 构造强制两侧配对校验）、F5（`TerminationFactsV1`
> 独立记录**删除**,改为 `derive_termination_facts(receipt)` 只读派生——上文 §termination 字段表
> 与"生产者接线"开放问题按新形态理解:事实全部派生自 FinalizationReceiptV1+RolloutAttemptOutcomeV2,
> attempt 锚必带,capture_closed 不再复制（owner=eligibility 事实层）,duration 不承诺（归 monotonic timeline））。

