# 修订单 v3、SWE-Gym 提示措辞时期的 R2E 摄入产物（历史，不被消费）

2026-09-24 深夜按封板输入 `t1_input_pins_r2e_v4.json`（pins 记录 sha256 = `91bcf90c…`，第五项是修订单 v3）生成的产物原件，
逐字节复制自当时的 `../ingest/`；提交记录 sha256 = `adbd27a1…`。批次三的正式运行（`runs/r2e_t0_batch3_20260924/`）与
静态筛查材料 v1 / v2（`runs/r2e_static_prep_20260924/`）都对应这一版。

现行产物在 `../ingest/`（提交记录 `781363b0…`，封板输入不变）。唯一差别：09-25 按 E09（用户批准"按来源区分的提示措辞"）
把 R2E 公开面的 `public_hints` 从 SWE-Gym 的 conda 措辞换成 R2E 措辞（`ingest_r2e_subset.R2E_PUBLIC_HINTS`），因此 48 题的
`public_hints` 与环境包里的 `public_bundle_digest` 变化；评分面、验证面与期望、隐藏测试逐字节不变。本目录只作对照，
任何正式入口都不读它。
