# MONAI5932 CPU接续

已准备，未执行。公开输入为同题task_inputs/public_commands.json；先核actor来源，再分别运行短在前（base预期SyntaxError）和长在前（base应4），以及公开解析器窄模块。

私有quality_plan.json要求noop/gold/反转顺序候选正式RH2评分及两顺序行为对照；反转顺序是既有题卡明确的漏测候选，不混入公开输入。恢复使用该题原manifest与baseline配方，不照搬2446的NiBabel pin。historical_refs绑定原ledger第3/4行；历史MetricsReloaded准备diff不能当干净base。

当前用途：问题定位；能力比较conditional（待actor），训练conditional（待退化判别）。剩余：执行、完整失败/skip解释、正式评分、独立复核；GPU公共前置仍归根任务。

本次可执行恢复入口为同题 `task_inputs/Project-MONAI__MONAI-5932/buildplan.json`（具体脚本与调用参数见该文件）。`evidence_sources.json` 保存既有题卡、公开读者、复核和材料原件的路径及SHA。私有 `patch_validation.json` 已记录每个补丁在base临时副本上的真实应用前后哈希与AST检查；它不代表远端投影或功能验证，远端仍需核最终应用字节。
