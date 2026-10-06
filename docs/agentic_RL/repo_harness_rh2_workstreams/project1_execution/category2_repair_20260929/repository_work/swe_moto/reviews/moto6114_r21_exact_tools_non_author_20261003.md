# Moto6114 R21 单 exact_qwen 工具非作者静态窄核

审查日期：2026-10-03。审查者为非作者 subagent；已接触本题私有金标、控制补丁、历史 GPU 源码及先前 CPU 原件，不是公开盲 solver。

## 结论及适用范围

未发现本次固定薄工具的静态启动阻断。可以按既定范围启动一次 R21 exact_qwen：它调用 R21 原 replay CLI，使用显式 CPU COPY-only ConfigID；发布政策在 CLI 实际 inspect 身份成功后，将交给原 manager 的完整评分 spec 的 env_reset_timeout_seconds 从300改为900。薄工具自身不修改该预算，且要求实际账本回读900及固定政策/请求/input身份，否则停止。

R19 已有效的 noop=0、gold=1、wrong_first=0 保留；本工具只恢复尚无有效分数的 exact_qwen。R19 exact_qwen 的 failed_to_grade / infra_failure / reward=null 仍是原基础设施观察，不能改成模型0。新臂预期0只是计划，本报告没有执行它，不能证明保护超时已恢复、实际评分已产生或新37项 CPU 最终准入通过。

本次只用本地标准库读取、SHA256/字节比对、JSON、AST 和文本差异核对。没有执行发布验证程序、prepare、项目代码、SDK、测试、Docker、SSH、CPU 或模型；没有读6185原件、在途作业或连接配置。只新增本报告，没有修改工具、发布材料、旧报告、历史 FP/raw、冻结输入或共享代码。

## 1. 固定字节与实际读取范围

工具根为 repository_work/swe_moto/tools/moto6114_cli_exact_r21_v1；已核目录恰为四件，manifest 的三件成员 SHA/bytes 均与实物相符，matrix.py 与 launcher 均能由标准库 AST 解析。

| 文件 | bytes | SHA256 |
| --- | ---: | --- |
| manifest.json | 495 | 72be860ca5865e08fae6d5b2c4d78d683acee76cd953ab47f2df0aca60cb9a40 |
| matrix.py | 16325 | 4dbf1688b27eba4adc32585c3993e3b5c1380da32fec034452a0aa55a045acd9 |
| expected_runtime.json | 6024 | 556a41c525a8b9931832b0f0c2ca875dc61d5cbab2b0f80543fe2c60daf67166 |
| image_recipe_binding.json | 1724 | 553e1aeaa984ea899518d12688462be0a35d815b4d94abae13a7af0e301d990f |
| ignored launcher launch_moto6114_r21_exact_v1.py | 6783 | 86edd594470c9cd3e50318ae5613d4d7038acd9473026cf3b37f22752c417397 |

expected_runtime.json、image_recipe_binding.json 与已审 R19 对应件逐字节相同。对照已审 R19 matrix 和安全 launcher，增量是固定 R21 release/manifest/policy、仅 exact_qwen 的选择集合、新输出根/独占运输回执，以及实际账本政策/reset900 guard。原评分入口、导出 gold 字节、候选 patch、测试/安装脚本、参考、资源与其它预算均保留。

读取了 R21 release 的 manifest、原 CLI 脚本、ReplayGrader、prepared_task_face、manager、spec_vendor、sandbox_profile、两种 preparation policy 及 JSON、原 producer/registry/三个 JSONL、固定 exact patch、support input 与部署原件；必要直接源文件 pin 对照本地 release manifest。另独立逐项读取作者导航列出的19对 R19/R21 actor/关闭链/DevRunner helper 源文件，核每件 SHA/bytes 并比对两侧字节全同；rollout_spec_from_view 函数正文也逐字相同。没有将作者1482成员总核布尔值当成我逐项重核1482的结论。

## 2. 发布/材料/镜像身份

R21 本地发布根：runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_moto6114_prepare900_v1。工具调用其 repo/rh2/scripts/replay_grade.py 和 repo/rh2/src，而非工作区最新实现。

| 绑定对象 | bytes | 实物 SHA256 |
| --- | ---: | --- |
| release manifest.json | 325055 | 630f71fc1a4ae6f587f3161fae56d92927a91801ae4b08954a556ee059cada9c |
| 原 producer ingest_manifest_swe_revision_v1.json | 6641 | f0154ff831d9a08fe9f2a819b08cf45068dee63657c6b8e632479a3068c9a0a7 |
| 原 moto6114_neptune_p2p_v2/material_revisions.json | 5513 | 6aecd8d4f9eb40b0a82af7faae73121dc2a0292122876166765f9ecd4a5d8bd1 |
| source_members 中 exact_qwen_a1_source.patch | 6463 | bb5eab97577260270def73fc06f8a0aa4917727cb9348afbe871f5905b2eb747 |
| moto6114_preparation_budget.py | 2554 | 31c937832429367c1296ab46dbe1c85553deb5d8e5e854d06562c1ff4e608d1f |
| moto6114_preparation_budget_v1.json | 927 | 515cb3e8341a62d943f778b5118372733cc7ec78001a85dfc3dd783bc68ba36c |
| 固定 support request input.json | 2366 | 3c986d8b21b4bf70de0aef7ea80a25eb69df74e79bc6815efd7bf70ef7f39ddf |

producer 路径为 s2/ingest_swe40_pyd6283_moto6114_p2p_20261003_v1，registry 为 s2/revisions/moto6114_neptune_p2p_v2；表中 producer、registry 和 exact patch 与 R19 逐字相同。原完整 public/grading/ENV JSONL 也逐字相同，分别为685498/2885387/227255 bytes。不是重新生产题面或测试材料。

实际预备消费要求原 base f01709f9ba656e7cf4399bcd1a0a07fd134b0aec；public digest 6c8f45da003f8e8d1e065d1801afa4659c43cbb212e319a5d07a84922af5f0f2；新37 grading digest 0d7a09c24df12b581adc180c577da3c947d6446ab64ec9f01789b4cc08f5afd6；ENV digest 941bebb539b3974ff894822f9920fdd07227f6a8cf08eaa5c31173f90ea206b2。ENV 此值与 R19 相同；相对旧 R7 的变化是已批准材料 grading link，不能将其解释成新的项目环境改造。

仍为 make init 和 pytest -n0 -rA tests/test_rds/test_rds_clusters.py；expected context 逐参考保留原1F/34P，再加既定两条 Neptune name P2P，合计1F/36P=37。context 未评估/result=null，五项脚本 SHA 与 R19相同；hygiene 仍仅保护 tests/test_rds/test_rds_clusters.py。没有新增评分器、parser 或公共要求，也没有将拟议分数写成实际通过。

镜像绑定仍为 moto6114_install_wave1_copy_only_20261003，来源 ConfigID fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249，来源 manifest cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a，CPU 派生实际 ConfigID 1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5。工具前置 inspect 同时检查来源 manifest/两侧 ID、linux/amd64、来源层前缀加一 COPY 层，以及 PIP_NO_INDEX=1、PIP_FIND_LINKS=/opt/rh2/build-wheels。这沿用原 supply binding；运行时 inspect 尚未发生，不能以静态常量宣称当前宿主镜像已实测。

explicit CLI --derived-image 传 CPU 实际1d8d ConfigID，并附原 recipe 名；未传 R2E-only overlay。没有混用旧 GPU43f 或其它 GPU 物理镜像。材料与源码相同不代表其它镜像自动获900政策。

## 3. 实际原消费者的300/900路由

已直接读取 R21 ReplayGrader.replay_one 相关分支及 manager.grade 调用，确认调用链如下：

1. 从原 HostGradingView 构建 default source 完整 spec；6114原 reset/apply/test 为300/120/1800。
2. 显式 derived_ref 先只替换 image、image_manifest_digest=None 与 image_local_build；在这一步尚未改 reset。6114政策函数只接受固定 task、修订、grading digest、effective patch SHA、CPU1d8d/manifest=None；不匹配则不应用，材料冲突会报绑定错误。
3. 原 replay 接口实际执行 docker image inspect -f {{.Id}}，失败或实际 ConfigID 不符进入 derived_error，停止评分；仅成功后才记录 actualID。
4. 只有固定政策存在且无 derived_error、实际 ConfigID 与政策一致、旧 reset 仍300，才 dataclasses.replace(spec, env_reset_timeout_seconds=900)，并记录 row.budgets.env_reset_timeout_seconds=900 与固定 policy/request/input三字段。
5. manager.grade 收到的正是上述替换后的完整 spec；原 manager 代码与 R19字节相同，control_surface_protect 使用该 spec 的 reset 限额。因此不是只把账本数字改成900。

policy loader 首先核 JSON 精确 SHA，再通过 StrictModel/Literal 校验固定值；没有调用者自由选择任务或预算的接口。R21 prepared_task_face 的全文件与 R19 有继承的 R20 政策差异，但该通用政策只匹配 pydantic8316、dvc9395，6114 default source 不匹配；Moto政策仅在 replay 显式派生路径应用。工具实际 default prepare 后再次要求 reset/apply/test ==300/120/1800，与此 API 相容。

本次也核原 replay CLI 参数名和字段形状。新增 row 预算字段是 env_reset_timeout_seconds；薄工具没有新增900命令参数，也没有本地替换 reset。candidate_stage=900、whole grading=1800、cleanup=120、image_pull=1800、apply=120、test=1800均保留。构造的 actor_spec 仅用来核原 SWE 镜像替换/无 grading_spec 的边界，不能算真实 CC 或 UID 开发安装证明。

## 4. 单臂编排、正常评分筛选和原件保全

--controls 只允许 exact_qwen，默认也只有此臂，重复值拒绝。候选直接取 release registry/source_members 的固定6463B原实际源码 diff，核 SHA、大小和非 symlink；repeat=1。没有运行旧 noop/gold/wrong_first 的路径。export-gold 仍调用原 producer，其输出只作既有身份检查，目录 gold_input 与候选目录 distinct，避免历史同名 mkdir 冲突。

输出根 packages/swe_moto/moto6114_r21_v1/<job> 要求 job 格式且 exist_ok=False，不能覆盖历史目录。原命令 argv、stdout、stderr、退出码、prepared summary、consumer_readback_before_checks、runtime_inputs、policy expectation、ledger/artifacts/eval logs 与资源查询均分件保存；非零外层命令立即停止。既有原件不回写，旧GPU FP/raw1及R19 failed_to_grade/null不改绑。

runtime_inputs.json 保存的是 default source prepare 的 reset300；supported_override_expectation.json 明确另记实际 explicit reset900预期。二者职责不同。验收时必须以本次真实 ledger/实际 manager路径为依据，不能拿 expectation 或 default prepare 本身证明900已应用。

执行后逐行筛选要求：一行 ledger；image_id_actual=固定CPU1d8d；policy字典恰为固定 SHA/request/input；全部预算字典恰为 candidate900/grading1800/cleanup120/pull1800/reset900；stage_error=null；report非空且 outcome 为 resolved/unresolved、failure_category 为 null/tests_failed、reward 为0/1。failed_to_grade/infra_failure/null reward 会停止并留原件，不能当普通 expected0不匹配或语义负例。

还要求 candidate cleanup.removed=true；原 CLI 最后 footer rows=1、halted/aborted=null、final_status.exit_code=0、cleanup_failures空。随后只查询本次 run_id label 的容器与网络；两查询均需rc0且stdout空，保存stdout/stderr/rc。查询失败不会当零残留。工具没有越权删除别人的对象；具体 candidate/manager finally 清理沿原 CLI/manager。

最后 result 状态仍是 completed_pending_raw_readback_and_independent_review，formal_cpu_accepted=false、actor_executed=false；实际 reward 与 planned0不符则最终非零。没有自主模型、CC训练入口、FrozenPatch旧身份重绑定、a2g或 typed-actor 资格授予。

## 5. 安全 launcher 与部署证据

launcher 固定 R21 release SHA、四件工具集合及 manifest SHA、解释器/PYTHONPATH/输出根；按独占 job ID 发起。运输不覆盖不同字节，检查成员集合、symlink 与 SHA/bytes，固定文件/目录权限；本次独占回执名为 moto6114_r21_exact_tools_transport_receipt.json，与 R19及其它 UID/actor回执区分。审查时该新运输回执尚不存在，不把准备脚本视为已运输或已执行。

实际矩阵整个 child 由既有 control/cpu_slot.py --mode run --package swe_moto 包裹，同仓槽范围涵盖 prepare/inspect/export/run/收口，而非只圈某个评分阶段。清除 RH2_IMAGE_OVERLAYS_PATH/SHA，固定原 runtime_cpu_v2 Python。调用记录仅含任务/固定版本/输出信息，没有连接参数。静态检查安全捕获/输出和异常处理，raw连接stdout/stderr仅落忽略证据文件，对外打印状态/rc/error_type；无 host/key/SSHargv/raw连接错误输出。本核未调用 launcher。

已独立读发布者原回执及其直接部署原件：

| 原件 | bytes | SHA256 |
| --- | ---: | --- |
| publication_cpu_takeover_20261003/r21/moto6114_publication_receipt.json | 4219 | 670af8483b847a08714d46fff7d6946fb6b8ecdec0e5bf6d8544df147b6d64d1 |
| cpu-a/release_receipts/cat2-cpu-r2e093-swe40-moto6114-prepare900-20261003-v1.json | 1049 | c4f327ccfb8b54b10827d74f679209c2aa1f247831caf4822ebc1d97f540ea1f |
| 同部署回执 .readback_stdout.log | 195 | dfb1db7f9e22cc4e42c048fbcf828fb17551be6205ecdaf63f7c0a11179b4cbb |

部署回执的release/manifest身份一致；真实 trusted stdout 是1482成员、48 R2E/216 SWE 的读取完成 JSON，stderr实物为空，明确 CPU_NOT_RUN。这支持固定版本已部署和原可信加载读回，不能代替本次 exact 的运行验收。作者导航 moto6114_r21_support_publication_owner_readback_20261003.json 为14715B、SHA d93174fe6e78fa787b9d3e64dbaa4132a1b1b88d6cf9a573de4c004739ee745c；其中19对源码由我实际读取比较，其 support_ACK_revision=5 是导航/题主提供的协调状态，本报告未另连接协调线程核 ACK。

## 6. 待实际原件验收的最小事项

本次无须静态修工具，也不要求重跑 R19 已有效三臂。单 exact 闭合后，仍须独立读真实 ledger、保护/reset调用与限额、完整 install/test输出、37参考逐项状态、实际 FP投影、candidate/manager/footer和本次归属资源查询。若仍发生基础设施/解析/清理错误，保留其 null分数并由支持流程处理；不得用 parent退出或计划reward代替这些原件。

既有历史公开 CC及 R19 UID 的条件范围引用固定 partial报告 moto6114_r19_partial_cpu_non_author_20261003.md（SHA 35fc2312ddadc6485f7511582e2cd6585048f756982e0ceb7bcda9e523484ec4）。本次19对 actor/helper源码和 rollout函数相同只支持其既有适用边界不被此增量扩大，不是 fresh CC、盲解题、a2g或训练声明；更不能跨物理 GPU 镜像推定900自动生效。待本次唯一未评分臂产生有效原件，再判新37整体 CPU结论。
