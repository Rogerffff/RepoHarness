# V4 阶段 0：基线确认和实施输入冻结

## 目标

本阶段只完成 V4 正式实施前的可信基线确认和 implementation input freeze。阶段 0 不接入 task adapter，不启动 rollout queue，不生成 V4 accepted / auditable task definitions，也不把 feasibility run 直接计入最终验收数量。

## 实现内容

- 新增 V4 Stage 0 schema version、visibility policy version、allowlist policy version 和 contamination denylist version。
- 新增统一的 `V4ContaminationDenylist`，用于后续阶段复用同一 denylist version、denylist sha256 和 allowlist policy version。
- 新增 `build-v4-implementation-inputs` 命令，在写入 Stage 0 产物之前运行正式 baseline、V2 regression、V3 acceptance、V3 acceptance bundle 和 Docker 探针。
- 新增 `inspect-v4-implementation-inputs` 命令，只读复核 manifest、绑定文件路径、sha256、denylist sha256、计数一致性、adapter-visible 输入污染扫描和 accepted counting 禁用状态。
- 绑定 PR / issue feasibility run 和 public SWE-Bench-like feasibility run，但明确标记 `accepted_counting_allowed=false`。
- 增加 V3 acceptance 兼容修复：历史 V3 pre-acceptance command log 中的 `python-m-pytest` 和 `inspect-v2-acceptance` 命令，如果 input ref 指向 `src` 或 `tests` 目录，则允许后续 V4 代码演进造成源码树哈希漂移。该修复不适用于 acceptance command log，不适用于其他命令，不适用于 output ref，也不放宽 V3 report、acceptance inputs、run selection、test evidence、bundle 和其他 ArtifactRef 的复核。

## 主要修改文件

- `src/repo_harness/schema_versions.py`
- `src/repo_harness/v4_visibility.py`
- `src/repo_harness/v4_implementation_inputs.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/v3_acceptance.py`
- `tests/unit/test_v4_implementation_inputs.py`
- `tests/integration/test_v3_acceptance_stage12.py`
- `docs/v4/evidence/implementation-inputs/`
- `docs/v4/review/implementation/00-baseline-and-input-freeze-review.md`

## 机器产物

- `docs/v4/evidence/implementation-inputs/v4_baseline_check_report.json`
  - sha256：`6ec75ac9ff41ae25a85567241d4a6d3a4a17b17161a98dc5f9a455ed610cf118`
- `docs/v4/evidence/implementation-inputs/v4_feasibility_input_binding.json`
  - sha256：`a5090a8a70663a58e24a298db3f6dc5d33fd4e1bed14e8a01bb096b127783561`
- `docs/v4/evidence/implementation-inputs/v4_implementation_input_audit_report.json`
  - sha256：`455a25280c97226f443cbe9f4cd571b164539df36fc3224109eed1eba5326ffe`
- `docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json`
  - sha256：`bb60544fd57840cda3ad49d2b9bcb1c0732062df0bc6e05ae0e3775b389e23b1`
- `V4ContaminationDenylist` 规则集 sha256：`cd22eb930ffa308f1f17127fd33135354f835e13c947d1a9d96edb598ed67e6e`

## 验证命令

```bash
pwd
git status --short
git log -1 --oneline
git status --short -- docs/v4
git diff --name-status -- docs/v4
git ls-tree -r --name-only f38cb93 docs/v4
git merge-base --is-ancestor f38cb93 HEAD
git merge-base --is-ancestor 17b1b95 HEAD
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
docker version
docker context show
docker info
docker info --format '{{json .MemTotal}}'
docker run --rm hello-world
docker run --rm alpine:3.20 uname -m
docker run --rm alpine:3.20 sh -lc 'grep MemTotal /proc/meminfo'
docker run --rm --platform linux/amd64 alpine:3.20 uname -m
PATH=.venv/bin:$PATH repo-harness build-v4-implementation-inputs --pr-issue-run runs/v4-pr-issue-task-source-feasibility-20260504T063745Z --public-swebench-run runs/v4-swe-task-feasibility-20260504T044301Z --v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --v3-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --output-dir docs/v4/evidence/implementation-inputs --run-live-baseline-checks --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-v4-implementation-inputs docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json --assert-complete
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_implementation_inputs.py tests/integration/test_v3_acceptance_stage12.py::test_v3_acceptance_allows_historical_repo_command_input_drift tests/integration/test_v3_acceptance_stage12.py::test_v3_acceptance_rejects_unmarked_repo_command_input_drift -q
```

## 验证结果

- 初始人工 baseline 检查通过：当前 `HEAD` 为 `f38cb93 docs: add V4 planning baseline`，`f38cb93` 和 `17b1b95` 均为当前 `HEAD` 祖先。
- 完整测试通过：`488 passed in 299.05s`。
- Stage 0 构建期间再次运行完整测试，baseline report 记录 `pytest=passed`。
- V2 acceptance inspect 通过。
- V3 acceptance inspect 通过。
- V3 acceptance bundle immutable inspect 通过。
- Docker Desktop 后端可用，Docker server 为 `linux/arm64`，内存约 32GB。
- `linux/amd64` Docker 探针通过，`uname -m` 返回 `x86_64`，因此本阶段没有 architecture compatibility risk。
- `inspect-v4-implementation-inputs --assert-complete` 通过。
- 针对性测试通过：`21 passed in 1.50s`。

## 正例证据

- PR / issue feasibility source 绑定 8 个 freeze-ready 候选，`accepted_counting_allowed=false`。
- public SWE-Bench-like feasibility source 绑定 5 个候选，`accepted_counting_allowed=false`。
- `v4_feasibility_input_binding.json` 中 PR / issue 计数为 `candidate_count=8`、`detail_count=8`、`freeze_ready_count=8`。
- `v4_feasibility_input_binding.json` 中 public SWE-Bench-like 计数为 `candidate_count=5`、`detail_count=5`、`freeze_ready_count=5`。
- `v4_implementation_input_audit_report.json` 的 `status=passed`，`failures=[]`。
- Stage 0 manifest、binding 和 audit report 均绑定同一个 denylist sha256：`cd22eb930ffa308f1f17127fd33135354f835e13c947d1a9d96edb598ed67e6e`。

## 负例证据

单元测试覆盖以下失败路径：

- implementation input manifest 指向不存在的 feasibility run path 时失败。
- 绑定 manifest 的 sha256 与实际文件不一致时失败。
- adapter-visible input 中出现 PR URL 时失败。
- adapter-visible input 中出现 issue URL 时失败。
- adapter-visible input 中出现 PR 编号时失败。
- adapter-visible input 中出现 issue 编号时失败。
- adapter-visible input 中出现 `gold_patch` marker 时失败。
- adapter-visible input 中出现 40 位 fix commit hash 时失败。
- adapter-visible input 中出现 hidden selector marker 时失败。
- adapter-visible input 中出现 AI session URL 时失败。
- adapter-visible input 中出现 PR body marker 时失败。
- adapter-visible input 中出现 PR diff marker 时失败。
- adapter-visible input 中出现 provider raw response marker 时失败。
- adapter-visible input 中出现 verifier raw output marker 时失败。
- feasibility manifest 汇总计数与明细行不一致且未降级为历史 audit-only artifact 时失败。
- denylist sha256 与当前统一规则集不一致时失败。
- CLI build / inspect 命令路径显式传入，不读取 latest run 或隐式当前目录。
- V3 command log 中没有历史命令身份的 `src` / `tests` 哈希漂移仍会失败。

## 允许降级项

- PR / issue feasibility run 中历史 partial probe artifact 只能作为 audit-only historical artifact 绑定，不能作为 accepted counting gate。
- public SWE-Bench-like selection summary 只作为 audit-only selector metadata 绑定，不能直接进入模型可见 task input。
- Stage 0 implementation inputs 全部保持 `accepted_counting_allowed=false`。
- 历史 V3 pre-acceptance command log 的 `src` / `tests` input ref 哈希漂移只允许用于指定历史命令，目的是让 V3 acceptance 在后续 V4 源码演进中仍可复核其历史 evidence。

## 禁止降级项

- V3 acceptance inspect 不允许失败。
- V3 acceptance bundle immutable inspect 不允许失败。
- V2 acceptance inspect 不允许失败。
- adapter-visible input 污染扫描不允许失败。
- feasibility source path、manifest path、sha256 和计数一致性不允许静默失败。
- `linux/amd64` Docker probe 如果失败，必须记录 architecture compatibility risk；本阶段实际没有该风险。
- V4 Stage 0 不允许把 feasibility 候选计入 V4 accepted / auditable task definitions。

## 已知限制

- 阶段 0 只冻结 implementation inputs；它不生成最终 V4 task definitions，不执行 source materialization repeat check，不运行 RepoHarness 自有 V4 verifier probe，也不执行 flaky probe 的正式 V4 验收逻辑。
- 阶段 0 不实现 rollout queue、task adapter integration、tool lifecycle audit、agent run integration、export quality、cards 或 V4 final acceptance。
- Stage 0 机器产物位于 tracked 文档目录中；正式构建器在写入这些产物之前已经验证 `docs/v4` 干净。

## 是否偏离设计文档

没有偏离 V4 implementation plan 的阶段顺序。本阶段没有提前实现后续阶段能力。

有一项兼容性说明：为了让 V4 后续代码变更后仍能复核 V3 acceptance bundle，`inspect-v3-acceptance` 对历史 pre-acceptance command log 中特定命令的 `src` 和 `tests` 目录 input ref 允许源码树漂移。该处理不放宽其他 evidence 的 sha256 复核，也不放宽 V3 report 或 bundle 的不可变性。

## 审查结论

subagent 初审发现 3 个 P2 和 2 个 P3。3 个 P2 已修复：V3 command log drift 例外收窄、denylist sha256 绑定、污染负例补齐。P3 中 baseline report 覆盖检查和更通用 AI session marker 负例也已一并修复。

完整审查记录保存在 `docs/v4/review/implementation/00-baseline-and-input-freeze-review.md`。

## 是否可以进入下一阶段

在修复后复审没有 P1 / P2 阻塞发现，且提交前 diff 检查和阶段验证继续通过后，可以进入阶段 1。
