# DVC6954 当前题卡

2026-10-03。状态：**草案私有CPU诊断及非作者材料／原日志窄核已完成；正式评分、actor交付和模型探针未完成**。题面不变。精确父身份、补丁、参考、绑定与候选SHA见 [revision.json](revision.json)。

公开目标：合法Python负数参数可被读取，并由run/repro记录到lock；原测试只直接计分负整数-1。既有正数/容器支持和题面一般“negative numbers”提供负浮点/容器负值的依据。非法operand、算术表达式不扩题，不因历史诊断脚本坏引号追加防御式规范。

历史可复用：actor_v1固定pygit2 1.14.1/libgit2 1.7.2，24个参数功能用例和2个序列化用例通过；六次有效模型尝试的负int/float/nested、lock和改值重跑与gold一致，另一次是infra。见 [09-29复核](../../../../../swegym40_status_20260929/reviews/dvc_conan_dask.md)及 [原题卡](../../../../../swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch03/results/iterative__dvc-6954/card.md)。不混入无效尝试，不改变旧分。

本轮追加两个F2P：负浮点与容器值的完整解析；真实 `dvc.run`→lock负数值→不变跳过→改浮点后repro及lock更新。新值-7/-0.25/-3.5区别于原例-1。保留原13例的全部输入/断言，给参数case显式安全ID，并列出旧截断键到精确节点的13项映射；不改全局parser。

候选 `negative_int_only.patch` 只使原helper接受负整数。轻量stdlib函数切片已显示：noop丢失负整数，gold读出全部值，int-only能读-1但丢失负浮点/容器。**该检查不是DVC导入、pytest或评分，int-only原reward仍未知。**

初始正式矩阵预期0/1/0；先核collection、绑定、pygit2实际来源和功能文件选择，再做原版int-only及修订版三方评分。基线不存在新增单测文件，恢复/保护要处理不存在状态。新功能文件 `tests/func/params/test_show.py` 必须实际进入评分选择器。已有正确模型工件可按接受性需要复用，不扩大非法表达式范围。

cpu-a 私有诊断见 [cpu_diagnostics_v1.json](cpu_diagnostics_v1.json)：原版13节点实际收集；noop仅负整数失败，gold与int-only全过。草案26节点中，noop三个F2P失败，gold全过，int-only仅新增解析和lock/repro两节点失败；12个P2P与11个非参考公开节点在三候选下均通过。六次清理成功。原v1诊断的便捷行提取漏记空白ID，本报告从完整pytest.log独立核全部原节点，不重写原证据、不据此改正式parser。

镜像准备的原config与7份wheel SHA吻合，基线源码工作区未改，`pip check=0`；实际DVC导入当前checkout，pygit2为1.14.1。新增 [有效安装配方草案](effective_install_recipe.json) 和 [公开开发说明](public_development.md)。当前结果仍是私有诊断；正式材料登记、资格和actor交付待完成。

[非作者CPU原件窄核](../../reviews/non_author_6954_9395_cpu_review_20261003.md) 已独立重建原版三行／当前三行的全部节点、13个旧截断绑定、退出与清理，无新增阻断。保留限制：新建单测是未跟踪文件，六份 `git diff --binary` 均未收入其字节；输入SHA、应用成功、真实collection和测试体支持运行，不能把diff当作完整新文件快照。正式消费者须核不存在状态的恢复／保护及新文件实际字节，不为补这份诊断快照机械重跑旧矩阵。

[本轮公开actor检查](public_actor_r5_v1.json) 已在R5真实CC/relay路径运行：四条公开命令均退出0，11个既有公开测试实际通过且无skip，首请求含逐字题面和开发说明，UID／解释器／pygit2身份及2CPU／4GiB／PID512一致，自有容器和网络清理。原件已SHA校验回收到本机，运行事实的非作者读回待完成；不授予新版正式reward、探针或训练资格。冻结helper未解析-q摘要，11 passed由完整捕获读回确认。
