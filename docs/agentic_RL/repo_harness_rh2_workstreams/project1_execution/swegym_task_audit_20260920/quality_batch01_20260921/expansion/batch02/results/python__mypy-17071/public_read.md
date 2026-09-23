# python__mypy-17071 公开阅读记录

本记录仅根据角色卡与本题公开包作静态判断。公开包根为 `runs/swegym_quality_batch02_20260921_v2/public/python__mypy-17071/`；下文文件行号均相对此目录。指定基线为 `4310586460e0af07fa8994a0b4f03cb323e352f0`（`public_bundle.json:1`、`base_identity.json:3`）。没有运行项目代码、测试、安装、容器、网络请求或模型，没有修改 `base/`。

公开材料足以定位一个具体而可调查的遗漏：检查返回 `TypeVar` 是否出现在参数中的收集器，没有遍历 `CallableType.type_guard`。这是静态调用链支持的根因判断，尚非执行复现结果。修复不需要已知的外部服务或额外问题背景；真实开发环境是否可用仍待 actor 验证。

## 1. 需求表

| 行为 | 强度与公开依据 | 合理边界 |
|---|---|---|
| `type_guard(x: Any, type_check_func: Callable[[Any], TypeGuard[T]]) -> T` 及其接收 `is_string` 的调用不应产生题面中的 `[type-var]` 错误。 | 明示：`user_prompt.txt:3-29`；同一内容在 `37-63` 重复。 | 示例要补导入、`T = TypeVar("T")` 并修正缩进；不能把原样粘贴产生的语法或名称错误当作目标 bug。 |
| 参数中回调的 `TypeGuard[T]` 应算作包含外层返回变量 `T`。 | 由题面与代码合理推知：`base/mypy/checker.py:1422-1430` 对所有参数收集变量；`base/mypy/types.py:1802` 说明 guard 目标另存字段。 | 这是检查器对类型结构的识别问题，不是要求用户改变函数签名、加 `cast` 或关闭错误码。 |
| 调用的结果应保留泛型推断能力；示例的 `val` 应推断为 `str`。 | 合理推知、非题面逐字规定：`base/mypy/constraints.py:1020-1037` 已从 guard 目标推导约束；`base/test-data/unit/check-typeguard.test:115-125,493-508,687-696` 已约定高阶回调、泛型与别名推断。 | “Should not error” 不应靠丢弃泛型或退化为 `Any` 达成。精确 `reveal_type` 文案是旧测试约定，不是题面新增输出格式。 |
| 真正无参数约束的返回 `TypeVar` 仍应报错，包括有上界或取值约束的变量。 | 旧接口/测试必须保留：`base/test-data/unit/check-typevar-unbound.test:1-19`、`base/test-data/unit/check-generics.test:1593-1601`；错误码见 `base/test-data/unit/check-errorcodes.test:256-263`。 | 不能全局取消 `check_unbound_return_typevar` 或忽略 `[type-var]`。上界提示等无关诊断也应保留。 |
| 普通 `Callable[..., T]`、容器中的回调、外层作用域已绑定的变量等既有合法签名继续成立。 | 旧测试：`base/test-data/unit/check-typevar-unbound.test:21-65`。 | 遍历新增字段时保留既有参数、返回值及嵌套类型处理，不把其它类型变量误当作同一个 `T`。 |
| `TypeGuard` 回调与普通 `bool` 回调的兼容关系，以及收窄行为继续成立。 | 旧测试：`base/test-data/unit/check-typeguard.test:1-10,57-76,461-508`；文档 `base/docs/source/type_narrowing.rst:215-274`。 | `TypeGuard[T]` 在内部的普通返回类型仍是 `bool`；不能用破坏该表示的方式消除报错。普通 `bool` 回调不能因此被接受为任意 `TypeGuard[T]`。 |
| 是否同时修复相同形式的 `TypeIs[T]`，以及是否扩大至所有类型查询/转换器。 | 有多种合理范围：题面只提 `TypeGuard`；但 `base/mypy/types.py:1802-1803`、`base/mypy/typeanal.py:1004-1005,1060-1061` 已有并行的 `TypeIs` 表示和 `base/test-data/unit/check-typeis.test:124-134,496-511,707-717`。 | 同时处理 `TypeIs` 有明确仓库依据；不能把所有 visitor 的全面改造当作题面唯一要求。改动公共遍历器时，应检验 `TypeIs` 的一致性并保留旧行为。 |

题面中的函数名、变量名、字符串内容和 `"failed type assetion"` 拼写只是复现样例，不构成必须新增的公共 API、报错或命名约定。

## 2. 合理实现范围

静态入口与调用链如下：

1. `base/mypy/message_registry.py:193-196` 定义了与题面一致的错误文本；`base/mypy/checker.py:1156-1168` 对直接返回类型变量的函数触发检查。
2. `base/mypy/checker.py:1422-1430` 遍历参数类型，再判断返回变量是否被收集；`CollectArgTypeVarTypes` 只重写了 `visit_type_var`（`7389-7396`），继承其它遍历行为。
3. `base/mypy/typetraverser.py:83-87` 访问 `arg_types`、`ret_type`、`fallback`，没有访问 `type_guard` 或 `type_is`。而 `base/mypy/types.py:1802-1803` 明说这两个目标单独保存，`ret_type` 是 `bool`；`base/mypy/typeanal.py:996-1064` 负责建立这些字段。
4. 因而当回调参数中的 `T` 只在 guard 目标出现时，现有参数收集路径会遗漏它。普通回调返回 `T` 能经 `ret_type` 到达；别名参数可经 `base/mypy/typetraverser.py:129-133` 到达，这也解释了为什么邻近旧测试不能替代直接形式的复现。

至少有两种可合理接受的实现路线，不能仅按修改文件或实现形状区分好坏：

- 在参数类型变量收集器中补足对回调 guard 目标的递归访问。优点是直接对应本检查，影响范围较小；必须覆盖合法嵌套，而非只对题面的一层参数或名称特殊放行。
- 完善公共 `TypeTraverserVisitor` 对 `CallableType` 组件的遍历，使该收集器自然得到目标变量。该类自述遍历全部类型组件（`base/mypy/typetraverser.py:40-41`），因此有设计依据；但也影响 `FreezeTypeVarsVisitor`（`base/mypy/checkmember.py:847-855`）、变量 namespace 设置（`base/mypy/tvar_scope.py:21-37`）、实例收集与错误显示（`base/mypy/messages.py:2680-2715`）、位置设置（`base/mypy/types.py:3486-3495`）及混合语法/类型遍历（`base/mypy/mixedtraverser.py:25-38`）。这些是审查影响面的理由，不是题面缺陷。

`TypeQuery`、`BoolTypeQuery` 也有自己的 callable 访问方法（`base/mypy/type_visitor.py:368-370,502-510`），但它们不是此报错的直接收集器；仅看到相似代码，不足以要求本次一并改完。泛型约束与替换已有专门 guard 处理（`base/mypy/constraints.py:1020-1037`、`base/mypy/expandtype.py:384-388`），因此也不能预设必须重写推断系统。

这些是可接受的实现范围分析，没有编写修复，也没有观察任何候选实现的运行结果。

## 3. 初态线索与疑义

| 事项 | 静态判断及实际影响 |
|---|---|
| 复现片段不完整 | `user_prompt.txt:10-21` 缺少 `Any`、`Callable`、`TypeGuard`、`TypeVar` 的导入与 `T` 定义，`return x` 缩进不一致。按 `base/docs/source/type_narrowing.rst:262-267` 与旧测试的惯用写法补齐即可。修正为 `if not ...: raise ...` 后在函数体返回 `x`，保留原语义。无需请求更多 issue 内容。 |
| 同一 issue 出现两遍 | `user_prompt.txt:3-34` 与 `37-68` 没有额外不同要求。重复是输入呈现现象，不需要双份修复。 |
| 报告版本与基线不同层次 | 用户报告 mypy 1.4.1（`user_prompt.txt:34,68`），任务要求修改指定 commit（`user_prompt.txt:1`）。应在指定基线调查，不应另装 1.4.1 替代基线。源码已经包含 `TypeIs`，不把它误作用户明示诉求。 |
| 旧测试不能直接当完整独立程序 | 数据测试使用简化 builtins（`base/test-data/unit/README.md:54-73`）。例如 `testGenericAliasWithTypeGuard` 依赖 `fixtures/list.pyi`，该 fixture 在 `base/test-data/unit/fixtures/list.pyi:5` 定义 `T`；不能因测试正文未重定义 `T` 就认定公开测试损坏，也不能省略实际复现中的 `T` 定义。 |
| 公开材料和运行环境的界限 | `base_identity.json:8-12` 声明无 symlink、未物化 LFS、gitlink，且没有 Git 元数据；本包中相关源码、stub 和测试文件可读。没有据此验证真实镜像里的包、二进制、权限或剩余容量。 |
| 外部资料/祖先历史 | 已读文档有外链，但核心语义、复现及测试入口均有本地材料；目前没有必须补入的外部附件或祖先提交。未访问外链、历史或共享镜像。 |

共享输入中的三类信息应分开：

- **Issue 需求**：消除所示合法签名上的错误，来源为 `user_prompt.txt` 的问题正文。
- **Harness 操作指令**：`public_bundle.json:1` 的 `public_hints` 要求探索根因、只改 NON-TEST 源码、不改测试、窄范围运行验证并简短结束。这些不是 Python 类型语义。若实际求解继续适用“不改测试”，上述两条源码修复路线均仍成立，可以用 `mypy -c` 和已有测试验证；若不适用，可正常加入回归测试，需以实际共享指令为准。未自行豁免原指令。
- **待验环境/机制声明**：同字段声称 conda `testbed` 已激活、工具位于 `/testbed`，以及“所有测试修改会恢复、永不计分”。前两项需要真实 actor 验证；后一项不能按当前事实引用。`environment_brief.md:18-26` 说明当前没有按测试文件名统一排除，仍有官方文件恢复等具体限制，具体适用范围由协调者核实。这里不从私有材料确认文件名单。字段未渲染进 `user_prompt.txt` 不代表 actor 看不到；公开 bundle 会写入容器公开路径（同文档 `25-26`）。

没有发现会让合理修复必然依赖修改测试文件的情况；“禁止改测试”限制回归测试提交方式，但从公开证据看不会阻断上述源码修复路线。实际指令投递方式仍是共享输入问题。

## 4. 开发需求与建议命令

下表及其后所有命令均为**建议，未执行**，目标是后续真实 actor 在 `/testbed` 运行。它们不是本次已验收环境的证据。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口与最小命令/预计现象 |
|---|---|---|---|
| Python 解释器、基线源码与运行依赖 | `base/setup.py:11-13` 要求 Python ≥3.8；`base/mypy-requirements.txt:2-4` 列出 `typing_extensions`、`mypy_extensions`、低版本 Python 的 `tomli`。 | `public_hints` 声称已激活 conda；`environment_brief.md:9-13` 明确需 actor 检查。 | 用下方 A 确认可导入、解释器路径、包来源及版本。成功应无 import 异常，源码来源应对应求解 checkout；conda 环境变量只是辅助信号。编译产物是否遮蔽源码尚未检查。 |
| 复现问题及独立负例 | `user_prompt.txt:10-29`；`base/test-data/unit/README.md:137-154` 说明模块与字符串输入用法。 | 有 bash/edit 和 `/testbed` 的计划性说明，无实测。 | 下方 B 应在原态出现目标 `[type-var]`，修复后无 error，并保留 `val: str` 的推断；下方 C 仍应报告 `[type-var]`。完整输出与退出码均待验证。 |
| 相关数据测试、pytest 及插件 | `base/CONTRIBUTING.md:65-77`；`base/pyproject.toml:90-111` 有 pytest 自定义收集与默认 `-nauto`；`base/test-requirements.txt:55-63` 列出 pytest、cov、xdist。 | 只知资源计划为 2 CPU/4 GiB/PID512，实际未验。 | 下方 D 单文件逐次运行，使用 `-n0` 限制并行；预期既有测试保持通过，但本次没有建立基线通过事实。配置保留 `-n` 时仍需 xdist 插件。 |
| 类型 stub 与 fixture | `base/test-data/unit/README.md:54-73`；`base/test-data/unit/lib-stub/typing_extensions.pyi:36-37` 同时定义 `TypeGuard`、`TypeIs`；相关 `fixtures/tuple.pyi`、`fixtures/list.pyi` 已读。普通 CLI 使用的 typeshed 文件亦在包中。 | `base/` 提供静态源码资产，真实镜像中的读取未验。 | 不需要为这组静态输入执行用户示例或联网查标准。`TypeIs` 测试输入能否被静态识别，不能只据运行包版本推断；测试使用所带 stub。 |
| 可写临时目录及测试工作目录 | `base/mypy/test/data.py:334-360` 使用 `TemporaryDirectory`、写入测试输入；`base/mypy/test/config.py:16-19` 指明子目录 `tmp`；`base/mypy/test/testcheck.py:127-151` 配置 fixture 和缓存。 | `environment_brief.md:9-12` 声称 workspace/home 可写，tmp1 GiB/home256 MiB 未实测。 | 需要 actor 验证临时文件创建和容量；导入成功不等于测试可运行。单进程窄测试是合适起点，不推定全仓可运行。 |
| 安装或构建（只有缺依赖时才需要） | `base/CONTRIBUTING.md:39-49` 给出 test requirements 与 editable 安装；`base/setup.py:88-96` 默认不启用 mypyc 编译；`base/pyproject.toml:1-16` 列构建依赖。 | 不保证解释器目录可写，也不假定公网下载（`environment_brief.md:9-10`）。 | 下方 E 仅适用于已有依赖或获准内部离线资产。若依赖缺失，应补齐允许来源的依赖/轮子与权限，不能假定 pip 可联网成功；本任务不要求 GPU、云服务或 C 编译。 |

**A — 建议，未执行：解释器与最小依赖/CLI 检查。**

```bash
cd /testbed
python -c 'import os, sys, mypy, typing_extensions, mypy_extensions, pytest, xdist; print(sys.executable); print(sys.version); print(mypy.__file__); print(os.environ.get("CONDA_DEFAULT_ENV"))'
python -m mypy --version
```

**B — 建议，未执行：最小补全后的问题复现，不修改仓库测试。**

```bash
cd /testbed
python -m mypy --no-incremental --cache-dir=/dev/null --show-error-codes -c 'from typing import Any, Callable, TypeVar
from typing_extensions import TypeGuard

T = TypeVar("T")

def type_guard(x: Any, type_check_func: Callable[[Any], TypeGuard[T]]) -> T:
    if not type_check_func(x):
        raise TypeError("failed type assetion")
    return x

def is_string(x: Any) -> TypeGuard[str]:
    return isinstance(x, str)

data = "helloworld"
val = type_guard(data, is_string)
reveal_type(val)
'
```

原态预期复现所示返回类型变量错误；具体附带诊断待实测。修复后预期零 error；`reveal_type` 的 `str` note 是附加的推断观测，不是题面要求新增的报错。使用 `typing_extensions.TypeGuard` 避免把 Python 3.8/3.9 的导入差异混入核心问题。

**C — 建议，未执行：防止错误地关闭原检查。**

```bash
cd /testbed
python -m mypy --no-incremental --cache-dir=/dev/null --show-error-codes -c 'from typing import TypeVar
T = TypeVar("T")
def unbound() -> T:
    raise RuntimeError
'
```

原态和正确修复后均应报告题面相同的 `[type-var]` 诊断；非零退出在这个负例中是预期结果。

**D — 建议，未执行：逐个运行公开旧测试文件。**

```bash
cd /testbed
python -m pytest -n0 -q mypy/test/testcheck.py::TypeCheckSuite::check-typeguard.test
python -m pytest -n0 -q mypy/test/testcheck.py::TypeCheckSuite::check-typevar-unbound.test
python -m pytest -n0 -q mypy/test/testcheck.py::TypeCheckSuite::check-typeis.test
```

前两项直接检查问题所在功能及原有拒绝规则；第三项适合公共 visitor 或双字段改动后的相邻回归验证。若只需更短首轮，建议、未执行：`python -m pytest -n0 -q mypy/test/testcheck.py -k 'testTypeGuardHigherOrder or testTypeGuardAsGenericFunctionArg or testNestedBoundTypeVar'`。旧测试可能在原 bug 尚存时通过，因此不能仅靠它们证明目标修复，B 仍有必要。没有要求一次运行全仓。

**E — 建议，未执行：有内部离线依赖条件时的可选准备。**

```bash
cd /testbed
python -m pip install --no-index -r test-requirements.txt
MYPY_USE_MYPYC=0 python -m pip install --no-index --no-build-isolation -e .
```

这是仓库安装步骤的离线形式，要求依赖已经安装或配置了可用的内部 wheel 来源；若没有，预期会因找不到依赖而失败，不代表源码问题不可修。`--no-build-isolation` 还要求当前环境已有 `pyproject.toml:1-16` 中的构建依赖。现有解释型 checkout 可以先按文档直接用 `python -m mypy`；不把重装、编译或访问公网列为本题必需步骤。

## 5. 实际阅读与暴露记录

阅读顺序为角色卡 → 三份指定公开输入 → 本题目录元数据/文件名与文本搜索 → 定位源码、调用者、旧测试及开发说明。实际使用工具仅为静态 `cat`、`nl`/`sed`、`rg`/`rg --files`、`head`、确认输出文件存在/大小的 `stat` 与写入本报告的文件编辑；没有调用 Python、mypy、pytest、pip、git、容器或网络工具。表中的建议命令只是本报告文本。

实际打开的范围如下；行号为主要已确认摘录。早期批量输出发生过显示截断，关键结论对应段落已用较小摘录重读；未将被截断部分声称为完整读完。

| 文件 | 实际阅读范围/用途 |
|---|---|
| 指定 `roles/public_reader.md` | 全文；唯一读取的题包外说明文件。 |
| `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json` | 全文；题面、可见旧提示、静态环境限制与导出元数据。 |
| `base/README.md`、`base/CONTRIBUTING.md` | README 1-190；CONTRIBUTING 全文（1-202）；安装/命令与开发约定，未访问其中外链。 |
| `base/test-data/unit/README.md` | 曾请求 1-240，确认重读 1-160；数据测试语法、fixtures、窄测试与 CLI。 |
| `base/pyproject.toml`、`base/setup.py`、`base/tox.ini` | 曾请求至 260/180/200；关键重读分别 1-133、1-125、1-85（文件不足时读至结尾）。pytest 配置、Python 最低版本、构建开关。 |
| `base/mypy-requirements.txt`、`base/test-requirements.txt`、`base/build-requirements.txt` | 全文；依赖声明。未打开 `test-requirements.in`，只看过其路径。 |
| `base/mypy/checker.py` | 1128-1182、1410-1450、5705-5770、7380-7425、7790-7835；诊断入口、参数收集器、guard 收窄及相关变量处理。 |
| `base/mypy/typetraverser.py` | 全文 1-142；直接遍历路径。 |
| `base/mypy/types.py` | 1780-1845、1860-1935（大块部分显示截断，关键 1795-1838、1870-1887 重读）、3480-3525；其它 guard 行号经 rg 搜索。 |
| `base/mypy/typeanal.py` | 990-1108 摘录，关键 996-1098 重读；函数类型语义分析。 |
| `base/mypy/typeops.py`、`base/mypy/type_visitor.py` | typeops 905-1010；type_visitor 曾请求 190-275、290-430、450-535，重点重读 350-408、480-527；确认另一套查询接口不是直接收集器。 |
| `base/mypy/message_registry.py` | 错误文本搜索及 187-201。 |
| `base/mypy/checkmember.py`、`base/mypy/tvar_scope.py`、`base/mypy/messages.py`、`base/mypy/mixedtraverser.py` | 分别 840-888、1-72、2680-2720、全文 1-112；公共遍历器调用者。 |
| `base/mypy/constraints.py`、`base/mypy/expandtype.py` | guard 搜索及 1005-1055、370-397；约束与类型替换。 |
| `base/docs/source/type_narrowing.rst` | guard 相关匹配及 187-295；公开类型收窄说明。 |
| `base/test-data/unit/check-typeguard.test` | case/关键词索引及 1-127、461-531、680-711；旧行为与泛型/别名。 |
| `base/test-data/unit/check-typeis.test` | case/关键词索引及 124-136、479-513、707-718；相邻功能约定。 |
| `base/test-data/unit/check-typevar-unbound.test`、`check-generics.test`、`check-errorcodes.test` | 前者全文 1-71；后两者分别 1570-1680、250-267。 |
| `base/mypy/test/testcheck.py`、`base/mypy/test/config.py`、`base/conftest.py`、`base/mypy/test/data.py` | testcheck 1-170 及匹配行；config/conftest 全文；data 的 import/临时目录搜索及 303-368。 |
| `base/test-data/unit/lib-stub/typing_extensions.pyi`、`lib-stub/builtins.pyi`、`fixtures/list.pyi`、`fixtures/tuple.pyi` | 分别 1-45、1-35、全文 1-41、1-40；确认本地 stub 与 fixture 语义。 |

仅搜索命中、未连续阅读的额外文件包括 `base/mypy/semanal.py`、`base/mypy/test/testtypes.py`、`base/mypy/typeshed/stdlib/typing_extensions.pyi`、`base/mypy/typeshed/stdlib/typing.pyi`，以及错误文本搜索命中的 `check-selftype.test`、`check-classes.test`、`check-parameter-specification.test`、`check-inference.test`、`check-unreachable-code.test`。还查看过本题 `base/` 中 README/requirements/config 的匹配文件名；未据此声称阅读它们内容。搜索遍历范围始终在本题公开 `base/` 内。

未查项：真实 Claude Code 消息、harness 执行过程、容器配置与实际 actor 权限/资源、环境中的编译模块和依赖版本、完整旧测试执行、全仓调用图、私有验收材料、gold、其他题、历史、批次 manifest/结论、任何其他角色产物。未发现误读私有材料。这里的范围遵守是协作记录，不是文件权限隔离或预训练无污染证明。`user_prompt.txt` 只作静态渲染读取，`base/` 不是完整可运行容器。

关键待核实事项仅保留为：真实 actor 能否加载并执行目标 checkout 与窄测试；临时目录/依赖是否齐全；原 public_hints 在实际求解中的投递及“不改测试”指令适用范围；`TypeIs` 同类行为是否纳入该次实现范围。未给题目作通过或淘汰判定。
