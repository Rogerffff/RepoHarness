# 03 — S1 执行计划：端到端最小闭环（草案，F 系列定案后去掉草案标注）

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

| # | 任务 | 位置 | 硬依赖 |
| --- | --- | --- | --- |
| S1-0 | **U-H 验证（硬阻塞）**：slime patch 镜像 on Blackwell | 单卡 GPU 短租 | E2 |
| S1-1 | contracts 先行：7 个 schema + 最小 inspector | 本机 | — |
| S1-2 | 环境包库抽取 + 8 题冻结固化 | 本机 | S1-1 |
| S1-3 | project_from_slime（主线投影 adapter） | 本机（fixture 驱动） | S1-1 |
| S1-4 | SWEGradingManager 最小版（P1~P11 对照） | 本机 docker | S1-2 |
| S1-5 | Gate + EligibilityReport + 投影扫描 | 本机 | S1-1/3/4 |
| S1-6 | slime 绑定：custom_generate 编排胶水 | 本机写 + GPU 验 | S1-2~5 |
| S1-7 | 端到端 bring-up（分两档，见 F2） | GPU | S1-0/6 |
| S1-8 | 离线导出 + project_from_verifiers + parity | 本机 | S1-3/5 |
| S1-9 | 验收：inspect-rh2-s1 + acceptance summary + AGENTS 同步 | 本机 | 全部 |

### S1-0 U-H 验证（第一个动作，单卡 Blackwell 短租数小时）

拉 slime 官方 docker 镜像（含 sglang-top_p.patch 的那个）→ 在 RTX PRO 6000 上起 SGLang + Qwen3-30B-A3B → 复跑 S0-6 探针脚本（top_p=0.95 + return_top_p_token_ids + return_routed_experts）→ 断言 meta_info 同时含 top-p tape 与 routing tape 且与 token 对齐。产出 `s1/uh_probe_report.md` + 镜像 digest pin。失败即触发回退梯并停下来与用户讨论。

### S1-1 contracts 先行

`rh2/src/repoharness2/contracts/`：trajectory.py（TrajectoryProjection/BranchProjection/TokenSpan/LossMaskSpan/LogprobProvenance/RoutingTensorRef/SamplingMaskRef/RewardFacts）、eligibility.py、grading.py、findings.py、anti_hack.py（schema 先行，S2 才接 filter）、handshake.py、timing.py。全部 pydantic `extra="forbid"` + 字段白名单常量（继承 L4/L5 marker 语义）。配 `inspect-rh2-artifact` 最小校验命令 + schema 单测。**验收：对着手工构造的合格/违规样例，校验通过/拒绝行为正确（fail-closed 单测）。**

### S1-2 环境包库抽取 + 冻结固化

把 S0-7 的 `SweSmokeTaskset` 拆成两层：**框架无关库**（`envpack/`：materialize 血缘校验、官方 parser 评分、题目数据 + digest）与 **verifiers 绑定**（Taskset 子类调库）。8 题冻结记录（instance_id + 镜像 digest + 题面 sha256）写进 `envpack/data/frozen_v1.json`。**验收：verifiers 绑定跑 8 题 smoke 结果与 S0-7 一致（回归）；库层单测不 import verifiers。**

### S1-3 project_from_slime（主线投影）

输入 slime `Sample`/TrajectoryManager 输出（含 rollout_log_probs / rollout_routed_experts / top-p ids），输出 `TrajectoryProjection`。要点：tape 解码唯一实现点；loss mask 语义对齐 H4（sampled ∧ role）；compaction 分叉 → CompactedSubTraceLineage；renderer/tokenizer 事实进 LogprobProvenance（logprob_source 标注 M4）；U-G 守门（断言 renderer 类名的检查函数供 S1-6 启动期调用）。**S1 阶段用离线 fixture 驱动**（从 slime 数据结构手工构造 + S1-7a 真实产物回归），不需要 GPU。**验收：fixture 全绿 + S1-7a 真实 Sample 投影 round-trip 校验。**

### S1-4 SWEGradingManager 最小版

`grading/manager.py`（prepare/grade/gc）+ `grading/queue.py`（有界队列 P11）。评分动作复用 S1-2 库层（fresh 评分沙箱 + patch replay + 官方 parser）。P1~P11 逐条落成测试或显式豁免记录表；五类计时埋点（agent/prep/test/env_reset/image_pull）写 timing schema。**验收：8 题冻结集经 manager 评分与 S0-7 直评结果一致；故障注入测试（杀评分容器 → infra_failure 而非 reward=0；队列打满 → 反压事件）。**

### S1-5 Gate + EligibilityReport + 投影扫描

`governance/gate.py`：七维事实合取 → 三档资格；S1 全程默认最高只发 `offline_or_sft_candidate`（安全加固未完成，fail-closed）；组修复信号接口（GRPO n=8 语义按 E2，降级须在组装配前对后端可见）。`governance/projection.py`：public projection 扫描（forbidden marker 继承）。EligibilityReport sidecar 与 Trace/Sample 以 id 关联。**验收：单测覆盖"任一维度失败即降级"“未知字段拒收”“绕过 gate 的路径不存在（wrapper 是唯一入口）"。**

### S1-6 slime 绑定（custom_generate 编排胶水）

`adapters/slime/generate.py`：实现 02 文档 §8 的 9 步生命周期——物化(库层)→Claude Code harness(slime 现成)→TrajectoryManager(slime 现成)→GradingManager→project_from_slime→Gate→合格 Sample 返回 slime。启动期跑 U-G renderer 断言 + U-H 探针断言（防镜像静默降级）。**验收：本机 mock SGLang 端点下编排逻辑单测全绿；真实验收在 S1-7。**

### S1-7 端到端 bring-up（拆两档，F2）

- **7a 数据链路验证（单/双卡）**：Qwen3-4B（dense）+ slime 最小训练配置，8 题冻结集 n=2，跑通 custom_generate 全链 → 一个真实训练 step（不求收敛）。验证 loss mask/logprob/样本传输/gate 拒绝路径在真实 slime 循环里正确。dense 无 routing tape——routing 字段缺失时 projection 须显式标注而非报错（本身就是一个验收项）。
- **7b 30B-A3B 全要素训练 step**：**并入 S4 前的 8 卡预实验**（与 U-C 一起关闭），不阻塞 S1 闸门。理由见 F2。

### S1-8 离线导出 + project_from_verifiers + parity

`adapters/offline_export/`：TrajectoryProjection → TrainingExportRecord（对接 warm-start 过滤契约）。`project_from_verifiers`：verifiers Trace → 投影（评测/导出路径用）。parity 按形态 B 判据：同一批 rollout 经离线导出与 slime 消费，**治理事实/RewardFacts/eligibility/logprob_source/provenance 逐项一致**；token 逐位一致仅在同 renderer 路径断言。**验收：parity 脚本 + 报告。**

### S1-9 验收收口

`inspect-rh2-s1` 完整 inspector（四步范式：digest 重算/report 对照/白名单/marker 扫描）+ `s1_acceptance_summary.json` + AGENTS.md 进度翻转 + implementation-notes 收口。闸门 `rh2_s1_closed_loop = true` 的判据：S1-0~8 全验收 + 独立汇总复核通过。

---

## 3. 工程切分与吞吐/稳定性决策（F 系列，待拍板）

| # | 决策 | 推荐 + 理由 | 状态 |
| --- | --- | --- | --- |
| F1 | 评测面绑定 | **已定**（E10 直接推出）：主评测面 = 训练路径 eval 模式；verifiers 路径 = transfer 面 + 治理审计 + 协议基线 | 定案 |
| F2 | S1-7 拆档 | **7a 用 Qwen3-4B 单/双卡先验数据链路，7b（30B 全要素）并入 S4 前 8 卡预实验**。理由：数据链路正确性与多卡训练稳定性是两类风险——前者小卡即可全覆盖（除 routing 字段），后者本来就要 8 卡专项（U-C）；合并省一次 8 卡租用，且避免"链路 bug 和多卡问题搅在一起查"的排障地狱 | 待确认 |
| F3 | bring-up 数据 ingestion 排期 | **S1 闭环只用 8 题冻结集；SWE-Gym Lite 100~200 题静态预筛 + ingestion 作为 S1 末尾的并行任务启动、S2 完成**。理由：闭环验证与数据规模无关；预筛只耗 agent 额度可先行 | 待确认 |
| F4 | GPU 租用策略 | S1-0 单卡 Blackwell 短租（数小时，验完即停）；S1-7a 单/双卡短租（半天）；8 卡等 S4 前预实验一次租够（7b + U-C + 吞吐画像一起做） | 待确认 |
| F5 | 评分并发首版参数 | per-worker asyncio + 信号量并发 8 + 有界队列 2×并发（P11）；埋点数据出来后再调。评分沙箱与 rollout 沙箱同宿主（S1 规模 8 题×n=2 不值得分离，M2 的接口预留兑现留 S5） | 待确认 |
| F6 | slime 版本 pin | S1-0 验证通过的 slime 镜像 digest + slime 代码 commit 双 pin，进 s1 acceptance 的 source_digests；升级走与 verifiers 同样的"契约测试先行"纪律（对 slime 的 Sample/TrajectoryManager 行为补一组小契约测试） | 待确认 |

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

预计代码规模：contracts + envpack + grading + governance + adapters 合计约 3~5k 行 + 等量测试。时间盒建议 2~3 周（S1-0 等 GPU 租用窗口，其余本机任务可先行并行）。
