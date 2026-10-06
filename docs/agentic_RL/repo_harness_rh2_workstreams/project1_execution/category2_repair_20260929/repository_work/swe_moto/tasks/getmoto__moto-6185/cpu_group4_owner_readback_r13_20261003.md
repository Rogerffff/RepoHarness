# Moto6185 R13 第四组四臂作者读回

2026-10-03。job `moto6185-cpu-811928f6a0d2` 自然闭合，parent0。88原件运输 SHA／长度匹配；archive `5c118782cb45cd2e97304d0b35b5296d1e2c270a3e152404c2f29ca5276ddd3f`，manifest `0447a7eeade865d395b0e158e365dee9ef03956f37470a55739ace34df42b099`。原件不回写。

| 控制 | 角色 | 正式分数 | 原安装 rc／秒 | 原测试 rc／秒 | 目标参考的结果 |
| --- | --- | ---: | --- | --- | --- |
| rv_break_after_s | 错误修法 | 0 | 0／11.742 | 1／7.229 | 978行 DID NOT RAISE：遇到属性名 S 后 break，后续同层畸形 N 成员未完整校验。 |
| rv_depth4 | 错误修法 | 0 | 0／11.074 | 1／6.730 | 967行 five_levels_deep 合法输入得到 SerializationException，阈值修法仍拒绝更深属性名 S。 |
| rv_dynamotype | 范围外漏判观察，不是正确正例 | 1 | 0／11.519 | 0／6.228 | 正式36项全过；已登记多标签畸形值差异不在本组保护断言中，原分不改成广泛语义正确结论。 |
| rv_scalar_s | 错误修法 | 0 | 0／10.923 | 1／6.726 | 967行 S_holding_a_map 合法属性得到 SerializationException。 |

作者已读三份完整失败段、实际 api_params、四份短摘要和逐参考状态，实际36项／解析35键。三负臂仅目标1F失败；观察臂1F通过；所有原34P通过，无 missing／skipped／unaccounted。历史两条合键参数的完整行与 PASSED 状态已核，parser 未改。目标参考在首次失败处停止，不能将未到达的后半段声明为通过。

四份原 CLI footer 均为 manager 创建／删除1、无 open／halted／aborted／cleanup failure；候选 removed。四份自有容器／网络查询实际 rc0、完整 stdout/stderr 为空。运行输入字节与 noop 相同。四份完整安装段与已完整读取的 noop 仅两次生成 wheel SHA、pip临时缓存目录、结束时间戳不同，其余字节及两轮成功不变；比较记录2412 bytes，SHA256 `6335997e965f9c4934df4250e55f2409a0f4a52cfdb9966155ff9527c35af8f4`，位于 `runs/category2_repair_20260929/moto_cpu_20261003/moto6185-cpu-811928f6a0d2_install_segment_comparison_owner_v1.json`。

逐项读回68812 bytes，SHA256 `42969dfb40a9372313f1fbd9e325a62330d677e1de84f855b23a3ff9714bd7c7`，位于同目录 `moto6185-cpu-811928f6a0d2_author_raw_readback_v2.json`。本报告仅作者读回；累计18/22，末组四臂在途，最终独立报告尚未完成。既有 [停止范围读回](../../reviews/moto6185_existing_stop_scope_readback_20261003.md)适用；不新增范围外穷举、不授最终准入或训练资格。
