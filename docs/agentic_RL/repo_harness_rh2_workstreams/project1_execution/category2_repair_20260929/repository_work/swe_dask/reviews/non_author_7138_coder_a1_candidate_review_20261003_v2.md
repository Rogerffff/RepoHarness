# Dask7138 首次真实 Coder 候选：非作者窄核

归档位置／链接纠正版（v2，2026-10-03）。本次只把题主报告入口归入 H/reviews 并重算相对链接，**没有重新语义审查，也没有改变结论、证据范围、正式 None 或资格状态**。原[封闭包内首次 MD](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/reviews/non_author_7138_coder_a1_candidate_review_20261003.md)保持历史原件，SHA `cb27454e279a9f606cc45290e34f6f6a9be9ff2b17688dc39491224b3455da1a`；H/reviews 的[JSON](non_author_7138_coder_a1_candidate_review_20261003.json)为原 JSON逐字节排他复制，SHA仍为 `33a04fc2913791a4f58b3e1f32def5780269eeb113d960d1c33c9f9e603b94ac`。未删除或改写封闭包内原件。后续报告归入题主 H/reviews，不再向 sealed closed_snapshots 追加评论报告。

2026-10-03；对象 `gpu1003-dask7138-coder-a1`。**位置调用的 array-like 修复路线成立且有公开自测支持，但最终参数改名破坏已批准的 `array=` 兼容，构成P1候选阻断。原正式评分仍为setup300 infra／None，不能计模型失败。** 当前没有CPU setup900新分；原输入、FP、baseline及评分运输没有发现阻止同FP恢复的静态阻断，新恢复worker和实际CPU环境不在本封包中，尚未验收。

本reviewer复用已审7656、7305、9378及harness的上下文；这是本题首次读取，未参与候选实现，也不重审既有59行矩阵。属于非作者复核，不冒称无历史上下文的盲审。本轮没有CPU/GPU/模型新执行、SSH/Docker、候选运行、归档解包执行或原件/共享源码修改。其它题历史文件只核闭合SHA，不展开其私有语义。

## 权威闭包及实际材料

[508文件清单](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/gpu1003-dask7138-coder-a1_closed_manifest_v1.json) SHA `8df01ab39be672264d938cccd1679121d20dda8a6be3f1af822b59db004d05ab`；508/508 SHA及字节数匹配，总37710899 B。[sync_receipt_v3](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/sync_receipt_v3.json) SHA `7810ca6f7920f0abb37dfc8d6aff147ccde59d78cade61ffb54115940f82a247`；508个source→authoritative映射逐项与清单相符。仅使用本权威包，未借legacy partial mirror补替原件；receipt保留两个legacy差异，未回写。

外层[probe_request](../tasks/dask__dask-7138/probe_request.json) SHA `819534ee0ada1c63ec2a2ad4a37a22f97aa4642e8ac010ad7083b3a421b123da` 与包内[实际owner_request](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/prepared_dask_pandas_four_code8_v1/dask7138/host_evidence/owner_request.json)字节相同。[题卡](../tasks/dask__dask-7138/card.md)、[revision](../tasks/dask__dask-7138/revision.json)是在父任务明确补充授权后读取的导航资料，不在508闭包内，其缺席不构成封包不完整。revision仍留早期preparation状态，当前实际输入以prepared/private registry及input_check为准；effective patch SHA和1F/468P+新增1P引用与实际消费相符，未采用旧状态替代现场。

实际revision为 `dask7138-array-keyword-v1`，材料身份 `3e94408ef02d1c2fb6c9113a5c86920325280b2a80962bf579d98087e283136e`，1F2P+468原P2P+1新增keyword P2P=470参考。[私有host grading](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/prepared_dask_pandas_four_code8_v1/dask7138/private/host_grading_views.jsonl)与[发布registry](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/prepared_dask_pandas_four_code8_v1/prepare_overlay/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/dask7138_fixed_test_patch_v1/material_revisions.json)的有效test patch字节相同，SHA `2f3c5c539816149a06b6c460b5d79d6b3223f452cd5862bcdbac41faf76bc44a`。新增 `test_ravel_keyword_array` 是批准范围，要求既有array关键字兼容；没有新加零拷贝或所有NumPy参数要求。

公开[prompt](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/queue_v26/results/gpu1003-dask7138-coder-a1/attempt/prompt.txt) SHA `b02c916a8faba2fe3718f1e67a58d230df7863c8abd4864ec7e78781200f46c8`；solver_prompt字节相同，首实际HTTP提示只发生24个LF→CRLF转换，规范化后全文相同，无新增语义。题面本已指出asanyarray转换方向（拼写示例有原始typo），必须保留引导属性；私有keyword调查及矩阵没有注入solver。

## 原FrozenPatch与逐操作重放

[FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/queue_v26/results/gpu1003-dask7138-coder-a1/attempt/frozen/frozen_patch.json)文件SHA `e18d7c5d01354d64d05832def64d9b29b4f282070f50d9b30b3f4794f522c09e`，sorted compact JSON规范摘要 **`451557c761f6f47f984e06695b51f66591f7ecaa8589c1188c1a5e7c6a5365e4`**。[baseline](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/queue_v26/results/gpu1003-dask7138-coder-a1/attempt/frozen/baseline_manifest.json)规范摘要 `1bb7df741c80d1271ab92408e0277d129c0b866011b218b79a8295bc38ad49b2`；仅安全读取tar成员并核425个对象，全部对应manifest；未解包执行。原base为 `9bb586a6b8fac1983b7cea3ab399719f93dbbb29`；actual grader baseline census与actor baseline census字节相同。

[完整trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/queue_v26/results/gpu1003-dask7138-coder-a1/attempt/trajectory.jsonl)306行、443599 B、SHA `672cd15c527cfe5f931c1b88db5397e0017a82be816c6a48e7bd2aee731981b4`，与harness副本字节相同。全部成功写操作在内存按顺序重放，两个Edit的old_string各唯一，最终5个FP entry全部字节匹配：

| tool／success行 | 操作 | 路径与结果 |
| --- | --- | --- |
| 84／88 | Write | `test_ravel_issue.py`，公开错误复现脚本 |
| 106／110 | Edit | `routines.py`，唯一生产改动，改名并加asanyarray |
| 132／136 | Write | `comprehensive_ravel_test.py`，6类输入及Dask样例 |
| 206／210 | Edit | `test_routines.py`，新增公开断言节点 |
| 271／275 | Write | `final_verification.py`，原题面list例子 |

最终生产entry SHA `b75b57d049fa0f00ac30ffc30293333043880798ad0fa8030e06ce31bce79cea`；其L1197–1198为 `def ravel(array_like): return asanyarray(array_like).reshape((-1,))`。基线已导入asanyarray（routines.py L29）；core.py L4058–4095支持array-like转换，L4085–4086对既有Dask Array直接返回，位置调用能保留原reshape路径。

原FP有5 entry，包括公开test文件修改；[评分projection](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/queue_v26/results/gpu1003-dask7138-coder-a1/grading/projection.json)明确只纳入4 entry，排除 `dask/array/tests/test_routines.py`。不要拿5项审阅diff当评分补丁，也不要把正式report的test_files_modified=false误读为模型从未改公开测试。cleaned applied-entry摘要 `538d9c68eba274359da2b13d779be4ca1874afc24d3ca368fe21648a3a3e39ef` 绑定4项投影；正式测试由trusted restore/apply提供。

## F1：保留array关键字兼容（P1，静态确认）

原公开签名是 `ravel(array)`；最终只有 `array_like` 参数，没有array别名或 `**kwargs`。基线 `dask/utils.py:685–695` 的derived_from只附docstring再返回原method，没有参数重映射。因此对正式 `test_ravel_keyword_array` 中的 `da.ravel(array=da.from_array(values, chunks=(1,3)))`，Python参数绑定会在转换体运行前报TypeError。这是由最终FP和既有签名确认的新兼容回归，直接违反当前已批准P2P；**本轮没有运行这条反例，也没有把预测写成实际raw0。**

第106／110行的rename同时引入转换与回归；不能因它与source gold相似而判正确，亦不因与gold不同判错。未来最窄修法是保留array参数名再调用asanyarray(array)，但任何修复须新候选，不能替换或“顺手修正”本原FP。此P1阻止本候选完整正确的结论，不阻止按已授权取得同原FP正式运行结果。

## 自测与最终说明

| trajectory行 | 实际证据 |
| --- | --- |
| 93／97 | 修前list确有AttributeError，脚本捕获打印；Dask Array位置调用正常。不能由脚本exit0否认复现失败。 |
| 119／123 | 修后原list和Dask Array值匹配。 |
| 141／145 | list、tuple、NumPy一维/二维、嵌套list、标量及Dask二维例子匹配；该脚本打印比较/捕获异常，不是所有分支断言强制。 |
| 219／223、232／236、245／249 | 新增公开array-like、既有ravel、1D-no-op各1 passed。 |
| 258／262 | public文件collected561，`-k ravel`选11 passed、550 deselected；包含前述三个节点，不能相加冒称14个独立节点。没有array=或完整470参考。 |
| 280／284 | 最终原题面list得到[0 0]。 |
| 302／306 | 最终称所有既有测试通过、full backward compatibility、NumPy API exactly。 |

**F2（P2）：最终说明超出验证，且与F1矛盾。** 位置调用和示例成功是真实证据；“所有既有测试通过”不能由11项筛选运行推出，“完整向后兼容”被静态array=回归否定，“NumPy API exactly”也非这组探针所验。未发现伪造结果或推断欺骗动机，问题是证据范围与最终声明不一致。

## 实际执行、准备失败与两层清理

[attempt](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/queue_v26/results/gpu1003-dask7138-coder-a1/attempt/attempt.json)记录CC2.1.205、UID54321实际actor、testbed激活及prefix拒写，actor image实际为 `fdd298b61309ae2df4cb9f528351526b7b3817c42fc34f47f98152a92a520881`。正式grader实际625b镜像由本job资源container ID及[image readback merge](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/q26_binder_image_readback_merge_v1/actual_image_readback.json)绑定：`625b404c6c1c40da31df4edfea6052a10fbd30b7fb49d58072b6ee2b215fab13`，源manifest `91df52cb66bb64003ecf4721832eae373c701536aa3dcb85ddc7d9e0ea757736`。这是pytest7.4.4固定诊断派生镜像，不是typed正式训练actor。

模型自然completed，harness RC0、25轮、24工具调用（13 Bash/6 Read/3 Write/2 Edit）、solve48.03s，CC duration44.374s，无工具错误、无预算耗尽。预算wall10800/turn240/context196608/output65536；实际25个generation请求均max_tokens65536、model_sent `Qwen3-Coder-30B-A3B-Instruct`，alias为slime-actor，总输出3642。CC modelUsage显示maxOutputTokens32000只作客户端元数据保留，不代替实际HTTP65536。当前服务capture有配置/HTTP/model mount匹配，但gateway audit的checkpoint_identity_verified=false、未重新hash全部权重/GPU权重attestation=false仍保留。

[原正式report](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/queue_v26/results/gpu1003-dask7138-coder-a1/grading/report.json) SHA `f94224785111770ceade4a28548dbf4ec0fe7eb79163112e75faf2a23c6c44b2`：`failed_to_grade/infra_failure/reward=null`，detail=`grading_control_surface_protect_timeout_after_300s`；whole3600/setup300/apply120/test1800。[eval log](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/queue_v26/results/gpu1003-dask7138-coder-a1/grading/eval_logs/evallog_gpu1003-dask7138-coder-a_0dad7b25.eval.log) SHA `400d215b74b0275f8d13e0899d43685e7a7376e170ec010c869071c0a6ed50bb`、405行，L393–405证明受信测试restore/apply及attestation通过，此后在protect阶段超时；没有install/test起止或结果。diagnostics candidate/control_surface/runner_integrity_changed均null、revision not_evaluated，470项result均None。没有评分候选UID54322的实际exec/id-u捕获，因为该阶段尚未启动；不借配置替代实际UID。entry RC3、queue attention对应基础设施收口，不对应模型解题失败。

两层清理都完成：actor pre-drain residual0、gateway revoked/drained/active0，quiescence进程为0且workspace双读稳定；container、relay、network清理无残留。grader manager created1/removed1、open/supply/cleanup_failures空，cleanup_ok true；[终态快照](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/gpu1003-dask7138-coder-a1_terminal_snapshot_v1.json)记录本job RC3、已结束。28条[封闭资源样本](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7138-coder-a1/gpu1003-dask7138-coder-a1_closed_resource_v1.jsonl)按本container/time匹配actor fdd298与grader625b，记录范围内PID quota/OOM/kill事件0，末样本自有container空；gaps_unknown=true，离散观测不推断连续全程或整机资源清空。

投影未触正式测试或禁区，trusted测试应用成功，候选未触conftest/fixture，未发现评分绕过或正式测试污染证据；保护/runner终局检查因pretest超时未完整完成，不把null改成false。

## 同FP恢复与停止条件

已核原FP、baseline、4项投影、470参考、材料、派生镜像和原现场，未发现当前封包中阻止只改setup900重评分的静态输入/运输阻断。新增CPUworker、CPU实际容器、安装/test、完整参考和清理尚不在本封包，**不预写恢复通过或正式分**；后续必须维持原FP规范摘要451557…、baseline1bb7…、same projection/materials/profile/recipe，只改setup900，并另存实际验收。F1预计会在keyword P2P暴露，仍应以实际完整评分收口。

本报告到此封存：单Coder样本、另一模型臂未知、原题面有引导、typed训练actor未接入；raw reward、qualification、training qualification均为None。已有matrix不重审，不改变候选或评分材料；本报告只新增派生reviews文件，原508清单、receipt和所有原件不变。逐字段及SHA见[同名JSON报告](non_author_7138_coder_a1_candidate_review_20261003.json)。任何后续CPU结果另存，不回写本报告。
