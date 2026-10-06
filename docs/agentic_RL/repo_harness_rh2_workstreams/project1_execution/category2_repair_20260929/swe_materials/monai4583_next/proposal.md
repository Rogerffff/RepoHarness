# MONAI4583 窄材料提案

2026-09-30。仍为第2类；本轮只准备材料，未运行新增节点或评分。公开 `convert_mask_to_box` 接受通道＋2D/3D空间，每个通道对应一个框，返回该通道的真实前景分类标签；类型、dtype和设备沿已有转换。3D的各轴最小坐标拼成框角，并不保证该角是前景。这些依据来自公开API和原题，不要求gold采用某一算法。

拟在原 `tests/test_box_transform.py::TestBoxTransform` 追加普通方法 `test_sparse_3d_mask_preserves_foreground_labels_cpu`。两通道int16 mask、背景-1、前景0/7；各通道仅 `(0,1,0)` 与 `(1,0,1)` 为前景，预期框 `[[0,0,0,2,2,2],[0,0,0,2,2,2]]`、标签 `[0,7]`。NumPy/Torch CPU×默认float32/int64与显式float64/int32共四组，检查值、返回类型、dtype和CPU设备。输入只有2×2×2，不下载数据或模型；本新增方法不要求CUDA。原测试依赖CUDA可用性展开的条件保持原状，正式引用10节点范围须在CUDA不可用的CPU环境核定。

旧CPU29已执行同样稀疏3D及输出矩阵：base与2D-only框/类型/dtype/device正确、标签均[-1,-1]，gold标签[0,7]。因此**新增节点是F2P**：`proposal.extra_fail_to_pass` 只增加本普通节点，原4F2P＋5P2P不改；有效5F2P＋5P2P（10节点）。早先作者把它写成P2P的提议已由root纠正，未冻结为P2P，也不会通过跳过/条件降低断言来让base伪通过。

最小正式0/1/0计划为noop原4F2P及新F2P失败、旧5P2P通过；gold全部10通过；2D-only原9通过、只新F2P标签失败。预期testRC1/0/1，全部属于待验证预期。真实collection、完整安装/日志、候选源码和测试保护、双层清理、相关公开开发及同次原actor工件直评仍须新材料另验。旧CPU0/1/1证明原参考漏判，不证明本候选节点已执行。

当前D6仅支持追加P2P；本题不能直接投入现登记操作。需root后续决定窄新增F2P操作，覆盖登记schema/白名单、完整有效test_patch、原参考与原补丁恢复后的parent digest、新材料身份和资格失效、共用builder文件保护/基线SHA、完整有效F2P、原/新增F2P诊断分区、actor/replay同源消费及验收预期。材料任务不修改这些消费者。
