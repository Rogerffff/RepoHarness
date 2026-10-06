# 8801 同原FP诊断宿主adapter独立窄核（2026-10-03）

结论：**最终adapter `83a870c4bebd21540f0ffe02ba0b575e16b98288e1f3593ae68e6d4ff72fa0fa` 未发现静态阻断，可由owner仅在宿主首次prepare。** 本审查没有运行adapter、capture或judge，不确认新输入产物已生成，也不作fresh语义裁决；实际raw1不等于整题完成，不授训练资格。

旧[prepare L16–37](../tools/judge_job_from_formal_log.py#L16)要求一份矩阵ledger及`candidate.apply_user=agent/54321`。本次原actor确实是54321，而CPU grader通过可信frozen-delta manager投影后，实际候选测试`id -u=54322`。新adapter在[L141–165](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/prepare_original_fp_diagnostic_v1.py#L141)分别绑定两者，用`not_a_formal_matrix_ledger=true / ledger_kind=verified_original_FP_runtime_binding_not_formal_matrix_ledger`明示runtime binding来源；没有伪造旧ledger，也没有改变UID事实。

[最终L43–65](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/prepare_original_fp_diagnostic_v1.py#L43)逐核1581 snapshot与41闭合原件的regular、安全相对路径、唯一性、SHA和size后才读取source。初稿仅核manifest SHA和粗slot终态的缺口已在未执行前修正。当前本地原件41份/353,509B及snapshot全成员复算通过。[L101–112](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/prepare_original_fp_diagnostic_v1.py#L101)要求唯一q01、slot terminal与admission的job/package/run/slot/command/cwd/start/父子PID逐字段一致，并核完整command等于本次唯一launcher回执；本次真实slot字段均匹配。

[L69–140](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/prepare_original_fp_diagnostic_v1.py#L69)核job/status/done、FP/baseline/material、projection原physical/included path、实际54322 UID、695d image与21e77 RepoDigest、2CPU/4GiB/pids512/断网、原8358…single-shell scripts、report与完整log SHA、45参考逐项完整。diag task/trajectory/material/sourceManifest与binding原attempt均明确绑定。本审查按真实原件核这些新增字段可兼容；环境实际71模块code8及资源/清理独立验收另封存，不把adapter成员SHA核验冒称它重做全部环境字段审计。

[L149–157](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/prepare_original_fp_diagnostic_v1.py#L149)固定capture protocol、v3 prompt和config SHA不变，仍调用原`validate_packets(segment, 'full_import')`。raw0仍为fail_behavior；raw1只有完整capture且13–23条才进入awaiting，否则needs_evidence。匿名输入仍是`id / semantic_judge_input`，r+SHA公式与旧prepare相同，仅ledgerSHA指向明确标注的runtime binding；case_id只留private binding。本审查核[旧finish L85–138](../tools/judge_job_from_formal_log.py#L85)和[validator](../tools/validate_semantic_verdicts.py)读取字段相容，不改输出校验或自然语言判定标准。

输出目录`mkdir(exist_ok=False)`、各文件open x；输入断言异常会停止并可能保留部分新目录。它不会输出诊断成功，也不允许盲复用该目录；错误后的新namespace及证据处理仍归owner。该边界保持fail-closed，不制造缺证状态下的pass。

后续仍需owner首次prepare产物SHA/捕获完整性核验、真正fresh independent judge输出，以及原host finish/validator的完整验收。仅raw1、构造通过或历史420控制都不能替此裁决。只核新增宿主运输适配，不重审R16/420，不SSH、不CPU/GPU/模型或候选执行，不改共享旧协议及历史证据。原None/单Coder/另一模型缺项/训练资格空保持。

| 固定对象 | SHA256 |
| --- | --- |
| 最终adapter | `83a870c4bebd21540f0ffe02ba0b575e16b98288e1f3593ae68e6d4ff72fa0fa` |
| capture protocol | `7886a70ac59d051eca4459c6e32d94b77159c6890341183041dc73df03d1292a` |
| v3 prompt | `9d49671b56ae155f9183d8a0280ff7e779959de2697cdf3887ba4f558f2c19c1` |
| v3 config | `7e7e861112af22ec7be814a084e395070a5806777eff908dd02c746e8c8acfea` |
| 原prepare/finish | `1a4c9a97470b026772961b9f7981a6f910d9f142e41e5ffbf8ff8c7486a51d12` |
| 原host validator | `4880feba7ace4e133475a8ceeb4d3b23b7d38fff764065e5d69bb59baa1e196b` |
| 本次41件闭合manifest | `19525fd89cd0dec61791aa0521576ce7e29e4fef6170714d2464647a4eaa2dcb` |

同名JSON保存全部证据SHA及边界。报告首次写入H/reviews，不改任何旧报告。
