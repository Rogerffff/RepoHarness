# 8801 同原FP实际诊断绑定独立窄核（2026-10-03）

结论：**本次actual job→raw packets→23匿名输入→fresh输出→固定host outcome的绑定链闭合，未发现阻断。** fresh judge为19pass/4fail/0uncertain，host state为`fail_diagnostic_semantics`。这只表示该真实候选的诊断未达目标，不指材料缺陷，不产生或授权训练reward。正式行为raw1与诊断失败分别保留。

本审查只读原件，以stdlib解析base64/JSON、读取固定protocol AST字面量并复算SHA/size、集合、匿名key和引用子串；没有运行adapter、protocol、finish/validator、项目、CPU/GPU或模型。**不代判自然语言、不复用420历史裁决。**

## actual job与匿名输入

[runtime binding](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_diagnostic_v1/original_fp_evaluation_binding.json)绑定原FP `sha256:739f20878faca8da44f55b164596413fe411b9a1054e4d9c227212bc0dabd7a1`、baseline `sha256:aff22965ee08670e719a8ae2c026cf1f78ef93e201356921845b61ada0262aea`及本次CPU JOB。原actor54321、grader实际54322分别记录，明示可信frozen-delta投影及非矩阵ledger。其11个actual_source、closed manifest、固定prompt/config/protocol/adapter引用SHA和size全部匹配原件；adapter仍为83a870…fa0fa，job ledger_sha256确实指该runtime binding，没有伪造旧matrix ledger。

**现有效运输统计必须同时读[主actual环境报告](non_author_8801_original_fp_CPU_environment_recovery_review_20261003.json)和[marker统计更正](non_author_8801_CPU_recovery_capture_count_correction_20261003.json)：23 diagnostic / 10 FALSY_COMPAT / 1 raw import。** 主JSON原compatibility0已明确更正，不能继续引用；两sealed文件均保持原SHA。此次从完整eval log中唯一test segment独立解码23 DIAGNOSTIC和10 FALSY_COMPAT，另数1 import marker。

23 packet case唯一、集合等于13固定base案例加10实际diagnostic_failure假值分支；before/after可读及content SHA逐项等于固定fixture字节。每个[judge input](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_diagnostic_v1/judge_inputs.json)仅含匿名id和semantic_judge_input；payload逐项等于原packet可见异常与固定protocol的trusted_facts。后者由冻结AST字面量核，未另执行YAML或候选。全部23 payloadSHA、r+SHA匿名ID、private cache_key按已验公式重算相等；case_id仅在[private binding](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_diagnostic_v1/private_run_binding.json)，不列入judge输入。

## 输出引用与fresh来源

[独立输出](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_diagnostic_v1/independent_verdicts_v1.json)23个ID各一次，恰好覆盖输入，无未知、缺失或重复；每份解释非空，所有file/reason/contradiction引用都确实在同项可见诊断message、displayed_type或notes中。没有从trusted_facts取引用；pass项有file/reason证据且无contradiction。独立复算19pass/4fail/0uncertain。四fail经private ID映射对应syntax_brace/tab的directory/file；这是映射已做出的fresh结果，不新增语义理由。

[root新spawn观察](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_diagnostic_v1/fresh_judge_dispatch_v1.json)记`collaboration.spawn_agent`、`fork_turns=none`、canonical task `/root/diagnostic_live_v3_20261003`、不override model/effort。与[provenance](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_diagnostic_v1/independent_judge_provenance_v1.json)一致；精确三份允许文件（v3 prompt、boundconfig、匿名inputs）的路径/SHA/size均匹配。input/output/job/prompt/config以及[owner crosscheck](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_diagnostic_v1/actual_fresh_provenance_crosscheck_v1.json)引用也逐项核验。本审查另外只读`collaboration.list_agents`，确见该task completed，其完成回复给出的输出/provenance SHA与本地原件一致，19/4/0一致；provenance自身SHA null保持，由外部完成回复和本审查SHA闭合，不填造自引用。

这些证明当前新task和当前输入输出绑定。**禁读来源于fresh代理自声明，不是独立读权限审计或密码身份认证；精确后端model/effort未暴露。** fork_none由root记录的新spawn参数与代理provenance交叉支持，当前list_agents补证实际task完成，不冒充它返回了fork/model隐藏字段。没有把历史420输出作为指定输入或本次结果依据。

## host outcome与适用边界

[diagnostic_outcome](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/actual_diagnostic_v1/diagnostic_outcome.json)保留job所有绑定字段（state除外），semantic_verdicts逐ID等于本次独立输出，verdict_sha为实际output SHA；validation complete/issues空。4个fail使state按固定[finish](../tools/judge_job_from_formal_log.py#L85)/combine规则为fail_diagnostic_semantics。旧finish/validator SHA仍与adapter静态审查一致，本审查未重新执行它们，也未以关键词替judge裁决。

适用结论是：本次环境和行为已完成、45参考全pass/raw1，但同一真实候选的独立诊断目标未通过。原None、单Coder、另一模型缺项及统计更正保留；不推断材料缺陷或未来全部措辞，不授训练reward。adapter一次宿主prepare是owner记录，单套新OUT/x写产物相符，不另声称有OS调用次数审计。

| 当前绑定证据 | SHA256 |
| --- | --- |
| runtime evaluation binding | `2d577121508efdccc70b64a70030c10d561636c855a280138da4291eb4934bc5` |
| 匿名inputs | `fcb9f3d2e169758399d33556578d5d159a3c0f16a4baeda84e289535617ef04f` |
| fresh output | `e5b1224e9d174fdf735d9d87927d12f3ac0f41abbf1f931a3c5355e1ddd3e5b3` |
| fresh provenance | `03c5d2a9997583fe25ffc60094ad2c756cbdfbfe9e4e0a2bad5416c87d40356f` |
| 新spawn记录 | `8c470631640ccbd1783b0aaf9e09437ae70c7e1db32f74eaf2a018f189eb43b8` |
| host outcome | `16ed6611dfb4114fe690eabcc4d60b0bb64d1eac1b2c1a2e628df2c1a33b3513` |
| 主actual环境报告JSON | `0748ccd3c1a7e5a388b4851cf994a5a7942c588c9dbe51d2b69e62d71191aff1` |
| marker更正JSON | `7b0536208df16c7a559d5c6dc08d1f2e2459f67b78a1ef36cfc5178d3362ff34` |

完整逐项绑定核验和证据SHA见同名JSON。报告首次写入H/reviews，原件及旧报告不回写。
