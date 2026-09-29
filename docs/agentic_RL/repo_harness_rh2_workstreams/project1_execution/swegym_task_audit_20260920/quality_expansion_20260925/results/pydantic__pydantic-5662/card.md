# 5662 静态短卡

目标是在模型左侧比较时允许ANY和支持BaseModel的自定义对象接手。base `0346ddb6a35770007f32815d8e4a179b778e0ef4`。建议 `needs_review/static_review`，仅用于 `development_diagnostic`；actual actor资格未知。

| 要求/旧行为 | 依据与断言 | 覆盖 |
|---|---|---|
| `m == ANY` | 题面原例；唯一F2P test_equality_delegation | 精确覆盖；历史noop失败/gold通过 |
| 一般matcher回退 | 题面自定义比较说明 | 未测True/False/NotImplemented等一般对象 |
| 模型规则与dict不等 | main.py:540–561；test_comparing及六个model_equality测试 | 相关P2P已读并通过；不能说P2P全是模型间比较 |

已完整读gold、新增断言与相关fixture，核Python比较入口、模型/泛型/私有属性边界。gold只是非模型分支改返回NotImplemented及控制流重排；保留早返回的非gold解也合理。源码局部支持目标正确，没有证成gold新增回归；一般matcher缺口可能放过ANY特判。

原install-v1两次安装RC0，选tests/test_main.py；noop141 passed/1 failed/26 skipped，gold142 passed/26 skipped；127个expected P2P均PASS。精确镜像、命令、初态pyproject/pdm.lock差异和测试恢复证据在前稿，不能替代actor消息、初始工作树、权限/PATH/依赖/资产/网络/资源。合法候选仅源码，测试恢复1文件；未穷审评分攻击面。关联/留出重叠和实际答案暴露unknown，审查者已见私有材料与两份旧记录。

历史对照确认pilot已纠正L1漏看dict护栏；题面带方案不等于已知训练价值。唯一优先下一步：任务二在actual actor核ANY和一般matcher、dict/object护栏的小脚本及窄P2P，捕获初态和解释器来源。没有本次实验。独立review与协调裁定已完成，保留一般matcher覆盖限制。详见analysis_before_history与old_findings_delta。


协调裁定：有条件静态开发候选，ready_for_probe=false。旧dict不等护栏已在P2P，撤回历史“全部P2P只比较模型、递归委托即可满分”的论据；一般matcher漏测仍在。公开ANY和自定义比较小脚本可并入同一actual actor开发验证，不另凑私有CPU实验。27只保局部正确证据，正式训练/评测未批准。
