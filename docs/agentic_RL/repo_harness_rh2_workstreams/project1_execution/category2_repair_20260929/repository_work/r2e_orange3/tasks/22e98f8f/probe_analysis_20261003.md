# Orange22：两模型首轮修法与行为分析

2026-10-03。**两模型各1次完整首轮均正式得1（23/23），作者核当前补丁符合064公开要求，仍待非作者语义窄核与第二阶段重复采样。** 无新评分/模型调用；原request已returned并ack，活动指针已清。请求结束不等于稳定能力结论或训练资格。

本题公开题面已经给出模块、函数和失败例，公开brief给出两个重构关系检查与pytest入口。本轮观察的是在这些公开线索下的修复，不能据此证明从未知仓库高效发现问题。

## 实际补丁为什么正确

两臂都只修改`Orange/widgets/data/owcreateclass.py`，保留`np.unique`产生唯一值、首次出现位置和原数组逆索引的原行为，没有改测试、评分控制面或硬编码输入。它们修复的是置换方向：设`p = argsort(idx)`，则首次出现顺序的唯一值为`u[p]`；需要构造`q`使`q[p[j]] = j`，再使用`mapping = q[inv]`。于是`u[p][q[inv]] = u[inv]`，恢复原数组，同时保留首次出现顺序。

- Coder以`reverse_map[order_of_appearance] = arange(k)`构造`q`，再索引`inv`。
- Qwen3.6以`argsort(order)`构造相同逆置换，再索引`inv`。

这来自对原baseline与原FrozenPatch源码的数学核对，加上真实公开需求复现和正式23键评分，不是凭reward反推正确。证明范围沿原`np.unique`支持的公开一维输入；没有新增或宣称NaN、混合不可比较对象、多维等任务未要求的语义。两臂原工件均由新grader直接消费且baseline重建通过；外部执行独立核查已完成，当前作者未再执行候选。

## 方法、定位和纠错

事件行均指相应attempt的`trajectory.jsonl`，不是流式chunk次数。时间是从该臂首个实际generation HTTP请求到相关tool_result，包含生成和工具往返，不能当纯搜索或纯工具时长。

| 观察 | Coder：`gpu1003-orange322e9-coder-a1` | Qwen3.6：`gpu1003-orange322e9-qwen36-a1` |
| --- | --- | --- |
| 首次读取相关文件 | 事件10→14，第1工具，0.559秒；随后第2工具读完整公开测试 | 事件11→15，第1工具，1.353秒；事件25→29再定点读函数 |
| 原缺陷复现 | 36→40重构失败；49→53数值重复例和字符串例均失败 | 43→47原表达式与错误的`inv.argsort()`都不能重构 |
| 错误假设 | 62→66第1次Edit仅把`argsort(idx)`赋变量再索引，数学上等价，未修复。75→79仍失败后，错误归因于编辑/导入未生效；88/97两次Read与110新进程复现重复工作 | thinking事件35提出`inv.argsort()`，在43→47实测否定；没有把这条错修写入源码 |
| 正确假设实测 | 136→140，第11工具，34.122秒：逆置换在内存重构成功 | 57→61，第4工具，32.194秒：逆置换实测成功；75→79再核三个公开例 |
| 最终修改与加载 | 149→153第2次Edit；158→162真实模块重构成功，40.388秒 | 93→97唯一一次Edit；111→115真实导入候选，公开例和重构断言通过，41.149秒 |

两臂都能依据反馈纠正推导。Coder有一次无效源码修改和至少三次围绕“未加载新源码”的重复检查，故不能把tool_error=0解释为过程全正确。Qwen的步骤较少，但最终回复和调试注释对置换方向有不够准确的措辞：应理解为从**排序唯一值下标到首次出现下标**的转换，不能把`np.argsort(order)`说成原数组位置的逆映射；代码和实测仍正确。

## 工具、并行与验证

Coder实际4 Read、13 Bash、2 Edit，共19工具；Qwen为3 Read、6 Bash、1 Edit，共10工具，均有对应真实结果，无工具层报错。Coder最初Bash没加brief的Qt前缀但实际导入成功，不能据此声称环境错误；警告为LibreSSL/urllib3兼容提醒，两臂的测试均继续完成。

两臂都逐次请求单工具，没有多工具batch或实际并行。初始源文件/公开测试读取，以及修改后的互不写入检查，存在潜在独立操作；但本次没有并行请求，也没有对执行层并行能力的实测，**模型并行能力不可判断**。不能由单卡服务串行推理或本次未并行，推断模型不会并行。

Coder在171→175检查空输入、单值、重复值和旧公开例；184→188检查原例及数值/字符串重复例；197→201 helper为1passed，210→214整个公开文件23passed/3skipped，223→227又重复两个重构断言。前面多数脚本只打印布尔值，正确性来自读具体True/False，最终223有实际assert。三条skip是未实例化widget基类，非23个正式参考缺项。

Qwen在111→115用实际候选的assert核原例及两个重构例；129→133 helper摘要1passed，147→151全文摘要23passed/3skipped。两个pytest命令接`head`/`tail`且未启用pipefail，故工具成功不能独立证明pytest退出码；正式grader另有完整testRC0/23键原件，评分端不存在这个歧义。Qwen没有额外单列空/单值检查，但实际公开helper包括这些原用例。两个模型最终报告与已见测试一致，不称覆盖全部可能输入。

## 效率、结束和下一步

| 实际指标 | Coder | Qwen3.6 |
| --- | ---: | ---: |
| 累计输入/输出tokens | 420128 / 5832 | 170982 / 7244 |
| CC/generation回合 | 20 | 11 |
| 工具次数 | 19 | 10 |
| solve墙钟（秒） | 70.640 | 55.607 |
| CC总时长/API时长（秒） | 67.030 / 47.473 | 51.796 / 43.210 |
| actor trusted init（秒） | 208.958 | 208.424 |
| grader总时长/测试段（秒） | 215.997 / 4.172 | 220.227 / 4.258 |
| 派发后整个作业（秒） | 535.279 | 524.828 |

输入tokens是每轮prompt累计，包含上下文重复；Qwen输出包含thinking，不能把这些单次数字当等价的纯最终答案长度或稳定速度比较。API时间含服务等待和传输，不等于纯GPU运算。工具call事件无时间，未伪造逐工具时长；队列派发前等待没有完整观察，保持未知，grader报告的queue_wait=0只限评分管理器。整个作业约9分钟主要含两侧环境准备，不能说模型解题用了9分钟。CC costUSD为本地估算，不是自托管实际账单。

两臂均正常completed/end_turn，无预算截断、缺模型、漏评分或已见运行异常。实际宽松设置196608 context、65536单响应、240回合、3小时求解；最大实际prompt26632/19446，尚无满196K负载证明。两模型采样设置不同，固定记录分别保留，不能从一次耗时因果归为模型架构差别。

**当前每模型只有1个完整样本：本轮语义正确率各1/1，首轮完成率各1/1，无截断/无效样本；尚未评估稳定性。** 不新增未经校准的总行为分。作者未发现需修题、改共享consumer或重跑首轮的真实缺陷；请求已收口，继续非作者语义窄核并等待全批第二阶段，同材料/预算下通常补至每模型总3次。仍需GPU，不提交退租就绪。

## 证据与用途限制

- [原两模型总回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/receipts/r2e-orange22-r064-cpu-sysconfig-v1-20261003.json)；SHA `5affdbc6725ea497584f8b60f3089f38b5dfc21d8736378cafa6cdaa919cd633`，所有31项直接引用已核SHA。
- [作者逐工具/模型文本/补丁/时长索引](../../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/orange22_first_probe_author_evidence_v1.json)，含全部249/183事件解析和19/10工具定位。
- coder：[完整轨迹](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v8r1/results/gpu1003-orange322e9-coder-a1/attempt/trajectory.jsonl)、[原FrozenPatch](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v8r1/results/gpu1003-orange322e9-coder-a1/attempt/frozen/frozen_patch.json)、[baseline](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v8r1/results/gpu1003-orange322e9-coder-a1/attempt/frozen/baseline_manifest.json)。
- qwen36：[完整轨迹](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v9/results/gpu1003-orange322e9-qwen36-a1/attempt/trajectory.jsonl)、[原FrozenPatch](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v9/results/gpu1003-orange322e9-qwen36-a1/attempt/frozen/frozen_patch.json)、[baseline](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v9/results/gpu1003-orange322e9-qwen36-a1/attempt/frozen/baseline_manifest.json)。
- [Coder独立执行复核](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/orange322e9_coder_a1_execution_review.md)、[Qwen独立执行复核](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/orange322e9_qwen36_a1_execution_review.md)。

code3 shared_entry路径/SHA记录错配以原queue命令/冻结manifest外部关联纠正；原baseline environment digest为null，仅input/host/rollout外部绑定，原件没有补写。两臂权重来源沿既有revision和只读mount，本轮未重新哈希权重；有限资源样本不证明全程OOM/节流为0。它们是本次诊断的限制，不重跑有效首轮来掩盖。当前用途限题目/环境与基座方法诊断，不授予训练或留出资格。
