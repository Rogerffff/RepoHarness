# DVC9395 当前题卡

2026-10-04。**双模型首次候选已完成题主及非作者语义／执行核收，请求已ACK、活动指针已释放。** Coder原GPU null／入口1／cleanupfalse保留；同一个原FP CPU补评分为有效0、F0/3／P37/37。Qwen原GPU有效0、F1/3／P36/37。两边实际均41节点37通过／4失败，但失败节点不同。材料R20不变，没有追加求解、评分或矩阵。

## 两模型候选与正式评分

[配对分析](../../dvc9395_two_model_first_round_audit_20261004_v1.md)、[配对验收](two_model_first_round_acceptance_v1.json)、[Coder七维](coder_a1_semantic_audit_v1.md)、[Qwen七维](qwen36_a1_semantic_audit_v1.md)分别记录候选、轨迹与原始结果。[新非作者执行报告](../../reviews/non_author_dvc9395_pair_execution_review_20261004_v1.md)及[新非作者语义报告](../../reviews/non_author_dvc9395_qwen_pair_semantic_review_20261004_v1.md)已完整核收；Coder既有语义／执行与[同原FP CPU验收](coder_a1_same_original_fp_cpu_grade_acceptance_v1.json)固定版本复用。

Coder在缺失检查之后才恢复，真实缺失时不可达；helper只有本地checkout，无新增远端拉取。CPU补评3F失败／37P通过，额外原import也失败。新CPU任务仅评分同原FP一次，不构成新模型样本、不覆盖旧GPU评分前relay删除超时，也不证明旧根因修好。[CPU完整读回](coder_a1_same_original_fp_cpu_grade_owner_readback_v1.md)保留38件、615基线、UID54322预检／安装0／测试1／外层0及评分清理；原FP三项包含stage与两根脚本，CPU投影三项不删。

Qwen将真实pull／checkout放在缺失检查前，普通source恢复与新增frozen F通过；复合原source F的失败发生在后段repo import，get_used_objs对该类型返回空映射，checkout仍缺缓存。另一个原F需要恢复远端run-cache，候选没有补该路径。新增P中modified、无缺失且无远端时仍多余调用cloud.pull，抛NoRemoteError；不把此失败描述成日志已证明覆盖源码。其余36P通过；额外原import失败而未计分。

Qwen完整FP为stage、command帮助、追加公开测试共3项；评分projection只应用两个源码，hygiene clean不表示完整FP没有测试改动。429封存成员／45,840,124字节全核，615基线逐类型／mode／SHA匹配。正式40参考与41actual逐节点绑定，parser42还含captured ERROR伪条目；不重复计算。

## 轨迹质量与限制

Coderhasattr自测不验恢复，后台测试stopped／管道BrokenPipe无完整回归，原FP保留2脚本；solve215.507秒，原GPU未评分，独立CPU评分246.473秒。Qwen真实push／删除文件和缓存／repro／内容检查，修了不存在导入；追加测试先修target，再将对象identity改addressing，保留恢复内容断言。最终五组公开193项（含追加2）均有结束摘要，但未覆盖imports／远端run-cache／modified无远端；总体完成判断过宽。

Qwen1264轨迹行、88工具（Bash51／Read29／Edit8）、88请求、CC89回合；29Read／8Edit文本回放等于最终FP。首SSE含2工具，其余单工具、末次纯总结，不能由总数推物理并行。全部工具ID／name匹配，86参数对象相同；工具50补默认replace_all=false、57去cd前缀两处保留。最后CLI过滤器抹repro输出，文件存在及内容观察有效，退出码未单独验证。

Qwensolve260秒／评分268.066秒，累计输入3,068,590／输出16,725，实际max_tokens65536与metadata32000分开；无观察到预算耗尽／stream_error。UID预检0／安装0／测试1、求解和两层清理true、精确PID1成功journal均核。两次不同验证覆盖的单次用时不作稳定速度排名。

原Coder模型清单声明28／列出25（16权重），Qwen声明40／列出37（26权重）；实际容器／只读挂载／HTTP配置另核，但没有重复全权重SHA或GPU内存身份验证。baseline环境lineage和diagnostic资源字段null保留，有限monitor不推全程峰值／零事件；8GiB配额仍只有配置证明。CPU补评分51个cgroup样本、关闭前kernel累计peak/events及精确label无残留只覆盖新grader，不推广原GPU。setup900已绑定；本次Qwen228.025秒／CPU156.179秒低于旧300，不能据此证明900必要或旧争用根治。

GPU回告曾误写Qwen P37/37，原评分／pair回执一直为P fail1/37；官方correct-summary保留旧摘要并更正，不重跑或修改评分原件。

## 当前材料与CPU对照

[revision](revision.json)固定`dvc9395-behavior-v2-draft`：核真实missing-source恢复、下游产物、import及用户修改保护；追加frozen、dry、无remote、no-run-cache、无hash、依赖变化和HTTP恢复共11参考。dry缺源允许原报错但无状态变化；不扩目录部分删除歧义。

[R20正式矩阵](formal_matrix_r20_v1.json)六项0／0／1／0／0／0，41实际／40参考、3F／37P；正确c3_frozenfix全41通过。gold和吞异常错解仍失败原missing-source F，却通过新增frozen F，不能说新增F判掉它们。[CPU验收](cpu_acceptance_r20_v1.json)和[非作者矩阵／actor适用核查](../../reviews/non_author_formal9395_r20_runtime_review_20261003.md)复用；R5公开actor17通过按同public输入复用，不重跑矩阵。

旧R14两次protect300 infra/null不计行为负例；旧R20六项准备149—249秒、新原FP准备156.179秒都不证明旧争用或效率根因已消除。准备900是原精确任务／材料／镜像绑定政策；未新扩预算。writable-layer总配额仍只有配置，未新增强制生效证明。

## 下一步与历史

DVC首覆盖完成，当前无必跑CPU／GPU缺项，进入训练信号与候选错误分析；普通追加采样暂缓。有效失败不构成放宽材料或重复求解依据，稳定性／训练与留出资格／最终用途未判定。[固定请求](probe_request.json)及SHA保持，当前状态见[results](results.json)。[Qwen返回前题卡](history/card_before_qwen_pair_20261004.md)、[旧题卡](history/card_before_coder_a1_20261003.md)、[CPU补评前快照](history/cpu_original_fp_grade_started_20261003_v1/card.md)和全部原报告保持形成时状态。
