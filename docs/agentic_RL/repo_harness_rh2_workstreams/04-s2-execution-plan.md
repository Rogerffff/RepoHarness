# 04 — S2 执行计划：SWE-Safety 加固 + 数据 ingestion（草案，G 系列定案后去掉草案标注）

> **2026-09-02 修订注记（06 D0 拍板）**：`S1_TIER_CAP` 解除机制、红队/闸门类退出判据按 06 §1 A3/§6 防御清理**改判**——cap 整套删除（W1b 同批切换 security 维为正向能力事实）,不再存在"解除 cap"这一动作;`rh2_s2_signal_trusted` 等闸门代码化形态废止,安全最小集缩为 06 A4/W3b 范围（评分正链+sandbox 正向能力事实,删 CommandFilter/attempted-executed 平台）。数据线 T2-d/T2-e 继续推进（06 §3）,S2-6 及 G 系列按就绪稿 §7 与 06 的注记了结。本文保留为历史计划。

输入：S1 全部产物（闸门 `rh2_s1_closed_loop=true` 已确认）、设计文档 2 §5.1/§5.3/§5.4 定案、data_freeze v0 交接面（strip_spec / labels 216 存活 / freeze_manifest / image runbook）、`s1/s2_blockers.md`（导出器阻塞项）、fully_async 升级设计 I-1。退出闸门：`rh2_s2_signal_trusted = true`。

S2 的一句话目标：**把 S1 闭环从"链路正确"加固到"训练信号可信"**——退出判据 = 红队环境包全部被正确拦截/降级 + `S1_TIER_CAP` 解除（gate 可发放 `online_policy_loss_eligible`）+ bring-up 数据 ingestion 完成（F3 收尾）。

与 P3 的关系：**完全独立**。S2 全程不需要 GPU（**该表述已过时，待 G10 修正**：S2 末尾应有一次短租集成验收，见 §5）；需要 x86 docker 的部分（验证门、红队包容器实验）用便宜 CPU 实例（G1），不被 P3 租卡排期绑架。协作纪律沿用（notes 三节制、每任务一 commit、独立复核、检查点在 S2-8 前）。

> **[P3 后修订 2026-07-11]** 本轮只做两类改动：(a) 新增任务 **S2-0b（batch schedule 准入 + fan-out 交付边界正规化）**，用户 2026-07-11 定案为 **S2 第一个实现任务**（G0 相应改判）；(b) codex 复核意见（存档 `s2/codex_reviews.md`，轮次 1）与相关修正登记为 **G6~G10 待决策项**。既有任务（S2-1~S2-8）的内容本轮不改，下一轮随 G 系列一并定案。
>
> **[S2-0b 开工前加固 2026-07-11]** codex 轮次 2 审查（`s2/codex_reviews.md`）指出两个 GRPO 正确性级遗漏，已补入 S2-0b：三层身份模型（PromptGroup / RolloutExecution / Branch）、问题 E（层次化优势归一化，含 J5 gbs20 单组回退实锤）、批次级记账归属改为 `BatchAdmissionReport`（不碰 eligibility）、修复管线顺序改写（fail-closed 是终点）、验收加与真 `build_dp_schedule` 的差分验证。
>
> **[fully-async-first 重排 2026-07-12]** 用户定案 fully-async-first：S2-0b 全部内容迁出至独立 FA 工作流（**`05-fully-async-execution-plan.md`**，FA-0~FA-5，退出闸门 `rh2_fully_async_training_path_verified`）。S2 恢复为纯 SWE-Safety + 数据 ingestion 阶段，与 FA **并行推进**；`rh2_formal_training_allowed` 需要两个闸门同时为真。S2 的 GPU 段验收（G4/G10）与 FA-5 合并为同一次短租。

---

## 1. 任务分解

| # | 任务 | 位置 | 依赖 |
| --- | --- | --- | --- |
| S2-0 | 契约小项包（start_len 扩展位 + cleanup 账本 + CAP 解除机制定义） | 本机 | — |
| ~~S2-0b~~ | **已迁出**：batch schedule 准入 + fan-out 正规化 → FA 工作流（`05-fully-async-execution-plan.md` FA-0/1/3，用户 2026-07-12 定案） | — | — |
| S2-1 | 数据 ingestion + 环境验证四门 | 本机开发；四门跑 x86 实例 | data_freeze v0，G1/G4 |
| S2-2 | SWE-SEE 安全 Runtime + 命令事件日志 | 本机开发；x86 验证 | G2 |
| S2-3 | anti-cheat 物化期：git sanitizer | 本机开发；x86 验证 | S2-2 |
| S2-4 | anti-cheat 运行期 + 评分期收尾 | 本机 | S2-2/3，G3 |
| S2-5 | 红队环境包（D4，5 类注入演示） | x86 实例 | S2-2~4 |
| S2-6 | 导出器分叉感知重建（S2 blocker） | 本机 | — （与 S2-2~5 并行） |
| S2-7 | TIER_CAP 解除 + 治理收尾 | 本机 | S2-2~6 |
| S2-8 | 验收：inspect-rh2-s2 + acceptance + 闸门翻转 | 本机 | 全部 |

### S2-0 契约小项包（半天）

1. ~~`RoutingTensorRef` 留 `routed_experts_start_len` 扩展位~~ **已迁出 → FA-0**（用户 2026-07-12 确认）：该项是 rollout tape 契约、唯一下游消费是 FA 递延的真续跑路径（680824dd cherry-pick），且 FA-0 本就要动同一批 tape/投影契约面——见 `05-fully-async-execution-plan.md` FA-0 第 8 条。
2. cleanup failure 进阶段账本（codex#6）：`CleanupFailureRecord` 汇入 acceptance summary 的结构化字段 + 告警口径（计数 > 0 即 summary 黄标）。
3. `S1_TIER_CAP` 解除机制**定义**（不解除）：解除条件写成代码内显式清单（S2-2~S2-5 验收 + 红队全拦截），`GATE_VERSION` 升版流程与测试骨架就位，真正解除在 S2-7。

### S2-0b（已迁出 → FA 工作流）batch schedule 准入 + fan-out 交付边界正规化

**2026-07-12 迁移**：本任务全部内容（三层身份模型、问题 A~E、`BatchAdmissionReport` 归属、修复管线、六项离线验收）已迁入独立 FA 工作流执行计划 **`05-fully-async-execution-plan.md`**（分布：FA-0 身份契约 / FA-1 fan-out 交付边界 / FA-3 batch 准入与差分预检），本节原文见 git 历史（commit `bbc50b69` 版本）与 `s2/codex_reviews.md` 轮次 2。

迁移原因：P3 实测尾闲 26~28% 触发 fully async 升级阈值，用户 2026-07-12 定案 **fully-async-first**——BatchAdmission 必须位于 ready queue 消费端；在持续 worker 与 PromptGroupAssembler 之前单独实现只能提前报错、不能消除失败（`fully_async_rollout_pipeline_design_discussion.md` §10）。S2 不再包含该任务；S2 侧起点恢复为 S2-6 / S2-1（可并行），与 FA 工作流并行推进。

### S2-1 数据 ingestion + 环境验证四门（S2 最大件之一）

> **执行级展开（2026-07-12）**：任务级执行文档见 **`s2/s2_1_data_ingestion_execution_plan.md`**（资产盘点 / 四门 fixture 预注册规格 / T0~T7 步骤 / 载体与成本估算 / 六不变量落位映射 / 与 FA 线程的并行纪律 / 开放问题 O-1~O-4）。本节以下为原始任务定义，细节以执行文档为准。

1. **ingestion**：envpack 扩展为多源——SWE-Gym Lite 格式进 `envpack/`（`strip_spec.yaml` 逐字段执行、**遇未列字段 fail-closed**（data_freeze 不变量 4）、labels 过滤只收 216 存活、`freeze_manifest_v0` 数据源 pin、镜像引用按 `image_manifest.md` 的 `_s_` 命名实测规则）。private 字段（patch/test_patch/F2P/P2P/hints）全部进 private bundle，`hints_text` 剥离即中和的语义保持。
2. **环境验证四门 runner**（设计文档 §5.4 定案的执行体）：empty patch 必失败 / golden patch 必通过且 **F2P>0 ∧ P2F=0** / **假阳性解检测**（已知错误 patch 必须被拒）/ 确定性（同题重跑 N=3 结果一致）。golden 来源 = private bundle 的 patch 字段。四门结果逐题写 `EnvValidationReport`（进 SCHEMA_REGISTRY）。
3. 执行策略（G4）：先 50 题试运行校准四门本身（SWE-Gym golden patch 质量未知——四门第一次跑很可能先暴露门的 bug 而非题的坏），再 216 全量。产出：**bring-up 候选题单**（过门存活集）+ 漏斗账（静态 216 → 环境门存活 N）+ benchmark card 雏形。
4. bug-triggering 测试文件从模型可见上下文排除（设计文档 5.3 定案第 6 条）在 ingestion 时落位。

**验收**：四门 runner 对 8 题冻结集回归（全部应过门，作为门本身的正确性基线）；50 题试运行报告；216 全量漏斗账 + 题单。

### S2-2 SWE-SEE 安全 Runtime + 命令事件日志

1. rollout 容器安全化（落 `SandboxLease → docker args`，G2）：`--network none`（默认档）、非 root 用户、`--cap-drop ALL`、`--pids-limit`、只读根 + 可写工作区挂载、内存/CPU 限制。评分容器已 deny_all（S1-4），本任务把 rollout 侧对齐。安全分档接口保留（container 档实现，microVM 档只留枚举）。
2. **轻量命令事件日志 + provenance**（设计文档 5.1 定案 P1 档）：rollout 容器内命令执行的有序事件流（cmd、cwd、exit、时间戳、stdout/stderr digest）落 runtime-private artifact——它同时是 S2-4 claim-check 和在线拦截的**证据底座**。实现位置：bash 包装层或 harness driver 钩子（对 slime Claude Code harness 侵入最小的方案，实施时定并记 notes）。
3. 与 slime harness 的兼容验证：安全化参数下 Claude Code harness 仍能装 CLI、跑工具（x86 实例上用 S1-7a 同款 toy 流程冒烟——**network=none 与 CLI 安装/模型端点的冲突是已知风险点**，见 §3 风险 1）。

**验收**：安全参数逐项落 SandboxLease schema 实例并有测试；事件日志对一次真实 rollout 产出完整有序流；冒烟通过或冲突面如实记录。

### S2-3 anti-cheat 物化期：git sanitizer

1. 第一步**实测泄漏面**：官方 SWE 镜像 /testbed 的 git 历史里到底有什么（future commits 在不在 log/reflog/packed-refs/origin refs 里）——用 8 题冻结集逐题扫描出报告，别按假设写代码。
2. sanitizer 实现（按实测面）：删 future refs / reflog / remote refs / 不可达未来对象（`git gc --prune` 级别），产出 `GitSanitizerReport`（回写 AntiCheatSpec 挂点）；物化路径插入 sanitize 步骤（rollout 容器可见的 /testbed 必须是净化后的）。
3. 净化后回归：8 题冻结集 + 血缘契约校验不破坏（HEAD^==base_commit 仍成立）、评分结果不变。

**验收**：泄漏面实测报告 + sanitizer 报告逐题 + 净化后 8 题评分回归一致。

### S2-4 anti-cheat 运行期 + 评分期收尾

1. CommandFilter 最小版（G3）：对明确定义的命令模式（`git reflog`、`git fetch`/remote 访问、包管理器出网、curl/wget）**真拦截**（block + 脱敏 dummy 观测 + rollout 继续，attempted 记 AntiHackEvent）；其余模式审计型记录。attempted/executed 区分进 findings（S1-1 schema 已备）。
2. monkeypatch 检测规则版：评分前对 patch 的测试文件触碰、conftest 注入、sys.modules 劫持模式做规则扫描（检出 → hygiene 降级，复用 S1-4 的 tamper 通道）。
3. **谎报成功 claim-check**（设计文档 5.3 定案第 5 条）：从最终 assistant 消息提取成功声明 → 对照 S2-2 事件日志找证据事件（真实跑过测试且 exit 0）→ 无证据记 `TrajectoryQualityFinding`（不进 reward 主通道，消费面 = SFT 过滤 + 审计）。

**验收**：四类注入测试（拦截命令、monkeypatch、假声明、正常轨迹不误伤）。

### S2-5 红队环境包（D4，简历亮点 4.1 的本体）

5 类作弊注入 fixture（每类一个最小任务包）+ 一页演示报告：

```text
R-1 test tampering（agent 改测试骗评分）      → S1-4 tamper 检测 + S2-4 monkeypatch 拦截
R-2 git 历史泄漏（solution 从 reflog 可恢复）  → S2-3 sanitizer 拦截（净化前 fixture 必须能作弊成功，
                                              净化后必须失败——两态都要演示）
R-3 hidden test 泄漏进 rollout workspace      → bundle 挂载 schema 拒绝 + 投影扫描 fail-closed
R-4 token 漂移样本（伪造投影混入训练）         → projection/capture 校验拒收
R-5 谎报成功（声明通过但未跑测试）             → S2-4 claim-check 记 finding + SFT 过滤演示
```

**验收**：5 类各自"作弊可行性对照（防线关闭时能成功）+ 防线开启后被拦截"的双态证据——这是"用注入实验证明治理有效"的完整叙事，E8 治理证据的核心件。

### S2-6 导出器分叉感知重建（S2 blocker）

**排序说明（2026-07-12 再改判）**：07-09 本任务曾定为 S2 起点；07-11 改为 S2-0b 先做；07-12 fully-async-first 定案后 S2-0b 迁出至 FA 工作流，**本任务恢复为 S2 侧起点**（与 S2-1 数据 ingestion 并行；FA 工作流另行并行推进）。与 S2-1~5 无依赖。

**依赖关系澄清（回应用户 2026-07-10 的疑问"导出器是不是 E3 warm-start 的前置依赖"）**：说"前置依赖"过强，准确的说法是**分路径的**：

```text
E3 warm-start 回退 = RL 行为崩坏时用离线过滤后的 SFT 数据回锚。SFT 数据来源分两路：
路径 1：回收当前策略自己的成功 rollout
  → token 级轨迹可直接 SFT，不需要重新分词。严谨条件是**同 tokenizer 与
    renderer 契约**（不要求权重是同一份——同家族续训模型也适用）：
    token-faithful 导出给出的就是精确 token 序列 + loss mask；重新渲染
    反而会引入漂移——thinking 块重渲染漂移正是 REALIGN 发生的原因。
  → 本任务（token-faithful 分叉感知重建）是这条路径的硬前置。
路径 2：用强 teacher（Claude/GPT 等异构模型）生成轨迹做 Qwen 的 SFT
  → teacher 的 token 在别家词表里，必须以结构化语义形态（messages / tool call /
    tool result / assistant target / 来源模型）导出后重新渲染+分词。
  → 这需要一个当前不存在的 SemanticSFT 导出器（新发现的设计缺口，见 G9）；
    本任务帮不上这条路径。
结论：本任务阻塞的是路径 1（以及在线/离线 parity、同模型 RFT），不阻塞所有 SFT。
E3 究竟主用哪条路径，随 G9 一起定。
```

按 `s1/s2_blockers.md` 的升级路径实施（档案已写死技术要点与验收判据，此处只提要）：

1. **核心转变**：放弃"从 capture 记录重建全序列再比对"，改为**以叶链自身 tokens 为权威序列，用 capture 记录逐段锚定其中的可训练段**。直接复用 S1-7a 已实证的两个同构组件——`adapters/slime/generate.py::_match_turns_to_runs`（token 同一性锚定回填）与 `s1_7a_bringup/verify_transport.py`（run7/8/9 逐位核对全过）。
2. **校验语义**：mask=1 段逐位 == 按序入训轮 output_ids（digest 逐 artifact 重算）；mask=0 段不要求可重建但必须逐段有 LossMaskSpan 理由码；产出 `ExportBranchTokens` 直接取叶链 tokens 不再拼接。
3. **契约面升级（显式，非配置开关）**：`ExportTokenFidelity` 加枚举（如 `token_faithful_anchor_verified`）或升 `EXPORTER_VERSION`，让线性重建与锚定重建两种证据形态在记录上可区分；audit 双防线原样保留；幂等语义保持。
4. **树侧血缘（增强，可选）**：hook TrajectoryManager 树快照导出 fork 点与 REALIGN 覆盖区（S1-6 假设 2 已证无现成 API，需自建提取器），解锁 compaction 分支的 `lineage_reconstruction_not_supported` 当前拒绝态。

**验收**：~~run8/run9 真实 CC 轨迹（60+65 条交付样本）导出成功且导出 token 与训练侧 rollout dump 逐位一致（与 verify_transport 交叉验证）~~ **该原标准已不可执行**（60+65 条原始 .pt 未同步到本地，codex 轮次 1 核实）——**开工前以 G8 的替代标准为准**：一条已留存的真实 t0 掉落轨迹（`s1/7a_artifacts/export_sample/` 邻近资产）+ REALIGN 平铺 / fan-out 多叶 / compaction 合成回归夹具 + 下次短租采集少量完整真实轨迹复验；旧线性假设路径对错位输入仍 fail-closed。关闭后在三处（`s1_acceptance_summary.json` blockers / `implementation-notes` / `s2_blockers.md`）显式改判为 closed，不允许静默消失。

### S2-7 TIER_CAP 解除 + 治理收尾

1. **解除 `S1_TIER_CAP`**：S2-0 已把解除条件写成代码内显式清单（S2-2~S2-5 验收 + 红队 5 类全拦截），本任务在清单全绿后执行解除 + 升 `GATE_VERSION`——此后 gate 才允许发放 `online_policy_loss_eligible`。解除本身是一次 fail-closed 事件：解除代码断言每个清单项的 evidence 存在，缺一即拒绝解除。
2. **在线拦截 GPU 段挂钩（G4）**：S2-4 的 CommandFilter 在本机段用 mock 工具链验证拦截逻辑；"真实 slime 循环里连续 N 步含拦截无崩溃"的实机证据挂 `rh2_s2_online_intercept_verified` 独立小闸门，并入 P3 租卡窗口或姊妹单卡作业一起做，不单独租卡。S2-7 只固化本机段判据与 GPU 段判据的分界（见 §4）。
3. cleanup failure 账本（S2-0 的 `CleanupFailureRecord`）汇入 acceptance summary，计数 > 0 即黄标。

**验收**：TIER_CAP 解除的 fail-closed 测试（缺任一清单项 evidence 即拒绝解除）；解除后一条合格轨迹能拿到 `online_policy_loss_eligible`（S1 期间不可能）；GPU 段小闸门保持 false 待租卡。

### S2-8 验收收口

`inspect-rh2-s2` 完整 inspector（四步范式，照抄 inspect-rh2-s1）+ `s2_acceptance_summary.json`（本机段闸门 `rh2_s2_signal_trusted_local=true`，GPU 段 `rh2_s2_online_intercept_verified` 标注 pending-rental；`rh2_s2_signal_trusted = 本机段 AND GPU 段`）+ source_digests + AGENTS.md 进度翻转 + 三处 blocker 登记改判核对。检查点：本机段全绿后停人工检查点，GPU 段随租卡在 P3 窗口关闭。

---

## 2. 复用 S1 资产清单（不重造）

```text
契约：anti_hack.py（AntiHackEvent/attempted|executed）、findings.py
  （AntiCheatFinding/TrajectoryQualityFinding）、sandbox.py（SandboxLease
  network_policy=deny_all 已 schema 锁）——S2 是这些契约的执行者。
锚定算法：_match_turns_to_runs + verify_transport（S2-6 直接复用）。
GradingManager：S1-4 的 patch hygiene 骨架（S2-4 补 test reset / monkeypatch）。
gate：S1-5 的 S1_TIER_CAP 常量（S2-0 定义解除机制，S2-7 解除）。
inspector 范式：inspect-rh2-s1 四步法（S2-8 照抄为 inspect-rh2-s2）。
envpack：S1-2 的 materialize/bundles/frozen（S2-1 扩展为多源 + 四门 runner）。
本机 docker：S1-4/7a-prep 已证可用（红队 fixture 与四门的验证载体）。
data_freeze v0：strip_spec / labels 216 / freeze_manifest / image runbook
  （S2-1 ingestion 直接消费）。
```

---

## 3. 风险与未知

```text
风险 1（S2-2，重要）：--network none 与 slime Claude Code harness 的冲突。
  CC harness 要装 npm 包、要连模型端点（SGLang）——纯 deny_all 会断掉这些。
  缓解：区分"依赖预装进镜像"（消除装包出网需求）+ "模型端点走宿主 loopback/
  内网白名单"（不是公网）；S2-2 冒烟第一件事就是排这条，冲突面如实记录，
  真解法可能要等 GPU 段用真实 harness 验。
风险 2（S2-1）：SWE-Gym golden patch 质量未知——四门第一次跑很可能先暴露
  门的 bug 而非题的坏。缓解：50 题试运行先校准门本身（S2-1 执行策略已含）。
风险 3（S2-3）：git 泄漏面按假设写代码会漏——必须先实测 8 题 /testbed 的
  真实 git 历史再写 sanitizer（S2-3 步骤 1 已含）。
U-K（新）：在线拦截的 dummy 观测语义在真实 CC 多轮里是否破坏 agent 的
  后续推理连贯性（GLM-5.2 说"继续 rollout 不崩"，但 dummy 内容的构造
  影响后续轮）——本机 mock 验不到，留 GPU 段真实循环观察。
```

---

## 4. 完成定义（本机段 / GPU 段分列）

```text
本机段闸门（GPU 荒期间可全部达成 → rh2_s2_signal_trusted_local=true）：
  S2-0 契约小项包 + S2-6 阻塞项关闭（run8/9 导出逐位一致）
  S2-1 四门 + 题单、S2-2~4 安全 Runtime/git/运行期拦截/claim-check、
  S2-5 红队 5 类全拦截（双态证据）、S2-7 TIER_CAP 解除
  inspect-rh2-s2 PASS + acceptance summary

GPU 段闸门（随租卡关闭 → rh2_s2_online_intercept_verified=true）：
  在线拦截在真实 slime 循环连续 N 步无崩溃（U-K 观察）
  谎报检测在真实 CC 轨迹的召回率统计

rh2_s2_signal_trusted = 本机段 AND GPU 段。
gate 解封 online_policy_loss_eligible 需要 rh2_s2_signal_trusted 全绿；
S2-7 本机段解除后，online 档在本机段判据下已可发放，
GPU 段小闸门只 gate "在线拦截已实机验证" 这一条附加保证。
```

evidence 目录：`docs/agentic_RL/repo_harness_rh2_workstreams/s2/`（implementation-notes 三节制 + 各任务报告 + 红队演示 + acceptance）。

---

## 5. 待讨论决策（G 系列）

| # | 决策 | 推荐 | 状态 |
| --- | --- | --- | --- |
| G0 | S2 起点 | ~~S2-6 导出器（07-09）~~ → ~~S2-0b 第一（07-11）~~ → **第三次改判（用户 2026-07-12）：S2-0b 迁出至 FA 工作流；S2 侧起点 = S2-6 导出器与 S2-1 数据 ingestion 并行；FA 与 S2 是并行工作流** | **定案（已改判）** |
| G1 | 四门/红队的 x86 docker 载体 | 优先本机 docker（S1 已证可用，8 题镜像 8GB）；216 全量四门若磁盘/时长吃紧再租便宜 CPU x86 实例（非 GPU），不被 P3 排期绑架 | 待确认 |
| G2 | 安全 Runtime 网络机制本机段范围 | 本机段做"预装镜像 + `--network none` + 规则式 CommandFilter"；透明出网代理（Anygress 式）留 GPU 段/S3——本机断网场景不需要代理。**注意与 G7 联动：`--network none` 的适用面需收窄** | 待确认 |
| G3 | 谎报成功检测形态 | 规则式 evidence-backed claim checking 起步（D7 已定）；LLM judge 复核异步后置，S2 本机段不接 LLM（省额度，规则够覆盖红队 fixture） | 待确认 |
| G4 | 在线拦截 GPU 验收与 P3 的关系 | S2 在线拦截 GPU 段并入下次租卡窗口（即 G10 的 S2 集成验收短租，**已定与 FA-5 合并为同一次短租**，05 计划 §1 FA-5），不单独租卡 | 待确认 |
| G5 | micro-VM 安全档 | 本机段只做容器档 + 留 `SandboxSecurityTier` 枚举扩展位，micro-VM 不实现 | 待确认 |

以下 G6~G10 为 P3 后新增（codex 复核意见，存档 `s2/codex_reviews.md` 轮次 1 + 本轮核实），**涉及既有任务内容的修改，按用户 2026-07-11 指示留下一轮定案**：

| # | 决策 | 推荐 | 状态 |
| --- | --- | --- | --- |
| G6 | 资格解封两处表述统一 | 计划存在张力：S2-7 写"解除 TIER_CAP 后 gate 才允许发放 `online_policy_loss_eligible`"，§4 又写"解封需要 `rh2_s2_signal_trusted` = 本机段 AND GPU 段"。建议（codex 同）：本机验收只解除**实现档封顶**，正式在线训练的资格发放必须等 GPU 段在线拦截实证 | 待下一轮 |
| G7 | 黑盒 rollout 容器网络方案 | `--network none` **不能**覆盖黑盒 rollout——Claude Code 必须访问模型代理，且容器内 localhost 不是宿主机。建议：预装依赖 + 隔离 docker 网络 + 仅放行模型代理/必要内部服务 + 公网默认拒绝；`--network none` 保留给评分容器、白盒任务、安全单测（影响 S2-2 条目 1 与 G2） | 待下一轮 |
| G8 | S2-6 验收资产改判 | 原验收"run8/run9 60+65 条全部导出"**已不可执行**（.pt 不在本地）。建议改为：1 条已留存的真实 t0 掉落轨迹（`7a_artifacts/export_sample/` 邻近资产）+ REALIGN/fan-out/compaction 合成回归夹具 + 下次短租采集少量完整真实轨迹复验 | 待下一轮 |
| G9 | SemanticSFT 导出契约（新设计缺口） | token-faithful 导出只服务"同模型回收自身 rollout"的 SFT/RFT；teacher（Claude/GPT）→ Qwen SFT 需要结构化语义导出（messages/tool call/tool result/target/来源模型），当前完全没有。建议（codex 同）：S2 至少定义 `SemanticSFTRecord` 契约 + 一个最小导出闭环，批量 teacher 数据生产放 S3——避免架构再次被 token-only 出口锁死。与 E3 回退形态的选择绑定（见 S2-6 依赖澄清） | 待下一轮 |
| G10 | "S2 全程不需要 GPU"表述修正 | 大部分 S2 是本机/x86 工作，但 S2 末尾应有**一次短租集成验收**（不是重做 P3）：strict J4（S2-0b 准入 + fan-out + 真实 optimizer step）+ 真实在线拦截链（CC 发违规命令 → CommandFilter 拦截 → dummy 返回 → agent 继续 → capture/评分/投影不崩）+ 代表性轨迹留存（线性 / t0 掉落 / fan-out 多叶 / attempted 作弊各至少一条，兼供 G8 复验）。与 G4 合并为同一次短租；**2026-07-12 起该短租进一步与 FA-5 合并**（05 计划），strict J4 复验项由 FA-3 承担 | 待下一轮 |

G1~G5 无异议即按推荐执行；G6~G10 下一轮与既有任务内容一起定案。