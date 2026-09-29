# Pydantic8567：actor/private 实际部分结果

2026-09-29。**公开两排列序列化缺陷已准确复现；gold修复原例，同时真实破坏默认配置下普通Custom+PlainValidator的类构建。G1从静态疑点转为实测；正式评分及最终用途尚未审定。**

actor四条命令完整。core2.15.0，base `8060fa1cff965850e5e08a67ca73d5272dcdcf9f`，实际原image `abbc218b579f2221817266e312e8df981459ee1cea4e5bc4f4b120942c62cf7a`。原例内部值仍为False/True，Python dump与JSON解码结果都为`{'x':'0','y':true}`，准确失败在`PUBLIC_SERIALIZER_ORDERS_FAILED`，rc1，不是导入/依赖失败。两个公开旧测选择分别6passed/158deselected（validators）与6passed/70deselected（serializers），rc0。

私有base同样复现原例；gold两种dump均变为`{'x':'0','y':'1'}`且内部bool不变。两方旧测各6+6通过。决定性兼容控制为普通`class Custom: pass`、默认配置`Annotated[Custom, PlainValidator(lambda v:v)]`：base类构建和实例验证均成功，保留输入对象身份，配置确认为`{}`；gold在**class定义阶段**抛`PydanticSchemaGenerationError`，code=`schema-for-unknown-type`，消息精确指向`__main__.Custom`。没有改为arbitrary_types_allowed，也未用任意异常代替判据。

公开依据是`functional_validators.py:130`说明PlainValidator取代内部验证，`docs/concepts/validators.md:66`明确终止内部验证；base实现不调用内层handler。gold新增无条件`handler(source_type)`，遇普通Custom进入`_unknown_type_schema`，与实际异常阶段对应。该结果证明具体兼容回归，不证明所有自定义类型或所有序列化模式都损坏；原例与既有12项通过也不覆盖这个新失败。

私有目标文件`pydantic/functional_validators.py`：base 23,387字节／SHA`15003cbbd1349882a64ce994671c223b90259cb791e6b620d97bd4ab1024113b`；gold 23,628字节／SHA`cbdbf0cf4557b0a2012621781a6a3c6e375d6821b12e939e5f6f6cb35363a5dd`。base准备4步、gold5步全0；矩阵耗时3.243/3.500秒，仅指私有子命令合计，不是正式评分成本。


## 身份、原件与清理范围

运行 `reserve6_v1_20260928T205304Z-725caa`。actor 实际 UID54321、Python3.8.19，解释器 `/opt/miniconda3/envs/testbed/bin/python`，包从 `/testbed/pydantic/__init__.py` 导入。prelaunch/activation均ok，真实 CC2.1.205 的 Bash/tool_result 逐ID配对，采集字节数逐项等于输出原件，无截断；harness 日志完整。初始 pdm.lock/pyproject.toml 两行 dirty 保留，结束 agent 进程0。actor 容器rm0、stub0、network/relay failures及前后残留列表全空。devcheck控制消息不能证明完整题面/public_hints交付或自主求解。

private 两组是独立 root UID0 行为对照，不能替代actor权限证明；同base、core和checkout导入，gold apply0。准备全部0，旧测先收集再执行；matrix和每条子命令尾标记齐全。捕获并报告目标异常的探针自身rc0，不能解释成gold无回归。两私有容器rm/query0、remaining空。actor实际配额2CPU/4GiB，private spec也请求2CPU/4GiB；无全生命周期资源事件证据，不外推无OOM。

本次新增源码SHA探针已核：private实际base文件与公开base全文SHA一致，gold文件SHA与纯文本逐hunk重建的base+原gold补丁一致。正式frozen export的跨阶段整字节对照、实际安装、全参考/完整测试与grader双层清理尚待完整结果，不把历史gold1当作本轮正式结论。此稿只确认已完成actor/private，未授予比较、训练或留出资格；D6未实施。

证据：[部分机器审计](actual_partial.json)；[actor记录](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-8567/reserve6_v1_20260928T205304Z-725caa/actor_original/attempt.json)；[private base原输出](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-8567/reserve6_v1_20260928T205304Z-725caa/private_base/base/private_matrix.out)；[private gold原输出](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-8567/reserve6_v1_20260928T205304Z-725caa/private_gold/gold/private_matrix.out)。
