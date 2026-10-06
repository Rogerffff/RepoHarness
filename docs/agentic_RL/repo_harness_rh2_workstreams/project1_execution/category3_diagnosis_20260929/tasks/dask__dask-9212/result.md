# dask__dask-9212：第3类诊断结果

2026-09-30 / Claude（云端，第3类第二批主审子代理）。原分类：第3类“已有具体疑点，缺辨别实验”。登记的下一步：在同一个 pure delayed 函数上核对 token、任务 key 和计算输出。读历史前的初判见 [initial_judgment.md](initial_judgment.md)（已封存，未改）。

**结论：问题和修法已明确，转第2类（R-c 修订 v1；正对照仍是 gold）。独立复核尚未进行。**

- **优先问题（同名 Enum 碰撞）已实测：后果真实，但只出现在边缘输入上，定性为 S2（T3），登记，不写进断言。**
  - gold 的 token 只取类短名。两个模块 `audit_a`、`audit_b` 里各有一个 `Color`，成员名和值都相同，它们的 `Color.RED` 得到同一 token，同一函数的任务 key 也相同。两个任务进同一张图时会合并成一个，返回同一个值：
    - pure delayed 返回 `audit_a, audit_a`，应为 `audit_a, audit_b`；
    - Delayed 的 `==` 与 `[]` 运算符返回 `True, True` 和两次 `from audit_a`。这两个运算符总是按 pure 建 key，不需要用户选择；
    - `map_blocks(color=...)` 给两个数组起了同一个名字，`x1 - x2` 全为 0，应为 −100。
  - 两个任务分开计算、或使用默认的 impure delayed 时，结果正确。base 上普通 Enum 的 token 是随机的，所以不会相撞，但也不确定。
  - 定为边缘输入的依据：
    - 要同时满足五个条件：两个不同的类短名相同、成员名相同、值相同；被同一个函数（其余参数也相同）放进同一张图；函数结果依赖类身份；
    - 题面自己建议的就是这种短名表示；
    - base 上 `IntEnum` 成员和 Enum 类对象本身早就按短名相撞（本次实测）；
    - 按文档示例写法（元组里放类对象）也一样相撞。
- **原测试放过错误实现（S1，§4 第 4 步；另有 T2c）。** 测试只比较题面示例里同一个类的两个成员。两个错误候选正式评分都是 1：
  - `w_value`（只用 value）：`Color.RED` 与其它类的同值成员、与整数 `1` 共用一个任务 key；
  - `w_noval`（丢掉 value）：Python 3.10 下 Flag 组合值的 name 都是 `None`，所有组合值共用一个 key，pure delayed 返回 `3, 3`，应为 `3, 5`。

  `w_hash`、`w_name` 在私有模拟中也得 1。
- **没有误拒（T1）。** 把模块名与限定名纳入 token 的 `alt_modqual` 正式评分 1；另外 4 个写法不同的合理实现在私有模拟中都是 1。§4 第 3 步的固定 token 退化候选 `w_const` 正式评分 0。
- **修法：R-c v1。** 在同一个测试函数内补两类非示例实例，测试 ID 与 F2P／P2P 分组都不变。正式诊断评分 13 次，全部符合预期：
  - gold 与 5 个合理实现为 1；
  - noop 与 5 个错误候选为 0；
  - 边界候选 `w_str` 为 1，理由见 §3。
- **题面自带修法。** “Possible Implementation”就是 gold 的核心函数。按现行做法记为难度属性（易题），不影响验收；修订后照题面写（即 gold）仍得 1。
- **不需要用户决定。** 本题没有 P5：原测试和修订测试都同时接受短名写法和带模块名的写法。如果要把“不同模块的同名类必须区分”写成硬要求，就会拒绝题面建议和 gold，属于改变任务目标，本页不建议。

## 1．公开要求

题面标题 “Enum deterministic hashing”。期望行为是示例 `tokenize(Color.RED) == tokenize(Color.RED)` 成立，其中 `Color(Enum)` 的 `RED = 1`、`BLUE = 2`。题面附了一段 “Possible Implementation”：`@normalize_token.register(Enum)`，返回 `type(e).__name__, e.name, e.value`。示例的 import 写成了 `from dask.base import normalize_enum`，实际用的是 `normalize_token`，只是示意。

按题面的一般表述，本页把要求定为两条：

- **R1 确定性**：同一个 Enum 成员多次 `tokenize` 得到同一 token。适用于 Enum 的各种类型：`Enum`、`Flag`、`IntEnum`、`IntFlag` 与混入类型；也适用于各种成员值。
- **R2 区分性**：不同的 Enum 成员得到不同 token。依据是 `tokenize` 的公开用途：base 的 `docs/source/custom-collections.rst` 写明它“generate keys based on the value of arguments”，要求 `__dask_tokenize__` 返回“fully representative of the object”的值，示例还断言“tokens for different objects aren't equal”。

  token 相撞时，按 token 命名的任务会在同一张图里合并，返回错误结果。这类任务包括 pure delayed、Delayed 运算符和 `map_blocks`，本页 §2 有实测。

以下不算核心要求，只登记：
- 跨进程稳定到任意复杂的值，例如值为 `frozenset` 或 `object()`；
- 短名、成员名与值都相同的不同类之间的区分，理由见 §3；
- Enum 子类上自定义的 `__dask_tokenize__` 仍然生效。

题面建议的实现方式是修法提示，不是强制要求：函数名、元组形状、注册位置都不锁定（Codex 09-30 原则 1）。

公开代码中可见的相关事实（base `aa801de0`）：
- `tokenize` 对 `normalize_token` 的结果先取 `str(tuple(...))`，再做 md5；
- `normalize_token` 是按 MRO 查注册表的 `Dispatch`，`int`、`str`、`type` 等注册为 `identity`：
  - 所以 `IntEnum`、`IntFlag`、str 混入的 Enum 在 base 上走 `repr`（如 `<IColor.RED: 1>`），本来就是确定的；
  - 普通 `Enum`／`Flag` 落到 `normalize_object`，返回 `uuid4`；`tokenize.ensure-deterministic=True` 时抛 `RuntimeError`；
- `dask/delayed.py`：pure 调用的 key 是 `funcname-tokenize(func, *args, **kwargs)`；Delayed 的 `==`、`[]` 等运算符固定按 pure 建 key；
- `dask/array/core.py:783`：`map_blocks` 的名字由 `tokenize(func, ..., *args, **kwargs)` 生成。

## 2．实测

### 环境与材料

| 项 | 值 |
| --- | --- |
| 原镜像 | `xingyaoww/sweb.eval.x86_64.dask_s_dask-9212:latest`，RepoDigest `@sha256:1ebd1560…ed60`，与 ingest 冻结摘要一致；image ID `sha256:974b8bd9…d982`，标签 `c3keep/dask9212:src`；镜像内 Python 3.10.14、pytest 8.3.2，自带 numpy 1.26.4、pandas 2.2.2 |
| 派生镜像 | compat_v2b 的云端**等效重建**：`rh2-envrepair/compat-v2b-dask__dask-9212:c3cloud`，ID `sha256:df4c9ec8…a103`。只把两个 wheel 拷进 `/opt/rh2/compat-wheels/`：pandas 1.4.4 `d0022fe6…8e49`、numpy 1.24.4 `7ffe43c7…a4d6`，已与镜像内文件核对。09-19 原版（ID `5b694933…f122`）的 wheel 清单不在仓库里，所以不是逐字节重建 |
| 配方 | [`compat_v2b/recipes/dask__dask-9212.json`](../../../env_recipe_repair_20260919/compat_v2b/recipes/dask__dask-9212.json)：先离线装 pandas 1.4.4、numpy 1.24.4，再 `pip install --no-deps -e .`。原因：`setup.cfg` 把 numpy 警告当错误，而 `cumproduct` 在 numpy 1.25 弃用。每次正式评分的日志都有 `RH2_COMPAT_VERSIONS={"pandas": "1.4.4", "numpy": "1.24.4"}` 与 `RH2_INSTALL_RC=0` |
| 材料 | 题面 `ad94c789…3c0b`；gold `0e1750f4…4d56`；原 test_patch `4039a4bc…323d`，与历史记录一致；grading 摘要 `5b49faf5…173c`；F2P 2 项（`test_tokenize_enum[Enum]`、`[Flag]`），P2P 103 项（含 `[IntEnum]`、`[IntFlag]`）。评分命令 `pytest -n0 -rA --color=no dask/tests/test_base.py`，收集 129 项；跳过 3 项，1 项缺 matplotlib，2 项需 `--runslow`，与 09-19 历史相同 |
| 代码与 grader | 分支 `claude/category3-20260929`，运行期间 HEAD 从 `dd417774` 前进到 `fe43b307`，评分路径未变，与 `a31cdcd` 逐字相同。另有诊断包装 `replay_with_install_recipe.py`，由 09-29 快照 `287bc09` 加入。grader `swebench-4.1.0+swegym_parsers@242429c1`，profile 摘要 `3ec1bfa8…`。`scripts_digest` 为 `f3555584…`，09-19 历史为 `db692fb6…`，原因未查；本批其它题也有同样差异 |
| Docker | 29.3.1、overlay2、cgroup v1 |

### 候选

全部位于 [`rh2/experiments/category3_cloud_20260929/dask9212/candidates/`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask9212/candidates/)，由 `make_candidates.py` 从 base 源码文本替换生成。

| 候选 | sha256 前缀 | 做法 | 按公开要求判断 |
| --- | --- | --- | --- |
| gold | `0e1750f4` | 注册 Enum，返回 `(类短名, name, value)` | 正确；同短名、同成员、同值的不同类相撞（T3） |
| `alt_modqual` | `87e1b0da` | 注册 Enum，返回 `("enum", 模块名, 限定名, name, value)` | 合理实现 |
| `alt_hookfirst` | `cb6bd0f7` | 不注册；在 `normalize_object` 的 `__dask_tokenize__` 检查之后处理 Enum，保留钩子优先 | 合理实现 |
| `alt_up2024` | `1a2d05d7` | 仿上游 2024.2.0：`("enum", (短名, 模块名), name, normalize_token(value))` | 合理实现；值为 `frozenset`、`object()` 时同一进程内也不确定（T3） |
| `alt_pickle` | `1a37a180` | 仿上游 2025：pickle 按引用，局部类改用 cloudpickle | 合理实现；两个值都是无状态 `object()` 的成员相撞（T3） |
| `alt_docs` | `934c0f90` | 照文档示例写法，返回 `(type(e), name, value)` | 合理实现；类对象的 `repr` 是 `<enum 'Color'>`，与 gold 一样只有短名 |
| `w_value` | `232adeb9` | 只返回 value | 错误：不同类的同值成员相撞，也与整数 `1` 相撞 |
| `w_noval` | `2d50c1ce` | 返回 `(类短名, name)`，丢掉 value | 错误：Python 3.10 下 Flag 组合值的 name 都是 `None`，全部相撞 |
| `w_hash` | `09fc456b` | 返回 `hash(e)`，即 `hash(name)` | 错误：不同类的同名成员相撞，Flag 组合值相撞，跨进程不稳定 |
| `w_name` | `c0fd5b70` | 只返回 name | 错误：不同类的同名成员、与字符串 `"RED"`、Flag 组合值都相撞 |
| `w_const` | `31561a80` | 固定返回 `"enum"`，用作 §4 第 3 步的退化探测 | 错误：所有成员相撞 |
| `w_str` | `8fe50d50` | 返回 `str(e)`，形如 `"Color.RED"` | 边界：只与字符串 `"Color.RED"` 相撞，另有与 gold 相同的同名碰撞；不违反核心要求，见 §3 |

题目机制下适用的错误写法类别：
- “只覆盖数据形态子集”：`w_noval` 只对单成员有效；
- “只处理示例”：`w_value`、`w_name`、`w_hash` 只在题面示例的同一个类内有效；
- “固定结果”：`w_const`。

“吞掉错误”“依赖顺序”“阈值”几类在本题没有对应机制：token 是纯计算，没有异常可吞，也没有顺序或规模分支。

### （1）私有行为对照

在断网、root 的一次性容器里运行 [`behavior.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask9212/behavior.py)，经 `semantic_control.py` 调用。镜像用派生镜像，并先按配方离线装好 pins。按公开要求判对错，不以 gold 为答案。

全表见 `evidence/semantic_v1/table.txt`，共 73 个用例 × 13 个变体（另有 1 行环境记录）。

**决定性对照：不同模块、同名同值的 `Color.RED`。** `audit_a`、`audit_b` 是容器内写出的两个真实模块，函数放在第三个模块里，所以函数本身的 token 是确定的。

| 路径 | base | gold |
| --- | --- | --- |
| `tokenize(A.Color.RED) == tokenize(B.Color.RED)` | 否。同一成员两次也不相等（随机） | **是**，二者都规范成 `('Color', 'RED', 1)` |
| `delayed(which, pure=True)`，其中 `which` 返回 `type(e).__module__`：两个 key | 不同 | **相同**：`which-b89de8d9…` |
| 同一张图 `dask.compute(a, b)`，sync 与 threads 调度器都试过 | `audit_a, audit_b` | **`audit_a, audit_a`** |
| 两个任务分开 `compute` | 正确 | 正确 |
| pure delayed 调用成员方法 `e.describe()`，两类返回值不同 | 正确 | **`audit_a, audit_a`** |
| 默认 impure delayed | 正确 | 正确（key 随机） |
| Delayed `v == A.Color.RED`、`v == B.Color.RED`（运算符总是 pure） | `True, False` | **`True, True`** |
| Delayed 字典 `d[A.Color.RED]`、`d[B.Color.RED]` | 正确 | **两次 `from audit_a`** |
| `x.map_blocks(f, color=A/B.Color.RED)` | 名字不同，`x1 - x2 = [-100]*4` | **名字相同，`x1 - x2 = [0]*4`** |
| 同名 `Flag` 成员 `Perm.R` | 正确 | **错** |
| 两个类都自带 `__dask_tokenize__`（返回模块名与限定名） | 正确：钩子生效 | **错**：钩子被 gold 的 Enum 注册遮蔽 |
| 同名 `IntEnum` 成员（gold 不改变这条路径） | **已经错**：`<IColor.RED: 1>` 相撞 | 同 base |
| Enum 类对象本身 `tokenize(A.Color) == tokenize(B.Color)` | **已经相等**：`<enum 'Color'>` | 同 base |
| 同一模块内的嵌套类 `Reader.Mode.FAST`、`Writer.Mode.FAST` | 不相撞（随机） | 相撞 |
| 同一函数两次创建的局部类，与测试写法相同 | 不相撞（随机） | 相撞 |

其它候选在同名碰撞上的表现：
- `alt_modqual`、`alt_hookfirst`、`alt_up2024`、`alt_pickle` 区分不同模块，上表各行全部正确。其中 `alt_up2024` 不含限定名，嵌套类仍会相撞；
- 局部类只有 `alt_pickle` 能区分；任何基于名字的确定性写法都区分不了同一函数两次创建的类；
- `alt_docs`、`w_str` 与 gold 相同；
- 各错误候选同样相撞。

**核心要求与非示例实例**（Y＝符合公开要求，N＝违反）：

| 检查 | base | gold | 5 个合理实现 | `w_value` | `w_noval` | `w_hash` | `w_name` | `w_const` | `w_str` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1：同一成员稳定。覆盖 Enum、Flag、IntEnum、IntFlag、str 混入，值为 int、tuple、dict | N（Enum/Flag 随机） | Y | Y | Y | Y | Y | Y | Y | Y |
| R1：严格模式 `ensure-deterministic=True` 下不报错 | N（抛 `RuntimeError`） | Y | Y；`alt_up2024` 在值为 `frozenset`、`object()` 时抛错 | Y | Y | Y | Y | Y | Y |
| R2：同一个类的不同成员 | Y | Y | Y；`alt_pickle` 在两个 `object()` 值上 N | Y | Y | Y | Y | **N** | Y |
| R2：不同类、同名同值（`Color.RED`～`Light.RED`） | Y | Y | Y | **N** | Y | **N** | **N** | **N** | Y |
| R2：不同类、同值（`Color.RED`～`Shape.CIRCLE`） | Y | Y | Y | **N** | Y | Y | Y | **N** | Y |
| R2：与原始值 `1`／`"RED"`／`"Color.RED"` | Y | Y | Y | **N**（`1`） | Y | Y | **N**（`"RED"`） | Y | N（`"Color.RED"`，边缘） |
| R2：Flag 组合值（`R\|W`～`R\|X`、`R\|W`～`Perm(0)`） | Y | Y | Y | Y | **N** | **N** | **N** | **N** | Y |
| 后果：pure delayed 同图计算 `type_name(Color.RED, Light.RED)` | Color, Light | 同左 | 同左 | **Color, Color** | 正确 | **Color, Color** | **Color, Color** | **Color, Color** | 正确 |
| 后果：`type_name(Color.RED, 1)` | Color, int | 同左 | 同左 | **Color, Color** | 正确 | 正确 | 正确 | 正确 | 正确 |
| 后果：`value_of(R\|W, R\|X)` | 3, 5 | 同左 | 同左 | 正确 | **3, 3** | **3, 3** | **3, 3** | **3, 3** | 正确 |
| 跨进程（`PYTHONHASHSEED` 1 与 2）：值为 int、tuple、dict 的普通 Enum，Flag 组合值 | N | Y | Y | Y | Y | **N** | Y | Y | Y |
| 跨进程，`frozenset` 或 `object()` 值 | N | N | N；`alt_pickle` 在 `object()` 上 Y | N | Y | N | Y | Y | Y |
| 用户自定义 `__dask_tokenize__` 是否生效 | 是 | 否 | 仅 `alt_hookfirst` 是 | 否 | 否 | 否 | 否 | 否 | 否 |
| 用户 `normalize_token.register(MyEnum)` 优先 | Y | Y | Y | Y | Y | Y | Y | Y | Y |

表中“R2”各行只看 token 是否不同；“后果”各行是同一个 pure delayed 函数、两个参数进同一张图后的实际返回值。`IntEnum`、`IntFlag`、str 混入走 base 已有的 `int`／`str` 注册，在所有变体下结果相同（跨进程也稳定）。

**私有模拟评分（应用原 test_patch 后跑整份 `test_base.py`）：**
- base：两个 F2P 失败，都在第 435 行的第一条断言；
- gold、5 个合理实现、`w_value`、`w_noval`、`w_hash`、`w_name`、`w_str`：126 passed，3 skipped；
- `w_const`：两个 F2P 失败，在第 436 行（`RED != BLUE`）。

### （2）原材料正式评分

`replay_with_install_recipe.py --recipe compat_v2b … run --derived-image sha256:df4c9ec8…`。所有行的参考缺席都是 0，安装 rc 0，补丁已应用，清理成功。

| 候选 | reward | F2P | P2P 失败 | 说明 |
| --- | --- | --- | --- | --- |
| noop | 0 | 0/2 | 0/103 | `[Enum]`、`[Flag]` 在第 435 行失败；2 failed、124 passed、3 skipped，与 09-19 历史一致 |
| gold | 1 | 2/2 | 0/103 | 126 passed、3 skipped，与历史一致 |
| `alt_modqual` | 1 | 2/2 | 0/103 | 没有误拒 |
| `w_value` | **1** | 2/2 | 0/103 | 错误实现得满分 |
| `w_noval` | **1** | 2/2 | 0/103 | 错误实现得满分 |
| `w_const` | 0 | 0/2 | 0/103 | 第 436 行被拒：§4 第 3 步没有命中 |

`alt_hookfirst`、`alt_up2024`、`alt_pickle`、`alt_docs`、`w_hash`、`w_name`、`w_str` 在原材料上只做了私有模拟，都是 1。

### 上游对照（只作佐证，不作公开依据）

来源是 raw.githubusercontent.com 上的 dask 源码，只读未运行，摘录与摘要见 `evidence/upstream/upstream_excerpts.txt`。

- 2022.7.0 至 2023.12.1：与 gold 相同；
- 2024.2.0：改为 `_normalize_seq_func((type(e), e.name, e.value))`，其中 `normalize_type` 返回 `(typ.__name__, typ.__module__)`，即纳入了模块名，但仍不含限定名；值也做递归规范化，与 `alt_up2024` 相同；
- 2025.9.1：删除了 Enum 的专用注册，改走 `normalize_object`：先调用 `__dask_tokenize__`，再 pickle。

可见上游后来区分了模块（2024.2.0，随作用于所有类型的 `normalize_type` 一起出现，本页未追查起因），更晚的版本还恢复了钩子优先。这支持“短名碰撞是真实缺陷”；上游保留 gold 写法约一年半，也说明它当时没有被当作必须立即修的问题。

## 3．判定（v1 §3–§4）

| 步 | 结果 | 依据 |
| --- | --- | --- |
| 1 核心要求有无直接断言 | 有 | R1：四类 Enum 各有 `RED == RED`；R2：各有同一个类内 `RED != BLUE` |
| 2 是否只用题面示例的字面值 | **部分是（T2c）** | R1 在四类 Enum 上检查，超出了示例；R2 只在题面示例的同一个 `Color` 类内检查，没有第二个类，也没有 Flag 组合值 |
| 3 退化探测 | 未命中 | 固定 token 的 `w_const` 正式评分 0，被原有的 `RED != BLUE` 拒绝 |
| 4 已有得 1 的候选是否在同一核心要求的其它实例上违例 | **是 → S1** | `w_value`、`w_noval` 正式得 1，`w_hash`、`w_name` 私有得 1。它们违反 R2 的实例都不边缘：<br>① 另一个 Enum 类的成员是“Enum types”最基本的非示例实例；按 `auto()` 或从 1 编号时，两个类有同值成员几乎是常态。`w_value` 还让 Enum 成员与整数 `1` 共用 key。<br>② Flag 组合值是 Flag 的主要用法，而测试本身把 `Flag` 列为 F2P。<br>同图计算的错误结果见 §2（1） |
| 4（gold） | **S2（T3），登记** | G1：同名碰撞造成真实的错误结果，但只出现在边缘输入上，理由见下 |

**同名碰撞为什么是 S2（T3）而不是 S1。**
- 触发条件苛刻，要同时满足：
  - 两个不同的类短名相同、成员名相同、值相同；
  - 两者被同一个函数（其余参数也相同）放进同一张图；
  - 函数结果依赖类身份，例如模块名、类方法或 `isinstance`。

  通用函数（`str`、`repr`、`.name`、`.value`）对这两个成员的结果本来就相同，合并无害。例如 `str(e)` 是 `"Color.RED"`，只含短名。
- 题面本身建议的就是短名表示。以它为理由判 gold 错，等于拒绝题面的建议。
- dask 在 base 上已经按短名处理 `IntEnum` 成员和 Enum 类对象，二者同样相撞（§2 实测）；按文档示例写法 `alt_docs` 也一样。gold 只是让普通 Enum 与已有行为一致。
- 与 `w_value` 的区别在于碰撞面：`w_value` 让所有同值成员与原始值相撞，gold 只让类短名、成员名、值三者都相同的类相撞。

**其它登记项（T3，不写成断言）：**
- **钩子遮蔽**：Enum 子类自己定义的 `__dask_tokenize__` 在 gold 下不再被调用，base 上会调用。实测会让用户用钩子区分开的同名类重新相撞。
  - 这与文档所述的分派规则一致：父类已注册时，应改用 `normalize_token.register`。实测 `register` 仍然优先。
  - Enum 上自带钩子的写法少见；`alt_hookfirst` 证明保留钩子的写法也能通过测试。
- **复杂值的跨进程稳定**：gold 用 `repr(value)`，值为 `frozenset` 或 `object()` 时跨进程不稳定，同一进程内稳定；实测 int、tuple、dict 值与 Flag 组合值跨进程稳定。
- **局部类**：同一函数两次创建的同名局部类，任何基于名字的确定性实现都会相撞。

**其它类别：**

| 类别 | 结论 |
| --- | --- |
| T1 | 无。`alt_modqual` 正式得 1；另外 4 个写法不同的合理实现私有得 1。测试不锁函数名、元组形状或注册位置 |
| P5 | 不适用。测试没有只接受一种读法：短名写法（gold、`alt_docs`）与带模块名的写法（`alt_modqual` 等）都得 1，修订后也是如此 |
| 题面带修法（P1 相关） | 题面的 “Possible Implementation” 与 gold 核心函数逐字相同（gold 另加 `from enum import Enum`）。按 numpy__18b7cd9d、dask-7656 的现行做法，记为**难度属性**（易题，修法已给出），在用途中注明，不要求 R-f。若下游需要无提示版本，可按 R-f 删去这一段：剩下的题面示例在 base 上确实复现（私有矩阵 `stable:Enum_int` 为 N）。这是用途取舍，不阻塞 |
| E1 | compat_v2b 配方（pins）已按等效重建复验：noop、gold 与 09-19 历史逐项一致 |
| X1 | 旧记录报告与 dask-8792 同仓关联（8792 的修复在本题 base 中），本次未核，只影响留出划分 |
| w_str（边界候选） | 修订后仍得 1。它只与内容恰为 `"Color.RED"` 的字符串参数相撞，另有与 gold 相同的同名碰撞；在 R1、R2 的全部核心实例上都正确（不同成员、不同类、Flag 组合值、原始值 `1` 与 `"RED"`）。与 gold 的同名碰撞同属边缘输入，不违反公开要求，所以不为它补断言 |

## 4．修法（交第2类）：R-c 修订 v1

**草案**：[`revised_test_v1.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask9212/revised_test_v1.patch)，sha256 `af2e68cf…7b36`，由 `make_revised_test.py` 生成。生成时做了自检：base 加 ingest 原 test_patch 与重建的原版逐字相同，base 加修订补丁与修订版逐字相同。材料 JSON 为 [`materials_revised_v1.json`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask9212/materials_revised_v1.json)，版本 `c3-dask9212-enum-distinct-v1`；修订后的 grading 摘要为 `3abaea77…6316`，原为 `5b49faf5…173c`。

只改 `test_tokenize_enum` 的函数体，保留原有 4 行断言，在其后追加：

```python
    # Members of another Enum class are different values, even when they have
    # the same member name and value.
    class Light(enum_type):
        RED = 1
        BLUE = 2

    assert tokenize(Light.RED) == tokenize(Light.RED)
    assert tokenize(Color.RED) != tokenize(Light.RED)          # 第 445 行

    if issubclass(enum_type, Flag):
        # Combined flags are values of the Flag class too.
        assert tokenize(Color.RED | Color.BLUE) == tokenize(Color.BLUE | Color.RED)
        assert tokenize(Color.RED | Color.BLUE) != tokenize(Color(0))   # 第 450 行
```

两处修改各对应一个窄问题：
- **不同类的区分**：依据是 R2（§1 所引文档）；题面建议的实现也把类纳入了 token。补一个类名不同、成员与值都相同的类，只断言“不等”，不锁定任何表示；
- **Flag 组合值**：依据同是 R1、R2。组合值是 Flag 类的值，而 Flag 已在测试范围内。

不断言同名不同模块的区分，理由见 §3。测试 ID、参数化、评分命令都不变。F2P／P2P 分组也不变：base 上 `[IntEnum]`、`[IntFlag]` 仍通过新断言（走 `repr`），`[Enum]`、`[Flag]` 仍在第 435 行失败。

**私有模拟**（`semantic_v2`，应用修订补丁后跑整份 `test_base.py`）与下表的正式诊断评分逐项一致。

**正式诊断评分（`--materials`＋compat_v2b 配方，13 次）**：grader 后缀 `+c3-dask9212-enum-distinct-v1`，`scripts_digest` 为 `50ecceca…`。13 次全部参考缺席 0、安装 rc 0、清理成功。逐次失败位置见 `evidence/formal_revised_v1/failure_reasons.txt`。

| 候选 | 性质 | 原材料 | **修订 v1** | 修订版失败位置 |
| --- | --- | --- | --- | --- |
| noop | — | 0 | **0** | 435：第一条断言 |
| gold | 正对照 | 1 | **1** | — |
| `alt_modqual`、`alt_hookfirst`、`alt_up2024`、`alt_pickle`、`alt_docs` | 合理实现 | 1／私有 1 | **1** | — |
| `w_value` | 错误 | **1** | **0** | 445（`Color.RED` 与 `Light.RED` 相撞） |
| `w_noval` | 错误 | **1** | **0** | `[Flag]` 在 450（组合值相撞）；F2P 1/2 |
| `w_hash`、`w_name` | 错误 | 私有 1 | **0** | 445 |
| `w_const` | 退化 | 0 | **0** | 436（原有的 `RED != BLUE`） |
| `w_str` | 边界 | 私有 1 | 1 | —（预期，§3） |

**v1 验收（v1 §5）：**

| 验收项 | 结果 |
| --- | --- |
| 正对照为 1，noop 为 0 | 满足：gold 为 1，noop 为 0 |
| 要纠正的误判已纠正 | 满足：`w_value`、`w_noval` 由 1 变为 0 |
| 已知相关错误候选为 0 | 满足：`w_value`、`w_noval`、`w_hash`、`w_name`、`w_const` 全为 0 |
| 没有新增误拒 | 满足：5 个写法不同的合理实现（含两个上游式）全为 1 |
| 修订后仍受保护的公开要求 | R1：四类 Enum 与 Flag 组合值；R2：同一类内、不同类之间、Flag 组合值之间；另有 103 项 P2P |
| 正对照 | gold 通过全部新断言，不需要替代正对照。5 个合理实现只用来证明没有误拒，由本主审编写，**待他人核实** |
| 独立复核、Codex 复核 | 未做 |

**R-f**：不需要。新增断言都能从题面“deterministic hashing for Enum types”与公开文档的 token 语义推出，不引入隐藏细节。题面修法提示的处理见 §3。

### 交接给第2类

1. **测试**：以 v1（`af2e68cf…`）替换原 test_patch。测试 ID 与 F2P／P2P 分组不变，不需要调整参考分组或 `statement_replace`。
   - 所需的 D6“测试补丁替换”已获总体授权，但尚未实现。D6 已验收的首片只有 `append_mypy_p2p`；
   - 本页的 `--materials` 诊断评分不等于正式 actor 已消费修订版。
2. **正对照**：gold，不变。
3. **复验**：v1 下 noop 0；gold 与 5 个合理实现 1；`w_value`、`w_noval`、`w_hash`、`w_name`、`w_const` 为 0；`w_str` 为 1，这是预期结果，理由见 §3。
4. **环境**：compat_v2b 派生镜像是云端等效重建，入库时应固定 wheel 清单与摘要（§2 环境表）。
5. **登记项（T3，不写成断言）**：
   - 同名不同模块的碰撞，附 §2 的具体后果；
   - 钩子遮蔽；
   - 复杂值跨进程不稳定；
   - 局部类相撞。

   训练中按 v1 §8 抽查：真实补丁照题面写成短名，属于已登记缺口，不判错。**不要**为同名碰撞补断言：那会拒绝题面建议与 gold，属于改变任务目标，需用户决定，本页不建议。
6. **用途说明**：题面给出完整修法，按难度属性标注。是否另做无提示的 R-f 版本属于用途取舍，不阻塞。
7. **复核**：独立复核（v1 §7.3）与 Codex 复核。

## 5．当前用途（v1 §2，D6 落地前）

| 版本 | 问题定位 | 能力比较 | 训练候选 | 留出评测 |
| --- | --- | --- | --- | --- |
| 原版 | 是 | 否（S1 未处理：两个错误实现正式得 1） | 否 | 否 |
| 修订版 v1（草案） | 是 | conditional：D6 落地并复验，另需独立复核 | conditional：同左；另注明题面给出完整修法（易题） | 否（修订题只能作标明版本的自建题；另有 X1 待核） |

## 6．未做与剩余事项

- 独立复核、Codex 复核：未做。
- 5 个合理实现只由本主审核对，作用是证明没有误拒，不是替代正对照（gold 已通过），**待他人核实**。
- 原材料正式评分只跑了 noop、gold、`alt_modqual`、`w_value`、`w_noval`、`w_const`。其余 7 个候选在原材料上只有私有模拟（都是 1）；修订版上 13 个全部做了正式诊断评分。
- 跨进程只在同一容器内比较了 `PYTHONHASHSEED` 1 与 2，未跨机器，也未跨 Python 版本。
- Python 3.11 及以后，Flag 组合值有名字（如 `RED|BLUE`），`w_noval` 在那些版本上不再算错。修订测试按本镜像的 Python 3.10.14 验证，gold 在新版本上仍满足新断言（按语义推断，未运行）。
- `dask.distributed` 与多进程调度器下的合并行为：未查。本地 sync、threads 调度器已查。
- 真实 actor 的开发条件：未验，没有模型求解证据。
- R-f 无提示版本：未起草。
- X1（与 dask-8792 的关联）：未核。

## 7．版本与证据

- 实验文件：[`rh2/experiments/category3_cloud_20260929/dask9212/`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask9212/)
  - `make_candidates.py`、`candidates/*.patch`；
  - `behavior.py`（私有矩阵）、`make_spec.py`、`run_semantic.sh`、`summarize_behavior.py`；
  - `original_test.patch`，即 ingest 原 test_patch 的副本；
  - `make_revised_test.py`、`revised_test_v1.patch`、`materials_revised_v1.json`；
  - `run_formal.sh`，有 `orig`、`rev1` 两种模式。失败位置由上级目录的 `failure_reasons.py` 汇总。
- 原始证据：[evidence/](evidence/)
  - `semantic_v1/`：私有矩阵与原测试私有模拟，`table.txt` 为汇总表；
  - `semantic_v2/`：修订测试私有模拟；
  - `formal/`：原材料正式评分 6 次；
  - `formal_revised_v1/`：修订版诊断评分 13 次；
  - 两个评分目录各有 `failure_reasons.txt`；
  - `derived/`：派生镜像的 `image.json`、构建日志与镜像内 wheel 摘要。wheel 本身未归档，摘要已登记；
  - `upstream/`：上游对照摘录；
  - `base_src_sha256.txt`：base 源码副本的摘要，副本可从镜像重新导出；
  - 全部文件的 SHA256 见 `evidence_manifest.json`。
- 旧材料：[旧题卡](../../../swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-9212/card.md)、[封存分析](../../../swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-9212/analysis_before_history.md)、[独立复核](../../../swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-9212/review.md)。旧材料对 I1（同名碰撞）只有静态推断，本页给出了运行结果与定性；I2（复杂值）、I3（钩子）也已实测，见 §2、§3。
- 环境：见[环境说明](../../environment.md)。
