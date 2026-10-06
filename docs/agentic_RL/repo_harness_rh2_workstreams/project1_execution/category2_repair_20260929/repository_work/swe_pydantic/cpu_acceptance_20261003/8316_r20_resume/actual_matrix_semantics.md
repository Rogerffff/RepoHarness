# 8316：实际24行矩阵与失败语义

2026-10-03。[最终组合非作者核查](../../reviews/non_author_8316_r20_combined_cpu_review_20261003.md)及[题主核收](../../coordination_20261003/8316_r20_combined_cpu_owner_acceptance_v1.json)已通过，[固定普通GPU探针](../../tasks/pydantic__pydantic-8316/probe_request.json)已提交并实际通知执行者。正式矩阵由R14五行和R20十九行组成；没有把24行写成在同一版本下执行，也没有覆盖旧超时记录。公开材料与v3断言不变，两版差异是精确镜像／材料绑定下的准备预算。当前证据支持本版本普通探针，不授予训练资格；GPU实际兼容性和模型结果仍待。

旧五行 `noop/gold/keep_digit/scan/w_example_only` 的实际奖励为0／1／1／1／0，复用[原实际独立核查](../../reviews/non_author_8316_partial_cpu_review_20261003.md)。gold与两种合理算法均通过全部144参考，包含F2P参数内部的11条新增断言。其余既有合理实现保留原纯函数与语义证据，没有再做完整项目评分。

R20作业`pyd8316-formal-20261003035447-r20-f5f0f`于03:54:50–05:04:36 UTC在CPU-a slot1实际运行，十九行奖励全部0。每行1个F2P和143个P2P都有正式终态，无参考缺失／跳过；安装均RC0、测试均RC1，属于候选断言失败。[题主正式读回](../../coordination_20261003/8316_r20_formal_owner_readback_v1.json)核了2,464件原件、144逐ID日志、分区、候选内容及基线身份。

各行在F2P参数 `CAMELToSnake-camel_to_snake` 内的首个实际失败如下。完整日志中的额外P2P失败继续保留；断言失败之后的测试体不会执行，不能称每个错误候选都执行了全部11个新增断言。

| 新候选 | F2P参数内实际首个失败输入 | 额外旧P2P失败数 |
| --- | --- | ---: |
| `w_acr_max8` | `loadCONFIGURATIONFile` | 0 |
| `skip_if_digit` | `base64URLEncode` | 0 |
| `no_lower_upper` | `getHTTPResponseCode` | 0 |
| `acr3` | `userIDToken` | 0 |
| `w_last_only` | `XMLToJSONConverter` | 0 |
| `w_window8` | `convertXMLToJSONViaHTTPRequest` | 0 |
| `w_skip_nonascii` | `ÜberHTTPClient` | 0 |
| `no_trailing_upper` | `parseURL` | 0 |
| `skip_if_underscore` | `__HTTPResponse__` | 0 |
| `w_count2` | `convertXMLToJSONViaHTTPRequest` | 0 |
| `only_if_no_us` | 原CAMELToSnake断言 | 0 |
| `lower_or_start` | `XMLToJSONConverter` | 0 |
| `w_len_cap` | `loadCONFIGURATIONFile` | 0 |
| `lower_or_start_la` | `__HTTPResponse__` | 0 |
| `no_digit_split` | `base64URLEncode` | 8 |
| `w_mid_underscore` | `get_HTTPResponse` | 0 |
| `literal` | 原CAMELToSnake断言 | 0 |
| `lead_only` | `getHTTPResponseCode` | 0 |
| `no_digit_upper` | `base64URLEncode` | 2 |

因此长缩写、多个缩写、串中位置、下划线、数字条件与非ASCII前缀回退等机制分别被实际断言拒绝。`ÜberHTTPClient` 的分词仍发生在ASCII的r/H与P/C位置，没有规定非ASCII字母本身的边界。数字类的旧兼容失败与新增缩写失败分开记录；已有两种合理数字处理正对照通过，不把范围外歧义作为新扣分要求。`only_if_no_us/literal` 在原断言就失败，不能把它们的拒绝归功于新断言。

真实运行使用f939…派生镜像、UID54322、Python3.8.19/core2.14.5及`/testbed`源码。十九个FrozenPatch只改alias_generators.py，451项完整baseline的canonical摘要和各候选实际内容均核对；baseline的environment字段仍null。来源parser给169个键，不代表全部173个原始pytest节点都合法解析；144个正式参考逐ID已核，无已知空格截断影响。

708次保存Docker调用均RC0；十九次控制面保护为129.630–315.576秒，账本明确记录reset900和固定政策身份，其中一次确实超过旧300秒。评分总时长之和3,773.022秒、单行最大344.665秒，报告内grader峰值最大664.258 MiB；这些是CPU评分开销，不是模型求解效率。manager十九建十九删，末尾本run容器／网络查询RC0空。该轮完成不证明共享I/O问题永久解决。旧R14第六行保护300秒超时的infra/null保持原样，新的同名候选0分属于另一个R20 job。

公开actor `pyd8316-actor-20261003050519-r20-f3934`于05:05:23–05:06:20 UTC在slot0运行，[32件原件题主读回](../../coordination_20261003/8316_r20_actor_owner_readback_v1.json)通过：实际f939…、UID54321、Python3.8.19/core2.14.5，CC2.1.205，四个桩请求和三条Bash命令0／1／0。原公开HTTPResponse仍为httpresponse，按预期复现TARGET_EQUALS False；原公开snake2camel测试9通过。原题面CRLF在实际文件与首请求中保留，逐原字节比较；420个解码请求字符串未出现完整私有补丁及核查的四个非公开例子。实际容器无Mounts/Binds，受控网络与清理记录通过，收尾agent进程0。固定桩诊断不计作新基座样本，也不替代实际GPU镜像与模型测试。

固定请求`swe-pydantic8316-behavior-v1-20261003`按probe-wide-v1申请Coder30B与Qwen3.6首次各1条，输入SHA为`d935ed00f0744ee8c4a248487d333e5d69fb4cd778f2ae06e349a283253ae3ff`，生成后snapshot与3,279个绑定已[核收](../../coordination_20261003/8316_r20_generated_probe_owner_readback_v1.json)。下一步核实际GPU两模型首轮、完整候选语义和效率。若GPU使用不同实际镜像，准备预算政策须由发布者提供准确兼容版本，不能自由覆盖900秒或冒用CPU镜像身份。旧材料、失败、分数与原件全部保留。
