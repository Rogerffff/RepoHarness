# 来源对账（rh2 vs oracle）

生成：2026-09-15T18:30:26.069443+00:00（screening_facts/0.1，只读汇总，不下因果结论）

口径：rh2 逐 ID 状态 = 离线 `parse_eval_log_v2` 重解析 eval 日志（parser_derived）；
oracle 逐 ID 状态 = 阶段一 `status_map.json`（oracle），按官方口径规约成 passed/failed/skipped/missing。
只列差异；没有 oracle 行的运行标 `oracle 缺席`。

## swe_gym_lite::conan-io__conan-13326

- oracle[empty]：verdict=RESOLVED_NO，result=passed，rc_install=0，rc_test=1，status_map=有
- oracle[gold]：verdict=RESOLVED_FULL，result=passed，rc_install=0，rc_test=0，status_map=有

### replay-e1-20260915 · a1 · noop （ledger_e1.jsonl:2）

- rh2 判定：outcome=unresolved，reward=0.0，F2P 0/3，P2P 失败 0/67，infra=None
- 离线重解析：resolution=RESOLVED_NO，apply_ok=True，解析条数=70（段外 0），参考缺席=0，跳过=0；与 sidecar 一致=True，与账本计数一致=True
- 逐 ID 对账（oracle gate=empty）：无差异（rh2 {'F2P:failed': 3, 'P2P:passed': 67}）
- 条件差异（rh2 → oracle）：network: deny_all → none；测试执行用户: rh2grader → root；memory_bytes: 4294967296 → 8589934592

### replay-e1-20260915 · a1 · gold （ledger_e1.jsonl:6）

- rh2 判定：outcome=resolved，reward=1.0，F2P 3/3，P2P 失败 0/67，infra=None
- 离线重解析：resolution=RESOLVED_FULL，apply_ok=True，解析条数=70（段外 0），参考缺席=0，跳过=0；与 sidecar 一致=True，与账本计数一致=True
- 逐 ID 对账（oracle gate=gold）：无差异（rh2 {'F2P:passed': 3, 'P2P:passed': 67}）
- 条件差异（rh2 → oracle）：network: deny_all → none；测试执行用户: rh2grader → root；memory_bytes: 4294967296 → 8589934592

## swe_gym_lite::iterative__dvc-5822

- oracle[empty]：verdict=RESOLVED_NO，result=passed，rc_install=0，rc_test=1，status_map=有
- oracle[gold]：verdict=RESOLVED_FULL，result=passed，rc_install=0，rc_test=1，status_map=有

### replay-e1-20260915 · a1 · noop （ledger_e1.jsonl:3）

- rh2 判定：outcome=unresolved，reward=0.0，F2P 0/1，P2P 失败 0/1，infra=None
- 离线重解析：resolution=RESOLVED_NO，apply_ok=True，解析条数=50（段外 1），参考缺席=0，跳过=0；与 sidecar 一致=True，与账本计数一致=True
- 逐 ID 对账（oracle gate=empty）：无差异（rh2 {'F2P:failed': 1, 'P2P:passed': 1}）
- 条件差异（rh2 → oracle）：network: deny_all → none；测试执行用户: rh2grader → root；memory_bytes: 4294967296 → 8589934592

### replay-e1-20260915 · a1 · gold （ledger_e1.jsonl:7）

- rh2 判定：outcome=resolved，reward=1.0，F2P 1/1，P2P 失败 0/1，infra=None
- 离线重解析：resolution=RESOLVED_FULL，apply_ok=True，解析条数=50（段外 1），参考缺席=0，跳过=0；与 sidecar 一致=True，与账本计数一致=True
- 逐 ID 对账（oracle gate=gold）：无差异（rh2 {'F2P:passed': 1, 'P2P:passed': 1}）
- 条件差异（rh2 → oracle）：network: deny_all → none；测试执行用户: rh2grader → root；memory_bytes: 4294967296 → 8589934592

## swe_gym_lite::pandas-dev__pandas-48106

- oracle[empty]：verdict=RESOLVED_NO，result=passed，rc_install=0，rc_test=1，status_map=有
- oracle[gold]：verdict=RESOLVED_NO，result=failed，rc_install=0，rc_test=0，status_map=有

### replay-e1-20260915 · a1 · noop （ledger_e1.jsonl:4）

- rh2 判定：outcome=failed_to_grade，reward=None，F2P None/None，P2P 失败 None/None，infra=grading_trusted_setup_failed:setup_exit_code:rc=1:
- 离线重解析：resolution=RESOLVED_NO，apply_ok=False，解析条数=0（段外 0），参考缺席=1036，跳过=0；与 sidecar 一致=None，与账本计数一致=None
- 逐 ID 对账（oracle gate=empty）：rh2 侧无测试结果（apply_ok=false，outcome=failed_to_grade，infra=grading_trusted_setup_failed:setup_exit_code:rc=1:），全部 1033 个参考 ID 在 rh2 侧 missing；不是判定分歧，是这次运行没跑到测试。
- 条件差异（rh2 → oracle）：network: deny_all → none；测试执行用户: rh2grader → root；memory_bytes: 4294967296 → 8589934592

### replay-e1-20260915 · a1 · gold （ledger_e1.jsonl:8）

- rh2 判定：outcome=failed_to_grade，reward=None，F2P None/None，P2P 失败 None/None，infra=grading_trusted_setup_failed:setup_exit_code:rc=1:
- 离线重解析：resolution=RESOLVED_NO，apply_ok=False，解析条数=0（段外 0），参考缺席=1036，跳过=0；与 sidecar 一致=None，与账本计数一致=None
- 逐 ID 对账（oracle gate=gold）：rh2 侧无测试结果（apply_ok=false，outcome=failed_to_grade，infra=grading_trusted_setup_failed:setup_exit_code:rc=1:），全部 1033 个参考 ID 在 rh2 侧 missing；不是判定分歧，是这次运行没跑到测试。
- 条件差异（rh2 → oracle）：network: deny_all → none；测试执行用户: rh2grader → root；memory_bytes: 4294967296 → 8589934592

### replay-e1-pandas-20260915 · a1 · noop （ledger_e1_pandas.jsonl:1）

- rh2 判定：outcome=failed_to_grade，reward=None，F2P None/None，P2P 失败 None/None，infra=grading_control_surface_protect_timeout_after_300s
- 离线重解析：resolution=RESOLVED_NO，apply_ok=False，解析条数=0（段外 0），参考缺席=1036，跳过=0；与 sidecar 一致=None，与账本计数一致=None
- 逐 ID 对账（oracle gate=empty）：rh2 侧无测试结果（apply_ok=false，outcome=failed_to_grade，infra=grading_control_surface_protect_timeout_after_300s），全部 1033 个参考 ID 在 rh2 侧 missing；不是判定分歧，是这次运行没跑到测试。
- 条件差异（rh2 → oracle）：network: deny_all → none；测试执行用户: rh2grader → root；memory_bytes: 4294967296 → 8589934592

### replay-e1-pandas-20260915 · a1 · gold （ledger_e1_pandas.jsonl:2）

- rh2 判定：outcome=unresolved，reward=0.0，F2P 16/16，P2P 失败 3/1020，infra=None
- 离线重解析：resolution=RESOLVED_NO，apply_ok=True，解析条数=1037（段外 1），参考缺席=3，跳过=0；与 sidecar 一致=True，与账本计数一致=True
- 逐 ID 对账（oracle gate=gold）：无差异（rh2 {'F2P:passed': 16, 'P2P:missing': 3, 'P2P:passed': 1017}）
- 条件差异（rh2 → oracle）：network: deny_all → none；测试执行用户: rh2grader → root；memory_bytes: 4294967296 → 8589934592

## swe_gym_lite::python__mypy-12741

- oracle[empty]：verdict=RESOLVED_NO，result=passed，rc_install=0，rc_test=1，status_map=有
- oracle[gold]：verdict=RESOLVED_FULL，result=passed，rc_install=0，rc_test=0，status_map=有

### replay-e1-20260915 · a1 · noop （ledger_e1.jsonl:1）

- rh2 判定：outcome=unresolved，reward=0.0，F2P 0/1，P2P 失败 0/1，infra=None
- 离线重解析：resolution=RESOLVED_NO，apply_ok=True，解析条数=2（段外 0），参考缺席=0，跳过=0；与 sidecar 一致=True，与账本计数一致=True
- 逐 ID 对账（oracle gate=empty）：无差异（rh2 {'F2P:failed': 1, 'P2P:passed': 1}）
- 条件差异（rh2 → oracle）：network: deny_all → none；测试执行用户: rh2grader → root；memory_bytes: 4294967296 → 8589934592

### replay-e1-20260915 · a1 · gold （ledger_e1.jsonl:5）

- rh2 判定：outcome=resolved，reward=1.0，F2P 1/1，P2P 失败 0/1，infra=None
- 离线重解析：resolution=RESOLVED_FULL，apply_ok=True，解析条数=2（段外 0），参考缺席=0，跳过=0；与 sidecar 一致=True，与账本计数一致=True
- 逐 ID 对账（oracle gate=gold）：无差异（rh2 {'F2P:passed': 1, 'P2P:passed': 1}）
- 条件差异（rh2 → oracle）：network: deny_all → none；测试执行用户: rh2grader → root；memory_bytes: 4294967296 → 8589934592

