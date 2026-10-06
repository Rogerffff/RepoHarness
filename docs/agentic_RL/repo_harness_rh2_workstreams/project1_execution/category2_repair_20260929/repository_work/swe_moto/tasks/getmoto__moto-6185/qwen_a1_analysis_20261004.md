# Moto6185：Qwen3.6 首次结果与轨迹分析

整理：2026-10-04；运行原件日期为2026-10-03 UTC。`gpu1003-moto6185-qwen36-a1` 原分1，安装／测试实际退出0，1F／34P参考齐全、实际36项全过。题主源码与轨迹核对确认当前目标正确；与已分析Coder形成双模型首次0／1；Coder是公开嵌套漏修的有效0。没有新增solve、CPU重跑、材料发布或普通追加；单样本不证明稳定、模型排名或训练资格。

## 实际绑定与完整性

权威原件为 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-moto6185-qwen36-a1/`，queue_qwen_next12／code8。closed manifest SHA `9a2ca2947a7cfcebbc5abaf5fb7f9f41c94150ad874a9e9e2da67a0d6c765fb8`，437成员／93,392,850字节逐项SHA、尺寸相符。它含共享及前序依赖，不是437次模型实验，也不能与Coder包直接相加。输入manifest `2f20d2710e4700274b463bd6471890991d8a71ee4b732134e2592e8c09c07231`。

固定请求 `swe-moto6185-nested-s-r13-20261003-v1` SHA `4c77bb434b8300040ef0075dd86ddd3de25aea46975bbac1ecc29e73276f3b19`，两份实际copy与原输入逐字节相等；public／environment／grading／materials身份、base commit、有效test_patch与固定请求相符。材料 `moto6185-nested-s-v3`，actor与grader实际镜像 `sha256:79d39d611186289b10956c2f845af1272218a1f4cf8fc00382c7c6ab4eced35d` 与CPU和Coder相同。全部baseline entry与Coder相等；完整实际首HTTP包含原题面和中性brief，delivered prompt逐字节等于Coder，保留原换行核验。profile只有批准的模型网关端口差异。

实际ctx196608／输出65536／CC240回合／wall10800秒／HTTP1024／first1800／idle14400；评分whole1800／setup300／apply120／test1800，两模型相同。全部生成HTTP max_tokens65536，正常end_turn；CC摘要的32000记账字段不覆盖实际预算。host eval前缀 `pytest -n0 -rA` 与展开实际测试文件分别核对。

完整正式footer `36 passed, 172 warnings in 2.38s`，安装4.744秒、测试3.04秒；candidate段完整、实际exec/install/test均0，没有infra、missing或skipped。原两条参数名带空格的实际PASSED行合为一个既有解析参考键；36实际项与35解析键分别核对，不修改parser。

## 最终修法与当前范围

最终FP只修改 `moto/dynamodb/models/table.py`，regular／100644、43708字节、内容SHA `029b06653273cec9aff8b1c9c217f220e7716dcad176dff67f2319fc0a526610`。完整2003项baseline与Coder内容、类型、执行位一致；341、589、631、719、747、803、817、873、929行九次Edit顺序重放，精确得到最终FP。所有临时脚本在/tmp，不投影到FP，未改正式测试。

实际修法逐个检查属性值包装：单M先展开为map成员，再按属性值继续处理；单L沿用DynamoType处理；S／N／B包装的dict值拒绝，N和S的int恢复SerializationException。属性名本身可以叫S，所以顶层、map中的S NULL、S string、S map均不会仅因名字被拒绝。正式目标完整执行到结尾，保护顶层string／NULL、公开嵌套NULL、深map、列表中的map、五层map、S本身持map、键名M、完整get_item原值，以及其它map成员N int和非键S dict的错误代码／消息；全部通过。当前目标正确，无需材料或环境修订，不把Coder正常0改成infra。

新增is_type_annotation参数在所有递归调用中都为False，没有True调用；其True分支中的NULL／BOOL／sets／M／L验证因此不可达。当前实际正确来自单M包装展开及属性值包装检查，不能照搬末答“完整上下文跟踪”作为一般类型验证保证。L分支不递归检查内部类型，未保护的畸形list、其它类型标记、五层以上穷举与实际AWS均不新增资格或CPU任务；遵守既定停止范围，不为猜测扩大材料。

## 定位、迭代与自测质量

11–67行定位并读库版本；81／85行原公开顶层S None实际SerializationException，唯一被工具标错的失败是有效修前复现。之后读取response、backend、table和_validate_item_types，277／291／323的debug与raw程序宽泛catch观察。341行首改用类型键形状豁免；355原例通过，439／443未安装pytest-timeout参数被head掩盖，453／457只看见4个put_item节点通过，467／473原文件159通过、483／487另一文件27通过，均没有修订目标的新增map保护。

497／501exceptions实际1 failed／33 passed，S dict错误落成AttributeError；557和617的临时程序把“任意异常”打印为OK，不能满足SerializationException要求。589、631修改后659／665原exceptions43通过，675／681原文件159通过，但691／695多案例脚本打印嵌套S NULL失败、退出仍0。719再改后733／737同一失败仍在；747改成展开M才让公开嵌套成功，却在775／779、789／793重新暴露S dict AttributeError。803、817修正结构值检查，831／835脚本打印通过和预期ClientError；845／849原wrong_datatype仍失败，873补N int后887／891孤立节点通过，901／905原S int仍失败，929补S int后943／947孤立节点通过。929以后没有源码变化，957／963exceptions43、973／979原文件159、989／993range文件29的footer通过。

1031／1037原DynamoDB目录实际输出末行为“434 passed, 2815 warnings in 23.74s”；这是可见footer、与前述文件重叠，tail不能证明434个逐节点状态或原pytest退出，也不是正式修订36项的替代。1003脚本组合仍宽泛catch，打印“ALL TESTS PASSED”不代表严格回归oracle。正式grader另执行完整修订目标和原34P，避免只看模型结语。

1051行完整轨迹、73回合、72工具：Bash50／Read13／Edit9，全部单工具串行，调用及结果逐ID对应。标错只有修前81，但未标错的错误参数、catch内错误、691与733打印嵌套失败、497／845／901真实pytest失败均保留。没有模型运行重试，源码迭代不另计attempt，没有量化每工具时间或并行收益。定位／验证较反复，末答没有交代这些中间失败；最终源码和正式成功均独立核对。

## 运输、运行成本与服务证据

HTTP73条为73生成＋0count_tokens，全部200；每条生成SSE的start／delta／stop齐、usage与adapter和CC累计一致。累计输入2411647／输出28433，单次最大输入61602／输出2404；solver286.907秒，CC283.437秒、API183.712秒，范围不同，没有据差值虚构工具耗时。manager总239.966秒，reset15.38、prep0.497、test8.387，可信setup段214.877392；保护／复制／运输不归入模型推理。queue_wait0只代表此臂。

原诊断capture于运行前即时读取engine／adapter、实际模板和config，capture过程前后ID、PID、StartedAt、restart_count保持，checkpoint manifest为 `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab`，config与实际HTTP一致。它不是整个模型运行前后连续证明；未重哈希37个live权重或GPU内存，也没有把历史capture时间改写成本次。inner service_readback false原字段保留，额外实际capture单列。完整RC0与PID1本作业成功journal相符，不用unit-not-found默认0充当终止证明。

## 资源、清理与后续

有限资源40切片按实际CID：actor22、relay22、grader16点；正式安装／测试窗口分别1／0个grader点，0个点表示未观测。actor记录memory.peak最大1229443072字节、grader857927680字节，report峰值846.996MiB单列。不能推出最低配置、连续无OOM或全局资源清理。

实际actor／relay清理成功，pre-drain residual0、gateway revoked／drained／active0；manager创建1／移除1，open／supply／cleanup_failures空。自有查询证据为空，不扩大到其它作业。正式运行、CPU历史失败、旧原raw和固定材料均保留。

题主完整读回 `runs/category2_repair_20260929/moto_cpu_20261003/moto6185_qwen36_a1_owner_readback_20261004.json`，263617字节，SHA `3befaea42c9a881eeb0dfccb7fef858a6eb124e31044c43b42a3f8fecd6f52a8`；机械回执SHA `e67a35db6691d1bd81e24a0a63e0990937d9ad74811a285695342d82b848f436`；[双模型首轮分析](two_model_first_round_analysis_20261004.md)引用总回执SHA `2c36e3c863d9abf738609b700335343ca5cd918284e427f048d19cbd2db6a80f`。题主确认终局后通过CLI ACK并closeout；当前无需CPU修复，普通追加暂缓。
