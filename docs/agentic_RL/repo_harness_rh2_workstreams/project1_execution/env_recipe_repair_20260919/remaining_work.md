# 已知问题后续修复与决策

2026-09-19 / B Codex。用户授权继续推进全部已知环境问题；以下是维修队列，不是题池准入清单。具体题号与已有证据索引见 [known_issues.json](known_issues.json)，逐类处理，不为凑全绿删测试或屏蔽错误。

**同日13:48追加授权：** 用户要求“继续修复完所有已知问题并验证和记录”，不能及时回复时由Codex作出所需决策并记录。以下原待决定项改为本批自主决策事项，不再等用户回复；[decisions.md](decisions.md)保留具体选择、理由与边界。只对本批环境维修生效，不改全局协作协议，不覆盖Claude共享代码。所有适用题均需复验或有明确未解决处置，代表题成功不算同类全部修好。

## 已批准、继续执行

**用户本轮已明确允许修订安装配方：** 保留来源原版与逐项差异，按实际仓库文件执行；测试命令、参考集合保持不变，另验证安装作用于候选。先从DVC验证，不把原安装串里的错误命令伪装成成功。原接线页的逐字安装一致性要求仅对未修订的来源配方保持；生产接入由Claude的共享代码工作与后续正式题包衔接，本批先做有版本的诊断变体。

| 类别 | 近期动作 |
| --- | --- |
| 离线安装 | 原主批133道noop有安装失败：mypy40、DVC35、Moto37、Pydantic20、Dask1。Dask已验；其余按checkout构建声明/现有环境分组，先修代表配方再逐题复验。不能用当前可编辑链接替代安装生效验证。 |
| 资产 | MONAI-1121权重、3205的MSD数据均已真实评分验证。3205由两侧下载失败恢复为noop目标接口失败、gold通过；详情见本批README。 |
| 依赖兼容 | DVC pathspec、networkx、pygit2；Dask pytest/pandas/fastparquet；MONAI NumPy/NiBabel/ITK；Moto pytest/Python/协议栈。先确认版本约束，保留目标源码，单变量或明确组合复验。 |
| 本地服务与未知原因 | 查Moto本地CORS名称/服务、SQS与HTTP读入错误、MONAI-763残留数值差异；先归因，不以改断言或屏蔽warning替代修复。 |
| 资源 | Claude负责grader回收与事实记录；其完成后复验DVC/Modin，再校准必要资源。MONAI内存与shm联合定档；诊断档位不直接成为全池默认。 |

每个问题留下原证据、修改理由、适用题/版本、真实noop/gold逐测试差异、剩余问题。准备阶段在远端联网下载；候选安装与测试继续非root、deny_all。已通过某项修复不代表安装、广泛测试或题意质量全部通过。

## 自主决策但必须保留证据的边界

1. **测试/材料修订**：MONAI helper被pytest误收集、mypy缺fixture；先恢复来源事实，给出逐文件差异。建议允许有来源的修订版，保留原版，不自动skip/删参考。已准备独立修订版，正在真实评分验证。
2. **来源标识与版本**：Unicode/转义/空格ID、Conan键碰撞、mypy gold/base不符。无碰撞的一一映射与真正改变测试/版本分开，提供逐例对照并记录自主决定；不静默unescape或用fuzz应用。
3. **服务能力**：Moto的Docker与EC2依赖。建议优先隔离服务；不开放宿主Docker socket或任意公网，不未经核对就把真实服务替换成mock。若隔离复现不能保持原行为，再讨论任务修订或当前条件不支持。

这些项目按新授权由Codex逐项决策。修订测试材料/标识时保留来源版与修订版的结果，不用删除失败断言代替修复；外部服务必须说明所复现的行为与真实服务的差别。确实无法在当前条件可靠复现时记录具体限制及恢复条件，不称为修复通过。

## 本轮机器安排

检测到Claude在独立树 `/work/claude_chainfix_20260919` 运行回收/归因对照；本批继续使用 `/work/full216_20260919/code` 冻结代码。**不在其作业期间切换metacopy。** 3205采用只有COPY新增数据文件的镜像，无RUN/chown或原前缀修改，可在内核配置保持Y时独立构建；先验证原层与代表内容一致。依赖安装类镜像等空闲窗口，沿第一批已验证的N构建/Y评分流程。

结果仍写入本批独立路径，历史证据不回写；需要比较耗时/内存时记录同期负载，不把并行时的耗时当成单变量性能结论。

**13:43 SGT 状态：** 下一批5个配方、11次真实评分已由systemd排队，等待Claude作业与容器结束后构建；包含DVC安装修订及新增依赖canary、mypy/Moto离线构建资产、MONAI NumPy、Dask pytest。执行完成不等于修复通过，仍逐条查完整安装日志与参考测试。自动巡检9-11已用官方工具恢复为每30分钟；从实际调度记录回读下次为14:08 SGT、仍属本任务，最晚09-20 12:00停止。尚未宣称本轮恢复后的首次唤醒已实际发生。

**13:48后的授权更新：** 自动巡检继续到全部已知项有处置且证据收口，替代上条旧截止/等待用户条件；仅用官方工具更新。

## 14:30 SGT 执行快照（替代上方旧排队状态）

所有作业根目录均在 `/work/env_recipe_repair_20260919/`；systemd作业仍运行时不重复启动。

| 子目录 / unit前缀 | 当前范围与状态 |
| --- | --- |
| `round2b` / `rh2-envrecipe-round2b` | 11次已收口并重放：DVC4778安装及canary、mypy11966/Moto6913安装、Dask7138 pytest、MONAI1121 NumPy均修复对应问题；MONAI helper另验。原round2构建失败保留。 |
| `inventory` / `rh2-envrepair-inventory` | 166个镜像来源/版本/构建声明检查完成，0探测错误；这是维修覆盖范围，不是166题全部不可用。 |
| `install_wave1` / `rh2-envrepair-install-wave1` | 75题149次，2个worker；只补构建wheel，源码安装命令不变。 |
| `reference_v1` / `rh2-envrepair-reference-v1` | 10题20次；精确参考绑定修订，不把旧parser重放当新版验收。 |
| `materials_v1` / `rh2-envrepair-materials-v1` | 5题9次；MONAI三个helper、mypy fixture、gold上下文。后两项等待安装批对应题完成。 |
| `pydantic_v1` / `rh2-envrepair-pydantic-v1` | 20题计划41次；先8500三个安装敏感对照成功才扩大。 |

上述后三类仍需完整日志、摘要、逐参考ID和参考外错误复核；`done.json`仅表示执行结束。新增派生镜像只COPY资产，保持metacopy=Y，不改共享内核、不动Claude代码。下一步继续DVC其余安装/依赖，Dask/MONAI兼容与Moto本地服务。遇到普通0分记录原因；fatal或清理失败保存现场、诊断，不能盲目继续派发。

**14:55追加：** Pydantic20题41次执行/日志重放完成，安装全部成功；8500新增依赖从absent变为真实site-packages。其余分数与来源对照保持（8977的旧ID问题独立处理）。`compat_v1`16题32次已开跑；`resources_v1`6题12次等reference/Pydantic完成后运行，固定Claude已修代码副本；`moto_local_v1`两题4次补loopback别名；`dvc_install_v1b`34题68次已排队，原`dvc_install_v1`只在下载阶段因NetworkX2.3无官方wheel失败，未启动评分，保留原失败。v1b改为远端下载官方sdist构建wheel，再做有记录的旧gcd兼容补丁。其余35题DVC元数据预检无直接未满足声明，但不据此代替真装。

## 15:25 SGT 最新队列

- 完成并核对：install_wave1 149行安装均成功；reference_v1 20行；Pydantic41行、组合4行；材料v1 9行、v2 2行；Moto本地别名4行、离线transport4行。范围结论见known_issues，gold得1但测试rc1仍留待处理。
- `dvc_install_v1c`在跑34题68行：已修旧AWS CLI/SDK不一致；NetworkX兼容函数与Python3.8原函数2304组输入对照一致。v1无wheel、v1b SDK冲突的失败保留。
- `compat_v2b`在跑4题8行：8792已完整通过；6801仍两项参考外失败。接着需处理MONAI3566 ITK5.2与Moto5134 SQS真实协议边界。
- `resources_v1`已确认6298两侧无OOM/PID拒绝且gold全过，继续其它四个Modin和MONAI763。
- `python311_v1b`恢复三题旧Python环境；首版准备被kill，保留失败证据。新准备预算12GiB，不是评分预算。
- `moto_docker_probe`只探测无宿主socket、非privileged、非root侧车；用户命名空间可用，默认vpnkit缺TUN，继续host网络命名空间内的rootless服务。外层仍network=none，不开放公网或宿主挂载。
- 当前暂停项不是等用户：Docker隔离能力、MONAI763数值残留、依赖组合残留由本批继续决策诊断。所有新根目录由systemd管理，先看status/done/failed，不能重复启动或拿done代替审阅。

## 16:00 SGT 最新续查入口

已审阅通过：Python3.11三题6次、Dask最终六题组合、Moto SQS协议2次；详见known_issues及analysis文件。

继续巡检`dvc_install_v1c`、`resources_v1`、`itk_v2`、`dvc2231_v3`、`moto_docker_v3`、`numeric_v1c`。v1/v2失败均保留，不重启相同目录。DVC2231修订版依赖decorator；准备派生镜像时须显式PIP_NO_INDEX=0，评分仍离线。

Modin5940 noop完成3087项收集；目标SQL失败之外还有7个S3依赖/标记异常。源码moto5不支持旧`moto_server s3`CLI；公开Parquet/JSON当前403，NOAA1788.csv当前404，探测证据在modin_s3_probe。不能把断网下两侧同报错的eval_io视为读数据成功，也不能为全绿凭空重造原资产；继续审阅gold与其它Modin后决定适用环境或隔离处置。Ray还报/tmp接近1GiB容量上限；没有自动抬全池资源。

## 16:12 SGT 续查顺序（覆盖前面旧队列）

1. **正在运行**：`resources_v1`（Modin5940 gold后还排6400/6780/6937和MONAI763）；`numeric_v1c`（16GiB、3小时gold，观察实际CPU/内存，不因pytest缓冲没有日志就重启）；`pandas_meta_v1`（安装会重编译两次）；`dvc_tail_v1`（5822/9395）。不要重启旧失败目录。
2. **已审阅**：DVC主批68行，除了2231（后续已修）、5822/9395（尾批）之外都满足完整安装/gold退出0；Moto Docker v4完整gold22pass，noop仍目标失败；ITK v2完整gold26pass；dvc2231_v3完整gold23pass。
3. **具体遗留**：5940 S3公共资产403/404、旧Moto CLI与strict xfail；原始S3数据不能凭空替换后冒充原口径。16GiB MONAI CPU试验尚未得到数值结论。必要处置由本批自主记录，不等用户。
4. 每个完成批先rsync（排除code/context/assets/wheels/大wheel），用`reconcile.py --batch <name>`重放；有reference_bindings_v1.json则显式传`--bindings`。然后更新known_issues与`build_repair_catalog.py`。目录不会把done视为验收。
5. `repair_catalog.json`保存输入镜像/脚本/资源与逐题两侧结果；mypy11352 gold仅重写上下文，复用同镜像、同scripts_digest、同policy的已测noop，三项均已代码断言；不重跑完全相同条件。旧pre_test_errors包含git diff的ERROR常量字面量，目录只在真实安装时间标记内识别ERROR，不把它们误报为安装失败。

服务版仍需正式题包/actor接入和隔离边界审查；没有修改Claude拥有的生产代码、P-A资格或二值奖励。机器保留运行。

## 16:29 SGT 当前执行入口（替代上方旧队列）

- `numeric_v1c`已结束；真实部分训练数值进入原容差，但内部测试限时仍为1800秒。`numeric_v1d`已启动，显式测试10800秒/总11400秒，4CPU、16GiB、shm1GiB，先gold再noop。读`diagnostic_test_budget.json`及实际policy确认，不再只看CLI总预算。
- `resources_v1`继续余下Modin及MONAI原torch资源对照。5940 gold有真实`/tmp`耗尽及测试超时；`modin5940_resources_v2`已准备，等待整批结束后做8GiB内存、4GiB临时盘和3600秒测试的两侧对照。S3问题不随资源修复自动解决。
- `pandas_meta_v1`仍在gold重编译/测试；DVC尾批已经全部审阅通过。
- 完成新批后同步、reconcile重放、更新目录与决策；部分日志只表示未知完整性，不把参考缺席当“未执行”。不得重复启动正在运行的unit。

## 16:45 SGT 当前增量

- **已确认161/166题的最终环境对照；5题仍开放。** Modin6400 gold702项通过、noop仅目标1fail；6780资源恢复后发现pytest8的28项异常传播问题和3个转义ID，`modin6780_compat_v1`正在用pytest7与精确绑定复验。独立小探针已证实pytest8/7的异常行为差异。
- Pandas48106 v1 gold1044项通过，但pip check仍报三个既有冲突。v2预检另发现gcsfs与fsspec锁版本，已在v3成组固定。**`pandas_meta_v3`元数据预检通过，正在真实两侧编译/评分**；旧v2准备失败保留，不重启。
- `numeric_v1d`测试10800秒与实际4CPU/16GiB/shm1GiB已回读验证；实际TensorBoard持续增加，不能以pytest缓冲判断挂起。`resources_v1`仍在6937，之后有MONAI原torch资源对照；`modin5940_resources_v2`继续等待该批，勿重复启动。
- 新完成批照前述同步/reconcile/目录流程收口；新主线状态优先于自动化prompt里的旧快照。远端`frozen_sources/`另外保留真实执行代码与依赖版本，机器删除后也可查到实际方法，不只留代码摘要。

## 16:55 SGT 下一次续查（以本段为准）

1. `modin6780_compat_v1`已完整复核：noop仅目标1fail，gold3227pass/6xfail，参考缺席0，安装/退出/清理正常。当前目录162题验证、2题完整复验中、2题原材料暂隔离。
2. `pandas_meta_v3`的预检及真实noop安装均无依赖冲突，gold仍在重编译；完成后带其bindings重放。`numeric_v1d`仍gold实际训练，测试10800秒已确认；不要改断言或因日志缓冲杀进程。
3. `resources_v1`6937的1GiB `/tmp`也已实际耗尽（宿主statvfs可用字节0），保存本批结果；后面还有MONAI原Torch对照。`modin5940_resources_v2`等该批完成后跑资源对照。
4. **新队列`modin_s3_compat_v1`**：先6937，等resources_v1结束；再5940，等modin5940_resources_v2结束。恢复Moto4.2.14的原CLI，加明确资源预算，仍完整原测试。独立候选UID/断网S3真实读写探针已通过；不能用小探针核销整题。
5. E23已自主决定暂隔离这两题的当前材料版本；具体条件见dispositions。它们仍必须跑完、审阅资源/服务对照，再收口证据，**不能因目录有隔离状态就现在暂停自动化**。如之后发现可追溯的原资产或上游本地材料替代，可另立有来源的修订版，不假称原版恢复。
6. 宿主资源观察器`rh2-envrepair-resource-observer2-20260919`每15秒记录cgroup、tmp/shm实际容量及同期负载，输出`resource_observer_1655.jsonl`；所有列出的批结束会自行退出。旧1650采样保留，切换观察器未中断任何评分。不要把采样峰值当不存在采样间隙的全程证明。

## 17:09 SGT 最新入口

- **163题已验，MONAI763一题继续复验，Modin两题原材料暂隔离。** Pandas v3两侧安装/pip check/日志/清理已核验，gold1044pass、noop目标16fail；`analysis_2.json`已入目录，不必再跑。
- `numeric_v1d`gold已结束：参考9项通过，但第1轮训练通过数值断言后被NiBabel5拒绝int64，完整测试仍1fail；noop在跑。新`numeric_v1e`合并NiBabel4.0.2，等v1d结束后执行完整gold/noop，保留4CPU/16GiB及显式测试10800秒。
- `resources_v1`、`modin5940_resources_v2`、`modin_s3_compat_v1`继续按上一节依赖顺序；隔离不代表组件对照已完成。不要重跑旧失败目录。
- 资源观察器现为`rh2-envrepair-resource-observer3-20260919`，输出`resource_observer_1705.jsonl`，从远端根`resource_observer_batches.json`读取覆盖批。后续新增批只更新该JSON，无需再重启观察器；旧采样均保留，评分未中断。
- 所有新批结束后按原步骤同步、reconcile、逐项审阅、更新目录/决定；确认没有待审的在跑批或证据缺口之后才暂停自动化。

## 17:48 SGT 巡检入口

- 自动化本次确于17:42触发，调度器回读下一次18:12；每30分钟配置正确，继续保留。
- `numeric_v1d`两侧已结束并重放：gold参考9项通过，但完整测试1fail；noop目标失败，另有相同NiBabel错误。不能核销此版。其45份证据已与远端逐文件核对。`numeric_v1e`已自动接续gold，实际CPU持续工作，观察到的OOM/PID拒绝均为0；完整多轮训练尚未结束。
- `resources_v1`已到最后MONAI原Torch资源对照。6937两侧完整日志确认gold425fail/19error、noop426fail/19error；全部参考键都解析到，失败集中伴随1GiB临时盘耗尽、Ray写盘/worker错误及19处旧Moto服务启动错误，不能归为模型失败。`analysis_10.json`与`inspection_1748.json`保存细账；新的资源/Moto组合继续按既定依赖等待，勿重复启动。
- 163题通过、1题复验、2题原材料暂隔离的处置不变。仍须等所有已派发批结束并审阅，才能收口或暂停巡检。

## 18:27 SGT 当前队列

- `resources_v1`整批12行已结束、重放和审阅，149份证据已SHA256对账。最后MONAI原Torch/8GiB两侧均内部1800秒超时，无OOM/PID拒绝、清理成功；部分日志不支持完整参考状态结论。不是0分。无需重跑此资源批。
- `modin5940_resources_v2`与`modin_s3_compat_v1`的6937两侧对照已经自动启动；当前均为noop，真实policy已确认8GiB/2CPU/4GiB tmp。S3批的5940仍按计划等资源v2结束。
- `numeric_v1e`仍gold：TensorBoard第一轮60步和3次验证完整，已进入第二轮并走完60步，原NiBabel报错点已经越过；这不是完整测试通过。第三轮使用CacheDataset，继续观察内存和最终断言，不调容差/预算、不因pytest缓冲重启。进度证据为该批`live_training_progress_1823.json`。
- 已验证163题、1题复验、2题原材料暂隔离不变。观察器继续覆盖三批；本次18:21实际自动触发已记录，后续以自动化回读与文件最新状态为准。

## 19:13 SGT 重要变更与续查

1. 先读[runtime_findings_1900.md](runtime_findings_1900.md)。MONAI v1e gold被另一个manager的3600秒孤儿清扫误删，已确认容器不存在；不是OOM或完整测试失败。原noop已经自动启动，继续保存这条有效在跑对照，不重复派发。
2. `numeric_v1f`已配置独立label命名空间，等待v1e结束后只补gold；镜像原样复用。是否复用v1e noop由完整日志、清理及五项输入等价检查决定。
3. S3 v1 noop真实触PID512；父派发器处于SIGSTOP，当前driver继续按3600秒完成收口。**不要SIGCONT恢复旧派发**。`rh2-envrepair-retire-s3-v1-20260919`等其driver退出、实际容器移除且收口正常后，结束父进程并登记superseded/未执行case；若有retire_superseded_s3_failed.json，先查原因，不能绕过。
4. `modin_s3_compat_v2`试PID1024，其余原测试/资源不动；6937复用已准备的Moto4镜像，随后5940等resource_v2结束。新批都有独立命名空间。`modin5940_resources_v2`当前gold仍继续。
5. 新runner检查manager_close，不只看candidate cleanup。reconcile根据退出码和结束标记标完整性，避免中途被删但log_partial=false时误报完整。已回查163题326条收口，无同类问题。生产代码未修，本批不代替A的链路修复。

**19:20补充：** `modin5940_resources_v2`已完整审阅：gold2640pass/6fail/2error（余项全S3），noop比gold多4项目标失败；两侧无ENOSPC、tmp采样最少约3.0GiB可用、manager收口干净。资源不足已消除，S3依赖/材料仍待v2，不能把整题标通过。无需再跑资源v2。


## 20:13 SGT 当前入口

1. **MONAI v1e已结束：** gold为外部误删、不可验收；noop参考目标1fail/P2P8pass，但全测试2fail/8pass，另有3D推理均值容差失败。已同步重放、收口核对；不要再写“只有目标失败”。v1f gold复用同一镜像/配置，第一轮60步及3次验证已走完，第二轮继续。完整gold尚未知，不改数值容差。
2. **S3 v1已安全退役：** 当前noop3600秒超时、PID拒绝，manager/候选收口均干净且实际容器消失；其余三条没有执行。分析`analysis_1.json`是部分日志，不能按MISSING认定未执行。
3. **S3 v2的容量假设已修正：** PID1024仍停，宿主证据和独立探针确认6937未消费Moto stderr管道导致阻塞。小探针读走日志即恢复，文件路由4096请求/对象读写通过。原v2父派发SIGSTOP，当前noop按3600秒收口；`retire_superseded_s3_v2.py`完成核对后退役，不手动恢复。若`retire_superseded_s3_v2_failed.json`出现，先诊断，不能绕过。
4. **新`modin_s3_compat_v3`：** 等v2安全退役后做两题完整noop/gold。6937只给固定Moto4入口包装文件日志，PID回512；5940原本DEVNULL，不加wrapper，只完成Moto4兼容对照。均独立label命名空间、2CPU/8GiB/4GiBtmp/test3600/whole4200；观察器名单已加入v3。原测试、断言、参考及材料隔离E23保持。
5. `numeric_v1e`及旧S3 v1新增71份结束批证据已远端/本地SHA对账，共6365份206.3MB。继续同步/审阅v2、v3、v1f；163题已验证、1题复验、2题原材料暂隔离不变。生产清扫/收口问题未修，不以实验隔离宣称链路验收。


**20:18收口增量：** S3 v2已于20:12安全退役并重放：安装0、测试3600秒超时、rewardNone；末期PID570但无拒绝/无OOM，候选及manager清理干净。v3已自动开始6937 noop，真实PID512/8GiB/2CPU/4GiB tmp及独立label已回读；后续检查wrapper安装记录和完整测试结果。当前只剩v1f与v3活动。v2与5个服务探针版本的49份证据新完成SHA对账，累计6414份207.1MB；早期探针失败原因保留，不算评分结果。材料隔离仍不解除。


本次自动唤醒实际为19:52:34 SGT。官方工具已更新为以上最新队列，回读仍为本任务、ACTIVE、每30分钟；调度器当前next_run_at为20:22:34 SGT（计划时间，实际触发另记）。v3候选容器内已回读日志wrapper和安装退出0，证据`live_route_check_2018.json`；不能据此预先算整题通过。


## 20:58 SGT 当前队列

- v3的6937 noop已完整重放/审阅：1494秒，9fail/3074pass；参考目标1fail、P2P2354pass、无参考缺席。PID采样峰值467、无拒绝/OOM，服务日志91989字节，候选和manager收口正常。8个非参考失败分为4个旧CSV strict XPASS、4个Parquet连接5555被拒；不可误写成全测试只有目标失败。
- E27：6937实际服务监听5500而storage_options配置5555。只修该fixture的端口计算，保留原断言/命令/参考；来源前后文件、diff、AST与摘要在新`modin_s3_compat_v4`。5940本就两侧5555，且stderr=DEVNULL，不套用6937两种修订。
- v4已排队等v3整批完成，再跑6937完整两侧；继承同一镜像、Moto4、日志修复及PID512/8GiB/2CPU/4GiBtmp、test3600/whole4200，使用独立label。观察器名单已加入。fixture通过诊断trusted_setup_append施加，正式采用仍要冻结版本，不是已接入生产。
- v3继续6937gold，随后5940两侧，不重复启动或中断。MONAI v1f已进入第三轮CacheDataset：前两轮各60步/3验证，20:50第三轮40步/1验证；仍有真实CPU活动，无观察到的资源终止。等完整测试退出，不因缓冲或超过一小时重启，不改容差。
- 当前仍163已验证、1复验、2原材料隔离。原CSV失效/strict xfail处置E23不变；端口及日志修复不自动恢复原资产。继续同步、重放、完整结果与资源/清理审阅；本轮尚无新完整批可入结束批SHA清单。

本次自动唤醒实际20:48:34 SGT；官方更新后回读仍为本任务、ACTIVE、每30分钟，next_run_at=21:18:34 SGT。v4状态已核实为waiting_for_batch(v3)，未重复派发；服务日志后观测JSON可解码，已随账本保存。资源汇总仅筛评分容器，排除候选准备容器；本条tmp采样最低可用约1.90GiB。


## 21:46 SGT 当前队列

- **MONAI763已收口，不重跑。** v1f gold完整10pass/5431秒；与v1e noop的镜像、脚本、身份、资源和预算五项完全相同，日志/安装/两层清理通过。noop为2fail/8pass，额外3D均值失败在gold消失；不改容差，不声称多次随机稳定性验证。目录现为164验证、2原材料隔离。30份新结束批证据已SHA对账，总计6444份207.3MB。
- **v3仍5940gold；6937两侧已审阅。** 6937 gold8fail/3075pass，noop9fail/3074pass，余项都是4CSV材料+4端口配置。PID512足够完成本对照，采样无拒绝/OOM，原日志阻塞已消除。5940 noop12fail/2636pass，另发现两项Ray缺模拟S3凭据，不能统称原数据不可用。
- **v4/v5已排队等v3整批done。** v4仅6937修fixture端口，v5仅5940提前导出来源假凭据；均完整noop/gold、独立label、PID512/2CPU/8GiB/4GiBtmp/test3600/whole4200，观察器动态名单已更新。v5复用镜像`sha256:151cb93a…`，不是缺Moto4 wheel的旧基础镜像。运行时核对实际修订及环境；不启用CI、不开放网络。
- v3/v4/v5所有已派发对照结束后，重放完整日志，逐项检查安装、参考、全测试、资源与两层清理，再更新目录与材料隔离记录。原始CSV/Parquet等资产隔离继续；v4/v5改善本地服务不能自动核销原资产。生产清扫/日志完整性/manager_close问题仍单列交接，未修改生产代码。

本次自动唤醒实际为21:32:05 SGT；后续自动化计划时间将在官方工具回读后补记。

官方工具已更新最新队列；回读仍为本任务、ACTIVE、每30分钟，next_run_at=2026-09-19T22:02:04.977000+08:00（计划时间，实际触发另记）。


## 22:32 SGT 当前队列

1. v3整批4条已完整审阅、远端/本地SHA一致；无需重跑。5940 gold的目标4项通过但原Parquet P2P1fail，完整8fail/2640pass，均已分类。新增93份结束批/对象微探针证据，累计6537份210.3MB。
2. v4（6937端口）当前gold。noop1128秒完整14fail/3069pass，9项新显露为6个无Ray凭据+3个worker403，另有CSV4/目标1；2个object读取从失败变通过。端口摘要实际匹配，无资源终止或清理问题。
3. v5（5940凭据）当前gold。noop1633秒完整10fail/2638pass；两项本地S3写入/读回已过，余项为4目标+6原材料，不是新的环境故障。等gold完整结果再核销凭据组合。
4. v6（6937端口+凭据）已排队，等v4整批done后完整noop/gold；只有提前导出来源假凭据这一新增因素，不改ACL、断言或参考。复用v4同一镜像/端口/日志，独立label、原2CPU/8GiB/4GiBtmp/PID512/test3600/whole4200；观察器名单已加入。
5. E29对匿名读作明确处置：源私有对象匿名403而带假凭据能真读，独立public-read微探针能改变这一点，但整题不改ACL。保持异常一致与内容读取两种证据分开，原材料仍隔离；不得因报PASSED就说读过数据。

本次实际自动唤醒22:19:05 SGT。164个已验证题不重跑；生产清扫/日志/收口问题仍未修。继续完成v4/v5/v6及证据审阅后再考虑暂停。


**22:34 SGT续记：** v4整批已完成、重放与审阅；gold完整1036秒13fail/3070pass，恰比noop少原目标失败，余6NoCredentials/3worker403/4CSV。两侧安装/完整日志/清理正常；gold采样峰值4.56GiB、PID465、无观察OOM/拒绝、tmp至少约2.02GiB。v6已经接续noop，实际镜像/fixture摘要/凭据标记/安装0/独立label与资源均已回读，证据inspection_2235.json。现在只剩v5 gold与v6两侧；v4不要重跑。结束批证据增至6588份、212.1MB，SHA无差异。

官方工具已更新为v5/v6最新队列；回读仍为本任务、ACTIVE、每30分钟，next_run_at=2026-09-19T22:49:05.088000+08:00（计划时间，实际触发另记）。


## 23:20 SGT 最终收口（替代全部旧队列）

- 自动化本次实际于23:06:35触发。最后v6 gold于23:13结束，23:14宿主检查无实验进程、无任何Docker容器；观察器自然退出。历史failed unit保留证据、不重启，均已对应后继修订。
- v5两侧已完整审阅：5940 gold6fail/2642pass，余4CSV旧材料+2公共Parquet；两项本地S3直接写读已修复。v6两侧也完整：6937 gold4fail/3079pass，余4CSV，9项凭据/worker403失败消失。逐ID状态对照、资源和两层清理记录均已保存；原材料隔离不解除。
- 最终目录164 verified_environment_pair、2 held_source_material。两题的component_runs_still_to_review均为空；所有已知环境项有验证结论或明确处置。生产清扫、日志完整性和manager_close问题另行交接，本批未改生产实现。正式题包/actor接入、题意质量和能力筛查不在本批验收范围。
- 新增94份结束批证据已SHA对账，分批独立文件累计6682份215.1MB；最终全量清单另覆盖根目录资源采样/检查记录等，共7151份221.0MB，零差异。两种计数有重叠，不能相加。3份真实源码归档及既有清单的排除项另外核对，历史摘要无变化。总核对文件closure_audit_final.json。
- 当前没有待执行或待审阅实验；满足暂停自动化条件。保持实例运行，不重跑已验证组合，不继续向隔离题盲目派发。暂停结果随后登记。

官方工具已于23:21 SGT暂停9-11；只读数据库回验status=PAUSED、next_run_at=null、任务归属未变。实例仍运行。

## 23:38 SGT 删除实例前复核

用户询问能否删除。重新SSH核实：无运行中rh2作业、无实验进程、Docker无容器；自动化仍PAUSED且无下一次执行。补回此前context/assets排除规则中的235个小型构建文件及399个镜像身份元数据，归档及逐成员SHA核验通过，见本地release_backup_20260919/local_verification.json。可删除本实例；本次没有代为删除。大型派生镜像、wheel/权重等下载缓存未回传，下次须按记录重新构建/下载，不能理解为完整机器快照。
