# Moto6185 R13 最后一组四臂作者读回

2026-10-03。job `moto6185-cpu-28e751fc3785` 自然闭合，parent0。88原件运输SHA／长度匹配；archive `3213a42a5dc48e601943d904f9ee7a0de011bbb1fbfa9cf84320fdc5c5b348b5`，manifest `d20fddb26721399bc4bbd82f537ed9feffd33514d573251838fad3e4cab33bf4`。原件不回写。

| 控制 | 正式分数 | 原安装 rc／秒 | 原测试 rc／秒 | 完整失败段的实际结果 |
| --- | ---: | --- | --- | --- |
| rv_shape_key | 0 | 0／11.424 | 1／6.802 | 1006行非键属性的S字典值到达Item／DynamoType／bytesize，实际AttributeError：dict无encode，预期ClientError没有保持。 |
| rv_swallow_attr | 0 | 0／11.847 | 1／7.394 | 978行畸形N拒绝循环DID NOT RAISE ClientError。日志没有该轮locals，不据静态补丁猜测实际循环项。 |
| rv_tagparent | 0 | 0／10.547 | 1／6.071 | 1006行非键S字典值同样触发内部dict.encode AttributeError，而非规定ClientError。 |
| rv_top_or_null | 0 | 0／11.979 | 1／6.452 | 967行实际pk=deeply_nested，合法A.M.B.M.S输入得到SerializationException。 |

作者已读四份完整失败段、实际api_params或内部val、四份短摘要和35个逐参考状态：每臂实际36项／解析35键，只有目标1F失败，原34P均通过，missing／skipped／unaccounted为空。历史两条合键参数的两行实际PASSED保留，parser未改。目标测试首次失败后停止，后半段未到达的断言不能声称通过。

四份完整CLI footer均为创建／删除1、无open／halted／aborted／cleanup failure，候选removed。四份自有容器／网络查询实际rc0，完整stdout和stderr为空。运行输入字节与noop相同。完整安装段与已全文读取的noop比较，只归一化两次固定wheel生成SHA、pip临时缓存目录和结束时间戳，其余字节相同，两次build／install均成功。

安装比较记录2420 bytes，SHA256 `c5f73508049958b769ededd9784ea462378213b32a17d6bc58b6bf9b9afbcaea`；逐项读回69138 bytes，SHA256 `b95d45bb7697ecd3a14c29e4394a3966746123e5af411c3d7cf01ab9bbbbdd73`。两记录位于 `runs/category2_repair_20260929/moto_cpu_20261003/`，分别以本job加 `_install_segment_comparison_owner_v1.json`、`_author_raw_readback_v2.json` 命名。

累计作者核对22/22，有限串行wrapper已退出0、没有后续CPU作业。最终独立验收待写，本报告不自行授准入。既有[停止范围](../../reviews/moto6185_existing_stop_scope_readback_20261003.md)适用，不新增穷举或授训练资格。
