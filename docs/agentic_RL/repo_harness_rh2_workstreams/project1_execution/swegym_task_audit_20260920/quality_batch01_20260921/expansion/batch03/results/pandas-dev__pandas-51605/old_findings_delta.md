# 51605 旧结论增量

初稿SHA256=`9368249d288851e632e6bf46726c2180f424edea257a331c6e58c2110a40bef6`。root在`2026-09-20T21:52:32.688367Z`正式封存并放行本题历史后，才读取唯一旧记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_modin_pandas/records/pandas-dev__pandas-51605.json`。未读旧聚合、其它题结论、reviewer或旧记录所指raw hints/stage1/optdeps/collide_detail。初稿原字节不改。

| 旧主张（行） | 判断 | 新决定性证据及适用范围 |
| --- | --- | --- |
| 材料对应、空列表初态异常、仅业务源/test分离（23-27） | 确认 | 本题source第154行/host grading核对；原baseline N4720-4829是同一TypeError；G仅multi.py投影；官方恢复仅test_isin.py。 |
| 返回ndarray还是Index不清楚（18） | 公开材料已消解 | 公开Index.isin:6182-6201明确np.ndarray[bool]及长度；MultiIndex复用文档，已有test_isin检查类型/dtype。题面用词不精准不意味着这个隐藏要求无依据。 |
| level不为None行为未说明/gold只改None（19,33） | 限缩 | 已有_get_level_number、level旧测试及algos.isin覆盖合同；gold保持原level分支，未发现该分支因本次修改受破坏。空值+非法level不是当前P2P，应按公开test_base889-903建议保护，不能单凭gold只改None判不完整。 |
| F2P与公开需求一致，未绑定gold写法（29-30） | 确认但补覆盖范围 | helper严格检查ndarray/bool/shape/value，有接口依据；新增用2行而公开原例3行，不能说逐字测了原例。合理iterator归一化/有层数空MI路线未遭实现级约束。 |
| 仅测空list，gold对无len生成器报错（31,45-49） | 确认并强化 | gold新增len在from_tuples559-563的iterator→list之前；因此不只是empty iterator未修，还会破坏非空iterator原本匹配的路径。公开zip构造测试与lib.is_list_like支持，这不是要求gold之外的新API。反例未执行。 |
| gold完整性pass，只把len记成局限（33） | 推翻宽泛pass | 既有非空iterator输入发生静态可证的协议回归；另外空str/bytes原非list-like验证被早返回绕过。当前13P2P/F2P不含这些输入。依赖完整/无无关文件改动仍确认。 |
| 13参考均唯一命中（37） | 本次条件确认 | N/G各收集13、摘要13个完整节点、parser13键，与1F2P+12P2P集合相等；无missing/skip，无碰撞。N普通pytest rc1/reward0，G rc0/reward1分别核实。旧stage1原件未再读。 |
| hints_text给first-bad commit/PR且不可见或强泄漏（25,34） | 旧raw内容未核实；不直接套当前输入 | 旧记录披露了其主张；当前public_bundle只有issue和通用public_hints，不含那段git show。未读取原raw hints、真实镜像历史或CLI消息，不能断言本次可见/不可见或已泄漏；过去回归定位信息也不能未经边界定义就等同gold答案。 |
| 不同题不同PR/模块（28） | 未核实 | 当前未检索其它题，不能以旧汇总代替具体关系证据。 |
| 829.6秒安装/5秒测试、99.4%无谓重编（35,40-44） | 耗时方向确认，旧数值与“全部/无谓”限缩 | 当前本题原baseline noop安装693.328秒/测试5.790秒，gold719.751/4.552；确有editable wheel build。旧stage1数值未复读，不能当本次成本。纯Python业务修改不必强制actor每次重编；具体全部扩展重编/可安全省略哪个步骤需缓存/产物生效证据。`--no-deps`建议没有证明可跳过包自身构建，不能照搬为已验证优化。 |
| Series/DataFrame.isin是本MultiIndex.isin的下游（55-56） | 推翻直接调用路径主张 | 历史阅读后定点检查本题公开`series.py:5324-5327`对自身_values调algorithms.isin；`frame.py:11171-11204`按dict/Series/DataFrame/普通values走递归isin、eq/reindex或algorithms.isin，并非统一调Index.isin。初稿已找到generic.py4582-4615的axis.isin真实调用者；不因名称相同扩大无关测试。 |
| ready_for_probe，唯一实质问题是成本（58） | 不沿用 | 原13节点成功仅说明当前评分工作；gold iterator回归与非法类型shortcut尚需定点验证，正式actor运行仍未验。当前为needs_review/static_review，仅development_diagnostic。 |
| 20分钟成本（59） | 不继承 | 本轮token/费用/项目CPU耗时未观测，costs全null；历史运行时间在facts中单列。 |

新增独立事实：F2P只用2行索引，固定2False的错误空list分支可能通过现有13项却违反原公开3行例；保留为未执行覆盖例，不为凑候选强制第二份补丁。空str/bytes验证绕过也不在旧记录；这两项不被旧“生成器缺覆盖”概括吞并。

独立初判不改变：优先做base/gold/iterator兼容合理路线的窄CPU行为对照（公开3行、空与非空iterator、非法空str），分别记录业务行为和原评分；尚未执行或准备候选，不写成已复现回归/已成功错分。正式actor开发验证另作模型开发门槛，固定grader诊断无需先通过模型链。所有当前私有审查产物不得给solver。

历史放行后额外实际阅读仅本题公开`pandas/core/series.py`的isin实现（5251-5327中接口及尾部）、`pandas/core/frame.py`的isin接口和分派实现（11099-11204中所列片段），用于核对旧caller主张；它们未加入封存初稿范围。
