# 5662：原Qwen候选在权限修复后的有效评分

2026-10-03。题主已核收[独立实际复验报告](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/pyd5662_original_fp_regrade_v2_non_author_review_v1.md)、27件闭合原件及外层宿主回执，见[32件绑定题主读回](../coordination_20261003/5662_original_fp_regrade_v2_owner_readback_v1.json)。**原完整FrozenPatch在新grader上安装RC0、测试RC0，2个F2P和127个P2P全部通过，raw reward=1。** 没有重新求解或增加模型样本；原Qwen尝试的安装RC1、raw1和全部原件保留。

本轮只改变grader的公开wheel权限层，FP、baseline、材料、预算和候选均保持。完整FP仍包含`pydantic/main.py`单行一般委托修复和Hypothesis Unicode缓存两项。FP摘要为`f1423fd9c9d4e6f276a1f961a8150977bda6de0a17f1b565810b59c52740ab13`；本轮没有把缓存从评分运输中删掉。正式参考分母为129，另有非参考节点及skip，不能用完整pytest摘要代替参考分母。

| 诊断方面 | 当前结论与范围 |
| --- | --- |
| 候选语义 | 复用[原完整轨迹和候选初审](5662_qwen36_a1_preliminary.md)：非BaseModel分支返回`NotImplemented`，一般比较对象收到原模型，原模型之间的比较分支不变；当前范围未见具体回归。 |
| 环境可操作性 | 新grader实际安装`pydantic-2.0a3`成功，安装/测试RC均0。关闭原wheel不可读造成的安装阻塞；没有新增actor或真实模型运行。 |
| 评分一致性 | 同一完整FP、baseline及修订参考运输，129参考无失败、缺席或跳过，raw1。原安装RC1时的raw1仍是历史执行事实。 |
| 公开问题与求解依据 | 原题面已给出`NotImplemented`修法；本臂正确理解并验证公开提示，不能称无提示独立发现。私有修订未交给solver。 |
| 效率 | 仍只有原17请求、16工具调用、累计127988上报token和30.606秒入口solve记录；新173.027秒是原FP独立评分耗时，不能计成新模型求解或与嵌套API时间相加。 |
| 并行行为 | 原5662轨迹工具串行，无实际子agent调用。共用执行层在6283接受过同消息双工具，但不能据此改称5662本臂并行。 |
| 身份、运输与清理 | 原完整baseline/FP核查保持；模型来源采用已核有限运营谱系，不能回写为当时逐job checkpoint快照。manager创建1/删除1且无open/supply/failure，宿主systemd成功退出并只剩原两服务。资源采样没有捕获grader，实际post-close网络原始输出缺席；保留未知，report峰值534.129MiB另列。 |

该Qwen候选现在具有权限修复后有效的正式参考评分；候选语义结论仍限定于已审范围。原请求继续claimed，Coder臂和重复样本尚无题主核收结果，不能比较模型、估计稳定成功率或授予训练资格。无需因这次评分补验机械重跑已完成CPU矩阵。
