# getmoto__moto-5960：B3 单题公开阅读

本报告是静态公开要求审查，不是修复或运行验收。仅读取协调者指定的角色卡与本题 `PUBLIC_DIR`，只保存本文件。未运行或导入项目、安装或下载依赖、联网、调用 Docker/SSH，未读取其它题、私有材料、历史结论或共享镜像克隆。下列开发、复现和测试命令均为**建议，未执行**。

公开包根目录：`${REPO_ROOT}/runs/swegym_quality_batch03_20260921_v1/public/getmoto__moto-5960`。以下证据路径均相对该目录；`public_bundle.json` 为单行 JSON，字段引用统一记第 1 行。

公开材料已足以定位默认 GSI 扫描的错误及预期。核心需求是按索引配置限制返回属性，同时保留原表数据和现有扫描接口。主要未知不是题面缺少复现，而是实际 actor 环境是否可用，以及未在题面覆盖的组合请求边界。

## 1. 需求表

| 行为 | 需求及应保留的行为 | 依据与确定程度 |
| --- | --- | --- |
| GSI 的 `INCLUDE` 扫描 | `table.scan(IndexName=...)` 返回表键、索引键和 `NonKeyAttributes` 指定的现有属性，排除其它属性。题面例子应得到 `id`、`attr2`，不能返回 `attr1`。 | **明示核心行为**：`user_prompt.txt:3-6,17-60,112-118`。不同表键/索引键也应保留全部键是**公开仓库可合理推知**：`base/moto/dynamodb/models/table.py:39-60`；已有 query 测试 `base/tests/test_dynamodb/test_dynamodb.py:4658-4708`。 |
| GSI 的 `KEYS_ONLY` 扫描 | 仅返回表主键与索引键。题面复合键例子为 `id`、`seq`，不能返回 `attr1`。 | **明示核心行为**：`user_prompt.txt:63-109,112-118`；键集合的通用含义见 `base/moto/dynamodb/models/table.py:48-53`、`base/tests/test_dynamodb/test_dynamodb.py:4609-4653`。不能只保留 GSI 自己的键而漏掉不同的表键。 |
| 适用所有返回项 | 规则应应用于本次扫描返回的每条记录，不应硬编码题面的表名、索引名、字段名或只处理第一项。无需新增 API 或让调用者额外传 `ProjectionExpression`。 | **明示并合理推广**：`user_prompt.txt:6,53-60,101-114`。例子只断言首项，但描述明确指扫描所得 items；`IndexName` 已通过公开接口传入（`base/moto/dynamodb/responses.py:769-789`）。 |
| `ALL` 与无索引扫描 | `ProjectionType=ALL` 不因本修复额外删除属性；无 `IndexName` 的表扫描不应套用任意索引投影。 | **公开仓库可合理推知的兼容要求**：`base/moto/dynamodb/models/table.py:59,814-818`；公开 GSI/LSI `ALL` 扫描测试见 `base/tests/test_dynamodb/test_dynamodb_table_with_range_key.py:1050-1148`、`base/tests/test_dynamodb/test_dynamodb_table_without_range_key.py:528-577`。这些扫描测试直接检查数量和分页键，未直接检查 `ALL` 的完整属性集合。 |
| 原始数据与后续操作 | 扫描返回属性的裁剪不能删除存储中的原属性；后续表 scan/query/get 应仍能取得原记录。 | **已有代码和公开测试明确约定**：`base/moto/dynamodb/models/dynamo_type.py:395-411` 提醒先深拷贝；`base/tests/test_dynamodb/test_dynamodb.py:529-533,762-775` 验证投影后仍保留原数据。GSI 投影同样裁剪 `Item`，故此约束可合理推广。 |
| 既有扫描筛选与分页 | 保留索引成员资格筛选、`Limit`、`ExclusiveStartKey`、响应 `Count`/`Items`/`ScannedCount`/`LastEvaluatedKey`、非法索引错误。不能因字段裁剪丢失分页所需键。 | **现有接口/公开测试约定**：`base/moto/dynamodb/models/table.py:779-858,860-905`；`base/moto/dynamodb/responses.py:793-800`；`base/tests/test_dynamodb/test_dynamodb.py:2390-2420,5635-5690`；无 range key 测试 `:505-524,564-577`，有 range key 测试 `:1122-1148`。 |
| 调用者的 `ProjectionExpression` | 保留已有进一步选择字段、嵌套字段和别名的能力；索引默认投影不能让显式字段选择失效。对索引已投影属性再取子集，与现有 query 路径一致。 | **公开仓库可合理推知**：`base/moto/dynamodb/models/table.py:749-764`；`base/moto/dynamodb/responses.py:729-775`；公开 scan 测试 `base/tests/test_dynamodb/test_dynamodb.py:470-533,717-775,994-1051`。题面本身未覆盖 GSI 与显式字段选择的组合。 |
| query 及 LSI | 现有 GSI query 的 `KEYS_ONLY`/`INCLUDE`、LSI query 的 `KEYS_ONLY` 应继续工作。是否同时扩展 LSI scan 的投影，不是 issue 明示的新目标。 | query 行为有直接公开测试（`base/tests/test_dynamodb/test_dynamodb.py:4609-4756`）。LSI/GSI 共用 `SecondaryIndex.project`（`base/moto/dynamodb/models/table.py:25-91`），因此统一处理 scan 是合理方向；仅凭题面不能把 LSI 扩展设为唯一合法实现。 |

题面的 Python 3.10、Ubuntu 20.04、boto3 1.26.74、botocore 1.29.74、Moto 4.1.3 是报告者当时环境（`user_prompt.txt:143-150`），不是要求解题者升级/降级到这些版本，也不是当前运行环境证明。

## 2. 合理实现范围

合理方案可以在模型的扫描路径使用已有索引投影能力，也可以构造独立的投影结果对象或在保持模型/响应契约的其它内部层实现相同效果。接受标准应是公开可观察行为：正确的属性集合及值、不破坏原数据、保持兼容的筛选和分页行为。无需指定私有辅助函数名称、变量名称、重构方式或必须调用某一函数；这里未编写修复。

`SecondaryIndex.project` 已有明确的 `KEYS_ONLY`、`INCLUDE`、`ALL` 语义（`base/moto/dynamodb/models/table.py:39-60`），是公开可见的复用线索，不是必须照抄的实现模板。现有 `Item.filter` 会就地删除字段（`base/moto/dynamodb/models/dynamo_type.py:395-411`）；因此复用时的独立结果/复制语义是必要行为约束，但不应强制唯一复制位置或技术。

确有约定的名称是 AWS 风格的公开字段，如 `IndexName`、`ProjectionType`、`NonKeyAttributes`、`Items`、`LastEvaluatedKey`。题面使用 `sorted(items[0].keys())` 比较属性集合（`user_prompt.txt:60,109`），没有要求字典键序；也没有要求新增日志、固定终端输出或新的异常文字。既有非法索引异常的 code、HTTP 状态、message 则被公开测试明确检查（`base/tests/test_dynamodb/test_dynamodb.py:2414-2420`）。

以下边界未由题面唯一规定，不应悄然混入核心验收标准：

- LSI scan 的同步改进范围。共享代码支持统一实现，但 issue 指向 GSI；现有 LSI query 与 LSI `ALL` scan 仍是兼容约束。
- 当 GSI 请求的 `ProjectionExpression`、`FilterExpression` 或旧 `ScanFilter` 引用未投影属性时，是拒绝、忽略还是以某种顺序过滤。现有 query 在索引投影后求 `FilterExpression`（`base/moto/dynamodb/models/table.py:749-764`），scan 目前在完整项上过滤（`:820-856`）；这是需要确认的组合语义，不能从两个默认扫描例子推出全部错误规则。
- 索引投影与 1 MB 分页尺寸计算的先后。`_trim_results` 使用 `Item.size()`（`base/moto/dynamodb/models/table.py:884-903`；`base/moto/dynamodb/models/dynamo_type.py:296-297`），query 提供一种顺序参考，但已读的公开测试没有覆盖 `INCLUDE`/`KEYS_ONLY` 的尺寸边界。不同裁剪位置可能在该边界产生差异，不能仅凭两例都过就断言这些实现完全等价。
- 题面未提出 `Select` 模式、容量精度、全部 DynamoDB 参数校验或其它 API 修订；已读的 scan 响应入口也未处理 `Select`（`base/moto/dynamodb/responses.py:754-800`）。这些不应被无依据地扩大成当前 issue 的强制目标。

若开发范围必须处理上述组合行为，可请求补充与当时接口对应、且不含未来修复的公开 API 文档片段；当前核心修复不依赖补充材料。本次未访问外链或猜测标准补丁。

## 3. 初态线索与疑义

**调查入口充分。** 题面提供完整建表、写入、扫描和断言，两例均在 `@mock_dynamodb` 下执行，且附错误属性集合（`user_prompt.txt:12-141`）。公开路径可以直接追踪：响应 `scan` 读取 `IndexName` → `DynamoDBBackend.scan` 传给 `Table.scan`（`base/moto/dynamodb/responses.py:754-800`；`base/moto/dynamodb/models/__init__.py:343-373`）→ 表的扫描函数依据索引键选择记录，但未调用已有索引投影能力（`base/moto/dynamodb/models/table.py:802-858`）。相邻 query 已在结果副本上执行索引投影（`:749-753`）。这是静态代码对题面错误的支持，不是已实测复现。

读取调用链即可明确 `Item.filter` 的修改语义、键集合和响应格式。这些是正常开发调查，不是题面缺陷。无需额外 issue 截图、外部数据集或真实 DynamoDB 账户即可表达核心复现。README/贡献文档有外链，但已给出的安装配置、公开测试和源码足够建立最小计划；未发现核心需求依赖包外附件。

**共享输入与运行条件应分开记录：**

| 类别 | 公开陈述 | 审查结论 |
| --- | --- | --- |
| issue 需求 | 修复 GSI scan 忽略 `INCLUDE`/`KEYS_ONLY`；给出两个 pytest 例子。 | 需求和失败现象明确，见上表。 |
| harness 操作指令 | `public_bundle.json:1` 的 `public_hints` 要求修改非测试源码、不改测试、仅做窄测试，完成后简短总结。`allowed_tools` 为 `bash`/`edit`，工作目录声明为 `/testbed`。 | 这些与 issue 目标不同；本静态审查不执行它们，也不擅自取消其对实际解题者的约束。源码层面的合理解不需要改测试；若原禁令生效，可以用终端内存脚本复现，并运行已有公开测试。若不生效，可增加回归测试，但这不是合法修复的先决条件。 |
| 旧机制解释 | `public_hints` 解释为“所有测试都会恢复、测试修改永不计分”。 | `environment_brief.md:18-26` 明确提醒该解释不能代表当前机制；目前不按测试文件名统一排除，仍有具体官方文件恢复限制。实际哪些文件受影响未在公开包核实，不把旧解释当现行事实，也不据此判题不可用。 |
| 环境事实声明 | `public_hints` 声称 conda `testbed` 已激活，`python`/`pip`/测试工具已指向它。 | 待 actor 身份核验；不能由包字段或镜像摘要推定导入/测试已成功。 |
| 消息和可见性 | `user_prompt.txt` 是静态渲染；是否把 hints 注入 CLI system message 尚未核验。 | 见 `environment_brief.md:3-6,25-26`。bundle 会写入真实解题容器的公开路径，未出现在渲染文本中不等于不可见。未验实际模型消息、shell 或工具。 |

真实阻碍开发的情况将是 actor 无法导入目标 checkout、缺少兼容依赖且无可用离线供给、或未进入所需工作区；本包没有证明这些问题发生。组合语义未知和未提供祖先历史目前不阻断默认扫描修复。`base_identity.json:10-17` 仅缺 Terraform provider 子模块内容（`base/.gitmodules:1-3`）；最小 DynamoDB mock 测试没有引用它，不需为本核心工作补齐该资产。

## 4. 开发需求表

以下仅给实际 actor 后续使用的建议；本次没有执行任何导入、项目测试或构建。命令中的 `/testbed` 是公开包声明的真实工作区，不是本地 `base/` 导出的别名。

| 操作／资产／服务 | 公开依据 | 环境说明支持层次 | 缺口 | 最小建议与预期 |
| --- | --- | --- | --- | --- |
| 解释器、源码与基本依赖 | `base/setup.cfg:26-38` 声明 Python ≥3.7、boto3/botocore/requests/responses 等；题面用 `mock_dynamodb`；`base/moto/__init__.py:6-15` 是懒加载，仅导入顶层 moto 不足以检查 DynamoDB 依赖。 | hints 声称 conda 已激活；brief `:8-12` 只陈述计划的 profile 和待验条件。 | 实际 Python 路径、版本、依赖兼容性、导入的 moto 是否来自目标源码未知。 | **建议，未执行：C1**。预期正确目标源码路径，且相关导入成功；导入失败属于环境/依赖调查，不能当成本 issue 的属性断言失败。 |
| 本地 DynamoDB mock | `base/moto/dynamodb/__init__.py:1-5` 接到 mock 装饰器；`base/moto/core/models.py:398-413` 按 `TEST_SERVER_MODE` 选择本地/服务器模式；`base/moto/settings.py:9` 默认关闭服务器模式；mock 有假凭据 `base/moto/core/models.py:57-60,190-196`。 | brief 不保证真实服务可用，公网也不可假定可达（`:10-12`）。 | 实际环境变量及 mock 初始化未验。 | **建议，未执行：C2**，显式本地 mock 模式。静态推断此最小路径不需真实 AWS、DynamoDB Local、Docker daemon 或网络服务。`setup.cfg:121` 的 `docker` 是 Python 依赖声明，不能据此推出必须运行 Docker daemon。 |
| 核心复现数据 | 题面两种表定义及 A/B/C 记录均自包含（`user_prompt.txt:17-109`）。 | 工作区/home 可写只是 profile 描述；无需把本地导出当运行容器。 | 尚未验证实际创建/写入/扫描是否到达断言。 | **建议，未执行：C2**。原 bug 预期 `INCLUDE` 多出 `attr1`，`KEYS_ONLY` 多出 `attr1`；修复后所有项符合预期集合，分别 3/6 项。 |
| 窄公开回归 | DynamoDB 测试使用 pytest、sure；`base/requirements-tests.txt:1-7` 列 pytest 和 `surer`，`base/tests/helpers.py:4` 实际导入 `sure`；相关测试见 C3。 | brief `:12-16` 要求实际 actor CPU 验证且无需全仓测试。 | pytest/断言库是否可用、是否有收集错误与插件差异未知。 | **建议，未执行：C3a–C3c**，逐个文件运行。预期保留 query 投影、表扫描字段选择及存储不变、非法索引、索引成员与分页键。已有 query 投影测试通过不能单独证明本 issue 已修好。 |
| 构建／依赖供给 | `base/CONTRIBUTING.md:19-22` 的 `make init`/`make test` 是全仓开发指引；`base/Makefile:17-19,21-44` 涉安装、广泛 lint/test；`base/requirements-dev.txt:1-14` 为全套开发依赖；`base/pyproject.toml:1-3` 使用 setuptools。 | 不假定公网或解释器系统目录可写（brief `:9-12`）。 | 若现有环境缺包，需要已批准离线依赖或环境修复；未检查其存在。 | 核心改动为 Python 源码行为，不需要额外 native 编译或全仓 wheel 构建才可做 C2/C3。**建议，未执行：C4** 可选语法检查，不能替代行为验证。不建议以 `make init`/全仓 `make test` 作为最小前置。 |
| CPU／内存／附加资产 | 自包含小表 mock 用例；Terraform 集成另有专用目标（`base/Makefile:46-50`）。 | brief `:11` 声明默认 2 CPU/4 GiB/PID512、tmp 1 GiB/home 256 MiB，但本题未实测。 | 实际耗时、内存、磁盘、写权限和 pytest 缓存条件未知。 | 无公开证据要求 GPU、大文件、外部数据库或 Terraform 子模块。C2/C3 应在声明 CPU 条件下实际记录结果；本报告不声称资源已足够或测试已通过。 |

### C1：最小导入与来源检查（建议，未执行）

```bash
PYTHONPATH=/testbed TEST_SERVER_MODE=false python -c 'import sys, boto3, botocore, pytest, sure; import moto; import moto.dynamodb; from moto import mock_dynamodb; print(sys.executable); print(sys.version); print(moto.__file__); print(boto3.__version__, botocore.__version__)'
```

该检查同时包含公开测试的断言库依赖；核心题面复现本身不需要 `sure`。若 C1 仅在 `sure` 导入失败，不能推定 boto3/moto 的最小复现也必然失败，需分别核对。预期 `moto.__file__` 指向 `/testbed/moto/`，不是其它已安装版本。

### C2：题面核心路径的内存复现（建议，未执行）

下例概括题面的两种建表/写入/扫描配置并检查所有返回项，不创建或修改测试文件。它是建议复现脚本，不是已运行结果，也不代替公开 pytest 回归。

```bash
PYTHONPATH=/testbed TEST_SERVER_MODE=false python - <<'PY'
import boto3
from moto import mock_dynamodb

@mock_dynamodb
def check_projection(mode):
    schema = [{"AttributeName": "id", "KeyType": "HASH"}]
    definitions = [{"AttributeName": "id", "AttributeType": "S"}]
    projection = {"ProjectionType": mode}
    if mode == "INCLUDE":
        projection["NonKeyAttributes"] = ["attr2"]
    else:
        schema.append({"AttributeName": "seq", "KeyType": "RANGE"})
        definitions.append({"AttributeName": "seq", "AttributeType": "N"})
    throughput = {"ReadCapacityUnits": 10, "WriteCapacityUnits": 10}
    db = boto3.resource("dynamodb", region_name="us-east-1")
    table = db.create_table(
        TableName="public-projection-repro",
        AttributeDefinitions=definitions,
        KeySchema=schema,
        GlobalSecondaryIndexes=[{
            "IndexName": "public-gsi",
            "KeySchema": schema,
            "Projection": projection,
            "ProvisionedThroughput": throughput,
        }],
        BillingMode="PROVISIONED",
        ProvisionedThroughput=throughput,
    )
    for identifier in ("A", "B", "C"):
        if mode == "INCLUDE":
            table.put_item(Item={"id": identifier,
                                 "attr1": "attr1_" + identifier,
                                 "attr2": "attr2_" + identifier})
        else:
            for seq in (0, 1):
                table.put_item(Item={"id": identifier, "seq": seq,
                                     "attr1": "attr1_" + identifier + str(seq)})
    items = table.scan(IndexName="public-gsi")["Items"]
    expected = {"id", "attr2"} if mode == "INCLUDE" else {"id", "seq"}
    expected_count = 3 if mode == "INCLUDE" else 6
    observed = [sorted(item) for item in items]
    print(mode, observed)
    return len(items) == expected_count and all(set(item) == expected for item in items)

results = [check_projection(mode) for mode in ("INCLUDE", "KEYS_ONLY")]
assert all(results), "GSI scan returned attributes outside the configured projection"
PY
```

原始代码的静态预期是先打印 `INCLUDE` 的 `['attr1', 'attr2', 'id']`、`KEYS_ONLY` 的 `['attr1', 'id', 'seq']`，最后断言失败；修复后分别只有 `['attr2', 'id']`、`['id', 'seq']`。若出现导入、服务连接或建表失败，应先登记环境或其它前置问题，不能说已观察到目标 bug。

### C3：已有公开测试（建议，未执行）

C3a：已有投影、原数据不变、非法索引、筛选与分页顺序；单文件窄选择。

```bash
PYTHONPATH=/testbed TEST_SERVER_MODE=false python -m pytest -q /testbed/tests/test_dynamodb/test_dynamodb.py -k 'gsi_projection_type or lsi_projection_type or (projection and scan) or projection_expression_execution_order or scan_by_non_exists_index or scan_filter'
```

C3b：复合主键下的 GSI/LSI 成员筛选和分页键。

```bash
PYTHONPATH=/testbed TEST_SERVER_MODE=false python -m pytest -q /testbed/tests/test_dynamodb/test_dynamodb_table_with_range_key.py::test_scan_by_index
```

C3c：单主键下的索引扫描及无索引分页。

```bash
PYTHONPATH=/testbed TEST_SERVER_MODE=false python -m pytest -q /testbed/tests/test_dynamodb/test_dynamodb_table_without_range_key.py -k 'test_scan_by_index or test_scan_pagination'
```

预期这些旧行为保持通过，但未执行，不能把该预期写为已通过。题面中的新断言并不是上面已有 query 投影测试的同义替代，因此需要 C2 或在测试编辑确获允许时的对应新增回归。

### C4：可选源码语法检查（建议，未执行）

```bash
python -m py_compile /testbed/moto/dynamodb/models/table.py
```

成功仅说明该文件可编译；会需要相应缓存写入条件，不验证索引投影正确性。实际修复若涉及其它源码文件，应仅按实际改动调整检查范围。

## 5. 阅读范围与限制

正文读取（完整文件或指定区间，不表示全文件逐行审查）：

- 给定角色卡 `roles/public_reader.md`；本题 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`。
- `base/moto/dynamodb/models/table.py`：1–130、183–244、634–924；`base/moto/dynamodb/models/__init__.py`：1–70、343–380；`base/moto/dynamodb/models/dynamo_type.py`：295–328、383–420；`base/moto/dynamodb/responses.py`：729–815；`base/moto/dynamodb/__init__.py`。
- `base/tests/test_dynamodb/test_dynamodb.py`：1–55、469–536、717–779、994–1054、1428–1468、2388–2426、4598–4768、5632–5695；`base/tests/test_dynamodb/test_dynamodb_table_with_range_key.py`：1–38、1048–1155；`base/tests/test_dynamodb/test_dynamodb_table_without_range_key.py`：1–20、503–595；`base/tests/test_dynamodb/conftest.py`；`base/tests/__init__.py`；`base/tests/helpers.py`：1–52。
- `base/README.md`、`base/CONTRIBUTING.md`、`base/requirements-tests.txt`、`base/requirements-dev.txt`、`base/pyproject.toml`、`base/.gitmodules`；`base/Makefile`：1–54；`base/setup.cfg`：24–70、118–128、205–240。
- 为核对 mock 入口和服务要求读取 `base/moto/__init__.py`：1–25、62–79，并检索 `mock_dynamodb` 定义；`base/moto/settings.py`：1–39；`base/moto/core/models.py`：32–68、185–204、300–345、388–419（另请求 730–770 未返回正文）。

检索另外覆盖了 `base/tests/test_dynamodb/` 下的 scan/projection 相关匹配行、上述模型/响应源码的相关符号，以及安装文档/config/requirements 的关键词；`base/requirements.txt` 仅见搜索命中。两次较宽检索结果发生输出截断，随后读取关键文件的定向区间，本报告不对未显示部分作完整审查声明。文件名枚举限于本题 `PUBLIC_DIR`，没有扩展到其它题。其余测试、完整依赖导入闭包、服务端测试、Terraform 子模块、全仓测试和构建均未查验运行。

`base/` 只是声明 base commit `d1e3f50756fdaaea498e8e47d5dcd56686e6ecdf` 的导出；`base_identity.json:3-4,17-23` 给出身份/导出校验声明，但不是本次容器运行或独立 Git 身份复核。`environment_brief.md:3-6` 明确未提供完整容器、预装包、环境提交、构建产物或公开祖先历史。本报告未声称实际模型消息、运行资源、开发条件或测试结果已经验证。

本任务未接触私有材料或历史结论；阅读范围由协作约定约束，不是文件权限隔离或预训练无污染证明。保留的关键未知是：actor 的解释器/依赖/本地 mock 模式是否可用；旧测试编辑禁令及具体文件恢复限制在本次求解的适用情况；超出默认扫描例子的组合请求和尺寸边界语义。无需给本题作“通过/淘汰”标签。
