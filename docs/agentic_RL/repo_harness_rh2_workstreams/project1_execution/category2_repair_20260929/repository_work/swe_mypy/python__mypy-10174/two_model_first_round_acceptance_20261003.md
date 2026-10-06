# 10174：两模型首轮验收

2026-10-03（Asia/Singapore）。当前材料 `mypy10174-strict-equality-v1`、正式1F/3P四参考。两模型各一次求解均正常结束，原候选语义在本题范围内成立、正式四参考通过。Qwen初始GPU安装失败仍保留；同原候选的新GPU恢复评分通过，不算新的模型样本。固定题主验收见[JSON](two_model_first_round_acceptance_20261003.json)，实际轨迹与比较见[Coder分析](coder_first_arm_trace_20261003.md)。

| 观测 | 实际修复 | 正式评分与环境 | 当前判断 |
| --- | --- | --- | --- |
| Qwen3.6首轮 | 修改 `mypy/meet.py`，去None后重检Any | 旧32f镜像四PASS/raw1，但editable实际RC1；随后同完整原FP在804/code8安装成功、四PASS/reward1 | 本题范围内成功，原失败与恢复分别保存；仅一个求解样本 |
| Coder首轮 | 修改 `mypy/checkexpr.py`，提前简化非strict_optional的Union | 804镜像actor/grader、code8；实际安装/测试0，完整footer四PASS/raw1，清理正常 | 本题范围内成功，原66项全部评分；仅一个求解样本 |

两个修法都消除公开误报，并保留真正不重叠比较的诊断。当前参考覆盖公开Optional[Any]问题、两条已有Any提示和新增非strict-optional下的Tuple负例；不能据四项通过证明全部mypy行为或所有底层overlap调用点等价。原CPU R6 noop/gold/bad为0/1/0，不重跑已完成矩阵。

Coder闭包552件全部核SHA/大小；完整1472项基线内容、文件类型与执行位相符，actor/grader census相同。与Qwen基线内容行相同，但规范摘要因runtime镜像身份不同而不同。Coder原FP66项包含55cache、10开发脚本和源码，全部投影；Qwen原51项中的候选测试修改被可信投影排除，原50项含49cache继续保留。没有换成净化补丁或用作者重建候选替代原FP。

受信评分的测试恢复/保护、runner前后摘要、实际参考执行与解析及actor/grader清理完整。完整安装日志支持三项安装成功，但没有逐成功安装命令的独立数字RC；记录的安装RC0是末命令、测试RC0另有实际记录。没有新增pytest进程内目标模块SHA、完整环境资格或包版本锁的证明。systemd已收集后的默认ExecMainStatus0不作成功依据。

题主独立核原件后合并本批新增[执行追踪](../reviews/non_author_10174_Coder_first_arm_execution_20261003.md)和[语义反证](../reviews/non_author_10174_Coder_first_arm_semantics_20261003.md)。执行角色核152个目标原件及当前调用链，语义角色核36个目标原件及完整FP/tar/四参考；不把两者的范围合并成每个角色都核552件。两位均见旧10174/gold/private上下文，非fresh；公开字节未变，复用适用已有公开依据，不增设公开读者。

没有发现当前候选或四参考评分的实质缺陷。Coder根因解释中的源码顺序错误、内联flags伪对照、Union[str,float]输出误读和“全部既有测试通过”的过宽声明，保留为P3行为问题。实际修复效果与解释质量分列，不修改raw1，不为得到更好的轨迹重复求解。

两模型均有有限运营来源归因：Qwen Q12已有87请求/adapter/后端完成补证；Coder有启动前实际服务/只读mount/下载manifest、25文件尺寸及本题68请求/adapter/SSE对应。Coder prejob backend日志没有覆盖本题68次生成完成。旧checkpoint false及HTTP revision/checksum null保留；manifest声明28但只列25，3项未知；未重新hash全部权重或证明GPU内存内容。

Coder求解150.336秒、68生成/67工具、累计输入2,869,312；Qwen273.650秒、87生成/86工具、累计输入2,234,730。两者API总时间接近，公开自验工作量及求解环境不同；累计输入包含重复上下文，CC美元数为别名估价。单次记录不用于模型速度、成本或稳定性排名。

原请求 `swe-mypy10174-strict-equality-v1-20261003` 保持输入SHA `117617f7…c5f7c`。执行者已returned；题主完成原件、语义和非作者核收后按工具ack并清空活动请求，当前状态看[总账](../../../repository_work_packages_20261002.json)。迁移请求中code_v3 blocker及legacy_gpu_status为已失效历史提示，现有工具无定点修改入口；当前progress及本验收承接现状，不能据历史字段重复派发或修环境。

本题无已知CPU/GPU计算待办，普通追加采样按覆盖优先暂缓；只在新具体缺陷或材料身份变化时按影响接续。两臂二元reward均1，没有本题成败分歧；定位、验证及表述问题可供跨仓分析，不能据单题断言训练收益或训练饱和。稳定性未知，训练/留出资格未授予。此处只记录题级依赖，不操作租机、停机或销毁。
