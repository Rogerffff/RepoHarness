# Moto5960：Qwen3.6 首次结果与轨迹分析

整理：2026-10-04；运行原件日期为2026-10-03 UTC。`gpu1003-moto5960-qwen36-a1` 原分1，安装／测试实际退出0，3F／155P参考齐全、实际159项全过。题主源码与轨迹核对确认当前目标正确；与已分析Coder形成双模型各首次1／1。没有新增solve、CPU重跑、材料发布或普通追加；单样本不证明稳定、模型排名或训练资格。

## 实际绑定与完整性

权威原件为 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-moto5960-qwen36-a1/`，queue_qwen_next12／code8。closed manifest SHA `b7434a3e54739b482f47dece50fae130b40e455056b539cf6ec36f45df908386`，379成员／62,669,615字节逐项SHA、尺寸相符。它含共享及前序依赖，不是379次模型实验，也不能与Coder包直接相加。输入manifest `2f20d2710e4700274b463bd6471890991d8a71ee4b732134e2592e8c09c07231`。

固定请求 `swe-moto5960-gsi-scan-r18-20261003-v1` SHA `c4baeddb4ef991d6787755ba23caef56cc385011305700295696f07796a8a964`，两份实际copy与原输入逐字节相等；public／environment／grading／materials身份、base commit、有效test_patch与固定请求相符。材料 `moto5960-gsi-scan-keys-only-v1`，actor与grader实际镜像 `sha256:4bafbb6965ff41c0f6eb50a73f831e7b62c41b5beda6ffad957fbc926c2359ac` 与CPU和Coder相同。全部baseline entry与Coder相等；完整实际首HTTP包含原题面和中性brief，delivered prompt逐字节等于Coder，保留原换行核验。profile只有批准的模型网关端口差异。

实际ctx196608／输出65536／CC240回合／wall10800秒／HTTP1024／first1800／idle14400；评分whole1800／setup300／apply120／test1800，两模型相同。全部生成HTTP max_tokens65536，正常end_turn；CC摘要的32000记账字段不覆盖实际预算。host eval前缀 `pytest -n0 -rA` 与展开实际测试文件分别核对。

完整正式footer `159 passed, 1836 warnings in 12.40s`，安装4.654秒、测试13.118秒；candidate段完整、实际exec/install/test均0，没有infra、missing或skipped。5960两条参数名带空格的实际PASSED行合成一个既有解析参考键，分别核实际159行与158键；不修改parser。

## 修法与正式保护

最终FP只修改 `moto/dynamodb/models/table.py`，regular／100644，内容SHA `be213ffa2df68086e737c1a5a717390bf41ec855da5d37211150dc236a42d6b6`。从完整1884项baseline重放轨迹135行唯一Edit，精确得到39694字节源码；没有修改测试、根目录文件或评分材料。

scan保持原trim、filter、scanned_count和last_evaluated_key顺序。存在index_name时先deepcopy结果，再对每项执行原Index.project；显式projection_expression在其后执行。原Index.project用表键、索引键、NonKeyAttributes处理KEYS_ONLY／INCLUDE，ALL不删属性。复制避免Item.filter就地损坏表内Item；不是仅修第一返回项，也没有硬编码索引名称。当前F2P的INCLUDE完整值／Count／get_item、两条KEYS_ONLY完整项／Count／原payload、LSI KEYS_ONLY均实际通过。无需当前材料或环境修订。

Qwen仅在索引scan或原显式projection分支复制；Coder在所有scan中无条件复制。两者在当前目标行为一致，源码并不相同。Qwen同时指定索引与显式projection时会复制两次，Coder普通无索引scan也复制一次；没有量化性能测试，不把这些差异当作已证明缺陷或据以追加CPU任务。

## 定位与自测的局限

轨迹11／25行定位源码，39–99行读取backend和table，117／121行用三条INCLUDE数据实际观察修前AssertionError。135行修正，149／153行同程序通过。167、185、199、217行分别执行KEYS_ONLY、ALL、普通表和LSI KEYS_ONLY，375行重做题面两类程序；这些程序虽严格让断言失败退出非零，却只断言第一项键集合，没有独立检查所有项、值、Count或表内原数据，不能替代正式保护。

solver自测footer分别为scan11、文件GSI/global8、query13、目录GSI16、LSI1、两个既有节点2通过；均通过head／tail截取输出，命令退出可能掩盖pytest退出，计为看见的footer，未虚构全部逐节点状态，且这些子集重叠不能相加。正式修订的全文件159项由独立grader另行执行。最后回答还宣称LSI INCLUDE正确，但轨迹没有独立LSI INCLUDE测试；不授这一额外结论。

393行完整轨迹，25回合、24工具：Bash17／Read6／Edit1，每个调用与结果逐ID对应，全部单工具串行。只有117／121修前预期断言失败标错，没有把它算作运行环境故障。无多工具batch、无每工具耗时或并行收益证据。定位较直接，与Coder的错路径／错节点纠正不同，但单次不证明一般效率优势。

## 运输、运行成本与服务证据

HTTP27条为25生成＋2count_tokens，全部200；每条生成SSE的start／delta／stop齐、usage与adapter和CC累计一致。累计输入737488／输出7428，单次最大输入41232／输出1016；solver67.382秒，CC63.761秒、API49.276秒，范围不同，没有据差值虚构工具耗时。manager总248.829秒，reset14.11、prep0.384、test18.378，可信setup段215.135737；保护／复制／运输不归入模型推理。queue_wait0只代表此臂。

原诊断capture于运行前即时读取engine／adapter、实际模板和config，capture过程前后ID、PID、StartedAt、restart_count保持，checkpoint manifest为 `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab`，config与实际HTTP一致。它不是整个模型运行前后连续证明；未重哈希37个live权重或GPU内存，也没有把历史capture时间改写成本次。inner service_readback false原字段保留，额外实际capture单列。完整RC0与PID1本作业成功journal相符，不用unit-not-found默认0充当终止证明。

## 资源、清理与后续

有限资源26切片按实际CID：actor7、relay7、grader17点；正式安装／测试窗口分别0／1个grader点，0个点表示未观测。actor记录memory.peak最大1034739712字节、grader911269888字节，report峰值869.055MiB单列。不能推出最低配置、连续无OOM或全局资源清理。

实际actor／relay清理成功，pre-drain residual0、gateway revoked／drained／active0；manager创建1／移除1，open／supply／cleanup_failures空。自有查询证据为空，不扩大到其它作业。正式运行、CPU历史失败、旧原raw和固定材料均保留。

题主完整读回 `runs/category2_repair_20260929/moto_cpu_20261003/moto5960_qwen36_a1_owner_readback_20261004.json`，215380字节，SHA `90e8d6a28ad56eb15ca8cfb1186bbba2a69d7e8bd606049c1854f31f63ce3b07`；机械回执SHA `65fa8c057908a42321da7309e075791c01666b518b9f93b8a0bf38ab07524c87`；[双模型首轮分析](two_model_first_round_analysis_20261004.md)引用总回执SHA `de9e365aa3a7d7a266caefdf6599b601ce1252c51c4404e60c3c2e52690bffe1`。题主确认终局后通过CLI ACK并closeout；当前无需CPU修复，普通追加暂缓。
