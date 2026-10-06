# DVC9395 当前题卡

2026-10-03 21:15 SGT。**Coder首臂的同一个原候选已在CPU补评得有效0：3个F2P参考失败、37个P2P通过；41实际测试为4失败／37通过，额外原import测试也失败但不计分。题主与非作者评分／清理核收已完成。原GPU entry RC1／cleanup=false／reward=null保持；Qwen首臂仍待返回，成对请求继续claimed。**

本次唯一补评`dvc9395-original-fp-cpu-grade-20261003-v1`关联原`gpu1003-dvc9395-coder-a1`，不是新增模型样本。GPU已确认无重复评分并交CPU题主；完整原FP三文件、615项baseline、冻结code8/R20材料与2CPU／4GiB／PID512／UID54322、3600／900／120／1800预算保持。首次私有运输权限拒绝与只读归档脚本错误另存，均未启动重复候选或改材料。

## 首轮候选与正式评分

[同原FP补评分读回](coder_a1_same_original_fp_cpu_grade_owner_readback_v1.md)、[核收摘要](coder_a1_same_original_fp_cpu_grade_acceptance_v1.json)与[非作者新run审查](../../reviews/non_author_dvc9395_same_original_fp_cpu_runtime_20261003_v1.md)完整闭合38件原件、41节点／40参考、安装0／测试1／外层0、实际UID／资源与两层清理。实际基线重建615项逐类型／mode／SHA一致；投影包含`dvc/stage/__init__.py`及两项根目录生成脚本。原FP canonical `1cad35171d386f0d905859d0232d29d7df9a398872d62e6e71e98ffc8d0cd456`没有改动。

真实missing-source、import和frozen恢复堆栈均在 `_check_missing_outputs()` 先抛MissingDataSource，随后恢复不可达；restore-pull保存输出时抛OutputDoesNotExistError(bar)，helper的本地checkout没有恢复远端缓存。`out.exists`是property，不误报缺少括号。原[七维轨迹／语义审计](coder_a1_semantic_audit_v1.md)及[非作者语义报告](../../reviews/non_author_dvc_three_coder_a1_semantic_review_20261003.md)仍适用，候选确为错修；没有为使其通过而放宽材料。

原GPU求解215.507秒、正常completed，因relay删除60秒超时未进入grader；原[执行独立报告](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/closed_four_execution_non_author_20261003_v1.md)和10:27UTC清理恢复原件保持。新CPU评分246.473秒单列，不改原模型用时或null。本次补评不能证明GPU relay超时根因已修复。

hasattr自测不核实际恢复，后台测试stopped／管道BrokenPipe无完整回归，FP保留2个脚本；hygiene clean不表示候选最小或正确。原服务25个模型文件含16个权重分片，declared count28与数组25不同，没有全权重重hash或GPU内存证明。原baseline环境lineage仍null，不以prepared摘要补填。

新CPU有51个自有cgroup样本及关闭前kernel累计peak/events，memory.peak1033506816B、pids.peak11、PID限额与OOM事件0、OOMKilled=false；manager创建／移除均1，slot finished／returncode0，结束后精确label复查无残留。原diagnostics.resource_facts仍null；这些观测只覆盖新grader，不推广到原GPU solver或全host。官方parser计数42含一条captured ERROR日志，pytest实际41、计分参考40分开，逐参考状态一致。

## 当前材料与CPU对照

[revision](revision.json)固定`dvc9395-behavior-v2-draft`：核真实missing-source恢复、下游产物、import及用户修改保护；追加frozen、dry、无remote、no-run-cache、无hash、依赖变化和HTTP恢复共11参考。dry缺源允许原报错但无状态变化；不扩目录部分删除歧义。

[R20正式矩阵](formal_matrix_r20_v1.json)六项0／0／1／0／0／0，41实际／40参考、3F／37P；正确c3_frozenfix全41通过。gold和吞异常错解仍失败原missing-source F，却通过新增frozen F，不能说新增F判掉它们。[CPU验收](cpu_acceptance_r20_v1.json)和[非作者矩阵／actor适用核查](../../reviews/non_author_formal9395_r20_runtime_review_20261003.md)复用；R5公开actor17通过按同public输入复用，不重跑矩阵。

旧R14两次protect300 infra/null不计行为负例；旧R20六项准备149—249秒、新原FP准备156.179秒都不证明旧争用或效率根因已消除。准备900是原精确任务／材料／镜像绑定政策；未新扩预算。writable-layer总配额仍只有配置，未新增强制生效证明。

## 下一步

等待Qwen首臂及其完整候选／轨迹与执行独立证据，分别核语义、评分和基础设施状态后再决定成对核收。当前无需重复solve、原FP评分或已验矩阵，不自动普通追加采样，不宣称稳定性或训练／留出用途。[固定请求](probe_request.json)及其SHA不变，claimed／active指针保留。[结果结构记录](results.json)、[旧题卡](history/card_before_coder_a1_20261003.md)和[旧CPU补评前快照](history/cpu_original_fp_grade_started_20261003_v1/card.md)保留。
