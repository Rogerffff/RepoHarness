# Moto6114：最终 CPU 结果

2026-09-29，`mixed-v1`。**正式noop=0、gold=1、wrong_first退化=1；退化按B实际ARN查询却返回数量1的A，确认S1对象身份覆盖缺口。** 原actor本已可开发；派生层恢复历史install_wave1离线构建资产，不是本夜已观测的actor故障修复。题主已核完整正式原件，[跨包独立复核](../../reviews/moto_pair_result_review.md)及最终卡窄对照已完成。历史partial保留；当前用于开发/配方和评分覆盖诊断，不授予无条件正确性比较或训练资格。

## 为什么原actor已通过仍构建派生层

原manifest为`cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a`，image ID `fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249`，base `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`。[原actor](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/actor_original) 的identity正常、按B实际ARN查询抛目标DBClusterNotFoundFault（预登记expect=nonzero）、旧4项回归通过，因此all_match_expect=true。这个字段既不表示目标BUG已修好，也不支持“原actor依赖坏了”的说法。

既定[recovery/buildplan](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/getmoto__moto-6114) 恢复旧install_wave1：COPY setuptools72.1.0、wheel0.43.0、packaging24.1三wheel到`/opt/rh2/build-wheels/`，设置PIP_NO_INDEX=1和PIP_FIND_LINKS；原正式make init不变。[实际Dockerfile和build日志](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/dependency_build) 没有RUN pip安装或改目标源码。它为正式构建准备离线资产，并让后续actor/private/grader沿同一派生条件；不能据此声称三包已经在actor前预装，或本夜原镜像正式安装一定会失败。没有原镜像正式评分的本轮对照来量化恢复收益。

派生image `aaf97ca9107336dc68a964386be07361bf363f3a4684998d3727d704c20cd5a0`保留原RootFS层前缀，只增COPY层和环境设置。三wheel精确文件名、大小和历史SHA在[wheel_manifest](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/getmoto__moto-6114/wheel_manifest.json)；下载和构建实际完成，调度代码先校验字节再build。同步原件未含wheel文件，本地未重算其hash，不把receipt当本地字节归档。下载容器rm后query成功且无残留。

## 两侧actor与私有身份反例

原/派生actor均CC2.1.205、UID54321、testbed Python3.12.4、boto3/botocore1.35.9、pytest8.3.2，源码从`/testbed/moto/__init__.py`导入。两侧使用相同3条公开命令，prelaunch/activation正常，开始/结束git status均0行，agent进程0。结果相同：identity rc0；ARN B查询DBClusterNotFoundFault rc1；public_existing 4 passed、31 deselected、21 datetime弃用warnings。31项因既定`-k`筛选未执行，不是skip，也不能算通过。两次actor容器、网络、relay、stub清理均确认无残留。

[私有root原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/private_behavior) 使用上述派生image，创建A、B两个真实mock集群，再查询B名称与创建时取得的实际ARN；只比Identifier/ARN，不比会变化的整对象。root行为不替actor权限。

| 变体 | 查询B实际ARN |
| --- | --- |
| base | DBClusterNotFoundFault，目标缺陷 |
| gold | 返回1个对象，Identifier=cpu-cluster-b、ARN=实际B ARN，通过 |
| wrong_first | 返回1个对象，Identifier=cpu-cluster-a、ARN=A ARN，身份断言失败 |

错误首对象反例不是数量错误，输出完整保留期望B与实际A。三变体各自命令独立执行，准备均完成；gold/退化先check再实际apply，完整`moto/rds/models.py` SHA分别为base `a614a137f21dce20445cad98611e578b435d4f09a592ced584d887d9edb9250c`、gold `00e61d1980f71fb4b0f37fa8e517a1fd3778c8ac5d687e4847d27217c5bc1c5b`、退化 `a5e0c305e9981b61209a2fc3bc4e2c40944fade972a4ff28b5ed0fc54b81815e`，与raw prep一致。私有三个容器rm/query均0、remaining为空。

## 正式安装、评分与实际导出

[三方完整原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1) 均在派生image实际执行原`make init`。日志明确`Looking in links: /opt/rh2/build-wheels`，两轮editable安装均完成build dependencies、editable metadata和wheel构建，最后Successfully installed；install rc0、failed_commands为空、未跳过。离线资产路径及成功构建有据，但非verbose日志未列出每个隔离build环境实际加载的全部包版本，不能反推三wheel都被逐个安装到actor testbed。

日志中的发行包元数据为`moto-4.1.0.dev0`，源码观测版本为`4.1.6.dev`，两种字符串如实保留，不称完全相同。实际导入路径仍为`/testbed/moto/__init__.py`，三次runner digest前后相同，目标源码冻结SHA另有完整核验；不靠包版本字符串替代源码身份。

| 正式项目 | noop | gold | wrong_first |
| --- | --- | --- | --- |
| F2P `test_describe_db_cluster_after_creation` | FAILED | PASSED | PASSED |
| 34 P2P | 全通过 | 全通过 | 全通过 |
| reward / test rc | 0 / 1 | 1 / 0 | 1 / 0 |
| 完整pytest | 1 failed, 34 passed | 35 passed | 35 passed |
| 安装 / 测试段秒数 | 10.014 / 7.503 | 9.928 / 7.026 | 9.445 / 7.126 |

正式完整运行`pytest -n0 -rA tests/test_rds/test_rds_clusters.py`，不同于公开actor只选择4项。从原test段逐一核来源1 F2P+34 P2P，共105个状态，无缺席、重复、skip、采集/导入故障或参考外失败；每组165个datetime弃用warnings。noop traceback确实在查询已创建第二个集群实际ARN时抛DBClusterNotFoundFault，0分是目标失败。gold/退化35项真实执行通过，test rc0且段完整。

candidate.patch均与输入逐字节一致。正式frozen_patch解码后的完整`moto/rds/models.py` SHA与前述私有apply后值一致：gold对输入拆出identifier；退化对任意arn前缀且存在集群时返回`next(iter(self.clusters.values()))`。两者仅投影此文件、mode100644、excluded_pathset_changed=false；noop entries为空。三份eval.log SHA与ledger匹配。这样正式满分候选与私有错误对象候选是同一实际源码，不是仅文件名相同。

每次candidate removed=true；原始grade log尾部与driver_close_checked一致，manager created=removed=1，containers_open/supply_open/cleanup_failures全空，最终exit0。真实安装、完整日志及两层清理均确认。

## 公开依据与数量断言缺口

[公开原题](../../../../../../../runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/user_prompt.txt) 明确期望按存在集群的ARN检索其数据；示例前后有`test-cluster-1`/`test-cluster-0`不一致。本次探针使用创建B时实际返回的ARN，避免把笔误当合法不存在输入。按B的ARN却返回A不符合“按ARN过滤查找集群”，无需要求整个可变响应字典相等。

[来源test.patch](../../../../../../../runs/swegym_quality_batch04_20260921_v1/private/getmoto__moto-6114/test.patch) 已创建两个集群并保留第二个的ARN，但新增断言只检查结果length_of(1)，没有核Identifier/ARN。wrong_first因此也通过该F2P和其余34个P2P。私有反例进一步核对同样两个实际对象，错误数量仍是1、对象明确是A；gold返回B。这是返回对象身份覆盖不足，不是parser遗漏、包安装故障或只靠gold规定的额外需求。

可供D6修订的最小方向是在现有两集群ARN断言后核同一目标Identifier/ARN；本批没有修改正式测试或评分。当前结论不扩张为跨账户/跨地区、Neptune、非法ARN或整对象字段一致性已经验证。

[root冻结parser重放](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/moto6114_final_v1.json) 与本卡逐参考读回一致；[远端/本地SHA对账](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_moto6114_v1.json) 确认106份、2,309,115 bytes原件无差异，二者均已完成。

## 资源、用途与剩余项

实际2 CPU / 4 GiB，setup/reset诊断上限900秒，test仍1800秒、whole1800秒。trusted_setup依次310.450、302.268、258.812秒；不能称旧300秒预算三方通过。ledger内存峰值969.551、940.684、943.078 MiB，resource_facts均null；峰值含准备，未证明测试独占需求或全程无OOM/PID拒绝。

[按真实评分report后缀匹配的资源采样](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_moto_pair_v1.json) 对noop/gold/退化分别有22/22/18个样本，采样内memory.events.max/oom/oom_kill及pids.events.max均0。约15秒间隔并非完整生命周期，保留ledger峰值与采样峰值差异，不用采样填补resource_facts=null或未知终止事实。

当前允许原/派生开发条件、恢复配方和评分覆盖诊断。原actor正常的事实保留；本轮没有原镜像正式评分对照，不宣称这次构建消除了已观测的原actor故障。D6未处理前不进入无条件正确性比较或训练奖励。剩余为D6新版本验证（若实施）；完整pip_check、wheel本地重hash及全生命周期资源事件未由本轮证明。正式题面/public_hints、自主模型、模型/GPU/预算/训练仍独立管理。

[最终机器结果与原件SHA](result.json) 保存105个逐参考状态、真实安装、实际导出及两层清理；[历史partial](result_partial.md)保持原快照。本轮只读本地证据，没有重跑或修改输入。
