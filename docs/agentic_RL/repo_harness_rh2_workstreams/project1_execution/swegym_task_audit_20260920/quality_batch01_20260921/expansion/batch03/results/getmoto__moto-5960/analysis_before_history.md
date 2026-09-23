# getmoto__moto-5960 — 独立初稿（历史未开放）

撰写标时：2026-09-20 21:45 UTC / 2026-09-21 05:45 SGT。状态：needs_review / static_review；用途：development_diagnostic。本稿保存后不回写。

## 边界与身份

权威根目录 ROOT=`${REPO_ROOT}`。下文 P=`ROOT/runs/swegym_quality_batch03_20260921_v1/public/getmoto__moto-5960`，Q=同批 `private/getmoto__moto-5960`，E=`ROOT/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-5960`；路径均相对此权威 ROOT，而非工具默认 cwd。

先读本题封存 `public_read.md`（SHA256 c2ac93029588118e7ba49745674a38096cbd9702d5b5c9f6b431e887662023dc），随后独立阅读公开 bundle、相关源码/旧测试、完整 test.patch/gold.patch、完整 2 F2P + 155 P2P 名单、grading/validation/environment_record/run_refs/source_refs，以及本题精确原始 ledger、diagnostics、image、日志片段与全部 pytest 摘要。未读本题 history/refs、旧质量记录、其他题结果、reviewer 或本批聚合。环境卡和 inventory 本题对象含 gold/noop 结果，已经暴露；这是“旧质量结论未读”的独立初稿，不是结果盲审。inventory 只取 common、families.install_wave1、exact id 对象，未追 analysis_reference。

基线 commit=`d1e3f50756fdaaea498e8e47d5dcd56686e6ecdf`，tree=`1a036474ade83906dcb02e8a99e452d10a5fad39`。公开清单 1879 entries / 1878 blobs 的整体物化核查复用协调者；Terraform gitlink `f9a6db6e3c3f3299701747972fd6c37ba4af36f4` 未物化，但下述 DynamoDB mock 调用与唯一正式测试文件不使用它，不能由此判环境不可用。公开 issue SHA256=`09e9327d2109afd7563f89bab3aa4da453332574e66bfcdd36f0996c852066c9`。

## 1. 公开需求与合理实现

公开问题明确要求扫描 GSI 时遵守 INCLUDE、KEYS_ONLY 投影；给出 INCLUDE 的 3 个 item 和 KEYS_ONLY 的 6 个 item（含数字 range key）的可复制用例。分别只返回键加 NonKeyAttributes、仅键；prose 指全部扫描项，示例断言却只看第一项，不能把第一项视为全部语义。旧公开 `SecondaryIndex.project` 的文档明确覆盖 LSI/GSI，已有 GSI/LSI query 测试给出表键与索引键的并集，因此实现共享投影是自然路线，但 issue 没有明确要求新增 LSI scan 行为。

可从 `Table.scan` 对返回副本调用现有 `index.project`；也可在 backend/response 的适当边界创建独立 Item/attrs 投影，保留筛选、分页和原表数据。不要求 gold 的准确位置、deepcopy 调用形式或 hunk。公开代码已提供 helper 和 query 的 copy→project 样板，非隐藏知识。只修 GSI 两种投影、保留 LSI scan 旧行为的方案符合 issue 的狭义字面范围，却会被第二个 F2P 拒绝；是否应接受这种范围需澄清，当前不能定性为已证误拒。

## 2. 完整 test.patch 与需求—断言双向映射

test.patch 只有 `tests/test_dynamodb/test_dynamodb.py` 两处追加；无新增 helper/fixture。两函数均为公开旧 `@mock_dynamodb` 函数，原来的 query 断言保留，新增 scan 断言才形成 F2P。函数自身构造表/item；`tests/test_dynamodb/conftest.py` 的 table fixture 不被这两函数请求。Imports 使用公开 boto3、sure、mock_dynamodb。

| 需求/旧行为 | 公开依据 | 官方节点与决定性断言 | 判断与限制 |
|---|---|---|---|
| GSI INCLUDE 返回所有表/索引键和列出的非键属性，删除其他属性 | issue 第一用例；table.py:39–59 | F2P `test_gsi_projection_type_include`：旧 query 先验证 1 项；新增 scan 的 `items[0]` 精确等于 4 字段，排除 nonProjectedAttribute | 覆盖单项 INCLUDE；未验证 scan 数量、所有项、后续原表读取；旧 query 的 length 不等于 scan length |
| GSI KEYS_ONLY scan，仅保留表/索引键 | issue 第二用例 | P2P `test_gsi_projection_type_keys_only` 只有 query；test.patch 未给它追加 scan | 明确缺失，不能因函数名或 LSI 的 KEYS_ONLY 断言当成覆盖 |
| LSI KEYS_ONLY scan | 共享 SecondaryIndex helper 与公开 LSI query；issue 未明确写 LSI | F2P `test_lsi_projection_type_keys_only`：旧 query 后，新增 scan 的 `items[0]` 精确等于 partitionKey、sortKey、lsiK1SortKey | 断言本身符合共享模型，但扩展了 issue 的字面对象；需保留范围争议而非自动认定错误 |
| 对多项均投影、不丢项、不复制额外项 | issue 3/6 项和“scanned items” | 两个 F2P fixture 各 1 项，新增 scan 均无长度/全集断言 | 部分；只处理第一项或错误扩大返回列表没有直接鉴别 |
| 投影不删除存储数据 | Item.filter:395–411 的公开警示；P2P basic/nested projection scan 的复读 | P2P `test_basic_projection_expressions_using_scan`、`test_nested_projection_expression_using_scan` 对无 IndexName 的 ProjectionExpression 后复读 | 覆盖旧无索引分支；缺少 GSI/LSI 投影 scan→get/query/无索引 scan 的复读 |
| 无索引 scan、表达式、过滤、无效索引、分页键保留 | 公开已有行为 | P2P basic/nested/alias projection scan、scan_filter、scan_by_non_exists_index、filter_expression_execution_order、projection_expression_execution_order | 相关旧行为有覆盖；最后一个索引 scan 是 ProjectionType ALL，仅保证不因过早显式投影使 LastEvaluatedKey 崩溃 |
| 索引稀疏项选择、ALL、Limit 的键形状 | table.py:788–905；两个公开 table_*range_key 测试文件 | 两文件的 `test_scan_by_index` 验证 ALL、Count/len、Limit 和表/索引 LastEvaluatedKey；without_range_key 的分页旧测试 | 公开但不在该正式命令及 F2P/P2P 引用内，不能计入本轮运行覆盖 |

逐 F2P 反向定位：GSI INCLUDE 排除 nonProjectedAttribute 直接对应 issue 主诉；LSI KEYS_ONLY 排除 someAttribute 对应共享抽象的扩展。两者均未锁实现或异常文案。没有用测试名称替代对断言、setup 和调用顺序的检查。

## 3. 调用链、旧行为与 gold 完整性

独立展开 `responses.py:754–800`（调整 ProjectionExpression、转发 IndexName、按结果构造 Count/Items/ScannedCount/LastEvaluatedKey），`models/__init__.py:343–373`（转换旧 ScanFilter、解析 filter expression、转发），`models/table.py:25–128,730–935`（SecondaryIndex/LSI/GSI、query 尾部、全部 scan/分页），`dynamo_type.py:395–411`（Item.filter 原地删除属性）。`Table.scan` 从 `all_items`/`has_idx_items` 取得存储 Item 引用，筛选后 append；既有无索引显式投影分支自行 deepcopy。gold 在 trim 前无条件复制 results，然后按 index_name 取现有 index，对每个结果投影。

gold SHA256=`df2af6b800578dc24b6ef33c396677683d766702734f44d506248354147b7af9`，仅 6 行新增，无测试修改。现有 project 保留表键与索引键，INCLUDE 再加入 NonKeyAttributes；ALL 不删属性。按当前调用链，gold 能处理公开两种 GSI 投影和所有结果，保留存储对象；无索引语义仅增加复制，显式投影继续在 trim 后执行。`LastEvaluatedKey` 依赖的表/索引键仍在，旧 query 的复制与投影不受更改。未发现已证的核心漏修或新回归。

这不是完整正确性证明：未穷举特殊属性名、嵌套 NonKeyAttributes、FilterExpression 引用未投影属性、Select、1MB 大项分页/投影组合。gold 在 trim 前投影与现有 query 一致；不能未经公开规范/区分用例就断言大小计费或未投影过滤有回归。无条件 deepcopy 可能增加大结果内存，但现有运行峰值不构成资源失败证据；不提出 CPU/内存改动。

真正展开的旧测试：本题 test_dynamodb.py 的 GSI KEYS_ONLY / INCLUDE / LSI KEYS_ONLY 三个完整函数；469–534、717–776、994–1051 的三种 scan 表达式；1432–1495 的过滤；2390–2421 的无效索引；4047–4081 的 1MB **query**（不能误记成 scan）；5486–5542 的 GSI LastEvaluatedKey **query**；5546–5631 过滤顺序；5635–5690 投影顺序；以及上述两个独立文件的 scan_by_index 和 without_range_key scan_pagination。完整 155 P2P 名单已读，但其余 update/transaction/list/get 等函数没有逐体展开。只读统计主文件全部直接 `.scan(IndexName=...)` 调用：基线仅无效索引和 ALL+ProjectionExpression 两处；加上 patch 才有两个投影 scan，支持覆盖缺口判断，不是全仓调用穷尽。

## 4. 测试充分性与合理非 gold 路线

I1【直接静态覆盖缺口】GSI KEYS_ONLY 是公开明确要求，却没有 scan 判据。自然的不完整分支实现“GSI 仅 INCLUDE 已处理，LSI KEYS_ONLY 已处理”可能通过当前两 F2P 和旧 query，仍失败公开第二用例；分支遗漏的满分只属静态预测，未运行候选。多项/数量遗漏附着同一覆盖问题，不用构造定制返回值来夸大风险。

I2【具体状态回归漏测】复制保障不是冗余：直接对原 Item 调 `index.project` 会删除原表非投影字段。F2P 的 query 在 scan 之前，scan 之后没有复读；既有复读 P2P 走另一条无索引分支。因而“省略新复制但保留投影循环”的部分修复可能通过现有判据却损坏数据；源码副作用确定，满分和复读失败仍是未执行预测。gold 已正确避免该问题，不能写成 gold 的缺陷。

I3【范围疑义】LSI scan 是合理的共享实现覆盖，却未在 issue 明示；需要确认它是意图的一部分，才可据此否决一条保守 GSI-only 实现。公开源提供合理推断基础，因此不足以直接标记不公平任务。

唯一优先实验（仅建议、未执行）：在同一冻结 replay 下，保留原命令/引用，增加 issue 的两个原始 GSI scan 用例并对所有项及总数断言；对照 base、gold、一个只遗漏 GSI KEYS_ONLY 分支的最小候选，同时报告原 reward 与新断言。它直接检验 I1 是否产生“公开功能未全修但原 reward=1”的鉴别失败。索引 scan 后原表复读可作为同一诊断表的观测，但不混称已实施或已得到结果。若资源只够一项，先补 GSI KEYS_ONLY 判据。

## 5. 开发条件、actor 公共材料和文件规则

public_bundle 保留完整 issue、base、repo、workdir=/testbed、allowed_tools=[bash,edit]；public_hints 是泛型 harness 工程说明，宣称 preactivated conda/testbed、bash cwd=/testbed、禁止改测试。冻结 prepared_task_face 的公开 rollout 路径是 render_user_prompt(public) 并传 bundle；未取得正式 actor messages/工具初始化捕获，因此不能确认实际 actor 收到全部提示、实际 cwd/激活/import或写权限。现有 grader import `/testbed/moto/__init__.py` 不能替 actor 补证。

官方恢复精确 test.patch 触达的 `tests/test_dynamodb/test_dynamodb.py`，整文件恢复后施加官方 patch；`test_globs=()`。不能把“所有 tests/** 不可投影”当成已存在的规则；公开提示禁止改测试与具体 hygiene 的路径覆盖分开记录。额外排除建议为空，无证据加 helper/conftest 或 Terraform 路径。当前相关 helper 在公开产品源码，候选可用；未见隐藏依赖使正常开发必败。

开发可先用公开 snippet 或单个函数检查，再跑唯一正式文件；本轮没有执行项目 Python、pytest、安装或任何 CPU 探针。正式 actor 开发验证与首错修复仍未验证。

## 6. 环境、安装和本题原始运行

install_wave1 是历史 baseline 代码加镜像 COPY wheels / ENV PIP_NO_INDEX=1、PIP_FIND_LINKS=/opt/rh2/build-wheels；无 recipe/materials/reference_bindings wrapper。COPY 本身不安装。E/image.json 记录 base digest=`sha256:4b71766331736b51bd74bb86cdb5e4e21040a7816e01fbb5d914526d33ef8944`、base id=`sha256:c67dbd356fcaa937ebff4b3fe0d78e4ea78211888233a4e5f07da95eddfe079d`、实际 image id=`sha256:5e8dbd0f9789953dad4712fb86d4b1fbb1058b41ccd279d27f16ad7d62c49860`；pin 元数据 setuptools72.1.0/wheel0.43.0/packaging24.1。实际镜像当前可用性与 wheel payload 未检查。

gold 日志410–588实际显示 make init、离线链接、editable build 和两次 Successfully installed moto-4.1.0.dev0、RC0、Python3.12.4/pytest8.3.2、`pytest -n0 -rA tests/test_dynamodb/test_dynamodb.py`；noop392起同样实际安装。ledger观测的 import版本4.1.4.dev 与 pip元数据4.1.0.dev0分开记，不凭元数据宣称错包。安装失败/跳过/安装未执行不适用于这两次记录。

| 原件（各 ledger.jsonl 第1行） | 条件和正式运行 | 结果 |
|---|---|---|
| E/gold/ledger.jsonl；eval_logs/evallog_replay-er19-iw1-getmoto__f12bdab3.eval.log | gold；2026-09-19T06:13:53.098451Z；安装10.952s，test36.397s，峰值252.594MiB（原字段MB） | pytest158 passed，RC0；解析157；F2P2/2，P2P155/155，reward1 |
| E/noop/ledger.jsonl；eval_logs/evallog_replay-er19-iw1-getmoto__a9c21d90.eval.log | noop；2026-09-19T06:12:38.028717Z；安装11.334s，test29.956s，峰值297.359（原字段MB） | pytest2 failed/156 passed，RC1；解析157；F2P0/2，P2P155/155，reward0 |

日志SHA：gold a942c7ed9cc6c9b64e3340b6a42b14794a2cd4c3a121ebffa23cb9aa20b7164e；noop 2d79bc1c50c4df481bc39bd1e16e765f52f8a572894333c94ac35bba88b6ff2b。ledger 文件SHA：gold81f72c8cbf713832b1c6c03e7d356991d9b7ad57e33d2a9320b34d607889826f；noop52615e511e8be43fad73aa0a7a10af958676a843344c8f15b8b061ea51883a5b。原日志noop687–715/827–847明确因多出非投影字段而失败，不是依赖、collection 或权限错误。

两行均 env_qualification=absent、deny_all、2CPU/4GiB、64MiB shm/1GiB tmpfs，apply user agent/54321、grader rh2grader/54322；这不是正式 actor 身份。diagnostics 的 trusted setup/protection成功、runner digest前后一致、reference missing/skipped均空。无模型token/费用/实际actor耗时观测，成本保持null；历史test耗时不冒充新审计或actor容器总耗时。

## 7. 执行节点、解析键、冻结评分引用

冻结 baseline.tar.gz 仅用 tarfile.extractfile 读文本，未解包落盘或导入执行。复用本包已沿调用链阅读且 SHA 固定的成员：prepared_task_face.py `3a3d7bcab18e8a83f99104180e065ed32d8ecbce5d1bd4aaa7f8bd72b001aa27`；spec_vendor.py `8e0037b27c87268ed7df97ef64d261d0e6dac7375bc85fd5badd0fecdb94d41d`；swegym_specs_242429c1.json `0da8f9caeec18e3b41386fb66e677807335c0fe12c41d811dd9fb65f9bfcc925`；swegym_parsers.py `995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276`；scoring.py `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`；trusted_projection.py `5ef126803e93e3606123a4aef4389d35bad0551a622020d1dd22f0db32224a60`。当前 ROOT/rh2 不代表这些历史字节。

spec选择 make init 和 pytest -n0 -rA，命令加 patch触达文件，不按 F2P 选节点。parser 44–56以空白split取第二token作为键，status_map随后由冻结F2P/P2P评判；普通完整pytest RC1不自动reward0，reward依赖解析结果RESOLVED_FULL。

I4【已证身份粒度丢失，未证错分】：两条真实参数节点 `test_set_attribute_is_dropped_if_empty_after_update_expression[use attribute name]` 与 `[use expression attribute name]` 被合并为 `[use`，解释158节点→157解析键→2+155引用。gold756–757、noop1009–1010均PASSED；noop-rA中所有PASSED在前、两个FAILED在1043–1044，不能仅凭字典last-write推断mixed状态在该顺序会被遮成pass。当前两次reward与目标F2P真实结果一致，没有已证reward误判。建议保留完整节点身份并同步重建引用，需另评迁移；本轮不改parser/ref/reward。

## 8. 初步处置与未查范围

静态主结论：核心公开任务可解、gold沿已查路径合理且真实原运行通过；oracle漏掉明确GSI KEYS_ONLY scan，并缺索引投影后的存储完整性。LSI扩展范围需澄清，解析身份合并另列，不用环境成功或gold成功替代功能充分性。

保留 needs_review / static_review，仅 development_diagnostic。无原件修改，revision_refs=[]，additional_exclusions=[]。未运行任何候选/探针，未审正式actor，未复现环境，未展开全部155 P2P函数、全仓所有间接调用或所有DynamoDB组合，未看历史/reviewer。优先下一步是上述公开GSI用例鉴别实验，而非先改资源/排除路径。等待协调者核SHA并明确放行本题history后，另写delta/card/record；本稿保持封存。
