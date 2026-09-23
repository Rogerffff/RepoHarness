# B3 单题公开阅读：pandas-dev__pandas-50319

这是静态公开要求审查，不是修复或运行验证。仅阅读指定角色卡及本题 `PUBLIC_DIR`；未接触本题私有材料、历史结论、其他题或共享镜像克隆。所有下列开发命令均为**建议，未执行**。未运行或导入项目、安装或下载依赖、联网、调用 Docker/SSH、查询或重置配额，也未修改 `base/`。

公开包根目录：`runs/swegym_quality_batch03_20260921_v1/public/pandas-dev__pandas-50319`。下文文件定位均相对此目录。包声明的 base commit 为 `1613f26ff0ec75e30828996fd9ec3f9dd5119ca6`（`public_bundle.json:1`、`base_identity.json:3`）。

## 1. 需求表

| 行为 | 公开依据 | 确定程度与边界 |
| --- | --- | --- |
| 调用 `guess_datetime_format('27.03.2003 14:55:00.000')` 不应抛出所报 `ValueError` | `user_prompt.txt:5-24` | **明示**。输入、直接调用和异常栈足以建立最小复现入口。标题中的 `guess_Datetime_format` 大小写与实际调用不同，但调用、栈和源码一致定位到 `guess_datetime_format`，无须新增另一名称的函数。 |
| 对该输入返回 `None`，或猜出有效格式 | `user_prompt.txt:24`；`base/pandas/_libs/tslibs/parsing.pyx:862-879` | **明示允许两种结果**。不能将“必须返回某个唯一格式字符串”提升为题面要求。若选择格式，接口约定是可供 `strftime`/`strptime` 使用的格式；`%d.%m.%Y %H:%M:%S.%f` 是符合此例语义的候选。 |
| 保持已经支持的日期、日期时间、时区和 ISO 部分日期的猜测结果 | `base/pandas/tests/tslibs/test_parsing.py:144-186`、`:196-207`；`base/pandas/_libs/tslibs/parsing.pyx:972-1014` | **由公开测试和现有接口合理推知**。旧测试对具体输入规定确切返回值，也有可解析但应返回 `None` 的时区形式；不能以一律返回 `None` 规避本题异常。 |
| 保留毫秒、微秒、纳秒位数字符串的格式猜测 | `base/pandas/tests/tslibs/test_parsing.py:315-327`；`base/pandas/_libs/tslibs/parsing.pyx:1017-1029` | **由公开测试合理推知**。3、6、9 位小数均期望 `%Y-%m-%dT%H:%M:%S.%f`。此函数返回格式，不能把辅助比较时截取六位微秒解释为本题要求更改实际时间值的精度。 |
| 保留 `dayfirst=False` 默认值、`dayfirst=True` 的偏好和相应警告行为 | `base/pandas/_libs/tslibs/parsing.pyx:862-873`、`:902-904`、`:1031-1051`；`base/pandas/tests/tslibs/test_parsing.py:189-193`、`:240-265` | **默认值明定，兼容要求可合理推知**。对目标输入若猜出日先格式，默认 `dayfirst=False` 可能产生现有 `UserWarning`；题面要求“不 error”不等于禁止这种警告。 |
| 不可猜测的既有字符串仍返回 `None`；不正确的参数类型仍可抛出 `TypeError` | `base/pandas/tests/tslibs/test_parsing.py:210-237`；`base/pandas/_libs/tslibs/parsing.pyx:906-910` | **由公开测试合理推知**。“不 error”针对所报合法字符串，不能扩张成任意对象都不得抛异常。 |
| 调用者继续识别“有格式”和“无法猜测”两条路径 | `base/pandas/core/tools/datetimes.py:129-146`、`:432-462`；`base/pandas/tests/tools/test_to_datetime.py:2294-2321` | **可合理推知**。`None` 会触发调用者的推断失败警告并进入逐项解析路径；非 `None` 走相应格式解析。题面没有要求改动这些调用者或消除回退警告。 |
| 其他点分日期、重复标点、更多小数秒形式的完整支持范围 | 题面仅给一个具体字符串；lexer 注释讨论点号既作分隔符又作小数点（`base/pandas/_libs/tslibs/parsing.pyx:789-815`） | **仍有多种合理解释**。处理同类分隔符是合理的一般化，但公开题面未给出完整新增格式集合、性能目标或对全部异常字符串的保证。无需先取得这类穷尽清单才能开发。 |

**issue、操作指令、环境声明分别记录：**

- issue 的目标是上述字符串不再因格式猜测而报错，接受 `None` 或有效格式（`user_prompt.txt:24`）。
- `public_bundle.json:1` 的 `public_hints` 要求探索原因、只改非测试源码、禁止修改测试、窄范围运行测试、完成后简要总结。这是原 harness 操作指令，不是 issue 的输出语义。
- 同一字段称 `/testbed` 下的 `testbed` conda 环境已激活，工具已指向它。这是**待验环境声明**，不是本次运行事实。
- `environment_brief.md:20-26` 明确：原“禁止改测试”指令是否用于本次实际求解待核对，审查不授权忽略；其“所有测试修改都会恢复、永不计分”的解释不能代表当前机制。当前没有按测试文件名统一排除，仍存在官方文件恢复等具体限制，逐题情况本角色不查。
- 若禁改测试指令适用，本题仍有非测试源码中的合理修复空间，且可用内联复现和既有测试验证；新增持久回归测试会受限。若不适用，新增回归测试属于合理开发手段，但测试改动本身不能替代函数行为修复。尚未发现本题必须改测试才能实现要求的公开证据；该指令的实际适用性仍是共享输入/运行条件问题。

## 2. 合理实现范围

对目标输入保守地返回 `None`，以及成功推断有效格式，都应按题面被接受。选择成功推断时，格式应描述实际的日、月、年、时间及小数秒，而非任意非空字符串；既有输出格式、类型和 `dayfirst` 约定构成兼容边界。

公开材料不规定必须修改某一行、保留 `_fill_token` 的内部实现、使用某种判断顺序或特定正则。调整 token 的处理条件、区分分隔符与小数秒，或者在无法可靠推断此类输入时以 `None` 返回，都是可以讨论的不同实现路径；这里只说明可接受范围，不提供修复代码。任何路径都要保留公开测试已规定的小数秒、类型错误、默认值和警告语义。仅让上层 `to_datetime` 吞掉异常而保留题面直接调用报错，不满足要求。

“只能猜出 `%d.%m.%Y %H:%M:%S.%f`”“必须新增某一测试名”“所有带点号的字符串均需成功猜出格式”均没有本题公开要求支持。题面允许的回退结果与选择更积极推断时的输出差异是实际实现自由度，不应被隐去。

## 3. 初态线索与疑义

**定位已经足够。** 源码中 `_timelex` 明确说明点号可能是日期分隔符或小数点，并以正则分词（`base/pandas/_libs/tslibs/parsing.pyx:789-815`）。静态推演显示，目标日期段会包含独立的 `.` token；格式匹配循环对 token 调用 `_fill_token`（`:963-969`），而该辅助函数把任何包含点号的 token 都当成秒与小数部分，以 `int(seconds)` 转换（`:1017-1028`）。对单独的 `.`，分割所得秒部分为空，和题面异常相吻合。这是**源码推演，未实际复现**。

题面 traceback 含调试 `print`，其行号与给定 base 略有偏移（题面 `967/1026`，base 的对应调用/转换为 `965/1023`）；base 不含这些调试输出。此差异不妨碍按符号和语句定位，也不构成需要加入调试输出的需求。

本次全 `base/` 的相关符号/目标字符串检索未发现目标字符串的既有公开回归测试。已有测试文件提供了兼容性基线；新复现可以直接使用题面字面量，无须附件、数据集或外部服务。查看调用者、测试参数和 Cython 构建方法属于正常代码调查，不是题面缺陷。

真正尚待确定的是实际 actor 是否能导入与当前源码一致的编译扩展，以及修改 `.pyx` 后能否重新构建和执行窄测试。缺少这些运行证据不意味着题目不可开发。当前没有必须补读的外部公开附件或公开祖先历史；没有访问题面或仓库中的任何外链，也未请求未来修复材料。

## 4. 开发需求表

下表所有命令编号均指后面的**建议，未执行**命令。建议运行地点是实际 actor 的 `/testbed` 工作区，不是本静态导出目录，也不是当前工具的默认 cwd。

| 操作 / 资产 / 服务 | 公开依据 | 环境说明支持到哪层 | 缺口 | 最小命令与预计现象 |
| --- | --- | --- | --- | --- |
| actor 身份、工作目录、Python 和本地扩展导入 | `public_bundle.json:1`；`base/pyproject.toml:24-30`；`base/pandas/_libs/tslibs/parsing.pyx:10-66` | `environment_brief.md:8-12` 描述计划 profile、可写区和待验激活；未证明实际解释器或扩展来自本 checkout | conda 是否激活；Python/NumPy/dateutil/pytz 版本；扩展是否存在及与源码一致 | A。应显示 actor 身份、`/testbed` cwd 及该工作区的 pandas/扩展路径。导入失败或导入其他安装版本是环境问题，不能当成已复现 issue。路径正确仍不能单独证明扩展已随 `.pyx` 更新。 |
| 目标函数最小复现 | `user_prompt.txt:5-24`；`base/pandas/_libs/tslibs/parsing.pyx:862-1029` | 仅有静态字符串和代码；没有执行证据 | 需在实际依赖和编译扩展中确认 | B。原态预计在 `_fill_token` 抛出空字符串转整数的 `ValueError`；修复后应返回 `None` 或可解析为 `2003-03-27 14:55:00` 的格式。现有日先警告可出现。 |
| Cython 源码修改后的本地重建 | `base/README.md:108-134`；`base/pyproject.toml:1-10`；`base/setup.py:18-49`、`:398-425`；开发文档要求修改 `_libs` 后重建 | 说明只给默认 2 CPU/4 GiB、临时空间与 home 配额；未验证本题构建资产或资源 | C/C++ 编译器、头文件、NumPy、Cython `>=0.29.32,<3`、setuptools、versioneer 等是否已备齐；工作区构建权限、空间和耗时是否足够 | C。依赖齐备时应产生可由当前源码导入的扩展。`-j 1` 同时限制本 setup 的 Cython 和编译并发；是否在资源上成功仍待验。不以安装其他 pandas wheel 替代当前源码重建。 |
| 已有格式猜测公开回归测试 | `base/pandas/tests/tslibs/test_parsing.py:144-265`、`:315-327`；`base/pyproject.toml:58`、`:287-318`；`base/pandas/conftest.py:37-48` | 未证明 pytest、Hypothesis、pytest-asyncio 等依赖可用 | 测试收集依赖、严格 pytest 配置及 JUnit 输出位置的写权限需确认；部分测试受 locale 限制 | D。应能收集并运行相关既有用例，无新失败；它们并不替代 B，因为公开旧测试未包含目标输入。缺包/插件导致的 collection error 应单列环境失败。 |
| 调用者兼容性窄验证 | `base/pandas/core/tools/datetimes.py:129-146`；`base/pandas/tests/tools/test_to_datetime.py:2294-2321` | 未验证调用者测试执行条件 | 同上，且导入完整测试模块的依赖须实际核对 | E。已有数组推断、首个非空值和全空值行为应保持；不能把通过该类测试称为目标 bug 已修复。 |
| locale 与覆盖范围 | `base/pandas/tests/tslibs/test_parsing.py:144`、`:196`；`base/pandas/util/_test_decorators.py:124-128`、`:202-205` | 未给实际 locale | 部分既有测试只在 `en_US` 下运行；目标数字字符串本身未显示需专用 locale | F，并查看 D/E 的 `-rs` 跳过原因。locale 不是 `en_US` 时相关用例会跳过；不能把这些 skip 当成该部分行为已验证。 |
| 资产、网络和服务 | 目标用例是内联字符串；`base_identity.json:8-11` 声明无未物化 LFS、无 gitlink、无 Git 元数据 | `environment_brief.md:5-12` 明确导出不包含所有运行资产，网络不假定能下载依赖 | 本题未显示需外部数据、数据库、GPU 或网络服务；预装依赖/构建产物仍待验 | 无需为该复现补充外部业务资产或访问外链。若 A/C/D 缺依赖，应登记需预置或离线提供的具体项目，不能假定公网安装可行。 |

**A — 建议，未执行：actor 与最小导入。** 以下各行均为独立建议命令，实际工作目录设为 `/testbed`。

```bash
id
pwd
python -c 'import sys, numpy, dateutil, pytz, pandas; from pandas._libs.tslibs import parsing; print(sys.executable); print(sys.version); print(numpy.__version__, dateutil.__version__, pytz.__version__); print(pandas.__file__); print(parsing.__file__); print(parsing.guess_datetime_format)'
```

**B — 建议，未执行：不修改测试文件的最小复现。** 保留异常的原始传播；不把两种允许结果收窄成唯一字符串。

```bash
python - <<'PY'
from datetime import datetime
from pandas._libs.tslibs.parsing import guess_datetime_format

text = "27.03.2003 14:55:00.000"
result = guess_datetime_format(text)
print(repr(result))
assert result is None or isinstance(result, str)
if result is not None:
    assert datetime.strptime(text, result) == datetime(2003, 3, 27, 14, 55)
PY
```

**C — 建议，未执行：仅在实际工作区需要生成或更新扩展时构建。** 以已预置依赖为前提，实际 cwd 为 `/testbed`；这里没有安排下载或安装。

```bash
python /testbed/setup.py build_ext --inplace -j 1
```

此命令的 `--inplace` 形式见 `base/doc/source/development/debugging_extensions.rst:15`，构建/安装及 `_libs` 变更后重建要求见 `base/doc/source/development/contributing_environment.rst:191-212`。本题不需要调试器或调试符号。成功构建后应在新 Python 进程重新执行 A、B；单纯编辑 `.pyx` 或仅看导入路径不足以验证修改已生效。

**D — 建议，未执行：直接函数的窄公开测试。**

```bash
python -m pytest -q -rs /testbed/pandas/tests/tslibs/test_parsing.py -k guess_datetime_format --junitxml=/testbed/pandas50319-parsing.xml
```

**E — 建议，未执行：调用者的窄公开测试。**

```bash
python -m pytest -q -rs /testbed/pandas/tests/tools/test_to_datetime.py::TestGuessDatetimeFormat --junitxml=/testbed/pandas50319-caller.xml
```

这两个命令沿用仓库 pytest 配置；显式给出 `/testbed` 下报告路径以便核对写权限。`pyproject.toml:290` 默认也会产生 JUnit 文件，`:318` 设置 `asyncio_mode`，不要把插件配置错误误判成业务测试失败。窄测试调用方式有公开开发文档依据（`base/doc/source/development/contributing_codebase.rst:803-814`）；无须先运行全仓测试。

**F — 建议，未执行：解释公开测试的 locale skip。**

```bash
python -c 'import locale; print(locale.getlocale())'
```

## 5. 阅读范围与证据限制

实际全文读取的公开文件：

- `user_prompt.txt:1-24`、`public_bundle.json:1`、`environment_brief.md:1-26`、`base_identity.json:1-18`。
- `base/README.md:1-170`。
- `base/pandas/tests/tslibs/test_parsing.py:1-327`。
- `base/pandas/_libs/tslibs/parsing.pyi:1-51`。

实际展开读取的源码、测试和文档片段：

- `base/pandas/_libs/tslibs/parsing.pyx:1-160`、`:700-1120`。
- `base/pandas/core/tools/datetimes.py:1-65`、`:125-155`、`:400-470`。
- `base/pandas/tests/tools/test_to_datetime.py:2260-2340`。
- `base/pyproject.toml:1-60`、`:287-330`；`base/setup.py:1-104`、`:398-435`。
- `base/environment.yml:1-40`、`:69-79`；`base/pandas/conftest.py:1-100`。
- `base/pandas/util/_test_decorators.py:119-135`、`:196-208`。
- `base/doc/source/development/contributing_environment.rst:1-20`、`:125-215`。
- `base/doc/source/development/contributing_codebase.rst:770-830`。
- `base/doc/source/development/debugging_extensions.rst:1-24`。

此外用 `rg --files` 枚举本题公开包的相关文件名，并在 `base/` 内检索函数名、目标字符串、构建/测试及依赖线索。只看过匹配行而未展开全文的材料包括 `base/setup.cfg`（`:65`、`:78`、`:80`）和 `base/web/pandas/pdeps/0004-consistent-to-datetime-parsing.md`（`:87`、`:89`、`:93`）；未据此将提案当作本题新要求。对 build/test 配置的关键词结果不是完整依赖审计，部分宽检索输出曾被工具截断，已对本报告依赖的关键段落另行定点读取。曾尝试检索 `base/conftest.py`，结果为文件不存在；实际读取的是 `base/pandas/conftest.py`。

唯一额外阅读的任务约束文件是指定角色卡：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/roles/public_reader.md`。未读取其父目录内容。

未查项包括：实际模型消息和 CLI system message、容器/镜像实际状态、actor 运行环境、扩展产物、完整依赖闭包、全仓测试、私有评分材料、gold、未来修复、公开祖先历史及外部网页。`user_prompt.txt` 仅为静态渲染；`public_hints` 不在其中不代表 actor 不可见，环境说明称 bundle 会写入真实工作区公开路径，但实际消息和读取行为仍待验证（`environment_brief.md:3-6`、`:20-26`）。`base_identity.json` 的校验字段是导出方提供的声明，本次未重做全树校验，也不能据此证明运行容器完整。

关键未知集中于：实际是否复现上述静态异常路径、当前源码扩展能否重建、窄测试依赖和资源是否满足、locale 跳过范围，以及原禁改测试指令与当前文件恢复限制的实际适用性。公开目标本身已给出最小调用和两种合法输出，无需猜测唯一标准实现。阅读边界是本次协作约定，不能称为文件权限隔离或预训练无污染证明。
