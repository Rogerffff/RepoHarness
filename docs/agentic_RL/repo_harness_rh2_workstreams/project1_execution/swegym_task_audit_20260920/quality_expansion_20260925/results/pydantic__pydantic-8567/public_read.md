# pydantic__pydantic-8567 单题公开静态审阅

本报告为独立公开读者的静态判断，未修题、未导入项目、未运行样例或测试。未读取 gold、隐藏测试或其他角色结论，不作成功率或训练资格判断。只使用指定角色卡、本题四个公开文件和 base 内公开源码、文档、旧测试；没有沿链接取材。fresh 上下文不等同于 OS 隔离或预训练污染证明。

路径约定：

- `PUBLIC=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-8567`
- 以下 `base/...` 均精确指 `PUBLIC/base/...`，其后数字为文件行号。
- 角色卡：`/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/roles/public_reader.md`。

## 1. 先从题面形成的目标、约束、旧行为与疑义

这一阶段先读角色卡及四个公开文件，再形成如下解释；没有先用实现反推需求。

目标：修复 `Annotated` 中 `PlainSerializer` 放在 `PlainValidator` 前面时不生效的问题。`user_prompt.txt:14-18,26-45` 明确期望两种顺序具有同样的验证/序列化作用。样例两字段输入不同，因此“相同结果”不是让 x、y 的值相等，而是都采用同一序列化转换：x 应为字符串 `"0"`，y 应为字符串 `"1"`。题面展示的旧输出是 `{"x":"0","y":true}`（48-53）；这是报告者观察，并非本轮复现事实。

约束：`public_bundle.json:1` 的 public_hints 声明修复 NON-TEST 源码、不得改测试、允许窄范围验证，工作目录 `/testbed`，工具 bash/edit，预激活 conda 环境名 testbed。这些是来源声明；`environment_brief.md:3-7` 明确说明真实消息、public_hints 交付、实际 actor 工作树、工具和环境尚未取得。静态审阅自身禁止项目运行，优先于这里列出的未来开发验证建议。

从题面可合理保留的旧行为：无问题顺序 BRight 应继续生效；两字段仍先通过 `bool(int(x))` 得到布尔值，再由序列化函数转成字符串；不要把字段验证结果直接改为字符串来伪装修复；不应硬编码字段名、bool 类型或本例 lambda。

当时尚有疑义：plain validator 是否有意切断序列化；Annotated 顺序是否普遍不重要；支持带 info 参数的 validator 是否也需修复；Python dump 与 JSON dump 的关系；是否须改变 JSON Schema 生成；是否需要 pydantic-core 改动；新调用内部 handler 会否改变原先绕过类型 schema 生成的行为。题面没有要求任意多个 serializer 的全排列可交换，也没有规定唯一实现方式。

## 2. 公开源码、文档、旧测试的消解结果

### 2.1 根因可静态定位

`base/pydantic/_internal/_generate_schema.py:1658-1672` 解包 Annotated，并调用 `_apply_annotations`。后者在 1725-1734 按 annotation 顺序逐层包装 handler；`_get_wrapped_inner_schema:1805-1825` 让当前 annotation 的 `__get_pydantic_core_schema__` 决定是否调用此前的内部 handler。因而最后一个 annotation 在外层。

`base/pydantic/functional_serializers.py:32-56` 的 `PlainSerializer.__get_pydantic_core_schema__` 先调用 `handler(source_type)`，再把含函数、info_arg、return_schema 和 when_used 的序列化规则写入 `schema['serialization']`。

反之，`base/pydantic/functional_validators.py:155-162` 的 `PlainValidator.__get_pydantic_core_schema__` 直接返回新的 with-info 或 no-info plain validator schema，两支均不调用 handler，也不附加 serialization。于是 BWrong 外层 PlainValidator 跳过内部 PlainSerializer；BRight 外层 PlainSerializer 能拿到 plain validator schema 再附加序列化规则。这条静态路径支持题面症状，但不等于已验证实际运行输出。

### 2.2 应保留的是验证短路，不是静默丢失显式序列化

`base/pydantic/functional_validators.py:129-162` 描述 plain validator 替代内部验证；`base/docs/concepts/validators.md:60-70` 明确不调用内部验证。该文档 131-135 又明确验证 metadata 顺序有意义；206、250-260 的示例输出表明 plain 左侧的内部验证被截断，而外层 after/wrap 仍执行。因此不能通过全局重排所有 Annotated metadata，或把 PlainValidator 改成 BeforeValidator/AfterValidator 来修复。

`base/docs/concepts/serialization.md:227-257` 与 `base/pydantic/functional_serializers.py:19-30` 定义 PlainSerializer 修改序列化输出，默认 `when_used='always'`，可配置仅 JSON 使用。已读文档并未把 plain 的验证短路表述为禁用序列化；结合题面，修复应在保留短路验证的同时保留显式序列化。

旧测试提供兼容性依据：

- `base/tests/test_validators.py:81-89` 覆盖带 info 的 PlainValidator；164-181 的 typing-cache 参数化覆盖不带 info 的 PlainValidator。两个分支都属于已有 API。
- `base/tests/test_validators.py:2711-2718` 验证字段名与已验证数据仍传入 plain validator，原输入 `'1'` 未先转 int，且输出为 dict，进一步限制“先执行基础类型验证”类修复。
- `base/tests/test_serialize.py:83-102` 明确默认 always 在 `model_dump()`、`model_dump(mode='json')`、`model_dump_json()` 均生效，而 json-only 保留 Python dump 的原值。因此合理修复范围不应只特判 `model_dump_json()`。
- `base/tests/test_serialize.py:105-146` 展示 WrapSerializer 和可选类型中的 serializer 既有行为；它们是相邻回归面，但题面没有明确要求重定义所有 serializer 组合语义。

已读旧测试区段没有直接覆盖本题 PlainValidator 与 PlainSerializer 的两种排序组合；不能因此断言完整公开测试树不存在任何相关覆盖。

### 2.3 可用实现结构及仍有边界

`base/pydantic/functional_validators.py:680-689` 的 SkipValidation 已使用独立 serialization wrapper 将原 schema 作为序列化依据，同时验证用 any_schema；同文件 638-655 的另一公开实现还示范原 schema 生成失败时保留 Python 验证能力。这些说明验证与序列化路径分离在本仓库已有结构依据，无需凭题面就断言必须修改 pydantic-core。

但 `base/pydantic/annotated_handlers.py:67-79` 明示调用内部 handler 可能抛 PydanticSchemaGenerationError。旧 PlainValidator 根本不调用它，所以简单增加无保护的 handler 调用可能引入构建阶段回归；这是静态风险，尚未用运行实例确认。是否复制顶层 serialization 已足够，取决于嵌套 schema 的序列化规则如何保存；不能把仅满足 bool 样例的浅层复制当作通用正确性证明。

`base/docs/concepts/json_schema.md:581-615` 说明 PlainValidator 的 JSON Schema 生成原本可能报错，并给出 WithJsonSchema 覆写方案。题目要求的是序列化数据输出，不是强制 PlainValidator 自动获得基础类型的验证 JSON Schema；不应无依据改变这项旧行为。

## 3. 合理实现范围与非唯一选择

必要行为：两种排序均保留 PlainSerializer，样例验证值为 False/True，dump 为字符串 `"0"`/`"1"`；保留 with-info/no-info、字段信息、默认 always 和显式 when_used/return_type 的约定；plain 左侧内部验证继续不运行，右侧外层验证仍遵循顺序。

合理落点是 PlainValidator 的 schema 构建，或等价的内部 schema 组合逻辑。至少有两类候选设计，均非对不可见 gold 的描述：

1. 构造 plain validation schema，同时通过独立序列化路径委托内部 schema，参考已有 SkipValidation 的分离方式；需审查 schema 构建失败与引用/递归情况。
2. 在组合阶段有针对性地保留内部序列化信息，再附到 plain validation schema；若采用复制或提取，必须证明嵌套规则、return_type、when_used 和 serializer info 不丢失，并控制影响面。

实现的代码形状、辅助函数位置和错误处理组织不是题面指定的；只做源码修复，不改公开测试以充当提交成果。未知底层类型、模型/容器默认序列化、WrapSerializer、多 plain/multiple serializers 的更广组合应作为按改动路径选择的兼容性探查，不能在没有公开依据时全部升级为本题强制新功能。

## 4. 开发需求表

下表命令只是在未来获得 actor 环境后可用的最小验证建议，本轮全部未执行。`/testbed` 是公开声明路径，实际存在性 unknown。

| 需要操作/资产 | 公开依据 | 实际证据或 unknown | 最小公开验证命令及预期 |
|---|---|---|---|
| 确认实际输入、提示及工具权限 | public_bundle.json 的 public_hints；environment_brief.md:4-7 | 实际用户/system 消息、public_hints 是否交付、bash/edit 可用性均 unknown | 仓库命令无法证明消息交付；需捕获 actor 本次实际消息和工具能力记录，逐项核对公开声明，当前仍 unknown。 |
| 确认初始源码身份及原有修改 | public_bundle.json base_commit；base_identity.json:3-6；environment_brief.md:2-3 | 静态导出身份为 8060fa1cff965850e5e08a67ca73d5272dcdcf9f；实际 actor HEAD/status/diff unknown | `git -C /testbed rev-parse HEAD`、`git -C /testbed status --short`、`git -C /testbed diff -- pydantic/functional_validators.py`；预期识别目标版本及预存修改，不能预设干净。 |
| 编辑 NON-TEST Python 源码 | public_hints；根因在 functional_validators.py:155-162 | 静态源码存在；actor 文件存在性、读写权限、edit 工具 unknown | `test -r /testbed/pydantic/functional_validators.py && test -w /testbed/pydantic/functional_validators.py`；预期可读写，随后实际编辑结果仍需复核。 |
| 项目解释器、Python 依赖与正确导入位置 | pyproject.toml:64-69 要求 Python>=3.8、typing-extensions>=4.6.1、annotated-types>=0.4.0、pydantic-core==2.15.0 | 只有静态依赖声明；实际 conda、解释器和依赖 unknown。题面报告的 core 2.14.6 不代表该 base 环境 | `python -c 'import sys,pydantic,pydantic_core; print(sys.executable); print(sys.version); print(pydantic.__file__); print(pydantic_core.__version__)'`；预期从 actor 源码导入，core 匹配 base 声明。 |
| 本题最小行为复现/验证 | user_prompt.txt:23-53 | 只有题面报告和静态根因，未复现 | 用 `python -` 执行下列公开样例验证片段；修复后断言应通过，旧症状预计在 y 序列化断言暴露，实际须运行核实。 |
| 窄范围旧测试工具及插件 | tests/test_validators.py:13-16；tests/test_serialize.py:11-13；pyproject.toml:98-109,154-170 | pytest、dirty-equals 及 benchmark 等插件是否安装 unknown；静态配置默认含 benchmark 参数 | `python -m pytest -q tests/test_validators.py -k 'annotated_validator_plain or annotated_validator_typing_cache or plain_validator_field_name'`；随后 `python -m pytest -q tests/test_serialize.py -k 'serializer_annotated'`。预期可以收集且相关测试通过；依赖或插件报错先作为环境事实记录。 |
| 本地运行临时目录及缓存写入 | tests/conftest.py:39-43,54-99 的临时模块机制 | actor UID/HOME/cwd/PATH、临时目录、缓存权限 unknown；上述窄选集是否用这些 fixture 不能仅凭该区段断言 | `python -c 'import tempfile; f=tempfile.TemporaryFile(); f.write(b"ok"); f.close()'`；预期可进行最小临时文件操作，具体测试路径由实际运行确认。 |
| 是否需要网络、容器、GPU、额外数据资产 | 本题纯 Python 验证/序列化样例；base_identity.json:10-13 的静态导出边界 | 无公开证据要求网络、GPU或模型；实际网络、镜像资产、资源权限均 unknown | 最小公开行为片段应可在已具依赖的本地 CPU 环境运行，无须新增网络/容器操作。不能从 base 未导出依赖或 .git 推断镜像缺失。 |

拟议的最小行为验证片段（未执行，不是提交改动）：

```python
from typing_extensions import Annotated
import json
from pydantic import BaseModel, PlainValidator, PlainSerializer

BWrong = Annotated[bool, PlainSerializer(lambda x: str(int(x)), return_type=str),
                   PlainValidator(lambda x: bool(int(x)))]
BRight = Annotated[bool, PlainValidator(lambda x: bool(int(x))),
                   PlainSerializer(lambda x: str(int(x)), return_type=str)]
class Blah(BaseModel):
    x: BRight
    y: BWrong

m = Blah(x=0, y=1)
assert m.x is False and m.y is True
assert m.model_dump() == {'x': '0', 'y': '1'}
assert m.model_dump(mode='json') == {'x': '0', 'y': '1'}
assert json.loads(m.model_dump_json(indent=2)) == {'x': '0', 'y': '1'}
```

用 typing_extensions 的 Annotated 是为了兼容 base 声明的 Python 3.8，与公开旧测试采用方式相同。额外验证宜替换为带 info 参数的等价 validator，确认两分支均保留 serializer；再检查 `when_used='json'` 时 Python dump 保持布尔值。验证短路可用 `Annotated[int, PlainValidator(lambda v: v)]` 输入非数字字符串，预期验证仍返回原字符串；这项验证只检查验证阶段，不把其 dump 行为预设为新契约。

## 5. 实际阅读边界与证据强度

完整阅读：角色卡；`PUBLIC/public_bundle.json:1`；`PUBLIC/user_prompt.txt:1-72`；`PUBLIC/environment_brief.md:1-10`；`PUBLIC/base_identity.json:1-21`。base_identity 声明静态条目 458、已验证 blob/模式/路径集合，且无静态 symlink/LFS/gitlink 条目；本读者未重新计算全部 base 清单，不将这些声明扩大为 actor 状态。

逐行阅读的 base 区段：

| 文件 | 实际显示并阅读区段 |
|---|---|
| pydantic/functional_validators.py | 1-180、632-690 |
| pydantic/functional_serializers.py | 1-155 |
| pydantic/_internal/_generate_schema.py | 1658-1738、1805-1836 |
| pydantic/annotated_handlers.py | 64-120（请求至 144，实际文件止于 120） |
| docs/concepts/validators.md | 48-77、114-270 |
| docs/concepts/serialization.md | 227-263 |
| docs/concepts/json_schema.md | 581-623 |
| tests/test_validators.py | 1-190、2680-2725 |
| tests/test_serialize.py | 1-155 |
| tests/conftest.py | 1-110 |
| pyproject.toml | 60-126、154-185 |

另外只读了 rg 返回的匹配行与文件名：对 functional_validators.py、functional_serializers.py、docs/、tests/ 搜索 `class PlainValidator|class PlainSerializer|PlainValidator|PlainSerializer`；对 functional_validators.py 和 _generate_schema.py 搜索 `_apply_annotations`、`_get_wrapped_inner_schema`、`_annotated_schema`、`serialization`、`SkipValidation`；对 pyproject.toml 搜索 Python/core/pytest/依赖配置；通过 `rg --files base` 后过滤 requirements、conftest.py、Makefile、annotated_handlers.py 定位文件。这些检索会显示其他文档/测试的命中行，但没有全文阅读它们。

未读范围包括上述文件其余区段、其他源码/文档/测试全文、Makefile 内容、外部 pydantic-core 实现、安装环境和 actor 工作树；未访问 private、history、其他题/角色输出、manifest、assignments、准备报告、根结论、旧质量结论或未授权工作区。检索输出中的外链未访问。

结论证据强度：排序缺陷的 schema 构建机制有直接公开源码支持；修复目标有题面、文档及旧测试语义支持；运行时症状、修复有效性和开发环境可用性尚未验证，均不能写成已确认事实。报告保存后计算 SHA256 并封存，不再回写。
