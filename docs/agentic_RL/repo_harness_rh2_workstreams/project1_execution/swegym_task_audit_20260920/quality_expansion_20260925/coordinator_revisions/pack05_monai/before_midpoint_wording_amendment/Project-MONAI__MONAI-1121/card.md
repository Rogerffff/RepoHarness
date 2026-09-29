# Project-MONAI__MONAI-1121 静态短卡

公开目标是给所有网络增加TorchScript导出/加载测试；当前提示却禁止改测试，实际交付未知。版本0.3/base 5b91f937234a。历史materials-v1采用修订收集材料，已能跑完40项：noop仅AHNet脚本失败，gold全部通过；参考为1 F2P+35 P2P，Discriminator的4项实际执行却不计参考。该成功不能代表所有网络覆盖。

| 需求 | 决定性断言 | 判断 |
|---|---|---|
| 导出/保存/重载 | 五网固定配置script/save/load后allclose | 局部覆盖；仅AHNet为F2P |
| 所有网络新增测试 | DenseNet、DynUNet、SegResNet等无对应新断言 | 漏测且交付目标错位 |
| 原有前向/预训练 | 五模块旧参数化shape断言 | 历史通过，非全数值回归证明 |

八方面已核：公开目标、base与原attempt、所有新断言/helper及逐expected状态、替代解空间、两处gold及AHNet调用链、开发依赖/权重需求、历史测试恢复/源码投影、私有暴露边界。其他网络实现未全读，actor消息/工作树/解释器/权限/资产均unknown。原收集helper错误及权重/NumPy故障不能继续当作新materials-v1阻断；封存后补充原件已核实：仅在helper末尾追加注释及test_script_save.__test__=False，目标函数和断言不变；这是可信测试收集修订，不能只称依赖修复，也不能代表原始test.patch原样通过。

旧结论两处纠正：AHNet默认上采样是transpose，非trilinear；原forward已强制dropout为0，不能要求新增“非0必须不同”行为。无已证gold回归。审查者已见gold/测试/指定历史，产物仅development_diagnostic。独立reviewer已完成，补充材料的首次暴露发生在初判封存后；原初判和delta保留当时未知状态。

needs_review/static_review。唯一优先下一步：统一“所有网络新增测试”、合法交付与评分范围，先于CPU/模型探针。详细证据与运行身份见冻结analysis和old_findings_delta。

协调修订和引用见本包 revision_log；needs_review/static_review，ready_for_probe=false。
