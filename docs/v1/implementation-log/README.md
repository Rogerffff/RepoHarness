# Implementation Log

本目录用于记录 RepoHarness 第一版实现过程中的阶段日志。它不是替代 Git 历史，而是补充 Git 历史中不容易表达清楚的内容：每个阶段为什么这样实现、验证命令是什么、审查发现了什么、哪些风险已经处理、哪些限制被明确接受。

## 记录目标

每个阶段完成后，应在本目录新增一篇日志。推荐命名方式：

```text
01-stage-01-scaffold.md
02-stage-02-core-schemas.md
03-stage-03-run-recorder.md
04-stage-04-task-adapter-fixtures.md
05-stage-05-workspace-adapter.md
06-stage-06-verifier-reward-metrics.md
07-stage-07-minimal-vertical-slice.md
08-stage-08-tool-permission-system.md
09-stage-09-context-model-client.md
10-stage-10-agent-loop-scaffold.md
11-stage-11-eval-runner-cli.md
12-stage-12-training-exporter.md
13-stage-13-final-acceptance.md
```

阶段日志应帮助后来阅读者回答三个问题：

- 本阶段实际实现了什么。
- 本阶段如何证明实现是正确的。
- 本阶段和设计文档相比是否有偏离、限制或后续风险。

## 推荐流程

每个阶段建议遵循以下闭环：

1. 主实现 agent 完成当前阶段范围内的代码和文档修改。
2. 主实现 agent 运行该阶段要求的验证命令。
3. 主实现 agent 写阶段日志初稿，记录实现范围、验证结果和已知限制。
4. 只读审查 sub agent 检查实现，不直接修改文件。
5. 主实现 agent 根据审查意见修正代码、测试或文档。
6. 主实现 agent 重新运行相关验证命令。
7. 主实现 agent 更新阶段日志，记录审查结论和处理结果。
8. 主实现 agent 创建阶段 commit。

这个流程的重点是可审计，而不是制造额外形式。日志应该简洁但具体，避免只写“已完成”“测试通过”这类无法复盘的信息。

## 阶段日志模板

可以复制下面的模板作为每个阶段的起点：

```markdown
# Stage NN: Stage Name

## Scope

本阶段实现了：

- ...

本阶段明确不实现：

- ...

## Design References

- docs/v1/implementation-plan.md
- docs/11-object-model-config-and-data-flow.md
- docs/...

## Files Changed

- src/repo_harness/...
- tests/...
- docs/...

## Verification

运行的命令：

```bash
python -m pytest ...
```

结果：

- 通过 / 未通过
- 如果未通过，原因和后续处理计划是什么。

## Review

审查方式：

- 主实现 agent 自查
- sub agent 只读审查

关键审查意见：

- ...

处理结果：

- 采纳：...
- 部分采纳：...
- 暂不采纳：...

## Known Limitations

- ...

## Commit

- Commit: `<commit-hash>`
- Commit message: `...`
```

## 审查记录和 Git 历史的关系

Git commit 记录代码和文档的精确变化；implementation log 记录阶段性的工程判断。两者都需要保留。

推荐做法：

- 每个高风险阶段至少有一篇 implementation log。
- 每个阶段日志应引用对应 commit hash。
- 如果 sub agent 产生较长审查报告，可以保存到 `docs/v1/review/implementation/`，然后在本目录的阶段日志中摘要关键结论。
- 不应把运行产物、临时工作区、导出数据或大模型完整输出直接写入本目录；这些内容应通过 run directory、artifact manifest 或 Git commit 引用。

## 当前边界

本目录只记录 RepoHarness 第一版实现过程。它不用于保存：

- `runs/` 下的实际运行产物。
- 训练导出的 JSONL 数据。
- 大段 provider 原始响应。
- 与实现阶段无关的源码阅读笔记。

这些边界可以避免实现日志变成新的不可维护资料堆。
