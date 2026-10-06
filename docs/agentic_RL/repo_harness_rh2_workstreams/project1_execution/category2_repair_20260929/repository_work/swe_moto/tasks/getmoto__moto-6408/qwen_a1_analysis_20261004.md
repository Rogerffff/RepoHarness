# Moto6408：Qwen3.6 首次结果与轨迹分析

整理：2026-10-04；运行原件日期为2026-10-03 UTC。`gpu1003-moto6408-qwen36-a1` 原分1，安装／测试实际退出0，1F／95P参考齐全、实际96项全过。题主源码与轨迹核对确认当前目标正确；与已分析Coder形成双模型各首次1／1。没有新增solve、CPU重跑、材料发布或普通追加；单样本不证明稳定、模型排名或训练资格。

## 实际绑定与完整性

权威原件为 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-moto6408-qwen36-a1/`，queue_qwen_next12／code8。closed manifest SHA `993f1672689aaf0f72b41328734fc070c3a2abe7bf1844c051ff9775aab07fb3`，396成员／90,427,288字节逐项SHA、尺寸相符。它含共享及前序依赖，不是396次模型实验，也不能与Coder包直接相加。输入manifest `2f20d2710e4700274b463bd6471890991d8a71ee4b732134e2592e8c09c07231`。

固定请求 `swe-moto6408-tag-ownership-r18-20261003-v1` SHA `271efb22d0e5e396d08a9341267e0c5d79ad4cc72b36892e1659ae4ee0c548d3`，两份实际copy与原输入逐字节相等；public／environment／grading／materials身份、base commit、有效test_patch与固定请求相符。材料 `moto6408-tag-ownership-v1`，actor与grader实际镜像 `sha256:f00e022c3edf2dd23121abab802e401a64ee9e98598f07fb37a83d5c4c2012a1` 与CPU和Coder相同。全部baseline entry与Coder相等；完整实际首HTTP包含原题面和中性brief，delivered prompt逐字节等于Coder，保留原换行核验。profile只有批准的模型网关端口差异。

实际ctx196608／输出65536／CC240回合／wall10800秒／HTTP1024／first1800／idle14400；评分whole1800／setup300／apply120／test1800，两模型相同。全部生成HTTP max_tokens65536，正常end_turn；CC摘要的32000记账字段不覆盖实际预算。host eval前缀 `pytest -n0 -rA` 与展开实际测试文件分别核对。

完整正式footer `96 passed, 366 warnings in 5.95s`，安装4.781秒、测试6.418秒；candidate段完整、实际exec/install/test均0，没有infra、missing或skipped。96条实际PASSED行与96解析键逐项相等。

## 最终修法与正式保护

最终FP只修改 `moto/ecr/models.py`，regular／100644，42103字节，内容SHA `669384cfe6020c1d71a98cfa1461e3a2d3763d9e5356b02edc7bd888bb290160`。完整2052项baseline逐内容、类型、执行位核对；169、273、391、475行四次Edit按原顺序重放，精确得到最终FP。所有临时程序在/tmp，不进入FP，也没有修改正式测试。

最终put_image按image_tags全部成员寻找标签，清理旧归属后才追加新镜像或给既有manifest添加标签。旧镜像只有迁移标签时移除镜像，有多个标签时只remove_tag；最终同manifest／同标签分支恢复ImageAlreadyExistsException。当前目标是把已有标签移到已有另一manifest，正式新增检查确认查询只返回目标、两条不同digest仍存在、两侧完整tag集合正确，不靠首项顺序掩盖重复。全部96参考通过，当前目标语义正确，不需材料或环境修订。

与Coder仅在已有manifest更新分支调用batch_delete_image相比，Qwen还重写新manifest分支、标签检索和重复推送判断。当前目标正确不代表所有扩展语义获独立资格；本次不新增实际AWS、多标签乱序、None标签或更广泛API验证。最终回答把原batch_delete_image概括成删除全部匹配镜像，但原函数删除时修改正在枚举的列表，这不是严格的“全部”保证；新代码在append前处理旧列表规避该路径，不能把模型概述当作完整证明。

## 修复过程、错误与自测

早期47／65／101／115行把两个manifest构造成相同，遇到原ImageAlreadyExistsException，101行还误读不存在的imageTags字段；这些失败不是有效的不同镜像标签迁移复现。133／137的trace宽泛catch后只打印ERROR、退出0。169行首次大改把重复推送改成返回，但未修已有manifest迁移；187／205又读错误imageDetails字段。237／241首次使用不同manifest严格断言，确实观察修前两个镜像都含mock-tag、查询仍取旧镜像；273行补既有manifest清理，287行同程序通过。

323／327使用未安装pytest-timeout参数，head掩盖用法错误、工具未标错。337／341自测看见1 failed／18 passed：只删标签留下无标签镜像，原单标签更换测试失败。391行改为删除只有该标签的镜像，405／409目标原节点通过。437／443全文件仍1 failed／94 passed：169行引入的重复推送不抛异常；475行恢复ImageAlreadyExistsException，489／493两个原节点通过，503／509原文件95 passed。537／541再次运行相同manifest旧脚本，异常是恢复后的预期行为，不是最终不同镜像目标漏修。555／559最终程序断言不同digest、旧侧不含迁移tag、目标侧含tag，实际通过；573／579目录footer120 passed。上述目录120与原文件95／正式修订96重叠，不能相加为新覆盖，head／tail也不能证明完整逐节点状态或原pytest退出。

625行完整轨迹、37回合、36工具：Bash26／Read6／Edit4，全部串行。八个标错结果：四个早期输入或字段错误、两个错误字段脚本、一个正确修前复现、一个恢复后的相同manifest异常；另有133 catch、323错误参数、337及437真实失败被pipeline掩盖，不能以工具is_error数量概括全部测试错误。最终475行后没有源码修改，评分用的是纠错后完整FP。未声称无错或一次修改解决。

## 运输、运行成本与服务证据

HTTP38条为37生成＋1count_tokens，全部200；每条生成SSE的start／delta／stop齐、usage与adapter和CC累计一致。累计输入1673711／输出31400，单次最大输入65415／输出4149；solver233.63秒，CC230.07秒、API197.719秒，范围不同，没有据差值虚构工具耗时。manager总235.353秒，reset15.871、prep0.442、test11.8，可信setup段206.423647；保护／复制／运输不归入模型推理。queue_wait0只代表此臂。

原诊断capture于运行前即时读取engine／adapter、实际模板和config，capture过程前后ID、PID、StartedAt、restart_count保持，checkpoint manifest为 `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab`，config与实际HTTP一致。它不是整个模型运行前后连续证明；未重哈希37个live权重或GPU内存，也没有把历史capture时间改写成本次。inner service_readback false原字段保留，额外实际capture单列。完整RC0与PID1本作业成功journal相符，不用unit-not-found默认0充当终止证明。

## 资源、清理与后续

有限资源36切片按实际CID：actor19、relay19、grader15点；正式安装／测试窗口分别1／0个grader点，0个点表示未观测。actor记录memory.peak最大1131208704字节、grader860413952字节，report峰值855.789MiB单列。不能推出最低配置、连续无OOM或全局资源清理。

实际actor／relay清理成功，pre-drain residual0、gateway revoked／drained／active0；manager创建1／移除1，open／supply／cleanup_failures空。自有查询证据为空，不扩大到其它作业。正式运行、CPU历史失败、旧原raw和固定材料均保留。

题主完整读回 `runs/category2_repair_20260929/moto_cpu_20261003/moto6408_qwen36_a1_owner_readback_20261004.json`，247263字节，SHA `91f95a4a1143d7165240b505ecf5d6217e6fbad0b4e12973915212c698eeebcd`；机械回执SHA `37e813a37c4ce1960d7807e5f3f5a79ef7f217eb4885bf41d61e4aedc0fa6e88`；[双模型首轮分析](two_model_first_round_analysis_20261004.md)引用总回执SHA `b53d28a93fbe972e60b6bfbd754f752a591042ec0789afa7ebd7280fc8de4ee4`。题主确认终局后通过CLI ACK并closeout；当前无需CPU修复，普通追加暂缓。
