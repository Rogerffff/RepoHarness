# DVC9395 当前题卡

2026-10-03 12:25 SGT。状态：**R20正式六项noop0、gold0、正确对照c3_frozenfix1、c3_missing_only0、up351_port0、w_swallow3 0已完成；每项41执行／40参考完整，正确对照全41通过。实际账本reset900、UID预检／安装／两层清理均核。最终非作者六控制／actor适用复查已完整核收，单题两模型GPU请求已登记并实际通知。** 见[正式矩阵](formal_matrix_r20_v1.json)和[题主读回](formal_cpu_r20_owner_readback_v1.md)。旧R14两次protect300 infra/null与隔离支持分开保留；六项准备聚合149–249秒均低于旧300上限，不据此宣布预算导致恢复或效率根治。成功账本resource_facts均为空，仅c3_frozenfix的单个运行时点留存实际2CPU/4GiB/PID512/none HostConfig；不证明全程无OOM/PID事件。固定题面、材料、镜像、保护／资源／安装测试预算未变；900涵盖九处既有reset步骤。候选和父身份见[revision.json](revision.json)，原提交快照与历史不改写。

公开目标是拉取此次repro必需的缺失数据；base的 `is_data_source`明确含add/import。原测试的checkout/restore次数约束误拒合理实现；吞错误候选在原云端私测得1但不恢复文件；gold会覆盖用户修改，且有已证dry、无remote和run-cache回归。最新范围见 [09-30交接](../../../../../category3_diagnosis_20260929/handover_to_category2_20260930.md)及 [原结果](../../../../../category3_diagnosis_20260929/tasks/iterative__dvc-9395/result.md)，以页首更正为准，不能沿用下面历史T3/S2豁免。

保留v4：去掉精确计数、核拉回内容和下游产物、确认修改不被旧数据覆盖、import缺失恢复、不可拉回时传播错误。另补11个精确参考：

| 缺口 | 新断言 | 草案分组 |
| --- | --- | --- |
| 冻结stage输出 | 工作区和缓存都删掉；下游恢复并用到remote数据；命令痕迹不变 | F2P |
| dry两种状态 | 缺源或缺输出时，workspace/对象cache/runs内容快照不变；允许base在缺源dry时报既有错误 | P2P 2项 |
| 无需下载无remote | normal/dry均能处理齐全数据，不因预拉取报错 | P2P 2项 |
| 无remote且用户修改源 | 修改保留，下游使用新内容 | P2P |
| 无remote且源确实缺失 | 抛出失败，不能吞掉错误并声称成功 | P2P |
| no-run-cache | 本地runs删除后，不下载runs、不执行不必要命令 | P2P |
| 无hash已有输出 | 普通新stage可以按原公开路径产生正确输出 | P2P |
| 依赖变化 | 旧输出cache不可得、remote空，仍按新依赖重算 | P2P |
| HTTP恢复 | 保留本地run-cache，从只读loopback HTTP恢复缺失对象和lock，不重新执行命令 | P2P |

HTTP没有要求新增外网服务或让HTTP列举runs。目录部分删除歧义继续登记，不补断言；原run-cache恢复要求的P3风险仍保留。新增行为不依赖gold的具体函数分解、调用次数或传参形式。

主正确对照复用独立核实的 `c3_frozenfix`（SHA以修订单为准）；gold与`up351_port`作为负/辨别对照，后者有dry回归，不能为保它删断言。正式矩阵预期noop0/gold0/c3_frozenfix1/c3_missing_only0/up351_port0/w_swallow3 0，**旧R14两次noop正式reward为null；R20六项0/0/1/0/0/0已完成见页首，最终非作者报告已完整核收**。

私有诊断 [cpu_diagnostics_v2.json](cpu_diagnostics_v2.json) 分开记录原版与当前v2：原版30执行／29参考，gold与吞错候选全过，`c3_frozenfix`仅被旧restore次数断言拒绝。当前v2为41执行／40参考，无参考缺席，六方观察如下；这些是pytest结果，不是正式评分。

| 候选 | 当前v2观察 |
| --- | --- |
| noop | 三个F2P及未计分的原import用例失败；37个P2P通过 |
| c3_frozenfix | 全部41节点通过 |
| gold | 修改源保护及全部10个新增P2P失败 |
| c3_missing_only | 仅新增冻结输出F2P失败 |
| up351_port | 两个dry及四个无remote边界失败 |
| w_swallow3 | 修改源保护及全部10个新增P2P失败 |

本轮v1诊断曾有6个新增节点因 `Repo.odb` 不存在而失败。v2仅把三处 `dvc.odb.local.cache_dir` 改为本base真实的 `dvc.cache.local.path`，不删断言、不改候选。v1材料保留在 [history](history/dvc9395-behavior-v1-draft/revision.json)；旧API错误的effective行不复用，original六行的补丁、依赖与候选身份未变，报告明确复用范围。当前六个容器全部清理成功，无残留。

[非作者v2差异窄核](../../reviews/non_author_4166_9395_v2_review_20261003.md) 确认API修正有基线源码依据且没有扩题；该报告写于新版运行结束前，不能代表六方原日志已验收。原restore仍含内部调用约束，后续合理实现接受性风险继续保留。

[非作者CPU原件读回](../../reviews/non_author_6954_9395_cpu_review_20261003.md) 随后独立核了未变original六行及当前v2六行：全部参考精确命中、退出与清理相符，失败落在实际行为路径而非旧API、导入或收集错误，无新增阻断。noop的非参考import失败明确保留；旧effective六行只核原件完整性，不混入当前结果。报告不验正式评分、完整安装或actor。

当前v2六方正式矩阵及独立运行核查已完成，下一步等待兼容冻结GPU消费者的两模型首轮结果并逐轨迹分析。原版`w_swallow3`正式成绩按可用封存入口核实；旧私测全过不冒充正式reward，旧工件不改绑。公开actor已另行完成。其它云端候选证据按接受性需要定向复用，不重跑历史全部组合；不能核销缺席、skipped或正对照失败。

环境：cpu-a已准备公开依赖镜像，源码未变、base层保留、`pip check=0`，实际pygit2为1.14.1。首轮旧assets的CPython3.10 wheel与本题CPython3.9不符，已改用历史核实的CPython3.9 wheel，未放宽SHA检查；身份见 [CPU准备记录](../../cpu_preparation_20261003.json)。

[v2发布请求](publication_request_v2.json) 已固定完整测试补丁、有效安装配方、公开开发说明及诊断报告身份，R14共用冻结版本及CPU-a部署回执已核收。未改题面，不把私有反例交给solver。正式CPU、actor、非作者验收通过后才能提交普通探针。

[本轮公开actor检查](public_actor_r5_v1.json) 已完成真实CC/relay的四条公开命令，17个既有公开测试实际通过且无skip／缺失；首请求逐字交付题面和开发说明，身份/profile一致，自有容器与网络清理。完整原件已SHA校验回收到本机，[非作者运行原件读回](../../reviews/non_author_actor4166_9395_runtime_review_20261003.md)已完成，无新增阻断；本段历史actor检查当时不含正式CPU评分；当前R20正式评分已完成，模型探针结果仍待回传。

[R5→R14公开actor复用窄核](../../reviews/non_author_public_actor_r14_reuse_review_20261003.md)已确认相同公开材料、固定镜像和公开执行路径的复用范围；本题两次R14 prepare均已另核公开payload和solver prompt text与R5相同，JSON metadata不声称相同；不把复用报告当新actor执行结果。

## R14失败与R20接续历史

以下是分开封存的历史过程；当前状态以页首和[CPU验收](cpu_acceptance_r20_v1.json)为准。

[本次正式失败原件](formal_cpu_r14_failure_v1.json)保留trusted restore/apply成功、没有OOM/pid耗尽事实及完整清理。保护脚本递归变更testbed/conda属主可能昂贵，但未交付子步输出，尚未证明哪条chown或主机争用导致超时。固定[CPU支持输入](../../requests/dvc9395_control_protect_timeout_support_input_v1.json)已发，见[实际发送回执](../../requests/dvc9395_control_protect_support_delivery_20261003_v1.json)。有实际诊断／版本修复变化后才接续，不能把infra算noop0或重绑旧工件。

[首个R14失败非作者窄核](../../reviews/non_author_formal9395_r14_failure_review_20261003.md)已完整读回：34原件和三冻结源码等SHA匹配，确认reward null／保护300秒超时，具体chown子步／宿主根因仍未知。发布者已claim CPU支持，并与Pyd8567同阶段问题一并诊断；本题停发，等待具体恢复证据及必要的新版本绑定。其余已验证DVC绑定保持有效。

接续时须新建与支持回执一致的固定series／输入／输出。旧R14流水线将任意已归档receipt当作完成控制，会误跳过本次infra noop；不能直接原样启动，不能把失败归档混进成功矩阵。历史失败及其它三题有效绑定保留。

本轮支持回执为[保护阶段诊断](../../../../../../../../../runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/cpu_a_control_surface_protect_v1/dvc9395_resource_support_receipt_v1.json)。62原件SHA/大小、两文件恢复／保护自证、实际2CPU/4GiB/PID512及清理已核。仓库chown约11.060秒、解释器前缀chown约231.108秒为宿主行到达墙钟；不证明旧失败子步或CPU耗时。新控制再次infra即停后续，不放大预算；旧失败归档不计completed。

[第二次正式失败记录](formal_cpu_r14_recovery_failure_v1.json)单独封存新prepare、run input、34原件及清理；材料、镜像、profile、budget与旧正式相同。trusted setup聚合301.288秒、启动46.730秒，留存峰值665.844MiB且无OOM/PID耗尽；eval字节与旧失败相同只表明都截止setup自证处，具体保护子步仍未知。[支持v2固定输入](../../requests/dvc9395_control_protect_timeout_support_input_v2.json)含43个SHA绑定，[实际通知](../../requests/dvc9395_control_protect_support_delivery_20261003_v2.json)已完成。六控制没有任何有效正式成绩；等待具体修正后再建新系列，其他三题绑定继续有效。

[第二次失败非作者差异窄核](../../reviews/non_author_formal9395_r14_recovery_failure_review_20261003.md)已核43 pins、34原件及tar精确集合、新prepare/FP身份、阶段和清理。没有新增误分级；正式policy只是调用绑定，归档没有实际HostConfig；不能从隔离支持外推正式子步。支持v2已claim，仍等待具体修正，不授予probe或训练资格。

维护线程已选定单独R20窄支持设计：仅对9395及Pydantic8316的既有固定材料／精确grader配对，将env_reset_timeout_seconds从300改900；其余262题spec不变，保护措施、资源、安装／测试／whole预算和材料不变。当前仅有设计，尚未实施或部署核收，不清除阻断、不启动CPU。此字段也用于其它reset/preflight/观测步骤，不能把设计缩写成只改某条chown。9395没有可复用的有效正式控制，部署后须新绑定补全六项；900仍不保证恢复，遇新infra或清理未知即停。

[R20支持变更非作者窄核](../../reviews/non_author_dvc9395_r20_budget_support_review_20261003.md)已完整核收，精确policy闭合、ledger取实际spec而评分仍用同一spec；外部替代依赖replay8例只验接线，不算实际CPU。题主另核新prepare、实际32字段spec、host/公开及prompt正文绑定，900与固定policy SHA匹配，镜像、材料与脚本digest同旧R14。六控制全部待实测，不重绑旧FrozenPatch。

R20首noop已完成35原件回收，实际预算900／UID预检成功／安装rc0／测试rc1、37计分P全部通过、三个计分F及未计分import失败，清理完备。准备聚合209.157秒小于旧300；这次可完成不证明用了扩大的时间额度，也不证明效率改进。captured logging的ERROR行不是pytest ERROR节点；离线汇总v1会误计，保留v1并用v2只读选择文件节点纠正，不修改官方报告／材料／日志或重跑候选。


## 当前GPU交接

[最终非作者正式运行报告](../../reviews/non_author_formal9395_r20_runtime_review_20261003.md)已完整读取并核58个报告文件身份，无新增阻断；[CPU验收](cpu_acceptance_r20_v1.json)固定六控制和R5 actor适用范围。[单题probe_request](probe_request.json)已登记，输入SHA `8dddd01f5530417085ea20cec8e884e1c0da0b1eca49de724c128d93185805f1`；[官方通知回执](../../requests/dvc9395_probe_delivery_20261003_v1.json)已保存且总账notice标sent。两模型首轮各1次，实际GPU消费者／镜像／权重与结果仍待回传；不把领取或回执当题目完成。
