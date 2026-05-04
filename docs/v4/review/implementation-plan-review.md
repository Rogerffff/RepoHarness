# RepoHarness V4 Implementation Plan Review

## 1. 审查目标

本文记录 `docs/v4/implementation-plan.md` 的多角度只读审查、发现和修复结果。审查目标是确认 V4 implementation plan：

- 完整覆盖 `docs/v4/scope-and-roadmap.md` 中已经收敛的 P0、P1-2、P1-4 范围。
- 没有把 P1-1 完整 provider / scaffold / budget matrix、P1-3 或任何 P2 候选误写成本阶段实施内容。
- 每个阶段都有机器产物、inspect 方向、正例和负例。
- 继续保护 evaluator-only evidence、final verifier 权威性、PreparedMessages 与 export observation 绑定、训练导出污染边界。
- 正确把 V4 PR / issue feasibility 和 public SWE-Bench-like feasibility 结果作为 implementation input，而不是直接计入 final accepted / auditable task definitions。

本次审查只读，不实现 V4 代码，不修改 V3 运行逻辑，不修改 V3 acceptance 产物。

## 2. 审查安排

实施计划草稿完成后，安排四个只读 subagent 审查：

1. 范围一致性审查：检查 P0、P1-2、P1-4 覆盖，以及 P1-1、P1-3、P2 阶段边界。
2. 工程可执行性审查：检查阶段顺序、机器产物、inspect、负例和 final acceptance 链路。
3. 训练数据、评测和污染边界审查：检查 evaluator-only evidence、gold patch、hidden selector、provider raw response、reward / verifier raw facts、AI marker 风险。
4. 任务数据接入和 acceptance 覆盖审查：检查 PR / issue freeze-ready 候选、public SWE-Bench-like 候选、accepted counting gate 和 final acceptance roles。

## 3. 审查结论摘要

- 未发现 P1 阻塞问题。
- 发现多个 P2 问题，均已修复。
- 发现若干 P3 建议，已修复或转化为 implementation log 要求。
- 当前 implementation plan 可以作为 V4 实施阶段输入，但实际实施时仍必须逐阶段写 implementation log，并在每阶段完成后继续安排只读审查。

## 4. 发现和修复记录

| 编号 | 优先级 | 来源 | 发现 | 处理结果 |
| --- | --- | --- | --- | --- |
| IP-V4-001 | P2 | 范围一致性审查 | P0-1 budget control 没有像 queue、lease、retry、resume 一样被明确写成 schema、inspect 和 negative test 要求。 | 已修复。Stage 3 新增 budget control 工作项、`budget_control_report.json`、`inspect-rollout-budget`、budget_exhausted 正例和超限仍继续执行的负例；final hard gate 和完成定义也加入 budget control。 |
| IP-V4-002 | P2 | 范围一致性审查 | P0-3 的 minimal / excessive patch 判断和 test-overfitting risk audit 没有显式展开。 | 已修复。Stage 6 新增 minimal patch / excessive patch diagnostic、`test_overfitting_risk_audit_report.json`，并要求检测只改测试、verifier bypass、删除失败路径、hidden selector hardcoding、evaluator-only leakage、删除断言和修改 verifier 配置。 |
| IP-V4-003 | P3 | 范围一致性审查 | P1-1 元数据小节混入 task source 和 visibility 字段，容易让人误解为 P1-1 范围扩大。 | 已修复。Stage 5 将 provider / scaffold / budget 元数据与 P0 task provenance / visibility 元数据分组。 |
| IP-V4-004 | P2 | 工程可执行性审查 | Stage 3 run selection query 依赖 final verifier status 和 sample tier，但这些字段分别在 Stage 5 和 Stage 6 之后才产生。 | 已修复。Stage 3 只验收 queue-native predicates；final verifier status 查询放到 Stage 5，sample tier 查询放到 Stage 6 或 final acceptance。 |
| IP-V4-005 | P2 | 工程可执行性审查 | Stage 5 缺少单独可 inspect 的机器产物。 | 已修复。Stage 5 新增 `v4_agent_run_integration_report.json`、`runspec_metadata_report.json`、`final_verifier_boundary_report.json`、`prepared_messages_binding_report.json`、`interrupted_run_recovery_report.json` 和 `inspect-v4-agent-run-integration`。 |
| IP-V4-006 | P2 | 工程可执行性审查 | Final acceptance 建议命令只有 inspect，没有 build run selection、build acceptance inputs、build acceptance report、build acceptance bundle 等生成链路。 | 已修复。Stage 8 补充 `build-v4-run-selection-manifest`、`build-v4-acceptance-inputs`、逐项 inspect、`build-v4-acceptance-report`、`build-v4-acceptance-bundle`，并要求 `inspect-v4-acceptance` 递归复核绑定产物。 |
| IP-V4-007 | P2 | 工程可执行性审查 | Stage 0 implementation input freeze gate 没有独立 inspect 命令。 | 已修复。Stage 0 新增 `inspect-v4-implementation-inputs`，并明确它与 final acceptance 的 `inspect-v4-inputs` 不是同一个阶段输入。 |
| IP-V4-008 | P3 | 工程可执行性审查 | 建议模块布局可能鼓励过度拆分。 | 已修复。代码落点说明补充：implementation log 应以机器产物和 inspect 契约为主，不以新增目录数量作为完成信号；复用现有模块是合格路径。 |
| IP-V4-009 | P2 | 训练数据和污染边界审查 | adapter-visible 和 export negative tests 没有覆盖完整全局 denylist。 | 已修复。Stage 2 negative tests 补充 official harness report、official report、official resolved status、verifier raw output、verifier trace、Docker verifier logs、flaky verifier logs、reward scalar、reward label、hidden selector 命中细节进入 adapter-visible input 或 trainable payload 时失败。 |
| IP-V4-010 | P2 | 训练数据和污染边界审查 | public SWE-Bench-like selection summary 需要明确 audit-only 绑定，因为其中可能包含 patch hash、test patch hash、fail-to-pass / pass-to-pass count 或 selector-derived metadata。 | 已修复。前置输入章节明确当前 public SWE-Bench-like selection summary 和相关 manifest 只能作为 audit-only implementation metadata，必须重新派生 sanitized model-visible task input。 |
| IP-V4-011 | P3 | 训练数据和污染边界审查 | cards、provenance summary 和 implementation log 也需要负例，防止 raw PR body、raw commit message、AI session URL 或详细 AI marker 文本被写入人工可读审计材料后被误采集。 | 已修复。Stage 7 negative tests 明确这些内容不得进入 cards、provenance summary、repro command index 或 implementation log；只允许脱敏摘要、hash、size、purpose 和 boundary status。 |
| IP-V4-012 | P2 | 任务数据接入和 acceptance 覆盖审查 | Final acceptance roles 缺少明确的 `v4_agent_run_integration` 或等价角色。 | 已修复。Stage 8 acceptance roles 新增 `v4_agent_run_integration`，final hard gate 和完成定义也加入 agent run integration inspect。 |
| IP-V4-013 | P3 | 任务数据接入和 acceptance 覆盖审查 | Final hard gate 对 post-patch verifier 表述不够显式。 | 已修复。Final hard gate 和最终完成定义都显式加入 post-patch verifier inspect。 |
| IP-V4-014 | P3 | 任务数据接入和 acceptance 覆盖审查 | 原始 Docker feasibility probe manifest 存在内部计数不一致风险，计划应要求 input inspect 拒绝这类不一致。 | 已修复。Stage 0 要求 feasibility input manifest 的 `candidate_count`、明细行数量和 passed / failed / freeze_ready 汇总一致；若历史 probe artifact 不一致，只能作为 audit-only historical artifact，并由上层 summary manifest 绑定。 |
| IP-V4-015 | P2 | 外部实施文档复核 | Stage 1 缺少“机器产物到 inspect 命令”的横向追踪表。 | 已修复。Stage 1 新增机器产物到 inspect 命令追踪表，覆盖 Stage 0、P0-1、P0-2、P0-3、P1-2、P1-4、全局污染扫描和 final acceptance。 |
| IP-V4-016 | P2 | 外部实施文档复核 | Stage 8 final acceptance 命令矩阵仍偏简略，`build-v4-acceptance-inputs` 不能只靠 `--run-selection`。 | 已修复。Stage 8 增加 V2 acceptance inspect、fresh directory / fail-if-output-exists 规则，并把 V2/V3 回归证据、implementation inputs、P0/P1 机器产物、export evidence、cards、command log 和 pre-acceptance docs 作为 `build-v4-acceptance-inputs` 显式输入。 |
| IP-V4-017 | P2 | 外部实施文档复核 | Stage 2 缺少 environment stability、dependency cache、license、provenance 和 use-boundary review 的机器化 evidence。 | 已修复。Stage 2 新增 `environment_stability_report.json`、`dependency_cache_report.json`、`license_provenance_review_report.json`、`use_boundary_review_report.json`，并把这些字段纳入 accepted / auditable task gate。 |
| IP-V4-018 | P2 | 外部实施文档复核 | Stage 2 需要写清模块所有权边界，避免 Task Adapter 被实现成执行器。 | 已修复。Stage 2 明确 Task Adapter 只产出规范化 task definition 和 evidence refs；source materialization、dependency setup、baseline verifier、post-patch verifier 分别由 Workspace Adapter、Eval Runner 和 Verifier 负责。 |
| IP-V4-019 | P2 | 外部实施文档复核 | Stage 3 batch resume 需要更硬的 checkpoint schema 和负例，并避免被误实现成 P1-3 session continuation。 | 已修复。Stage 3 新增 checkpoint state schema 字段、`checkpoint_state_report.json`、tamper / lock / hidden verifier inheritance 负例，并明确 batch resume 不实现跨实验 session continuation 或长期用户记忆。 |
| IP-V4-020 | P2 | 外部实施文档复核 | Stage 5 / Stage 6 需要更细的 trajectory store 和 PreparedMessages 字段级 inspect。 | 已修复。Stage 5 新增 `trajectory_store_integrity_report.json` 和 `inspect-v4-trajectory-store`，要求检查 ArtifactRef、sha256、redaction status、retention policy、stable record_id / event_id、RunRecorder 幂等、半写 artifact、finalize 重入、PreparedMessages tool schema hash、content replacement state hash 和 observation source event ref。 |
| IP-V4-021 | P2 | 外部实施文档复核 | Stage 6 需要把 sample tier、failure dataset、RewardMetadata 和导出格式 schema 写得更确定。 | 已修复。Stage 6 明确 outcome tier 与 trainability status 分离、failure dataset 绑定 task / turn / tool / workspace / verifier、RewardMetadata 必填字段，以及 SFT / rollout / preference export valid 和 negative fixtures。 |
| IP-V4-022 | P2 | 外部实施文档复核 | Stage 4 audit-only hook 与 hook deny 语义需要补齐 permission / MCP / tool order / dynamic tool surface 检查。 | 已修复。Stage 4 新增 PermissionPolicySnapshot、MCP disabled / frozen facts、stable tool order、tool schema hash、dynamic tool discovery 禁止和 tool contract snapshot 检查。 |
| IP-V4-023 | P2 | 外部实施文档复核 | 污染扫描应统一引用全局 denylist，而不是阶段局部清单。 | 已修复。新增 V4 全局污染 denylist 和统一扫描面，覆盖 adapter-visible input、prepared messages、transcript、events、artifacts manifest、export records、cards、implementation log 和 acceptance bundle。 |
| IP-V4-024 | P2 | 外部复核 code comment | 全局 denylist 把 export records 纳入扫描面，同时把 reward scalar / reward label 放入 denylist，可能误拒合法 reinforcement learning rollout structured reward 字段或 RewardMetadata。 | 已修复。全局 denylist 现在明确 reward scalar / reward label 禁止进入模型可见文本、prompt、action、observation、assistant target、SFT target 和 preference target；但允许出现在非模型可见、allowlisted path、带 visibility 标记的 RL structured reward 字段、RewardMetadata、reward audit report 或 audit-only metadata 中。 |
| IP-V4-025 | P2 | 外部复核 code comment | Final hard gate 和阶段退出门漏列已经新增的 resource lock 和 checkpoint state。 | 已修复。Stage 8 final hard gate 和阶段退出门表都补齐 resource lock 与 checkpoint state。 |

## 5. 复核后的范围状态

当前 `docs/v4/implementation-plan.md` 的范围状态为：

- P0-1：rollout queue、lease、retry、budget control、resource lock、resource usage、batch resume、checkpoint state、run selection query 均有产物、inspect 方向和 final hard gate 覆盖。
- P0-2：task source freeze、PR / issue task adapter、public SWE-Bench-like 扩展、source materialization、baseline verifier、post-patch verifier、flaky detection、environment stability、dependency cache、license / provenance / use-boundary review、task validity 均有产物和负例。
- P0-3：sample tiers、failure dataset、trajectory packing、preference pair trainability、blocked pair report、patch quality、minimal / excessive patch、test-overfitting risk audit、RewardMetadata、SFT / rollout / preference export schema、reward audit、reward hacking risk audit 均有产物和验收口径。
- P1-2：permission trace、tool lifecycle trace、hook audit-only facts、permission / hook / MCP disabled policy snapshots、tool contract snapshot 纳入本阶段，并明确不做完整产品式 hook 系统或 MCP。
- P1-4：dataset card、run card、export card、provenance summary、contamination scan summary、repro command index 纳入本阶段，并有负例防止夸大或泄漏。
- P1-1：只保留 provider / scaffold / budget 元数据，不做完整矩阵报告。
- P1-3 和全部 P2：明确本阶段不完成。

## 6. 最终审查结论

四个只读审查方向均未发现未修复的 P1 阻塞问题。发现的 P2 问题已经修复，P3 建议已经修复或转化为 implementation log 约束。

当前 implementation plan 可以进入 V4 实施阶段。实施时应继续遵守：

- 不修改 V3 acceptance 产物。
- 不让 feasibility 候选直接计入 final accepted / auditable。
- 不把 evaluator-only evidence、gold patch、hidden selector、official report、provider raw response、reward / verifier raw facts 放进模型可见上下文或训练 payload。
- 不把 P1-1、P1-3 或 P2 候选扩张进本阶段实施范围。
- 每个阶段完成后继续安排只读审查，并把发现写入 `docs/v4/implementation-log/` 或后续 review 文档。
