# Pydantic5662：非作者正式CPU结果窄核

2026-10-03。**本题本轮CPU验收通过，可以提交普通GPU探针；没有本轮题级CPU阻断。** noop／gold／any_only／all_nonmodels_equal 原reward为 **0／1／0／0**。any_only原ANY节点通过、新普通matcher节点失败，说明已证旧漏奖被新增行为断言纠正；失败不是基础设施异常。报告保留同根因的非参考parser缺口，不授予训练资格，不回写历史分数。

审查者不是本轮材料或runner作者，已读5662及6283私有测试、gold、错误候选与旧结果，**不是fresh公开读者**。本次按同仓窄核接续：复用[6283共享R7／runner核查](non_author_6283_cpu_review_20261003.md)、[5662／6283静态审查](non_author_5662_6283_review_20261003.md)和既有公开actor证据，只补本job的原始运行结果、129参考、身份、运输、清理。未重做全题审查或旧矩阵，未SSH、启动Docker、安装、调用模型、运行项目测试或作者自动检查脚本。只用本地标准库核SHA、JSON、冻结parser函数、完整节点行、canonical digest、base64和census；仅新增本文与[同名JSON摘要](non_author_5662_cpu_review_20261003.json)，没有改共享／作者文件或发跨线程消息。

## 运行与材料身份

真实job为 `pyd5662-formal-20261002203421-07d42`。[作业回执](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/jobs/swe_pydantic/pyd5662-formal-20261002203421-07d42/status.json)记载2026-10-02 20:34:25–20:47:12 UTC、cpu-a作业槽0、`runtime_cpu_v2`、`--execute`、自然退出0，stderr为空。[status](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd5662-formal-20261002203421-07d42/status.json)与[results.json](../cpu_acceptance_20261003/results.json)匹配；结果清单本attempt的496份文件路径／字节数／SHA全部独立核实。

- R7仍为 `cat2-cpu-r2e088-swe12-git-20261003-v1`，manifest SHA `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`，本次重新核manifest字节，905成员逐文件验证及部署证据复用6283核查，不重新审共用代码。
- runner SHA `8c1c055957535012df0fbed9e7404592d0c8badacadee32042171702ad8d41f4`，formal inputs SHA `14c66d454ea7e1f83e6bde849b2431d9b976162aec86024d706f55ba4ce48097`，与已核共用版本及作业status相同。
- [5662 revision](../tasks/pydantic__pydantic-5662/revision.json) SHA `e32a0d91eda052f84cafd732195fb2766f1038d3c4c70684e1c66788f559b598`；七项输入资产SHA相符。host消费 `pyd5662-behavior-v1`、有效补丁SHA `a5f554782a82e2c312694b897e0f529b212a265e2e03acbfddd72d17429b5a63`；原1 F2P及127 P2P逐ID保持，新增独立F2P为 `test_equality_delegation_nonexample`。
- 安装资产为独立 `pyd5662-e10-v1`，SHA `eb87eeb91b66a6ed7550897c09ccfe29b08d6218b0ffac31ee5f42ad334e8adf`，host的revised_install与固定输入逐字相同。安装脚本文本与6283相同，不把两题资产、core或镜像合并。
- prepared manifest／公开JSONL／host grading的SHA链相符；public digest为 `sha256:70cc3103e90eed08a0a723b491fada5d8158721f0a542314338694723bb7e180`，环境digest `sha256:c3d69715138f5f648216b300131181fa6334fe90fe690e7acf17520086aef8ca`，材料身份独立重算 `sha256:d35a8345e297f1b05eaabd8289633753e9b5385509794a035a048058dd8c1e7b`，与各行ledger／diagnostics一致。

## 逐参考结果与普通失败

正式分母为2 F2P＋127 P2P＝129。四行所有129个参考均从原始日志逐ID核对，再对照冻结parser及原／新参考分区；完整状态保存在JSON的各行 `reference_states`。无参考missing、skip、unaccounted，无收集错误或零测试。

| 候选 | 原reward | 原ANY F2P | 新普通matcher F2P | P2P通过／127 | 测试退出 |
| --- | --- | --- | --- | --- | --- |
| noop | 0 | FAILED | FAILED | 127／127 | 1 |
| gold | 1 | PASSED | PASSED | 127／127 | 0 |
| any_only | 0 | PASSED | FAILED | 127／127 | 1 |
| all_nonmodels_equal | 0 | PASSED | FAILED | 125／127 | 1 |

noop在旧 `MyModel(foo='bar') == ANY` 第2216行及新普通matcher相等结果第2236行失败。gold的新测试完整通过，执行了True／False／NotImplemented返回、接收原模型对象和dict／object边界断言；没有要求内部实现形态或固定调用次数。

any_only唯一失败为新增第2236行：普通matcher返回True应相等，实际False。原ANY和127项旧回归均通过，故新0分准确来自此前没有覆盖的一般委托行为。另只读旧[any_only正式ledger](../../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5662/followup_20260928T182457Z-a73f19/grade_any_only/ledger.jsonl)与冻结导出，核旧reward仍为1、输入patch SHA `f889a2d5f579b5e3237c1702f8774355251dda97bac32f5f3bda0cfa598fa05f`，导出源码SHA与新any_only完全相同；这是同候选在修订参考下被正确拒绝，不改绑或重写旧分。

all_nonmodels_equal在新增第2237行失败：`matcher.seen`为None，没有把原模型交给接收者；同时旧 `test_comparing` 第123行与 `test_model_equality_dump` 第1987行失败，均为模型错误地等于dict。三处都是实际行为AssertionError。新节点并未代替或移除旧边界护栏。

四份安装均完整打印 `RH2_INSTALL_RC=0`、没有失败命令；实际执行editable安装及由候选pyproject导出的testing／testing-extra依赖安装。候选exec均退出0且测试段完整结束，测试退出1／0／1／1；最后时间标记导致exec为0，不能拿它替代pytest结果。report的binary原reward、resolved／unresolved、`tests_failed`及F2P／P2P计数都与原始行为相符，infra／执行失败阶段为空，没有安装、收集、超时、baseline或清理失败冒作错解被拒。

[noop ledger](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd5662-formal-20261002203421-07d42/noop/ledger.jsonl)、[gold ledger](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd5662-formal-20261002203421-07d42/gold/ledger.jsonl)、[any_only ledger](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd5662-formal-20261002203421-07d42/any_only/ledger.jsonl)、[all_nonmodels_equal ledger](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd5662-formal-20261002203421-07d42/all_nonmodels_equal/ledger.jsonl)与各目录report及diagnostics已逐项对照。下面日志byte_size／SHA均与report和ledger一致；对应候选exec stdout完整包含于归档eval log，测试段相同。

| 候选 | 原始日志 | 字节数 | SHA256 |
| --- | --- | --- | --- |
| noop | [evallog_replay-pyd5662-formal-20_f636ca08.eval.log](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd5662-formal-20261002203421-07d42/eval_logs/evallog_replay-pyd5662-formal-20_f636ca08.eval.log) | 366584 | `d684db20cf5df44b7a76ce96e79e049673e89ecadf0050e9fedaa7f81ede3683` |
| gold | [evallog_replay-pyd5662-formal-20_033aec72.eval.log](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd5662-formal-20261002203421-07d42/eval_logs/evallog_replay-pyd5662-formal-20_033aec72.eval.log) | 366612 | `2446653cbc708a64d9817607f0b131ec6d1017d4318d42c78f794b68c8b8960a` |
| any_only | [evallog_replay-pyd5662-formal-20_feeb176a.eval.log](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd5662-formal-20261002203421-07d42/eval_logs/evallog_replay-pyd5662-formal-20_feeb176a.eval.log) | 366590 | `1e70f77d763e8fe9612f0221c4c533546caebfc65a4268465d1fb8dfc6e93ba5` |
| all_nonmodels_equal | [evallog_replay-pyd5662-formal-20_aede7206.eval.log](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd5662-formal-20261002203421-07d42/eval_logs/evallog_replay-pyd5662-formal-20_aede7206.eval.log) | 367874 | `bd56a30628cd8a6a81fed182b0c51fa7833f9465b2f36df9ccb0ec33cef9d3a4` |

## 全收集范围及同根因parser缺口

每行真实收集169节点：129正式参考＋14额外普通节点＋26既有skip。noop为141 PASSED／2 FAILED／26 SKIPPED，gold为143 PASSED／26 SKIPPED，any_only为142 PASSED／1 FAILED／26 SKIPPED，all_nonmodels_equal为140 PASSED／3 FAILED／26 SKIPPED。26 skip均不在正式参考：25项日志为`not implemented`，1项为`need 3.10 version`，不是新断言跳过；它们不能计为通过。三组参考分区无任何缺失或跳过。

按AST仅抽取同一冻结parser函数复算，结果与作者states相同；**138个parser键＝129个正确参考键＋9个非法非参考条目，不能称138个有效终态。** 14个带空格参数名的非参考节点原日志均PASSED，但空白拆词造成截断及冲突合并，例如输入 `tests/test_main.py::test_model_export_nested_list[exclude nothing] PASSED` 被记成键 `…[exclude`、状态 `nothing]`；26个带原因的SKIPPED也未纳入parser结果。完整原始169节点及非参考条目保存在JSON。

这是[6283已记录parser问题](non_author_6283_cpu_review_20261003.md)的同根因范围补充，标记 **production_observed**。位置为 [冻结swegym_parsers.py](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_088_swe12_git_candidate_v1/repo/rh2/src/repoharness2/envpack/swegym_parsers.py) 第78–82行；真实评分路径及函数复算均产生错误记录。被违反的不变量是完整节点ID应对应合法终态，空白拆词还会让不同参数实例覆盖。当前129参考完全正确，14项都不在参考中，故**本题binary评分不受影响，不扩为全pool阻断**。

建议复用同一维护事项 `deferred_with_owner_and_gate`（尚未代表维护者已接受）：共享parser归发布线程，题主跟踪；将这些含空格节点纳入正式参考前修复。修复验收应保持完整参数名、PASSED／FAILED及真实百分比行终态，防止键冲突，做受影响参考回归并保留原分；本次不改parser、不要求5662重跑旧矩阵。

## 精确环境、完整baseline运输与清理

基础镜像为 `sha256:96aaecfda19343d97563572c064c50f02f1ebb107417dc8c8b303df868abbf7d`；四候选和grader实际均使用 `sha256:5b15de37fee0ae9af3430a92de5de7c94f539852663c403bde0b208e67016b60`。image／run／ledger／FrozenPatch身份一致；140份Docker调用退出记录均为0。实际run保留断网、2 CPU／4 GiB／PID512，容器内cgroup核 `200000 100000`、`4294967296`、`512`。

四行源码观察均为grader UID54322、`/opt/miniconda3/envs/testbed/bin/python`、Python3.8.19／core0.27.0，包导入 `/testbed/pydantic/__init__.py`、main导入 `/testbed/pydantic/main.py`。实际文件及导入SHA均与固定候选一致：

| 候选 | main.py SHA256 |
| --- | --- |
| noop | `cf537426448d1e9a768c2e6debccfd7b3dcec718b22df0ccfaf8ca1d47f69e4e` |
| gold | `d25d5c562195d388f9a9756c9e0fc22f13006ac715ddc36fc3bfdb9935ea12fc` |
| any_only | `9d0025db2036e6163f6e5543bbfbccb7eebbe4adf3a3a2d0219c12d6bc77479b` |
| all_nonmodels_equal | `87ef0f4a42fddfa2778b14fc61210ea882e0eb7679b8c8f32fc6eede27c4790a` |

七段脚本保存SHA与spec相同；实际传入的trusted_setup／test脚本逐字相同，四次真实attest都确认原测试恢复、基线SHA核对、补丁应用0及1文件存在。测试后有效文件SHA为 `d6a2dd5080262a495667108a819d7545393c9fb8398aefef11f6ae57c2e7b3e8`、owner root且grader不可写，runner前后digest相同。额外源码观察JSON与对应Docker stdout逐字相同，观察在正式post阶段之后，不回写评分。

每候选有独立physical attempt、一份FrozenPatch和**完整288文件baseline**。canonical baseline digest独立重算 `sha256:d655b5b83ef702fe52f53ef289cf5b90b2d0303d1b9da76cd2033f66f8db7058`，policy／排除路径摘要相符；四份候选初态与fresh grader census都逐文件匹配路径／type／mode／内容digest。noop delta为空，其余仅改main.py；冻结base64字节、digest、projection与实际运输stdin一致，随后导入源码SHA相同。没有只核源码子集或重绑旧FrozenPatch。

baseline环境字段仍为null，和6283同一范围限制；本轮另核prepared／host／revision环境身份，不能把它包装成完整环境lineage或训练准入。四行候选清理和grader清理分别对应8次rm：0011／0033／0046／0068／0081／0103／0116／0138，均退出0、stdout为对应容器名、stderr为空。manager close记4创建／4删除，open／supply／cleanup failure为空；final status为ok／0。0139／0140按本run标签查容器／网络，退出0且输出为空，证明**归档时本run零残留**；本次没有新现场查询或对其它作业作结论。

## 公开actor复用与当前用途

旧job `pyd5662-actor-v1-20261002T174202Z-e9db3` 的public view与本轮逐字段相同（题面、public_hints、base、镜像及public digest）。窄核旧result／attempt／slot回执SHA，[首桩请求](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/diagnostics_v1/outputs/pyd5662-actor-v1-20261002T174202Z-e9db3/actor/stub/requests/messages_000.json)确实收到原issue＋hints，prompt及request SHA相符；四个固定桩请求驱动三条预定命令。UID54321、Python3.8.19、core0.27.0、base main.py SHA及可写性断言通过；原公开ANY示例准确复现已知失败，现有相等测试7 passed／160 deselected。

此证据只证明原公开开发路径、CC交付和收尾，**不是实际模型求解**，没有运行新私有断言或导出FrozenPatch，也未做BASH_ENV专用写入拒绝探针；原checks相关False不被改成全startup通过。纯私有测试变化因此可按身份复用，不要求新公开读者；本审查未见R7新的CC首请求，实际GPU执行者仍记录本轮真实公开交付，私有gold、反例、断言及审查结论不进入solver上下文。

**5662可继续普通GPU探针。** 本轮关闭的是ANY特判已证漏奖及正式CPU材料消费缺口；真实模型难度、候选语义分析、GPU部署兼容性、训练／留出资格与RL信号仍不在本报告证明范围。题卡和离线revision的准备阶段状态是旧快照，本次不改其历史内容；当前事实以本job原件和本报告为准。
