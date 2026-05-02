# V3 Stage 06 SWE-Bench-Like Verifier Plan And Final Verifier

## 目标

阶段 6 的目标是实现 RepoHarness 自己的 SWE-Bench-like verifier plan 和 fail-to-pass / pass-to-pass final verifier evidence。本阶段不使用 official SWE-Bench harness report 作为 final verifier result，也不进入 Agent Loop。

## 实现内容

新增 `build-v3-swebench-like` 和 `inspect-swebench-like`：

- 为阶段 0 固定的 3 个 accepted task 生成 resolved `SweBenchLikeEnvironmentSpec`。
- 为每个 task 生成 `SweBenchLikeVerifierPlan`，包含 base test command、fail-to-pass command、pass-to-pass command、selector source、selector cache、selector failure strategy、per-command timeout、parser policy、expected artifact refs 和 hidden visibility policy。
- 解析 evaluator-only `FAIL_TO_PASS` 和 `PASS_TO_PASS`，生成 selector cache。
- selector 转换同时覆盖路径型 pytest node id 和裸函数名 selector；`sympy__sympy-24909` 的 `test_prefix_operations` 被转换为 `sympy/physics/units/tests/test_prefixes.py::test_prefix_operations`。
- 对包含 `::` 参数值的旧 pytest parametrized selector，转换为同文件 `-k` 函数表达式，避免旧 pytest 命令行把参数里的 `::` 误解析为 node 层级。
- Docker setup 阶段允许受控网络安装 verifier 依赖；实际 F2P/P2P test execution 使用 `--network none`。
- 对每个 task 记录 baseline fail-to-pass failing evidence、pass-to-pass baseline evidence、gold patch passing evidence 和独立 final patch verifier result。
- `inspect-swebench-like --assert-complete` 会重新读取 plan、selector cache 和 evidence refs，并在既有 verifier workspaces 中重新执行 F2P/P2P 命令。

## 主要修改文件

- `src/repo_harness/v3_swebench_like.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/tasks/schemas.py`
- `src/repo_harness/verifier/schemas.py`
- `tests/unit/test_v3_swebench_like.py`
- `docs/v3/implementation-log/06-stage-06-swebench-like-verifier-plan-and-final-verifier.md`
- `docs/v3/review/implementation/stage-06-review.md`

## 机器产物

阶段 6 SWE-Bench-like verifier 产物目录：

- `runs/v3-stage-06-swebench-like-20260502T191500Z/`

关键机器产物：

- `runs/v3-stage-06-swebench-like-20260502T191500Z/swebench_like_task_manifest.json`
- `runs/v3-stage-06-swebench-like-20260502T191500Z/tasks/*/swebench_like_environment_spec.json`
- `runs/v3-stage-06-swebench-like-20260502T191500Z/tasks/*/swebench_like_verifier_plan.json`
- `runs/v3-stage-06-swebench-like-20260502T191500Z/tasks/*/selector_cache.json`
- `runs/v3-stage-06-swebench-like-20260502T191500Z/tasks/*/verifier_evidence/baseline/*.json`
- `runs/v3-stage-06-swebench-like-20260502T191500Z/tasks/*/verifier_evidence/gold/*.json`
- `runs/v3-stage-06-swebench-like-20260502T191500Z/tasks/*/verifier_evidence/model_final/*.json`
- `runs/v3-stage-06-swebench-like-20260502T191500Z/tasks/*/final_verifier_result.json`
- `runs/v3-stage-06-swebench-like-20260502T191500Z/tasks/*/command_outputs/*.txt`
- `runs/v3-stage-06-swebench-like-20260502T191500Z/inspect_rerun/*/command_outputs/*.txt`

## 验证命令和结果

- `PATH=.venv/bin:$PATH python -m compileall src`：通过。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_swebench_like.py -q`：`3 passed`。
- `PATH=.venv/bin:$PATH repo-harness build-v3-swebench-like --source-materialization-run runs/v3-stage-05-source-materialization-20260502T181500Z --hidden-verifier-inputs docs/v3/evidence/swebench-lite-fixed/evaluator_only/hidden_verifier_inputs.jsonl --gold-patch-predictions docs/v3/evidence/swebench-lite-fixed/evaluator_only/gold_patch_predictions.jsonl --output-dir runs/v3-stage-06-swebench-like-20260502T191500Z`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-swebench-like runs/v3-stage-06-swebench-like-20260502T191500Z --manifest runs/v3-stage-06-swebench-like-20260502T191500Z/swebench_like_task_manifest.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_swebench_like.py tests/unit/test_v3_source_materialization.py tests/unit/test_v3_task_set.py tests/unit/test_repo_materialization.py tests/integration/test_repo_materialization_smoke.py -q`：`27 passed`。
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v3_schemas.py tests/unit/test_v3_swebench_like.py -q`：`10 passed`。
- `PATH=.venv/bin:$PATH python -m pytest -q`：`419 passed`，最终修复后重新运行通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-swebench-fixture --fixture-dir tests/fixtures/v3/swebench_lite_fixed --evidence-dir docs/v3/evidence/swebench-lite-fixed --manifest tests/fixtures/v3/swebench_lite_fixed/adapter_inputs/v3_feasibility_input_manifest.json --assert-frozen`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-source-materialization runs/v3-stage-05-source-materialization-20260502T181500Z --report runs/v3-stage-05-source-materialization-20260502T181500Z/source_materialization_report.json --assert-complete`：通过。

上述全量测试和 V2 regression 均已在最终修复后重新运行。

## 正例证据

- 3 个 accepted task 都生成了 environment spec、verifier plan、selector cache 和 final verifier result。
- environment spec 记录真实 40 位 `environment_setup_commit`，例如 `pytest-dev__pytest-7220` 为 `678c1a0745f1cf175c442c719906a1f13e496910`。
- `pytest-dev__pytest-7220` final result：F2P `1/1`，P2P `11/11`，accepted `true`。
- `pytest-dev__pytest-8365` final result：F2P `1/1`，P2P `32/32`，accepted `true`。
- `sympy__sympy-24909` final result：F2P `1/1`，P2P `2/2`，accepted `true`。
- 所有 final result 均记录 `official_harness_report_used=false`。
- hidden verifier stdout / stderr artifact refs 标记为 `evaluator_only`。
- `inspect-swebench-like --assert-complete` 重新执行 plan command 后通过。

## 负例证据

单元测试覆盖：

- 裸函数名 selector 能映射到 test patch 中唯一测试文件。
- 多个 test patch 文件下的裸函数名 selector 会 fail closed。
- selector cache 的 expanded fail-to-pass 为空时 inspect 拒绝。

真实构建过程中还暴露并修复了一个 selector 转换问题：`pytest-dev__pytest-7220` 的部分 PASS_TO_PASS 参数值包含 `::`，旧 pytest 对精确 node id 命令行选择返回 `not found`。修复后该类 selector 转换为同文件 `-k` 表达式，inspect 重新执行通过。

## 允许降级项

阶段 6 不运行真实 Agent Loop，因此还没有由 Agent Loop 生成的模型 final patch。本阶段使用固定 evaluator-only gold patch prediction 作为 `stage6_reference_patch_probe_from_fixed_gold_prediction`，在独立 `model_final_workspace` 中执行 strict patch replay，以证明 RepoHarness 自有 final verifier path。真实 provider 或 mock provider 产生的 model final patch 将在阶段 7 进入同一 final verifier 路径。

## 禁止降级项

- 不允许使用 official SWE-Bench harness report 作为 RepoHarness final verifier result。
- 不允许把 raw `test_patch`、raw `FAIL_TO_PASS`、raw `PASS_TO_PASS` 或 gold patch 写入模型可见上下文。
- 不允许 selector 为空、PASS_TO_PASS 为空或 parser confidence 低于阈值时标记 accepted。
- 不允许 baseline fail-to-pass 已通过或 baseline pass-to-pass 未通过时进入 accepted evidence。

## 已知限制

阶段 6 的 verifier workspaces 和 Docker command evidence 尚未接入常规 Agent Loop run metadata、trajectory store、export audit 或 final acceptance inputs；这些属于阶段 7 到阶段 12。

## 设计偏离

没有使用 official harness final report。为了在没有 Agent Loop 的阶段 6 生成独立 final verifier evidence，本阶段用固定 gold prediction 作为 reference final patch probe；该事实在 manifest 中明确标记为 `model_final_patch_source=stage6_reference_patch_probe_from_fixed_gold_prediction`。

## 审查结论

首轮只读子代理审查发现 1 个 P1、1 个 P2 和 1 个 P3，均已修复并重新验证。最终只读复审未发现 P1/P2/P3，阶段 6 允许进入阶段 7。详细记录见 `docs/v3/review/implementation/stage-06-review.md`。
