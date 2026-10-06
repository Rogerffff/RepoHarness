# Dask7305 补评分线程预算：最小环境恢复建议

2026-10-03T16:45:21.989414+08:00。**建议已整理并经非作者窄核，尚未部署或实测通过。** setup900补评分已进入pytest，但现场24个spawn及数学库线程叠加，pids峰512且max事件1，无OOM。评分容器2CPU是配额，旧Dask只认识cgroup v1，当前v2下实际CPU_COUNT仍24。最小恢复是新评分运行明确`DASK_NUM_WORKERS=2`与`OPENBLAS_NUM_THREADS=1`，附带OMP/MKL/NumExpr线程1；保留原候选、scheduler、105参考和资源/测试预算。

| 对照 | GPU此次实际现场 | 既有CPU noop / gold_full_auto |
| --- | --- | --- |
| 镜像config | b4f186ca，原同FP | 同b4f186ca来源inspect，运行manifest21fd7dd8固定核 |
| 资源 | actual2CPU/4GiB/pids512，cpu.max200000/100000 | 同policy；没有本轮cgroup/NLWP/实际CPU_COUNT实测 |
| 默认并行 | os.cpu_count/affinity/DaskCPU_COUNT皆24，num_workers null；24spawn | worker/BLAS线程数未知，不从通过结果补造为2 |
| 线程／BLAS | pytest39线程，部分spawn32；Python进程合计495；实际映射OpenBLAS0.3.25，选定线程env无设置 | 无实际线程/后端证据；镜像Config.Env只有PATH/TZ，不能当shell完整env |
| 结果 | pids.current500、peak512、max事件1；无OOM；GPU有界终止pytest后infra/None，105参考不完整，清理完成 | processes tasks/disk两组都PASSED，各约32–35秒；模块测试122.938/125.66秒，105参考完整 |

现场支持Dask默认池与OpenBLAS等线程叠加导致配额耗尽；没有逐线程归属和单因素隔离，不说OpenBLAS单独充分致错。当前只有静态调用链和实际现场，不能宣称设置env后已恢复。原候选在L650的端点错误和环境阻塞分开；原300秒infra None、本setup900尝试、新env尝试各留记录，不重求解或替换FP。

冻结baseline源码：`system.py:33–48`没有cpu.max；`multiprocessing.py:184–197`默认num_workers配置或CPU_COUNT并spawn，`threaded.py:58–72`同样消费默认池数；`config.py:194–203`正确解析DASK_NUM_WORKERS整数2。正式`test_rearrange`两processes组没有传worker数；`-n0`只控制pytest-xdist。显式Pool(8)的`test_set_index_consistent_divisions`是slow项，无--runslow会跳过；历史3skipped不证明八池执行。DASK_NUM_WORKERS不覆盖显式参数/现有pool，八池如需另验须单独--runslow且不计105参考。

[导出资产](grader_thread_budget_exports_v1.sh)只是待部署建议。已映射OpenBLAS对应的两项核心控制是Dask池2、OpenBLAS线程1；OMP/MKL/NumExpr线程1为防守性固定，不能据此反推当前三库各占多少线程。设置位置必须在**实际评分shell环境激活、安装carry恢复之后，pytest/Python及数学库导入之前**。仅改宿主env不会自动进入Docker；只在trusted setup另一个exec export也不会跨exec延续。使用新namespace和明确新运行环境差异/SHA，正式采纳由publisher绑定环境配方及脚本身份；不能在新export后仍声称原环境/脚本身份完全未变。

最小验收保留原processes测试路径。可以先窄跑原两组或直接在完整模块中核逐项及资源，避免重复有效测试；同FP完整模块必须实际安装/测试结束、105参考齐全、原3slow skip保留，记录首失败和auto是否到达，新fresh容器pids.events.max为0、无OOM/信号/超时，并核清理。不能删进程P、改sync、提高pids限额或放大test1800/whole3600来掩盖默认并发。setup900/apply120沿当前恢复，模型宽预算不改，同FP补评不增加样本。

setup900尝试已于08:36:16UTC有界终止并收口：GPU核同容器/cgroup/UID/精确命令后对pytest发SIGTERM，manager按pids_quota_hits/signal143收为infra/None；安装完成、测试marker闭合不等于105参考完整，参考仍不完整。79份1,735,664B原件逐SHA/大小核，manager1建1删及实际清理已回执，不增加模型样本。原300s超时、setup900失败和新env恢复须分别保存。其它题9378已由GPU继续，不能把本包闭合证明当全局dispatch授权。

当前不需新增CPU整矩阵或再次求解；GPU负责人用新`dask7305-grader-thread-budget-v1` recipe和新完整测试脚本摘要，在空隙对原FP做窄环境恢复。导出资产SHA只标识新增控制文本，不代替最终完整candidate test/after-install脚本摘要；实际新完整脚本及合并`grading_scripts_digest`须在执行前核清。[原候选分析](model_probe_coder_a1_analysis_20261003.md)、[线程预算非作者核查](../../reviews/non_author_7305_grader_thread_budget_review_20261003.md)和[建议JSON](grader_thread_budget_proposal_20261003.json)保存事实/推断/待验证边界。现场原件、CPU日志及安全读取baseline成员SHA在JSON；不改旧分析、请求或正式材料。没有新的模型分或训练资格。
