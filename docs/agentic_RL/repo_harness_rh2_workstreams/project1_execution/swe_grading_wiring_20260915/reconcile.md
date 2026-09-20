# e2 对账（2026-09-16，Claude；由 `rh2/experiments/e2_reconcile.py` 从 `runs/swe_grading_wiring_20260915/e2/` 的账本生成）

oracle 来源：`env_probe_20260909/ledger/cc_candidate_grading.jsonl`（`gate=candidate` 原组、`gate=candidate_projected` 投影组）。rh2 判定列：`resolved` / `unresolved:<类别>` / `failed_to_grade:<类别>:<detail>` / `apply_failed`（未评分）。同/异只对已评分行比较 resolved 与否；未评分与 infra 记"不可比"。解读见 [e2_report_20260916.md](e2_report_20260916.md)。

## B 组：24 条 DeepSeek 候选 — rh2 vs oracle

| 题 | 尝试 | rh2 判定 | reward | 原组 oracle | 投影组 oracle | 同/异（原） | 同/异（投影） | apply | 投影忽略 | F2P | P2P | 参考缺席 | install rc / s | test rc / s | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Project-MONAI__MONAI-2454 | e2B-20260915/1 | unresolved:tests_failed | 0.0 | infra_failed:test_patch_not_applied:UNPARSED | unresolved:RESOLVED_NO | 异 | 同 | git_apply | tests/test_to_tensor.py | 0/1 | 0/1 | 0 | 0 / 13.344 | 1 / 9.747 |  |
| Project-MONAI__MONAI-6975 | e2B-20260915/1 | apply_failed | None | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 不可比 | 不可比 | apply_failed | - | None/None | None/None | 0 | None / None | None / None | candidate patch failed `git apply --check`; not graded |
| Project-MONAI__MONAI-6975 | e2B-20260915/1 | apply_failed | None | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 不可比 | 不可比 | apply_failed | - | None/None | None/None | 0 | None / None | None / None | candidate patch failed `git apply --check`; not graded |
| conan-io__conan-13326 | e2B-20260915/1 | unresolved:tests_failed | 0.0 | unresolved:RESOLVED_PARTIAL | unresolved:RESOLVED_PARTIAL | 同 | 同 | git_apply | conans/test/unittests/tools/build/test_cppstd.py | 2/3 | 0/67 | 0 | 0 / 2.946 | 1 / 1.218 |  |
| conan-io__conan-13326 | e2B-20260915/1 | unresolved:tests_failed | 0.0 | unresolved:RESOLVED_PARTIAL | unresolved:RESOLVED_PARTIAL | 同 | 同 | git_apply | conans/test/unittests/tools/build/test_cppstd.py | 2/3 | 0/67 | 0 | 0 / 2.273 | 1 / 1.125 |  |
| conan-io__conan-14296 | e2B-20260915/1 | resolved | 1.0 | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 同 | 同 | git_apply | conans/test/integration/toolchains/cmake/test_cmaketoolchain.py | 1/1 | 0/32 | 0 | 0 / 2.497 | 0 / 10.619 |  |
| dask__dask-7656 | e2B-20260915/1 | resolved | 1.0 | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 同 | 同 | git_apply | dask/tests/test_delayed.py | 1/1 | 0/48 | 0 | 0 / 4.037 | 1 / 7.567 |  |
| dask__dask-7894 | e2B-20260915/1 | resolved | 1.0 | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 同 | 同 | git_apply | dask/array/tests/test_overlap.py | 5/5 | 0/75 | 0 | 0 / 2.764 | 0 / 6.042 |  |
| getmoto__moto-5701 | e2B-20260915/1 | unresolved:tests_failed | 0.0 | unresolved:RESOLVED_NO | unresolved:RESOLVED_NO | 同 | 同 | git_apply | tests/test_s3/test_s3.py,tests/test_s3/test_server.py | 1/1 | 1/149 | 1 | 0 / 9.008 | 1 / 27.308 |  |
| getmoto__moto-5899 | e2B-20260915/1 | resolved | 1.0 | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 同 | 同 | git_apply | tests/test_iam/test_iam_groups.py | 1/1 | 0/22 | 0 | 2 / 9.178 | 0 / 5.071 |  |
| getmoto__moto-6470 | e2B-20260915/1 | unresolved:tests_failed | 0.0 | unresolved:RESOLVED_NO | unresolved:RESOLVED_NO | 同 | 同 | git_apply | tests/test_batch/test_batch_compute_envs.py | 0/1 | 0/11 | 0 | 2 / 9.148 | 1 / 10.152 |  |
| getmoto__moto-6913 | e2B-20260915/1 | resolved | 1.0 | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 同 | 同 | git_apply | tests/test_sesv2/test_sesv2.py | 1/1 | 0/17 | 0 | 2 / 9.15 | 0 / 3.67 |  |
| getmoto__moto-6913 | e2B-20260915/1 | resolved | 1.0 | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 同 | 同 | git_apply | tests/test_sesv2/test_sesv2.py | 1/1 | 0/17 | 0 | 2 / 9.07 | 0 / 4.028 |  |
| iterative__dvc-5822 | e2B-20260915/1 | resolved | 1.0 | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 同 | 同 | git_apply | tests/func/test_api.py | 1/1 | 0/1 | 0 | 0 / 39.361 | 1 / 23.143 |  |
| iterative__dvc-5822 | e2B-20260915/1 | resolved | 1.0 | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 同 | 同 | git_apply | tests/func/test_api.py | 1/1 | 0/1 | 0 | 0 / 39.34 | 1 / 20.937 |  |
| iterative__dvc-9395 | e2B-20260915/1 | unresolved:tests_failed | 0.0 | unresolved:RESOLVED_PARTIAL | unresolved:RESOLVED_PARTIAL | 同 | 同 | git_apply | - | 1/2 | 0/27 | 0 | 0 / 40.47 | 1 / 22.579 |  |
| modin-project__modin-6298 | e2B-20260915/1 | failed_to_grade:test_log_parse_failed:eval_log_zero_parsed_tests | None | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 不可比 | 不可比 | git_apply | - | None/None | None/None | 39 | 0 / 5.713 | 1 / 38.941 |  |
| modin-project__modin-6937 | e2B-20260915/1 | failed_to_grade:test_log_parse_failed:eval_log_zero_parsed_tests | None | unresolved:RESOLVED_NO | unresolved:RESOLVED_NO | 不可比 | 不可比 | git_apply | modin/pandas/test/test_io.py | None/None | None/None | 2355 | 0 / 4.101 | 1 / 32.304 |  |
| pandas-dev__pandas-48106 | e2B-20260915/1 | unresolved:tests_failed | 0.0 | unresolved:RESOLVED_NO | unresolved:RESOLVED_NO | 同 | 同 | git_apply | - | 1/16 | 3/1020 | 3 | 0 / 573.078 | 1 / 15.741 |  |
| pandas-dev__pandas-50319 | e2B-20260915/1 | unresolved:tests_failed | 0.0 | unresolved:RESOLVED_NO | unresolved:RESOLVED_NO | 同 | 同 | git_apply | pandas/tests/tslibs/test_parsing.py | 1/1 | 1/109 | 1 | 0 / 596.771 | 0 / 7.982 |  |
| pydantic__pydantic-5706 | e2B-20260915/1 | apply_failed | None | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 不可比 | 不可比 | apply_failed | - | None/None | None/None | 0 | None / None | None / None | candidate patch failed `git apply --check`; not graded |
| pydantic__pydantic-8500 | e2B-20260915/1 | apply_failed | None | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 不可比 | 不可比 | apply_failed | - | None/None | None/None | 0 | None / None | None / None | candidate patch failed `git apply --check`; not graded |
| pydantic__pydantic-8500 | e2B-20260915/1 | apply_failed | None | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 不可比 | 不可比 | apply_failed | - | None/None | None/None | 0 | None / None | None / None | candidate patch failed `git apply --check`; not graded |
| pydantic__pydantic-8793 | e2B-20260915/1 | apply_failed | None | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 不可比 | 不可比 | apply_failed | - | None/None | None/None | 0 | None / None | None / None | candidate patch failed `git apply --check`; not graded |
| pydantic__pydantic-9214 | e2B-20260915/1 | apply_failed | None | unresolved:RESOLVED_NO | unresolved:RESOLVED_NO | 不可比 | 不可比 | apply_failed | - | None/None | None/None | 0 | None / None | None / None | candidate patch failed `git apply --check`; not graded |
| python__mypy-11236 | e2B-20260915/1 | apply_failed | None | unresolved:RESOLVED_NO | unresolved:RESOLVED_NO | 不可比 | 不可比 | apply_failed | - | None/None | None/None | 0 | None / None | None / None | candidate patch failed `git apply --check`; not graded |
| python__mypy-11352 | e2B-20260915/1 | apply_failed | None | unresolved:RESOLVED_PARTIAL | unresolved:RESOLVED_PARTIAL | 不可比 | 不可比 | apply_failed | - | None/None | None/None | 0 | None / None | None / None | candidate patch failed `git apply --check`; not graded |
| python__mypy-12741 | e2B-20260915/1 | resolved | 1.0 | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 同 | 同 | git_apply | - | 1/1 | 0/1 | 0 | 0 / 10.894 | 0 / 3.75 |  |
| python__mypy-12741 | e2B-20260915/1 | resolved | 1.0 | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 同 | 同 | git_apply | - | 1/1 | 0/1 | 0 | 0 / 10.653 | 0 / 3.333 |  |
| python__mypy-16869 | e2B-20260915/1 | resolved | 1.0 | resolved:RESOLVED_FULL | resolved:RESOLVED_FULL | 同 | 同 | git_apply | test-data/unit/stubgen.test | 2/2 | 0/4 | 0 | 0 / 10.182 | 0 / 64.732 |  |

汇总（rh2 判定 × 与投影组 oracle 同/异）：apply_failed·不可比=9, failed_to_grade·不可比=2, resolved·同=11, unresolved·同=8

## A 组：9 题 gold / noop ×2

| 题 | 候选 | 尝试 | 判定 | reward | 参考缺席 | 导入路径 | 运行器变化 | install rc / s | test rc / s | 阶段秒（setup/test/cleanup） | 峰值 MB |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Project-MONAI__MONAI-6975 | gold | 1 | resolved | 1.0 | 0 | /testbed/monai/__init__.py | False | 0 / 10.022 | 0 / 17.378 | 7.495259/36.646848/2.833119 | 892.023 |
| Project-MONAI__MONAI-6975 | gold | 2 | resolved | 1.0 | 0 | /testbed/monai/__init__.py | False | 0 / 9.032 | 0 / 15.786 | 7.20745/34.638034/2.670572 | 858.57 |
| Project-MONAI__MONAI-6975 | noop | 1 | unresolved:tests_failed | 0.0 | 0 | /testbed/monai/__init__.py | False | 0 / 14.328 | 1 / 25.122 | 13.847997/49.257495/3.260573 | 1442.73 |
| Project-MONAI__MONAI-6975 | noop | 2 | unresolved:tests_failed | 0.0 | 0 | /testbed/monai/__init__.py | False | 0 / 10.444 | 1 / 16.669 | 8.269264/36.78698/4.470528 | 918.305 |
| conan-io__conan-13326 | gold | 1 | resolved | 1.0 | 0 | /testbed/conans/__init__.py | False | 0 / 1.985 | 0 / 0.962 | 3.441278/4.314295/0.634202 | 68.398 |
| conan-io__conan-13326 | gold | 2 | resolved | 1.0 | 0 | /testbed/conans/__init__.py | False | 0 / 2.678 | 0 / 1.056 | 3.393703/5.068163/0.512796 | 63.895 |
| conan-io__conan-13326 | noop | 1 | unresolved:tests_failed | 0.0 | 0 | /testbed/conans/__init__.py | False | 0 / 2.647 | 1 / 1.101 | 4.399219/5.105705/0.847647 | 82.777 |
| conan-io__conan-13326 | noop | 2 | unresolved:tests_failed | 0.0 | 0 | /testbed/conans/__init__.py | False | 0 / 2.652 | 1 / 1.023 | 3.116931/5.015092/0.632537 | 66.711 |
| dask__dask-7894 | gold | 1 | resolved | 1.0 | 0 | /testbed/dask/__init__.py | False | 0 / 2.932 | 0 / 5.216 | 5.492497/9.798624/1.832432 | 252.523 |
| dask__dask-7894 | gold | 2 | resolved | 1.0 | 0 | /testbed/dask/__init__.py | False | 0 / 3.035 | 0 / 5.362 | 5.210333/10.044356/1.811277 | 246.066 |
| dask__dask-7894 | noop | 1 | unresolved:tests_failed | 0.0 | 0 | /testbed/dask/__init__.py | False | 0 / 3.229 | 1 / 5.561 | 10.488998/10.448813/1.6849 | 295.852 |
| dask__dask-7894 | noop | 2 | unresolved:tests_failed | 0.0 | 0 | /testbed/dask/__init__.py | False | 0 / 2.914 | 1 / 5.753 | 5.604444/10.344874/1.767511 | 238.148 |
| getmoto__moto-6913 | gold | 1 | resolved | 1.0 | 0 | /testbed/moto/__init__.py | False | 2 / 9.351 | 0 / 4.467 | 4.547575/15.683035/1.024753 | 202.434 |
| getmoto__moto-6913 | gold | 2 | resolved | 1.0 | 0 | /testbed/moto/__init__.py | False | 2 / 9.224 | 0 / 3.33 | 4.711242/14.52368/1.328022 | 203.102 |
| getmoto__moto-6913 | noop | 1 | unresolved:tests_failed | 0.0 | 0 | /testbed/moto/__init__.py | False | 2 / 9.26 | 1 / 5.014 | 4.774551/16.185116/1.338824 | 267.121 |
| getmoto__moto-6913 | noop | 2 | unresolved:tests_failed | 0.0 | 0 | /testbed/moto/__init__.py | False | 2 / 9.339 | 1 / 4.014 | 4.715768/15.343475/1.363126 | 201.492 |
| iterative__dvc-5822 | gold | 1 | resolved | 1.0 | 0 | /testbed/dvc/__init__.py | False | 0 / 38.805 | 1 / 21.283 | 5.111484/61.629432/1.252874 | 241.621 |
| iterative__dvc-5822 | gold | 2 | resolved | 1.0 | 0 | /testbed/dvc/__init__.py | False | 0 / 39.218 | 1 / 21.916 | 4.514637/62.631163/1.398237 | 235.656 |
| iterative__dvc-5822 | noop | 1 | unresolved:tests_failed | 0.0 | 0 | /testbed/dvc/__init__.py | False | 0 / 40.058 | 1 / 20.928 | 8.633996/62.580515/1.404385 | 273.387 |
| iterative__dvc-5822 | noop | 2 | unresolved:tests_failed | 0.0 | 0 | /testbed/dvc/__init__.py | False | 0 / 39.567 | 1 / 21.098 | 4.49492/62.185492/1.209195 | 230.785 |
| modin-project__modin-6937 | gold | 1 | failed_to_grade:test_log_parse_failed:eval_log_zero_parsed_tests | None | 2355 | /testbed/modin/__init__.py | False | 0 / 4.213 | 1 / 31.842 | 7.978919/37.419811/2.414356 | 1577.062 |
| modin-project__modin-6937 | gold | 2 | failed_to_grade:infra_failure:grading_test_timeout_after_1800s:candidate_phase=test | None | 0 | - | None | 0 / 4.296 | None / None | 7.845975/None/3.663895 | 1568.012 |
| modin-project__modin-6937 | noop | 1 | failed_to_grade:test_log_parse_failed:eval_log_zero_parsed_tests | None | 2355 | /testbed/modin/__init__.py | False | 0 / 5.802 | 1 / 40.459 | 9.114567/47.629788/2.844424 | 1833.887 |
| modin-project__modin-6937 | noop | 2 | failed_to_grade:test_log_parse_failed:eval_log_zero_parsed_tests | None | 2355 | /testbed/modin/__init__.py | False | 0 / 4.285 | 1 / 28.87 | 6.756214/34.408311/2.972862 | 1550.566 |
| pandas-dev__pandas-48106 | gold | 1 | unresolved:tests_failed | 0.0 | 3 | /testbed/pandas/__init__.py | False | 0 / 579.445 | 0 / 12.209 | 9.960516/595.430345/3.174642 | 900.379 |
| pandas-dev__pandas-48106 | gold | 2 | unresolved:tests_failed | 0.0 | 3 | /testbed/pandas/__init__.py | False | 0 / 591.537 | 0 / 11.446 | 9.502164/606.707689/3.631267 | 971.102 |
| pandas-dev__pandas-48106 | noop | 1 | unresolved:tests_failed | 0.0 | 3 | /testbed/pandas/__init__.py | False | 0 / 583.632 | 1 / 13.629 | 9.536043/601.055611/3.704931 | 969.559 |
| pandas-dev__pandas-48106 | noop | 2 | unresolved:tests_failed | 0.0 | 3 | /testbed/pandas/__init__.py | False | 0 / 574.509 | 1 / 16.21 | 9.229517/594.749097/4.154564 | 970.312 |
| pydantic__pydantic-8500 | gold | 1 | resolved | 1.0 | 0 | /testbed/pydantic/__init__.py | False | 2 / 0.322 | 0 / 5.082 | 4.265235/6.848548/1.166641 | 193.754 |
| pydantic__pydantic-8500 | gold | 2 | resolved | 1.0 | 0 | /testbed/pydantic/__init__.py | False | 2 / 0.274 | 0 / 3.104 | 4.090412/4.69928/1.158934 | 185.82 |
| pydantic__pydantic-8500 | noop | 1 | unresolved:tests_failed | 0.0 | 0 | /testbed/pydantic/__init__.py | False | 2 / 0.279 | 1 / 4.769 | 4.403965/6.37097/1.169557 | 233.805 |
| pydantic__pydantic-8500 | noop | 2 | unresolved:tests_failed | 0.0 | 0 | /testbed/pydantic/__init__.py | False | 2 / 0.267 | 1 / 2.942 | 4.102491/4.575419/1.129851 | 185.953 |
| python__mypy-12741 | gold | 1 | resolved | 1.0 | 0 | /testbed/mypy/__init__.py | False | 0 / 10.87 | 0 / 2.817 | 3.117269/15.08029/0.603636 | 105.723 |
| python__mypy-12741 | gold | 2 | resolved | 1.0 | 0 | /testbed/mypy/__init__.py | False | 0 / 10.858 | 0 / 3.017 | 3.164649/15.227945/0.614153 | 105.188 |
| python__mypy-12741 | noop | 1 | unresolved:tests_failed | 0.0 | 0 | /testbed/mypy/__init__.py | False | 0 / 10.875 | 1 / 3.775 | 3.863056/16.045834/0.558186 | 119.746 |
| python__mypy-12741 | noop | 2 | unresolved:tests_failed | 0.0 | 0 | /testbed/mypy/__init__.py | False | 0 / 10.92 | 1 / 3.175 | 3.621086/15.487155/0.731471 | 113.164 |

## C 组反例与派生镜像

| 账本 | 题 | 候选 | 镜像 | 判定 | reward | infra detail / stage_error | 参考缺席 | test rc / s | 峰值 MB | shm |
|---|---|---|---|---|---|---|---|---|---|---|
| ledger_e2_C.jsonl | Project-MONAI__MONAI-1121 | gold | xingyaoww/sweb.eval.x86_64.project-monai_s_monai-1121:latest | unresolved:tests_failed | 0.0 | - | 0 | 1 / 423.283 | 3092.215 | 67108864 |
| ledger_e2_C.jsonl | Project-MONAI__MONAI-3205 | gold | xingyaoww/sweb.eval.x86_64.project-monai_s_monai-3205:latest | unresolved:tests_failed | 0.0 | - | 0 | 1 / 14.928 | 805.965 | 67108864 |
| ledger_e2_C.jsonl | getmoto__moto-4799 | gold | xingyaoww/sweb.eval.x86_64.getmoto_s_moto-4799:latest | unresolved:tests_failed | 0.0 | - | 0 | 1 / 25.669 | 318.578 | 67108864 |
| ledger_e2_C.jsonl | Project-MONAI__MONAI-763 | gold | xingyaoww/sweb.eval.x86_64.project-monai_s_monai-763:latest | resolved | 1.0 | - | 0 | 1 / 32.503 | 1429.035 | 67108864 |
| ledger_e2_C_shm1g.jsonl | Project-MONAI__MONAI-763 | gold | xingyaoww/sweb.eval.x86_64.project-monai_s_monai-763:latest | failed_to_grade:test_log_parse_failed:eval_log_zero_parsed_tests | None | eval_log_zero_parsed_tests | 9 | 137 / 478.615 | 4096.0 | 1073741824 |
| ledger_e2_derived.jsonl | getmoto__moto-6913 | cc | rh2-derived/moto-6913:20260915 | resolved | 1.0 | - | 0 | 0 / 3.417 | 202.449 | 67108864 |
| ledger_e2_derived.jsonl | pydantic__pydantic-8500 | cc | rh2-derived/pydantic-8500:20260915 | apply_failed | None | - | 0 | None / None | None | 67108864 |
| ledger_e2_derived.jsonl | getmoto__moto-6913 | noop | rh2-derived/moto-6913:20260915 | unresolved:tests_failed | 0.0 | - | 0 | 1 / 3.255 | 225.914 | 67108864 |
| ledger_e2_derived.jsonl | getmoto__moto-6913 | gold | rh2-derived/moto-6913:20260915 | resolved | 1.0 | - | 0 | 0 / 3.266 | 205.484 | 67108864 |
| ledger_e2_derived.jsonl | pydantic__pydantic-8500 | noop | rh2-derived/pydantic-8500:20260915 | unresolved:tests_failed | 0.0 | - | 0 | 1 / 2.751 | 188.996 | 67108864 |
| ledger_e2_derived.jsonl | pydantic__pydantic-8500 | gold | rh2-derived/pydantic-8500:20260915 | resolved | 1.0 | - | 0 | 0 / 3.01 | 187.426 | 67108864 |
| ledger_e2_derived.jsonl | Project-MONAI__MONAI-1121 | gold | rh2-derived/monai-1121:20260915 | resolved | 1.0 | - | 0 | 1 / 742.405 | 2346.43 | 67108864 |
