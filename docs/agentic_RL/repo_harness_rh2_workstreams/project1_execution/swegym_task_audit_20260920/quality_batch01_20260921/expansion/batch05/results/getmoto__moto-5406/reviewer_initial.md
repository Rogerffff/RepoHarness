# getmoto__moto-5406 — 独立初判（交叉复核前封存）

- 角色：fresh independent reviewer；本文件在读取主审、公开读者或旧质量结论之前形成。当前仅为 `static_review`，用途 `development_diagnostic`。
- 唯一权威根目录 `ROOT=${REPO_ROOT}`。`P=ROOT/runs/swegym_quality_batch05_20260921_v1/public/getmoto__moto-5406`；`V=ROOT/runs/swegym_quality_batch05_20260921_v1/private/getmoto__moto-5406`；以下源码行号指 `P/base/`。
- 已读角色卡、记录模板、actor 环境卡、质量协议；先读 P 题面/提示/环境说明和相关源码，再读 V 的 test/gold/grading/validation、原始环境运行材料。未读 `public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`、own history refs、旧质量报告、根质量汇总/handoff 或其他任务材料。
- 限定操作：文本检索/读取、stdlib JSON/hash/AST、指定 frozen archive 的 `tarfile.extractfile` 只读。仅在内存核对补丁上下文及测试 AST，没有运行、导入或安装项目，没有网络、Docker、SSH、GPU、模型实验或子代理。唯一写入是本文件。

**独立结论。** 原题目标明确且在指定 base 成立；gold 是作用范围合适的修复，历史 RH2 原始日志支持 noop 因目标 ARN 不符失败、gold 通过 1 F2P + 26 P2P。未发现具体误拒或 gold 新增回归。发现一个直接影响得分解释的测试缺口：唯一地区断言只检查 `us-east-2`，原来的 `us-east-1` 断言被替换；因此把硬编码常量由 east-1 换成 east-2 的错误实现，静态上预计可通过全部官方参考测试，同时破坏已存在的 east-1 公共行为。此反例尚未执行，不能写成已验证的 reward 漏洞。建议先做下文唯一 CPU 定点实验，暂保留 `needs_review`；不能仅据历史 gold=1 把本题标成完整正确性已验或 actor 已可探针。

**1. 公开要求及可消除的疑义（3、23）。**

`P/user_prompt.txt:3–6,26–56` 要求：以 `region_name="us-east-2"` 创建 DynamoDB 表后，描述返回的 TableArn 应包含该区域，而非固定 us-east-1。既有名称、账户、属性、吞吐量/计费、索引等行为应保持。题面示例创建并描述 `mock_Foundational_AMI_Catalog`，最后却断言 `/table/test_table`（39、54、56 行）；这是实际可见的表名不一致。公开旧测试 `tests/test_dynamodb/test_dynamodb_create_table.py:12–52`、`test_dynamodb_table_without_range_key.py:12–72` 都把 ARN 后缀与 TableName 对应，故不需要隐藏材料便能确定合理期望应使用实际表名；不应把这一笔误解释为重命名表的需求。原示例照抄会在正确修复后仍因名字失败，后续公开复现应显式记下这一处修正。

公开源码已能定位开发入口：`moto/core/responses.py:287,307–323` 解析请求区域；`moto/dynamodb/responses.py:135–140` 按账户和区域取 backend；`models/__init__.py:1200–1207` 向 Table 传入 `region=self.region_name`；Table 构造器接受该参数（398–412），但 `_generate_arn:568–569` 写死 us-east-1。表实际上已存入对应区域的 backend，并非所有表都被存到 east-1。合理解法可在构造时直接用传入区域拼 ARN，或保存区域后让 ARN helper 使用它；不需要新 API、移动 backend、改测试或新增依赖。

**2. 材料、初态和版本（1、2、27）。**

P public/base_identity 与 V grading 均给 base `87683a786f0d3a0280c92ea01fecce8a3dd4b0fd`。base_identity 记录 tree `895c012fc15bb2256dcc71e570bcdc9796acb153`、导出 blob 已核对、无 `.git`；本 reviewer 未重新穷举验证 1679 个 blob。Terraform 子模块未物化，和当前 Python DynamoDB 路径无必要联系。

本次独立字节/JSON 核对：V/test.patch 与 grading.test_patch 相等；V/gold.patch 与 validation.golden_patch 相等；历史原 gold 文件也同 SHA256 `2a707374963e8e522bb609524cba59460828b3ecc05a9503e4de7e72d10545de`。grading.json SHA256 `2f2ef874297dc6d4fdeb51276dc1d3fae9b74320bc1dc940d44f5ddfe33bb5a1`，validation.json `3cefc6d02bbf261b810d029022a12b86f339353df7c76d7b743e3c0747aa4c75`，均与 V/source_refs.json 的导出摘要一致。test.patch SHA256 `8ebca50a732adf095b78e805dabf13bb64efd7037639c3280b08425705c4db8f`。

原 host_grading_views.jsonl 仅取第 63 行本题；prepared_manifest 仅取本题项（数组 index 62）。base、grading、gold、原日志中的 diff 对应一致。原 noop 日志 `390d6d0a:132–160` 为 clean tree，`git show` 打印的 ThreadedMotoServer 改动是 base 提交自身内容，随后相对 base 的 `git diff` 为空；不能把它误报成未提交污染。gold 日志 `c94b9e6b:165–186` 的未提交差异只有本题 models 文件的两处 gold 修改。

**3. 需求—断言双向映射（18–20、25、32）。**

已逐行读完完整 test.patch 和 `tests/test_dynamodb/test_dynamodb_table_without_range_key.py:1–577`，包括 `_create_user_table:304–313`、局部 `OrderedSet:469–477`、文件 imports；另读目录 conftest 的 Table fixture 和 `mock_dynamodb` 对应的公开装饰器/凭据与 HTTP stub 路径。补丁只改一个测试文件，22 个 P2P 函数纯重命名，F2P 函数也改名并把客户端/预期区域由 east-1 改 east-2，没有新增 helper 或业务源码。只在内存按原始 hunk 精确匹配构造测试 AST，确认共 27 个测试函数、参考集 27 个 ID 均能对应，未执行它们。

| 公开需求或合理旧行为 | 依据 | 评分断言及结果 | 覆盖判断 |
| --- | --- | --- | --- |
| us-east-2 的 DescribeTable 返回该区域的 TableArn | issue 3–6、31、53–56；Table `_generate_arn` | 唯一 F2P `test_create_table`：client east-2，表 messages，完整 ARN 等于 `arn:aws:dynamodb:us-east-2:{ACCOUNT_ID}:table/messages`；原 noop 日志 683–693 实际返回 east-1，gold 日志 704 通过 | 直接覆盖目标区域和读取接口，非只检查补丁形状 |
| ARN 保持实际表名和账户 | 旧创建测试及 Table 构造器 account_id/name | 同一完整 ARN 断言覆盖 messages 与默认账户；resource P2P 仅断言 users 的 name | 对给定实例覆盖；未覆盖多账户或不同表名的 ARN |
| east-1 原行为不退化，其他合法区域使用各自区域 | base 创建测试 12–72；create_table.py 12–52、56–119 | 官方 F2P 替换原 east-1 断言；26 P2P 虽创建 east-1/west-2 表，但没有 ARN 区域断言；create_table.py 未进入本次命令/参考集 | 明确缺口；固定 east-2 反例可区分 |
| CreateTable 的返回 ARN 与 DescribeTable 一致 | responses.py:240–252 和 360–363 共用模型；issue 说返回 ARN | F2P 丢弃 `client.create_table(...)` 的返回值，仅断言 describe | 未直接覆盖；只修 describe 的部分实现也有漏测风险，但未另行扩成第二优先实验 |
| 原示例 PAY_PER_REQUEST + StreamEnabled + SSE Disabled + TableClass | issue 43–51；Table stream/SSE 分支 | F2P 用 PROVISIONED + GSI，未启用 stream/SSE；P2P 有 PAY_PER_REQUEST 的 CRUD，但未检查其 ARN；流的公开测试不参与评分 | 原例组合未重放；gold 走同一 Table 构造路径，静态应修正 TableArn/LatestStreamArn，不冒称运行已验 |
| 既有 CRUD、条件更新、分页、索引扫描、缺表错误继续工作 | 原测试文件各测试体 | 全部 26 P2P 的断言不变；原 noop/gold 都 26 通过 | 对这些旧路径有历史保护，不能据此替代区域/ARN 回归保护 |

26 个 P2P 的实际阅读覆盖（全部属于上述一个文件，以下为补丁后 ID 后缀）：`test_delete_table`、`test_item_add_and_describe_and_update`、`test_item_put_without_table`、`test_get_item_with_undeclared_table`、`test_delete_item`、`test_delete_item_with_undeclared_table`、`test_scan_with_undeclared_table`、`test_get_key_schema`、`test_update_item_double_nested_remove`、`test_update_item_set`、`test_create_table__using_resource`、`test_conditions`、`test_put_item_conditions_pass`、`test_put_item_conditions_pass_because_expect_not_exists_by_compare_to_null`、`test_put_item_conditions_pass_because_expect_exists_by_compare_to_not_null`、`test_put_item_conditions_fail`、`test_update_item_conditions_fail`、`test_update_item_conditions_fail_because_expect_not_exists`、`test_update_item_conditions_fail_because_expect_not_exists_by_compare_to_null`、`test_update_item_conditions_pass`、`test_update_item_conditions_pass_because_expect_not_exists`、`test_update_item_conditions_pass_because_expect_not_exists_by_compare_to_null`、`test_update_item_conditions_pass_because_expect_exists_by_compare_to_not_null`、`test_update_settype_item_with_conditions`、`test_scan_pagination`、`test_scan_by_index`。无新增条件语义要求、无测试 ID 缺席。

**4. 合理替代解与误拒（24、28）。**

新要求是 API 可见的 ARN 精确值，有公开 SDK/旧测试语义支撑；未检查 `region_name` 字段名、`_generate_arn` 调用次数、内部 helper 或实现顺序。因此，直接在构造器用已有 region 参数形成 `self.table_arn` 的不同实现也应满足评分，静态未见因不采用 gold 结构被拒的依据。F2P 中索引/属性/吞吐量等精确断言继承自公开旧测试，不是隐藏新增规格。未做替代解执行，不宣称穷尽所有合理解。

**5. gold 完整性和合理回归（26、27）。**

gold 仅给 Table 保存 `self.region_name = region` 并修改 ARN 生成式，赋值早于构造中的 `_generate_arn`（base 452 行）；名称/账户保持原值。普通创建、CloudFormation `create_from_cloudformation_json:534–557`、RestoredTable/RestoredPITTable（1052–1111；backend 1821–1853）都传已有区域，无新增必填参数；两类恢复仍经 super 初始化。备份的 TableArn/SourceTableArn（1061、1092、1153–1177）、tags 的 ARN 比较（1222–1238）、GetAtt Arn（499–505）、LatestStreamArn（599–603）以及 dynamodbstreams 的 ShardIterator/list_streams（models.py:29–35、100–115）均使用同一 table ARN。未发现 gold 将存储区域改错、破坏恢复构造或令这些 ARN 彼此不一致的证据。

额外读取公共回归测试：create_table.py 的标准/本地索引创建、stream spec、tags；test_dynamodb.py 的西二区 tags 操作 73–155；test_dynamodbstreams.py 的 setup、describe/list stream/iterator 13–92。它们均不在评分的 26 P2P 内，不能填成已跑过。未穷举全仓、其他 AWS partition 或所有跨服务集成。

`StreamRecord:214–242` 的事件字段 `awsRegion` 也固定 east-1，但那是写入后的流事件内容，gold 未动；题面仅执行创建/描述，未要求修复流事件地域。记录为邻近的既存问题，不把它算成 gold 引入回归，也不据此擅自扩大本题标准。

**6. 开发条件及边界（6–15）。**

| 所需操作/资产 | 公开依据和已有证据 | 当前边界与最小核验 |
| --- | --- | --- |
| 可定位并编辑 Python 工作区 | 上述 ARN 调用链；public_hints 给 bash/edit、/testbed、NON-TEST 源文件修复 | 修改 models 源码即可，无需不可提交的外部文件；实际 CC 工具/提示呈现未捕获 |
| 导入工作区 moto、boto3、botocore 并运行 pytest/sure/xdist | setup.py:29–42；requirements-tests.txt；Makefile:17–19；历史 make init 成功、导入观测 `/testbed/moto/__init__.py` | 历史是 grader 的 conda testbed/Python 3.12.4；actor 54321 的 PATH、解释器、导入源、可写前缀和激活仍未知。将来在实际 actor shell 先打印 UID/HOME/cwd、`command -v python pytest`、`sys.executable`/moto 路径，再运行窄公开测试；本轮不执行 |
| 公开复现用临时凭据及本地 mock；无需真实 AWS 服务、密钥或运行期公网 | issue 用 mock_dynamodb 和 testing 凭据；core/models.py:54–59,76–87,184–200,269–304 对 boto3 凭据/HTTP 做模拟；Table 在内存 | 正常创建/描述路径没有数据下载、编译、大模型/权重需求；题面 SSE Disabled 仍进入现有 KMS key 默认化路径，资产在仓库/已装依赖。不能因存在 boto3 就要求公网 |
| 准备期依赖与安装权限 | Makefile `python setup.py develop` 后 `pip install -r requirements-dev.txt`；requirements-dev 首行为 `-e .[all,server]` | 历史 deny_all 下依赖已满足且 make init 成功；这不保证新 actor 能修改 testbed 前缀，亦不证明需要再次安装。先确认现有导入即可；不要求把安装当解题内容 |
| 最小公开验证及资源 | `pytest -n0 -rA tests/test_dynamodb/test_dynamodb_table_without_range_key.py`；原例纠正名字后另作窄复现 | base 公开文件只检查 east-1，单跑通过不能证明修复目标；应加客户端 east-2 公开复现。历史测试约 7.4/7.6 秒、峰值约 251/231 MB，仅本对诊断观测；actor 的有效资源、清理及模型交互成本未知 |

**7. 原始运行、交付和评分边界（4、16–17、21–22、29–31）。**

仅使用 `B/environment_replay_inventory.json` 的 common 和精确本题 entry。环境 family 是 `baseline01`，无 install_wave1 或派生镜像覆写。原入口为 `campaign.py -> worker.py -> ReplayGrader.replay_one`；campaign.py:145–149 生成 noop/gold jobs，187–199 同 worker 分派但 fresh 容器；worker.py:70–83 读 prepared summary、构造默认 profile/ReplayGrader，104–107 逐题执行，无自定义修复 wrapper。两个源码 SHA256 分别 `37e3fb31733278dbe80970706f5615a9f158442a78dcd4c94e97f51cc9bbebce`、`b5584d5266515ecb64cdb4d46715de0a1696d80c80b4ef575ed2c8b347046207`，与原 config 一致。jobs 只取 w04-3.json indices 0/1；events 只取本题行 1–4；共享 ledger 只取第 1/2 行。

原账本公共前缀 `L=ROOT/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w04-3`：

| 原件 | 已核原始事实 | 适用范围 |
| --- | --- | --- |
| `L/ledger.jsonl:1`；eval log `evallog_replay-f216-baseline01-w_390d6d0a.eval.log` | noop，apply_user agent/54321；安装 rc=0；pytest rc=1；1 F2P 失败、26 P2P 通过，reward=0；日志 651 为实际完整命令，683–693 为 east-1/east-2 差异，792–823 为各测试结果/rc | 历史真实 RH2 replay/评分，不是本轮独立运行 |
| `L/ledger.jsonl:2`；eval log `evallog_replay-f216-baseline01-w_c94b9e6b.eval.log` | gold git_apply；included_paths 仅 models/__init__.py、ignored_paths 空；安装 rc=0；677 为同一测试命令，704–735 为 27 passed/rc=0，reward=1 | 证明该 gold 和评分路径在当时这对环境生效 |
| 两个 diagnostics | trusted setup restored=1、apply_rc=0、expected_test_files=1；num_parsed_tests=27，outside_segment=0，reference_missing/skipped 空，runner_integrity_changed=false；observed import 位于 /testbed | 日志有真实收集、断言失败及测试逐项结果，不只是 parser 分数 |

已独立计算两份完整日志 SHA256：noop `638770be004f76b18eb6a7282a74ed9067f6ba144b94823b19b064aec78e0cd5`，gold `d7b295655202fa21a634d4da33269d0f6265ff81ccc678b2ba78f57a50f53b9f`，与 V/run_refs 一致。ledger 行去掉末尾换行后的 SHA256 分别 `dcb82a661211950c1e8f43621505d369027f87495411bf500131dd5c6b81bb9f`、`d135061f70ce610c47c33ddcfd3de6c99a7f1ab9bfaecae336c9b31a582baf11`，也一致；没有把带换行摘要差异误判为材料变化。

历史 grader policy 为 rh2grader/54322、2 CPU、4 GiB、PID512、shm64 MiB、tmpfs1 GiB、deny_all，candidate_writable_prefixes 为 `/opt/miniconda3/envs/testbed`。candidate 应用身份是 agent，但由机械 git apply 后交给 grader，不能推出真实 actor 的开发、安装和 CC 工具链已通过。原 `image_id_actual=null`、`derived_image_recipe=null`；tag 为 `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5406:latest`，expected/identity manifest digest 为 `sha256:727caa5dba157d41b1e839a5044106f0ad7ea1fe824c9a5f562e2f74113339d6`。它不是 actual image ID，不代填；当前目标机镜像是否存在未知。`env_qualification=absent` 也未被静默升为环境合格。

按 common 指定 archive，只读 `runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz` 的四个允许成员：scripts/replay_grade.py、src/repoharness2/adapters/slime/replay_grade.py、prepared_task_face.py、envpack/spec_vendor.py；四个成员哈希均与 inventory 相符。核对关键路径：replay_grade.py:293–378 以 agent 应用候选并投影；424–473 仅派生镜像路径才填写 actual ID；prepared_task_face.py:179–228 恢复官方测试后应用补丁、分开安装/测试；298–332 仅 test_patch 触碰文件作为 official test files，test_globs 空；spec_vendor.py:164–191 按触碰路径形成具体测试命令。原日志恢复的就是唯一 tests 文件，业务 models 文件不会被覆盖。test.patch 不夹带普通源码。没有发现本题必须改受保护/排除路径的问题；未对共享 parser、全平台清理/隔离或任意恶意候选做新的完整安全审计。

public_hints 的“所有测试改动都会恢复/永不计分”比现有机制宽，但此题的合理业务修复不需改测试，不形成已证实的解题阻塞。实际 public_hints 是否进入 CLI 消息、public bundle 路径可见性、镜像里是否含未来答案/未跟踪资产，仍是共用卡所述未知，不能用静态导出无 `.git` 代替 actor 可见性验收。

**8. 题目关系、暴露与用途（5、29–30、37–40）。**

本题是区域标识/ARN 输出的局部缺陷修复，题面给可运行思路但不直接给内部改法；本 reviewer 已见 gold、隐藏测试与历史运行，不适合作为独立模型 solver。遵守隔离未读其他题，因此没有证据给同题派生/跨题答案污染作确定结论，也没有按同文件臆造簇。未使用网络寻找公开 issue/PR 答案，未读取未来 Git 历史。不从补丁短小推断模型成功率、训练价值或成本；token/费用与真实模型成败未知。

**唯一优先后续实验（尚未执行、须独立授权及新输出路径）。**

做一个限定本题的 CPU 负对照：在独立候选中仅把 base `_generate_arn` 中的常量 `us-east-1` 改为 `us-east-2`，保持其他源码不变；以已核 frozen baseline01 入口和本题唯一 job 运行官方 27 项评分，同时在相同候选/解释器上运行已存在的公开 `tests/test_dynamodb/test_dynamodb_create_table.py::test_create_table_standard`。预期可区分结果是“官方 reward=1，而公共 east-1 ARN 断言失败”；可用 gold 在该单一公共测试上的通过作阳性校验。若不符预期，先根据实际失败/投影日志收回反例，而非归因模型。此实验不需扩大到全仓或另造需求；确认后再决定是否以独立版本保留原 east-1 检查并增加区域对照。正式 actor 的 UID/PATH/导入/消息/镜像事实仍须在后续探针前补齐，不被这个 grader 实验替代。

未封存任何主审意见；此初判到此停止，等待协调者验哈希和明确 release 后才读取交叉复核材料。

封存时间（Asia/Singapore）：2026-09-21T07:31:07+08:00
