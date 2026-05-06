# V5 Canonical Demo Walkthrough

## 5 分钟讲解主线

1. 原始任务来自 `pelletier/go-toml#1041`，仓库是 `pelletier/go-toml`，任务族是 `parser_error_location`。
2. 模型只看到脱敏后的任务描述：Parser errors for an incomplete key at the end of a document without a trailing newline should point at the incomplete key position rather than the document end.
3. Stage 2 固定了源码哈希 `04ff5f94c003a78d1168cd1fb694ccce79135694e435aec1109bf380dfbab5cb`、任务输入哈希和 verifier 计划引用。
4. Stage 3B 运行了真实 provider family `deepseek`，运行编号是 `v5_accepted_deepseek_v5_task_008_deepseek_v4_pro`。
5. 这条运行使用 `single_shot_patch` scaffold 和 `v5_accepted_single_shot_patch_budget` budget；provider 产出补丁后，RepoHarness 在独立 verification workspace 中重放 final patch。
6. Strict final verifier 状态为 `accepted`，并且 Stage 4 export pack 记录了真实 provider trainable record，因此这条 run 可以进入 trainable SFT 和 reinforcement learning rollout 分区。
7. Stage 4 生成导出分区结构和审计证据；accepted run 进入 SFT / reinforcement learning rollout trainable 分区，diagnostic-only、blocked 和 failure dataset 继续单独分区。
8. Stage 5 的 public-safe bundle 只引用脱敏摘要和 redacted transcript excerpt。

## 可展示的关键 observation

脱敏 transcript excerpt 会显示系统消息、模型可见任务输入、assistant 的第一轮回答，以及由于 budget 限制产生的工具中断结果。这个 excerpt 只使用 `content_preview`，不包含 provider 私有载荷、evaluator-only 证据、隐藏测试或 reward 数值。

## 现场负例 inspect

可以复制 `v5_demo_negative_inspect_report.json` 中的负例说明：如果 public demo bundle 引入私有 provider 载荷、evaluator-only 内容、模型可见泄漏，或者把被 claim gate 阻断的强表述放入可复制简历 bullet，`inspect-v5-demo-artifacts --assert-share-safe` 应拒绝该 artifact。

## 降级讲法

如果现场不展示 provider 调用细节，只讲 evidence chain：task freeze -> real provider run metadata -> final verifier boundary -> export partition -> public-safe demo bundle -> acceptance binding。需要强调当前 V5 具备通过 final verifier 的真实 trainable record 和可复核证据链；resume-ready 的 scaffold comparison、budget comparison 和 preference pair 门槛仍然被 claim gate 阻断。
