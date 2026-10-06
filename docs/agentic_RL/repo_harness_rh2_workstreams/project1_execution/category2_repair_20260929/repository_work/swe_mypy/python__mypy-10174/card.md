# mypy10174：保留严格比较的真实负例

2026-10-03 21:33（Asia/Singapore）。base `c8bae06919674b9846e3ff864b0a44592db888eb`，mypy0.820。R6正式矩阵0/1/0保持。原Qwen候选的CPU r16窄复验及新GPU80418df/code8实际安装/四参考重评分均已由题主和两非作者验收，见[新GPU收口](new_GPU_regrade_acceptance_20261003.md)。完整1472基线/50投影含49cache保持，editable真实成功、四PASS/reward1、清理正常。旧GPU安装RC1/raw1与CPU预热范围分别保留；本次没有新模型生成，Qwen仍一次观测。原[GPU请求](../probe_request.json)现已returned/ack，Coder新增首轮与两模型[配对验收](two_model_first_round_acceptance_20261003.md)完成；两臂各四参考通过，修法不同。本包无CPU/GPU待办；每模型一次观测，训练、留出资格均未增加。

公开目标是在 `--no-strict-optional --strict-equality` 下消除 `Optional[Any]` 成员检查的误报，同时保留真正不重叠比较的诊断。原F2P覆盖前者；原两条P2P只是未导入Any的提示。原参考保持不变，再追加与同开关相配的成员检查保护。

新case复用精确base中 `testStrictEqualityWithFixedLengthTupleInCheck` 的 `1 in ('x', 'y')` 和现成桩，唯一语义变更是增加 `--no-strict-optional`。该行为有base的strict-equality文档及既有公开测试依据；不从gold输出反推新要求。原F2P内容和两条P2P未删改。

[修订记录](revision_proposal.json)引用 [有效补丁](private/effective_test.patch)、[新增case](private/added_case.test) 和 [源码负对照](private/disable_non_strict_comparisons.patch)。负对照在 `dangerous_comparison` 中对非strict-optional直接取消比较诊断。原评分实测noop0／gold1／负对照1，见 [原CPU回读](original_cpu_readback_20261003.json)。新版本正式实测0/1/0，见 [修订后CPU回读](revised_cpu_readback_20261003.json)：负对照原三参考均过，只新增P2P因真正不重叠诊断消失而失败；gold四参考全过。新增case此前的私有窄验base/gold通过、负对照失败另保留为 [诊断证据](private_behavior_readback_20261003.json)。

09-25正式actor原例确有假阳性，32项公开回归通过；私有gold原例修复。09-19固定派生grader原官方矩阵noop0/gold1。这些证据支持接续准备，不能代替新材料/新宿主验收。历史actor有 `test-requirements.txt` 初始改动；新运行须解释该初态、冻结所用配方，不能把不同条件合并为同一次验收。

已完成：公开依据和材料窄核；原材料三候选漏判确认；新增case校准；第六版新三候选正式矩阵。新矩阵每候选四参考实际执行/解析，缺席/跳过/段外解析均0；安装editable构建与安装成功，源码来自/testbed，runner摘要未变，可信测试恢复/保护成功，源码投影未含测试文件，候选和grader清理及完整退出正常。

本轮正式登记：第六版 `cat2-cpu-r2e080087-swe8-git-20261003-v1`，1F/3P；producer为 `s2/ingest_mypy10174_swe8_v1`，有效补丁91ea4e…、grading b24e78…已在受信loader读回。完整身份见 `results_manifest.json`；cpu-a855成员及48/216可信读回经总协调确认。新job重新prepare，没有改绑旧FrozenPatch。

真实CC actor见 [当前actor证据](actor_cpu_readback_20261003.json)：公开复现确有误报，所选1项公开回归通过；不冒充历史32项全量重验。第六版公开bundle、镜像、Git四件和builder均保持第五版，私有测试增量不要求机械重跑该公开actor。继承的bashenv写入标记未测已明列。新增节点ID已在正式评分实际执行：`mypy/test/testcheck.py::TypeCheckSuite::testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional`，没有.test文件层。新正式前两请求因CPU槽忙退出75，没有执行，成绩来自r3新job。

本题题面不改，无需新的公开读者。两非作者核查已披露gold/private上下文，不当作fresh审。普通GPU请求两模型各先1次，执行者另核实际镜像、提示交付及版本；实际模型轨迹和候选仍由本题主分析。CPU参考覆盖限于已知漏判，ledger包版本`?`及安装非逐成功命令数字回执的限制留在收口记录；训练、留出资格及模型能力结论均未增加。

GPU沿[轻交接说明](gpu_original_regrade_handoff_20261003.json)执行一次原FP新GPU重评分，现[题主固定验收](new_GPU_regrade_acceptance_20261003.json) SHA `5689bf5a295b6d8adbb578664d38453dbe48d16914517c8910e9e24b62ffe282`已回告执行者。79件闭包和22个固定执行输入相符，正式三pip完整输出成功，但逐成功命令数字RC缺席；四正式参考真实PASS。旧FP51项含候选测试修改，该测试继续被可信投影排除，原49cache保持；不把“投影未含测试”描述成原模型从未改测试。CPU r16仍仅是CPU观察，新的GPU结果另有完整原件；不新增普通探针请求或Qwen采样。
本题code4与code8的manager/整树不同，实际材料、脚本、命令、预算及三分区四参考相符。systemd已收集后的not-found默认RC0不证成功；unit journal与done证流程完整，四PASS另由原eval/exec核实。未新增pytest进程内目标模块SHA，资源/资格空值保留；无具体矛盾就停止本次增量核验。后续Coder首轮完整原件、轨迹和新增两非作者核查已完成，见[逐轨迹分析](coder_first_arm_trace_20261003.md)和[配对验收](two_model_first_round_acceptance_20261003.json)。Coder原66项全部投影，55cache/10开发脚本/源码保持；安装成功、四PASS、清理正常。根因顺序误解、flags伪对照和自验范围过宽保留为行为问题，无新增材料或评分缺陷。普通追加采样按覆盖优先暂缓。
