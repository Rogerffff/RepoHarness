# V3 Stage 01 Implementation Review

## 审查范围

本审查覆盖阶段 1 的 schema、配置扩展、版本常量、可见性策略和污染 denylist：

- V3 schema/version constants。
- Docker runtime config、Docker backend facts、container execution facts。
- Real repository source facts。
- SWE-Bench-like task facts、task adapter facts、environment spec 和 verifier plan。
- Run checkpoint 和 experiment resume manifest。
- Context compaction facts。
- Core failure diagnostics。
- ToolContractSnapshot、PermissionPolicySnapshot、HookPolicySnapshot、MCPPolicySnapshot。
- TrajectoryStoreFacts。
- CommandLogEntry 和 V3AcceptanceReport。
- V3VisibilityPolicy 和 V3ContaminationDenylist。
- 第一阶段新增和修改的单元测试、run config fixture。

本审查不覆盖 Docker backend factory、Docker command/file/patch execution、task adapter、source materialization、Agent Loop、Experiment Runner、export audit builder 或 final acceptance bundle，因为这些不属于阶段 1 范围。

## 审查命令

只读子代理和本地自审使用了以下命令：

- `git status --short`
- `git diff --stat`
- `git diff --name-only`
- `git diff -- src/repo_harness/...`
- `rg -n "V3ContaminationDenylist|assert_clean|scan_payload|model_visible|provider_raw|gold_patch|test_patch|FAIL_TO_PASS|PASS_TO_PASS|reward_metadata|run_outcome|credential|/Users/" src tests`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_visibility_policy.py tests/unit/test_v3_schemas.py tests/unit/test_config_schema.py tests/unit/test_experiment_config.py tests/unit/test_core_schemas.py -q`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_schemas.py tests/unit/test_v3_visibility_policy.py tests/unit/test_config_schema.py tests/unit/test_experiment_config.py tests/unit/test_task_schema.py tests/unit/test_v2_schemas.py tests/unit/test_export.py tests/unit/test_v2_acceptance.py`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_swebench_fixture.py tests/unit/test_v2_task_set.py tests/integration/test_export_from_run.py`
- 只读 Python 边界验证脚本，验证 acceptance 空 checks、缺污染扫描 refs、surface coverage 缺失、普通公开 patch 文本、普通公开 resolved 文本和各类污染 term。

最终提交前验证另行执行：

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH python -m pytest -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`

## 第一轮发现

### P1

未发现。

### P2

`V3AcceptanceReport` 允许 `status="passed"` 且 `checks=[]`，也没有 contamination scan refs、scan surface coverage、visibility policy version 或 denylist version 约束。这会导致后续阶段即使遗漏 prompt、prepared messages、tool observation、transcript、checkpoint、context compaction report、SFT/RL/preference export 的污染扫描，schema 仍可能表达“通过”。

修复：`V3AcceptanceReport` 新增 `visibility_policy_version`、`contamination_denylist_version`、`contamination_scan_refs` 和 `contamination_scan_surfaces`。`status="passed"` 现在必须包含非空 checks、非空 contamination scan refs，并覆盖全部 `V3_VISIBILITY_SURFACES`。

### P2

`V3ContaminationDenylist` 把普通 `patch` 作为隐藏引用禁词，导致公开软件工程语句例如 “submit a patch” 被误拦。裸 `resolved` / `unresolved` 也可能误伤公开 issue 文本。

修复：移除普通 `patch`、裸 `resolved` 和裸 `unresolved` 的通用字符串匹配。denylist 继续拦截 `gold_patch`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS`、official status key/value、official harness/report、provider raw、credential、本机绝对路径、hidden verifier result、reward metadata 和 run outcome。新增测试确认普通公开 patch 文本和普通公开 resolved 句子可以通过。

### P2

当前工作树存在大量与阶段 1 无关的既有改动或未跟踪文件，包括 V1 文档迁移或删除、`.vscode/`、`docs/build-your-own/`、`docs/resume/`、`docs/v1/`、`uv.lock` 等。若这些文件进入 Stage 1 commit，会违反阶段范围。

处理：这些改动记录为既有无关工作区状态，不回滚、不删除、不提交。Stage 1 commit 只 stage schema、policy、测试、fixture 和阶段文档相关文件。

### P3

`ExperimentResumeManifest` 只校验 `completed_run_ids`，没有校验 `pending_run_ids` 和 `interrupted_run_ids` 与 checkpoint 状态一致。

修复：同阶段内补齐 validator，校验 completed、pending 和 interrupted 三类 run ids 与 checkpoint 状态一致。新增 pending mismatch 负例测试。

## 第二轮复核

只读子代理复核确认：

- `V3AcceptanceReport` 已要求 passed 状态必须包含 checks、contamination scan evidence 和所有 V3 visibility surfaces 覆盖。
- `V3ContaminationDenylist` 不再误拦普通公开 patch 文本或普通公开 resolved 文本。
- `gold_patch`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS`、`provider_raw_response`、Authorization marker、本机绝对路径、reward metadata、run outcome 和 `{"officialStatus": "resolved"}` 均会被拦截。
- 定向复核测试结果为 `101 passed`。

复核仍指出一个 P3：`V3AcceptanceReport` 目前只要求 contamination scan evidence refs 和 surface 名称覆盖，还没有建立每个 surface 到 clean scan result 的结构化映射。该检查属于阶段 12 inspect 和 acceptance builder 的 evidence 内容校验范围，本阶段记录为后续必做项，不阻断阶段 2。

复核结论为：P1 未发现；代码层面 P2 已修复；有条件允许进入阶段 2，条件是 Stage 1 commit 必须排除无关既有工作树改动。

## 最终自审

在第二轮复核之后，本地又修复了 P3 resume manifest 约束，并重新运行第一阶段定向测试、compileall、全量 pytest、V2 acceptance 和 Stage 0 fixture inspect。

最终结果：

- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_visibility_policy.py tests/unit/test_v3_schemas.py tests/unit/test_config_schema.py tests/unit/test_experiment_config.py tests/unit/test_core_schemas.py -q`：`33 passed`。
- `PATH=.venv/bin:$PATH python -m compileall src`：通过。
- `PATH=.venv/bin:$PATH python -m pytest -q`：`397 passed in 148.21s`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`：通过。

## 结论

阶段 1 的 P1 未发现，P2 已修复，阶段内可修 P3 已修复。剩余 P3 是 acceptance builder / inspect 阶段的 evidence 内容映射校验，已记录为后续阶段必做项。只要提交时排除无关既有工作树改动，阶段 1 可以进入阶段 2。
