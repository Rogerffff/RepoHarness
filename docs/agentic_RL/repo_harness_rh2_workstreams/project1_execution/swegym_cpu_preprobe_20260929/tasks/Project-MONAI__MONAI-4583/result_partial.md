# MONAI4583 actor/private 部分结果

2026-09-29。原镜像 actor 的 2D／稀疏3D 标签缺陷已准确复现；私有 gold 两维均修复，2D-only 退化仍在3D返回背景标签。正式结果未在本卡验收。

actor UID54321，Python3.8.20，NumPy1.24.4、Torch1.13.1+cu117、pytest8.3.3，CUDA不可用；解释器及MONAI/目标模块均指向testbed。2D与3D各有 NumPy／Torch CPU × 默认／显式dtype 四行：base boxes 均正确，但 labels 为[-1,-1]，应为实际前景标签[0,7]；类型、dtype和device全部正确，失败精准落在 PUBLIC_MASK_LABEL_OR_OUTPUT_CONTRACT_FAILED，rc1。公开原有矩形往返/box转换五项实际通过，无导入或collection失败。没有因2446历史问题安装NiBabel兼容层。

私有 base/gold/degenerate 的三条命令退出序列分别 [1,1,0]／[0,0,0]／[0,1,0]。gold的两维四组均输出[0,7]；2D-only退化仅2D正确、3D仍[-1,-1]，所有box、容器类型、dtype、device检查保持通过。三方旧五项都通过。此处验证的是实际盒子和标签值，不以返回数量替代标签检查；3D是公开API支持的形态，非从gold反推。正式退化能否得1仍需完整正式结果。

三组private均为独立root UID0容器，不能替代actor权限证明。base准备3步、gold/退化各6步均rc0，apply前后实际目标源码SHA与冻结输入的逐hunk重建结果匹配，见机器记录。actor全部命令和日志字节完整，清理container_rm/stub均0，网络/relay失败与残留列表为空；三私有容器rm/query均0、remaining为空。这里只确认各行为段清理，未代替正式grader验收。actor原镜像已可运行，未构建派生依赖层。2CPU/4GiB是本次配额，不是最低需求；未核全程资源事件。

证据：[机器记录](result_partial.json)；[原始运行目录](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-4583/reserve6-v1)；[公开依据和实验设计](plan.md)。正式仍以完整原件复核为准；D6未实施，不授予比较/训练/留出资格。

跨包独立复核已完成：[actor/private review](../../reviews/reserve6_monai_behavior_review.md)，与本卡对齐，非fresh盲审；不包含正式评分。
