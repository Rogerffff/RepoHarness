# MONAI2446：公开开发与私有行为阶段结果

2026-09-29，`mixed-v1`。**源镜像恢复、NiBabel 4.0.2 重建、两轮真实 actor 与私有三变体已完成。NiBabel 兼容性修复有效；SmartCache 本身的列表修改缺陷仍准确复现。** 此为题主读回，独立复核未做。审查快照中正式 `grade_noop` 已启动但尚无终态 ledger；gold/退化正式结果均未知，不据历史结果填值。

## 实际环境恢复

源 manifest `cca2571758f276aa5d82fcb372b523e2201cd10be150776badceaaa04defad6a` 与 public latest pull 一致，config ID 为 `7f21570d…`。远端从 PyPI 下载 `nibabel-4.0.2-py3-none-any.whl`（3,345,004 bytes；历史 SHA256 `c4fe76348aa865f8300beaaf2a69d31624964c861853ef80c06e33d5f244413c`）。调度代码先校验完整文件名/大小/hash 再构建；已同步原件没有 wheel 字节，因此本次没有独立本地重算 wheel hash，也不宣称具备归档逐文件下载直链。

[构建日志](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-2446/mixed-v1/build_dependencies.log) 明确卸载 5.2.1、向原 testbed 解释器安装 4.0.2。派生 image ID `e463edf9eddf29d59db779a0ecc3d2ab009f8f63885dc26425c938d4059b6220` 保留全部 base layers，只加 wheel COPY 和预装层；[镜像与 Dockerfile 原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-2446/mixed-v1/dependency_build) 可追溯。这一 actor 预装层有别于旧 compat 的 COPY-only 层，不能称为旧派生镜像字节复原。下载容器已 `--rm`，补充 rm 提示不存在，随后 query rc=0/remaining=[]，是清理完成证据。

## 真实 actor：失败位置和修复效果

两轮均为 CC 2.1.205、uid 54321、Python 3.8.20，`/opt/miniconda3/envs/testbed/bin/python`，从 `/testbed/monai/__init__.py` 导入；base 为 `05b2da61d70324c2f02b5d72429ddb7cc171b9b9`。numpy 1.24.4、torch 1.13.1、parameterized 0.9.0、pytest 8.3.3 均实际可用，源码与 `/tmp` 可写。两轮各 4 个 Bash 调用完整，prelaunch/activation 正常，结束 git status 无改动，容器/网络/relay/stub 清理无残留。

| 公开命令 | 原镜像 | NiBabel 4.0.2 镜像 | 解释 |
| --- | --- | --- | --- |
| identity | 0 | 0 | 实际身份、激活、import 和版本确认；不是单独合格凭证 |
| nibabel | 1，打印 5.2.1 | 0，打印 4.0.2 | 原失败是版本断言，不是导入失败 |
| public_smartcache | 1 | 1 | 两轮均输出完整结构化结果后在输入保持断言失败，目标 bug 未被环境修复掩盖 |
| public_existing | 5 failed / 2 passed | 7 passed | 原 `test_shape_0` 至 `_4` 在 Nifti1Image 构造处因 int64 数据被 NiBabel 5.2.1 拒绝；降至 4.0.2 后变为 warning，7 项完成，无 collection/import failure |

原与修订 [actor 原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-2446/mixed-v1) 中 `public_smartcache` 的 shuffle=True 都把调用者 `[0,1,2,3,4]` 变成 `[2,0,1,3,4]`；内部顺序和前两项缓存正确。shuffle=False 三项均正确。故目标失败是调用者列表被修改，不是随机数、缓存、缺包或采集故障。实际消息仍是 Devcheck 控制文本，正式题面/public_hints 交付及自主模型推理未由本批证明；桩使用量不是模型费用证据。全环境 pip_check 未执行，不宣称整个依赖集合健康。

## 私有行为：正确修复与退化可区分

使用同一派生镜像，但运行身份是 root，**只证明行为，不替代 actor 权限或真实开发证明**。每个变体先核 base 源码 SHA；gold/退化随后 `git apply --check`、实际 apply、再核目标文件 SHA，全部成功。base/gold/退化的 `monai/data/dataset.py` SHA 分别为 `22f52cd4…` / `f29bf46a…` / `1653727e…`，完整值及准备步骤见 [私有 summary](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-2446/mixed-v1/private_behavior/summary.json) 与机器记录。

| 变体 | shuffle=True 调用者列表保持 | 内部 shuffle | 缓存 | 退出码 |
| --- | --- | --- | --- | --- |
| base | 否 | 正确 `[2,0,1,3,4]` | 正确 `[2,0]` | 1，目标断言 |
| gold | 是 | 正确 `[2,0,1,3,4]` | 正确 `[2,0]` | 0 |
| 数组列表不打乱退化 | 是 | 错误 `[0,1,2,3,4]` | 错误 `[0,1]` | 1，目标断言 |

三变体 shuffle=False 均保持列表、内部原序和 `[0,1]` 缓存。没有 import/collection 失败；3 个变体命令均完成，逐容器 rm/query 确认无残留。这里只跑一个公开行为命令的两种 shuffle 模式；没有把未跑的私有旧模块或其它 transform 组合补记为通过。退化违例来自公开 shuffle 需求；**其是否被正式评分漏判仍未知**。

## 当前用途和剩余项

当前支持“NiBabel 4.0.2 下的公开开发条件已复验、目标行为可观察且 gold/退化行为可区分”。尚不支持正式评分覆盖或模型/训练准入。下一步由在途队列完成 noop/gold/退化正式导出、安装、测试、逐参考判分和清理；随后核冻结 parser、资源与独立审查。正式题面交付、全依赖边界，以及另行管理的模型/GPU/预算/训练条件仍保留。本轮没有改题目源码、正式测试、评分或在途脚本，也没有重启或等待远端任务。

[机器记录与原件 SHA 索引](result_partial.json) 保存此次快照和全部已核输出；正式在途状态不纳入已完成结论。
