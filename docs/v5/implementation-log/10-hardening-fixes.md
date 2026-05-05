# V5 Hardening Fixes Implementation Log

## 目标

本轮修复上一轮复核指出的 V5 假阳性问题，重点是让 evidence ref、acceptance report reference integrity、final command log immutable binding 和 trainable export 分区都遵守 V5 的可审计边界。

## 实现内容

- `inspect-v5-inputs --assert-complete` 现在会校验顶层 V2 / V3 / V4 refs 和 `v5_evidence_refs` 中每个 evidence ref 的 `path`、`sha256` 和 `size_bytes`。
- `inspect-v5-acceptance --assert-core-complete` 现在会重新读取 `acceptance_inputs_ref`，并把 acceptance report 中没有由 acceptance inputs 绑定的关键 evidence refs 作为失败处理。
- V5 acceptance bundle manifest 支持 `final_command_log_ref`，并在 immutable inspect 中校验 final command log 的哈希、路径、inspect argv 和 input refs。
- Stage 4 export pack 不再把 `accepted=false` 或 `final_verifier_status` 不是 `accepted` 的真实 provider run 写入 SFT 或 reinforcement learning rollout trainable 分区。
- Stage 5 result summary 和 repro command index 不再硬编码 Stage 2B / Stage 4 路径，而是从显式输入读取任务库存和 export manifest 路径。
- `docs/v5/implementation-plan.md` 已澄清 scaffold / budget 双轴比较属于 resume-ready comparison 目标，不是当前单 provider core 证据的强结论。

## 主要修改文件

- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/v5_acceptance.py`
- `src/repo_harness/v5_export_pack.py`
- `src/repo_harness/v5_demo_artifacts.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v5_acceptance.py`
- `tests/unit/test_v5_export_pack.py`
- `tests/unit/test_v5_demo_artifacts.py`
- `docs/v5/final-acceptance.md`
- `docs/v5/walkthrough.md`
- `docs/v5/implementation-plan.md`

## 新增和更新的机器产物

```text
runs/v5-stage4-export-pack-hardening-20260505T184706Z/
runs/v5-stage5-demo-artifacts-hardening-20260505T184706Z/
runs/v5-final-acceptance-hardening-20260505T184706Z/
```

## 验证命令

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_v5_*.py -p no:cacheprovider
PATH=.venv/bin:$PATH repo-harness inspect-v5-export-pack runs/v5-stage4-export-pack-hardening-20260505T184706Z/v5_export_result_pack_manifest.json --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-hardening-20260505T184706Z/v5_resume_artifact_index.json --assert-share-safe
PATH=.venv/bin:$PATH repo-harness inspect-v5-inputs runs/v5-final-acceptance-hardening-20260505T184706Z/v5_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v5-final-acceptance-hardening-20260505T184706Z/v5_acceptance_bundle_manifest.json --final-command-log runs/v5-final-acceptance-hardening-20260505T184706Z/v5_final_acceptance_command_log.jsonl --assert-immutable
```

## 正例证据

- V5 unit tests 覆盖 acceptance inputs ref 篡改、acceptance report ref 篡改、final command log 篡改和 non-accepted trainable export。
- Hardening 后的 Stage 4 export pack 通过 clean inspect，且 `real_provider_trainable_records=0`。
- Hardening 后的 Stage 5 public-safe demo artifact 通过 share-safe inspect。
- Hardening 后的 V5 acceptance bundle 通过 immutable inspect，并绑定 final command log。

## 负例证据

- `inspect-v5-acceptance --assert-core-complete` 对 hardening 后的 acceptance report 失败，因为当前没有 accepted final verifier trainable record。
- `inspect-v5-acceptance --assert-resume-ready` 继续失败，因为第二个真实 provider family、真实 preference pair、scaffold comparison 和 budget comparison 仍然缺失。

## 允许降级项

- 当前 V5 可以保留任务冻结、真实 provider run metadata、diagnostic comparison proof、public-safe demo 和 immutable evidence bundle 的展示价值。
- 当前 V5 不再声称 core acceptance passed。

## 禁止降级项

- 不能把未执行 final verifier 的运行计入 trainable export。
- 不能在 acceptance inputs 中接受失效的 `path`、`sha256` 或 `size_bytes`。
- 不能让 final command log 只靠外部参数存在，必须由 bundle manifest 绑定。
- 不能在简历或最终文档中写 multi-provider comparison、preference export completed、trainable export completed 或 V5 core acceptance passed。

## 已知限制

当前真实 provider run 仍然是 Stage 3B minimal provider loop，没有执行最终 verifier 并产生 accepted patch。因此本轮修复后的正确结论是 V5 evidence chain hardened，但 final acceptance 不通过 core gate。

## 审查结论

已请求现有 sub agent 线程做只读复核；如果 sub agent 结果返回新的 P1 / P2 问题，必须继续修复后才能把 hardening 结果作为最新状态。
