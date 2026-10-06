# Project-MONAI__MONAI-3715

`needs_review`：评分漏掉题面强调的train模式；仅供development_diagnostic，独立review待完成。base `d36b835b226a…`。gold把look_up_option结果赋回局部mode，静态上同时修复两个字符串及共享子类路径。

| 要求/旧行为 | 公开依据与验收 | 判断 |
|---|---|---|
| train字符串能运行训练上下文 | 题面、Evaluator文档及with self.mode | 无F2P/P2P覆盖 |
| eval字符串可构造/run | F2P test_content仅新增mode="eval"，验image/label | noop报eval ValueError，gold通过 |
| 默认模式保留 | P2P test_empty_data | 仅构造/空epoch直接返回，不跑模型 |

八方面已查：公开目标、base初态、全部修改与两个参考项、非gold路线/静态错修、gold与两个Evaluator子类/上下文、CPU合成数据与Ignite依赖、投影恢复、用途暴露。未执行mutant、train集成或模型，未把独立mode helper测试当字符串分派已验。

只修eval或无条件eval_mode可满足现有断言而不满足公开train诉求，这是check25漏测；eval要求有公开依据，不能记成隐藏规格冲突。P2P少也不证明gold新增回归，check26未知。旧报告“仅删train分支即可满分”缺少先修eval的前提；字面删除仍会失败。public_read建议的函数身份检查也不应升为验收，等效上下文实现应被允许。

原RH2 w05-1 ledger15/16分别目标失败/两项全过，恢复及源码投影吻合，无参考缺席/skip；历史镜像实际ID未记录。实际actor消息、初态、依赖/权限/源码生效仍unknown。旧3690关联仅为未核实线索；审查已见私有答案和旧记录，不可转交solver。

唯一优先下一步：先提出公开API的train行为验收，检查forward时training/梯度与退出恢复，并保留eval/枚举行为；静态选择器遗漏无需先跑CPU证明。本阶段不改评分或执行任务二。完整映射与原件定位见analysis_before_history.md，历史纠正见old_findings_delta.md。
