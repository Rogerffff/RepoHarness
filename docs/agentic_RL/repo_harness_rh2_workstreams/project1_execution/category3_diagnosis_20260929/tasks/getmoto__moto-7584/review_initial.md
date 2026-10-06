# getmoto__moto-7584 独立复核：初判（封存稿）

- 日期：2026-09-29；角色：第3类题目诊断的独立复核者，不继承作者上下文。
- **写作时点：在阅读作者的 `result.md`、`evidence/` 和 `rh2/experiments/category3_cloud_20260929/moto7584/` 之前写成，写完后不再修改。**
- 证据层级：本稿全部来自静态阅读，包括原件，以及用 `--network none` 的只读 docker 查看 base 源码和镜像内的 botocore 文档。**没有运行任何测试、gold 或候选。**

## 读过的材料

| 材料 | 位置 | 备注 |
| --- | --- | --- |
| 公开题面 | `docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/public_bundles_v0.jsonl` 第 110 行的 `problem_statement` | sha256 `572c500f…`，与登记值一致。下文“题面 Ln”指题面文本去掉 `\r` 后用 `cat -n` 数出的行号 |
| gold | `validation_bundles_v0.jsonl` 第 110 行的 `golden_patch` | sha256 `42595779…`，与登记值一致。“gold Ln”指补丁文本的行号 |
| 测试补丁、F2P/P2P | `grading_bundles_v2_v0.jsonl` 第 110 行 | `test_patch` sha256 `5b1c7b7a…`；F2P 1 个，P2P 19 个，全部在 `tests/test_sns/test_application_boto3.py`。“test Ln”指补丁文本的行号 |
| 既有调查 | `swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch02/results/getmoto__moto-7584/` 下的 `card.md`、`review.md`、`public_read.md` | 09-21 的静态审查 |
| base 源码 | 镜像 `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-7584:latest`，`/testbed` HEAD 为 `cc1193076090…` | `moto/sns/models.py`、`exceptions.py`、`responses.py`，`tests/test_sns/__init__.py`、`test_application_boto3.py`、`test_subscriptions_boto3.py`，`docs/docs/contributing/development_tips/tests.rst`，以及 botocore 1.35.9 的 `botocore/data/sns/2010-03-31/service-2.json.gz` |

## (a) 公开题面要求什么

题面原文要点：
- 标题（题面 L1）：使用 `application` 协议时，如果 endpoint 不存在，`subscribe` 应抛 `InvalidParameterException`。
- 正文（L2）：“moto allows subscribing a non-existing endpoint to a topic when the `application` protocol is used”，并说明 AWS 会报 `(InvalidParameter) … Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint {endpoint_arn}`。
- 例子（L21–33）：对有效 endpoint 的第一次订阅 “Works as expected”；接着 `delete_endpoint`；再用同样参数订阅，注释为 “Should raise InvalidParameterException”。
- 期望结果（L37）：“The last call to `subscribe` should raise `InvalidParameterException`”。

初判：
1. **核心要求**按 §4 的定义取标题和期望行为，并按一般性理解：用 `application` 协议订阅、而 endpoint 不存在时，报 `InvalidParameter`（HTTP 400）。**“先订阅、删除端点、再订阅应报错”就是期望结果原文所指的情形，属于核心要求本身，不是审查者另加的边界。** 标题的一般表述也覆盖“删除后第一次订阅”和“从未存在过的 ARN”。
2. 题面同样给出了应保留的行为：有效 endpoint 的 application 订阅应当成功（L25 “Works as expected”），所以不能一律拒绝 application。其它协议不在本题范围内，应保持原行为。
3. **gold 在原例上不会报错**（静态推断）。base `moto/sns/models.py:514–517` 一旦查重命中就直接 `return old_subscription`；`:714–716` 的 `delete_endpoint` 只删除 `platform_endpoints` 里的条目，不删订阅；gold 把检查插在这段提前返回之后（gold L5–9）。所以按题面序列，第二次订阅会命中旧订阅并直接返回，不抛异常。第二步需要实跑确认。
4. gold 注释（gold L12）说 “Existing subscriptions are still found if an endpoint is deleted, at least for a short period”。这句话的依据情况如下：
   - 公开材料里**找不到**“删除 endpoint 后用同样参数再订阅，应返回旧订阅、不报错”的依据。题面的说法正好相反（L33、L37），并且称这就是 AWS 的行为（L2）。
   - 公开旁证只能支持一半。镜像内 botocore 1.35.9 的 SNS `DeleteEndpoint` 文档写着：“When you delete an endpoint that is also subscribed to a topic, then you must also unsubscribe the endpoint from the topic.” 这说明 AWS 删除 endpoint 不会顺带删除订阅，与 base 一致；但它**没有说**再次 Subscribe 会跳过 endpoint 校验、直接返回这条订阅。`Subscribe` 的文档也没有相关说明。base `models.py:514` 的注释 “AWS doesn't create duplicates” 只说明有效的重复订阅是幂等的，同样不涉及已删除的 endpoint。
   - 这句话的直接来源只有 gold 注释和私有测试上的 `aws_verified` 标记（test L8），两者都是私有材料，本轮也没有、也无法核实 AWS 的实际行为。
   - 结论：按 §4“核心要求以公开题面为准，gold 的实现范围不决定需求”，原例属于核心要求。gold 注释不能算作一种与题面对等、有公开依据的读法，**初判不属于 P5**。这里登记一个风险：如果将来用户决定“以真实 AWS 行为为准”优先于题面，且维护者对 AWS 的观察属实，那么题面原例本身就成了错误陈述。那是改变规则层面的选择；按现行 §4，本题不需要为此交给用户。

## (b) 报错正文 `arn{endpoint_arn}`（即 `arnarn:aws:…`）的断言有没有公开依据

- 测试（test L40–44）要求 `err["Message"] == f"Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint arn{endpoint_arn}"`。endpoint ARN 本身已经以 `arn:` 开头（base `models.py:347`），所以测试实际要求的是 `…for endpoint arnarn:aws:sns:…`。
- 公开题面 L2 写的是 `…for endpoint {endpoint_arn}`，照字面实现得到的是 `…for endpoint arn:aws:sns:…`。在 base 的 `moto/`、`tests/`、`docs/` 中检索 py/rst/md/json 文件，`does not exist for endpoint`、`Endpoint Reason`、`for endpoint arn` 都没有命中；botocore 文档里也没有这段报文。
- 多出来的 `arn` 只有 gold 注释 L15（“Space between `arn{endpoint}` is lacking in AWS as well”）和 `aws_verified` 标记作依据，两者都是私有材料。
- 初判：**这条断言没有公开依据，而且与题面字面冲突。** 一个照题面正文实现、其它方面都正确的解，会只因这一个字符串在 F2P 上失败，属于 P2（照题面做会判 0）；问题出在测试一侧，归 T1（精确文案没有公开依据），处置走 R-b。不能用 R-f 把 `arn` 前缀写进题面：R-f 不允许把隐藏测试的精确文案写进题面，AWS 的实际报文也无法在 base 上实跑证实。
- 有公开依据、修订时应保留的部分有两项：
  - 错误码 `InvalidParameter`：依据是题面 L2，以及 botocore 中 `InvalidParameterException` 的形状（`code: InvalidParameter`，`httpStatusCode: 400`）；
  - 报文说明 endpoint 不存在，并带出请求中的 endpoint ARN：依据是题面 L2。
- moto 贡献文档 `docs/docs/contributing/development_tips/tests.rst:10–22` 建议负面测试同时断言 Code 和 Message。这是测试的写法约定，不能为这段报文的精确格式提供依据。

## (c) P2P 是否保护“有效端点可以订阅”

- **不保护。** 19 个 P2P 全部位于 `tests/test_sns/test_application_boto3.py`。base 中这个文件共 19 个测试函数，`subscribe` 一次都没有出现（`grep -n subscribe` 无输出）。F2P 也只在删除 endpoint 之后订阅了一次（test L31–38），没有成功订阅的路径。
- 其它协议（SQS/HTTP/email/SMS）的订阅同样没有保护。公开的 `tests/test_sns/test_subscriptions_boto3.py`（19 个测试，例如 `test_subscribe_sms`、`test_double_subscription`、`test_creating_subscription`）不在 P2P 里。
- 静态推论（未实跑）：在原材料上，至少以下两种退化候选会得 1：
  - **D-a**：对 application 协议一律抛 `SNSInvalidParameter`，报文与 gold 相同。它违反题面 L25 的 “Works as expected”。
  - **D-b**：去掉协议条件，对所有协议都校验 platform endpoint。它违反“using `application` protocol”这一限定，并破坏有公开旧测试的 SQS/HTTP/SMS 订阅，即 §4 第 4 步说的“有文档、常用的公开行为”。
- 按 §4 第 3 步，D-a 如果实跑得 1，就是 S1（T2b）。

## (d) 处置

**初判：做 R-b 加 R-c 的测试层修订，按 D4 用经独立核实的替代解作正对照；不走 R-f，不属于 P5，不弃题。** 在 SWE-Gym 修订机制实现之前（§9 D6），原版只能用于问题定位，不进能力比较的分母，也不进训练。

需要的修订，每一处只针对一个窄问题：
1. **R-b（T1/P2）**：把 F2P 的报文断言放宽为有依据的行为断言：`Code == "InvalidParameter"`，Message 能表明 endpoint 不存在（例如包含 `Endpoint does not exist`），并且包含请求的 `endpoint_arn`。这样 `arn:` 和 `arnarn:` 两种报文都会被接受，但不能放宽到“任意带 ARN 的 InvalidParameter 报错都通过”。这是文案层面的放宽，不属于 P5。
2. **R-c（§4 第 4 步；G1。参考测试对原例没有直接断言，也碰到第 1 步）**：补上题面原例：有效 endpoint 第一次订阅成功，然后 `delete_endpoint`，再用同样参数订阅，应抛 `InvalidParameter`。gold 预计在这一条失败，因此按 D4 用经独立核实的替代解作正对照，并记录 gold 的失败。
3. **R-c（§4 第 3 步；T2b）**：补正例：对有效 endpoint 的 application 订阅应成功并返回 `SubscriptionArn`，用来拦住 D-a。
4. **R-c（建议在同一轮完成）**：从公开的 `test_subscriptions_boto3.py` 中至少选一个非 application 协议的订阅测试加进 P2P，用来拦住 D-b。
5. **可选**（按 D1 严格版，成本很低）：补一个从未创建过的 endpoint ARN 实例，对应标题的一般表述，避免测试只覆盖“删除过的 endpoint”这一种输入形态。

验收预期：
- 正对照（使用题面报文，并在查重之前校验 endpoint）得 1；
- gold 得 0，原因是原例失败，按 D4 记录；
- D-a、D-b 得 0；
- noop 得 0。

## 初判未查

- 没有运行任何测试、gold、候选或正式评分；上文所有“得 1”“不报错”都是静态推断。
- 没有联网核对 AWS 的实际报文，也没有核对 AWS 上删除 endpoint 后的订阅行为；只读了镜像内的 botocore 文档。
- 没有读作者的 `result.md`、`evidence/`、候选补丁和脚本，也没有读批次 README 或其它题目。
