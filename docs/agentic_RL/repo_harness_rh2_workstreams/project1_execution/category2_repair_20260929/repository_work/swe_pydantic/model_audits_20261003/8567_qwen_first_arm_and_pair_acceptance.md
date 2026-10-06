# 8567：两模型的 inner schema 回归与首轮核收

2026-10-03。**Qwen与Coder都改善公开bool示例，却无条件生成内层schema，正式各有2F/2P失败，原分均0。** 这是候选行为回归，现有材料准确拒绝；暂未见需要新CPU或材料改版的证据。Qwen原FP只有源码，没有Coder那两个失败临时脚本的交付缺陷。两模型首次执行和题主分析已完成，训练资格和重复稳定性仍待。

题主完整阅读551条原轨迹中所有非重复思考、文本与33次工具调用/返回，包括functional_validators和serializers完整源码；204封存成员、21,130,321字节与458项baseline已核SHA/类型/执行位。唯一生产Edit从真实baseline重建与原FP一致。[非作者复核](../reviews/non_author_8511_8567_qwen_first10_execution_semantic_review_20261003.md)、[题主读回](../coordination_20261003/8567_qwen_pair_owner_readback_v1.json)及[原Coder报告](8567_coder_first_arm_acceptance.md)分别保存语义和交付结论。

| 诊断方面 | 结论和证据范围 |
| --- | --- |
| 目标与语义回归 | Qwen先 `handler(source_type)`，再抽取serialization挂到plain函数schema。它保留了bool serializer，却让PlainValidator无法跳过不支持的内层类型。原F节点在Unsupported部分失败，新Unsupported两顺序F也失败，未知forward和stdlib typing.TypedDict两个P失败。与Coder同一无条件handler机制，组织和FP字节不同。 |
| 思考与纠错 | 多轮混淆构建时handler与运行时validator的作用，调试打印后只确认PlainSerializer已挂但被PlainValidator覆盖；未进一步验证“不生成内层schema”的语义。初次Python3.8不能从typing导入Annotated，改用typing_extensions修正。这项环境使用纠错不解释正式四失败。 |
| 完整候选与自测 | 26Bash/6Read/1Edit，无Write，验证为inline脚本，没有临时文件留在FP。公开bool两顺序、with-info、before validator与TypeAdapter示例通过；公开所选旧测试通过，不能替代Unsupported/forward/stdlib TypedDict保护。候选最终无公开测试修改；Coder两个失败文件仍按原FP另记，不因Qwen交付更干净而消除。 |
| 评分一致性与公开依据 | 真实install0/test1，158正式参考PASS、四项FAIL，formal162全部有终态，无参考missing/skip。整个测试文件164PASS/4FAIL分母不同。外层entry0与shell0不改pytest1，正式raw0优先于一次根摘要误写Qwen1。公开PlainValidator即替代内层验证，当前三个新增节点没有扩成新公开保证；首HTTP题面相同，私有补丁和新增标记未交solver。 |
| 版本与环境 | code_v8、base8060fa1c…、精确bc5d796f…镜像与Coder一致，同458项baseline canonical `eb494e76…`；Python3.8.19/core2.15.0、UID54321/54322及实际/testbed导入、可信安装/测试恢复保护通过。旧安装及保护infra/null不回写。前后freeze相同，whole3600/setup300/apply120/test1800保持；env qualification absent仍非训练验收。 |
| 效率与并行 | 34生成、零count_tokens、33工具全串行、无子agent、一次工具error。累计输入897628/输出10466，共908094 token，单次输入峰41980；长源码阅读与重复解释放大上下文。首生产Edit41.907秒，solve99.884秒、CC95.359秒/嵌套API68.708秒，grader177.341秒；安装2.621秒、测试3.309秒。没有超时/OOM证据解释正式失败，不推算串行工具的假定并行节省。 |
| 服务、资源与清理 | 派发前14:14:02.597→.784 UTC实际捕获 Qwen3.6 engine/adapter身份及只读revision，配置/HTTP关联通过。37文件大小核实，不作权重SHA/显存字节证明。actor8/grader12采样，安装1点、pytest0点，缺口未知；report峰647.934MiB分开。actor/relay/network无标签残留、drain active0、manager1建1删；exact PID1成功14:19:11.095131 UTC，retired unit默认0不作退出证明。 |

原FP摘要 `0f494797…`、四个失败节点和原分0保持。此次核收的是完整执行与回归判断，既有负结果可用于题目诊断，不能称模型修复成功或授予训练/留出资格。两模型各一次完成不等于稳定失败率；后续重复服从全局覆盖门槛，本轮没有新增模型或CPU调用。
