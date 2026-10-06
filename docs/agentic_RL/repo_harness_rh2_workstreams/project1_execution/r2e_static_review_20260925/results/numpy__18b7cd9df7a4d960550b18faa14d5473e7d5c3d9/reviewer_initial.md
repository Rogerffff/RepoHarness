# numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9 · 独立复核初判（第一步）

R2E 独立复核者（静态审查），2026-09-25。本稿写于阅读任何主审产物、公开读者产物与历史材料之前。未运行项目代码或容器；本地只做了 `shasum` / `diff` / `grep` 核对，以及用 Python `ast` 解析隐藏测试文件结构（只解析，不导入、不执行）。

路径缩写（均相对仓库根）：

- `PUB` = `runs/r2e_static_prep_20260924/v2/public/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9`
- `PRIV` = `runs/r2e_static_prep_20260924/v2/private/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9`
- `DEV` = `runs/r2e_actor_20260925/devcheck/numpy__18b7cd9df7a4d960550b18faa14d5473e`

## 0. 初判摘要

- **材料一致，评分依据可解释。** 唯一目标键是 `TestDocs.test_poly_eq`。noop 在它的第一条断言处抛出题面所述的 `AttributeError: 'NoneType' object has no attribute 'coeffs'`（`numpy/lib/polynomial.py:1202`）；gold 11/11。其余 10 键在 noop 与 gold 下都是 PASSED。期望里没有非 PASSED 键；本题无材料修订，也没有 env / 资源配方。
- **未发现误拒。** 题面允许的两种返回值（`False` / `NotImplemented`），以及强制转换、`hasattr` 鸭子类型等路线，按静态推演都能得 1。测试只检查运算符结果，不直接断言 `__eq__` 的返回值。
- **隐含要求（不是误拒，但要知道）：** 隐藏测试还断言 `p != None` 为 `True`（`test_1.py:220`）。题面只举了 `==`，而 base 的 `__ne__` 是 `return not self.__eq__(other)`。**只在 `__eq__` 返回 `NotImplemented`、不改 `__ne__`** 的解答会让 `p != None` 静默得到 `False`：Python 3.7 把 `NotImplemented` 当真值，而且不给任何警告。这样的解答被判 0 是对的（它确实把结果算错了），但对照题面字面这是一个陷阱。证据级别：静态推断。
- **漏测（低）：** 非 `poly1d` 对象只测了 `None`。只特判 `other is None` 的部分修复会得 1，但 `p == 3`、`p == [1, 2, 3]` 仍抛 `AttributeError`，违反题面 "non-`poly1d` objects" 这条一般要求。证据级别：静态推断。
- **死键（信息）：** `TestDocs.test_doctests` 实际上一个 doctest 都不执行。`test_1.py` 的第 1 条语句是 `from __future__ import ...`，所以第 3–80 行的三引号字符串不是模块 docstring（`ast.get_docstring` 返回 `None`），`rundocs()` 找到 0 个例子。10 个回归键里真正起作用的是 9 个。
- **未测回归（低）：** 不同长度 `poly1d` 之间的比较（`__eq__` 的 shape 分支）不在隐藏测试里。仓库公开的 `TestRegression.test_poly_eq`（`test_regression.py:81-86`）覆盖这种情况，但它不参与评分。
- **题面给出了修法方向：** 返回 `False` 或 `NotImplemented`，并点明根因是访问非 poly1d 对象的 `.coeffs`。所以题目难度低。
- **暂定处置：** 作为静态候选（开发诊断 / 低难度探针），暂不建议修订。实际发给 actor 的任务提示措辞待 actor 验证。唯一优先的下一步：做一次评分回放，放入 3 个构造候选（§11）。

## 1. 实际读取范围

**已读**

- 角色卡与方法：`roles/reviewer_r2e.md` 全文。`roles/investigator_r2e.md`：Read 工具一次返回了全文（34 行），但我只把"R2E 的评分口径"和"材料"两节当作依据。`quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`record_template.md` 全文。
- 公开包：
  - `PUB/user_prompt.txt`、`environment_brief.md`、`public_bundle.json` 全文。
  - `worktree_manifest.json` 的头部（export / initial_diff / untracked_*），以及 3 个文件的哈希条目。
  - `worktree/` 中：
    - `numpy/lib/polynomial.py:935-1274`（整个 poly1d 类）
    - `numpy/lib/tests/test_polynomial.py`（与隐藏测试做 diff）
    - `numpy/lib/tests/test_regression.py:14-95, 185-200`
    - `numpy/testing/utils.py:289-412, 1110-1160`
    - `numpy/lib/function_base.py` 中的 `trim_zeros`
    - `numpy/core/shape_base.py:49-58`（`atleast_1d`）
    - `numpy/testing/__init__.py:10`
  - 对 worktree 做了全仓 `poly1d` grep，看了顶层文件列表，确认没有 conftest。
- 私有包：`PRIV` 下全部文件，包括 `hidden_tests/test_1.py` 全文、`__init__.py`（空）、`expected_output.json`、`gold.patch`、`grading_bundle.json`、`validation_bundle.json`、`revisions.json`、`run_refs.json`、`run_tests.sh`。
- 运行原件（`run_refs.json` 的全部 6 行）：
  - 4 个 current 账本行（各账本第 16 行，逐字段展开）和对应的 4 份 `.eval.log` 全文。
  - M3 独立参考 `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` 第 1、49 行，以及两份 `test_output.txt`。
  - 6 份日志的 sha256 都与 `run_refs.json` 一致。
- devcheck：
  - `DEV/orig/` 下：`attempt.json`（展开）、`prelaunch.json`、`activation_check.json`、`devcheck_stdout.json`、`commands_with_preflight.json`、`captures/*.out`（6 份）、`post_run_facts_root.txt`、`devcheck_stderr.log`、`bringup_artifacts/cc_version_observed.json`。
  - `stub/requests/messages_000.json`：只看了 system 与首条 user 消息，并做了关键词检索。
  - `DEV/private_gold/private_control.json`、`stdout.log`。

**未读**

- `OUTPUT_DIR` 下的其它文件（含 `public_read.md`）。
- 任何 `history/`。
- `r2e_env_repair_20260924/` 以及各审查目录。
- `r2e_static_review_20260925/` 下的 README、assignments.json、actor_devcheck.md、grader_candidates.md。
- 环境卡链接的 `r2e_actor_wiring_20260925.md`。
- `runs/` 下的分析或汇总文件。
- 账本 `diagnostics_ref` 指向的 diagnostics.json。
- `DEV/orig/` 下的 `stub_script.json`、`stub/stub_log.json`、`harness/trajectory.jsonl`、`messages_001–006.json`。另有 `stub_stdout.log`、`harness/stderr.log` 为 0 字节。
- 我 `ls` 过 devcheck 的上级目录，看到了其它题的目录名，但没有打开。

## 2. 公开目标（只依据公开包）

- **题面**（`PUB/user_prompt.txt:3-22`）：`poly1d` 与非 `poly1d` 对象（例如 `None`）比较时不应抛异常，而应"return `False` or `NotImplemented`, indicating that the objects are not equal"。原例是 `p == None`；题面把根因解释为访问非 poly1d 对象的 `coeffs`。
- **代码里看得到的事实：**
  - `polynomial.py:1201-1204` 的 `__eq__` 直接读取 `other.coeffs`。
  - `:1206-1207` 的 `__ne__` 是 `return not self.__eq__(other)`。
  - `:1042` 是 `__hash__ = None`。
  - 算术方法用 `poly1d(other)` 做强制转换（`:1159-1181`），这为"强制转换"这条修法提供了公开依据。
- **可以推出、但题面没写明的：** `!=` 也必须给出"不相等"（即 `True`）；反射比较 `None == p` 走的是同一个 `__eq__`。
- **题面没有规定的：** 与数组、列表、标量比较时，是按系数比较还是一律判不等。gold 返回 `NotImplemented`，于是 `p == [1, 2, 3]` 得 `False`；强制转换路线会得 `True`。测试也没有规定这一点，属于合理的开放空间。
- **公共提示：** `public_bundle.json` 的 `public_hints` 写的是 conda、pip、"测试文件会被重置"，与 R2E 镜像不符（环境卡 §3 已说明）。实际发给 actor 的 R2E 提示本包没有捕获（见 §6、§7）。

## 3. 隐藏测试展开

`PRIV/hidden_tests/test_1.py` 等于仓库的 `numpy/lib/tests/test_polynomial.py` 加上新增的 `test_poly_eq`：`diff` 只差 `:216-223` 和末尾一个空行。文件里只有一个类 `TestDocs(TestCase)`，`TestCase` 来自 `unittest`（`numpy/testing/__init__.py:10`），共 11 个键。

**目标键 `TestDocs.test_poly_eq`**（`:216-223`）。5 条断言都用 `numpy.testing.assert_equal`（`utils.py:289-405`）；标量最终走 `desired == actual`（`:404`），所以 `False`、`True`、`np.bool_` 都能正确比较。

| 行 | 断言 | 测什么 | base 下的表现 |
| --- | --- | --- | --- |
| 219 | `p == None` 为 `False` | 题面原例 | 抛 AttributeError（noop 日志就停在这里） |
| 220 | `p != None` 为 `True` | `!=` 的语义（隐含要求） | 同样抛：`__ne__` 调 `__eq__`（`DEV/orig/captures/mcve_other_entries.out:3-7`） |
| 221 | `p == p` 为 `True` | 旧行为 | 正常（静态判断） |
| 222 | `p == p2` 为 `False`（p2 同长度，`[1, 2, 4]`） | 旧行为 | 正常（静态判断） |
| 223 | `p != p2` 为 `True` | 旧行为 | 正常（静态判断） |

**回归键**（noop 与 gold 下都是 PASSED）：

| 键 | 实际检查的内容 | 与本修复的关系 |
| --- | --- | --- |
| `test_doctests`（`:89-90`） | **死键。** `rundocs()`（`utils.py:1138-1152`）把文件重新加载成模块，再调用 `DocTestFinder().find`。模块没有 docstring：第 1 条语句是 `ImportFrom`，第 3 行的字符串只是一个表达式，`ast.get_docstring` 返回 `None`。唯一的方法 docstring（`test_poly_int_overflow` 的）里没有 `>>>`。所以找到 0 个例子，这个键恒过，第 3–80 行的 poly1d 打印与算术样例从来没被执行。上游原文件也是这么写的，不是搬迁造成的伪影。 | 无 |
| `test_poly`、`test_roots`、`test_polyfit`、`test_poly_int_overflow` | 检查 `np.poly`、`roots`、`polyfit` 的数值结果。`test_poly` 固定了 `np.random.seed(42)`。`test_polyfit` 里的 `assert_raises` 依赖 nose（`utils.py:1161`、`:1187`），镜像里有 nose 1.3.7。 | 无 |
| `test_str_leading_zeros`、`test_objects`、`test_complex`、`test_integ_coeffs` | 检查 poly1d 的 `__str__`、`__setitem__`、Decimal / 复数系数、`integ` / `deriv`。 | 只有当改动波及 poly1d 的其它方法时才相关 |
| `test_zero_dims`（`:203-207`） | 只要求不抛 `ValueError` 以外的异常。 | 无 |

小结：回归键基本不碰 `__eq__` / `__ne__`。旧的比较语义只靠目标键第 221–223 行保护，而且只覆盖同长度的情况。

## 4. 需求—断言双向映射

| 公开要求 / 合理旧行为 | 公开依据 | 对应断言 | 覆盖情况 | 执行证据 / 下一步验证 |
| --- | --- | --- | --- | --- |
| `p == None` 不抛异常，结果为"不相等" | 题面原例 | `:219` | 覆盖 | noop 在 `:219` 失败（两份 noop 日志 L31-42）；gold PASSED；DEV private gold 的 `mcve_statement` 打印 `False` |
| 与其它非 poly1d 对象（int、list、str、ndarray）比较也不抛 | 题面 "non-`poly1d` object, such as `None`" | 无 | **缺失**（只测了 None） | 静态推断；§11 候选 C1 |
| `!=` 给出"不相等" | 题面 "indicating that the objects are not equal"；`__ne__` 委托给 `__eq__`（`polynomial.py:1206-1207`） | `:220` | 覆盖（题面没写明） | gold 下 DEV `mcve_other_entries` 第 1 项为 `True`；§11 候选 C2 |
| 反射比较 `None == p` | 走同一个 `__eq__` | 无 | 没有直接测；但任何改在 `__eq__` 内的修复都会同时覆盖它 | DEV private gold 第 2 项为 `False` |
| `__eq__` 返回 `False` 或 `NotImplemented` 都可以 | 题面 | 测试只看运算结果 | 没有过度约束 | 静态 |
| 同长度 poly1d 的相等 / 不等 | 旧行为 | `:221-223` | 覆盖 | gold PASSED |
| 不同长度 poly1d 的比较（shape 分支） | 旧行为；公开的 `TestRegression.test_poly_eq` | 无 | **缺失**（评分侧没有） | 静态；解题者可以用公开测试自检 |
| poly1d 的其它功能 | 旧行为 | 9 个有效回归键 | 与本改动基本无交集 | 4 次 current 运行都 PASSED |

反向核对：每条关键断言都有公开依据。`:220` 的依据来自语义推导而不是题面原文；`:221-223` 保护的是旧行为。

## 5. 替代实现与部分实现（静态推演，Python 3.7.9）

| 候选 | `:219` 的结果 | `:220` 的结果 | 其余断言 | 预测 reward | 判断 |
| --- | --- | --- | --- | --- | --- |
| gold：`__eq__`、`__ne__` 对非 poly1d 都返回 `NotImplemented` | False | True | 通过 | 1（4 次实测 + M3 两次） | 正确 |
| 只改 `__eq__`，对非 poly1d 返回 `False` | False | `not False`，即 True | 通过 | 1 | 正确；题面明确允许 |
| 只改 `__eq__`，对非 poly1d 返回 `NotImplemented` | False | `not NotImplemented`，即 **False** | — | **0** | 判 0 是对的（`p != None` 静默算错）；但对照题面字面是陷阱 |
| 强制转换 `other = poly1d(other)`（仿照 `__add__`） | `poly1d(None)` 不会抛：`atleast_1d(None)` 得到 `[None]`（object），`trim_zeros` 对它保持不变；shape (1,) 与 (3,) 不等，所以 False | True | 通过 | 1 | 正确 |
| 用 `hasattr(other, 'coeffs')` 判断，否则返回 `NotImplemented`，`__ne__` 同步修改 | False | True | 通过 | 1 | 正确 |
| 删掉 `__ne__`，依赖 Python 3 自动对 `__eq__` 取反 | False | 回退到身份比较 `is not`，即 True | 通过 | 1 | 在本环境正确（不兼容 Python 2，但与评分无关） |
| 只特判 `other is None` | False | True | 通过 | **1** | **漏测**：`p == 3` 仍然会抛 |
| 按字面理解，让 `__ne__` 对非 poly1d 返回 `False` | False | **False** | — | 0 | 判 0 是对的（语义错误） |
| 把 `__eq__` 重写成 `isinstance(...) and (self.coeffs == other.coeffs).all()`，去掉 shape 检查 | False | True | `:221-223` 都是同长度，仍然通过 | 1 | **未测回归**：不同长度比较时，numpy 1.13 的逐元素比较会失败，返回的不是数组，`.all()` 调不了或直接抛错，隐藏测试抓不到 |

"`poly1d(None)` 不会抛"的依据是 `polynomial.py:1053-1059`、`shape_base.py:51-53`，以及 `trim_zeros` 里 `None != 0.` 为真；没有运行验证。

## 6. 运行原件核对

**current 行**（`run_refs.json` 的全部 4 行，每个账本的第 16 行）：

- 四行都是同一题、同一张派生镜像：`rh2-r2e-derived/numpy:18b7cd9df7a4-r2e_derive_v1`，镜像 ID `sha256:61363b45…`，来源 digest `sha256:f0258fc6…`，recipe `r2e_derive_v1`。
- 四行都是 `derived_image_recipe=None`、`env_qualification=absent`、`resource_facts=None`，与 `run_refs.json` 里 `env_recipe/resource_recipe=null` 一致。环境卡提到的 numpy `43e333e2`（env 配方）和 `2f4a9650`（资源配方）是别的题。
- 评分条件：用户 54322，2 CPU / 4 GiB / `/tmp` 1 GiB，`network=deny_all`。观测到 `RH2_OBS_IMPORT_PATH=/testbed/numpy/__init__.py`、`RH2_OBS_PKG_VERSION=1.13.0.dev0+6a3edf3`，与 base 一致。
- 日志里 `RH2_SETUP_HIDDEN_TESTS_TREE=2197510…` 等于 grading_bundle 的 `hidden_tests_tree_sha256`；`RH2_SETUP_ENTRY_SHA256=8285765…` 等于 `run_tests_sh_sha256`；`RH2_SETUP_OK=1`。
- **noop**（R-f 的 `evallog_replay-r2e-rf-all-noop-n_3cdaf461.eval.log`、rerun2 的 `evallog_replay-r2e-envrepair-rer_f466e78b.eval.log`）：`collected 11 items`，进度为 `.....F.....`。失败位置是 `r2e_tests/test_1.py:219`，报 `numpy/lib/polynomial.py:1202: AttributeError: 'NoneType' object has no attribute 'coeffs'`（两份日志都在 L21-42）。账本记录 `mismatched=['TestDocs.test_poly_eq']`、`keys_equal=True`，reward 0。
- **gold**（R-f 的 `…gold-n_d91e0720.eval.log`、rerun2 的 `…rer_f34c3153.eval.log`）：
  - `git status` 第一行是 ` M numpy/lib/polynomial.py`，结果 11 passed（L37）。
  - 账本 `candidate.patch_sha256=07bbe5f4…`，与 `validation_bundle.json` 的 `golden_patch_sha256` 以及本地 `gold.patch` 的哈希一致。
  - `projection.included_paths=['numpy/lib/polynomial.py']`，reward 1。
- 一处时间标注：rerun2 这组的标签写的是"09-24"，账本 `started_at_utc` 是 `2026-09-23T18:27Z`。这只是时区差，不影响结论。

**M3 独立参考**（来源镜像、来源材料，只作对照）：两次 gold 都是 11/11，两份 `test_output.txt` 只有耗时不同。facts 记录 `head_is_parent_of_fix=yes`、`gold_matches_git_diff_changed_lines=True`。gold_meta 显示来源修复只包含 `numpy/lib/polynomial.py` 和被排除的测试文件，所以 gold 没有漏掉非测试文件。

**devcheck**（真实 Claude Code 2.1.205 + 桩端点，agent/54321 经 CC Bash 执行）：

- **镜像：** `sha256:065c0cc8…`；`DEV/orig/attempt.json` 记录 `overlay.recipe_id=r2e_derive_v1`、`base_image_ref=namanjain12/numpy_final:18b7cd9d…`。**它与评分行的 `61363b45…` 不是同一个镜像 ID**，而是同一配方、同一来源镜像在另一台机器上的重建。本题是纯 Python 改动，依赖都来自来源镜像，所以我把两者当作等价，但这不等于证明了它们是同一张镜像。orig 与 private_gold 用的是同一个 `065c0cc8…`。
- **预检**（`captures/r2e_preflight.out:1-3`）三项都 ok：解释器可执行；隐藏测试不可见（没有 `/r2e_tests`，没有 `/testbed/r2e_tests`，私有目录不可读）；HEAD 没有子提交。
- **环境**（`captures/env.out:1-11`）：解释器是 `/testbed/.venv/bin/python` 3.7.9；numpy 从 `/testbed/numpy/__init__.py` 导入；有 nose 1.3.7 和 pytest 7.4.4，没有 pip；初始工作区只有 `?? install.sh`、`?? run_tests.sh` 两个未跟踪文件。
- **base 复现：** `mcve_statement.out:3-5` 报出与题面相同的错误；`mcve_other_entries.out:3-7` 显示 `p != None` 经 `__ne__` → `__eq__` 同样会抛。
- **公开测试：** `test_polynomial.out` 10 passed（公开版没有 `test_poly_eq`）；`test_regression_poly.out` 9 passed。
- **private gold**（`private_control.json`）：
  - `mcve_statement` 输出 `False`。
  - `mcve_other_entries` 输出 `True False False False NotImplemented`，依次对应 `p != None`、`None == p`、`p == 3`、`p == [1, 2, 3]`、`p.__eq__(None)`。
  - 两组公开测试仍然全过。
- **提示渲染没有捕获：** `stub/requests/messages_000.json` 的 user 消息是 devcheck 的桩指令（"execute exactly the tool calls you are given"），system 里也没有 venv、conda 或测试重置的字样。所以**本题实际任务提示是怎样渲染的，这里看不到**。

## 7. 八方面覆盖

| 方面 | 已查 | 未查 / 缺项 |
| --- | --- | --- |
| 公开需求 | 题面、public_hints、brief、poly1d 源码与公开测试 | 实际渲染给 actor 的 R2E 提示措辞（devcheck 里只有桩消息） |
| 材料与初始问题 | base 是修复提交的父提交（M3 facts）；源码 `:1202` 的出错路径；两次 noop 日志加 devcheck 复现；隐藏测试 = 公开测试 + 新测试；gold 上下文吻合；无修订；initial diff 为空 | — |
| 测试是否测到要求 | 目标键的 5 条断言和 helper 都追到底；逐个定性回归键；找出死键 | 数值类键在不同 CPU 上是否稳定没有验证 |
| 误拒 | 静态推演了 9 条替代 / 部分实现路线（§5） | 没有实际回放 |
| 回归与 gold | gold 只加了两处守卫、没有无关改动、修到了原例；grep 了仓库内 `poly1d` 的用法；公开回归测试在 gold 下仍然通过（devcheck private） | 不同长度比较不在评分内 |
| 开发条件 | 环境卡、brief、devcheck（真实 CC 链路、agent 身份） | 正式启动链与提示措辞（环境卡写明待 A 审） |
| 交付与评分边界 | 修复文件被跟踪，且在投影内；没有 conftest；隐藏测试只依赖 `numpy` 和仓库内的 `numpy.testing`；`install.sh` 没有进入公开导出（manifest 的 `untracked_missing` 已声明） | 平台共性问题没有逐题展开（agent 可以写 `.venv`；`candidate_writable_prefixes` 指向 conda 路径） |
| 题目关系与用途 | 与公开的 `TestRegression.test_poly_eq`（Ticket #554）同主题，但不撞键；题面给出了修法方向 | 本批其它题是否同源（不在读取范围内） |

## 8. R2E 专项

- **(a) 非 PASSED 期望键：** 没有，11 个键全是 PASSED。因此不存在"更完整的修复把 FAILED 翻成 PASSED 反而判 0"的风险。唯一的判 0 风险是真的破坏了 9 个有效回归键。
- **(b) 题面报错是否出现在 noop 目标键里：** 是。两次 current noop 都在 `test_1.py:219` 抛出 `AttributeError: 'NoneType' object has no attribute 'coeffs'`（`polynomial.py:1202`），与题面示例的注释一字不差。
- **(c) 题面是否泄漏修法：** 题面给出了返回值选项（`False` / `NotImplemented`）并点明根因，几乎等于告诉了修法；但没有提到 `__ne__`。这影响难度，不影响评分是否正确。
- **(d) 测试支撑与撞键：**
  - 隐藏测试只导入 `numpy` 和 `numpy.testing`。后者是仓库内的库代码，用的是 base 版，候选可以修改，评分时也不会重置。这是 numpy 系题目的共性，合法修复没有理由去碰它。
  - 不导入仓库的测试模块，没有 conftest，也没有相对路径资源。
  - 只有一个文件、一个类，不会撞键。仓库里另一个 `test_poly_eq` 在 `TestRegression` 类里，也不在 `r2e_tests` 中。
  - 死键 `test_doctests` 来自上游原文件的写法，不是搬迁造成的。
- **(e) 时间 / 随机 / 资源敏感：** 没有依赖时间的键；`test_poly` 固定了随机种子。数值类键在 4 次 current、2 次 M3 和 devcheck 的公开测试运行里都通过。单次测试不到 1 s，内存峰值约 300 MB。
- **(f) 修订：** 没有（`revisions.json` 为 `[]`，`material_revisions` 为 `[]`）。

## 9. 发现清单

| # | 类型 | 内容 | 影响 | 证据级别 |
| --- | --- | --- | --- | --- |
| R1 | 漏测（低） | 非 poly1d 对象只测了 `None`；只特判 `None` 的部分修复能得 1 | reward 可能给到"只修了原例"的解 | 静态推断 |
| R2 | 隐含要求（信息，不是误拒） | `:220` 要求 `p != None` 为 True；只在 `__eq__` 里返回 NotImplemented 的解会判 0 | 判 0 是对的；对照题面字面是个陷阱，同时也是有用的区分点 | 静态推断（依据 Python 语义） |
| R3 | 死键（信息） | `test_doctests` 执行 0 个 doctest | 实际回归覆盖比键数看上去少；本修复不受影响 | 静态（ast 解析 + `rundocs` 源码） |
| R4 | 未测回归（低） | 不同长度 poly1d 比较不在评分内 | 去掉 shape 检查的重写也能得 1 | 静态推断 |
| R5 | 题面给修法（信息） | 返回值和根因都写在题面里 | 难度低 | 静态 |
| R6 | 开发条件缺项 | 实际任务提示没有捕获；devcheck 与评分用的镜像 ID 不同（同配方重建） | 需要在 actor 条件下确认 | 证据缺项 |

未发现：材料错配、误拒、错误回归、开发缺口（镜像层面和 devcheck 都已跑通复现与公开测试）。

## 10. 开发需求（逐题）

- **导入：** 在 `/testbed` 下用 `python -c`，或设 `PYTHONPATH=/testbed`。numpy 在 `/testbed` 就地构建（`1.13.0.dev0+6a3edf3`）。devcheck 已实测（agent/54321，经 CC Bash）。
- **依赖：** 不需要新包。nose 1.3.7（`assert_raises` 要用）和 pytest 7.4.4 已经在 venv 里；没有 pip，也无法出网。镜像层面与 devcheck 均已实测。
- **资产 / 网络阶段：** 都不需要。
- **权限：** `/testbed` 属主为 54321，可写（prelaunch 记录 `WORKDIR_OWNER=54321`、`WORKDIR_WRITABLE=1`）。
- **构建：** 纯 Python 改动，不需要重新编译。
- **最小验证命令：**
  - `cd /testbed && python -c "from numpy import poly1d; p = poly1d([1, 2, 3]); print(p == None, p != None, None == p, p == 3)"`
  - `python -m pytest numpy/lib/tests/test_polynomial.py`
  - `python -m pytest numpy/lib/tests/test_regression.py -k poly`（包含不同长度的比较）
- **提交边界：** 修复落在已跟踪的 `numpy/lib/polynomial.py`，gold 的投影里也包含它。候选放进 `r2e_tests/` 的文件会被评分删掉；放进 `numpy/lib/tests/` 的测试不参与评分。
- **actor 待验：**
  - 实际渲染的 R2E 提示措辞（`public_hints` 原文写的是 conda、pip、测试重置）。
  - 正式启动链是否使用派生镜像（环境卡说 09-25 已接上，待 A 审）。

## 11. 暂定处置与下一步

- **暂定处置：** 在 `static_review` 下保留 `needs_review`，理由写"静态候选待 actor 验证"；暂不建议修订。如果以后不只用于开发诊断，而要进入训练奖励，可以考虑在 `test_poly_eq` 里补一条非 None 的非 poly1d 断言，例如 `assert_equal(p == object(), False)`。gold 和强制转换路线都应得 False，这仍在原需求范围内，不算扩大需求。但这会改变测试标准，需要按协议另行决定。
- **唯一优先的下一步：** 在本题的派生镜像上做一次评分回放，放入 3 个构造候选：
  - **C1** 只特判 `None`（在 `__eq__` 里写 `if other is None: return False`）：预期 reward 1。同时手动确认 `p == 3` 仍然会抛，以此证实 R1。
  - **C2** 只在 `__eq__` 返回 `NotImplemented`，不改 `__ne__`：预期 `test_poly_eq` 在 `:220` 失败、reward 0，以此证实 R2。
  - **C3** 只在 `__eq__` 返回 `False`：预期 reward 1，证明题面明确允许的路线不会被误拒。
- **可选：** 在同一个容器里对 `r2e_tests/test_1.py` 调用 `rundocs`，统计 `runner.tries`，确认它为 0（证实 R3）。
