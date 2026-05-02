# V3 Stage 00 Implementation Review

## 审查范围

本审查覆盖阶段 0 的实现和产物：

- `prepare-v3-swebench-fixture`
- `inspect-v3-swebench-fixture`
- `src/repo_harness/v3_swebench_fixture.py`
- `tests/unit/test_v3_swebench_fixture.py`
- `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/`
- `docs/v3/evidence/swebench-lite-fixed/evaluator_only/`

本审查不覆盖 Docker backend、task adapter、Agent Loop、source materialization 或 final verifier，因为这些不属于阶段 0 范围。

## 审查轮次和修复记录

### 第一轮

第一轮只读子代理审查发现 1 个 P1 和 2 个 P2：

- P1：冻结检查仍依赖未跟踪 `runs/` evidence。
- P2：没有从 feasibility source 验证 dataset split。
- P2：inspect 没有扫描整个 adapter-visible input root。

修复：source refs 改为 `source_provenance_refs`，只记录 `original_path`、`sha256` 和 `size_bytes`；inspect 不再读取原始 `runs/` source；prepare 读取并校验 `hf_dataset_schema.json` 的 dataset name、revision、split 和 Level 2 task ids；adapter root 增加额外文件和 raw hidden content 扫描。

### 第二轮

第二轮只读子代理审查发现 1 个 P2：adapter input root scan 跳过嵌套目录。

修复：inspect 现在拒绝 `adapter_inputs/` 下的任何嵌套目录，并递归扫描所有文件。

### 第三轮

第三轮只读子代理审查发现 1 个 P2：JSON 转义后的真实 hidden patch 可绕过原始文本扫描。

修复：inspect 现在解析 adapter root 中的 JSON 和 JSONL 文件，并递归扫描所有字符串 value。新增 JSON 转义 multiline hidden patch 负例。

### 第四轮

第四轮只读子代理审查发现 1 个 P2：允许的 adapter manifest 未递归拒绝 forbidden key。

修复：inspect 现在对 adapter-visible JSON 和 JSONL 文件递归扫描 key，拒绝 `patch`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS`、`model_patch`、`resolved`、`unresolved`、`official_report` 等 forbidden key。新增同步更新 sha256 后仍必须拒绝的负例。

### 第五轮

第五轮只读子代理审查发现 2 个 P2 和 1 个 P3：

- P2：来源文件哈希没有真正绑定到 Green 输入。
- P2：JSON 字段名形式的隐藏内容仍可绕过 inspect。
- P3：adapter-visible manifest 仍直接暴露 evaluator-only artifact 名称。

修复：prepare 新增 source sidecar、`hf_dataset_schema.json:candidate_field_sha256`、`level2_dataset_sha256`、decision report sha256 校验；inspect 同时扫描 JSON key 和 value；adapter-visible manifest 不再直接列出 evaluator-only 文件 refs 或敏感术语 policy 列表，只保留 evaluator evidence manifest ref 与抽象 visibility policy ref。

### 第六轮

第六轮只读子代理审查发现 1 个 P2 和 1 个 P3：

- P2：禁用字段表仍不完整。
- P3：evaluator manifest 缺少必需文件集合校验。

修复：forbidden key 扩展到 `gold_patch`、`official_harness`、`completed_ids`、`submitted_ids`、`resolved_instances`、`unresolved_instances` 等 official status 和 audit 字段；新增 forbidden visibility term 扫描；evaluator manifest 强制包含 `hidden_verifier_inputs`、`gold_patch_predictions` 和 `official_harness_reports` 三个 required refs。

### 第七轮

第七轮只读子代理审查发现 2 个 P2 和 1 个 P3：

- P2：adapter 可见 value 侧状态变体仍可漏过。
- P2：evaluator required refs 的 sidecar 校验可被外部路径绕过。
- P3：`environment_setup_commit` 如存在 schema hash，应参与来源字段哈希校验。

修复：forbidden visibility term 扩展到 `resolved`、`unresolved`、`completed`、`submitted`、`resolved_status`、`unresolved_status`、`official_status` 和 camelCase 变体；evaluator required refs 必须指向 canonical evaluator-only 文件路径并校验 sidecar；`environment_setup_commit` 在 schema 提供 hash 时参与校验。

### 第八轮

第八轮只读子代理审查发现 3 个 P2：

- P2：camelCase 禁用语义仍可绕过。
- P2：evaluator required ref 类型不强制为 file-ref。
- P2：prepare 只校验来源自洽，未硬绑定 Green 来源哈希。

修复：forbidden term 扫描加入归一化匹配，覆盖 `officialStatus`、`goldPatch`、`officialHarness`、`testPatch`、`failToPass`、`passToPass` 等 key/value 变体；evaluator required refs 必须是 object；prepare 增加 fixed Green source sha256 常量表，拒绝仅靠 source sidecar、schema 和 decision 自洽的篡改来源。

### 第九轮

第九轮只读子代理审查发现 1 个 P2：evaluator manifest 的三个 required refs 可退化为 path-only object。

修复：inspect 对三个 required refs 直接调用完整 file-ref 校验，缺少 `path`、`sha256` 或 `size_bytes`，或者 `sha256` / `size_bytes` 与文件不一致，均会失败。新增 path-only required ref 负例。

## 最终验证

- `PATH=.venv/bin:$PATH python -m compileall src`：通过。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_swebench_fixture.py -q`：`18 passed`。
- `PATH=.venv/bin:$PATH repo-harness prepare-v3-swebench-fixture --feasibility-root runs/v3-swe-feasibility-20260502T083722Z --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`：通过，返回 `status: passed`、`failures: []`。
- 自审探针：forbidden camelCase/status term 命中，path-only evaluator required ref 失败，fixed Green source sha256 常量存在。通过。
- `PATH=.venv/bin:$PATH python -m pytest -q`：`383 passed`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过。

## 最终只读复核

最终只读子代理复核结论：

- P1：未发现。
- P2：未发现。
- P3：未发现。
- 允许进入阶段 1。

复核确认：

- evaluator manifest 的三个 required refs 已要求完整 file-ref object，并强制校验 `path`、`sha256`、`size_bytes`。
- required refs 已强制指向 canonical evaluator-only 路径并校验 sidecar。
- forbidden term normalized matching 覆盖 `officialStatus`、`goldPatch`、`officialHarness`、`testPatch`、`failToPass`、`passToPass`、`resolved`、`unresolved`、`completed`、`submitted` 等 key/value 形式。
- prepare 已通过 `EXPECTED_SOURCE_SHA256` 和来源 sidecar 校验硬绑定 fixed Green source，不能只靠 self-consistent tampered source 通过。
- 当前 frozen fixture 的 inspect 返回 `status: passed`，`failures: []`。

## 结论

阶段 0 满足当前 V3 实施计划要求，可以进入阶段 1。后续阶段必须继续保持 adapter-visible 与 evaluator-only 分离，默认读取 `tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/`，不能默认读取未跟踪 `runs/` 目录。
