# Stage 16G.2 Implementation Notes

## Stage 16G.2A

- 设计决策：本阶段只完成 structured file tools 的 schema、默认工具注册、scaffold 暴露、profile delta 和机器 evidence。`write_file`、`apply_patch`、`delete_file`、`move_file`、`mkdir` 现在会被注册并进入默认工具面，但 executor 只返回结构化的 `stage16g2a_behavior_not_enabled` 拒绝，不会修改工作区。真实文件行为留给 Stage 16G.2B。
- 设计决策：`write_file` 的 core schema 只允许 `mode="create"` 和 `mode="overwrite"`，没有暴露 `mode="upsert"`。如果后续要支持 upsert，需要显式 profile gate。
- 设计决策：`apply_patch` 只暴露结构化 `operations` schema，不暴露 shell patch、`git apply` 或 free-form unified diff 字段。
- 前置复核：开始 Stage 16G.2A 代码修改前，已重新运行 Stage 16G.1 inspector，结果为 `status="passed"` 且 `failure_count=0`。Stage 16G.1 已提交 evidence 不在本阶段原地改写。
- 权衡：Stage 16G.2A 把新工具加入 `DEFAULT_TOOL_ORDER` 和 `simple_react`，是为了让 run_episode 的 schema snapshot 和 profile delta 能看见目标工具；同时用 schema-only 拒绝避免在 Stage 16G.2B 前产生半成品写入行为。
- 复核后修正：Stage 16G.2A inspector 现在会重新构建 `schema_registration_report`、`scaffold_exposure_report`、`tool_surface_delta_report` 和 `profile_delta_report`，并与公开 evidence 做结构化对照。这样即使有人篡改详细工具列表并同步更新摘要里的 sha256，只要报告内容不再等于当前代码和 Stage 16G.1 输入重新推导出的结果，验收也会失败。
