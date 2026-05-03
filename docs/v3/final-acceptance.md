# RepoHarness 第三版（V3）最终验收记录

本文是第三版（V3）验收报告生成之后编写的 post-acceptance 文档，不是
`v3_acceptance_report.json` 的输入。最终验收报告只绑定报告生成前已经冻结的范围文档、实施计划、审查文档、阶段 0 至阶段 12 的 implementation log、阶段 0 至阶段 12 的 implementation review、预验收测试证据和显式 run selection manifest。本文只由 `acceptance_bundle_manifest.json` 在报告生成之后绑定。

## 验收结论

RepoHarness 第三版（V3）已经完成阶段 0 至阶段 13 的实现闭环。最终验收报告路径为：

- `runs/v3-final-acceptance-20260503T034631Z/acceptance/v3_acceptance_report.json`
- 报告状态：`passed`
- `inspect-v3-acceptance --assert-complete`：通过
- 报告 sha256：`fc199c1638dceb0869174750cc025a939eb2603fa8b6fdee44dbf66845353c4c`

最终验收包路径为：

- `runs/v3-final-acceptance-20260503T034631Z/acceptance/acceptance_bundle_manifest.json`

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
- 阶段 13：本文件所在提交，内容为最终验收文档、walkthrough、第十三阶段日志和第十三阶段审查记录。

## 预验收测试证据

预验收测试证据先写入独立目录，再由 `build-v3-acceptance-inputs` 显式绑定，未提前写入最终 `ACCEPTANCE_DIR`。

- 预验收证据目录：`runs/v3-final-pre-acceptance-20260503T034631Z/evidence`
- 预验收命令日志：`runs/v3-final-pre-acceptance-20260503T034631Z/pre_acceptance_command_log.jsonl`
- 预验收文档清单：`runs/v3-final-pre-acceptance-20260503T034631Z/manifests/pre_acceptance_documentation_manifest.json`

全量测试：

- 命令：`PATH=.venv/bin:$PATH python -m pytest -q`
- 结果：`447 passed in 201.53s`
- stdout sha256：`c87f3319236ec35b5d029a88bf0c09bf69484e0743df1ffcb31a3edaf7102af2`
- stderr sha256：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- exit code sha256：`9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`

第二版（V2）回归：

- 命令：`PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- 结果：`status=passed`，`task_count=20`，mock provider 为 `accepted`，真实 provider 为 `accepted_with_credentials`
- stdout sha256：`a32dc40c6e7cadd37511855ad46786fa454d28870883a4b0c6cbf69c82b200dc`
- stderr sha256：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- exit code sha256：`9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`

## 最终验收输入

最终运行选择清单：

- 路径：`runs/v3-final-acceptance-20260503T034631Z/run_selection_manifest.json`
- sha256：`c7e51c3452ea6a6d405443afc219afad5d6ab2821f73527e2a0b7dd965d78305`

最终验收输入清单：

- 路径：`runs/v3-final-acceptance-20260503T034631Z/v3_acceptance_inputs.json`
- sha256：`c032f71759a25d3a27b0eeb62374cdbf3c47a369d20ae648584cddde3e56b440`

最终验收报告绑定的 `ACCEPTANCE_INPUTS` 包含以下类别：

- `run_selection_manifest`
- `export_root`
- `v2_report`
- `pre_acceptance_docs`
- `documentation_manifest`
- `command_log`
- `test_evidence`

最终 run selection 显式绑定了 replay、mock provider、credential-gated real provider、真实 repository-level、SWE-Bench-like、resume、context、long rollout 和 failure diagnostics 角色。SWE-Bench-like 角色使用 `sympy__sympy-24909` 的第三版第十三阶段 Agent Loop 运行：

- `runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3`
- 运行结果：`run_outcome=success`
- final verifier：`accepted`
- 补丁来源：adapter-visible problem statement 和固定本地 source checkout；未把 evaluator-only patch、隐藏 selector 或官方 harness 报告放入模型可见上下文。

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

残余风险：

- 阶段 11 export audit 根状态为 `passed_with_warnings`，原因是早期 SWE-Bench-like diagnostic failed run 被样本级 audit 拒绝并过滤。最终正式 run selection 已额外绑定 accepted 的 SWE-Bench-like Agent Loop 运行，但历史诊断失败运行仍保留为审计证据。
- 第三版（V3）实现的是本地可执行、可审计 harness，不是公开榜单可比的 SWE-Bench Lite 复现。

## 审查结论

阶段 13 完成后由 subagent `Lorentz` 执行只读审查，并将结论写入：

- `docs/v3/review/implementation/stage-13-review.md`

审查结论为：未发现 P1、P2 或 P3 问题；最终验收报告可以作为第三版（V3）最终 acceptance evidence，验收包可以作为 post-acceptance documentation binding。
