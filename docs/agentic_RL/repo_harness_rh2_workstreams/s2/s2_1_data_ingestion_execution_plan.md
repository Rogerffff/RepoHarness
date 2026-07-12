# S2-1 执行文档：数据 ingestion + 环境验证四门

日期：2026-07-12。状态：**执行级展开，待用户确认 §9 开放问题后开工**。上位计划：`../04-s2-execution-plan.md` S2-1 节（范围以本文为准，冲突时回写上位计划）。执行线程：本线程（与 FA 工作流并行，FA 由另一 Claude 实例执行，见 §7 协调）。

一句话目标：**把 data_freeze 冻住的"静态存活 216 题"变成"环境级可信的 bring-up 候选题单"**——用可重跑的四道环境门逐题证明"这个环境能公正地判定成败"，产出漏斗账与 `EnvValidationReport`，为 GPU pass-rate 预筛（S3/S4 前单卡作业，不在本任务内）备好输入。

---

## 1. 当前仓库已有的数据处理资产（开工前盘点）

数据侧的完整叙事见 `../data_freeze/00-data-pipeline-guide.md`（强烈建议先读——全景角色划分、每步为什么、坑与规则都在那里）。本节只列 S2-1 直接消费的资产：

| 资产 | 位置（相对 `../data_freeze/`） | S2-1 怎么用 |
| --- | --- | --- |
| 四源元数据 + 真实 HF revision | `meta/*.jsonl` + `*.revision` | ingestion 的唯一数据源（**不重新抓取**；若重抓必须重跑 fail-closed 字段检查——交接义务 2） |
| 静态门存活题单（216） | `labels/static_gate_survivors.txt` + `labels/swe_gym_lite_quality_final.jsonl` | ingestion 只收这 216 题；13 题 ps-warn 带 `leakage_watch` 标记随行进池 |
| 字段处置规格 | `strip_spec.yaml`（六类：model_visible / env_materialization / grader_only / **validation_only** / pipeline_meta / strip） | ingestion 逐字段执行；**遇 spec 未列字段一律 fail-closed** |
| 镜像引用清单（实测 `_s_` 命名） | `image_manifest.md` + `meta/image_refs_swegym.txt` / `image_refs_r2e.txt` | 直接消费清单，**禁止重新拼名**（官方 `_1776_` 惯例在 SWE-Gym 上 100% 错误） |
| held-out 候选（542 题，四仓库） | `meta/heldout_candidates.jsonl` + `heldout_proposal.md` | D5 不变量执行（训练池断言排除四仓库）；§9 O-1 定是否在本任务内跑 held-out 的门 |
| 互斥断言脚本 | `meta/assert_repo_disjoint.py` | ingestion 收口时重跑留证 |
| 冻结账本 | `freeze_manifest_v0.json`（v0.1，四源 revision + 24 项 digest） | 开工第一步做 digest 自检；S2-1 产物追加进新账本（见 §4 T6） |
| R2E 物化断言语义 | `r2e_prefix_check.md`（容器 HEAD == commit_hash 的 parent） | 物化检查器实现依据（R2E 题进门时逐题自动复验） |

**rh2 代码侧已有的积木**（S1 产物，扩展不重造）：

| 积木 | 位置（相对 `rh2/src/repoharness2/`） | 现状与扩展点 |
| --- | --- | --- |
| envpack 双 bundle 契约 | `envpack/bundles.py`（`PublicTaskBundle` / `PrivateGradingBundle` / `BundlePair`，公有面泄漏扫描 `scan_public_bundle`） | 契约直接复用；新增 SWE-Gym 行 → BundlePair 的构造器（strip_spec 驱动） |
| 冻结机制 | `envpack/freeze.py`（`build_frozen_v1` / `verify_pairs_against_frozen`，8 题 frozen_v1） | 照抄机制建 `bringup_candidate_v0` 冻结记录（题 id + 镜像 digest + 题面 sha256 + 门证据 ref） |
| 物化与探针 | `envpack/materialize.py`（容器物化 + `build_probe_script` 血缘检查 HEAD^==base_commit） | 扩展：SWE-Gym 镜像物化 + R2E parent 断言分支 |
| 双沙箱 clean grading | `grading/manager.py` + `grading/queue.py`（S1-4：干净容器 apply patch → 跑测试 → 官方 parser，P1~P11 故障矩阵） | 四门 runner 的执行底座——每道门本质都是一次受控 grading 运行 |
| 8 题冻结集 | `envpack/data/` + `taskset/swebench_smoke.py` | 四门 runner 的正确性基线（8 题全部应过门） |

**尚不存在、S2-1 要造的**：SWE-Gym→envpack 的 ingestion 构造器；四门 runner 与门 fixture；`EnvValidationReport` 契约；bring-up 候选题单冻结记录；漏斗账与 benchmark card 雏形。

**明确不在 S2-1 内的下游**（防误解范围）：GPU pass-rate 预筛 [0.1,0.8] 与 pre-RL 行为诊断（S3/S4 前单卡作业，输入=本任务存活集）；R2E 全量打标（success run 题单确定时）；success run 数据组装（R2E≥50%）；held-out 的 GPU 中段筛与最终冻结。

## 2. 范围与目标

**交付物（验收面）**：

1. **ingestion 库**：216 题从 `meta/swe_gym_lite.jsonl` 行构造为 BundlePair，strip_spec 逐字段执行 + 未列字段 fail-closed 测试；`(repo, base_commit)` 去重断言（对 pandas 跨源重复的防御，现在实现、success run 池化两源时生效）。
   注：216 已经**不含** held-out 仓库题（静态门漏斗 230 → 剔 hydra/bokeh 12 → 剔质量 2 → 216，见 guide §5）；ingestion 仍要**代码级重跑 D5 断言**（预期零剔除）留证，不信转述数字。
2. **四门 runner**：empty patch 必败 / golden patch 必过且 F2P>0 ∧ P2F=0 / 假阳性解必须被拒 / 确定性 N 次一致（N 见 §9 O-3）。逐题产出 `EnvValidationReport`（新契约，进 SCHEMA_REGISTRY）。
3. **8 题基线回归**：四门对 S1 冻结集全过（门本身的正确性基线）。
4. **50 题试运行报告**（校准门，预期先暴露门的 bug 而非题的坏——风险 2）。
5. **216 全量漏斗账 + bring-up 候选题单**（冻结记录 `bringup_candidate_v0`）+ **benchmark card 雏形**（题分布/仓库分布/门通过率/leakage_watch 计数）。
6. （§9 O-1 若定为包含）held-out 542 题的静态门 + 环境门，产出 held-out 环境级存活集（GPU 中段筛的输入）。

## 3. 设计要点

### 3.1 四门的 fixture 规格（预注册，先写死再跑）

```text
门 1 empty patch 必败：空 diff 提交评分 → 官方测试必须报 FAIL（存在 F2P 未过）。
  检验的是"没有修复时环境能暴露 bug"。
门 2 golden patch 必过：private bundle 的 patch（validation_only 类）apply 后
  → F2P 全过 ∧ P2F=0。检验"金标解在本环境可复现"。
  注意 validation_only 的最小权限：golden 只在验证门沙箱可见，
  绝不落 rollout workspace，也不进模型补丁的评分路径。
门 3 假阳性解必须被拒（两种 fixture，都要跑）：
  3a 无关文件触碰 patch（新建 /tmp 层无关文件 + 不改源码）→ 必须 FAIL；
  3b golden 变异 patch（删除 golden 的最后一个 hunk；单 hunk 题改为
     hunk 内删关键行）→ 必须 FAIL。
  两种都过 = 环境"假阳性面"有下界证据。3b 若出现"删了 hunk 仍 PASS"，
  按题记 suspicious_test_coverage，进人工复核清单（不静默剔除）。
门 4 确定性：同题重跑 N 次（O-3）结果逐位一致（outcome + F2P/P2F 集合）。
  检验 flaky 测试（评分信号方差的直接来源）。
```

门的执行底座 = `grading/manager.py` 的干净容器 clean grading 路径（每道门一次受控运行，队列反压沿用 S1 P11）。

### 3.2 `EnvValidationReport` 契约要点

逐题一份：`instance_id / image_digest / 四门逐门 verdict + evidence_ref（日志 digest）/ leakage_watch 透传 / suspicious_test_coverage 标记 / runner 版本 / 重跑次数与时间戳`。进 SCHEMA_REGISTRY 走契约测试；**它是环境事实，不碰 EligibilityReport**（资格权威边界与 FA 侧 BatchAdmissionReport 的教训一致）。

### 3.3 载体与资源估算（G1 的具体化）

本机是 Apple Silicon（darwin/arm64），SWE 镜像全是 x86_64——本机跑 = QEMU 模拟，单测试 2~5 倍减速，可用于开发与小批量。数量级估算：

```text
216 题 × 6 次运行（门1 + 门2 + 门3a + 门3b + 门4×N-1 摊销）≈ 1300 次评分运行
本机模拟：单次 ~5-15min → 4 并发也要 ~2-7 天，且 216 镜像
  朴素压缩和 ~0.5TiB 级（Lite 全量口径），本机磁盘不现实。
便宜 x86 CPU 实例（16 核 / 1TB 盘，~$0.3-0.8/h）：原生速度 + 8~16 并发，
  全量预计 1~2 天墙钟，成本 ~$15-40。
磁盘策略：分批 pull → 跑门 → docker rmi（批大小按盘余量定），
  不留全量镜像；Docker Hub 认证账号 + 逐镜像 1-3s 间隔 + 429/5xx
  指数退避（image_manifest.md 限流方案照抄）。
```

**建议执行拆分**：T1~T4（开发 + 8 题基线 + 50 题试运行）在本机做（8 题镜像已在本地，50 题镜像 ~
数十 GB 可控）；T5 全量上 CPU 实例。此为 G1 推荐的落地版，§9 O-2 请求确认。

## 4. 执行步骤

| 步 | 内容 | 验收 |
| --- | --- | --- |
| T0 | 开工自检：`freeze_manifest_v0.json` 24 项 digest 复验 + `assert_repo_disjoint.py` 重跑 | 全 PASS 留证（不 PASS 即停，先查数据面变动） |
| T1 | ingestion 构造器：SWE-Gym 行 → BundlePair（strip_spec 驱动 + 未列字段 fail-closed + D5 断言 + `(repo,base_commit)` 去重） | 契约测试：216 题全构造成功；注入未列字段的负测试拒绝；held-out 仓库题注入必须被 D5 断言拦截 |
| T2 | 四门 runner + fixture（§3.1 规格逐条实现）+ `EnvValidationReport` 契约 | 契约测试 + 门逻辑单测（含 3b 变异器对单/多 hunk patch 的行为） |
| T3 | 8 题基线回归 | 8/8 四门全过；任何 fail = 门的 bug，修门不动题 |
| T4 | 50 题试运行（本机，分批 pull-run-rm） | 试运行报告：门校准问题清单 + 修复记录 + 单题耗时分布（外推 T5 预算） |
| T5 | 216 全量（载体按 O-2 定案） | 漏斗账（216 → 环境门存活 N）+ 逐题 EnvValidationReport + suspicious 清单人工复核记录 |
| T6 | 收口：bring-up 候选题单冻结（`bringup_candidate_v0`：题 id + 镜像 digest + 题面 sha256 + 门证据 ref）+ benchmark card 雏形 + guide 附录追加本阶段叙事 + implementation-notes 三节制 | 冻结记录可被 `verify_pairs_against_frozen` 同款机制复验；`00-data-pipeline-guide.md` 附录补 S2-1 章 |
| T7 | （O-1 定案后）held-out 静态门（claude headless 复用 prompt v1，R2E 题只扫 problem_statement）+ 环境门（含 R2E parent 物化断言首次实战） | held-out 环境级存活集 + 漏斗账（`heldout_proposal.md` 流程步骤 1~2 完成态） |

每步一 commit；`inspect-rh2-s1` 提交前照跑（S1 面不回归）；T2 起新契约的 digest 纳入未来 `inspect-rh2-s2` 账本面。

## 5. data_freeze 交接义务 → 实现位置映射（六不变量逐条落位）

| 交接义务（data_freeze_report 不变量） | S2-1 落位 |
| --- | --- |
| 1 训练池 ∩ Verified = ∅ + 排除 held-out repos | T0 重跑断言 + T1 D5 断言（代码级，非文档级） |
| 2 strip_spec fail-closed；重抓必须重跑字段检查 | T1 构造器 + 负测试；本任务**不重抓**（用冻结 meta） |
| 3 泄漏门只对模型可见面生效；ps-warn 带 leakage_watch 进池 | T1 透传标记 → EnvValidationReport → benchmark card 计数 |
| 4 R2E 物化断言（HEAD == commit_hash 的 parent） | materialize 扩展（T2 实现，T7 首次实战） |
| 5 镜像名 `_s_` 规则，直接消费清单 | T1/T4/T5 只读 `image_refs_*.txt`，代码里禁止出现拼名逻辑 |
| 6 四源 revision pin + digest 账本 | T0 自检 + T6 新产物追加账本 |

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
风险 C：arm64 模拟的确定性门可能出现"模拟环境特有 flaky"——
  T4 发现的 flaky 需在 x86 实例复核一次再判题坏（避免错杀）。
风险 D：磁盘/限流（§3.3 已含缓解：分批 + 认证账号 + 退避）。
风险 E：216 题分布偏斜（漏斗账要按 repo 分组呈现，若某仓库整体
  门失败率异常，先怀疑门对该仓库测试栈的适配而非题）。
```

## 8. 开放问题（开工前请用户定案）

| # | 问题 | 我的建议 |
| --- | --- | --- |
| O-1 | held-out 542 题的静态门+环境门（T7）是否并入本任务 | **并入**：runner 同一套、CPU 实例同一次租期顺跑最省；held-out 冻结虽只阻塞 S4 评测面，但晚做就要再租一次实例。静态门打标（claude headless）本机先行 |
| O-2 | G1 载体确认：T1~T4 本机 + T5/T7 便宜 x86 CPU 实例（非 GPU） | 按 §3.3 执行；成本 ~$15-40 + 1~2 天墙钟 |
| O-3 | 确定性门 N 值：04 计划写 N=3（训练池），heldout_proposal 写 2 次（held-out） | **统一 N=3**（多一次的边际成本低，flaky 检出率显著更高）；heldout_proposal 相应勘误 |
| O-4 | 假阳性 fixture 构造法（§3.1 门 3 的 3a+3b 双 fixture）认可 | 按预注册规格执行；3b 变异器的实现细节记 implementation-notes |

## 9. evidence 目录

`docs/agentic_RL/repo_harness_rh2_workstreams/s2/`：`implementation-notes.md`（三节制）、`s2_1_ingestion_report.md`（T4/T5 报告与漏斗账）、`env_validation/`（逐题 report + 日志 digest）、`bringup_candidate_v0.json`（题单冻结）。过程叙事按约定追加进 `../data_freeze/00-data-pipeline-guide.md` 附录区。
