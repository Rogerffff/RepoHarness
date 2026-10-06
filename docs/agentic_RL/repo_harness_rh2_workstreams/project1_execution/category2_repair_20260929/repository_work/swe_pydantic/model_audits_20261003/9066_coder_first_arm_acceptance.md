# 9066：标量 IP 默认值修复有效，首 Coder 成功核收

2026-10-03。**公开目标源码修复有效，正式370项参考全部通过，保留原奖励1。** 候选在默认值编码失败后，仅对六种IP类型返回字符串，保留原core编码调用和dataclass默认实例行为。未发现当前公开范围内的决定性漏修、评分绕过或回归；已知容器内IP默认值限制仍是题外T3，不据此重跑CPU或新增本轮评分条件。

题主完整阅读404条原轨迹对应2011行非重复正文、34次工具及返回；逐件核368件封存成员／23,336,197字节、482项baseline、完整FP和370参考。[独立执行与语义复核](../reviews/non_author_9066_coder_q24_execution_semantic_review_20261003.md)通过并获核收；[题主读回](../coordination_20261003/9066_coder_first_arm_owner_readback_v1.json)保存绑定。权威为`closed_snapshots/gpu1003-pyd9066-coder-a1`；旧remote兼容副本不覆盖它。Qwen首次结果待，整请求仍claimed，不ACK、不清活动指针。

| 诊断方面 | 当前结论与证据范围 |
| --- | --- |
| 目标源码语义 | 只有`GenerateJsonSchema.encode_default` AST变化，原`to_jsonable_python(dft, timedelta_mode=..., bytes_mode=...)`调用AST完全保留并先执行。仅捕获`PydanticSerializationError`，对IPv4/IPv6 Address/Interface/Network返回str，其他类型继续raise。既有IP schema已用to_string serializer，修法有源码依据；没有字段／地址字符串硬编码、任意类型TypeAdapter重建或奖励改写。公开IPv4和正式IPv6默认值F2P均通过。 |
| 完整候选与验证 | FP五项为json_schema.py及四个新增root复现／诊断脚本，没有修改正式tests或fixture，五项全部投影运输。原复现、普通默认值、自写2个pytest测试和原test_schema_class1项真实通过，工具无错误。但两次`pytest ... | head`主动截断，不证明完整模块通过；模型最终“全部既有测试通过／完全向后兼容”过宽。IPvAnyAddress注解下的IPv4Network默认值未验证，只证明该默认值编码，不证明地址验证接受Network。 |
| 评分一致性 | install RC0、test RC0；2F2P＋367原P2P＋1新增dataclass P2P逐完整ID均PASSED，无missing／skip。完整文件摘要383 passed／1 skipped／1 xfailed与370正式参考分母不同。原parser377键包含非参考空白参数截断限制，不能据此声称完整pytest语法已修复；正式370逐键一致，原分不失真。482项tar路径／内容／规范执行位、actor→grader census及原FP`78a3a6f0…`保持，正式命令没有收集四个root脚本。 |
| 公开要求与求解依据 | 首HTTP原题面块逐字节一致，保留原22处CRLF；没有新增hints，private有效patch／新增保护标记未进入HTTP正文。模型从warning路径定位default_schema和encode_default，读取既有IP schema，再直接确认core编码IP报错而str可行，形成可追溯根因链。仅补顶层标量IP，`List[IPvAnyAddress]`等容器IP默认值仍预计遗漏；旧诊断已列题外T3，不扩成本轮阻断。 |
| 环境与运行身份 | queue_v24／题级code_v8，actor与grader同`2241ad13…`精确镜像，Python3.8.19/Pydantic2.7.0a1/core2.16.3。actor UID54321激活、prelaunch和公开wheel逐SHA可读；grader UID54322固定前置和真实editable／testing requirements安装成功，源码导入正确，runner前后摘要相同。probe-wide-v1和whole/setup/apply/test3600/300/120/1800保持，没有超时；baseline环境digest仍null，不补造typed资格。 |
| 效率与并行 | 35生成HTTP/SSE＋1 count_tokens均200；34工具为18 Bash、11 Read、4 Write、1 Edit，全串行、无子agent、无工具错误或生产修法重试。累计输入521938、输出4806、合计526744，最大单请求输入27907。首HTTP到唯一生产编辑18.623秒，solve51.109秒，CC47.557秒及嵌套API39.620秒不相加。大段标准类型源码、重复读相邻片段和末尾既有依赖diff增加上下文；部分独立检查可批量，但不虚估节省比例。 |
| 模型来源、资源与清理 | 派发前实测engine／adapter、只读固定Coder revision `b2cff646…`和真实HTTP服务关联获独立复核；所谓after inspect仍是派发前capture后的读回，不是作业结束后checkpoint证明。adapter使用code_v4服务，与题级code_v8分开；原checkpoint false/config_only字段保持，未重算权重或显存哈希。22个离散采样按CID/run关联actor6、relay6、grader14；actor1条资源null保持空值，安装2.083秒／测试3.581秒各0采样，间隙未知。report峰值684.5与外部采样分开。quiescence、drain active0、actor/relay/network及manager1建1删无本job残留，未现场重查全宿主。 |

`pdm.lock`／`pyproject.toml`在solver启动前已dirty，并非本次FP改动；模型的“依赖更新”解释不作为环境修改证据。四个临时文件保持原字节，本轮仅本地静态读回，无新CPU/GPU/模型调用。后续沿原固定请求排Qwen首次臂；单次成功不证明稳定成功率、通用模型能力、训练或留出资格。
