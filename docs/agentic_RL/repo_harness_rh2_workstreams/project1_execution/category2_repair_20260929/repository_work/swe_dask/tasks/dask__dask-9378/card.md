# Dask9378：按用户 B 验收 mask 与值

2026-10-04T01:59:26.439112+08:00。Qwen原raw1/137参考全过；Coder原GPU None/同FP CPU1亦按用户B通过，旧可选参数限制分别保留。 当前目标经[新分析](model_probe_qwen36_a1_analysis_20261004.md)和[非作者核](../../reviews/non_author_9378_qwen36_a1_candidate_review_20261004.md)通过；双模型回执已ack，活动请求清空。实际code9/R25材料/镜像ID/完整脚本已核，当前没有新增题级阻断，不追加CPU或模型。单次结果不授稳定能力/训练资格。

采用用户已定 B：对应 `da.ma` 入口存在时它必须正确；入口缺失时接受顶层 `da.<like>` 的正确路线。保留原题面及已有 ma/map_blocks 修法提示，不要求新增 API。三项逐元素比较 mask，ones/zeros 再比较有效值；`empty_like` 未初始化值不作为判据。默认 shape/chunks 等已发现边界的对照不能证明穷尽所有实现。

| 候选 | 本轮正式实际分 | 关键证据 |
| --- | --- | --- |
| noop | 0 | 三项 mask 退化 |
| gold | 1 | ma 路线正确 |
| toplevel_only | 1 | ma 入口缺失，顶层正确路线被接受 |
| ma_mask_none / ma_mask_invert | 0 / 0 | ones/zeros 丢失或反转 mask，empty 通过 |
| wrong_values_seven | 0 | mask 正确，ones/zeros 的有效值却为 7；empty 通过 |

每行137参考完整、134个原回归项全通过；安装与测试区间完整，无基础设施错误，清理完成。76份原件的 SHA 和大小已读回核验，详见[固定作者读回](formal_cpu_readback_r15_20261003.json)及独立报告。最后一份错解是本轮新构造，不冒称尚未找到字节原件的历史 `invert_values7`。

来源镜像在准备阶段实际观察到 config ID，冻结评分路径逐运行容器校验 manifest。六行账本的 `image_id_actual=null` 保留；没有逐容器原始 config ID 或本轮独立 `id -u` 捕获，不以初始 inspect 或历史 actor 冒充。候选54321、评分策略54322的证据范围见独立报告；CPU验收不授予训练资格。

R15发布版本 `cat2-cpu-r2e089092-swe39-dask-monai-20261003-v1` 和材料已固定。旧v1完成首noop后由本包错误的来源ID断言中止，原件与[旧单行审查](../../reviews/non_author_source_image_matrix_adapter_r15_review_20261003.json)保留。新v2冻结快照使用 source050，完整六行重新运行；评分器、测试及配方未热改，旧原路径208仍保留。

历史[公开actor与私有CPU读回](cpu_readback_20261003.md)包括同源非root CC2.1.205首请求、134 masked及320个选取的creation-like公开项，属于脚本桩调用，不是模型推理。后续GPU必须重新核实际镜像、base、公开交付和预算，并将真实模型的原FrozenPatch与正式评分、完整轨迹关联。题主继续分析修法、定位、工具、并行机会、验证与效率，必要时复修；当前没有整题完成或退租条件。

固定输入：[revision.json](revision.json)、[acceptance_matrix.json](acceptance_matrix.json)。当前机器记录：[results.json](results.json)、[cpu_acceptance_plan.json](cpu_acceptance_plan.json)。base：`8b95f983c232c1bd628e9cba0695d3ef229d290b`；历史决定与证据见[09-30交接](../../../../../category3_diagnosis_20260929/handover_to_category2_20260930.md)及[原结果](../../../../../category3_diagnosis_20260929/tasks/dask__dask-9378/result.md)。

实际新job `dask9378-original-fp-cpu-recovery-20261003-v2` 为single-shell，完整脚本与原FP/code8/材料/137参考绑定已核；实际UID54322、2CPU/4GiB/pids512/断网。PID峰值53、max事件0、无OOM；内存峰值4GiB，memory.events max154，保留限额回收压力。50份原件339,204B闭合、manager1创建/1移除、自有容器0、槽已结束，详见[固定补评分读回](coder_original_FP_CPU_recovery_readback_20261003.md)。dtype真实失败、chunks/name/shape忽略与最终说明过宽仍见[原轨迹分析](model_probe_coder_a1_analysis_20261003.md)。

CPU v1因前序7305的grade前镜像API检查失败而未派发；独立API绑定核后新版本完成，旧失败和原None保留。已验环境支持`support-swe-dask-grader-env-20261003-v1`已入账并直接交发布/GPU，R23已封包返回并确认、直接交GPU，继续缺失模型臂。该CPU运行依赖已关闭；7138源归档供应与恢复作业依赖已核关闭，文件保留；整机其它依赖由发布合并，未重验actor或授训练资格。

R23共享consumer已返回并由题主确认，冻结版本与限制见[当前接续入口](../../preparation.md)。本题新Qwen code9/R25实际材料、镜像ID/完整脚本/预算已核；旧code8不热换。


本次新Qwen限制：仅默认B资格通过。新Qwen签名只a/dtype，不接受chunks/name/shape/order；原Coder dtype失败、chunks/name/shape忽略及过宽说明是该旧臂边界。Qwen少量dtype实例不证明全部可选API或稳定能力。 评分投影排除模型新测试，实际原FP与自测仍保留。详见新分析；不把旧臂缺陷默认为新臂同样失败，也不推广有限自测。
