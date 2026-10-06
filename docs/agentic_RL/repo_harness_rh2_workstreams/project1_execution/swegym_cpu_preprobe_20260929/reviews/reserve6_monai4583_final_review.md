# MONAI4583：正式三方独立结果复核

2026-09-29。**正式 noop=0、gold=1、2D-only退化=1；退化实际遗漏公开3D前景标签行为，确认S1误奖。** 本稿先读原始安装、完整测试、候选导出和清理，再对照题主最终卡；这是跨包独立复核，复用此前[actor/private审查](reserve6_monai_behavior_review.md)，不是新盲审。不运行项目、容器或远端，不修改题面/测试/生产。

原件根：[reserve6-v1](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-4583/reserve6-v1)。三方已结束，status为executed_pending_review；该状态只是运行收口，不能替代题目验收。

## 正式测试与已证公开缺陷

三方实际命令都是 `pytest -rA tests/test_box_transform.py`，完整收集9项。原4个F2P全为新增2D稀疏mask；原5个P2P包含3D，但其mask往返使用 `ellipse_mask=False` 的实心矩形，包围盒角点本来就是前景，不会拒绝这次3D角点取背景的缺陷。

下表ID统一前缀为 `tests/test_box_transform.py::TestBoxTransform::`，每个原参考在每份日志恰出现一次；没有缺席、跳过、额外测试或参考外失败。

| 参考ID后缀 | 分组 | noop | gold | 2D-only |
| --- | --- | --- | --- | --- |
| test_value_2d_mask_0 | F2P | FAILED | PASSED | PASSED |
| test_value_2d_mask_1 | F2P | FAILED | PASSED | PASSED |
| test_value_2d_mask_2 | F2P | FAILED | PASSED | PASSED |
| test_value_2d_mask_3 | F2P | FAILED | PASSED | PASSED |
| test_value_2d_0 | P2P | PASSED | PASSED | PASSED |
| test_value_2d_1 | P2P | PASSED | PASSED | PASSED |
| test_value_3d_0 | P2P | PASSED | PASSED | PASSED |
| test_value_3d_1 | P2P | PASSED | PASSED | PASSED |
| test_value_3d_mask | P2P | PASSED | PASSED | PASSED |

noop准确在四个2D新增参数的标签断言失败，实际-1对期望0，双通道为[-1,-1]对[0,1]，不是安装/导入/收集失败。完整结果为4 failed/5 passed/22 warnings，testRC1；gold与退化均9 passed/22 warnings，testRC0。三方report分别0/1/1、F2P0/4/4、P2P均5/5，与原件逐键及[root冻结parser](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/monai4583_final_v1.json)一致。

此前实际私有八组合已证明：2D-only在NumPy/Torch CPU、默认和显式dtype的3D稀疏mask中都把应有[0,7]取为[-1,-1]；boxes、类型、dtype/device均正确。gold两维均正确，退化只2D正确。3D支持、前景标签含义及dtype来自[公开base API](../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-4583/base/monai/apps/detection/transforms/box_ops.py)，不从gold推导新增要求。故缺陷与正式误奖均有证据，不能将“正式1”解释为完整修复。

## 实际源码、镜像与安装

noop冻结entries为空（没有candidate.patch文件，不能写成实际导出了空patch文件）。gold/退化各只有 `monai/apps/detection/transforms/box_ops.py`，mode100644，excluded_pathset_changed=false；实际candidate.patch与输入逐字一致。解码完整frozen文件后，逐字等于公开base应用对应补丁，且SHA与此前私有apply后实际捕获一致：

- gold：17755字节，`ad4fd4db54ee21ce6d2da4e5e707a91f2e3b8e16ca269eaa03b72d3b1460539a`。
- 2D-only：17737字节，`ff73733407f3f1d096331da2c90b289a98fe68b7bd28293f1c4cb9754db700ac`；仅替换2D取标签表达式，保留原3D表达式。没有改测试或环境文件。

三方materialized_head均为 `9c4710199b80178ad11f7dd74925eee3ae921863`，runtime image digest为原manifest `79bf18ecd969a2e68a113b6d29b3d9e77ed977e37bd02666f17eef51930824d5`。original_alias记录immutable来源与config ID `8305e1f5f6f13226ef30941433ed794fc294acc62fef85a28bc82131c6f6e0c4` 的同镜像本地tag别名；没有派生层。正式ledger的image_id_actual是null，不能冒称这个字段记录了grader config ID；原manifest身份、别名核对及frozen runtime摘要提供本轮镜像绑定。实际安装后从 `/testbed/monai/__init__.py` 导入，Python3.8.20，Torch1.13.1+cu117/NumPy1.24.4/pytest8.3.3。

三方均实际执行原安装串：清除requirements-dev中MONAI Git依赖行、安装types-pkg-resources0.1.3/pytest、安装requirements-dev，然后 `python setup.py develop`。输出确认Installed /testbed，未跳过候选安装；每个安装失败记录为空，最终RC0，完整安装/测试起止标记齐全。无新增环境修复或替换配方。setup.py给出 `.dirty` 版本不等于候选扩散修改；受保护测试资产和实际安装阶段状态需与actor初态区分。三方runner digest前后均为 `1cfac6828a8ce1101528108a0a3379da1fe8e2b0ba4a9021ea32c5ffc26e13a4`。

| 项目（秒） | noop | gold | 2D-only |
| --- | --- | --- | --- |
| 实际安装 | 15.132 | 9.608 | 8.588 |
| 完整test段 | 11.253 | 8.975 | 8.603 |
| trusted setup | 729.912481 | 516.826642 | 453.437106 |

## 完整性、清理与用途边界

三份完整eval.log本地SHA与ledger一致：noop `d31c77b2a0806c03a6122e81cbe9ae215648cb98a58f854d4777e81e32660653`；gold `d107a88a970d3b75921932e3c3f6efd16e31a7113edfbcd1c7982ed0f8a36d58`；退化 `1b2324ce365c1fc120224111fcebef1ef3021b07515ee13a5b55f1584948eae0`。log_partial=false、apply_ok=true、candidate段exec0，测试进程RC与上述结果一致。

三个candidate容器removed=true；原driver终行与driver_close_checked一致，manager created=removed=1，containers_open/supply_open/cleanup_failures为空，final exit0、grader_containers_open为空、cleanup_failures_total=0。先前actor及三私有容器也已独立核清理，不能仅以manager状态代替它们。

本轮2CPU/4GiB、setup900、原测试预算/whole3600；三方记录memory peak=4096MiB，已触及内存上限，不能称为无内存压力。[root容器采样](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_monai_reserve_setup900_v1.json)分别覆盖noop/gold/退化50/36/32个样本，memory.events.max为2976/2981/2934，表明存在限额与回收压力；采样未观察OOM、oom_kill或PID拒绝。约15秒采样包含准备开销，ledger resource_facts仍为null，不支持全生命周期零事件或测试独占内存需求结论。[root传输对账](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_monai4583_v1.json)确认99件、1,270,496字节远端/本地SHA一致。这里只验证CPU确定性行为与评分覆盖，不授予模型比较、训练或留出资格。

已存在可运行的最小补充验收是公开输入中的 `mask_3d`（并保留 `mask_2d`）：核前景标签、boxes与已有类型/dtype/device契约；该脚本已被actor与私有三方实际执行，可供D6版本化参考修订复用。正式测试尚未修订，不能用私有后检把原正式奖励当成可靠训练信号。

2026-09-29最终卡窄对齐已完成：[result.md](../tasks/Project-MONAI__MONAI-4583/result.md)、[result.json](../tasks/Project-MONAI__MONAI-4583/result.json)及[evidence_audit.json](../tasks/Project-MONAI__MONAI-4583/evidence_audit.json)与上述已验原件一致，无新增阻断。正式0/1/1、27个逐参考状态、完整安装/测试退出、实际候选整字节与私有身份、两层清理和资源边界均对齐，支持S1/T2b覆盖遗漏分类；题主可核销最终卡独立复核待回执。卡中保留D6未实施、CPU验证不等于模型比较或训练资格、image_id_actual及resource_facts缺失边界。本次仅复用已有独立原件审查核对最终卡，仍为跨包非fresh复核，未重跑实验或补造条件。
