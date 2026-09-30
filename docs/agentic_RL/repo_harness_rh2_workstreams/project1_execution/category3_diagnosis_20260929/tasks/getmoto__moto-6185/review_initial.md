# getmoto__moto-6185 独立复核：初判（读作者材料前封存）

2026-09-30，独立复核者（Claude 子代理，不继承作者上下文）。本稿写于读作者 `result.md`、`evidence/` 与 `rh2/experiments/category3_cloud_20260929/moto6185/` 任何文件之前，写完不再修改。

## 本稿读过、跑过什么

- 规则：统一标准 v1 §3、§4、§5、§7.3、§9 D4；`review-standards.md`；本目录 README 的两段校准、`environment.md`；写法参照 conan-13403、pydantic-8567 的初判与复核。
- 原件：`s2/ingest/` 四个 bundle 中本题的题面、gold（sha256 `868fd2d1…79e1`）、test_patch、F2P 1 项、P2P 34 项、`eval_cmd`（`pytest -n0 -rA`）。
- 镜像 `c3keep/moto6185:src`（RepoDigest `…getmoto_s_moto-6185@sha256:ade7d85a…6eda`，与冻结值一致），一次性容器、`--network none`、root。读了 base 的 `moto/dynamodb/models/table.py`（`_validate_item_types`、`put_item`）、`dynamo_type.py`（`DynamoType`、`size`）、`responses.py`（`put_item`、`batch_write_item`、前置校验）、`models/__init__.py`（`transact_write_items`、`update_item` 新建条目）、原测试文件，以及 git 历史中引入该校验的提交 `37845792d`（#5654）。
- 我自己的小探针（`probe0.py`，base 与 gold 各跑一次），以及 PyPI 上 moto 4.1.5、4.2.14、5.0.28、5.2.3 wheel 中的 `_validate_item_types`。
- **如实说明**：派发说明里已写明作者的几条主张（原版 S1：T2a 嵌套 `S` 无断言，T2b `swallow`、`skip_s_subtree` 得 1；无 T1；gold 两处缺口判 T3；修订 v2、v2s；`ctx`、`parity` 作正对照），我在 `ls` 时也看到本题目录下有 `result.md` 与 `evidence/`。这些文件的内容我没有读，实验目录我没有列出。

## (a) 根因与公开核心要求

**根因**（源码直接可见）：`_validate_item_types` 递归遍历整个条目字典，但不区分“属性名”和“类型标签”。只要某层字典里出现键 `"S"` 且值是 dict，就抛 `SerializationException("Start of structure or map found where not expected")`。属性名恰好是 `S` 时，它的值是带类型的 dict，于是被误判。列表（`L`）不递归，所以列表里的 `S` 属性在 base 上本来就不报错。

**核心要求**（按题面一般表述）：条目中任何位置的属性名为 `S` 时，`put_item` 都不能因此报 `SerializationException`。
- “任何位置”包括顶层（例 1 `{'index': 0, 'S': None}`）、map 内（例 2 `{'index': 0, 'A': {'S': None}}`）和多层嵌套（题面原文 “It could be deeply nested”）；
- 属性值可以是任意类型：例子用的是 NULL，测试用的是 S；
- 表的 key schema 任意；
- 写条目的入口 `batch_write_item` 的 PutRequest 和 `transact_write_items` 的 Put 都走同一个 `Table.put_item`，自然一并覆盖。

**应保留的公开旧行为**（关闭 botocore 参数校验时的服务端校验，依据是 base 代码注释 “This scenario is usually caught by boto3, but the user can disable parameter validation. Which is why we need to catch it 'server-side' as well”、提交 #5654 与公开测试）：
1. S 类型值为 int 时报 `NUMBER_VALUE cannot be converted to String`（原 F2P 函数，key 属性）；
2. S 类型值为 dict 时报 `Start of structure or map found where not expected`：原测试只测了 key 属性，**base 对所有属性、所有层都这样做**；
3. N 类型值为 int 时报同一文案。公开 P2P `test_put_item_wrong_datatype` 专门测了“non-key, and nested”。这说明服务端类型校验本来就覆盖非 key 属性和嵌套层。

## (b) 参考测试断言了什么

F2P 只有 `test_put_item__string_as_integer_value` 一项。整函数使用 `parameter_validation=False` 的低层 client，表 `without_sk` 只有 hash key `pk`（S）。

| 断言 | 性质 |
| --- | --- |
| `{"pk": {"S": 123}}` 报 SerializationException，精确文案 | 旧行为，base 已有 |
| `{"pk": {"S": {"S": "asdf"}}}` 报 SerializationException，精确文案 | 旧行为，只测 key 属性 |
| **新增**：`{"pk": {"S": "val"}, "S": {"S": "asdf"}}` 能写入，`get_item` 原样取回 | 核心要求，但**只测顶层**、只测 S 类型值、只测 `pk` 在前的属性顺序 |

没有断言的：嵌套 `S`（题面例 2）、多层嵌套、例 1 的 NULL 值、resource 入口、batch／transact 入口、非 key 的 S→dict 报错、`S` 在前的属性顺序、列表内的 `S`。

P2P 34 项都在同一文件，其中与本题相关的是 `test_put_item_wrong_datatype`（N→int，含非 key 嵌套）、`test_put_item_wrong_attribute_type`、`test_put_item_empty_set`、`test_batch_put_item_with_empty_value`。

## (c) 预测：会被放过的错误候选、会被误拒的合理实现（未运行，待第二步核实）

可能得 1 的错误候选：
1. **只修顶层**：深度 0 的 `S` 跳过检查，其余照旧。F2P 只测顶层，预计得 1，但题面例 2 仍报错。这是同一核心要求的明示实例，**判 S1 的主要依据**（§4 第 1 步；也可看作第 2 步，因为测试只用了例 1 的形态）。
2. **吞错**：在 `put_item` 里捕获 `SerializationException`，只要 key 属性没问题就放行；或者碰到名为 `S` 的属性就跳过整棵子树。预计得 1。它违反的是上面第 2、3 条旧行为，但只在关闭参数校验、又发送畸形数据时才触发。注意 gold 在“非 key 的 S→dict”上本身也不再报 SerializationException，见 (d)。所以这类候选能否构成 T2b 并单独判 S1，要看它是否在 gold 之外还有更坏的后果（例如把错误数据存进去），或是否影响常用路径。
3. **依赖属性顺序、跨兄弟节点泄漏状态**的写法：测试只有 `pk` 在前一种顺序，可能放过。
4. **只修到固定深度**（如只到两层）：测试没有多层嵌套，可能放过。
5. **给列表加了递归但沿用 base 的朴素判断**：把 base 本来能用的“列表内 `S` 属性”弄坏。测试不涉及列表，可能放过。

预计会被原测试挡住的：
- 删掉 S→dict 检查（被 key 断言挡住）；
- 只放行字面值 NULL（测试用的是 S 类型值）；
- “值长得像类型值就当属性名”的启发式（`{"pk": {"S": {"S": "asdf"}}}` 会被放行，被 key 断言挡住）。

可能被误拒的合理实现：**预计没有**。新增断言是自然的写入加读回；两条报错文案都来自 base 已有的公开测试，合理修法应当保留。**初判无 T1。**

## (d) gold 的缺口（`probe0.py` 实跑）

- 题面例 1、例 2、三层嵌套、列表都正常；key 的 S→dict、非 key 的 S→int 仍报正确错误；属性顺序反过来也正常。
- **缺口 1**：递归时传下去的 `attr` 在嵌套层是类型标签（`M`），而不是属性名。所以表的 key 属性恰好叫 `M` 时，任何 map 里的 `S` 属性仍会报错。我实测了 key 为 `M` 的表加 `{"A": {"M": {"S": {"NULL": true}}}}`，结果是 SerializationException。这属于同一核心要求，但只在 key 名为 `M` 这种罕见 schema 上出现，按 §4 第 4 步是边缘输入，**倾向 T3（S2）**。
- **缺口 2**：非 key 属性的 S→dict（包括名为 `S` 的属性）不再报 SerializationException，而是在 `Item.__init__` 计算大小时抛出内部 `AttributeError: 'dict' object has no attribute 'encode'`。mock 模式下这个异常直接抛给调用者，服务器模式下应是 500。条目**没有写入**，之后 `get_item`、`scan` 都为空。这是 base 公开旧行为的回归，但只在关闭参数校验、又发送畸形值时出现，而且请求仍然失败、没有存入错误数据。**倾向 T3（S2），不作 S1 依据。**
- **上游佐证**（只作佐证，不是公开依据）：moto 4.1.5 仍是 base 写法；4.2.14、5.0.28、5.2.3（当前最新）都保留 gold 的“只对 key 属性检查 S→dict”写法，两处缺口一直没有修。

## (e) 初判处置

- 原版：**S1**。依据是 §4 第 1 步（题面明示的嵌套实例没有直接断言；“只修顶层”预计得 1），也可以落在第 2 步。第 3 步是否另外命中，要看吞错类候选的实际后果，见 (c) 第 2 条。**无 T1**。
- P4 登记：题面原例原样运行时，在该镜像上先报 `NoRegionError`，因为没有默认 region。设 `AWS_DEFAULT_REGION=us-east-1` 后复现 SerializationException。
- **修订方向（R-c）**：
  - 补例 2 形态的嵌套 `S`，并读回比对；
  - 补至少一处多层嵌套；
  - 可以顺带补 `S` 在前的属性顺序，以及列表内 map 的 `S` 属性，防止“加了列表递归反而弄坏”；
  - 保留 key 的两条报错断言。
  这些断言 gold 都能通过，**gold 仍可作正对照**。
- **若要断言“非 key 的 S→dict 仍报 SerializationException”**：依据是有的（base 行为、代码注释、N→int 的同类 P2P），但 gold 过不了，需要按 D4 用经独立核实的替代正对照，并记录 gold 失败。这条是罕见路径，我倾向**可选**：只有它能挡住会造成更坏后果（如存入错误数据）的已知错误候选时，才值得为它换正对照。
- 当前用途：SWE-Gym 暂无修订机制（D6），原版只作问题定位；修订版待机制落地后按 §5 验收。
