# V5 Stage 0 baseline blocker review

日期：2026-05-05

## 审查方式

本轮没有启动 subagent。原因是 Stage 0 的硬性基线门禁已经在主流程中失败，继续进入实现审查没有意义。这里记录等价的只读自审结论，审查范围仅限已经执行的预检命令、工作区状态和是否允许进入 V5 Stage 1。

## 审查维度

- V5 baseline commit 是否正确。
- V4 closure commit 是否仍是当前分支祖先。
- `docs/v5` 是否缺失、删除、未跟踪或被意外修改。
- V2 / V3 / V4 回归 inspect 是否通过。
- 当前工作区是否是可信的 V5 implementation baseline。
- 是否存在可以安全降级的阻塞项。

## 发现

### P1：V4 doc-sync acceptance bundle immutable inspect 因源码哈希漂移失败

当前工作区中 `src/repo_harness/evaluation/runner.py` 已被修改，导致 V4 acceptance inputs、V4 acceptance report 和 V4 doc-sync acceptance bundle 的传递性复查失败。失败字段集中在 `src` 和 `src/repo_harness` 的 sha256。

影响：当前工作区不是可信 V5 baseline。继续实现 V5 会把新变更叠加到一个无法证明 V4 closure baseline 仍成立的工作区上，违反 V5 Stage 0 不变量。

处理：停止进入 V5 Stage 1，只提交阻塞报告，不修改实现代码。

## 已确认通过项

- 当前 `HEAD` 是 `9fd7007 docs: add V5 implementation baseline`。
- `git merge-base --is-ancestor 9fd7007 HEAD` 通过。
- `git merge-base --is-ancestor e0da89c HEAD` 通过。
- `docs/v5` 在预检时无 diff、无删除、无未跟踪文件。
- `compileall` 通过。
- 全量测试通过，`712 passed in 601.01s`。
- V2 acceptance inspect 通过。
- V3 acceptance inspect 通过。
- V3 acceptance bundle immutable inspect 通过。
- Docker 基础环境探针通过。

## 修复记录

未修复任何既有改动。按照工作规则，当前与 V5 Stage 0 无关的改动不能由本轮擅自删除、回滚或提交。

## 是否允许进入下一阶段

不允许。P1 阻塞项必须先消除。下一次进入 V5 Stage 0 时，应在 V4 doc-sync acceptance bundle immutable inspect 重新通过后，再读取完整 V5 文档并进入 Stage 1。
