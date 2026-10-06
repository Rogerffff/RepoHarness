# 8801 原 FP CPU 构造增量独立审查（2026-10-03）

结论：**当前 `snapshot_v1`、作者构造器及唯一8801 launcher未发现静态派发阻断，可按既有授权经统一CPU槽做仅setup900的窄恢复。** 作者纯构造rc0；正式运行、45参考结果和本题独立语义裁决仍待验，原`infra_failure/reward=None`保留。本报告不产生新分数，也不授训练资格。

本次由非作者subagent承接已验7138/7305/9378执行base，仅读本地原件并用stdlib复算SHA/size和集合。未SSH、Docker、CPU/GPU/模型、项目或候选执行，不重审29/59矩阵或420控制语义，不修改原候选、共享源码与历史证据；不是fresh全题盲审。[授权decision](../../../../../../../../runs/category2_repair_20260929/overnight_watch_20261003/user_infra_completion_check_20261003/dask8801_recovery_decision.json)只准原FP setup300→900、whole3600保持及既有CPU槽，明确reward不能单独关闭该题。

## 固定输入与构造

本地完整核验1581 snapshot成员/172,232,443B、原GPU闭合528成员/52,779,768B及code8原inventory1045源码成员，全为regular且SHA/size相等；原code8 inventory与此前固定CPU/global inventory字节一致。[builder L21–34](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/prepare_snapshot_v1.py#L21)也按原GPU闭合逐成员核，复制执行base及helpers不改字节。

[worker L39–75](../tools/cpu_dask8801_original_fp_setup900_v1.py#L39)核原timeout/FP/baseline/cleanup和四份实际原config SHA；tasks=`config_v31/tasks.json`，gateway=`config_v31/gateway_coder.json`，summary为原8801 prepared bundle，adapter为原`services_v14`。四SHA均与原input_check匹配。[L76–90](../tools/cpu_dask8801_original_fp_setup900_v1.py#L76)只改setup300→900，回滚比较后再投射summary prepared/private与task prepared_summary运输路径；因此“只改setup”指执行语义，路径投射另有明确边界。

15个固定input身份字段、原materials/public/scripts及45参考由[L100–127](../tools/cpu_dask8801_original_fp_setup900_v1.py#L100)核。原45分区为2 F2P、41原P2P、2新增P2P；revision及references逐原record相等，命令仍为`pytest -n0 -rA  --color=no dask/tests/test_config.py`。**这些是固定参考范围，不是已测45通过。** 原FP canonical `sha256:739f20878faca8da44f55b164596413fe411b9a1054e4d9c227212bc0dabd7a1`、baseline `sha256:aff22965ee08670e719a8ae2c026cf1f78ef93e201356921845b61ada0262aea`及single-shell scripts `sha256:835811ced3255278f9fd36b35e68ae6deee2791ed710367d832e4d9954af67e5`保持；FP raw JSON文件SHA另列，不能混作canonical摘要。

此次未加7305五env caps，尤其未添加`DASK_NUM_WORKERS`。2CPU/4GiB/pids512、candidate UID54322、whole3600/apply120/test1800都保持。没有重求解或修候选。

## 原来源镜像和执行base

8801保持manifest绑定的来源镜像`xingyaoww/sweb.eval.x86_64.dask_s_dask-8801:latest`及RepoDigest `sha256:21e77aea7025bad694a5c600ed6d4b372c80c83bc319fafa2fedb23d9ff48483`，actual ID为`sha256:695d2cc28e303a0224c1109fe245f7296c6290d480124fa4fd4cc2ad072124b1`；它没有改用7138的local-build派生模式。[worker L104–105](../tools/cpu_dask8801_original_fp_setup900_v1.py#L104)明确要求非local build、原source tag与manifest digest。[固定manager L2027](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/snapshot_v1/source/frozen_code_v8/rh2/src/repoharness2/grading/manager.py#L2027)调用L2858–2895，从实际运行容器image查RepoDigests再核原digest，避免仅相信`:latest`标签。

[CPU只读预检L13–20](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/preflight_cpu_image.py#L13)在成功返回前核不可变`@21e77…`source_ref映射到695d ID；回执保存CPU五字段表示，**未包含完整RepoDigests清单**，正式运行仍须核实际container/source digest。[builder L40–46](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/prepare_snapshot_v1.py#L40)的CPU完整17键Config另冻结；GPU仅有完整Config canonical摘要，CPU四键`Env/Cmd/WorkingDir/Labels`canonical摘要与其相等 `0e9fdcf3e818150127174b708f22cf1ab585019f895bc5b46e8b823e2c2744c2`，RootFS摘要相等 `c30806d1c3d01d8a1064197c4d397e4e45187028b732bb6ba598feda478bd930`，Id/amd64/linux一致。本审查独立复算这两摘要，不把CPU17键raw称作GPU完整raw。

base逐字SHA仍为`3086fb2e63fdd6c984baf717c1525ce2bdf7f8693ca9954d8cc815cb817f4312`，[main L159–168](../tools/cpu_dask8801_original_fp_setup900_v1.py#L159)拒绝旧out并调用原`execute_with_signals`。base L111–138强制实际slot admission、supply=None及CPU full Config严格相等；L181–184核actual container ID/profile；L237–309保留原账目、资源、清理和末次snapshot核验。此次只验字节复用与8801输入消费，不重审这些已有收口或控制矩阵。存在after-install脚本不推定two-stage。

## 纯构造与唯一派发

[作者pure回执L4–10](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/deploy_and_pure_receipt_v1.json#L4)为1581成员核验、rc0、stderr空、0候选/0模型；71个实际加载模块路径/SHA均在固定code8且逐项匹配。L416只表示identity构造完成，不证明恢复或评分成功。

[launcher L9–28](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/launch_cpu_recovery_v1.py#L9)以前述pure为前置，只生成8801一个配置。[L32–49](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/launch_cpu_recovery_v1.py#L32)核固定slot wrapper/full snapshot，要求全新serial/job目录；完整worker foreground经统一CPU槽持有，只有外层queue持久化。固定wait helper仅busy75退让，最多15次、间隔120秒；非75立即停，serial stop_on_nonzero=true，不自动重跑grader。实际admission尚未发生。

构造阶段另有一次receipt命名漏改：builder写v3而deploy预读v1，**在SSH/上传前的本地读取阶段失败，零CPU/模型启动**。[纠正回执](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask8801_same_fp_cpu_c_v1/local_predeployment_receipt_name_correction_v1.json)保留原v3及builder，另首次写同字节v1 receipt；本审查核两receipt SHA相等，snapshot与archive字节未变。这个准备错误不归作模型失败。

## 后续最小验收与边界

owner需读回真实slot admission/terminal、actual UID54322、原695d image与21e77 RepoDigest/CPU完整Config、断网及固定资源profile、原baseline rebuild/FP/projection/materials、单shell原scripts与完整45参考逐项结果。无infra/parse/partial/missing/skipped/unaccounted；真实success/failure如实记，不能用模块总数代45参考。资源需pids.events max0、oom/oom_kill0及OOMKilled=false，并保留内存限额事件和runner变化等真实限制。清理需own容器0、created=removed=1、open/failures空及结束1581源SHA不变；失败留新证据，不自动重跑grader。

候选与原执行closure由另一独立审查承担；实际CPU封包后再按既有本题行为+独立diagnostic协议fresh裁决。本构造通过、未来raw reward或历史420控制都不能替该语义裁决。当前仍单个原Coder样本，另一模型缺项；不授训练资格，不扩大为wholehost释放。

A/D/F/G/H/L/M/N证据见上述路径；B/C/I保留单样本、既有挡板与分期后验；E明确pure不替45结果；J/K只核短适配复用，不扩范围。完整逐维说明和原四config、helpers/FP等SHA见同名JSON。

| 本次固定证据 | SHA256 |
| --- | --- |
| worker | `afb419eb2dfe5b8955fd3d3beb8cbf4b1ac9e91c85bee281ecba7267e82f2c1a` |
| snapshot_v1 manifest | `08acd2a983ab8ee4ff720258d7a8b87e68b153b32b81b4bfa9ea5528d73b948d` |
| archive（48,326,421B） | `460878ba590de079bd50bec0407dc1ca70bcb875dd12e6a476e09035c5129412` |
| inputs_8801 | `30f8be68940ee9b3d1884f59ab8f88a9ed9179228e580fbbfbf83eef2927f836` |
| 唯一8801 launcher | `4e0bbff37516ae332cfc4120a761a01ddf12908f91750399c180902579f16e76` |
| pure回执 | `2454c160cffd6aa2422a072a2b1cff6b1166dfdbcadf6228434f8db7c3047678` |
| 原528闭合manifest | `eba8b49c23fb6ff22fea8ed2cbd2cbf87ab1bf851bbac09844fb790e781dc021` |
| CPU image readback | `c21c234db03b610c7688d035012fd3f12e9bec6101ca1b2f9fbf031fac4704e4` |

报告首次写入H/reviews，所有原件及旧审查保留。
