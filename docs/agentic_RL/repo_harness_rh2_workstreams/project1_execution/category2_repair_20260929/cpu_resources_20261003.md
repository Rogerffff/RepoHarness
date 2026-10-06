# 当前 CPU 资源与执行入口

**当前可用：cpu-a、cpu-c。cpu-b已于2026-10-03 06:07 SGT销毁并由提供商清单确认不存在，禁止继续SSH、部署或派发到cpu-b。** 原cpu-b五仓13题在退租当时没有已知CPU待办，证据已完整归档；随后EA69发现公开交付缺项，已将coveragepy补充窄验先分配cpu-c，随后因两槽均有在途于08:43改分配现有cpu-a，网关18210／桩18211，原两作业槽和一镜像准备限额不变。GPU求解和轨迹分析继续。若模型结果发现具体CPU修复需求，向发布线程申请剩余资源，不自动重租。

发布线程维护公共运行环境、control/setup与部署记录；两台各2个作业槽，镜像准备最多1项且占一个作业槽，当前合计最多4作业。R14–R17已直接回题主；R17的EA69公开题面补充已在cpu-a/c核部署与可信读回，实际overlay／镜像及首请求由题主在cpu-a验证。迁移时cpu-c无coveragepy自有作业，已移除该包的未来准入；两主机仍各两槽、prepare最多1并占槽，未预留名额。mypy10174临时优先窗口已因实际入槽消费，恢复两槽公平轮转。R16材料部署范围保持；Dask8801的后续题级CPU与非作者验收由题主完成，具体当前结论见下方依赖审计，不能由发布通过数替代。按题材料阻断独立有效。以下初始化和发布记录保留其历史范围；当前版本见部署清单。

退租原件：`runs/category2_repair_20260929/overnight_watch_20261003/retirement_cpu-b_20261003/retirement_result.json`。没有修改cpu-a/c或GPU实例。

## 独立评分性能工作包（2026-10-03 22:19 SGT）

按用户授权，已在cpu-a/c的现有准入配置中登记`grading_performance`，并建立独立目录`/work/rh2-category2-20261003/packages/grading_performance/`。由“评分性能与 Prime Sandbox 验证”线程负责：cpu-a先调查DVC／Coverage，cpu-c先调查Pandas。所有下载、准备和实验仍经现有`cpu_slot.py`；每机全局2槽、prepare最多1且占槽、磁盘及内存余量门槛保持，控制脚本逐字未改。

起步每机该包最多运行1项是线程间合作约定，现有脚本不单独强制包级限额。此次没有派发作业、部署代码或镜像、分配端口、停止其它任务或处置实例；不改变原15仓／52题分工，也不代表性能或题目已验收。实际两机配置前后与脚本SHA回执：`runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/grading_performance_package_admission_v1/resource_support_receipt_v1.json`。请求及结果直接在该线程与发布线程之间沟通，无需背景线程转发。

Coverage性能对照的精确e23评分镜像供给已闭合：GPU源端单次导出，CPU-a整档核413,471,752B及完整SHA一致，prepare作业`gperf-coverage-exact-load-02`实际finished／退出0、load0、目标ID及Linux/amd64准确。首个性能线程包装因系统Python缺`hashlib.file_digest`在load前停止，改流式hash的新作业成功，失败历史保留。没有重建或修改题主材料，源档与实例保留；性能收益由该线程后续实验验证。源v1回执不回写，当前闭合回执：`runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/grading_performance_coverageea69_exact_image_v1/resource_support_receipt_v2_target_closed.json`。这只关闭单项镜像供给依赖，不代表题级验收或性能收益。

## aiohttp1c1：模型候选取消回归的现存CPU支持

2026-10-03 13:57 SGT：`r2e_aiohttp`的新CPU支持使用现存cpu-a，gateway18212／stub18213只登记、未启动；直接公开脚本无需CC端口。仍两槽公平入场、不预留、不停在途。R6实际核855成员及可信48/216通过。

GPU原actor `00ad3e96…b87683` 已以596,233,375B原归档传入并在准备槽加载；两端归档SHA、加载退出0、精确ID及linux/amd64已核收，未重建镜像或启动项目容器。准备作业已正常退出。支持请求已回执；这表示环境供给完成，实际UID54321、解释器3.9.21及公开取消对照由题主在一次有界实验中取证。原完整Frozen／raw1／58不改，不自动授予训练资格。就绪回执：`runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/aiohttp1c1_cancelled_main_v1/resource_support_receipt_v2.json`。当前仍有该题的已计划CPU验证，不能将原cpu-b无待办快照当成当前cpu-a可退租依据。

## GPU code8：Pyd8316／Moto6114固定镜像供给

2026-10-03 14:38 SGT：现存cpu-a的精确f939／1d8镜像已核linux/amd64，并在单个准备作业内串行导出，两路save/gzip及作业退出均为0。Pyd归档1,485,694,785B，Moto归档1,236,203,973B；两份SHA/绝对路径已直接交GPU执行线程。9份小原件8,107B已SHA回收，大镜像未回传本地。仅原像供给完成，GPU迁移、加载及code8严格绑定由GPU执行者核收，不新增题级CPU或材料发布。

供给回执：`runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/code8_exact_image_supply_v1/resource_support_receipt_v1.json`。源归档保留至目标核收或无源依赖确认；当前不沿旧退租门槛自动停机或销毁实例。CPU日常两槽/单准备限额保持。

## cpu-c：Dask 的剩余资源依赖

当前接续（2026-10-03 21:39 SGT）：Dask题主确认四项同原FP CPU恢复均自然结束、作业槽闭合、自有容器0，已无新CPU恢复待办；7138供给依赖关闭，源档保留。7305／9378／7138已有R23/R24支持，8801 R25已核收并直交GPU。8801新CPUraw1／45参考全pass，final运行绑定非作者核无阻断，fresh23为19pass／4fail；四项是当前候选未达既定诊断目标，不据此推断题目材料缺陷。原GPUNone、新CPU原分和候选语义结果分列，仍无自动训练奖励资格。剩余缺失Qwen首轮和实际GPU R25绑定由执行端与题主接续，不重Coder。当前只关闭题主确认的Dask CPU／供给依赖，未核整机其它仓库依赖；源文件和cpu-a/c继续保留，不授权停机或销毁。最新依赖审计`runs/category2_repair_20260929/publication_cpu_takeover_20261003/resource_dependencies/dask_cpu_c_dependency_20261003_v7.json`；后续验收补记同证据根`r25/owner_final_acceptance_supplement_v1.json`，原R25输入／回执不回写。

历史接续（2026-10-03 18:17 SGT）：题主已在cpu-c按统一槽串行恢复7305／9378的原FrozenPatch评分，首题在途、次题等待；固定1100文件快照与v2启动回执已保存，旧59行有效矩阵不重跑。前次v1在grade前因Docker Config API表示差异停止，无自有容器；新v2保留精确镜像及原Config字段，实际完整参考、资源和清理待题主验收。[题主当前入口](repository_work/swe_dask/current_checkpoint_20261003.md)与`runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask_same_fp_cpu_c_v1/launch_receipt_v2.json`为依据。本段旧“无CPU待办”是历史快照，不能用于当前退租判断。7138归档迁移已由GPU四档收口通知确认完成，源档仍保留；这不解除正在恢复的CPU依赖。

2026-10-03 12:50 SGT：Dask题主报告五题59行CPU矩阵、8801的29行及420份新鲜语义裁决已完成独立验收，当前无CPU作业或既定复修作业。8801的306份原件、7,202,870B已完整回收，首轮请求已由题主直接交GPU；发布侧只核最终验收及请求文件SHA，不重复题级语义审查，也不授予训练资格。

**7656的源归档依赖已解除，7138仍需保留。** 发布侧已核7656目标证据SHA、归档SHA、load退出0、精确actor118f47／grader50bca及linux/amd64；题主转述GPU明确后续UID／配方窄核从目标本地卷进行、不再依赖cpu-c。该证据只证明目标镜像供应，不代表actor开发或模型求解已通过。7138尚未下载/load，GPU仍要求保留源端。7305、9378使用来源digest，无派生归档依赖。

cpu-c整体退租仍须合并7138及其他仓库的依赖和真实现场；本段不是退租就绪声明，不启动重跑或清理。当前审计：`runs/category2_repair_20260929/publication_cpu_takeover_20261003/resource_dependencies/dask_cpu_c_dependency_20261003_v3.json`；旧v1/v2保留。

## EA69：当前CPU窄验已结束，后续材料等待正常提交

题主确认两轮CPU-A窄验自然结束、自有残留0，当前不请求新资源。真实生成的extra_css文件对Git忽略存在已证覆盖缺口，最小50键v2提案尚未正式发布；非作者正式报告现已完成，发布侧已核提案及8份资产引用SHA／size。原探针在本次读回仍为claimed，等其终态与题主核收后正常提交publish，再在固定新材料上仅补原FrozenPatch评分与CPU窄验。新50键完整评分及新grader身份尚未验证。现在无新作业或预留槽，原Qwen调查按执行端协议继续。源文件和实例保留；此题CPU结论不授权整机处置。原依赖记录`runs/category2_repair_20260929/publication_cpu_takeover_20261003/resource_dependencies/coverage_ea69_cpu_dependency_20261003_v1.json`，当前提案记录`runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/coverage_ea69_generated_css_proposal_v2/noted_proposal_v2.json`。

## 机器与并发

| 项目 | cpu-a 实测／当前安排 |
| --- | --- |
| 系统 | Ubuntu 22.04.5，KVM，x86_64 |
| 可用资源 | guest 21 vCPU、约49 GiB内存；ext4约993 GiB，初始化前空闲986 GiB |
| Docker | 28.1.1，overlay2，systemd cgroup v2；初始化时0容器、0镜像 |
| 作业上限 | 全机2个作业同时运行；每个验收作业内串行执行候选矩阵 |
| 镜像准备 | 同时最多1项，并占用上述2个作业槽之一 |
| 起步资源范围 | 普通作业按既有profile，合计峰值不超过4 CPU／8 GiB；需要更多资源先与发布线程安排独占；全局资源变更按既有授权处理，不擅改题级运行profile |

这里只按guest实际资源安排，不用API中的整机CPU／内存数字代替可用份额。新增cpu-b实测19 vCPU、24.6 GiB内存、ext4约775 GiB；cpu-c实测19 vCPU、49.3 GiB内存、ext4约775 GiB。新增两台初始化前均约767 GiB空闲。初始化时每台2个作业槽与1个镜像准备名额。cpu-b退租后仅cpu-a/c可派发：总计最多4个作业、2项镜像准备，镜像准备仍占作业槽。

## 固定分组与迁移

| 主机 | 仓库 | 题数 |
| --- | --- | ---: |
| cpu-a | Conan、Moto、Pydantic、DVC、mypy | 24 |
| cpu-b（已退租；历史分组） | coveragepy、Pillow、NumPy、Scrapy、aiohttp；当前无CPU待办 | 13 |
| cpu-c | Dask、MONAI、pandas、orange3、DataLad | 15 |

每个仓库后续作业只在仍开放的分配主机运行；原cpu-b组出现新需求时先走CPU支持请求重新分配。迁移前已在cpu-a获槽的作业自然完成，输入、镜像和历史证据保留；未获槽的请求不再重试cpu-a。题主将必要输入复制到新主机自己的包目录，逐文件核SHA；不同时在两台重跑同一候选。新机尚未开放时继续本地材料工作。

各包的`cpu_host`、`actor_gateway_port`、`actor_stub_port`在分工JSON登记。公开actor需要网关和桩两个端口，每台五个仓库各占一对18190–18199，兼容现有入口。以该登记替代先前183xx单端口预留（包括Pillow18321），不为分配问题扩公共入口规则。端口预留不表示服务已启动，额外端口由发布线程维护分配。GPU模型服务与探针仍由原第一类线程管理。

## 连接、目录与版本

当前可用发布版本、覆盖范围与真实部署主机统一见[CPU发布部署清单](cpu_release_deployments_20261003.json)。它不替代各题的固定绑定，也不表示全部草案已经生效。

**共享Git修复从第五版提供**`cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest SHA256为`80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`。三台均已核837成员大小/SHA及可信48+216读回；Git四文件逐字匹配独立审查版本，builder保持已完成真机验证的字节。此版另加入MONAI3715与NumPy078/079材料，其它题的材料变更仍以各自登记为准。后续基线作业从本版或本题已发布的更新版入口生成prepared及新作业身份，不能拼接旧prepared绝对路径或改绑旧FrozenPatch；旧尝试与已完成验收保留，不因共享部署机械重做。

第六版`cat2-cpu-r2e080087-swe8-git-20261003-v1`已在cpu-a/b验证855成员与可信48+216读回，manifest SHA256为`ab0a3a13fd65e0ea4cd60541ea3b37b01196170477e25832df246f33ea208828`。它供mypy10174、aiohttp1c1/240/618与coverage016的增量验收；Git/builder逐字继承第五版，其他题不自动换版。Moto5406 tools v3继续固定第五版，在途运行不受本发布影响。cpu-c没有本版受影响题，因此未部署第六版。

第七版`cat2-cpu-r2e088-swe12-git-20261003-v1`已在cpu-a/c完成905成员精确集合、大小/SHA及可信48+216读回，manifest SHA256为`f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`。cpu-a供Moto6114、Pydantic5662/6283及DVC5839正式验收，cpu-c供DataLad6b6f的088三方增量验收；cpu-b没有本次受影响题，保留原绑定。Git四文件、builder和manager均与第六版逐字一致。DataLad旧GPU请求继续暂停，待新noop／C-A／gold三方及非作者结果复核收口再提交新请求。题级验收未因部署自动完成，Moto5406仍使用第五版工具。材料范围与条件见[第七版发布核查](swe12_datalad088_publication_review_20261003.md)。

第八版`cat2-cpu-r2e088-swe13-git-20261003-v1`仅在cpu-a部署，923成员精确集合、大小/SHA及可信48+216读回均通过，manifest SHA256为`95ff56085fc2ccf6857829f960c23195a3dd332cfecabe8fe6b3f0c3817ebd08`。相对第七版仅Moto5134增加mixed-list兼容性P2P，2F／13P；该题仍由“负责处理第一类的模型探针”负责，不计入本次Moto六题或52题新增完成数。题主使用`--package coordination`、唯一job前缀`gpuowner-moto5134-`和`packages/coordination/moto5134/`目录，遵守相同作业槽与资源规则。新noop／gold／原a3候选内容三臂另留身份及派生关系，旧GPU FrozenPatch／SHA／分数不改绑；发布完成不代表三臂已验。其余题保持自己的固定版本，第七版在途不切换。

- 私有连接入口：被Git忽略的 `runs/category2_repair_20260929/host_setup_20261003/<cpu_host>/connection.json`。凭据不写入题卡、提交文档、作业命令参数或solver材料。
- 远端统一根：`/work/rh2-category2-20261003`。`control/`和`setup/`由发布线程维护；`releases/`由“负责处理分类二的明确问题”作为SWE/R2E共用材料发布者维护；各题主只写 `packages/<package_id>/` 和自己的作业输出。
- 后续新作业共用解释器：`runtime_cpu_v2/rh2/.venv/bin/python`，三台均已通过真实harness导入与CPU张量检查。基础仍按冻结`rh2/uv.lock`的swe/data组；补充官方CPU轮子`torch==2.13.0+cpu`、Pillow12.3.0、networkx3.6.1和setuptools83.0.0，其余基础依赖完全不变，三台完整freeze摘要相同，未安装CUDA依赖。输入锁、轮子SHA和验证原件见忽略证据根的`actor_runtime_v2/manifest.json`及各主机同名目录。
- 原`runtime/rh2/.venv/bin/python`保留供在途作业完成。实际Conan/DataLad/Pillow的CC启动暴露了原swe/data最小环境遗漏torch；失败发生在宿主导入链，零模型请求，旧证据保留，不记题目失败。v2不覆盖旧venv；导入检查通过不替代各题实际actor复验。
- 不在宿主环境editable安装活动工作区。正式运行用发布者确认的独立源码快照及材料版本，通过原runner支持的入口或明确的`PYTHONPATH`绑定；不能只clone旧HEAD，也不能各自更新共享代码。
- Claude Code准备位置：`cc/claude-code-linux-x64-2.1.205.tgz`，以npm integrity校验结果为准。这里没有为CPU机开通模型服务；公开actor检查沿用已有桩或正式授权入口。
- 首份不可变CPU候选：`releases/cat2-cpu-r2e064065-swe5-20261003-v1/`，执行源码根为其`repo/`。manifest SHA256为`282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f`。三台传输的794个成员均已核大小与SHA；三台可信读回均已通过。该版本含material_v13／pins_v14，只新增Orange22的064题面与DataLad6b6f的065隐藏测试，保留其余46个R2E条目及SWE原已接受5题。其他仓库草案没有因此自动生效，后续由共用发布者增量登记。
- 发布目录仅为宿主可信私有资产，不可整体挂给actor。运行设置`PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=<release>/repo/rh2/src`，输出写本包目录；不editable安装、不热改release、不照搬本地prepared路径。材料可信读回通过不等于真机actor、评分或探针通过。
- cpu-b已追加第二份不可变候选`cat2-cpu-r2e066068-swe5-20261003-v1`，manifest SHA256为`0ce1aaf92f625f385fdf0ed560a9f5d505e9c555c2c9a00d262d503c79f79863`；797成员大小/SHA与可信48+216读回通过。相对父版仅新增Scrapy修订066/067及coveragepy 5dbb题面068，供两包接续；其它包继续自己确认的版本，在途作业不热切。第二版校验脚本字节与父版完全一致，运输侧使用父版已绑定的校验脚本SHA，不改写发布原件。

公共Git初始化的pack表示不稳定问题已完成窄修及非作者复核，见[修复复核与适用边界](../ordinary_probe_20260929/git_pack_fix_review_20261003.md)。第五版已包含修复，前四版原件保持不变。GPU新Moto5134与R2E NumPy18b7均已通过自身原生非空工件的完整基线重建及直评；Moto正式得1但另查出候选语义回归，NumPy正式10/11得0且为测试失败，均与基础设施验收结论分开记录。若旧版CPU作业遇同类完整baseline不一致，应记为基础设施阻断，保留原候选/基线/日志并停止该运行；不能改成题目失败、忽略excluded摘要或改绑新baseline。Moto5406已发生同类旧版阻断，其新尝试从第五版及材料发布者相应工具附件接续。无关材料准备继续，GPU新模型派发状态以统一探针线程记录为准。

## 领取作业槽

R2E新镜像准备使用当前第五版中固定的`build_r2e_derived.py`（SHA256 `5af7dc214976336ea440674bc4416cfa0a805881463798e05ebbb3e33af19471`）；该文件与第四版已验字节相同。新builder调用增加`--job-prefix <本次唯一名称> --container-cpus 2 --container-memory 4g --container-pids-limit 512 --cleanup-timeout 60`，保留该题原有材料、环境、sysconfig和配方参数。已有派生镜像不因这次运输修复自动作废；在途作业不热切，题主记录新作业实际绑定。

总协调已在cpu-b真机验证：正常stdout/stderr、真实退出23、启动后1秒超时三项均通过；四个创建对象的真实HostConfig均为2 CPU／4 GiB／512进程／无网络／无挂载，builder仅清理自有容器，异主哨兵在每项检查后保留，再由探针清理。最终四个对象均确认不存在，作业槽正常释放。证据为忽略运行目录`host_setup_20261003/cpu-b/builder-daemon-20261002T174716Z/`。此验证覆盖builder的bash检查容器，**不代表Docker daemon的build过程已设置同样限额，也不是全部异常路径或题级验收的证明**。

所有Docker拉取、构建和题级运行均经同一包装器启动，不需要逐命令向用户请示：

```bash
ROOT=/work/rh2-category2-20261003
python3 "$ROOT/control/cpu_slot.py" \
  --mode run --package r2e_datalad --job datalad-6b6f-acceptance-v1 -- \
  "$ROOT/runtime_cpu_v2/rh2/.venv/bin/python" <冻结runner路径> <本次参数>
```

镜像拉取／构建使用 `--mode prepare`。退出75表示当前忙、暂停或资源余量不足，不是题目验收失败；稍后重试即可，不高频轮询。每次使用新job ID；同名记录拒绝覆盖。包装器等待命令完成并保存 `jobs/<package_id>/<job>/status.json`、`stdout.log`、`stderr.log`。需要断开SSH时，在包装器外使用既有持久启动方式；不能把内部命令变成 `docker run -d` 或“后台启动后立即退出”，否则会过早释放名额。

作业槽是合作式并发控制，不是新的评分或隔离边界。容器CPU／内存限制、技术超时、标签和清理继续由原runner负责；每个作业使用本包和尝试的唯一标签，只清理自己创建的容器／网络。发现残留、身份不符或共享运行异常时保存证据并向发布线程提交`cpu_support`请求，不做全机prune或删除他人缓存。

公平轮转：已获槽的长矩阵自然完成；同机其他仓库明确等待时，同一仓库后续最多占一个作业槽（prepare也算），把另一槽留给其他仓库。此约定是协作调度，现有包装器没有实现仓库优先级或预约，不假称有先到先得队列。2026-10-03 02:56实查cpu-a空闲、cpu-b一项coverage016矩阵、cpu-c两项Pandas50319/Dask7305作业；1秒CPU忙比例分别0.33%／1.27%／16.51%，可用内存47.99／23.26／46.15 GiB，磁盘空余950.87／748.64／713.25 GiB。这是瞬时快照，不代表长时峰值；暂不据退出75新增机器或改变题级profile。原始记录为各主机忽略证据目录的`capacity_sample_20261002T185651Z.json`，较早快照保留。

## 验证证据

本地证据根为 `runs/category2_repair_20260929/host_setup_20261003/cpu-a/`；远端安装记录位于统一根的 `setup/`。初始化输入清单记录pyproject、uv.lock、bootstrap和控制脚本SHA。初版沿旧bootstrap误带dev依赖，已在下载阶段终止；原日志／终止记录保留，正式宿主检查以 `bootstrap_cpu_only.sh` 与 `bootstrap_cpu.rc` 为准，不把初版退出算成通过。并发控制已实测：两作业满额拒绝第三个、取消后释放、镜像准备串行、一次运行与一次准备可重叠、启动失败释放名额、重复job不覆盖历史。

正式宿主检查已通过：`bootstrap_cpu.rc=0`；Docker SDK 7.1.0、Pydantic 2.13.4、SWE-bench 4.1.0、verifiers 0.1.15.dev419与PyArrow 24.0.0均可导入；CC包npm integrity一致。非root容器实测UID/GID54321、CPU配额1核、memory.max=268435456、pids.max=64，退出后本次label残留为0。汇总见忽略证据目录的 `readiness.json`、`remote_setup/container_smoke.json`、`remote_setup/pool_validation.json` 和 `cc_integrity.json`。这些只证明宿主与基础运行条件，不替代任何题级CPU验收、独立复核或模型探针。

新增cpu-b/c复用了已验证的同SHA并发包装器，分别通过真实作业入槽冒烟；两台CPU依赖导入、CC完整性和受限容器检查均通过。cpu-c初次apt安装因系统自动更新持有dpkg锁而退出100，原日志保存在远端setup/attempt1；随后以有界等锁参数正常重试成功，没有终止系统更新。各主机的连接、setup原件、readiness与release运输回执分别保存在上述忽略证据根的同名主机目录。


## 2026-10-03 发布线程接管

三机解除暂停前均再次核对：无未结束job记录、无容器和任务网络，两个作业槽及准备锁均空闲。原暂停文件已按字节归档，04:32 SGT三台门均已解除。原`cpu_slot.py`字节和并发上限不变，旧字符串coordinator仅为历史提示，不产生路由。连接/控制文件SHA、实际网络及资源原件见 `runs/category2_repair_20260929/publication_cpu_takeover_20261003/`。接管不重新运行宿主冒烟或题级矩阵；R9随后已在cpu-c部署并可信读回，929成员；仅Orange受影响三题使用，题级CPU另验。实际恢复回执见该证据目录的`resume_v1/summary.json`与各主机回执；没有新增题级作业或更改资源上限。

第九版R9于04:37在cpu-c完成部署/可信读回。实际消费registry20/pins21；manifest顶层19/20为陈旧描述，已在`publication_cpu_takeover_20261003/r9_publication_receipt.json`纠正，封存原件保留。其他仓库不自动切版。

## R10：mypy15184与DVC5839候选预检

R10 `cat2-cpu-r2e089092-swe14-preflight-20261003-v1` 已在cpu-a核对950成员及可信48/216读回，manifest `00ac5c375629f59543f548fbc7b0cb3cbe7d1418f7a956d9deebcefab2e8a87c`。mypy15184使用nested v2公开补充与精确3F/2P；DVC5839由Docker候选UID执行固定wheel预检，不增加权限、不在root切换身份。其他262个consumer不变，R2E仍实际registry20/pins21。两题fresh prepared与正式CPU结果仍由题主复验；R7/R8/R9的DVC阻断保留，不改写旧失败。

回执：`runs/category2_repair_20260929/publication_cpu_takeover_20261003/r10/`。旧包和在途绑定不变，CPU材料发布不代表普通探针或训练资格。

## R11：Dask7656与Conan13230／14177

R11 `cat2-cpu-r2e089092-swe17-dask-conan-20261003-v1` 已在cpu-a/c核对980成员及可信48/216读回，manifest `bf1d0e8a279f996a7737de775c9a30abf3401dc34840ef54bf7e56b754991bb9`。Dask7656固定E11评分环境并保持1F/48P；Conan13230为3F/34P，14177为2F/11P。97项不同受影响维护最终通过，3题prepare及264实际消费核对仅三题改变，全部公开bundle原样。回放账本不再把来源manifest写成固定本地grader镜像的期望身份，拒绝的overlay不会被后续静态检查覆盖。

题主接续正式CPU矩阵和独立结果核查；Dask预安装actor尚未由本版正式接入。回执在 `runs/category2_repair_20260929/publication_cpu_takeover_20261003/r11/`。发布不核销题级缺陷，不重跑其它题，不热换在途代码。

## CPU-b 结束派发（2026-10-03 06:04 SGT）

五仓13题已无已知CPU待办，45个作业均结束，容器/自建网络为空；派发门已封并回读三个槽锁可获得。四仓题主归档加NumPy完整救援归档已核，另回收共享control/setup/jobs。退租就绪回执：`runs/category2_repair_20260929/overnight_watch_20261003/retirement_ready_cpu-b.json`。发布者没有停止或销毁实例，实际供应商操作由巡检线程执行并核实；CPU-a/c与GPU继续。

## R12：Conan13403／11594／15422／12397

`cat2-cpu-r2e089092-swe21-conan-20261003-v1`已部署cpu-a，1020成员及48/216可信读回通过，manifest `3fe07ef04c88f9883b2bc3040cac425374cbd7bcd23041fc4280e17ef62e7987`。三个固定grader镜像实机ID准确；12397保持来源环境。新增四题消费，相对R11仅四目标题变化，旧17＋48R2E及其它题共260行不变。61项受影响维护及四prepare通过。题主继续完整CPU正负矩阵和非作者核查，actor仍source的边界、15422完整FrozenPatch要求都在逐题回执；发布者不再终审题级语义。回执：`runs/category2_repair_20260929/publication_cpu_takeover_20261003/r12/`。

## R13：Pandas48106／50319与Moto5960／6408／6185／7584

`cat2-cpu-r2e089092-swe27-pandas-moto-20261003-v1`已部署cpu-a/c，1094成员及48/216可信读回通过，manifest `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641`。三个固定grader镜像的宿主实际ID准确。仅六题消费改变，旧21与其它258题保持；公开材料全部不变。保留原件、准备、镜像配对和真实评分入口替身等受影响窄核，失败历史未覆盖。题级正式CPU矩阵及非作者验收由题主接续；评分发布不等于actor、模型或训练验收。各题回执位于 `runs/category2_repair_20260929/publication_cpu_takeover_20261003/r13/`。


## R14：DVC三题与Pydantic四题

`cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`已部署cpu-a/c，1220文件与48/216可信读回通过，manifest `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8`。cpu-a七个固定grader实际ID准确。仅七题改变、其它257题和所有公开材料保持；新矩阵和独立验收由题主执行。原E10/DVC安装、完整测试补丁和固定参考消费已接通，不据此授予探针或训练资格。回执在 `runs/category2_repair_20260929/publication_cpu_takeover_20261003/r14/`。

R13辅助Moto检查的同名JSON覆盖已用R14独立22+6记录补证，旧冻结物不回写，详 `r14/r13_moto_maintenance_evidence_correction.json`。Root首次封包前置检查误将历史失败attempt列入最终通过清单，复制前即停止；已按保留24通过及另3修正fixture通过核定、保留root失败记录。题目材料和历史评分未改。


## R15：Dask三题与MONAI两题

`cat2-cpu-r2e089092-swe39-dask-monai-20261003-v1`已部署cpu-c，1305精确成员与48/216可信回读通过，manifest `2b788d1ce84228a27894e04886ade347e91993f48ddc9bdeeb8f92de4aa92917`。cpu-c三个固定grader实际ID准确。39题累计producer；相对R14只新五题变化，259全字段及全部公开材料保持。发布仅核共用实现与材料消费；各题CPU矩阵、公开actor和非作者验收由原题主继续，不授予模型或训练资格。回执在 `runs/category2_repair_20260929/publication_cpu_takeover_20261003/r15/`。

Dask7138的本地wheel未回传，但cpu-c精确grader已实际存在；runtime按固定SHA离线安装并以候选UID预检，实际读/安装证据仍由题主取得。MONAI两题的固定镜像已实查，不等于GPU镜像存在或正式typed actor租约接通。


## R16：Dask8801完整材料与公开题面

`cat2-cpu-r2e089092-swe40-dask8801-20261003-v1`部署cpu-c，1369精确成员及48/216可信读回通过，manifest `f98eddad0c75df00e8e8352d52819d602a06d5e5ccb8d40feacb8c2658a2b80a`。累计40条SWE修订不等于40题准入；相对R15只8801消费及公开题面变，其余263全字段相同。原来源镜像/vendor/setup300/apply120/test1800及P-A=None保持。CPU-c原镜像实查不存在，由题主经slot拉取和核实际ID，不宣称镜像准备或新版CPU已通过。2F/43P、完整补丁及保留162CRLF的8563B题面固定；host匿名语义诊断工具仅宿主调查，不接自动训练reward。题主继续完整矩阵及实际actor验收，回执在 `runs/category2_repair_20260929/publication_cpu_takeover_20261003/r16/`。

封包首次预检发现R15目录多出3个运行生成pyc，原1305成员逐SHA不变；缓存已原字节隔离存证后恢复精确集合，失败不覆盖。该目录后续消费继续使用-B/PYTHONDONTWRITEBYTECODE=1。


## R17：coveragepy EA69公开要求补齐

`cat2-cpu-r2e093-swe40-coverage-ea69-20261003-v1`已部署cpu-c，1378精确成员及48/216可信读回通过，manifest `76aee53151d3b58758d00a9feb5a901b720b4b430f37d2057ed07c1ef0ce2fa6`。正式登记r2e-mr-093，仅补充保留已有.gitignore内容及重复保存后的忽略规则；旧073/074/075、49期望键、隐藏测试、runner与全部264题的32个评分spec字段相同，其它263题完整消费相同，SWE40 producer六件字节保持。原Qwen旧题面下0分与旧请求取消回执保留，不能混入新题面能力比较。发布未重验实际镜像、CPU矩阵或actor；题主沿已有固定overlay/镜像在cpu-c核新版实际首请求及必要公开操作、正负对照后自行请求GPU。回执在 `runs/category2_repair_20260929/publication_cpu_takeover_20261003/r17/`。28窄维护及受影响Ruff通过，四个辅助检查失败原件保留，最终scope05通过；发布不授予模型或训练资格。


## mypy10174一次未完成正式重评分的名额支持（08:29 SGT）

前次r8实际入槽后owner元数据检查出错，未进入正式tests；安装成功不等于评分验收。新支持 `swe-mypy10174-cpu-formal-regrade-slot-20261003` 使用已修正的固定worker86ed和原binding，仍仅一个原候选。08:28 cpu-a两槽为Pyd8567/DVC9395，当前作业自然完成；已定向通知a仓，将下一次释放的run机会给mypy单项，另一槽公平轮转、每仓最多1槽，45分钟未启动到期。它是合作约定，不是技术锁或新调度系统。真实admission及子进程确认后才收口；r13误报running已双方撤回，实际75且无admission，支持总账仍claimed。原件和实际通知在 `runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/mypy10174_formal_slot_support_v2/`。


2026-10-03 09:45 SGT：DVC9395公共保护-only诊断等待cpu-a两项既有长作业自然完成，已定向通知当前Moto/Pyd题主，将下一次释放的一项机会留给root单次prepare；另槽公平轮转。仅原300秒保护，不运行安装或测试，不取消在途。实际入槽后立即消费该窗口，最晚10:15到期；协作约定不是技术预约。原75且无job／无诊断事实保留，证据见忽略目录publication_cpu_takeover_20261003/support/cpu_a_control_surface_protect_v1/one_prepare_window_0945.json。


## R18：Moto5960／6408离线供给

`cat2-cpu-r2e093-swe40-moto-offline-20261003-v1`已部署cpu-a，1419精确成员和48/216可信读回通过，manifest `a84bdc339618e010440df3728c982b2d1d141b1f8295f69761984386ee3a512e`。两份供给均已实际COPY-only构建、以UID54321读取三wheel核SHA并清理，实际镜像ID读回准确；新增consumer只影响两Moto环境和固定wheel预检，其它262与全部264公开内容保持。原测试补丁/参考/安装命令/预算不改。独立维护26项及replay14/prepare2通过，仅是受影响接线验收。实际make init三臂、actor公开开发与非作者题级验收由Moto题主完成；未授予探针或训练资格。回执在`runs/category2_repair_20260929/publication_cpu_takeover_20261003/r18/`。


10:03 SGT：DVC9395的一次临时自然空槽机会已由`dvc9395-protect-phase-v1-20261003-07`真实消耗（prepare/slot1）。Moto和Pyd题主已实际通知恢复公平轮转；没有后续保留槽，也不停止在途题目。支持探针清理结束后释放本槽。实际入槽证据与窗口结束记录在`publication_cpu_takeover_20261003/support/cpu_a_control_surface_protect_v1/`。


10:10 SGT：DVC9395保护-only实测242.417秒，仓库chown约11.060秒、解释器前缀chown约231.108秒（宿主行到达间隔，非CPU时间）。固定R14身份与300秒、2CPU/4GiB/profile不变；两官方文件及双流完整性、精确自有容器清理核定。旧300秒失败的细分原因未知，新一次成功不代表正式矩阵恢复或训练资格。支持回执`publication_cpu_takeover_20261003/support/cpu_a_control_surface_protect_v1/dvc9395_resource_support_receipt_v1.json`直接回原题主；未改测试、安装或安全策略。


## R19：Pyd6283／Moto6114补充P2P

`cat2-cpu-r2e093-swe40-pyd6283-moto6114-20261003-v1`已部署cpu-a；1476精确成员、48/216可信读回通过，manifest `2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e`。6283保留原40后增加PrivateAttr P2P（2F39P=41），6114保留原35后增加Neptune-name start/delete（1F36P=37）。仅两题材料及身份改变，其他262完整消费和公开264保持；实际prepare、31项窄维护及4个replay入口替身通过。默认source镜像保持，显式既有derived镜像已只读核准确；两目标显式derived的账本expected manifest改为None，不新增默认typed镜像接线。实际41/37四臂、actor、非作者与GPU用途由题主继续核；6283自有CPU hold仍待共享支持，材料发布不能解除。回执在`runs/category2_repair_20260929/publication_cpu_takeover_20261003/r19/`。


## R20：8316／9395重复准备超时的有界支持

`cat2-cpu-r2e093-swe40-prepare900-20261003-v1`已部署cpu-a，1479精确成员及可信48/216读回通过；manifest `2a4ceb0315ea959232151d70f29ccc48bd34bdb0cb7dcfbb4aa177fec07bd393`。仅8316 acronym-v3＋f939镜像、9395 behavior-v2-draft＋c093镜像的env_reset准备/reset300→900；此字段覆盖现有准备/reset调用，不是只计chown的独立预算。测试/candidate/whole/cleanup预算、材料、保护权限、网络、资源和其他262题不变。5项窄维护、8路实际replay入口替身、2题prepare通过，spec及保存账本均记录900；未做新题级CPU，不能称恢复或效率改善。题主只续失败/未覆盖控制，原有效证据和旧infra/null保留；遇新infra/清理未知停派并保现场。6283仍300，其hold不会自动解除。回执在`runs/category2_repair_20260929/publication_cpu_takeover_20261003/r20/`。


## R21：Moto6114保护阶段超时的有界支持

`cat2-cpu-r2e093-swe40-moto6114-prepare900-20261003-v1`已部署cpu-a，1482精确成员及可信48/216读回通过；manifest `630f71fc1a4ae6f587f3161fae56d92927a91801ae4b08954a556ee059cada9c`。只有6114 v2材料显式选择精确1d8派生镜像、实际ID再次匹配后，env_reset准备/reset才从300变900，spec与保存账本同时记录；默认来源仍300，其余题和R20既有政策保持。实际ID不符则保存真实ID并拒绝，不应用900也不记0。5项窄维护、1题prepare与有界实际replay入口替身通过；未做新题级CPU，不能称已恢复。题主仅补exact_qwen，复用先前同材料noop0/gold1/wrong_first0；旧超时保infra/null，遇新infra/清理未知停派。actor、非作者验收与题级用途由题主继续；独立6185不受改动。回执在`runs/category2_repair_20260929/publication_cpu_takeover_20261003/r21/`。


## R22：aiohttp1c1取消清理保留测试的材料发布

`cat2-cpu-r2e094095-swe40-aio1c1-cancelled-20261003-v1`已部署cpu-a，1491精确成员及可信48/216读回通过；manifest `aaa957435ca509a7733a1965a74915b26d86a3c7d09624786755ed50c9aea6c9`。094/095替换080/081，只加一项取消时资源清理P2P，旧58键、题面、runner和reward不变；其它263完整消费、264公开材料、48gold及SWE40/R20/R21字节保持。四项窄维护及prepare通过。59键尚未实际收集，新grader/overlay尚未构建；原exact00ad仅actor可复用，不能冒充新隐藏评分镜像。题主按本回执prepare/build入口接续原五行CPU与非作者窄核；旧binding仍blocked，不追加模型采样、不改旧raw1/58。发布回执在`runs/category2_repair_20260929/publication_cpu_takeover_20261003/r22/`，不授予普通探针或训练资格。


## Pydantic8511／8567／9066：精确镜像供给

CPU-a已有三题请求中的精确Linux/amd64镜像，合并一次save/gzip并核前后ID；父作业、save和gzip均0。归档2514187661字节，SHA `b5d91c606432dc1d38970da79ec284f484407b01c6f32fa050c99efc01336d58`，仅在远端保留；GPU执行者按供给回执直迁及load一次后逐ID核对。没有新构建、consumer发布或题级CPU复跑；此前8316／6114及本次源均保留，GPU迁移未核收不自动退租或销毁。回执 `runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/pyd_three_exact_image_supply_v1/resource_support_receipt_v1.json`。

8511后续保留行为窄诊断已供给（2026-10-03 23:04 SGT快照）：CPU-a实际仍有精确df6c镜像，R14冻结入口及既有runtime可读，两作业槽与prepare锁当时均空闲，余量满足原门槛。支持已直回题主，无预留、构建、load或项目实验；题主按固定8份输入在统一槽串行验证baseline／narrow／原Qwen候选的Field工厂、约束及别名保留。实际UID／解释器／行为及清理待题主运行核验；旧173参考、raw1及FP保持，不以镜像可用解除语义缺陷。资源回执`runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/pyd8511_fieldinfo_retention_resource_v1/resource_support_receipt_v1.json`。本项是新增具体CPU需求，源与实例继续保留。


## Moto7584／Orange9b与Dask7138／Pandas48106：GPU精确镜像供给

Moto7584在cpu-a、Orange9b在cpu-c各占一次prepare槽，现已安全结束并保存精确镜像归档；父作业及save/gzip均0。Dask7138 actor＋grader和Pandas48106 grader已有题主导出归档，本次直接复用并重新核完整SHA、大小及宿主精确ID，没有重复save或构建。四题均为Linux/amd64；只交源镜像供给，GPU直迁、load及目标身份读回由GPU执行者接续，不新增consumer、不重跑题级CPU、不授予用途资格。

两份回执：`runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/moto7584_orange9b_exact_image_supply_v1/resource_support_receipt_v1.json`、`runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/dask7138_pandas48106_exact_image_supply_v1/resource_support_receipt_v1.json`。所有源镜像及归档继续保留，无自动停机或销毁。


## MONAI两题／Moto三题／DVC三题：八题精确镜像供给

八题请求的精确镜像均在源宿主实际存在，未找到匹配完整归档；cpu-a六题、cpu-c两题各占一次prepare槽，合并save以复用共享层。两父作业及save/gzip均0、导出前后ID和Linux/amd64一致；只回传小证据，大归档保留远端供GPU直接迁移。没有镜像重建、题级CPU复跑或consumer发布，不自动授予普通探针和训练用途。MONAI6975仅供当前fbfdd公有NIfTI层，旧vendor组合阻断不改变。回执`runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/remaining_eight_exact_image_supply_v1/resource_support_receipt_v1.json`。源镜像、归档与实例继续保留，GPU目标load由执行者核。


## GPU一次性归档只读直连（2026-10-03）

为避免归档经本机中转的低速，按GPU执行者本次指定条件在cpu-a/c各追加一条独立临时SSH公钥授权；仅固定GPU源IP、四个精确归档token、强制root只读wrapper，禁止任意命令／路径、PTY、转发及写操作。现有授权逐字保留，SSH主机密钥、服务与在途传输保持。入口拒绝未知／注入命令、额外参数及过期请求，允许归档头与固定文件一致（7／9项校验），不运行项目构建或题目测试。新加坡时间2026-10-03 22:00自动失效；GPU完成通知后由发布者只撤销该单key。GPU真实认证、整档SHA／大小与load另核，不能把源端配置成功当迁移完成。

受限入口、两机主机公钥、逐档既有SHA／size及撤销命令均在忽略目录回执`runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/restricted_archive_transfer_v1/restricted_transfer_receipt_v1.json`。当前两机实测主机公钥相同，保留既有值、不更换在途连接身份；客户端按各host／port严格校验并必须核归档完整SHA。没有新开HTTP、复制长期私钥或改变模型网络边界。

日期格式兼容修正：GPU首次直连认证失败；源端日志确认IP／公钥、有效授权文件及权限一致。两机OpenSSH 8.9的日期解析实际拒绝尾缀`Z`，接受14位格式；两端时区为UTC且sshd无TZ覆盖，故只将本次授权行改为`20261003140000`，截止时刻、来源限制及强制命令不变，其他授权逐字保持、无需重载sshd。[OpenSSH 8.9源码](https://raw.githubusercontent.com/openssh/openssh-portable/V_8_9_P1/misc.c)支持这一诊断。旧记录保留，新回执为同目录`restricted_transfer_receipt_v2.json`；后续仅使用`revoke_entry_v2.py`撤销。真实GPU认证与整包迁移仍待执行者验证。截止后禁止新认证／归档请求，不声称既有合法传输流会被自动终止。

2026-10-03 18:17 SGT已收口：GPU确认四份归档真实完成，发布侧核其完成回执的四个size／archiveSHA均匹配原固定输入。两机各精确撤销本次一条临时登录key，共两条，其他授权逐字保留；主机密钥、源档、镜像、实例及题级作业不动。撤销回执同目录`revocation_closed_receipt_v3.json`，不再需要等待22:00到期。归档迁移完成、目标镜像加载、题级CPU／模型结果分别验收，本次撤销不授用途资格或解除其它CPU依赖。

## Pydantic8511 v2：现存CPU-a正式材料供给

2026-10-04，R26 `cat2-cpu-r2e094095-swe40-pyd8511-fieldinfo-v2-20261004-v1` 已在cpu-a核1528成员与48/216可信读回；精确df6c评分镜像linux/amd64已存在，无build/pull/load。公开环境、E10/core2.14.5及题级预算保持。新177参考矩阵由题主经现有swe_pydantic作业槽运行，发布者没有派发或预留名额；两机global2/prepare1与共享运行环境不变。旧R14/v1的语义阻断保留，不因供给完成清空。回执：`runs/category2_repair_20260929/publication_cpu_takeover_20261003/r26/publication_receipt_v1.json`。

## 8511 v2测试目标：CPU-a材料R27

2026-10-04，R27 `cat2-cpu-r2e094095-swe40-pyd8511-fieldinfo-v2-test-target-20261004-v1` 已核1529成员与48/216可信消费。只有8511 v2三脚本原测试文件目标恢复；精确df6c评分镜像存在、未build/pull/load，公开环境/E10/core2.14.5与预算profile保持。题主按原swe_pydantic作业槽完成新固定输入和177正式矩阵，发布者没有启动项目CPU/模型或预留槽。两机global2/prepare1、共享runtime和在途任务保持。R26 hold及旧语义阻断未清。回执：`runs/category2_repair_20260929/publication_cpu_takeover_20261003/r27/publication_receipt_v1.json`。

## EA69评分51：CPU-a材料R28

2026-10-04，R28 `cat2-cpu-r2e096097-swe40-coverage-ea69-scoring51-20261004-v1` 已部署1542成员和历史overlay support，48/216可信读回通过。原e23 linux/amd64镜像现存；发布者未启新grader，不声明镜像内已有51树。题主用既有直接官方spec的精确image供给和新root restore执行完整FP补评分，实际OCI、baseline、51参考和收尾由其验收。两机global2/prepare1与在途任务不变；本次不新增模型或镜像。回执：`runs/category2_repair_20260929/publication_cpu_takeover_20261003/r28/publication_receipt_v1.json`。
