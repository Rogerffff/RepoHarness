# B3 单题公开要求审查：python__mypy-10174

本报告只依据指定角色卡及本题公开包；路径引用均相对 PUBLIC_DIR。没有读取其他题、私有材料、gold、历史结论、镜像克隆或网络资料，没有运行或导入项目、安装依赖、修改 base、调用 Docker/SSH 或查询配额。下面所有开发命令都是**建议，未执行**。

PUBLIC_DIR：`${REPO_ROOT}/runs/swegym_quality_batch03_20260921_v1/public/python__mypy-10174`

公开身份：`base_commit=c8bae06919674b9846e3ff864b0a44592db888eb`；`base_identity.json:3-17` 记录 1466 个已导出 blob、无 gitlinks、无未物化 LFS 指针、无导出的 Git 元数据。这是包内身份声明及静态源码，不是实际解题容器已验结果。

## 1. 需求表

| 要求或应保留行为 | 依据 | 确定程度 |
| --- | --- | --- |
| 同时启用 `no-strict-optional` 与 `strict-equality` 时，题面 `x: Optional[Any]`、`if x in (1, 2)` 不应报告 non-overlapping container check。 | `user_prompt.txt:3-15`；相同问题保存在 `public_bundle.json:1` 的 `problem_statement`。 | 明示，是最小验收行为。 |
| 启用 strict optional 后，这个例子继续不报错。 | `user_prompt.txt:17`。 | 明示的既有正确行为。 |
| 仍保留 strict equality 对真正不重叠的 equality、identity、container 比较的检查，包括 `in` 与 `not in`。不能用整体关闭诊断完成修复。 | `base/docs/source/command_line.rst:562-580`；`base/test-data/unit/check-expressions.test:2397-2462,2764-2769`。 | 公开接口及旧测试可合理推知。 |
| `Any` 与其他类型比较不能仅因类型不重叠而告警；这一原则不应因去除可选性后才暴露出 `Any` 而失效。 | `base/mypy/checkexpr.py:2293-2308` 明确写出 Any overlaps with everything；`base/mypy/meet.py:164-176`；`base/test-data/unit/check-expressions.test:2514-2524`。 | 一般 `Any` 行为已有明确代码/测试约定；扩展至题面这个组合有强公开依据。 |
| 保留默认 `strict_optional=True`、`strict_equality=False`；保留题面内联选项的作用。 | `base/docs/source/config_file.rst:468-476,603-609`；`base/mypy/options.py:151,182`；`base/docs/source/inline_config.rst:6-20,29-43`。 | 公开接口约定。无需新增选项或改变默认值。 |
| 保留 `None` 比较例外、无其他交集的两个 Optional 类型仍可判不重叠，以及 bytes 特例、数值提升、合法自定义 `__eq__`、已有操作数错误的处理。 | `base/mypy/checkexpr.py:2225-2229,2241-2253,2293-2353`；`base/test-data/unit/check-expressions.test:2464-2512,2526-2625`。 | 公开代码与测试可合理推知。不是所有带 Optional 的比较都应无条件放行。 |
| `Optional[Any]` 出现在右侧元素类型、其他容器、`==`/`is` 或其他联合类型中的完整行为矩阵。 | 题面只列 tuple 成员检查；共享路径见 `base/mypy/checkexpr.py:2191-2261,2353`，联合类型原则见 `base/mypy/meet.py:130-218`。 | 同一 `Any` 语义应一致；题面没有逐项列出全部新回归用例。不能把某个未声明的精确内部实现或矩阵当明示要求。 |

问题不要求执行被分析的 Python 片段。它是静态类型检查器的误报：题面中未赋值的 `x` 可用于这种分析；单元测试文档也说明测试片段只做类型检查、不执行（`base/test-data/unit/README.md:28-38`）。

## 2. 合理实现范围

公开要求以诊断行为为核心，没有指定修改文件、辅助函数名、补丁形状或算法步骤。可以在通用类型重叠判断中维持规范化前后的 `Any` 语义，也可以在比较分析路径中采用一致的类型处理；只要修复题面组合并保留上述接口及合理相邻行为，都有接受空间。这是实现位置的可替代性分析，不是修复建议或标准答案推测。

如选择修改共享函数，需考虑调用者：`is_overlapping_types` 除严格比较外，还参与类型收窄/可达性判断，例如 `base/mypy/checker.py:4984-4987`。因此不能仅为了压掉 tuple 成员检查的消息，将所有 overlap 检查都改成宽松结果。相反，题面也未要求一次性重构所有重叠、子类型或联合类型算法。

外部约定是现有选项名称和默认值，以及仍应出现的诊断种类/格式。`base/mypy/messages.py:990-996` 生成 `Non-overlapping … check` 并使用 `COMPARISON_OVERLAP`；公开文档列出错误码 `comparison-overlap`（`base/docs/source/error_code_list2.rst:87-105`）。题面成功条件是这条错误消失，不是改写错误措辞、添加 ignore 注释或改变用户输入。

## 3. 初态线索与疑义

公开材料足以启动正常开发调查，不需要外部附件才能理解目标：

1. 题面完整给出两项内联配置、导入、类型注解和触发行（`user_prompt.txt:6-15`）。内联配置优先于其他配置（`base/docs/source/inline_config.rst:13-14`）；做 strict optional 对照时需要改掉片段中的 `no-strict-optional`，不能只在命令行加反向参数。
2. `visit_comparison_expr` 将 `in`/`not in` 送入容器类型分析及 `dangerous_comparison`（`base/mypy/checkexpr.py:2176-2229`）；固定长度 tuple 的元素类型有明确调用路径（`base/mypy/checker.py:3514-3534`）。
3. `dangerous_comparison` 在 strict equality 未开启时返回 False，最后调用 `is_overlapping_types`（`base/mypy/checkexpr.py:2310-2311,2353`）。
4. 静态可见一个强调查线索：`is_overlapping_types` 先处理直接 `AnyType`，再在 non-strict optional 模式中简化联合类型（`base/mypy/meet.py:164-176`）；`relevant_items` 去除 None，`make_union` 对单项返回该项（`base/mypy/types.py:1777-1783,1801-1806`）。这使 `Optional[Any]` 在检查顺序中可能从联合类型变为 `Any`。后续 proper-subtype 并不把 Any 当任意类型的兼容通行证（`base/mypy/subtypes.py:1132-1140,1218-1219`）。这是静态根因候选，不是已经捕获的运行轨迹。
5. 现有公开测试已覆盖 Any、strict optional 开/关、tuple 成员检查、真不重叠类型等邻近情形（需求表引用）。所读的这组 `check-expressions.test` 用例未见题面完整 `Optional[Any] + no-strict-optional + tuple in` 组合；这一观察不等于断言全仓不存在任何等价用例。

真正尚缺的是运行证据：实际 Python 版本、依赖/解析器是否兼容、actor 是否导入 `/testbed` 源码而非另一套已编译包、测试收集和 stub 读取能否完成。这些会阻碍实际运行时的验证，但不能据静态包缺证据判定开发不可行。已见材料没有表明需要数据库、GPU、外部服务或特殊数据集。

外链主要是一般安装、贡献和类型说明。解决本题核心需求所需内容已在包内；未发现必须补齐的公开外链/附件。没有读取这些外链，也没有请求未来代码或历史。完整联合类型/别名/TypeVar 传播仍可按实现范围继续正常查代码，不是题面缺陷。

### issue、harness 指令与环境声明分开记录

| 层次 | 公开内容 | 本次审查中的处理 |
| --- | --- | --- |
| issue 目标 | 修复给定配置组合下的误报，并维持 strict optional 开启时的正确行为。`user_prompt.txt:3-17`。 | 按行为审查，不引入额外环境承诺。 |
| harness 操作指令 | `public_bundle.json:1` 的 `public_hints` 要求只改 NON-TEST 源码、禁止改测试、运行窄测试、完成后简述；允许工具字段为 bash/edit，工作目录为 `/testbed`。 | 保留原指令，不自行取消。此题有合理的非测试源码修复空间；禁止改测试主要限制新增持久回归用例，不妨碍执行已有测试或用 `mypy -c` 临时复现。若该禁令不适用，可加入回归用例；两种情况下行为目标一致。 |
| 旧机制解释 | hints 声称所有测试改动会恢复、永不计分。 | 不把它当当前已核实机制。`environment_brief.md:20-26` 说明当前没有按测试文件名统一排除，仍有官方文件恢复等具体限制。实际禁令及恢复范围属于共享输入/运行条件核对项。 |
| 环境事实声明 | hints 声称 `testbed` conda 已激活，Python/pip/测试工具已指向它；bundle 给出镜像及 digest。 | 仅是公开声明/身份，不是 actor 运行验证。`environment_brief.md:3-12` 明确未验解释器、依赖、资产及实际资源。 |
| 公开材料可见性 | bundle 有 public_hints 字段；user_prompt 只渲染 issue。 | `environment_brief.md:4,25-26` 说明 bundle 会写到真实解题容器公开路径。不能因不在渲染消息内便称它不可见，也不能称已验证进入 system message。 |

## 4. 开发需求表

下表的命令编号指向下一节。**各命令均为建议，未执行；预期不是实测。** 运行位置为未来实际 actor 的 `/testbed`，不是本次静态导出目录。

| 操作 / 资产 / 服务 | 公开依据 | 环境说明支持到哪层 | 缺口与最小命令 / 预期 |
| --- | --- | --- | --- |
| 选择源码及 Python 解释器，能导入 checker | `base/README.md:64-68`、`base/setup.py:8-10,193-203`；`base/test-data/unit/README.md:126-143` 支持从源码 `python -m mypy`。 | bundle 声称已激活 conda；brief 仅声明 `/testbed` 和 actor，未提供实测。 | C1：应输出解释器和 `/testbed` 下模块路径，无 import 错误。Python 最低要求不代表任意较新版本均已验证。 |
| 运行依赖 | `base/mypy-requirements.txt:1-6`：`typing_extensions`、`mypy_extensions>=0.4.3,<0.5.0`、`typed_ast>=1.4.0,<1.5.0`、相应 types 包、`toml`；`base/setup.py:193-200`。 | 不假定可联网安装，依赖要由预置环境提供（brief:10-12）。 | C1 导入 checker/依赖；C2 实际覆盖解析与分析。缺包或旧 typed_ast 与实际解释器不兼容属于运行条件问题，不能把 import 失败当原 bug。 |
| 内联配置和 tuple/typing stubs | `base/docs/source/inline_config.rst:6-43`；`base/mypy/typeshed/stdlib/typing.pyi:16,38-40`；`base/test-data/unit/fixtures/tuple.pyi:13-16`、`typing-full.pyi:15-17,44-48`。 | 源码和 stub 文本可读，identity 声明无未导出 gitlinks；真实镜像的路径/读取未验。 | C2、C3：原配置应重现题面错误，strict optional 对照应无此误报；修复后两者均无误报。 |
| 公开窄测试及测试插件 | `base/test-data/unit/README.md:47,111-124,176-178`；`base/mypy/test/testcheck.py:26-97,110-112`；`base/conftest.py:3-11`；`base/pytest.ini:21-22`。 | 已给出测试源码与数据，但 pytest 及插件可用性未验。 | C5：应收集相应命名测试并通过；默认 `-nauto` 需 xdist，`-n0` 限制为单进程。单独通过旧测试不证明题面已经修复，仍需 C2。 |
| 旧测试依赖和可写临时目录 | `base/test-requirements.txt:1-18` 限定 pytest `>=6.1.0,<6.2.0`、xdist `<2` 等；测试会写出待检查程序（`base/mypy/test/testcheck.py:137-153`）。 | brief:9-12 声明 workspace/home 可写与默认 CPU/内存/临时空间，实际未验。 | C5 会覆盖测试收集、fixture 读取和临时文件写入；若依赖/权限失败需分别报告。无需为本题先证明全仓/Python 2 执行测试可运行。 |
| 构建、安装、外部服务 | 文档允许直接源码运行（`base/test-data/unit/README.md:126-143`）；mypyc 编译是可选分支（`base/setup.py:77-85`）。 | 公网依赖下载不在承诺内；无本题特定服务声明。 | 最小验证不要求新安装、C 编译、文档构建、Docker、SSH 或外部 API；无必需构建命令。C1 需确认编辑源码确实被加载，已有二进制产物状态未验。 |

### 最小验证命令（全部为建议，未执行）

每组预设实际 actor 工作目录为 `/testbed`。不在静态导出包运行；不执行下面的被检查程序本身。内联设置在代码里显式指定，避免对照被题面原选项覆盖。

**C1 — 建议，未执行：最小导入与环境路径核验。**

```bash
PYTHONPATH=/testbed python -c 'import sys, mypy.checkexpr, mypy.meet, typed_ast.ast3, typing_extensions, mypy_extensions, toml; print(sys.executable); print(sys.version); print(mypy.checkexpr.__file__); print(mypy.meet.__file__)'
```

预期导入成功并从预期源码树加载。此步不证明完整测试依赖齐全；若显示其他安装位置或编译扩展，需要先核对其是否覆盖源码编辑。

**C2 — 建议，未执行：题面最小复现。**

```bash
PYTHONPATH=/testbed python -m mypy --no-incremental --show-error-codes -c '# mypy: no-strict-optional, strict-equality
from typing import Any, Optional
x: Optional[Any]
if x in (1, 2):
    pass
'
```

预期原始版本复现 `Non-overlapping container check`，通常带 `comparison-overlap`；修复后该片段应无诊断并成功退出。实际措辞、类型展示与返回码尚未观察。

**C3 — 建议，未执行：strict optional 开启的对照。**

```bash
PYTHONPATH=/testbed python -m mypy --no-incremental --show-error-codes -c '# mypy: strict-optional, strict-equality
from typing import Any, Optional
x: Optional[Any]
if x in (1, 2):
    pass
'
```

预期原始及修复后都无误报。这里替换内联选项，而不是只加命令行 `--strict-optional`。

**C4 — 建议，未执行：真不重叠类型与禁用 strict equality 的边界。**

```bash
PYTHONPATH=/testbed python -m mypy --no-incremental --show-error-codes -c '# mypy: no-strict-optional, strict-equality
if 1 in ("x", "y"):
    pass
'
```

预期原始和修复后仍报告 non-overlapping container check。再将这一代码字符串首行替换为 `# mypy: no-strict-optional, no-strict-equality` 重跑同一命令（**建议，未执行**），预期不报告这类可选诊断。边界依据是公开选项语义和 tuple 旧测试，不是要求额外的接口。

**C5 — 建议，未执行：已有公开严格比较回归测试。**

```bash
PYTHONPATH=/testbed python -m pytest -n0 /testbed/mypy/test/testcheck.py -k 'StrictEquality or EmptyListOverlap'
```

预期相关既有用例被收集并通过（包含预期错误比对，不能把测试代码中的 `# E:` 误当测试失败）。这些旧用例主要检查行为未退化；C2 才直接验证题面故障。若修改共享重叠函数，应按实际影响再挑选类型收窄等公开用例；本审查没有运行或穷尽这些扩展测试，也不以全仓测试成功为前提。

## 5. 阅读范围与限制

实际打开全文或局部内容的文件：

- 角色卡：指定的 `roles/public_reader.md`（仅该卡，没有读取其父目录资料）。
- 包根：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`base_identity.json`。
- 安装/测试入口：`base/README.md`、`base/CONTRIBUTING.md`、`base/test-data/unit/README.md`、`base/setup.py`（局部）、`base/mypy-requirements.txt`、`base/test-requirements.txt`、`base/pytest.ini`、`base/conftest.py`、`base/mypy/test/testcheck.py:1-155`。
- 行为文档：`base/docs/source/inline_config.rst`；`command_line.rst` 的 Optional/strict equality 段；`config_file.rst` 的两个选项段；`error_code_list2.rst:83-118`。
- 调查源码：`base/mypy/checkexpr.py:2170-2430`；`base/mypy/meet.py:110-365`；`base/mypy/types.py:1735-1815`；`base/mypy/checker.py` 的容器元素分析、收窄和 overlap 包装器局部；`base/mypy/messages.py:985-1009`；`base/mypy/subtypes.py` 的 proper-subtype 说明和 Any 处理局部。
- 公开测试/资产：`base/test-data/unit/check-expressions.test:2390-2627,2675-2773`；`base/test-data/unit/fixtures/tuple.pyi:1-47`；`base/test-data/unit/fixtures/typing-full.pyi:1-80`。

另做了仅限本题包的文件名清单、定向文本检索：`base/mypy/options.py`、`base/build-requirements.txt`、`base/tox.ini`、`base/mypy/test/testtypes.py`、`base/mypy/typeshed/stdlib/{typing,builtins}.pyi`；在 `base/test-data/unit/` 与 `base/mypy/test/` 搜索 strict-equality / Non-overlapping container / overlap 相关入口，并检索过 `check-optional.test`、`check-unsupported.test`。命中其他测试文件仅用于定位，没有将其当全文已审；大清单/部分检索输出有截断，因此不宣称完整资产或全仓覆盖。

未查项包括完整的类型分析传播、所有 overlap 调用者、其他测试全文、完整 requirements 的实际安装状态、真实 shell/CLI 消息、解释器与系统包权限、容器资源和运行结果。`user_prompt.txt` 只做静态渲染阅读；base 是公开 commit 的导出，不是完整运行容器。本次没有私有材料暴露，但这种阅读边界是协作约定，不是权限隔离或预训练无污染证明。

关键未知：实际 actor 能否按 C1–C5 使用指定源码、兼容依赖和 stubs；旧测试编辑禁令及官方文件恢复的实际适用范围；若扩大修复到共享 overlap 函数，其相邻类型收窄影响还需针对实现继续检查。没有发现需要先向出题者补问才能启动的核心行为歧义。
