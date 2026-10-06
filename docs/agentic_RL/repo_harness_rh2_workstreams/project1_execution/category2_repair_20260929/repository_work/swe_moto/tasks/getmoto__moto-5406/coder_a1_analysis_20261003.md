# Moto5406：Coder 首轮源码与轨迹分析

2026-10-03。`gpu1003-moto5406-coder-a1`，Qwen3-Coder-30B-A3B-Instruct。原分1，安装／测试真实rc0，1F与27P逐项通过。实际FrozenPatch的region修法符合公开问题，未发现需要再修本题评分或题面的缺陷。本轮与原Qwen首轮共同完成当前请求的两模型首次覆盖；每模型仅一次，不证明稳定性或训练资格。

原FP含`moto/dynamodb/models/__init__.py`修改及新增`FIX_SUMMARY.md`，两项均100644，canonical digest `ba30ae7ae05b4c113c5cb1c849c2dff91b7124c2c173562e448c2a1e4e1125f7`。作者核完整1685项baseline tar的类型、执行位和内容SHA；源码与原baseline恰好三处region修改，不改测试或私有材料。Table保存constructor的region，ARN取此region，StreamRecord取同一Table的region；原backend实际通过`region=self.region_name`创建Table。修法使用实际地域，East1行为保留，没有替换成另一个地域常量。额外说明文件没有改变执行行为。

轨迹240条事件均解析，逐一核18个工具请求与18个结果。第10条创建公开复现，23／27条实际失败为East1与East2 ARN不符。49／53条一次全文Read 1872行模型源码，58条首次明确定位ARN常量及constructor未保存region；62、75条修改Table后，88／92条原复现通过。101／105条East1标准测试通过；114／118条错误节点`test_dynamodb.py::test_create_table`退出4、零收集，127条查目录、140／144条恢复到原create_table文件12项通过。153条自拟三地区ARN测试，162／166条三项通过。175／179条读StreamRecord，188条同步修正awsRegion；201／205、214／218条重跑原复现和三地区ARN均通过。227条写说明，236条最终答复，正常end_turn。

原复现被完整交付，模型实际看到了失败及通过结果。最后修改StreamRecord后，模型没有显式检查stream事件awsRegion；修法的静态数据来源一致，但ARN自测不能冒充stream行为覆盖。模型自测只是一个原标准节点、create_table文件12项与自拟三地区，不是全部DynamoDB测试。`FIX_SUMMARY.md`及最终答复的“全部既有测试通过／无回归／无副作用”超出证据，应记录为回答夸大。正式评分另在可信还原测试下完整28项通过，不据这些宽泛文字判定正确。

| 指标 | 本轮实际值 |
| --- | ---: |
| solver墙钟 | 58.800秒 |
| CC回合／gateway生成／adapter生成 | 19／19／19 |
| 工具调用 | 18：Bash10、Read2、Write3、Edit3 |
| 真实工具错误结果 | 2：原复现失败、误选节点退出4 |
| 累计输入／输出token | 493835／5192 |
| 单请求最大输入／输出token | 36268／1569 |
| 独立候选安装／测试段 | 2.572／2.942秒 |

读1872行扩大后续上下文，误选节点造成一次无效验证；最后额外说明文件也增加输出，但无需为此重跑。18个工具均逐消息单个调用，没有多工具batch。可独立的源码定位或互不依赖验证存在合并机会，但本轨迹不能证明执行重叠、加速或执行器能力不足；没有逐工具开始／结束时刻，记并行收益不可判断。源修改和后续复现必须按依赖串行。

manager原记录grade总计227.755秒、env reset12.696、prep0.439、test6.110、该manager队列等待0；trusted setup207.715秒为另一诊断阶段口径。不能相加当solver时间、用差额解释模型效率，或把manager等待0当全局GPU未排队。实际宽预算context196608、max_new_tokens65536、240回合、10800秒、1024请求、first-byte1800／idle TTL14400；grade setup900／apply120／test1800／whole3600。CC元数据32000不替代实际HTTP65536；无压缩、length终止或预算截断，CC costUSD是元数据估算，不是实际额外API账单。

本臂冻结code7，source manifest `be705a777484c70af2afe9a34b6dd288bd85c2b1f536c6d57bd59aecb4eb0352`。实际image `808c60d962cb94330e499404720a0813fa400a2e86464aabdb47fcaa05aad5f6`，材料identity `c50ae6995399541699c041b82e91e55b08a7236e14d820b64c1ddad106687032`。首HTTP完整prompt、固定模型／adapter配置和现场只读model挂载绑定已由执行独立报告核，本臂启动前实际capture为07:06:39 UTC，不能改称旧Qwen作业现场证据；25个权重文件数量／尺寸检查不是重核所有权重内容或GPU内存hash。

作者核闭合136件／32977866 bytes，全部SHA和长度匹配；完整原安装段与已全文读过的Qwen首轮只差结束时间戳。原短摘要28行逐参考全部PASSED、安装0；actor与relay/network清理、gateway drain、pre-drain residual0及manager创建／移除1均核，无本臂残留。24个资源快照仅有限采样，actor7／relay7／grader15，短安装和测试期间没有采样点；787.688MiB报告峰值不证明正式测试最低内存或全程无OOM。不是全GPU资源审计，typed actor资格absent保留。

原件根：`runs/ordinary_gpu_probe_20261002/remote/queue_v21/results/gpu1003-moto5406-coder-a1/`。执行独立报告SHA `882f513564194a63347ec62700b369f7647756998a49aad3ae51df38ca83c83c`；题主读回位于`runs/category2_repair_20260929/moto_cpu_20261003/moto5406_coder_a1_owner_readback_20261003.json`，SHA `bcc6ab2209b7a024bbbcd016c65965626f0dbba7ce1e933b3040469ac7f077dd`。两模型差异与当前收口见[首轮比较](two_model_first_round_analysis_20261003.md)，无需新增修订或重复样本。
