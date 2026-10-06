# Moto6185 R13 第二组五臂作者读回

2026-10-03。job `moto6185-cpu-171d1b6897be` 自然闭合，parent0。102件原件的运输 SHA／长度全部匹配；archive `248433b0c5fa8144523e6a2c999c5e867bc5455ab9e2163e8911cb4368dfd17a`，manifest `ca15ac962795e649a5a4d939607f848f1ea9a4e8d944887918bb6f65e29a469f`。原件不回写。

| 控制 | 正式分数 | 原安装 rc／秒 | 原测试 rc／秒 | 实际项／解析键 | 目标参考的实际失败 |
| --- | ---: | --- | --- | --- | --- |
| depth2 | 0 | 0／10.862 | 1／6.341 | 36／35 | 967行合法 `deeply_nested`，属性 `A.M.B.M.S` 收到 SerializationException。 |
| list_as_names | 0 | 0／11.404 | 1／5.571 | 36／35 | 967行合法 `nested_in_list`，属性 `A.L[0].M.S` 收到 SerializationException。 |
| null_only | 0 | 0／11.739 | 1／6.716 | 36／35 | 944行合法顶层属性名 S、字符串值 `asdf` 收到 SerializationException。 |
| rootkey | 0 | 0／13.837 | 1／7.587 | 36／35 | 1006行非主键的畸形 S 字典值未得到预期 ClientError，进入 Item/DynamoType/bytesize 后因 dict 无 encode 得到 AttributeError。 |
| shape | 0 | 0／11.077 | 1／6.381 | 36／35 | 938行主键的畸形 S 字典值进入 validate_key_sizes/DynamoType.size，同样得到内部 AttributeError，未保持预期 ClientError。 |

作者已核原 ledger、逐参考状态、完整 pytest 短摘要、具体失败栈与实际 api_params。五臂均为有效 `unresolved/tests_failed`，只有原目标1F失败，原34P全部通过，无 missing／skipped／unaccounted。历史合键 `test_update_item_with_duplicate_expressions[set` 的两条实际参数行均 PASSED；parser 保持原样。

原安装与测试段均完整，安装均0且无失败命令；失败发生在题目测试而非 SDK 安装。各臂原 CLI footer 记录 manager 创建／删除1、无 open／halted／aborted／cleanup failure；候选已 removed。五份自有容器、网络残留查询均实际 rc0，stdout/stderr 完整为空。运行输入与 noop 的 `runtime_inputs.json` 字节相同，固定发布、材料、脚本与预算未变。

详细读回：`runs/category2_repair_20260929/moto_cpu_20261003/moto6185-cpu-171d1b6897be_author_raw_readback_v2.json`。本报告仅本组作者读回，不是最终独立 CPU 准入。计入 noop 与首组后，作者已核10/22臂；剩余12臂继续沿既定22对照停止条件运行，最终非作者检查只补新闭合17臂。原金标不完整、rv_dynamotype 漏判观察及普通诊断用途均保留。
