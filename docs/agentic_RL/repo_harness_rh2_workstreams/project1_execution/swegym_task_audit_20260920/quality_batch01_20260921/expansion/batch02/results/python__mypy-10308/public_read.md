# python__mypy-10308：独立公开阅读

本报告仅依据角色卡和本题公开包的静态文件。公开包根目录为 `runs/swegym_quality_batch02_20260921_v2/public/python__mypy-10308/`；以下相对路径、行号均以该目录为基准。权威仓库根为 `${REPO_ROOT}`，未使用继承的 worktree 材料。

公开材料足以给出调查入口：题面提供完整的两个协议定义、mypy 参数和 traceback，末帧对应现有源码中的成员存在性断言。仍须实际复现才能确认具体中间类型和触发顺序；本报告没有运行项目代码或测试，也没有给题目作通过/淘汰判断。

## 1. 需求与保留行为

| 行为或约束 | 明确程度 | 公开依据及解释 |
| --- | --- | --- |
| 对题面的 `Vector`、`Matrix` 定义完成类型检查，不出现 INTERNAL ERROR、未处理断言或无限递归 | 明示 | `user_prompt.txt:3–32` 报告定义这两个协议即崩溃；不需要实例化对象或实际执行加法。`Vector` 有 `__len__` 和 `__add__`，`Matrix` 仅声明 `__add__`；二者通过注解关联，没有相互继承。 |
| 保留泛型、`float` 上界、显式 `self` 注解、联合参数和递归返回类型的语义 | 由题面与接口合理推知 | `user_prompt.txt:7–30`。修复目标是类型检查器，而不是要求用户删掉 `__len__`、改成 `Any` 或改写示例。 |
| 结构子类型必须具有协议要求的成员，且成员类型兼容 | 公开文档与代码已有约定 | `base/docs/source/protocols.rst:6–22`；`base/mypy/subtypes.py:531–574`。缺成员或签名不兼容不能因消除崩溃而被一律接受。 |
| 支持递归、互递归协议，并保留可推导的类型参数 | 公开文档与旧测试已有约定 | `base/docs/source/protocols.rst:384–411`；`base/test-data/unit/check-protocols.test:770–887` 同时包含合法递归、合法推断以及不兼容情况；`:791–807` 要求 `last(L())` 推断为 `int`。 |
| 保留变型检查、可写成员不变性和显式 self 的兼容规则 | 公开源码、旧测试已有约定 | `base/mypy/checker.py:1805–1830`；`base/mypy/constraints.py:440–444`；`base/test-data/unit/check-protocols.test:436–487,624–683,685–728,730–765`。不能通过跳过全部协议变型检查消除崩溃。 |
| 保留泛型方法兼容性，不能统一退化为无约束的 `Any` | 公开旧测试已有约定 | `base/test-data/unit/check-protocols.test:403–434,496–587,1957–2015` 有合法赋值、类型推断和不兼容泛型方法的预期诊断。 |
| 修复后题面必须完全无诊断、退出码必须为 0 | 未明示，不能据此定死 | 题面没有提供期望 stdout、退出码或修复后的类型揭示结果。至少应正常完成检查；是否有合法变型诊断须按现有规则核对，不能将普通类型错误与 INTERNAL ERROR 混为一谈。 |
| 必须使用某个补丁位置、函数名称或新数据结构 | 没有此约定 | 题面只描述可见行为，没有指定内部实现。`Vector`、`Matrix`、`T1`、`T2` 是复现用名称，不构成需要识别的特殊标识符。 |

Issue、harness 指令、环境声明须分别处理：

- **Issue 目标**是上述崩溃修复。报告版本 0.790、Python 3.8.5、Windows 10 和命令行参数位于 `user_prompt.txt:90–96`；解题基线则是 `user_prompt.txt:1` 和 `public_bundle.json:1` 指定的提交。不能因此把开发目标替换成另行下载的 0.790。
- **harness 操作指令**见 `public_bundle.json:1` 的 `public_hints`：调查并修改非测试源码、禁止改测试、测试保持小范围、完成后简短总结。是否进入实际 system message 尚未验证。公开 bundle 会在真实工作区可见，不能因为 `user_prompt.txt` 未包含该字段就认定不可见（`environment_brief.md:3–4,20–26`）。
- **环境事实声明**包括 `/testbed`、预激活的 conda `testbed`、工具已指向该环境等，仍待 actor 核验。原提示“所有测试修改都会恢复、永不计分”的解释不能代表当前机制；当前取消了按测试文件名统一排除，仍有官方文件恢复等限制（`environment_brief.md:20–25`）。
- 若“禁止改测试”适用，本题可在非测试的子类型/约束推断代码中修复，并用既有测试及临时复现输入验证，尚未发现它会排除必要修复。若不适用，添加小型回归用例符合项目建议（`base/CONTRIBUTING.md:95–101`、`base/test-data/unit/README.md:8–47`）。指令适用范围仍是共享输入/运行条件问题；本报告没有擅自取消它，也未检查私有恢复清单。

## 2. 调查入口与合理实现范围

静态调用链与题面基本吻合：

1. 协议定义检查调用 `check_protocol_variance`，以上下界实例调用子类型判断（`base/mypy/checker.py:1813–1830`）。
2. `is_protocol_implementation` 对正在递归检查的同一类型对直接返回 True，否则绑定 self 并比较各成员类型（`base/mypy/subtypes.py:503–558`）。`TypeInfo` 的注释明确说明这种暂时假定关系是处理递归协议的算法组成部分，并记录 `infer_constraints → is_subtype → callable subtype → infer_constraints` 的循环（`base/mypy/nodes.py:2352–2385`）。
3. 获取成员会展开泛型参数；展开联合类型又调用联合简化和 proper subtype 检查（`base/mypy/subtypes.py:674–702`、`base/mypy/expandtype.py:19–29,98–127`、`base/mypy/typeops.py:317–387`）。泛型 callable 比较会再次进入约束推断（`base/mypy/subtypes.py:827–843,1049–1086`）。
4. 结构约束推断在 `is_protocol_implementation` 返回真后逐个获取协议成员，断言两侧都存在（`base/mypy/constraints.py:378–404,425–444`）。题面 traceback 末帧 `constraints.py:437` 对应这一断言；题面没有附上最后的异常类别行，故这里只确认源码位置，不声称已观察到运行时异常对象。

**有根据的调查假设，而非已运行证实的根因：**递归检查的暂时 True 可能让“成员均已确认存在”的推断前提过强。示例中两协议成员集合不一致，且 `protocol_members` 按名称排序，`__add__` 会先于 `__len__` 处理（`base/mypy/nodes.py:2491–2501`）；比较前者可在真正检查缺失的后者前重入推断。这解释了为何应同时查看递归假设、成员存在性和约束方向，而不是把问题仅看成加法运算符解析错误。需要实际执行确认是哪次 `find_member` 返回 None。

合理修复路线至少有两类，不要求选中某个特定函数：

- 在协议关系被递归假设短路之前，建立足够可靠的成员存在性前提，例如针对协议之间的关系先核对必要成员，再进行可能递归的类型兼容检查。必须考虑已有 `__init__`/`__new__` 忽略规则，以及 `find_member` 的动态属性和 `fallback_to_any` 规则；不能把普通类与协议的所有情况都简单替换为直接声明名称的集合比较（`base/mypy/subtypes.py:531–545,586–631`）。
- 在结构约束推断路径识别“递归假设成立但成员尚不齐全”的情形，保守停止该次推断或调整进入推断的条件，使不完整关系不会触发断言。若采用这种局部防御，需证明外层兼容检查仍会拒绝缺成员/不兼容关系，不会保留误导性的部分约束或让合法推断普遍退化。

也可以重构递归状态管理，只要实现同样的可见语义并保留既有防无限递归逻辑。仅删除断言、吞掉所有异常、总是返回兼容、跳过协议变型检查、识别示例名称或全面关闭联合简化，均不能作为充分的行为修复说明。联合简化本身已有删除冗余项但保留必要 `Any`/erased 信息的约定（`base/mypy/typeops.py:321–336`）。

无需把所有递归推断扩展都纳入本题：`base/test-data/unit/check-protocols.test:889–903` 有明确标注 FIXME、并跳过的递归推断案例，它只能说明已知边界，不能当作本题新增承诺或已经通过的测试。

## 3. 初态线索、疑义与缺项

- **足够的复现材料：**题面代码自包含，直接使用标准 typing 注解，无需应用工程、数据集或远程服务。原参数全部给出。traceback 同时给出入口、成员展开、联合简化、子类型和推断路径。需要正常阅读调用者，不构成题面缺陷。
- **当前未证明的行为：**目标提交是否仍以相同方式崩溃、具体内部类型、修复后的全部诊断，以及需要保留的时间/空间性能量级。已有源码足以开始调查；这些首先需要 actor 复现，不需要隐藏验收材料。
- **平台与版本：**用户报告是 Windows/Python 3.8.5，而公开 bundle 指向 x86_64 镜像。可见触发点是类型检查算法，暂未见必须使用 Windows 的证据；不能反向宣称平台无关已经验证。使用目标提交并以 `--python-version 3.8` 固定输入语言版本，有助于区分问题本身和环境差异。
- **外链：**README、CONTRIBUTING 和协议文档有网站、PEP 与开发指南链接，未访问。现有包已包含复现、核心代码、测试格式与递归协议说明；本次未识别出阻碍开展修复的必要外链内容或附件。无需请求未来 PR、答案或历史对象。公开祖先历史没有提供，本次静态调查不依赖它。
- **资产：**文件名检查确认本题包含标准库 `builtins.pyi`、`typing.pyi`，以及相关公开测试使用的 typing/list/property fixtures；仅确认存在，未校验内容或实际读取权限。`base/.gitmodules` 为 0 行，本次未发现必须补取子模块的公开依据，也未读取任何身份/manifest 文件。

## 4. 开发条件与最小验证建议

下表及下方全部命令均为**建议，未执行**；供实际 actor 在 `/testbed` 核验。静态 base 导出不是完整运行容器，不能把本表写成环境验收结果。

| 操作／资产／服务 | 公开依据 | 环境说明支持到哪层 | 缺口及最小建议 |
| --- | --- | --- | --- |
| 正确基线源码与可写工作区 | `user_prompt.txt:1`；`public_bundle.json:1` 的提交与 workdir | `environment_brief.md:5–9` 说明是 base 源码导出，正式 profile 以 agent/54321 执行，可写 workspace/home | actor 应确认当前目录、源码导入路径和编辑生效；不能把桌面静态包当作 `/testbed`。建议下方导入检查。 |
| 可运行的 Python 与 mypy 依赖 | `base/setup.py:8–10,193–203`；`base/mypy-requirements.txt:1–6` | conda 预激活仅为提示声明；`environment_brief.md:12` 要求实际核验 | 建议优先在与报告接近的 Python 3.8 环境复现；`python_requires >=3.5` 不等于此旧版本已经在任意新 Python 上验证。缺包需预装或提供离线资产，不能假设能上公网安装。 |
| Python 3 解析器 | `base/mypy/fastparse.py:42–81`；`base/mypy/parse.py:23–35` | 未验证解释器和已安装扩展 | Python ≥3.8 的 Python 3 路径使用 stdlib ast；较旧解释器需 typed_ast。`mypy-requirements.txt` 统一列 typed_ast，但 `setup.py:194` 仅对 Python <3.8 强制，二者范围不同，不能把 typed_ast 当作本题所有环境的绝对前提。 |
| typeshed 与测试 fixtures | `base/setup.py:70–75`；`base/test-data/unit/README.md:50–77`；相关旧测试中的 fixtures 指令 | base 含跟踪文件；真实镜像资产未验证 | 本包只通过文件名确认关键资产存在。CLI 与公开测试仍需能读取它们。复现不依赖额外数据集、凭证或网络服务。 |
| pytest、收集插件与 xdist | `base/test-requirements.txt:9–13`；`base/pytest.ini:8–22`；`base/conftest.py:3–11` | 环境声称测试工具可用，但尚未执行验证 | 要求相容 pytest（清单为 ≥6.1,<6.2）及插件。建议 `python -m pytest -n0 ...`；`-n0` 限制并发，仍依赖 xdist 识别该选项。收集失败应先区分依赖问题与原 bug。 |
| 测试数据、临时目录写入 | `base/mypy/test/config.py:10–20`；`base/mypy/test/data.py:163–239,522–565`；`base/mypy/test/testcheck.py:149–174` | profile 声明 workspace/home 可写；tmp 1 GiB、2 CPU/4 GiB 为默认值，实际未验（`environment_brief.md:9–12`） | 测试会建立临时输入；需 actor 确认可写与资源足够。窄测不应直接扩为全仓测试。 |
| 安装或构建 | `base/test-data/unit/README.md:126–143` 支持从源码以模块方式运行；`base/setup.py:77–85,155–156` 显示 mypyc 编译可选 | 不假定可下载依赖；解释器/系统包写权限仍待核对 | 已有依赖时无需先构建 C 扩展、安装 mypy 或建立全仓测试环境。仅在确有缺包时安排离线依赖；未建议在此任务预先跑全量安装/构建。 |

**建议，未执行：最小导入／来源检查。** 在真实 `/testbed` 下执行：

```sh
python -c 'import sys, mypy, mypy.main; print(sys.version); print(sys.executable); print(mypy.__file__); print(mypy.main.__file__)'
```

预期能导入并显示目标工作区源码；导入失败或指向无关已安装副本是环境/源码选择问题，不能算作复现了 issue。可另用 `python -m mypy --version`（建议，未执行）记录实际版本；不要求它恰好显示报告人的 0.790。

**建议，未执行：原输入复现。** 将 `user_prompt.txt:7–31` 的代码原样保存为临时 `/tmp/mypy10308_repro.py`，不要执行该 Python 文件本身。在 `/testbed` 运行：

```sh
python -m mypy --python-version 3.8 --follow-imports=silent --show-error-codes --warn-unused-ignores --warn-redundant-casts --strict --show-traceback /tmp/mypy10308_repro.py
```

除了显式固定 Python 3.8，沿用题面参数。预期原 bug 若存在，会出现 INTERNAL ERROR/traceback，可能落在上述断言；修复后应正常完成类型检查，无内部崩溃或挂起。是否有普通诊断、最终退出码与完整输出，须实际观察并按公开规则解释。为排除已有增量缓存影响，可再加 `--no-incremental`（建议，未执行）。

**建议，未执行：最小旧测试。**

```sh
python -m pytest -q -n0 mypy/test/testcheck.py::TypeCheckSuite::testRecursiveProtocols2
```

该用例应通过且保留 `int` 推断；它不是题面复现，原 bug 可能存在而此旧测试仍通过。测试入口有公开依据：`base/mypy/test/testcheck.py:26–97,110–135` 收集 `check-protocols.test`；`base/test-data/unit/README.md:111–120` 支持按 suite/case 选择。

**建议，未执行：与此修改直接相关的窄回归集合。**

```sh
python -m pytest -q -n0 mypy/test/testcheck.py -k 'RecursiveProtocol or MutuallyRecursiveProtocols or AutomaticProtocolVariance or ProtocolVarianceWithCallableAndList or GenericProtocolsInference or ProtocolGenericInference or InferProtocolFromProtocol or GenericMethodWithProtocol or SelfTypesWithProtocolsBehaveAsWithNominal or GenericSubProtocolsExtension'
```

预期已启用的旧测试保持通过，不兼容场景仍产生既有预期诊断；带 `-skip` 的已知边界可能仍被跳过，不将跳过计为修复成功。这里按已读 case 名称筛选，不声称覆盖全部协议用例。若改动涉及更广的子类型逻辑，可在此后按实际风险扩大，不能凭本次静态阅读宣布全部检查已通过。

全仓 README 提到 Python 2.7 与 typing（`base/test-data/unit/README.md:83–100`），但题面是 Python 3 代码，窄测也不要求执行 Python 2 程序；Python 2 解析仅在对应路径导入 `fastparse2`/typed_ast（`base/mypy/parse.py:23–35`、`base/mypy/fastparse2.py:55–79`）。因此未把 Python 2 运行时列为本题最小开发条件。

## 5. 实际阅读与暴露记录

实际操作仅有静态文本读取、限定目录内的 `rg`/文件名查找，以及 `.gitmodules` 行数元数据检查；未运行 Python、mypy、pytest、项目脚本、安装器、容器、网络或模型服务。唯一写入是本报告。

实际打开/检索范围如下；范围外内容未据此宣称已审查：

- 角色卡：协调者指定的 `quality_batch01_20260921/roles/public_reader.md`，全文。
- 本题 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`，全文。必读 JSON 的 image/digest 字段随文件可见；未打开单独 manifest、身份文件或镜像内容。
- 核心源码：`base/mypy/constraints.py` 的 1–210、285–445；`base/mypy/subtypes.py` 的 503–718、816–853、1049–1093、1255–1308，另检索函数定义位置；`base/mypy/checker.py` 的 1805–1840；`base/mypy/expandtype.py` 的 1–42、91–148；`base/mypy/typeops.py` 的 317–405；`base/mypy/nodes.py` 的 2342–2390、2490–2512，另检索递归状态与成员字段。一次批量输出被截断，随后重新读取本报告依赖的关键段落；未将截断中不可见部分当作已核实依据。
- 协议公开旧测试：`base/test-data/unit/check-protocols.test` 中按关键词和 case 名搜索，并打开 403–588、624–728、730–926、1281–1315、1957–2022。检索 `base/test-data/unit/check-generics.test` 与 `check-classes.test` 的相关 case 标题；没有进一步阅读其无关用例。检索 `base/mypy/test/testsubtypes.py` 的 Protocol/constraint 关键词没有命中；猜测的 `base/mypy/test/testconstraints.py` 不存在，随后定位并只读 `base/mypy/test/testinfer.py:1–100`，没有把它当作直接协议回归证据。
- 测试入口与配置：`base/mypy/test/testcheck.py:1–190`、`base/mypy/test/data.py:163–239,504–574` 及相关搜索命中、`base/mypy/test/helpers.py:1–87` 及 parse/python2 检索、`base/mypy/test/config.py:1–20`、`base/conftest.py`、`base/pytest.ini`、`base/tox.ini:1–72`。
- 开发文档及依赖：`base/README.md` 的初次 1–220 读取有批量截断，随后重读并实际依据 95–215；`base/CONTRIBUTING.md:1–189`；`base/test-data/unit/README.md:1–210`；`base/docs/source/protocols.rst:1–70,380–422` 及关键词搜索；`base/setup.py:1–208`；`base/test-requirements.txt`、`base/mypy-requirements.txt`、`base/build-requirements.txt` 全文；空的 `base/.gitmodules`。
- 解析与 CLI：`base/mypy/fastparse.py:1–95`、`base/mypy/fastparse2.py:45–93`、`base/mypy/parse.py:1–36`、`base/mypy/__main__.py:1–23`。
- 文件名检索：仅本题 `base/` 内的 README/安装、测试配置、协议相关路径，以及前述 typeshed/fixtures 文件。未打开 `runtests.py`、`setup.cfg`、其余 README 或这些 stub 的内容，不能声称检查了全仓或全部资产。

未读取其他题、私有评分材料、gold、历史、批次结论、其他角色产物或共享镜像克隆；未发生已知越界暴露。公开隔离是本次协作范围约定，不是文件权限隔离，也不能证明预训练无污染。`user_prompt.txt` 只是静态渲染，base 只是导出源码；实际模型消息、工具配置、身份权限、资源和依赖可用性均未验证。
