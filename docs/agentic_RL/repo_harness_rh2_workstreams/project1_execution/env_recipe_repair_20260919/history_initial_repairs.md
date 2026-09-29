# 已发现环境问题：配方修复与真机复验

2026-09-19 / B Codex。用户授权与 Claude 的评分链路修复并行。**Claude 拥有通用评分代码；本批 Codex 只改环境配方、实验材料和记录。** 复用已完成的[零分审查](../swe_grading_wiring_20260915/zero_reward_audit_20260919/README.md)，不重复全池诊断，不调整 reward、参考集合或正式训练准入。

**最新安排：** 用户已允许按实际文件修订DVC安装配方，保留原版及差异；全部已知问题的后续安排、待具体决策边界和运行状态见[短工作队列](remaining_work.md)，逐题证据索引见[known_issues.json](known_issues.json)。

**同日追加授权与状态：** 用户现已授权Codex自行决定本批必要环境修订并记录，不再等待每项回复。最新范围包括有来源的测试材料、显式参考绑定和资源配方；原记录中的“待讨论/不在本批”是此前边界，以[决策表](decisions.md)及[当前执行队列](remaining_work.md)为准。它们均先作为独立诊断版本，尚未改正式训练题包或通用评分语义。

**已验证的新结果：** DVC4778安装修订与新增依赖canary、mypy11966/Moto6913离线安装、Dask7138的92个pytest兼容失败、MONAI1121的4个NumPy失败，均已完成真实对照。8题参考绑定fresh对照恢复noop目标失败/gold参考全过；安装与参考外问题仍独立保留。大批逐题扩展、材料和兼容验证还在执行，不以代表成功代替全范围验证。

## 第一批及方法

| 题目 | 已有证据与本批动作 | 复验要求 |
| --- | --- | --- |
| MONAI-1121 | 权重下载失败；预置固定 ResNet 权重并明确候选 UID 的读取位置 | 真实 RH2 deny_all 下相关8个P2P能加载权重；noop目标缺陷保持、gold目标修复；额外NumPy/fixture问题仍单列 |
| Dask-10972 | pip 构建隔离获取 setuptools 失败；先核对构建要求及现有包版本，准备离线 wheel 资产 | 安装关键命令实际成功；noop/gold原目标0/1不变、参考逐ID可解释；不升级被测Dask或修改题目 |
| DVC-4778 | F2P被重复命名组 `ps_d` 正则异常遮蔽；先定位实际依赖与源码/历史要求 | 最小依赖修复后noop真正到达目标行为、gold通过；核对其它受影响测试，不猜测降版本凑绿 |

先核对根因，再建立单变量配方。原镜像、原账本保留，派生镜像使用独立名称并记录实际 image ID。完整运行使用已完成216题实验的远端代码快照、真实 replay/grader 与同一正式身份；不注入P-A资格。Claude的新代码不会自动覆盖这一实验基线，合并后再选针对性对照。

配方按仓库/适用版本保存，题目引用差异；每项记录原问题、修改、前后运行及尚未解决内容。资产准备在远端直接联网完成，候选安装与测试维持既有非root/deny_all条件。构建不能带入目标库的新修复；公共开发资产与私有评分材料分开。

## 机器与协作

已有实例于本次开工确认空闲：没有运行作业或容器，空闲盘约365 GiB。连接凭据只留本地忽略目录。实验根为远端 `/work/env_recipe_repair_20260919/`，本地证据为 `runs/env_recipe_repair_20260919/`；旧 `/work/full216_20260919/` 不回写。

该机已证 metacopy=Y 时部分 commit 内容会损坏。构建仅在确认无活动评分时使用已验证的兼容条件，完成后恢复；必须确认派生内容正确才评分。此项是当前机器事实，不作为其它主机的通用开关。若 Claude 要共用机器，先按此记录协调构建与评分时段。

资源回收、P-A归因、parser/参考ID、gold/base修订归各自代码或语义工作，不在本批用配方绕过。Moto Docker/EC2服务需要更具体的方案，暂先整理依赖，不开放宿主Docker socket或改变网络边界。

## 进展

**2026-09-19 13:08 SGT，第一小批实施与真机自验完成：3 个派生镜像、6 次 fresh noop/gold，均为 0/1。** 这是下列具体问题的修复验证，不是三题整体环境验收；尚未做独立审查或改正式题包。

| 题目 | 实际改动 | 真实 RH2 结果与保留边界 |
| --- | --- | --- |
| Dask-10972 | 只预置 setuptools/wheel/packaging/versioneer/tomli wheel，保留当前构建要求和运行库，安装仍断网 | 两次 editable build/install 实际成功，安装 rc 从 1→0、约6秒；noop 两个 UTF-16 目标失败，gold 2/2通过；两侧150个P2P全通过。未验证任意新增构建依赖型候选。 |
| DVC-4778 | `pathspec 0.12.1→0.8.1`，满足该源码声明的 `>=0.6.0`；原源码/测试不变 | 最小复现确认旧DVC合并regex时重复引入命名组 `ps_d`；改依赖后合并成功。noop四个F2P从正则错误变为未按要求抛出 `DvcException`；gold4/4通过，原51个参考外失败消失，pytest为55 passed/4 skipped。**安装仍有缺requirements文件和离线build失败，未标环境整体完成。** 0.8.1是经验证的兼容选择，不声称是唯一历史版本。 |
| MONAI-1121 | 预置 torchvision 实际请求的 ResNet50 权重，`TORCH_HOME=/opt/rh2/torch`，候选UID可读 | 原8个下载失败P2P全部恢复，两侧35/35通过；noop目标TorchScript错误保持，gold目标通过、reward从0→1。参考外4个NumPy兼容失败及6个helper fixture错误仍在，因此gold测试命令仍rc1。 |

代码、参考集合、候选身份、网络与资源档位均保持原实验条件：2 CPU、4 GiB、shm 64 MiB、PID 512。6份日志逐份摘要核对、逐参考ID重解析与账本一致；Dask/DVC的参考状态未变，MONAI仅各8个P2P从FAILED变PASSED。峰值内存约0.33–2.62 GiB，宿主采样未见OOM或PID配额拒绝；这不替代评分器尚未持久化的完整终止事实。

基础镜像digest、派生image ID、配方与7个下载资产的sha256在 [recipe_manifest.json](recipe_manifest.json)；Dockerfile在 [recipes/](recipes/)。脚本位于 `rh2/experiments/env_recipe_repair_20260919/`，ruff通过；**不增加生产闸门或修改生产评分代码**。

本地 `runs/env_recipe_repair_20260919/analysis_6.json` 保存逐参考前后差异，`verification.json` 为回传核验；`remote/runs/` 为原始账本、日志和冻结工件。86个远端文件（约1.4 MiB）已回传并逐文件对上，196个原代码/输入文件未变。两项systemd作业已正常结束、无容器残留、metacopy恢复Y；实例保持运行。没有提交、推送或通知其它任务。

## 后续接入流水线

### 第二小批（继续执行）

**09-19 13:30运行结束、13:46完成本地核对：MONAI-3205公共数据缺失已修复。** 远端预置原测试要求的28.4 MB MSD Hippocampus归档，MD5与原源码一致；没有改源码、测试、参考集合或网络。两次fresh真实RH2中，noop从下载异常恢复为`get_dataset()`不接受`transform`的目标接口错误；gold唯一参考测试通过，reward 0→1。参考缺席0，安装rc0，gold测试rc0；日志摘要、重解析和原资源/身份条件均对上。原镜像层和代表源码/解释器内容保持，内核metacopy保持Y。

证据在本地`runs/env_recipe_repair_20260919/round2/`；[第二批资产清单](recipe_manifest_round2.json)记录镜像与下载身份。本批与Claude链路作业有时间重叠，因此不将约11秒的测试耗时归因为配方性能提升。下一组DVC/mypy/Moto安装与MONAI/Dask兼容修复已排队，尚未算通过。

### 接入要求

1. 本批留下“故障证据→配方变体→真实noop/gold→逐测试解释→剩余问题”的可复用例子，不另建一套评分器。继续修复离线安装，并按仓库版本归并已发现的依赖兼容问题；不能把一题通过直接扩成同仓全部适用。
2. Claude 的链路修复先处理进程回收、资源/安装事实和已确认P-A归因等问题；本批只复用了冻结旧快照。**合并后针对受影响代表题复验**，不能拿本批结果替新代码签收。DVC-2141/Modin的PID问题也不在此靠抬配额绕开。
3. Moto Docker/EC2、参考ID/base/gold修订仍按各自方案讨论；题面充分性、测试对合理解法的覆盖、依赖/构建修改型候选，仍是后续流水线工作。本批未改变二值reward、0/None归因、参考集合或deny_all。
