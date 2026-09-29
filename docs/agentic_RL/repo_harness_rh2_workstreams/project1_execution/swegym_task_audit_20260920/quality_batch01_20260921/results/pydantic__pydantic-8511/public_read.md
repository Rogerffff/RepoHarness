# pydantic__pydantic-8511：公开视角静态审查

审查范围：仅角色卡与本题 `PUBLIC_DIR`。没有执行项目代码、导入包、运行测试、安装依赖、访问网络或 Git 历史，也没有修改 `base/`。以下路径均相对于本题公开包；行号对应导出的静态文件。本审查没有接触私有评分材料或修复答案。

公开材料足以说明核心问题并定位调查入口：在 Pydantic dataclass 中，赋值形式的 `Field(repr=False)` 应让字段退出自动生成的实例表示，达到示例中 `dataclasses.field(repr=False)` 的效果。需要核对的是运行条件和未明示组合的边界，而不是重新索取核心复现。

## 1. 需求表

| 行为 | 要求与应保留的旧行为 | 依据 | 确定程度 |
|---|---|---|---|
| 字段级隐藏 | 对题面 `a` 的 `c: int = pydantic.dataclasses.Field(repr=False)`，实例表示应省略 `c`；`b` 仍显示。题面注释 `a(b=1, c=2)` 是报告的原问题输出，不是目标输出。顶层执行该示例的目标可合理推知为 `x(y=3) a(b=1)`。 | `user_prompt.txt:3,10,18-29`；`base/pydantic/fields.py:670` | 隐藏行为明示；具体目标字符串由示例和接口说明推知。 |
| 标准库字段与普通字段 | `dataclasses.field(repr=False)` 已有隐藏行为应保留；没有关闭 `repr` 的普通字段、`Field()` 和 `Field(repr=True)` 应继续显示。输出应保持 dataclass 的类名、字段名、顺序与值的表示惯例。 | `user_prompt.txt:18-29`；`base/pydantic/fields.py:201,576-593`；`base/docs/concepts/dataclasses.md:13-24,27-30`；`base/docs/concepts/fields.md:515-534` | 公开接口与示例可合理推知；后一个文档示例是 BaseModel，不能当作所有 dataclass 组合的专门测试。 |
| 支持的调用入口 | 保留题面使用的 `pydantic.dataclasses.Field`，也应兼容 `pydantic.Field`、`pydantic.fields.Field` 所指向的同一字段函数。无需为题目增加新 API 或要求用户换写法。 | `base/pydantic/dataclasses.py:15`；`base/pydantic/__init__.py:24,96,246`；`base/tests/test_dataclasses.py:38,561` | 现有导出关系可推知。`dataclasses.py:20` 的 `__all__` 未列出 Field，但题面入口当前确实有显式导入绑定。 |
| 校验与数据内容 | 隐藏表示不等于删除字段、放弃校验或排除序列化。构造后仍应能取到 `c`，位置/关键字参数的正常处理应保留。`repr` 与 `exclude` 是不同参数。 | `base/pydantic/fields.py:664,670`；`base/pydantic/_internal/_dataclasses.py:135-145,178-182`；`base/tests/test_dataclasses.py:42-84` | 现有接口与测试可合理推知；题面没有要求改序列化。 |
| 默认值、工厂、元信息与继承 | 字段默认值、`default_factory`、schema 元信息、类属性默认值、构造签名不应因修复表示而丢失。 | `base/docs/concepts/dataclasses.md:47-99`；`base/tests/test_dataclasses.py:519-589,1938-1969,2481-2507`；`base/pydantic/_internal/_fields.py:281-292` | 有已有公开测试支撑的保留要求。 |
| 关键字参数与版本兼容 | 保留 `Field(kw_only=True)`，包括继承场景。普通 `repr=False` 不应凭空变成仅限 Python 3.10+ 的功能；项目声明 Python >=3.8，当前代码对 `kw_only`/`slots` 分支有版本保护。 | `base/tests/test_dataclasses.py:1622-1647`；`base/pydantic/dataclasses.py:144-167`；`base/pyproject.toml:46-50,64` | 现有支持范围与公开测试可推知；无需为此要求所有 Python 版本都在单个 actor 中预装。 |
| 类级表示控制 | 字段级 `Field(repr=False)` 不应等同于关闭整个类的自动表示；已有 `@dataclass(repr=...)` 参数及标准库兼容行为应保留。 | `base/pydantic/dataclasses.py:96-115,208-220`；`base/docs/concepts/dataclasses.md:103-104` | 现有接口可推知。装饰器参数说明 `dataclasses.py:122` 使用了“field”措辞，但转交标准库的调用位置能区分类级与字段级控制。 |
| 扩展组合 | `Annotated[..., Field(repr=False)]`、与 `dataclasses.field` 混用、重复 Field 设置冲突、既有标准库 dataclass 再装饰等组合未在 issue 中给出 repr 验收规则。继承、slots、自定义 `__repr__` 应避免回归，但无法由本题列出所有组合的精确输出。 | `base/tests/test_dataclasses.py:2395-2441`；`base/pydantic/fields.py:330-362`；`base/pydantic/dataclasses.py:194-220` | 有合理一致性期待，具体冲突优先级仍有解释空间。公开混用测试本身明确提示存在边界问题，不能把修复所有历史混用问题强加给本题。 |

## 2. 合理实现范围

- 验收应围绕字段是否出现在实例表示以及相关旧行为是否保持，不应绑定某个内部函数名、函数放置位置、循环形状或固定修改行数。`make_pydantic_fields_compatible` 是现有内部实现线索，不是题面规定的交付名称（`base/pydantic/dataclasses.py:147-167,208`）。
- 在标准库生成表示前整理字段元信息，或以其他兼容方式实现同样的表示语义，都应有被接受的空间。若采用自行处理表示的路线，仍需保留 dataclass 的格式、类级开关和已有自定义表示等语义；这里只界定等价行为，没有给出修复代码。
- 可以只调整需要处理的 Pydantic 字段，也可以在证明相关旧行为保持的前提下统一整理字段。公开要求没有规定必须包装所有字段、必须增加某个公共 API，或必须修改某个指定源码文件。
- 不能用只改题面例子、让用户改用标准库字段、关闭整类表示、删除 `c` 或硬编码类名的方式满足这项需求。题面明确要继续使用 Pydantic Field（`user_prompt.txt:10,23-28`）。
- 明确约定的命名与默认行为是既有 `Field`/`repr`/`kw_only` API 和默认 `repr=True`；示例中的 `x/a/y/z/b/c` 是复现数据，不是实现必须识别的名字。顶层示例可以按完整字符串验证，局部类的限定名称则应遵循正常 dataclass 表示，不能机械要求都输出顶层名称。

## 3. 初态线索与疑义

**可直接进入的调查路径。** 题面同时提供标准库字段与 Pydantic 字段的对照。`FieldInfo.repr` 已记录布尔值（`base/pydantic/fields.py:201`），但 Pydantic dataclass 在调用标准库装饰器前只为 Python 3.10+ 且 `kw_only` 为真的 FieldInfo 做兼容处理；该调用没有传递字段级 `repr`（`base/pydantic/dataclasses.py:144-167,208-220`）。随后才调用 `complete_dataclass` 收集 Pydantic 字段和生成校验器（同文件 `226-229`；`base/pydantic/_internal/_dataclasses.py:94,118,178-182`）。这足以形成“Pydantic 字段设置与标准库自动生成表示之间未同步”的静态调查假设；尚未执行，不能写成已经复现或已验证根因。

**已有测试的作用。** `base/tests/test_dataclasses.py` 提供默认值、工厂、schema、继承、关键字参数、签名等回归入口；对该文件搜索 `repr=False` / `repr=True` 未见匹配。因此不能把已有 dataclass 测试通过等同于核心问题已修复，也不能说全仓不存在相关测试。本题自身的短脚本已足以补上核心验证场景，禁改测试也不阻止用临时 shell 输入运行该脚本。

**版本差异。** issue 报告的是 Python 3.11.4、Pydantic 2.1.1、core 2.4.0 与 macOS（`user_prompt.txt:35-42`）；指定 base 的 `base/pydantic/version.py:6` 是 `2.6.0a1`，`base/pyproject.toml:68` 固定 core 2.14.5。前者是报告者环境，不是本次容器应被降级安装的规范。应在指定 base 上复现，再判断是否同一行为。

**哪些缺口真正重要。** actor 身份能否导入本地源码、是否有匹配的 pydantic-core 二进制依赖、pytest 与其默认配置需要的插件是否齐备，若缺失且无离线来源，会实际阻碍运行验证。真实解释器、安装包、资源、可写目录和网络限制只在环境说明中声明，未经过本角色验证（`environment_brief.md:3-13`）。核心问题不需要数据库、GPU、外部服务或外部数据文件；贡献说明也说明普通测试不需要数据库（`base/docs/contributing.md:40-42`）。

**无需补充的内容。** 此例没有依赖公开外链或附件中的专门内容；本地源码、说明和测试足以理解核心需求。标准库文档外链是参考，不是目前必须导入的缺失资产。读取调用者、跟踪字段收集和检查 Python 分支属于正常开发调查，不是题面不清。暂不需要请求公开祖先历史。

**分别登记三类输入。**

| 类别 | 本题材料 | 适用与待核对事项 |
|---|---|---|
| issue 目标 | `user_prompt.txt:3-42` 与 `public_bundle.json:1` 的 `problem_statement` | 修正字段级 repr；报告者版本仅是复现背景。 |
| harness 操作指令 | `public_bundle.json:1` 的 `public_hints`：只改非测试源码、禁止改测试、允许窄范围测试、完成后简短汇报 | 原禁止改测试指令是否进入当前实际求解条件仍须核对，审查不自行取消。若适用，源码修复与 shell 复现仍可进行；若不适用，可增加回归测试，但是否保留/计分须按实际恢复机制判断。本题未发现必须修改测试才能实现合理修复的理由。 |
| 环境事实声明 | 同字段称 `/testbed`、conda `testbed` 已激活；bundle 指定镜像与 digest；`environment_brief.md:8-12` 声明 actor、CPU/内存与网络范围 | 都不是本角色完成的运行证明。环境说明明确撤回“所有测试修改都会恢复、永不计分”作为当前机制概括；当前无按测试文件名统一排除，仍有具体官方文件恢复限制（`environment_brief.md:18-24`）。影响哪些文件由协调侧核对，不据此判本题不可用。 |

`public_bundle.json` 会写到解题容器公开路径；`public_hints` 没有渲染到 `user_prompt.txt` 不等于 actor 无法读取，也不证明它已经成为 system message（`environment_brief.md:3-4,23-24`）。

## 4. 开发需求表

以下命令全部是**建议，未执行**，预期在真实 actor 的 `/testbed` 中执行；不是在本静态导出目录执行的记录。成功/失败现象均为预期。

| 操作 / 资产 / 服务 | 公开依据 | 环境说明支持到哪层 | 缺口与最小验证 |
|---|---|---|---|---|
| Python 与本地包导入 | `base/pyproject.toml:64-68`：Python >=3.8、typing-extensions >=4.6.1、annotated-types >=0.4.0、core ==2.14.5；`base/pydantic/_internal/_dataclasses.py:12-18` 直接导入 core | 声明 conda 预激活，但明确待 actor 验证（`environment_brief.md:12,18-19`） | 执行下方 A。应成功导入且 `pydantic.__file__` 指向 `/testbed/pydantic`，版本与 base/依赖声明相容。ImportError、二进制加载错误或指到另一安装目录属于环境/路径问题，不能当作原 bug。 |
| 原问题复现 | `user_prompt.txt:15-29`，仅标准库与 Pydantic | 2 CPU/4 GiB 等为默认声明，本题未验证；没有重计算资产要求 | 执行 B。静态预期旧代码打印 `x(y=3) a(b=1, c=2)` 并在目标断言失败；修复后打印 `x(y=3) a(b=1)`，且 `c` 仍为 2。若实际原态不同，须记录实际输出再调查。 |
| 已有窄范围公开测试 | `base/tests/test_dataclasses.py:13-16` 需 pytest、dirty-equals、core、typing_extensions；`base/pyproject.toml:97-108,163-167` 列测试依赖并启用 benchmark 参数；`base/tests/conftest.py:14-20,39-43` | 声明允许工作区/home 写入，实际测试与依赖未核验 | 执行 C，再有需要执行 D。应完成收集与断言，旧代码可能通过这些保留行为用例；它们不能替代 B。缺 pytest-benchmark 时默认 addopts 可能导致参数错误；应按环境问题处理，不能声称 bug 复现失败。完整模块还可能使用临时目录 fixture。 |
| 依赖准备 | `base/README.md:34-38` 给普通安装方式；`base/Makefile:12-16`、`base/docs/contributing.md:48-77` 给 PDM 开发安装 | 公网下载不保证，解释器/系统包写权限待核对（`environment_brief.md:9-10`） | 最小复现依赖应由镜像或已声明离线缓存提供。只有缺依赖时才需要补足相应 wheel/包；不建议照 README 升级至最新发布版或无条件执行全量 `make install`，那会改变基线或依赖公网。PDM、pre-commit 不是直接运行 B/C 的必需服务。 |
| 构建 / 外部资源 | Python 源码问题；`base/pyproject.toml:1-6` 声明 hatchling 构建后端；`base/docs/contributing.md:40-42` | 没有已验证构建工具或缓存清单 | 本题最小修复验证不要求 wheel、文档构建或 core 源码编译。若交付流程需要打包，可用 E；须先有 hatchling、hatch-fancy-pypi-readme 与 pip，预期产出本地 wheel。无需为核心复现启动外部服务。 |

**A：最小导入与实际解释器/包路径检查（建议，未执行）。**

```bash
python -c "import sys, pydantic, pydantic.dataclasses, pydantic_core, annotated_types, typing_extensions; print(sys.executable); print(sys.version); print(pydantic.__file__); print(pydantic.__version__, pydantic_core.__version__)"
```

**B：核心复现与目标断言（建议，未执行）。** 通过标准输入运行，不修改仓库测试文件。

```bash
python - <<'PY'
import dataclasses
import pydantic.dataclasses

@pydantic.dataclasses.dataclass
class x:
    y: int
    z: int = dataclasses.field(repr=False)

@pydantic.dataclasses.dataclass
class a:
    b: int
    c: int = pydantic.dataclasses.Field(repr=False)

left, right = x(3, 4), a(1, 2)
print(left, right)
assert repr(left) == 'x(y=3)'
assert right.c == 2
assert repr(right) == 'a(b=1)'
PY
```

**C：保留行为的最小公开测试组（建议，未执行）。**

```bash
python -m pytest -q tests/test_dataclasses.py::test_simple tests/test_dataclasses.py::test_value_error tests/test_dataclasses.py::test_default_factory_field tests/test_dataclasses.py::test_schema tests/test_dataclasses.py::test_kw_only_subclass tests/test_dataclasses.py::test_dataclasses_inheritance_default_value_is_not_deleted tests/test_dataclasses.py::test_signature
```

**D：需要更广回归时运行相关单模块（建议，未执行）。**

```bash
python -m pytest -q tests/test_dataclasses.py
```

**E：仅在需要打包验证且构建依赖已提供时（建议，未执行）。**

```bash
python -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/pydantic-audit-wheel .
```

E 不会替代运行验证；若缺构建后端且网络受限，应登记依赖缺口，不推定源码修复有误。对 Python <3.10 的支持分支，若实际开发环境提供对应解释器，可以复用 B 检查；不把安装额外解释器列为核心复现前提。

## 5. 阅读范围与限制

实际读取的材料：

- 指定 `public_reader.md` 全文；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md` 全文。
- `base/pydantic/dataclasses.py` 全文；`base/pydantic/fields.py` 的 Field/FieldInfo 参数、初始化、dataclass 转换与 Annotated 合并片段；`base/pydantic/_internal/_fields.py:226-302`；`base/pydantic/_internal/_dataclasses.py:1-206`；`base/pydantic/__init__.py` 中 Field 导出相关搜索命中；`base/pydantic/version.py:1-28`。
- `base/tests/test_dataclasses.py` 中导入、基础校验、默认值/工厂、schema、kw_only、继承、元信息、Annotated 混用、init=False、签名、slots 相关片段，并在该文件搜索 repr 与字段调用；`base/tests/conftest.py` 全文。没有执行任何测试。
- `base/README.md` 安装与基础说明片段；`base/Makefile` 安装和测试目标及相关搜索结果；`base/pyproject.toml:1-171` 及测试/依赖相关搜索结果；`base/docs/contributing.md:35-109` 与相关搜索结果；`base/docs/concepts/dataclasses.md:1-121` 与字段相关搜索结果；`base/docs/concepts/fields.md:509-539` 与 repr 相关搜索结果。
- 对公开包执行文件名枚举；枚举到文件名不表示已打开其正文。

未查项：其余源码/测试全文、`pdm.lock` 的完整依赖解析、`docs/install.md`、`HISTORY.md`、`base_identity.json`、Python 标准库源码、真实镜像、实际 actor、运行资产、完整祖先历史及所有私有材料。没有网络搜索、没有读取其它题、没有访问角色卡父目录中的调查文件。

`user_prompt.txt` 是静态渲染文本，不证明真实模型收到的完整消息；`base/` 是源码导出，不是完整运行容器（`environment_brief.md:3-6`）。本报告不声称模型消息、工具入口、conda 激活、CPU/内存、依赖、源码可写性或公开测试运行条件已经验收。读取范围限制是协作约定，不是文件权限隔离，也不能证明预训练无污染。

关键未知：实际 actor 的本地导入路径与 core/pytest 插件可用性；原禁改测试指令的当前适用方式及具体官方文件恢复范围；未明示的 Annotated/混合字段冲突语义。前两类需运行侧核对，第三类不阻碍题面赋值形式的核心需求开发。
