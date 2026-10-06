# 15184：Coder首臂轨迹与两模型比较

2026-10-03 15:32（Asia/Singapore）。作业`gpu1003-mypy15184-coder-a1`，code_v7；题主原件回读见[冻结JSON](coder_first_arm_trace_20261003.json)，SHA `4fde288ea947e1f199b67c7f1f64e6b5f1814745148d94832054592e723d98e9`。142件闭合集合的SHA/大小相符，完整1422条基线与102条原FP/评分投影已逐项核实。两模型首轮已运行并交回，分别保留原raw1，不能据此称稳定成功或训练通过。

## 修法与评分依据

Coder仅将`MessageBuilder.assert_type_fail`的两次独立`format_type`改为现有`format_type_distinctly`联合格式化。核心源码SHA `2ca8bce8…`与已验Qwen3.6候选逐字节相同。helper通过`collect_all_instances`递归类型参数，顶层`a.C/b.C`和嵌套`List[a.C]/List[b.C]`均有依据；`checkexpr`中的类型是否相同判断及原返回值没有改动，有效断言继续成功。

正式3F/2P五参考均真实执行并通过，四分区没有缺席、跳过或参考外解析。安装与测试段RC0，失败命令为空；可信测试恢复/保护、`/testbed/mypy`来源、runner前后摘要、终止与双层清理已核。原FP102条为97个cache文件、4个独立复现脚本及`mypy/messages.py`，投影保持全部102条，未净化或替换。四脚本只构造公开顶层负例和合法断言，不改受保护测试。原Qwen测试文件修改被可信投影排除的警示继续保留，不能混称两份FP相同。

## 方法、定位与纠错

第1个工具按文件名泛搜未直达根因；第2个工具搜索`assert_type`即找到`messages.py/checkexpr.py`。第3个工具整读大型`messages.py`，第4/5个工具定位失败诊断；第6–10个工具读联合formatter及名称重叠收集，形成明确根因。第11–14个工具构造公开C/C复现，第15个工具完成唯一实现编辑。第16个工具输出a.C/b.C，仍退出1，这是预期类型不匹配，不是修复失败。第17/18个工具核合法断言无报错；这里仅证明有效断言保持，不能单凭无诊断证明“无歧义诊断仍简洁”。

工具22使用`-k assert_type`没有选中任何项，真实退出5；工具23改为`testAssert`，11项通过。这是一次选择错误及随后的纠正。三个error标记中两项为预期mismatch（工具14/16），只有工具22属于操作问题，不能把三项都计为工具失误。

## 验证的实际范围

工具19精确公开`testAssertType`通过。工具20直接执行公开expression文件组，归档中的完整输出为179项通过；大输出在轨迹只显示预览，题主从`cc_home.tgz`对应tool-result原件核完整footer。工具23的11项也有完整成功输出，两组选中范围重叠，不能相加为190项独立覆盖。工具21的API负例打印`exit_status:1`，外层Python退出0只代表脚本完成。

模型没有自行显式构造嵌套例；嵌套依据来自原helper源码与正式受信nested参考。模型最终“All existing assert_type related tests pass”超出所选范围，未选中的`testTypingSelfAssertType`不能算通过；“无回归”也只适用于观察到的组。本题正式五参考与候选语义已支持当前有限用途，这项P3表述问题不要求机械扩大CPU或重新采样。

## 工具、并行与效率

实际25次消息生成/adapter回合、24工具：Bash14、Read5、Write4、Edit1。网关文件另有1次`count_tokens`，合计26条记录，不能计为26次生成。44条assistant事件对应25个不同消息；首条user消息包含CC环境提醒和独立的1830字节任务block，任务block与Qwen已验公开交付SHA `2efeb37e…`一致。

每轮只请求一个工具，未观察到工具层并发；部分文件读取与a.py/b.py写入可批量完成，但没有逐工具重叠时间或执行层并发验收，模型并行能力不可判断。公开pytest输出创建12个xdist worker，这是测试进程并行，不能算模型并行工具。

Coder求解52.738秒，CC49.153秒/API32.280秒；attempt总97.947秒，grader另102.904秒，均按原字段分列，嵌套时间不相加。累计input864729、output3051、cache0，单次最大input42603。整文件读取使长内容随后反复发送；比Qwen更少回合/工具并不等于累计输入更省。CC4.39992美元是`slime-actor`估值，不是GPU实付。

| 单次首轮观察 | Qwen3.6 | Coder |
| --- | --- | --- |
| 正式评分／语义范围 | raw1／顶层、嵌套、有效断言保持 | raw1／相同范围、相同核心源码 |
| 求解秒数 | 62.946 | 52.738 |
| 生成回合／工具 | 40／39 | 25／24 |
| 累计input／output | 528184／6067 | 864729／3051 |
| 单次最大input | 21402 | 42603 |
| 自验边界 | 两次自写测试错误已修；管道tail不能单独证pytestRC0 | 一次选择错误已修；全量相关测试陈述过宽 |

这只是各模型一次同题观测。code_v5与code_v7的7个共享成员字节不同；本题材料、实际镜像、完整baseline、任务prompt、五参考及预算相同，实际generated scripts摘要`eb6990fb…`也相同。四个关键运输入口和15184专属AST节点相同；新增其他仓库分支没有改变本题观察到的脚本及参考，不声称同一棵runtime。

## 身份与当前用途

Coder实际服务在启动本job前约0.6秒完成读回，engine/adapter均restart0；Qwen3-Coder下载revision为`b2cff646eb4bb1d68355c01b18ae02e7cf42d120`，挂载自volume只读`/model`，实际路由和25次生成对应。本次另核25份列出文件大小及下载manifest/template/config SHA，其中16份为safetensors分片。manifest声明files_count=28却只列出25项，不能将25项称为25份权重，也不能推断未列出的3项。HTTP revision和model_checksum仍null，没有重新hash全部权重或GPU内存加密自证；旧`checkpoint_identity_verified=false`、`config_only=true`等标记不改。

Qwen的Q13已由题主另写[40请求运营来源补证](q13_operational_identity_supplement_20261003.json)，不冒称原Q12审覆盖Q13；40次网关/adapter/后端完成与同服务历史来源相符。此补证仍不等于当时逐作业snapshot或权重驻GPU自证，旧false标记保持。本题可记录两份一次性候选的有限语义与执行观察；普通追加采样当前按[覆盖优先规则](../../../overnight_watch_20261003.md)暂缓，稳定性未知。无新增题面/评分修复或CPU作业，训练、留出资格均未增加。[最终题主配对验收](two_model_first_round_acceptance_20261003.md)已绑定新增非作者执行链、语义及Q13身份报告；总账returned/ack且活动请求清空。冻结JSON中的当时pending项由新增配对记录承接，不改旧JSON。
