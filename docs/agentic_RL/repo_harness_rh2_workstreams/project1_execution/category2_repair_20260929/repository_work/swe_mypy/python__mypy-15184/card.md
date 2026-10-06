# mypy15184：公开复现、嵌套消歧与有效assert_type保护

2026-10-03 15:32（Asia/Singapore）。base `13f35ad0915e70c2c299e2eb308968c86117132d`，mypy1.4。**正式材料`mypy15184-nested-nominal-types-v2`的R10 CPU四候选0/1/0/0及两模型各一次首轮语义/执行观察已验收。** 两臂原reward1、正式3F/2P五参考全通过，核心源码相同，正常结束及双层清理正常；见[配对验收](two_model_first_round_acceptance_20261003.md)。总账returned/ack、活动请求清空。本题无新增CPU/GPU作业；有限运营模型来源已补核，精确GPU驻留权重身份和稳定性仍未知，不增加训练或留出资格。

目标是`assert_type`失败诊断能够区分同短名的不同类型，包括嵌套类型；无歧义保持简洁，有效断言继续成功并保留原表达式类型。原SupportsIndex程序在固定base不触发，现[公开题面](public/problem_statement_v1.txt)按10-02 R-f安排使用已复现的两个模块各定义C的例子：base输出C/C，gold输出a.C/b.C。09-25/09-29保留原题面的条件留在原记录，不作为当前指令。

**公开例本就应报告类型不匹配，gold修正文案后mypy仍退出1。** 私有helper退出0仅说明输出匹配检查成功；不能用“gold应该Success”验这段程序。题面没有gold函数、私有case名或隐藏输入；[fresh静态审](../reviews/fresh_public_reader_20261003.md)只见固定公开材料和base。新[中性环境brief](public/development_note_20261003.md)只有非fresh边界核，不冒称被原fresh审覆盖。

原正式评分只覆盖三参考，四候选实测0/1/1/1，漏判两种错误修法，见[原矩阵](original_cpu_readback_20261003.json)。正式修订保留原三case正文，新增一个嵌套F2P，并选取base已有`testAssertType`作为有效断言P2P，共3F/2P五键。F2P是修复前失败、gold通过的参考；P2P是修复前后均应通过的参考。另四项开发case和含Self的六项actor公开回归不计入正式五键。

嵌套首版误写小写list，导致gold也失败，原件保留；v2按固定base的`force_uppercase_builtins`配置改为List，源码注解仍是list。一个新增嵌套F2P和一个有效断言P2P分别保护不同语义，不能相互替代，依据见[护栏依据](p2p_basis.md)、[私有校准](nested_guard_cpu_readback_20261003.json)及[发布回读](publication_readback_20261003.json)。

| 候选 | 原评分实测 | R10正式评分实测 | 新评分实际区分 |
| --- | --- | --- | --- |
| noop | 0 | 0 | 三个F2P失败，两个P2P通过 |
| gold | 1 | 1 | 五参考全部通过 |
| gold＋全部assert_type报错 | 1 | 0 | 仅有效断言P2P失败；int/Literal正确断言被误报 |
| 仅限定顶层类型名 | 1 | 0 | 仅嵌套F2P失败；仍为List[C]/List[C] |

正式作业`mypy15184-revised-r1-20261002T214419Z-e743aa`使用R10冻结源码及新prepared。每个候选收集/执行/解析五键，缺席、跳过、参考外执行均0；实际安装、/testbed源码、测试恢复/保护、源码投影、runner摘要、UID/资源和退出/清理已核。负对照因预定断言失败而得0，不是环境或评分链失败。见[作者原件回读](revised_cpu_readback_20261003.json)、[运行链增量核查](../reviews/non_author_15184_r10_execution_trace_20261003.md)、[反证增量核查](../reviews/non_author_15184_r10_falsifier_20261003.md)及[CPU条件收口](cpu_probe_acceptance_20261003.json)。两非作者已见gold/私有上下文，独立回读原件，非fresh；旧10174审查报告不变。

R10材料摘要：public`77b85678…`、grading`3a3c4e78…`、environment`de06cc63…`，完整身份及55份原件归档SHA见收口记录。R10 manager新增DVC前置条件，本题为None；不能声称manager字节未变。每条成功安装命令的独立数值rc缺席、ledger包版本为`?`、BASHENV写入检查未测等边界均保留，不推导完整隔离或训练资格。

[GPU请求](probe_request_20261003.json)`swe-mypy15184-nested-nominal-v2-20261003`固定SHA `623bc39612a9812e92b3c5ec218480e916e3c4dae219c4e4f17d7e85056e993e`，Qwen3-Coder-30B-A3B-Instruct、Qwen3.6-35B-A3B各1次、预算`probe-wide-v1`已完整返回。两臂首条solver实际任务block、兼容/镜像与正式评分已核，任务block SHA相同。request revision5已ack、task progress revision13进入closeout并清空活动请求；冻结GPU回执not_sent/request_returned字段保留当时状态。

本题当前无已知待运行CPU或GPU作业。按[完整性与资源依赖](../result_completion_20261003.md)已逐轨迹核方法、定位、工具、并行、验证及效率，截断输出已从归档补齐。按当前覆盖优先暂停尚未开始的普通追加采样，不机械要求每模型三次；只有新的具体失败或材料/评分缺陷才登记修复与按影响复验。

## 首臂方法与当前接续

Qwen3.6原候选只将`assert_type_fail`改用联合`format_type_distinctly`；该helper遍历内层类型参数，因此顶层与嵌套限定均成立，未改有效断言判定/返回值。模型修改的测试没有进入评分投影；源码与正式五参考共同支持此范围。见[七维轨迹回读](qwen36_first_arm_trace_20261003.md)、[题主原件回读](qwen36_first_arm_trace_20261003.json)、两份[执行链审查](../reviews/non_author_15184_qwen36_execution_trace_20261003.md)/[语义反证审查](../reviews/non_author_15184_qwen36_semantic_20261003.md)及[首臂收口](qwen36_first_arm_acceptance_20261003.json)。

Qwen求解62.946秒、40生成/39工具；8错误中6个预期mismatch、2个已纠正自写测试错误。Coder求解52.738秒、25生成/24工具；3错误中2个预期mismatch、1个已纠正空选择RC5，最终自验陈述过宽登记P3。模型未自己直接测嵌套，正式受信参考另证；Qwen管道tail不证独立pytestRC0，Coder179项/11项组重叠不能相加。完整[Coder轨迹与两模型比较](coder_first_arm_trace_20261003.md)及[固定配对收口](two_model_first_round_acceptance_20261003.json)已绑定新增非作者报告；无具体修题/评分缺陷。
Q13新增[40请求运营来源补证](q13_operational_identity_supplement_20261003.json)及[独立窄核](../reviews/non_author_15184_q13_identity_20261003.json)支持有限来源归因，不冒称Q12旧审覆盖Q13。Coder有job前服务读回及25生成对应；manifest列25文件/16safetensors但声明28，未列3项未知。旧身份false、单臂收口、raw1和完整FP保持；各一次观察不证明稳定性或可靠性能排序。
