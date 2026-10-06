# python__mypy-10424 公开材料静态审查

本次仅阅读角色卡及指定公开包，未运行项目代码、测试、安装或网络搜索，未修改 `base/`。下文路径均相对于本题 `PUBLIC_DIR`，行号来自导出文件；`public_bundle.json` 为单行 JSON，因此其字段均引用第 1 行。没有读取本题私有材料或既有审查结论。

题面足以开始调查：它提供完整 Python 示例、错误类型、期望类型及回归版本。公开源码和旧测试能定位调查入口及应保留行为。当前主要未知是实际开发环境是否能运行，以及未在示例中规定的元类缩窄边界，不能据此声称已复现或环境已可用。

## 1. 需求表

| 行为 | 依据与性质 | 审查解释 |
| --- | --- | --- |
| 示例中 `if type(t) is not M: return` 之后的 `reveal_type(t)` 应仍为 `Type[C]`，而非 `<nothing>` | 明示：`user_prompt.txt:3–24` | 这是可直接验收的核心要求；不能仅消除某条诊断而继续推断为空类型，也不能通过退化为 `Any` 代替保留 `Type[C]`。 |
| `Type[C]` 可以接收 `C` 的子类对象，子类可以采用自定义元类 | 明示示例：`user_prompt.txt:9–21`；仓库语义：`base/docs/source/kinds_of_types.rst:577–583,648–651`、`base/docs/source/metaclasses.rst:6–25` | 不能仅凭 `C` 自身的默认元类排除 `D`；`f(D)` 是示例中的合法调用。这里 `t` 是类对象，不能与 `C` 的实例混淆。 |
| 普通 `type(x) == int` / `is int` 的正分支仍可缩窄 | 公开测试：`base/test-data/unit/check-isinstance.test:2577–2608` | 已有 `Any → int` 及 `Union[int, str] → int` 约定；一律禁用 `type(...)` 比较缩窄会破坏公开旧行为。 |
| 普通非 `final` 类型的否定分支保留联合；`!=` / `is not` 的另一分支仍缩窄 | 公开测试：`base/test-data/unit/check-isinstance.test:2601–2608,2625–2646`；解释：`base/mypy/checker.py:4026–4033` | 原因是变量还可能是比较目标的子类实例。不能把本题理解成所有否定比较都不得产生任何分支信息。 |
| `final` 类的双分支缩窄、已有链式比较规则应保留 | 公开测试：`base/test-data/unit/check-isinstance.test:2585–2592,2610–2624,2648–2673` | 单一目标的链式比较能够缩窄；多个不同目标的示例不缩窄；`final` 类示例允许从联合中排除该类。 |
| 现有 `Type[...]` 与 `builtins.type` 的类型交集行为应保持兼容 | 公开代码与测试：`base/mypy/meet.py:630–641`、`base/mypy/test/testtypes.py:943–950` | 若实现改变共享的交集计算，需要保留这类既有类型运算，不应只关注示例的打印结果。 |
| 修复是否必须覆盖 `is`、`==`、`!=`、反向比较、元类别名、泛型、联合或 `isinstance` | 部分可推知，部分未规定：`base/mypy/checker.py:4141–4204,4232–4233` | 四种比较共用入口且否定运算交换分支，因此一致处理直接等价的 `is M` 表达是合理预期；题面没有逐一规定所有扩展情形，也没有要求实现完整元类交集系统或更改全部 `isinstance` 行为。 |

**输入层次应分开记录：**

- Issue 需求是上述类型推断修复；“回归自 0.812”是报告人的历史线索，未由本包实测（`user_prompt.txt:26`）。
- Harness 操作指令来自 `public_bundle.json:1/public_hints`：在 `/testbed` 工作、修改非测试源码、禁止改测试、窄范围运行测试、完成后简述。这些不是 Python 类型语义。
- “conda 环境 testbed 已激活”是同字段的待验环境声明，不能代替 actor 身份验证。`environment_brief.md:18–24` 说明旧的“所有测试修改都会恢复、永不计分”解释已不能代表当前机制；当前没有按测试文件名统一排除，但仍可能有官方文件恢复等具体限制。本次不推断哪些文件会被恢复。
- 若“禁止改测试”原指令适用，仍存在只改源码、以命令行示例及已有测试验证的合理开发路径，未发现核心修复必需修改测试或 fixture 的证据；它会限制新增仓库回归测试。若该指令不适用，可按仓库测试格式补回归用例，但不能从本审查推定这已获允许。实际适用情况列为共享输入/运行条件问题。

## 2. 合理实现范围

公开要求约束可观察类型行为，没有指定应改哪个函数、内部变量名或数据结构。合理实现可以在比较产生约束时保守处理类对象与元类，也可以在共享的类型相交/缩窄计算中避免错误的空交集；两者都应以示例保留 `Type[C]`、上述旧行为不回退为条件。前者与后者的影响范围不同，需要按实际改动选择验证范围。本审查不指定补丁或标准答案。

更准确的内部表示同样不应仅因结构不同被排除，但题面给出的这一例最终仍应体现原来的 `Type[C]` 信息。仅扩大为 `Any`、改成 `Type[M]`、只隐藏 `reveal_type` 的输出，均没有满足该明确期望。关闭全部类型比较缩窄也与旧测试冲突。

输出沿用现有 `reveal_type` 诊断格式。题面中的 `Type[C]` 是语义描述，公开测试采用 `Type[__main__.A]` 这类带模块名的表示（`base/test-data/unit/check-isinstance.test:2574`）；模块前缀随运行入口变化，不应把题面缩写解释为必须逐字打印 `Type[C]`。没有新 API、配置开关、环境变量或特殊命名要求。

元类自定义 `__eq__`、动态生成元类、特殊 `final` 情形等仍有边界问题。仓库明确不理解任意元类代码或动态元类（`base/docs/source/metaclasses.rst:103–106`），比较处理本身也有自定义等价运算的限制（`base/mypy/checker.py:4156–4175`）。本题不能被扩张为要求解决这些全部限制。

## 3. 初态线索与疑义

静态调查链条完整：

1. `visit_if_stmt` 取得并应用两条分支的类型约束（`base/mypy/checker.py:3243–3266`）。
2. 比较处理落到 `find_type_equals_check`，否定比较再交换约束（`base/mypy/checker.py:4201–4204,4232–4233`）。该函数识别单参数 `builtins.type` 并把参数原类型与比较目标送入条件缩窄（`base/mypy/checker.py:3960–4016`）。
3. 表达式读取分支约束后调用 `narrow_declared_type`（`base/mypy/checkexpr.py:4170–4194`）；它可能调用 `meet_types` 求类型交集（`base/mypy/meet.py:53–78`）。
4. 重叠检查中已有 `Type[C]` 与元类的特殊逻辑（`base/mypy/meet.py:264–285`），而 `visit_type_type` 对实例类型显式识别的是 `builtins.type`（`base/mypy/meet.py:630–641`）。两处语义衔接是正常的源码调查入口，不是已经运行确认的根因。

题面不含专用失败测试文件，但完整示例足以构造命令行复现；公开 `check-isinstance.test` 尾部集中列出了相关旧行为。因此，继续阅读调用者、类型表示或更多测试属于正常开发，不构成题面缺陷。

没有发现当前必须补充的公开附件或外链内容。README、贡献指南有外链，但本题语义及最小运行入口在包内可读；没有访问外链。若确需核对“0.812 回归”的确切历史，可请求不含未来修复的公开祖先记录或旧版材料；当前定位不依赖这些历史，本次没有访问 Git 镜像。

实际阻碍只能由后续运行核验确定：例如解释器/依赖缺失、源码导入被镜像中的编译产物遮盖、测试临时目录不可写。包中没有证据证明这些故障已经发生，也没有证据证明它们已经排除。`base_identity.json:3–11` 给出了 base 身份及导出元数据，但不是可运行性证明。

## 4. 开发需求表

以下命令均为**建议，未执行**，面向真实 actor 在 `/testbed` 的工作区；不是本静态导出上已经成功的命令。命令编号对应后文。

| 操作 / 资产 / 服务 | 公开依据 | 环境说明支持到哪层 | 缺口 | 最小验证及预期 |
| --- | --- | --- | --- | --- |
| Python 解释器及源码导入 | `base/README.md:64–68`、`base/setup.py:8–10,194–202`、`base/mypy/__main__.py:6–23` | 提示声称 conda 已激活；说明明确要求另验（`environment_brief.md:8–12,18–19`） | 实际版本、路径、依赖兼容及导入来源未验；“Python ≥3.5”不证明任意新版解释器都兼容这份旧源码 | C1：应导入成功并显示实际 Python、源码位置；导入错误属于环境入口失败。 |
| 运行依赖及解析器 | `base/setup.py:194–201`、`base/mypy-requirements.txt:1–5`；Python ≥3.8 的 stdlib AST 路径见 `base/mypy/fastparse.py:42–50` | 不假定可访问公网或下载依赖（`environment_brief.md:10`） | 安装清单和离线包未验；`typed_ast` 在安装声明中有版本条件，测试 requirements 则无该条件 | C1、C2：最小 Python 3 示例应可解析；缺少依赖时需预装或已有离线资产，不能直接假定可联网补齐。 |
| 本题示例与内置类型桩 | `user_prompt.txt:7–21`；`base/setup.py:70–73` 声明打包 typeshed | 导出含源码/旧测试，镜像资产另验（`environment_brief.md:5–6,12`） | 已枚举到 `base/mypy/typeshed/stdlib/builtins.pyi`、`typing.pyi`，未实测 actor 的路径及读取 | C2：报告中的 base 现象为 `<nothing>`；修复后应显示对应 `Type[C]`，无需第三方业务包、数据集或服务。 |
| pytest、自定义收集器及数据驱动测试 | `base/test-requirements.txt:1–18`、`base/pytest.ini:8–22`、`base/conftest.py:3–11`、`base/mypy/test/testcheck.py:27–51,111–136` | 默认 CPU/内存只是 profile 声明，实际未验证（`environment_brief.md:11–12`） | pytest 6.1 系列、xdist 等旧依赖与实际 Python 的兼容性及收集是否成功未验 | C3：相关已有用例应能收集且保持通过；`-n0` 覆盖默认 `-nauto`，避免自动开大量进程。 |
| 测试 fixture、临时目录及写权限 | `base/test-data/unit/README.md:28–40,53–72`、`base/mypy/test/testcheck.py:150–154,174–192`、`base/mypy/test/config.py:10–20` | 说明称工作区/home 可写，解释器写权限仍须核对（`environment_brief.md:9`） | 已枚举到所用 `lib-stub` 与 `fixtures` 文件，未运行验证路径、临时目录及资源上限 | C3/C4：应能写测试临时程序、读取桩并结束；fixture 缺失或写权限错误不能当成原 bug。 |
| 若触及共享类型运算，检查旧交集语义 | `base/mypy/test/testtypes.py:802–815,943–950` | 仅提供同一静态环境声明 | 没有执行记录 | C4：保留既有 Type 类型交集测试；必要时扩展同模块，仍无需全仓测试。 |
| 安装 / 构建 / 外部服务 | 无安装源码运行方式：`base/test-data/unit/README.md:126–143`；默认无扩展模块：`base/setup.py:77–85,155–156` | 无公网下载保证；系统包写权限待验 | 本题无必需的 C 编译、GPU、网络服务或新外部资产证据 | 最小路径直接使用 C1–C3，不要求构建。若实际工作流确需安装，C5 为可选离线安装入口，需已有构建依赖与目标写权限。 |

**C1：最小导入与来源检查（建议，未执行）。** 预期成功导入，并打印实际解释器及 `mypy` 入口/相关模块来源。若出现 `.so` 或工作区外路径，需继续确认源码编辑是否真正生效；不能仅凭 conda 名称认定就绪。

```bash
cd /testbed
PYTHONPATH=/testbed python -c 'import sys; import mypy.main, mypy.checker, mypy.meet; print(sys.version); print(sys.executable); print(mypy.main.__file__); print(mypy.checker.__file__); print(mypy.meet.__file__)'
```

**C2：题面复现（建议，未执行）。** 保留原例，用 mypy 做静态检查；不要用 Python 执行含 `reveal_type` 的程序。成功标准是诊断中的类型而非仅看退出码；题面报告原 bug 显示 `<nothing>`，修复后应为 `Type[__main__.C]` 或入口对应模块限定的同一类型，且 `f(D)` 不新增类型错误。

```bash
cd /testbed
PYTHONPATH=/testbed python -m mypy --no-incremental --cache-dir=/dev/null -c 'from typing import Type

class M(type):
    pass

class C: pass

class D(C, metaclass=M): pass

def f(t: Type[C]) -> None:
    if type(t) is not M:
        return
    reveal_type(t)

f(D)
'
```

**C3：相关公开旧测试（建议，未执行）。** 按公开测试 README 的模块及 `-k` 选择方式（`base/test-data/unit/README.md:111–124`）运行；预期选中的旧行为用例保持通过。它们不是本题新增回归测试，不能以这些通过替代 C2。

```bash
cd /testbed
PYTHONPATH=/testbed python -m pytest -q -n0 mypy/test/testcheck.py -k 'testTypeEquals or testTypeNotEquals or testMultipleTypeEquals or testNarrowInElseCaseIfFinal or testNarrowInIfCaseIfFinalUsingIsNot'
```

**C4：共享类型交集最小回归（建议，未执行；改动触及该层时）。** 预期保持该公开单元测试的既有结果；必要扩展范围由实际改动决定。

```bash
cd /testbed
PYTHONPATH=/testbed python -m pytest -q -n0 mypy/test/testtypes.py::MeetSuite::test_type_type
```

**C5：可选本地安装（建议，未执行；不是最小复现的前置条件）。** `base/pyproject.toml:1–6` 需要 setuptools/wheel，其他依赖须预先存在。下列离线、无依赖解析安装仅在真实 actor 有对应环境写权限且确有安装需要时使用；成功安装也不代替 C1 的导入来源检查。

```bash
cd /testbed
python -m pip install --no-index --no-deps --no-build-isolation .
```

## 5. 阅读范围与限制

实际完整读取或分段打开：角色卡；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`；`base/README.md`、`base/CONTRIBUTING.md`、`base/setup.py`、`base/pyproject.toml`、`base/mypy-requirements.txt`、`base/build-requirements.txt`、`base/test-requirements.txt`、`base/pytest.ini`、`base/conftest.py`；`base/docs/source/kinds_of_types.rst:570–655`、`base/docs/source/metaclasses.rst:1–106`；`base/mypy/checker.py` 的 if 调用、类型比较、条件缩窄和目标类型提取相关片段；`base/mypy/checkexpr.py:4159–4197`；`base/mypy/meet.py` 的缩窄、重叠及 Type 交集片段；`base/mypy/__main__.py:1–23`、`base/mypy/fastparse.py:1–75`；`base/test-data/unit/README.md:1–175`、`base/test-data/unit/check-isinstance.test:2540–2673`、`base/mypy/test/testcheck.py:1–220`、`base/mypy/test/config.py:1–20`、`base/mypy/test/testtypes.py:800–820,940–971`。

另对上述源码及 `base/test-data/unit/check-type-checks.test`、`base/test-data/unit/check-narrowing.test` 做关键词检索，对 typeshed、测试桩目录做文件名枚举；没有逐一阅读这些文件全文。初次全包文件名列表及部分合并输出被工具截断；本报告采用的关键源码片段随后均按范围读取。曾尝试读取不存在的 `base/base_identity.json`，收到“文件不存在”，随后读取了公开包根目录的正确文件。

未查：完整 binder 实现、全部语义分析/子类型调用者、全套元类测试及所有边界组合、依赖实际安装状态、构建产物、真实 shell/actor 运行、真实模型消息、任何私有验收材料及 Git 历史。`user_prompt.txt` 只是当前函数静态渲染；`base/` 是指定提交导出而非完整运行容器（`environment_brief.md:3–6`）。public bundle 会写入解题工作区可见路径，未出现在渲染用户消息中不能据此称其不可见（`environment_brief.md:23–24`）。本次读取范围是协作约定，不是文件权限隔离或预训练无污染证明。

关键待核实项：真实解释器/依赖/测试入口可用性；实际输入中原禁止修改测试指令的适用及官方文件恢复范围；超出示例的元类相关缩窄精度边界。前两项需要 actor/协调者核验，最后一项应与明确核心需求分开评估。
