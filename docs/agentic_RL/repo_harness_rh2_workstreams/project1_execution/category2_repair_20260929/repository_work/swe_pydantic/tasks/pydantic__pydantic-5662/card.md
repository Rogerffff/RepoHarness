# Pydantic 5662 当前题卡

2026-10-03。**离线修订已准备，待非作者核查、正式登记和CPU验收。**

题面要求模型左侧的相等运算可委托给一般比较对象。09-29正式结果为 noop0／gold1／all_nonmodels_equal0／any_only1；`any_only` 只修ANY，普通matcher仍失败。gold的一般委托、dict/object护栏与旧7项相等测试已有实测。原件：[CPU结果](../../../../../swegym_cpu_preprobe_20260929/tasks/pydantic__pydantic-5662/result.md)。

本轮保留原ANY F2P与127 P2P，追加 `test_equality_delegation_nonexample` 为F2P：普通对象返回True、False或NotImplemented，且收到原模型；不限制内部代码形态或调用次数。保留dict/object不等控制。[有效补丁](effective_test.patch)与[修订单](revision.json)已检查可应用，新增断言没有在本题Python3.8/core0.27.0下运行。

正式最小矩阵沿用四份工件，预期0／1／0／0；这些是新版本预期，不能覆盖旧reward。旧actor行为检查及安装成功证据可按身份复用，另核新宿主与实际题面/public_hints交付。独立核查、新材料评分、探针与结果分析仍未完成；当前只作问题定位与修订准备，不新增训练／留出资格。
