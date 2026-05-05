# V5 Stage 0 preimplementation review

日期：2026-05-05

## 审查方式

本轮先完成主流程自审，并安排只读 subagent 对 Stage 0 evidence 进行独立复核。审查对象是：

```text
runs/v5-stage0-preimplementation-20260505T143530Z/
```

主流程自审不修改 evidence，只读取 `v5_preflight_input_binding.json`、`v5_baseline_check_report.json`、`v5_preimplementation_command_log.jsonl` 和关键 stdout / stderr 产物。

## 审查维度

- V5 baseline commit `9fd7007` 是否仍是当前 `HEAD` 祖先。
- V4 closure commit `e0da89c` 是否仍是当前 `HEAD` 祖先。
- `docs/v5` 是否在 Stage 0 baseline gate 中保持干净。
- V2 / V3 regression inspect 是否通过。
- V3 acceptance bundle immutable inspect 是否通过。
- V4 inputs、V4 acceptance report 和 V4 doc-sync acceptance bundle 是否在独立还原快照中通过。
- Stage 0 command log 是否包含用户要求的 baseline 命令、cwd、argv、stdout / stderr sha256、exit code 和输出引用。
- V5 preflight 输入是否明确标记为不能计入 final accepted task、真实 provider run 或训练样本。
- 是否存在阻止进入 Stage 1 的 P1 或 P2 问题。

## 发现

### P1

无。

### P2

无。

### P3：Stage 2B 仍有任务库存缺口

当前 Stage 0 输入冻结的是既有 10 个 preflight candidates：其中 PR / issue candidates 为 6 个，SWE-Bench-like anchors 为 4 个。它满足 Stage 0 输入绑定，但不满足 V5 core acceptance 的严格任务库存门：

```text
至少 12 个 accepted / auditable task definitions
至少 8 个 PR / issue flow tasks
至少 3 个 SWE-Bench-like anchor tasks
```

处理：这是 V5 implementation plan 已知的 Stage 2B 工作项，不阻止进入 Stage 1。后续必须补齐 2 个 PR / issue candidates，或者通过正式范围变更修改 scope、preflight plan 和 review 记录。

### P3：Stage 0 policy 显式 inspect 门需要 hardening

Subagent 审查发现，`inspect-v5-preimplementation` 已经显式检查 `accepted_counting_allowed=false`、`real_agent_run_executed=false` 和 `provider_api_called=false`，但对 `stage0_policy.preflight_artifacts_do_not_count_as_final_v5_accepted_tasks=true`、`stage0_policy.preflight_artifacts_do_not_count_as_real_provider_runs=true` 和 `stage0_policy.preflight_artifacts_do_not_count_as_training_samples=true` 主要依赖 evidence 字段本身。

处理：已修复。`inspect-v5-preimplementation` 现在会显式检查上述三个字段必须为 `true`，并新增测试覆盖 preflight artifact 被错误声明为 training sample 的漂移场景。

## 已确认通过项

- `git merge-base --is-ancestor 9fd7007 HEAD` 通过。
- `git merge-base --is-ancestor e0da89c HEAD` 通过。
- `git status --short -- docs/v5` 无输出。
- `git diff --name-status -- docs/v5` 无输出。
- `python -m compileall src` 通过。
- `python -m pytest -q` 通过，结果为 `712 passed in 816.41s (0:13:36)`。
- `inspect-v2-acceptance --assert-complete` 通过。
- `inspect-v3-acceptance --assert-complete` 通过。
- `inspect-acceptance-bundle` 对 V3 bundle 的 `--assert-immutable` 通过。
- `inspect-v4-inputs --assert-complete` 在独立还原快照中通过。
- `inspect-v4-acceptance --assert-complete` 在独立还原快照中通过。
- `inspect-acceptance-bundle` 对 V4 doc-sync bundle 的 `--assert-immutable` 在独立还原快照中通过。
- Docker `hello-world`、arm64 Alpine、`linux/amd64` Alpine 和内存探针通过。
- `inspect-v5-preimplementation --assert-complete` 通过。

## 修复记录

修复了 V5 Stage 0 builder 在外部 baseline worktree 中运行命令时可能误用主工作区 editable source 的问题。现在当 `--baseline-command-cwd` 指向独立快照时，命令执行环境会把该快照的 `src` 放在 `PYTHONPATH` 最前面。

修复了 subagent 提出的 Stage 0 policy inspect hardening 建议。`inspect-v5-preimplementation` 现在会明确拒绝把 Stage 0 preflight artifacts 计入 final accepted tasks、real provider runs 或 training samples 的 evidence 漂移。

增加 `.gitattributes` 规则，使 `runs/**/command_outputs/*.txt` 作为原始命令输出证据保持字节精确提交。这样不需要修改 Docker stdout 中已经被 command log sha256 绑定的空白字节，也可以让 `git diff --cached --check` 通过。

本轮没有删除、回滚或提交任何与 Stage 0 无关的既有改动。

## 时序边界复核

旧 V4 doc-sync acceptance bundle 没有在 V5 源码变更后的主工作区作为后续阶段门使用。它只在以下独立还原快照中作为 Stage 0 baseline proof 运行：

```text
/tmp/repo-harness-v5-stage0-baseline-20260505T142500Z
```

该通过结果已经由以下文件绑定：

```text
runs/v5-stage0-preimplementation-20260505T143530Z/v5_baseline_check_report.json
runs/v5-stage0-preimplementation-20260505T143530Z/v5_preflight_input_binding.json
runs/v5-stage0-preimplementation-20260505T143530Z/v5_preimplementation_command_log.jsonl
```

## 是否允许进入下一阶段

允许进入 V5 Stage 1。当前没有阻止进入 Stage 1 的 P1 或 P2 问题。P3 任务库存缺口必须在 Stage 2B 解决，不能在 final acceptance 中降级或忽略。
