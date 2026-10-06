# Moto6114 R19 部分 CPU 原件非作者窄核

日期：2026-10-03。范围：固定 R19 新37参考中的已闭合 noop，以及 gold／wrong_first／exact_qwen 作业，另增量核新 R19 UID 原公开安装与 R19/R7 公开开发条件。审查者不是工具、材料或作者读回的作者，已接触私有对照／金标，非公开盲读者。本轮只新增本报告，不改旧35验收、旧模型原始分数／FrozenPatch、固定输入或原件。

## 结论

**可以保留 noop=0、gold=1、wrong_first=0 三个有效的新37评分结果，以及新宿主 UID54321 原 make init 成功的开发环境证据。不能宣称新37最终 CPU 验收通过。**

exact_qwen 的实际 report 是 **failed_to_grade／infra_failure／reward=null**，detail 为 grading_control_surface_protect_timeout_after_300s。它已经完成候选 apply、冻结投影、grader baseline、可信测试 restore/setup，但在保护控制面阶段超时，原安装与测试均未执行。不能将它记作 planned0已兑现、模型0、两条新增P2P已失败、旧Qwen raw1被推翻或全题语义失败。

三臂作业 moto6114-cpu-fb987905af02 的 parent1是薄矩阵正常评分 guard 拒绝上述 infra report 后抛出的结果；原 exact CLI仍返回0，footer清理正常。两个退出层级不能混淆。剩余的是**一个未评分臂的基础设施支持与恢复读回**，不需要机械重跑已经有效的三臂。本报告不运行支持，不修改预算，也不新增审批。题主告知支持已交发布者，R21窄策略拟仅对本题 exact v2材料、显式CPU derived1d8d条件调整保护/reset限额，尚未部署／验证；本报告不静态认证该未来实现或预先判断恢复成功。

本轮仅做本地标准库文本、JSON、hash、只读tar成员与内存补丁应用核对。没有执行项目、SDK、测试、Docker、CPU、SSH、模型或远端，没有读取6185在途作业。无新增CC／自主模型／actor冻结／a2g或训练资格声明。

## 1. 原件运输身份和实际终局

证据根：runs/category2_repair_20260929/moto_cpu_20261003/。独立逐件核各transport_manifest列出的SHA256、字节数、常规文件身份；共 **121件运行原件、2,985,316字节**（noop44＋三臂71＋UID6），全部相符。另只读归档每件manifest成员与manifest本身，逐字节等于本地原件，未解包或回写。三份transport receipt中的archive SHA/bytes、manifest SHA/count和原件状态均相符。

| 作业 | 实际范围／终局 | 件数／总字节 | manifest SHA256 |
| --- | --- | --- | --- |
| moto6114-cpu-4b4f57ea39ed | noop；finished、parent0 | 44／593567 | 2268e485f4e983e8a8095295834763698b0b15f07874662d1021b166c54ef9c8 |
| moto6114-cpu-fb987905af02 | gold／wrong_first有效，exact基础设施失败；finished、parent1 | 71／2296327 | bb972c4f7f01d39b7e5156b0c915a15515150ca34b1a95df3becfa43937ad93d |
| moto6114-uid-68f461740f14 | UID原开发安装；finished、parent0 | 6／95422 | 017400b652a49ef1a898396c7ddb7e1cbe5a489627b14a9ae8269be8b135197a |

| 作业后缀 | archive字节 | archive SHA256 |
| --- | --- | --- |
| 4b4f57ea39ed | 117185 | 36a747d3dc82794ca7721608d0b209fec41742c5365360019824592207db1716 |
| fb987905af02 | 435529 | e96c19031a7bbfa22e6306714007538ce514c139f939c81fb13be378b0aebde1 |
| 68f461740f14 | 17126 | 9b83dbc9848862708ca8b9d7f95275b36d3f9f8cceb3824aeb08272d73d9a49f |

作者 reviews/moto6114_r19_partial_cpu_owner_readback_20261003.json 为32221字节，SHA256 f54d7ec99d0f2f629fb8e5458044a695d8b66e75ed0d357946eb88e851da4aee；成功两臂的 moto6114-cpu-fb987905af02_author_partial_raw_readback_r19_v1.json 为29380字节，SHA256 3087d72ca245f9509cce4b290589fc121bfc3a2b9c699e22cfab214c478d2d85。仅作导航：先核原件，后比对作者三臂report/cleanup，以及成功两臂逐参考状态，均相同，未用作者true代替读回。

## 2. 固定R19消费与同条件

沿用已固定 moto6114_r19_matrix_tools_non_author_20261003.md 的薄工具静态范围，不重审发布全部1476成员或题级语义。R19 release为 cat2-cpu-r2e093-swe40-pyd6283-moto6114-20261003-v1，manifest SHA256 **2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e**；registry SHA256 **6aecd8d4f9eb40b0a82af7faae73121dc2a0292122876166765f9ecd4a5d8bd1**。两次作业的runtime_inputs逐字节相同，6827字节、SHA256 **c4e27ea4a78f76d3c6761975a103079ef0d9e4f4dac73242729a4bc9dbf8cf33**。实际consumer_readback_before_checks对象与固定expected_runtime完全相同（6024字节／556a41c525a8b9931832b0f0c2ca875dc61d5cbab2b0f80543fe2c60daf67166）。

| 身份项 | 本次实际固定值 |
| --- | --- |
| task/base | swe_gym_lite::getmoto__moto-6114／f01709f9ba656e7cf4399bcd1a0a07fd134b0aec |
| public bundle | sha256:6c8f45da003f8e8d1e065d1801afa4659c43cbb212e319a5d07a84922af5f0f2 |
| ENV bundle | sha256:941bebb539b3974ff894822f9920fdd07227f6a8cf08eaa5c31173f90ea206b2 |
| grading bundle | sha256:0d7a09c24df12b581adc180c577da3c947d6446ab64ec9f01789b4cc08f5afd6 |
| revision | moto6114-cluster-identity-neptune-preservation-v2 |
| materials | sha256:ea5d966eb5dfe35b9b4a8a4f5732d7fdf4c8383bc2558302a5d60c4f795ab29e |
| effective patch | sha256:2a9661d78743cf5e36f8363e308d63260ab2076bf4bc1d68de8a9e5fd226dda4 |
| scripts aggregate | sha256:36b05c97ac33b4f10070b5ccf35af953d8c54631ddec71f10d0cc8701ea67cab |
| source manifest | sha256:cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a |
| source ConfigID | sha256:fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249 |
| CPU actual ConfigID | sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5 |
| registered COPY recipe | moto6114_install_wave1_copy_only_20261003 |

public source face保留 xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6114:latest。实际image inspect两次均给出source13层、derived14层，source是完整前缀，actualENV含PIP_NO_INDEX=1和PIP_FIND_LINKS=/opt/rh2/build-wheels。原prepare/export-gold/run命令、退出和stdout/stderr已读；四个前置阶段verify／inspect／prepare／export均RC0、stderr空，原run明确传registeredrecipe和CPU1d8d exact override、无overlay。本次不借GPU43f／613条件。

预算仍setup/reset300、apply120、test1800、candidate900、whole1800、cleanup120、pull1800秒；ledger评分策略为UID54322、2CPU／4GiB／PID512／shm64MiB、deny_all。resource_facts为null、env_qualification absent，不把策略字段或UID容器的actualHostConfig变成训练所需的全量grader资质。

## 3. 三个有效评分臂的完整37参考

完整读取三份eval log、diagnostics和ledger，分别独立重建每条pytest短摘要状态；每臂实际收集37项、短摘要37行、解析键37、无重复／缺失／skip／XFAIL／范围外键。实际状态集合恰好是固定1F、原34P及新增2P的并集；再核diagnostics各分区success/failure/missing/skipped/unaccounted，完全相同。

| 臂 | 正常report | 原make init | 原pytest | 逐参考 |
| --- | --- | --- | --- | --- |
| noop | unresolved／tests_failed／0 | 0；10.871秒 | 1；6.204秒 | 1F失败，原34P全过，新增2P全过 |
| gold | resolved／null／1 | 0；11.244秒 | 0；8.408秒 | 完整37项全过 |
| wrong_first | unresolved／tests_failed／0 | 0；11.661秒 | 1；9.644秒 | 1F失败，原34P全过，新增2P全过 |

三臂原命令均为 make init 与 pytest -n0 -rA tests/test_rds/test_rds_clusters.py；完整安装／测试开始、结束和RC标记唯一成对，candidate_segment_completed=true、install_skipped=false、install_failed_commands=[]、log_partial=false。包装exec0与内层pytest1明确区分；noop／wrong_first的测试失败有具体语义位置，不能因为原CLI0就称全部测试通过。

noop的 test_describe_db_cluster_after_creation 在R19第267行对B的实际ARN调用describe，报原目标DBClusterNotFoundFault。wrong_first已经返回到身份断言，但第269行实际 **'cluster-id1' != 'cluster-id2'** 失败。该R19行号与旧35版本的行号不同，不倒写旧报告。

两条新增参考是 tests/test_rds/test_rds_clusters.py::test_rds_facade_preserves_neptune_name_start 和 ::test_rds_facade_preserves_neptune_name_delete；三次真实结果均PASSED。这只能证明这三个实际候选下两条P2P通过，不能拿来填exact_qwen未执行的两条状态。

| 完整eval log | 字节 | SHA256 |
| --- | --- | --- |
| noop | 45902 | 0c021b59203e176bde202101b68e64c78bddeecdf18e62d7d3868abb4dcc7b9b |
| gold | 41666 | 2b362a075200230ddeb412e9f888f29f5970b40da42a909b603bc8ef40762094 |
| wrong_first | 43023 | 3d7edd915f8a8997032736c6c053ef08a7e364e84ac21d73d4700096d9970c2c |

## 4. exact_qwen基础设施失败的准确位置

exact_qwen ledger的stage_error=null是候选准备阶段已完成，不是评分成功。它的实际report为failed_to_grade、failure_category=infra_failure、reward=null，f2p/p2p数值全部null，detail精确为 **grading_control_surface_protect_timeout_after_300s**。install=null、test=null；diagnostics.candidate、control_surface、observations、verdict均null。完整eval log14999字节、SHA256 **db3d3dfaaf5ea96f826d3d85bed6b6b455dc0797b987f9c8f205bf3b68a62cba**，只保留可信restore/setup前缀和attest；没有make init、pytest、安装／测试开始或RC标记。

原manager代码的执行顺序为trusted_setup与独立attest核验→control_surface_protect（timeout=spec.env_reset_timeout_seconds）→后续候选观测／安装／测试。其_exec_bash_checked在该阶段TimeoutError时明确产生grading_<phase>_timeout_after_<timeout>s。故原件中的300s错误与实际阶段相容，且发生在候选代码执行前。delta_apply已完成、grader sanitize有效，trusted_setup显示restore1/apply0、预期/实际test文件1、缺失/irregular空、RH2_SETUP_OK1。grader_trusted_setup计时301.463553秒支持这一阶段超时，但不证明内部哪条权限命令或宿主I/O是最终根因。

因此本次只能认定评分基础设施未完成保护阶段；不能具体归咎模型代码、安装wheel权限、测试断言或SDK。此前两容器Neptune诊断发现的两个实际代码行为回归仍有自己的原件，但**不等于本次新37正式评分已得到0**。

三个run_*日志都记录原CLI returncode0，rows1、最后final_status.exit_code0/reasonok、正常manager_close。薄矩阵在第185行正常outcome/failure_category/reward guard因exact report不符合正常组合而抛RuntimeError，父job遂1；没有output/result.json成功矩阵终局，也没有把未知reward当普通expected不匹配继续包装。这个guard在实际异常上工作，既不能消除infra，也不让已有gold/wrong_first结果失效。

## 5. 实际候选内容、模式与旧模型身份保全

对公开base RDS源码160973字节、SHA256 **a614a137f21dce20445cad98611e578b435d4f09a592ced584d887d9edb9250c**作标准库只读：读取旧模型baseline.tar中的单个公开base成员，不提取或执行工作区。再对三份实际candidate.patch逐hunk检查旧行、计数、位置，**仅在内存应用**；结果与新CPU FP解码完整内容逐字节相同。未使用题主scratch的git apply结果代证。

三臂实际输入patch分别与本次原CLI export-gold的固定pin、原degenerate_first_object.patch、R19冻结source_members/exact_qwen_a1_source.patch完全相同。每个FP只有一条moto/rds/models.py modify、regular、mode100644；baseline文件也为同a614原base／100644。classification为projectable、reason_codes空、runtime_private_pathset_changed=false；独立canonical JSON SHA重算新FP与baseline digest，和projection/FP字段相符。noop FP entries为空。

| 臂 | patch SHA256／字节 | actual payload SHA256／字节 | 新CPU FP canonical digest |
| --- | --- | --- | --- |
| gold | bfae681e1044acffe64d7d65c1615b5545f4b62b2625961b7a6fe7d0ad591bbc／635 | 00e61d1980f71fb4b0f37fa8e517a1fd3778c8ac5d687e4847d27217c5bc1c5b／161153 | sha256:2b85d63fd97edb11e7fbefa4f57f53e46092c0dd21050e009c636d0e5f3b7884 |
| wrong_first | 5c042121e4bf56693c71f418c139b628d108b0c1fcd67bc0af48201e471c6451／492 | a5e0c305e9981b61209a2fc3bc4e2c40944fade972a4ff28b5ed0fc54b81815e／161120 | sha256:db58080d50f5621b815189aa381fe15cdd801d6260a61f95e08cfc0fedb090cc |
| exact_qwen | bb5eab97577260270def73fc06f8a0aa4917727cb9348afbe871f5905b2eb747／6463 | 05e9b6a1d3f57caaeba1a616fa3a1a9529ffa6f6aa6d91be9a5963a239b5171d／161961 | sha256:b2d54a17d4526e3a4f8290ecf0624f58312c6ce6a7af06cd7a96d89905e16538 |

exact payload还与先前moto6114_neptune_name_diagnostic_inputs_v1/candidate_rds_models.py逐字节相同，非同文件名推定。旧GPU attempt/frozen/frozen_patch.json仍216817字节、SHA256 **6acc1b2d3de238b08780adfb493883abe617aa1c0e1983fdbda9a0bd2fc8405c**，canonical digest **sha256:68557bc28b72fb3f45912e70d585b7c296ec1a7d1ec7a6e9eec57ce82f5f40d8**；旧单entry内容与新exact相同，但physical_attempt_id不同，旧runtime为sha256:43f685f4308354a90d8d88d3a2fd31dcc01bdd41fff3f04210d2668281716e20，新CPU为1d8d…。相同源码内容不允许改绑旧FP；旧raw1及其既有安装／重grade上下文不由本报告改写。

题主候选投影导航 reviews/moto6114_r19_candidate_projection_owner_readback_20261003.json 的4179字节、SHA2560b538f366cab14c272a0c0418dc26da08869c72cfb14a077d8e1295cf0928b2e已定位；本轮实际比对来自原FP、base和patch，结论不依赖作者bool。

## 6. 可信保护、candidate／manager双清理

四臂candidate stage都保留HEAD、历史7454，sanitize删除52个ref、余186，remotes/reflog/unreachable0、验证违规列表空。成功三臂grader sanitize同条件，trusted restore1/apply0、预期与实际test文件1、缺失/irregular空，保护自证EXPECTED_FILES1／PROTECTED_FILES1／PROTECTED_DIRS3／RH2_PROTECT_OK1。exact已完成可信setup，但control_surface保护未完成，不补造保护成功字段。

四臂candidate cleanup均removed=true、steps=[rm:ok]、detail空。每个CLI完整footer manager_created_total1/removed_total1、containers_open/supply_open/cleanup_failures空、open grader空、regrade_total0、halted/abortednull、final exit0。评分失败与资源清理成功是不同事实，不能彼此替代。

noop及gold/wrong_first原residual JSON均有容器、网络实际returncode0且stdout/stderr空。exact因薄矩阵guard终止，未生成同位置residual_exact_qwen.json；不能靠不存在的文件称零残留。为此读取已闭合job的独立只读追加回执 **moto6114-cpu-fb987905af02_finished_absence_readback_v1.json**，1253字节、SHA256 **668e14fb1f96a44602154f79b3b7ef490126fca2ccc82d6abd4f732e517cf90a**。三行run_id逐一等于gold/wrong_first/exact的实际ledger run_id；各自容器和网络共6次查询都实际returncode0、stdout/stderr空。该追加回执在parent1已finished之后取得，无查询失败伪装为空。

它是原71件运输包之外的独立闭合后查询，不声称它属于原transport manifest。其实际字段与原manager关闭、候选删除相互支持，足以核本次自有资源零残留；不用于补评分或扩大成全宿主无任何资源。

## 7. 新R19 UID原公开安装实际结果

moto6114-uid-68f461740f14的6件原件已逐hash核。docker_calls共**13次实际调用，全RC0**：source/actual image inspect、run、生产sanitize、trusted init、activation写入和检查、实际make init、身份导入、两次inspect、rm、双absence。逐次全stdout/stderr均保留；result的public_development_install与第7次实际调用全输出/RC相同。

原安装实际以user54321、HOME=/home/agent、BASH_ENV=/rh2/bash_env，在/testbed执行PYTHONDONTWRITEBYTECODE=1 make init，**不是grader/root安装代证**。stdout21045字节／156行，SHA256 **5de98bdc49917a78ebba9560952fcdbff65ec92d2a4c51449af3d644d0b672c4**；stderr426字节、SHA256 **ed35e0e19a25feaf7ed5c8ae560c1768d041c025c8d733fb28ad3ece924d8f7f**。两轮离线editable Moto构建、安装均实际成功，make init最终RC0；普通site-packages不可写后使用user install。stderr两条moto_server用户bin不在PATH警告不等于安装失败；未额外验证该CLI的PATH可用性。

sanitize实际HEAD正确、历史7454及引用清理同条件，init AGENT_UID54321／RH2_INIT_OK1，activation实际testbed Python/prefix、CONDA_DEFAULT_ENV=testbed、VIRTUAL_ENV空、RH2_ACTIVATION_PROBE_OK1。第8次独立identity JSON与result相同：UID/GID54321、cwd/testbed、HOME/home/agent，解释器/opt/miniconda3/envs/testbed/bin/python，moto从/testbed/moto/__init__.py、RDS从/testbed/moto/rds/models.py，模块完整SHA为a614…250c，boto3/botocore均**1.35.9**。

实际HostConfig为NanoCpus2000000000、Memory4294967296、PidsLimit512、ShmSize67108864、NetworkMode none，实际image为CPU1d8d…；再次inspect核自有job label后rm RC0，最终容器／网络查询RC0且stdout/stderr空。prepared摘要实际绑定本次noop replay_summary，SHA256 **398b17b5565f6ec465576dcc8b6e34bd64a7216bef506ca56252832bba808550**；不是旧R7 prepared替代新ENV。actor_executed=false/model_attempts0保留：这是新宿主开发UID安装验证，没有新CC。

## 8. R19/R7公开开发条件及历史CC复用的限定范围

额外读回 moto6114_r19_public_development_binding_readback_v2.json，13098字节、SHA256 **e4c98caae8c7c016746488042facd6f78a0aa3b7c9d0f8ed0aa497fd8cfb5ffb**。核其四个旧/新prepared prompt/view ref的真实hash和字节；两个public对象逐字段相同，prompt文本逐字节相同、文本SHA256 **00bd0d4b2b8ae3974d0ec8def8814dc83aaf3bf80eb4e9e47c6a52f074ad7f78**，仅prompt.metadata和view的environment_package_digest变化。

进一步对固定R7/R19 producer本题原public和ENV对象直接比对并重算摘要：public全字段不变，ENV仅grading_bundle_digest link不同，旧ENV sha256:a791b087e4475a2a4f7d70183e7031a711e077091206e7826a3203cd32189f41变为新941b…；base、原source、archive、vendor、validation及其余环境字段相同。因此没有将评分链接变化当开发环境变化或相反。

comparison v2列出的17组actor相关source和2组真实DevRunner/acceptance_startup源均逐文件核SHA/bytes和两端字节相同。本轮还直接核生产sandbox_profile、bringup、materialize与R7全文件相同，以及rollout_spec_from_view函数正文相同。只说明这些实际核到的开发路径；不以作者124计数虚称本轮重新审完全部共享源码。新UID真实安装0补充了该比较记录生成时actual_R19_UID_make_init_pending尚未核实的事实，不回写旧comparison文件。

沿用有效的 moto6114_public_actor_reuse_non_author_20261003.md／旧35最终报告的有限历史证据：历史真实CC能执行identity rc0、目标B ARN复现DBClusterNotFoundFault rc1、原公开-k describe_db_cluster为4passed31deselected。历史首请求是Devcheck执行指定tool calls，**不是完整公开题面自主求解**；历史物理derived ID为aaf97…，与新CPU1d8d不同，不是同一镜像对象。

本轮相同public/base/source配方/开发helper加实际新UID安装、激活、模块/SDK事实，支持继续保留这些历史公开功能路径证据的条件适用性，**没有补出fresh R19 CC、完整public prompt实际执行、独立求解或冻结/a2g事实**。旧interpreter_in_tool_result=false仅因RH2_SYS_EXECUTABLE标记未命中，历史命令实际打印PY_CHECK；bashenv_denied_for_agent=false是那三条公开命令没有专门执行／返回RH2_BASHENV_WRITE=DENIED标记。两个false不改true，也不写成CC通道全套访问控制通过。

当前R19四臂计划中exact仍未评分，故即使UID开发安装已独立有效、历史路径边界已说明，也不能拿它们替代缺失控制臂，从而授予新37普通探针最终准入，更不能授予模型／typed-actor／训练资格。

## 9. 最小未完成项

有效三臂、UID安装和所有已有原件可保留；本次唯一评分缺项是exact_qwen。已知基础设施阻断为其原保护阶段300s超时；进一步根因与支持实现有效性尚未在本报告验证。支持交接及后续策略不改变本批原件中的infra/null，也不自动产生新分数。

恢复后只需对该未评分臂的实际适用发布、explicit CPU image、材料/候选、原安装与37项逐参考、正常report、具体两P2P行为及双层清理独立读回，并明确与本批不同的实际策略条件。这里不发起运行、不建议机械重跑有效臂、不自行扩大预算。本报告保持**部分有效结果＋一个基础设施失败**的结论，旧35验收、旧Qwen FP/raw和新37最终资格各自保留其原边界。

