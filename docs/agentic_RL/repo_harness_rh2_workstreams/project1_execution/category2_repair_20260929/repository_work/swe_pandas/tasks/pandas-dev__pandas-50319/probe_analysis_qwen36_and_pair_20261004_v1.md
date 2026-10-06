# 50319：Qwen3.6首轮与两模型对照

2026-10-04。适用于新臂 `gpu1003-pandas50319-qwen36-a1` 及既有已验 `gpu1003-pandas50319-coder-a1`。新Qwen快照227件、280,036,452字节，作者逐件大小/SHA核齐；旧Coder分析和独立窄核按其已有范围复用，GPU在本次成对回执另记录旧531件、239,938,367字节重新核SHA。不改原评分、候选或输入，不重复CPU与模型采样；新增Qwen非作者窄核另存。

**两模型首轮原1分均可信，均在已验的“None或正确格式”公开契约内成功。Qwen还完成了actor编译及原样例的真实格式断言，验证证据比本题Coder首轮完整。** 两者选了不同的局部修法：Coder为空seconds补0，Qwen保留原token。Qwen原样例真实返回 `%d.%m.%Y %H:%M:%S.%f`；不能借此补写正式第二输入的具体返回分支或本候选数组转换。单次成对成功不表示稳定成功率、题目饱和或训练资格。

## 评分、修法及运输范围

| 范围 | Qwen原结果与证据 |
| --- | --- |
| 原评分 | reward1、resolved；execution/infra failure null |
| replacement F2P | 2/2成功：reported、another-dot-date；缺席／跳过／未归类0 |
| 来源P2P | 109/109成功；3组7绑定成员全部实际PASSED |
| 物理pytest | 115个唯一节点全部PASSED，3 warnings，0.22秒 |
| 实际安装／测试 | RC0／RC0；安装317.562秒，测试包装2.989秒 |
| 基线与FP | baseline `sha256:3da93f2518e48272209d08a9045857954b4b5110e68ffa8a17946e653b3c504d`；FP `sha256:de94997d6eae27396fc9bae092804438964885af028a539ce3b9d22b3a728612` |

109个来源P参考由94个精确节点、12个按原空白截断规则唯一匹配的别名、3个显式绑定组组成，覆盖113个物理P节点；再加2个新F，合计115。原回执、diagnostics、完整日志与绑定对得上，不能把109来源参考改写为109个物理PASSED。三个绑定组分别覆盖ISO反斜杠格式1项、parseable datetime2项、no-padding4项；全部完整成员存在且通过，不用别名末值掩盖缺席。

实际改动在 `pandas/_libs/tslibs/parsing.pyx::_fill_token`：先拆 `seconds, nanoseconds = token.split(".")`，如果seconds为空，直接返回原token，避免对日期分隔符 `.` 做 `int("")`，其余秒／微秒归一化保留。真实lexer输出和修前栈支持这个定位。新增分支也覆盖以点起始的token，未声称所有潜在token或日期格式都已穷尽；本轮正式参考没有回归。

完整FP有99项、59,090,036字节payload，全部entry digest重算相符且实际projection包括。其中95项位于build目录（43共享对象、52对象文件），另有修改后的pyx、生成C、源码目录的parsing共享对象，以及最后公开pytest生成的test-data.xml。build及源码目录的parsing共享对象逐字相同；生成C在同分支真实返回token，与pyx相符。没有修改正式测试／conftest或评分保护面。模型源码修法虽小，候选运输并不是只有四行源码。

正式grader从原FP重建baseline，重新Cythonize parsing.pyx（原日志3165行），编译／链接parsing扩展（3873–3880行）并复制新的共享对象（4014行），然后115项通过（5066行）。这支持正式评分确实消费候选源码，不是仅沿用actor的既有二进制。原compile_probe仍null，编译日志不能静默改成该字段已通过。

## 定位、编译、自测与完成声明

行号均指原 `attempt/trajectory.jsonl`，下表按决策意义排列。

| 原行／工具 | 实际行为 | 可成立的判断 |
| --- | --- | --- |
| 11–89，工具1–6 | 读_fill_token及guess调用；真实lexer拆出两个`.`；原调用复现ValueError；逐属性演示空seconds | 根因定位直接且具体；唯一工具error是修前原故障，不是基础设施失败 |
| 103–153，工具7–10 | 找公开测试、读原小数秒测试及helper | 有效测试路径定位，无48106的路径错误 |
| 167–171，工具11 | 一次Edit加空seconds返回token | 没有反复试错改法；生成C与最终源码相符 |
| 185–301，工具12–19 | 启动build_ext后台构建，等待并看进程／输出，最终看到parsing共享对象复制 | 与后续进程检查重叠；构建命令接tail，无独立build退出码，不能只凭管道表面成功认定构建成功 |
| 315–319，工具20 | 新进程调用原样例，真实输出正确格式，并给dayfirst原警告 | 编译后行为已修正，结合新.so和复制输出支持actor构建完成 |
| 333–337，工具21 | 无shell管道的公开guess_datetime选择集 | 62 passed、51 deselected、1 warning，0.15秒；工具结果非error |
| 351–355，工具22 | 原样例用格式相等断言；另打印无时间、无小数、微秒及纳秒4变体 | 原样例有明确oracle；其它4项仅打印，不冒称逐项oracle已验 |
| 369–373，工具23 | 公开test_parsing全模块，接tail | 113 passed、1 warning、0.17秒的完整footer；管道未独立保存pytest RC，不将它与62重复相加 |
| 387–405，工具24／终局 | 读回最终源码，说明lexer／int空串机制，并明确原样例已正确返回格式 | 完成声明与已观察原样例一致；没有Coder首轮“仍需重建”的未闭合项 |

Qwen确实等待编译结束才做后续新进程调用，并对原样例加入真实assert；这与Coder主动停止后台构建、后续仍加载旧扩展失败的行为不同。actor后台命令及全模块pytest都有管道退出码限制，因此“build命令独立RC0”不是本分析结论；复制输出、新候选.so、修后正确返回和有效pytest一起支持实际构建及验证闭合。

实际公开baseline的test_parsing模块有113个物理节点，没有受信评分新增的 `test_guess_datetime_format_dot_date_contract`。正式新增两个输入为 `27.03.2003 14:55:00.000` 与 `28.04.2004 16:07:08.123456`，均允许None或能按返回格式解析成正确datetime。本臂只在actor原样例直接记录具体格式；正式F日志没有记录具体返回值，另一个输入不能默认也返回格式。原1分证明限定契约通过，不证明每个输入必须格式推断成功；本候选未观察pd.to_datetime数组路线，旧CPU None对照不迁移为当前候选证据。

## 耗时、token及可观察并行

| 指标 | Coder首轮（复用已验） | Qwen3.6首轮 |
| --- | --- | --- |
| 求解墙钟 | 177.117秒；自测构建未闭合 | 386.155秒；CC382.439秒，API34.707秒 |
| 生成／CC回合／工具 | 27／27／26 | 25／25／24：Bash17、Read6、Edit1 |
| 累计input／output | 588,802／5,738 | 312,515／5,518；cache0，单请求input峰22,098 |
| 工具协议 | pending峰1；有后台build | pending峰1；有后台build及查看／等待 |
| 正式评分总耗时 | 1013.803秒 | 994.782秒 |
| 受信准备／评估包装 | 604.545／约329.2秒 | 591.119／321.976秒 |
| 原安装／测试包装／pytest自身 | 324.623／3.081／0.21秒 | 317.562／2.989／0.22秒 |

25个gateway请求与25个唯一assistant message ID相符，全部HTTP200、无stream_error；24工具全部按ID回收。流式60条assistant事件不等于60次生成。累计input不是单次上下文。Qwen的生成与累计输入更少，但实际求解更久：它完成了后台构建，后续四次poll命令显式请求sleep共220秒。没有精确分段足以把386秒全部归到编译，也不能从一次探索与完成标准不同的对照推出模型普遍效率优劣。

两臂工具协议最大只有1个未回收调用；Qwen没有批量工具，但build后台进程确实与后续等待／检查重叠，不能称所有进程完全串行。可用工具为Bash/Edit/NotebookEdit/Read/Write，没有子agent入口，跨agent能力不可评估。背景编译期间没有继续独立代码检查是可见行为，不能据此断言模型在受限工具面之外的并行能力。

宽预算仍为196,608上下文、每响应65,536输出、240回合、10,800秒求解及1024请求护栏；实际25请求max_tokens均65536，原CC maxOutputTokens32000元数据保留。正常end_turn、harness exit0，无预算耗尽或流截断证据。queue_wait字段0只表示该字段；准备、安装及测试时间分列，不将321.976秒称纯pytest。清理及parser分段原null保持。

## 身份、结束及当前用途

两臂同公开prompt、base、原baseline、材料 `pandas50319-dot-date-full-bindings-v1` 及code_v8；profile逐项比较唯一差异为批准的model_proxy_upstream两个模型端口，其它参数相同。来源actor和grader actual Docker image ID均为 `sha256:a3f20f616f78963bee9c87426b8a93c28fb63a6ade97d0f444115279c28f859a`，登记／grader材料中的manifest identity为 `sha256:e645e4346df9200174e8b879ad8fb7a09f64f91c7375311e2569596d054ba21e`，二者不是同一种身份字段。

101条资源采样按本job精确名字／run_id筛出33个actor、66个grader观察，各角色容器ID稳定、actual image吻合；采样间隙和全程资源未知保持。实际消费Gold资格 `ok:gold_ledger.jsonl:rpt_grading_a29b64e6`，材料 `aec98b…2979`、绑定及runner身份与Coder同版本；原runner前后digest不变。actor与grader清理成功，manager创建1／移除1、无open／supply；gateway revoked/drained、active0。当前RC0和本job精确PID1 journal成功退出相符，不借旧job终态或not-found默认0填补结束事实。

本臂同期服务读回绑定 `Qwen/Qwen3.6-35B-A3B` revision `995ad96eacd98c81ed38be0c5b274b04031597b0`，采集前后engine／adapter ID、PID、StartedAt相同、restart0，模型只读mount。下载原files_count40与列明37条不等；列明37项现场大小全部一致，含26权重分片，不声称另三件已核或显存权重哈希认证。原checkpoint_identity_verified=false、配置验证范围与compile_probe=null保留；不升级typed actor训练接线或资格。

本题首轮两模型各一次的执行已returned。作者成对分析完成，新增Qwen窄核只覆盖这次原件与语义，不重做旧CPU/Coder验收。当前没有需改材料、CPU补评或模型重解的具体问题；保留两种合理修法及两模型验证质量差异作为限定诊断观察。普通重复仍暂缓，不为单次成功自动增加采样；成对成功不等于稳定成功率、训练饱和或准入。

## 原件与核验入口

- [两模型总回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/probe-swe-pandas-50319-20261003-v1_pair_execution_receipt_v1.json)：SHA `3bffd0623ab64925274dc9b879692f3902d71d2b6fb7aa2d367b031cb0497f0e`。
- [新臂机械回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/pandas50319_qwen36_execution_receipt_v1/execution_receipt.json)：SHA `e1b22549ff2dcaae46a5a53bf82701001a17a5239701299c5fa54f4c234e3c6d`，只对账执行。
- [作者核验与计数原件](../../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/gpu_analysis_20261004/pandas50319_qwen36_a1_v1/evidence.json)：SHA `5e913c93f8a362115e069f413b472ad25e68e9b6f71f71bde21625bf69347cd0`；[轨迹阅读副本](../../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/gpu_analysis_20261004/pandas50319_qwen36_a1_v1/trace_normalized.json)、[源码diff](../../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/gpu_analysis_20261004/pandas50319_qwen36_a1_v1/source_delta.patch)。
- [原评分日志](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pandas50319-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-pandas50319-qwen36-a1/grading/eval_logs/evallog_gpu1003-pandas50319-qwen_5f6a14d1.eval.log)、[既有Coder分析](probe_analysis_coder_20261003_v1.md)。所有原件不回写。
