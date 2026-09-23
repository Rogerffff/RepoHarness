# getmoto__moto-6185：历史读取前独立初稿

封存时间：2026-09-20 21:32 UTC / 2026-09-21 05:32 SGT。本稿写入后不回写。仅静态文件、归档成员文本和已有日志阅读；未导入/执行项目，未运行测试、安装、网络、Docker/SSH、模型或配额操作。

路径约定：`ROOT=${REPO_ROOT}`；`P=ROOT/runs/swegym_quality_batch03_20260921_v1/public/getmoto__moto-6185`；`V=.../private/getmoto__moto-6185`；`E=ROOT/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6185`。源码行号均为 `P/base`。先读了本题已封存 `public_read.md`，再读本题私有 test/gold/grading/validation、run_refs、environment_record 和原运行证据。**environment_record 已显示 gold/noop 结果摘要；本稿不宣称无结果暴露盲审。** 尚未读取 history/refs、旧质量调查、其他题结果、reviewer 或批次质量聚合。

## 暂定处置

`needs_review / static_review`，用途仅 `development_diagnostic`。原问题、F2P 初态及已修环境评分对照有实证；但验收仅保护顶层字符串 `S`，gold 对合法深层 `S` 仍有具体漏修路径，并改变非主键畸形字符串的旧错误路径。先做下述唯一优先 CPU 对照，再决定修订测试/gold 的范围；所有实验和修订均为建议，未执行。

## 1. 公开要求与材料

公开 base 为 `dc460a325839bc6797084a54afc297a2c9d87e63`，tree `e6198e1c93632b169ec590b7d25dd9df7d9bf173`；P/public_bundle、P/base_identity、V/grading 一致。复用协调者已核材料/210 清单，不重新枚举验证全库 blob。gold SHA256 为 `868fd2d166ddc9e3bb4028fe491ef6dbb9b45b160ef53d7d05ed3cc9647979e1`，validation 与 gold ledger 一致。

题面明确：普通属性名 `S`，包括顶层 `None` 和任意深层 map 中的 `S`，不得引发 `SerializationException`；`s`/`A` 是公开对照。写入后不丢字段由既有 put/get 行为支持。题面没有指定私有 helper、签名或主键名限制。公开异常测试还要求关闭 botocore 参数校验后保留真正 `S` 类型的整数/字典诊断，以及顶层/嵌套 `N` 类型整数诊断。静态渲染 user_prompt 不是实际模型请求；public_hints 是否成为工具/system 消息未验。

base `_validate_item_types`（table.py:487–503）对任意字典递归，遇到键 `S` 和字典值就报错，未区分属性映射与类型标签。put_item 在主键类型检查后调用它（514–544）；普通 `S: None` 经正常 AttributeValue 表达会落入此错误。原日志进一步证实新增顶层 `S` 用例真实失败，不能仅以 gold 差异代替初态证据。

## 2. 需求—断言双向映射

| 公开要求/合理旧行为 | 公开依据 | 验收与关键断言 | 判断与证据层次 |
| --- | --- | --- | --- |
| 顶层合法 `S` 属性不报错并完整读回 | user_prompt:6–10、34；test_dynamodb.py:538–589 的存储/读回约定 | 唯一 F2P `test_put_item__string_as_integer_value` 新增低层 Item `{"pk":{"S":"val"},"S":{"S":"asdf"}}`，get 后整个 Item 相等 | 对顶层字符串覆盖；noop 原日志603–607/700失败于新增 put，gold654通过。不是题面 `None` 原例。 |
| 顶层 `S=None`、`A={"S":None}`、更深 map/不同合法表键名 | user_prompt:10、34–35；DynamoType:18–27、54–64 | 无新增参数化/资源层测试；全部 34 P2P 名单亦无这些输入 | 明示范围覆盖不足；可只修顶层而得分。gold 主键名 `M` 反例见下。 |
| 真正 `S` 标记的整数、字典值报既有错误 | exceptions test:917–940；table.py:493–503 | 同一个 F2P 先执行 `pk:{S:123}` 和 `pk:{S:{S:"asdf"}}` 两个负例，各断言 ClientError Code 和 Message | 负例有公开依据；不是隐藏新错误格式，也不强制某种实现。禁用全部校验会被它拒绝。只测主键畸形值。 |
| 顶层/嵌套非键 `N:123/5` 仍错误 | exceptions test:623–650 | P2P `test_put_item_wrong_datatype` 两例都断言 SerializationException 和 NUMBER_VALUE 消息 | 递归旧行为受到直接保护；非键 `S` 字典未受到等价保护。 |
| 主键类型、空集、空主/排序/GSI 键、更新键、批量/事务约定 | exceptions test:359–403、653–670、699–740、769–980 | P2P wrong_attribute_type、empty_set、batch_put_empty、transact 两项、update_primary_key 两项、gsi_key_empty | 已展开这些测试和共享 put 调用链；保护所列边界，不能推及全部字典层级。 |
| 普通多层 map、NULL、返回旧值、list 初始写入 | test_dynamodb.py:538–589、2221–2256、3307–3347；exceptions:983起 | 前三组公开测试不在冻结参考且不在本次执行模块；P2P list_append 有合法 L 初始值和后续错误断言 | 是合理回归依据，但不能说本题评分已经执行前三组。list 内 map 原检查不递归，不能冒称那里已有同样初态失败。 |

完整 test.patch 仅一文件一 hunk：新增一段成功 put/get 相等断言，以及解释旧负例的注释，没有新增 helper、Mock 调用次序或内部方法断言。F2P 使用 `@mock_dynamodb`，botocore Session/Config(parameter_validation=False)，显式 us-east-1 和 pk:S 表；ServerMode 会 skip，但本次原日志为 PASSED/FAILED 而非 SKIPPED。已读模块 imports、全局 schema、DynamoDB conftest、tests/__init__.py、tests/helpers.py；F2P 不使用 table fixture，也不调用自定义 sure helper，旧负例用 sure.equal。

已完整阅读 V/grading 的 F2P=1/P2P=34 **参考键清单**以及两份日志全部测试摘要节点；实际展开 P2P 仅上述受影响测试、`test_update_item_with_duplicate_expressions`、`test_list_append_errors_for_unknown_attribute_value` 的大部分错误断言及初始写入。其余 query/create-table 等节点只核清单和执行结果，未逐体展开；不称全模块源码审阅或全回归证明。

## 3. 合理解法、漏测与 gold

合理非 gold 路线：明确区分“属性名 → AttributeValue”与“AttributeValue 类型 → 值”两个遍历上下文，在 M 中重新进入属性映射；维持 S/N 的既有错误校验。不必增加 attr 参数，更无需按主键名单判定普通 map 的语义。黑盒新增测试无内部形状约束，未见它必然误拒这条路线。可能蒙混的部分实现只跳过顶层普通 `S`，保留旧递归；会满足当前唯一正例，却仍拒绝题面深层 map。

gold 只改 table.py 的该 helper，无新增依赖或无关文件。`attr=key if attr is None else key` 两分支相同，递归实际只传当前父键；随后仅当 `attr in self.table_key_attrs` 时保留字典型 S 错误。table.py:245–259 表明名单是表的 HASH/RANGE 属性名，没有公开理由限制这些名不能是 `M`。

**I1：gold 的具体漏修（强静态推断，未运行）。** 合法 HASH 属性名 `M`、类型 S，Item `{"M":{"S":"id"},"A":{"M":{"S":{"NULL":true}}}}`（resource 形式 `{"M":"id","A":{"S":None}}`）。递归沿 A → 类型 M → 属性 S，处理该 S 字典时当前 attr=`M`，恰好命中 table_key_attrs，仍抛原 SerializationException。这是题面深层合法属性名的实例；F2P 固定主键 pk、正例仅顶层，无法检出。普通 index 主键的题面原例静态上可修；不能因此称 gold 完整。

**I2：gold 的旧行为回归（强静态推断，API 实际结果待验）。** 无 SDK 校验时，Item `{"pk":{"S":"id"},"bad":{"S":{"S":"x"}}}`：base 在 bad 的真正 S 字典处报 SerializationException；gold 的 attr=bad 不在表键名中，绕过该检查。后续 Item → LimitedSizeDict → DynamoType.size 的非 M/L 路径调用 bytesize(dict) → dict.encode 不存在（dynamo_type.py:193–212、248–282；utilities.py:15–16），因而预计变为内部 AttributeError，不能写成“合法接受成功”。本题旧源码的 server-side 校验注释及公开类型标签支持保留该边界；现有 S 负例只覆盖 pk，N 的 P2P 不能替代它。此项与 I1 分开保留。

唯一优先下一实验（建议，未执行）：在经确认的本题条件下，以正常 SDK 校验、HASH 名 `M`、上述合法嵌套 NULL 为输入，对照 base/gold/上下文正确实现的 put/get 等值行为，再记录 gold 现有 F2P/P2P 得分。预期 base、gold 原例仍失败，而上下文实现成功；它直接区分“参考通过”与“满足公开深层需求”。I2 暂列后续窄回归，不为凑双补丁而追加执行。

## 4. 原运行证据与解析边界

E/gold/ledger.jsonl:1（2026-09-19T06:23:14.115549Z）和 E/noop/ledger.jsonl:1（06:22:14.362105Z），角色分别 gold/noop，均 install-wave1 派生镜像 `sha256:03d0313ef99258a707b5218ca0fc91985dca2bcde321650e709365b8f2597720`。gold included_paths 仅 `moto/dynamodb/models/table.py`，noop 空；apply_user=agent/54321 只证明候选应用身份，实际评分 policy 为 rh2grader/54322、2 CPU、4 GiB、deny_all、testbed conda 前缀可写，env_qualification=absent。

原件日志简名：G=`E/gold/eval_logs/evallog_replay-er19-iw1-getmoto__1e09829a.eval.log`；N=`E/noop/eval_logs/evallog_replay-er19-iw1-getmoto__416532ff.eval.log`。两份 diagnostics 和 driver.log 亦已读。

- image.json 的 Dockerfile 仅 COPY 离线 wheels、ENV PIP_NO_INDEX/PIP_FIND_LINKS；**COPY 不等于完成安装**。冻结 spec 的 getmoto/moto 4.1 安装为 `make init`，Makefile:17–19 先 editable 安装再 requirements-dev。G:424–433/454–465、466–475/570–584 见两轮 editable build/install 真完成，N 同样有对应成功阶段；install 最后命令 rc=0，未仅凭它推断全部安装。导入观测 `/testbed/moto/__init__.py`、版本4.1.7.dev；包元数据4.1.0.dev0与源码版本不同有公开 setup.cfg 原因，不能混为错包。G:434–435 依赖 boto3/botocore 1.35.9，执行 Python3.12.4；均非题面报告者的版本。
- G:594/N:561 的实际命令都是 `pytest -n0 -rA tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py`；G:600、657为36收集/36通过、rc0；N:567、755为36收集/1失败35通过、rc1；N失败位于新增 put，旧负例先行完成。
- 冻结引用：F2P1、P2P34。实际 pytest 节点36。解析键35。G:643–644/N:741–742 的两条 `test_update_item_with_duplicate_expressions[set example_column ...]` 被冻结 parser `line.split()[1]` 合并为 `...[set`，恰好也是冻结 P2P 键。两次实跑这两个节点都通过，**没有已观测错分**；但该参考不是两个独立回归门，混合 pass/fail 时存在遮蔽风险，须单列诊断而非篡改引用。
- ledger 的 gold F2P1/1、P2P34/34、reward1；noop F2P0/1、P2P34/34、reward0；reference_missing/skipped 均空。普通完整 pytest rc1不自动决定 reward0，评分依冻结参考的解析状态；本次 noop 的零分有具体 F2P 失败支持。
- driver close 无 cleanup failures、containers_open为空；不是新的资源/清理复验。历史峰值约224/252 MiB只适用于上述单次 grader，不能填正式actor pass。

## 5. 开发条件与交付控制面

| 需要 | 公开依据/已有证据 | 当前缺口与建议（均未执行） |
| --- | --- | --- |
| 定位当前源码并导入 moto、boto3、botocore、pytest、sure | put调用链；setup.cfg:27–38；requirements-tests；历史正确工作区导入 | 正式 actor 的 UID/HOME/PATH/解释器、工作目录、conda激活与源码写权限仍待实测。复用 public_read C1。 |
| 正常进程内 DynamoDB mock 与 NULL/map 输入 | issue 示例；DynamoType:54–64；conftest | 显式 region和虚拟凭证，不需真实AWS/远程数据库/外部资产；TEST_SERVER_MODE=false，避免两项负例被skip。未验完整mock依赖链。 |
| 相关公开复现和窄回归 | public_read C2–C4、异常模块及表级源码 | 先公开 put/get，再 S/N 负例及 map/NULL/ReturnValues 旧测试；不要求全仓/lint或新编译。Docker Python extra并不证明需Docker daemon。 |
| 准备安装资产、离线构建 | image.json pins setuptools72.1.0/wheel0.43.0/packaging24.1；历史真实安装成功 | 原 wheel payload/context 未保存在当前副本，目标机镜像存在性未知；如重建需准备阶段重获资产，不能默认现时可重放。运行期无需公网。 |
| 提交合法修复 | gold projected源码成功；精确官方测试只有 exceptions文件 | `moto/dynamodb/models/table.py`可交付。冻结 test_globs=()，不得按 tests目录/文件名扩大排除；test.patch所触精确文件会恢复并保护。additional_exclusions=[]。 |

Terraform gitlink未物化（P/base_identity），所查 Python put/get路径不引用它，不判环境坏。未读整个镜像、真实可见Git祖先/包资产，答案泄漏未知；本题静态base不含Git不能代替容器隔离审查。test.patch无普通源码，未发现本题必需的修复只能写到恢复文件。tests/helpers/conftest是可影响执行的非官方恢复依赖，此处只记录适用控制面，不凭假想漏洞加排除。

## 6. 冻结执行源码身份、题目关系及未查范围

仅从 `ROOT/runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz` 读取成员文本，未解包、导入或执行。引用身份：prepared_task_face.py `3a3d7bcab18e8a83f99104180e065ed32d8ecbce5d1bd4aaa7f8bd72b001aa27`（179–212恢复/应用；299–348参考、projection与公开prompt）；spec_vendor.py `8e0037b27c87268ed7df97ef64d261d0e6dac7375bc85fd5badd0fecdb94d41d`（121–197命令）；swegym_parsers.py `995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276`（44–56）；scoring.py `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`（230–269）；trusted_projection.py `5ef126803e93e3606123a4aef4389d35bad0551a622020d1dd22f0db32224a60`（79–88）；pinned spec JSON `0da8f9caeec18e3b41386fb66e677807335c0fe12c41d811dd9fb65f9bfcc925`只取getmoto/moto4.1。未用当前ROOT/rh2代替历史。

environment_replay_inventory仅读common、families.install_wave1及本题exact-id对象；未追analysis_reference。其common中含其他归档的元信息，不曾读取这些归档代码。install_wave1没有recipe/materials/reference_bindings wrapper，保持原spec安装和测试。未打开原 prepared 全量清单；题目材料绑定复用已核结果，非本人逐blob重验。

八方面已覆盖：公开要求、材料与初态、断言映射、合理替代、gold/回归、开发条件、交付评分边界、关系与用途。关系方面尚无具体跨题commit/补丁证据，暂不聚类；题面给复现而未给准确修法。主审已暴露于隐藏验收和gold，不能用作新solver或正式评测。未知包括完整SDK序列化、全部DynamoDB及其他服务测试、全量畸形类型、真实AWS行为、真正actor工具与消息、当前镜像可用性、模型成功率/成本；未查历史将在明确放行后单独记录。仅本题所述静态候选判断，不作训练/评测批准。
