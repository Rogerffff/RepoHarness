# 公开读者静态审查：pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0

- 角色：R2E 公开读者（干净上下文，只读角色卡与本题公开包），2026-09-25。
- base：`b7f061c3d24df943e16918ad3932e767f5639a38`（`public_bundle.json:9`，与 `user_prompt.txt:1` 的 `b7f061c3d24d` 一致）。源码处于 pandas 1.1.0 开发期（`doc/source/whatsnew/v1.1.0.rst` 是最新一份 whatsnew）。
- 路径约定：源码路径相对 `worktree/`；公开包顶层文件直接写文件名。
- 全文结论都来自静态阅读，没有运行任何代码。写成"会报错 / 会返回"的地方都是按源码推断的。

## 速览

- 题面说的报错能从 base 源码走通。`numeric_only` 不为 None 时，`DataFrame._reduce` 按块归约；EA 块的一维数组被直接交给 `nanops.nanmean`，后者调用 `values.sum(axis, dtype=...)`，落到 `IntegerArray.sum` 里的 `nv.validate_sum`，抛出 `ValueError: the 'dtype' parameter is not supported in the pandas implementation of sum()`。
- **最关键的环境未知项：镜像里有没有 bottleneck。**如果装了并且启用，`mean` 会先走 `bn.nanmean`，得到什么结果无法从公开材料判断。`df.sum(numeric_only=True)` 不经过 bottleneck，两种环境下都能复现题面的同一条报错。
- **最大的题意不确定：**题面只演示了 `mean`，标题却泛指 reduction。在同一路径上，`sum` 会抛同样的错，`prod/min/max` 按静态阅读会抛 AttributeError。`numeric_only=False`、`axis=1`、缺失值语义和结果 dtype 题面都没说明。
- 有一条公开测试约束实现方式：`test_mean_datetimelike_numeric_only_false` 要求 Period 列在 `numeric_only=False` 下求 `mean` 时抛出 "reduction operation 'mean' not allowed"。如果把所有 EA 都改走数组自己的 `_reduce`，Period 列会改抛另一条消息。
- 附带发现（静态推断，非 bottleneck 路径）：在默认 `numeric_only=None` 下，这个混合 dtype 的 DataFrame 会走 `frame_apply(ignore_failures=True)`，Int64 列在内部抛同样的错后被静默丢掉。因此 `df.mean()` 很可能只返回 A 列，不能用来对照期望值。

## 1. 需求表

要改变的行为：

| # | 行为 | 类别 | 依据 |
|---|---|---|---|
| R1 | `df.mean(numeric_only=True)`（一列 int64，一列 `Int64`）不再抛错，返回 Series | 明示 | `user_prompt.txt:9-25`。失败路径：`pandas/core/frame.py:8317-8335` |
| R2 | 结果要包含 EA 列 `B`，不能靠排除 EA 列来"修好" | 明示 | `user_prompt.txt:25`（"including the ExtensionArray column 'B'"）。`numeric_only` 的文档写的是 "Include only float, int, boolean columns"（`pandas/core/generic.py:10425-10427`）。`Int64` 的 `_is_numeric` 为 True（`pandas/core/arrays/integer.py:70-72`），所以会被 `_get_numeric_data` 保留（`pandas/core/internals/blocks.py:1644-1646`、`pandas/core/internals/managers.py:705-713`） |
| R3 | 每列结果与逐列调用 Series 归约一致（例中 B 的均值为 5.5）；结果以保留下来的列标签为索引，列序不变 | 可合理推知 | 题面只写了 "a Series with the mean values for each numeric column"。Series 会把 EA 分派给数组自己的 `_reduce`（`pandas/core/series.py:4003-4005` → `integer.py:556-575`），这条路在 base 下能用。按块路径最后执行 `out.index = df.columns`（`frame.py:8339-8340`） |
| R4 | 其它归约（sum、prod、min、max、median、std、var、sem、skew、kurt）在 `numeric_only=True` 下遇到 EA 列也应能用 | 多解（倾向于需要） | 标题是 "DataFrame Reduction Fails"，正文是 "reduction operations (e.g., mean)"（`user_prompt.txt:4,7`）。按静态阅读：`sum` 在 `pandas/core/nanops.py:505` 触发同一个 ValueError；`prod/min/max` 分别在 `nanops.py:1159` 和 `nanops.py:863` 调用 `IntegerArray` 上并不存在的方法（`integer.py` 的归约方法只有 `sum`，在 `integer.py:577`），会抛 AttributeError；`median/var/std` 会先执行 `astype("f8")`（例如 `nanops.py:755-761`），无缺失值时可能能跑，但 `var/std` 计数时不看掩码，列里有缺失值时结果可能是 NaN。其它能进入这条路径的数值 EA，比如 `Sparse[int64]`，按静态阅读也会报同样的错，因为 `SparseArray.sum` 同样调用 `nv.validate_sum`（`pandas/core/arrays/sparse/array.py:1243-1251`）。另外，`mean/median/std/var/min/max` 都带 bottleneck 分支，装了 bottleneck 时的行为未知 |
| R5 | 结果 dtype；整列缺失或 `min_count` 不足时用 `pd.NA` 还是 `NaN` | 多解 | 题面没说。结果为 NaN 时，`IntegerArray._reduce` 返回 `pd.NA`（`integer.py:572-573`），这个值与 numpy 列的结果拼在一起后，Series 可能变成 object dtype |
| R6 | `numeric_only=False` 时同一 EA 列也不报错 | 多解（可推知有同样的问题） | 按块路径的进入条件是 `numeric_only is not None`（`frame.py:8317`）。值为 False 时也走这里，只是跳过数值列筛选（`frame.py:8318-8320`）。题面只提到 True |
| R7 | `axis=1` | 多解 | 题面没提。混合 dtype 的 DataFrame 转置后是 object 块（`frame.py:2663-2669`），大概率不会进入 EA 分支。全为同一种 EA dtype 的 DataFrame 转置后仍是 EA 列（`frame.py:2652-2662`），会回到同一条失败路径 |
| R8 | 默认 `numeric_only=None` 时的行为 | 多解（题面没提） | 混合 dtype 时，`_reduce` 走 `frame_apply(..., ignore_failures=True)`（`frame.py:8347-8372`）。这里的 `f` 直接把 `nanops.nanmean` 作用到每列 Series 上（`frame.py:8297-8298`）。`extract_array` 把 Series 拆成 `IntegerArray`（`pandas/core/construction.py:380-386`）后同样报错，异常被 `apply_series_generator` 吞掉（`pandas/core/apply.py:324-333`），B 列就被静默丢掉了。这里要不要修，题面没有要求 |

要保留的旧行为：

| # | 行为 | 依据 |
|---|---|---|
| P1 | 非 EA 数值列的结果和 dtype 不变 | 可合理推知；公开测试见 `pandas/tests/frame/test_analytics.py:264-290`、`:843-858` 等 |
| P2 | `numeric_only=True` 仍然排除 datetime、timedelta、period 等非数值列 | `test_analytics.py:860-874`（期望值为 `pd.Series({"A": 1.0})`） |
| P3 | `numeric_only=False` 时对 Period 列求 `mean` 抛 `TypeError`，消息匹配 `reduction operation 'mean' not allowed` | `test_analytics.py:882-900`。这条消息来自 `nanops.disallow`（`nanops.py:52-80`）和 `nanmean` 上的 `@disallow(PeriodDtype)`（`nanops.py:511`）。`PeriodArray.mean` 抛的是另一条消息 "mean is not implemented for PeriodArray ..."（`pandas/core/arrays/datetimelike.py:1639-1645`，经 `datetimelike.py:1555-1560` 的 `_reduce` 调用） |
| P4 | `IntegerArray.sum` 的现有公开用法保持可用：`arr.sum(skipna=..., min_count=...)`、`np.sum(arr)`；`np.add.reduce(arr)` 仍抛 NotImplementedError | `pandas/tests/arrays/integer/test_function.py:116-133`、`:67-72` |
| P5 | Series 级的 EA 归约不变 | `pandas/tests/extension/base/reduce.py:17-60`、`test_function.py:75-92` |

补充：公开仓库里找不到现成的 DataFrame 级测试同时覆盖 EA 列和非 None 的 `numeric_only`（在 `pandas/tests` 中检索 `numeric_only` 与 `Int64` 等 EA 的组合，没有结果）。修复是否正确，只能靠自己写脚本或新增测试来核对。

## 2. 合理实现范围

下面几种方向都有公开材料支持，但题面一种也没有指定。这里不写修复代码，也不猜隐藏测试预期哪一种。

1. **在 `DataFrame._reduce` 的按块路径里单独处理 EA 块**（`frame.py:8327-8331` 的 `blk_func`），让 EA 用数组自己的归约接口，与 `Series._reduce` 的分派方式一致（`series.py:4003-4005`）。接口上有两个约束。第一，`ExtensionArray._reduce(name, skipna=True, **kwargs)` 不接收 `axis`（`pandas/core/arrays/base.py:1026-1050`）。`IntegerArray._reduce` 会把 kwargs 原样传给 `masked_reductions.sum/prod/min/max`（它们没有 `axis` 参数，`pandas/core/array_algos/masked_reductions.py:55-102`），或者传给已经写死 `axis=0` 的 nanops 调用（`integer.py:569-570`），多传一个 `axis` 就会报 TypeError。第二，必须满足 P3。DatetimeTZ、Categorical 等 EA 在 `numeric_only=False` 下的现有行为会不会变，公开测试（按本次检索范围）只覆盖到 Period 这一条。
2. **在 nanops 层识别 EA**，例如在 `_get_values`（从 `nanops.py:284` 开始）或装饰器里，把带掩码的 EA 转成"ndarray + 掩码"或带 NaN 的浮点数组。影响面更大：`numeric_only=None` 的 `frame_apply` 路径和其它调用者也都经过 nanops。
3. **遇到 EA 块时退回逐列的 Series 归约。**
4. **只改 `IntegerArray.sum`，让它接受 numpy 风格的 `axis`/`dtype` 参数。**在非 bottleneck 路径下，这能让题面示例跑通，但静态阅读能看到三个风险：
   - nanops 按位置传入 `axis`（`nanops.py:554`、`:505`）。在当前签名下，这个值会绑定到 `skipna` 参数上（`integer.py:577`）。
   - `_maybe_get_mask` 对整数 dtype 返回 None（`nanops.py:226-229`），`nanmean` 于是按数组长度计数（`nanops.py:553`）。列里有缺失值时均值会偏小，例如 `[1, <NA>]` 会得到 0.5 而不是 1.0。
   - `prod/min/max` 仍然会失败（见 R4）。
   这种改法算不算可接受，取决于隐藏测试是否只覆盖无缺失值的 `mean`，公开材料无法判断。

约定层面：题面没有规定结果 dtype 和缺失值的表示方式，除列序外对输出格式也没有要求，也不要求新增公开 API 或特定命名。自然的输出是以保留列为索引的 Series，`mean` 的结果为 float64。对 `numeric_only=False`、`axis=1` 和默认 `None` 路径，几种处理方式都说得通（见 R6–R8）。

## 3. 题面质量与初态线索

**3.1 是否直接给出或强烈暗示了修法。**没有给修复代码。"Actual Behavior" 转述的是 `sum()` 的 `dtype` 参数校验报错（`user_prompt.txt:27-28`），容易把解题者引向症状层，也就是去改 `IntegerArray.sum`。根因在按块路径把 EA 直接交给了 nanops，这需要解题者自己追调用链才能找到。这不算泄题，但可能诱导出第 2 节第 4 种那样的窄修。

**3.2 题面描述的报错能否从 base 源码读出。**能。非 bottleneck 路径的调用链如下：

1. `generic.py:10188-10196`：`DataFrame.mean` 的 `func` 是 `nanops.nanmean`。
2. `generic.py:11160-11175`：`stat_func` 调用 `_reduce`。
3. `frame.py:8317-8320`：`numeric_only=True`，`_get_numeric_data` 保留 Int64 块。
4. `frame.py:8335` → `managers.py:336-338`：对每个块调用 `blk_func(blk.values)`。
5. `frame.py:8328-8330`：值是一维且不是 ndarray，于是调用 `op(values, axis=0, ...)`。
6. `nanops.py:538-554`：`_get_values` 不拆开 `IntegerArray`（`nanops.py:284`），接着调用 `values.sum(axis, dtype=np.float64)`。
7. `integer.py:577-578`：`nv.validate_sum((), {"dtype": float64})`。
8. `pandas/compat/numpy/function.py:254-273` → `pandas/util/_validators.py:64-68`：抛出 `ValueError: the 'dtype' parameter is not supported in the pandas implementation of sum()`。

题面没写异常类型，报错文字与源码一致。

bottleneck 分支：`nanmean` 带有 `@bottleneck_switch()`（`nanops.py:512`），而 `_bn_ok_dtype` 对 `Int64Dtype` 返回 True（`nanops.py:136-152`）。所以只要装了 bottleneck 且 `compute.use_bottleneck` 为 True，就会先调用 `bn.nanmean(IntegerArray, axis=0)`（`nanops.py:115-120`）。结果取决于仓库外的 bottleneck 和 numpy 版本，静态阅读判断不了会得到同一条报错、别的报错还是一个数值。`nansum` 没有 bottleneck 分支（`nanops.py:466-508`），所以 `df.sum(numeric_only=True)` 在两种环境下都应该复现题面的报错。`install.sh:44` 从 `requirements-dev.txt` 安装依赖，其中包含 `bottleneck>=1.2.1`（`requirements-dev.txt:47`），但这一步是否成功、bottleneck 是否真的在镜像里，公开材料没有交代。

**3.3 题面示例在 base 接口下是否说得通。**说得通。`dtype='Int64'` 和 `DataFrame.mean(numeric_only=...)` 都是 base 已有的接口。用 numpy 数组和 Series 混合构造 DataFrame 时会按 RangeIndex 对齐，没有问题。A 列是随机数，没法写死期望值；B 列的均值是 5.5。

**3.4 范围说明不足（见 R4–R8）。**题面只演示了 `mean`，没提 `numeric_only=False`、`axis=1`、缺失值和结果 dtype，也没提默认路径会静默丢列。

**3.5 初态线索。**
- `doc/source/whatsnew/v1.1.0.rst:759` 记录了 "IntegerArray now implements the sum operation (GH 33172)"，`:511` 记录了 nullable 类型归约的性能改动。由此推断，`IntegerArray.sum` 是这个开发周期新加的，它的签名与 nanops 的调用方式 `values.sum(axis, dtype=...)` 不兼容。这只是推断，没有核对提交历史（工作树不含 `.git`）。
- 镜像初态相对 base 的改动（见 `worktree_manifest.json` 的 `initial_diff`）只和 versioneer 有关：`pandas/__init__.py:408-409` 追加了版本号代码，`pandas/_version.py` 被重新生成，`setup.cfg` 被替换成只剩 `[versioneer]` 段（`setup.cfg:1-7`），`pyproject.toml` 被删除。这些都与题意无关。唯一的副作用是原 `setup.cfg` 里的 pytest 配置没了，跑公开测试时可能出现 marker 未注册的警告（推断）。
- `install.sh:106-112` 在 `exit 1` 之后还有几行非脚本文字，永远不会执行，不影响环境。

**3.6 复现与调查入口。**题面示例加上报错文字就足以复现，调查入口集中在 `frame.py` 的 `_reduce`、`nanops.py` 和 `integer.py`。没有会真正阻碍开发的缺失信息。主要的不确定性在于隐藏测试覆盖哪些归约、哪种 dtype、是否含缺失值、`numeric_only` 取哪些值；解题者只能按"与逐列 Series 归约一致"的原则尽量全覆盖。

**3.7 `public_hints` 的三类内容**（`public_bundle.json:15`）：
- **题目需求：**修复 `/testbed` 中的真实 issue，找到根因，只改非测试源码。与题面一致。
- **操作指令：**先探索代码；不要改测试文件；测试只跑单个文件或模块；完成后简短总结并停止调用工具。这些对本题没有妨碍。新增的回归测试不会计分，但不影响合法解法。
- **环境事实声明：**
  - 提示说 `python`、`pip` 和测试工具都指向"预激活的 conda 环境 `testbed`"，这与 `environment_brief.md:10-11` 不符。实际上是镜像环境变量让 `python` 指向 `/testbed/.venv/bin/python`（3.7.9）；pip 存在，但不能联网。照提示执行 `conda activate` 会失败，直接用 `python` 即可。本题也不需要装包。
  - 提示说评分前会重置测试文件、测试改动永不计分。按角色卡，这不是本来源的实际机制。`run_tests.sh:1` 实际运行的是隐藏的 `r2e_tests` 目录，所以改 `pandas/tests` 本来也不影响评分。

## 4. 开发需求表

所有命令均为**建议，未执行**；"预期"一栏都是按源码推断的。

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令（建议，未执行）与预期 |
|---|---|---|---|---|
| 用仓库解释器导入 pandas（依赖已编译的 C 扩展） | `install.sh:54-69`（`build_ext --inplace`、`pip install -e .`、导入自检） | `python` 指向 `/testbed/.venv/bin/python`，Python 3.7.9（`environment_brief.md:10`） | 工作树不含编译产物（`worktree_manifest.json` 的 `not_included`）；没有写明 numpy 版本，也没写导入是否成功。`install.sh:77-80` 的第一组组合是 Python 3.7 + NumPy 1.17.*，与 3.7.9 对得上，推断 numpy 为 1.17.x | `cd /testbed && python -c "import pandas as pd, numpy as np; print(pd.__version__, np.__version__, pd.__file__)"`；预期没有 ImportError，`pd.__file__` 位于 `/testbed/pandas/` 下 |
| 确认 bottleneck 是否启用 | `requirements-dev.txt:47`；`nanops.py:37-49` | 没有提及 | 是否安装未知，而这决定了 `mean` 复现出来是什么样子 | `python -c "import pandas.core.nanops as n; print(n._BOTTLENECK_INSTALLED, n._USE_BOTTLENECK)"`；输出两个布尔值 |
| 复现（走确定路径的 `sum`） | 3.2 的调用链；`nanops.py:466-508` | 解释器可用 | 无 | `python -c "import numpy as np, pandas as pd; df = pd.DataFrame({'A': np.arange(10), 'B': pd.Series(range(1, 11), dtype='Int64')}); print(df.sum(numeric_only=True))"`；在 base 上预期抛 `ValueError: the 'dtype' parameter is not supported in the pandas implementation of sum()`，traceback 依次经过 `frame.py` 的 `blk_func`、`managers.py` 的 `reduce`、`nanops.py` 的 `nansum`、`integer.py` 的 `sum`；修复后预期打印 A=45、B=55 的 Series |
| 复现题面的 `mean`（强制关闭 bottleneck） | 题面示例；`nanops.py:115-129`；公开测试也用 `pd.option_context("use_bottleneck", False)` 关闭它（`test_analytics.py:432`） | 同上 | bottleneck 分支的行为未知 | `python -c "import numpy as np, pandas as pd; pd.set_option('compute.use_bottleneck', False); df = pd.DataFrame({'A': np.arange(10), 'B': pd.Series(range(1, 11), dtype='Int64')}); print(df.mean(numeric_only=True))"`；在 base 上预期抛同一个 ValueError；修复后预期得到 A=4.5、B=5.5，dtype 为 float64。去掉 `set_option` 再跑一次，看启用 bottleneck 时的表现 |
| 对照期望值 | `series.py:4003-4005`；`integer.py:556-575` | 同上 | 不要用 `df.mean()` 当对照：按 R8 的静态推断，它会丢掉 B 列 | 在上面的脚本末尾加上 `import pandas._testing as tm; tm.assert_series_equal(df.mean(numeric_only=True), pd.Series({c: df[c].mean() for c in df.columns}))`；修复后预期静默通过。可以换成 `sum/prod/min/max/median/std/var` 以及含 `pd.NA` 的列再各跑一遍 |
| 跑公开测试（窄范围） | `run_tests.sh` 用 `.venv/bin/python -m pytest`；`install.sh:42` 安装了 pytest 和 hypothesis；`pandas/conftest.py:28-29` 需要 import hypothesis | 资源为 2 CPU / 4 GiB，`/tmp` 1 GiB（`environment_brief.md:12`） | 没有确认 venv 里是否真的有 pytest 和 hypothesis；`pytest-xdist` 只列在 `requirements-dev.txt` 里，不宜用 `-n` | `python -m pytest pandas/tests/frame/test_analytics.py -q -k "mean or sum or numeric_only or stat_op"`；`python -m pytest pandas/tests/arrays/integer/test_function.py -q`；`python -m pytest pandas/tests/extension/test_integer.py -q -k reduce`。base 和修复后都应通过，重点看 `test_mean_datetimelike_numeric_only_false`（P3） |
| 官方评分脚本 | `run_tests.sh:1` 运行 `r2e_tests` | — | `r2e_tests` 是隐藏测试，不在工作树里 | `bash run_tests.sh`；预期 pytest 报找不到 `r2e_tests`，不能用来自检 |
| 重新编译扩展 | `install.sh:54-58`；`Makefile:11-12` | 没有提及编译器和 Cython | 不能联网；镜像里有没有编译工具未知 | 本题的失败链路全在 `.py` 文件里（`frame.py`、`nanops.py`、`integer.py`、`compat/numpy/function.py`），只改纯 Python 代码不需要重新编译；只有改了 `.pyx` 才需要执行 `python setup.py build_ext --inplace` |
| 联网 / 装包 | `public_hints` 声称 pip 可用 | 有 pip，但无出网（`environment_brief.md:11`） | 装不了新包 | 本题用不到。即使缺 bottleneck 也补装不了，但这只影响复现时看到的现象 |

## 5. 阅读范围

实际打开的文件（`worktree/` 内的写相对路径）：
- 角色卡；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`；`worktree_manifest.json`：只看了顶层键和 `initial_diff`、`untracked_*` 两段，并在 `files` 列表里检索了 `r2e` 和 `.so`，没有打开 `initial_diff.source` 指向的 `PUBLIC_DIR` 以外的路径。
- 构建与说明文件：`install.sh`、`run_tests.sh`、`setup.cfg`、`test.sh`、`test_fast.sh`、`test_rebuild.sh`、`requirements-dev.txt`、`Makefile`、`README.md`（安装一节）、`pandas/__init__.py`（版本相关行）、`pandas/_version.py`（文件开头）。
- 源码：
  - `pandas/core/frame.py`：`_reduce`（8264-8420）、`_numeric_only_doc`、`_is_homogeneous_type`、`transpose`、`_iter_column_arrays`
  - `pandas/core/nanops.py`：1-360、380-700、745-792、836-875、1124-1230
  - `pandas/core/arrays/integer.py`：1-130、429-474、540-610
  - `pandas/core/arrays/masked.py`：全文
  - `pandas/core/arrays/base.py`：380-400、1015-1050
  - `pandas/core/arrays/datetimelike.py`：1540-1660
  - `pandas/core/array_algos/masked_reductions.py`：全文
  - `pandas/core/internals/managers.py`：329-353、705-720
  - `pandas/core/internals/blocks.py`：类列表、1636-1650
  - `pandas/core/series.py`：3985-4034
  - `pandas/core/generic.py`：统计方法工厂与 `_num_doc`
  - `pandas/core/apply.py`：80-380
  - `pandas/core/construction.py`：338-386
  - `pandas/compat/numpy/function.py`：1-80、250-281
  - `pandas/util/_validators.py`：54-69
  - `pandas/core/dtypes/base.py`：290-320
  - 只做了检索：`pandas/core/arrays/sparse/array.py`、`pandas/core/arrays/boolean.py`、`pandas/core/arrays/numpy_.py`、`pandas/core/arrays/sparse/dtype.py`、`pandas/core/config_init.py`、`pandas/compat/_optional.py`、`pandas/conftest.py`
- 测试与文档：
  - `pandas/tests/frame/test_analytics.py`：1-300、420-1154、1225 至文件末尾
  - `pandas/tests/extension/base/reduce.py`
  - `pandas/tests/arrays/integer/test_function.py`：60-140
  - `pandas/tests/reductions/test_reductions.py`：350-366，外加检索
  - `pandas/tests/groupby/test_groupby.py`：770-795
  - `doc/source/whatsnew/v1.1.0.rst`：检索，外加 500-520、560-590、730-760

没有查的范围：修复对其它测试目录的回归影响、Cython 源码、Sparse 和 boolean 等其它 EA 在修复后的具体行为、上游提交历史（工作树不含 `.git`，按要求也不查上游）。

限制：
- `user_prompt.txt` 只是当前 `render_user_prompt` 的静态渲染结果，不是捕获到的模型实际消息。`public_hints` 是否出现在模型消息里、以什么形式出现，都没有核实。
- `worktree/` 不是完整的运行容器，里面没有 `.venv`、编译好的扩展、`.git` 和隐藏测试。numpy、bottleneck、pytest 的实际版本和可用性，pandas 能否成功导入，在资源限制下能否正常运行，都没有验证。
- 本文所有"会报错 / 会返回"的说法都是静态推断，没有执行任何命令。
- 没有读到任何私有材料（gold 补丁、隐藏测试、期望结果、旧的审查结论）。
