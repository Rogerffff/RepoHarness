# MONAI3715：Coder 首次尝试的题主分析

2026-10-03，job `gpu1003-monai3715-coder-a1`。**候选修复语义合理，原评分1，2 F2P＋1 P2P全部通过。模型没有运行自测；完整行为证据来自正式评分，不能冒称模型自行验证。** 两个模型的首次执行已完成，本记录不授予稳定能力或训练资格，也没有发现需要新环境修复的具体缺陷。

原请求 `swe-monai3715-string-modes-r5-20261003-v1` 的SHA仍为 `6a348f0a92f54a054eacf3e51d22cb14f769fb8d7d13f11d279a1889c0b14d67`。本次使用code_v7、`monai3715-string-modes-forward-cpu-v1`材料；题主复用GPU非作者的运输审查，另核16份原件SHA、完整62条harness事件、候选冻结内容、正式日志和实际请求。不重新执行CPU或模型，也不把旧结果重绑新版本。

1. **根因和修法。** 固定base中的`ForwardMode`是普通Enum；字符串必须由`look_up_option`归一化，旧分支却比较原参数。候选把转换结果存入局部`mode_enum`并比较它，仍将`self.mode`设为原`eval_mode`／`train_mode`。实际FP唯一文件为`monai/engines/evaluator.py`，内容与固定base上这一次Edit精确相等，未改测试或其它实现。它保留字符串、枚举、非法输入拒绝及原上下文管理，不按与gold文字相同判正确。
2. **定位过程。** 事件10读evaluator，23读枚举，36读lookup，45明确定位“转换结果未被比较”，49一次Edit。事件45有一句误称原`mode`被overwrite，实际赋值给`self.mode`；其后解释和最终说明正确区分两者，补丁没有这个错误。无修改前的失败复现，也无补丁返工。
3. **工具使用。** 只有3 Read＋1 Edit，结果分别见14／27／40／53，无工具格式拒绝或执行错误。轨迹不存在Bash、自写测试或真实Saliency运行。不能用“没有执行失败”推断验证完整，也不能把没有自测归因于环境不可运行。
4. **并行。** 每轮只有一个tool_use，实际串行。独立读操作理论上可合并，但现有轨迹未证明执行器并行支持，不能判断模型并行能力。
5. **验证质量。** 模型编辑后直接结束，最终“已修复／兼容”是静态判断，不是测试结果；它没有虚构具体测试通过日志。正式评分安装RC0、测试RC0、完整footer为`3 passed, 17 warnings`，原F2P／原P2P／新增F2P均实际PASSED，无缺席、skip或部分日志。新增节点涵盖4种字符串／枚举模式×2种初始training状态×2种初始grad状态，共16组合，检查非空forward、预测值、梯度及状态恢复。这些是正式验收证据，不是模型自测；真实Saliency算法端到端仍未覆盖。
6. **效率。** 5轮／5次模型请求，累计输入62,060、输出957 tokens；单请求最大输入18,638、输出454。累计输入是多轮之和，不是上下文占用。CC耗时8.290秒、API8.178秒，entry求解11.687秒；评分554.02秒，其中受信准备513.712秒，候选安装17.42秒、测试9.351秒。静态定位和窄修很快，缺少自测同时降低了调用量；不能把这次速度直接推广为模型能力或吞吐结论。
7. **完成与稳定性。** 实际completed／end_turn，5次HTTP均200且SSE完整，没有length截断；双层清理及gateway drain由GPU审查支持。有效context196608、实际HTTP输出65536、240轮、求解10800秒；CC显示32000的原值保持，不当实际请求限制。单次成功不能估计稳定解决率、证明训练饱和；本次未触发长上下文压缩或训练消费。按14:01现行覆盖优先规则暂缓普通追加采样。

Qwen首臂用code_v4，本臂用code_v7。GPU审查核4个关键运输文件同字节；两次题级材料、实际image、完整baseline、公开prompt、3参考、脚本摘要和预算相同，但8个共享consumer／grader文件发生变化，因此不称整棵runtime相同，也不称两个FP相同。原公开prompt含CRLF；本次用原始字节解码与实际HTTP比对，未通过换行归一化改变证据。

grader生命周期高水位4GiB和有限42个资源样本保留；安装、测试窗口各仅1个样本，不能推出测试最低内存、连续峰值或全程无OOM。root chown单点观察和准备耗时也不能解释全部准备原因。普通探针`env_qualification=absent`，真实训练actor接线仍不在本次范围。

原件位于 `runs/ordinary_gpu_probe_20261002/remote/queue_v21/results/gpu1003-monai3715-coder-a1/`；复用审查为 `runs/ordinary_gpu_probe_20261002/reviews/monai3715_coder_a1_execution_review_v1.json`。两模型总回执SHA `36740efe35e1d98af4c9efcc90e00e3c9582194feb3795d875f59ae94070e832`：生成时`not_sent`／`request_returned`标记保持原件，当前行政回传事实以总账returned和实际发送notice为准。

[机器核查与逐调用索引](checks/monai3715_coder_a1_owner_analysis_20261003.json)绑定16份原件、FP／baseline摘要、逐参考结果及指标。本记录等待独立语义窄核；整题现行结论在[双模型首次诊断](probe_summary_3715_two_model_20261003.md)维护，旧Qwen单臂报告保持历史原件。
