# V5 Canonical Demo Walkthrough

## 5 分钟讲解主线

1. 原始任务来自 `pallets/click#3208`，仓库是 `pallets/click`，任务族是 `cli_error_formatting`。
2. 模型只看到脱敏后的任务描述：Command error output should display a helpful help-option hint only when the relevant help option is actually available, including cases where a subcommand option shadows a parent option.
3. Stage 2 固定了源码哈希 `159473a9db63bb74955941c7358e861aca67e73cec04e3661c788e6804924d97`、任务输入哈希和 verifier 计划引用。
4. Stage 3B 运行了真实 provider family `deepseek`，运行编号是 `v5_stage3b_deepseek_v5_task_003`。
5. 这条运行使用 `simple_react` scaffold 和 `stage3b_constrained_one_turn_no_tool_calls` budget；本轮是最小真实 provider loop，没有执行仓库内工具或 final verifier。
6. Final verifier 状态保留为 `not_executed_stage3b_minimal_provider_loop`，因此 demo 不把它讲成 accepted patch。
7. Stage 4 从真实运行生成 sanitized SFT / rollout 格式样本，同时把 diagnostic-only、blocked 和 failure dataset 分开。
8. Stage 5 的 public-safe bundle 只引用脱敏摘要和 redacted transcript excerpt。

## 可展示的关键 observation

脱敏 transcript excerpt 会显示系统消息、模型可见任务输入、assistant 的第一轮回答，以及由于 budget 限制产生的工具中断结果。这个 excerpt 只使用 `content_preview`，不包含 provider 私有载荷、evaluator-only 证据、隐藏测试或 reward 数值。

## 现场负例 inspect

可以复制 `v5_demo_negative_inspect_report.json` 中的负例说明：如果 public demo bundle 引入私有 provider 载荷、evaluator-only 内容、模型可见泄漏，或者把被 claim gate 阻断的强表述放入可复制简历 bullet，`inspect-v5-demo-artifacts --assert-share-safe` 应拒绝该 artifact。

## 降级讲法

如果现场不展示 provider 调用细节，只讲 evidence chain：task freeze -> real provider run metadata -> final verifier boundary -> export partition -> public-safe demo bundle -> acceptance binding。需要强调当前 V5 core 方向已具备证据链，但 resume-ready 的多 provider 和 preference pair 仍然被 claim gate 阻断。
