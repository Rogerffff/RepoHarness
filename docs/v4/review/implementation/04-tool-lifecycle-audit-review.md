# V4 Stage 4 Implementation Review: Tool Lifecycle Audit

## 审查范围

本次审查覆盖阶段 4 的 P1-2 轻量 audit-only 权限判断、工具生命周期、hook 审计事实、MCP disabled / frozen 外部工具面，以及新增 inspect 命令和负例测试。

审查文件和产物包括：

- `src/repo_harness/v4_tool_lifecycle.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v4_tool_lifecycle.py`
- `docs/v4/evidence/tool-lifecycle/`
- `docs/v4/implementation-log/04-tool-lifecycle-audit.md`

## 审查方法

- 对照 `docs/v4/implementation-plan.md` 的阶段 4 要求逐项检查。
- 对照 `docs/v4/scope-and-roadmap.md` 确认未扩张到完整产品式 hook 系统、MCP 动态发现或完整 provider / scaffold / budget matrix。
- 只读检查机器产物字段、交叉引用、hash 绑定、稳定工具顺序和 schema 快照。
- 检查单元测试是否覆盖阶段 4 要求的负例。
- 检查 V2 / V3 回归 inspect 是否仍保留为阶段门槛。

## 审查发现和修复记录

### 已修复 P1：非 allow permission decision 可能进入工具执行事实

初始实现中，生命周期 trace 对 permission decision 的执行边界不够强，存在将 deny 类 permission decision 错误绑定到已执行工具调用的风险。

修复结果：

- `inspect-v4-tool-lifecycle --assert-complete` 强制实际执行的 lifecycle 记录只能引用 `allow` permission decision。
- `permission_decision_trace.jsonl` 中 `deny`、`ask`、`safety_deny`、`hook_deny` 均必须保持未执行。
- `tests/unit/test_v4_tool_lifecycle.py` 增加 deny 被执行和 lifecycle 引用 deny permission 的负例。

### 已修复 P2：tool result pairing 和 id 稳定性校验不足

初始实现只检查 pairing 状态存在，未充分检查 `tool_call_id`、`tool_result_id` 和重复 id。

修复结果：

- lifecycle inspect 强制 `tool_result_pairing_status=paired`。
- lifecycle inspect 强制 `tool_call_id` 和 `tool_result_id` 非空且唯一。
- 单元测试覆盖 unpaired result、缺失 result id 和重复 id。

### 已修复 P2：MCP snapshot 与 tool contract 缺少交叉校验

初始实现冻结了 MCP disabled facts，但没有充分证明 MCP snapshot 与 tool contract 中记录的工具顺序、schema hash 和外部工具面 hash 一致。

修复结果：

- `inspect-v4-tool-contract --assert-frozen` 读取并交叉校验 `mcp_policy_snapshot.json`。
- 强制 `mcp_enabled=false`、`dynamic_tool_discovery_allowed=false`、`dynamic_tool_surface_freeze_status=frozen`。
- 强制 stable external tool surface hash、stable tool order 和 tool schema hash 与 contract 一致。

### 已修复 P2：permission decision 覆盖和 rule 绑定不完整

初始实现未强制覆盖 `allow`、`deny`、`ask`、`safety_deny`、`hook_deny` 五类决策，也未强制 `matched_rule`、`reason` 和 `rule_source` 与冻结 policy snapshot 一致。

修复结果：

- inspect 强制五类 decision 全部存在。
- inspect 强制 `matched_rule` 必须存在于 `permission_policy_snapshot.json`。
- inspect 强制 permission trace 中的 `reason` 和 `rule_source` 与 policy snapshot 一致。
- 单元测试覆盖缺少 decision、缺少 rule、reason 漂移和 rule_source 漂移。

### 已修复 P2：最低审计字段不完整

初始实现对 permission trace 和 tool lifecycle trace 的最低字段检查不完整，可能无法支持后续阶段审计。

修复结果：

- permission trace 最低字段包含 run、turn、tool call、decision stage、rule source、matched rule、permission mode、headless / interactive、hook override、content safety check、final decision、reason、created_at、lookup、schema validation、execution、artifact、truncation 和 duration。
- lifecycle trace 最低字段包含 run、turn、tool name、lookup、schema validation、permission decision ref、hook decision ref、execution status、artifact refs、truncation、pairing、error type 和 duration。
- 单元测试覆盖最低字段缺失。

### 已修复 P3：hook audit-only 语义未完全强制

初始实现已有 hook audit facts，但对 `audit_only`、`model_visible`、`entered_prepared_messages` 和 `modified_tool_result` 的组合约束不够明确。

修复结果：

- inspect 强制所有 hook event 均为 audit-only。
- inspect 强制 hook event 不进入 prepared messages，不 model-visible，不改写 tool result。
- inspect 强制覆盖 `before_tool`、`after_tool` 和 `tool_error`。

## 正例确认

- `tool_contract_v4_snapshot.json` 绑定 permission、hook、MCP policy snapshot refs。
- `tool_contract_v4_snapshot.json` 记录 stable external tool surface hash、stable tool order、tool schema hash、tool result pairing policy、large output artifact policy 和 dynamic tool surface freeze status。
- `permission_decision_trace.jsonl` 覆盖五类 permission decision。
- `tool_lifecycle_trace.jsonl` 至少包含一个已执行、已配对、引用 allow permission decision 的工具调用。
- `hook_audit_report.json` 只记录 audit-only hook facts，不进入 model-visible prepared messages，不改写 tool result。

## 负例确认

单元测试覆盖以下失败条件：

- tool contract 缺少 permission / hook / MCP policy snapshot ref。
- MCP enabled、dynamic tool discovery enabled 或 dynamic tool surface 未冻结。
- tool order、tool schema hash 或 MCP snapshot 与 contract 漂移。
- hook 进入 prepared messages、改写 tool result 或失去 audit-only 标记。
- hook event type 覆盖不完整。
- tool result 未配对、id 缺失或 id 重复。
- deny / safety deny 被执行，或 safety deny reason 丢失。
- lifecycle tool call 引用 deny permission。
- permission decision 覆盖不足。
- `matched_rule`、`reason` 或 `rule_source` 与 policy snapshot 不一致。
- lifecycle trace 为空。
- permission trace 或 lifecycle trace 缺少最低审计字段。
- `permission_decision_ref` 或 `hook_decision_ref` 漂移。

## 范围控制

阶段 4 没有实现完整产品式 hook 系统，没有实现 before_model_call / after_model_call hook，没有实现 stop hook、session hook、file changed hook、subagent hook 或远程会话 hook。MCP 保持 disabled / frozen，没有启用动态工具发现。

## 最终结论

本阶段审查未发现剩余 P1、P2 或 P3 问题。阶段 4 实现满足 V4 文档中 P1-2 轻量 audit-only 权限、工具生命周期、hook 和 MCP 审计要求，可以进入阶段 5。
