# getmoto__moto-6185 独立复核

2026-09-30 / 独立复核者（Claude 子代理，不继承作者上下文）。初判见同目录 [review_initial.md](review_initial.md)，写于读作者 `result.md`、`evidence/` 与实验目录之前，之后未改，sha256 `f040cfcfd953b85d082e0397aa490685ba9d4a3c58d4686ef7f0ea668e6b8cf8`。该文件已被负责人的快照提交 `945d39cf` 一并提交（不是我提交的），提交内容与这个哈希一致。复核进行中，负责人转达了三条判断原则（来自 Codex 09-30 对本批的复核意见），本页按这三条执行；与初判不同的地方见 §0。

**总判断：部分同意，阻断项 3 项。**

1. **同意**作者对原题的诊断：原版 S1（T2a：嵌套 `S` 无断言；T2b：吞错候选得 1），没有 T1，P4 登记。gold 两处缺口的实测事实属实。v2 新增的断言都有公开依据，没有误拒合理实现。
2. **不同意**把 gold 两处缺口与 `rootkey` 记 T3、以 v2 为默认（**B1**）：
   - 缺口 1 就是题面缺陷本身，只是表的主键恰好叫 `M`；
   - 缺口 2 是 base 服务端校验的回归。

   按原则 2，两处都应由修订版断言，也就是走作者预留的 v2s 路线：正对照换成 `ctx`，`parity` 作第二正对照，gold 的失败留档。
3. **v2s 也还不能直接验收**。它放过了我构造的两个错误候选：
   - `rv_depth4`：只修到两层嵌套（**B2**）；
   - `rv_tagparent`：名为 `S` 的属性，其畸形 S 值不再报 SerializationException（**B3**）。
4. **`ctx`、`parity` 可以作正对照**（§3）：
   - 两者都相当于“base 去掉误报”：与 base 的差异只出现在含 `S` 这个名字的条目上；
   - 与 gold 的差异只在 gold 的两处缺口上；
   - 在评分 UID 与 root 下结果相同。
5. **修法**：草案 v3 = v2s 加四行数据，外加三行构造五层嵌套。私有模拟下 22 个版本全部符合预期：
   - `ctx`、`parity`、`ctx_list`、`rv_dynamotype` 为 1；
   - noop、gold 和 16 个错误候选为 0，各自失败在预期的断言处。

   停止条件见 §6。

## 0．与初判的差别

- **初判（封存）**：两处缺口都倾向 T3。依据是 §4 第 4 步“只影响边缘输入、罕见路径 → S2（T3）”：主键名为 `M` 少见；非主键 S→dict 只在关闭参数校验时出现，而且 gold 仍是报错，不存数据。
- **原则 2 的要求**：已知错误候选不能因为“少见”“实现不自然”而放过；修订测试放过它时，要列为阻断项或给出修法；gold 两处缺口与 `rootkey` 也要明确判断是否由修订版断言。
- **改判**：据此改为“两处都应断言”，理由见 B1。
- **实验上的佐证**：v2s 中断言缺口 2 的那一行（第 993 行）拦下的不只是 `rootkey`，还有 `rv_shape_key`、`rv_swallow_attr`。这两个都是不区分“类型标签”与“属性名”的写法，说明这条断言是从另一侧检验本题的核心区分，不只为了 gold。
- **初判中另一处需要更正**：初判把“S 类型值给 dict”的非主键校验只当作可选项；现在它是默认版本的一部分。其余判断（S1、无 T1、P4、gold 可修题面两例）与现在一致。

## 1．复核范围与证据层级

- **镜像**：`c3keep/moto6185:src`，image ID `sha256:47443b04…9325`，RepoDigest `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6185@sha256:ade7d85a…6eda`，与 ingest 冻结值一致。镜像内 Python 3.12.4、boto3／botocore 1.35.9，`moto` 4.1.7.dev 从 `/testbed` 导入。
- **材料**：
  - gold `868fd2d1…79e1` 与原 test_patch `506b3670…fc52`，都从 `s2/ingest/` 的 bundle 直接取出；
  - 作者 v2 `7bbae287…c3a9`、v2s `4122cced…25e4`，与作者正式评分 `audit_*/materials.json` 里的 test_patch 逐一核对一致；
  - 我的草案 v3 `fc65a527…332d`，由 [`make_v3_draft.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/moto6185/review/make_v3_draft.py) 从 v2s 生成。
- **我的运行**：只做**私有对照**与**私有模拟评分**。容器都是一次性的，`--network none`，以 root 运行，每个版本用一个新容器；**没有运行正式评分**。
  - 私有模拟评分用评分包的测试命令 `pytest -n0 -rA`（另加 `-p no:cacheprovider --tb=short`）跑 `tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py`；
  - 按 SWE 解析规则（状态词＋节点名取到第一个空白为止，两个 `[set …]` 节点因此合并为一个键）逐项核对 F2P 1 项、P2P 34 项；
  - 每次运行都解析出 35 个键。
- **版本（22 个）**：
  - base（noop）、gold；
  - 作者的 12 个候选：`ctx`、`parity`、`ctx_list`、`top_only`、`siblings`、`depth2`、`list_as_names`、`null_only`、`shape`、`rootkey`、`swallow`、`skip_s_subtree`；
  - 我构造的 8 个，见 §4.1。
- **测试版本（4 个）**：原材料、v2、v2s、v3。
- **补充检查**：
  - 行为探针 [`probe_review.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/moto6185/review/probe_review.py)，39 行，每个版本都跑；
  - [`probe_extra.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/moto6185/review/probe_extra.py)，10 行，跑 9 个版本；
  - `tests/test_dynamodb` 全套，跑 gold、ctx、parity、ctx_list、rv_dynamotype；
  - v3 在 UID 54322 与 root 下的对比，跑 gold、ctx、parity。
- **作者证据**：
  - 读了三组正式评分全部 42 条账本、`failure_reasons.txt`、`materials.json`；
  - 读了 `semantic_v2_matrix.md`；
  - 核对了 `evidence_manifest.json`：已归档的 326 个文件哈希全部一致；未归档的 254 个都在 `artifacts/`、`prepared/`、`private/` 下，与作者的说明相符。
- **脚本与输出**都在 [`moto6185/review/`](../../../../../../../rh2/experiments/category3_cloud_20260929/moto6185/review/)：
  - 汇总表 `results.md`、`extra.md`、`uid_check.txt`；
  - 逐版本记录 `out/<版本>/record.json`，含候选 sha256、每个测试版本的分数、P2P、失败行与探针结果；
  - 复现命令见该目录各脚本的文件头。

## 2．作者主张逐条核对

| # | 作者主张（result.md） | 我的核对 | 结论 |
| --- | --- | --- | --- |
| 1 | gold 对题面两例、字符串值、两层嵌套、list 内 map、batch／transact 入口都能写入并等值读回 | probe_review 的 L、K 组；另测三层、四层嵌套，`S` 的值为 map／list／bool／set，`S` 排在最前 | 属实，这些情形 gold 都正常 |
| 2 | 缺口 1：主键名为 `M` 时嵌套 `S` 仍报错 | 初判 probe0 与 probe_review（HASH 键）；RANGE 键未测，按源码 `table_key_attrs` 同理 | 属实 |
| 3 | 缺口 2：关闭参数校验时，非主键 `S`→dict 在 gold 下抛内部 `AttributeError`，条目没有存入 | 调用栈：`table.py:558 put_item` → `dynamo_type.py:282 Item.__init__` → `:260 __setitem__` → `:208 size` → `utilities.py:16 bytesize`；之后 get、scan 都为空 | 属实 |
| 4 | 上游到 5.2.3 仍是 gold 写法（只作佐证） | 自行下载 PyPI wheel：4.1.5 仍是 base 写法；4.2.14、5.0.28、5.2.3 与 gold 逻辑相同（改用 `isinstance`） | 属实；4.1.8 与上游测试文件未核 |
| 5 | 原测试是漏检不是误拒；6 个错误候选在原材料正式评分中得 1 | 读 formal 14 条账本；私有模拟逐格复现 | 属实。我构造的 7 个错误候选（含与 gold 同类的 `rv_shape_key`）在原材料下也都得 1 |
| 6 | 原版 S1（T2a＋T2b） | 对照题面与原 test_patch | 同意；T2b 的措辞见 §5 建议 2 |
| 7 | 无 T1：三份不同写法的合理实现在原材料下得 1；两条精确文案来自公开旧测试 | 私有模拟；另加 `rv_dynamotype`（用 DynamoType 解析），原材料为 1 | 同意 |
| 8 | P4：题面原例没写 region | 原样运行报 `NoRegionError`；设 `AWS_DEFAULT_REGION=us-east-1` 后复现 SerializationException | 同意 |
| 9 | v2 新增断言有公开依据；gold、ctx、ctx_list、parity 为 1，9 个错误候选为 0，`rootkey` 为 1 | 读 v2 账本与 materials（均为 `7bbae287…`）；私有模拟逐格复现，失败行一致 | 事实属实。依据与“不过严”我同意：v2 与 v3 的每个负例都只含一个类型错误，期望文案与校验顺序无关；`rv_dynamotype`、`rv_shape_key` 在 v2 上也为 1。**但 v2 另放过我构造的 5 个错误候选**（§4） |
| 10 | gold 两处缺口与 `rootkey` 记 T3（S2），默认用 v2 | — | **不同意**，见 B1 |
| 11 | v2s 下 gold 为 0（986 行，`key_named_m`），ctx／parity／ctx_list 为 1，其余为 0 | 读 v2s 账本与 materials（`4122cced…`）；私有模拟逐格复现 | 属实；但 v2s 仍放过 `rv_depth4`、`rv_tagparent`（B2、B3） |
| 12 | `ctx`、`parity` 可作附加正对照，待他人核实 | §3 | 已核实，可以 |
| 13 | 私有矩阵 154 格与重跑一致；私有模拟与正式评分 42 格一致 | 我的私有模拟复现了全部 42 格的分数与失败行。作者矩阵中与我的探针重合的行（例 2 嵌套、三层、list 内 map、主键名 M／S、batch、transact、非主键 S→dict、S 在前＋嵌套 N 整数）在 14 个共同版本上一致 | 已核部分属实；矩阵其余行未逐格核 |
| 14 | 派生镜像按配方重建，三个 wheel 与登记一致 | 读 `derived/…/image.json`：三个 `expected_match` 为 true，base 层保留 | 记录一致；我未独立重建，也没有在派生镜像上跑 |
| 15 | noop 与 09-19 历史一致（36 个节点、35 个解析键、F2P 失败在第 945 行） | 私有模拟：1 failed、35 passed，35 个键，失败在第 945 行 | 本批数值属实；09-19 记录未读 |

## 3．正对照核实（`ctx`、`parity`）

**3.1 是否满足公开要求。**probe_review 有 24 行合法输入，ctx、parity 全部写入并等值读回。覆盖的情形：
- 题面两例；
- 两层、三层、四层嵌套；
- `S` 的值为 map、list、bool、set；
- `S` 排在最前的属性顺序；map 里 `S` 与其它成员并列；
- list 内的 map、map 内的 list；
- batch 与 transact 入口；
- 主键名为 `M` 或 `S` 的表。

v3 的全部正例也都通过。

**3.2 是否保留相关旧行为。**
- 四个测试版本上 P2P 都是 34/34；`tests/test_dynamodb` 全套 434 passed，与 gold 相同。
- 服务端类型校验全部保留：
  - 我的探针覆盖的输入：主键与非主键的 S→int、S→dict；嵌套位置的 S→int 与 N→int；名为 `S` 的属性里面的 N 整数；排在 `S` 之后的 N 整数；同一 map 内排在 `S` 成员之后的 N 整数；
  - 结果：都报 SerializationException，文案与 base 相同，数据都没有存入；
  - 嵌套位置的 S→dict 我没有单独测，作者矩阵的 `N.nested_nonkey_S_dict` 行中 ctx、parity 为 SerEx。

**3.3 与 base、gold 的差异，是否影响判分。**逐行比较两份探针：
- **与 base 的差异**只出现在含 `S` 这个名字的条目上：
  - 24 行合法条目中有 21 行 base 报错，ctx／parity 正常写入；另 3 行是 list 相关的写法，base 本来就能写入；
  - 3 行“`S` 在前、后面还有真错误”的畸形条目，base 因误报先报 “Start of structure…”，ctx／parity 报出真实错误 “NUMBER_VALUE…”。
- **与 base 相同的行**：其余畸形输入完全相同，包括 base 原有的缺口：S 给布尔会被存入；list 里的值不校验。
- **与 gold 的差异**只有两行：主键名 `M` 加嵌套 `S`；非主键 S→dict。
- **裸值不构成差异**：成员值不是 AttributeValue 时（如 `{"A": {"M": {"S": 5}}}`），所有版本都在 botocore 客户端序列化阶段（`botocore/serialize.py` 的 `_serialize_type_structure`）抛 `AttributeError`，请求到不了 moto。
- **不影响判分**：这些差异都不落在原材料、v2、v2s、v3 或 P2P 的任何断言上。

**3.4 是否是合理修法。**
- **`ctx`**：
  - 把“属性名 → AttributeValue”和“类型标签 → 值”分成两层，`M` 的成员重新当属性名；
  - S、N 的旧检查只作用在 AttributeValue 上；
  - list 不校验，与 base 相同。
- **`parity`**：
  - 按字典深度的奇偶区分，偶数层是属性名，奇数层是类型标签；
  - 只在奇数层做 S 检查，N 检查不变。
- 两者的改动都局限在 `_validate_item_types`。
- 在 v3 上，`test_put_item__string_as_integer_value` 以评分 UID 54322 运行（`setpriv`）与以 root 运行结果相同：ctx、parity 通过，gold 失败（`uid_check.txt`）。

**结论**：两者都能作为 v2s／v3 的正对照。建议 `ctx` 为主，`parity` 为第二正对照。`ctx_list` 与 `rv_dynamotype` 可作补充的“合理实现”检查，它们另外校验 list，比 base 更严。`rv_dynamotype` 有一处与 base 不同：多类型标签的畸形值 `{"S": "a", "N": 5}` 被它存入，而 base 报错。所以它不作正对照。

## 4．反例与新问题

### 4.1 我构造的候选

补丁由 [`make_review_candidates.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/moto6185/review/make_review_candidates.py) 从 base 的 `table.py` 生成，存于 `review/candidates/`，都只改这一个文件。

| 候选 | sha256 | 性质 | 写法 | 违反的公开要求（输入） |
| --- | --- | --- | --- | --- |
| `rv_swallow_attr` | `9d37f01b…` | 错误：吞错，依赖顺序 | `put_item` 里逐个顶层属性校验；非主键属性抛出的 SerializationException 一律吞掉 | 同一嵌套 map 里 `S` 成员在前时，后面成员的 `{"N": 5}` 不报错，并以整数存入（公开 P2P 保护的非主键嵌套 N 整数校验）；非主键 S→dict 变成内部 `AttributeError`；主键名为 `S` 的表写不进带嵌套 `S` 的条目 |
| `rv_depth4` | `ae21146f…` | 错误：阈值型部分修复 | 只把第 0、2、4 层字典的键当属性名（最多两层嵌套 map） | 三层及更深的 `S` 仍报错（题面 “It could be deeply nested”） |
| `rv_scalar_s` | `e068f41a…` | 错误：只修了部分值形态 | gold 写法，另把“S 的值里还有结构”当畸形 | 名为 `S`、值为 map 的属性仍报错（资源层写法 `{'S': {'x': 'y'}}`）；另外继承 gold 两处缺口 |
| `rv_tagparent` | `9d4c841f…` | 错误：gold 思路的修正版 | 父键不是类型标签时，才把这一层当 AttributeValue | 属性名恰为类型标签时（如名为 `S` 的属性），它的值被当成属性名层：`{"S": {"S": {"S": "asdf"}}}` 抛内部 `AttributeError`，不再报 SerializationException |
| `rv_shape_key` | `d0c12753…` | 与 gold 同类 | 按根属性名判断是否主键；非主键处，`S` 的值“像 AttributeValue”时当属性名 | 主路径正确；缺口 2 与 gold 相同 |
| `rv_top_or_null` | `5d441c3e…` | 错误：示例字面值 | 只放过顶层的 `S` 与值为 NULL 的 `S` | 深层 `S` 为字符串值时仍报错 |
| `rv_break_after_s` | `48702342…` | 错误：依赖顺序 | 奇偶写法；处理完名为 `S` 的属性就 break | 同层排在 `S` 之后的属性不再校验，N 整数被存入 |
| `rv_dynamotype` | `2d73d9d7…` | 合理，与 gold、ctx、parity 都不同 | 用 moto 自己的 `DynamoType` 解析每个属性值，按类型递归（含 M 与 L）；S 的值不是字符串就报错 | —（多类型标签的畸形值与 base 不同，见 §3） |

### 4.2 私有模拟评分

1 表示 F2P 与 P2P 全过，`0@行号` 是失败在测试文件中的行。各版本的对应行：

| 断言 | v2s | v3 |
| --- | --- | --- |
| 第一组 put | 960 | 967 |
| 第二组 `pytest.raises` | 970 | 978 |
| `key_named_m` 的 put | 986 | 994 |
| 非主键 S→dict 的 put | 993 | 1006 |

v2 比 v2s 多一行注释，所以第一组、第二组分别是 961、971。顶层 `S` 的 put 在原材料和 v2 中是 945 行，在 v2s 和 v3 中是 944 行；938 是主键 S→dict 的旧断言。

| 版本 | 候选 sha256 | 原材料 | v2 | v2s | v3 |
|---|---|---|---|---|---|
| `base` | — | 0@945 | 0@945 | 0@944 | 0@944 |
| `gold` | 868fd2d1 | **1** | **1** | 0@986 | 0@994 |
| `ctx` | 139572e8 | **1** | **1** | **1** | **1** |
| `parity` | d7ca0fd9 | **1** | **1** | **1** | **1** |
| `ctx_list` | 9169306d | **1** | **1** | **1** | **1** |
| `rv_dynamotype` | 2d73d9d7 | **1** | **1** | **1** | **1** |
| `top_only` | 1d82e10d | **1** | 0@961 | 0@960 | 0@967 |
| `siblings` | c39acf3b | **1** | 0@961 | 0@960 | 0@967 |
| `depth2` | 2bdf47a6 | **1** | 0@961 | 0@960 | 0@967 |
| `list_as_names` | f4a791b5 | **1** | 0@961 | 0@960 | 0@967 |
| `null_only` | 23b58b21 | 0@945 | 0@945 | 0@944 | 0@944 |
| `shape` | 36f1b5d7 | 0@938 | 0@938 | 0@938 | 0@938 |
| `rootkey` | 0232a04f | **1** | **1** | 0@993 | 0@1006 |
| `swallow` | 35a765d8 | **1** | 0@971 | 0@970 | 0@978 |
| `skip_s_subtree` | c273d7e3 | **1** | 0@971 | 0@970 | 0@978 |
| `rv_swallow_attr` | 9d37f01b | **1** | **1** | 0@993 | 0@978 |
| `rv_depth4` | ae21146f | **1** | **1** | **1** | 0@967 |
| `rv_scalar_s` | e068f41a | **1** | **1** | 0@986 | 0@967 |
| `rv_tagparent` | 9d4c841f | **1** | **1** | **1** | 0@1006 |
| `rv_shape_key` | d0c12753 | **1** | **1** | 0@993 | 0@1006 |
| `rv_top_or_null` | 5d441c3e | **1** | 0@961 | 0@960 | 0@967 |
| `rv_break_after_s` | 48702342 | **1** | 0@971 | 0@970 | 0@978 |

- 所有运行的 P2P 都是 34/34，参考键无缺席。
- 作者 14 个版本在原材料、v2、v2s 上的 42 格，分数与失败行都和作者的正式账本逐格一致。
- `rv_tagparent` 在 v3 第 1006 行失败于循环的第二例（名为 `S` 的属性）。`rootkey`、`rv_shape_key` 失败于第一例（`attr`），见 `extra.md` 的前两行。

### 4.3 行为探针摘录（`probe_review.py`）

合法行记 ok 表示写入且等值读回；畸形行记 **存入** 表示 put 成功、之后读得到含整数 N 的错误数据。

| 版本 | 例2 嵌套 | 三层 map | S 的值是 map | 主键名 M＋嵌套 S | 主键名 S＋嵌套 S | 非主键 S→dict | S 在前＋嵌套 N 整数 | 同一 map 内 S 在前＋N 整数 |
|---|---|---|---|---|---|---|---|---|
| `base` | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx |
| `gold` | ok | ok | ok | SerEx | ok | AttrErr | SerEx | SerEx |
| `ctx`、`parity`、`ctx_list`、`rv_dynamotype` | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx |
| `rootkey`、`rv_shape_key` | ok | ok | ok | ok | ok | AttrErr | SerEx | SerEx |
| `swallow` | ok | ok | ok | ok | SerEx | AttrErr | **存入** | **存入** |
| `rv_swallow_attr` | ok | ok | ok | ok | SerEx | AttrErr | SerEx | **存入** |
| `rv_break_after_s` | ok | ok | ok | ok | ok | SerEx | **存入** | **存入** |
| `rv_depth4` | ok | SerEx | ok | ok | ok | SerEx | SerEx | SerEx |
| `rv_scalar_s` | ok | ok | SerEx | SerEx | ok | AttrErr | SerEx | SerEx |
| `rv_tagparent` | ok | ok | ok | ok | ok | SerEx（`S` 命名时 AttrErr） | SerEx | SerEx |

完整 22 行 × 11 列见 `results.md`。

### 4.4 新发现

- **v2 放过 7 个违反公开要求的版本**：gold 本身、`rootkey`、`rv_shape_key`（这三个是缺口 2；gold 另有缺口 1），以及 `rv_swallow_attr`、`rv_scalar_s`、`rv_depth4`、`rv_tagparent`。
  - `rv_swallow_attr` 会静默存入错误数据，与作者据以判 T2b 的 `swallow` 同一性质，只是吞错的粒度细到单个属性，v2 第二组的顶层两例因此拦不住它。
  - `rv_scalar_s` 在“名为 `S`、值为 map 的属性”这一常见写法上仍报题面那条错误。
- **v2s 放过 2 个**：`rv_depth4`、`rv_tagparent`。另外两个（`rv_scalar_s`、`rv_swallow_attr`）得 0，但只是附带拦下：
  - `rv_scalar_s` 沿用 gold 的父键写法，失败在 `key_named_m`；
  - `rv_swallow_attr` 吞错后让畸形 S→dict 走到内部错误，失败在非主键 S→dict 一行；
  - v2s 并没有针对它们各自缺陷的断言。
- **原测试的漏检面比作者列的更宽**：`rv_top_or_null`、`rv_break_after_s` 在原材料下也得 1。这进一步支持 S1，v2 起它们为 0。
- **范围外的 base 旧缺口**（`extra.md`）：S 给布尔值会被存入；list 里的值不校验（`{"L": [{"N": 5}]}` 以整数存入）。base、gold、ctx、parity 在这些输入上完全相同。多类型标签的畸形值在 base 下报错，只因 base 扫描全部键。见 §5 建议 4。

## 5．阻断项与非阻断建议

### 阻断项（3 项）

**B1　默认版本必须断言 gold 的两处缺口，也就是作者预留的 v2s 路线。**
- **当前行为**：结论页以 v2 为默认，把 gold 缺口 1、缺口 2 与 `rootkey` 记 T3；v2 下 gold、`rootkey`、`rv_shape_key` 都得 1。
- **判断与依据**：
  - **缺口 1 违反核心要求本身。**
    - 题面标题与正文要求：Item 中任何位置（含嵌套）的属性名 `S` 都可以写入，对表的主键名没有任何限制。
    - gold 在主键名为 `M` 的表上，对 `{"A": {"M": {"S": {"NULL": true}}}}` 仍报题面那条 SerializationException（v2s 第 986 行，v3 第 994 行）。
    - 这不是实现方式之争，符合原则 1：ctx、parity、ctx_list、rv_dynamotype、rootkey、rv_shape_key、rv_tagparent 在这张表上都能写入。修好了题面例 2 的版本里，失败的只有沿用 gold“父键是否主键”写法的 gold 与 `rv_scalar_s`。
  - **缺口 2 是公开旧行为的回归。**
    - base 的 `_validate_item_types` 对所有属性检查 S→dict，注释写明“用户可以关闭参数校验，所以服务端也要拦”。这段代码来自 `/testbed` git 历史中可见的提交 `37845792d`（#5654）。
    - 公开 P2P `test_put_item_wrong_datatype` 以注释 “Same thing - but with a non-key, and nested” 对非主键嵌套的 N→int 做了同类断言。
    - gold 下这类输入变成直接穿出 client 的 `AttributeError`，调用方按 `ClientError` 处理会出错。
    - 满足这条的写法有多种：ctx、parity、ctx_list、rv_dynamotype。
  - **`rootkey`、`rv_shape_key` 与缺口 2 的行为相同，应为 0。**
  - **规则依据**：
    - 原则 2：这些都是已知错误行为，不能以“少见”登记 T3 放过；
    - D4 允许用经独立核实的替代解作正对照、记录 gold 失败，并要求“任何情况下都不为保住 gold 而放宽需求”；
    - 同类先例：pydantic-9066 的修订版上 gold 为 0。
- **修法**：
  - 默认采用 v2s 路线，补上 B2、B3，也就是草案 v3；
  - 正对照 `ctx`，第二正对照 `parity`；
  - gold 的失败留档：v3 第 994 行，主键名 `M` 的表上嵌套 `S` 报 SerializationException。若去掉该行，gold 还会在第 1006 行非主键 S→dict 处失败。
  - 注明上游 4.2.14–5.2.3 与 gold 写法相同。
- **修后预期（已私有验证，§4.2 v3 列）**：gold、`rootkey`、`rv_shape_key` 为 0；ctx、parity 为 1。

**B2　v2s 仍放过 `rv_depth4`（阈值型部分修复）。**
- **当前行为**：只把最多两层嵌套 map 里的键当属性名。三层及更深的 `S` 仍报 SerializationException（探针 `L.deep3_S`、`L.deep4_S`、`N.ok_deep3`）。v2、v2s 最深的实例只有两层（`deeply_nested`），所以它在两版上都得 1。
- **违反**：题面 “It could be deeply nested, and still raise the exception”“It does not matter where in the payload it might be”。
- **修法**：第一组加 `five_levels_deep` 一例。v3 第 950–953 行构造，第 963 行加入列表。
- **修后预期**：`rv_depth4` 为 0（第 967 行）；ctx、parity、ctx_list、rv_dynamotype 与 gold 都能通过这一例。

**B3　v2s 仍放过 `rv_tagparent`。**
- **当前行为**：
  - 属性名恰为类型标签时，它的值被当成属性名层；
  - `{"S": {"S": {"S": "asdf"}}}` 不再报 SerializationException，而是穿出内部 `AttributeError`；
  - `{"attr": {"S": {"S": "asdf"}}}` 仍正常报错，所以 v2s 只有这一例时拦不住它（`extra.md` 前两行）。
- **违反**：与 B1 缺口 2 相同的公开旧行为，而输入正是本题关心的“名为 `S` 的属性”。
- **修法**：v2s 的“非主键 S 类型值不能是 dict”断言改为两例循环，补上 `{"S": {"S": {"S": "asdf"}}}`（v3 第 1001–1003 行）。
- **修后预期**：`rv_tagparent` 为 0（第 1006 行，第二例）；ctx、parity、ctx_list、rv_dynamotype 通过。

### 非阻断建议

1. **保留 v3 中另外两行直接断言**：
   - 两行分别是：“名为 `S` 的属性本身是 map”（第 964 行）；“同一 map 内 `S` 成员排在 N 整数成员之前”（第 976 行）。
   - 为什么需要：v2s 虽然也让 `rv_scalar_s`、`rv_swallow_attr` 得 0，但靠的是它们的其它缺陷，没有针对各自问题的断言。
   - 代价：这两行都有公开依据（依据与 v2 第一组、第二组相同），gold 也能通过。gold 在 v3 上的 0 只来自 B1 的两处。
2. **作者 §4 T2b 的措辞**：
   - `swallow`、`skip_s_subtree` 的触发输入同样要求关闭参数校验，与缺口 2 的前提相同，“不属于边缘输入”的说法不准确。
   - 两者的真实区别在于：前者违反的是公开 P2P 直接断言的行为，而且是静默存入。
   - 按原则 2，两类都应断言，这一区分已不影响处置。
3. **结论页相应更新**：
   - §1 需求表 R5、R6 的“罕见路径／少见配置”改为已断言；
   - §4 “G1＋T3” 改为按 B1 处置；
   - §5 交接第 1、2、6 条改为 v3 与 ctx 正对照；
   - §7 记录本页结论。
4. **范围外、不断言、只登记**：list 里的畸形值；S 给布尔值；多类型标签的值。依据：
   - 题面与公开测试都不涉及 list 内容、布尔值或多类型标签；
   - base、gold、ctx、parity 在这些输入上行为相同，不是本题修法引入的回归；
   - 若断言，会把 ctx、parity 这类只修题面问题、其余保持 base 行为的合理实现判 0，属于测试要求超出题面（P3）。
5. **`rv_dynamotype` 不作正对照**：它在多类型标签的畸形值上存入了 base 会拒绝的数据（见 §3）；只作“与 gold、ctx、parity 机制都不同的合理实现”这一检查。

## 6．停止条件

1. **第2类要做的**：把 v3（sha256 `fc65a527…332d`）经 D6 测试补丁替换接成正式材料；测试 ID、P2P、测试命令都不变。之后做一次正式诊断评分，至少覆盖：
   - noop、gold、ctx、parity、ctx_list、`rootkey`；
   - 作者的 9 个错误候选；
   - 我的 7 个错误候选；
   - `rv_dynamotype`。

   预期与 §4.2 v3 列逐格一致，失败行也一致。
2. **一致即结束**：本题第3类工作即告完成，转第2类，不需要再做本题的聚焦复核。v3 相对 v2s 只加了数据行，没有改变断言的写法与依据。Codex 复核照常。
3. **有不一致时**：只定位不一致的那一格（材料哈希、镜像、UID、解析），不重新开放题目判断。
4. **以下不再构成阻断理由，只登记**：
   - 深于五层嵌套的阈值写法；
   - 除 `S` 以外其它“属性名恰为类型标签”的畸形值组合；
   - base 本来就不校验的输入（list 内的值、S 给布尔或列表、多类型标签）；
   - 服务器模式下的 HTTP 状态码；
   - 真实 AWS 的确切报错文案。

   依据：它们都不是题面要求，也不是本题修法引入的回归；review-standards §10.5 第 8 条规定“还能想出反例”不构成继续阻塞的理由。

## 7．未查

- **正式评分**：按要求没有运行。v3 只有私有模拟，正式诊断评分由第2类在 D6 落地后做。
- **派生镜像**：未独立重建，也没有在派生镜像上跑；只读了作者的重建记录。
- **actor 条件**：没有查 actor 开发条件（UID 54321、public_hints 注入），也没有按公开读者的命令清单原样重跑。
- **真实 AWS**：没有核对真实 AWS 的行为，例如 S 给 list 或多类型标签时的确切报错；也没有在服务器模式（`TEST_SERVER_MODE=true`）下查状态码。F2P 函数在服务器模式下本来就跳过。
- **模型求解证据**：没有。
- **其它**：
  - 09-19 历史运行记录、X1 跨题关系、上游 4.1.8 与上游测试文件，都未核；
  - 作者私有矩阵中与我的探针不重合的行未逐格核对；
  - RANGE 键名为 `M` 的情形只按源码推断，未实测。
