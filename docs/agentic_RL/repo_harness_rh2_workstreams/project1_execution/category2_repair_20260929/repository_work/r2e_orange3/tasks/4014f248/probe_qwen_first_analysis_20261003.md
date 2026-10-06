# Orange4014：Qwen 首轮原生修法与行为分析

2026-10-03。**本次Qwen正常完成，原五项源码/构建工件正式得1，27/27参考全PASS；作者判断符合089公开数值区间要求，待新增行为分析的非作者窄核。Coder尚未执行，原请求保持claimed和活动指针。** 本文只读原证据，没有启动CPU、GPU、评分或独立源码重建；已有执行/语义审查按范围复用。

## 1．修法与问题解决方法

唯一源码Edit修改`Orange/preprocess/_discretize.pyx`的`split_eq_freq`两个返回点：`n>=llen`先计算原相邻中点，再`list(numpy.unique(points))`；计数分支保留原权重/中点算法，仅最终返回也去重。有限有序输入的相等阈值被合并，正常互异阈值不变，仍由原`low<high`断言约束区间。没有十进制舍入、硬编码样例、删除断言或修改输入；`entropy_normalized1`至尾部字节不变。候选实际公开复现得到`[1,1.0000000000000004]`及三个有效区间，显示名称“1 - 1”是原格式精度造成，不是数值边界相等。

输出箱数可以少于请求n，公开说明也允许实际箱数减少，不能强制原例一定4箱；这也不授权任意退成单箱。r089正式增强覆盖两个分支、极近/混合值、`arange(100)*1e-12`的四组等频结果，避免将先舍入为0的捷径误奖。其它26项参考也通过。源码机制、实测与正式评分相互支持，未发现具体语义缺陷；范围非任意输入或全部Orange回归。

## 2．定位、假设与纠错

题面和中性brief已有问题例、模块与构建/测试提示。本次不是未知仓库盲定位。时间从首个实际generation请求到结果，含生成/工具/往返；事件号对应原trajectory行。

| 事件 | 实际行为与判断 |
| --- | --- |
| 11→15、25→29 | find/grep定位EqualFreq（1.042秒），Read完整discretize.py（1.502秒），追到Cython调用。 |
| 39→43、53→57；thinking 63 | find扩展文件，Read pyx（2.959秒）；初步指出相邻中点可能重复，但还未实测核清。 |
| 71→75、85→89 | 题面baseline实际AssertionError（6.284秒），随后打印重复中点及False数值区间。 |
| thinking 95、99→103、thinking 109 | 数组默认打印均为1；109误判distribution发生舍入且np.unique将原值视同。没有立即按此错误改源码。 |
| 113→117、thinking 123、127→131 | 逐值repr表明四个原值确实互异（15.341秒），123纠正显示误读；再实测相邻中点后两项相等（18.463秒）。 |
| thinking 137/151、155→159、169→173、183→187 | 比较Python调用点与Cython源头两种修法，选择两返回分支去重；另核unique、digitize、dict.fromkeys。 |
| 201→205、219→223、237→241 | 唯一Edit（43.705秒），实际Cython/GCC/link/copy构建RC0（45.896秒），新Python进程题面复现成功（48.343秒）。 |

模型能用repr反馈纠正误读，并在修改前把最终原因落实为中点重复。不能写一路定位正确，也不能把“源码Edit一次”当推理从未走弯路。对unique/dict、Python/Cython位置多次重议，以及已知微小浮点的重复打印造成额外回合，但没有多次错误源码修改。

## 3．工具与原生开发

实际26工具：4 Read、21 Bash、1 Edit，最大batch1。唯一tool_error是baseline缺陷复现，不是构建或候选失败。实际`python setup.py build_ext --inplace`输出包含Cythonizing、编译、链接和copy，工具RC0；不能把单有命令或find旧so当已经重建。原FP包含pyx、生成c、源码目录so、build/lib同so和o共5 regular modifies，全部直接投影，两个so SHA相同；评分对象明确包括这些构建工件，并非仅源码补丁。

轨迹未见网络、gold、隐藏测试/私有grader或未来Git读取；未修改公开测试、依赖、runner/控制。pipfreeze一致，缓存/排除目录集合实际变化，不能称工作区无任何其它变化。没有观察到答案通道不排除模型先验记忆。

## 4．并行

所有26工具均逐次单请求，未观察成组多工具或实际并行。初始源码/公开测试读取，以及修改后的独立只读检查存在潜在可并行操作，但本次未尝试；缺工具起止时段，不能据此评估模型或执行层并行能力，亦不能把本次串行解释为模型不会并行。

## 5．验证质量与不足

255→259公开TestEqualFreq为3PASS，269→273完整test_discretize为26PASS。283→287脚本包含普通阈值、少distinct和100to4的实际assert，近值场景本段只打印。297→301的test_preprocess为18PASS完整footer，但接`head`且无pipefail，工具RC不能独立证pytest RC；原正式grader另有testRC0及27项完整日志。

315→319虽注释提close，实际输入为普通1..8/n4，只打印`[2.5,4.5,6.5]`。329→333用`[1,1+eps,2..9]`/n4，输出`[1.5,4.5,6.5]`并断言各数值区间；两段都没有展示计数分支重复中点的修前/修后精度失败对照。该分支精度覆盖来自**正式r089既有审查**，不冒称模型自测已完成同样覆盖。343→347的常数输入空阈值只打印，385→389近值各比较True也仅打印，不能把“PASSED”字样当assert。371→375重复完整公开文件26PASS。

brief要求的**`extension.__file__`直接读回没有执行**。实际build、新进程行为和变更so字节支持新工件生效，但不是该路径的直接证明。正式installation为**SKIPPED、RC=null、compile_probe=null**，grader直接应用源码与编译工件；**没有独立source-only重建验证**。这些已知验证局限需保留，当前没有具体缺陷可据此把raw1改成0或要求重跑来抹掉原事实。

## 6．效率

| 指标 | 实际值 |
| --- | ---: |
| 累计输入 / 输出 tokens | 641074 / 10290 |
| 最高单次输入 / 输出 tokens | 34247 / 1279 |
| CC turns / 实际generation / 全HTTP请求 | 27 / 27 / 28 |
| solve墙钟 / CC总时长 / CC API（秒） | 86.681 / 83.279 / 65.0 |
| actor trusted_init（秒） | 203.903 |
| grader总时长 / wrapper测试段（秒） | 199.618 / 2.471 |
| 实际TEST marker区间（秒） | 1.45 |
| 派发后整个作业（秒） | 529.055722 |

累计输入包含各轮上下文重复，输出包含thinking；API是等待/传输在内的时间，不是纯GPU计算。工具call时间缺失，只有结果时间，无法算纯工具耗时。派发前排队未知；grader queue_wait=0只限评分管理器。trusted_init与求解分列，整个作业约9分钟主要包括两侧环境准备，不能说模型解题用了9分钟。wrapper、TEST marker和pytest正文时长口径不同，原diagnostics未给细分grader phase（null），不伪造它们。CC costUSD是估算，不是自托管账单。

累计输入641074不是峰值上下文；实际最高单次34247。多次重议修法位置/去重实现、再读刚改的pyx（357）与无修改再次跑全文（371）形成可避免重复；部分复现可合为一次逐值repr、原函数中点与修后assert。必要Cython重编和修前/修后新进程复现不能删除。若改善轨迹，优先补extension路径证明、给两个精度分支直接断言，而不是继续重复普通全套测试。建议没有重新运行来制造节省量或补写原轨迹。

## 7．结束与稳定性

本次completed/end_turn/exit0，无观察到的length、压缩、预算截断、缺评分或不完整轨迹。实际probe-wide-v1为196608 context、65536单响应、240回合、10800秒求解；最高单次prompt34247/output1279，不证明196K长负载。CC metadata32000与实际每HTTP/adapter65536分记，未据元数据推断隐藏32K截断。

Qwen正常完成1/1、本次语义受支持1/1；Coder尚未执行（已完成0次、仍缺计划1次），没有Coder失败率或两模型比较。没有重复样本，稳定性未知。原`r2e-orange4014-r089-cpu-native-sysconfig-v1-20261003`仍claimed，不ack、不清活动指针。下一步完成新增行为窄核，等待Coder首轮及全批第二阶段重复采样。没有发现需新CPU补修的具体材料/consumer缺陷；GPU与题主端到端工作仍未结束。

## 原件、身份和用途

- [trajectory](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v15/results/gpu1003-orange4014-qwen36-a1/attempt/harness/trajectory.jsonl)
- [frozen_patch](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v15/results/gpu1003-orange4014-qwen36-a1/attempt/frozen/frozen_patch.json)
- [baseline_tar](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v15/results/gpu1003-orange4014-qwen36-a1/attempt/frozen/baseline.tar)
- [result](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v15/results/gpu1003-orange4014-qwen36-a1/result.json)
- [prompt](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v15/results/gpu1003-orange4014-qwen36-a1/solver_prompt.txt)
- [gateway](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/services_v13/qwen36/gateway/gpu1003-orange4014-qwen36-a1/requests.jsonl)
- [terminal_snapshot](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/gpu1003-orange4014-qwen36-a1_terminal_snapshot_v1.json)
- [原执行/语义独立报告](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/q15_orange4014_qwen36_a1_execution_semantic_review_v1.md)，JSON SHA `12bf75a1d0b4939886dde2bb1695b6bfcacb07a5e43cb5c1e0676652a745d613`。
- [作者完整文本/工具/源码/时长索引](../../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/q15_orange50_4014_qwen_first_author_evidence_v1.json)，SHA `a128bdc798a59159fadd1b7b4965ca4add9a2c7cd96598986e05da354cd440f2`；[封闭原件清单](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/gpu1003-orange4014-qwen36-a1_closed_manifest_v1.json)。

本次实际GPU actor/grader为`sha256:255669f41a10dcf6a8c4fae6f121532da65d4f68cec5b53930b4f609e89624df`；CPU验收镜像不是本次实际GPU镜像。r089/code4、公开题面与brief精确交付、baseline重建、原FP及double cleanup复用原独立审查。作者本次再核封闭89文件共81,147,426B的SHA/size、源码差异、全部模型文本与工具。原request本地未另存独立raw文件，身份来自terminal_snapshot.original_request规范重建及dispatcher SHA匹配，不能称独立原请求文件读回。

Qwen来源绑定沿本次作业前实际capture、固定revision `995ad96eacd98c81ed38be0c5b274b04031597b0`、只读模型mount及下载manifest（SHA `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab`），不是物理GPU权重证明。HTTP revision/checksum为null、weight_version默认，无逐POST engine/权重attestation；manifest宣称40但列37文件的局限保留。

资源只有约15秒有限宿主样本，有CPU throttle，不证明完整峰值、最低内存或全程无干扰；退出容器的无效内存样本不能读作0。原schema的env_qualification缺失、material identity/revision部分为null，本轮用外部固定材料/运行证据关联，不能冒称typed训练合同已接通。gateway first-byte 1800与common.py sock_read 900不同，不证明全链1800边界。本次用途为题目/环境和基座修法诊断，不授予训练或留出资格。
