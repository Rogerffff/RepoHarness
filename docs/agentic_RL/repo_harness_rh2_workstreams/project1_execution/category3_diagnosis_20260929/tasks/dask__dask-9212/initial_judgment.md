# dask__dask-9212 读历史前的初判（封存，写完不再改）

2026-09-30 / Claude（第3类第二批主审子代理）。只依据原件：`s2/ingest/` 的题面、gold、test_patch、F2P／P2P 名单，以及在一次性断网容器（`c3keep/dask9212:src`，`/testbed` 在 `aa801de0f`，Python 3.10.14）里读到的 base 代码与 base 文档。此时尚未打开旧题卡、复核或状态说明，也没有跑任何实验。

## 1．公开要求

题面标题 “Enum deterministic hashing”，期望行为是示例 `tokenize(Color.RED) == tokenize(Color.RED)` 成立（`Color(Enum)`，`RED = 1`、`BLUE = 2`）。题面附“Possible Implementation”：`normalize_token.register(Enum)`，返回 `type(e).__name__, e.name, e.value`。这只是修法提示，不是强制要求。

按一般表述理解，我读出两条要求：

- **R1 确定性**：同一个 Enum 成员多次 `tokenize` 得到同一 token；按 dask 的用法，最好跨进程也稳定（token 用作任务 key）。
- **R2 区分性**（隐含）：不同的 Enum 成员应得到不同 token。依据：`tokenize` 是“基于参数值生成 key”的哈希（base 的 `docs/source/custom-collections.rst` “Implementing Deterministic Hashing”）；文档要求 `__dask_tokenize__` 返回“fully representative of the object”的值，并在示例里写明 “tokens for different objects aren't equal”。如果 token 把不同成员混为一个，`delayed(pure=True)`、`map_blocks` 这类按 token 命名的任务会被合并，返回错误结果。

## 2．测试与要求的对应

`test_tokenize_enum` 按 `Enum`、`IntEnum`、`IntFlag`、`Flag` 参数化，每个参数都在函数内定义局部类 `Color`（`RED = 1`、`BLUE = 2`），断言：

- `tokenize(Color.RED) == tokenize(Color.RED)` → R1，只在同一进程内；
- `tokenize(Color.RED) != tokenize(Color.BLUE)` → R2，只在同一个类的两个单成员之间。

F2P 是 `[Enum]`、`[Flag]`；`[IntEnum]`、`[IntFlag]` 在 P2P。原因：`Dispatch.dispatch` 沿 MRO 查找，`IntEnum`／`IntFlag` 先遇到已注册为 `identity` 的 `int`，`tokenize` 再对 `str(tuple(...))` 取 md5，实际用的是 `repr`（`<Color.RED: 1>`），base 上已经确定。普通 `Enum`／`Flag` 落到 `normalize_object`：没有 `__dask_tokenize__`、不可调用、不是 dataclass，于是返回 `uuid4`（`tokenize.ensure-deterministic` 为 True 时抛 `RuntimeError`）。

测试没有覆盖：不同类之间的区分、Flag 组合值（Python 3.10 下组合成员的 `name` 是 `None`）、跨进程稳定、非 int 值或复杂值、`ensure-deterministic=True`、Enum 子类自带的 `__dask_tokenize__`。

## 3．gold 的机制与疑点

gold 在 `normalize_object` 之前注册 `Enum`，返回 `(type(e).__name__, e.name, e.value)`：

1. **只取类短名**：两个不同的类，只要短名、成员名和值都相同，token 就相同。例如不同模块里的同名类、同一模块里不同外层类下的同名嵌套类、函数内的局部类。base 上这类成员的 token 是随机的，不会相撞。所以对 pure delayed 或 `map_blocks` 来说，这可能是用户可见的回归：两个任务 key 相同、在图里合并，返回同一个值。不过，base 上 `IntEnum` 走 `repr`，本来就只带短名；文档示例式写法 `(type(e), ...)` 经 `repr` 后也只剩 `<enum 'Color'>`；题面建议的也正是短名。所以我**预计这是 T3／S2（边缘输入的已知缺口）**，不是 S1。要用实验确认后果并收窄范围。
2. **值不经 `normalize_token`**：`e.value` 直接进 `str(tuple)`，用的是 `repr`。值是 `object()`、字符串集合等时，同一进程内稳定，跨进程可能变化。成员名已经区分了单成员，值主要影响组合 Flag；预计属于 T3。
3. **遮蔽 `__dask_tokenize__`**：Enum 子类若自己定义了 `__dask_tokenize__`，base 会走 `normalize_object` 调用它；gold 注册 `Enum` 之后，这个方法不再被调用。这与文档说的“父类已注册就改用 `normalize_token.register`”一致，预计 T3／S2，需实测。
4. `IntEnum`、`IntFlag` 与 str／float 混入的 Enum 仍然先命中 `int`／`str` 等内置类型的注册，gold 不改变它们的行为。

## 4．可能被原测试放过的错误候选（按机制选）

- `c_value`：只返回 `e.value`。同值的不同类成员相撞（`auto()` 从 1 开始，很常见），还会与原始值 `1` 相撞。测试只比同一类，预计得 1。
- `c_noval`：返回 `(type(e).__name__, e.name)`。Python 3.10 下所有 Flag 组合值的 `name` 都是 `None`，全部相撞。测试只比单成员，预计得 1。
- `c_name`／`hash(e)`：Enum 的 `__hash__` 就是 `hash(name)`，只按成员名区分，跨类相撞；`hash` 还跨进程不稳定。预计得 1。
- 合理但与 gold 不同的实现（查 T1）：`c_modqual`，把 `type(e).__module__`、`__qualname__` 纳入 token。预计得 1。

## 5．初步处置与会改变结论的实验

初步倾向是**转第2类**。修法用 R-c：在同一个参数化测试里补“不同类名、同成员名同值”与“Flag 组合值”两类非示例实例。gold 应能通过，可以继续作正对照。gold 的同名碰撞登记为 T3／S2，不写成断言，否则会拒绝题面自己建议的写法和 gold。

会改变结论的实验：

- (a) 同名不同模块的 `Color.RED`：在 base 与 gold 下比较 token、pure delayed key 与一起 compute 的结果。如果后果超出边缘输入，要重新定性，并考虑替代正对照（D4）。
- (b) 上面几个错误候选在原测试上是否真的得 1。如果都得 0，可能改为申请转第1类。
- (c) `c_modqual` 在原测试上是否得 1（查 T1）。
