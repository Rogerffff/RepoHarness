# orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237：公开读者报告

- 角色：公开读者（静态审查，不解题）；日期：2026-09-25。
- 只读了角色卡和 `PUBLIC_DIR`。下文路径都相对 `PUBLIC_DIR`，`owcreateclass.py` 指 `worktree/Orange/widgets/data/owcreateclass.py`，`test_owcreateclass.py` 指 `worktree/Orange/widgets/data/tests/test_owcreateclass.py`。
- 没有运行项目代码，没有联网，没有读到任何私有材料。文中所有"base 行为"和"测试结果"都是静态推演。

## 要点

- **要改的行为只有一处**：`owcreateclass.py:150-158` 中 `unique_in_order_mapping` 返回的 `mapping` 是错的。按 base 代码推演，输入 `[2, 3, 1]` 得到 `mapping = [2, 0, 1]`，和题面"实际行为"的数值一致。
- **原因能直接从代码读出**：第 157 行用置换 `p = np.argsort(idx)` 本身去索引 `inv`，正确做法需要用 `p` 的逆置换。两者只在 `p` 是对合（自身的逆）时相同。现有 5 组公开用例（`test_owcreateclass.py:76-91`）里的 `p` 都是恒等或对合，所以 base 能通过全部公开用例，公开测试暴露不了这个 bug。
- **最大的题面质量问题**：题面里标成 "Example Buggy Code" 的代码块（`user_prompt.txt:14-23`）不是仓库实现。按推演，它对 `[2, 3, 1]` 返回的正是题面期望的 `[0, 1, 2]`，5 组公开用例也全部符合。也就是说，题面把一份正确实现标成了"有 bug"，等于直接交出了可用修法；而照题面示例运行只会看到期望输出，复现不出 bug。
- **关键未知**：返回类型没有约定（base 返回 `ndarray`，题面代码块返回 `list`）；隐藏测试的比较方式不知道（`run_tests.sh` 指向的 `r2e_tests` 不在工作树里）；运行环境中 Cython 扩展是否已构建、pytest 是否已装、导入 widget 模块是否需要显示，都只能推知，未验证。

## 1. 需求表

| # | 需求 | 改变 / 保留 | 依据 | 确定程度 |
|---|---|---|---|---|
| R1 | 输入 `[2, 3, 1]`：返回 unique `[2, 3, 1]`，mapping `[0, 1, 2]` | 改变 | 题面 `user_prompt.txt:31-37` | 明示 |
| R2 | 一般规则：对任意输入 `a`，`mapping[i]` 是 `a[i]` 在返回的 unique 列表中的下标，即 `unique_in_order[mapping[i]] == a[i]`；mapping 长度等于 `len(a)` | 改变 | 题面 `user_prompt.txt:8`；docstring `owcreateclass.py:151-154`（"indices of the input list onto the returned uniques"）；公开用例 `[2,1,2,3] → [0,1,0,2]`（`test_owcreateclass.py:89-91`） | 题面只给一个例子；一般规则由 docstring 和公开用例推出，没有歧义（可推知） |
| R3 | unique 列表仍按元素首次出现的顺序排列。base 这一项本来就对 | 保留 | 题面 L8，以及 L34、L42 两处 unique 都是 `[2, 3, 1]`；docstring L152；公开用例 L86-91 | 明示 |
| R4 | 现有 5 组公开用例继续成立：`[]→([],[])`、`[42]→([42],[0])`、`[42,42]→([42],[0,0])`、`[2,1,0,3]→([2,1,0,3],[0,1,2,3])`、`[2,1,2,3]→([2,1,3],[0,1,0,2])` | 保留 | `test_owcreateclass.py:76-91` | 明示（公开测试） |
| R5 | 函数名、单个位置参数、返回二元组不变；仍能从 `Orange.widgets.data.owcreateclass` 导入 | 保留 | 测试导入 `test_owcreateclass.py:9-12`；调用方解包 `owcreateclass.py:537` | 可推知（接口） |
| R6 | 与唯一调用方 `_create_variable` 兼容：两个返回值都可迭代；unique 元素能 `str()`；mapping 元素能被 `np.array(map_values, dtype=int)` 转换，转成 tuple 后可哈希（会进缓存键 `var_key` 和 `ValueFromStringSubstring.__hash__`） | 保留 | `owcreateclass.py:537-548`、`:38-41`、`:104-108` | 可推知 |
| R7 | 空输入不报错，返回两个空序列。调用方在规则全部删除后仍会用 `names=()` 调用 | 保留 | 公开用例 L77-79；`test_add_remove_lines` 删光规则后调用 `apply`（`test_owcreateclass.py:486-491`），经 `owcreateclass.py:526-537` 进入本函数 | 明示 + 可推知 |
| R8 | 输入既可能是 int 列表（测试），也可能是 str 元组（调用方传入的类名） | 保留 | `test_owcreateclass.py:77-91`；`owcreateclass.py:531-537` | 可推知 |
| R9 | 返回类型（`ndarray`、`list` 或 `tuple`）和元素类型（`np.int64` 还是 `int`，`np.str_` 还是 `str`） | 未约定 | docstring 没说；base 返回 `ndarray`；题面代码块返回 `list`，题面的输出格式也是 list 风格（带逗号） | 有多种合理解释 |
| R10 | 混合类型或不可哈希元素的语义。`np.unique` 会先统一 dtype，例如 `[1, "1"]` 会被当成同一个 `'1'`；按哈希建表的做法会把两者分开 | 未约定 | 没有依据；调用方只传 str | 有多种合理解释（与本题主线无关） |
| R11 | Widget 层后果：规则类名的首现顺序与字典序不同、且对应置换不是对合时，实例会被分到错误的类值。例：类名依次为 `b, c, a` 时，base 得到 `map_values = (2, 0, 1)`，命中规则 `b` 的实例被标成 `a`。默认标签编到 `C10`、且这些规则都有效时也会触发（字典序 `C10 < C2`）。按静态阅读，调用方把 mapping 当作"第 i 条规则在 names 中的下标"使用（`owcreateclass.py:537-548`，再到 `map_by_substring` 的 L46-49），与 docstring 一致；只要 helper 满足 R2，调用方不用另改 | 间接改变 | `owcreateclass.py:21-50`、`:523-552`；静态推演 | 可推知（题面没提 widget 层） |

**base 推演**（`owcreateclass.py:155-157`，输入 `[2, 3, 1]`）：

- `u = [1, 2, 3]`，`idx = [2, 0, 1]`，`inv = [1, 2, 0]`，`p = np.argsort(idx) = [1, 2, 0]`
- `unique_in_order = u[p] = [2, 3, 1]`：正确
- `mapping = p[inv] = [2, 0, 1]`：错误，应为 `[0, 1, 2]`

公开用例 `[2,1,0,3]` 的 `p = [2,1,0,3]`，`[2,1,2,3]` 的 `p = [1,0,2]`，都是对合，所以 `p[inv]` 碰巧正确。`[2,3,1]` 的 `p` 是三元轮换，不是对合，bug 才显现。现有 widget 用例用到的类名组合（`C1`/`C2`、`Cls1`/`Cls2`/`Cls3`、`repeated`/`not repeated`/`repeated`、空元组）同样都是恒等或对合，也触发不了。

## 2. 合理实现范围

以下几类实现都应接受。这里只描述思路，不写修复：

1. **保留 `np.unique` 路径**，对排序置换取逆之后再按 `inv` 取值。返回 `ndarray`，与 base 类型一致。
2. **纯 Python 单遍扫描**，按首次出现顺序建"元素 → 新下标"的表。题面代码块就属于这一类。仓库里已有保序去重的先例：`worktree/Orange/widgets/data/oweditdomain.py:56-61` 用 `dict.fromkeys`，这依赖 Python 3.7 起保证的字典插入顺序，环境是 3.7.9（`environment_brief.md:10`）。返回 `list`，也可以再包成数组。
3. **调用已有依赖里"按出现顺序编码"的现成函数**，例如 pandas 的因子化。`pandas>=1.0.0` 列在 `worktree/requirements-core.txt:23`，但镜像里是否安装、是什么版本都没核实。

按静态推理，三类都满足 R1-R8，差别只在 R9、R10。

**各项约定的情况**

- 名称：函数名和所在模块已被测试导入和调用方固定；不需要新增参数。
- 输出：返回类型没有约定。公开测试用 `np.testing.assert_equal`，拿 `ndarray`、`list` 或 `tuple` 去比 list 期望值都能通过；调用方也会先转成 tuple。如果隐藏测试改用 `assertEqual`，或者检查类型、dtype，不同返回类型的结果就会不同，公开材料判断不了。
- 题面示例里的 `print("Unique Elements:", ...)` 和 `print("Mapping:", ...)` 只是用法演示，不是必须产生的输出。
- 题面没要求改调用方、用户文档或 `CHANGELOG.md`。

**明显不满足需求的做法**（给审查者对照）

- mapping 直接等于 `range(len(a))`：能过题面唯一的例子（它没有重复元素），但违反 R4 中 `[42,42]` 和 `[2,1,2,3]` 两例。
- 只改调用方、不改 helper：题面和公开测试都直接调用 helper，违反 R1。
- 把 unique 改成排序后的顺序：违反 R3。

## 3. 题面质量与初态线索

### 3.1 题面是否直接给出或强烈暗示修法：是，而且标注错了

- `user_prompt.txt:12-29` 的 "Example Buggy Code" 和仓库实现不是一回事：仓库用 `np.unique`（`owcreateclass.py:155-157`），代码块（L14-23）用字典加列表单遍构造。
- 按推演，这段所谓"有 bug"的代码对 `[2, 3, 1]` 返回 `([2, 3, 1], [0, 1, 2])`，正好是题面的期望输出（L34-35），而不是题面说的实际输出（L42-43）。对 5 组公开用例，它也全部给出期望值。
- 影响有两点：
  - 题面自相矛盾："buggy code" 产生不了 "actual behavior"。
  - 解题者只要把这段代码替换进仓库，按静态推理就能同时满足题面和公开测试，题目的难度和区分度因此大幅下降。它是否与参考修复一致，本角色不判断。

### 3.2 题面描述的行为能否从 base 源码读出：数值能，格式对不上

- 数值：按 §1 的推演，base 对 `[2, 3, 1]` 返回 mapping `[2, 0, 1]`，与 L43 一致。
- 格式：base 返回 `ndarray`，`print` 显示的是不带逗号的 `[2 3 1]` 和 `[2 0 1]`；题面 L34-35、L42-43 却是 list 格式 `[2, 3, 1]`。所以"实际行为"那一段不是 base 的原样输出。
- 照抄题面 L25-28 的 "Example usage" 去运行，调用的是代码块自己定义的函数，会打印期望结果，复现不出 bug。要复现必须导入仓库里的函数（见 §4）。

### 3.3 题面示例在 base 接口下是否说得通：接口对得上，但例子太弱

- 调用方式 `unique_in_order_mapping([2, 3, 1])` 与 base 签名一致：一个参数，返回二元组。
- 示例输入没有重复元素，只看这一个例子，区分不了两种读法："每个输入元素在 uniques 中的下标"和"每个 unique 元素首次出现的位置"都会得到 `[0, 1, 2]`。docstring `owcreateclass.py:153`、公开用例 L89-91（`[2,1,2,3]→[0,1,0,2]`，长度跟输入走）和调用方 L536-548 能消除这个歧义，属于正常读代码的范围。
- 题面 L8 把返回值说成 "a list of unique elements"，base 实际返回 `ndarray`。这句话最多算弱暗示，不构成类型约定（见 R9）。
- 题面没给文件路径，但按函数名 grep 只有一处定义，不算缺陷。

### 3.4 public_hints 分三类（`public_bundle.json:15`）

- **题目需求**："find the root cause, and edit NON-TEST source files to fix the issue"。与题面一致。
- **给解题者的操作指令**：不改测试文件；测试只跑单个文件或模块；完成后简短总结，停止调用工具。本题只需改一个非测试函数，这些指令不妨碍合法解法。唯一的代价是：因为不能改测试文件，`[2,3,1]` 这类回归例子只能放在临时脚本里验证。
- **环境事实声明**：
  - "pre-activated conda env named `testbed`"：与 `environment_brief.md:10` 不符。实际是镜像环境变量让 `python` 指向 `/testbed/.venv/bin/python`（Python 3.7.9）。照提示执行 `conda activate testbed` 会失败，但直接用 `python` 不受影响。
  - "`pip` ... already point at it"：pip 有，但无法出网（`environment_brief.md:11`）。本题不需要新依赖。
  - "grading resets the test files ... test edits never count"：按角色卡，这不是本来源的实际机制。公开可见的 `worktree/run_tests.sh:1` 只跑 `r2e_tests` 目录。
  - "fixing a real GitHub issue"：按角色卡，R2E 题面是模型根据修复提交和测试生成的，不是原始 issue。对解法没有影响。

### 3.5 初态线索

- `worktree_manifest.json` 中 `initial_diff` 为 0 字节，说明镜像初态相对 base 没有改动。工作树 = base 的跟踪文件 + `run_tests.sh`。镜像里还有未跟踪的 `datasets` 和 `install.sh`，但没有收进本快照（见 `untracked_missing`）。
- 调查入口清楚：题面给的函数名 → `owcreateclass.py:150` 唯一定义 → 同文件 L537 唯一调用方 → 专门的公开用例 `test_owcreateclass.py:75-91`。用"用了置换而不是逆置换"这一条观察，就能解释为什么公开用例全过、题面例子却失败。
- 背景：`owcreateclass.py:536` 的注释 "join patters with the same names" 说明这个 helper 用来合并同名类值。`worktree/CHANGELOG.md:25`（3.28.0 的 Bugfixes）列有 "Create Class: multiple patterns for a class value (#5283)"，可能与此功能相关；没有核对 git 历史，不作结论。

### 3.6 会真正阻碍开发的缺失信息

- 没有。修复所需的信息，从题面加正常读代码都能拿到。
- 仍然未知、但不妨碍开发的：返回类型的期望；隐藏测试只测 helper 还是也测 widget 层；运行环境细节（见 §4）。

## 4. 开发需求表（命令一律为"建议，未执行"）

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令与预计现象 |
|---|---|---|---|---|
| 定位与编辑源码 | `public_bundle.json:5-8` 允许 `bash`、`edit`；题面给了函数名 | 工作目录 `/testbed`；agent 可写 `/testbed`（L10、L12） | 无 | `grep -rn "unique_in_order_mapping" /testbed/Orange` → 预计命中 `owcreateclass.py:150`（定义）、`:537`（调用），以及 `tests/test_owcreateclass.py:12`、`:76-91` |
| 只用 numpy 复现逻辑（不导入 Orange） | `owcreateclass.py:155-157`；`requirements-core.txt:2` 为 `numpy>=1.16.0` | Python 3.7.9 venv（L10）；brief 没单独写 numpy，但 Orange 本身依赖它 | numpy 版本未知（不影响这段逻辑） | `cd /testbed && python -c "import numpy as np; u,i,v=np.unique([2,3,1],return_index=True,return_inverse=True); p=np.argsort(i); print(u[p], p[v])"` → 预计输出 `[2 3 1] [2 0 1]` |
| 导入仓库函数复现 | 题面示例；模块顶部导入 AnyQt 和 widget 框架（`owcreateclass.py:7-18`） | brief 只说 widget 测试要带 Qt 前缀、纯库调用不需要（L13）；导入 widget 模块算哪一类没写 | (1) Cython 扩展：清单里有 `Orange/data/_valuecount.pyx` 等源文件，编译产物被 `.gitignore` 排除，brief 没说镜像里是否已构建。评分要导入 Orange，所以可推知已构建。(2) 仅导入是否需要显示：未知，保险起见带前缀 | `cd /testbed && QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -c "from Orange.widgets.data.owcreateclass import unique_in_order_mapping as f; print(f([2, 3, 1])); print(f(('b', 'c', 'a')))"` → base 下预计第一行为 `(array([2, 3, 1]), array([2, 0, 1]))`，第二行的 mapping 也是 `[2, 0, 1]`；修复后两例的 mapping 都应为 0、1、2（显示格式取决于返回类型） |
| 公开单测：只跑 helper | `test_owcreateclass.py:75-91` | 有 Qt 前缀（L13）。测试模块导入时就会加载 widget 和 Qt 相关模块（`test_owcreateclass.py:9-13`），所以只跑 helper 用例也建议带前缀。`run_tests.sh` 用 `.venv/bin/python -m pytest`，可推知已装 pytest | 现有用例在 base 上全过（静态推演），证明不了 bug；又不能改测试文件，回归例子只能放临时脚本 | `cd /testbed && QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -m pytest -q Orange/widgets/data/tests/test_owcreateclass.py -k unique_in_order_mapping` → 预计修复前后都是 1 passed，其余 deselected |
| 公开单测：整个文件（widget 回归） | `test_owcreateclass.py:228-567`；用到的数据集 `heart_disease`、`zoo`、`iris` 在 `worktree/Orange/datasets/` | 有 Qt 前缀；资源 2 CPU / 4 GiB（L12） | `WidgetTest` 继承自外部包 `orangewidget.tests.base`（`worktree/Orange/widgets/tests/base.py:18-20`），它的 Qt 初始化细节不在工作树里，没读；耗时未知 | `cd /testbed && QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -m pytest -q Orange/widgets/data/tests/test_owcreateclass.py` → 按静态推演，现有用例不触发这个 bug，预计修复前后结果相同（环境导致的失败未知）。用途是确认空输入路径（L486-491）和重复类名路径（L305-355）没被改坏 |
| 官方评分脚本 | `worktree/run_tests.sh:1` 执行 `pytest -rA r2e_tests` | brief 未提 | `r2e_tests` 既不在工作树里，也不在镜像的未跟踪清单（`worktree_manifest.json` 的 `untracked_in_image`）里 | `cd /testbed && bash run_tests.sh` → 预计 pytest 报 `file or directory not found: r2e_tests`（退出码 4），不能用来验证解题 |
| 装包 / 出网 | public_hints 提到 conda 和 pip | pip 有，无出网（L11） | 本题不需要新依赖 | 无 |
| git | 题面说仓库 checked out at commit `96fda39bb0dc` | brief 说静态工作树不含 `.git`；容器里的 `/testbed` 有没有 `.git` 没写 | `git diff` 能不能用未知；不影响修复 | 可选：`git -C /testbed status` → 预计要么列出改动，要么报"不是 git 仓库" |

## 5. 阅读范围与限制

**实际打开的文件**（路径相对 `PUBLIC_DIR`）

- 角色卡；`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`（全文）。
- `worktree_manifest.json`：用本机 `python3` 解析 JSON，只看了 `export`、`initial_diff`、`untracked_*`、`not_included` 字段，并按文件名模式筛了 `files`。没有打开它引用的、位于 `PUBLIC_DIR` 以外的路径（例如 `initial_diff.source`）。
- 读了全文：`owcreateclass.py`、`test_owcreateclass.py`、`worktree/run_tests.sh`、`worktree/requirements.txt`、`worktree/requirements-core.txt`、`worktree/requirements-dev.txt`、`worktree/requirements-gui.txt`、`worktree/setup.cfg`、`worktree/pyproject.toml`、`worktree/tox.ini`、`worktree/README-dev.md`、`worktree/doc/visual-programming/source/widgets/data/createclass.md`。
- 读了片段：`worktree/Orange/widgets/tests/base.py:1-80`；`worktree/Orange/preprocess/transformation.py` 中的 `Lookup`（L140-175）以及 `Transformation.__eq__` 和 `__hash__`；`worktree/CONTRIBUTING.md:96-120`；`worktree/CHANGELOG.md:1-25`，并检索了其中的 "Create Class"；`worktree/Orange/widgets/data/oweditdomain.py:52-63`。
- 检索：在 `worktree/` 里 grep 了 `unique_in_order_mapping`、`return_inverse=True`、`dict.fromkeys|factorize`、`map_values`；在 `worktree/Orange/datasets/` 里确认了 `heart_disease`、`zoo`、`iris` 三个数据集存在。

**没查的范围**

- 外部已安装包的源码和版本：`orangewidget`、`orange-canvas-core`、AnyQt / PyQt5、numpy、pandas、pytest。它们装在 `.venv` 里，不在工作树中。
- 镜像里的 `datasets/`、`install.sh`（没有收进快照）、编译产物、`.git`，以及隐藏测试 `r2e_tests`。
- 其它 widget 及其测试；git 历史和上游仓库。

**限制**

- `user_prompt.txt` 是用当前的 `render_user_prompt` 渲染出的静态文本，不是捕获到的模型实际消息。
- `worktree/` 不是完整的运行容器。文中关于 base 行为、公开用例结果和 widget 层影响的结论都来自静态推演，没有运行过；运行资源和开发条件都没有验证。
- 本上下文没有接触任何私有材料（gold 补丁、隐藏测试、期望结果、旧的审查结论）。
