# MONAI：当前修订与探针

2026-10-04。持续负责人：`SWE | MONAI 题目修订`，线程 `01a0fd62-fb0a-7d02-877a-f9ef7ef32399`。用户已指派本线程处理工作包 `swe_monai` 的 2446、3715、6975；5932、4583 沿既有接收关系由探针线程负责，不重复接题。当前 progress 与交接请求由本线程按总账工具维护，发布和探针分别直接交对应线程。

**本仓三题CPU修订、非作者验收与双模型首次诊断均已完成。2446／3715／6975每题每模型首次各一次，共6次候选原评分均1，实际候选语义、完整轨迹及执行证据按各自范围核完；三个原探针请求已ACK并释放active。** 当前无确定新CPU/GPU作业，CPU在途0。旧6975缺图vendor环境组合继续阻断；没有追加普通采样、稳定率估计或训练/留出资格。当前统一入口为[三题汇总](probe_summary_three_tasks_20261004.md)，逐题证据见下表；机器状态去留不由本仓完成状态推导。

**6975阻断标识已澄清。** 旧裸`material_revision_id`也用于R15新COPY环境，存在匹配歧义。总账revision17起将阻断精确限定为该测试修订＋`vendor-nifti-absent@sha256:0a529471…`旧镜像组合；[范围依据](checks/monai6975_blocker_scope_clarification_20261003.json)核原actor缺图、COPY恢复及同材料正式0／1／0。已直接通知GPU；固定请求db75fe72和旧失败原件未改，未重跑CPU。本首Coder的[GPU原件核查](checks/monai6975_coder_a1_owner_analysis_20261003.json)已核实际COPY镜像、baseline官方资产、运行公开例及首HTTP原题面；[独立执行回读](checks/monai6975_coder_a1_execution_review_readback_20261003.json)已完成，资源观测及谱系限制保留。CPU验收等历史文件中的裸v1标签保持历史原文，不再理解成所有环境下该测试修订均被阻断。

| 题目 | 已有事实与本轮处理 | 下一步 |
| --- | --- | --- |
| **2446** | R15正式 **0／1／0／1** 及CPU独立验收完成。Coder/Qwen首轮各raw1、1F/3P及正式9P全过，完整轨迹和非作者语义已核，原请求已ACK、active已释放。 | [双模型首次诊断](probe_summary_2446_two_model_20261004.md)及[核收绑定](checks/monai2446_two_model_first_diagnosis_20261004.json)为当前入口；Qwen初版误报内部shuffle被旧回归检出后修正、返回协议外部兼容未验，Coder打印型检查弱项保留。无新CPU或普通追加采样待办。 |
| **3715** | 新版 **2 F2P＋1 P2P**；release5五行 **0／1／0／0／1**及CPU非作者核查完成。Qwen／Coder各首次评分1，实际修法均合理，3参考完整通过；两模型总回执已回传，旧请求不重提。 | [双模型首次诊断](probe_summary_3715_two_model_20261003.md)记录7方面行为分析及两份非作者语义意见：Qwen自测多次API误用，Coder零自测；code4／7差异和训练边界保留。当前无新修订或追加采样待办。 |
| **6975** | R15正式64参考 **0／1／0** 及CPU独立验收完成；首Coder/Qwen各raw1、4F60P全过，新增硬编码12像素节点通过，实际COPY镜像和官方资产已核。 | [双模型首次诊断](probe_summary_6975_two_model_20261004.md)及[核收绑定](checks/monai6975_two_model_first_diagnosis_20261004.json)已完成；原请求ACK、progress21/closed/active=null。两模型打印型验证、None未自测、Qwen集成未知/超时与附加Zip/NPZ未专项运行的范围保留；无新CPU或普通追加待办。 |


## 材料与证据

- **2446：** [修订单草案](materials/2446/revision_request.json)、[完整有效测试补丁](materials/2446/effective_test.patch)、[新断言增量](materials/2446/extra_tests.patch)、[参考候选](materials/2446/references_candidate.json)、[本轮静态检查](checks/monai2446_static_20261003.json)。旧事实以 [CPU 结果](../../../swegym_cpu_preprobe_20260929/tasks/Project-MONAI__MONAI-2446/result.md)及[独立复核](../../../swegym_cpu_preprobe_20260929/reviews/monai2446_result_review.md)为准，旧静态卡不是当前运行状态。
- **3715：** [修订单草案](materials/3715/revision_request.json)、[完整有效测试补丁](materials/3715/effective_test.patch)、[新断言增量](materials/3715/extra_tests.patch)、[参考候选](materials/3715/references_candidate.json)、[本轮静态检查](checks/monai3715_static_20261003.json)。公开依据及已有独立语义意见见[原题卡](../../../swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-3715/card.md)和[复核](../../../swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-3715/review.md)。没有把静态错修推导记成历史满分实测。
- **6975：** [接续单](materials/6975/revision_request.json)、[本轮材料复查](checks/monai6975_existing_pack_20261003.json)、[现成草案入口](../../swe_materials/monai6975_next/README.md)。历史 root 静态核查位于 `runs/category2_repair_20260929/analysis/monai6975_materials_root_review_0930.json`；原正式 **0／1／1** 和 setup900 准备失败分别保留，不能改成修后分数。

新材料只写本目录。`static_prepare.py` 是本包标准库材料生成和检查脚本，不是 CPU／探针启动器；已实际执行，单次耗时不足一秒。[cpu_prepare.py](cpu_prepare.py) 仅在新 CPU 机的 prepare 作业槽中准备固定镜像、核来源初态和清理，不作正式评分或 actor 权限证明。[公开开发清单](public/README.md)中 3715 已在新机执行，2446 已完成；6975 原版缺图和恢复版原例成功分别保存证据。[3715 actor 核查](checks/monai3715_actor_cpu_c_20261003.json)保留六条命令、实际身份及清理；两个通用 marker 的 false 保持原值，其原因和核查范围见 CPU 接续记录，不宣称平台保护全验收。没有修改共享代码、ingest、pins 或历史证据；本包 progress 和发布请求已通过总账工具更新。[2446／3715 非作者静态报告](reviews/non_author_material_review_20261003.md)已核公开契约、原测试保持、实际调用链和对照区分力，未发现具体阻断；报告对应的有效补丁 SHA 与当前文件一致，含 3715 的 detach 修订。这不是 fresh 盲审，不替代运行后独立验收，6975 不重复重审。3715 的数值比较仅对预测副本 detach，以兼容该版本测试 helper 的 NumPy 转换；梯度检查仍使用原计算图。

## 新机恢复与验收要点

1. **复用共用入口与固定版本。** 领取机器统一名额，使用 MONAI 独占输出目录和容器标签。新机先核镜像 ID／digest、linux-amd64、题级 base、导入路径、UID、解释器和来源初态；既有 actor 证据按版本复用，换宿主只补实际身份与关键路径。不得把静态导出当 actor 实际状态。
2. **2446 固定配方已恢复，wheel 已归档并核实。** 复用 `runs/swegym_cpu_preprobe_20260929/task_inputs/Project-MONAI__MONAI-2446/buildplan.json`、`wheel_manifest.json` 和 `private/historical_recipe.json`。固定 wheel 为 `nibabel-4.0.2-py3-none-any.whl`，实际大小 3,345,004 bytes、SHA 与历史记录匹配；cpu-a、cpu-c 按同一原 Dockerfile 分别重建并保留各自实际 ID，不能把新构建冒称历史 image ID。正式安装配方已由R15受信绑定，2446四行、6975三行的安装均已核RC0且无失败命令；安装弃用警告仍保留。 [实际构建绑定补充](materials/2446/image_binding_supplement_v1.json)已固定并发给发布者，明确绑定cpu-c ID及构建完成原件SHA；旧syntax-only构建计划不回写。GPU本机实际ID待执行者准备和核验，CPU ID不冒填为GPU已存在。旧摘要已追溯到原配方文件，命令与归档审计副本一致，见[摘要来源](materials/2446/recipe_hash_provenance_v1.json)。
3. **3715 只需 CPU 合成张量和小网络。** 必要依赖为项目 testbed、Torch、NumPy、pytorch-ignite、已有测试工具；不用预训练权重或 Saliency 全算法回归。先核真实 actor 中公开 API 可执行及 base 字符串错误仍可复现；相关旧模式测试按实际失败补验。新增私有测试使用 CPU，不调用 CUDA、不比较上下文函数身份。
4. **6975 新镜像已实测恢复原图。** [COPY镜像核查](checks/monai6975_public_asset_image_cpu_c_20261003.json)证明固定源13层保持、仅多一COPY层、13源件不变；[恢复actor核查](checks/monai6975_actor_public_asset_cpu_c_20261003.json)证明官方SHA原图在UID54321可读，原公开 `LoadImaged`／`RandAffined` 直调与Dataset均实际完成。[非作者实测窄核](reviews/non_author_public_asset_runtime_review_20261003.md)完成，没有发现恢复切片的新具体阻断；旧条件草案和准备失败证据保持。新环境已由R15正式登记，旧v1阻断保持；公开56项不冒填为正式64参考。
5. **正式评分读完整结果。** 使用未变的 vendor 测试命令；核原参考完整、新节点实际 collection／执行、无 skip／缺席、安装与测试逐段 RC、候选冻结源码／投影、材料身份及两层清理。2446、6975 有既有有效正对照；3715 新版五行及完整原件已由作者和非作者核完，gold 与合理替代均为 1。异常或导入失败不能替代预期的目标失败。

6975 延续已有 setup1800／test1800／whole3600 的有界恢复；2446 复用已验修复配方和准备条件，3715 采用本轮正式入口有效 profile。历史 4 GiB 回收压力继续保留，不自行提高资源或宣称换机修好了根因；具体预算／版本由共用维护者和资源协调者落实。探针模型与预算仅引用统一执行线程的有效配置。

## 需要共享维护者接入的具体范围

3715沿原release5已验版本进入探针；2446、6975已由R15接入，下列为题级封闭范围。共享接入完成不替代题级CPU验收：

- **2446：** 唯一 `tests/test_smartcachedataset.py`，`replace_test_patch_append_p2p`，只追加 `TestSmartCacheDataset::test_shuffle_ndarray_list_and_cache_cpu`。
- **3715：** 唯一 `tests/test_prepare_batch_default.py`，`replace_test_patch_append_f2p`，只追加 `TestPrepareBatchDefault::test_evaluator_string_modes_forward_and_restore_cpu`。枚举回归控制包含在同一新方法里，不另外修改 P2P 清单。
- **6975：** 完整有效补丁必须同时保留 `tests/test_compose.py` 与 `tests/test_dataset.py`；追加像素 P2P，不能截成单文件绕过受信恢复。现成 [消费者扩展清单](../../swe_materials/monai6975_next/consumer_extension_plan.md)继续作为接缝依据。

维护者需保留父材料、原参考次序和原测试断言，逐题封闭登记新节点／路径／基线 SHA／有效补丁 SHA，生成并冻结新 producer／registry／code。不改 parser、通用 reward、权限或安全边界，不把全局任意路径放开。只有相关正式运行等待接入，其它材料工作继续。

已与“负责处理分类二的明确问题”核对：该线程负责本批 SWE/R2E 共用登记和发布；3715 已进入 SWE7 producer 与 release5，cpu-c 发布 manifest SHA 为 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`，837 文件与可信读回已通过。本包另作启动前逐件 SHA 核对；该候选也包含已审 Git 初始化修复，因此重新生成 prepared，不把旧 FrozenPatch 重绑新代码。2446、6975在R15正式接入并核收发布回执，完整正式矩阵和独立验收均已完成；release5原prepared仍保留，不用于R15矩阵。旧草案中的“另授权”等措辞是当时状态，既有题级授权没有新增审批。3715旧模型原件和固定请求保留，最新双模型结论在本页链接的摘要维护；本线程继续负责2446、6975结果分析及结果触发的必要修复。
