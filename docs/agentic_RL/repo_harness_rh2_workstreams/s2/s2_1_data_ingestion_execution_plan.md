# S2-1 执行文档：数据 ingestion + 环境验证四门

日期：2026-07-12。状态：**已按 codex 开工前审查修订（轮次 4，存档 `codex_reviews.md`），O-1~O-4 已定案，可开工**。上位计划：`../04-s2-execution-plan.md` S2-1 节（范围以本文为准，冲突时回写上位计划）。执行线程：本线程（与 FA 工作流并行，FA 由另一 Claude 实例执行，见 §7 协调）。

> **[开工前修订 2026-07-12]** codex 审查发现 4 个硬阻塞（冻结 meta 缺 patch/test_patch 列、镜像清单无键无 digest、bundle v1 的 golden 归属与 strip_spec 冲突、grader 缺受控 patch 入口），全部核实成立并已修入 §2/§3/§4；四门规格按其修正（empty/golden/determinism 为硬门，假阳性降为 probe 层）；O-1 改判不并入 held-out（R2E 需要另一套 ingestion + scaleswe grader，原推荐漏算了该增量）。

一句话目标：**把 data_freeze 冻住的"静态存活 216 题"变成"环境级可信的 bring-up 候选题单"**——用可重跑的四道环境门逐题证明"这个环境能公正地判定成败"，产出漏斗账与 `EnvValidationReport`，为 GPU pass-rate 预筛（S3/S4 前单卡作业，不在本任务内）备好输入。

---

## 1. 当前仓库已有的数据处理资产（开工前盘点）

数据侧的完整叙事见 `../data_freeze/00-data-pipeline-guide.md`（强烈建议先读——全景角色划分、每步为什么、坑与规则都在那里）。本节只列 S2-1 直接消费的资产：

| 资产 | 位置（相对 `../data_freeze/`） | S2-1 怎么用 |
| --- | --- | --- |
| 四源元数据 + 真实 HF revision | `meta/*.jsonl` + `*.revision` | **revision pin 的权威来源**。注意（codex 核实）：`swe_gym_lite.jsonl` 是**裁剪后的 8 列**（instance_id/repo/base_commit/version/problem_statement/hints_text/F2P/P2P），**缺 patch/test_patch/created_at**——不足以构造 bundle 或跑 golden 门。T1 必须**按冻结 revision 重抓完整 11 列**（交接义务 2 早已预设此情形："重抓必须重跑 fail-closed 字段检查"），裁剪版 meta 不能当字段覆盖验证依据 |
| 静态门存活题单（216） | `labels/static_gate_survivors.txt` + `labels/swe_gym_lite_quality_final.jsonl` | ingestion 只收这 216 题；13 题 ps-warn 带 `leakage_watch` 标记随行进池 |
| 字段处置规格 | `strip_spec.yaml`（六类：model_visible / env_materialization / grader_only / **validation_only** / pipeline_meta / strip） | ingestion 逐字段执行；**遇 spec 未列字段一律 fail-closed** |
| 镜像引用清单（实测 `_s_` 命名） | `image_manifest.md` + `meta/image_refs_swegym.txt` / `image_refs_r2e.txt` | **禁止重新拼名**的规则保持；但（codex 核实）现清单是 Full 2438 条**无键 `:latest` 列表、无 manifest digest**，而 `PublicTaskBundle` 强制 `image_manifest_digest`——T1 须生成**键控解析清单**（instance_id → ref → resolved digest，见 §3.0），`_s_` 规则只用于校验映射 |
| held-out 候选（542 题，四仓库） | `meta/heldout_candidates.jsonl` + `heldout_proposal.md` | 本任务只执行 D5 不变量（训练池断言排除四仓库）；held-out 自己的门 = 后继独立任务（O-1 定案：不并入，R2E 需另一套 ingestion + scaleswe grader） |
| 互斥断言脚本 | `meta/assert_repo_disjoint.py` | ingestion 收口时重跑留证 |
| 冻结账本 | `freeze_manifest_v0.json`（v0.1，四源 revision + 24 项 digest） | 开工第一步 digest 自检；S2-1 产物**新建 s2_1_manifest 回链 v0.1**（冻结的 v0.1 不追加不修改，§4 T6） |
| R2E 物化断言语义 | `r2e_prefix_check.md`（容器 HEAD == commit_hash 的 parent） | 物化检查器实现依据（R2E 题进门时逐题自动复验） |

**rh2 代码侧已有的积木**（S1 产物，扩展不重造）：

| 积木 | 位置（相对 `rh2/src/repoharness2/`） | 现状与扩展点 |
| --- | --- | --- |
| envpack 双 bundle 契约 | `envpack/bundles.py`（`PublicTaskBundle` / `PrivateGradingBundle` / `BundlePair`，公有面泄漏扫描 `scan_public_bundle`） | **v1 已冻结且不能原样复用**（codex 核实）：`PrivateGradingBundle.v1` 强制含 `golden_patch`（bundles.py:152），违反 strip_spec 的 `validation_only` 归属（golden 只许验证门可见）。方案 = 新增 v2 三分体系（§3.0），**不改 v1**；8 题基线经适配器仍走 v1 |
| 冻结机制 | `envpack/freeze.py`（`build_frozen_v1` / `verify_pairs_against_frozen`，8 题 frozen_v1） | 照抄机制建 `bringup_candidate_v0` 冻结记录（题 id + 镜像 digest + 题面 sha256 + 门证据 ref） |
| 物化与探针 | `envpack/materialize.py`（容器物化 + `build_probe_script` 血缘检查 HEAD^==base_commit） | 扩展：SWE-Gym 镜像物化 + R2E parent 断言分支 |
| 双沙箱 clean grading | `grading/manager.py` + `grading/queue.py`（S1-4：干净容器 apply patch → 跑测试 → 官方 parser，P1~P11 故障矩阵） | 门 runner 的执行底座，但（codex 核实）`grade()` 只有"从 agent workspace 导出 patch"一个入口（manager.py:356 WorkspaceRunner）——须新增 `grade_controlled_patch(patch_bytes, patch_origin, patch_digest, validation_run_id)` 受控入口，与原入口共用 image check / clean checkout / apply / eval / parser，**不为四门伪造 agent workspace** |
| 8 题冻结集 | `envpack/data/` + `taskset/swebench_smoke.py` | 四门 runner 的正确性基线（8 题全部应过门） |

**尚不存在、S2-1 要造的**：完整 11 列 raw 重抓归档；键控镜像 digest 清单；bundle v2 三分体系；SWE-Gym eval_script 生成；grading 受控 patch 入口；门 runner 与 fixture；`EnvValidationReport` 契约；bring-up 候选题单冻结记录；s2_1 manifest；漏斗账与 benchmark card 雏形。

**明确不在 S2-1 内的下游**（防误解范围）：GPU pass-rate 预筛 [0.1,0.8] 与 pre-RL 行为诊断（S3/S4 前单卡作业，输入=本任务存活集）；R2E 全量打标（success run 题单确定时）；success run 数据组装（R2E≥50%）；held-out 的 GPU 中段筛与最终冻结。

## 2. 范围与目标

**交付物（验收面）**：

1. **raw 重抓归档**：按冻结 revision（`meta/swe_gym_lite.revision`）从 HF 重抓 Lite **完整 11 列**原始行 → 不可变 raw archive + 独立 digest 账（新 s2_1 manifest，§4 T6）；对完整字段集执行 strip_spec 未知字段 fail-closed（交接义务 2 的预设情形）。
2. **键控镜像清单**：216 题逐题 `instance_id → source_image_ref → resolved_manifest_digest → platform → resolved_at → registry_evidence_ref`（`docker manifest inspect` 解析，认证账号 + 退避）；运行期按 digest 拉取比对。`_s_` 规则仅用于校验映射，不保存裸 `:latest` 作身份。
3. **ingestion 库（v2 三分体系，§3.0）**：216 题构造为 `EnvironmentPackage`（public / grading-v2 / validation-only 三 bundle 以 digest 关联）；strip_spec 逐字段驱动 + 未列字段 fail-closed 负测试；SWE-Gym 的 `eval_script` 生成（make_test_spec 同源机制，spec 映射适配见风险 B）；`(repo, base_commit)` 去重断言；代码级重跑 D5 断言（216 已不含 held-out 题——漏斗 230→剔 12→剔 2→216，断言预期零剔除，留证不信转述）。
4. **门 runner（硬门 3 + 探针层，§3.1）**+ 逐题 `EnvValidationReport`（枚举结果 + 全量 provenance，§3.2；注册进 `EXTRA_SCHEMA_REGISTRY` 扩展面，S1 冻结核心 15 契约不动）+ grading 受控 patch 入口。
5. **8 题基线回归**（硬门全过 + 探针诚实分类）；**50 题分层抽样试运行报告**（repo × golden hunk 数 × F2P/P2P 规模分层、固定 seed，**不取前 50**）。
6. **216 全量漏斗账 + bring-up 候选题单**（冻结记录 `bringup_candidate_v0`）+ **benchmark card 雏形**（仓库分布/门通过率/probe suspicious 计数/leakage_watch 计数）。
7. **runner 可复用性说明**（held-out 后继任务的接口面：R2E ingestion 与 scaleswe grader 是后继任务自己的增量，见 O-1 定案）。

## 3. 设计要点

### 3.0 bundle v2 三分体系（codex 阻塞 3 的方案；v1 冻结不动）

```text
PublicTaskBundle（复用 v1 schema，不改）      模型可见面
PrivateGradingBundleV2（新）                  test_patch / F2P / P2P / eval_script
                                              —— 评分沙箱可见，不含 golden
ValidationOnlyBundle（新）                    golden_patch / mutation fixtures
                                              —— 只有环境验证门可见（strip_spec
                                              validation_only 归属的契约化）
EnvironmentPackage（新）                      三者只以 digest/ref 关联的包记录
```

冻结的 v1（8 题）不迁移不修改；门 runner 内部用 `GateInputs` 适配器统一两种来源（`from_v1_pair` 提取 golden / `from_v2_package` 直读 ValidationOnlyBundle），保证 T3 基线与 T5 全量走同一门逻辑。新 schema 全部注册 `EXTRA_SCHEMA_REGISTRY`（registry.py 扩展面，FA 契约同款机制），S1 核心 15 契约保持冻结。

### 3.1 门规格（预注册，先写死再跑；**硬门 = 1/2/4，探针层 = 3**）

```text
硬门 1 empty patch 必败：空 diff 受控评分 → 前提 = 测试真实运行且官方 parser
  成功解析，然后 ≥1 个 F2P 处于失败态。infra_failure / patch_apply_failed
  一律不算"门 1 正确失败"——那是 runner/环境故障，进 infra_failed 态重试。
硬门 2 golden patch 必过：ValidationOnlyBundle 的 golden apply 后
  → 全部 F2P 通过 ∧ P2P 零失败（RESOLVED_FULL），不只是"存在 F2P 转绿"。
  golden 只在验证门沙箱可见（validation_only 最小权限）。
硬门 4 确定性：empty 与 golden 各跑 N=3 次（O-3 定案），每次全新容器；
  比较语义 verdict + F2P/P2P 结果集合，不比较含时间戳的日志文本。
探针层 3 假阳性 probe（不是硬门，不自动剔题）：
  3a 控制探针：仓库内可 clean-apply 的无关文件变更 patch（新增仓库内
     无关文档/空白文件，不改源码；不能用 /tmp 层——那不构成 repo patch）
     → 预期 FAIL；PASS 即强假阳性信号，进人工复核。
  3b mutation probe：golden 删末 hunk（单 hunk 题改 hunk 内删关键行）。
     注意：被删 hunk 可能是冗余清理，"删了仍 PASS"不必然证明 verifier
     有问题——所以结果四态：
       rejected / suspicious_pass / fixture_invalid / infra_failure
     suspicious_pass 进人工复核清单（复核结论决定标记或剔题）；
     fixture_invalid（如变异后无法 clean apply）计数不判题。
```

门的执行底座 = `grading/manager.py` 新增 `grade_controlled_patch(patch_bytes, patch_origin, patch_digest, validation_run_id)` 受控入口（与 workspace 入口共用 image check / clean checkout / apply / eval / parser；队列反压沿用 S1 P11）——不为门伪造 agent workspace，否则 fixture 构造错误会混进环境质量结论。

**执行完整性规则**：每次运行幂等键 = `(instance_id, gate, fixture_digest, image_digest, validator_config_digest, attempt)`；evidence 原子写 + 断点续跑；**只对 infra failure 重试，质量失败不重试**；日志 digest 必须对应真实留存的日志 artifact（只有 digest 没有内容不算证据）。

### 3.2 `EnvValidationReport` 契约要点

逐题一份。结果是枚举不是布尔：`passed / failed / infra_failed / not_applicable / suspicious`（硬门逐门 + probe 逐 fixture）。provenance 全量：`source revision / 三 bundle digest / image manifest digest / swebench+parser 版本 / runtime fingerprint（载体、docker 版本）/ validator_config_digest / runner 版本 / attempt 重跑账`；透传 `leakage_watch`。注册 `EXTRA_SCHEMA_REGISTRY`；**它是环境事实，不碰 EligibilityReport**（资格权威边界与 FA 侧 BatchAdmissionReport 的教训一致）。

### 3.3 载体与资源估算（G1 的具体化）

本机是 Apple Silicon（darwin/arm64），SWE 镜像全是 x86_64——本机跑 = QEMU 模拟，单测试 2~5 倍减速，可用于开发与小批量。数量级估算：

```text
216 题 × 8 次运行（empty×3 + golden×3 + probe 3a + probe 3b，
  确定性即 empty/golden 的三次重复，O-3 定案口径）≈ 1730 次评分运行
本机模拟：单次 ~5-15min → 4 并发也要 ~2-7 天，且 216 镜像
  朴素压缩和 ~0.5TiB 级（Lite 全量口径），本机磁盘不现实。
便宜 x86 CPU 实例（16 核 / 1TB 盘，~$0.3-0.8/h）：原生速度 + 8~16 并发，
  全量预计 1~2 天墙钟，成本 ~$15-40。
磁盘策略：分批 pull → 跑门 → docker rmi（批大小按盘余量定），
  不留全量镜像；Docker Hub 认证账号 + 逐镜像 1-3s 间隔 + 429/5xx
  指数退避（image_manifest.md 限流方案照抄）。
```

**执行拆分（O-2 定案，按 codex 修正）**：T0~T3（开发 + 8 题基线）本机做（8 题镜像已在本地）；**T4 的 50 题与 T5 的 216 全量都在同一台 x86 CPU 实例上跑**——不能用 ARM/QEMU 校准门之后换 x86 判题（基质换掉会引入 flaky/耗时分布漂移，校准失效）。T4 在实例上开跑前先用 8 题做一次跨基质 re-baseline（成本 ~8×8 次运行，锚定两基质等价性）。

## 4. 执行步骤

| 步 | 内容 | 验收 |
| --- | --- | --- |
| T0 | 开工自检：`freeze_manifest_v0.json` 24 项 digest 复验 + `assert_repo_disjoint.py` 重跑 | 全 PASS 留证（不 PASS 即停，先查数据面变动） |
| T1 | **数据身份就位**：按冻结 revision 重抓 Lite 完整 11 列 → 不可变 raw archive + digest；对完整字段集跑 strip_spec fail-closed；生成键控镜像清单（216 题逐题 resolve manifest digest） | raw archive digest 入 s2_1 manifest；11 列全部被 strip_spec 覆盖（负测试：注入未知字段拒绝）；216/216 镜像 digest 解析成功且 `_s_` 映射校验通过 |
| T2 | **契约与 runner**：bundle v2 三分体系（§3.0）+ ingestion 构造器（strip_spec 驱动 + survivor 级 D5 断言收编【T1a 已有原型】+ 去重语义按**任务身份 ≠ 环境身份**定案：任务键 = `(repo, base_commit, F2P 集合)` 级或标记复核，禁止按 `(repo,base_commit)` 盲目去重【T1 实测两对同镜像不同 issue】+ **规范化完整 repo identity（owner/name，不用 basename，codex 轮次 5）** + eval_script 生成）+ `grade_controlled_patch` 受控入口 + 门 runner 与 fixture（§3.1）+ `EnvValidationReport` | 契约测试（注册 EXTRA_SCHEMA_REGISTRY）；216 题全构造成功；held-out 题注入被 D5 拦截；moto-6469/6470 与 mypy-11824/11857 两对在去重断言下均保留；门逻辑单测（含 3b 变异器对单/多 hunk 的四态行为、幂等键、原子写断点续跑） |
| T3 | 8 题基线回归（本机，经 `GateInputs.from_v1_pair` 适配） | **硬门（empty/golden/determinism）8/8 全过**；probe 层只验诚实分类（不要求 mutation 必 rejected）；任何硬门 fail = 门的 bug，修门不动题 |
| T4 | x86 CPU 实例就位 → 8 题跨基质 re-baseline → **50 题分层抽样**试运行（repo × golden hunk 数 × F2P/P2P 规模，固定 seed） | re-baseline 与 T3 语义一致；试运行报告：门校准问题清单 + 修复记录 + 单题耗时分布（外推 T5 预算） |
| T5 | 216 全量（同一实例，分批 pull-run-rmi） | 漏斗账（216 → 硬门存活 N）+ 逐题 EnvValidationReport + probe suspicious 清单人工复核记录 |
| T6 | 收口：bring-up 候选题单冻结（`bringup_candidate_v0`：题 id + 镜像 digest + 题面 sha256 + 门证据 ref）+ **新建 `s2_1_manifest_v0.json`（回链 freeze_manifest v0.1 的 digest；冻结的 v0.1 不追加不修改）** + benchmark card 雏形 + guide 附录追加叙事 + implementation-notes 三节制 | 冻结记录可被 `verify_pairs_against_frozen` 同款机制复验；`00-data-pipeline-guide.md` 附录补 S2-1 章 |

（原 T7 held-out 门已按 O-1 定案移出本任务，见 §8。）每步一 commit；`inspect-rh2-s1` 提交前照跑（S1 面不回归）；T2 起新契约的 digest 纳入未来 `inspect-rh2-s2` 账本面。

## 5. data_freeze 交接义务 → 实现位置映射（六不变量逐条落位）

| 交接义务（data_freeze_report 不变量） | S2-1 落位 |
| --- | --- |
| 1 训练池 ∩ Verified = ∅ + 排除 held-out repos | T0 重跑断言 + T1 D5 断言（代码级，非文档级） |
| 2 strip_spec fail-closed；重抓必须重跑字段检查 | **T1 重抓完整 11 列即触发该义务**：raw archive 全字段过 fail-closed 检查 + 负测试（原文"不重抓"已按 codex 核实撤销——裁剪版 meta 缺 golden 门必需字段） |
| 3 泄漏门只对模型可见面生效；ps-warn 带 leakage_watch 进池 | T1 透传标记 → EnvValidationReport → benchmark card 计数 |
| 4 R2E 物化断言（HEAD == commit_hash 的 parent） | materialize 扩展（T2 实现接口 + 单测；实战归 held-out 后继任务，O-1） |
| 5 镜像名 `_s_` 规则 | T1 键控清单以 `image_refs_*.txt` 为源、`_s_` 规则只作映射校验；运行期按 resolved digest 拉取（不信 `:latest`）；代码里禁止拼名逻辑 |
| 6 四源 revision pin + digest 账本 | T0 自检 + T6 **新建 s2_1_manifest 回链 v0.1**（不向冻结 manifest 追加） |

## 6. 与 FA 线程的协调（并行纪律）

```text
文件区域划分：本线程动 envpack/ grading/ taskset/ contracts/env_validation*
  与 s2/ data_freeze/（追加区）；FA 线程动 adapters/slime、contracts/handshake
  与 fa/。交叉点 = contracts/ 目录与 SCHEMA_REGISTRY 注册表：
  新增 schema 各自独立文件、注册表条目按字母序插入（降低合并冲突面）。
账本纪律共享：两线程提交前都跑 inspect-rh2-s1；若 FA 先建 inspect-rh2-fa，
  互不校验对方新账本（各自阶段账本独立）。
语义交叉点唯一：BundlePair/frozen 记录格式是 FA 的 envpack 消费面上游——
  本任务只加新构造器不改既有 schema 字段，FA 不受影响；
  若确需改动 bundles.py 既有字段，先在两线程间打招呼再动。
```

## 7. 风险

```text
风险 A（继承 04 计划风险 2）：SWE-Gym golden patch 质量未知，四门首跑
  大概率先暴露门的 bug——T4 50 题试运行就是为此设的校准段，
  T3 的 8 题基线保证"门对已知好题不误杀"。
风险 B：Verified 官方镜像（8 题）与 SWE-Gym 镜像（xingyaoww 命名空间）
  的测试驱动细节可能不同（conda 环境名/测试命令/parser 兼容）——
  T3→T4 之间的门适配工作量未知，预留 1-2 天。
风险 C：基质漂移——O-2 已定 50/216 同实例跑消除主要面；本机仅承担
  开发与 8 题基线，T4 开头的跨基质 re-baseline 锚定等价性。
风险 D：磁盘/限流（§3.3 已含缓解：分批 + 认证账号 + 退避）。
风险 E：216 题分布偏斜（漏斗账要按 repo 分组呈现，若某仓库整体
  门失败率异常，先怀疑门对该仓库测试栈的适配而非题）。
风险 F【已关闭 2026-07-13，T2-a】：swebench 4.1.0 官方对 11 仓库
  0 覆盖（实锤）；SWE-Gym fork constants（pin 242429c1）216/216 全覆盖，
  已 vendor 为冻结资产（s2/vendor/ + provenance），门 runner 只消费
  vendor 文件。注意最终表为小写键——repo 大小写归一化并入 T2 身份定案。
```

## 8. 开放问题定案记录（2026-07-12，codex 轮次 4 审查 + orchestrator 复核）

| # | 问题 | 定案 |
| --- | --- | --- |
| O-1 | held-out 542 题的门是否并入 | **不并入**（codex 意见成立，orchestrator 原推荐撤销）：542 题中 450 题是 R2E（tornado/pyramid），需要另一套 ingestion、R2E parent 断言实战与 scaleswe grader——并入会把任务从 216 题膨胀到 758 题 / 4500+ 次评分，成本估算失效。S2-1 只保证 runner 可复用（GateInputs 适配器 + 受控 patch 入口与数据源无关）；held-out 门 = 后继独立任务。542 题的**静态门打标**（claude headless，无 docker）不占实例，可由任意线程随时先行 |
| O-2 | 载体拆分 | **T0~T3 本机；T4（50 题）与 T5（216）同一台 x86 CPU 实例**——不用 ARM/QEMU 校准后换 x86 判题；T4 开头 8 题跨基质 re-baseline |
| O-3 | 确定性 N 值 | **N=3，且 empty 与 golden 各跑 3 次**；heldout_proposal 的"2 次"由后继任务执行时按此勘误 |
| O-4 | 假阳性 fixture | **不作硬门**：3a 保留为控制探针，3b 改为 mutation probe（四态：rejected / suspicious_pass / fixture_invalid / infra_failure），suspicious_pass 人工复核，不自动剔题；8 题基线不要求 mutation 必失败 |

## 9. evidence 目录

`docs/agentic_RL/repo_harness_rh2_workstreams/s2/`：`implementation-notes.md`（三节制）、`s2_1_ingestion_report.md`（T4/T5 报告与漏斗账）、`env_validation/`（逐题 report + 日志 digest）、`bringup_candidate_v0.json`（题单冻结）。过程叙事按约定追加进 `../data_freeze/00-data-pipeline-guide.md` 附录区。
