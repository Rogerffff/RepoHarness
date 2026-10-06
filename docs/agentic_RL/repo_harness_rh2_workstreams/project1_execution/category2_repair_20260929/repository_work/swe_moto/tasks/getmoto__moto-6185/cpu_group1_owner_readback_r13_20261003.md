# Moto6185 R13 首组四臂作者读回

2026-10-03。job `moto6185-cpu-d3ebfdc58aa8` 自然结束，实际 parent0。运输88件原件的 SHA／长度全部匹配，manifest `b3bd95d3fe240e4d46f22f0e50ef82b4263b6815657ff875fbae948afced3f97`，archive `e4e24a8d76fde4ccef67c3d9c6f2e4d221f2a9ecbd9fddf82cbdebe069cd9fbd`。原件不回写。

| 控制 | 正式分数 | 原安装 rc／秒 | 原测试 rc／秒 | 实际项／解析键 |
| --- | ---: | --- | --- | --- |
| gold（已知不完整） | 0 | 0／10.263 | 1／6.544 | 36／35 |
| ctx | 1 | 0／11.336 | 0／6.450 | 36／35 |
| ctx_list（兼容修法） | 1 | 0／10.541 | 0／6.286 | 36／35 |
| parity | 1 | 0／11.046 | 0／5.980 | 36／35 |

已核原 ledger、完整 pytest 短摘要的每条状态及两个合键参数的完整字符串，所有原34P通过；gold 只有目标1F失败，另三臂全部参考通过，无 missing／skipped／unaccounted。历史 `test_update_item_with_duplicate_expressions[set` 合键对应两条实际参数，四臂的两行均 PASSED，没有修改 parser。

gold 完整失败栈确认：此前合法顶层／多层／列表属性名 `S` 和畸形值检查均已越过，最终以合法主键名 `M`、嵌套属性名 `S` 写入 `key_named_m` 表时，在原修订测试994行收到 `SerializationException: Start of structure or map found where not expected`。这是既有 D4 不完整金标的真实语义失败，不能把 gold 强改为正对照或基础设施错误。

四臂原 `make init` 和测试标记完整，安装无失败命令。作者读取逐项状态、gold 完整失败、四份原 CLI 完整 footer 和四份归属资源回执；manager 各创建／删除1、无 open／halted／aborted／cleanup failure，候选均 removed，自有容器／网络查询实际 rc0且完整输出为空。全部运行输入 `runtime_inputs.json` 与已闭合 noop 原件字节相同，固定材料、脚本和预算保持。

详细机器读回位于 `runs/category2_repair_20260929/moto_cpu_20261003/moto6185-cpu-d3ebfdc58aa8_author_raw_readback_v2.json`，68081 bytes，SHA256 `abeea8e5ba5ca6ca3e7eb971b4337f01635c9a1ea14914695983dadf34cef7b1`；它核原件和参考身份，但其中 true 不能替代失败语义和完整清理读取。实际安装／测试全日志随88件原件保留。

本报告仅本组作者读回，不是最终 CPU 验收。另有 noop、实际UID原安装和真实 CC 原公开四操作的闭合原件；还需固定其余17臂及最终非作者检查。`rv_dynamotype` 的历史漏判观察不升级为正确修法，既有22对照停止条件不扩成新穷举，训练／留出／typed-actor 资格未授予。
