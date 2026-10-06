# Conan15422：Qwen3.6 首次探针分析

2026-10-03。请求 `swe-conan15422-r12-briefv1-20261003-v1`，作业 `gpu1003-conan15422-qwen36-a1`；实际code8／R12，材料v2、`probe-wide-v1`，本模型仅一次。

**raw1，5F／40P全部45完整参考通过；原日志另三平台skip均非参考。生产无条件使用公开build_jobs，默认值与显式配置都保持，区别于Coder首臂的默认遗漏raw0。** 候选及材料判断与模型自测质量分别记录，不把新公开测试或退出0当独立评分依据。当前为题主分析，独审核收及ACK见处置与配对页。

## 原件与评分范围

[固定请求](probe_request_20261003_r12_v1.json) SHA `c7062edcbdb67ecaa7085099394865578407e83fb8be279969e0d5534ba7da09`未改。权威快照 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/`，题主逐件核178件／18,631,732字节SHA／大小一致。完整候选3,165字节、SHA `9ab2e85632b10b03923efa531995133756e419258eadcb41d39ade627a60a506`，两项modify：生产`presets.py`和受保护公开`test_cmaketoolchain.py`。从实际baseline／公开base应用完整diff，两项Frozen内容逐字节相同；正式projection**仅生产**，官方测试修改被剔除。新公开例未进入45参考，旧测试无删除或弱化；不能按“改了测试”自动判候选0，也不能用投影后hygiene抹去完整候选的改测事实。

FP canonical digest `7c2ecd3456098c228d9b82189252fbb0d3f5187f944c8aa1f69b7b18669ef31c`，baseline canonical digest `c041d7fad2f908302f448cbda2ab81b95557b0018b7efe5cdea4b87d51ca50af`。安装0／测试0；原log完整`45 passed, 3 skipped`与逐key一致，eval SHA `deedb927b5f3a652183ffe9fed169bcda16ec37e2529b32542c0788592749c51`。45参考全P，三个非参考skip按可信源码AST与原行号分别定位，不伪造完整skip node日志。diagnostics parsed_tests46另是parser口径，不能替换45完整参考分母。

actor／grader实际固定config ID `a27936515e625ace25f5d76dcef25566079c7ac355b51bdfc5c3408c26a07ead`；首gateway请求含完整issue＋brief，prompt SHA `475fff849ec5f2d04441bcfd4a9b0de9bd5f707a6888c63df36293cc77e6fc92`，brief SHA `7d82590d898dda57d0b281eb07e12e154f2f4e66dcb88f026dc3d1d576b47054`。保留原issue CRLF，只剥brief首尾空白中的末尾换行。

[新臂机械回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-conan15422-qwen36-a1_execution_receipt_v1/execution_receipt.json)和[双模型回执](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-conan15422-r12-briefv1-20261003-v1_pair_execution_receipt_v1.json)（SHA `b7f007238f09e0db190b10e6d908a799cc85d090b30f4b8300c9ca400c1983aa`）只证明所列执行范围；两臂完成不等于两臂都成功。本轮私有SHA／工具全文在 `runs/category2_repair_20260929/conan_cpu_20261003/probe_analysis_15422_qwen36_a1_20261003_v1/`；下列行号为原trajectory一基行。

## 七个维度

### 方法

行215／229两次生产Edit：导入公开`build_jobs`，在`_build_preset_fields()`由原common字段构造后设置`ret['jobs']=build_jobs(conanfile)`。复用既有conf整数检查及cgroup／CPU默认逻辑，不引入“仅显式配置”guard，不硬编码16或宿主CPU数；保留single／multi字段、append／replace和schema版本。默认实际生成2是本次actor观察，不能规定所有主机默认必须2。

正式默认节点同进程与helper比对，显式2／7节点真实CMake3.23.5 configure／build，Multi-Config append／replace节点核两配置及替换。生产修法与本题需求一致，测试不能误把默认空配置判“不应有jobs”。原Coder自测错误驱动guard遗漏该字段，可信KeyError有效；本臂不会借另一模型成功核销Coder失败。

### 定位

首响应两个工具核导入与实际CMake3.23.5。工具4读对生产preset，首次源码读取距第一模型请求 **2.684秒**；工具7完整读`build_jobs`及CPU/cgroup回退。行193定位build preset字段，行211明确使用build_jobs后编辑；第14模型响应完成上界 **14.411秒**，是实现判断完成时间，不是首次生成时刻。私有audit的诊断行193为初步索引，最终采用更明确的211并在JSON注明修正，不回写原audit。

读错不存在的functional路径一次；随后integration片段和正确functional文件用于找测试。改前未实际生成失败JSON，定位依据为公开issue与当前源码；改后有真实Conan install生成证据，不倒写成前后复现。

### 工具与纠错

46工具为**Bash29、Read13、Edit4**：生产Edit2，新增公开测试与修正Edit2。显式错误122是不存在文件；537是新增测试第三次install未带jobs16却错误期待16，实际回到默认2。模型补上第三次命令的显式配置，重新通过；未把正确生产默认改坏，旧测试保持。新增例generator写成`Multi-Config`仅生成配置，没有验证该名称能被真实CMake使用；可信Multi-Config节点另核实际范围。

行639广测61P／20skip／8setupError，tail没有保留各错误完整原因，也掩盖pytest退出；行649模型把它们全归因“缺cmake”，但首工具明确cmake可执行，且继承preset真实构建已过。缺某fixture特定工具版本仍可能，当前原输出不足以证明八例全相同原因。后续`-k 'not tool'`行657将89例全deselect，不是排除环境要求后测试成功。没有修环境或重新通过八例，最终integration41P不能核销这些错误。

### 并行

gateway46HTTP由**45实际模型请求＋1count_tokens请求**组成；第13条count_tokens返回input18274，不是新样本或模型重试。adapter45、CC47回合、46工具是不同计数。模型seq1与10各两独立Bash，其他43个工具响应各一个，最后结束；批量工具交付成立，无执行区间证明同时运行。SSE与CC两处工具参数规范化（Edit补replace_all=false、去掉已处于/testbed的cd）不算生产改动或新的调用。

读源码后helper与公开测试可批量取，长测试片段多次串行Read有减少空间。编辑、fixture纠错和重新验证有先后依赖；Conan客户端／pytest共享缓存与工作树不直接认定可安全并行。

### 验证

| 轨迹行 | 实际结果及范围 |
| --- | --- |
| 283／301／371 | 实际生成默认jobs2、显式16，Windows声明配置的Release／Debug preset均jobs2；生成范围，不是Windows构建 |
| 321 | functional preset选测10P／8skip／27deselected；skip包含旧Linux版本条件，不等于当前CMake无法运行 |
| 339 | 继承preset功能1P；公开源码实际CMake configure／build并运行Debug／Release C++程序，默认jobs，是真实构建证据 |
| 353／601 | 公共integration preset13P／1skip后14P／1skip，第二次含新增一例；重复旧例不累加独立覆盖 |
| 537→555→583 | 新例错期待16失败；补明确jobs16后新例P；只生成JSON，没有真实Multi-Config名称验收 |
| 619 | 自称“end-to-end”脚本仅install并读jobs8、打印布尔值，未运行它写出的CMakeLists或main.cpp |
| 639／657／673 | 两目录61P20skip8error；89例全deselect；单integration41P3skip含新增一例，不算所有旧例回归成功 |
| 可信grader | 5F40P45参考均P；默认同进程helper、显式2／7真实configure／build、Multi-Config配置回归成立，另三skip非参考 |

新增公开默认只断言大于0，不核同进程helper相等；显式16检查有效，第三次generate固定配置后通过，不恢复其最初错误假设。正式参考独立恢复旧公开测试并用固定强化oracle，原模型测试剔除。最终41integration通过陈述与原footer一致；未披露广测八错误，且“build much faster”没有吞吐计时依据。质量问题不改变当前正确生产候选／raw1。

### 效率

求解 **92.610秒**，harness89.666秒；CC89.047／API64.161秒，残差24.886秒不是纯工具时间。45模型请求累计输入 **1,761,359**／输出 **9,008 tokens**，最大单输入62,926；count_tokens不加入模型累计usage。定位后生产未回退，成本主要为长测试文件多次读取、找新例位置、错误fixture重试、重复与广测；不能因更多token判更优验证。

Git16.363秒、可信初始化8.256秒单列；评分94.229秒，reset16.997／prep0.268／test5.633，队列0。实际45模型请求max_tokens均65536；CC32000为汇总元数据。声明196608上下文／240回合／3小时未触及，不证明极限容量。CC费用9.031995美元是估算，非GPU账单。

### 结束与稳定性

completed／success／end_turn，harness0，45模型SSE及count_tokens HTTP均200，无stream error；不能把非stream count响应要求为SSE message_stop。完整退出及PID1成功journal、actor／grader清理和gateway revoked／drained／active0合读；not-found默认0不作退出证据。资源间隔采样、完整限额和当前权重hash边界保持，不推全程峰值。

两模型各一次结果齐：Qwenraw1、Coderraw0。该对照支持一次尝试的默认语义差异，不建立稳定成功率、模型排名或训练资格；候选失败保持有效样本，不自动追加修复样本。普通追加采样按覆盖优先暂缓。

## 处置

题主已全文核收[语义窄核](../../reviews/non_author_15422_qwen36_a1_semantic_review_20261003.md)，SHA `808b8d7dc1d64b37d101f36dfcf0ac136c32f64a933c3062f886bdf04a9de2e4`，以及[执行窄核](../../reviews/non_author_15422_qwen36_a1_execution_review_20261003.md)，SHA `9cac51222c830c63b3b94d5ac901fa31b18be57b0cd56b866ad00ff38461c96c`。无当前候选／材料或运输阻断；采纳P2 `F15422Q-1`，按`no_fix_accept_residual_risk`保留原轨迹，只修正本文验证范围和失败披露，八ERROR根因仍未知，继承preset真实C++执行独立保留。两显式可信参考用`project(JobsPreset NONE)`，真实configure／build接受preset但不编译源码，也不证明吞吐增益。原reward、完整候选及历史失败保留；当前根核无材料误拒或合理求解阻断依据。质量问题只修正分析范围，不修改冻结模型候选，不新跑CPU／GPU或改共享consumer；两臂核收完成后核总回执、先ACK再释放活动指针；整项执行完成不是两臂都成功。
