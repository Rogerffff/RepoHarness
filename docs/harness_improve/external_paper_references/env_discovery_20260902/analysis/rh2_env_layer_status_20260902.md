# RH2 环境层现状盘点（2026-09-02）

> 来源：Claude 主线程派出的仓库探索 subagent（very thorough 档），2026-09-02。
> 性质：只读调查报告，非定案文档。文中路径与行号以调查当日工作树为准。
> 用途：环境层规划（E-Wave 划分）的现状输入。配套分析见同目录
> `claude_env_layer_analysis_20260902.md`。

---

**一句话结论**：环境层的**数据身份链**（ingestion → 三分 bundle → EnvironmentPackage → trusted loader）已经建成且防篡改链极硬（216 题真实产物已落盘、133 项定向测试）；但**环境质量链**（四门 runner / EnvValidationReport / grade_controlled_patch）**零行代码**，且已建成的 216 题资产**在训练 runtime 上零消费者**——miles/slime 链今天仍固定吃 S1 的 8 题 Verified 探针表。

---

## 1. 代码现状：`rh2/src/repoharness2/envpack/`

目录：`rh2/src/repoharness2/envpack/`（9 个 .py，2167 行；配套测试 `rh2/tests/envpack/` 9 个文件 1595 行）

### 1.1 逐文件职责

| 文件 | 行数 | 职责 |
|---|---|---|
| `__init__.py` | 93 | 库层门面；docstring 钉死硬约束：**import 时不得引入 verifiers/swebench**（`tests/envpack/test_no_verifiers_import.py` 用子进程探针钉死）。注意：**只 re-export v1 面**（bundles/freeze/materialize/scoring），v2/ingest/spec_vendor/t1_pins 不在 `__all__` 里，消费方必须按子模块 import |
| `bundles.py` | 331 | **v1 双分体系**：`PublicTaskBundle` / `PrivateGradingBundle` / `BundlePair` + 三道防线 + `load_bundle_pairs`（8 题冻结集唯一入口） |
| `bundles_v2.py` | 279 | **v2 三分体系**：`PrivateGradingBundleV2`（无 golden）/ `ValidationOnlyBundle`（golden）/ `EnvironmentPackageV1`（纯 digest 记录）+ 两个 canonical builder |
| `freeze.py` | 159 | `frozen_v1.json` 冻结账本的生成与防漂移校验（只服务 v1 的 8 题） |
| `materialize.py` | 280 | `/testbed` **血缘校验**探针（脚本文本生成 + 判定）+ `BASH_ENV` 注入内容 + 运行期**镜像 RepoDigests 比对**。刻意零容器 API |
| `scoring.py` | 210 | 官方 swebench parser 封装 → `EvalVerdict` → `grading_outcome_fields()`（GradingReport 字段组）。**只服务 v1 的 `PrivateGradingBundle`** |
| `ingest_swegym_lite.py` | 598 | SWE-Gym Lite 216 题 ingestion 构造器 + 事务化写盘 + strict loader + `load_trusted_ingest_outputs`（正式消费唯一入口） |
| `spec_vendor.py` | 115 | vendor spec 封闭注册表；`eval_cmd` 的唯一权威派生 + 消费期互检 |
| `t1_pins.py` | 102 | T1 封板输入 pins 的三级验证（代码常量 → pins 记录 → 七项输入文件） |

### 1.2 数据结构（字段级）

**v1（8 题冻结集，`envpack/data/frozen_v1.json` + `swe_smoke_tasks.json`）**

- `PublicTaskBundle`：`schema_id / instance_id / repo / base_commit / image / image_manifest_digest / workdir(/testbed) / allowed_tools(bash,edit) / problem_statement / problem_statement_sha256 / public_hints`
- `PrivateGradingBundle`：`instance_id / repo / version / base_commit / golden_patch / test_patch / fail_to_pass / pass_to_pass / eval_script(官方全文) / test_cmd / environment_setup_commit`
- `BundlePair`：public+private，构造时校验 instance_id 与 base_commit 一致

**三道防线**（`bundles.py:13-27` docstring；均有测试）：① `extra="forbid"` schema 白名单 ② `PRIVATE_ONLY_FIELD_NAMES` 字段名静态互斥（模块级 assert + 单测）③ `scan_public_bundle` 整树 forbidden-marker 扫描（8 题实测 0 误报）。

**v2（216 题，S2-1）** — 因 `strip_spec.yaml` 把 `patch` 归为 `validation_only`，v1 的"grading 面强制内嵌 golden"违规，故新增三分体系，**v1 原样保留不迁移**：

- `PrivateGradingBundleV2`：`instance_id / repo / repo_key_lower / version / base_commit / test_patch / fail_to_pass / pass_to_pass / eval_cmd / python_version / spec_vendor_id`。**无 golden**。schema 级不变量：`repo_key_lower == repo.lower()`；F2P/P2P 各自无重复且交集为空
- `ValidationOnlyBundle`：`instance_id / golden_patch / golden_patch_sha256`（自证）
- `EnvironmentPackageV1`：`task_id("<source>::<iid>") / source / instance_id / repo / repo_key_lower / base_commit / image / image_manifest_digest / public_bundle_digest / grading_bundle_digest / validation_bundle_digest / raw_archive_sha256 / image_manifest_keyed_sha256 / spec_vendor_json_sha256`。**零内容字段**——只有身份与 digest，可以进任何账本而不构成泄漏面

关键定案（`bundles_v2.py:19-32`）：**内部权威 repo 身份 = 原始大小写 `owner/name`，`repo_key_lower` 是显式存储的小写投影**（docker 仓库名与 SWE-Gym spec 表最终键都是小写，这个坑在 T1/T2-a 出现两次）。**环境身份 = `(repo_key_lower, base_commit)`，任务身份 = source-qualified `task_id`**——同环境多任务合法共存（moto-6469/6470、mypy-11824/11857 两对实测）。

### 1.3 冻结（freeze）流程

**v1 路径**（`envpack/freeze.py`）：`swe_smoke_tasks.json` → `split_frozen_entry` 拆两半 → 逐题 `build_freeze_record`（instance_id / image / image_manifest_digest / problem_statement_sha256 / public_bundle_digest / private_grading_bundle_digest）→ 加 meta（`frozen_at` 运行期 `date -u`、`source_tasks_file_sha256`、`records_digest`）→ 写 `frozen_v1.json`。`load_bundle_pairs()` 默认逐题重算比对，任一字段不符抛 `FrozenRecordMismatch`（fail-closed）。

**v2 路径**（`envpack/ingest_swegym_lite.py` + `t1_pins.py` + `spec_vendor.py`）是完全不同的、更硬的一条链，**四级防篡改**：

```
代码常量 (T1_PINS_SHA256 / INGEST_MANIFEST_SHA256_PIN / VENDOR_REGISTRY)
  → t1_input_pins_v1.json（七项输入封板 digest，不可追加）
  → 七项输入文件（raw archive / keyed image manifest / registry evidence /
     survivors / image_refs / strip_spec / vendor specs JSON）
  → ingest_manifest_v0.json（五数据文件 digest + 行数 + t1_input_pins）
  → 五个数据文件
```

`load_trusted_ingest_outputs(repo_root)` 是 T2-d/e 唯一正式入口，链条：T1 pins 三级验证 → survivors/image store 严格加载 + `finish_assertions` → 提交记录对代码 pin → `load_ingest_outputs`（严格键集/int 类型/五文件 digest/模型解析/重复 id 拒绝/**四方 id 集合 == 可信 survivor 全集**/逐包 `verify_package_relations`/duplicate clusters 由已加载 bundle **重算逐字比对**）。

### 1.4 物化（materialize）流程

`envpack/materialize.py` 只做两件事：生成探针 bash 脚本文本、解析输出并判定。执行通道由绑定层提供（verifiers 用 `runtime.run`，slime 用自己的 sandbox）。

**血缘判据**（S0-7 两次实证得到）：`base_commit 对象存在 且 (HEAD == base_commit 或 HEAD^ == base_commit)`。原因：官方预构建镜像的 `/testbed` HEAD 是构建时叠加的 "SWE-bench" 提交，**且不保证内容为空**（astropy-14995 带 1 行 pyproject.toml 环境修补）。环境修补 diffstat 与工作树脏项**只作证据不参与判定**。

第二部分是 `ImageDigestCheck`：判据用 `RepoDigests`（registry manifest digest）而不是 image ID（本地 config digest，两者永不相等）；**空 RepoDigests 即不通过**，本地构建镜像必须在任务面显式 `local_build` 豁免。

### 1.5 评分（scoring）如何接 grading

```
容器内 eval 脚本 stdout+stderr 合并单流（调用方负责 2>&1）
  → swebench.harness.grading.get_logs_eval（MAP_REPO_TO_PARSER 选 parser）
  → get_eval_tests_report（对照 F2P/P2P 清单）
  → get_resolution_status → EvalVerdict
  → grading_outcome_fields() → contracts.GradingReport 的
     outcome / failure_category / reward / 四个计数字段
```

三类官方 parser 已实测覆盖：django unittest verbose / sympy `bin/test` / pytest `-rA`（含 ANSI 色码，回归测试用真实带色日志钉住）。对 swebench 的依赖是**惰性**的（模块 import 不需要它）。

两个"如实沿用官方语义"：silent success（不在日志出现的测试按通过计）、`apply_ok=False` 的坏码是并集不区分成因（本层映射为 `patch_apply_failed`，容器级故障改判 `infra_failure` 是 manager 的职责）。

消费方 `rh2/src/repoharness2/grading/manager.py`（`SWEGradingManager.grade()`）：workspace 导出 patch → hygiene 切段 → fresh 容器（`--network none`）clean checkout → `materialize` 血缘核验 → 重放 cleaned patch → 跑 eval → `envpack.scoring` 解析 → 三分归因 + GradingReport。

**关键缺口**：`grade()` **只有"从 agent workspace 导出 patch"一个入口**（`manager.py:769`），S2-1 计划要求的 `grade_controlled_patch(patch_bytes, patch_origin, patch_digest, validation_run_id)` 受控入口**不存在**——这是四门 runner 无法开工的直接前置。

### 1.6 当前支持哪些数据源

| 数据源 | 状态 |
|---|---|
| **SWE-bench Verified**（8 题） | ✅ 完整支持（v1 双分 + frozen_v1 + 官方 eval_script + 真实回归），**但被闸门禁止用于正式训练**（checkpoint 用后即弃条款） |
| **SWE-Gym Lite**（216 题） | ✅ ingestion 完成（v2 三分 + 包记录 + trusted loader），❌ 环境门未跑，❌ 训练 runtime 未接线 |
| **R2E-Gym-Subset** | ❌ **从未发生**。全仓唯一 ingester 是 swegym_lite；R2E 需另一套 ingestion + scaleswe grader + ~2.3TiB 镜像面（`miles_spike/first_training_readiness_alignment_claude.md:18`）。`strip_spec.yaml` 里有 14 列处置规格，但零代码 |
| SWE-Gym Full / SWE-smith | 只有元数据与选型记录，零 ingestion |

注意 v2 的 `source` 字段是 `Literal["swe_gym_lite"]` 封闭枚举——**扩源要升 schema 版本**。

### 1.7 `taskset/` 两个文件

- `taskset/image_manifest_store.py`（396 行）：S2-1 T1b **键控镜像清单的状态存储**（纯逻辑零网络）。schema **v4**：全部 header 字段必填必验、entry↔evidence 逐字段交叉核对、双文件事务（evidence 先写、manifest header 内嵌 evidence digest 作提交记录）、事务恢复对已提交集合**规范化重序列化 SHA 回验**、写盘前对称守卫、`finish_assertions` 完成断言。核心教训："严格性不可被删字段关闭"。44 项无网络单测。
- `taskset/swebench_smoke.py`（196 行）：**verifiers 薄壳**。S1-2 后只剩协议适配。**如实记录的隔离缺陷**：eval 仍在 agent 用过的同一容器/工作树上跑（clean-checkout 重放归 S1-4 manager）。

---

## 2. 数据冻结现状

主文档：`docs/agentic_RL/repo_harness_rh2_workstreams/data_freeze/`（`00-data-pipeline-guide.md` 叙事、`data_freeze_report.md` 收口、`freeze_manifest_v0.json` 24 项 digest 账本、`implementation-notes.md`、`heldout_proposal.md`、`strip_spec.yaml`、`labels/`、`meta/`）

### 2.1 SWE-Gym Lite 216/230 的静态门

漏斗（`00-data-pipeline-guide.md:116-124`，已从 `labels/swe_gym_lite_quality_final.jsonl` 230 行复算验证）：

```
230
 −12  D5 不变量：held-out repo 整体剔除（hydra 11 + bokeh 1）
 −1   test_adequacy = fail（dvc-2017：打包/文档整理，无可断言的运行时行为差异）
 −1   solution_leakage = fail 且 leakage_source = problem_statement（MONAI-3326）
 =216（labels/static_gate_survivors.txt 实测 216 行）
```

**门的构成**：① SPICE 式 LLM 三标签（issue clarity / test adequacy / solution leakage，claude headless 批量 230 题零解析错误，人工校准 15/15 标签级一致）② 正则泄漏扫描（`labels/regex_scan_lite.jsonl`）③ D5 held-out repo 排除断言。

**D7 口径修正**：泄漏门**只对模型可见面（problem_statement）生效**——正则层合并题面+评论区判命中 38/230，分字段归因后题面只有 2 题（0.9%），另 36 题全在 `hints_text` 里，而 hints 按 strip_spec 本来就整体剥离。13 个 ps-warn 带 `leakage_watch` 标记**进池不剔**。

**注意**：这三个标签恰好对应设计文档 `task_quality_report` 的前三字段——但它是一次性 LLM 批处理脚本（`labels/run_labeling.py`）产出的 jsonl，**不是** `TaskQualityEvaluator` 对象，也没有 `task_quality_report_ref` 挂到环境包上。

### 2.2 held-out 候选 542：来源与状态

来源（`heldout_proposal.md` + `meta/heldout_candidates.jsonl`）：按 repo **整仓库切出**——R2E-Gym-Subset 的 tornado(261) + pyramid(189)，SWE-Gym 的 facebookresearch/hydra(66) + bokeh/bokeh(26)。互斥性已断言 PASS（`meta/repo_disjoint_report.json`）。

**状态：一题未冻结**。且 **542 里 450 题（tornado+pyramid）依赖 R2E ingestion，而 R2E ingestion 从未发生**——处置建议（对齐意见书）是首训取闭环档、held-out 改用 SWE-Gym 半区（hydra 66 + bokeh 26，够 T=50~80）。

**D5 不变量**：Lite 230 里就含 hydra 11 + bokeh 1，"一切训练 run（含 bring-up）排除 held-out repos"已做成代码级断言（`ingest_swegym_lite.py:71` `HELDOUT_BASENAMES` + `build_task` 内 fail-closed）。

### 2.3 "四门" —— 注意有两个不同的"四门"

**(A) 环境验证四门**（S2-1 主体，`s2/s2_1_data_ingestion_execution_plan.md:68-90`）：

| # | 门 | 判据 | 实现状态 |
|---|---|---|---|
| 1 | **empty patch 必败**（硬门） | 空 diff 受控评分 → 前提=测试真跑且 parser 成功解析 → ≥1 F2P 失败。infra_failure/patch_apply_failed **一律不算"正确失败"** | ❌ 零实现 |
| 2 | **golden patch 必过**（硬门） | golden apply 后全部 F2P 通过 ∧ P2P 零失败（RESOLVED_FULL） | ❌ 零实现 |
| 3 | **假阳性 probe**（**探针层，非硬门，不自动剔题**） | 3a 控制探针（无关文件变更 patch，预期 FAIL）；3b mutation probe（golden 删末 hunk），四态：rejected / suspicious_pass / fixture_invalid / infra_failure | ❌ 零实现 |
| 4 | **确定性**（硬门） | empty 与 golden **各跑 N=3 次**（O-3 定案），每次全新容器；比较语义 verdict + F2P/P2P 结果集合 | ❌ 零实现 |

配套 `EnvValidationReport` 契约要点已写死（§3.2）：结果是**枚举不是布尔**（`passed/failed/infra_failed/not_applicable/suspicious`）、provenance 全量、注册 `EXTRA_SCHEMA_REGISTRY`、**它是环境事实不碰 EligibilityReport**。执行完整性规则已写死：幂等键 = `(instance_id, gate, fixture_digest, image_digest, validator_config_digest, attempt)`、evidence 原子写 + 断点续跑、**只对 infra failure 重试**。

**资源估算已做**（§3.3）：216 × 8 次运行 ≈ 1730 次评分；本机 ARM/QEMU 不现实；x86 CPU 实例（16 核/1TB，~$0.3-0.8/h）1~2 天、~$15-40；**T4 的 50 题与 T5 的 216 全量必须在同一台 x86 实例上跑**。

**(B) held-out 的四道门**（`data_freeze_report.md:23-24` + `heldout_proposal.md:22-35`）：① 静态质量门 ② 环境验证门（= A）③ GPU pass-rate 中段筛 ④ 分层冻结（按四仓库比例抽 T=50~80）。全部未执行。

### 2.4 GPU pass-rate 预筛：设计与状态

**设计**：目标模型 n=8 采样，保留 pass-rate ∈ **[0.1, 0.8]**（MAI 组锚点），与 **pre-RL 行为诊断同批 rollout**（省卡时），单卡 30B 推理即可。输入 = 环境门存活集，输出 = bring-up 题单（100~200 题）。

**状态：零实现、载体未定**。`freeze_manifest_v0.json` 的 `pending_gpu_steps` 之一；plan-06 列为**界外**，载体归 C 决策包（对齐意见书第 14 条待拍板项）。

---

## 3. S2-1 数据段产物

| 阶段 | 状态 | 产物 |
|---|---|---|
| T0 开工自检 | ✅ | `s2_1_t0_selfcheck.md`（24 项 digest 复验全 PASS） |
| T1a raw archive | ✅ 封板 | `raw/swe_gym_lite_full_f70b1a29.jsonl`（230 行 × 11 列，HF revision `f70b1a29`） |
| T1b 键控镜像清单 | ✅ 封板 | `image_manifest_keyed.json`（schema v4，**216/216 fully-verified**）+ `raw/image_registry_evidence.jsonl` |
| T1 关闭 | ✅ 2026-07-13 用户确认 | `t1_input_pins_v1.json`（七项输入封板） |
| T2-a 风险 F | ✅ 关闭 | 官方 swebench 4.1.0 对 SWE-Gym 11 仓库**零覆盖**；SWE-Gym fork@242429c1 覆盖 216/216（33 仓库/808 spec 对）→ vendor 冻结 |
| T2-b bundle v2 契约 | ✅ | `bundles_v2.py` + registry 注册 |
| T2-c ingestion | ✅ **216/216 ALL PASS** | `ingest/` 五文件 + `ingest_manifest_v0.json` |
| **T2-d `grade_controlled_patch`** | ❌ **未实现** | — |
| **T2-e 四门 runner + fixture + EnvValidationReport** | ❌ **未实现** | — |
| T3 8 题基线回归 / T4 50 题试运行 / T5 216 全量 / T6 收口 | ❌ 全未执行 | — |

历经 codex 轮次 12/13/14/15 四轮加固（`s2/s2_1_t2_report.md`、`s2/codex_reviews.md`），修掉的都是"安全模型级"的洞（身份交叉核对缺失、vendor 路径注入、互检未接线、输入未对封板 pins 验证、输出提交记录可被一致性重封等）。

---

## 4. 设计文档对照

### 4.1 八步流水线（`docs/harness_improve/environment_production_and_quality_pipeline_design.md`）实现对照

| 步 | 设计要求 | 现状 |
|---|---|---|
| 1 Source Intake | PR/issue/fixture/合成/benchmark item | 只做了"benchmark item"（HF 拉取） |
| 2 Repository Snapshot | 固定 snapshot/base commit/依赖锁 | ✅ `base_commit` + `image_manifest_digest` 双 pin |
| 3 Diff/Test Split | 拆 code/test diff、隐藏评分资源 | ✅ **v2 三分体系正是这一步落地** |
| 4 Task Draft | prompt、公开约束、隐藏约束 | 部分：`render_user_prompt` + `PUBLIC_SYSTEM_HINTS` 逐字冻结；无"隐藏约束" |
| 5 Image Build | 构建/选择镜像、dep cache | 只做"选择 + digest 验证"，**零构建能力** |
| 6 **Anti-cheat Preparation** | git 历史净化、future/remote refs 删除 | ❌ **零实现**（且归属线被 W3b 移动，见 §6 注） |
| 7 **Validation Runs** | empty/golden/determinism/runtime 复验 | ❌ **零实现**（= S2-1 T2-e） |
| 8 **Task Quality Evaluation** | `TaskQualityEvaluator` 出报告 | ⚠️ 只有一次性 jsonl，无对象无 schema 无 ref 挂载 |
| 9 EnvironmentPackage Freeze | 冻结 spec + digest | ✅ `EnvironmentPackageV1`（**但缺 task_quality_report_ref / anti_cheat_spec_ref / verified_in_training_runtime 三个字段**） |

§5 六条准入门槛，当前三条无载体（empty/golden/determinism），三条无字段（runtime 复验、quality ref、anti-cheat ref）。

### 4.2 E4 "agent 自产任务流水线"（实验设计 L182-186）

```
并行（不阻塞首训）：agent 自产流水线作为 5.4 环境生产线的实战验证——
  "PR 抓取 → agent 建环境自纠错 → F2P/P2P 抽取 → 陈述重写 → 环境验证门"，
  目标自产 50~200 题供第二轮。良率数据即简历证据。
  参考实现优先精读 Scale-SWE（arXiv:2602.09892——微调对象恰为 Qwen-30B-A3B）。
```

关联条款：L148（agent 化自产 = 简历亮点定位）、调查结论 3（公共瓶颈步 = agent 建 Docker 环境 + 迭代自纠错，MAI 实测建环境成功率仅 42.8%）、L224（自产任务禁 solution hint 写进任务描述）、L348（良率与失败归因 2026-07-07 升为 E8 必交付）。**状态：纯设计，零实现，无执行计划文档**。

### 4.3 设计文档 2 §5.4 环境验证门定案（2026-07-06）与后续修订

定案扩展三项：① gold patch 判据精化为 `F2P>0 且 P2F=0` ② 假阳性解检测 ③ 非功能 verifier 检测。生产线深度项（难度校准/SWE-Test 反转/多语言解析/合成子流水线等）全部进 backlog B1~B7。

S2-1 执行计划两处修订：① 假阳性检测从硬门降为 probe 层 ② golden 门取更严的 RESOLVED_FULL。

**⚠️ W3b 已推翻部分 §5.3 anti-cheat 定案**：plan-06 W3b 明确"删除 CommandFilter + dummy 观测 + attempted/executed 平台"，git 净化从**物化期环境生产动作**改为**运行期沙箱正向能力核实**（"git future refs + reflog + remotes 已清"为 sandbox 创建后核实项，缺任一项不产训练样本）。环境层与 runtime 层的归属线被移动，规划时需显式确认 `AntiCheatSpec`/`git_sanitizer_report` 的最终归属。

---

## 5. plan-06 W2 环境接口与 miles 链任务消费

### 5.1 W2a 原文要求（摘）

- 入口 = `load_trusted_ingest_outputs`（不收未核可信 pins 的 caller objects）
- 模型可见面只含 public projection；`PrivateGradingBundleV2` 仅 host 侧 grading 控制面消费；`ValidationOnlyBundle/golden_patch` 永不进 rollout/正式 grader
- `EnvironmentPackageV1.digest()` 贯穿 baseline/grading/eligibility join
- codex 终核补充：`EnvironmentPackageV1` 仅身份+digest（无 prompt/test_patch/eval_cmd），完整 v2 评分链归 T2-d/W3a——W2a 不宣称单独产出可评分链
- W2b 真实数据集成是条件式（启动条件 = T2-d/e 完成 且 owner 在 C 包确认 GPU spike 数据目标）

### 5.2 当前 miles 链的任务消费（"8 题固定表"）

```
miles --custom-generate-function-path
  → repoharness2.adapters.miles.generate_fn.Rh2MilesGenerateFn
  → rh2_custom_generate (slime/generate.py)
  → BringupService.__init__ (slime/bringup.py:729)
       self.pairs = {p.instance_id: p for p in bundles.load_bundle_pairs()}   ← 固定 8 题
  → RolloutTaskSpec (slime/generate.py:1749)
```

`RolloutTaskSpec` 携带的是 **`public.digest()`，不是 `EnvironmentPackageV1.digest()`**——W2a 与就绪稿 §2.3 第 3 条都明确要求改。`rh2/tests/adapters_miles/test_bringup_vendor_only.py:81` 有 `assert len(service.task_specs) == 8` 钉死现状。

就绪稿 §2.1 formal preflight 必须拒绝项包括："S1 的 8 道 Verified 探针题冒充训练数据"、"未绑定 `EnvironmentPackageV1.digest()` 的任务"。

### 5.3 216 题资产的消费者数量

全仓 grep：`load_trusted_ingest_outputs` 引用只有三处——定义处、一次性运行器（`experiments/s2_1_ingestion/build_environment_packages.py:97`）、测试。**生产链零消费者**。`bundles_v2` 三个类在 `adapters/`、`grading/`、`taskset/` 下零引用。

---

## 6. 缺口清单（按实现状态四档）

### 【已实现 + 有测试】
v1 双分 bundle + 三道防线；frozen_v1 冻结账本；/testbed 血缘校验 + 镜像 digest 比对；官方 parser 评分链；v2 三分 bundle + EnvironmentPackageV1；vendor spec 注册表；T1 pins 三级验证；SWE-Gym Lite ingestion + trusted 入口；键控镜像清单 store v4；框架无关性探针；216 题真实产物；静态门标签数据（230 行，已复算一致）。

### 【已实现但未接线】（环境层最大的一块）
| 项 | 缺什么 |
|---|---|
| `load_trusted_ingest_outputs` 216 题可信入口 | 生产消费者为 0；`BringupService` 仍固定 8 题 |
| `EnvironmentPackageV1.digest()` | 未进 `RolloutTaskSpec` / `BaselineWorkspaceManifestV1` / frozen patch / run manifest |
| `PrivateGradingBundleV2` 评分链 | grading manager 只认 v1（有 `eval_script` 全文）；v2 只有 `eval_cmd`，评分正链（T2-d/W3a）未实现 |
| `ValidationOnlyBundle` | 唯一消费方（四门 runner）不存在 |
| `AntiHackEvent` 契约 | `generate.py:3800` 硬编码 `findings=()` |

### 【已设计未实现】（设计文本齐备到可直接开工）
`grade_controlled_patch` 受控评分入口（签名已定）；环境验证四门 runner + fixture + `EnvValidationReport` 契约 + `GateInputs` 适配器（v1/v2 同门）；`TaskQualityEvaluator` + 十字段 `TaskQualityReport`；`AntiCheatSpec` + git sanitizer（⚠️ 归属待确认）；`verified_in_training_runtime` 复验；held-out 四道门 + T=50~80 分层冻结；GPU pass-rate 预筛（载体待拍板）；R2E ingestion（~2.3TiB）；bring-up 题单冻结；benchmark card 雏形；假阳性 mutation 生成器。

### 【只有提及 / 观察项】
agent 自产任务流水线（五步已列，无执行计划）；难度校准 + query evolution（backlog B7）；合成任务子流水线 + pass@100 过滤（B2）；多语言日志解析（B3）；任务类型分化 reward / SWE-Test 反转 / bug injection（B1）；非功能 verifier 检测（定案有、S2-1 规格缺）；LLM rewrite 低质题面；held-out 家族治理细则；SWE-Gym Full / SWE-smith 扩源；SWE-World / MEnvAgent / DockSmith / EvoConfig（观察项）。

---

## 7. 三条最值得注意的结构性事实

1. **两条数据链平行存在且互不相通**。v1（8 题）撑着今天全部能跑的东西；v2（216 题）是正确的未来但下游零消费者。桥（`GateInputs` 适配器、v2 评分正链 T2-d、`BringupService` 换表）三处全缺。环境层第一优先不是"再造资产"而是"接线 + 补四门"。
2. **`grade_controlled_patch` 是单点瓶颈**。四门 runner、mutation probe、golden 门、held-out 四道门第 2 步、bring-up 题单、E8 导入良率——全部堵在这一个受控入口上。
3. **"环境层"的边界正在被 plan-06 重划**（W3b：git 净化从环境生产期动作改为运行期能力核实）。规划前必须确认 `AntiCheatSpec` 的最终归属。
