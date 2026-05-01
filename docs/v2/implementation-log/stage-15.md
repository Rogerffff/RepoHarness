# Stage 15: finalize v2 acceptance docs

## 本阶段目标

本阶段目标是把第二版实现从分阶段完成状态收束成可复盘、可检查、可展示的最终验收状态。Stage 15 不新增核心 agent 能力，不扩大 Docker backend 范围，不新增训练算法；它只汇总既有稳定机器产物，补最终检查器和最终文档。

## 本阶段实现内容

- 新增全局验收模块 `repo_harness.v2_acceptance`：
  - `inspect-feedback-policy-coverage`
  - `build-v2-acceptance-report`
  - `inspect-v2-acceptance`
- 新增全局验收报告：
  - 汇总 V1 replay 回归。
  - 汇总 Stage 13 task set experiment。
  - 汇总 mock provider smoke。
  - 汇总 DeepSeek real provider smoke。
  - 汇总 Docker stage status。
  - 汇总 feedback policy coverage。
  - 汇总多个 exports root 下的 SFT、RL 和 preference audit。
- 新增正式文档：
  - `docs/v2/final-acceptance.md`
  - `docs/v2/walkthrough.md`
  - `docs/v2/implementation-log/README.md`
  - `docs/v2/developer-checklist.md`
  - `docs/v2/review/implementation/template.md`
- 新增 Stage 15 单元测试：
  - `tests/unit/test_v2_acceptance.py`

## 修改的主要文件

- `src/repo_harness/v2_acceptance.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v2_acceptance.py`
- `docs/v2/final-acceptance.md`
- `docs/v2/walkthrough.md`
- `docs/v2/implementation-log/README.md`
- `docs/v2/developer-checklist.md`
- `docs/v2/review/implementation/template.md`
- `docs/v2/implementation-log/stage-15.md`

## 生成的机器可读产物

- `runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json`
- `runs/v2-final-acceptance-20260501T223447Z-command.log`
- `runs/v2-final-task-set-20260501T223447Z/feedback_policy_report.json`

被最终验收报告引用的关键输入：

- `runs/v2-final-v1-regression-20260501T223447Z/batch_manifest.json`
- `runs/v2-final-mock-provider-20260501T223447Z/mock_provider_smoke_report.json`
- `runs/v2-final-task-set-20260501T223447Z/experiment_manifest.json`
- `runs/v2-final-task-set-20260501T223447Z/aggregate_metrics.json`
- `runs/v2-real-provider-smoke-20260501T214500Z/real_provider_smoke_report.json`
- `runs/v2-docker-stage-20260501T222345Z/docker_stage_status.json`

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v2_acceptance.py -q

RUN_ID=20260501T223447Z
V1_DIR="runs/v2-final-v1-regression-$RUN_ID"
MOCK_DIR="runs/v2-final-mock-provider-$RUN_ID"
TASK_SET_DIR="runs/v2-final-task-set-$RUN_ID"
FEEDBACK_POLICY_REPORT="$TASK_SET_DIR/feedback_policy_report.json"
DOCKER_STATUS_FILE="runs/v2-docker-stage-20260501T222345Z/docker_stage_status.json"
REAL_PROVIDER_REPORT="runs/v2-real-provider-smoke-20260501T214500Z/real_provider_smoke_report.json"
ACCEPTANCE_REPORT="runs/v2-final-acceptance-$RUN_ID/v2_acceptance_report.json"

PATH=.venv/bin:$PATH repo-harness run-batch --config tests/fixtures/run_configs/batch_replay.yaml --output-dir "$V1_DIR"
PATH=.venv/bin:$PATH repo-harness export "$V1_DIR" --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export "$V1_DIR" --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness export "$V1_DIR" --format preference_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export "$V1_DIR/exports" --all --assert-clean

PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/v2/mock_provider_smoke.yaml --output-dir "$MOCK_DIR"
PATH=.venv/bin:$PATH repo-harness export "$MOCK_DIR" --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export "$MOCK_DIR" --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export "$MOCK_DIR/exports" --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-mock-provider-smoke --run-dir "$MOCK_DIR" --output "$MOCK_DIR/mock_provider_smoke_report.json" --assert-accepted --assert-export-clean

PATH=.venv/bin:$PATH repo-harness run-experiment --config tests/fixtures/run_configs/v2/replay_experiment.yaml --output-dir "$TASK_SET_DIR"
PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format preference_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --format sft_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --format rl_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-experiment "$TASK_SET_DIR" --assert-minimums tests/fixtures/run_configs/v2/task_set_thresholds.yaml
PATH=.venv/bin:$PATH repo-harness inspect-feedback-policy-coverage --experiment-dir "$TASK_SET_DIR" --output "$FEEDBACK_POLICY_REPORT" --assert-complete

PATH=.venv/bin:$PATH repo-harness inspect-real-provider-smoke --report "$REAL_PROVIDER_REPORT" --allow-skip-without-credentials --require-accepted-with-credentials
PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file "$DOCKER_STATUS_FILE" --assert-stage-complete
PATH=.venv/bin:$PATH repo-harness build-v2-acceptance-report --v1-regression-dir "$V1_DIR" --task-set-manifest "$TASK_SET_DIR/experiment_manifest.json" --mock-provider-report "$MOCK_DIR/mock_provider_smoke_report.json" --real-provider-report "$REAL_PROVIDER_REPORT" --feedback-policy-report "$FEEDBACK_POLICY_REPORT" --export-audit-root "$V1_DIR/exports" --export-audit-root "$MOCK_DIR/exports" --export-audit-root "$TASK_SET_DIR/exports" --docker-status "$DOCKER_STATUS_FILE" --output "$ACCEPTANCE_REPORT"
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance "$ACCEPTANCE_REPORT" --assert-complete
```

提交前还会运行：

```bash
PATH=.venv/bin:$PATH python -m pytest -q
git status --short
git diff --check
git diff --cached --check
```

## 验证结果

- `python -m compileall src` 通过。
- `tests/unit/test_v2_acceptance.py` 通过，8 个测试通过。
- `inspect-v2-acceptance --assert-complete` 通过。
- 全量测试通过，352 个测试通过。
- final task set：20 个任务，18 个 success，2 个 structured skipped。
- mock provider：accepted。
- real provider：DeepSeek primary accepted。
- Docker stage：`interface_only` passed。
- export audit：SFT、RL 和 preference audit 均存在并 clean。

## 正例证据

- `v2_acceptance_report.json` 引用所有关键输入文件，并记录 sha256。
- `inspect-v2-acceptance` 会校验引用文件存在且 sha256 匹配。
- `inspect-v2-acceptance` 会要求必需 evidence refs 全部存在。
- `inspect-v2-acceptance` 会重新读取引用源文件，并校验 report 摘要和源文件事实一致。
- `inspect-v2-acceptance` 会拒绝 OpenAI fallback 伪装成 DeepSeek primary accepted。
- `inspect-v2-acceptance` 会拒绝无凭证 accepted 伪装。
- `inspect-v2-acceptance` 会拒绝 Docker summary 和 `docker_stage_status.json` 不一致。
- `inspect-v2-acceptance` 会扫描正式训练 JSONL，拒绝 provider raw markers。
- `inspect-v2-acceptance` 会在 inspect 阶段重新检查正式训练 JSONL，拒绝非 trainable 样本进入正式训练数据。
- feedback policy report 覆盖四种 `test_feedback_policy` 和三种 `feedback_tests_passed_policy`。
- Docker stage 使用 `inspect-workspace-backend --assert-stage-complete` 作为最终验收输入。

## 负例证据

- 本阶段没有新增 Docker backend，也没有把 Stage 14 `interface_only` 写成 Docker backend 已完成。
- 本阶段没有重新运行 verifier 或改写已有 run facts；acceptance builder 只读取已有 run directory、report 和 export audit。
- 本阶段没有把 provider raw response、raw request body 或 reasoning summary 放入训练 payload。
- 本阶段没有把无凭证 skip 记成真实 provider accepted。

## 允许降级项

- Docker backend 继续采用 `interface_only`。
- Preference export 在单 rollout task set 中 skipped。
- feedback policy coverage report 记录测试证据和样例字段，不内嵌完整 pytest XML 或 JSON report。

## 禁止降级项

- 不能让 `inspect-v2-acceptance --assert-complete` 接受缺失关键引用或 sha256 不匹配。
- 不能把 OpenAI fallback 成功伪装成 DeepSeek primary 成功。
- 不能把无凭证 skip 伪装成真实 provider accepted。
- 不能让 provider raw response 进入训练 payload。
- 不能让非 trainable 样本进入正式训练 JSONL。

## 已知限制

- 任务集多样性仍然有限，后续应增加更多 repository-level task 类型。
- Docker backend 后续实现时需要新增独立验收证据，而不是复用当前 `interface_only` status。
- 当前最终验收使用 Stage 11 已生成的 DeepSeek accepted smoke report，避免重复真实模型调用。

## 是否偏离设计文档

未发现需要记录的设计冲突。Stage 15 按计划新增全局 acceptance report 和检查器，并保持最终验收与 Stage 13 task-set 阈值检查分离。

## sub agent 审查结论

已安排只读 sub agent 审查。审查 agent 没有修改文件。

审查发现：

- P1：发现 3 个，均已修复。
  - 必需 evidence refs 缺失时初始检查器没有拒绝。修复后，`inspect-v2-acceptance --assert-complete` 要求所有关键引用存在并校验 sha256。
  - `accepted_with_credentials` 初始检查没有要求凭证事实。修复后，DeepSeek accepted 和 OpenAI fallback success 都必须有 `credential_status=present`、redacted credential source、accepted final verifier 和 success run outcome。
  - Docker stage 初始检查没有比对 report 摘要和 `docker_stage_status.json`。修复后，Docker stage summary 必须和 status file 逐字段一致。
- P2：发现 2 个，均已修复。
  - 初始检查器过度信任 report 内部摘要。修复后，inspect 会重新读取 referenced manifest、provider report、feedback report、Docker status 和 export roots。
  - provider raw marker 和非 trainable formal JSONL 初始检查主要是 build-time snapshot。修复后，inspect 阶段会重新扫描 export roots。
- P3：Stage 15 负例测试不足。已补充至 8 个单元测试，覆盖 missing evidence ref、accepted without credentials、Docker summary mismatch、inspect-time provider raw marker 和 non-trainable formal JSONL。

审查记录保存到 `docs/v2/review/implementation/stage-15-review.md`。

## 是否可以完成第二版

等待全量回归验证完成后即可提交 Stage 15。
