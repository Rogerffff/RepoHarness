# Pydantic8511：非作者正式CPU与公开actor结果窄核

2026-10-03。**本题本轮CPU验收通过，实际公开actor环境及CC交付也已核，可以继续普通GPU探针；没有本轮题级阻断。** noop／gold／narrow 原reward为 **0／0／1**。gold修复原repr节点，但三类继承回归使新增P2P失败；narrow完整173参考通过。失败是普通行为回归，不是安装、收集或运行基础设施失败。本报告不授予训练／留出资格，不修改reward。

审查者不是本轮材料或runner作者；已接触私有新增测试、gold、错误候选及历史结果，不是fresh公开读者。按未变公开身份复用[四题材料窄核](non_author_remaining_material_review_20261003.md)、[R14入口窄核](non_author_remaining_runner_review_20261003.md)和既有R7共用运输审查，不全量重核release、不重做旧矩阵或换公开读者。只读原件并使用本地标准库；未SSH、Docker、安装、调用模型、运行项目pytest或作者验证脚本。仅写本文和[同名JSON](non_author_8511_cpu_review_20261003.json)，不改共享文件、固定输入或历史证据。

## 真实作业与固定身份

正式job `pyd8511-formal-20261002232906-r14-f1f09` 在cpu-a作业槽1自然完成（2026-10-02 23:29:09–23:39:58 UTC、runtime_cpu_v2、`--execute`、退出0、stderr空）；[slot回执](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/jobs/swe_pydantic/pyd8511-formal-20261002232906-r14-f1f09/status.json)、[status](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v2/outputs/pyd8511-formal-20261002232906-r14-f1f09/status.json)和[results清单](../cpu_acceptance_20261003/remaining/results.json)一致。独立核本attempt的398份路径／大小／SHA，tar SHA为 `1df7d22b07a988a990d22a59a807d4c309434a81fc174d88ddbfaf5e89f1dc7d`。前次槽忙75未运行题目，仍保留为未执行记录，没有并入此三行。

R14为 `cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`，manifest SHA `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8`；完整1220成员和共用consumer维护／部署证据复用此前入口核查。runner SHA `b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5`、formal input SHA `bea70edd55d2a316b5d92fde1a3a894e9c79363a168e2cd92c7de2d40b83ac1b`、revision SHA `9b0dd24d100e5251ab5d2e4c9b1d522ca5f8e04ca60a7113c7bf960d739aca00`一致。本轮host有效补丁与本题工件逐字相同，1 F2P＋172 P2P逐项相同，prepared／host文件SHA、public与grading canonical摘要及材料identity独立重算相符。

材料identity为 `sha256:879bf1d3bc96bd56a96b8190728fa24df0e28cece50119015d402c917abb8eb6`，public digest为 `sha256:edc64cdddc65f7fe20b6d9f7fdfd3c8fcfb77dacbd6457010e1a8b06c9d46165`，环境digest为 `sha256:a72f287143d76320f9979e13c023966fb1915f265f5d901d790ef87dc1b15947`。实际base image为 `sha256:b331c8fa2b55168dbce5d57753265c02d9aa2a3525761d202f3802684681b9a0`，candidate／fresh grader均为注册derived `sha256:df6c3affb7ea6fd826f44863ec92926f7b52558dd0f1b42e05f97aec9fe8ca68`；原image inspect JSON及6次run参数相符。`pyd8511-e10-fixed-v1`固定Python3.8／core2.14.5，未把评分镜像发布混作正式训练actor已接通。

## 原日志、173参考与失败机制

| 候选 | 原reward | 原F2P | 原168 P2P | 新4 P2P | 真实test_rc | 原日志 |
| --- | --- | --- | --- | --- | --- | --- |

| noop | 0 | 失败 | 全通过 | 4通过／0失败 | 1 | [rpt_grading_34ace3ae](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v2/outputs/pyd8511-formal-20261002232906-r14-f1f09/eval_logs/evallog_replay-pyd8511-formal-20_34ace3ae.eval.log) |

| gold | 0 | 通过 | 全通过 | 1通过／3失败 | 1 | [rpt_grading_1d0400cd](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v2/outputs/pyd8511-formal-20261002232906-r14-f1f09/eval_logs/evallog_replay-pyd8511-formal-20_1d0400cd.eval.log) |

| narrow | 1 | 通过 | 全通过 | 4通过／0失败 | 0 | [rpt_grading_cb5445c6](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v2/outputs/pyd8511-formal-20261002232906-r14-f1f09/eval_logs/evallog_replay-pyd8511-formal-20_cb5445c6.eval.log) |


原 `test_repr_false[Field]` 在noop失败，输出仍含hidden_field；gold及narrow通过。四项新增保护中，noop与narrow全部通过；gold只通过 `test_field_default_repr_stays_visible`，三项 `test_inherited_{required,hidden,factory}_field_without_local_annotations` 失败。[gold原日志](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v2/outputs/pyd8511-formal-20261002232906-r14-f1f09/eval_logs/evallog_replay-pyd8511-formal-20_1d0400cd.eval.log)明确定位测试2659／2671／2683行创建 `Child(Parent)`，经实际候选 `pydantic/dataclasses.py:218`进入Python3.8 stdlib `dataclasses._process_class:885`，抛 `TypeError: 'x' is a field but has no type annotation`。这是候选把继承Field转换后设置到无本地注解Child引起的已知继承回归；不是测试收集错误或安装中断。narrow仅处理本地注解的替代修法通过这些保护及完整173参考，关闭其完整正对照待验项，但不外推为所有范围外语义通过。

我从固定R14 parser源码提取 `parse_log_pytest_pydantic` 的AST函数，用标准库独立执行；同时用保留完整参数ID的raw终态行重解析。每行实际收集184节点：noop为172 passed／1 failed／11 skipped，gold170 passed／3 failed／11 skipped，narrow173 passed／11 skipped。所有173参考都有合法PASSED／FAILED且与冻结parser相同；逐分区的success／failure集合与原日志逐ID相同，missing／skipped／unaccounted均为空。全部逐ID状态及11个非参考SKIP见JSON。

来源parser每行给180键＝173正式参考＋7非参考SKIP；其余4个带换行reason的非参考SKIP未收录（kw_only、kw_only_subclass和两种dataclass_slots）。11个SKIP来自Python3.8对kw_only／slots等既有版本限制，均不在参考集；三行一致，没有新增参考被skip。**不能把180键写成184完整states或180参考。** 当前180键状态均合法；不是此前5662的138键含9个非法非参考状态。这里保留非参考parser范围限制、复用共享维护事项，不据此阻断本题或全pool；将这些节点纳入参考前须先处理。

三份原log SHA／字节数分别为 `52efd857659e817990a24042d38e1feac7597b7f8cb34e0538f519a9262f36fc`／50113、`4615d55601459c9ba86d84200c504ded23a2918bff75a5cc189285c551bcd9e6`／55307、`ec701338afeb73d04e76fee31ce93e29ea51ff92df233c6aea59804ccc9fe416`／50850，与ledger／report相符；每份只有一对真实测试起止标记，无ERROR collecting／no tests ran。report／ledger均保留binary_v1、原分和普通tests_failed／resolved分类，没有infra detail或execution failure stage。

## 安装、源码、完整基线与收尾

三次原日志均实际运行editable install及testing／testing-extra依赖安装，RH2_INSTALL_RC=0、无实际失败命令标记，candidate segment完成、shell exec退出0。真实pytest退出分别1／1／0，不能把包脚本退出0当测试全部通过。R14新增8wheel prerequisite三次在UID54322执行返回0并输出唯一成功标记；实际stdin绑定Python3.8、core2.14.5、PIP_NO_INDEX／公开wheelhouse及八份wheel SHA。原件证明确实消费fixed安装和镜像，不仅是prepared字节。

七段保存脚本SHA与spec相符，三次trusted setup／test上传stdin逐字与保存脚本一致；实际attest确认原测试恢复、应用退出0和1个有效测试文件。补充观察原stdout与保存JSON逐字相同，位于正式post观察后：UID54322、Python3.8.19、`/opt/miniconda3/envs/testbed/bin/python`、core2.14.5，包和dataclasses均从/testbed导入。有效测试SHA `d5a5c1c2968f3a7e2d58e902a8d185e91fc8dcb227f359df22b227b3d3afdb90`、owner root／grader不可写；runner前后digest相同。实际源码与固定候选、FrozenPatch内容、运输stdin和导入文件SHA一致：

| 候选 | pydantic/dataclasses.py SHA256 | FrozenPatch canonical digest |
| --- | --- | --- |

| noop | `3fd9cc00c536227d63b4232c60e67ce45521b1b7d8473cf7c8bd9866d9a1539f` | `sha256:88d119bcc0f1641069ce70a4a2a01904aa6a2a237e515fd45d4090aeb676672c` |

| gold | `3635a04fcb3b3b5a450216a71f3f1477f9e5855ec41e88a275894d4869bcdc6d` | `sha256:2a6538f359cc666b9118f1ea7efb30a4953907f200ffdb8cd65c3948d4fed9a7` |

| narrow | `337e4d552b22aef94960740b385c7ca93cd1b09619997e74e4e93da6427190df` | `sha256:6c1136c1d71fc44c4942314885caa6b59463ccc750815594d6b6a051ea337b56` |


每行拥有独立physical attempt、一份FrozenPatch及**完整452文件baseline**，canonical digest独立重算均为 `sha256:40135f281c216e76a04de6772eaaadcdfd0b46d949e98c5164f29cba2f454e45`。九份原始census（各候选初态／后态及fresh grader）逐文件核完整路径、类型、mode、内容digest；25个排除路径摘要与policy摘要重算相符。noop空delta；gold／narrow只改dataclasses.py，冻结base64内容digest、projection与实际运输stdin相同；fresh grader在delta运输前的452文件基线逐项相同，随后仅运输登记的单一源码delta。核对没有缩成单一源码或只有文件数。

baseline环境字段仍为null，另核prepared／host／revision的环境identity；因此不能宣称完整环境lineage或训练准入。六次实际run为断网、2 CPU／4 GiB／PID512，grader原cgroup也为200000 100000／4294967296／512。预算沿既有reset300／apply120／test1800秒，candidate900／grading3600／cleanup120秒，manager close300秒，没有改预算或追加候选。111份Docker call均退出0。候选与grader对应6次rm为0011／0035／0048／0072／0085／0109，原stdout为对应容器名、stderr空；manager3创建／3删除，open／supply／cleanup failure为空。0110／0111按本run标签查容器／网络，返回0且输出空，证明归档时本run零残留；不外推其它作业或当前新现场。

## 实际公开actor与数据流

actor job `pyd8511-actor-20261002234027-r14-3deca` 在作业槽1于2026-10-02 23:40:31–23:41:28 UTC自然完成退出0。独立核32份原件和tar SHA `1821b15a84f188e2ecdfe245e57e4dfd2e1f126440ea593a480838dcac83af47`，[diagnostic_result](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/diagnostics_v2/outputs/pyd8511-actor-20261002234027-r14-3deca/diagnostic_result.json)、[actor attempt](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/diagnostics_v2/outputs/pyd8511-actor-20261002234027-r14-3deca/actor/attempt.json)及slot回执一致。actual image和公开source base仍与上述固定身份相符；派生构建已有的pdm.lock／pyproject两项改动保留，实际源码没有变成gold或narrow。

实际CC为2.1.205，4次控制桩请求驱动3条Bash命令，完整trajectory返回0／returned、stderr空。第一命令实际执行固定源码SHA与可写性assert并返回0：UID54321、Python3.8.19／testbed解释器、core2.14.5、/testbed包与dataclasses导入、base源码SHA `3fd9cc00c536227d63b4232c60e67ce45521b1b7d8473cf7c8bd9866d9a1539f`。我从实际trajectory取Bash command，与固定命令逐字quoted内容相符，不只读作者checks。原公开目标输出 `x(y=3) a(b=1, c=2)`、TARGET_EQUALS False及指定AssertionError，rc1正确复现已知base问题；两项既有公开default_factory测试实际2 passed／rc0。三项capture字节数完整且未截断。

[首桩请求body](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/diagnostics_v2/outputs/pyd8511-actor-20261002234027-r14-3deca/actor/stub/requests/messages_000.json) SHA `f98e9a0b90c9d4bd684798803d35f2a6552684ffe2e2763008adb5ec23bf73a1`、public_prompt SHA `08cd1f9d2209cc1d02db3996d3946b248422f33fa722c81ff9f0b8b0ea70645c`。按原字节保留题面CRLF核对，首请求确含完整原题面＋hints；递归解码四份请求文本，不含私有effective patch／gold／narrow全文、新增私有函数名或host材料路径。实际[prelaunch inspect/probe](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/diagnostics_v2/outputs/pyd8511-actor-20261002234027-r14-3deca/actor/prelaunch.json)记录binds=[]／mounts=[]，没有把host private目录挂入actor。

数据流也核过：run_actor仅从public view渲染prompt及读取独立public命令；devcheck只对rollout spec做精确image override；acceptance_startup_2虽在host加载prepared context，但从rollout_views构造 `grading_spec=None` 的公开任务面，actor路径只写激活文件、运行CC及固定公开命令，没有应用test_patch或执行正式评分。结合实际mount、首请求、全部工具命令／输出及源码SHA，当前范围内无私有材料交付；不是单凭“私有函数名未出现”作结论，也不是全系统泄漏审计。

prelaunch与activation均通过，实际容器2 CPU／4 GiB／PID512，探针ACTIVATION_WRITE=DENIED；专门agent Bash写BASH_ENV拒绝命令未运行，`bashenv_denied_for_agent=false`原值保留。post事实agent进程为0；actor容器rm0、relay／network failures空、stub rc0、带run标签容器／网络与force后残留为空。**这是实际CC控制桩的环境、公开开发和首消息交付验收，不是模型求解。** 命令只读源码、检查可写性和运行既有测试，未实际修改源码、应用私有测试或导出候选FrozenPatch。精确override按现行诊断边界有效，正式SWE source actor／训练typed actor接线没有因此变成已验。


**8511可以提交普通GPU探针。** 本轮完成其R14正式消费、完整参考／行为失败、FrozenPatch／full baseline、清理及实际公开actor条件的非作者原件核查。GPU仍按请求核当前部署兼容版本、精确actor镜像和真实首消息，私有材料不进入solver；真实模型难度、GPU执行结果及训练／留出资格不在本文证明范围。
