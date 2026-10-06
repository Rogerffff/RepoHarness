# Moto7584：Qwen 首次结果与轨迹分析

2026-10-03。`gpu1003-moto7584-qwen36-a1` 原分1，安装／测试退出0，1F／19P共20参考完整通过。题主确认端点存在性校验仅用于application协议，且先于重复订阅提前返回，当前修法正确。删除后再订阅不能绕过校验，合法application、email和SQS保持；无需新评分材料、CPU重跑或模型重跑。本题两模型首轮各一次已齐备，单样本不证明稳定或训练资格。

## 固定身份与真实执行

唯一权威包 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-moto7584-qwen36-a1/`，manifest位于其 `qwen_next12_closed_v1/gpu1003-moto7584-qwen36-a1/closed_manifest.json`。SHA `556d1cfe9ad6e3becc46e9c6003d7b8b6b2edfbaa47dd2ec776710a82d37075f`，180成员／72,410,891字节全核SHA和尺寸，含准备与共享依赖，不能按180次实验或与Coder的398成员累加。兼容remote目录不替代权威原件。

机械回执SHA `bc6796b6a6316ae30b4639336a78bc361f9cb3a31ea3f934d8726f7e299e8581`；两臂总回执SHA `f55a45806b98e6e5176a1ff69bf7b13b80cad1382eed4695c473bdfca6672d86`，均按原字节核验。机械回执semantic空及单臂paired_request_closed=false保留；题主结论与总账确认另记，不回填旧原件。

当前请求 `swe-moto7584-endpoint-r13-20261003-v1` 输入SHA `bfd638718181356e230c432844ddc494fb51903f48dcad46505f2ce7512dd34d`，与prepared及本次Qwen evidence两份实际复制相等。queue为 `queue_qwen_next12_v1`，runtime code8，fixed inputs manifest `2f20d2710e4700274b463bd6471890991d8a71ee4b732134e2592e8c09c07231`。材料 `moto7584-endpoint-v3`、host patch SHA `58875207adea3feddb71bb0b04bfd47423f0663ac79b9be54f402e815f144fd3`，base、public／environment／grading／materials身份与原输入一致。actual actor／grader镜像为CPU及Coder相同的 `990e0e91a190f85426e6900828cf758c30f389c927f6c1d0cd1ed8c68b902f96`。

实际Qwen服务在22:35:02 SGT启动本题前capture，22:41:02 SGT终局；before／after engine与adapter inspect、只读模型挂载、配置和checkpoint manifest在包中关联。checkpoint manifest SHA `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab`，没有把历史Qwen捕获重标为本题时间，也未重复全部权重文件或GPU内存hash。input_check内部service_readback config_only／verified=false保留，外部捕获与真实HTTP另核，slime-actor通道名本身不证明权重身份。

完整原题面与中性brief实际交到首HTTP，delivered prompt SHA `2ff938f86c2f3cf5d09ecc01b9418ba5662d5a63b6e4ea8d7995a10fb683f611`，保留原CRLF逐字节核对。2537项baseline entries及prompt与Coder完全相等，内容／类型／执行位全部核验；两臂材料身份、实际镜像及模型／评分预算也相等。

模型预算ctx196608／输出65536／240回合／10800秒／1024请求／首字节1800秒／idle14400。实际15次生成max_tokens均65536、finish stop，CC正常end_turn，无预算截断。评分whole1800／setup300／apply120／test1800，未使用6114专属900。host eval前缀 `pytest -n0 -rA` 固定选择为 `pytest -n0 -rA tests/test_sns/test_application_boto3.py`，与input_check及实际日志相符。

正式安装4.824秒、测试1.001秒，完整footer `20 passed, 80 warnings in 0.67s`；20参考均PASSED，无missing／skipped／infra／段外未归账。正式可信恢复v3目标测试，solver公开原application文件仍只有19项，两者不混同。

## 源码及验证质量

FP `5731f0679ed98f04940acc699cc03ef6c11550acc2c2d3fccd727453caee71ab` 仅一项 `moto/sns/models.py`，regular／100644，44926字节，内容SHA `c92b1faab04cb5d5160d57bed54dc6037ff98a7ada4b6aeffd686ef147803753`，全部投影。93行唯一Edit从实际baseline精确得到FP；原SMS校验、其它协议和后续订阅逻辑没有改动。与Coder最终源码的完整AST（忽略注释和排版）相等，两者功能修法一致。

新增分支 `protocol == "application"` 调用 `get_endpoint(endpoint)`；缺项经既有SNSNotFoundError转为SNSInvalidParameter，消息保留原端点ARN。分支位于 `_find_subscription`／old_subscription之前，避免已有订阅在端点删除后提前返回。有效端点仍走原订阅流程，未按ARN形状猜测存在，也未普遍拒绝其它协议。正式v3目标同时保护“删除未订阅”“订阅后删除”“从未创建ARN”和email／SQS保持，当前原分1有对应源码依据。

75／79行inline程序实际显示“Second subscribe did not raise exception”，但用宽泛catch／print，不抛断言，退出0是观察而非严格失败判据。111／115行修后实际抛InvalidParameter并通过捕获分支中的code／message断言；若意外不抛，仍只打印ERROR而退出0，因此不能称完整严格回归。129／133行实际观察合法端点成功和从未创建端点拒绝，但无拒绝code断言、无强制no-raise失败。三段程序均通过python -c执行，未新增工作区文件或进入FP；完整文本与输出在轨迹中。正式20项提供更强的验收，模型“与真实AWS完全一致”的表述没有实际AWS执行或外部规范核验。

## 定位、工具纠错与成本

251行完整CC轨迹、15回合／生成、14工具：Bash10、Read3、Edit1，逐ID一一对应、全单工具串行，无实际多工具batch或量化并行收益。HTTP17条为15生成＋2count_tokens，响应全200；全部生成SSE有message_start／message_delta／message_stop完整结束，usage与adapter和CC累计相等。

11行查SNS subscribe路径，25行全文读模型、39行读异常类、57行读订阅测试；75行复现缺校验，93行修源码，111行观察修后目标，129行观察有效及不存在端点。没有导入重试或多次source Edit。

147／153行subscriptions原19项经head显示完整footer；167／171行publishing经tail显示104 passed／802 warnings／2.30秒；213／217行application原19项无管道、完整19 passed／64 warnings／0.50秒。185／189行选不存在的test_platform_http_requests.py，pytest空收集且打印路径错误，但tail掩盖退出码，tool_result未标错；不能由0个标错结果推无操作错误。199行ls后找到实际application文件，改用真实路径。231／237行全SNS经tail有184 passed／1427 warnings／13.97秒footer，只有尾段，不能补造全部184逐项状态或独立pytest退出码；19／104／19与184重叠，不累加为额外尝试。当前正式20另行完整核验。

累计输入394279、输出2853，最大单次输入35313、输出550；solver53.708秒、CC50.065秒、API20.131秒各自记录，没有工具独立耗时可据差值推精确测试开销。manager总244.301秒、reset22.471、prep0.551、test6.6；phase trusted setup213.861155秒。运输保护、正式项目安装／测试与模型推理分开，单次queue_wait0不证明全局无排队。

## 清理、资源及收口

actor／relay所属容器及网络查询实际为空，manager创建1／移除1、open／supply／cleanup_failures空；gateway revoked／drained／active0，pre-drain residual0。systemd unit终局已not-found，其默认PID0／status0不是退出证据；当前完整RC0及精确PID1成功journal事件另存并核验。

26有限资源切片中actor8／relay8／grader16点按实际CID归属，无其它任务点混入；正式安装和测试窗口均0采样，区间资源未知。actor记录峰值1096425472字节、grader802025472字节，report854.188MiB单列，不据此推最低内存、连续无OOM或宿主全局空。

题主读回 `runs/category2_repair_20260929/moto_cpu_20261003/moto7584_qwen36_a1_owner_readback_20261003.json`，85509字节，SHA `ec44cd6a6890fce7c7008b28a53bcc778f0804a97ff487df0fe6bb0e3b6d06a8`。当前两模型各首次原1／1、目标修法正确；本题首轮可收口，无新CPU、材料或重复模型安排，训练资格未定。
