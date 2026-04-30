# Stage 06: Verifier, Accepted Policy, Reward And Metrics

## Scope

本阶段实现了：

- `PytestVerifier`：
  - `run_baseline()`
  - `run_feedback()`
  - `run_final()`
- 第一版 pytest 文本 parser helper，用于 parser confidence 和常见错误分类。
- `repo_harness_acceptance_policy_v0`：
  - 低 parser confidence 不能接受。
  - timeout 不能接受。
  - 声明了 fail-to-pass 和 pass-to-pass 时必须分别满足。
  - pass-to-pass regression 会标记 `regression_detected`。
  - 未声明测试集合时退化为整体 exit code 判定，并记录 fallback reason。
- 对声明的 fail-to-pass 和 pass-to-pass 测试逐个运行 `python -m pytest -q <test_id>`，稳定统计用例级结果。
- `compute_reward_metadata()`：
  - 只读取 final verifier、patch stats 和 event counts。
  - 处理缺失 fail-to-pass 分母时不把该分量当满分。
  - timeout、低 parser confidence 和 patch apply failure 标记为训练无效。
- `build_metrics_record()`，从 final verifier 和 run 摘要字段构造 `MetricsRecord`。
- Verifier、acceptance、reward 和 micro-repo 集成测试。

本阶段明确不实现：

- 不实现 Eval Runner 的 baseline 质量门控编排。
- 不实现 Agent Loop。
- 不实现 Tool System 或 Permission System。
- 不把 feedback verifier 当作 formal final verifier。
- 不实现 training export。

## Design References

- `docs/14-v1-implementation-plan.md`
- `docs/07-verifier-reward-and-evaluation.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/05-workspace-sandbox-and-permissions.md`

## Files Changed

- `src/repo_harness/verifier/pytest_parser.py`
- `src/repo_harness/verifier/acceptance.py`
- `src/repo_harness/verifier/runner.py`
- `src/repo_harness/verifier/__init__.py`
- `src/repo_harness/reward/calculator.py`
- `src/repo_harness/reward/__init__.py`
- `src/repo_harness/evaluation/metrics.py`
- `src/repo_harness/evaluation/__init__.py`
- `src/repo_harness/workspace/adapter.py`
- `tests/unit/test_pytest_parser.py`
- `tests/unit/test_acceptance_policy.py`
- `tests/unit/test_reward.py`
- `tests/integration/test_verifier_micro_repos.py`

## Verification

运行的命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_pytest_parser.py tests/unit/test_acceptance_policy.py tests/unit/test_reward.py tests/integration/test_verifier_micro_repos.py
PATH=.venv/bin:$PATH python -m pytest
PATH=.venv/bin:$PATH python -m compileall src
```

结果：

- 通过。
- verifier/reward 相关测试收集并通过 14 个测试。
- 全量测试收集并通过 73 个测试。
- `compileall` 通过。

调试记录：

- 初次运行 micro-repo verifier 时，子进程在临时 workspace 中找不到 `pytest`。根因是 `.venv/bin` 在 shell 中是相对 PATH，切换 cwd 后不再指向仓库虚拟环境。
- 处理方式：Workspace Adapter 执行命令时，将当前 Python 解释器所在目录的绝对路径加入 PATH 前缀。
- 另一个调试点是 full pytest 命令可能出现 collection-level error，而逐个声明测试仍能给出精确 regression 结果；accepted policy 现在让 pass-to-pass regression 覆盖泛化的 full-command error。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查。

关键审查意见：

- 完整 verifier 命令出现 `test_command_error` 或 dependency error 时，即使逐个声明测试通过，也必须 `accepted = false`。
- `final.patch` 应用失败需要能落成 `VerifierResult(accepted=false, error_type=patch_apply_failed)`，供 reward、metrics 和 export filter 使用。
- `VerifierResult` 缺少 verifier stage 和完整 verifier 原始输出 artifact 引用。
- fail-to-pass 分母为 0 时使用备用 reward 公式，但 formula 字符串仍写主公式，审计口径不一致。
- 建议明确当前 pytest 用例级统计依赖 declared test rerun 策略，而不是完整 pytest 输出解析。

处理结果：

- 采纳：accepted policy 增加命令级错误优先阻断，`test_command_error`、`dependency_error` 和 `patch_apply_failed` 都不能被声明测试通过覆盖。
- 采纳：新增 `build_error_verifier_result()`，用于把 patch apply failure 等 verifier 前置错误转换成结构化 `VerifierResult`。
- 采纳：`VerifierResult` 增加 `verifier_stage` 和 `raw_output_ref`，`PytestVerifier` 会填入完整 verifier 命令输出 artifact。
- 采纳：reward 计算在 fail-to-pass 分母缺失时写入实际使用的备用公式字符串。
- 采纳：新增测试覆盖命令级错误阻断、patch apply failure 结构化结果、stage/raw output ref、feedback path 和备用 reward 公式。

## Known Limitations

- pytest parser 仍是第一版文本解析 helper，不是通用跨语言 parser。
- 第一版为了稳定统计声明测试用例，会额外逐个运行 fail-to-pass 和 pass-to-pass 测试；这适合当前 micro-repo fixture，后续需要扩展到结构化测试报告。
- baseline invalid/flaky 质量门控仍由后续 Eval Runner 阶段实现。
- RewardMetadata 是 verifier-aligned prototype，不是新的强化学习算法。

## Commit

- Commit: `stage 06: implement verifier reward metrics`
- Commit message: `stage 06: implement verifier reward metrics`
