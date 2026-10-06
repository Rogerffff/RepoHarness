# Moto6114 新37材料：Coder首次结果分析

2026-10-03。当前请求 `swe-moto6114-identity-neptune37-r21-20261003-v1` 的首Coder臂已完成，原评分1，安装／测试退出均0，37参考逐键通过。题主核对完整候选与原源码差异：只修改 `describe_db_clusters`，目标集群身份修法正确；启停、删除及原Neptune委托代码未改，新增两条Neptune名称保持项实际通过。当前没有新证据要求再次修订题目或重采样。新R21 Qwen臂尚未完成，请求仍claimed；旧35参考Qwen及其源码重放0不能拼成当前双模型覆盖。

## 实际绑定与评分

实际作业 `gpu1003-moto6114-neptune37-coder-a1`，queue22／code8。输入原SHA `6dfa36e642bee0e9fb5e8d35efe85149bb8c9258a4a980591c9706cc57d31723` 未变；材料仍为 `moto6114-cluster-identity-neptune-preservation-v2`，测试patch `2a9661d78743cf5e36f8363e308d63260ab2076bf4bc1d68de8a9e5fd226dda4`，原1F／34P加两条P保持。actor／grader实际镜像均 `1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5`，由精确CPU导出镜像及本作业外部读回关联；UID安装证据按同ID／同配方复用，不能称此次新增GPU双UID安装实验。

实际code8独立评分入口绑定严格setup900、apply120、test1800、whole1800；这是本作业实际输入／政策／执行的证据，不从CPU ReplayGrader900直接推定。原policy `actual_image_inspect_verified=false` 和attempt中空元数据保持，外部镜像capture另行关联。五项消费脚本与当前请求固定SHA相符，可信setup恢复固定评分测试材料。

完整评分日志有安装开始／结束、安装RC0、测试RC0、End Test Output和 `37 passed, 166 warnings in 3.45s`；原1F／34P及新增两P全部PASSED，没有缺席、跳过或未归账。安装段4.812秒、测试段3.902秒；pytest footer的3.45秒是另一测量。manager总评分249.361秒，其中reset14.970、prep0.598、test9.309；独立phase记录trusted setup223.799282秒。不将这些时间归入solver，单次manager queue_wait0也不证明整个GPU队列无等待。

## 候选语义

完整FrozenPatch摘要 `7975b8a4743191d6c043eafcc106ee55a1c091c1b2a63804d2e14305401fdb1d`，四项regular／100644均进入投影：一项 `moto/rds/models.py` 修改，三项根目录自测新增。1972项baseline tar的内容、类型和执行位逐项相符；候选源码可由baseline唯一一次Edit精确构造，没有其它源码修改。原FP四项内容摘要均核验。

查询接收ARN时沿用现有 `find_db_from_id` 的解析模式，取ARN的region和最后一段名称，选对应RDS backend，再查该backend的RDS／Neptune集群。普通名称仍使用self，找不到仍抛带原输入的 `DBClusterNotFoundError`，无过滤的列表路径保持。它不采用“返回第一个集群”的退化修法，也没有旧Qwen对 `start_db_cluster`／`delete_db_cluster` 的统一查找改写；两条新增Neptune保持项因此有明确静态依据及实际评分支持。

结论限于当前同账号目标查询及已保护的Neptune名称行为。通用ARN正则还接受其它RDS资源类型，账号选择跟随既有模式；没有据此宣布跨账号、跨服务或畸形ARN完整正确。这些不是本题已批准扩展的评分范围。模型额外跨地区自测作为观察记录，不能把题单用途或验收范围静默扩大。

三个新增自测均已读：basic核无过滤／名称／ARN对应身份；comprehensive核两个集群的精确名称、两种不存在输入的错误码；cross_region核从另一区域客户端按原ARN取得同名目标。正式命令指定原集群测试文件，三项自测不计入37正式参考，也未替换评分测试。

## 轨迹与效率

217行实际CC轨迹，18回合、18生成，17工具调用：Bash8／Read5／Edit1／Write3。调用与结果逐ID对应，无tool_result错误，无多工具batch；不能推定工具重叠或并行提速。HTTP共21条，18条生成及3条count_tokens，响应均200；独立报告中“18 HTTP／SSE／adapter”按生成解释，不把count_tokens计为生成或重试。18份完整SSE与adapter生成及usage一致，生成请求实际max_tokens65536。

源码定位按轨迹可复核：10行find源码；23／36两次宽Read扩展上下文；45行已指出ARN被直接当字典键；49／62搜索、读原公开测试；75／88／97定位响应层；106行据既有 `find_db_from_id` 提出修法；110行唯一Edit；123／132基本自测；145行原公开集群文件35项通过；160行相关分页1项通过；173／182综合自测；195／204跨地区自测；213行最终回答，217行正常end_turn。没有修前失败ARN复现，首次明确ARN自测发生在源码修改后；原公开35项不含本轮强化后的身份与新增Neptune断言，不能把它们说成solver自行验证37项。正式私有评分37项另证补丁通过。

solver墙钟61.527秒；CC duration57.988秒、API47.533秒是各自测量，不互相替换。累计输入965999、输出3756 token，最大单次输入67039、输出736。宽Read使后续请求维持较大上下文，累计输入不等于context峰值。原模型预算ctx196608／response65536／240回合／10800秒／1024请求／首字节1800秒／idle TTL14400。所有生成finish stop、CC正常end_turn，未见compact或预算截断；CC modelUsage中32000元数据不是实际HTTP输出cap，costUSD也不是租机账单。

模型最后“full backward compatibility／all test cases”表述超过实际自测范围，按当前目标及正式37项限制其主张。此臂单样本与旧Qwen不同版本／安装状态，不能比较两者一般能力或据耗时、token比值排名。

## 清理、资源与未完成项

actor／relay容器、所属网络清理记录为空，manager创建1／移除1、open／supply／failures为空，gateway revoked／drained／active0，终局exit0／evidence_ready。dispatcher保留的历史PID不能证明宿主systemd PID0；本作业终局队列idle也不能推广成当前所有服务闲置。

26个有限资源切片按实际CID和角色窗口核：actor／relay各8点、grader16点；安装窗口1点、测试窗口0点。report峰值932.035MiB另存，采样间隙及正式测试内存未知，不能推最低内存或连续无OOM保证。启动前后Coder engine／adapter现场原件与固定revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120` 关联；未重复所有权重hash或硬件内存hash，不扩大身份保证。

回传partial v2 SHA `6591bb38c6fc0aa507962a9ed2f75cf01e704b6b1464fa32f38c54b72fd4a587`；[独立执行核查](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/moto6114_neptune37_coder_a1_execution_review_v1.md)仅接受执行证据。题主本次核130闭合成员／59,283,909字节、1972baseline、四项FP和217轨迹；[原件读回](../../../../../../../../../runs/category2_repair_20260929/moto_cpu_20261003/moto6114_neptune37_coder_a1_owner_readback_20261003.json) SHA `d62a5e5f3f4b4a564807b473551aa85d482d4f85551b2356dc310bbbcd023d43`。不改原raw、旧35／安装2／CPU重放0，不新赋训练、留出或typed资格。下一步等待同材料Qwen首次结果，再完成当前双模型收口。
