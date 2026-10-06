# MONAI6975 actor/private 部分结果

2026-09-29。原镜像 actor 已准确复现 Dataset 忽略Compose lazy策略；私有 gold 六行均正确，丢弃dict结果的退化只在Dataset+lazy=True返回原图。正式noop已因准备900秒超时停止，reward=null、安装/测试未开始；gold/退化未执行，不能给正式通过结论。

actor UID54321，解释器及MONAI/目标模块均指向testbed，NumPy1.24.4、Torch2.4.1+cu121、pytest8.3.3、NiBabel5.2.1，CUDA不可用。初始requirements-dev.txt已有删除MetricsReloaded git依赖的一行修改，已原样记录，不称干净base或本次修复。公开旧Compose/Dataset文件实际56项通过（不是照抄历史正式59个P2P数量）。

公开/私有矩阵使用真实MetaTensor图像及两次Flipd，direct／Dataset × lazy=True／False／None共六行。base全部图像值正确，但Dataset的True和None两行把两子变换强制为False，policy_ok=false；实际lazy.functional.resample调用数分别为0，direct对应为1，目标断言PUBLIC_DATASET_LAZY_OR_VALUE_FAILED，rc1。False控制正确。gold六行policy/value均正确，True／None均保留预期策略，返回双轴翻转图像，rc0。

退化实际执行lazy变换和重采样，却丢弃Dataset+dict+lazy=True的返回结果：该行返回[[[0,1,2,3],[4,5,6,7],[8,9,10,11]]]，而期望[[[11,10,9,8],[7,6,5,4],[3,2,1,0]]]；其policy_ok仍true、实际resample调用1。其它五行图像正确，整矩阵仅因此rc1。三方旧56项均通过。调用数只记录所wrap的真实函数，非全后端总重采样次数规范；不使用applied_operations长度作重采样代理。内存Flip实验不等于完整重放题面NIfTI/RandAffine所有情形。

三组private均为独立root UID0容器，不能替代actor权限证明。base准备3步、gold/退化各6步均rc0，apply前后实际目标源码SHA与冻结输入的逐hunk重建结果匹配，见机器记录。actor全部命令和日志字节完整，清理container_rm/stub均0，网络/relay失败与残留列表为空；三私有容器rm/query均0、remaining为空。这里只确认各行为段清理，未代替正式grader验收。actor原镜像已可运行，未构建派生依赖层。2CPU/4GiB是本次配额，不是最低需求；未核全程资源事件。

证据：[机器记录](result_partial.json)；[原始运行目录](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-6975/reserve6-v1)；[公开依据和实验设计](plan.md)。正式仍以完整原件复核为准；D6未实施，不授予比较/训练/留出资格。

跨包独立复核已完成：[actor/private review](../../reviews/reserve6_monai_behavior_review.md)，与本卡对齐，非fresh盲审；不包含正式评分。

05:35 SGT同步后的正式状态：本轮noop在control_surface_protect准备900秒超时，reward为null／infra_failure，安装和测试未开始；gold/退化未继续派发。两层清理已从ledger与原driver确认。外层“formal reference counts differ”是先检查空参考计数造成的误导性分类，不是参考实际失配。详见[失败复核](failure_review_setup900.md)。root拟在4583收口后新目录单独提高setup至1800秒复验，其余预算/镜像/材料/权限不变；尚未执行，不改写旧失败。
