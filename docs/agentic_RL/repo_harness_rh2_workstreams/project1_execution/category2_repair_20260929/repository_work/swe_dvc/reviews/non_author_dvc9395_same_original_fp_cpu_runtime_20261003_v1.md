# DVC9395 原 Coder FP CPU 补评分：非作者实际运行窄核

日期：2026-10-03。结论：本次单个原 FP 补评分运行已完成，可以核收有效正式 raw reward=0；不是基础设施失败。官方 report 为 unresolved / tests_failed，3个F参考全失败、37个P参考全通过。pytest真实执行41节点：37 passed、4 failed，第四个失败是未计分的原import节点。安装退出0、pytest退出1，manager及slot完成后清理均通过。没有新增执行阻断，也没有据此授予训练、稳定性或双模型ACK。

审查者已见私有材料、R20校准及原Coder语义审查，属于授权的非作者读回，不是fresh公开读者。本次仅本机标准库读取、SHA/tar/JSON与原件重建；未运行SSH、Docker、候选、测试、评分或模型。未改旧报告、输入、评分或总账。新评分关联旧 `gpu1003-dvc9395-coder-a1`；保留旧 GPU entry RC1、cleanup=false、reward=null及 solve 215.507秒，不能把新CPU raw0回填成旧运行0，也不是增加一个模型样本。

## 来源、投影与执行身份

下文 `P` 为本包，`R` 为 `runs/category2_repair_20260929/repository_work/swe_dvc/dvc9395_same_original_fp_cpu_recovery_20261003_v1`，`A=R/actual_readback_v1`，`G=A/grade_v1`。执行前审查 `P/reviews/non_author_dvc9395_same_original_fp_cpu_preflight_20261003_v1.md` SHA `b52e6f7a7630ae7f818b23f6cfef5682793385393905c5dd7e89135013d37602` 原样保留，复用其快照1092/code8 1045成员身份及静态边界，不重复材料审批。

实际 q01 slot admission记录 running/child1103386/supervisor1103385，与最终slot相同。真实命令使用固定快照 `snapshot_7c8c9bccd699a74f`、worker SHA `46b35703dda5a24441d9548a54e0705287700b4aab6f4cdb019c5a602e2aa664`，在原 code8 runtime 中新输出 grade_v1；仅传 --execute，未求解或调用模型。slot于12:58:09Z开始、13:02:20Z结束，finished/returncode0，外层completion0、stderr空。这个0表示补评分worker正常完成，候选评分仍是0。

`G/binding.json`、complete_scripts、projection、summary与pure_v2对应字节相同。旧input_check与实际input_check的task/source/solver/budget/public_delivery/assignment/baseline_policy、prepared/host artifact SHA、材料/revision、精确policy与grading budgets、entry runner/spec overrides逐字段一致。tasks回退 prepared_summary/public_notes 后完全等于旧配置；summary只重定位prepared_dir/private_dir。整份input_check/tasks JSON文件不相同，不误说仅路径变动后仍整文件同SHA。71个实际加载模块逐个与快照frozen code8 SHA一致；entry SHA为 `bdf806bf8da1d5ebb4970887bfc3c7738eb3e57a75e1d07215d6d68b17e574c4`。

已回收预审缺的pure_v2 projection/tasks/summary三项，回执SHA `28d9b85a55e69c550a948aecc67a7d222c507e564a9ced7964d3a92c4a060fc9`，逐项SHA/size匹配。实际projection包含完整原FP三项：`dvc/stage/__init__.py`、`test_comprehensive.py`、`test_pull_fix.py`，原rollout/physical ID仍为旧job和 `#p1`。独立重算原FP canonical `sha256:1cad35171d386f0d905859d0232d29d7df9a398872d62e6e71e98ffc8d0cd456`、baseline canonical `sha256:0c75caa0ac9790c739e0250f37125f342241d19d57bb430e6a6c7fa009acf0ec`。按官方manager的operation/type/mode/content_digest/path换行规则重算三项 applied_entry_set 为 `sha256:d42cae3df94118fb656c8962226021527d9343edbc8d9e6eba74a493e30f5762`，等于report hygiene digest；不是原FP artifact digest。三个delta_write阶段均真实退出0，候选三项保留；hygiene clean不等于临时脚本不存在。

baseline_rebuild真实exec003的615个census项，独立按类型/mode/内容SHA与原baseline_manifest615项比对：无多、缺、值差异，缓存省略0。base/materialized HEAD均 `c75a5583b3840ba90a8e800a0f42c1cb120916db`；baseline环境digest仍None，未重绑成新材料digest。实际restore官方两测试base SHA分别 `ca738a7a94b991881a48abdb02aa1d27565f087e5742511d1fbbd752afde99e1`、`0d9bfa7a96c4e29e178c89b96357ec1adae59bfa27027173f07b234b08504960`，trusted setup/apply、attest、protect依次退出0，RESTORED=2、TEST_FILES=2、无缺项/不规则文件，PROTECTED_FILES=2/DIRS=6、PROTECT_OK=1。

材料仍 `sha256:9d456666b845fd90146499033601805ce2ecdc3d88e26202f8b9855cf287f68a`，revision dvc9395-behavior-v2-draft，grading bundle b939c2ea…，预算 whole/setup/apply/test=3600/900/120/1800秒，原精确任务/revision/testpatch/image/requestinput policy不变。脚本实际single-shell digest为 `sha256:ec5f61cf288b78aaafd469b40013bcd571e93e1ab5db7c32c8852b6a83f035f3`，supply=None；完整五脚本与pure_v2相同，不把two-stage构造digest当实际模式。官方trusted_setup聚合156.179秒低于旧300，不能说本次必须靠900才恢复或已经消除历史争用。

## 完整节点与失败原因

从完整eval.log及exec016实际stdout逐行重建pytest状态，节点只认所选两文件的pytest状态行；不采用作者summary或官方诊断总数作分母。footer（eval.log第5791行）为 `4 failed, 37 passed in 21.87s`；collect41 items，无skip、missing、收集错误或节点重复。

|计分分区|参考数|通过|失败|缺席/skip|
|---|---:|---:|---:|---:|
|bound_source_f2p|2|0|2|0|
|added_f2p|1|0|1|0|
|bound_source_p2p|27|27|0|0|
|added_p2p|10|10|0|0|
|正式参考合计|40|37|3|0|
|额外原import（未计分）|1|0|1|0|
|实际pytest合计|41|37|4|0|

所有40参考按输入精确ID与完整状态逐项映射，分区结果与official diagnostics/full_reference_readback逐项一致。完整41节点及日志行号列于本报告同名JSON，不截断param ID。三个F及额外失败如下：

- `tests/func/test_repro_multistage.py::test_repro_pulls_mising_data_source`：stage.run第585行先调用_check_missing_outputs，第618行进入check_missing_outputs，stage/utils.py第143行抛MissingDataSource(foo)，包装成foo.dvc的ReproductionError。关键堆栈eval.log第773—925行，最终FAILED第5787行。
- `tests/func/test_repro_multistage.py::test_pull_recovers_frozen_stage_for_downstream`：同一路径MissingDataSource(raw)，包装download的ReproductionError；关键第1503—1659行，FAILED第5789行。
- `tests/func/test_run_cache.py::test_restore_pull`：stage.run第598行save→save_outs，第518行out.save，OutputDoesNotExistError(bar)，包装copy-foo-bar的ReproductionError；关键第1869—2025行，FAILED第5790行。
- `tests/func/test_repro_multistage.py::test_repro_pulls_mising_import`：未计分，但实际同第585行早抛MissingDataSource(foo)，包装foo.dvc的ReproductionError；关键第1126—1279行，FAILED第5788行。不是Python模块导入错误。

这些是测试调用真实业务时未能恢复数据/输出，不能冒充import/collect infra。与已封存候选语义意见一致：原FP把_pull_missing_outputs放在_check_missing_outputs后，源缺失时先抛异常，后续新helper不可达；helper也只checkout本地数据，没有远端cloud.pull，不能恢复被移除的cache。静态wrong与本次三F实失败一致，本报告不因评分0再修改题义或断言。

官方diagnostics原件仍 `num_parsed_tests=42`、num_parsed_outside_segment=0、RESOLVED_NO，正式reference missing/skipped空。第42个伪计数来自eval.log第2218行 `ERROR    dvc.commands.freeze:freeze.py:19 failed to freeze ':copy-file1-file3'`，属于PASSED test_non_existing_stage_name的captured logging；不是pytest ERROR节点。真实分母41、参考40与官方便捷parsed总数42必须区别。本报告不改parser、日志或reward；正式40参考不受该非参考伪条目改变。

## 安装、UID、资源与清理

16个真实exec log逐个读取，全部外层退出0；各阶段依次为env_reset、git_sanitize、baseline_rebuild、cache_normalization、3次delta_write、eval_write、trusted_setup、attest、protect、eval_write、candidate_prerequisite、eval_write、candidate_log_dir、test。root trusted setup UID0离线轮子预检标记存在；候选prerequisite明确user54322/HOME rh2grader、exit0、UID54322_WHEEL_BYTES_OK=1。actual_candidate_uid另有id -u stdout54322/exit0。exec016 test用户参数54322，安装在testbed前缀中进行，实际pygit2 1.14.1、dvc 2.56.1.dev27+gc75a5583.d20261003。

安装完整执行、非skip、无failed commands，RH2_INSTALL_RC=0（eval第658行）；pytest实际RH2_TEST_RC=1（第5795行）。single-shell最后echo返回0，所以candidate_exec_exit_code=0不表示测试通过。candidate_segment_completed=true、log_partial=false，report execution_failure_stage/infra detail均null，runner integrity digest前后一致。未把外层rc0误报成pytest rc0。

实际image inspect选定的Id/Architecture/Os/RootFS/Config逐字段等于预审固定输入；c093本地构建manifestNone保留。容器start归档实际HostConfig为NanoCpus=2e9、Memory=4294967296、MemorySwap=4294967296（无额外swap）、PID512、NetworkMode=none、非Privileged、no-new-privileges、cap_dropALL、受信init限定caps、tmpfs1GiB/shm64MiB。Config.User空是默认root，与candidate54322区别。新容器ID为7958fbc4b0799e173efa510c5736b949c77cd290bd850343d72352b7c407e8c2，host PID1103471；owner与本job trajectory labels明确。

资源原件有51条own-cgroup采样，含fresh_before_baseline、during、before_cleanup，约245.159秒；同实际PID派生的cgroup读cpu.max=200000/100000、pids.max512，无读错误。memory.peak最高1033506816B（985.629MiB），采样memory.current最高1026838528B，pids.peak最高11。所有样本memory.events low/high/max/oom/oom_kill/oom_group_kill为0，pids.events max0；关闭前OOMKilled=false。内核累计peak/events补足5秒采样间隔，但不据此给全host/其它job或所有瞬时进程归因；只覆盖该容器cgroup。官方diag.resource_facts仍null，这里资源结论来自独立实际文件，不伪填官方字段。

manager_close：created=removed=1，containers_open/supply_open/cleanup_failures空，regrade0；runner owned_containers_remaining空，cleanuptrue、received_signals空；status末检fixed_sources_unchanged_after_run=true。这个末检是实际worker执行固定SHA guard的结果，本机再次核快照列明成员SHA一致；没有另归档远端逐项after-SHA清单，不将bool扩成新的逐文件遥测。

第二层：slot最终finished/returncode0；关闭采集在finished后以精确trajectory label查询owned容器，query rc0/stdout空，闭合manifest保存该事实。deny_all/no_supply没有新actor relay/network需要清理。本次正常结束，没有验证信号/异常清理分支。

## 封存与限制

闭合包独立逐项核38原件（35grade+3slot），大小合计856053B，SHA/size和精确集合无差异；tar39普通成员恰为38原件加closed_manifest，内容逐字相同。tar SHA `badd8d663e571bf7ac4b54c079b509c17e80f914f3b290ee2a6d7acb0a1802ef`；closed_manifest SHA `5d106389938f110050a7a16c5205c1cb723f27851d6ba193ea8fbcd727b46fa1`，collect receipt SHA `9e4691f178bcb5b4d1aa745bbc5b4d3b3105a87c2df6fcd63aad46483e8f209f`。本报告JSON保存全部38实际原件及辅助原件完整SHA指针。

第一次只读归档collector发生SyntaxError，collect_closed.stderr保留SHA `6f15b2ac74775eafe2b7807d000338ac072a9c6d83695f56b45f3c1c6d720f60`。生成的远端程序因嵌套字符串换行未闭合，在解释阶段失败，无归档创建或评分重跑。v2仅移除该manifest换行字符串、改独立stdout/stderr保存名，差异不涉及候选或grade；v2 SHA `d1f7d080c4731309855610eb082fa2bc6fa3b94e34a4c3fab016a36de8384ff3`。旧权限pure_v1失败及原GPUcleanup失败同样保留。

关键实际SHA：report `643e47665e0510dfba0da453f7b2ba2f4aa6962e40816b8dd296fbbcc2815d4c`；完整eval.log `0225b10025cfd8b19c036ce8a578c28d14cc13d5e4a0fc19e1b36cb6e04cbe31`；diagnostics `83a0f2abba55d9165fa0f9ce0ddbd30139c82f57e069681a8458b115c741ca89`；status `b92bb40bfd0808e88512f08fdedbaf31b8dda53fe69c64fbed9eaa6e6a04fb70`；slot status `2b4da5a78a4410cf0fa7444d5c80e78698078c5fcba39d85edd85abf08b04ada`。同名JSON SHA256为 `940a96ba9032d26911f9e38072551f6b070bbb1ee0c19bf409eb6c02bbceac8b`。

本次核收范围是旧Coder单臂原FP的有效CPU正式补评分与正常清理；不是新GPU执行、全三方矩阵复跑、模型复采或正式训练准入。旧GPU null不会消失，单臂补分不证明模型稳定性；Qwen待核、双模型ACK及共享看板不由本报告操作。
