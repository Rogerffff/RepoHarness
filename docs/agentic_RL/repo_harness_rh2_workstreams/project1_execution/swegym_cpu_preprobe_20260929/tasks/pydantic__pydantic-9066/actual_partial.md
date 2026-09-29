# Pydantic9066：actor/private 实际部分结果

2026-09-29。**IPv4默认值的schema缺失和警告已准确复现；gold修复原IP例，同时真实使标准dataclass实例默认值的schema生成抛配置错误。G1从静态疑点转为实测；正式评分及最终用途尚未审定。**

actor三条命令完整。core2.16.3，base `a3b7214a1d6ac8e32c29e9d4436ea6a9e253ead7`，实际原image `5a05759a5549cc7d65c471fb5d57d8fc554485b6c178a389a1fd373111ff3f4d`。IP原例schema保留format=`ipvanyaddress`/type=`string`但无default，并准确捕获`PydanticJsonSchemaWarning`的`non-serializable-default`消息；命令随后在`PUBLIC_IP_DEFAULT_FAILED`断言失败，rc1。不是IP输入解析失败，也不是异常类型不明。旧IP schema九项全部通过、373deselected。

私有base同样复现IP症状；gold实际schema含`default:'127.0.0.1'`、format/title/type保持、无警告，旧九项仍全过。标准库`@dataclass class D: x:int`作为`Model.data: D = D(1)`的对照固定`model_config=={}`，模型默认实例本身可构建。base的`model_json_schema()`成功，`properties.data.default == {'x':1}`、含D引用定义且无警告；gold在**model_json_schema阶段**抛`PydanticUserError`，code=`type-adapter-config-unused`，消息明确不允许给BaseModel/dataclass/TypedDict的TypeAdapter传config；警告列表仍空。没有通过改变配置绕过结果。

公开base支持标准dataclass schema（如`test_nested_python_dataclasses`）和通用默认值编码。gold新增对无`__pydantic_serializer__`对象调用`TypeAdapter(type(dft), config=config.config_dict)`，其空配置仍是非None；`type_adapter.py:193–204`会对dataclass抛上述错误，gold只捕获SchemaGenerationError，外层default_schema也只捕获SerializationError。实际base成功/gold精确失败支持这条已定位回归；不是要求内部字典必须具有某种新形状，也不从gold推导公开需求。旧九项测的是无default的IP schema，不能替代dataclass默认实例覆盖。

私有目标文件`pydantic/json_schema.py`：base 103,160字节／SHA`f5b675891b23ab3ce275db9d30f9a871bb01691bd0f4ce60912e14c71950f16e`；gold 103,620字节／SHA`1dcdfe4f2143ae0b089030c5bc98332f99fd0d686cffa23a9cbeb2ce51126c80`。base准备3步、gold4步全0；矩阵耗时2.390/2.460秒，仅指私有子命令合计，不是正式评分成本。


## 身份、原件与清理范围

运行 `reserve6_v1_20260928T205304Z-4f3c46`。actor 实际 UID54321、Python3.8.19，解释器 `/opt/miniconda3/envs/testbed/bin/python`，包从 `/testbed/pydantic/__init__.py` 导入。prelaunch/activation均ok，真实 CC2.1.205 的 Bash/tool_result 逐ID配对，采集字节数逐项等于输出原件，无截断；harness 日志完整。初始 pdm.lock/pyproject.toml 两行 dirty 保留，结束 agent 进程0。actor 容器rm0、stub0、network/relay failures及前后残留列表全空。devcheck控制消息不能证明完整题面/public_hints交付或自主求解。

private 两组是独立 root UID0 行为对照，不能替代actor权限证明；同base、core和checkout导入，gold apply0。准备全部0，旧测先收集再执行；matrix和每条子命令尾标记齐全。捕获并报告目标异常的探针自身rc0，不能解释成gold无回归。两私有容器rm/query0、remaining空。actor实际配额2CPU/4GiB，private spec也请求2CPU/4GiB；无全生命周期资源事件证据，不外推无OOM。

本次新增源码SHA探针已核：private实际base文件与公开base全文SHA一致，gold文件SHA与纯文本逐hunk重建的base+原gold补丁一致。正式frozen export的跨阶段整字节对照、实际安装、全参考/完整测试与grader双层清理尚待完整结果，不把历史gold1当作本轮正式结论。此稿只确认已完成actor/private，未授予比较、训练或留出资格；D6未实施。

证据：[部分机器审计](actual_partial.json)；[actor记录](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-9066/reserve6_v1_20260928T205304Z-4f3c46/actor_original/attempt.json)；[private base原输出](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-9066/reserve6_v1_20260928T205304Z-4f3c46/private_base/base/private_matrix.out)；[private gold原输出](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-9066/reserve6_v1_20260928T205304Z-4f3c46/private_gold/gold/private_matrix.out)。
