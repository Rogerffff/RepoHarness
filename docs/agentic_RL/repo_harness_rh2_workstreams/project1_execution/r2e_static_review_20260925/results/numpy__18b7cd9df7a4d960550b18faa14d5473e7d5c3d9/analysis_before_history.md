<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9 私有主审分析（读历史前）

- 角色：R2E 私有主审（静态审查）；2026-09-25。本文件在打开任何历史调查之前保存。
- 暴露范围：已读本题 gold、隐藏测试、期望映射、摄入面原行，以及 `run_refs.json` 列出的全部原始日志和账本行。没有读 history 包、`r2e_env_repair_20260924/`、任何 `*review*` 目录、本批 README / `assignments.json`，也没有读 `runs/` 下的分析或汇总文件。
- 没有运行项目代码、容器或远端。本机只执行过两件事：用 python3.12 的 `ast` 解析隐藏测试文件（不执行）；构造一个与 numpy 无关的合成模块做 doctest 对照（附录 C）。
- 证据层级标记：【执行】当前材料下的 RH2 回放日志；【账本】账本解析字段；【源码】静态推断；【合成】本机合成对照。

## 0. 结论先行

- **题目**：`poly1d.__eq__` 与非 poly1d 对象（例如 `None`）比较时抛 `AttributeError`；要求不抛异常，结果表示"不相等"。base `6a3edf32`，NumPy 1.13.0.dev0，Python 3.7.9。
- **材料与初态**：材料一致，初态确实有这个 bug。两次当前 noop 都在 `r2e_tests/test_1.py:219` 的 `p == None` 处失败，报错与题面相同（`numpy/lib/polynomial.py:1202` 抛 `AttributeError`）；两次 gold 都是 11/11。只有一个目标键 `TestDocs.test_poly_eq`。期望映射的 11 个键全是 PASSED，所以不存在"更完整的修复把期望 FAILED 的键翻成 PASSED 而判 0"的风险。
- **不误拒**：测试只断言比较表达式的结果，`__eq__` 返回 `False` 或 `NotImplemented` 都能通过。只改 `__eq__` 返回 `NotImplemented`、不改 `__ne__` 的实现会被拒，因为那时 `p != None` 得到 `False`。这个拒绝有公开依据（题面要求比较结果"表示不相等"），也是本题主要的区分点。
- **两处不阻塞的覆盖缺口**（【源码】，未执行）：
  - (i) 只测 `None`：只特判 `if other is None: return False` 也能得 1，但 `p == 3` 仍然抛异常；
  - (ii) poly1d 之间只比较了 `p == p`（同一个对象）和系数不同的 `p2`：删掉 `__eq__` / `__ne__`，退化为按对象身份比较，也能得 1，但 `poly1d([1,2,3]) == poly1d([1,2,3])` 会变成 `False`。
  - 另外，`test_doctests` 是死键：文件开头那段字符串不是模块 docstring，所以它实际上一个例子也不跑。
- **暂定处置**：`static_review` / `needs_review`，理由是"静态候选待 actor 验证"。可以作 development_diagnostic 和基座探针候选（易题，主要区分点在 `__ne__`）。探针后要检查通过的补丁是否属于 (i) 或 (ii) 类。如果打算用于训练，先用 CPU 验证这两个蒙混候选，再决定是否修订测试。
- **唯一最值得先做的下一步**：在派生镜像上用 RH2 评分回放四个候选：A（`isinstance` 不成立时返回 `False`）、D（只改 `__eq__`）、N（只特判 `None`）、I（删除 `__eq__` / `__ne__`），核对得分是否为预期的 1 / 0 / 1 / 1。

## 1. 公开读者产物与它没有捕获的条件（步骤 1）

公开读者（`public_read.md`）独立列出了 R1–R12，并指出三个疑点：`__ne__` 陷阱（其 §2 D）、强制转换实现（§2 E），以及题面允许两种返回值带来的歧义。对照私有材料，结果如下：

| 公开读者的未知 | 私有证据给出的事实 |
|---|---|
| 隐藏测试是否检查 `!=` | 检查：`test_1.py:220` `assert_equal(p != None, True)`，所以 D 类会被拒 |
| 是否直接断言 `p.__eq__(None)` 的值 | 不断言，只看表达式结果，所以 A、B 两类都接受 |
| E（强制转换）能否通过 | 能【源码】：`poly1d(None)` 经 `atleast_1d` / `trim_zeros`（`function_base.py:2239-2243`）得到 `array([None], dtype=object)`，形状 (1,) 与 (3,) 不同，结果为 `False`；隐藏测试不测 list 和二维输入 |
| venv 里有没有 nose | 有（间接证据）：`test_polyfit` 第一条执行的断言是 `assert_raises`（`test_1.py:141`），它要调 `import_nose()`（`numpy/testing/utils.py:1187`）；四次当前运行这个键都是 PASSED |
| pytest 版本与导入来源 | pytest 7.4.4，带 hypothesis 6.79.4 与 env 插件；日志里没有 configfile 行，工作树也没有 conftest / pytest.ini。numpy 从 `/testbed/numpy/__init__.py` 导入，版本 `1.13.0.dev0+6a3edf3`（账本 `observations`） |
| 解题时 `r2e_tests/` 是否存在 | 派生镜像：隐藏测试放在 root 私有目录（环境卡 §1）。来源镜像：`/r2e_tests` 下有 2 个文件，`/testbed` 下没有（M3 账本 `facts.r2e_tests_root=2`、`r2e_tests_in_testbed=0`） |
| 实际渲染的消息、hints 是否进入模型消息 | 仍未知（属于计划输入） |
| `install.sh` 的内容 | 仍未知：公开包和私有包都没有收入；评分时 `RH2_INSTALL_SKIPPED=1` |

公开读者没有发现两件事：`test_doctests` 是死键；poly1d 之间按值相等的行为没有被评分覆盖（见 §3）。

## 2. 隐藏测试展开（步骤 2）

隐藏测试就是 base 的 `numpy/lib/tests/test_polynomial.py` 原文，加上新增的 `test_poly_eq`（`test_1.py:216-223`）。`diff` 显示两者只差这 8 行和 1 个空行；另有一个空的 `__init__.py`。全部测试在 1 个文件的 1 个类 `TestDocs` 里，11 个键不会撞名。

### 2.1 目标键 `TestDocs.test_poly_eq`（noop FAILED，gold PASSED）

```python
p = np.poly1d([1, 2, 3]); p2 = np.poly1d([1, 2, 4])
assert_equal(p == None, False)   # L219 题面原例
assert_equal(p != None, True)    # L220 同一根因的 `!=`
assert_equal(p == p, True)       # L221 同一个对象
assert_equal(p == p2, False)     # L222 形状相同、系数不同
assert_equal(p != p2, True)      # L223
```

`assert_equal` 来自 base 的 `numpy/testing/utils.py:289-405`。参数不是 dict、list 或 ndarray 时，它依次检查两边 `isscalar` 是否一致（L375）、是否有限、`desired == 0 and actual == 0` 时的 signbit（L391），最后执行 `if not (desired == actual)`（L404）。Python `bool` 和 `numpy.bool_` 都按值比较，所以返回类型不受约束。

gold 下 L219 的执行过程：`p.__eq__(None)` 返回 `NotImplemented`，Python 再试 `None.__eq__(p)`，也返回 `NotImplemented`，于是回退到身份比较，得到 `False`。L220 同理得到 `True`。

noop 的实际失败【执行】：两份当前 noop 日志第 31–42 行都是 `r2e_tests/test_1.py:219` → `numpy/lib/polynomial.py:1202` → `AttributeError: 'NoneType' object has no attribute 'coeffs'`，与题面逐字一致。noop 下 L220–223 没有执行。两份 gold 日志中这个键是 PASSED，说明 5 条断言都执行并通过了。

### 2.2 回归键（10 个，noop 和 gold 下都是 PASSED）

| 键 | 实际检查的内容 | 与本题修改的关系 |
|---|---|---|
| `test_poly` | `np.poly` 的数值；`np.random.seed(42)` 固定了随机数 | 无关，不经过 poly1d 比较 |
| `test_roots` | `np.roots` | 无关 |
| `test_str_leading_zeros` | `poly1d.__setitem__` 与 `__str__`，断言比较的是字符串 | 间接：poly1d 的其它接口 |
| `test_polyfit` | `np.polyfit`；含 `assert_raises`，需要 nose | 无关 |
| `test_objects` | Decimal 系数下的 `*`、`deriv`、`integ`、`__getitem__`；比较的是系数，不是 poly1d | 间接 |
| `test_complex`、`test_integ_coeffs` | `integ` / `deriv` 之后对 `.coeffs` 做 ndarray 比较 | 间接 |
| `test_zero_dims` | `try: np.poly(zeros((0,0))) except ValueError: pass`，几乎总能通过 | 无关 |
| `test_poly_int_overflow` | `np.poly(arange(1,21))` 与 `np.poly(diag(v))` 按默认 7 位小数近似比较 | 无关；数值型断言（见 §4 e） |
| `test_doctests` | **死键**。`rundocs()` 只在模块 `__doc__` 里找例子，而文件第 1 行是 `from __future__ ...`，第 3–80 行那段 `>>>` 字符串因此不是 docstring（`ast.get_docstring` 返回 `None`）；类和方法也没有带例子的 docstring。实际运行 0 个例子【源码＋合成】 | 永远 PASSED。因此 poly1d 的 repr、算术、`__call__`、`__array__` 都没有评分保护 |

阅读范围：隐藏测试全文逐行读过；回归键只追到被调用的 API，没有追进 `np.poly`、`polyfit` 和 LAPACK 内部。

## 3. 双向映射（步骤 3）

### 3.1 公开要求 → 断言

| # | 公开要求 / 合理旧行为 | 依据 | 对应断言 | 判断 |
|---|---|---|---|---|
| R1 | `p == None` 不抛异常，结果为 `False` | 题面原例 `user_prompt.txt:11-18` | L219 | 覆盖 |
| R2 | 与任意非 poly1d 对象比较都不抛异常，并表示不相等 | 题面泛称 "a non-`poly1d` object" | 无，只测了 `None` | 部分；反例 N（§3.3） |
| R3 | `__eq__` 返回 `False` 或 `NotImplemented` 都可以 | 题面第 18 行 | 只看表达式结果 | 覆盖，且不误拒 |
| R4 | `p != None` 不抛异常，结果为 `True` | 题面"表示不相等"，加上 `__ne__` 调用 `__eq__`（`polynomial.py:1206-1207`）；公开读者独立推出了这条 | L220 | 覆盖；会拒绝 D |
| R5 | `None == p` 结果为 `False` | Python 反射比较协议 | 无 | 缺失；A、B、N 都自然满足，风险低 |
| R6 | `assert_equal` 比较单系数 poly1d 时不崩 | 公开读者的推断（`utils.py:391`、`:396`） | 无 | 缺失，不重要 |
| R7 | poly1d 之间按系数值比较，`!=` 是取反 | base `polynomial.py:1201-1207`；公开 `test_regression.py:18-21, 74-79` 用 `assert_equal` 比较两个不同但等值的 poly1d 对象，`:81-86` | L221-223 | **部分**：L221 比较的是同一个对象，L222 的系数不同，按身份比较也全部通过；反例 I |
| R8 | 其它接口不变（算术、repr、`__hash__ = None` 等） | base 源码 | 10 个回归键，其中 doctests 是死键 | 部分：str、getitem、setitem、integ、deriv、乘标量有覆盖；repr、`+ - /`、`__call__` 没有 |
| R9–R11 | 与 ndarray、鸭子类型对象、系数相同的 list 比较 | 题面没有约定 | 无 | 既未约定也未测，不会误拒 |

### 3.2 断言 → 公开依据

- L219 ← 题面原例。
- L220 ← 由题面"表示不相等"推知，不是字面要求。
- L221–223 ← 旧行为；公开的 `test_regression.py::test_poly_eq` 同样检查 `x != y` 和 `x == x`。
- 10 个回归键 ← base 同文件的原有测试，noop 下已经通过。
- 没有任何断言要求内部 helper 名、报错文案或返回类型。

### 3.3 替代解与蒙混候选（全部是【源码】推断，未执行）

| 候选 | 改法 | 隐藏测试结果 | 题面要求的行为 |
|---|---|---|---|
| A（合理替代） | `if not isinstance(other, poly1d): return False`，`__ne__` 不改 | 5 条全过，预期得 1 | 正确；与 `numpy/polynomial/_polybase.py:437-446` 的写法一致 |
| C（合理替代） | 用 `getattr(other, 'coeffs', None)` 或 `try/except AttributeError` 识别后返回 `False` | 全过，预期得 1 | 正确；只在鸭子类型对象上与 A 不同，题面没有约定 |
| F（合理替代） | `__eq__` 按 A 或 gold 改，删掉 `__ne__`，依赖 Python 3 自动派生 | 全过，预期得 1 | Python 3 下正确；但本提交仍声明支持 Python 2（公开读者 §2 F），评分看不到这个差别 |
| D（陷阱） | 只让 `__eq__` 对非 poly1d 返回 `NotImplemented`，`__ne__` 仍是 `not self.__eq__(other)` | L220 失败：3.7.9 下 `not NotImplemented` 为 `False`，3.9 起才发警告；抛 AssertionError，得 0 | 错误：`p != None` 等于声称两者相等。拒绝有依据 |
| E（强制转换） | 先 `other = poly1d(other)` 再比较 | 全过，预期得 1 | 部分违背 R2、R11：`p == [1,2,3]` 为 `True`，二维输入抛 `ValueError` |
| **N（蒙混）** | `if other is None: return False` | 全过，预期得 1 | **违背 R2**：`p == 3`、`p == 'a'`、`p == [1,2,3]` 仍抛 `AttributeError` |
| **I（蒙混）** | 删除 `__eq__` 和 `__ne__`（或写成 `return self is other`） | 按身份比较时 L219–223 依次得到 False、True、True、False、True，全部符合断言；其余键不涉及 poly1d 的值比较；预期得 1 | **违背 R7**：`poly1d([1,2,3]) == poly1d([1,2,3])` 变为 `False`。公开的 `test_regression.py::test_poly1d` 和 `test_poly_div` 会失败，但它们不计分 |

结论：

- 没有发现误拒合理解的断言（检查 24）。
- 有两个具体的蒙混反例 N 和 I（检查 25、32）。N 更可能真的出现：较弱的模型只处理题面原例时，自然会写出这种特判。I 在正常求解中不自然，风险主要在 RL 奖励漏洞层面。

## 4. R2E 专项（步骤 4）

- **(a) 非 PASSED 键**：期望里没有非 PASSED 键。更完整的修复（同时处理 `!=`、统一返回 `False`、专门处理 ndarray 等）不会改变 11 个键的状态【源码】。收集结果也不受修复影响：共 11 项，账本 `num_parsed_tests=11`、`keys_equal=true`。
- **(b) 报错是否出现在目标键的失败原因里**：出现了。两次当前 noop 的失败位置和文案一致，见 §2.1。
- **(c) 题面是否泄漏修法**：给出了修法方向，但没有给代码。标题点名 `poly1d.__eq__`，"Actual Behavior" 说明了根因，"Expected Behavior" 给出两种返回值。唯一没提示的是 `__ne__`。属于易题，泄漏程度为"方向明示"。
- **(d) 辅助代码、搬迁伪影与撞键**：
  - 隐藏测试从 `numpy/testing` 导入 `assert_equal`、`rundocs` 和 `assert_raises`（后者依赖 nose）。这些文件候选可以改，评分也不重置；但合法解不需要改它们。这属于 R2E 的共享机制（环境卡 §3），本题没有特例。
  - 搬迁：原目录没有 conftest，也没有相对路径资源。`rundocs()` 用的是调用者的 `__file__`，搬到 `r2e_tests/` 后仍指向本文件（而且本来就是 0 个例子）。`r2e_tests/__init__.py` 让 rootdir `/testbed` 进入 `sys.path`；日志回溯中的 `numpy/lib/polynomial.py:1202` 证明测试用的是工作树里的源码。
  - 只有一个测试文件，不存在跨文件撞键。
- **(e) 时间、随机与资源**：
  - `test_poly` 用了固定种子。
  - `test_poly_int_overflow` 和 `test_polyfit` 是浮点数值断言。6 次运行全部通过（当前材料 4 次在派生镜像上，M3 2 次在来源镜像上，至少涉及两台主机），没有看到波动。
  - 测试本身不到 1 秒，内存峰值约 296–305 MB（账本 `resource.mem_peak_mb`），默认的 2 CPU / 4 GiB 足够。
- **(f) 材料修订**：没有（`revisions.json` 为 `[]`），不适用。

## 5. gold 检查与运行证据（步骤 5）

**gold 改了什么**：只改 `numpy/lib/polynomial.py`，在 `__eq__` 和 `__ne__` 开头各加一行 `if not isinstance(other, poly1d): return NotImplemented`（共 4 行）。

- 修到了原例（R1），也处理了 `!=`（R4）；`None == p`（R5）经反射比较同样正确；poly1d 之间的比较逻辑不变（R7）。
- 没有无关改动。来源提交另外只改了已被剔除的 `numpy/lib/tests/test_polynomial.py`（M3 账本 `gold_meta.excluded`）。

**未被测试覆盖、但不算回归的行为变化**：

- 与 ndarray 比较：原来抛异常，现在交给 ndarray 做反射比较；公开读者推断结果是逐元素数组。
- 带 `coeffs` 属性的鸭子类型对象不再按系数比较。
- 仓库里没有非测试代码依赖 poly1d 的 `==`。依据是在 `polynomial.py` 里 grep `==` / `!=`，以及 grep `numpy/` 下非测试文件对 `poly1d` 的用法。

**运行证据**【执行】【账本】：都是当前材料，派生镜像 `rh2-r2e-derived/numpy:18b7cd9df7a4-r2e_derive_v1`（ID `sha256:61363b45…`），没有 env / resource 配方。

| 运行 | 结果 | 要点 |
|---|---|---|
| R-f noop（账本 L16） | 0，10/11 | 只有 `test_poly_eq` 失败；`test_rc=1`；没有 missing 或 unexpected |
| R-f gold（L16） | 1，11/11 | `apply_ok`；投影 `included_paths=["numpy/lib/polynomial.py"]` |
| 环境轮复跑 noop（L16） | 0，10/11 | 失败位置和文案与 R-f noop 相同 |
| 环境轮复跑 gold（L16） | 1，11/11 | 同上 |
| M3 来源镜像 gold a1 / a2（参考） | 1，11/11 | 独立 runner；`network=none` |

**一致性核对**：

- 日志里的隐藏测试树 `219751051c84…` 和入口 `8285765f…` 都与 grading bundle 一致。
- gold 补丁的 sha `07bbe5f4…` 与账本一致。
- 6 份本地日志的 sha 与 `run_refs.json` 一致。
- 在本地重算隐藏测试、期望映射和 gold 的 sha，结果也一致。

**缺项**：

- `run_refs` 没有 M3 的 noop 参考。
- 当前材料的两轮运行可能在同一台主机上，用的是同一个派生镜像 ID。
- 并发和环境复用没有查。
- 没有读账本引用的 `diagnostics.json`（`run_refs` 没有列出它）。

## 6. 开发需求（步骤 6）

| 项 | 需求 | 证据层级 |
|---|---|---|
| 导入 | 在 `/testbed` 下用 `python -c ...`（当前目录会进入 `sys.path`），或设 `PYTHONPATH=/testbed`；numpy 必须从 `/testbed/numpy` 导入 | 评分侧实测（账本 `RH2_OBS_IMPORT_PATH`）；解题侧为镜像层面实测（环境卡 §2，`environment_brief.md:13`） |
| 解释器与测试工具 | `/testbed/.venv/bin/python`（3.7.9）；用 `python -m pytest`，直接运行 `pytest` 收集会失败；pytest 7.4.4，nose 可用 | 评分日志加推知；解题侧为镜像层面实测 |
| 依赖与网络 | 不需要新依赖；没有 pip / uv，也没有出网；各阶段都不需要网络 | 镜像层面实测；评分侧 `network=deny_all` |
| 资产 | 不需要 | 源码 |
| 构建 | 纯 Python 改动，改完立即生效；不要运行 `runtests.py`（它会先构建项目），也不要运行内容未知的 `install.sh` | 源码推断 |
| 权限与提交边界 | agent（uid 54321）可写 `/testbed`；只需改 `numpy/lib/polynomial.py`，它会被投影收入 | 镜像层面实测；评分侧实测（gold 账本）；正式链 actor 待验 |
| 建议验证命令（未执行） | `python -c "from numpy import poly1d as P; p=P([1,2,3]); print(p==None, p!=None, None==p, p==3, p==P([1,2,3]), p!=P([3,4]))"`，修好后应输出 `False True False False True True`；另跑 `python -m pytest -rA numpy/lib/tests/test_polynomial.py` 与 `python -m pytest -rA numpy/lib/tests/test_regression.py -k poly` | actor 待验 |
| 资源 | 默认 2 CPU / 4 GiB / `/tmp` 1 GiB | 评分侧实测表明足够 |
| 正式 actor 的前置条件（环境级，不是本题特有） | 必须改用派生镜像：来源镜像的 `/r2e_tests` 所有用户可读，修复提交在 git 中可达（M3 `facts.fix_reachable=commit`、`commits_after_head=28671`、`r2e_tests_root=2`）；解释器前缀默认是 conda，会拒绝 `.venv`；`public_hints` 里 conda / pip 和"测试文件会被重置"的说法与 R2E 实际不符 | 代码事实（环境卡 §2）；B 线待实现、A 线审查 |

## 7. 八方面覆盖（已查 / 未查）

| 方面 | 已查 | 未查 / 未知 |
|---|---|---|
| 公开需求（3、23） | 题面、hints、`environment_brief.md`、公开读者报告；`!=` 的要求可以推知 | 实际渲染的消息没有捕获（计划输入）；hints 的 conda / pip 说法是已知的环境级问题 |
| 材料与初始问题（1、2、27） | 各 sha 对齐；`initial_diff` 为 0 字节；noop 的失败就是题面描述的报错 | — |
| 测试是否测到要求（18–20、25、32） | 目标键的 5 条断言逐条追到 `assert_equal`；11 个键都完整执行 | 反例 N、I 没有执行 |
| 是否误拒（24、28） | A、C、F 静态推断可过；拒绝 D 有依据 | 替代解没有执行 |
| 回归与 gold（26、27） | gold 逐行读过；查了 `numpy/` 内 poly1d 的调用者；回归键逐个读过 | 没追 `np.poly`、`polyfit` 内部；doctests 是死键，repr 和算术没有评分保护 |
| 开发条件（6–15） | 引用环境卡与 `environment_brief.md`；评分侧的依赖、资源和网络 | actor 正式链；并发与复用（15） |
| 交付与评分边界（4、16–17、21–22、29–31） | 投影、测试恢复、解析、M3 对照；来源镜像泄漏（环境级） | 候选改写 `numpy/testing` 或新建 rootdir conftest 的风险只引用共享机制，没有单独审 |
| 题目关系与用途（5、29–30、37–40） | 本池 48 题中只有本题的 gold 触及 `polynomial.py` / `poly1d`；修法方向明示；没有修订 | 跨来源重复、预训练污染；真实求解（33–36） |

## 8. 缺口与建议队列（交协调者安排）

1. **CPU 定点回放（优先）**：在派生镜像上用 RH2 评分回放候选 A、D、N、I，预期得分依次为 1、0、1、1。每个候选同时跑一遍 §6 的 `python -c` 探针，把"题面要求的行为"和"得分"分开记录。
2. **测试修订**（只在打算用于训练时考虑，由协调者或用户决定）：
   - 在 `test_poly_eq` 里加 `assert_equal(p == np.poly1d([1, 2, 3]), True)`，依据是旧行为，用来堵住 I；
   - 加 `assert_equal(p == 3, False)` 和 `assert_equal(p != 3, True)`，依据是题面的泛称，用来堵住 N；
   - 这几条在 gold、A、C、F 下都应成立。不要加与 ndarray 的比较：R9 没有约定，gold 下会得到逐元素数组；
   - 修订后要用 gold、A、C、D、N、I 双向复验，并登记为修订版。
3. **探针后复核**：逐个检查通过的补丁，看是否属于 N（只特判 `None`）或 I（丢掉了按值相等）。
4. **环境级（不是本题特有）**：正式 actor 改用派生镜像，改 `.venv` 的解释器前缀核对，改 hints 措辞。

## 9. 暂定处置

- `disposition.scope=static_review`，state 为 `needs_review`。reason：静态候选待 actor 验证；题意、目标测试与 gold 一致；另有两处不阻塞的覆盖缺口（静态推断）和一个死键。
- `usage.intended_use=development_diagnostic`；可以列为基座探针候选（易题，主要区分点在 `__ne__`）。审查者已经看过 gold、隐藏测试和运行日志。
- 拟定的 `checks`（稀疏记录）：
  - pass：1、2、4、5（只查了本池）、6、7、8（评分侧实测，解题侧为镜像层面实测）、9、11、13、14（noop 与 gold 各 2 次）、16–23、24、26、27、30（镜像层面）；
  - unknown：3（hints 是已知的环境级问题，实际消息未捕获）、10（actor 待验）、31（共享机制）；
  - issue：25（反例 N、I）、29（环境级：来源镜像泄漏）、32（同 25 的 I）；
  - not_checked：15、33–36；
  - not_applicable：12、37–39。

## 附录 A：实际阅读范围

- 方法文件：角色卡、八方面协议、R2E 环境卡、记录模板、40 项清单。
- 公开侧：
  - `public_read.md` 全文；
  - `user_prompt.txt`、`environment_brief.md`、`public_bundle.json` 全文；
  - `worktree_manifest.json` 中除 `files` 以外的键；
  - 工作树：`numpy/lib/polynomial.py` 第 1–30 行和第 930–1277 行，并 grep 了 `==` / `!=`；`numpy/lib/tests/test_regression.py` 第 1–100 行，并 grep 了 `poly1d`；`numpy/lib/tests/test_polynomial.py` 第 1–12 行，并与隐藏测试做了全文 diff；`numpy/testing/utils.py` 第 40–130、280–406、1105–1195 行；`numpy/lib/function_base.py` 中 `trim_zeros` 的片段；`numpy/core/shape_base.py` 中 `atleast_1d` 的片段；
  - 还做了这些检查：查 conftest 和 pytest 配置；grep `numpy/` 下非测试代码对 `poly1d` 的用法；grep 修复特征串，确认工作树里没有泄漏。
- 私有侧：`PRIVATE_DIR` 下的全部文件。
- 运行原件：
  - 4 份当前 eval 日志全文，以及对应 4 个账本各自的第 16 行（完整）；
  - M3 的 2 份日志全文，以及 `r2e_gold_m3.jsonl` 第 1 行和第 49 行。
- 其它题：只 grep 了 `runs/r2e_static_prep_20260924/v2/private/*/gold.patch` 是否含 `numpy/lib/polynomial.py` 或 `poly1d`，只看命中了哪些题，用于检查 5。
- 没读：C 源码；`np.poly`、`polyfit` 的内部实现；`diagnostics.json`；`install.sh`（没有收入材料）；任何历史材料。

## 附录 B：证据索引

- 隐藏测试 `PRIVATE_DIR/hidden_tests/test_1.py`：第 1 行 `from __future__`；第 3–80 行模块字符串；第 89–90 行 `test_doctests`；第 112 行 `seed(42)`；第 141 行 `assert_raises`；第 216–223 行 `test_poly_eq`。sha `4a86bd4b…`，与 grading bundle 一致。
- 期望映射 `expected_output.json`：sha `bbf6d58d…`；11 个键全是 PASSED。
- gold `gold.patch`：sha `07bbe5f4…`；共 4 行新增。
- base 源码 `worktree/numpy/lib/polynomial.py`：`__eq__` 在第 1201–1204 行，`__ne__` 在第 1206–1207 行，`__hash__ = None` 在第 1042 行。
- `worktree/numpy/testing/utils.py`：`assert_equal` 在第 289–405 行（第 375、391、396、404 行是关键分支）；`rundocs` 的第 1135 行用 `sys._getframe(1)` 取调用者文件；`assert_raises` 在第 1187 行调 `import_nose()`。
- noop 日志：
  - `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-n_3cdaf461.eval.log`，第 31–42 行和第 55 行；
  - `runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_f466e78b.eval.log`，同样位置。
- gold 日志：
  - `…/evallog_replay-r2e-rf-all-gold-n_d91e0720.eval.log`，第 31 行；
  - `…/evallog_replay-r2e-envrepair-rer_f34c3153.eval.log`，第 31 行。
- 账本：`runs/r2e_rf_20260923/remote/ledger_r2e_all_{noop,gold}.jsonl` 第 16 行；`runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl` 第 16 行。用到的字段：`verdict_diagnostics.expected_match`、`observations.RH2_OBS_IMPORT_PATH`、`projection.included_paths`、`resource.mem_peak_mb`、`policy`。
- M3 参考：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` 第 1 行和第 49 行（`facts`、`gold_meta`）；对应日志 `…/logs_r2e/numpy/18b7cd9df7a4/gold/a{1,2}/test_output.txt`。

## 附录 C：死键的合成对照

- 对隐藏测试做 `ast.parse` 后，`ast.get_docstring(tree)` 返回 `None`；模块的第一条语句是 `ImportFrom`，第二条是 `Expr`。
- 构造了一个同样结构的合成模块：先写 `from __future__ import division`，再写一段含故意写错的例子（`>>> 1 + 1` 期望 `3`）的字符串，另有一个类方法，其 docstring 不含例子。结果：`__doc__` 为 `None`；`DocTestFinder` 只找到那个方法，且 0 个例子；failures 为 0。
- 这说明模块字符串里的例子不会运行。对照用的是本机 Python 3.12，但模块 docstring 的判定规则在各版本间一致；隐藏测试在 3.7.9 下的实际例子数没有在容器里核对。
