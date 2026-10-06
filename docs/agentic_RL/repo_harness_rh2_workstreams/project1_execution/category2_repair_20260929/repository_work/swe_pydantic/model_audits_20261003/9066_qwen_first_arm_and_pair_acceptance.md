# 9066：Qwen 标量IP修复与两模型首轮核收

2026-10-03。**Qwen最终只对六类stdlib标量IP默认值转字符串，保留原core序列化调用；370正式参考全通过/raw1，当前公开范围内未见新阻断。** Coder同范围修复也有效、正式370全过；两模型各首次一次已完整执行和分析。容器中IP默认值仍是既有题外T3，不升级本轮评分要求，也不由两个raw1推稳定成功率或训练资格。

题主完整阅读640条轨迹中的全部非重复思考、文本、41次工具调用与返回；214封存成员、21,096,651字节及482项baseline路径/类型/执行位/内容SHA相符。五次Edit从实际baseline重建与唯一 `pydantic/json_schema.py` FP条目一致。[非作者独立复核](../reviews/non_author_9066_qwen_first10_execution_semantic_review_20261003.md)与[题主读回](../coordination_20261003/9066_qwen_pair_owner_readback_v1.json)给出版本、执行和语义范围。

| 诊断方面 | 结论和证据范围 |
| --- | --- |
| 最终源码语义 | isinstance限定IPv4/IPv6 Address/Interface/Network，先str，再执行原to_jsonable_python配置参数。其它输入仍走原调用，dataclass等行为保持；没有表格硬编码IP值。Coder先调用原core，遇SerializationError再对同六类IP返回str，机制不同，当前目标都有效，不能冒称补丁相同。 |
| 定位、错误与修正 | 实际复现IP默认值缺失后先添加过宽fallback=str。公开pytest发现Callable不再产生预期warning，模型读实际失败后撤回通用fallback，改为六类IP限定；误加未使用import随后删除。早期回归在正式FP前修复，不能归到最终候选，也不能把中途的pipe exit0当作测试通过。 |
| 完整候选与验证 | 26Bash/10Read/5Edit，无Write或临时文件留下，无正式测试修改。一次动态类缺类型注解的工具错误在下一调用补__annotations__纠正；六类IP打印检查不是失败即退出断言。后续Callable8项及公开选择380PASS/1SKIP/1XFAIL支持纠错，最终可信370另核。最终“全部测试”表述只能指实际所选范围。 |
| 评分、公开要求与隔离 | 真实install0/test0、原2F2P和368P2P全部PASSED，无参考missing/skip。新增stdlib dataclass默认实例保护通过，原raw1、FP摘要 `e4c40db9…`保持。原公开六类标量IP行为是目标，列表/容器递归处理不被默认为本轮新保证。首HTTP原题面精确匹配，私有有效patch和新增节点标记未出现在完整请求中。 |
| 环境及误判撤回 | code_v8、basea3b7214a…、精确2241ad13…镜像与Coder一致，同482项baseline canonical `358bf444…`，Python3.8.19/core2.16.3，UID54321/54322，实际/testbed导入与可信前置通过。题主早先疑似pytest/Faker版本变化的线索在权威原轨迹中不存在，明确撤回；前后pip_freeze字节相同，SHA `b88b1934…`，pytest7.4.4/Faker22.2.0不变。whole3600/setup300/apply120/test1800及env qualification absent保持。 |
| 效率与并行 | 39生成、零count_tokens、41工具/CC42回合，按同一message.id合并为三个2工具并行组，其余串行、无子agent。累计输入570297/输出8676，共578973 token，单次输入峰26279。首Edit16.087秒，solve75.367秒、CC70.891秒/嵌套API54.889秒，grader209.393秒；安装2.105秒/测试3.681秒不重复相加。更短的单次轨迹不是稳定效率结论。 |
| 服务、资源及收尾 | 派发前实际捕获Qwen3.6 engine/adapter CID、PID、restart0、只读revision及真实HTTP/配置；37实际文件大小核实，未重复权重哈希或证明显存字节。actor6/grader13有限采样，短安装/pytest各零采样，缺口未知；report峰678.996MiB单独保存。actor/relay/network无残留、drain active0、manager1建1删，exact PID1成功14:24:49.445815 UTC；不使用not-found默认0或声称全宿主无其它作业。 |

完整执行、当前范围源码和候选交付可以核收，原件中的历史owner pending与pair未闭合不回填。配对receipt证明各首次执行完成；接受范围依赖本报告与旧Coder结论，不推typed训练消费、跨环境稳定性或模型胜负。当前没有具体缺陷要求新材料、CPU或模型调用；后续重复仍按覆盖门槛另排。
