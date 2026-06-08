# RepoHarness Agent Guide

所有编写的文档或者注释，除了必要的专业词汇、命令名称、文件名、字段名和代码标识符之外，都使用清晰、详细、通俗易懂的中文。如果解释一个容易混淆的概念，尽量搭配具体数值、文件路径、命令或者实现例子。

## 项目一句话定位

RepoHarness 是一个面向软件工程智能体训练和评测的 Harness，目标是让真实或半真实仓库任务产生可执行、可审计、可导出的训练轨迹。核心闭环是：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

它不是 Claude Code、Cursor、OpenHands、SWE-agent、Codex 或官方 SWE-Bench harness 的复刻；也不要把它描述成生产级安全沙箱、分布式 rollout 服务、公开榜单系统、完整产品复刻或已经训练出模型的项目。

---

## 当前进度（接手前必读）

**重要：AGENTS.md 这一节经常需要随阶段推进同步更新。如果你接手时发现与最新 commit 不一致，请先以 `git log --oneline` 和 `docs/agentic_RL/repo_harness_verl_workstreams/` 下最新阶段执行计划 / 完成报告为准。**

截至本次更新（基于 commit `1e783f41 feat: complete stage 16g2 file mutation linkage` 之后）：

```text
Stage 13 / 14 / 15           已完成  RepoHarness ↔ verl fully async 桥接、partial rollout 远端 smoke
Stage 16A ~ 16E              已完成  execute_bash 收口 / diagnostic shell / 公开环境 prompt / verifier
                                    healthcheck / patch hygiene
Stage 16F.0 ~ 16F.7          已完成  统一新入口 run-episode-task / run_episode(real_episode)；旧
                                    run_task(...) 仅 legacy compatibility；真实 provider 小 smoke 完成
Stage 16G.0                  已完成  RepoHarness vs Claude Code / Codex / mini-SWE-agent 能力差距盘点
Stage 16G.0 follow-up        已完成  收紧 baseline 契约，加严 evaluator-only 边界
Stage 16G.1                  已完成  4 档 profile taxonomy + 工具 registry 契约（27 条能力）
Stage 16G.2A                 已完成  apply_patch / write_file / delete_file / move_file / mkdir
                                    结构化 schema 注册 + scaffold 暴露 + profile delta
Stage 16G.2A 修正            已完成  独立 delete/move/mkdir 退回 swe_public_extended，core 经
                                    apply_patch 表达
Stage 16G.2B                 已完成  共享 file_mutation 行为：preflight → snapshot → apply → rollback
                                    原子语义；audit artifact；FileMutationDenial 拒绝路径
Stage 16G.2C                 已完成  run_episode → write_run_episode_compat_projection 投影 linkage
                                    打通；14 个公开文件 + manifest + policy_loss 守门员
                                    audit_ref → audit_artifact_id 改名修复 L4 forbidden marker 冲突
Stage 16G.3                  设计阶段，未实施
                                    计划：公开命令 / 项目测试路由 / scratch Python 三件套
                                    当前重大讨论：是否参照微软 MAI-Thinking-1（2026-06-02）走
                                    bash(command:string) + SEE-equivalent 路线，详见
                                    docs/harness_improve/bash_tool_advice.md 和
                                    docs/agentic_RL/repo_harness_verl_workstreams/56-stage-16g-3-preplan-design-decisions.md
Stage 16G.4 ~ 16G.6          未开始
Stage 17B / 20 / 21          闸门仍 false，不允许进入数据冻结 / warm-start / 正式 RL
```

闸门字段当前真实值（来自 `stage16g2c_acceptance_summary.json`）：

```text
stage16g2c_complete = true
stage16g3_allowed_to_start = true
stage17b_real_data_freeze_allowed = false
stage20_warm_start_data_generation_allowed = false
stage21_formal_rl_allowed = false
```

---

## 仓库结构速览

### Python 主实现 `src/repo_harness/`

旧 V1 ~ V5 模块（仍在维护，作为版本闭环留作 acceptance）：

```text
v2_acceptance.py
v3_*.py               V3 Docker backend / SWE-Bench-like fixture / export audit / acceptance
v4_*.py               V4 task freeze / rollout / tool lifecycle / agent run / export quality / cards
v5_*.py               V5 evidence / export pack / provider gate / run matrix / demo artifacts
pre_verl_*.py         pre_verl agent loop / evaluation / evidence ledger / failure injection / run facts
```

agentic RL / verl 桥接相关模块（**当前训练链路主路径**）：

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
  其他               public_command_profiles 等待 16G.3 引入

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

agentic RL / verl 工作流文档（**当前主战场**）：

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

docs/harness_improve/                    外部 harness 设计参考与建议
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

## 关键代码架构（5 个值得新接手 agent 先理解的子系统）

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

## 当前 agentic RL / verl 工作流背景

主链路：

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

## 两个 worktree 的并行协作

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

## 新接手 agent 必读清单

按优先级排列。<b>★ 标记为强制必读</b>，其余按当前任务方向选读。

### A. 项目定位 + 当前进度（★ 全部必读）

```text
★ AGENTS.md                                                  本文件
★ docs/agentic_RL/repo_harness_verl_workstreams/49-stage-16g-0-execution-plan.md
                                                             16G.0 起点：盘点能力差距，理解项目当前为什么"暂不进 17A 数据冻结"
★ docs/agentic_RL/repo_harness_verl_stage16g2c_completion_report.html
                                                             最新已完成阶段的独立核验报告
★ docs/agentic_RL/repo_harness_verl_harness_capability_acceptance_map.html
                                                             27 条能力的四象限地图，含每个工具的"模型视角 / 实现位置 / 训练投影 / 阶段历史"
```

### B. 代码导览（★ 推荐都读，建立心智模型）

```text
★ docs/agentic_RL/code_guide_index.html                      代码导览总览：T0-T9 执行时间线 + 4 侧栏
  docs/agentic_RL/code_guide_t5_execute.html                 T5 工具执行（10 步调用链 + 13 段 code excerpt）
  docs/agentic_RL/code_guide_t8_projection.html              T8 投影（policy_loss 守门员 + 14 公开文件）
  docs/agentic_RL/code_guide_side_safety.html                侧栏 A：5 道安全防线 L1-L5
```

### C. 16G.3 设计阶段（如果你接手 16G.3 实施 ★ 必读）

```text
★ docs/agentic_RL/repo_harness_verl_workstreams/55-stage-16g-3-execution-plan.md
                                                             16G.3 原始执行计划（700+ 行）
★ docs/agentic_RL/repo_harness_verl_workstreams/56-stage-16g-3-preplan-design-decisions.md
                                                             16G.3 启动前设计决策审议
★ docs/harness_improve/bash_tool_advice.md
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

### E. 核心设计文档（旧但仍然准确，看模块前先看）

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

### F. 训练设计（如果你接手 RL 算法 / 训练流程 ★ 必读）

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

### G. 评测 worktree 同步背景（如果你需要跨 worktree 协作）

```text
evaluation worktree 的 docs/resume/stage16_5_execution_plan.md
evaluation worktree 的 docs/resume/repo_harness_vs_claude_code_capability_gap_analysis.md
```

---

## 常用复核命令

### 16G 系列 inspector（最新）

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

## 接手前最关键的 3 个判断（不要犯）

1. <b>不要默认 16G.0 是当前任务</b>。16G.0 / 16G.1 / 16G.2A / 16G.2B / 16G.2C 都已经完成。<b>当前任务是 16G.3 的设计冻结和实施前评估</b>。如果你打开仓库发现 16G.3 还没启动，那就是当前位置；如果已经启动了，看 `git log` 和 `docs/agentic_RL/repo_harness_verl_workstreams/` 下最大编号的执行计划。

2. <b>不要直接进入 Stage 17 数据冻结、Stage 20 warm-start 数据生成或 Stage 21 正式 RL</b>。所有 acceptance summary 的 17B / 20 / 21 闸门<b>都是 false</b>，必须经过 16G.3 ~ 16G.6 才能开。强行进入会让真实数据被污染、训练 reward signal 被 hack。

3. <b>不要把"运行 tools/file_mutation.py 的真实写盘"或"绕过 visibility.py 的 forbidden marker"当成"可以临时这么做"</b>。这两个机制是整个 16G.2 series 的成果，任何"我这次只是测试一下"的临时绕过都会让后续 inspector fail closed。新增字段或新增写盘动作必须先查：

```text
新写盘动作  → 是否走 _apply_prepared_operation（不变量 I-2）
新字段名    → 是否在 rl/visibility.py:56 的 forbidden 集合里（FORBIDDEN_FIELD_MARKERS）
新公开文件  → 是否含 _FORBIDDEN_PUBLIC_MARKERS（episode_projection.py:46）
新 evidence → 是否被 inspector 的字段白名单覆盖
```

---

## 文档同步原则

修改 RepoHarness 主链路代码时（特别是 `rl/runtime.py` / `tools/minimal.py` / `tools/file_mutation.py` / `evaluation/episode_projection.py` / `rl/visibility.py`），必须：

1. 同步更新本 AGENTS.md 的"关键代码架构"章节（如果接口变化）
2. 同步更新对应阶段的 implementation-notes.md（用户需要知道的设计决策 / 偏离 / 权衡 / 开放问题）
3. 同步更新代码导览（`docs/agentic_RL/code_guide_*.html`）的相关章节
4. 不要修改已经提交的 stage16g_*/ 下任何 evidence JSON（会让 source_digests sha256 失配，inspector 失败）

---
