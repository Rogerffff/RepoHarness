# getmoto__moto-5752 公开视角审查

本记录仅依据指定角色卡及本题公开包。以下路径相对于 `runs/swegym_quality_batch02_20260921_v2/public/getmoto__moto-5752/`；范围引用表示实际阅读的源码段。本轮只静态读取，未运行项目代码或测试、未安装依赖、未联网、未修改 `base/`。

## 1. 需求表

| 行为 | 判断层级 | 公开依据与边界 |
| --- | --- | --- |
| `ssm.describe_parameters(ParameterFilters=...)` 的过滤结果不应随过滤器顺序变化。 | 明示 | `user_prompt.txt:3-8,42-72,77-86` 给出两种顺序及相同预期。具体输入字段是 `ParameterFilters`，不是旧字段 `Filters`。 |
| 示例中同时要求 `tag:x=b` 与 `tag:hello=world`；两次都只能返回 `test_my_param_01_b`。 | 数量明示；参数身份可合理推知 | `user_prompt.txt:21-39,42-72,79` 创建的 a、b 都有 hello=world，只有 b 有 x=b。仅把两次结果改成相同但仍含不匹配参数，不能满足“返回值应匹配过滤器”的要求。 |
| 不同过滤器之间应为 AND（全部满足）；一个过滤器的 `Values` 中通常任一值命中即可。 | 可由公开仓库合理推知 | `base/moto/ssm/models.py:1578-1587` 明确写“matches all the filters”；普通字段匹配在 `1617-1624` 使用 `any`。已有 Type 多值测试 `base/tests/test_ssm/test_ssm_boto3.py:166-173`、Path 多值测试 `809-817,858-869` 支持值列表的 OR 语义。Label 分支有自己的既有规则，不能据此顺带重定义。 |
| 标签命中不能绕过后面的标签或非标签条件；任何一个条件不匹配都应排除参数。 | 可合理推知 | 上述“all”契约及题面“values returned do not match the filters”；`base/moto/ssm/models.py:1608-1613` 的标签分支目前直接返回，因此影响不局限于题面两组字面量。标签与 Name、Type、KeyId 等已支持条件的组合属于合理一般化。 |
| 保留单标签匹配、缺少所需标签时不匹配、默认 `Equals`、无过滤器时包含所有候选参数。 | 公开代码/测试约定 | 单标签及无标签参数的对照见 `base/tests/test_ssm/test_ssm_boto3.py:1026-1045`；默认值见 `base/moto/ssm/models.py:1584-1587`；无过滤器返回 True 见 `1644-1645`，无过滤器 API 测试见 `553-572`。 |
| 保留 Name、KeyId、Path 等现有过滤行为，以及参数校验、响应字段和分页。 | 公开代码/测试约定 | 默认 Path 为 `OneLevel`，其他字段为 `Equals`，见 `base/moto/ssm/models.py:1337-1340,1584-1587`。Name 斜杠归一化、Contains，Path OneLevel/Recursive，KeyId 过滤测试见 `base/tests/test_ssm/test_ssm_boto3.py:672-892`。校验测试见 `895-999`；元数据见 `1002-1023`；分页见 `575-604`。 |
| 旧 `Filters` 字段与 `ParameterFilters` 的互斥错误不变。 | 公开测试明确约定 | `base/moto/ssm/models.py:1291-1295`；`base/tests/test_ssm/test_ssm_boto3.py:895-904`。旧字段的单个 Name、Type、KeyId 测试见 `607-669`。题面不足以要求重写旧字段的多过滤器语义。 |
| 若改动共用匹配函数，应保留 `get_parameters_by_path` 的既有行为。 | 可由调用者合理推知 | 共用调用在 `base/moto/ssm/models.py:1302,1531`。路径接口的过滤、分页、非法键、Label 测试见 `base/tests/test_ssm/test_ssm_boto3.py:66-234`。这属于正常回归范围，并非缺失题面信息。 |

**仍存在多种解释或未承诺的部分：**题面没有规定内部算法、局部变量或新辅助函数名；没有要求更改返回参数的排序规则。它也没有明示要补齐所有 SSM 过滤能力。校验器对非 Path 条件普遍允许 `BeginsWith`（`base/moto/ssm/models.py:1462-1468`），但标签分支目前只检查值相等（`1608-1613`）；Tier 通过专门值校验（`1448-1453`），而匹配字段选择段 `1589-1616` 没有 Tier 分支。这些是可见的相邻疑义，不能在缺少独立需求的情况下自动扩大为本题必修项目。

## 2. 合理实现范围

应接受多种保持相同公开行为的实现，例如：逐项匹配并仅在某项失败时终止；对每项独立求布尔值后取逻辑与；或逐步缩小候选参数集合。标签的存在性判断可以使用循环、`any` 或内部索引。公开要求没有指定必须采用其中一种，也不要求添加某个固定名称的 helper。

可在现有共用匹配逻辑中修复，也可在保持共用调用者语义的前提下适当重构。合理结果必须适用于任意有效标签键值和过滤器排列，不能只识别示例名字、只检查第一个条件、仅排序后保留“首个命中即通过”的行为，或只保证两次返回数量相等。代码最终应保留“过滤器之间 AND、单个普通过滤器多值 OR”的既有约定。

确有外部约定的名称包括 boto3 方法 `describe_parameters`、请求字段 `ParameterFilters`/`Key`/`Option`/`Values`、标签前缀 `tag:`、响应字段 `Parameters` 及已有分页字段 `NextToken`。响应构造在 `base/moto/ssm/responses.py:247-271`；底层参数描述字段在 `base/moto/ssm/models.py:242-259`。过滤应发生在现有分页之前；没有必要为修复增加输出字段或改写元数据。

原“仅改非测试源码”的指令若适用，核心修复仍可合法完成，复现可用内联脚本执行，不需保存测试文件。若该限制不适用，添加顺序排列和混合条件回归测试也是合理开发方式，但不是另一种产品需求。当前审查不授权忽略原指令，也不根据其旧机制解释推断某类改动是否计分。

## 3. 初态线索与疑义

公开材料足以定位主要调查入口：API 响应层读取 `ParameterFilters` 后调用 backend（`base/moto/ssm/responses.py:247-258`），backend 对每个参数调用 `_match_filters`（`base/moto/ssm/models.py:1297-1303`），该函数在标签值命中时直接 `return True`（`1608-1613`）。静态推演显示，hello 在前时 a、b 都命中 hello 并跳过 x；x 在前时 a 首项失败、b 首项命中。因此源码能够解释题面两种结果，尚未实际复现。

已有 `test_describe_parameters_tags` 只有一个标签条件（`base/tests/test_ssm/test_ssm_boto3.py:1026-1045`），可作为保留行为检查，却不足以证明多条件排列问题已修复。应补用题面 MWE 检查两个顺序，并检查实际返回 Name；也可增加标签和普通条件的排列、不匹配标签位于首/末项等变体。无需先取得未来修复、私有测试或 Git 历史。

MWE 使用 `boto3.client('ssm')` 而未指定区域（`user_prompt.txt:19-20`）；公开旧测试明确传入 `region_name="us-east-1"`（例如 `base/tests/test_ssm/test_ssm_boto3.py:1028`）。开发时给出区域即可消除机器配置差异，这不是阻断需求理解的缺项。依赖导入、凭据占位和 mock 生效仍需实际 actor 检查，不能把潜在 `NoRegionError` 或导入失败当成该过滤 bug。

题面建议去真实 AWS 对照（`user_prompt.txt:13,79`），但已给出预期行为，源码契约也支持该预期。本题的最小复现和回归不需要 AWS 账号、真实云资源或外网。README 的文档链接和安装文档的外链未访问；目前没有发现必须补齐的外部附件或公开历史。若要另外裁定上述标签 `BeginsWith`、Tier 等扩展语义，才需要相应时代的公开接口依据；不能以此阻断当前窄修复。

**分别登记三类输入：**

- Issue 需求：修复 `ParameterFilters` 顺序导致的错误结果，见 `user_prompt.txt:3-86`。
- Harness 操作指令：`public_bundle.json:1` 的 `public_hints` 要求探索源码、只改非测试文件、禁止改测试、窄范围运行测试、完成后简短总结。字段虽未渲染在 `user_prompt.txt` 内，仍是公开可读材料（`environment_brief.md:20-26`）。
- 待验环境声明：`public_bundle.json:1` 声称 `/testbed`、conda `testbed` 已激活、python/pip/测试工具已指向该环境；包也给出镜像及 digest。静态材料不能证明这些运行事实。`environment_brief.md:3-12` 明确真实消息、预装包、资产、资源及 actor 执行均未验证。

旧提示“所有测试修改都会恢复、永不计分”不能代表当前机制：环境说明确认目前没有按测试文件名统一排除，仍有官方文件恢复等具体限制（`environment_brief.md:18-26`）。实际是否向求解者施加“禁止改测试”、哪些官方文件恢复，属于共享输入/运行条件待核事项；本公开角色不读取私有调查，也不据此给题目有效性标签。

## 4. 开发需求表

下表及后续代码块中的所有命令均为**建议，未执行**，以真实解题工作区 `/testbed` 为执行目录。这里没有验证该目录、镜像或 actor 身份。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口及最小建议命令、预期现象 |
| --- | --- | --- | --- |
| Python 与源码可写工作区 | `public_bundle.json:1`；`base/setup.py:140` 声明 Python >=3.6 | `environment_brief.md:8-12` 描述拟用 bash/edit、agent/54321 和可写工作区/home；实际解释器仍待验 | **建议，未执行：** `pwd`；`id`；`python -c 'import sys; print(sys.executable); print(sys.version)'`。应确认 `/testbed`、actor 及兼容解释器；输出未知，不能声称 conda 已激活。 |
| boto3、Moto SSM 及传递导入依赖 | `base/setup.py:29-48,92,99`；`base/moto/ssm/models.py:7-17` 导入 EC2、Secrets Manager、yaml；`base/moto/ssm/__init__.py:1-4` | 静态源码存在；没有已装版本清单或成功导入证据 | **建议，未执行：** `python -c 'import boto3, botocore, yaml; from moto import mock_ssm; import moto.ssm.models; print("imports ok")'`。应成功导入；缺包或版本不兼容属于环境故障，先于 issue 复现。SSM extras 不足以证明所有传递导入均满足。 |
| pytest、sure 与公开测试收集 | `base/requirements-tests.txt:1-7`；`base/tests/test_ssm/test_ssm_boto3.py:1-15`；`base/tests/__init__.py:3`、`base/tests/helpers.py:4` | 环境说明没有执行收集 | **建议，未执行：** `python -c 'import pytest, sure; print("test imports ok")'`；`python -m pytest --collect-only -q tests/test_ssm/test_ssm_boto3.py`。应能导入并收集该文件；不能从文本断言能成功。 |
| 依赖准备及离线来源 | `base/docs/docs/contributing/installation.rst:21-35`；`base/Makefile:17-19`；`base/requirements-dev.txt:1-5` | `environment_brief.md:10` 不允许假定公网下载；预装包和缓存未提供 | 文档完整开发安装入口是 **建议，未执行：** `make init`，会执行 setup develop 并安装开发依赖，不是当前已完成步骤。若实际缺包，应由协调者提供兼容预装环境或已声明离线源；不假定 pip 联网可行，也不先要求安装所有服务依赖。 |
| 本地 SSM mock、区域及占位凭据 | `user_prompt.txt:16-74`；`base/tests/test_ssm/test_ssm_boto3.py:1026-1045` | 可见 `mock_ssm` 入口；无实际 mock 成功记录 | **建议，未执行：** 运行下方内联 MWE，显式 `region_name`，使用虚拟凭据和禁用 EC2 元数据查询。初态预期第二种顺序多出 a 并触发断言；修复后两次均只有 b。无需真实 AWS 服务。 |
| 现有窄回归与共用调用者回归 | `base/tests/test_ssm/test_ssm_boto3.py:66-234,553-1045`；`base/moto/ssm/models.py:1531` | 未执行测试；只看到旧测试源码 | **建议，未执行：** `python -m pytest -q tests/test_ssm/test_ssm_boto3.py -k 'describe_parameters or get_parameters_by_path'`。目标为已有行为继续通过；现有单标签测试预计不能暴露题面顺序 bug。可给命令加与下方相同的占位 AWS 环境变量。 |
| 代码风格/构建 | `base/docs/docs/contributing/installation.rst:39-46`；`base/requirements-dev.txt:4-5`；`base/Makefile:21-44` | 工具是否安装及版本未验 | 纯 Python 局部逻辑无另行编译需求。若需要项目风格检查，**建议，未执行：** `python -m black --check moto/ssm/models.py`（公开固定 black 22.3.0）；`python -m flake8 moto/ssm/models.py`。预期无格式/静态检查错误；不需要为本题先运行全仓 `make test`。 |
| 静态资产、子模块及资源 | `base/.gitmodules:1-3` 仅列 Terraform AWS provider 子模块；`base/moto/ssm/models.py:54-82` 显示 `/aws` 参数可按需加载资源 | `environment_brief.md:5-6,11-15` 说明导出及资源限制，非完整容器 | MWE 仅创建普通 String 参数，不触发 `/aws` 默认参数加载，亦不使用 Terraform、Docker 或 GPU；这些不是本题已识别的最小必需服务。传递导入所需本地资产是否可读须随最小导入/MWE 验证。2 CPU/4 GiB 等是默认说明，未核验本题实际限额。 |

**建议，未执行：最小复现命令。** 这是题面 MWE 的等价精简版，显式补区域和本地凭据，并核对参数身份；不写入测试文件。

```bash
AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_DEFAULT_REGION=us-east-1 AWS_EC2_METADATA_DISABLED=true python - <<'PY'
import boto3
from moto import mock_ssm

with mock_ssm():
    client = boto3.client("ssm", region_name="us-east-1")
    for x in "ab":
        client.put_parameter(
            Name=f"test_my_param_01_{x}",
            Value=f"Contents of param {x}",
            Type="String",
            Tags=[{"Key": "hello", "Value": "world"}, {"Key": "x", "Value": x}],
        )
    filters = [
        {"Key": "tag:x", "Option": "Equals", "Values": ["b"]},
        {"Key": "tag:hello", "Option": "Equals", "Values": ["world"]},
    ]
    for ordered_filters in (filters, filters[::-1]):
        result = client.describe_parameters(ParameterFilters=ordered_filters)
        names = [p["Name"] for p in result["Parameters"]]
        print([f["Key"] for f in ordered_filters], names)
        assert names == ["test_my_param_01_b"], names
PY
```

上述预期全部来自题面和静态源码推演；这里没有真实执行结果。

## 5. 实际阅读范围与限制

实际全文读取：指定 `roles/public_reader.md`；本题 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`；`base/README.md`、`base/CONTRIBUTING.md`、`base/docs/docs/contributing/installation.rst`、`base/requirements-tests.txt`、`base/requirements-dev.txt`、`base/setup.cfg`、`base/Makefile`、`base/moto/ssm/__init__.py`、`base/tests/__init__.py`、`base/tests/helpers.py`、`base/.gitmodules`。

实际分段读取：`base/setup.py:1-152`；`base/moto/ssm/models.py:1-82,176-272,1270-1653`；`base/moto/ssm/responses.py:209-277`；`base/tests/test_ssm/test_ssm_boto3.py:1-238,503-1068`；`base/docs/docs/services/ssm.rst:1-120`。对部分段落因工具聚合输出截断而补读；未把未显示的截断内容当成已阅读。

仅搜索/列举：本题公开包文件名清单；`base/moto/ssm/` 的 `_match_filters` 调用点；models 中标签字段/资源标签相关行；`base/tests/test_ssm/` 内 `ParameterFilters`/`tag:` 相关命中（包括 `test_ssm_cloudformation.py:56`，未阅读全文）；配置文件名与 setup/requirements 关键词。尝试读取 `base/tests/conftest.py`，该路径不存在；未据此推断其他测试配置或实际运行环境。

未查：`base_identity.json`、完整 Git 历史、真实镜像或 `/testbed`、安装包版本/权限、全仓测试、其他服务的完整实现、其他题、私有评分材料、gold、manifest、汇总和其他角色产物。没有访问共享镜像克隆或外部网站，没有进行 AWS 对照。

`user_prompt.txt` 只是静态渲染，不是实际模型消息捕获；`public_bundle.json` 的可见字段不能证明它进入了 CLI system message；`base/` 只是源码导出，不是完整运行容器（`environment_brief.md:3-6,20-26`）。因此本记录不声称消息、依赖、资源或开发条件已通过验证。本轮没有读取私有材料；这仅是阅读范围的协作记录，不是文件权限隔离或预训练无污染证明。

关键未知集中在实际 actor 的解释器/依赖/资源可用性，以及旧“禁止改测试”指令和官方文件恢复机制的实际适用方式。核心行为需求已有足够的公开依据；未识别需要额外私有或未来材料才能开展的必要步骤。
