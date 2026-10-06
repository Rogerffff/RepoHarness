# Dask7656 双模型首轮：当前目标通过

2026-10-03T22:24:50.179794+08:00。Qwen3.6首臂 `gpu1003-dask7656-qwen36-a1` 的正式1F／48P全部通过，原raw reward1；源码和轨迹经非作者窄核接受当前目标。与先前Coder合并后，两模型各一次首轮及题主分析均已完成，请求回执已核收。没有新的题级修订或CPU复修依赖；不证明稳定能力或训练资格。

Qwen在 `unpack_collections` 和 `to_task_dask` 两处采用公开issue给出的 `f.init or hasattr(expr, f.name)` 条件，跳过未初始化且不存在的init=False字段，保留原类构造及嵌套Delayed求值。两次源码Edit均有行为变化；第三次Edit只添加公开回归测试。三次编辑重放与实际两项FrozenPatch逐字节一致。已存在init=False默认／手设状态仍进入不支持的构造kwargs，属于原有且本题明确未新增的要求；弃用入口仅有静态核查，没有单独运行。

| 观察 | 实际证据与范围 |
| --- | --- |
| 定位与修法 | L15旧函数名检索为空，L29–117定位实际fields和两分支；L131／145修复、L163／177读回。公开题面已给workaround，不称独立发现算法。 |
| 自检 | L195原例返回常量，只证明原异常消失；L213单测过；新增L245回归检查other_field值，L259两项过。没有修前失败对照，模型新测试未检查实际参数原类；私有增强测试补足原类、字段和嵌套求值。 |
| 纠错 | L277使用未安装的--timeout=60，L281明确报参数错误。管道到head让工具is_error=false，不能当成功验证；L291移除参数后L295完整可见51PASS／2XFAIL。 |
| 正式评分 | 恢复受信测试并重打固定patch，投影仅纳入dask/delayed.py。完整log50PASS／2非参考XFAIL；49正式键全部通过。模型新增测试不进入正式分，未发现控制污染。 |
| 最终说明与并行 | 最后说明准确列两处过滤及新增测试；All tests pass仅限单文件并保留2预期XFAIL。19工具均串行，独立读文件可合并，编辑／验证须有序；没有实际多工具请求，不能判断后端并行能力。 |

求解27.802秒，CC本体24.36秒、累计API20.147秒；20个模型响应／19工具（Bash9、Read7、Edit3），累计提示155,653 tokens、输出3,220，最大单次提示12,629。提示计数含重复上下文，API时间不是纯GPU推理，CC别名costUSD不是实际账单。正常completed，未预算截断。评分384.38秒，其中trusted setup365.008574秒；安装3.78秒、测试命令1.554秒、含运输测试分段5.992406秒分别保留，不能把准备计为模型求解时间。

[非作者报告](../../reviews/non_author_7656_qwen36_a1_candidate_review_20261003.md)在封存时保留公开说明范围待对齐，随后GPU已[明确现行口径](../../../../../../../../../runs/category2_repair_20260929/swe_dask/model_analysis_20261003/dask7656_qwen36_a1_v1/public_hint_scope_GPU_clarification_v1.json)：`unchanged`只保持prepared spec.prompt原字节，不追加内部题包或旧通用public_hints。两臂实际prompt同SHA／3199B，原source题面完整；CPU控制桩曾收到hints与GPU真实输入范围分开。原probe把题面／hints并称的basis措辞由当前入口澄清，原请求／原裁决不回写。不能把未交付的Do NOT modify tests当模型违令，也未发现具体必要开发说明缺失；不要求重跑或暂停其它Dask。

148原件13,107,604B及31回执引用已逐SHA／尺寸核收，三次Edit重放吻合。actor118f47／grader50bca、UID54321／54322、当前材料d7a8、single-shell摘要8833、setup900／whole3600实际绑定保留。双层清理、gateway drain0和PID1成功终态核过。原resource_facts=null不补造，32资源采样间隙未知、peak memory1968.199MB；未重验GPU权重内存或正式训练typed actor。

[固定分析JSON](model_probe_qwen36_a1_analysis_20261003.json)保存完整身份与引用；[Coder点时分析](model_probe_coder_a1_analysis_20261003.md)及原四行CPU控制结果保留。两模型各一次通过只支持本题当前范围，code7／code8差异和单样本限制不消除；后续重复依全局覆盖规则，当前不追加模型样本或重评。
