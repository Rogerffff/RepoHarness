# MONAI2446 CPU接续

已准备，未执行。沿既有card/public_read/review与compat_v1原件继续；不重做静态审查。

公开输入见 `runs/swegym_cpu_preprobe_20260929/task_inputs/Project-MONAI__MONAI-2446/public_commands.json`。先恢复NiBabel 4.0.2到actor/grader实际解释器，运行原列表/内部shuffle/缓存同输入对照及公开旧模块。base原例预期nonzero必须由结构化结果定位。

私有补丁与历史安装脚本在同题输入的private/，数组分支禁shuffle用于v1退化探测。正式参考不改；跑noop、gold、退化候选并分别核实际投影、全部测试和清理。输入目录recovery.json记录原镜像manifest、下载/安装命令和历史配方。旧机器镜像不视为已恢复。

当前用途：问题定位；能力比较conditional（待actor），训练conditional（待退化判别）。剩余：本次执行、依赖一致性、判分与行为交叉核验、独立复核；公共GPU入口/预算另待根任务。

本次可执行恢复入口为同题 `task_inputs/Project-MONAI__MONAI-2446/buildplan.json`（具体脚本与调用参数见该文件）。`evidence_sources.json` 保存既有题卡、公开读者、复核和材料原件的路径及SHA。私有 `patch_validation.json` 已记录每个补丁在base临时副本上的真实应用前后哈希与AST检查；它不代表远端投影或功能验证，远端仍需核最终应用字节。
