# NumPy d805：两模型首轮结果与轨迹分析

2026-10-03。题主核已有完整原件，复用执行独立核查，另完成候选语义非作者窄核。本轮只分析已完成样本，没有模型采样、CPU评分重跑、候选执行或材料改动。

## 当前结论与处置

078／079修订材料的两模型首轮质量诊断已收口。两次均正常完成，原FrozenPatch直接评分均为 **raw 0，228／229键通过**；唯一失败是 `TestMaskedArray.test_str_repr` 第458行的公开大数组实例。不是预算截断、环境失败或缺评分。

两份零分对应不同问题。Coder仍漏省略号，把整数显示成字符串，并沿用固定100项裁剪；Qwen3.6已修好默认实例的首尾、遮罩和省略提示，但遗漏公开Expected及当时NumPy摘要格式中的逗号。原分保持，不能把Qwen记录成完全没修摘要，也不能因差一个逗号把它升级成完整正确解。

没有新题级阻断；本轮无需修改题面、隐藏测试或CPU配方，也无需重复矩阵。**值得小批校准，但只是建议：**在已就绪题两模型首轮覆盖之后，若共同题组仍需要“已见错误仍宣称完成”的样本，可在同材料、同模型及各自原采样／预算下，每模型最多额外一次，回答下面两个具体问题。本轮不提交追加请求，NumPy也不自动挤入巡检当前四题校准预案。

- Qwen的格式漏验是否会重复出现，还是下一条独立轨迹能主动把公开Expected变成断言并得到正确结果？
- Coder的字符串化／遮罩覆盖省略号与无mask诊断盲点是否重复出现，还是能根据失败输出更换机制？

两条新样本也只能提供校准案例，不能估计整批无偏成功率。若其它已有题组已回答相同问题，NumPy无需重复。校准价值是解释行为和失败分型，不是追求把零分重试成一分。旧“每模型累计三次”和自动退租安排已经撤销；后续资源操作服从用户新指示。

## 身份、执行证据和统计分母

原请求 `r2e-numpy-d805-078079-cpu-v1-20261003`（SHA `71591ff29d7b…`）仍是每模型一次。固定base为 `25e3ebf4def51b290f544fb0bc7f6d8eb5c04b85`，隐藏修订078、题面079、期望229键。两臂实际actor／grader镜像均为 `sha256:0121ac120aca48fc63320efc126ebd903214d8742f3639b6797d95fd366327e4`；CPU验收镜像 `e5c5233c…`另列，不冒充同一image ID。实际公开prompt相同，SHA `fe7277aaeff919ddbfa883ae9a5e7876f1f3b41db52bbdf2bbaf3b4fc90d0e41`，首生成请求含正式题面及中性开发说明。

| 原样本 | Coder | Qwen3.6 |
| --- | --- | --- |
| job ID | `gpu1003-numpyd805-coder-a1` | `gpu1003-numpyd805-qwen36-a1` |
| 模型 | Qwen3-Coder-30B-A3B-Instruct | Qwen3.6-35B-A3B |
| 正常完成／实际尝试 | 1／1 | 1／1 |
| 有效正式评分／实际尝试 | 1／1 | 1／1 |
| 原预算成功／实际尝试 | 0／1 | 0／1 |
| 完整样本满足当前任务要求 | 0／1 | 0／1 |
| 正式测试键 | 228 PASSED、1 FAILED／229 | 228 PASSED、1 FAILED／229 |
| 结束 | CC success／end_turn／completed，dispatcher rc0 | 同左 |
| 清理 | actor、manager、gateway drain均完成 | 同左 |

总分母2次：正常完成2／2、有效评分2／2、原成功0／2、截断0／2、基础设施失败0／2、无有效评分0／2。两臂均在正常结束后评分；solver没有收到这次正式失败，不能说它们“忽略正式评分”。可评估的是求解期间已观察到的自测输出及后续决策。

两份完整执行核查已逐键重算，未缺项、多项或skip；baseline完整1447对象重建一致，原FrozenPatch绑定及直评可追溯，安装明确skipped。完整封包231文件／210,357,682字节已由执行侧独立读回，全部SHA一致。题主复用该核查，不重哈大包或重复评分。

## 根因、修法与评分依据

**Coder。** 原 `MaskedArray.__str__` 为避免大数组object转换，先裁前后各50项，既不遵循公开printing options，也未标示丢失的中间值。Coder知道裁剪漏省略号，但最终把字符串 `'...'` 直接与整数数组拼接，再给该位置的mask设 `True`。拼接先把数值字符化；后续object转换无法恢复数值类型，新槽位又被遮罩显示 `--` 覆盖。正式失败输出含 `'0'`、`'1950'` 等带引号的整数，没有数据省略号，仍保留约100个槽位。它没有解决公开默认实例，固定裁剪也未修好全量显示条件。

**Qwen3.6。** 读取 `_summaryThreshold` 和 `_summaryEdgeItems`，先按选项取首尾，再object转换／遮罩替换，最后插入 `__repr__` 返回 `...` 的 `_SummaryEllipsis`。此顺序避免字符化和遮罩覆盖。正式默认实例的首尾、mask、fill value及其它排版都正确，actual为142字符，expected为143字符：

```text
actual data:   [0 -- -- ... 1997 1998 1999]
expected data: [0 -- -- ..., 1997 1998 1999]
```

去掉expected的这个逗号后，两份完整repr完全相同。缺逗号仍有公开依据：实际交付的同一个Expected示例明确含 `..., `；base `numpy/core/arrayprint.py:252–254` 的摘要标记也是 `summary_insert = "..., "`，489–490行交给formatter。候选只有7个object元素，未达默认阈值1000，sentinel成为普通元素，绕开原生摘要标记路径。因此是格式兼容失败，不是隐藏测试发明私有算法而误拒。不能由此扩张成所有情形下任意空白都必须固定。

**229键的限制。** 两臂小数组str／repr断言已过，但同一测试函数在458行就失败，468行及之后的尾部遮罩、500项全量、threshold／edgeitems断言未执行。228／229是测试键分母，不是内部断言通过数。非作者源码核查支持Qwen若干后续全量分支，支持大edgeitems例中的两次摘要行为；这只是静态推导。不能声明“修一个逗号就能全过”。Qwen缺少公开 `_leading_trailing` 的 `len(a) > 2*edgeitems` 保留条件，也不足以证明全部一维参数正确；二维、dtype／subclass全面兼容及性能不在本次已验范围。

独立语义报告见[两份候选窄核](reviews/gpu_pair_semantic_review_20261003.md)。reviewer为非候选作者、非执行者，已知此前私有修订背景，不是fresh solver；本次完整解码两份core.py，读取原baseline、公开测试／prompt和完整失败段，未运行候选。

## 定位、纠错和已见错误后的行为

以下 **G** 为实际生成请求序号，**T** 为tool_use序号，**E** 为原trajectory.jsonl从1开始的记录序号；E含流式片段，不能当回合。相对秒数从各臂首生成请求开始：工具行用结果返回时刻，诊断行用该生成请求开始时刻，后者不是推理完成时间。完整tool ID、输入、输出和时间戳在各臂[轨迹索引](../../../../../../../runs/category2_repair_20260929/r2e_numpy/gpu_analysis_20261003/metrics_and_anchors_v1.json)。

| 定位节点 | Coder | Qwen3.6 |
| --- | --- | --- |
| 复现公开错误 | T1／G1／E10，直接打印2000项masked例 | T2／G2／E29，先T1核解释器及print options |
| 找到相关文件 | T2／G2／E23→27，2.162秒 | T3／G3／E47→51，3.412秒 |
| 找到相关符号并读取 | 先T3–5大段读；T6 grep、T7–8读repr／str，E75→105，20.539秒 | T4 grep、T5精确读，E61→79，4.700秒 |
| 首次正确根因假设 | G9／E110，20.551秒：硬裁剪漏省略号 | G6／E85，4.711秒：repr委托str，硬裁剪漏省略号 |
| 首次修改返回 | T11／G11／E140→144，34.595秒 | T25／G25／E379→383，32.828秒；修改前核arrayprint与公开测试 |

**Coder主要纠错过程。** T12（E153→157）第一次修改后的公开例已显示字符化且无数据省略号，G13（E162）明确承认修法未生效，并识别字符串转换问题。此后仍多次回到相近拼接方案。T38（E483→487，127.578秒）再次得到同类失败，G39（E492）承认没有省略号。T33、40、50分别checkout回退，最终T53（E674→678，195.657秒）仍提交最初这类机制。

T46加debug后，T47／48／49以及最终T54的示例都没有真正mask，走原有 `mask=False` 分支，无法检查修改后的分支。T47（E596→600）无debug，G48（E605）误判为不了解维度／条件；T54（E687→691）20项无mask不裁剪，G55（E696）又怀疑条件或NumPy环境。结果里的 `mask=False` 足以解释这些诊断为什么没测到目标分支。最终G59／E748声称大数组显示已修复，新增fix_description.md同样宣称成功，与此前观察及正式原输出矛盾。这是看见自测无效后继续修改、最终错误收口；不是执行层强制中断。

**Qwen主要纠错过程。** T26（E393→397）首版仍无省略号；加标记后T29仍不显示。T30检查长度6，G31／E463正确发现先裁剪后条件 `n > 2*edgeitems` 永远不成立并移除错误guard。T32显示带引号的 `'-- --'`，T34显示带引号的 `'...'`；G39／E579从原生formatter解释字符串会被当元素引用，随后测试Ellipsis和自定义对象。T43（E639→643，65.159秒）确认需要 `__repr__`；T44／47完成sentinel。

T48（E717→721，73.578秒；tool ID `toolu_745c648cb11c993e`）公开原例已只差逗号，G49／E727却把它描述成包含逗号的Expected并称匹配。T54（E825→829，90.954秒；`toolu_358e4b02c8d04fdd`）再次打印同样缺逗号的结果，G55／E835重复称完全匹配。另一方面G53／E799面对7项未摘要，先怀疑edgeitems，再重新读公开“未过threshold应全量”要求，正确撤回错误假设。它有依证据纠错能力，但没有把最后的格式差异转为字面比较。

## 工具、验证和并行机会

Coder有58次工具调用、3次工具错误：T25错pytest node，缺少 `TestMaskedArray` 类路径，exit4且没有收集测试；T31、35是Edit旧字符串／文件版本不匹配。后续修正节点并运行公开测试，属于已恢复工具错误，不是基础设施失败。第一次三次大段Read返回273,095 UTF-8字节，覆盖大量无关源码；所有Read共287,198字节。全仓find／grep及三次回退增加了反复上下文；精确符号搜索是在这三次Read以后进行。Qwen55次工具调用无error flag，先grep后定位读取，总Read31,128字节；其间语义失败的打印仍是失败证据，不能因工具rc0记为正确。

| 验证层面 | Coder | Qwen3.6 |
| --- | --- | --- |
| 公开原例 | 复现充分；改后多次仍坏，最终没有精确Expected断言 | 多次复现、纠错；两次缺逗号均被误称匹配，无精确断言 |
| 公开回归 | 输出9／6／9／1 passed；最后同名公开str_repr仅小数组 | 6 passed／234 deselected，core229 passed，core＋subclassing＋extras301 passed |
| 边界验证 | 降_print_width的小例数次无mask，绕开修改分支 | T52六个edge打印仅一例有mask且n100，未覆盖原硬裁100的失败；其余5例无mask |
| 结果解读 | 公开小例通过被用于宣称原问题修好 | 公开测试全过被用于声称格式一致 |
| 正式评分 | 原候选直接评分，真实大数组失败 | 原候选直接评分，真实逗号失败 |

Qwen T49的四个打印中有正确带mask大例，但只观察输出，没有对Expected建立断言。T51、55的pytest经 `2>&1 | tail -20`，工具pipeline exit0本身不证明pytest退出码；归档输出确实显示公开测试通过，仍不能覆盖另一路正式评分。公开core的229与正式R2E的229只是数量相同，内容和测试键不同。

两臂每个生成请求最多一个tool_use，实际未观察到多工具并行。可识别的独立机会包括找到位置后分别读取ma实现、arrayprint及公开测试，以及固定候选后独立运行不同公开回归组。修改同一core及依赖修改的复现不能算独立机会。本批没有执行层支持重叠调用的同臂实测，不能判断模型并行能力，更不能从串行轨迹推断“不会并行”；索引只证明实际串行及工具结果完整配对。此项记 **不可判断**，不为补字段启动新实验。

## Token、回合及纯求解效率

数据来自实际CC结果、gateway／adapter逐请求记录及attempt计时；量纲分别保留。累计input含每次重送上下文，不是独立读取量；Read字节不是token。CC num_turns和生成请求在本臂数值相同但来自不同记录，114／131个assistant流式事件不是回合。

| 指标 | Coder | Qwen3.6 |
| --- | ---: | ---: |
| 累计input tokens | 5,913,900 | 1,120,980 |
| 累计output tokens | 14,436 | 13,914 |
| cache read／creation tokens | 0／0 | 0／0 |
| 生成请求／CC num_turns | 59／59 | 56／56 |
| 独立count_tokens请求 | 5 | 0 |
| 工具总数 | 58 | 55 |
| Bash／Read／Edit／Write | 39／10／8／1 | 35／13／7／0 |
| 工具error flag | 3 | 0 |
| solve入口墙钟（秒） | **233.310** | **102.466** |
| CC自身墙钟（秒） | 229.405 | 97.868 |
| CC累计API时长（秒） | 217.596 | 88.951 |
| gateway生成HTTP累计（秒） | 216.002 | 87.485 |
| 整个job墙钟（秒） | 329.458 | 328.529 |
| 正式grading总时长（秒） | 37.830 | 57.846 |
| 正式test段时长（秒） | 1.624 | 1.900 |
| 最大单请求prompt tokens | 119,710 | 39,421 |
| 最大单响应output tokens | 1,022 | 1,103 |

本报告的“纯求解”是solve入口包围实际CC求解的墙钟，仍包含其内部工具／测试等待；排除了actor准备、正式grading和排队。API／HTTP含模型prefill／decode及传输，不称纯GPU计算。整个job近乎同长不表示求解同样高效。Coder此例累计input约为Qwen的5.28倍、Read字节9.23倍、solve墙钟2.28倍，输出token和回合却相近，说明大段读取／重复上下文及反复修法是实际成本来源。两模型tokenizer与采样设置不同，不能仅以这些倍率推断普遍效率排名或因果归因。

准备阶段单列（秒）：Coder image／network-container／git-sanitize／trusted-init／baseline-census／quiescence为0.019／1.185／16.053／19.629／0.456／0.973；Qwen为0.026／24.472／16.825／30.913／0.480／0.967。进入job之前的全局排队时间未知；report的grader queue_wait=0只表示评分阶段，不是总排队0。尚未完整拆出的工具独占时间、其它入口开销保持未知，不用总时间减累计API补成“纯工具耗时”。资源归档两臂都观察到CPU节流，稀疏样本中的零OOM不等于全程零OOM，也不能据此把两臂速度差全部归到模型。CC本地美元估计不是自托管账单，不列为租机成本。

## 生效预算、可比性和用途

两臂都是 `probe-wide-v1`：context196608、每响应65536、CC240回合、solve10800秒、网关1024生成请求、HTTP1800秒、adapter idle TTL14400秒；正式whole／setup／apply／test为3600／300／120／1800秒。全部实际请求max_tokens65536，无length截断、compaction、400或stream error；最终end_turn正常。模型有充足剩余预算，但不能据此认为增加预算一定改善行为。

模型来源复用已核部署关联，BF16／TP1；Coder revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`，温度0.7／top_p0.8／top_k20／repetition1.05；Qwen revision `995ad96eacd98c81ed38be0c5b274b04031597b0`，温度1／top_p0.95／top_k20、无repetition覆盖。采样结论是冻结code3＋实际入站请求＋Session defaults推导，未捕获adapter→SGLang原HTTP或最终渲染input_ids。Coder实际thinking块0；Qwen55块在后继请求保留。没有重哈全部权重。两模型各一次且参数不同，只能作此题案例观察，不能声称稳定能力相同、稳定成功率或训练收益已定。

现有二元评分把明显机制错误与接近正确但格式失败都压成0，轨迹分析保留了这一区别。可供后续数据／训练设计评估的实际现象是：两者能定位裁剪根因，但失败分别落在修法／分支诊断和精确输出验证；Coder和Qwen均存在成功声明超出自测支持的情况。这是潜在训练问题线索，不是已证明能带来RL增益，不能单靠本题宣布R2E有效或饱和。

执行来源仍有边界：code3原attempt中shared_entry路径与SHA错配，code_snapshot_id=null；queue argv及固定manifest已在独立执行核查中外部关联到正确入口。baseline.environment_package_digest=null，prepared／host环境身份另核；外部关联不等于正式lineage字段已闭环。Coder excluded_pathset_changed=true保留，Qwen为false，不称所有排除区始终未变。X1同仓答案暴露／留出划分和E3共享控制保护延后仍在。因此本包只完成当前修订版质量诊断，不授训练或holdout资格。当前无CPU修复依赖，无缺失首轮GPU样本，不自行处理云资源。

## 原件导航

- [总回执](../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/receipts/r2e-numpy-d805-078079-cpu-v1-20261003.json)：两模型、原分及完整结束，SHA `8ffdc32e6456…`。返回通知已恢复送达，题主ack已落账；ack只确认核收，语义结论以本报告为准。
- [Coder完整执行核查](../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/numpyd805_coder_a1_execution_review.md)／[Qwen完整执行核查](../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/numpyd805_qwen36_a1_execution_review.md)。
- [Coder原轨迹](../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v8r1/results/gpu1003-numpyd805-coder-a1/attempt/trajectory.jsonl)／[全文索引](../../../../../../../runs/category2_repair_20260929/r2e_numpy/gpu_analysis_20261003/coder_trajectory_index.json)；[Qwen原轨迹](../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v9/results/gpu1003-numpyd805-qwen36-a1/attempt/trajectory.jsonl)／[全文索引](../../../../../../../runs/category2_repair_20260929/r2e_numpy/gpu_analysis_20261003/qwen36_trajectory_index.json)。
- [Coder原FrozenPatch](../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v8r1/results/gpu1003-numpyd805-coder-a1/attempt/frozen/frozen_patch.json)／[完整失败日志](../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v8r1/results/gpu1003-numpyd805-coder-a1/grading/eval_logs/evallog_gpu1003-numpyd805-coder-_f2d62716.eval.log)。
- [Qwen原FrozenPatch](../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v9/results/gpu1003-numpyd805-qwen36-a1/attempt/frozen/frozen_patch.json)／[完整失败日志](../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v9/results/gpu1003-numpyd805-qwen36-a1/grading/eval_logs/evallog_gpu1003-numpyd805-qwen36_2ef938d9.eval.log)。
- [独立语义窄核](reviews/gpu_pair_semantic_review_20261003.md)、[可机读分析／完整SHA索引](gpu_pair_analysis_20261003.json)、[当前清单](result_manifest.json)、[CPU验收原件索引](cpu_acceptance_v1.json)。
- [现行覆盖优先规则](../../overnight_watch_20261003.md)取代旧自动重复／退租安排；暂停／恢复检查点和分析前入口快照仅保留历史。
