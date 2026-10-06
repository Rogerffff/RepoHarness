# 修订前的 R2E 摄入产物（历史，不被消费）

2026-09-24 用户批准材料修订 T0-1 / T0-2 之前的产物原件，逐字节取自 Codex R-f 复核归档的输入快照
（`runs/r2e_rf_review_20260924/verified_input_snapshot.tar.gz`）。提交记录 sha256 = `ea567fec…`，即旧代码常量
`R2E_INGEST_MANIFEST_SHA256_PIN` 的值；R-f（09-23）与 09-24 中央复跑都是按这一版评分的。

现行产物在 `../ingest/`（封板输入 `t1_input_pins_r2e_v2.json`，多了第五项材料修订单）。与本目录相比：
46 题评分面只多了空的 `material_revisions` 字段；coveragepy `016af5f6` 的期望原文改了一个键（`r2e-mr-001`）；
datalad `58ba5165` 的隐藏测试清单里 `test_1.py` 的摘要变了（`r2e-mr-002`）；公开面、gold 面不变；环境包只有
评分面摘要随之变化。本目录只作来源版对照，任何正式入口都不读它。
