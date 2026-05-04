# V4 Stage 3: Rollout Orchestration

## 目标

阶段 3 的目标是在单机优先、`max_workers=1` 的边界内实现 rollout queue、lease、retry、resource lock、budget control、resource usage、batch resume、checkpoint state 和 run selection query 的机器产物与检查命令。阶段 3 不实现分布式调度、集群调度、长期 session continuation 或用户记忆。

## 实现内容

- 新增 `repo-harness build-v4-rollout-orchestration`，从阶段 2 `task_freeze_manifest.json` 显式构建阶段 3 产物。
- 新增阶段 3 专用检查器，覆盖：
  - `inspect-rollout-queue`
  - `inspect-rollout-leases`
  - `inspect-rollout-retry`
  - `inspect-rollout-budget`
  - `inspect-resource-locks`
  - `inspect-resource-usage`
  - `inspect-rollout-resume`
  - `inspect-run-selection-query`
- 强制 `max_workers=1`、`distributed_or_cluster_mode=false`。
- 强制 worker log 只有一个 `worker_id`，每条记录必须有 `worker_id`，状态写入必须携带与 queue item 匹配的 lease。
- 强制 retry 不超过 policy max attempts，fallback provider 成功不能伪装成 primary accepted。
- 强制 budget 超限时停止继续执行并写入 worker log。
- 强制 checkpoint 记录包含阶段要求字段，并复核 `phase_sha256` 与 `checkpoint_payload_sha256`。
- 强制 batch resume 只用于 rollout orchestration phase recovery，不允许长期 session continuation，不允许继承 hidden verifier、reward、outcome、failure diagnostics、evaluator-only 或 session marker。
- 强制 run selection query 包含 queue-native predicate，并与同目录 queue item ids 交叉校验。

## 主要修改文件

- `src/repo_harness/v4_rollout.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v4_rollout.py`

## 机器产物

目录：`docs/v4/evidence/rollout-orchestration/`

- `rollout_queue_manifest.json`
- `worker_run_log.jsonl`
- `lease_state_report.json`
- `batch_resume_report.json`
- `checkpoint_state_report.json`
- `retry_policy_report.json`
- `resource_lock_report.json`
- `budget_control_report.json`
- `resource_usage_report.json`
- `run_selection_query_report.json`

## 验证命令

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH repo-harness build-v4-rollout-orchestration --task-freeze docs/v4/evidence/task-source-freeze/task_freeze_manifest.json --output-dir docs/v4/evidence/rollout-orchestration`
- `PATH=.venv/bin:$PATH repo-harness inspect-rollout-queue docs/v4/evidence/rollout-orchestration --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-rollout-leases docs/v4/evidence/rollout-orchestration --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-rollout-retry docs/v4/evidence/rollout-orchestration --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-rollout-budget docs/v4/evidence/rollout-orchestration --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-resource-locks docs/v4/evidence/rollout-orchestration --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-resource-usage docs/v4/evidence/rollout-orchestration --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-rollout-resume docs/v4/evidence/rollout-orchestration --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-run-selection-query docs/v4/evidence/rollout-orchestration/run_selection_query_report.json --assert-complete`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_rollout.py tests/unit/test_v4_task_freeze.py -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`

## 验证结果

- Compileall 通过。
- 阶段 3 build 通过。
- 阶段 3 的 8 个 inspect 命令全部通过。
- 阶段 3 与阶段 2 单元测试组合通过：29 passed。
- V2 acceptance inspect 通过。
- V3 acceptance inspect 通过。
- V3 acceptance bundle immutable inspect 通过。

## 正例证据

- `rollout_queue_manifest.json` 记录 `max_workers=1` 和 `distributed_or_cluster_mode=false`。
- `worker_run_log.jsonl` 中所有 state write 均有匹配 queue item 的 lease。
- `checkpoint_state_report.json` 包含阶段要求的 checkpoint 字段，hash 可复核。
- `batch_resume_report.json` 限定为 `rollout_orchestration_phase_recovery_only`，并只继承 queue state、workspace state ref、public task context 和 non-leaking run facts。
- `run_selection_query_report.json` 与同目录 queue item ids 一致。

## 负例证据

测试覆盖以下失败场景：

- 无 lease 写入 run state。
- 多 worker 或缺少 worker id。
- state write lease 与 queue item 不匹配。
- expired lease 未进入 reclaim 或 active lease 被第二 worker 抢占。
- retry 超过 max attempts 仍继续执行。
- fallback provider 成功被标记为 primary。
- 全局或逐项 budget 超限却未停止或未写 worker log。
- resource lock 缺失。
- checkpoint hash 被篡改。
- resumed context 继承 reward、hidden verifier、裸 session marker 等禁止内容。
- run selection query 缺少 predicate / input hash，predicate 错误，selected ids 与 queue 不一致，或缺少 sibling queue manifest。

## 允许降级项

- 阶段 3 只生成单机 rollout orchestration 产物，不启动真实 agent run。
- resource usage 是阶段 3 orchestration 级记录，不作为最终 agent run performance benchmark。

## 禁止降级项

- 不允许实现 Kubernetes、云端多租户调度、集群调度或分布式强化学习 rollout。
- 不允许 batch resume 变成长期 session continuation 或默认用户记忆。
- 不允许 resumed agent context 继承 hidden verifier result、reward、run outcome、failure diagnostics 或 evaluator-only evidence。

## 已知限制

- 阶段 3 只为后续 agent run integration 提供 queue / checkpoint / resume 结构，不执行实际模型调用。

## 是否偏离设计文档

没有偏离。阶段 3 保持在 P0-1 单机 rollout orchestration 范围内。

## Subagent 或等价自审结论

阶段 3 经过多轮只读 subagent 审查。审查先后发现 resume 递归污染检查过浅、worker log 单 worker 约束不强、run selection query predicate 不完整、batch resume scope 不强、budget 逐项超限检查不完整、裸 `session` marker 未拒绝等问题。上述 P1/P2/P3 均已修复。最终复审结论：未发现新的 P1、P2 或 P3，允许进入阶段 4。

## 是否可以进入下一阶段

可以进入阶段 4。
