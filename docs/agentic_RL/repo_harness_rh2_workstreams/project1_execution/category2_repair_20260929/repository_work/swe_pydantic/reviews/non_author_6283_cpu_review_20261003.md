# Pydantic6283：非作者正式CPU结果窄核

2026-10-03。**本题本轮CPU验收通过，现有证据足以提交普通GPU探针；没有本轮题级CPU阻断。** noop／gold／validate_construct 的原始reward为 **0／1／0**。新增合法字符串相等节点真实执行，原1 F2P与38 P2P均保留。一个不影响本题40项参考评分的parser缺口见下文；本报告不宣称训练资格，不改原reward。

审查者不是本轮材料或runner作者，已读私有测试、gold、validate_construct、正式原始日志与既有静态审查，因此**不是fresh公开读者**。按[三方流程](../../../coordination_workflow_20261003.md)及[实验量规则第3节](../../../remaining_workflow_20261002.md)接续已有证据，仅审6283本轮正式作业与必要的公开actor身份复用，没有重新全题审查或复做旧矩阵。未连接SSH、启动Docker、安装依赖、调用模型、运行项目测试或作者自动检查脚本；本地只使用标准库读取、SHA256、JSON、AST抽取冻结parser函数、canonical digest、base64及逐文件census比对。仅新增本报告与[机器可读核查摘要](non_author_6283_cpu_review_20261003.json)，未改共享文件或发送跨线程消息。

## 固定身份与原件

作业为 `pyd6283-formal-20261002185959-dbe65`，[作业回执](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/jobs/swe_pydantic/pyd6283-formal-20261002185959-dbe65/status.json)记载2026-10-02 19:00:03–19:08:38 UTC、cpu-a作业槽0、`runtime_cpu_v2`、`--execute`、退出0，stderr为空。[本轮status](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd6283-formal-20261002185959-dbe65/status.json)与[作者结果清单](../cpu_acceptance_20261003/results.json)绑定同一job；后者375项归档文件的路径、字节数与SHA已逐项独立核实一致。job stdout／stderr另核，stdout只记矩阵执行完成。

- R7：`cat2-cpu-r2e088-swe12-git-20261003-v1`；外部manifest SHA `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`。本地冻结发布905成员的大小、SHA、无软链及精确文件集合均独立核实，实际远端部署事实接续[部署清单](../../../cpu_release_deployments_20261003.json)，没有进行新远端复验。
- [固定输入](../cpu_acceptance_20261003/formal_inputs.json) SHA `14c66d454ea7e1f83e6bde849b2431d9b976162aec86024d706f55ba4ce48097`；[runner](../cpu_acceptance_20261003/run_formal.py) SHA `8c1c055957535012df0fbed9e7404592d0c8badacadee32042171702ad8d41f4`，与作业status相同。6283六项输入资产SHA全相同；[revision](../tasks/pydantic__pydantic-6283/revision.json)仍为 `ee160fac81c3ad8776bed31b31f53ff9cc12a1e81377770d4632bda0b9275ff4`。
- 本轮prepared manifest、公开两份JSONL和私有host grading的SHA链相符；host消费的有效测试补丁SHA为 `785d1d6ccdbb74a141c4178f84c21ebd69e6a68ef3a57b04ab1682ee7626bc26`，F2P／P2P逐ID与输入一致，激活 `pyd6283-behavior-v1` 和独立安装资产 `pyd6283-e10-v1`（资产SHA `6e50864b8f8976413f6fb32df2fd11060e1b190fb4161c8567810ac748e6a570`）。
- 公开digest `sha256:d2d8b998296f14d164a024519603119def49bbc9ba84fad05b7a5c0eebceddc5`；prepared／host／各行revision的环境digest均为 `sha256:1087783fda3557fd5172706ee58a240d243c561974f4a1c860e797f384562f16`。材料身份依冻结代码定义独立重算为 `sha256:c5f9d60ac1fc4d16d58bfe606e2d6a6c9215a0ae442ae84430b815ba000bfeae`，与spec、ledger和diagnostics一致。

## 原始结果与失败归因

F2P是待修复节点，P2P是必须保留的回归节点。以下分母仅为正式参考：2 F2P＋38 P2P＝40；测试文件实际收集45节点。

| 候选 | 原reward | F2P通过／2 | P2P通过／38 | 新字符串节点 | 测试退出 |
| --- | --- | --- | --- | --- | --- |
| noop | 0 | 0／2 | 38／38 | FAILED | 1 |
| gold | 1 | 2／2 | 38／38 | PASSED | 0 |
| validate_construct | 0 | 2／2 | 36／38 | PASSED | 1 |

noop失败在真实相等断言：原42节点第313行与新增 `TextRoot('another') == TextRoot.model_construct('another')` 第498行。gold没有普通失败。validate_construct的两项失败均为旧P2P：`test_construct`／`test_construct_nested` 在可信Base64字符串 `'test'` 上错误重新验证，堆栈经过 `root_model.py:61 → main.py:194 → cls(values['root'])` 并抛ValidationError。这是候选违反无验证构造行为，不是依赖、收集或基础设施异常。**它早已被旧P2P拒绝，本轮不构成新发现的漏奖；新增字符串节点也不负责拒绝它。**

三份真实安装都打印唯一 `RH2_INSTALL_RC=0`，无失败命令，执行editable安装及按候选pyproject导出的测试依赖安装。测试退出分别1／0／1，候选exec均退出0且有完整测试结束标记；脚本最后输出时间标记，所以exec退出0不能单独代表测试通过。完整report的resolved／unresolved、`tests_failed`、F2P／P2P计数与原始逐ID结果一致，`infra_failure_detail`／`execution_failure_stage`为空，没有安装、超时、baseline或清理失败冒作0分。

[noop账本](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd6283-formal-20261002185959-dbe65/noop/ledger.jsonl)、[gold账本](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd6283-formal-20261002185959-dbe65/gold/ledger.jsonl)、[validate_construct账本](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd6283-formal-20261002185959-dbe65/validate_construct/ledger.jsonl)与各目录 `report.json`／diagnostics逐项对照。原始日志SHA及byte_size均与report和ledger相符，候选exec的stdout完整包含于归档eval log，测试段逐字相同。

| 候选 | 原始日志 | 字节数 | SHA256 |
| --- | --- | --- | --- |
| noop | [evallog_replay-pyd6283-formal-20_f338117b.eval.log](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd6283-formal-20261002185959-dbe65/eval_logs/evallog_replay-pyd6283-formal-20_f338117b.eval.log) | 369083 | `6ef2cb21fbc6c08e54c758626edff4dc1f7a127d796c30a7a8fc246f844ea6b6` |
| gold | [evallog_replay-pyd6283-formal-20_cdff58ef.eval.log](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd6283-formal-20261002185959-dbe65/eval_logs/evallog_replay-pyd6283-formal-20_cdff58ef.eval.log) | 367723 | `267f58e6ce388fc29cd42f678a36f5fc004a6cf8d4c053c68f71107540388822` |
| validate_construct | [evallog_replay-pyd6283-formal-20_f495cc29.eval.log](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd6283-formal-20261002185959-dbe65/eval_logs/evallog_replay-pyd6283-formal-20_f495cc29.eval.log) | 370356 | `85adea1cd5878eae6c04a00220f45d719b9ab701886886ec61b9367c447650fa` |

## parser完整性的通过范围与一项非阻断缺口

每份日志各有唯一Start／End测试标记，没有收集错误或零测试。独立按完整节点名逐行核：noop／validate_construct实际各40 PASSED＋2 FAILED＋3 XFAIL；gold实际42 PASSED＋3 XFAIL。**40个正式参考全部是明确PASSED／FAILED，没有missing、skip或unaccounted**；原F2P、新F2P、原P2P三个分区与ledger／diagnostics的success／failure集合完全相同。

另用AST仅抽取冻结发布的 `parse_log_pytest_pydantic` 函数，在相同原始测试段中复算，结果与作者 `review.json.states`相同。该parser返回42个键，其中40个正式参考正确，另两个非参考节点存在确定缺口：

- `test_root_model_specialized[dict[int, bool]]`；
- `test_root_model_inherited[dict[int, bool]]`。

两项原始日志均PASSED，但parser按空白拆词，把键截断为 `…[dict[int,`，把状态记为 `bool]]`；三个预期XFAIL也没有计入parser结果。**因此`num_parsed_tests=42`不能表述成42个有效终态或全45节点解析完整。** 本题正式参考列表不包含这两个dict参数节点，也不包含三个XFAIL，当前binary评分完全由已核的40项决定，故这不是6283普通GPU探针的阻断。题主应保留此共享parser缺口，若以后纳入这些参考，须先修parser并做受影响验证；本轮不修改consumer或reward。

该缺口标记为 **production_observed**：本轮真实 `ReplayGrader → SWEGradingManager → 测试段parser` 路径已产生上述截断键，归档状态与冻结函数独立复算一致。文件位置为 [冻结swegym_parsers.py](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_088_swe12_git_candidate_v1/repo/rh2/src/repoharness2/envpack/swegym_parsers.py) 第78–82行。最小复核输入为 `tests/test_root_model.py::test_root_model_specialized[dict[int, bool]] PASSED`，同一函数实际返回键 `…[dict[int,`、值 `bool]]`；应保持完整节点名并返回PASSED，不能以parser字典长度代替有效终态数。影响限于当前两项非参考结果的记录，未来将其纳入参考会产生错误缺失或误分风险。

建议分期为 `deferred_with_owner_and_gate`，此为审查建议，尚未代表维护者已接受：共享parser归发布线程维护，题主跟踪；**纳入带空格节点参考前**须修复并验收。修复验收应覆盖完整参数ID、PASSED／FAILED及含百分比的真实行，确认输出键／状态正确，按受影响路径回归既有40参考及错误候选，保留原运行分数；不要求6283为本次递延重跑旧矩阵。

## 精确运行、FrozenPatch与清理

原基础镜像为 `sha256:24e9c51fedb7dc930796362c90f72e8e7a9c47d9362fa72414c6c6ff8a1a2882`，实际候选和grader均使用 `sha256:58d0c004cec144834a01dfc160c0f4caf427a9b31fd5ad95a60d03f6f3623226`；image inspect、run argv、各行ledger、FrozenPatch和源码观察一致。105个Docker调用原件均有完整退出记录且退出0；run参数保留断网、2 CPU／4 GiB／PID512，容器内cgroup实读 `200000 100000`、`4294967296`、`512`。

额外源码观察在正式post观察之后，以同一grader UID54322执行；其JSON与对应Docker stdout相同。三行均为 `/opt/miniconda3/envs/testbed/bin/python`、Python3.8.19、core0.42.0，包从 `/testbed/pydantic/__init__.py` 导入，`pydantic.main`／`pydantic.root_model`均导入 `/testbed` 内实际源码。main.py的SHA分别为 noop `627bf18d6c5b6b7d204c4a97fc70316c7290aeda77d2984ab9e19005f1bc261d`、gold `2a6ba2b34275a9b41065e958e62762160ba675be037e77211a1319bd3e624c3f`、validate_construct `709ba1bfe57c25dedf580245afbd2b10dad41f84b9e1db56424e8239fdc3ba3f`；root_model.py均为 `d1cdddb080df67eae718e31ea89c56e1ccf76bd7ca5e3cd1a6f5ab878691309d`，与固定候选一致。

七段保存脚本的SHA与spec相同，实际stdin传入的trusted_setup／test脚本也逐字相同。三行真实setup attest均确认原测试恢复、基线SHA正确、补丁应用0、1文件存在。执行后有效测试文件SHA为 `d50d61ef9552dec427be4515accb87b96d4ed24180aa6cec151f70bf72457d19`、owner root且UID54322不可写；runner前后digest相同。该检查不宣称全部控制面安全验收。

每行各有一份FrozenPatch与**完整391文件baseline**，不只两个源码哈希。按canonical JSON独立重算baseline digest `sha256:0143226df9f52b56a3921127ed7ef0cb3b56c11b3eea232418cfffc9ab35e0ef`、policy与排除路径摘要，分别与每份候选容器及fresh grader的完整census逐文件比较，路径／类型／mode／内容digest完全相同，未省略cache。FrozenPatch的task、public、runtime image、base HEAD与各自physical attempt一致；noop delta为空，另两行只改main.py，base64内容摘要、冻结digest与projection一致。实际运输stdin等于冻结文件内容，随后真实import SHA一致，未重绑旧工件。

baseline中的 `environment_package_digest` 仍为null；本轮已核的是prepared／host／revision环境身份及完整基线运输，不能把该字段空缺写成完整环境lineage或训练准入已完成。它不改变本次普通CPU矩阵的40参考结果。

候选容器在Docker调用0011／0046／0081删除，grader在0033／0068／0103删除，六次rm均退出0、stdout为对应容器名且stderr为空。manager close记3创建／3删除、open与supply为空、cleanup_failures为空；最终状态ok／退出0。0104／0105按本run标签查询容器／网络，命令退出0且输出为空，支持**归档时本run零残留**；本次只读审查没有新现场查询，不外推其它作业或以后状态。

## 公开actor复用与用途边界

纯私有测试变化的公开依据与断言适用性接续[既有非作者静态窄核](non_author_5662_6283_review_20261003.md)。本轮与旧actor的 `rollout_task_views.public`（包括题面、public_hints、base、镜像）逐字段相同、public digest相同，故按身份复用既有开发证据，不要求新公开读者。

必要窄核读取旧job `pyd6283-actor-v1-20261002T173908Z-652bc` 的原件：[首请求](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/diagnostics_v1/outputs/pyd6283-actor-v1-20261002T173908Z-652bc/actor/stub/requests/messages_000.json)确实包含原题面及public_hints，prompt和请求SHA与诊断相符；四个请求由**固定桩响应**驱动三条预定公开命令。UID54321／Python3.8.19／core0.42.0／base main.py SHA与源码可写性命令通过；公开示例按已知基线问题失败，已有公开测试41 passed／3 xfailed。它证明这三条公开开发路径、CC交付与收尾，**不是实际模型求解或新测试评分**，没有FrozenPatch导出，也未执行BASH_ENV专用写入拒绝探针。旧报告对应False保持原义，不因本审查转为全startup通过。旧基础设施缺torch的零请求失败不计题目0分。

本轮prepared的prompt行本身只含issue，public_hints仍在公开view；旧actor首请求是显式issue＋hints交付的原事实。这里复用公开材料身份，不冒称已看到R7的新CC首请求；实际GPU执行者仍须按固定公开入口交付并记录真实首消息。私有gold、反例、断言与本报告不应进入solver上下文。

**当前用途：6283可按固定材料提交普通GPU探针，观察真实求解后的候选与评分运输。** 本报告没有完成GPU部署兼容验证、真实模型尝试、训练／留出资格或RL信号判断，也没有新增审批。[题卡](../tasks/pydantic__pydantic-6283/card.md)和离线revision的准备阶段状态属于旧快照，当前运行事实以本轮原件为准；本报告未改其历史内容。

## 附：40项正式参考逐ID结果

下表ID均带同一前缀 `tests/test_root_model.py::`；三列来自原始执行行，已逐项对照正式parser和参考分区。

| 参考ID后缀 | noop | gold | validate_construct |
| --- | --- | --- | --- |
| test_root_model_equality | FAILED | PASSED | PASSED |
| test_root_model_construct_equality_nonexample | FAILED | PASSED | PASSED |
| test_root_model_specialized[list[int]] | PASSED | PASSED | PASSED |
| test_root_model_base_model_equality | PASSED | PASSED | PASSED |
| test_construct | PASSED | PASSED | FAILED |
| test_assignment | PASSED | PASSED | PASSED |
| test_validate_assignment_false | PASSED | PASSED | PASSED |
| test_validate_assignment_true | PASSED | PASSED | PASSED |
| test_root_model_nested | PASSED | PASSED | PASSED |
| test_root_model_inherited[InnerModel] | PASSED | PASSED | PASSED |
| test_root_model_in_root_model_default | PASSED | PASSED | PASSED |
| test_root_model_wrong_default_value_without_validate_default | PASSED | PASSED | PASSED |
| test_root_model_as_attr_with_validate_default | PASSED | PASSED | PASSED |
| test_root_model_nested_equality | PASSED | PASSED | PASSED |
| test_root_model_default_value | PASSED | PASSED | PASSED |
| test_root_model_repr | PASSED | PASSED | PASSED |
| test_construct_nested | PASSED | PASSED | FAILED |
| test_v1_compatibility_serializer | PASSED | PASSED | PASSED |
| test_root_model_as_field | PASSED | PASSED | PASSED |
| test_root_model_specialized[str] | PASSED | PASSED | PASSED |
| test_root_model_with_private_attrs_equality | PASSED | PASSED | PASSED |
| test_model_validator_before | PASSED | PASSED | PASSED |
| test_root_model_literal | PASSED | PASSED | PASSED |
| test_root_model_inherited[list[int]] | PASSED | PASSED | PASSED |
| test_root_model_dump_with_base_model[RB] | PASSED | PASSED | PASSED |
| test_root_model_inherited[int] | PASSED | PASSED | PASSED |
| test_root_model_default_value_with_validate_default | PASSED | PASSED | PASSED |
| test_private_attr | PASSED | PASSED | PASSED |
| test_nested_root_model_naive_default | PASSED | PASSED | PASSED |
| test_root_model_json_schema_meta | PASSED | PASSED | PASSED |
| test_root_model_inherited[str] | PASSED | PASSED | PASSED |
| test_root_model_recursive | PASSED | PASSED | PASSED |
| test_root_model_specialized[InnerModel] | PASSED | PASSED | PASSED |
| test_root_model_validation_error | PASSED | PASSED | PASSED |
| test_root_model_specialized[int] | PASSED | PASSED | PASSED |
| test_root_model_default_factory | PASSED | PASSED | PASSED |
| test_root_model_default_value_with_validate_default_on_field | PASSED | PASSED | PASSED |
| test_model_validator_after | PASSED | PASSED | PASSED |
| test_nested_root_model_proper_default | PASSED | PASSED | PASSED |
| test_root_model_dump_with_base_model[BR] | PASSED | PASSED | PASSED |
