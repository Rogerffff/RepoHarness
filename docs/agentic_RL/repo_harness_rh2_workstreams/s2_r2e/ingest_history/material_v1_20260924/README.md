# 修订单 v1 时期的 R2E 摄入产物（历史，不被消费）

2026-09-24 按封板输入 `t1_input_pins_r2e_v2.json`（pins 记录 sha256 = `60e187a0…`，第五项是材料修订单
`material_revisions_v1.json`，只含 `r2e-mr-001` / `r2e-mr-002`）生成的产物原件，逐字节复制自当时的 `../ingest/`。
提交记录 sha256 = `706abc8a…`，即当时代码常量 `R2E_INGEST_MANIFEST_SHA256_PIN` 的值。T0-1 / T0-2 的真实评分验证
（A 线机器，`runs/r2e_t0_revisions_20260924/`）与 numpy `43e333e2` 环境配方的验证都是按这一版评分的。

现行产物在 `../ingest/`（封板输入 `t1_input_pins_r2e_v3.json`，第五项换成修订单 v2，另加 T0-5 / T0-6 的五条修订）。
与本目录相比：coveragepy `016af5f6`、datalad `58ba5165` 与其余 44 题的评分面逐字节不变；scrapy `cfed9b66`
（`r2e-mr-003`…`005`）与 pandas `4ec87eb9`（`r2e-mr-006`、`007`）的隐藏测试清单、期望原文随修订变化，
环境包里这两题的评分面摘要随之变化；公开面、gold 面不变。本目录只作对照，任何正式入口都不读它。
