# Moto5960：Coder 首次结果与轨迹分析

2026-10-03。`gpu1003-moto5960-coder-a1` 原分1，安装／测试退出均0；3F／155P共158解析参考完整，实际159项全部通过。源码分析确认当前目标修法正确：scan使用既有索引投影，投影前复制返回项以保护表内存储。本次不需题目修订或CPU重跑。Qwen首次待回传，请求保持claimed，单样本不证明稳定或训练资格。

## 实际绑定与正式评分

权威原件仅为 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-moto5960-coder-a1/`。manifest SHA `a6f7aa70a4cb58cf1e112373d16691b816170711da7b6f631614ccd50fa74a6b`，595成员／66,143,937字节逐项SHA和尺寸相符，含前序依赖，不能解释为595次模型实验或与其它包直接相加。queue27／code8，source manifest `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`，fixed inputs manifest `18daed50fe16dcde3fde48dd5222d3038c6d7084ad894172f99f7a95b96425a2`。兼容remote目录不替代此包。

请求 `swe-moto5960-gsi-scan-r18-20261003-v1` 原输入 SHA `c4baeddb4ef991d6787755ba23caef56cc385011305700295696f07796a8a964` 与实际复制逐字节相等。材料 `moto5960-gsi-scan-keys-only-v1`，host test_patch SHA `b9a656bde376f6fefa3dd33b16dad74704b50213795b3c52dfcecfa3c57c296e`；public／environment／grading／materials身份、base commit与请求一致。actor和grader实际镜像均为CPU已验证的 `4bafbb6965ff41c0f6eb50a73f831e7b62c41b5beda6ffad957fbc926c2359ac`。

原题面、当前中性开发brief与实际首HTTP相符，delivered prompt SHA `d38bf35c13c2166063e4f66b4fe68cfec78263a951f075123995cff324643d2e`。保留原换行字节核验。正式host eval前缀 `pytest -n0 -rA` 经消费者选择文件，input_check和完整日志实际为 `pytest -n0 -rA tests/test_dynamodb/test_dynamodb.py`。可信评分恢复有效patch；模型新增根目录自测不替代正式测试。

实际模型预算ctx196608／输出65536／240回合／10800秒／1024请求／首字节1800秒／idle14400；评分whole1800／setup300／apply120／test1800。实际生成max_tokens全部65536，正常end_turn，没有预算截断证据。CC摘要中的maxOutputTokens32000是记账字段，不能覆盖实际HTTP设置。模型通道名称为slime-actor，角色依据GPU固定Coder服务证据；题主没有另行活查权重或GPU内存。

完整正式footer `159 passed, 1836 warnings in 12.86s`，安装4.727秒、测试13.617秒，无infra／missing／skipped／段外测试。参数名含空格的 `test_set_attribute_is_dropped_if_empty_after_update_expression` 两条实际PASSED行合成一个原参考键；完整159实际行与158解析状态分别保留，未改parser。三条F2P为既有GSI INCLUDE、LSI KEYS_ONLY和新增GSI KEYS_ONLY全项检查，均通过；155P保持。

## 修法与验证质量

FP `d3c083e61d95d73ef99f7f434d8b8a6165489a60c06ccc6c35dc6d1f1689b3a4` 共三项regular／100644全部投影：`moto/dynamodb/models/table.py` 和两份根目录自测。baseline1884项内容、类型、执行位全核；所有成功Write／Edit从实际baseline重放，精确得到FP，无额外源码或测试目录修改。唯一源码Edit位于轨迹207行，源码内容SHA `5f6826072cd01345f25a789a6df38e7c4a03701a75a58d667484330146bc9b41`。

scan在既有trim／filter之后深复制results，有index_name时调用既有 `get_index` 和 `index.project`，然后执行显式projection_expression。原Index.project按表键、索引键与NonKeyAttributes处理KEYS_ONLY／INCLUDE，ALL维持全部属性；没有硬编码返回某一条或某一个索引。复制使Item.filter的就地操作不损坏存储。scanned_count与last_evaluated_key生成顺序保持，原LSI路径也获得投影。源码与当前目标及正式保护一致；没有据此授予一般AWS兼容资格。

正式INCLUDE检查完整返回值、Count和原表get_item；新增KEYS_ONLY检查两条不同表键／索引键的全部返回值、Count及每条原payload仍在。模型自写两份测试仅断言第一返回项的键集合，未独立保护所有项、payload值或表内存储，这些由正式修订目标提供。模型直接执行的程序宽泛catch后只打印失败，退出0不足为通过证据；194／198行严格pytest修前实际失败，220／224行两自测修后通过，351／355行ALL／INCLUDE／KEYS_ONLY三个严格自测通过。另三个原节点scan_filter、scan_by_non_exists_index、query_gsi_with_range_key分别通过。未执行原完整159项的solver自测，不采信其“现有测试套件无回归”的泛化表述。

无条件deepcopy也覆盖普通表scan，可能增加复制成本；本次没有量化性能测量，不把此点判为已证明缺陷，也不为了普通有效1追加CPU任务。

## 定位、纠错与运行成本

377行完整CC轨迹，32回合／生成、31工具：Bash17、Read10、Write3、Edit1。所有调用和结果逐ID对应，均单工具串行，无多工具batch或量化并行收益。HTTP34条为32生成＋2count_tokens，均200；每条生成SSE的message_start／message_delta／message_stop完整、usage与adapter和CC累计一致。

10行定位目录，23／41两次读取不存在models.py，随后才列目录并读models包与table；133行读scan，142行已明确缺投影；159行读既有Index.project，172行写复现，181／185行观察两个失败，194行严格复现后207行修源码。重复错误路径可减少，但不是环境损坏。共五个标错结果：两次缺文件Read、一次预期修前断言失败、259／263不存在scan节点、364／368拒绝未先读README的Write；失败README不在最终FP。没有重试同一模型运行。

累计输入937083、输出5622，最大单次输入42876、输出1276；solver65.338秒、CC61.742秒、API54.239秒，各有不同测量范围，没有每工具耗时可据以拆分差值。manager总254.615秒、reset14.373、prep0.499、test18.94；phase trusted setup219.547726秒。正式安装／测试与运输保护耗时另列，不归到模型推理。单次queue_wait0不证明全局无排队。

## 清理与后续

actor／relay容器、标签查询和网络清理为空；manager创建1／移除1、open与cleanup_failures空；gateway revoked／drained／active0，pre-drain residual0。有限资源27切片中actor8／relay8／grader17个点按实际CID归属，正式安装及测试窗口各仅一个grader采样点；actor记录峰值958357504字节、grader908079104字节，report866.012MiB单列。不能由这些点推出最低内存、连续无OOM或宿主全局清理。

题主读回 `runs/category2_repair_20260929/moto_cpu_20261003/moto5960_coder_a1_owner_readback_20261003.json`，273682字节，SHA `35995f2f4df2f94a6c6b67099dc815bec02b910503fd3a409fbd59b2542ae8f6`。原材料、CPU历史R13安装2和原raw保持。等待同材料Qwen首次后完成双模型收口；普通追加暂缓。
