# RepoHarness 第三版（V3）最终验收记录

本文是第三版（V3）验收报告生成之后编写的 post-acceptance 文档，不是
`v3_acceptance_report.json` 的输入。最终验收报告只绑定报告生成前已经冻结的范围文档、实施计划、审查文档、阶段 0 至阶段 12 的 implementation log、阶段 0 至阶段 12 的 implementation review、阶段 7 至阶段 10 追溯子代理智能体补审材料、预验收测试证据和显式 run selection manifest。本文只由 `acceptance_bundle_manifest.json` 在报告生成之后绑定。

## 验收结论

RepoHarness 第三版（V3）已经完成阶段 0 至阶段 13 的实现闭环。由于最终验收后发现阶段 7 至阶段 10 原始阶段审查曾因为子代理智能体线程未清理而退回自审，项目已补充追溯子代理智能体审查，修复阶段 9 发现的 P2 审计一致性问题，并重新构建最终验收报告。随后又发现旧验收报告没有拦截 SWE-Bench-like selected run 的 Docker final verifier phase 缺失，并且 acceptance contamination scan 对若干 surface 使用占位 payload。本次已经修复这些 P1 缺口，重新生成并检查新的最终验收报告。新的最终验收报告路径为：

- `runs/v3-final-acceptance-20260503T095012Z/acceptance/v3_acceptance_report.json`
- 报告状态：`passed`
- `inspect-v3-acceptance --assert-complete`：通过
- 报告 sha256：`6d6e65904aa07b2d08e1b026c34f6462ac5c50deef8f2e5ee1f12e114ba9cdff`

最终验收包路径为：

- `runs/v3-final-acceptance-20260503T095012Z/acceptance/acceptance_bundle_manifest.json`
- `inspect-acceptance-bundle --assert-immutable`：通过

先前的 `runs/v3-final-acceptance-20260503T034631Z/acceptance/v3_acceptance_report.json` 和 `runs/v3-final-acceptance-20260503T043025Z/acceptance/v3_acceptance_report.json` 保留为历史验收证据，但已被本次重新构建的最终验收报告取代。新版本 `inspect-v3-acceptance` 会重新读取被绑定的 Docker backend evidence，因此旧 `20260503T043025Z` 报告现在会因为 SWE-Bench-like Docker phase coverage 缺失而被拒绝。

第三版（V3）仍然保持实施计划限定的定位：它是可执行、可审计、可导出的 repository-level evaluation harness。它不是完整 SWE-Bench Lite 公开榜单复现，不声称生产级安全沙箱，不声称工业级分布式 rollout 服务，也不声称已经训练出了 coding agent。

## 阶段提交

- 阶段 0：`1cef08d feat: freeze v3 swebench fixture inputs`
- 阶段 1：`6694432 feat: add v3 schema and visibility policy`
- 阶段 2：`e341f4c feat: add v3 docker workspace backend`
- 阶段 3：`a47587d feat: add v3 docker phase coverage`
- 阶段 4：`39bc006 feat: add v3 task set adapters`
- 阶段 5：`947e99d feat: add v3 source materialization`
- 阶段 6：`01cdae4 feat: add v3 swebench-like verifier`
- 阶段 7：`73848ea feat: add v3 agent loop integration`
- 阶段 8：`7d4a9fc feat: add v3 experiment resume runner`
- 阶段 9：`dff8c69 feat: add v3 context diagnostics`
- 阶段 10：`39f4fca feat: add v3 failure diagnostics`
- 阶段 11：`572ed96 feat: add v3 export audit`
- 阶段 12：`b0491af feat: add v3 acceptance inspection bundle`
- 阶段 13：`7167508 docs: add v3 final acceptance closure`
- 阶段 7 至阶段 10 追溯补审与阶段 9 修复：本文件所在后续补充提交，内容包括阶段 7 至阶段 10 追溯子代理智能体审查、阶段 9 context compaction 审计修复、新的阶段 9/10 机器产物和重新构建的最终验收证据。
- P1 验收修复：`ee01fcd fix: record swebench verifier docker phases`、`c7692f3 fix: enforce v3 acceptance docker inspection`、`bf987d0 fix: scan acceptance evidence surfaces`、`a6cfd67 fix: project export payload contamination scans`。

## 预验收测试证据

预验收测试证据先写入独立目录，再由 `build-v3-acceptance-inputs` 显式绑定，未提前写入最终 `ACCEPTANCE_DIR`。

- 预验收证据目录：`runs/v3-final-pre-acceptance-20260503T095012Z/evidence`
- 预验收命令日志：`runs/v3-final-pre-acceptance-20260503T095012Z/pre_acceptance_command_log.jsonl`
- 预验收文档清单：`runs/v3-final-pre-acceptance-20260503T095012Z/manifests/pre_acceptance_documentation_manifest.json`

全量测试：

- 命令：`PATH=.venv/bin:$PATH python -m pytest`
- 结果：`452 passed in 253.02s`
- stdout sha256：`3b5b3a4f7cf7d21aa945650f3b41be43d777e550d8bf3cdec8993a5f5886f4fe`
- stderr sha256：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- result.json sha256：`7d2c9858482cdc5531e9bae9f1bf51d87a8bb009ed0e823cd9206acfb0285ce0`

第二版（V2）回归：

- 命令：`PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- 结果：`status=passed`，`task_count=20`，mock provider 为 `accepted`，真实 provider 为 `accepted_with_credentials`
- stdout sha256：`a32dc40c6e7cadd37511855ad46786fa454d28870883a4b0c6cbf69c82b200dc`
- stderr sha256：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- result.json sha256：`2318c9e48326b76a6a0859b40e26764244a9c544d19512363cc98a88e6f6b02b`

阶段 9 和阶段 10 补审修复相关 inspect 也写入同一预验收证据目录：

- `inspect-context-report` 结果：通过，stdout sha256 为 `48f8883284c94cfb8bb2b3d73fa3da4930b4ad9f6f338d22a72d7371f3a0cc05`。
- `inspect-long-rollout-diagnostics` 结果：通过，stdout sha256 为 `3664e08f6c8fd60bbf70516f943041960f1d0a6158a59cc78cd51572e0f59cd6`。
- `inspect-reward-diagnostics` 结果：通过，stdout sha256 为 `1904d0e9bbdbc0b63e342a86e0bd2aa41697e2598587bc216aea8561d6d69165`。

## 最终验收输入

最终运行选择清单：

- 路径：`runs/v3-final-acceptance-20260503T095012Z/run_selection_manifest.json`
- sha256：`55ba29a89f15d938581aa863b0e32a7ec2f8f07ee3b2bce66bb4e81440247909`

最终验收输入清单：

- 路径：`runs/v3-final-acceptance-20260503T095012Z/v3_acceptance_inputs.json`
- sha256：`7811734f0d0a8d38f106511ec1b1fb5718c51431028c5b6fda20953a93f5aa81`

最终验收报告绑定的 `ACCEPTANCE_INPUTS` 包含以下类别：

- `run_selection_manifest`
- `export_root`
- `v2_report`
- `pre_acceptance_docs`
- `documentation_manifest`
- `command_log`
- `test_evidence`

最终 run selection 显式绑定了 replay、mock provider、credential-gated real provider、真实 repository-level、SWE-Bench-like、resume、context、long rollout 和 failure diagnostics 角色。SWE-Bench-like 角色使用 `sympy__sympy-24909` 的第三版第十三阶段 Agent Loop 运行：

- `runs/v3-final-swebench-agent-loop-20260503T-p1-docker-facts/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3_p1_python311_docker_facts`
- 运行结果：`run_outcome=success`
- final verifier：`accepted`
- Docker phase coverage：`source_checkout`、`setup`、`agent_tool`、`run_tests`、`final_patch_capture`、`verification_workspace_creation`、`model_final_patch_apply`、`fail_to_pass_test_execution`、`pass_to_pass_test_execution` 和 `final_verifier` 均有 Docker facts；`verifier_patch_apply` 和 `test_patch_apply` 仅在该任务无对应 patch 时结构化标记为 not applicable。
- 补丁来源：adapter-visible problem statement 和固定本地 source checkout；未把 evaluator-only patch、隐藏 selector 或官方 harness 报告放入模型可见上下文。

本次重建的 context、long rollout 和 failure diagnostics 角色绑定修复后的补充产物：

- context 和 long rollout：`runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/`
- failure diagnostics：`runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/`

## 允许降级项、禁止降级项和残余风险

允许降级项：

- 没有真实 provider 凭证时允许结构化 skip；本次最终选择绑定的是已有 DeepSeek accepted-with-credentials evidence，因此未使用 skip。
- 不可训练或诊断性运行允许被 export audit 标记为 `invalid`、`diagnostic_only` 或 `skipped`，但不得静默进入正式训练 JSONL。
- 第三版（V3）验收可以保持 `max_parallel_runs=1` 和 `evaluation.concurrency=1`。

禁止降级项：

- 禁止把官方 SWE-Bench harness report 当作第三版（V3）final verifier。
- 禁止把 Docker `interface_only` 或硬拒绝当作第三版（V3）Docker backend 通过。
- 禁止把 evaluator-only gold material、verifier patch、隐藏测试选择器、provider raw 原文、Authorization marker 或本机绝对路径放入模型可见上下文或正式训练 payload。
- 禁止用失败 run、mock run 或 replay run 冒充 credential-gated real provider accepted evidence。
- 禁止覆盖旧 `ACCEPTANCE_DIR`；本次 `acceptance` 目录由 builder 新建。
- 禁止继续使用旧阶段 9 context compaction 报告作为最终验收输入；最终验收必须使用修复后的阶段 9 产物。

残余风险：

- 阶段 8 追溯审查保留一个 P3 范围说明：正式机器产物只演示 baseline interrupt injection，agent_loop 和 final_verifier interrupt injection 由代码和测试覆盖，没有为每一种状态组合生成同等重量的阶段机器产物。
- 阶段 10 追溯审查保留 audit-only 输入边界 P3：诊断 input run 可以包含 reward 和 verifier 相关审计标记，但这些标记不得进入模型可见上下文或正式训练 payload。
- 阶段 11 export audit 根状态为 `passed_with_warnings`，原因是早期 SWE-Bench-like diagnostic failed run 被样本级 audit 拒绝并过滤。最终正式 run selection 已额外绑定 accepted 的 SWE-Bench-like Agent Loop 运行，但历史诊断失败运行仍保留为审计证据。
- 第三版（V3）实现的是本地可执行、可审计 harness，不是公开榜单可比的 SWE-Bench Lite 复现。

## 审查结论

阶段 13 完成后由子代理智能体 `Lorentz` 执行只读审查，并将结论写入：

- `docs/v3/review/implementation/stage-13-review.md`

随后针对阶段 7 至阶段 10 原始子代理智能体审查缺口，已经完成追溯子代理智能体补审：

- `docs/v3/review/implementation/stage-07-to-10-retrospective-subagent-review.md`

追溯补审结论为：阶段 7、阶段 8 和阶段 10 没有新的 P1/P2 阻断项；阶段 9 发现的 P2 已修复、重新生成机器产物并复审通过。新的最终验收报告可以作为第三版（V3）最终 acceptance evidence，验收包可以作为 post-acceptance documentation binding。
