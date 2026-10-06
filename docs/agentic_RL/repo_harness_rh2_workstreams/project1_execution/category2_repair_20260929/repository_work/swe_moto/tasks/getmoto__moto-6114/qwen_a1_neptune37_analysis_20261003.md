# Moto6114 新37：Qwen 首次结果与完整轨迹分析

2026-10-03。`gpu1003-moto6114-neptune37-qwen36-a1` 原分1，安装／测试0，1F／36P共37项完整通过。题主确认当前ARN查询返回稳定身份，以及新增Neptune名字start／delete保持项正确；未重现旧35 Qwen的两项回退。Qwen额外改了五个操作的ARN路径，当前未授予这些扩改的一般正确性；下面单列源码限制。新37两模型首轮各一次已齐备，旧R7／35材料不参与配对，单样本不证明稳定或训练资格。

## 原件、模型与执行绑定

唯一权威目录 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-moto6114-neptune37-qwen36-a1/`。闭合manifest在其 `qwen_first10_closed_v1/gpu1003-moto6114-neptune37-qwen36-a1/closed_manifest.json`，SHA `2af5f1e0ef984505ab2fc20dcb3cc8e79325d07f115706d0465b3dfcfa2dd1e2`；183成员／58,984,726字节逐项SHA和尺寸全核，含准备及共享依赖，不能算183次模型或题目实验。

机械回执v4 SHA `a8febc8067a703db04e0e6a5e08d7aae25f611c7bfe0f2f41d69053be9ec4943`、两臂回执SHA `ea6eba363c8e9565ac02de8b9f9b5558c132ff4671e4c184ee64a8623536f7b8` 均核原字节。原件中的semantic_acceptance／training_qualification空、paired_request_closed=false及pair中Coder semantic_review_pending=true保留，题主分析和总账终局状态另记，不回填原件。

当前请求 `swe-moto6114-identity-neptune37-r21-20261003-v1` 输入SHA `6dfa36e642bee0e9fb5e8d35efe85149bb8c9258a4a980591c9706cc57d31723` 与冻结request copy完全相等。source queue为 `queue_qwen_first10_v1`，runtime code8，fixed inputs manifest `97bd3ed8b8b8943c1a2272a9cb5b965df2d8fa2b7812a0c28f795fa4e842ee3f`；实际entry及源文件身份由包内SHA关联。材料仍 `moto6114-cluster-identity-neptune-preservation-v2`、materials identity `ea5d966eb5dfe35b9b4a8a4f5732d7fdf4c8383bc2558302a5d60c4f795ab29e`，base／public／environment／grading／effective patch均与R21输入相等。actor及grader实际镜像 `1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5` 与CPU和Coder相等。

实际Qwen3.6固定服务在22:01:09 SGT启动本题前capture，22:07:44 SGT终局；engine／adapter实际before与after inspect及只读模型挂载、配置、checkpoint manifest被关联。checkpoint manifest SHA `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab`，不是旧Qwen历史时间补标。没有重复全部权重文件或GPU内存hash。input_check内部service_readback的config_only／verified=false保留，外部现场capture另核，不用内部模型名称slime-actor单独证明权重身份。

实际首HTTP含完整原题面与中性brief，delivered prompt SHA `8974243c9d3df94c6de1a79d5a4e7d12963c79395153a545e917f542496ab599`；按原CRLF字节核对，且与Coder prompt逐字节一致。1972项baseline entries与Coder完全相等，内容、类型及执行位全部核；当前材料与模型预算、实际评分预算均相同。这能支持当前首轮配对，不能拿旧35 Qwen替代。

模型预算ctx196608／输出65536／240回合／10800秒／1024请求／首字节1800秒／idle14400。实际42次生成max_tokens均65536，均finish stop、CC正常end_turn，无预算截断。评分whole1800／setup900／apply120／test1800，900来自本次实际input_check及code8政策证据，不由CPU设置推定。原strict300超时仍为历史infra，未改写。

## 评分与当前源码语义

正式执行 `pytest -n0 -rA tests/test_rds/test_rds_clusters.py`，可信恢复当前patch，1F／原34P／新增2P完整37参考全部PASSED。footer `37 passed, 166 warnings in 3.52s`；安装4.567秒、测试3.974秒，candidate segment完整，无missing／skipped／infra／段外测试。新增 `test_rds_facade_preserves_neptune_name_start` 与 `test_rds_facade_preserves_neptune_name_delete` 实际通过；这些不是solver公开35项的一部分。

FP `a15e9c30af7b494a4df5accfd36faec3e5132334a42dee18981ed4996e2ca987` 仅一项 `moto/rds/models.py`，regular／100644、162277字节，内容SHA `e7df8b2f391eee0cd43e241eb8961afc5a1a3c0bebcec5c281ba77b9fdf5c34f`，投影完整。六次Edit239／309／337／365／393／421从实际baseline顺序重放精确等于FP；AST比较只有describe、delete、start、stop、create snapshot、modify六方法变化。没有正式测试目录改动或额外工作区文件进入FP。

describe在匹配既有arn_regex时取最后一段作为cluster_name，否则保留原名字；继续按原RDS clusters再Neptune clusters顺序查询，missing仍报原DBClusterNotFound。当前同地区／账号RDS ARN指向正确稳定Identifier与ARN，名字查询对应同一对象，非返回第一集群或伪造长度。start和delete保留原Neptune委托：短名字不匹配ARN，送入Neptune的仍是原名字，正是旧Qwen删掉委托导致回退的两个位置，本次已静态核对并由新增P2P运行保护。

五个额外ARN操作不自动成为本题要求。[固定旧题卡](card.md)明确不扩入跨账号／地区／服务；当前新37主要增加原本应保持的Neptune名字行为。Qwen只是使用本地backend并截取ARN末段，没像既有find_db_from_id那样按ARN地区选backend；此范围外差异记录而不另改评分或推一般AWS真实性。

额外modify分支仅正规化局部cluster_id，却将原kwargs交给Neptune.modify_db_cluster；后者从kwargs读取未正规化的db_cluster_identifier并按字典键访问。因此它新声称支持的Neptune ARN modify路径在静态调用链上仍不一致，当前没运行该反例，也不是新短名字回退。原题要求describe，模型自测也没有验证modify／start／stop／delete全部ARN操作；最终“六操作均修复”的表述超过证据。当前目标及37保持项通过，额外路径不授资格；无需因此扩大当前任务、重发材料或重复CPU。

## 完整轨迹与自测质量

599行完整CC轨迹、42回合／生成、41工具：Bash20、Read15、Edit6。所有调用与结果逐ID对应，全单工具串行，无实际多工具batch或并行时长证据。HTTP42条全部生成、无count_tokens，响应全200；每条SSE有完整message_start／message_delta／message_stop，输入／输出usage与adapter及CC累计相等。

11行定位RDS，25／29行核实际解释器、Moto源码及版本；53／81行读目标及临近方法，109／113行首次复现因误用当前版本没有的mock_aws导入失败。123行查当前导出，137行换mock_rds后141行严格复现：名字查询成功、ARN抛DBClusterNotFound。151至221行读既有ARN模式；239行先修describe，253／257行同一严格自测成功。后续267至421行再扩改其它五方法，没有先建立每个新操作的修前反例；435行重跑describe自测成功。

449／455行公开cluster文件footer35 passed，465／469行filters26 passed；两者经head，但实际输出包含完整footer，作为自测观察保存。479／483行原rds.py -k cluster全部113 deselected、0 selected，管道使tool_result未报错，不能计为通过测试。493／499行全tests/test_rds（排除test_server）经tail输出footer210 passed、106483 warnings、21.11秒；仅有尾段，不能凭此列出210逐项状态，更不包含当前新增私有Neptune保护。579／585行重复cluster＋filters61 passed；35、26、61和210重叠，不累加成独立覆盖或模型尝试。

509／513行临时综合程序以assert核两个集群中的正确名字／ARN、缺失ARN报错、ARN创建snapshot以及列全部集群2项，实际打印成功。它不验证其余四项扩改的ARN行为。两份自测由Bash写到/tmp，临时文件没有进入工作区FP，但完整写入文本与输出留在轨迹；它们不替换正式评分。唯一两次标错结果是113导入失败、141预期修前目标失败，另有一次未标错空测试；未重试模型求解。

累计输入611249、输出8237，最大单次输入26423、输出801；solver93.869秒、CC90.184秒、API52.194秒分开记录，无每工具独立耗时可把差值全归给测试。manager总247.499秒、reset14.797、prep0.435、test9.132；phase trusted setup222.349971秒，正式安装／测试和运输保护另列。单次queue_wait0不能证明全局无排队。

## 清理、资源与后续

actor／relay所属容器与网络查询实际清理空；manager创建1／移除1、open／supply／cleanup_failures空；gateway revoked／drained／active0，pre-drain residual0。原systemd unit已not-found，不用其默认MainPID0／ExecMainStatus0证明本题退出；当前完整RC0与精确PID1成功journal事件另存并核验。

29有限资源切片，actor10／relay10／grader16点按实际CID归属；正式安装及测试窗口均0采样点，区间内存未知。actor记录峰值1336647680字节、grader746188800字节与report923.789MiB分别保留，不推最低内存、连续无OOM或全宿主空。

题主读回 `runs/category2_repair_20260929/moto_cpu_20261003/moto6114_neptune37_qwen36_a1_owner_readback_20261003.json`，116805字节，SHA `4882df34be669375ff775afbec28f912015c40e8d7bf271493414404d12ae791`。当前两臂原1／1、已保护目标正确，额外源码路径限制单列。原R7／35 Qwen、旧安装2、strict300 infra与原源码复评0均保留身份；每模型仅一次，普通追加暂缓，非训练资格。
