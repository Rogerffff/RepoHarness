# iterative__dvc-5839

base 为 daf07451f8e8，目标是让 metrics show 的 --precision n 按既有“小数点后 n 位、默认5”生效。源码漏传参数；gold仅补一个实参，静态符合原例和旧契约。建议保留为 development_diagnostic 候选，状态 needs_review/static_review；actor 条件尚未验证。

| 需求/旧行为 | 公开依据 | 测试/覆盖 | 证据或待验 |
| --- | --- | --- | --- |
| CLI精度生效 | metrics.py:250–258 | F2P只查空数据时helper收到8，部分覆盖 | 原始noop在该断言失败，gold通过 |
| 默认5及自定义精度 | 旧test_metrics_show_precision:303–333 | P2P直接验证helper的默认/4/7 | 两角色均通过 |
| 原科学记法样例及Markdown/JSON组合 | prompt:14–41、run:87–98 | 未被真实CLI断言覆盖 | 需公开CLI对照 |

八方面已查题面/源码、材料身份与初态、全部修改断言和fixture、1 F2P及21 P2P、合理替代路线、相关调用者、gold和提交恢复边界；题族未按同文件归类。S2原行、补丁与日志哈希一致。09-19派生配方下grader完成离线安装，noop为1失败/21通过，gold为22通过，参考无缺席；这些只证明该grader条件。实际消息、actor解释器/权限/配方消费、真实镜像泄漏及CLI原例未验。

内部mock限制实现形式，且不验证输出；尚无已执行误拒。只在命令层硬编码8可能仍过评分，但它明显违背公开默认与任意n要求，属于窄校准候选，不能仅因此阻断范围明确的诊断。旧报告称8位舍入后小数仍为零、helper忽略precision也能过，均被源码与既有show精度P2P推翻。gold没有已确认缺陷，无新增路径排除。

唯一下一步是在真实actor入口核导入并对固定YAML做默认/4/8 CLI比较；若同时校准评分，按封存分析比较base/gold/单行硬编码8候选。CPU未执行。独立reviewer已收口。详证见 analysis_before_history.md 与 old_findings_delta.md；主审已见gold及历史，不可充当未暴露solver。


复核收口：独立复核认可窄参数传递诊断；标量float既有不舍入行为不归为新gold缺陷，不能把该题概括为全部指标精度已验证。默认/4/8真实CLI先行，硬编码8只是可选评分校准。 详细依据与处置分歧见 review.md；未回写封存前稿。
