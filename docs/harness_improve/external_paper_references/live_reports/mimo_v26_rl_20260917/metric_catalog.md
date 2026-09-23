# 全部公开指标目录

冻结快照：2026-09-17 02:24:38 UTC 开始采集。Pro 主曲线 step 1–12，Flash step 1–15。

下表显示主曲线末步值；`缺失；最近 sN=…` 表示该末步没有点，严禁当作末步实测值或零。`—` 表示此 run 无公开序列。
完整逐步值见快照中的 `pro_series_merged.json`、`flash_series_merged.json`；精确首末值、范围与非零点数见 [metrics_summary.json](metrics_summary.json)。

2,067 个标签是两个 run 的并集：Pro 2,019，Flash 2,050；它们不是 2,067 项独立实验。

## actor · 257

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `actor/agentic/entropy_loss` | 0.396628 | 0.438344 |
| `actor/agentic/pg_clipfrac` | 0 | 0 |
| `actor/agentic/pg_loss` | 0.00703206 | 0.0108173 |
| `actor/agentic/pg_tis_clipfrac` | 0.000280968 | 0.00020089 |
| `actor/agentic/pg_tis_clipfrac_neg_high` | 1.34748e-05 | 1.03374e-05 |
| `actor/agentic/pg_tis_clipfrac_neg_low` | 0.000114338 | 8.89229e-05 |
| `actor/agentic/pg_tis_clipfrac_pos_high` | 1.62352e-05 | 1.03212e-05 |
| `actor/agentic/pg_tis_clipfrac_pos_low` | 0.00013692 | 9.13086e-05 |
| `actor/agentic/ppo_kl` | 0 | 0 |
| `actor/chat/dataset-8kb6/entropy_loss` | 0.387075 | 0.400215 |
| `actor/chat/dataset-8kb6/pg_clipfrac` | 0 | 0 |
| `actor/chat/dataset-8kb6/pg_loss` | 0.00227551 | -0.00416511 |
| `actor/chat/dataset-8kb6/pg_tis_clipfrac` | 7.48461e-06 | 3.51151e-05 |
| `actor/chat/dataset-8kb6/pg_tis_clipfrac_neg_high` | 4.2131e-07 | 2.7564e-07 |
| `actor/chat/dataset-8kb6/pg_tis_clipfrac_neg_low` | 3.68655e-06 | 1.20438e-05 |
| `actor/chat/dataset-8kb6/pg_tis_clipfrac_pos_high` | 0 | 0 |
| `actor/chat/dataset-8kb6/pg_tis_clipfrac_pos_low` | 3.37675e-06 | 2.27957e-05 |
| `actor/chat/dataset-8kb6/ppo_kl` | 0 | 0 |
| `actor/chat/dataset-eup7/entropy_loss` | 0.397746 | 0.583195 |
| `actor/chat/dataset-eup7/pg_clipfrac` | 0 | 0 |
| `actor/chat/dataset-eup7/pg_loss` | 0.0135488 | 0.0230852 |
| `actor/chat/dataset-eup7/pg_tis_clipfrac` | 2.08847e-07 | 1.25993e-06 |
| `actor/chat/dataset-eup7/pg_tis_clipfrac_neg_high` | 0 | 0 |
| `actor/chat/dataset-eup7/pg_tis_clipfrac_neg_low` | 0 | 4.51299e-07 |
| `actor/chat/dataset-eup7/pg_tis_clipfrac_pos_high` | 0 | 0 |
| `actor/chat/dataset-eup7/pg_tis_clipfrac_pos_low` | 2.08847e-07 | 8.08632e-07 |
| `actor/chat/dataset-eup7/ppo_kl` | 0 | 0 |
| `actor/chat/dataset-lm3t/entropy_loss` | 0.33823 | 0.281922 |
| `actor/chat/dataset-lm3t/pg_clipfrac` | 0 | 0 |
| `actor/chat/dataset-lm3t/pg_loss` | -0.0436887 | 0.0713205 |
| `actor/chat/dataset-lm3t/pg_tis_clipfrac` | 2.36662e-05 | 2.86491e-06 |
| `actor/chat/dataset-lm3t/pg_tis_clipfrac_neg_high` | 0 | 4.09273e-07 |
| `actor/chat/dataset-lm3t/pg_tis_clipfrac_neg_low` | 0 | 1.63709e-06 |
| `actor/chat/dataset-lm3t/pg_tis_clipfrac_pos_high` | 0 | 1.36424e-07 |
| `actor/chat/dataset-lm3t/pg_tis_clipfrac_pos_low` | 2.36662e-05 | 6.82122e-07 |
| `actor/chat/dataset-lm3t/ppo_kl` | 0 | 0 |
| `actor/clip_high` | 0.27 | 0.27 |
| `actor/clip_low` | 0.2 | 0.2 |
| `actor/code/dataset-4onq/entropy_loss` | 0.528322 | 0.549582 |
| `actor/code/dataset-4onq/pg_clipfrac` | 0 | 0 |
| `actor/code/dataset-4onq/pg_loss` | 0.0104121 | 0.034453 |
| `actor/code/dataset-4onq/pg_tis_clipfrac` | 6.57926e-07 | 1.74335e-07 |
| `actor/code/dataset-4onq/pg_tis_clipfrac_neg_high` | 0 | 0 |
| `actor/code/dataset-4onq/pg_tis_clipfrac_neg_low` | 3.47969e-07 | 1.22783e-07 |
| `actor/code/dataset-4onq/pg_tis_clipfrac_pos_high` | 0 | 0 |
| `actor/code/dataset-4onq/pg_tis_clipfrac_pos_low` | 3.09957e-07 | 5.15522e-08 |
| `actor/code/dataset-4onq/ppo_kl` | 0 | 0 |
| `actor/code/dataset-bvg7/entropy_loss` | 0.448356 | 0.495861 |
| `actor/code/dataset-bvg7/pg_clipfrac` | 0 | 0 |
| `actor/code/dataset-bvg7/pg_loss` | 0.00837578 | 0.0209426 |
| `actor/code/dataset-bvg7/pg_tis_clipfrac` | 0.000196275 | 8.51546e-05 |
| `actor/code/dataset-bvg7/pg_tis_clipfrac_neg_high` | 6.17856e-06 | 4.87825e-06 |
| `actor/code/dataset-bvg7/pg_tis_clipfrac_neg_low` | 6.25796e-05 | 4.08689e-05 |
| `actor/code/dataset-bvg7/pg_tis_clipfrac_pos_high` | 1.33847e-05 | 4.199e-06 |
| `actor/code/dataset-bvg7/pg_tis_clipfrac_pos_low` | 0.000114132 | 3.52085e-05 |
| `actor/code/dataset-bvg7/ppo_kl` | 0 | 0 |
| `actor/code/dataset-dnpn/entropy_loss` | 0.402802 | 0.466003 |
| `actor/code/dataset-dnpn/pg_clipfrac` | 0 | 0 |
| `actor/code/dataset-dnpn/pg_loss` | -0.00157594 | -0.0036994 |
| `actor/code/dataset-dnpn/pg_tis_clipfrac` | 0.000219398 | 5.04744e-05 |
| `actor/code/dataset-dnpn/pg_tis_clipfrac_neg_high` | 1.06339e-05 | 1.96919e-06 |
| `actor/code/dataset-dnpn/pg_tis_clipfrac_neg_low` | 9.74568e-05 | 2.09011e-05 |
| `actor/code/dataset-dnpn/pg_tis_clipfrac_pos_high` | 1.05243e-05 | 2.25595e-06 |
| `actor/code/dataset-dnpn/pg_tis_clipfrac_pos_low` | 0.000100783 | 2.53481e-05 |
| `actor/code/dataset-dnpn/ppo_kl` | 0 | 0 |
| `actor/code/dataset-m1dt/entropy_loss` | 0.364915 | 0.378917 |
| `actor/code/dataset-m1dt/pg_clipfrac` | 0 | 0 |
| `actor/code/dataset-m1dt/pg_loss` | -0.00258994 | -0.00477525 |
| `actor/code/dataset-m1dt/pg_tis_clipfrac` | 0.000167346 | 0.000143717 |
| `actor/code/dataset-m1dt/pg_tis_clipfrac_neg_high` | 7.16389e-06 | 7.65378e-06 |
| `actor/code/dataset-m1dt/pg_tis_clipfrac_neg_low` | 5.91081e-05 | 6.71713e-05 |
| `actor/code/dataset-m1dt/pg_tis_clipfrac_pos_high` | 1.02395e-05 | 6.7107e-06 |
| `actor/code/dataset-m1dt/pg_tis_clipfrac_pos_low` | 9.08346e-05 | 6.21814e-05 |
| `actor/code/dataset-m1dt/ppo_kl` | 0 | 0 |
| `actor/code/dataset-obg8/entropy_loss` | 0.429536 | 0.499446 |
| `actor/code/dataset-obg8/pg_clipfrac` | 0 | 0 |
| `actor/code/dataset-obg8/pg_loss` | 0.00394274 | 0.00725478 |
| `actor/code/dataset-obg8/pg_tis_clipfrac` | 0.000474604 | 0.000104855 |
| `actor/code/dataset-obg8/pg_tis_clipfrac_neg_high` | 2.53094e-05 | 4.51757e-06 |
| `actor/code/dataset-obg8/pg_tis_clipfrac_neg_low` | 0.000217869 | 4.17776e-05 |
| `actor/code/dataset-obg8/pg_tis_clipfrac_pos_high` | 2.45943e-05 | 5.73136e-06 |
| `actor/code/dataset-obg8/pg_tis_clipfrac_pos_low` | 0.000206831 | 5.28285e-05 |
| `actor/code/dataset-obg8/ppo_kl` | 0 | 0 |
| `actor/code/dataset-sin0/entropy_loss` | 0.400575 | 0.450972 |
| `actor/code/dataset-sin0/pg_clipfrac` | 0 | 0 |
| `actor/code/dataset-sin0/pg_loss` | 0.0103585 | 0.0136248 |
| `actor/code/dataset-sin0/pg_tis_clipfrac` | 0.000220274 | 0.000148487 |
| `actor/code/dataset-sin0/pg_tis_clipfrac_neg_high` | 1.07973e-05 | 6.9237e-06 |
| `actor/code/dataset-sin0/pg_tis_clipfrac_neg_low` | 9.21246e-05 | 6.22518e-05 |
| `actor/code/dataset-sin0/pg_tis_clipfrac_pos_high` | 1.19164e-05 | 7.81279e-06 |
| `actor/code/dataset-sin0/pg_tis_clipfrac_pos_low` | 0.000105436 | 7.14987e-05 |
| `actor/code/dataset-sin0/ppo_kl` | 0 | 0 |
| `actor/code/dataset-ta4j/entropy_loss` | 0.424008 | 0.501919 |
| `actor/code/dataset-ta4j/pg_clipfrac` | 0 | 0 |
| `actor/code/dataset-ta4j/pg_loss` | 0.0120959 | 0.00352017 |
| `actor/code/dataset-ta4j/pg_tis_clipfrac` | 0.000335649 | 0.000127204 |
| `actor/code/dataset-ta4j/pg_tis_clipfrac_neg_high` | 1.22511e-05 | 8.04188e-06 |
| `actor/code/dataset-ta4j/pg_tis_clipfrac_neg_low` | 0.000105493 | 6.69067e-05 |
| `actor/code/dataset-ta4j/pg_tis_clipfrac_pos_high` | 2.288e-05 | 5.3098e-06 |
| `actor/code/dataset-ta4j/pg_tis_clipfrac_pos_low` | 0.000195025 | 4.69452e-05 |
| `actor/code/dataset-ta4j/ppo_kl` | 0 | 0 |
| `actor/code/dataset-v7yx/entropy_loss` | 0.466763 | 0.475587 |
| `actor/code/dataset-v7yx/pg_clipfrac` | 0 | 0 |
| `actor/code/dataset-v7yx/pg_loss` | 0.010215 | -0.00351058 |
| `actor/code/dataset-v7yx/pg_tis_clipfrac` | 0.00014907 | 0.000136065 |
| `actor/code/dataset-v7yx/pg_tis_clipfrac_neg_high` | 8.04989e-06 | 8.28053e-06 |
| `actor/code/dataset-v7yx/pg_tis_clipfrac_neg_low` | 7.25607e-05 | 7.03542e-05 |
| `actor/code/dataset-v7yx/pg_tis_clipfrac_pos_high` | 6.54897e-06 | 4.29312e-06 |
| `actor/code/dataset-v7yx/pg_tis_clipfrac_pos_low` | 6.19102e-05 | 5.31369e-05 |
| `actor/code/dataset-v7yx/ppo_kl` | 0 | 0 |
| `actor/code/dataset-x7wh/entropy_loss` | 0.425948 | 0.492145 |
| `actor/code/dataset-x7wh/pg_clipfrac` | 0 | 0 |
| `actor/code/dataset-x7wh/pg_loss` | -0.00146034 | 0.000576223 |
| `actor/code/dataset-x7wh/pg_tis_clipfrac` | 0.000434681 | 0.000112303 |
| `actor/code/dataset-x7wh/pg_tis_clipfrac_neg_high` | 1.98275e-05 | 4.45555e-06 |
| `actor/code/dataset-x7wh/pg_tis_clipfrac_neg_low` | 0.000173646 | 4.09789e-05 |
| `actor/code/dataset-x7wh/pg_tis_clipfrac_pos_high` | 2.5795e-05 | 6.51065e-06 |
| `actor/code/dataset-x7wh/pg_tis_clipfrac_pos_low` | 0.000215412 | 6.03579e-05 |
| `actor/code/dataset-x7wh/ppo_kl` | 0 | 0 |
| `actor/code/dataset-yfch/entropy_loss` | 0.45824 | 0.449691 |
| `actor/code/dataset-yfch/pg_clipfrac` | 0 | 0 |
| `actor/code/dataset-yfch/pg_loss` | -0.00858998 | 0.00888059 |
| `actor/code/dataset-yfch/pg_tis_clipfrac` | 0.00100482 | 0.00219659 |
| `actor/code/dataset-yfch/pg_tis_clipfrac_neg_high` | 3.75879e-05 | 0.00010108 |
| `actor/code/dataset-yfch/pg_tis_clipfrac_neg_low` | 0.000297293 | 0.00084897 |
| `actor/code/dataset-yfch/pg_tis_clipfrac_pos_high` | 7.68421e-05 | 0.000133469 |
| `actor/code/dataset-yfch/pg_tis_clipfrac_pos_low` | 0.000593097 | 0.00111308 |
| `actor/code/dataset-yfch/ppo_kl` | 0 | 0 |
| `actor/code/dataset-zg6q/entropy_loss` | 0.412787 | 0.454137 |
| `actor/code/dataset-zg6q/pg_clipfrac` | 0 | 0 |
| `actor/code/dataset-zg6q/pg_loss` | 0.00317278 | 0.0171964 |
| `actor/code/dataset-zg6q/pg_tis_clipfrac` | 0.000112585 | 5.11484e-05 |
| `actor/code/dataset-zg6q/pg_tis_clipfrac_neg_high` | 4.73158e-06 | 2.77644e-06 |
| `actor/code/dataset-zg6q/pg_tis_clipfrac_neg_low` | 3.99325e-05 | 2.46944e-05 |
| `actor/code/dataset-zg6q/pg_tis_clipfrac_pos_high` | 6.93567e-06 | 2.1959e-06 |
| `actor/code/dataset-zg6q/pg_tis_clipfrac_pos_low` | 6.09852e-05 | 2.14817e-05 |
| `actor/code/dataset-zg6q/ppo_kl` | 0 | 0 |
| `actor/cyber/dataset-9aui/entropy_loss` | 0.483004 | 0.470906 |
| `actor/cyber/dataset-9aui/pg_clipfrac` | 0 | 0 |
| `actor/cyber/dataset-9aui/pg_loss` | 0.0889505 | 0.13735 |
| `actor/cyber/dataset-9aui/pg_tis_clipfrac` | 0.00052472 | 0.000581264 |
| `actor/cyber/dataset-9aui/pg_tis_clipfrac_neg_high` | 4.24284e-05 | 4.88706e-05 |
| `actor/cyber/dataset-9aui/pg_tis_clipfrac_neg_low` | 0.000330206 | 0.000401878 |
| `actor/cyber/dataset-9aui/pg_tis_clipfrac_pos_high` | 1.69792e-05 | 1.37268e-05 |
| `actor/cyber/dataset-9aui/pg_tis_clipfrac_pos_low` | 0.000135106 | 0.000116788 |
| `actor/cyber/dataset-9aui/ppo_kl` | 0 | 0 |
| `actor/entropy_loss` | 0.392207 | 0.431725 |
| `actor/general/dataset-1doa/entropy_loss` | 0.208533 | 0.247515 |
| `actor/general/dataset-1doa/pg_clipfrac` | 0 | 0 |
| `actor/general/dataset-1doa/pg_loss` | 0.013384 | -0.0105417 |
| `actor/general/dataset-1doa/pg_tis_clipfrac` | 3.92752e-05 | 5.48559e-06 |
| `actor/general/dataset-1doa/pg_tis_clipfrac_neg_high` | 2.81525e-06 | 2.43418e-07 |
| `actor/general/dataset-1doa/pg_tis_clipfrac_neg_low` | 2.83658e-05 | 1.72639e-06 |
| `actor/general/dataset-1doa/pg_tis_clipfrac_pos_high` | 6.7044e-07 | 4.3729e-08 |
| `actor/general/dataset-1doa/pg_tis_clipfrac_pos_low` | 7.42367e-06 | 3.47206e-06 |
| `actor/general/dataset-1doa/ppo_kl` | 0 | 0 |
| `actor/general/dataset-5610/entropy_loss` | 0.372195 | 0.411544 |
| `actor/general/dataset-5610/pg_clipfrac` | 0 | 0 |
| `actor/general/dataset-5610/pg_loss` | 0.00647559 | 0.00908666 |
| `actor/general/dataset-5610/pg_tis_clipfrac` | 0.000230973 | 3.37319e-05 |
| `actor/general/dataset-5610/pg_tis_clipfrac_neg_high` | 1.40204e-05 | 1.31712e-06 |
| `actor/general/dataset-5610/pg_tis_clipfrac_neg_low` | 0.00012248 | 1.57607e-05 |
| `actor/general/dataset-5610/pg_tis_clipfrac_pos_high` | 9.70017e-06 | 1.05267e-06 |
| `actor/general/dataset-5610/pg_tis_clipfrac_pos_low` | 8.47719e-05 | 1.56014e-05 |
| `actor/general/dataset-5610/ppo_kl` | 0 | 0 |
| `actor/general/dataset-epqd/entropy_loss` | 0.286687 | 0.331667 |
| `actor/general/dataset-epqd/pg_clipfrac` | 0 | 0 |
| `actor/general/dataset-epqd/pg_loss` | 0.00703724 | 0.0136884 |
| `actor/general/dataset-epqd/pg_tis_clipfrac` | 2.37321e-05 | 9.65733e-06 |
| `actor/general/dataset-epqd/pg_tis_clipfrac_neg_high` | 1.39989e-06 | 1.06821e-07 |
| `actor/general/dataset-epqd/pg_tis_clipfrac_neg_low` | 1.17603e-05 | 2.45455e-06 |
| `actor/general/dataset-epqd/pg_tis_clipfrac_pos_high` | 8.51012e-07 | 4.01144e-07 |
| `actor/general/dataset-epqd/pg_tis_clipfrac_pos_low` | 9.72091e-06 | 6.69481e-06 |
| `actor/general/dataset-epqd/ppo_kl` | 0 | 0 |
| `actor/general/dataset-trla/entropy_loss` | 0.410851 | 0.487338 |
| `actor/general/dataset-trla/pg_clipfrac` | 0 | 0 |
| `actor/general/dataset-trla/pg_loss` | 0.0120946 | 0.00825078 |
| `actor/general/dataset-trla/pg_tis_clipfrac` | 0.000100652 | 5.10783e-05 |
| `actor/general/dataset-trla/pg_tis_clipfrac_neg_high` | 5.18933e-06 | 2.24716e-06 |
| `actor/general/dataset-trla/pg_tis_clipfrac_neg_low` | 5.29813e-05 | 2.08731e-05 |
| `actor/general/dataset-trla/pg_tis_clipfrac_pos_high` | 4.85396e-06 | 2.60283e-06 |
| `actor/general/dataset-trla/pg_tis_clipfrac_pos_low` | 3.76274e-05 | 2.53552e-05 |
| `actor/general/dataset-trla/ppo_kl` | 0 | 0 |
| `actor/grad_norm` | 0.00543666 | 0.00550012 |
| `actor/lr` | 3e-06 | 3e-06 |
| `actor/num_zeros_in_grad` | 5.97391e+08 | 4.09105e+08 |
| `actor/num_zeros_in_grad_encoders` | 2.94705e+08 | — |
| `actor/num_zeros_in_grad_moe` | 4421 | 0 |
| `actor/num_zeros_in_grad_mtp` | 0 | 0 |
| `actor/num_zeros_in_grad_nonmoe` | 430097 | 0 |
| `actor/num_zeros_in_grad_vocab` | 3.02251e+08 | 0 |
| `actor/pg_clipfrac` | 0 | 0 |
| `actor/pg_loss` | 0.00617481 | 0.0112836 |
| `actor/pg_tis_clipfrac` | 0.000254096 | 0.000181866 |
| `actor/pg_tis_clipfrac_neg_high` | 1.21758e-05 | 9.33558e-06 |
| `actor/pg_tis_clipfrac_neg_low` | 0.000103295 | 8.04907e-05 |
| `actor/pg_tis_clipfrac_pos_high` | 1.46636e-05 | 9.31854e-06 |
| `actor/pg_tis_clipfrac_pos_low` | 0.000123962 | 8.27217e-05 |
| `actor/ppo_kl` | 0 | 0 |
| `actor/skipped_iter` | 0 | 0 |
| `actor/update_skipped` | 0 | 0 |
| `actor/update_successful` | 1 | 1 |
| `actor/updated_iter` | 1 | 1 |
| `actor/visual/dataset-053e/entropy_loss` | 0.285903 | 0.293213 |
| `actor/visual/dataset-053e/pg_clipfrac` | 0 | 0 |
| `actor/visual/dataset-053e/pg_loss` | -0.00881366 | -0.00879627 |
| `actor/visual/dataset-053e/pg_tis_clipfrac` | 0.00028918 | 9.0464e-05 |
| `actor/visual/dataset-053e/pg_tis_clipfrac_neg_high` | 1.41658e-05 | 4.47829e-06 |
| `actor/visual/dataset-053e/pg_tis_clipfrac_neg_low` | 0.00012333 | 4.31262e-05 |
| `actor/visual/dataset-053e/pg_tis_clipfrac_pos_high` | 1.63408e-05 | 4.14376e-06 |
| `actor/visual/dataset-053e/pg_tis_clipfrac_pos_low` | 0.000135344 | 3.87157e-05 |
| `actor/visual/dataset-053e/ppo_kl` | 0 | 0 |
| `actor/visual/dataset-gtav/entropy_loss` | 0.269832 | 0.275766 |
| `actor/visual/dataset-gtav/pg_clipfrac` | 0 | 0 |
| `actor/visual/dataset-gtav/pg_loss` | 0.00233887 | -0.00155298 |
| `actor/visual/dataset-gtav/pg_tis_clipfrac` | 1.68155e-05 | 1.89001e-05 |
| `actor/visual/dataset-gtav/pg_tis_clipfrac_neg_high` | 8.53798e-07 | 8.49996e-07 |
| `actor/visual/dataset-gtav/pg_tis_clipfrac_neg_low` | 7.27606e-06 | 7.7187e-06 |
| `actor/visual/dataset-gtav/pg_tis_clipfrac_pos_high` | 6.71682e-07 | 1.20276e-06 |
| `actor/visual/dataset-gtav/pg_tis_clipfrac_pos_low` | 8.01396e-06 | 9.12868e-06 |
| `actor/visual/dataset-gtav/ppo_kl` | 0 | 0 |
| `actor/visual/dataset-jzd3/entropy_loss` | 0.277459 | 0.279251 |
| `actor/visual/dataset-jzd3/pg_clipfrac` | 0 | 0 |
| `actor/visual/dataset-jzd3/pg_loss` | -0.0045478 | 0.00207201 |
| `actor/visual/dataset-jzd3/pg_tis_clipfrac` | 3.93814e-05 | 2.21495e-05 |
| `actor/visual/dataset-jzd3/pg_tis_clipfrac_neg_high` | 1.8965e-06 | 9.19074e-07 |
| `actor/visual/dataset-jzd3/pg_tis_clipfrac_neg_low` | 1.49544e-05 | 1.1249e-05 |
| `actor/visual/dataset-jzd3/pg_tis_clipfrac_pos_high` | 2.57977e-06 | 6.79691e-07 |
| `actor/visual/dataset-jzd3/pg_tis_clipfrac_pos_low` | 1.99508e-05 | 9.3018e-06 |
| `actor/visual/dataset-jzd3/ppo_kl` | 0 | 0 |
| `actor/visual/dataset-ol8x/entropy_loss` | 0.289323 | 0.290317 |
| `actor/visual/dataset-ol8x/pg_clipfrac` | 0 | 0 |
| `actor/visual/dataset-ol8x/pg_loss` | -0.00361129 | -0.00142094 |
| `actor/visual/dataset-ol8x/pg_tis_clipfrac` | 0.000236953 | 6.20418e-05 |
| `actor/visual/dataset-ol8x/pg_tis_clipfrac_neg_high` | 1.16323e-05 | 2.40601e-06 |
| `actor/visual/dataset-ol8x/pg_tis_clipfrac_neg_low` | 9.29053e-05 | 2.30323e-05 |
| `actor/visual/dataset-ol8x/pg_tis_clipfrac_pos_high` | 1.40812e-05 | 2.54902e-06 |
| `actor/visual/dataset-ol8x/pg_tis_clipfrac_pos_low` | 0.000118335 | 3.40544e-05 |
| `actor/visual/dataset-ol8x/ppo_kl` | 0 | 0 |
| `actor/visual/dataset-pt5v/entropy_loss` | 0.279123 | 0.319157 |
| `actor/visual/dataset-pt5v/pg_clipfrac` | 0 | 0 |
| `actor/visual/dataset-pt5v/pg_loss` | -0.0126329 | -0.0290916 |
| `actor/visual/dataset-pt5v/pg_tis_clipfrac` | 0.000174918 | 8.00435e-05 |
| `actor/visual/dataset-pt5v/pg_tis_clipfrac_neg_high` | 2.24904e-06 | 2.03667e-06 |
| `actor/visual/dataset-pt5v/pg_tis_clipfrac_neg_low` | 1.94308e-05 | 2.40261e-05 |
| `actor/visual/dataset-pt5v/pg_tis_clipfrac_pos_high` | 1.56634e-05 | 5.31806e-06 |
| `actor/visual/dataset-pt5v/pg_tis_clipfrac_pos_low` | 0.000137575 | 4.86627e-05 |
| `actor/visual/dataset-pt5v/ppo_kl` | 0 | 0 |
| `actor/visual/dataset-ve5o/entropy_loss` | 0.382321 | 0.382291 |
| `actor/visual/dataset-ve5o/pg_clipfrac` | 0 | 0 |
| `actor/visual/dataset-ve5o/pg_loss` | -0.00569187 | -0.0092348 |
| `actor/visual/dataset-ve5o/pg_tis_clipfrac` | 0.000346614 | 0.000203845 |
| `actor/visual/dataset-ve5o/pg_tis_clipfrac_neg_high` | 8.95242e-06 | 4.3369e-06 |
| `actor/visual/dataset-ve5o/pg_tis_clipfrac_neg_low` | 7.9728e-05 | 3.83719e-05 |
| `actor/visual/dataset-ve5o/pg_tis_clipfrac_pos_high` | 2.54704e-05 | 1.60909e-05 |
| `actor/visual/dataset-ve5o/pg_tis_clipfrac_pos_low` | 0.000232463 | 0.000145045 |
| `actor/visual/dataset-ve5o/ppo_kl` | 0 | 0 |

## critic · 324

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `critic/advantages/max` | 1.32344 | 1.1543 |
| `critic/advantages/mean` | -0.0108076 | -0.0198392 |
| `critic/advantages/min` | -0.9375 | -1.47134 |
| `critic/agentic/advantages/max` | 1.32344 | 1.1543 |
| `critic/agentic/advantages/mean` | -0.0112049 | -0.0203594 |
| `critic/agentic/advantages/min` | -0.930868 | -1.47134 |
| `critic/agentic/returns/max` | 1.32344 | 1.1543 |
| `critic/agentic/returns/mean` | -0.0112049 | -0.0203594 |
| `critic/agentic/returns/min` | -0.930868 | -1.47134 |
| `critic/agentic/rewards/max` | 1 | 1 |
| `critic/agentic/rewards/mean` | 0.592068 | 0.575407 |
| `critic/agentic/rewards/min` | -0.237846 | -0.8 |
| `critic/agentic/score/max` | 1 | 1 |
| `critic/agentic/score/mean` | 0.592068 | 0.575407 |
| `critic/agentic/score/min` | -0.237846 | -0.8 |
| `critic/chat/dataset-8kb6/advantages/max` | 0.9375 | 0.9375 |
| `critic/chat/dataset-8kb6/advantages/mean` | -0.0287924 | -0.0142691 |
| `critic/chat/dataset-8kb6/advantages/min` | -0.859449 | -0.898159 |
| `critic/chat/dataset-8kb6/returns/max` | 0.9375 | 0.9375 |
| `critic/chat/dataset-8kb6/returns/mean` | -0.0287924 | -0.0142691 |
| `critic/chat/dataset-8kb6/returns/min` | -0.859449 | -0.898159 |
| `critic/chat/dataset-8kb6/rewards/max` | 1 | 1 |
| `critic/chat/dataset-8kb6/rewards/mean` | 0.364276 | 0.348579 |
| `critic/chat/dataset-8kb6/rewards/min` | 0 | 0 |
| `critic/chat/dataset-8kb6/score/max` | 1 | 1 |
| `critic/chat/dataset-8kb6/score/mean` | 0.364276 | 0.348579 |
| `critic/chat/dataset-8kb6/score/min` | 0 | 0 |
| `critic/chat/dataset-eup7/advantages/max` | 0.9375 | 0.875 |
| `critic/chat/dataset-eup7/advantages/mean` | -0.0202086 | -0.0821976 |
| `critic/chat/dataset-eup7/advantages/min` | -0.921959 | -0.922486 |
| `critic/chat/dataset-eup7/returns/max` | 0.9375 | 0.875 |
| `critic/chat/dataset-eup7/returns/mean` | -0.0202086 | -0.0821976 |
| `critic/chat/dataset-eup7/returns/min` | -0.921959 | -0.922486 |
| `critic/chat/dataset-eup7/rewards/max` | 1 | 1 |
| `critic/chat/dataset-eup7/rewards/mean` | 0.484088 | 0.566966 |
| `critic/chat/dataset-eup7/rewards/min` | 0 | 0 |
| `critic/chat/dataset-eup7/score/max` | 1 | 1 |
| `critic/chat/dataset-eup7/score/mean` | 0.484088 | 0.566966 |
| `critic/chat/dataset-eup7/score/min` | 0 | 0 |
| `critic/chat/dataset-lm3t/advantages/max` | 0.9375 | 0.9375 |
| `critic/chat/dataset-lm3t/advantages/mean` | 0.0334538 | -0.0663004 |
| `critic/chat/dataset-lm3t/advantages/min` | -0.926303 | -0.814802 |
| `critic/chat/dataset-lm3t/returns/max` | 0.9375 | 0.9375 |
| `critic/chat/dataset-lm3t/returns/mean` | 0.0334538 | -0.0663004 |
| `critic/chat/dataset-lm3t/returns/min` | -0.926303 | -0.814802 |
| `critic/chat/dataset-lm3t/rewards/max` | 1 | 1 |
| `critic/chat/dataset-lm3t/rewards/mean` | 0.372288 | 0.321169 |
| `critic/chat/dataset-lm3t/rewards/min` | 0 | 0 |
| `critic/chat/dataset-lm3t/score/max` | 1 | 1 |
| `critic/chat/dataset-lm3t/score/mean` | 0.372288 | 0.321169 |
| `critic/chat/dataset-lm3t/score/min` | 0 | 0 |
| `critic/code/dataset-4onq/advantages/max` | 0.875 | 0.9375 |
| `critic/code/dataset-4onq/advantages/mean` | -0.00811409 | -0.0213024 |
| `critic/code/dataset-4onq/advantages/min` | -0.928544 | -0.922735 |
| `critic/code/dataset-4onq/returns/max` | 0.875 | 0.9375 |
| `critic/code/dataset-4onq/returns/mean` | -0.00811409 | -0.0213024 |
| `critic/code/dataset-4onq/returns/min` | -0.928544 | -0.922735 |
| `critic/code/dataset-4onq/rewards/max` | 1 | 1 |
| `critic/code/dataset-4onq/rewards/mean` | 0.569255 | 0.489573 |
| `critic/code/dataset-4onq/rewards/min` | 0 | 0 |
| `critic/code/dataset-4onq/score/max` | 1 | 1 |
| `critic/code/dataset-4onq/score/mean` | 0.569255 | 0.489573 |
| `critic/code/dataset-4onq/score/min` | 0 | 0 |
| `critic/code/dataset-bvg7/advantages/max` | 0.945946 | 0.9375 |
| `critic/code/dataset-bvg7/advantages/mean` | -0.00965955 | -0.0345297 |
| `critic/code/dataset-bvg7/advantages/min` | -0.927117 | -0.920633 |
| `critic/code/dataset-bvg7/returns/max` | 0.945946 | 0.9375 |
| `critic/code/dataset-bvg7/returns/mean` | -0.00965955 | -0.0345297 |
| `critic/code/dataset-bvg7/returns/min` | -0.927117 | -0.920633 |
| `critic/code/dataset-bvg7/rewards/max` | 1 | 1 |
| `critic/code/dataset-bvg7/rewards/mean` | 0.627437 | 0.578861 |
| `critic/code/dataset-bvg7/rewards/min` | 0 | 0 |
| `critic/code/dataset-bvg7/score/max` | 1 | 1 |
| `critic/code/dataset-bvg7/score/mean` | 0.627437 | 0.578861 |
| `critic/code/dataset-bvg7/score/min` | 0 | 0 |
| `critic/code/dataset-dnpn/advantages/max` | 1.04348 | 0.945946 |
| `critic/code/dataset-dnpn/advantages/mean` | 0.00426381 | 0.00299899 |
| `critic/code/dataset-dnpn/advantages/min` | -0.926119 | -0.913178 |
| `critic/code/dataset-dnpn/returns/max` | 1.04348 | 0.945946 |
| `critic/code/dataset-dnpn/returns/mean` | 0.00426381 | 0.00299899 |
| `critic/code/dataset-dnpn/returns/min` | -0.926119 | -0.913178 |
| `critic/code/dataset-dnpn/rewards/max` | 1 | 1 |
| `critic/code/dataset-dnpn/rewards/mean` | 0.576868 | 0.574903 |
| `critic/code/dataset-dnpn/rewards/min` | 0 | 0 |
| `critic/code/dataset-dnpn/score/max` | 1 | 1 |
| `critic/code/dataset-dnpn/score/mean` | 0.576868 | 0.574903 |
| `critic/code/dataset-dnpn/score/min` | 0 | 0 |
| `critic/code/dataset-m1dt/advantages/max` | 0.772059 | 0.834559 |
| `critic/code/dataset-m1dt/advantages/mean` | 9.9299e-05 | 0.00421784 |
| `critic/code/dataset-m1dt/advantages/min` | -0.798177 | -0.857721 |
| `critic/code/dataset-m1dt/returns/max` | 0.772059 | 0.834559 |
| `critic/code/dataset-m1dt/returns/mean` | 9.9299e-05 | 0.00421784 |
| `critic/code/dataset-m1dt/returns/min` | -0.798177 | -0.857721 |
| `critic/code/dataset-m1dt/rewards/max` | 1 | 1 |
| `critic/code/dataset-m1dt/rewards/mean` | 0.634083 | 0.590303 |
| `critic/code/dataset-m1dt/rewards/min` | 0 | 0 |
| `critic/code/dataset-m1dt/score/max` | 1 | 1 |
| `critic/code/dataset-m1dt/score/mean` | 0.634083 | 0.590303 |
| `critic/code/dataset-m1dt/score/min` | 0 | 0 |
| `critic/code/dataset-obg8/advantages/max` | 1.32344 | 1.08333 |
| `critic/code/dataset-obg8/advantages/mean` | -0.0038131 | -0.00713806 |
| `critic/code/dataset-obg8/advantages/min` | -0.925511 | -0.926285 |
| `critic/code/dataset-obg8/returns/max` | 1.32344 | 1.08333 |
| `critic/code/dataset-obg8/returns/mean` | -0.0038131 | -0.00713806 |
| `critic/code/dataset-obg8/returns/min` | -0.925511 | -0.926285 |
| `critic/code/dataset-obg8/rewards/max` | 1 | 1 |
| `critic/code/dataset-obg8/rewards/mean` | 0.527397 | 0.537569 |
| `critic/code/dataset-obg8/rewards/min` | 0 | 0 |
| `critic/code/dataset-obg8/score/max` | 1 | 1 |
| `critic/code/dataset-obg8/score/mean` | 0.527397 | 0.537569 |
| `critic/code/dataset-obg8/score/min` | 0 | 0 |
| `critic/code/dataset-sin0/advantages/max` | 0.952381 | 1.1543 |
| `critic/code/dataset-sin0/advantages/mean` | -0.00813319 | -0.0131203 |
| `critic/code/dataset-sin0/advantages/min` | -0.929642 | -0.928843 |
| `critic/code/dataset-sin0/returns/max` | 0.952381 | 1.1543 |
| `critic/code/dataset-sin0/returns/mean` | -0.00813319 | -0.0131203 |
| `critic/code/dataset-sin0/returns/min` | -0.929642 | -0.928843 |
| `critic/code/dataset-sin0/rewards/max` | 1 | 1 |
| `critic/code/dataset-sin0/rewards/mean` | 0.59631 | 0.590938 |
| `critic/code/dataset-sin0/rewards/min` | 0 | -0.0761594 |
| `critic/code/dataset-sin0/score/max` | 1 | 1 |
| `critic/code/dataset-sin0/score/mean` | 0.59631 | 0.590938 |
| `critic/code/dataset-sin0/score/min` | 0 | -0.0761594 |
| `critic/code/dataset-ta4j/advantages/max` | 1.08333 | 1.04348 |
| `critic/code/dataset-ta4j/advantages/mean` | -0.0106478 | -0.00331673 |
| `critic/code/dataset-ta4j/advantages/min` | -0.918937 | -0.919499 |
| `critic/code/dataset-ta4j/returns/max` | 1.08333 | 1.04348 |
| `critic/code/dataset-ta4j/returns/mean` | -0.0106478 | -0.00331673 |
| `critic/code/dataset-ta4j/returns/min` | -0.918937 | -0.919499 |
| `critic/code/dataset-ta4j/rewards/max` | 1 | 1 |
| `critic/code/dataset-ta4j/rewards/mean` | 0.586309 | 0.537378 |
| `critic/code/dataset-ta4j/rewards/min` | 0 | 0 |
| `critic/code/dataset-ta4j/score/max` | 1 | 1 |
| `critic/code/dataset-ta4j/score/mean` | 0.586309 | 0.537378 |
| `critic/code/dataset-ta4j/score/min` | 0 | 0 |
| `critic/code/dataset-v7yx/advantages/max` | 1.12617 | 0.945946 |
| `critic/code/dataset-v7yx/advantages/mean` | 9.22041e-05 | -0.00265586 |
| `critic/code/dataset-v7yx/advantages/min` | -0.922119 | -0.906679 |
| `critic/code/dataset-v7yx/returns/max` | 1.12617 | 0.945946 |
| `critic/code/dataset-v7yx/returns/mean` | 9.22041e-05 | -0.00265586 |
| `critic/code/dataset-v7yx/returns/min` | -0.922119 | -0.906679 |
| `critic/code/dataset-v7yx/rewards/max` | 1 | 1 |
| `critic/code/dataset-v7yx/rewards/mean` | 0.560319 | 0.554721 |
| `critic/code/dataset-v7yx/rewards/min` | 0 | 0 |
| `critic/code/dataset-v7yx/score/max` | 1 | 1 |
| `critic/code/dataset-v7yx/score/mean` | 0.560319 | 0.554721 |
| `critic/code/dataset-v7yx/score/min` | 0 | 0 |
| `critic/code/dataset-x7wh/advantages/max` | 1.08333 | 0.982143 |
| `critic/code/dataset-x7wh/advantages/mean` | 0.00317077 | -0.00340872 |
| `critic/code/dataset-x7wh/advantages/min` | -0.930868 | -0.927328 |
| `critic/code/dataset-x7wh/returns/max` | 1.08333 | 0.982143 |
| `critic/code/dataset-x7wh/returns/mean` | 0.00317077 | -0.00340872 |
| `critic/code/dataset-x7wh/returns/min` | -0.930868 | -0.927328 |
| `critic/code/dataset-x7wh/rewards/max` | 1 | 1 |
| `critic/code/dataset-x7wh/rewards/mean` | 0.591731 | 0.551868 |
| `critic/code/dataset-x7wh/rewards/min` | 0 | 0 |
| `critic/code/dataset-x7wh/score/max` | 1 | 1 |
| `critic/code/dataset-x7wh/score/mean` | 0.591731 | 0.551868 |
| `critic/code/dataset-x7wh/score/min` | 0 | 0 |
| `critic/code/dataset-yfch/advantages/max` | 0.760144 | 0.668944 |
| `critic/code/dataset-yfch/advantages/mean` | 0.00739922 | -0.00562471 |
| `critic/code/dataset-yfch/advantages/min` | -0.915506 | -1.23787 |
| `critic/code/dataset-yfch/returns/max` | 0.760144 | 0.668944 |
| `critic/code/dataset-yfch/returns/mean` | 0.00739922 | -0.00562471 |
| `critic/code/dataset-yfch/returns/min` | -0.915506 | -1.23787 |
| `critic/code/dataset-yfch/rewards/max` | 1 | 1 |
| `critic/code/dataset-yfch/rewards/mean` | 0.669231 | 0.555773 |
| `critic/code/dataset-yfch/rewards/min` | 0 | -0.7537 |
| `critic/code/dataset-yfch/score/max` | 1 | 1 |
| `critic/code/dataset-yfch/score/mean` | 0.669231 | 0.555773 |
| `critic/code/dataset-yfch/score/min` | 0 | -0.7537 |
| `critic/code/dataset-zg6q/advantages/max` | 1.12617 | 1.12246 |
| `critic/code/dataset-zg6q/advantages/mean` | -0.0085193 | -0.0222294 |
| `critic/code/dataset-zg6q/advantages/min` | -0.920357 | -1.47134 |
| `critic/code/dataset-zg6q/returns/max` | 1.12617 | 1.12246 |
| `critic/code/dataset-zg6q/returns/mean` | -0.0085193 | -0.0222294 |
| `critic/code/dataset-zg6q/returns/min` | -0.920357 | -1.47134 |
| `critic/code/dataset-zg6q/rewards/max` | 1 | 1 |
| `critic/code/dataset-zg6q/rewards/mean` | 0.600653 | 0.548108 |
| `critic/code/dataset-zg6q/rewards/min` | 0 | -0.792815 |
| `critic/code/dataset-zg6q/score/max` | 1 | 1 |
| `critic/code/dataset-zg6q/score/mean` | 0.600653 | 0.548108 |
| `critic/code/dataset-zg6q/score/min` | 0 | -0.792815 |
| `critic/cyber/dataset-9aui/advantages/max` | 0.9375 | 0.957835 |
| `critic/cyber/dataset-9aui/advantages/mean` | -0.0869287 | -0.165738 |
| `critic/cyber/dataset-9aui/advantages/min` | -0.916415 | -1.22455 |
| `critic/cyber/dataset-9aui/returns/max` | 0.9375 | 0.957835 |
| `critic/cyber/dataset-9aui/returns/mean` | -0.0869287 | -0.165738 |
| `critic/cyber/dataset-9aui/returns/min` | -0.916415 | -1.22455 |
| `critic/cyber/dataset-9aui/rewards/max` | 1 | 1 |
| `critic/cyber/dataset-9aui/rewards/mean` | 0.636038 | 0.530695 |
| `critic/cyber/dataset-9aui/rewards/min` | -0.237846 | -0.8 |
| `critic/cyber/dataset-9aui/score/max` | 1 | 1 |
| `critic/cyber/dataset-9aui/score/mean` | 0.636038 | 0.530695 |
| `critic/cyber/dataset-9aui/score/min` | -0.237846 | -0.8 |
| `critic/general/dataset-1doa/advantages/max` | 0.9375 | 0.9375 |
| `critic/general/dataset-1doa/advantages/mean` | -0.0148817 | 0.0137946 |
| `critic/general/dataset-1doa/advantages/min` | -0.92406 | -0.915247 |
| `critic/general/dataset-1doa/returns/max` | 0.9375 | 0.9375 |
| `critic/general/dataset-1doa/returns/mean` | -0.0148817 | 0.0137946 |
| `critic/general/dataset-1doa/returns/min` | -0.92406 | -0.915247 |
| `critic/general/dataset-1doa/rewards/max` | 1 | 1 |
| `critic/general/dataset-1doa/rewards/mean` | 0.437055 | 0.55713 |
| `critic/general/dataset-1doa/rewards/min` | 0 | 0 |
| `critic/general/dataset-1doa/score/max` | 1 | 1 |
| `critic/general/dataset-1doa/score/mean` | 0.437055 | 0.55713 |
| `critic/general/dataset-1doa/score/min` | 0 | 0 |
| `critic/general/dataset-5610/advantages/max` | 0.9375 | 0.9375 |
| `critic/general/dataset-5610/advantages/mean` | 0.00312287 | -0.00565096 |
| `critic/general/dataset-5610/advantages/min` | -0.869143 | -0.907684 |
| `critic/general/dataset-5610/returns/max` | 0.9375 | 0.9375 |
| `critic/general/dataset-5610/returns/mean` | 0.00312287 | -0.00565096 |
| `critic/general/dataset-5610/returns/min` | -0.869143 | -0.907684 |
| `critic/general/dataset-5610/rewards/max` | 1 | 1 |
| `critic/general/dataset-5610/rewards/mean` | 0.461521 | 0.507453 |
| `critic/general/dataset-5610/rewards/min` | 0 | 0 |
| `critic/general/dataset-5610/score/max` | 1 | 1 |
| `critic/general/dataset-5610/score/mean` | 0.461521 | 0.507453 |
| `critic/general/dataset-5610/score/min` | 0 | 0 |
| `critic/general/dataset-epqd/advantages/max` | 0.9375 | 0.9375 |
| `critic/general/dataset-epqd/advantages/mean` | -0.0161635 | -0.0175885 |
| `critic/general/dataset-epqd/advantages/min` | -0.924951 | -0.923188 |
| `critic/general/dataset-epqd/returns/max` | 0.9375 | 0.9375 |
| `critic/general/dataset-epqd/returns/mean` | -0.0161635 | -0.0175885 |
| `critic/general/dataset-epqd/returns/min` | -0.924951 | -0.923188 |
| `critic/general/dataset-epqd/rewards/max` | 1 | 1 |
| `critic/general/dataset-epqd/rewards/mean` | 0.591047 | 0.664104 |
| `critic/general/dataset-epqd/rewards/min` | 0 | 0 |
| `critic/general/dataset-epqd/score/max` | 1 | 1 |
| `critic/general/dataset-epqd/score/mean` | 0.591047 | 0.664104 |
| `critic/general/dataset-epqd/score/min` | 0 | 0 |
| `critic/general/dataset-trla/advantages/max` | 0.9375 | 0.9375 |
| `critic/general/dataset-trla/advantages/mean` | -0.0181186 | -0.0130614 |
| `critic/general/dataset-trla/advantages/min` | -0.917865 | -0.922886 |
| `critic/general/dataset-trla/returns/max` | 0.9375 | 0.9375 |
| `critic/general/dataset-trla/returns/mean` | -0.0181186 | -0.0130614 |
| `critic/general/dataset-trla/returns/min` | -0.917865 | -0.922886 |
| `critic/general/dataset-trla/rewards/max` | 1 | 1 |
| `critic/general/dataset-trla/rewards/mean` | 0.449766 | 0.520708 |
| `critic/general/dataset-trla/rewards/min` | 0 | -0.432242 |
| `critic/general/dataset-trla/score/max` | 1 | 1 |
| `critic/general/dataset-trla/score/mean` | 0.449766 | 0.520708 |
| `critic/general/dataset-trla/score/min` | 0 | -0.432242 |
| `critic/returns/max` | 1.32344 | 1.1543 |
| `critic/returns/mean` | -0.0108076 | -0.0198392 |
| `critic/returns/min` | -0.9375 | -1.47134 |
| `critic/rewards/max` | 1 | 1 |
| `critic/rewards/mean` | 0.581967 | 0.563659 |
| `critic/rewards/min` | -0.237846 | -0.8 |
| `critic/score/max` | 1 | 1 |
| `critic/score/mean` | 0.581967 | 0.563659 |
| `critic/score/min` | -0.237846 | -0.8 |
| `critic/visual/dataset-053e/advantages/max` | 0.7375 | 0.609375 |
| `critic/visual/dataset-053e/advantages/mean` | 0.00872443 | 0.006916 |
| `critic/visual/dataset-053e/advantages/min` | -0.865625 | -0.875 |
| `critic/visual/dataset-053e/returns/max` | 0.7375 | 0.609375 |
| `critic/visual/dataset-053e/returns/mean` | 0.00872443 | 0.006916 |
| `critic/visual/dataset-053e/returns/min` | -0.865625 | -0.875 |
| `critic/visual/dataset-053e/rewards/max` | 1 | 1 |
| `critic/visual/dataset-053e/rewards/mean` | 0.565571 | 0.590499 |
| `critic/visual/dataset-053e/rewards/min` | 0 | 0 |
| `critic/visual/dataset-053e/score/max` | 1 | 1 |
| `critic/visual/dataset-053e/score/mean` | 0.565571 | 0.590499 |
| `critic/visual/dataset-053e/score/min` | 0 | 0 |
| `critic/visual/dataset-gtav/advantages/max` | 0.683587 | 0.610894 |
| `critic/visual/dataset-gtav/advantages/mean` | -0.00435827 | 0.000611369 |
| `critic/visual/dataset-gtav/advantages/min` | -0.640637 | -0.656269 |
| `critic/visual/dataset-gtav/returns/max` | 0.683587 | 0.610894 |
| `critic/visual/dataset-gtav/returns/mean` | -0.00435827 | 0.000611369 |
| `critic/visual/dataset-gtav/returns/min` | -0.640637 | -0.656269 |
| `critic/visual/dataset-gtav/rewards/max` | 1 | 1 |
| `critic/visual/dataset-gtav/rewards/mean` | 0.574515 | 0.575427 |
| `critic/visual/dataset-gtav/rewards/min` | 0 | 0 |
| `critic/visual/dataset-gtav/score/max` | 1 | 1 |
| `critic/visual/dataset-gtav/score/mean` | 0.574515 | 0.575427 |
| `critic/visual/dataset-gtav/score/min` | 0 | 0 |
| `critic/visual/dataset-jzd3/advantages/max` | 0.856406 | 0.90625 |
| `critic/visual/dataset-jzd3/advantages/mean` | 0.00411357 | -0.00668089 |
| `critic/visual/dataset-jzd3/advantages/min` | -0.9375 | -0.75 |
| `critic/visual/dataset-jzd3/returns/max` | 0.856406 | 0.90625 |
| `critic/visual/dataset-jzd3/returns/mean` | 0.00411357 | -0.00668089 |
| `critic/visual/dataset-jzd3/returns/min` | -0.9375 | -0.75 |
| `critic/visual/dataset-jzd3/rewards/max` | 1 | 1 |
| `critic/visual/dataset-jzd3/rewards/mean` | 0.450904 | 0.377933 |
| `critic/visual/dataset-jzd3/rewards/min` | 0 | 0 |
| `critic/visual/dataset-jzd3/score/max` | 1 | 1 |
| `critic/visual/dataset-jzd3/score/mean` | 0.450904 | 0.377933 |
| `critic/visual/dataset-jzd3/score/min` | 0 | 0 |
| `critic/visual/dataset-ol8x/advantages/max` | 0.494806 | 0.367694 |
| `critic/visual/dataset-ol8x/advantages/mean` | 0.00388735 | 0.00130539 |
| `critic/visual/dataset-ol8x/advantages/min` | -0.604175 | -0.656269 |
| `critic/visual/dataset-ol8x/returns/max` | 0.494806 | 0.367694 |
| `critic/visual/dataset-ol8x/returns/mean` | 0.00388735 | 0.00130539 |
| `critic/visual/dataset-ol8x/returns/min` | -0.604175 | -0.656269 |
| `critic/visual/dataset-ol8x/rewards/max` | 1 | 1 |
| `critic/visual/dataset-ol8x/rewards/mean` | 0.633989 | 0.66774 |
| `critic/visual/dataset-ol8x/rewards/min` | 0 | 0 |
| `critic/visual/dataset-ol8x/score/max` | 1 | 1 |
| `critic/visual/dataset-ol8x/score/mean` | 0.633989 | 0.66774 |
| `critic/visual/dataset-ol8x/score/min` | 0 | 0 |
| `critic/visual/dataset-pt5v/advantages/max` | 0.322048 | 0.562648 |
| `critic/visual/dataset-pt5v/advantages/mean` | 0.011444 | 0.0260286 |
| `critic/visual/dataset-pt5v/advantages/min` | -0.895892 | -0.900713 |
| `critic/visual/dataset-pt5v/returns/max` | 0.322048 | 0.562648 |
| `critic/visual/dataset-pt5v/returns/mean` | 0.011444 | 0.0260286 |
| `critic/visual/dataset-pt5v/returns/min` | -0.895892 | -0.900713 |
| `critic/visual/dataset-pt5v/rewards/max` | 0.989744 | 0.990236 |
| `critic/visual/dataset-pt5v/rewards/mean` | 0.75294 | 0.743089 |
| `critic/visual/dataset-pt5v/rewards/min` | 0 | 0 |
| `critic/visual/dataset-pt5v/score/max` | 0.989744 | 0.990236 |
| `critic/visual/dataset-pt5v/score/mean` | 0.75294 | 0.743089 |
| `critic/visual/dataset-pt5v/score/min` | 0 | 0 |
| `critic/visual/dataset-ve5o/advantages/max` | 0.182998 | 0.428099 |
| `critic/visual/dataset-ve5o/advantages/mean` | 0.00601431 | 0.00911799 |
| `critic/visual/dataset-ve5o/advantages/min` | -0.839656 | -0.852208 |
| `critic/visual/dataset-ve5o/returns/max` | 0.182998 | 0.428099 |
| `critic/visual/dataset-ve5o/returns/mean` | 0.00601431 | 0.00911799 |
| `critic/visual/dataset-ve5o/returns/min` | -0.839656 | -0.852208 |
| `critic/visual/dataset-ve5o/rewards/max` | 0.993126 | 0.986764 |
| `critic/visual/dataset-ve5o/rewards/mean` | 0.88361 | 0.855682 |
| `critic/visual/dataset-ve5o/rewards/min` | 0 | 0 |
| `critic/visual/dataset-ve5o/score/max` | 0.993126 | 0.986764 |
| `critic/visual/dataset-ve5o/score/mean` | 0.88361 | 0.855682 |
| `critic/visual/dataset-ve5o/score/min` | 0 | 0 |

## ctx_prompt_length · 81

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `ctx_prompt_length/agentic/max` | 48994 | 710514 |
| `ctx_prompt_length/agentic/mean` | 3923.94 | 4098.81 |
| `ctx_prompt_length/agentic/min` | 462 | 452 |
| `ctx_prompt_length/chat/dataset-8kb6/max` | 34804 | 58472 |
| `ctx_prompt_length/chat/dataset-8kb6/mean` | 9456.93 | 9098.88 |
| `ctx_prompt_length/chat/dataset-8kb6/min` | 2493 | 2284 |
| `ctx_prompt_length/chat/dataset-eup7/max` | 2652 | 3338 |
| `ctx_prompt_length/chat/dataset-eup7/mean` | 1342.07 | 1296.12 |
| `ctx_prompt_length/chat/dataset-eup7/min` | 119 | 87 |
| `ctx_prompt_length/chat/dataset-lm3t/max` | 107477 | 111841 |
| `ctx_prompt_length/chat/dataset-lm3t/mean` | 42541.6 | 38476.4 |
| `ctx_prompt_length/chat/dataset-lm3t/min` | 6140 | 6597 |
| `ctx_prompt_length/code/dataset-4onq/max` | 1055 | 974 |
| `ctx_prompt_length/code/dataset-4onq/mean` | 588.938 | 574.097 |
| `ctx_prompt_length/code/dataset-4onq/min` | 285 | 232 |
| `ctx_prompt_length/code/dataset-bvg7/max` | 6080 | 121698 |
| `ctx_prompt_length/code/dataset-bvg7/mean` | 3359.25 | 3471.5 |
| `ctx_prompt_length/code/dataset-bvg7/min` | 723 | 892 |
| `ctx_prompt_length/code/dataset-dnpn/max` | 5868 | 8074 |
| `ctx_prompt_length/code/dataset-dnpn/mean` | 2945.65 | 3040.19 |
| `ctx_prompt_length/code/dataset-dnpn/min` | 502 | 522 |
| `ctx_prompt_length/code/dataset-m1dt/max` | 2418 | 6045 |
| `ctx_prompt_length/code/dataset-m1dt/mean` | 1753.33 | 1814.58 |
| `ctx_prompt_length/code/dataset-m1dt/min` | 1419 | 1417 |
| `ctx_prompt_length/code/dataset-obg8/max` | 5461 | 5410 |
| `ctx_prompt_length/code/dataset-obg8/mean` | 2943.43 | 2832.17 |
| `ctx_prompt_length/code/dataset-obg8/min` | 570 | 620 |
| `ctx_prompt_length/code/dataset-sin0/max` | 5629 | 101639 |
| `ctx_prompt_length/code/dataset-sin0/mean` | 3282.23 | 3163.45 |
| `ctx_prompt_length/code/dataset-sin0/min` | 676 | 646 |
| `ctx_prompt_length/code/dataset-ta4j/max` | 5066 | 5338 |
| `ctx_prompt_length/code/dataset-ta4j/mean` | 2847.69 | 2634.96 |
| `ctx_prompt_length/code/dataset-ta4j/min` | 591 | 601 |
| `ctx_prompt_length/code/dataset-v7yx/max` | 5074 | 5202 |
| `ctx_prompt_length/code/dataset-v7yx/mean` | 2538.02 | 2469.83 |
| `ctx_prompt_length/code/dataset-v7yx/min` | 571 | 545 |
| `ctx_prompt_length/code/dataset-x7wh/max` | 5404 | 5372 |
| `ctx_prompt_length/code/dataset-x7wh/mean` | 3079.79 | 3154.44 |
| `ctx_prompt_length/code/dataset-x7wh/min` | 644 | 623 |
| `ctx_prompt_length/code/dataset-yfch/max` | 4878 | 710514 |
| `ctx_prompt_length/code/dataset-yfch/mean` | 2256.16 | 5585.86 |
| `ctx_prompt_length/code/dataset-yfch/min` | 658 | 658 |
| `ctx_prompt_length/code/dataset-zg6q/max` | 6777 | 5286 |
| `ctx_prompt_length/code/dataset-zg6q/mean` | 2884.35 | 2862.42 |
| `ctx_prompt_length/code/dataset-zg6q/min` | 462 | 452 |
| `ctx_prompt_length/cyber/dataset-9aui/max` | 1646 | 262051 |
| `ctx_prompt_length/cyber/dataset-9aui/mean` | 1610.99 | 2207.36 |
| `ctx_prompt_length/cyber/dataset-9aui/min` | 1603 | 1602 |
| `ctx_prompt_length/general/dataset-1doa/max` | 1737 | 1600 |
| `ctx_prompt_length/general/dataset-1doa/mean` | 1136.06 | 1106.39 |
| `ctx_prompt_length/general/dataset-1doa/min` | 896 | 914 |
| `ctx_prompt_length/general/dataset-5610/max` | 1576 | 2088 |
| `ctx_prompt_length/general/dataset-5610/mean` | 927.344 | 975.903 |
| `ctx_prompt_length/general/dataset-5610/min` | 626 | 647 |
| `ctx_prompt_length/general/dataset-epqd/max` | 31946 | 40559 |
| `ctx_prompt_length/general/dataset-epqd/mean` | 13250.5 | 14288.8 |
| `ctx_prompt_length/general/dataset-epqd/min` | 6615 | 6586 |
| `ctx_prompt_length/general/dataset-trla/max` | 48994 | 37618 |
| `ctx_prompt_length/general/dataset-trla/mean` | 19263.6 | 19162.5 |
| `ctx_prompt_length/general/dataset-trla/min` | 4525 | 7386 |
| `ctx_prompt_length/max` | 107477 | 710514 |
| `ctx_prompt_length/mean` | 4085.96 | 4182.04 |
| `ctx_prompt_length/min` | 23 | 22 |
| `ctx_prompt_length/visual/dataset-053e/max` | 3445 | 4130 |
| `ctx_prompt_length/visual/dataset-053e/mean` | 2249.94 | 2361.81 |
| `ctx_prompt_length/visual/dataset-053e/min` | 1404 | 1412 |
| `ctx_prompt_length/visual/dataset-gtav/max` | 525 | 827 |
| `ctx_prompt_length/visual/dataset-gtav/mean` | 203.366 | 321.195 |
| `ctx_prompt_length/visual/dataset-gtav/min` | 23 | 32 |
| `ctx_prompt_length/visual/dataset-jzd3/max` | 924 | 711 |
| `ctx_prompt_length/visual/dataset-jzd3/mean` | 275.073 | 276.537 |
| `ctx_prompt_length/visual/dataset-jzd3/min` | 28 | 22 |
| `ctx_prompt_length/visual/dataset-ol8x/max` | 3770 | 3977 |
| `ctx_prompt_length/visual/dataset-ol8x/mean` | 2352.03 | 2487.35 |
| `ctx_prompt_length/visual/dataset-ol8x/min` | 1391 | 1389 |
| `ctx_prompt_length/visual/dataset-pt5v/max` | 6950 | 7016 |
| `ctx_prompt_length/visual/dataset-pt5v/mean` | 4114.06 | 3979.71 |
| `ctx_prompt_length/visual/dataset-pt5v/min` | 1748 | 1825 |
| `ctx_prompt_length/visual/dataset-ve5o/max` | 5664 | 6590 |
| `ctx_prompt_length/visual/dataset-ve5o/mean` | 3832.95 | 4120.91 |
| `ctx_prompt_length/visual/dataset-ve5o/min` | 2254 | 2328 |

## ctx_response_length · 81

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `ctx_response_length/agentic/max` | 663096 | 1047910 |
| `ctx_response_length/agentic/mean` | 96424.8 | 111664 |
| `ctx_response_length/agentic/min` | 442 | 80 |
| `ctx_response_length/chat/dataset-8kb6/max` | 109381 | 64716 |
| `ctx_response_length/chat/dataset-8kb6/mean` | 8054.64 | 4505.46 |
| `ctx_response_length/chat/dataset-8kb6/min` | 323 | 340 |
| `ctx_response_length/chat/dataset-eup7/max` | 42165 | 26566 |
| `ctx_response_length/chat/dataset-eup7/mean` | 2639.83 | 2597.27 |
| `ctx_response_length/chat/dataset-eup7/min` | 102 | 152 |
| `ctx_response_length/chat/dataset-lm3t/max` | 10018 | 94467 |
| `ctx_response_length/chat/dataset-lm3t/mean` | 1246.18 | 3917.08 |
| `ctx_response_length/chat/dataset-lm3t/min` | 70 | 54 |
| `ctx_response_length/code/dataset-4onq/max` | 261108 | 261649 |
| `ctx_response_length/code/dataset-4onq/mean` | 40130.2 | 52505.2 |
| `ctx_response_length/code/dataset-4onq/min` | 752 | 586 |
| `ctx_response_length/code/dataset-bvg7/max` | 379355 | 1046050 |
| `ctx_response_length/code/dataset-bvg7/mean` | 92677.6 | 90075.8 |
| `ctx_response_length/code/dataset-bvg7/min` | 18124 | 8652 |
| `ctx_response_length/code/dataset-dnpn/max` | 380344 | 250294 |
| `ctx_response_length/code/dataset-dnpn/mean` | 51511.1 | 53411.3 |
| `ctx_response_length/code/dataset-dnpn/min` | 5553 | 4434 |
| `ctx_response_length/code/dataset-m1dt/max` | 314047 | 361555 |
| `ctx_response_length/code/dataset-m1dt/mean` | 62424.4 | 74474.6 |
| `ctx_response_length/code/dataset-m1dt/min` | 6706 | 5125 |
| `ctx_response_length/code/dataset-obg8/max` | 407426 | 660525 |
| `ctx_response_length/code/dataset-obg8/mean` | 109551 | 112931 |
| `ctx_response_length/code/dataset-obg8/min` | 12177 | 15924 |
| `ctx_response_length/code/dataset-sin0/max` | 490003 | 684894 |
| `ctx_response_length/code/dataset-sin0/mean` | 89523.2 | 106034 |
| `ctx_response_length/code/dataset-sin0/min` | 9381 | 979 |
| `ctx_response_length/code/dataset-ta4j/max` | 640063 | 381591 |
| `ctx_response_length/code/dataset-ta4j/mean` | 110128 | 103200 |
| `ctx_response_length/code/dataset-ta4j/min` | 14131 | 10359 |
| `ctx_response_length/code/dataset-v7yx/max` | 330577 | 415602 |
| `ctx_response_length/code/dataset-v7yx/mean` | 85928 | 79895.9 |
| `ctx_response_length/code/dataset-v7yx/min` | 534 | 80 |
| `ctx_response_length/code/dataset-x7wh/max` | 475646 | 403645 |
| `ctx_response_length/code/dataset-x7wh/mean` | 106591 | 111816 |
| `ctx_response_length/code/dataset-x7wh/min` | 6819 | 18908 |
| `ctx_response_length/code/dataset-yfch/max` | 578802 | 1047910 |
| `ctx_response_length/code/dataset-yfch/mean` | 262637 | 440762 |
| `ctx_response_length/code/dataset-yfch/min` | 26646 | 29913 |
| `ctx_response_length/code/dataset-zg6q/max` | 419872 | 1043650 |
| `ctx_response_length/code/dataset-zg6q/mean` | 52787.7 | 60598.9 |
| `ctx_response_length/code/dataset-zg6q/min` | 442 | 3858 |
| `ctx_response_length/cyber/dataset-9aui/max` | 663096 | 1046970 |
| `ctx_response_length/cyber/dataset-9aui/mean` | 228349 | 233262 |
| `ctx_response_length/cyber/dataset-9aui/min` | 22761 | 17825 |
| `ctx_response_length/general/dataset-1doa/max` | 248102 | 233232 |
| `ctx_response_length/general/dataset-1doa/mean` | 65261.2 | 83765.1 |
| `ctx_response_length/general/dataset-1doa/min` | 17228 | 7337 |
| `ctx_response_length/general/dataset-5610/max` | 243950 | 181122 |
| `ctx_response_length/general/dataset-5610/mean` | 70133.6 | 70869.5 |
| `ctx_response_length/general/dataset-5610/min` | 12918 | 8765 |
| `ctx_response_length/general/dataset-epqd/max` | 338708 | 288522 |
| `ctx_response_length/general/dataset-epqd/mean` | 61208.6 | 63754.1 |
| `ctx_response_length/general/dataset-epqd/min` | 4769 | 2069 |
| `ctx_response_length/general/dataset-trla/max` | 372730 | 796397 |
| `ctx_response_length/general/dataset-trla/mean` | 64391 | 80689.6 |
| `ctx_response_length/general/dataset-trla/min` | 4231 | 893 |
| `ctx_response_length/max` | 663096 | 1047910 |
| `ctx_response_length/mean` | 88990.6 | 103314 |
| `ctx_response_length/min` | 70 | 54 |
| `ctx_response_length/visual/dataset-053e/max` | 216804 | 224197 |
| `ctx_response_length/visual/dataset-053e/mean` | 95707.6 | 107432 |
| `ctx_response_length/visual/dataset-053e/min` | 19718 | 3929 |
| `ctx_response_length/visual/dataset-gtav/max` | 101774 | 613876 |
| `ctx_response_length/visual/dataset-gtav/mean` | 29185.7 | 39288 |
| `ctx_response_length/visual/dataset-gtav/min` | 6120 | 5854 |
| `ctx_response_length/visual/dataset-jzd3/max` | 84704 | 625828 |
| `ctx_response_length/visual/dataset-jzd3/mean` | 27924.3 | 34561.2 |
| `ctx_response_length/visual/dataset-jzd3/min` | 2146 | 2010 |
| `ctx_response_length/visual/dataset-ol8x/max` | 239207 | 221866 |
| `ctx_response_length/visual/dataset-ol8x/mean` | 87855.3 | 100286 |
| `ctx_response_length/visual/dataset-ol8x/min` | 3080 | 2843 |
| `ctx_response_length/visual/dataset-pt5v/max` | 372888 | 495384 |
| `ctx_response_length/visual/dataset-pt5v/mean` | 96908.8 | 142711 |
| `ctx_response_length/visual/dataset-pt5v/min` | 6578 | 177 |
| `ctx_response_length/visual/dataset-ve5o/max` | 238652 | 320186 |
| `ctx_response_length/visual/dataset-ve5o/mean` | 140446 | 188418 |
| `ctx_response_length/visual/dataset-ve5o/min` | 37468 | 42676 |

## ctx_total_length · 108

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `ctx_total_length/agentic/clip_ratio` | 0 | 0.000490568 |
| `ctx_total_length/agentic/max` | 664700 | 1048570 |
| `ctx_total_length/agentic/mean` | 100349 | 115763 |
| `ctx_total_length/agentic/min` | 2757 | 760 |
| `ctx_total_length/chat/dataset-8kb6/clip_ratio` | 0 | 0 |
| `ctx_total_length/chat/dataset-8kb6/max` | 118052 | 67749 |
| `ctx_total_length/chat/dataset-8kb6/mean` | 17511.6 | 13604.3 |
| `ctx_total_length/chat/dataset-8kb6/min` | 3175 | 2792 |
| `ctx_total_length/chat/dataset-eup7/clip_ratio` | 0 | 0 |
| `ctx_total_length/chat/dataset-eup7/max` | 42284 | 26718 |
| `ctx_total_length/chat/dataset-eup7/mean` | 3981.9 | 3893.39 |
| `ctx_total_length/chat/dataset-eup7/min` | 788 | 588 |
| `ctx_total_length/chat/dataset-lm3t/clip_ratio` | 0 | 0 |
| `ctx_total_length/chat/dataset-lm3t/max` | 109834 | 114891 |
| `ctx_total_length/chat/dataset-lm3t/mean` | 43787.7 | 42393.5 |
| `ctx_total_length/chat/dataset-lm3t/min` | 6351 | 6719 |
| `ctx_total_length/clip_ratio` | 7.99584e-05 | 0.000520354 |
| `ctx_total_length/code/dataset-4onq/clip_ratio` | 0.00390625 | 0.00403226 |
| `ctx_total_length/code/dataset-4onq/max` | 262144 | 262144 |
| `ctx_total_length/code/dataset-4onq/mean` | 40719.2 | 53079.2 |
| `ctx_total_length/code/dataset-4onq/min` | 1254 | 997 |
| `ctx_total_length/code/dataset-bvg7/clip_ratio` | 0 | 0.00120048 |
| `ctx_total_length/code/dataset-bvg7/max` | 380350 | 1048570 |
| `ctx_total_length/code/dataset-bvg7/mean` | 96036.8 | 93547.3 |
| `ctx_total_length/code/dataset-bvg7/min` | 20408 | 9815 |
| `ctx_total_length/code/dataset-dnpn/clip_ratio` | 0 | 0 |
| `ctx_total_length/code/dataset-dnpn/max` | 382985 | 252451 |
| `ctx_total_length/code/dataset-dnpn/mean` | 54456.7 | 56451.4 |
| `ctx_total_length/code/dataset-dnpn/min` | 6368 | 6019 |
| `ctx_total_length/code/dataset-m1dt/clip_ratio` | 0 | 0 |
| `ctx_total_length/code/dataset-m1dt/max` | 316123 | 363212 |
| `ctx_total_length/code/dataset-m1dt/mean` | 64177.7 | 76289.2 |
| `ctx_total_length/code/dataset-m1dt/min` | 8137 | 6648 |
| `ctx_total_length/code/dataset-obg8/clip_ratio` | 0 | 0 |
| `ctx_total_length/code/dataset-obg8/max` | 409492 | 662902 |
| `ctx_total_length/code/dataset-obg8/mean` | 112495 | 115763 |
| `ctx_total_length/code/dataset-obg8/min` | 15573 | 16852 |
| `ctx_total_length/code/dataset-sin0/clip_ratio` | 0 | 0 |
| `ctx_total_length/code/dataset-sin0/max` | 493563 | 690063 |
| `ctx_total_length/code/dataset-sin0/mean` | 92805.4 | 109197 |
| `ctx_total_length/code/dataset-sin0/min` | 10255 | 1792 |
| `ctx_total_length/code/dataset-ta4j/clip_ratio` | 0 | 0 |
| `ctx_total_length/code/dataset-ta4j/max` | 642276 | 384957 |
| `ctx_total_length/code/dataset-ta4j/mean` | 112976 | 105835 |
| `ctx_total_length/code/dataset-ta4j/min` | 14868 | 13704 |
| `ctx_total_length/code/dataset-v7yx/clip_ratio` | 0 | 0 |
| `ctx_total_length/code/dataset-v7yx/max` | 334362 | 417826 |
| `ctx_total_length/code/dataset-v7yx/mean` | 88466 | 82365.7 |
| `ctx_total_length/code/dataset-v7yx/min` | 2757 | 760 |
| `ctx_total_length/code/dataset-x7wh/clip_ratio` | 0 | 0 |
| `ctx_total_length/code/dataset-x7wh/max` | 477826 | 407095 |
| `ctx_total_length/code/dataset-x7wh/mean` | 109671 | 114970 |
| `ctx_total_length/code/dataset-x7wh/min` | 10074 | 21186 |
| `ctx_total_length/code/dataset-yfch/clip_ratio` | 0 | 0.00457666 |
| `ctx_total_length/code/dataset-yfch/max` | 580951 | 1048570 |
| `ctx_total_length/code/dataset-yfch/mean` | 264893 | 446348 |
| `ctx_total_length/code/dataset-yfch/min` | 28796 | 34791 |
| `ctx_total_length/code/dataset-zg6q/clip_ratio` | 0 | 0.000405844 |
| `ctx_total_length/code/dataset-zg6q/max` | 423174 | 1048570 |
| `ctx_total_length/code/dataset-zg6q/mean` | 55672 | 63461.4 |
| `ctx_total_length/code/dataset-zg6q/min` | 4555 | 4430 |
| `ctx_total_length/cyber/dataset-9aui/clip_ratio` | 0 | 0.00486855 |
| `ctx_total_length/cyber/dataset-9aui/max` | 664700 | 1048570 |
| `ctx_total_length/cyber/dataset-9aui/mean` | 229960 | 235469 |
| `ctx_total_length/cyber/dataset-9aui/min` | 24367 | 19437 |
| `ctx_total_length/general/dataset-1doa/clip_ratio` | 0 | 0 |
| `ctx_total_length/general/dataset-1doa/max` | 249839 | 234505 |
| `ctx_total_length/general/dataset-1doa/mean` | 66397.3 | 84871.5 |
| `ctx_total_length/general/dataset-1doa/min` | 18313 | 8336 |
| `ctx_total_length/general/dataset-5610/clip_ratio` | 0 | 0 |
| `ctx_total_length/general/dataset-5610/max` | 244576 | 183210 |
| `ctx_total_length/general/dataset-5610/mean` | 71061 | 71845.4 |
| `ctx_total_length/general/dataset-5610/min` | 13602 | 9601 |
| `ctx_total_length/general/dataset-epqd/clip_ratio` | 0 | 0 |
| `ctx_total_length/general/dataset-epqd/max` | 352831 | 301266 |
| `ctx_total_length/general/dataset-epqd/mean` | 74459.1 | 78042.9 |
| `ctx_total_length/general/dataset-epqd/min` | 12642 | 12782 |
| `ctx_total_length/general/dataset-trla/clip_ratio` | 0 | 0 |
| `ctx_total_length/general/dataset-trla/max` | 385623 | 814991 |
| `ctx_total_length/general/dataset-trla/mean` | 83654.6 | 99852.1 |
| `ctx_total_length/general/dataset-trla/min` | 8756 | 10770 |
| `ctx_total_length/max` | 664700 | 1048570 |
| `ctx_total_length/mean` | 93076.6 | 107496 |
| `ctx_total_length/min` | 788 | 588 |
| `ctx_total_length/visual/dataset-053e/clip_ratio` | 0 | 0 |
| `ctx_total_length/visual/dataset-053e/max` | 219109 | 227237 |
| `ctx_total_length/visual/dataset-053e/mean` | 97957.5 | 109794 |
| `ctx_total_length/visual/dataset-053e/min` | 22660 | 5993 |
| `ctx_total_length/visual/dataset-gtav/clip_ratio` | 0 | 0 |
| `ctx_total_length/visual/dataset-gtav/max` | 101864 | 614018 |
| `ctx_total_length/visual/dataset-gtav/mean` | 29389.1 | 39609.1 |
| `ctx_total_length/visual/dataset-gtav/min` | 6149 | 5886 |
| `ctx_total_length/visual/dataset-jzd3/clip_ratio` | 0 | 0 |
| `ctx_total_length/visual/dataset-jzd3/max` | 84740 | 625897 |
| `ctx_total_length/visual/dataset-jzd3/mean` | 28199.4 | 34837.7 |
| `ctx_total_length/visual/dataset-jzd3/min` | 2185 | 2051 |
| `ctx_total_length/visual/dataset-ol8x/clip_ratio` | 0 | 0 |
| `ctx_total_length/visual/dataset-ol8x/max` | 242258 | 223510 |
| `ctx_total_length/visual/dataset-ol8x/mean` | 90207.3 | 102773 |
| `ctx_total_length/visual/dataset-ol8x/min` | 5242 | 4947 |
| `ctx_total_length/visual/dataset-pt5v/clip_ratio` | 0 | 0 |
| `ctx_total_length/visual/dataset-pt5v/max` | 379653 | 497891 |
| `ctx_total_length/visual/dataset-pt5v/mean` | 101023 | 146691 |
| `ctx_total_length/visual/dataset-pt5v/min` | 8326 | 2917 |
| `ctx_total_length/visual/dataset-ve5o/clip_ratio` | 0 | 0 |
| `ctx_total_length/visual/dataset-ve5o/max` | 243314 | 323050 |
| `ctx_total_length/visual/dataset-ve5o/mean` | 144279 | 192539 |
| `ctx_total_length/visual/dataset-ve5o/min` | 40187 | 49266 |

## dynsam · 83

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `dynsam/agentic/num_accepted/step` | 1627 | 1345 |
| `dynsam/agg_turn/mean` | 55.0367 | 57.0229 |
| `dynsam/avg@n` | 0.608784 | 0.596286 |
| `dynsam/chat/dataset-8kb6/num_accepted/carryover` | 8 | 8 |
| `dynsam/chat/dataset-8kb6/num_accepted/held` | 23 | 24 |
| `dynsam/chat/dataset-8kb6/num_accepted/step` | 16 | 16 |
| `dynsam/chat/dataset-eup7/num_accepted/carryover` | 8 | 10 |
| `dynsam/chat/dataset-eup7/num_accepted/held` | 23 | 26 |
| `dynsam/chat/dataset-eup7/num_accepted/step` | 14 | 18 |
| `dynsam/chat/dataset-lm3t/num_accepted/carryover` | 9 | 9 |
| `dynsam/chat/dataset-lm3t/num_accepted/held` | 25 | 24 |
| `dynsam/chat/dataset-lm3t/num_accepted/step` | 17 | 15 |
| `dynsam/code/dataset-4onq/num_accepted/carryover` | 9 | 16 |
| `dynsam/code/dataset-4onq/num_accepted/held` | 41 | 47 |
| `dynsam/code/dataset-4onq/num_accepted/step` | 29 | 25 |
| `dynsam/code/dataset-bvg7/num_accepted/carryover` | 24 | 24 |
| `dynsam/code/dataset-bvg7/num_accepted/held` | 75 | 76 |
| `dynsam/code/dataset-bvg7/num_accepted/step` | 69 | 50 |
| `dynsam/code/dataset-dnpn/num_accepted/carryover` | 20 | 27 |
| `dynsam/code/dataset-dnpn/num_accepted/held` | 82 | 90 |
| `dynsam/code/dataset-dnpn/num_accepted/step` | 66 | 56 |
| `dynsam/code/dataset-m1dt/num_accepted/carryover` | 41 | 48 |
| `dynsam/code/dataset-m1dt/num_accepted/held` | 195 | 202 |
| `dynsam/code/dataset-m1dt/num_accepted/step` | 157 | 145 |
| `dynsam/code/dataset-obg8/num_accepted/carryover` | 89 | 129 |
| `dynsam/code/dataset-obg8/num_accepted/held` | 242 | 283 |
| `dynsam/code/dataset-obg8/num_accepted/step` | 195 | 153 |
| `dynsam/code/dataset-sin0/num_accepted/carryover` | 24 | 79 |
| `dynsam/code/dataset-sin0/num_accepted/held` | 177 | 233 |
| `dynsam/code/dataset-sin0/num_accepted/step` | 143 | 151 |
| `dynsam/code/dataset-ta4j/num_accepted/carryover` | 26 | 47 |
| `dynsam/code/dataset-ta4j/num_accepted/held` | 88 | 110 |
| `dynsam/code/dataset-ta4j/num_accepted/step` | 75 | 67 |
| `dynsam/code/dataset-v7yx/num_accepted/carryover` | 15 | 28 |
| `dynsam/code/dataset-v7yx/num_accepted/held` | 66 | 80 |
| `dynsam/code/dataset-v7yx/num_accepted/step` | 51 | 62 |
| `dynsam/code/dataset-x7wh/num_accepted/carryover` | 81 | 104 |
| `dynsam/code/dataset-x7wh/num_accepted/held` | 209 | 233 |
| `dynsam/code/dataset-x7wh/num_accepted/step` | 171 | 116 |
| `dynsam/code/dataset-yfch/num_accepted/carryover` | 2 | 300 |
| `dynsam/code/dataset-yfch/num_accepted/held` | 56 | 355 |
| `dynsam/code/dataset-yfch/num_accepted/step` | 56 | 71 |
| `dynsam/code/dataset-zg6q/num_accepted/carryover` | 47 | 63 |
| `dynsam/code/dataset-zg6q/num_accepted/held` | 200 | 217 |
| `dynsam/code/dataset-zg6q/num_accepted/step` | 146 | 143 |
| `dynsam/cyber/dataset-9aui/num_accepted/carryover` | 47 | 0 |
| `dynsam/cyber/dataset-9aui/num_accepted/held` | 112 | 64 |
| `dynsam/cyber/dataset-9aui/num_accepted/step` | 112 | 64 |
| `dynsam/general/dataset-1doa/num_accepted/carryover` | 16 | 14 |
| `dynsam/general/dataset-1doa/num_accepted/held` | 48 | 45 |
| `dynsam/general/dataset-1doa/num_accepted/step` | 35 | 26 |
| `dynsam/general/dataset-5610/num_accepted/carryover` | 8 | 13 |
| `dynsam/general/dataset-5610/num_accepted/held` | 40 | 44 |
| `dynsam/general/dataset-5610/num_accepted/step` | 34 | 26 |
| `dynsam/general/dataset-epqd/num_accepted/carryover` | 30 | 42 |
| `dynsam/general/dataset-epqd/num_accepted/held` | 95 | 106 |
| `dynsam/general/dataset-epqd/num_accepted/step` | 65 | 73 |
| `dynsam/general/dataset-trla/num_accepted/carryover` | 29 | 34 |
| `dynsam/general/dataset-trla/num_accepted/held` | 94 | 98 |
| `dynsam/general/dataset-trla/num_accepted/step` | 78 | 62 |
| `dynsam/infra_error/seq_rate` | 0.00453477 | 0.0051083 |
| `dynsam/num_measurable` | 2970 | 2443 |
| `dynsam/num_target` | 1568 | 1568 |
| `dynsam/passrate/one` | 0.247565 | 0.234573 |
| `dynsam/passrate/zero` | 0.151495 | 0.150797 |
| `dynsam/visual/dataset-053e/num_accepted/carryover` | 28 | 43 |
| `dynsam/visual/dataset-053e/num_accepted/held` | 60 | 74 |
| `dynsam/visual/dataset-053e/num_accepted/step` | 52 | 23 |
| `dynsam/visual/dataset-gtav/num_accepted/carryover` | 17 | 20 |
| `dynsam/visual/dataset-gtav/num_accepted/held` | 58 | 61 |
| `dynsam/visual/dataset-gtav/num_accepted/step` | 42 | 43 |
| `dynsam/visual/dataset-jzd3/num_accepted/carryover` | 19 | 22 |
| `dynsam/visual/dataset-jzd3/num_accepted/held` | 60 | 63 |
| `dynsam/visual/dataset-jzd3/num_accepted/step` | 43 | 42 |
| `dynsam/visual/dataset-ol8x/num_accepted/carryover` | 25 | 35 |
| `dynsam/visual/dataset-ol8x/num_accepted/held` | 57 | 66 |
| `dynsam/visual/dataset-ol8x/num_accepted/step` | 42 | 22 |
| `dynsam/visual/dataset-pt5v/num_accepted/carryover` | 13 | 21 |
| `dynsam/visual/dataset-pt5v/num_accepted/held` | 45 | 52 |
| `dynsam/visual/dataset-pt5v/num_accepted/step` | 35 | 18 |
| `dynsam/visual/dataset-ve5o/num_accepted/carryover` | 21 | 34 |
| `dynsam/visual/dataset-ve5o/num_accepted/held` | 53 | 65 |
| `dynsam/visual/dataset-ve5o/num_accepted/step` | 45 | 17 |

## env · 15

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `env/active` | 23848 | 37786 |
| `env/code/dataset-m1dt/active` | 662 | 2850 |
| `env/code/shared/active` | 16638 | 26215 |
| `env/cyber/dataset-9aui/active` | 3448 | 2449 |
| `env/general/dataset-1doa/active` | 210 | 786 |
| `env/general/dataset-5610/active` | 336 | 788 |
| `env/general/dataset-epqd/active` | 352 | 1649 |
| `env/general/dataset-trla/active` | 556 | 1614 |
| `env/possible_leak` | 0 | 0 |
| `env/total_error` | 41 | 134 |
| `env/total_setup` | 86528 | 538096 |
| `env/visual/dataset-053e/active` | 497 | 351 |
| `env/visual/dataset-ol8x/active` | 425 | 381 |
| `env/visual/dataset-pt5v/active` | 176 | 357 |
| `env/visual/dataset-ve5o/active` | 548 | 346 |

## partial · 375

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `partial/0/entropy_loss` | 0.389221 | 0.409983 |
| `partial/0/frac` | 0.322084 | 0.157042 |
| `partial/0/n_tokens` | 3.64141e+08 | 2.26282e+08 |
| `partial/0/train_infer_diff/new_infer/F(tau=1.5)` | 0.0048067 | 0.00696334 |
| `partial/0/train_infer_diff/new_infer/F(tau=10)` | 5.88782e-06 | 1.02438e-05 |
| `partial/0/train_infer_diff/new_infer/F(tau=2)` | 0.000800357 | 0.00125145 |
| `partial/0/train_infer_diff/new_infer/F(tau=3)` | 0.000136793 | 0.000222854 |
| `partial/0/train_infer_diff/new_infer/F(tau=5)` | 2.74042e-05 | 4.6959e-05 |
| `partial/0/train_infer_diff/new_infer/diff_abs_max` | 28.0473 | 27.3796 |
| `partial/0/train_infer_diff/new_infer/diff_abs_mean` | 0.0248826 | 0.0289948 |
| `partial/0/train_infer_diff/new_infer/diff_abs_std` | 0.066836 | 0.0758404 |
| `partial/0/train_infer_diff/new_infer/kl` | 0.0024692 | 0.00317817 |
| `partial/0/train_infer_diff/nll_loss/log_probs` | 0.344103 | 0.360856 |
| `partial/0/train_infer_diff/nll_loss/rollout_log_probs` | 0.341636 | 0.357682 |
| `partial/1/entropy_loss` | 0.416933 | 0.439925 |
| `partial/1/frac` | 0.677916 | 0.527276 |
| `partial/1/n_tokens` | 7.66436e+08 | 7.59755e+08 |
| `partial/1/train_infer_diff/new_infer/F(tau=1.5)` | 0.0217364 | 0.0102988 |
| `partial/1/train_infer_diff/new_infer/F(tau=10)` | 0.000184537 | 4.27888e-05 |
| `partial/1/train_infer_diff/new_infer/F(tau=2)` | 0.00726397 | 0.00246159 |
| `partial/1/train_infer_diff/new_infer/F(tau=3)` | 0.00216372 | 0.000598294 |
| `partial/1/train_infer_diff/new_infer/F(tau=5)` | 0.0006494 | 0.000161131 |
| `partial/1/train_infer_diff/new_infer/diff_abs_max` | 42.1275 | 53.8695 |
| `partial/1/train_infer_diff/new_infer/diff_abs_mean` | 0.0441644 | 0.0338916 |
| `partial/1/train_infer_diff/new_infer/diff_abs_std` | 0.130694 | 0.0910466 |
| `partial/1/train_infer_diff/new_infer/kl` | 0.00851288 | 0.00442359 |
| `partial/1/train_infer_diff/nll_loss/log_probs` | 0.368895 | 0.387763 |
| `partial/1/train_infer_diff/nll_loss/rollout_log_probs` | 0.36037 | 0.38334 |
| `partial/2/entropy_loss` | 缺失；最近 s11=0.411866 | 0.361505 |
| `partial/2/frac` | 缺失；最近 s11=0.0767076 | 0.105111 |
| `partial/2/n_tokens` | 缺失；最近 s11=80466800 | 1.51455e+08 |
| `partial/2/train_infer_diff/new_infer/F(tau=1.5)` | 缺失；最近 s11=0.0421523 | 0.0225368 |
| `partial/2/train_infer_diff/new_infer/F(tau=10)` | 缺失；最近 s11=0.00046541 | 0.00016638 |
| `partial/2/train_infer_diff/new_infer/F(tau=2)` | 缺失；最近 s11=0.0157392 | 0.00729828 |
| `partial/2/train_infer_diff/new_infer/F(tau=3)` | 缺失；最近 s11=0.00502514 | 0.00207242 |
| `partial/2/train_infer_diff/new_infer/F(tau=5)` | 缺失；最近 s11=0.00157861 | 0.000596351 |
| `partial/2/train_infer_diff/new_infer/diff_abs_max` | 缺失；最近 s11=21.9919 | 28.7008 |
| `partial/2/train_infer_diff/new_infer/diff_abs_mean` | 缺失；最近 s11=0.0649476 | 0.0432262 |
| `partial/2/train_infer_diff/new_infer/diff_abs_std` | 缺失；最近 s11=0.180673 | 0.130614 |
| `partial/2/train_infer_diff/new_infer/kl` | 缺失；最近 s11=0.0160591 | 0.00846423 |
| `partial/2/train_infer_diff/nll_loss/log_probs` | 缺失；最近 s11=0.364717 | 0.320495 |
| `partial/2/train_infer_diff/nll_loss/rollout_log_probs` | 缺失；最近 s11=0.348614 | 0.312015 |
| `partial/3/entropy_loss` | 缺失；最近 s11=0.4041 | 0.451539 |
| `partial/3/frac` | 缺失；最近 s11=0.0365499 | 0.0276141 |
| `partial/3/n_tokens` | 缺失；最近 s11=38341100 | 39789400 |
| `partial/3/train_infer_diff/new_infer/F(tau=1.5)` | 缺失；最近 s11=0.0565639 | 0.0425425 |
| `partial/3/train_infer_diff/new_infer/F(tau=10)` | 缺失；最近 s11=0.000698232 | 0.000423354 |
| `partial/3/train_infer_diff/new_infer/F(tau=2)` | 缺失；最近 s11=0.022424 | 0.0155379 |
| `partial/3/train_infer_diff/new_infer/F(tau=3)` | 缺失；最近 s11=0.00742462 | 0.00482755 |
| `partial/3/train_infer_diff/new_infer/F(tau=5)` | 缺失；最近 s11=0.00236915 | 0.0014673 |
| `partial/3/train_infer_diff/new_infer/diff_abs_max` | 缺失；最近 s11=25.146 | 24.1638 |
| `partial/3/train_infer_diff/new_infer/diff_abs_mean` | 缺失；最近 s11=0.0784128 | 0.0668552 |
| `partial/3/train_infer_diff/new_infer/diff_abs_std` | 缺失；最近 s11=0.210279 | 0.179124 |
| `partial/3/train_infer_diff/new_infer/kl` | 缺失；最近 s11=0.0216274 | 0.0159509 |
| `partial/3/train_infer_diff/nll_loss/log_probs` | 缺失；最近 s11=0.360314 | 0.400762 |
| `partial/3/train_infer_diff/nll_loss/rollout_log_probs` | 缺失；最近 s11=0.338675 | 0.38474 |
| `partial/4/entropy_loss` | 缺失；最近 s11=0.424751 | 0.379641 |
| `partial/4/frac` | 缺失；最近 s11=0.0181359 | 0.0312279 |
| `partial/4/n_tokens` | 缺失；最近 s11=19024700 | 44996500 |
| `partial/4/train_infer_diff/new_infer/F(tau=1.5)` | 缺失；最近 s11=0.0648355 | 0.0466935 |
| `partial/4/train_infer_diff/new_infer/F(tau=10)` | 缺失；最近 s11=0.000861566 | 0.000650739 |
| `partial/4/train_infer_diff/new_infer/F(tau=2)` | 缺失；最近 s11=0.0266049 | 0.0184077 |
| `partial/4/train_infer_diff/new_infer/F(tau=3)` | 缺失；最近 s11=0.00902345 | 0.00618136 |
| `partial/4/train_infer_diff/new_infer/F(tau=5)` | 缺失；最近 s11=0.00291248 | 0.00204605 |
| `partial/4/train_infer_diff/new_infer/diff_abs_max` | 缺失；最近 s11=31.2902 | 25.059 |
| `partial/4/train_infer_diff/new_infer/diff_abs_mean` | 缺失；最近 s11=0.0872645 | 0.0675522 |
| `partial/4/train_infer_diff/new_infer/diff_abs_std` | 缺失；最近 s11=0.226449 | 0.196633 |
| `partial/4/train_infer_diff/new_infer/kl` | 缺失；最近 s11=0.0251917 | 0.0181128 |
| `partial/4/train_infer_diff/nll_loss/log_probs` | 缺失；最近 s11=0.37711 | 0.339883 |
| `partial/4/train_infer_diff/nll_loss/rollout_log_probs` | 缺失；最近 s11=0.351806 | 0.321675 |
| `partial/5/entropy_loss` | 缺失；最近 s11=0.382226 | 0.371293 |
| `partial/5/frac` | 缺失；最近 s11=0.00539851 | 0.0417716 |
| `partial/5/n_tokens` | 缺失；最近 s11=5663080 | 60189000 |
| `partial/5/train_infer_diff/new_infer/F(tau=1.5)` | 缺失；最近 s11=0.0601548 | 0.0524893 |
| `partial/5/train_infer_diff/new_infer/F(tau=10)` | 缺失；最近 s11=0.000834352 | 0.000698815 |
| `partial/5/train_infer_diff/new_infer/F(tau=2)` | 缺失；最近 s11=0.0248868 | 0.021299 |
| `partial/5/train_infer_diff/new_infer/F(tau=3)` | 缺失；最近 s11=0.00854377 | 0.00718491 |
| `partial/5/train_infer_diff/new_infer/F(tau=5)` | 缺失；最近 s11=0.00279071 | 0.00233386 |
| `partial/5/train_infer_diff/new_infer/diff_abs_max` | 缺失；最近 s11=14.1313 | 16.5612 |
| `partial/5/train_infer_diff/new_infer/diff_abs_mean` | 缺失；最近 s11=0.0809267 | 0.0722937 |
| `partial/5/train_infer_diff/new_infer/diff_abs_std` | 缺失；最近 s11=0.220832 | 0.206235 |
| `partial/5/train_infer_diff/new_infer/kl` | 缺失；最近 s11=0.0235818 | 0.0202768 |
| `partial/5/train_infer_diff/nll_loss/log_probs` | 缺失；最近 s11=0.338249 | 0.332874 |
| `partial/5/train_infer_diff/nll_loss/rollout_log_probs` | 缺失；最近 s11=0.314309 | 0.312539 |
| `partial/6/entropy_loss` | 缺失；最近 s11=0.399277 | 0.419658 |
| `partial/6/frac` | 缺失；最近 s11=0.00320432 | 0.0540587 |
| `partial/6/n_tokens` | 缺失；最近 s11=3361360 | 77893600 |
| `partial/6/train_infer_diff/new_infer/F(tau=1.5)` | 缺失；最近 s11=0.0650928 | 0.0599198 |
| `partial/6/train_infer_diff/new_infer/F(tau=10)` | 缺失；最近 s11=0.000779448 | 0.000781617 |
| `partial/6/train_infer_diff/new_infer/F(tau=2)` | 缺失；最近 s11=0.0267663 | 0.0244816 |
| `partial/6/train_infer_diff/new_infer/F(tau=3)` | 缺失；最近 s11=0.00889493 | 0.00826071 |
| `partial/6/train_infer_diff/new_infer/F(tau=5)` | 缺失；最近 s11=0.00273818 | 0.00264568 |
| `partial/6/train_infer_diff/new_infer/diff_abs_max` | 缺失；最近 s11=12.0266 | 37.0371 |
| `partial/6/train_infer_diff/new_infer/diff_abs_mean` | 缺失；最近 s11=0.085788 | 0.0813497 |
| `partial/6/train_infer_diff/new_infer/diff_abs_std` | 缺失；最近 s11=0.224244 | 0.218281 |
| `partial/6/train_infer_diff/new_infer/kl` | 缺失；最近 s11=0.0250434 | 0.0231484 |
| `partial/6/train_infer_diff/nll_loss/log_probs` | 缺失；最近 s11=0.350086 | 0.374897 |
| `partial/6/train_infer_diff/nll_loss/rollout_log_probs` | 缺失；最近 s11=0.324963 | 0.351668 |
| `partial/7/entropy_loss` | 缺失；最近 s11=0.358482 | 0.528704 |
| `partial/7/frac` | 缺失；最近 s11=0.00172692 | 0.0522237 |
| `partial/7/n_tokens` | 缺失；最近 s11=1811550 | 75249500 |
| `partial/7/train_infer_diff/new_infer/F(tau=1.5)` | 缺失；最近 s11=0.0586841 | 0.0699292 |
| `partial/7/train_infer_diff/new_infer/F(tau=10)` | 缺失；最近 s11=0.000810357 | 0.000829613 |
| `partial/7/train_infer_diff/new_infer/F(tau=2)` | 缺失；最近 s11=0.0244045 | 0.0280035 |
| `partial/7/train_infer_diff/new_infer/F(tau=3)` | 缺失；最近 s11=0.00836025 | 0.00921451 |
| `partial/7/train_infer_diff/new_infer/F(tau=5)` | 缺失；最近 s11=0.00275952 | 0.00288809 |
| `partial/7/train_infer_diff/new_infer/diff_abs_max` | 缺失；最近 s11=14.2526 | 24.184 |
| `partial/7/train_infer_diff/new_infer/diff_abs_mean` | 缺失；最近 s11=0.0772727 | 0.0948625 |
| `partial/7/train_infer_diff/new_infer/diff_abs_std` | 缺失；最近 s11=0.218216 | 0.22964 |
| `partial/7/train_infer_diff/new_infer/kl` | 缺失；最近 s11=0.0230258 | 0.0265989 |
| `partial/7/train_infer_diff/nll_loss/log_probs` | 缺失；最近 s11=0.314476 | 0.473384 |
| `partial/7/train_infer_diff/nll_loss/rollout_log_probs` | 缺失；最近 s11=0.291149 | 0.446764 |
| `partial/8/entropy_loss` | — | 0.537789 |
| `partial/8/frac` | — | 0.00276346 |
| `partial/8/n_tokens` | — | 3981900 |
| `partial/8/train_infer_diff/new_infer/F(tau=1.5)` | — | 0.0845763 |
| `partial/8/train_infer_diff/new_infer/F(tau=10)` | — | 0.00100505 |
| `partial/8/train_infer_diff/new_infer/F(tau=2)` | — | 0.034916 |
| `partial/8/train_infer_diff/new_infer/F(tau=3)` | — | 0.0116693 |
| `partial/8/train_infer_diff/new_infer/F(tau=5)` | — | 0.00363998 |
| `partial/8/train_infer_diff/new_infer/diff_abs_max` | — | 15.9402 |
| `partial/8/train_infer_diff/new_infer/diff_abs_mean` | — | 0.110955 |
| `partial/8/train_infer_diff/new_infer/diff_abs_std` | — | 0.250155 |
| `partial/8/train_infer_diff/new_infer/kl` | — | 0.0322638 |
| `partial/8/train_infer_diff/nll_loss/log_probs` | — | 0.480422 |
| `partial/8/train_infer_diff/nll_loss/rollout_log_probs` | — | 0.448028 |
| `partial/9/entropy_loss` | — | 0.528084 |
| `partial/9/frac` | — | 0.000912662 |
| `partial/9/n_tokens` | — | 1315060 |
| `partial/9/train_infer_diff/new_infer/F(tau=1.5)` | — | 0.0877678 |
| `partial/9/train_infer_diff/new_infer/F(tau=10)` | — | 0.00122732 |
| `partial/9/train_infer_diff/new_infer/F(tau=2)` | — | 0.0372287 |
| `partial/9/train_infer_diff/new_infer/F(tau=3)` | — | 0.0126929 |
| `partial/9/train_infer_diff/new_infer/F(tau=5)` | — | 0.00407281 |
| `partial/9/train_infer_diff/new_infer/diff_abs_max` | — | 14.1473 |
| `partial/9/train_infer_diff/new_infer/diff_abs_mean` | — | 0.114019 |
| `partial/9/train_infer_diff/new_infer/diff_abs_std` | — | 0.259754 |
| `partial/9/train_infer_diff/new_infer/kl` | — | 0.0342927 |
| `partial/9/train_infer_diff/nll_loss/log_probs` | — | 0.473675 |
| `partial/9/train_infer_diff/nll_loss/rollout_log_probs` | — | 0.439415 |
| `partial/agentic/0/frac` | 0.310905 | 0.143056 |
| `partial/agentic/0/n_tokens` | 3.3257e+08 | 1.9508e+08 |
| `partial/agentic/1/frac` | 0.689095 | 0.523874 |
| `partial/agentic/1/n_tokens` | 7.37114e+08 | 7.14389e+08 |
| `partial/agentic/2/frac` | 缺失；最近 s11=0.0817624 | 0.11057 |
| `partial/agentic/2/n_tokens` | 缺失；最近 s11=80466800 | 1.5078e+08 |
| `partial/agentic/3/frac` | 缺失；最近 s11=0.0389585 | 0.0291783 |
| `partial/agentic/3/n_tokens` | 缺失；最近 s11=38341100 | 39789400 |
| `partial/agentic/4/frac` | 缺失；最近 s11=0.019331 | 0.0329968 |
| `partial/agentic/4/n_tokens` | 缺失；最近 s11=19024700 | 44996500 |
| `partial/agentic/5/frac` | 缺失；最近 s11=0.00575426 | 0.0441377 |
| `partial/agentic/5/n_tokens` | 缺失；最近 s11=5663080 | 60189000 |
| `partial/agentic/6/frac` | 缺失；最近 s11=0.00341548 | 0.0571209 |
| `partial/agentic/6/n_tokens` | 缺失；最近 s11=3361360 | 77893600 |
| `partial/agentic/7/frac` | 缺失；最近 s11=0.00184072 | 0.0551819 |
| `partial/agentic/7/n_tokens` | 缺失；最近 s11=1811550 | 75249500 |
| `partial/agentic/8/frac` | — | 0.00292 |
| `partial/agentic/8/n_tokens` | — | 3981900 |
| `partial/agentic/9/frac` | — | 0.000964359 |
| `partial/agentic/9/n_tokens` | — | 1315060 |
| `partial/agentic/avg_staleness` | 0.689095 | 1.94626 |
| `partial/avg_staleness` | 0.677916 | 1.87435 |
| `partial/chat/dataset-8kb6/0/frac` | 0.548266 | 0.635891 |
| `partial/chat/dataset-8kb6/0/n_tokens` | 1059730 | 733273 |
| `partial/chat/dataset-8kb6/1/frac` | 0.451734 | 0.364109 |
| `partial/chat/dataset-8kb6/1/n_tokens` | 873145 | 419869 |
| `partial/chat/dataset-8kb6/avg_staleness` | 0.451734 | 0.364109 |
| `partial/chat/dataset-eup7/0/frac` | 0.248557 | 0.51636 |
| `partial/chat/dataset-eup7/0/n_tokens` | 157416 | 343196 |
| `partial/chat/dataset-eup7/1/frac` | 0.751443 | 0.48364 |
| `partial/chat/dataset-eup7/1/n_tokens` | 475904 | 321449 |
| `partial/chat/dataset-eup7/avg_staleness` | 0.751443 | 0.48364 |
| `partial/chat/dataset-lm3t/0/frac` | 0.653503 | 0.176648 |
| `partial/chat/dataset-lm3t/0/n_tokens` | 208314 | 166024 |
| `partial/chat/dataset-lm3t/1/frac` | 0.346497 | 0.823352 |
| `partial/chat/dataset-lm3t/1/n_tokens` | 110451 | 773836 |
| `partial/chat/dataset-lm3t/avg_staleness` | 0.346497 | 0.823352 |
| `partial/code/dataset-4onq/0/frac` | 0.516509 | 0.248723 |
| `partial/code/dataset-4onq/0/n_tokens` | 10612300 | 6477250 |
| `partial/code/dataset-4onq/1/frac` | 0.483491 | 0.751277 |
| `partial/code/dataset-4onq/1/n_tokens` | 9933890 | 19564800 |
| `partial/code/dataset-4onq/2/frac` | 缺失；最近 s9=0.0530885 | 缺失；最近 s11=0.045277 |
| `partial/code/dataset-4onq/2/n_tokens` | 缺失；最近 s9=1166860 | 缺失；最近 s11=1805850 |
| `partial/code/dataset-4onq/avg_staleness` | 0.483491 | 0.751277 |
| `partial/code/dataset-bvg7/0/frac` | 0.574778 | 0.311638 |
| `partial/code/dataset-bvg7/0/n_tokens` | 19789600 | 11288800 |
| `partial/code/dataset-bvg7/1/frac` | 0.425222 | 0.615216 |
| `partial/code/dataset-bvg7/1/n_tokens` | 14640400 | 22285600 |
| `partial/code/dataset-bvg7/2/frac` | 缺失；最近 s10=0.0753245 | 0.0522503 |
| `partial/code/dataset-bvg7/2/n_tokens` | 缺失；最近 s10=1959680 | 1892710 |
| `partial/code/dataset-bvg7/3/frac` | 缺失；最近 s9=0.0329302 | 0.0208964 |
| `partial/code/dataset-bvg7/3/n_tokens` | 缺失；最近 s9=862136 | 756950 |
| `partial/code/dataset-bvg7/avg_staleness` | 0.425222 | 0.782405 |
| `partial/code/dataset-dnpn/0/frac` | 0.506096 | 0.518313 |
| `partial/code/dataset-dnpn/0/n_tokens` | 11336200 | 11195900 |
| `partial/code/dataset-dnpn/1/frac` | 0.493904 | 0.481687 |
| `partial/code/dataset-dnpn/1/n_tokens` | 11063100 | 10404700 |
| `partial/code/dataset-dnpn/2/frac` | 缺失；最近 s7=0.0185756 | 缺失；最近 s13=0.0408128 |
| `partial/code/dataset-dnpn/2/n_tokens` | 缺失；最近 s7=316827 | 缺失；最近 s13=1027450 |
| `partial/code/dataset-dnpn/3/frac` | — | 缺失；最近 s11=0.0409856 |
| `partial/code/dataset-dnpn/3/n_tokens` | — | 缺失；最近 s11=864812 |
| `partial/code/dataset-dnpn/avg_staleness` | 0.493904 | 0.481687 |
| `partial/code/dataset-m1dt/0/frac` | 0.449115 | 0.460418 |
| `partial/code/dataset-m1dt/0/n_tokens` | 31221000 | 40274900 |
| `partial/code/dataset-m1dt/1/frac` | 0.550885 | 0.494777 |
| `partial/code/dataset-m1dt/1/n_tokens` | 38295700 | 43280400 |
| `partial/code/dataset-m1dt/2/frac` | 缺失；最近 s10=0.0541523 | 0.0183774 |
| `partial/code/dataset-m1dt/2/n_tokens` | 缺失；最近 s10=3258080 | 1607560 |
| `partial/code/dataset-m1dt/3/frac` | 缺失；最近 s10=0.0159306 | 0.0264276 |
| `partial/code/dataset-m1dt/3/n_tokens` | 缺失；最近 s10=958464 | 2311740 |
| `partial/code/dataset-m1dt/avg_staleness` | 0.550885 | 0.610815 |
| `partial/code/dataset-obg8/0/frac` | 0.209326 | 0.043571 |
| `partial/code/dataset-obg8/0/n_tokens` | 29347800 | 6613710 |
| `partial/code/dataset-obg8/1/frac` | 0.790674 | 0.906435 |
| `partial/code/dataset-obg8/1/n_tokens` | 1.10854e+08 | 1.37589e+08 |
| `partial/code/dataset-obg8/2/frac` | 缺失；最近 s10=0.0739841 | 0.0499942 |
| `partial/code/dataset-obg8/2/n_tokens` | 缺失；最近 s10=9263800 | 7588700 |
| `partial/code/dataset-obg8/3/frac` | 缺失；最近 s10=0.00812337 | 缺失；最近 s14=0.0187875 |
| `partial/code/dataset-obg8/3/n_tokens` | 缺失；最近 s10=1017160 | 缺失；最近 s14=2924710 |
| `partial/code/dataset-obg8/avg_staleness` | 0.790674 | 1.00642 |
| `partial/code/dataset-sin0/0/frac` | 0.503918 | 0.279142 |
| `partial/code/dataset-sin0/0/n_tokens` | 48730300 | 33880800 |
| `partial/code/dataset-sin0/1/frac` | 0.496082 | 0.671143 |
| `partial/code/dataset-sin0/1/n_tokens` | 47972600 | 81459800 |
| `partial/code/dataset-sin0/2/frac` | 缺失；最近 s10=0.0325815 | 0.0345324 |
| `partial/code/dataset-sin0/2/n_tokens` | 缺失；最近 s10=2733610 | 4191360 |
| `partial/code/dataset-sin0/3/frac` | 缺失；最近 s9=0.0165498 | 0.0151825 |
| `partial/code/dataset-sin0/3/n_tokens` | 缺失；最近 s9=1651630 | 1842770 |
| `partial/code/dataset-sin0/avg_staleness` | 0.496082 | 0.785755 |
| `partial/code/dataset-ta4j/0/frac` | 0.3294 | 0.123549 |
| `partial/code/dataset-ta4j/0/n_tokens` | 15569700 | 5953820 |
| `partial/code/dataset-ta4j/1/frac` | 0.6706 | 0.851111 |
| `partial/code/dataset-ta4j/1/n_tokens` | 31697200 | 41015100 |
| `partial/code/dataset-ta4j/2/frac` | 缺失；最近 s10=0.0909611 | 0.0253407 |
| `partial/code/dataset-ta4j/2/n_tokens` | 缺失；最近 s10=3250000 | 1221170 |
| `partial/code/dataset-ta4j/3/frac` | 缺失；最近 s8=0.0249555 | 缺失；最近 s14=0.0551193 |
| `partial/code/dataset-ta4j/3/n_tokens` | 缺失；最近 s8=937899 | 缺失；最近 s14=2804900 |
| `partial/code/dataset-ta4j/avg_staleness` | 0.6706 | 0.901792 |
| `partial/code/dataset-v7yx/0/frac` | 0.339734 | 0.340339 |
| `partial/code/dataset-v7yx/0/n_tokens` | 9296960 | 9696700 |
| `partial/code/dataset-v7yx/1/frac` | 0.660266 | 0.538381 |
| `partial/code/dataset-v7yx/1/n_tokens` | 18068500 | 15339200 |
| `partial/code/dataset-v7yx/2/frac` | 缺失；最近 s10=0.0473288 | 0.12128 |
| `partial/code/dataset-v7yx/2/n_tokens` | 缺失；最近 s10=1181170 | 3455410 |
| `partial/code/dataset-v7yx/3/frac` | 缺失；最近 s7=0.0712487 | 缺失；最近 s14=0.0161214 |
| `partial/code/dataset-v7yx/3/n_tokens` | 缺失；最近 s7=1503120 | 缺失；最近 s14=504704 |
| `partial/code/dataset-v7yx/avg_staleness` | 0.660266 | 0.78094 |
| `partial/code/dataset-x7wh/0/frac` | 0.212564 | 0.00655512 |
| `partial/code/dataset-x7wh/0/n_tokens` | 23583100 | 756571 |
| `partial/code/dataset-x7wh/1/frac` | 0.787436 | 0.9346 |
| `partial/code/dataset-x7wh/1/n_tokens` | 87363000 | 1.07869e+08 |
| `partial/code/dataset-x7wh/2/frac` | 缺失；最近 s10=0.0506607 | 0.0588451 |
| `partial/code/dataset-x7wh/2/n_tokens` | 缺失；最近 s10=4416030 | 6791720 |
| `partial/code/dataset-x7wh/3/frac` | 缺失；最近 s9=0.0226598 | 缺失；最近 s14=0.0117988 |
| `partial/code/dataset-x7wh/3/n_tokens` | 缺失；最近 s9=2278900 | 缺失；最近 s14=1421030 |
| `partial/code/dataset-x7wh/avg_staleness` | 0.787436 | 1.05229 |
| `partial/code/dataset-yfch/0/frac` | 0.312261 | 9.13438e-05 |
| `partial/code/dataset-yfch/0/n_tokens` | 41773300 | 26609 |
| `partial/code/dataset-yfch/1/frac` | 0.687739 | 0.00263287 |
| `partial/code/dataset-yfch/1/n_tokens` | 92003300 | 766972 |
| `partial/code/dataset-yfch/2/frac` | 缺失；最近 s11=0.215558 | 0.0181469 |
| `partial/code/dataset-yfch/2/n_tokens` | 缺失；最近 s11=38750800 | 5286310 |
| `partial/code/dataset-yfch/3/frac` | 缺失；最近 s11=0.175035 | 0.0741502 |
| `partial/code/dataset-yfch/3/n_tokens` | 缺失；最近 s11=31466000 | 21600400 |
| `partial/code/dataset-yfch/4/frac` | 缺失；最近 s11=0.105828 | 0.154465 |
| `partial/code/dataset-yfch/4/n_tokens` | 缺失；最近 s11=19024700 | 44996500 |
| `partial/code/dataset-yfch/5/frac` | 缺失；最近 s11=0.0315019 | 0.206618 |
| `partial/code/dataset-yfch/5/n_tokens` | 缺失；最近 s11=5663080 | 60189000 |
| `partial/code/dataset-yfch/6/frac` | 缺失；最近 s11=0.0186981 | 0.267395 |
| `partial/code/dataset-yfch/6/n_tokens` | 缺失；最近 s11=3361360 | 77893600 |
| `partial/code/dataset-yfch/7/frac` | 缺失；最近 s11=0.0100771 | 0.258318 |
| `partial/code/dataset-yfch/7/n_tokens` | 缺失；最近 s11=1811550 | 75249500 |
| `partial/code/dataset-yfch/8/frac` | — | 0.0136691 |
| `partial/code/dataset-yfch/8/n_tokens` | — | 3981900 |
| `partial/code/dataset-yfch/9/frac` | — | 0.00451436 |
| `partial/code/dataset-yfch/9/n_tokens` | — | 1315060 |
| `partial/code/dataset-yfch/avg_staleness` | 0.687739 | 5.4749 |
| `partial/code/dataset-zg6q/0/frac` | 0.503478 | 0.404396 |
| `partial/code/dataset-zg6q/0/n_tokens` | 28014700 | 28234400 |
| `partial/code/dataset-zg6q/1/frac` | 0.496522 | 0.584428 |
| `partial/code/dataset-zg6q/1/n_tokens` | 27627700 | 40804000 |
| `partial/code/dataset-zg6q/2/frac` | 缺失；最近 s9=0.00164914 | 0.00366619 |
| `partial/code/dataset-zg6q/2/n_tokens` | 缺失；最近 s9=95374 | 255969 |
| `partial/code/dataset-zg6q/3/frac` | 缺失；最近 s9=0.0119759 | 0.00750981 |
| `partial/code/dataset-zg6q/3/n_tokens` | 缺失；最近 s9=692597 | 524326 |
| `partial/code/dataset-zg6q/avg_staleness` | 0.496522 | 0.61429 |
| `partial/cyber/dataset-9aui/0/frac` | 0.0913198 | 0.104017 |
| `partial/cyber/dataset-9aui/0/n_tokens` | 11603500 | 13912300 |
| `partial/cyber/dataset-9aui/1/frac` | 0.90868 | 0.544747 |
| `partial/cyber/dataset-9aui/1/n_tokens` | 1.15461e+08 | 72860300 |
| `partial/cyber/dataset-9aui/2/frac` | 缺失；最近 s11=0.388464 | 0.255886 |
| `partial/cyber/dataset-9aui/2/n_tokens` | 缺失；最近 s11=41716000 | 34224900 |
| `partial/cyber/dataset-9aui/3/frac` | 缺失；最近 s11=0.0640219 | 0.0953505 |
| `partial/cyber/dataset-9aui/3/n_tokens` | 缺失；最近 s11=6875120 | 12753200 |
| `partial/cyber/dataset-9aui/avg_staleness` | 0.90868 | 1.34257 |
| `partial/general/dataset-1doa/0/frac` | 0.515753 | 0.414987 |
| `partial/general/dataset-1doa/0/n_tokens` | 6311750 | 6918510 |
| `partial/general/dataset-1doa/1/frac` | 0.484247 | 0.585013 |
| `partial/general/dataset-1doa/1/n_tokens` | 5926180 | 9753140 |
| `partial/general/dataset-1doa/avg_staleness` | 0.484247 | 0.585013 |
| `partial/general/dataset-5610/0/frac` | 0.461834 | 0.394818 |
| `partial/general/dataset-5610/0/n_tokens` | 9002010 | 7998210 |
| `partial/general/dataset-5610/1/frac` | 0.538166 | 0.605182 |
| `partial/general/dataset-5610/1/n_tokens` | 10489900 | 12259800 |
| `partial/general/dataset-5610/2/frac` | 缺失；最近 s10=0.0468438 | 缺失；最近 s14=0.0608405 |
| `partial/general/dataset-5610/2/n_tokens` | 缺失；最近 s10=759606 | 缺失；最近 s14=1654640 |
| `partial/general/dataset-5610/3/frac` | — | 缺失；最近 s12=0.0439404 |
| `partial/general/dataset-5610/3/n_tokens` | — | 缺失；最近 s12=1137710 |
| `partial/general/dataset-5610/avg_staleness` | 0.538166 | 0.605182 |
| `partial/general/dataset-epqd/0/frac` | 0.463671 | 0.418716 |
| `partial/general/dataset-epqd/0/n_tokens` | 8648140 | 9006710 |
| `partial/general/dataset-epqd/1/frac` | 0.536329 | 0.581284 |
| `partial/general/dataset-epqd/1/n_tokens` | 10003300 | 12503600 |
| `partial/general/dataset-epqd/avg_staleness` | 0.536329 | 0.581284 |
| `partial/general/dataset-trla/0/frac` | 0.578317 | 0.358695 |
| `partial/general/dataset-trla/0/n_tokens` | 11391300 | 8537330 |
| `partial/general/dataset-trla/1/frac` | 0.421683 | 0.606475 |
| `partial/general/dataset-trla/1/n_tokens` | 8306020 | 14434800 |
| `partial/general/dataset-trla/2/frac` | 缺失；最近 s10=0.0242512 | 0.03483 |
| `partial/general/dataset-trla/2/n_tokens` | 缺失；最近 s10=483314 | 828992 |
| `partial/general/dataset-trla/3/frac` | — | 缺失；最近 s11=0.0253587 |
| `partial/general/dataset-trla/3/n_tokens` | — | 缺失；最近 s11=531240 |
| `partial/general/dataset-trla/avg_staleness` | 0.421683 | 0.676135 |
| `partial/visual/dataset-053e/0/frac` | 0.280665 | 缺失；最近 s14=0.00093033 |
| `partial/visual/dataset-053e/0/n_tokens` | 9483510 | 缺失；最近 s14=32965 |
| `partial/visual/dataset-053e/1/frac` | 0.719335 | 0.221245 |
| `partial/visual/dataset-053e/1/n_tokens` | 24305900 | 7792480 |
| `partial/visual/dataset-053e/2/frac` | 缺失；最近 s10=0.22352 | 0.778755 |
| `partial/visual/dataset-053e/2/n_tokens` | 缺失；最近 s10=6771620 | 27428600 |
| `partial/visual/dataset-053e/3/frac` | 缺失；最近 s6=0.0425685 | 缺失；最近 s9=0.0240003 |
| `partial/visual/dataset-053e/3/n_tokens` | 缺失；最近 s6=1258910 | 缺失；最近 s9=781530 |
| `partial/visual/dataset-053e/avg_staleness` | 0.719335 | 1.77876 |
| `partial/visual/dataset-gtav/0/frac` | 0.54228 | 0.513396 |
| `partial/visual/dataset-gtav/0/n_tokens` | 10382000 | 13231400 |
| `partial/visual/dataset-gtav/1/frac` | 0.45772 | 0.460425 |
| `partial/visual/dataset-gtav/1/n_tokens` | 8763130 | 11866200 |
| `partial/visual/dataset-gtav/2/frac` | — | 0.026179 |
| `partial/visual/dataset-gtav/2/n_tokens` | — | 674692 |
| `partial/visual/dataset-gtav/avg_staleness` | 0.45772 | 0.512783 |
| `partial/visual/dataset-jzd3/0/frac` | 0.499591 | 0.452152 |
| `partial/visual/dataset-jzd3/0/n_tokens` | 9151360 | 10251000 |
| `partial/visual/dataset-jzd3/1/frac` | 0.500409 | 0.547848 |
| `partial/visual/dataset-jzd3/1/n_tokens` | 9166330 | 12420500 |
| `partial/visual/dataset-jzd3/2/frac` | — | 缺失；最近 s14=0.022683 |
| `partial/visual/dataset-jzd3/2/n_tokens` | — | 缺失；最近 s14=566650 |
| `partial/visual/dataset-jzd3/3/frac` | — | 缺失；最近 s6=0.0394469 |
| `partial/visual/dataset-jzd3/3/n_tokens` | — | 缺失；最近 s6=899252 |
| `partial/visual/dataset-jzd3/avg_staleness` | 0.500409 | 0.547848 |
| `partial/visual/dataset-ol8x/0/frac` | 0.0918127 | 缺失；最近 s14=0.00958964 |
| `partial/visual/dataset-ol8x/0/n_tokens` | 2669150 | 缺失；最近 s14=380711 |
| `partial/visual/dataset-ol8x/1/frac` | 0.908187 | 0.364392 |
| `partial/visual/dataset-ol8x/1/n_tokens` | 26402600 | 11728600 |
| `partial/visual/dataset-ol8x/2/frac` | 缺失；最近 s10=0.354739 | 0.635608 |
| `partial/visual/dataset-ol8x/2/n_tokens` | 缺失；最近 s10=11441800 | 20458200 |
| `partial/visual/dataset-ol8x/3/frac` | 缺失；最近 s7=0.0790613 | — |
| `partial/visual/dataset-ol8x/3/n_tokens` | 缺失；最近 s7=2189490 | — |
| `partial/visual/dataset-ol8x/avg_staleness` | 0.908187 | 1.63561 |
| `partial/visual/dataset-pt5v/0/frac` | 0.168349 | 0.0144654 |
| `partial/visual/dataset-pt5v/0/n_tokens` | 5747220 | 783595 |
| `partial/visual/dataset-pt5v/1/frac` | 0.831651 | 0.874974 |
| `partial/visual/dataset-pt5v/1/n_tokens` | 28391500 | 47397500 |
| `partial/visual/dataset-pt5v/2/frac` | 缺失；最近 s9=0.00946416 | 0.11056 |
| `partial/visual/dataset-pt5v/2/n_tokens` | 缺失；最近 s9=307038 | 5989070 |
| `partial/visual/dataset-pt5v/3/frac` | 缺失；最近 s9=0.029415 | 缺失；最近 s11=0.0355272 |
| `partial/visual/dataset-pt5v/3/n_tokens` | 缺失；最近 s9=954286 | 缺失；最近 s11=1547760 |
| `partial/visual/dataset-pt5v/avg_staleness` | 0.831651 | 1.09609 |
| `partial/visual/dataset-ve5o/0/frac` | 0.242699 | 2.99416e-05 |
| `partial/visual/dataset-ve5o/0/n_tokens` | 9050810 | 1629 |
| `partial/visual/dataset-ve5o/1/frac` | 0.757301 | 0.456661 |
| `partial/visual/dataset-ve5o/1/n_tokens` | 28241600 | 24845100 |
| `partial/visual/dataset-ve5o/2/frac` | 缺失；最近 s10=0.623941 | 0.543309 |
| `partial/visual/dataset-ve5o/2/n_tokens` | 缺失；最近 s10=19690100 | 29559200 |
| `partial/visual/dataset-ve5o/3/frac` | 缺失；最近 s9=0.0275981 | 缺失；最近 s8=0.107921 |
| `partial/visual/dataset-ve5o/3/n_tokens` | 缺失；最近 s9=778209 | 缺失；最近 s8=4571490 |
| `partial/visual/dataset-ve5o/avg_staleness` | 0.757301 | 1.54328 |

## penalty · 535

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `penalty/action/adv_mul_min` | 1 | 1 |
| `penalty/action/adv_mul_tokens` | 0 | 0 |
| `penalty/action/adv_reduction_tokens` | 0 | 0 |
| `penalty/action/adv_reduction_total` | 0 | 0 |
| `penalty/signed/neg_hit_tokens` | 291829 | 1378780 |
| `penalty/signed/neg_mass_added` | 128387 | 1625430 |
| `penalty/signed/neg_scale` | 0.999142 | 0.991795 |
| `penalty/signed/neg_scale_clamped` | 0 | 0 |
| `penalty/signed/pos_hit_tokens` | 455107 | 244384 |
| `penalty/signed/pos_mass_removed` | 63757.2 | 36111.1 |
| `penalty/signed/pos_scale` | 1.00046 | 1.00021 |
| `penalty/signed/pos_scale_clamped` | 0 | 0 |
| `penalty/stage_credit_group/dev_neg_turns` | 0 | 0 |
| `penalty/stage_credit_group/end2end_success_rate` | 0.9625 | 0.941691 |
| `penalty/stage_credit_group/groups_attempted` | 880 | 686 |
| `penalty/stage_credit_group/groups_expired_unjudged` | 0 | 0 |
| `penalty/stage_credit_group/groups_failed_pass1` | 0 | 0 |
| `penalty/stage_credit_group/groups_failed_pass2` | 0 | 0 |
| `penalty/stage_credit_group/groups_failed_pod` | 12 | 13 |
| `penalty/stage_credit_group/groups_failed_select` | 21 | 23 |
| `penalty/stage_credit_group/groups_judged` | 847 | 646 |
| `penalty/stage_credit_group/groups_judged_after_drop` | 0 | 4 |
| `penalty/stage_credit_group/groups_skipped_empty_inputs` | 0 | — |
| `penalty/stage_credit_group/groups_skipped_unbalanced` | 0 | 0 |
| `penalty/stage_credit_group/groups_total` | 1788 | 1504 |
| `penalty/stage_credit_group/harness/harness-A/dev_neg_turns` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/end2end_success_rate` | 0.983516 | 0.933333 |
| `penalty/stage_credit_group/harness/harness-A/groups_attempted` | 182 | 150 |
| `penalty/stage_credit_group/harness/harness-A/groups_expired_unjudged` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/groups_failed_pass1` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/groups_failed_pass2` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/groups_failed_pod` | 2 | 2 |
| `penalty/stage_credit_group/harness/harness-A/groups_failed_select` | 1 | 8 |
| `penalty/stage_credit_group/harness/harness-A/groups_judged` | 179 | 140 |
| `penalty/stage_credit_group/harness/harness-A/groups_judged_after_drop` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/groups_skipped_empty_inputs` | 0 | — |
| `penalty/stage_credit_group/harness/harness-A/groups_skipped_unbalanced` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/groups_total` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/judge_aux_missing_rollouts` | 0 | — |
| `penalty/stage_credit_group/harness/harness-A/judge_pass1_attempts` | 180 | 148 |
| `penalty/stage_credit_group/harness/harness-A/judge_pass2_attempts` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/keep_mass_capped` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/pass1_success_rate` | 0.983516 | 0.933333 |
| `penalty/stage_credit_group/harness/harness-A/pass2_success_rate` | 1 | 1 |
| `penalty/stage_credit_group/harness/harness-A/rollouts_masked` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/select_above_gold_share` | 0.375725 | 0.2434 |
| `penalty/stage_credit_group/harness/harness-A/select_adv_group_sum_abs_mean` | 1.35308e-16 | 1.18326e-16 |
| `penalty/stage_credit_group/harness/harness-A/select_factor_mean` | 0.833664 | 0.801821 |
| `penalty/stage_credit_group/harness/harness-A/select_groups_failed` | 3 | 10 |
| `penalty/stage_credit_group/harness/harness-A/select_groups_judged` | 179 | 140 |
| `penalty/stage_credit_group/harness/harness-A/select_groups_skipped_uniform` | 19 | 9 |
| `penalty/stage_credit_group/harness/harness-A/select_hack_attempt` | 900 | 687 |
| `penalty/stage_credit_group/harness/harness-A/select_hack_attempt_ge_min` | 119 | 142 |
| `penalty/stage_credit_group/harness/harness-A/select_hack_attempt_ge_min_rate` | 0.0656371 | 0.0961408 |
| `penalty/stage_credit_group/harness/harness-A/select_hack_attempt_rate` | 0.496415 | 0.465132 |
| `penalty/stage_credit_group/harness/harness-A/select_hack_attempt_turns_per_pass` | 0.990072 | 1.1977 |
| `penalty/stage_credit_group/harness/harness-A/select_hack_exposed_not_relied` | 9 | 9 |
| `penalty/stage_credit_group/harness/harness-A/select_impl_over_gold_mean` | 2.15523 | 1.60111 |
| `penalty/stage_credit_group/harness/harness-A/select_pass_new_tests_rate` | 0.850488 | 0.782357 |
| `penalty/stage_credit_group/harness/harness-A/select_pass_turns_mean` | 47.6024 | 63.0522 |
| `penalty/stage_credit_group/harness/harness-A/select_probe_disagree_rate` | 0.549974 | 0.61306 |
| `penalty/stage_credit_group/harness/harness-A/select_process_severe` | 6 | 11 |
| `penalty/stage_credit_group/harness/harness-A/select_r1_masked` | 57 | 39 |
| `penalty/stage_credit_group/harness/harness-A/select_r1_rate` | 0.048927 | 0.0486284 |
| `penalty/stage_credit_group/harness/harness-A/select_r2_capped` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/select_r2_capped_rate` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/select_r2_evidence_rejected` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/select_r2_flagged` | 29 | 39 |
| `penalty/stage_credit_group/harness/harness-A/select_r2_rate` | 0.0159956 | 0.0264049 |
| `penalty/stage_credit_group/harness/harness-A/select_r3_gold_fails` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/select_r3_groups` | 3 | 7 |
| `penalty/stage_credit_group/harness/harness-A/select_r3_rate` | 0.0167598 | 0.05 |
| `penalty/stage_credit_group/harness/harness-A/select_rank_invalid` | 4 | 6 |
| `penalty/stage_credit_group/harness/harness-A/select_rank_score_conflict` | 1 | 2 |
| `penalty/stage_credit_group/harness/harness-A/select_regression_flagged` | 5 | 3 |
| `penalty/stage_credit_group/harness/harness-A/select_renorm_capped_rate` | 0.04 | 0.0225564 |
| `penalty/stage_credit_group/harness/harness-A/select_renorm_k_mean` | 1.18502 | 1.19939 |
| `penalty/stage_credit_group/harness/harness-A/select_score_A_mean` | 4.29152 | 4.17606 |
| `penalty/stage_credit_group/harness/harness-A/select_score_B_mean` | 4.38516 | 4.43028 |
| `penalty/stage_credit_group/harness/harness-A/select_score_E_mean` | 4.54122 | 4.46197 |
| `penalty/stage_credit_group/harness/harness-A/select_score_P_mean` | 4.59541 | 4.4831 |
| `penalty/stage_credit_group/harness/harness-A/select_score_S_mean` | 4.12014 | 4.0338 |
| `penalty/stage_credit_group/harness/harness-A/select_spread_logratio_mean` | 0.707132 | 0.738234 |
| `penalty/stage_credit_group/harness/harness-A/select_tier_mismatch` | 43 | 64 |
| `penalty/stage_credit_group/harness/harness-A/select_tier_share_H` | 0.00717044 | 0.014218 |
| `penalty/stage_credit_group/harness/harness-A/select_tier_share_T1` | 0.646994 | 0.58497 |
| `penalty/stage_credit_group/harness/harness-A/select_tier_share_T2` | 0.340871 | 0.394719 |
| `penalty/stage_credit_group/harness/harness-A/select_tier_share_T3` | 0.00496415 | 0.00609343 |
| `penalty/stage_credit_group/harness/harness-A/select_tq_adv_rows_rewritten` | 2863 | 2223 |
| `penalty/stage_credit_group/harness/harness-A/time_pass1_sec_mean` | 573.745 | 695.737 |
| `penalty/stage_credit_group/harness/harness-A/time_pass2_sec_mean` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/time_pod_setup_sec_mean` | 15.8702 | 15.1533 |
| `penalty/stage_credit_group/harness/harness-A/time_total_sec_max` | 1548.72 | 7243.99 |
| `penalty/stage_credit_group/harness/harness-A/time_total_sec_mean` | 590.109 | 710.976 |
| `penalty/stage_credit_group/harness/harness-A/tq_adv_mul_tokens` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/tq_adv_neg_mass` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/tq_adv_pos_mass` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/tq_adv_rows_rewritten` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-A/tq_adv_set_tokens` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/dev_neg_turns` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/end2end_success_rate` | 0.972222 | 0.952096 |
| `penalty/stage_credit_group/harness/harness-B/groups_attempted` | 252 | 167 |
| `penalty/stage_credit_group/harness/harness-B/groups_expired_unjudged` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/groups_failed_pass1` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/groups_failed_pass2` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/groups_failed_pod` | 3 | 5 |
| `penalty/stage_credit_group/harness/harness-B/groups_failed_select` | 4 | 3 |
| `penalty/stage_credit_group/harness/harness-B/groups_judged` | 245 | 159 |
| `penalty/stage_credit_group/harness/harness-B/groups_judged_after_drop` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/groups_skipped_empty_inputs` | 0 | — |
| `penalty/stage_credit_group/harness/harness-B/groups_skipped_unbalanced` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/groups_total` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/judge_aux_missing_rollouts` | 0 | — |
| `penalty/stage_credit_group/harness/harness-B/judge_pass1_attempts` | 249 | 162 |
| `penalty/stage_credit_group/harness/harness-B/judge_pass2_attempts` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/keep_mass_capped` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/pass1_success_rate` | 0.972222 | 0.952096 |
| `penalty/stage_credit_group/harness/harness-B/pass2_success_rate` | 1 | 1 |
| `penalty/stage_credit_group/harness/harness-B/rollouts_masked` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/select_above_gold_share` | 0.32079 | 0.279639 |
| `penalty/stage_credit_group/harness/harness-B/select_adv_group_sum_abs_mean` | 1.29754e-16 | 1.2563e-16 |
| `penalty/stage_credit_group/harness/harness-B/select_factor_mean` | 0.824195 | 0.841886 |
| `penalty/stage_credit_group/harness/harness-B/select_groups_failed` | 7 | 8 |
| `penalty/stage_credit_group/harness/harness-B/select_groups_judged` | 245 | 159 |
| `penalty/stage_credit_group/harness/harness-B/select_groups_skipped_uniform` | 14 | 12 |
| `penalty/stage_credit_group/harness/harness-B/select_hack_attempt` | 1018 | 734 |
| `penalty/stage_credit_group/harness/harness-B/select_hack_attempt_ge_min` | 87 | 73 |
| `penalty/stage_credit_group/harness/harness-B/select_hack_attempt_ge_min_rate` | 0.0337471 | 0.0461441 |
| `penalty/stage_credit_group/harness/harness-B/select_hack_attempt_rate` | 0.39488 | 0.46397 |
| `penalty/stage_credit_group/harness/harness-B/select_hack_attempt_turns_per_pass` | 0.728472 | 0.871681 |
| `penalty/stage_credit_group/harness/harness-B/select_hack_exposed_not_relied` | 32 | 4 |
| `penalty/stage_credit_group/harness/harness-B/select_impl_over_gold_mean` | 6.99804 | 99.0736 |
| `penalty/stage_credit_group/harness/harness-B/select_pass_new_tests_rate` | 0.763465 | 0.742874 |
| `penalty/stage_credit_group/harness/harness-B/select_pass_turns_mean` | 68.4369 | 62.4382 |
| `penalty/stage_credit_group/harness/harness-B/select_probe_disagree_rate` | 0.571572 | 0.519863 |
| `penalty/stage_credit_group/harness/harness-B/select_process_severe` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/select_r1_masked` | 80 | 103 |
| `penalty/stage_credit_group/harness/harness-B/select_r1_rate` | 0.0547945 | 0.0971698 |
| `penalty/stage_credit_group/harness/harness-B/select_r2_capped` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/select_r2_capped_rate` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/select_r2_evidence_rejected` | 1 | 1 |
| `penalty/stage_credit_group/harness/harness-B/select_r2_flagged` | 58 | 40 |
| `penalty/stage_credit_group/harness/harness-B/select_r2_rate` | 0.0224981 | 0.0252845 |
| `penalty/stage_credit_group/harness/harness-B/select_r3_gold_fails` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/select_r3_groups` | 2 | 7 |
| `penalty/stage_credit_group/harness/harness-B/select_r3_rate` | 0.00816326 | 0.0440252 |
| `penalty/stage_credit_group/harness/harness-B/select_rank_invalid` | 6 | 5 |
| `penalty/stage_credit_group/harness/harness-B/select_rank_score_conflict` | 4 | 1 |
| `penalty/stage_credit_group/harness/harness-B/select_regression_flagged` | 20 | 15 |
| `penalty/stage_credit_group/harness/harness-B/select_renorm_capped_rate` | 0.0658436 | 0.0394737 |
| `penalty/stage_credit_group/harness/harness-B/select_renorm_k_mean` | 1.20314 | 1.18259 |
| `penalty/stage_credit_group/harness/harness-B/select_score_A_mean` | 4.2323 | 4.37938 |
| `penalty/stage_credit_group/harness/harness-B/select_score_B_mean` | 4.33767 | 4.5027 |
| `penalty/stage_credit_group/harness/harness-B/select_score_E_mean` | 4.46257 | 4.52898 |
| `penalty/stage_credit_group/harness/harness-B/select_score_P_mean` | 4.6188 | 4.63881 |
| `penalty/stage_credit_group/harness/harness-B/select_score_S_mean` | 4.1367 | 4.22237 |
| `penalty/stage_credit_group/harness/harness-B/select_spread_logratio_mean` | 0.710025 | 0.706137 |
| `penalty/stage_credit_group/harness/harness-B/select_tier_mismatch` | 86 | 55 |
| `penalty/stage_credit_group/harness/harness-B/select_tier_share_H` | 0.00620636 | 0.00758534 |
| `penalty/stage_credit_group/harness/harness-B/select_tier_share_T1` | 0.630334 | 0.675727 |
| `penalty/stage_credit_group/harness/harness-B/select_tier_share_T2` | 0.354926 | 0.311631 |
| `penalty/stage_credit_group/harness/harness-B/select_tier_share_T3` | 0.00853375 | 0.00505689 |
| `penalty/stage_credit_group/harness/harness-B/select_tq_adv_rows_rewritten` | 3918 | 2545 |
| `penalty/stage_credit_group/harness/harness-B/time_pass1_sec_mean` | 526.316 | 533.898 |
| `penalty/stage_credit_group/harness/harness-B/time_pass2_sec_mean` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/time_pod_setup_sec_mean` | 16.0118 | 14.1513 |
| `penalty/stage_credit_group/harness/harness-B/time_total_sec_max` | 1475.92 | 3185.93 |
| `penalty/stage_credit_group/harness/harness-B/time_total_sec_mean` | 542.774 | 549.438 |
| `penalty/stage_credit_group/harness/harness-B/tq_adv_mul_tokens` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/tq_adv_neg_mass` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/tq_adv_pos_mass` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/tq_adv_rows_rewritten` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-B/tq_adv_set_tokens` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/dev_neg_turns` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/end2end_success_rate` | 0.943723 | 0.917098 |
| `penalty/stage_credit_group/harness/harness-C/groups_attempted` | 231 | 193 |
| `penalty/stage_credit_group/harness/harness-C/groups_expired_unjudged` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/groups_failed_pass1` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/groups_failed_pass2` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/groups_failed_pod` | 3 | 5 |
| `penalty/stage_credit_group/harness/harness-C/groups_failed_select` | 10 | 8 |
| `penalty/stage_credit_group/harness/harness-C/groups_judged` | 218 | 177 |
| `penalty/stage_credit_group/harness/harness-C/groups_judged_after_drop` | 0 | 3 |
| `penalty/stage_credit_group/harness/harness-C/groups_skipped_empty_inputs` | 0 | — |
| `penalty/stage_credit_group/harness/harness-C/groups_skipped_unbalanced` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/groups_total` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/judge_aux_missing_rollouts` | 0 | — |
| `penalty/stage_credit_group/harness/harness-C/judge_pass1_attempts` | 228 | 188 |
| `penalty/stage_credit_group/harness/harness-C/judge_pass2_attempts` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/keep_mass_capped` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/pass1_success_rate` | 0.943723 | 0.932642 |
| `penalty/stage_credit_group/harness/harness-C/pass2_success_rate` | 1 | 1 |
| `penalty/stage_credit_group/harness/harness-C/rollouts_masked` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/select_above_gold_share` | 0.387296 | 0.382363 |
| `penalty/stage_credit_group/harness/harness-C/select_adv_group_sum_abs_mean` | 1.20209e-16 | 1.19044e-16 |
| `penalty/stage_credit_group/harness/harness-C/select_factor_mean` | 0.812631 | 0.833545 |
| `penalty/stage_credit_group/harness/harness-C/select_groups_failed` | 13 | 13 |
| `penalty/stage_credit_group/harness/harness-C/select_groups_judged` | 218 | 177 |
| `penalty/stage_credit_group/harness/harness-C/select_groups_skipped_uniform` | 11 | 14 |
| `penalty/stage_credit_group/harness/harness-C/select_hack_attempt` | 1043 | 973 |
| `penalty/stage_credit_group/harness/harness-C/select_hack_attempt_ge_min` | 122 | 146 |
| `penalty/stage_credit_group/harness/harness-C/select_hack_attempt_ge_min_rate` | 0.0552787 | 0.0833333 |
| `penalty/stage_credit_group/harness/harness-C/select_hack_attempt_rate` | 0.472587 | 0.555365 |
| `penalty/stage_credit_group/harness/harness-C/select_hack_attempt_turns_per_pass` | 1.01722 | 1.21005 |
| `penalty/stage_credit_group/harness/harness-C/select_hack_exposed_not_relied` | 14 | 12 |
| `penalty/stage_credit_group/harness/harness-C/select_impl_over_gold_mean` | 3.22973 | 7.89855 |
| `penalty/stage_credit_group/harness/harness-C/select_pass_new_tests_rate` | 0.794232 | 0.74244 |
| `penalty/stage_credit_group/harness/harness-C/select_pass_turns_mean` | 54.7081 | 50.3347 |
| `penalty/stage_credit_group/harness/harness-C/select_probe_disagree_rate` | 0.598892 | 0.530263 |
| `penalty/stage_credit_group/harness/harness-C/select_process_severe` | 1 | 12 |
| `penalty/stage_credit_group/harness/harness-C/select_r1_masked` | 86 | 43 |
| `penalty/stage_credit_group/harness/harness-C/select_r1_rate` | 0.0634218 | 0.0370052 |
| `penalty/stage_credit_group/harness/harness-C/select_r2_capped` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/select_r2_capped_rate` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/select_r2_evidence_rejected` | 0 | 2 |
| `penalty/stage_credit_group/harness/harness-C/select_r2_flagged` | 42 | 33 |
| `penalty/stage_credit_group/harness/harness-C/select_r2_rate` | 0.0190304 | 0.0188356 |
| `penalty/stage_credit_group/harness/harness-C/select_r3_gold_fails` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/select_r3_groups` | 5 | 4 |
| `penalty/stage_credit_group/harness/harness-C/select_r3_rate` | 0.0229358 | 0.0225989 |
| `penalty/stage_credit_group/harness/harness-C/select_rank_invalid` | 11 | 1 |
| `penalty/stage_credit_group/harness/harness-C/select_rank_score_conflict` | 3 | 2 |
| `penalty/stage_credit_group/harness/harness-C/select_regression_flagged` | 3 | 3 |
| `penalty/stage_credit_group/harness/harness-C/select_renorm_capped_rate` | 0.0422535 | 0.017341 |
| `penalty/stage_credit_group/harness/harness-C/select_renorm_k_mean` | 1.19993 | 1.16877 |
| `penalty/stage_credit_group/harness/harness-C/select_score_A_mean` | 4.26175 | 4.32754 |
| `penalty/stage_credit_group/harness/harness-C/select_score_B_mean` | 4.35338 | 4.52216 |
| `penalty/stage_credit_group/harness/harness-C/select_score_E_mean` | 4.41118 | 4.54671 |
| `penalty/stage_credit_group/harness/harness-C/select_score_P_mean` | 4.57566 | 4.6509 |
| `penalty/stage_credit_group/harness/harness-C/select_score_S_mean` | 4.13581 | 4.20299 |
| `penalty/stage_credit_group/harness/harness-C/select_spread_logratio_mean` | 0.696891 | 0.693652 |
| `penalty/stage_credit_group/harness/harness-C/select_tier_mismatch` | 81 | 42 |
| `penalty/stage_credit_group/harness/harness-C/select_tier_share_H` | 0.0135931 | 0.0182648 |
| `penalty/stage_credit_group/harness/harness-C/select_tier_share_T1` | 0.614409 | 0.667808 |
| `penalty/stage_credit_group/harness/harness-C/select_tier_share_T2` | 0.363842 | 0.309361 |
| `penalty/stage_credit_group/harness/harness-C/select_tier_share_T3` | 0.00815587 | 0.00456621 |
| `penalty/stage_credit_group/harness/harness-C/select_tq_adv_rows_rewritten` | 3484 | 2832 |
| `penalty/stage_credit_group/harness/harness-C/time_pass1_sec_mean` | 513.454 | 519.233 |
| `penalty/stage_credit_group/harness/harness-C/time_pass2_sec_mean` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/time_pod_setup_sec_mean` | 16.4735 | 15.1618 |
| `penalty/stage_credit_group/harness/harness-C/time_total_sec_max` | 2127.78 | 2017.49 |
| `penalty/stage_credit_group/harness/harness-C/time_total_sec_mean` | 530.338 | 535.763 |
| `penalty/stage_credit_group/harness/harness-C/tq_adv_mul_tokens` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/tq_adv_neg_mass` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/tq_adv_pos_mass` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/tq_adv_rows_rewritten` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-C/tq_adv_set_tokens` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/dev_neg_turns` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/end2end_success_rate` | 0.953488 | 0.965909 |
| `penalty/stage_credit_group/harness/harness-D/groups_attempted` | 215 | 176 |
| `penalty/stage_credit_group/harness/harness-D/groups_expired_unjudged` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/groups_failed_pass1` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/groups_failed_pass2` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/groups_failed_pod` | 4 | 1 |
| `penalty/stage_credit_group/harness/harness-D/groups_failed_select` | 6 | 4 |
| `penalty/stage_credit_group/harness/harness-D/groups_judged` | 205 | 170 |
| `penalty/stage_credit_group/harness/harness-D/groups_judged_after_drop` | 0 | 1 |
| `penalty/stage_credit_group/harness/harness-D/groups_skipped_empty_inputs` | 0 | — |
| `penalty/stage_credit_group/harness/harness-D/groups_skipped_unbalanced` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/groups_total` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/judge_aux_missing_rollouts` | 0 | — |
| `penalty/stage_credit_group/harness/harness-D/judge_pass1_attempts` | 211 | 175 |
| `penalty/stage_credit_group/harness/harness-D/judge_pass2_attempts` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/keep_mass_capped` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/pass1_success_rate` | 0.953488 | 0.971591 |
| `penalty/stage_credit_group/harness/harness-D/pass2_success_rate` | 1 | 1 |
| `penalty/stage_credit_group/harness/harness-D/rollouts_masked` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/select_above_gold_share` | 0.315562 | 0.319406 |
| `penalty/stage_credit_group/harness/harness-D/select_adv_group_sum_abs_mean` | 1.25584e-16 | 1.29131e-16 |
| `penalty/stage_credit_group/harness/harness-D/select_factor_mean` | 0.827501 | 0.859008 |
| `penalty/stage_credit_group/harness/harness-D/select_groups_failed` | 10 | 5 |
| `penalty/stage_credit_group/harness/harness-D/select_groups_judged` | 205 | 170 |
| `penalty/stage_credit_group/harness/harness-D/select_groups_skipped_uniform` | 14 | 22 |
| `penalty/stage_credit_group/harness/harness-D/select_hack_attempt` | 584 | 423 |
| `penalty/stage_credit_group/harness/harness-D/select_hack_attempt_ge_min` | 62 | 43 |
| `penalty/stage_credit_group/harness/harness-D/select_hack_attempt_ge_min_rate` | 0.030754 | 0.0239955 |
| `penalty/stage_credit_group/harness/harness-D/select_hack_attempt_rate` | 0.289683 | 0.236049 |
| `penalty/stage_credit_group/harness/harness-D/select_hack_attempt_turns_per_pass` | 0.560516 | 0.464844 |
| `penalty/stage_credit_group/harness/harness-D/select_hack_exposed_not_relied` | 39 | 8 |
| `penalty/stage_credit_group/harness/harness-D/select_impl_over_gold_mean` | 2.72593 | 3.40381 |
| `penalty/stage_credit_group/harness/harness-D/select_pass_new_tests_rate` | 0.617342 | 0.607355 |
| `penalty/stage_credit_group/harness/harness-D/select_pass_turns_mean` | 65.8812 | 55.9903 |
| `penalty/stage_credit_group/harness/harness-D/select_probe_disagree_rate` | 0.896082 | 0.869416 |
| `penalty/stage_credit_group/harness/harness-D/select_process_severe` | 7 | 0 |
| `penalty/stage_credit_group/harness/harness-D/select_r1_masked` | 62 | 74 |
| `penalty/stage_credit_group/harness/harness-D/select_r1_rate` | 0.0456218 | 0.0670898 |
| `penalty/stage_credit_group/harness/harness-D/select_r2_capped` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/select_r2_capped_rate` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/select_r2_evidence_rejected` | 8 | 1 |
| `penalty/stage_credit_group/harness/harness-D/select_r2_flagged` | 30 | 48 |
| `penalty/stage_credit_group/harness/harness-D/select_r2_rate` | 0.014881 | 0.0267857 |
| `penalty/stage_credit_group/harness/harness-D/select_r3_gold_fails` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/select_r3_groups` | 2 | 6 |
| `penalty/stage_credit_group/harness/harness-D/select_r3_rate` | 0.0097561 | 0.0352941 |
| `penalty/stage_credit_group/harness/harness-D/select_rank_invalid` | 6 | 5 |
| `penalty/stage_credit_group/harness/harness-D/select_rank_score_conflict` | 2 | 0 |
| `penalty/stage_credit_group/harness/harness-D/select_regression_flagged` | 6 | 14 |
| `penalty/stage_credit_group/harness/harness-D/select_renorm_capped_rate` | 0.0541872 | 0.0184049 |
| `penalty/stage_credit_group/harness/harness-D/select_renorm_k_mean` | 1.18229 | 1.15479 |
| `penalty/stage_credit_group/harness/harness-D/select_score_A_mean` | 4.3349 | 4.45443 |
| `penalty/stage_credit_group/harness/harness-D/select_score_B_mean` | 4.44027 | 4.48295 |
| `penalty/stage_credit_group/harness/harness-D/select_score_E_mean` | 4.49922 | 4.55859 |
| `penalty/stage_credit_group/harness/harness-D/select_score_P_mean` | 4.63328 | 4.68816 |
| `penalty/stage_credit_group/harness/harness-D/select_score_S_mean` | 4.16171 | 4.2517 |
| `penalty/stage_credit_group/harness/harness-D/select_spread_logratio_mean` | 0.803272 | 0.617068 |
| `penalty/stage_credit_group/harness/harness-D/select_tier_mismatch` | 62 | 62 |
| `penalty/stage_credit_group/harness/harness-D/select_tier_share_H` | 0.0168651 | 0.0106027 |
| `penalty/stage_credit_group/harness/harness-D/select_tier_share_T1` | 0.659226 | 0.71875 |
| `penalty/stage_credit_group/harness/harness-D/select_tier_share_T2` | 0.311508 | 0.263951 |
| `penalty/stage_credit_group/harness/harness-D/select_tier_share_T3` | 0.0124008 | 0.00669643 |
| `penalty/stage_credit_group/harness/harness-D/select_tq_adv_rows_rewritten` | 3276 | 2716 |
| `penalty/stage_credit_group/harness/harness-D/time_pass1_sec_mean` | 544.84 | 517.738 |
| `penalty/stage_credit_group/harness/harness-D/time_pass2_sec_mean` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/time_pod_setup_sec_mean` | 16.497 | 14.7681 |
| `penalty/stage_credit_group/harness/harness-D/time_total_sec_max` | 3468.81 | 1985.37 |
| `penalty/stage_credit_group/harness/harness-D/time_total_sec_mean` | 562.113 | 532.792 |
| `penalty/stage_credit_group/harness/harness-D/tq_adv_mul_tokens` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/tq_adv_neg_mass` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/tq_adv_pos_mass` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/tq_adv_rows_rewritten` | 0 | 0 |
| `penalty/stage_credit_group/harness/harness-D/tq_adv_set_tokens` | 0 | 0 |
| `penalty/stage_credit_group/judge_aux_missing_rollouts` | 0 | — |
| `penalty/stage_credit_group/judge_pass1_attempts` | 868 | 673 |
| `penalty/stage_credit_group/judge_pass2_attempts` | 0 | 0 |
| `penalty/stage_credit_group/judge_pending` | 77 | 113 |
| `penalty/stage_credit_group/judge_pool_dead_replaced` | 0 | 0 |
| `penalty/stage_credit_group/judge_pool_in_flight` | 77 | 113 |
| `penalty/stage_credit_group/judge_pool_max_load` | 6 | 9 |
| `penalty/stage_credit_group/keep_mass_capped` | 0 | 0 |
| `penalty/stage_credit_group/pass1_success_rate` | 0.9625 | 0.947522 |
| `penalty/stage_credit_group/pass2_success_rate` | 1 | 1 |
| `penalty/stage_credit_group/rollouts_masked` | 0 | 0 |
| `penalty/stage_credit_group/routed/off` | 872 | 706 |
| `penalty/stage_credit_group/routed/select_v4` | 406 | 412 |
| `penalty/stage_credit_group/routed/select_v4_nogold` | 510 | 386 |
| `penalty/stage_credit_group/select_above_gold_share` | 0.347784 | 0.314955 |
| `penalty/stage_credit_group/select_adv_group_sum_abs_mean` | 1.27476e-16 | 1.2316e-16 |
| `penalty/stage_credit_group/select_factor_mean` | 0.823999 | 0.835357 |
| `penalty/stage_credit_group/select_groups_failed` | 33 | 36 |
| `penalty/stage_credit_group/select_groups_judged` | 847 | 646 |
| `penalty/stage_credit_group/select_groups_skipped_uniform` | 58 | 57 |
| `penalty/stage_credit_group/select_hack_attempt` | 3545 | 2817 |
| `penalty/stage_credit_group/select_hack_attempt_ge_min` | 390 | 404 |
| `penalty/stage_credit_group/select_hack_attempt_ge_min_rate` | 0.0452751 | 0.0611843 |
| `penalty/stage_credit_group/select_hack_attempt_rate` | 0.411539 | 0.426624 |
| `penalty/stage_credit_group/select_hack_attempt_turns_per_pass` | 0.818203 | 0.923974 |
| `penalty/stage_credit_group/select_hack_exposed_not_relied` | 94 | 33 |
| `penalty/stage_credit_group/select_impl_over_gold_mean` | 3.90729 | 28.5328 |
| `penalty/stage_credit_group/select_pass_new_tests_rate` | 0.754751 | 0.715734 |
| `penalty/stage_credit_group/select_pass_turns_mean` | 59.9666 | 57.5577 |
| `penalty/stage_credit_group/select_probe_disagree_rate` | 0.626182 | 0.597433 |
| `penalty/stage_credit_group/select_process_severe` | 14 | 23 |
| `penalty/stage_credit_group/select_r1_masked` | 285 | 259 |
| `penalty/stage_credit_group/select_r1_rate` | 0.0533708 | 0.0627574 |
| `penalty/stage_credit_group/select_r2_capped` | 0 | 0 |
| `penalty/stage_credit_group/select_r2_capped_rate` | 0 | 0 |
| `penalty/stage_credit_group/select_r2_evidence_rejected` | 9 | 4 |
| `penalty/stage_credit_group/select_r2_flagged` | 159 | 160 |
| `penalty/stage_credit_group/select_r2_rate` | 0.0184583 | 0.0242314 |
| `penalty/stage_credit_group/select_r3_gold_fails` | 0 | 0 |
| `penalty/stage_credit_group/select_r3_groups` | 12 | 24 |
| `penalty/stage_credit_group/select_r3_rate` | 0.0141677 | 0.0371517 |
| `penalty/stage_credit_group/select_rank_invalid` | 27 | 17 |
| `penalty/stage_credit_group/select_rank_score_conflict` | 10 | 5 |
| `penalty/stage_credit_group/select_regression_flagged` | 34 | 35 |
| `penalty/stage_credit_group/select_renorm_capped_rate` | 0.0515588 | 0.0241546 |
| `penalty/stage_credit_group/select_renorm_k_mean` | 1.19345 | 1.17504 |
| `penalty/stage_credit_group/select_score_A_mean` | 4.27619 | 4.33829 |
| `penalty/stage_credit_group/select_score_B_mean` | 4.37556 | 4.48618 |
| `penalty/stage_credit_group/select_score_E_mean` | 4.47409 | 4.5261 |
| `penalty/stage_credit_group/select_score_P_mean` | 4.60615 | 4.6192 |
| `penalty/stage_credit_group/select_score_S_mean` | 4.13889 | 4.18151 |
| `penalty/stage_credit_group/select_spread_logratio_mean` | 0.728505 | 0.685715 |
| `penalty/stage_credit_group/select_tier_mismatch` | 272 | 223 |
| `penalty/stage_credit_group/select_tier_share_H` | 0.0107964 | 0.0127215 |
| `penalty/stage_credit_group/select_tier_share_T1` | 0.636522 | 0.665001 |
| `penalty/stage_credit_group/select_tier_share_T2` | 0.344091 | 0.316674 |
| `penalty/stage_credit_group/select_tier_share_T3` | 0.00859067 | 0.00560351 |
| `penalty/stage_credit_group/select_tq_adv_rows_rewritten` | 13541 | 10316 |
| `penalty/stage_credit_group/select_v4/dev_neg_turns` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/end2end_success_rate` | 0.948649 | 0.928161 |
| `penalty/stage_credit_group/select_v4/groups_attempted` | 370 | 348 |
| `penalty/stage_credit_group/select_v4/groups_expired_unjudged` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/groups_failed_pass1` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/groups_failed_pass2` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/groups_failed_pod` | 6 | 9 |
| `penalty/stage_credit_group/select_v4/groups_failed_select` | 13 | 14 |
| `penalty/stage_credit_group/select_v4/groups_judged` | 351 | 323 |
| `penalty/stage_credit_group/select_v4/groups_judged_after_drop` | 0 | 2 |
| `penalty/stage_credit_group/select_v4/groups_skipped_empty_inputs` | 0 | — |
| `penalty/stage_credit_group/select_v4/groups_skipped_unbalanced` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/groups_total` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/judge_aux_missing_rollouts` | 0 | — |
| `penalty/stage_credit_group/select_v4/judge_pass1_attempts` | 364 | 339 |
| `penalty/stage_credit_group/select_v4/judge_pass2_attempts` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/keep_mass_capped` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/pass1_success_rate` | 0.948649 | 0.933908 |
| `penalty/stage_credit_group/select_v4/pass2_success_rate` | 1 | 1 |
| `penalty/stage_credit_group/select_v4/rollouts_masked` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/select_above_gold_share` | 0.347784 | 0.314955 |
| `penalty/stage_credit_group/select_v4/select_adv_group_sum_abs_mean` | 1.27813e-16 | 1.28281e-16 |
| `penalty/stage_credit_group/select_v4/select_factor_mean` | 0.841602 | 0.848213 |
| `penalty/stage_credit_group/select_v4/select_groups_failed` | 19 | 23 |
| `penalty/stage_credit_group/select_v4/select_groups_judged` | 351 | 323 |
| `penalty/stage_credit_group/select_v4/select_groups_skipped_uniform` | 36 | 33 |
| `penalty/stage_credit_group/select_v4/select_hack_attempt` | 1694 | 1567 |
| `penalty/stage_credit_group/select_v4/select_hack_attempt_ge_min` | 200 | 283 |
| `penalty/stage_credit_group/select_v4/select_hack_attempt_ge_min_rate` | 0.0527565 | 0.0841511 |
| `penalty/stage_credit_group/select_v4/select_hack_attempt_rate` | 0.446848 | 0.465953 |
| `penalty/stage_credit_group/select_v4/select_hack_attempt_turns_per_pass` | 0.884199 | 1.10199 |
| `penalty/stage_credit_group/select_v4/select_hack_exposed_not_relied` | 47 | 7 |
| `penalty/stage_credit_group/select_v4/select_impl_over_gold_mean` | 3.90729 | 28.5328 |
| `penalty/stage_credit_group/select_v4/select_pass_new_tests_rate` | 0.710646 | 0.688999 |
| `penalty/stage_credit_group/select_v4/select_pass_turns_mean` | 46.5318 | 47.0199 |
| `penalty/stage_credit_group/select_v4/select_probe_disagree_rate` | 0.600344 | 0.578786 |
| `penalty/stage_credit_group/select_v4/select_process_severe` | 8 | 17 |
| `penalty/stage_credit_group/select_v4/select_r1_masked` | 91 | 96 |
| `penalty/stage_credit_group/select_v4/select_r1_rate` | 0.0432921 | 0.0465116 |
| `penalty/stage_credit_group/select_v4/select_r2_capped` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/select_r2_capped_rate` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/select_r2_evidence_rejected` | 1 | 1 |
| `penalty/stage_credit_group/select_v4/select_r2_flagged` | 44 | 35 |
| `penalty/stage_credit_group/select_v4/select_r2_rate` | 0.0116064 | 0.0104074 |
| `penalty/stage_credit_group/select_v4/select_r3_gold_fails` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/select_r3_groups` | 8 | 11 |
| `penalty/stage_credit_group/select_v4/select_r3_rate` | 0.022792 | 0.0340557 |
| `penalty/stage_credit_group/select_v4/select_rank_invalid` | 16 | 7 |
| `penalty/stage_credit_group/select_v4/select_rank_score_conflict` | 3 | 1 |
| `penalty/stage_credit_group/select_v4/select_regression_flagged` | 4 | 8 |
| `penalty/stage_credit_group/select_v4/select_renorm_capped_rate` | 0.0437318 | 0.0192308 |
| `penalty/stage_credit_group/select_v4/select_renorm_k_mean` | 1.17402 | 1.16062 |
| `penalty/stage_credit_group/select_v4/select_score_A_mean` | 4.39134 | 4.42871 |
| `penalty/stage_credit_group/select_v4/select_score_B_mean` | 4.43036 | 4.54349 |
| `penalty/stage_credit_group/select_v4/select_score_E_mean` | 4.5873 | 4.60427 |
| `penalty/stage_credit_group/select_v4/select_score_P_mean` | 4.65451 | 4.64306 |
| `penalty/stage_credit_group/select_v4/select_score_S_mean` | 4.23953 | 4.27384 |
| `penalty/stage_credit_group/select_v4/select_spread_logratio_mean` | 0.814836 | 0.812838 |
| `penalty/stage_credit_group/select_v4/select_tier_mismatch` | 115 | 55 |
| `penalty/stage_credit_group/select_v4/select_tier_share_H` | 0.014508 | 0.0154624 |
| `penalty/stage_credit_group/select_v4/select_tier_share_T1` | 0.681087 | 0.693726 |
| `penalty/stage_credit_group/select_v4/select_tier_share_T2` | 0.296228 | 0.285757 |
| `penalty/stage_credit_group/select_v4/select_tier_share_T3` | 0.00817726 | 0.00505501 |
| `penalty/stage_credit_group/select_v4/select_tq_adv_rows_rewritten` | 5613 | 5158 |
| `penalty/stage_credit_group/select_v4/time_pass1_sec_mean` | 525.81 | 518.822 |
| `penalty/stage_credit_group/select_v4/time_pass2_sec_mean` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/time_pod_setup_sec_mean` | 15.0689 | 13.738 |
| `penalty/stage_credit_group/select_v4/time_total_sec_max` | 3468.81 | 7243.99 |
| `penalty/stage_credit_group/select_v4/time_total_sec_mean` | 541.41 | 533.774 |
| `penalty/stage_credit_group/select_v4/tq_adv_mul_tokens` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/tq_adv_neg_mass` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/tq_adv_pos_mass` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/tq_adv_rows_rewritten` | 0 | 0 |
| `penalty/stage_credit_group/select_v4/tq_adv_set_tokens` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/dev_neg_turns` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/end2end_success_rate` | 0.972549 | 0.955621 |
| `penalty/stage_credit_group/select_v4_nogold/groups_attempted` | 510 | 338 |
| `penalty/stage_credit_group/select_v4_nogold/groups_expired_unjudged` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/groups_failed_pass1` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/groups_failed_pass2` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/groups_failed_pod` | 6 | 4 |
| `penalty/stage_credit_group/select_v4_nogold/groups_failed_select` | 8 | 9 |
| `penalty/stage_credit_group/select_v4_nogold/groups_judged` | 496 | 323 |
| `penalty/stage_credit_group/select_v4_nogold/groups_judged_after_drop` | 0 | 2 |
| `penalty/stage_credit_group/select_v4_nogold/groups_skipped_empty_inputs` | 0 | — |
| `penalty/stage_credit_group/select_v4_nogold/groups_skipped_unbalanced` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/groups_total` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/judge_aux_missing_rollouts` | 0 | — |
| `penalty/stage_credit_group/select_v4_nogold/judge_pass1_attempts` | 504 | 334 |
| `penalty/stage_credit_group/select_v4_nogold/judge_pass2_attempts` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/keep_mass_capped` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/pass1_success_rate` | 0.972549 | 0.961538 |
| `penalty/stage_credit_group/select_v4_nogold/pass2_success_rate` | 1 | 1 |
| `penalty/stage_credit_group/select_v4_nogold/rollouts_masked` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/select_adv_group_sum_abs_mean` | 1.27241e-16 | 1.18006e-16 |
| `penalty/stage_credit_group/select_v4_nogold/select_factor_mean` | 0.810162 | 0.822014 |
| `penalty/stage_credit_group/select_v4_nogold/select_groups_failed` | 14 | 13 |
| `penalty/stage_credit_group/select_v4_nogold/select_groups_judged` | 496 | 323 |
| `penalty/stage_credit_group/select_v4_nogold/select_groups_skipped_uniform` | 22 | 24 |
| `penalty/stage_credit_group/select_v4_nogold/select_hack_attempt` | 1851 | 1250 |
| `penalty/stage_credit_group/select_v4_nogold/select_hack_attempt_ge_min` | 190 | 121 |
| `penalty/stage_credit_group/select_v4_nogold/select_hack_attempt_ge_min_rate` | 0.0393946 | 0.0373457 |
| `penalty/stage_credit_group/select_v4_nogold/select_hack_attempt_rate` | 0.383786 | 0.385802 |
| `penalty/stage_credit_group/select_v4_nogold/select_hack_attempt_turns_per_pass` | 0.766328 | 0.739198 |
| `penalty/stage_credit_group/select_v4_nogold/select_hack_exposed_not_relied` | 47 | 26 |
| `penalty/stage_credit_group/select_v4_nogold/select_pass_new_tests_rate` | 0.789843 | 0.744448 |
| `penalty/stage_credit_group/select_v4_nogold/select_pass_turns_mean` | 70.6562 | 68.8756 |
| `penalty/stage_credit_group/select_v4_nogold/select_probe_disagree_rate` | 0.649271 | 0.625829 |
| `penalty/stage_credit_group/select_v4_nogold/select_process_severe` | 6 | 6 |
| `penalty/stage_credit_group/select_v4_nogold/select_r1_masked` | 194 | 163 |
| `penalty/stage_credit_group/select_v4_nogold/select_r1_rate` | 0.0599135 | 0.0790111 |
| `penalty/stage_credit_group/select_v4_nogold/select_r2_capped` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/select_r2_capped_rate` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/select_r2_evidence_rejected` | 8 | 3 |
| `penalty/stage_credit_group/select_v4_nogold/select_r2_flagged` | 115 | 125 |
| `penalty/stage_credit_group/select_v4_nogold/select_r2_rate` | 0.0238441 | 0.0385802 |
| `penalty/stage_credit_group/select_v4_nogold/select_r3_gold_fails` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/select_r3_groups` | 4 | 13 |
| `penalty/stage_credit_group/select_v4_nogold/select_r3_rate` | 0.00806452 | 0.0402477 |
| `penalty/stage_credit_group/select_v4_nogold/select_rank_invalid` | 11 | 10 |
| `penalty/stage_credit_group/select_v4_nogold/select_rank_score_conflict` | 7 | 4 |
| `penalty/stage_credit_group/select_v4_nogold/select_regression_flagged` | 30 | 27 |
| `penalty/stage_credit_group/select_v4_nogold/select_renorm_capped_rate` | 0.0570265 | 0.0291262 |
| `penalty/stage_credit_group/select_v4_nogold/select_renorm_k_mean` | 1.20701 | 1.18961 |
| `penalty/stage_credit_group/select_v4_nogold/select_score_A_mean` | 4.18998 | 4.2479 |
| `penalty/stage_credit_group/select_v4_nogold/select_score_B_mean` | 4.33454 | 4.42889 |
| `penalty/stage_credit_group/select_v4_nogold/select_score_E_mean` | 4.38934 | 4.44796 |
| `penalty/stage_credit_group/select_v4_nogold/select_score_P_mean` | 4.56994 | 4.59535 |
| `penalty/stage_credit_group/select_v4_nogold/select_score_S_mean` | 4.06354 | 4.0892 |
| `penalty/stage_credit_group/select_v4_nogold/select_spread_logratio_mean` | 0.662815 | 0.551157 |
| `penalty/stage_credit_group/select_v4_nogold/select_tier_mismatch` | 157 | 168 |
| `penalty/stage_credit_group/select_v4_nogold/select_tier_share_H` | 0.00787891 | 0.00987654 |
| `penalty/stage_credit_group/select_v4_nogold/select_tier_share_T1` | 0.601493 | 0.635185 |
| `penalty/stage_credit_group/select_v4_nogold/select_tier_share_T2` | 0.381713 | 0.348765 |
| `penalty/stage_credit_group/select_v4_nogold/select_tier_share_T3` | 0.00891561 | 0.00617284 |
| `penalty/stage_credit_group/select_v4_nogold/select_tq_adv_rows_rewritten` | 7928 | 5158 |
| `penalty/stage_credit_group/select_v4_nogold/time_pass1_sec_mean` | 545.592 | 604.453 |
| `penalty/stage_credit_group/select_v4_nogold/time_pass2_sec_mean` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/time_pod_setup_sec_mean` | 17.059 | 15.9197 |
| `penalty/stage_credit_group/select_v4_nogold/time_total_sec_max` | 3051.58 | 7238.79 |
| `penalty/stage_credit_group/select_v4_nogold/time_total_sec_mean` | 563.175 | 620.778 |
| `penalty/stage_credit_group/select_v4_nogold/tq_adv_mul_tokens` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/tq_adv_neg_mass` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/tq_adv_pos_mass` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/tq_adv_rows_rewritten` | 0 | 0 |
| `penalty/stage_credit_group/select_v4_nogold/tq_adv_set_tokens` | 0 | 0 |
| `penalty/stage_credit_group/time_pass1_sec_mean` | 537.274 | 561.014 |
| `penalty/stage_credit_group/time_pass2_sec_mean` | 0 | 0 |
| `penalty/stage_credit_group/time_pod_setup_sec_mean` | 16.2223 | 14.8129 |
| `penalty/stage_credit_group/time_total_sec_max` | 3468.81 | 7243.99 |
| `penalty/stage_credit_group/time_total_sec_mean` | 554.024 | 576.642 |
| `penalty/stage_credit_group/tq_adv_mul_tokens` | 0 | 0 |
| `penalty/stage_credit_group/tq_adv_neg_mass` | 0 | 0 |
| `penalty/stage_credit_group/tq_adv_pos_mass` | 0 | 0 |
| `penalty/stage_credit_group/tq_adv_rows_rewritten` | 0 | 0 |
| `penalty/stage_credit_group/tq_adv_set_tokens` | 0 | 0 |

## perf · 1

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `perf/total_num_tokens` | 2.3281e+09 | 2.68554e+09 |

## timing_s · 3

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `timing_s/outer_gen` | 5251.64 | 3510.31 |
| `timing_s/step` | 9063.03 | 7552.1 |
| `timing_s/trainer_ops` | 3624.12 | 3818.61 |

## train · 191

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `train/adv_neg_sum_post_penalty` | -1.49746e+08 | -1.99726e+08 |
| `train/adv_neg_sum_pre_penalty` | -1.49746e+08 | -1.99726e+08 |
| `train/adv_pos_sum_post_penalty` | 1.37512e+08 | 1.683e+08 |
| `train/adv_pos_sum_pre_penalty` | 1.37512e+08 | 1.683e+08 |
| `train/harness/harness-A-pw/training/advantage_mean` | -1.95151e-09 | 5.25188e-09 |
| `train/harness/harness-A-pw/training/negative_adv_rate` | 0.482143 | 0.423611 |
| `train/harness/harness-A-pw/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-A-pw/training/positive_adv_rate` | 0.517857 | 0.576389 |
| `train/harness/harness-A-pw/training/rollouts` | 224 | 144 |
| `train/harness/harness-A-pw/training/trained_rollout_share` | 0.0100629 | 0.0065244 |
| `train/harness/harness-A/training/advantage_mean` | -5.4544e-10 | 6.18537e-10 |
| `train/harness/harness-A/training/negative_adv_rate` | 0.433061 | 0.431125 |
| `train/harness/harness-A/training/nonzero_adv_rate` | 0.984915 | 0.960555 |
| `train/harness/harness-A/training/positive_adv_rate` | 0.551854 | 0.52943 |
| `train/harness/harness-A/training/rollouts` | 3182 | 3245 |
| `train/harness/harness-A/training/trained_rollout_share` | 0.140791 | 0.141226 |
| `train/harness/harness-B/training/advantage_mean` | 3.55612e-09 | 3.08041e-09 |
| `train/harness/harness-B/training/negative_adv_rate` | 0.395917 | 0.432328 |
| `train/harness/harness-B/training/nonzero_adv_rate` | 0.991935 | 0.977858 |
| `train/harness/harness-B/training/positive_adv_rate` | 0.596018 | 0.54553 |
| `train/harness/harness-B/training/rollouts` | 3968 | 3613 |
| `train/harness/harness-B/training/trained_rollout_share` | 0.176819 | 0.160074 |
| `train/harness/harness-C/training/advantage_mean` | 2.46977e-09 | 4.86945e-10 |
| `train/harness/harness-C/training/negative_adv_rate` | 0.420127 | 0.465964 |
| `train/harness/harness-C/training/nonzero_adv_rate` | 0.976932 | 0.985542 |
| `train/harness/harness-C/training/positive_adv_rate` | 0.556805 | 0.519578 |
| `train/harness/harness-C/training/rollouts` | 3468 | 3320 |
| `train/harness/harness-C/training/trained_rollout_share` | 0.152201 | 0.148249 |
| `train/harness/harness-D-pw/training/advantage_mean` | -4.70381e-09 | -6.9642e-10 |
| `train/harness/harness-D-pw/training/negative_adv_rate` | 0.520833 | 0.4375 |
| `train/harness/harness-D-pw/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-D-pw/training/positive_adv_rate` | 0.479167 | 0.5625 |
| `train/harness/harness-D-pw/training/rollouts` | 144 | 208 |
| `train/harness/harness-D-pw/training/trained_rollout_share` | 0.006469 | 0.00942413 |
| `train/harness/harness-D/training/advantage_mean` | 1.49511e-09 | 5.20773e-11 |
| `train/harness/harness-D/training/negative_adv_rate` | 0.432799 | 0.429474 |
| `train/harness/harness-D/training/nonzero_adv_rate` | 0.995068 | 0.978947 |
| `train/harness/harness-D/training/positive_adv_rate` | 0.562269 | 0.549474 |
| `train/harness/harness-D/training/rollouts` | 3244 | 3800 |
| `train/harness/harness-D/training/trained_rollout_share` | 0.145013 | 0.168547 |
| `train/harness/harness-E/training/advantage_mean` | -3.51886e-09 | -6.88445e-09 |
| `train/harness/harness-E/training/negative_adv_rate` | 0.512545 | 0.418605 |
| `train/harness/harness-E/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-E/training/positive_adv_rate` | 0.487455 | 0.581395 |
| `train/harness/harness-E/training/rollouts` | 558 | 430 |
| `train/harness/harness-E/training/trained_rollout_share` | 0.0250674 | 0.0194826 |
| `train/harness/harness-F/training/advantage_mean` | -5.69139e-09 | -3.91538e-09 |
| `train/harness/harness-F/training/negative_adv_rate` | 0.58125 | 0.523649 |
| `train/harness/harness-F/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-F/training/positive_adv_rate` | 0.41875 | 0.476351 |
| `train/harness/harness-F/training/rollouts` | 480 | 592 |
| `train/harness/harness-F/training/trained_rollout_share` | 0.0215633 | 0.0268225 |
| `train/harness/harness-G-pw/training/advantage_mean` | -2.99315e-10 | 1.09696e-08 |
| `train/harness/harness-G-pw/training/negative_adv_rate` | 0.493056 | 0.520833 |
| `train/harness/harness-G-pw/training/nonzero_adv_rate` | 0.9375 | 1 |
| `train/harness/harness-G-pw/training/positive_adv_rate` | 0.444444 | 0.479167 |
| `train/harness/harness-G-pw/training/rollouts` | 144 | 144 |
| `train/harness/harness-G-pw/training/trained_rollout_share` | 0.00606469 | 0.0065244 |
| `train/harness/harness-H/training/advantage_mean` | -3.18037e-09 | 1.68974e-09 |
| `train/harness/harness-H/training/negative_adv_rate` | 0.445847 | 0.457586 |
| `train/harness/harness-H/training/nonzero_adv_rate` | 0.996743 | 0.998776 |
| `train/harness/harness-H/training/positive_adv_rate` | 0.550896 | 0.541191 |
| `train/harness/harness-H/training/rollouts` | 2456 | 2452 |
| `train/harness/harness-H/training/trained_rollout_share` | 0.109973 | 0.11096 |
| `train/harness/harness-I/training/advantage_mean` | 7.35687e-09 | -4.00302e-09 |
| `train/harness/harness-I/training/negative_adv_rate` | 0.325397 | 0.33 |
| `train/harness/harness-I/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-I/training/positive_adv_rate` | 0.674603 | 0.67 |
| `train/harness/harness-I/training/rollouts` | 126 | 100 |
| `train/harness/harness-I/training/trained_rollout_share` | 0.00566038 | 0.00453083 |
| `train/harness/harness-J/training/advantage_mean` | 1.20158e-08 | 4.50414e-09 |
| `train/harness/harness-J/training/negative_adv_rate` | 0.28125 | 0.320755 |
| `train/harness/harness-J/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-J/training/positive_adv_rate` | 0.71875 | 0.679245 |
| `train/harness/harness-J/training/rollouts` | 160 | 159 |
| `train/harness/harness-J/training/trained_rollout_share` | 0.00718778 | 0.00720402 |
| `train/harness/harness-K/training/advantage_mean` | -9.61109e-09 | -4.69392e-09 |
| `train/harness/harness-K/training/negative_adv_rate` | 0.3125 | 0.385057 |
| `train/harness/harness-K/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-K/training/positive_adv_rate` | 0.6875 | 0.614943 |
| `train/harness/harness-K/training/rollouts` | 176 | 174 |
| `train/harness/harness-K/training/trained_rollout_share` | 0.00790656 | 0.00788365 |
| `train/harness/harness-L/training/advantage_mean` | -1.66083e-08 | 6.81507e-09 |
| `train/harness/harness-L/training/negative_adv_rate` | 0.333333 | 0.277778 |
| `train/harness/harness-L/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-L/training/positive_adv_rate` | 0.666667 | 0.722222 |
| `train/harness/harness-L/training/rollouts` | 192 | 144 |
| `train/harness/harness-L/training/trained_rollout_share` | 0.00862534 | 0.0065244 |
| `train/harness/harness-M/training/advantage_mean` | 1.71831e-08 | 3.56683e-09 |
| `train/harness/harness-M/training/negative_adv_rate` | 0.277778 | 0.369792 |
| `train/harness/harness-M/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-M/training/positive_adv_rate` | 0.722222 | 0.630208 |
| `train/harness/harness-M/training/rollouts` | 144 | 192 |
| `train/harness/harness-M/training/trained_rollout_share` | 0.006469 | 0.0086992 |
| `train/harness/harness-N/training/advantage_mean` | -1.34456e-08 | -1.23165e-09 |
| `train/harness/harness-N/training/negative_adv_rate` | 0.380682 | 0.3375 |
| `train/harness/harness-N/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-N/training/positive_adv_rate` | 0.619318 | 0.6625 |
| `train/harness/harness-N/training/rollouts` | 176 | 160 |
| `train/harness/harness-N/training/trained_rollout_share` | 0.00790656 | 0.00724933 |
| `train/harness/harness-O/training/advantage_mean` | 2.20601e-08 | 4.50969e-09 |
| `train/harness/harness-O/training/negative_adv_rate` | 0.575 | 0.53125 |
| `train/harness/harness-O/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-O/training/positive_adv_rate` | 0.425 | 0.46875 |
| `train/harness/harness-O/training/rollouts` | 80 | 160 |
| `train/harness/harness-O/training/trained_rollout_share` | 0.00359389 | 0.00724933 |
| `train/harness/harness-P/training/advantage_mean` | 1.59343e-08 | 3.15506e-09 |
| `train/harness/harness-P/training/negative_adv_rate` | 0.520833 | 0.447115 |
| `train/harness/harness-P/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-P/training/positive_adv_rate` | 0.479167 | 0.552885 |
| `train/harness/harness-P/training/rollouts` | 240 | 208 |
| `train/harness/harness-P/training/trained_rollout_share` | 0.0107817 | 0.00942413 |
| `train/harness/harness-Q/training/advantage_mean` | 2.13768e-08 | -1.02841e-08 |
| `train/harness/harness-Q/training/negative_adv_rate` | 0.552083 | 0.648438 |
| `train/harness/harness-Q/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-Q/training/positive_adv_rate` | 0.447917 | 0.351562 |
| `train/harness/harness-Q/training/rollouts` | 192 | 128 |
| `train/harness/harness-Q/training/trained_rollout_share` | 0.00862534 | 0.00579947 |
| `train/harness/harness-R/training/advantage_mean` | -2.67345e-09 | -2.30414e-09 |
| `train/harness/harness-R/training/negative_adv_rate` | 0.366442 | 0.454102 |
| `train/harness/harness-R/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-R/training/positive_adv_rate` | 0.633558 | 0.545898 |
| `train/harness/harness-R/training/rollouts` | 1037 | 1024 |
| `train/harness/harness-R/training/trained_rollout_share` | 0.0465858 | 0.0463957 |
| `train/harness/harness-S/training/advantage_mean` | -2.66894e-09 | -2.41084e-09 |
| `train/harness/harness-S/training/negative_adv_rate` | 0.558594 | 0.445565 |
| `train/harness/harness-S/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-S/training/positive_adv_rate` | 0.441406 | 0.554435 |
| `train/harness/harness-S/training/rollouts` | 512 | 496 |
| `train/harness/harness-S/training/trained_rollout_share` | 0.0230009 | 0.0224729 |
| `train/harness/harness-T/training/advantage_mean` | 3.45106e-09 | 1.12804e-09 |
| `train/harness/harness-T/training/negative_adv_rate` | 0.418112 | 0.338883 |
| `train/harness/harness-T/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-T/training/positive_adv_rate` | 0.581888 | 0.661117 |
| `train/harness/harness-T/training/rollouts` | 1038 | 1021 |
| `train/harness/harness-T/training/trained_rollout_share` | 0.0466307 | 0.0462598 |
| `train/harness/harness-U/training/advantage_mean` | -8.59847e-10 | 1.53398e-09 |
| `train/harness/harness-U/training/negative_adv_rate` | 0.533203 | 0.489919 |
| `train/harness/harness-U/training/nonzero_adv_rate` | 1 | 1 |
| `train/harness/harness-U/training/positive_adv_rate` | 0.466797 | 0.510081 |
| `train/harness/harness-U/training/rollouts` | 512 | 496 |
| `train/harness/harness-U/training/trained_rollout_share` | 0.0230009 | 0.0224729 |
| `train/passrate/avg_passrate` | 0.578962 | 0.561994 |
| `train/passrate/avg_passrate/chat/dataset-8kb6` | 0.3648 | 0.353015 |
| `train/passrate/avg_passrate/chat/dataset-eup7` | 0.495541 | 0.57805 |
| `train/passrate/avg_passrate/chat/dataset-lm3t` | 0.377678 | 0.323772 |
| `train/passrate/avg_passrate/code/dataset-4onq` | 0.577001 | 0.494757 |
| `train/passrate/avg_passrate/code/dataset-bvg7` | 0.643375 | 0.590135 |
| `train/passrate/avg_passrate/code/dataset-dnpn` | 0.591873 | 0.590418 |
| `train/passrate/avg_passrate/code/dataset-m1dt` | 0.633827 | 0.589805 |
| `train/passrate/avg_passrate/code/dataset-obg8` | 0.534727 | 0.538779 |
| `train/passrate/avg_passrate/code/dataset-sin0` | 0.606763 | 0.599258 |
| `train/passrate/avg_passrate/code/dataset-ta4j` | 0.596867 | 0.54086 |
| `train/passrate/avg_passrate/code/dataset-v7yx` | 0.569818 | 0.565069 |
| `train/passrate/avg_passrate/code/dataset-x7wh` | 0.600596 | 0.550733 |
| `train/passrate/avg_passrate/code/dataset-yfch` | 0.668986 | 0.560145 |
| `train/passrate/avg_passrate/code/dataset-zg6q` | 0.616413 | 0.559917 |
| `train/passrate/avg_passrate/cyber/dataset-9aui` | 0.648355 | 0.556687 |
| `train/passrate/avg_passrate/general/dataset-1doa` | 0.442318 | 0.562345 |
| `train/passrate/avg_passrate/general/dataset-5610` | 0.472283 | 0.513036 |
| `train/passrate/avg_passrate/general/dataset-epqd` | 0.602212 | 0.673347 |
| `train/passrate/avg_passrate/general/dataset-trla` | 0.462906 | 0.53072 |
| `train/passrate/avg_passrate/visual/dataset-053e` | 0.565571 | 0.590499 |
| `train/passrate/avg_passrate/visual/dataset-gtav` | 0.253834 | 0.259772 |
| `train/passrate/avg_passrate/visual/dataset-jzd3` | 0.450904 | 0.378213 |
| `train/passrate/avg_passrate/visual/dataset-ol8x` | 0.485249 | 0.66774 |
| `train/passrate/avg_passrate/visual/dataset-pt5v` | 0.75294 | 0.743089 |
| `train/passrate/avg_passrate/visual/dataset-ve5o` | 0.874941 | 0.851075 |
| `train/passrate/passrate_0_ratio` | 0.0573575 | 0.0623824 |
| `train/passrate/passrate_1_ratio` | 0.0881909 | 0.076819 |
| `train/spec_accept_length/request_mean` | 3.53581 | 2.81937 |
| `train/spec_accept_length/token_mean` | 3.44612 | 2.79267 |
| `train/trace/backpressure_wait_seconds_max` | 0 | 0 |
| `train/trace/backpressure_wait_seconds_sum` | 0 | 0 |
| `train/trace/backpressure_waits` | 0 | 0 |
| `train/trace/drain_wait_seconds` | 2.34426 | 3.85103 |
| `train/trace/failed_writes` | 0 | 0 |
| `train/trace/files` | 4274 | 3117 |
| `train/trace/late_finishes` | 0 | 177 |
| `train/trace/orphan_resolves` | 0 | 0 |
| `train/trace/outcome_write_seconds` | 0.605648 | 0.575178 |
| `train/trace/records` | 1649820 | 1640070 |
| `train/trace/terminal_conflicts` | 0 | 0 |
| `train/trace/writer_seconds_max` | 34.4102 | 21.035 |
| `train/trace/writer_seconds_sum` | 7094.12 | 4347.33 |
| `train/verdicts/carried` | 19150 | 20054 |
| `train/verdicts/dropped_empty_response` | 0 | 0 |
| `train/verdicts/dropped_zero_adv` | 0 | 0 |
| `train/verdicts/expired` | 0 | 753 |
| `train/verdicts/rejected` | 19024 | 15088 |
| `train/verdicts/trained` | 25088 | 25088 |

## train_infer_diff · 11

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `train_infer_diff/new_infer/F(tau=1.5)` | 0.0162633 | 0.020902 |
| `train_infer_diff/new_infer/F(tau=10)` | 0.000126839 | 0.000192145 |
| `train_infer_diff/new_infer/F(tau=2)` | 0.00517569 | 0.00706439 |
| `train_infer_diff/new_infer/F(tau=3)` | 0.001509 | 0.00216418 |
| `train_infer_diff/new_infer/F(tau=5)` | 0.000448506 | 0.000663873 |
| `train_infer_diff/new_infer/diff_abs_max` | 42.1275 | 53.8695 |
| `train_infer_diff/new_infer/diff_abs_mean` | 0.0379067 | 0.0436608 |
| `train_infer_diff/new_infer/diff_abs_std` | 0.114389 | 0.129878 |
| `train_infer_diff/new_infer/kl` | 0.00655812 | 0.00832682 |
| `train_infer_diff/nll_loss/log_probs` | 0.36046 | 0.376767 |
| `train_infer_diff/nll_loss/rollout_log_probs` | 0.353894 | 0.368426 |

## training · 2

| 标签 | Pro s12 | Flash s15 |
| --- | ---: | ---: |
| `training/actor_optimizer_steps` | 1 | 1 |
| `training/global_step` | 12 | 15 |

