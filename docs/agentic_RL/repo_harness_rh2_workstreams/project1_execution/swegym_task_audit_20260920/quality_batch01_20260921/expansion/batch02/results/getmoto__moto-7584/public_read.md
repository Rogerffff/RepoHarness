# getmoto__moto-7584 公开阅读记录

本次仅静态阅读角色卡和本题公开包。未运行项目代码、测试、安装、容器或网络查询，未修改 `base/`。以下源码定位、预期运行现象均为静态推断，不能视为复现成功或环境验证。

公开包：`runs/swegym_quality_batch02_20260921_v2/public/getmoto__moto-7584/`。下文文件位置均相对该目录；源码文件以 `base/` 开头。固定基线为 `cc1193076090f9daf90970db286b6b41581dd8bc`（`public_bundle.json:1`、`base_identity.json:3`）。

## 1. 需求与保留行为

| 行为 | 要求与边界 | 证据与确定程度 |
| --- | --- | --- |
| application 协议订阅不存在的 endpoint | `Subscribe` 应拒绝请求，客户端得到 `InvalidParameterException`。不限于题面中一个固定 ARN。 | **明示**：`user_prompt.txt:3-4,31-39`。标题覆盖不存在的 endpoint，示例具体覆盖删除后的 endpoint。 |
| 先成功订阅，删除 endpoint，再对原 topic/endpoint 订阅 | 第二次订阅也必须报错；不能因已经存在相同订阅而返回成功。 | **明示**：`user_prompt.txt:23-35`。**代码线索**：`base/moto/sns/models.py:514-517` 提前返回旧订阅，`:714-718` 删除 endpoint 时未清除订阅。 |
| 存在的 endpoint | 创建 platform application 和 endpoint 后，第一次 application 订阅仍成功。 | **明示**：`user_prompt.txt:10-27` 的 `Works as expected`。不应把 `application` 一律禁用。 |
| 错误代码和文本 | 服务错误代码应为 `InvalidParameter`；消息正文应为 `Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint {endpoint_arn}`，其中 ARN 使用请求值。 | **明示**：`user_prompt.txt:4` 给出 AWS 客户端错误串。**仓库约定**：`base/moto/sns/exceptions.py:45-49` 已有对应服务错误；`base/docs/docs/contributing/development_tips/tests.rst:13-24` 要求同时检查错误代码和消息。 |
| SDK 异常名称与服务响应代码 | Python SDK 的 `InvalidParameterException` 不意味着把响应 `Code` 改为同名字符串；也不要求新增一个同名 Moto 内部异常类。 | **可由公开接口合理推知**：题面在同一句给出异常名称和 `InvalidParameter` 代码；`base/moto/sns/exceptions.py:45-56` 区分 `InvalidParameter` 与 `InvalidParameterValue`。客户端异常映射仍应由运行验证确认。 |
| HTTP 错误形状 | 沿用 SNS 的 HTTP 400、Sender 类型和现有错误封装。不要把 SDK 的 `An error occurred ...` 前缀重复塞入服务 `Message`。 | **仓库约定**，题面未单独明示状态码：`base/moto/sns/exceptions.py:6-9,45-49`；`base/moto/core/exceptions.py:16-27,43-74`。题面完整错误串是客户端呈现。 |
| 其他协议及正常重复订阅 | 保留 SMS 的格式校验；保留 HTTP/邮箱等普通订阅；正常重复订阅仍应返回相同 ARN。不能对所有协议要求 SNS platform endpoint 已存在。 | **公开旧测试/代码**：`base/tests/test_sns/test_subscriptions_boto3.py:15-78`、`:82-104`、`:174-208`；其中 `test_double_subscription` 在没有创建对应 SQS queue 的情况下使用固定 endpoint（`:29-43`）。`base/moto/sns/models.py:502-548`。 |
| 订阅属性与返回值 | 保留成功订阅的 `SubscriptionArn`、属性设置及过滤策略路径；验证应在非法请求造成新增订阅或属性变更之前完成。 | 前半为**公开旧测试/代码约定**：`base/tests/test_sns/test_subscriptions_boto3.py:211-310`；`base/moto/sns/responses.py:221-255`。失败请求不产生新订阅是**合理接口推断**，题面未明确讨论已有订阅的清理。 |
| 其他 endpoint 操作 | 不应全局把 `get_endpoint` 的缺失错误改为 `InvalidParameter`；`GetEndpointAttributes` 对不存在 endpoint 的 `NotFound` 行为应保留，重复删除 endpoint 仍应幂等。 | **明确的公开旧测试**：`base/tests/test_sns/test_application_boto3.py:270-275,311-326,473-492`；实现为 `base/moto/sns/models.py:699-718,1088-1090`。 |

尚有多种合理解释、但不妨碍核心开发的边界：

- **跨账号或跨区域的“存在”范围**：题面只用一个 client，没有跨账号/区域实例。当前 `SNSResponse.backend` 按请求账号和区域选 backend，endpoint 存储也属于该 backend（`base/moto/sns/responses.py:23-25`、`base/moto/sns/models.py:392-397,699-703`）。按当前作用域校验是合理最小实现；公开材料不足以凭空要求新的全账号/全区域检索或跨区域策略。
- **多个参数同时无效时的错误优先级**：不存在 topic、错误 ARN 语法、无效订阅属性与 endpoint 缺失同时发生时，题面没有指定先报哪一个。已有代码先做 SMS 校验、查重、再取 topic（`base/moto/sns/models.py:502-519`）。核心要求仅确定 application endpoint 缺失不能绕过验证返回成功。
- **endpoint 删除时是否连带清理旧订阅**：题面只要求下一次 Subscribe 报错，没有要求修复删除副作用或清理历史订阅。不能把新增清理行为当作唯一正确解。
- **存在但 Disabled 的 endpoint**：公开实现把 Enabled 作为单独属性，发布时才检查（`base/moto/sns/models.py:351-368`）。本题没有要求订阅时增加 Enabled 校验，应避免把“不存在”扩展成“存在但不能发布”。

## 2. 调查入口与合理实现范围

公开材料足以给出具体调查链：

1. 题面给出完整资源创建顺序和出错的最后调用。只缺通常运行脚手架，例如 `import boto3`、`mock_aws` 和明确区域；这些可从 README 的 mock 用法（`base/README.md:44-63`）及本题 SNS 旧测试直接补齐，属于正常开发阅读，不是关键输入缺陷。
2. `SNSResponse.subscribe` 读取三个参数后直接调用 backend（`base/moto/sns/responses.py:221-227`）。backend 仅对 SMS 做 endpoint 校验，随后返回匹配的旧订阅或创建新订阅（`base/moto/sns/models.py:502-536`）。
3. platform endpoint 创建后进入 `platform_endpoints`，删除时从该字典移除（`base/moto/sns/models.py:659-688,714-718`）。订阅查重独立检查 topic ARN、endpoint 和 protocol（`:538-548`）。因此静态上可解释“从未创建的 endpoint 被接受”和“删除后旧订阅仍被返回”两条路径。

可接受的实现不应被绑定到某个新方法名、局部变量或代码行位置。至少存在以下合理路线：

- 在 backend 的 application 分支查 `platform_endpoints`，不存在时使用现有 `SNSInvalidParameter` 和题面消息；有效 endpoint 继续既有查重与创建流程。
- 在 application 分支复用 `get_endpoint`，只在该调用边界把 `SNSNotFoundError` 转换为要求的 `SNSInvalidParameter`，保留其他 `get_endpoint` 调用者原来的 NotFound 语义。
- 抽出一个只负责订阅 endpoint 验证的 helper，或为公用查询提供保持原默认行为的专用错误策略，也可以实现同样外部行为。没有公开依据要求必须新增异常类型或必须新增 helper。

不论结构如何，验证必须覆盖“找到旧订阅”分支。仅在新建 `Subscription` 前、但在 `return old_subscription` 后加验证，无法处理题面复现。仅在 `delete_endpoint` 清除订阅也不足以拒绝不存在 endpoint 的首次订阅。

把验证放在 response 层也可能满足题面中的 boto3 路径，不能仅凭函数布局否定它；但 backend 更适合维护统一行为，因为 CloudFormation 创建 SNS Topic 的内联订阅也直接调用 backend（`base/moto/sns/models.py:128-145`）。若选择 response 层，应说明该直接调用者的行为，不应遗漏调用路径差异。

本次检索未找到旧测试中的 `Protocol="application"`/同类直接订阅用例；已读旧测试分别覆盖订阅协议和 application endpoint 生命周期，没有读到二者串联的删除后重订阅断言。因此两个旧模块通过也不能单独证明本 issue 已修复。

版本信息不一致但不是核心定位障碍：issue 报告 Moto 5.0.3（`user_prompt.txt:41`）；固定导出源码 `base/moto/__init__.py:4` 为 `5.0.6.dev`，`base/setup.cfg:3` 另有静态版本字段。开发应以指定 commit 的源码和实际 import 位置为准，不能用包版本字符串代替基线确认。

## 3. Issue、操作指令与环境声明分开记录

| 类别 | 本题公开输入 | 本次判断 |
| --- | --- | --- |
| Issue 需求 | `user_prompt.txt:3-41` 及 `public_bundle.json:1` 的 `problem_statement` | application 订阅应拒绝不存在 endpoint；文本和复现足以确定核心行为。 |
| harness 操作指令 | `public_bundle.json:1` 的 `public_hints`：在 `/testbed` 调查、改 NON-TEST source、不改测试、允许窄范围运行、完成后简述并停止 | 属于原操作指令。本阅读任务未执行它们，也未擅自取消“禁止改测试”。若实际求解继续适用，源文件即可实现修复，复现可用临时 stdin 命令；若不适用，可把同一复现加入公开回归测试。两种情况都不要求通过改测试来规避错误。 |
| 旧机制解释 | 同字段称所有测试修改会恢复且永不计分 | `environment_brief.md:18-26` 明确指出此解释不能代表当前机制。当前没有按测试文件名统一排除，但仍有具体官方文件恢复限制；具体范围未由本角色核实。不能把旧解释当成当前事实，也不能据此给题目贴不可用标签。 |
| 工具/路径与可见性 | bundle 列 bash/edit、`/testbed`、镜像标识及 digest；`environment_brief.md:8,25-26` | 这是公开声明，不是工具实测。bundle 会写入真实解题容器的公开路径，字段未出现在渲染 `user_prompt.txt` 不能解释为解题者不可见。 |
| 待验环境事实 | public hints 称名为 testbed 的 conda 环境已激活；brief 描述 actor、CPU/内存/空间及网络边界 | 均未实际核验。`environment_brief.md:3-12` 明确是静态说明，不是实际模型请求或容器抓取记录。不能据此声明 Python、pip、pytest、文件权限或资源已可用。 |

本题的非测试源码修复路线未发现必须违反原“禁止改测试”指令的地方；该指令的真实消息适用状态仍应作为共享运行条件核对。

## 4. 开发条件与建议命令

以下全部为**建议，未执行**。命令面向真实 actor 在 `/testbed` 的执行环境；并非让审查者在静态 `base/` 上运行。默认采用进程内 `mock_aws`，避免把最小复现依赖扩大到真实 AWS、Firebase、Docker 或 Moto server。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 未证实项与最小命令/预期 |
| --- | --- | --- | --- |
| Python 解释器和源码导入 | `base/setup.cfg:27-37` 要求 Python >=3.8 和 boto3/botocore 等依赖；`base/pyproject.toml:1-3` 声明 setuptools 构建后端 | brief 仅声明 conda、actor 和待验状态（`:8-12,20-21`） | 建议命令 A。应导入当前工作区的 Moto、SNS 模型、pytest；import 错误是环境问题，不是 issue 已复现。 |
| 测试依赖、开发依赖 | `base/requirements-tests.txt:1-7`；`base/requirements-dev.txt:1-15`；SNS/SQS extras 无单独条目依赖（`base/setup.cfg:230-231`） | 未列实际已装包和锁定版本；网络不能假定允许公网下载 | 最小复现需 Moto 的直接依赖、boto3/botocore；旧测试需 pytest。若缺包，应补预装依赖/离线资产后再验证，不能假定可执行公网 pip install。 |
| SNS mock 资源 | 题面创建 topic、platform application、endpoint；`base/README.md:44-63`；`base/moto/sns/models.py:392-397,659-688` | 已有静态源码，无资源运行证明 | 建议命令 B，资源全部在 mock 上下文内创建；不需外部 ARN、账户密钥或 Firebase token。基线预计最后 Subscribe 不抛异常，触发显式 AssertionError；修复后捕获预期异常。 |
| 进程内测试模式 | `base/moto/core/decorator.py:25-37`；`base/moto/settings.py:10-15`；`base/tests/test_sns/__init__.py:11-48` | 模式环境变量未核验 | 建议命令 B/C 显式关闭 server/proxy/AWS 请求模式。`sns_aws_verified` 默认也使用 mock 和假 API key；仅主动打开 AWS 模式才需 SSM/Firebase 真资产，非本题最小条件。 |
| 相关旧测试 | `base/tests/test_sns/test_subscriptions_boto3.py`；`base/tests/test_sns/test_application_boto3.py`；贡献文档允许按服务跑 pytest（`base/docs/docs/contributing/installation.rst:45-53`） | brief 要求另做 actor CPU 验证（`:12-13`） | 建议命令 C，每次一个模块。基线可能全部通过，因为未读到本 issue 的组合断言；修复后也应保留这些旧行为。收集失败不能当作业务失败。 |
| 代码风格/构建 | `base/requirements-dev.txt:4` 固定 Ruff 0.3.3；`base/Makefile:20-27`；`base/pyproject.toml:1-7` | Ruff/构建工具是否安装未知 | 建议命令 D。本修复为 Python 源码条件校验，无必需编译产物或完整 wheel 构建步骤。全仓 `make test` 含 lint 和其他服务，不是最小验证需求。 |
| 资源/权限/文件资产 | `environment_brief.md:9-12`；`base_identity.json:5-12` | 说明默认 2 CPU/4 GiB、空间上限等；导出记录无 gitlinks、symlinks 或未物化 LFS | 这些不是本题实测。窄 SNS 测试看起来只需普通 CPU、可读源码及 pytest 临时目录；时长、峰值资源和 actor 写权限须运行确认。未发现本题所需子模块或专用大资产缺口。 |

**建议命令 A，未执行：最小导入与实际路径核对。**

```bash
cd /testbed
python -c 'import sys, moto, boto3, botocore, pytest; from moto.sns.models import SNSBackend; print(sys.executable); print(sys.version); print(moto.__file__); print(boto3.__version__, botocore.__version__, pytest.__version__)'
```

此命令应确认导入的是待修的源码。包依赖未完全锁定，版本输出只用于记录真实环境，不能预先声称与镜像一致。若包还未注册、依赖已完整预装且有相应写权限，可条件性建议 `python -m pip install --no-deps --no-build-isolation -e .`（**建议，未执行**）；这不替代依赖缺口调查。公开 `make init` 会安装大量依赖（`base/Makefile:16-18`），不应当作离线环境必定可用的步骤。

**建议命令 B，未执行：不修改测试文件的核心复现。**

```bash
cd /testbed
env MOTO_TEST_ALLOW_AWS_REQUEST=false TEST_SERVER_MODE=false TEST_PROXY_MODE=false AWS_EC2_METADATA_DISABLED=true python - <<'PY'
import boto3
from moto import mock_aws

with mock_aws():
    client = boto3.client("sns", region_name="us-east-1")
    app = client.create_platform_application(
        Name="test", Platform="GCM", Attributes={}
    )["PlatformApplicationArn"]
    endpoint = client.create_platform_endpoint(
        PlatformApplicationArn=app, Token="test-token"
    )["EndpointArn"]
    topic = client.create_topic(Name="test-topic")["TopicArn"]
    first = client.subscribe(
        TopicArn=topic, Endpoint=endpoint, Protocol="application"
    )["SubscriptionArn"]
    repeated = client.subscribe(
        TopicArn=topic, Endpoint=endpoint, Protocol="application"
    )["SubscriptionArn"]
    assert repeated == first
    client.delete_endpoint(EndpointArn=endpoint)
    try:
        client.subscribe(TopicArn=topic, Endpoint=endpoint, Protocol="application")
    except client.exceptions.InvalidParameterException as exc:
        assert exc.response["Error"]["Code"] == "InvalidParameter"
        assert exc.response["Error"]["Message"] == (
            "Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint "
            + endpoint
        )
        assert exc.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    else:
        raise AssertionError("Deleted application endpoint was accepted")
PY
```

静态预计基线在最后的 `else` 报 `AssertionError`；若依赖/环境没有先失败，才是在观察 issue 行为。修复后应退出成功。还可**建议，未执行**：在上述过程中新建另一个 topic，用已删除 ARN 做首次订阅；或使用同结构但从未创建的 endpoint ARN，检查同样的异常。这些是标题自然覆盖的补充用例，用于排除仅修复“旧订阅”特例。

**建议命令 C，未执行：两个公开旧测试模块分别运行。**

```bash
cd /testbed
env MOTO_TEST_ALLOW_AWS_REQUEST=false TEST_SERVER_MODE=false TEST_PROXY_MODE=false AWS_EC2_METADATA_DISABLED=true python -m pytest -q tests/test_sns/test_subscriptions_boto3.py
```

```bash
cd /testbed
env MOTO_TEST_ALLOW_AWS_REQUEST=false TEST_SERVER_MODE=false TEST_PROXY_MODE=false AWS_EC2_METADATA_DISABLED=true python -m pytest -q tests/test_sns/test_application_boto3.py
```

两者主要防止回归，不能取代命令 B。若调查中改动到 CloudFormation 通路，再按其依赖另选相关测试；本次未把该额外服务作为最小前置条件。

**建议命令 D，未执行：按最终改动文件缩小风格检查。**

```bash
cd /testbed
ruff check moto/sns/models.py moto/sns/exceptions.py moto/sns/responses.py
ruff format --check moto/sns/models.py moto/sns/exceptions.py moto/sns/responses.py
```

应使用仓库指定 Ruff 版本，实际修复仅涉及其中一个文件时可进一步缩小。此处没有建议执行会改动源码的自动格式化命令。

## 5. 实际阅读与暴露记录

实际打开或返回了内容的文件如下；范围是静态文本，部分为选段，不能据此声称通读全仓：

- 指定 `roles/public_reader.md` 全文。
- 公开包根目录：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json` 全文。
- 开发/安装材料：`base/README.md`、`base/CONTRIBUTING.md`、`base/docs/docs/contributing/installation.rst`、`base/docs/docs/contributing/development_tips/tests.rst`、`base/Makefile`、`base/requirements.txt`、`base/requirements-tests.txt`、`base/requirements-dev.txt`、`base/pyproject.toml`；`base/setup.cfg` 的 1-85、219-275 行及关键词匹配。
- 核心源码：`base/moto/sns/models.py` 的 1-180、188-250、315-380、385-570、635-730、1070-1115 行选段（一次输出截断后重读了关键 695-725、1080-1105 段）；`base/moto/sns/responses.py` 的 1-38、210-320、515-655 行选段（关键 subscribe 和 endpoint 段随后重读）；`base/moto/sns/exceptions.py`；`base/moto/core/exceptions.py` 的 1-160 行；`base/moto/core/decorator.py`；`base/moto/__init__.py`；`base/moto/settings.py` 只读模式变量的检索命中行；`base/docs/docs/services/sns.rst`。上述包含实际请求打开的选段；被工具输出截断而未完整呈现的部分不作为独立结论依据。
- 旧测试与测试支持：`base/tests/__init__.py`、`base/tests/test_sns/__init__.py`；`base/tests/test_sns/test_subscriptions_boto3.py` 的 1-339、436-476 行选段；`base/tests/test_sns/test_application_boto3.py` 的 1-28、117-139、240-336、360-388、470-493 行选段。
- 仅搜索命中行、未通读的文件包括 `base/tests/test_sns/test_topics_boto3.py`、`test_publish_batch.py`、`test_publishing_boto3.py`、`test_sns_cloudformation.py`；另在 `moto/`、`tests/` 的 Python/JSON/YAML 文本中检索 application 订阅和 backend 调用者。检索 `Protocol.*application|protocol.*application` 没有返回直接匹配；这不是运行覆盖率证明。
- 仅做目录/文件名枚举：公开包内 `rg --files`（输出过长截断）、SNS 测试文件列表及 conftest/AGENTS 文件名检索。未打开文件名枚举中的无关内容。一次元数据/依赖搜索误以公开包根目录为工作目录，返回找不到 `setup.cfg` 等；随后改为 `base/` 重查。`tests/conftest.py` 不存在的错误只是该候选路径不存在，不是依赖或测试失败。

未查项与限制：

- 没有打开私有评分材料、gold、未来修复、Git history、共享镜像克隆、其他题、批次结论或其他角色产物；没有请求或查阅外链。包内 `public_bundle.json` 的公开 image digest 已读，但没有打开任何独立 manifest 文件。
- 本题没有必须额外补充的公开外链或附件。README 和贡献文档中的外链未访问；核心复现、接口和已有源码均已在本地公开包中。若将验收扩大到跨账号/区域或多重无效参数优先级，才需要明确新增语义依据，不能擅自以最新 AWS/未来修复补齐。
- 未通读所有 SNS 测试、完整 CloudFormation 处理链、完整错误分发器或 boto3/botocore 安装包；没有验证客户端动态异常类型映射、JSON/XML 实际响应、CPU/内存、权限或离线依赖。
- `user_prompt.txt` 只是静态渲染；base 导出不是完整运行容器。`environment_brief.md:3-6,12,25-26` 对消息、构建产物、预装包和实际 shell 的限制仍全部保留。
- 未发生已知越界材料暴露。这是本次阅读范围和协作约定的记录，不是文件权限隔离、模型预训练无污染或实际 actor 输入已验的证明。

关键未决项是实际 actor 环境和原 harness 提示的应用状态；公开行为本身已有明确调查和修复入口。本文不为题目给出“通过/淘汰”标签。
