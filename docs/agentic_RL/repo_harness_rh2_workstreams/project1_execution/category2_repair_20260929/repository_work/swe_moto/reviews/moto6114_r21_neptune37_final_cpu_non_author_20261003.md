# Moto6114 Neptune 新37参考最终 CPU 非作者验收

日期：2026-10-03。审查者为非作者 subagent，已接触本题私有金标、对照补丁及历史模型源码；不是公开盲读者。本报告仅新增，不改任何既有报告、固定输入、发布材料、工具、原件、旧 FrozenPatch 或 rawscore。

## 结论

**新37参考已具备提交当前普通双模型探针的题级 CPU 条件，未发现该用途的剩余阻断。** 已审并保留的 R19 noop/gold/wrong_first 为0/1/0；本次唯一恢复的 R21 exact_qwen 得到有效的 unresolved/tests_failed/reward0。四个有效臂均完整覆盖37项参考、原 make init 成功、候选与 manager 正常清理。本次 exact 原35项全部通过，只在新增的 Neptune name start/delete 两项失败，实际失败栈与此前代码行为诊断相符。

**这不是四臂全部同预算运行。** R19三个有效臂 reset300，R21单 exact 使用发布者固定 CPU1d8d 保护政策 reset900；其它材料、参考、脚本及预算不变。旧 R19 exact 的300秒 control_surface_protect 超时、infra_failure/null 分数仍保留，不能改记0。无需机械重跑三个有效臂。

实际 UID54321 的原公开 make init、激活、模块/SDK和清理已在固定 R19 原件中验证；历史真实 CC 三条公开开发命令按既有条件范围复用。未执行 fresh R19/R21 CC、完整新题面自主求解、真实 actor FP/a2g或训练验收。当前结论只支持普通诊断探针题级 CPU 准入，不授予 typed-actor/训练资格，也不证明不同物理 GPU 镜像自动应用900政策。

本轮只做本地标准库读取、hash/JSON、只读 tar 成员、文本比较及内存补丁应用；没有执行项目、SDK、测试、Docker、CPU、SSH或模型，没有读取6185或在途作业。

## 1. 新原件身份与已固定证据复用

新证据根为 runs/category2_repair_20260929/moto_cpu_20261003/moto6114-cpu-9b1ef9d10723_evidence。独立核 transport_manifest 的 **46件运行原件、822367 bytes**：目录集合恰好对应清单、无 symlink，每件 SHA256及长度全部匹配。只读归档中的46件与 manifest 本身共47个常规文件，逐字节等于本地原件；未提取或回写。

| 新原件 | bytes | SHA256 |
| --- | ---: | --- |
| transport_manifest.json | 7637 | a7166a7f0680e2f519d87b2059fa0d78eec6db5eb8139b7500f375f989c9756b |
| moto6114-cpu-9b1ef9d10723.transport.tar.gz | 158537 | 9ffa9628e31ed9ab1dd50aa4bb3b882f6e3828146b60fe6a21619d245adec74e |
| 同job transport_receipt.json | 553 | 886ad6330024a534f95713b9453aa4d1780e86c7183f7cab944e6ef831d00c74 |
| exact_qwen/ledger.jsonl | 13533 | 09853a2ba177731ed35ccbdec3a5483190b16cdeece3ee9b57c1a4450a94148b |
| 完整 exact eval.log | 50127 | d4e00f53d8dc699e9c5b441adf7722a8ba0244ce02efb51f8bc2959d1aa28ad9 |
| exact diagnostics.json | 11676 | b39b8ef7d25853dfe98af6345cb8a24fd7b1200e96b2d2ea763bb112709f6037 |

实际 job/status 为 finished、parent0，始末时间05:11:01Z至05:15:42Z；整矩阵 child 在原 CPU slot0内，只选 exact_qwen。job stdout 五阶段 verify_release/image_inspect/prepare/export_gold/run_exact_qwen 均实际rc0，job stderr空。新CLI实际 argv调用固定 R21原入口，不是作者读回函数替代评分。

复用固定 moto6114_r19_partial_cpu_non_author_20261003.md，20731 bytes、SHA256 **35fc2312ddadc6485f7511582e2cd6585048f756982e0ceb7bcda9e523484ec4**：该报告已独立核121运行原件（noop44＋gold/wrong/exact71＋UID6）及3归档。本轮核其固定SHA，增量读三个有效ledger/footer、旧未评分exact、UID实际调用、必要 prepared/FP绑定；不重复全量语义审查或虚称本轮重新读取121件全部内容。总验收依据为先前121件加本次46件，共167件及4归档；其中旧基础设施失败原件也保留，不把167件解释成167次有效评分。

| 已固定作业 | 范围 | manifest SHA256 |
| --- | --- | --- |
| moto6114-cpu-4b4f57ea39ed | R19 noop；parent0 | 2268e485f4e983e8a8095295834763698b0b15f07874662d1021b166c54ef9c8 |
| moto6114-cpu-fb987905af02 | R19 gold/wrong有效，旧exact infra/null；parent1 | bb972c4f7f01d39b7e5156b0c915a15515150ca34b1a95df3becfa43937ad93d |
| moto6114-uid-68f461740f14 | 实际开发UID原安装；parent0 | 017400b652a49ef1a898396c7ddb7e1cbe5a489627b14a9ae8269be8b135197a |

作者新导航 reviews/moto6114_r21_exact_cpu_owner_readback_20261003.json 为13113 bytes、SHA256 **6db6e2a78726958ffcfc87604126908db1700fe4aaf39c3fa953974e06cf7cfd**；其原始读回输出15276 bytes、SHA256 **fd89f418763ab0840de8400ba2eb89d2b3ab4f5345dcb03a5571fe2eb9d65e26**。先核实际原件，再比较其report/安装/测试/参考/FP/清理字段；相符，不以作者true替代独立读回，也没有执行作者读取器或导入项目 parser。

## 2. 原材料、实际消费与300/900差异

R19 release为 cat2-cpu-r2e093-swe40-pyd6283-moto6114-20261003-v1，manifest **2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e**；R21为 cat2-cpu-r2e093-swe40-moto6114-prepare900-20261003-v1，manifest **630f71fc1a4ae6f587f3161fae56d92927a91801ae4b08954a556ee059cada9c**。新 verify_release 实际stdout报1482成员、48 R2E/216 SWE核读完成；这是固定发布的读取阶段，正式评分另有真实ledger和eval log。

增量静态政策/入口依据固定 moto6114_r21_exact_tools_non_author_20261003.md，13897 bytes、SHA256 **0695d96bb83f660b22fc0a5d6a1f3c2715dd7b3ec406a767de5bca922b660e71**。本轮实际 consumer_readback_before_checks 仍与 expected_runtime.json逐字相同，6024 bytes、SHA256 **556a41c525a8b9931832b0f0c2ca875dc61d5cbab2b0f80543fe2c60daf67166**。

新/旧 runtime_inputs 解码对象只差 code_manifest_sha256：R21为6827 bytes、SHA256 **cde9fa789b358f838ac97ad23a5cbf8c7108816ca5acc5090838b19007cb68f4**，R19为同长度、SHA256 **c4e27ea4a78f76d3c6761975a103079ef0d9e4f4dac73242729a4bc9dbf8cf33**。原 public prompt、rollout view及private host_grading_view也逐字相同；新 prepared manifest直接固定这些成员摘要。

| 实际消费项 | 固定值 |
| --- | --- |
| task/base | swe_gym_lite::getmoto__moto-6114 / f01709f9ba656e7cf4399bcd1a0a07fd134b0aec |
| public digest | 6c8f45da003f8e8d1e065d1801afa4659c43cbb212e319a5d07a84922af5f0f2 |
| ENV digest | 941bebb539b3974ff894822f9920fdd07227f6a8cf08eaa5c31173f90ea206b2 |
| 新37 grading digest | 0d7a09c24df12b581adc180c577da3c947d6446ab64ec9f01789b4cc08f5afd6 |
| registry / revision | 6aecd8d4f9eb40b0a82af7faae73121dc2a0292122876166765f9ecd4a5d8bd1 / moto6114-cluster-identity-neptune-preservation-v2 |
| effective test patch SHA | 2a9661d78743cf5e36f8363e308d63260ab2076bf4bc1d68de8a9e5fd226dda4 |
| scripts aggregate SHA | 36b05c97ac33b4f10070b5ccf35af953d8c54631ddec71f10d0cc8701ea67cab |

原 install/test仍为 **make init** 和 **pytest -n0 -rA tests/test_rds/test_rds_clusters.py**；参考保持原1F/34P加两条已批准的 Neptune name P2P，合计1F/36P=37。逐参考顺序、五个脚本SHA、原测试恢复保护集合及parser均不变，没有重新定义原题面、AWS要求或私有断言。

实际 inspect来源ConfigID为 fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249，manifest cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a；CPU派生ConfigID为 **1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5**。来源13层是派生14层的完整前缀，额外仅一COPY层，实际ENV含PIP_NO_INDEX=1、PIP_FIND_LINKS=/opt/rh2/build-wheels。CLI --derived-image实际传1d8d，recipe仍 moto6114_install_wave1_copy_only_20261003，overlay=null，不借旧GPU43f/其它GPU条件。

本次新ledger明确记录 env_reset_timeout_seconds=900和固定政策：policy SHA **515cb3e8341a62d943f778b5118372733cc7ec78001a85dfc3dd783bc68ba36c**，request_id swe-moto6114-control-protect-timeout-support-20261003-v1，input SHA **3c986d8b21b4bf70de0aef7ea80a25eb69df74e79bc6815efd7bf70ef7f39ddf**。已再次读固定原 replay分支：实际inspect成功及ConfigID/材料匹配后才修改传给manager的完整spec，而非仅修改账本；default source仍300。runtime_inputs中的setup300是默认prepare回读，不冒充实际评分900。

R19三有效臂依据原spec/runtime绑定使用reset300（旧ledger未增列reset字段）；R21新exact为900。apply120、test1800、candidate900、whole grading1800、cleanup120、image_pull1800秒保持。一次恢复成功不证明900是该次成功的唯一原因或揭示旧超时的宿主根因，结论仅限固定支持条件下实际评分已完成。

## 3. 四个有效臂的逐参考结果

R19三臂完整日志/逐参考核查沿固定partial报告保留，本轮又核ledger/footer与新材料绑定；R21 exact完整读取802行eval log，独立重建pytest短摘要37个唯一状态键，与原固定参考集合、ledger及diagnostics分区逐项相同。无重复、missing、skip、unaccounted或范围外解析项。

| 有效臂 / release / reset | 正式reward | 原make init / 秒 | 原pytest / 秒 | 原1F | 原34P | 新2P |
| --- | ---: | --- | --- | --- | --- | --- |
| noop / R19 / 300 | 0 | 0 / 10.871 | 1 / 6.204 | 失败 | 全过 | 全过 |
| gold / R19 / 300 | 1 | 0 / 11.244 | 0 / 8.408 | 通过 | 全过 | 全过 |
| wrong_first / R19 / 300 | 0 | 0 / 11.661 | 1 / 9.644 | 失败 | 全过 | 全过 |
| exact_qwen / R21 / 900 | 0 | 0 / 10.652 | 1 / 8.414 | 通过 | 全过 | 两项失败 |

gold为resolved/null failure_category；其它三个有效负臂为unresolved/tests_failed。noop仍在目标B ARN describe处报DBClusterNotFoundFault；wrong_first在新37版本 test_rds_clusters.py:269实际 'cluster-id1' != 'cluster-id2'，不能因为返回了某个集群就计通过。其旧34P和新增2P均实际保持。

本次exact原安装实际两轮离线editable构建/安装Moto成功，未跳过或失败；install/test开始结束及RC标记均唯一成对，完整输出尾部存在。原pytest收集37项，短摘要35 PASSED/2 FAILED；正式report f2p_pass=1/1、p2p_fail=2/36、outcome=unresolved、failure_category=tests_failed、reward=0.0、infra_failure_detail=null、stage_error=null、num_parsed_tests=37、reference_missing/skipped=[]。

包装exec_exit_code=0与内层pytest rc1不同；新CLI0/parent0表示运行和正常收口成功，不表示37项全过。日志实际Python3.12.4、pytest8.3.2、rootdir=/testbed、conda testbed；依赖输出boto3/botocore均1.35.9，Moto从工作区导入，runner integrity未变。

### 新exact的两个具体失败

- **start**：tests/test_rds/test_rds_clusters.py:833，两个mock隔离下按名称创建Neptune cluster，先实际确认status='available'。backend.start_db_cluster(name)进入候选RDS start分支，moto/rds/models.py:2018因状态不等于stopped而抛InvalidDBClusterStateFault；日志明确Code和Message，不是SDK/安装/收集失败。
- **delete**：tests/test_rds/test_rds_clusters.py:848，先实际确认名称在backend.neptune.clusters。backend.delete_db_cluster(name)进入候选RDS delete分支，moto/rds/models.py:2003读取 cluster.deletion_protection，Neptune DBCluster缺该属性而报AttributeError；尚未完成原名称删除路径。

这两个正式新37失败分别对应此前独立两容器诊断的既有名称回退问题；本轮没有扩成任意ARN写操作、真实AWS规则或额外功能需求。原35全部通过是完整37分区的实际状态，并非只运行旧测试选集后推定。

## 4. 新物理FP及源码精确投影

本次candidate.patch为6463 bytes、SHA256 **bb5eab97577260270def73fc06f8a0aa4917727cb9348afbe871f5905b2eb747**；逐字等于固定R21 registry/source_members及旧R19实际candidate.patch。stage记录原base HEAD、git_apply、apply_user agent/54321、无stage错误；classification projectable/reason_codes=[]、runtime_private_pathset_changed=false。

新FP只含 **moto/rds/models.py modify / regular / mode100644**，无测试、fixture或conftest路径。baseline该文件为原公开base，160973 bytes、SHA256 **a614a137f21dce20445cad98611e578b435d4f09a592ced584d887d9edb9250c**，mode100644。标准库只读历史baseline.tar中的这一公开成员，对本次diff的5个hunk逐旧行/计数核验并仅在内存应用；所得完整161961B与新FP解码内容逐字相同，SHA256 **05e9b6a1d3f57caaeba1a616fa3a1a9529ffa6f6aa6d91be9a5963a239b5171d**。

同一payload又与R19未评分FP、先前Neptune诊断candidate_rds_models.py及旧GPU FP单entry解码内容逐字相同。独立重算canonical JSON digest，baseline和新projection字段均相符；不是靠作者same=true或文件名推定。

| FP | 文件SHA / bytes | canonical digest |
| --- | --- | --- |
| 本次R21新FP | 8c28d105ebcad08be536fbdfbf446e339b8a7199ad47cb6985ab1efcf41ca888 / 216923 | d877559634988e9b0cc1b9df028f1f7b436fdcbb6c8cadbb68aaa53c9433921e |
| R19旧未评分FP | 沿固定partial报告保存 | b2d54a17d4526e3a4f8290ecf0624f58312c6ce6a7af06cd7a96d89905e16538 |
| 旧GPU FP | 6acc1b2d3de238b08780adfb493883abe617aa1c0e1983fdbda9a0bd2fc8405c / 216817 | 68557bc28b72fb3f45912e70d585b7c296ec1a7d1ec7a6e9eec57ce82f5f40d8 |

本次physical_attempt_id为 replay-moto6114-cpu-9b1ef9d10723-exact_qwen-swe_gym_lite--getmoto__moto-6114-611fc79c，旧R19后缀为c7ffb43b，旧GPU为gpu1003-moto6114-qwen36-a1#p1。旧GPU runtime为43f685f4308354a90d8d88d3a2fd31dcc01bdd41fff3f04210d2668281716e20，本次为CPU1d8d。不同物理尝试形成不同FP身份；旧FP/raw1与其安装/重grade上下文未修改。本次只能记“固定旧实际源码内容在新37和本CPU条件下的诊断得分0”。

CLI ledger candidate.kind='cc'是patch输入分类，本次实际输入为patch:路径，没有运行真实CC。此机械候选FP不等于真实模型actor导出，不能转成新actorFP/a2g证明。

## 5. 可信恢复、保护与双层清理

candidate sanitize保留HEAD、历史7454，删除52ref、余186，remotes/reflog/unreachable0、violations空。grader sanitize同base条件；trusted_setup原件显示restore1/apply0、expected/actual test文件1、absent0/irregular空、RH2_SETUP_OK1。control_surface实际自证EXPECTED_FILES1、PROTECTED_FILES1、PROTECTED_DIRS3、RH2_PROTECT_OK1、missing/irregular空。本次评分已越过旧未完成的保护阶段。

新ledger policy为grader UID54322、2CPU/4GiB/PID512/shm64MiB、deny_all；与R19相同。resource_facts=null、env_qualification='absent'、reference=null保留原义，不将普通策略/日志字段升级成训练所需资质。trusted_setup阶段计时151.281242秒、delta_apply0.375023秒、test阶段20.630531秒；原安装/pytest净计时如上，阶段计时不能与其混为同一指标。

本次candidate cleanup removed=true、steps=[rm:ok]、detail空。原CLI完整最后footer：rows1、halted/aborted=null，manager containers_created_total1/removed_total1，containers_open/supply_open/cleanup_failures=[]，regrade_total0；final_status.exit_code0/reasonok、grader_containers_open=[]。完整run stderr空。随后本run_id容器和网络两查询都实际rc0、stdout/stderr空，查询失败没有被解释成零残留。

R19三个有效臂candidate和manager双层清理、noop/gold/wrong自有查询沿固定报告保留；本轮再次核其CLI完整footer。旧R19 exact原CLI/footer也关闭成功，薄矩阵因正常report guard拒绝infra/null才parent1。其归属资源由闭合后独立 moto6114-cpu-fb987905af02_finished_absence_readback_v1.json确认，1253B、SHA256 **668e14fb1f96a44602154f79b3b7ef490126fca2ccc82d6abd4f732e517cf90a**；不伪称该追加回执属于原71件manifest，也不拿清理补其评分。

新result仍标pending raw readback/independent review、formal_cpu_accepted=false、actor_executed=false；这是作者薄工具应保留的未审状态。本报告依据原件完成题级独立CPU结论，不回写result或把它的布尔值当验收。

## 6. 实际开发UID与历史公开CC的条件范围

固定 R19 UID job moto6114-uid-68f461740f14原6件已在partial报告逐hash核。本轮增量读取13次Docker调用和result，实际调用全部rc0，原公开安装第7次以user54321、HOME=/home/agent、BASH_ENV=/rh2/bash_env，在/testbed执行 PYTHONDONTWRITEBYTECODE=1 make init。两轮离线editable安装Moto成功；完整stdout21045B、SHA256 **5de98bdc49917a78ebba9560952fcdbff65ec92d2a4c51449af3d644d0b672c4**，stderr426B、SHA256 **ed35e0e19a25feaf7ed5c8ae560c1768d041c025c8d733fb28ad3ece924d8f7f**。用户bin的两条PATH警告不构成安装失败，未扩大成moto_server CLI PATH验收。

生产sanitize/init/activation实际成功；独立identity调用与result一致：UID/GID54321、cwd/testbed、HOME/home/agent、testbed解释器/prefix、Moto路径/testbed/moto/__init__.py，RDS完整模块SHA为原a614…250c，boto3/botocore1.35.9。两次实际inspect核CPU1d8d、归属label和NanoCpus2000000000/Memory4294967296/PidsLimit512/ShmSize67108864/NetworkMode none；rm0，最后容器/网络查询rc0且完整stdout/stderr空。此为开发UID安装原件，不是grader/root安装代证，也不是CC。

R19/R7公开开发条件比较依据固定 partial第8节及其真实source/prompt读取；R21/R19增量依据固定R21工具独立报告。此前已逐文件核17个actor相关源码加2个真实DevRunner helper共19对全字节相同，rollout_spec_from_view函数正文相同。本次原prepared prompt/view与R19又逐字相同。R19相对R7仅ENV的grading link变化，base/source/COPY供应和公开开发helpers不变；新实际UID安装/模块/SDK事实满足既定有限复用条件。

历史独立报告 moto6114_public_actor_reuse_non_author_20261003.md仍11429B、SHA256 **5d81a1c39477825eef278b2cf237f5b472a6b1c0ea787c8b0c62367980eba642**。保留其真实CC三命令证据：identity rc0，B实际ARN查询的预期DBClusterNotFoundFault rc1，公开-k describe_db_cluster为4passed31deselected。历史base/公开路径证据不能改称新版私有37项测试曾进入actor。

历史CC物理derived为aaf97…，与当前1d8d不同；历史首请求是Devcheck指定tool calls，使用确定桩，无冻结导出。因此复用只覆盖这些已验证公开开发功能路径，未补出fresh R19/R21CC、完整公开题面真实请求、模型理解/自主解题或actor→grader事实。

两项legacyfalse继续保留：interpreter_in_tool_result=false因原通用匹配只找RH2_SYS_EXECUTABLE，命令实际输出的是正确testbed路径的PY_CHECK；bashenv_denied_for_agent=false因这三条命令没有在CC tool_result执行/返回RH2_BASHENV_WRITE=DENIED标记。历史prelaunch写拒绝仅保留该预检范围，不能静默改true或称CC通道全套安全通过。

## 7. 准入用途与尚未证明的事项

本题原1F/34P的ARN身份要求与两条已批准既有Neptune名称P2P已由四个有效控制完整核到；gold37全过，noop/wrong保留具体目标失败，固定实际Qwen源码能通过旧35而在新增两P2P分别失败。真实安装和清理有效、UID开发安装有效、历史公开CC有限复用条件明确。**就当前普通双模型诊断probe的题级CPU准入，没有剩余必补项，可以提交新37普通probe。**

提交与后续结果应显式携带R19三臂300/R21单exact900差异，不写成四臂同条件；旧R19 infra/null不转成0，旧GPU raw/FP不改绑。当前不同物理GPU镜像的政策匹配和实际预算未由本CPU结果证明；不能凭same source/recipe声称GPU已获得900或已恢复。ordinary probe与训练准入分开，后者所需fresh CC/fullprompt、真实actor FP/a2g及typed-actor资质仍未验证，本报告不授予。
