# Project-MONAI__MONAI-5686 独立初判

结论：有真实目标分差，但现有验收不足以证明可训练的SSIMLoss；gold静态上残留文档支持的多通道/pseudo-3D梯度断开路径。建议作为标明争议的开发诊断保留，needs_review/static_review；不宣称gold新增回归、完整正确解或ready_for_probe。

## ①身份与②公开目标

base `25130db17751bb709e841b9727f34936a84f9093`；公开/私有grading/历史host view身份一致。题面最后一句“will be False. But it should be True”结合代码可明确解释为观测False、期望True，不是互斥要求。公开单batch单channel二维例子在y.requires_grad=True时希望loss保留计算图。SSIMLoss为torch _Loss，文档 `monai/losses/ssim_loss.py:39,49–55,69–74` 还公开batch/channel/3D、尤其[1,5,10,10]的pseudo-3D用途。

## ③完整需求—断言双向表

全部expected前缀为 `tests/test_ssim_loss.py::TestSSIMLoss`。完整读新增数据构造、两条新增测试体断言及所有旧数值断言；无需导入parameterized即可按构造顺序追踪身份。

|需求/既有行为|测试身份与决定性断言|覆盖/反向依据|
|---|---|---|
|公开二维单通道例子requires_grad=True|F2P `test_grad_0`：device=None；`test_grad_1`：device='cpu'；两者都是x=y=0.5、B=C=1、y需要梯度；`result=1-SSIMLoss(...)`后assertTrue(result.requires_grad)|直接覆盖题面标志；通常是同CPU路径，非两种梯度语义。没调用backward、没查y.grad或梯度值。|
|二维相同/不同图像SSIM数值|P2P `test2d_0` None相同→1，`test2d_1` None零y→0，`test2d_2` CPU相同→1，`test2d_3` CPU零y→0|全部断言Tensor且abs(expected-result).item()<0.001；结果是1-loss。保护两个极端数值，未检查一般输入或梯度。|
|三维相同/不同图像SSIM数值|P2P `test3d_0` None相同→1，`test3d_1` None零y→0，`test3d_2` CPU相同→1，`test3d_3` CPU零y→0|同上；全部B=C=1。没有3D梯度断言。|
|真正梯度回传到模型/输入|无断言|loss语义要求可训练，requires_grad标志只是必要条件，不保证与y连通。|
|公开pseudo-3D多通道/多batch梯度|无expected断言|loss doc明确示例，不是reviewer凭空扩展；gold残留见下。|
|CUDA|测试构造只有torch.cuda.is_available时追加组|CPU历史只收集10项；expected只有上述CPU身份，不能推断GPU已验。|

相关旧 `tests/test_ssim_metric.py` 全读：2D/3D数值及aggregate一致性，testfull检查多通道3D contrast为1；本题历史未执行，也不检测loss梯度。没有把它算为本题P2P。

## ④决定性helper、gold与未修完整问题

base loss `:83–94` 调SSIMMetric的公开__call__。`metrics/metric.py:313–336` 委托IterationMetric，`:69–71` 对y_pred/y detach后才调用_compute_tensor。`metrics/regression.py:78–82` 的_compute_tensor保留shape/type检查并进入SSIM `_compute_metric`；`:289–307,347–355` 卷积/乘除/mean为可微计算。gold在loss两个batch分支都换成_compute_tensor，能保留单channel路径的输入计算图，并不改metric公开累积接口。

但是 `_compute_metric` 的多通道分支 `regression.py:329–345` 逐通道再次调用 `SSIMMetric(...)(...)`，又经过metric.py:69–71的detach。因此把公开pseudo-3D例子[1,5,10,10]的y设requires_grad=True、data_range来自不需梯度的x，gold仍将各通道计算图切断；stack/mean不能重接输入。这里是基于完整调用链的高置信静态残留缺陷，尚无本轮执行；base也有同问题，**不是gold新增回归**。check25和27应保留问题，check26不得因此判issue。

另一旧问题：loss在B>1循环的每轮 `ssim_value.view(1)`（:94）到第三个batch时已有两个元素，静态上可能失败；base与gold均未改此拼接，B>=3未在expected中。它是既有范围限制，不作为本题新增回归或强制前置门。

合理非gold方案包括抽出纯可微SSIM计算供loss/metric复用，或在loss处理channel而维持metric的detach/累积契约。测试不要求调用私有_compute_tensor。错误方案仅在脱离输入的loss上requires_grad_，或加0*y.sum以伪造图依赖，也能满足新标志并保留旧数值；缺少backward/梯度合理性断言（静态反例，未执行）。公开相同图像处真实梯度可能为零，因此补强不能武断要求题面例子梯度非零，应选非恒等小输入检查与y连通、有限梯度及必要的数值差分。未发现合理实现被现有断言强制排除的证据。

## ⑥开发需求和条件

|需要的操作/资产|公开依据|历史证据范围|缺口|最小公开命令与预期|
|---|---|---|---|---|
|torch+workspace MONAI CPU导入/自动微分|题面完整例子、requirements.txt torch>=1.8/numpy>=1.17|历史Python3.8.20/torch1.13.1，grader导入/testbed|actor解释器/源码来源与权限未知|记录解释器/monai.__file__后原样执行题面；base标志False，修复单通道预期True。|
|公开相关窄测试|CONTRIBUTING.md:102–120；test_ssim_loss.py|历史加隐藏patch后10项|公开base仅8项数值测试；当前actor未验|`python -m tests.test_ssim_loss`或窄pytest，加题面API例子区分目标；CPU足够，无权重/文件fixture。|
|多通道实际梯度连通|SSIMLoss doc :69–74 pseudo-3D例子|完整静态链表明gold残留；无此运行|需独立私有gold对照确认范围|沿公开SSIMLoss API，把公开C=5例子y设requires_grad，记录loss.requires_grad并尝试autograd.grad；用非恒等输入避免把正确零梯度误判断开。|

依赖供应可预置；任务行为没有网络服务或GPU硬需求。setup.py:25默认不编译MONAI扩展，本路径是torch算子；全量requirements-dev含可选包不等于此题必须全库安装/通过。历史deny_all grader成功不是actor开发可用证明。

## ⑧用途与唯一优先下一步

优先让任务二在同一可追溯条件，用公开SSIMLoss API核单通道原例及公开多通道例子的真实输入梯度连通，并保留base/gold对照，明确残留范围。这一步同时检验actor可用性和最重要质量疑点，不需要GPU或为本题另造全仓流程。不能只重复requires_grad标志测试后宣布完整。编号：2/18/19/20在下述历史范围有支持；23明确；25 issue，27公开单通道修复有效但多通道不完整（静态）；26 unknown；3/6/8/10/29–36 unknown或not_checked。未检查项不记pass。

## 边界与八方面口径

本稿为 fresh reviewer 的独立静态初判，未读任何 public_read、主审初判/card/record/delta、旧质量报告、history、其它包或根汇总。共享目录按允许路径控制暴露，不声称 OS 隔离。只读指定三题公开/私有材料及其精确原件引用；只写本 reviewer_initial.md。没有执行/导入项目、测试、安装、网络、容器、SSH、GPU 或模型，没有修改题目/评分，也没有派发新运行。

八方面分别为：①身份与公开输入；②题意与合法实现；③新增测试及原断言；④gold与相关调用者/回归；⑤历史执行与评分；⑥actor开发条件；⑦泄漏、提交和控制面；⑧用途及下一步。下文逐项覆盖，不以八个 pass 代替范围。

共同限制：base_identity 是明确 base_commit 的跟踪 Git blob 导出，actual_actor_worktree=unknown；计划 user_prompt、public_hints 不等于实际模型消息。实际镜像 HEAD、来源规定初始改动、准备后 porcelain status 的输出/退出码/阶段、忽略资产、UID/HOME/cwd/PATH、源码导入和写权限均未获本轮 actor 证据。历史 grader 日志中的普通 git status 是当时 grader 阶段，不替代上述记录；git show 中的 diff 是提交内容，不是未提交变更。合法解可改非测试源码；未发现需要额外路径排除。审查者已暴露 gold、隐藏测试及本题原 grader 结果，审查资料不可交独立 solver。实际泄漏/控制面抗篡改、全库重复/留出重叠、真实 CC 交付和能力/训练适配没有据此认证。

## ⑤原始运行与评分证据

- noop：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-1/ledger.jsonl:3`；日志 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-1/eval_logs/evallog_replay-f216-baseline01-w_8270b8b1.eval.log`。test rc=1，F2P 0/2，P2P fail=0/8，parsed=10，outside_segment=0，reference_missing/skipped均空。实际image ID `None`；scripts digest `sha256:538e47decf626343d421e958d14f877ac651f42182f009dff533c16cf843f13c`。资源原字段 `{"mem_peak_mb": 1001.273, "mem_peak_unavailable_or_zero": false}`，不外推单位。
- gold：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-1/ledger.jsonl:4`；日志 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-1/eval_logs/evallog_replay-f216-baseline01-w_2d0e37bb.eval.log`。test rc=0，F2P 2/2，P2P fail=0/8，parsed=10，outside_segment=0，reference_missing/skipped均空。实际image ID `None`；scripts digest `sha256:538e47decf626343d421e958d14f877ac651f42182f009dff533c16cf843f13c`。资源原字段 `{"mem_peak_mb": 542.176, "mem_peak_unavailable_or_zero": false}`，不外推单位。

已核各选中ledger行和日志文件SHA与run_refs一致，gold候选原件逐字节等于本题gold.patch；projection frozen digest与原ledger吻合，baseline仅核授权/task_id，stage核/apply_method=git_apply。未浏览其它ledger行内容。历史tar仅检查授权4个源码成员的名字/size/mode，未读归档源码实现、未据此认证当前scorer。host grading view仅读本题选择行（2446为3，3715为10，5686为18）。

原命令 `pytest -rA tests/test_ssim_loss.py`：noop日志689/695/710–725/790–800为命令、10项收集、两个requires_grad断言失败及8pass/2fail；gold718/724/792–802为10pass。失败直接对应题面，非依赖阻断。baseline生成shell未单独定位；gold日志387–595记录删requirements-dev中MONAI git URL、装types-pkg-resources0.1.3/pytest、pip requirements-dev、setup.py develop。actual image ID为null。

上述均历史RH2 grader条件：rh2grader UID54322、candidate apply身份agent/54321，policy cpus=2.0、memory_bytes=4294967296、network=deny_all、pids_limit=512，candidate_stage_seconds=900、grading_deadline_seconds=3600。install_rc_last_command=0仅代表最后安装命令；已抽读实际安装/测试段，未声称安装每一步均经fail-fast保障。cleanup记录removed=true、rm:ok；每种候选只引用一次运行，未证明重复稳定、并发/重置健全。来源grader status显示noop clean、gold只改目标源码，是历史评分阶段；不是actor初始工作树采集。测试恢复/patch apply日志RH2_SETUP_OK=1及目标文件匹配支持本次执行身份，但没有审计全部安全边界。

## ⑦实际阅读/未读声明

已读本题公开prompt/bundle/identity/environment brief和私有grading/test.patch/gold.patch/run_refs/environment_record；其JSON字段用stdlib解析。已按上文范围读base目标/调用者/测试与决定性helper；README、CONTRIBUTING、requirements、setup.cfg/setup.py/runtests只读或检索开发相关段落，并非通读全仓。私有validation/source_refs的2446内容已读；其它两题未单独读这两个冗余文件。日志读取为安装命令/身份/可信恢复/测试失败与结果段及检索，不声称逐行通读所有依赖输出。原件hash核对不是项目执行。

未读公开读者或主审输出、旧质量结论、跨包结果；未读整个base所有文件、实际actor消息/镜像和未定位资产；未检查当前控制面源码、网络泄漏路径及模型求解记录。没有本轮CPU/模型验证。八方面中⑦只有静态提交边界和暴露声明，不提供安全认证；⑧只有development_diagnostic建议。
