# Stage 16D.1 执行计划：真实 verifier healthcheck smoke

本文是 Stage 16D.1 的具体执行计划。它承接
[39-stage-16d-execution-plan.md](39-stage-16d-execution-plan.md) 中已经实现的 schema、builder
和 inspector，把 Stage 16D 从“本地 contract evidence 已经闭合”推进到“至少一组真实 verifier
healthcheck 结果可以被机器验收”。

Stage 16D.1 的定位非常明确：

```text
用极小样本真实运行 verifier healthcheck。
验证 gold patch 和 no-op patch 的真实执行结果能进入 Stage 16D evidence。
验证 inspect-stage16d-healthcheck --assert-official-healthcheck-complete 真的能通过真实结果。
不训练模型，不扩大工具权限，不把小样本 smoke 外推成全量任务池已经健康。
```

## 1. 背景和阶段边界

Stage 16D 已经完成下面能力：

```text
healthcheck schema
healthcheck artifact builder
inspect-stage16d-healthcheck
本地 contract evidence
official input builder
Stage 16D.0 seed manifest 绑定
公开 evidence 泄漏扫描
```

但是 Stage 16D 的本地 evidence 仍然是 schema / classification / inspector 级别，它没有真正对 seed
运行：

```text
gold patch -> official verifier
no-op patch -> official verifier
```

因此 Stage 16D.1 的目标不是新增大模块，而是补一次真实 smoke：

```text
Stage 16D.0 seed 中选出极小 concrete seed 子集
-> 准备 gold / no-op official harness 输入
-> 使用真实 verifier runner 运行
-> 生成 runtime-private raw result
-> 转成 Stage 16D results JSONL
-> 调用 build_stage16d_healthcheck_artifacts.py
-> inspect-stage16d-healthcheck --assert-official-healthcheck-complete
```

Stage 16D.1 不是 Stage 17 任务注册表，也不是 SWE-Bench 大规模评测。只有本阶段实际选中的
small smoke seed 可以被标记为 official-complete；Stage 16D.0 的其它 seed 仍然保持
`diagnostic_only_until_stage16d_healthcheck_passes`。

## 2. 通过标准

Stage 16D.1 完成时必须满足两层条件：

第一层是 official-complete 执行完整性。这里的 `official_healthcheck_complete=true` 只表示：

```text
本次 smoke manifest 中所有 concrete seed 都有真实 official gold/no-op 执行结果。
这些结果都有 image / runner digest、runtime-private result ref 和 sha256。
inspect-stage16d-healthcheck --assert-official-healthcheck-complete 能通过。
```

它不表示每个 seed 都健康，也不表示每个 seed 都能进入训练。Stage 16D 当前 inspector 的语义就是
“真实结果齐全且可审计”，而训练资格由 `healthcheck_training_disposition` 单独决定。

第二层是 Stage 16D.1 smoke 成功性。它要求至少一个 positive-path seed 真实健康：

```text
至少 1 个 positive-path concrete seed 的 gold patch 真实 official verifier 结果为 resolved。
同一个 positive-path seed 的 no-op / empty patch 真实 official verifier 结果为 unresolved。
runner / harness digest 和 per-instance execution image digest 都已锁定；只有 official runner 本身就是
单层固定执行环境，并能证明不存在独立 per-instance execution image 时，才允许使用等价单层
environment digest。
raw official result 只保存在 runtime-private evidence。
公开 evidence 只包含 sha256、opaque ref、状态和聚合计数。
Stage 16D official-complete inspector 通过。
```

如果同时完成 2 个 concrete seed 更好。推荐目标是：

```text
必需：1 个 positive-path concrete seed
推荐：再加 1 个 no-op oracle risk seed
```

最小成功口径：

```text
selected_concrete_seed_count >= 1
selected_positive_path_seed_count >= 1
positive_path_gold_healthcheck_pass_count == selected_positive_path_seed_count
positive_path_noop_expected_unresolved_count == selected_positive_path_seed_count
official_healthcheck_complete = true
official_healthcheck_assert_complete_passed = true
training_eligible_after_healthcheck_count >= selected_positive_path_seed_count
stage16d1_positive_path_healthcheck_passed = true
```

如果选中的 positive-path seed 出现 gold patch 不通过或 no-op patch 异常通过，但 official harness
确实执行完成、image digest 已锁定、runtime-private result ref 齐全，那么
`official_healthcheck_complete=true` 仍然可以成立，因为真实结果是完整且可审计的。但是
Stage 16D.1 的 positive-path smoke 不能标记为通过，必须记录：

```text
environment_or_oracle_invalid
diagnostic_only
stage16d1_positive_path_healthcheck_passed = false
```

只有 official harness 无法启动、Docker 不可用、runner 未执行、image digest 无法锁定或 raw result
artifact 不完整时，才应写成：

```text
official_healthcheck_complete = false
```

如果选中的 no-op oracle risk seed 出现 no-op 异常通过，这不必然让整个 Stage 16D.1 失败。它应被
记录为真实风险发现：

```text
noop_healthcheck_status = noop_unexpectedly_resolved
healthcheck_training_disposition = environment_or_oracle_invalid
stage16d1_risk_seed_classification_complete = true
```

也就是说，positive-path seed 负责证明一条健康任务路径真实可用；risk seed 负责证明异常任务会被真实
分类，而不是被误放进训练候选。

## 3. 非目标

Stage 16D.1 不做下面事情：

- 不训练模型。
- 不运行真实模型 rollout。
- 不修改 Stage 16A 的 `execute_bash` 工具面。
- 不修改 Stage 16B 的 `diagnostic_shell` 生命周期。
- 不把 official harness 的隐藏 selector、gold patch 原文、test patch 原文或 official raw report 放进公开 evidence。
- 不要求 Stage 16D.0 manifest 中所有 concrete seed 都完成 healthcheck。
- 不把本次小样本 smoke 外推为 SWE-Bench Verified 全量稳定。
- 不把内部 proxy verifier 成功当成 official healthcheck 成功。
- 不把 synthetic / mock result 填进 `--assert-official-healthcheck-complete` 路径。

## 4. 推荐 seed 选择

Stage 16D.1 必须使用一个新的小样本 seed manifest，不直接复用 Stage 16D.0 的全量 manifest。
原因是 Stage 16D.0 包含多个诊断性质不同的 seed，其中有些是已知 no-op 风险、gold unhealthy
候选或 flaky 候选。Stage 16D.1 smoke 应先证明一条真实路径可以跑通，再扩大到完整 Stage 16D seed
集合。

建议新增运行时或公开安全的 smoke seed manifest：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_1/stage16d_1_official_smoke_seed_manifest.json
```

推荐 seed 优先级：

```text
第一优先级：django__django-17029
  seed_role = positive_path_official_resolved
  用途：验证正常 gold pass / no-op fail 的 happy path。

第二优先级：django__django-10097
  seed_role = noop_oracle_risk
  用途：验证疑似 no-op 风险任务是否能被真实 no-op healthcheck 识别。
  如果 no-op 异常 resolved，应把该 seed 标成 environment_or_oracle_invalid，而不是失败提交。

备用 seed：sphinx-doc__sphinx-9591
  seed_role = positive_path_official_resolved
  用途：当 django seed 因官方镜像或依赖问题不可跑时，作为第二条 positive path 候选。
```

第一版最小 smoke 可以只选 `django__django-17029`。如果 official harness 环境已经稳定，建议同时
选择 `django__django-10097`，因为它能验证 no-op 风险分类是否真实有效。

如果选择了 risk seed，则通过标准不能要求所有 selected seed 都成为 `trainable_candidate`。risk seed
只需要满足“真实执行完成、分类正确、不会进入训练候选”。

### 4.1 不能直接使用 aggregate seed

下面 seed 不能直接进入 Stage 16D.1 official-complete smoke：

```text
repr20-gold-smoke-aggregate
```

它是 aggregate evidence，不是可运行 concrete instance。除非先展开成具体 instance 列表，并生成新的
seed resolution evidence，否则它只能保留为 diagnostic 背景。

## 5. 真实 verifier 路线

Stage 16D.1 按三条 verifier 路线分层执行。

### 5.1 路线 A：SWE-Bench-like official harness smoke

这是本阶段必须完成的路线。

输入：

```text
selected Stage 16D.0 concrete seed
SWE-Bench Verified dataset row 或等价 official harness row
dataset gold patch
empty patch / no-op patch
official harness Docker image 或 official runner
official image digest / runner digest
```

执行：

```text
gold patch official run
no-op patch official run
```

预期：

```text
gold official_resolved = true
noop official_resolved = false
```

如果 gold 或 no-op 结果不符合预期，不能修 summary 让 inspector 强行通过。必须保留真实结果，并让
`build_stage16d_healthcheck_artifacts.py` 把该 seed 分类为不可训练或诊断。

### 5.2 路线 B：RepoHarness-owned verifier healthcheck

这是本阶段推荐完成的补充路线，用于验证内部微型任务池的 healthcheck 机制也可以工作。

推荐选择 1 到 2 个当前仓库已有 fixture，例如：

```text
buggy_calculator
import_config_bug
missing_helper_file
```

每个内部 fixture 需要构造：

```text
known-good patch -> RepoHarness final verifier should accept
empty patch -> RepoHarness final verifier should reject
```

这条路线的结果不能替代 SWE-Bench official healthcheck，但可以写入：

```text
stage16d_1_repo_harness_owned_verifier_report.json
```

报告必须明确：

```text
official_validation_backend = repo_harness_owned_verifier
not_swebench_official
not_leaderboard_comparable
```

### 5.3 路线 C：R2E-Gym / SWE-Gym dataset-native runner

这条路线是可选项。只有在本机或远端已经有 reference runner，且不需要临时设计大量适配代码时才执行。

如果执行，必须把结果写成独立报告：

```text
stage16d_1_dataset_native_runner_report.json
```

如果没有 reference runner，不阻塞 Stage 16D.1。此时写：

```text
dataset_native_runner_status = not_available_in_stage16d_1
```

## 6. Evidence 设计

### 6.1 运行目录

Stage 16D.1 推荐运行目录：

```text
runs/repo-harness-verl-stage16d1-official-smoke-<timestamp>/
```

公开 evidence 文件：

```text
stage16d_acceptance_summary.json
stage16d_input_seed_manifest.json
stage16d_healthcheck_manifest.json
stage16d_seed_resolution_report.json
stage16d_gold_healthcheck_report.json
stage16d_noop_healthcheck_report.json
stage16d_proxy_official_disagreement_report.json
stage16d_training_disposition_report.json
stage16d_public_leak_scan_report.json
stage16d_command_log.sanitized.jsonl
stage16d_canonical_evidence_map.json
stage16d_1_smoke_scope_report.json
stage16d_1_official_runner_report.json
stage16d_1_repo_harness_owned_verifier_report.json
```

可选公开 evidence：

```text
stage16d_1_dataset_native_runner_report.json
```

runtime-private evidence 文件：

```text
runtime_private/stage16d_command_log.raw.jsonl
runtime_private/stage16d_1_selected_dataset_rows.jsonl
runtime_private/stage16d_1_gold_predictions.jsonl
runtime_private/stage16d_1_noop_predictions.jsonl
runtime_private/stage16d_1_gold_results.jsonl
runtime_private/stage16d_1_noop_results.jsonl
runtime_private/official_runner_logs/
runtime_private/official_report_dirs/
runtime_private/gold_patch_inputs/
runtime_private/noop_patch_inputs/
```

runtime-private 文件不能提交到 Git。公开 evidence 中只能通过下面方式引用它们：

```text
runtime-private:<artifact-kind>:<sha256>
```

公开 evidence 根目录中的可传播产物不能出现：

```text
gold patch 原文
test patch 原文
FAIL_TO_PASS
PASS_TO_PASS
hidden_verifier
本机绝对路径
官方 raw report 中的完整路径
runtime_private 真实目录路径
```

这里的“可传播产物”指运行目录中的 summary、report、manifest、sanitized log 和 canonical evidence map。
执行计划文档、单元测试、扫描规则说明文档可以在规则上下文里出现 `FAIL_TO_PASS`、`PASS_TO_PASS`、
`/private/`、`diff --git`、`@@` 等拒绝词，但它们不能作为真实 evidence 内容或 raw result 泄漏出现。

`stage16d_1_smoke_scope_report.json` 必须说明本次 smoke 的覆盖范围：

```text
source_manifest_ref
source_manifest_sha256
selection_policy
selected_instance_ids
selected_positive_path_seed_count
selected_risk_seed_count
full_stage16d0_seed_coverage_claimed = false
remaining_stage16d0_seed_count_not_healthchecked
dataset_name
dataset_split
dataset_revision_or_snapshot
selected_dataset_rows_ref
selected_dataset_rows_sha256
selected_instance_row_sha256_by_instance
```

如果不扩展 `stage16d_input_seed_manifest.json`，这些 scope 字段必须保存在
`stage16d_1_smoke_scope_report.json`，并且该报告必须进入 `stage16d_canonical_evidence_map.json`。

### 6.2 Result JSONL 格式

Stage 16D builder 期望 gold / noop results JSONL 中每条记录至少包含：

```json
{
  "instance_id": "django__django-17029",
  "check_kind": "gold_patch",
  "official_resolved": true,
  "official_harness_execution_status": "executed",
  "official_image_source": "swebench_official_harness:<image-or-runner-ref>",
  "official_image_digest": "sha256:<64-hex-digest>",
  "official_image_digest_locked": true,
  "selected_dataset_rows_ref": "runtime-private:selected-dataset-rows:<64-hex-digest>",
  "selected_dataset_rows_sha256": "<64-hex-digest>",
  "selected_instance_row_sha256": "<64-hex-digest>",
  "gold_predictions_ref": "runtime-private:gold-predictions:<64-hex-digest>",
  "gold_predictions_sha256": "<64-hex-digest>",
  "noop_predictions_ref": "runtime-private:noop-predictions:<64-hex-digest>",
  "noop_predictions_sha256": "<64-hex-digest>",
  "official_command_ref": "runtime-private:official-command:<64-hex-digest>",
  "official_command_sha256": "<64-hex-digest>",
  "official_result_ref": "runtime-private:official-result:<64-hex-digest>",
  "official_result_sha256": "<64-hex-digest>"
}
```

`official_result_ref` 中的 digest 必须和 `official_result_sha256` 完全一致。这个 digest 应来自
runtime-private raw result artifact，而不是公开 summary。

`selected_dataset_rows_ref`、`gold_predictions_ref`、`noop_predictions_ref` 和
`official_command_ref` 也必须是 runtime-private opaque ref，并且各自 digest 必须和对应 sha256
字段一致。这样才能机器化证明 official harness 当时使用的 dataset row、gold/no-op predictions
和命令参数就是本次 Stage 16D.1 选中的输入。

如果 official runner 只产出目录而不是单个 JSON 文件，则先把该 seed 的关键 raw report 聚合为一个
runtime-private JSON，再对该 JSON 计算 sha256。

### 6.3 Image digest / runner digest

official-complete 模式下不能使用未锁定 image 或未锁定 execution environment。

接受的记录方式：

```text
official_image_source = docker:<image>@sha256:<digest>
official_image_digest = sha256:<digest>
official_image_digest_locked = true
```

对于 SWE-Bench-like official harness，要区分两层环境：

```text
runner / harness 环境：运行 swebench.harness.run_evaluation 的代码和依赖环境。
per-instance execution 环境：实际执行某个 instance 测试的 Docker image、testbed image 或等价环境。
```

如果 official harness 使用 per-instance Docker image，必须按 selected seed 记录：

```text
execution_image_digest_by_instance
execution_image_source_by_instance
official_environment_digest_lock_method
```

如果 runner container 和 instance execution image 是两层，也必须分别记录：

```text
runner_digest
runner_digest_method
execution_image_digest_by_instance
```

如果使用本机安装的 official runner 而不是固定 Docker image，必须记录等价 runner digest：

```text
official_image_source = local_runner:<package-name-or-repo-ref>
official_image_digest = sha256:<runner-environment-digest>
official_image_digest_locked = true
official_runner_lock_method = pip_freeze_and_source_tree_digest 或 docker_image_digest
```

但只记录 local runner digest 不足以证明 official-complete。还必须证明 selected seed 的实际 execution
environment 被锁定。如果无法证明 per-instance execution environment 稳定，则不能通过
`--assert-official-healthcheck-complete`。

如果不能锁定 digest，则 Stage 16D.1 不能通过 `--assert-official-healthcheck-complete`。

## 7. 执行步骤

### Step 0：确认前置状态

运行：

```bash
git status --short
git rev-parse HEAD
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_stage16d_healthcheck_schema.py \
  tests/unit/test_stage16d_healthcheck_builder.py \
  tests/unit/test_stage16d_healthcheck_acceptance.py \
  tests/unit/test_pre_verl_swebench_official_inputs.py
PATH=.venv/bin:$PATH python -m compileall -q src scripts/pre_verl
```

要求：

```text
Stage 16D commit 124df743 或其后续提交在当前历史中。
Stage 16D focused tests 通过。
当前工作区不能有未提交的 Stage 16D 代码改动。
无关未跟踪 HTML、training_design 资料、平台凭证文档不得进入本阶段提交。
```

### Step 1：创建 Stage 16D.1 小样本 seed manifest

创建：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_1/stage16d_1_official_smoke_seed_manifest.json
```

最小内容：

```json
{
  "schema_version": "repo_harness_stage16d_1_official_smoke_seed_manifest_v0",
  "source_manifest_ref": "docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/stage16d_seed_task_manifest.json",
  "selection_policy": "small_real_official_healthcheck_smoke",
  "scope_limit": "This manifest is a smoke subset and does not claim full Stage 16D.0 seed coverage.",
  "seeds": [
    {
      "instance_id": "django__django-17029",
      "seed_role": "positive_path_official_resolved",
      "source_dataset": "swebench_verified",
      "source_evidence_ref": "docs/resume/swebench-verified-score-gap-investigation-progress.md",
      "source_doc_sha256": "<stage16d0-source-doc-sha256>",
      "gold_patch_source": "dataset_gold_patch_or_not_available",
      "noop_patch_source": "not_available",
      "official_validation_backend": "swebench_official_harness",
      "candidate_instance_status": "concrete_not_healthchecked_in_stage16d_0",
      "stage16d_execution_precondition": "run Stage 16D healthcheck before training use",
      "stage16d0_source_instance_id": "django__django-17029",
      "training_use_recommendation": "diagnostic_only_until_stage16d_1_official_healthcheck_passes"
    }
  ]
}
```

如果加入第二个 seed，建议使用：

```text
django__django-10097
```

并且明确它是 no-op oracle risk，不要求它成为训练候选。它的任务是验证 Stage 16D.1 能把真实
no-op 异常通过分类为不可训练。

创建 smoke manifest 后，还必须生成或保留一个 public scope report，避免 builder 丢弃 top-level
`source_manifest_ref`、`selection_policy`、`scope_limit` 后，后续读者无法判断这是 Stage 16D.0 的子集。
每条 seed 也应从 Stage 16D.0 投影公开安全字段，至少包括：

```text
gold_patch_source
noop_patch_source
source_evidence_ref
source_doc_sha256
candidate_instance_status
stage16d_execution_precondition
```

### Step 2：准备 official harness 输入

对每个 selected seed 准备两套输入：

```text
gold patch prediction
no-op / empty patch prediction
```

实现时需要注意：SWE-Bench official harness 可能会把完全空的 `model_patch` 归类为
`empty_patch_instances`，这种情况下不会真正执行测试。Stage 16D.1 的 no-op verifier smoke 不能只依赖
“空补丁被跳过”来证明 no-op unresolved。第一版可以使用一个非空但语义无关的 source-only no-op patch
强制 official harness 真实执行，例如只在源码文件中添加注释。该 no-op patch 原文必须保留在
`runtime_private`，公开 evidence 只能记录 opaque ref、sha256 和公开安全的 source label。

如果使用 `scripts/pre_verl/build_swebench_official_inputs.py`，必须保证：

```text
官方输入 builder 的内容级泄漏扫描开启。
runtime-private manifest 不提交。
official predictions JSONL 不作为公开 evidence 提交。
```

如果直接从 SWE-Bench dataset 构造输入，也必须遵守同样规则：

```text
dataset row raw content -> runtime_private
gold patch raw content -> runtime_private
no-op patch raw content -> runtime_private
public evidence -> opaque ref + sha256 only
```

同时必须记录 dataset 版本和行级 digest：

```text
dataset_name
dataset_split
dataset_revision_or_snapshot
selected_dataset_rows_ref
selected_dataset_rows_sha256
selected_instance_row_sha256_by_instance
```

公开 evidence 中可以出现 dataset 名称、split、revision、sha256 和 opaque ref；不能出现 raw dataset row
内容、gold patch 原文或 no-op prediction 原文。

### Step 3：运行真实 official verifier

推荐命令形态：

```bash
python -m swebench.harness.run_evaluation \
  -d <runtime_private/dataset.parquet-or-json> \
  -s test \
  -p <runtime_private/predictions.jsonl> \
  --max_workers 1 \
  --timeout 1800 \
  --cache_level instance \
  --clean false \
  -id <stage16d1-run-id> \
  --report_dir <runtime_private/official_report_dirs/<run-id>>
```

如果本机 Docker 环境已经配置好，可以在本机运行。否则使用 Stage 16B.5 已验证的
Docker-capable 远端后端运行，但必须把 raw result 下载回本地并生成 sanitized evidence。

每个 selected seed 至少运行两次：

```text
gold patch run
no-op patch run
```

也可以把 gold/no-op 放进同一个 official harness 批次，但 result extraction 必须能区分
`check_kind`。

### Step 4：生成 Stage 16D results JSONL

从 official raw report 提取：

```text
instance_id
check_kind
official_resolved
official_harness_execution_status
official_image_source
official_image_digest
official_image_digest_locked
runner_digest
execution_image_digest_by_instance
official_environment_digest_lock_method
selected_dataset_rows_ref
selected_dataset_rows_sha256
selected_instance_row_sha256
gold_predictions_ref
gold_predictions_sha256
noop_predictions_ref
noop_predictions_sha256
official_command_ref
official_command_sha256
official_result_ref
official_result_sha256
```

写入：

```text
runtime_private/stage16d_1_gold_results.jsonl
runtime_private/stage16d_1_noop_results.jsonl
```

注意：

```text
gold results JSONL 的 check_kind 必须是 gold_patch。
noop results JSONL 的 check_kind 必须是 noop_patch。
任何 not_run、runner_error、image_digest_unlocked 记录都不能被伪装成 executed。
official command 中实际使用的 dataset 和 predictions 文件 sha256 必须和 result JSONL 记录一致。
```

### Step 5：调用 Stage 16D artifact builder

示例：

```bash
PATH=.venv/bin:$PATH PYTHONPATH=src python scripts/pre_verl/build_stage16d_healthcheck_artifacts.py \
  --seed-manifest docs/agentic_RL/repo_harness_verl_workstreams/stage16d_1/stage16d_1_official_smoke_seed_manifest.json \
  --output-dir runs/repo-harness-verl-stage16d1-official-smoke-<timestamp> \
  --gold-results runs/repo-harness-verl-stage16d1-official-smoke-<timestamp>/runtime_private/stage16d_1_gold_results.jsonl \
  --noop-results runs/repo-harness-verl-stage16d1-official-smoke-<timestamp>/runtime_private/stage16d_1_noop_results.jsonl
```

如果 builder 当前不接受 Stage 16D.1 schema version，需要在 Stage 16D.1 实施时做一个很小的兼容更新：

```text
允许 stage16d_1 official smoke seed manifest 投影成 Stage 16D seed manifest 结构。
通过 stage16d_1_smoke_scope_report.json 或扩展后的 stage16d_input_seed_manifest.json 保留 source_manifest_ref 和 smoke scope 字段。
不能降低 Stage 16D.0 manifest 的完整性检查。
```

Stage 16D.1 实施还必须扩展 `Stage16DHealthcheckInputResult` 和 result loader。新增的
dataset rows、gold/no-op predictions、official command、runner digest 和 execution image digest
字段必须被 schema 接收、保存、校验并投影到 Stage 16D.1 报告。不能通过 `extra=ignore`、预处理删除
字段或其它“丢弃 extra fields”的方式兼容，否则 official-complete 会失去输入绑定意义。

### Step 6：运行 inspector

必须运行：

```bash
PATH=.venv/bin:$PATH PYTHONPATH=src python -m repo_harness.cli.main inspect-stage16d-healthcheck \
  runs/repo-harness-verl-stage16d1-official-smoke-<timestamp> \
  --assert-contract-complete

PATH=.venv/bin:$PATH PYTHONPATH=src python -m repo_harness.cli.main inspect-stage16d-healthcheck \
  runs/repo-harness-verl-stage16d1-official-smoke-<timestamp> \
  --assert-official-healthcheck-complete
```

两个命令都必须通过，Stage 16D.1 才能标记为完成。

Stage 16D.1 实施必须扩展 inspector 或增加等价 Stage 16D.1 检查逻辑。对 Stage 16D.1 run 执行
`--assert-official-healthcheck-complete` 时，除了原有 Stage 16D artifact，还必须检查：

```text
stage16d_1_smoke_scope_report.json 存在并进入 canonical evidence map。
stage16d_1_official_runner_report.json 存在并进入 canonical evidence map。
selected_dataset_rows_sha256 / gold_predictions_sha256 / noop_predictions_sha256 / official_command_sha256 存在。
runtime-private opaque refs 的 digest 与对应 sha256 一致。
runner_digest 和 execution_image_digest_by_instance 已锁定。
full_stage16d0_seed_coverage_claimed = false。
```

如果 `stage16d_1_repo_harness_owned_verifier_report.json` 暂不执行，也必须生成公开安全报告：

```text
status = not_run_in_stage16d_1
reason = optional_supplement_not_required_for_official_smoke
```

### Step 7：公开 evidence 扫描

公开 evidence 扫描必须覆盖：

```text
*.json
*.jsonl
*.md
*.log
*.txt
*.yaml
*.yml
*.sh
```

扫描规则至少拒绝：

```text
/Users/
/private/
/workspace/
runtime_private 真实路径
FAIL_TO_PASS
PASS_TO_PASS
hidden_verifier
gold_patch 原文
test_patch 原文
diff --git
@@
```

允许的上下文必须写入 allowlist，例如：

```text
字段名 gold_healthcheck_status
字段名 noop_healthcheck_status
状态名 gold_healthcheck_failed
状态名 noop_unexpectedly_resolved
runtime-private:<kind>:<sha256> opaque ref
```

## 8. 失败处理

### 8.1 official harness 无法运行

如果 Docker 不可用、official package 缺失、镜像拉取失败或 runner 启动失败：

```text
Stage 16D.1 不通过。
生成 blocked evidence。
official_harness_execution_status = runner_unavailable 或 equivalent。
official_healthcheck_complete = false。
不能把本地 contract evidence 当成替代。
```

### 8.2 gold patch 不通过

如果 gold patch 结果不是 resolved：

```text
gold_healthcheck_status = gold_healthcheck_failed
overall_healthcheck_status = gold_healthcheck_failed
healthcheck_training_disposition = environment_or_oracle_invalid
invalid_for_training = true
invalid_for_online_rl = true
```

这不是模型失败样本，也不能进入训练。

### 8.3 no-op patch 异常通过

如果 no-op / empty patch 结果是 resolved：

```text
noop_healthcheck_status = noop_unexpectedly_resolved
overall_healthcheck_status = noop_unexpectedly_resolved
healthcheck_training_disposition = environment_or_oracle_invalid
invalid_for_training = true
invalid_for_online_rl = true
```

这说明 verifier 对该任务缺少基本区分力，不能作为模型成功或模型失败样本进入训练。

### 8.4 official image digest 无法锁定

如果 `official_image_digest_locked != true`：

```text
official_healthcheck_complete = false
healthcheck_training_disposition = diagnostic_only
```

不能为了让 smoke 通过而写假 digest。

## 9. 本地测试计划

Stage 16D.1 实施应补充或复用下面测试：

```text
tests/unit/test_stage16d_healthcheck_schema.py
tests/unit/test_stage16d_healthcheck_builder.py
tests/unit/test_stage16d_healthcheck_acceptance.py
tests/unit/test_pre_verl_swebench_official_inputs.py
```

建议新增测试：

```text
tests/unit/test_stage16d_1_official_smoke_plan.py 或合并到 Stage 16D builder 测试
```

需要覆盖：

```text
Stage 16D.1 smoke seed manifest 能被 builder 接受或正确投影。
Stage 16D.1 smoke manifest 的 source manifest ref、selection policy 和 scope limit 不会丢失，或者进入独立 scope report。
Stage 16D.1 inspector 缺少 smoke scope report 或 official runner report 时必须拒绝。
result loader 必须保留新增字段，静默丢弃 dataset / prediction / command / digest 字段时测试失败。
gold/no-op 输入 sha256 和 official command sha256 缺失时 official-complete 拒绝。
result JSONL 中 dataset / prediction / command opaque ref digest 与 sha256 不一致时拒绝。
缺少 per-instance execution image digest 时 official-complete 拒绝。
gold/noop executed result 缺少 official_result_ref 时 official-complete 拒绝。
official_result_ref digest 和 official_result_sha256 不一致时拒绝。
official_image_digest_locked=false 时 official-complete 拒绝。
删除 selected seed 的所有公开记录并同步调小 summary 后 inspector 仍拒绝。
gold failed 不能标成 trainable_candidate。
no-op unexpectedly resolved 不能标成 trainable_candidate。
runtime-private raw result 不能出现在公开 evidence。
risk seed no-op unexpectedly resolved 可以让 official-complete 表示执行完整，但不能增加 training_eligible_after_healthcheck_count。
```

远端或本机真实 official harness smoke 结束后还需要运行：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_stage16d_healthcheck_schema.py \
  tests/unit/test_stage16d_healthcheck_builder.py \
  tests/unit/test_stage16d_healthcheck_acceptance.py \
  tests/unit/test_pre_verl_swebench_official_inputs.py

PATH=.venv/bin:$PATH python -m compileall -q src scripts/pre_verl

git diff --check -- \
  docs/agentic_RL/repo_harness_verl_workstreams/40-stage-16d-1-execution-plan.md \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16d_1 \
  src/repo_harness/evaluation/stage16d_healthcheck.py \
  scripts/pre_verl \
  tests/unit
```

## 10. 需要记录的最终报告字段

`stage16d_acceptance_summary.json` 必须保留现有 Stage 16D inspector 兼容字段，不能把 `stage` 从
`16D` 改成 `stage16d_1`。Stage 16D.1 只能新增 scope 字段，不能替换现有字段。

兼容字段至少包括：

```text
stage = 16D
stage16d0_commit
stage16c_commit
seed_count
concrete_seed_count
aggregate_seed_count
official_harness_execution_status
official_healthcheck_complete
official_healthcheck_assert_complete_passed
gold_healthcheck_pass_count
gold_healthcheck_fail_count
noop_healthcheck_expected_unresolved_count
noop_unexpectedly_resolved_count
training_eligible_after_healthcheck_count
environment_or_oracle_invalid_count
public_path_leak_scan_passed
```

Stage 16D.1 扩展字段可以放在 summary、`stage16d_1_smoke_scope_report.json` 或
`stage16d_1_official_runner_report.json` 中，但必须可由 canonical evidence map 找到：

```text
stage16d1_smoke_scope = official_verifier_healthcheck_smoke
stage16d_commit
selected_seed_count
selected_concrete_seed_count
selected_positive_path_seed_count
selected_risk_seed_count
positive_path_gold_healthcheck_pass_count
positive_path_noop_expected_unresolved_count
stage16d1_positive_path_healthcheck_passed
stage16d1_risk_seed_classification_complete
official_image_digest_locked_count
official_image_digest_unlocked_count
dataset_name
dataset_split
dataset_revision_or_snapshot
selected_dataset_rows_ref
selected_dataset_rows_sha256
selected_instance_row_sha256_by_instance
gold_predictions_ref
gold_predictions_sha256
noop_predictions_ref
noop_predictions_sha256
official_command_ref
official_command_sha256
runtime_private_evidence_present
full_stage16d0_seed_coverage_claimed = false
remaining_stage16d0_seed_count_not_healthchecked
```

`stage16d_1_official_runner_report.json` 中至少应包含：

```text
runner_kind
runner_version
official_image_source
official_image_digest
official_image_digest_locked
runner_digest
runner_digest_method
execution_image_digest_by_instance
execution_image_source_by_instance
official_environment_digest_lock_method
selected_dataset_rows_ref
selected_dataset_rows_sha256
gold_predictions_ref
gold_predictions_sha256
noop_predictions_ref
noop_predictions_sha256
official_command_ref
official_command_sha256
docker_available
docker_version
max_workers
timeout_seconds
selected_instance_ids
gold_run_status
noop_run_status
raw_report_ref
raw_report_sha256
sanitized_command_log_ref
```

如果使用远端机器，还必须记录：

```text
remote_execution_backend
remote_instance_kind
remote_instance_final_status
raw_remote_paths_private_only = true
```

## 11. 提交范围

Stage 16D.1 计划或实现提交只能包含：

```text
docs/agentic_RL/repo_harness_verl_workstreams/40-stage-16d-1-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_1/*.json
必要的 Stage 16D builder / inspector 小修
必要的 Stage 16D.1 runner helper
Stage 16D.1 单元测试
sanitized public evidence，且仅在用户明确希望提交 evidence 时纳入
```

不能混入：

```text
runtime_private/
official raw report
official predictions JSONL 原文
gold patch 原文
no-op patch 原文
既有未跟踪 HTML
training_design 资料
平台凭证文档
pyrightconfig.json
```

## 12. 完成定义

Stage 16D.1 可以标记为通过，当且仅当：

```text
至少一个 selected positive-path concrete seed 有真实 gold/no-op official verifier 结果。
该 positive-path seed 的 gold patch resolved，no-op patch unresolved。
official command、dataset rows、gold predictions 和 no-op predictions 都有 runtime-private ref 与 sha256 绑定。
runner / harness digest 和 per-instance execution image digest 都已锁定。
official result raw artifact 有 runtime-private sha256 引用。
Stage 16D artifact builder 生成完整 evidence。
Stage 16D.1 scope report 和 official runner report 被 inspector 强制检查。
inspect-stage16d-healthcheck --assert-contract-complete 通过。
inspect-stage16d-healthcheck --assert-official-healthcheck-complete 通过。
公开 evidence 泄漏扫描通过。
单元测试和 compileall 通过。
Stage 16D.0 未覆盖 seed 仍明确标记为未 healthcheck，不能进入训练。
```

如果 official harness 暂时不可用，本阶段不能被视为完成。可以提交 blocked report 或继续修复 runner
环境，但不能把本地 contract 结果改名为 official-complete。
