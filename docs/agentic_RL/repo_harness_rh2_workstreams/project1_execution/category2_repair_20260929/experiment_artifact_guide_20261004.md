# 本次双模型探针实验产物说明

整理时间：2026-10-04 04:06（Asia/Singapore）。范围为本批52题的修订、CPU验收、双模型探针、分析与归档；旧17题另列，评分优化和外部调研作为配套产物。

**本批52题的双模型历史首轮已结束，轨迹、评分、题主分析、环境信息和已有性能记录均已落在本地。** 这里说明“保存了什么、去哪里找、验证到什么程度”，不把执行完成写成全部解对或训练准入。最新收尾采用信息与必要材料保存方式，已取消200多GB中间镜像的全量下载。

**按最新信息保存范围，根线程验收已通过，可由用户确认后关闭GPU。** 所需资料没有剩余GPU依赖，只有模型服务容器保留运行；本线程没有执行停机。见[最终本地保存验收](../../../../../runs/category2_repair_20260929/overnight_watch_20261003/gpu_local_preservation_gate_20261004/root_information_acceptance_20261004.json)。本轮定时巡检已结束，下面列出的本地派生分析及未来优化验证仍按各自范围保留。

## 先从哪里找

- 想看某一道题：打开[52题产物查找表](experiment_artifact_index_20261004.json)，搜索题目ID。每行关联负责人、当时进度、题主证据、两模型实际尝试、逐文件原件和请求/回执。
- 想理解题目做对没有、评分是否可信：先读下方对应仓库的分析，再沿其中证据回到原始评分；不要只看 reward。
- 想重新运行：先读[CPU恢复资料说明](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/cpu_inventory/recovery_information_20261004_v1/README.md)，核定要使用的材料版本，再看[实际环境索引](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/gpu_source/environment_information_index_52_v1.json)。这次没有重新做完整离线重建验收。
- 想分析为什么慢：从[性能原件清单](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/gpu_source/performance_preservation_local_file_index_v1.json)和[评分优化对照](../../../../../runs/grading_performance_20261003/comparison.json)进入。原始数据已齐，统一的逐题耗时、逐环境资源和整批瓶颈三个派生报表仍待本地整理，不需要继续占用GPU。

所有链接指向本地工作区；JSON中的仓库相对路径从仓库根目录解释。目录名中的 `remote/` 表示远端原件在本地的回收目录，不代表文件仍只在远端。

## 本次记录的范围

| 范围 | 实际记录 | 解释边界 |
| --- | --- | --- |
| 本批题目 | 52题、15个仓库：SWE-Gym Lite 34题，R2E 18题 | 这是本批题单，不是整个来源数据集。 |
| 两模型 | `Qwen/Qwen3-Coder-30B-A3B-Instruct` 与 `Qwen/Qwen3.6-35B-A3B` | 精确加载和预算以每次冻结配置为准。 |
| 历史首轮 | Coder 52次，Qwen3.6 54次，共106次历史尝试；52个题ID都具备两模型历史运行 | 多出的尝试、材料变更、原失败与补评分别保存。不能写成104次同条件有效样本，更不能把106当独立题数。 |
| 题主分析 | 根线程已记录52题普通首轮分析及已知必要补评收口 | 有正常模型失败、材料/环境不同及用途限制；不表示52题全部语义正确或适合训练。 |
| 另账旧17题 | GPU原始10次尝试、API历史4次尝试及CPU/准备材料另有索引 | API模型与日期不同，不能并入当前双模型统计；未运行或历史缺件仍如实保留。 |

覆盖依据：[首轮执行收口](../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/first52_execution_delivery_closeout_20261004_v1.json)、[题主收口观察](../../../../../runs/category2_repair_20260929/overnight_watch_20261003/user_remaining_status_20261004_0332/summary.json)与[本次固定总账快照](../../../../../runs/category2_repair_20260929/overnight_watch_20261003/artifact_documentation_20261004/repository_work_packages_snapshot.json)。旧的“继续a2/a3”等字段可能仍留在历史检查点；当前有效决定是普通重复暂缓，不据旧文字启动新采样。

## 产物位置与记录内容

| 产物 | 已记录的内容 | 本地入口 |
| --- | --- | --- |
| 题单与责任人 | 52题、来源、负责人线程、材料版本、阶段、请求和回执；保存了本次读取快照。 | [逐题总账](repository_work_packages_20261002.json)；[本次52题产物查找表](experiment_artifact_index_20261004.json) |
| 模型执行与首轮覆盖 | 两精确模型、历史尝试、执行结束、请求交付及当时剩余作业。 | [执行收口回执](../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/first52_execution_delivery_closeout_20261004_v1.json)；[GPU运行总账](../../../../../runs/ordinary_gpu_probe_20261002/orchestration.json) |
| 轨迹与候选补丁 | 原始交互、工具使用、求解日志、冻结候选 FrozenPatch、基线快照和结束原因；缺失原件也有记录。 | [原件逐文件清单](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/gpu_source/local_execution_evidence_body_manifest_v1.json)；[本地运行原件目录](../../../../../runs/ordinary_gpu_probe_20261002/remote) |
| 评分与失败恢复 | 原始 reward、测试/安装日志、评分诊断、基础设施失败和原补丁补评；恢复结果另存，不覆盖原失败。 | [历史恢复补充清单](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/gpu_source/historical_recovery_supplement_index_v1.json)；[各仓分析与核查目录](repository_work) |
| 逐题语义与行为分析 | 根因/修法、准确定位与纠错、工具使用、可判断的并行行为、验证质量、耗时与调用效率、剩余用途限制。 | [各仓题主记录](repository_work)；[52题进度与证据关联](experiment_artifact_index_20261004.json) |
| 环境身份与实际版本 | 每题每次运行的 base commit、actor/grader 来源、镜像身份、系统与架构、环境事实、依赖版本及实际材料引用。 | [GPU实际环境信息](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/gpu_source/environment_information_index_52_v1.json) |
| 构建配方与必要材料 | 固定请求、Docker/安装配方、受信测试与评分脚本、依赖和必要本地资产；历史运行版、题主当前版和最新封包分开。 | [CPU恢复资料说明](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/cpu_inventory/recovery_information_20261004_v1/README.md)；[逐题恢复索引](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/cpu_inventory/recovery_information_20261004_v1/recovery_information_index_52_v1.json)；[完整材料行](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/cpu_inventory/recovery_information_20261004_v1/selected_task_material_rows_v1.json) |
| 冻结代码与材料身份 | 入口链、冻结代码快照、材料清单和实际哈希匹配；用于解释某次尝试真正消费了哪个版本。 | [冻结运行与材料索引](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/gpu_source/frozen_runtime_and_material_metadata_index_v1.json)；[104项记录哈希的本地定位](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/gpu_source/frozen_material_recorded_sha_resolution_v2.json) |
| 性能与资源原始观测 | 队列、派发、准备、切模型及服务日志；逐题计时、评分阶段、GPU/显存与标记容器资源采样、实际配置和存储拓扑。 | [性能本地文件清单](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/gpu_source/performance_preservation_local_file_index_v1.json)；[采集范围与已知缺测](../../../../../runs/category2_repair_20260929/overnight_watch_20261003/gpu_local_preservation_gate_20261004/performance_preservation_supplement_20261004/request.json) |
| 发布和CPU验证 | 封包、可信材料登记、分机部署、版本核对、正负对照与必要补评。 | [发布记录](publication_20261003.md)；[CPU部署账](cpu_release_deployments_20261003.json)；[实际发布/补评产物](../../../../../runs/category2_repair_20260929) |
| 评分性能改造 | 独立实现快照/补丁、测试与独立审查、CPU计时对照、Prime离线接线。不是本批模型的新采样。 | [性能改造说明](../grading_performance_20261003/README.md)；[当前检查点](../../../../../runs/grading_performance_20261003/checkpoint.json)；[v13交付包](../../../../../runs/grading_performance_20261003/deliveries/rollout_v13) |
| 外部模型与数据调查 | 确切模型续训证据、数据开放状态、难度/接入判断、来源版本和限制。 | [调研报告](../base_models_and_data_survey_20261003/research_report.md)；[结构化证据](../base_models_and_data_survey_20261003/evidence.json) |
| 协作、裁定与归档核验 | 三方分工、题级决定、提醒记录、范围变化、原件完整性与停止镜像传输回执。 | [协作规则](coordination_workflow_20261003.md)；[巡检与裁定](overnight_watch_20261003.md)；[根线程核验目录](../../../../../runs/category2_repair_20260929/overnight_watch_20261003/gpu_local_preservation_gate_20261004) |

`FrozenPatch` 是冻结后的候选补丁，用来复用同一份模型答案补评分；它与模型重新解题是两回事。恢复索引中的受信测试/评分材料只供内部验收和恢复使用，不应作为公开求解上下文。

## 按仓库查分析与独立核查

以下目录集中保存题主修订、分析、必要核查和各次交接。常见分析文件含 `probe_analysis`、`model_analysis`、`semantic_audit`、`trajectory_analysis`；`reviews/` 为独立审查入口。同目录旧材料保留，当前版本由逐题查找表中的检查点和固定请求指定。

| 来源 | 仓库记录目录 | 题数 | 题目简称 |
| --- | --- | --- | --- |
| SWE | [Conan](repository_work/swe_conan) | 6 | 11594、12397、13230、13403、14177、15422 |
| SWE | [Moto](repository_work/swe_moto) | 6 | 5406、5960、6114、6185、6408、7584 |
| SWE | [Pydantic](repository_work/swe_pydantic) | 6 | 5662、6283、8316、8511、8567、9066 |
| SWE | [Dask](repository_work/swe_dask) | 5 | 7138、7305、7656、8801、9378 |
| SWE | [DVC](repository_work/swe_dvc) | 4 | 4166、5839、6954、9395 |
| SWE | [MONAI](repository_work/swe_monai) | 3 | 2446、3715、6975 |
| SWE | [mypy](repository_work/swe_mypy) | 2 | 10174、15184 |
| SWE | [pandas](repository_work/swe_pandas) | 2 | 48106、50319 |
| R2E | [aiohttp](repository_work/r2e_aiohttp) | 4 | 1c1c0ea3、240da100、4075c653、61833518 |
| R2E | [coveragepy](repository_work/r2e_coveragepy) | 4 | 016af5f6、5dbbe143、ea6906b0、f5eb5f21 |
| R2E | [orange3](repository_work/r2e_orange3) | 4 | 22e98f8f、4014f248、50f6a758、9b5494e2 |
| R2E | [Pillow](repository_work/r2e_pillow) | 3 | 2d01f7d0、3a61c9e9、a682ceaf |
| R2E | [NumPy](repository_work/r2e_numpy) | 1 | d805e9b6 |
| R2E | [DataLad](repository_work/r2e_datalad) | 1 | 6b6fa389 |
| R2E | [Scrapy](repository_work/r2e_scrapy) | 1 | a95a338e |

查单次执行的路径顺序是：题目ID → 逐题查找表里的 `attempts` → `attempt` 和 `local_artifact_files`。这些文件包含原始轨迹、候选 `.diff`、冻结基线、result/评分报告及日志；用 `job_id` 和材料版本对应，不能把不同尝试目录中的文件拼成一次成功。

## 原始失败与后续修复怎么保存

原始失败、无评分、超时或基础设施异常没有被删除或改成成功。原补丁的CPU补评、材料变更后的诊断分数和独立语义判断另有回执。有效的模型解错本身是结果，不为通过无限重跑。

三个查找例子：

- DVC9395的原评分缺件与原补丁CPU恢复，从[DVC题主目录](repository_work/swe_dvc/tasks/iterative__dvc-9395)及[历史恢复索引](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/gpu_source/historical_recovery_supplement_index_v1.json)查找；不回填原始缺失报告。
- Coverage ea69新增51键评分后，原候选补评与旧49键分数分开，见[51键补充分析](repository_work/r2e_coveragepy/tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/model_analysis_scoring51_supplement_20261004.md)。
- Pydantic8511原候选按177项新参考集合补评，保留旧173项历史结论，见[原补丁补评回执](../../../../../runs/category2_repair_20260929/pyd8511_original_FP_regrade_20261004/technical_receipt_v1.json)。

## 本地完整性已经核了什么

SHA256用于核对文件内容是否与交付记录一致；它证明文件完整性，不证明评分规则或模型答案正确。下面各清单有交叉引用，**文件数和大小不能相加当成总数据量**。

| 检查 | 本次/既有核验范围 | 证据 |
| --- | --- | --- |
| GPU执行原件 | 本批106次＋旧GPU10次的3386份原件，3,785,793,226字节，大小/哈希通过；实际缺件另列 | [原件核验](../../../../../runs/category2_repair_20260929/overnight_watch_20261003/check_20261004_0241/execution_body_integrity_verification.json) |
| 冻结代码、材料及补充 | 8453个本地引用核验通过，含104项原记录哈希的精确本地定位 | [补充材料核验](../../../../../runs/category2_repair_20260929/overnight_watch_20261003/check_20261004_0311/supplemental_local_integrity_verification_v2.json) |
| 旧API原件 | 4次历史尝试，318份文件，113,749,374字节 | [旧API范围与核验](../../../../../runs/category2_repair_20260929/overnight_watch_20261003/gpu_local_preservation_gate_20261004/old17_api_scope_correction_20261004_0329/summary.json) |
| 逐题环境信息 | 52题、106次历史环境映射；936个本地引用大小/哈希通过 | [环境信息核验](../../../../../runs/category2_repair_20260929/overnight_watch_20261003/gpu_local_preservation_gate_20261004/materials_only_transition_20261004_0344/environment_information_integrity_verification.json) |
| CPU恢复材料 | 发布方913份既有本地文件；本线程再核底层文件、快照及5份交付文件，共918个不同文件，通过 | [CPU材料核验](../../../../../runs/category2_repair_20260929/overnight_watch_20261003/gpu_local_preservation_gate_20261004/materials_only_transition_20261004_0344/cpu_recovery_information_integrity_verification.json) |
| 性能资料 | 3818行映射到2724个不同本地文件，共544,118,409字节，通过；本轮实际补传34,076,392字节 | [性能原件核验](../../../../../runs/category2_repair_20260929/overnight_watch_20261003/gpu_local_preservation_gate_20261004/materials_only_transition_20261004_0344/performance_local_integrity_verification.json) |

总收尾依据：[GPU信息收口回执](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/gpu_source/environment_metadata_only_closeout_v2.json)与[CPU信息收口回执](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/cpu_inventory/recovery_information_20261004_v1/closeout_receipt_v1.json)。本次停止大镜像传输后，两侧该批大包本地接收均为0字节；此前已经保存的单个镜像包保留，这不构成全量镜像备份。

## 哪些没有保存或尚未验证

1. **未全量下载中间镜像，也未复制基础模型权重。** 保存镜像/模型身份、版本、来源、配方和现有必要材料。完整离线恢复、未来registry可用性和新构建后的评分一致性未在本轮重新验证；以后修改优化链路和镜像时，要对新版本做相应验收。
2. **没有补造历史性能指标。** 已有GPU利用率/显存和标记容器资源观测，但没有完整的历史宿主CPU、内存、磁盘、网络时间序列。当前宿主读数不是历史峰值，API累计时间不是纯GPU计算时间，采样峰值也不是最低资源要求。
3. **旧17题的历史缺口保留。** 某些旧镜像精确载荷和已消失实例不可恢复，见[有界历史恢复说明](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/cpu_inventory/old17_lookup_20261004_v1/README.md)、[旧17非GPU材料清单](../../../../../runs/ordinary_gpu_probe_20261002/local_preservation_20261004/gpu_source/old17_nonGPU_evidence_and_material_inventory_v2.json)。这些不是当前52题仍待求解，也不是已验证全项目可复现。
4. **性能改造尚未正式集成部署。** v13本地实现、CPU对照及独立复核已交付；真实Claude Code原容器验收、通用编译型任务推广和Prime线上验证不在已完成范围。Prime还需账户输入和费用授权；不因此继续占用本批GPU。
5. **尚无全面重复稳定性或训练收益结论。** 普通追加采样暂缓，训练/holdout准入和训练前后收益都不能由首轮高分推定。逐题现有用途限制仍有效。

账户凭据、主机秘密不属于本次交付内容。

## 后续维护与使用

这份说明是当前阅读入口，逐题JSON是固定时点的查找快照；原始文件不回写。后续模型尝试、补评或镜像优化使用新版本和新目录，注明对旧结果的适用关系。将来搬迁工作区，应连同清单中引用的本地文件一起保存，仅复制本说明或几个索引JSON不等于复制实验数据。

目前剩余的三个性能派生报表可以在本地继续整理。GPU关机由用户确认并操作；文档整理、本地统计及Prime待输入不会自动触发新GPU任务或资源采购。
