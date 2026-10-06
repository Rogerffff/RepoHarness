# mypy15184：修订版两模型首轮验收

2026-10-03 15:29（Asia/Singapore）。正式材料 `mypy15184-nested-nominal-types-v2` 的 CPU 四候选及两模型各一次首轮已完成验收。Qwen3.6、Qwen3-Coder 都正常完成，原评分各为1，正式3个F2P、2个P2P共五项均实际执行并通过，安装与测试段退出0，双层清理正常。总账请求已 returned/ack，活动请求已清空；这是当前版本普通探针的完成记录，训练、留出资格均未增加。

两候选的 `mypy/messages.py` 字节相同：失败诊断复用既有 `format_type_distinctly`，同时格式化实际类型和目标类型。helper 递归类型参数，支持顶层和嵌套同名类型消歧；有效断言判断及原表达式返回类型保持。CPU 的 noop/gold/错误拒绝有效断言/仅修顶层四候选为0/1/0/0，与实际模型五项参考共同支持这次有限语义结论。没有发现需要修题、改评分或新增 CPU 作业的问题。

| 每模型一次观测 | Qwen3.6 | Qwen3-Coder |
| --- | --- | --- |
| 正式参考 | 5/5通过 | 5/5通过 |
| 求解秒数 | 62.946 | 52.738 |
| 生成回合／工具 | 40／39 | 25／24 |
| 累计输入／输出 token | 528184／6067 | 864729／3051 |
| 自验问题 | 两次自写测试错误已纠正；管道尾部不单独证明 pytest 退出0 | 空选择退出5已纠正；最终测试覆盖陈述过宽，登记P3 |

Coder 的有效断言无报错只能证明有效断言保持，不能证明无歧义错误文案简洁；“全部既有 assert_type 相关测试通过”也超出实际选择范围。正式 `testAssertTypeFail3`、`testAssertType` 和未改 guard 分别补足当前评分行为的依据；无需为修正文案评价而补跑。模型没有主动验证嵌套，嵌套通过来自正式受信参考。两模型完整 FP 不同：Qwen 的测试修改被可信投影排除；Coder 的97项缓存、4个开发脚本及源码共102项全部投影，原件均保留。

两臂材料、镜像、完整基线内容、任务 block、参考和预算相同，但 runtime 分别为 code_v5/code_v7，共有7个共享成员不同。实际本题脚本和参考相符，不能据此称整个 runtime 相同。各一次墙钟、回合和 token 只作观察，不能得出可靠性能排序或稳定性结论。

Qwen 的 Q13 已另核40次请求、adapter 和后端完成对应；复用适用的共享服务来源事实，不冒称旧 Q12 审覆盖 Q13。Coder 有 job 前服务读回和25次生成对应。两者仅支持有限运营来源归因：未重新核全部权重或 GPU 驻留内容，HTTP revision/checksum 为 null，Qwen capture 是事后记录；Coder manifest 声明28项但列出25项（16个 safetensors），未列出的3项未知。旧身份 false 标记、旧审查和 raw1 不变。

当前无待运行 CPU/GPU 作业。按[覆盖优先规则](../../../overnight_watch_20261003.md)暂缓普通追加采样；只有新具体失败、评分缺陷或材料身份变化才按影响接续。本记录不恢复旧退租或自动销毁安排。

固定证据见[题主验收 JSON](two_model_first_round_acceptance_20261003.json)，SHA `a7b15e173df1d2044f309f17cbf01689711de12ddf2d6497e9bfdf9058792793`。它绑定 CPU 条件验收、旧 Qwen 原件与非作者收口、新 [Coder 轨迹](coder_first_arm_trace_20261003.md)、[语义反证](../reviews/non_author_15184_coder_semantic_20261003.md)、[执行链核查](../reviews/non_author_15184_coder_execution_20261003.md)、[Q13 来源补证](q13_operational_identity_supplement_20261003.json)及[其独立窄核](../reviews/non_author_15184_q13_identity_20261003.json)。新增审查已见 gold/private，非 fresh，未重复执行模型或项目测试。
