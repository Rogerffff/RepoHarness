# V5 面试 Demo 卡片

## 代表任务

- 任务编号：`v5_task_008`
- 候选来源：`pelletier/go-toml#1041`
- 仓库：`pelletier/go-toml`
- 任务族：`parser_error_location`
- 模型可见任务描述：Parser errors for an incomplete key at the end of a document without a trailing newline should point at the incomplete key position rather than the document end.

## 代表真实运行

- 运行编号：`v5_accepted_deepseek_v5_task_008_deepseek_v4_pro`
- Provider：`deepseek`
- Scaffold：`single_shot_patch`
- Budget：`v5_accepted_single_shot_patch_budget`
- Final verifier 状态：`accepted`
- Accepted：`true`

## 可展示数字

- 已冻结并可审计任务：12
- PR / issue flow 任务：8
- 真实 provider run：7
- 真实 provider accepted：1
- 真实 provider trainable records：2
- Diagnostic records：1
- Blocked records：1

## 声明边界

当前可以展示 V5 已经具备任务冻结、真实 provider accepted run evidence、trainable 分区导出、provider-axis 补充证据和 public-safe demo artifact。当前不能声称 resume-ready 多 provider 结论、preference export 已完成，或 export stress test 已完成。
