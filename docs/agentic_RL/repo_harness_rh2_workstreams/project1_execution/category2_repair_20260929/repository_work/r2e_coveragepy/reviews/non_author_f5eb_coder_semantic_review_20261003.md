# F5eb Coder 首臂非作者语义窄核（2026-10-03）

结论：**当前 R6／076+077／用户已选 A／最终 rb3h 八键下，候选修法语义通过。无新材料阻断，无必跑新增 CPU。** 原 reward=1、8/8 保留。候选有五项遗留调试产物，工程合入前需要清理；不能称整个七项补丁已达到干净合入质量，也未授训练资格。

本次读取完整七项 FrozenPatch、baseline.tar 的相关完整源码、全部 32 个可见解释块、41 个工具参数与返回（25 Bash、7 Read、5 Write、4 Edit），并核 stream 参数与实际执行参数。只作本地读取、SHA、AST／编辑内存对拍、SQLite 内存解析及固定 parser 纯函数重放。没有 SSH、Docker、安装、模型、CPU 或项目测试。不是 fresh public reader，已接触本题私有材料；沿用已决定 A 与 rb3h，不重开边界决定。

## 当前公开目标与根因修复

实际 delivered prompt SHA `c10fd285b3fc598e74574e3345413778acd43ab8674489988fd518bed5a6a649`，含 totals 应有 covered/missing 两键的题面及中性公开开发 brief；原 statement SHA `6a516854b3c59b686b767267e0fe0a49d828934ccabd1a0e4b7159d9b883a88c` 是不同对象。brief 只提示完整字典预期可能需同步，没有给出私有断言或候选。

生产文件只在 `coverage_data.has_arcs()` 下的 totals 字典新增两行：covered 取 `self.total.n_executed_branches`，missing 取 `self.total.n_missing_branches`。全文件逐字节等于本题已独立验过 CPU gold 正对照（不是只比较 reward）。删掉这两项新增字典项后，完整 AST 等于 baseline；没有常数答案、按测试名特例、吞异常、改计数器、改评分控制面。公开测试也只有 totals 新增 1/1 两项，删掉两项后完整 AST 等于 baseline；原四项测试、fixture、时间断言、完整字典等式和其余全部预期仍在。原 fixture 执行一个目的地、缺失一个，1/1 正确。这是合理同步预期，非删改关键断言或评分污染。

| 当前要求 | 独立语义判断 |
| --- | --- |
| totals | 新增covered=self.total.n_executed_branches、missing=self.total.n_missing_branches，保留已有其他字段。 |
| optional_per_file_pair | 两键均不输出，原summary完整保留；已选A允许这种最小修法，无须强迫扩展。 |
| saved_branch_data | 条件是coverage_data.has_arcs()，跟随已测量数据而非report对象config.branch。 |
| multiple_files | report_one_file仍self.total += analysis.numbers；Numbers.__add__累加目的地分支及missing计数。 |
| measured_report_subset | get_analysis_to_report(morfs)及include/omit选择实际报告文件；json_report每次创建新JsonReporter，子集不沿用前次总计。 |
| zero_branch_in_branch_mode | has_arcs条件不依赖n_branches非零，因此分支数据中无分支也输出0/0。 |
| destination_arc_counts | Analysis按exit_counts>1的出口数及missing_branch_arcs逐目的地计数；n_executed_branches=n_branches-n_missing_branches，未替换成partial-line数。 |
| line_mode_and_context | 只在has_arcs分支加两键，行覆盖与上下文字段/过滤/断言未变。 |

每文件 summary 完全未扩展，与 Qwen 在每文件也增加成对字段的候选不同；两种都符合 A。缺少可选字段不构成错解。已有多文件总计、saved-data、子集、零分支、目的地计数与行／context行为均保留。

## 七项冻结改动逐项核查

所有七项均为 regular、100644；原投影明确纳入全部七项。FP canonical／Git 二进制往返身份复用执行核查，另独立解码每项完整字节核 SHA。两个原文件从实际 pre-solver tar 读取，原内容 SHA 与 manifest 相同。baseline 共335项；完整共享模式审查已验，不机械重做。

| 路径 | 操作／字节 | SHA256 | 判断 |
| --- | --- | --- | --- |
| `.coverage` | add／53248 | `dfc866a10b31a6a82830abe78c5f997f743c9585773a14f7cc76a864fb86ed4a` | 最终演示 SQLite 数据，合入前清理 |
| `a.json` | add／455 | `ac03afe4af0a19caedd7bc9e09edc12acc2a2aa9a409efd075e6bfc646b41417` | 遗漏 start 的0/3未测量报告，不能当成功证据 |
| `a.py` | add／38 | `311fbdbfd2d101dc84d9fd812b7a5c54ee8e2448b96dd40255a535b62a1b612b` | 三行公开复现 fixture，合入前清理 |
| `coverage/jsonreport.py` | modify／3563 | `c9bfca18f6a70f17f84a431d8651839da9eb63516539f90254a031a90ffbcf93` | 两行 totals 修复；正确 |
| `coverage_no_branch.json` | add／496 | `5d3a36c8b490bce7790153ccad93898ebb5839bff5383dd3b437d6799b7e5140` | 有效非分支演示输出，无新分支键 |
| `demo_coverage.json` | add／645 | `af708a4138d02b0cef072a0cf8eb8f52ed42367af74ac5c5b7628e0615cc8f37` | 有效分支演示，totals1/1，无可选每文件键 |
| `tests/test_json.py` | modify／5522 | `3c52986235e2ece2de057267e8f2e0a9b97fbc1dae44ffdb93536da329d2a543` | 两项 totals 预期同步；原断言保留 |

生产 before SHA `82f4f4d9dc940d0b1be6d027e66ed8c103314847d901f0281aec04d8ab34c6f3`；公开 test before SHA `70116b13adea657318148c8a1aaae40d29e66cca8660611190bf4d839db36e54`。完整文本与全部 diff、工具输入／返回和32段可见解释存同名 JSON，二进制不重复存 base64。

`.coverage` 独立按 SQLite 解码，integrity_check=ok：schema7，meta版本5.0.5a0、has_arcs=1、sys_argv=['final_demo.py']、when=2026-10-03 06:14:45；唯一 file=/tmp/tmppdd9uvnw.py，八条执行弧，无 line_bits/tracer，空 context。与最后有效演示的源码、工具返回、demo JSON 的文件名／时间／执行行闭合，没有私有测试或预期 map 数据。该临时源码在 finally 中删除。**默认数据文件含失效临时路径，后续显式 load／CLI 报告可能受影响**：这是由消费关系推断的工程质量风险，未新跑命令。

`a.py` 只有题面分支三行，无 imports、评分逻辑或劫持；三个 JSON 分别与实际工具输出逐对象相等。最后 `rm test_*.py final_demo.py` 清掉四个 test_*.py 调试脚本及 final_demo（共五个），但没清掉 a.py、三个JSON或数据库。因此不能称“临时材料已全部清理”。建议未来整理工程补丁时删掉这五项，另定新补丁身份；本次原七项 FrozenPatch 与原评分保持。

## 可见解释、所有工具与自测

完整原轨迹与 harness 轨迹同字节。原 stream 是32个text、41个tool_use，没有thinking块；已读完整可见解释，不声称取得未记录的内部推理。逐工具 ID 配对41个返回，并在内存重放所有有效 Write/Edit；两个最终改动文件恰等于 FrozenPatch。stream／effective 参数有正常规范化差异（去 cd /testbed &&、Edit缺省replace_all=false、空白行尾空格清理）；两套原参数都保留在JSON，不虚称完全同字节。

初始把旧公开expected说成已有两键与原文件矛盾；之后重读纠正。有效临时模块导入复现确实先看到旧 totals 缺键，再在修复后看到1/1。原工具共有9次错误：outfile 类型错误2次、no-data3次、Numbers非法n_executed参数1次、旧完整字典预期差异1次、扩测空集rc5两次；这些均保留。正确复现之后仍重复过旧 no-data 写法，最终“exact scenario成功／thoroughly tested”表述过宽，不能替代实测证据。

| 实际自测阶段 | 原返回 |
| --- | --- |
| 修复前单项branch／公开JSON | 1 passed 0.55s／4 passed 0.54s |
| 生产修复后、公开预期同步前 | 1 failed、3 passed 0.60s；仅新增 totals 字段引起旧字典不等 |
| 同步公开预期后JSON | 4 passed 0.58s |
| test_report／test_api -k json | 两次 no tests ran、rc5；不能算额外回归通过 |
| results | 35 passed 0.54s |
| JSON+results | 39 passed 0.62s |
| 有效非分支／最终分支演示 | 无分支键／totals1/1；仅成功输出，不扩成多文件、saved-data完整自测 |

## 正式八键、污染与CPU复用

从完整 Start／End Test Output 提取原段，AST 取固定 release parser 的三项纯函数独立重放；与 native expected map、原 diagnostics 和执行核查逐键相同，无missing/unexpected。footer `8 passed in 0.70 seconds`，testRC0，完整结束；xdist没有collected header，不补造收集行。原报告无infra、runner_integrity_changed=false。安装实际跳过，不称安装命令执行成功。

| 正式键 | expected／observed |
| --- | --- |
| `JsonReportTest.test_branch_coverage` | PASSED／PASSED |
| `JsonReportTest.test_branch_totals_add_up_across_files` | PASSED／PASSED |
| `JsonReportTest.test_branch_totals_count_branch_arcs` | PASSED／PASSED |
| `JsonReportTest.test_branch_totals_from_saved_branch_data` | PASSED／PASSED |
| `JsonReportTest.test_branch_totals_without_branches` | PASSED／PASSED |
| `JsonReportTest.test_context_non_relative` | PASSED／PASSED |
| `JsonReportTest.test_context_relative` | PASSED／PASSED |
| `JsonReportTest.test_simple_line_coverage` | PASSED／PASSED |

正式 rb3h 导入未改的 `tests.coveragetest`，使用自身临时 fixture、显式 morfs；saved-data用自身显式 data_file。没有读取这些根目录 JSON／默认数据库／a.py来满足断言。七项候选及完整工具没有改隐藏test、runner、expected map、fixture或conftest，也没有skip、删assert、强制绿色、读取私有评分控制面的操作。调试文件存在不能自动判作弊；本结论由完整内容、来源与实际消费关系支撑。

原 report 的 `patch_hygiene.test_files_modified=false` 与实际FP含公开 test 的事实并存；保留原字段，但不能用false声称公开测试未改。classification 的 runtime_private_pathset_changed=true／FP excluded_pathset_changed=true也不能单独证明访问私有评分；候选／工具没有这样的控制面写入。既有排除缓存与运输结论由执行核查负责。

复用先前独立 CPU 16行矩阵和Qwen语义核查；当前生产文件等于本题CPU gold（8/8），GPU实际全部七项原FP也直接完成8/8。没有新增语义或材料缺口要求必跑CPU。CPU镜像与GPU镜像身份分开，CPU证据不替代GPU环境验证。Qwen为code4，Coder actor/grader为code7、实际adapter仍code4；保留实际差异，不能写整树同版。共同材料、共享差异适用性及运输闭环复用执行核查，完整七维、效率、ACK及当前入口由父线程负责。

本结果可用于当前修订普通基座能力诊断及注明版本差异的两模型首臂比较；不授训练资格，不称原benchmark未修订成绩，也不称全仓回归通过或无需清理即可合入。普通a2/a3按覆盖优先暂缓。本次无新材料阻断及必跑CPU项。

## 固定证据身份

- FrozenPatch canonical digest `24793689f257128a5390fdb6df1798fb2155221c2674d8d5943b72e420043f67`。
- 总回执 SHA `5813e392337eac05414173627804feee18764aba10789ced7d1fd486d6375932`。
- baseline.tar SHA `fa69047ef338d52522c9b95015cf288aa1e8dc84fd62c6ffab430c8f0f696a2f`。

- [baseline.tar](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/attempt/frozen/baseline.tar)：4055040B，`fa69047ef338d52522c9b95015cf288aa1e8dc84fd62c6ffab430c8f0f696a2f`。
- [baseline_manifest.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/attempt/frozen/baseline_manifest.json)：77627B，`d4661fd7c319247c825140b375c55181c2e856e907ed0364345d4d44a7128b99`。
- [frozen_patch.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/attempt/frozen/frozen_patch.json)：87579B，`c435dee6ad917c9321f4e6add7cabcef76d684ac1b2de91457ad577fd4e0fe7d`。
- [classification.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/attempt/frozen/classification.json)：92B，`f5ffbaced0b3236a35e0fc6319c51b3077006f339e8a219377b606e8e26bce15`。
- [trajectory.jsonl](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/attempt/trajectory.jsonl)：358020B，`bac0157a79a72c69262e35f97f94d179bc8800fc102a588c3e9b8b533b0d30e8`。
- [trajectory.jsonl](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/attempt/harness/trajectory.jsonl)：358020B，`bac0157a79a72c69262e35f97f94d179bc8800fc102a588c3e9b8b533b0d30e8`。
- [solver_prompt.txt](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/solver_prompt.txt)：1959B，`c10fd285b3fc598e74574e3345413778acd43ab8674489988fd518bed5a6a649`。
- [prompt.txt](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/attempt/prompt.txt)：1959B，`c10fd285b3fc598e74574e3345413778acd43ab8674489988fd518bed5a6a649`。
- [coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96.diff](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/attempt/candidate/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96.diff)：6081B，`bdcbd6e59c6d65adcbac0870a413b21196cdee81e703ff5b3e1804f48c4d3fd8`。
- [projection.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/grading/projection.json)：458B，`9e497450a023ebe2d93defa3fe6bef15bbd1243c37d53ecbbee1088332550244`。
- [report.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/grading/report.json)：1875B，`cec931f0f7d164f504fc7fe46be87c8d53e9b3794621825cc065992f138cd63c`。
- [status.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/grading/status.json)：2659B，`f7d2d5aa8f9d521e4128abf44c4c772fae3f1be2cdb32b0bc993048a56addedd`。
- [input_check.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/input_check.json)：2940B，`cebc9cff5793a5980939fe50751282777e9129a1cc5118ead7db9534b8abf572`。
- [evallog_gpu1003-coveragef5eb-cod_22178277.eval.log](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/grading/eval_logs/evallog_gpu1003-coveragef5eb-cod_22178277.eval.log)：1569B，`58ca6301e3d06065b0531f18737abc5c0bd4947ef68e3c40a2967e6b1c75e8ae`。
- [evallog_gpu1003-coveragef5eb-cod_22178277.diagnostics.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-coveragef5eb-coder-a1/grading/eval_logs/evallog_gpu1003-coveragef5eb-cod_22178277.diagnostics.json)：3766B，`7fe181c82b1421c80bda960ceb713601eeb7a686be33557452f29d044e0cc98d`。
- [coveragepyf5eb_coder_a1_execution_review_v1.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/reviews/coveragepyf5eb_coder_a1_execution_review_v1.json)：20599B，`40f17b028c49582f2f8f78fbffa4f69c76a2b0c9341026d69c1e906ef48f812d`。
- [coveragepyf5eb_coder_a1_execution_review_v1.md](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/reviews/coveragepyf5eb_coder_a1_execution_review_v1.md)：1432B，`a09a3c4fee1a689214623858ae3e670b2089c9c9efd1d7c292d617c8c90ffae8`。
- [r2e-coveragepy-f5eb-r076077-cpu-r6-20261003-v1_two_model_v1.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/ordinary_gpu_probe_20261002/receipts/r2e-coveragepy-f5eb-r076077-cpu-r6-20261003-v1_two_model_v1.json)：18582B，`5813e392337eac05414173627804feee18764aba10789ced7d1fd486d6375932`。
- [non_author_f5eb_cpu_review_20261003.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/r2e_coveragepy/reviews/non_author_f5eb_cpu_review_20261003.md)：11133B，`f553d8c2e34fe00ac2c0d421fa9cd569fef52defb532ed615ce319b879841eea`。
- [non_author_f5eb_cpu_review_20261003.json](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/r2e_coveragepy/reviews/non_author_f5eb_cpu_review_20261003.json)：181805B，`d1b35179e30d3668b0b8139e7e2d877bc8d45060001fd32c0fabd5a0b9ea027e`。
- [non_author_f5eb_qwen36_semantic_review_20261003.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/r2e_coveragepy/reviews/non_author_f5eb_qwen36_semantic_review_20261003.md)：7674B，`8da9d0d4b5d5b82ef8264a476be49378d2b9f1ddd909e79c8fe4a6e92f63c511`。
- [non_author_f5eb_qwen36_semantic_review_20261003.json](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/r2e_coveragepy/reviews/non_author_f5eb_qwen36_semantic_review_20261003.json)：14239B，`c1c93b8762b334e699a916af347c20d8fcdfaf4bf5f70c0fcdaa16525579de6c`。
- [test_1_rb3h.py](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/r2e_coveragepy/tasks/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/materials/test_1_rb3h.py)：12432B，`fd4d6ac9ca8e1edbe148e30cc73a1f48c9a3eecb4ffbaef5a388dbd430de2050`。
- [public_devbrief_20261003.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/r2e_coveragepy/tasks/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/public_devbrief_20261003.md)：670B，`840de42ff336cc91217a0f4e1f297a2c45c707ccf2caea8a73934af2ca5ee920`。
- [frozen_patch.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/category2_repair_20260929/coveragepy_owner_cpu/remaining_r6_v1/f5eb_formal_matrix01/gold/artifacts/r2e_gym_subset--coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f/a1-47263148/frozen_patch.json)：5761B，`73825998d907b3bb0c80f7075a5cbb3a3c9f177a7e8c154e57d9b0dcbc51d376`。
- [r2e_parsers.py](/Users/roger/Desktop/claude-code-verl-stage0h/runs/category2_repair_20260929/releases_20261003/r2e_080_087_swe8_git_candidate_v1/repo/rh2/src/repoharness2/envpack/r2e_parsers.py)：10622B，`339b7c80cca516dc7d1bcf9c11e3ff9a42f1bc993b5027a0d06c41c85d024b58`。
- [expected_output_json.json](/Users/roger/Desktop/claude-code-verl-stage0h/runs/category2_repair_20260929/releases_20261003/r2e_080_087_swe8_git_candidate_v1/repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/files_20261003_v16/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/expected_output_json.json)：508B，`e150a338879b6703fba4950e2f3eeb284ea415140a6f68c1c80cf085aca6e0d9`。
