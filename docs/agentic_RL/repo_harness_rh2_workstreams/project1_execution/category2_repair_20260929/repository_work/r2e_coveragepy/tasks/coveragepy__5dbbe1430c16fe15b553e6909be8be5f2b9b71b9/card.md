# 5dbbe143：采用已决定的按 slug 题面

**已按统一恢复通知继续。当前接续与CPU门控见[恢复检查点](../../resume_checkpoint_20261003.md)；历史暂停记录保留。**

2026-10-03。**R5 CPU与非作者核查通过；双模型首轮已返回，原 FrozenPatch 正式评分各76/76，最终源码均满足A。七维轨迹分析与非作者候选窄核完成，等待同条件重复采样。Coder留下2个失败的新测试，完整候选不能作为干净修复示例。**

- 已决定：用户 09-29 选 A；同 slug 后续 once 警告不重复，不同 slug 各显示一次。不重问、不用两种相反语义做 OR。
- 实际处理：`materials/statement_A.txt` 与已通过新公开读者的云端版逐字一致，摘要 `b2a7f5fb…`。保留 038/039 与 v5 的 76 键，私有评分材料无本轮新变化。
- 候选：正式矩阵采用原 `runs/r2e_actor_20260925/grader_cands` 的 CE1/3/4；云端重建补丁仅作历史对照。字节比较在本包 `static_checks.json`，不能以重建版替换原工件身份。
- 材料与矩阵：[revision_draft.json](revision_draft.json)、[cpu_matrix.json](cpu_matrix.json)、[results_manifest.json](results_manifest.json)。已有 v5 正式矩阵与新公开读者可复用；题面-only 不机械重跑不变评分集。
- 发布：非作者[窄核通过](../../reviews/non_author_5dbb_statement_A_review_20261003.md)，维护者登记 **068** 进入 `cat2-cpu-r2e066068-swe5-20261003-v1`（material_v14／pins_v15）。本地与远端外部 manifest 已核，总协调确认完整回读；038／039、76键原样，不把静态检查记成真实题面交付。
- CPU：第五版 prepared／A题面／038/039/068／76键已核；派生 image `5091d0c5…` 复用已完成第四版身份，配方及该题材料字节不变。实际首条CC请求完整交付正式prompt/A；agent预检/环境通过，两个MCVE复现初态错误，公开warn6通过。NOOP 74/76=0、原CE3 76/76=1、原CE1 75/76=0。三次正式评分及actor正常退出、零容器/网络残留；完整基线与冻结补丁往返通过。
- 证据：[cpu_acceptance_r5_v1.json](cpu/cpu_acceptance_r5_v1.json)、[实际题面交付](cpu/public_delivery_r5_check.json)、[CE3逐键](cpu/ce3_r5_per_key.json)、[CE1逐键](cpu/ce1_r5_per_key.json)。原件在验收JSON所指忽略目录；CPU桩不是基座模型成绩。
- 模型：[七维分析](model_analysis_20261003.md)及[机器记录](model_analysis_20261003.json)已完成；[非作者候选窄核](../../reviews/non_author_5dbb_model_semantic_review_20261003.md)确认两臂源码符合A，无题面／环境／评分新阻断。Coder新测试实际2失败未清理；Qwen公开helper扩签名未改断言，正式once键直接测真实stderr。两臂生成数据库均保留原工件身份。
- 剩余：首轮每模型仅1次；GPU[第二阶段安排](repeat_sampling_plan_20261003.json)已登记各追加2次至总3次，共4条新尝试，当前未派发。新题首轮／缺臂优先；本题暂无新CPU修复依赖，新增结果逐次分析。原请求已returned／ACK，保留原ID/SHA及当时记录。本题保持第五版，不因其它题第六版发布热切。
- 当前用途：标明R5自建修订版的普通基座诊断；源码正确、原评分和完整候选质量分别报告。不能报原benchmark成绩、单次稳定性或训练资格。

历史依据：[用户 A 与落实](../../../../../category3_diagnosis_20260929/tasks/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/result.md)、[修后新读者](../../../../../category3_diagnosis_20260929/tasks/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/public_read_revised_A.md)。
