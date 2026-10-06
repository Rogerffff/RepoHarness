# python__mypy-16869：公开视角静态审查

审查日期：2026-09-21。本报告依据全新单题公开读者上下文。公开包为 `runs/swegym_quality_batch04_20260921_v1/public/python__mypy-16869/`，下文文件/行号均相对此目录。bundle 指定 base 为 `8c2ef9dde8aa803e04038427ad84f09664d9d93f`。未修复代码，未执行项目、导入项目或运行测试。

核心判断：题面提供了完整的小型复现和可追踪的调用栈；公开源码足以提出具体调查路线。明确目标是让 `stubgen` 处理 `Generic[*_Ts]` 时不再崩溃。源码还支持“保留基类的可变长类型参数语义”这一合理预期，但没有提供新场景的完整预期 `.pyi`。尤其 `_Ts` 是私有名称，现有过滤规则可能省略其定义；这应与本次星号表达式崩溃分开记录，不能直接扩展成“所有私有定义都必须输出”。开发环境是否可运行尚未验证。

## 1. 需求表及输入性质

| 行为/约束 | 性质 | 公开依据与解释 |
| --- | --- | --- |
| `stubgen test.py` 能处理 `TypeVarTuple` 配合 `Generic[*_Ts]`，不因该表达式抛出内部 `TypeError` | 明示 | `user_prompt.txt:3–11,15–44,51–55` 给出标题、完整源代码、调用和环境。应能实际生成该模块的 stub；单纯吞异常并不生成类不满足通常的“修复崩溃”含义。 |
| 保持类名、泛型基类和解包的类型参数语义 | 可由公开仓库合理推知 | `base/docs/source/stubgen.rst:8–16,50–53` 说明 stub 的类型接口用途及草稿性质；`base/mypy/stubgen.py:703–758` 保留类名和下标基类；`base/test-data/unit/stubgen.test:1198–1212` 明确保留 `Generic[T]`。因此把星号参数删掉、输出普通单参数泛型或无基类的类，不是有力的语义修复。 |
| 已支持的普通泛型、TypeVar/ParamSpec/TypeVarTuple 声明和已有导入别名行为不退化 | 强公开回归约束 | `base/test-data/unit/stubgen.test:1198–1212,1349–1425`，以及 `base/mypy/stubgen.py:998–1007`。已有 `TypeVarTuple` 声明支持不等于星号基类打印支持。 |
| 保持非星号表达式打印、类型别名、导入跟踪和格式约定 | 可推知，部分由公开输出固定 | `base/mypy/stubgen.py:272–340,1045–1049`；`base/test-data/unit/stubgen.test:1427–1477,3705–3721`。已有测试逐行比对输出（`base/mypy/test/teststubgen.py:713–722`）。不能以此推断新场景唯一允许的内部实现或完整输出。 |
| 默认过滤私有名称，`--include-private` 可改变过滤 | 明确现有约定；与新需求有边界疑义 | `base/mypy/stubutil.py:767–780`；`base/mypy/stubgen.py:826–834,1121–1126`；文档 `base/docs/source/stubgen.rst:165–168`；公开测试 `base/test-data/unit/stubgen.test:297–313`。原复现恰好使用 `_Ts`，题面没有说明是否同时要求默认输出其定义。 |
| 默认文件输入与 `--no-analysis` 路径都应维持合理生成行为 | 合理回归范围，非题面逐项列出的新功能 | `base/mypy/stubgen.py:1579–1601,1634–1644` 的两条 AST 获取路径共用生成器；`base/mypy/test/teststubgen.py:655–674,700–713` 明确区分解析、语义分析、导入和检查模式。不能用强制改变默认模式代替修复。 |
| 输出位置、CLI 标志、错误处理默认值不需要改变 | 明确现有接口 | `base/docs/source/stubgen.rst:65–71,120–145,160–168,186–191`；`base/mypy/stubgen.py:1723–1760,1821–1853`。题面没有请求新标志或改变默认导出范围。 |
| 修改非测试源码、不要修改测试、测试保持窄范围、完成后短总结 | harness 操作指令，不是 issue 的语义需求 | `public_bundle.json:1` 的 `public_hints`。这些字段虽未拼进当前静态 `user_prompt.txt`，仍是容器公开可读输入，不能视为不存在。 |
| `/testbed`、conda `testbed` 已激活、Python/pip/test 工具可用 | 待验证环境声明 | `public_bundle.json:1`；`environment_brief.md:3–13,20–26` 明确未验证实际消息、shell、身份下的依赖和运行条件。镜像名及 digest 是定位信息，不能证明镜像内运行状态。 |

旧提示中“所有测试修改都会恢复、永不计分”的解释不能代表已核实的当前机制；公开环境说明指出已取消按测试文件名统一排除，仍有官方文件恢复等具体限制（`environment_brief.md:18–26`）。本角色不据此取消“不改测试”的原指令。若该指令适用，生产源码修复仍有合理空间，可运行既有测试与临时复现，不必修改测试文件；若不适用，可以补充公开回归用例。当前何种指令实际应用、哪些官方文件被恢复属于共享输入/运行条件待核对项。本题公开代码没有显示必须修改测试才能完成源码修复。

## 2. 调查入口、相关调用者和合理实现范围

静态可追踪的链路是：

1. `main` → `generate_stubs` → `generate_stub_for_py_module` → `ASTStubGenerator`（`base/mypy/stubgen.py:1857–1865,1654–1683,1634–1644`）。原命令按文件路径输入，实际走 `create_source_list` 分支，不要求执行复现模块的顶层代码；按 `-m/-p` 输入时才有默认导入分支（同文件 `1396–1425`）。
2. `visit_class_def` 调用 `get_base_types`，对 `base_type_exprs` 和语义分析移出的 `removed_base_type_exprs` 中的 `IndexExpr` 使用 `AliasPrinter`（同文件 `703–758`）。同时处理两组基类是需要保留的行为。
3. `AliasPrinter.visit_index_expr` 递归打印下标；`visit_tuple_expr` 将子节点结果交给 `str.join`（同文件 `308–326`）。`fastparse` 将下标和星号 AST 转成 `IndexExpr`、`StarExpr`（`base/mypy/fastparse.py:1611–1631`）；`StarExpr.accept` 分派到 `visit_star_expr`（`base/mypy/nodes.py:1726–1744`）。
4. 公开 base 的整个 `AliasPrinter`（`base/mypy/stubgen.py:262–340`）没有 `visit_star_expr`；继承的 `NodeVisitor` 文档说明默认返回 `None`，该方法本身为空（`base/mypy/visitor.py:349–360,483–484`）。这与题面“拼接期待字符串却得到 None”的症状直接对应，是静态根因线索，未通过实际执行确认。纯 Python 与编译版可能给出不同 `TypeError` 文本，不能要求 traceback 字面完全一致。题面旧 traceback 行号与 base 略有偏移，但同名函数可定位，不构成材料缺失。

合理路线包括在表达式访问器层面处理星号节点，或在基类表达式序列化层面用统一递归逻辑覆盖它。两者都应递归保留被解包的表达式、参数顺序、名称及导入依赖，不应依赖 `_Ts` 或 `ClassName` 这两个复现字面值。实现位置和辅助函数名称未被公开需求固定，本报告不提供补丁。

保留原来的 `Generic[*Ts]` 拼写最符合现有打印器的行为；语义等价的 `Generic[Unpack[Ts]]` 也有公开仓库依据（`base/test-data/unit/check-typevar-tuple.test:98–118`）。若采用后一条路线，应处理相应导入、名称冲突、目标语法版本和既有非星号输出，不应仅因新场景未指定精确文本就拒绝这种实现，也不能据公开材料断言任何特定验收器必然接受它。

不能把 `None` 转成字符串、丢掉不支持的子节点、统一降级成 `Any/Incomplete`、跳过出问题的类或要求用户改成 `--ignore-errors`，作为有充分语义依据的完成方式。未发现有公开要求必须增加新 CLI 标志、改类型检查器的泛型推理、支持所有 PEP 646 场景或覆盖所有 Python 新语法。

`AliasPrinter` 还服务于元类、dataclass 装饰器、Typed NamedTuple 字段、TypedDict 键/值及类型别名/类型变量声明（`base/mypy/stubgen.py:719,792–800,886–898,965–985,1045–1049`）。修改共享打印器时需保持这些调用者的非星号行为。普通变量/函数注解另经 `AnnotationPrinter`（`base/mypy/stubutil.py:193–278,751–758`）；不能假设只修复基类路径就验证了全部注解解包。`is_alias_expression` 也有独立的接受条件（`base/mypy/stubgen.py:992–1043`），本次是否扩展星号类型别名属于范围选择，不是题面明示必须完成的功能。

## 3. 初态线索与真正的未知

- **调查信息充足：**源代码仅需一个文件，无外链附件、私有数据、服务凭据或远端接口。已有源码与测试能给出行为保留的依据。阅读调用者、追查 AST 节点、确认运行模式属于正常开发工作，不是题面缺陷。
- **精确输出尚未固定：**题面没有 `.pyi` 样例。最确定的是生成该类而不崩溃，并保留解包语义。是否要求同时修复默认过滤 `_Ts` 导致的声明缺失，应单列。可以用默认原复现判断崩溃，再用公开名称 `Ts` 或 `--include-private` 隔离打印功能；这些变体不能替代原命令的回归检查。草稿 stub 的文档说明也不等于允许任意丢失泛型信息。
- **解释器版本是真正的开发前提：**issue 报告 Python 3.12.0。项目整体最低要求是 3.8（`base/setup.py:234`），并不代表任意受支持解释器都能复现该星号下标语法。解析器使用运行时 stdlib `ast`（`base/mypy/fastparse.py:124–140,210–242`）；公开 typeshed 也将 `typing.TypeVarTuple/Unpack` 放在 3.11 分支（`base/mypy/typeshed/stdlib/typing.pyi:110–118,207–220`）。建议原复现使用 3.12，至少须验证实际解释器能解析该语法。仅更换为 `typing_extensions` 并不能为旧解释器增加星号下标语法。
- **部署代码来源未知：**静态 base 未包含实际安装状态或编译产物。需要确认容器中导入的是这份源码；若导入的是已安装发行版或遮盖源码的编译扩展，编辑可能不会影响复现。源码默认可用纯 Python 安装路径，mypyc 是显式开关（`base/setup.py:88–96,178–179`），因此没有公开依据将 C 编译器、GPU 或完整编译构建视为最小开发必需条件。
- **运行条件未验：**`environment_brief.md:8–12` 只说明准备使用的工具、actor 和资源 profile；未验证 Python、依赖、typeshed/测试数据可读、临时目录可写、资源是否足够。若缺少适用解释器或必需依赖且没有已声明离线供给，才会实际阻碍开发。无需现在补公开祖先历史、完整仓库测试能力、外部文档或隐藏验收材料。

## 4. 开发需求与最小公开验证建议

下表及后续代码块中的命令全部为**建议，未执行**。供真实 `/testbed` 中的 actor 身份 CPU 验证使用，不是本次静态审查的运行记录。

| 操作/资产/服务 | 公开依据 | 环境说明支持层级 | 未知/缺口 | 最小建议与预期 |
| --- | --- | --- | --- | --- |
| 适用 Python、项目运行依赖、指向源码的导入 | `user_prompt.txt:51–55`；`base/mypy-requirements.txt:1–4`；`base/setup.py:209–224,234` | bundle 声明 conda 已激活；环境说明要求 actor 再验证 | 真实版本、`typing_extensions`/`mypy_extensions`、源码/编译模块路径未验；`tomli` 只在低于 3.11 时要求 | 建议，未执行：运行下面 A；成功应导入 stubgen 并报告 `/testbed` 对应代码路径，解释器满足原复现语法。依赖错误是环境入口问题，不是原 bug 的失败信号。 |
| 本地源文件、stdlib/typeshed、可写临时输出 | `base/mypy/stubgen.py:1396–1425,1535–1546,1557–1601,1646–1651`；公开 `typing.pyi` | base 有跟踪源码/资料；真实额外资产和权限未知 | actor 能否读取 typeshed、写输出/临时目录未验 | 建议，未执行：运行下面 B；预期 base 在打印处出现与 issue 一致类别的 `TypeError`，修复后生成 `.pyi`。文件输入不必导入复现模块，不依赖 macOS 或外部服务。 |
| 解析与语义分析两种路径 | `base/mypy/test/teststubgen.py:658–674,700–713`；`base/mypy/stubgen.py:1579–1601` | 仅静态测试入口存在 | 原复现各路径是否实际到达相同节点未执行确认 | 建议，未执行：B 中先原默认命令，再 `--no-analysis`。后者用于定位共用打印器；不能用它替代默认路径。 |
| 公开窄回归、pytest 配置和测试数据 | `base/test-requirements.txt:55–63,78`；`base/conftest.py:5–11`；`base/pyproject.toml:89–110`；`base/mypy/test/config.py:12–19` | 工具和资产都需再验 | pytest/xdist 是否安装、数据插件可否收集、临时目录可写未知 | 建议，未执行：运行下面 C，以 `-n0` 限定串行。既有相关输出应保持；旧用例通过不能证明新 bug 已修复，须同时做 B。 |
| 必要时离线可编辑安装；完整构建不是默认前置 | `base/CONTRIBUTING.md:39–49`；`base/pyproject.toml:1–16`；`base/setup.py:88–96,178–179` | 不能假定公网或解释器目录写权限（`environment_brief.md:9–12`） | pip/build 依赖/可写目标与离线包供给未验 | 建议，未执行：仅在 A 发现源码绑定缺失且本地 prerequisites 齐全时，考虑 `MYPY_USE_MYPYC=0 python -m pip install --no-index --no-deps --no-build-isolation -e .`。然后重查 A。不要据此声称当前环境需要安装，也不要把安装失败算作逻辑修复失败。 |
| 外部服务、网络、GPU、大型数据 | 单文件纯 Python 复现与上述源码调用链 | 环境只允许模型代理及声明内部服务；无公网假设 | 未见本题所需的此类资产 | 本题最小 CPU 复现/窄测试不需要这些服务。不建议联网下载或运行全仓测试来补静态证据。 |

**A：导入及代码来源检查（建议，未执行）。**

```bash
python -c 'import sys; import mypy.stubgen as s; import mypy.nodes as n; import mypy.visitor as v; import mypy_extensions; import typing_extensions; print(sys.version); print(sys.executable); print(s.__file__); print(n.__file__); print(v.__file__)'
```

此步骤须在真实工作区和指定 actor 身份下执行。若打印出编译扩展路径，应核对其与编辑源码的关系，而不是直接声称源码修复无效。

**B：原复现及解析路径（建议，未执行）。**

```bash
audit_tmp="$(mktemp -d /tmp/mypy16869.XXXXXX)"
cat > "$audit_tmp/repro.py" <<'PY_REPRO'
from typing import Generic, TypeVarTuple

_Ts = TypeVarTuple("_Ts")

class ClassName(Generic[*_Ts]):
    pass
PY_REPRO
python -m mypy.stubgen "$audit_tmp/repro.py" -o "$audit_tmp/out-default"
python -m mypy.stubgen --no-analysis "$audit_tmp/repro.py" -o "$audit_tmp/out-parse"
cat "$audit_tmp/out-default/repro.pyi"
cat "$audit_tmp/out-parse/repro.pyi"
```

这里用模块入口绑定同一解释器；它对应 `setup.py` 中的 `stubgen=mypy.stubgen:main`。成功应不再出现该表达式引起的内部崩溃，并实际生成含 `ClassName` 和解包泛型基类的输出；不强求纯 Python 与编译版失败文本相同。默认输出中 `_Ts` 声明的处理需按第 3 节另行审视。最小补充是用 `Ts` 的公开名称版本、`--include-private` 版本及 `Generic[T, *Ts]` 检查名称无关性和参数顺序；导入别名或 `typing_extensions.TypeVarTuple` 版本是合理低成本回归建议，未声称这些均为明示验收要求。

**C：既有公开回归（建议，未执行）。**

```bash
python -m pytest -n0 mypy/test/teststubgen.py -k 'GenericClass or TypeVar or PrivateVar or AliasPullsImport'
```

此选择覆盖已见到的普通泛型、类型变量声明、导入别名、私有变量过滤及导入依赖。若修改共享表达式打印逻辑，建议再运行整个 Python stubgen 数据套件（建议，未执行）：

```bash
python -m pytest -n0 mypy/test/teststubgen.py::StubgenPythonSuite
```

此套件会根据 case 后缀使用解析、语义分析或运行时导入；其模式不同于所有用例均运行原 CLI 默认路径（`base/mypy/test/teststubgen.py:700–713`）。尚未确认上述 selector 在真实安装环境的收集结果。项目文档认可窄测试，命令模式依据 `base/CONTRIBUTING.md:65–84` 与 `base/test-data/unit/README.md:48`。

## 5. 阅读、未查及暴露范围

实际阅读的范围：

- 协调者指定的角色卡 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/roles/public_reader.md`；没有打开它的父目录或邻接调查资料。
- 本题 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md` 全文。JSON 以原始文本阅读，未把字段当作本次执行授权。
- `base/mypy/stubgen.py` 的相关导入、Options、AliasPrinter、类基类/声明/别名/导入处理、源码目标收集、AST 构建、生成入口及 CLI 区段，重点行号为 `55–340,695–809,813–875,883–908,960–1085,1115–1150,1380–1485,1535–1700,1715–1768,1805–1869`；另对该文件进行了相关关键词检索。
- `base/mypy/visitor.py:1–58,347–390,470–490`；`base/mypy/nodes.py:1720–1750,2248–2280`；`base/mypy/fastparse.py:122–146,205–251,1520–1543,1600–1640,2040–2055`，以及这些文件中的相关关键词命中行。
- `base/mypy/stubutil.py:193–295,510–605,743–790`；`base/mypy/stubgenc.py` 仅相关关键词搜索，无相关正文展开；在 `base/mypy/**/*.py` 内检索 `AliasPrinter` 引用，返回的调用点全部位于 `stubgen.py`。
- `base/mypy/test/teststubgen.py`：一次全文显示被工具截断，随后明确阅读 `655–780`，并检索相关入口；只依据实际可见文本，不声称全文已读。文件顶部导入与部分命令行测试、尾部其他测试也在首次输出中可见。
- `base/test-data/unit/stubgen.test`：全文件相关关键词/用例名检索，明确展开 `269–314,1155–1214,1334–1507,3698–3723`；未见星号 TypeVarTuple 基类的既有专用 stubgen 用例。`base/test-data/unit/check-typevar-tuple.test` 仅关键词命中与 `97–120`；未全读该类型检查套件。`base/mypy/typeshed/stdlib/typing.pyi` 仅关键词命中与 `105–121,202–246`。
- `base/docs/source/stubgen.rst` 全文；`base/README.md:1–190`；`base/CONTRIBUTING.md` 全文；`base/test-data/unit/README.md:1–95`；`base/mypy-requirements.txt`、`base/test-requirements.txt`、`base/build-requirements.txt` 全文；`base/pyproject.toml:1–25,89–125` 及相关检索；`base/setup.py:31–60,73–102,175–239` 及相关检索；`base/tox.ini`、`base/runtests.py` 仅 pytest 等关键词命中。
- `base/conftest.py`、`base/mypy/test/config.py` 全文；`base/mypy/test/data.py:1–82`；`base/mypy/test/helpers.py:1–78`。在本题 `base/` 内用 `rg --files` 发现相关源/测试/安装文档文件名，部分未打开的 README 等只有路径可见；`.gitmodules` 路径搜索未返回结果，未据此断言真实镜像不存在额外资产。

未查：任何 private、gold、未来代码/历史、共享镜像克隆、质量报告、批次聚合/manifest/inventory、其他题、隐藏测试、外部链接、网络页面、实际容器与 actor 环境。未执行 Git 历史命令、项目 import、复现、测试、构建、安装、下载、容器、SSH、GPU/模型请求或 quota/reset；未修改源码、测试、评分材料或旧批次，未提交。唯一写入为本报告。

`user_prompt.txt` 只是按当前模板静态渲染的文本；`environment_brief.md:3–6` 明示它不是实际模型消息捕获，`base/` 也只是固定 base 的跟踪文件导出，不是完整运行容器。本报告不证明真实消息/工具配置、运行资源、conda 激活或开发条件已通过。没有读取到本题私有材料的事件；这是协作范围声明，不是文件权限隔离或预训练无污染证明。报告保存后不回写。
