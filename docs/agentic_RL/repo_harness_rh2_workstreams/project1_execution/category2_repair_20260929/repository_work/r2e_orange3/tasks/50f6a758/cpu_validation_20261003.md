# Orange50 CPU实际验收

2026-10-03。**八方正式对照、实际CC及独立诊断CPU验收已完成。固定单题探针已提交，GPU实际准入／模型结果尚待。** 版本090/091、R9来源和实际镜像绑定见[固定绑定](r9_cpu_release_binding.json)；[正式结果](cpu_matrix_result_20261003.json)记录完整SHA和原件入口，固定验收计划的生成时空值保留。

| 对照 | 实际分数／键匹配 | 实际判断 |
| --- | --- | --- |
| noop | 0／47-of-48 | 原缺警告，目标断言失败 |
| gold | 1／48-of-48 | 正确修复通过 |
| K1 | 1／48-of-48 | 完整列出长名单的合理解被接受 |
| K2 | 0／47-of-48 | 加载数据后未警告，目标断言失败 |
| K3 | 0／47-of-48 | 混合定义不警告，目标断言失败 |
| K4 | 0／47-of-48 | numeric未用变量漏报，目标断言失败 |
| C-deg | 0／47-of-48 | 警告检查通过，但匹配class定义未应用，目标输出断言失败 |
| K5 | 0／47-of-48 | 有警告却不点名，目标断言失败 |

八方原始日志与固定expected逐键重比对一致：键集48，参考无缺席或跳过，测试段完整，运行／解析无基础设施异常。实际setup为1200秒，测试预算1800秒；所有candidate与grader清理、CLI footer及远端作业终态0已核。218份matrix、job和观察原件逐文件大小／SHA回收通过。矩阵SSH运输曾以255断开，远端继续完成；运输失败与评分成功分别保留，未重启或重复计数。

资源ledger的`resource_facts`仍为空。旁路观察覆盖gold后段（一个grader容器）和K1–K5/C-deg（candidate与grader），核实际HostConfig／cgroup；noop没有独立实测，不能由后来观察回推。完整观察保留自身起止时间，尚待非作者核查。

[实际CC结果](cpu_actor_result_20261003.json)已完整回收70文件并核SHA。CC2.1.205正常完成10个Bash步骤、原生FrozenPatch导出、quiescence与容器／网络／relay清理；题面8d7ddab…含ISSUE标记，是首HTTP正文逐字后缀，全prompt0e229b…另有repo/commit前缀。

| 公开开发验证 | base实际结果 | 私有gold控制实际结果 |
| --- | --- | --- |
| 五个既有回归selector | 5通过 | 5通过 |
| 公开需求临时检查 | 3失败、2通过 | 5通过 |
| 原完整冲突测试 | 1通过 | 1失败，抵达公开文件888行最后unused定义的“不警告”断言 |

两阶段实际导入均为`/testbed/Orange/widgets/data/owcolor.py`；base源码c5390b…，固定修复源码14fcfc…与正式gold冻结源码相同。原生render对actual baseline归档应用后，逐字等于本次FrozenPatch及已加载源码。仓库测试未改；私有gold只用于CPU控制，不交求解者。真实actor主容器2CPU／4GiB／512／swap0；relay独立256MiB／64，不能称relay也为2CPU。合成endpoint用量和费用不是模型消耗；本actor使用`--no-grade`，不产生新的正式候选分数。

[非作者审查](../../reviews/orange50_r9_cpu_review_20261003.md)已完成八方／资源、实际CC和中性公开brief的结果窄核，无未解决阻断。[最终CPU验收](cpu_acceptance.json)和[接收回执](independent_cpu_review_receipt.json)记录当前用途；单项matrix/actor及原binding保留各自生成时的pending／false快照，不能代替更晚的最终验收状态。公开brief尚未在CPU HTTP交付，GPU仍须按固定请求逐字交付并读回。

[单题探针请求](probe_request.json)已通过总账落账并定向送GPU，SHA为`5a99f02f…`，请求ID为`r2e-orange50-r090091-cpu-sysconfig-v1-20261003`；[发送回执](probe_submission_receipt.json)保存实际工具返回，不虚构message ID。两模型各1完整首轮及当前权威宽松预算由执行者落实，当前无模型结果，不宣称GPU准入。题主继续按公开要求审候选、分析具体轨迹和必要修复；重复采样服从全批第二阶段安排。CPU验收和探针提交不自动赋予训练或留出资格。
