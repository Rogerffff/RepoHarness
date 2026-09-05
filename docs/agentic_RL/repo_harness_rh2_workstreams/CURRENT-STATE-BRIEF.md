# RepoHarness rh2 · 当前状态简报（给外部模型 / 新接手者）

更新：2026-09-05。用途：让一个**没有任何上下文**的模型或人在 15 分钟内知道"这个仓库是什么、做到哪了、什么已定、什么未定、该读哪些文件、哪些文件已过时"。本文是**导航与快照**，不是权威定案——所有定案以下文列出的权威文档为准；本文与它们冲突时以它们为准，并请顺手修本文。

---

## 1. 三十秒定位

- **项目**：RepoHarness（rh2 架构）= 面向 SWE agent 强化学习的**环境生产线 + 训练治理层**。它不造训练内核、推理服务和 agent 本体：训练后端用 **miles**（SGLang 团队维护的 slime fork，fully-async RL），推理用 SGLang，agent 用 **Claude Code**（经 vendored 的 slime agent adapter 接入）。RH2 自己负责三件事：① **环境可信**（任务包/镜像/评分材料的可信入口与隔离）；② **reward 可信**（fresh grader、评分投影、反作弊边界）；③ **哪些轨迹能进 policy loss**（身份、eligibility、组准入、逐 token 对齐、staleness）。
- **目标实验**：在 8×RTX PRO 6000（sm_120，PCIe，无 NVLink）上用 GRPO（n=8）+ faithful DIS（重要性采样校正，默认候选 loss）训练 Qwen3-30B-A3B 做 SWE 任务；首训目标是**验证闭环可信**，不是主张能力提升。
- **现状一句话**：本地训练链已按 Wave1~Wave3 搭完（身份铸造、可信输入、组准入、sandbox 双 profile、评分投影、staleness 唯一权威、关停链、最小冷恢复、多 engine 最小正确性、CP>1 支持），正在等 codex 对最后一个反例的窄复核，之后进入 **W8（eval 运输链）→ C 包决策 → W7（实验包）→ 租 GPU 做资格作业**。**首训用哪批任务（taskset）尚未决定**——数据线（T2-d/T2-e/W2b）与训练链并行，目前有 216 题 SWE-Gym Lite 的可信 ingestion 产物，但未选定首训题单。

## 2. 已定 vs 未定（决策状态表）

| 决策包 | 状态 | 内容摘要 | 权威文本 |
|---|---|---|---|
| D0（2026-09-02） | 已批 | miles = 唯一开发与 GPU 资格候选（迁移结论等 GPU）；W1a 中立身份边界；W2a 可信输入/public-private 所有权；删除授权官僚设计但保留真实正确性挡板；A8 配置真实性 | `06-first-training-local-execution-plan.md` §1、§1.5 |
| D1（2026-09-02） | 已批 | 三终态（FATAL / ABORTED / DROP_GROUP）高层原则；组准入 = 全员 KEEP_FULL；A3 删 S1_TIER_CAP；unused handler 语义；两阶段 staleness（后被 B-1 改判为 consume-time 唯一权威） | 同上 §4、附录 A |
| A9（2026-09-02） | 已批 | private grading 材料共址于可信 RolloutManager 进程；模型执行始终在隔离 sandbox；不承诺进程被攻破后的内存隔离 | 同上 §1 A9 |
| D2 + B（2026-09-04，v2） | 已批 | D2-1 fresh grader + 冻结产物后立即释放容器；D2-2 唯一正式 rollout profile + 独立 grader profile，创建期强制 + 启动前探针 + run 级记录（**不再有逐轨迹能力事实**）；D2-3 可信评分投影（改测试路径 ≠ 篡改，控制面不重放）；D2-4 删 projection 扫描资格语义；B-1 staleness 以 miles consume-time 为唯一权威，N 为 profile 参数；B-2 drop + drop 事件 + no-progress；B-3 **最小**冷恢复（不建 joint commit/复合版本）；B-4 update interval=1；B-5 retract + 多 engine 最小正确性（W10）；B-6 落账 | `miles_spike/decision_package_D2_B.md`（v2） |
| **C 包** | **未定** | 首训 taskset 与规模档（D3，Claude 推荐纯 SWE-Gym Lite 150~200 题闭环档）；A5 timeout/truncation 处置；loss 终选（faithful DIS 为默认候选）；staleness N 起始值（建议 2）；GPU 拓扑与 engine 数（GPU matched comparison 定）；阈值/预算/停止规则；harness 工具面（subagent/compaction/fork）；eval 补充面 | 06 §4 C；`miles_spike/first_training_readiness_alignment_claude.md` §2.1（D3 建议） |

**三条长期原则**（外部建议若与之冲突会被直接拒绝）：
1. **不建授权官僚**：不写"owner 是否批准训练"的闸门/manifest/解封仪式（06 §6）；能否训练由 owner 判断。保留的是训练科学有效性校验（fail-closed、typed 错误、run-fatal）。
2. **不为边界情况建平台**：不建 ledger/WAL、通用规则引擎、常驻 supervisor、粘滞路由、dead-engine 恢复、监控平台；能删的机制优先删（2026-09-04 就删掉了每轨迹能力事实证明系统、第二套 staleness 阈值、projection marker 扫描）。
3. **红线**：不 fork miles 核心语义；miles 侧只允许窄 commit（现 0001–0016，全部存档并由 manifest 钉死）。

## 3. 该读什么、按什么顺序（含新鲜度）

**A. 权威且新鲜（先读）**
1. `06-first-training-local-execution-plan.md` — 执行计划权威：§1 决策包 A、**§1.5 改判记录**、§2 对旧计划的替换条款、§3 工作包表 W0~W10、§4 决策包 D1/D2/B/C、§5 下一步、§6 防御清理原则、**附录 A 终态判定**（注意 2026-09-04 修订注记）。
2. `miles_spike/decision_package_D2_B.md`（v2）— D2/B 已批全文，含 §0 "v1 的四处根本性缺失"（了解我们踩过的坑）。
3. `miles_spike/spike-log.md` — append-only 账本，决策表**新行在上**；每一批实现/复核/修复都有一行。想知道"某事为什么这样"先查这里。
4. `miles_spike/wave1/*.md` — 各工作包实现报告（w0、w1a、w1b_slice1/2、w2a、w3a、w3b、w4、w5a、w5b、w9、w10、wave3_precleanup），每份含 T1 决策、偏离、开放问题、测试证据，末尾有 append-only 的复核修正节。
5. `miles_spike/integration_base_manifest.json` + `miles_spike/patches/README.md` — miles 集成基座事实（pin f2b7c7929、分支 rh2-integration-v3、上游选材、16 个语义 patch 及 sha256、期望 tree、双 lane 期望计数）。
6. `collaboration-protocol.md`、`review-standards.md`、仓库根 `CLAUDE.md` — 协作/审查规则（T0/T1/T2 分级、五段收尾报告、A~N 审查维度）。

**B. 设计背景（需要理解"为什么"时读）**
- `docs/harness_improve/repo_harness_design_doc2_verifiers_based.md`（主架构）、`repo_harness_final_review_before_implementation.md`（范围与治理定案）。
- `docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md`（为什么 GRPO + faithful DIS）、`repoharness_validation_experiment_design.md`（E 系实验定案，顶部有 miles 迁移修订注记）、`RL训推不一致与重要性采样基础.md`。
- `miles_spike/formal_first_training_readiness_scope.md`（codex 就绪范围稿，顶部横幅说明已被 06 取代）、`gpu_spike_scope_v1_claude.md`（GPU 上必须验什么、为什么本地验不了）。

**C. 已过时或仅作历史（不要据此判断现状）**
- `00-project-status.md`：2026-07 快照，顶部有 2026-09 注记；"FA 自建线"章节已冻结。
- `05-fully-async-execution-plan.md`（slime 自建 FA 线，剩余面已被 06 §2 取代）、`04/03/01`、`s0/ s1/ s2/ fa/` 目录：历史阶段流水。
- `README.md`：V4 时代描述；`AGENTS.md` 的"当前进度"章节部分过时（其协作协议摘要仍有效）。
- `rh2/experiments/miles_gpu_spike/`：未审的实验脚本草案，W7 会从范围反向重生成（W10 已删其单 engine 硬约束）。

## 4. 代码地图（rh2/src/repoharness2）

| 包 | 职责 | 关键文件 |
|---|---|---|
| `contracts/` | 公共 schema（改动 = T0） | `eligibility.py`（七维事实 + 三档资格）、`fa_runtime.py`（Outcome v2、终止类别五族）、`finalization.py`（receipt）、`trajectory.py`、`handshake.py` |
| `envpack/` | 可信输入 | `ingest_swegym_lite.py`（完整 loader，四面含 golden，**只能由 trusted controller 调**）、`training_view.py`（TrustedTaskController → RolloutTaskView / HostGradingView，opaque digest 锚）、`trusted_prep.py` + `prepared_tasks.py`（一次性 prep → prompts.jsonl + runtime-private grading artifact + 外部 manifest SHA）、`termination_facts.py`（只读派生） |
| `grading/` | fresh grader | `manager.py`（SWEGradingManager：root trusted setup → 权限布置 → 候选非 root 只跑测试；自证读回）、`trusted_projection.py`（候选 delta vs 控制面拆分）、`queue.py` |
| `governance/` | 资格与准入 | `gate.py`（七维 eligibility，security 维 = 执行级事实，第七维 = 版本事实合法）、`admission.py`（KEEP_FULL / DROP_GROUP / FATAL 薄处置纯函数，disposition 未注入即 fail-fast）、`wrapper.py`（finalize_rollout） |
| `adapters/slime/` | 执行编排（vendored slime 之上） | `generate.py`（RolloutOrchestrator：materialize → 屏障 → 冻结产物 → 评分 → 交付；sandbox 创建路径也在这里）、`bringup.py`（BringupService：启动核对、prepared 任务面、profile、关停链入口）、`sandbox_profile.py`（唯一正式 rollout/grader Docker profile、探针、egress relay）、`capture_wire.py`（模型调用捕获与 abort）、`engine_router_client.py`（abort 广播）、`prepared_task_face.py`、`attempt_timing.py` |
| `adapters/miles/` | miles 接线 | `generate_fn.py`（Rh2MilesGenerateFn 入口）、`identity.py`（六字段身份铸造，PENDING/ABORTED 状态规则）、`canonicalize.py`（30 字段 fail-closed 映射）、`group_admission.py`（miles dynamic filter = 唯一组准入点，叶版本绑定）、`faithful_dis_loss.py`（custom loss，CP>1 已接）、`attempt_assignment.py`、`drop_events.py` |
| `shutdown/` | 关停链 | `chain.py`（有界十步）、`resource_closure.py`（估计口径）、`run_residue.py`（launch trap） |
| `training/` | 标量权威 | `faithful_dis.py`（DENOMINATOR_SEMANTICS_V1，**不得改**） |
| `rh2/src/slime/` | vendored slime agent 层，与 pin 逐字节一致，**不得改** | — |
| `reference/miles-rh2-integration/` | miles fork 分支 rh2-integration-v3（pin + 16 patch）；改动只能以窄 commit + 存档 patch 形式 | `miles/rollout/fully_async_*`, `miles/utils/rh2_*` |

**测试与验证**（在 `rh2/` 目录）：
```bash
uv run pytest tests/ -q                                             # 默认 pin base（2026-09-05：1761 passed / 310 skipped）
RH2_MILES_PATH=$PWD/../reference/miles-rh2-integration uv run pytest tests/ -q   # integration base（2069 passed）
bash scripts/miles_integration_lanes.sh                             # 正式双 lane：tree/patch digest/pin 校验 + 精确计数（lane A 358/310，lane B 668/0）
```
真实 Docker 测试（sandbox profile、grader 权限）在本机 Docker 上真跑；GPU 相关（CP=2 真机、多 engine e2e、retract 代价）只能在租卡时验。

## 5. 诚实的边界与开放项

- **Wave3 闭合口径**：只声称 exact official-file 边界（official test 文件在位内容不可改、应缺路径不可重建；当前 profile 对 official patch 删除/改名后仍缺失的路径 fail-closed，216 题冻结集为新增 8/删除 0/改名 0）。**通用 evaluator 控制面**（glob-only 辅助文件、conftest.py/pytest.ini/plugin）尚未定义，须由最终 environment adapter 在 taskset 确定后声明并实测——在此之前不得据本地绿灯宣称首训 reward 可信。
- **数据线未闭合**：T2-d（v2 评分正链：official test_patch 后写 + vendor eval_cmd + SWE-Gym parser 的真实镜像验证）、T2-e（四门 runner）、W2b（真实数据进训练）、held-out 冻结、GPU pass-rate 预筛。官方 swebench 4.1.0 对 SWE-Gym 11 仓库零覆盖，216 题 eval 常量来自 vendored fork。
- **租卡前必闭合**：R1 容器可写层预算强制（现只记录未强制）；launch.sh 的重启入口（`RESUME_FROM`）；W7 judge 消费 `run_restarted`/`engine_versions_after_publish` 事件；P2-2 新 run 必须唯一 run_id；W9 的真机 CP=2（含 `normalize_advantages=false` 约束）。
- **不做清单**（明确）：microVM、透明代理、LLM claim-check、完整红队、pending replay/精确 cursor/exactly-once、joint checkpoint、复合版本身份、粘滞路由、dead-engine 恢复、通用 quota/monitor 平台。

## 6. 术语速查

- **fa_formal / fa_audit_only / s1_compat**：执行模式。formal = 正式训练链（真身份、真准入、真 profile）；audit_only = 探针；s1_compat = 冻结的旧兼容路径。
- **六字段身份**：`rh2_prompt_group_id / rh2_group_index / rh2_rollout_execution_id / rh2_member_slot / rh2_physical_attempt_id / rh2_physical_attempt_seq`。
- **三终态**：FATAL（结构/账实矛盾，停 run）、ABORTED（未形成 present 对象的 task-local 故障，miles handler 按 drop 处理）、DROP_GROUP（完整但不合格，复合 filter 整组丢弃）。
- **faithful DIS**：在采样支持集上重归一化的重要性采样校正；标量权威 `training/faithful_dis.py`；custom loss 经 miles `--custom-loss-function-path`。
- **weight-version spans**：每 token 的行为策略版本区间（miles patch 0008/0009），staleness = 消费时已发布版本 − 组内最老版本。
- **prepared artifact**：trusted-prep 产出的 prompts.jsonl + runtime-private grading artifact + 外部 manifest SHA；rollout actor 只读它，不调完整 loader。
- **runtime_profile_digest**：run 级 sandbox profile 参数摘要，样本只盖这一个键供 join（不是逐轨迹能力事实）。

## 7. 给外部模型的提问边界

有价值的输入：首训 taskset 与规模档的取舍（D3）、evaluator 控制面的通用定义、GPU profile/拓扑与 staleness N 的实验设计、eval 补充面、faithful DIS vs PPO 在首训的取舍证据。
不需要的输入：重新设计训练后端或 harness、引入新服务/平台/依赖、为边界情况增加治理层、把已批的最小合同（B-3、D2-2）重新复杂化。
