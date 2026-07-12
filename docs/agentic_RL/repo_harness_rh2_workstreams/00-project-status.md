# rh2 项目进度总览（状态快照：2026-07-12）

> **本文档的用途**：给项目所有者和任何新接手的 agent 一份"当前我们在哪、已经完成什么、证据在哪、接下来做什么"的单一入口。每个结论都标注了证据文件路径，可以直接点开核对。
>
> **维护约定**：每个阶段收口时更新本文（与 `AGENTS.md` 的阶段状态区同步）；两者不一致时，以 `git log --oneline` 和各阶段 acceptance summary（JSON 账本）为准。

---

## 1. 项目一句话定位

**RepoHarness rh2 = 架在工业训练后端之上的"环境生产 + 训练治理层"**：verifiers v1 做环境基座、slime 做训练后端（这两样是拿来用的），自建的部分是**环境生产线（含质量门槛）、评分隔离、反作弊、训练资格治理（EligibilityGate）、后端中立投影（TrajectoryProjection）**——最终用一次真实的 coding-agent RL 训练（Qwen3-30B-A3B MoE + Claude Code harness + SWE 任务）证明这套基建可用。

总设计文档：`docs/harness_improve/repo_harness_design_doc2_verifiers_based.md`（下称"设计文档 2"）。

## 2. 全局路线图与当前位置

```text
S0 可行性验证            ✅ 已完成（V1~V4 全过；Form B 定为训练主线）
S1 端到端最小闭环        ✅ 已完成（S1-0~9 全验收；检查点 2 已由用户确认
                            2026-07-11，闸门 pending 注记已摘除）
P1 数据冻结包 v0.1       ✅ 已完成（即"训练数据预处理"，codex 线程执行）
P3 八卡预实验            ✅ 已完成（2026-07-08/09 真机，机器已释放。准确口径：
                            训练后端与架构决策完成；formal J4 严格绿灯
                            留待 FA-3 batch 准入落地后随合并短租复验）
FA fully async 训练链    🔨 进行中 ← ★ 第一实施工作流（05 计划，FA-0~5；
                            用户 2026-07-12 定案 fully-async-first）。
                            FA-0 ✅ 已完成（四契约 + 真实 weight_version 管道 +
                            正式链启动断言 + D-FA-6 硬事实 + 表面契约测试，
                            测试 647→684；notes：fa/implementation-notes.md）。
                            下一步：FA-3 离线部分 ∥ FA-4 对拍（可并行）→ FA-1/2
S2 SWE-Safety 加固       ⏳ 计划草案（S2-0b 已迁出），与 FA 并行，尚未开工
S3 训练治理完备          未开始（三档资格全量、环境验证四门收尾）
S4 正式训练实验          未开始（before/after 实验，简历叙事收尾）
S5 第二后端 + 服务化     按需（verl adapter、EnvServer 服务化）
```

注意 P1 / P3 是穿插在 S 系列之间的独立工作流：P1（数据冻结）为 S2 的数据 ingestion 备料；P3（8 卡预实验）关闭 S1 递延的训练侧未知，为 S4 排雷。两者都不在 S0~S5 的编号序列里。

## 3. 已完成工作详情



### 3.1 S0 可行性验证（已完成）

**回答的问题**："这条技术路线物理上走得通吗？"四项验证全过：


| 验证                     | 结论                          | 证据                                            |
| ---------------------- | --------------------------- | --------------------------------------------- |
| V1 verifiers 依赖与用法     | pass（pin + 契约测试）            | `s0/contract_baseline.md`、`s0/deps_report.md` |
| V2 renderer 逐 token 保真 | pass（Qwen3Renderer 12+12 项） | `s0/v2_renderer_report.md`                    |
| V3 协议 token 保真         | pass                        | `s0/v3_protocol_report.md`                    |
| V4 MoE 张量透传            | pass，**Form B 定为主线**        | `s0/topology_ab_report.md`                    |


（本节路径均相对 `docs/agentic_RL/repo_harness_rh2_workstreams/`，下同。）

另有 SWE smoke（8/8 跑通、7/8 resolved，`s0/swe_smoke_report.md`）与实验设计收口（`s0/s0_8_expdesign_review.md`）。账本：`s0/s0_acceptance_summary.json`。

**Form A / Form B 是什么**（后文反复出现）：A = verifiers TrainClient + vLLM 协议 shim；B = slime `custom_generate` 直调 SGLang（slime patch 镜像，能拿到 routing tape 和 top-p tape）。S0 定案：**B 是训练主线**，A 保留为协议基线/调试路径。

### 3.2 S1 端到端最小闭环（已完成，刚收口）

**回答的问题**："从 Claude Code harness 跑 SWE 题，到轨迹投影、评分、资格治理，再到 slime 真实训练 step，整条链是不是真的（token 级保真地）通了？" 答案是通了。十个任务：


| 任务        | 一句话                                                                                          | 关键证据                                      |
| --------- | -------------------------------------------------------------------------------------------- | ----------------------------------------- |
| S1-0      | U-H 探针：slime 官方镜像在 sm_120 跑 30B + top-p tape 可用，镜像 digest pin                                | `s1/uh_probe_report.md`                   |
| S1-1(+1b) | 契约层 15 个 schema + 六处泄漏收紧                                                                     | `s1/contracts_object_guide.md`            |
| S1-2      | 框架中立 envpack 库 + **frozen_v1（8 题 SWE-bench Verified 冻结集）**                                   | `s1/envpack_freeze_v1.md`                 |
| S1-3      | `project_from_slime` 主线投影 adapter                                                            | `rh2/src/repoharness2/adapters/`          |
| S1-4      | SWEGradingManager（P1~P11 故障矩阵 + 双沙箱 clean grading）                                           | `s1/grading_p_matrix.md`                  |
| S1-5      | TrainingEligibilityGate 七维 + finalize wrapper 唯一入口 + `S1_TIER_CAP`                           | `rh2/src/repoharness2/governance/`        |
| S1-6      | slime `custom_generate` 编排 glue（Form B 主线拼装）                                                 | `rh2/experiments/s1_7a_bringup/glue.py`   |
| S1-7a     | **真实 slime 循环跑通 debug transport step**（Qwen3-4B dense，2 个 optimizer step，checkpoint 用后即弃留证）  | `s1/bringup_7a_report.md`                 |
| S1-7b     | 30B 全要素训练 step → 递延给 P3 → **P3 已关闭**                                                         | `preflight/preflight_report.md` §1        |
| S1-8      | 离线导出 + verifiers 投影 + 双 parity PASS；**发现导出器对 thinking 模型真实轨迹全量 fail-closed 拒绝** → 登记为 S2 阻塞项 | `s1/parity_report.md`、`s1/s2_blockers.md` |
| S1-9      | 收口：inspector 账本、三处阻塞登记、闸门翻转                                                                  | `s1/s1_final_review.md`                   |


**账本与复核**：`s1/s1_acceptance_summary.json` 由 `rh2/src/repoharness2/inspect_s1.py` 生成/校验（digest 覆盖 22 个 evidence 文件 + 51 个代码文件）。任何 rh2 提交前跑 `cd rh2 && uv run inspect-rh2-s1` 必须 PASS。测试基线：**647 个 pytest 全绿**。

`s1/s2_blockers.md` **的来历**（用户 2026-07-09 问过）：这是 **S1-9 收口时建档的**（commit `f9181997`），内容是 S1-8 实测发现的导出器问题——线性追加式 token 重建假设被 Claude Code 的 thinking 块剥离行为打破，真实轨迹全部 `token_reconstruction_mismatch` 拒绝（fail-closed 按设计工作，但意味着离线导出/warm-start 对 thinking 模型暂不可用）。它是三处登记之一（另两处：acceptance summary 的 `blockers` 字段、`s1/implementation-notes.md`），按"显式登记、不淡化"的纪律留下的。

### 3.3 P1 数据冻结包 v0.1（已完成——即"训练数据预处理"）

**回答的问题**："正式训练/评测用什么数据，如何保证不污染评测面？" 由实验设计线程 + codex 执行（commit `bc3ae7d5`，2026-07-08），DF-1~DF-8 全部完成。目录：`data_freeze/`。

关键数字与产物：

```text
静态门漏斗：SWE-Gym Lite 230 → 剔 held-out 仓库 12 → 剔质量 fail 2
           → 存活 216（等 S2-1 环境四门 + GPU pass-rate 预筛后出 bring-up 题单）
held-out 候选：542 题（tornado 261 / pyramid 189 / hydra 66 / bokeh 26）
           → 走四道门后冻结 T=50~80 作为自建评测面（流程：heldout_proposal.md）
治理证据：hints 剥离中和了 47.4% 的题面泄漏（LLM 语义层全查，人工校准 15/15）
数据 pin：四数据源真实 HF revision + 24 项 artifact digest（freeze_manifest_v0.json）
磁盘警示：Lite ~0.5TiB / SWE-Gym Full ~5.3TiB / R2E ~2.3TiB（高于早期粗估）
```

**与 S1 的 8 题冻结集的关系（容易混）**：S1-2 的 frozen_v1（8 题，来自 SWE-bench Verified）只是**基建验证探针**，P3 也用它；正式训练数据来自 data_freeze 的 216 存活题（SWE-Gym Lite，与 Verified 仓库级不相交），评测面 = 自建 held-out（542 候选中冻结 50~80）+ Verified 只作外部参考。所以 `rh2_formal_training_allowed` 闸门保持 false：8 题 Verified 探针**不允许**用于正式训练。

遗留（登记在 `data_freeze/data_freeze_report.md` 末节）：GPU pass-rate 预筛（S3/S4 前单卡作业）、两条勘误待回写实验文档附录 B（Lite 是 230 不是 234；SWE-Gym 镜像命名是 `_s_` 不是 `_1776_`）、R2E 打标推迟到 success-run 题单确定时。

### 3.4 P3 八卡预实验（刚完成，机器已释放）

**回答的问题**："8×RTX PRO 6000（sm_120，PCIe 无 NVLink）这个训练形态到底行不行，数值是多少？" 2026-07-08/09 真机执行（codex ~7h + orchestrator 接手 ~2h）。**收口判定全文：**`preflight/preflight_report.md`（每个未知的绿/黄/红灯 + 依据），原始过程记录：`preflight/p3_remote_experiment_handoff_20260708.md`，证据 19MB：`preflight/remote_evidence_20260708/`。

一句话结论 + 关键数字：

```text
训练侧全绿：Megatron on sm_120 ✓、PCIe all-to-all ✓（actor_train 174s）、
  CPU offload ✓（4528 tok/s）、30B 真实训练 step + 权重同步 ✓（11.45s@512MB）
S1-7b 关闭：routing tape + top-p tape 首次真实进 loss（J4 replay + J5 online）
放置定案：T3 分离（4 训 + 4 推）+ train_async 双缓冲；
  废弃早期"必须 colocate"推论（colocate 只省 0.8%/step，换不回重叠窗口）
整 step 实测 23min（rollout-bound，wait_ratio 0.82）→ C3 反推 30~50 步 ≈ 12~19h，
  远低于"首训 ≤4 天"预算
尾部空闲 26~28% > 25% 注册阈值 → fully_async 升级触发条件成立（但首训不需要）
唯一没拿到的严格绿灯：formal J4 在线端到端——根因已定位为
  "治理过滤后 batch schedule 对齐"（纯本地 Python 可修，不需要 GPU 复现）
```

实测数值已回填实验设计文档 `docs/agentic_RL/training_design/repoharness_validation_experiment_design.md` **§4.2**（该节是 C1/C3/E6 的实测锚点）。S1 acceptance 三条递延项已改判 `closed_by_p3_20260708`（commit `28a7d91f`）。

## 4. 闸门状态（真实值，出处 `s1/s1_acceptance_summary.json` 的 gates 字段）


| 闸门                            | 值     | 说明                                                                                                                                              |
| ----------------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `rh2_s0_complete`             | true  | S0 全部完成                                                                                                                                         |
| `rh2_s1_closed_loop`          | true  | 检查点 2 已由用户确认（2026-07-11），pending 注记已摘除；gates 字段保留 `checkpoint2_confirmed_by_user_20260711` 作为审计痕迹 |
| `rh2_s2_signal_trusted`       | false | S2 的退出闸门                                                                                                                                        |
| `rh2_formal_training_allowed` | false | 正式训练总闸门；8 题 Verified 探针不得用于正式训练                                                                                                                 |




## 5. 遗留问题与阻塞项总表（全项目合并视图）


| #   | 事项                                                                                                                            | 来源         | 归属                 | 状态                                                              |
| --- | ----------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------ | --------------------------------------------------------------- |
| 1   | ~~用户检查点 2 确认~~                                                                                                     | S1-9       | 用户                 | ✅ 已确认（2026-07-11），注记已摘除                                   |
| 2   | **batch schedule 准入 + fan-out 正规化 + 层次化 GRPO 归一化（问题 A~E）**（formal J4 严格绿灯的唯一阻塞；J5 gbs20 保留 36≠32 已实测踩中 slime 单组回退，P3 的有限 loss 不证明组归一化语义正确） | P3 + codex 轮次 2     | **FA 工作流（05 计划 FA-0/1/3；2026-07-12 自 S2-0b 迁入）** | FA-3 离线部分可先行；验收用 J4 事件元数据夹具（**本地无 .pt 张量**）+ 与真 `build_dp_schedule` 差分验证 |
| 3   | **导出器分叉感知重建**（thinking 模型轨迹离线导出 0 可用。依赖澄清：它阻塞的是 E3 的**同策略 token 级回收路径**，不阻塞 teacher-SFT 路径——后者的前置是 SemanticSFT 契约，见 G9）                                                                 | S1-8       | S2-6（S2 侧起点，与 S2-1 并行）               | 待实现，技术方案在 `s1/s2_blockers.md`；验收资产需改判（G8：60+65 条 .pt 不在本地）                                 |
| 4   | ~~fan-out 形状正式方案~~                              | P3         | 并入 FA-1（三视图交付边界）        | ✅ 方向已定：内部三层结构 / rollout-filter 视图保留组外层 / converter 平铺 + 身份回链；不给 slime 打零散补丁                                           |
| 5   | pause_generation 对在途请求 abort/hold 语义 + CC 原生重试行为实证（原 gap ①收窄版；proxy 更新窗口逻辑 D-FA-3 的经验基础）                                                                                    | P3 + FA 设计         | **FA-5 短租实证项**（05 计划 §1）  | 2026-07-12 起 fully async 即正式主线；该实证决定 proxy 分支最终形态                                                       |
| 6   | data_freeze 遗留：GPU pass-rate 预筛 / P5 两条勘误回写附录 B / R2E 打标                                                                      | P1         | S3/S4 前            | 已登记                                                             |
| 7   | S2 计划 G 系列决策：G1~G5（无异议即按推荐执行）+ **G6~G10（P3 后新增，codex 复核意见，涉及既有任务修改）**                                                                                                 | S2 计划 §5   | 用户（下一轮）                 | 待确认                                                             |
| 8   | 下次租卡 = **FA-5 + S2 G10 合并短租**：FA 六项集成验收 + strict J4 复验 + abort 语义实证 + M1 多步分布 + 真实在线拦截链 + 代表性轨迹留存（兼供 #3 复验）                                                                           | FA + S2 计划 | 下次 GPU 窗口          | 一次短租、两份验收账目、两个闸门独立记账                                                   |
| 9   | **SemanticSFT 导出契约**（新设计缺口：teacher 异构模型 → Qwen SFT 需要结构化语义导出，当前只有 token-faithful 出口）                                                                           | codex 复核 2026-07-10 | G9（下一轮定）          | 建议 S2 定契约 + 最小闭环，批量生产放 S3                                                   |




## 6. 下一阶段：S2 概览与待决策项

**FA 工作流（第一实施工作流，用户 2026-07-12 定案 fully-async-first）**：`05-fully-async-execution-plan.md`。正式训练链 = **version-aware fully async + faithful DIS**（P3 实测尾闲 26~28% 触发升级阈值；GRPO 保持首训算法，DIS 是正确性组件而非可选增量）。任务：FA-0 身份/版本/执行结果契约 → FA-1 持续 worker + proxy 边界（权重更新 abort → **proxy 级 turn 重生成**，用户已拍板）→ FA-2 PromptGroupAssembler + 合格组队列 → FA-3 SlimeBatchAssembler + `build_dp_schedule` 差分预检（原 S2-0b 问题 A~E 迁入，离线部分可先行）→ FA-4 faithful DIS + 逐 token 对拍 → FA-5 故障注入 + 短租集成验收。eval 首版定案：**训中不评，只 before/after**。退出闸门 `rh2_fully_async_training_path_verified`；估计 16~24 人日本地 + 1 次短租。设计依据：`fully_async_rollout_pipeline_design_discussion.md`（codex）+ `training_design/repoharness_sao_dis_grpo_ppo_analysis.md`（算法定案）。

**S2 执行计划（草案，与 FA 并行）**：`04-s2-execution-plan.md`。目标不变：把 S1 闭环加固到"训练信号可信"。S2-0b 已迁出；S2 侧起点 = S2-6 导出器重建与 S2-1 数据 ingestion 并行 → S2-2 安全 Runtime → S2-3/4 anti-cheat → S2-5 红队环境包 → S2-7 TIER_CAP 解除 → S2-8 验收。S2 的 GPU 段（G4/G10）与 FA-5 合并为同一次短租。G1~G10 决策仍待下一轮。`rh2_formal_training_allowed` = FA 闸门 ∧ `rh2_s2_signal_trusted`。

## 7. 文档地图（新接手者按层查找）

```text
【第 0 层：入口】
  本文档                                        当前进度 + 全部指针
  AGENTS.md（仓库根）                            协作纪律 + 阶段状态 + 闸门

【第 1 层：设计定案】docs/harness_improve/
  repo_harness_design_doc2_verifiers_based.md   总设计（架构/契约/决策 D 系列）
  repo_harness_final_review_before_implementation.md  实施前范围定案评审
  repo_harness_implementation_plan_v1.md        实施计划总纲（S0~S5 划分）

【第 2 层：训练实验设计】docs/agentic_RL/training_design/
  repoharness_validation_experiment_design.md   E/C 系列定案 + §4.1 S0 实测锚点
                                                + §4.2 P3 实测锚点（最新）
  repoharness_sao_dis_grpo_ppo_analysis.md      算法定案（GRPO 首训 + faithful
                                                DIS 正确性组件；PPO/SAO/
                                                CompactionRL 分期路线）
  repoharness_validation_experiment_design_review.md  （已经不需要了，看最终的实验设计文档即可）
  RL_algorithm_design.md / warm_start_offline_data_filtering_design.md

【第 3 层：执行计划】docs/agentic_RL/repo_harness_rh2_workstreams/
  01-s0-execution-plan.md / 02-s0-conclusions-and-architecture.md
  03-s1-execution-plan.md / 04-s2-execution-plan.md（草案，S2-0b 已迁出）
  05-fully-async-execution-plan.md（FA-0~5，第一实施工作流）
  fully_async_rollout_pipeline_design_discussion.md（FA 设计讨论稿，codex，
    机制分析与对象模型的权威出处）

【第 4 层：阶段证据】docs/agentic_RL/repo_harness_rh2_workstreams/
  s0/   → s0_acceptance_summary.json 为账本，各 V 报告
  s1/   → s1_acceptance_summary.json 为账本（inspect-rh2-s1 生成/校验），
          s1_final_review.md（判定）、s2_blockers.md（阻塞登记）
  data_freeze/ → data_freeze_report.md（收口）、freeze_manifest_v0.json（24 项 digest）
  preflight/   → preflight_report.md（P3 收口判定，先读这个）、
          8gpu_preflight_protocol.md（协议）、p3_remote_experiment_handoff_20260708.md
          （过程实录）、slime_fully_async_upgrade_design.md（升级设计）、
          implementation-notes.md、remote_evidence_20260708/（19MB 证据）
  s2/   → codex_reviews.md（codex 两轮复核意见的受版本控制存档——
          tmp/ 被 .gitignore，正式引用一律指向这里）
  tmp/  → 外部顾问意见草稿箱（gpt5.5pro 等），gitignore 不入库，只读参考

【第 5 层：代码】
  rh2/src/repoharness2/     contracts / envpack / grading / governance /
                            taskset / adapters{slime, offline_export,
                            verifiers_projection} / inspect_s1.py
  rh2/experiments/          s1_7a_bringup（Form B glue）、p3_preflight（J 系列脚本）
  rh2/tests/                647 个测试
  reference/                外部参考库（slime pin、verifiers、verl 等，勿改）
```



## 8. 协作纪律与安全约束（对所有接手 agent 生效）

1. **账本纪律**：任何 rh2 相关 commit 前跑 `cd rh2 && uv run inspect-rh2-s1` 必须 PASS；改动被 digest 追踪的文件时，同一 commit 内先改文件、再 `--write --pytest-count <N>` 重生成账本、verify 后提交。此纪律来自三次账本漂移事故（见 `s1/implementation-notes.md` S1-9 条目）。
2. **notes 三节制**：每阶段 `implementation-notes.md` 记设计决策/偏离/权衡/开放问题，只记重要事项。
3. **密钥安全**：deepseek key 在 `deepseek_api.md`（已 gitignore）；一切文档/evidence/代码**只允许引用路径，绝不允许出现 key 内容**。vastai SSH key：`~/.ssh/vastai_ed25519`（`-o IdentitiesOnly=yes`）；verda 凭据：`~/.verda/credentials`。
4. **不碰**：`reference/` 子模块工作区、另一线程正在编辑的 `training_design/repoharness_validation_experiment_design_review.md`。
5. **checkpoint 纪律**：基建验证产生的模型 checkpoint 一律用后即弃并留删除证据（8 题 Verified 探针不得成为任何后续训练起点）。



## 9. 术语速查


| 术语                         | 含义                                                                                                    |
| -------------------------- | ----------------------------------------------------------------------------------------------------- |
| Form B                     | slime `custom_generate` 直调 SGLang 的训练主线接入形态（vs Form A = verifiers + vLLM shim）                        |
| tape                       | 采样期逐 token 记录：routing tape（MoE 每 token 每层 top-8 专家 id）与 top-p tape（截断集 token ids），训练侧 replay 用，保证训推一致 |
| fan-out                    | 一条 harness 轨迹树按 root-to-leaf 展开成多个训练样本（branch）。权威 reward 语义 = **整 reward 广播给每个 branch + rollout 级 loss 分母**（我方 adapter 实际行为，`generate.py:1727`）；旧文档 "reward/K 分摊" 说法源自 slime README，与源码不符，已废止（D-FA-7）         |
| 三层身份                    | PromptGroup（GRPO 归一化单位）/ RolloutExecution（batch 计数单位）/ Branch（共享 rollout_id，loss 按 rollout 聚合）——FA-0 契约         |
| faithful DIS                | 训练时按 current/rollout token logprob 比值加权/拒绝的重要性采样修正（论文语义自定义 loss，逐 token 对拍）；与 slime TIS/IcePop 近似分开命名；algorithmic mask 不改写 provenance loss mask         |
| TrajectoryProjection       | 后端中立的轨迹投影契约（slime/verifiers 两路都汇入它，tape 解码只在这一层做一次）                                                   |
| EligibilityGate / TIER_CAP | 训练资格治理：七维检查决定样本能否进 loss；`S1_TIER_CAP` 是 S1 期的资格上限（S2-7 解除后才能发放 `online_policy_loss_eligible`）         |
| U-C / U-H                  | 未知项编号：U-C = 多卡训练侧四未知（P3 已关）；U-H = slime 镜像在 sm_120 可用性（S1-0 已关）                                       |
| J0~J5 / J4b / J4c          | P3 作业序列：环境检查/带宽/推理画像/合成训练/端到端/放置对比/fully_async 冒烟/权重同步                                                |
| V / E / C / DF / G 系列      | 分别为 S0 验证项、实验设计决策项、硬约束、数据冻结任务、S2 待决策项的编号前缀                                                            |
| batch schedule alignment   | P3 主要教训：治理过滤后可训练样本数须对齐 `dp_size × mb_group`，否则 slime `build_dp_schedule` 断言失败；须做纯 Python 准入预检         |
| 账本（ledger）                 | 各阶段 acceptance summary JSON：digest 锁定 evidence + 代码，inspector 四步范式校验，防静默漂移                            |
