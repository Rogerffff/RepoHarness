# pandas-dev__pandas-48106 公开视角静态审阅

本文只依据本题公开包和指定 `public_reader.md` 角色卡。下文文件路径均相对本题 `PUBLIC_DIR`；`public_bundle.json` 是单行 JSON，字段引用统一标为第 1 行。未运行项目代码、测试、安装或构建，未联网，未读取私有材料、其它题、历史或其他角色产物，未修改 `base/`。这里的读取边界是协作约定，不是文件权限隔离或预训练无污染证明。

**1. 需求表**

| 要求或旧行为 | 明确程度与公开依据 | 审阅判断 |
| --- | --- | --- |
| 对 `pd.Series(["a", "b", "c"], dtype="category")` 执行 `s.loc[3] = 0` 应成功 | 明示：`user_prompt.txt:3–28` 给出回归描述和完整示例 | 不能仅把内部 `TypeError` 换成另一种错误；需要真正插入值。 |
| 示例结果保留 `a,b,c`，在新标签 `3` 上保存数值 `0`，dtype 为 `object` | 明示：`user_prompt.txt:10–20` | 不应把 `0` 转成字符串、缺失值或类别编码，也不应自动添加一个新类别后仍返回 categorical。 |
| 修复数值赋值扩容这一类问题，而非只匹配示例的常量 | 标题称 numeric value；代码分别处理整数、浮点、复数：`user_prompt.txt:3`；`base/pandas/core/dtypes/cast.py:650–705` | 可合理推知应调查其它数值标量、其它新标签。题面只给整数 `0` 的具体预期，不能声称已经明确穷举数值类型及所有 dtype 组合。 |
| `.loc` 和按标签的 `[]` 扩容保留已有元素、索引顺序和 Series 名称 | 仓库可推知：`base/doc/source/user_guide/indexing.rst:800–805`；`base/pandas/core/series.py:1104–1127`；`base/pandas/core/indexing.py:2089–2105,2122–2131` | 缺失标签追加路径共用该实现；名称在构造新管理器时明确保留。索引可匹配现有标签时不得制造重复元素。 |
| 普通 categorical 原位赋值仍接受已存在类别和适当缺失值，拒绝新的非缺失类别 | 代码、文档及旧测试：`base/pandas/core/arrays/categorical.py:1556–1592`；`base/doc/source/user_guide/categorical.rst:764–790`；`base/pandas/tests/series/indexing/test_setitem.py:595–629` | 扩容修复不能演变成全局放宽 categorical 的原位赋值规则。`base/pandas/tests/arrays/categorical/test_indexing.py:276–280` 也要求 `where` 遇新类别报错。 |
| 现有数值、缺失值和 object 的扩容规则应保留 | 旧测试：`base/pandas/tests/series/indexing/test_setitem.py:497–563`；`base/pandas/tests/dtypes/cast/test_promote.py:233–362,508–582` | 特别涉及 Timedelta 不被误转整数、可空数值 dtype 的精度/类型保留、NA 转换及布尔/数值类型区分。 |
| `.iloc`、`.iat` 不获得扩容能力 | 旧测试：`base/pandas/tests/indexing/test_partial.py:258–267` | 这是原有索引 API 约定，不属于应修复的错误。 |
| 新标签上的值恰好已在类别中、数值类别、ordered categorical、空 Series、各种 NA 的扩容结果 | 多种合理解释仍存在：题面只展示非空字符串 categorical 插入类别外整数；`base/pandas/core/indexing.py:2107–2127` 注释强调尽量保留 dtype，concat 文档也保留同类别组合的 dtype（`base/doc/source/user_guide/categorical.rst:808–812`） | 核心示例的 object 结果明确；其余边界应结合现有行为正常调查。公开材料不足以把某一种 categorical 保留策略宣布为本题唯一验收契约。 |

Issue 目标、harness 指令和环境声明需分开：

| 类别 | 本题公开内容 | 对此次审阅的影响 |
| --- | --- | --- |
| Issue 目标 | 上述 categorical Series 扩容回归；`user_prompt.txt:3–105` | 定义需要修复的用户行为。 |
| Harness 操作指令 | `public_bundle.json:1` 的 `public_hints` 要求修改 NON-TEST 源文件、不修改测试，允许窄范围验证、完成后简短总结 | 这是原操作指令，不是 pandas 的功能需求。若实际求解适用，源代码层的合理修复仍可进行，回归可通过临时内存脚本与已有测试验证；若不适用，则可增加常规回归测试。两种情况下均没有发现必须修改测试本身才能满足 issue 的理由。 |
| 环境事实声明 | 同一字段声称已激活 `testbed` conda 环境，工具在 `/testbed` 执行 | 仅为声明，待真实 actor 验证。`environment_brief.md:3–12,20–26` 明确没有提供运行证明。 |
| 旧评分机制解释 | 同一字段称测试修改全部恢复且永不计分 | `environment_brief.md:21–24` 已说明这不代表当前机制；当前无按测试文件名统一排除，仍有官方文件恢复等具体限制。本角色不推断具体受影响文件，不据此忽略原禁改测试指令。 |

**2. 合理实现范围**

可以接受在 Series 缺失标签插入路径正确选择承载 dtype，也可以接受在类型提升辅助函数中正确处理 categorical 后复用现有拼接流程，或采用效果等价的局部重构。公开契约限制的是结果和旧行为，不限制补丁必须落在 `cast.py`、必须新增某个内部函数、分支排列或缓存实现。这里没有提出或运行修复。

`maybe_promote` 的文档将参数描述为 `np.dtype`，返回可容纳原 dtype 与填充值的 dtype/value 二元组（`base/pandas/core/dtypes/cast.py:528–547`）；但公开调用者确实把 categorical dtype 传入这一通路（`base/pandas/core/indexing.py:2113–2118`）。因此，在辅助函数侧支持此实际调用和在调用方避开不适用的 NumPy 转型假设，都是可以讨论的实现范围。不能仅凭堆栈经过该函数，要求解题者必须改变其独立调用时的 categorical 行为。

如果修改共享提升函数，需保护其现有值与类型契约。旧测试不仅检查 dtype，也检查返回标量的具体类型及值（`base/pandas/tests/dtypes/cast/test_promote.py:68–119`）；缓存还刻意区分 `1` 与 `True`（`base/pandas/core/dtypes/cast.py:567–572`）。`maybe_upcast` 和数组 take 路径也使用它（`base/pandas/core/dtypes/cast.py:948–979`；`base/pandas/core/array_algos/take.py:95–114`），因此广泛吞掉 TypeError 或全局禁用标量转换不构成有依据的行为修复。

结果中的 `object` dtype、元素值及标签是明确约定。交互式显示空格、内部变量名、辅助函数名、修复后的异常堆栈均无额外约定。本题不是要求修复 `CategoricalIndex` 扩容：`base/pandas/tests/indexing/test_categorical.py:23–40,76–102,316–323` 讨论的是索引标签类别，而题面是 Series 值的 dtype；二者应区分。

**3. 初态线索与疑义**

调查入口充分：题面包含最小构造、单条触发操作、旧版本 `1.4.3` 的期望、内部错误全文，以及从 `.loc` 到 `_setitem_with_indexer_missing`、`maybe_promote`、`_ensure_dtype_type` 的堆栈（`user_prompt.txt:7–105`）。公开 bundle 固定了 base commit `8b72297c8799725e98cb2c6aee664325b752194f`。题面堆栈行号和导出源码有少量偏移，函数名和调用链足以定位。

静态线索与报错相符：非空且非 object 的 Series 在扩容时调用 `maybe_promote`（`base/pandas/core/indexing.py:2113–2118`）；categorical dtype 的 `type` 是元类 `CategoricalDtypeType`（`base/pandas/core/dtypes/dtypes.py:124–129,186–192`）；提升函数的部分数值分支未将其转换为 object，最后调用 `dtype.type(value)`（`base/pandas/core/dtypes/cast.py:650–731`）。这提供了可检验的原因假设，尚不是本环境中实测复现或完整根因证明。

当前没有发现会阻碍理解核心需求的缺失附件、外部数据或必须访问的公开网页。完整最小例子直接包含在包内，相关代码、文档和旧测试可查。阅读全文、调用者与 dtype 边界属于正常开发调查，不是题面缺陷。祖先历史没有提供，但对当前明确示例不是必需输入；若要精确恢复未说明边界的历史语义，可另请求只含公开祖先的材料，无需未来对象或未来修复。

真正待核对的是执行条件：actor 身份下是否导入指定 checkout，C 扩展是否存在，依赖与测试配置是否可用，写权限和资源是否足够。静态包不包含这些运行事实（`environment_brief.md:5–13`）。若导入失败，先登记环境问题，不能把它当作原 issue 的预期 TypeError。

**4. 开发需求表**

所有命令均为**建议，未执行**；应在真实 actor 的 `/testbed` 工作区执行，不在本次静态导出的 `base/` 执行。下表的 C1–C6 对应后续命令。

| 操作 / 资产 / 服务 | 公开依据 | 环境说明支持到哪层 | 缺口与最小检查 / 预期 |
| --- | --- | --- | --- | --- |
| Bash、可写源码工作区、真实 Python 环境 | `public_bundle.json:1` 的 tools、workdir、hints | `environment_brief.md:8–12` 给出拟用 profile，称 actor 为 `agent/54321`，工作区/home 可写；本题未验证 | C1 核对身份、工作目录、解释器及导入路径；应来自 `/testbed` 对应构建。conda 名称输出仅辅助，不能替代实际导入确认。 |
| Python、NumPy、pytz、python-dateutil 与 pandas C 扩展 | `base/setup.cfg:31–38`；`base/pandas/__init__.py:5–32`；`base/README.md:101–127` | 仅旧 hints 声称预装激活；没有运行清单 | C1 应成功导入；若缺硬依赖或 C 扩展，会先出现 ImportError，与原 bug 区别记录。源码支持 Python >=3.8，列出 3.8/3.9/3.10；不能由此证明任意新版本都兼容此旧提交。 |
| 内存中构造 categorical Series，执行扩容 | `user_prompt.txt:10–28` | 不依赖文件数据、网络或外部服务；CPU profile 只给默认限额（`environment_brief.md:10–12`） | C2 为最小复现。初态预计在赋值行出现题面 TypeError；修复后断言精确结果通过。未实测。 |
| pytest、Hypothesis 与必要测试插件 | `base/setup.cfg:51–55`；`base/pandas/conftest.py:37–44`；`base/requirements-dev.txt:4–9,21`；`base/pyproject.toml:34–64` | 公共测试可静态读取，能否收集/运行仍待 actor 检查 | C3/C4/C5 为窄范围公开测试。Hypothesis 是 conftest 的直接导入；pytest-asyncio 对应 strict-config 下的 `asyncio_mode`。缺插件、依赖或收集失败不是功能验收结果。 |
| 若缺构建产物，使用本地工具链构建并让解释器使用 checkout | `base/doc/source/development/contributing_environment.rst:9–10,41–47,171–173,199–220`；`base/pyproject.toml:1–8`；`base/setup.cfg:57–58` | 未证明 C/C++ 编译器、Cython、setuptools、wheel、NumPy 头文件、磁盘及写权限可用；不假定公网下载 | C6 仅在需要时建议。构建要求 Cython >=0.29.32,<3，开发文件固定 0.29.32。默认 2 CPU/4 GiB、tmp/home 限额不等于构建验证通过；采用单 worker 只是降低并发。 |
| 远程服务、外链、附件、GPU | 示例和所读测试均使用内存值；无相应功能调用 | `environment_brief.md:10` 不保证公网 | 核心复现无这类需求。不需要安装公开网站版本来替换固定 checkout；缺构建依赖时应由环境方提供与该版本兼容的本地资产。 |

C1：**建议，未执行**。在 `/testbed` 分别检查身份和最小导入；成功时应打印实际解释器、checkout 导入路径与版本。

```sh
# 建议，未执行
id
```

```sh
# 建议，未执行
python -c 'import os, sys; import pandas as pd; import numpy as np; from pandas._libs import lib, hashtable; print(os.getcwd()); print(sys.executable); print(os.environ.get("CONDA_DEFAULT_ENV")); print(pd.__file__, pd.__version__); print(np.__version__)'
```

C2：**建议，未执行**。核心复现与预期结果断言；原 bug 预计使赋值行抛错，修复后应保留原值、追加 `0` 并得到 object dtype。

```sh
# 建议，未执行
python - <<'PY'
import pandas as pd
from pandas.testing import assert_series_equal

s = pd.Series(["a", "b", "c"], dtype="category")
s.loc[3] = 0
expected = pd.Series(["a", "b", "c", 0], index=[0, 1, 2, 3], dtype=object)
assert_series_equal(s, expected)
print(s)
PY
```

C3：**建议，未执行**。已有 Series 扩容与 categorical 赋值测试应继续通过；这些旧测试未直接包含题面的新回归断言，单独通过不能证明修复完成。

```sh
# 建议，未执行
python -m pytest pandas/tests/series/indexing/test_setitem.py -q -k 'TestSetitemWithExpansion or categorical'
```

C4：**建议，未执行**。若触及共享类型提升逻辑，运行该公开模块检查已有 dtype/标量类型规则；预期旧用例继续通过。

```sh
# 建议，未执行
python -m pytest pandas/tests/dtypes/cast/test_promote.py -q
```

C5：**建议，未执行**。若触及 categorical 通用赋值或索引分支，分别检查新类别拒绝规则及位置索引不得扩容的约定；按实际变更选择，无需扩展到全仓。

```sh
# 建议，未执行
python -m pytest pandas/tests/arrays/categorical/test_indexing.py -q -k 'where_new_category_raises or where_unobserved_categories'
```

```sh
# 建议，未执行
python -m pytest pandas/tests/indexing/test_partial.py -q -k partial_setting
```

C6：**建议，未执行**。仅当真实环境缺少可用的本地构建且所需工具/依赖已提供时考虑；成功后重做 C1。命令来自仓库构建流程，限制并发并禁止解析运行依赖；具体 pip 是否接受旧构建选项仍待核对。若仅修改 Python 源码且现有扩展可用，通常不需重新编译。

```sh
# 建议，未执行
python setup.py build_ext -j 1
```

```sh
# 建议，未执行
python -m pip install -e . --no-deps --no-build-isolation --no-use-pep517
```

**5. 实际阅读范围与限制**

完整读取指定角色卡，以及 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。对公开包做过文件名清单扫描，输出被截断；列名不等于阅读文件内容。实际定点打开并审阅的源码、文档和旧测试如下：

| 文件 | 实际打开范围 |
| --- | --- |
| `base/pandas/core/dtypes/cast.py` | 509–740、933–986 |
| `base/pandas/core/indexing.py` | 2056–2165 |
| `base/pandas/core/dtypes/dtypes.py` | 124–206 |
| `base/pandas/core/arrays/categorical.py` | 1556–1605 |
| `base/pandas/core/dtypes/concat.py` | 69–159 |
| `base/pandas/core/series.py` | 1092–1137 |
| `base/pandas/core/array_algos/take.py` | 46–117 |
| `base/pandas/tests/series/indexing/test_setitem.py` | 459–651 |
| `base/pandas/tests/dtypes/cast/test_promote.py` | 1–119、225–365、508–585（文件到 582） |
| `base/pandas/tests/arrays/categorical/test_indexing.py` | 206–295 |
| `base/pandas/tests/indexing/test_categorical.py` | 1–110、298–345 |
| `base/pandas/tests/indexing/test_partial.py` | 244–282 |
| `base/doc/source/user_guide/categorical.rst` | 759–818 |
| `base/doc/source/user_guide/indexing.rst` | 796–827 |
| `base/README.md` | 初次 1–185 的合并工具输出被截断；另完整复读 72–136，安装依据取后者 |
| `base/doc/source/development/contributing_environment.rst` | 1–51、145–175、196–221；另做安装关键词检索 |
| `base/setup.cfg` | 18–62；另做环境关键词检索 |
| `base/pyproject.toml` | 1–73；另做环境关键词检索 |
| `base/requirements-dev.txt` | 1–24；另做环境关键词检索 |
| `base/pandas/conftest.py` | 1–84、98–122；另检索 pytest 配置关键词 |
| `base/pandas/__init__.py` | 1–56 |

另对 `base/pandas/tests/dtypes/`、`base/pandas/tests/indexing/`、`base/pandas/tests/series/indexing/`、`base/pandas/tests/arrays/categorical/` 做了类型提升/扩容关键词搜索；对 `base/pandas/core/` 做了 `maybe_promote` 调用位置搜索；对 `base/environment.yml` 只看了环境依赖关键词命中行。搜索命中的其他文件未展开；未读取所有调用者实现或全量测试。尝试检索 `base/conftest.py` 得到文件不存在，随后使用实际存在的 `base/pandas/conftest.py`，没有据此判定环境异常。

未打开 `base_identity.json`，未查 `.gitmodules` 或子模块内容；本题所读调用链未显示需要子模块。未查历史、未来代码、外链、容器、依赖实装、任何私有验收或其它题。公开测试与源码只作静态阅读；没有测试通过、bug 实际复现、资源够用或开发环境可用的运行证据。

`user_prompt.txt` 是静态渲染文件，不是实际模型消息记录；`public_bundle.json` 的 hints 是否进入 CLI system message 未知，但该公开 bundle 会在真实解题容器的公开路径出现，不能因为提示文本没有渲染到 user prompt 就视为不可见（`environment_brief.md:3–6,20–26`）。`base/` 也不是完整运行容器。需要保留的关键未知为：真实 actor 的导入/窄测试能力、原测试修改指令实际适用情况，以及非示例扩容边界的完整 dtype 契约。
