# Moto6114：公开开发、配方恢复与私有行为结果

2026-09-29，`mixed-v1`。**原actor已经满足本轮开发命令预期；派生层恢复历史install_wave1离线构建资产，并非本夜观测到原actor损坏后的修复。私有gold按B的ARN返回B；退化返回数量同为1的A，身份错误。** 正式三方尚未齐，不在此卡判最终评分或用途。

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

后续接续正式35项参考、真实安装是否使用离线资产、完整日志/实际投影/两层清理，再做独立复核和最终用途判断。完整pip_check、全程资源事件、正式题面/public_hints交付、自主模型及模型/GPU/预算/训练未由此卡证明。[机器记录与原件SHA](result_partial.json) 保留本次范围；没有重跑或改在途输入。
