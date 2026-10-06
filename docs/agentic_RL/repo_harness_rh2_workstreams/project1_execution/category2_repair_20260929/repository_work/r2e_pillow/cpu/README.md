# Pillow 题级 CPU 开发对照

2026-10-03。此目录是宿主上的确定性验收输入，不整体交付给 fresh solver。正式源码、材料和派生镜像仍绑定共用维护者确认的不可变 release。

`2d01_actor_base_commands.json` 保持已审公开兼容命令，补实际 CC Bash 工具中的解释器、UID 与激活文件不可写标记。`2d01_actor_positive_commands.json` 使用同一命令，只将两个目标原例的预期退出改为 0。两个清单中的兼容 heredoc 与 `../public/tiff_pytest8_compat.py` 逐字相同。

`2d01_actor_positive_control.py` 是该题私有正确解开发对照的薄装配：核固定 runner 与补丁摘要，只允许 `src/PIL/TiffImagePlugin.py`；沿原 R2E actor 入口完成启动、隔离与解释器检查，在正式 driver 前以 agent 身份应用源码补丁。实际 UID 必须为 54321。原入口继续负责真实 CC 桩命令、逐命令结果、终止和清理。它不修改共享代码、测试或评分材料，也不把私有候选加入公开命令。

公开兼容方法与[正对照装配](../reviews/non_author_2d01_positive_wrapper_review_20261003.md)均已通过非作者静态窄核；真实 base 和正确解 actor 已完成，九条命令与 13 项入口检查全部通过，公开测试各 82 通过、2 跳过。正确解应用观测 UID 54321。完整证据见[CPU 验收记录](../cpu_2d01_acceptance_v1.json)。

`rgba_gif_actor_identity_commands.json` 是另外两题换宿主的三条公开检查；正式 R2E 入口注入预检后共四条。`3a61`、`a682` 均已完成真实 CC Bash、四个工具返回、五个桩请求与 13 项入口检查，解释器、UID、激活文件不可写、PIL 源码及 C 扩展导入均有原件支撑。按未变范围复用已有公开开发验收。完整结果见[3a61 CPU 记录](../cpu_3a61_acceptance_v1.json)、[a682 CPU 记录](../cpu_a682_acceptance_v1.json)和[非作者原件核查](../reviews/non_author_cpu_results_20261003.md)。

首个 runtime v1 actor 因宿主缺 torch 失败，旧证据保留；成功复验使用已开放 runtime_cpu_v2。所有作业固定 CPU-b，端口为 gateway 18192 / stub 18193，actor 使用串行；每个矩阵内部逐候选串行。两个既有矩阵已自然结束，后续其他仓有等待时本包最多占一个 CPU 槽，prepare 也计入。正式矩阵脚本、输入绑定和运行原件保存于本包忽略 evidence 目录，不属于公开求解说明。
