# Moto5406 双模型首次覆盖收口

2026-10-03。当前请求 `swe-moto5406-east1-r5-20261003-v1` 的两模型首次运行与题主语义／轨迹分析已完成。两者原分均1、安装／测试rc0、28参考完整；源码均保存实际region并用于Table ARN和StreamRecord，未发现本题需继续修订的语义或评分缺陷。结论限于这两个实际样本，不授稳定能力、训练、留出集或typed actor资格；当前覆盖优先，不启动普通追加采样。

| 项目 | Qwen3.6-35B-A3B | Qwen3-Coder-30B-A3B-Instruct |
| --- | --- | --- |
| 实际job | gpu1003-moto5406-qwen36-a1 | gpu1003-moto5406-coder-a1 |
| 冻结runtime | code4 | code7 |
| 原评分 | 1，1F／27P全过 | 1，1F／27P全过 |
| solver墙钟 | 67.969秒 | 58.800秒 |
| CC回合／生成 | 25／23（另2count_tokens） | 19／19 |
| 工具调用 | 24 | 18 |
| 累计输入／输出token | 896259／6266 | 493835／5192 |
| 最大单次输入token | 51845 | 36268 |
| 正式安装／测试段 | 2.621／2.739秒 | 2.572／2.942秒 |
| 完整FP entry数 | 1个源码 | 同机制源码＋1个说明文件 |

同一原owner request SHA、材料、实际image、完整baseline、公开prompt及中性brief、28参考、全部模型和评分预算相等；四项关键运输代码同字节。完整runtime code4与code7不同，八项共享成员发生变化，不能称整棵代码同版或用这些单样本推出一般模型排名。累计输入不是context峰值，model token不能与保护／评分时长混为一项效率指标。

Qwen有两次多工具batch且结果逆序，只支持执行链具备batch，缺逐工具时刻不能量化重叠；Coder全部单工具串行。二者都用全文Read扩大上下文，都有一次误选验证路径／节点；模型报告里的广泛“全部测试／无回归”主张以实际验证范围约束。Coder没有对最后StreamRecord改动直接检查事件awsRegion；静态修法与原region数据流正确，实际28参考过，不能将ARN自测扩成所有stream行为覆盖。详细证据分别见[Qwen首轮分析](qwen_a1_analysis_20261003.md)、[Coder首轮分析](coder_a1_analysis_20261003.md)。旧Qwen分析保留当时Coder未覆盖的历史状态，当前入口以本报告与results为准。

Qwen旧作业的engine归属为事后固定下载／只读挂载／服务日志操作链推断，没有旧时点独立CID capture；原checkpoint flags、HTTP revision/checksum null等保持。Coder有启动前现场capture与实际配置绑定，但没有重复所有权重hash或GPU内存hash。两者都不是完整硬件资源审计，有限采样峰值不是正式测试最低内存。

GPU总回执 `runs/ordinary_gpu_probe_20261002/receipts/swe-moto5406-east1-r5-20261003-v1_two_model_v1.json`，SHA `3a0030ba9c4a228869ffc91792e89be85cd182aadaf2596b0392b6a17ebee113`。实际总账returned与通知已核；固定回执中的not_sent=true／request_returned=false是生成时字段，保留原字节，不据此否定实际后续回传，也不回填原件。语义结论独立于rawscore，无奖励覆盖。本题首次覆盖可收口，后续资源与其它五题各自进度不能据此标为完成。
