# L1_moto_3 · 逐题静态审查汇总

包：`L1_moto_3`（20 题，全部 getmoto/moto）。开工 2026-09-16 02:45，止 08:30。
记录目录：`docs/.../env_overnight_20260916/L1_moto_3/records/<instance_id>.json`；大文件与 worktree：`runs/env_overnight_20260916/L1_moto_3/`。

## 本包共性前提（不逐题重复）
- 20 题信号完全同质：`in_e2` 空、`fragile_reference_id=false`、stage1 `gold=RESOLVED_FULL` / `empty=RESOLVED_NO`、`p2p_missing=f2p_missing=0`、无 DeepSeek 候选。因此 L1 brief 的优先级排序退化为 ASSIGNMENT 原序。
- **install 阶段 rc=2 是本包 20/20 的共性**：stage1 离线跑 `make init` 时 pip 需要联网装 `setuptools>=40.6.0`，DNS 失败 → `make: *** [Makefile:18: init] Error 1`。证据：`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-6212/gold/offline/a1/test_output.txt:327-353`。测试仍全过（镜像自带 testbed 环境且 /testbed 源码生效）。全 216 题里 moto 37 题 + pydantic 20 题同样 rc=2。
- `eval_cmd` 记录为 `pytest -n0 -rA`，实际 eval.sh 追加的是 **test_patch 触碰的测试文件路径**（不是 F2P/P2P 的 node id），即整文件跑。

## 跨题发现（本包在逐题过程中顺带查出，影响面超出本包 20 题）

### A. 判分用的 test id 被空白字符截断，且两个测试会塌缩成同一个键（P1）
- 216 题里 **35 题**的 `fail_to_pass`/`pass_to_pass` 含被截断的参数化 test id（含 `[` 但不以 `]` 结尾）：合计 **15 个截断的 F2P id（分布在 9 题）**、**1278 个截断的 P2P id**。清单：`truncated_test_ids.json`。
- 截断来自上游原始数据：`s2/raw/swe_gym_lite_full_f70b1a29.jsonl` 里 `getmoto__moto-5865` 的 `FAIL_TO_PASS` 就是 `[..., 'tests/test_ecs/test_ecs_boto3.py::test_list_unknown_service[no']`（真实 id 是 `[no args]`）。
- **解析器源码已核对**：`rh2/src/repoharness2/envpack/swegym_parsers.py:44-56` 的 `parse_log_pytest` 里是 `test_case = line.split()` 然后 `test_status_map[test_case[1]] = test_case[0]` —— 对 `PASSED <nodeid>` 摘要行按空白切，只取第 2 段。该模块自述是 SWE-Gym fork 解析器的**逐字移植**（docstring 第 11-14 行），所以数据集里的截断 id 和 RH2 解析出的 status_map 键来自同一个 bug、恰好互相匹配，`f2p_missing=0` 是巧合而非正确。证据：`runs/env_probe_stage1_20260910/.../getmoto__moto-5865/gold/offline/a1/status_map.json` 里存在键 `...::test_list_unknown_service[no`。
- 同一行还决定了塌缩语义：`test_status_map[test_case[1]] = test_case[0]` 是**后写覆盖**，所以同前缀的多条参数化用例只保留最后一条的状态。
- **真正的漏洞是塌缩**：`getmoto__moto-7273` 的日志 555–556 行是两条不同的参数化用例（`[use attribute name]` 与 `[use expression attribute name]`），而它的 `status_map.json` 只有 161 个键、其中只有一个截断键 `...[use`。两条用例的状态被合并成一个，后写的覆盖先写的 —— 若其中一条失败、另一条通过，判分看不到失败。本包受影响的题：6226、7273、7335、7348、7484。

### B. 10 题的 `gold=RESOLVED_NO` 是 id 编码问题造成的假阴性（P1）
- 排除 mypy 的 35 题（无阶段一记录），216 题里 gold 非 RESOLVED_FULL 的共 16 题；其中 **10 题的唯一原因是 `status_map` 里找不到某个 P2P id**：
  - 非 ASCII 参数化 id（pytest 在 `-rA` 摘要里把它转义成 `\xee` / `\U0001f4a9` 形式，而数据集里存的是原字符）：`getmoto__moto-5417`、`5545`、`5562`、`5701`、`6308`、`pydantic__pydantic-8977`。证据：`getmoto__moto-5701` 日志 1505 行是 `PASSED tests/test_s3/test_s3.py::test_key_with_special_characters[/the-key-un\xeecode/test]`，而数据集里是 `[/the-key-unîcode/test]`。
  - id 里含反斜杠或空格：`iterative__dvc-4185`、`modin-project__modin-6780`、`pandas-dev__pandas-48106`、`pandas-dev__pandas-50319`。
- 也就是说：**把 status_map 解析从“按空白切”改成“取 `PASSED ` 之后整行 + 统一做 pytest 的 ascii 转义归一”，可能一次性救回最多 10 道被误判为 gold 不通过的题**，同时消除 A 的塌缩风险。

### C. 后一题的 base 里含前一题的标准答案（train/eval 污染，P2）
- 59 道 moto 题里，**35 对**（A 早于 B）共用至少一个 gold 文件，且每一对里 A 的 base_commit 都是 B 的 base_commit 的祖先。
- 抽样 11 对做实证（把 A 的 `golden_patch` 拿到 B 的 base 树上 `git apply -R --check`），**6 对逐字命中**：6585→7111、6355→7584、7331→7335、5699→6387、5737→6508、4833→6317。（另 5 对 `-R` 因上下文漂移失败，属不确定，不能判为“不含”。）清单：`contamination_pairs.json`。
- 处置建议：数据划分时按“共用 gold 文件 + 祖先关系”成组，整组同进 train 或同进 eval。

### D. moto 测试材料里有通向真实 AWS 的分支（P2）
- `MOTO_TEST_ALLOW_AWS_REQUEST=true` 时，`tests/test_awslambda/__init__.py`（由 7111 的 test_patch 写入）以及 base 仓库里已有的 `tests/test_kms/__init__.py:19`、`tests/test_sns/__init__.py:23`、`tests/test_s3/__init__.py:31`、`tests/test_timestreamwrite/__init__.py:20`、`tests/test_lakeformation/__init__.py:14`、`tests/test_logs/test_export_tasks.py:16` 会**跳过 mock 直接打真实 AWS**。默认 `false` 时安全。建议在评测容器里显式置 false 并列入禁止 agent 修改的环境变量。

## 逐题表

| task | 主要发现 | 建议处置 | 下一实验 |
| --- | --- | --- | --- |
| getmoto__moto-6212 | 材料干净（test 只碰 test_athena.py，gold 只碰 athena/models.py）；base 确有缺陷（`create_work_group("primary","","",[])`）。F2P 断言 `primary["Configuration"] == {}`，但题面从未规定该取值，按真实 AWS 语义填默认配置会被拒（检查 23 issue，P3）；F2P 只查 primary，硬编码 `if name=="primary"` 可蒙混（检查 25 issue，P3）。 | ready_for_probe | 用 AWS 风格默认 Configuration 的补丁跑 F2P 验证会被拒；用硬编码补丁验证能通过。 |
| getmoto__moto-6226 | **本包最强发现（P2）**：F2P 新增 `assert "tags" not in resp`，因为 `responses.py:430-433` 把 `tags=None` 序列化成 JSON null、botocore 丢键。于是最惯用、且与同文件 203/360/539/863 行一致的修法 `Cluster.__init__: self.tags = tags or []` 会被拒；该断言题面没提，且与真实 AWS（返回 `tags: []`）相反。另：F2P 的 test id 不是新增测试名，而是改写 base 上已通过的同名测试。 | needs_review | 用 `self.tags = tags or []` 补丁跑 F2P，确认在该断言处失败。 |
| getmoto__moto-6317 | **P1 题面信息不足**：题面只描述“mock_s3 下 put_object 得到空对象”，全文无 `patch_client`；而真正根因（patch_client 与 mock_s3 重复注册 botocore_stubber → Body 被消费两次）只写在不可见的 `hints_text` 里，题面自带的复现代码在 base 上根本不复现。F2P 是 `test_core/test_importorder.py::test_patch_can_be_called_on_a_mocked_client`。另 P2：gold 依赖 botocore 私有属性链 + 裸 except，botocore 升级会让 F2P 直接失败（gold 注释自述）。 | needs_repair | 只给题面跑一次 agent 定位，预期失败；并在镜像里记录 botocore 版本与该私有属性链是否可取。 |
| getmoto__moto-6355 | 题面自足、gold 单行（`parsed_arn.region`→`self.region_name`）。P2：**base 的 `tests/test_sns/test_topics_boto3.py:4` 把 `import sure` 注释掉了，而文件有 67 处 `.should`**，test_patch 的第一个 hunk 才恢复它；任何“base 上不打 test_patch 跑 P2P 预检”的流程会全线报错。P3：F2P 只走 GetTopicAttributes，而 `get_topic` 有 9 个调用点，只改 responses 层的窄修复能蒙混。 | ready_for_probe | base 上不打 test_patch 直接跑该文件，确认报错；再用只改 responses 的窄补丁验证能过 F2P。 |
| getmoto__moto-6387 | P2 判分面窄：gold 改的是 `responses.py:_get_xml_body`（被 create_distribution:43 / update_distribution:92 / create_invalidation:108 三处共用），但评测只跑 `test_cloudfront_invalidation.py` 4 个用例，改坏 distribution 解析也能满分。P3 难度偏低：题面直接写出根因（xmltodict 单元素返回 str）、类名 `CloudFrontResponse`、模板常量 `CREATE_INVALIDATION_TEMPLATE` 与那行 Jinja；gold 为单行 `force_list="Path"`。`hints_text` 为空。 | ready_for_probe | 用 `force_list=True` 的补丁验证：本题满分但 test_cloudfront_distributions.py 大面积失败。 |
| getmoto__moto-6408 | P2 测试放过错误修复：F2P 名为 `test_multiple_tags__ensure_tags_exist_only_on_one_image`，注释写“旧镜像的 tag 应被移除”，但只断言 `batch_get_image` 返回的**第一个**镜像的 manifest（`new_image, *_ =` 会吞掉多匹配），所以只改返回顺序的假修复可满分。P3：gold 的第一个 hunk（`image_tag in x.image_tags`）不被任何判分用例覆盖，只写第二个 hunk 就满分。 | ready_for_probe | 构造“反向遍历 repository.images”的假修复跑 F2P+P2P，确认满分；再构造只含 hunk(b) 的补丁确认满分。 |
| getmoto__moto-6469 | 本包目前最干净的一题：题面自足、base 缺陷明确（`if recovery_window_in_days` 对 0 短路）、gold 单行 `is not None`，且已核对 `responses.py:162` 缺省返回 None 所以不会误伤不传参的调用；两条 F2P 分别钉住 force / 非 force 路径并断言消息子串，能区分“只改第二个校验”的错解。P3：`models.py:734` 的同类 0 短路未修（当前不可达）；区间端点 7/30 无用例。collected 91 = 90 graded + 1 server-mode skip。 | ready_for_probe | 无需复验；若要加固，补 7/30 边界用例。 |
| getmoto__moto-6508 | P2 要求需外部 AWS 知识：F2P 断言缺省时 `OriginReadTimeout==30`、`OriginKeepaliveTimeout==5`（AWS 默认值），题面全文没有这两个数；而公开材料支持的另一种合理修法“缺省就不输出该 XML 元素”会在 F2P 处 KeyError。**正面发现**：test_patch 同时把既有夹具的显式值改成 10/15 并在 P2P 加断言，有效堵死“模板里写死 30/5”的假修复，是本包里判分设计最好的一题。P3：gold 用 `or 5`/`or 30`（显式 0 被吞），与本包 6469 修的 falsy 短路自相矛盾。 | needs_review | 用“省略元素”补丁跑 F2P 确认 KeyError，量化这条隐含要求的代价。 |
| getmoto__moto-6585 | 干净题：题面自足、gold 最小、P2P 的 `test_create_function_from_image`（用 `WorkingDirectory: "/opt"`）构成有效对照组，堵住“永远省略该键”的偷懒修复。P3：与本包 **getmoto__moto-7111 共用 `tests/test_awslambda/test_lambda.py` 与 `moto/awslambda/models.py`**，数据划分时应放同一侧。P3：“显式传空串”与“未提供”两种语义无用例区分（gold 保留空串，按题面字面实现会省略，两者都能过 F2P）。 | ready_for_probe | 无需复验；划分时按测试文件分组。 |
| getmoto__moto-6701 | P2 判分无法区分改动风险：hints 里报告者给的全局补丁（在 `moto/core/responses.py:_get_param` 里对 uri_match 结果 unquote）同样能过本题全部 17 条用例，而维护者明确因为“会影响所有 service”才改用 iot 局部方案（gold）。评测只跑 `test_iot_thing_groups.py`，对全局改动零拦截。P3：10 条 F2P **全是 base 已有的测试名**，test_patch 只把组名字面量改成含 `:` 的形式（本包第二例，破坏“F2P 必为新增测试”的假设）。 | ready_for_probe | 打 hints 的全局补丁跑本题（预期全过），再跑其它 service 测试看回归，量化判分面与改动面的差距。 |
| getmoto__moto-7111 | **两个跨题问题在这题第一次实证**：(1) **train/eval 污染**——把 6585 的 golden_patch 拿到本题 base 上 `git apply -R --check` 成功，即 6585 的标准答案逐字存在于本题 base 的 `moto/awslambda/models.py:364-377`；(2) **测试材料含真实 AWS 分支**——test_patch 把 `tests/test_awslambda/__init__.py` 从空文件改写成 108 行的 `lambda_aws_verified`，其中 `MOTO_TEST_ALLOW_AWS_REQUEST=true` 时跳过 mock 直接打真实 AWS（同模式在 base 里已有 6+ 处：test_kms/test_sns/test_s3/test_timestreamwrite/test_lakeformation/test_logs）。题目本身干净：gold 单行 `spec.get("PackageType", "Zip")`，Image 型 P2P 构成对照。 | needs_review | 对 216 题跑 contam.py 出全量污染对；在镜像里确认 MOTO_TEST_ALLOW_AWS_REQUEST 未设置且不透传宿主环境变量。 |
| getmoto__moto-7273 | P2 隐含约束：F2P 除 Items 外还断言 `ScannedCount == 1`，题面全文无 ScannedCount；“先收全量、排序反转后再截 limit”这一自然修法会让 Items 正确但 ScannedCount=3 被拒。gold 的做法是把 SORT+reverse 整块从 FILTER 之后前移到 FILTER 之前（作用于 `possible_results`）。P1：本题是 id 塌缩的受影响样本（collected 162 vs graded 161）。P2：与 5960→6185→7273→7484 同属一条祖先链、共用 `models/table.py`，划分需成组。 | needs_review | 用“后截断”补丁验证 ScannedCount 断言失败；并构造让两条 `[use ...]` 参数化用例一真一假的补丁，看判分是否仍报满分。 |
| getmoto__moto-7331 | **本包最严重的一题（两个 P1）**。(1) 题面与判分不是同一个问题：题面报的是 Cognito **Identity** 的 `GetId`，而 gold 新增的 `PUBLIC_OPERATIONS` 只有 5 个 `AWSCognitoIdentityProviderService.*`（ConfirmSignUp/GetUser/ForgotPassword/InitiateAuth/SignUp），**不含 GetId**；GetId 由同在本包的 7335 处理（同一 issue 拆成两个 PR）。(2) 判分集合里**没有任何鉴权仍生效的断言**（`test_cognitoidp.py` 全文无 AccessDenied），而 `tests/test_core/test_auth.py` 不跑——把 `_authenticate_and_authorize_action` 改成无条件 `return`（关闭整个 IAM 访问控制）即可 4 F2P + 191 P2P 全过。另 P2：7331 的 gold 在 7335 的 base 里逐字存在；`@set_initial_no_auth_action_count(2)` 依赖精确请求计数，脆弱。 | needs_repair | 用“首行 return 关闭鉴权”的补丁跑本题确认满分，再跑 `tests/test_core/test_auth.py` 确认大面积失败。 |
| getmoto__moto-7335 | **与 7331 的 `problem_statement_sha256` 逐字相同**（`sha256:2a08bd1a…`），是同一 issue 的后半个 PR：gold 只是往 7331 建的 `PUBLIC_OPERATIONS` 里加 `AWSCognitoIdentityService.GetId` / `.GetOpenIdToken`。全局扫描发现 216 题里题面重复的只有两组：(7331,7335) 与 (6121,6157)，而现有 `s2/ingest/duplicate_clusters_v0.json` 只按相同 base_commit 聚类，**这两组都没收录**。P1 同 7331：`test_cognitoidentity.py` 无任何鉴权失败断言，关闭鉴权即满分。P2：题面只提 GetId，F2P 还要 GetOpenIdToken。P3：base 已有机制，难度极低。 | needs_repair | 把去重判据扩到 problem_statement_sha256 重跑聚类；用“关闭鉴权”补丁验证满分；用“只加 GetId”补丁验证半数 F2P 失败。 |
| getmoto__moto-7348 | P1 判分锁死逐字报文：F2P 要求 `err["Message"]` 完全等于一段 AWS Java 风格消息，其中 `KeySchemaElement(attributeName=UUID, keyType=HASH)` 这种渲染**在整个 moto 代码库里 grep 零命中**（外层 `1 validation error detected:` 模板倒是有先例，见 kinesis/exceptions.py:67 等），题面也没给任何错误文本 —— 只能靠对 AWS 报文的记忆猜中。P2 题面噪声：三个抱怨里两个（LSI/GSI 为空、BillingMode 不对）是用户自己 helper 没传参，澄清只在不可见的 hints 里；题面把真问题说成“Attributes 不能多于 keys”，而判分的约束是“KeySchema 长度 ≤ 2”。本题也是 id 塌缩受影响样本（42 collected vs 41 graded）。 | needs_review | 用“语义正确但措辞不同”的补丁跑 F2P 确认失败，量化逐字断言的代价。 |
| getmoto__moto-7361 | P1 判分远超题面：题面是一条功能请求（只要 `add` + `/apiStages`，并给了 `apiId:stage` 格式），F2P 却还断言 `add` 对 `/productCode`、`/quota/limit`、`/quota/offset`、`/quota/period`、`/throttle/burstLimit`、`/throttle/rateLimit` 全部生效——其中 `/quota/offset` 连 base 的 `replace` 都不支持、题面从未出现。只按题面实现会在第 2 条断言失败。P2 隐藏的类型转换：gold 把 throttle 两项改成 `int(value)` 而同函数的 quota 仍用原值（base 已有断言证明 integer shape 的转换在 botocore 侧），照抄上面几行写法的实现会被拒。F2P 又是 base 已有的测试名（本包第四例）。 | needs_review | 只实现 `/apiStages` 的补丁跑 F2P 确认在 productCode 断言处失败；再把 throttle 写成 `= value` 确认 throttle 断言失败。 |
| getmoto__moto-7484 | 题面自足、F2P 覆盖四个场景（精确键 / 略大 / 大幅增大 / query+scan 两路），判分较紧。P2 **gold 语义存疑**：`_item_smaller_than_dct` 复合键分支写成 `item.hash_key <= H and item.range_key <= R`，这不是 (hash, range) 的字典序比较；query 因已按单一 hash key 过滤而无碍，但 **scan 跨 hash key 时**，`hash<H 且 range>R` 的条目不会被跳过、会被重复返回 —— 而两条 F2P 的条目全部共享同一个 pk，完全测不到该分支。另：id 塌缩受影响样本（192 collected vs 191 graded）；F2P 挂在 `dynamodb_aws_verified` 上，属跨题发现 D 的真实 AWS 分支；与 5960→6185→7273→7484 同一祖先链。 | needs_review | 建 pk+sk 表写 (a,z) 与 (b,a) 两条，用 ExclusiveStartKey={pk:b,sk:a} 做 scan 分页，看 (a,z) 是否被重复返回。 |
| getmoto__moto-7495 | 干净题：模型层 `models/instances.py:374` 已经算好了 `User initiated (…)`，缺陷只在 `responses/instances.py:466` 的模板写成空元素 `<reason/>`；gold 单行改成 `<reason>{{ instance._reason }}</reason>`，且 grep 确认全仓库只有这一处同类模板。P3：F2P 只断言 `startswith("User initiated")`，把模板写死成 `User initiated` 即可满分（题面给的期望值是带时间戳的）；`terminate()` 的同类 reason 也被连带修好但零覆盖。P2：与 4975/5347/5980 共用 `tests/test_ec2/test_instances.py`，划分需成组。F2P 又是 base 已有测试名（本包第五例）。 | ready_for_probe | 用写死 `User initiated` 的补丁确认满分；补一条正则回归校验时间戳格式。 |
| getmoto__moto-7584 | P2 题面报文与判分不一致：题面写期望消息是 `... for endpoint {endpoint_arn}`，F2P 逐字断言的却是 `... for endpoint arn{endpoint_arn}`（多一个字面量 `arn`，gold 注释自述 AWS 真实报文就缺这个空格）——照题面实现会被拒。P2 环境：F2P 挂 `@sns_aws_verified`，该装饰器在 `MOTO_TEST_ALLOW_AWS_REQUEST=true` 时会用真实 SSM `get_parameter(..., WithDecryption=True)` **取出解密的 Firebase/GCM API key** 再打真实 AWS（比 7111 那例更强）。P2 污染：6355 的 gold 在本题 base 里逐字存在。P3：测试名 `test_publish_to_deleted_platform_endpoint` 里根本没有 publish。 | needs_review | 按题面逐字实现消息（不带多出的 `arn`）跑 F2P 确认失败。 |
| getmoto__moto-7607 | **三个新问题**。(1) P2 挂死风险：gold 在拿不到 TaskToken 时进入 `while time.time() < mustend_at: … time.sleep(1)`，上限是 `DEFAULT_TIMEOUT_SECONDS = 99999999`（约 3.17 年）；`moto/stepfunctions/parser/` 下 **没有任何 `daemon`**（执行线程见 `backend/execution_worker.py:79`），而测试的失败分支（`parser/__init__.py:90-93`）只 `assert False`、**从不 stop_execution** —— 候选补丁一旦让 F2P 失败，pytest 报完结果后进程也不会退出。(2) P2 文件边界：eval.sh 的 `git checkout <base> …` **不含 test_patch 新建的** `templates/services/dynamodb_task_token.json`；对“test_patch 全是新文件”的三题（5885/dvc-6954/MONAI-2454），checkout 后面干脆没有 pathspec，等于完全不恢复测试文件。全 216 题里 test_patch 新建文件的共 8 题。(3) P2 期望行为只在 hints 里（AWS 也不传真 token、执行一直 RUNNING、DDB 存字面量 `$$.Task.Token`）。判分集合只有 3 条。 | needs_review | 用会让 F2P 失败的补丁跑该文件并计时，确认进程挂住；再先 touch 那个 .json 跑 eval.sh，确认 `git apply` 报 already exists。 |

## 收尾

**覆盖数：20 / 20**（ASSIGNMENT.json 全部完成；每题一份 `records/<instance_id>.json`）。
处置建议分布：`ready_for_probe` 8、`needs_review` 9、`needs_repair` 3（6317、7331、7335）。
问题严重度合计：P1 10 条、P2 26 条、P3 21 条；检查项 pass 201、issue 98、unknown 1。

**未做 / 未验证清单**
- 所有 `next_experiment` 都只写了方案，**一次都没跑**（本包不启动 Docker、不装依赖，只做静态审查）。最该先跑的三条：6226 的 `self.tags = tags or []`、7331 的“首行 return 关闭鉴权”、7607 的挂死复现。
- 跨题发现 C（污染）只抽样实证了 11 对中的 6 对；另 5 对 `git apply -R` 因上下文漂移失败，结论是 unknown，不能判为“不含”。全量 216 题未跑。
- 跨题发现 A/B 的修复方案（status_map 解析改为取整行 + ascii 转义归一）只做了根因定位与影响面统计，**未改任何代码**（`rh2/src` 只读）。
- RH2 当前接线是否仍沿用阶段一那份 eval.sh 生成逻辑（尤其是 checkout 的 pathspec 过滤）：`not_checked`。
- 本包 20 题在 e2 里都没有记录，也没有 DeepSeek 候选轨迹可交叉验证；所有“某某假修复能拿满分”的判断都是静态推理 + 证据引用，未经实跑确认。

**最值得用户裁定的 3 个问题**
1. **status_map 的 test id 解析要不要修？** `rh2/src/repoharness2/envpack/swegym_parsers.py:52-55` 是 SWE-Gym fork 解析器的逐字移植，按空白切 + 后写覆盖。修它能救回最多 10 道被误判为 gold 不通过的题（跨题发现 B），并消除 35 题上的状态塌缩（跨题发现 A）；但会**偏离“逐字移植上游”的既有约定**，且会让本地判分与上游数据集的 id 形状不再一致。修 / 不修 / 只加告警，需要定。
2. **题面与判分不对应的题怎么处置？** 明确命中的有三道：6317（根因只在不可见 hints 里）、7331（题面讲 cognito-identity GetId，gold/F2P 全是 cognito-idp 的另外五个操作）、7335（与 7331 题面逐字相同，是同一 issue 的后半个 PR）。是剔除、改写题面，还是保留并在解题率统计里单列？另外 216 题里题面 sha256 重复的两组（7331/7335、6121/6157）现有 `duplicate_clusters_v0.json` 都没收录，去重判据要不要扩到 problem_statement_sha256？
3. **“判分面远小于改动面”要不要在 RH2 侧补齐？** 至少四题（7331/7335 关闭 IAM 鉴权即满分、6701 改全局 `_get_param` 零拦截、6387 改坏 distribution 解析零拦截）都能靠破坏性改动拿满分，因为评测只跑 test_patch 触碰的那一个文件。是接受上游判分原样、还是由 RH2 为这些题挂上附加回归（如 `tests/test_core/test_auth.py`）？后者会让分数与上游 SWE-Gym 口径不可比。
