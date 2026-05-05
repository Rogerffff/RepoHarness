# V5 Stage 0 preimplementation baseline

日期：2026-05-05

## 目标

在进入 V5 schema、task set、provider run matrix、export pack 和 demo artifacts 之前，完成 V5 Stage 0 的两件事：

- 绑定 V5 正式实施 baseline commit `9fd7007 docs: add V5 implementation baseline` 和后续澄清 commit `ee82434 docs: clarify V5 baseline gate timing`。
- 在不污染 V5 当前工作区的前提下，复核 V4 closure baseline、V2 / V3 regression、V4 doc-sync acceptance bundle、Docker execution mode 和 V5 preflight 输入。

## 结论

V5 Stage 0 已通过。`inspect-v5-preimplementation --assert-complete` 对以下输入返回通过：

```text
runs/v5-stage0-preimplementation-20260505T143530Z/v5_preflight_input_binding.json
```

当前 `HEAD` 为 `ee82434 docs: clarify V5 baseline gate timing`。`9fd7007` 和 V4 closure commit `e0da89c` 都仍然是当前 `HEAD` 的祖先。`docs/v5` 在 Stage 0 baseline gate 中没有被修改、删除或变成未跟踪文件。

## 重要时序说明

V4 doc-sync acceptance bundle 绑定了 V4 验收时的文件字节，其中顶层 `src` 哈希包含本地生成的 `src/repo_harness.egg-info`。该目录被 `.gitignore` 忽略，因此不能只依赖干净 Git 提交自然复现。

本轮没有在已经包含 V5 源码草稿变更的主工作区，把旧 V4 doc-sync bundle 的 immutable inspect 当作阶段门。为了满足 V5 文档要求，先建立独立还原快照：

```text
/tmp/repo-harness-v5-stage0-baseline-20260505T142500Z
```

该快照以 `ee82434` 为代码基线，并补入：

- V4 doc-sync bundle 绑定所需的 `src/repo_harness.egg-info` 本地打包元数据。
- V4 doc-sync bundle 绑定的 `docs/v4/final-acceptance.md` 和 `docs/v4/walkthrough.md` 当前字节。
- 主工作区 `runs/` evidence 的克隆副本，用于保持 V4 final command log 中的相对路径自引用检查可复现。

## 实现内容

- 增加 V5 Stage 0 schema version 常量。
- 增加 `repo-harness build-v5-preimplementation`。
- 增加 `repo-harness inspect-v5-preimplementation`。
- 增加 V5 Stage 0 command log、baseline report、V4 closure report、documentation sync report 和 preflight input binding builder。
- 修正外部 baseline worktree 命令执行环境：当 `--baseline-command-cwd` 指向独立快照时，命令执行环境会把该快照的 `src` 放到 `PYTHONPATH` 前面，避免误用主工作区已经包含 V5 草稿变更的 editable source。
- 增加 `.gitattributes` 规则，让 `runs/**/command_outputs/*.txt` 作为字节精确的原始命令输出证据提交，避免 Git whitespace 检查要求修改已经被 command log sha256 绑定的 stdout / stderr 文件。

## 主要修改文件

- `src/repo_harness/schema_versions.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/v5_evidence.py`
- `tests/unit/test_v5_preimplementation.py`
- `.gitattributes`
- `docs/v5/implementation-log/00-stage-0-preimplementation.md`
- `docs/v5/review/implementation/00-stage-0-preimplementation-review.md`

## 新增或更新的 schema

- `repo_harness_v5_schema_v0`
- `repo_harness_v5_evidence_ref_v0`
- `repo_harness_command_log_entry_v5_v0`
- `repo_harness_v5_baseline_check_report_v0`
- `repo_harness_v5_v4_closure_report_v0`
- `repo_harness_v5_documentation_sync_report_v0`
- `repo_harness_v5_preflight_input_binding_v0`

## 新增或更新的 inspect 命令

- `repo-harness inspect-v5-preimplementation V5_PREFLIGHT_INPUT_BINDING --assert-complete`

## 新增或更新的 tests

- `tests/unit/test_v5_preimplementation.py`

该测试覆盖 Stage 0 builder 的输出存在性、默认不覆盖旧 evidence、inspect 对完整输入通过、inspect 对错误 candidate count 失败、inspect 对 skipped command log 失败等基础行为。

## 机器产物

V5 Stage 0 机器产物目录：

```text
runs/v5-stage0-preimplementation-20260505T143530Z/
```

关键文件和 sha256：

| 文件 | sha256 |
| --- | --- |
| `v5_preflight_input_binding.json` | `9bb61057970e01fe91f32d998b9094f9db06284b7910ad273799805683953758` |
| `v5_baseline_check_report.json` | `020c62c7bbc123c4083048180a18a23c3b11cdde9be87b3dddcfb51435ae348d` |
| `v5_preimplementation_command_log.jsonl` | `2487764380d01e32b08bb47cd3959bb0005fa0bdd767e4df7a844452f1e98697` |
| `v4_review_findings_closure_report.json` | `3019fd3e8085a8bbb64a2c8982ae6557053ed11ad01b523bd5203de46133a479` |
| `v5_documentation_sync_report.json` | `a1db19084efef50f0670fddd0c16d17f7260cbea625df6524d0fc91f51257ec5` |

## 验证命令和结果

Stage 0 builder 在独立 baseline 快照中执行并记录了以下命令：

```bash
pwd
git status --short
git log -1 --oneline
git status --short -- docs/v5
git diff --name-status -- docs/v5
git ls-tree -r --name-only 9fd7007 docs/v5
git merge-base --is-ancestor 9fd7007 HEAD
git merge-base --is-ancestor e0da89c HEAD
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json --assert-immutable
docker version
docker context show
docker info
docker info --format '{{json .MemTotal}}'
docker run --rm hello-world
docker run --rm alpine:3.20 uname -m
docker run --rm alpine:3.20 sh -lc 'grep MemTotal /proc/meminfo'
docker run --rm --platform linux/amd64 alpine:3.20 uname -m
```

`v5_baseline_check_report.json` 中所有 baseline status 均为 `passed`。全量测试结果为：

```text
712 passed in 816.41s (0:13:36)
```

最终只读检查：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-preimplementation runs/v5-stage0-preimplementation-20260505T143530Z/v5_preflight_input_binding.json --assert-complete
```

结果为 `Inspect V5 preimplementation: complete` 和 `Inspect V5 preimplementation: passed`。

## 正例证据

- V5 baseline commit `9fd7007` 是当前 `HEAD` 的祖先。
- V4 closure commit `e0da89c` 是当前 `HEAD` 的祖先。
- `docs/v5` 在 baseline gate 中干净。
- V2 acceptance inspect 通过。
- V3 acceptance inspect 通过。
- V3 acceptance bundle immutable inspect 通过。
- V4 acceptance inputs inspect 通过。
- V4 acceptance report inspect 通过。
- V4 doc-sync acceptance bundle immutable inspect 在独立还原快照中通过。
- Docker Desktop context、内存探针、`hello-world`、`alpine:3.20` arm64 和 `linux/amd64` 探针通过。
- V5 preflight input 明确记录 initial candidate count 为 10，PR / issue candidate count 为 6，SWE-Bench-like anchor count 为 4。

## 负例证据

- 当前 10 个 preflight candidates 不能计入 V5 final accepted task、real provider run 或 training sample。
- 当前 preflight 只满足 Stage 0 输入冻结，不满足 V5 core acceptance 的严格任务库存门。后续 Stage 2B 仍必须补齐 2 个 PR / issue candidates，或者通过正式范围变更修改 scope、preflight plan 和 review 记录。

## 允许降级项

无。Stage 0 baseline gate 不能降级为 warning。

## 禁止降级项

- 不得把 Stage 0 preflight 输入直接计为 V5 final accepted task。
- 不得把 Stage 0 preflight 输入直接计为真实 provider run。
- 不得把 Stage 0 preflight 输入直接计为训练样本。
- 不得在 V5 源码变更后的主工作区，把旧 V4 doc-sync bundle immutable inspect 当作后续阶段门。
- 不得降低 12 total / 8 PR-issue / 3 SWE-Bench-like anchor 的任务库存门，除非先完成正式范围文档和审查记录修订。

## 已知限制

- Stage 0 只完成 baseline proof 和 preflight input binding，没有实现 V5 task set、provider gate、run matrix、export pack、demo artifacts 或 acceptance bundle。
- 主工作区存在大量与 Stage 0 无关的既有改动，本阶段没有删除、回滚或提交这些无关改动。
- V4 doc-sync acceptance bundle 的可复现性依赖独立快照补入 `src/repo_harness.egg-info`，这是因为 V4 历史 command log 绑定了该本地生成目录。

## 是否偏离设计文档

没有偏离。V5 implementation plan 要求 Stage 0 先冻结 V4 closure baseline 和 V5 preflight 输入；本轮正是按这个顺序完成。对 V4 doc-sync bundle 的复核使用独立还原快照，符合 V5 文档中关于旧 V4 bundle 时序边界的要求。

## Subagent 或等价自审结论

已安排只读 subagent 审查 `runs/v5-stage0-preimplementation-20260505T143530Z/`。审查记录保存到：

```text
docs/v5/review/implementation/00-stage-0-preimplementation-review.md
```

## 是否可以进入下一阶段

可以进入 V5 Stage 1。进入 Stage 1 后不得再把旧 V4 doc-sync bundle immutable inspect 作为当前 V5 工作区的阶段门；该检查结果已经由 Stage 0 的 `v5_baseline_check_report.json`、`v5_preflight_input_binding.json` 和 command log 绑定。
