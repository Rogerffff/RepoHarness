# pandas-dev__pandas-53958 公开视角阅读

本报告只依据指定角色卡和本题公开包。除角色卡外，下文路径均相对于 `runs/swegym_quality_batch02_20260921_v2/public/pandas-dev__pandas-53958/`。仅静态阅读，未运行项目代码、导入、测试、构建或安装；未修改 `base/`，未联网、读取历史或访问共享镜像。

公开材料足以定位问题和开始实现：现有两个类型均已定义，差异在导出位置。但题面同时提出向 `pandas._libs` 增加 `NAType`、或向 `pandas.api.typing` 增加两个类型，没有给出最终选择。另一项实质约束是旧 API 测试精确限定 `pandas.api.typing` 的名称，正常新增导出会要求同步更新这份名单，而旧 harness 提示禁止改测试。

## 1. 需求表

| 行为/要求 | 依据与性质 | 公开可确定的边界 |
| --- | --- | --- |
| 为应用类型注解提供一致的 `NaTType`、`NAType` 导入入口 | 明示：`user_prompt.txt:3-14`，`public_bundle.json:1` 的 `problem_statement` | 问题是类型所在命名空间不一致，不是缺失值计算错误。 |
| 目标入口可能是 `pandas._libs` | 明示的候选：`user_prompt.txt:6-10`；现有 `base/pandas/_libs/__init__.py:1-27` 已导出 `NaTType`，没有导出 `NAType` | 新增 `NAType` 至该包是题面直接支持的一个答案，不能仅凭题面排除。 |
| 目标入口也可能是 `pandas.api.typing` | 明示的另一候选：`user_prompt.txt:14`；`base/doc/source/reference/index.rst:21-25` 把该包定义为类型注解所需类的公共入口 | 当前该包已有中间结果类型，但没有这两个名称，见 `base/pandas/api/typing/__init__.py:1-50`。公开材料未把此候选升级为唯一必选。 |
| 导出应指向现有类型，保留名称 `NaTType`、`NAType` | 由公开代码合理推知：`base/pandas/_libs/missing.pyi:4-7`；`base/pandas/_libs/tslibs/nattype.pyi:11-20`；实例初始化见 `missing.pyx:543-544`、`tslibs/nattype.pyx:1417-1418` | 应能用导出的类表示 `pd.NA`、`pd.NaT` 的真实类型。新建同名但无关的类，或用值对象替代类型，不能满足目的。 |
| 已有导入及缺失值行为应继续工作 | 合理兼容性推断，并非题面给私有包作出的稳定性承诺：`user_prompt.txt:4-8` 给出原有效导入；`base/pandas/_typing.py:31-43` 使用 `_libs.NaTType`；`base/pandas/core/dtypes/cast.py:24-28,173` 使用 `missing.NAType` | 题面没有要求迁移、删除旧入口或更改单例/运算语义。保留原入口是合理最小范围。`test_na_scalar.py:19-22,41-48` 与 `test_nat.py:96-101` 是已有行为的公开约束。 |
| 选定命名空间后遵循其导出约定 | 由仓库推知：两个包均有 `__all__`（`base/pandas/_libs/__init__.py:1-10`、`base/pandas/api/typing/__init__.py:31-50`）；`base/pandas/tests/api/test_api.py:18-30,254-271,342-343` 检查 typing 命名空间的精确名称集合 | 普通显式导入和对外列出的名称应一致。没有要求新函数、参数、默认值、消息文本或 CLI 输出。 |
| 文档、外部 stubs 和具体 checker 的要求 | 仍有多种合理解释：题面说这两种类型未文档化，并提及 `pandas-stubs`，但未指定版本、checker、检查命令或新文档页面（`user_prompt.txt:12-14`） | 补充新公开入口的说明合理；强制某段文案、强制修改外部 `pandas-stubs` 仓库或通过特定 checker，均不能从现有题面推出。 |

## 2. 合理实现范围

至少有两种不同的正常实现应被公开需求容纳，前提是没有另行提供公开的设计定论：

1. 在已有 `pandas._libs.NaTType` 旁提供同一 `NAType` 的导出，使 `from pandas._libs import NaTType, NAType` 成为共同入口。
2. 在 `pandas.api.typing` 提供现有两个类的导出，作为面向用户类型注解的公共入口，保留既有内部入口。

同时提供两个入口也符合问题目的，但范围更大；公开材料没有要求它。现有代码采用直接导入再列入 `__all__` 的方式；导入来源是定义模块还是已有中间导出模块，不应成为额外验收标准，只要类型对象相同、正常导入无循环、对外名称正确。题面没有要求移动 Cython 类型定义、重写构造/运算、把类改名或将全部内部调用改为新的公共路径。

`pandas.api.typing` 的文档目前强调“作为中间结果出现、不应由用户直接实例化”的类（`base/doc/source/reference/index.rst:21-25`，模块说明见 `base/pandas/api/typing/__init__.py:1-3`）。若选择增加缺失值类型，可合理调整该说明，但这个现状不能消除题面明确提出的另一候选。没有读取或推测标准修复。

## 3. 初态线索与疑义

**可调查、可复现的入口充分。** 题面有两个有效导入和明确基线提交（`user_prompt.txt:1,6-7`），对应源码在包中；`NaTType` 从 `tslibs.nattype` 经 `tslibs` 转导出至 `_libs`（`base/pandas/_libs/tslibs/__init__.py:48-53`、`base/pandas/_libs/__init__.py:19-27`），`NAType` 在 `missing` 中定义（`base/pandas/_libs/missing.pyx:366-407`）。无需业务数据、外部附件或应用样例即可检验候选入口的缺失。

**真正影响验收边界的未知是目标入口。** 题面以 “Should …” 和 “Another option …” 保留讨论语气，未包含被点名维护者的答复（`user_prompt.txt:10-14`）。这不阻止开发者选择合理实现，却不能支持仅接受一个入口的唯一解释。若必须限定入口，需补充当时公开的设计决定或直接给出明确要求；本角色未搜索讨论、PR 或后续修复。

**旧测试与指令的相互作用需要单独核对。** `TestApi.test_api_typing` 使用 `dir()` 得到实际名称，并与不含两个类型的 `allowed_typing` 精确比较（`base/pandas/tests/api/test_api.py:18-30,254-271,342-343`）。因此，普通新增两个 typing 导出的实现，在旧测试不变时预计使该测试失败；这不是依赖问题，也不能用它反推“题面只允许 `_libs` 方案”。本次对 `base/pandas/tests/api/` 的定向搜索未发现同类 `_libs` 子命名空间名单约束，但未据此宣称全仓不存在约束。

| 信息类别 | 公开内容 | 本报告如何处理 |
| --- | --- | --- |
| issue 目标 | 统一类型导入位置及两种候选，见 `user_prompt.txt:3-14` | 与 harness 指令分开解释。 |
| harness 操作指令 | `public_bundle.json:1` 的 `public_hints` 要求修改非测试源码、禁止修改测试、窄范围验证 | 不自行撤销。若该禁令适用，普通 typing 方案无法通过“编辑旧名单”的正常方式同步公开测试；应记录这个冲突，由协调者核对实际输入及官方文件恢复范围。若禁令不适用，同步名单和加入针对新导出的回归验证属于合理开发工作。 |
| 旧机制说明 | 同一字段称所有测试修改都会恢复、永不计分 | 不是已经核实的当前事实。`environment_brief.md:18-26` 明确说当前没有按测试文件名统一排除，仍存在官方文件恢复等具体限制；本题涉及哪些文件未知。不能直接判题目无效，也不建议靠隐藏 `dir()` 名称等方式迎合旧名单。 |
| 待验环境声明 | `/testbed`、预激活 `testbed` conda、工具 `bash/edit`、python/pip 已指向环境，见 `public_bundle.json:1` | 仅为可见字段声明。未核验实际消息、解释器、权限、构建产物、依赖与测试可运行性。bundle 会写入公开工作区；没出现在渲染题面不等于不可读（`environment_brief.md:3-12,25-26`）。 |

导入顺序、调用者、已有测试和构建方式都可通过正常读代码解决，不构成缺题面。`pandas-stubs` 的精确版本及内容没有随本题提供；它是说明需求动机的外部项目，而不是完成基本导出和类型身份验证的必要资产。若验收额外要求端到端类型检查，才需要补充 checker/stubs 版本与预期诊断。此任务没有发现必须依赖祖先历史或子模块内容的需求。

## 4. 开发需求表与最小命令

以下命令**全部为建议，未执行**，应在真实 actor 身份、真实 `/testbed` 中运行，不应把静态 `base/` 当作完整可运行容器。成功/失败现象均为源码推断。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口与最小命令（建议，未执行） | 预计现象 |
| --- | --- | --- | --- | --- |
| 确认解释器及基线 pandas 可导入 | `base/pyproject.toml:26-32` 要求 Python ≥3.9、NumPy/dateutil/pytz/tzdata；`base/pandas/__init__.py:5-32` 检查依赖及 C 扩展 | `environment_brief.md:8-12` 给预定工具、身份、资源和待核验范围；没有 actor 运行证据 | 建议，未执行：`python -c 'import sys, pandas as pd; print(sys.executable); print(pd.__file__); print(pd.__version__)'` | 应导入目标工作区所构建的 pandas。缺依赖或扩展未构建属于环境失败，不能当作本题 API bug。 |
| 确认原有两个入口及类型身份 | `user_prompt.txt:6-7`；`base/pandas/_libs/missing.pyx:543-544`；`base/pandas/_libs/tslibs/nattype.pyx:1417-1418` | 源码可见；已编译扩展和实际加载来源未提供 | 建议，未执行：`python -c 'import pandas as pd; from pandas._libs import NaTType; from pandas._libs.missing import NAType; assert NaTType is type(pd.NaT); assert NAType is type(pd.NA)'` | 基线和修复后均应成功；验证旧行为及类身份。 |
| 最小复现/验证候选共同入口 | `base/pandas/_libs/__init__.py:1-27`、`base/pandas/api/typing/__init__.py:1-50` 均缺所需新导出 | 只证明源码初态，不证明真实容器运行结果 | `_libs` 方案建议，未执行：`python -c 'import pandas as pd; from pandas._libs import NaTType, NAType; assert NaTType is type(pd.NaT); assert NAType is type(pd.NA)'`。typing 方案建议，未执行：`python -c 'import pandas as pd; from pandas.api.typing import NaTType, NAType; assert NaTType is type(pd.NaT); assert NAType is type(pd.NA)'` | 健康基线预计分别在缺失新名称处 `ImportError`；选定方案修复后对应命令应成功。这两条是候选分支，不把它们同时成功强加为题面要求。 |
| 运行窄范围公共 API 测试 | `base/pandas/tests/api/test_api.py:342-343`；运行方法见 `base/doc/source/development/contributing_codebase.rst:766-778` | 无测试执行证据；`base/pyproject.toml:59` 列测试依赖，`base/pandas/conftest.py:40-47` 无条件导入 Hypothesis/NumPy/pytest | 建议，未执行：`python -m pytest pandas/tests/api/test_api.py::TestApi::test_api_typing -q`；需要兼容的 pytest ≥7.3.2、Hypothesis 等，见 `base/pyproject.toml:59,454-457` | 健康基线预计通过；向 typing 普通新增名称而保持旧名单，预计出现名称集合不一致。需先解决测试修改指令的适用范围，不能保证“源码修复后旧测试仍通过”。 |
| 保留标量行为的最小回归 | `base/pandas/tests/scalar/test_na_scalar.py:19-22`、`base/pandas/tests/scalar/test_nat.py:96-101` | 源码和旧测试可见；依赖是否已装待验 | 建议，未执行：`python -m pytest pandas/tests/scalar/test_na_scalar.py::test_singleton -q`；建议，未执行：`python -m pytest pandas/tests/scalar/test_nat.py::test_identity -q` | 基线及导出修复后均应保持通过。无需运行全仓测试才能调查本题。 |
| 必要时构建/重建原生扩展 | `base/README.md:125-151`；`base/doc/source/development/contributing_environment.rst:9-10,207-229`；构建依赖见 `base/pyproject.toml:1-13` | 静态包不含真实镜像的构建事实；默认 2 CPU/4 GiB/PID512、tmp 1 GiB/home 256 MiB 也未在本题验证（`environment_brief.md:5-12`） | 仅在确需重建且依赖已供应时，建议，未执行：`python -m pip install -ve . --no-build-isolation --no-deps --no-index --config-settings editable-verbose=true`。需可用 C/C++ 编译器、Meson 1.0.1/meson-python 0.13.1、Cython ≥0.29.33 且 <3、NumPy 与其他声明的构建依赖，以及 actor 可写构建/安装路径 | 成功后能执行导入。依赖不齐、安装位置不可写或空间不足会阻塞运行验证；不假定能联网补装。若只是修改 Python 重导出且现有工作区构建健康，可不触发完整 Cython 重建；具体安装方式仍须检查。 |
| 外部服务、GPU、数据文件、端到端 checker | 问题只有类型导出；现有相关源码和所列窄测试均在本题公开包 | `environment_brief.md:10` 不承诺公网 | 基本开发不需要额外服务或数据；本表无下载命令。若另要求外部 `pandas-stubs`/mypy/pyright 联合检查，应先补齐版本与配置 | 没有公开证据表明本题需要 GPU、数据库或网络服务。不把全仓可选依赖、文档全量构建或外部 checker 设为最低复现条件。 |

## 5. 实际阅读范围及限制

实际全文读取了指定 `roles/public_reader.md`（未读其父目录）、`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base/README.md`、`base/pandas/_libs/__init__.py`、`base/pandas/_libs/tslibs/__init__.py`、`base/pandas/_libs/missing.pyi`、`base/pandas/api/__init__.py`、`base/pandas/api/typing/__init__.py`、`base/doc/source/reference/index.rst`、`base/doc/source/reference/general_functions.rst`。

按相关行段读取了：

- `base/pandas/_libs/missing.pyx:360-430,536-544`；`base/pandas/_libs/tslibs/nattype.pyx:350-405,1410-1424`；`base/pandas/_libs/tslibs/nattype.pyi:1-44`。
- `base/pandas/__init__.py:1-155`；`base/pandas/core/api.py:1-40`；`base/pandas/core/tools/timedeltas.py:1-29`；`base/pandas/core/dtypes/cast.py:12-35,165-188`；`base/pandas/_typing.py:23-49,370-383`。
- `base/pandas/tests/api/test_api.py:1-34,246-355`；`base/pandas/tests/scalar/test_na_scalar.py:1-150`；`base/pandas/tests/scalar/test_nat.py:1-112`；`base/pandas/conftest.py:1-130`。
- `base/pyproject.toml:1-64,454-513`；`base/environment.yml:1-28`；`base/requirements-dev.txt:1-24`；`base/doc/source/development/contributing_environment.rst:1-27,79-123,207-293`；`base/doc/source/development/contributing_codebase.rst:739-781`。

另做了包内文件名列举，以及围绕类型名称、API 导出和构建/测试依赖的定向 `rg` 搜索。搜索触及但未展开全文的包括相关 core 调用者、scalar 测试其他段落、`base/setup.py`、`base/doc/source/development/contributing.rst`、`base/doc/source/development/policies.rst` 及上述已读文件的其他匹配行。首次文件清单输出被截断；这不是对全仓内容的阅读。两个猜测文档路径 `base/doc/source/reference/general_utility_functions.rst`、`base/doc/source/reference/api.rst` 不存在，随后读取了实际 `general_functions.rst` 与 `index.rst`。

未读 `base_identity.json`、未逐文件 hash、未阅读全部仓库/测试或外部 `pandas-stubs`，未读其他题、私有包、gold、历史、manifest、汇总及其他角色产物。没有发现必须补取子模块或公开祖先历史的入口，因此未扩大范围。

`user_prompt.txt` 只是静态渲染；`base/` 是源码导出，不是已验证运行容器（`environment_brief.md:3-6`）。本报告不证明实际模型收到什么消息、拥有何种权限/资源、是否激活 conda、是否加载目标构建或能否执行测试。阅读边界是本次协作约定，不是文件权限隔离或预训练无污染证明。
