# 7138 原 FP CPU 构造增量独立审查（2026-10-03）

结论：**最终 `snapshot_v3` 与唯一7138派发入口未发现静态阻断，可按已有授权经统一CPU槽进行有界窄恢复。正式评分、资源和清理验收仍待执行；纯构造通过不证明补分成功。** 本报告不授训练资格，也不产生新模型分数。

本次由非作者subagent承接此前CPU执行base审查，仅核7138新增构造、固定输入与派发接缝。它不是fresh全题盲审、小阶段集成验收或59矩阵重审。本审查只读本地证据并用stdlib复算SHA/size；没有SSH、Docker、项目或候选导入/执行、CPU/GPU评分、模型调用，也未改共享源码及历史报告。

## 已核的输入和变更

- 本地全量核验1563个snapshot固定成员（157,221,954B）、原GPU闭合508成员（37,710,899B）及code8原inventory的1045源码成员，均regular且SHA/size匹配。code8 inventory文件本身另计；未把1046个prefix文件误称1046源码。71个纯构造实际加载模块也逐项核对固定code8路径和SHA。
- [作者构造器L39–75](../tools/cpu_dask7138_original_fp_setup900_v1.py#L39)先核原508文件、旧`infra_failure/reward=None`、清理及FP/baseline，再以原`input_check.input_sha256`精确核tasks、summary、gateway、adapter四份配置。v3网关为`config_v26/gateway_coder.json`，其SHA实际匹配原绑定；这不是包中任意同名服务副本。
- [L76–90](../tools/cpu_dask7138_original_fp_setup900_v1.py#L76)只把grader setup 300改900，回滚比较确保预算以外原task配置未变；随后投射summary的prepared/private路径和task的prepared_summary至已固定运输副本及新out。15个固定input身份、原470 refs及完整单shell scripts另由[L100–127](../tools/cpu_dask7138_original_fp_setup900_v1.py#L100)核验。因此“只改setup”指执行语义，运输绝对路径也有明确投射，不能声称最终JSON只有一个字节字段改变。
- 原470参考为`original_f2p=1 / original_p2p=468 / added_p2p=1`，reference列表和grading_revision与原input逐字相等；固定命令仍为`pytest -n0 -rA  --color=no dask/array/tests/test_routines.py`。它们是评分参考范围，**不是本次已观测470通过**。
- 2CPU、4GiB、pids512、candidate UID54322、完整scripts digest、FP/public/materials均保留。本题未额外加7305的DASK/BLAS五env caps。原FP canonical为`sha256:451557c761f6f47f984e06695b51f66591f7ecaa8589c1188c1a5e7c6a5365e4`；原single-shell digest为`sha256:6f61a742aacc681b4e07e2b1825cd1d8cba5450da1791e2aae7b9eee659c0d5b`。FrozenPatch JSON文件raw SHA与canonical FP digest不同，不能混用。

## 镜像和运行路径

实际grader image仍为`sha256:625b404c6c1c40da31df4edfea6052a10fbd30b7fb49d58072b6ee2b215fab13`。CPU独立readback的完整17键Config表示被固定；原GPU材料只有完整Config的canonical摘要，并无完整raw Config。[GPU摘要grader段L44–49](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/snapshot_v3/source/closed/q26_binder_image_readback_merge_v1/actual_image_readback.json#L44)的Config摘要`0e9fdcf3e818150127174b708f22cf1ab585019f895bc5b46e8b823e2c2744c2`与CPU `Env/Cmd/WorkingDir/Labels`四键canonical摘要相同；Id/amd64/linux及完整RootFS摘要`4800b186f23ea6a55a2beedc7110285599f455fb3d665d78ac22c0824797d439`也相同。本审查独立复算这两个canonical SHA，但不把CPU17键称作原GPU完整raw。执行base会对actual CPU inspect与固定CPU完整Config严格相等核验，[base L135–138](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/snapshot_v3/validated_execution_base.py#L135)没有丢字段或默认值归一化。

adapter [L159–168](../tools/cpu_dask7138_original_fp_setup900_v1.py#L159)拒绝旧out并将base逐字锁到`3086fb2e63fdd6c984baf717c1525ce2bdf7f8693ca9954d8cc815cb817f4312`，调用原`execute_with_signals`。base的manager `supply=None`且`_supply_applies=False`，[L129–138](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/snapshot_v3/validated_execution_base.py#L129)确认为single-shell；存在after-install脚本不代表two-stage。此次不重新审查此前已验base的全部异常收口或矩阵，只复核其字节、消费输入和7138不进入7305专属caps分支。

[launcher L9–28](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/launch_cpu_recovery_v1.py#L9)先读v3 pure成功且0候选/0模型，只生成7138一个配置。远端[L32–49](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/launch_cpu_recovery_v1.py#L32)核统一slot wrapper与全snapshot SHA，要求新serial/job目录，全部foreground worker命令由统一CPU槽持有；只有外层queue持久化。固定wait helper [L41–68](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/snapshot_v3/cpu_wait_for_slot.py#L41)仅在slot返回75时退让，最多15次、间隔120秒，其他returncode立即停；serial启用stop_on_nonzero。本次不自动重跑grader。实际child/父PID、run/package和完整command仍由[base L111–124](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/snapshot_v3/validated_execution_base.py#L111)在评分前核；本报告未见实际派发。

## 已纠正与仍待验

v1的`profile.network_mode`不存在属性访问在作者静态准备时被纠正；v1未用于评分。v2选错gateway，作者纯构造rc1且0候选/0模型，失败回执保留。最终[v3回执L4–10](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/deploy_and_pure_receipt_v3.json#L4)为rc0、stderr空、1563成员核验、0候选/0模型；L416的pure_check仅表示identity构造成功。旧错误不会被归为模型失败，也不把旧v2列作可派发版本。

owner后续最小验收仍须：实际统一slot admission、CPU完整image/资源/UID/断网核验、原baseline rebuild、原FP同模块和470参考逐项完成、无infra/parse/partial/missing/skipped/unaccounted、pids.events max0及oom/oom_kill均0、原base cleanup闭合和own容器0、结束snapshot全部SHA不变。参考可有真实success或failure；环境恢复不要求模型全部通过。[base L237–309](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/snapshot_v3/validated_execution_base.py#L237)将完整账目与候选语义成绩分开，失败保留新证据、不可自动补跑。

原结果仍是setup300阶段`infra_failure/reward=None`，install/test未开始。原候选diff [L71–74](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask7138_same_fp_cpu_c_v1/snapshot_v3/source/closed/queue_v26/results/gpu1003-dask7138-coder-a1/attempt/candidate/dask__dask-7138.diff#L71)保留`ravel(array)`改为`ravel(array_like)`；本次不替模型修这个改名，也不宣布正式候选语义通过。当前仍仅一个原Coder样本，另一模型缺项；正式重评分未完成，不授训练资格。

适用维度A/D/F/G/H/L/M/N以上有证据；B/C/I保留单样本、fail-closed和owner后验；E明确pure不替正式测试；J/K仅评价短适配复用base，不扩成新恢复协议。完整逐维说明与精确证据SHA见同名JSON。

## 固定证据SHA

| 证据 | SHA256 |
| --- | --- |
| 作者worker | `bfe59992559f9108869cb763b2a6a8f7dc547cb01533d0b1227fcb042e262219` |
| v3 snapshot manifest | `833d863329e908ffddb287edd1d80e4b3e0f9995122e13cf492955a662115118` |
| v3 archive（40,446,870B） | `b4e988fa0eb654a7acd8ed567bff84a9402a95fe8ba057e90eff20d0031133e9` |
| inputs_7138 | `2a8b2a9a39a43a2cd907d08d916dcec19eb0043e8958e5c6a8bdc89933ffde97` |
| 执行base | `3086fb2e63fdd6c984baf717c1525ce2bdf7f8693ca9954d8cc815cb817f4312` |
| 唯一7138 launcher | `e7110232e3c7c2f892dfe527c793238d0628f41d66d94d673cc26783183b2c20` |
| v3 pure回执 | `df66e16b3c999fd4583f981d16e46d3f32fedf016fb9f7dc8cb9bc2ea3dcc2c7` |
| 原GPU闭合manifest | `8df01ab39be672264d938cccd1679121d20dda8a6be3f1af822b59db004d05ab` |
| CPU image readback | `28ef712b76736c2f8d7b531c4acd2f2077a7a0332ff466b69e3c3e11ed66c23a` |

四原配置SHA、固定helpers、原FP raw JSON、candidate diff、v2失败回执及其余证据SHA列于同名JSON。所有原件保留，本报告首次写入，不回写旧审查。
