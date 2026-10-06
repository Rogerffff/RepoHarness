# Orange22两臂首轮候选非作者语义及行为窄核

2026-10-03。**两个最终补丁均修复公开r064要求的根因并保留既有行为；本题两臂首轮语义窄核完成，没有需要修题或重跑首轮的新阻断。** 原正式分数各reward=1、23/23，与本次独立语义结论分列。每模型只有1个完整样本，不评价稳定性或普遍模型能力；本报告不授予训练／留出资格，不决定GPU退租。

只读本地已回收baseline、原FrozenPatch及完整轨迹；复用独立执行完整性审查，没有运行候选、NumPy、模型、CPU／Docker或新测试，也没有改已有执行／50／brief核查报告、候选或总账。

## 身份与修复依据

[原总回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/receipts/r2e-orange22-r064-cpu-sysconfig-v1-20261003.json)SHA`5affdbc6725ea497584f8b60f3089f38b5dfc21d8736378cafa6cdaa919cd633`，请求`r2e-orange22-r064-cpu-sysconfig-v1-20261003`；两attempt分别为`gpu1003-orange322e9-coder-a1`和`gpu1003-orange322e9-qwen36-a1`，同公开要求、base commit `96fda39b…`与实际actor／grader镜像`c91075ae…`、配方`e2e17bf1…`。完整执行／输入交付、预算和评分运输复用[C执行复核](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/orange322e9_coder_a1_execution_review.json)、[Q执行复核](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/orange322e9_qwen36_a1_execution_review.json)，不重做运输全审。

本轮实际消费的attempt、trajectory、FrozenPatch、baseline manifest、result和上述执行复核SHA全部与总回执相符；从实际baseline.tar定点读出的源码SHA`949c1561…`与manifest一致。两臂都只改`Orange/widgets/data/owcreateclass.py`；按轨迹Edit的逐字替换在内存重建后，字节精确等于原frozen源码，目标函数外AST不变。未发现测试修改、评分控制修改、输入硬编码或绕过。

| 候选 | 原FrozenPatch完整文件SHA | 实际源码SHA | 最终修法 |
| --- | --- | --- | --- |
| Coder | `fb6e997504637658362365fa548e3a6a9721fffbb40f96f4541669d76c0f34bd` | `9b73231252ba3f9a06675930204fdc6dcd58e7e04e09011714e7cb21ea2312bd` | scatter赋值构造逆置换，再索引`inv`。 |
| Qwen3.6 | `6c017d50e415bf36b936168590fb69b14a11afd05695622557eb6620655fa6e3` | `f9e0711c0ba784fafb5032229492c6a755812488250bbf4210e0595e1cd05b65` | 对`order`再次argsort构造逆置换，再索引`inv`。 |

[Coder原FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v8r1/results/gpu1003-orange322e9-coder-a1/attempt/frozen/frozen_patch.json)；[Qwen原FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v9/results/gpu1003-orange322e9-qwen36-a1/attempt/frozen/frozen_patch.json)。语义结论不是由总分反推：`np.unique`给排序唯一值`u`、首次位置`idx`和满足`u[inv]=a`的索引。设`p=argsort(idx)`，首次出现顺序为`U=u[p]`；需要`q[p[j]]=j`的逆置换，再返回`q[inv]`，从而`U[q[inv]]=u[p[q[inv]]]=u[inv]`。原式把`p`直接用于`inv`，方向错误。Coder的`q[p]=arange(k)`和Qwen的`argsort(p)`建立同一`q`；空输入／单值仍有效，scatter中所有k项都由置换赋值，不存在遗留未初始化索引。

两者保留unique值及首次出现顺序、整数映射与原长度、重复值和字符串的公开合同，也保留调用端对names／map_values的处理。证明沿既有`np.unique`支持的公开一维输入；不新增NaN相等语义、混合不可比较对象或多维合同。

## 七维观察及作者结论窄核

以下`C`、`Q`事件行分别引用[Coder完整JSONL](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v8r1/results/gpu1003-orange322e9-coder-a1/attempt/trajectory.jsonl)与[Qwen完整JSONL](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v9/results/gpu1003-orange322e9-qwen36-a1/attempt/trajectory.jsonl)，每个工具的ID、调用行／返回行及内容SHA在同名JSON中完整保存。

| 维度 | Coder实际观察 | Qwen3.6实际观察 |
| --- | --- | --- |
| 解题方法与修法 | C62→66首Edit只将原错误表达式赋予`inverse_argsort`，语义等价；C75→79仍失败。C132承认逻辑错误，136→140逆置换实测正确，149→153第二Edit才真正修复。 | Q21／35 thinking猜`inv.argsort()`，43→47实际重构失败；Q53修正过程中仍有错算。57→61正确逆置换实测，75→79三个原型例通过，93→97唯一Edit后111→115核真实候选。 |
| 定位能力 | C10→14首工具读对模块，23→27读公开测试；第11工具才首次得到正确逆置换结果。 | Q11→15首工具读对模块，25→29再定点读函数；第4工具得到正确逆置换结果。 |
| 工具使用 | 4 Read／13 Bash／2 Edit共19项，真实结果全部配对。C84／106／119把等价修改后失败误归因于编辑／导入未生效，88／97读取及110复现增加了无效工作；没有实际导入错误。 | 3 Read／6 Bash／1 Edit共10项，结果全部配对。错误假设先试再否定，未写入最终源码；129与147的pytest接head／tail且没有pipefail，成功工具状态不独立证明pytestRC。 |
| 并行调用 | 每次一个工具、最多1个未返回ID，无batch或实际重叠。初始模块／公开测试读取有潜在独立机会，但执行层支持未知。 | 每次一个工具、最多1个未返回ID，无batch或实际重叠；是否能并行不可判断。 |
| 验证质量 | C36→40原例失败、49→53两个重构例失败；修后171→175核空／单值／重复旧例，184→188核原例及数值／字符串；197→201 helper1passed，210→214全文件23passed／3skipped，223→227重构assert通过。 | Q43→47复现错误，75→79只是内存原型；Edit后111→115才是真实模块的原例及两个重构assert。129→133 helper1passed，147→151完整摘要23passed／3skipped，165→169读最终源码；另有正式grader RC0／23键。 |
| 完成效率 | 20回合、19工具、solve70.640s；首等价Edit、重复Read／导入复现和末次重复检查增加工作。 | 11回合、10工具、solve55.607s；步骤较少，但thinking演算不是全程正确，也不能把单次差异当普遍更快。 |
| 结束与稳定性 | C249为success/completed，无预算截断；最终工件正确，正式23/23，只有1个样本。 | Q183为success/completed，无预算截断；代码正确，Q179最终解释方向不准，只有1个样本。 |

公开题面已经给模块、函数、失败例，brief给测试与重构入口。因此首个Read读对位置不能证明未知仓库定位效率。未观察到并行请求，也未验证执行层并行支持，不能判模型不会并行。

两臂都能利用实测反馈纠错，但需要保留过程限制。Coder不是第一次Edit就修好；工具层错误数0不代表逻辑操作全正确。Qwen的Q21／35／53有多次具体错算／自相矛盾，例如把`inv.argsort()`算成期望值，真实Q47输出否定该结论；不能把它概括成一次性正确推导。最终回复还把置换方向说反：`p[j]`是首次出现顺序第j项在排序唯一值u中的下标，`q`才把排序唯一值下标转换为首次出现下标。正确补丁和Q115实测不受该文字错误影响。

Coder早期脚本多只打印布尔值；本次结论读了具体False／True，最后C227有实际assert。Qwen两条pytest管道未单独保留pytest退出码，但完整passed摘要和复用的正式grader test_rc=0支持本轮通过；不从`is_error=false`单独给成功结论。urllib3／LibreSSL warning出现，实际导入与测试继续完成，没有环境失败。三项skip不属于23个正式参考缺项。

已窄核[作者七维分析](../tasks/22e98f8f/probe_analysis_20261003.md)和[作者抽取索引](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/orange22_first_probe_author_evidence_v1.json)：修法、Coder等价Edit／误归因、Qwen先否定错假设、最终文字限制、工具／回合数、计时边界及单样本限制都与原件一致，无必须改的作者结论。上段对Qwen反复错算的描述补充了推理过程的具体范围，不改变最终代码正确结论。作者JSON的`independent_semantic_review_complete=false`是生成时状态，本报告独立核查完成；不回写其历史状态。

## 时间和用量不能混作模型能力

| 指标 | Coder | Qwen3.6 |
| --- | ---: | ---: |
| 累计input／output tokens | 420128／5832 | 170982／7244 |
| generation／CC回合 | 20 | 11 |
| 工具数 | 19 | 10 |
| solve墙钟秒 | 70.640 | 55.607 |
| CC总时长／API秒 | 67.030／47.473 | 51.796／43.210 |
| actor trusted init秒 | 208.958 | 208.424 |
| grader总时长／测试段秒 | 215.997／4.172 | 220.227／4.258 |
| 派发后作业墙钟秒 | 535.279035 | 524.827778 |
| 首Read结果延迟秒 | 0.558835（C14） | 1.353404（Q15） |
| 首正确逆置换原型结果延迟秒 | 34.121835（C140） | 32.194404（Q61） |
| 首真实候选正确结果延迟秒 | 40.387835（C162） | 41.149404（Q115） |

三种“结果延迟”独立重算自每臂首个实际generation HTTP请求至相关tool_result，包含生成和工具往返，不是纯定位／工具时长，也不是首次完全正确内部推理的时间。调用事件无timestamp，不伪造逐工具起止。作业墙钟由原queue start／end重算，包含两侧环境与评分；不能说模型解题用了9分钟。派发前队列等待未知，grader queue_wait=0只限评分管理器；API时间含等待／传输，不等于纯GPU计算。

input tokens累计多轮prompt重复；Qwen output含thinking，Coder未暴露thinking，两臂采样设置不同，不能把一次token／时长差因果归为模型优劣。CC cost是别名估算，非自托管账单。196608 context／65536单响应／240回合／10800s为生效技术预算，实际最大prompt26632／19446，不能宣称已证明满196K负载。

## 当前结论与后续边界

两臂在本题固定公开要求和预算下各取得一个语义正确、正常完成且正式得1的样本，原首轮无缺模型／截断／漏评分。没有新证据要求修题、改共享consumer或重跑有效首轮；稳定性仍需按全批第二阶段同材料／预算重复采样，不新增总行为分或据首轮给普遍能力结论。

既有执行审查保留的限制继续有效：权重沿既有revision／只读mount来源，本轮未全量重哈；baseline environment digest为null只在input／host／rollout层外部关联；code3 shared_entry路径／SHA错配由冻结manifest外部关联；有限资源采样不证明全时段，配置／代码派生采样不冒作出站SGLang POST抓包。原件不改，不用重跑掩盖记录限制。

当前用途限题级／环境和基座方法诊断，不授予训练或留出资格，不将语义首轮完成等同资源可退租。后续重复样本单独接续；本轮止于两份真实候选及关键七维新结论的非作者窄核完成。
