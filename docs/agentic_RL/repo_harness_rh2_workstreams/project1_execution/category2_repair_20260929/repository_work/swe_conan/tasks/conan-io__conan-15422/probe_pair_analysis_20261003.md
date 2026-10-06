# Conan15422：两模型首轮配对结论

2026-10-03。固定请求 `swe-conan15422-r12-briefv1-20261003-v1`；Coder和Qwen3.6各首次一次。[原双模型回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-conan15422-r12-briefv1-20261003-v1_pair_execution_receipt_v1.json) SHA `b7f007238f09e0db190b10e6d908a799cc85d090b30f4b8300c9ca400c1983aa`；题主逐臂语义与执行独审均已核收。

**两模型首次各一次执行齐，Qwen raw1／5F40P共45参考全P；Coder raw0／4F40P共44参考P、默认节点F。** Coder显式conf guard令默认jobs缺键，仍是有效P1候选遗漏，原负分不改；不是材料误拒。Qwen无条件调用公开build_jobs，默认／显式／Multi-Config路径正确，不因另一模型raw1把Coder记成功或悄悄修补其冻结候选。

Qwen完整候选还追加公开官方测试，正式投影剔除它、只用固定v2可信45参考。模型纠正自测第三次未设jobs16却期待16的错误，只改测试CLI、保持正确生产；原例逐字保留。模型实际通过默认继承preset的C++ configure／build／运行，另一自称end-to-end脚本只读jobs8 JSON。广测61P20skip8error完整根因未知，89全deselect不是通过，后续integration41P3skip不能核销八错误。正式显式2／7参考为project NONE，证明真实CMake接受configure／build presets，不证明源码编译或并行吞吐。

Qwen92.610秒、45模型请求另1token-count HTTP、46工具／CC47，输入1,761,359／输出9,008；Coder92.707秒、输入759,342／输出9,995。请求、工具、CLI回合不是同一分母，两次多工具批次无起止区间证明同时运行。原始有效成功／失败只支持本次题级诊断，不建立稳定胜率或模型排名。

两臂完整题面／brief、当前材料与参考、评分及模型预算、实际actor／grader镜像与完整baseline相同。实际runtime为code7／code8，65来源成员差异（5修改、60新增），新增strict preparation policy在本题实际null；关键运输路径与现有固定材料消费有窄证据，不宣称全运行树相同。profile只改变模型服务端点，也不宣称整个profile相同。原回执和旧首臂pending字段是产生时的快照，保持原字节；当前核收汇合在[配对JSON](probe_pair_analysis_20261003.json)和[结果清单](result_manifest.json)，总账记录ACK和活动指针。

候选质量与材料质量分别记录；本题当前无材料阻断、无新CPU或普通GPU任务。按先ACK再清指针结束本次交接，覆盖优先暂缓普通追加采样。资源切片、权重未重新全量散列及容量未知不补造；未授予稳定成功率、训练／留出资格或整机销毁授权。

逐臂完整七维：[Coder](probe_coder_a1_analysis_20261003.md)、[Qwen3.6](probe_qwen36_a1_analysis_20261003.md)。
