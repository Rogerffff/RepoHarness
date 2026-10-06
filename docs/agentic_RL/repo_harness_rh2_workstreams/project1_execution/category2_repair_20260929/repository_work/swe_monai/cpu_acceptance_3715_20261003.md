# MONAI3715：修订后 CPU 结果

2026-10-03。题主为 `SWE | MONAI 题目修订`。**五行正式评分及非作者原件核查已完成，结果为 0／1／0／0／1；可提交探索性模型探针。** [非作者最终报告](reviews/non_author_cpu_review_20261003.md)未发现题级阻断。当前提交／执行状态以 [准备入口](preparation.md)和 [preparation.json](preparation.json)为准。

## 修订解决什么

原测试只把 `test_content` 的 mode 设为 `"eval"`，不能充分拒绝只支持 eval 字符串或强制使用 eval 的修法。本轮保留该原断言和 `test_empty_data`，在同一文件增加一个 F2P，实际调用 `SupervisedEvaluator.run()`，检查字符串／枚举的 train 与 eval、真实 forward 的模型／梯度状态、预测值、训练时输入梯度及退出后的状态恢复。新节点包含 16 个小张量 CPU 子情形，不比较上下文函数身份，不要求唯一源码写法。

有效补丁为 [effective_test.patch](materials/3715/effective_test.patch)，SHA256 `1e38b2d6a5dcfa2e2de5622c4db601a446da4e68ef1bd642d9c8100c3415565e`。正式参考为 **2 F2P＋1 P2P**；题面、已有公开提示、安装来源、文件级测试命令保持。静态材料审查见 [非作者材料报告](reviews/non_author_material_review_20261003.md)。

## 实际结果

固定版本为 release5 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest SHA256 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`，宿主解释器为 `runtime_cpu_v2`。五行使用同一新 prepared 和原 vendor 命令 `pytest -rA  tests/test_prepare_batch_default.py`。

| 候选 | 原 F2P | 新 F2P | 原 P2P | reward | 日志中的实际原因 |
| --- | --- | --- | --- | --- | --- |
| 原始代码 | 失败 | 失败 | 通过 | 0 | 分别触发 `unsupported mode: eval` 和 `unsupported mode: train`。 |
| gold | 通过 | 通过 | 通过 | 1 | 三节点全部通过。 |
| 只修 eval 字符串 | 通过 | 失败 | 通过 | 0 | 新节点运行 train 字符串时仍触发 `unsupported mode`。 |
| 强制使用 eval | 通过 | 失败 | 通过 | 0 | 真实 forward 记录 `(False, False)`，train 要求 `(True, True)`。 |
| 另一局部规范化实现 | 通过 | 通过 | 通过 | 1 | 三节点全部通过；允许该不同源码写法。 |

五行均实际解析三个参考，无 missing／skip；安装段均 RC0，测试段为 **1／0／1／1／0**，候选执行与 runner 均 RC0。失败来自目标行为，未用导入或准备异常代替负对照。四个修订候选的 FrozenPatch 仅投影 `monai/engines/evaluator.py`，内容 SHA 与冻结对照一致；原始候选为空。完整评分、候选及 manager 清理均完成，外层作业 `finished / RC0`。

[作者原件读回](checks/monai3715_formal_cpu_c_20261003.json)绑定 55 份最终原件、逐参考结果、候选源码、命令、分段退出、两层清理及外层状态。正式作业为 `monai-3715-formal-20261003-e9716177`，原件在忽略的 `runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/` 下。记录未回写历史分数，也未把旧 FrozenPatch 重绑到新版本。

## 公开开发和身份范围

公开 actor 使用真实 CC 桩、UID54321、testbed Python 和 `/testbed` 源码，共六条命令。枚举 train／eval 的 forward、预测和梯度符合公开 API；字符串 train／eval 复现原报错；原公开模块 **2 项通过**。身份、实际 CPU／内存、完整轨迹和清理见 [actor 核查](checks/monai3715_actor_cpu_c_20261003.json)、[公开交付范围核查](checks/monai3715_public_delivery_cpu_c_20261003.json)及[外层退出核查](checks/monai3715_outer_exit_cpu_c_20261003.json)。

该 actor 首条实际用户消息为通用 `Devcheck run` 指令，未交付原题面或 `public_hints`，因此只证明公开命令的执行能力。原公开内容保持由新 prepared 与来源逐字段相同证明；GPU 探针仍需核实际首请求中的原题面与已有提示。两个通用 marker 的 false 保持原值，不据此宣称开发失败或平台保护全验收。

CPU 准备实际镜像 ID 为 `sha256:6cbdf6b5eefbe27e97db5839aa8586584cc57f20759fb6c408690fddc8202e38`，来源 manifest 为 `sha256:503ca39274e12c0aa0d06d0e77ad4f41628516a7b175feb4a5c10f940e2d1ab8`。五行原 vendor ledger 的 `image_id_actual` 均为 null，保持原值；冻结 manager 启动后按**运行容器的实际 Image ID**查 RepoDigests 验证来源 manifest，不能用启动前 ID 代填每行字段。

正式行记录 2 CPU／4 GiB／PID512 的 profile，未额外保存每个 grader 的实际 HostConfig；`resource_facts` 为 null，不把报告内的内存数值冒称独立测量峰值。公开 actor 和来源探针的实际 inspect 证据另行绑定。CPU reset／准备预算为 900 秒，测试仍为 1800 秒，整次评分 CLI 截止为 3600 秒；不改变评分语义或模型预算。

## 当前用途与下一步

本轮用于修订质量和基座难度调查，不授予训练或留出资格。非作者核查已通过，本线程单题提交统一执行者，由其钉 GPU 实际镜像、代码、原公开输入与 `probe-wide-v1` 预算并串行运行；结果仍回本线程审计实际候选及评分，必要修复继续由本线程负责。
