# V5 Stage 2A 初始任务集接入审查

日期：2026-05-05

## 审查方式

本轮先完成主流程自审，并安排只读 subagent 对 Stage 2A 的代码、测试和机器产物进行独立复核。审查对象：

```text
runs/v5-stage2a-initial-task-set-20260505T145206Z/
```

## 审查维度

- `build-v5-task-set` 是否只使用显式输入路径，不扫描 latest run。
- 输出目录已经存在时是否默认失败。
- 当前 10 个候选是否全部进入 V5 task inventory。
- 当前 10 个候选是否保持 `stage2a_initial_10`、`initial_batch_freeze_ready` 和 `blocked_pending_stage2b` 状态。
- 是否错误宣称已经满足 `12 total / 8 PR-issue` 严格任务库存门。
- adapter-visible task input 是否没有 raw PR body、raw PR diff、gold patch、raw test patch、hidden selector、provider raw content、reward scalar 或 reward label。
- evaluator-only evidence 是否保持隔离，且没有进入 share-safe 或 model-visible 内容。
- `inspect-v5-task-set --assert-complete` 和 `inspect-v5-task-visibility --assert-clean` 是否通过。
- negative tests 是否覆盖错误库存门声明和 adapter-visible forbidden marker。

## 主流程发现

### P1

无。

### P2：初轮 subagent 发现 adapter-visible 泄漏检查覆盖不足

初轮只读 subagent 复审发现两个 P2：

- `_adapter_visible_findings` 对 forbidden marker 的覆盖不足，只匹配部分空格形式，没有覆盖 `raw_pr_diff`、`raw_pr_body`、`hidden_selector`、`gold_patch`、`raw_test_patch`、`provider_raw_content`、`reward_scalar`、`reward_label` 等常见下划线形式。
- `inspect-v5-task-visibility --assert-clean` 只检查报告汇总计数，没有重新读取 `adapter_visible_input_refs` 指向的实际模型可见文件做独立复扫。

处理：已修复。当前实现把 adapter-visible forbidden marker 统一到共享常量 `V5_FORBIDDEN_ADAPTER_VISIBLE_MARKERS`，builder 和 inspect 共用同一组标记；`inspect-v5-task-visibility` 现在会重新读取 `adapter_visible_input_refs` 指向的文件，并独立扫描 forbidden marker。新增单元测试覆盖 `raw_pr_diff`、`provider_raw_content`、`hidden_selector`、`reward_scalar` 等下划线形式，也覆盖报告计数未变化但 adapter-visible 文件被污染时 inspect 仍会失败。

### P3：adapter-visible 安全提示扫描规则需要区分提示词和泄漏内容

初次生成 `runs/v5-stage2a-initial-task-set-20260505T144733Z/` 时，scanner 把 adapter-visible 约束中的“不要查看 evaluator-only evidence”安全提示误判为泄漏，导致 `model_visible_leak_count=10`。

处理：已把 scanner 调整为拒绝真实 evaluator-only 内容标记和 raw evidence marker，而不是拒绝这种安全提示。修复后重新生成当前正式产物目录 `runs/v5-stage2a-initial-task-set-20260505T145206Z/`，`inspect-v5-task-visibility --assert-clean` 已通过。

## 已确认通过项

- `python -m compileall src/repo_harness/v5_task_set.py src/repo_harness/v5_evidence.py src/repo_harness/cli/main.py src/repo_harness/schema_versions.py` 通过。
- `python -m pytest tests/unit/test_v5_task_set.py -q` 通过，结果为 `22 passed`。
- `build-v5-task-set` 使用真实 preflight 输入通过。
- `inspect-v5-task-set --assert-complete` 对当前 Stage 2A 产物通过。
- `inspect-v5-task-visibility --assert-clean` 对当前 Stage 2A 产物通过。
- 用同一输出目录重新运行 `build-v5-task-set` 会按预期失败，不会覆盖旧 evidence。

## 时序和边界复核

- Stage 2A 没有执行真实 provider agent run。
- Stage 2A 没有调用 provider API。
- Stage 2A 没有把 preflight artifact 直接计为最终训练样本。
- Stage 2A 没有在当前包含 V5 源码变更的主工作区重跑旧 V4 doc-sync bundle immutable inspect 作为阶段门。

## 是否允许进入下一阶段

初轮 subagent 复审不允许进入 Stage 2B，因为存在 2 个 P2。两项 P2 已修复并重新生成 Stage 2A 产物。

修复后 subagent 复审结论：

- P1：无。
- P2：无。
- P3：单元测试没有穷举全部 forbidden marker 变体。

P3 处理：已补充参数化测试，覆盖 `raw pr diff`、`raw_pr_diff`、`raw pr body`、`raw_pr_body`、`hidden selector`、`hidden_selector`、`gold patch`、`gold_patch`、`raw test patch`、`raw_test_patch`、`provider raw content`、`provider_raw_content`、`reward scalar`、`reward_scalar`、`reward label` 和 `reward_label`。

最终结论：允许进入 V5 Stage 2B。
