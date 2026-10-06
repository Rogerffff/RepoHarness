# 修订单 v2 时期的 R2E 摄入产物（历史，不被消费）

2026-09-24 晚按封板输入 `t1_input_pins_r2e_v3.json`（pins 记录 sha256 = `5f6ed8d6…`，第五项是材料修订单
`material_revisions_v2.json`，含 `r2e-mr-001`…`007`）生成的产物原件，逐字节复制自当时的 `../ingest/`。
提交记录 sha256 = `e8d305f0…`，即当时代码常量 `R2E_INGEST_MANIFEST_SHA256_PIN` 的值。T0-5（scrapy `cfed9b66`）与
T0-6 代表题（pandas `4ec87eb9`）的正式运行（`runs/r2e_t0_batch2_20260924/`）是按这一版评分的。

现行产物在 `../ingest/`（封板输入 `t1_input_pins_r2e_v4.json`，第五项换成修订单 v3，另加 T0-6 第二步与 T0-7 的
13 条修订 `r2e-mr-008`…`020`）。与本目录相比：pandas `19c5eea5`、`294cbc8d`、`32dd55cb`、`7dd34ea7`、`87787609`、
`f656217a` 的隐藏测试清单（多一个私有 `conftest.py`）与期望原文随修订变化，orange3 `9b5494e2` 的期望原文随修订变化，
环境包里这 7 题的评分面摘要随之变化；其余 41 题的评分面、全部 48 题的公开面与 gold 面逐字节不变。
本目录只作对照，任何正式入口都不读它。
