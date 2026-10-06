# mypy10174：原 Qwen 候选新 GPU 镜像重评分验收

2026-10-03。作业 `gpu1003-mypy10174-qwen36-originalfp-80418df-regrade-a1` 在08:52:21–08:53:57 UTC执行，使用 code_v8 与实际镜像 `sha256:80418df01e0544855bbba9d858a53e45089320ed650bc4b1eb05e91bbf33880f`。**原候选的实际安装及四项正式参考重评分已验收，无新增题面、评分或安装阻断。** 已回告 GPU 线程接续原请求缺失的 Coder 首轮；请求继续 claimed，不确认部分结果为整项 returned。

题主核228项检查、79件闭包的SHA/大小和22个固定执行输入，并合并两位非作者窄核。原 FP 共51项保持，评分投影继续保留49个缓存文件和 `mypy/meet.py` 共50项，原候选测试修改仍排除。完整1472条基线重建逐内容/模式相符，50次 delta 写入实际退出0；没有净化缓存、换成作者补丁或重新求解。

完整正式安装段执行原三条 pip 命令，editable 真实完成构建和安装，ERR trap无失败；候选 exec、安装末段和测试均退出0。每条成功 pip 没有独立数值退出码，不冒称原件记录了三条RC0。四项正式参考真实执行并通过，1个F2P、3个P2P，reward1，无缺席、跳过或额外解析。不是9423项全套回归通过。

manager创建/移除1/1，无open/supply/清理失败；外层按本job标签核无容器，前后仅原有两个共享Coder服务和默认网络。systemd unit已收集，not-found默认RC0不作为退出证明；采用实际unit journal的启动与 `Deactivated successfully`，与done/report/完整exec相符。journal/done证明重评分流程结束，四项PASS另由原eval/exec证明；本次没有actor或session生命周期。

code_v4与code_v8整树和manager不同，不以“字节未变”说明等价。实际本题材料、生成脚本、测试命令、预算及三分区四参考相符；执行报告的manager范围已[另存更正](../reviews/non_author_10174_new_GPU_regrade_execution_scope_correction_20261003.json)。反证报告的“四分区”实际应为“三分区四参考”；input_check是未评分状态，新旧diagnostics才具有相同的已解析结果对象，题主已区分并核实。

本次没有新模型调用，Qwen仍只有一个首轮样本。旧32f镜像上的raw1/安装RC1、CPU r16预热及独立Python来源探针范围、原FP旧镜像来源身份均保持，不回填成此次GPU结果。目标模块pytest进程内加载SHA没有新增；`resource_facts=null`、`env_qualification=absent`和包版本观测`?`保留。本次只关闭指定新镜像的安装/四参考增量，不授予训练、留出或完整隔离资格；无需CPU矩阵、Qwen重解/重采/再次重评。

证据：[题主固定验收JSON](new_GPU_regrade_acceptance_20261003.json)，SHA `5689bf5a295b6d8adbb578664d38453dbe48d16914517c8910e9e24b62ffe282`；[原件回读](new_GPU_regrade_readback_20261003.json)；[执行链窄核](../reviews/non_author_10174_new_GPU_regrade_execution_20261003.md)及[反证窄核](../reviews/non_author_10174_new_GPU_regrade_falsifier_20261003.md)。两角色已见gold/private，非fresh，均只读本地，没有重复执行模型或项目测试。原审查和回执不修改；新具体失败或材料变化才按影响接续。
