# 10174：Coder首轮轨迹与两模型比较

2026-10-03（Asia/Singapore）。作业 `gpu1003-mypy10174-coder-a1` 正常完成，实际安装与测试退出0，正式1F/3P四参考全部通过，原reward1。完整求解、候选及清理已回读；[冻结JSON](coder_first_arm_trace_20261003.json)记录2,783项原件检查、560个引用及逐工具索引。闭包552件、75,526,063字节全部核SHA。旧Qwen求解、安装失败及后来同候选重评分分别保留，这次只增加Coder首轮一次观测。

## 修法与真实根因

公开症状是非strict-optional模式下 `Optional[Any]` 的成员检查误报。底层 `meet.is_overlapping_types` 先检查Any，再去除Union中的None；`Union[Any, None]` 到第二步才成为Any，已经错过早期返回。这是源码顺序问题；Coder多次把Any检查说成发生在去None之后，最终又称底层已正确处理，根因解释不准确。

Coder第10个工具定位 `dangerous_comparison`，第19–22个工具读取底层overlap和 `relevant_items`；在第49个工具给 `mypy/checkexpr.py` 增加8行。在既有双Union分支之后，非strict-optional时先用 `relevant_items` 去None，再把简化后的类型交给底层函数，因而底层能直接看到Any。它没有修改 `mypy/meet.py`，也没有直接关闭严格比较。原None、双Union、bytes、白名单和strict模式的控制结构保留；实际负例仍报告Optional[str]不重叠。

[Qwen首轮](qwen36_first_arm_trace_20261003.md)采用另一种修法：在底层去None后再次检查Any。两种候选源码不同，不能借用另一模型源码语义作字节相同的验收。当前公开症状、模型边界例和正式四参考支持两者在本题范围内成功；不据此声称所有overlap调用点或全部mypy行为等价。

## 定位、工具和纠错

轨迹809条JSONL、117条assistant事件，对应68个不同生成消息、67个工具调用：Bash41、Read14、Write10、Edit2。每次生成最多一个工具，未观察到工具层并发。pytest `-n2` 属于测试进程并行，不是模型同时调用工具。

Coder前半段多次广搜代码，再反复阅读相同分支。第6个工具整读 `messages.py`，返回约108KB，使下一请求输入从4,426增至32,655 token。第24个工具的debug文件没有成员表达式，未复现问题；第26次生成却错误归因为没有strict-equality开关。第30–38个工具在 `mypy/test/*.py` 内找数据驱动case，连续空结果，两次退出123；它没有切换到实际case数据目录。上述行为解释了部分多余回合，不是基础设施失败。

[实际工具交付补证](coder_tool_delivery_supplement_20261003.json)逐项核了67个工具名称。核心第49个Edit的old/new字符串在adapter、SSE和实际轨迹中精确相等，既有AbstractSet分支保留；另有两处cd前缀、四处Write行尾空白及默认replace_all的差异，不声称所有参数对象字节一致。

12个错误标记须分列：修前复现诊断5次（2/25/27/29/45），修后预期负例4次（51/55/63/64），测试搜索无匹配2次（37/38），最后一次无变化Edit（67）。第43个工具通过 `api.run` 读到诊断退出1，但外层Python成功，因此不在12个错误标记中。第67个工具试图用完全相同的新旧字符串编辑初态依赖文件，被工具拒绝；原FP未包含该修改。

## 自验证的有效范围

第50和66个工具分别验证公开复现与最终复现无误报；第51个工具保留Optional[str]负例，第52个工具确认Optional[int]仍可成员比较。第54/55、56/57个工具新建未含no-strict-optional的文件，实际默认strict模式分别保留负例和正例。

第53个工具使用原文件时仍受内联no-strict-optional控制，不能充当strict模式对照。第64个工具重用comprehensive文件也没有改变其内联配置。第63/64个工具实际只有Optional[str]错误，模型随后却宣称Union[str,float]也有预期错误，与输出不符。这些是验证设计与结果解释不足，不改变正式评分原件。

模型自己的公开pytest输出为：修前指定Tuple组1通过，修后同组1通过；strict选择125通过、container选择6通过、equality选择41通过。后三个命令使用head管道，没有pytest独立数字退出回执；输出含完整通过footer，但选择组可能重叠，也不是全套测试。因此最终“全部既有测试通过”是范围过宽的声明。模型没有修改受保护的测试；正式四参考由受信评分独立执行，不依赖这些自验声明。

## 候选、评分与清理

原FrozenPatch规范摘要 `172bffdc…7c80`，66项全部进入投影：55项普通 `.mypy_cache`、10个开发脚本及 `mypy/checkexpr.py`。完整1472项基线逐内容SHA、文件类型与执行位核实，actor/grader census字节相同；与原Qwen的1472行内容相同，baseline规范摘要因runtime镜像身份不同而不同。没有删缓存、换成手工净化补丁或把裸仓库diff替代原候选。

actor与grader均实际使用80418df权限修复镜像，入口为code_v8。正式材料、公开任务block、脚本、三分区四参考和预算与适用Qwen证据相符；Qwen最初求解仍发生于旧32f镜像/code_v4，不能说两次求解整个运行条件相同。可信恢复/保护完整，runner前后摘要相同，实际导入 `/testbed/mypy/__init__.py`；没有pytest进程内checkexpr模块摘要的额外自证。

完整评分日志支持三项安装命令成功、editable构建与安装成功，无Permission denied或失败标记；candidate、安装末命令与测试退出均0。逐成功安装命令的独立数字RC缺席，不能将末命令0泛化为逐项数字回执。实际收集9423项、选中4项，全部PASS：

- 原F2P `testOverlappingAnyTypeWithoutStrictOptional`。
- 原P2P `testUnimportedHintAnyLower`、`testUnimportedHintAny`。
- 新P2P `testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional`。

完整footer为4 passed / 9419 deselected，无缺失、跳过或段外解析。actor正常end_turn/harness退出0，gateway撤销并drain、active0、进程及工作区quiescence完整；actor容器/网络/relay清理和grader 1建1删、无open或failure均有原件。执行者pair回执的safe_closed与评分原件分列，不拿已收集unit的默认ExecMainStatus0证明成功。

## 模型来源与效率

任务启动前0.591秒完成实际服务读取，开跑前同一capture内两次读取的engine/adapter ID、启动时间和restart0相同；这些读取不构成题后连续性证明。实际只读挂载对应 `Qwen/Qwen3-Coder-30B-A3B-Instruct`、revision `b2cff646…f42d120`。下载manifest列25个文件，实际尺寸相符；声明28项但未列的3项仍未知。68条生成请求、adapter响应、SSE及usage对应成立，另有1次count_tokens，不计生成。原gateway的checkpoint核验false保留；HTTP revision/checksum为null，没有逐权重重算或GPU内存权重证明。闭包的backend日志在本次求解前采集，不声称它覆盖本题68次后端完成记录。上述仅支持有限运营来源归因。

| 指标 | Coder首轮 | Qwen首轮 |
| --- | ---: | ---: |
| attempt记录求解秒 | 150.336 | 273.650 |
| CC记录秒 / API总秒 | 146.652 / 125.271 | 270.101 / 125.916 |
| 生成 / 工具次数 | 68 / 67 | 87 / 86 |
| 累计输入token | 2,869,312 | 2,234,730 |
| 输出token | 12,327 | 19,196 |

Coder单次最大输入55,361、输出1,804，全部生成请求上限65536，正常结束，没有上下文恢复或预算截断。CC报告的32000模型描述字段不是实际请求上限。Coder累计输入更多，主要包含多轮重复上下文，不能视为单轮上下文长度。其14.654735美元为CC别名估价，不能当实际GPU账单。

Coder attempt含准备及收尾191.644秒，另有评分93.986秒；CC、API、求解时间存在包含关系，不能相加。两模型本次API总时间相近，但自验工作量明显不同：Qwen执行了更广的testcheck/meet组，Coder只选少量公开组。镜像与消费者也不同，单次耗时和token不用于速度、价格或稳定性排名。

## 当前用途

两模型在本题正式四参考均成功，没有二元成败分歧；定位反复、配置对照错误和自验证表述过宽提供行为分析线索，但不能单题断言训练饱和或训练收益。保留两个首轮及Qwen原FP环境恢复记录，稳定性仍未知，训练/留出资格未授予。按当前覆盖优先安排不重复求解、不追加普通采样；题级配对验收与总账收口见后续固定记录。
