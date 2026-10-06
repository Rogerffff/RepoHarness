# ea6906b0：保留规则内容并忽略HTML报告

2026-10-04。**R28的51项评分材料已发布并完成实际CPU及非作者增量验收。两份原模型补丁均50/51、奖励0：旧49全部通过，各自一个新增行为键失败。原GPU49/49、奖励1报告保留，没有重新模型求解。**

公开目标是保留已有用户`.gitignore`内容，让首次及再次生成的报告文件被真实Git忽略。本轮只补其既有行为验收，不增字节相同、文本幂等或指定实现要求。

| 输入 | 原GPU49项 | 新CPU51项 | 实际语义结论 |
| --- | --- | --- | --- |
| 原Coder完整FP | 49/49，1 | 50/51，0 | 特殊CSS字面名漏Git忽略；新CSS方法失败 |
| 原Qwen3.6完整FP | 49/49，1 | 50/51，0 | 既有规则使处理跳过；新已有规则方法失败 |
| safe_append私有正控制 | 非模型 | 51/51，1 | 原49及两个新方法全通过 |
| noop私有负控制 | 非模型 | 41/51，0 | 两新方法及原8项失败 |

[新评分补充分析](model_analysis_scoring51_supplement_20261004.md)、[最终CPU验收](cpu/scoring51_final_acceptance_20261004_v1.json)和[非作者实际核查](../../reviews/non_author_ea69_scoring51_full_FP_CPU_review_20261004_v1.md)共同说明本次修订已能识别两份候选的已知公开目标缺口。没有把单次样本据为能力排序或稳定性结论。失败方法首错停止，完整边界反例仍见[此前CPU窄验](cpu/qwen_boundary_and_scoring51_closeout_20261004_v1.json)。

## 材料与实际消费

R28保留073公开测试兼容与093题面，登记096/097替换旧074/075的私有test_2/expected。旧49方法和期望保持，新增CSS字面名与已有规则两键。公开题面、brief、源镜像、base和配方均不变；私有评分改变，因此整个环境包摘要已更新；[旧50提案](generated_css_material_revision_proposal_20261003_v2.json)未发布，由51项提案接续，历史不回写。

新可信评分面摘要f7a65179…；root按其固定身份恢复正文，真机核新f6052572…测试树、原run_tests.sh及四个官方文件保护。评分容器显式用原精确e23镜像，各自重建同一360项基线后应用完整FrozenPatch，不从审阅diff重建候选。Qwen53248B.coverage与html.py两条完整保留；不宣称原DB各记录都被测试消费或已作DB污染专项复验。

四次正式评分安装均跳过/RCnull，safe测试rc0，其余测试rc1明确归tests_failed而非infra。全部job/wrapper rc0，2CPU/4GiB/512、断网、无挂载；正常结束后在途和容器0。可信prepare与四次评分合计103个payload项、5份清单、108个tar成员全核；[计数命名勘误](cpu/scoring51_archive_count_erratum_20261004_v1.json)保留作者原报告字节。

## 当前交接和后续边界

发布请求 `r2e-coveragepy-ea69-scoring51-publish-20261004-v1` 已returned/ACK，活动指针清空。当前CPU验收和本次增量独立核查完成，本轮无剩余CPU实验或新GPU求解。

旧R6公开缺项与旧R17评分盲区版本仍保持阻断；原49分不用于宣称候选完整成功。新51的CPU direct评分资格与未来actor/overlay资格分开：旧949B overlay保留旧测试树facts，不能直接作为新51 PreparedTaskFace完整overlay资格。未来另选新求解或可选校准时，须先核该次实际actor构造及镜像身份；本次不授GPU或训练资格。

## 历史证据

[首对七维分析](model_analysis_first_pair_r17_20261004.md)、[Coder原分析](model_analysis_coder_r17_a1_20261003.md)、[Qwen原分析](model_analysis_qwen36_r17_a1_20261004.md)原SHA不变。R17公开目标交付、[公开读者](../../reviews/fresh_ea69_statement_preserve_reader_20261003.md)及[CPU公开验收](cpu/cpu_acceptance_r17_closeout_v1.json)按未变范围复用，旧R6 Qwen不混作R17样本。

[当前结果清单](results_manifest.json)只列现版；完整旧字段见[历史导航](../../history/scoring51_20261004/results_manifest_pre_R28_navigation_20261004.json)，[历史卡片](../../history/scoring51_20261004/card.md)保留先前进程和矩阵。
