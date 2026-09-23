# getmoto__moto-5960 独立初判（封存后不回写）

状态`needs_review`，范围`static_review`，用途`development_diagnostic`。本稿先于任何本题public_read、主审初稿/delta/card/record和旧质量结论；纯静态，只读文件/日志/源码，stdlib文本/JSON/AST定位/哈希，未执行项目、测试、安装、Docker、网络、模型。

ROOT=${REPO_ROOT}；I3=ROOT/runs/swegym_quality_batch03_20260921_v1；IW=ROOT/runs/env_recipe_repair_20260919/install_wave1。源码引用均为I3/public/getmoto__moto-5960/base。

独立初判：公开GSI投影问题与base对应，gold沿已存在的query投影模式修复scan，历史两项F2P的失败/通过也解释清楚。主要质量限度是题面明确GSI INCLUDE和GSI KEYS_ONLY，而新增评分实际为GSI INCLUDE与LSI KEYS_ONLY；冻结P2P中的GSI KEYS_ONLY只做query，不能补上scan缺口。还未专门保护索引投影后原表数据保留。可以作为有限范围的开发诊断静态候选，但不得把reward1解释为题面两种GSI scan均已验证；优先补窄CPU语义检查。未据LSI字样直接判误拒或认定gold有错。

## 1. 独立性与材料身份

已读共用四份方法文件，本题公开user_prompt/public_bundle/base_identity/environment_brief，私有test/gold/grading/validation/source_refs/run_refs/environment_record。inventory只读common、families.install_wave1及所分配三题exact项。environment_record自带verified_environment_pair、gold/noop结果摘要和history运行指针，已见到并披露；不称无结果盲审。未追analysis_reference/analysis_149，未读本批聚合、其它题和任何主审/公开读者/旧质量记录。

base=`d1e3f50756fdaaea498e8e47d5dcd56686e6ecdf`，tree=`1a036474ade83906dcb02e8a99e452d10a5fad39`；公开与评分包身份相同，base_identity记录blob/OID/mode/path校验。无.git、Terraform子模块未物化，本题窄Python测试不依赖该子模块。gold与validation patch字符串相等，test.patch与grading.test_patch相等；gold SHA=`df2af6b800578dc24b6ef33c396677683d766702734f44d506248354147b7af9`被原候选账本引用。

精确选取原prepared_manifest本题项，canonical SHA=`e1d1e0b62782454ce5f80264c0a96866c4f2dbcf6503f7161ff32a2f93c4872c`；原host_grading_views第79行raw SHA=`5431a78f3647a43bce119bd728cbae65afcfb03650b36972d1372e35f5a3e2a5`，其grading与冻结私有材料相同。未打印原prepared全tasks/files。

## 2. 需求与全部新增断言

公开要求：对GSI scan遵守ProjectionType；INCLUDE仅返回表键、索引键及NonKeyAttributes，KEYS_ONLY仅返回键。题面两个完整pytest例分别用GSI INCLUDE（id/attr2）和GSI KEYS_ONLY（id/seq）；预期不是任意过滤列名、修改存储或只修query。

| 需求/旧行为 | 公开依据和源码 | 评分断言 | 覆盖结论 |
| --- | --- | --- | --- |
| GSI INCLUDE scan | 题面第一例；SecondaryIndex.project:39–60 | F2P test_gsi_projection_type_include新增scan(IndexName=GSI-INC)，items[0]完整等于四属性字典 | 覆盖；键与索引键不同，比题面更能区分遗漏索引键 |
| GSI KEYS_ONLY scan | 题面第二例明确要求；project已有KEYS_ONLY分支 | 没有新增对应scan；P2P test_gsi_projection_type_keys_only:4609–4654只调用query | 明确未直接验收，不可用同名P2P或LSI断言替代 |
| LSI KEYS_ONLY scan | 公开旧LSI query测试；project文档标注LSI/GSI；scan共用get_index | F2P test_lsi_projection_type_keys_only新增scan(IndexName=LSI)，items[0]完整等于table hash/sort和LSI sort三键 | 是额外相关要求；可由公共共享接口合理发现，仍需说明不等于题面第二例 |
| 投影只改变返回值，原表数据不丢 | 公共test_basic_projection_expressions_using_scan:529–533、nested scan:762–775明确保留存储 | P2P验证无IndexName时ProjectionExpression不破坏数据；F2P无索引scan后get/scan检查 | 部分；gold的deepcopy正确保护，错误的原地index.project仍可能逃过 |
| 保留查询语义和ALL投影 | 公共query已有copy+project:749–764；旧测试 | 两F2P先运行原query断言；P2P GSI KEYS_ONLY query；部分ALL索引/显式投影 | 覆盖部分现有路径；未验证所有Select规则 |
| Limit/ExclusiveStartKey/LastEvaluatedKey | _trim_results:860–905；旧execution_order测试 | P2P projection_expression_execution_order含ALL GSI scan Limit=1；filter_expression_execution_order含表scan两页 | 部分；无新增KEYS_ONLY/INCLUDE多页扫描 |
| 稀疏索引/无索引错误 | has_idx_items:788–800；scan错误检查814–815 | P2P test_scan_by_non_exists_index；其它公开文件test_scan_by_index有稀疏/分页 | 后两文件未进入本题正式命令和冻结参考，不能计作本次P2P覆盖 |

test.patch全部内容已读：在两个既有函数各追加一次scan和items[0]完整字典相等，共两个新断言，无新helper/fixture、无源码混入。完整读两个F2P原函数/装饰器、schema、put/query、旧len=1和原值断言；新scan不另assert总长度，但单个预置item和现有扫描行为限制了范围。fixture只用mock_dynamodb及内联表定义，没有云资产。

冻结P2P155项全核名单和原日志状态，未声称读完155个函数。实际完整展开本文件P2P：test_gsi_projection_type_keys_only；test_basic_projection_expressions_using_scan、test_nested_projection_expression_using_scan及两个with_attr_expression_names版本；test_scan_filter、test_scan_filter2/3/4、test_scan_filter_should_not_return_non_existing_attributes、test_bad_scan_filter；test_scan_by_non_exists_index；test_dynamodb_max_1mb_limit（实际是query）；test_gsi_lastevaluatedkey（也是query）；test_filter_expression_execution_order；test_projection_expression_execution_order。另读本文件imports/部分参数化尾段；从两个相邻公开文件完整展开test_scan_by_index（with_range_key:1050–1148，without_range_key:528–577），它们是相关公开回归证据，未计入冻结P2P或历史实际158节点。

## 3. gold、调用链和误拒分析

读Table.query/scan/all_items/all_indexes/get_index/has_idx_items/_trim_results、SecondaryIndex.project及两Index类型；读DynamoDBBackend.scan:343–373、DynamoHandler.scan和_adjust_projection_expression:729–800、Item.filter:397–411和DynamoType.filter:66–86。

base的scan已按IndexName选择具有索引全部键的items，却未做index.project。gold在结果列表形成后deepcopy，再对每个result用get_index(index_name).project，随后_trim_results、FilterExpression、ProjectionExpression；与公开query既有实现一致。index.project保留全部table和index键，因此在普通名称上不会因KEYS_ONLY破坏LastEvaluatedKey所需索引键；显式ProjectionExpression仍在分页键计算之后。deepcopy防止Item.filter的pop写回self.items。这是源码推断，不是本轮执行，也不证明所有非默认分支。

合理非gold实现可在scan构造返回Item时选取允许attrs，或只对会投影的索引复制，再保留分页与显式projection顺序；无需调用特定helper或使用deepcopy。新增字典等式检查外部属性集合和值，未限制内部结构、排序或Mock调用。

LSI范围需谨慎：只对GlobalSecondaryIndex做完整INCLUDE/KEYS_ONLY scan修复的实现会满足题面两例，却可能失败新增LSI断言；这是可复现的“字面题面范围与评分范围”差异候选。另一方面，公开SecondaryIndex.project明示LSI/GSI、公共旧LSI query测试和scan共用索引接口足以提示一般索引投影契约。当前不直接判测试无效或已确认误拒；协调时应明确接纳范围，不能把隐藏LSI要求当题面原文。

可解释的漏测候选：只给INCLUDE的GSI和LSI执行project、跳过KEYS_ONLY的GSI，则两新增F2P可被满足而题面第二例仍错；或对原Item直接project但不复制，索引scan后原表非投影数据丢失，而现有无索引ProjectionExpression P2P仍有原有复制保护。两者均是静态候选，未执行、未证明reward，不能报“漏洞已复现”。

Select非默认行为保留未知：responses.scan未将Select传给backend，已读P2P test_scan_filter2只在普通表Select=ALL_ATTRIBUTES核Count；未核LSI显式ALL_ATTRIBUTES与索引projection的完整契约。避免把base既存未实现项一律算gold新错。也未穷举特殊属性名、全部索引组合和资源上限。

## 4. 历史运行和评分口径

原件：IW/tasks/getmoto__moto-5960/{gold,noop}/ledger.jsonl第1行、driver.log；gold eval=`evallog_replay-er19-iw1-getmoto__f12bdab3.eval.log`，SHA=`a942c7ed9cc6c9b64e3340b6a42b14794a2cd4c3a121ebffa23cb9aa20b7164e`；noop eval=`evallog_replay-er19-iw1-getmoto__a9c21d90.eval.log`，SHA=`2d79bc1c50c4df481bc39bd1e16e765f52f8a572894333c94ac35bba88b6ff2b`。完整日志与ledger重算hash均与run_refs一致。

| 层次 | gold | noop |
| --- | --- | --- |
| 实际命令 | 日志583：pytest -n0 -rA tests/test_dynamodb/test_dynamodb.py | 日志561同命令 |
| 实际pytest | 589收集158，790摘要158 passed | 567收集158，1045摘要2 failed,156 passed |
| 失败含义 | 两F2P均PASSED（754–755） | 689/826的新增scan字典等式失败；712–715多nonProjectedAttribute，844–847多someAttribute |
| 解析键与冻结参考 | 157键；F2P2/2、P2P155/155 | 157键；F2P0/2、P2P155/155 |
| 测试退出码/奖励 | RH2_TEST_RC=0（794），reward1 | RH2_TEST_RC=1（1049），reward0 |
| 安装 | make init414，build deps done418/460，build+install450/456、564/570，RH2_INSTALL_RC=0 | make init392，done396/438，build+install428/434、542/548，末码0 |

用stdlib逐行对照摘要与冻结参考，158状态行→157键，两份日志155 P2P均PASSED，无缺键。差异来自 `test_set_attribute_is_dropped_if_empty_after_update_expression[use attribute name]` 与 `[use expression attribute name]`：历史swegym parser的line.split()[1]同映到冻结键`[use`。两实际节点本次均PASSED，不能虚构已发生掩盖；将来混合状态可能后者覆盖前者，故155参考键不等于155独立完整节点。F2P本身不受此空白截断。

历史harness从ROOT/runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz以tarfile.extractfile只读scripts/replay_grade.py、adapters/slime/replay_grade.py、prepared_task_face.py、envpack/spec_vendor.py、swegym_parsers.py、scoring.py与固定specs的getmoto/moto4.1项，未解包/import/执行。common四成员hash核匹配；swegym_parsers:44–56切摘要键，scoring:189–271只读Start/End段并按冻结F2P/P2P计分；完整pytest rc另作诊断。原spec=make init、Python3.12、pytest -n0 -rA，没有install_wave1 recipe/materials/reference_bindings覆盖。

## 5. 开发、交付与环境证据边界

逐题plan/image.json/status.json与共用launcher已读。原派生image=`sha256:5e8dbd0f9789953dad4712fb86d4b1fbb1058b41ccd279d27f16ad7d62c49860`，base image=`sha256:c67dbd356fcaa937ebff4b3fe0d78e4ea78211888233a4e5f07da95eddfe079d`，scripts_digest=`sha256:5fade887f26755d6f0215bfdb327623a2aa0fc57da1041b917d8602bcd0de179`。pins=setuptools72.1.0/wheel0.43.0/packaging24.1，COPY wheels+ENV PIP_NO_INDEX/PIP_FIND_LINKS仅是离线准备，不是安装成功证据；上表两轮make init输出才证明历史安装。status.json是最后gold的原/work命令；noop由共用launcher生成并有原日志，不能把status说成两次命令捕获。

原policy字段：user=rh2grader、uid54322、cpus2.0、memory_bytes4294967296、pids_limit512、shm_bytes67108864、tmpfs_bytes1073741824、network=deny_all、candidate_writable_prefixes=[/opt/miniconda3/envs/testbed]。candidate apply_user=agent/54321，非正式模型actor。resource.mem_peak_mb gold252.594/noop297.359，resource_facts=null，保留原字段名不改单位。历史导入观察/testbed/moto/__init__.py、version4.1.4.dev；安装元数据4.1.0.dev0另记，不据此否定base绑定。env_qualification=absent，driver_close无残留/cleanup_failures；不是当前actor通过。

| 开发需要 | 公开依据 | 现有证据与缺口 | 最小未来验证 |
| --- | --- | --- | --- |
| 定位投影和编辑源码 | 题面、table.scan/query/SecondaryIndex.project | base可读，普通Python修复，可提交；正式shell未知 | actor打印UID/cwd/python及moto.__file__后跑题面两例 |
| boto3/mock_dynamodb/pytest | Makefile17–19、requirements-dev/tests、setup.cfg、contributing安装 | 历史grader两次editable安装与导入成功；actor激活/PATH/必要安装权限未验 | 窄跑相关公开投影/scan测试；确认候选工作区代码生效 |
| 资产与服务 | 题面直接在mock内建表/放item | 无真实AWS、Terraform、外部数据或持久服务需要 | 明确region与虚假凭证；不以全仓Docker依赖要求本题必须Docker服务 |
| 可重放原条件 | inventory/common、status原路径 | 当前原prepared仍指/work，镜像可用性和wheel payload待准备 | 另建重定位副本和独立输出；本轮未修改原件 |

正式actor身份/实际消息注入/派生镜像消费/资源配置待共同验收，是模型开发门槛，不自动要求先验actor才能做固定grader语义诊断。public_hints的NON-TEST编辑限制与本题合法源码修复不冲突；“已激活”和“所有测试修改不计分”不是运行事实。官方恢复文件仅tests/test_dynamodb/test_dynamodb.py（prepared_task_face:306–331），test_globs=()；gold路径moto/dynamodb/models/table.py被projection包含、ignored_paths空。未另加排除路径，未改源/tests/gold/reward/expected。实际镜像未来资产/隔离未验，不能从无.git导出推定完全无答案暴露。

## 6. 八方面收口和最小后续

八方面已覆盖：公开需求；版本/原问题；全部新增断言/F2P和相关P2P；替代实现/LSI范围疑点；gold及分页/存储回归；开发条件；交付/parser；用途及暴露。未读其它题来推导题簇，不因同文件宣布重复，也不估计模型成功率；全仓和所有合法实现未穷举。

优先未来窄实验：绑定原条件后运行题面GSI KEYS_ONLY原例，再在同一fixture做投影scan→原表get/scan，核所有item、分页键和原表非投影属性仍在；独立记录语义与固定grader分数。若要判断测试遗漏是否影响奖励，仅追加一个有明确目的的部分修复（跳过GSI KEYS_ONLY或省略copy中择其实际疑点），不强制双候选。LSI范围分歧先由公开共同契约判断，不能为了让gold通过而扩大题面；若将来修订需保留版本和原要求依据。
