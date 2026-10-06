# Pandas 48106 R13 正式 Gold 与矩阵收尾原件独立窄核（2026-10-03）

结论：**本次 48106 首轮 NoOp/Gold 两臂正式 CPU 矩阵在所核范围内通过，未发现阻断。** NoOp 为正式 `reward=0/tests_failed`；原 validation Gold 字节作为普通 patch 候选取得正式 `reward=1/resolved`，16 个来源 F2P 全翻转，1020 个来源 P2P 与五组 13 个完整成员无回退，缺席为 0。原 CLI、矩阵与外层作业均正常结束；在作业结束后的 2026-10-03 01:33:47 UTC，六条精确查询证明本次两个 run 标签的容器/网络及两个确切 grader 名字均无残留。

该结论只覆盖本题、本次冻结 R13、E19 镜像、候选字节和实际预算。**Gold driver 的真实 `candidate.kind=cc` 保留，不作为 P-A Gold 环境资格**；先前已核的 NoOp 行仍是符合条件的资格来源。通过本矩阵不等于真实模型求解、probe 或训练资格已完成，也不对全主机或 50319 作结论。

## 核查角色、上下文与复用范围

核查者为本包非作者 subagent，未参与材料编写、包装器修改、作业执行或取回。已接触题主提供的入口、固定版本、结果主张及前序审查上下文，因此不属于盲审。作者摘要作为待核主张；本轮根据完整原命令、冻结候选、日志、账本、作业状态和逐查询原输出独立判定。

复用 `non_author_48106_formal_noop_review_20261003.md`（SHA256 `21175165ef3690b64195c3f0ac4ba9b338e624e8459cb9bc04375fdedd6d92c6`）已核 NoOp 与身份/摘要构造范围。原静态材料审查与 `non_author_cpu_evidence_review_20261003.md` 按已核版本限定复用，不重做旧范围。历史 48106 原公开 actor 仍只支持其首版发布/runtime_cpu_v2 下的开发模型桩与原公开行为，不改写为 R13 actor，不作为本次正式 reward 或真实模型求解证据。

本轮只做本机文件只读、SHA/字节重算、JSON/文本解析、内存补丁应用与冻结 payload 解码、逐来源/成员对照。没有 SSH、Docker、联网、安装、项目代码导入执行或新实验；下文 Docker/SSH 的 rc 均为题主取回的原记录。唯一写入是排他新建本报告；旧报告、输入、作者材料、共享代码和总账均未修改。未审 50319 在途结果，未向其它线程广播。

## 完整回执与新增原件

主原件根：`runs/category2_repair_20260929/pandas_cpu_20261003/formal_r13_48106_received_whole_v1/`，下文主原件名相对该根。

- 作业 `pandas48106-formal-r13-v1-c8c68284885c`，CPU 主机 `cpu-c`，V1 输入 `pandas48106-formal-r13-v1-387bf7b5d4`。
- `receipt_manifest.json` SHA256 `65b466412dbc31dc3d9c3391fa86f4fd58b4749d0ca0c1fd9463aca62744c77f`。独立重算 **60 件、4,255,048 字节**，全部大小/SHA 匹配，总字节不含 receipt 自身。
- 与旧 NoOp 回执重叠 42 件，其中 40 件字节相同；只 `gold.stdout.log` 与 `matrix_state.json` 从在途快照增长为完成结果。所有 NoOp 臂原文件、共同输入、prepared/private 材料与生产脚本保持原字节，旧 receipt 未改写。
- 最终残留 V2 的 response、transport、原查询脚本是另存的三个原件，不混入上述 60 件的计数；摘要与查询细节见收尾部分。

固定 source 为 `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe27_pandas_moto_v1/`，R13 manifest SHA `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641`，runtime_cpu_v2。共同 `private/host_grading_views.jsonl`、`input_identity.json` 和 prepared 原件与已核 NoOp 回执相同；Gold ledger/diagnostics 的身份逐字段一致：

| 身份 | 实际值 |
| --- | --- |
| revision | `pandas48106-complete-bindings-e19-v1` |
| parent grading digest | `sha256:3c5e123be70f030ed8355e8b9aa8b51c32651c33d2c7a3da34724080f0f1127f` |
| public digest | `sha256:23ec7b2316ca1852adbf2b80c998895f02f73e49d7848d407a6777c5c6a067f7` |
| effective grading digest | `sha256:1b0dbf2b6ce752cedc45e359d8b50fbaeebada462aa192f5dca43c8db4ff1111` |
| environment package digest | `sha256:64fdb83d7c1e8c4ca2b8c5b2336c999cee5ef4b651ff215ff4e5eb90096f1cbb` |
| material identity | `sha256:15859c0693ca6330f58b274bd6ea24de9504daac1653a7cc6a7a3f8010c24315` |
| binding registry/bindings SHA | `sha256:d0ddf68c4f77729d854fbe1bb382b7cb326f46e597eeefdf3b986c4a821ba16f` / `sha256:4c628adf0150848e756bae3afb917af9d248b2c983c30612a9e6925a266f3b08` |
| E19 grader image identity | `local_build:sha256:53b17fe21e906498091df64913c28682c23c6eaad8fbc7106fffa737d170860a` |
| base HEAD | `8b72297c8799725e98cb2c6aee664325b752194f` |

公开材料、原 16 F2P/1020 P2P 和原测试补丁保持已核版本，未向 solver 交付本次私有材料。E19 ID 不冒称原 actor/source RepoDigest。

## Gold 字节与真实 driver 角色

`gold.command.json:19–20` 实际候选是 `patch:…/gold.patch`，不是 `gold-dir`。`gold/ledger.jsonl:1` 保留 `kind=cc`、`apply_method=git_apply`、apply 用户 `agent/54321`，没有重贴标签或伪改历史行。`gold.stdout.log:1` 为 `qualifications=0/from=[]`，Gold 本臂 `env_qualification=absent` 如实保留。

独立核收到的 `inputs/gold.patch`、Gold artifact 的 `candidate.patch` 与冻结 producer 的 `validation_bundles_v0.jsonl` 中该题原 `golden_patch` 字节完全相同，630 字节，SHA：

`cf099ba87549e41673503275a6e66263685a795770c42c373d1fd41554fed23d`

从原源码在内存应用该 unified diff，再解码 `gold/artifacts/swe_gym_lite--pandas-dev__pandas-48106/a1-34add2c1/frozen_patch.json` 的 `content_b64` 对照，两份源码字节相同：69431 字节、SHA `e671c46d20c4f82abd9e4a7847722df04bb70524bb355e801f7c7b0e5c2d9a5a`。冻结候选只有一个 `modify/regular/100644` 条目 `pandas/core/dtypes/cast.py`，projection 只包含该路径，忽略/不支持条目为空，`excluded_pathset_changed=false`。源码 SHA 同时匹配输入预期、frozen content_digest 和实际后观测；不是仅比候选补丁文件名。

Gold 正式评分成功可以用于本次原 Gold 字节的判别矩阵验收，但冻结 `load_env_qualifications` 只接受 `gold/noop` kind，本 `cc` 行不满足。已核 NoOp 的真实 `kind=noop` 和完整参考结果满足资格来源条件；本矩阵没有实际传入该资格账本，不能写成已消费 NoOp 资格。

## 实际安装、身份与评分控制面

新增完整 Gold 日志 `gold/eval_logs/evallog_replay-pandas48106-forma_66524509.eval.log` 为 6081 行、592288 字节，SHA `0bc319f9afe6039b636434dd912a03598b17c291de5ab37debee1976b9344de7`。

- 十份 wheel 的实际 SHA 行为 3124、3129、3134、3139、3144、3149、3154、3159、3164、3169，逐份与冻结 pins 匹配；此前候选 UID54322 固定字节前置探测返回 0/verified，输出 `RH2_PANDAS_UID54322_WHEEL_BYTES_OK=1`，其脚本 SHA `aa081d905fdb4ca53cf2adf210a806f066037e964ba180855c0f24aa8816f749` 与已独立重算的原模板一致。
- 3172 行真实执行登记的十包离线固定安装；3206/3208 行执行原 `numpy<2` 与 editable 安装；4953 行实际安装本 pandas 源码成功，4954 行执行原 pytest-qt 卸载。4958–4959 行 `python -I -m pip check` 输出 `No broken requirements found.`；4964 行 `RH2_INSTALL_RC=0`。独立扫描未发现真实失败命令 marker，安装耗时 638.555 秒。
- 实际 post-observation 为 `uid=54322`、`python=/opt/miniconda3/envs/testbed/bin/python`、`pandas_file=/testbed/pandas/__init__.py`、`identity_ok=true`，实际 cast.py SHA 是上述 Gold SHA。不是用 apply 用户 54321 代替 grader 安装/测试用户 54322。
- 1594 行恢复原 `test_loc.py`；1599 行原基线 SHA `eea3ba3024413981e10f4cde31cd867f0411e2471d6d274d2cbbf483f079f7d3` 匹配；1610–1612 行原官方测试补丁 cleanly 应用，1633–1645 行自证 apply_rc0/restored1/setup_ok1。diagnostics 控制面保护 `RH2_PROTECT_OK=1`、预期/保护测试文件 1、缺失 0、异常文件为空。runner digest 前后均为 `1cfac6828a8ce1101528108a0a3379da1fe8e2b0ba4a9021ea32c5ffc26e13a4`，`runner_integrity_changed=false`。

评分脚本 digest 为 `sha256:594109504074848b0988037581294fd922056fba076d8e8807e0dd6f9b4215b2`：共同生产脚本与旧回执字节相同，复用 NoOp 报告的独立内存重算；Gold scope 的 before/after、ledger、diagnostics 逐项相等。Gold 私有观测与 NoOp 私有观测只改预期 source SHA，不改正式测试/安装/parser/参考。setup 300→900 秒、测试预算仍 1800 秒，candidate stage1800、grading deadline3600、cleanup120；两臂实际 profile 同为 2 CPU/4 GiB/pids512、UID54322、网络 deny_all。

## 全来源翻转与完整成员

对新增 Gold 原日志的完整 `pytest -rA` nodeid 独立解析，按固定五组绑定精确取完整成员；其余来源取完整 ID，33 个旧空白截断来源各核唯一匹配，没有用最后一值代替整个绑定组。1020 个来源 P2P 实际对应 1028 个唯一物理节点；来源分母与物理分母分开。

| 分区 | 来源数 / 唯一物理节点 | NoOp | Gold | 缺席/重复 |
| --- | --- | --- | --- | --- |
| 原 F2P | 16 / 16 | 16 FAILED | 16 PASSED | 0 / 0 |
| 原 P2P | 1020 / 1028 | 1028 PASSED | 1028 PASSED | 0 / 0 |
| 五组完整绑定（含于 P2P） | 5 / 13 | 13 PASSED | 13 PASSED | 0 / 0 |

Gold 4981 行实际 collected1045，6070 行汇总 `1044 passed, 1 xfailed`；唯一非参考节点为 `TestLocBaseIndependent::test_loc_copy_vs_view` 的 XFAIL（6069 行），未充作参考通过。官方 diagnostics 的 `num_parsed_tests=1040` 是既有 parser 键计数，不当物理节点计数。

下表来源 F2P 统一完整前缀为 `pandas/tests/indexing/test_loc.py::TestLocWithMultiIndex::`；数字是相应臂原 eval.log 行号。NoOp 原日志与旧审查字节相同，逐状态对照证明真实翻转。

| 来源节点（上述前缀之后） | NoOp 状态 / 行 | Gold 状态 / 行 |
| --- | --- | --- |
| `test_additional_element_to_categorical_series_loc` | FAILED / 7033 | PASSED / 5606 |
| `test_loc_set_nan_in_categorical_series[UInt8]` | FAILED / 7035 | PASSED / 5608 |
| `test_loc_set_nan_in_categorical_series[Int8]` | FAILED / 7039 | PASSED / 5612 |
| `test_loc_set_nan_in_categorical_series[UInt32]` | FAILED / 7037 | PASSED / 5610 |
| `test_loc_consistency_series_enlarge_set_into[None]` | FAILED / 7047 | PASSED / 5620 |
| `test_loc_set_nan_in_categorical_series[Float32]` | FAILED / 7043 | PASSED / 5616 |
| `test_loc_consistency_series_enlarge_set_into[nan]` | FAILED / 7045 | PASSED / 5618 |
| `test_loc_consistency_series_enlarge_set_into[na1]` | FAILED / 7046 | PASSED / 5619 |
| `test_loc_consistency_series_enlarge_set_into[na3]` | FAILED / 7048 | PASSED / 5621 |
| `test_loc_set_nan_in_categorical_series[Int32]` | FAILED / 7041 | PASSED / 5614 |
| `test_loc_set_nan_in_categorical_series[Int64]` | FAILED / 7042 | PASSED / 5615 |
| `test_additional_categorical_element_loc` | FAILED / 7034 | PASSED / 5607 |
| `test_loc_set_nan_in_categorical_series[Int16]` | FAILED / 7040 | PASSED / 5613 |
| `test_loc_set_nan_in_categorical_series[Float64]` | FAILED / 7044 | PASSED / 5617 |
| `test_loc_set_nan_in_categorical_series[UInt64]` | FAILED / 7038 | PASSED / 5611 |
| `test_loc_set_nan_in_categorical_series[UInt16]` | FAILED / 7036 | PASSED / 5609 |

以下 13 个成员统一完整前缀为 `pandas/tests/indexing/test_loc.py::`，组号按收到的 revision.bindings 顺序，组大小 2、3、2、2、4。

| 组 | 完整成员（上述前缀之后） | NoOp 状态 / 行 | Gold 状态 / 行 |
| --- | --- | --- | --- |
| 1 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2017', 'A-DEC'\\), 'foo', Period\\('2015', 'A-DEC'\\)-key5]` | PASSED / 6039 | PASSED / 5060 |
| 1 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2017', 'A-DEC'\\), 'z1', 'bar'-key6]` | PASSED / 6040 | PASSED / 5061 |
| 2 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2019', 'A-DEC'\\), 'foo', 'bar'-key0]` | PASSED / 6034 | PASSED / 5055 |
| 2 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2019', 'A-DEC'\\), 'foo', 'z1'-key2]` | PASSED / 6036 | PASSED / 5057 |
| 2 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2019', 'A-DEC'\\), 'y1', 'bar'-key1]` | PASSED / 6035 | PASSED / 5056 |
| 3 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2018', 'A-DEC'\\), 'foo', 'y1'-key4]` | PASSED / 6038 | PASSED / 5059 |
| 3 | `TestLocBaseIndependent::test_contains_raise_error_if_period_index_is_in_multi_index[Period\\('2018', 'A-DEC'\\), Period\\('2016', 'A-DEC'\\), 'bar'-key3]` | PASSED / 6037 | PASSED / 5058 |
| 4 | `TestLocBaseIndependent::test_loc_setitem_datetimeindex_tz[datetime.timezone(datetime.timedelta(days=-1, seconds=82800), 'foo')-idxer1]` | PASSED / 6178 | PASSED / 5199 |
| 4 | `TestLocBaseIndependent::test_loc_setitem_datetimeindex_tz[datetime.timezone(datetime.timedelta(days=-1, seconds=82800), 'foo')-var]` | PASSED / 6177 | PASSED / 5198 |
| 5 | `TestPartialStringSlicing::test_loc_getitem_partial_slice_non_monotonicity[datetime.timezone(datetime.timedelta(days=-1, seconds=82800), 'foo')-DataFrame-2020-01-02 23:59:59.999999999]` | PASSED / 6720 | PASSED / 5757 |
| 5 | `TestPartialStringSlicing::test_loc_getitem_partial_slice_non_monotonicity[datetime.timezone(datetime.timedelta(days=-1, seconds=82800), 'foo')-DataFrame-None]` | PASSED / 6719 | PASSED / 5756 |
| 5 | `TestPartialStringSlicing::test_loc_getitem_partial_slice_non_monotonicity[datetime.timezone(datetime.timedelta(days=-1, seconds=82800), 'foo')-Series-2020-01-02 23:59:59.999999999]` | PASSED / 6722 | PASSED / 5759 |
| 5 | `TestPartialStringSlicing::test_loc_getitem_partial_slice_non_monotonicity[datetime.timezone(datetime.timedelta(days=-1, seconds=82800), 'foo')-Series-None]` | PASSED / 6721 | PASSED / 5758 |

Gold 原正式 `report_id=rpt_grading_66524509` 为 `reward=1.0/outcome=resolved/failure_category=null`、F2P16/16、P2P失败0/1020，缺席/skip为空、`reference_missing_count=0`，无 infra detail、stage_error 或 execution failure。4973/6076 行 Start/End 标记包围真实测试，6078 行测试 rc0；candidate exec0、segment_completed=true、log_partial=false 与之相符。NoOp 原报告仍是已核的 0/tests_failed，未因新增完成状态改写。

## 正常矩阵结束与本次精确残留收口

`gold.command.json:38` rc0。`noop.stdout.log:3` 与 `gold.stdout.log:3` 各自 manager close 的累计 grader 创建1/移除1，containers_open/supply_open/cleanup_failures 全空，halted/aborted均null，final_status `exit_code=0/reason=ok`。两个原 ledger 的 candidate `cleanup.removed=true/steps=[rm:ok]`。matrix_state 的两个 `cleanup=null` 是已知摘要字段错误，不用于清理判定，也不回写为成功。

NoOp finished 时间 1790982433.3154504，Gold started 时间 1790982433.3236024，顺序成立，每臂 repeat1；`inputs/attempts.jsonl` 只有本次作业的一行 rc0。`matrix_state.json:36–38` 已结束，`job/status.json:18–21` 为 finished/returncode0（2026-10-02 23:29:26 UTC），`inputs/launcher.exit=0` 与 launcher_result一致。此处验证正常完成路径，不声称 V1 外部 SIGTERM/强杀的普遍保证。

完整 60 件回执本身只含臂/CLI/作业清理，起初缺少现场查询事实。旧归一化 V1 读回只有空数组，未单凭 `own_scope_zero_residue=true` 作独立清理结论。随后收到 V2 原查询证据，全部独立重算且引用链匹配：

| 另存原件（相对 `runs/category2_repair_20260929/pandas_cpu_20261003/`） | 字节 | SHA256 |
| --- | --- | --- |
| `formal_48106_final_residue_readback_20261003_v2.json` | 2046 | `89e5cc0889414dfbf3351145b58a5d4495b8af968e2f473846899a8fec57d175` |
| `formal_48106_final_residue_transport_20261003_v2.json` | 458 | `e99cebc33f9c8bef4dd2a0bf05e1b1ed528b7824c0d62e98e7c037dccafb6f8b` |
| `residue_formal_48106_r13_cpu_c_v2.sh` | 1670 | `a375c0b4708f2775f51eb6c13304dcdf7c492426236cd4307045cb2ae1ded4bd` |

原脚本 8 行先断言本作业已结束/exit0，12–14 行只构造下列精确只读查询，18–19 行保留各查询原 argv/rc/stdout/stderr。按原 ledger 的 run_id 重建的六条 argv 与 response 完全一致，独立规范 JSON 重算 `query_spec_sha256=8804132f6d23ae81246929313d7b5eeb7171d96a2423ab007038b8ec47f650e1` 匹配；response 中 matrix_launcher_result 与完整回执的原件一致。

| 过滤范围 | 查询 | rc | stdout / stderr |
| --- | --- | --- | --- |
| `rh2.run_id=pandas48106-formal-r13-v1-c8c68284885c-noop` | `docker ps -a` | 0 | 空 / 空 |
| 同一 NoOp 标签 | `docker network ls` | 0 | 空 / 空 |
| `rh2.run_id=pandas48106-formal-r13-v1-c8c68284885c-gold` | `docker ps -a` | 0 | 空 / 空 |
| 同一 Gold 标签 | `docker network ls` | 0 | 空 / 空 |
| `name=^/rh2-grading-replay-pandas48106-forma-3268a121$` | `docker ps -a` | 0 | 空 / 空 |
| `name=^/rh2-grading-replay-pandas48106-forma-66524509$` | `docker ps -a` | 0 | 空 / 空 |

实际观测为 2026-10-03 01:33:47.627516 至 01:33:47.915757 UTC，晚于作业结束。transport 原脚本/response 引用与 SHA 相等，外层 `ssh_wrapper_rc=0/stderr=""`。因此可独立证明上述本次已完成 scope 在观测时的容器和网络零残留，既不是查询失败归一化为空，也不是只信 manager 摘要。没有清理其它任务，没有证明全机、50319、所有进程/文件/镜像或以后任何时刻零残留。

## 关键原件指针与结论用途

| 主原件 | SHA256 |
| --- | --- |
| `gold/ledger.jsonl` | `7488f6f5996a5fe7247a483e8906e96f0d6caf82b5f928cbf00129f8d0253223` |
| `gold/eval_logs/evallog_replay-pandas48106-forma_66524509.eval.log` | `0bc319f9afe6039b636434dd912a03598b17c291de5ab37debee1976b9344de7` |
| `gold/eval_logs/evallog_replay-pandas48106-forma_66524509.diagnostics.json` | `9743c00063252188747fdb59574be49735f9fd2689526ae0a794d5dd0f2adb5c` |
| `gold/artifacts/swe_gym_lite--pandas-dev__pandas-48106/a1-34add2c1/frozen_patch.json` | `9e9517fe7097b1070729c6ae11254808fda770d3510e5ef78380e1a53acf89c0` |
| `gold.stdout.log` | `f92d656e12dfce47e21b058523618cd173b80f1adf1fee99faf84e5ece11f691` |
| `job/status.json` | `ce8d338154bbe5fbc17c442c3080ab5b4373c7d5e0ad68cabfc62c620672d27b` |

已证事实是这次固定两臂矩阵的正式判分、完整来源/成员、控制面及本次正常收尾。建议将其用于 48106 本轮 CPU 验收，并以真实 NoOp 行作为后续符合身份条件的环境资格来源；不要把 kind=cc 的 Gold 行改作 P-A Gold 资格。不把本报告推广为 probe/训练已准入，后续关键决策及正式准入按当前流程办理。本次任务范围内没有待补原件或执行阻断；其它任务和后续用途不在本轮核查范围。
