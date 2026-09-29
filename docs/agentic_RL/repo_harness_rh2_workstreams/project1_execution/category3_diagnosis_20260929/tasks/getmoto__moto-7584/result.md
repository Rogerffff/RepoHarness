# getmoto__moto-7584：第3类诊断结果

2026-09-29 / Claude（云端，第3类负责人）。原分类为第3类，缺口是“具体疑点缺辨别实验”：需执行题面“先订阅、删除、再订阅”的序列并做正式评分，确定问题出在 gold 遗漏还是规格解释。

**结论：问题和修法已明确，建议转第2类。** 原材料确认有三处问题：

1. gold 没有修好题面原例，题面原例也没有断言（G1＋T2a）；
2. 隐藏测试锁定的报错正文超出题面模板，导致按题面实现的修法被拒（T1）；
3. 退化候选“application 协议一律报错”能得满分（T2b，S1）。

修订草案与替代正对照已通过诊断评分。实施依赖 SWE 正式修订入口（D6）。独立复核待做。

## 1．公开要求

题面要求：`application` 协议订阅不存在的端点时，抛 `InvalidParameterException`，错误码为 `InvalidParameter`，正文模板为 `Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint {endpoint_arn}`。示例代码明确写了三步：先订阅成功，然后 `delete_endpoint`，**最后一次订阅应抛异常**（Expected result）。

gold 的注释称“AWS 上已存在的订阅在端点删除后短期内仍可找到”，这一说法只出现在私有材料里。按 v1 §4，核心要求以题面为准，gold 的实现范围不决定需求。题面没有给出另一种读法，因此不按 P5 处理。

## 2．环境

镜像 `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-7584`，摘要 `sha256:3b263c0c…2fbf9`，image ID `437ec771…`，均与记录一致。

正式评分使用 09-19 的 install_wave1 离线安装配方，在云端按原 Dockerfile 文本重建：`setuptools 72.1.0`、`wheel 0.43.0`、`packaging 24.1` 三个 wheel 的 SHA256 与 09-29 批次登记逐一相同；原 13 层保留，新增 1 层。派生 ID 为 `sha256:c0569089…f239`，评分以 `image_local_build` 方式运行。私有对照使用原镜像。

## 3．实测结果

**（1）私有行为对照**：root、断网、`mock_aws`。

| 版本 | 题面原例：删除后再订阅 | 从未订阅的已删端点 | 从未创建的端点 | 有效端点重复订阅 | sqs／email |
| --- | --- | --- | --- | --- | --- |
| base | 成功（缺陷复现） | 成功 | 成功 | 同一 ARN | 正常 |
| gold | **仍然成功**（未修题面原例） | 报错，正文 `…for endpoint arnarn:aws:…` | 报错 | 同一 ARN | 正常 |
| `stmt`：检查放在旧订阅查重之前，正文按题面模板 | 报错 `…for endpoint arn:aws:…` | 报错 | 报错 | 同一 ARN | 正常 |
| `stmt_arnmsg`：同上，正文用 `arn{endpoint}` | 报错 | 报错 | 报错 | 同一 ARN | 正常 |
| `gold_order_stmtmsg`：gold 的检查位置，题面正文 | 仍然成功 | 报错 | 报错 | 同一 ARN | 正常 |

公开测试 `test_application_boto3.py` 与 `test_subscriptions_boto3.py`（base 版）在五个版本下均为 38 项通过。

**（2）原材料正式评分**：F2P 1 项，P2P 19 项。

| 候选 | reward | 说明 |
| --- | --- | --- |
| noop | 0 | 与 09-19 一致 |
| gold | 1 | 与 09-19 一致；但题面原例未修 |
| `stmt` | **0** | 唯一差异是正文 `arn:aws…` 与期望的 `arnarn:aws…` 不同（日志逐字核对）。按题面实现被拒 |
| `stmt_arnmsg` | 1 | |
| `gold_order_stmtmsg` | 0 | 正文不同 |
| `reject_all_arnmsg`：application 一律报错 | **1** | 退化候选。19 个 P2P 里没有订阅有效 application 端点的测试 |

所有正式评分：参考缺席 0，安装失败 0，测试段完整，清理成功。

## 4．判定（v1 §3–§4）

- **T2a＋G1（S1）**：题面 Expected result 所述的原例没有断言，gold 在旧订阅查重处提前返回，不满足该原例却得 1（§4 第 4 步：得 1 的候选违反同一核心要求的实例）。
- **T1**：正文要求 `arnarn:` 这一未公开细节，按题面模板实现的修法被判 0，属于误拒。
- **T2b（S1）**：退化候选“一律拒绝”得 1（§4 第 3 步）。

## 5．修法（交第2类）

**修订版测试草案 v1**：[`revised_test_v1.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/moto7584/revised_test_v1.patch)，sha256 `a4dbe106…f598`。保留原 F2P 编号 `test_publish_to_deleted_platform_endpoint`，改动三处：

- 报错断言改为三项行为检查：错误码为 `InvalidParameter`，正文含 `Endpoint does not exist`，正文含该端点 ARN。不再锁定 `arn` 与 ARN 之间是否有空格（R-b）。
- 补上题面原例：有效端点先订阅成功，删除后再订阅必须报错（R-c）。这一步同时保护有效端点可以订阅，因此能拒绝“一律报错”的退化。
- 保留原有的“从未订阅的已删端点”检查。

**修订版诊断评分**（`--materials`，grader 后缀 `+c3-moto7584-issue-example-v1`，使用同一派生镜像）：

| 候选 | 修订版 reward |
| --- | --- |
| noop | 0 |
| `stmt`（正对照，题面正文） | **1** |
| `stmt_arnmsg`（正对照，AWS 形态正文） | **1** |
| gold | 0（未修原例，按 D4 记录 gold 失败） |
| `gold_order_stmtmsg` | 0 |
| `reject_all_application`（一律报错，题面正文） | 0 |
| `reject_all_arnmsg`（一律报错，隐藏正文；原材料下得 1） | 0 |
| `wrong_code`（检查位置正确，但抛 NotFound） | 0 |

参考缺席 0，清理均成功。

**交接给第2类的事项：**

1. 经 D6 做成正式材料版本；
2. 独立 reviewer 核实 `stmt` 可作替代正对照，确认它满足全部公开要求且不破坏相关旧行为，公开订阅／应用测试 38 项已过；
3. 复验上表；
4. Codex 复核。

## 6．未做与剩余事项

- **独立复核待做。** 特别请复核“题面原例优先于 gold 注释中的 AWS 行为说法”这一判定。若复核认为 AWS 实际语义有公开依据，此项转为 P5，由用户选择；报错正文与“一律报错”两项修订仍然成立。
- 真实 actor 开发条件本次未验。
- `aws_verified` 标记表示该测试可对真实 AWS 运行。修订版新增的原例在真实 AWS 上的结果未知，本项目也不做真实 AWS 调用，因此修订版只按 moto 行为验收。
- 没有模型求解证据。

## 7．版本与证据

- 代码：分支 `claude/category3-20260929`，基于 `4a969c3`。评分路径同 [环境说明](../../environment.md)。
- 派生镜像配方：`rh2/experiments/category3_cloud_20260929/rebuild_install_wave1.py`，重建记录（wheel 清单、base/derived 身份）见 [evidence/derived_image.json](evidence/derived_image.json)。
- 原始证据：[evidence/](evidence/)，文件清单与 SHA256 见 `evidence_manifest.json`。
