# getmoto__moto-7584 独立复核结论

**总判断：部分同意。** 我同意作者的诊断和处置方向：G1、T1、T2b 都成立；走 R-b 加 R-c，按 D4 以 `stmt` 作替代正对照；不按 P5 交用户；转第2类。**但修订草案 v1 还会放过两类违反公开要求的候选**（私有检查中都是 20/20 通过）。因此“修订版已过诊断评分、退化候选均为 0”只对作者实际测过的候选成立。交接前必须把草案补成 v2 并重新验证。

- 2026-09-29，独立复核者，不继承作者上下文。
- **初判**：[`review_initial.md`](review_initial.md)，sha256 `523e887c04729be28589f071d1cc8b72d115e24eb9d7af1b24b341d57eea42bc`。它在阅读 `result.md`、`evidence/` 之前写成，之后没有改动。
  - 与作者一致的判断：原例属于核心要求；gold 没有修好原例；`arnarn` 没有公开依据；P2P 不保护有效订阅；处置为 R-b + R-c + D4；不属于 P5。
  - 初判另外静态指出了两点，本稿已实跑确认，见下文 N1、N2。
- **证据层级**：
  - 作者的正式评分：只读核对了账本与日志。
  - 我自己的检查：全部是私有检查，即原镜像 `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-7584:latest`、root、`--network none`、一次性容器，运行 `pytest -p no:cacheprovider -n0 -q`，每次不到 15 秒。**没有跑正式评分，没有改动仓库中除两份复核文件以外的任何文件。**
  - 探针脚本放在会话 scratchpad（不入库），关键改动已在下文逐字写出。

## 一、逐条核对

| # | 作者主张（`result.md` 位置） | 判断 | 依据 |
| --- | --- | --- | --- |
| 1 | gold 在题面原例上不报错（L32、L44） | **同意** | 作者证据 `evidence/semantic_v1/gold/b1_behavior.out:8-11`：`second_after_delete.raised=false`，返回的就是第一次订阅的 ARN。我逐字执行题面示例代码（补 `mock_aws` 和区域）复核：gold 的 `issue last subscribe : OK b7510a166ff3`，与第一次订阅相同；`stmt` 报 `InvalidParameter`。静态原因：base `moto/sns/models.py:514-517` 查重命中后直接 `return old_subscription`；`:714-716` 的 `delete_endpoint` 只删除 endpoint；gold 的检查插在提前返回之后（gold 补丁 L5-9）。 |
| 2 | `stmt` 用原材料正式评分得 0，唯一原因是 `arn:` 与 `arnarn:` 之差（L45） | **同意** | `evidence/formal/ledger_stmt.jsonl`：`reward 0.0`、`f2p_pass 0/1`、`p2p_fail 0/19`、`reference_missing_count 0`、`cleanup.removed true (rm:ok)`、`install_rc 0`、测试段完整。日志 `formal/eval_logs/evallog_replay-c3-moto7584-stmt-_cd19a707.eval.log:654-666`：`Code` 断言已通过，失败发生在测试第 474 行的正文等式，差异只有多出的 `arn`；`:695` 为 `1 failed, 19 passed`。对照组 `stmt_arnmsg` 与 `stmt` 只差正文，账本 `reward 1.0`（日志 `stmt__834a7234.eval.log:641-645`，20 passed），由此把原因隔离在正文上。 |
| 3 | 退化候选 `reject_all_arnmsg`（application 一律报错）用原材料得 1（L48） | **同意** | `ledger_reject_all_arnmsg.jsonl`：`reward 1.0`、`f2p 1/1`、`p2p_fail 0/19`、参考缺席 0、清理成功；日志 `rejal_26d52445.eval.log:638,642`，20 passed。base 的 `tests/test_sns/test_application_boto3.py` 里 `grep -n subscribe` 没有输出，19 个 P2P 都不会订阅有效的 application endpoint。它违反的公开要求是题面 L25 的 “Works as expected”。补充：这个候选用的是隐藏测试的 `arnarn` 正文，换成题面正文会因 T1 失败；但“P2P 不保护有效订阅”这一结论不受影响。 |
| 4 | 修订草案 v1 的断言有公开依据，放宽没有过度（L60-64） | **断言本身同意；覆盖范围不同意** | `rh2/experiments/category3_cloud_20260929/moto7584/revised_test_v1.patch:8-13` 的三项断言都能对应题面 L2：`Code == "InvalidParameter"`（题面和 botocore 中 `InvalidParameterException` 的 `code: InvalidParameter`）、`"Endpoint does not exist"`、请求中的 ARN。它不是“任何带 ARN 的报错都能过”：必须同时满足错误码和原因短语。`wrong_code` 在修订版的日志 `rev1-_f4695659.eval.log:660-666` 失败（`'NotFound' == 'InvalidParameter'`），说明错误码断言有效。原例序列（`:50-67`）有题面依据，并隐含了“有效 endpoint 可以订阅”。**但仍有两个缺口**：(a) 对其它协议没有任何正例，见 N1；(b) 所有“不存在”的实例都是“先创建后删除”的 endpoint，与题面示例同一种输入形态，见 N2。 |
| 5 | 修订版诊断评分：两个正对照得 1，gold 与各退化候选得 0（L66-79） | **就已测候选同意；作为验收结论不同意** | 8 行账本（`formal_revised_v1/ledger_*.jsonl`）与作者表格一致：`stmt`、`stmt_arnmsg` 得 1（日志 `rev1-_3170de22`、`_5bfee746` 第 645 行，20 passed）；noop 在测试 L475 `DID NOT RAISE`；gold 与 `gold_order_stmtmsg` 在原例 L494 `DID NOT RAISE`；两个 `reject_all_*` 在 L488 有效订阅被拒；`wrong_code` 见上一行。全部 `reference_missing_count 0`、`p2p_fail 0/19`、清理成功、安装 rc 0。8 次运行的 `scripts_digest` 都是 `886dee82…`，原材料为 `234baa6b…`；grader 版本带 `+c3-moto7584-issue-example-v1` 后缀；`audit_*/materials.json` 的 `revised_patch_sha256` 为 `a4dbe106…`，与草案文件一致。候选补丁的 sha256 与账本 `candidate.patch_sha256` 逐一相符。**但本复核构造的 N1、N2 两类候选在 v1 上私有检查为 20/20**，按 §5“已知相关的错误候选仍为 0”，v1 不能验收。 |
| 6 | 题面原例优先于 gold 注释中的 AWS 说法，不按 P5（L17、L90） | **同意**，附一处措辞修正 | 题面对这一情形有明确的期望结果（题面 L33、L37），而且称这就是 AWS 的行为。另一种读法“删除后再订阅应返回旧订阅”的直接来源只有 gold 注释（gold L12）和私有测试对这一情形的回避。它没有公开依据，不满足 P5“两种读法都有依据”。修正：`result.md` L17 写“这一说法只出现在私有材料里”稍微绝对。镜像内 botocore 1.35.9 的 `DeleteEndpoint` 文档写着 “When you delete an endpoint that is also subscribed to a topic, then you must also unsubscribe the endpoint from the topic.”，公开支持了“删除 endpoint 后订阅仍然存在”这一前提（与 base 一致）。但它没有说再次 Subscribe 会跳过 endpoint 校验、返回旧订阅；`Subscribe` 文档里也没有这层意思。我在 base 的 `moto/sns`、`tests/test_sns`、`docs/docs/services/sns.rst`、`CHANGELOG.md` 中检索了 `short period`、`still found`、`endpoint is deleted`、`deleted endpoint`，均无命中。所以结论不变。另外，AWS 行为无法在 base 上实跑证实，因此也不能用 R-f 按 gold 的读法去改题面。 |
| 7 | 转第2类，交接事项完整（L81-86） | **转第2类同意；交接不完整** | 按 `category3_diagnosis_20260929/README.md:18-24`，“问题和修法已明确”才能转第2类。问题已明确，但修法（v1）还要补 N1、N2。交接清单缺少：v2 修订与扩大候选集后的复验；用途结论（§2）；本题评分所用的派生配方；在另一个文件中追加 P2P 时受 D6 机制限制（`category2_repair_20260929/README.md:28`）。清单第 2 项“独立核实 `stmt` 可作替代正对照”已由本复核在私有层面完成：题面原例报错；从未创建的 ARN 报错；有效 endpoint 重复订阅返回同一 ARN；http/sms 订阅正常；整个 base 的 `tests/test_sns` 共 184 passed。 |
| 8 | 在本机重建的派生镜像与历史配方等价（L23、`evidence/derived_image.json`） | **同意内容等价；记录本身的出处不全（非阻断）** | 逐项核对如下：<br>① 配方文本：`rebuild_install_wave1.py:15-16` 与历史 `rh2/experiments/env_recipe_repair_20260919/run_install_wave1.py:36` 逐字相同，本机 `context/Dockerfile` 与历史字符串比对为 `True`。<br>② pins 与 base：取自 `installation_wave1.json` 本题条目（72.1.0/0.43.0/24.1，`image_id 437ec771…`）；base 的 `RepoDigests` 为 `…@sha256:3b263c0c…`，等于 ingest 的 `image_manifest_digest`。<br>③ wheel 摘要：三个 wheel 的 sha256 和字节数，与 `swegym_cpu_preprobe_20260929/tasks/getmoto__moto-6114/result.json:975,988`（注明是 “historical install_wave1 COPY-only wheels”）相同；packaging 24.1 另与 `env_recipe_repair_20260919/recipe_manifest.json:18` 相同。<br>④ 镜像内容：我在派生镜像内对 `/opt/rh2/build-wheels/*` 做了 `sha256sum`，三个值都相符；`docker image inspect` 显示 base 的 13 层原样保留、新增 1 层，Config 只多了 `PIP_NO_INDEX`、`PIP_FIND_LINKS` 两个 Env。<br>⑤ `evidence/derived_image.json` 与 `runs/.../image.json` 的 sha256 相同（`2452d853…`）。<br>⑥ 行为：noop 0、gold 1、安装 rc 0，与 09-19 一致。<br>记录的不足见 S3。 |
| — | 原材料的 noop 0、gold 1 与 09-19 一致；所有正式评分参考缺席 0、安装失败 0、测试段完整、清理成功（L43-50、L79） | **同意** | 14 行账本逐行核对：`reference_missing_count 0`；`cleanup.removed true`，`steps ["rm:ok"]`；`install_failed_commands []`；两个 `segment_completed` 都是 true；`stage_error null`；`num_parsed_tests 20`；`apply_ok true`。14 份日志的 sha256 都与账本 `log.sha256` 相符；`evidence_manifest.json` 中登记为已归档的 93 个文件，sha256 全部相符。noop 在原材料上失败于 `DID NOT RAISE`（`noop-_b81ce7b5.eval.log:624`）。 |

## 二、新发现的问题与反例

**N1（阻断，§4 第 3、4 步）：“对所有协议都校验 platform endpoint”的退化候选，在原材料和修订 v1 上都能得满分。**
- 构造方法：取 `stmt.patch` 并去掉 `if protocol == "application":` 这一条件（记作 `db_pre_*`），或取 gold 并去掉同一条件（记作 `db_post_arn`）。这就是在 gold 修改位置“扩大检查”：
  ```python
          try:
              self.get_endpoint(endpoint)
          except SNSNotFoundError:
              raise SNSInvalidParameter(f"...Endpoint does not exist for endpoint arn{endpoint}")  # 或题面正文
  ```
- 私有检查结果：
  - 原材料：`db_pre_arn` 和 `db_post_arn` 在 `test_application_boto3.py` 上都是 **20 passed**；
  - 修订 v1：`db_pre_stmt` 和 `db_pre_arn` 都是 **20 passed**（`db_post_arn` 因原例失败）；
  - 同一候选在公开的 `tests/test_sns/test_subscriptions_boto3.py` 上是 **11 failed, 8 passed**，被拒的包括 `test_subscribe_sms`、`test_double_subscription`、`test_creating_subscription` 等。
- 违反的公开要求：题面把范围限定为 “using `application` protocol”（L1-2）；SMS/SQS/HTTP/email 订阅是有公开旧测试的常用行为（base `test_subscriptions_boto3.py:16-27,30-44,83-105`）。
- 根因：P2P 只有 `test_application_boto3.py`，而该文件在 base 中没有任何 `subscribe` 调用（T6：回归选集过窄）。初判已静态指出这一点。

**N2（阻断，§4 第 2 步，D1 严格版）：所有“不存在”的断言都只用了“删除过的 endpoint”这一种输入形态，与题面示例相同；“从未创建过的 ARN”没有断言。**
- 反例 `deleted_set`：`delete_endpoint` 把 ARN 记进一个旁路集合；`subscribe` 只拒绝集合中的 ARN（放在查重之前，用题面正文）。
- 私有检查结果：修订 v1 **20 passed**；公开订阅测试 19 passed；但对从未创建过的 endpoint ARN，订阅**成功**（`never-created endpoint: OK`）。
- 违反的公开要求：标题 “when the endpoint does not exist”、正文 “subscribing a non-existing endpoint”。
- 作者自己的私有矩阵其实已有“从未创建的端点”一列（gold、`stmt` 都会报错），只是没有写进修订测试。

**N3（可行性，私有探针，不是正式修订版本）**：在 v1 第一处 `_assert_endpoint_does_not_exist(...)` 之后追加下面几行：
```python
        never_created = endpoint_arn.rsplit("/", 1)[0] + "/" + str(uuid4())
        with pytest.raises(ClientError) as exc:
            conn.subscribe(TopicArn=topic_arn, Endpoint=never_created, Protocol="application")
        _assert_endpoint_does_not_exist(exc.value.response["Error"], never_created)
        conn.subscribe(TopicArn=topic_arn, Protocol="http", Endpoint="http://example.com/")
```
私有结果：
- `stmt` 与 `stmt_arnmsg` 都是 20 passed；
- gold 只在原例处失败（L503 `DID NOT RAISE`，按 D4 记录）；
- noop（L475）、`reject_all_application`（L497）、`wrong_code`（L444）失败；
- `db_pre_stmt`、`db_pre_arn` 在 http 订阅处失败（L490）；
- `deleted_set` 在从未创建的 ARN 处失败（L485 `DID NOT RAISE`）。

这说明两处缺口都能在同一个测试文件内低成本补上，而且不改测试命令，也不新增 P2P 文件。

**N4（非阻断）**：修订后的 F2P 仍保留 `@pytest.mark.aws_verified`。新增的原例断言没有在 AWS 上验证过；而且按 gold 注释的说法，它在真实 AWS 上可能暂时不成立。评分时 `sns_aws_verified` 默认走 mock（base `tests/test_sns/__init__.py:22-47`），所以不影响分数，但这个标记会误导读者对修订版来源的理解。

## 三、必须修改（阻断）

1. **把修订草案补成 v2，堵住 N1。** 加一条非 application 协议订阅成功的正例，公开依据是题面的协议限定和 `test_subscriptions_boto3.py` 旧测试。可选做法有两种：
   - 按 N3 写进同一个 F2P 测试，或写成同文件中的新测试并加入 P2P；
   - 把 `test_subscriptions_boto3.py` 的 `test_creating_subscription`、`test_subscribe_sms`、`test_double_subscription` 等加入 P2P。这要求 D6 支持把另一个文件纳入选择、恢复和保护范围。

   验收要求：`db_pre_*` 两类候选在修订版上得 0。
2. **把修订草案补成 v2，堵住 N2。** 加一个从未创建过的 endpoint ARN 实例，依据是标题和正文的一般表述。验收要求：`deleted_set` 得 0，gold 与 `stmt` 在这一条上仍然通过；gold 在这一条上已实测报错。
3. **更新 `result.md`。** 需要改动的内容：
   - 在“判定”中补 N1（T2b/T6）和 N2（T2c，第 2 步）；
   - 把“修订草案…已通过诊断评分”限定为 v1 与已测候选；
   - 在交接清单里加上：v2 的正式诊断评分，候选集至少包括 noop、gold、`stmt`、`stmt_arnmsg`、两个 `reject_all_*`、`wrong_code`、`gold_order_stmtmsg`、`db_pre_stmt`、`db_pre_arn`、`deleted_set`，要求正对照得 1、其余得 0，gold 的原例失败按 D4 记录。

## 四、建议修改（非阻断）

- **S1**：`result.md` L17 改为：删除 endpoint 后订阅仍存在，这一点有公开依据（botocore `DeleteEndpoint` 文档）；但“再次订阅应返回旧订阅”没有公开依据，结论不变。
- **S2**：修订版的 F2P 去掉 `aws_verified` 标记，或把原例断言拆成不带该标记的独立测试。如果坚持保留标记，N3 中的 http 正例建议改用在测试内创建的 SQS 队列，以免在真实 AWS 上发送确认请求。另外，在 `materials_revised_v1.json` 的 `reason` 里注明：修订版只按 moto 行为验收，并与上游私有的 AWS 观察存在已知分歧。
- **S3（派生镜像记录）**：
  - `derived_image.json` 只写了 `expected_match: true`，没有记录期望摘要从哪里来。建议补上出处：`swegym_cpu_preprobe_20260929/tasks/getmoto__moto-6114/result.json` 的 `environment.wheel_manifest`，以及历史 `install_wave1/assets_manifest.json`。
  - 注明这次下载参数是 `--python-version 3.12`，历史为 `3.9`；由于字节摘要相同，这个差异无害。
  - 注明 09-19 本题的逐题 `image.json` 不在仓库内。
  - 把 `derived_image.json` 与 `derived_image_build.log` 登记进 `evidence_manifest.json`，目前没有登记。
- **S4**：按 §2 写明用途。原版：问题定位 yes；能力比较、训练候选、留出评测 no。原因是 T1 误拒、G1，并且 N1、N2 未消解。修订版经 D6 入库并通过验收后再重新评估。
- **S5**：T2a 的说法可以更精确。核心要求的一般情形（删除后首次订阅）原测试有直接断言；缺的是“期望结果”所指的原例这一实例。主要依据是第 4 步（gold 得 1 却违反该实例），第 1 步只是部分命中。
- **S6**：在交接中写明本题评分使用 `install-wave1:getmoto__moto-7584` 重建配方（tag `…:c3cloud`），以及上面 S3 的出处。
- **S7（可选）**：正文断言可以收紧为正则 `Endpoint does not exist for endpoint (arn)?<ARN>`，更贴近题面模板，同时仍容忍 AWS 的写法。也可以加一条“有效 application endpoint 重复订阅返回同一 ARN”，依据是 base 的 “AWS doesn't create duplicates” 行为。

## 五、未查

- 没有跑正式评分（`replay_grade.py`，按要求不跑）。N1、N2、N3 都是私有 pytest 结果，没有经过正式 grader profile（UID 54322、deny_all）和 `make init` 重装；只能说“按同一测试文件与命令，预计正式评分结果相同”。
- 没有核实真实 AWS 的报文，也没有核实 AWS 上删除 endpoint 后的订阅行为。
- 没有验证真实 actor（UID 54321）的开发条件，也没有模型求解证据。
- 没有读到 09-19 本题的逐题派生镜像记录和历史 `assets_manifest.json`（不在仓库内）；历史 wheel 摘要只能通过 09-29 的登记间接对照。
- 没有核对 conan-14177、dask-9378 等其它题，也没有核对 `semantic_control.py`、`replay_with_install_recipe.py` 的实现。

## 六、v2 聚焦复核（2026-09-29）

**结论：阻断项 1–3 都已落实，不再有阻断。** 范围只限于上文的阻断项 1–3、S1–S7，以及 v2 是否引入了过严或过宽的断言，不重审其它部分。

另有一条新的非阻断意见：v2 新加的 email 正例覆盖面偏窄，“凡形如 ARN 的 endpoint 都按 platform endpoint 校验”的候选仍能在 v2 上 20/20 通过，见 Q5。

核对的材料：
- `revised_test_v2.patch`：sha256 `5da7fefb7608e2a04b8a7ac9916112da08df434dc736f856b6a7b1af9d3ddb9f`。与 v1 相比，只在同一个 F2P 末尾追加两段（新文件第 502-513 行）。
- `materials_revised_v2.json`：内嵌补丁的 sha256 相同，`parent` 指向 v1。
- `all_protocols.patch`、`deleted_set.patch`。
- `evidence/formal_revised_v2/` 的 10 行账本和 10 份日志：日志 sha256 与账本一致；`evidence_manifest.json` 中 50 个 v2 归档文件的 sha256 全部相符。
- 更新后的 `result.md`。

私有检查的条件与前文相同：原镜像、root、`--network none`；没有跑正式评分。

| 项 | 结论 | 依据 |
| --- | --- | --- |
| **Q1 阻断 1**：`all_protocols` 在 v2 上为 0；`db_pre_arn` 是否等价、是否要补跑 | **已落实。两者等价，不需要补正式评分** | ① 正式诊断：`ledger_all_protocols.jsonl` 为 `reward 0.0`、`f2p 0/1`、`p2p_fail 0/19`、参考缺席 0、清理 `rm:ok`、安装 rc 0。失败点在 `rev2-_0377c3c1.eval.log:684-687`（测试第 513 行的 email 订阅），报文为 `…Endpoint does not exist for endpoint someone@example.com`（`:780`）。<br>② `all_protocols.patch` 与我的 `db_pre_stmt` 逐行相同。`db_pre_arn` 只是正文多了 `arn`，而 v2 的 `_assert_endpoint_does_not_exist` 对两种正文一视同仁，所以两者在 application 部分的表现相同，都会在 email 处失败。<br>③ 私有检查：v2 上 `db_pre_arn` 与 `db_pre_stmt` 都是 `1 failed, 19 passed`，失败都在第 513 行；gold 位置的变体 `db_post_arn` 在原例（第 494 行）失败。 |
| **Q2 阻断 2**：`deleted_set` 在 v2 上为 0 | **已落实** | `ledger_deleted_set.jsonl` 为 `reward 0.0`，其余字段同上；失败点在 `rev2-_848a47df.eval.log:683-687`（第 504 行，从未创建的 ARN `DID NOT RAISE`）。正对照 `stmt`、`stmt_arnmsg` 得 1（`rev2-_805b2183`、`_da86d30b` 第 645 行，20 passed）。gold 的正文 `arnarn` 也能通过新增的“从未创建”断言：`stmt_arnmsg` 与 gold 正文相同，而且得 1。 |
| **Q3 阻断 3**：`result.md` 已更新 | **已落实，另有三处措辞问题（非阻断）** | 已落实的内容：§4 补了 T2b/T6 与 T2c（L68-73）；结论改为 v2 通过 10 个候选的诊断评分（L13、L88-103），v1 结果保留为历史；交接清单含配方（L111）；正对照已由复核核实（L108）。<br>措辞问题：<br>① L155 写“全部文件的 SHA256 见 `evidence_manifest.json`”，但 `derived_image.json` 和 `derived_image_build.log` 仍未登记进 manifest，我实查 manifest 里没有这两项；<br>② L22 说在“base 中的 moto 代码、文档与 CHANGELOG 里都找不到”，而我实际检索的只是 `moto/sns`、`tests/test_sns`、`docs/docs/services/sns.rst`、`CHANGELOG.md` 中的指定关键词，建议写明检索范围；<br>③ L100 的“等同复核的 `db_pre_*`”，准确说法是“等同 `db_pre_stmt`；`db_pre_arn` 只差正文，私有检查同样在 email 处失败”。 |
| **Q4** email/http 正例在真实 AWS 上会触发确认；`aws_verified` 标记列为交接建议 | **可以接受（非阻断）** | 评分不会连到 AWS：`sns_aws_verified` 只有在 `MOTO_TEST_ALLOW_AWS_REQUEST=true` 时才访问 AWS，否则走 mock（base `tests/test_sns/__init__.py:22-47`）；grader 的网络策略又是 deny_all。所以这只是来源标注的问题，`result.md` §8（L147）也已写明修订版只按 moto 行为验收。建议第2类在 D6 落地时直接处理，不必退回第3类：去掉标记或拆分测试。如果保留标记，正例改用在测试内创建的 SQS 队列（同账号订阅不需要确认），这与 Q5 的修法可以合并。 |
| **Q5** 有没有新引入的过严或过宽断言 | **过严：未发现。过宽：一处残余（非阻断）** | **过严**：两种不照抄 gold 的合理实现在 v2 上都能通过，私有检查均为 20 passed，并且整个 base `tests/test_sns` 都是 184 passed：<br>• `cleanup_route`：删除 endpoint 时一并删除其 application 订阅，检查放在 gold 的位置；<br>• `response_layer`：在 `responses.py` 的 Subscribe 入口校验。<br>新增的两段断言都有公开依据：从未创建的 ARN 对应标题与正文的一般表述；email 订阅是 base 已有的公开行为（`test_subscriptions_boto3.py` 的 `test_subscription_paging` 用的就是 email）。<br>**过宽**：候选 `arn_shape` 在查重前加 `if protocol == "application" or endpoint.startswith("arn:")` 校验。它在 v2 上私有检查 **20 passed**，但会让 base 的 `tests/test_sns` 失败 97 项（共 184），例如 `test_publishing_boto3.py::test_publish_to_sqs`，因为 SQS/Lambda 这类 ARN 形式的 endpoint 被误伤；email 正例覆盖不到这一点。我不把它列为阻断，理由有三：一是原阻断项 1 要求的代表候选（去掉协议条件）已经被拦下；二是这种“按 ARN 前缀扩大校验”既不是题面或 gold 修改位置的自然产物，也属于 §7.1 第 4 步提醒不要为凑数去造的候选；三是修起来只要一行。**建议**第2类在 D6 落地时，把 email 正例换成或加上一个 ARN 形式的 SQS 订阅，例如在测试内创建队列后订阅其 ARN，公开依据是 `test_subscriptions_boto3.py::test_double_subscription`。这一处可以同时兜住 `all_protocols` 与 `arn_shape`，之后把 `arn_shape` 加入复验的负例。 |

S1–S7 的落实情况：

| 项 | 状态 |
| --- | --- |
| S1 措辞 | 已改（L19-24）。只剩 Q3② 的检索范围表述 |
| S2 `aws_verified` | 列为交接建议（L115），可以接受，见 Q4 |
| S3 派生镜像出处 | **部分落实**：`result.md` §2 已补期望摘要出处、下载参数差异，并说明历史 `image.json` 不在库内（L32-34）；manifest 登记未做，见 Q3① |
| S4 用途 | 已写（§6，L119-126） |
| S5 T2a 说法 | 已精确化（L66） |
| S6 配方 | 已写（L111，§2） |
| S7 正则、幂等 | 列为交接建议（L116-117） |

**是否仍有阻断：无。**

建议（非阻断）：
- 在 D6 落地时补一个 SQS-ARN 正例，理由见 Q5；
- 修正 Q3 列出的三处措辞；
- 把 `derived_image.json` 与 `derived_image_build.log` 登记进 manifest。

本节的私有检查脚本只在会话 scratchpad 中（不入库），关键改动已在上表写出。
