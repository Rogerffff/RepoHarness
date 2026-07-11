# rh2 项目进度总览（状态快照：2026-07-09）

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
P3 八卡预实验            ✅ 已完成（2026-07-08/09 真机，机器已释放）
S2 SWE-Safety 加固       ⏳ 计划已写（草案），尚未开工 ← ★ 我们在这里
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
| 2   | **batch schedule 准入 preflight/repair**（治理过滤后样本数须对齐 `dp_size × mb_group`，否则 slime `build_dp_schedule` 断言炸；formal J4 严格绿灯的唯一阻塞） | P3 新发现     | S2（**尚未写进 S2 计划**） | 待实现，纯本地，设计草稿见 handoff §7.2 + `preflight/preflight_report.md` §3 |
| 3   | **导出器分叉感知重建**（thinking 模型轨迹离线导出 0 可用，E3 warm-start 回退预案的前置依赖）                                                                 | S1-8       | S2-6               | 待实现，技术方案已写在 `s1/s2_blockers.md`                                 |
| 4   | fan-out 形状正式方案（我们的嵌套 `list[list[Sample]]` 打崩 slime 两条路径：dynamic_filter 和 fully_async 消费侧 `_key`）                              | P3         | 建议并入 #2 一起做        | 待决策：交付时展平 vs 补丁 slime                                           |
| 5   | ABORTED 组重入实证（fully_async 缺口①，P3 未观测到，非否定）                                                                                    | P3         | fully_async 升级实施期  | 注入式测试，不租卡                                                       |
| 6   | data_freeze 遗留：GPU pass-rate 预筛 / P5 两条勘误回写附录 B / R2E 打标                                                                      | P1         | S3/S4 前            | 已登记                                                             |
| 7   | S2 计划 G1~G5 决策确认（"无异议即按推荐执行"）                                                                                                 | S2 计划 §5   | 用户                 | 待确认                                                             |
| 8   | 下次租卡捆绑包：formal J4 严格绿灯复验（#2 修好后）+ S2-7 在线拦截 G4 实机证据                                                                           | P3 + S2 计划 | 下次 GPU 窗口          | 几小时短租，不是完整 P3                                                   |




## 6. 下一阶段：S2 概览与待决策项

S2 执行计划（**草案**）：`04-s2-execution-plan.md`。一句话目标：把 S1 闭环从"链路正确"加固到"**训练信号可信**"——退出判据 = 红队环境包全部被正确拦截 + `S1_TIER_CAP` 解除 + bring-up 数据 ingestion 完成。全程不需要 GPU。任务：S2-0 契约小项包 → S2-1 数据 ingestion + 环境四门（消费 data_freeze 的 216 题）→ S2-2 安全 Runtime → S2-3/4 anti-cheat → S2-5 红队环境包 → S2-6 导出器重建 → S2-7 TIER_CAP 解除 → S2-8 验收（`inspect-rh2-s2`）。

**关于"S2-6 导出器先做"（G0）的出处说明**：S2 计划 §5 把 G0 记为"用户 2026-07-09 指定"。实际经过是：当时用户在 S2 规划讨论中表达了"先清 S1 遗留阻塞项"的意向，计划据此把导出器（唯一的 S1 显式阻塞项）排为起点。用户后来（2026-07-09 晚）表示不记得做过这个具体指定且尚未读过 S2 计划——**因此 G0 应视为可重议**。当前的重排建议（orchestrator，P3 结论出来之后）：**把 #2 batch schedule 准入放在导出器之前**作为 S2 第一个实现任务，理由是它阻塞训练主线（导出器只阻塞回退预案）、体量小（1~~2 天 vs 3~~5 天）、可用 P3 真实 rollout dump 离线验证、且决定下次租卡效率。等用户拍板。

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
  repoharness_validation_experiment_design_review.md  （已经不需要了，看最终的实验设计文档即可）
  RL_algorithm_design.md / warm_start_offline_data_filtering_design.md

【第 3 层：执行计划】docs/agentic_RL/repo_harness_rh2_workstreams/
  01-s0-execution-plan.md / 02-s0-conclusions-and-architecture.md
  03-s1-execution-plan.md / 04-s2-execution-plan.md（草案）

【第 4 层：阶段证据】docs/agentic_RL/repo_harness_rh2_workstreams/
  s0/   → s0_acceptance_summary.json 为账本，各 V 报告
  s1/   → s1_acceptance_summary.json 为账本（inspect-rh2-s1 生成/校验），
          s1_final_review.md（判定）、s2_blockers.md（阻塞登记）
  data_freeze/ → data_freeze_report.md（收口）、freeze_manifest_v0.json（24 项 digest）
  preflight/   → preflight_report.md（P3 收口判定，先读这个）、
          8gpu_preflight_protocol.md（协议）、p3_remote_experiment_handoff_20260708.md
          （过程实录）、slime_fully_async_upgrade_design.md（升级设计）、
          implementation-notes.md、remote_evidence_20260708/（19MB 证据）
  tmp/  → 外部顾问意见存档（gpt5.5pro 等），只读参考

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
| fan-out                    | 一条 harness 轨迹树按 root-to-leaf 展开成多个训练样本（reward/K 分摊，共享 rollout_id）；我们交付嵌套 `list[list[Sample]]`         |
| TrajectoryProjection       | 后端中立的轨迹投影契约（slime/verifiers 两路都汇入它，tape 解码只在这一层做一次）                                                   |
| EligibilityGate / TIER_CAP | 训练资格治理：七维检查决定样本能否进 loss；`S1_TIER_CAP` 是 S1 期的资格上限（S2-7 解除后才能发放 `online_policy_loss_eligible`）         |
| U-C / U-H                  | 未知项编号：U-C = 多卡训练侧四未知（P3 已关）；U-H = slime 镜像在 sm_120 可用性（S1-0 已关）                                       |
| J0~J5 / J4b / J4c          | P3 作业序列：环境检查/带宽/推理画像/合成训练/端到端/放置对比/fully_async 冒烟/权重同步                                                |
| V / E / C / DF / G 系列      | 分别为 S0 验证项、实验设计决策项、硬约束、数据冻结任务、S2 待决策项的编号前缀                                                            |
| batch schedule alignment   | P3 主要教训：治理过滤后可训练样本数须对齐 `dp_size × mb_group`，否则 slime `build_dp_schedule` 断言失败；须做纯 Python 准入预检         |
| 账本（ledger）                 | 各阶段 acceptance summary JSON：digest 锁定 evidence + 代码，inspector 四步范式校验，防静默漂移                            |


