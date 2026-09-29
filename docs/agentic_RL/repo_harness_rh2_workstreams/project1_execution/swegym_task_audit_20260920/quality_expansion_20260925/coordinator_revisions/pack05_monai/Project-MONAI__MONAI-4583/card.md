# Project-MONAI__MONAI-4583 静态短卡

版本0.9/base 9c4710199b80。题面反对角前景的框正确、标签误读背景。gold在2D/3D从同一真实前景坐标取类，保留框和转换路径；历史baseline01为noop4失败5通过、gold9通过。静态候选成立，actor资格未验。

| 需求 | 决定性断言 | 判断 |
|---|---|---|
| 单/双通道2D类别 | 四项反对角fixture检查框、标签、类型/device | 直接对应公开目标 |
| 3D稀疏前景类别 | 旧3D仅矩形往返 | 缺口：只修2D也能过现有选中用例 |
| 输出dtype/跨设备 | helper只查容器类型/device与数值 | 精确dtype不足；CUDA改变相同ID参数类型 |

八方面已核公开需求、版本/投影、全部新旧选中断言及helper、非gold取前景实现、gold/MaskToBox及字典平移调用链、CPU内存数组需求、历史恢复、答案暴露。未证gold新回归；旧称包装未覆盖需纠正，包装已有矩形用例。CUDA分支会把NumPy参数替换为Tensor而保持编号相同，当前CPU对账成立不代表跨profile同一性质。

旧“改tests/utils可伪过”是具体待核风险：当前完整投影/恢复/权限未验证，不沿用旧排除建议，additional_exclusions=[]。actual image ID为null；actor消息、初态、导入和权限unknown。审查者已见私有/历史，限development_diagnostic；reviewer未读，意见待协调者接入。

needs_review/static_review。唯一优先下一步：任务二在实际actor条件跑公开2D+3D稀疏API小对照，记录初态、导入、RC、框/标签/dtype/device，并在私有隔离条件核gold同命令；不跑全仓/GPU模型。
