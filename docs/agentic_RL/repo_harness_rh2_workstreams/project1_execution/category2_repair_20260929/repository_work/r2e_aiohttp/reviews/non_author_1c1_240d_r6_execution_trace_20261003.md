# 1c1／240d R6 CPU：非作者执行追踪复核

2026-10-03（Asia/Singapore）。角色：Production Tracer。结论：**本切片未发现实质阻断；R6 的两题材料绑定、13 行评分结果和240d最终题面交付证据，足以继续已安排的探索性 GPU 验证。** 这是当前实际调用及原件复核，不授予训练／留出资格，不证明模型能力。最终 GPU 仍需按既有流程核对模型首请求中的当前题面与中性 brief；本报告没有新增审批或重跑要求。

## 审查范围与独立性

先重新计算固定请求 SHA，再读取其引用。[固定请求](../review_handoff_1c1_240d_r6_cpu_20261003.json) 的 SHA256 为 `dc7c0ac318fc1020ff0fdebb8e4b4b14aaba3ac5460ab6c9257563ca63ee50cb`；[R6 manifest](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_080_087_swe8_git_candidate_v1/manifest.json) 为 `ab0a3a13fd65e0ea4cd60541ea3b37b01196170477e25832df246f33ea208828`，release 为 `cat2-cpu-r2e080087-swe8-git-20261003-v1`。

输入已包含私有候选与作者结果，因此本轮是**非作者、非 fresh、非盲审**，不能记成新的公开读者审查。遵循 review-standards §10.4 的真实路径追踪与 §10.5 的有界停止条件；不重审相同 SHA 的共同 Git／wrapper／brief 机制。这里只核1c1的080/081、240d的082/083/084、原登记六方／七方结果及指定公开证据。共享 receipt 内6183的文件只核字节与长度，未给6183题级通过结论，4075也不在本轮范围。

只做本地文本、JSON／SHA256、标准库解析，按 `PYTHONDONTWRITEBYTECODE=1 python -B` 执行。没有 SSH、Docker、安装、模型、pytest、矩阵重跑或生产文件修改。仅新增本报告及 ignored 机器目录。机器检查提取固定 parser 的三段纯函数 AST；原补丁只在内存中应用，不写公开工作树或固定 release。

## 原件绑定与实际调用

固定请求以及其固定 JSON 中的152个唯一带摘要引用均吻合；R6 manifest登记的855个文件逐项 SHA／长度吻合。四份 receipt 的38、99、80、148个登记文件均吻合，共365个登记条目；其中R5的99文件为两题共享，未重复计数。receipt 总数包含非本轮题目，仅表示字节完整，不能用作本轮题级完成数。完整核对与重现脚本见 [机器摘要](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/non_author_r6_execution_20261003/summary.json)、[只读检查脚本](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/non_author_r6_execution_20261003/check_originals.py)。

实际链路由 [固定 controller](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/run_r6_acceptance_v1.py) 和 [job 原始输出](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/job/stdout.log) 绑定：controller先执行R6 release verifier，再顺序执行公开题面交付，最后逐题逐候选调用R6 release中的 `rh2/scripts/replay_grade.py run`。prepared／private来源为本轮准备目录，overlay为 `overlays_for_r6.jsonl`，不是R5旧prepared。[job status](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/job/status.json) 记录18:42:35Z开始、18:56:44Z完成、rc=0；[release verifier 输出](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/verify_release.stdout.log) 记录855成员检查。原 `matrix_summary.json` 的 `full_log_readback_pending`／`non_author_review_pending` 是作者当时快照，本报告不回写它。

矩阵路径为 `ReplayGrader.replay_one` → fresh候选容器 → materialize/sanitize/trusted-init → baseline census → agent UID54321应用原patch（noop为空）→ FrozenPatch/projection → 候选容器有界清理 → `SWEGradingManager.grade(workspace=None, frozen_delta=…)` → fresh grader UID54322 → 重建baseline／应用冻结内容／可信hidden setup → 测试段 →固定parser。对应R6源码为 [replay driver](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_080_087_swe8_git_candidate_v1/repo/rh2/src/repoharness2/adapters/slime/replay_grade.py)、[grader manager](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_080_087_swe8_git_candidate_v1/repo/rh2/src/repoharness2/grading/manager.py)。这用于指认本次真实消费者，不是重审共同机制。

controller的矩阵循环无并行分派，一次只调用一个候选；driver在评分开始前已完成候选容器清理，因此这条路径的候选与grader容器不同时存活。prepared job在18:38:32Z结束；240d交付在18:44:07Z结束；首个1c1矩阵账本在18:44:09Z开始。这里不推断宿主机其它批次的并发。

## 当前材料与镜像

[prepared manifest](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/revised_prepare_r6_v1/final_artifacts/prepared/prepared_manifest.json)、[私有 grading view](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/revised_prepare_r6_v1/final_artifacts/private/host_grading_views.jsonl) 和 [overlay](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/revised_prepare_r6_v1/final_artifacts/overlays_for_r6.jsonl) 的原件摘要与R6结果引用一致。独立重算hidden树（按文件名排序的SHA列表）、expected正文与entry正文，且context中的 `test_1.py` 字节与R6 registry的080/083修订文件一致。

| 题目 | 消费的修订 | hidden树SHA256 | expected正文SHA256 | base commit |
| --- | --- | --- | --- | --- |
| 1c1 | hidden080 / expected081 | `bf037fbf28cfea4af689b46ee1df2d28f342f51012935c55fe5e8033dc31f151` | `1bc0a6c74ee6fceb75b695d4d269c90f752deccf60b842db647a3602e1499370` | `87342c791dfd4c916877ba3dffafb9345bb0491f` |
| 240d | statement082 / hidden083 / expected084 | `e66b0f13ef2b275c3f1bfe68ff377765bad12bfeebb9443c19206329833ff704` | `8dab59950c1837a195f854e669fc3778200025beaf29431864e58a2ebe3a3c70` | `ef756ce29cc40a9b69e5e794eda722e252a62b4d` |

共同entry SHA256为 `8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf`。13份原日志各自记录相应 `RH2_SETUP_HIDDEN_TESTS_TREE` 和 `RH2_SETUP_ENTRY_SHA256`；setup成功、参考文件缺席为0、无不规则文件。不是仅凭prepared宣称实际安装了新材料。

实际1c1镜像ID为 `b25d4c9a986bc3e8349b453b1b859dd2e90d75f3306bf5945992f52fbe77f48b`，recipe SHA256为 `81f9e79996dfa5b11e766230fb4ddfbc46f65037013ed260b7964409d1fc3479`；240d镜像ID为 `8ab5550544d266c8b0b3e421b39af3362ca29c64a919d3ca0454aec79edceb08`，recipe为 `a48f5949054ddba8fa51e61ba7020927bba44cb8f9d1672bd1a9a7964004c392`。分别与build facts、overlay、矩阵ledger以及Frozen／baseline身份一致。build facts见 [1c1 facts](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/revised_prepare_r6_v1/final_artifacts/derived/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/facts.json)、[240d facts](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/revised_prepare_r6_v1/final_artifacts/derived/aiohttp__240da100151933883d7dea0528d45877df025b92/facts.json)。已有root/agent/grader访问探针记录hidden不可由54321／54322读取，root tree与entry摘要一致。prepare的2CPU／4GiB容器参数不构成Docker daemon构建阶段也受该限额的证明。

## 13行完整日志与冻结输入

每行重新解析Start/End之间的原日志，使用R6固定 `r2e_prime_pytest_v1` 的 `parse_log_pytest`／`normalize_status_map`，并按期望键与观测键的精确相等关系计算reward。13/13日志各有一个有序Start/End测试段；每行键集合精确等于58或33键，段外解析数为0，参考缺席为0，无skip／xfail／收集错误。测试段正常结束，`RH2_TEST_RC` 与ledger一致（有效对照为0，行为负对照为1）；外层exec rc=0表示测试脚本正常返回，不表示负对照测试全绿。

| 题目／候选 | 相同状态键／全部键 | reward | 不符位置 | 完整原日志 |
| --- | --- | --- | --- | --- |
| 1c1 / gold | 58/58 | 1 | 无 | [24771 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/gold/eval_logs/evallog_replay-aio-r6-1c1c0ea3_g_f8bbe436.eval.log) |
| 1c1 / noop | 56/58 | 0 | startup 两键 | [28635 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/noop/eval_logs/evallog_replay-aio-r6-1c1c0ea3_n_8894ccf4.eval.log) |
| 1c1 / F1 | 57/58 | 0 | server-start failure | [26179 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/F1/eval_logs/evallog_replay-aio-r6-1c1c0ea3_F_296e32b2.eval.log) |
| 1c1 / C5 | 51/58 | 0 | shutdown 七键 | [75150 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/C5/eval_logs/evallog_replay-aio-r6-1c1c0ea3_C_ea883763.eval.log) |
| 1c1 / C1 | 58/58 | 1 | 无 | [24771 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/C1/eval_logs/evallog_replay-aio-r6-1c1c0ea3_C_3dfa9596.eval.log) |
| 1c1 / C3 | 57/58 | 0 | cleanup 错误可观察性 | [26698 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/C3/eval_logs/evallog_replay-aio-r6-1c1c0ea3_C_f11034a4.eval.log) |
| 240d / gold | 33/33 | 1 | 无 | [4125 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__240da100151933883d7dea0528d45877df025b92/gold/eval_logs/evallog_replay-aio-r6-240da100_g_da1674d1.eval.log) |
| 240d / noop | 31/33 | 0 | 原端口 + 非示例端口 | [6841 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__240da100151933883d7dea0528d45877df025b92/noop/eval_logs/evallog_replay-aio-r6-240da100_n_244834f5.eval.log) |
| 240d / DG1 | 32/33 | 0 | 非示例端口 | [5640 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__240da100151933883d7dea0528d45877df025b92/DG1/eval_logs/evallog_replay-aio-r6-240da100_D_3d64c95f.eval.log) |
| 240d / WR1 | 32/33 | 0 | CONNECT 端口重复 | [5947 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__240da100151933883d7dea0528d45877df025b92/WR1/eval_logs/evallog_replay-aio-r6-240da100_W_a9fe5402.eval.log) |
| 240d / WR2 | 32/33 | 0 | CONNECT 端口重复 | [5971 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__240da100151933883d7dea0528d45877df025b92/WR2/eval_logs/evallog_replay-aio-r6-240da100_W_26328b8e.eval.log) |
| 240d / AL1 | 33/33 | 1 | 无 | [4125 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__240da100151933883d7dea0528d45877df025b92/AL1/eval_logs/evallog_replay-aio-r6-240da100_A_2c5c25ad.eval.log) |
| 240d / SC1 | 33/33 | 1 | 无 | [4125 bytes](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/matrix_artifacts_v1/matrices/aiohttp__240da100151933883d7dea0528d45877df025b92/SC1/eval_logs/evallog_replay-aio-r6-240da100_S_418e4e56.eval.log) |

这里是**5个正对照通过、8个负对照拒绝**，不是13个候选全部修复。完整日志为4125–75150 bytes，无partial标记；所有失败键及逐键观测存于机器摘要。1c1测试段耗时18.075–34.740s，240d为1.381–1.669s，均含测试结束时间，未把失败行归因成超时。

11份非空原patch与落盘 `candidate.patch` SHA逐一一致，且匹配ledger的 `candidate.patch_sha256`。进一步把每份原patch在内存中应用到公开base文件：先确认公开文件SHA等于该行baseline entry，再确认所得完整字节等于Frozen entry的base64解码字节。冻结正文的content SHA、canonical Frozen SHA、projection SHA引用及baseline canonical SHA均独立重算；task、public bundle、runtime image、materialized HEAD、baseline base commit全部对应。每题所有候选使用同一baseline canonical身份。noop两行没有补丁文件、Frozen entries和projection paths均为空；非空行仅投影其实际源码文件。13行 `excluded_pathset_changed=false`，无测试／fixture候选投影。

1c1：旧57键逐键保留，只加入 `test_run_app_cleanup_error_is_observable_after_interrupt[pyloop]` 的PASSED期望。C3原57键全部满足，新键唯一失败；其完整异常区实录 `cleanup_reached=[True]`、`raised=''`、`reported=False`、`reports=[]`，失败为“cleanup exception was silently lost”，说明走到cleanup但异常既不传播也不报告。证据为表中C3日志91–134行。noop／F1分别仍在旧startup报告断言失败；C5在七个shutdown行为上出现CancelledError／websocket断言，未伪装成环境故障。C1的58/58结果表明新键没有拒绝该登记有效路线。

240d：相对R5 prepared，恰好删除 `HttpClientConnectorTests.test_tcp_connector` 与 `.test_unix_connector` 两个原FAILED期望键；保留其余33旧键，未把FAILED改成PASSED、未新增skip。新hidden字节等于已审083版本。noop缺显式1234和8080端口；DG1仅非示例8080端口失败；WR1／WR2实录 `www.python.org:8443:8443` 与单一8443预期不符；gold／AL1／SC1均33/33。范围只证明当前33键政策的判别结果，不证明被移除TCP／Unix目标已修复。

## Profile、runner与生命周期

13行ledger均使用正式grader profile：UID54322、2CPU、4GiB memory、PIDs512、deny_all、tmpfs1GiB、shm64MiB；profile digest均为 `3ec1bfa87ff800d5d2c5e53e874603f6850b64e1392baa167968b9ec31a50a94`。R6 CLI显式给manager传入grader profile；manager在任何评分前调用真实inspect与候选UID探针，不合格会抛 `SandboxProfileViolation`。当前评分正常越过该检查，是按固定源码调用路径推得profile生效的证据；本轮没有在线重查daemon。逐行原ledger／diagnostics未保存完整prelaunch inspect正文，`resource_facts`仍为null，因此不把它写成额外实测资源快照。

各题runner前后摘要一致且 `runner_integrity_changed=false`。每行ledger的 `cleanup.removed=true`、`rm:ok` 明确指**候选阶段容器**，driver在评分前已收口；grader生命周期由manager独立close以及各行非空grader_cleanup阶段时长支持。[完成后的本批残留回读](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/own_matrix_residue_readback_v1.json) 在19:01:56Z记录 `rh2.run_id` 以 `aio-r6-` 开头的containers/networks均为空。这里只证明已记录时点、本批label范围的结束状态，不宣称宿主机全局无残留。

13行通用账本的 `grading_materials_identity`／`derived_image_recipe` 仍为null。本轮用registry → prepared私有view → context／build facts → overlay实际image／recipe → 原日志hidden／entry补充核对材料身份，不声称空字段已修复。该缺省字段在本切片原件绑定可复证的条件下不构成新增阻断；不能把该方法扩大为未来任意缺失材料身份都可接受。

## 240d最终题面及R5公开开发复用

240d的 [真实首请求](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/delivery_artifacts_v1/delivery240d/stub/requests/messages_000.json) SHA256为 `f18efca6c6c05f108567f27aa77b4abec8915df0a1ce28189db800f30264add1`。从R6 prepared public解码的完整题面SHA256为 `d3ff12a9a27890831dcedc62d53e8c124647d6fe036c28712505ed247d7a272c`，逐字节完整出现在首请求的user message中；与082 registry、prepared、public bundle一致。[真实CC attempt](../../../../../../../../runs/category2_repair_20260929/r2e_aiohttp/cpu-b/r6_acceptance_v1/delivery_artifacts_v1/delivery240d/attempt/attempt.json) 记录CC `2.1.205`、R6 snapshot、新240d image、54321解释器环境，harness正常结束、0 tool error，pre-drain-stop residual=0、gateway revoked/drained且active_requests=0、容器／network／relay清理为空残留。attempt／scenario误写r084标签，实际题面身份为082；保留原标签，不需要为名称重跑。

**CPU上游为 `stub_script`，该交付指定 `--no-grade`，Frozen entries=0，中性brief实际送达=false。** 它证明真实CC收到最终题面并正常结束，不能记作模型求解、真实模型预算、非空求解产物直评或brief送达证明。11行非空矩阵确实进入FrozenDelta评分，但属于原patch重放并重新冻结；也不能据此宣称本次空求解导出证明了非空直接评分接口。

相同SHA的 [brief既有审查](non_author_public_briefs_review_20261003.md)、[wrapper既有审查](non_author_public_actor_wrapper_review_20261003.md) 和240d公开读题原结论仅按其既有范围复用。两题R5公开开发原件再次核对base/gold的身份、完整captures和正常清理：Python3.9.21、UID/GID54321、`/testbed/.venv/bin/python`、源码均从 `/testbed/aiohttp` 导入。1c1的startup异常两方均传播，相关asyncio日志数base=1、gold=0，公开run_app55项两方均通过；240d路径base丢1234且assert rc1，gold保留1234且rc0，公开proxy13项两方均通过（43 warnings）。不能仅凭1c1症状命令rc0核销重复日志，也不能用公开55／13项通过替代新58／33键评分。R5使用旧prepared／旧hidden镜像；它支撑不变公开开发路径，R6新材料实际消费由上文独立证据支持。

## 实质阻断、残余范围与停止条件

本角色在当前 `production_observed` 的CPU重放／交付路径中**没有发现应阻止本切片继续的P0/P1**。未发现新材料错绑、候选替换、缺键／多键、提前结束、runner改变或本批残留证据。对缺省metadata、未落盘完整inspect以及r084标签误名，保留上述适用边界；没有要求补跑13行或修复相同SHA共同机制。

已足以进入下一切片：两题正式修订／prepared／新hidden镜像对应；13行CPU判别结果可由原日志独立恢复；240d最终082题面在真实CC首请求完整可见。建议继续现有统一探索性GPU流程，真实模型首请求核当前题面及中性brief实际送达，并保持新image／prepared／grading材料身份对应。1c1题面SHA未变，本轮不追加一次无变化CPU交付。

仍未覆盖：实际GPU模型求解／reward表现、模型非空输出的直接评分共用验收、brief在真实模型请求中的实际交付、正式miles训练消费、全仓TCP／Unix兼容、训练／留出资格与同仓划分实施；6183／4075题级结果及整机生命周期也不在本轮结论内。仍沿原owner／既有gate推进，不新增发布者终审或审批。

本轮停止条件已满足：每条登记矩阵一次原件追踪／精确parser重算／冻结身份核对，240d交付一次首请求与生命周期核对，以及指定R5公开证据按原范围复用。除非当前gate出现新的实际错绑、真实路径回归或契约／安全边界证据，不扩展候选、不重跑、不主动继续下一轮。
