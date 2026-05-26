# Stage 16G.0 Follow-up Implementation Notes

## 设计决策

1. 本次实现新增了独立 builder：`scripts/pre_verl/build_stage16g0_baseline_contract_followup.py`，用于生成 Stage 16G.0 follow-up 的 baseline contract、逐能力对照和 follow-up 验收摘要。
2. mini-SWE-agent 本地没有官方仓库源码，因此 follow-up 计划改为优先使用 evaluation worktree 中已经保存的真实配置、public-safe 配置摘录和运行日志摘要。公开产物中只能使用 `evaluation_worktree`、repo-relative path、sha256 和 opaque ref，不能写真实本机绝对路径。
3. 对 mini-SWE-agent 的外部可观察行为，例如单一 Bash 闭环、stdout / stderr / exit code 反馈和缺少结构化工具分层，可以给出中高置信判断；对动作解析、安全机制和完整 sandbox 细节，必须标记 `confidence=medium` 和 `primary_source_verification_required=true`。
4. follow-up 计划明确采用“结构化公开命令优先”的主 SWE 强化学习 core profile 假设：用 `run_public_command`、`run_project_test` 和 `scratch_python` 覆盖动态验证能力，把 persistent shell 放入 `swe_public_extended`，不作为 core 默认能力。
5. 第一轮 `stage16g0_acceptance_summary.json` 被视为 immutable。新增四个 baseline 产物需要单独由 `stage16g0_followup_acceptance_summary.json` 绑定 sha256 和派生计数。
6. 子代理只读复核指出 follow-up summary 的 `validation_checks` 初版偏静态。已改为从实际生成的 Claude Code contract、mini-SWE-agent contract 和 per-capability comparison 重新推导。
7. 根据 Stage 16G.0 follow-up 识别出的阻塞能力，新增后续阶段计划 `docs/agentic_RL/repo_harness_verl_workstreams/51-stage-16g-1-to-16g-6-execution-plan.md`。该计划把 Stage 16G.1 到 Stage 16G.4 定义为实现阶段，把 Stage 16G.5 定义为改造后的 parity probe，把 Stage 16G.6 定义为主 SWE 强化学习工具 profile 冻结和训练放行门禁。
8. 子代理只读复核后，后续阶段计划已经补上 `task_management_todo` 在 Stage 16G.2 的承接、Stage 16G.5 的硬性失败阈值、Stage 16G.6 的纯冻结定位、Stage 16G.3 probe 的依赖前置条件，以及 `post_16G_optional` 能力在 Stage 16G.1 registry 中的保留字段要求。
9. 根据后续复核建议，51 号计划继续补强了六个边界：Stage 16G.1 必须有机器验收器；Stage 16G.3 必须先统一 shared public command execution substrate；`task_management_todo` 保留在 Stage 16G.2D 但标为 P2 non-blocking；Stage 16G.4 只产出 reward metadata / quarantine facts，不提前设计数值型 process reward；所有新增能力必须绑定 `run_episode(real_episode)`；每个新增工具都要验证模型可见说明、public environment 提示、scaffold/profile 暴露和实际 executor registry 一致。

## 偏离

1. 原 follow-up 计划只列出四个新增 JSON 产物。本次根据 R3 增加第五个 follow-up 验收摘要：`stage16g0_followup_acceptance_summary.json`，并由 builder 派生计数和 sha256。
2. 原 follow-up 计划把 mini-SWE-agent primary source 放在来源优先级第一位。本次根据当前本地事实改为优先使用 evaluation worktree 已有真实配置和运行日志，并把官方源码验证留给后续补充。
3. 原 Stage 16G.0 主计划中 Stage 16G.5 的描述是“Claude Code parity probes 与 mini-SWE-agent 对照诊断”。本次改为“改造完成后的 parity probe”，避免后续接手者误读成第一次 baseline 对照。
4. 新增后续阶段计划时，我把原 requirements 中集中在 Stage 16G.4 的训练资格、reward linkage 和 export projection 单独在 Stage 16G.6 做最终冻结门禁。这样没有改变 Stage 16G.4 的实现责任，但避免把“实现 linkage”和“训练放行冻结”混成一个阶段。
5. 子代理指出 Stage 16G.2 原本把 `final_answer_verifier_reward_linkage` 放进必须覆盖能力，容易和 Stage 16G.4D 混淆。已改为 Stage 16G.2 只产出文件、补丁和任务状态动作的结构化事实，完整 final answer / verifier / reward linkage 仍由 Stage 16G.4D 收口。
6. 后续计划把 `task_management_todo` 继续放在 Stage 16G.2，是为了保持和 baseline comparison 的 `required_stage` 一致；但它不是 `blocking_for_main_swe_rl=true`，因此计划明确它不能阻塞 apply_patch / write_file / delete / move / mkdir 这些 P0 文件工具主线。

## 权衡

1. 没有在公开计划文档中写入真实本机绝对路径。这样牺牲了一点定位便利，但符合项目对 public evidence 的路径脱敏要求。
2. 没有把 mini-SWE-agent 结论全部降为低置信。评测 worktree 的真实配置和运行日志足以支持外部行为层面的中高置信判断；只有内部机制细节需要等待官方源码验证。
3. 没有建议 RepoHarness 复制 mini-SWE-agent 的裸 shell 形态。计划把 mini-SWE-agent 作为动态诊断能力下限，而不是实现形态目标，这样可以同时保留 RepoHarness 的防泄漏和训练审计边界。
4. 后续阶段计划没有把 persistent diagnostic shell 放入主 SWE 强化学习默认 profile。它被放入 `swe_public_extended`，原因是 persistent shell 对真实诊断很重要，但也最容易带来 session 残留、路径泄漏和依赖污染风险。

## 开放问题

1. Stage 16G.0 follow-up 当前只选了一组代表性 mini-SWE-agent smoke / official 日志和配置作为 source inventory。是否需要把同一 run directory 下更多 `mini_swe_agent_b0_*` 日志纳入 inventory，可以在 Stage 16G.5 parity probe 前再决定。
2. 如果后续能联网或取得 mini-SWE-agent 官方仓库源码，是否要求在 Stage 16G.5 前升级 `stage16g0_mini_swe_agent_baseline_contract.json` 的 source evidence。
3. `run_public_command`、`run_project_test` 和 `scratch_python` 的最终工具 schema 应该在 Stage 16G.1 设计阶段确定；当前 follow-up 只固定能力覆盖目标，不固定具体 schema。
4. Stage 16G.6 是否最终保留为独立阶段，还是在 Stage 16G.5 全部 probe 通过后合并为验收门禁，可以由后续执行者根据 Stage 16G.4 的实现规模决定。当前文档选择保留独立 Stage 16G.6，是为了让训练放行条件更清楚。
