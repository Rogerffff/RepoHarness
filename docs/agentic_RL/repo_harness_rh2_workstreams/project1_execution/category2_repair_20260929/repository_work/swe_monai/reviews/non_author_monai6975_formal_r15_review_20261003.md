# MONAI6975 R15 正式 CPU：非作者完整原件验收

日期：2026-10-03。审查者：GPT-6.1 Sol / high，非材料、准备脚本或候选作者。

## 结论与范围

**固定 R15 的 MONAI6975 正式三行 CPU 验收成立，未发现阻断提交探索性 GPU 探针的具体问题。** noop／gold／degenerate_discard_dict_output 的实际 reward 为 **0／1／0**；每行64参考均真正执行，无参考缺席、skip或异常代替目标失败。负对照已修复原4F并保留原59P，只在新增真实像素节点失败。可以按既有流程提交探索性探针；执行者仍须核 GPU 本机环境／派生镜像身份及真实首请求的原题面与已有 hints 交付。本报告不证明模型求解、paired 完成、稳定性、训练或留出资格。

本次不是 fresh 公开读者盲审。本人已接触本包私有 oracle／controls、6975 缺图原 actor、COPY v1 失败与 v2 成功、R15 静态和2446正式原件。接续已有独立语义意见，新增读取6975三行完整原件及其prepared、外层退出，未重审其余题。只用本地标准库读取、SHA／JSON和内存内严格统一diff核对，未 import 项目模块、执行任务代码／测试、SSH、Docker或CPU/GPU复跑。只新增本报告，同名原件不存在，旧报告／代码／请求／账本／检查单均未改。

依据当批 `remaining_workflow_20261002.md` 第74—76、113行的非作者接续核查规则。A／D／E／F／G／H／I／L／M／N分别落实为失败归因、角色与真实配置、逐参考与候选字节、固定版本、正式路径、身份链、用途限制、预算／清理、完整日志、原依赖；B／C未改变训练分布／准入挡板，J／K未变实现复用既有静态核查，不据本次运行外推其它维度已全验收。

## 固定身份与 prepared 消费

完整原件根为 `runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/`；正式 job `monai-6975-formal-r15-20261003-5c944a89`，prepared `monai-r15-prepared-20261003-df08dee4`。

| 身份 | 实际绑定 |
| --- | --- |
| R15 manifest SHA256 | `2b788d1ce84228a27894e04886ade347e91993f48ddc9bdeeb8f92de4aa92917` |
| 冻结编排 runner SHA256 | `7dbc9b7b108b816c6da65ed5c8bd01ebb913fc91cf26b995c81d422a3539f63c` |
| prepared replay_summary 文件 SHA256 | `55a9d854ed1ebf81df223a83b9b0b03789001cbd82b7880bc1fe17be4fd7ce5a` |
| prepared_manifest 文件 SHA256 | `2e40943f48e00ba5d10752263919182af5974590a948e229852b63036bea89a0` |
| host_grading_views 文件 SHA256 | `5020d44f0165fc3caea607efce60616e7ce5818c99aeb5ebf2c01cdd39c742fa` |
| base commit／HEAD | `392c5c1b860c0f0cfd0aa14e9d4b342c8b5ef5e7` |
| CPU实际派生 image ID | `sha256:fbfdddc4edda1f0ea4c1b76a572bd95045be4bbd202b197a94e8d8ee14a73fd6` |
| 固定源 vendor manifest | `sha256:0a529471d25c944c76e598474d7a665b20edc2ee95b1a2f30bf9c36fd8db6055` |
| public bundle digest | `sha256:962e5ee3c94e576f93003e1f6465bf5606fbc5377b7ea9ebb3e5b32bf43723e7` |
| 新 environment package digest | `sha256:248b10f8b0d447c3d25965f85fdca8fe06879f759bcd7ce05195ec6e7d482843` |
| 新 grading bundle digest | `sha256:0e7e10ffd9e854b151e11c7aba2d50c8cf5ea6b3604320b8c460d5c3207380f4` |
| grading materials identity | `sha256:790984d103cffad557230cb0188b5c3a5e3e9d6728f3d3a37defeb84cbbc20f6` |
| 原 parent grading digest | `sha256:637914aaac0270ea812bdd853ecfbffdbc6436777043d7d2ced41db9685e543b` |
| R15 registry文件 SHA256 | `4e8ab1f132a4546a53c32ee2845fedc372e837164dd9b41ebeba497d77ef074d` |
| effective test patch SHA256 | `b45d702474e07849816f2540af31513a1c0ef2fa94a0aea9d841fe7a4c00eb97` |
| environment binding资产 SHA256 | `cd5a58a4be3acd202757606e3f0f2614718599d9f481acc7083ab539db474a56` |

沿用[既有R15静态报告](non_author_r15_runner_static_review_20261003.md)已独立核对的1,305 release文件与174固定输入，不机械重复完整census。此次读回prepared五件文件链，summary／manifest／private／public SHA一致；6975 private revision去除registry_sha256后与R15完整固定记录逐字段相同，独立重算grading对象canonical digest命中新bundle。有效patch／原4F、59P、新1P及环境绑定与实际三行ledger／diagnostics一致，scripts_digest均为 `sha256:981626055327a1fe69d30881e890e2d5bff7f29172d255f8d771948a4c4c760f`。

新prepared的public对象与release5 `monai-release5-prepared-20261003-3537d9d8` 逐字段相同，canonical public digest匹配；外层environment digest变更，不能称整份rollout row字节不变。原公开题面未变，不要求新增公开读者。新prepared的完整身份／正常外层退出已由[2446同prepared核查](non_author_monai2446_formal_r15_review_20261003.md)验证，本轮复用该退出范围并直接核6975行内容。此前busy75不算成功准备。

## 三行逐参考结果与失败语义

每行实际命令为 `pytest -rA tests/test_compose.py tests/test_dataset.py`，collected64。本人从三份完整日志逐条提取带正式node ID的PASSED／FAILED，分别与ledger／diagnostics分区逐集合核对，并与owner索引的每条状态比对；192条参考结果完全一致，64个唯一node ID无多项代替、无漏项。num_parsed_outside_segment=0，missing／skipped／unaccounted均空，没有ERROR节点。

| 控制 | 原4F | 原59P | 新1P真实像素 | 模块实际结果 | install／test RC | reward |
| --- | --- | --- | --- | --- | --- | --- |
| noop | 0通过／4失败 | 59通过 | 通过 | 4 failed, 60 passed, 20 warnings | 0／1 | 0 |
| gold | 4通过 | 59通过 | 通过 | 64 passed, 20 warnings | 0／0 | 1 |
| degenerate_discard_dict_output | 4通过 | 59通过 | 失败 | 1 failed, 63 passed, 20 warnings | 0／1 | 0 |

原4F为 `tests/test_dataset.py::TestDatsesetWithLazy::test_dataset_lazy_with_logging_{0,1,2,3}`，每项noop均在 `self.assertEqual(actual,expected)` 触发日志语义AssertionError：实际Apply pending／lazy=False，预期Accumulate pending／lazy=True及操作应用。lazy=False的原P2P logging_4及其余原59P逐项通过。因此noop失败不是缺图、导入／安装或任意非零。

新增P2P为 `tests/test_dataset.py::TestDataset::test_dataset_lazy_dict_returns_transformed_pixels_cpu`。正式body使用1×3×4的float32 MetaTensor、Compose内两个lazy Flipd，Dataset索引后读取字典返回的实际image；先检查shape和CPU device，再比较硬编码双轴翻转像素。负对照真实走到 `torch.testing.assert_close(actual,expected,atol=1e-6,rtol=0)`：12／12像素不符、最大绝对差11.0，前面的shape／device检查已通过。这是执行变换后丢弃dict输出的目标退化，不是异常／缺图替代判错；此节点不绑定唯一内部调用或某种补丁写法。

gold保留 `_apply_transform` 返回值并把默认lazy从False改为None，使Dataset不强制覆盖Compose自身lazy设置；新增像素节点在base与gold均通过，符合P2P定位。负对照也改默认值并执行真实变换，原4F／59P全通过，但dict＋Compose.lazy=True时返回原data而丢掉result，精确触发新节点。原59P不足以区分此退化的已知失真机制在这次真实正式链路被确认关闭。这里只验证固定三个对照，未声称覆盖所有可能修法或已证模型能力。

## Baseline、候选字节与 FrozenPatch 投影

三份baseline均1,334项且文件SHA相同 `5a92966c1f9cc9e9c12f9a938ea2c64da02c45072ad535d78c2a478b5063ed5c`，独立canonical digest为 `sha256:0241a5dba43c1c62be62ee0c34ffae916e14e1e146492f2ca5b3d40e345e3e53`。HEAD／public／runtime image均匹配本轮身份。baseline的environment_package_digest=null原样保留，正式prepared／ledger的实际digest通过另一身份链核对，不补写null。

基线transform.py SHA `1e39afa8d4464c4ef18ac3f1a05c654a213af65e4364fa194923faa92b156ee9`。本人解码gold FP的完整源码，在内存中严格按gold各hunk逆向重建baseline，重算SHA吻合；再逐hunk应用两份原候选patch，与各FP解码完整源码逐字节相同。归档candidate.patch与固定输入包 `inherited6975/controls/` 正文逐字相同，SHA也吻合。本轮未在文件系统改源码或运行git apply。

| 控制 | candidate patch文件 SHA256 | 新FrozenPatch canonical digest | 投影源码内容 SHA256 |
| --- | --- | --- | --- |
| noop | 空输入 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`；无patch文件 | `cefd69f018abeaf91b0803c6e6d8702f93295019f8d2a3e110a517cb728d51e3` | 无修改 |
| gold | `fdd419570d9b18f8b9ce762d0112ab2cfc5a8c3f527c03f198b98bfae6800c3d` | `f4136cbc4068804e0df788a1832cf96335b5a61ed5235a96f092999352b1d54c` | `5d8ba724a4e09bdf533c1030e0891a9acfb00a98069ca6586533cddb4e369bb5` |
| degenerate_discard_dict_output | `326d8624ed445a99281ff33d02b99670e1cc364b827fd26593b745da7ff09118` | `cb1c61bb69f68a587cb1b1b6677024f12c70c3bf4090472e41f2a0249b3fc627` | `a8382325df5169732767963fa29553845514fe29b318ce60184bdcc12ddf369a` |

两候选唯一modify／projection path均为 `monai/transforms/transform.py`，不是dataset.py／compose.py；没有候选test／conftest／fixture修改，ignored_paths为空。所有stage均projection／stage_error=null／git_sanitize verified，classification projectable且runtime_private_pathset_changed=false，FP excluded_pathset_changed=false。独立重算FP canonical digest与projection／ledger一致，各自物理attempt ID和本行run绑定，未读旧FP换身份重评分。noop空entries；baseline重建和两份补丁正文支持本轮实际候选范围。

受信setup原日志真实恢复 `tests/test_compose.py` 与 `tests/test_dataset.py` 两文件，原SHA分别 `ef004f2fa3fb371cfcbadf31bfaa30efb43fa3321e3f77065e54734d1f0d1901`、`7a54e57faf059bca0767e9ebefd9c5dddfac518c6a78d223c860f1fc9c981d29`；随后固定revision补丁两文件cleanly applied，applyRC0／expected2／present2／absent0／irregular空／setupOK1。**RH2_SETUP_RESTORED=2是恢复文件数，不是布尔值或2446的一文件期望。** 它与64项正式节点和R15材料绑定共同支持正确测试面消费，不能仅凭restored计数验收。

## 正式 UID、原图与安装／测试原段

三行root prerequisite实际trace核UID0、O_NOFOLLOW打开普通文件、官方原NIfTI SHA `c01a50caa7a563158ecda43d93a1466bfc8aa939bc16b06452ac1089c54661c8`，真实stdout成功。candidate prerequisite三次均UID54322／home=/home/rh2grader／RC0／verified／stderr空，独立原stdout `RH2_MONAI_FIXED_UID54322_ASSET_OK=1`；其脚本SHA `f0098da4331f5127abc176418a729722eb758c3a6a2b0aef4eeff19a5700c987`。按冻结源码的脚本文字独立重建该SHA一致，包含UID检查、O_NOFOLLOW／普通文件与同官方SHA。manager真实以profile.candidate_exec_uid运行，并独立保留诊断stdout／stderr／RC；非零进入infra诊断，不打任务失败分。正式54322与公开actor／apply54321两个角色不能混用。

完整安装段先保留原sed，再安装types-pkg-resources／pytest、requirements-dev及setup.py develop；6975 original_install与revised_install逐字相同，未加2446的NiBabel4兼容wheel。真实日志为NiBabel5.2.1、torch2.4.1+cu121、numpy1.24.4、pytest8.3.3、Python3.8/testbed；setup.py develop实际将egg-link安装至/testbed。没有实际pip ERROR、失败命令或RH2_INSTALL_CMD_FAILED输出，trap声明不算失败marker。三行install末RC0且未skip／截断，实际时长15.550／16.069／16.742s；测试段RC1／0／1，时长22.263／21.535／22.746s，均segment_completed=true。包装exec RC0是正常交付测试结果，不把真实testRC1抹掉。

安装警告必须保留：每行有EasyInstallDeprecationWarning和SetuptoolsDeprecationWarning。测试每行20warnings，含TorchScript optimizer、NumPy别名、SciPy旧namespace等弃用内容；没有“全无警告”的结论。owner此次warning字段限定真实安装时间段，列出的四行含两警告和warnings.warn续行，与原段一致；该字段不等于完整测试／构建警告清单。pre/post runner digest相同 `1cfac6828a8ce1101528108a0a3379da1fe8e2b0ba4a9021ea32c5ffc26e13a4`，prefix owner54322、导入/testbed/monai/__init__.py和版本observations一致。没有仅按末RC判断前序命令成功。

## 实际资源、预算、清理与槽退出

六份完整container inspect覆盖每行candidate与grader，各自精确rh2.run_id匹配本行；实际Image均上述fbfdddc4…完整ID。NanoCpus=2000000000／Memory=4294967296／PidsLimit=512、MemorySwap=4294967296、network none、privileged false、Init true、无bind／Mounts／GPU DeviceRequests。Config.User空对应受信bootstrap，不能因此断言候选安装／测试以root执行；实际apply与正式prerequisite角色由独立执行记录核对。

ledger image_identity为 `local_build:sha256:fbfdddc4…`，image_ref／image_id_actual为裸完整ID，image_digest_expected=null且image_local_build=true。三个字段各保留原义；本机派生ID不是vendor manifest或跨宿主registry摘要。实际正式image inspect、COPY receipt、新prepared绑定、公开actor attempt和三行均同一ID；13项源件SHA全部与本轮baseline entries逐项一致，官方原图SHA亦在baseline命中。

三行budget原件均before1800→after1800、test_seconds_unchanged=1800，原命令setup1800／candidate900／grading3600／cleanup120／image1800，同冻结编排；gold及负对照只读本轮noop资格ledger。真实行总时长462.69／475.67／474.36s。没有外层超时／强杀／观察错误，无额外重评分；noop资格absent，后两行ok:本轮noop报告，execution_failure_decision=null，不是训练资格。

每行candidate ledger cleanup removed=true／rm:ok；完整runner末条JSON与campaign逐字段一致，manager创建1／移除1，containers_open／supply_open／cleanup_failures空、regrade0、final_status0。自身run label残留查询RC0／containers=[]／stderr空，runner RC0。评分容器network none，本轮无需额外relay链；本报告没有通过父标签扫描其它包。

按observed_at选择最新 `monai-6975-formal-r15-20261003-5c944a89.snapshot-cd9fa9f1.json`，SHA `3db2a47612890a12546782fa2989a517e0cf16a06365901b033b99fb9bb512d1`：slot0／finished／returncode0／launcher exitRC0，02:42:47 UTC结束。command与 `.launch.json` 逐元素一致，launch SHA `420c91706779cb34087f74b148248c8f56b7501bdc1152e51b0aebeb99a8c1eb`，绑定新prepared、R15、固定输入和冻结runner。外层launcher_log仅目录打印，不能替代内部完整日志；内外两层正常退出和清理合并支持本次完成。

HostConfig是创建时限额证据；正式grader无独立cgroup／CPU或内存峰值采样，resource_facts=null、mem_peak_mb=4096原样保留，不能据此宣称实际峰值／余量。formal StorageOpt=null，旧actor StorageOpt={}，8GiB可写层配额未实证；COPY build daemon资源上限未测。上述范围不升级为平台安全全验收。

## COPY与公开 actor 的复用边界

复用[实际COPY／公开actor独立报告](non_author_public_asset_runtime_review_20261003.md)的已证范围，SHA仍 `af91e9e87da3678430a17d709403dc2e032f341de3fb1255698a01cd5256d09f`；R15静态报告SHA仍 `1812fd7b3dda189e13cd9e91b99c238c66b7f882a13ae3d6b9cd9199407480b4`，同prepared的2446报告SHA仍 `dcba766535d6f613a7e00e468735230ed24f988dd178087463b16b2e3324fe36`。此次读回key receipts和13源件绑定同ID／base，不重复既有全部CC桩运输与COPY层census。

COPY job `monai-6975-public-asset-image-v2-20261003-526bfdc3` 的receipt SHA仍 `607bbfe396e72d5e11e633240f05ff11b5fa00c7a140f5ff631ab8d82918b534`；原源13层为新14层前缀，仅新增原图COPY层，原运行Config保持，Labels及Config.Image构建元数据变化的旧限制继续保留。旧receipt actor_verified／new_test_executed／formal_acceptance_passed=false原样存在；本次正式证据另立，未回写它或用归档资产冒称整题通过。

公开actor `monai-6975-actor-20261003-b7c29487` attempt SHA仍 `74fb0e995dd82a9392c462e9c7dd34ac4c9a6c6d63d30fd0af788488f3b682d7`。其UID54321真实公开原图LoadImaged／RandAffined direct／Dataset路径成功、原lazy矩阵精确目标AssertionError RC1、原56模块节点全通过、同镜像身份与HostConfig／cgroup／capability、完整CC桩链和清理／finished0范围沿旧报告有效。R15没有改变公开对象、原命令、COPY配方或同CPU实际镜像；actor曾用release5，可以复用公开开发能力，不能顶替R15私有正式评分，后者由本次192参考结果承担。

首条真实CPU actor请求仍是generic `Devcheck run: execute exactly the tool calls you are given, then stop.`，原件 `stub/requests/messages_000.json` SHA `54d4ecfd18dfd2ead09e6cf87e1becad340de62683a33df6d3b2b6d125bcb82b`；不是正式题面／hints已送到solver的证明。两项generic marker `interpreter_in_tool_result=false`、`bashenv_denied_for_agent=false`保留，不机械补marker／重跑。本轮证明可执行公开开发操作，未证明真实训练typed actor的采样、轨迹capture、训练消费／loss或稳定性；GPU首请求交付、本机身份和真实模型候选仍待后续原件。

## 原件索引与适用限制

作者检查单 `checks/monai6975_formal_r15_cpu_c_20261003.json` SHA `0cb7757c35855da2b7eb92105e11a4f4fa7fa33b857f50747d59f367f958bb69` 只作为索引。其登记40文件与实际目录文件集合精确相同，40份SHA／bytes已独立全匹配，JSON／JSONL可读，全部三份eval.log正文及候选字节已直接核对。三份完整eval.log SHA分别：

- noop：`6e3896bf4cec70583929c6de75c45ccfbb911f3c918a5ce006081083fbeb67df`，82,348字节。
- gold：`53e9217439f3fc3c2dcd8cad32baa77ce9e5dab4c91e9ee66bf5752e1b3795b3`，79,205字节。
- degenerate_discard_dict_output：`bdfb9ffb48035caa77ba887925535ddf4dad88fa6688db2dd506433e5e85cbee`，81,467字节。

正式根目录各行保存ledger／diagnostics／完整eval.log／candidate.patch（noop无）／baseline／FrozenPatch／projection／stage／classification／budget／inspect／runner原件。作者草稿中“改dataset／compose”及“restored必须1”的假设纠正与原件一致，不是CPU失败、原件重写或重新运行。本文仅核6975固定R15 CPU资格，旧阶段“正式64参考未执行／consumer待发布”报告保留其历史适用时点；本次消费R15新prepared已实证，不把旧未完成状态静默改写。

当前没有必须先修的材料误拒／漏判、缺图／依赖或清理退出阻断。提交探索性GPU后仍须保存真实输入、跨宿主构建／运行身份、完整模型候选与评分并按题级审计；本轮没有调整分数、修改预算、热改冻结版本或自动解除训练挡板。
