# 返回像素修订提案

2026-09-30；建议，不是已实施或新 CPU 验证。范围是已明确公开的 Dataset+dict+Compose(lazy=True) 返回变换图像，使用已有确定性 CPU 输入，不扩大随机NIfTI/RandAffine完整原例或GPU要求。

公开题面同时写 `out_1=xform(d)` 和 `out_2=Dataset([d], transform=xform)[0]`。公开 `monai/data/dataset.py` 的取样接口说明应用 transform，`_transform` 明确返回 `apply_transform` 的结果；Compose公开True/False/None分别为启用lazy、强制逐步执行、继承子变换属性。Flipd公开支持按spatial_axis翻转及lazy执行。由这些接口要求实际返回转换后的图，不只让日志或操作记录正确。base及公开源码固定副本见材料manifest的source项。

已有独立复核及原CPU18六行输出为 direct/Dataset×True/False/None。基准图像是float32 CPU的0…11，shape1×3×4；双轴翻转的具体期望为 `[[[11,10,9,8],[7,6,5,4],[3,2,1,0]]]`。

| 候选 | 六行政策 | 六行返回像素 | 已有旧56测 | 原正式63测 |
| --- | --- | --- | --- | --- |
| base | Dataset True/None被False覆盖 | 全对 | 56通过 | 原4F2P失败、59P2P通过，reward0 |
| gold | 全对 | 全对 | 56通过 | 63通过，reward1 |
| discard dict output | 全对 | Dataset True给0…11原图，其余5行对 | 56通过 | 63通过，reward1 |

以上是已有实际结果，不是新节点结果。gold和discard的Dataset True均wrapped真实resample调用1次，说明计数不能决定返回图正确；次数也仅覆盖被wrap函数，不能写成全后端重采样规范。新普通测试不使用wrapper或mock、不约束调用数。`historical_behavior_summary.json`逐行保留原值/政策/观测计数及原输出SHA；完整原输出和正式43件均冻结供复用。

新增节点只有一个：`tests/test_dataset.py::TestDataset::test_dataset_lazy_dict_returns_transformed_pixels_cpu`。函数局部导入Torch/MetaTensor/Flipd，使已有模块级AST不变；构造CPU图像和两次lazy Flipd，Compose lazy=True，通过真实Dataset读取字典图像，对实际返回数据断言shape、CPU以及具体像素。期望是图像翻转的直接数学结果，未取gold源码算法。容差atol1e-6/rtol0沿已有同输入矩阵，错误原图最大差11，不能混淆为数值容差。

该节点的归属是P2P：base同路径像素已有正结果，gold也正确，discard漏修失败。若加入政策断言，base因政策不符会失败而成为F2P；本片不这样重复原4个政策F2P，也不改变原政策要求。新的像素守卫与原4F2P合起来要求政策和输出都满足公开契约。旧4F2P/59P2P原顺序逐字保留，追加1P2P，候选64参考。正式预期：noop原4F2P失败、新P2P和原59P2P通过；gold全部通过；discard原4F2P/59P2P通过，只新P2P失败，奖励0/1/0、testRC1/0/1。新方法未运行/collection，以上须正式三方复验。

原 `test_dataset_lazy_on_call` 的无效体、日志测试和Compose hunk保持，不顺手修旧测试。本包原patch=`base→原两文件`，extra=`原patch后Dataset→新增方法`，effective=`base→完整两文件`；静态证明两种应用链同字节，去新增方法AST完全一致，Compose原patch后字节也一致。正常node而非私有shell检查必须进入正式参考。

准备成本是新题注册及两文件受信支持；当前consumer不能直接加载。本题保持第2类，root另给隔离实施/CPU授权。材料不声明新prepared/qualification可复用，不声明比较、训练或留出资格。
