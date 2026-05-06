# V5 Implementation Review 13：最终命令日志闭环和 provider-axis 绑定

## 审查范围

- final command log 是否必须绑定当前最终 `v5_acceptance_bundle_manifest.json` 的构建 entry 和 inspect entry。
- OpenAI / DeepSeek provider-axis report 是否可以由 `inspect-v5-run-matrix` 机器检查。
- provider-axis proof 是否进入 Stage 5 result summary、claim gate 和 Stage 6 acceptance inputs。
- 展示文案是否仍然阻断 resume-ready、preference export 和 trainable export 强表述。

## 结论

允许进入下一步验证和提交。当前修复没有把 V5 提升为 core acceptance passed；`core_acceptance.status=failed` 仍然是正确状态，失败原因是缺少通过 final verifier 的真实 provider trainable record。

## 发现与处理

- P1：旧 final command log 只记录 pre-final bundle 的 build / inspect entry。已通过 planned build entry、planned inspect entry 和新的 immutable inspect 要求修复。
- P1：inspect entry 不能再用 previous bundle 作为当前最终 bundle 的替代证明。已要求至少一条 inspect entry 的 argv 与自引用 input path 指向当前最终 bundle。
- P2：`v5_provider_comparison_report.json` 之前不能由 `inspect-v5-run-matrix` 检查。已新增 schema spec 和 deep inspect。
- P2：provider-axis proof 之前没有进入 acceptance inputs。已新增 `--v5-provider-comparison-report` 并计划在新的 Stage 6 证据中绑定。
- P2：result summary 和 Q&A 仍沿用单 provider blocker。已改为“provider-axis proof exists，但整体 resume-ready 仍被 scaffold、budget、preference pair 和 trainable export 阻断”。
- P2：只读复核发现 provider comparison inspect 对受控变量字段全集校验不足。已补强全局 `controlled_variables`、每个 `provider_pairs[*].task_id`、`provider_pairs[*].cell_ids` 和 pair-level controlled variables 必备字段校验，并增加“只保留 task_id 必须失败”的负例测试。

## 负例

- 使用新代码检查旧的 `runs/v5-final-acceptance-hardening-followup-20260506T062200Z/v5_acceptance_bundle_manifest.json` 时，immutable inspect 应失败，并指出 final command log 缺少当前最终 bundle 的 build / inspect entry。
- 将 provider comparison report 的 `controlled_variables` 缩减为只包含 `task_id` 时，`inspect-v5-run-matrix --assert-complete` 应失败，并提示缺少受控变量字段。

## 残余风险

当前仍没有可计入 trainable payload 的 accepted final verifier run。这个风险不在本轮修复范围内，必须继续由 claim gate 和 acceptance report 阻断。
