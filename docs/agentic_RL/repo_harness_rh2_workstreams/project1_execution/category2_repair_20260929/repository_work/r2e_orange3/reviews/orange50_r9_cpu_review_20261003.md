# Orange50 R9 CPU 非作者结果核查

整理日期：2026-10-03。核查者为题主安排的非作者 subagent。当前状态为 **diagnostic_cpu_acceptance_verified**：八方正式CPU矩阵、实际CC公开开发验证及私有gold控制、工件和清理已核，**本题当前诊断CPU验收及非作者结果审查可以封存**。资源观察的覆盖缺项按下文保留；没有模型成绩，GPU probe未派发或准入，训练资格不在本轮。

本次只读核新R9原件，继承前三方已核证据；未重跑实验、共用101检查、旧材料静态审查或fresh公开阅读，只更新本报告及同名JSON。冻结八方计划的`observed_score=null`保持不变。

## 当前可确认的结果

同一实际镜像`64b59aea…`、配方`2e03f54f…`及R9 public090／hidden091下，八方按noop、gold、K1、K2、K3、K4、Cdeg、K5得到 **0／1／1／0／0／0／0／0**。每方48个参考键精确齐全；两个正对照48/48，六个负对照47/48，唯一失败键均为`TestOWColor.test_load_ignore_warning`。

| 对照 | 固定期望／正式reward | 参考匹配 | 真正抵达的语义检查 | 证据 |
| --- | ---: | ---: | --- | --- |
| noop | 0／0 | 47/48 | 第一个单变量案例没有warning；第802行`assert_called()`失败。 | [原日志](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_noop_completed_v2/noop/eval_logs/evallog_replay-orange-50f6a758-r_15ff04f0.eval.log) |
| gold | 1／1 | 48/48 | 新版目标方法完整通过：1—7个未用变量及混合文件／匹配class更名。 | [原日志](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_gold_completed_v2/gold/eval_logs/evallog_replay-orange-50f6a758-r_590cb892.eval.log) |
| K1 | 1／1 | 48/48 | 全列名单的合理解正式通过，证明新版容许此格式。 | [原日志](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_K1_completed_v2/K1/eval_logs/evallog_replay-orange-50f6a758-r_97938b5c.eval.log) |
| K2 | 0／0 | 47/48 | 加载iris后混合文件没有warning；第833行调用`shown_text()`，第802行`assert_called()`失败。 | [原日志](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_matrix_complete_v2/matrix/K2/eval_logs/evallog_replay-orange-50f6a758-r_934800e7.eval.log) |
| K3 | 0／0 | 47/48 | 混合文件没有warning；失败位置与K2相同。 | [原日志](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_matrix_complete_v2/matrix/K3/eval_logs/evallog_replay-orange-50f6a758-r_515df61e.eval.log) |
| K4 | 0／0 | 47/48 | 第835行`assertIn("bar", text)`失败；实际只报categorical的foo，漏numeric的bar。 | [原日志](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_matrix_complete_v2/matrix/K4/eval_logs/evallog_replay-orange-50f6a758-r_5238fed3.eval.log) |
| Cdeg | 0／0 | 47/48 | 第838行输出class名检查失败：`iris != species`；前面的warning、foo、bar及输出非空检查已经通过。 | [原日志](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_matrix_complete_v2/matrix/Cdeg/eval_logs/evallog_replay-orange-50f6a758-r_a4235004.eval.log) |
| K5 | 0／0 | 47/48 | 第819行单变量点名检查失败：`[] != [foo]`；实际有警告“Unused variable definitions were ignored.”。 | [原日志](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_matrix_complete_v2/matrix/K5/eval_logs/evallog_replay-orange-50f6a758-r_efa0289f.eval.log) |

gold缩写长名单与K1全列长名单均被正式接受。新增负对照的真实失败分别覆盖加载数据后的警告、混合文件警告、numeric变量点名、已匹配定义继续应用以及警告正文点名。尤其Cdeg真实抵达输出class变量更名断言，不能再把其结果只解释为早期warning失败。它们证明固定候选的接受／拒绝边界；未穷尽所有标点、顺序、缩写、多个warning或`text`关键字形式的兼容性。

## 运行与身份依据

完整证据根为`runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_matrix_complete_v2/`。作者check与notes只作索引，本报告独立读取原件核对。

- 完整读回218文件（matrix 113、job 3、observations 102），逐项字节大小／SHA-256与manifest匹配；fetch request、archive和manifest与readback receipt摘要相符。manifest SHA为`aadc3d71…`。前三方在完整归档中的ledger SHA与此前已核原件相同，保留原结论。[完整读回清单](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_matrix_complete_v2/readback_manifest.json)；[读回回执](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_matrix_complete_v2_readback_receipt.json)。
- 五个新增patch SHA均匹配固定计划和ledger；全部成功`git_apply`、stage无错误。唯一projection条目为`Orange/widgets/data/owcolor.py`，decoded源码SHA重算一致；按固定patch在内存从baseline源码重建的字节逐字等于frozen源码，canonical baseline／frozen digest与projection／ledger回链一致。没有修改native源码或产物，不涉及候选native重编。完整source digest及工件路径保存在同名JSON。
- 实际hidden tree为`5d7df733…`、entry为`5dee57d9…`；raw eval有setup OK及新版方法正文。每方在正式test段内完整解析48键，无reference missing／reference skip／unexpected／段外解析，raw log与ledger／manifest SHA一致，均非partial。51 collected包含三个非参考基类skip，不代表参考键缺失。
- 同一冻结R9包装器`ordinary_probe_20260929/replay_probe.py`调用正式`scripts/replay_grade.py`。config仅`setup_seconds=1200`，逐方在spec构造处记录before=300、after=1200、test_seconds=1800；这是grader准备预算，不是模型求解时限。matrix输入、wrapper和acceptance plan摘要与实际summary均匹配。
- 逐方ledger的`cleanup`来自候选阶段finally，八个候选容器均确认removed=true／`rm:ok`。逐方真实CLI footer均exit0、无halted／aborted／cleanup failure，grader 1 created=1 removed、open containers／supply为空；合计八个grader创建及移除。远端job状态为finished、returncode=0，2026-10-02 21:27:52 UTC收口，stdout逐方started／finished完整。该清理结论覆盖本矩阵manager，不外推整机所有任务。[矩阵结果](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_matrix_complete_v2/matrix/matrix_result.json)；[远端job终态](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_matrix_complete_v2/job/status.json)。
- 原SSH运输在20:59:24 UTC中断、returncode=255；remote job从20:54:48 UTC继续运行至上述终态0。保存运输原件，不把SSH中断计为任务失败、重复实验或评分不完整。[原运输回执](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/orange-50f6a758-r9-matrix-c-20261003-v2.transport_receipt.json)。

矩阵ledger只直接记录Orange包路径`/testbed/Orange/__init__.py`，没有逐方`owcolor.__file__`观测；固定patch／frozen源码、真实projection消费及候选特有目标行为共同支持矩阵源码应用。实际CC另行读回base／gold的具体模块路径和源码SHA，见下文；这份诊断不外推成八方逐个模块路径观测。

此前构建读回41文件与本题21项integrity仍按已核范围复用：镜像、材料与环境身份成立，不能单独替代题级验收。此前v1缺`prepared/replay_summary.json`的原件保留；它没有候选工件、ledger或正式成绩。新prepared manifest`25b3007b…`、summary`ba8a44ab…`、host grading`4632b750…`及不变的rollout字节按既有核查接续，不重跑prepare。

## 资源事实的准确覆盖

完整观察有101次采样、13个唯一容器；observer receipt与逐文件原件重建一致，reason为`job_finished`。捕获到的所有HostConfig均为2CPU、4GiB内存、512 pids、MemorySwap=4GiB、network none、Binds null；可读取的cgroup均为`cpu.max=200000 100000`、`memory.max=4294967296`、`memory.swap.max=0`、`pids.max=512`，未见配置不符或OOMKilled=true。

| 对照 | 采样次数 | 容器数 | 实际范围 |
| --- | ---: | ---: | --- |
| noop | 0 | 0 | 未在观察窗口；资源policy及ledger峰值是现有证据，不能宣称独立实测。 |
| gold | 4 | 1 | 仅grader后段grader 4次 |
| K1 | 18 | 2 | candidate 8次；grader 10次 |
| K2 | 15 | 2 | candidate 7次；grader 8次 |
| K3 | 16 | 2 | candidate 8次；grader 8次 |
| K4 | 15 | 2 | candidate 7次；grader 8次 |
| Cdeg | 17 | 2 | candidate 8次；grader 9次；末次在removing/PID0阶段无法读cgroup。 |
| K5 | 16 | 2 | candidate 7次；grader 9次 |

观察从21:02:08.069528 UTC持续至21:27:50.314281 UTC，属于15秒周期旁路采样。它独立于ledger；`ledger.resource_facts`仍为null。**noop无独立资源实测，gold只覆盖评分后段。** K1–K5／Cdeg的候选和grader均有实际限制读回；采样不能证明每一时刻或未捕获区间，也不替代CLI清理回执。[观察收据](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_matrix_complete_v2/observations/observer_receipt.json)；每份原样本路径与SHA见完整读回清单。

Cdeg最后一次采样在21:23:48.666702 UTC读到grader为removing、PID0、ExitCode137、OOMKilled=false，cgroup unavailable。原始test段已在21:23:45.162458 UTC完整结束，test_rc=1是目标断言失败，随后`rm:ok`并正常manager清理；该137位于评分后容器清理阶段，不是pytest执行失败或OOM。此缺项如实保留，不伪造成一份成功cgroup读回。

## 实际CC与公开开发验证

完整CC归档含70文件（actor 55、job 3、observations 12），逐项大小／SHA与manifest吻合，fetch request、archive及manifest与receipt摘要一致。archive SHA为`13e82336…`、manifest为`475efef8…`。真实job returncode=0，CC 2.1.205的attempt为`ran/completed`、harness_exit_code=0，10个Bash工具与10个结果ID一一匹配，轨迹完整；不是只据summary或退出0给结论。[CC读回清单](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_actor_complete_v1/readback_manifest.json)；[完整实际轨迹](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_actor_complete_v1/actor/attempt/trajectory.jsonl)。

首个gateway原始HTTP与stub收到的user文本均逐字等于真实prompt，SHA`0e229b0c…`。其中完整`[ISSUE]`正文是当前题面文件的逐字后缀，SHA`8d7ddab8…`；前缀仅添加repo、workdir和base commit。Development Note确实交付，并与实际旧测试冲突位置一致。[原HTTP](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_actor_complete_v1/actor/gateway/orange-50f6a758-r9-actor-c-20261003-v1/requests.jsonl)；[真实prompt](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_actor_complete_v1/actor/attempt/prompt.txt)。

actor实际为uid/gid 54321，workdir `/testbed`，解释器`/testbed/.venv/bin/python`，Python 3.7.9、NumPy 1.17.5；Orange与owcolor分别从`/testbed/Orange/__init__.py`、`/testbed/Orange/widgets/data/owcolor.py`加载。base源码SHA为`c5390b37…`，私有gold后为`14fcfc1c…`，后者逐字等于正式矩阵gold的frozen源码。首阶段没有应用patch；第二阶段实际固定gold字节SHA为`8f3d578b…`。

| 实际公开检查 | base结果／pytest rc | 私有gold后结果／pytest rc |
| --- | --- | --- |
| 既有5个回归selector | 5 passed／0 | 5 passed／0 |
| 5个临时公开合同检查 | 3 failed、2 passed／1 | 5 passed／0 |
| 原完整`test_parse_var_defs_no_rename` | 1 passed／0 | 1 failed／1 |

base三个失败均是unused categorical、unused numeric、unused与有效rename混合案例没有调用warning；是检查中的`AssertionError`，没有应用异常。临时的duplicate-variable-renames与name-swap案例在base及gold均通过。私有gold后，原完整冲突方法的前面两段duplicate-name检查和name-swap检查真实通过，**失败精确位于公开源码第888行最后的`msg_box.assert_not_called()`**：有效categorical varA更名为X，加未用numeric `var not`更名为X时，新行为应报警。不是先前duplicate-name检查失败，不应为让这条旧断言通过而压掉新警告。临时等效检查还核了警告点名未用变量、不是duplicate告警且有效rename继续应用。

事前提醒的`set -e`缺标记情况没有在完成原件发生：全部10项真实`RH2_STEP_RC`齐全，上述两项失败均为1。完整tool_result的`is_error`均false、没有独立数字`Exit code`字段，工具正文包含真实pytest失败和完整traceback。因此`tool_result_errors=0`／CC成功不表示所有pytest通过；报告不虚构缺失标记或未暴露的Bash数值退出码。urllib3／LibreSSL warning在实际输出中出现，但未阻断本轮导入或检查。

实际执行预算是wall_seconds=1200、CC max_turns=14、context=32768、max_new_tokens=4096；11个assistant事件、10个工具结果在实际solve 45.85秒内完成（包含准备和收口的外层探针为200.7秒）。此预算与矩阵grader的setup1200／test1800分列。场景v3 SHA`31fefc2e…`与v2所有命令相同，只修正范围描述；这是**真实CC执行的CPU stub固定控制**，不是新的fresh阅读或真实模型解题。actor使用`--no-grade`，没有自己的正式reward；同源码gold的48/48正式成绩来自已核矩阵。桩生成的usage／cost不作为模型成绩。

## native工件与实际CC资源、清理

从实际pre-solver baseline.tar只读重算1661项路径集合、类型、mode和内容／symlink摘要，全部与baseline manifest一致；canonical digest为`f2cf4b7d…`。唯一FrozenPatch条目为`Orange/widgets/data/owcolor.py`，decoded源码SHA重算为`14fcfc1c…`；frozen canonical digest为`16fe2f06…`。将1902字节渲染diff在内存应用到该真实baseline源码，输出逐字等于frozen及实际加载gold源码；diff SHA`c9437b45…`，render selfcheck tree与post tree一致。原公开测试SHA`c9784d7f…`，不在frozen修改集合；pip freeze前后字节相同。classification为projectable／无reason／unsafe=false，excluded_pathset_changed=true及生成缓存变化如实保留，不伪写成runtime完全不变。[实际baseline manifest](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_actor_complete_v1/actor/attempt/frozen/baseline_manifest.json)；[FrozenPatch](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_actor_complete_v1/actor/attempt/frozen/frozen_patch.json)；[渲染diff](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_actor_complete_v1/actor/attempt/candidate/orange3__50f6a758f1c66b8f4a18806714e3c2f4cefcab3e.diff)。

CC旁路观察从21:30:06.148982至21:32:37.652189 UTC，共11次、2个容器，逐样本限制一致。main为2CPU／4GiB／512 pids，cgroup `cpu.max=200000 100000`、`memory.max=4294967296`、`memory.swap.max=0`、`pids.max=512`；观察到memory peak为3,180,023,808字节。relay为256MiB／64 pids、swap 0，`NanoCpus=0`／`cpu.max=max 100000`，**没有2CPU配额上限**，观察到memory peak为27,213,824字节；两者未见OOMKilled=true。main用隔离内部网络及模型relay，relay为bridge，不能套用矩阵的network none。预启动原件同时核了agent无caps、NoNewPrivs、外网／直连上游受限、模型relay可达以及隐藏路径不可读。[CC观察收据](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_actor_complete_v1/observations/observer_receipt.json)；[prelaunch原件](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_actor_complete_v1/actor/attempt/facts/prelaunch.json)。这仍是周期采样，不回溯补齐矩阵noop／gold缺项。

真实pre-drain stop residual=0，gateway session_close为revoked=true／active_requests=0／drained=true；quiescence确认agent processes为0且workspace双读digest稳定。cleanup的main删除rc0、无relay／network失败、按本attempt标签无残留容器／网络，stub与gateway停止rc均0。该结论只覆盖此attempt，不证明整机所有任务，也不替代训练adapter的正式receipt。[attempt及清理](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_actor_complete_v1/actor/attempt/attempt.json)；[原session close](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_50_actor_complete_v1/actor/gateway/orange-50f6a758-r9-actor-c-20261003-v1/session_close.jsonl)。

## 当前公开开发说明的窄核

[public_development_brief.md](../tasks/50f6a758/public_development_brief.md)当前SHA为`3f5c26d6…`。其中环境、5个公开selector、完整原冲突方法和“没有运行整个公开文件”的范围说明均符合实际base原件；`python`在观测activation中确实解析到现有venv。它要求保留原测试，用临时公开断言检查unused行为，且保留duplicate及swap行为，与实际公开来源、当前题面／Development Note一致。关于外网禁用的文字指agent直连外网，模型relay例外仍存在。

未发现该说明含私有gold、隐藏测试、固定候选或实现算法，也未发现必须改的事实错误。它在本次CC后保存，**没有作为这次HTTP交付内容接受动态验证**；不能借本次结果宣称未来solver已收到它或读懂它。本轮只窄核事实和可见边界，没有再跑fresh reader。

## 验收结论与用途边界

在上述原件身份、完整八方语义结果、公开交付及开发路径、native工件和清理都成立，并明确保留资源观察缺项的范围内，**本题当前R9诊断CPU验收可以封存，非作者结果审查完成，无未解决阻断项**。无需再为本轮机械补跑或等待4014。本结果可作为后续probe申请依据；GPU准入／派发和训练资格仍不能由本报告替代。

当前solver-facing说明应保留“unused定义静默而不报警”的真实症状、分类／数值定义的警告要求、有效定义继续应用及原公开末尾断言冲突，不规定隐藏格式或实现算法。真实模型能力、held-out表现、训练分布代表性及正式训练链均未在本轮取得证据；不把固定gold／桩控制的成功写入模型成绩。

审查范围为A／D／E／F／G／H／I／L／M／N的题级运行证据窄核，C的本题CPU结果审查现已完成；GPU准入另列未完成。B不评价未提供的模型／训练分布，J／K不重新审共用实现及已独立核过的材料。这不是公共代码审查或阶段总审计。冻结计划及初始release binding的观察／qualification字段保留原文；当前结论以本报告顶层与同名JSON为准。
