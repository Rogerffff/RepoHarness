# 第 5 章：Final verifier、reward、export、acceptance

## 本章链路图

```text
AgentLoop 停止
-> capture_final_patch
-> verification workspace
-> final verifier
-> VerifierResult.accepted
-> compute_reward_metadata
-> run_metadata / metrics
-> export quality evidence
-> v4 acceptance inputs
-> v4 acceptance report
-> doc-sync acceptance bundle
```

SWE-Bench-like final-only 分支：

```text
Agent final patch
-> frozen baseline verifier workspace
-> evaluator-only verifier plan
-> selector cache
-> fail-to-pass command
-> pass-to-pass command
-> swebench_like_agent_loop_final_verifier_report.json
-> VerifierResult
```

## 本章实际运行或查看的命令

```bash
jq '{accepted, pass_ratio, fail_to_pass, pass_to_pass, exit_code, error_type, verifier_stage, command}' \
  runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker/artifacts/tutorial_realrepo_docker_artifact_000051_final_verifier_result.json

jq '{final_reward, components, invalid_for_training, sources: {patch_added_lines: .sources.patch_added_lines, patch_removed_lines: .sources.patch_removed_lines, tool_call_count: .sources.tool_call_count, test_run_count: .sources.test_run_count, turn_count: .sources.turn_count}}' \
  runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker/reward.json

jq '{accepted, pass_ratio, fail_to_pass, pass_to_pass, exit_code, timeout, error_type, verifier_stage, command}' \
  runs/v3-core-swebench-deepseek-20260504T000000Z/agent_loop_runs/v3_core_pytest_dev__pytest_8365_deepseek_docker_patch_focused_amd64_final_only_v7/artifacts/v3_core_pytest_dev__pytest_8365_deepseek_docker_patch_focused_amd64_final_only_v7_artifact_000066_final_verifier_result.json

PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs \
  runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json \
  --assert-complete

PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance \
  runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json \
  --assert-complete

PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle \
  runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json \
  --assert-immutable

PATH=.venv/bin:$PATH python -m pytest -q
```

实际复核结果：

- tutorial realrepo final verifier：accepted，fail-to-pass `1/1`，pass-to-pass `2/2`，exit code `0`。
- tutorial realrepo reward：`0.996`，其中 accepted bonus、fail-to-pass、pass-to-pass 都是 `1.0`，patch size penalty 为 `0.004`。
- SWE-Bench-like `pytest-dev__pytest-8365` final-only verifier：accepted，fail-to-pass `1/1`，pass-to-pass `32/32`。
- V4 acceptance report：`passed`，accepted auditable task definition 数量为 `8`，trainable payload contamination status 为 `clean`，final verifier authority preserved 为 `true`。
- 全量测试结果见本文件后续更新的“最终测试结论”。

## 源码入口和对象流

关键入口：

- `src/repo_harness/verifier/runner.py:32`：feedback verifier。
- `src/repo_harness/verifier/runner.py:64`：final verifier。
- `src/repo_harness/verifier/runner.py:79`：pytest 命令执行和 parser。
- `src/repo_harness/verifier/runner.py:148`：declared fail-to-pass / pass-to-pass 测试执行。
- `src/repo_harness/verifier/acceptance.py:11`：`VerifierResult.accepted` 判定策略。
- `src/repo_harness/v3_agent_runtime.py:119`：SWE-Bench-like agent loop final verifier。
- `src/repo_harness/v3_agent_runtime.py:269`：通过 workspace adapter 执行 SWE-Bench-like verifier command。
- `src/repo_harness/reward/calculator.py:12`：reward metadata。
- `src/repo_harness/v4_export_quality.py:425`：V4 export quality inspect。
- `src/repo_harness/v4_acceptance.py:233`：V4 acceptance report builder。

关键理解：

- final verifier 是 formal authority，不是 agent 自报结果。
- ordinary realrepo 任务在 clean verification workspace 中重放 final patch，然后运行 pytest verifier。
- SWE-Bench-like final-only 任务使用 evaluator-only verifier plan 和 selector cache，不把隐藏验证材料暴露给模型。
- reward metadata 来自 final verifier、patch stats 和事件计数；V4 reward audit 进一步用 allowlist 限制 reward 字段来源。
- export quality 把 outcome tier 和 trainability status 分开：verifier accepted 不自动等于 trainable。

## 面试追问与推荐回答

问：为什么 final verifier 要在干净 workspace 里跑？

答：agent workspace 可能包含临时文件、缓存、调试副作用或未记录环境变化。strict patch replay 先捕获 final patch，再在干净 verification workspace 重放，能把最终评分绑定到源码补丁本身。

问：accepted 是不是等于 pytest 退出码为 0？

答：不是。`VerifierResult.accepted` 来自 acceptance policy。它会考虑 timeout、parser confidence、fail-to-pass、pass-to-pass、dependency error 和 regression。只有没有声明测试集合时，才 fallback 到整体 exit code。

问：为什么 verifier accepted 不自动等于 trainable？

答：训练样本还要经过 export quality 检查，例如污染风险、patch quality、reward allowlist、preference pair 可比较性和 failure dataset 策略。accepted 是结果事实，trainable 是导出策略判断。

## 最终测试结论

本轮已运行：

```bash
PATH=.venv/bin:$PATH python -m pytest -q
```

结果：

```text
712 passed in 822.26s (0:13:42)
```

这与 V4 final acceptance 文档中的完整测试结论一致，说明当前工作区代码、测试和最新 V4 验收口径是对齐的。
