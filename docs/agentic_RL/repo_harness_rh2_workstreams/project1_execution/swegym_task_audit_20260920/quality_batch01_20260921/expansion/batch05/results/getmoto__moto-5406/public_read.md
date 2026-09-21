# getmoto__moto-5406 公开视角审查

本报告只依据本题公开包及公开视角角色卡，未读取私有评分、未来修复、历史或旧结论。下文文件位置均相对 `PUBLIC_DIR=runs/swegym_quality_batch05_20260921_v1/public/getmoto__moto-5406`。所有行为判断均为静态分析；没有导入项目、执行复现或测试。

公开材料足以定位一个具体问题：请求和存储后端已有区域信息，但 `Table._generate_arn` 将 ARN 的区域写成 `us-east-1`。题面“表被创建在 us-east-1”不能仅凭错误 ARN 当作存储区域已错的证据。题面还存在创建表名与断言表名不一致的问题，可由现有接口和测试消解，无需猜测隐藏验收。

## 1. 需求表

| 行为 | 公开依据 | 确定程度及应保留的行为 |
| --- | --- | --- |
| `us-east-2` 客户端创建表后，描述返回的 `TableArn` 应包含 `us-east-2` | `user_prompt.txt:3–6,25–31,53–56` | 明示。问题针对客户端所选区域与返回 ARN 不一致。 |
| 其他有效客户端区域也应得到相应区域的表 ARN | `base/moto/dynamodb/responses.py:134–140`；`base/moto/dynamodb/models/__init__.py:1181–1207`；`base/moto/core/utils.py:416–438,463–476` | 由通用区域路由合理推知；不应只为 Ohio 特判或把常量换成 `us-east-2`。题面没有逐一列出区域矩阵。 |
| ARN 保留实际表名及所属账户，不固定为 `test_table` 或固定账户 | 题面创建/描述名为 `mock_Foundational_AMI_Catalog`，断言却使用 `test_table`：`user_prompt.txt:39,53–56`；现有构造：`base/moto/dynamodb/models/__init__.py:413–414,452,568–569`；旧测试：`base/tests/test_dynamodb/test_dynamodb_create_table.py:13–45` | 题面示例有名称矛盾。合理目标是 `arn:aws:dynamodb:us-east-2:123456789012:table/mock_Foundational_AMI_Catalog`，或将输入表名统一改成 `test_table`。不能把错误示例字面值提升为“任意表返回 test_table”的约定。账户仍应来自当前账户；覆盖规则见 `base/moto/core/responses.py:339–352`。 |
| `CreateTable.TableDescription.TableArn` 与 `DescribeTable.Table.TableArn` 一致 | `base/moto/dynamodb/responses.py:240–252,360–363`；`base/moto/dynamodb/models/__init__.py:580–589,1262–1264` | 由两接口共用同一模型描述合理推知。不能只修复一个响应的显示字符串而使模型中的 ARN 仍然错误。响应键名与 ARN 的既有结构有约定。 |
| 区域/账户之间的后端隔离继续成立，同一地区的查表、标签等仍使用同一资源身份 | `base/moto/core/utils.py:479–485,508–521`；`base/moto/dynamodb/models/__init__.py:1182–1185,1200–1207,1222–1238`；`base/tests/test_dynamodb/test_dynamodb.py:20–35,72–106` | 应保留的既有设计；静态代码指向 ARN 元数据问题，没有证据要求迁移表或重写全局路由。实际隔离尚未执行验证。 |
| 开启流时，`LatestStreamArn` 与表 ARN 的区域和表名一致，相关 ARN 消费者继续可用 | 题面启用流：`user_prompt.txt:44–47`；派生字符串：`base/moto/dynamodb/models/__init__.py:599–605`；流服务：`base/moto/dynamodbstreams/models.py:29–35,71–77,100–115` | 合理推知的连带一致性。旧测试验证流字段与服务间一致性，但主要在 `us-east-1`，见 `base/tests/test_dynamodb/test_dynamodbstreams.py:13–77`。 |
| `us-east-1`、计费/吞吐、键/索引、标签、SSE 和普通读写的既有行为保留 | `base/tests/test_dynamodb/test_dynamodb_create_table.py:11–119,122–196,199–241,244–406`；`base/tests/test_dynamodb/test_dynamodb_table_without_range_key.py:12–72` | 公开回归约束。题面使用 `PAY_PER_REQUEST` 和关闭 SSE，但未要求改变它们；不能通过丢弃这些参数规避 ARN 问题。 |
| CloudFormation 和备份恢复创建的表仍获得与其后端区域一致的身份 | `base/moto/dynamodb/models/__init__.py:499–505,534–557,1052–1107,1821–1852`；`base/tests/test_dynamodb/test_dynamodb.py:5184–5217,5291–5358` | 同一模型及区域参数的现有调用路径，属于合理兼容范围；并非题面明示的新功能。备份 ARN 本身已使用后端区域，见同文件 `1131–1138`。 |
| 不另行规定私有 helper 名称、内部区域属性名或新的客户端默认区域 | `base/moto/dynamodb/models/__init__.py:398–412,568–569`；`base/moto/core/responses.py:197–201,307–323` | 内部组织方式没有题面约定。现有缺省区域解析仍应保留；本题不要求重新定义 boto3 未指定区域时的行为。 |

边界仍有合理解释空间：题面并未明确要求修复所有 DynamoDB 区域相关字段。另见 `StreamRecord` 的 `awsRegion` 常量（`base/moto/dynamodb/models/__init__.py:214–237`），但题面没有写入项、读取流记录或相关断言；它是相邻调查点，不能直接当成本题必须满足的独立要求。同理，非 `aws` ARN 分区、任意无效区域、跨区域复制、全面支持 `TableClass` 都没有在题面中形成明确的新功能要求。

## 2. 合理实现范围

可以接受多种保持上述外部行为的实现：在表构造时用已有 `region` 参数统一生成 ARN；保留生成 helper 并把区域显式传入或保存为模型属性；或者使用共享 ARN 构造逻辑。无公开依据要求某个属性必须命名为 `region` / `region_name`、必须保留私有 helper，或必须采用特定改动行数。

接受范围有实质约束：表模型直接实例化的公开 fixture 使用 `Table(..., account_id=..., region=...)`（`base/tests/test_dynamodb/conftest.py:6–20`）；后端创建、两个恢复子类和 CloudFormation 路径都传递区域（`base/moto/dynamodb/models/__init__.py:554–556,1053–1055,1085–1087,1200–1205,1825–1850`）。改变内部接口时必须保持这些公开调用者可工作。把修复仅放在 HTTP 响应层，需要额外保证内部标签匹配、流 ARN、CloudFormation 属性、备份/恢复描述也一致；这条路线不是因为改动位置而不合法，而是容易遗漏已有消费者。

不能接受把所有 ARN 固定为 `us-east-2`、把表名统一替换成示例的 `test_table`、把账户固定为默认值，或通过改变区域路由让非默认客户端实际共用 `us-east-1` 存储来凑出输出。以上均违背题面目的或已有公开接口。无需指定一份唯一修复方案。

## 3. 初态线索与疑义

调查入口完整：`mock_dynamodb` 从公开入口延迟加载该服务（`base/moto/__init__.py:6–15,57`；`base/moto/dynamodb/__init__.py:1–5`）；请求 URL 匹配区域化 DynamoDB endpoint（`base/moto/dynamodb/urls.py:3–5`），基础响应从 URL、User-Agent 或签名读取区域（`base/moto/core/responses.py:287,307–323`）。响应按当前账户/区域选后端，后端把 `region_name` 传给 `Table`，但 ARN helper 忽略区域并写死值（`base/moto/dynamodb/responses.py:140`；`base/moto/dynamodb/models/__init__.py:398–414,452,568–569,1200–1207`）。这是静态可定位链条，尚非已运行的复现结果。

已有公开测试也能帮助辨别问题范围：建表文件的 ARN 断言使用 `us-east-1`（`base/tests/test_dynamodb/test_dynamodb_create_table.py:13,43–45,57,110–112`）；`us-west-2` 的建表/标签测试取返回 ARN 继续使用，没有断言 ARN 的区域（`base/tests/test_dynamodb/test_dynamodb.py:20–35,72–106`）；`us-east-2` 的表达式测试能正常表达建表和读写预期，但不检查 ARN（`base/tests/test_dynamodb/test_dynamodb_condition_expressions.py:10–41`）。因此这些旧测试即使通过，也不足以证明本缺陷已修复。读取调用者与这些测试是正常开发调查，不是题面缺失。

需要保留的疑义及其影响：

- **示例表名笔误：**原样运行第 56 行断言，即使区域已正确，也会因表名不同失败。应明确修正复现预期或统一输入表名，再评估区域；公开代码和旧测试已经足够消解，不构成需要外部资料才能推进的阻碍。
- **SDK 版本：**题面带 `TableClass="STANDARD"`（`user_prompt.txt:51`），但公开依赖只约束 boto3/botocore 的下限（`base/setup.py:29–42`）。静态包不能证明实际安装版本接受该字段。如果 SDK 在发请求前拒绝该参数，先记录为运行兼容问题；不含该可选字段的最小建表仍可调查核心 ARN 问题。当前 handler 在已读建表路径中没有消费 `TableClass`（`base/moto/dynamodb/responses.py:174–252`）；没有依据把完整实现 TableClass 作为此问题修复的前置条件。
- **标题与观察的差别：**题面只提供错误 ARN，没有跨区域列举/读取的观测。现有代码分区存储，因此“资源真实存入另一地区”尚未证实。下方建议复现同时检查另一地区的列表，避免误诊。
- **无必要外部附件：**题面本身无必须访问的外链或附件；开发说明的主要内容在包内。没有发现本次调查必须依赖公开祖先历史的证据；不请求或读取历史镜像。
- **环境证据不足：**是否使用正确解释器、依赖是否齐全、是否选中普通 mock 模式、是否有工作区写权限及足够资源，均需实际 actor 验证。缺证据不等于这些条件已失败，也不据此给题目标记不可用。

### issue、操作指令与环境声明分开记录

`public_bundle.json:1` 的 `problem_statement` 与静态题面一致；`public_hints` 另含 `/testbed`、编辑非测试源码、禁止改测试、窄范围验证及完成后停止工具调用等操作指令，并声明 conda `testbed` 已激活。`allowed_tools` 是 `bash/edit`，不是本次读者已经获准在真实容器运行的证明。

`environment_brief.md:3–12,20–26` 明确说明：静态题面不是捕获到的真实模型消息；hints 是否进入 CLI system message 未验，但 bundle 会写入公开路径，不能因它不在 `user_prompt.txt` 就断言解题者不可读；conda 激活、实际工具和 shell 均待验证。“所有测试修改都会恢复、永不计分”的旧解释不代表当前机制；目前不存在按测试文件名统一排除，仍有官方文件恢复等具体限制。这里不推断哪些具体文件会恢复。

若本次实际求解仍适用“禁止改测试”，本题可以在非测试源码中完成合理修复，使用内联复现和已有公开测试验证；不必改动现有 fixture 的 `region` 调用。若该指令不适用，可以补充区域化回归测试，但这不保证其计分或保留情况。指令适用性及恢复细则属于共享输入/运行条件待核对事项，不是业务目标歧义；本审查没有擅自取消原指令。

## 4. 开发需求表

以下命令均为 **建议，未执行**，默认由实际 actor 在真实 `/testbed` 仓库中运行；不是在本静态 `base/` 上执行。表中环境支持层次来自 `environment_brief.md`，不表示已验证成功。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口及最小建议命令/预期 |
| --- | --- | --- | --- |
| Python 与正确 checkout 的最小导入 | `base/setup.py:29–42,129–143`（Python `>=3.6`）；`base/moto/__init__.py:57`；`base/moto/dynamodb/models/__init__.py:1–42` | hints 声明预激活 conda；说明只描述准备采用的 profile（`environment_brief.md:8–12`） | 实际解释器、版本及来源路径未验。建议，未执行：`python -c 'import sys, boto3, botocore, moto; from moto import mock_dynamodb; from moto.dynamodb.models import Table; print(sys.executable, sys.version); print(moto.__file__, boto3.__version__, botocore.__version__)'`。预期成功导入且 `moto` 来自待修源码；若缺依赖/导入兼容失败，先登记环境问题。 |
| pytest 与旧测试断言库 | `base/requirements-tests.txt:1–6`；`base/tests/test_dynamodb/test_dynamodb_create_table.py:1–8`；`base/tests/helpers.py:1–4` | 未提供已安装清单或测试可执行证明 | 建议，未执行：`python -c 'import pytest, sure; print(pytest.__version__)'`，然后运行下列 T1。预期完成收集与执行；导入失败或收集失败不能直接归为 ARN bug。版本未锁定，实际兼容性须检查。 |
| 原示例的 boto3 输入 schema | `user_prompt.txt:35–52`；`base/setup.py:30–31` | SDK 版本、服务模型资产均未验 | 建议，未执行：`python -c 'from botocore.session import Session; s=Session().get_service_model("dynamodb").operation_model("CreateTable").input_shape; print("TableClass" in s.members)'`。这不发 AWS 请求。若为 False，原示例可能先在 SDK 校验层失败；下方 R1 不依赖该字段。 |
| 最小建表/描述及区域隔离复现 | `user_prompt.txt:25–56`；`base/moto/dynamodb/responses.py:140,240–252,360–363` | 声明 CPU 2 核/4 GiB/PID512 等默认限制，但本题实际资源未验；网络不假定公网（`environment_brief.md:10–12`） | 建议，未执行：R1。只需本地 Python mock，无真实 AWS 服务、真实凭据、GPU 或模型。预计基线返回错误的 `us-east-1` ARN，且目标表不在另一地区的列表，最后 ARN 断言失败；这些是源代码推测，等待 actor 观测。修复后预期断言成立。 |
| 既有行为回归与 ARN 消费者 | 公开建表、标签、恢复、流测试见 T1–T3；`base/docs/docs/contributing/installation.rst:29–36` | 可写工作区/home 属 profile 声明，实际测试依赖及执行未验 | 建议，未执行：T1；有必要时 T2/T3。预期保持旧行为。仅通过这些已有测试不证明非默认区域 ARN 正确，需配合 R1。CloudFormation 可另跑单文件，但其额外依赖较多（`base/setup.py:119–120`）。 |
| 安装/构建/样式条件 | `base/CONTRIBUTING.md:19–28`；`base/Makefile:17–40`；`base/requirements-dev.txt:1–10` | 不假定公网下载；解释器/系统包写权限待核（`environment_brief.md:9–12`） | 项目安装入口为 `make init`（建议，未执行），会执行 develop 安装并装全部开发依赖，不是此小问题的最小前置步骤；缺包时需要可用的预装/离线依赖来源。没有从相关路径发现必须执行原生构建的依据。样式可建议，未执行：`flake8 moto/dynamodb/models/__init__.py` 与 `black --check moto/dynamodb/models/__init__.py`；black 版本应按 `requirements-dev.txt:4` 的 `22.3.0`。 |
| Docker、MotoServer 与 Terraform 子模块 | `base/setup.py:50,108–111`；`base/moto/dynamodb/models/__init__.py:270–289`；`base/docs/docs/contributing/development_tips/tests.rst:27–37,50–75`；`base_identity.json:10–17`；`base/.gitmodules:1–3` | 真实镜像资产及服务未提供；Terraform 子模块明确没有导出内容 | DynamoDB extras 包含 Python `docker` 依赖，不等于最小建表必须运行 Docker daemon。R1/T1 使用普通 mock 模式；无需启动 MotoServer、Lambda 容器或 Terraform。若扩展运行这些专项，再核服务及资产。Terraform 缺子模块不阻碍本题最小验证，无需为此补齐整个仓库。 |

### R1：最小复现（建议，未执行）

该命令统一表名并使用普通 mock 模式；省略与 ARN 根因无关的可选 TableClass、流、SSE 参数，使 SDK 兼容问题与核心问题可分别观测。需要复核题面完整组合时，可在同一 `create_table` 调用恢复 `StreamSpecification={"StreamEnabled": True, "StreamViewType": "NEW_AND_OLD_IMAGES"}`、`SSESpecification={"Enabled": False}`，并在服务模型确认支持后恢复 `TableClass="STANDARD"`；同样属于建议，未执行。

```bash
# 建议，未执行；真实 actor 的工作目录为 /testbed
TEST_SERVER_MODE=false MOTO_ACCOUNT_ID=123456789012 AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_SESSION_TOKEN=testing python - <<'PY_REPRO'
import boto3
from moto import mock_dynamodb

name = "mock_Foundational_AMI_Catalog"
with mock_dynamodb():
    ohio = boto3.client("dynamodb", region_name="us-east-2")
    virginia = boto3.client("dynamodb", region_name="us-east-1")
    created = ohio.create_table(
        TableName=name,
        AttributeDefinitions=[{"AttributeName": "AMI_Id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "AMI_Id", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )["TableDescription"]
    described = ohio.describe_table(TableName=name)["Table"]
    elsewhere = virginia.list_tables()["TableNames"]
    print(created["TableArn"], described["TableArn"], elsewhere)
    assert created["TableArn"] == described["TableArn"]
    assert name not in elsewhere
    assert described["TableArn"] == (
        f"arn:aws:dynamodb:us-east-2:123456789012:table/{name}"
    )
PY_REPRO
```

根据静态代码，基线的最后一个断言预计失败，错误 ARN 的尾部仍应为实际表名。若先遇到导入/SDK/网络或收集错误，应记录真实阻断点，不宣称已复现 ARN 问题。修复后还可用 `us-east-1` 和另一受支持非默认区域重复同类断言，保持账户和表名变量不变；这也是建议，未执行。

### T1–T3：窄范围公开回归（均为建议，未执行）

```bash
# T1：建表参数、默认区域 ARN、流字段、标签和 SSE 的既有约定
# 建议，未执行
TEST_SERVER_MODE=false python -m pytest -q tests/test_dynamodb/test_dynamodb_create_table.py

# T2：标签、备份/恢复、区域 endpoint 的相关既有消费者
# 建议，未执行
TEST_SERVER_MODE=false python -m pytest -q tests/test_dynamodb/test_dynamodb.py -k 'list_table_tags or describe_backup or list_backups or restore_table_from_backup or restore_table_to_point_in_time or describe_endpoints'

# T3：需要核查流 ARN 消费链时，再运行已有流测试文件
# 建议，未执行
TEST_SERVER_MODE=false python -m pytest -q tests/test_dynamodbstreams/test_dynamodbstreams.py
```

T1–T3 预计应保留既有成功行为，但本报告不声称基线或修复版已经通过。T1 的精确表 ARN 断言只覆盖 `us-east-1`；T2/T3 也主要验证身份的一致使用，不能替代 R1 的区域值断言。CloudFormation 兼容性若需额外核验，建议，未执行：`TEST_SERVER_MODE=false python -m pytest -q tests/test_dynamodb/test_dynamodb_cloudformation.py`。不要求运行完整 `make test`；开发文档的 Docker/全仓说明不能转化成本题必需的全部服务清单。

## 5. 阅读范围及暴露范围

完整阅读了角色卡，以及 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`。`user_prompt.txt` 只是静态渲染材料；其与实际模型消息、CLI system message 的关系仅保留环境说明给出的证据层次。

实际打开并按相关区段阅读的公开文件如下；未逐行审查整个仓库：

- 开发材料：`base/README.md`、`base/CONTRIBUTING.md`、`base/docs/docs/contributing/installation.rst`、`base/docs/docs/contributing/development_tips/tests.rst`、`base/docs/docs/services/dynamodb.rst`、`base/Makefile`、`base/setup.py:1–145`、`base/setup.cfg`、`base/requirements.txt`、`base/requirements-tests.txt`、`base/requirements-dev.txt`、`base/.gitmodules`。
- 核心服务：`base/moto/dynamodb/__init__.py`、`base/moto/dynamodb/urls.py`、`base/moto/dynamodb/responses.py:1–374`；`base/moto/dynamodb/models/__init__.py:1–65,214–625,1048–1278,1800–1871`；`base/moto/dynamodbstreams/models.py:1–135`。
- 框架与入口：`base/moto/__init__.py:1–70`；`base/moto/core/__init__.py`；`base/moto/core/base_backend.py:1–55`；`base/moto/core/models.py:1–85,388–403`；`base/moto/core/responses.py:180–220,277–330,337–353`；`base/moto/core/utils.py:416–521`；`base/moto/settings.py:1–24,84–100`。
- 测试与 fixture：`base/tests/__init__.py`、`base/tests/helpers.py`、`base/tests/test_dynamodb/conftest.py`；`base/tests/test_dynamodb/test_dynamodb_create_table.py:1–406`；`base/tests/test_dynamodb/test_dynamodb_table_without_range_key.py:1–75`；`base/tests/test_dynamodb/test_dynamodb.py:1–165,5184–5255,5290–5361,5488–5525`；`base/tests/test_dynamodb/test_dynamodb_cloudformation.py`；`base/tests/test_dynamodb/test_dynamodb_condition_expressions.py:1–47,364–395`；`base/tests/test_dynamodbstreams/test_dynamodbstreams.py:1–155`。

另做了包内文件清单及有限模式检索（`TableArn`、区域传递、表构造、备份/恢复、相关导入等）；部分较大检索输出被截断，后续针对关键区段补读，不将初次搜索当作穷举。检索命中过 `resourcegroupstaggingapi`、EC2 区域定义及其他 DynamoDB 测试等同一 base 文件，但未将这些命中视为已完整审查。曾尝试不存在的 `base/tests/conftest.py` 和 `base/tests/test_dynamodb/test_dynamodb_model.py`；没有读取到内容，随后定位实际 `test_dynamodb/conftest.py`。

未查项包括其余测试/源码的完整内容、真实镜像、预装依赖与 botocore 服务模型数据、运行资产/资源、实际用户身份与权限、shell 激活、实际工具/消息投递、任何祖先/未来 Git 历史，以及缺失 Terraform 子模块的内容。公开包没有 `.git`，也不是完整运行容器（`environment_brief.md:3–6,12–16`；`base_identity.json:10–17`）。没有访问网络、容器、SSH、GPU、模型或用量/重置工具；没有创建子 agent、改动 base 或执行提交。

本角色没有已知私有材料暴露；只在授权 OUTPUT 写入本报告。这里的访问约束是协作约定，不是文件系统权限隔离或预训练无污染证明。关键待确认项是实际运行依赖/SDK、原“禁止改测试”指令的实际适用性，以及 actor 对最小复现和公开回归的真实观测。
