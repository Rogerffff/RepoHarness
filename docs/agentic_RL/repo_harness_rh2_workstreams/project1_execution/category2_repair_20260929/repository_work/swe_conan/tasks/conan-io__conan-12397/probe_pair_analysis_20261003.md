# Conan12397：两模型首轮配对结论

2026-10-03。固定请求 `swe-conan12397-r12-briefv1-20261003-v1`；Coder和Qwen3.6各首次一次。[原双模型回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-conan12397-r12-briefv1-20261003-v1_pair_execution_receipt_v1.json) SHA `61651ec6bb95e53264ea5d2b05b92e877faac4ef0fa5646a66339a72f37df2a9`；题主逐臂语义与执行独审均已核收。

**两模型首次各一次均raw1，2F／2P四完整参考全部通过；生产候选内容SHA相同，配置生成修复成立。** 两者在既有非空libcxx selector分支增加cpp_link_args append，保留独立ABI compile宏、用户flags及原格式。完整候选不同：Coder有新增公开测试但正式排除；Qwen仅生产一行。当前评分真实生成完整cpp键，不是实际Clang／libc++或Apple SDK编译链接。

Qwen有三组改前／改后配置，四profile assert、Sun配置；Apple手工加载native，cross依据来自独立可信参考。功能目录setup失败、11skip、timeout参数错误、VS未装及GCC mock缺conf均保留；排除tool_meson后1P27deselected不算功能链接通过，compiler19关键词选择不算全helper。Coder的功能setup错误及过宽最终陈述也保留，不将前臂“exact scenario”声称移植到Qwen。两模型的方法质量问题不改原reward，不触发材料修订或重跑。

Qwen59.949秒、30请求、输入718,386／输出7,123；Coder30.374秒、15请求、输入271,298／输出2,816。两臂均串行单工具；当前一次耗时与token差异不用于模型总体效率／成功率排名。

两臂完整题面／brief、当前材料与参考、评分及模型预算、实际actor／grader镜像与完整baseline相同。实际runtime为code7／code8，65来源成员差异（5修改、60新增），新增strict preparation policy在本题实际null；关键运输路径与现有固定材料消费有窄证据，不宣称全运行树相同。profile只改变模型服务端点，也不宣称整个profile相同。原回执和旧首臂pending字段是产生时的快照，保持原字节；当前核收汇合在[配对JSON](probe_pair_analysis_20261003.json)和[结果清单](result_manifest.json)，总账记录ACK和活动指针。

候选质量与材料质量分别记录；本题当前无材料阻断、无新CPU或普通GPU任务。按先ACK再清指针结束本次交接，覆盖优先暂缓普通追加采样。资源切片、权重未重新全量散列及容量未知不补造；未授予稳定成功率、训练／留出资格或整机销毁授权。

逐臂完整七维：[Coder](probe_coder_a1_analysis_20261003.md)、[Qwen3.6](probe_qwen36_a1_analysis_20261003.md)。
