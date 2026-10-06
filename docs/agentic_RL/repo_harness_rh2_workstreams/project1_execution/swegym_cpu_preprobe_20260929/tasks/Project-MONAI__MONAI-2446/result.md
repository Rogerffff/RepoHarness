# MONAI2446：完整 CPU 结果与用途

2026-09-29，`mixed-v1`。**NiBabel 开发条件修复有效；正式 noop=0、gold=1、数组列表不打乱退化=1。退化违背公开内部 shuffle 要求，却通过全部正式参考，确认 S1 评分覆盖缺口。** 本题 CPU 对照及跨包独立复核已完成；原评分未修订，不进入无条件正确性比较或训练奖励。历史 `result_partial.md/json` 保留，当前结论以本文件为入口；CPU 完成不代表正式题面交付、自主模型或训练资格。

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

三变体 shuffle=False 均保持列表、内部原序和 `[0,1]` 缓存。没有 import/collection 失败；3 个变体命令均完成，逐容器 rm/query 确认无残留。这里只跑一个公开行为命令的两种 shuffle 模式；没有把未跑的私有旧模块或其它 transform 组合补记为通过。退化违例来自公开 shuffle 需求；**其正式误奖现已由下述完整评分确认**。

## 正式评分、实际导出与独立验收

三次沿用 NiBabel 4.0.2 配方和原 `pytest -rA tests/test_smartcachedataset.py`，安装前后版本均为 4.0.2，原 `python setup.py develop` 完成、导入位置 `/testbed`。安装无失败命令，测试段/footer 完整，没有 import/collection 故障；runner digest 未变。noop 的 `test_datalist` 在比较调用者列表与 backup 时失败，属于目标缺陷。

| 正式参考/结果 | noop | gold | 数组列表不打乱退化 |
| --- | --- | --- | --- |
| F2P `test_datalist` | FAILED | PASSED | PASSED |
| P2P `test_shuffle` | PASSED | PASSED | PASSED |
| P2P `test_update_cache` | PASSED | PASSED | PASSED |
| reward | 0 | 1 | 1 |
| 完整模块 | 1 failed / 7 passed | 8 passed | 8 passed |
| 安装 / 测试段秒数 | 7.568 / 8.087 | 9.992 / 7.924 | 7.909 / 8.078 |

以上 nodeid 前缀均为 `tests/test_smartcachedataset.py::TestSmartCacheDataset::`。正式参考是 1+2，不是全部 8 个测试。三方 9 个逐参考状态已核，无缺失/跳过参考、段外解析或参考外失败；与 [冻结 parser 重放](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/monai2446_final_v1.json) 一致。

两份正式 candidate.patch 与输入逐字节相同；解码 frozen_patch 全量源码的 SHA 与前述实际应用后 SHA 一致，projection 仅含 `monai/data/dataset.py`、excluded_pathset_changed=false，noop 没有投影改动。三份完整 eval.log 的 SHA 与 ledger 均匹配。每次 candidate removed=true，manager created=removed=1、open/supply_open/cleanup_failures=[]，driver 正常退出，不能只看步骤 rc=0 判断成功。

[跨包独立复核](../../reviews/monai2446_result_review.md) 已确认原件、公开要求、实际冻结源码和三方评分。误奖原因是断言覆盖不足：新增 datalist 测试只看调用者列表；旧 shuffle 测试使用字典列表，数组分支特判没有破坏它。公开题面明确要求只在 SmartCacheDataset 内打乱；本反例仅验证原题五个 ndarray 列表、shuffle=True/default seed=0 下的内部和缓存顺序，不扩张到深复制或任意 transform。

## 资源与用途边界

三次正式配置均为 2 CPU / 4 GiB；本批诊断 setup/reset 上限900秒，未更改原测试预算，whole1800。trusted setup 依 noop/gold/退化为 374.779、524.216、461.583 秒；不能称为旧300秒条件通过。三次 ledger 峰值均4096 MiB、resource_facts=null。root 对 noop 的27个对应容器采样观察 memory.events.max=1650、oom/oom_kill/pids拒绝均未观察到；这表明触及限额并有回收压力，**4 GiB 峰值不等于 OOM，也不等于测试进程必需4 GiB**。采样不覆盖全程，不能外推 gold/退化全部事件。

root 的只读宿主快照显示当时准备中的 grader 正在 chown，内存主要是 file cache，支持 OverlayFS copy-up/文件缓存压力解释；其中5932容器的具体事件数不能记到2446。后续宿主资源汇总另按真实容器对齐，不将准备开销混为项目测试内存。

当前可用于环境修复和评分覆盖诊断。公开 `public_smartcache` 已有 base/gold/退化失败/通过/失败的最小验收证据，可作为后续 D6 修订草案；本轮没有改正式测试或评分，不能把草案视为已实施。剩余是 D6处置及新版本验证（若决定实施）、正式题面/public_hints真实交付、全环境依赖健康与wheel本地重hash缺证，以及另行管理的模型/GPU/预算/训练条件。已完成的CPU对照和独立复核不需要为这些不同问题机械重跑。

[机器结果与证据 SHA 索引](result.json) 保存正式逐参考状态、安装/测试/资源/清理和原件索引；历史 partial 保留原快照。
