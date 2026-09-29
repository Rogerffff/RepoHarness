<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237：私有主审初判（读历史前封存）

- 角色：R2E 私有主审（静态审查）；日期 2026-09-25；按角色卡第 1–7 步完成，本稿在打开任何历史调查之前保存。
- 路径简写：`PUBLIC_DIR` = `runs/r2e_static_prep_20260924/v2/public/orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237`；`PRIVATE_DIR` = 同级 `private/` 下的同名目录；`DEVCHECK` = `runs/r2e_actor_20260925/devcheck/orange3__22e98f8f4cccc25f0d0217f9f4251b6`。`owcreateclass.py` 指 `Orange/widgets/data/owcreateclass.py`，`test_1.py` 指 `PRIVATE_DIR/hidden_tests/test_1.py`。
- 证据级别：【静态】源码或文本推断；【grader 执行】RH2 回放评分的日志与 ledger；【actor 实测】`DEVCHECK/orig`（正式启动路径 + 真实 Claude Code 2.1.205 + 桩模型，agent 54321，派生镜像）；【私有对照】`DEVCHECK/private_gold`（root，同一派生镜像，应用 gold 后执行同一批公开命令，不联网）。

## 0. 要点

1. **题目**：`unique_in_order_mapping` 计算 `mapping` 时直接用了排序置换 `p = np.argsort(idx)`，应当用它的逆置换；`p` 不是对合（自身的逆）时结果出错。目标键只有 `TestHelpers.test_unique_in_order_mapping`，其余 22 键是同文件回归，期望 23 键全部 PASSED。
2. **评分侧在已读范围内无问题**：noop 在 `test_1.py:94` 失败，`x: array([2, 0, 1])`，正是题面 "Actual Behavior" 的数值。RH2 的 noop ×3、gold ×3 与 M3 独立 runner 的 gold ×2 逐键一致。断言只用 `np.testing.assert_equal`，不限定返回类型；静态上没有发现会误拒的合理解法。
3. **主要问题：题面把 gold 当作 "buggy code" 给出。** "Example Buggy Code" 的函数体与 `gold.patch` 新写的函数体逐字节相同（9 行）。actor 实测逐字运行这段代码，输出 `Mapping: [0, 1, 2]`，也就是期望行为。所以题面自相矛盾，而且等于把完整修法交给了解题者。
4. **题目关系**：同批另外 3 道 orange3 题（`50f6a758…`、`c3fb72ba…`、`f5026689…`）的 base 工作树里，这个函数已经是 gold 版本（含 docstring 的整段函数文本哈希相同）。
5. **暂定处置**：`needs_review`。原因是题面泄漏修法，不是测试或评分争议。建议修订公开题面（换成仓库真实实现或删去该代码块，隐藏测试与 expected 不动）；若不修订，标注"题面给修法"，不用于能力测量或留出评测。
6. **关键未知**：正式链路下模型实际收到的题面消息没有被捕获（DEVCHECK 的用户消息是桩文本）；正式 rollout 是否使用派生镜像要以 B 线实现为准（DEVCHECK 这次用的是派生镜像）。

## 1. 公开读者产物核对（第 1 步）

| 公开读者的判断 | 私有材料或运行证据 | 结论 |
| --- | --- | --- |
| base 对 `[2,3,1]` 返回 mapping `[2,0,1]` | actor 实测 `mcve_repo_function`：`(array([2, 3, 1]), array([2, 0, 1]))`；grader noop 在 `test_1.py:94` 得到同值 | 确认 |
| "Example Buggy Code" 不是仓库实现，运行后得到期望输出 | 文本比对：与 gold 函数体逐字相同；actor 实测 `mcve_statement_code`：`Mapping: [0, 1, 2]` | 确认，且比公开读者判断的更严重：它就是 gold |
| 5 组公开用例在 base 上全过，暴露不了 bug | actor 实测 `test_helper`：1 passed；noop 日志中 L77–91 的断言全部通过后才在 L94 失败 | 确认 |
| 返回类型未约定，隐藏测试的比较方式未知 | 隐藏测试 L77–100 只用 `np.testing.assert_equal`，list、ndarray、tuple 都能通过 | 已消除 |
| Cython 扩展是否已构建、pytest 是否已装未知 | actor 实测：`/testbed/Orange/data/_valuecount.cpython-37m-x86_64-linux-gnu.so` 存在；pytest 7.4.4；numpy 1.17.5 | 已消除 |
| 只导入 widget 模块是否需要显示 | DEVCHECK 的命令都带 Qt 前缀，没有测不带前缀的情况 | 仍未知，不影响开发 |
| widget 层后果：类名按 `b,c,a` 首现时实例被分错类 | actor 实测 base 下 `f(('b','c','a'))` 的 mapping 为 `[2, 0, 1]`；私有对照中 gold 为 `[0, 1, 2]`；隐藏 widget 用例没有这种顺序 | 确认；测试只在 helper 层覆盖 |
| public_hints 中 conda 与"重置测试文件"的说法不符 | actor 实测 `VIRTUAL_ENV=/testbed/.venv`，没有 conda；环境卡 §2–3 | 确认；不妨碍本题的合法解 |
| 容器里 `git` 是否可用 | actor 实测：`/testbed` 有 `.git`，HEAD=`96fda39b…`，13478 个提交，refs、remotes、reflog 都为 0，HEAD 没有子提交 | 已消除 |
| `bash run_tests.sh` 预计找不到 `r2e_tests` | 没有执行；与预检 `RH2_PREFLIGHT_HIDDEN_TESTS=ok`（`/testbed/r2e_tests` 不存在）一致 | 静态一致 |

公开读者没有捕获、本稿也补不上的：**正式链路下的实际消息（题面 + 提示）**。DEVCHECK 捕获的首个请求 `orig/stub/requests/messages_000.json` 中，用户消息是 "Devcheck run: execute exactly the tool calls you are given, then stop."，不是题面；系统提示是 Claude Code 自带的，含 git status 和 base 的近期提交，不含 `public_hints`。

## 2. 隐藏测试展开（第 2 步）

**材料**：`hidden_tests/` 只有空的 `__init__.py` 和 `test_1.py`。`test_1.py` 与公开的 `Orange/widgets/data/tests/test_owcreateclass.py` 相比，只在 `test_unique_in_order_mapping` 里多了 L92–100 共 9 行：

```
[2, 3, 1]    → u [2, 3, 1], m [0, 1, 2]      (L92–94)
[2, 3, 1, 1] → u [2, 3, 1], m [0, 1, 2, 2]   (L95–97)
[2, 3, 1, 2] → u [2, 3, 1], m [0, 1, 2, 0]   (L98–100)
```

**目标键** `TestHelpers.test_unique_in_order_mapping`（L75–100，`@staticmethod`）：直接调用 helper，没有 fixture；最终断言是 `np.testing.assert_equal(u, …)` 和 `np.testing.assert_equal(m, …)`。三组新输入的唯一值首现顺序都是 `[2,3,1]`，排序置换都是三元轮换 `p=[1,2,0]`（非对合），正是 base 出错的情形；公开 5 组的 `p` 都是恒等或对合。noop 在第一组新断言 L94 处失败，后两组在 noop 上没有执行到。

**回归键（22 个）**：

- `TestHelpers` 其余 8 个：测 `map_by_substring`、`ValueFromStringSubstring`、`ValueFromDiscreteSubstring`（含 `map_values` 参数和 `__eq__`/`__hash__`）。它们不调用 `unique_in_order_mapping`，保护的是 `map_values` 在下游的用法，与 helper 的返回类型无关。
- `TestOWCreateClass` 14 个：本类定义 11 个，另有 3 个继承自 `orangewidget` 的 `test_image_export`、`test_minimum_size`、`test_msg_base_class`。`set_data` 在属性列表非空时末尾会调用 `apply()`（`owcreateclass.py:306`），所以除 `test_no_data` 和 3 个继承用例（实现未读，推测不发送数据）外，其余用例都会经 `_create_variable`（L523–552）进入 helper。用到的类名序列有：`C1`、`C1,C2`、`Cls1,Cls2`、`Cls1..Cls3`、`repeated, not repeated, repeated`，以及 `test_add_remove_lines` 删光规则后的 `names=()`（L495–500）。这些序列对应的置换都是恒等或对合，**不会触发本 bug**；它们守的是调用方对返回值的消费方式：`str()`、`tuple()`、缓存键哈希（`test_same_class` 依赖 `cached_variables` 做 `assertIs`）和空输入。
- 阅读范围：`test_1.py` 全文；`owcreateclass.py` 全文；`Orange/widgets/tests/base.py` L1–60 与定义列表；`Orange/widgets/tests/__init__.py`。**没读** site-packages 里 `orangewidget/tests/base.py`（3 个继承用例的实现）。

## 3. 双向映射（第 3 步）

| 需求或旧行为 | 公开依据 | 测试与决定性断言 | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- |
| R1：`[2,3,1]` → u `[2,3,1]`、m `[0,1,2]` | 题面 Expected Behavior | L92–94 | 覆盖 | noop 在 L94 失败（`[2,0,1]`）；gold 3 次 PASSED |
| R2：一般规则 `u[m[i]] == a[i]`，`len(m) == len(a)` | 题面描述句；docstring L151–153；公开用例 `[2,1,2,3]` | L95–100（含重复元素的三元轮换）和 L77–91 | 覆盖；置换类型最多到三元轮换，见下 | 同上 |
| R3：uniques 按首现顺序 | 题面；docstring | 所有 `assert_equal(u, …)` | 覆盖 | base 本来就对 |
| R4：5 组公开用例 | 公开测试 L76–91 | 同文件 L77–91 | 覆盖 | noop 上全部先通过 |
| R5：函数名、单参数、返回二元组 | 导入和调用方解包 | 导入 L9–12；解包 | 覆盖 | — |
| R6/R7：调用方兼容（`str()`、`tuple()`、可哈希）与空输入 | `owcreateclass.py:537-548`；删光规则的路径 | 14 个 widget 键；`test_add_remove_lines` L495–500；`test_same_class` | 覆盖，但不含非对合置换 | noop 与 gold 下都 PASSED |
| R9：返回类型 | 未约定 | `np.testing.assert_equal` 与类型无关 | 无冲突 | — |
| R11：widget 层按错类（类名首现顺序对应非对合置换） | 静态推演，题面没提 | 没有 widget 层用例 | 部分：只在 helper 层覆盖 | actor 实测 base `('b','c','a')` → `[2,0,1]` |

**反查**：L92–100 的每条断言都能追到题面原例或 docstring 的规则，没有看到缺少公开依据的断言。

**非 gold 的合理解**：保留 `np.unique`，把 mapping 改成 `np.argsort(np.argsort(idx))[inv]`（先对 `p` 取逆），返回 `ndarray`。【静态】`assert_equal` 遇到 ndarray 走 `assert_array_equal`，数值相同即通过；空输入走的是 base 已在 noop 上通过的同一条 `np.unique` 路径；调用方先 `tuple()` 再用，`np.int64` 与 `int` 的哈希和相等比较一致。预计 23/23。没有具体疑点，不需要 CPU 反例。

**可能蒙混的部分实现**（都会被现有断言拒绝）【静态】：

- `mapping = inv`：公开用例 `[2,1,0,3]` 得到 `[2,1,0,3]`，在 L88 失败。
- `mapping = idx[inv]`（每个元素在输入中的首现位置）：三组新用例都能过，但公开用例 `[2,1,2,3]` 得到 `[0,1,0,3]`，在 L91 失败。
- `mapping = p[p][inv]`（对三元轮换恰好等于逆置换）：公开用例 `[2,1,0,3]` 得到 `[2,1,0,3]`，在 L88 失败。
- `mapping = range(len(a))`：`[42,42]` 得到 `[0,1]`，在 L85 失败。
- 只改调用方、不改 helper：在 L94 失败。

剩下的理论缺口只有四元及以上轮换（例如 `p^5` 这类不自然的写法）或针对具体输入硬编码，不构成现实风险。

## 4. R2E 专项（第 4 步）

- **(a) 非 PASSED 键**：期望 23 键全是 PASSED，没有 FAILED/ERROR，不存在"更完整的修复把失败翻成通过而被判 0"。更完整的修法（例如另外改进 widget 层）也不会改变任何现有键。
- **(b) 题面描述的报错是否出现在 noop 失败里**：出现。三次 noop 的失败位置都是 `r2e_tests/test_1.py:94`，`x: array([2, 0, 1])`，`y: array([0, 1, 2])`，与 "Actual Behavior" 的数值一致。格式对不上：题面写的是 list 风格 `[2, 3, 1]`，base 返回 ndarray（`print` 显示 `[2 3 1]`）；gold 返回 list，恰好是题面的格式。由此推测题面生成时运行的是修复后的代码（推断，未核实）。
- **(c) 题面是否泄漏修法：是，逐字泄漏。** 比对方法：取题面代码块中 `def` 之后到 `return` 的 9 行，与 `gold.patch` 的 8 行 `+` 加上未改动的 `return unique_in_order, mapping` 逐行比较，完全相同【静态】；actor 实测和私有对照里，这段代码都输出期望值。影响有两点：
  1. 把这段代码照抄进仓库就是 gold，得 23/23。
  2. 题面说这段代码"有 bug、返回 `[2, 0, 1]`"，与事实矛盾，可能误导解题者去找仓库里不存在的 `first_position` 实现，或刻意回避正确写法。这是解题侧的风险，不影响评分是否正确。
- **(d) 测试辅助与搬迁伪影**：
  - 隐藏测试导入仓库内 base 版 `Orange/widgets/tests/base.py` 的 `WidgetTest`。候选可以改它，评分时也不重置，这是 R2E 通用机制（环境卡 §3）；合法修法不需要碰它。
  - 工作树里没有任何 `conftest.py`，`setup.cfg`、`tox.ini`、`pyproject.toml` 也没有 pytest 配置，所以搬到 `r2e_tests/` 不会丢配置。数据集 `heart_disease`、`zoo`、`iris` 按 Orange 的数据路径查找，与测试文件的位置无关。
  - 只有一个隐藏测试文件，不存在跨文件撞键。
  - 被导入的 `WidgetTest` 本身也被 pytest 当作测试类收集，产生 3 个 SKIPPED（"… as .widget was not set"）。SKIPPED 不成键，合法修法也改变不了它们。
- **(e) 时间、随机与资源**：
  - 没有时间或随机依赖。
  - Qt/xvfb 相关的回归键（含继承的 `test_image_export`、`test_minimum_size`）原则上受显示环境影响，但在以下条件下全部稳定：3 个派生镜像构建（`24840fed…`、`a0135227…`、`50fd6e31…`），以及三种身份（评分 54322、actor 54321、私有对照 root）。
  - grader 内存峰值 2139–2198 MB（上限 4 GiB），测试阶段 4.8–5.6 s。
  - `cached_variables` 是类级缓存，会跨用例保留；只有 `test_same_class` 显式依赖它，而且在用例内部自洽，顺序风险低。
- **(f) 材料修订**：无（`revisions.json` 为 `[]`）。

## 5. gold 检查（第 5 步）

- **改动内容**：把 `owcreateclass.py` 中 `unique_in_order_mapping` 的 3 行 `np.unique` 实现换成 dict 单遍扫描。docstring 和签名不变，没有改其它文件，也没有无关改动。
- **原例**：私有对照中，`f([2,3,1])` → `([2, 3, 1], [0, 1, 2])`，`f(('b','c','a'))` → `(['b', 'c', 'a'], [0, 1, 2])`【私有对照】；grader 上 gold 3 次 23/23【grader 执行】。
- **行为差异**：
  - 返回类型从 ndarray 变成 list。仓库内唯一的调用方（L537，已 grep 核对）先 `str()`、`tuple()` 再使用，缓存键和 `__eq__`/`__hash__` 不受影响。
  - 对元素的要求从"可排序"变成"可哈希"。例如 `[1, "1"]`：`np.unique` 会先统一 dtype、合并成一个值，dict 会保留两个。调用方只传 str，这属于没测到、但也没有影响的边界【静态】。
  - site-packages 里其它潜在调用者没查。
- **结论**：gold 正确、改动最小，与本题对应。判断依据是公开规则 R1–R8，不是"与 gold 相同"。

## 6. 开发需求（第 6 步）

| 方面 | 需求 | 证据与级别 |
| --- | --- | --- |
| 解释器与导入 | `python` 指向 `/testbed/.venv/bin/python`（3.7.9）；Orange 从 `/testbed/Orange` 导入，改源码立即生效，不用重装；Cython 扩展已构建 | actor 实测（`env.out`）；grader 侧 `RH2_OBS_IMPORT_PATH=/testbed/Orange/__init__.py` |
| 依赖 | numpy 1.17.5、pytest 7.4.4 已安装；pip 24.0 存在但不能出网；本题不需要新依赖 | actor 实测 |
| 资产 | widget 测试用到 `Orange/datasets/` 下的 `heart_disease`、`zoo`、`iris`，agent 可读 | actor 实测（`test_widget_file` 23 passed） |
| 权限 | `/testbed` 属主 54321，可写；HOME 是 256 MiB tmpfs；`/tmp` 1 GiB；`/rh2/bash_env` 对 agent 只读 | actor 实测（`prelaunch.json`、`env.out`） |
| 网络 | 各阶段都不需要；外部 DNS 被拒绝，只通模型中继；grader 为 `deny_all` | actor 实测 + ledger |
| 构建 | 不需要（纯 Python 改动） | 静态 |
| 复现 | 公开测试在 base 上通过，需要自己写复现；带 `QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum` 导入仓库函数可行 | actor 实测（`mcve_repo_function`）；不带前缀的情况未测 |
| 公开测试 | 只跑 helper 用例 1.15 s；跑整个文件 1.42 s（23 passed, 3 skipped） | actor 实测 |
| git | HEAD=`96fda39b…`，13478 个提交，refs、remotes、reflog 都为 0，HEAD 没有子提交；`git status`、`git diff` 可用 | actor 实测（`attempt.json` 的 `git_sanitize` 与预检） |
| 提交边界 | 只需要改 `Orange/widgets/data/owcreateclass.py`；grader 对 gold 的投影包含该路径，`apply_user=agent/54321` | grader 执行；**真实工作区编辑后的冻结与投影没有经过 actor 验证**（DEVCHECK 没有编辑文件） |
| 实际消息 | 正式渲染的题面与提示没有被捕获；`public_hints` 中 conda 和"重置测试文件"的说法对 R2E 不成立（环境卡 §2–3） | actor 待验 |
| 镜像选择 | DEVCHECK 用的是派生镜像（`image_is_overlay_derived_id: true`，`/r2e_tests` 不存在）。环境卡说正式 `rollout_spec_from_view` 默认取来源镜像（`/r2e_tests` 可读、修复提交在 main 上），需要 B 线修改 | actor 待验（以 B 线实现和 A 线审查为准） |

## 7. 八方面覆盖

| 方面 | 已查 | 未查或限度 |
| --- | --- | --- |
| 公开需求（3、23） | 题面、hints、docstring、公开测试、调用方；发现题面自相矛盾并泄漏修法 | 实际渲染消息未捕获 |
| 材料与初始问题（1、2、27） | base、gold、隐藏测试、expected、`run_tests.sh` 对应同一版本（隐藏测试树与入口的 sha256 在 grading bundle、`run_refs.json` 和日志中一致）；`initial_diff` 为 0 字节；初态 bug 经 actor 实测和 noop 日志双重确认 | — |
| 测试是否测到要求（18–20、25、32） | 目标键直接测原例和两个推广例；22 个回归键按类核对调用路径；解析到 23 键，都在输出段内，测试段执行完整 | 3 个继承的 orangewidget 用例实现未读 |
| 是否误拒合理解（24、28） | 用 numpy 取逆的替代解静态上能通过；断言与返回类型无关 | 没做 CPU 验证（没有具体疑点） |
| 回归与 gold 完整性（26、27） | 唯一调用方、缓存键、`__eq__`/`__hash__`、空输入 | site-packages 中的潜在调用者未查 |
| 开发条件（6–15） | 见 §6；actor 实测覆盖导入、依赖、资产、权限、网络和公开测试 | 不带 Qt 前缀的导入未测；编辑后的冻结未测 |
| 交付与评分边界（4、16–17、21–22、29–31） | 单文件交付；grader 恢复 2 个隐藏文件和入口；没有 conftest；派生镜像里没有隐藏测试和未来提交；M3 的 gold 测试段与 RH2 gold 一致 | 共享机制（根目录 conftest、改仓库测试辅助）只核了适用性，没做平台审计；M3 没有 noop 参考 |
| 题目关系与用途（5、29–30、37–40） | 题面逐字给出 gold；同批 3 道 orange3 题的 base 已含 gold 版函数 | 本批以外的跨来源重复未查；预训练污染无法判断 |

**checks 初拟**（第 8 步再定）：

- pass：1、2、4、6、7、8、9、10、11、13、14、17、18、19、20、21、22（仅 gold 有独立参考）、24、25、26、27、30、32。
- issue：3、23（题面矛盾）；29（题面泄漏 gold）；5（与 3 道同仓题的关系，影响划分）。
- unknown：16（actor 侧冻结未验）。
- not_applicable：12、28、37、38、39。
- not_checked：15、31、33–36、40。

## 8. 缺口与建议队列（交协调者）

1. **（需用户决定）修订公开题面**：把 "Example Buggy Code" 换成仓库真实实现（`owcreateclass.py` L155–157 三行），或删去该代码块；"Actual Behavior" 可改成 ndarray 的实际打印格式。这只改公开规格，隐藏测试和 expected 不动，属清单第 37 项中的"题面纠错"，会形成修订版；修订后要由新的公开读者重新阅读。若不修订：标注"题面给修法"，不用于能力测量或留出评测，只作为易题或链路冒烟测试。
2. **（数据划分）** 记录题目关系：`orange3__50f6a758…`、`c3fb72ba…`、`f5026689…` 的初态已含本题修复（函数文本相同）。本题应与它们放在同一划分组，至少不能在它们用于训练时把本题当作留出评测。
3. **（actor，B 线共性项）** 在正式链路下捕获一次真实的题面消息与 `public_hints`，并确认正式 rollout 使用的是派生镜像。
4. （可选，低优先级）CPU 校准：用 numpy 取逆的替代解跑一次评分，验证"断言与返回类型无关"的静态判断。

## 9. 暂定处置

- `disposition.scope=static_review`，state 保留 `needs_review`。原因：**题面泄漏修法，而且自相矛盾**（证据：文本逐字比对【静态】+ 逐字运行得到期望输出【actor 实测】）。这**不是**测试或评分争议，评分侧在已读范围内未见问题。
- 若按建议 1 修订题面，本题可作为静态候选进入 actor 验证。在当前题面下，泄漏会抬高成功率，不宜作能力测量。
- 唯一最值得先做的下一步：请用户决定是否修订题面（建议 1）。

## 附录 A：运行证据

以下各行在 `run_refs.json` 中都标为 `material=current`；日志 sha256 已与 `run_refs.json` 逐一核对，全部一致。

| 组 | 候选 | ledger:行 | 镜像 ID（前 12 位） | 结果 | 日志要点 |
| --- | --- | --- | --- | --- | --- |
| R-f 全池 09-23 | noop | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:23` | `24840fed8928` | 0，22/23 | 在 L94 失败；1 failed / 22 passed / 3 skipped |
| R-f 全池 09-23 | gold | `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl:23` | `24840fed8928` | 1，23/23 | 23 passed / 3 skipped |
| R-f 代表题重复 | noop | `runs/r2e_rf_20260923/remote/ledger_r2e_reps_noop.jsonl:4` | `a013522716b2` | 0，22/23 | 同 R-f 全池 noop |
| R-f 代表题重复 | gold | `runs/r2e_rf_20260923/remote/ledger_r2e_reps_gold.jsonl:4` | `a013522716b2` | 1，23/23 | 同 R-f 全池 gold |
| 环境轮复跑 | noop | `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:23` | `24840fed8928` | 0，22/23 | 同 R-f 全池 noop |
| 环境轮复跑 | gold | `runs/r2e_env_repair_20260924/_rerun2/ledger_gold.jsonl:23` | `24840fed8928` | 1，23/23 | 同 R-f 全池 gold |
| M3 独立 runner（来源镜像） | gold ×2 | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:7,56` | 来源镜像 | 1 | 测试段与 RH2 gold 逐行相同（耗时行除外） |

- 三份 noop 日志之间除时间戳和耗时行外逐行相同，三份 gold 日志也是如此。
- 共同条件：评分用户 `rh2grader`（54322），2 CPU、4 GiB、`/tmp` 1 GiB，`network=deny_all`。日志中 `RH2_SETUP_RESTORED=2`、`RH2_SETUP_TEST_FILES=3`。复跑两行 ledger 中 `num_parsed_tests=23`、`num_parsed_outside_segment=0`。
- `grader_trusted_setup` 阶段耗时 131–172 s，测试本身约 5 s。这是平台成本，不是本题问题。

## 附录 B：actor 实测与私有对照（`DEVCHECK`）

- `orig/attempt.json`：派生镜像 `50fd6e31e77a…`（tag `rh2-r2e-derived/orange3:22e98f8f4ccc-r2e_derive_v1`），Claude Code 2.1.205，桩模型。6 次 Bash 调用全部 rc 0；`checks` 各项均为真，包括 `r2e_preflight_ok`、`image_is_overlay_derived_id`、`bashenv_denied_for_agent`。
- `orig/captures/`：`env.out`、`mcve_repo_function.out`、`mcve_statement_code.out`、`test_helper.out`、`test_widget_file.out`、`r2e_preflight.out`，内容见 §1 和 §6。
- `orig/prelaunch.json`：`cap_drop` 为 ALL，开启 `no-new-privileges`；`DNS_EXTERNAL=DENIED`，`NET_relay=CONNECTED`，`WORKDIR_OWNER=54321`。
- `orig/stub/requests/messages_000.json`：只读了 system 与首条 user 消息；user 消息是桩文本，不含题面。
- `private_gold/private_control.json`：root 身份，gold 补丁干净应用；各公开命令的结果见 §1 和 §5。
- 这批公开命令是否够用：足以证明开发条件和复现路径；不覆盖真实编辑后的冻结，也不覆盖正式题面渲染（见 §6）。

## 附录 C：阅读与暴露范围

- **读了**：
  - 角色卡和四份方法文档；`public_read.md`。
  - `PUBLIC_DIR` 中的 `user_prompt.txt`、`environment_brief.md`、`public_bundle.json`、`worktree_manifest.json`（只看元数据字段）；`owcreateclass.py` 全文；公开测试（通过 diff 对照）；`Orange/widgets/tests/base.py` 片段和 `Orange/widgets/tests/__init__.py`；在整个工作树 grep 调用者、`conftest.py` 和 pytest 配置。
  - `PRIVATE_DIR` 的全部文件。
  - 附录 A 中的 8 份日志和 6 行 ledger；附录 B 所列的 `DEVCHECK` 文件。
- **为第 5 项额外读了**：同批其它 6 道 orange3 题公开工作树中 `owcreateclass.py` 的该函数文本（只做哈希比对），以及它们 `public_bundle.json` 的 `base_commit`；并 grep 了它们的 `user_prompt.txt` 是否提到该函数（都没有提到）。
- **没读**：
  - 任何 `history/` 目录、`docs/.../r2e_env_repair_20260924/`、任何 `*review*` 目录。
  - `r2e_static_review_20260925/` 下的 README 与 `assignments.json`。
  - `runs/` 下的分析与汇总文件、ledger 引用的 `diagnostics.json`、site-packages 源码。
- 本稿见过 gold、隐藏测试、expected 和运行日志，属于审查暴露记录，不提供给解题模型。
