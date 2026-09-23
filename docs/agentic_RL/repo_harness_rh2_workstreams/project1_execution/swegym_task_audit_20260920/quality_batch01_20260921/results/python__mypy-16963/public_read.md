# python__mypy-16963 公开材料审查

本次仅静态读取指定角色卡和本题 `PUBLIC_DIR`，未运行项目代码、安装依赖、修改 `base/`、联网或读取私有材料。下列路径和行号均相对本题公开包。`user_prompt.txt` 是静态渲染文本；不能据此证明实际模型消息、工具权限或容器开发条件已经验证。

公开材料足以建立复现并定位调查入口。核心要求是使 TypedDict 类型对象能够通过 `type[D]` 和包含它的 `type[Union[...]]` 传递、赋值和调用，并保持返回类型信息。需要注意：issue 报告的是 mypy 0.910，而导出的基线版本标识为 1.10.0+dev；不能把题面中的五条旧报错当成当前基线已经实测的输出（`user_prompt.txt:111–136`；`base/mypy/version.py:7–18`）。

## 1. 需求表

| 行为/边界 | 公开依据 | 需求性质与合理解释 |
| --- | --- | --- |
| 空 TypedDict `D` 可传给 `f(d: type[D])`，且 `d()` 的结果可作为 `D` 返回 | `user_prompt.txt:8–20` | 明示。不能继续报不能实例化、同名类型不兼容或因该调用产生的 `Any` 返回错误。仅把返回值退化成 `Any` 不满足问题描述。 |
| `U = Union[int, D]` 时，`g(u: type[U])` 同时接受 `int`、`D`，且 `u()` 可返回 `U` | `user_prompt.txt:21–34` | 明示。需要保留普通类分支的已有支持，不能只接受 TypedDict 分支或跳过整个 Union 的检查。 |
| `Car` 接受 `Point` 和 `PointDict`；通过保存的类型对象用 `x=`、`y=` 构造，结果符合 `PointLike` | `user_prompt.txt:45–70`、`:103–107` | 明示。涉及函数实参检查、成员保存、间接关键字调用、返回类型四个可观察环节。 |
| `Truck._container: type[PointLike]` 能接收条件选择的两个类型对象，并正确调用 | `user_prompt.txt:87–100`、`:103–107` | 明示。修复范围包含带显式注解的条件表达式赋值，不能要求用户改写示例来规避问题。 |
| `Boat` 未显式注解的条件表达式也应在完整示例中不报错 | `user_prompt.txt:73–84`、`:105–107`；另见 `:120–128` | “No errors”字面上覆盖它。但作者又把替换成 NamedTuple 后的 `object` 返回问题称为可能的另一问题。应默认保留完整示例目标；若验收只要求 TypedDict 的传递/调用，需要明确说明是否允许剩余的通用条件表达式推断错误。不能静默删除 `Boat`。 |
| 直接调用 TypedDict 的合法构造方式及类型精度不退化 | `base/test-data/unit/check-typeddict.test:3–42`、`:89–98`；`base/docs/source/typed_dict.rst:66–77` | 由公开仓库合理推知的保留要求。关键字、单个字典字面量、`dict(...)`、空 TypedDict 无参数构造均有旧测试。返回值仍是具有相应字段类型的 TypedDict，运行时是普通字典。 |
| 必需键、未知键、字段值类型及非法参数形式仍检查 | `base/test-data/unit/check-typeddict.test:47–76`；`base/mypy/checkexpr.py:958–996` | 由公开测试/代码合理推知。不能用全局关闭参数、赋值或返回检查来达成“无错误”。新增的间接调用至少应遵守声明的字段签名；题面未规定新增非法用法的逐字诊断。 |
| 保留 `total=False` 的可缺省字段和结构兼容规则 | `base/test-data/unit/check-typeddict.test:1072–1095`、`:1108–1125`；`base/docs/source/typed_dict.rst:82–91`、`:123–151` | 已有直接构造和实例兼容行为有明确约定。将相同规则延伸至间接构造是合理预期；题面未单列间接 `total=False`、混合必需键、泛型/插件 TypedDict 等覆盖范围。 |
| 既有普通 `Type`/Union/NamedTuple 检查保持 | `base/test-data/unit/check-classes.test:3381–3404`、`:3472–3487`、`:3524–3528`、`:3568–3581` | 由旧测试合理推知。例如普通元组类型依然不能作为相应构造器，NamedTuple 的缺参数错误仍应保留。TypedDict 的修复不等于允许任意 `Type[X]` 无条件调用。 |

题面中的 `D`、`PointDict`、`Car` 等是示例标识符，公开材料没有规定新增函数名、内部辅助方法名、修改文件集合或补丁结构。新功能不应只对这些名称生效。

## 2. 合理实现范围

可以接受多种内部实现：在类型对象调用处专门处理 TypedDict；或者复用/整理现有 TypedDict 构造检查与可调用类型表示，使普通调用分派获得同等行为。判定应以以上传递、赋值、调用、返回类型和旧检查是否正确为依据，不应要求某个私有辅助函数或特定重构形状。本报告不选择方案或提供修复。

现有表示和调用约定能够从公开代码查明：

- 具体 TypedDict 名称引用已经转换为 `CallableType`，返回 TypedDict，fallback 是 `builtins.type`（`base/mypy/checkexpr.py:383–387`、`:925–956`）。类型别名也有相关路径（`:4694–4753`）。
- `Type[Union[A, B]]` 内部正规化为 `Union[Type[A], Type[B]]`，因此这两类表达应有一致的核心行为（`base/mypy/types.py:2977–2999`）。公开文档把 `typing.Type[C]` 与 `type[C]` 描述为对应拼写（`base/docs/source/kinds_of_types.rst:554–561`）。
- Union 调用逐分支检查，再合并结果类型（`base/mypy/checkexpr.py:3210–3224`）。接受合法示例不授权忽略另一分支的不合法参数。
- 已有 `.test` 用例的错误/提示文本是具体回归约定，测试框架逐项比较输出（`base/test-data/unit/README.md:27–45`；`base/mypy/test/testcheck.py:173–195`）。题面没有为新增间接调用的错误文本指定统一精确格式，也没有要求复刻 0.910 的旧大小写和五条报错顺序。

有多种合理解释的扩展边界应单独记录：间接调用是否必须接受直接构造支持的单字典参数；泛型、插件生成、递归 TypedDict 的新增组合是否属于本题完整目标；以及 `Boat` 的通用推断问题是否一并解决。直接构造的原有能力不能因此回退。当前 `typeddict_callable` 和 `typeddict_callable_from_context` 把字段列成命名参数，而直接调用还有专门的键检查；这是需要正常查代码厘清的接口差异，不是必须知道未来修复才能继续开发的缺口（`base/mypy/checkexpr.py:488–500`、`:925–956`）。

## 3. 初态线索与疑义

### 可从公开材料定位的入口

1. 最小空字典例子和完整 `Car`/`Boat`/`Truck` 例子都在题面，无外部数据、私有服务或第三方应用才能重建的输入（`user_prompt.txt:8–34`、`:38–103`）。前两个短例子省略导入，完整例子已给出 `typing` 和 `dataclasses` 导入；补上标准库导入属于正常复现工作。
2. `check_call` 对 `TypeType` 调用 `analyze_type_type_callee`（`base/mypy/checkexpr.py:1593–1595`）。后者处理 Any、Instance、Union、TypeVar 和 NamedTuple，但没有 TypedDict 分支，最后产生“不支持实例化”的诊断并返回错误来源的 Any（`:1818–1860`）。这是可直接调查的静态线索，不是实际复现结果。
3. 类型对象参数兼容已有检查：具体构造器与 `TypeType` 比较时使用其返回类型，两个 `TypeType` 则比较内部类型（`base/mypy/subtypes.py:724–726`、`:1041–1051`）。结合当前 TypedDict 可调用表示可推知，旧 issue 的“`Type[D]` 不兼容 `Type[D]`”未必仍以相同形式存在；需要实际基线复现确定剩余症状。
4. `Boat` 与 `Truck` 的差异有源码入口。条件表达式只有在上下文为 Union 时直接合并分支，否则计算共同类型；可调用对象合并又可能使用 fallback（`base/mypy/checkexpr.py:5616–5690`；`base/mypy/join.py:396–422`）。这解释了为什么不能仅从消除一个构造报错就断言完整示例会通过。

### 缺口的实际影响

- **运行条件待验，影响能否执行复现与测试。** 未提供 actor 身份下解释器、依赖、源代码加载位置、临时目录可写性和选定测试执行结果。不能把“conda 已激活”当作已验证事实。需要环境验证，不需要补隐藏验收用例。
- **完整示例的范围有局部歧义，影响何时称为完成。** 默认需求是全部无错误，但对 NamedTuple/`Boat` 的旁注使“只修 TypedDict 特有部分”的解读也有出处。开发者可以先独立调查核心 `type[TypedDict]` 问题；不能据此把整个题面视为无法开发。
- **版本差异影响报错基准。** 原环境为 mypy 0.910/Python 3.9.7/Arch Linux（`user_prompt.txt:130–136`），实际指定源码版本不同。复现应使用指定 base 和明示 flags；不应安装 0.910 替代本题基线来满足旧日志。
- **未见必须补充的公开附件。** 当前核心问题、示例、接口、安装说明及测试框架都在包内。未访问文档中的公共链接，也没有发现必须取回外链内容才能建立最小复现的证据。公开祖先历史可能有帮助，但本次没有必要请求或读取它。

### issue、harness 指令和环境声明分开处理

| 类别 | 可见内容 | 本次处理 |
| --- | --- | --- |
| issue 需求 | 接受题面有效程序，修复 TypedDict 类型对象/Union 的问题 | 以上需求表是行为依据，来自 `user_prompt.txt` 及 `public_bundle.json:1` 的 `problem_statement`。 |
| harness 操作指令 | 在 `/testbed` 修复，只改 NON-TEST 源码；禁止改测试；测试保持窄范围；完成后简短总结 | 来自 `public_bundle.json:1` 的 `public_hints`，不是类型系统语义要求。本审查没有授权忽略。 |
| 待验环境声明 | bash 已在 `/testbed`、名为 `testbed` 的 conda 环境预激活、工具已经就位 | 同字段中的声明，尚无 actor 执行证据。镜像名、digest、workdir、allowed_tools 也是清单信息，不是运行验证。 |
| 旧机制解释 | “所有测试改动都会恢复、永不计分” | `environment_brief.md:18–24` 明确说明该解释不代表当前机制；现在没有按测试文件名统一排除，仍有官方文件恢复等限制。逐文件影响留给协调者核实。 |

若“禁止改测试”实际适用，可在非测试实现中开发，运行已有公开用例，并通过 `mypy -c` 或临时复现输入验证，不依赖修改仓库测试。它会限制把新增回归例直接写进 `.test` 的常规工作流，但目前没有证据说明核心实现必须修改测试文件才能成立。若该指令不适用，则可按仓库正常流程补回归用例和 fixture（`base/CONTRIBUTING.md:126–128`；`base/test-data/unit/README.md:8–10`、`:68–78`）。两种情况下都要满足同一行为需求；不能以旧评分机制说明直接判题无效。指令如何进入实际消息仍待核对；bundle 会写入真实工作区，未出现在渲染题面不等于不可见（`environment_brief.md:3–6`、`:23–24`）。

## 4. 开发需求表

表中 C1–C8 均指下方“建议，未执行”的命令；没有任何一项已经通过。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口 | 最小验证及预期 |
| --- | --- | --- | --- | --- |
| 指定源码和正确 Python 解释器 | `user_prompt.txt:1`；`base/setup.py:11–13`、`:234`；`base/mypy/version.py:11` | 声明工作目录 `/testbed`，源码按 base 导出；未验证真实容器 | 必须确认 actor 使用本题源码，而不是另一份已安装/编译的 mypy；Python 至少 3.8，运行原 `type[...]` 示例宜 3.9+ | C1 应打印预期解释器、环境名和 `/testbed` 下的模块路径；C2 应能启动 CLI。单靠版本号不能确认所有资源。 |
| mypy 运行依赖 | `base/mypy-requirements.txt:1–4`；`base/setup.py:221–225` | 仅旧提示宣称预装环境；`environment_brief.md:10–12` 不保证公网下载或安装成功 | `typing_extensions`、`mypy_extensions`，Python <3.11 时 `tomli` 是否已安装未知 | C2 成功导入/启动；依赖缺失是环境失败，不是 issue 原 bug。缺包需已有本地依赖或协调者补充，不默认联网。 |
| 标准库类型资产和公开输入 | 题面仅用 `typing`、`dataclasses`；包有 `base/mypy/typeshed/stdlib/typing.pyi`、`dataclasses.pyi` | 提供跟踪源码/静态资产，不保证镜像实际可读 | actor 的安装是否能找到正确 typeshed 未验 | C3/C4 应进入类型检查，不能因为缺 stub 或导入路径失败而算复现成功。无数据库、GPU、远端服务需求。 |
| 最小 TypedDict/Union 复现 | `user_prompt.txt:8–34`、`:103–107`；调用入口见 `base/mypy/checkexpr.py:1818–1860` | CPU profile 的声明存在；本题实际资源未验 | 当前精确诊断尚未捕获 | C3 在原基线上预计出现 `Cannot instantiate type` 类诊断；是否仍有全部旧伴随错误不能静态确认。修复目标为无类型错误且保留类型信息。 |
| 完整 `Car`/`Boat`/`Truck` 验证 | `user_prompt.txt:40–107` | 可写工作区/home 是 profile 声明；临时空间默认 1 GiB | 临时文件权限、当前三条路径输出及 `Boat` 范围待验/澄清 | C4 保持原代码和 flags；按字面目标修复后应无错误。不能以 C3 通过替代完整示例检查。 |
| 公开 TypedDict 回归套件、fixture、临时写入 | `base/test-data/unit/check-typeddict.test:3–76`、`:1085–1095`；`base/mypy/test/testcheck.py:108–129`；`base/mypy/test/config.py:12–19` | 声明 CPU 2/内存 4 GiB 和可写空间，不是实测保障 | pytest/xdist 可用性、临时文件创建、fixture 读取、耗时/内存未知 | C5 后运行 C6，预期已有合法/非法构造用例全部保持原输出；这些旧测试不等于本题新增行为已覆盖。 |
| `Type` 普通类型与 Union 行为回归 | `base/test-data/unit/check-classes.test:3381–3404`、`:3472–3487`、`:3524–3581` | 同上 | 是否可完成该窄测试选择未知 | C7 预期旧 `Type` 用例通过，含应保留的错误诊断。 |
| 本地安装/构建（仅必要时） | `base/CONTRIBUTING.md:39–49`；`base/pyproject.toml:1–16`；`base/setup.py:88–96`、`:178–179` | 解释器/系统包写权限仍需核对，无公网依赖保证 | setuptools、wheel 和构建依赖是否就绪，site-packages 可写性未知 | 源码根目录可直接 `python -m mypy`，最小验证不必编译 C 扩展。确需 editable 安装时用 C8；应成功安装当前源码，缺依赖不应擅自以网络下载补齐。 |

测试框架至少需要 pytest 和 pytest-xdist；公开锁定版本分别为 7.4.2、3.3.1（`base/test-requirements.txt:55–63`）。默认 pytest 自动并行（`base/pyproject.toml:90–111`），故建议显式 `-n0` 进行窄测试。`lxml` 在 `testcheck.py` 中可选导入，缺失时跳过报告类测试；本题 TypedDict 套件不据此要求安装它（`base/mypy/test/testcheck.py:27–30`、`:57–59`）。不需要先执行全仓测试或 mypyc 构建。

以下每条命令均为**建议，未执行**；应由实际 actor 在 `/testbed` 中运行，不是在本静态导出上运行。

**C1：建议，未执行——确认解释器、激活声明和加载位置。**

```sh
python -c 'import os, sys, mypy; print(sys.version); print(sys.executable); print(os.environ.get("CONDA_DEFAULT_ENV")); print(mypy.__file__)'
```

**C2：建议，未执行——最小导入及 CLI 启动。**

```sh
python -c 'import mypy.main, mypy_extensions, typing_extensions; print("runtime imports ok")'
python -m mypy --version
```

**C3：建议，未执行——无需改仓库测试的最小公开复现。**

```sh
python -m mypy --python-version 3.9 --show-error-codes --warn-return-any -c 'from typing import TypedDict, Union
D = TypedDict("D", {})
def f(d: type[D]) -> D:
    return d()
f(D)
U = Union[int, D]
def g(u: type[U]) -> U:
    return u()
g(int)
g(D)
'
```

`--python-version 3.9` 用于固定题面语言目标；原 flags 是 `--show-error-codes --warn-return-any`。预计原基线仍会在类型对象调用处出现不支持实例化；这是静态推断，具体数量和文本以 actor 捕获为准。

**C4：建议，未执行——完整公开复现。**先将 `user_prompt.txt:41–100` 的 Python 代码按代码块自身缩进保存到独立临时输入 `/tmp/mypy16963_repro.py`，不修改仓库已有测试，然后：

```sh
python -m mypy --python-version 3.9 --show-error-codes --warn-return-any /tmp/mypy16963_repro.py
```

**C5：建议，未执行——公开测试框架导入。**

```sh
python -c 'import pytest, xdist, mypy.test.testcheck; print("test imports ok")'
```

**C6：建议，未执行——现有 TypedDict 套件。**

```sh
python -m pytest -n0 mypy/test/testcheck.py::TypeCheckSuite::check-typeddict.test
```

**C7：建议，未执行——现有 `Type` 行为窄回归。**

```sh
python -m pytest -n0 mypy/test/testcheck.py::TypeCheckSuite::check-classes.test -k testTypeUsingTypeC
```

**C8：建议，未执行——仅缺少必要的本地安装时使用。**运行依赖和构建工具应已就绪，且 actor 有目标环境写权限；该命令不负责补齐缺包。

```sh
MYPY_USE_MYPYC=0 python -m pip install --no-deps --no-build-isolation -e .
```

## 5. 阅读范围和限制

实际打开的文件（源码、长测试与文档均按相关片段读取，未做全文件穷尽审查）：

- 指定的 `public_reader.md` 角色卡；公开包 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。
- `base/README.md`、`base/CONTRIBUTING.md`、`base/test-data/unit/README.md`。
- `base/mypy/checkexpr.py`：名称引用、直接构造、TypedDict callable、一般调用/TypeType 分派、Union 调用、类型别名、条件表达式及表达式入口相关片段。
- `base/mypy/subtypes.py`：callable 与 TypeType、TypeType 与 TypeType 兼容片段；`base/mypy/types.py`：callable 类型对象标识、TypedDictType 定义、TypeType 说明及正规化；`base/mypy/join.py`：可调用对象合并、TypeType 合并和 fallback 片段。
- `base/test-data/unit/check-typeddict.test`：直接构造、类定义、错误构造、totality 与部分等价 Union 用例片段；`base/test-data/unit/check-classes.test:3380–3585`。有一批较长工具输出被截断，未把未呈现段落当成已完整审查；关键构造、totality 和 TypeType 段落已有可见证据。
- `base/docs/source/typed_dict.rst:45–103,116–153`；`base/docs/source/kinds_of_types.rst:549–634`。
- `base/pyproject.toml`、`base/setup.py:1–245`、`base/test-requirements.txt`、`base/mypy-requirements.txt`、`base/build-requirements.txt`、`base/conftest.py`、`base/mypy/test/config.py`、`base/mypy/version.py`、`base/mypy/__main__.py`。
- `base/mypy/test/testcheck.py:1–210`、`base/mypy/test/data.py:1–105`、`base/mypy/test/helpers.py:1–90`。

另外进行了包内文件名列举和定向 `rg` 搜索：`mypy/typeops.py`、`mypy/messages.py`；`check-type*.test`、`check-classvar.test`、`check-functions.test`、`check-unions.test`、`check-isinstance.test` 的相关关键词；fixture/typeshed 文件名。搜索命中不等于完整阅读。未打开 `base_identity.json`，未全面阅读全部类型检查器、dataclass 插件、stub 内容和测试用例，也没有证明所有间接构造边界已有公开测试。

没有读取角色卡父目录、其它题、调查报告、gold、私有评分材料、未来历史或共享镜像克隆。base 导出不包含完整容器、`.git`、预装依赖和运行资源；因此本报告只评价公开需求及可调查性，全部运行成功/失败均保留为待验证。阅读限制是本次协作约定，不是文件权限隔离或预训练无污染证明。
