# V4 Stage 4: Tool Lifecycle Audit

## 目标

阶段 4 的目标是在不实现完整产品式 hook 系统、不启用 MCP 动态发现的前提下，生成 audit-only 的 permission decision、tool lifecycle、hook audit、MCP disabled 和 tool contract freeze 事实。

## 实现内容

- 新增 `repo-harness build-v4-tool-lifecycle`。
- 新增阶段 4 专用 `inspect-v4-tool-contract --assert-frozen` 和 `inspect-v4-tool-lifecycle --assert-complete` 检查器。
- 冻结 `permission_policy_snapshot.json`、`hook_policy_snapshot.json`、`mcp_policy_snapshot.json` 和 `tool_contract_v4_snapshot.json`。
- 生成 `permission_decision_trace.jsonl`，覆盖 allow、deny、ask、safety deny 和 hook deny 五类 decision。
- 生成 `tool_lifecycle_trace.jsonl`，记录工具查找、schema validation、permission decision、hook decision、execution status、artifact refs、truncation、tool result pairing 和 duration facts。
- 生成 audit-only hook events，覆盖 before_tool、after_tool 和 tool_error。
- 强制 `mcp_enabled=false`、`dynamic_tool_discovery_allowed=false`、`dynamic_tool_surface_freeze_status=frozen`。

## 主要修改文件

- `src/repo_harness/v4_tool_lifecycle.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v4_tool_lifecycle.py`

## 机器产物

目录：`docs/v4/evidence/tool-lifecycle/`

- `hook_policy_snapshot.json`
- `hook_audit_report.json`
- `tool_lifecycle_trace.jsonl`
- `permission_decision_trace.jsonl`
- `permission_policy_dataset_manifest.json`
- `permission_policy_snapshot.json`
- `mcp_policy_snapshot.json`
- `tool_contract_v4_snapshot.json`

## 验证命令

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH repo-harness build-v4-tool-lifecycle --output-dir docs/v4/evidence/tool-lifecycle`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-tool-contract docs/v4/evidence/tool-lifecycle --assert-frozen`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-tool-lifecycle docs/v4/evidence/tool-lifecycle --assert-complete`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_tool_lifecycle.py tests/unit/test_v4_rollout.py -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`

## 验证结果

- Compileall 通过。
- 阶段 4 build 通过。
- `inspect-v4-tool-contract --assert-frozen` 通过。
- `inspect-v4-tool-lifecycle --assert-complete` 通过。
- 阶段 4 与阶段 3 单元测试组合通过。
- V2 acceptance inspect 通过。
- V3 acceptance inspect 通过。
- V3 acceptance bundle immutable inspect 通过。

## 正例证据

- `tool_contract_v4_snapshot.json` 绑定 permission、hook、MCP policy snapshot refs，并记录 stable external tool surface hash、stable tool order、tool schema hash、tool result pairing policy、large output artifact policy 和 dynamic tool surface freeze status。
- `permission_decision_trace.jsonl` 覆盖 allow、deny、ask、safety deny、hook deny。
- `tool_lifecycle_trace.jsonl` 在 assert-complete 下必须非空，实际 tool call 只能引用 allow permission。
- `hook_audit_report.json` 覆盖 before_tool、after_tool、tool_error，并保持 `audit_only=true`、`model_visible=false`、`modified_tool_result=false`。

## 负例证据

测试覆盖以下失败场景：

- tool contract 缺少 permission / hook / MCP policy snapshot ref。
- MCP enabled 或 dynamic discovery enabled。
- tool order、tool schema hash、MCP snapshot 与 contract 漂移。
- dynamic tool surface freeze status 不是 `frozen`。
- hook 进入 prepared messages、hook 改写 tool result、hook audit 非 audit-only。
- 缺少 before_tool / after_tool / tool_error hook event。
- tool lifecycle 缺少 paired result、tool_call_id / tool_result_id 缺失或重复。
- deny / safety deny 被执行，safety deny reason 丢失。
- lifecycle tool call 引用 deny permission。
- permission decision 覆盖不足。
- matched_rule 不在 policy snapshot，或 reason / rule_source 漂移。
- lifecycle trace 为空。
- permission trace 或 tool lifecycle trace 缺少最低审计字段。
- permission_decision_ref 或 hook_decision_ref 漂移。

## 允许降级项

- hook 系统保持 disabled / audit-only，不实现用户可配置、项目可配置、插件可配置或技能 frontmatter 可配置 hook。
- MCP 保持 disabled / frozen，不实现动态发现。

## 禁止降级项

- 不允许 hook 产物进入 model-visible prepared messages。
- 不允许 audit-only hook 改写 tool result。
- 不允许 permission deny、ask、safety deny 或 hook deny 执行为 tool call。
- 不允许 tool order、tool schema、MCP snapshot 或 dynamic tool surface freeze status 漂移。

## 已知限制

- 阶段 4 只生成 audit facts，不接入真实 agent run recorder；该集成留到阶段 5。

## 是否偏离设计文档

没有偏离。阶段 4 保持在 P1-2 轻量 audit-only 范围内，没有扩张到完整产品式 hook 系统或 MCP 动态工具发现。

## Subagent 或等价自审结论

阶段 4 经多轮只读 subagent 审查。审查先后发现 deny tool call 可绕过、paired result 校验偏弱、MCP snapshot 与 contract 未交叉校验、permission decision 覆盖不足、最低审计字段不完整、matched_rule / reason / rule_source 未强绑定、hook lifecycle 样例不足、permission_decision_ref / hook_decision_ref 未解析、dynamic tool surface freeze status 未强制为 frozen、hook audit_only 未强制等问题。上述 P1/P2/P3 均已修复。最终复审结论：未发现 P1/P2/P3，允许进入阶段 5。

## 是否可以进入下一阶段

可以进入阶段 5。
