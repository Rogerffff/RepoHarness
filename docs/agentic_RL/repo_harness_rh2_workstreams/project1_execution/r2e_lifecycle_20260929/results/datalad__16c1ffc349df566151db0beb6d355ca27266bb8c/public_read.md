# 公开读者记录：datalad__16c1ffc349df566151db0beb6d355ca27266bb8c

- 角色：R2E 公开读者（单题闭环试行 2026-09-29），干净上下文；只读了角色卡和本题 `PUBLIC_DIR`。
- 路径约定：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json` 相对 `PUBLIC_DIR`；其余路径相对 `worktree/`，也就是解题者看到的 `/testbed`。
- 本文结论全部来自静态阅读。所有命令都是**建议，未执行**；机器可读版本见同目录 `commands.json`。

## 1. 需求表

| # | 行为 | 改变 / 保留 | 依据 | 确定程度 |
|---|---|---|---|---|
| R1 | 用户传入的 `result_filter` 要以关键字展开的形式收到 API 调用里的关键字参数：`custom_filter(res, **kwargs)` 的 `kwargs` 要含 `dataset`。题面调用 `Test_Utils().__call__(4, dataset='awesome', result_filter=custom_filter)` 应正常返回结果，不再报错 | 改变 | 题面 `user_prompt.txt:10-24`；base 只传 `res`：`datalad/interface/utils.py:1028-1034` | 明示 |
| R2 | filter 的第一个位置参数仍是单条结果 dict | 保留 | 题面签名 `user_prompt.txt:12`；参数文档 `datalad/interface/utils.py:863-868` | 明示 |
| R3 | 过滤语义不变：filter 返回假值或抛 `ValueError` 时丢弃该条，其余结果按原顺序返回；其它异常照常抛出；`on_failure` 的失败收集发生在过滤之前（`utils.py:1021-1027`） | 保留 | `utils.py:1028-1034`、`863-868`；公开测试 `datalad/interface/tests/test_utils.py:400-422` | 明示（代码和公开测试） |
| R4 | 调用带关键字参数时，Constraint 对象作 filter 仍然可用。两处库内用法：`Create` 的类级默认 filter `EnsureKeyChoice(...) & EnsureKeyChoice(...)`（`datalad/distribution/create.py:89-91`，经 `utils.py:979-983` 成为每次 `create` 的默认值）；CLI 的 `--report-status/--report-type` 组合出 `EnsureKeyChoice`（`datalad/interface/base.py:325-336`），随后 `cls.__call__(**kwargs)` 把所有参数按关键字传入（`base.py:338`）。`Constraint.__call__` 只接受一个参数（`datalad/support/constraints.py:54、290、420`）；`Dataset` 方法调用总会把 `dataset` 和其它参数转成关键字（`datalad/distribution/dataset.py:441-451`） | 保留 | 代码 | 合理推知（强）：不兼容时，`ds.create(...)` 和 CLI 过滤会报 `TypeError` |
| R5 | 调用带关键字参数时，只收一个参数的普通函数或 lambda 作 filter 仍然可用 | 保留 | 库函数 `is_ok_dataset(r)`（`datalad/interface/results.py:66-67`）被 `datalad/interface/tests/test_save.py:119,135,155` 通过 `ds.save(...)` 使用；另有单参数 lambda 配合关键字调用：`datalad/interface/tests/test_clean.py:39-40`（`clean(dataset=ds, ...)`）、`datalad/distribution/tests/test_get.py:244,403-405,409`、`datalad/distribution/tests/test_uninstall.py:157-158` | 合理推知：提示禁止改测试文件（`public_bundle.json:15`），按公开依据，这些用法应继续通过；隐藏测试里是否还有这类用法未知 |
| R6 | `test_result_filter` 的现有断言继续成立：不加 filter 得 `[0,1,2,3]`；`EnsureKeyChoice('somekey',(0,2))` 和等价 lambda 都得 `[0,2]`，最后一条是完整 dict | 保留 | `datalad/interface/tests/test_utils.py:400-422` | 明示（公开测试） |
| R7 | `build_doc` 生成的文档仍含 `result_filter`、`return_type`、`dictionary is passed` 等子串 | 保留 | `test_utils.py:373-379`；文档来源 `utils.py:857-892`、`1115-1121` | 明示（公开测试）；只在修改参数文档时相关 |
| R8 | 结果渲染器继续收到 `**_kwargs` | 保留 | `utils.py:1046-1050`；各命令的 `custom_result_renderer(res, **kwargs)`：`datalad/interface/save.py:161`、`datalad/interface/unlock.py:147`、`datalad/distribution/create.py:303` | 代码 |
| R9 | list / item-or-list 模式和 generator 模式共用 `generator_func`，所以两种模式下 filter 都应拿到关键字参数 | 改变（随 R1） | `utils.py:1063-1082` | 合理推知 |
| A1 | `kwargs` 的具体内容有两种读法：一是只含调用时显式给出、且去掉 `return_type` 等 eval 参数后的关键字参数（即 `_kwargs`，与渲染器一致）；二是还包括按位置传入的参数、默认值，甚至 eval 参数 | 待定 | 题面只要求 `'dataset' in kwargs` | 多解 |
| A2 | `dataset` 按位置传入（`Test_Utils().__call__(4, 'awesome', result_filter=f)`）或根本没传时，filter 是否应看到 `dataset` | 待定 | 题面未提 | 多解 |
| A3 | 值原样传递（字符串 `'awesome'`），还是先做 `EnsureDataset` 一类转换。`eval_results` 本身不做参数约束转换，约束只在 CLI 解析时作为 argparse 的 `type` 使用（`base.py:279-280`） | 待定 | 题面未提 | 多解；原样传递最贴近现有代码 |

## 2. 合理实现范围

- **调用约定由题面确定**：参数必须以关键字展开的方式传入（`**kwargs`）。如果把参数打包成一个 dict、作为第二个位置参数传入，就不满足题面签名 `custom_filter(res, **kwargs)`，会报 `TypeError`。
- **修改位置**：可以改 `eval_results` 的过滤步骤（`utils.py:1028-1034`），也可以在 `common_params` 取出 filter 时（`utils.py:979-983`）包一层，两者效果相同。
- **兼顾 R4 和 R5 的做法有多种，都应接受**：
  - 按 filter 的签名判断是否接受额外关键字参数，只给接受的 filter 传 `**kwargs`。`utils.py:15` 已经 `import inspect`。这种做法要处理可调用对象实例（如 Constraint）、`functools.partial`，以及拿不到签名的内建函数。
  - 先按新约定调用，遇到参数不匹配再退回只传 `res`。代价是可能掩盖 filter 内部自己抛出的 `TypeError`，而且同一个 filter 可能被调用两次。
  - 单独处理 `Constraint` 实例，或给 Constraint 的 `__call__` 加上可以忽略的关键字参数，再配合对普通函数的判断。只做其中一半不够：只改 Constraint，R5 的单参数 lambda 会失败；只判断普通函数，R4 会失败。
- **不兼容的做法**：无条件执行 `result_filter(res, **_kwargs)` 能让题面例子通过，但按 R4 和 R5，`ds.create(...)`、CLI 过滤以及上面列出的公开测试都会报 `TypeError: ... unexpected keyword argument 'dataset'`。这些公开测试大多需要 git-annex，在解题环境里不一定能跑，所以解题者自己未必能发现这类回归（见第 4 节的 `filters_backcompat`）。
- **`kwargs` 的具体内容（A1-A3）**：传入与渲染器相同的 `_kwargs`，是与现有代码最一致的读法；传入绑定后的全部参数（含位置参数和默认值）也满足题面例子。隐藏测试是否检查 `kwargs` 的精确内容，目前未知。
- **命名、输出和默认值**：题面没有要求改变参数名 `result_filter`、默认值 `None`（`utils.py:893-899`）、`Create` 的类级默认 filter、返回类型或结果内容，也没有要求新增 API、输出或日志。`result_filter` 的参数文档（`utils.py:863-868`）可以顺手更新，但不是必需的；如果修改，要保留 R7 列出的子串。
- **实现时的边界情况**：在 `(res, **kwargs)` 约定下，如果 filter 的第一个参数与命令参数同名（例如 `def f(path, **kw)`，而命令本身有 `path` 参数），调用会报 `got multiple values`。渲染器和题面例子都把第一个参数命名为 `res`。这不属于本题要求。
- **本题范围之外**：`result_xfm` 仍然只收一个参数（`datalad/interface/results.py:70-105`，`ResultXFM.__call__(self, res)`），改动它会破坏 `known_result_xfms`。项目声明支持 Python 2（`tox.ini:2` 列出 py27，`utils.py:32,957` 有 `PY2` 分支），但当前环境是 3.7.9，无法验证 Python 2 兼容性；另外 `inspect.signature` 只在 Python 3 可用。

## 3. 题面质量与初态线索

### 3.1 是否直接给出或强烈暗示修法

- 题面标题和示例签名 `custom_filter(res, **kwargs)`（`user_prompt.txt:5,12`）给出了调用约定，实际上已经指明要在调用 filter 的地方补传关键字参数。同一个函数里，渲染器的调用已经是 `(res, **_kwargs)` 的形式（`utils.py:1048,1050`），修改点很容易找到。
- 示例代码是调用方的测试场景，不是修好后的实现。题面没有提到 R4 和 R5 的兼容要求，而这恰好是实现中最容易出错的地方。结论：题面强烈暗示了修改位置和调用约定，但没有泄露实现。

### 3.2 描述的报错能否从 base 源码读出

- 能。`utils.py:1030` 只调用 `result_filter(res)`，所以 filter 内的 `kwargs == {}`。`AssertionError` 不是 `ValueError`，不会被 `utils.py:1032` 捕获。默认 `return_type='list'` 时，`return_func` 会在调用内执行 `list(results)`（`utils.py:1066-1070`），所以错误在调用时就会抛出。
- 一个小出入：题面报告的消息 `'dataset' not found in {}` 是 `assert_in` 的格式（来自 `nose.tools`，即 unittest 的 `assertIn`，见 `datalad/tests/utils.py:38-40`），而示例里写的是裸 `assert`。在普通脚本里，裸 `assert` 只会抛出不带消息的 `AssertionError`。这不影响理解题意。

### 3.3 示例在 base 接口下是否说得通

- 说得通。`Test_Utils` 是测试模块里的假命令（`datalad/interface/tests/test_utils.py:327-352`），签名 `__call__(number, dataset=None)`（`:347`）接受 `dataset`；`result_filter` 是有文档的 eval 参数（`utils.py:863-868`）；`eval_results` 不做参数约束检查，所以字符串 `'awesome'` 会原样传给命令。
- 题面没说 `Test_Utils` 定义在哪里，但 `grep -rn Test_Utils` 就能找到。要复现，可以 import 这个测试模块，它依赖 `nose` 和 `mock`（`test_utils.py:17`、`datalad/tests/utils.py:27,38-45`）；也可以在脚本里自己定义一个结构相同的 `Interface` 子类。`eval_results` 按 `__qualname__` 和所在模块查找命令类（`utils.py:956,975-976`），类定义在模块顶层即可。

### 3.4 复现与调查入口

- `grep -rn result_filter datalad` 可以找到 `utils.py:863-868,993,1028-1034` 和各个调用者；`grep -rn Test_Utils` 可以找到 `test_utils.py:329`。`Dataset` 方法的绑定在 `datalad/distribution/dataset.py:404-454`；CLI 入口在 `base.py:296-338` 和 `datalad/cmdline/main.py:118-128`。公开材料足以定位复现方法和修改入口。

### 3.5 缺失信息

- **不妨碍开发、正常读代码就能获得的**：修改点、调用者、Constraint 的签名。
- **题面没说、会影响隐藏测试风险的**：是否要求 R4 和 R5 的兼容（公开代码强烈支持"要求"），以及 A1-A3 中 `kwargs` 的精确内容。
- **环境层面的未知**（见第 4 节）：`.venv` 里是否装了 `nose`、`pytest`、`wrapt`，以及有没有 `git-annex`。它们决定能跑哪些公开测试，但不决定题目能否解。

### 3.6 `public_hints` 分类（`public_bundle.json:15`）

- **题目需求**：修复一个 GitHub issue；找到根因，修改非测试源码；由另一组测试判分。
- **给解题者的操作指令**：不要改仓库里的测试文件；测试范围要窄（单个文件或模块），在 `/testbed` 用 `python -m pytest` 运行；确认完成后给出简短总结，并停止调用工具。
- **环境事实声明**：bash 已经在 `/testbed`；`/testbed/.venv` 里的 `python` 和测试工具已经就位；没有网络，`pip` 可能不可用，只能用已安装的包。`environment_brief.md:10-13` 进一步写明：Python 3.7.9；没有 pip、pip3 和 uv；不能出网；解题身份 uid 54321；资源 2 CPU / 4 GiB；`/tmp` 1 GiB；HOME 里没有 git 身份。
- **对合法解法的影响**：解题者不能改 `Test_Utils`，也不能改测试里的单参数 lambda，所以修复必须在库代码里兼容这些用法（R5）。`is_ok_dataset` 在库代码 `results.py` 里，可以改，但只改它不够。修复是纯 Python，没有网络和 pip 不构成障碍。

### 3.7 初态

- `worktree_manifest.json` 中 `initial_diff` 为 0 字节，说明工作树就是 base 的跟踪文件，另加未跟踪的 `run_tests.sh`。`install.sh` 在镜像里有，但公开工作树里缺，内容未知。
- `run_tests.sh:1` 运行的是 `.venv/bin/python -W ignore -m pytest -rA r2e_tests`，而公开工作树里没有 `r2e_tests/`（隐藏测试），所以在解题初态直接运行它测不到任何东西。它能说明的只是：判分时用 `.venv` 里的 pytest。
- 项目原本用 nose 跑测试（`tox.ini:9` 为 `nosetests -s`），仓库里没有 pytest 配置文件，也没有 `conftest.py`。本题相关的公开测试都是普通函数，pytest 可以收集。

## 4. 开发需求表

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令（建议，未执行）与预计现象 |
|---|---|---|---|---|
| 导入 datalad 及其依赖 `wrapt`、`six`、GitPython；import 时会调用 `git`（`datalad/__init__.py:17-25`、`datalad/config.py:189-198`） | `utils.py:15-50` | 写到 `python` 指向 `/testbed/.venv/bin/python`（3.7.9）、没有 pip、不能出网（`:10-11`）；没列出已装的包；没直接写 git 是否安装，只写了 HOME 里没有 git 身份（`:13`） | 包清单；git 和 git-annex 是否在 PATH | `env_imports`：预计打印 3.7.9、`/testbed/datalad/__init__.py`、各包版本、`git version ...`，以及 git-annex 的路径或 `git-annex not on PATH`；退出码 0 |
| 按题面复现 | `user_prompt.txt:10-24`；`test_utils.py:327-352` | 无直接说明。import 测试模块需要 `nose`、`mock`（`test_utils.py:17`、`datalad/tests/utils.py:27,38-45`），还会导入 `datalad.api` 的全部接口模块（`test_utils.py:45`、`datalad/api.py:83-103`） | `nose` 和 `mock` 是否已装未证实 | `repro_issue_example`：修复前报 `AssertionError: FILTER_KWARGS={}`，退出码 1；修复后打印 `RESULT [0, 1, 2, 3]`，退出码 0 |
| 兼容性回归检查（R4、R5），不需要 git-annex | `constraints.py:54,290,420`；`create.py:89-91`；`dataset.py:441-451`；`base.py:325-338` | 同上 | 无额外缺口 | `filters_backcompat`：修复前和兼容的修复后都打印 6 行结果和 `BACKCOMPAT_OK`，退出码 0；如果修复无条件传关键字参数，预计报 `TypeError ... unexpected keyword argument 'dataset'`，退出码非 0 |
| 观察 filter 实际收到的键（A1、A2） | `utils.py:979-988,1046-1050`；`dataset.py:441-451` | 同上 | 无 | `filter_kwargs_probe`：修复前各项都是 `[]`。修复后，按 `_kwargs` 读法，`kw_dataset` 和 `kw_dataset_generator` 为 `['dataset']`，`dataset_method` 为 `['dataset', 'number']`，`positional_dataset` 和 `no_dataset` 为 `[]`；其它读法下这几项会多出键 |
| 相关公开测试，不需要 git-annex | `test_utils.py:355-422`；`datalad/tests/test_constraints.py`（16 个普通函数） | 提示要求用 `python -m pytest`；`run_tests.sh` 说明 `.venv` 里装了 pytest | pytest 版本 | `public_tests_narrow`：修复前后都预计 18 passed |
| 较重的公开测试（涉及 `create`、`save`、`get`、`clean`、`uninstall`，如 `test_utils.py:72-104`、`test_clean.py`、`test_get.py`） | 这些测试会真正建库、提交 | HOME 里没有 git 身份（`:13`）；没提 git-annex | 可能缺 git-annex；提交需要临时设置身份 | 不作为必要验证。如果要跑，范围缩小到单个文件，并在命令前临时设置 `GIT_AUTHOR_NAME`、`GIT_AUTHOR_EMAIL`、`GIT_COMMITTER_NAME`、`GIT_COMMITTER_EMAIL` |
| 构建与外部服务 | datalad 是纯 Python，工作树里没有 `.c`、`.pyx`、`.so` 文件 | — | 无 | 不需要构建，也不需要网络或外部服务 |

以下命令都是建议，未执行，均在 `/testbed` 下运行；与 `commands.json` 内容相同。

```bash
# env_imports（expect zero）
PYTHONDONTWRITEBYTECODE=1 python -c "
import sys; print('python', sys.executable, sys.version.split()[0])
import datalad; print('datalad', datalad.__version__, datalad.__file__)
import wrapt, nose, pytest; print('wrapt', wrapt.__version__, 'nose', nose.__version__, 'pytest', pytest.__version__)
" && git --version && (command -v git-annex || echo 'git-annex not on PATH')
```

```bash
# repro_issue_example（expect nonzero：base 上复现原 bug）
PYTHONDONTWRITEBYTECODE=1 python -c "
from datalad.interface.tests.test_utils import Test_Utils
def custom_filter(res, **kwargs):
    assert 'dataset' in kwargs, 'FILTER_KWARGS=%r' % (kwargs,)
    return True
out = Test_Utils().__call__(4, dataset='awesome', result_filter=custom_filter)
print('RESULT', [r['somekey'] for r in out])
"
```

```bash
# filters_backcompat（expect zero：修复前后都应通过）
PYTHONDONTWRITEBYTECODE=1 python -c "
from datalad.interface.tests.test_utils import Test_Utils
from datalad.distribution.dataset import Dataset
from datalad.support.constraints import EnsureKeyChoice
keys = lambda rs: [r['somekey'] for r in rs]
call = Test_Utils().__call__
ds = Dataset('/does/not/matter')
checks = [
    ('keychoice', keys(call(4, dataset='awesome', result_filter=EnsureKeyChoice('somekey', (0, 2)))), [0, 2]),
    ('and_constraints', keys(call(4, dataset='awesome', result_filter=EnsureKeyChoice('status', ('ok',)) & EnsureKeyChoice('somekey', (1, 3)))), [1, 3]),
    ('one_arg_lambda', keys(call(4, dataset='awesome', result_filter=lambda x: x['somekey'] in (0, 2))), [0, 2]),
    ('generator_mode', keys(call(4, dataset='awesome', return_type='generator', result_filter=EnsureKeyChoice('somekey', (0, 2)))), [0, 2]),
    ('dataset_method_constraint', keys(ds.fake_command(4, result_filter=EnsureKeyChoice('somekey', (0, 2)))), [0, 2]),
    ('dataset_method_lambda', keys(ds.fake_command(4, result_filter=lambda x: x['somekey'] in (0, 2))), [0, 2]),
]
for name, got, want in checks:
    print(name, got)
    assert got == want, (name, got, want)
print('BACKCOMPAT_OK')
"
```

```bash
# filter_kwargs_probe（expect any：只看 filter 收到哪些键）
PYTHONDONTWRITEBYTECODE=1 python -c "
from datalad.interface.tests.test_utils import Test_Utils
from datalad.distribution.dataset import Dataset
seen = {}
def spy(tag):
    def f(res, **kwargs):
        seen.setdefault(tag, sorted(kwargs))
        return True
    return f
call = Test_Utils().__call__
call(1, dataset='awesome', result_filter=spy('kw_dataset'))
list(call(1, dataset='awesome', return_type='generator', result_filter=spy('kw_dataset_generator')))
call(1, 'awesome', result_filter=spy('positional_dataset'))
call(1, result_filter=spy('no_dataset'))
Dataset('/does/not/matter').fake_command(1, result_filter=spy('dataset_method'))
for k in sorted(seen):
    print(k, seen[k])
"
```

```bash
# public_tests_narrow（expect zero）
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -rA datalad/interface/tests/test_utils.py::test_result_filter datalad/interface/tests/test_utils.py::test_eval_results_plus_build_doc datalad/tests/test_constraints.py
```

## 5. 阅读范围

- **读了**：角色卡；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。`worktree_manifest.json` 只看了顶层键，以及 `export`、`initial_diff`、`untracked_*` 这几段摘要；`files` 段只数了条目数（362），没有打开 `initial_diff.source` 指向的 `PUBLIC_DIR` 外路径。
- **在 worktree 里打开过的**：`run_tests.sh`；`datalad/interface/utils.py`（1-75、780-1122 行）；`datalad/interface/tests/test_utils.py`（全文）；`datalad/support/constraints.py`（30-69、230-440 行）；`datalad/interface/base.py`（240-370 行）；`datalad/distribution/create.py`（60-120、295-320 行）；`datalad/distribution/dataset.py`（404-470 行）；`datalad/interface/results.py`（60-130 行）；`datalad/interface/save.py`、`datalad/interface/unlock.py` 中的渲染器片段；`datalad/interface/tests/test_clean.py`（30-66 行）；`test_save.py`、`test_get.py`、`test_uninstall.py` 中的 filter 用法片段；`datalad/tests/utils.py`（导入部分）；`datalad/tests/test_constraints.py`（函数列表和 127-240 行）；`datalad/__init__.py`（1-120 行）；`datalad/config.py`（161-205 行）；`datalad/cmd.py`（460-483 行）；`datalad/api.py`（1-130 行）；`datalad/cmdline/main.py`（100-140 行）；`datalad/version.py`；`datalad/support/vcr_.py`（导入部分）；`tox.ini`；`requirements*.txt`；`setup.py`（40-120 行）；`.gitignore`；`datalad/interface/tests/__init__.py`。
- **只用 grep 搜过的**：`result_filter`、`Test_Utils`、`custom_result_renderer`、`@eval_results`、`report-status`、`result_renderer`。`docs/`、`CHANGELOG.md`、`CONTRIBUTING.md`、`README.md` 里没有 `result_filter` 或 `eval_results` 的相关内容。
- **没查的**：其它命令的实现细节（`get.py`、`clean.py`、`remove.py`、`uninstall.py` 等只看了 filter 的用法）；`docs/` 正文、`benchmarks/`、`tools/`、`cfgs/`；`install.sh`（公开工作树里缺）；`.venv` 实际装了哪些包（工作树不含）。按角色卡，隐藏测试、gold 补丁和历史审查都不读；角色卡引用的 SWE-Gym 公开读者卡在 `PUBLIC_DIR` 之外，也没读。
- **限制**：`user_prompt.txt` 只是静态渲染，不是捕获到的模型实际消息。`worktree/` 不是完整的运行容器，没有 `.git`、`.venv`、编译产物和隐藏测试。我没有运行任何项目代码；第 4 节和 `commands.json` 里的命令都没有执行，预计结果是静态推断。我只在本机对自己写的命令片段做过语法检查（`bash -n` 和 Python `compile`）。模型实际收到的消息、运行资源和开发条件都没有验证。
- **意外**：生成命令清单时，我在本会话共享的临时目录里看到了另一道题（coverage 相关）命令清单的片段。它与本题无关，也没有用于本记录。
