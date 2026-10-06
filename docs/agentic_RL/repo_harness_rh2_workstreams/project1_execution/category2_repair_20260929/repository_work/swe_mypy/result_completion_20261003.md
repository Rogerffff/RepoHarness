# mypy结果完整性与资源依赖

2026-10-03 21:33更新（Asia/Singapore）。依据[当前覆盖优先规则](../../overnight_watch_20261003.md)，入口为[preparation.md](preparation.md)。固定旧原件、请求和审查不回写，当前状态在本页和总账更新。

## 当前完成与剩余事项

15184正式材料`mypy15184-nested-nominal-types-v2`已完成CPU四候选0/1/0/0及两模型各一次完整首轮。Qwen3.6、Qwen3-Coder原raw1、正式3F/2P五参考全通过，实际公开交付、候选/材料、安装、执行及双层清理已核，源码语义与题意相符。题主结合两臂原件和新增非作者审查作[配对验收](python__mypy-15184/two_model_first_round_acceptance_20261003.md)。总账已returned/ack，活动请求清空、phase=closeout；本题无新增CPU或GPU作业。

10174 R6矩阵0/1/0保持；原Qwen首臂旧GPU raw1/四参考、清理和editable安装RC1均保留。原候选CPU r16窄重评分已[验收](python__mypy-10174/gpu_install_revalidation_acceptance_20261003.json)：完整1472基线/50路径投影，49cache保留，三安装RC0、四参考通过、reward1，清理正常。12次槽忙及r3/r8/r15编排失败不计候选成绩，r13误通知更正保留。[GPU权限/Q12来源补证](python__mypy-10174/gpu_identity_and_wheel_supplement_20261003.md)已核80418df权限层、1663项清单不变、双UID读取及87次请求对应。原候选在80418df/code8新GPU的实际完整安装和四参考重评分现已[验收](python__mypy-10174/new_GPU_regrade_acceptance_20261003.md)，79原件、1472基线、原50投影含49cache保持，reward1、manager及外层清理正常。原候选恢复不增加Qwen模型样本。新增Coder首轮现在已[完整回读](python__mypy-10174/coder_first_arm_trace_20261003.md)：66项原FP全部投影，实际安装/测试0、四参考PASS、reward1及双层清理完整；两模型不同源码修法、共同题目范围、验证行为与计量已由题主结合新增两非作者报告[配对验收](python__mypy-10174/two_model_first_round_acceptance_20261003.md)。总账returned/ack、活动请求清空，不重解原候选或扩大旧矩阵。

**本包两题CPU及两模型各一次首轮均已收口，无已知CPU/GPU待办或在途。** 15184的有限运营来源补证和行为分析已完成；精确GPU驻留权重身份、单次成功稳定性仍未知，属于结论边界，无具体错绑/语义缺陷就不机械追加运行。训练、留出资格均未增加。题级依赖不推导资源可停机或销毁，旧退租/自动销毁安排已停止。

## 原件验收与接续条件

回执到达后核请求ID/固定输入SHA、材料版本、实际模型/镜像/消费者、预算、job/attempt、完整轨迹、最终原候选、逐参考评分、结束原因和清理。returned是执行者交付状态；题主核关键原件、独立审查和语义后才ack并清空活动请求。15184已完成该流程。

- 正常结束且正确：记录解法与全部参考，可作该版本一次观测，不能自动授予训练/留出资格。
- 正常结束但解错：核失败参考与解法；材料正确时保留为能力结果，不为求通过无限重跑。
- 截断：保留原attempt/预算/分数与推进位置，以新身份接续必要缺项；不同预算不合并为同一次完整观测。
- 基础设施失败、评分异常或缺轨迹/模型：保留具体缺口并定向交接，不能记作能力不足。已知误奖/误拒优先复用完整原FP和定向CPU验收。

公开字节未变则复用已有fresh静态审；新增中性brief仅有非fresh边界核。实际首条solver消息另核，不能以CPU控制prompt代替交付。15184两臂任务block实际SHA一致，已完成交付检查；私有测试、gold、负对照及审查留在可信评分/审计面。

## 已完成的逐轨迹分析

10174见[Qwen首臂](python__mypy-10174/qwen36_first_arm_trace_20261003.md)、安装/来源补证及[新GPU原FP重评分](python__mypy-10174/new_GPU_regrade_acceptance_20261003.md)。旧GPUraw1/installRC1、CPU r16预热和本次新GPU结果分别保留；journal/done只证流程完成，四PASS来自实际eval/exec。新增[Coder首轮](python__mypy-10174/coder_first_arm_trace_20261003.md)及[两模型收口](python__mypy-10174/two_model_first_round_acceptance_20261003.json)已完成，实际804镜像、code8消费者、相同公开block/四参考及不同修法分列。Coder 68生成/67工具，源码提前化简非strict_optional的Union；根因解释、内联flag对照及全部测试声明的问题保留为行为质量限制，无当前材料/评分阻断。15184见[Qwen轨迹](python__mypy-15184/qwen36_first_arm_trace_20261003.md)、[Coder轨迹与比较](python__mypy-15184/coder_first_arm_trace_20261003.md)、[新增Q13来源补证](python__mypy-15184/q13_operational_identity_supplement_20261003.json)和[配对收口](python__mypy-15184/two_model_first_round_acceptance_20261003.json)。新增审查者已见gold/private，非fresh，均只读原件，没有重复执行。

下表为15184的既有逐轨迹结论；10174的不同修法、67/86工具、flags伪对照及自验范围另见其Coder分析，不将两题混作同一候选。

| 维度 | 实际回读要求与当前结论 |
| --- | --- |
| 方法与根因 | 15184联合formatter递归内层参数，保留有效断言guard/返回；10174需修Optional[Any]误报并保留真正不重叠诊断。语义与raw reward分列。 |
| 定位与纠错 | 引用首次定位、helper读取、编辑及错误纠正；gateway到达offset不冒称工具真实执行时间。 |
| 工具 | Coder24工具中2个预期mismatch、1个已纠正空选择；Qwen39工具中6个预期mismatch、2个已纠正自写测试错误。不能全计基础设施/操作失败。 |
| 并行 | 两臂未观察到模型工具并发；Coder的12个xdist worker属于测试进程并行。独立读取可批量，但没有受控加速证据。 |
| 验证 | 两臂没有主动直接测嵌套，正式受信参考另证。Coder179项和11项公开组重叠；Qwen管道tail不证独立pytest退出0。Coder“全部相关测试通过”登记P3范围过宽。 |
| 效率 | Coder52.738秒/25生成/24工具/input864729；Qwen62.946秒/40生成/39工具/input528184。环境、队列、嵌套时间及费用口径分列，不由单例排名。 |
| 结束与稳定性 | 两臂正常end_turn、原FP及评分/清理完整，每模型仅一次观测，稳定性未知。 |

15184两候选核心源码相同，完整FP不同：Qwen测试修改被可信投影排除；Coder原102项（97cache/4脚本/源码）全部投影。code_v5/code_v7共有7个共享成员不同，但本题材料、镜像、基线内容、任务block、脚本、五参考及预算相符；不称整个runtime一致或受控性能对照。

Qwen Q13新增40请求/adapter/后端完成对应成立，复用适用共享服务事实，不借用旧Q12题目覆盖范围。Coder有job前实际读回/25生成对应，manifest列25文件（16safetensors）但声明28，未列3项未知。HTTP revision/checksum为null，未重新核全部权重或GPU内存，旧false标记保留；只支持有限运营来源归因。

## 首轮完成与后续采样

沿现行安排优先覆盖就绪未测题及缺失的另一模型首轮，暂缓尚未开始的普通追加采样；不机械要求每题每模型三次。两题在用首轮请求均已完成，无理由为旧重复计划追加CPU/GPU任务。只有跨仓首轮结果形成具体校准问题后，再按新明确安排选少量样本；在途正常作业不因优先级调整中断。

同模型、材料、采样与预算的重复才用于稳定性比较；材料修订或扩大预算单列。未来比较须保留全部attempt、分母、截断/无效数，缺数据写未知。首轮可以在当前范围验收，稳定性未知和训练资格未授予必须同时保留。

## 记录与资源边界

当前题卡、配对记录和总账checkpoint维护固定版本、CPU正负对照、模型行为、独立核查、用途及剩余依赖。旧CPU条件收口和单臂JSON按当时事实保留，新的题级收口承接其后完成事实。仅新具体失败、评分缺陷或材料身份变化按影响接续。

本线程只维护本包证据和依赖。按当前用户指令停止沿用旧退租检查/自动销毁流程，后续停机、销毁由用户新的明确指示决定；不操作云实例。
