# Project-MONAI__MONAI-3566 静态短卡

公开请求是在现有LoadImage目录调用中返回DICOM标签；base 9417ff217843、版本0.8。隐藏测试增加未公开series_meta=True，gold默认False，所以原例仍走旧路径。这个接口/默认行为错位尚未解决。

| 需求 | 决定性断言 | 判断 |
|---|---|---|
| 原公开默认调用含可用标签 | 测试只用series_meta=True | 冲突/缺失 |
| 标签来自样本 | 仅0008|103e精确字符串 | 单键覆盖，可漏掉其他标签 |
| 体积几何/旧reader | DICOM affine/shape、ITK/Nibabel等P2P | 历史通过；新选项分支几何未直接断言 |

八方面已读公开目标、base/投影、全部新断言及20项P2P实现、非gold默认保留方案、gold与LoadImage/LoadImaged调用链、ITK/本地DICOM/临时目录需求、可信恢复、私有暴露。新itk_v2固定组件5.2.1.post1/NumPy1.23.5，noop1失败25通过，gold26通过；旧5项ITK错误已不适用于此运行。noop失败发生在新参数读取阶段，不能冒充原默认调用缺标签的实测。TimedCall的5项无关且有spawn计时风险，但未证并发翻车，不自动删除。

首片代表策略的TODO不证明错误；公开也未要求唯一归并方法。actor消息/工作树/权限/导入/资产仍unknown；旧gold FULL不构成当前资格。审查者已见私有答案/测试/指定历史，仅development_diagnostic；reviewer未读，意见待协调者。

needs_review/static_review。唯一优先下一步：先统一公开默认行为与series_meta接口/验收，再决定验证范围；不先做模型猜参数实验。详表与原运行逐项对账见analysis，历史纠正见delta。
