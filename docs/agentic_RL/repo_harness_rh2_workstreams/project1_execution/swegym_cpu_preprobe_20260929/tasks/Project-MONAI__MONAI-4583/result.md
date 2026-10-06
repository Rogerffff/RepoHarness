# MONAI4583：最终 CPU 结果

2026-09-29。**原镜像可开发、目标缺陷可复现；正式 noop／gold／只修2D候选为0／1／1。** 退化在稀疏3D输入仍返回背景标签，正式参考未检出，确认 **S1／T2b 覆盖遗漏**。本次只完成 CPU 行为与评分诊断，未实施D6或授予训练资格。历史 `result_partial.md/json` 保留。

## 开发与私有行为

原镜像无需依赖修复或派生层。actor实际UID54321、Python3.8.20，Torch1.13.1+cu117、NumPy1.24.4、pytest8.3.3；导入来自testbed，CUDA不可用。公开2D和稀疏3D命令各覆盖NumPy／Torch CPU × 默认float32/int64／显式float64/int32。base八组盒子、类型、dtype与device正确，标签均为[-1,-1]，应为前景[0,7]；退出1精准落在标签契约断言。公开旧五项全部通过，无import或collection失败。

| 私有变体 | 2D四组标签 | 3D四组标签 | 原五项 |
| --- | --- | --- | --- |
| base | 错：[-1,-1] | 错：[-1,-1] | 5通过 |
| gold | 对：[0,7] | 对：[0,7] | 5通过 |
| 只修2D | 对：[0,7] | 错：[-1,-1] | 5通过 |

三组私有准备成功，实际apply后整文件SHA已捕获；私有UID0仅证明行为，不等同actor。actor及三私有容器、桩服务、网络/relay清理均已核；详见[保留的行为机器记录](result_partial.json)及[跨包行为复核](../../reviews/reserve6_monai_behavior_review.md)。

## 正式评分与完整性

三方实际执行冻结原安装串：清除requirements-dev的MONAI Git依赖行，安装types-pkg-resources0.1.3/pytest和requirements-dev，再执行 `python setup.py develop`。安装未跳过、失败命令为空、RC0，实际导入 `/testbed/monai/__init__.py`。随后完整执行 `pytest -rA tests/test_box_transform.py`，收集9项。

| 项目 | noop | gold | 只修2D |
| --- | --- | --- | --- |
| reward／test RC | 0／1 | 1／0 | 1／0 |
| 4 F2P | 全失败 | 全通过 | 全通过 |
| 5 P2P | 全通过 | 全通过 | 全通过 |
| 安装秒数 | 15.132 | 9.608 | 8.588 |
| 测试秒数 | 11.253 | 8.975 | 8.603 |
| trusted setup秒数 | 729.912 | 516.827 | 453.437 |

noop四个失败均为2D标签断言：单通道-1对0、双通道[-1,-1]对[0,1]；没有安装、导入、收集或parser故障冒充0。三方各22 warnings。逐参考27个状态完整、唯一，无缺失/跳过/段外状态；[audit](evidence_audit.json)保存完整键、实际日志SHA、安装/测试标记与退出。

noop冻结entries为空，未产生candidate.patch文件。gold／退化只投影 `monai/apps/detection/transforms/box_ops.py`（mode100644），未改测试。实际candidate.patch与输入逐字一致；解码整份frozen源码等于公开base纯文本应用对应patch，也与私有apply后SHA一致：gold17755字节 `ad4fd4db54ee21ce6d2da4e5e707a91f2e3b8e16ca269eaa03b72d3b1460539a`，退化17737字节 `ff73733407f3f1d096331da2c90b289a98fe68b7bd28293f1c4cb9754db700ac`，完整值见audit。gold同时修2D/3D取值，退化只改2D，3D仍按独立坐标最小值形成的包围盒角点取标签。

镜像沿原immutable manifest `79bf18ecd969a2e68a113b6d29b3d9e77ed977e37bd02666f17eef51930824d5`，base为 `9c4710199b80178ad11f7dd74925eee3ae921863`；原镜像别名检查绑定config ID `8305e1f5f6f13226ef30941433ed794fc294acc62fef85a28bc82131c6f6e0c4`，无派生层。正式ledger的image_id_actual为null，身份依据是manifest、别名记录与frozen runtime摘要，不能将缺字段补写为实测ID。三方runner digest前后相同；完整eval.log字节SHA与ledger一致。候选容器removed=true，原driver尾部与checked receipt一致，manager每次created=removed=1，open/supply/failures为空、final exit0，两层清理确认。

[root冻结parser](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/monai4583_final_v1.json)与直接逐键核对一致；[传输对账](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_monai4583_v1.json)确认99件、1,270,496字节远端/本地SHA无差异。[跨包正式原件复核](../../reviews/reserve6_monai4583_final_review.md)结论一致，最终卡窄对齐已完成，无新增阻断。

## 覆盖缺口与用途

[公开base API](../../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-4583/base/monai/apps/detection/transforms/box_ops.py)明确返回Nx4或Nx6盒子及对应前景分类标签，接受3/4维mask，并提供输出dtype参数。要求3D前景标签来自实际前景不是gold反推。原新增4 F2P只有2D稀疏mask；旧 `test_value_3d_mask` 从 `ellipse_mask=False` 的实心矩形生成mask，包围盒角点本来是前景，因此无法拒绝稀疏3D角点落在背景的实现。退化正式得1且实际3D标签错误，构成具体误奖，不是泛称“测试少”。

最小修订设计是保留2D并加入已运行的稀疏3D双通道[0,7]对照，核实际盒子、标签、类型、dtype/device；gold是该CPU范围内已验正对照。此为D6候选设计，未改正式参考，未声称覆盖任意输入或GPU。当前可用于开发环境、行为与奖励覆盖诊断；无条件模型正确性比较、训练奖励和留出准入均未获本批证明。若后续作受限比较，仍需统一、事先固定的语义验收及材料/预算/分母条件，原分不能单独判胜负。

三次正式2CPU/4GiB，诊断setup900、原test1800、whole3600；三方ledger peak均4096MiB，不能称无内存压力，也不等于OOM或测试进程必须4GiB。[root按真实report容器匹配的采样](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_monai_reserve_setup900_v1.json)覆盖noop／gold／退化50／36／32个样本，memory.events.max分别2976／2981／2934，采样未观察OOM、oom_kill或PID拒绝。该采样包含准备开销、间隔约15秒，resource_facts仍为null，不证明全生命周期零事件；准备开销和测试独占需求不能混算。完整pip check、自主模型、题面/public_hints真实交付、GPU及训练资格仍未验证。本地仅核同步原件，未重跑或操作远端。
