# 1c1：新增取消清理P2P已完成CPU与非作者核收

2026-10-03。任务 `aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52`，持续题主为 `R2E | aiohttp 题目修订`。R22的094/095已替换080/081；题面、runner、原58键和两种合理清理错误上报方式不变。只新增一个保留公开取消传播及资源收尾的P2P。

| 原候选／对照 | 新版实际匹配 | 新P2P | 本批诊断reward |
| --- | --- | --- | --- |
| 原baseline | 57/59 | PASSED | 0 |
| gold／C1 | 各59/59 | PASSED | 各1 |
| 完整原Coder7条 | 58/59 | FAILED | 0 |
| 完整原Qwen2条 | 59/59 | PASSED | 1 |

五行59精确键已实际评分，旧58状态在各自原结果上逐项不变。基线保留原两个F2P失败；Coder只在新增取消清理键失败。其observer前快照为worker未done、asyncgen和loop未闭、pending1；其余四行finally完成、loop闭、pending0。完整候选包含coverage/helper，原Frozen entries的字节／模式均未改，projection无裁剪。

[当前修订入口](revision_1c1_cancelled_main_p2p_20261003/README.md)、[实际逐键原件](revision_1c1_cancelled_main_p2p_20261003/results_five_rows_20261003_v2.json)、[题主范围核收](revision_1c1_cancelled_main_p2p_20261003/assessment_five_rows_20261003.md)、[最终非作者核收](revision_1c1_cancelled_main_p2p_20261003/review_acceptance_five_rows_20261003.json)。同一批材料Falsifier与执行ProductionTracer均完成并停止；本批无已知待跑／待归档CPU作业，cpu-a归属标签残留0，原cpu-b已销毁。资源依据见[最新依赖](resource_dependencies_20261003.json)。

本批是**同一原候选在新材料上的CPU诊断**，不增加模型样本，不改原两份首轮raw1/58。新baseline/Frozen外层身份随新评分镜像与physical attempt变化；相同的是原文件entries，不能冒称整体摘要相同。旧binding继续禁用，新grading bundle消费已核收，但未来GPU仍须生成相应新binding；当前没有新GPU请求，普通重复仍按统一队列暂停策略。null元数据、未留独立cgroup/prelaunch原件、未触发timeout及原actor两个false marker如实保留，不授整体runtime、稳定能力或训练／留出资格。

此前[公开取消归因](followup_1c1_cancelled_main_20261003/results_public_cancelled_main_20261003.json)及[非作者核收](followup_1c1_cancelled_main_20261003/review_acceptance_public_cancelled_main_20261003.json)证明完整Coder在已取消main上读取 `exception()`，使后续收尾被跳过。该输入使用原00ad演员镜像、实际CC桩、公开run_app(coroutine)及完整原三侧文件，归因已结束不重跑。新P2P来自该已证实遗漏；仅覆盖这一个公开启动自取消场景，不代表触发频率或全部取消路线。

原[首轮行为](1c1_trajectory_analysis_20261003.md)、[首轮收口](closure1c1_20261003.json)与[首轮核收](review_acceptance1c1_240d_gpu_first_round_20261003.json)保留补证前时点事实，不能再把已证实回归称为纯理论风险。4075／240d／6183不受本题缺陷影响。

## 原58键CPU材料验收与首轮历史依据

正式隐藏080／expected081只增加“中断后实际进入 cleanup，且新错误向调用者或 loop 异常处理器可见”的一个断言，57→58键；其余旧键与 runner 保留，题面不变。下列为已完成CPU材料验收依据。

第六版 `cat2-cpu-r2e080087-swe8-git-20261003-v1` 的匹配镜像已实际执行六方矩阵，完整58键均被解析，未缺键、增键或提前结束。按原日志重算：

| 候选 | PASSED／全部键 | reward | 结果含义 |
| --- | --- | --- | --- |
| gold | 58／58 | 1 | cleanup 新错误向调用者传播 |
| C1 | 58／58 | 1 | cleanup 新错误经 loop 报告 |
| noop | 56／58 | 0 | startup RuntimeError 与 server-start OSError 重复报告 |
| F1 | 57／58 | 0 | OSError 仍重复报告 |
| C5 | 51／58 | 0 | 破坏 shutdown 等待／取消顺序 |
| C3 | 57／58 | 0 | 实际进入 cleanup，却吞掉新异常，新键唯一失败 |

这关闭了 C3 在旧57键下得1的已知漏判，同时接受两种合理的错误可观察路线。完整原件与冻结身份见[六方结果](results1c1_r6_matrix_20261003.json)，[CPU 核收裁决](cpu_result_acceptance_r6_20261003.json)汇合两份独立报告与题主重算依据；候选／grader 清理完成，本批标签的容器和网络残留为空。ledger 的材料／recipe空字段由实际 registry→prepared→context／build／overlay→原日志摘要补证，并未宣称这些空字段已修复。

公开开发证据按原范围复用：[base／gold](results1c1_public_development_20261003.json)均抛题面 RuntimeError，base 多1条 asyncio shutdown日志，gold为0；双方公开 run_app 各55 passed。该作业使用旧评分镜像，只证明公开开发路径，不替代上述新58键。题面未变，不重复 fresh 阅读；[中性 brief](public/1c1_development_brief.md)已独立核查，两模型首轮真实prompt均核送达。

已结束固定请求 `aiohttp1c1-r080081-probe-wide-v1-20261003`，两模型各一次、统一probe-wide-v1。固定[请求](requests/1c1/probe_request.json) SHA256为 `c5a01f0302705c3179581137662f77b725c22f3fa7d7304dc98a35d0eb5718cf`；[最初交接](probe_submission1c1_20261003.json)保留，[原回执读回](aggregate_receipt_readback1c1_20261003.json)、[Qwen结果](results1c1_qwen36_a1_20261003.json)、[Coder结果](results1c1_coder_a1_20261003.json)为当前依据。该首轮闭合时点请求revision5已核收、题进度revision8，phase为result_analysis；当前新增归因进度以总账为准。

该58键遗漏现已由上述094/095新增P2P关闭；旧binding继续禁止复用，未来1c1重复须新binding。GPU统一将尚未开始的普通重复暂缓，先补新题与缺少另一模型首轮，本包不重复已有首轮。后续同条件重复仍须按统一门槛和队列安排。只在 `__cause__` 保留异常消息的未来包装实现可能误拒，当前无实际候选证据，保留条件性风险；真实候选出现时再窄核。当前结论不授予训练／留出资格，aiohttp仍按整仓划分。
