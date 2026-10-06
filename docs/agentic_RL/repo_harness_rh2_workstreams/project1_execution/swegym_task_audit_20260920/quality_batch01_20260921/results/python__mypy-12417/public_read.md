# python__mypy-12417 公开视角审查

公开材料足以定位本题的调查入口：题面给出四行复现代码和断言栈，源码中存在对应断言。明确目标是让未定义类名的类模式不再使 mypy 内部崩溃；正常的名称错误诊断和已有模式匹配行为可由公开代码与测试推知。主要待验条件是实际使用 Python 3.10 或经验证兼容的更高版本，以及该解释器能导入当前工作区源码和运行相关公开测试。本次仅静态阅读，未运行项目代码、安装依赖、修改 base 或访问网络。

下文路径相对于本题 PUBLIC_DIR；行号指本包导出文件。`public_bundle.json` 是单行 JSON，字段引用均落在第 1 行。

## 1. 需求表

| 行为 | 明确程度及依据 | 应改变或保留的内容 |
| --- | --- | --- |
| 未定义类名的 `case xyz()` 不应触发内部断言 | **题面明示**：`user_prompt.txt:3–11, 51–57`；对应代码 `base/mypy/checkpattern.py:459–466` | 修复该输入引发的内部崩溃。用户没有要求创建 `xyz`、替用户改正拼写或执行被分析程序。 |
| 保留未定义名称的正常错误 | **可合理推知**：`base/mypy/semanal.py:3788–3803, 4356–4362, 5083–5098`；`base/mypy/errorcodes.py:32` | 解析不到 `xyz` 应保留 `Name "xyz" is not defined`，错误代码为 `name-defined`。仅吞掉异常并报告成功不符合现有检查器约定。这一诊断不是题面明确给出的预期输出，而是公开实现已有行为。 |
| CLI 用普通类型检查失败表达问题 | **现有接口约定**：`base/mypy/main.py:112–141, 706–708` | 未被配置屏蔽的普通名称错误应产生非零退出状态；当前普通诊断路径为状态 1。错误代码默认不显示，需相应选项；题面没有要求改变输出格式、摘要或默认选项。 |
| 合法类模式继续检查捕获类型、位置/关键字匹配及类型收窄 | **公开测试明确**：`base/test-data/unit/check-python310.test:468–540, 659–687, 705–772` | 保留普通类、导入模块中的类、内置类、自匹配、泛型和无实参类型别名的既有行为；不应以停用类模式检查来消除崩溃。 |
| 已解析但不是类型、带类型参数的别名、模式参数错误继续诊断 | **公开测试明确**：`base/test-data/unit/check-python310.test:689–703, 812–868`；错误文本常量 `base/mypy/message_registry.py:239–248` | 保留 `Expected type in class pattern; found ...`、不允许带类型参数别名、未知属性、重复关键字、位置参数过多等现有结果。未定义名称与“已找到但不是类型”是不同情况。 |
| 出错模式之后如何恢复分析 | **有现有惯例，但题面未完全规定**：`base/mypy/checkpattern.py:467–481, 669–670`；`base/mypy/checker.py:4116–4159` | 现有无效类模式会返回不匹配结果，保留剩余主体类型并提供空捕获表；相应非类型/别名用例的分支内 `reveal_type` 没有期望输出。对未定义类的分支体、嵌套捕获和后续诊断数量，题面未给出完整要求。应保持现有公开测试，但不能把某一种新增内部恢复表示当成题面唯一答案。 |
| 限定名称、嵌套模式及错误抑制等扩展情形 | **仍有多种合理边界解释**：题面只给未限定的 `xyz()`；`base/mypy/patterns.py:120–137` 和 `base/mypy/fastparse.py:1560–1568` 表明类引用使用通用 `RefExpr` | 不崩溃这一健壮性目标自然适用于同类解析失败；但每种扩展输入的准确诊断、捕获类型及可达性并未由题面或已读测试逐项规定。不应据此额外要求完整的新模式匹配语义。 |

## 2. Issue、harness 指令与环境声明分开记录

| 类别 | 公开内容 | 审查解释 |
| --- | --- | --- |
| Issue 需求 | `user_prompt.txt:3–58` 与 `public_bundle.json:1` 的 `problem_statement` | 修复上述崩溃；没有预期补丁、强制函数名或新增接口。 |
| Harness 操作指令 | `public_bundle.json:1` 的 `public_hints` 要求探索代码、修改 NON-TEST 源码、不修改测试、可运行窄范围测试、完成后简短总结 | 原指令应独立登记，不能因未出现在 `user_prompt.txt` 中就视为不可见或无效。环境说明明确 bundle 会进入解题容器公开路径（`environment_brief.md:18–24`）。本审查自己的“仅静态读取”范围不授权执行其中的开发动作。 |
| 待验环境事实声明 | `public_bundle.json:1` 声称 `/testbed`、预激活 conda `testbed`、工具已指向该环境，并提供镜像标识及 digest | 这些不是 actor 身份的运行证据。`environment_brief.md:3–12, 24` 明确实际消息、shell、资源、解释器和依赖仍待验。题面栈含 Python 3.10 路径（`user_prompt.txt:17–19`），也不能证明容器解释器版本。 |
| 旧测试恢复解释 | 原 hints 声称测试改动都会恢复且永不计分；`environment_brief.md:18–23` 说明这一解释不能代表当前机制 | 当前无按测试文件名统一排除，仍有官方文件恢复等限制，具体影响须另核实。不能在公开审查中重述旧解释为已验事实，也不能自行取消原“禁止改测试”指令。 |

若原“禁止改测试”指令适用，本题仍有清晰的非测试源码调查入口，且可通过 CLI 内联源码复现，不必修改测试文件；该限制主要影响提交新增回归用例。若该指令不适用，开发者可增加对应的 `.test` 用例，但当前恢复机制是否保留该文件的改动仍需核对。两种情况下，都没有公开证据表明必须修改测试才能修复本题。仓库贡献指南通常建议新增单元测试（`base/CONTRIBUTING.md:72–74`），这一惯例与实际任务指令的适用关系属于共享输入问题。

## 3. 合理实现范围

可以接受在模式检查边界处理无法解析的引用，也可以接受在语义分析与模式检查之间传递可识别的错误状态；前提是正常名称错误仍可报告、类型检查能完成、已有合法模式及既有诊断不回退。这里只描述行为上等价的实现范围，不指定修复代码。

公开接口要求 `PatternChecker.accept` 返回包含匹配类型、剩余类型和捕获映射的 `PatternType`，调用者会在捕获推断和分支收窄阶段分别使用它（`base/mypy/checkpattern.py:53–62, 105–110`；`base/mypy/checker.py:4116–4159`）。现有 `early_non_match` 是一种可复用惯例；复用它、等价构造返回值或作保持行为的局部重构，不应仅因内部写法不同而被区别对待。

题面没有约定新 helper 的名字、特定修改行、补丁长度、某个新的类错误文本或拼写建议。现有名称诊断与类模式错误文本已有明确约定；保留这些约定比另造统一“无效类模式”错误更符合公开材料。对于只有错误分支才会观察到的新捕获类型/可达性差异，已读材料不足以证明某一新增策略是唯一合法实现；现有无效类分支的恢复惯例可作为优先参考。不能据此接受移除所有断言、全局吞掉异常、屏蔽名称诊断或跳过所有 match 检查。

## 4. 初态线索与疑义

静态调用链与题面一致：

1. `ClassPattern` 保存 `RefExpr`，该引用的 `node` 初始允许为 `None`（`base/mypy/patterns.py:120–137`；`base/mypy/nodes.py:1606–1619`）。
2. 语义分析先访问类引用；名字查找失败会调用 `name_not_defined` 并返回 `None`，名字表达式仅在查到符号时绑定节点（`base/mypy/semanal.py:3788–3803, 4288–4293, 4356–4362, 5083–5098`）。
3. 类型检查进入类模式后，无条件断言该节点非空（`base/mypy/checkpattern.py:459–466`），与题面栈最后一帧吻合。

这是足够具体的初态调查线索，不是运行复现证明。检查两个分析阶段之间的约定和 `PatternType` 调用者属于正常读代码工作，不是题面信息缺陷。

必要开发条件中的主要风险是解释器：本版本在 Python 3.10 及以上才加入 match AST 和 `check-python310.test` 测试文件（`base/mypy/fastparse.py:55–57, 116–137`；`base/mypy/test/testcheck.py:102–108`）。测试文件又将被检查程序的目标版本设为 3.10（`base/mypy/test/helpers.py:287–300, 392–394`）。只设置 `--python-version 3.10` 不能证明运行 mypy 的旧解释器具备所需 AST；旧解释器下相关测试可能根本未被收集。

题面没有列出作者的完整命令、mypy 配置和安装依赖版本，但四行复现、Python 3.10 栈与本地 CLI/测试说明足以构造最小验证；这些缺项当前不阻碍源码调查。已读 `check-python310.test` 类模式部分没有未定义类名的显式回归期望，定向搜索该文件也未找到 `Name ... not defined`。不能据此断言全仓从无相关测试。

没有发现复现必须依赖包外公开附件、外部项目或历史提交；暂不请求外链内容或祖先历史。真实运行时是否存在会遮蔽编辑后 Python 源码的编译扩展仍待确认：仓库默认可走纯 Python 路径，也支持 mypyc 编译（`base/setup.py:77–85, 147–160`），本包未给出镜像中的构建产物。

## 5. 开发需求表

所有下列命令均为**建议，未执行**，应在真实 actor 的 `/testbed` 中运行；这里没有宣称实际环境通过。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口与最小验证命令 | 预计现象 |
| --- | --- | --- | --- | --- |
| Python 3.10 解释器及 shell | `user_prompt.txt:17–19`；`base/mypy/fastparse.py:116–137`；`base/mypy/test/testcheck.py:102–108` | hints 声称 conda 已激活；正式 profile 说明 actor 为 agent/54321，但未逐题验实（`environment_brief.md:8–12`） | **建议，未执行**：`id`、`pwd`、`python -c 'import sys; print(sys.executable); print(sys.version)'` | 记录实际身份、`/testbed` 和解释器；优先使用 3.10。若低于 3.10，不能完成此题所需解析/测试覆盖。更高版本的实际兼容性也需测。 |
| 最小导入、当前工作区源码和运行依赖 | `base/setup.py:198–209`；`base/mypy-requirements.txt:1–4`；`base/README.md:88–90` | 只声称工具指向环境；镜像预装包、构建产物未提供（`environment_brief.md:5–6, 12`） | **建议，未执行**：`python -m mypy --version`；**建议，未执行**：`python -c 'import mypy.main; import mypy.checkpattern; print(mypy.main.__file__); print(mypy.checkpattern.__file__)'` | 正常导入；来源应对应预期工作区/构建。3.10 的运行依赖包括 `typing_extensions`、`mypy_extensions`、`tomli`。导入失败或来源不对是环境问题；`.so` 来源须确认能反映源码改动。 |
| 题面最小复现 | `user_prompt.txt:6–11, 55–57`；`base/mypy/main.py:762–766` | 没有运行证据；不需要额外服务或用户数据 | **建议，未执行**：下方 R1 | 原 base 预计进入内部错误，并在开启 traceback 后看到所给断言路径；修复后预计普通 `Name "xyz" is not defined`，无内部 traceback，普通错误退出状态 1。未实际验证。 |
| 公开数据驱动测试、pytest 及插件 | `base/CONTRIBUTING.md:57–61`；`base/test-data/unit/README.md:28–47, 103–120`；`base/test-requirements.txt:1–18`；`base/pytest.ini:21–24` | 默认 CPU 2、内存 4 GiB 等仅 profile 声明；未确认测试依赖、兼容版本和资源足够（`environment_brief.md:11–12`） | **建议，未执行**：`python -m pytest -n0 --collect-only -q mypy/test/testcheck.py -k testMatchClassPattern`；**建议，未执行**：`python -m pytest -n0 mypy/test/testcheck.py -k testMatchClassPattern` | 应收集到非零类模式用例，已有公开用例应保持通过；它们并不替代 R1 的未定义类复现。`-n0` 是仓库已有单进程用法；配置仍使用 xdist 选项，因此要确认相应插件。零收集不能算覆盖成功。 |
| 本地 typeshed、测试 fixture 与可写临时目录 | `base/test-data/unit/README.md:53–72`；`base/mypy/test/config.py:10–17`；`base/mypy/test/data.py:279–305`；`base/mypy/test/testcheck.py:153–158` | base 文件名清单含本地 builtins/typing、tuple/primitives fixture；actor 可写 workspace/home 只是说明，临时目录实测未做 | **建议，未执行**：`python -c 'import tempfile; p = tempfile.TemporaryDirectory(prefix="mypy-audit-"); print(p.name); p.cleanup()'`；上述 R1 与公开测试验证资产读取 | 可创建清理临时目录；类型检查和测试能找到自带 stub/fixture。没有证据要求 GPU、网络 API、数据库或其它外部服务。 |
| 必要时进行纯 Python 开发安装；离线依赖准备 | `base/CONTRIBUTING.md:20–35`；`base/pyproject.toml:1–6`；`base/setup.py:77–85, 147–160`；`base/build-requirements.txt:1–2` | 不假定能访问公网或下载依赖（`environment_brief.md:10`）；系统包写权限仍须核对（第 9 行） | 仅在导入/开发安装确有需要且依赖、setuptools、wheel 已具备时，**建议，未执行**：`MYPY_USE_MYPYC=0 python -m pip install --no-index --no-deps --no-build-isolation -e .` | 可用当前源树进行纯 Python 开发安装；本题不强制 C 编译。缺失依赖应作为预装包/离线资产缺口处理，不能默认公网 pip 可用。安装写权限及成功状态未验。 |

R1——**建议，未执行**：使用 CLI 内联源码，避免修改任何公开测试文件。

```bash
python -m mypy --python-version 3.10 --no-incremental --show-traceback -c 'o: object
match o:
    case xyz():
        pass'
```

该命令运行的是 mypy 对文本作静态检查，不应把复现文本作为 Python 程序执行。预计修复后的类型错误是此复现的正确结果，不能把退出状态 1 误判为修复失败。若要扩大到同一公开测试文件，**建议，未执行**：`python -m pytest -n0 mypy/test/testcheck.py::TypeCheckSuite::check-python310.test`；自定义文件收集层来自 `base/mypy/test/data.py:618–649`。本题不要求全仓测试、Python 2.7 环境或 mypyc 编译测试均可执行；一般测试指南的全套要求不应无差别升级为本题最低开发条件。

## 6. 阅读范围与限制

完整读取了角色卡、`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。实际打开以下 base 文件的相关行段，非全仓通读：

- 实现与接口：`mypy/checkpattern.py`（1–145、435–680）、`mypy/checker.py`（4080–4195）、`mypy/semanal.py`（3750–3805、4260–4310、4340–4370、4430–4480、5070–5125）、`mypy/patterns.py`（111–142）、`mypy/nodes.py`（1600–1635）、`mypy/fastparse.py`（47–140、155–211、1510–1570）、`mypy/main.py`（80–145、700–712、757–768）、`mypy/message_registry.py`（231–253）。
- 公开测试与收集器：`test-data/unit/check-python310.test`（1–85、468–542、659–775、794–870）、`mypy/test/testcheck.py`（100–160）、`mypy/test/config.py`、`mypy/test/data.py`（260–312、553–650）、`mypy/test/helpers.py`（275–300、367–400）、`conftest.py`。
- 说明与配置：`README.md`（55–98、151–190）、`CONTRIBUTING.md`（1–110）、`test-data/unit/README.md`（1–125）、`setup.py`（1–35、73–87、90–137、143–162、182–218）、`mypy-requirements.txt`、`test-requirements.txt`、`build-requirements.txt`、`pytest.ini`、`tox.ini`（1–90）、`pyproject.toml`。
- 另作定向文本检索，读取了 `mypy/errorcodes.py`、`mypy/__main__.py` 中的命中行；在 `mypy/messages.py` 等上述相关文件中搜索名称/模式入口。用 `rg --files` 查看过本包路径清单，并定位了 `test-data/unit/lib-stub/{builtins,typing}.pyi`、`test-data/unit/fixtures/{tuple,primitives}.pyi`、`mypy/typeshed/stdlib/{builtins,typing}.pyi`；未打开这些 stub 的正文。最初全包路径清单输出有截断，不作为完整资产清单证明。

未读私有评分材料、gold、旧审查结论、其它题、角色卡父目录或项目调查文档；未访问共享镜像克隆、网络或未来历史。未阅读完整测试库、所有解析/构建流程、所有第三方依赖或 fixture 内容。`base_identity.json` 未打开。

`user_prompt.txt` 仅是静态渲染，base 只是指定提交的跟踪文件导出，不是完整运行容器（`environment_brief.md:3–6`）。本报告没有验证真实模型消息、public_hints 是否进入 system message、actor 环境激活、导入成功、资产可读性、测试通过率、资源适配或官方文件恢复规则。只读范围来自协作约定，不能据此宣称文件权限隔离或预训练无污染。

关键未知：实际解释器是否达到本题 AST/测试要求；依赖、插件、编译产物是否允许测试真正执行当前源码；原“禁止改测试”指令及具体恢复限制在真实求解中的适用方式。错误模式分支的扩展恢复语义未被题面完全指定，但不阻碍处理给出的最小复现。
