# 6283：原 Qwen 候选的 v2 补评分与语义结论

2026-10-03。**原候选修复了普通 RootModel 相等问题，但破坏了可信构造的 PrivateAttr 默认值行为，因此没有完成正确修复。** 原完整 FrozenPatch 已在 GPU 宿主的 code_v8、v2 正式材料及公开 wheel 权限修复镜像下实际补评分：安装RC0，2个F2P全部通过，39个P2P中38个通过，唯一新增P2P失败，原始奖励0。此次没有新模型样本。原尝试的安装RC1、奖励1及全部原件保留；跨材料诊断单列，不能写成同条件重复成功率。

## 原件核收与实际失败

新重评job为`gpu1003-pydantic6283-qwen36-originalfp-v2-regrade-a1`；正式报告时间为2026-10-03 14:46:51 SGT。复用原`gpu1003-pydantic6283-qwen36-a1`的完整FP和baseline：canonical摘要分别为`1ac71744…`与`5db85318…`，FP只含`pydantic/root_model.py`。完整源码SHA仍为`2e8b2748…`，与之前真实CPU负对照一致，没有删去候选条目或改写旧分。

[题主核收](../coordination_20261003/6283_original_fp_v2_regrade_owner_readback_v1.json)逐项重算29件闭合原件、23件固定输入及相关报告共63个绑定的大小与SHA；重算FP／baseline canonical摘要，并核391个baseline tar成员的集合、内容和执行位，以及实际重建census与原census逐行相同。GPU实际使用的完整有效测试补丁与已封v2补丁逐字相同，参考列表相同，材料身份为`6cbe982f…`。

| 范围 | 新实际结果 | 含义 |
| --- | --- | --- |
| 原相等F2P与v1新增非示例F2P | 2／2通过 | 普通相等修复有效，未仅特判公开42示例 |
| 原38个P2P | 38／38通过 | 旧参考没有检出该构造与私有默认值组合 |
| v2新增PrivateAttr P2P | 0／1通过 | 可信构造后读取`_secret`抛出`TypeError` |
| 安装与完整测试 | RC0／RC1 | 安装成功后的普通候选行为失败 |

[原完整日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/pyd6283_original_fp_v2_regrade_v1/eval_logs/evallog_gpu1003-pydantic6283-qwe_52dd4531.eval.log)第3156–3161行显示，`PrivateRoot.model_construct(42)._secret == 'abc'`在`pydantic/main.py:685`访问`self.__pydantic_private__[item]`时得到`'NoneType' object is not subscriptable`。41个正式参考均与日志逐ID核对，无缺失或跳过。整个pytest命令的摘要为1 failed、42 passed、3 xfailed，包含非参考节点，不能把46个收集节点替代正式41项分母。

实际导入路径为`/testbed/pydantic/__init__.py`、包版本2.0b3；运行前后正式测试脚本摘要未变。实际镜像为`540e1b34…`，现场Id／Config／RootFS／Architecture／Os与此前已核公开wheel权限修复镜像相同；双UID读取与八wheel字节校验复用对应v3证据。此次是独立trusted grader重评，没有启动新公开actor或模型，也不声称新增HTTP首消息或完整角色隔离验收。

## 为什么判候选未完成正确修复

候选保留基类无验证构造，再无条件执行`m.__dict__.pop('__pydantic_private__', None)`。普通RootModel的None占位可被移除，但有PrivateAttr的子类在构造期间已初始化真实私有字典；同一删除会丢失合法默认值，随后属性读取退回类级None。这是保持既有行为的要求，不是强制某种内部实现形状。

该判断结合[原非作者七维初审](6283_qwen36_a1_preliminary.md)对公开文档、构造／post-init源码和候选的审阅，[v2实际CPU语义确认](6283_privateattr_v2_cpu_semantic_readback.md)及其独立核查，以及本次[非作者执行复核](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/pyd6283_original_fp_v2_regrade_execution_non_author_review_v1.md)。CPU对照中base的新P2P通过、gold全部41项通过；原Qwen等价源码仅新增P2P失败。本次进一步确认原完整FP在实际GPU评分链路得到同一失败。已有证据足以拒绝这个原候选，无须重复模型或CPU证明同一回归；不扩大为对所有合法实现、所有潜在回归或训练资格的证明。

## 原模型行为与效率

原轨迹初审保持原件，下面只接续其结论；补评分不产生新的定位、工具或模型验证事件。

| 维度 | 当前结论 |
| --- | --- |
| 方法与修法 | 经实验找到普通实例字典污染，但把合法私有字典也当作污染删除。普通修复有效，保留既有行为失败。 |
| 定位 | 首次完整正确根因陈述在原公开prompt后37.982秒；此前位置／关键字传参等假设经源码和实验纠正。沿用原轨迹时间证据。 |
| 工具 | 原38次请求、38个工具调用，含31 Bash、6 Read、1 Edit；3个探索/API错误及重复读取分别记录，不混作事后安装故障。 |
| 并行 | 首个message的两条独立Bash实际重叠；没有子agent调用证据。该一组机会不证明稳定并行能力。 |
| 验证 | 原模型选定公开测试通过，但没有覆盖可信构造与PrivateAttr组合。新的正式失败由评分端检出，不能反向算作模型当时已验证；“fix complete”表述过强。 |
| 效率 | 原solve为80.957秒；日志累计输入510,055、输出10,740 token，总计520,795，含反复送入的上下文。新补评分191.851秒属于评分开销，不增加模型求解时间或token。 |
| 结束与稳定性 | 原模型正常结束但候选有可证回归。仍只有一份Qwen首臂；Coder首臂及后续同条件重复待，不作模型间或稳定性比较。 |

## 清理、限制与接续

manager实际一建一删，open／supply／cleanup failures为空；12个保存exec阶段均RC0，其中候选包装器退出0只表示完成运输与收口，测试仍RC1。实际本job标签容器查询RC0空。执行者保存的闭合清单记录systemd inactive、MainPID0、ExecMainStatus0；题主未SSH复查GPU。专门结束后network原件、独立资源采样与CID覆盖缺席，保留未知；报告来源的grader峰值537.555 MiB单列，不写成独立实测峰值。

原模型服务身份仍沿用已核的[有限运营来源补证](../coordination_20261003/q12_limited_checkpoint_lineage_owner_readback_v1.json)，没有因这次零模型调用重评而补出原job当时的checkpoint快照。baseline环境digest仍null；本次prepare的环境身份不替代它。

本题v2新增保护已经解决已知漏检，不需再次修改材料来迎合此错误候选。GPU继续补尚未执行的Coder首臂，题主核其完整轨迹与候选；请求`swe-pydantic6283-behavior-v2-20261003`保持claimed，不ACK、不清活动指针、不标整题完成。原第一次纯计划缺固定request的失败及执行前false标志保留，不能改写为历史执行成功。
