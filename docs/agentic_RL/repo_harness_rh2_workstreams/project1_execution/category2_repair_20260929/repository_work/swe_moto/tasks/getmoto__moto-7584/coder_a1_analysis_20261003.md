# Moto7584：Coder首次结果与轨迹分析

2026-10-03，依据17:30:30 SGT结束的 `gpu1003-moto7584-coder-a1`。当前 `swe-moto7584-endpoint-r13-20261003-v1` 的Coder首轮原分1，安装／测试退出均0，1F／19P共20项逐参考通过。题主源码核对认为目标修法正确：仅application协议检查端点存在，检查先于重复订阅提前返回，修复“订阅→删除→再订阅”且不误拒有效application、email和SQS订阅。当前没有必要追加题目修订、CPU重跑或模型重复采样。Qwen首次尚未完成，请求保持claimed，单样本不能证明稳定或训练资格。

## 绑定与实际执行

唯一权威包为 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-moto7584-coder-a1/`。manifest SHA `78a4451faa2b97cd1d9792033d4b92a83b08d52c790fcc0b23bc420dfd9b2926`，398成员／75,652,967字节逐项SHA和尺寸相符。这包括固定输入及前序依赖快照，不是398次题目实验；不能用兼容remote镜像覆盖权威包中不同历史字节。

原owner输入 `bfd638718181356e230c432844ddc494fb51903f48dcad46505f2ce7512dd34d` 与执行者复制逐字节相等。材料仍 `moto7584-endpoint-v3`，实际host test_patch SHA `58875207adea3feddb71bb0b04bfd47423f0663ac79b9be54f402e815f144fd3`；public／environment／grading／materials身份与请求一致。actual actor、资源样本中actor和grader镜像均 `990e0e91a190f85426e6900828cf758c30f389c927f6c1d0cd1ed8c68b902f96`，与原CPU验证镜像相符。

queue25／code8 source manifest `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`，入口、固定消费及before／after模型capture留在包内。Coder revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`；实际启动前capture关联只读挂载、engine／adapter身份及配置，没有重复全部权重或GPU内存hash。inner `service_readback.runtime_request_and_sglang_readback_verified=false` 等字段保留，外部现场证据另行关联，不回填原件。

原题面与中性brief交付完整，实际首HTTP包含delivered prompt SHA `2ff938f86c2f3cf5d09ecc01b9418ba5662d5a63b6e4ea8d7995a10fb683f611`。题面原CRLF逐字节保留，核SHA使用原bytes，不用换行归一化后的文本冒称一致。公开模型工作区原测试只有19项，正式评分可信恢复v3后的20项；私有host评分视图没有替换公开说明。

模型预算ctx196608／输出65536／240回合／10800秒／1024请求／首字节1800秒／idle14400；实际生成max_tokens65536、33次finish stop、CC正常end_turn，没有compact或预算截断证据。评分whole1800／setup300／apply120／test1800，未使用6114专属900政策。原host eval前缀 `pytest -n0 -rA` 由固定消费者选择目标文件，input_check和实际日志的完整命令均为 `pytest -n0 -rA tests/test_sns/test_application_boto3.py`。

完整日志原安装／测试RC0，可信setup恢复1个目标测试文件，20参考均PASSED，parser无missing／skipped／段外未归账。footer为 `20 passed, 80 warnings in 0.65s`；正式安装4.922秒、测试1.008秒。manager总265.396秒、reset29.767、prep0.719、test6.718；另phase trusted setup225.873319秒。保护／安装／测试与solver分开，单次manager queue_wait0不表示全局无排队。

## 源码与自测质量

冻结补丁FP摘要 `7e53ebb97567b005d4c604afdfa02d0756d595c3780290435c31fb709c3b9811`，五项regular／100644全部投影：一项 `moto/sns/models.py` 修改，三项根目录自测及 `FIX_SUMMARY.md` 新增。2537项baseline tar的内容、类型和执行位全部核对；源码唯一一次Edit可由baseline精确构造，既有SMS校验、其它协议和后续订阅逻辑未改。三个根目录测试不参与指定的正式20项，不替换评分测试。

新增分支仅在 `protocol == "application"` 执行 `self.get_endpoint(endpoint)`，其缺项KeyError转换为既有 `SNSNotFoundError`，再转换为 `SNSInvalidParameter`，消息含原端点ARN。该分支先于 `_find_subscription`／old_subscription返回，因此已有订阅不能绕过删除后校验；有效端点继续原重复订阅路径。不是按ARN字符串形状推测存在，也不是一概拒绝application或对所有协议检查平台端点。v3正式目标包含“已删除未订阅”“先订阅再删除”“从未创建ARN”和email／SQS保持，本次目标节点及19P实际通过。

源码与本题公开依据相符；没有真实AWS调用或额外规范核验。模型说明中“exact AWS behavior／no regressions／all existing SNS tests”不能作为外部真实性或全SNS覆盖证据，保留其超范围表述，不据此扩展评分。多输入同时无效时的错误优先级等未保护行为也没有新资格。

`test_issue.py` 与 `test_comprehensive.py` 用宽泛catch／print，预期不抛也只打印ERROR后退出0，因此仅是观察型复现。修前实际输出“Second subscribe should have failed but didn't”，修后实际有InvalidParameter及目标消息；不能将这种退出0当严格测试成功。后来的 `test_fix_verification.py` 使用ClientError和code／message断言，两个测试实际通过，证明删除后拒绝以及HTTP／HTTPS保持；它没有单独覆盖从未创建ARN、email、SQS，这些由本次正式v3补充。

## 定位、纠错与效率

384行完整CC轨迹，33回合／生成、32工具：Bash20、Read5、Write4、Edit3，其中两Edit修自测导入，唯一源码Edit在150行。工具调用／结果逐ID对应，全部单工具串行，没有实际多工具batch或可量化重叠。HTTP34条：33生成＋1count_tokens，响应均200，完整SSE与adapter usage对应。累计输入687224、输出5205，最大单次输入27091、输出809；solver71.133秒，CC67.639秒、API44.733秒是不同测量，不能混算工具或环境时间。

10／23行定位并全文读SNS源码，36行查错误类，45行已识别缺application端点检查。49行写复现，58／80两次运行都因旧 `mock_sns` 导入失败；71行只加pytest没有修复根因，93行读当前Moto5.0.6.dev导出后102行换 `mock_aws`，111／115修前复现目标缺陷。124／137精读subscribe／get_endpoint，150行源码Edit；163／185修后观察成功。229行原application19项通过，312行subscription19项通过；349／358行两个严格自测通过。

共7个tool_result错误：62／84导入失败；211／255空测试退出5；246／268／307不存在节点退出4。277／281的 `pytest ... | head` 另一次空测试被管道掩盖退出码，tool_result未标错，不计成已验证。模型在已知 `test_sns.py` 无测试后仍重复选错路径／节点，增加无效回合；最终改到真实subscriptions文件。327行topics25项显示全点号及100%，但head裁掉最终footer并隐藏pytest退出码，保留有限观察，不并入完整通过统计。33回合和累计token只能描述此样本，不能推出一般模型排名或稳定性。

## 清理与下一步

actor／relay所属容器和网络清理空，manager创建1／移除1、open／supply／failures为空；gateway revoked／drained／active0，pre-drain residual0，终局exit0／evidence_ready。终局仍保留历史PID，不据此宣称独立宿主systemd PID0或全GPU闲置。

32个有限资源切片按实际CID归属：actor10、relay11、grader17；正式安装／测试窗口均没有采样点，区间内存未知。actor记录峰值1,020,100,608字节、grader812,408,832字节与report863.215MiB是不同来源，不能互相替代或推最低内存、连续无OOM保证。

题主原件读回 `runs/category2_repair_20260929/moto_cpu_20261003/moto7584_coder_a1_owner_readback_20261003.json`，151377字节，SHA `9f5339c3c66eac395387246815d3c38c3a463d5ced68c222f4c955541427cef6`。不改原分、固定题面或历史对照；本次目标修法与已保护行为通过语义分析，暂不新增CPU任务。等待同材料Qwen首次工件后完成本题双模型首轮收口；普通追加继续暂缓。
