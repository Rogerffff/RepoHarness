# Moto6408：Coder 首次结果与轨迹分析

2026-10-03。`gpu1003-moto6408-coder-a1` 原分1，安装／测试退出均0，1F／95P共96项完整通过。源码分析确认当前“在两份已有manifest间迁移标签”的修法正确：更新目标前使用既有删除接口清除旧归属，两侧其它标签与镜像保持。没有必要题目修订或CPU重跑。Qwen首次待回传，请求仍claimed，单样本不证明稳定或训练资格。

## 实际输入与正式评分

权威包 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-moto6408-coder-a1/`，manifest SHA `43f272c5749978b8100ee8bda9644c4edd0a1dc7d69c8ddef15addf4c4af9134`。585成员／87,027,748字节逐项核SHA和尺寸，包含前序依赖，不能算作585次实验或与其它包相加。queue27／code8 source manifest `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`；fixed inputs manifest `18daed50fe16dcde3fde48dd5222d3038c6d7084ad894172f99f7a95b96425a2`。兼容remote镜像不替代权威历史字节。

请求 `swe-moto6408-tag-ownership-r18-20261003-v1` 原输入SHA `271efb22d0e5e396d08a9341267e0c5d79ad4cc72b36892e1659ae4ee0c548d3`，与实际复制相等。材料 `moto6408-tag-ownership-v1`，host patch SHA `00546841fca20f0b6b781fb49124370d0dab60bf99fdcd01e55aa947b4b65365`；base／public／environment／grading／materials均与请求一致。actor／grader实际镜像均为CPU验证的 `f00e022c3edf2dd23121abab802e401a64ee9e98598f07fb37a83d5c4c2012a1`。

首HTTP实际含完整题面与当前开发brief，delivered prompt SHA `85f58f166164eba15ec6b666e1213b29e33c5cf5bbca48218a35e1d892e3feb1`，按原换行字节核验。host eval前缀 `pytest -n0 -rA` 固定消费为 `pytest -n0 -rA tests/test_ecr/test_ecr_boto3.py`，与input_check和日志相符。根目录新增自测没有替换正式测试。

模型预算ctx196608／输出65536／240回合／10800秒／1024请求／首字节1800秒／idle14400；评分whole1800／setup300／apply120／test1800。实际生成max_tokens全部65536，正常end_turn，无预算截断证据。CC摘要maxOutputTokens32000不覆盖HTTP事实。slime-actor模型通道由GPU固定Coder服务关联，题主未另行活查权重／GPU内存。

正式footer `96 passed, 366 warnings in 5.76s`，实际安装5.431秒、测试6.186秒。逐参考96完整，无missing／skipped／infra／段外未归账。目标 `test_multiple_tags__ensure_tags_exist_only_on_one_image` 不只检查查询第一项，还检查迁移标签恰好命中一镜像、两份digest唯一、两侧全部原标签及迁移标签集合；目标与95P全过。

## 补丁语义与自测

FP `6e1a8b3fbd1ae808843e985b6cd70ee14ef2f0363f1373481de0970adbdad59c` 三项regular／100644全部投影：`moto/ecr/models.py` 与两个根目录自测。baseline2052项内容／类型／执行位全核，所有成功Write／Edit逐步重放精确等于FP。唯一源码Edit149行，最终源码SHA `00a50af15ca9fd3bcc3a75a2e037557b7b6117abc12b378c1f2d7bd958b7f320`。

原put_image仅在manifest尚不存在的分支清理同名tag；manifest已存在时直接update_tag，旧镜像仍有迁移tag。补丁将既有 `batch_delete_image(repository_name, image_ids=[{"imageTag": image_tag}])` 逻辑补到已有manifest分支，放在update_tag之前。原“目标当前tag相等则ImageAlreadyExists”分支保留。既有删除实现对多tag镜像只remove_tag，剩唯一tag时才删除镜像；当前复现的旧镜像还有image_001，目标还有image_002，两侧均保留。不是调整repository.images排序以掩盖重复，不清空所有镜像，也不硬编码mock-tag。

源码满足当前保护范围。既有多tag查找还依赖response_object当前imageTag，这次未改造一般标签查找、错误优先级或删除无其它tag镜像的旧语义；当前证据不自动授予所有ECR／真实AWS兼容资格。

101行写复现，110／114行修前断言失败，149行修源码，162／166行同复现修后成功。这个复现以 `initial_image != new_image` 断言辨别查询变化，单独不能保证没有第二份同tag镜像。219行新增严格自测除查询变化还检查两份镜像和仅一份含mock-tag，228／232行1项通过；它未逐一断言全部原tag集合，正式修订目标另作保护。175／184／193行三个原节点通过，206／210行put_image选中10项通过、85项未执行，241行单原节点通过；这些重叠自测不相加成新的独立样本，也不声称solver执行完整96项。

## 轨迹与运行成本

267行完整轨迹，22回合／生成、21工具：Bash12、Read6、Write2、Edit1，逐ID一一对应、全为单工具串行。HTTP23条为22生成＋1count_tokens，均200；各生成完整SSE start／delta／stop及usage与adapter／CC一致。唯一标错工具结果是114行预期的修前AssertionError；无导入、空节点、运输或环境错误。

10行定位代码、23行读模型，49／75行读公开测试，88行读manifest生成helper；101行构造复现，123／136行核put_image两条分支后149行修。定位与修前／后证据连贯。只有串行选择，没有多工具batch或实际并行节省证据；不同源码／测试搜索可能可独立进行，但本次没有执行层重叠时长，记不可量化。

累计输入516529、输出5074，最大单次输入32379、输出1122；solver54.592秒、CC50.954秒、API44.058秒分别记录，不能按差值冒充工具耗时。manager总250.177秒、reset16.361、prep0.562、test12.217；phase trusted setup219.535738秒。保护恢复、正式安装／测试与solver分开，单次queue_wait0不推全局无队列。

## 清理与后续

actor／relay容器及网络所属查询实际清理空；manager创建1／移除1、open与cleanup_failures空；gateway revoked／drained／active0，pre-drain residual0。26有限资源切片中actor7／relay7／grader17点按实际CID归属，正式安装0个、测试1个grader采样点，安装区间资源未知。actor记录峰值1012658176字节、grader871673856字节，report844.039MiB单列；不足以推最低内存、连续无OOM或宿主全局空。

题主读回 `runs/category2_repair_20260929/moto_cpu_20261003/moto6408_coder_a1_owner_readback_20261003.json`，238287字节，SHA `9de4e2c1c3e8382e8176afcaced20cb873c066a235d60be784ecf5232be69e87`。原输入、有效材料、旧R13安装2及原raw均保留。当前等待同材料Qwen首次收口，普通追加暂缓。
