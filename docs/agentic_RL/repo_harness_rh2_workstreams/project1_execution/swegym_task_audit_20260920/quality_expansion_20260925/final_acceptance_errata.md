# 最终验收与措辞勘误

依据[根最终验收](root_final_review.md)，冻结32题静态交付全部接受：12项有条件开发候选、20项质量优先处理，全部ready_for_probe=false。实际actor资格及CPU/模型运行不由静态验收代替。分类和每题唯一优先下一步不变。

已提交的reserve20_final_report.md、reserve20_final_inventory.json及封存稿保持原字节；其“后11题待根复核”是提交时状态，当前验收状态见[README](README.md)和[assignments](assignments.json)。仅追加以下两处解释：

- **MONAI1121**：“测试路径网络隔离”容易误解。应明确为：题面要求为所有支持的神经网络补测试，与预定非测试交付范围/public_hints之间的边界待对齐。这里的“网络”指神经网络；实际actor收到的消息仍未取得，不能从预定材料推断实际交付范围已验证。
- **Conan13610**：gold把裸`-v`的行为从verbose改为status，却仍保留旧帮助`-v or -vverbose`。新增的是行为与旧帮助的不一致；gold没有新增该帮助文本。仍优先明确公开CLI契约。

本次仅更新本目录当前验收元数据与导航、追加勘误；未重做审查、派发新题或执行CPU/模型，未改root_dispatch、共享交接页或总入口。
