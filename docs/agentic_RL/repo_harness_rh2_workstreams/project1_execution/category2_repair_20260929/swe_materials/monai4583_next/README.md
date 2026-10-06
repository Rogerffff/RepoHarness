# MONAI4583 下一切片：稀疏3D真实前景标签

2026-09-30。**第2类；材料已静态准备，未生产接线、未收集或运行新节点。** 原材料CPU29正式noop/gold/2D-only为0/1/1，已有公开3D行为显示2D-only仍返回背景标签。这一片把已明确的3D输出契约变成正常测试节点，候选新版为5F2P＋5P2P；不把本轮静态结果写成正式通过。

[提案及关键断言](proposal.md)先交root，root纠正了作者最初把新增节点称P2P的错误：它预期base失败/gold通过，必须是新增F2P。现 `proposal.extra_fail_to_pass` 只有一个普通节点 `tests/test_box_transform.py::TestBoxTransform::test_sparse_3d_mask_preserves_foreground_labels_cpu`，原4F2P和5P2P及顺序不改，新增P2P为空。**当前D6只支持追加P2P，不能直接消费本包；新增F2P扩展由root另行决定实施。** [消费者与成本](consumer_extension_plan.md)逐项列出接缝。

## 规范与关键断言

公开题面要求2D前景0返回标签0；公开[API](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/source/base/monai/apps/detection/transforms/box_ops.py)273–319行接受通道＋2D/3D mask，每通道代表一个框，返回其真实前景分类标签及Nx4/Nx6框。标签来自实际前景这一要求不限于矩形角点，也不限于2D。配对生成器196–237行公开支持ellipse/ellipsoid；本片没有添加多标签单通道、连通分量、插值或冲突解决规范。

新增普通unittest方法用两个int16通道、背景-1、前景0/7；每通道前景只在 `(0,1,0)`、`(1,0,1)`，因此框为 `[[0,0,0,2,2,2],[0,0,0,2,2,2]]`，标签为 `[0,7]`。各轴最小值拼成的 `(0,0,0)` 是背景；这是坐标集合和公开标签语义的推导，不是gold算法反推。[box_utils.py](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/source/base/monai/data/box_utils.py)40–45行固定右端点不包含最后像素（TO_REMOVE=0），故最大索引1＋1＝2。新测试不检查gold的内部取值路径。

四组沿已经执行的CPU29矩阵：NumPy/Torch CPU×默认float32/int64、显式float64/int32，核精确框/标签值、类型、dtype和CPU设备。[convert_to_dst_type](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/source/base/monai/utils/type_conversion.py)294–336行公开按输入类型和device转换并接受显式dtype；本片不引入新设备规范。新增方法明确用 `torch.from_numpy`，不依赖CUDA。原测试 `TEST_NDARRAYS` 的CUDA条件完全保留；正式10引用的CPU范围需实际确认CUDA不可用，不把GPU作为新门槛。

CPU29原[3D输出](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/history/degenerate_mask_3d_cpu29.out)已证明四组盒子、类型、dtype/device正确，但base与2D-only标签均[-1,-1]，gold为[0,7]。因此新node预期在标签断言失败，不应因错误坐标、dtype、导入或收集失败制造0。新方法使用 `subTest` 保留四组上下文；普通node的真实collection及各组目标失败位置仍待CPU核定。

## 材料与静态核定

完整逐文件SHA/字节和来源行见 [materials_manifest.json](materials_manifest.json)。主要候选为：

- [original_test.patch](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/original_test.patch)：来源grading的原字节副本。
- [extra_tests.patch](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/extra_tests.patch)：只供已应用原test_patch的base追加审查。
- [effective_test.patch](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/effective_test.patch)：直接应用immutable base的完整有效候选。
- [references_candidate.json](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/references_candidate.json)：原4F2P/5P2P与新增1F2P分别保存，有效5F2P/5P2P。
- [gold](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/controls/gold.patch)、[2D-only](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/controls/degenerate_2d_only.patch)、[noop](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/controls/noop.patch)：原对照精确冻结；gold等于来源validation字节。
- [static_checks.json](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/static_checks.json)、[精确apply命令](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/patch_commands.json)：只做标准库AST及隔离git apply；未导入MONAI/NumPy/Torch，也未运行项目或测试。

base commit `9c4710199b80178ad11f7dd74925eee3ae921863`，tree `43bb8d82537f723fa907dca32e8edb9cb538b7a9`；原四面来源均为s2/ingest第13行。原grading digest `sha256:56f52f4bebe7bd2db4c31cf46976e3267c0bd1ec019b63bf85f9a5489a5d2f36`、public digest `sha256:c1d76edfb73f1a0a2a1c91765952b43f5d1f82b964ab4851eccea17c3494e164`。base源码SHA `a439e2cf0de7ac19d715e0fefb5224e96e933d7001b4e554f4fbc5f6090c4f5c`；原base测试SHA `f9e0cf78b5117f34d7151f859fce8e1700633d1f39fbba8fb89aadfdb0f88cfe`。

本轮5次 `git apply --check`及隔离应用退出0，结果全文确认原补丁＋新增补丁等于完整有效补丁；删除新增唯一普通方法后AST与原patched测试完全相同。gold应用后SHA `ad4fd4db54ee21ce6d2da4e5e707a91f2e3b8e16ca269eaa03b72d3b1460539a`、2D-only `ff73733407f3f1d096331da2c90b289a98fe68b7bd28293f1c4cb9754db700ac`，均与CPU29实测原件一致；有效测试文件SHA `4e2d30a66dd9903b0011b4664f6c85e2a6226f2b43d6d49dd2b3aec9e2e8d9b9`。这些只证明静态构造和字节，不证明新测试通过。

首次生成在gold应用SHA断言失败：仓库子目录的git自动发现父Git，使带 `diff --git` 的补丁退出0但未作用。首次产物与失败记录保留在材料目录 `_failed_build_v1/`，不属于有效候选或消费清单。修正为以 `GIT_CEILING_DIRECTORIES` 隔离父Git后重新静态应用，且额外确认原F2P方法实际出现；没有以退出0掩盖失败。完整成功构造命令为 `python -B runs/category2_repair_20260929/swe_materials/monai4583_next/build_materials.py`；构造器拒绝覆盖已有冻结源树。

## 环境复用、缺件与最小计划

[环境复用记录](../../../../../../../runs/category2_repair_20260929/swe_materials/monai4583_next/environment_reuse.json)指定固定恢复来源 `xingyaoww/sweb.eval.x86_64.project-monai_s_monai-4583@sha256:79bf18ecd969a2e68a113b6d29b3d9e77ed977e37bd02666f17eef51930824d5`，CPU29历史config ID为 `sha256:8305e1f5f6f13226ef30941433ed794fc294acc62fef85a28bc82131c6f6e0c4`。本包只有历史inspect元数据，无可执行镜像层/daemon状态、完整冷安装锁或wheel缓存；新机须实际inspect核固定digest/ID后恢复，不能把历史ID回填成新实测。无需新增数据、权重或测试依赖，原vendor安装和原命令 `pytest -rA tests/test_box_transform.py` 保持。

旧CPU29原镜像公开开发可用，原三行安装完整RC0：过滤requirements-dev中的MONAI Git行，pip安装types-pkg-resources0.1.3/pytest和requirements-dev，再 `python setup.py develop`。这只是既有正式消费证据，不授权从日志拼安装替代脚本或更换依赖pin。原三次trusted setup约730/517/454秒、测试约11/9/9秒；诊断setup900、test1800、whole3600，2CPU/4GiB。峰值4GiB包含准备/cache copy-up；历史resource_facts=null且约15秒采样未观察OOM，不能称无内存压力或零事件。固定镜像不可用、安装/导入/旧测试异常时停，环境恢复来源固定，不猜版本补件。

| 待验候选 | 原4F2P | 新1F2P | 原5P2P | 预期reward/testRC |
| --- | --- | --- | --- | --- |
| noop | 失败 | 标签[-1,-1]失败 | 通过 | 0/1 |
| gold | 通过 | 四组真实标签[0,7]通过 | 通过 | 1/0 |
| 2D-only | 通过 | 标签[-1,-1]失败 | 通过 | 0/1 |

以上全为待验预期。新producer/资格必须新建；旧prepared、私有root行为和原0/1/1不能当新正式验收。之后最少三次单路正式CPU评分，核真实10节点、原/新增F2P分区、所有安装子命令、完整退出/原日志、源码和测试root保护、ledger及manager双层清理；真实公开开发只见原题/公开源码与已有测试，再同次原actor完整baseline原件直评，最后独立复核。材料阶段没有实施这些运行，也没有转类或训练资格结论。
