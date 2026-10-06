# 016af5f6：不可编码文件名的保存行为

2026-10-04。**两模型首轮各原评分1／15参考键全匹配，符合当前保存/read目标；候选质量分别有余项，不能称全面正确或直接合入。** 首对总回执已returned/ACK，七维及非作者语义核查完成，无新材料阻断或必跑CPU；stage2追加计划本轮4次均未执行，现已returned/ACK且清除活动指针；仅保留后续可选校准计划。单次不判稳定，不授训练资格。

目标是让不可按UTF-8编码的执行文件名不导致保存崩溃，并保留正常文件的数据。允许跳过或内部转义等合理实现，不新增特定告警、坏名最终表示或题外API要求。

086隐藏测试与087修正公开示例已发布，保留001期望修订和15键。材料见[变更](material_changes.diff)与[实际版本清单](results_manifest.json)；草案901/902只用于历史解析，占位编号不代表正式登记。

实际公开CC桩首请求包含完整087题面；预检、解释器与工作树导入正常。初态示例产生预期编码错误，正常文件保存和加载成功，公开回归154通过、1跳过。两份二进制覆盖数据库形成非空FrozenPatch，完整基线、补丁运输及排除路径证据往返一致，正式回放14/15=0，仅目标键失败。该产物不是纯NOOP，矩阵另有独立base。见[公开交付原件读回](cpu/public_delivery_r6_check.json)。

原14行正式矩阵实际完成：6个合理候选各15/15=1，base与7个错误候选各14/15=0，只在不可编码文件名键不符。逐行补丁SHA、完整测试段、退出、身份和清理已核；所有自有标签容器／网络无残留。见[矩阵读回](cpu/formal_matrix_r6_check.json)和[作者CPU快照](cpu/cpu_acceptance_r6_v1.json)。作者快照的pending只记录当时状态，不回写原件。

[非作者CPU核查](../../reviews/non_author_016a_cpu_review_20261003.md)由干净上下文的GPT-6.1 Sol/high子agent完成，独立核855成员、14行逐键结果、真实首请求、工具返回及二进制往返，无具体阻断。它依据保存原件离线核查，未SSH或重跑，不是fresh公开读者；fresh阅读另见[公开静态阅读](public_reader_review_20261003.md)。原四条命令已经实际执行，旧六条重建命令仍是未执行的补充计划。

[probe_request.json](probe_request.json)固定R6/001+086+087和probe-wide-v1，每模型1次。CPU桩与固定候选不计模型结果。GPU最终镜像、代码、公开说明交付和模型预算由统一执行者读回；本题主收到完整回执后分析实际候选及评分，再决定必要修复。只报告明确标注版本的修订题诊断结果。

历史依据：[云端result](../../../../../category3_diagnosis_20260929/tasks/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae/result.md)、[v2独立复核](../../../../../category3_diagnosis_20260929/tasks/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae/review.md)。暂停原件保留，当前调度见[接续点](../../resume_checkpoint_20261004.md)。


## 两模型首轮与接续

当前R6保存目标15/15；同对象measured_files仍枚举跳过坏名，模型发现自测失败后改弱断言，两份SQLite是不必要生成物。这些余项不扩大成现行新评分目标；源码/公开测试完整改动和污染路径已独立核，无新材料阻断。 见[七维分析](model_analysis_qwen36_a1_20261003.md)、[非作者语义窄核](../../reviews/non_author_016a_qwen36_semantic_review_20261003.md)。原评分、FrozenPatch和所有自测失败保留。

Coder仅在文件表插入处捕获编码异常并return None，后续add_lines未筛None；原保存SQLite确有一条file_id=NULL行数据，正常normal.py第1行同时保留。四个新增helper没有存储内容/fresh read断言，final helper捕获异常仍无条件成功；本次实际helper未失败，不能称隐藏实际失败。既有公开tests未改，四helper及两SQLite保留。plugin/touch与重复孤儿行增长仅静态风险，未新增运行核查。见[Coder七维](model_analysis_coder_a1_20261003.md)、[非作者窄核](../../reviews/non_author_016a_coder_semantic_review_20261003.md)。

[首对当前分析](model_analysis_first_pair_20261003.md)区分现行目标成功、工程质量和单次消耗，不改原分、不扩大现行评分要求。旧Qwen单臂报告保留历史时间点。[第二阶段计划](repeat_sampling_plan_20261003.json)及[固定原请求](probe_request_stage2_20261003_v1.json)均保留原SHA：每模型额外2次的计划没有实施。

2026-10-04核收执行方[未执行返还回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/coverage016a_stage2_current_scope_deferral_receipt_v1.json)：追加4臂全部0执行，无本请求在途，原请求不是取消，也不是四次重复已完成。按照首轮覆盖优先、不默认追加的范围返还，已returned/ACK并清除活动指针。将其保留为后续可选校准；需具体重复选题后再关联旧request接续，不默认派GPU，不重跑首轮。
