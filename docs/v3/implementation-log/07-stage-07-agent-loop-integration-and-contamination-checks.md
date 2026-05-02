# V3 Stage 07 Agent Loop Integration And Contamination Checks

## 目标

阶段 7 的目标是把 V3 真实 repository-level task 和 SWE-Bench-like final-only task 接入常规 `run_task` / Agent Loop 主干，并验证 Docker backend 工具执行、final patch 冻结、独立 verification workspace strict replay、RepoHarness 自有 final verifier 和模型可见污染扫描。

本阶段不重做 provider 主线，不使用 official SWE-Bench harness report，不把 Stage 6 的 evaluator-only gold patch 当作模型输出。

## 实现内容

新增 Stage 7 Agent Loop 集成能力：

- `run_task` 可以识别带有 Stage 6 `swebench_like_task_manifest.json` 引用的 SWE-Bench-like final-only 任务投影。
- 对 SWE-Bench-like final-only 任务，baseline 不运行模型可见隐藏测试，而是使用 Stage 6 冻结的 evaluator-only baseline evidence 生成结构化 baseline summary。
- SWE-Bench-like Agent Loop 完成后，RepoHarness 先通过 Docker backend 创建独立 verification workspace 并 strict replay `final.patch`，再在 Stage 6 verifier workspace 副本中执行 RepoHarness 自有 fail-to-pass / pass-to-pass final verifier。
- 新增 `build-v3-agent-loop-integration`，一次性生成并运行一个真实仓库 Agent Loop run 和一个 SWE-Bench-like Agent Loop run。
- 新增 `inspect-v3-agent-loop-integration`，只读检查 Stage 7 报告、run 轨迹文件、Docker backend status、tool call 终态配对、SWE-Bench-like final verifier evidence 和污染扫描结果。
- 新增 `scan_v3_run_surfaces`，扫描 prompt、prepared messages、tool observation、transcript、checkpoint、context compaction report 和训练导出占位 surface。
- 调整 Context Builder 系统提示，不再把内部 `reward_metadata` 对象名写入模型可见上下文。
- 调整 V3 host path denylist，保留当前本机 home 路径、`/Users/`、`/private/` 和 Windows 盘符，但不再把公开 issue 文本中的通用 `/home/...` 示例误判为本机绝对路径泄漏。

## 主要修改文件

- `src/repo_harness/v3_agent_runtime.py`
- `src/repo_harness/v3_agent_loop.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/context/builder.py`
- `src/repo_harness/v3_visibility.py`
- `tests/unit/test_v3_agent_loop.py`
- `docs/v3/implementation-log/07-stage-07-agent-loop-integration-and-contamination-checks.md`
- `docs/v3/review/implementation/stage-07-review.md`

## 机器产物

阶段 7 Agent Loop 集成产物目录：

- `runs/v3-stage-07-agent-loop-20260502T203000Z/`

关键机器产物：

- `runs/v3-stage-07-agent-loop-20260502T203000Z/v3_agent_loop_integration_report.json`
- `runs/v3-stage-07-agent-loop-20260502T203000Z/real_repository_contamination_scan.json`
- `runs/v3-stage-07-agent-loop-20260502T203000Z/swebench_like_contamination_scan.json`
- `runs/v3-stage-07-agent-loop-20260502T203000Z/generated_inputs/*`
- `runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_realrepo_local_buggy_calculator/`
- `runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_pytest-dev__pytest-7220/`
- `runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_pytest-dev__pytest-7220/v3_swebench_like_final_verifier/pytest-dev__pytest-7220/final_verifier_result.json`

两个实际启动的 run 都包含 `transcript.jsonl`、`events.jsonl`、`artifacts.json`、`run_config_facts.json`、`run_metadata.json`、`final.patch`、`final.diff`、`verifier.json`、`reward.json` 和 `metrics.json`。

## 验证命令和结果

- `PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v3_agent_runtime.py src/repo_harness/v3_agent_loop.py src/repo_harness/evaluation/runner.py src/repo_harness/cli/main.py`：通过。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_agent_loop.py tests/unit/test_v3_visibility_policy.py tests/unit/test_v3_swebench_like.py tests/integration/test_single_shot_patch.py -q`：`14 passed`。
- `PATH=.venv/bin:$PATH repo-harness build-v3-agent-loop-integration --source-materialization-run runs/v3-stage-05-source-materialization-20260502T181500Z --swebench-like-run runs/v3-stage-06-swebench-like-20260502T191500Z --output-dir runs/v3-stage-07-agent-loop-20260502T203000Z`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-agent-loop-integration runs/v3-stage-07-agent-loop-20260502T203000Z --report runs/v3-stage-07-agent-loop-20260502T203000Z/v3_agent_loop_integration_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_realrepo_local_buggy_calculator/docker_backend_status.json --assert-docker-backend`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-workspace-backend --status-file runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_realrepo_local_buggy_calculator/docker_stage_status.json --assert-docker-backend`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-run runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_realrepo_local_buggy_calculator`：通过，run outcome `success`，final verifier `accepted`。
- `PATH=.venv/bin:$PATH repo-harness inspect-run runs/v3-stage-07-agent-loop-20260502T203000Z/agent_loop_runs/v3_stage_07_pytest-dev__pytest-7220`：通过，run outcome `failed`，final verifier `failed`，失败原因为诊断 patch 未修复隐藏 F2P。
- `PATH=.venv/bin:$PATH python -m compileall src`：通过。
- `PATH=.venv/bin:$PATH python -m pytest -q`：`421 passed`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-source-materialization runs/v3-stage-05-source-materialization-20260502T181500Z --report runs/v3-stage-05-source-materialization-20260502T181500Z/source_materialization_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-swebench-like runs/v3-stage-06-swebench-like-20260502T191500Z --manifest runs/v3-stage-06-swebench-like-20260502T191500Z/swebench_like_task_manifest.json --assert-complete`：通过。

## 正例证据

- 真实仓库 run `v3_stage_07_realrepo_local_buggy_calculator` 使用常规 `simple_react` Agent Loop，执行了 `read_file`、`edit_file` 和 `run_tests` 三个 tool call，三者都有终态 tool result。
- 真实仓库 run 在 Docker backend 下完成 baseline、Agent Loop、final patch capture、verification workspace creation、model final patch apply、fail-to-pass、pass-to-pass 和 final verifier，最终 `run_outcome=success`，`final_verifier_status=accepted`。
- SWE-Bench-like run `v3_stage_07_pytest-dev__pytest-7220` 使用常规 `single_shot_patch` Agent Loop，完成 final patch freeze 和 Docker strict patch replay。
- SWE-Bench-like final verifier 使用 Stage 6 verifier plan 执行 RepoHarness 自有 F2P/P2P 命令，`official_harness_report_used=false`。
- `real_repository_contamination_scan.json` 和 `swebench_like_contamination_scan.json` 均为 `clean=true`，`finding_count=0`。
- Stage 7 报告中的 tool pairing 检查显示真实仓库 run `requested_tool_call_count=3`，`missing_terminal_tool_call_ids=[]`。

## 负例证据

新增单元测试覆盖：

- 模型可见 transcript 中出现 `gold_patch` 时，V3 污染扫描会报告 finding。
- Stage 7 inspect 遇到不干净的 contamination scan ref 时会拒绝通过。

真实构建初次运行还暴露了两个污染扫描问题：

- 系统提示中出现内部对象名 `reward_metadata`，已改成不暴露内部对象名的 `scoring artifacts`。
- 公开 SWE-Bench issue 文本中的 `/home/lhn/...` 示例路径被误判为本机路径，已将 denylist 调整为当前本机 home 路径和已知本机路径前缀。

修复后重新构建 Stage 7 产物，污染扫描和 `inspect-v3-agent-loop-integration --assert-complete` 均通过。

## 允许降级项

SWE-Bench-like Agent Loop run 使用的是不含隐藏解法材料的诊断 patch，因此 final verifier 完成但不 accepted。这样做是为了证明常规 Agent Loop、final patch freeze、Docker strict patch replay 和 Stage 6 F2P/P2P final verifier 已经贯通，同时避免把 evaluator-only gold patch 或隐藏测试选择器放进模型可见 replay。

## 禁止降级项

- 不允许把 official SWE-Bench harness report 当作 Stage 7 final verifier。
- 不允许把 raw `test_patch`、raw `FAIL_TO_PASS`、raw `PASS_TO_PASS` 或 gold patch 写入 prompt、prepared messages、tool observation 或 transcript。
- 不允许 Docker backend 静默回退到 `local_process`。
- 不允许真实仓库 Agent Loop run 缺少 final patch、run metadata、Docker backend status 或终态 tool result。

## 已知限制

阶段 7 尚未实现可恢复 Experiment Runner、context compaction、long rollout diagnostics、failure diagnostics 分布报告、export audit 或 acceptance bundle。这些属于阶段 8 到阶段 12。

SWE-Bench-like Agent Loop run 当前是 diagnostic failed run；正式 accepted SWE-Bench-like verifier evidence 仍由阶段 6 的独立 verifier 证明。后续阶段可以在不泄漏 hidden material 的前提下加入真实 provider 或人工非隐藏解法 patch 的 accepted Agent Loop run。

## 设计偏离

没有偏离阶段顺序。本阶段只在阶段 6 之后接入 Agent Loop，并未回头替代阶段 6 verifier，也未使用 official harness final report。

为避免隐藏解法污染，Stage 7 的 SWE-Bench-like Agent Loop 选择 diagnostic patch 而非 gold prediction patch；该 run 的失败结果是有意的诊断结果，不作为任务成功率证明。

## 审查结论

当前环境尝试创建只读子代理时返回 thread limit reached，因此本阶段执行等价独立只读自审。自审未发现剩余 P1/P2/P3 阻断项，阶段 7 允许进入阶段 8。详细记录见 `docs/v3/review/implementation/stage-07-review.md`。
