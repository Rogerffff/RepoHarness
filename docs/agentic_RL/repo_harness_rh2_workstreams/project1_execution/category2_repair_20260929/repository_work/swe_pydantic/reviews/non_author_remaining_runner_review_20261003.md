# Pydantic剩余四题：R14执行入口与固定输入非作者窄核

2026-10-03。**本轮静态入口与身份核对通过，没有新增入口阻断，可以继续四题正式CPU矩阵及公开actor诊断。四题当前不能据本报告直接进入普通GPU探针：R14题级正式运行、实际公开actor及相应非作者原件验收仍缺。** 发布、local prepare与预期分数不是CPU结果；本报告不授予训练／留出资格。

审查者不是本轮材料、输入或runner作者；已接触四题及5662／6283私有测试、gold、错误候选和既有结果，不是fresh公开读者。本次接续[材料窄核](non_author_remaining_material_review_20261003.md)、[8567正对照语义窄核](non_author_8567_positive_semantics_20261003.md)、[R7正式CPU入口核查](non_author_6283_cpu_review_20261003.md)及[5662结果核查](non_author_5662_cpu_review_20261003.md)。复用父线程已核1220发布成员／100材料成员和发布者R14维护、部署证据，不机械重审共同代码或材料，不重跑旧矩阵。

只用本地标准库读SHA、JSON、AST、diff和canonical digest，并在内存核有效补丁身份；未SSH、Docker、安装、调用模型、运行项目pytest或作者自动检查脚本。只新增本文和[同名JSON](non_author_remaining_runner_review_20261003.json)，不改共享文件、固定输入、原件或历史reward。

## 固定身份与本地prepare

版本为 `cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`，manifest SHA `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8`。四份[发布回执](../../../../../../../../runs/category2_repair_20260929/publication_cpu_takeover_20261003/r14/close_summary.json)均绑定R14、cpu-a、runtime_cpu_v2，并明确题级CPU未由发布者运行、正式SWE actor仍为source；[部署回执](../../../../../../../../runs/category2_repair_20260929/host_setup_20261003/cpu-a/release_receipts/cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1.json)与[固定grader镜像readback](../../../../../../../../runs/category2_repair_20260929/publication_cpu_takeover_20261003/r14/grader_image_readback.json)保留。此处复用其适用范围，没有新现场确认。

| 输入 | SHA256 |
| --- | --- |

| [run_formal.py](../cpu_acceptance_20261003/remaining/run_formal.py) | `b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5` |

| [formal_inputs.json](../cpu_acceptance_20261003/remaining/formal_inputs.json) | `bea70edd55d2a316b5d92fde1a3a894e9c79363a168e2cd92c7de2d40b83ac1b` |

| [run_actor.py](../cpu_acceptance_20261003/remaining/run_actor.py) | `21caef4f953334a2b3759657ac3d5de00bd03373ffa8e40794674ddf5797f4f9` |

| [actor_inputs.json](../cpu_acceptance_20261003/remaining/actor_inputs.json) | `226ef4ab9be63c08f0ddfdd5755dc48353d87b3c24fbc3732745737cf36e3882` |

| [upload_manifest.json](../cpu_acceptance_20261003/remaining/upload_manifest.json) | `e9d29aec3f252a836a5fd49aaf3118e93248edeefa47c4bc41976cf2a0edaa67` |


独立核66上传成员的路径、字节数、SHA和无符号链接；formal／actor两输入的R14元数据、四回执SHA和三份public／grading／environment bundle SHA相同。[远端输入简略回执](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remaining_r14_upload_verified.json)记66成员精确集合和SHA通过，本轮不把它替代成新逐成员远端实测。

四份忽略目录[local_prepare_r14_v1](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/local_prepare_r14_v1/8511/status.json)均是 `local_prepare_identity_join_passed_not_cpu`。我独立核prepared manifest、host及两份prepared文件的SHA／单行数；public与published bundle逐字段、host grading与published grading逐字段相同；重新计算public／grading／environment／materials四种canonical digest；参考和补丁字节、安装资产／core／prepared grader ID／source ID均相符。28份保存脚本SHA与status相同。四个有效测试文件由base公开文件和固定补丁在内存还原，SHA与输入吻合，Python3.8 AST可解析；这不证明真实git apply或pytest收集。

| 题目 | F2P／P2P | 正式行数 | core | local prepare材料identity |
| --- | --- | --- | --- | --- |

| 8316 | 1／143 | 24 | 2.14.5 | `sha256:05c815276fd0e953aa6a6fb90cbd1a4e1d6e936d7bb1fb7f4499b0557007aaa9` |

| 8511 | 1／172 | 3 | 2.14.5 | `sha256:879bf1d3bc96bd56a96b8190728fa24df0e28cece50119015d402c917abb8eb6` |

| 8567 | 2／160 | 9 | 2.15.0 | `sha256:79fdb8c6fb5328a023a3f1b5ff2ade9e6fa405aec636d42755783bbb36546d0d` |

| 9066 | 2／368 | 5 | 2.16.3 | `sha256:c72cb966577c64feeb474ea27d304810ce07970af5a5271835a8c812dfeff906` |


各题revision、prepared manifest、host、有效文件及脚本完整SHA见JSON。四份fixed安装登记分别为 `pyd8316-e10-fixed-v1`／`pyd8511-e10-fixed-v1`／`pyd8567-e10-fixed-v1`／`pyd9066-e10-fixed-v1`；source与prepared grader身份均按回执登记。

## 正式入口的新增部分

与已实际运行的R7 `run_formal.py`相比，仅改变题ID／run_id允许表、将release ID／SHA／精确成员数从常量移入固定输入、按每题 `len(fail_to_pass)` 核F2P数量、重命名参考parser检查和actor范围声明。实际prepare仍校验全部release精确集合与材料SHA，拒绝未激活revision、错误补丁／参考／安装；没有改原binary_v1评分、七段正式脚本调用、FrozenPatch重放、资源或清理逻辑。

`spec_record` 的相等检查覆盖材料identity／revision诊断、七脚本、hygiene和三个预算，**不是全部GradingEnvSpec字段或实际actor相等**。R14固定grader选择及8wheel prerequisite消费复用发布方共用窄验证；我另外核本地host installation的registered grader／source／core／recipe与固定输入。execute会inspect base与derived实际ID、将derived明确用于重放，并核ledger实际镜像、FrozenPatch镜像及源码import。上述运行检查现在尚无四题实际原件。

F2P／P2P总数是1／143、1／172、2／160、2／368，不再误固定为2 F2P。正对照和noop的 `required_statuses`覆盖全参考；特定负对照只列已知关键失败／通过节点，仍要求所有参考都有合法PASSED／FAILED终态。负对照的自动检查不意味着其余参考没有附带回归，非作者实际验收仍须核全部参考和失败原因。41份候选资产字节均绑定现有工件，正对照没有漏参考、预期节点均属本题参考、状态合法；不把预期1或0当实测。

| 题目 | 必须实际区别的预期 |
| --- | --- |
| 8316 | 24行：noop0；gold／keep_digit／scan各1；其余20行各0。noop原缩写节点失败、其余143参考通过。保留两种数字读法和不同算法；误写分别由同一参考体内的新增行为拒绝。3类同机制合并及7份合理实现不机械复跑，34原工件保持。 |
| 8511 | noop0：原repr节点失败、172 P2P通过；gold0：原repr与默认可见保护通过、三类无本地注解子类构造回归失败；narrow1：全部173通过。gold0必须是继承行为失败，不能是安装或收集失败。 |
| 8567 | noop0：原v4与B03两个F失败、160 P通过；gold0：四关键节点失败；upstream261原v4通过、新B03／B06／N3失败；c3_reorder／ok_post_attach各1且162参考全通过。后四行B1／B2／B3／Python-only代表各0，原v4节点必须失败。共9行，旧v4适用证据不重绑v5。 |
| 9066 | noop0：IPv4／IPv6 F失败、368 P通过；gold／gold_catch_user_error各0：两IP F通过、独立stdlib dataclass默认实例P失败；fallback／upstream271各1且370参考全通过。新增独立P节点不能靠旧混合节点记录代替。 |


`reference_parser_complete`只指参考：结合真实日志逐ID合法终态、missing／skipped为空及partition完整性，数量下界只是辅证。四题当前参考ID都没有空格。6283／5662已记录的非参考参数拆词缺口仍保留；**5662的138个parser键是129个正确参考＋9个非法非参考键，不是138个完整states**。本入口未修parser，也不能因此声称所有非参考节点完整；复用共享parser维护事项，带空格参数ID成为参考前修复，新矩阵核原日志时继续披露实际边界。

## 原source actor与私有评分边界

R14改的是正式固定grader安装／镜像消费，原公开bundle逐字段未变，正式SWE rollout仍source，训练typed actor未由本release接通。诊断 `run_actor.py` 接续旧入口，换为R14 ID／SHA／1220、diagnostics_v2输出及四个精确derived ID，通过既有devcheck `--image` 覆盖使用公开wheel派生镜像；它不是正式训练actor已变成grader。部署仅证明镜像可用，实际容器镜像／资源与公开开发必须另验。

actor只以公开view渲染原题面＋public_hints，命令文件独立绑定SHA；未读取formal候选、gold或required_statuses用于solver交付，也不应用私有effective patch。12条命令按“身份→原公开示例→既有公开测试”运行。Python3.8 AST通过，身份命令源码SHA与noop baseline值相同；6个已有函数名均在base公开测试AST中存在。四题目标分别为原HTTPResponse示例、Field repr=False示例、bool serializer两顺序示例、IPv4默认schema示例，未加入私有B03／B06／N3、继承或dataclass默认实例要求。

入口预计核UID54321、Python3.8／testbed解释器／精确core／源码import及可写性，检查实际derived容器2 CPU／4 GiB、命令zero／nonzero期望、公开原目标明确False＋指定AssertionError、CC prelaunch／activation／完整日志及清理；首桩请求还须含原题面＋hints，排除3题新增私有节点名。8316 guard为空，因为新增断言在原节点体内，**空guard本身不是零私有暴露证明**；本次依据公开数据流及命令内容限定静态结论，实际请求／挂载／源码仍待核。

四题actor目前均未实际运行。devcheck是固定桩驱动预定命令，即使将来通过，也只证明公开环境、CC操作交付与收尾，不是模型求解或语义通过。BASH_ENV专用拒绝探针未测，不称全角色隔离；private命名排除不是通用泄漏检测。原公开题面未变，无需因私有测试更新添加新公开读者；普通GPU仍需本轮真实actor首消息和实际身份证据，私有gold／反例／审查结论不得进入solver上下文。

## 预算、清理和当前缺口

正式矩阵按题串行，计划总41行，使用既有CPU作业槽，不扩资源。脚本固定2 CPU／4 GiB，PID512由既有profile及实际cgroup检查；spec预算为reset300／apply120／test1800秒，ReplayBudgets仍为candidate900／grading3600／cleanup120秒，manager close300秒。actor命令90／90／180秒、CC wall1800秒、外层子进程2400秒，超时先TERM进程组、180秒后KILL并记cleanup_unconfirmed。这些是现有边界，不是整41行总时长保证。

正式每行保存原log、ledger、report、FrozenPatch和full baseline；观察发生在正式post观察后、不回写reward。安装退出、真实test_rc、收集错误、完整日志、apply与stage/infra字段分别检查，负对照须普通 `tests_failed`；失败停止后续候选。正常／异常路径调用manager close及按run标签查容器／网络，并要求候选删除、manager无未清理及本run零残留。检查失败或收尾中断时保留原件、按阶段分析，不能因设计有finally就宣称现场清理已完成，也不能把异常当题目0分。R14尚无FrozenPatch／完整baseline运输或零残留实测；R7运输证据只证明可复用机制。

本次所见首次[8511派发记录](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/pyd8511-formal-20261002230939-r14-8d68e.json)及[原dispatch日志](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/pyd8511-formal-20261002230939-r14-8d68e.dispatch.log)为 `All CPU slots busy; retry later`、rc75／deferred，未运行题目、没有候选reward。不能由它推导安装失败、题级0分或R14验收通过。

现有停止条件保持：四题逐一补正式安装、完整参考及关键节点行为／原日志、正确source／import／core／image、FrozenPatch与完整baseline运输、两层清理，补实际公开actor与交付，再由非作者核CPU原件；满足后申请普通GPU。发现差异只补受影响范围。材料与部署可复用，但local prepare、静态入口通过和桩均不核销这些实际运行缺口。
