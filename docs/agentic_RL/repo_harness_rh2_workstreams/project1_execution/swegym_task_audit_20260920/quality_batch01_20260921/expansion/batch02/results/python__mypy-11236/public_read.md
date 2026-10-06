# python__mypy-11236：独立公开阅读记录

本次只作静态公开审查，没有实现修复，没有运行项目代码、测试、安装、容器或网络请求。材料根目录为 `runs/swegym_quality_batch02_20260921_v2/public/python__mypy-11236/`；下文除角色卡外的文件引用均相对此目录。未使用继承 cwd 的另一份 worktree。

公开任务定位为 `python/mypy`、base commit `209a7193feb4bbfa38d09232b0a5a916e9d2e605`（`user_prompt.txt:1`；`public_bundle.json:1`）。`base_identity.json:3-12` 声明源码导出对应该提交，1722 个跟踪条目均已物化，无 gitlink、未物化 LFS 指针或导出的 Git 元数据；这是材料自身的身份声明，本次没有独立核对容器提交。

## 1. 需求、保持项与歧义

题目标题说“Cannot infer return type”，但示例的函数返回类型已经显式标注。实际要修复的是：在该返回类型提供的上下文中，推断返回表达式 `(1,)` 的元素类型并检查兼容性，而不是自动推断一个未标注函数的返回签名。

| 行为 | 公开依据与明确程度 | 审查判断 |
| --- | --- | --- |
| `does_not_work` 返回 `(1,)` 时，应接受它符合 `Union[Tuple[str], Tuple[Literal[1]]]` | 明示示例和错误描述，`user_prompt.txt:14-21`；期望输出栏为空，见 `:22-23` | 尽管期望栏未填，修正这一误报的目标足够清楚。无需另行提供答案型材料。 |
| 同一函数的 `("a",)` 分支仍然合法 | 示例 `user_prompt.txt:15-16`；联合类型逐分支检查 `base/mypy/subtypes.py:114-143` | 是应保留的行为；修复不能只强行选取 Literal 分支。 |
| 不符合任一返回分支的 `(2,)`、错误元组长度仍应报错 | 可由 Literal 的精确值含义、返回类型检查、元组子类型规则合理推知：`base/docs/source/literal_types.rst:6-9`；`base/mypy/checker.py:3362-3371`；`base/mypy/subtypes.py:350-355` | 题面未逐例列出，但“消除误报”不授权把任意整数或元组一概判为兼容。 |
| 直接 Literal 返回和直接 `Tuple[Literal[...]]` 上下文的既有接受/拒绝行为保留 | 旧测试 `base/test-data/unit/check-literal.test:1448-1467,1512-1526` | `return 1` 可符合 `Literal[1]`，`return 2` 不可；元组各位置的 Literal 值不能被忽略。 |
| 无上下文时仍按普通类型推断，不把所有整数常量或普通元组永久收窄成 Literal | 文档明确为兼容性保留普通变量推断，`base/docs/source/literal_types.rst:93-107`；旧测试 `base/test-data/unit/check-literal.test:1521-1523` | `d = (1, 2)` 的已记录结果是 `Tuple[int, int]`。全局改变常量默认推断不是本题要求。 |
| 已支持的单一元组候选、变长元组上下文、长度不匹配处理和星号展开保留 | 旧测试 `base/test-data/unit/check-tuples.test:1207-1233,978-1003`；源码 `base/mypy/checkexpr.py:3317-3358` | 共享推断路径的修改应考虑这些回归边界。星号展开的新 Literal 能力并未由题面单独要求。 |
| 同样问题在显式变量注解或函数参数上下文中保持合理一致 | 可由双向推断文档 `base/docs/source/type_inference_and_annotations.rst:130-158` 和共享 `accept` 入口 `base/mypy/checkexpr.py:3902-3930` 推知 | 是自然的通用修复方向；题面的直接验收示例仍是函数返回。不能仅凭 issue 声称所有容器、所有上下文都必须全面增强。 |
| 联合项顺序颠倒后仍接受同一个合法值 | 联合类型按任一成员匹配，`base/mypy/subtypes.py:114-143`；题面没有规定优先分支 | 可以合理要求此基本语义；内部算法不应无条件依赖第一个分支。 |
| 多个同长元组、不同长度、固定长度与 `Tuple[T, ...]` 混合、嵌套元组、多个元素的关联、`Any`、TypeVar、别名和星号表达式的全部新推断结果 | 代码有相关机制，题面只给出两个单元素固定元组，`user_prompt.txt:14-18`；现有候选筛选 `base/mypy/checkexpr.py:3306-3315` | 仍有合理实现空间。需要普通代码调查和针对所改路径的验证，不能把未陈述的完整扩展矩阵当成唯一必需规格。 |

没有要求新增 CLI 开关、公共 helper 名称、输出文件或修改用户程序。`Literal`、`Tuple`、`Union` 的注解意义和原有错误判定具有公开约定；示例修复后无需输出精确的中间 `reveal_type` 文本。失败样例的诊断仍应有意义，但题面没有规定调整推断后错误消息里必须继续显示 `Tuple[int]` 还是更精确的 Literal。

## 2. 三类输入分开记录

| 类别 | 可见材料 | 对本次审查的含义 |
| --- | --- | --- |
| Issue 需求 | `user_prompt.txt:3-30`，重复存于 `public_bundle.json:1` 的 `problem_statement` | 修复上述兼容性误报；报告使用 Python 目标版本 3.7，列出 strict-optional、warn_return_any 和 strict。没有填写实际 Python/mypy 版本，只称在 Git master 也出现。 |
| Harness 操作指令 | `public_bundle.json:1` 的 `public_hints`：在 `/testbed` 工作、修改 NON-TEST 源码、禁止改测试、窄测、完成后简述 | 是公开可读字段；没有出现在渲染题面并不等于求解者看不到。仓库贡献说明鼓励添加测试（`base/CONTRIBUTING.md:95-101`），不能据此擅自取消 harness 的原禁止指令。 |
| 待核验的环境事实 | 同字段称 conda `testbed` 已激活；bundle 给出镜像名及摘要；`environment_brief.md:3-12,20-26` | 不能视作实际 actor 环境已通过，亦不能确认该字段进入了 CLI system message。 |

原提示解释“所有测试修改都会恢复、永不计分”。`environment_brief.md:21-25` 明确说明这已不能代表当前机制：没有按测试文件名统一排除，仍有官方文件恢复等具体限制。本次没有读取私有调查，因此不判断本题哪些文件实际受恢复机制影响。

若“禁止改测试”适用于实际求解，本题仍存在直接修改 `mypy/checkexpr.py` 等非测试源码、用 CLI `-c` 输入和既有测试验证的路线，不需要以修改测试作为修复前提。若该指令不适用，则在 `check-literal.test` 添加回归用例符合仓库惯例，但这须由运行方核对实际指令，不能由公开审查自行授权。此处登记的是共享输入/运行条件问题，不据旧机制文字判题目无效。

## 3. 初态调查入口与合理实现范围

静态阅读得到一条直接的解释链，尚未通过执行复现确认：

1. `base/mypy/checker.py:3313-3334` 取已声明的返回类型，并作为上下文传入 `expr_checker.accept`。
2. `base/mypy/checkexpr.py:3902-3930` 把上下文压栈，访问表达式，再记录结果类型。
3. `visit_tuple_expr` 在 `base/mypy/checkexpr.py:3306-3315` 筛选同长度固定元组或普通变长 tuple 候选；仅在候选恰好为一个时选择上下文。示例中两个分支都含一个元素，所以候选数为二；原代码注释明确说无法决定上下文。
4. `base/mypy/checkexpr.py:3317-3355` 因而没有为该元素取得位置上下文。`infer_literal_expr_type`（`:2085-2114`）只在 Literal 上下文中生成 `LiteralType`；否则产生普通实例类型并记录原字面值。
5. `base/mypy/typeops.py:652-667` 已可识别含 Literal 成员的联合上下文。末端返回检查仍调用普通子类型规则（`base/mypy/checker.py:3362-3371`）；联合目标逐成员检验、固定元组逐位置检验（`base/mypy/subtypes.py:114-143,350-366`）。现有实例对非实例目标的处理也解释了仅保留原字面值不等同于成为 Literal（`:243-297`）。

至少有两种值得正常开发验证的实现路线，不应把某个 helper 名称或唯一代码布局当作需求：

- 在元组表达式推断阶段，为多个合适候选构造位置级上下文，使题例中的元素可看到 `Union[str, Literal[1]]`，再对推断出的真实元组类型执行原来的完整联合兼容性检查。这能利用已有 Literal 上下文识别。它不能把原联合目标永久改写为各位置的独立联合，也不能直接把期望类型当作表达式结果。
- 逐候选进行受控的上下文推断，选择能够通过完整兼容性检查的候选/推断结果，失败时保留正常诊断。此路线要处理错误暂存、类型缓存和多候选歧义，具体实现仍需读相关辅助机制，但 issue 没有禁止它。

两条路线都需要实测才能宣称正确。位置级联合可能丢失元组元素之间的分支关联；逐分支尝试也可能产生顺序相关的上下文推断。共同边界是保持完整分支语义。例如目标 `Union[Tuple[Literal[1], str], Tuple[Literal[2], int]]` 不应因把两个位置分别放宽而接受 `(1, 1)`。此例用于说明既有联合语义约束，并非声称题面已经给出了该额外验收用例。

只修改错误消息、无条件使用 `Any`、放宽整数对 Literal 的全局子类型关系、硬编码函数名/数值，或要求用户改成 cast，均不能正常满足本题修复目标。

公开材料可以定位复现和源码入口。缺少原作者精确运行版本不会阻止从指定 base 开始调查；包内版本文件声明 `0.920+dev`（`base/mypy/version.py:8`），不等于容器实测版本。现有资料不需要补充外部附件或未来修复。已读旧测试中的 issue 7399 链接（`base/test-data/unit/check-literal.test:2690-2694`）涉及 Final 元组的另一处已记录限制；未访问，解决题面示例不以该讨论为前提。公开祖先历史没有导出，本次无需请求。

## 4. 开发条件与建议验证

以下全部是建议条件和建议命令，未执行。正式运行时以实际 actor 身份、工作目录 `/testbed` 执行，不能用本机静态导出已可读取来替代运行证明。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口与最小验证 |
| --- | --- | --- | --- |
| Python 执行器及正确源码导入 | `base/setup.py:8-10,193-200` 要求 Python ≥3.6；`base/mypy/fastparse.py:48-82` 区分内置 ast 与 typed_ast | 声称有已激活 conda；`environment_brief.md:9-12` 要求 actor 核验 | 实际版本、可执行路径、扩展模块是否遮蔽正在修改的 `.py` 均未知。用建议命令 A 打印解释器和 `mypy.checkexpr.__file__`。README 的 Python ≥3.5 文字（`base/README.md:68`）落后于 setup 要求，采用后者。目标 `--python-version 3.7` 与运行 mypy 的宿主版本是两回事。 |
| 运行依赖 | `base/setup.py:193-199`；`base/mypy-requirements.txt:1-4`：typing_extensions、mypy_extensions、tomli；旧宿主 Python 的解析路径需 typed_ast | 镜像名可见，未列已安装包或证明导入成功 | 用 A 实际加载源码。Python ≥3.8 的此 Python 3 解析路径可用内置 ast；测试依赖文件仍列 typed_ast。若缺包，需要已有兼容依赖或离线包源，不能假定公网下载。 |
| 类型信息资产 | `base/mypy/typeshed/stdlib/typing_extensions.pyi:45-49`；旧测试使用 `base/test-data/unit/fixtures/tuple.pyi:1-48` 及 lib-stub；`base/mypy/test/testcheck.py:163` 启用内置 fixtures | 本包有相关源码和 stub；`base_identity.json:9-10` 无 LFS/gitlink 缺项 | CLI 复现与 fixture 测试用的 stub 集不同，建议分别执行 B 和 D。未核验真实 `/testbed` 内资产可读性。 |
| 窄范围公开回归测试 | `base/test-data/unit/README.md:111-143,176-178`；`base/mypy/test/testcheck.py:70,87,112-137`；`base/pytest.ini:21-22` | 默认资源声明 2 CPU/4 GiB/PID512，未实测 | 需要 pytest 6.2.x、pytest-xdist 等兼容测试依赖（`base/test-requirements.txt:9-16`）。D 显式 `-n0` 避免默认多进程；不要直接将 `.test` 当普通 pytest Python 模块。未验证收集成功或耗时/内存。 |
| 临时文件、缓存和工作目录 | `base/mypy/test/data.py:267-272` 的 TemporaryDirectory；`base/mypy/test/config.py:14-17`；`base/mypy/test/testcheck.py:150-155,174-181` | 声称 actor 可写 workspace/home，tmp 1 GiB/home 256 MiB，具体仍待验 | pytest 仍需临时文件写权限和少量空间。B/C 禁用持久缓存；无法因此宣称所有测试完全不写盘。 |
| 构建/安装 | `base/test-data/unit/README.md:126-143` 支持直接以源码模块运行；`base/setup.py:77-85,155-156` 默认不启用 mypyc；`base/pyproject.toml:1-6` 给出可选安装构建依赖 | 解释器/系统包写权限待核验；无公网依赖保证 | 这个纯 Python 推断修复没有独立 C 编译或打包的必要前提，A/B 即最小加载冒烟。仅当实际环境必须重装/重建才需额外构建工具和资产，本次不把全量安装、mypy 自举、mypyC 编译列为最低要求。 |
| 外部服务、GPU、历史 | 示例与旧测试皆本地类型检查；`environment_brief.md:6,10,16` | 网络限模型代理及已声明内部服务；历史未导出 | 当前公开调查无必需外部服务、GPU、远程数据或祖先历史。离线时依赖缺失才形成运行阻塞；不需要向求解者暴露隐藏验收测试。 |

**建议命令 A，未执行：身份、解释器和源码加载。** 预期能确认实际 actor、工作目录和所加载模块路径；导入错误代表环境问题，不能当成 issue 已复现。

```sh
pwd
id
python -c 'import sys; import mypy.checkexpr; import mypy.build; import mypy.version; print(sys.executable); print(sys.version); print(mypy.version.__version__); print(mypy.checkexpr.__file__)'
```

**建议命令 B，未执行：完整题面最小复现。** 参数依据 `user_prompt.txt:27` 和 `base/mypy/main.py:540,614,635,675`。依赖和资产正常时，预计原 base 在 `return (1,)` 处报告题面中的不兼容返回类型并以非零状态退出；修复后该示例应无类型错误。具体行号由 `-c` 输入决定，不以题面显示行号为约定。

```sh
python -m mypy --python-version 3.7 --strict --strict-optional --warn-return-any --no-incremental --cache-dir=/dev/null -c 'from __future__ import annotations
from typing import Union, Tuple
from typing_extensions import Literal

def does_not_work(arg: int) -> Union[Tuple[str], Tuple[Literal[1]]]:
    if arg > 5:
        return ("a",)
    else:
        return (1,)
'
```

**建议命令 C，未执行：负例防止过度放宽。** 原 base 和合理修复均应拒绝 `(2,)`；不能用吞掉返回类型错误的办法使 B 通过。

```sh
python -m mypy --python-version 3.7 --strict --no-incremental --cache-dir=/dev/null -c 'from typing import Union, Tuple
from typing_extensions import Literal

def invalid() -> Union[Tuple[str], Tuple[Literal[1]]]:
    return (2,)
'
```

**建议命令 D，未执行：公开旧测试的窄回归集。** 依据上面直接读取的 case 名称选择，不改测试文件。环境正常时预计原 base 与修复版均保持这些旧用例通过；测试中的错误注释是预期诊断，出现它们不等于 pytest 失败。若所选测试收集为空，应先查收集环境，不应报告测试通过。

```sh
python -m pytest -n0 -q mypy/test/testcheck.py -k 'testLiteralInferredInReturnContext or testLiteralInferredInTupleContext or testTupleWithUnionContext or testTupleWithVariableSizedTupleContext or testTupleWithUndersizedContext or testTupleWithOversizedContext or testTupleWithStarExpr'
```

若实现显著改变通用 Literal/元组路径，**建议命令 E，未执行**，可扩到同一公开模块中的相关 case，而非先运行全仓：

```sh
python -m pytest -n0 -q mypy/test/testcheck.py -k 'Literal or Tuple'
```

B/C 都用命令行字符串输入，不需要修改仓库测试；D/E 只运行已存在的测试。上述命令的预期现象均来自静态资料，不是运行结果。

## 5. 实际阅读与暴露记录

先完整读角色卡，再读 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`，随后才查 `base/`。本次未读其他题、私有材料、评分文件、gold、history、批次 manifest、批次结论或其他角色产物；未查 Git 历史、未来代码、PR、外网或共享镜像克隆。无已知私有暴露需要登记或换人。

实际打开或摘读的文件如下；区间表示有目的的相关片段，不表示全仓逐行审阅：

- 唯一目录外读取：任务指定的 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/roles/public_reader.md` 全文。
- 公开包装：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json` 全文；`rg --files` 查看了本题公开目录的文件名列表，输出被截断，没有据此宣称完整审阅所有文件。
- 核心源码：`base/mypy/checkexpr.py` 的 2045-2145、3230-3375、3880-3965 及相关名称检索；`base/mypy/checker.py` 的 3290-3415 及返回检查检索；`base/mypy/typeops.py` 的 640-675、770-815；`base/mypy/subtypes.py` 的 45-145、180-302、325-366（首次合并输出末尾截断，关键 240-302、332-366 后续重读）。
- 已有测试：`base/test-data/unit/check-literal.test` 的 1-108、1420-1535、2600-2710；`base/test-data/unit/check-tuples.test` 的 925-1004、1170-1265、1425-1473；`base/test-data/unit/fixtures/tuple.pyi` 全文。相关文件内还检索了 case 名、Literal/Union/Tuple 上下文。
- 文档：`base/README.md` 的 1-245；`base/CONTRIBUTING.md` 全文；`base/test-data/unit/README.md` 的 1-210；`base/docs/source/literal_types.rst` 的 1-165、360-371 及相关关键词；`base/docs/source/type_inference_and_annotations.rst` 的 122-180 及相关关键词。
- 开发与入口：`base/setup.py` 的 1-207；`base/mypy-requirements.txt`、`base/test-requirements.txt`、`base/build-requirements.txt`、`base/pytest.ini`、`base/pyproject.toml`、`base/conftest.py`、`base/mypy/test/config.py`、`base/mypy/__main__.py`、`base/mypy/version.py` 全文；`base/mypy/fastparse.py` 的 1-100；`base/mypy/test/testcheck.py` 请求 1-200 的摘读，首次合并输出有截断，后来重读 1-92，已读到 112-200 的测试执行路径。
- 仅检索而未展开完整上下文：`base/test-data/unit/check-unions.test`、`base/test-data/unit/check-inference-context.test`、`base/test-data/unit/check-functions.test`；`base/mypy/main.py` 的上述 CLI 参数；`base/docs/source/command_line.rst` 的相关参数；`base/mypy/test/data.py` 的 imports、pytest 和临时目录；`base/test-data/unit/lib-stub/typing_extensions.pyi` 与 `base/mypy/typeshed/stdlib/typing_extensions.pyi` 的 Literal/Final 定义。不能把这些检索视为通读对应模块。

未查项目其他实现细节、完整测试矩阵、真实 actor 环境、实际模型消息、容器权限/资源、已安装依赖版本及隐藏验收。`user_prompt.txt` 是静态渲染，`base/` 是源码导出，不是完整可运行容器；本报告没有证明运行环境或开发条件已可用。阅读范围限制是协作约定，不是文件权限隔离，也不是预训练无污染证明。

唯一写入为指定的本报告。关键后续未知是：actor 是否实际加载兼容解释器及这份源码、依赖与资产是否齐备、旧禁止改测试指令如何进入求解输入；多元组扩展场景的完整推断政策未由 issue 唯一指定。
