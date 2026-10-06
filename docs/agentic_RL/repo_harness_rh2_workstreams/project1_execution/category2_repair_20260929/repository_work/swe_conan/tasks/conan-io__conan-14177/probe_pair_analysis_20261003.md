# Conan14177：两模型首轮配对结论

2026-10-03。固定请求 `swe-conan14177-r11-briefv2-20261003-v1`；Coder和Qwen3.6各首次一次。[原双模型回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-conan14177-r11-briefv2-20261003-v1_pair_execution_receipt_v1.json) SHA `3ad116601fa17ecc48259eaa3b098388198871e3ed0eac76485906b43be6c17a`；题主逐臂语义与执行独审均已核收。

**两模型首次各一次均raw1，2F／11P原13完整参考全过；opt-in文件名日志及原metadata／版本／参数／异常兼容成立。** Qwen完整候选仅生产；Coder有公开新增测试与demo，受保护官方测试实际从固定base恢复。Qwen无二次pop错误，没有修改或删除旧公开测试；两模型生产字节不同，不从raw1推出任意输入等价。

Qwen首次inline因示例文件缺失而失败，后两次使用patch_ng mock，真实观察两日志及版本／字符串支路；未创建或成功应用真实磁盘补丁。Coder demo只观测首Applying便缺文件，最终两条观察声称P2仍保留，不因另一模型通过核销。可信13参考亦为受控dispatch，核真实生产路径、参数／metadata／次数与异常，非patch engine真实文件改写。Qwen三次pytest均为同13节点，不能当39独立例；Qwen两独审无新增finding、无材料阻断。

Qwen36.810秒、15请求、输入169,819／输出5,028；Coder55.135秒、输入347,827／输出5,736。Qwen全部单工具串行，验证范围较窄但陈述符合mock观察；本轮一次数字不建立总体模型排名或稳定成功率。

两臂完整题面／brief、当前材料与参考、评分及模型预算、实际actor／grader镜像与完整baseline相同。实际runtime为code7／code8，65来源成员差异（5修改、60新增），新增strict preparation policy在本题实际null；关键运输路径与现有固定材料消费有窄证据，不宣称全运行树相同。profile只改变模型服务端点，也不宣称整个profile相同。原回执和旧首臂pending字段是产生时的快照，保持原字节；当前核收汇合在[配对JSON](probe_pair_analysis_20261003.json)和[结果清单](result_manifest.json)，总账记录ACK和活动指针。

候选质量与材料质量分别记录；本题当前无材料阻断、无新CPU或普通GPU任务。按先ACK再清指针结束本次交接，覆盖优先暂缓普通追加采样。资源切片、权重未重新全量散列及容量未知不补造；未授予稳定成功率、训练／留出资格或整机销毁授权。

逐臂完整七维：[Coder](probe_coder_a1_analysis_20261003.md)、[Qwen3.6](probe_qwen36_a1_analysis_20261003.md)。
