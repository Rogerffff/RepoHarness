# F5EB Qwen 首臂：题主七维分析

2026-10-03。**原1／8-of-8保留，生产全文与已验证CPU C1相同；修法正确、局部，公开测试四项预期同步合理，无新材料阻断。** 当前仅Qwen首臂已完成，Coder未执行，活动请求未按双臂完成ACK。本轮不授训练资格。

固定材料R6／['r2e-mr-076', 'r2e-mr-077']，原作业`gpu1003-coveragef5eb-qwen36-a1`。完整版本、原件SHA、各工具ID与返回时间见[JSON](model_analysis_qwen36_a1_20261003.json)。题主核推理、参数、诊断摘要和完整源码／公开测试改动；[非作者语义核查](../../reviews/non_author_f5eb_qwen36_semantic_review_20261003.md)与[执行核查](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/coveragepyf5eb_qwen36_a1_execution_review.md)分别核候选和运输／评分闭环，本轮未新跑CPU、模型或远端。

## 修法与根因

在branch has_arcs块中给totals加入self.total.n_executed_branches/n_missing_branches，并给每文件summary加入对应nums属性。沿原逐报告文件累加，不硬编码、不拿最后文件代总计、不误用partial行数；测量has_arcs支持保存数据，morfs/include/omit限定实际报告子集。可选每文件成对字段符合已定A/rb3h。完整生产文件与已验C1完全同字节。

## 定位与纠错

L61正确找到jsonreport.py与缺字段位置；L76/L80读取results.Numbers，L86确认covered=n_branches-n_missing而不是partial行数。改前MCVE误把file对象作为outfile(L116)，L122理解API参数并改成路径，L130真正复现缺字段。L144/L158增加两处字段后验证。

工具返回时间相对首条gateway请求：L61：2.686秒；L80：4.159秒；L116：11.518秒；L130：13.795秒。这是可定位证据的到达时间，不代表纯模型思考时间或工具执行时长。

## 工具使用

20调用：Bash12、Read5、Edit3。3个双调用批次用于独立目录/文件读取；find包含.venv噪声。两项is_error为outfile API误用与源代码增加字段后原字典测试失败，第二项是预期格式同步的正常开发反馈。另L262扩测tests/test_report.py不存在，L266输出no tests ran/ERROR但head管道掩蔽is_error；这是第三项可观察失败命令，不能计为扩展回归成功。其后只重跑JSON四项，重复验证。

原FP包含公开测试改动；`patch_hygiene.test_files_modified=false`不是“没有改公开测试”的证据。完整投影包含原候选，无审查源码与正式评分候选分叉。没有runner/conftest/私有评分修改；具体质量与污染路径按非作者全文核查保留。

## 并行机会与执行能力

共有3个同一助手消息内的双工具批次，工具ID和返回逐一对应；批次中是独立检索/读取。回传顺序有倒置，可确认多调用协议支持；没有工具开始时间，实际重叠与节省时长不可判断。依赖源码状态的修改和验证须按先后执行；可能共享目录／测量库的测试不机械并行。

## 验证质量

改前JSON4通过并MCVE证明缺字段；源码改后MCVE看到数值，原branch完整字典1失败3通过；保持原四测试与断言结构，仅给两份预期各补covered=1/missing=1。此后4通过，扩测路径错误后只重复同4通过。最终MCVE核totals总计恒等式并核branch=False无两字段。MCVE打印totals54分支含coverage自身，单文件1/1；打印不能替代精确多文件/子集判定。正式8键和不变C1控制证据支持保存、零分支、目的地弧计数、多文件/子集语义。模型把每文件也称issue必需略宽，但实现属于许可范围；无完整全仓回归。

## 完成效率

| 口径 | 实际值 |
| --- | --- |
| 累计输入／输出token | 276152／5646 |
| cache read／creation | 0／0 |
| 生成HTTP／count_tokens | 18／0 |
| CC回合／工具调用 | 21／20 |
| solve／CC wall／CC API 秒 | 42.315／38.725／35.218 |
| gateway生成响应累计秒 | 34.686 |
| actor开始至清理收口秒 | 88.692 |
| trusted init／Git sanitize秒 | 23.629／2.35 |
| grader总计／实际测试秒 | 28.11／2.039 |
| grader报告peak_memory_mb原字段值 | 268.109 |

cache为0，反复整文件读入会增大累计上下文，但没有对照运行，不能量化可省token。gateway累计含adapter／运输，不等于纯GPU推理；CC API外残差3.507秒也不能当纯工具时间。actor准备／清理和grader独立核，不混作模型效率；各阶段子项不穷尽总时长。grader queue_wait=0仅是本次评分器排队，不是全批模型队列等待。CC估计费用1.521910 USD是本地别名估计，真实账单未知。

## 结束、用途与接续

completed、CC success/end_turn、harness exit0、正式testRC0，无预算/链路截断。可作固定076/077、A/rb3h单次能力结果；Coder未执行，配对和稳定结论待完整请求。没有新材料/评分污染，当前不增CPU和不重跑相同矩阵。

**CPU动作：**本轮无新增必跑CPU；source与已验C1字节相同，公开测试正确预期同步，正式8键通过。

实际context/output/turn/wall预算196608／65536／240／10800秒；实际生成、权重revision及BF16/TP1服务按固定执行证据关联。上限配置不等于实测196K能力；gateway checkpoint_identity_verified=false保留为身份链限制。资源仅闭批有限采样，未采间隙未知，宿主GPU字段不归因每题。全部原件、旧分数和各次自测失败保留，不能以重复成功替换失败，不能把单臂当稳定能力或训练准入。
