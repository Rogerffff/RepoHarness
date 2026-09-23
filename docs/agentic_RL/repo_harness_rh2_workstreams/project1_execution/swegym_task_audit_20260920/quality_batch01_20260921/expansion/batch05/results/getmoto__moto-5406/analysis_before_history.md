# getmoto__moto-5406：解封历史前的独立初判

本稿于 2026-09-21 完成静态原件审查后封存。未读本题历史调查、旧 record、reviewer、其它题或环境聚合质量分析；后续历史比对应另写 delta，不回写本稿。仅写此文件；未导入项目、运行项目测试、安装、访问网络/容器/SSH/GPU/模型、修改题目或提交。使用 Python 标准库读取 JSON、AST、归档成员及计算哈希不属于项目执行。

路径约定：`ROOT=.`；`P=ROOT/runs/swegym_quality_batch05_20260921_v1/public/getmoto__moto-5406`；`V=ROOT/runs/swegym_quality_batch05_20260921_v1/private/getmoto__moto-5406`；`R=ROOT/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01`；下文 `base/...` 均在 P。环境入口仅从 batch05 inventory 的 common 与本题 entry 展开。共享角色卡中其它题的例子仅作方法背景。

**初步建议：保留为开发诊断题，但先做单个 CPU 评分反例；暂不直接列为模型优先探针或训练/评测准入。** 问题真实、修复入口公开、gold 与目标一致，原 baseline 有可靠的 noop 失败／gold 成功记录。主要质量缺口是唯一 ARN 断言只看 `us-east-2`，评分没有保护原有 `us-east-1` ARN；把硬编码常量改成 `us-east-2` 的错误实现有明确的漏收风险，尚未执行验证。题面另有可消解的表名笔误；完整原例、实际 actor 条件和原 actual image ID 均未获得新验证。

## 1. 公开需求（3、23）

题面明确要求：`us-east-2` boto3 客户端创建的 DynamoDB 表，其描述 `TableArn` 应反映该区域（`P/user_prompt.txt:3–6,25–31,53–56`）。标题将错误 ARN 描述为“创建到 us-east-1”，但公开源码已按账户/区域分配后端；没有证据表明存储本身去了另一地区。合理修复应修正资源身份并保留既有区域隔离，不应重定向所有请求。

示例创建和描述 `mock_Foundational_AMI_Catalog`（39、54 行），断言却要求 `table/test_table`（56 行）。正确解释是保持实际表名，或统一示例输入名；不能让任意表都返回 `test_table`。这项文字矛盾有公开接口和旧测试佐证，不需要猜隐藏要求。按字面执行原断言，gold 仍会因为名字不同失败；这是题面笔误，不等于 gold 未修区域问题。

题面开启流、`PAY_PER_REQUEST`、SSE=False、`TableClass="STANDARD"`。这些参数不应为了修 ARN 被丢弃，但题面没有要求扩充 TableClass 功能、修正所有流记录字段、支持新分区或跨区域复制。`StreamRecord.awsRegion` 仍写死 `us-east-1`（`models/__init__.py:214–237`），属于已定位的相邻行为，当前原例没有写入项或读取记录，不升格为本题独立必修项。

`public_bundle.json` 的 issue 与静态 prompt 对应；base 为 `87683a786f0d3a0280c92ea01fecce8a3dd4b0fd`。hints 的“只改非测试源码”“禁止改测试”与环境已激活声明必须分别记录：它们是操作指令/待验声明，实际 CLI 消息是否含 hints 未验证。当前公开说明明确没有按所有测试文件名一概排除的机制；不能继续把旧 hints 的恢复解释当真实评分规则。该限制不妨碍本题在普通源码中修复。

## 2. 材料、初态和执行原件（1、2、27）

- `P/base_identity.json` 报告 base tree=`895c012fc15bb2256dcc71e570bcdc9796acb153`、1679 个物化 blob、磁盘对象/模式/路径验证通过；本轮未重新全量重建这些校验。未导出 `.git`；仅 Terraform provider 子模块内容缺失，不参与本题最小验证。
- V 的 `grading.json` 与原 `host_grading_views.jsonl:63` 的 grading 对象逐字段相同；原行（不含换行）SHA256=`84d445e6a5326cc4978e141740950e767a6192a9a0e18fdf5de2a1f4299811f8`，bundle digest=`sha256:e2ed44cf22c9ddf0466c2b2f4891378af251774fe8a63f0a0fa7e3150684e088`。
- `test.patch` 与 grading 内嵌补丁完全相同，SHA256=`8ebca50a732adf095b78e805dabf13bb64efd7037639c3280b08425705c4db8f`。`gold.patch` 与 validation 及原 replay gold 文件逐字相同，SHA256=`2a707374963e8e522bb609524cba59460828b3ecc05a9503e4de7e72d10545de`。gold 仅改 `moto/dynamodb/models/__init__.py` 两处；test patch 仅改一个测试文件。
- 初态调用链：`mock_dynamodb` 延迟导入服务（`moto/__init__.py:6–15,57`），URL 提供地区（`moto/dynamodb/urls.py:3–5`；`core/responses.py:287,307–323`），响应按 `[current_account][region]` 取后端（`dynamodb/responses.py:134–140`），后端把 `region_name` 传给 Table（`models/__init__.py:1200–1207`）。Table 接收 region 却丢弃它，构造时调用硬编码 `_generate_arn`（398–414、452、568–569）。这是直接源码证据。

原件运行是 **baseline01，不是 install_wave1**。令 N=`R/workers/w04-3/eval_logs/evallog_replay-f216-baseline01-w_390d6d0a.eval.log`，G 为同目录 `_c94b9e6b.eval.log`：

| 证据 | noop | gold | 范围 |
| --- | --- | --- | --- |
| HEAD/候选 | N:132–160 为 clean、HEAD 精确 base、无候选 diff | G:132–186 为同 base，只有上述 gold diff | 原评分侧初态，不能代替未来 actor 检查 |
| 官方恢复与补丁 | N:161–201：恢复单个测试文件、apply 成功、setup OK | G:187–227 同样成功 | 测试确实装入，不仅有 parser 标签 |
| 安装 | N:338 `make init`；638–646 安装成功与 RC=0 | G:364；664–672 同样成功 | 原评分用户环境，非 actor 安装验证 |
| 测试命令 | N:651 `pytest -n0 -rA tests/test_dynamodb/test_dynamodb_table_without_range_key.py` | G:677 同命令 | 实际只运行这一文件 |
| 测试体/失败点 | N:657 收集27；683–693 与753–775 明确显示实际 East1 ARN 对预期 East2 ARN，失败于测试66行 | G:683 收集27；704–731 所有27项 PASSED | 原件证明功能目标失败/通过，非收集或依赖错误 |
| 完整结果与退出 | N:792–823：26 pass、1 fail，test RC=1 | G:704–735：27 pass，test RC=0 | 仅这个评分范围通过 |

原 `R/workers/w04-3/ledger.jsonl` **只读取第1、2行**：reward 0/1，F2P 0/1→1/1，P2P fail=0/26 两次一致；parsed=27，outside segment=0，reference_missing/skipped 均空，无 stage_error，cleanup removed=true。`reference:null` 不等于参考测试未执行，参考匹配由这些字段及逐项测试输出共同支持。对应 diagnostics 也核了 setup=1、保护文件存在、导入路径 `/testbed/moto/__init__.py`、runner digest 前后一致。它们没有提供 actor 工具观测。

N SHA256=`638770be004f76b18eb6a7282a74ed9067f6ba144b94823b19b064aec78e0cd5`；G=`d7b295655202fa21a634d4da33269d0f6265ff81ccc678b2ba78f57a50f53b9f`。账本两行去换行 SHA256 分别为 `dcb82a661211950c1e8f43621505d369027f87495411bf500131dd5c6b81bb9f`、`d135061f70ce610c47c33ddcfd3de6c99a7f1ab9bfaecae336c9b31a582baf11`，均匹配 V/run_refs。

## 3. 需求—断言双向映射与完整测试阅读（18–20、25、32）

评分文件简称 T=`base/tests/test_dynamodb/test_dynamodb_table_without_range_key.py`。F2P=1、P2P=26；完整读了 T:1–577、其 helper 和全部 test patch。AST 只作静态名称对照：补丁23处函数改名（包括 F2P），补丁后27个测试名称与参考集完全相等，没有遗漏或额外未参考测试。除首项区域与 ARN 预期由 East1 改为 East2 外，其余22处测试改名不改变行为；另4项原名不变。

| 公开要求/合理旧行为 | 依据 | 验收 ID 与决定性断言 | 覆盖及证据 |
| --- | --- | --- | --- |
| Ohio 建表后 Describe ARN 为 East2，保留账户/表名 | prompt:25–56；Table 接口 | `T::test_create_table`：client East2、表 messages、HASH id、GSI gsi_col、吞吐1/1；describe后完整 ARN=`arn:aws:dynamodb:us-east-2:{ACCOUNT_ID}:table/messages` | **覆盖核心**；N 在 ARN 精确值失败，G 通过。无私有 helper 或 Mock 调用形状要求 |
| 建表基本输出仍成立 | T 原公开断言 | 同一 F2P 还断言属性列表、datetime 类型、GSI内容、空LSI、吞吐、size=0、name/status、schema、itemcount=0 | **覆盖该输入**；最后 schema/itemcount 在 noop 首次失败后未达，gold 达到并通过 |
| `us-east-1` 和其它受支持地区 ARN 仍准确 | `core/utils.py:416–438,463–476`；公开 `test_dynamodb_create_table.py:11–119` 明确保留 East1 ARN | 26项P2P没有任何 TableArn/区域值断言；T唯一 ARN 断言是 F2P | **缺失且有具体错误实现候选**；默认区公开旧测试不在实际评分命令 |
| Create/Describe及内部资源身份一致 | `responses.py:240–252,360–363`；model:452,580–603 | F2P 丢弃 create 响应，只检查 describe；P2P创建资源仅查名字 | **部分**；只改 describe 显示可能漏修 create/model/tags/stream，尚未构造或运行此类候选 |
| 原题 PAY_PER_REQUEST + stream + SSE=False + TableClass 组合 | prompt:35–52 | F2P 使用 provisioned+GSI，无stream/SSE/TableClass；P2P有PAY_PER_REQUEST更新项，但无此组合 | **缺失完整原例**；源码可解释 gold 作用，不能声称原例真实执行通过 |
| ARN 标签消费者、流ARN、备份/恢复、CloudFormation | model:499–505,599–605,1052–1107,1153–1177,1222–1238,1821–1853 | 无对应评分P2P。额外公开测试见第5节 | **评分缺失**；本轮仅静态追踪消费者 |
| 普通表/项生命周期、缺表错误、键schema | T:75–229 | delete table/list变1→0；缺表异常HTTP400及既有code/message；put/get/update内容；delete使item_count1→0；key_schema | **覆盖既有样例**；26项原 baseline 两次均pass，不代表跨区隔离已测 |
| 更新、条件、集合、query、scan分页/index | T:232–577 | 具体映射见下段 | **覆盖既有样例**；不保护ARN地区正确性 |

F2P 的唯一测试体不使用额外 fixture；`@mock_dynamodb` 包装执行真实 boto3 调用，重置后端并通过模拟HTTP服务路径进入业务代码（`core/models.py:64–118,388–403`）。`ACCOUNT_ID` 来自公开 core 常量；sure 是普通断言库。`tests/__init__.py` 导入 `tests/helpers.py`，已完整阅读；这些自定义 assertion 不用于 F2P。`test_dynamodb/conftest.py:6–20` 的 Table fixture传递 account_id、region、schema、attr，27项没有请求它。不是靠 Mock 返回固定ARN或跳过函数的测试。

P2P逐项阅读分组如下（ID均为补丁后的 T:: 名称，未省略某类测试）：

- 10项生命周期/缺表：`test_delete_table`、`test_item_add_and_describe_and_update`、`test_item_put_without_table`、`test_get_item_with_undeclared_table`、`test_delete_item`、`test_delete_item_with_undeclared_table`、`test_scan_with_undeclared_table`、`test_get_key_schema`、`test_update_item_double_nested_remove`、`test_update_item_set`。最后两项分别验证嵌套 REMOVE 的保留字段、SET+REMOVE 后最终dict；其余断言见映射表。缺表delete_item沿用旧 `ConditionalCheckFailedException`，不是此次隐藏新增规格。
- `test_create_table__using_resource` 只查 resource.name=`users`；`test_conditions` 验证 Key equality query 返回恰好 johndoe 一项。共享 `_create_user_table`（304–313）在 East1 创建HASH username表，固定吞吐5/5。
- `test_put_item_conditions_pass`、`test_put_item_conditions_pass_because_expect_not_exists_by_compare_to_null`、`test_put_item_conditions_pass_because_expect_exists_by_compare_to_not_null` 验证EQ/NULL/NOT_NULL时最终foo=baz；`test_put_item_conditions_fail` 的NE比较应抛ClientError。
- `test_update_item_conditions_fail`、`test_update_item_conditions_fail_because_expect_not_exists`、`test_update_item_conditions_fail_because_expect_not_exists_by_compare_to_null` 对不匹配Value/Exists=False/NULL抛ClientError。`test_update_item_conditions_pass` 及后缀 `because_expect_not_exists`、`because_expect_not_exists_by_compare_to_null`、`because_expect_exists_by_compare_to_not_null` 四项验证相应条件下foo=baz。这些 negative case 仅断言ClientError类型，回归保护有自身粒度限制。
- `test_update_settype_item_with_conditions`：局部 OrderedSet只控制序列化顺序，反序集合应EQ并更新为{baz}；`test_scan_pagination`：10项分6+4、分页key及最终集合准确；`test_scan_by_index`：普通scan3项、GSI仅2项、limit1及LastEvaluatedKey的id/gsi值。均为外部行为断言。

反查新增验收约束：East2地区来自题面；messages 与账户来自该测试输入/公开常量；ARN格式和其余表描述字段来自公开旧测试/实现。23次名称整理只影响参考ID绑定；没有证据要求solver采用某个内部属性名或补丁形式。

## 4. 合理替代解与漏收候选（24、28）

合理非 gold 路线是直接在 Table 构造时用已存在的 `region`、account_id、table_name 计算 `self.table_arn`，保持所有公开构造调用者和共享消费者的语义；也可为 helper 显式传入地区。评分只看外部字段，没有约束必须新增 `region_name` 属性、必须调用 `_generate_arn`、或严格匹配两行 gold。未发现有根据的误拒点，不为形式而另造替代补丁。

**具体漏收疑点 Q1（静态推断）：** 只把 `_generate_arn` 的地区常量 `us-east-1` 改成 `us-east-2`，保留账户/名字，其余逻辑原样。这将满足F2P唯一地区值，同时破坏旧East1与West2 ARN。已读26项P2P不观察ARN，因此预期原评分仍可能满分。公开默认区测试 `test_dynamodb_create_table.py::test_create_table_standard`（43–45）足以反证业务正确性。尚未运行此补丁，**不写“已获reward=1”**。

唯一优先下一实验：在另行授权的CPU原baseline重放条件中，对此常量替换候选同时记录原27项RH2得分与上述公开East1断言，并以base/gold为参照。必要时附三地区Create/Describe最小矩阵确认边界。若错误候选满分而公开旧行为失败，再修订验收：保留East1的旧ARN断言，并增加至少另一非默认地区；具体修订要独立版本化，当前未改题或测试。

## 5. 回归与 gold 完整性（26、27）

gold 在调用 `_generate_arn` 前保存region，然后用它生成ARN；已有 Table 签名不变，无新依赖。后端 create、CloudFormation create 和两个恢复子类都传region（model:534–557,1052–1055,1084–1087,1200–1207,1821–1853）。因此静态上Create/Describe、`get_cfn_attribute("Arn")`、LatestStreamArn、备份 SourceTableArn 与标签匹配共用正确身份。未发现无关业务改动或需要未交付文件；原gold投影也只包含该源码。

额外独立阅读了这些公开回归，但它们**不在本题评分命令内，未执行**：

- `test_dynamodb_create_table.py:1–406` 全文：East1表ARN、range key/LSI/GSI、PAY_PER_REQUEST/provisioned、stream字段、tags、SSE正负/自定义KMS等。默认地区ARN既有行为明确；stream只要求字段存在，非默认地区一致性仍需专门验证。
- `test_dynamodb.py:1–165`：West2表列表、pagination、缺表、tag/untag/list同一ARN；`5184–5255,5291–5361`：backup描述、列表和两类恢复，主要East1、ARN值相互一致或包含表名。仅读到165行的下一缺表tags测试前半，未将其完整判定纳入结论。
- `test_dynamodb_cloudformation.py:1–51` 全文：East1建栈创建/删除表，未查ARN。直接model fixture完整读过。
- `tests/test_dynamodbstreams/test_dynamodbstreams.py:1–240`：TestCore setup/teardown及完整读取流/迭代器/记录顺序用例，另读TestEdges开启流及重复开启报错用例；这些主要East1。补读242–280只是下一range-key用例前段，不将其视为完整回归审查。对应 `moto/dynamodbstreams/models.py:1–135` 完整读取，其backend仍按账户/地区取表；ARN/iterator从table_arn派生。

gold 的核心区域修复有原27项执行证据，其跨地区、账户、完整原例、流、恢复、CFN正确性仅有上述静态支持，不能扩大为全回归通过。`StreamRecord.awsRegion` 常量和非aws分区不随gold修复，是已知审查边界，不以其存在直接否决此ARN题。

## 6. 逐题开发需求与原环境适用范围（6–15）

原运行入口由 `campaign.py:145–149,187–200` 分配本题noop/gold，再由 `worker.py:65–83,103–107` 调用默认 `ReplayGrader.replay_one`。worker/campaign文件哈希与 `R/config.json` 一致，分别为 `b5584d5266515ecb64cdb4d46715de0a1696d80c80b4ef575ed2c8b347046207`、`37e3fb31733278dbe80970706f5615a9f158442a78dcd4c94e97f51cc9bbebce`。仅读取本题 `R/jobs/w04-3.json` 索引0、1（canonical SHA256=`54e2a7b41f782e48ebff9a78658ccf1a03c1aa0abaa79c5e6e6c4906bfe8981f`）及events第1–4行；没有查看/执行其它jobs。

baseline归档通过 `tarfile.extractfile` 读取相关成员，未解包或导入。`replay_grade.py:293–375,424–475` 表明候选由agent/54321施补丁再投影；无derived配置时使用public image。原worker的qualifications为空，没有额外recipe/material/reference override。原grader为rh2grader/54322，2CPU/4GiB/PID512、shm64MiB、tmp1GiB、deny_all、可写解释器前缀 `/opt/miniconda3/envs/testbed`；这不是正式actor开发条件验收。

**镜像身份限制：** public/原账本的期望manifest digest为 `sha256:727caa5dba157d41b1e839a5044106f0ad7ea1fe824c9a5f562e2f74113339d6`，ref=`xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5406:latest`，两次 `image_id_actual=null`、`image_local_build=false`、`derived_image_recipe=null`。`image_identity` 采用期望digest，不能充作实际image ID。当前镜像是否存在、原/work路径迁移、解释器依赖和新actor入口均未检查。

以下验证命令/步骤均是建议，未执行；最小公开复现R1可复用封存 `public_read.md` 中统一表名版本。

| 需要的操作/资产 | 公开依据 | 已有证据/适用范围 | 缺口与最小验证 |
| --- | --- | --- | --- |
| 定位代码、编辑并提交普通源码 | prompt；Table/response调用链；setup.py | 公开入口完整；原gold由agent施补丁且源码投影成功 | 实际actor的UID、cwd、工作区/home权限待验；观测`id`、`pwd`及源码可写/差异。无需写会被官方恢复的文件 |
| Python、boto3/botocore、moto及测试工具导入 | setup.py:29–42,141；requirements-tests.txt:1–6；T导入 | 原测试Python3.12.4、pytest8.3.2、xdist3.6.1；安装日志boto3/botocore1.35.9；moto导入/testbed | actor打印sys.executable、moto.__file__及版本并导入mock_dynamodb/pytest/sure；不把共享卡激活声明当已验证 |
| 原例可选TableClass、流和SSE依赖 | prompt:44–51；model:469–493；setup.py:108–111 | 原评分没有使用完整组合；已知原SDK版本，不等于当前actor的服务模型已检查 | 在实际actor检查CreateTable input shape包含TableClass，再运行统一表名完整原例；旧断言原样仍有名称笔误 |
| 准备/安装 | CONTRIBUTING.md:19–28；Makefile:17–19；requirements-dev.txt | 原grader的`make init`执行develop安装和依赖安装成功、RC0；无已观察安装阻断 | actor若需安装，要有可写env/离线预装依赖；不假定运行期公网。此纯Python修复没有新增依赖或必须重新原生编译的依据 |
| 最小复现与旧行为 | prompt；公开T、create_table测试 | mock路径不需真实AWS凭据或服务；原评分deny_all完成 | actor运行公开R1（East2、同名Create/Describe、另一地区list隔离）；再窄跑`TEST_SERVER_MODE=false python -m pytest -q tests/test_dynamodb/test_dynamodb_create_table.py`；结果待验 |
| 外部资产/服务及资源 | setup.py:50,108–111；model:270–289；开发测试文档 | Python docker包为流/Lambda扩展依赖，不等于建表必须有Docker daemon；Terraform子模块与最小mock无关 | 不需要新数据/模型/附件、真实AWS、GPU、MotoServer或Terraform。若扩展Lambda/ServerMode另核服务。原内存峰值250.824/230.828MiB仅两次grader观测，非actor保证 |

## 7. 交付、恢复、评分控制面和泄漏（4、16–17、21–22、29–31）

相关归档 `prepared_task_face.py:179–228,298–331` 从test patch触碰路径生成官方恢复/保护集合，test_globs为空；本题集合仅 `tests/test_dynamodb/test_dynamodb_table_without_range_key.py`。N/G的实际恢复记录与diagnostics的1个protected file相符。业务文件不在官方恢复集合；原gold ledger included_paths只有 `moto/dynamodb/models/__init__.py`，ignored_paths空。无需额外文件排除规则。

test patch没有混入业务源码，23次改名及一项区域变化均已阅读。`tests/__init__.py`、helpers、conftest、setup.cfg和Makefile是公开Python/安装控制面；本题没有要求通过修改它们交付合法修复。未在本轮重做共享评分隔离或尝试控制面攻击，也未证实全部控制面都已保护。原 runner digest不变仅支持原noop/gold两次，没有证明任意候选不可规避评分。

公开静态包未含.git或私有测试/gold；这只是包形态及阅读范围，不能证明真实镜像没有答案资产/未来refs，或预训练无污染。允许读取的public_read哈希确认为 `8328456f849f833c40063144697030e2a101684256ea61d387eecc5d8fee4ac9`，没有改动。它对环境与原例的未知项在本稿中按新证据区分了grader与actor，不替其补写“已验”。

## 8. 题目关系、用途与封存范围（5、29–30、37–40）

本题是公开issue复现型、小范围资源ARN修复；公开题面给出客户端、地区及完整示例，但没有直接给gold两行实现。未访问其它题、历史或网络，不能给跨题同源/污染/时间穿越关系结论；不凭同仓/同文件聚类。没有静态估计基座成功率、训练收益或模型成本。

已查：本题公开材料、完整gold/test patch/参考集、全部27项评分测试/helper、相关模型/响应/区域路由/ARN消费者、上述公开回归和开发文件、原baseline任务selector及原始执行证据、归档相关入口。未查：其余源码/全仓回归穷举、真实模型消息和CLI/tool、当前actor容器/资产/权限/资源、完整原例执行、错误候选得分、所有合理替代解、未来/祖先历史和跨题关系。部分首次大输出被工具截断，核心Table段、评分文件尾段、helpers、归档候选链和host selector随后已定点补读；不把检索命中当完整审查。

静态状态建议 `needs_review`，范围 `static_review`、用途 `development_diagnostic`：Q1的具体漏收风险与actor未验分开记录；题面笔误Q2建议保持原件另做规格勘误。下一步仅优先做第4节的CPU对照，当前没有任何新执行授权或修改。审查上下文已暴露私有gold、隐藏测试和原grading证据，不得充当未来solver；历史仍未解封。

归档成员身份已与inventory核对：`scripts/replay_grade.py` SHA256 `6115714639d677a7a2b116738507d8adf8fc9f5a4f4059ff7f792360359a0311`；`src/repoharness2/adapters/slime/replay_grade.py` `b8f1fbe2f37032e52b496f2eb9296c8a647a3072af2b7def600809544c9999fb`；`src/repoharness2/adapters/slime/prepared_task_face.py` `3a3d7bcab18e8a83f99104180e065ed32d8ecbce5d1bd4aaa7f8bd72b001aa27`；`src/repoharness2/envpack/spec_vendor.py` `8e0037b27c87268ed7df97ef64d261d0e6dac7375bc85fd5badd0fecdb94d41d`。前者CLI只是未来可用单题静态入口，原运行确为campaign→worker，不混称CLI已运行。没有查询quota/reset；本轮token与费用无工具观测，保持未知。
