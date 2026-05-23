# Stage 16D 执行计划：official verifier / gold patch / no-op healthcheck

本文是 Stage 16D 的具体执行计划。它承接
[post_stage15_training_infra_stage_plan.md](../training_design/post_stage15_training_infra_stage_plan.md)
中的 Stage 16D 高层路线，并且建立在下面几个前置阶段已经完成的基础上：

```text
Stage 16A：安全最小 execute_bash 工具面
Stage 16B：diagnostic_shell 生命周期和 Docker persistent session
Stage 16B.5：远端 Docker-capable 训练执行后端验证
Stage 16C：公开环境入口和模型行为提示
Stage 16D.0：跨 worktree verifier / harness 状态同步
```

Stage 16D 的核心目标是把“这个任务的验证环境是否可信”变成机器可读、可复现、可进入
Stage 17 任务注册表的数据。具体来说，Stage 16D 要实际运行或结构化接入下面三类检查：

```text
gold patch healthcheck：正确补丁应该被官方验证器判定为通过。
no-op / empty patch healthcheck：空补丁或无效补丁应该被官方验证器判定为失败。
proxy / official disagreement check：内部 verifier、proxy reward 和 official verifier 的结论差异必须被分类。
```

Stage 16D 不是模型训练阶段，也不是大规模 SWE-bench 评测阶段。它只建立小规模、强审计的
official verifier 健康检查门槛，避免后续把 verifier 环境坏、oracle 无区分力、no-op 异常通过
或内部 verifier 漂移误当成模型能力信号。

## 1. 阶段目标

Stage 16D 必须完成下面几件事：

1. 消费 Stage 16D.0 生成的 seed manifest 和同步报告，不重新从两个 worktree 的历史中人工拼输入。
2. 新增 official verifier healthcheck 的结构化 schema、分类规则和 evidence builder。
3. 对每个 concrete seed 至少记录：

   ```text
   official_image_source
   official_image_digest_locked
   local_rebuild_environment
   gold_healthcheck_backend
   noop_healthcheck_backend
   remote_image_correction_applied
   proxy_validation_backend
   proxy_official_disagreement
   healthcheck_training_disposition
   ```

4. 建立 gold patch / no-op 的训练资格门槛：
   - gold patch 不通过的任务不能作为模型失败样本进入训练。
   - no-op / empty patch 异常通过的任务不能作为模型成功样本或模型失败样本进入训练。
   - official harness 不可运行、镜像 digest 漂移或环境不健康的任务只能进入诊断侧通道。
5. 区分下面几类验证结果：

   ```text
   verifier_healthy
   gold_healthcheck_failed
   noop_unexpectedly_resolved
   official_environment_unhealthy
   official_image_digest_mismatch
   proxy_official_disagreement
   healthcheck_not_run
   aggregate_seed_not_runnable
   ```

6. 新增机器验收命令或等价 inspector，能拒绝：
   - 缺少 gold / no-op 结果的 concrete seed；
   - 把 aggregate seed 伪装成 concrete healthcheck 结果；
   - 公开 evidence 泄漏 gold patch 原文、test patch 原文、hidden selector、本机绝对路径或 runtime-private 路径；
   - 把 `environment_or_oracle_invalid` 样本标成训练可用。
7. 生成 Stage 16D 本地 evidence 目录。第一版允许只在本地构造和验证 schema / 分类逻辑；真正运行 official harness 的部分可以由 remote Docker-capable 后端执行，但 evidence 格式必须先固定。

## 2. 非目标

Stage 16D 不做下面这些事情：

- 不训练模型。
- 不扩大 Stage 16A 的 `execute_bash` 权限。
- 不扩大 Stage 16B 的 `diagnostic_shell` 权限。
- 不修改 Stage 16C 的公开提示词主路径。
- 不实现 Stage 16E 的 patch hygiene 最终训练目标清洁度；Stage 16D 只消费和记录 final patch / official prediction hygiene 事实。
- 不执行 20 到 30 题代表性 harness 诊断扩展；它属于 Stage 16.5。
- 不把 Stage 16D.0 的 aggregate seed 直接当成已经 healthcheck 通过的任务。
- 不把 official verifier 的隐藏 selector、gold patch、test patch 或 official result 放进模型可见 prompt、TrainingView、AgentLoopOutput、DataProto 或训练导出样本。

## 3. 前置条件

进入 Stage 16D 前必须满足：

```text
Stage 16C 提交存在。
Stage 16D.0 提交存在，当前基线至少包含 69da8353。
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/stage16d_seed_task_manifest.json 存在且可解析。
scripts/pre_verl/build_swebench_official_inputs.py 已有内容级泄漏扫描。
tests/unit/test_pre_verl_swebench_official_inputs.py 通过。
```

如果当前工作区仍有 Stage 16D.0 未提交文件，Stage 16D 实施必须停止，先整理 Stage 16D.0。Stage 16D 的提交不能混入既有未跟踪 HTML、训练设计资料、平台凭证文档或其它与 healthcheck 无关的文件。

## 4. 输入与输出

### 4.1 输入文件

Stage 16D 第一版必须消费下面这些文件：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/stage16d_seed_task_manifest.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/stage16d_gold_patch_source_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/stage16d_noop_patch_source_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/stage16d_sync_regression_report.json
```

如果实际运行 official harness，还需要 runtime-private 输入：

```text
SWE-bench Verified dataset rows
gold patch source 或 opaque gold patch ref
empty patch / marker no-op patch
official harness image 或 official harness runner
official image digest / resolved image metadata
official predictions JSONL
official result JSON / report directory
```

这些 runtime-private 输入不能直接提交为公开 evidence。公开 evidence 只能包含 sha256、opaque ref、任务标识、分类结果和聚合统计。

### 4.2 输出文件

建议新增 Stage 16D 本地 evidence 目录：

```text
runs/repo-harness-verl-stage16d-<timestamp>/
```

公开可提交 evidence 最小文件清单：

```text
stage16d_acceptance_summary.json
stage16d_healthcheck_manifest.json
stage16d_seed_resolution_report.json
stage16d_gold_healthcheck_report.json
stage16d_noop_healthcheck_report.json
stage16d_proxy_official_disagreement_report.json
stage16d_training_disposition_report.json
stage16d_public_leak_scan_report.json
stage16d_command_log.sanitized.jsonl
stage16d_canonical_evidence_map.json
```

本地或远端私有 evidence 可以保存在同一运行目录的 `runtime_private/` 子目录中，但不能提交到
公开 Git 历史，也不能出现在公开 manifest 的可传播字段里：

```text
runtime_private/stage16d_command_log.raw.jsonl
runtime_private/stage16d_official_runner_manifest.json
runtime_private/stage16d_official_report.raw.json
runtime_private/stage16d_gold_patch_inputs/
runtime_private/stage16d_noop_patch_inputs/
```

如果第一版只实现本地 schema / classification / inspector，不实际运行 official harness，必须在 summary 中明确：

```text
official_harness_execution_status = not_run_in_local_schema_phase
stage16d_complete = false
local_contract_ready = true
remote_healthcheck_required = true
```

不能把本地 schema 通过冒充成 official healthcheck 通过。

## 5. Healthcheck 语义

### 5.1 Gold patch healthcheck

gold patch healthcheck 的含义是：在 official harness 或等价官方验证环境中，应用该任务的正确补丁后，验证结果应为 resolved。

结构化结果建议：

```json
{
  "instance_id": "django__django-17029",
  "check_kind": "gold_patch",
  "healthcheck_backend": "swebench_official_harness",
  "official_image_digest": "sha256:<digest-or-opaque>",
  "patch_ref": "runtime-private:gold-patch:<sha256>",
  "patch_content_public": false,
  "status": "passed",
  "official_resolved": true,
  "failure_reason": null
}
```

如果 gold patch 不通过，则任务必须分类为：

```text
healthcheck_status = gold_healthcheck_failed
healthcheck_training_disposition = environment_or_oracle_invalid
invalid_for_training = true
invalid_for_online_rl = true
```

它不能被解释为“模型失败”，因为此时连正确补丁都无法通过验证。

### 5.2 No-op / empty patch healthcheck

no-op healthcheck 的含义是：在 official harness 或等价官方验证环境中，不应用有效修复时，验证结果应为 unresolved。

允许的 no-op 输入：

```text
empty patch
只包含无效 marker 的空语义 patch
Stage 16D.0 中记录的 no-op opaque ref
```

no-op patch 的内容也不能公开提交。公开报告只记录 sha256、大小、生成方式和分类。

Stage 16D.0 的 seed manifest 中，多个 concrete seed 的 `noop_patch_source` 可能是 `not_available`。
Stage 16D builder 不能把这个状态解释为 no-op 不适用。对所有 SWE-Bench-like concrete seed，builder
必须执行下面的规则：

```text
如果 seed manifest 已有 no-op opaque ref，则使用该 ref。
如果 seed manifest 没有 no-op source，则生成 canonical empty patch 或 canonical marker no-op patch ref。
如果无法生成 canonical no-op ref，则记录 noop_patch_ref_status=not_run_missing_noop_input。
not_run_missing_noop_input 必须导致 healthcheck_training_disposition=diagnostic_only。
```

也就是说，Stage 16D 第一版不允许 concrete SWE-Bench-like seed 因为 `noop_patch_source=not_available`
而跳过 no-op 健康检查后仍进入训练候选。

如果 no-op / empty patch 被 official harness 判定 resolved，则任务必须分类为：

```text
healthcheck_status = noop_unexpectedly_resolved
healthcheck_training_disposition = environment_or_oracle_invalid
invalid_for_training = true
invalid_for_online_rl = true
```

像 `django__django-10097` 这类已知 no-op 风险 seed 必须重点覆盖。它不能作为模型成功样本，也不能作为可信模型失败样本进入训练。

### 5.3 Proxy / official disagreement

Stage 16D 必须把下面几类结论分开记录：

```text
internal_final_verifier_status
proxy_reward_status
official_verifier_status
gold_healthcheck_status
noop_healthcheck_status
```

如果内部 verifier 接受而 official verifier 拒绝，或者内部 verifier 拒绝而 official verifier 接受，必须记录：

```text
proxy_official_disagreement = true
disagreement_type = internal_accept_official_reject | internal_reject_official_accept | reward_official_mismatch
training_disposition = diagnostic_only_until_reviewed
```

第一版不要求自动修复 disagreement，但不能把 disagreement 样本静默放进训练。

### 5.4 内部 final verifier 边界和跳过控制流

高层计划已经明确：Stage 16D 不能只看最终 `status=succeeded` 或 reward 分数，还必须能解释内部
final verifier 是否真的执行，以及它和 official verifier 的关系。因此 Stage 16D 的 evidence 必须记录：

```text
final_verifier_boundary_ref
final_verifier_boundary_available
internal_final_verifier_reran
evaluation_rerun_final_verifier
final_verifier_skip_reason
internal_final_verifier_status_source
```

如果 `evaluation.rerun_final_verifier=false`，或者缺少 `final_verifier_boundary.json`，该 run 不能被用来证明
内部 verifier 接受或拒绝。它仍然可以作为 official harness healthcheck 的输入背景，但必须记录：

```text
internal_final_verifier_status_source = unavailable_or_skipped
proxy_validation_backend = not_trusted_for_healthcheck
training_disposition = diagnostic_only_until_official_healthcheck
```

这条规则防止执行 agent 把“没有 rerun final verifier”误解释为“final verifier 已经和 official verifier 一致”。

## 6. Seed 处理规则

Stage 16D.0 的 seed manifest 中有两类输入：

```text
concrete seed：有具体 instance_id，可以运行 healthcheck。
aggregate seed：例如 repr20-gold-smoke-aggregate，只是历史聚合证据，不能直接运行。
```

Stage 16D 必须对 aggregate seed fail closed：

```text
seed_resolution_status = aggregate_not_directly_runnable
healthcheck_status = not_run
training_disposition = diagnostic_only
```

如果执行 agent 希望使用 aggregate seed，必须先展开成具体 instance 列表，并生成新的 seed resolution evidence。不能把 aggregate 记录直接写成 healthcheck passed。

对 concrete seed，第一版至少覆盖：

```text
django__django-10097
psf__requests-2317
psf__requests-1766
django__django-16502
sphinx-doc__sphinx-8638
django__django-17029
sphinx-doc__sphinx-9591
matplotlib__matplotlib-25122
```

如果某个 seed 缺少 dataset row、gold patch ref 或 official harness 运行条件，必须记录结构化状态，例如：

```text
seed_materialization_status = missing_dataset_row
gold_patch_ref_status = unavailable
official_harness_execution_status = not_run_missing_input
training_disposition = diagnostic_only
```

不能用空结果填充为通过。

## 7. 公开和私有 evidence 分层

### 7.1 公开 evidence 允许内容

公开 evidence 可以包含：

```text
instance_id
seed_role
source_dataset
healthcheck_status
training_disposition
official_image_digest_locked
gold_patch_sha256
noop_patch_sha256
official_result_sha256
aggregate counts
opaque runtime-private refs
```

opaque runtime-private ref 必须使用固定格式，不能用真实相对路径伪装：

```text
runtime-private:<artifact-kind>:<sha256>
```

例如：

```text
runtime-private:gold-patch:sha256-...
runtime-private:official-report:sha256-...
```

公开报告中不能出现 `runtime_private/...`、`runs/...`、Docker mount path 或本机文件路径。

### 7.2 公开 evidence 禁止内容

公开 evidence 不能包含：

```text
gold patch 原文
test patch 原文
hidden verifier 原文
FAIL_TO_PASS selector
PASS_TO_PASS selector
官方测试 selector
official harness 逐条隐藏测试输出
runtime_private 路径
本机绝对路径
Docker mount 真实宿主路径
official report directory 真实绝对路径
```

公开扫描至少覆盖：

```text
Markdown
JSON
JSONL
log
shell script
manifest
```

允许出现在字段名或风险枚举中的词必须登记 allowlisted context，例如：

```text
gold_patch_source
noop_oracle_risk
candidate_oracle_noop_resolved
gold_healthcheck_failed
```

但这些 allowlist 不能允许 patch 原文、selector 原文或 diff hunk 原文进入公开文件。

## 8. 建议实现步骤

### Step 1：新增 Stage 16D healthcheck schema

建议新增：

```text
src/repo_harness/evaluation/stage16d_healthcheck.py
```

第一版包含纯 Python schema 和分类 helper，不依赖 Docker、SWE-bench、torch、ray 或 verl。

建议模型：

```python
class Stage16DHealthcheckRecord(BaseModel):
    instance_id: str
    seed_role: str
    seed_resolution_status: str
    official_validation_backend: str
    official_image_source: str | None
    official_image_digest_locked: bool
    official_image_digest: str | None
    gold_healthcheck_status: str
    noop_healthcheck_status: str
    proxy_official_disagreement: bool
    healthcheck_training_disposition: str
    invalid_for_training: bool
    invalid_for_online_rl: bool
```

字段归属必须固定，避免不同报告用相近字段表达不同语义：

```text
gold_healthcheck_status：只描述 gold patch healthcheck 的执行和 official resolved 结果。
noop_healthcheck_status：只描述 no-op / empty patch healthcheck 的执行和 official unresolved 结果。
overall_healthcheck_status：汇总 gold、no-op、official image、seed resolution 和 proxy disagreement 后的总状态。
healthcheck_training_disposition：Stage 16D 对训练资格的最终分类。
```

`training_disposition` 可以作为旧报告兼容别名，但新 schema、builder、inspector 和 acceptance summary
必须使用 `healthcheck_training_disposition`。

分类 helper 至少包含：

```text
classify_gold_healthcheck(...)
classify_noop_healthcheck(...)
classify_proxy_official_disagreement(...)
compute_stage16d_training_disposition(...)
validate_stage16d_public_evidence(...)
```

### Step 2：新增 healthcheck artifact builder

建议新增：

```text
scripts/pre_verl/build_stage16d_healthcheck_artifacts.py
```

它第一版可以接收：

```text
--seed-manifest
--gold-results-jsonl
--noop-results-jsonl
--proxy-results-jsonl
--output-dir
```

其中 results JSONL 可以来自真实 official harness，也可以来自测试 fixture。builder 负责输出统一的 Stage 16D evidence。

必须实现：

```text
aggregate seed 拒绝直接当作已运行 healthcheck
concrete seed 缺少结果时记录 not_run，而不是伪造通过
gold fail -> environment_or_oracle_invalid
noop resolved -> environment_or_oracle_invalid
proxy / official disagreement -> diagnostic_only_until_reviewed
公开 evidence path leak scan
runtime-private artifact refs
```

### Step 3：新增 inspector

建议新增 CLI 命令或脚本：

```text
repo-harness inspect-stage16d-healthcheck <stage16d_acceptance_summary.json> --assert-contract-complete
repo-harness inspect-stage16d-healthcheck <stage16d_acceptance_summary.json> --assert-official-healthcheck-complete
```

如果短期不接 CLI，也可以先新增脚本：

```text
scripts/pre_verl/inspect_stage16d_healthcheck.py
```

第一版建议把 inspector 明确拆成两个验收模式：

```text
--assert-contract-complete
--assert-official-healthcheck-complete
```

`--assert-contract-complete` 用于本地 schema、builder、分类规则和公开泄漏扫描完整性。它可以接受
结构化 `not_run_*`，但必须要求这些 not-run 结果被标成诊断侧通道，不能标成训练可用。

`--assert-official-healthcheck-complete` 用于真实 official harness 健康检查完成。它不能接受训练候选
concrete seed 只有 `not_run_*` 原因；所有训练候选 concrete seed 都必须有真实 gold 和 no-op official
结果。

两种模式必须区分下面两种情况：

```text
missing_healthcheck_record：
  缺少 gold 或 no-op 的记录对象。contract 模式和 official 模式都必须拒绝。

structured_not_run_healthcheck_record：
  有完整记录对象，状态为 not_run_*，且 healthcheck_training_disposition=diagnostic_only 或
  environment_or_oracle_invalid。contract 模式可以接受；official 模式不能把它计入训练候选完整通过。
```

两个模式下都必须拒绝：

```text
concrete seed 缺少 gold healthcheck 或 no-op healthcheck
gold_healthcheck_failed 被标成训练可用
noop_unexpectedly_resolved 被标成训练可用
已声称执行 official harness，但 official_image_digest_locked != true
official healthcheck complete 模式下 official_image_digest_locked != true
contract 模式中 official_harness_execution_status 为 not_run_*，但相关 seed 被标成 trainable_candidate
公开 evidence 泄漏 forbidden marker
aggregate seed 被标成 healthcheck passed
proxy_official_disagreement 样本被标成直接训练可用
runtime-private raw artifact 出现在公开 manifest 中
```

公开泄漏扫描必须覆盖下面这些具体公开文件，而不只是按扩展名粗略扫描：

```text
stage16d_acceptance_summary.json
stage16d_healthcheck_manifest.json
stage16d_seed_resolution_report.json
stage16d_gold_healthcheck_report.json
stage16d_noop_healthcheck_report.json
stage16d_proxy_official_disagreement_report.json
stage16d_training_disposition_report.json
stage16d_public_leak_scan_report.json
stage16d_command_log.sanitized.jsonl
stage16d_canonical_evidence_map.json
```

### Step 4：official harness 运行封装

如果本阶段执行真实 official harness，建议新增 runtime-private runner：

```text
scripts/pre_verl/run_stage16d_official_healthcheck.py
```

它必须：

```text
读取具体 seed 列表。
构造 gold prediction 和 no-op prediction。
运行 official SWE-bench harness 或等价官方验证入口。
锁定 official image digest 或记录无法锁定的结构化失败。
把 raw official output 写入 runtime_private。
只把 sanitized summary 写入公开 evidence。
```

如果本机没有 Docker 或 official harness 不可用，不应伪造运行结果。应输出：

```text
official_harness_execution_status = not_run_environment_unavailable
stage16d_complete = false
remote_healthcheck_required = true
```

### Step 5：生成本地 evidence

本地 evidence 至少证明：

```text
schema 可生成。
分类规则正确。
公开扫描有效。
aggregate seed 不能冒充通过。
training disposition fail closed。
```

真正的 official harness 运行可以在 Stage 16D 的远端 Docker-capable 环境中补跑。补跑后再把 sanitized summary 和 sha256 回填。

## 9. 测试计划

### 9.1 新增测试

建议新增：

```text
tests/unit/test_stage16d_healthcheck_schema.py
tests/unit/test_stage16d_healthcheck_builder.py
tests/unit/test_stage16d_healthcheck_acceptance.py
```

覆盖：

```text
gold patch passed + no-op expected_unresolved -> verifier_healthy + training eligible
gold patch failed -> environment_or_oracle_invalid + not trainable
no-op resolved -> environment_or_oracle_invalid + not trainable
proxy official disagreement -> diagnostic_only_until_reviewed
aggregate seed -> not directly runnable
concrete seed missing result -> not_run_missing_input
official image digest missing -> not complete
public evidence containing hidden selector -> rejected
public evidence containing patch diff hunk -> rejected
public evidence containing local absolute path -> rejected
runtime-private refs allowed only as opaque refs
```

其中 `stage16d_acceptance_summary.json`、`stage16d_healthcheck_manifest.json`、所有公开报告和
`stage16d_command_log.sanitized.jsonl` 都必须进入公开泄漏扫描范围。

### 9.2 前置回归

Stage 16D 实施完成后至少运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PATH=.venv/bin:$PATH python -m pytest -q -p no:cacheprovider \
  tests/unit/test_pre_verl_swebench_official_inputs.py \
  tests/unit/test_repo_harness_stage16c_public_environment_context.py \
  tests/unit/test_repo_harness_stage16c_public_test_entry.py \
  tests/unit/test_repo_harness_stage16c_visibility.py \
  tests/unit/test_repo_harness_stage16b_diagnostic_shell_tool.py \
  tests/unit/test_repo_harness_stage16a_execute_bash.py \
  tests/unit/test_task_adapter.py \
  tests/unit/test_task_schema.py
```

如果新增 Stage 16D 测试，则合并运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PATH=.venv/bin:$PATH python -m pytest -q -p no:cacheprovider \
  tests/unit/test_stage16d_healthcheck_schema.py \
  tests/unit/test_stage16d_healthcheck_builder.py \
  tests/unit/test_stage16d_healthcheck_acceptance.py
```

还必须运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PATH=.venv/bin:$PATH python -m compileall -q src scripts/pre_verl
git diff --check -- \
  src/repo_harness/evaluation \
  scripts/pre_verl \
  tests/unit \
  docs/agentic_RL/repo_harness_verl_workstreams/39-stage-16d-execution-plan.md
```

### 9.3 远端或 Docker official harness 验证

如果执行真实 official harness，必须记录：

```text
docker_version
official_image_source
official_image_digest
official_harness_commit_or_version
dataset_sha256
predictions_sha256
official_report_sha256
raw_report_runtime_private_ref
```

如果没有执行真实 official harness，则 Stage 16D 只能标记为：

```text
local_contract_ready
remote_healthcheck_required
```

不能标记为：

```text
official_healthcheck_complete
```

## 10. Acceptance summary 最小字段

`stage16d_acceptance_summary.json` 至少包含：

```json
{
  "schema_version": "repo_harness_stage16d_acceptance_summary_v0",
  "stage": "16D",
  "stage16d0_commit": "69da8353",
  "stage16c_commit": "4711573c",
  "stage16d_complete": false,
  "local_contract_ready": true,
  "official_healthcheck_complete": false,
  "official_harness_execution_status": "not_run_in_local_schema_phase",
  "remote_healthcheck_required": true,
  "contract_assert_complete_passed": true,
  "official_healthcheck_assert_complete_passed": false,
  "seed_count": 9,
  "concrete_seed_count": 8,
  "aggregate_seed_count": 1,
  "gold_healthcheck_pass_count": 0,
  "gold_healthcheck_fail_count": 0,
  "noop_healthcheck_expected_unresolved_count": 0,
  "noop_unexpectedly_resolved_count": 0,
  "environment_or_oracle_invalid_count": 0,
  "proxy_official_disagreement_count": 0,
  "training_eligible_after_healthcheck_count": 0,
  "public_path_leak_scan_passed": true,
  "hidden_selector_leak_scan_passed": true,
  "patch_content_public_leak_scan_passed": true,
  "runtime_private_evidence_present": true
}
```

真实 official harness 跑完后，应把 `official_healthcheck_complete` 改为 `true`，并填入真实计数。

## 11. 训练资格规则

只有满足下面条件的任务才能进入 Stage 17 task registry 的训练候选：

```text
seed_resolution_status = concrete
official_image_digest_locked = true
gold_healthcheck_status = passed
noop_healthcheck_status = expected_unresolved
proxy_official_disagreement = false
healthcheck_training_disposition = trainable_candidate
public_leak_scan_passed = true
runtime_private_raw_artifact_not_public = true
```

如果未来出现非 SWE-Bench-like 任务，确实没有 no-op / empty patch 概念，必须在后续阶段单独设计
`noop_not_applicable_with_reviewed_reason`。Stage 16D 第一版面向 SWE-Bench Verified 风格任务，不能把
no-op 未运行、no-op 不可用或 no-op 缺失直接当作训练可用。

下面情况必须默认排除出训练分母：

```text
aggregate seed 未展开
gold patch healthcheck failed
no-op / empty patch unexpectedly resolved
no-op / empty patch healthcheck missing
official harness unavailable
official image digest not locked
proxy / official disagreement 未复核
公开 evidence 泄漏 hidden selector / patch content / local path
```

排除不等于删除。所有排除样本必须保留诊断记录，用于 Stage 16.5 和 Stage 17 的 denominator policy。

## 12. 提交边界

Stage 16D 实施提交应只包含：

```text
docs/agentic_RL/repo_harness_verl_workstreams/39-stage-16d-execution-plan.md
src/repo_harness/evaluation/stage16d_healthcheck.py 或等价模块
scripts/pre_verl/build_stage16d_healthcheck_artifacts.py
scripts/pre_verl/inspect_stage16d_healthcheck.py 或 CLI 接入
tests/unit/test_stage16d_healthcheck_*.py
runs/repo-harness-verl-stage16d-<timestamp>/ 中可公开提交的 sanitized evidence
```

不要混入：

```text
既有未跟踪 HTML
training_design 草稿资料
平台 CLI 凭证文档
runtime-private raw official harness 输出
gold patch 原文
test patch 原文
```

如果生成 runtime-private 证据，只能保留在本地或远端工作目录，不应随公开提交进入 Git。

## 13. 出口条件

Stage 16D 本地 contract 阶段通过条件：

```text
Stage 16D schema / builder / inspector 测试通过。
Stage 16D.0 seed manifest 能被解析和分类。
aggregate seed 不能被标成通过。
gold fail、no-op resolved、proxy disagreement 全部 fail closed。
公开 evidence 泄漏扫描通过。
Stage 16A / 16B / 16C / official input builder 关键回归通过。
```

Stage 16D official healthcheck 完整通过条件：

```text
所有训练候选 concrete seed 都有真实 official gold / no-op healthcheck 结果。
所有 not-run concrete seed 都被归入 diagnostic_only 或 environment_or_oracle_invalid，不能计入 official healthcheck complete 的训练候选分子。
official image digest 已锁定。
gold patch 通过率和 no-op expected_unresolved 率被记录。
environment_or_oracle_invalid 样本被排除出训练分母。
proxy / official disagreement 被记录并默认排除训练。
stage16d_acceptance_summary.json 同时通过 inspector --assert-contract-complete 和 --assert-official-healthcheck-complete。
```

只有 Stage 16D official healthcheck 完整通过后，Stage 17 才能把这些任务纳入正式训练任务注册表候选。
