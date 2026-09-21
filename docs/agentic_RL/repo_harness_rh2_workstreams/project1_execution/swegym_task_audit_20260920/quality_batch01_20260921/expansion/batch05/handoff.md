# B5后备材料交接（不启动角色）

状态：只准备；根任务先完成B4验收，再按时间和额度决定是否启用。冻结manifest在同目录`batch_manifest.json`，不得把本文件当派发授权。

固定两题：`python__mypy-11707`、`getmoto__moto-5406`。材料根为`runs/swegym_quality_batch05_20260921_v1/`；每题public/private/history路径及本批results输出路径均在manifest。若启用，公开阅读只给本题public目录；私有环境入口和历史引用按既定分阶段规则使用。不要交叉读取别题材料，不覆写前批输出。

材料验核见`material_check.json`；原运行入口见`environment_replay_inventory.json`和`environment_replay_notes.md`。mypy沿install_wave1派生镜像，Moto沿原baseline；二者都无recipe/materials/bindings覆写。真实actor条件和题目质量尚未审查。当前没有dispatch、角色分配或审查结论。
