# Pydantic 8567 当前题卡

2026-10-03。**v5提案和五候选私有诊断已完成，完整正对照仍待正式矩阵核实，不可直接提交普通探针。**

目标是Annotated serializer在PlainValidator前后都生效，同时保留PV取代内层验证的既有能力。云端v4已覆盖精确Python/JSON输出、注解复用、被取代的约束／验证器、中间元数据、双serializer优先级及未知类型。旧31格工件和证据全部保留。[旧最终卡](../../../../../category3_diagnosis_20260929/tasks/pydantic__pydantic-8567/result.md)不是最终准入。

[接收纠正](../../../../../category2_repair_20260929/cloud_intake_20261002.md)指出：不能为了保upstream261正对照而排除B03、B06/N3。本轮只补已知机制：

- **B03，新F2P**：未知类型有PV时，serializer在PV前后均应产生精确Python/JSON输出。这是题面一般顺序要求与已有未知类型支持的组合；失败某种实现路线不等于约束内部实现。
- **B06，新P2P**：内层未定义前向引用，PV已取代其验证；直接核 `Model(value=5).value == 5`，不规定内部complete标志。
- **N3，新P2P**：Python3.8的stdlib typing.TypedDict作为被PV取代的内层类型，维持已实测正常构造。不是要求普通TypedDict改变兼容政策。

原1 F2P＋158 P2P保留，提案为2 F2P＋160 P2P。[有效补丁](effective_test.patch)保留v4原测试体，追加三项独立节点；[修订单](revision.json)固定31份旧工件。upstream261在新版本预期为0，不能再称完整正对照。c3_reorder、ok_post_attach、ok_pv_first_keep_sers均为正对照候选；前两份已有下述新行为实证，第三份仍未运行新增B06/N3。ok_wrapshim已有validation JSON schema问题，不用作正对照。

cpu-a第五版冻结入口已执行第一轮私有root诊断，实际Python3.8.19／core2.15.0、源码哈希及2 CPU／4 GiB／PID512吻合。五候选的安装、测试补丁应用和非空收集均退出0，运行原v4 F2P＋新增B03／B06／N3；noop两个F2P失败、两个P2P通过，gold四项失败，upstream261仅原v4通过。**c3_reorder和ok_post_attach四项全部通过**，五个容器零残留。[逐节点与原件指针](../../cpu_diagnostics_20261003/private_results.json)保留完整输出。这里支持两份候选满足本轮针对性行为，不冒称全部162参考的正式正对照；ok_pv_first_keep_sers未在本轮运行。

首轮先跑noop、gold、c3_reorder、upstream261、一个不同机制的正对照提名，再选B1／B2／B3及Python-only错误候选；这不是删去其余已知候选，扩大或去重须说明每个机制由哪一行覆盖。保留A16/A17源类型／类型参数serializer等原范围说明，不扩成无关新目标。

新节点私有实跑已补齐；尚缺正对照完整参考与语义核查、正式材料发布与评分、实际actor开发与公开交付。本轮没有正式reward，不新增普通比较、训练或留出资格。
