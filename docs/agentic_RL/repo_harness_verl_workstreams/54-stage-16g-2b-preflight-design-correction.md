# Stage 16G.2B Preflight Design Correction

## 背景

Stage 16G.2A 最初把 `write_file`、`apply_patch`、`delete_file`、`move_file`、`mkdir` 全部作为默认可见结构化文件工具暴露。复核后认为：结构化优先的方向仍然正确，但主训练默认工具面如果同时暴露多个高度相近的文件组织工具，会增加模型在强化学习阶段的工具选择负担，也更容易让模型过拟合 RepoHarness 的私有工具 schema。

因此 Stage 16G.2B 行为实现前，先收敛默认工具面。

## 修正后的默认工具面

`apply_patch` 是主训练默认的批量文件操作入口。多文件修改、单文件删除、单文件移动和目录创建都优先通过 `apply_patch.operations` 表达。

`write_file` 是主训练默认的整文件新建和覆盖写入入口。`create_file` 继续保持只新建语义，`write_file(mode="overwrite")` 继续要求显式 `expected_content_hash`。

`delete_file`、`move_file`、`mkdir` 保留为独立 ToolDefinition 和后续内部 executor 能力，但不进入 `swe_public_core` 默认 scaffold。它们可以在 `swe_public_extended` 或后续实验 profile 中显式暴露。

Stage 16G.5 parity probe 再决定是否把独立 `delete_file`、`move_file`、`mkdir` 提升为默认可见工具。判断依据应包括：模型是否能用 `apply_patch` 干净表达单个删除或移动、工具调用错误率、权限拒绝恢复率、任务解决率和跨 harness 迁移表现。

## Stage 16G.2B 必须验证

Stage 16G.2B 实现时必须证明 `apply_patch` 可以干净表达一元删除和一元移动：

```json
{"operations": [{"op": "delete_file", "path": "src/old.py", "expected_content_hash": "...", "reason": "..."}]}
```

```json
{"operations": [{"op": "move_file", "source_path": "src/old.py", "target_path": "src/new.py", "expected_source_hash": "...", "reason": "..."}]}
```

如果这个路径在真实文件系统 probe 中显得笨重、脆弱或高失败率，Stage 16G.5 可以重新建议独立暴露 `delete_file` 或 `move_file`。

删除和移动 operation 必须包含模型提供的 `reason` 字段。这个字段不是 harness 拒绝时的 `reason_code`，而是模型说明“为什么删除或移动是正确改动”的审计事实，用于后续 reward attribution、LLM judge 评估和 reward hacking 诊断。

`apply_patch.operations[*]` 的 `path`、`source_path`、`target_path` 必须进入权限和路径边界检查。真实行为启用前，不能只检查顶层 `apply_patch.operations` 数组。

## 多 Harness 适配方向

RepoHarness 主训练可以使用更结构化、更可审计的工具面，但训练目标不能只适配这一种 schema。后续 Stage 16G.5+ 和 Stage 17+ 应保留多 harness 适配路线，包括：

1. RepoHarness structured profile。
2. Claude Code-like Bash / Write / Edit profile。
3. mini-SWE-agent-like shell profile。
4. patch-only profile。
5. profile mixing、tool dropout、schema randomization 和 cross-harness SFT / OPD。

目标是让模型学习“语义动作到当前工具 schema 的映射”，而不是死记某一个私有工具名。
