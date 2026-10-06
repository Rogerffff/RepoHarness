# Dask7305：大整数精确端点与 auto 行归属

2026-10-04T01:43:32.012930+08:00。两模型各一次首轮已完整核收、总账已ack并清活动请求：Qwen code9/R25原raw0；Coder原GPU prepare300 None及setup900/PID143保留、同原FrozenPatch CPU派生0。两候选均在uint64 1输入/3输出分区最小端点偏大1，105参考齐、104P通过，auto未到达。Qwen[分析](model_probe_qwen36_a1_analysis_20261004.md)与[非作者核](../../reviews/non_author_7305_qwen36_a1_candidate_review_20261004.md)一致：局部摘要修复遗漏后续浮点插值，未发现新增材料缺陷或误拒。本次零CPU/模型/控制新运行，不因此追加重试，不授稳定能力/训练资格。

新评分shell需在激活／安装carry恢复之后、pytest／数学库导入之前明确Dask池2与OpenBLAS线程1，附带OMP/MKL/NumExpr线程1，另核完整实际脚本摘要。保留processes路径、105参考、2CPU/4GiB/pids512及测试预算，不解除既有slow skip。历史CPU worker/BLAS数未知，不能从其通过补造为2。[三题适用范围独立核](../../reviews/non_author_dask_thread_budget_applicability_review_20261003.md)：7138/9378仅默认threaded可达，无同类process现场证据；8801读取ambient DASK变量，避免机械加入DASK_NUM_WORKERS。

实际原评分是deny_all单shell：supply=null，按combined脚本摘要绑定，五键在安装/激活后且pytest/native import前加入。after-install只核将来分段入口在carry恢复后的消费位置，本次不启供应网络或执行分段模式。[运行模式纠正](grader_execution_mode_correction_20261003.json)另存，旧发布对齐记录保留；CPU纯构造、[独立静态核](../../reviews/non_author_cpu_same_fp_regrade_worker_review_20261003.md)与实际运行验收均完成。

固定R15/source050 v2完整17行已于09:56 SGT自然结束，186份原件已逐SHA／大小回收；[非作者完整结果核查](../../reviews/non_author_7305_formal_cpu_r15_review_20261003.md)通过。实际只有 `gold_full_auto` 为1，其余16行为0；这些CPU控制结果不能转移给实际模型候选。完整[作者读回](formal_cpu_readback_r15_20261003.json)保持固定字节，[双模型首轮请求](probe_request.json)字节不改。

公开要求是大整数分位数的精确端点，`set_index` 每行须落在自身分界区间；内部分界允许近似，不锁成gold的具体值。当前v3保留v2七组大整数控制及1F/104P，补1000个乱序大uint64、最小值置末尾、4个输入分区的auto实例。auto只传给支持它的`set_index`；端点、总行量和归属用Python整数比较，避免uint64/float64提升掩盖错误。原题面保持不变。

| 候选组 | 本轮正式实际分 | 实际参考与边界 |
| --- | --- | --- |
| gold_full_auto | 1 | 105参考通过；正确替代解覆盖精确端点及整数auto归属 |
| noop / source gold | 0 / 0 | 各1F失败、104P通过，原gold标签不代替正确性判断 |
| gold_full / exact_full / higher_full | 0 / 0 / 0 | 各104P通过，仍在新auto控制失败 |
| 7份机制错解 | 全为0 | 105参考均有状态；first_last另失2项已知旧P，其余六份104P通过 |
| rv_pin_noclip / rv_interp_pin_noclip / rv_maxonly_threshold / rv_k_le4 | 全为0 | 本次完整正式模块均实际拒绝，并补齐此前未执行的104P，全通过 |

每行105个正式参考完整。`first_last`实际3 failed/102 passed；正对照105 passed，其余负对照1 failed/104 passed。每个完整模块另有3个未列入正式参考的既有skipped，均照实保留，不能说整个模块没有跳过项。安装、测试与清理均完整，无本轮基础设施失败。完整17行列表、逐参考、日志和SHA见固定读回及[矩阵](acceptance_matrix.json)。

`gold_full_auto`在历史`gold_full`上修补整数auto分支，从精确摘要取分界，避免浮点插值；非整数分支保留原逻辑。非作者已核实际失败机制、公开接受性和材料／运行绑定。此处确认已运行的有限对照范围，不证明穷尽所有输入或授训练资格。负对照提前失败时，后续断言未执行，逐行实际失败分支以独立报告为准。

来源镜像初始config inspect、运行manifest验证与账本`image_id_actual=null`分开保留，不填成每个评分容器独立实测config。UID54321/评分策略54322沿实际账本与冻结执行路径核，没有本轮各进程新增`id -u`输出；资源为policy，`resource_facts=null`。base为`8663c6b7813fbdcaaa85d4fdde04ff42b1bb6ed0`，setup仍300秒，没有热改配方、评分器或在途材料。GPU须留实际部署、公开交付与评分原件。

历史[公开actor和私有CPU读回](cpu_readback_20261003.md)含真实非root CC2.1.205原题面首请求、原公开shuffle模块104 passed/3 skipped、13份完整私有模块及4份聚焦F2P；是脚本桩，无基座推理。历史定向结果没有执行104P的范围已保留，本次完整17行另存新原件。旧正式v1只完成首noop后被作者wrapper的来源ID断言中止，不能冒称完整验收；当前可变记录已分离v1部分结果和v2完整结果，不回写原件。

固定版本为 R15 `cat2-cpu-r2e089092-swe39-dask-monai-20261003-v1`。材料见[revision.json](revision.json)，当前机器记录见[results.json](results.json)、[cpu_acceptance_plan.json](cpu_acceptance_plan.json)。已有[材料和历史CPU窄核](../../reviews/non_author_cpu_and_7305_review_20261003.md)保留原范围；v2历史依据见[09-30交接](../../../../../category3_diagnosis_20260929/handover_to_category2_20260930.md)及[原结果](../../../../../category3_diagnosis_20260929/tasks/dask__dask-7305/result.md)。当前两模型首轮与非作者候选核均已完成，原Coder同FP补评分和R23来源身份保持；Qwen code9/R25实际输入/镜像ID/完整脚本/五export已核。不替换原探针候选、不重复有效CPU矩阵；未发现新增材料缺陷，不授训练资格或整题完成。

实际新job `dask7305-original-fp-cpu-recovery-20261003-v2` 使用setup900及五键recipe，single-shell摘要已核。实际UID54322、2CPU/4GiB/pids512/断网，两个原processes节点均通过；PID峰值27、max事件0、无OOM。selected env与num_workers=2已读回，但各pool子进程env和BLAS内部计数未直接测量。三个原slow skip仍属于正式参考外。58份原件374,598B闭合、manager1创建/1移除、自有容器0、槽已结束，详见[固定补评分读回](coder_original_FP_CPU_recovery_readback_20261003.md)。旧CPU v1在grade前镜像API表示检查失败，独立API绑定核后新版本完成；旧失败原件不改。

已验环境支持`support-swe-dask-grader-env-20261003-v1`已入账并直接交发布/GPU，R23已封包返回并确认、直接交GPU，继续缺失模型臂。该CPU运行依赖已关闭；7138源归档供应与恢复作业依赖已核关闭，文件保留；整机其它依赖由发布合并。此次未重验actor、不授训练资格，也不扩大线程变量到其它Dask题。

R23来源consumer及已验CPU配置保留。首Qwen实际code9/R25作业的镜像ID、材料、single-shell完整五脚本、setup900与五export已核，与Coder CPU有效评分脚本相同；148原件17,888,313B和33回执引用全SHA、3次Edit重放一致。grader33样本PID峰19/max0、内存峰2,261,078,016B/事件0，无OOM；自然结束、双层清理和drain齐。原policy的actual_image_inspect_verified=false、actual_execution_mode=null、two_stage=false及原diag resource_facts=null保持，声明profile与观察事实另列，不升级完整Docker Config/内核profile或子进程env验收。详见新分析；旧在途code8不热换。
