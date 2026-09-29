# Project-MONAI__MONAI-3715 独立初判

结论：可作受限开发诊断静态候选，但验收对题面核心字符串 `train` 有明显漏测（check25）。gold 的一行变量修正静态上同时修复 eval/train 且保存枚举行为；历史2项成功只证明 eval 字符串和空数据默认路径。保留 needs_review/static_review，非 ready_for_probe。

## ①身份与②公开需求

base `d36b835b226ab95ffae5780629a5304d8df5883e`；公开/私有grading/本题host view一致。题面报告 `mode="train"` 被拒并妨碍SaliencyInferer。`monai/engines/evaluator.py:67–68,94` 明示同时接收字符串eval/train或ForwardMode枚举，`utils/enums.py:207–213` 是普通Enum，不与字符串相等。base `evaluator.py:117` 把标准化结果赋给self.mode，却在118/120判断未经标准化的局部mode，因此有效字符串触发123处ValueError。`look_up_option` 在 `utils/module.py:78–93` 接收有效str/enum，去首尾空格并返回枚举。

## ③需求—断言双向表

全部expected均为 `tests/test_prepare_batch_default.py::TestPrepareBatchDefault`。

|公开要求/旧行为|断言/测试|覆盖与反向依据|
|---|---|---|
|字符串eval接受且能跑一次|F2P `test_content`，唯一patch是添加mode="eval"；base :26–50构造SupervisedEvaluator后run，比较output image=[1,2]、label=[3,4]|覆盖受文档支持的eval字符串，未覆盖题面实际train；断言是输入/标签而非预测或模式状态。|
|字符串train接受并进入训练/启用梯度|无新增/expected断言|缺失；题面直接要求，不能因eval测试通过宣称已验Saliency流程。|
|默认枚举eval/空数据继续可用|P2P `test_empty_data`，:52–63，epoch_length=0，默认mode，只运行无异常|部分保护默认构造；没有网络forward、训练状态或梯度检查。|
|两枚举仍可用；不支持的mode被拒；网络原状态恢复|无expected断言|分别由Union类型、look_up_option和eval_mode/train_mode公开代码支持；未把全部诊断要求升级为题面额外规范。|
|EnsembleEvaluator同样委托Evaluator|旧 `test_ensemble_evaluator.py:20–81` 默认枚举，预测值/事件属性检查|已读完整旧测试，但历史本题未执行，不计P2P。|
|SaliencyInferer公开用户路径|旧 `test_saliency_inferer.py:21–48` CAM/GradCAM/GradCAMpp形状检查|不经过Evaluator字符串mode，无法弥补核心漏测；已读未执行。|

已完整读唯一新增参数及其后所有断言、TestNet identity forward、PrepareBatchDefault/default_prepare_batch (`engines/utils.py:106–159`)、assert_allclose (`tests/utils.py:62–93`)。assert_allclose检测类型/数值，默认不检查device，且不会验证forward训练模式。

## ④合理路线、误拒、漏测与gold

gold 将117行变为局部 `mode = look_up_option(...)`，已有分支随后给self.mode装入上下文管理器。SupervisedEvaluator在221传递mode、260处调用self.mode(network)；EnsembleEvaluator在354/397同样委托。`networks/utils.py:294–357` 的eval_mode切eval并torch.no_grad，train_mode切train并set_grad_enabled(True)，finally恢复先前状态；SaliencyInferer (`inferer.py:182–224`) 选择CAM/GradCAM并调用。该调用链支持gold修复字符串train，但本轮无运行验证，也未完整审阅CAM反向传播内部。

合理替代是直接把规范化enum映射到两个上下文管理器，或改条件比较规范化值；无需与gold同样赋值。简单将所有有效mode映成eval、仅特判"eval"，都可能通过这2项却保留题面train错误；这是静态反例路线而非已运行结果。仅修train会被F2P拒绝，但eval也是现有公开API，所以不能把这种拒绝称为错误验收。invalid mode、枚举train、网络状态和启用梯度仍漏测。当前未发现gold新增回归，不能以测试覆盖不足记check26 issue；check27是静态合理及历史eval有效，不是Saliency全流程完整性认证。

## ⑥开发需求和条件

|需要的操作/资产|公开依据|历史证据适用范围|缺口|最小公开命令及预期|
|---|---|---|---|---|
|实际workspace导入MONAI、torch、ignite|题面Evaluator；requirements-dev.txt:3 pin pytorch-ignite0.4.8；CONTRIBUTING:98–116|历史gradereditable develop及/testbed导入|actor实际解释器、PATH、权限/版本未知|记录sys.executable、monai.__file__，在CPU运行公开SupervisedEvaluator的一批dict数据；base mode='train'应在构造时失败。|
|观察训练模式和梯度实际启用|题面Saliency训练推理；eval/train上下文实现|本题历史只跑eval身份网络|当前train与状态恢复未验|在CPU小网络forward中记录training和torch.is_grad_enabled，分别用'train'/'eval'及两枚举运行，期望train=True/True、eval=False/False，结束恢复原状态。是公开API流程，不只内部helper。|
|旧测试可执行|CONTRIBUTING建议python -m tests模块；公开已有test_prepare_batch_default|历史本题2项执行|公开base原测试无mode参数，单跑不能复现目标|`python -m tests.test_prepare_batch_default` 配合上述mode原例；不要求全仓绿。|

无权重、医疗数据或网络服务需求；可用小网络和内存tensor CPU检查，Saliency旧测试也自建DenseNet，无预训练下载。必要依赖与可写源码需在actor中核验，历史grader安装不是actor资格。

## ⑧用途与唯一优先下一步

任务二优先在正式actor入口核实际工作树/解释器后跑上述SupervisedEvaluator mode矩阵，直接覆盖题面train并记录forward模式/梯度与状态恢复。可在独立私有条件用gold对照，不能将私有补强提示交solver。此步骤比再重复现有eval隐藏测试更有价值。不自行执行/派发。编号：2/18/19/20仅下述历史范围成立；3/6/8/10/26/29–36为unknown或not_checked，23明确，24未见唯一实现约束，25 issue；未检查编号不记pass。

## 边界与八方面口径

本稿为 fresh reviewer 的独立静态初判，未读任何 public_read、主审初判/card/record/delta、旧质量报告、history、其它包或根汇总。共享目录按允许路径控制暴露，不声称 OS 隔离。只读指定三题公开/私有材料及其精确原件引用；只写本 reviewer_initial.md。没有执行/导入项目、测试、安装、网络、容器、SSH、GPU 或模型，没有修改题目/评分，也没有派发新运行。

八方面分别为：①身份与公开输入；②题意与合法实现；③新增测试及原断言；④gold与相关调用者/回归；⑤历史执行与评分；⑥actor开发条件；⑦泄漏、提交和控制面；⑧用途及下一步。下文逐项覆盖，不以八个 pass 代替范围。

共同限制：base_identity 是明确 base_commit 的跟踪 Git blob 导出，actual_actor_worktree=unknown；计划 user_prompt、public_hints 不等于实际模型消息。实际镜像 HEAD、来源规定初始改动、准备后 porcelain status 的输出/退出码/阶段、忽略资产、UID/HOME/cwd/PATH、源码导入和写权限均未获本轮 actor 证据。历史 grader 日志中的普通 git status 是当时 grader 阶段，不替代上述记录；git show 中的 diff 是提交内容，不是未提交变更。合法解可改非测试源码；未发现需要额外路径排除。审查者已暴露 gold、隐藏测试及本题原 grader 结果，审查资料不可交独立 solver。实际泄漏/控制面抗篡改、全库重复/留出重叠、真实 CC 交付和能力/训练适配没有据此认证。

## ⑤原始运行与评分证据

- noop：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w05-1/ledger.jsonl:15`；日志 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w05-1/eval_logs/evallog_replay-f216-baseline01-w_5146f8c9.eval.log`。test rc=1，F2P 0/1，P2P fail=0/1，parsed=2，outside_segment=0，reference_missing/skipped均空。实际image ID `None`；scripts digest `sha256:56d3a76fcd8e956e3960c6d170247fe2b24142f99012d9625b6e684eb276590d`。资源原字段 `{"mem_peak_mb": 840.281, "mem_peak_unavailable_or_zero": false}`，不外推单位。
- gold：`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w05-1/ledger.jsonl:16`；日志 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w05-1/eval_logs/evallog_replay-f216-baseline01-w_1bbe329c.eval.log`。test rc=0，F2P 1/1，P2P fail=0/1，parsed=2，outside_segment=0，reference_missing/skipped均空。实际image ID `None`；scripts digest `sha256:56d3a76fcd8e956e3960c6d170247fe2b24142f99012d9625b6e684eb276590d`。资源原字段 `{"mem_peak_mb": 444.496, "mem_peak_unavailable_or_zero": false}`，不外推单位。

已核各选中ledger行和日志文件SHA与run_refs一致，gold候选原件逐字节等于本题gold.patch；projection frozen digest与原ledger吻合，baseline仅核授权/task_id，stage核/apply_method=git_apply。未浏览其它ledger行内容。历史tar仅检查授权4个源码成员的名字/size/mode，未读归档源码实现、未据此认证当前scorer。host grading view仅读本题选择行（2446为3，3715为10，5686为18）。

原命令 `pytest -rA tests/test_prepare_batch_default.py`：noop日志897/903/989–998/1040–1042为命令、2项收集、`unsupported mode: eval`的目标ValueError、1pass/1fail；gold915/921/966–968为2pass。不是依赖失败。baseline没有单独定位生成shell原件，以日志614–792的实际安装命令和host view为据：删requirements-dev中MONAI git URL、装types-pkg-resources0.1.3/pytest、pip requirements-dev、setup.py develop。actual image ID缺失保持null，不能拿tag或期望digest代替。

上述均历史RH2 grader条件：rh2grader UID54322、candidate apply身份agent/54321，policy cpus=2.0、memory_bytes=4294967296、network=deny_all、pids_limit=512，candidate_stage_seconds=900、grading_deadline_seconds=3600。install_rc_last_command=0仅代表最后安装命令；已抽读实际安装/测试段，未声称安装每一步均经fail-fast保障。cleanup记录removed=true、rm:ok；每种候选只引用一次运行，未证明重复稳定、并发/重置健全。来源grader status显示noop clean、gold只改目标源码，是历史评分阶段；不是actor初始工作树采集。测试恢复/patch apply日志RH2_SETUP_OK=1及目标文件匹配支持本次执行身份，但没有审计全部安全边界。

## ⑦实际阅读/未读声明

已读本题公开prompt/bundle/identity/environment brief和私有grading/test.patch/gold.patch/run_refs/environment_record；其JSON字段用stdlib解析。已按上文范围读base目标/调用者/测试与决定性helper；README、CONTRIBUTING、requirements、setup.cfg/setup.py/runtests只读或检索开发相关段落，并非通读全仓。私有validation/source_refs的2446内容已读；其它两题未单独读这两个冗余文件。日志读取为安装命令/身份/可信恢复/测试失败与结果段及检索，不声称逐行通读所有依赖输出。原件hash核对不是项目执行。

未读公开读者或主审输出、旧质量结论、跨包结果；未读整个base所有文件、实际actor消息/镜像和未定位资产；未检查当前控制面源码、网络泄漏路径及模型求解记录。没有本轮CPU/模型验证。八方面中⑦只有静态提交边界和暴露声明，不提供安全认证；⑧只有development_diagnostic建议。
