# V3 Stage 00 Feasibility Input Freeze

## 目标

阶段 0 的目标是把前置 SWE-Bench-like 可实现性实验冻结为第三版后续阶段可读取、可审计、可校验的固定输入。阶段 0 只实现输入冻结命令和只读检查命令，不实现 Docker backend、task adapter、source materialization、Agent Loop 或 final verifier。

本阶段使用 Green 路径，固定任务为：

- `pytest-dev__pytest-7220`
- `pytest-dev__pytest-8365`
- `sympy__sympy-24909`

## 实现内容

新增 `prepare-v3-swebench-fixture` 写型命令。该命令显式读取 `runs/v3-swe-feasibility-20260502T083722Z`，校验 `feasibility_decision.json`、`hf_dataset_schema.json`、固定 dataset revision、dataset split、SWE-Bench commit、accepted task 清单、Level 2 gold patch 全 resolved 状态、source sidecar、decision report sha256、candidate field sha256，以及阶段 0 固定 Green 来源文件 sha256 常量，然后生成受版本控制的 adapter-visible input 与 evaluator-only evidence。

新增 `inspect-v3-swebench-fixture` 只读检查命令。该命令只接收显式 `--fixture-dir`、`--evidence-dir` 和 `--manifest`，不读取 latest run，不猜测当前目录，不需要原始 `runs/` feasibility 目录存在。它重新读取固定输入、evaluator-only evidence refs 和 sha256 sidecar，检查 adapter-visible 目录中没有 evaluator-only 文件、未知额外文件、嵌套目录、raw hidden content、JSON 转义 hidden content、forbidden key、forbidden visibility term 或 evaluator-only required ref 漂移。

## 主要修改文件

- `src/repo_harness/v3_swebench_fixture.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v3_swebench_fixture.py`
- `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/`
- `docs/v3/evidence/swebench-lite-fixed/evaluator_only/`
- `docs/v3/implementation-log/00-stage-00-feasibility-input.md`
- `docs/v3/review/implementation/stage-00-review.md`

## 机器产物

Adapter-visible input：

- `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/swebench_like_tasks.jsonl`
- `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/task_input_manifest.json`
- `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json`
- 对应 `.sha256` sidecar 文件

Evaluator-only evidence：

- `docs/v3/evidence/swebench-lite-fixed/evaluator_only/hidden_verifier_inputs.jsonl`
- `docs/v3/evidence/swebench-lite-fixed/evaluator_only/gold_patch_predictions.jsonl`
- `docs/v3/evidence/swebench-lite-fixed/evaluator_only/official_harness_reports.json`
- `docs/v3/evidence/swebench-lite-fixed/evaluator_only/evaluator_evidence_manifest.json`
- 对应 `.sha256` sidecar 文件

## 验证命令和结果

- `PATH=.venv/bin:$PATH python -m compileall src`：通过。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_swebench_fixture.py -q`：`18 passed`。
- `PATH=.venv/bin:$PATH repo-harness prepare-v3-swebench-fixture --feasibility-root runs/v3-swe-feasibility-20260502T083722Z --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed`：通过，生成 `v3_feasibility_input_manifest.json`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`：通过，返回 `v3_swebench_fixture=frozen`。
- 自审探针：验证 `officialStatus`、`goldPatch`、`officialHarness`、`testPatch`、`failToPass`、`passToPass`、`resolved`、`unresolved_status`、`submittedIds` 等 key/value 变体命中 forbidden term；验证 path-only evaluator required ref 被 file-ref 校验拒绝；验证固定 Green source sha256 常量存在。通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH python -m pytest -q`：`383 passed`。

## 正例证据

- Green decision 必须为 `green_ready_for_v3_implementation_plan`，否则 prepare 命令失败。
- Dataset name 必须为 `princeton-nlp/SWE-bench_Lite`。
- Dataset revision 必须为 `6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`。
- Dataset split 必须由 `hf_dataset_schema.json` 验证为 `test`。
- SWE-Bench commit 必须为 `f7bbbb2ccdf479001d6467c9e34af59e44a840f9`。
- Accepted task ids 必须精确匹配三任务 Green 清单。
- Fixed Green source sha256 必须匹配阶段 0 常量表，不能只靠 source sidecar、schema 和 decision 字段自洽。
- `inspect-v3-swebench-fixture --assert-frozen` 在只保留冻结 fixture 与 evidence、删除原始 feasibility source 的单元测试场景中仍能通过。
- `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/` 的敏感术语扫描没有命中 `gold_patch`、`official_harness`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS`、`resolved` 或 `unresolved`。

## 负例证据

单元测试覆盖以下拒绝场景：

- 非 Green decision 被拒绝。
- Dataset split 不匹配被拒绝。
- 自洽更新 sidecar 和 schema 后篡改 dataset 字段仍被固定 Green source sha256 或 candidate field sha256 拒绝。
- Official report 被篡改后被固定 Green source sha256 或 decision report sha256 拒绝。
- Adapter-visible JSONL 被篡改导致 sha256 不匹配时被拒绝。
- Adapter input 根目录出现 evaluator-only 文件名被拒绝。
- Adapter input 根目录出现改名后的额外文件或 raw hidden content 被拒绝。
- Adapter input 根目录出现嵌套目录或嵌套 raw hidden content 被拒绝。
- Adapter manifest 中写入 JSON 转义后的 multiline raw hidden patch，即使同步更新 sha256，也会被拒绝。
- Adapter manifest 中把 raw hidden patch 写成 JSON key，即使同步更新 sha256，也会被拒绝。
- Adapter manifest 中写入 forbidden key，例如 `patch`、`resolved_ids`、`submitted_ids` 或 `official_report`，会被拒绝。
- Adapter manifest 中写入 forbidden visibility term，例如 `official_harness`、`gold_patch`、`officialStatus`、`goldPatch`、`testPatch`、`failToPass`、`passToPass`、`resolved`、`unresolved_status` 或 `submittedIds`，会被拒绝。
- Evaluator manifest 缺少 `hidden_verifier_inputs`、`gold_patch_predictions` 或 `official_harness_reports` required ref 时会被拒绝。
- Evaluator required ref 指向 evaluator-only canonical path 之外的位置会被拒绝。
- Evaluator required ref 不是 file-ref object，或缺少 `sha256` / `size_bytes`，会被拒绝。

## 允许降级项

本阶段没有使用 Yellow 路径，也没有替换任务。官方 SWE-Bench harness 只作为阶段 0 来源证明，未被用作 V3 final verifier。

## 禁止降级项

- 不允许跳过阶段 0 后先做 Docker backend 或 Agent Loop。
- 不允许从 Hugging Face 浮动默认分支重新读取任务。
- 不允许手工复制文件绕过 `prepare-v3-swebench-fixture`。
- 不允许 adapter-visible input 包含 raw `patch`、raw `test_patch`、raw `FAIL_TO_PASS`、raw `PASS_TO_PASS`、gold patch prediction、official harness report payload 或 resolved / unresolved / completed / submitted status。
- 不允许 evaluator-only required refs 漂移到 canonical evaluator-only 目录之外，或退化成不完整 file-ref object。

## 已知限制

阶段 0 只冻结任务输入和 evaluator-only evidence，不实现后续 task adapter、source materialization、Docker backend 或 RepoHarness 自有 final verifier。后续阶段必须继续默认读取 `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/`，不能默认读取 `runs/`。

## 设计偏离

没有偏离 Green 路径。为支持后续 RepoHarness 自有 verifier，本阶段额外生成 `hidden_verifier_inputs.jsonl`，用于 evaluator-only 保存 raw `test_patch`、`FAIL_TO_PASS` 和 `PASS_TO_PASS`。该文件不在 adapter-visible 目录中，并通过 evaluator evidence manifest 与 sha256 sidecar 绑定。

## 审查结论

阶段 0 经多轮只读子代理审查和修复。修复项包括：inspect 不再依赖未跟踪 `runs/` evidence；prepare 校验 dataset split；adapter root 递归扫描；拒绝嵌套目录；解析 JSON/JSONL 后扫描 key 和 value；拒绝 forbidden key 与 normalized forbidden term；source 输入固定 Green sha256 硬绑定；evaluator required refs 强制 canonical path、完整 file-ref 和 sidecar。

最终只读子代理复核结论为：P1 未发现、P2 未发现、P3 未发现，允许进入阶段 1。阶段 0 没有 deferred enhancement。
