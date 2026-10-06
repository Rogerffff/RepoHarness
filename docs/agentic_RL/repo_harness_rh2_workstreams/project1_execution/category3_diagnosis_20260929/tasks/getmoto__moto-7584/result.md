# getmoto__moto-7584：第3类诊断结果

2026-09-29 / Claude（云端，第3类负责人）。原分类：第3类“具体疑点缺辨别实验”。要做的是：执行题面“先订阅、删除、再订阅”的序列并正式评分，确定是 gold 遗漏还是规格解释问题。

**结论：问题和修法已明确，建议转第2类。** 原材料上确认五处问题：

1. gold 未修好题面原例；
2. 报错正文要求超出题面模板，按题面实现的修法被拒；
3. “application 一律报错”的退化候选得满分；
4. “对所有协议都校验端点”的退化候选得满分；
5. 从未创建过的端点没有断言。

第 4、5 项由独立复核发现。当前修订草案 **v3**（v2 聚焦复核后补 SQS 正例）已通过 11 个候选的正式诊断评分，独立复核已确认无阻断。实施依赖 D6 的“测试补丁替换”切片。

## 1．公开要求

题面要求：用 `application` 协议订阅不存在的端点时，抛 `InvalidParameterException`，错误码 `InvalidParameter`，正文模板为 `Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint {endpoint_arn}`。示例代码逐步给出“先订阅成功 → `delete_endpoint` → **最后一次订阅应抛异常**”（Expected result）。

题面的读法没有公开反证，因此以题面为准。依据如下：

- **有公开依据的部分**：删除端点后订阅本身仍然存在。镜像内 botocore 1.35.9 的 `DeleteEndpoint` 文档写道：“When you delete an endpoint that is also subscribed to a topic, then you must also unsubscribe the endpoint from the topic.”
- **只有私有依据的部分**：gold 注释的读法是“删除后再次订阅应返回旧订阅”。这一点公开材料没有依据；`Subscribe` 文档、base 中的 moto 代码、文档与 CHANGELOG 里都找不到。
- 按 v1 §4，核心要求以题面为准，所以不按 P5 交用户。
- AWS 的实际行为无法在 base 上实跑证实，所以也不能用 R-f 按 gold 的读法改题面。

## 2．环境

镜像 `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-7584`，摘要 `sha256:3b263c0c…2fbf9`，image ID `437ec771…`，均与记录一致。

正式评分使用 09-19 的 install_wave1 离线安装配方，在云端按原 Dockerfile 文本重建：

- 三个 wheel（`setuptools 72.1.0`、`wheel 0.43.0`、`packaging 24.1`）的 SHA256 与 09-29 登记逐一相同。期望摘要来自 `swegym_cpu_preprobe_20260929/tasks/getmoto__moto-6114/result.json` 的 `environment.wheel_manifest`；packaging 另见 `env_recipe_repair_20260919/recipe_manifest.json`。
- 下载参数是 `--python-version 3.12`，历史为 3.9；三个都是 py3-none-any wheel，字节相同，因此无影响。
- 原 13 层保留，新增 1 层。派生 ID `sha256:c0569089…f239`，本机构建。重建记录见 [evidence/derived_image.json](evidence/derived_image.json)；09-19 本题的逐题 `image.json` 不在仓库内。
- 私有对照用原镜像。

## 3．实测结果

**（1）私有行为对照**：root、断网、`mock_aws`。

| 版本 | 题面原例：删除后再订阅 | 从未订阅的已删端点 | 从未创建的端点 | 有效端点重复订阅 | sqs／email |
| --- | --- | --- | --- | --- | --- |
| base | 成功（缺陷复现） | 成功 | 成功 | 同一 ARN | 正常 |
| gold | **仍然成功**（未修题面原例） | 报错，正文 `…for endpoint arnarn:aws:…` | 报错 | 同一 ARN | 正常 |
| `stmt`：检查放在旧订阅查重之前，正文按题面模板 | 报错 `…for endpoint arn:aws:…` | 报错 | 报错 | 同一 ARN | 正常 |
| `stmt_arnmsg`：同上，正文为 `arn{endpoint}` | 报错 | 报错 | 报错 | 同一 ARN | 正常 |
| `gold_order_stmtmsg`：gold 的检查位置，题面正文 | 仍然成功 | 报错 | 报错 | 同一 ARN | 正常 |

公开测试 `test_application_boto3.py` 与 `test_subscriptions_boto3.py`（base 版）在五个版本下都是 38 项通过。独立复核另外在私有环境中确认，`stmt` 下整个 `tests/test_sns` 共 184 项通过。

**（2）原材料正式评分**：F2P 1 项，P2P 19 项。

| 候选 | reward | 说明 |
| --- | --- | --- |
| noop | 0 | 与 09-19 一致 |
| gold | 1 | 与 09-19 一致；但题面原例未修 |
| `stmt` | **0** | 错误码断言已通过，唯一差异是正文 `arn:aws…` 与期望的 `arnarn:aws…`；`stmt_arnmsg` 只改正文即得 1，原因由此隔离 |
| `stmt_arnmsg` | 1 | |
| `gold_order_stmtmsg` | 0 | 正文不同 |
| `reject_all_arnmsg`：application 一律报错 | **1** | 退化候选。19 个 P2P 中没有订阅有效 application 端点的测试 |

另有一个“对所有协议都校验端点”的候选，独立复核在私有测试中用原测试跑出 20/20。它会让公开 `test_subscriptions_boto3.py` 失败 11 项。所有正式评分：参考缺席 0，安装失败 0，测试段完整，清理成功。

## 4．判定（v1 §3–§4）

- **G1＋§4 第 4 步（S1）**：gold 得 1，却在题面 Expected result 所指的原例上不报错。原测试对一般情形（删除后首次订阅）有直接断言，缺的是原例这一实例。
- **T1**：报错正文要求 `arnarn:` 这一未公开细节，按题面模板实现的修法被判 0。
- **T2b／T6（S1，§4 第 3 步）**：
  - 退化候选“application 一律报错”得 1；
  - “对所有协议都校验端点”在原测试下也通过。

  两者的根因相同：P2P 只有 `test_application_boto3.py`，这个文件里没有任何 `subscribe` 调用。
- **T2c（S1，§4 第 2 步，D1 严格版）**：所有“不存在”的实例都是“先创建后删除”，与题面示例同一种输入形态；从未创建过的 ARN 没有断言。

## 5．修法（交第2类）：修订版测试草案 v3

**草案文件**：[`revised_test_v3.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/moto7584/revised_test_v3.patch)，sha256 `58875207…4fd3`；父版本 v2 为 `5da7fefb…db9f`，v1 为 `a4dbe106…f598`。

原 F2P `test_publish_to_deleted_platform_endpoint` 编号保留，不改测试命令，不新增 P2P 文件。

| 断言 | 公开依据 | 拦下的错误候选 |
| --- | --- | --- |
| 从未订阅的已删端点：错误码 `InvalidParameter`，正文含 `Endpoint does not exist` 和该端点 ARN；不锁定 `arn` 与 ARN 之间是否有空格（R-b） | 题面错误码与正文模板 | noop、`wrong_code` |
| 题面原例：有效端点先订阅成功，删除后再订阅报同样的错（R-c） | 题面示例与 Expected result | gold、`gold_order_stmtmsg`、两个 `reject_all_*`（有效端点首次订阅失败） |
| 从未创建过的端点 ARN 同样报错（R-c，非示例实例） | 标题“when the endpoint does not exist”、正文“subscribing a non-existing endpoint” | `deleted_set` |
| 非 application 协议照常订阅成功：email，以及以 SQS 队列 ARN 为端点的 sqs 订阅（R-c） | 题面限定“using `application` protocol”；公开旧测试 `test_subscriptions_boto3.py` | `all_protocols`（在 email 处）、`arn_form`（在 SQS 处） |

**v3 正式诊断评分**：`--materials`，grader 后缀 `+c3-moto7584-issue-example-v3`，同一派生镜像。

| 候选 | reward | 失败位置 |
| --- | --- | --- |
| `stmt`（正对照，题面正文） | **1** | |
| `stmt_arnmsg`（正对照，AWS 形态正文） | **1** | |
| noop | 0 | 首处 `DID NOT RAISE` |
| gold | 0 | 原例 `DID NOT RAISE`，按 D4 记录 gold 失败 |
| `gold_order_stmtmsg` | 0 | 原例 `DID NOT RAISE` |
| `reject_all_application` | 0 | 有效端点订阅被拒 |
| `reject_all_arnmsg` | 0 | 有效端点订阅被拒 |
| `wrong_code` | 0 | `'NotFound' == 'InvalidParameter'` |
| `all_protocols`（去掉协议条件；等同复核的 `db_pre_*`） | 0 | email 订阅被拒 |
| `deleted_set`（只拒删除过的 ARN） | 0 | 从未创建的 ARN 未报错 |
| `arn_form`（凡 ARN 形式的端点都按 platform endpoint 校验，不论协议） | 0 | SQS 队列 ARN 订阅被拒 |

所有评分参考缺席 0，清理成功。v1（8 个候选）与 v2（10 个候选，除 `arn_form` 外结果与上表相同）保留在 `evidence/formal_revised_v1/`、`formal_revised_v2/`，仅作历史。

**交接给第2类：**

1. 经 D6 的“测试补丁替换”切片形成正式材料版本。首片不支持；该类型计划随后续的 MONAI5932 切片引入。
2. 替代正对照 `stmt` 已由独立复核在私有层面核实：题面原例报错、从未创建的 ARN 报错、重复订阅返回同一 ARN、http/sms 订阅正常，`tests/test_sns` 184 项通过。
3. 正式版本复验上表。
4. Codex 复核。
5. 评分使用重建的 install_wave1 配方，见 §2。

**非阻断建议**（留给第2类决定）：

- 修订后的 F2P 仍带 `@pytest.mark.aws_verified`，新增断言没有在 AWS 上验证过；email、SQS 正例在真实 AWS 上会发确认或留下队列。建议去掉该标记，或把新增部分拆成不带标记的测试。评分走 mock，不影响分数。
- 可以把正文检查收紧为正则 `Endpoint does not exist for endpoint (arn)?<ARN>`。
- 可以补一条“有效端点重复订阅返回同一 ARN”。

## 6．当前用途（v1 §2）

| 版本 | 问题定位 | 能力比较 | 训练候选 | 留出评测 |
| --- | --- | --- | --- | --- |
| 原版 | 是 | 否 | 否 | 否 |
| 修订版 | 经 D6 入库并通过验收后重新评估 | | | |

原版不能用于能力比较、训练和留出，原因是存在 T1 误拒、G1，以及三类退化候选满分。

## 7．独立复核（已完成）

复核结论为“部分同意”，见 [review_initial.md](review_initial.md)（先于读作者材料封存）和 [review.md](review.md)。

- **同意的部分**：G1、T1、T2b 成立；不属于 P5；`stmt` 作正对照；派生镜像与历史配方内容等价；14 行账本与日志逐行相符。
- **阻断项及处理**：
  - N1（所有协议都校验）与 N2（从未创建的 ARN）：已在 v2 修正，正式评分为 0；
  - `result.md` 需更新：已更新。
- **v2 聚焦复核**（review.md 末尾“六、v2 聚焦复核”）：阻断项 1–3 已落实，无阻断；`db_pre_arn` 与 `all_protocols` 等价；提出非阻断建议“email 正例拦不住凡 ARN 都校验的候选”，已在 v3 补 SQS 正例落实，`arn_form` 正式评分为 0。
- **非阻断项及处理**：
  - S1 措辞：已改；
  - S3 派生镜像出处：已补；
  - S4 用途：已写；
  - S5 T2a 说法：已精确化；
  - S6 配方：已写；
  - S2、S7：列为交接建议。

## 8．未做与剩余事项

- 真实 actor 开发条件未验。
- 真实 AWS 的报文和订阅语义未核。本项目不调用真实 AWS，修订版只按 moto 行为验收，与上游私有的 AWS 观察存在已知分歧（见 §1）。
- 没有模型求解证据。

## 9．版本与证据

- 代码与运行环境：见 [环境说明](../../environment.md)。
- 派生镜像配方：`rh2/experiments/category3_cloud_20260929/rebuild_install_wave1.py`。
- 候选补丁：`rh2/experiments/category3_cloud_20260929/moto7584/`。
- 原始证据：[evidence/](evidence/)，其中 `formal/` 为原材料评分，`formal_revised_v1/`、`formal_revised_v2/`、`formal_revised_v3/` 为修订版评分，`semantic_v1/` 为私有对照；全部文件的 SHA256 见 `evidence_manifest.json`。
