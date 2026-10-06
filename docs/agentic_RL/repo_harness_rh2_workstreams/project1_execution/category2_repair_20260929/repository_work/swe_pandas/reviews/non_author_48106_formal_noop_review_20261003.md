# Pandas 48106 R13 正式 NoOp CPU 原件独立窄核（2026-10-03）

结论：本次正式 NoOp 原件在所核范围内成立，未发现阻断。真实 manager 报告为 `reward=0.0`、`outcome=unresolved`、`failure_category=tests_failed`；16 个来源 F2P 全失败，1020 个来源 P2P 全通过，参考缺席为 0。该 NoOp 行满足冻结 `load_env_qualifications` 的接受条件，可作为相同镜像、脚本和材料身份下的环境资格来源。

**只验收已完成的 NoOp 臂。** 原回执为 `finished arm only; task may still be running`；`matrix_state.json:23–24` 仍为 `running_formal_arm/current_arm=gold`。本报告不判定 Gold、整个矩阵、正式新材料准入、probe 或训练资格完成，也不把“可加载资格”写成后续作业已实际消费资格。

## 接触上下文与边界

核查者是本包非作者 subagent，未参与材料编写、包装器修改、CPU 作业执行或回执取回。已接触题主提供的任务范围、固定版本、预期结果及此前审查上下文，因此本核查不是盲审。题主摘要只作为待核主张；本次结论由收到的原命令、产物、完整测试日志、账本和清理原件得出。

本轮仅做本机文件只读、SHA/字节重算、JSON/文本解析、逐来源/完整成员映射，以及依照冻结文本模板的内存摘要重算。没有 SSH、Docker、联网、安装、导入运行项目实现、启动评分或重跑测试；唯一写入为排他新建本报告。没有修改共享代码、作者材料、总账、历史输入或旧报告。

原静态材料审查 `non_author_material_review_20261003.md` 和此前 `non_author_cpu_evidence_review_20261003.md` 按已核版本限定复用，不重做全题静态审查或其它 CPU 审查。历史 48106 公开 actor 仅沿用其首版发布/runtime_cpu_v2、固定开发模型桩下的原公开环境与行为核查；它不是 R13 的新 actor、真实模型求解或本次正式评分证据。V1 Gold 的 `patch:`/真实 `kind=cc`、矩阵摘要 cleanup 字段错误及信号边界已另行核过，本轮不改写或重审。

## 原件与版本身份

- 原件根：`runs/category2_repair_20260929/pandas_cpu_20261003/formal_r13_48106_received_noop_v1/`。以下文件名均相对该根。
- 作业：`pandas48106-formal-r13-v1-c8c68284885c`，CPU 主机 `cpu-c`，输入为 `pandas48106-formal-r13-v1-387bf7b5d4`，解释器来自 `runtime_cpu_v2`。
- `receipt_manifest.json` SHA256：`b1659cd6e886556c720d55c2fd30c51bedb1aa94e08408578b69637ec5c379c3`。逐项独立重算全部 **42 件、2,425,875 字节**，无大小或 SHA 不匹配。该总字节数不含 receipt 自身。
- `inputs/input_manifest.json` SHA256：`74e0546a88ea7b1b7c3ef7e2f0b4a2bccb9f8b9aa0b43b67f33bcead6f1ad4e9`；其中 7 份输入字节全部匹配已核 V1 快照。
- 冻结 R13：`runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe27_pandas_moto_v1/`，manifest SHA256 独立读回为 `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641`。

`prepare.command.json:2–19` 指向上述冻结 CLI 与 repo，单题/source 精确，返回 0。`prepared/prepared_manifest.json` SHA `1ec93897ba4e95b3349772e400f8a7bfc9d500872b90e32bb347426482ec0b9b`；独立核其 prompt、rollout view 和 host grading 文件引用的 SHA/行数，均为实际收到的文件，一题一行。

对收到的 public/grading/environment 行与冻结 R13 producer 的原行作字节内容和规范 JSON 摘要核对，结果一致；公开 bundle 与原 batch02 public bundle 内容相同。原 16 F2P、1020 P2P 和原测试补丁保持，五组绑定与原 E19 登记一致。

| 身份 | 独立核对结果 |
| --- | --- |
| revision | `pandas48106-complete-bindings-e19-v1` |
| parent grading digest | `sha256:3c5e123be70f030ed8355e8b9aa8b51c32651c33d2c7a3da34724080f0f1127f` |
| public digest | `sha256:23ec7b2316ca1852adbf2b80c998895f02f73e49d7848d407a6777c5c6a067f7` |
| effective grading digest | `sha256:1b0dbf2b6ce752cedc45e359d8b50fbaeebada462aa192f5dca43c8db4ff1111` |
| environment package digest | `sha256:64fdb83d7c1e8c4ca2b8c5b2336c999cee5ef4b651ff215ff4e5eb90096f1cbb` |
| material identity | `sha256:15859c0693ca6330f58b274bd6ea24de9504daac1653a7cc6a7a3f8010c24315` |
| E19 grader image ID | `sha256:53b17fe21e906498091df64913c28682c23c6eaad8fbc7106fffa737d170860a` |
| base HEAD | `8b72297c8799725e98cb2c6aee664325b752194f` |

镜像身份有 `grader_image_inspect.json`、`input_identity.json` 与原 ledger 一致支持，正确记为固定 `local_build` ID，不冒称来源 RepoDigest。NoOp 的 `frozen_patch.json` 为 `entries=[]`、`excluded_pathset_changed=false`，projection 为空；`stage.json` 的 HEAD、`apply_method=noop`、git sanitize 验证和无 stage_error 一致。

## E19 实际安装与候选身份

原完整日志 `noop/eval_logs/evallog_replay-pandas48106-forma_3268a121.eval.log` 共 7060 行、631272 字节，SHA256 `e7ba38682d4a36affaf768bbea74dd37f6df6e31b2fc9e20e8c83d4884f31156`。测试段有真实 Start/End 标记（4951、7055 行），不是从包装器摘要推断执行。

- 3102、3107、3112、3117、3122、3127、3132、3137、3142、3147 行给出十份 wheel 的实际 `sha256sum` 结果，逐个与冻结 pins 相等；前后有普通文件/非符号链接检查。候选前置探测脚本摘要独立重算为 `sha256:aa081d905fdb4ca53cf2adf210a806f066037e964ba180855c0f24aa8816f749`，与 diagnostics 一致；该脚本实际以 user `54322` 返回 0，输出 `RH2_PANDAS_UID54322_WHEEL_BYTES_OK=1`。其模板强制 UID54322，并逐文件核大小、正规文件、非符号链接读取及 SHA。
- 3150 行执行登记的十包离线安装；3183 行实际安装成功。3184–3186 行执行原 `numpy<2` 和 `python -m pip install -ve . --no-build-isolation -Ceditable-verbose=true`；4931 行出现本源码的 editable 安装成功，4932 行执行原 pytest-qt 卸载。
- 4936–4937 行真实执行 `python -I -m pip check`，输出 `No broken requirements found.`；4942 行 `RH2_INSTALL_RC=0`。独立扫描未发现真实 `RH2_INSTALL_CMD_FAILED=<rc>` 输出行；trap 定义本身不算失败。安装段 marker 时间差为 612.216 秒。
- diagnostics 的候选前置身份与实际后观测同时支持 UID54322。`RH2_OBS_PANDAS_DETAIL` 记录 `python=/opt/miniconda3/envs/testbed/bin/python`、`pandas_file=/testbed/pandas/__init__.py`、`identity_ok=true`。实际 `pandas/core/dtypes/cast.py` SHA 为 `ae7fd950e2bbb75ba2d2d0879e2f9850cc04726aae123af42c3ed019b56eaf5f`，与收到的原源码及预期 NoOp 相同。

候选/评分 profile 的实际记录为 2 CPU、4 GiB、pids512、UID54322、网络 deny_all；正式测试文件恢复/补丁应用自证成功，保护记录 `RH2_PROTECT_OK=1`、缺失文件 0。这里的候选 apply 用户 `agent/54321` 与 grader install/test 用户 `54322` 是两个阶段，不应混称。

## 全来源与完整成员逐状态

独立解析真实 `pytest -rA` 汇总中的完整 nodeid，先取绑定中的精确完整成员；其余来源先取完整 nodeid，33 个原始空白截断来源另核同一旧 parser 键仅匹配一个完整物理节点。没有把多成员组的最后一个结果当整个组，也没有把未运行节点视为通过。

| 分区 | 来源参考数 | 对应唯一物理节点 | 独立原日志状态 | 缺席/重复 |
| --- | --- | --- | --- | --- |
| 原 F2P | 16 | 16 | 16 FAILED | 0 / 0 |
| 原 P2P | 1020 | 1028 | 1028 PASSED | 0 / 0 |

P2P 的构成为 982 个直接完整来源、33 个各唯一匹配的原截断来源，以及五组 13 个绑定成员。1020 是来源分母，1028 是物理节点分母，不能互换。原日志还包含一个不在来源参考内的 `TestLocBaseIndependent::test_loc_copy_vs_view` XFAIL（7032 行），未充作参考通过。日志实际 `collected 1045`（4959 行），汇总 `16 failed, 1028 passed, 1 xfailed`（7049 行），与独立解析一致。diagnostics 的 `num_parsed_tests=1040` 是既有 parser 键计数，不能当物理节点总数。

下表所有成员统一完整前缀为 `pandas/tests/indexing/test_loc.py::`；行号均指原 eval.log。组号依收到的 `grading.revision.bindings` 顺序，大小为 2、3、2、2、4。

| 组 | 完整成员（上述前缀之后） | 原状态 | 原日志行 |
| --- | --- | --- | --- |
| 1 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2017', 'A-DEC'\\), 'foo', Period\\('2015', 'A-DEC'\\)-key5]` | PASSED | 6039 |
| 1 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2017', 'A-DEC'\\), 'z1', 'bar'-key6]` | PASSED | 6040 |
| 2 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2019', 'A-DEC'\\), 'foo', 'bar'-key0]` | PASSED | 6034 |
| 2 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2019', 'A-DEC'\\), 'foo', 'z1'-key2]` | PASSED | 6036 |
| 2 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2019', 'A-DEC'\\), 'y1', 'bar'-key1]` | PASSED | 6035 |
| 3 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2018', 'A-DEC'\\), 'foo', 'y1'-key4]` | PASSED | 6038 |
| 3 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2018', 'A-DEC'\\), Period\\('2016', 'A-DEC'\\), 'bar'-key3]` | PASSED | 6037 |
| 4 | `TestLocBaseIndependent::test_loc_setitem_datetimeindex_tz[datetime.timezone(datetime.timedelta(days=-1, seconds=82800), 'foo')-idxer1]` | PASSED | 6178 |
| 4 | `TestLocBaseIndependent::test_loc_setitem_datetimeindex_tz[datetime.timezone(datetime.timedelta(days=-1, seconds=82800), 'foo')-var]` | PASSED | 6177 |
| 5 | `TestPartialStringSlicing::test_loc_getitem_partial_slice_non_monotonicity[datetime.timezone(datetime.timedelta(days=-1, seconds=82800), 'foo')-DataFrame-2020-01-02 23:59:59.999999999]` | PASSED | 6720 |
| 5 | `TestPartialStringSlicing::test_loc_getitem_partial_slice_non_monotonicity[datetime.timezone(datetime.timedelta(days=-1, seconds=82800), 'foo')-DataFrame-None]` | PASSED | 6719 |
| 5 | `TestPartialStringSlicing::test_loc_getitem_partial_slice_non_monotonicity[datetime.timezone(datetime.timedelta(days=-1, seconds=82800), 'foo')-Series-2020-01-02 23:59:59.999999999]` | PASSED | 6722 |
| 5 | `TestPartialStringSlicing::test_loc_getitem_partial_slice_non_monotonicity[datetime.timezone(datetime.timedelta(days=-1, seconds=82800), 'foo')-Series-None]` | PASSED | 6721 |

16 个来源 F2P 统一前缀为 `pandas/tests/indexing/test_loc.py::TestLocWithMultiIndex::`，逐节点如下。

| 来源节点（上述前缀之后） | 原状态 | 原日志行 |
| --- | --- | --- |
| `test_additional_element_to_categorical_series_loc` | FAILED | 7033 |
| `test_loc_set_nan_in_categorical_series[UInt8]` | FAILED | 7035 |
| `test_loc_set_nan_in_categorical_series[Int8]` | FAILED | 7039 |
| `test_loc_set_nan_in_categorical_series[UInt32]` | FAILED | 7037 |
| `test_loc_consistency_series_enlarge_set_into[None]` | FAILED | 7047 |
| `test_loc_set_nan_in_categorical_series[Float32]` | FAILED | 7043 |
| `test_loc_consistency_series_enlarge_set_into[nan]` | FAILED | 7045 |
| `test_loc_consistency_series_enlarge_set_into[na1]` | FAILED | 7046 |
| `test_loc_consistency_series_enlarge_set_into[na3]` | FAILED | 7048 |
| `test_loc_set_nan_in_categorical_series[Int32]` | FAILED | 7041 |
| `test_loc_set_nan_in_categorical_series[Int64]` | FAILED | 7042 |
| `test_additional_categorical_element_loc` | FAILED | 7034 |
| `test_loc_set_nan_in_categorical_series[Int16]` | FAILED | 7040 |
| `test_loc_set_nan_in_categorical_series[Float64]` | FAILED | 7044 |
| `test_loc_set_nan_in_categorical_series[UInt64]` | FAILED | 7038 |
| `test_loc_set_nan_in_categorical_series[UInt16]` | FAILED | 7036 |

原 ledger 与 diagnostics 的 `reference_missing=[]/reference_skipped=[]`、`reference_missing_count=0`、F2P 0/16、P2P 失败 0/1020 与上述逐节点核查一致。

## 正式评分、脚本摘要及资格条件

`noop.command.json:38` 为本臂 driver rc0；`noop.stdout.log:2` 与 `noop/ledger.jsonl:1` 对应正式 `report_id=rpt_grading_3268a121`。真实结果是 `reward=0.0/unresolved/tests_failed`，`infra_failure_detail=null`、`stage_error=null`、execution failure 字段为空；不是 infra 零分或私有校准。测试自身 rc1（7057 行），候选 shell 正常完成/exec rc0，不能把后二者写成测试通过。

依冻结 `grading_scripts_digest` 规则，使用收到的生产 trusted/candidate 脚本、冻结完整 eval 拼接模板和固定 candidate prerequisite，在内存重建摘要，独立得到：

`sha256:594109504074848b0988037581294fd922056fba076d8e8807e0dd6f9b4215b2`

它与 `input_identity.json`、`noop/audit/scope.json:4–5` 的 before/after、ledger、diagnostics 全部相等。scope 记录 setup 300→900 秒、测试仍为 1800 秒；追加的私有 post-observation 保留原生产观测前缀，只读回本候选导入及源码身份，未进入测试日志/评分 parser。runner 摘要前后相同，`runner_integrity_changed=false`。

按冻结 `rh2/src/repoharness2/adapters/slime/replay_grade.py:951–964` 的实际接受谓词，本行 `candidate.kind=noop`、`outcome=unresolved`、`failure_category=tests_failed`、缺席 0，且 image/scripts/material identity 齐全，**符合正式 NoOp 环境资格来源条件**。不需要 reward1 才能满足该定义。当前 NoOp 自身的 `env_qualification=absent`、CLI 初始 `qualifications=0/from=[]` 如实保留；那是本臂未传既有资格，不是否定它完成后可供加载。同题加载最多一项；下游仍须核实际加载、镜像/脚本/材料三身份一致，不能扩大到异版本或真实训练资格。

## 本臂清理与未完成项

- `noop/ledger.jsonl:1` 的真实 `cleanup={removed:true,steps:["rm:ok"],detail:""}`，证明本臂候选容器移除成功。
- `noop.stdout.log:3` 的原 CLI `manager_close` 为评分容器累计创建 1、累计移除 1，`containers_open=[]`、`supply_open=[]`、`cleanup_failures=[]`；`containers_removed=[]` 是 close 时追加清理列表为空，不能误读为累计未移除。`halted=null/aborted=null`，`final_status.exit_code=0/reason=ok`。
- V1 `matrix_state.json:19` 的 `cleanup=null` 是此前已知摘要取错字段，未用于本次清理判断。本报告只依据原 ledger 与 CLI close。

以上是已完成 NoOp 候选/评分 scope 的清理事实，不是整个远端作业或主机零残留结论。回执没有完整矩阵结束/自身 run 最终残留收口原件；Gold 仍在途。外部信号/强杀保证和后续实际资格消费不在此已验范围。剩余：Gold 原件、完整矩阵及作业最终清理回执到达后再按新增范围核验；不为重贴 Gold 标签重跑已有效的 NoOp。

## 最少原件指针

| 原件 | SHA256（raw bytes） |
| --- | --- |
| `noop/ledger.jsonl` | `e54caa26aab06df4d13161f74860a5d2121ab1f086ec9460e49e21599a4f9c89` |
| `noop/eval_logs/evallog_replay-pandas48106-forma_3268a121.eval.log` | `e7ba38682d4a36affaf768bbea74dd37f6df6e31b2fc9e20e8c83d4884f31156` |
| `noop/eval_logs/evallog_replay-pandas48106-forma_3268a121.diagnostics.json` | `de75fe0e3870c20a15690a89db8ccf136376eaced9c034e8309ccc6f06933801` |
| `noop.stdout.log` | `d375f1bcc7117acb8e82105e77cc09593b0c5d20018a0b10827e4395f4d284c5` |
| `private/host_grading_views.jsonl` | `2eba77c29807303c8d418bf47d119049d5221875c92a376a5c6c8ca939004ee3` |
| `input_identity.json` | `5e89d90da4e52a34833553960067602192f43d1f15253014a921a848926e58d0` |

建议与已证事实分开：本报告建议下游以此原 NoOp 账本作为符合条件的资格候选，并核实际加载；已证事实为上述本臂正式执行/判分/清理，未完成项为 Gold、矩阵结束及最终作业残留收口。
