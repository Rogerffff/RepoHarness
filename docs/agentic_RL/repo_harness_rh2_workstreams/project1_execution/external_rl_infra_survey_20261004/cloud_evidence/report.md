# 52 题探针：逐题环境准备与评分开销

生成于 2026-10-04T08:53:55.617139+00:00（analyze_env_costs.py，只读 GPU 探针证据）。
单位秒；actor 列为可用尝试的中位数，评分列为候选段实际运行的评分的中位数。
列：GS=actor git_sanitize，TI=actor trusted_init（chown -R /testbed），Cen=baseline_census，Net=network_and_container，
Boot=CC 引导（CLI 安装 + agent 用户初始化），Pre=启动前合计，TTFR=到第一条模型请求，
Ovh=actor 非 CC 开销，CC=CC 求解时长，Gtot=评分合计，gGS=评分侧 git sanitize，
Setup=评分可信 setup（官方测试恢复 + 权限交接），Inst=安装，Test=候选测试，
Cost=Ovh+Gtot，n_g=未截断评分数 / 评分数。

| task | src | GS | TI | Cen | Net | Boot | Pre | TTFR | Ovh | CC | Gtot | gGS | Setup | Inst | Test | Cost | n_g | compile |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| pandas-dev__pandas-48106 | SWE | 70.8 | 20.4 | 0.6 | 1.2 | 1.8 | 102.5 | 110.3 | 118.0 | 112 | 1220.2 | 69.3 | 816.2 | 321.9 | 7.7 | 1338 | 2/2 | needs compile cache |
| pandas-dev__pandas-50319 | SWE | 73.7 | 19.3 | 0.6 | 1.2 | 1.8 | 104.4 | 112.1 | 123.3 | 278 | 1004.3 | 74.0 | 597.8 | 321.1 | 3.0 | 1128 | 2/2 | needs compile cache |
| Project-MONAI__MONAI-6975 | SWE | 8.4 | 10.4 | 0.2 | 1.2 | 1.8 | 28.4 | 35.7 | 42.2 | 347 | 714.9 | 8.4 | 662.4 | 17.0 | 20.2 | 757 | 2/2 | no |
| Project-MONAI__MONAI-3715 | SWE | 6.6 | 7.4 | 0.2 | 7.2 | 1.8 | 29.8 | 37.1 | 48.9 | 33 | 546.6 | 6.3 | 505.2 | 17.5 | 9.2 | 595 | 2/2 | no |
| dask__dask-7305 | SWE | 11.6 | 3.9 | 0.1 | 1.3 | 1.8 | 24.9 | 32.1 | 38.3 | 196 | 508.0 | 11.6 | 477.9 | 0.9 | 15.2 | 546 | 1/2 | no |
| orange3__50f6a758f1c66b8f4a18806714e3c2f4cefcab3 | R2E | 12.5 | 238.1 | 1.5 | 1.2 | 1.9 | 261.6 | 268.6 | 279.7 | 74 | 263.8 | 12.4 | 243.9 | skip | 3.8 | 544 | 2/2 | no (install skipped) |
| dask__dask-7138 | SWE | 11.5 | 3.6 | 0.1 | 1.3 | 1.8 | 24.5 | 31.9 | 38.3 | 34 | 487.5 | 11.6 | 464.8 | 1.6 | 7.2 | 526 | 1/2 | no |
| orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b423 | R2E | 13.7 | 208.7 | 1.3 | 1.2 | 1.9 | 233.2 | 240.5 | 250.7 | 59 | 218.1 | 13.1 | 198.6 | skip | 3.0 | 469 | 2/2 | no (install skipped) |
| orange3__4014f2483e3bab0621c9ae0f994947c00818325 | R2E | 12.7 | 210.3 | 1.3 | 1.3 | 1.9 | 233.9 | 240.9 | 251.1 | 76 | 215.9 | 11.7 | 199.2 | skip | 1.5 | 467 | 2/2 | no (install skipped) |
| Project-MONAI__MONAI-2446 | SWE | 5.5 | 6.0 | 0.2 | 1.2 | 1.8 | 20.9 | 28.2 | 34.6 | 61 | 414.1 | 5.5 | 381.9 | 14.5 | 7.0 | 449 | 2/2 | no |
| dask__dask-9378 | SWE | 13.7 | 4.2 | 0.1 | 1.3 | 1.8 | 27.4 | 34.7 | 40.9 | 189 | 406.5 | 13.8 | 383.9 | 1.0 | 5.3 | 447 | 1/2 | no |
| dask__dask-8801 | SWE | 13.1 | 4.2 | 0.1 | 1.3 | 1.8 | 26.8 | 34.1 | 40.2 | 56 | 387.0 | 13.1 | 369.5 | 0.9 | 1.2 | 427 | 1/2 | no |
| dask__dask-7656 | SWE | 11.7 | 3.7 | 0.1 | 1.2 | 1.8 | 24.7 | 31.9 | 38.2 | 42 | 386.0 | 11.8 | 365.9 | 3.7 | 1.5 | 424 | 2/2 | no |
| iterative__dvc-9395 | SWE | 17.3 | 5.6 | 0.1 | 1.3 | 1.9 | 32.5 | 39.9 | 127.4 | 231 | 268.1 | 16.8 | 228.0 | 3.9 | 16.8 | 395 | 1/1 | no |
| getmoto__moto-7584 | SWE | 21.1 | 19.6 | 0.4 | 1.2 | 1.9 | 50.9 | 58.2 | 111.2 | 59 | 254.8 | 21.5 | 219.9 | 4.9 | 1.0 | 366 | 2/2 | no |
| iterative__dvc-4166 | SWE | 12.7 | 3.1 | 0.1 | 1.2 | 1.9 | 25.3 | 32.6 | 38.9 | 244 | 272.6 | 13.0 | 249.4 | 3.0 | 3.5 | 311 | 2/2 | no |
| getmoto__moto-5960 | SWE | 13.3 | 15.5 | 0.3 | 1.3 | 1.8 | 38.6 | 45.9 | 52.5 | 63 | 251.7 | 13.4 | 217.3 | 4.7 | 13.4 | 304 | 2/2 | no |
| getmoto__moto-6114 | SWE | 14.0 | 16.0 | 0.3 | 1.2 | 1.8 | 40.0 | 47.7 | 54.5 | 90 | 247.5 | 14.1 | 222.3 | 4.6 | 3.9 | 302 | 3/3 | no |
| getmoto__moto-6408 | SWE | 15.2 | 16.7 | 0.3 | 1.2 | 1.9 | 42.0 | 49.2 | 56.0 | 141 | 242.8 | 15.3 | 213.0 | 5.1 | 6.3 | 299 | 2/2 | no |
| iterative__dvc-5839 | SWE | 13.4 | 4.8 | 0.1 | 1.3 | 1.9 | 27.6 | 36.2 | 43.1 | 24 | 248.4 | 13.3 | 225.7 | 3.6 | 1.1 | 292 | 2/2 | no |
| getmoto__moto-6185 | SWE | 14.3 | 16.0 | 0.3 | 1.3 | 1.8 | 40.2 | 47.5 | 54.7 | 230 | 226.3 | 15.4 | 199.5 | 5.0 | 3.1 | 281 | 2/2 | no |
| getmoto__moto-5406 | SWE | 11.6 | 13.3 | 0.2 | 1.2 | 1.9 | 34.5 | 41.9 | 48.9 | 60 | 223.2 | 11.9 | 201.0 | 2.6 | 2.8 | 272 | 2/2 | no |
| orange3__9b5494e26f407b75e79699c9d40be6df1d80a04 | R2E | 10.5 | 110.2 | 0.8 | 1.2 | 1.8 | 131.0 | 138.0 | 147.0 | 47 | 125.0 | 10.5 | 108.9 | skip | 2.5 | 272 | 2/2 | no (install skipped) |
| iterative__dvc-6954 | SWE | 14.2 | 4.7 | 0.1 | 1.3 | 2.0 | 28.5 | 35.9 | 42.3 | 55 | 219.5 | 14.2 | 197.6 | 3.5 | 1.6 | 262 | 2/2 | no |
| datalad__6b6fa3898546793fa3517def09f85a74d51ec4b | R2E | 1.0 | 112.3 | 0.8 | 1.3 | 1.8 | 123.3 | 130.3 | 138.9 | 37 | 112.8 | 0.9 | 108.9 | skip | 1.3 | 252 | 2/2 | no (install skipped) |
| pydantic__pydantic-9066 | SWE | 5.5 | 4.1 | 0.1 | 1.3 | 2.1 | 19.4 | 27.0 | 33.1 | 59 | 213.5 | 5.2 | 200.1 | 2.1 | 3.6 | 247 | 2/2 | no |
| pydantic__pydantic-8567 | SWE | 5.3 | 3.3 | 0.1 | 1.2 | 2.1 | 18.4 | 25.9 | 32.2 | 86 | 212.9 | 5.2 | 197.7 | 3.1 | 3.0 | 245 | 2/2 | no |
| pydantic__pydantic-8316 | SWE | 4.7 | 4.1 | 0.1 | 1.3 | 1.8 | 18.2 | 25.4 | 32.1 | 36 | 212.2 | 4.7 | 201.4 | 2.0 | 1.7 | 244 | 2/2 | no |
| pydantic__pydantic-8511 | SWE | 4.8 | 4.1 | 0.1 | 1.3 | 1.8 | 18.3 | 25.5 | 31.6 | 83 | 197.1 | 4.8 | 185.2 | 2.3 | 2.3 | 229 | 2/2 | no |
| pydantic__pydantic-5662 | SWE | 3.2 | 2.6 | 0.1 | 1.3 | 1.9 | 15.3 | 23.6 | 29.9 | 30 | 189.5 | 3.2 | 179.2 | 1.3 | 1.3 | 219 | 2/2 | no |
| pydantic__pydantic-6283 | SWE | 3.8 | 3.4 | 0.1 | 1.3 | 1.8 | 16.6 | 24.1 | 30.1 | 82 | 186.6 | 3.7 | 176.1 | 1.3 | 1.1 | 217 | 2/2 | no |
| aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e5 | R2E | 4.7 | 61.3 | 0.4 | 1.2 | 1.8 | 75.4 | 82.4 | 89.5 | 84 | 94.3 | 4.4 | 58.6 | skip | 29.6 | 184 | 2/2 | no (install skipped) |
| aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343 | R2E | 4.6 | 65.7 | 0.4 | 1.3 | 2.0 | 80.2 | 87.7 | 94.5 | 125 | 77.3 | 4.4 | 65.4 | skip | 5.7 | 172 | 2/2 | no (install skipped) |
| numpy__d805e9b66228e68a0eb14d901cd350159c49af18 | R2E | 16.4 | 25.3 | 0.5 | 12.8 | 2.4 | 63.8 | 71.3 | 114.3 | 164 | 47.8 | 18.2 | 19.2 | skip | 1.4 | 162 | 2/2 | no (install skipped) |
| python__mypy-15184 | SWE | 14.0 | 10.9 | 0.2 | 1.2 | 1.9 | 34.5 | 41.7 | 48.7 | 54 | 99.8 | 14.0 | 76.7 | 2.5 | 0.8 | 149 | 2/2 | no |
| conan-io__conan-15422 | SWE | 16.3 | 8.4 | 0.2 | 1.2 | 1.8 | 34.1 | 41.4 | 47.6 | 89 | 97.2 | 16.3 | 72.9 | 1.1 | 4.0 | 145 | 2/2 | no |
| conan-io__conan-11594 | SWE | 10.1 | 10.1 | 0.2 | 1.3 | 1.8 | 29.9 | 37.2 | 43.8 | 72 | 98.2 | 10.1 | 81.9 | 1.1 | 1.0 | 142 | 2/2 | no |
| conan-io__conan-12397 | SWE | 10.5 | 10.3 | 0.2 | 1.3 | 1.9 | 30.8 | 38.1 | 45.4 | 42 | 95.0 | 10.6 | 79.3 | 1.1 | 0.9 | 140 | 2/2 | no |
| conan-io__conan-14177 | SWE | 15.3 | 7.9 | 0.2 | 1.2 | 1.8 | 33.0 | 40.3 | 46.6 | 42 | 93.7 | 15.3 | 73.8 | 1.1 | 0.5 | 140 | 2/2 | no |
| conan-io__conan-13230 | SWE | 15.1 | 8.0 | 0.2 | 1.2 | 1.8 | 32.6 | 39.7 | 46.2 | 42 | 91.6 | 15.0 | 71.9 | 1.2 | 0.5 | 138 | 2/2 | no |
| python__mypy-10174 | SWE | 9.0 | 11.1 | 0.2 | 1.2 | 1.8 | 29.5 | 36.8 | 43.7 | 208 | 92.1 | 9.1 | 71.3 | 2.1 | 1.7 | 136 | 2/2 | no |
| conan-io__conan-13403 | SWE | 15.0 | 7.4 | 0.2 | 1.3 | 1.9 | 32.2 | 39.5 | 46.0 | 57 | 86.3 | 14.6 | 67.8 | 1.1 | 0.5 | 132 | 2/2 | no |
| pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96 | R2E | 9.5 | 37.0 | 0.5 | 1.3 | 2.0 | 56.9 | 64.5 | 71.8 | 55 | 48.5 | 8.4 | 37.4 | skip | 0.8 | 120 | 2/2 | no (install skipped) |
| pillow__a682ceaf47abbe28dc70c6bd4aab06f8f3f4ac90 | R2E | 10.4 | 36.2 | 0.5 | 1.2 | 1.9 | 56.6 | 63.9 | 71.4 | 75 | 48.4 | 9.8 | 36.0 | skip | 1.1 | 120 | 2/2 | no (install skipped) |
| pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07 | R2E | 9.4 | 37.1 | 0.5 | 1.2 | 1.8 | 56.5 | 63.7 | 70.9 | 221 | 48.5 | 8.9 | 37.0 | skip | 0.7 | 119 | 2/2 | no (install skipped) |
| coveragepy__ea6906b092d9bb09285094eee94e322d2cb4 | R2E | 2.8 | 39.5 | 0.3 | 1.2 | 1.8 | 51.8 | 58.9 | 65.6 | 50 | 45.2 | 2.7 | 39.3 | skip | 1.8 | 111 | 3/3 | no (install skipped) |
| scrapy__a95a338eeada7275a5289cf036136610ebaf07eb | R2E | 3.6 | 24.5 | 0.2 | 1.2 | 1.8 | 37.6 | 44.8 | 51.8 | 28 | 31.4 | 3.5 | 25.4 | skip | 0.9 | 83 | 2/2 | no (install skipped) |
| coveragepy__016af5f6352d69206ac8f7537c2b18828767 | R2E | 2.4 | 25.7 | 0.2 | 1.4 | 1.9 | 37.7 | 44.9 | 51.7 | 63 | 31.2 | 2.1 | 25.0 | skip | 2.6 | 83 | 2/2 | no (install skipped) |
| coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140 | R2E | 2.3 | 24.8 | 0.2 | 1.3 | 1.9 | 36.5 | 43.5 | 50.2 | 58 | 29.8 | 2.2 | 24.3 | skip | 2.0 | 80 | 2/2 | no (install skipped) |
| coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b | R2E | 2.4 | 23.5 | 0.2 | 1.2 | 1.9 | 35.2 | 42.6 | 49.6 | 50 | 30.1 | 2.5 | 22.9 | skip | 3.2 | 80 | 2/2 | no (install skipped) |
| aiohttp__618335186f22834c0d8daabcf53ccf44d42488a | R2E | 0.7 | 8.6 | 0.1 | 1.3 | 1.8 | 18.6 | 25.6 | 31.6 | 70 | 11.4 | 0.6 | 8.5 | skip | 0.7 | 43 | 2/2 | no (install skipped) |
| aiohttp__240da100151933883d7dea0528d45877df025b9 | R2E | 0.3 | 8.4 | 0.1 | 1.3 | 1.7 | 17.7 | 24.6 | 31.3 | 44 | 10.6 | 0.3 | 8.2 | skip | 0.7 | 42 | 2/2 | no (install skipped) |

## 覆盖率

- 题目 52（SWE-Gym 34，R2E 18）；尝试 106；actor 计时 106/106；网关首请求 106/106；评分报告 105/106；候选段实际运行的评分 101/105。
- 两次评分都未截断的题 47/52；缺失或截断：dask__dask-7138（gpu1003-dask7138-coder-a1:grading_control_surface_protect_timeout_after_300s）；dask__dask-7305（gpu1003-dask7305-coder-a1:grading_control_surface_protect_timeout_after_300s）；dask__dask-8801（gpu1003-dask8801-coder-a1:grading_control_surface_protect_timeout_after_300s）；dask__dask-9378（gpu1003-dask9378-coder-a1:grading_control_surface_protect_timeout_after_300s）；iterative__dvc-9395（gpu1003-dvc9395-coder-a1）
- 评分权限路径：{'plain_fresh_no_template': 105}（GPU frozen_code_v6–v9 无 prepared_image.py / performance.py）。
- 时间重叠的作业数最大 0（严格串行）。安装日志中的网络下载：0。

## 跨题汇总（逐题中位数 → 跨题 median / p90）

| metric | all n | all median | all p90 | SWE median | SWE p90 | R2E median | R2E p90 |
|---|---:|---:|---:|---:|---:|---:|---:|
| actor_git_sanitize_s_med | 52 | 11.0 | 16.2 | 12.9 | 17.0 | 4.6 | 13.0 |
| actor_trusted_init_s_med | 52 | 10.6 | 65.3 | 7.4 | 16.5 | 37.1 | 209.2 |
| actor_baseline_census_s_med | 52 | 0.2 | 0.6 | 0.2 | 0.3 | 0.4 | 1.3 |
| actor_network_and_container_s_med | 52 | 1.3 | 1.3 | 1.3 | 1.3 | 1.3 | 1.3 |
| actor_cc_bootstrap_s_med | 52 | 1.8 | 2.0 | 1.8 | 1.9 | 1.9 | 2.0 |
| actor_cc_cli_install_s_med | 52 | 1.8 | 1.9 | 1.8 | 1.9 | 1.8 | 2.0 |
| actor_env_facts_step_s_med | 52 | 5.5 | 5.7 | 5.5 | 5.7 | 5.2 | 5.2 |
| actor_launch_gap_s_med | 52 | 7.3 | 7.6 | 7.3 | 7.7 | 7.1 | 7.5 |
| actor_pre_launch_s_med | 52 | 33.6 | 104.2 | 29.6 | 41.4 | 56.8 | 233.4 |
| actor_time_to_first_model_request_s_med | 52 | 40.8 | 111.9 | 37.0 | 48.8 | 64.2 | 240.6 |
| actor_post_solve_approx_s_med | 52 | 6.8 | 11.0 | 6.5 | 10.2 | 7.2 | 10.5 |
| actor_post_quiescence_to_finish_s_med | 52 | 1.4 | 3.1 | 1.3 | 4.0 | 1.7 | 2.9 |
| actor_non_cc_overhead_s_med | 52 | 48.8 | 127.0 | 43.7 | 94.7 | 71.6 | 250.8 |
| actor_cc_duration_s_med | 52 | 62.1 | 219.4 | 62.1 | 231.1 | 61.1 | 136.5 |
| grading_total_s_med | 52 | 204.7 | 480.1 | 234.5 | 535.0 | 48.5 | 216.6 |
| grader_git_sanitize_s_med | 52 | 11.1 | 16.2 | 13.0 | 16.6 | 4.4 | 12.6 |
| grader_trusted_setup_s_med | 52 | 191.4 | 456.7 | 207.2 | 497.0 | 37.2 | 198.8 |
| install_s_med | 34 | 2.5 | 16.2 | 2.5 | 16.2 | – | – |
| candidate_test_s_med | 52 | 2.2 | 9.1 | 2.9 | 12.1 | 1.6 | 4.4 |
| grader_other_s_med | 52 | 0.8 | 2.7 | 1.3 | 2.9 | 0.1 | 0.1 |
| non_model_cost_per_attempt_s | 52 | 245.8 | 541.8 | 286.2 | 580.7 | 120.1 | 467.5 |

## 非模型时间构成（101 次评分完整的尝试；同批 CC 执行合计 9217s）

- actor_git_sanitize: 1202s (4.1%)
- actor_trusted_init: 3215s (11.0%)
- actor_cc_bootstrap: 188s (0.6%)
- actor_other_non_cc: 2471s (8.4%)
- grader_git_sanitize: 1195s (4.1%)
- grader_trusted_setup: 18729s (64.0%)
- grader_install: 1521s (5.2%)
- grader_candidate_test: 395s (1.4%)
- grader_other: 357s (1.2%)

## 编译缓存分类

- pandas-dev__pandas-48106: needs compile cache — compile=64 cython=0 ext=42; install median 321.876s; link=42; 改动原生源码的候选：无
- pandas-dev__pandas-50319: needs compile cache — compile=66 cython=2 ext=43; install median 321.092s; link=43; 改动原生源码的候选：['gpu1003-pandas50319-coder-a1', 'gpu1003-pandas50319-qwen36-a1']
- 仓库内有原生二进制、但评分安装段被跳过的 R2E 题（候选的 C/Cython 改动不会被评分侧重编）：coveragepy__016af5f6352d(1 .so), coveragepy__5dbbe1430c16(1 .so), coveragepy__ea6906b092d9(1 .so), coveragepy__f5eb5f215918(1 .so), numpy__d805e9b66228e68a0(12 .so), orange3__22e98f8f4cccc25(22 .so), orange3__4014f2483e3bab0(22 .so), orange3__50f6a758f1c66b8(22 .so), orange3__9b5494e26f407b7(11 .so), pillow__2d01f7d02243d1b9(5 .so), pillow__3a61c9e95e5c0a2d(5 .so), pillow__a682ceaf47abbe28(5 .so)
