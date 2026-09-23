# python__mypy-15184：fresh 公开要求审查

本审查只读取指定角色卡和本题 PUBLIC_DIR。未读取私有评分、gold、旧结论、其他题、祖先或未来历史、镜像克隆；未联网、运行项目、安装依赖或修改 base。以下运行结果均为静态推断，所有开发命令均为**建议，未执行**。相对路径以本题 PUBLIC_DIR 为根。

## 1. 需求表

| 行为 | 明确程度与应有边界 | 公开依据 |
|---|---|---|
| `assert_type` 失败时，同名而不同的类型应显示完整限定名 | **明示。**示例应能区分表达式的 `typing_extensions.SupportsIndex` 与期望的 `typing.SupportsIndex`，避免 `"SupportsIndex", not "SupportsIndex"`。问题要求改善诊断，并未明确要求此断言通过。 | `user_prompt.txt:3,7–28` |
| 消歧能力不应只针对这两个内置协议的名字 | **可合理推知。**标题讨论一般的名称歧义；仓库已有按短名收集多个完整名的通用实现，并递归收集类型参数中的实例。任意两个模块中的同名类，以及嵌套类型中的同名实例，均是合理的调查/验证范围。 | `user_prompt.txt:3`；`base/mypy/messages.py:2559–2602,2638–2661` |
| 保留无歧义错误的简洁文本、表达式在前/目标在后的顺序、引号及 `assert-type` 错误码 | **代码及公开测试约定。**现有用例明确期待 `"int", not "str"`、`"int", not "Any"` 等文本；错误构造函数固定了顺序和错误码。 | `base/test-data/unit/check-expressions.test:931–941`；`base/mypy/messages.py:1658–1664`；`base/mypy/errorcodes.py:151` |
| 保留原有断言判定、返回类型、字面量处理及未检查函数提示 | **可合理推知为旧行为。**当前使用 `is_same_type`；失败才报告，最后返回源类型。字面量值、泛型推导、未检查函数、`--check-untyped-defs` 及不压缩联合类型的既有用例应继续成立。这里的 `is_same_type` 不是简单对象身份比较，而是双向 proper-subtype 检查。 | `base/mypy/checkexpr.py:3911–3932`；`base/mypy/subtypes.py:251–267`；`base/test-data/unit/check-expressions.test:931–990` |
| 两个公开入口都应继续使用一致的断言行为 | **现有接口约定。**`typing.assert_type` 与 `typing_extensions.assert_type` 共用语义分析路径；仍要求两个位置参数、第二参数可解释为类型。 | `base/mypy/types.py:138`；`base/mypy/semanal.py:4807–4819,5147–5151`；`base/test-data/unit/semanal-errors.test:846–852`（搜索命中） |
| 将方法完全相同的协议视为同一类型，使示例通过 | **仍有多种解释，属于讨论性扩展。**题面用 “perhaps” 并征求意见；没有给出新的相等性定义或边界。不能据此将改变协议等价关系作为必需验收，也不能通过直接压制错误替代明确的消歧要求。 | `user_prompt.txt:26–28`；`base/docs/source/error_code_list.rst:884–896`；现有判定见上行 |

公开材料没有新增配置开关、函数名或内部实现结构的约定。示例的模块限定名有明确依据：两份已导出的类型桩分别声明了 `SupportsIndex`，且都声明 `__index__ -> int`（`base/mypy/typeshed/stdlib/typing.pyi:308–312`；`base/mypy/typeshed/stdlib/typing_extensions.pyi:181–184`）。不能把运行时协议类是否为同一对象，直接当成此静态检查器的判定依据。

## 2. 合理实现范围

- 可以让该诊断利用已有的联合格式化能力，也可以采用另一种等效的格式化组织方式：共同检查源/目标类型中的名称冲突，仅为有冲突的类型显示完整限定名，并保留既有错误语义。公开要求没有限定必须调用某个内部函数或修改几行代码；这里不提供补丁。
- 仓库已有 `format_type_distinctly` 的契约：联合格式化各类型，必要时提高详细程度，并区分短名相同的不同类型；其他诊断已有调用者（`base/mypy/messages.py:654–659,675–679,2638–2661`）。因此，对联合类型、类型参数等进行一致处理有公开设计依据，不能仅凭示例把实现限制成 `SupportsIndex` 特例。
- 完整名的通常含义是类型定义的 `fullname`，不只是调用方采用的导入别名；短名和完整名的选择见 `base/mypy/messages.py:2397–2424`。只改变局部别名或只硬编码示例字符串，无法覆盖标题描述的一般情况。
- 无条件将所有无歧义类型改成完整限定名，会与既有简洁诊断测试冲突，不能视为无差别等价方案。仅为一侧加限定名虽然可能可读，但示例明确要求完整限定名，并且现有共同格式化机制会限定冲突的双方；这是更有证据的输出约定。
- 对递归别名、类型变量同名、重载函数等所有可能“显示相同”的情形，题面没有逐一承诺新的可区分表示；现有格式化实现本身仍有特定缩写和边界（例如 `base/mypy/messages.py:2384–2394,2427–2442,2542–2546`）。不能把“所有内部不同类型必有不同字符串”擅自提升为此题的完整规格。
- 改变协议等价关系会扩大类型系统语义范围，公开材料不足以规定怎样修改或验证这种扩展；保留现有判定、修正诊断是有直接公开依据的合理范围。

## 3. 初态线索与疑义

**可定位的调查入口。**题面提供完整短程序和错误文本。语义分析将两个入口转换为 `AssertTypeExpr`，检查器进行原有相等性判断，然后调用 `assert_type_fail`。该错误函数分别格式化两个类型，而 `format_type_bare` 每次只在自身类型内部查同名重叠；仓库另有跨多个类型共同消歧的工具。这条静态调用链足以定位调查入口，无需外链、附件或历史提交（`base/mypy/semanal.py:4807–4819`；`base/mypy/checkexpr.py:3911–3932`；`base/mypy/messages.py:1658–1664,2621–2661`）。这是代码阅读结论，尚未验证实际运行经过此链。

**版本信息缺失但可正常查代码解决。**题面没有给出原 CLI 参数、解释器或目标 Python 版本；`typing.SupportsIndex` 在桩中要求目标 Python ≥3.8。`typing.assert_type` 在 ≥3.11 才直接提供，而 `typing_extensions.assert_type` 有兼容定义/重导出（`base/mypy/typeshed/stdlib/typing.pyi:308–312,783–786`；`base/mypy/typeshed/stdlib/typing_extensions.pyi:210–233`）。可显式选择 3.10 并使用包内类型桩复现，不需要先补充原报告者环境；命令是否真的可运行仍须实际 actor 核验。

**证据范围。**旧 `assert_type` 用例给出了多项必须保留的行为，但所读用例中没有题面这组同名协议的专门回归案例。已有其他诊断的歧义用例使用 `__main__.Any`、`__main__.List` 等完整名，支持此命名惯例（`base/test-data/unit/check-basic.test:69–86`）。“还需阅读调用者/类型桩”属于正常开发调查，不能据此说题面缺陷。

**真正未核实的条件。**源码导入是否命中该工作区、实际 Python/依赖版本、pytest 插件是否可收集这些旧测试、可写临时目录和缓存空间，均未运行验证；若缺依赖且没有离线供给，会实际阻碍开发。公开包没有承诺预装已满足要求。未发现此问题必须取得的公开外链内容，也无需请求隐藏验收测试或未来修复。

**issue、harness 指令、环境声明分开处理。**

- issue 目标是第 1 节中的诊断消歧；协议等价是未决讨论（`user_prompt.txt:3–28`）。
- 原 `public_hints` 要求编辑 NON-TEST 源码、不改测试、窄范围验证；它还称 bash 位于 `/testbed`，工具为 bash/edit（`public_bundle.json:1`，字段 `public_hints`、`allowed_tools`、`workdir`）。若禁止修改测试适用，本题有明确的非测试诊断代码入口，可以读取并运行现存测试、用 `-c` 做临时验证；它会限制把新回归用例写入测试文件，但没有从公开材料显示必然阻断源码修复。若该指令不适用，则可以按常规开发补充回归测试；本审查不擅自宣布取消它。
- “conda 已激活”只是待验环境声明。“所有测试修改都会恢复、永不计分”已不能概括当前机制；当前没有按测试文件名统一排除，仍有官方文件恢复等具体限制，逐题适用文件由协调侧另核实。此项登记为共享输入/运行条件问题，不据此判断题目不可用（`environment_brief.md:18–26`）。
- bundle 会放到求解工作区公开路径；未出现在静态 `user_prompt.txt`，不能推断字段不可见，也不能推断实际 CLI system message 已包含它（`environment_brief.md:3–6,25–26`）。

## 4. 开发需求表

本表中的 C1–C6 均为**建议，未执行**，指向未来真实 `/testbed` 工作区；本次没有在静态 base 导出上执行。命令不依赖访问公网。

| 操作 / 资产 / 服务 | 公开依据 | 环境说明支持到哪层 | 缺口 | 最小建议及预计现象 |
|---|---|---|---|---|
| Python、实际 mypy 源码导入、运行依赖 | `base/setup.py:11–13,223–236` 要求 Python ≥3.7、`typing_extensions`、`mypy_extensions`，并按 Python 版本需要 `typed_ast` / `tomli`；`base/mypy-requirements.txt:1–5` | `/testbed`、actor 和可写工作区为说明中的预期；预激活 conda 仅为 hints 声明（环境说明 8–13 行） | 解释器版本、导入路径、是否有旧编译扩展覆盖 `.py`、依赖实装情况均未知 | C1：打印解释器、相关模块路径；C2：CLI 版本启动。预计成功导入本工作区代码并正常退出；缺依赖/旧扩展属于运行条件问题，不能当成原 bug。 |
| 完整标准库 / typing 类型桩和题面输入 | `base/mypy/typeshed/stdlib/typing.pyi:308–312`；`typing_extensions.pyi:181–184,210–233`；`user_prompt.txt:7–17` | 类型桩已在静态 base 中；`base_identity.json:5–15` 声明 blob 已物化、无 gitlink/LFS 缺件 | 实际镜像是否相同、是否被第三方类型包或配置覆盖未核实 | C3：设目标 3.10、禁用 site-package 搜索，按完整题面进行静态检查。预计 base 报重复短名错误；修复后仍报告类型不匹配，但两侧完整名不同。 |
| pytest、pytest-xdist、pytest-forked 等旧测试依赖及内置 fixture | `base/test-requirements.txt:1–20`；`base/pytest.ini:8–24`；`base/conftest.py:5`；`base/mypy/test/testcheck.py:35–55`；`base/test-data/unit/check-expressions.test:931–990` | 环境说明只要求日后 CPU 核验，未提供通过证据 | 依赖版本兼容性、收集成功、fixture 可读性均未知；运行样例使用完整 typeshed，数据测试默认使用最小桩，不能混为同一资产需求（`base/test-data/unit/README.md:54–73`） | C4：串行运行既有 `testAssertType` 用例。预计旧实现和正确诊断修复均能通过，故此命令本身不能证明新 bug 已修。C5 可扩至一个公开数据文件。 |
| 临时目录、缓存和工作区写入 | `base/mypy/test/data.py:328–354` 创建临时用例目录和文件；`base/docs/source/command_line.rst:747–759` 明确禁用增量读取后仍写缓存 | 环境说明 9–12 行声称工作区/home 可写，给出默认 tmp 1 GiB 等上限，但本题实际配置未验 | 实际 actor 的 tmp/cache 写权限与剩余容量待验 | C3/C4 会实际覆盖这些必要写入路径；应观察是否发生权限或空间错误。此题无需 GPU、外部数据库或常驻服务；按现有代码与测试未发现这类需要。 |
| 本地开发安装 / 构建（仅现有环境不能直接导入时） | `base/CONTRIBUTING.md:39–45`；`base/test-data/unit/README.md:137–154` 也允许源码目录直接 `python -m mypy`；`base/setup.py:88–96` 默认不启用 mypyc；`base/pyproject.toml:1–18` | 不保证公网或系统包写权限；真实镜像构建产物未导出（环境说明 5–12 行） | 缺失依赖的离线分发和 pip/setuptools/wheel 可用性，及可写安装位置待核实 | 首选 C1/C2 检查已有环境，无须为诊断格式化强制编译 C。确需安装时 C6 是离线条件性命令；依赖已预装且可写才预计成功。缺件时需环境侧提供，不能默认在线下载可用。 |

**C1：最小导入检查，建议，未执行。**工作目录应为真实 `/testbed`。

```bash
python -c 'import sys, mypy, mypy.messages, typing_extensions, mypy_extensions; print(sys.executable); print(sys.version); print(mypy.__file__); print(mypy.messages.__file__); print(typing_extensions.__file__); print(mypy_extensions.__file__)'
```

这是基本导入证据，不单独证明所有测试依赖或分支均可用；还应确认打印出的 mypy 路径是正在修改的源码或明确对应的构建产物。

**C2：CLI 启动，建议，未执行。**

```bash
python -m mypy --version
```

**C3：题面复现，建议，未执行。**`--no-site-packages` 避免目标版本选择导致查找另一 Python 安装或外部 PEP 561 包；这是对复现条件的显式限定，不是对原报告实际命令的声称（`base/docs/source/command_line.rst:244–253`）。

```bash
python -m mypy --python-version 3.10 --no-site-packages --no-incremental --hide-error-codes --no-error-summary -c 'from typing import TypeVar
import typing
import typing_extensions

U = TypeVar("U", int, typing_extensions.SupportsIndex)

def f(si: U) -> U:
    return si

def caller(si: typing.SupportsIndex):
    typing_extensions.assert_type(f(si), typing.SupportsIndex)'
```

预计原 bug 为第 11 行 `Expression is of type "SupportsIndex", not "SupportsIndex"`；诊断修复后预计为 `Expression is of type "typing_extensions.SupportsIndex", not "typing.SupportsIndex"`。输入方式改变路径前缀为字符串来源；这是有意保留的类型错误，不能以退出成功作为唯一修复标准。没有 `--hide-error-codes` 时应保留既有 `[assert-type]`。以上均未观察运行输出。

**C4：最窄既有回归范围，建议，未执行。**

```bash
python -m pytest -n0 mypy/test/testcheck.py -k testAssertType
```

依据 `base/CONTRIBUTING.md:81–85`、`base/test-data/unit/README.md:122–135,187–189`；`-n0` 避免 pytest 配置中的 `-nauto` 扩大并行资源。预计所选用例通过，保留普通类型、Literal、泛型、未检查函数及联合类型的旧行为。

**C5：单公开数据文件验证，建议，未执行。**

```bash
python -m pytest -n0 mypy/test/testcheck.py::TypeCheckSuite::check-expressions.test
```

若实现改动了共享格式化逻辑，可再针对已有歧义用例运行以下窄检查；不要求全仓测试：

```bash
# 建议，未执行
python -m pytest -n0 mypy/test/testcheck.py -k testIncompatibleAssignmentAmbiguousShortnames
```

**C6：有条件的离线 editable 安装，建议，未执行。**仅在基础依赖和构建依赖均已具备、安装位置可写且确有安装必要时使用；不是要求审查期间安装。

```bash
MYPY_USE_MYPYC=0 python -m pip install --no-index --no-build-isolation --no-deps -e .
```

该命令不补齐缺失依赖。公开安装指南的 `pip install -r test-requirements.txt` 需要可用包源或本地包资产；本题环境说明未保证公网，不应把该指南误读为当前已具备条件。

## 5. 阅读范围与限制

**完整打开的文件：**指定 `roles/public_reader.md`；本题 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`；`base/README.md`、`base/CONTRIBUTING.md`、`base/test-requirements.txt`、`base/mypy-requirements.txt`、`base/build-requirements.txt`、`base/pytest.ini`、`base/pyproject.toml`、`base/conftest.py`、`base/test-data/unit/fixtures/tuple.pyi`、`base/mypy/__main__.py`。

**打开相关段落：**

- `base/mypy/messages.py:650–682,1645–1675,2345–2445,2520–2725,2870–2960`。
- `base/mypy/checkexpr.py:3890–3945`；`base/mypy/semanal.py:4780–4835,5140–5160`；`base/mypy/subtypes.py:240–294`；`base/mypy/types.py:132–141`。
- `base/setup.py:1–37,78–100,213–245`；`base/mypy/test/testcheck.py:1–102`；`base/mypy/test/data.py:321–367,686–732`。
- `base/mypy/typeshed/stdlib/typing.pyi:298–318,771–789`；`base/mypy/typeshed/stdlib/typing_extensions.pyi:168–189,207–237`。
- `base/test-data/unit/check-expressions.test:925–1005`；`base/test-data/unit/check-basic.test:45–124`；`base/test-data/unit/README.md:1–83,101–157,177–191`。
- `base/docs/source/error_code_list.rst:873–905`；`base/docs/source/command_line.rst:240–258,690–720,741–763`。

**检索而非通读：**在 `base/mypy` 的相关源文件、`base/mypy/test`、`base/test-data/unit` 和 `base/docs/source` 中检索 `assert_type`、联合格式化、同名歧义、测试收集/临时目录、CLI 参数等；包括 `base/mypy/errorcodes.py`、`base/mypy/main.py`、`base/mypy/test/config.py` 和表中标注的测试搜索命中。曾尝试搜索 `base/mypy/test/testmessages.py`，该文件不存在；随后依据实际存在的源文件和公开测试继续阅读。`rg --files` 曾枚举 PUBLIC_DIR，输出截断；没有将目录枚举等同于通读全部文件。

**未查项：**未读全部类型系统实现、全部调用者/格式化分支、全部测试与 fixture、完整构建链；未查外链、包下载源、Git 历史、实际容器、实际 CLI 消息及实际模型工具能力。当前未发现必须补齐才能理解本题的外部公开材料。base 是指定提交的静态导出，不是完整运行容器；`base_identity.json` 的校验字段只是公开包声明，本审查没有重新运行仓库身份/字节校验。

本次所称 fresh 表示此次任务未接触私有或历史结论，范围受协作约定约束；不构成文件权限隔离或预训练无污染证明。输出没有给题目“通过/淘汰”标签。
