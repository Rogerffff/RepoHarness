# 7138 原 FP CPU 环境恢复实际独立验收（2026-10-03）

结论：**此次同原FP、setup900的CPU环境执行已闭合，正式结果可评分；候选仍失败，实得 `reward=0 / unresolved / tests_failed`。** 原setup300的`infra_failure/reward=None`原件保留，两次记录分别使用。此结论仅覆盖该作业，不授训练资格，也不释放wholehost。

本次非作者审查承接已验v3/input/base/dispatcher，仅只读核新原件并复算SHA/size、集合和计数；不重审59矩阵，不SSH，不运行Docker、CPU/GPU、项目/候选或模型。不是fresh全题盲审。旧审查和原闭合包不改写。

## 运输与实际身份

[新闭合manifest L5–10](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/closed_readback_manifest.json#L5)的46份原件/504,226B全部regular、SHA与size一致，没有缺额外原件；manifest本身不混入46成员。其SHA为`0b29bddc43cdbce55bf9833fc1ad200d220be8a4eaf03785ac7cfadfbab6caae`。

[actual admission](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/actual_cpu_slot_admission.json)与[slot终态](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/slot/dask7138-original-fp-cpu-recovery-20261003-v1-q01/status.json)的完整command、job、mode、package和PID逐字段相符：唯一q01、slot0、child814231、父814230，`run/swe_dask`，结束rc0。queue只有这一次attempt且`command_finished/rc0`，它是环境验收完成，不能解释成模型答对。原固定slot wrapper在已绑定base入口严格核SHA；此次没有裸启动或评分自动重跑证据。

[UID读回](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/actual_candidate_uid.json)为实际`id -u` stdout `54322`、exit0。实际container为同image `sha256:625b404c6c1c40da31df4edfea6052a10fbd30b7fb49d58072b6ee2b215fab13`，2CPU/4GiB/pids512、NetworkMode none；[CPU image inspect](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/actual_image.json)的Id/platform/RootFS及完整17键Config与已审CPU冻结表示严格相等。原GPU只有Config canonical摘要的边界保持，不能把CPU raw表示称作GPU完整raw。

[runtime binding](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/runtime_code_binding.json)的71个actual模块路径与SHA均匹配固定code8；worker `bfe59992559f9108869cb763b2a6a8f7dc547cb01533d0b1227fcb042e262219`、base `3086fb2e63fdd6c984baf717c1525ce2bdf7f8693ca9954d8cc815cb817f4312`均保持。五份脚本文本逐项SHA匹配binding，diagnostic实际scripts digest与原单shell `sha256:6f61a742aacc681b4e07e2b1825cd1d8cba5450da1791e2aae7b9eee659c0d5b`相同且supply=null；未把存在after脚本推作two-stage。实际15固定input字段与原值相等，grading_revision只有运行态`not_evaluated→parsed / apply_ok null→true`，身份摘要及参考列表保持。

[baseline exec](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/exec_logs/003.json)的425个included census条目（类型、mode、digest、path）与原baseline_manifest逐项相等，原base rebuild验证返回成功。[binding/projection](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/binding.json)均绑定原FP `sha256:451557c761f6f47f984e06695b51f66591f7ecaa8589c1188c1a5e7c6a5365e4`。trusted setup恢复并保护正式测试；projection排除候选改动的正式`test_routines.py`，保留的test-like helper由原路径规则处理。本次无conftest/fixture触碰记录；不扩大为“候选所有文件均无影响”。

## 正式结果与失败原因

[470参考完整账目](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/full_reference_readback.json#L2)逐项与原列表匹配，无重复、missing、skipped或unaccounted：

| 分区 | 参考 | success | failure |
| --- | ---: | ---: | ---: |
| 原F2P | 1 | 1 | 0 |
| 原P2P | 468 | 468 | 0 |
| 新增P2P | 1 | 0 | 1 |
| 合计 | 470 | 469 | 1 |

新增失败为`test_ravel_keyword_array`。[eval log L635–644](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/eval_logs/evallog_dask7138-original-fp-cpu_3e2f0c25.eval.log#L635)实际执行`da.ravel(array=array)`并报`TypeError: ravel() got an unexpected keyword argument 'array'`，确认了参数改名造成的既有keyword兼容性缺口。原FP未被替模型修正。[正式报告L8–16](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/report.json#L8)为raw0/unresolved/tests_failed、F1pass、P总469中1fail，infra_failure_detail=null；没有把此前未测试的None当0。

同一固定模块[日志L616–622和L1226–1231](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/eval_logs/evallog_dask7138-original-fp-cpu_3e2f0c25.eval.log#L616)为562 collected、561passed/1failed、92warnings；**模块562项与470评分参考是两个范围**，不得用561通过替代470分区账目。安装rc0/4.07s，测试rc1/15.293s，candidate segment完整且非partial，trusted setup202.623573s。候选外层shell exit0包含末尾marker输出，不能据它把测试rc1解释成成功。

## 资源、清理与限制

独立复算54个[资源样本](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/resource_samples.jsonl)：关键字段无缺项，cpu.max `200000 100000`，pids.peak28，所有pids.events为max0，oom/oom_kill/oom_group_kill均0。[precleanup L9–14、L28](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/resource_before_cleanup.json#L9)另读回OOMKilled=false。**memory.peak达到4GiB，memory.events.max=209**；这次有内存限额压力，不能称未碰资源限额或所有事件为0。完整结果已返回，未观察到OOM或PID上限事件。

[diagnostic L1091–1095](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/eval_logs/evallog_dask7138-original-fp-cpu_3e2f0c25.diagnostics.json#L1091)原样保留`resource_facts=null`、`runner_integrity_changed=true`。资源判断来自owner新增sidecar，不回写原null。前后runner digest不同（L1077–1078）；安装日志可见pytest与editable安装，但没有逐文件runner diff，变化原因仍未证，不能把安装推断冒充差分证明，也不能称runner未变。固定harness code8核验与候选环境runner观测是不同对象；本次仅认可该作业环境执行和账目闭合。

[worker status L83–98](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/actual_readback/dask7138-original-fp-cpu-recovery-20261003-v1/job/run/status.json#L83)为manager created=removed=1、open/supply/cleanup failures均空、own容器0、cleanup_ok=true，无资源监测/清理读回异常。[末次base L299](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/snapshot_v3/validated_execution_base.py#L299)调用L39–47的全1563 SHA/size核验后记录`fixed_sources_unchanged_after_run=true`；本审查又复算本地固定1563文件全通过。该远端末次核验由已绑定代码及回执证明，本审查没有另开SSH探针。slot终态finished/rc0与闭合manifest自有容器为空相符。

仍只有一个原Coder样本，另一模型缺项；候选keyword兼容性实际失败。runner变化无逐文件归因、内存限额压力也须保留。此次不外推其他题、59矩阵、wholehost或训练资格。新结果单独封存，原None与所有旧证据保留。

完整46成员SHA、实际profile/code8/scripts/参考核验、资源与清理字段及19+证据摘要见同名JSON。报告首次写入，不替代任何旧记录。
