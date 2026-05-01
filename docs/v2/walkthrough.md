# RepoHarness V2 Walkthrough

## 目标

这个 walkthrough 展示如何复现第二版最终验收的核心路径。它假设当前工作目录是仓库根目录：

```bash
cd /Users/roger/Desktop/claude-code
```

所有命令都使用本地虚拟环境：

```bash
PATH=.venv/bin:$PATH
```

## 1. 基础验证

先确认代码可以编译并通过测试：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

## 2. 运行 replay task set

```bash
TASK_SET_DIR=runs/v2-final-task-set-20260501T223447Z

PATH=.venv/bin:$PATH repo-harness run-experiment \
  --config tests/fixtures/run_configs/v2/replay_experiment.yaml \
  --output-dir "$TASK_SET_DIR"

PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness export "$TASK_SET_DIR" --format preference_jsonl

PATH=.venv/bin:$PATH repo-harness inspect-export "$TASK_SET_DIR/exports" --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-experiment "$TASK_SET_DIR" \
  --assert-minimums tests/fixtures/run_configs/v2/task_set_thresholds.yaml
```

预期结果：

- 20 个 task。
- 18 个 success。
- 2 个 structured skipped/invalid。
- SFT 和 RL 有 trainable 样本。
- Preference export 因 pair 不足结构化 skipped。

## 3. 运行 mock provider smoke

```bash
MOCK_DIR=runs/v2-final-mock-provider-20260501T223447Z

PATH=.venv/bin:$PATH repo-harness run-task \
  tests/fixtures/tasks/task_001.yaml \
  --config tests/fixtures/run_configs/v2/mock_provider_smoke.yaml \
  --output-dir "$MOCK_DIR"

PATH=.venv/bin:$PATH repo-harness export "$MOCK_DIR" --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export "$MOCK_DIR" --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export "$MOCK_DIR/exports" --all --assert-clean

PATH=.venv/bin:$PATH repo-harness inspect-mock-provider-smoke \
  --run-dir "$MOCK_DIR" \
  --output "$MOCK_DIR/mock_provider_smoke_report.json" \
  --assert-accepted \
  --assert-export-clean
```

预期结果：

- mock provider run accepted。
- final verifier accepted。
- raw mock provider artifacts 已脱敏。
- SFT 和 RL export audit clean。

## 4. 检查 real provider smoke

最终验收使用这个已生成的 DeepSeek accepted report：

```bash
REAL_PROVIDER_REPORT=runs/v2-real-provider-smoke-20260501T214500Z/real_provider_smoke_report.json

PATH=.venv/bin:$PATH repo-harness inspect-real-provider-smoke \
  --report "$REAL_PROVIDER_REPORT" \
  --allow-skip-without-credentials \
  --require-accepted-with-credentials
```

如果当前环境没有 DeepSeek 或 OpenAI 凭证，真实 provider smoke 可以生成结构化 skip report；结构化 skip 不能被记为 accepted。

## 5. 检查 Docker stage

第二版当前没有实现 Docker backend，采用 interface-only 验收路径：

```bash
DOCKER_STATUS_FILE=runs/v2-docker-stage-20260501T222345Z/docker_stage_status.json

PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend \
  --status-file "$DOCKER_STATUS_FILE" \
  --assert-stage-complete
```

预期结果：

- `mode = "interface_only"`。
- `docker_backend_implemented = false`。
- `docker_execution_mode_behavior = "clearly_rejected"`。

## 6. 生成 feedback policy 覆盖报告

```bash
FEEDBACK_POLICY_REPORT="$TASK_SET_DIR/feedback_policy_report.json"

PATH=.venv/bin:$PATH repo-harness inspect-feedback-policy-coverage \
  --experiment-dir "$TASK_SET_DIR" \
  --output "$FEEDBACK_POLICY_REPORT" \
  --assert-complete
```

覆盖范围：

- `disabled`
- `public_only`
- `structured_public_feedback`
- `oracle_hidden_feedback`
- `stop_immediately`
- `require_model_final`
- `continue`

## 7. 生成全局验收报告

```bash
V1_DIR=runs/v2-final-v1-regression-20260501T223447Z
ACCEPTANCE_REPORT=runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json

PATH=.venv/bin:$PATH repo-harness build-v2-acceptance-report \
  --v1-regression-dir "$V1_DIR" \
  --task-set-manifest "$TASK_SET_DIR/experiment_manifest.json" \
  --mock-provider-report "$MOCK_DIR/mock_provider_smoke_report.json" \
  --real-provider-report "$REAL_PROVIDER_REPORT" \
  --feedback-policy-report "$FEEDBACK_POLICY_REPORT" \
  --export-audit-root "$V1_DIR/exports" \
  --export-audit-root "$MOCK_DIR/exports" \
  --export-audit-root "$TASK_SET_DIR/exports" \
  --docker-status "$DOCKER_STATUS_FILE" \
  --output "$ACCEPTANCE_REPORT"

PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance \
  "$ACCEPTANCE_REPORT" \
  --assert-complete
```

预期结果：

- `status = "passed"`。
- task count 为 20。
- mock provider 为 accepted。
- real provider 为 DeepSeek accepted 或无凭证结构化 skip。
- Docker stage 为 interface-only passed。
- 三种导出格式都有 audit report。
- provider raw response 没有进入训练 payload。

## 边界提醒

第二版是轻量级研究 harness，不是生产级安全平台。Docker 当前是可审计扩展路径，不是已完成后端。真实 provider 只表示可以驱动评测运行，不表示已经训练出 coding agent。
