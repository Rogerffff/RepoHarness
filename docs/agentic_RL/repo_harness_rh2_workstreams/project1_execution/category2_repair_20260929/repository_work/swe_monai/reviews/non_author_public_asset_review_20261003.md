# MONAI6975 官方公开资产恢复：非作者窄核

2026-10-03 / Codex，GPT-6.1 Sol / high，非材料与运行脚本作者。本轮仅核公开资产来源、原 actor 缺图触发、COPY-only 配方与准备阶段的退出／清理边界；已经接触 owner 检查与历史私有修订线索，不是新公开读者盲审。

**结论：真实 actor 的缺图触发条件成立，归档资产与官方 base 配置的固定 SHA 一致；当前 COPY-only 配方没有发现阻断准备的具体材料问题。恢复尚未运行，不能据此解除6975开发／探针阻断。** 第一次申请为 busy75，不是恢复实验失败，也不是镜像已部署。还需实际准备结果、新环境版本、原公开命令复验、正式参考矩阵及对应非作者核查；不机械重做未受影响的旧证据。

本人只读本地文本／JSON／哈希，以标准库解析 gzip 与 NIfTI header；没有调用 SSH、Docker、网络、CPU/GPU 作业、项目导入或维护测试，没有改共享文件／总账。仅新增本报告。[旧3715报告](non_author_cpu_review_20261003.md)原件保持不变，SHA256仍为 `e3d0000d81bc147a8a7acf490e821615a5f162470bf3651cd41f8dbf83534913`。

## 1. 核查对象与固定来源

| 对象 | SHA256／结果 |
| --- | --- |
| [准备脚本](../cpu_prepare_6975_public_asset.py) | `47a464d048268bc4e29aa678c274e8add06f5009f649be13ddc8d186c4922371`，与本次launcher工具清单一致 |
| [候选说明](../materials/6975/public_asset_recovery_candidate_v1.json) | `6cc20dfdc0d1f4c1f63c7e69a6e6f126a47cee63d43e631c32e179c5d0bc3c5e`；conditional／未部署／未验收 |
| [归档receipt](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/public_asset_6975_v1/archive_receipt.json) | 1,368字节；`761ff87fe816540aedf9f5d581a27c620927578917f5ce382a446ead85814942`，匹配候选 |
| [公开base data_config](../../../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-6975/base/tests/testing_data/data_config.json) | 7,914字节；`8bbb4ef59ac546183eb7764ca4cd6d0ddb1416fef59a81273ca9235490fda5ad`，匹配receipt／候选 |
| [归档NIfTI](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/public_asset_6975_v1/ref_avg152T1_LR.nii.gz) | 531,671字节；`c01a50caa7a563158ecda43d93a1466bfc8aa939bc16b06452ac1089c54661c8`，匹配配置／receipt／候选／脚本常量 |

base commit 为 `392c5c1b860c0f0cfd0aa14e9d4b342c8b5ef5e7`。所读data_config来自既有固定Git blob导出，其base_identity说明“静态精确Git blobs，不是当前actor树”；本轮独立核实际文件SHA，未重新联网下载或重查整仓Git导出。配置 `images.ref_avg152T1_LR` 指向 `Project-MONAI/MONAI-extra-test-data` 的0.8.1发布文件 `avg152T1_LR_nifti.nii.gz`，hash_type=sha256，hash_val正是上述资产SHA。候选URL与receipt相同，不是私有测试或gold派生图像。

标准库解压可完成，解压后902,981字节。NIfTI header为大端、sizeof_hdr348、维度 `(3,91,109,91,1,1,1,1)`、datatype2／bitpix8、magic `n+1\0`，与receipt一致。本轮未用NiBabel实际载图，不把header核查当作LoadImaged／RandAffined开发通过。

## 2. 原 actor 缺图：触发成立，但开发尚未通过

[原actor attempt](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-723cd019/attempt.json) 作业 `monai-6975-actor-20261003-723cd019`，输入prepared为已核release5的 `monai-release5-prepared-20261003-3537d9d8`，actual image为 `789cb5d10d9b343a2e8b656581697a7127b56a0d467b1cc5b8779a79a0ff0727`。其RepoDigest为固定vendor manifest `0a529471d25c944c76e598474d7a665b20edc2ee95b1a2f30bf9c36fd8db6055`，与script SOURCE及base镜像原件一致。

[owner原actor检查](../checks/monai6975_actor_original_cpu_c_20261003.json)列出的20份原件SHA本人逐份匹配；四条命令与现有公开命令清单逐元素相同，清单SHA为 `c426f4ec0ac56d6a7a2c6951b1bb28bebcf5626ccf695f4463092db79ea16e0f`。真实trajectory为41,184字节、54个事件；四个Bash调用逐ID关联四个结果，五次message_start与stub请求一致，最终success、harness RC0、日志完整、stderr空。

| 公开命令 | 实际结果 | 本次判断 |
| --- | --- | --- |
| identity | RC0；UID54321，工作目录/testbed，解释器与transform.py均从testbed导入，CUDA false | 证明真实非root CPU开发身份；不是root资产探针代替actor |
| public_nifti_original | RC1；`PUBLIC_NIFTI_FILE` 的 path为 `tests/testing_data/ref_avg152T1_LR.nii.gz`、exists=false；随后 `AssertionError: public example NIfTI asset missing` | 缺图确证；assert在LoadImaged／RandAffined及Dataset执行前触发，因此原公开例子**未完成** |
| lazy_value_matrix | RC1，目标 `PUBLIC_DATASET_LAZY_OR_VALUE_FAILED` 断言 | base的Dataset对lazy=True／None仍按False执行，六场景像素都正确但两场景lazy policy错误；这是原功能缺陷，不是NIfTI依赖错误，COPY不修它 |
| public_regression | RC0；56 PASSED，20 warnings | 原公开模块使用测试自建临时NIfTI，不能据此核销题面固定路径缺图 |

直接 [缺图capture](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-723cd019/captures/public_nifti_original.out) SHA为 `6bae92dc56b06021fcb0988e70a6acd86a85c46c8765c650468ac9f025a7dde6`。551字节完整输出低于采集截断限额，缺图marker也出现在真实tool_result中，不只是owner摘要。base镜像root identity同时记nifti_exists=false，可复用为补充而非actor主证据。

[actor外层完成snapshot](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-actor-20261003-723cd019.snapshot-39003244.json)是finished／returncode0／launcher exit0；内部两条命令RC1仍保留，`all_match_expect=false`、`public_development_complete=false`。因此检查单没有把外层RC0冒称开发验收，所述缺图阻断成立。原actor已正常收尾：agent进程0，harness／launcher marker不存在，候选容器rm与stub RC0，无relay／network失败，按attempt标签再查无容器／网络残留。两个通用marker false仍只是清单未触发对应探针，不能扩大为平台保护验收。

## 3. COPY-only 配方范围与当前可验证性

脚本先核资产SHA、base task／SOURCE／HEAD／cleanup，再核actor使用同一actual image、harness正常结束、容器与stub清理，以及该真实capture的精确路径／exists=false／缺图AssertionError。当前所绑定原件已独立满足这些条件，因此没有用静态导出或归档成功替代“actor真的缺图”的授权触发。

固定source是原vendor image的manifest引用，不是mutable tag。运行前inspect须与base实际ID及RepoDigests匹配。生成Dockerfile只有：

```dockerfile
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
COPY ref_avg152T1_LR.nii.gz /testbed/tests/testing_data/ref_avg152T1_LR.nii.gz
```

没有RUN、pip／conda安装、源码补丁、测试补丁、题面写入或全局入口修改。build参数 `--pull=false --network=none`，新tag按唯一job命名，不覆盖原vendor tag。原source实际Config.OnBuild为null，未隐藏额外FROM触发步骤。脚本要求原镜像层完全为派生镜像的前缀、仅多一层；完成后还要核指定关键源码／测试／依赖声明文件的SHA与原identity相同，HEAD和porcelain不变。上述检查的**运行结果尚不存在**，本轮只接受静态配方范围。

需要精确表述“保持原源码／测试／依赖”：原镜像初态已有 `requirements-dev.txt` 删除MetricsReloaded行，actor也实际看到该唯一Git改动；COPY保留该镜像状态，**不把它恢复为pristine Git base**。13份关键文件SHA检查不是整文件系统逐项diff，但固定无RUN配方、源层前缀及唯一COPY目标可支撑本次窄操作的范围。没有恢复后的layer／config／实际文件结果前，不宣称这些条件已验证。COPY图像字节与原vendor安装流程均独立于私有测试内容，之后仍需单独绑定新环境材料版本，不能直接把旧环境digest配到新镜像。

宿主写入限于本包outputs的新目录与其build／日志文件，输入asset先resolve并限制在包内，output限制在本包outputs内；out已存在会拒绝，job名有字符限制。Docker写入是新image／cache及带本job标签的临时身份容器；派生image作为产物保留，不属于“所有Docker对象已删除”。脚本不写共享源码／registry／CPU总账。

## 4. 限额、异常、清理与未执行状态

准备探针将使用非root54321:54321、Python `-I -B`、PYTHONDONTWRITEBYTECODE、network none、2CPU／4GiB／PID512；脚本还会从实际inspect核User、Image及HostConfig四项。其功能仅NiBabel读图／SHA／HEAD／关键文件身份，没有对LoadImaged或Dataset做执行；准备receipt仍明确 `actor_verified=false`、`new_test_executed=false`、`formal_acceptance_passed=false`。

Dockerbuild期限1800s，身份启动期限600s，普通子命令120s；子进程独立进程组，正常失败／超时／信号会尝试TERM、30s后KILL，并进入finally清理。COPY没有执行源镜像代码的RUN；**build daemon工作本身没有脚本层2CPU／4GiB上限**，不能把之后身份容器限额说成整个build的实际限额。当前由共享prepare队列控制构建并发，不能外推宿主容量或真实资源峰值。

清理边界必须合看而不能只信status：脚本先写 `image_prepared_not_task_accepted`，finally才rm／query和保存cleanup；若清理RC非零／有残留，末尾assert使外层非零，但receipt的status可能仍是prepared。若cleanup subprocess自身timeout／抛异常，后续query和最终记录可能缺席。**未来验收须要求外层RC0、完整cleanup字段、rm_rc=0、query_rc=0、remaining空及原始日志齐全；单凭status不能认定准备已成功。** 这是一项现有失败分支归档限制，不是本轮已发生的清理事故。题主说明接续actor入口同时要求launcher exit RC0、prepared状态、remaining空，镜像验收另核rm_rc／query_rc均0；本轮未把这项说明冒称独立客户端代码全审，不只按status放行，也不热改已冻结未执行脚本。若实际清理失败／超时，保留失败原件、停止在诊断状态，再版本化修复；不把未知记成零残留。

已读 [第一次prepare申请snapshot](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-public-asset-image-20261003-295281d0.snapshot-90079bd4.json)：status／prep均null，exit.rc=75，launcher_log为 `Image preparation busy; retry later`，SHA `e15119a97f941a6a0f20f76917c90ac0e670265df0b56c31660c5dc8d646a0c6`。这证明申请未获准备名额，**尚未运行恢复**；launcher创建或归档download完成都不能计作image prepared、actor开发通过或GPU准入。

## 5. 下一步与停止条件

本次无需回头机械重做3715或6975未受影响的旧静态证据。没有新增必须用户决定的题面目标，也没有发现官方图像来源／COPY路径的静态阻断。

6975当前真正的放行阻断是：原公开例子因实际缺图未完成；派生准备、环境身份登记和恢复后的真实actor验证均未完成。后续只补相关路径：拿到实际派生输出并核唯一COPY层／新ID／原源码与依赖初态、非root资产可读／SHA及清理／外层退出；用新环境跑原LoadImaged／RandAffined直调与Dataset例子，之后核本题新材料正式64参考的0／1／0矩阵和非作者结果。单靠COPY身份probe或旧56公开测试通过不能顶替这些缺口。

本报告接受的是“缺图触发与离线配方可进入准备”，不是“6975已开发验收／可进探针”。未运行恢复前，候选、archive receipt的未部署措辞应保留；未来实际完成后按新证据记录，不回写旧actor失败或把归档receipt的旧scope静默改成已验证。
