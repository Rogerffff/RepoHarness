# RepoHarness V4 范围审查记录

## 1. 审查目标

本文件记录 V4 范围文档的只读探索、范围审查、训练数据边界审查、工程可执行性审查和修复记录。审查对象是：

- `docs/v4/scope-and-roadmap.md`

本轮任务只编写 V4 范围文档和必要审查记录，不实现 V4 代码，不修改 V3 运行逻辑，不修改 V3 acceptance 产物。

## 2. 只读基线确认

范围编写前已执行以下只读确认：

```bash
git status --short
git log -1 --oneline
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
```

确认结果：

- V3 closure commit 为 `17b1b95 fix: handle excluded post acceptance docs`；范围编写前 HEAD 指向该提交。后续 V4 文档提交后，应检查 `17b1b95` 是否仍是当前 HEAD 的祖先，而不是要求 HEAD 永远停在该提交。
- V3 acceptance report inspect 通过，状态为 `passed`。
- V3 acceptance bundle immutable inspect 通过，状态为 `passed`。
- 工作区存在与本任务无关的既有脏改动和未跟踪文件；本轮范围编写不删除、不回滚、不覆盖这些内容，只新增 `docs/v4/` 下的 V4 文档。

## 3. 必读材料覆盖记录

本轮范围设计已经阅读并使用以下材料：

项目总览和设计文档：

- `AGENT.md`
- `docs/02-system-architecture.md`
- `docs/03-agent-loop-and-message-protocol.md`
- `docs/04-tool-system-and-orchestration.md`
- `docs/05-workspace-sandbox-and-permissions.md`
- `docs/06-task-dataset-and-environment-adapters.md`
- `docs/07-verifier-reward-and-evaluation.md`
- `docs/08-trajectory-store-and-training-export.md`
- `docs/09-agent-scaffolds-and-multi-agent.md`
- `docs/10-context-session-and-failure-diagnostics.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/13-agentic-technical-report-reading-map.md`

V3 文档：

- `docs/v3/scope-and-roadmap.md`
- `docs/v3/implementation-plan.md`
- `docs/v3/final-acceptance.md`
- `docs/v3/walkthrough.md`
- `docs/v3/swe-task-feasibility-experiment-plan.md`
- `docs/v3/review/scope-review.md`
- `docs/v3/review/implementation-plan-review.md`
- `docs/v3/review/swe-task-feasibility-results.md`
- `docs/v3/review/implementation/`
- `docs/v3/implementation-log/`

V2 / V1 参考：

- `docs/v2/scope-and-roadmap.md`
- `docs/v2/implementation-plan.md`
- `docs/v2/final-acceptance.md`
- `docs/v2/walkthrough.md`
- `docs/v1/final-acceptance.md`
- `docs/v1/walkthrough.md`

技术报告材料：

- `docs/13-agentic-technical-report-reading-map.md`
- `/Users/roger/Desktop/technical_report_agentic/FIRST5_REPOHARNESS_SYNTHESIS.md`

V4 新增前置设计：

- `docs/v4/swe-task-feasibility-experiment-plan.md`

Claude Code 参考实现：

- `reference/claude-code-typescript-src/AGENT.md`
- query loop 相关源码：`query.ts`、`QueryEngine.ts`
- tool lifecycle 相关源码：`Tool.ts`、`services/tools/toolOrchestration.ts`、`services/tools/toolExecution.ts`
- permission decision 相关源码：`utils/permissions/permissions.ts`、`hooks/useCanUseTool.tsx`
- hook lifecycle 相关源码：`services/tools/toolHooks.ts`、`types/hooks.ts`、`commands/hooks/hooks.tsx`
- MCP 相关源码：`tools/MCPTool/MCPTool.ts`、`services/mcp/client.ts`、`commands/mcp/mcp.tsx`
- slash command / skill 相关源码：`commands/skills/skills.tsx`
- session / context / memory 相关源码：`services/compact/autoCompact.ts`、`utils/toolResultStorage.ts`
- subagent / sidechain transcript 相关源码：`tools/AgentTool/AgentTool.tsx`、`tools/AgentTool/runAgent.ts`、`tools/AgentTool/forkSubagent.ts`
- background or concurrent tool execution 相关源码：`tasks/LocalAgentTask/LocalAgentTask.tsx`、`tasks/LocalShellTask/LocalShellTask.tsx`

## 4. 初稿自审结论

初稿自审重点：

1. 是否准确继承 V3 已实现基线。
2. 是否把 V4 最小完成定义限制在三条 P0 主线上。
3. 是否把 provider/scaffold matrix、permission/hook、context strategy、dataset card、MCP、retrieval、subagent 放在 P1 或 P2，而不是硬核心。
4. 是否明确保留 evaluator-only evidence 隔离、PreparedMessages 与 export observation 绑定、final verifier 权威性和 V2/V3 export 契约。
5. 是否把 `preference_pair_baseline_blocked` / `no_trainable_preference_pair` 作为 V4 待解决的训练导出质量问题，而不是描述成已解决。
6. 是否明确写出 V4 非目标。

初稿自审结果：

- 未发现 P1 阻塞问题。
- 未发现 P2 必须修复问题。
- 发现一个需要持续关注的 P3 风险：P1/P2 候选范围较多，后续 implementation plan 必须把它们放在 P0 稳定后的 gating 阶段，避免计划阶段重新膨胀。

## 5. Subagent 只读审查安排

本轮环境支持 subagent，因此范围文档草稿完成后安排三个只读 subagent 审查。所有 subagent 的要求都是：只读，不修改文件，只报告发现。

### 5.1 范围一致性审查

审查问题：

- 是否继承 V3。
- 是否没有把 V4 写成完整训练集群。
- 是否没有把 V4 写成完整 Claude Code / Codex 产品复刻。
- 是否和 RepoHarness 的可执行、可审计、可导出训练轨迹目标一致。

审查状态：已完成。

审查结论：

- 未发现 P1 必须修复问题。
- 未发现 P2 必须修复问题。
- V4 范围没有被写成完整训练集群；核心仍限定为单机队列、租约、重试、资源锁、可恢复批处理和可审计运行选择。
- V4 范围没有被写成完整 Claude Code / Codex 产品复刻；Claude Code 相关能力被降维为 policy snapshot、permission trace、context replacement trace、artifact reference、sidechain transcript manifest 等审计事实。
- V3 已实现基线继承总体准确，包括真实 Docker backend、真实 repository-level task、固定 SWE-Bench-like 小子集、context compaction、export audit、PreparedMessages 与 export observation 绑定、显式 acceptance inputs，以及 `preference_pair_baseline_blocked` / `no_trainable_preference_pair` 作为非阻塞残余项。
- 残余 P3 风险：P1/P2 候选范围数量较多，后续 implementation plan 必须继续防止 provider matrix、hook、context strategy、MCP、retrieval、subagent 等增强项重新挤占 P0。

### 5.2 训练数据和评测边界审查

审查问题：

- 是否继续保护 evaluator-only evidence。
- 是否没有把 reward、verifier、gold patch、hidden test selector、provider raw response 放进训练 payload。
- 是否 final verifier 仍然是成功和 reward 主事实的权威来源。
- 是否把 `preference_pair_baseline_blocked` / `no_trainable_preference_pair` 合理转化为 V4 候选，而不是掩盖为已解决。

审查状态：已完成。

审查结论：

- 未发现 P1 必须修复问题。
- 发现并修复 1 个 P2 问题：训练 payload 禁止项中，对 reward scalar、reward label、verifier 原始输出、verifier trace、隐藏测试执行细节的模型可见边界需要写得更硬。
- 已在 `docs/v4/scope-and-roadmap.md` 的 P0-3 验收原则中补充：reward scalar、reward label、verifier 原始输出、verifier trace、隐藏测试执行细节和隐藏 selector 命中细节只能作为评测、审计、筛选、分层或外部元数据使用；如果需要随导出保留，也必须位于非模型可见字段中，并接受 export policy、visibility policy 和污染扫描约束，不能进入模型可见训练 payload 或训练 target 文本。
- `preference_pair_baseline_blocked` / `no_trainable_preference_pair` 已被正确转化为 V4 待解决目标和阻塞原因报告要求，没有被掩盖为已解决。
- 残余 P3 风险：后续 implementation plan 仍需要把 trainable payload、diagnostic-only metadata、external audit metadata 的字段边界写成明确 schema 和 negative test。

### 5.3 工程可执行性审查

审查问题：

- P0 是否能在一个版本内完成。
- P1/P2 是否没有挤掉 P0 主线。
- 是否有明确机器产物和 inspect 验收方向。
- 是否避免大规模云集群、完整榜单、完整产品复刻等过大范围。

审查状态：已完成。

审查结论：

- 未发现 P1 必须修复问题。
- 未发现 P2 必须修复问题。
- P0 三条主线整体可以在一个版本内完成，前提是后续 implementation plan 严格按 P0 机器产物、inspect 验收、negative tests、RUN_SELECTION_MANIFEST 和 ACCEPTANCE_INPUTS 推进，不把 P1/P2 提前并入最小完成门槛。
- 文档已经明确避免大规模云集群、完整 SWE-Bench 榜单、完整 Claude Code / Codex 产品复刻等过大范围。
- 残余 P3 风险：P0 仍然偏紧，尤其是“约 10 个 accepted / auditable tasks”加上 baseline verifier、flaky detection、source materialization repeat check，会消耗较多工程和验证时间。范围文档已经保留“质量优先，数量可降级”的口径。
- 残余 P3 风险：真实 provider 凭证、成本和 fallback 区分仍是验收风险。范围文档已经要求 credential-gated、mock、fallback、skipped 明确区分。

## 6. 审查发现和修复记录

| 编号 | 优先级 | 来源 | 发现 | 处理结果 |
| --- | --- | --- | --- | --- |
| SR-V4-001 | P3 | 初稿自审 | P1/P2 候选范围较多，后续 implementation plan 存在重新膨胀风险。 | 已在范围文档第 11 节要求 implementation plan 按 P0 机器产物组织阶段，并将 P1/P2 放入 P0 稳定后的 gating 阶段。 |
| SR-V4-002 | P2 | 训练数据和评测边界审查 | 训练 payload 禁止项中，对 reward scalar、reward label、verifier 原始输出、verifier trace、隐藏测试执行细节和隐藏 selector 命中细节的模型可见边界还不够硬。 | 已修复。范围文档 P0-3 验收原则补充明确要求：这些字段只能作为评测、审计、筛选、分层或外部元数据使用，不得进入模型可见训练 payload 或训练 target 文本。 |
| SR-V4-003 | P3 | 训练数据和评测边界审查 | 审查记录中的训练数据边界问题列表没有显式列入 final verifier 仍然是成功和 reward 主事实的权威来源。 | 已修复。审查记录第 5.2 节已补充该审查问题，并在审查结论中确认主文档保持 final verifier 权威性。 |
| SR-V4-004 | P3 | 范围一致性审查、工程可执行性审查 | P1/P2 候选范围数量较多，后续 implementation plan 可能重新膨胀。 | 已记录为残余风险。当前范围文档已经要求 P1/P2 只能在 P0 稳定后进入 gating 阶段，后续 implementation plan 需继续执行该约束。 |
| SR-V4-005 | P3 | 工程可执行性审查 | P0 任务扩展目标偏紧，约 10 个 accepted / auditable tasks 加 baseline verifier、flaky detection 和 source materialization repeat check 可能消耗较多验证时间。 | 已记录为残余风险。范围文档已经保留“质量优先，数量可降级”的验收口径，允许不稳定任务降级为 diagnostic-only、quarantined 或 rejected。 |
| SR-V4-006 | P3 | 工程可执行性审查 | 真实 provider 凭证、成本和 fallback 区分仍是验收风险。 | 已记录为残余风险。范围文档已经要求 credential-gated、mock、fallback、skipped 明确区分，不能把 fallback 成功伪装成 primary provider 成功。 |

## 7. 追加多维度复核

在用户要求进入 V4 implementation plan 前，又追加安排四个只读 subagent 从以下维度复核：

1. V3 基线继承和范围一致性。
2. 工程可执行性和实施计划准备度。
3. 训练数据、评测、导出和污染边界。
4. 技术报告和 Claude Code 参考吸收是否合理。

追加复核发现：

| 编号 | 优先级 | 来源 | 发现 | 处理结果 |
| --- | --- | --- | --- | --- |
| SR-V4-007 | P3 | V3 基线继承审查 | 文档把当前 export audit 的唯一非阻塞 warning 简写成 `no_trainable_preference_pair`，但机器产物中的 warning 是 `preference_pair_baseline_blocked`，`no_trainable_preference_pair` 是 blocked reason / residual risk。 | 已修复。范围文档现在区分 warning 名称和 blocked reason，避免后续 implementation plan 按错字段名设计 schema 或 inspect。 |
| SR-V4-008 | P1 | 工程可执行性审查 | P1 增强项如果被纳入 implementation plan，缺少和 P0 同等的 schema、inspect、正例、负例、是否进入最终验收和失败阻塞口径。 | 已修复。范围文档明确：任何 P1 若进入实际阶段或最终验收，必须像 P0 一样定义验收口径；否则只能保留为非验收候选。 |
| SR-V4-009 | P1 | 工程可执行性审查 | “约 10 个 accepted / auditable tasks”缺少机器可检查的最低门槛，无法判断 V3 既有任务、V4 新构造任务、diagnostic-only、quarantined 或 rejected 是否计数。 | 已修复。范围文档明确 V4 最小验收建议至少 8 个 accepted / auditable task definitions，其中至少 4 个为 V4 PR / issue 构造流程新增任务；diagnostic-only、quarantined 和 rejected 不计入 accepted / auditable 最低数量。 |
| SR-V4-010 | P2 | 工程可执行性审查 | “P0 稳定后”进入 P1/P2 过于抽象。 | 已修复。范围文档新增 P0 stability gate：V3 回归通过、P0 schema / inspect / negative tests 完成、P0 acceptance dry run 通过、selected run refs / role refs 已进入 RUN_SELECTION_MANIFEST，P0 机器产物已通过 ACCEPTANCE_INPUTS 或 acceptance bundle 绑定后，才允许开启 P1/P2 实施阶段。 |
| SR-V4-011 | P2 | 工程可执行性审查 | V4 implementation plan 需要在 rollout 批处理前拆出 task source freeze / construction preflight 阶段。 | 已修复。范围文档第 11 节新增 V4 task source freeze / construction preflight 阶段，要求先冻结 source archive、任务 manifest、baseline verifier、flaky evidence、source materialization repeat check 和 evaluator-only evidence 分区。 |
| SR-V4-012 | P2 | 工程可执行性审查 | P0-1 要求 run leasing 和 batch resume，但建议机器产物缺少显式 lease / resume 状态产物。 | 已修复。范围文档新增 `lease_state_report.json` 和 `batch_resume_report.json`。 |
| SR-V4-013 | P2 | 训练数据和污染边界审查 | 显式污染边界漏列 `Authorization marker`、provider credential marker、official harness report 和 official report。 | 已修复。范围文档在训练 payload 禁止项、V3 边界继承和 implementation plan 提示中补充这些字段。 |
| SR-V4-014 | P2 | 技术报告和 Claude Code 参考审查 | Claude Code tool lifecycle 吸收略薄，容易被 implementation plan 缩成 permission / hook 审计；permission trace 缺少决策阶段和规则来源最低 schema。 | 已修复。范围文档新增 `tool_lifecycle_trace.jsonl`，并要求记录 tool lookup、schema validation、permission decision、hook decision、execution status、artifact ref、truncation status 和 tool_result pairing status；同时补充 `permission_decision_trace.jsonl` 的最低字段。 |
| SR-V4-015 | P3 | 技术报告和 Claude Code 参考审查 | P0-2 的 baseline verifier 语义可再明确，避免把 bug-fix task 的预期 `fail_to_pass` 失败误判为 invalid。 | 已修复。范围文档明确 `fail_to_pass` 初始失败是有效任务信号，`pass_to_pass`、setup、依赖、环境健康、broad regression failure 才用于判定 unstable、quarantined 或 rejected。 |
| SR-V4-016 | P3 | 技术报告和 Claude Code 参考审查 | scaffold quality 没有贯穿到 P0 trajectory/export 元数据硬要求。 | 已修复。范围文档要求 P0 trajectory quality 和 export 样本保留 `scaffold_id`、`tool_policy_id`、`verifier_id`、`environment_id` 和任务来源标识。 |
| SR-V4-017 | P3 | 技术报告和 Claude Code 参考审查 | 可补充低风险高价值候选：prompt injection / instruction conflict diagnostic tasks。 | 已修复。范围文档新增 P2-4，限定为小规模固定 fixture、diagnostic-only，不进入 V4 最小完成硬门。 |
| SR-V4-018 | P2 | 用户追问和任务可执行性复查 | V4 implementation plan 前需要提前设计 SWE / PR 任务预选、Docker image prewarm、baseline verifier、flaky probe、patch feasibility 和 freeze readiness；否则“至少 8 个 accepted / auditable task definitions，其中至少 4 个 V4 新构造任务”会成为实施阶段最大不确定性。 | 已修复。新增 `docs/v4/swe-task-feasibility-experiment-plan.md`，并在范围文档第 11 节加入 V4 SWE / PR task feasibility and freeze preparation 阶段。 |
| SR-V4-019 | P2 | V4 SWE / PR feasibility 范围边界审查 | Level 4 patch feasibility 的通过标准可能被误读为“patch 冲突但可诊断也可以 accepted”。 | 已修复。feasibility 计划明确 accepted / auditable 必须 patch 干净应用到 fixed revision，并且 post-patch verifier 达到预期；冲突可诊断只能进入 quarantined、diagnostic-only 或 rejected。 |
| SR-V4-020 | P2 | V4 SWE / PR feasibility 范围边界审查 | accepted / auditable checklist 的 adapter-visible denylist 比前文和 scope 文档窄。 | 已修复。feasibility 计划补齐 raw test patch、FAIL_TO_PASS / PASS_TO_PASS 原始 selector、official harness report、official resolved status、Authorization marker、provider credential marker 和 provider raw response。 |
| SR-V4-021 | P2 | V4 SWE / PR 候选任务选择审查 | 轨道 B 的 auditable PR / issue task 定义和计数规则不够可执行。 | 已修复。feasibility 计划新增轨道 B auditable 定义：source provenance、issue / pull request / commit provenance、patch provenance、测试证据、adapter-visible input 和 evaluator-only evidence 边界，且只靠人工描述构造的任务不能计入 V4 PR / issue 新构造任务。 |
| SR-V4-022 | P2 | V4 SWE / PR 候选任务选择审查、工程可执行性审查 | 复杂度 tier、accepted 判定和资源边界缺少机器化阈值。 | 已修复。feasibility 计划新增 max_workers、Docker build 并发、timeout、磁盘门槛、镜像大小、重试次数、清理边界、tier_1 / tier_2 / tier_3 阈值和 flaky 判定规则。 |
| SR-V4-023 | P2 | V4 SWE / PR 候选任务选择审查、工程可执行性审查 | 候选 metadata schema 和机器审计字段不够完整。 | 已修复。feasibility 计划补充 license、source provenance、issue / pull request / commit URL、source archive sha256、source tree hash、language、network/external service、Docker fit、patch size、manifest sha256、verifier command/hash、timeout、attempt、retry_reason、exit code、log refs、adapter-visible input hash 和 evaluator-only evidence manifest hash。 |
| SR-V4-024 | P2 | V4 SWE / PR 候选任务选择审查、工程可执行性审查 | 失败分类分散且不闭合。 | 已修复。feasibility 计划新增统一 failure taxonomy，并要求每个候选最终状态写入 `final_status`、`stage`、`primary_failure_category`、`secondary_failure_category`、`evidence_ref` 和 `retryable`。 |
| SR-V4-025 | P2 | V4 SWE / PR 候选任务选择审查 | 候选池规模和最终目标之间余量偏薄，并缺少初始候选家族与硬排除规则。 | 已修复。feasibility 计划将扫描目标提高到 30 到 45 个、完整 probe 提高到 18 到 24 个，增加初始候选家族、硬排除规则和候选类别重叠说明。 |
| SR-V4-026 | P3 | V4 SWE / PR 工程可执行性审查 | “至少 2 个 tier_2_complex 任务”容易被误读为 V4 acceptance 硬门。 | 已修复。feasibility 计划将其改为 stretch / preference；若 feasibility 不足，应记录为 staged enhancement。 |
| SR-V4-027 | P2 | 用户追加 review finding | 范围文档仍可能把 `no_trainable_preference_pair` 写成 V3 export audit warning 字段，而不是 blocked reason / residual risk。 | 已复核并确认当前 `docs/v4/scope-and-roadmap.md` 已修正为：V3 warning 是 `preference_pair_baseline_blocked`，`no_trainable_preference_pair` 是 blocked reason / residual risk。 |
| SR-V4-028 | P3 | 用户追加 review finding | P0 stability gate 中的 `RUN_SELECTION_MANIFEST` / `ACCEPTANCE_INPUTS` 绑定口径可能让后续计划误把所有报告类产物塞进 run selection manifest。 | 已复核并确认当前范围文档已修正为：selected run refs / role refs 进入 `RUN_SELECTION_MANIFEST`，P0 机器产物通过 `ACCEPTANCE_INPUTS` 或 acceptance bundle 绑定。 |
| SR-V4-029 | P2 | V4 SWE 初始本机 probe | 需要在 implementation plan 前提前选择复杂度高于 V3、项目家族更多样的 SWE 候选，并在本机 Docker 中验证 gold patch feasibility。 | 已执行初始 public SWE-Bench-like probe。`runs/v4-swe-task-feasibility-20260504T044301Z/` 生成 300 条候选 inventory、18 条家族配额候选、5 条 `tier_2_complex` 初始 probe 候选；Django、Astropy、Sphinx、Matplotlib、Scikit-learn 五个 gold patch probe 全部 resolved。 |
| SR-V4-030 | P2 | 用户确认的 V4 本阶段 P1/P2 取舍 | V4 implementation plan 前需要把 P1/P2 候选进一步收敛，避免完整 provider matrix、context strategy、MCP、retrieval、subagent 或 prompt injection diagnostic task 被误写进本阶段实施范围。 | 已修复。范围文档明确：本阶段与 P0 一起纳入 P1-2 轻量 audit-only 版本和 P1-4 完整轻量卡片版本；P1-1 只保留 provider、scaffold、budget、fallback、token usage 和 provider error 元数据，不做完整矩阵报告；P1-3 和全部 P2 明确标记为本阶段不完成。 |

追加复核后的状态：

- 未发现剩余 P1 问题。
- 未发现剩余 P2 问题。
- 剩余 P3 均已修复或转化为 implementation plan 需要继续关注的风险。
- V4 public SWE-Bench-like 初始数据选择和本机 gold patch feasibility probe 已启动并完成第一批 `5 / 5` resolved；该结果提升了 V4 task freeze 的可信度，但仍不等同于 V4 最终 accepted / auditable task definitions。

## 8. 最终结论

初稿阶段三个 subagent 只读审查和追加四个维度复核都已经完成。当前结论：

- 未发现未修复的 P1 问题。
- 未发现未修复的 P2 问题。
- 训练数据和评测边界审查、工程可执行性审查、技术报告 / Claude Code 参考审查发现的 P1/P2 问题已经修复。
- 剩余风险主要集中在 P0 任务扩展工作量、真实 provider 凭证、fallback 区分、非 Python 任务平台兼容性，以及至少 4 个 V4 PR / issue 构造流程新增任务仍需在 RepoHarness 正式实现中接入和验收上；这些风险已经被转化为 P0 stability gate、P1/P2 本阶段取舍、任务数量最低门槛、V4 SWE / PR task feasibility 前置设计、资源边界、failure taxonomy、run selection / acceptance inputs 绑定边界和 implementation plan 阶段拆分要求。
- `docs/v4/scope-and-roadmap.md` 当前可以作为后续 V4 implementation plan 编写阶段的范围输入。
