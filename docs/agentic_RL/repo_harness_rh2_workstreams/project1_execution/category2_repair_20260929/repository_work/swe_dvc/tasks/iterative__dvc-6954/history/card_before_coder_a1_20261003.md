# DVC6954 当前题卡

2026-10-03。状态：**R14正式CPU三方0/1/0及两份非作者核查完成，普通基座诊断的CPU验收已固定，两模型探针已登记并通知GPU；尚无本轮模型结果。** 题面不变。精确父身份、补丁、参考、绑定与候选SHA见[revision.json](revision.json)，提交快照保持原件。

公开目标：合法Python负数参数可被读取，并由run/repro记录到lock；原测试只直接计分负整数-1。既有正数/容器支持和题面一般“negative numbers”提供负浮点/容器负值的依据。非法operand、算术表达式不扩题，不因历史诊断脚本坏引号追加防御式规范。

历史可复用：actor_v1固定pygit2 1.14.1/libgit2 1.7.2，24个参数功能用例和2个序列化用例通过；六次有效模型尝试的负int/float/nested、lock和改值重跑与gold一致，另一次是infra。见 [09-29复核](../../../../../swegym40_status_20260929/reviews/dvc_conan_dask.md)及 [原题卡](../../../../../swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch03/results/iterative__dvc-6954/card.md)。不混入无效尝试，不改变旧分。

本轮追加两个F2P：负浮点与容器值的完整解析；真实 `dvc.run`→lock负数值→不变跳过→改浮点后repro及lock更新。新值-7/-0.25/-3.5区别于原例-1。保留原13例的全部输入/断言，给参数case显式安全ID，并列出旧截断键到精确节点的13项映射；不改全局parser。

候选 `negative_int_only.patch` 只使原helper接受负整数。轻量stdlib函数切片已显示：noop丢失负整数，gold读出全部值，int-only能读-1但丢失负浮点/容器。**该检查不是DVC导入、pytest或评分，int-only原reward仍未知。**

[R14正式矩阵](formal_matrix_r14_v1.json)：noop得0（23通过／3失败），gold得1（26全过），int-only得0（24通过／2失败，仅新增两F失败）。每档26个实际节点／15个计分参考完整，12个P2P与11个非参考节点均通过；UID54322离线wheel预检及安装均成功，没有缺席、skip或infra充作负例。三份正式日志中的新增单测均严格解码为1624字节／56行，与effective patch逐字节相同，见[完整文件读回](actual_new_file_capture_r14_v1.json)。[非作者正式原件报告](../../reviews/non_author_formal6954_r14_runtime_review_20261003.md)已完整读取，无阻断；原版int-only正式成绩仍未知，不用新版成绩推断或改绑。

cpu-a 私有诊断见 [cpu_diagnostics_v1.json](cpu_diagnostics_v1.json)：原版13节点实际收集；noop仅负整数失败，gold与int-only全过。草案26节点中，noop三个F2P失败，gold全过，int-only仅新增解析和lock/repro两节点失败；12个P2P与11个非参考公开节点在三候选下均通过。六次清理成功。原v1诊断的便捷行提取漏记空白ID，本报告从完整pytest.log独立核全部原节点，不重写原证据、不据此改正式parser。

镜像准备的原config与7份wheel SHA吻合，基线源码工作区未改，`pip check=0`；实际DVC导入当前checkout，pygit2为1.14.1。新增 [有效安装配方草案](effective_install_recipe.json) 和 [公开开发说明](public_development.md)。这段镜像准备和私测属于历史诊断；当前正式材料、评分与验收见上述R14记录，公开actor另有完成记录。

[非作者CPU原件窄核](../../reviews/non_author_6954_9395_cpu_review_20261003.md) 已独立重建原版三行／当前三行的全部节点、13个旧截断绑定、退出与清理，无新增阻断。保留限制：新建单测是未跟踪文件，六份 `git diff --binary` 均未收入其字节；输入SHA、应用成功、真实collection和测试体支持运行，不能把diff当作完整新文件快照。R14正式原件已证明immutable base中不存在该路径、登记路径删除后trusted apply成功，并读回三份完整字节，关闭当前正式验收的缺口；旧诊断原件保持不变。

[本轮公开actor检查](public_actor_r5_v1.json) 已在R5真实CC/relay路径运行：四条公开命令均退出0，11个既有公开测试实际通过且无skip，首请求含逐字题面和开发说明，UID／解释器／pygit2身份及2CPU／4GiB／PID512一致，自有容器和网络清理。原件已SHA校验回收到本机，[非作者运行读回](../../reviews/non_author_actor6954_and_metadata_delta_review_20261003.md)已完成；不授予新版正式reward、探针或训练资格。冻结helper未解析-q摘要，11 passed由完整捕获读回确认。

[R5→R14公开actor适用范围独立核查](../../reviews/non_author_public_actor_r14_reuse_review_20261003.md)已完成：公开输入、固定镜像和公开执行路径一致；6954新prepared公开内容与solver prompt字符串字节也已核；prompts.jsonl的environment digest metadata变化，整文件并非相同。复用旧实际公开环境证据，不新增一次R14 actor运行或训练接入事实。

[CPU验收](cpu_acceptance_r14_v1.json)仅支持当前固定版本的普通基座诊断，未另存实际grader HostConfig，8GiB actor writable-layer配额未证明已强制生效；不授予训练资格。探针请求为 `swe-dvc6954-behavior-r14-v1-20261003`，见[固定输入](probe_request.json)和[实际发送回执](../../requests/dvc6954_probe_delivery_20261003_v1.json)。GPU自行核兼容消费者及实际GPU镜像后，两款模型BF16首轮各1次；随后题主继续分析完整轨迹、候选语义与评分一致性，提交不等于完成。
