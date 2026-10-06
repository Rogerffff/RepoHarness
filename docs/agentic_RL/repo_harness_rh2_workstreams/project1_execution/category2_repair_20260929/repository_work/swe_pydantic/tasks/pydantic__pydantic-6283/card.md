# Pydantic 6283 当前题卡

2026-10-03。**离线修订已准备，待非作者核查、正式登记和CPU验收。**

题面要求同一合法值经RootModel正常构造与model_construct所得实例相等。原参考只查42。既有TextRoot合法字符串控制已实测base不等、gold与validate_construct相等；正式原矩阵为noop0／gold1／validate_construct0，后者被既有 `test_construct`／`test_construct_nested` 的无验证护栏正确拒绝。[CPU与非示例证据](../../../../../swegym_cpu_preprobe_20260929/tasks/pydantic__pydantic-6283/result.md)。

本轮保留原1 F2P＋38 P2P，追加 `test_root_model_construct_equality_nonexample` 为F2P，直接采用已有TextRoot字符串实例；不要求内部字典形状，不重新验证输入。完整[有效补丁](effective_test.patch)与[修订单](revision.json)已经静态检查。

新正式矩阵预期仍为0／1／0。validate_construct在新增合法字符串断言上预期通过，但必须继续因旧无验证护栏失败，不能删旧P2P。Python3.8/core0.42.0身份、原actor行为与安装证据可复用，换宿主及新材料验收另核；尚未证明示例42特判候选的实际误奖。新评分、独立核查、实际公开交付和探针尚未做；不新增用途准入。
