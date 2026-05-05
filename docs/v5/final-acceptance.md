# V5 Final Acceptance

## 结论

截至 2026-05-05，本轮 V5 final acceptance 的核心验收已经通过，简历完成验收仍然阻断。当前最新 V5 验收目录为：

```text
runs/v5-final-acceptance-20260505T191500Z/
```

核心验收通过的含义是：V5 已经把 V4 的可执行、可审计、可导出闭环扩展为面向展示的结果包，覆盖任务冻结、真实 provider 运行证据、比较范围证明、分区训练导出、public-safe demo artifact、result summary、acceptance inputs、acceptance report 和 acceptance bundle。

简历完成验收仍然阻断的原因是：当前只有一个真实 provider family 有实际运行证据，并且没有真实可比较 preference pair。因此最终文档、简历和项目展示不得写成多 provider 已形成公平对比、preference export 已完成，或者 export stress test 已完成。

## 关键机器产物

```text
runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_inputs.json
runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_report.json
runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_report_reference_integrity_report.json
runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_bundle_manifest.json
runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_bundle_command_lineage_report.json
runs/v5-final-acceptance-20260505T191500Z/v5_pre_bundle_command_log.jsonl
runs/v5-final-acceptance-20260505T191500Z/v5_final_acceptance_command_log.jsonl
```

Stage 5 展示包入口为：

```text
runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_resume_artifact_index.json
runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_interview_result_pack_manifest.json
```

## 验收状态

- `core_acceptance.status=passed`。
- `resume_ready_acceptance.status=blocked`。
- V5 acceptance report reference integrity 检查通过，未绑定关键证据数量为 `0`。
- V5 public-safe demo bundle 检查通过。
- V5 acceptance bundle immutable inspect 通过。

## 关键验证结果

本轮 Stage 6 使用当前 V5 代码重新运行全量测试：

```text
766 passed in 622.16s
```

同时通过：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v5-inputs runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_report.json --assert-core-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_bundle_manifest.json --final-command-log runs/v5-final-acceptance-20260505T191500Z/v5_final_acceptance_command_log.jsonl --assert-immutable
```

`inspect-v5-acceptance --assert-resume-ready` 按预期失败，并生成 command log entry 作为降级声明证据。这个失败不是 core acceptance 失败，而是提醒当前不得使用简历完成级强表述。

## V4 Baseline 说明

V4 closure baseline 由 Stage 0 的以下产物绑定：

```text
runs/v5-stage0-preimplementation-20260505T143530Z/v5_baseline_check_report.json
runs/v5-stage0-preimplementation-20260505T143530Z/v5_preflight_input_binding.json
runs/v5-stage0-preimplementation-20260505T143530Z/v5_preimplementation_command_log.jsonl
```

Stage 6 没有在已经包含 V5 源码变更的当前工作区重新运行旧 V4 doc-sync bundle immutable inspect。旧 V4 doc-sync bundle 绑定的是 V4 验收当时的文件字节，V5 源码变更后不应把它作为当前工作区阶段门。

## 可使用表述

可以保守表述为：

```text
RepoHarness V5 实现了本地优先的软件工程智能体评测与训练数据 Harness，覆盖任务冻结、真实 provider 运行证据、受控变量比较范围证明、分区导出审计、public-safe demo artifact、result summary 和 immutable acceptance bundle。
```

不得表述为完整 SWE-Bench 榜单复现、生产级安全沙箱、分布式强化学习 rollout 集群、完整 Claude Code / Codex 产品复刻，或者已经训练出 coding agent。
