# MONAI3715：首个 Qwen 尝试的题主分析

2026-10-03，job `gpu1003-monai3715-qwen36-a1`。**本次候选修法合理，正式评分为1，原F2P、新增F2P及原P2P三项全部通过。第二模型尚未完成，原请求保持claimed；本记录只核一个模型的一次尝试。** 没有发现需要停止其它作业的新题面、环境或评分缺陷。

原请求为 `swe-monai3715-string-modes-r5-20261003-v1`，固定SHA `6a348f0a92f54a054eacf3e51d22cb14f769fb8d7d13f11d279a1889c0b14d67`。使用code_v4运输、`monai3715-string-modes-forward-cpu-v1`评分材料；普通探针不授予训练或留出资格。题主复用GPU非作者的执行运输核查，另读实际候选、305条harness事件、完整测试日志、冻结产物和原结果；不是重新运行实验或fresh盲审。

1. **根因和修法。** `look_up_option(mode, ForwardMode)`将输入转换后存入`self.mode`，旧分支却比较原`mode`。候选只把两处条件改为`self.mode`，保留eval_mode、train_mode和非法输入拒绝逻辑。实际FrozenPatch只有`monai/engines/evaluator.py`，无测试修改；冻结内容摘要为`cf1e7a18…`。它与gold全文摘要不同，语义仍合理，不按字符串与gold相同判正确。
2. **定位过程。** 第一条Read读取evaluator；事件21已准确指出转换结果未被分支使用。读取`look_up_option`确认后，事件61一次Edit完成修复，无补丁返工。没有在修改前执行失败复现；这是过程缺项，不伪造前后对照。
3. **工具使用。** 18次调用：4 Read、13 Bash、1 Edit；未见工具参数格式拒绝，2次Bash因错误导入失败。另有3次Saliency构造或运行错误被`try/except`捕获，shell仍退出0。特别是事件231实际打印cam_name错误后又打印“All tests passed”；该宣称无效。模型最终回到字符串/枚举构造检查，未完成正确Saliency端到端运行。现有API与解释器可用，失败指向模型误用，不据此要求换环境。
4. **并行。** 本次每轮只有一个tool_use，实际均串行；没有并行提交或执行证据，无法判断模型并行能力。若执行器支持，可合并独立搜索与部分修后检查，但本次不声称已验证其支持。
5. **验证质量。** 模型修后验证四种字符串/枚举构造和非法输入，运行`test_ensemble_evaluator.py`得到1通过；pytest输出虽经`head -60`，本次完整通过footer实际可见。随后Saliency探索多次失败，且自测主要检查构造，不能证明非空forward、梯度和模式恢复。正式评分侧的新增F2P实际覆盖这些行为，与原两项参考一起全部通过，无缺席、skip或异常替代目标断言；安装和测试段完整、测试RC0。正式行为证据和模型自测质量分别记载。
6. **效率。** 19轮／19次模型请求，累计输入257,849、输出5,556 tokens；累计输入是多轮请求之和，不是一次上下文占用。单次最大输入18,973、输出669。CC记录57.377秒，其中API34.4秒；entry求解61.005秒。评分总耗时539.19秒，候选安装17.534秒、测试9.12秒；评分/准备耗时不能算模型推理时间。定位与补丁很快，后续API猜测和重复构造验证增加了调用成本。
7. **完成与稳定性。** 实际终止completed、end_turn，无length截断；SSE/adapter与usage一致，actor、网络、relay、grader和gateway drain均已收口。有效配置为context196608、HTTP/adapter输出65536、240轮、求解10800秒。CC显示的maxOutputTokens32000原值保持，实际请求全为65536；CC估算费用不当作额外API账单。只观察一次成功，不推断稳定解决率；待第二模型，再按全批重复抽样规则决定后续。

原件位于仓库 `runs/ordinary_gpu_probe_20261002/remote/queue_v12/results/gpu1003-monai3715-qwen36-a1/`。GPU运输核查为 `runs/ordinary_gpu_probe_20261002/reviews/monai3715_qwen36_a1_execution_review.json`；其未覆盖全GPU现场空闲、长上下文压缩或训练链路的限制保持。报告中的4096MB不称独立实测峰值。

[题主机器核查与逐调用索引](checks/monai3715_qwen36_a1_owner_analysis_20261003.json)绑定11份原件大小/SHA、实际参考、调用事件、失败证据和指标。后续继续原请求，不重复这个已完成首尝试，也不据首模型完成清空整项待办。
