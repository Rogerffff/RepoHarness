# MONAI6975 COPY 恢复与公开 actor：非作者运行核查

2026-10-03 / Codex，GPT-6.1 Sol / high，非材料／准备脚本作者。接续已有[资产来源窄核](non_author_public_asset_review_20261003.md)和[v2增量静态核查](non_author_public_asset_v2_review_20261003.md)，已经接触原actor缺图、v1准备失败和私有修订线索，**不是fresh公开读者／独立重新运行实验**。

**结论：限定范围的实际COPY恢复与真实公开CPU开发复验成立，旧缺图和v1准备Git探针问题在此版本已关闭；未发现该恢复切片的新具体阻断。** 原lazy缺陷仍保留并被预期命令复现。新64参考正式评分尚未执行，consumer发布待回执，**6975整题CPU验收／GPU派发尚未放行**。本报告没有重审不变私有测试或3715，不授予训练或留出资格。

本人只读本地完整原件，以标准库核SHA、JSON、逐tool关联和结果语义；没有SSH、Docker、CPU/GPU运行、网络下载、项目测试或共同代码／总账修改。只新增本报告，三个旧报告原件未改，SHA仍分别为 `9c4f60693ace670ef80406e72b2dea4e98a16b51e7cd4e21185342d65a9c3ea9`、`c5660c49fd7c55180e6ec7c6dd313c9f892bbd798ff4ebf0e556c022103c48d7`、`e3d0000d81bc147a8a7acf490e821615a5f162470bf3651cd41f8dbf83534913`。

## 1. 本次适用身份与原件

| 对象 | 作业／摘要 |
| --- | --- |
| 实际COPY准备 | `monai-6975-public-asset-image-v2-20261003-526bfdc3`；[完整receipt](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-public-asset-image-v2-20261003-526bfdc3/preparation.json) SHA `607bbfe396e72d5e11e633240f05ff11b5fa00c7a140f5ff631ab8d82918b534` |
| 新真实CC桩actor | `monai-6975-actor-20261003-b7c29487`；[完整attempt](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-b7c29487/attempt.json) SHA `74fb0e995dd82a9392c462e9c7dd34ac4c9a6c6d63d30fd0af788488f3b682d7` |
| 准备脚本 | v2 SHA `b7084603b80986049bedd35ed5173f9e4c242409e6b351d3eb81afaea9701955`，与receipt／launcher工具清单一致 |
| 原镜像 | actual ID `789cb5d10d9b343a2e8b656581697a7127b56a0d467b1cc5b8779a79a0ff0727`；固定vendor manifest `0a529471d25c944c76e598474d7a665b20edc2ee95b1a2f30bf9c36fd8db6055` |
| 新派生镜像 | actual ID `fbfdddc4edda1f0ea4c1b76a572bd95045be4bbd202b197a94e8d8ee14a73fd6`；新唯一job tag，未覆盖vendor tag |
| base／公开资产 | commit `392c5c1b860c0f0cfd0aa14e9d4b342c8b5ef5e7`；官方NIfTI SHA `c01a50caa7a563158ecda43d93a1466bfc8aa939bc16b06452ac1089c54661c8`，来源／配置按旧已核材料复用 |

准备receipt仍绑定原缺图actor `723cd019`和原base镜像job `f121f560`，两份原receipt SHA与其当前字节匹配。新actor沿release5 manifest `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`、既有prepared `3537d9d8`运行，用explicit image override取上述新派生ID；这证明本次诊断条件，**不证明新的正式环境consumer身份已经发布**。

## 2. COPY实际范围、root Git与非root检查

准备七步均RC0，其每份完整日志SHA与receipt逐项一致。固定SOURCE实际inspect的ID／RepoDigests命中原base；[build.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-public-asset-image-v2-20261003-526bfdc3/build.log)只有FROM和一次指定COPY，没有RUN／依赖安装／源码补丁。Dockerfile SHA `838aa459f1718541af80c9115002624e983049accda669f216fcda8baa81d5cd`仍是原已核配方；构建RC0，未使用mutable pull。

独立读base／derived inspect：原13层逐项为新14层的前缀，仅新增1层。Config的运行字段（Env／Cmd／Entrypoint／WorkingDir／User等）不变；实际差异是新增本包／job Labels，及Docker构建生成的`Config.Image`元数据由旧值变空。**严格字面“整个Config仅差标签”不成立，但没有运行配置语义改变。** 原镜像无OnBuild触发，构建记录与唯一公开资产COPY相符。没有逐层tar逐文件清单，本轮不声称多做了该验证。

[root Git日志](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-public-asset-image-v2-20261003-526bfdc3/repository_git_identity.log) SHA `c29467272d37d9270e5fbd59ec7de520cd77a8300073d821913ce1ed4095245d`：UID0，HEAD固定base，porcelain为原镜像已有的 ` M requirements-dev.txt`，没有v1 dubious ownership异常。该root探针仅核Git身份，不替代非root资产读图或actor能力。

[非root日志](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-public-asset-image-v2-20261003-526bfdc3/source_identity.log) SHA `b867348a560b1fe044f00ff84f173bcebcdaf163dd5f6ea91da35e2d12e5b653`：UID54321，实际解释器testbed，文件可读、SHA为官方固定值，NiBabel实际载图shape `[91,109,91]`；13份关键源码、测试、依赖声明／setup文件SHA逐字段等于原base identity。原requirements-dev中MetricsReloaded行删除状态也由porcelain保留，不能称为恢复pristine Git base。

准备非root容器的实际inspect命中新派生ID、User54321:54321、2CPU／4GiB／PID512／network none；root Git命令也带相同限额、network none和唯一`-git`名称／同job标签，但root容器已`--rm`，没有单独归档其HostConfig。构建daemon本身没有脚本层CPU／内存上限，不能借身份容器限额声称整个build峰值受相同上限证明。

两类容器清理通过同job标签覆盖：cleanup_before列一个已停止非root容器ID（与create_identity对应），root正常`--rm`后不在列表；实际rm RC0，再查RC0／输出空。receipt仅在cleanup成功后为 `image_prepared_not_task_accepted`，没有cleanup_error／未知状态。派生image和cache作为产物保留，不算残留执行容器。外层 [prepare snapshot](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-public-asset-image-v2-20261003-526bfdc3.snapshot-1cd7fbda.json)为finished／cpu_slot returncode0／launcher exit0，launch与snapshot命令逐元素一致。准备本身仍保留actor_verified／new_test_executed／formal_acceptance_passed=false，真实actor证据在下一节单列，不回填此旧receipt。

## 3. 新actor四条公开命令的实际结果

四条命令逐元素与原缺图actor／原公开清单相同，清单SHA仍 `c426f4ec0ac56d6a7a2c6951b1bb28bebcf5626ccf695f4463092db79ea16e0f`。actual image、prelaunch image及attempt image一致；HEAD／初态porcelain与原actor一致。四份完整capture的字节与attempt记数一致，最大9,559字节，均低于200,000字节限额；tool_result尾部截断不影响独立完整capture核查。

| 命令 | RC／完整capture SHA | 实际结论 |
| --- | --- | --- |
| [identity](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-b7c29487/captures/identity.out) | 0；`c568c246e6130ba82d887c0d650c320ff368bd9eb33e1f63cb65d3e3a34966eb` | UID54321／testbed Python和MONAI／transform.py，CUDA false，原初态改动保留；与原identity capture逐字相同 |
| [public_nifti_original](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-b7c29487/captures/public_nifti_original.out) | 0；`2e36325ac1ee3a3b09e9accc41e7bca14eb97ff4bbcd1c5510bb816f088415b8` | 固定路径exists=true、SHA为官方值；原LoadImaged／RandAffined直调和Dataset都实际执行，输出shape `[91,109,91]`／float32／cpu／finite=true |
| [lazy_value_matrix](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-b7c29487/captures/lazy_value_matrix.out) | 1；`a06752900602d6e1e902422eae164934d0b433a833c7436da1bc2da8a01d9e85` | 原lazy目标缺陷仍在，明确目标AssertionError，不是任意非零 |
| [public_regression](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-b7c29487/captures/public_regression.out) | 0；`20956bce1e4c968bd5d944b5fb91e83d33bccfd9e2b66736240bb707c65f51cc` | test_compose／test_dataset原公开56节点逐键PASSED，无FAILED／ERROR／SKIPPED；20 warnings |

NIfTI原例现在达到两个 `PUBLIC_NIFTI_RESULT`，直接日志是lazy=True、RandAffined pending操作实际应用；Dataset日志仍lazy=False，正是原公开目标bug的可达表现。随机RandAffine两次输出不作像素互等测试，本轮只核可执行、CPU形状／有限值，没有把随机一致性或功能已修作为目标。

确定性lazy矩阵六行JSON逐项核过：所有返回像素均等于双轴flip期望；direct True／False／None和Dataset False的有效lazy policy正确，Dataset True／None却传effective=false，两行policy_ok=false，最终精确 `AssertionError: PUBLIC_DATASET_LAZY_OR_VALUE_FAILED`。记录的真实resample调用数分别为1／0／0／0／1／0，本轮不把唯一调用次数当正确性oracle。RC1符合base预期，**all_match_expect=true不等于原lazy bug已修**；COPY没有掩盖该缺陷，也没有为通过开发命令把expect从失败改成成功。

缺图环境问题因此已在同一原例复验关闭；旧56公开测试仍不是新64私有参考。恢复后的来源／公开命令与基础开发可执行性成立，与正式修订材料资格分开。

## 4. actor实际资源、完整桩链和收尾

[prelaunch原件](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-b7c29487/prelaunch.json) SHA `ee1442c0b5414a50c45eb144118e61e6d6b94b3aafca49ebc3def1b1b23e84d9` 与actual image一致；inspect_facts包含2CPU／4GiB、MemorySwap4GiB、PID512、home tmpfs256MiB、tmp tmpfs1GiB、无bind／mount、init true、非privileged。actor容器Config.User为空是可信启动容器配置，实际探针及identity的执行UID54321；不据Config.User推定solver为root。

cgroup v2原始probe是CPU_MAX `200000 100000`、MEMORY_MAX4294967296、SWAP_MAX0、PIDS_MAX512，与HostConfig匹配；实际agent有效／允许capability均0、NNP1、workdir owner54321且可写。记录的路由／relay与禁止目标探针符合本次prelaunch判据，但这不是平台安全全验收。StorageOpt为空，effective profile中8GiB writable layer quota没有独立实际强制证据；真实峰值／余量不由本包证明。

[activation_check](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-b7c29487/activation_check.json) SHA `f4f614f01fbcc236eee8cae066452ce968b81b2f0ef7ab5c3fce9986e9b7b994` 明确testbed解释器／prefix／conda环境。generic检查 `interpreter_in_tool_result=false`、`bashenv_denied_for_agent=false`仍保留：本清单采用IDENTITY而非固定RH2_SYS_EXECUTABLE标记，并未执行BASHENV写入命令。prelaunch实际ACTIVATION_WRITE=DENIED是另一条有范围的证据，不能把generic false改成true或扩大安全核销。

完整[harness trajectory](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-b7c29487/harness/trajectory.jsonl)为43,158字节、54个合法JSON事件（system14／stream_event30／assistant5／user4／result1），SHA `8d8ae8c1d8eddb78ffa3b5aae441a7debd979973f3979a1735722c37be53b1e1`。四个Bash调用与结果逐tool ID一致，五次message_start与五份stub请求对应，最终success／is_error=false／num_turns5／terminal_reason=completed；harness exit0、exec exited、log_complete=true、stderr零字节，与attempt日志长度一致。CC实际版本2.1.205，包摘要／冻结bounded image shim沿旧有效证据。

[首个真实请求](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-b7c29487/stub/requests/messages_000.json) SHA `54d4ecfd18dfd2ead09e6cf87e1becad340de62683a33df6d3b2b6d125bcb82b` 的用户消息仍是 `Devcheck run: execute exactly the tool calls you are given, then stop.`，**不是原题面／public_hints正式交付证据，也不是模型求解**。后续GPU执行必须核实际首请求公开内容；本轮没有新增题面或公共输入。

post_run记录agent进程0、harness／launcher marker不存在、Git改动1行保持旧初态，新文件494项为开发运行缓存等记录，不宣称零写入。actor container rm／stub RC0，network／relay失败空，按attempt标签容器／网络查询及复查残留空。外层 [actor snapshot](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-b7c29487.snapshot-8f595a2b.json)为finished／returncode0／launcher exit0，实际command与launch相同，完成时间在内部正常收尾之后。没有强杀或不完整日志被冒称完成。

## 5. 当前用途与未完成项

本次恢复运行切片不存在需要先修改COPY材料或重做有效旧证据的具体阻断；v1准备失败原件和两个旧资产报告仍保留，不静默改写历史。

当前只确认：新派生ID下公开资产恢复、关键来源保持、真实actor环境和原公开开发路径可达、原lazy缺陷仍可复现、正常收尾成立。6975整题仍缺**新环境consumer发布回执与其身份绑定、正式新64参考完整矩阵及非作者结果核查**。待这些实际完成再按题级条件判断是否可提交探索性GPU探针；本文不提前放行CPU全验收／GPU派发，不声称有训练信号或平台可信性全完成。
