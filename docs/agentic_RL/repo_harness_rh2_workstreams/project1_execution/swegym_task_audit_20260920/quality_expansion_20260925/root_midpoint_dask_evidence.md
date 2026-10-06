# Dask 三题中期决定性复核

2026-09-25。仅复核 6801、7138、7305 的决定性结论；已读三题原题、完整 test.patch/gold.patch、下列 base 源码及当前 card/review、pack07_report/followups。7305 另按 run_refs 读取两份既有日志中的目标测试状态及 grading.json。未运行或导入项目、测试、容器、网络、安装、模型；未复核完整角色流程、摘要链或所有 P2P。没有新增 actor 证据。

结论：pack07 的三项核心判断可保留，未发现需推翻当前裁定的技术误归因。以下收窄是证据表达与后续范围，不增加执行或审批前置。

| 题目 | 本次直接核得的依据 | 保留与边界 |
| --- | --- | --- |
| 6801 | base parquet/core.py:536–585 在 initialize_write 后以 df.to_delayed() 构写图；dataframe/core.py:1474–1497 默认各自优化。gold 改用依赖原 df 的 HighLevelGraph。arrow.py:836–873 仍在初始化中对 object 列逐分区同步 compute。test.patch 仅检查写图中的 read-parquet 层、BlockwiseParquet 与列 B。 | 普通共享图修复有局部机制支持；原题 infer 目标仍有未改的采样残留。残留受 PyArrow、schema_field_supported、object 列等条件约束，不能泛化为所有 infer 都提前计算，不能静态宣称精确次数。保留普通/infer 分阶段计数提案；它用于量化与直接验收，不必等它才能指出现有评分缺计数。 |
| 7138 | base routines.py:1197 为 ravel(array)，gold 更名 array_like。utils.py:685–695 的 derived_from 正常分支改 docstring 后返回原函数，不补别名。core.py:4058–4095 中 asanyarray 对现有 Array 直接返回。 | 旧 da.ravel(array=...) 的绑定破坏明确，保留兼容问题；新转换机制也成立。保留旧形参再在函数体转换是足够窄的合理方向，是否版本化修改参考由维护者处理；不需要 CPU 重证 Python 绑定，不应把参考维护解释为等待上游响应的外部前置。全零测试不证一般顺序、no_op 名称不证零拷贝。 |
| 7305 | grading.json 列 large_uint 于 104 P2P；noop 日志:1597 与 gold:1602 均 PASSED。shuffle.py:489–492 先 compute quantiles/min/max，523–530 的单输入=单输出分区条件随后以 min/max 替换 divisions。partitionquantiles.py:337–343 仅在唯一值少于输出边界数时 np.interp；381–382 可再转回原 dtype。 | 保留“测试运行 quantiles，但其错误端点可被后续覆盖”，撤回旧“未执行/不在 P2P”说法的现有更正准确。gold nearest 是有效局部机制，不能称假修复；不能由这个 P2P 成功证明直接返回端点已修。1 与 3 输出分区的直接对照有明确分支区分价值，不需 CSV、真实多文件数据或全仓。 |

7305 的分支还能静态细化：公开两值输入会走 sample_percentiles 的小样本分支（partitionquantiles.py:144–145），gold 的 nearest 只选原值，merge_and_compress_summaries 合并相同值。因此请求 1 输出分区时两个唯一值可走 len(vals)==npartitions+1 的直接返回；请求 3 输出分区时两个唯一值少于四个边界，会进入 np.interp。前者支持局部修复，后者定位剩余浮点精度风险；这不是新的数值运行证明，完整性仍按现有 unknown 保留。小整数 {1,2,4} 的唯一 F2P 确实约束特定内部边界，但未执行完整替代解，不应提升为已实证误拒或所有合理解必拒。

建议对短卡的“7305 未验直接问题”使用更精确的“未单独验收 partition_quantiles 返回的精确端点”，避免再被读成该调用未执行。6801 短汇总提到 infer 残留时保留上述触发条件。两项 CPU 对照仍只是后续建议；现有静态证据已足以维持质量待处理，不能将对照或历史 grader 成功替代 actor 初态、工具、权限与资产验证。
