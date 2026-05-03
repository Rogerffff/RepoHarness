# RepoHarness 第三版（V3）最终验收记录

本文是第三版（V3）验收报告生成之后编写的 post-acceptance 文档，不是
`v3_acceptance_report.json` 的输入。最终验收报告绑定的是报告生成前已经冻结的范围文档、实施计划、审查文档、阶段日志、阶段审查、预验收测试证据、显式 run selection manifest、export audit 和 V2 回归证据。本文只在报告生成之后由 `acceptance_bundle_manifest.json` 绑定。

## 验收结论

RepoHarness 第三版（V3）当前最终验收通过。

- 最终验收目录：`runs/v3-final-rerun-20260504T010000Z/acceptance`
- 最终验收报告：`runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json`
- 报告状态：`passed`
- `inspect-v3-acceptance --assert-complete`：通过
- 报告 sha256：`17574314b53c02c84874ab02caaf862b30e5051ac1a835a38bc7aead9aeba2e4`

本次验收取代了 2026-05-03 的旧验收目录。旧验收报告保留为历史证据，但不再作为当前 V3 passed 依据，因为后续审查发现旧 run selection 中核心 V3 角色曾由 replay run 替代，且 Docker phase evidence、训练 payload 污染扫描和 post-acceptance 文档边界存在检查盲区。本次验收使用当前检查器重新绑定证据并重新生成报告。

第三版（V3）的定位保持不变：RepoHarness 现在具备可执行、可审计、可导出的 repository-level evaluation harness 能力。它不是完整 SWE-Bench Lite 公开榜单复现，不声称生产级安全沙箱，不声称工业级分布式 rollout 服务，也不声称已经训练出了 coding agent。

## 核心运行

`real_repository` 角色使用真实 DeepSeek provider 和 Docker backend：

- 路径：`runs/v3-core-realrepo-deepseek-20260504T000000Z/agent_loop_runs/v3_core_realrepo_local_buggy_calculator_deepseek_docker_v2`
- provider：`deepseek`
- workspace backend：`docker`
- final verifier：`accepted`
- fail-to-pass：`1/1`
- pass-to-pass：`2/2`
- Docker backend inspect：通过
- trajectory store inspect：通过
- tool contract inspect：通过

`swebench_like` 角色使用真实 DeepSeek provider、Docker backend、固定 SWE-Bench-like task 和 RepoHarness 自有 final verifier：

- 路径：`runs/v3-core-swebench-deepseek-20260504T000000Z/agent_loop_runs/v3_core_pytest_dev__pytest_8365_deepseek_docker_patch_focused_amd64_final_only_v7`
- task：`pytest-dev__pytest-8365`
- provider：`deepseek`
- workspace backend：`docker`
- final verifier：`accepted`
- fail-to-pass：`1/1`
- pass-to-pass：`32/32`
- `test_feedback_policy`：`disabled`
- `max_test_runs`：`0`
- Docker backend inspect：通过
- trajectory store inspect：通过
- tool contract inspect：通过

该 SWE-Bench-like run 是 final-only 候选：模型可见上下文没有 `run_tests`，没有暴露 raw `test_patch`、gold patch、`FAIL_TO_PASS`、`PASS_TO_PASS`、隐藏 selector、official harness report 或 hidden verifier result。只读 subagent 复审未发现 P1、P2 或 P3。

## 预验收测试证据

预验收测试证据写入独立目录，然后由 `build-v3-acceptance-inputs` 显式绑定。

- 预验收证据目录：`runs/v3-final-rerun-20260504T010000Z/pre_acceptance_evidence`
- 预验收命令日志：`runs/v3-final-rerun-20260504T010000Z/pre_acceptance_command_log.jsonl`
- 预验收文档清单：`runs/v3-final-rerun-20260504T010000Z/pre_acceptance_documentation_manifest.json`

全量测试：

- 命令：`PATH=.venv/bin:$PATH python -m pytest`
- 结果：`488 passed in 220.34s`
- stdout sha256：`18aa01239587cc2a180e8a3563ffa60dad33b40bb17ad183b0b5dcd71ac9be3e`
- stderr sha256：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

第二版（V2）回归：

- 命令：`PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- 结果：`status=passed`，`task_count=20`
- mock provider：`accepted`
- real provider：`accepted_with_credentials`
- stdout sha256：`a32dc40c6e7cadd37511855ad46786fa454d28870883a4b0c6cbf69c82b200dc`
- stderr sha256：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

## 验收输入

最终 run selection manifest：

- 路径：`runs/v3-final-rerun-20260504T010000Z/run_selection_manifest.json`
- sha256：`201de0c4d2fcd777d2a7050e4008f0053875539c3d2305b4ae78944b77d72adc`

最终 acceptance inputs：

- 路径：`runs/v3-final-rerun-20260504T010000Z/v3_acceptance_inputs.json`
- sha256：`ece2ffa6bf59acb25bdb595f858c038597f96dd7b45e50e5668a5805302359c4`

Export audit：

- 路径：`runs/v3-export-audit-rerun-20260504T003000Z`
- `inspect-v3-export-audit --assert-clean`：通过
- audit 状态：`passed_with_warnings`
- 唯一 warning：`preference_pair_baseline_blocked`
- blocked reason：`no_trainable_preference_pair`

`ACCEPTANCE_INPUTS` 显式绑定以下类别：

- `run_selection_manifest`
- `export_root`
- `v2_report`
- `pre_acceptance_docs`
- `documentation_manifest`
- `command_log`
- `test_evidence`

## 修复提交

本次重新验收前补充的关键提交包括：

- `87b4af9 fix: strengthen fallback component scaffold guidance`
- `05c9abe fix: avoid windows path contamination false positive`
- `76f9790 fix: harden fallback identity scaffold guidance`
- `8d9457a fix: avoid broad windows drive path contamination`
- `4796807 fix: record blocked preference baseline reason`

这些提交修复了真实 DeepSeek SWE-Bench-like 候选的 final-only scaffold 指导、公开 Windows 路径误报、本机路径 URI 拦截边界，以及没有 preference pair 时 export audit 缺少 blocked reason 的结构性问题。

## 允许降级项、禁止降级项和残余风险

允许降级项：

- 没有真实 provider 凭证时允许结构化 skip；本次绑定的是 DeepSeek accepted-with-credentials evidence，没有使用 skip 冒充 accepted run。
- 不可训练或诊断性样本允许由 export audit 标记为 `invalid`、`diagnostic_only` 或 `skipped`，但不得静默进入正式训练 payload。
- 第三版（V3）验收保持 `max_parallel_runs=1` 和 `evaluation.concurrency=1`。

禁止降级项：

- 禁止把官方 SWE-Bench harness report 当作 V3 final verifier。
- 禁止把 Docker `interface_only` 或硬拒绝当作 V3 Docker backend 通过。
- 禁止把 replay 或 mock run 作为 `real_repository` 或 `swebench_like` 核心角色替代品。
- 禁止把 evaluator-only gold material、verifier patch、隐藏测试选择器、provider raw 原文、Authorization marker 或本机绝对路径放入模型可见上下文或正式训练 payload。
- 禁止覆盖旧 `ACCEPTANCE_DIR`；本次 acceptance builder 使用新的不存在目录创建报告。

残余风险：

- Export audit 当前为 `passed_with_warnings`，原因是没有形成可训练 preference pair；该情况已经结构化记录为 `no_trainable_preference_pair`，并未阻断 `inspect-v3-export-audit --assert-clean`。
- 阶段 8 的正式机器产物主要演示 baseline interrupt injection；agent_loop 和 final_verifier interrupt injection 由代码和测试覆盖。
- 第三版（V3）是本地可执行、可审计 harness，不是公开榜单可比的 SWE-Bench Lite 复现。
