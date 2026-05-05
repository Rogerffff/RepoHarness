# V5 Stage 0 baseline gate blocker

日期：2026-05-05

## 目标

在进入 V5 实现之前，确认当前分支满足 V5 正式实施基线、V4 closure baseline、V2 / V3 / V4 回归验收和本机 Docker execution mode 预检要求。

## 结论

V5 Stage 0 未通过。当前 `HEAD` 是 V5 正式实施 baseline commit `9fd7007 docs: add V5 implementation baseline`，并且 `9fd7007` 与 V4 closure commit `e0da89c test: refresh V4 acceptance evidence after hardening` 都是当前 `HEAD` 的祖先；但是工作区存在大量与 V5 Stage 0 无关的既有改动，其中包括 `src/repo_harness/evaluation/runner.py` 修改。该源码漂移导致 V4 最新 doc-sync acceptance bundle 的哈希复查失败，因此当前工作区不是可信的 V5 implementation baseline。

按照 V5 implementation plan 和用户指令，本轮停止进入 Stage 1，不实现 V5 schema、builder、inspect、task set、provider run matrix 或 demo artifact。

## 工作区状态摘要

预检开始时执行 `git status --short`，发现以下关键风险：

- `AGENT.md` 被删除。
- `AGENTS.md` 是未跟踪文件。
- `src/repo_harness/evaluation/runner.py` 被修改。
- 多个 V4 和核心设计文档被修改。
- 多个 V1 历史文档和实现日志被删除或迁移。
- `docs/v5` 自身没有修改、删除或未跟踪文件。

## 已执行命令和结果

| 命令 | 结果 |
| --- | --- |
| `pwd` | `/Users/roger/Desktop/claude-code` |
| `git status --short` | 失败门禁风险：工作区存在大量非 V5 既有改动 |
| `git log -1 --oneline` | `9fd7007 docs: add V5 implementation baseline` |
| `git status --short -- docs/v5` | 无输出，`docs/v5` 干净 |
| `git diff --name-status -- docs/v5` | 无输出，`docs/v5` 无 diff |
| `git ls-tree -r --name-only 9fd7007 docs/v5` | 列出 5 个已审查 V5 文档 |
| `git merge-base --is-ancestor 9fd7007 HEAD` | 通过，退出码为 0 |
| `git merge-base --is-ancestor e0da89c HEAD` | 通过，退出码为 0 |
| `PATH=.venv/bin:$PATH python -m compileall src` | 通过 |
| `PATH=.venv/bin:$PATH python -m pytest -q` | 通过，`712 passed in 601.01s` |
| `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete` | 通过，`status: passed`，`task_count: 20` |
| `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete` | 通过 |
| `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable` | 通过 |
| `PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json --assert-complete` | 失败 |
| `PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json --assert-complete` | 失败 |
| `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json --assert-immutable` | 失败 |
| `docker version` | 通过，client/server 均为 `29.4.1` |
| `docker context show` | 通过，当前 context 为 `desktop-linux` |
| `docker info` | 通过，Docker Desktop server 架构为 `aarch64`，内存约 `31.29GiB` |
| `docker info --format '{{json .MemTotal}}'` | 通过，输出 `33598365696` |
| `docker run --rm hello-world` | 通过 |
| `docker run --rm alpine:3.20 uname -m` | 通过，输出 `aarch64` |
| `docker run --rm alpine:3.20 sh -lc 'grep MemTotal /proc/meminfo'` | 通过，输出 `MemTotal: 32810904 kB` |
| `docker run --rm --platform linux/amd64 alpine:3.20 uname -m` | 通过，输出 `x86_64` |

## V4 baseline 失败细节

`inspect-v4-inputs` 失败原因：

```text
acceptance_command_log[1].input_refs[1] sha256 不匹配：src
acceptance_command_log[2].input_refs[1] sha256 不匹配：src/repo_harness
acceptance_command_log[3].input_refs[1] sha256 不匹配：src
```

`inspect-v4-acceptance` 失败原因：

```text
acceptance_inputs_ref 复查失败：
acceptance_command_log[1].input_refs[1] sha256 不匹配：src
acceptance_command_log[2].input_refs[1] sha256 不匹配：src/repo_harness
acceptance_command_log[3].input_refs[1] sha256 不匹配：src
```

V4 doc-sync acceptance bundle immutable inspect 失败原因：

```text
acceptance bundle 传递性复查 v4_acceptance_report 失败：
acceptance_inputs_ref 复查失败：
acceptance_command_log[1].input_refs[1] sha256 不匹配：src
acceptance_command_log[2].input_refs[1] sha256 不匹配：src/repo_harness
acceptance_command_log[3].input_refs[1] sha256 不匹配：src
```

## 机器产物

本轮没有生成 V5 acceptance inputs、V5 acceptance report、V5 acceptance bundle、V5 task set、V5 run matrix、V5 export result pack 或 V5 demo artifact。

本轮新增的唯一 Stage 0 产物是人工阻塞记录：

- `docs/v5/implementation-log/00-stage-0-baseline-blocker.md`
- `docs/v5/review/implementation/00-stage-0-baseline-blocker-review.md`

## 正例证据

- V5 baseline commit 和 V4 closure commit 的祖先关系通过。
- `docs/v5` 在预检时没有被修改、删除或变成未跟踪文件。
- 全量测试通过，结果为 `712 passed`。
- V2 acceptance inspect 通过。
- V3 acceptance inspect 通过。
- V3 acceptance bundle immutable inspect 通过。
- Docker 基础环境和 `linux/amd64` 平台运行探针通过。

## 负例证据

- V4 acceptance inputs inspect 未通过。
- V4 acceptance report inspect 未通过。
- V4 doc-sync acceptance bundle immutable inspect 未通过。
- 失败原因集中在 `src` 和 `src/repo_harness` 的 sha256 与 V4 closure evidence 绑定值不一致。

## 允许降级项

无。Stage 0 baseline gate 是进入 V5 implementation 的硬门槛，不允许降级为 warning。

## 禁止降级项

- 不得在当前不可信 baseline 上继续实现 V5 Stage 1。
- 不得把 V4 doc-sync bundle inspect 的 sha256 漂移解释为可忽略问题。
- 不得通过修改 V4 acceptance evidence 来掩盖当前工作区源码漂移。
- 不得删除、回滚或提交当前工作区中与本阶段无关的既有改动。

## 已知限制

本轮没有读取完整 V5 implementation plan 和所有设计文档，因为 Stage 0 的硬性前置门禁已经失败。继续读取和实现不会改变当前工作区不可信的事实，反而可能扩大无效工作范围。

## 是否偏离设计文档

没有偏离。V5 文档要求 Stage 0 先确认 V4 closure baseline 和 V5 preflight 输入冻结；当前 V4 closure baseline 复查失败，因此停止。

## 是否可以进入下一阶段

不可以。必须先在干净基线下重新运行 Stage 0 预检，或者由用户明确处理当前与 V5 Stage 0 无关的既有改动并恢复 V4 doc-sync acceptance bundle immutable inspect 通过后，才能进入 V5 Stage 1。
