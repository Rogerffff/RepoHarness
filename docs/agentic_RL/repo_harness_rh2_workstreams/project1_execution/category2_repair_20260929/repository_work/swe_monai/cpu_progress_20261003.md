# MONAI：新 CPU 机接续

2026-10-03。本包接续 2446、3715、6975。总协调已将本包后续执行固定到 **cpu-c，19 vCPU／49.3 GiB，已明确开放**；cpu-a 的已获槽作业自然完成，不派发新作业。旧机限制继续保留。宿主验收不是题目验收。资源与领取规则以[共用入口](../../cpu_resources_20261003.md)为准，远端只写 `packages/swe_monai/` 及本包作业输出。

**当前依据2026-10-04：三题CPU修订、非作者验收及两模型首次诊断均完成；共6次候选原评分各1、逐题参考全过，语义与完整轨迹独立复核完成。三个原探针请求已ACK、active释放；本仓CPU在途0、无确定新CPU/GPU作业。** 当前入口[三题汇总](probe_summary_three_tasks_20261004.md)及[R15检查点](continuation_checkpoint_r15_20261003.md)。R15 2446=0／1／0／1、6975=0／1／0和历史原件保持，旧vendor缺图组合仍阻断。下文旧“在途/待/新prepared”等均为各时点证据，不覆盖本段当前状态；不重复已验CPU矩阵或成功首臂、不从本仓完成状态操作云机器，单次诊断不授训练/稳定率资格。

2446 私有作业 `monai2446-private-unit-20261003-63e95bed` 的实测模块退出为 **1／0／1／0**：原始代码只失败于 `test_datalist`，不打乱 ndarray 的错误修法只失败于新增 shuffle／缓存 P2P，gold 与外层 list 复制方案各 9 项通过。四行源件／补丁检查与导入检查全部 RC0，新增节点无跳过，各行清理查询 RC0、残留空。[原件检查](checks/monai2446_private_unit_cpu_c_20261003.json)绑定日志和摘要。这里是 root 私有单元诊断，不能当正式 reward、actor 权限或独立验收；请求的 2 CPU／4 GiB 限额也没有额外冒称实际 HostConfig 证明。

## 固定准备输入

cpu-a 输入版本 `inputs-20261003-e19f5b28`，manifest SHA256 为 `5c6174632af0d8562c6e77618c1b9fa480ea79aa2223d17abfb0cbfe4924d64c`。cpu-c 接续版本为 `inputs-cpu-c-20261003-84df00d5`，manifest SHA256 为 `902e402a20724488b95df81d2d4ffbb198d8609f7bbccbd0db50b7a43673db77`，174 件文件已在远端逐件核大小与 SHA。接续版新增已核 wheel、公开命令和私有检查辅助，修订补丁未改变。两版均在本包 `preparation_inputs/` 下，包括原始 public／grading／environment、本包修订、静态报告、2446 兼容配方和 6975 现成包；不整体挂载给 solver。

[cpu_prepare.py](cpu_prepare.py) 固定镜像 manifest 拉取；2446 获取并核实历史 wheel 后按原 Dockerfile 重建，保留新实际 image ID、source 层前缀、Dockerfile／wheel 摘要和日志。来源身份检查容器的 2 CPU／4 GiB、无网络、512 pids 配置已从实际 Docker inspect 核对，唯一名称和作业标签明确，退出后只清理本次容器。它只检查 base、文件摘要、解释器与依赖身份；root 运行不证明 actor 权限或题目可开发。cpu-a 的 image ID 不冒填为 cpu-c 已有镜像，迁移后重新核本机实际身份。

输入里的 6975 `requirements-dev.txt` 保留历史源件，但不作“镜像 clean base”断言：已有证据表明镜像初态曾删除 MetricsReloaded 行，仍需记录实际 porcelain。这不是本轮修订；其它来源文件照锁检查。

## 公开开发与正式验收

[公开命令](public/README.md)已补齐：2446 复用既有清单，3715 运行枚举／字符串模式的真实非空 forward，6975 加原 NIfTI／RandAffine 示例。3715 已在真实 CC 桩、UID54321 下运行六条命令：枚举 train／eval 实际预测与梯度符合公开 API，字符串 train／eval 都确为题面的 `unsupported mode`，原公开模块 2 项通过。[本包核查](checks/monai3715_actor_cpu_c_20261003.json)保留完整 captures、实际 CPU／内存与清理。原 Runner 的两个通用 marker 检查 false 也保留：本清单打印 `PY_CHECK`，原检查寻找 `RH2_SYS_EXECUTABLE`；没有运行其 BASH_ENV 写探针，不宣称平台 guard 全验收。2446已完成；6975原版缺图，现已用新COPY镜像完成同一公开原例复验，旧证据保留。

三题原材料 release1 prepared 的[历史核查](checks/monai_baseline_prepared_cpu_c_20261003.json)保留，分别为 1＋2、1＋1、4＋59，不含新节点。当前 [release5 prepared 核查](checks/monai_release5_prepared_cpu_c_20261003.json)确认三份 public 逐字保持、只有 3715 正式增加 F2P；固定 manifest 为 `18da4cd12d7813fbef7348e300a94fefde0be18603298640127a11e7685df0cf`，private artifact 为 `8e78e1bc655e7464ab93c587776289d0d939225378730baa32400cf2886c5a96`。

[最新外层退出核查](checks/monai3715_outer_exit_cpu_c_20261003.json)记录 3715 镜像、release5 prepared、固定 tag 和公开 actor 四个作业均为 `finished`，cpu_slot RC0 与 launcher RC0 一致。[正式原件读回](checks/monai3715_formal_cpu_c_20261003.json)另核五行外层 RC0、15 个参考结果、冻结源码和两层清理；[非作者最终报告](reviews/non_author_cpu_review_20261003.md)已完成，保留实际 ID／资源归档及公开提示交付边界。

本包 3715 使用[发布记录](../../publication_20261003.md)中的固定版本 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest SHA256 为 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`。总协调确认 cpu-c 的 837 文件与可信读回通过；本包启动前也逐件核大小／SHA。该历史release5仅 **3715** 新材料在此版生效，最终 **2 F2P／1 P2P**；2446 安装配方／新增 P2P 和 6975 两文件消费随后已由R15发布，release5本身不包含。因为该版还包含已审 Git 初始化修复，新 prepared 重新生成；原 release1 的 prepared 及旧 FrozenPatch 不重绑。新 actor／评分使用 `runtime_cpu_v2/rh2/.venv/bin/python`，testbed 自身依赖保持；正式运行设置 `PYTHONDONTWRITEBYTECODE=1`，不热改工作树或 release。

[私有语义辅助](cpu_private_behavior.py)仅在旧标准库辅助脚本上追加本包／本次作业标签，保持串行候选、有界命令和 finally 清理。[输入生成器](prepare_private_unit_spec.py)核固定材料与实际镜像准备报告，生成明确标记 private unit 的检查单；2446 四行已在 cpu-c 的 run 槽执行。它不产正式 reward、不作 actor 权限证明。

[3715 正式编排](cpu_formal_3715.py)仅调用固定 release5 的原评分入口及原有 CPU setup900 辅助，五候选串行，test1800／whole3600 保持，有效结果和清理确认后继续；不编辑共享评分逻辑。[公开 actor 限额适配](cpu_actor_bounded.py)只给冻结 devcheck 的临时 root 镜像初态探针增加 2 CPU／4 GiB／PID512，原非 root actor 和 CC 路径保持。两脚本冻结到本包新版本目录，摘要在启动时核对；记录原入口 SHA 和实际传入参数，不改在途脚本。

总表为本包预留 actor stub 端口 18193、gateway 18192，同包公开 actor 串行复用。3715 已完成该端口上的公开 actor，正式矩阵无模型服务。暂停前已只读核到 Orange 的 `orange9b-envonly-derived-c-20261003-v4` 与 `orange9b-envonly-actor-c-20261003-v1` 真实入槽并完成；本包随后恢复一次 6975 申请 `monai6975-image-20261003-4787720e`，仍为 busy／75，没有开始准备，不计题目失败。此前 `f0e82406` 的未获槽记录也保留。这两次 75 是历史未获槽记录。恢复后新申请 `monai6975-image-20261003-f121f560` 已入 prepare 槽0，不把历史忙碌记成题目失败；仍不抢占或跨机重跑。

3715 [单题请求](probe_request.json)已通知统一执行者并保存独立快照、进入接收登记，尚非运行准入。当前按三方流程直接交接并通过总账工具登记；本线程持续负责结果解释和必要修复。


## 本轮公开 actor 与原图条件

2446 `monai-2446-actor-20261003-b6bf42bd` 已完成并读回：四条命令0／0／1／0，UID54321、testbed解释器、NiBabel4、实际2CPU／4GiB／PID512、7个原公开测试与清理均核。[检查](checks/monai2446_actor_cpu_c_20261003.json)保留旧两个通用marker的false，不扩称平台安全全验收；该公开actor证据自身不证明正式矩阵；当前R15正式结果见首段。

6975 原镜像 `monai6975-image-20261003-f121f560` 已完成，[检查](checks/monai6975_image_cpu_c_20261003.json)核实际原ID和13源件SHA。原公开actor `monai-6975-actor-20261003-723cd019` 已完成，[检查](checks/monai6975_actor_original_cpu_c_20261003.json)确认UID54321实际缺原图，原例RC1；旧模块56通过，内存六行的真实像素均正确、Dataset True／None的lazy策略错误。原外层RC0保持，all_match_expect=false也保持，不当题目开发通过。

官方原图按固定base的data_config归档，SHA `c01a50caa7a563158ecda43d93a1466bfc8aa939bc16b06452ac1089c54661c8`。首次申请295281d0为busy75；随后8e8b9cff构建成功，但数值UID的Git身份探针被dubious ownership拒绝，已完整归档清理，没有Git版本证据。[v2准备脚本](cpu_prepare_6975_public_asset_v2.py)分开root Git和非root图像检查，实际作业 `monai-6975-public-asset-image-v2-20261003-526bfdc3` 已完成，外层RC0、清理完整；[镜像核查](checks/monai6975_public_asset_image_cpu_c_20261003.json)绑定新ID、唯一COPY层和13源件。没有RUN／pip／源码或测试改动，构建daemon限额与探针容器限额分开，不外推整次构建峰值。

恢复actor `monai-6975-actor-20261003-b7c29487` 已完成并全部读回，[核查](checks/monai6975_actor_public_asset_cpu_c_20261003.json)记录命令0／0／1／0；原NIfTI SHA精确匹配，原LoadImaged／RandAffined直调和Dataset均实际输出CPU有限张量。原lazy策略缺陷仍在，原公开56测试通过；实际HostConfig/cgroup及两层清理已核。CC桩首prompt仍是generic devcheck，不能当正式题面交付或模型求解。

[非作者运行窄核](reviews/non_author_public_asset_runtime_review_20261003.md)已完成，无恢复切片新阻断；该窄核报告自身不涵盖正式发布或64参考；当前R15已发布，64参考矩阵正在执行，非作者验收仍待。旧v1阻断保持，新候选 `monai6975-dataset-dict-pixels-cpu-v1+public-nifti-v1` 不能未经发布直接送GPU。

新节点私有作业 `monai-6975-private-node-20261003-81ccfd89` 已完成并读回：[原件核查](checks/monai6975_private_node_cpu_c_20261003.json)证明noop／gold各1通过，discard_dict_output在真实像素比较失败，12／12像素不匹配；所有源件／补丁／导入准备RC0、三容器清理与外层RC0。只跑该节点，不填作正式64参考reward或非root actor。旧未领取v1已取消并核收回执，原两文件测试＋官方COPY层合并请求 `swe-monai6975-dict-pixels-public-nifti-publish-20261003-v3` 已提交并通知发布者，[固定输入](materials/6975/publish_combined_request_v3.json)SHA为0dffab73…；环境单独v2不另提交。CPU和GPU均仍需；该历史时点无在途，当前已有6975正式作业。

2446构建身份补充已通过同一原请求的supplement机制提交并通知发布者：[固定说明](materials/2446/image_binding_supplement_v1.json)SHA为6b8bced6…，明确cpu-c实际镜像28959a33…、构建完成原件86201bf3…、实际actor和grader待正式验证范围。原buildplan syntax-only历史保持，原发布输入3e93dfa9…不改，不复跑已验构建/actor。GPU实际镜像ID仍待执行者按既有code4 image_override及同固定配方准备和核验，不把CPU ID冒填为GPU已存在；不新增训练typed契约。
