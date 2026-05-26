# Stage 16G.1 Implementation Notes

## 设计决策

1. Stage 16G.1 新增可复用模块 `src/repo_harness/stage16g_tool_profile.py`，让 builder、CLI inspector 和单元测试共用同一套 registry / profile / gate 校验逻辑，避免只靠一次性脚本生成 JSON。
2. `run_episode` smoke 原先只验证 `EpisodeExecutionSpecToolFacts`，经过子代理复核后改为真实调用 `run_episode_task` 的 mock 小闭环。现在 smoke 会经过 `EpisodeExecutionSpecBuilder`、`RepoHarnessRuntime.run_episode(real_episode)` 和 `write_run_episode_compat_projection`，公开 evidence 只保存状态、公开投影摘要和 sha256，不保存临时路径或 raw artifact。
3. 训练投影字段分成工具事件层和样本层：单个工具事件不是 policy loss sample，`allowed_in_policy_loss_trajectory` 只表示该工具事件是否允许出现在合格轨迹中。
4. CLI inspector 不再只校验文件 sha256 和重新推导结果是否通过；现在会把 `stage16g1_acceptance_summary.json` 中的核心计数、机器检查状态、路径泄漏扫描状态、Stage 16G.2 放行字段，以及 Stage 17B / Stage 20 / Stage 21 禁止字段逐项反向校验。
5. `swe_public_extended` 和 `persistent_diagnostic_session` 明确记录 session reset、artifact hygiene、路径脱敏和 public-safe projection 边界。这样后续如果把 persistent diagnostic shell 接进扩展 profile，不能绕过这些训练安全条件。
6. 第二轮外部复核发现 inspector 对 evidence 篡改仍然不够强：`stage16g1_source_inventory.json` 没有纳入 summary digest，且 path leak scan 只信任旧报告。现在 summary 增加 `source_inventory_sha256`，inspector 会校验 Stage 16G.0 输入文件覆盖和 sha256，并且每次验收时重新扫描当前公开 evidence。

## 偏离

1. Stage 16G.1 没有新增真实模型可见工具。`apply_patch`、`run_public_command`、`run_project_test` 和 `scratch_python` 都只进入 registry 的 planned 状态，行为实现留给 Stage 16G.2 / 16G.3。
2. `stage16g1_run_episode_profile_smoke_report.json` 没有调用外部 provider，也没有运行真实 SWE 任务；它使用本地 fixture 和 mock route，只证明统一入口、执行规格和公开投影路径可达。这样可以避免把 Stage 16G.1 从 profile / gate 阶段扩大成工具行为阶段。

## 权衡

1. registry 对部分能力使用 `planned`、`partial` 或 `schema_reserved` 状态，而不是强行假装已经实现。这样会让 Stage 16G.2 之后的待办更明显，但也让 Stage 16G.1 的验收更严格。
2. 当前 evidence 不包含真实本机路径；所有 source inventory 只保存 repo-relative path 和 sha256。定位时少了一点便利，但符合 public evidence 边界。
3. smoke 选择 `tests/fixtures/tasks/task_stage16f3_passing.yaml`，让公开报告中的 `result_status` 是 `succeeded`。这不是为了证明工具能力已经提升，而是为了让 Stage 16G.1 的入口连通性证据更干净。
4. inspector 现在拒绝 `stage16g1_acceptance_summary.json` 的未知字段。这样可以防止有人把本机路径或未审计字段塞进 summary 后仍然通过验收，代价是以后如果需要新增 summary 字段，必须同步更新 inspector。

## 开放问题

1. Stage 16G.2 开始实现文件和 patch 工具时，是否把 `write_file` 作为独立工具，还是扩展 `create_file` 的覆盖语义，需要在 Stage 16G.2 计划中明确。
