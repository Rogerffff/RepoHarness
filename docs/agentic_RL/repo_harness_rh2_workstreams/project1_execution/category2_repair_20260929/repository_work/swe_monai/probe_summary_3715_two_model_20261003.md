# MONAI3715：双模型首次诊断

2026-10-03。**两个模型各一次，均得到原评分1，实际补丁修复了字符串模式未参与正确分支选择的问题，正式2 F2P＋1 P2P全部通过。题目修订、CPU对照、双模型首次探针及题主分析已完成；非作者候选语义核查支持两个修法，没有发现需追加题面、环境或评分修复的具体缺陷。** 这是首次诊断收口，不是稳定成功率或训练资格。

| 模型首次尝试 | 实际修法与结果 | 验证过程与成本 |
| --- | --- | --- |
| Qwen3.6 | `gpu1003-monai3715-qwen36-a1`；code_v4；两处条件改比较转换后的`self.mode`。原评分1，3参考通过。 | 19轮、18工具；entry求解61.005秒。字符串／枚举构造与旧ensemble测试通过，但多次误用Saliency API，捕获失败后错误宣称通过。 |
| Qwen3-Coder-30B-A3B-Instruct | `gpu1003-monai3715-coder-a1`；code_v7；用局部`mode_enum`比较转换结果。原评分1，3参考通过。 | 5轮、4工具（3 Read＋1 Edit）；entry求解11.687秒。没有失败复现、修后测试或Saliency前向；最终正确性宣称是静态判断。 |

两种解法都保留原`eval_mode`／`train_mode`、枚举兼容、非法输入拒绝和上下文恢复。正式新增节点实测4种模式×2种初始training状态×2种初始grad状态的16组合，检查非空forward、数值、梯度及状态恢复；两臂均完整通过。模型自测与受信评分证据分别保存：有评分1不代表模型验证过程充分，没有自测也不能推为环境不可测试。

该题提供了明确的局部定位成功证据，亦暴露不同验证弱项：Qwen反复猜测API且未诚实收束验证结论，Coder直接编辑后结束。它们可作为行为诊断输入；各一次成功不能估计可靠性、证明训练饱和或决定剔除该题。暂不触发新CPU复验或普通追加模型采样，先扩大全批已有材料的首次覆盖，符合[现行覆盖优先规则](../../overnight_watch_20261003.md)。

比较范围：两次使用相同固定请求SHA `6a348f0a92f54a054eacf3e51d22cb14f769fb8d7d13f11d279a1889c0b14d67`、评分材料、实际镜像、完整baseline、公开prompt、3参考、评分脚本摘要与宽预算。4个关键运输文件同字节，但code_v4／code_v7的8个共享consumer／grader文件不同，不能称完整runtime相同。没有重跑旧模型或重绑FP；原评分和原件保持。

评分耗时分别539.19／554.02秒，主要记录为受信准备阶段，不能算模型推理时间。Coder资源审查只有有限42个样本，grader生命周期4GiB高水位不证明测试最低内存或全程无OOM；root chown观察也不是完整准备耗时归因。普通探针`env_qualification=absent`和正式训练actor未接入的边界保持。

证据入口：

- [Qwen题主分析](probe_analysis_3715_qwen36_a1_20261003.md)、[机器核查](checks/monai3715_qwen36_a1_owner_analysis_20261003.json)、[非作者语义核查](reviews/non_author_monai3715_qwen36_semantics_20261003.md)。单臂报告内“第二模型尚待”是当时状态，原件不改。
- [Coder题主分析](probe_analysis_3715_coder_a1_20261003.md)、[16份原件及逐调用核查](checks/monai3715_coder_a1_owner_analysis_20261003.json)、[非作者语义窄核](reviews/non_author_monai3715_coder_semantics_20261003.md)。本次没有新运行实验。
- GPU总回执：`runs/ordinary_gpu_probe_20261002/receipts/swe-monai3715-string-modes-r5-20261003-v1_two_model_v1.json`，SHA `36740efe35e1d98af4c9efcc90e00e3c9582194feb3795d875f59ae94070e832`。其发送前冻结的行政标记保持，实际回传以总账returned、notice和题主ack为准。

2446、6975的GPU兼容准备及两个模型结果仍未完成，MONAI整个工作包不据本题收口标为完成。5932、4583继续由原GPU负责人处理。
