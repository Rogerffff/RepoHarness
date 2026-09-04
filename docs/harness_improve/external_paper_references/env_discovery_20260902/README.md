# 环境层第二阶段调查包（env_discovery_20260902）

状态：**调查完成，外部调研任务书已就绪待派发，环境层工作波次未定案。**
首次调查日期：2026-09-02
性质：本目录服务环境层的方向收敛与工作规划，不预先决定 E-Wave 排期，也不改变
任何已定案的训练语义或闸门。讨论阶段不套开发期协作手册。

## 背景

方向发现（`../direction_discovery_20260818/`）确定了分层交付兜底框架（infra 层
+ 环境层是简历项目基本交付，无论最终实验做什么）与三条暂定主线（A 环境资格 / B
多 harness / C OPD）。本轮把环境层单独拿出来做深度盘点：现状、可复用资产、外部
增量、工作波次。

## 文件

### analysis/（本轮产出的调查与分析）

- `rh2_env_layer_status_20260902.md`：本项目环境层现状盘点（subagent，very
  thorough）。核心结论"资产硬、门缺、线断"——216 题数据身份链已建成且防篡改极硬，
  但四门 runner / `grade_controlled_patch` / EnvValidationReport 零实现，216 题训练
  链上零消费者。
- `pi_environment_assets_20260902.md`：Prime Intellect 生态现成环境资产盘点
  （subagent）。73 个环境分类清单 + verifiers v1 抽象 ownership + 对"扩展第二可验证
  域"的可复用度判断。核心结论：terminal 域（Harbor 格式薄壳）是最优第二域候选。
- `external_env_increment_20260902.md`：环境生产/资格化/规模化的外部增量补查
  （subagent 实时检索）。prime-rl v0.9.0 admission gates、Envs-FORGE、Nebius 成本
  数字、Surge 跨域迁移等锚点外增量。
- `claude_env_layer_analysis_20260902.md`：**Claude 综合分析与规划建议**（讨论
  材料）。环境坐标系、现状合并地图、portfolio 建议、E-Wave1~4 工作波次、5 个待
  拍板项。三份调查的收束入口。
- `verifiers_v031_primerl_v090_impact_20260902.md`：verifiers 升级影响面 +
  prime-rl admission gates 摘录（subagent 代码级，clone 到 scratchpad 分析）。
- ~~`harbor_miles_integration_audit_20260902.md`~~：Harbor⇄miles 集成两形态（T-a 黑盒 /
  T-b capture 主线）代码级审计——**未产出**（调查 agent 被 owner 停止，按取消处理）。
  已知事实的现有出处：`claude_env_layer_analysis_20260902.md` 第三节的 T-a/T-b 取舍分析
  + `reference/miles/examples/swe-agent-harbor-docker/README.md`（T-a 形态、timeout 联动、
  aborted 样本拖垮 GRPO 组等一手细节）。如需重做，已作为可选任务 4 挂进
  `prompts/codex_env_code_audit_brief.md`。
- `codex_env_code_audit_<date>.md`：codex 本地代码级审计（待生成，见 prompts）。

### prompts/（外部调研与 codex 任务书，待派发）

- `common_env_brief.md`：三个任务书共用的项目事实与资源边界。
- `pro_env1_qualification_synthesis.md`：Pro 任务 1——环境资格化与合成配方深挖。
- `pro_env2_terminal_domain.md`：Pro 任务 2——terminal 作为第二可验证域尽调。
- `codex_env_code_audit_brief.md`：codex 任务书——E-Wave1 实现切片 + 换表接线面
  + W3b 归属线。

## 关键结论速览（详见 claude_env_layer_analysis）

1. 环境坐标系：harness 从环境包拆出为独立轴；taskset×verifier 决定训什么测什么。
2. 最大杠杆：E-Wave1（接线 + 补四门，两周）兜住分层交付的底；E-Wave2（Harbor
   terminal，低成本第二域）为 C 线 specialist 与评测层铺路。
3. 研究差异点（admission gates 进 prime-rl 正式版后）：不在"做一个资格门"，而在
   "贯通到训练资格的可审计整链 + 诚实良率/成本数字"。
4. 五个待拍板项：E-Wave1 启动时机 / terminal 第二域定案 / held-out 冻结方案 /
   W3b 归属线 / verifiers pin 升级。

## 单篇精读（knowledge/ 同批产出）

本轮为环境层配套精读了 7 篇论文，存 `../../../../knowledge/`：MOPD、CalibForge
（solver 校准）、Envs-FORGE、Harness Interplay、Endless Terminals、SWE-smith、
Surge office-RL。
