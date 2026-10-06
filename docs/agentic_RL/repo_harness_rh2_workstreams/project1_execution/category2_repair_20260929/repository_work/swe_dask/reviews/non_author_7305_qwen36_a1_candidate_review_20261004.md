# Dask7305：Qwen3.6 首臂非作者语义与轨迹核查

2026-10-04。**候选部分修复，仍违反公开精确端点目标；本次 raw reward 0 准确。所核范围未发现新增材料缺陷、评分误拒或控制污染，不要求重新跑 CPU 矩阵，也不自动追加模型样本。** 这是一臂真实模型结果，不据此宣布题目失败、模型稳定能力或训练资格。

我是非作者核查者，没有参与候选编写或运行。已见私有测试、替代正对照和既有作者／非作者报告，属于证据核查，不能作为 fresh 公开盲审。本次只读冻结原件，在内存重放编辑、比对源码并解析原日志；没有运行模型、Dask／pytest、CPU、容器或 SSH。仅新增本报告与同名 JSON。机械运输、code9／R25 的实际部署与共享消费绑定、当前入口由题主独占核收。

## 评分失败在哪里

固定版本为 `dask7305-exact-ends-auto-v3`，实际 job 为 `gpu1003-dask7305-qwen36-a1`。完整正式日志的 105 项参考无缺席：1F 失败、104P 通过；全模块另有 3 个既有 slow skip，位于正式参考外。原日志安装与测试均结束，测试 rc1 对应断言失败，report 无 infra failure。

F2P 先通过原小整数／float 控制和大 uint64 的 1 输入／1 输出分区 helper。随后在原公开二值输入的 **1 输入／3 输出分区**失败：`test_shuffle.py:668` 调用 `_assert_exact_int_divisions(issue, "uint64", 1, 3)`，`623` 行比较 Python 整数的最小端点，得到 `612509347682975744`，真实值为 `612509347682975743`。这不是近似内部分界的选择差异。

该调用的 dtype 检查已过，但最大端点、排序、set_index 端点／区间／行量断言尚未到达；后六组大整数与 auto helper 也未到达。不能写成“Qwen 在 auto 失败”或“auto 已验证”。单独的 `test_set_index_interpolate_large_uint` 和其余 104P 通过，不能代替这些未执行断言。

## 实际候选遗漏了哪一步

直接解码 FrozenPatch，只有 `dask/dataframe/partitionquantiles.py` 一项生产文件修改，正文 SHA 为 `a204ac5c6c1a8691e1193105acb04d01e8ba0ca5e991bbd19ff8fd143d2ca690`。候选在 `percentiles_summary:417–425` 先转回整数 dtype，再把每个输入分区摘要首尾改为真实 min／max。

该修法恢复了模型测试的字面 1→1 例子，却漏掉摘要合并后的处理：两行数据在 `sample_percentiles:144–145` 产生 0／50／100 三个摘要值，3 个输出分区需要 4 个分界。`process_val_weights:337–343` 的欠采样分支仍用 `np.interp`，再次转成 float64；`381–382` 转回 uint64 后，端点又偏大 1。源码路径与原日志数值一致。跨 `2**63` 的 dtype 推断和 `shuffle.py:506–510` 的整数 auto 插值也未改，但本次运行提前失败，这两项只能记为未到达的静态遗漏。

全轨迹的 3 次 Edit 已在原 baseline 正文上逐字重放：首次修改 `dask/array/percentile.py`，随后完整回退，再修改 `partitionquantiles.py`。最终重放正文及内存应用审阅 diff 的正文都等于实际 FP，array 文件等于原 baseline。没有根据模型最终说明猜测候选内容。

## 公开目标与替代解

实际首请求保留原题面：要求大整数 minimum／maximum 精确，并描述乱序输入末尾最小值的 set_index 行归属症状。prepared prompt、solver prompt、attempt prompt 和首 API user 的题目文本按原字节相等，SHA 为 `17fa4f73b0935467b461da018519009038bcd73c6e3e22938dffb014fd4bc752`，2721 字节；另一个 user 块只是 CC 日期提醒。旧通用 public_hints 不在实际题目块中，不把旧控制桩的交付范围套给本臂。

v3 不锁定近似的内部分界值或 gold 算法；它核精确端点、整数 dtype、有序分界、每行归属和完整行多重集合。dtype 保护有公开报告的转换症状及 base 收尾 cast／`df._meta` 依据，本候选也通过了该检查。此次拒绝发生在最小端点真错误，不存在 dtype 分歧造成的误拒。

复用固定正式 17 行的既有独立 CPU 验收：`gold_full_auto=1`，其余 16 行为 0。正确替代解没有实例常量，整数 auto 从有序精确摘要取分界；旧 gold／full／exact／higher 的 auto 真缺陷没有因名称被忽略。该正对照证据说明当前已核范围可被合理修法满足；它不能转为 Qwen 通过，也不证明穷尽全部合理实现。本次没有发现具体的新增误拒案例。

## 模型表现与验证边界

模型先猜 uint 溢出，再用 float64→整数实际读回纠正为精度损失；对第一层定位准确。首次全局改 `_percentile` 后，普通 `test_quantile` 和 `test_dataframe_quantile` 实际失败。它读取 `core.py`，发现 quantile 内部会补 0／100 分位数，主动撤回会截断插值值的改动，改到局部摘要函数。这次纠错有真实回归证据。

最终公共测试实际是 array percentiles 的 16 passed／1 unconditional skipped，两个 dataframe quantile 组各 2 passed，以及 quantile／repartition 选择的 164 passed／109 slow skipped／348 deselected。选择并未覆盖 test_shuffle 模块。模型的少量大整数／多分区／set_index 实例确有正确端点打印，但没有测欠采样的 1→3、auto、每分区区间或完整行保留。若干 uint64 比较没有先转 Python int，验证方法可能掩盖精度差异；所测实例已有正确打印，不能一概称为假通过。首次 int64 实验曾打印中间值 `-9223372036854775808`，模型只接受端点正确，未继续追踪摘要内部有序性。

本臂 39 次响应／39 CC turns，38 次工具调用（27 Bash、8 Read、3 Edit），solve 120.362 秒；CC 报告输入 1,092,050 tokens、输出 14,782 tokens。多数工具串行，重复 float64 演示和相似端点检查较多，关键遗漏在验证选择。最终 float64 根因和为什么不全局改 `_percentile` 的解释准确，但“fix is complete”超过已有证据，应列为模型最终说明不准确，不能当成实现完成。

## 污染、原件与停止条件

检查 39 份请求 body，未见私有 helper、gold_full_auto、材料修订 ID、effective_test.patch 或 host_grading_views 等标记。观察到的 Read 只读公开源码和既有公共测试；actor baseline 的 `test_shuffle.py` SHA 为 `b019a81adb92ddca708845b87866517551f7353739563f573707992da1d13b42`，没有新私有 helper。实际 FP 只改生产文件，未改测试或评分控制面。这里未见本次材料泄漏证据，不证明预训练污染不存在，也不替代完整安全审计。

同名 JSON 列出本次实际读取的 33 件原件路径、SHA／大小及 4 个 baseline archive 成员 SHA；全 148 成员清单与实际 code9／R25 绑定仍由题主另验。

关键原件：

- [实际轨迹](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7305-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7305-qwen36-a1/attempt/trajectory.jsonl)。失败相关调用／结果在 529／533、547／551、601／605，最终说明在 615 行。
- [正式评分日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7305-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7305-qwen36-a1/grading/eval_logs/evallog_gpu1003-dask7305-qwen36-_85f0af94.eval.log)。实际失败在 1578–1605 行。
- [候选 FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7305-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7305-qwen36-a1/attempt/frozen/frozen_patch.json)、[审阅 diff](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7305-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask7305-qwen36-a1/attempt/candidate/dask__dask-7305.diff)。
- [既有正式 CPU 独立验收](non_author_7305_formal_cpu_r15_review_20261003.md)、[有效测试](../tasks/dask__dask-7305/effective_test.patch)、[正确替代解](../tasks/dask__dask-7305/gold_full_auto.patch)。

本轮已足以核收 Qwen 首臂的题级失败机制和评分语义；没有具体新材料／评分误拒反例，停止本轮语义追查。Coder 同 FP CPU0 与 Qwen0 是各自首轮结果，不能自动变成题目缺陷或重采样理由。后续由题主结合双模型回执及机械核收更新当前入口。本轮没有改变已定案题意、reward、运行预算或训练准入语义。
