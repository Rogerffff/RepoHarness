# Moto6185 R13 第三组四臂作者读回

2026-10-03。job `moto6185-cpu-2a9a5338febf` 自然结束，parent0。88原件的运输 SHA／长度全部匹配；archive `b84d3980b1cf09e09242b2c3e1b5d43c933b6d1bed32cc00fd10bbc31aafb492`，manifest `80cc25181611f58c94ffff37cb735198b216a59fa62cdbbbb83e43a905c4fe4f`。原件不回写。

| 控制 | 正式分数 | 原安装 rc／秒 | 原测试 rc／秒 | 目标参考的具体失败 |
| --- | ---: | --- | --- | --- |
| siblings | 0 | 0／11.334 | 1／6.901 | 967行合法 issue_nested 的 A.M.S.NULL 被误判，PutItem 收到 SerializationException。 |
| skip_s_subtree | 0 | 0／11.748 | 1／6.652 | 978行畸形 N 数值校验未触发预期 ClientError；补丁跳过属性名 S 的整个子树，失去子树校验。 |
| swallow | 0 | 0／11.391 | 1／6.566 | 978行同一畸形值拒绝检查 DID NOT RAISE；补丁捕获 SerializationException 后只校验主键，非主键异常被吞掉。 |
| top_only | 0 | 0／10.510 | 1／6.099 | 967行合法 issue_nested 的 A.M.S.NULL 仍误判为 SerializationException。 |

作者读取原失败段、实际请求参数、逐参考状态、完整短摘要和两个历史合键参数。四臂实际收集36项／解析35键，只有目标1F失败，原34P全部通过，无 missing／skipped／unaccounted；合键的两条实际参数行都 PASSED。失败为题目语义检查，不是基础设施或安装失败。978行是参数循环的异常检查，不能据此声明失败后尚未执行的循环或目标参考后半段均已验证。

四份原 CLI footer 均为 manager 创建／删除1、无 open／halted／aborted／cleanup failure，候选 removed。四份自有容器／网络查询均实际 rc0、完整 stdout/stderr 为空。运行输入与已闭合 noop 字节相同，R13发布、补丁、脚本、身份和预算不变。

原安装段与已完整读取的 noop 段做全量比较，仅两次原 editable wheel 的生成SHA、pip临时缓存目录和结束时间戳不同；固定文件名、大小、两次 build/install 成功及所有其余字节一致。比较原件 `runs/category2_repair_20260929/moto_cpu_20261003/moto6185-cpu-2a9a5338febf_install_segment_comparison_owner_v1.json`，2388 bytes，SHA256 `9fcbad1d637a6895759869c7e76539ff6c8ea2b591c5e000004d8671a9779b2e`。

逐项读回 `runs/category2_repair_20260929/moto_cpu_20261003/moto6185-cpu-2a9a5338febf_author_raw_readback_v2.json`，69089 bytes，SHA256 `3e6d16c37b7266adeda089fd37f4868166cbb7e1ca8795e712b70feb11b873d7`。本报告仅作者本组读回。作者累计14/22，独立报告仍只覆盖最先五臂、UID和公开CC；最终报告沿固定22对照停止条件增加未覆盖17臂，不扩穷举，不授训练／留出／typed-actor资格。
