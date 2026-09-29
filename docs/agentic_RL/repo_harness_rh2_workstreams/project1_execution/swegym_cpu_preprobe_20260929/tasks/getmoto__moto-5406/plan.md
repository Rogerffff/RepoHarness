# getmoto__moto-5406 CPU接续

已准备，未执行。原baseline01 make init，无install_wave1或derived覆写；既有历史原27项分差有效范围保留。私有恒East2补丁必须实际RH2评分，并与East1公开行为/已有East1测试对照。最小公开复现统一题面表名，观察Create/Describe及跨地区隔离。完整TableClass/Stream/SSE组合尚未核，不偷换为已验。

公开输入在本题task_inputs/public_commands.json；私有gold/退化输入独立存放。当前用途仅问题定位；能力比较、训练均待决定性质量对照和actor条件，不能因旧gold通过升格。

剩余：冷恢复、真实actor公开执行与原例缺项、正负及退化正式评分、投影/完整测试/清理、失败归因与独立复核。共同GPU入口/预算待根任务；没有新增正式题面/测试/评分修订。

本次可执行恢复入口为同题 `task_inputs/getmoto__moto-5406/buildplan.json`（具体脚本与调用参数见该文件）。`evidence_sources.json` 保存既有题卡、公开读者、复核和材料原件的路径及SHA。私有 `patch_validation.json` 已记录每个补丁在base临时副本上的真实应用前后哈希与AST检查；它不代表远端投影或功能验证，远端仍需核最终应用字节。
