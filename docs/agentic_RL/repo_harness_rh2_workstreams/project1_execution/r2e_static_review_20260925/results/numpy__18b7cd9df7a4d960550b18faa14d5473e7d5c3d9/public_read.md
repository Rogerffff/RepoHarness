# numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9 公开读者报告

- 角色：R2E 公开读者（静态审查，不解题）；日期 2026-09-25。
- 只读了角色卡和本题公开包 `PUBLIC_DIR = runs/r2e_static_prep_20260924/v2/public/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9/`。下文路径都相对 `PUBLIC_DIR`；`worktree/` 下的路径就是解题者在 `/testbed` 看到的路径。
- 没有运行项目代码，没有联网，也没有修改 `worktree/`。文中的"预期现象"都是读源码推出来的；标"静态推断"的结论还要结合 Python 比较协议或 NumPy C 层源码才能得出。
- 本上下文没有接触本题私有材料（gold 补丁、隐藏测试、期望结果、旧审查结论）。

## 0. 题目与初态速览

- 题面（`user_prompt.txt:3-22`）：`poly1d` 与非 `poly1d` 对象（示例是 `None`）比较时抛 `AttributeError`；期望不抛异常，返回 `False` 或 `NotImplemented`。
- base 提交 `6a3edf3210b4…`（`public_bundle.json:9`），NumPy 1.13.0 开发版（`worktree/setup.py:64-68`）。
- 问题代码在 `worktree/numpy/lib/polynomial.py:1201-1207`（base 原文）：

  ```python
  def __eq__(self, other):
      if self.coeffs.shape != other.coeffs.shape:
          return False
      return (self.coeffs == other.coeffs).all()

  def __ne__(self, other):
      return not self.__eq__(other)
  ```

- 初态：`worktree_manifest.json` 的 `initial_diff` 为 0 字节，所以工作树就是 base 的 966 个跟踪文件加上未跟踪的 `run_tests.sh`。镜像里另一个未跟踪文件 `install.sh` 没有收入公开包。

## 1. 需求表

| # | 行为 | 改变 / 保留 | 性质 | 依据 |
|---|---|---|---|---|
| R1 | `poly1d([1, 2, 3]) == None` 不再抛 `AttributeError`，表达式结果为 `False` | 改变 | 明示 | 题面 `user_prompt.txt:11-18`；base 在 `worktree/numpy/lib/polynomial.py:1202` 读取 `other.coeffs` |
| R2 | 与任意非 poly1d 对象比较都不抛异常，并表示"不相等" | 改变 | 明示（题面用泛称 "a non-`poly1d` object"），但只举了 `None` 一个例子 | `user_prompt.txt:7,18`；base 第 1202 行对任何没有 `coeffs` 属性的对象（`int`、`list`、`str`、`ndarray` 等）都会抛 |
| R3 | `poly1d.__eq__(非 poly1d)` 的方法返回值 | 改变 | 明示为 `False` 与 `NotImplemented` 二选一，没指定哪一个 | `user_prompt.txt:18` |
| R4 | `p != None` 不抛异常，结果为 `True` | 改变 | 推知：题面没提 `!=`，但 `__ne__` 直接调用 `self.__eq__`（`polynomial.py:1206-1207`），base 下同样会抛；"不相等"取反后就是 `True` | 代码 |
| R5 | 反向写法 `None == p` 不抛异常，结果为 `False` | 改变 | 推知：`None` 一侧返回 `NotImplemented` 后，Python 会反射调用 `poly1d.__eq__(p, None)`，base 下同样会抛 | Python 比较协议 + `polynomial.py:1202` |
| R6 | `numpy.testing.assert_equal(np.poly1d([1]), np.poly1d([1]))` 这类比较 0 次多项式的断言不再崩 | 改变（同一根因的另一条触发路径） | 推知（静态推断）：只有 1 个系数时，`assert_equal` 会走到 `desired == 0`（`worktree/numpy/testing/utils.py:391`）。base 下这里抛 `AttributeError`，而第 396 行只捕获 `TypeError`、`ValueError`、`NotImplementedError` | 代码 |
| R7 | poly1d 与 poly1d 之间：形状不同为 `False`；形状相同则系数逐项相等才为真；`!=` 取反；`variable` 不参与比较 | 保留 | 现有代码和公开测试都明确体现 | `polynomial.py:1201-1207`；`worktree/numpy/lib/tests/test_regression.py:81-86`（`test_poly_eq`：`x != y`、`x == x`），以及 `:18-21`、`:74-79`（用 `assert_equal` 比较 poly1d） |
| R8 | 其余接口不变：`__hash__ = None`、算术方法对 `other` 的强制转换、`__array__` 提供的数组语义 | 保留 | 推知（题面没要求改这些） | `polynomial.py:1042, 1065-1069, 1145-1199`；docstring `:1011-1018`；doctest `worktree/numpy/lib/tests/test_polynomial.py:48-49` |
| R9 | 与 `ndarray` 或 NumPy 标量比较时，得到标量 `False` 还是逐元素布尔数组 | 未定 | 多种解释：取决于 R3 选 `False` 还是 `NotImplemented`（见 §2 B），题面没涉及 | 静态推断，见 §2 B |
| R10 | 带 `coeffs` 属性的非 poly1d 对象（鸭子类型）以及 poly1d 子类 | 未定 | 多种解释：base 按鸭子类型读 `other.coeffs`；题面说非 poly1d 应"不相等" | `polynomial.py:1202` |
| R11 | `poly1d([1, 2, 3]) == [1, 2, 3]` 这类系数相同的非 poly1d 对象 | 未定，题面字面倾向"不相等" | 有多种实现，但题面字面排除了"按系数相等" | `user_prompt.txt:18`；与算术方法的强制转换惯例（`polynomial.py:1159-1181`）不同 |
| R12 | 只改非测试源码 | 约束 | 来源提示里的操作指令 | `public_bundle.json:15` |

## 2. 合理实现范围

任何实现都应满足 R1、R2、R4、R5，并且不回归 R7。题面没有要求新增名字、参数、报错信息或文档。下面 A、B 两类实现都让表达式 `p == None` 得到 `False`。

- **A. 类型判断后返回 `False`**（例如 `isinstance(other, poly1d)` 不成立时）。`__ne__` 不用改，`p != None` 就是 `True`。这与仓库里新多项式类的写法一致：`worktree/numpy/polynomial/_polybase.py:437-446` 在 `isinstance` 不成立时返回 `False`，`__ne__` 写成 `not self.__eq__(other)`。与 `ndarray` 比较时返回标量 `False`。应接受。
- **B. 类型判断后返回 `NotImplemented`，同时让 `__ne__` 正确处理这种情况**（例如 `__ne__` 对非 poly1d 也返回 `NotImplemented`，或对 `==` 运算的结果取反）。`p == None` 和 `None == p` 会由 Python 回退到身份比较，得到 `False`；`p != None` 得到 `True`。静态推断的副作用：`p == np.array([1, 2, 3])` 会交给 ndarray 的反射比较。poly1d 没有 `__array_priority__` 和 `__numpy_ufunc__`，ndarray 不会让位（`worktree/numpy/core/src/multiarray/number.c:126-154, 290-323`，`arrayobject.c:1405-1412`），于是经 `__array__` 按系数逐元素比较，结果是 `[ True  True  True]`，不是 `False`。题面允许 `NotImplemented`，应接受。
- **C. 用 `try/except AttributeError` 或 `getattr(other, 'coeffs', None)` 识别没有系数的对象，再返回 `False` 或 `NotImplemented`。** 与 A、B 的差别只在 R10：带 `coeffs` 属性的对象仍按系数比较。题面没约定这类对象，应接受；对 `__ne__` 的要求同 A、B。
- **D.（不完整）只让 `__eq__` 返回 `NotImplemented`，`__ne__` 仍是 `not self.__eq__(other)`。** 这时 `p == None` 正确，但 `p != None` 在 Python 3.7.9 下是 `not NotImplemented`，静默得到 `False`（Python 3.9 起才对这种用法发 DeprecationWarning）。它满足题面字面，却违反 R4。题面既允许 `NotImplemented` 又不提 `!=`，最容易诱发这种实现；隐藏测试是否检查 `!=` 未知。
- **E.（与题面冲突）仿照算术方法，用 `poly1d(other)` 强制转换后再比较。** 这样 `poly1d([1, 2, 3]) == [1, 2, 3]` 会变成 `True`，违背"表示不相等"；二维输入会在 `polynomial.py:1054-1055` 抛 `ValueError`，违背"不应抛异常"。如果隐藏测试只测 `None`，这种实现也可能通过（未知）。
- **F. 删除 `__ne__`，依赖 Python 3 从 `__eq__` 自动派生。** 在本环境（Python 3.7.9）配合 A 或 B，行为是对的。但本提交仍声明支持 Python 2.7（`worktree/setup.py:49-50`、`worktree/.travis.yml:33-37`）。Python 2 不会自动派生，`!=` 会退回身份比较，`poly1d([1]) != poly1d([1])` 会变成 `True`。这对仓库是回退；评分只在 3.7 下运行，可能看不出来（推测）。

题面没有约定的有：R3 选哪一个、R9 到 R11 的边界，以及 `__eq__` 比较两个 poly1d 时返回 `numpy.bool_`（`.all()` 的结果）还是 Python `bool`。除上面几类之外，想不出其它有实质差别的实现。

## 3. 题面质量与初态线索

**3.1 是否直接给出或强烈暗示修法。** 题面强烈暗示了修法方向，但没给代码。标题点名 `poly1d.__eq__`（`user_prompt.txt:4`）；Actual Behavior 直接说出根因，即访问非 poly1d 对象的 `coeffs`（`:21`）；Expected Behavior 列出两种可接受的返回值（`:18`）。修法因此基本确定为"在 `__eq__` 里识别非 poly1d"。示例代码（`:11-14`）只是复现，不是修好后的实现。剩下的难点主要是 `__ne__` 和返回值的选择。

**3.2 题面描述的报错能否从 base 源码读出。** 能。`worktree/numpy/lib/polynomial.py:1202` 先求 `self.coeffs.shape`，再求 `other.coeffs`。`other` 为 `None` 时抛 `AttributeError: 'NoneType' object has no attribute 'coeffs'`，与题面注释一致（Python 3 的报错格式）。类属性 `coeffs = None`（`:1039`）只定义在 poly1d 上，不会影响 `None`。

**3.3 题面示例在 base 接口下是否成立。** 成立。`poly1d` 在 `polynomial.py:7-9` 的 `__all__` 里，经 `worktree/numpy/lib/__init__.py:18` 和 `worktree/numpy/__init__.py:162` 暴露为 `numpy.poly1d`；`poly1d([1, 2, 3])` 是合法构造（`polynomial.py:1044-1063`）。

**3.4 题面的不精确与遗漏。**
- "the comparison should return `False` or `NotImplemented`"（`:18`）混淆了方法返回值和表达式结果。表达式 `p == None` 在 A、B 两类实现下都是 `False`；只有直接调用 `p.__eq__(None)` 才看得到 `NotImplemented`。如果评分直接断言 `p.__eq__(None)` 的具体值，题面允许的另一种实现就会失败（隐藏测试未知）。
- 没提 `!=`。它与 `==` 是同一根因（`polynomial.py:1206-1207`），而且和返回值的选择相互影响（§2 D）。
- 没界定"非 poly1d 对象"的范围：`ndarray` 和 NumPy 标量、带 `coeffs` 的对象、子类都没说（R9 到 R11）。
- 标题里的 "Crashes" 指抛异常，不是进程崩溃，不影响理解。

**3.5 `public_hints` 分类**（`public_bundle.json:15`）。`user_prompt.txt` 里没有这些提示，它们是否真的进入模型消息，公开材料看不出来。
- 题目需求："find the root cause, and edit NON-TEST source files"。与本题一致，修复只需改 `numpy/lib/polynomial.py`。
- 给解题者的操作指令：不要改测试文件；测试只跑单个文件或模块；确信完成后简短总结并停止调用工具。这与 2 CPU / 4 GiB 的资源相符；只跑单个文件也正好避开了同名测试模块冲突（见 §4）。
- 环境事实声明：
  - "pre-activated conda env named `testbed`… `pip` and the repo's test tools already point at it" 与 `environment_brief.md:10-13` 不符：`python` 指向 `/testbed/.venv/bin/python`，没有 pip 和 uv，直接运行 `pytest` 收集会失败。照提示做（`pip install -e .`、`conda activate`、直接运行 `pytest`）会浪费步数，但不影响合法修复。
  - "grading resets the test files… test edits never count"：按角色卡，这不是本来源的实际机制。本题不需要改测试，不影响合法解法。
  - "fixing a real GitHub issue" 与 R2E 题面由模型生成的事实不符，不影响解法。

**3.6 定位与调查入口。** 公开材料足够。标题直接指向 `polynomial.py:1201`；复现只要一行（`user_prompt.txt:13-14`）；体现现有等式语义的公开测试在 `worktree/numpy/lib/tests/test_regression.py:81-86`；仓库内可对照的写法在 `worktree/numpy/polynomial/_polybase.py:437-446`。`worktree/numpy/lib/tests/test_polynomial.py` 里没有 poly1d 的 `==` 或 `!=` 测试，只比较系数数组（`:193`、`:195`、`:200-201`）。

**3.7 初态线索。**
- `worktree_manifest.json` 的 `initial_diff` 为 0 字节，镜像初态相对 base 没有改动，不需要区分"初态改动"和题目本身。
- `worktree/run_tests.sh:1` 执行 `.venv/bin/python -W ignore -m pytest -rA r2e_tests`。`r2e_tests/` 不在公开工作树（manifest 的 `not_included` 里列了隐藏测试），解题时是否存在未知，不能当作解题者的验证入口。`install.sh` 在镜像里，但没收入公开包，内容未知。
- 导入 numpy 依赖构建产物：`numpy/__config__.py`、`numpy/version.py` 和 `*.so` 都被 `.gitignore` 忽略（`worktree/.gitignore:39, 103, 107`），不在工作树里。缺 `__config__.py` 时，`import numpy` 会抛 `worktree/numpy/__init__.py:125-131` 的 "you should not try to import numpy from its source directory"。`environment_brief.md:13` 说 `/testbed` 在 `sys.path` 上即可导入，说明镜像里做过就地构建；公开包无法静态确认这一点。

**3.8 哪些缺失会真正阻碍开发。** 没有。定位、复现和根因都能直接得到；`__ne__` 与 `__eq__` 的依赖关系读相邻 5 行就能发现，属于正常读代码。公开材料解决不了的是 R3 的二选一和 R9 到 R11 的范围。这不妨碍写出修复，但决定了题面允许的各种实现能否都通过评分（隐藏测试未知）。环境层的未知（是否装了 nose、pytest 版本）只影响对公开测试结果的解读。

## 4. 开发需求表

命令一律为**建议，未执行**；预期现象来自读源码。

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令与预期现象 |
|---|---|---|---|---|
| 定位代码 | 标题点名 `poly1d.__eq__`；`worktree/numpy/lib/polynomial.py:1201-1207` | 工作目录是 `/testbed`（`:10`） | 无 | `cd /testbed && grep -n "def __eq__\|def __ne__" numpy/lib/polynomial.py`，预期输出第 1201、1206 行 |
| 从源码树导入 numpy | `environment_brief.md:10,13`；`worktree/numpy/__init__.py:125-131` | 环境阶段实测：`python` 是 `/testbed/.venv/bin/python`（3.7.9），`/testbed` 在 `sys.path` 上即可导入 | 就地构建产物不在公开包；Python 3.7 超出本提交声明支持的 3.6（`worktree/setup.py:47-55`），整体兼容性未验证 | `cd /testbed && python -c "import sys, numpy; print(sys.version.split()[0], numpy.__version__, numpy.__file__)"`，预期 `3.7.9`、`1.13.0.dev0+…`、`/testbed/numpy/__init__.py`；若构建产物缺失，会看到 3.7 节那条 ImportError |
| 复现原 bug（`==`） | `user_prompt.txt:11-14`；`polynomial.py:1202` | 同上 | 无 | `cd /testbed && python -c "from numpy import poly1d; p = poly1d([1, 2, 3]); print(p == None)"`。base：`AttributeError: 'NoneType' object has no attribute 'coeffs'`；修后：`False` |
| 同一根因的其它入口（`!=`、反向比较、其它类型、方法返回值） | `polynomial.py:1206-1207`；Python 比较协议 | 同上 | 题面没规定 `p.__eq__(None)` 取哪个值 | `cd /testbed && python -c "from numpy import poly1d; p = poly1d([1, 2, 3]); print(p != None, None == p, p == 3, p == [1, 2, 3], p.__eq__(None))"`。base：`AttributeError`。A、B 类修后：前四项为 `True False False False`，最后一项为 `False` 或 `NotImplemented`。第一项若是 `False`，说明 `__ne__` 仍在对 `NotImplemented` 取反（§2 D）；第四项若是 `True`，说明用了强制转换（§2 E） |
| `numpy.testing` 触发路径（可选） | `worktree/numpy/testing/utils.py:381-397` | 同上 | 属于静态推断 | `cd /testbed && python -c "import numpy as np; np.testing.assert_equal(np.poly1d([1]), np.poly1d([1])); print('ok')"`。base：`AttributeError: 'int' object has no attribute 'coeffs'`；修后：`ok` |
| 与 ndarray 比较（可选，只用来确认自己选了哪类实现） | `worktree/numpy/core/src/multiarray/number.c:290-323`；`arrayobject.c:1405-1412` | 同上 | 题面没规定（R9） | `cd /testbed && python -c "import numpy as np; p = np.poly1d([1, 2, 3]); print(p == np.array([1, 2, 3]))"`。base：`AttributeError: 'numpy.ndarray' object has no attribute 'coeffs'`；A 类修后：`False`；B 类修后：`[ True  True  True]` |
| 检查保留行为的公开测试 | `test_regression.py:18-21, 74-79, 81-86`；`test_polynomial.py` 全文 | `python -m pytest` 可用，直接运行 `pytest` 收集会失败（`:13`） | pytest 版本和是否装了 nose 都未知。`assert_raises` 需要 nose（`worktree/numpy/testing/utils.py:52-70, 1161-1188`），没装 nose 时 `test_polyfit`（`test_polynomial.py:141-142`）会因与本题无关的原因失败。各 `tests/` 目录都没有 `__init__.py`，一次调用里混跑不同目录的同名文件（例如 7 个 `test_regression.py`）可能报 import file mismatch | `cd /testbed && python -m pytest -rA numpy/lib/tests/test_regression.py -k poly`，预期修前修后都通过（包含 `test_poly_eq`，选中的用例都不用 `assert_raises`）。`cd /testbed && python -m pytest -rA numpy/lib/tests/test_polynomial.py`，预期修前修后结果一致；如果 `test_polyfit` 报 "Need nose >= 1.0.0"，那是环境问题 |
| 官方评分脚本 | `worktree/run_tests.sh:1` | 未提及 | `r2e_tests/` 不在公开工作树，解题时是否存在未知 | 不建议作为验证入口。若该目录不存在，`cd /testbed && bash run_tests.sh` 预计会报找不到 `r2e_tests`（推测） |
| 装包、联网 | 修复是纯 Python，不需要新依赖 | 没有 pip 和 uv，无出网（`:11`） | 无 | 不需要 |
| 重新构建 | `polynomial.py` 是纯 Python 模块，就地导入，改完即生效（推知） | 未提及构建工具 | 无 | 不需要；也不要用 `runtests.py`，它会先构建项目（`worktree/runtests.py:5`） |
| 资源 | 无 | 2 CPU、4 GiB，`/tmp` 1 GiB，以 uid 54321 运行，可写 `/testbed`（`:12`） | 无 | 上面的命令规模都很小，资源足够（推测） |

## 5. 阅读范围

实际打开的文件（路径相对 `PUBLIC_DIR`）：
- 角色卡；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md` 全文。
- `worktree_manifest.json`：用脚本读了顶层键、`export`、`initial_diff`、`untracked_*`，并核对 `files` 列表与磁盘一致（967 项，双向都没有缺失）。其中指向公开包以外的路径（`initial_diff.source`）没有打开。
- `worktree/numpy/lib/polynomial.py`：第 1-30 行、第 920-1278 行（`poly1d` 类全文），以及全文 grep。
- `worktree/numpy/lib/tests/test_polynomial.py` 全文；`worktree/numpy/lib/tests/test_regression.py` 第 1-100、115-125、185-200 行。
- `worktree/numpy/testing/utils.py` 第 50-75、94-128、289-406、1110-1215 行附近；`worktree/numpy/testing/__init__.py` 全文。
- `worktree/numpy/polynomial/_polybase.py` 第 437-446 行；`worktree/numpy/lib/type_check.py` 中的 `iscomplexobj`；`worktree/numpy/lib/__init__.py` 和 `worktree/numpy/__init__.py`（grep，以及后者第 100-131 行）。
- `worktree/numpy/core/src/multiarray/arrayobject.c` 第 1300-1420 行；`worktree/numpy/core/src/multiarray/number.c` 第 91-154、290-323 行。
- `worktree/setup.py`（grep）、`.travis.yml` 第 1-60 行、`tox.ini` 第 1-60 行、`runtests.py` 第 1-40 行、`README.md`、`CONTRIBUTING.md`、`INSTALL.rst.txt`（grep）、`.gitignore`（grep）、`run_tests.sh`。
- `worktree/doc/release/1.13.0-notes.rst` 第 40-62、260-280 行：只有 `array == None` 和对象数组 `np.equal` 的变更说明，没有 poly1d 条目。`worktree/doc/source/reference/routines.polynomials.poly1d.rst`。
- 在整个工作树里 grep 了 `poly1d`、`return NotImplemented`、`def __eq__` 和 `def __ne__`。

没查的范围：其它子包的测试与实现；C 源码中比较路径以外的部分；`benchmarks/`、`tools/`；git 历史（公开包不含 `.git`）；`install.sh`（没收入公开包）。

限制：
- `user_prompt.txt` 只是当前渲染器的静态输出，不是捕获到的模型请求；`public_hints` 是否以及如何进入模型消息未知。
- `worktree/` 不是完整的运行容器，不含 `.venv`、编译扩展、构建生成的文件和隐藏测试。§4 里的环境事实全部转引自 `environment_brief.md`，本角色没有验证。
- 所有预期现象（包括标"静态推断"的 NumPy C 层行为）都没有运行确认。本报告不声称模型实际收到的消息、运行资源或开发条件已经验证。
