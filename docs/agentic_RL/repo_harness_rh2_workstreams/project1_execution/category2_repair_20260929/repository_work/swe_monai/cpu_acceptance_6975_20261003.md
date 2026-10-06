# MONAI6975：当前 CPU 证据与缺口

2026-10-03。**R15正式矩阵已完成0／1／0，题主已核40份完整原件、三行共192个参考结果；[非作者完整验收](reviews/non_author_monai6975_formal_r15_review_20261003.md)通过，单题GPU请求已落账并直接通知。** 官方原图、公开actor、两文件受信消费已验证，旧缺图版本 `monai6975-dataset-dict-pixels-cpu-v1` 继续阻断；当前材料为该版本加 `+public-nifti-v1`。不授予训练或留出资格。

## R15正式结果

| 对照 | 原4个F2P | 原59个P2P | 新像素P2P | 正式评分／完整模块 |
| --- | --- | --- | --- | --- |
| noop | 全失败：lazy调度日志不符 | 全通过 | 通过 | 0／4失败60通过 |
| gold | 全通过 | 全通过 | 通过 | 1／64通过 |
| discard_dict_output | 全通过 | 全通过 | 失败：12／12像素不符 | 0／1失败63通过 |

三行均运行完整 `pytest -rA  tests/test_compose.py tests/test_dataset.py`，每行64参考无缺席、skip、ERROR或未归账。错误候选确实修复lazy默认值，却丢弃字典变换后的返回值，新增节点在真实像素比较处失败；不能用shape、调用参数或原日志通过代替结果正确性。gold与错误候选的源码修改均只在 `monai/transforms/transform.py`，测试文件是Compose／Dataset两文件，不能将测试路径当候选源码路径。

实际 job `monai-6975-formal-r15-20261003-5c944a89` 在cpu-c经共享槽准入，`cpu_slot`及launcher均finished／RC0；新的prepared为 `monai-r15-prepared-20261003-df08dee4`。R15 manifest SHA `2b788d1ce84228a27894e04886ade347e91993f48ddc9bdeeb8f92de4aa92917`，启动前核1305发布成员、174输入及固定runner SHA。各行新导出baseline／FrozenPatch／projection，控制补丁与实际源码逐字核对，原图只来自固定COPY资产，不重绑定旧候选。

[题主完整原件核查](checks/monai6975_formal_r15_cpu_c_20261003.json) SHA `0cb7757c35855da2b7eb92105e11a4f4fa7fa33b857f50747d59f367f958bb69`保存40份原件摘要、逐参考状态、源码与实际inspect。实际candidate/grader镜像均为 `sha256:fbfdddc4edda1f0ea4c1b76a572bd95045be4bbd202b197a94e8d8ee14a73fd6`；每行两容器HostConfig为2 CPU／4 GiB／PID512。UID54322原图预检通过；受信恢复两测试文件，无缺失／异常形状。安装段均RC0、完整且无失败命令，easy_install／setup.py弃用警告保留；测试段RC1／0／1，每行20warnings。候选移除、grader manager关闭、按本行标签查询的残留及外层退出都已确认，当前本仓无CPU在途。

作者私有审计草稿曾将恢复数量当作单文件常量1，首次断言失败；实际 `RH2_SETUP_RESTORED=2`是本题两个测试文件的数量。已根据固定消费者和原日志修正草稿，未重跑CPU或改原件。此前亦在审计前按原控制补丁补齐transform.py的源码核对；这都是审计假设校正，不是运行故障。

同镜像UID54321公开actor的原题NIfTI例子、真实有限CPU张量和完整清理按已有证据复用。它采用脚本桩和通用首prompt，不能证明GPU正式题面的实际交付；两项原通用marker false保持。资源限额不是实测峰值，CPU派生ID不是GPU本机镜像证明，正式训练typed actor租约仍未接通。[固定单题输入](materials/6975/probe_request_r15_v1.json) SHA `db75fe723a73f2db160439b271023c033fc82316d03cfdab3c81a37f6d1a91e3`已落账并直接通知GPU，请求ID`swe-monai6975-r15-dict-pixels-public-nifti-20261003-v1`。非作者报告SHA `2d6b9c32c4e7e8c644c9fd697c3aa8b3448b504e2f09dca0e245eb3a36231dc2`；GPU沿已有精确image_override另核本机镜像与首请求。

## 既有来源、公开恢复与私有诊断证据


| 范围 | 事实 | 意义与下一步 |
| --- | --- | --- |
| 原镜像 | 固定源 manifest `0a529471…`；实际ID `789cb5d1…`；base `392c5c1b…`、13源件SHA、实际2CPU／4GiB／PID512与清理已核。 | root准备仅证明来源；历史 `requirements-dev.txt` 删除MetricsReloaded行保持，actor diff已确认，不宣称clean。 |
| 原公开actor | UID54321／testbed Python／实际transform.py／CUDA false。命令 **0／1／1／0**，原公开模块 **56项通过、20 warnings**。 | 原图实际缺失，原例在缺图断言处失败，尚未执行LoadImaged／RandAffined；外层RC0与all_match_expect=false分别保留。 |
| 恢复镜像 | 官方原图531,671 bytes，SHA `c01a50caa7a563158ecda43d93a1466bfc8aa939bc16b06452ac1089c54661c8`；实际新ID `fbfdddc4…`。原13层保持，仅多一COPY层，13源SHA不变，Config只差Labels／Image元数据。 | root核Git初态，UID54321核原图可读／SHA／NiBabel形状；资源与清理、外层RC0成立。不改变源码、测试、依赖或原题面；新环境已由R15固定登记，该准备行自身不证明正式评分。 |
| 恢复公开actor | `monai-6975-actor-20261003-b7c29487` 命令 **0／0／1／0**；原NIfTI直调／Dataset均输出 `[91,109,91]` CPU有限float32张量，原SHA匹配；原公开模块仍 **56项通过**。 | 实际UID54321、解释器、HostConfig/cgroup、完整captures／CC轨迹和两层清理已核，all_match_expect=true；非作者窄核未见恢复切片新阻断。CC桩通用首prompt不是正式原题面交付或模型求解证明。 |
| 内存矩阵 | 六行直调／Dataset × lazy True／False／None均返回正确像素；Dataset在True／None传effective=false，精确目标AssertionError。 | 原题策略缺陷仍在，非任意非零。随机RandAffine输出不互比，不用调用数作唯一oracle；新增像素P2P仍需保留原F2P。 |
| 新节点私有诊断 | 未修复代码／gold各1项通过，discard_dict_output在像素断言失败，12／12像素不匹配。三行源件／补丁／导入检查RC0，清理完整，外层RC0。 | 只执行新增节点，root私有诊断，不产正式reward，不证明完整64参考或正式consumer；私有容器资源只留请求flags，未归档HostConfig。 |
| 正式新材料 | Compose／Dataset两文件，原4F2P＋59P2P保序，新增一个像素P2P，共64参考；合并发布请求已由R15消费，回执returned/safe_closed且题主ack完成。 | 一次发布两文件测试＋官方COPY环境，新prepared `df08dee4`已核，正式核 **noop0／gold1／discard_dict_output0**、64参考逐键、逐段RC、材料/候选/投影身份和两层清理，另做非作者结果核查。 |

原件：[原镜像](checks/monai6975_image_cpu_c_20261003.json)、[原actor缺图](checks/monai6975_actor_original_cpu_c_20261003.json)、[COPY镜像](checks/monai6975_public_asset_image_cpu_c_20261003.json)、[恢复actor](checks/monai6975_actor_public_asset_cpu_c_20261003.json)、[非作者实测报告](reviews/non_author_public_asset_runtime_review_20261003.md)、[新增节点私有核查](checks/monai6975_private_node_cpu_c_20261003.json)、[固定两文件发布输入](materials/6975/publish_request_v1.json)、[合并发布输入](materials/6975/publish_combined_request_v3.json)。完整原日志、captures、桩轨迹、外层与清理原件已回收到 `runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/` 对应作业目录，摘要逐件绑定。原公开56项不是正式新64参考分母。

历史准备尝试保持：295281d0为busy75、未执行；8e8b9cff构建成功，但数值UID的Git身份探针被dubious ownership拒绝，已完整归档清理，没有Git版本证据。[v2脚本](cpu_prepare_6975_public_asset_v2.py)分开root Git和非root图像检查，526bfdc3实际准备成功，然后以正式actor初始化路径完成公开复验。旧三个资产报告不回写成新实测接受。

[非作者运行窄核](reviews/non_author_public_asset_runtime_review_20261003.md)SHA为 `af91e9e87da3678430a17d709403dc2e032f341de3fb1255698a01cd5256d09f`，接续既有上下文，不是fresh公开读者或独立重新运行。它核完整原件及范围，没有放行整题CPU／GPU。准备root探针只留资源flags，没有独立HostConfig；构建daemon不受探针2CPU／4GiB限额证明，也未检查新增层tar。actor两个通用marker false保持；实际StorageOpt为空，8GiB层配额及资源峰值无额外强制证据，不宣称平台保护全验收。

当前正式矩阵、题主读回及独立完整核查均完成；之后需统一GPU执行者收齐两模型完整结果，原负责人继续行为分析和必要修复。预算／超时截断、缺模型或缺评分保持待接续，单次不作稳定能力结论。CPU和GPU均仍需要，本包未提供退租就绪。

当前合并发布请求为 `swe-monai6975-dict-pixels-public-nifti-publish-20261003-v3`，输入SHA `0dffab73849f35e0bc51cbe3ae8f3c3e68ac53ebee82ddf4064656fc9709358d`；已经通过总账提交并直接通知发布者，R15正式回执已核收。原测试／64参考／候选字节不变，COPY环境明确同时供actor和grader受信绑定，原vendor安装／测试命令保持。旧未领取v1由发布者确认未实施／无在途后取消，本题已核回执并ack、释放旧active，旧缺图版本阻断和原件均保留。环境单独v2原件SHA `18f8ae20f7aca42abd35bb07bc3a3e72285adc3b726fcd8ee777c11ba9f95706` 保持，但不单独提交，改由合并请求一次发布。当前正式作业已结束，无本仓CPU在途或后台自动重试；行政恢复仍有效。正式noop的安装15.55秒RC0、测试22.263秒RC1，4原F2P按目标缺陷失败、59原P2P和新增像素P2P均通过；module footer为4 failed/60 passed/20 warnings，未以外层0覆盖真实测试失败。其安装弃用警告保留。完整三行已得0/1/0，细节见上方正式结果；非作者完整原件验收通过，单题探针已提交。
