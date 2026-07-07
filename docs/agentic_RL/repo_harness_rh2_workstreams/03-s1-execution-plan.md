# 03 — S1 执行计划：端到端最小闭环（定稿 2026-07-09）

> **补充条款绑定**：`s1/s1_supplementary_clauses.md`（两复核线程建议 A1~A10/B1/C1~C3，2026-07-09 全部采纳）是本计划的正式附件，各任务小节标注的 A#/B#/C# 条款为**验收级要求**，与正文同等效力；冲突时以补充条款为准（更细）。F5 按用户收紧版定案。

输入：S0 全部结论（`02-s0-conclusions-and-architecture.md`）、实验层 E2~E9 定案（实验设计文档定案批准记录）、8 题题单已冻结（`s0/swe_smoke_report.md`）。退出闸门：`rh2_s1_closed_loop = true`。

S1 的一句话目标：**把形态 B 训练主链路和治理层从"设计"变成"可运行的最小闭环"**——一条 SWE 轨迹能从 slime custom_generate 出发，经物化→harness→评分→中立投影→资格门，合格样本进一个真实训练 step，全程 evidence 可审计。

协作纪律沿用 S0（implementation-notes 三节制、每任务一 commit、独立复核、两个人工检查点：S1-0 后与 S1-9 前）。

---

## 1. S0 → S1 的结构性输入（设计前提，不再讨论）

```text
1. 形态 B（slime 原生）是训练主线；project_from_slime 是主线交付物，
   project_from_verifiers 服务评测/导出（总纲原表述已过时，以本文为准）。
2. E2 定 top_p=0.95 → U-H（slime patch 镜像 on sm_120）是 S1 硬阻塞，
   必须第一个验证（S1-0）。回退梯：U-H 失败 → 临时 top_p=1.0 起跑
   （解耦镜像依赖，偏离配方，只作 bring-up 应急）+ 上报重议。
3. E10 定"训练=主评测同 harness 同栈"：主评测面 = 训练路径 eval 模式；
   verifiers 路径 = transfer scaffold 面 + 治理审计 + 协议基线。
4. tape 解码只在 projection 层做一次；renderer 加载必须断言类名（U-G）；
   /testbed 物化校验用血缘判据；taskset 插件 id 单段命名。
5. S1 闭环用已冻结的 8 题 smoke 集；bring-up run 训练数据
   （SWE-Gym Lite 100~200 预筛）是 S2 前的独立数据任务，不阻塞闭环（F3）。
```

---



## 2. 任务分解


| #    | 任务                                                 | 位置             | 硬依赖      |
| ---- | -------------------------------------------------- | -------------- | -------- |
| S1-0 | **U-H 验证（硬阻塞）**：slime patch 镜像 on Blackwell        | 单卡 GPU 短租      | E2       |
| S1-1 | contracts 先行：7 个 schema + 最小 inspector             | 本机             | —        |
| S1-2 | 环境包库抽取 + 8 题冻结固化                                   | 本机             | S1-1     |
| S1-3 | project_from_slime（主线投影 adapter）                   | 本机（fixture 驱动） | S1-1     |
| S1-4 | SWEGradingManager 最小版（P1~P11 对照）                   | 本机 docker      | S1-2     |
| S1-5 | Gate + EligibilityReport + 投影扫描                    | 本机             | S1-1/3/4 |
| S1-6 | slime 绑定：custom_generate 编排胶水                      | 本机写 + GPU 验    | S1-2~5   |
| S1-7 | 端到端 bring-up（分两档，见 F2）                             | GPU            | S1-0/6   |
| S1-8 | 离线导出 + project_from_verifiers + parity             | 本机             | S1-3/5   |
| S1-9 | 验收：inspect-rh2-s1 + acceptance summary + AGENTS 同步 | 本机             | 全部       |




### S1-0 U-H 验证（第一个动作，单卡 Blackwell 短租数小时）

拉 slime 官方 docker 镜像（含 sglang-top_p.patch 的那个）→ 在 RTX PRO 6000 上起 SGLang + Qwen3-30B-A3B → 复跑 S0-6 探针脚本（top_p=0.95 + return_top_p_token_ids + return_routed_experts）→ 断言 meta_info 同时含 top-p tape 与 routing tape 且与 token 对齐。产出 `s1/uh_probe_report.md` + 镜像 digest pin。失败即触发回退梯并停下来与用户讨论。

### S1-1 contracts 先行

`rh2/src/repoharness2/contracts/`：trajectory.py（TrajectoryProjection/BranchProjection/TokenSpan/LossMaskSpan/LogprobProvenance/RoutingTensorRef/SamplingMaskRef/RewardFacts）、**capture.py（GenerationCaptureRecord，A4：SGLang 客户端响应层的原始事实 sidecar——request/turn/trajectory id、backend 名与版本、sampling 参数、renderer 类名与 template hash、prompt/response token ids ref、raw meta_info digest、logprobs/top-p/routing refs、capture_status/alignment_status；TrajectoryProjection 引用它而非从训练后 Sample 反推审计事实）**、eligibility.py、grading.py、findings.py、anti_hack.py（schema 先行，S2 才接 filter）、**sandbox.py（A5：SandboxLease/WorkspaceHandle/HarnessLaunchSpec/ModelProxyEndpoint/CleanupPolicy——S1-6 握手契约的 schema 先行）**、handshake.py、timing.py。全部 pydantic `extra="forbid"` + 字段白名单常量（继承 L4/L5 marker 语义，**泄漏扫描字段名单含 golden_patch/test_patch/FAIL_TO_PASS/PASS_TO_PASS/hidden_verifier/grader_only，A6**）。配 `inspect-rh2-artifact` 最小校验命令 + schema 单测。**验收：合格/违规样例 fail-closed 单测 + `s1/contracts_object_guide.md`（A8：按对象生命周期讲——创建者/消费者/安全关键字段/fail-closed 行为/最小合法与非法样例，不是字段表）。**

### S1-2 环境包库抽取 + 冻结固化

把 S0-7 的 `SweSmokeTaskset` 拆成两层：**框架无关库**（`envpack/`：materialize 血缘校验、官方 parser 评分、题目数据 + digest）与 **verifiers 绑定**（Taskset 子类调库）。8 题冻结记录写进 `envpack/data/frozen_v1.json`（题单已经用户确认冻结，C2 状态已同步）。**bundle 拆分（A6，验收级）**：public task bundle（模型可见题面/repo/base_commit/镜像 digest/允许工具/公开提示）与 private grading bundle（test_patch/F2P/P2P/官方 parser 配置/golden 相关）分开存放、各自 digest；public bundle 过泄漏扫描（A6 字段名单）；private bundle 永不进 rollout 容器、public projection、SFT/export。**验收：verifiers 绑定跑 8 题结果与 S0-7 一致（回归）；库层单测不 import verifiers；两 bundle digest + 泄漏扫描通过。**

### S1-3 project_from_slime（主线投影）

输入 slime `Sample`/TrajectoryManager 输出（含 rollout_log_probs / rollout_routed_experts / top-p ids），输出 `TrajectoryProjection`。要点：tape 解码唯一实现点；loss mask 语义对齐 H4（sampled ∧ role）；compaction 分叉 → CompactedSubTraceLineage；renderer/tokenizer 事实进 LogprobProvenance（logprob_source 标注 M4）；U-G 守门（断言 renderer 类名的检查函数供 S1-6 启动期调用）。**S1 阶段用离线 fixture 驱动**（从 slime 数据结构手工构造 + S1-7a 真实产物回归），不需要 GPU。**验收：fixture 全绿 + S1-7a 真实 Sample 投影 round-trip 校验。**

### S1-4 SWEGradingManager 最小版

`grading/manager.py`（prepare/grade/gc）+ `grading/queue.py`（有界队列 P11，**首版并发 4/队列 8 可配置，F5 用户版**）。评分动作复用 S1-2 库层。**最小 patch hygiene（A7，验收级，不推迟到 S2）**：从 agent workspace 导出 cleaned final patch → fresh grading sandbox / clean checkout 上重放（S0-7 的同容器评分在此升级）→ 测试文件篡改、题面/运行时私有/grader-only 文件污染一律拒绝或降级 → 再跑官方 parser；patch_apply_failed / tests_failed / infra_failure 三分，infra_failure 绝不落 reward=0。P1~P11 逐条落测试或显式豁免表；五类计时埋点 + 容器峰值/队列等待记录（F5）。**验收：8 题经 manager 评分与 S0-7 结果一致；故障注入测试（杀评分容器→infra_failure；队列打满→反压事件；篡改测试文件→降级）。**

### S1-5 Gate + EligibilityReport + 投影扫描

`governance/gate.py`：七维事实合取 → 三档资格；S1 全程默认最高只发 `offline_or_sft_candidate`（安全加固未完成，fail-closed）；组修复信号接口（GRPO n=8 语义按 E2，降级须在组装配前对后端可见）。`governance/projection.py`：public projection 扫描（forbidden marker 继承）。EligibilityReport sidecar 与 Trace/Sample 以 id 关联。**验收：单测覆盖"任一维度失败即降级"“未知字段拒收”“绕过 gate 的路径不存在（wrapper 是唯一入口）"。**

### S1-6 slime 绑定（custom_generate 编排胶水）

`adapters/slime/generate.py`：实现 02 文档 §8 的 9 步生命周期——物化(库层)→Claude Code harness(slime 现成)→TrajectoryManager(slime 现成)→GradingManager→project_from_slime→Gate→合格 Sample 返回 slime。启动期跑 U-G renderer 断言 + U-H 探针断言（防镜像静默降级）。**sandbox 所有权握手（A5，验收级）**：进入编排实现前先落 S1-1 的 sandbox.py 契约实例——谁建容器、谁物化 /testbed、harness workdir 如何传入、模型代理地址注入、网络/权限策略归属、public/private bundle 挂载（private 不进 rollout 容器）、失败清理责任与清理失败的 FailureCategory 记录。**验收：mock SGLang 端点下编排单测全绿（含握手契约实例校验、清理失败注入）；真实验收在 S1-7。**

### S1-7 端到端 bring-up（拆两档，F2；A1/A2/A3 为验收级条款）

- **7a debug training transport step（单/双卡）**：Qwen3-4B（dense）+ slime 最小训练配置 + **S1-0 pin 的 slime patch 镜像**，8 题冻结集 **n=4（沿用 E2 生产配置；若降回 n=2 必须显式关闭动态采样并在报告标注 bring-up 偏离）**，采样 **top_p=0.95** 并沿用 E2 flags（disable-grpo-std-normalization、clip 0.2/0.28）。跑通 custom_generate 全链 → 一个真实训练 step。**定义（A1）**：这是 debug training transport step，只验证 custom_generate→projection→gate→trainer 的数据传输链路，不代表 online_rl_candidate 开放；**checkpoint 即弃**——产生的 checkpoint 不得作为任何后续训练/评测/warm-start/debug baseline 的初始权重，`s1_acceptance_summary.json` 记录该声明，`rh2_formal_training_allowed` 保持 false（8 题来自 Verified 仓库，复用会污染评测叙事）。验证点：loss mask/logprob/样本传输/gate 拒绝路径；**top-p tape 在真实循环中的生产、投影与消费**（A2——dense 只是没有 routing，top-p tape 照样要验）；routing 字段缺失时 projection 显式标注 `routing_not_applicable_dense_model`，不得静默成功。
- **7b 30B-A3B 全要素训练 step**：**并入 S4 前的 8 卡预实验**（与 U-C 一起关闭），不阻塞 S1 闸门。**S1 验收措辞（A3）**：S1 关闭的是"slime 形态 B 数据链路闭环"；30B 的 top-p/routing 服务端能力由 S1-0 探针背书；30B 全要素训练 step、多卡训练侧、routing tape 训练消费、显存与通信风险显式递延（acceptance summary 按 C3 记录递延清单）。



### S1-8 离线导出 + project_from_verifiers + parity

`adapters/offline_export/`：TrajectoryProjection → TrainingExportRecord（对接 warm-start 过滤契约）。`project_from_verifiers`：verifiers Trace → 投影（评测/导出路径用）。**parity 拆两类（C1）**：**parity-core**——slime 在线消费路径 vs offline export，同 renderer 同 projection，**token 逐位一致**（E8 解耦证据本体）；**parity-cross**——verifiers 路径 vs slime 路径，只比治理事实/RewardFacts/eligibility/logprob_source/provenance，token 不强求逐位（除非 renderer/tokenizer/template 全同）。**验收：两类 parity 各自脚本 + 报告。**

### S1-9 验收收口

`inspect-rh2-s1` 完整 inspector（四步范式：digest 重算/report 对照/白名单/marker 扫描，**并读取机器可读的 `uh_probe_result.json`，A10**）+ `s1_acceptance_summary.json`（**须含递延风险记录，C3/A3**：30B 全要素训练 step deferred_to_s4_pre_8card、U-C still_open、routing tape 训练消费未被 dense run 关闭、S1-7a checkpoint_discarded=true、rh2_formal_training_allowed=false）+ AGENTS.md 进度翻转 + implementation-notes 收口。闸门 `rh2_s1_closed_loop = true` 的判据：S1-0~8 全验收 + 独立汇总复核通过。

---



## 3. 工程切分与吞吐/稳定性决策（F 系列，2026-07-09 全部定案）


| #   | 决策                       | 推荐 + 理由                                                                                                                                                           | 状态  |
| --- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- |
| F1  | 评测面绑定                    | **已定**（E10 直接推出）：主评测面 = 训练路径 eval 模式；verifiers 路径 = transfer 面 + 治理审计 + 协议基线                                                                                      | 定案  |
| F2  | S1-7 拆档                  | 7a = **debug training transport step**（Qwen3-4B 单/双卡，A1 语义），7b（30B 全要素）并入 S4 前 8 卡预实验。理由：链路正确性与多卡稳定性两类风险分开查，省一次 8 卡租用 | **已定（2026-07-09）** |
| F3  | bring-up 数据 ingestion 排期 | S1 闭环只用 8 题冻结集；SWE-Gym Lite 静态预筛 + ingestion 为 S1 末并行任务、S2 完成。**GPU pass-rate 预筛 [0.1,0.8] + pre-RL 行为诊断（同批 rollout，E3/E4）归 S2 末或 S3-0，单卡 30B 推理即可**（B1 归属补齐） | **已定** |
| F4  | GPU 租用策略（**四段式**，B1）  | ① S1-0 单卡短租（已完成）；② S1-7a 单/双卡短租（半天）；③ S2 末/S3-0 单卡短租：30B pass-rate 预筛 + pre-RL 诊断；④ S4 前 8 卡整机：7b + U-C + 吞吐画像 | **已定** |
| F5  | 评分并发首版参数                 | **默认并发 4、队列 8（2×），参数可配置**；evidence 记录容器峰值、队列等待、评分耗时与 prep/test/env_reset/image_pull 分段；实测稳定后再升 8（A9 + 用户收紧版）。评分与 rollout 沙箱同宿主，分离留 S5 | **已定（用户版）** |
| F6  | slime 版本 pin             | 镜像 digest（S1-0 已 pin `a7317182…`）+ slime commit 双 pin，进 source_digests；**机器可读探针结果 `s1/uh_probe_result.json` 供 inspect-rh2-s1 读取（A10，已生成）**；升级走契约测试先行纪律（对 slime Sample/TrajectoryManager 行为补小契约测试） | **已定** |


---



## 4. 风险与未知

```text
U-H（阻塞级）：slime 镜像 on sm_120 —— S1-0 首位验证，回退梯已定（E2）。
U-I（新）：slime Claude Code harness 对我们环境包沙箱的适配面——slime 的
  harness 假设其自带 Sandbox Protocol（E2B/docker），与我们 envpack 物化的
  对接点在 S1-6 首次真实接触，可能出现工作目录/权限/网络假设不匹配。
  预案：S1-6 的 mock 单测先钉住接口，S1-7a 首日排它。
U-J（新）：Qwen3-4B 与 30B-A3B 的 renderer/模板差异——7a 用 4B 验链路，
  投影层的 renderer 断言必须按模型分别配置，防止 4B 验过的配置被误用于 30B。
U-C（承接）：8 卡训练侧 —— 并入 S4 前预实验（F2）。
```

---



## 5. 完成定义与 evidence

```text
docs/agentic_RL/repo_harness_rh2_workstreams/s1/
  implementation-notes.md        全程维护（三节制）
  uh_probe_report.md             S1-0（含镜像 digest pin）
  contracts_review.md            S1-1 schema 设计要点与 fail-closed 单测清单
  envpack_freeze_v1.md           S1-2（8 题 digest + 回归对照）
  grading_p_matrix.md            S1-4（P1~P11 逐条：实现/测试/豁免）
  bringup_7a_report.md           S1-7a（真实训练 step 的数据链路证据）
  parity_report.md               S1-8
  s1_acceptance_summary.json     闸门账本 + source_digests
```

预计代码规模：contracts + envpack + grading + governance + adapters 合计约 3~~5k 行 + 等量测试。时间盒建议 2~~3 周（S1-0 等 GPU 租用窗口，其余本机任务可先行并行）。