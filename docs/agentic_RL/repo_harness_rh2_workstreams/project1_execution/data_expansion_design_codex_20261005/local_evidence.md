# 本地数据扩量证据：Coder分流、池外规模与时间边界

整理日期：2026-10-05。只读核对本地材料，没有访问远端、运行容器或模型，也没有修改原材料、共享总账和历史结果。未读取另一份扩量方案。复算脚本为 [local_audit.py](local_audit.py)，逐题结果及原件路径为 [local_evidence.json](local_evidence.json)。

**优先复用现有52题的诊断与评分证据，再接旧6题和129题环境池；同来源池外扩量已有足够大的候选空间，无需先引入新来源。** 52题中的Coder结果可分为32题在已核目标范围内成功、18题有证据的候选失败、2题诊断或材料限制单列。这个分流用于安排后续工作，不是52题训练准入名单，也不是可泛化的模型正确率。

## 52题：历史尝试、补评分、候选语义分别记录

直接读取 [52题产物索引](../category2_repair_20260929/experiment_artifact_index_20261004.json) 指向的106份attempt和105份原始report，106份attempt及索引中对应report的SHA全部相符。DVC9395的Coder原轮次未进入grader，所以没有原始report。52道题包含34 SWE＋18 R2E，所有题有且仅有一个Coder求解；Qwen有54次历史求解，额外两次属于Moto6114和Coverage ea69的旧材料。后续CPU补评分不新增模型样本。

| 口径 | Coder | Qwen3.6对照 | 含义 |
| --- | ---: | ---: | --- |
| 原始求解尝试 | 52 | 54 | 106次历史attempt，不是106道题。 |
| 原始report的1 / 0 / null | 33 / 12 / 7 | 45 / 9 / 0 | 保留每次原材料和原结果。 |
| 每题最新有证据的范围内成功 | 32 | 40 | 成功范围有明确限制；不代表所有API正确或稳定成功。 |
| 每题有证据的候选失败 | 18 | 10 | Coder中16题有原始或补评0，另2题仍为原null但候选破坏有直接证据。 |
| 诊断或材料限制单列 | 2 | 2 | Dask8801与Datalad6b6f；不能纳入完整成功或可直接训练分母。 |

三类按题互斥：Coder为32＋18＋2＝52，来源内分别为SWE 24＋9＋1、R2E 8＋9＋1。Qwen按每题最新求解关联最新补评，仍有跨求解环境、评分版本和范围差异；**不以40与32推断严格同条件胜率或显著优势。** 两模型都仅首轮求解过的题不能据单次0/1判为稳定困难或已饱和。

以下差异决定了不能直接统计raw reward：

| 题目 | 原Coder结果 | 最新有证据的结论 | 后续使用边界 |
| --- | --- | --- | --- |
| Dask7138、7305 | null | 同原FrozenPatch在CPU补评0：分别漏`array=`兼容、uint64重分区端点错误。 | 原infra事实保留，候选失败已可分析，不需重新求解来补分。 |
| Dask9378 | null | 同原FP在CPU补评1，用户选定的默认mask/有效值目标通过。 | `dtype`及可选参数缺陷保留；不能写成一般API兼容成功。 |
| Dask8801 | null | 同原FP行为评分1，但fresh23中4个诊断失败；Qwen也有4个诊断失败。 | v7仅诊断，行为分不等于完整目标成功；不要自动转成训练reward。 |
| DVC9395 | null，原入口RC1/cleanup false | 同原FP CPU补评0：F0/3、P37/37。 | 原relay清理故障不回写；已完成求解与补评分分开。 |
| aiohttp240d、6183 | null、参考测试未运行 | 模型`git checkout`撤回兼容预置，最终候选在actor与grader均SyntaxError；是有证据的候选失败。 | 原null不改成0，不把未执行的33/49键写成全失败；自动reward归因仍有契约资格边界。 |
| aiohttp1c1 | 原58键1 | 新取消清理P2P加入后，完整原Coder FP58/59，Qwen59/59。 | Coder转为候选失败；未来新求解需要新runtime binding。 |
| Coverage ea69 | R17/49键1 | R28/51键完整原Coder及Qwen FP均50/51、0。 | 旧R6/R17禁止新派发；新版actor/overlay资格未由CPU补评建立。 |
| Pydantic8511 | 旧173键0 | 原Coder的旧0保持；Qwen旧1在R27/177键补评0。 | 未找到Coder在新177键下完整FP补评分，机器表明确该成绩unknown。 |
| Datalad6b6f | 正常16/17、0 | 转义冒号路径回归有证，两个模型都失败。 | CPU/GPU baseline环境血缘null的formal gate未闭；此处单列，不把身份缺口当模型失败原因。 |

关键来源：[Dask当前汇总](../category2_repair_20260929/repository_work/swe_dask/preparation.md)、[DVC9395补评分](../category2_repair_20260929/repository_work/swe_dvc/tasks/iterative__dvc-9395/coder_a1_same_original_fp_cpu_grade_owner_readback_v1.md)、[aiohttp240d归因](../category2_repair_20260929/repository_work/r2e_aiohttp/240d_trajectory_analysis_20261003.md)、[aiohttp6183归因](../category2_repair_20260929/repository_work/r2e_aiohttp/6183_trajectory_analysis_20261003.md)、[aiohttp1c1五行](../category2_repair_20260929/repository_work/r2e_aiohttp/revision_1c1_cancelled_main_p2p_20261003/results_five_rows_20261003_v2.json)、[Coverage最终验收](../category2_repair_20260929/repository_work/r2e_coveragepy/tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/scoring51_final_acceptance_20261004_v1.json)、[Pydantic8511补评分](../category2_repair_20260929/repository_work/swe_pydantic/model_audits_20261003/8511_original_fp_v2_regrade_acceptance.md)、[当前源账](../category2_repair_20260929/repository_work_packages_20261002.json)。

其余Coder失败题为Conan15422、Moto6185、Pydantic8567、DVC4166、Pandas48106、Orange4014、Pillow2d01/3a61/a682、NumPy d805。完整52行JSON分别保存原始attempt/report、当前材料、最新题主说明、分流原因及证据路径。除上述窄核，本次复用已有题主和独立语义审查，**没有重新逐条审完106条完整轨迹**。

`training_admission=not_established_by_this_inventory`只表示那次盘点不建立准入，不证明历史上没有训练候选，也不证明没有训练过。例如旧 [NumPy a5ea题卡](../r2e_lifecycle_20260929/results/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764/probe_card.md)及[NumPy5e83题卡](../r2e_lifecycle_20260929/results/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb/probe_card.md)明确写“训练候选 yes”。本报告字段改用`not_established_by_this_audit`，历史用途标签、当前runtime绑定、训练实际运行事实必须分别查证。

## 本地元数据池：足以选题，不等于已经准备好

按完整ID重算，保留既有留出仓hydra、bokeh、tornado、pyramid；当前264题均不属于这四仓。与Verified仓库短名交集为空。来源为[SWE Full元数据](../../data_freeze/meta/swe_gym_full.jsonl)、[R2E元数据](../../data_freeze/meta/r2e_subset.jsonl)和[既有留出提案](../../data_freeze/heldout_proposal.md)。本报告沿用仓库排除边界，没有重新批准旧提案中的逐题筛选阈值或n=8采样计划。

| 来源 | 本地元数据行 | 留出仓行 | 排除留出后 | 当前池 | 池外候选 |
| --- | ---: | ---: | ---: | ---: | ---: |
| SWE-Gym Full | 2,438 | 92 | 2,346 | 216 | **2,130** |
| R2E-Gym Subset | 4,578 | 450 | 4,128 | 48 | **4,080** |

2,130＋4,080＝6,210只是两来源的候选行总数，未经跨来源任务去重，不能写成6,210个独立、就绪训练任务。SWE的2,438个instance_id全部唯一，但只有2,163个`repo×base_commit`组合；共享初态不代表任务相同，不能直接删掉相对重复的275条。SWE base与R2E fix commit按仓库短名机械相交34组，全部Pandas；两个字段语义不同，不能直接按此去重或证明环境相同。取到完整R2E行后应恢复真正parent/base，再按问题、补丁和测试重叠排查。

| SWE仓库 | 当前216之外 | 同当前216的仓库×版本组 |
| --- | ---: | ---: |
| Pandas | 732 | 626 |
| MONAI | 348 | 234 |
| Moto | 284 | 284 |
| mypy | 217 | 146 |
| DVC | 190 | 110 |
| Dask | 131 | 35 |
| Modin | 102 | 52 |
| Conan | 63 | 31 |
| Pydantic | 63 | 52 |
| 合计 | **2,130** | **1,570** |

当前216覆盖78个仓库×version组；仅当前52中的34个SWE覆盖26组，对应池外696题。JSON保留全部组及数量。这说明依赖配方和检查方法可按组复用，但version粒度较粗，不能跳过逐题base、依赖、目标测试和正负对照的差异核对，也不代表镜像层实际相同。

R2E池外分布为Pandas1,437、NumPy774、Pillow613、Orange475、aiohttp294、Scrapy210、DataLad174、Coverage103。轻元数据没有version，也没有实际baseline：`commit_hash`是修复commit，镜像tag存在不等于可拉取。已核的本地48行[完整R2E输入](../../../../../runs/env_overnight_20260916/M3/probe_data/r2e_candidates_full.jsonl)覆盖当前48题，池外为0；不能拿这份完整包证明池外4,080题的评分材料已落地。

SWE Full文件只有`instance_id/repo/base_commit/version`四字段；R2E轻文件只有`repo_name/docker_image/commit_hash/problem_statement`四字段。**本次没有核验池外完整题包、镜像存在性、离线恢复或当前部署状态。** 当前264题有环境/发布证据，与池外轻元数据是不同准备层次。

## 最有实证的扩量顺序

1. **先复用52题，按候选行为与当前材料分开使用。** 32次Coder成功适合保留作较易样本和覆盖锚点，不能因一次成功全删；18次失败适合错误类型与学习信号分析，不能因一次失败全判过难。Conan15422、Moto6185、Orange4014、Pillow3a61/a682已有Coder失败与Qwen成功，是成本较清楚的对照切片。Dask7138也有对照，但补评与公开提示边界需保留。只有明确需要判断重复稳定性或组内reward差异时，才选择少量固定材料重复；不要为凑每题三次或八次先全量重跑。
2. **先接旧17题中尚无模型记录的6题。** 这是NumPy5e83、a5ea、d89b，R2E Pandas32dd，Scrapy7545、9a15；均有正式固定命令开发检查和具体控制证据。优先绑定当前题卡、镜像和入口，不重做整个检查流水线。NumPy5e83须使用C-A正对照，原gold失败；Scrapy7545有60秒时序风险，需保留。它们全是R2E，不能把这6题的结果代表SWE扩量表现。
3. **对129道未找到模型记录的SWE环境池做分层首轮覆盖。** 来源是quality142减已有模型记录13，分布为Moto47、mypy27、DVC24、MONAI17、Pydantic8、Dask4、Modin2。已有环境正负对照与全池早期调查可复用；“未进入72题主复核”不等于“完全没调查”，也不等于质量已通过。建议先按仓库×版本与任务类型各取小量，用已有材料定点补质量/开发缺口，再按实测保留率扩。不要让可复用镜像多的仓库自然吞掉全部名额。
4. **以同来源池外、同仓库×版本为下一扩量层。** SWE的1,570条提供最明确的配方复用候选；先保证现有仓库覆盖和失败类型，再扩版本。R2E在既有8个非留出仓内取完整题包后筛选，不能先承诺4,080就绪。池外Pandas最多，应有意识抽样，而不是按文件顺序取题。
5. **51题已知问题池按价值定点续接，保留2题原材料隔离。** 不把51题全部作为扩量前置阻塞，也不因一个仓库有问题整仓弃用；有明确修复收益且材料缺口小的可并行接回。隔离针对Modin5940/6937原材料，不自动推成Modin全仓永久排除。

以上是扩量次序建议，不改变已批筛查标准、训练配方和当前所有权。准备/评分性能另由专门线程负责，本报告不新增该方向实现任务。

**不能整仓排除的实证例子：** Pandas48106两模型正常失败，50319两模型通过且确实编译交付；Dask原4个Coder null经补评分别有真失败、成功和诊断限定，不是“Dask都不能跑”；aiohttp两个Coder破坏兼容预置的题，Qwen在同基线保留兼容后通过，4075也有双成功。另一方面，基于成功样本选题也会偏易：52题经历了修订、提示和人工筛选，129题环境池按历史工作进度留下，旧6题又全是R2E。三者都不是全来源随机样本，不能把局部成功率外推全池。

R2E同仓跨题已有修复/测试出现在别题初态的机械线索，历史36/48计数不等于36个已证泄漏事故，但足以要求在拆训练/评测时保留仓库或时间隔离检查。此处沿用四个既有留出仓，不临时为了扩量消耗它们。

## 时间记录能支持的容量估计

下表直接取每题所选的Coder首轮原件，不混入CPU补评分。P90采用nearest-rank定义。Qwen每题最新一轮和全部106历史尝试的同口径统计保留在JSON，便于主线程复核。

| Coder区间 | 样本数 | 中位数 | P90 | 区间总和 |
| --- | ---: | ---: | ---: | ---: |
| `solve_seconds` | 52 | 63.8秒 | 215.5秒 | 1.37小时 |
| actor `finished_at-started_at` | 52 | 114.1秒 | 317.9秒 | 2.38小时 |
| 原grader `total_grading_seconds` | 51 | 208.0秒 | 387.6秒 | 3.15小时 |
| attempt开始至原graded_at | 51 | 324.1秒 | 628.0秒 | 5.42小时 |

这些时间支持“在该批已备环境、该入口和预算下，单次求解通常为分钟量级，评分/生命周期不能忽略”的判断，可作为新批次资源测量的基线；**不能据此承诺每天完成多少题或把模型求解时间当GPU占用时间。** 全106次原件的首开始至最后评分跨度为23.36小时；Coder区间总和5.42小时、两模型总和等数字都不是这个实际日历窗口。

限制如下：

- `solve_seconds`包含在actor生命周期内；grader子阶段属于grader总耗时，不能重复相加。直接取开始/结束时间优先于拼阶段。
- 多attempt可能重叠，派发、材料等待及人工分析又会产生间隔；`queue_wait=0`只表示grader自己的队列，不代表GPU作业无排队。
- 51份Coder原grader中包含准备超时和候选收集失败，且缺DVC9395未发生的原评分；CPU补评分是后续额外成本，不在表内。不能拿原失败的短评分时间预测新题完整评分。
- 本批原件不能确定冷镜像拉取、第一次依赖构建、新题质量处理、稳定并发、资源峰值与训练learner开销。时间字段的`prep_seconds`也不涵盖所有准备/控制面成本，不能据它接近零宣称准备已无成本。

因此当前适合给出分层小批及可测停止条件，不适合承诺确定总工期。下一批只需复用同口径记录实际完成题数、首轮有效评分数、有效候选失败数、端到端批次起止和新增CPU补评成本；不要用阶段时长累加代替墙钟，也不要把所有null混成“没学会”。

## 本次验证范围

脚本独立重算题目分母、原始attempt/report分数、逐题路线、元数据仓库与版本组、留出交集及原始时间区间；106份attempt与对应105份report核对索引SHA，无不符。关键补评/语义更正读取当前源账、作者验收和已有独立复核，原始/派生字段分开保存。没有新跑测试、容器或模型，没有全量重审候选源码，也没有核远端镜像与训练执行历史。涉及未核的当前资格、材料或运行事实均不由本报告补成肯定结论。
