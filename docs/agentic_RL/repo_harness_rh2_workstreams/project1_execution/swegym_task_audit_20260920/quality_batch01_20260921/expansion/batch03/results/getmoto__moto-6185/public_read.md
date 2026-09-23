# B3 单题公开要求审查：getmoto__moto-6185

本审查仅使用公开角色卡和指定 PUBLIC_DIR。以下路径均相对 PUBLIC_DIR；`base/` 是导出的基线仓库。未读私有评分材料、未来代码、历史结论、其他题或共享镜像，未联网，未运行或导入项目，未安装依赖、调用 Docker/SSH 或查询配额。本文中的开发命令全部是**建议，未执行**。静态阅读只能说明公开要求和调查入口，不能证明实际开发环境或测试结果。

## 1. 需求表

| 行为或约束 | 依据 | 确定程度与边界 |
| --- | --- | --- |
| `Table.put_item(Item=...)` 应接受普通属性名 `S`，包括顶层 `{'index': 0, 'S': None}` 和嵌套 `{'index': 0, 'A': {'S': None}}`，不应因此抛出 `SerializationException`。 | `user_prompt.txt:3-10,19-37`。 | **明示**。要求修复该行为；无需调用者重命名字段或改变 payload。 |
| 多层合法 map 中名为 `S` 的属性同样应正常保存；保存后字段名、值和嵌套结构应能读回。 | 题面“deeply nested”，`user_prompt.txt:10`；已有嵌套写入和完整读回测试 `base/tests/test_dynamodb/test_dynamodb.py:538-589`。 | 多层 map 是**明示**范围，读回一致性是**合理推知**，不能仅吞掉异常或丢弃字段。题面只给出 `None` 示例，但没有把修复限定为该值。 |
| 原来合法的 `s`、`A` 等属性，以及普通字符串、map、list、`None` 的行为应保留。 | `user_prompt.txt:10,32-35`；`base/moto/dynamodb/models/dynamo_type.py:18-27,54-64`；`base/tests/test_dynamodb/test_dynamodb.py:3307-3347`。 | **明示对照 + 合理推知**。`None` 是已被公开测试使用的合法非主键属性值，不是需要禁止的输入。 |
| 真正的 DynamoDB AttributeValue 类型标记 `S` 仍要求字符串；关闭 botocore 参数校验后，`{'pk': {'S': 123}}`、`{'pk': {'S': {'S': 'asdf'}}}` 仍应得到原有错误。 | `base/tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py:917-940`；`base/moto/dynamodb/models/table.py:493-503`。 | **公开测试明确约定**：错误码均为 `SerializationException`；整数值消息为 `NUMBER_VALUE cannot be converted to String`，字典值消息为 `Start of structure or map found where not expected`。属性名 `S` 与类型标记 `S` 必须区分。 |
| 真正的 `N` 类型值用整数而不是数字字符串时，顶层主键和嵌套非主键的旧错误应保留。 | `base/tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py:623-650`；`base/moto/dynamodb/models/table.py:491-492`；`base/moto/dynamodb/exceptions.py:329-332`。 | **公开测试明确约定**：`SerializationException` 和上述 `NUMBER_VALUE` 消息。不能通过取消所有递归校验来解决本题。 |
| 普通 PutItem 返回值、主键校验、条件写入、存储行为应保留。 | `base/moto/dynamodb/responses.py:417-470`；`base/moto/dynamodb/models/table.py:514-575`；`base/tests/test_dynamodb/test_dynamodb.py:2221-2256`。 | **现有接口和公开测试可合理推知**。`ReturnValues` 默认 `NONE`，`ALL_OLD` 返回旧值，非法 `ALL_NEW` 报错；题目不要求改变这些约定。 |
| list 中包含 map，且 map 有 `S` 属性时，也不应新增失败；批量或事务 Put 的共享路径不应退化。 | `base/moto/dynamodb/models/dynamo_type.py:61-64`；`base/moto/dynamodb/responses.py:472-494`；`base/moto/dynamodb/models/__init__.py:567-596`。 | **合理兼容性推知**，题面没有逐项枚举这些入口。基线检查只递归 dict，不能据题面“anywhere”就断言 list 内已经复现同一错误。是否扩展 list 内畸形类型的校验及其错误顺序，公开材料没有完整规定。 |

Issue 的需求是修复合法属性名造成的错误，并解释为何大写 `S` 特殊；用户对“编码”的猜测不是实现约束。`public_bundle.json:1` 中的 `public_hints` 则是 harness 操作指令（改非测试源码、不改测试、窄范围验证、完成后简述）和环境声明（`testbed` conda 已激活），两者不应混同为 issue 的功能验收条件。

## 2. 合理实现范围

公开可观察目标是：正确区分“属性名称到 AttributeValue 的映射”与“AttributeValue 内的类型标签”，允许合法名称 `S`，同时保留已经明确的无效类型诊断。这并不唯一指定递归函数的签名、辅助函数名、遍历顺序或所在文件。保持语义等价的递归上下文识别、分别遍历属性映射和类型值、或复用/调整类型表示的内部实现，均有合理空间；这里仅列实现自由度，不提供修复补丁。

`_validate_item_types` 是现有私有方法名（`base/moto/dynamodb/models/table.py:487`），不是题面要求的新增公共 API。公开材料没有要求增加配置开关、迁移存储格式、修改 boto3、限制用户字段名，或仅让 `None` 特判通过。也没有要求解决所有 DynamoDB 类型校验的不一致、改变其他服务，或复刻尚未给出的 AWS 边界错误顺序。

不可接受的行为包括：要求用户把 `S` 改名、删除该字段后声称写入成功、把所有类型校验关闭、将合法字符串类型标记一起跳过。前两项违反明示示例和保存语义，后两项与上述公开负面测试冲突。合法字段名与类型标签的差别，已经足以让开发者判断修复方向，无需知道标准答案的内部写法。

## 3. 初态线索与疑义

### 可直接定位的入口

静态调用链为请求中的 `Item` → `DynamoHandler.put_item`（`base/moto/dynamodb/responses.py:417-419,455-463`）→ backend `put_item`（`base/moto/dynamodb/models/__init__.py:218-236`）→ `Table.put_item` 中的 `_validate_item_types`（`base/moto/dynamodb/models/table.py:543`）。

该检查遍历每个 `key, value`，对所有字典值继续递归，随后只要 `key == 'S'` 且值为字典就抛出题面原文错误（`base/moto/dynamodb/models/table.py:487-503`）。因此，普通属性映射中的 `S` 会被当作字符串类型标记。公开类型表示同时明确了 `S/N/M/L/NULL` 标签和 map/list 的嵌套处理（`base/moto/dynamodb/models/dynamo_type.py:18-27,54-64,270-282`）。这些材料可形成很强的静态解释；**没有实际复现或捕获 boto3 序列化请求**。

公开测试还提供了关闭 SDK 参数校验的入口（`parameter_validation=False`），因此保留错误行为也可从公开材料调查，不必请求隐藏验收。正常阅读调用者、序列化层或依赖版本不属于题面缺陷。

### 真正需要保留的未知

1. **实际环境尚未证实。** `user_prompt.txt:45-49` 是报告者的 Ubuntu/Python/boto3/botocore/moto 版本；`base/setup.cfg:3,27-38` 则给出基线包版本声明和较宽依赖范围。不能把报告者环境或 bundle 的 conda 声明当成当前 actor 版本。实际导入来源、依赖组合、权限和测试可执行性须核实。
2. **示例缺默认区域说明。** `user_prompt.txt:26` 未指定 `region_name`；现有相关测试通常显式指定区域，如 `base/tests/test_dynamodb/test_dynamodb.py:540`。没有默认 AWS 区域时可能先遇到区域配置错误，这不是 `S` 修复失败。建议复现显式设 `us-east-1` 并使用虚拟凭证。注释中的 `A` 对照还漏了一个引号（`user_prompt.txt:33`）；它没有执行，不影响实际 `S` 示例。
3. **list 内路径和全部畸形输入的范围不完整。** dict 内任意深度的合法 `S` 明确；list 内 map 的兼容性可推知，但基线不会递归进入 list。没有公开依据要求在本题中新增全部无效 list 元素的错误规则或指定多重错误优先级。
4. **旧 harness 提示适用性待核对。** `environment_brief.md:20-26` 明确说明“conda 已激活”未验证；原“禁止改测试”不能擅自取消，而其“所有测试修改都会恢复、永不计分”的解释不能代表当前机制。若禁改测试指令适用，可修改非测试实现、运行已有测试和独立 stdin 复现；本题合理源码修复并不因此受阻。若不适用，补充回归测试也是合理开发活动，但哪些官方文件会恢复仍是共享输入/运行条件问题。本文未验证实际消息注入、文件恢复清单或评分机制。

没有发现推进这项静态调查必须补充的外链、附件或祖先历史。源码中的 AWS 文档链接不是当前定位问题和保留已测行为的必需输入；若以后要裁决新增畸形类型行为，才可能需要相应公开规范。包内未导出的 Terraform 子模块位于 `tests/terraformtests/terraform-provider-aws`（`base_identity.json:10-17`、`base/.gitmodules:1-3`），当前所选 DynamoDB Python 单测不引用它；不据此认定开发受阻。

## 4. 开发需求表

| 操作 / 资产 / 服务 | 公开依据 | 环境说明支持到哪层 | 缺口与最小建议 |
| --- | --- | --- | --- |
| 导入正确的基线 Python 源码和依赖 | `base/setup.cfg:27-38,124-125`；`base/pyproject.toml:1-3`；`public_bundle.json:1` 的 commit/workdir。 | `environment_brief.md:5-12` 仅提供源码导出和计划环境；conda 声明不是运行证据。 | 执行建议 C1 核对解释器、moto 导入路径及 boto3/botocore 版本。缺依赖时需环境准备阶段补齐；本审查没有安装或下载。 |
| 进程内模拟 DynamoDB 并复现 `S` 属性写入 | `user_prompt.txt:24-39`；`base/moto/dynamodb/__init__.py:1-5`。 | bash/edit、工作目录 `/testbed`、默认资源和 actor 描述均是说明，非本题实测。 | 建议 C2 指定 region、虚拟凭证和普通 decorator 模式。预期仅使用本地内存 mock；无需真实 AWS 账号、云表、远程数据库或下载资产。实际 mock 启动仍待验证。 |
| 运行旧错误诊断和合法 map / `None` 的公开测试 | `base/requirements-tests.txt:1-8`；`base/tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py:1-8,623-650,917-940`；`base/tests/test_dynamodb/conftest.py:1-20`；`base/tests/__init__.py:1-8`、`base/tests/helpers.py:1-4`。 | 未证明 pytest、`sure` 模块及测试导入依赖可用。requirements 文件写 `surer`，测试实际导入 `sure`，需检查该模块是否可导入。 | 建议 C1 检查导入、C3 运行两项负面测试、C4 运行合法值/返回值用例。不运行全仓或 xdist 并发，不以未查其他服务依赖阻断本题。 |
| 选择普通测试模式 | `base/moto/settings.py:9`；两个负面测试在 ServerMode 主动 skip，见 `base/tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py:625-626,919-920`；`base/docs/docs/contributing/development_tips/tests.rst:27-37`。 | 未验证实际 shell 的 `TEST_SERVER_MODE`。 | C1–C4 显式 `TEST_SERVER_MODE=false`；应看到执行通过，而不能把 skip 当校验成功。此最小路径无须启动 MotoServer。 |
| 开发安装、构建和系统依赖 | README 安装命令在 `base/README.md:14-18`；开发说明 `base/CONTRIBUTING.md:17-22`；`base/docs/docs/contributing/installation.rst:9-13,24-46`；`base/Makefile:17-19,36-44`。 | 网络不保证可下载，解释器/系统包权限待验（`environment_brief.md:9-12`）。 | 这是 Python 源码逻辑问题，最小复现和已装环境中的单测不需要额外打包构建。`make init` 会安装广泛依赖，`make test` 含全仓 lint/测试，均不是本题最小前提。DynamoDB extra 声明 Docker **Python 包**不证明本次 PutItem 单测需要 Docker daemon；未提出 Docker 启动或下载建议。 |
| 工作区写入和测试限制 | `public_bundle.json:1` 的 `public_hints`；`environment_brief.md:9,20-26`。 | 仅声明 actor 可写工作区/home；未实测权限或具体官方恢复规则。 | actor 阶段核对实际指令和源码写权限；本审查只写本报告，不修改 base。原禁改测试适用时，C2 不改测试文件，C3/C4 只运行已有公开测试。 |

下列路径指向**未来真实 actor 环境的 `/testbed`**，不是让静态公开导出包承担容器身份。所有命令均为**建议，未执行**；它们没有在本轮被运行。

**C1：最小导入与身份核对——建议，未执行。** 预期导入成功、打印实际解释器和版本，`moto.__file__` 指向 `/testbed` 源码。若失败，则先报告具体缺包/导入错误；不把它当成功复现原 bug。

```bash
env TEST_SERVER_MODE=false PYTHONPATH=/testbed python -c 'import sys, boto3, botocore, moto, pytest, sure; from moto import mock_dynamodb; from moto.dynamodb.models import Table; print(sys.executable); print(moto.__file__); print(boto3.__version__, botocore.__version__, moto.__version__)'
```

**C2：有效输入的最小复现及读回——建议，未执行。** 保留题面数字主键/预置吞吐量；增加显式区域、控制项和独立案例记录。根据静态源码，原基线预计顶层和纯 map 深层 `S` 用例报题面错误，`s`/`A` 对照成功；list 内 map 是否成功须实测，不声称它是已复现失败。修复后各有效输入均应写入并等值读回，最终断言通过。

```bash
env TEST_SERVER_MODE=false AWS_DEFAULT_REGION=us-east-1 AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_EC2_METADATA_DISABLED=true PYTHONPATH=/testbed python - <<'PY'
import boto3
import moto
from botocore.exceptions import ClientError

cases = [
    ('control_lower_s', {'s': None}),
    ('control_A', {'A': None}),
    ('top_S', {'S': None}),
    ('nested_S', {'A': {'S': None}}),
    ('deep_S', {'A': {'B': {'S': 'text'}}}),
    ('list_map_S', {'A': [{'S': None}]}),
]
failed = []
with moto.mock_dynamodb():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='test',
        KeySchema=[{'AttributeName': 'index', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'index', 'AttributeType': 'N'}],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
    )
    for index, (name, extra) in enumerate(cases):
        item = {'index': index, **extra}
        try:
            table.put_item(Item=item)
            assert table.get_item(Key={'index': index})['Item'] == item
            print(name, 'OK')
        except ClientError as error:
            failed.append(name)
            print(name, error.response['Error'])
assert not failed, failed
PY
```

**C3：保留现有类型错误——建议，未执行。** 原基线与修复后均预计通过两项已存在的公开测试；它们只验证兼容性，不能单独证明 `S` 属性名已修复。不应在 ServerMode 跳过。

```bash
env TEST_SERVER_MODE=false AWS_DEFAULT_REGION=us-east-1 AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_EC2_METADATA_DISABLED=true PYTHONPATH=/testbed python -m pytest -q -p no:cacheprovider /testbed/tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py::test_put_item_wrong_datatype /testbed/tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py::test_put_item__string_as_integer_value
```

**C4：合法值、嵌套结构与返回值的窄范围回归——建议，未执行。** 原基线与修复后均预计通过这些公开用例；无需 Terraform 子模块、真实 AWS、Docker daemon 或全仓构建。

```bash
env TEST_SERVER_MODE=false AWS_DEFAULT_REGION=us-east-1 AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_EC2_METADATA_DISABLED=true PYTHONPATH=/testbed python -m pytest -q -p no:cacheprovider /testbed/tests/test_dynamodb/test_dynamodb.py::test_put_item_with_special_chars /testbed/tests/test_dynamodb/test_dynamodb.py::test_nested_projection_expression_using_get_item /testbed/tests/test_dynamodb/test_dynamodb.py::test_update_item_if_original_value_is_none /testbed/tests/test_dynamodb/test_dynamodb.py::test_update_nested_item_if_original_value_is_none /testbed/tests/test_dynamodb/test_dynamodb.py::test_put_return_attributes
```

## 5. 阅读范围与限制

实际打开的公开文件：

- `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`：全文。
- `base/.gitmodules`、`base/README.md`、`base/CONTRIBUTING.md`、`base/setup.cfg`、`base/pyproject.toml`、`base/requirements.txt`、`base/requirements-tests.txt`、`base/requirements-dev.txt`、`base/Makefile`：全文。还确认公开导出中没有 `base/setup.py`；没有向包外寻找它。
- `base/docs/docs/contributing/installation.rst`、`base/docs/docs/contributing/development_tips/tests.rst`：全文。
- `base/moto/dynamodb/models/table.py`：1–60、400–590；核心关注 475–577。
- `base/moto/dynamodb/models/dynamo_type.py`：1–155、262–307、350–421；仅用于理解类型表示和容器层级。
- `base/moto/dynamodb/models/__init__.py`：1–70、218–242、554–608；另对文件做 put/validation 调用符号检索。
- `base/moto/dynamodb/responses.py`：1–55、417–505；另做相关调用符号检索。
- `base/moto/dynamodb/exceptions.py`：310–350；`base/moto/dynamodb/__init__.py`：全文；`base/moto/settings.py`：1–15，以及测试模式/区域设置的符号检索结果。
- `base/tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py`：1–50、580–655、885–970，另做异常、测试名和类型输入符号检索。
- `base/tests/test_dynamodb/test_dynamodb.py`：1–45、160–365、530–600、2220–2265、3305–3365，另做 put/嵌套/null 相关符号检索。
- `base/tests/test_dynamodb/conftest.py`、`base/tests/__init__.py`、`base/tests/helpers.py`：全文。
- `base/tests/test_dynamodb/test_dynamodb_validation.py`：仅看 `rg` 返回的测试名、list/map 类型及更新校验相关匹配行，未展开全文；未据此声称全面审阅该模块。

文件名清单搜索涉及指定 PUBLIC_DIR 内 README/安装配置、DynamoDB 源码和测试、conftest、贡献文档；没有打开清单中其他服务文件。个别批量输出曾截断，随后针对本报告引用的关键片段单独重读；不把截断部分视为已完整审阅。

未查项包括完整 SDK 序列化实现、完整 mock 核心/传递依赖、全部 DynamoDB/其他服务测试、全量 list 畸形值诊断、真实 AWS 对照、公开祖先历史、镜像运行状态、网络策略实效和实际模型消息。`user_prompt.txt` 仅静态渲染，`base/` 并非完整容器（`environment_brief.md:3-6`）；bundle 会进入公开工作区的说明也不能证明其已进入 system message。当前上下文没有接触本题私有材料，但这只是遵守阅读范围的陈述，不是权限隔离或预训练无污染证明。
