# Stage 16G.2 Implementation Notes

## Stage 16G.2A

- 历史说明：Stage 16G.2A 最初只完成 structured file tools 的 schema、默认工具注册、scaffold 暴露、profile delta 和机器 evidence，executor 返回结构化的 `stage16g2a_behavior_not_enabled` 拒绝，不修改工作区。复核后默认工具面已收敛为只暴露 `write_file` 和 `apply_patch`；独立 `delete_file`、`move_file`、`mkdir` 只保留为 extended profile / 内部能力。
- 设计决策：`write_file` 的 core schema 只允许 `mode="create"` 和 `mode="overwrite"`，没有暴露 `mode="upsert"`。如果后续要支持 upsert，需要显式 profile gate。
- 设计决策：`apply_patch` 只暴露结构化 `operations` schema，不暴露 shell patch、`git apply` 或 free-form unified diff 字段。
- 前置复核：开始 Stage 16G.2A 代码修改前，已重新运行 Stage 16G.1 inspector，结果为 `status="passed"` 且 `failure_count=0`。Stage 16G.1 已提交 evidence 不在本阶段原地改写。
- 权衡：Stage 16G.2A 只把 `write_file` 和 `apply_patch` 加入 `DEFAULT_TOOL_ORDER` 和 `simple_react`，是为了让 run_episode 的 schema snapshot 和 profile delta 能看见主训练默认入口；独立 `delete_file`、`move_file`、`mkdir` 保留为可构造 ToolDefinition 和 extended profile 能力，同时用 schema-only 拒绝避免在 Stage 16G.2B 前产生半成品写入行为。
- 复核后修正：Stage 16G.2A inspector 现在会重新构建 `schema_registration_report`、`scaffold_exposure_report`、`tool_surface_delta_report` 和 `profile_delta_report`，并与公开 evidence 做结构化对照。这样即使有人篡改详细工具列表并同步更新摘要里的 sha256，只要报告内容不再等于当前代码和 Stage 16G.1 输入重新推导出的结果，验收也会失败。
- 设计修正：Stage 16G.2B 行为实现前收敛主训练默认工具面。`write_file` 和 `apply_patch` 继续默认可见；独立 `delete_file`、`move_file`、`mkdir` 保留 schema 和 extended profile 能力，但不进入 `swe_public_core` 默认 scaffold。删除、移动和目录创建默认通过 `apply_patch.operations` 表达，Stage 16G.2B 必须验证一元删除和一元移动不会因此变得笨重或脆弱。
- 设计修正：删除和移动 operation 增加模型提供的 `reason` 字段。它不同于 harness 拒绝时的 `reason_code`，用于记录模型为什么认为该删除或移动是正确修改，后续可用于审计、reward attribution 和 reward hacking 诊断。

## Stage 16G.2B

- 设计决策：新增 `src/repo_harness/tools/file_mutation.py` 作为共享文件变更服务，`write_file`、`apply_patch` 以及 extended profile 中的独立 `delete_file`、`move_file`、`mkdir` 都走同一个路径检查、UTF-8 检查、哈希检查、操作审计和拒绝语义。
- 设计决策：`apply_patch` 第一版采用“所有 operation 预检通过后再写入”的语义；预检阶段发现 stale hash、隐藏路径、二进制文件或重复触碰同一路径时，不修改任何文件。若预检通过后运行时仍发生极少数写入失败，会返回 `partial_failure=true`、rollback fact，并默认标记为不可进入训练、official prediction 或训练导出。
- 设计决策：为了保持第一版原子语义清晰，单次 `apply_patch` 暂时拒绝多个 operation 触碰同一路径。大规模同文件改写应先使用 `write_file(mode="overwrite")` 搭配显式 `expected_content_hash`，后续如果要支持同文件多段结构化替换，需要增加虚拟文件状态预检。
- 权衡：`move_file` 目标父目录会自动创建，理由是保持“移动单个文件”路径足够直接，避免模型为了一次重命名额外构造 `mkdir` operation。这个行为会在 operation audit 中保留移动事实，Stage 16G.2C 再继续检查 patch/export linkage。
- 权衡：Stage 16G.2B 路径拒绝规则暂时较保守，继续拒绝 `.git`、runtime-private、依赖目录以及常见生成物目录。Stage 16G.5 parity probe 需要统计真实 SWE 任务中的拒绝率，再决定是否按项目类型放宽 `build`、`dist` 等目录。
- 复核后修正：写入入口现在会对 path segment 做敏感 marker 归一化匹配，小写并去掉 `-`、`_`、`.` 等分隔符后拒绝 runtime-private、RepoHarness runtime、参考补丁、隐藏测试选择器、隐藏或正式 verifier、reward metadata 和 provider secret 等命名变体，避免模型新建 evaluator-only 或 runtime-private 伪装路径。
- 验收补充：新增 Stage 16G.2B probe 证据，覆盖 `write_file` create/overwrite、`apply_patch` 批量操作、一元删除、一元移动、安全拒绝、原子预检和 extended standalone 工具可执行性。公开 evidence 只记录状态、operation kind、路径数量和 artifact sha256，不记录临时仓库绝对路径或原始文件内容。

## Stage 16G.2C

- 设计决策：Stage 16G.2C probe 直接调用 `RepoHarnessRuntime.run_episode(real_episode)`，再调用统一的 `write_run_episode_compat_projection` 生成兼容投影。这样验证的是真实 episode 入口、结构化文件工具、final patch、patch hygiene、TrainingView 和兼容投影之间的 linkage，而不是只验证离线 JSON builder。
- 实施中发现并修正：Stage 16G.2B 文件变更工具成功结果的模型可见 payload 曾包含字段名 `audit_ref`，会被 gateway 的 forbidden marker 检查拒绝。现在模型可见字段改为 `audit_artifact_id` / `audit_artifact`，完整审计仍通过 `artifact_refs` 和私有 artifact 绑定。
- 验收边界：Stage 16G.2C 只证明 mock route 下的结构化文件变更能被公开安全地投影，并且 tool observation 的 response mask 为 0；它不把 mock route 轨迹放入 policy loss，也不放行 Stage 17B 数据冻结、Stage 20 warm-start 数据生成或 Stage 21 正式强化学习。
