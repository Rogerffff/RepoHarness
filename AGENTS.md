# RepoHarness Agent Guide

所有编写的文档或者注释，除了必要的专业词汇、命令名称、文件名、字段名和代码标识符之外，都使用清晰、详细、通俗易懂的中文。如果解释一个容易混淆的概念，尽量搭配具体数值、文件路径、命令或者实现例子。

## 项目一句话定位（2026-07 起，rh2 新架构）

RepoHarness 是**建立在 PrimeIntellect verifiers v1 基座之上的、面向 SWE agent RL 的安全与训练治理层 + 环境生产线**：

```text
RepoHarness =
    verifiers v1 基座（环境组合 / Trace / interception / EnvServer，直接采用）
  + SWE-Safety 扩展层（安全沙箱 / 评分隔离 / 反作弊 / 权限）
  + 训练治理层（训练资格分级 / artifact 可见性 / fail-closed inspector）
  + 训练后端 adapter 层（slime / verl / 离线导出，经中立投影契约解耦）
  + 环境生产线（SWE taskset / 质量验证门槛）
```

它**不再造** rollout 捕获、token 保真轨迹、训练内核、推理服务（verifiers / slime / vLLM / SGLang 已分别商品化）；它专注工业训练后端普遍缺失的部分：环境生产质量门槛、评分隔离语义、anti-cheat 纵深、可审计的训练资格治理、多后端解耦。也不要把它描述成生产级产品、公开榜单系统或已经训练出模型的项目。

旧定位（"白盒 SWE harness + verl 桥接"，实现于 `src/repo_harness/`）已于 2026-07 冻结为 legacy，见下文进度章节。

---

## 协作协议（所有 agent 必读；唯一权威 = `docs/agentic_RL/repo_harness_rh2_workstreams/collaboration-protocol.md`）

三方分工：用户 = owner（T0 决策）；Claude = 实现者；codex = 独立审查 +
设计顾问 + 代码讲解。硬规则摘要（冲突以权威文档为准）：

- **T0/T1/T2 决策分级**：T0（训练语义/公共契约/状态所有权与恢复语义/新增
  剔除轨迹的拒绝路径/安全边界/重要依赖/重大成本/推翻既有定案）必须用户
  **写码前**拍板，以决策包格式提出；T1 实现后报告；T2 只留 commit。
- **报告六段模板**：待拍板 T0 / T1 决策 / 挡板变动 / 推翻的旧结论 /
  测试与账本 / 学习摘要（进 `learning-log.md`）。
- **codex 审查九维度**：A 正确性并发安全 / B 训练分布影响 / C 挡板审计
  （守卫必须有移除条件）/ D 所有权与配置真实性 / E 测试有效性（真进目标
  分支、不过度钉死）/ F 文档一致性 / G 生产路径证明（不是只测 helper）/
  H 唯一事实来源 / I 问题分期（"本轮必修 / 正式训练前修 / 可递延"，并
  列出不值得立即修的）。每轮必答：新拒绝路径丢哪类轨迹？失败是否结构化
  留痕？有无静默降级？测试是否经过真实线程拓扑？哪些不值得立即修？
- **审查标准**：六级审查（决策包含 T0 完整性扫描与 A~N 适用性扫描 /
  执行计划审迁移顺序与回滚 / 切片 A~N / 小阶段集成 / 大阶段验收（后两级
  强制独立上下文 + 证据产物清单）/ 训前总审计出 Owner Gate Packet），唯一权威 =
  `docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md`。
  finding 八要素（行为/不变量/证据/影响/分期/位置/复现/修复验收条件）；
  N/A 与"未发现问题"必须给证据；Claude 只能三选一回应（accepted /
  rejected_with_evidence / deferred_with_owner_and_gate），复核最多一轮，
  T0 分歧交用户。测试 oracle 改动不是 T2。
- **修复循环熔断**：同一状态边界连续两轮新 P0 / 修复引入新 P0 / 修复
  跨多个 ownership 边界 → 停止增量修补，先出根因分析与替代设计。
- **现状权威**：实现现状看 `fa/implementation-notes.md` 顶部"⚡ 当前权威
  状态"页（含临时挡板登记表）；历史小节是流水账，可能已被推翻。

---

## 当前进度（接手前必读）

**单一入口：`docs/agentic_RL/repo_harness_rh2_workstreams/00-project-status.md`**（2026-07-09 起）——当前位置、各阶段完成详情、闸门状态、全项目遗留/阻塞合并表、文档地图、术语速查都在那里；本节只保留压缩版。

**重要：AGENTS.md 这一节与 00-project-status.md 随阶段推进同步更新。如果你接手时发现与最新 commit 不一致，以 `git log --oneline` 和 `docs/agentic_RL/repo_harness_rh2_workstreams/` 下最新执行计划 / evidence 为准。**

**2026-07 重大转折：项目已转入 rh2 新架构，旧阶段线（16G.x）终止。**

```text
【已终止】Stage 13 ~ 16G.2C     旧白盒单体架构的成果，全部完成并冻结为 legacy。
                              代码在 src/repo_harness/（不再新增功能），evidence 在
                              docs/agentic_RL/repo_harness_verl_workstreams/stage16g_*/
                              （不可修改，旧 inspector 仍可复核历史）。
【不再执行】Stage 16G.3 ~ 16G.6  由 rh2 新架构取代（工具面问题被 verifiers 内置
                              default harness 直接覆盖）。任何旧文档说"当前任务是
                              16G.3"均已过时。
【作废】Stage 17B / 20 / 21 闸门  由 rh2 新闸门体系取代（Stage 20 warm-start 语义
                              由 rh2 离线导出 adapter 承接）。
【已完成】rh2 S0 可行性验证      V1~V4 全过。执行计划：
                              docs/agentic_RL/repo_harness_rh2_workstreams/01-s0-execution-plan.md
【已完成】rh2 S1 端到端最小闭环（检查点 2 已由用户确认，2026-07-11）
                              S1-0~9 全部执行完毕：slime 形态 B 数据链路真实闭环
                              （7a 两个 optimizer step + checkpoint 用后即弃）、
                              离线导出 parity 双通过、总 inspector inspect-rh2-s1
                              + s1_acceptance_summary.json 就位。执行计划：
                              docs/agentic_RL/repo_harness_rh2_workstreams/03-s1-execution-plan.md
                              递延与 S2 阻塞项见 s1/s1_acceptance_summary.json 的
                              deferred_risks/blockers 字段与 s1/s2_blockers.md
                              （S1-8 导出器对 thinking 模型轨迹全 fail-closed 拒绝，
                              E3 warm-start 回退预案的前置依赖，S2 必须显式处置）。
【已完成】rh2 P1 数据冻结包 v0.1（训练数据预处理，codex 线程 2026-07-08）
                              DF-1~8 全部完成：SWE-Gym Lite 静态门存活 216/230、
                              held-out 候选 542 题（冻结 T=50~80 待四道门）、
                              hints 剥离中和 47.4% 泄漏、四源 HF revision pin +
                              24 项 digest 账本。收口报告：
                              docs/agentic_RL/repo_harness_rh2_workstreams/data_freeze/data_freeze_report.md
                              注意：S1 的 8 题 Verified 冻结集只是基建探针，
                              正式训练数据 = 本包 216 存活题（等 S2-1 环境四门）。
【已完成】rh2 P3 八卡预实验     2026-07-08/09 真机执行（8×RTX PRO 6000, sm_120）。
                              训练侧四项未知全关、S1-7b routing tape 首次真实进
                              loss、放置定案 T3 分离 + train_async（废弃"必须
                              colocate"）、整 step 实测 23min（rollout-bound
                              0.82）、尾部空闲 26~28% > 25% 升级阈值。
                              formal J4 严格绿灯留一项本地任务：治理过滤后
                              batch schedule alignment（纯 Python 可修，归 S2
                              adapter 层，协议 J4 判据第 0 项）。收口判定：
                              docs/agentic_RL/repo_harness_rh2_workstreams/preflight/preflight_report.md
                              acceptance 三条递延项已改判 closed_by_p3_20260708。
【下一阶段·双工作流并行】（用户 2026-07-12 定案 fully-async-first）
                              ① FA fully async 训练链（第一实施工作流）：
                              docs/agentic_RL/repo_harness_rh2_workstreams/05-fully-async-execution-plan.md
                              正式链 = version-aware fully async + faithful DIS；
                              FA-0~5（身份契约 → worker/proxy 边界 → 组装器 →
                              batch 准入[原 S2-0b 问题 A~E 迁入] → DIS → 短租
                              验收）；权重更新 abort = proxy 级 turn 重生成；
                              eval 首版只 before/after；退出闸门
                              rh2_fully_async_training_path_verified。
                              进度：FA-0 / FA-1 / FA-3 离线 / FA-4 对拍 已完成
                              （FA-1 含 codex 轮次 6~14 九轮审查修复与 closure
                              批次，2026-07-20，测试 647→903+；FA-2 下一步：
                              先 2A 身份与持久性基座再 assembler；notes 顶部
                              "当前权威状态"页是现状权威）。
                              ② S2 SWE-Safety + 数据 ingestion（并行）：
                              docs/agentic_RL/repo_harness_rh2_workstreams/04-s2-execution-plan.md
                              S2-0b 已迁出；S2 侧起点 = S2-6 导出器 ∥ S2-1
                              ingestion；G1~G10 决策待用户下一轮。
                              rh2_formal_training_allowed = FA 闸门 ∧ S2 闸门；
                              两工作流的 GPU 段合并为同一次短租（FA-5 + G10）。
```

rh2 新闸门字段当前真实值：

```text
rh2_s0_complete              = true    （S0 全部 9 项任务完成，V1~V4 全过；见 s0_acceptance_summary.json）
rh2_s1_closed_loop           = true   （checkpoint-2 已由用户确认 2026-07-11，pending 注记
                                       已摘除；gates 字段保留 checkpoint2_confirmed_by_user_20260711
                                       作为审计痕迹）
rh2_s2_signal_trusted        = false
rh2_formal_training_allowed  = false   （≈ 旧 stage21 语义；为 false 时禁止正式训练。
                                       S1-7a 为 debug transport step，checkpoint 已删除留证）
```

rh2 S1 复核命令（本机，rh2/ 目录下）：

```bash
cd rh2 && uv run inspect-rh2-s1                        # 四步范式校验阶段总账本
cd rh2 && uv run inspect-rh2-s1 --run-contract-tests   # 附带重跑契约测试
cd rh2 && uv run inspect-rh2-s1 --write --pytest-count <N>  # evidence 变动后重新生成 summary
```

rh2 阶段一览（细节见实施计划总纲）：

```text
S0 可行性验证（已完成）   verifiers pin 契约测试、玩具闭环、renderer/协议/MoE 张量
                        验证、SWE smoke 题、实验设计收口；S0-0~4 本机，S0-5 起租 GPU
S1 端到端最小闭环（已完成，检查点 2 已确认 2026-07-11）
                        SWE taskset 冻结（8 题探针）、SWEGradingManager、
                        EligibilityReport + Gate、离线导出 adapter、slime adapter
P1 数据冻结 / P3 八卡预实验（已完成，穿插工作流，不在 S 编号序列）
FA fully async 训练链（计划已写未开工，第一实施工作流，与 S2 并行）
                        持续 worker + PromptGroupAssembler + batch 准入
                        （原 S2-0b）+ faithful DIS + 短租验收；05 计划
S2 SWE-Safety 加固（计划已写未开工，与 FA 并行）
                        安全 Runtime、anti-cheat（在线拦截）、红队环境包、
                        数据 ingestion + 环境四门、导出器重建
S3 训练治理完备          三档资格全量、环境验证四门收尾
S4 正式训练实验          before/after 实验（简历叙事收尾）
S5 第二后端 + 服务化     verl adapter、EnvServer 服务化（按需）
```

---

## 仓库结构速览

新架构（rh2，进行中）：

```text
rh2/                                     rh2 新包独立子项目（S0-1 创建：pyproject + src/repoharness2 + tests）
docs/agentic_RL/repo_harness_rh2_workstreams/
                                         rh2 执行计划 + 阶段 evidence（01-s0-execution-plan.md、s0/）
docs/harness_improve/                    rh2 设计文档区（设计文档 2 / final review / 实施计划总纲）
reference/                               外部参考库（verifiers / slime / verl / prime-rl / ROCK 等，
                                         各有 CLAUDE.md 导览；只读，不属于主实现）
```

### 【legacy】Python 旧主实现 `src/repo_harness/`

**以下描述 2026-07 冻结的旧架构代码。不再新增功能；契约与不变量已由 rh2 设计文档继承（"迁契约不迁代码"）。**

旧 V1 ~ V5 模块（冻结，作为版本闭环留作 acceptance）：

```text
v2_acceptance.py
v3_*.py               V3 Docker backend / SWE-Bench-like fixture / export audit / acceptance
v4_*.py               V4 task freeze / rollout / tool lifecycle / agent run / export quality / cards
v5_*.py               V5 evidence / export pack / provider gate / run matrix / demo artifacts
pre_verl_*.py         pre_verl agent loop / evaluation / evidence ledger / failure injection / run facts
```

agentic RL / verl 桥接相关模块（旧训练链路主路径，已随整个 legacy 实现冻结）：

```text
rl/                   verl 训练桥接的核心
  runtime.py          RepoHarnessRuntime.run_episode / start_episode 真实入口
  episode.py          RepoHarnessEpisodeRequest / RepoHarnessEpisodeResult 数据契约
  training_view.py    TrainingView projection（response_ids / mask / spans）
  visibility.py       FORBIDDEN_FIELD_MARKERS / VisibilityContractError（L4 安全防线）
  reward_boundary.py  reward boundary policy（invalid_for_training / invalid_for_online_rl 决定点）
  gateway.py / provider_gateway.py
                      LLM Gateway routing；mock / verl / openai / deepseek 等
  async_contracts.py / async_runtime.py / async_validation.py
                      verl 异步框架接入契约
  partial_checkpoint.py / pause_resume.py
                      partial rollout / 同进程 resume
  budget.py / resources.py / throughput.py / timing.py
                      预算、资源、吞吐量

execution/
  spec.py             EpisodeExecutionSpec 任务 / verifier / tool / budget / feedback 策略绑定
  builder.py          spec 构造

evaluation/
  episode_runner.py   run-episode-task CLI 执行入口
  episode_projection.py
                      新入口 → 14 个公开文件 + manifest + provider_route_qualification（policy_loss 守门员）
  episode_parity.py   新旧入口 parity audit
  entrypoint_policy.py
                      legacy run_task vs run-episode-task 训练资格
  outcome_policy.py
  stage16d_healthcheck.py / stage16f6_smoke.py
                      阶段专用诊断 / smoke

workspace/
  adapter.py / docker_adapter.py / backend_factory.py
                      Docker / local backend 抽象
  diagnostic_session.py
                      Stage 16B 诊断 shell session
  dependency_environment.py
                      依赖环境注入
  patch_hygiene.py
                      final.patch / final.diff 清洁投影、过滤 runtime-private、public-safe hygiene report
  reuse.py / materialization.py / source_hash.py

tools/
  minimal.py          【模型可见工具的主入口】ToolRegistry + ToolExecutor
                      execute() 内部 15 路 dispatch，覆盖 19 个工具名（DEFAULT_TOOL_ORDER 14 +
                      execute_bash + diagnostic_shell + delete_file/move_file/mkdir 共 4 个 extended）
                      DEFAULT_TOOL_ORDER：list_files / glob_files / read_file / read_tool_result_artifact
                      / grep / symbol_search / update_working_state / edit_file / create_file /
                      write_file / apply_patch / bash / run_tests / git_diff
                      file 变更 5 件套（write_file / apply_patch / delete_file / move_file / mkdir）
                      共用同一 handler _stage16g2b_file_mutation_tool（minimal.py:2229）
  file_mutation.py    【16G.2B 新增】结构化文件变更共享核心
                      execute_structured_file_mutation：preflight → snapshot → apply → rollback
                      原子语义；_apply_prepared_operation 是唯一真实写盘点（line 555）
                      _SENSITIVE_PATH_MARKERS（L3 安全防线）
  symbol_index.py     symbol_search 缓存

stage16g_tool_profile.py
                      【16G.1 新增】4 档 profile taxonomy + 工具 registry 契约（27 条能力）
stage16g2_file_surface.py
                      【16G.2A/B/C 新增】file 变更工具面 + 4 个 inspector 实现：
                        inspect_stage16g2a_tool_surface
                        inspect_stage16g2b_file_mutation
                        inspect_stage16g2c_projection_linkage
                      字段白名单常量 STAGE16G2C_PROBE_KEYS / STAGE16G2C_LINKAGE_KEYS /
                      STAGE16G2C_PATH_SCAN_KEYS / STAGE16G2C_PATCH_ENTRY_KEYS 等

tasks/
  command_policy.py   Stage 16A 安全最小 execute_bash 策略（不是完整 Claude Code Bash）
  public_environment.py
                      公开环境上下文 prompt 拼装（Stage 16C 落地）
  environment.py      任务执行环境抽象
  其他               public_command_profiles（原计划 16G.3 引入，已随 16G.3 废弃而搁置）

cli/
  main.py             repo-harness CLI 入口；143 个 inspector 子命令
                      含 inspect-stage16g1-tool-profile / inspect-stage16g2a-tool-surface /
                      inspect-stage16g2b-file-mutation / inspect-stage16g2c-projection-linkage

verifier/ permissions/ scaffolds/ context/ budget/ trajectory/ export/ model_client/ reward/
config/ schema_base.py schema_versions.py errors.py
                      其他横切模块
agent_loop/           早期 agent loop 实现（V1/V2 闭环用）
run_metadata/         run-time metadata writer / fingerprint / tool snapshot
inspect_initial_context.py
                      顶层独立 inspector，不是 CLI 子命令
```

### 测试 `tests/`

```text
tests/unit/
  test_v2_*.py / test_v3_*.py / test_v4_*.py / test_v5_*.py
  test_pre_verl_*.py
  test_repo_harness_stage16f*.py       Stage 16F 系列
  test_repo_harness_stage16g2a_tool_surface.py
  test_repo_harness_stage16g2b_file_mutation.py
  test_repo_harness_stage16g2c_projection_linkage.py

tests/integration/                       Docker backend / 端到端 / fixture 相关
```

### 文档 `docs/`

旧版本闭环文档（按版本）：

```text
docs/v1/ ~ docs/v5/                      V1 ~ V5 范围 / 计划 / 实现日志 / review / acceptance / final
docs/00-* ~ docs/13-*                    核心设计文档（架构 / agent loop / 工具系统 / workspace / verifier 等）
docs/build-your-own/                     旧 walkthrough
docs/project_tut_for_me/                 项目教程
docs/resume/                             简历 / 评测 worktree 同步记录
docs/review/ docs/implementation-log/    审查记录 / 实现日志
docs/assets/                             图片素材
```

agentic RL / verl 工作流文档（legacy，旧线历史主战场；rh2 工作流见 `repo_harness_rh2_workstreams/`）：

```text
docs/agentic_RL/
  agentic_RL.md / harness_connect_verl.md
                                         总览
  repo_harness_verl_*.md                 设计 / 实施 / 契约
  repo_harness_verl_*.html               HTML 报告（每个阶段都有 plan / completion report）
                                         16G 相关 HTML 包括：
                                           stage16g0_completion_review / followup_completion_review /
                                           full_stage_report / harness_comparison_basics
                                           stage16g1_completion_report
                                           stage16g2a/b/c_completion_report
                                           stage16g3_plan_overview / 3a / 3b / 3c / 3d_plan
                                           stage16g_4way_tool_comparison
                                           stage16g_codex_harness_overview
                                           harness_capability_acceptance_map（27 条能力四象限地图）
  code_guide_index.html                  代码导览总览（T0-T9 + 4 侧栏）
  code_guide_t5_execute.html             T5 工具执行（已写，10 步调用链 + 13 段 code excerpt）
  code_guide_t8_projection.html          T8 投影（已写）
  code_guide_side_safety.html            侧栏 A 安全边界（5 道防线 L1-L5）
  repo_harness_verl_workstreams/         按编号 01 ~ 56 的执行计划 + shared_contracts/
  training_design/                       训练设计：RL_algorithm_design / 实验设计 /
                                         post_stage15_training_infra_stage_plan 等

docs/harness_improve/                    外部 harness 设计参考与建议（现同时是 rh2 三份定案文档所在处，见上文"新架构"段）
  codex_vs_claude_code_harness_design_analysis.md
  gpt_advice*.md / harness_design_advice.md / bash_tool_advice.md / env_design.md /
  harness_env_design.md / 16G-3_advice.md / 16G-3_plan_V1.md
  main_20260602_2.pdf                    微软 MAI-Thinking-1 SWE RL 报告（2026-06-02）
```

### 阶段证据 `docs/agentic_RL/repo_harness_verl_workstreams/stage16g_*/`

每个子阶段都有自己的 evidence 目录：

```text
stage16g_0/                              16G.0 + follow-up（共 19 份 JSON）
stage16g_1/                              16G.1（11 份 JSON + implementation-notes）
stage16g_2/                              16G.2A/B/C（17 份 JSON + implementation-notes）
```

每个目录的 `_acceptance_summary.json` 是该子阶段的总账本，含 `source_digests`（绑定源代码 sha256）和闸门字段。

### 运行产物 `runs/`

按阶段命名，含远端 smoke / 本地 acceptance / partial rollout 等。**不要默认读取 latest run**，所有 inspect 命令都应显式传入路径。

### 外部参考 `reference/`

```text
claude-code-docs/                        Claude Code 架构分析资料
claude-code-typescript-src/              Claude Code TypeScript 参考源码（含其自己的 AGENTS.md）
codex/                                   Codex 参考源码（codex-rs Rust 实现）
verl/                                    verl 异步训练框架
```

只作为设计参考，不是 RepoHarness 主实现的一部分。

---

## 【legacy】关键代码架构（旧 src/repo_harness 的 5 个子系统）

**本章描述冻结的旧实现。新架构见 rh2 设计文档；这里保留是因为旧五道防线 / inspector 范式 / 原子语义的契约被 rh2 继承，读旧实现有助于理解契约出处。**

### 1. 模型可见工具表面（tools/minimal.py）

```text
ToolExecutor.execute(tool_call, context)            minimal.py:368
  └─ normalize(tool_call, context)                  minimal.py:431  schema 校验 + 参数归一
  └─ if/elif 分派到 18 个 handler                    minimal.py:370-422
       特别注意 line 391：5 个文件变更工具
       {"write_file","apply_patch","delete_file","move_file","mkdir"}
       共用 _stage16g2b_file_mutation_tool 处理器     minimal.py:2229
```

`ToolExecutionContext`（minimal.py:189）含 `file_state_cache`（read/edit/write 共享缓存）/ `artifact_writer`（= `recorder` @property）/ `output_limits` / `permission_context` / `workspace_facade`。

### 2. 结构化文件变更原子语义（tools/file_mutation.py）

```text
execute_structured_file_mutation(*, tool_name, arguments, context)   file_mutation.py:177
  ① _normalize_operations(...)            5 件套 → 统一 ops 列表          line 238
  ② _prepare_operations(...)              逐 op 预检（路径黑名单 / hash / UTF-8）  line 279
  ③ _snapshot_paths + _snapshot_path      affected paths 快照             line 731 / 略
  ④ for mutation in prepared:
       _apply_prepared_operation(mutation)真实 write_text/unlink/rename/mkdir line 555
  ⑤ except → _rollback_snapshots(...)      失败回滚                       略
```

不变量：`policy_loss_candidate` 永远 False（mock route）/ partial_failure → `invalid_for_training=True` / 所有真实写盘只能走 `_apply_prepared_operation`（不可绕过）。

### 3. Episode 投影 + policy_loss 守门员（evaluation/episode_projection.py）

```text
write_run_episode_compat_projection(...)              episode_projection.py:118
  ① _provider_route_qualification(...)               episode_projection.py:610
       policy_loss_candidate = (route=="verl"
                                AND llm_gateway_route=="verl"
                                AND not invalid_for_training
                                AND not invalid_for_online_rl)
  ② 字段白名单提取 14 个公开 dict（training_view / status / metrics 等）
  ③ _write_projection_file × 14
  ④ _manifest_payload + compat_projection_manifest.json
  ⑤ validate_run_episode_compat_projection(assert_complete=True)
       五处 mismatch 兜底
  ⑥ _scan_public_projection_for_leaks                 episode_projection.py:638
       公开扫描 _FORBIDDEN_PUBLIC_MARKERS（含 /Users/ / /home/ / hidden_verifier 等）
```

### 4. 5 道安全防线（横跨多个模块）

详见 `docs/agentic_RL/code_guide_side_safety.html`：

```text
L1 工具 schema 校验          T4 dispatch 前    minimal.py 各 ToolDefinition（additionalProperties:false）
L2 路径黑名单                T5 写盘前         minimal.py:61 MODEL_HIDDEN_TOOL_PATH_PARTS（30+ 条）
L3 敏感 marker 路径变体      T5 写盘前         file_mutation.py:56 _SENSITIVE_PATH_MARKERS
                                              file_mutation.py:603 触发（小写归一 + frozenset 比对）
L4 model-visible 出站扫描    T6 出站前         rl/visibility.py:56 FORBIDDEN_FIELD_MARKERS
                                              （合并 line 28-40 EVALUATOR_ONLY_DENYLIST +
                                               line 48-54 FORBIDDEN_BATCH_EXTRA_FIELD_KEYS +
                                               line 55 FORBIDDEN_BATCH_EXTRA_FIELD_ALIASES）
                                              rl/visibility.py:133 _find_forbidden_marker 触发
                                              ⚠️ 16G.2C audit_ref → audit_artifact_id 改名就是因为踩这一层
L5 公开投影最终扫描          T8 写完后         episode_projection.py:46 _FORBIDDEN_PUBLIC_MARKERS
                                              + episode_projection.py:638 _scan_public_projection_for_leaks
```

### 5. 4 档 profile + 27 条能力（stage16g_tool_profile.py + stage16g2_file_surface.py）

```text
profiles:
  safe_structured_only          只读 + 结构化编辑，最严
  swe_public_core               主训练默认（含 write_file / apply_patch / 文件编辑等）
  swe_public_extended           swe_public_core + 独立 delete_file / move_file / mkdir
  redteam_restricted            红队探针专用，待 16G.6 freeze

能力：27 条 capability_id，记录在 stage16g1_tool_registry_contract.json
能力地图 HTML：docs/agentic_RL/repo_harness_verl_harness_capability_acceptance_map.html
            含四象限卡（① 模型视角 ② 实现位置 ③ 训练投影 ④ 阶段历史 + profile）
```

### Inspector 自校验范式

每个子阶段都有一个 `inspect-stage16g*` CLI 命令，inspect 不仅看 acceptance summary 的 status 字段，而是：

```text
① 重新读 source_digests 列出的源代码，sha256 重算 → 防止"摘要刷分但源代码偷换"
② 重新构造关键 report（如 schema_registration_report / profile_delta_report）
  与公开 evidence 做结构化对照 → 防止"篡改 evidence 但同步更新摘要"
③ 字段白名单严格枚举 → 任何未知字段一律拒
④ 公开扫描 forbidden marker → fail closed
```

新增子阶段时<b>必须</b>遵循同样范式。

---

## 【legacy】旧 agentic RL / verl 工作流背景

**本章描述旧白盒单体的训练链路，已冻结。rh2 的训练链路是 verifiers rollout → TrajectoryProjection（中立契约）→ EligibilityGate → slime / 离线导出 adapter。**

旧主链路：

```text
RepoHarness task
-> run_episode(real_episode)                rl/runtime.py:559
-> RepoHarnessEpisodeResult                 rl/episode.py:234
-> TrainingView / GenerationRecord
-> repo_harness_verl bridge
-> verl fully async rollout / MessageQueue / trainer smoke
```

新入口 `run-episode-task` / `run_episode(real_episode)` 是 canonical；旧 `run_task(...)` 只保留 legacy compatibility，不应作为新训练数据默认事实来源。

外部 provider（openai / deepseek 等）轨迹默认<b>不能</b>进 policy loss，因为缺少 verl 训练路径需要的 token / logprob provenance。mock route 同样<b>不能</b>进 policy loss。

---

## 【已搁置】两个 worktree 的并行协作

**2026-07 定案（设计文档 2 §1.5）：evaluation worktree 的迁移显式搁置，本章协作协议暂停生效。** 长期方向一句话：新架构下"评测 = 同一 Environment + EvalClient，训练 = 同一 Environment + TrainClient"，两个 worktree 不再需要各自维护 harness 语义；细化设计在 rh2 S1 跑通后单独一轮进行。以下为搁置前的协议存档。

```text
training_worktree:     当前仓库，public label 为 training_worktree
                       负责 verl / RL 训练链路、formal gates、数据 schema、reward、export、远端训练 smoke
evaluation_worktree:   相邻评测仓库，public label 为 evaluation_worktree
                       负责 SWE-Bench / 强模型真实任务测评、harness 能力诊断、score gap 排查
```

协作原则：

1. 两个 worktree 不能长期分叉出不同 harness 语义。评测 worktree 发现的共享链路 bugfix，应及时同步回 training worktree。
2. 训练 worktree 当前以 `run-episode-task` / `run_episode(real_episode)` 为 canonical 新入口。
3. evaluation worktree 仍会继续发现工具能力、public test、diagnostic shell、provider accounting、patch hygiene 等问题。若修复影响共享 harness 行为，不应只留在 evaluation worktree。
4. 未通过代表性 Stage 16.5 harness 诊断前，不应贸然冻结真实 Stage 17 数据 split、生产 Stage 20 warm-start 数据或启动 Stage 21 RL 训练。

公开文档<b>不要</b>写入真实本机绝对路径。需要引用另一个 worktree 时，使用 `source_worktree_label`、`source_commit`、`source_doc_sha256`、`opaque_ref` 这类 public-safe 字段；真实路径只应留在不提交的 runtime-private 报告里。

常见同步背景文档：

```text
docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md
docs/agentic_RL/training_design/stage16f_unified_baseline_handoff_to_evaluation_agent.md
evaluation worktree 的 docs/resume/stage16_5_execution_plan.md
evaluation worktree 的 docs/resume/repo_harness_vs_claude_code_capability_gap_analysis.md
```

---

## 新接手 agent 必读清单（rh2，2026-07 起）

按优先级排列。<b>★ 标记为强制必读</b>。

```text
★ AGENTS.md                                                  本文件（先读进度章节确认当前位置）
★ docs/harness_improve/repo_harness_design_doc2_verifiers_based.md
                                                             主设计文档：verifiers 基座架构 + 全部设计定案
★ docs/harness_improve/repo_harness_final_review_before_implementation.md
                                                             实施前最终检查：范围 P0/P1/P2/backlog、D1~D7 定案、
                                                             R3~R12 技术报告核对台账、简历叙事
★ docs/harness_improve/repo_harness_implementation_plan_v1.md
                                                             实施计划总纲：S0~S5、包结构、E 系列决策
★ docs/agentic_RL/repo_harness_rh2_workstreams/01-s0-execution-plan.md
                                                             当前执行计划：S0 任务清单、C 系列定案、残余未知 U-x
  docs/agentic_RL/repo_harness_rh2_workstreams/s0/implementation-notes.md
                                                             S0 执行中的决策 / 偏离 / 新未知（行车记录）
  docs/agentic_RL/training_design/repoharness_validation_experiment_design.md
                                                             验证实验设计（草案，S0-8 收口）
  docs/harness_improve/repo_harness_repositioning_after_polar.md
                                                             设计原则与硬边界来源（H1~H10 见其 §16）
  reference/*/CLAUDE.md                                      外部库导览（verifiers / slime / prime-rl 优先）
```

### 【legacy】旧架构选读清单

以下 A~G 清单服务于冻结的旧架构（16G 线），仅在需要理解旧契约出处或复核旧 evidence 时选读。

### A. 旧项目定位 + 旧进度

```text
docs/agentic_RL/repo_harness_verl_workstreams/49-stage-16g-0-execution-plan.md
docs/agentic_RL/repo_harness_verl_stage16g2c_completion_report.html
docs/agentic_RL/repo_harness_verl_harness_capability_acceptance_map.html
```

### B. 旧代码导览（理解 legacy 实现时选读）

```text
  docs/agentic_RL/code_guide_index.html                      代码导览总览：T0-T9 执行时间线 + 4 侧栏
  docs/agentic_RL/code_guide_t5_execute.html                 T5 工具执行（10 步调用链 + 13 段 code excerpt）
  docs/agentic_RL/code_guide_t8_projection.html              T8 投影（policy_loss 守门员 + 14 公开文件）
  docs/agentic_RL/code_guide_side_safety.html                侧栏 A：5 道安全防线 L1-L5
```

### C. 16G.3 设计阶段（已废弃——16G.3 不再执行，仅作历史参考）

```text
  docs/agentic_RL/repo_harness_verl_workstreams/55-stage-16g-3-execution-plan.md
                                                             16G.3 原始执行计划（700+ 行）
  docs/agentic_RL/repo_harness_verl_workstreams/56-stage-16g-3-preplan-design-decisions.md
                                                             16G.3 启动前设计决策审议
  docs/harness_improve/bash_tool_advice.md
                                                             微软 MAI-Thinking-1（2026-06-02）SWE RL 报告启发的
                                                             bash 工具 vs 结构化 DSL 设计辩论
  docs/agentic_RL/repo_harness_verl_stage16g3_plan_overview.html
  docs/agentic_RL/repo_harness_verl_stage16g3a_plan.html     共享底座 + 22 条要求 + Docker 隔离决策状态图
  docs/agentic_RL/repo_harness_verl_stage16g3b/c/d_plan.html
  docs/harness_improve/16G-3_advice.md / 16G-3_plan_V1.md
  docs/harness_improve/main_20260602_2.pdf                   MAI-Thinking-1 原始报告 PDF
```

### D. 三标杆参考 harness（视任务方向选读）

```text
docs/agentic_RL/repo_harness_verl_stage16g_4way_tool_comparison.html
                                                             Codex / Claude Code / mini-SWE-agent / RepoHarness 四方对比
docs/agentic_RL/repo_harness_verl_stage16g_codex_harness_overview.html
                                                             Codex 架构深度解读
reference/claude-code-typescript-src/AGENTS.md               Claude Code 参考源码导航
reference/codex/AGENTS.md                                    Codex 参考源码导航
docs/harness_improve/codex_vs_claude_code_harness_design_analysis.md
                                                             Codex vs Claude Code 横向对比
```

### E. 旧核心设计文档（描述 legacy 模块，看旧代码前先看）

```text
docs/00-reading-guide.md                                     阅读路径和当前文档定位
docs/01-project-positioning-and-requirements.md              项目定位 / 边界 / 版本进度
docs/02-system-architecture.md                               系统分层 / 模块职责 / 对象流
docs/04-tool-system-and-orchestration.md                     工具契约 / 执行顺序 / 权限交互
docs/05-workspace-sandbox-and-permissions.md                 workspace boundary / permission / Docker
docs/07-verifier-reward-and-evaluation.md                    verifier / accepted policy / reward metadata
docs/08-trajectory-store-and-training-export.md              RunRecorder / transcript / artifact manifest
docs/11-object-model-config-and-data-flow.md                 对象模型 / 配置字段 / 端到端数据流
```

### F. 旧训练设计文档（rh2 的训练实验以 repoharness_validation_experiment_design.md 为准，以下选读）

```text
docs/agentic_RL/training_design/post_stage15_training_infra_stage_plan.md
                                                             Stage 15 之后的训练基础设施分阶段计划
docs/agentic_RL/training_design/RL_algorithm_design.md       RL 算法设计
docs/agentic_RL/training_design/实验设计.md                  实验设计
docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md
                                                             两个 worktree 同步契约
docs/agentic_RL/training_design/stage16f_unified_baseline_handoff_to_evaluation_agent.md
                                                             evaluation worktree 交接文档
docs/agentic_RL/training_design/长链路 SWE Agent RL 在 verl 异步 Harness 中的落地研究.pdf
                                                             长链路 SWE Agent RL 设计研究
```

### G. 评测 worktree 同步背景（协作已搁置，仅存档）

```text
evaluation worktree 的 docs/resume/stage16_5_execution_plan.md
evaluation worktree 的 docs/resume/repo_harness_vs_claude_code_capability_gap_analysis.md
```

---

## 【legacy】常用复核命令（旧 evidence 复核仍可用）

**以下命令针对冻结的旧 evidence（stage16g_* / v2~v5），仍可运行用于复核历史，但不会再新增。rh2 的复核命令（`inspect-rh2-s1` / `inspect-rh2-artifact`）已随 S1 inspector 建立，见上文进度章节。**

### 16G 系列 inspector（旧线最新）

```bash
PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main \
  inspect-stage16g1-tool-profile \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_acceptance_summary.json \
  --assert-complete

PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main \
  inspect-stage16g2a-tool-surface \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/stage16g2a_acceptance_summary.json \
  --assert-complete

PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main \
  inspect-stage16g2b-file-mutation \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/stage16g2b_acceptance_summary.json \
  --assert-complete

PYTHONPATH=src PATH=.venv/bin:$PATH python -m repo_harness.cli.main \
  inspect-stage16g2c-projection-linkage \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16g_2/stage16g2c_acceptance_summary.json \
  --assert-complete
```

### 16F 系列 inspector

```bash
PATH=.venv/bin:$PATH repo-harness inspect-stage16f4-parity <summary> --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-stage16f5-entrypoint-policy <summary> --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-stage16f6-real-model-smoke <summary> --assert-complete
```

### 通用编译 + 单测

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

### 历史版本 acceptance（仍可用）

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance \
  runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance \
  runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle \
  runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs \
  runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance \
  runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json --assert-complete
```

---

## 接手前最关键的 4 个判断（不要犯）

1. <b>不要按任何旧文档去做 16G.3</b>。16G.3 ~ 16G.6 已被 rh2 新架构取代、永不执行。当前任务看本文进度章节 + `docs/agentic_RL/repo_harness_rh2_workstreams/` 下最大编号执行计划。凡是与设计文档 2 / final review / 实施计划总纲冲突的旧文档表述，一律以这三份为准。

2. <b>不要在 `rh2_formal_training_allowed = false` 时进入正式训练、数据冻结或 warm-start 数据生产</b>（旧 17B/20/21 闸门已作废，语义由 rh2 闸门承接）。强行进入会让训练 reward signal 被 hack、数据被污染。

3. <b>不要在冻结的 `src/repo_harness/` 上新增功能</b>。它是 legacy：旧 inspector / evidence 仍可复核历史，但新代码一律进 `rh2/`。也不要修改 `docs/agentic_RL/repo_harness_verl_workstreams/stage16g_*/` 下任何旧 evidence（source_digests 会失配）。旧代码的价值是契约（五道防线 / fail-closed inspector / 原子语义），这些契约在 rh2 里重新落位，实现不迁移。

4. <b>不要把凭据写进任何 git 追踪文件或产出物</b>。`deepseek_api.md` 等 key 文件已 gitignore，文档 / evidence / 代码只允许引用其路径，绝不允许出现 key 内容；提交前发现疑似凭据一律 fail closed 停下来问。

---

## 文档同步原则（rh2）

1. rh2 每个任务 / 阶段推进时，同步更新本 AGENTS.md 的进度章节（阶段状态、闸门字段）。
2. 执行中的设计决策 / 偏离计划 / 权衡 / 新未知，发现即记入当前阶段 evidence 目录的 `implementation-notes.md`（如 `repo_harness_rh2_workstreams/s0/implementation-notes.md`，分 Decisions / Deviations / New-Unknowns 三节）。
3. 执行计划文档不随手改：只有决策实质改变计划内容时才回写对应小节并标注日期——"计划是地图、notes 是行车记录"。
4. 每个任务完成 = 一个独立 commit（`rh2(s0-x): ...` 前缀），便于按 baseline diff 复查。
5. 不要修改已提交的旧 evidence（`stage16g_*/`、`runs/`）——source_digests 会失配。
6. legacy 章节（本文标【legacy】的部分）不再维护，只在纠错时更新。

---
