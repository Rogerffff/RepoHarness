# MONAI2446 R15 正式 CPU：非作者完整原件验收

日期：2026-10-03。审查者：GPT-6.1 Sol / high，非材料作者。

## 结论

固定版本的 MONAI2446 CPU 材料、公开开发能力和正式四行矩阵通过本次独立核查，未发现阻断提交探索性 GPU 探针的具体问题。可以提交探索性探针；执行者仍须核 GPU 本机镜像/环境身份与首条真实请求的原题面和已有 hints 交付。本报告不证明 GPU 求解成功，不授予训练/留出资格，也不代表 MONAI6975 已完成正式验收。

本次不是 fresh 公开读者盲审。审查者已经接触本包私有材料、controls、前次静态审查及 3715/6975 运行原件；此次新增读取 2446 的 prepared、四行正式 ledger/完整 eval.log/diagnostics、候选 patch、baseline/FrozenPatch/projection/stage/classification、八份 container inspect、runner log、最新外层 snapshot，并复核同镜像公开 actor 和镜像准备原件。作者检查单作为索引，不替代原件。仅使用本地读取、JSON/SHA、内存内统一 diff 字节核对；未 import 项目模块、未执行任务代码/测试、未 SSH/Docker/重跑 CPU，仅新增此报告。原同名文件不存在，旧报告/实现/原证据均未改。

## 版本与新 prepared

证据根：`runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/`。

正式 job：`monai-2446-formal-r15-20261003-d5aae6a8`。新 prepared：`monai-r15-prepared-20261003-df08dee4`。沿用已经独立核过的 R15 1,305 个 release 文件、174 个固定输入和冻结 runner，不机械重跑。

| 身份 | 实际值 |
| --- | --- |
| R15 manifest SHA256 | `2b788d1ce84228a27894e04886ade347e91993f48ddc9bdeeb8f92de4aa92917` |
| runner SHA256 | `7dbc9b7b108b816c6da65ed5c8bd01ebb913fc91cf26b995c81d422a3539f63c` |
| 新 replay_summary 文件 SHA256 | `55a9d854ed1ebf81df223a83b9b0b03789001cbd82b7880bc1fe17be4fd7ce5a` |
| 新 prepared_manifest 文件 SHA256 | `2e40943f48e00ba5d10752263919182af5974590a948e229852b63036bea89a0` |
| 新 host_grading_views 文件 SHA256 | `5020d44f0165fc3caea607efce60616e7ce5818c99aeb5ebf2c01cdd39c742fa` |
| 2446 public bundle digest | `sha256:e28bef68fdde56691302cf89bf38e41ecdd122166538f6303beefda8b450b503` |
| 2446 grading bundle digest | `sha256:daa0d5055a89be7e9c0a9710e928e2969eb87d818c6ca4b688dd8384573752a7` |
| grading materials identity | `sha256:7b12ba8af3b62aee6ceba5d5d94255efabd68614dc91514994b22bfcdc87752a` |
| 正式实际 image ID | `sha256:28959a332c8a17ebfb2db681d3afaf79f8fd6e845ba51406fc7772f32453bcdd` |

summary 对 manifest/private 文件的 SHA、manifest 对 prompts/rollout views 的 SHA 均匹配。新 private revision 去除 registry_sha256 后与 R15 registry 的 2446 完整固定记录逐字段相同；原评分面恢复后的 canonical digest 匹配 parent `baf96ec699b48a0aa07608ed405e240571103868a92016aea4e8eb9d3579e4f0`。有效测试 patch SHA 为 `c413f2b150eec668aee425cf1171faedaf7fdbb8c9a3bae171328a741231b7e7`，固定 registry SHA 为 `4e8ab1f132a4546a53c32ee2845fedc372e837164dd9b41ebeba497d77ef074d`，全部与四行诊断一致。

新 prepared 的 public 对象与原 release5 prepared 逐字段相同，public canonical digest 也匹配；其外层 environment_package_digest 因修订变为 `ad9664900cf6e7693cca97354038ad80edf8146e76cc536efbdefa42181c89db`，所以不能把整份 rollout row 宣称字节不变。这不是公开题面改变，公开 actor 交付证明仍需另看真实请求。

按 observed_at 选择最新原件：prepared 的 `snapshot-c961eeb8.json` finished/returncode0、launcher exit0；正式的 `snapshot-b745af06.json`（SHA256 `fb5caf42c76a10e3a40c20bf60d7c7e79f1adec78ea8f1ce9cff3fc0f68e996f`）finished/returncode0、launcher exit0，slot0，02:15:17 UTC 结束。两次 command 与各自 launch 绑定的新准备/冻结工具路径一致。此前 busy75 申请不作为本次 prepared。外层0只证明作业退出；下述内部原件才支持评分验收。

## 完整四行及失败归因

表中“列表原状”为原 F2P `test_datalist`；“shuffle/换缓存”为原 P2P `test_shuffle`、`test_update_cache`；“数组打乱/缓存”为新增 P2P `test_shuffle_ndarray_list_and_cache_cpu`。

| 控制 | 列表原状 | shuffle | 换缓存 | 数组打乱/缓存 | 完整模块 | install/test RC | reward |
| --- | --- | --- | --- | --- | --- | --- | --- |
| noop | FAILED | PASSED | PASSED | PASSED | 8 passed / 1 failed | 0 / 1 | 0 |
| gold | PASSED | PASSED | PASSED | PASSED | 9 passed | 0 / 0 | 1 |
| array_no_shuffle | PASSED | PASSED | PASSED | FAILED | 8 passed / 1 failed | 0 / 1 | 0 |
| alternative_list_copy | PASSED | PASSED | PASSED | PASSED | 9 passed | 0 / 0 | 1 |

每行完整 `pytest -rA tests/test_smartcachedataset.py` collected9，九个 node 均有真实 PASSED/FAILED 摘要，无 ERROR/skip、参考缺席数0；四行合计16个正式参考结果，原/新增分区与 ledger/diagnostics 一致。所有 log.partial=false、segment_completed=true；四份 eval.log SHA 独立匹配 ledger。测试 shell exec RC0 是包装脚本正常结束，真实测试段 RC 保留为1/0/1/0，未拿 exec0抹掉失败。

noop 的具体 AssertionError 为输入调用者列表从 `[0,1,2,3,4]` 变为 `[2,0,1,3,4]`，`assert_allclose(data_list,data_list_backup)` 的3/5元素不符；同时新增 P2P 通过，说明原实现内部 shuffle/cache 尚正确。array_no_shuffle 在 `assert_array_equal(np.stack(dataset.data),expected)` 比较未打乱 `[0,1,2,3,4]` 与期望 `[2,0,1,3,4]` 失败，原列表 F2P 已通过。这是针对退化行为的失败，不是任意依赖异常。gold 与 list-copy 替代均保留打乱/缓存并通过全部参考，未把 gold 字面形式作为唯一可接受实现。

## 安装、候选 UID 与警告

四行 root prerequisite 的实际 trace 核 UID0、NiBabel4.0.2 和固定 wheel SHA `c4fe76348aa865f8300beaaf2a69d31624964c861853ef80c06e33d5f244413c`，输出成功；candidate prerequisite 均为 UID54322、RC0、verified，原 stdout `RH2_MONAI_FIXED_UID54322_ASSET_OK=1`、stderr空，脚本SHA `28810f676f5957e89dc24cf5658fdadf044d35b3b6e4236f4a694b0e6a3f2de2`。这是正式 grader 身份，区别于公开 actor/apply 的 UID54321。

完整安装段实际先从固定本地 wheel 离线/no-deps安装 nibabel==4.0.2，再执行原 vendor 的 sed、types-pkg-resources/pytest、requirements-dev、setup.py develop。四行均在前后原日志输出 NiBabel4.0.2，setup.py 的 torch1.13.1+cu117、numpy1.24.4、Python3.8/testbed 路径一致，实际 egg-link 指向 `/testbed`；pre/post runner digest 一致，导入源码为 `/testbed/monai/__init__.py`。没有实际 RH2_INSTALL_CMD_FAILED 输出（声明 trap 的 trace 不算失败 marker），没有 pip ERROR 或实际 install 非零，段末均0、未skip/截断。没有仅靠末 RC 判断安装。

必须保留警告：每行安装有 pkg_resources、setuptools installer、easy_install、setup.py install 的弃用警告；测试每行20warnings，含 int64 NIfTI 在 NiBabel5 将报错、np.bool、scipy 和 pkg_resources 等。当前 NiBabel4.0.2 实际测试通过相应 shape节点，未出现 NiBabel5 错误。这些警告不是本轮阻断，也不是“无安装警告”。作者检查单 `installation_warning_lines=[]` 是其提取字段，不能代表原日志无警告。镜像 build 原件另保留 pip root 用户与 InvalidDefaultArgInFrom 警告；显式实际 BASE_IMAGE 和构建结果明确，未冒称无警告或 build daemon 限额已测。

## 新 baseline/FrozenPatch/投影的字节核对

四份 baseline 都有736项，原文件 SHA `e62ca9ede9d4e8434de91684fd7a84830e85f44f92475d149540a7ece7d8c578` 相同；独立重算 canonical digest 为 `sha256:8de0d2139b533d32fce8238e98e9aa8680f773611e6988d1b036cd83e8b8e570`。固定 base/HEAD 为 `05b2da61d70324c2f02b5d72429ddb7cc171b9b9`，runtime image/public 身份匹配。baseline 的 environment_package_digest=null 原样保留，prepared/ledger 的实际 environment digest 由另一身份链核对，不补写此 null。

基线 `monai/data/dataset.py` 内容SHA `22f52cd44c1b8bc2afac1111aa6824e4c563920a631c3336984a910bd264299a` 与镜像 source_identity 原件匹配；基线测试SHA `25717b4fff4134d31bc15f5bb31b490b976c0be32636824935ad3bdad41cfa3b` 与登记原测试匹配。独立从 gold FP 解码完整源码、严格逆向原gold diff重建基线，SHA匹配，再内存中逐hunk应用三份原候选diff，与各FP解码源码逐字节匹配，无文件/代码执行。

| 控制 | 新 FrozenPatch canonical digest | 投影源码内容 SHA256 |
| --- | --- | --- |
| noop | `080afbe2e97e0f43b9937e60ea4ac344ad6ec9eafe83b1326ccb4119b691abfd` | 无修改 |
| gold | `008b8adb07737d23376f28e838149768ec39d036649e80790507042cf8dc9714` | `f29bf46a6bc40e9d4e09ac1e94e46513fcec160c860ca87cbe6633f01b4e301b` |
| array_no_shuffle | `38d1034e36316bc4e333296232cd94fcd69c99cbd558956fdfb26c32ba85742e` | `1653727e6f823ad96967d6f717d8a49db05b2f136e782a4f3df73f16c1ea811b` |
| alternative_list_copy | `89d47002bd88f5443bab59392a90782929fcd311e680f4e529c9b4f13349d25b` | `2a2d2283b58328f143dfc1d226b4ddf3e132bbc68d107aa77db2f6f72ffea4bb` |

三行唯一 modify/projection path 都是 `monai/data/dataset.py`，无测试/fixture修改、ignored_paths为空；noop空entries。所有classification projectable且私有/excluded路径集合未变；FP、projection、ledger的digest与每次全新物理attempt/run身份一致。三份归档 candidate.patch SHA/正文与固定输入逐字相同；gold copy(data)、退化array分支省shuffle、替代list(data)均与期望机制相符。不是旧FP重绑材料身份。

## 实际容器资源、身份与清理

八份完整 inspect 覆盖每行 candidate 和 grader，SHA/自己精确run label与campaign记录匹配：均实际 Image=`28959…`、NanoCpus=2000000000、Memory=4294967296、PidsLimit=512、MemorySwap=4294967296、network none、privileged false、Init true，无 bind/GPU DeviceRequests。Config.User为空对应受信bootstrap；实际 apply UID54321、grader prerequisite/test配置54322、prefix owner54322不能被空User替换成“候选root”。

ledger image_identity 实际是 `local_build:sha256:28959…`，不是裸ID；image_ref/image_id_actual为完整ID，expected manifest=null且image_local_build=true，四行一致。它是 cpu-c 局部派生ID，与来源vendor manifest不同；不能将此ID宣称跨宿主registry manifest，GPU须记录其本机actual ID与同固定源/配方/wheel证明。

四行 budget 原件均 before300→after900，test_seconds_unchanged=1800；原命令candidate900、grading3600、cleanup120、image1800，未改测试预算。实际行总时长240.43/256.31/236.73/243.00s，无外层超时/强杀字段，无observation_errors。

每行 candidate ledger cleanup removed=true/rm:ok；runner完整末条JSON与campaign相同，manager创建1/移除1、containers_open/supply_open/cleanup_failures空、regrade0，final_status0。自身run标签残留queryRC0/容器空/stderr空，四个runner RC0；配合外层槽finished0与launcher0确认正常退出。网络none，无正式评分relay应额外保留；这里不以父job标签推扫其它包。

实际HostConfig证明创建限额；正式grader没有独立cgroup读回和峰值归档，ledger resource_facts=null、mem_peak_mb=4096一律原样保留，不当真实峰值或余量。formal StorageOpt缺少值、actor StorageOpt={}，也未证明profile声明的8GiB可写层磁盘配额。网络/能力等事实是本轮角色范围，未升级为平台安全全验收。

## 同镜像公开 actor 可复用范围

复核 `monai-2446-actor-20261003-b6bf42bd` 的20件登记artifact SHA、全部captures、attempt/prelaunch/activation/52事件trajectory/5份实际request/清理和最新 `snapshot-d874f127.json`，外层finished0/launcher0。四命令与原公开命令JSON逐字同，命令文件SHA `5171897e0f188192fa2748388ee531a12a35c0ca231e971994d1bb201d7c826c`；四tool_use/result ID一一对应，message_start5=request5，harness0日志完整、stderr空、CC2.1.205终止completed。

实际同image ID、base HEAD/source SHA；UID54321、testbed解释器、MONAI源码、工作区/tmp可写，NiBabel4.0.2真实输出。公开SmartCache复现输出shuffle=True调用者列表被修改、内部顺序和缓存正确，shuffle=False全部正确，以明确input ownership/shuffle AssertionError RC1结束；不是任意nonzero。公开原模块7节点全PASSED/20warnings，未含新私有节点。prelaunch HostConfig2CPU/4GiB/512与实际cgroupv2 cpu.max=200000/100000、memory.max=4294967296、swap.max=0、pids.max512匹配，actor实际CAPPRM/CAPEFF0/NNP1。退出后agentprocs0、Git状态0，252新文件主要缓存，不等于零写入；container_rm0、stub0、relay/network失败空、label残留/force后残留空。

该actor用release5而非R15启动；由于公开对象、公开命令、实际派生image、base/源件和角色开发操作未变，它可以复用为这张cpu-c镜像的公开开发能力证据，不能复用为R15私有评分证据，后者由本次四行承担。两项通用marker `interpreter_in_tool_result=false`、`bashenv_denied_for_agent=false` 原样保留；直接身份/预启动ACTIVATION_WRITE=DENIED分别有证，不机械改false或重跑补marker。

首条真实请求仍只有通用“Devcheck run: execute exactly the tool calls you are given, then stop.”，没有正式原题面/hints实际交付证明。public保持与actor消息交付是两件事；GPU探索请求必须继续明确 `actual_formal_prompt_delivery_in_cpu_actor=false` 并让执行者核真实首请求。公开题面未变，当前不需要新增公开读者盲审。

## 原件完整性与保留

作者检查单 `checks/monai2446_formal_r15_cpu_c_20261003.json` SHA256 `02a37a0caa6e0dc563e187b222b82d89a1e51c14266a798fee9f611a8859d7d2`；其53个登记文件SHA/bytes已独立全部匹配，之外另核prepared文件链、actor20件和image10件。实际读原件结果支持其0/1/0/1与16参考结论；local_build前缀纠正是字段语义修正，不是CPU失败或重跑。安装警告空字段的限制如上，作者原件不回写。

四份完整eval.log SHA256：noop `70c56c634daa304ba815d249a30a58036d4cc0b6d748d79ec1ff4c76364f502f`；gold `c0546dfe109f0ab2135ae58a44ea530c6b09fe04595619147c0b2aca172c2c74`；array_no_shuffle `d0aab971a0ed04fa69496c566bbb6de117c210d48e104df70635146472acc1e1`；alternative_list_copy `77c9c1ed03143cf587ce89dc4fdf30fb1955726a5090c89841e905eea39e66f3`。各行目录保存ledger/diagnostics/FP/baseline/projection/stage/budget/inspect/runner原件，可逐项追溯。

本报告仅2446固定CPU验收。此前3715、6975、R15静态报告原件保留；GPU环境兼容、真实模型求解、正式题面首请求交付、跨宿主镜像ID、正式资源峰值及训练用途未验证。
