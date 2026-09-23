# 本批环境维修决策

2026-09-19 / Codex。用户已授权自主处理本批所需决策；原材料与历史结果不回写。本文只记具体选择，不修改全局权限或正式训练配方。

| 编号 | 决定与理由 | 验证与状态 |
| --- | --- | --- |
| E01 | DVC保留来源安装串，新增按实际requirements文件及真实extras执行的修订版；不存在的可选文件明确记缺席，不假装安装成功。来源错误不应每次重跑。用户已明确批准。 | round2b中4778三次安装均成功：noop仍暴露目标缺陷、gold通过、新增候选依赖从缺席变为实际安装；其余35题范围内继续逐版本处理。 |
| E02 | MONAI公共权重/数据在准备时下载、固定摘要，原测试保持离线访问相同资产。无需让agent或测试访问公网。 | 1121权重、3205数据各2次真实评分已验证；1121还有独立兼容/收集问题。 |
| E03 | 按仓库与源码版本确定依赖组合，先代表题诊断，再对所有适用已知题复验；不把同仓库视为同配方。 | known_issues.json保存题级范围，后续追加实测。 |
| E04 | 参考ID修订优先恢复无损完整标识；必须核验一一对应及状态一致。碰撞不能用字符串替换掩盖；保留原来源分数并单列修订结果。 | 逐例核对中；尚未改生产parser或正式题包。 |
| E05 | helper误收集、缺fixture、gold/base不符按来源证据做最小材料修订；不修改目标断言或用fuzz模糊应用。确认无法恢复才记录当前版本不支持及恢复条件。 | 逐例核对中；尚未把材料问题标为修复完成。 |
| E06 | Moto所需本地服务先恢复原服务启动/名称解析；Docker使用隔离服务且不连接宿主socket。EC2测试先查实际网络语义，不将任意mock响应当作等价环境。 | 诊断中；确实依赖不稳定外部行为时另列版本化处置。 |
| E07 | 10题的16个旧参考键绑定到21个完整pytest nodeID，运行时只用冻结的精确映射。Pandas/Conan的截断碰撞保留来源参考组计数，但该组所有原始成员都成功才通过；缺席不算成功，避免覆盖顺序决定分数。 | 20份历史日志重放及缺成员/失败覆盖反例已验；20次fresh真实评分进行中。原始与修订分数并存。这不解决候选stdout伪造。 |
| E08 | mypy/Moto离线构建依赖按每个镜像实际版本与源码build-system要求固定；只添加wheel缓存，保留原安装命令。代表成功后扩到适用题。 | 两代表已验，另75题149次进行中；11352暂只跑noop，gold上下文修订另验。 |
| E09 | MONAI三题为辅助函数增加`__test__ = False`，仍由真实测试调用，断言不变；mypy10308补回原修复提交的fixture；11352只重写gold的一条上下文行，增删代码逐字相同，不用fuzz。 | 私有测试材料独立版本化，新增9次真实评分进行中。诊断spec覆写不能替代正式题包重新冻结。 |
| E10 | Pydantic把每次执行的开发者全套bootstrap改为安装候选项目及其testing/testing-extra依赖；文档、lint、Git pre-commit初始化留在环境准备。测试命令与参考集合不变。新下载的构建后端固定版本/摘要，不冒称历史原版。 | 先8500 noop/gold/新增依赖canary，安装与对照全通过后再扩其余19题；保留来源命令和逐题修订JSON。 |

| E11 | 16题依赖兼容对照先只改变已定位的API版本边界：pytest7、历史pandas、NiBabel4/ITK5.3、pygit2旧常量，以及Moto的旧SQS/HTTP协议栈。COPY资产后以候选身份离线安装，保留原测试和来源安装串；兼容安装前后输出实际版本。 | 已排队32次；这些是待验证假设，不能仅凭gold通过核销：检查新增失败、目标noop、原安装错误。urllib3旧行为只代表历史任务配方，不宣称修正Moto本身的HTTP协议缺陷。 |

| E12 | Modin先保持Ray和PID512，只把`MODIN_CPUS`限制为容器实际2核；使用Claude已修`--init`代码的独立快照，不回写两方代码。MONAI763用已有8GiB/1GiB shm配方联合复验，不设为全池默认。 | 6题12次排队；宿主独立采样memory/pids事件及峰值。若首个Modin仍infra，先解释再扩大。资源事实未知不当作零。 |

| E13 | DVC其余34题按真实checkout安装项目及存在的测试requirements，只请求真实extras；基线元数据声明满足只是预检，仍逐题真装。Python3.9与NetworkX2.3的冲突使用`2.3+rh2.1`兼容wheel，保留旧gcd符号/Euclid行为，不修改DVC或测试、不违反`networkx<2.4`约束。 | 35题元数据预检完成；34题68次待执行。已实测直接换math.gcd会改变负数符号，因此弃用该简化；兼容代码及上游/修订wheel摘要另记。DVC2141改用Claude已修代码副本；4778三次既有验证复用。 |

| E14 | Moto6121/6157只补`testcors.localhost→127.0.0.1`；源码自己启动6789端口的ThreadedMotoServer，不需要公网或外部服务。 | 4次真实评分进行中；生产环境包还需把相同公开别名提供给rollout，便于agent自行运行本地测试。 |

| E15 | Moto4799/4833的两个network测试是在证明mock启停前后行为，原版还依赖真实AWS对假凭据返回固定AuthFailure。新增明确的离线材料版：在底层HTTP transport返回固定错误，Moto before-send拦截链仍真实执行，原函数体/断言保留并新增恰好一次到达transport的断言。 | 4次真实评分待验证。这个版本不验证真实AWS认证服务；原版及其网络失败保留，不冒称官方联网口径等价。没有放宽公网或把EndpointConnectionError视为通过。 |

每项核销必须有具体运行或可重建的静态证据。仍在排队、只在代表题通过、代码待正式接入和无法复现，分别记录，不合并为“完成”。

| E16 | Moto4975/5347/5980恢复Python3.11.9，库版本沿镜像固定、pytest用7.4.4；新解释器前缀独立准备，安装/测试仍候选身份、断网。原用例明确断言无警告，不能用过滤Python3.12弃用警告代替环境修复。 | 准备与真实对照进行中；4GiB准备进程被kill的失败保留，改libmamba/12GiB准备预算，评分不抬内存。 |

**15:25复核更新：** E07的10题20次真实参考绑定全部通过；E08的75题149次安装均成功，与两代表合并覆盖mypy40/Moto37。E09中10308先前漏补第二份typing fixture，现按同一上游提交补齐，gold两项全通过。E10全部20题41次安装通过，8977再与绑定合并复验通过。E14四次gold完整通过；E15四次离线修订对照通过，其真实AWS边界保持。E11继续保留失败配方：6801仍两项参考外失败；3566 ITK5.3不足；5134 SDK仍不兼容。

| E17 | Moto7105使用每次评分独享的rootless Docker侧车：UID1000、无privileged、无宿主bind/socket，与grader共享原network=none命名空间，只监听loopback。准备时固定busybox/amazonlinux镜像，评分时载入；外层另限1CPU/2GiB/PID512。 | rootless daemon在该主机已启动；下一步先实跑嵌套容器，再真实noop/gold。侧车为允许用户namespace/内部挂载而放宽自身seccomp/AppArmor/mount masks，仅保留SETUID/SETGID；grader权限不变。这是明确的隔离能力变体，尚未作为生产安全边界验收。Docker匿名状态卷随本次侧车删除。依据：[Docker rootless说明](https://docs.docker.com/engine/security/rootless/tips/)。 |

| E18 | MONAI763数值回归先按源码CI明确的torch1.4做单依赖CPU对照，保留当前NumPy/测试/断言；该源码只在GPU跑完整集成测试、CPU用quick，不能先假定CPU数值必然可复现。 | 先一条gold真实RH2，8GiB/1GiB shm、2CPU；诊断评分预算3小时容纳原测试3次训练，不能把这个预算当正式全池默认。若仍不等价，记录具体GPU/历史依赖恢复条件，不改目标数值或随意加容差。 |

**15:55补充验证与处置：** E11的Dask六题最终组合、Moto三题协议栈全部完成真实noop/gold；E16三题gold完整测试通过。ITK5.2依赖的`np.bool`需要NumPy1.23.5，继续组合复验。DVC2231另缺NetworkX依赖decorator，补固定4.4.2。旧失败变体保留。

**E17修订：** Docker28.1.1的`fillRootlessVersion`会直接读取空的host网络驱动，导致SDK的`/version`请求panic；CLI info/exec成功不足以验收。v3改回镜像自带vpnkit，侧车仅添加TUN设备、loopback端口转发，外层仍无网络。新增真实version预检，不伪造API响应。v2因镜像没有slirp4netns在预检结束，未执行评分。源码依据：[Moby v28.1.1](https://github.com/moby/moby/blob/v28.1.1/daemon/info_unix.go)。

**E18资源补充：** 补six1.16/Pillow9.5后，旧Torch CPU运行在8GiB处真实OOM（峰值8192MiB、oom_kill=1、rc137），不是模型失败。只对该诊断升16GiB继续验证，保留3小时上限；不调数值断言，不设为训练默认。

| E19 | Pandas48106安装末rc0仍报两项依赖冲突：GeoPandas缺Fiona、fastparquet2024要求正式pandas>=1.5而题目是1.5.dev。补Fiona1.9.6及两项缺依赖，fastparquet固定0.8.3（声明pandas>=1.1），保留被测pandas真实开发版本。 | 结合参考绑定重新编译/评分，安装末运行pip check。不是用rc0忽略冲突，也不改被测包版本元数据。 |

**E17再次补齐实际能力：** v3的版本API已恢复，但AWS Batch还传入`host-gateway`；先前关闭默认bridge使真实容器start失败。v4恢复仅位于rootless命名空间内的默认bridge，外层无网络、无宿主socket不变；预检增加与测试一致的add-host并运行实际嵌套容器。预检通过也仍需完整gold测试。

**16:10 E13复核：** DVC34题68次全部执行结束；2231后续已修。5822完整测试仍有6项参考外失败，定位为Moto2.0.5依赖responses旧私有API、pygit2移除了常量；9395是本批下载器按宿主CPython3.10下载了wheel，而题目为3.9，修正按目标解释器下载。两题在`dvc_tail_v1`合并复验。首份该批recipe的reason误写Moto1.3.14，仅说明文字错误；真实版本证据是2.0.5，实际pin不受影响，本地说明已更正，不回写历史运行审计。

**E17验证完成：** `moto_docker_v4`中noop目标失败保留，gold完整22项通过、安装rc0；两侧真实Docker服务、嵌套容器、loopback API和双容器清理均通过。侧车额外1CPU/2GiB的预算须单列，未采到最终峰值，不能把grader峰值当总成本。未作为生产隔离边界验收。

**16:16 E13收口：** dvc_tail_v1四行完整复核：5822 gold48pass/24skip、noop仅目标1fail；9395 gold30pass、noop目标3fail，四次安装均成功。合并此前4778、2231与主批其它题，DVC35题最终组合均完成真实两侧验证。

**16:29 E18预算更正：** v1c只抬了driver总预算，spec内部测试仍为1800秒；此前“3小时gold”不能理解为测试限时也已修改。v1c已结束，保留其超时与部分日志。实际TensorBoard前四个epoch的平均loss与原预期相差0.6–1.9×10⁻⁶，均在原rtol=10⁻³内，支持历史torch版本这一归因，但不代表完整测试通过。v1d显式将测试预算设为10800秒、总预算11400秒，4CPU与OMP/MKL线程数4，16GiB/1GiB shm；先gold再noop，仍保留全部原断言。这是专用诊断档位，不能当全池默认或纯性能单变量实验。

| E20 | Modin5940 gold实际耗尽1GiB `/tmp`并碰到内部1800秒测试限时；没有OOM或PID拒绝。新增独立资源版：8GiB内存、4GiB `/tmp`、测试3600秒、总预算4200秒，保留2CPU、shm64MiB、PID512及全部原测试。 | `modin5940_resources_v2`等待原资源批结束后跑noop/gold。这只验证资源不足是否消除；S3资产、旧Moto服务与strict xfail问题仍须分别处理，不能用加资源自动核销。 |

| E21 | Modin6780资源恢复后，gold仍有28个warning检查失败及3个参考键缺席。分别恢复pytest7.4.4的异常传播行为、把3个旧键精确绑定到3个完整nodeID；原测试、断言与参考分组不变。 | 两侧旧日志均能唯一匹配；ID修订重放恢复目标noop0/gold1，但不核销28项失败。`modin6780_compat_v1`验证组合后的完整测试。 |

**16:39 E19继续修订：** v1的gold已完整1044项通过，但`pip check`发现三个既有冲突，不能只看测试成功。保持目标pandas及Dask版本，fsspec/s3fs/gcsfs共同固定2021.9.0，nbsphinx0.8.9匹配Sphinx4/docutils0.17，补build1.2.2.post1与pyproject-hooks1.2.0。v2只在元数据预检发现gcsfs锁定旧fsspec，未重跑评分；v3补齐这一关联后继续预检和真实两侧复验，全部失败版本保留。

| E22 | Modin5940/6937的原fixture需要`moto_server s3`。恢复Moto4.2.14；不改fixture断言，不让grader访问公网。与8GiB内存、4GiB临时盘、测试3600秒的资源档位组合复验。 | 候选UID54322、network=none的独立服务探针确认：原Moto5 CLI退出失败，4.2.14完成真实建桶、写入、读回、删除。`modin_s3_compat_v1`等待资源批后运行完整noop/gold；小探针不代替整题验收。 |

| E23 | 暂时隔离Modin5940/6937的**原测试材料版本**，不作为已修复可用题。5940公共Parquet/JSON当前403，两题的NOAA1788.csv当前404且原测试保留过时xfail；断网时双方同报错可变成strict XPASS。先完成资源/服务因果对照，避免再次把这些失败归给模型。 | 不声称原资产永久消失。恢复条件：得到可追溯的原资产并冻存，或另立经过验证的本地fixture/数据修订版；须验证实际读到数据，明确其与原版的区别。未改测试标记、未删断言，也未修改正式题池配置。上游早在2022年记录此CSV缺失：[Modin #4875](https://github.com/modin-project/modin/issues/4875)。 |

**17:04 E18新证据与修订：** v1d gold参考1+8项全通过，但完整10项中仍有1fail。第1轮6个epoch的loss、最佳Dice及epoch均通过原断言；随后NiftiSaver将int64交给NiBabel5.2.1，被新版类型检查拒绝。不是新的数值失配。`numeric_v1e`合并2446已验证的NiBabel4.0.2，保留Torch1.4与所有原断言；等v1d noop结束后完整gold/noop复验。v1d实际峰值约12.6GiB，16GiB只是本题专用档位；后面缓存数据阶段仍需观察，不能凭首轮宣称全程资源充分。

**17:09 E19核销：** pandas_meta_v3两侧pip check/安装均无错误，gold1044pass/1xfail、noop只有目标16fail，参考缺席0且清理正常。实际安装约709秒，包含候选源码重编译；通过环境验证不代表其训练评分成本已优化。

**17:48 E18/E20/E22复核：** MONAI763 v1d noop同样被NiBabel阻断，除此之外保留目标断言失败；gold参考通过不能覆盖完整测试失败。v1e已接续，无需新授权。Modin6937原资源版gold的425fail与19error不是参考键丢失：F2P1项FAILED、P2P1934项PASSED/420项FAILED，无MISSING；完整日志有414处ENOSPC字串，19处旧Moto启动错误。noop同族426fail/19error。采样未见OOM/PID拒绝，但有采样间隙；故只核实已观察到的临时盘/服务问题，不宣称其它资源已充分。继续既定4GiB临时盘/Moto4完整对照，不更改奖励或原断言。

**18:27 E18/E20对照收口：** 原Torch/8GiB/2CPU、内部1800秒的MONAI两侧均超时，峰值分别noop5852MiB/gold6327MiB，终止事实为无OOM/PID拒绝；RH2正确保留infra/None，不能据部分日志比较完整测试成败。该对照与v1e在Torch、线程数、CPU、内存和预算上有多项差别，不能将耗时变化单归因于Torch。v1e第一轮已完成训练/保存并进入第二轮，支持NiBabel修订消除原先阻断；第三轮缓存训练及完整断言仍未验完。Modin两条资源/服务后续已按既定计划自动启动，无新增环境决策。

| E24 | 对已实证的跨manager年龄清扫，后续诊断使用现有label_prefix作批级隔离；原生产问题单列，不关掉清理。numeric_v1f仅补被误删gold，同镜像等价条件满足时复用v1e noop。后续runner严格检查manager_close及实际测试结束标记。 | 活跃sleep反例和命名空间对照均验证，见runtime_findings_1900.md；163题326条旧收口回查通过。新gold排队，生产未修。 |

| E25 | Modin6937 Moto4组合达到PID512且内核拒绝fork，试两题PID1024，其它测试/依赖/资源保持；不是全池默认。暂挂旧S3父派发，当前noop收口后由专用助手登记superseded，三个未跑case由v2替代。 | 保留旧noop证据、实际进程/线程分布；必须先核对旧driver与实际容器清理，不能绕过fatal。原材料隔离边界不变。 |

**19:20 E20分项验证：** 5940资源v2 gold完整结束，目标4/4通过；其6fail/2error均为原S3依赖/材料，noop另有目标4fail。两侧日志均无ENOSPC，tmp采样最低约3.0GiB可用，峰值内存约2.5–2.7GiB，未观察OOM/PID拒绝，manager收口正常。因此可核销该组合的临时盘容量问题，不能核销整题环境或原材料。


## E26 · 20:10 SGT：6937修服务日志阻塞，撤回“只需加PID”的推断

- **新证据：** 6937来源`modin/conftest.py`把Moto stderr接入PIPE却不持续读取。PID1024对照仍停在末尾；宿主看到一个服务线程处于`pipe_write`，其余163线程等待锁。PID512拒绝是真实后果，不能因此把正常需求定为1024。
- 独立UID54322、断网探针：默认管道65536字节，1078次请求后超时，积压65263字节；仅排空日志即可恢复同一服务。改普通文件后4096次请求及S3真实对象写入/读取通过，日志246599字节，探针容器已移除。证据`moto_log_backpressure_probe_v5/result.json`；早期四次探针的脚本/失败保留（Python3.9常量、400次不足填满管道、超时类型、线程快照竞态），不计为环境结果。
- **决定与实施：** 新`modin_s3_compat_v3`仅对6937包装已固定Moto4的console入口，将stderr保存到普通文件；不改变测试、断言、参考集合或评分parser。安装段记录原入口及wrapper摘要，候选身份后观测保存服务日志大小、摘要和尾部，属于诊断线索。PID回到512，继续2CPU/8GiB/4GiB tmp与原3600秒测试预算；完整两侧尚待验证。
- 5940来源fixture实际使用DEVNULL，没有上述PIPE问题。其v3保留原fixture，只完成此前排队的Moto4兼容对照，仍PID512；不把6937的根因套给它。
- 旧v2只让当前6937 noop到有界收口，父派发已暂停；`retire_superseded_s3_v2.py`须确认driver/容器全部收口后登记superseded，再由v3替代未执行三条。未清理或fatal不能继续。原材料隔离E23保持。

**MONAI的补充读数：** v1e noop已完整结束，参考目标1fail、P2P8pass，但全测试是2fail/8pass；另一失败是3D集成推理输出均值相对误差0.005302，超过原0.005容差。gold补丁改变窗口切片数量，可能影响该输出；目前只作待对照现象，不能直接认定剩余环境故障，也不能称noop只有目标失败。v1f gold已进入第二轮训练，保持原断言，不另派重复测试。


## E27 · 20:55 SGT：6937的S3端口不一致，单独修fixture配置

E26版本的noop现已完整结束（1494秒）：参考目标1fail、P2P2354pass；全测试9fail/3074pass，其中4个CSV strict XPASS属于E23旧材料，4个Parquet测试明确连接`127.0.0.1:5555`被拒，另1项是目标失败。服务日志91989字节、采样PID峰值467且未见拒绝，说明日志阻塞已解除，但不代表全部环境问题解决。

源码确认：6937的`s3_storage_options`在master算出5555，实际`s3_base`启动5500。5940两侧均为5555，没有此问题。决定只修6937消费端计算，使其逐分支与实际服务一致；原测试函数、断言、命令和参考集合保持。版本`modin6937-port-v1`保留完整前后文件、diff、摘要、AST检查；以诊断spec的`trusted_setup_append`应用。这样不把conftest加入来源test_patch而意外扩大pytest命令。正式采用时仍须冻结该fixture版本；未修改原来源或生产代码。

新批`modin_s3_compat_v4`仅做6937 noop/gold，继承Moto4与文件日志、PID512/2CPU/8GiB/4GiBtmp/test3600/whole4200，等待v3完整批结束后执行；独立label命名空间。原CSV材料隔离继续，不能删除xfail或让同报网络错误充当真实数据读取。v3的5940继续原配方，不套用6937端口修订。

本次另修实验分析脚本的失败摘要提取：原正则仅匹配`tests/`，漏掉`modin/pandas/test/`。现从真实pytest摘要提取9项，与canonical parser得到的1个目标及8个非参考失败一致；不改生产parser或评分。分类证据`modin_s3_compat_v3/failure_review_noop6937.json`。


## 21:46 SGT · MONAI最终组合与E28

**E18/E24核销范围：** `numeric_v1f` gold完整5430.964秒、10pass、测试退出0；三轮训练/推理原断言通过。与`numeric_v1e` noop的镜像身份、脚本、policy、budgets五项逐项相同，只改manager标签命名空间。noop完整2314秒、2fail/8pass，其中非参考3D均值失败也随gold消失；本次对照支持当前组合可用，不能据一次配对宣称随机稳定性已复验。362个15秒评分容器样本最大间隔15.12秒，gold峰值13.32GiB、PID47，未观察OOM/PID拒绝；两侧candidate/manager收口正常。16GiB/4CPU/shm1GiB、test10800秒仍是本题诊断档位。原跨manager清扫和结果运输问题没有被生产修复。

**E26分项收口：** 6937 v3两侧均完整：noop1494秒、gold1835秒，gold3075pass/8fail，noop多1个目标失败；8个余项都是已定位的4CSV材料和4端口配置。PID512下采样峰值分别467/465、无观察拒绝/OOM，服务日志不再堵住整题。此处核销日志阻塞，不核销整题环境，v4端口修订仍须实跑。

**E28（已实施，待整题验证）：** 5940 v3 noop完整12fail/2636pass：4目标失败、4CSV strict XPASS、2公共Parquet在断网下无法读取、2本地S3写入`RayTaskError(NoCredentialsError)`。最后两项不能混入原资产问题。源码`initialize_ray`仅在GithubCI开启时提前配置模拟凭据，普通`s3_base`是在已启动worker之后设置主进程环境；改为在pytest/Ray启动前导出来源已有的`foobar_key`/`foobar_secret`。这是本地Moto的假凭据，不读取任何真实云凭据，不打开网络，也不启用会改变端点的CI模式。

新批`modin_s3_compat_v5`仅做5940完整noop/gold，复用v3的确切派生镜像（已有Moto4 wheel），只增加上述两项导出；PID512/2CPU/8GiB/4GiBtmp/test3600/whole4200不变。等v3完整结束后启动，与v4使用各自label；资源观察器已覆盖。v3 gold未完成前保留“待验证”结论，E23材料隔离不解除。


## 22:32 SGT · E27/E28组合复验与E29结果含义

- v3整批4条已经完成并审阅；5940 gold为8fail/2640pass：4目标通过，但原Parquet P2P仍1fail。失败分为4CSV旧strict XPASS、2公共Parquet断网、2本地写入Ray无凭据。两侧资源/清理正常，这不是候选补丁无效。
- v5的5940 noop完整1633秒、10fail/2638pass；两项本地`test_to_parquet_s3`已从失败变通过，原函数直接执行两侧写入、读回和df_equals，没有双方错误等价分支。剩4目标+6原材料，gold仍待。
- v4的6937 noop完整1128秒、14fail/3069pass；原fixture已确实从5555改到5500。2个object读取成功，但6项缺Ray凭据、3项anon=False在worker中403。7个先前PASSED变FAILED，不能据此说端口修订破坏了7个正常测试：来源helper会接受双方同类错误，错误地址时的PASSED不证明读过对象。逐ID对照在`port_state_comparison_noop.json`，各失败原始traceback另存。
- **E28扩展（已实施、待验证）：** `modin_s3_compat_v6`仅6937，继承v4的端口/日志及同一镜像，提前导出来源假凭据；测试、参考、资源、原ACL都不改，等v4整批完成后完整noop/gold。独立label与观察器名单已登记。

**E29（处置，不是全绿修法）：** 独立UID54322/network=none/Moto4探针用来源JSON原始348字节验证：默认私有对象，带默认或另一个假key均真实读回；匿名返回403。只在独立探针设置public-read之后匿名才读回相同字节。来源helper明确支持异常类型一致，故匿名用例的PASSED可能是在比错误，不能算数据读取覆盖。当前保留整题原ACL，不把可能的权限负例擅改为公开成功读取。两题仍材料隔离；后续明确版本必须写明匿名用例要测错误语义还是内容比较。探针容器已清理，未改整题权限或断言，证据`moto_object_access_probe_v1/result.json`。


**22:34 E27收口补充：** v4 gold完整1036秒13fail/3070pass，参考2355项通过；与noop相比只消除原目标失败，9个worker凭据/权限失败和4CSV材料失败仍在。两侧无观察资源终止，清理正常。v6已实际启动、配置回读正确；端口配置修复已实施验证，整题环境仍未通过。


## 23:20 SGT · E20/E22/E26–E29最终对照收口

- 5940 v5完整noop10fail/2638pass、gold6fail/2642pass；与v3逐ID对照，两侧恰有2项本地S3直接写读由FAILED变PASSED。gold余4CSV strictXPASS和2公共Parquet不可达，P2P仍1fail，保持E23隔离。
- 6937 v6完整noop5fail/3078pass、gold4fail/3079pass；与v4逐ID对照，两侧恰有9项凭据/worker403失败消失。gold参考全通过，但完整测试余4CSV strictXPASS、退出1，保持E23隔离。没有改ACL、断言、参考或binary奖励；异常一致的PASS仍不等于成功读数据。
- 两题均同版本noop/gold输入相等、安装0、完整测试输出、两层清理正常。2CPU/8GiB/shm64MiB/tmp4GiB/PID512下采样无OOM/PID拒绝；5940两侧峰值约2.73/2.76GiB，6937约4.56/4.44GiB，15秒采样不是无间隙保证。
- 最后gold于23:13结束；23:14远端无实验进程、无任何Docker容器，观察器已自然退出。8个failed systemd记录均为已保留并有后继修订的历史准备/预检失败，不重启。此前生产跨manager清扫、日志完整性和manager_close运输问题仍是独立交接项，本批未修。
