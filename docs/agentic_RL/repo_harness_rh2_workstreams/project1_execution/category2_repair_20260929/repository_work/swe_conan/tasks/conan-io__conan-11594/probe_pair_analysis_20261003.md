# Conan11594：两模型首轮配对结论

2026-10-03。固定请求 `swe-conan11594-r12-briefv2-20261003-v1`；Coder和Qwen3.6各首次一次。[原双模型回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-conan11594-r12-briefv2-20261003-v1_pair_execution_receipt_v1.json) SHA `2ba6709ce574cd4a19879c5b9378cb26e96abd141d21f1a04486ae1fd1a8d7c6`；题主逐臂语义与执行独审均已核收。

**两模型首次各一次均raw1，2F／4P六逻辑参考全过，对应七完整节点；真实CTest Release分别成立。** Coder用“multi且Visual／Xcode”，Qwen用“multi且非Ninja”；当前已知字符串生成器目标一致，均保留配置转发，不是生产字节相同或任意输入等价。Qwen无条件substring在外部null preset会TypeError，标准toolchain生成字符串、当前公开支持null范围未知，记条件可达非阻断P2。不能以两次raw1建立所有输入兼容。

Qwen新增八公开测试实际调用helper、mock run，断言仅substring；正式评分固定另一受保护文件，不计其八例。Qwen旧helper广测4F62P7skip、错nodeid和最终49分母错误已披露；Coder的表达式自测及无关1F78P2skip亦保留。两者正确生产修法与各自验证质量分开，原失败没有被以后所选通过核销。

Qwen求解110.811秒、60模型请求、输入1,493,206／输出11,831；Coder39.538秒、22模型请求、输入283,679／输出3,416。Qwen首响应两工具批次支持批量交付，但无执行区间证明实际同时运行；CC61与HTTP60为不同计数。更多自测和耗时不能直接解释成模型稳定性或质量优势。

两臂完整题面／brief、当前材料与参考、评分及模型预算、实际actor／grader镜像与完整baseline相同。实际runtime为code7／code8，65来源成员差异（5修改、60新增），新增strict preparation policy在本题实际null；关键运输路径与现有固定材料消费有窄证据，不宣称全运行树相同。profile只改变模型服务端点，也不宣称整个profile相同。原回执和旧首臂pending字段是产生时的快照，保持原字节；当前核收汇合在[配对JSON](probe_pair_analysis_20261003.json)和[结果清单](result_manifest.json)，总账记录ACK和活动指针。

候选质量与材料质量分别记录；本题当前无材料阻断、无新CPU或普通GPU任务。按先ACK再清指针结束本次交接，覆盖优先暂缓普通追加采样。资源切片、权重未重新全量散列及容量未知不补造；未授予稳定成功率、训练／留出资格或整机销毁授权。

逐臂完整七维：[Coder](probe_coder_a1_analysis_20261003.md)、[Qwen3.6](probe_qwen36_a1_analysis_20261003.md)。
