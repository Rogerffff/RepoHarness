# 8801 同原FP CPU环境恢复实际独立验收（2026-10-03）

结论：**该唯一CPU作业的环境执行、正式45参考账目与清理已闭合，实际行为分为raw1/resolved。** 本报告不判整题诊断语义完成；fresh独立语义裁决仍须另行验收。原setup300的infra/reward=None与此次raw1分开保留，不授训练资格，不释放wholehost。

本次承接已验v1/input/base/dispatcher，仅只读核实际闭合原件并复算SHA/size、集合与字段；没有SSH、Docker、CPU/GPU/模型、项目或候选执行，不重审29/59矩阵或420，不修原FP，也不覆盖旧报告。

## 完整读回及实际身份

[manifest L5–10](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/closed_readback_manifest.json#L5)的41份原件/353,509B全部regular，逐项SHA/size正确，无缺额外原件；manifest本身另计，SHA `19525fd89cd0dec61791aa0521576ce7e29e4fef6170714d2464647a4eaa2dcb`。本地1581固定snapshot成员也再次全量SHA/size通过。

[actual admission](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/actual_cpu_slot_admission.json)与[slot terminal](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/slot/dask8801-original-fp-cpu-recovery-20261003-v1-q01/status.json)的完整command/job/package/run/slot/cwd/start与PID逐字段一致，并匹配本次唯一launcher：q01、slot0、child817580、父817579，结束finished/rc0；queue只这一次attempt，command_finished/rc0。[实际id-u](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/actual_candidate_uid.json)为54322/exit0，与原actor54321分别记录，没有将trusted frozen-delta投影伪称matrix agent apply。

[actual image完整RepoDigests](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/actual_image.json)仅有`xingyaoww/sweb.eval.x86_64.dask_s_dask-8801@sha256:21e77aea7025bad694a5c600ed6d4b372c80c83bc319fafa2fedb23d9ff48483`，actual ID仍为`sha256:695d2cc28e303a0224c1109fe245f7296c6290d480124fa4fd4cc2ad072124b1`。Id/platform/RootFS与CPU完整17键Config严格匹配已冻表示；manifest-bound原来源镜像模式保持，没有7138式local build替换。实际2CPU/4GiB/pids512/NetworkMode none，与原profile相符。

[runtime binding](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/runtime_code_binding.json)的71实际加载模块路径/SHA全部匹配固定code8，worker `afb419eb2dfe5b8955fd3d3beb8cbf4b1ac9e91c85bee281ecba7267e82f2c1a`、base `3086fb2e63fdd6c984baf717c1525ce2bdf7f8693ca9954d8cc815cb817f4312`未变。五份脚本文本SHA逐项匹配binding，actual单shell scripts `sha256:835811ced3255278f9fd36b35e68ae6deee2791ed710367d832e4d9954af67e5`保持，supply=null，不推作two-stage。15固定input字段及grading_revision身份/参考列表保持；仅运行态not_evaluated→parsed、apply_ok null→true。

[baseline exec](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/exec_logs/003.json)的463 included census条目逐类型/mode/digest/path匹配原manifest，固定base rebuild验证成功。[projection](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/projection.json)继续绑定原FP `sha256:739f20878faca8da44f55b164596413fe411b9a1054e4d9c227212bc0dabd7a1`，仅included `dask/config.py`。trusted setup恢复并保护正式test_config.py，control_surface成功，无候选test-like/conftest/fixture触碰记录；public/materials仍为原绑定。

## 真实行为结果及因果限制

[report L8–16](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/report.json#L8)为resolved/reward1、failure_category和infra_failure_detail均null，F2P2/2pass、P2P43中0fail。原[None结果](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/snapshot_v1/source/closed/queue_v31/results/gpu1003-dask8801-coder-a1/result.json#L14)不回写；此次不是新模型求解。

| 原固定分区 | 参考 | success | failure/missing/skipped/unaccounted |
| --- | ---: | ---: | ---: |
| 原F2P | 2 | 2 | 0 |
| 原P2P | 41 | 41 | 0 |
| 新增P2P | 2 | 2 | 0 |
| 合计 | 45 | 45 | 0 |

[full reference readback](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/full_reference_readback.json)逐项列表和集合与原45参考相等，无重复或缺项。[eval log L1385、L1539–1543](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/eval_logs/evallog_dask8801-original-fp-cpu_aff67a56.eval.log#L1385)为45 collected/45passed，测试marker rc0；安装rc0/2.274s，测试rc0/2.239s，完整非partial candidate segment。可见诊断包等marker数量仅是运输证据，不能代fresh自然语言语义裁决。

本次trusted setup为134.698491s，低于旧300预算。只据此认可**已授权setup900/whole3600方案在此次CPU实际成功**；不能证明900是唯一或必要原因，也不能证明原GPU准备时延已消除。本报告不为这些未知因果追加未经授权实验。

## 资源与收口

独立复算38个[sidecar资源样本](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/resource_samples.jsonl)，关键字段无缺项：cpu.max200000/100000、pids.max512、pids.peak34，所有pids.events max0；memory.peak2,047,328,256B，所有样本memory low/high/max/oom/oom_kill/oom_group_kill均0。[precleanup L9–14、L28](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/resource_before_cleanup.json#L9)另证OOMKilled=false。此次未观察到PID或内存上限事件，不外推其他题或wholehost容量。

[diagnostic L216–234](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/eval_logs/evallog_dask8801-original-fp-cpu_aff67a56.diagnostics.json#L216)保留resource_facts=null，资源判断来自独立sidecar。runner_integrity_changed=false，前后摘要均`f42f077db8e6148dc3319c685c359cf5d5f001b5e92b8e3529a977deeb82d8cc`；这是已记录摘要相等的范围，不冒充逐文件diff。

[status L83–98](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_readback/dask8801-original-fp-cpu-recovery-20261003-v1/job/run/status.json#L83)为manager created=removed=1，containers_open/supply_open/cleanup_failures空，own容器0、cleanup_ok=true，无监测/清理读回异常。固定base末次逐1581文件SHA/size核验后记录fixed_sources_unchanged_after_run=true；本审查本地重验也全部相等，非新SSH探针。slot/queue已terminal，闭合manifest自有容器为空；只关闭本作业，不释放wholehost。

raw1证明正式行为参考通过，题目要求的独立diagnostic语义另行fresh验收；本报告既不借旧420判断，也不代判新judge。仍是原Coder单样本，另一模型缺项，训练资格空。owner原点时分析10,472B/SHA `cb17d453ba4620ebe7e9bf88c60fac1deb6d753753a38dc45c9c7754c08f014b`保持；其中CPU/语义pending是当时状态，不能静默回写。本次事实另存于此。

全部41成员SHA、实际RepoDigests/71模块/5scripts/45账目、资源及收口核验见同名JSON。报告首次写入H/reviews，旧证据不变。
