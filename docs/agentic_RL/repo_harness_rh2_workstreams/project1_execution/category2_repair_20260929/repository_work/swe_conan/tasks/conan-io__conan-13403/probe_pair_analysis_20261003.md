# Conan13403：两模型首轮配对结论

2026-10-03。固定请求 `swe-conan13403-r12-briefv1-20261003-v1`；Coder和Qwen3.6各首次一次。[原双模型回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-conan13403-r12-briefv1-20261003-v1_pair_execution_receipt_v1.json) SHA `da11eb09698c9ab49a97930189e5954c63d94a6041ee1171295bf8f2bea601a9`；题主逐臂语义与执行独审均已核收。

**两模型首次各一次均raw1，1F／0P唯一完整可信参考全过；所选目录、原args／单次调用／异常和cwd恢复成立。** 参考内部多分支真实chdir＋受控RunRecorder，不是真实GNU构建。两生产实现公开语义相同、文档和计算顺序不同，完整候选不同：Coder附加非官方脚本，Qwen追加48行官方公开单测；Qwen正式投影排除官方单测，固定可信v4测试独立恢复。

Qwen真正调用新helper，用mock chdir和ConanFileMock记录默认／相对／args；三个新增测试失败逐步修正，生产未回退、旧例原字节保留。最后79P为78旧例＋1新例，tail完整footer支持数字，但管道不保留pytest退出码；没有真实GNUautoreconf工程、自测绝对／异常／cwd恢复的证据。Coder脚本只构造对象不调用helper、真实GNU功能两失败与source相对误说build相对的两P2保持，不能把Qwen更好的调用自测移植到Coder或更改原reward。

Qwen57.368秒、26模型请求／CC27、26工具，输入408,214／输出8,058；Coder64.881秒、23请求。Qwen首批两Bash是批量交付，无执行起止证明重叠。两次raw1及本轮耗时差不建立稳定胜率／模型排名；没有当前材料阻断，无需新CPU／GPU或普通采样。

两臂完整题面／brief、当前材料与参考、评分及模型预算、实际actor／grader镜像与完整baseline相同。两臂实际input／grading runtime均code8，所登记source manifest逐字相同；Coder模型运输仍为原固定独立运输配置，不宣称整个模型transport／profile相同。原回执和旧首臂pending字段是产生时的快照，保持原字节；当前核收汇合在[配对JSON](probe_pair_analysis_20261003.json)和[结果清单](result_manifest.json)，总账记录ACK和活动指针。

候选质量与材料质量分别记录；本题当前无材料阻断、无新CPU或普通GPU任务。按先ACK再清指针结束本次交接，覆盖优先暂缓普通追加采样。资源切片、权重未重新全量散列及容量未知不补造；未授予稳定成功率、训练／留出资格或整机销毁授权。

逐臂完整七维：[Coder](probe_coder_a1_analysis_20261003.md)、[Qwen3.6](probe_qwen36_a1_analysis_20261003.md)。
