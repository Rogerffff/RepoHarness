# getmoto__moto-5960 对照复审

结论：同意 `needs_review / static_review`、用途 `development_diagnostic`。明确公开要求GSI KEYS_ONLY scan没有进入新增判据，同名P2P只做query；gold沿已读核心路径合理，未发现具体核心漏修。索引scan后数据保留漏测、LSI范围疑义、参数节点身份合并各自保留，不能合并为已证错误奖励。主CPU方案选“遗漏GSI KEYS_ONLY分支是否仍获原分”的一项受控诊断；本轮只建议、未执行。

独立性：本人initial SHA256=`0b4e64757dc4c348ef5e1f9a4f63672598335d8c126d89ab108731a612430afe`。root于2026-09-20T22:03:11.721133+00:00确认整包封存并明确放行后，才读取本题public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json及history/refs.json指定唯一旧单题记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_2/records/getmoto__moto-5960.json`。未追其mat、repo_level、stage1、216题材料或聚合。initial未回写；环境摘要已有gold/noop结果暴露，不能称结果盲审。纯静态文本/源码/已有日志/stdlib JSON/hash，没有项目import/执行、测试、安装、网络、Docker/SSH、模型或配额操作。

路径：ROOT=${REPO_ROOT}；P=ROOT/runs/swegym_quality_batch03_20260921_v1/public/getmoto__moto-5960；V为对应private；E=ROOT/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-5960。原件SHA、源码及展开函数范围沿封存initial。

## 八方面对照及决定性判断

| 方面/主张 | 判断 | 证据与实际边界 |
| --- | --- | --- |
| 公开要求与开发材料 | 同意公开两GSI模式明确，核心材料齐全 | user_prompt分别给INCLUDE三项、KEYS_ONLY六项的自包含例子；helper/query模式公开可查。题面报告者Python/Moto版本不是当前环境实测或强制升级目标。完整静态bundle不能证明实际actor消息未丢失。 |
| base初态与版本绑定 | 同意 | scan选择索引项但未project；本题base/grading/prepared/gold字符串绑定已在initial核对。历史noop两F2P多出未投影属性，是目标业务失败，非依赖异常；公开第二GSI原例没有历史实跑证据。 |
| 全新增断言与F2P | 同意缺口 | 全test.patch仅对GSI INCLUDE、LSI KEYS_ONLY旧query函数追加scan，再比较items[0]完整字典。没有新helper/fixture，旧query断言保留；没有scan长度、全部项或后续存储复读。两个F2P已逐体展开。 |
| P2P及真实展开范围 | 同意严分名单、函数、执行节点 | 155个P2P参考名单全读，实际展开相关scan/projection/filter/query/index/pagination函数，详见initial。GSI KEYS_ONLY P2P只query；1MB和gsi_lastevaluatedkey也为query。其它公开文件scan_by_index是ALL，且不在正式命令/引用；不能计入本题158节点。 |
| 合理替代及LSI范围 | 同意保留疑义，不直接判误拒 | 断言是外部字典结果，不强制index.project/deepcopy位置。只修GSI符合issue狭义字面，但新LSI F2P会区分它；公开SecondaryIndex.project文档及旧LSI query支持统一抽象，不能以gold便利性直接裁定所有GSI-only路线不合法。范围问题需依据公共契约澄清，CPU本身不决定其规范地位。 |
| gold/调用链/旧行为 | 同意有限正确性判断 | response→backend→Table.scan→project→Item.filter和trim已查。gold先deepcopy、逐项project，保留表键/索引键、原存储及后续分页键。普通核心路径未见漏修；FilterExpression引用非投影属性、Select和大项尺寸组合仍未穷举，不能凭query相同顺序认证全部AWS语义。 |
| 环境、交付与评分 | 同意，仅历史grader | 原make init真实两轮editable完成；精确官方恢复test_dynamodb.py，test_globs=()；普通源码修复可投影。原harness来自冻结tar成员，不是当前ROOT/rh2。原退出码、执行节点、解析键、参考结果分账，正式actor另待验。 |
| 关系、暴露与用途 | 维持开发诊断，有限关系证据升级见后文 | 本人已见test/gold/原结果和授权旧结论，不能当本题新solver。没有真实模型、重复稳定性或费用观测。源码包含关系不等于任务重复/实际泄漏；未批准训练或正式评测。 |

GSI KEYS_ONLY scan缺口是直接需求—断言映射，不依赖旧记录才能成立。遗漏该分支但保留INCLUDE/LSI、以及省掉复制的两种部分实现，都是有源码依据的预测；未运行原评分，不称已证满分反例。省掉复制时Item.filter的原地pop会影响存储，gold已用deepcopy避免它，所以这是验收保留数据的缺口，不能列作gold缺陷。

本人与主审业务初判一致。public_read对LSI曾明确“不应作为唯一合法实现”，主审及本人均保留为范围问题；旧记录的“实践上不构成额外要求”过于确定，赞同delta收窄。record中black-box检查的pass只能指没有内部实现身份约束，不代表已经验证全部合理替代方案不会被拒绝；gold检查的pass也以该record写明的核心范围为限。

## 历史差异、本人撤回与证据分级

同意delta对旧记录的主要修正：只改moto/没有当前普遍白名单依据；public_hints的NON-TEST指令与精确hygiene不同。旧make init rc2不适用于最新本题两条install_wave1原运行。旧“所有155 P2P各自建表，因此全绿”超出了实际逐体核查，且其next_experiment仍是预期，不能当执行证据。旧test_dynamodb.py::test_scan_pagination引用错误，本轮实际公共分页函数在test_dynamodb_table_without_range_key.py:505–524；不在本题唯一官方命令。旧hints致谢、无泄漏、ready_for_probe和18分钟成本不承袭，也未沿旧链接补证。

**撤回本人initial第62行对真实管线的过强可能性描述。** 当时写“将来混合状态可能后者覆盖前者”。字典last-write机制确实存在，但不能用参数声明/执行先后推导本题pytest -rA的汇总先后。现在直接核N原日志：887–1042全部PASSED在前；1043–1044两个FAILED在后。两个合并节点在1009–1010均PASS。按本题这个汇总顺序，同键FAILED不会仅因另一个节点的PASSED而被覆盖成通过；不能把任意摘要顺序的假设写成这轮观察或已证奖励风险。主审初稿和delta对此已采用正确限定，接受这项对本人初判的修正，initial仍封存不改。

确证事实保留：两完整参数名`test_set_attribute_is_dropped_if_empty_after_update_expression[use attribute name]`与`[use expression attribute name]`经冻结parser的split()[1]同映到`[use`，158实际节点→157解析键→F2P2+P2P155参考键。G原日志756–757和N1009–1010两节点均PASS；两条运行无skip或参考缺席。合并键仍无法分别证明各真实节点的身份与出席；reference_missing/reference_skipped只检查合并键，如果将来一个节点没有独立可识别状态，另一节点的PASS不能证明它也运行。skip摘要形状/顺序及混合缺席在本轮无观察，因此只记录剩余核验边界，不声称已证错分，不在本轮改parser/ref/reward。

原运行观察与新推断分开：G命令583、collect589、summary790为158 passed、rc0（794），ledger F2P2/2、P2P155/155、reward1；N命令561、collect567、summary1045为2 failed156 passed、rc1（1049），ledger F2P0/2、P2P155/155、reward0。N新增scan断言分别多出nonProjectedAttribute和someAttribute，解释真实分差。原pytest rc1不是奖励定义；冻结scoring只以marker内解析状态及参考决定结果。本轮stdlib摘要复核158行/157键和PASSED→FAILED顺序，未执行项目parser。

主审封存稿mem峰值的MiB/MB文字已在delta撤回。最终只保留原字段resource.mem_peak_mb=252.594/297.359，resource_facts=null；不换算，不据此认证actor资源。源码推断不会因历史作者和两位审查者一致而升级成实跑；复制安全与公开GSI两模式的静态合理性，也不能当成所有参数组合的正确性证明。

## 选定的一项主CPU方案

目的只聚焦I1：确定“遗漏公开GSI KEYS_ONLY scan是否仍得原满分”。在绑定冻结条件的同一诊断中，以精确base/gold作控制，再加入一份仅跳过GSI KEYS_ONLY投影、保留复制与INCLUDE/LSI处理的最小部分实现；这份候选有明确鉴别目的，当前没有生成或运行。分别保留原正式文件的原F2P/P2P、完整节点状态、解析键、退出码和reward；另行执行公开两个GSI原例，对全部项与总数检查，重点为KEYS_ONLY六项。预期部分实现可能原reward1但公开KEYS_ONLY失败，尚待运行验证；若不符，先追具体旧节点/分支而非修改参考。

可在相同诊断fixture中记录索引scan后get/无索引scan的原数据完整性，以防实验候选意外引入I2；不为此再强制制作“去copy”第二候选。LSI范围澄清、解析迁移和全量分页/Select探索都不混入主实验。该方案比只有base/gold直接复现多一个有因果用途的候选，用于量化评分充分性；不要求机械双候选。所有补充断言保存在另版诊断输出，不改冻结gold/reference/reward/expected。

## 原环境与重放入口边界

install_wave1原spec未被recipe/materials/reference binding覆盖：make init、Python3.12、pytest -n0 -rA仍适用。COPY wheels和PIP_NO_INDEX/PIP_FIND_LINKS只是准备方式；G日志414起及N392起真实两轮build/install成功才证明这两次安装执行。pins setuptools72.1.0/wheel0.43.0/packaging24.1；派生image=sha256:5e8dbd0f9789953dad4712fb86d4b1fbb1058b41ccd279d27f16ad7d62c49860；scripts_digest=sha256:5fade887f26755d6f0215bfdb327623a2aa0fc57da1041b917d8602bcd0de179。历史import /testbed/moto/__init__.py、4.1.4.dev与metadata4.1.0.dev0分账，不能因版本显示不同单独判错包。

原prepared副本仍指/work，未来需另建重定位summary/manifest并核目标机镜像、冻结baseline code-root/Python依赖，以新run_id和输出重放；不覆盖原文件。原status仅捕获最后gold命令，noop凭launcher和原日志，不能夸成status含两次完整命令。当前image可用性、原wheel payload/context仍有准备缺口，不假定联网可取或任何镜像ID文本即可运行。

固定grader语义CPU诊断不自动以正式actor资格为前提；模型开发仍须单独验实际actor的UID/HOME/cwd/PATH/解释器、导入/编辑权限、CLI消息、工具与镜像消费。已有grader rh2grader/54322、candidate apply agent/54321、env_qualification=absent均不代替它。原资源字段cpus=2.0、memory_bytes=4294967296、pids_limit=512、shm_bytes=67108864、tmpfs_bytes=1073741824、network=deny_all保持；未申请资源扩大或额外排除。公开进程内mock不要求真实AWS、DynamoDB Local或Docker daemon；这也不证明正式actor当前可用。

## 同包公开源码关系与最终范围

root在对照阶段提示后，本人核读所分配三题的精确原件：5960 gold的scan deepcopy+index.project核心逐行存在于6185公开base的moto/dynamodb/models/table.py:846–850；6408同文件839–842保留复制和投影，但已改为返回值列表推导，不能称字节相同。另6185 gold的attr参数/递归/主键条件完整存在于6408同文件487–504。它们使“未核关系”升级为公开base包含早题实现及后续演变的有限证据；不支持旧记录仅凭同文件/不同函数断定非派生，也不直接证明Git祖先、重复题或真实solver已泄漏。

新增阅读范围为自己五份对照材料、指定唯一旧记录、N原日志885–891/1005–1014/1038–1049及全摘要的stdlib计数、initial第62行原文，以及已分配三题精确源码/gold关系片段。screening_record较长输出一度截断，随后补读缺失checks7–10。没有本包三题之外的质量资料、旧聚合或外部规范。其余未展开P2P函数、全部SDK/core、特殊键/filter/Select/大项组合、正式actor、当前资产、稳定性及模型成本继续未知。只写本review；所有initial、源/tests/gold/reference/reward/expected保持不动。
