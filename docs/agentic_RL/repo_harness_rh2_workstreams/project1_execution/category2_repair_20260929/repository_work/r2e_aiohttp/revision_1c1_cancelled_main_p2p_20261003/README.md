# 1c1：取消清理保留P2P修订

2026-10-03。本批已批准的一项P2P已发布为R22的094/095，并沿固定入口完成五行CPU实测。**新判据检出完整原Coder的资源收尾回归；baseline、gold、C1、完整原Qwen的新键通过，所有行旧58键逐项不变。** 题主与非作者执行窄核均已核收，详见[本批最终核收](review_acceptance_five_rows_20261003.json)；未授训练资格。

| 原候选／对照 | 新版匹配数 | 新P2P |
| --- | --- | --- |
| baseline | 57/59 | PASSED |
| gold | 59/59 | PASSED |
| C1 | 59/59 | PASSED |
| 完整原Coder7条 | 58/59 | FAILED |
| 完整原Qwen2条 | 59/59 | PASSED |

[逐键实际结果与固定原件](results_five_rows_20261003_v2.json)、[题主语义与范围核收](assessment_five_rows_20261003.md)。Coder失败快照在observer补清理前：worker未done、generator/loop未闭、pending1；其余四行worker/generator finally完成、loop闭、pending0。基线旧两个F2P失败保留，不要求基线解决原问题。

题面、runner、旧58键与原两种合理错误上报方式不变。新函数只从精确R6 080父材料插入一次，旧全部顶层AST及58状态保持。[材料非作者窄核](reviews/non_author_cancelled_P2P_material_20261003.md)已完成且[核收](material_review_acceptance_v1.json)；[实际执行窄核](reviews/non_author_cancelled_P2P_execution_20261003.md)沿用同一ProductionTracer，已核收并停止，不增加审查轮次。

[材料清单](material_manifest_v1.json)、[局部检查](local_material_checks_v1.json)、[发布操作](publication_operations_v1.json)、[固定发布请求](publish_request_v1.json)。094/095替换080/081，没有同目标叠加；正式59键现已在全部五行实际消费。

[完整候选运输核对](complete_candidate_transport_readback_v1.json)保留coverage/helper；CPU实际新Frozen entries与原Coder7/Qwen2字节／模式一致，未删减候选。新grader的实际ID、材料树、runner、完整结束与本批清理见实际结果，不用旧actor冒称新grader。null元数据、缺少独立cgroup/prelaunch原件、未触发timeout及原actor失败探测标记如实保留，不扩成运行资格。

旧首轮raw1/58、原Frozen及历史报告原样保留；本批重评分是新材料诊断，不增加模型样本。旧binding `80e6573433d21aa2e3cc4477e3d84f58ed1a1214c478a19167527278b9c0deea` 继续阻断复用；新材料最终核收后，未来GPU消费仍须新binding。普通重复仍按统一队列策略暂停，其他三题继续。
