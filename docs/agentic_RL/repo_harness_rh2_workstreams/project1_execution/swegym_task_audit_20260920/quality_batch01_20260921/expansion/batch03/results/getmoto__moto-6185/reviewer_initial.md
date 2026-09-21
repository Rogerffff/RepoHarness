# getmoto__moto-6185 独立初判（封存后不回写）

状态：`needs_review`；范围：`static_review`；用途：`development_diagnostic`。独立审查者首次接触本题，在阅读任何 public_read、主审初稿/delta/card/record、旧质量结论以前保存。全程只读文本、JSON、源码与历史日志，使用 stdlib 做路径选择/AST定位/哈希；未执行项目、import 项目、测试、安装、Docker、网络或模型。

路径约定：ROOT=.；I3=ROOT/runs/swegym_quality_batch03_20260921_v1；以下 public/private 路径均在 I3 本题目录内；IW=ROOT/runs/env_recipe_repair_20260919/install_wave1。

初判：公开问题和 base 确实对应，新增回读断言有效触发原 bug；但只测顶层字符串，遗漏题面 None、嵌套和属性名/类型标签同名的关键边界。gold 的递归上下文仍混淆属性名和类型标签：存在合法嵌套 S 在主键名 M 的表上仍被拒绝的静态反例，并把普通非键的非法 S 字典值校验放宽。建议先做下述窄 CPU 语义诊断，不能由 gold=1 宣布题意完整修复。没有发现新增断言本身误拒合理实现的具体证据。

## 1. 暴露与材料身份

已读共用 reviewer 角色卡、actor_environment_card、record_template、quality_review_protocol；I3 本题 user_prompt/public_bundle/base_identity/environment_brief；本题 test.patch、gold.patch、grading、validation、source_refs、run_refs、environment_record；inventory 仅 common、families.install_wave1 和所分配三题 exact 项。本题 environment_record 内含 `verified_environment_pair`、gold/noop reward/退出码摘要和 history 的运行指针，已看到，故不是“无结果盲审”。未追 analysis_reference/analysis_149，未读任何旧质量报告、本批聚合或其它题材料。

base=`dc460a325839bc6797084a54afc297a2c9d87e63`，public、grading 相同；base_identity 记录 tree=`e6198e1c93632b169ec590b7d25dd9df7d9bf173`、blob/OID/mode/path 校验。导出不含 .git，Terraform 子模块未物化；该子模块不在本题窄验证链。private gold 与 validation patch 同文；gold SHA=`868fd2d166ddc9e3bb4028fe491ef6dbb9b45b160ef53d7d05ed3cc9647979e1`，历史候选账本亦同值。

精确读取原 prepared_manifest 的本题项，其 canonical SHA=`5804689be5a09144cd1f7c41f0b09a626a6ae643f1523e5ff547a9c01a991ff0`；原 host_grading_views 第87行 raw SHA=`c97313d2eea78b808016e4e513446153a97c729249186437186662ecf18d6fe7`，其 grading 与本题冻结 grading JSON 相等。未打印全 tasks/files。

## 2. 公开需求—断言与回归

公开题面是资源层 `Table.put_item`：任意位置的普通属性名 S 应像 A/s 一样合法；原例数字主键 index=0、S=None，并明确 A 下嵌套 S=None。不要求删掉服务端非法类型校验，也不限定内部 helper/实现路线。public_hints 要求改 NON-TEST 源码；其环境激活承诺及消息实际注入尚未验证。

| 需求/旧行为 | 公开依据、实现位置 | 验收断言与覆盖 | 独立判断 |
| --- | --- | --- | --- |
| 顶层普通属性名 S 合法并原样读回 | 题面；table.py:487–503 将所有 dict 的 key=S 当类型标签 | 唯一 F2P `test_put_item__string_as_integer_value` 新增 client.put/get 和完整 dict 相等；字符串 asdf、pk=val | 覆盖此点，实际回读不只是无异常；noop 原日志在新增 put 上失败 |
| S=None、A 中嵌套 S=None | 题面两个原例；DynamoType:54–64 的 M/L 分层 | F2P 未测 resource API、NULL 或真正 M 嵌套 | 明确覆盖缺口；gold 对常见 pk/index 的路径静态看来能放行，但无实跑 |
| 非默认合法键名不改变嵌套属性语义 | 公开 any key / any position；table.py:257–259 | 无主键名 M / S 或多层容器断言 | gold 在主键名 M 时仍误拒合法嵌套 S，见下文 |
| 非法字符串类型值仍拒绝 | base F2P 原段 test:930–940，禁用 botocore parameter validation；table.py:493–503 | 同一个 F2P 保留 S:123 与主键 S:{S:asdf} 的 SerializationException/code/message | 两种主键非法形状被保护；精确字符串来自公开旧测试，不是新增私有契约 |
| N 类型不能直接用整数，含非键嵌套 | base test_put_item_wrong_datatype:623–650 | P2P 对 mykey N:123 与 nested M sth N:5 两次错误 code/message | 覆盖，gold 保留 int/N 分支 |
| 键类型、空键/空集合、GSI 与 update | 旧测试和 responses.py:425–431；Table.put_item:514–544 | 展开见阅读范围；P2P 保护部分旧验证 | 未保护普通非键 S 字典值、M 键名冲突或列表递归 |

test.patch 仅改上述一个测试函数；全部新增内容为两条解释注释、一条 put、一条 get、一条完整字典等式；无新增 helper/fixture。已完整读原函数和其装饰器/import/config、参数验证关闭与 TEST_SERVER_MODE skip 条件。该函数把正例附在旧负例之后，历史失败点证明负例先通过并走到了新正例。

冻结 F2P 全1项、P2P 全34项已核名单；**不是声称逐行读了34个函数**。实际完整展开的 P2P 函数为：test_put_item_wrong_attribute_type、test_put_item_wrong_datatype、test_put_item_empty_set、test_batch_put_item_with_empty_value、test_gsi_key_cannot_be_empty、test_transact_write_items_with_empty_gsi_key、test_update_primary_key、test_update_primary_key_with_sortkey、test_update_item_range_key_set。另读 test_batch_get_item_non_existing_table/test_batch_write_item_non_existing_table 与同文件 import/table_schema。其它 P2P 仅核列表与运行状态；特别 update_item_range_key_set 实际测重复 ADD，并非按名称推定测键尺寸。

## 3. gold、调用链、合理替代解

读 Table.__init__/attribute_keys/_validate_key_sizes/_validate_item_types/put_item/get_item，DynamoType.__init__/size/to_json、LimitedSizeDict.__setitem__、Item.__init__/to_json、utilities.bytesize；读 DynamoHandler.put_item/batch_write_item 与 DynamoDBBackend.put_item/transact_write_items Put 分支、update_item 创建前段。

gold 把递归调用改为 `attr=key if attr is None else key`，两边相同，实际永远传当前 key。然后只在 `attr in self.table_key_attrs` 时拒绝 key=S 且 value=dict。它没有显式区分“属性名称字典”与“AttributeValue 类型字典”。

具体合法反例（源码推断，未执行）：HASH 属性名为 M、类型 N；resource Item=`{'M': 0, 'A': {'S': None}}`，或等价 client Item=`{'M': {'N': '0'}, 'A': {'M': {'S': {'NULL': True}}}}`。走 A→类型 M→嵌套字段 S 时，本层 attr=M，而 M 恰在 table_key_attrs；S 的合法 AttributeValue 是 dict，于是 gold 仍抛“Start of structure or map found where not expected”。该反例属于公开的嵌套 S 目标，不是新增服务。

具体回归疑点（源码推断）：parameter_validation=False 下普通非键 x=`{'S': {'a': 'b'}}`。base 会报 SerializationException；gold 的 attr=x 非主键，放过后，Item 构造调用 DynamoType.size→bytesize(dict)→dict 无 encode，可能转为未处理异常，而非正确的服务端类型错误。这里**不声称非法值成功落库**。GSI 只在 table.attribute_keys 中、未进 table_key_attrs，也需留意相同形状；已有 GSI P2P 只测 None/type mismatch，不能代证。

合法替代路线：按 AttributeValue 的 S/N/M/L 语义层级校验，遍历 M 的子 AttributeValue 和 L 元素，跳过普通属性名称层；继续保留旧非法类型异常。测试不要求 gold 的 attr 参数或递归策略，该路线静态上有机会满足现有断言；未用候选实跑证明。无需凭精确错误文案直接判误拒。

## 4. 历史执行证据和评分分账

原件：IW/tasks/getmoto__moto-6185/{gold,noop}/ledger.jsonl 第1行、driver.log；eval 日志分别 `evallog_replay-er19-iw1-getmoto__1e09829a.eval.log` 和 `evallog_replay-er19-iw1-getmoto__416532ff.eval.log`。重算完整日志 SHA 分别为 `95e280e2f801b816a1dbf7378e4a7be50951ed0a5a1ec4bd85e323758f0c0ecc`、`674174642eba48755b5de328b08bc9ad6d9e2ea42a1fdf91ecff946af9ddc267`，与 run_refs 相符；ledger SHA 亦逐一相符。

| 层次 | gold | noop |
| --- | --- | --- |
| 实际命令 | 日志594：pytest -n0 -rA tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py | 日志561，同命令 |
| 实际 pytest 节点 | 36 passed（657） | 1 failed,35 passed（755）；603–605 新正例失败，700为预期原 SerializationException |
| 解析键 | 35 | 35 |
| 冻结参考 | F2P 1/1、P2P 34/34 | F2P 0/1、P2P 34/34 |
| 退出码/奖励 | RH2_TEST_RC=0；reward1 | RH2_TEST_RC=1；reward0 |
| 安装 | make init（423），两次 editable build/install done（459/465、575/581），RH2_INSTALL_RC=0 | 同样两次成功（426/432、542/548），末码0 |

36个实际节点成为35键的原因可从 baseline.tar.gz 内 `src/repoharness2/envpack/swegym_parsers.py:44–56` 核实：line.split()[1] 在参数化名称的空格处截断。两条 `test_update_item_with_duplicate_expressions[set ...]` 都映到冻结 P2P 的 `[set`。历史两条实际均 PASSED，因此这里没有隐蔽失败证据；将来前一个失败后一个通过可能被覆盖，不能把34 P2P键写成34个独立完整节点。

只用 tarfile.extractfile 读取历史 baseline.tar.gz 的 scripts/replay_grade.py、adapters/slime/replay_grade.py、prepared_task_face.py、envpack/spec_vendor.py、swegym_parsers.py、scoring.py 和固定 specs JSON 的 getmoto/moto 4.1 项；未解包、import或执行。前四文件 SHA 与 inventory 相符。spec 原样为 install=`make init`、python=`3.12`、test_cmd=`pytest -n0 -rA`；prepared_task_face:128–157 安装/测试分账，scoring:189–271 按 marker 段、冻结 F2P/P2P评分，不能用全文件退出码替代 reward。

## 5. 开发环境和交付边界

原 install_wave1 launcher:24–62、逐题 plan/image.json/status.json 已核：只 COPY setuptools72.1.0/wheel0.43.0/packaging24.1 的离线 wheels 并设 PIP_NO_INDEX/PIP_FIND_LINKS，没有 recipe/materials/reference_bindings 覆盖，实际仍执行原 make init。COPY/ENV本身不算安装证明，上述原日志的两次 editable 安装完成才是。base Makefile:17–19 对应 pip install -e . 与 pip install -r requirements-dev.txt；requirements-tests 列 pytest/xdist/surer 等。历史导入观察=/testbed/moto/__init__.py，包观察4.1.7.dev与安装元数据4.1.0.dev0并存，不据此宣告错版；base身份、patch和冻结引用另有绑定。

派生镜像=`sha256:03d0313ef99258a707b5218ca0fc91985dca2bcde321650e709365b8f2597720`，base=`sha256:47443b04543c5fa25c85bb4e86c871f1f98ea0df9e254b2ca8fac9f9bdb19325`；scripts_digest=`sha256:80f2f995f16033f90aa2624be1991aec547956228b0b9364614be1c72b32f64c`。原始 command 在 status.json（最后 gold）；noop 命令生成规则在 launcher，不能把 status 当两次命令捕获。

历史 grader 是 rh2grader/54322，candidate apply 是 agent/54321，均不是正式模型 actor。policy 原字段：cpus=2.0、memory_bytes=4294967296、pids_limit=512、shm_bytes=67108864、tmpfs_bytes=1073741824、network=deny_all、candidate_writable_prefixes=[/opt/miniconda3/envs/testbed]。resource.mem_peak_mb gold224.422/noop252.023；resource_facts=null，保留字段原名，不擅自改单位。env_qualification=absent；driver_close 无残留/cleanup_failures。不能据此填当前 actor 环境通过。

| 必要开发操作 | 公开依据 | 已有证据/缺口 | 最小未来验证 |
| --- | --- | --- | --- |
| 定位并编辑 DynamoDB 类型校验 | 题面、上述源码/旧测试 | 纯Python源码可读；无需改测试、系统文件或外部资产 | 实际actor shell确认 cwd、UID、python与moto.__file__ |
| 本地复现与公开测试 | contributing/installation.rst:24–46；Makefile；mock_dynamodb | 历史grader可导入并跑；actor PATH/激活/写权限未验 | 窄跑该测试旧版+题面两例，显式region和虚假AWS凭证 |
| 安装/构建依赖 | setup.cfg、requirements-dev/tests | 历史离线make init成功；原wheel payload未保存在当前副本 | 若现成环境足够，直接验证工作区代码生效；必要安装仅用已准备环境 |
| 服务/资产 | mock_dynamodb；不涉及Terraform | 源码和历史deny_all执行支持本地模拟；无需真实AWS或公开网 | 检查TEST_SERVER_MODE未开启，避免把skip当目标覆盖 |

正式 actor 的镜像消费、CLI实际消息、激活、权限/资源仍待共同验收；这只影响模型开发探针资格，不把正式actor验收强加为每项固定grader语义诊断前置。当前原 prepared 副本仍指 /work，目标镜像可用性未验，未来运行须另建重定位副本和独立输出；本次不改。

test.patch只触及 tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py；historical prepared_task_face:306–331 将该文件列为官方恢复/保护文件，test_globs=()。gold 的 moto/dynamodb/models/table.py 在 projection.included_paths、ignored_paths空；正常源码解可提交。未做完整隔离/答案泄露验收；公开base无.git不证明真实镜像无未来资产。

## 6. 八方面收口与后续

八方面均有阅读：公开目标；版本与初始问题；全部新增断言/F2P及受影响P2P；合理替代解/误拒；调用者/gold回归；开发条件；恢复/投影和parser边界；用途/暴露。未查全仓回归、所有合理实现、实际模型消息及actor资格；未查看其它版本来推定同题簇，不由同文件声称题目重复。

优先未来窄实验：在绑定原grader条件的隔离CPU环境，用上述主键名 M 的合法嵌套 S 例比较 base/gold 的实际 Put/Get 行为，并记录同一 gold 的固定评分结果；再用非键非法 S 字典值核异常类别。若确认，按公开嵌套目标和既有非法类型契约补审覆盖/实现，保留旧版本；不用为了实验强制两个候选，也不在本轮改题。正式模型探针须另外完成共同actor准备。
