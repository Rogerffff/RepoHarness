# RepoHarness 接入 verl 的顺序开发总览

本文档目录用于规划 RepoHarness 接入 verl 的分阶段实现路线。当前结论是：暂时不拆成两个并行 worktree 开发，而是按照明确依赖顺序推进，先让 RepoHarness 自身形成稳定的 episode runtime 和 training fast 能力，再接入 verl adapter。

这个目录不是当前实现状态说明，而是后续开发阶段的设计边界和验收入口。

## 1. 为什么从并行 worktree 改为顺序开发

RepoHarness 接入 verl 会同时触碰下面几类关键边界：

```text
episode request
runtime run_episode(...)
LLMGateway
training view
audit reference
timing/resource summary
workspace/container lifecycle
verifier/reward
AgentLoopOutput
visibility policy
```

如果在 agent 之间没有实时沟通的情况下拆成两个并行 worktree，一个 agent 很容易先实现 verl adapter，另一个 agent 同时改 Harness training fast，最后出现接口语义不一致：

- adapter 假设 `RepoHarnessEpisodeResult.training_view` 已经稳定，但 Harness 侧还没有抽出 runtime facade。
- Harness 侧为了加速减少 artifact 写入，导致 adapter 拿不到稳定 `audit_ref`。
- adapter 为了赶通 smoke test 绕过 `RepoHarnessEpisodeResult`，直接拼 `AgentLoopOutput`。
- 两边各自定义 `status`、`invalid_for_training`、`timing_summary_ref` 或 `extra_fields`，阶段衔接时需要重构。

因此第一版改为顺序路线：

```text
先固定 contract
  -> 再改造 RepoHarness runtime
  -> 再实现 training_fast 能力
  -> 再抽象 LLMGateway
  -> 再接 verl AgentLoop adapter
  -> 最后做端到端训练 smoke test
```

## 2. 当前目录结构

```text
docs/agentic_RL/repo_harness_verl_workstreams/
  00-overview.md
  01-sequential-implementation-plan.md
  02-sequential-implementation-plan-review.md
  03-stage-0h-execution-brief.md

  shared_contracts/
    01-episode-contract.md
    02-llm-gateway-contract.md
    03-training-view-and-audit-ref-contract.md
    04-timing-and-resource-contract.md
    05-acceptance-contract.md
    06-contract-hardening-v1.md
```

`shared_contracts/` 保留作为所有阶段共同遵守的接口契约。`06-contract-hardening-v1.md` 是审查后新增的前置硬门槛，集中约束 token、mask、log probability、visibility、cancellation、training_fast 和验收分层。`01-sequential-implementation-plan.md` 是实际开发路线入口，`03-stage-0h-execution-brief.md` 是进入 Stage 1 代码实现前必须执行的短执行单。后续 agent 应优先阅读这些文件，而不是自行恢复并行 worktree 模式。

## 3. 当前 contract 版本

当前第一版 contract 使用下面的文档版本号：

```text
repo_harness_verl_shared_contracts_v0
```

这个版本号表示：

- 字段命名仍是实施前设计，不代表代码已经存在。
- contract 只冻结第一版最小语义边界，不冻结所有未来扩展字段。
- 如果后续实现发现字段必须改名、拆分或移动，需要先更新 `shared_contracts/` 和顺序实施计划，再修改代码。

## 4. 阶段推进原则

每个阶段必须满足下面的原则：

1. 后一阶段不能绕过前一阶段尚未稳定的 contract。
2. `RepoHarnessVerlAgentLoop` 不能直接调用 CLI 级 `run_task(...)` 作为长期方案。
3. `training_fast` 不能为了加速删除结构化 `AuditRef`、进入 batch 的 opaque refs、reward metadata 引用、关键 hash、timing summary 或 resource summary。
4. 任何进入 verl dataset non-tensor fields、`AgentLoopOutput.extra_fields` 或训练 batch 的字段，都必须通过 visibility 规则。
5. 第一版 reward 必须在 `RepoHarnessVerlAgentLoop.run(...)` 返回前可用；真正的异步 reward backfill 放到 fully async 阶段再设计。
6. `LLMGateway` 是 RepoHarness 面向模型调用的统一抽象，verl 只是其中一个 backend，RepoHarness core 不能被 verl 依赖绑定死。
