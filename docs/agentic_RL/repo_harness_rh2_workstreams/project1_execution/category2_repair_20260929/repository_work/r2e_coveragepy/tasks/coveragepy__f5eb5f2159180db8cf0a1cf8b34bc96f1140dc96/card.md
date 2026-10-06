# f5eb5f21：JSON分支汇总，最终rb3h／8键

2026-10-03。**两模型首轮各原reward1／8-of-8保留；修法符合已选A，公开预期同步合理，七维与非作者语义核查完成，无新材料阻断或必跑CPU。** 原请求returned/ACK；Coder保留5项调试产物及开发失败。普通a2/a3因覆盖优先暂缓，单次不判稳定，不授训练资格。

沿用户09-30已选A：每文件summary可包含covered/missing两字段，出现任一则须成对且值正确。实际采用最终test_1_rb3h.py和8键expected，保留保存后数据、目的地分支弧计数、多文件、零分支与只报告测量文件子集。原4键保留并增加4键，076/077整体替换053/054；旧rb3与最终rb3h不同，不能混记。公开题面保持原字节。见[实际版本／结果](results_manifest.json)与[材料变更](material_changes.diff)。

[实际公开交付](cpu/public_delivery_r6_check.json)包含完整原题面和rendered prompt；真实CC桩执行预检、环境、临时分支JSON和原公开JSON测试，均退出0，公开测试4通过。agent54321、Python3.7.9、pytest4.6.6、coverage5.0.5a0，工作树导入正常。FrozenPatch为空，原正式NOOP3/8=0，完整基线／运输／排除证据往返及清理通过；原公开JSON缺分支covered/missing totals，符合初态缺陷。

原16行计划由该同版实际NOOP和新15候选覆盖。[正式矩阵读回](cpu/formal_matrix_r6_check.json)证明：gold/A1/C1/rv_sym_xml各8/8=1；其余11个错误候选得0。C3只在保存后数据失败，LF/FC/wr_alldata_proj只在跨文件/报告子集失败，NB只在零分支失败；其余路线的完整逐键map均与原件一致。实际补丁及投影、setup材料树、runner、image/recipe/base、完整测试段、失败类别和清理均核对，无infra误记。新15行job自然退出0、标签容器和网络残留0。

[非作者CPU核查](../../reviews/non_author_f5eb_cpu_review_20261003.md)由干净上下文GPT-6.1 Sol/high子agent完成，独立核16行逐8键、15份实际补丁和冻结源码、公开首请求与四次工具/SSE返回、335成员baseline.tar、完整往返及清理，无具体阻断。它接触本题私有材料，不是fresh公开读者；依据原件离线核查，没有新CPU或模型执行。有效[材料窄核](../../reviews/non_author_f5eb_material_review_20261003.md)和旧独立采用版语义继续复用。

[作者CPU快照](cpu/cpu_acceptance_r6_v1.json)保留当时pending状态；通过审查另附报告。[cpu_matrix.json](cpu_matrix.json)是已绑定SHA的原输入计划，旧planned/not_run字段不回写；完成事实以formal_matrix_r6_check和results_manifest为准。37份旧最终rb3h日志的历史读回不计本轮新运行。

[公开开发说明](public_devbrief_20261003.md)只提供环境、公开pytest命令及原测试完整字典比较的事实。合理新增字段后，原公开预期可能需按题面同步；不能仅用旧格式断言失败否定修法。solver不接收私有断言或候选。额外brief的最终GPU交付由执行者核实际首请求。

[固定探针请求](probe_request.json)使用R6、原gold正确对照与probe-wide-v1，每模型首轮1次。本题主收到约定各模型完整回执后，分析真实修法、定位、工具／并行机会、验证、效率和结束原因，再做必要修复与按影响复验。截断、缺模型或缺评分均待接续；单次不作稳定能力结论。当前仅支持标明修订版本的普通诊断，不报无版本说明的原benchmark成绩。

历史依据：[已定A及最终材料](../../../../../category3_diagnosis_20260929/tasks/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/result.md)、[独立采用版复核](../../../../../category3_diagnosis_20260929/tasks/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/review.md)。当前协作和归档见[本仓入口](../../preparation.md)。


## 两模型首轮与接续

当前076/077 8/8；生产全文等于已验CPU C1，公开四项预期同步正确。扩测不存在的test_report.py没有执行测试，后续只重复JSON四项，不称全仓回归或新增覆盖。无新材料阻断、无新增必跑CPU。 见[七维分析](model_analysis_qwen36_a1_20261003.md)、[非作者语义窄核](../../reviews/non_author_f5eb_qwen36_semantic_review_20261003.md)。原评分、FrozenPatch和所有自测失败保留。

Coder仅在totals追加两个Numbers分支属性，生产全文与此前CPU gold正对照完全一致；每文件可选字段省略，符合A。公开测试只补totals1/1，原完整断言保留；不是评分污染。公开JSON+results共39项通过，两次空测试集及重复复现错误均保留，不能称全仓回归。L490删除五个脚本，但FP仍留a.py、三个JSON和.coverage五项调试产物；默认DB指向已删除临时源码的后续消费风险仅静态推断，不改原评分。见[Coder七维](model_analysis_coder_a1_20261003.md)及[非作者语义核查](../../reviews/non_author_f5eb_coder_semantic_review_20261003.md)。

当前配对入口：[首对分析](model_analysis_first_pair_20261003.md)、[机器结果](model_analysis_first_pair_20261003.json)。旧Qwen单臂报告保留原时间点及SHA。两个有效a1保留；[普通重复计划](repeat_sampling_plan_20261003.json)拟额外每模型2次至总3次，当前因覆盖优先暂缓，未提交新固定请求/未执行重复。实际Qwen code4、Coder actor/grader code7且adapter仍code4，材料/镜像/prompt/评分脚本实值相同，不宣称整树同版。
